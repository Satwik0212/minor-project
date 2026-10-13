# SWM-ICS Features, Algorithms and Acceptance Criteria

## 1. Feature priorities

- **P0:** device/bin registry, MQTT telemetry, backend fill calculation, dashboard/live map, alerts, collection candidates, vehicle/driver/depot registry, route optimization, driver workflow, auditable verification.
- **P1:** area/trend analytics, hotspot detection, ML prediction, advanced reports and model lifecycle.
- **P2:** optional environmental/low-battery enhancements, richer audit/report exports and future integrations.

## 2. Bin and device registry

Features: create/edit/retire bins; map location; assign area/type/capacity; pair device; version calibration; activate/deactivate; replace device without changing bin identity.

Constraints:
- `bin_id` and `device_id` are separate.
- A bin has at most one active device assignment; a device has at most one active bin assignment.
- Activation requires a recent valid diagnostic reading.
- Telemetry for DRAFT/INACTIVE/MAINTENANCE is stored with `eligible_for_operations=false`, excluded from live analytics and routing.
- Replacement revokes old ACL/credentials and audits actor/reason.

## 3. Sensor ingestion and fill calculation

ESP32 publishes raw measurements to MQTT/TLS using `schemas/mqtt-telemetry-v1.schema.json`. Backend worker validates topic/payload identity, schema, assignment and deduplication key `(device_id, boot_id, sequence)`. It stores raw values, event/received timestamps, calibration version and quality flags.

Authoritative formula:
`fill_percent = clamp((empty_distance_cm - distance_cm) / (empty_distance_cm - full_distance_cm) * 100, 0, 100)`

Require `empty_distance_cm > full_distance_cm > 0`. Invalid/missing distance means `fill_percent=null`, never zero. Raw readings are append-only. Calibration changes create new versions; recalculation is audited.

## 4. Device health and offline detection

Health fields: lifecycle state, reported state, derived sensor health, last seen, RSSI, battery if present, firmware version and fault codes. Sensor health:
- `OK`: no faults.
- `DEGRADED`: optional sensor fails but fill-critical measurement works.
- `FAULT`: fill-critical distance unavailable or acquisition is unusable.

Device offline is inferred from MQTT Last-Will or last telemetry older than `device_offline_after_seconds`. Create/update one open `DEVICE_OFFLINE` alert idempotently; resolve when device resumes.

## 5. Priority and alert logic

Current fill priority:
- `UNKNOWN`: no valid fill.
- `NORMAL`: `<70%`.
- `MEDIUM`: `70–85%` inclusive.
- `HIGH`: `>85–95%` inclusive.
- `CRITICAL`: `>95%`.

At exactly 85%, MEDIUM; at exactly 95%, HIGH. `predicted_priority` is separate (`NONE`, `PREDICTED_HIGH`, `PREDICTED_CRITICAL`).

Per-bin warning/critical thresholds govern alert generation and must satisfy `0 <= warning < critical <= 100`; they do not change the standard current-priority bands. Alert severity: INFO/WARNING/ERROR/CRITICAL. Alert types include threshold, device offline/fault, predicted critical, hotspot, overdue collection, route failure, telemetry rejected, sensor anomaly, geofence failure, OTP failure, collection anomaly, low battery, vehicle overload and communication failure.

## 6. Analytics and hotspots

- Area analytics: group eligible current states by area; compute counts, mean/median fill, priority counts and stale-device count.
- Trends: aggregate eligible readings into time buckets; use event time and preserve gaps rather than treating missing readings as zero.
- Hotspots: use PostGIS spatial clustering or a documented grid/DBSCAN approach on high-priority bins; expose algorithm, radius/min-points configuration and cluster timestamp.
- Do not claim statistically meaningful hotspot results from only three prototype bins.

## 7. Collection candidate generation

Threshold/prediction crossing creates or updates an idempotent candidate in `PENDING`; it does not auto-dispatch a vehicle. Source is `THRESHOLD`, `PREDICTION`, or `MANUAL`. Repeated telemetry for the same bin/rule/window must not duplicate candidates. Operator assigns/approves route. Candidate generation should retain reason and source reading/prediction.

## 8. Vehicle capacity and load estimation

