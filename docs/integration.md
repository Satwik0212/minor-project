# SWM-ICS — Canonical Integration Contract

**Status:** Normative. This file is the single source of truth for cross-layer names, enums, MQTT topics, units, state transitions and ownership. Other documents must match it; do not treat their old examples as alternatives.

## 1. Global conventions

- REST base path: `/api/v1`. Liveness/readiness are operational endpoints outside that base: `/health/live` and `/health/ready`.
- Browser ↔ backend: HTTPS REST + JSON. ESP32 ↔ broker: MQTT over TLS + JSON. Browser clients never subscribe directly to MQTT.
- JSON keys: `snake_case`. Timestamps: ISO-8601 UTC with `Z`. Database timestamps: `TIMESTAMPTZ`.
- IDs are stable public strings: `BIN-001`, `ESP32-A123`, `VEH-001`, `DRV-001`, `ALT-001`, `DEP-001`, `JOB-001`, `ROUTE-001`. IDs used in MQTT topic segments must match `^[A-Za-z0-9_-]{1,64}$`; `/`, `+`, `#`, spaces and control characters are forbidden.
- REST list response: `{"items":[...],"next_cursor":null}`. Errors: `{"error":{"code":"...","message":"...","details":{},"request_id":"..."}}`.
- `null` means unknown/unavailable/invalid, never zero.
- Mutating, non-repeatable operations accept `Idempotency-Key`. Same actor + same key + same body replays the original response. Same actor + same key + different body returns `409 IDEMPOTENCY_KEY_REUSED`.
- Authenticated Firebase ID token is sent as `Authorization: Bearer <firebase_id_token>`. Backend verifies it and maps the identity to a local user and one of `SUPER_ADMIN`, `OPERATOR`, `DRIVER`. Do not treat “Firebase/JWT” as two independent auth systems.

## 2. Identity and MQTT topics

Device identity and physical-bin identity are distinct. A server-side `device_bin_assignments` record determines which bin a device currently reports for. The backend must not trust a device-provided `bin_id` as authoritative.

Topics:
- Device → backend: `smartwaste/device/{device_id}/telemetry`
- Device → backend: `smartwaste/device/{device_id}/status`
- Backend → device: `smartwaste/device/{device_id}/config`
- Device → backend: `smartwaste/device/{device_id}/ack`

ACL:
- Device credential may publish only to its own `telemetry`, `status`, and `ack` topics, and subscribe only to its own `config` topic.
- Backend worker has service credentials for required topics.
- Topic `{device_id}` must equal payload `device_id`. Mismatch, unknown device, retired device or conflicting bin assignment is quarantined and audited.
- Replacement revokes the old credential/ACL and closes its assignment before the replacement device is activated.

## 3. Canonical telemetry payload v1

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

`bin_id` and `fill_percent` are deliberately absent. Server resolves bin assignment and calculates fill. `timestamp` may be `null` only when `time_synced=false`; server sets `received_at` and uses that as effective event time with `timestamp_quality=SERVER_RECEIVED_FALLBACK`. If timestamp is present, `time_synced` must be true. `message_id` is exactly `{device_id}:{boot_id}:{sequence}`.

Deduplication key: unique `(device_id, boot_id, sequence)`. `boot_id` is a UUID generated once at boot; sequence starts at zero and increments for every telemetry publication during that boot. A duplicate is acknowledged/ignored without duplicating readings or side effects.

Units:
- `distance_cm`: cm, positive finite number or `null`
- `weight_kg`: kg, non-negative finite number or `null`
- `temperature_c`: °C or `null`
- `humidity_percent`: % RH, 0–100 or `null`
- `rssi_dbm`: dBm integer or `null`
- `battery_percent`: percent 0–100 or `null`
- `fill_percent`: computed server-side, percent 0–100 or `null`

Unknown schema versions and malformed payloads go to `rejected_telemetry_events`; readings from valid but inactive/draft bins are retained in `sensor_readings` with `eligible_for_operations=false` and cannot drive alerts, predictions or routing until activation.

## 4. Fill calculation and calibration

Backend is authoritative:
`fill_percent = clamp((empty_distance_cm - distance_cm) / (empty_distance_cm - full_distance_cm) * 100, 0, 100)`

Calibration requires finite positive values and `empty_distance_cm > full_distance_cm`. Invalid/missing/out-of-range sensor readings yield `fill_percent=null` plus a quality/fault code, not zero. Calibration is versioned. Every reading records `calibration_version`. Recalculation after a calibration correction is an audited admin action that creates a derived calculation revision; raw distance and original reading are immutable. Analytics can use the latest approved derived value while audit/history preserves prior values.

## 5. Status/config/ack messages

