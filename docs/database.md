# SWM-ICS Database Design

## 1. Conventions

PostgreSQL + PostGIS. Use UUID internal primary keys plus stable public IDs (`BIN-001`, `ESP32-A123`, etc.). UTC `TIMESTAMPTZ`. Geometry uses SRID 4326. Never use nullable measurements as zero. All tables include `created_at`; mutable registry tables also include `updated_at`.

## 2. Required tables

### `users`
`id UUID PK`, `firebase_uid TEXT UNIQUE NOT NULL`, `email CITEXT UNIQUE`, `display_name TEXT`, `role ENUM(SUPER_ADMIN,OPERATOR,DRIVER)`, `active BOOLEAN`, timestamps.

### `areas`
`id UUID PK`, `area_id TEXT UNIQUE`, `name TEXT`, `boundary GEOMETRY(MULTIPOLYGON,4326)`, `active BOOLEAN`.

### `smart_bins`
`id UUID PK`, `bin_id TEXT UNIQUE`, `name TEXT`, `bin_type`, `status`, `location GEOGRAPHY(POINT,4326)`, `area_id FK`, `capacity_kg NUMERIC CHECK >=0` (physical/nominal bin mass capacity), `nominal_full_bin_weight_kg NUMERIC NULL CHECK >=0` (optional full-bin estimated waste mass for routing), `warning_threshold_pct NUMERIC`, `critical_threshold_pct NUMERIC`, `created_at`, `updated_at`. Check thresholds are in [0,100] and warning < critical.

### `devices`
`id UUID PK`, `device_id TEXT UNIQUE`, `lifecycle_state`, `reported_state`, `firmware_version`, `last_seen_at`, `last_rssi_dbm`, `sensor_health ENUM(OK,DEGRADED,FAULT)`, `credential_ref` (secret reference only, never credential), timestamps.

### `device_bin_assignments`
`id UUID PK`, `device_id FK`, `bin_id FK`, `started_at TIMESTAMPTZ`, `ended_at TIMESTAMPTZ NULL`, `assigned_by FK users`, `reason TEXT`; only one active assignment per device and only one active device per bin (partial unique indexes).

### `sensor_configurations`
`id UUID PK`, `bin_id FK`, `calibration_version INTEGER`, `empty_distance_cm NUMERIC`, `full_distance_cm NUMERIC`, `sampling_interval_seconds INTEGER`, `effective_at`, `created_by FK`, `reason`; unique `(bin_id, calibration_version)`. Validate `empty_distance_cm > full_distance_cm > 0`.

### `sensor_readings`
`id UUID PK`, `bin_id FK`, `device_id FK`, `timestamp TIMESTAMPTZ` (effective event time), `received_at TIMESTAMPTZ NOT NULL`, `timestamp_quality ENUM(DEVICE_SYNCED,SERVER_RECEIVED_FALLBACK)`, `boot_id UUID`, `sequence BIGINT`, `message_id TEXT`, `calibration_version INTEGER NULL`, `distance_cm NUMERIC NULL`, `fill_percent NUMERIC NULL`, `weight_kg NUMERIC NULL`, `raw_hx711_count BIGINT NULL`, `temperature_c NUMERIC NULL`, `humidity_percent NUMERIC NULL`, `rssi_dbm INTEGER NULL`, `battery_percent NUMERIC NULL`, `sensor_health ENUM(OK,DEGRADED,FAULT)`, `sensor_faults TEXT[]`, `quality_flags TEXT[]`, `eligible_for_operations BOOLEAN`, `eligibility_reason TEXT NULL`, `created_at`. Unique `(device_id, boot_id, sequence)`. Check units/ranges. Partition by time only if scale warrants it.

### `bin_latest_state`
One row per bin: `bin_id PK/FK`, `latest_reading_id FK`, `latest_event_at`, `fill_percent`, `weight_kg`, `priority`, `predicted_priority`, `sensor_health`, `device_reported_state`, `is_stale`, `updated_at`. Upsert transactionally from eligible readings.

### `vehicles`, `drivers`, `depots`
Vehicles: `id`, `vehicle_id UNIQUE`, `vehicle_type`, `capacity_kg`, `status`, optional registration. Drivers: `id`, `driver_id UNIQUE`, `user_id UNIQUE FK`, `license_no`, `status`. Depots: `id`, `depot_id UNIQUE`, `name`, `location GEOGRAPHY(POINT,4326)`, active status.

