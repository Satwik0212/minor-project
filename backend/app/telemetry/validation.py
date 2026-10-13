"""MQTT message decoding, topic parsing, and JSON schema validation.

Normative source: docs/integration.md §2, §3, §5, §15; docs/schemas/*.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, Optional, Tuple

import jsonschema

# Topic format patterns according to docs/integration.md §2
DEVICE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"
DEVICE_ID_REGEX = re.compile(DEVICE_ID_PATTERN)

TOPIC_TELEMETRY_REGEX = re.compile(r"^smartwaste/device/([A-Za-z0-9_-]{1,64})/telemetry$")
TOPIC_STATUS_REGEX = re.compile(r"^smartwaste/device/([A-Za-z0-9_-]{1,64})/status$")
TOPIC_CONFIG_REGEX = re.compile(r"^smartwaste/device/([A-Za-z0-9_-]{1,64})/config$")
TOPIC_ACK_REGEX = re.compile(r"^smartwaste/device/([A-Za-z0-9_-]{1,64})/ack$")


def _find_schemas_dir() -> Path:
    """Find docs/schemas directory across dev, package, and container layouts."""
    candidates = [
        Path(__file__).resolve().parents[3] / "docs" / "schemas",
        Path.cwd() / "docs" / "schemas",
        Path.cwd().parent / "docs" / "schemas",
    ]
    for candidate in candidates:
        if candidate.exists() and (candidate / "mqtt-telemetry-v1.schema.json").exists():
            return candidate
    raise FileNotFoundError("docs/schemas directory containing canonical schemas not found.")


SCHEMAS_DIR = _find_schemas_dir()

with open(SCHEMAS_DIR / "mqtt-telemetry-v1.schema.json", "r", encoding="utf-8") as f:
    TELEMETRY_SCHEMA = json.load(f)

with open(SCHEMAS_DIR / "mqtt-status-v1.schema.json", "r", encoding="utf-8") as f:
    STATUS_SCHEMA = json.load(f)

TELEMETRY_VALIDATOR = jsonschema.Draft202012Validator(
    TELEMETRY_SCHEMA,
    format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
)

STATUS_VALIDATOR = jsonschema.Draft202012Validator(
    STATUS_SCHEMA,
    format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER,
)


@dataclass
class ValidationResult:
    """Outcome of decoding and validating an incoming MQTT message."""
    is_valid: bool
    payload: Optional[Dict[str, Any]] = None
    device_id: Optional[str] = None
    reason_code: Optional[str] = None
    error_message: Optional[str] = None
    redacted_payload: Optional[Dict[str, Any]] = None


def redact_payload(data: Any, max_depth: int = 5) -> Any:
    """Redact sensitive fields (passwords, tokens, credentials, secrets) from payload."""
    if max_depth <= 0 or data is None:
        return data

    sensitive_keys = {"password", "secret", "token", "credential", "auth", "api_key"}

    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            if any(s in str(k).lower() for s in sensitive_keys):
                redacted[k] = "[REDACTED]"
            elif isinstance(v, (dict, list)):
                redacted[k] = redact_payload(v, max_depth - 1)
            else:
                redacted[k] = v
        return redacted
    elif isinstance(data, list):
        return [redact_payload(item, max_depth - 1) for item in data]
    return data


def parse_iso8601_utc(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse strictly formatted ISO-8601 UTC timestamp ending in Z."""
    if not ts_str:
        return None
    if not ts_str.endswith("Z"):
        return None
    try:
        # Replace Z with +00:00 for datetime.fromisoformat
        dt = datetime.fromisoformat(ts_str[:-1] + "+00:00")
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def decode_and_validate_telemetry(payload_bytes: bytes, topic: str) -> ValidationResult:
    """Decode raw bytes and validate against topic rules and mqtt-telemetry-v1.schema.json.

    Rejection codes from docs/integration.md §15:
        - UNAUTHORIZED_TOPIC: Malformed topic or invalid topic device segment
        - INVALID_JSON: Non-UTF8 or malformed JSON
        - UNSUPPORTED_SCHEMA_VERSION: schema_version != 1
        - SCHEMA_VALIDATION_FAILED: Schema constraints or message_id contract violated
        - TOPIC_DEVICE_MISMATCH: Topic device_id does not match payload device_id
        - INVALID_TIMESTAMP: time_synced is True but timestamp is not valid UTC ISO-8601
    """
    # 1. Topic structure validation
    topic_match = TOPIC_TELEMETRY_REGEX.match(topic)
    if not topic_match:
        return ValidationResult(
            is_valid=False,
            reason_code="UNAUTHORIZED_TOPIC",
            error_message=f"Topic does not match required pattern: {topic}",
        )

    topic_device_id = topic_match.group(1)

    # 2. UTF-8 decode
    try:
        payload_str = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ValidationResult(
            is_valid=False,
            device_id=topic_device_id,
            reason_code="INVALID_JSON",
            error_message=f"Payload is not valid UTF-8: {exc}",
            redacted_payload={"raw_bytes_len": len(payload_bytes)},
        )

    # 3. JSON parse
    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            is_valid=False,
            device_id=topic_device_id,
            reason_code="INVALID_JSON",
            error_message=f"Malformed JSON: {exc}",
            redacted_payload={"raw_text": payload_str[:500]},
        )

    if not isinstance(payload, dict):
        return ValidationResult(
            is_valid=False,
            device_id=topic_device_id,
            reason_code="SCHEMA_VALIDATION_FAILED",
            error_message="Payload must be a JSON object",
            redacted_payload={"parsed_type": type(payload).__name__},
        )

    redacted = redact_payload(payload)

    # 4. Schema version check
    schema_version = payload.get("schema_version")
    if schema_version != 1:
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=topic_device_id,
            reason_code="UNSUPPORTED_SCHEMA_VERSION",
            error_message=f"Unsupported schema_version: {schema_version}. Only version 1 is supported.",
            redacted_payload=redacted,
        )

    # 5. Canonical JSON Schema validation
    errors = list(TELEMETRY_VALIDATOR.iter_errors(payload))
    if errors:
        error_msgs = [f"{e.json_path}: {e.message}" for e in errors]
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=topic_device_id,
            reason_code="SCHEMA_VALIDATION_FAILED",
            error_message="; ".join(error_msgs),
            redacted_payload=redacted,
        )

    payload_device_id = payload.get("device_id")

    # 6. Topic and payload device_id match
    if topic_device_id != payload_device_id:
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=topic_device_id,
            reason_code="TOPIC_DEVICE_MISMATCH",
            error_message=f"Topic device_id '{topic_device_id}' does not match payload device_id '{payload_device_id}'",
            redacted_payload=redacted,
        )

    # 7. message_id format contract verification: {device_id}:{boot_id}:{sequence}
    boot_id = payload.get("boot_id")
    sequence = payload.get("sequence")
    expected_message_id = f"{payload_device_id}:{boot_id}:{sequence}"
    if payload.get("message_id") != expected_message_id:
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=payload_device_id,
            reason_code="SCHEMA_VALIDATION_FAILED",
            error_message=f"message_id must equal '{expected_message_id}', got '{payload.get('message_id')}'",
            redacted_payload=redacted,
        )

    # 8. Timestamp validity check
    time_synced = payload.get("time_synced", False)
    raw_timestamp = payload.get("timestamp")
    if time_synced:
        parsed_dt = parse_iso8601_utc(raw_timestamp)
        if parsed_dt is None:
            return ValidationResult(
                is_valid=False,
                payload=payload,
                device_id=payload_device_id,
                reason_code="INVALID_TIMESTAMP",
                error_message=f"Invalid ISO-8601 UTC timestamp: {raw_timestamp}",
                redacted_payload=redacted,
            )

    return ValidationResult(
        is_valid=True,
        payload=payload,
        device_id=payload_device_id,
        redacted_payload=redacted,
    )