### Status event v1
```json
{
  "schema_version": 1,
  "device_id": "ESP32-A123",
  "boot_id": "8b7c3c82-9a9e-4c90-a4f2-9a1e2f0f4c33",
  "timestamp": "2026-10-12T10:30:00Z",
  "event": "ONLINE",
  "firmware_version": "0.1.0",
  "sensor_faults": [],
  "rssi_dbm": -61
}
```
`event`: `ONLINE`, `FAULT`, `MAINTENANCE`, `REBOOTED`. `OFFLINE` is server-inferred from MQTT Last-Will or stale telemetry, not trusted as a device-reported event. Last-Will payload uses the same schema with `event="FAULT"` and `reason_code="MQTT_UNEXPECTED_DISCONNECT"`; backend maps this to reported state `OFFLINE` and records the reason.

### Config v1 (backend → device)
```json
{
  "schema_version": 1,
  "config_version": 7,
  "issued_at": "2026-10-12T10:30:00Z",
  "sampling_interval_seconds": 60,
  "sensor_settings": {
    "distance_min_cm": 2.0,
    "distance_max_cm": 400.0,
    "weight_enabled": true,
    "environment_enabled": true
  }
}
```
Config is a device-facing operational hint; backend remains authoritative for fill calculation. Firmware applies a config only if `config_version` is newer, persists the version if possible, and publishes an ack.

### Ack v1 (device → backend)
```json
{
  "schema_version": 1,
  "device_id": "ESP32-A123",
  "config_version": 7,
  "timestamp": "2026-10-12T10:30:02Z",
  "status": "APPLIED",
  "error_code": null
}
```
`status`: `APPLIED`, `REJECTED`; `error_code` is required only for `REJECTED`.

## 6. Device health and fault codes

Allowed `sensor_faults` codes: `ULTRASONIC_TIMEOUT`, `ULTRASONIC_OUT_OF_RANGE`, `LOAD_CELL_NOT_READY`, `LOAD_CELL_CALIBRATION_MISSING`, `ENV_SENSOR_READ_FAILED`, `I2C_ERROR`, `ADC_ERROR`, `LOW_BATTERY`, `UNKNOWN_SENSOR_FAULT`.

Derived `sensor_health`: `OK` when no faults; `DEGRADED` when at least one optional sensor fault exists but distance/fill remains usable; `FAULT` when fill-critical ultrasonic data is unavailable or multiple critical acquisition failures exist. Keep reported health and derived health distinct.

## 7. Status vocabularies

- Bin registry `smart_bins.status`: `DRAFT`, `ACTIVE`, `INACTIVE`, `MAINTENANCE`, `RETIRED`.
- Device lifecycle `devices.lifecycle_state`: `UNPROVISIONED`, `PAIRED`, `ACTIVE`, `INACTIVE`, `RETIRED`.
- Device reported health `devices.reported_state`: `ONLINE`, `OFFLINE`, `FAULT`, `MAINTENANCE`.
- Current fill priority: `UNKNOWN`, `NORMAL`, `MEDIUM`, `HIGH`, `CRITICAL`.
  - `UNKNOWN`: no valid computed fill.
  - `NORMAL`: fill `< 70`.
  - `MEDIUM`: `70 <= fill <= 85`.
  - `HIGH`: `85 < fill <= 95`.
  - `CRITICAL`: `fill > 95`.
  - At exact 85%, priority is `MEDIUM`; at exact 95%, priority is `HIGH`.
