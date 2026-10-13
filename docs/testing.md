# SWM-ICS Test Plan

## 1. Contract tests

- Validate all example telemetry/status/config/ack messages against `schemas/*.schema.json` with JSON Schema Draft 2020-12 format checker enabled.
- Assert `message_id == device_id + ":" + boot_id + ":" + sequence`.
- `time_synced=true` requires non-null UTC `Z` timestamp; false requires timestamp null.
- Unknown fields rejected (`additionalProperties=false`).
- Device IDs containing `/`, `+`, `#`, spaces rejected.
- Ensure payload has no `bin_id` and no authoritative `fill_percent`.

## 2. MQTT and ingestion

- Valid telemetry resolves bin via active assignment, calculates fill server-side and persists.
- Duplicate `(device_id, boot_id, sequence)` is idempotent.
- Device reboot with a new boot_id and sequence 0 is accepted.
- Topic/payload device mismatch, unknown/revoked device, assignment conflict and unsupported schema version are quarantined with reason code.
- Draft/inactive/maintenance readings persist with `eligible_for_operations=false`, do not affect latest operational state or create alerts/jobs.
- Timestamp fallback uses `received_at`, `timestamp_quality=SERVER_RECEIVED_FALLBACK`.
- MQTT worker starts once independently of number of Uvicorn workers.
- Last-Will maps to OFFLINE; valid new telemetry restores online status.

## 3. Fill and priority boundaries

Fill formula test with `empty=100 cm`, `full=10 cm`: distance 100→0%, 55→50%, 10→100%; clamp values outside endpoints. Invalid calibration or distance gives null and quality flag.

Priority boundaries:
- null → UNKNOWN
- 69.99 → NORMAL
- 70 → MEDIUM
- 85 → MEDIUM
- 85.01 → HIGH
- 95 → HIGH
- 95.01 → CRITICAL

Per-bin warning/critical thresholds alter alert generation, not standard priority enum.

## 4. API and authorization

- Every endpoint validates role and resource assignment.
- Driver cannot access another driver's job or arbitrary users/bins.
- `409` on invalid transition, conflicting assignment, stale state and idempotency key reused with changed body.
- `422` on invalid field/unit/range; null numeric fields accepted only where schema allows.
- OTP expiry/attempt/rate limits enforced; production response never contains OTP.
- `/verify` rejects/ignores any attempted client reading IDs or sensor values.
- `/override-verification` only permits authorized operator/admin with non-empty reason and audit record.
- Route assignment updates route and linked jobs transactionally.
- Async endpoints return task_id and poll returns complete status enum.

## 5. Collection state machine

Valid sequence: PENDING → ASSIGNED → EN_ROUTE (`depart`) → ARRIVED (`arrive`) → COLLECTING (`start`) → finish event → verify → VERIFIED or ANOMALY.
Test out-of-order requests, unauthorized driver, outside geofence, invalid/expired OTP, missing before reading, no post-finish reading, stale after reading, failed reduction threshold, and operator override. Ensure after-reading timestamp is strictly after `pickup_finished_at`.

## 6. Route optimization

- Valid OSRM matrix + feasible capacities produces draft route.
- OSRM timeout, invalid coordinates, incomplete matrix, no candidates and infeasible capacity produce structured FAILED task, no fake route.
- Missing weight and nominal full-bin estimate excludes candidate from automatic capacity-constrained solve or requires documented override.
- Route assignment persists route driver/vehicle and linked job assignment consistently.

## 7. Frontend/E2E

- Null values render “Unavailable”, not 0.
- API errors 400/401/403/404/409/422/429/5xx show distinct UX.
- Role navigation matches server authorization.
- Driver buttons follow current state only and disable during requests.
- Async task polling ends for success/failure/cancel.
- WCAG AA contrast and keyboard navigation checked.
- End-to-end prototype: one bin/device → telemetry → dashboard → alert/candidate → route → driver depart/arrive/OTP/start/finish → fresh after reading → verification outcome and audit.
