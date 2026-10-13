# SWM-ICS — Smart Waste Management & Intelligent Collection System

SWM-ICS combines ESP32 smart-bin telemetry, MQTT/TLS, a FastAPI backend, PostgreSQL/PostGIS, browser dashboards, waste analytics, prediction, and route optimization.

## Documentation index

1. `integration.md` — **canonical cross-layer contract** for MQTT topics/payloads, units, nullability, enums, collection state machine and API naming.
2. `features.md` — feature requirements, algorithms, constraints and acceptance criteria.
3. `hardware.md` — ESP32 sensors, firmware responsibilities and MQTT contract.
4. `api.md` — REST endpoints, roles, request/response conventions.
5. `frontend.md` — pages, dashboards, interaction and design.
6. `database.md` — schema, constraints, indexes and ownership.
7. `architecture.md` — component boundaries and sequence flow.
8. `folders.md` — repository layout.
9. `testing.md` — unit, contract, integration and end-to-end tests.
10. `deployment.md` — environment, TLS, containers, monitoring and backup.
11. `decisions.md` — decisions requiring team sign-off.
12. `schemas/` — machine-readable MQTT telemetry/status/config/ack JSON Schemas.
13. `diagrams/` — current system context plus MQTT ingestion, route optimization and collection verification sequence diagrams.

## Canonical stack

- Hardware: ESP32, ultrasonic sensor, load cell + HX711, BME280/DHT22.
- Messaging: MQTT over TLS, JSON payloads, per-device broker ACL.
- Backend: Python, FastAPI, SQLAlchemy, Pydantic.
- Auth: Firebase ID-token verification mapped to local roles (`SUPER_ADMIN`, `OPERATOR`, `DRIVER`).
- Database: PostgreSQL + PostGIS.
- Frontend: HTML5, CSS3, JavaScript, Tailwind CSS, Leaflet + OpenStreetMap.
- Routing: OSRM + Google OR-Tools.
- ML: Pandas, NumPy, scikit-learn, XGBoost.

## Non-negotiable implementation rules

- Browser uses HTTPS REST; it never connects directly to MQTT or the database.
- MQTT consumer is a separate process from Uvicorn API workers.
- Backend calculates authoritative fill percentage from raw distance and versioned calibration.
- `bin_id` and `device_id` are distinct; server resolves the current device/bin assignment.
- Deduplication uses `(device_id, boot_id, sequence)`.
- Collection evidence readings are selected by backend, never submitted as trusted IDs/values by the driver.
- Runtime settings live in DB after initial seed; all changes are audited.
- See `integration.md` for the only canonical cross-layer contract. Other docs and schemas must match it.