def decode_and_validate_status(payload_bytes: bytes, topic: str) -> ValidationResult:
    """Decode raw bytes and validate against topic rules and mqtt-status-v1.schema.json."""
    topic_match = TOPIC_STATUS_REGEX.match(topic)
    if not topic_match:
        return ValidationResult(
            is_valid=False,
            reason_code="UNAUTHORIZED_TOPIC",
            error_message=f"Topic does not match required status pattern: {topic}",
        )

    topic_device_id = topic_match.group(1)

    try:
        payload_str = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return ValidationResult(
            is_valid=False,
            device_id=topic_device_id,
            reason_code="INVALID_JSON",
            error_message=f"Status payload is not valid UTF-8: {exc}",
            redacted_payload={"raw_bytes_len": len(payload_bytes)},
        )

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            is_valid=False,
            device_id=topic_device_id,
            reason_code="INVALID_JSON",
            error_message=f"Malformed JSON in status: {exc}",
            redacted_payload={"raw_text": payload_str[:500]},
        )

    if not isinstance(payload, dict):
        return ValidationResult(
            is_valid=False,
            device_id=topic_device_id,
            reason_code="SCHEMA_VALIDATION_FAILED",
            error_message="Status payload must be a JSON object",
            redacted_payload={"parsed_type": type(payload).__name__},
        )

    redacted = redact_payload(payload)

    schema_version = payload.get("schema_version")
    if schema_version != 1:
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=topic_device_id,
            reason_code="UNSUPPORTED_SCHEMA_VERSION",
            error_message=f"Unsupported status schema_version: {schema_version}",
            redacted_payload=redacted,
        )

    errors = list(STATUS_VALIDATOR.iter_errors(payload))
    if errors:
        error_msgs = [f"{e.json_path}: {e.message}" for e in errors]
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=topic_device_id,
            reason_code="SCHEMA_VALIDATION_FAILED",
            error_message="; ".join(error_msgs),
            redacted_payload=redacted,
        )

    payload_device_id = payload.get("device_id")
    if topic_device_id != payload_device_id:
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=topic_device_id,
            reason_code="TOPIC_DEVICE_MISMATCH",
            error_message=f"Status topic device_id '{topic_device_id}' != payload device_id '{payload_device_id}'",
            redacted_payload=redacted,
        )

    raw_timestamp = payload.get("timestamp")
    parsed_dt = parse_iso8601_utc(raw_timestamp)
    if parsed_dt is None:
        return ValidationResult(
            is_valid=False,
            payload=payload,
            device_id=payload_device_id,
            reason_code="INVALID_TIMESTAMP",
            error_message=f"Invalid ISO-8601 UTC timestamp in status: {raw_timestamp}",
            redacted_payload=redacted,
        )

    return ValidationResult(
        is_valid=True,
        payload=payload,
        device_id=payload_device_id,
        redacted_payload=redacted,
    )
