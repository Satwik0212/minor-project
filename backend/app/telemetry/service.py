"""Transactional telemetry ingestion and persistence service.

Normative source: docs/integration.md §2, §3, §4, §5, §6, §7, §11, §15; docs/database.md.
"""
from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, Optional
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.bin_latest_state import BinLatestState
from app.models.calibration import SensorConfiguration
from app.models.device import Device
from app.models.device_bin_assignment import DeviceBinAssignment
from app.models.enums import (
    BinStatus,
    DeviceLifecycleState,
    DeviceReportedState,
    FillPriority,
    PredictedPriority,
    SensorHealth,
    TimestampQuality,
)
from app.models.rejected_telemetry_event import RejectedTelemetryEvent
from app.models.sensor_reading import SensorReading
from app.models.smart_bin import SmartBin
from app.telemetry.fill_calculation import (
    calculate_fill_percent,
    derive_sensor_health,
    determine_current_priority,
)
from app.telemetry.schemas import ProcessingOutcome, TelemetryProcessingResult
from app.telemetry.validation import (
    decode_and_validate_status,
    decode_and_validate_telemetry,
    parse_iso8601_utc,
)

logger = logging.getLogger(__name__)


def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure datetime has UTC tzinfo for cross-dialect comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)



def quarantine_rejected_message(
    session: Session,
    topic: str,
    reason_code: str,
    device_id: Optional[str] = None,
    payload_redacted: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> RejectedTelemetryEvent:
    """Persist a rejected/invalid telemetry event into rejected_telemetry_events table."""
    event = RejectedTelemetryEvent(
        id=uuid.uuid4(),
        device_id=device_id,
        topic=topic,
        reason_code=reason_code,
        received_at=datetime.now(timezone.utc),
        payload_redacted=payload_redacted,
        request_trace_id=None,
    )
    session.add(event)
    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        logger.error("Failed to persist quarantine event: %s", exc)
        raise
    return event


def process_telemetry_message(
    session: Session,
    topic: str,
    payload_bytes: bytes,
) -> TelemetryProcessingResult:
    """Process a raw MQTT telemetry message in a transactional boundary.

    Steps:
        1. Decode UTF-8, validate topic, and validate against canonical schema.
        2. Quarantine invalid messages to rejected_telemetry_events.
        3. Resolve registered device; quarantine UNKNOWN_DEVICE or REVOKED_DEVICE.
        4. Resolve active physical bin assignment; quarantine ASSIGNMENT_CONFLICT.
        5. Check operational eligibility based on bin status.
        6. Resolve active calibration and compute authoritative fill and priority.
        7. Enforce deduplication on (device_id, boot_id, sequence).
        8. Insert immutable SensorReading.
        9. Update device last seen/reported state.
        10. Atomically update bin_latest_state for eligible, newer events.
        11. Commit or rollback.
    """
    # 1 & 2. Message decoding and schema validation
    val_res = decode_and_validate_telemetry(payload_bytes, topic)
    if not val_res.is_valid:
        quarantine_rejected_message(
            session=session,
            topic=topic,
            reason_code=val_res.reason_code or "SCHEMA_VALIDATION_FAILED",
            device_id=val_res.device_id,
            payload_redacted=val_res.redacted_payload,
            error_message=val_res.error_message,
        )
        return TelemetryProcessingResult(
            outcome=ProcessingOutcome.REJECTED,
            device_id=val_res.device_id,
            reason_code=val_res.reason_code,
            detail=val_res.error_message,
        )

    payload = val_res.payload or {}
    device_id_str = payload["device_id"]
    boot_id = uuid.UUID(str(payload["boot_id"]))
    sequence = int(payload["sequence"])

    try:
        # 3. Resolve registered device
        device = (
            session.query(Device)
            .filter(Device.device_id == device_id_str)
            .first()
        )
        if device is None:
            quarantine_rejected_message(
                session=session,
                topic=topic,
                reason_code="UNKNOWN_DEVICE",
                device_id=device_id_str,
                payload_redacted=val_res.redacted_payload,
                error_message=f"Device '{device_id_str}' is not registered in system.",
            )
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.REJECTED,
                device_id=device_id_str,
                boot_id=boot_id,
                sequence=sequence,
                reason_code="UNKNOWN_DEVICE",
                detail=f"Device '{device_id_str}' is not registered.",
            )

        if device.lifecycle_state == DeviceLifecycleState.RETIRED:
            quarantine_rejected_message(
                session=session,
                topic=topic,
                reason_code="REVOKED_DEVICE",
                device_id=device_id_str,
                payload_redacted=val_res.redacted_payload,
                error_message=f"Device '{device_id_str}' has been retired/revoked.",
            )
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.REJECTED,
                device_id=device_id_str,
                boot_id=boot_id,
                sequence=sequence,
                reason_code="REVOKED_DEVICE",
                detail=f"Device '{device_id_str}' is retired/revoked.",
            )

        # 4. Resolve active physical bin assignment (ended_at IS NULL)
        assignment = (
            session.query(DeviceBinAssignment)
            .filter(
                DeviceBinAssignment.device_id == device.id,
                DeviceBinAssignment.ended_at.is_(None),
            )
            .first()
        )
        if assignment is None:
            quarantine_rejected_message(
                session=session,
                topic=topic,
                reason_code="ASSIGNMENT_CONFLICT",
                device_id=device_id_str,
                payload_redacted=val_res.redacted_payload,
                error_message=f"Device '{device_id_str}' has no active bin assignment.",
            )
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.REJECTED,
                device_id=device_id_str,
                boot_id=boot_id,
                sequence=sequence,
                reason_code="ASSIGNMENT_CONFLICT",
                detail=f"Device '{device_id_str}' has no active bin assignment.",
            )

        bin_obj = session.query(SmartBin).filter(SmartBin.id == assignment.bin_id).first()
        if bin_obj is None:
            quarantine_rejected_message(
                session=session,
                topic=topic,
                reason_code="ASSIGNMENT_CONFLICT",
                device_id=device_id_str,
                payload_redacted=val_res.redacted_payload,
                error_message="Active assignment references nonexistent bin.",
            )
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.REJECTED,
                device_id=device_id_str,
                boot_id=boot_id,
                sequence=sequence,
                reason_code="ASSIGNMENT_CONFLICT",
                detail="Assigned bin not found.",
            )

        # 7. Concurrency-safe Deduplication Check
        existing_reading = (
            session.query(SensorReading)
            .filter(
                SensorReading.device_id == device.id,
                SensorReading.boot_id == boot_id,
                SensorReading.sequence == sequence,
            )
            .first()
        )
        if existing_reading is not None:
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.DUPLICATE,
                reading_id=existing_reading.id,
                bin_id=bin_obj.id,
                device_id=device_id_str,
                boot_id=boot_id,
                sequence=sequence,
                fill_percent=existing_reading.fill_percent,
                reason_code="DUPLICATE_MESSAGE",
                detail="Duplicate delivery acknowledged without duplicating side effects.",
            )

        # 5. Determine operational eligibility
        if bin_obj.status == BinStatus.ACTIVE:
            eligible_for_operations = True
            eligibility_reason = None
        else:
            eligible_for_operations = False
            eligibility_reason = "BIN_NOT_ACTIVE"

        # 6. Resolve active calibration and calculate authoritative fill
        calib = (
            session.query(SensorConfiguration)
            .filter(SensorConfiguration.bin_id == bin_obj.id)
            .order_by(SensorConfiguration.calibration_version.desc())
            .first()
        )

        measurements = payload.get("measurements", {})
        raw_dist = measurements.get("distance_cm")
        raw_weight = measurements.get("weight_kg")
        raw_temp = measurements.get("temperature_c")
        raw_humidity = measurements.get("humidity_percent")

        health = payload.get("health", {})
        reported_state_str = health.get("reported_state", "ONLINE")
        try:
            reported_state = DeviceReportedState(reported_state_str)
        except ValueError:
            reported_state = DeviceReportedState.ONLINE

        sensor_faults = health.get("sensor_faults", [])
        rssi_dbm = health.get("rssi_dbm")
        battery_pct = health.get("battery_percent")

        sensor_health = derive_sensor_health(raw_dist, sensor_faults)
        quality_flags = []

        if calib is None:
            fill_percent = None
            calibration_version = None
            quality_flags.append("CALIBRATION_MISSING")
        else:
            calibration_version = calib.calibration_version
            fill_percent = calculate_fill_percent(
                raw_dist, calib.empty_distance_cm, calib.full_distance_cm
            )
            if fill_percent is None and raw_dist is not None:
                quality_flags.append("INVALID_CALIBRATION")

        current_priority = determine_current_priority(fill_percent)

        # Effective timestamp and quality
        received_at = datetime.now(timezone.utc)
        time_synced = payload.get("time_synced", False)
        if time_synced and payload.get("timestamp"):
            effective_time = parse_iso8601_utc(payload["timestamp"]) or received_at
            timestamp_quality = TimestampQuality.DEVICE_SYNCED
        else:
            effective_time = received_at
            timestamp_quality = TimestampQuality.SERVER_RECEIVED_FALLBACK

        # 8. Insert append-only SensorReading
        reading = SensorReading(
            id=uuid.uuid4(),
            bin_id=bin_obj.id,
            device_id=device.id,
            timestamp=effective_time,
            received_at=received_at,
            timestamp_quality=timestamp_quality,
            boot_id=boot_id,
            sequence=sequence,
            message_id=payload["message_id"],
            calibration_version=calibration_version,
            distance_cm=Decimal(str(raw_dist)) if raw_dist is not None else None,
            fill_percent=fill_percent,
            weight_kg=Decimal(str(raw_weight)) if raw_weight is not None else None,
            raw_hx711_count=None,
            temperature_c=Decimal(str(raw_temp)) if raw_temp is not None else None,
            humidity_percent=Decimal(str(raw_humidity)) if raw_humidity is not None else None,
            rssi_dbm=rssi_dbm,
            battery_percent=Decimal(str(battery_pct)) if battery_pct is not None else None,
            sensor_health=sensor_health,
            sensor_faults=sensor_faults,
            quality_flags=quality_flags,
            eligible_for_operations=eligible_for_operations,
            eligibility_reason=eligibility_reason,
        )
        session.add(reading)

        # 9. Update Device record
        device.last_seen_at = effective_time
        device.last_rssi_dbm = rssi_dbm
        device.reported_state = reported_state
        device.sensor_health = sensor_health
        device.firmware_version = payload.get("firmware_version", device.firmware_version)

        # 10. Update bin_latest_state atomically for eligible messages
        if eligible_for_operations:
            latest_state = (
                session.query(BinLatestState)
                .filter(BinLatestState.bin_id == bin_obj.id)
                .first()
            )
            if latest_state is None:
                latest_state = BinLatestState(
                    bin_id=bin_obj.id,
                    latest_reading_id=reading.id,
                    latest_event_at=effective_time,
                    fill_percent=fill_percent,
                    weight_kg=reading.weight_kg,
                    priority=current_priority,
                    predicted_priority=PredictedPriority.NONE,
                    sensor_health=sensor_health,
                    device_reported_state=reported_state,
                    is_stale=False,
                )
                session.add(latest_state)
            else:
                # Do not overwrite if older out-of-order reading arrives
                latest_dt = ensure_utc(latest_state.latest_event_at)
                current_dt = ensure_utc(effective_time)
                if latest_dt is None or current_dt >= latest_dt:
                    latest_state.latest_reading_id = reading.id
                    latest_state.latest_event_at = effective_time
                    latest_state.fill_percent = fill_percent
                    latest_state.weight_kg = reading.weight_kg
                    latest_state.priority = current_priority
                    latest_state.sensor_health = sensor_health
                    latest_state.device_reported_state = reported_state
                    latest_state.is_stale = False

        session.commit()
        return TelemetryProcessingResult(
            outcome=ProcessingOutcome.ACCEPTED,
            reading_id=reading.id,
            bin_id=bin_obj.id,
            device_id=device_id_str,
            boot_id=boot_id,
            sequence=sequence,
            fill_percent=fill_percent,
            current_priority=current_priority,
            sensor_health=sensor_health,
        )

    except IntegrityError as exc:
        session.rollback()
        # Concurrency guard: check if duplicate key violation occurred
        if "uq_sensor_readings_device_boot_sequence" in str(exc) or "unique" in str(exc).lower():
            dup_reading = (
                session.query(SensorReading)
                .filter(
                    SensorReading.device_id == device.id,
                    SensorReading.boot_id == boot_id,
                    SensorReading.sequence == sequence,
                )
                .first()
            )
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.DUPLICATE,
                reading_id=dup_reading.id if dup_reading else None,
                bin_id=bin_obj.id if bin_obj else None,
                device_id=device_id_str,
                boot_id=boot_id,
                sequence=sequence,
                reason_code="DUPLICATE_MESSAGE",
                detail="Concurrent duplicate detected and handled idempotently.",
            )
        logger.error("Database integrity error during telemetry persistence: %s", exc)
        raise

    except Exception as exc:
        session.rollback()
        logger.error("Unexpected error during telemetry processing: %s", exc)
        raise