- Predicted priority is a separate field: `predicted_priority` = `NONE`, `PREDICTED_HIGH`, `PREDICTED_CRITICAL`; never put predicted status into current `priority`.
- Collection job status: `PENDING`, `ASSIGNED`, `EN_ROUTE`, `ARRIVED`, `COLLECTING`, `VERIFIED`, `ANOMALY`, `CANCELLED`, `FAILED`.
- Alert severity: `INFO`, `WARNING`, `ERROR`, `CRITICAL`.
- Alert status: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`.
- Alert types: `BIN_THRESHOLD`, `DEVICE_OFFLINE`, `DEVICE_FAULT`, `PREDICTED_CRITICAL`, `AREA_HOTSPOT`, `COLLECTION_OVERDUE`, `ROUTE_FAILURE`, `TELEMETRY_REJECTED`, `SENSOR_ANOMALY`, `GPS_OUTSIDE_GEOFENCE`, `OTP_FAILURE`, `COLLECTION_ANOMALY`, `LOW_BATTERY`, `VEHICLE_OVERLOAD`, `COMMUNICATION_FAILURE`.
- Job source: `THRESHOLD`, `PREDICTION`, `MANUAL`.
- Bin type: `MUNICIPAL`, `RECYCLING`, `ORGANIC`, `HAZARDOUS`, `OTHER`.
- Vehicle type: `VAN`, `TRUCK`, `COMPACTOR`, `OTHER`.
- Route objective: `MIN_DISTANCE`, `MIN_DURATION`, `DISTANCE_WITH_PRIORITY`.
- Background task status: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.

Per-bin configured warning/critical thresholds override the default band thresholds for alert generation only; they do not change the returned standard `priority` bands. Configuration must satisfy `0 <= warning_threshold_pct < critical_threshold_pct <= 100`.

## 8. Collection state machine (per collection job / per stop)

Transitions:
1. `PENDING → ASSIGNED`: operator assigns driver and vehicle.
2. `ASSIGNED → EN_ROUTE`: driver calls `POST /api/v1/collections/{job_id}/depart`.
3. `EN_ROUTE → ARRIVED`: driver calls `/arrive`; server verifies current GPS is within the configured geofence.
4. `ARRIVED → COLLECTING`: driver requests OTP via `/otp/issue` (OTP delivered through the configured recipient/channel), then submits OTP to `/start`; server validates OTP and attempt/expiry rules.
5. `COLLECTING`: backend captures/chooses a fresh before-reading from the same bin before the pickup begins.
6. Driver calls `/finish` after physical pickup is complete. Server records `pickup_finished_at`; this starts the after-reading selection window.
7. Driver calls `/verify`; backend selects first valid after-reading captured after `pickup_finished_at` and inside the configured window, compares before/after evidence and sets `VERIFIED` or `ANOMALY`.
8. Operator may change `ANOMALY → VERIFIED` only via `/override-verification` with a non-empty reason, permission check and audit event.
9. `VERIFIED`, `CANCELLED`, and `FAILED` are terminal. `ANOMALY` is reviewable; it may be overridden to `VERIFIED` or closed as `FAILED`.

OTP issue is permitted to an assigned driver for their own job or an authorized operator. OTP is delivered to the configured recipient (e.g. registered facility contact) using a delivery provider chosen by the team. In local demo mode only, an explicit `OTP_DEMO_MODE=true` may expose OTP to an operator; never expose it to the driver in production.

Proposed defaults (team must confirm): OTP TTL 300 s; maximum 5 attempts; GPS geofence radius 100 m; before reading max age 15 min; after-reading window 15 min. A successful verification requires valid arrival + OTP + fresh before/after evidence + fill drop >= 10 percentage points OR weight drop >= max(2 kg, 10% of before weight). If evidence is unavailable or the rule fails, mark `ANOMALY`; never silently verify.

## 9. Route and assignment ownership

`routes` is the source of truth for route-level vehicle/driver assignment and ordered stops. Each route stop references one collection job; job assignment fields are derived/synchronized transactionally from the route assignment. A database/service invariant prevents route/job assignment disagreement. `POST /routes/{route_id}/assign` updates route and all linked jobs in one transaction.

Vehicle capacity is kg. If a valid weight reading is available, use it as the measured load estimate. If weight is absent, only use `estimated_load_kg = nominal_full_bin_weight_kg * fill_percent / 100` when `nominal_full_bin_weight_kg` is explicitly configured on the bin. `capacity_kg` means the bin's physical/nominal mass capacity, not vehicle capacity. If no measured or configured estimate exists, do not claim capacity-safe automatic optimization; exclude the stop from auto-optimization or require a documented operator override. `usable_vehicle_capacity_kg = vehicle.capacity_kg * capacity_safety_factor`, where factor is `(0,1]`; proposed default 0.90 reserves 10%.

## 10. Settings, runtime defaults, and locations

`system_settings` is the runtime source of truth for adjustable values. Environment variables seed defaults only on first initialization; after initialization the database value wins. Secrets, URLs, CORS, process topology and credentials remain environment-controlled. Settings updates require audit trail and validation.

Required runtime settings: `device_offline_after_seconds`, `default_geofence_radius_m`, `otp_ttl_seconds`, `otp_max_attempts`, `before_reading_max_age_seconds`, `after_reading_window_seconds`, `default_capacity_safety_factor`, default warning/critical thresholds and `sampling_interval_seconds`.

Driver location: store latest location plus append-only route-session points while a driver is actively assigned/en-route. Proposed rate limit one point every 10 seconds; retain detailed route-session points for 30 days, then delete/anonymize; retain collection verification location evidence according to project audit retention. Driver can only post their own location; operator can view active assigned routes; Super Admin can view audit/retained history.

## 11. Telemetry quarantine and activation

- Valid telemetry from `DRAFT`, `INACTIVE`, or `MAINTENANCE` bins is stored in `sensor_readings` with `eligible_for_operations=false` and `eligibility_reason` such as `BIN_NOT_ACTIVE`. It can be used for activation diagnostics only.
- Malformed payloads, unknown devices, topic/payload identity mismatch, unsupported schema version, revoked devices, and assignment conflicts are stored in `rejected_telemetry_events` with bounded/redacted payload, reason enum, topic, received timestamp, and device identifier if known. Never store credentials/secrets.
- Activation requires a recent diagnostic reading with valid distance and configured required sensors. On activation, future readings become eligible; historical diagnostic readings are not silently retroactively promoted.

## 12. API additions and naming

All business API paths below are prefixed `/api/v1`. Operational health endpoints are unprefixed.
- `GET /health/live`, `GET /health/ready`
- `GET/PATCH /api/v1/admin/settings`
- `GET/PATCH /api/v1/bins/{bin_id}/calibration`
- `GET /api/v1/drivers/{driver_id}`
- `GET/POST /api/v1/depots`, `GET/PATCH /api/v1/depots/{depot_id}`
- `POST /api/v1/drivers/{driver_id}/location`
- `POST /api/v1/collections/{job_id}/depart`, `/arrive`, `/otp/issue`, `/start`, `/finish`, `/verify`, `/override-verification`, `/cancel`
- `GET /api/v1/collections/{job_id}/evidence-status`
- `POST /api/v1/routes/{route_id}/reoptimize`
- `GET /api/v1/tasks/{task_id}` for asynchronous work; never use `job_id` for background tasks.
- `GET /api/v1/alerts/{alert_id}`, `POST /api/v1/alerts/{alert_id}/acknowledge`, `/resolve`, `/dismiss`
- `GET /api/v1/telemetry/health` for ingestion counters.

`POST /collections/{job_id}/verify` does not accept `before_reading_id`, `after_reading_id`, fill values or weight values from the client. The backend selects evidence itself. `POST /finish` marks the physical pickup-complete event and is required before selecting after-reading evidence.

## 13. API response models that must be documented/implemented

`BinSummary`, `SensorReading`, `Device`, `Calibration`, `Alert`, `Vehicle`, `Driver`, `Depot`, `Route`, `RouteStop`, `CollectionJob`, `CollectionEvidenceStatus`, `PredictionResult`, `DashboardSummary`, `SystemSettings`, `BackgroundTaskStatus`, `ApiError`.

## 14. API role rules

- `SUPER_ADMIN`: all administration, users/roles, settings, audit, calibration, fleet, route approval, manual verification override.
- `OPERATOR`: bins/areas/devices, monitoring, alerts, jobs, vehicles/drivers/depots, route optimization/assignment/approval, ordinary reports; cannot manage roles or global security settings unless explicitly granted.
- `DRIVER`: own assigned routes/jobs, depart/arrive/OTP start/finish/verify, own location updates; cannot view arbitrary bins/users, change settings, assign routes, or override verification.

## 15. Rejected telemetry reason codes

`INVALID_JSON`, `SCHEMA_VALIDATION_FAILED`, `UNSUPPORTED_SCHEMA_VERSION`, `UNKNOWN_DEVICE`, `REVOKED_DEVICE`, `TOPIC_DEVICE_MISMATCH`, `ASSIGNMENT_CONFLICT`, `INVALID_TIMESTAMP`, `INVALID_MEASUREMENT`, `DUPLICATE_MESSAGE`, `UNAUTHORIZED_TOPIC`.

`timestamp_quality`: `DEVICE_SYNCED`, `SERVER_RECEIVED_FALLBACK`.

## 16. Environment variable names and precedence

Use these names consistently: `DATABASE_URL`, `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_CA_CERT_PATH`, `MQTT_CLIENT_ID`, `MQTT_TELEMETRY_TOPIC_TEMPLATE`, `MQTT_STATUS_TOPIC_TEMPLATE`, `MQTT_CONFIG_TOPIC_TEMPLATE`, `MQTT_ACK_TOPIC_TEMPLATE`, `FIREBASE_PROJECT_ID`, `CORS_ALLOWED_ORIGINS`, `OSRM_BASE_URL`, `OTP_DEMO_MODE`, `LOG_LEVEL`. Runtime settings listed in §10 may also have `DEFAULT_*` seed variables, but DB values win after first initialization. Do not use both `MQTT_HOST` and `MQTT_BROKER_HOST`.

## 17. Worker model

MQTT consumer is a separate supervised process/container from Uvicorn API workers. Plain MQTT has no Kafka-style consumer groups. Prototype: one worker; horizontal scaling only with MQTT 5 shared subscriptions where supported plus database idempotency. Background optimization/training use a task queue and `task_id`. Use one home for asynchronous jobs under `backend/app/jobs/`; MQTT worker entry point may live under `backend/app/workers/` but must not duplicate generic task logic.

## 18. Proposed defaults needing team sign-off

Sampling interval 60 s; offline timeout 180 s; geofence 100 m; OTP TTL 300 s; OTP max attempts 5; before reading max age 900 s; after-reading window 900 s; capacity safety factor 0.90; verification fill reduction 10 percentage points; verification weight reduction `max(2 kg, 10%)`. These are prototype defaults, not validated operational guarantees.
