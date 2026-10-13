# SWM-ICS REST API Specification

## 1. Conventions

Base path: `/api/v1`; `/health/live` and `/health/ready` are unprefixed operational endpoints. JSON keys use `snake_case`. Auth: `Authorization: Bearer <Firebase ID token>`. Times are UTC ISO-8601 `Z`. Lists return `{"items":[...],"next_cursor":null}`. Mutating operations use `Idempotency-Key` where indicated.

Error envelope:
```json
{"error":{"code":"VALIDATION_ERROR","message":"Readable explanation","details":{},"request_id":"req_123"}}
```
Handle `400`, `401`, `403`, `404`, `409`, `422`, `429`, and `5xx`.

## 2. Roles

- `SUPER_ADMIN`: users/roles, audit, global settings, all operations.
- `OPERATOR`: operational bins/devices, monitoring, alerts, fleet, routes, jobs, reports; no role administration.
- `DRIVER`: only own assigned routes/jobs and location/collection transitions.

## 3. Canonical enums

Bin: `DRAFT`, `ACTIVE`, `INACTIVE`, `MAINTENANCE`, `RETIRED`.
Device lifecycle: `UNPROVISIONED`, `PAIRED`, `ACTIVE`, `INACTIVE`, `RETIRED`.
Device reported state: `ONLINE`, `OFFLINE`, `FAULT`, `MAINTENANCE`.
Current priority: `UNKNOWN`, `NORMAL`, `MEDIUM`, `HIGH`, `CRITICAL`; predicted priority is separate: `NONE`, `PREDICTED_HIGH`, `PREDICTED_CRITICAL`.
Collection job: `PENDING`, `ASSIGNED`, `EN_ROUTE`, `ARRIVED`, `COLLECTING`, `VERIFIED`, `ANOMALY`, `CANCELLED`, `FAILED`.
Alert severity: `INFO`, `WARNING`, `ERROR`, `CRITICAL`; alert status: `OPEN`, `ACKNOWLEDGED`, `RESOLVED`, `DISMISSED`.
Alert type: `BIN_THRESHOLD`, `DEVICE_OFFLINE`, `DEVICE_FAULT`, `PREDICTED_CRITICAL`, `AREA_HOTSPOT`, `COLLECTION_OVERDUE`, `ROUTE_FAILURE`, `TELEMETRY_REJECTED`, `SENSOR_ANOMALY`, `GPS_OUTSIDE_GEOFENCE`, `OTP_FAILURE`, `COLLECTION_ANOMALY`, `LOW_BATTERY`, `VEHICLE_OVERLOAD`, `COMMUNICATION_FAILURE`.
Bin type: `MUNICIPAL`, `RECYCLING`, `ORGANIC`, `HAZARDOUS`, `OTHER`; vehicle type: `VAN`, `TRUCK`, `COMPACTOR`, `OTHER`; job source: `THRESHOLD`, `PREDICTION`, `MANUAL`; route objective: `MIN_DISTANCE`, `MIN_DURATION`, `DISTANCE_WITH_PRIORITY`; task status: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELLED`.

Priority bands: `UNKNOWN` when fill unavailable; `NORMAL <70`; `MEDIUM 70–85 inclusive`; `HIGH >85–95 inclusive`; `CRITICAL >95`. At exactly 85, `MEDIUM`; at exactly 95, `HIGH`.

## 4. Authentication and health

| Method | Path | Function | Access |
|---|---|---|---|
| GET | `/health/live` | Process liveness | Public/internal |
| GET | `/health/ready` | DB and required dependency readiness | Public/internal |
| POST | `/api/v1/auth/session` | Exchange verified Firebase identity for app profile/roles | Authenticated |
| GET | `/api/v1/auth/me` | Current local user and permissions | Authenticated |
| POST | `/api/v1/auth/logout` | Client session/logout audit if applicable | Authenticated |

## 5. Dashboard, bins and devices

| Method | Path | Function |
|---|---|---|
| GET | `/api/v1/dashboard/summary` | Counts, critical bins, active routes, open alerts |
| GET/POST | `/api/v1/bins` | List/create bins |
| GET/PATCH | `/api/v1/bins/{bin_id}` | Detail/update metadata |
| POST | `/api/v1/bins/{bin_id}/activate` | Validate diagnostic reading and activate |
| POST | `/api/v1/bins/{bin_id}/deactivate` | Deactivate with reason |
| GET/PATCH | `/api/v1/bins/{bin_id}/calibration` | Get/update versioned geometry calibration |
| GET/POST | `/api/v1/devices` | List/register device |
| GET/PATCH | `/api/v1/devices/{device_id}` | Device detail/update registry |
| POST | `/api/v1/devices/{device_id}/pair` | Pair device with physical bin |
| POST | `/api/v1/devices/{device_id}/replace` | Revoke/close old assignment and replace safely |
| GET | `/api/v1/devices/{device_id}/health` | Health, last seen, sensor faults |

## 6. Readings, analytics, predictions

| Method | Path | Function |
|---|---|---|
| GET | `/api/v1/readings/latest` | Latest state for eligible bins |
| GET | `/api/v1/readings` | Historical readings; filters: bin_id, from, to, cursor |
| GET | `/api/v1/readings/{bin_id}` | Historical readings for one bin |
| GET | `/api/v1/telemetry/health` | Accepted, duplicate, rejected and quarantined counters |
| GET | `/api/v1/analytics/areas` | Area-wise rollups |
| GET | `/api/v1/analytics/bins` | Bin status/priority distribution |
| GET | `/api/v1/analytics/hotspots` | Spatially clustered high-priority bins |
| GET | `/api/v1/analytics/trends` | Fill/weight trends over time |
| GET | `/api/v1/predictions` | Prediction availability and latest results |
| GET | `/api/v1/predictions/{bin_id}` | Forecast for one bin |
| POST | `/api/v1/predictions/train` | Enqueue training; returns `202 {task_id}` |

Readings response uses `distance_cm` (cm), `fill_percent` (percent or null), `weight_kg` (kg or null), `temperature_c` (°C or null), `humidity_percent` (% RH or null), `timestamp`, `received_at`, `sensor_health`, `priority`, `predicted_priority`, `quality_flags`.

## 7. Areas, alerts and settings

| Method | Path | Function | Access |
|---|---|---|---|
| GET/POST | `/api/v1/areas` | List/create service areas | Operator+ |
| GET/PATCH | `/api/v1/areas/{area_id}` | Area detail/update | Operator+ |
| GET | `/api/v1/alerts` | Filter/list alerts | Operator+ |
| GET | `/api/v1/alerts/{alert_id}` | Alert detail | Operator+ |
| POST | `/api/v1/alerts/{alert_id}/acknowledge` | Acknowledge alert | Operator+ |
| POST | `/api/v1/alerts/{alert_id}/resolve` | Resolve with note | Operator+ |
| POST | `/api/v1/alerts/{alert_id}/dismiss` | Dismiss with reason | Operator+ |
| GET | `/api/v1/admin/settings` | Read runtime settings | Super Admin; selected safe values Operator |
| PATCH | `/api/v1/admin/settings` | Update validated settings + audit | Super Admin |

## 8. Vehicles, drivers, depots

| Method | Path | Function |
|---|---|---|
| GET/POST | `/api/v1/vehicles` | List/register vehicle |
| GET/PATCH | `/api/v1/vehicles/{vehicle_id}` | Vehicle detail/update |
| GET/POST | `/api/v1/drivers` | List/register driver |
| GET/PATCH | `/api/v1/drivers/{driver_id}` | Driver detail/update |
| POST | `/api/v1/drivers/{driver_id}/location` | Own driver's latest location/route point; role and assignment checked |
| GET/POST | `/api/v1/depots` | List/create depot |
| GET/PATCH | `/api/v1/depots/{depot_id}` | Depot detail/update |

`capacity_kg` on a vehicle is vehicle waste payload capacity. `capacity_kg` on a bin is the bin's physical/nominal mass capacity. `nominal_full_bin_weight_kg` is a separate optional estimate for routing when no weight sensor is available.

## 9. Collection jobs and verification

| Method | Path | Function |
|---|---|---|
| GET/POST | `/api/v1/collections` | List/create collection candidates |
| POST | `/api/v1/collections/generate` | Generate idempotent candidates from threshold/prediction/manual criteria |
| GET | `/api/v1/collections/{job_id}` | Job detail |
| POST | `/api/v1/collections/{job_id}/assign` | Assign to route or candidate dispatch |
| POST | `/api/v1/collections/{job_id}/cancel` | Cancel with required reason |
| POST | `/api/v1/collections/{job_id}/depart` | `ASSIGNED → EN_ROUTE` |
| POST | `/api/v1/collections/{job_id}/arrive` | Validate GPS/geofence; `EN_ROUTE → ARRIVED` |
| POST | `/api/v1/collections/{job_id}/otp/issue` | Send OTP to configured facility contact |
| POST | `/api/v1/collections/{job_id}/start` | Validate OTP; `ARRIVED → COLLECTING`; capture before evidence |
| GET | `/api/v1/collections/{job_id}/evidence-status` | Freshness/readiness of before/after readings |
| POST | `/api/v1/collections/{job_id}/finish` | Record physical pickup finished time and location |
| POST | `/api/v1/collections/{job_id}/verify` | Backend selects after-reading and sets `VERIFIED` or `ANOMALY` |
| POST | `/api/v1/collections/{job_id}/override-verification` | Operator changes `ANOMALY → VERIFIED` with reason/audit |

`/verify` request may contain `{ "latitude": 22.7196, "longitude": 75.8577, "captured_at": "2026-10-12T10:45:00Z" }`; it must not contain reading IDs or sensor values. Coordinates are decimal degrees. Backend selects evidence by job/bin/device assignment and timestamps. OTP is never returned to the driver in production.

## 10. Routes and asynchronous tasks

| Method | Path | Function |
|---|---|---|
| GET/POST | `/api/v1/routes` | List/create draft routes |
| GET | `/api/v1/routes/{route_id}` | Route detail/stops |
| POST | `/api/v1/routes/optimize` | Enqueue optimization; `202 {task_id}` |
| POST | `/api/v1/routes/{route_id}/reoptimize` | Enqueue re-optimization with reason |
| POST | `/api/v1/routes/{route_id}/assign` | Transactionally assign route + linked jobs |
| POST | `/api/v1/routes/{route_id}/approve` | Approve route |
| GET | `/api/v1/tasks/{task_id}` | Poll task state/progress/result |
| GET | `/api/v1/reports/collections` | Collection history/report |
| GET | `/api/v1/reports/vehicle-usage` | Fleet usage report |
| GET | `/api/v1/audit` | Audit search (Super Admin) |

Optimization request example:
```json
{
  "candidate_job_ids": ["JOB-001", "JOB-002"],
  "vehicle_ids": ["VEH-001"],
  "depot_id": "DEP-001",
  "objective": "DISTANCE_WITH_PRIORITY"
}
```
Task response: `{"task_id":"TASK-001","status":"QUEUED","status_url":"/api/v1/tasks/TASK-001"}`. Poll until `SUCCEEDED`, `FAILED`, or `CANCELLED`. If OSRM fails or no feasible capacity solution exists, task is `FAILED` with structured reason; do not fabricate a route.

## 11. Schemas and examples

Use `docs/schemas/*.schema.json` for MQTT. REST schemas should be implemented as Pydantic models and mirrored by frontend TypeScript/JSDoc types. Keep nullable numeric values explicitly `number | null`. The backend response must include `request_id` for traceability and must never expose raw secrets, OTP hashes, or rejected raw credentials.

## 12. Idempotency, concurrency and validation

- Idempotency header required for: create collection candidate, optimize route, train model, assign route, issue OTP, transition actions and override.
- Return `409` for invalid state transitions, conflicting assignment, stale config version, duplicate idempotency key with changed body.
- Return `422` for valid JSON with invalid schema/field values.
- Rate-limit OTP issue/attempts and driver location.
- All state transitions run in DB transactions and append audit events.
