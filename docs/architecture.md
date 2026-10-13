# SWM-ICS System Architecture

## 1. Main boundaries

```text
ESP32 + Sensors
  └─ MQTT/TLS JSON → MQTT Broker (ACL)
       └─ Separate supervised MQTT Worker
            ├─ Validate topic identity + JSON schema
            ├─ Resolve device→bin assignment
            ├─ Deduplicate (device_id, boot_id, sequence)
            ├─ Load calibration; compute fill_percent
            ├─ Persist sensor_readings + bin_latest_state
            └─ Trigger idempotent alerts/candidates
Browser (HTML/CSS/JS/Tailwind + Leaflet)
  └─ HTTPS REST/JSON → FastAPI API workers
       ├─ Auth (Firebase ID token → local role)
       ├─ Pydantic validation
       ├─ Service layer / domain state machines
       ├─ PostgreSQL + PostGIS via SQLAlchemy
       └─ Background task queue → optimization/training workers
             ├─ OSRM road matrix
             ├─ OR-Tools route optimization
             └─ XGBoost prediction pipeline
```

MQTT worker and FastAPI API workers are separate processes. Do not start MQTT subscriptions in FastAPI lifespan when deploying multiple Uvicorn workers.

## 2. Data ingestion flow

1. ESP32 publishes telemetry to `smartwaste/device/{device_id}/telemetry` over TLS.
2. Broker checks ACL and forwards to the MQTT worker.
3. Worker validates payload schema/version and topic `device_id`.
4. Worker resolves active device/bin assignment from DB; device cannot choose its own bin.
5. Worker deduplicates `(device_id, boot_id, sequence)`.
6. Worker reads calibration version, computes fill, validates measurements and records event/received timestamps.
7. Worker appends sensor reading and updates latest-state projection.
8. Ineligible bin readings are retained for diagnostics but do not trigger normal operations.
9. Alert/candidate rules execute idempotently.

## 3. Browser/API flow

Frontend calls FastAPI over HTTPS. It never directly accesses the database, MQTT broker, or service credentials. FastAPI authenticates the Firebase ID token, checks role and resource assignment, validates request schemas, calls service methods, commits transactions and returns stable response models.

## 4. Feature modules

- Registry: users, areas, bins, devices, device assignments, calibration.
- Monitoring: latest readings, health, stale/offline detection, alert rules.
- Analytics: area/bin/trend summaries and spatial hotspots.
- Prediction: data sufficiency checks, training tasks, model registry, forecast.
- Fleet: vehicles, drivers, depots, availability/capacity.
- Collection: candidates, assignment, per-stop state machine, OTP, evidence, override.
- Routing: OSRM matrix, OR-Tools, draft routes, approval and assignment.
- Reporting/audit: collection history, vehicle usage, immutable event trail.

## 5. Route optimization

Admin sends candidate job IDs, vehicle IDs, depot and objective. API validates then returns `202 Accepted` with `task_id`. Background task fetches candidate locations and credible load estimates, obtains OSRM road distance/duration matrix and solves a capacity-constrained vehicle routing problem with OR-Tools. It persists a draft route or a structured failure (`OSRM_UNAVAILABLE`, `INFEASIBLE_CAPACITY`, `NO_CANDIDATES`). Admin reviews/approves and assigns; driver sees assigned stops.

## 6. Collection verification

Per stop: `PENDING → ASSIGNED → EN_ROUTE → ARRIVED → COLLECTING → VERIFIED` or `ANOMALY`. Driver departure is explicit. Arrival validates geofence. OTP starts collection. Driver signals physical pickup completion; backend selects the first valid new sensor reading after that timestamp and evaluates evidence. The client never supplies sensor reading IDs or readings. Operator override from `ANOMALY` requires reason and audit.

## 7. Reliability and security

- TLS for MQTT and HTTPS; per-device ACL; Firebase token verification; role/resource authorization.
- MQTT QoS 1 plus database idempotency.
- Readiness checks distinguish DB unavailable from process alive.
- DB-backed operational settings, audited changes.
- Rate limits for OTP and location; minimal retention for driver location.
- ML is marked unavailable/experimental until enough quality history exists; a three-bin demo validates plumbing, not model quality.