def process_status_message(
    session: Session,
    topic: str,
    payload_bytes: bytes,
) -> TelemetryProcessingResult:
    """Process a raw MQTT status message in a transactional boundary."""
    val_res = decode_and_validate_status(payload_bytes, topic)
    if not val_res.is_valid:
        quarantine_rejected_message(
            session=session,
            topic=topic,
            reason_code=val_res.reason_code or "SCHEMA_VALIDATION_FAILED",
            device_id=val_res.device_id,
            payload_redacted=val_res.redacted_payload,
            error_message=val_res.error_message,
        )
        return TelemetryProcessingResult(
            outcome=ProcessingOutcome.REJECTED,
            device_id=val_res.device_id,
            reason_code=val_res.reason_code,
            detail=val_res.error_message,
        )

    payload = val_res.payload or {}
    device_id_str = payload["device_id"]
    boot_id = uuid.UUID(str(payload["boot_id"]))
    event_str = payload["event"]
    reason_code = payload.get("reason_code")
    sensor_faults = payload.get("sensor_faults", [])
    rssi_dbm = payload.get("rssi_dbm")
    firmware_version = payload.get("firmware_version")
    timestamp_str = payload.get("timestamp")
    event_time = parse_iso8601_utc(timestamp_str) or datetime.now(timezone.utc)

    try:
        device = session.query(Device).filter(Device.device_id == device_id_str).first()
        if device is None:
            quarantine_rejected_message(
                session=session,
                topic=topic,
                reason_code="UNKNOWN_DEVICE",
                device_id=device_id_str,
                payload_redacted=val_res.redacted_payload,
                error_message=f"Device '{device_id_str}' in status is not registered.",
            )
            return TelemetryProcessingResult(
                outcome=ProcessingOutcome.REJECTED,
                device_id=device_id_str,
                boot_id=boot_id,
                reason_code="UNKNOWN_DEVICE",
                detail="Device not registered.",
            )

        # Last-Will mapping: event="FAULT" with reason_code="MQTT_UNEXPECTED_DISCONNECT" -> OFFLINE
        if event_str == "FAULT" and reason_code == "MQTT_UNEXPECTED_DISCONNECT":
            reported_state = DeviceReportedState.OFFLINE
        else:
            try:
                reported_state = DeviceReportedState(event_str)
            except ValueError:
                reported_state = DeviceReportedState.ONLINE

        # Sensor health derivation for status
        sensor_health = derive_sensor_health(None if "ULTRASONIC" in str(sensor_faults) else 20.0, sensor_faults)

        device.last_seen_at = event_time
        device.reported_state = reported_state
        device.last_rssi_dbm = rssi_dbm
        device.sensor_health = sensor_health
        if firmware_version:
            device.firmware_version = firmware_version

        # Update bin_latest_state device_reported_state if bin assigned
        assignment = (
            session.query(DeviceBinAssignment)
            .filter(
                DeviceBinAssignment.device_id == device.id,
                DeviceBinAssignment.ended_at.is_(None),
            )
            .first()
        )
        if assignment is not None:
            latest_state = (
                session.query(BinLatestState)
                .filter(BinLatestState.bin_id == assignment.bin_id)
                .first()
            )
            if latest_state is not None:
                latest_dt = ensure_utc(latest_state.latest_event_at)
                ev_dt = ensure_utc(event_time)
                if latest_dt is None or ev_dt >= latest_dt:
                    latest_state.device_reported_state = reported_state
                    latest_state.sensor_health = sensor_health

        session.commit()
        return TelemetryProcessingResult(
            outcome=ProcessingOutcome.ACCEPTED,
            device_id=device_id_str,
            boot_id=boot_id,
            sensor_health=sensor_health,
            detail=f"Status event {event_str} processed successfully.",
        )

    except Exception as exc:
        session.rollback()
        logger.error("Error processing status message: %s", exc)
        raise
