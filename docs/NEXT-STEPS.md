# SWM-ICS — Prioritized Implementation Backlog & Engineering Roadmap

**Audit Date:** 2026-10-14  
**Authoritative Basis:** Evidence gathered during the October 2026 Comprehensive Monorepo Audit.

---

## 1. Executive Implementation Strategy

The repository has established a working vertical slice for municipal operations: 24 SQLAlchemy models exist, authoritative telemetry calculations are verified, 19 core REST endpoints are active, and an operational 3-screen frontend dashboard is functional.

However, the architecture has significant technical debt and uncommitted artifacts that must be resolved before implementing new product capabilities:
1. **Foundation First (P0):** Correct repository hygiene, untrack binary databases from git, add missing dependencies, stage and commit the verified frontend, and configure local PostgreSQL and frontend unit testing.
2. **Next Milestone (P1):** Live MQTT Broker Provisioning, Device Registry Management, and Background Device Offline Detection.
3. **Subsequent Milestones (P2 & P3):** Collection Workflow with Geofence & OTP Verification, followed by OSRM/OR-Tools Route Optimization, and finally ML Forecasting when historical data permits.

---

## 2. The Single Recommended Next Milestone

### Milestone Title
**Milestone 1.0: Foundation Hardening, Real PostgreSQL Validation & Live MQTT Ingestion**

### Why This Must Come Next
Before building routes, collections, or machine learning, the foundation must be reliable:
- The system currently runs on SQLite with mock spatial types. Until PostgreSQL with PostGIS is provisioned and migrations execute online, spatial queries cannot be developed.
- The MQTT worker has only been exercised with mock clients; it must be verified with an active broker.
- Untracked database binaries and missing manifest dependencies create severe developer friction and CI fragility.

---

## 3. Ordered Task Backlog

### Phase P0: Correctness, Hygiene & Foundational Stability

#### Task P0.1: Repository Hygiene & Git Database Untracking
- **Priority:** `P0`
- **Why It Matters:** `backend/demo.db` is currently committed to Git. Any test run or demo seed dirties the working tree and risks binary merge conflicts.
- **Current State:** `git status` shows `modified: backend/demo.db`. `.gitignore` does not exclude `*.db`.
- **Prerequisites:** None.
- **Files Involved:** `.gitignore`, `backend/demo.db`.
- **Definition of Done:**
  - `git rm --cached backend/demo.db` executed.
  - `*.db` and `*.sqlite3` added to root `.gitignore`.
  - `backend/demo.db` remains on local disk for demo use, but is untracked by Git.
- **Tests Required:** `git status` is clean after running `pytest`.
- **Blockers / Dependencies:** None. Can proceed immediately without hardware.
- **Frontend Impact:** None.

#### Task P0.2: Manifest Dependency Fix for GeoAlchemy2
- **Priority:** `P0`
- **Why It Matters:** `geoalchemy2` is imported in `backend/app/db/base.py` and `0001_initial_schema.py`, but omitted from `backend/pyproject.toml`. Fresh installs fail immediately.
- **Current State:** `geoalchemy2==0.20.0` is installed manually in the local Python environment, but not declared in dependencies.
- **Prerequisites:** None.
- **Files Involved:** `backend/pyproject.toml`.
- **Definition of Done:**
  - `"geoalchemy2>=0.14.0"` added to `dependencies` array in `backend/pyproject.toml`.
  - `pip install -e "backend[dev]"` installs cleanly in a fresh virtualenv.
- **Tests Required:** `pytest tests/unit/test_models.py` in a clean environment.
- **Blockers / Dependencies:** None. Can proceed without hardware.
- **Frontend Impact:** None.

