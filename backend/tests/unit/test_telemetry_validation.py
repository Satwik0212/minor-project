"""Unit tests for MQTT message decoding, topic structure, and schema validation.

Normative source: docs/integration.md §2, §3, §5, §15; docs/testing.md §1.
"""
import json
import uuid
import pytest

from app.telemetry.validation import (
    decode_and_validate_status,
    decode_and_validate_telemetry,
    redact_payload,
)


def make_valid_telemetry_dict(device_id: str = "ESP32-A123", sequence: int = 42) -> dict:
    boot_id = str(uuid.uuid4())
    return {
        "schema_version": 1,
        "message_id": f"{device_id}:{boot_id}:{sequence}",
        "device_id": device_id,
        "boot_id": boot_id,
        "sequence": sequence,
        "timestamp": "2026-10-12T10:30:00Z",
        "time_synced": True,
        "firmware_version": "0.1.0",
        "measurements": {
            "distance_cm": 20.4,
            "weight_kg": 43.5,
            "temperature_c": 31.5,
            "humidity_percent": 61.0,
        },
        "health": {
            "reported_state": "ONLINE",
            "sensor_faults": [],
            "rssi_dbm": -61,
            "battery_percent": None,
        },
    }


def test_valid_telemetry_decoding():
    data = make_valid_telemetry_dict()
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is True
    assert res.reason_code is None
    assert res.device_id == data["device_id"]
    assert res.payload["measurements"]["distance_cm"] == 20.4


def test_invalid_utf8_payload():
    payload_bytes = b"\x80\x81\x82\xff"
    topic = "smartwaste/device/ESP32-A123/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "INVALID_JSON"
    assert "UTF-8" in res.error_message


def test_malformed_json_payload():
    payload_bytes = b'{"schema_version": 1, "device_id": '
    topic = "smartwaste/device/ESP32-A123/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "INVALID_JSON"


def test_missing_required_fields():
    data = make_valid_telemetry_dict()
    del data["measurements"]  # required field
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "SCHEMA_VALIDATION_FAILED"


def test_incorrect_field_types():
    data = make_valid_telemetry_dict()
    data["sequence"] = "not_an_integer"
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "SCHEMA_VALIDATION_FAILED"


def test_nullable_sensor_values_preserved():
    data = make_valid_telemetry_dict()
    data["measurements"]["distance_cm"] = None
    data["measurements"]["weight_kg"] = None
    data["measurements"]["temperature_c"] = None
    data["measurements"]["humidity_percent"] = None
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is True
    assert res.payload["measurements"]["distance_cm"] is None
    assert res.payload["measurements"]["weight_kg"] is None


def test_topic_device_id_mismatch():
    data = make_valid_telemetry_dict(device_id="ESP32-A123")
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = "smartwaste/device/ESP32-DIFFERENT/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "TOPIC_DEVICE_MISMATCH"


def test_unsupported_or_malformed_topic():
    data = make_valid_telemetry_dict()
    payload_bytes = json.dumps(data).encode("utf-8")

    # Invalid topic path
    res = decode_and_validate_telemetry(payload_bytes, "unknown/path/telemetry")
    assert res.is_valid is False
    assert res.reason_code == "UNAUTHORIZED_TOPIC"

    # Forbidden characters in device_id segment (e.g. + or /)
    res2 = decode_and_validate_telemetry(payload_bytes, "smartwaste/device/ESP32+A123/telemetry")
    assert res2.is_valid is False
    assert res2.reason_code == "UNAUTHORIZED_TOPIC"


def test_unsupported_schema_version():
    data = make_valid_telemetry_dict()
    data["schema_version"] = 99
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "UNSUPPORTED_SCHEMA_VERSION"


def test_message_id_contract_mismatch():
    data = make_valid_telemetry_dict()
    data["message_id"] = "completely-wrong-message-id"
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code == "SCHEMA_VALIDATION_FAILED"
    assert "message_id" in res.error_message


def test_invalid_timestamp_when_time_synced():
    data = make_valid_telemetry_dict()
    data["time_synced"] = True
    data["timestamp"] = "2026-10-12 10:30:00"  # missing Z format
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = f"smartwaste/device/{data['device_id']}/telemetry"

    res = decode_and_validate_telemetry(payload_bytes, topic)
    assert res.is_valid is False
    assert res.reason_code in ("SCHEMA_VALIDATION_FAILED", "INVALID_TIMESTAMP")


def test_valid_status_decoding():
    boot_id = str(uuid.uuid4())
    data = {
        "schema_version": 1,
        "device_id": "ESP32-A123",
        "boot_id": boot_id,
        "timestamp": "2026-10-12T10:30:00Z",
        "event": "ONLINE",
        "firmware_version": "0.1.0",
        "sensor_faults": [],
        "rssi_dbm": -61,
    }
    payload_bytes = json.dumps(data).encode("utf-8")
    topic = "smartwaste/device/ESP32-A123/status"

    res = decode_and_validate_status(payload_bytes, topic)
    assert res.is_valid is True
    assert res.reason_code is None
    assert res.device_id == "ESP32-A123"


def test_redact_payload_filters_secrets():
    payload = {
        "device_id": "ESP32-A123",
        "token": "secret_token_123",
        "password": "my_password",
        "nested": {"credential_secret": "raw_pass", "safe": 123},
    }
    redacted = redact_payload(payload)
    assert redacted["token"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["credential_secret"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == 123