### `collection_jobs`
`id UUID PK`, `job_id TEXT UNIQUE`, `bin_id FK`, `source ENUM(THRESHOLD,PREDICTION,MANUAL)`, `status`, `priority`, `route_stop_id FK NULL`, `created_at`, `assigned_at`, `en_route_at`, `arrived_at`, `collecting_started_at`, `pickup_finished_at`, `verified_at`, `cancelled_at`, `failure_reason`, `created_by FK NULL`. Route assignment is canonical; do not independently store conflicting vehicle/driver values here. Unique active candidate per bin/source/window enforced via partial unique index or service transaction.

### `routes`, `route_stops`
Routes: `id`, `route_id UNIQUE`, `depot_id FK`, `vehicle_id FK NULL`, `driver_id FK NULL`, `status`, `objective`, `distance_m`, `duration_s`, `capacity_safety_factor`, `approved_by FK NULL`, timestamps. Route is source of truth for assignment.
Stops: `id`, `route_id FK`, `collection_job_id FK UNIQUE`, `bin_id FK`, `sequence_no`, `planned_arrival_at`, `actual_arrival_at`, `distance_from_previous_m`, unique `(route_id, sequence_no)`.

### `collection_verifications`
`id UUID PK`, `job_id FK UNIQUE`, `before_reading_id FK`, `after_reading_id FK`, `otp_verified_at`, `arrival_lat/lon`, `finish_lat/lon`, `verify_lat/lon`, `fill_before_pct`, `fill_after_pct`, `weight_before_kg`, `weight_after_kg`, `outcome ENUM(VERIFIED,ANOMALY)`, `reason_codes TEXT[]`, `override_reason NULL`, `overridden_by FK NULL`, timestamps. Reading IDs are chosen by backend only.

### `alerts`
`id UUID PK`, `alert_id TEXT UNIQUE`, `type`, `severity`, `status`, `bin_id FK NULL`, `device_id FK NULL`, `job_id FK NULL`, `message TEXT`, `details JSONB`, `opened_at`, `acknowledged_by FK NULL`, `resolved_by FK NULL`, `resolved_at`, timestamps.

### `predictions`, `model_registry`
Predictions: `id`, `bin_id FK`, `model_version`, `generated_at`, `horizon_minutes`, `predicted_fill_percent`, `predicted_priority`, `confidence NUMERIC NULL`, `status`. Model registry: `model_version UNIQUE`, `algorithm`, `trained_at`, `data_start`, `data_end`, `metrics JSONB`, `artifact_uri`, `status`.

### `system_settings`
`key TEXT PK`, `value JSONB`, `unit TEXT`, `validation JSONB`, `updated_by FK`, `updated_at`. Changes create audit entries. Environment defaults seed values once; DB value wins after initialization.

### `background_jobs`
`id UUID PK`, `task_id TEXT UNIQUE`, `task_type`, `status ENUM(QUEUED,RUNNING,SUCCEEDED,FAILED,CANCELLED)`, `progress NUMERIC`, `result_ref JSONB`, `error_code`, `error_message`, `created_by FK`, timestamps.

### `idempotency_keys`
`id UUID PK`, `actor_id FK`, `key TEXT`, `request_hash TEXT`, `response_status INTEGER`, `response_body JSONB`, `expires_at`, unique `(actor_id,key)`.

### `rejected_telemetry_events`
`id UUID PK`, `device_id TEXT NULL`, `topic TEXT`, `reason_code`, `received_at`, `payload_redacted JSONB NULL`, `request_trace_id TEXT NULL`. Never persist credentials or secrets.

### `driver_location_points`
`id UUID PK`, `driver_id FK`, `route_id FK NULL`, `location GEOGRAPHY(POINT,4326)`, `captured_at`, `received_at`, `source`, `created_at`. Rate limit; retain detailed route points 30 days as proposed default. Collection verification locations follow audit retention policy.

### `audit_logs`
`id UUID PK`, `actor_id FK NULL`, `action`, `entity_type`, `entity_id`, `reason TEXT NULL`, `before_diff JSONB NULL`, `after_diff JSONB NULL`, `created_at`, `request_id`.

## 3. Indexes and invariants

- Unique public IDs; unique `(device_id, boot_id, sequence)`.
- GIST indexes on area boundaries and bin/vehicle/depot/location points.
- B-tree `(bin_id, timestamp DESC)`, `(device_id, timestamp DESC)`, `(status, priority)`, `(route_id, sequence_no)`.
- Partial unique active assignment indexes for device↔bin mapping.
- State transitions and route assignment changes run transactionally.
- Raw sensor readings are append-only; calibration recompute creates an auditable derived revision rather than rewriting the raw message.
- Every alert/job side effect is idempotent per source reading/rule/window.