#### Task P0.3: Commit and Preserve Verified Frontend Assets
- **Priority:** `P0`
- **Why It Matters:** The entire 1,129-line operational frontend (`frontend/src/main.js`, `styles/main.css`, `index.html`) and reverse proxy config (`frontend/vite.config.js`) exist only locally as uncommitted changes.
- **Current State:** Working tree has uncommitted modifications replacing the old placeholder.
- **Prerequisites:** P0.1.
- **Files Involved:** `frontend/index.html`, `frontend/src/main.js`, `frontend/src/styles/main.css`, `frontend/vite.config.js`.
- **Definition of Done:**
  - Files staged and committed with a clear message (`feat(frontend): implement operational dashboard and vite proxy`).
  - `git status` reflects clean tree.
- **Tests Required:** `npm run build` succeeds.
- **Blockers / Dependencies:** None. Can proceed without hardware.
- **Frontend Impact:** Preserves the frontend developer's active work.

#### Task P0.4: Frontend Baseline Unit Testing Setup
- **Priority:** `P0`
- **Why It Matters:** `frontend/package.json` specifies `"test": "vitest run"`, which exits with code 1 because no test files exist, breaking CI if triggered.
- **Current State:** 0 test files in `frontend/src/tests/`.
- **Prerequisites:** P0.3.
- **Files Involved:** `frontend/src/tests/priority.test.js`, `frontend/src/tests/formatting.test.js`.
- **Definition of Done:**
  - Add tests verifying priority badge rendering, fill bar bounds, and relative time formatting.
  - `npm test` runs and passes with exit code 0.
- **Tests Required:** `npm test`.
- **Blockers / Dependencies:** None. Can proceed without hardware.
- **Frontend Impact:** Ensures regression testing for frontend helpers.

#### Task P0.5: Local PostgreSQL & PostGIS Provisioning
- **Priority:** `P0`
- **Why It Matters:** PostgreSQL with PostGIS is the normative production engine. The app has only been tested on SQLite with emulated text types.
- **Current State:** PostgreSQL 18 is running on port 5432, but credentials for `swm_ics` fail authentication.
- **Prerequisites:** Administrative access to local PostgreSQL instance.
- **Files Involved:** `backend/.env`, `docker-compose.yml`, `backend/migrations/env.py`.
- **Definition of Done:**
  - Database `swm_ics` and user `swm_ics` created with PostGIS extension enabled.
  - `alembic upgrade head` executes online against PostgreSQL successfully.
  - Liveness and readiness endpoints return `{"status":"ready","database":"ok"}` with PostgreSQL.
- **Tests Required:** Run test suite with `DATABASE_URL` pointing to PostgreSQL.
- **Blockers / Dependencies:** Local PostgreSQL credentials or starting Docker daemon. Can proceed without hardware.
- **Frontend Impact:** None.

---

### Phase P1: Core Device Lifecycle & Real-Time Ingestion

#### Task P1.1: Local MQTT Broker Integration & Supervised Worker Daemon
- **Priority:** `P1`
- **Why It Matters:** Telemetry ingestion is verified only via REST simulation and mock clients. Real MQTT broker transport is unverified.
- **Current State:** Standalone worker code exists (`app/workers/mqtt_worker.py`), but no broker is listening on ports 1883/8883.
- **Prerequisites:** P0.5.
- **Files Involved:** `backend/app/workers/mqtt_worker.py`, `infra/mqtt/mosquitto.local.conf`, `scripts/publish_test_telemetry.py`.
- **Definition of Done:**
  - Mosquitto broker started on port 1883/8883.
  - MQTT worker runs as an independent supervised process subscribing to `smartwaste/device/+/telemetry`.
  - Publishing synthetic telemetry via `scripts/publish_test_telemetry.py` results in a new row in `sensor_readings` and updated `bin_latest_state`.
- **Tests Required:** End-to-end telemetry ingestion test with real MQTT network transport.
- **Blockers / Dependencies:** Broker binary or Docker. Can proceed without hardware.
- **Frontend Impact:** Live dashboard reflects telemetry without manual browser simulation.