Vehicle capacity is kg. If weight sensor reading is valid, use measured `weight_kg`. Otherwise, use `estimated_load_kg = nominal_full_bin_weight_kg * fill_percent / 100` only when that nominal value is explicitly configured. Bin `capacity_kg` is not vehicle capacity and must not be treated as the nominal full waste mass unless explicitly defined by a configuration mapping. If no defensible estimate exists, exclude the stop from capacity-constrained optimization or require a reasoned operator override.

Usable capacity: `vehicle.capacity_kg * capacity_safety_factor`; factor is in `(0,1]`, proposed default `0.90`.

## 9. Route optimization

Inputs: candidate jobs, eligible bins/locations, vehicle capacities and availability, depot, objective, load estimate provenance, and optional time windows/priorities. OSRM provides road distance/duration matrix; OR-Tools solves CVRP/VRP with capacity constraints and objective.

Objective options: `MIN_DISTANCE`, `MIN_DURATION`, `DISTANCE_WITH_PRIORITY`. Route optimization is asynchronous: API returns `202` with `task_id`; frontend polls `/api/v1/tasks/{task_id}`. Persist a draft route only for a feasible solution. Handle OSRM unavailable, incomplete matrix, invalid coordinates and infeasible capacity as structured task failures; never fabricate route distances.

Route is source of truth for vehicle/driver assignment and stop order. Assign route + linked jobs transactionally. Admin approves route before dispatch.

## 10. Driver workflow and state machine

`PENDING → ASSIGNED → EN_ROUTE → ARRIVED → COLLECTING → VERIFIED` or `ANOMALY`.
- `/depart`: assigned driver acknowledges departure.
- `/arrive`: backend checks GPS/geofence.
- `/otp/issue`: OTP sent to configured facility contact.
- `/start`: validates OTP and captures before evidence.
- `/finish`: records physical pickup finished time/location.
- `/verify`: backend selects a new post-finish reading and evaluates evidence.
- `/override-verification`: operator may change ANOMALY to VERIFIED with reason and audit.
- Cancellation/failure require authorized actor and reason. VERIFIED/CANCELLED/FAILED are terminal.

## 11. Collection verification algorithm

Before reading: latest valid eligible reading for same bin/device assignment no older than configured `before_reading_max_age_seconds` when collection starts.

After reading: first valid eligible reading for same bin/device assignment after `pickup_finished_at` and within `after_reading_window_seconds`.

Proposed pass criteria: valid arrival/geofence + valid OTP + fresh before/after readings + fill reduction >= 10 percentage points OR weight reduction >= max(2 kg, 10% of before weight). If evidence is missing or both reductions fail, state `ANOMALY` with reason codes. Thresholds require real sensor validation. Driver cannot submit reading IDs or measurement values.

## 12. OTP and geofence

OTP TTL proposed 300 seconds; maximum 5 attempts; issue rate-limited and audited. Production OTP delivered to registered facility contact; never returned to driver. Demo-only exposure requires `OTP_DEMO_MODE=true` and must not be enabled in production. Geofence proposed radius 100 m; compare reported GPS coordinate with bin point using geodesic distance and record accuracy/captured time.

## 13. ML prediction

Data pipeline: select quality-filtered eligible readings; resample by bin/time; create lag/rolling features; split chronologically to avoid leakage; train XGBoost to forecast fill at a stated horizon; compare against simple persistence baseline; store metrics and model version. Gate prediction if data coverage or validation quality is insufficient. Predictions return status `NOT_AVAILABLE` rather than made-up values. A three-bin short demo validates integration, not accuracy.

## 14. Reports, audit and settings

Reports: collection history, route distance/duration, vehicle usage, bin overflow incidents, device uptime and alert resolution. Audit every settings change, calibration change, assignment/replacement, route approval, cancellation, verification override and role change.

Runtime settings live in DB `system_settings`; environment defaults seed them once. Database values win after initialization. Settings have unit, bounds, updated_by/time and audit diff.

## 15. Acceptance criteria

- Repeated MQTT delivery produces one reading and no duplicate alert/job side effect.
- A reboot with new `boot_id` and reset sequence accepts new messages.
- Fill formula and exact priority boundaries match integration contract.
- Invalid sensor reading yields null fill, not 0%.
- Draft/inactive readings are stored but excluded from operational analytics.
- OSRM failure and infeasible capacity return explicit failed task.
- Every collection transition rejects out-of-order/unauthorized calls with 409/403.
- Driver cannot forge reading IDs/values to mark collection verified.
- Anomaly override requires reason and audit record.
- API/UI/firmware schema tests use the same JSON Schemas.
