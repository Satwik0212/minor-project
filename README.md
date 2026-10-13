# SWM-ICS — Smart Waste Management & Intelligent Collection System

GitHub-ready monorepo scaffold for the SWM-ICS minor project. This includes the complete planned repository layout and Documentation v2; it is **not** a claim that every feature is already implemented.

## Stack
- ESP32 + ultrasonic distance, load cell/HX711, BME280/DHT22
- MQTT over TLS with per-device broker ACLs and a separate MQTT worker
- FastAPI, SQLAlchemy, Pydantic, Firebase ID-token verification and local roles
- PostgreSQL + PostGIS
- Browser-only HTML/CSS/JavaScript/Tailwind UI, Leaflet + OpenStreetMap
- OSRM + Google OR-Tools routing
- Pandas, NumPy, scikit-learn, XGBoost prediction when history is sufficient

## Read first
1. `docs/integration.md` — normative cross-layer contract
2. `docs/architecture.md`, `docs/features.md`, `docs/database.md`
3. `docs/decisions.md` and `docs/REVIEW-NOTES.md` — proposed defaults need sign-off/testing
4. `docs/DEVELOPMENT-ROADMAP.md`, `docs/SECURITY.md`

## Non-negotiable invariants
- Browser uses HTTPS REST only; never MQTT or direct database access.
- MQTT worker is a separate process from Uvicorn.
- `bin_id` and `device_id` are distinct; server resolves active assignment.
- Deduplicate by `(device_id, boot_id, sequence)`.
- Backend calculates authoritative fill from raw distance and versioned calibration.
- Raw readings are append-only; invalid/unknown values are `null`, not zero.
- Backend selects collection evidence; driver cannot submit trusted reading IDs/values.
- Three demo bins demonstrate the pipeline but do not prove reliable ML accuracy.

See `PROJECT-STRUCTURE.txt` for the file inventory.