#### Task P1.2: Device Registry & Pairing Management APIs
- **Priority:** `P1`
- **Why It Matters:** Devices are currently seeded via demo scripts. Operators need formal APIs to register devices, pair them with bins, and replace failing units.
- **Current State:** `app/devices/` contains stub files with TODOs.
- **Prerequisites:** P0.5.
- **Files Involved:** `backend/app/devices/service.py`, `backend/app/devices/router.py`, `backend/app/devices/schemas.py`.
- **Definition of Done:**
  - Endpoints implemented: `GET/POST /api/v1/devices`, `POST /api/v1/devices/{device_id}/pair`, `POST /api/v1/devices/{device_id}/replace`.
  - Device replacement revokes previous assignment and logs audit event while preserving bin identity.
- **Tests Required:** Unit and integration tests for pairing constraints and replacement workflows.
- **Blockers / Dependencies:** None. Can proceed without hardware.
- **Frontend Impact:** Enables "Device Management" screen in frontend.

#### Task P1.3: Background Device Offline Detection Service
- **Priority:** `P1`
- **Why It Matters:** Bins with dead batteries or disconnected Wi-Fi must be detected automatically to raise `DEVICE_OFFLINE` alerts.
- **Current State:** `app/monitoring/health_rules.py` is a stub.
- **Prerequisites:** P1.1.
- **Files Involved:** `backend/app/monitoring/service.py`, `backend/app/monitoring/health_rules.py`.
- **Definition of Done:**
  - Scheduled background check compares `devices.last_seen_at` against `device_offline_after_seconds`.
  - Sets `reported_state="OFFLINE"` and creates/updates `DEVICE_OFFLINE` alert idempotently.
- **Tests Required:** Unit test simulating elapsed time and verifying alert creation.
- **Blockers / Dependencies:** None. Can proceed without hardware.
- **Frontend Impact:** Offline devices display gray status dots and warning badges on dashboard.

---

### Phase P2: Collections Workflow, Geofence & Routing Optimization

#### Task P2.1: Collection Job Candidate Generation
- **Priority:** `P2`
- **Why It Matters:** High-fill bins must automatically transition into collection work orders.
- **Current State:** `app/collections/` contains stub files.
- **Prerequisites:** P1.1.
- **Files Involved:** `backend/app/collections/service.py`, `backend/app/collections/router.py`.
- **Definition of Done:**
  - `CRITICAL` (>95%) or `HIGH` (>85%) bins automatically generate or update an idempotent candidate job in `PENDING` status.
  - Endpoints: `GET /api/v1/collections/jobs`, `POST /api/v1/collections/jobs/{id}/assign`.
- **Tests Required:** Unit test checking candidate deduplication per bin/window.
- **Blockers / Dependencies:** None. Can proceed without hardware.
- **Frontend Impact:** Collection queue tab displays actionable dispatch items.

#### Task P2.2: Driver Workflow State Machine with Geofence & OTP Verification
- **Priority:** `P2`
- **Why It Matters:** Prevents fraudulent collection records and guarantees physical bin servicing.
- **Current State:** `app/collections/state_machine.py`, `otp.py`, `verification.py` are stubs.
- **Prerequisites:** P2.1.
- **Files Involved:** `backend/app/collections/state_machine.py`, `otp.py`, `verification.py`.
- **Definition of Done:**
  - State machine: `PENDING -> ASSIGNED -> EN_ROUTE -> ARRIVED -> COLLECTING -> VERIFIED/ANOMALY`.
  - `/arrive` validates GPS within 100m of bin coordinate using PostGIS `ST_DWithin`.
  - `/start` validates OTP (with rate limiting and expiry).
  - `/verify` checks that sensor fill dropped by at least 10 percentage points after `/finish`.
- **Tests Required:** State transition tests, geofence boundary tests, OTP failure tests.
- **Blockers / Dependencies:** Requires PostGIS for geofence distance calculation.
- **Frontend Impact:** Enables dedicated Driver View in frontend.

