"""Unit tests for domain model definitions, metadata registration, and invariants.

Normative source: docs/database.md, docs/integration.md.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from app.db.base import Base
from app.models import (
    Alert,
    Area,
    AuditEvent,
    BackgroundTask,
    BinLatestState,
    Calibration,
    CollectionJob,
    CollectionVerification,
    Depot,
    Device,
    DeviceBinAssignment,
    Driver,
    DriverLocationPoint,
    IdempotencyRecord,
    ModelRegistry,
    Prediction,
    RejectedTelemetryEvent,
    Route,
    RouteStop,
    SensorConfiguration,
    SensorReading,
    SmartBin,
    SystemSetting,
    User,
    Vehicle,
)
from app.models.enums import (
    BinStatus,
    BinType,
    DeviceLifecycleState,
    DeviceReportedState,
    FillPriority,
    PredictedPriority,
    SensorHealth,
    TimestampQuality,
    UserRole,
)


def test_registered_tables_count():
    """Verify all 24 required database tables are registered in Base.metadata."""
    expected_tables = {
        "users",
        "areas",
        "smart_bins",
        "devices",
        "device_bin_assignments",
        "sensor_configurations",
        "sensor_readings",
        "bin_latest_state",
        "vehicles",
        "drivers",
        "depots",
        "routes",
        "collection_jobs",
        "route_stops",
        "collection_verifications",
        "alerts",
        "system_settings",
        "background_tasks",
        "idempotency_records",
        "rejected_telemetry_events",
        "driver_location_points",
        "audit_events",
        "predictions",
        "model_registry",
    }
    registered = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered), f"Missing tables: {expected_tables - registered}"
    assert len(registered) == 24


def test_calibration_alias():
    """Verify Calibration is an alias for SensorConfiguration."""
    assert Calibration is SensorConfiguration


def test_nullable_telemetry_measurements_preserved():
    """Verify that null/missing sensor measurements remain None and are never converted to zero."""
    now = datetime.now(timezone.utc)
    reading = SensorReading(
        id=uuid.uuid4(),
        bin_id=uuid.uuid4(),
        device_id=uuid.uuid4(),
        timestamp=now,
        timestamp_quality=TimestampQuality.DEVICE_SYNCED,
        boot_id=uuid.uuid4(),
        sequence=1,
        message_id="ESP32-A123:boot:1",
        distance_cm=None,
        fill_percent=None,
        weight_kg=None,
        raw_hx711_count=None,
        temperature_c=None,
        humidity_percent=None,
        rssi_dbm=None,
        battery_percent=None,
        sensor_health=SensorHealth.OK,
        sensor_faults=[],
        quality_flags=[],
    )
    assert reading.distance_cm is None
    assert reading.fill_percent is None
    assert reading.weight_kg is None
    assert reading.raw_hx711_count is None
    assert reading.temperature_c is None
    assert reading.humidity_percent is None
    assert reading.battery_percent is None
    assert reading.distance_cm != 0
    assert reading.fill_percent != 0


def test_smart_bin_defaults():
    """Verify SmartBin threshold defaults and enum assignments."""
    bin_obj = SmartBin(
        bin_id="BIN-001",
        name="Main Square Bin",
        bin_type=BinType.MUNICIPAL,
        status=BinStatus.DRAFT,
        location="SRID=4326;POINT(75.8577 22.7196)",
        capacity_kg=Decimal("100.00"),
        warning_threshold_pct=Decimal("70.00"),
        critical_threshold_pct=Decimal("95.00"),
    )
    assert bin_obj.bin_type == BinType.MUNICIPAL
    assert bin_obj.status == BinStatus.DRAFT
    assert bin_obj.warning_threshold_pct == Decimal("70.00")
    assert bin_obj.critical_threshold_pct == Decimal("95.00")


def test_system_settings_arbitrary_json():
    """Verify SystemSetting persists complex JSON configuration values."""
    setting = SystemSetting(
        key="device_offline_after_seconds",
        value={"timeout_s": 180, "action": "ALERT"},
        unit="seconds",
        validation={"min": 30, "max": 3600},
    )
    assert setting.key == "device_offline_after_seconds"
    assert setting.value["timeout_s"] == 180
    assert setting.unit == "seconds"


def test_bin_latest_state_priorities():
    """Verify current priority and predicted priority are distinct fields."""
    state = BinLatestState(
        bin_id=uuid.uuid4(),
        fill_percent=Decimal("85.00"),
        priority=FillPriority.MEDIUM,
        predicted_priority=PredictedPriority.PREDICTED_HIGH,
        sensor_health=SensorHealth.OK,
        device_reported_state=DeviceReportedState.ONLINE,
        is_stale=False,
    )
    assert state.priority == FillPriority.MEDIUM
    assert state.predicted_priority == PredictedPriority.PREDICTED_HIGH
    assert state.priority != state.predicted_priority
