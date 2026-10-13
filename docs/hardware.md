# SWM-ICS Hardware and MQTT Contract

## 1. Responsibilities

The hardware measures and reports raw sensor/device values. It does **not** own the authoritative fill calculation, alert prioritization, ML prediction, or route optimization.

Core prototype:
- ESP32 DevKit
- Ultrasonic sensor for distance from sensor face to waste surface
- Load cell + HX711 for approximate waste mass
- BME280 or DHT22 for temperature and humidity
- Regulated power supply and weather-appropriate enclosure

Environmental and weight sensors may be optional in the smallest proof-of-concept if the team explicitly marks missing values `null`; do not fabricate values.

## 2. Sampling and sensor handling

Proposed prototype interval: 60 seconds, configurable. Read sensors, validate plausibility, then publish one telemetry envelope. Use median of 3–5 ultrasonic samples with a short delay to reduce spikes; reject timeout/out-of-range readings. Tare and calibrate load cell using known weights. Record a sensor fault instead of publishing zero when a sensor fails.

Firmware publishes raw `distance_cm`, `weight_kg`, `temperature_c`, `humidity_percent`, health and firmware information. The backend calculates `fill_percent` from the latest approved bin calibration. Local firmware may calculate a non-authoritative diagnostic estimate only.

## 3. MQTT connection and topics

Use MQTT over TLS, normally port 8883, with per-device credentials and broker ACLs.

- `smartwaste/device/{device_id}/telemetry` — device → backend
- `smartwaste/device/{device_id}/status` — device → backend
- `smartwaste/device/{device_id}/config` — backend → device
- `smartwaste/device/{device_id}/ack` — device → backend

`device_id` topic segment must match `^[A-Za-z0-9_-]{1,64}$`. Topic identity must match payload identity. `bin_id` is resolved by backend from the active device/bin assignment, not trusted from the device.

## 4. Canonical telemetry JSON

The normative JSON schema is `schemas/mqtt-telemetry-v1.schema.json`; the following is a conforming example:

```json
{
  "schema_version": 1,
  "message_id": "ESP32-A123:8b7c3c82-9a9e-4c90-a4f2-9a1e2f0f4c33:42",
  "device_id": "ESP32-A123",
  "boot_id": "8b7c3c82-9a9e-4c90-a4f2-9a1e2f0f4c33",
  "sequence": 42,
  "timestamp": "2026-10-12T10:30:00Z",
  "time_synced": true,
  "firmware_version": "0.1.0",
  "measurements": {
    "distance_cm": 20.4,
    "weight_kg": 43.5,
    "temperature_c": 31.5,
    "humidity_percent": 61.0
  },
  "health": {
    "reported_state": "ONLINE",
    "sensor_faults": [],
    "rssi_dbm": -61,
    "battery_percent": null
  }
}
```

If time is not synchronized, use `timestamp: null` and `time_synced: false`. Server uses `received_at` as effective time and records `timestamp_quality=SERVER_RECEIVED_FALLBACK`. If time is synchronized, timestamp must end in `Z` and `time_synced=true`.

`message_id` must equal `{device_id}:{boot_id}:{sequence}`. Generate one UUID `boot_id` at each boot and increment `sequence` for each telemetry message. Backend deduplication key is `(device_id, boot_id, sequence)`.

## 5. Units and nullable values

| Field | Unit | Valid value |
|---|---|---|
| `distance_cm` | cm | finite positive number or `null` |
| `weight_kg` | kg | finite number ≥ 0 or `null` |
| `temperature_c` | °C | finite number in sensor's supported range or `null` |
| `humidity_percent` | % RH | 0–100 or `null` |
| `rssi_dbm` | dBm | integer or `null` |
| `battery_percent` | % | 0–100 or `null` |
| `fill_percent` | % | computed by backend only; never sent as authoritative telemetry |

Never encode sensor failure as zero. Fault codes: `ULTRASONIC_TIMEOUT`, `ULTRASONIC_OUT_OF_RANGE`, `LOAD_CELL_NOT_READY`, `LOAD_CELL_CALIBRATION_MISSING`, `ENV_SENSOR_READ_FAILED`, `I2C_ERROR`, `ADC_ERROR`, `LOW_BATTERY`, `UNKNOWN_SENSOR_FAULT`.

## 6. Status/config/ack schemas

Use `mqtt-status-v1.schema.json`, `mqtt-config-v1.schema.json`, and `mqtt-ack-v1.schema.json`. Device status events are `ONLINE`, `FAULT`, `MAINTENANCE`, `REBOOTED`. `OFFLINE` is inferred by the server from Last-Will or stale telemetry. Config versions increase monotonically; device acknowledges `APPLIED` or `REJECTED`.

## 7. Provisioning, activation and replacement

1. Admin creates a `DRAFT` bin and device registry entry.
2. Backend provisions per-device credentials and ACL.
3. Install and pair device; diagnostic telemetry may be stored with `eligible_for_operations=false`.
4. Activation requires a recent valid distance reading and configured required sensor checks.
5. On activation, future readings are eligible for live analytics.
6. Device replacement revokes old credentials, closes old assignment, records an audit entry, creates a new assignment and provisions new credentials. Physical `bin_id` remains unchanged.

## 8. Security and reliability

- Do not embed broker credentials in source control.
- Use TLS certificate verification, unique device credentials, ACLs, payload schema validation and message size limits.
- Use MQTT Last-Will to signal unexpected disconnect; server maps it to reported state `OFFLINE`.
- Publish QoS 1 for telemetry unless the team measures that QoS 0 is sufficient; deduplication makes at-least-once delivery safe.
- Retain rejected payload metadata and redacted payload only; never persist secrets.
- Offline detection uses DB-backed `device_offline_after_seconds`, seeded from deployment defaults at first startup.

## 9. Fill calculation

Backend formula:

`fill_percent = clamp((empty_distance_cm - distance_cm) / (empty_distance_cm - full_distance_cm) * 100, 0, 100)`

Calibration requires `empty_distance_cm > full_distance_cm > 0`. Store calibration version with each reading. Raw distance remains immutable; recalculation after a calibration correction is audited and stored as a derived revision.