#### Task P2.3: OSRM & Google OR-Tools Route Optimization
- **Priority:** `P2`
- **Why It Matters:** Automates optimal multi-stop collection paths considering vehicle weight capacity.
- **Current State:** `routing/src/` and `app/routes/` are stubs.
- **Prerequisites:** P2.1.
- **Files Involved:** `routing/src/osrm_client.py`, `routing/src/optimizer.py`, `backend/app/routes/service.py`.
- **Definition of Done:**
  - Queries OSRM for road distance matrix between depot and pending collection bins.
  - OR-Tools solves CVRP minimizing total distance while respecting vehicle `capacity_kg * 0.90`.
  - API returns `202 Accepted` with `task_id`; frontend polls `/api/v1/tasks/{task_id}` for completed route.
- **Tests Required:** Routing matrix tests, infeasible capacity error tests, optimization benchmark.
- **Blockers / Dependencies:** OSRM endpoint (public or local Docker).
- **Frontend Impact:** New Route Planning screen displaying ordered stops on Leaflet map.

---

### Phase P3: Physical Firmware, Analytics & Machine Learning

#### Task P3.1: ESP32 C++ Firmware Implementation (PlatformIO)
- **Priority:** `P3`
- **Why It Matters:** Connects physical hardware to the cloud infrastructure.
- **Current State:** 5-line placeholder in `firmware/esp32/src/main.cpp`.
- **Prerequisites:** P1.1.
- **Files Involved:** `firmware/esp32/src/main.cpp`, `firmware/esp32/include/`.
- **Definition of Done:**
  - PlatformIO project compiles for ESP32.
  - Reads HC-SR04 ultrasonic distance using median filter.
  - Connects to Wi-Fi and publishes MQTT telemetry over TLS matching `mqtt-telemetry-v1.schema.json`.
  - Stores persistent boot UUID in NVS.
- **Tests Required:** Hardware-in-the-loop bench testing.
- **Blockers / Dependencies:** Physical ESP32 DevKit, sensor hardware, Wi-Fi access.
- **Frontend Impact:** Displays genuine hardware telemetry indicators.

#### Task P3.2: PostGIS Spatial Analytics & Hotspot Clustering
- **Priority:** `P3`
- **Why It Matters:** Identifies urban zones with recurring overflow incidents for long-term municipal planning.
- **Current State:** `app/analytics/` contains stubs.
- **Prerequisites:** P0.5.
- **Files Involved:** `backend/app/analytics/service.py`, `backend/app/analytics/hotspots.py`.
- **Definition of Done:**
  - SQL query utilizing `ST_ClusterDBSCAN` to identify spatial clusters of high-priority bins.
  - Endpoint `GET /api/v1/analytics/hotspots` returns GeoJSON clusters.
- **Tests Required:** Spatial clustering query tests with sample coordinates.
- **Blockers / Dependencies:** PostGIS extension.
- **Frontend Impact:** Adds Heatmap / Hotspot layer to frontend Leaflet map.

#### Task P3.3: XGBoost ML Fill-Level Forecasting
- **Priority:** `P3`
- **Why It Matters:** Shifts collection from reactive overflow handling to proactive scheduling.
- **Current State:** `ml/src/` contains stubs; 0 tests.
- **Prerequisites:** Sufficient historical sensor readings (minimum 14–30 days of data).
- **Files Involved:** `ml/src/features/`, `ml/src/training/train.py`, `backend/app/predictions/`.
- **Definition of Done:**
  - Feature extraction pipeline generating rolling and lag features.
  - Chronological train/test split preventing data leakage.
  - Trained XGBoost model serialized to `ml/artifacts/`.
  - `GET /api/v1/predictions/bins/{id}` returns forecast with confidence metric or `NOT_AVAILABLE`.
- **Tests Required:** Model validation against simple persistence baseline.
- **Blockers / Dependencies:** Requires genuine historical time-series data.
- **Frontend Impact:** Displays predicted fill curve in bin detail drawer.
