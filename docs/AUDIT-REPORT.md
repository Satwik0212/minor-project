# SWM-ICS — Comprehensive Project Status Audit & Architecture Discovery Report

**Audit Date:** 2026-10-14  
**Auditor:** Antigravity AI Engineering Team  
**Corpus / Repository Root:** `c:\Users\asus\Downloads\SWM-ICS`  
**Current Branch:** `main`  
**Base Commit:** `4eb8681` (`backend apis for demo monitoring and collection`)  
**Working Tree State:** Active uncommitted changes present (Frontend operational dashboard, Vite configuration, CORS enhancements, tracked `backend/demo.db`).

---

## 1. Scope, Methodology & Classification Standard

### 1.1 Scope
This audit is an exhaustive, evidence-based discovery review of the entire **Smart Waste Management & Intelligent Collection System (SWM-ICS)** monorepo. It establishes the authoritative baseline across the software, firmware, database, testing, API, and deployment layers.

### 1.2 Audit Rules of Engagement
- **Strict Read-Only Discovery:** No product features were implemented, no architecture rewritten, no database tables dropped or modified, and no demo data reset during this audit.
- **Direct Repository Evidence:** Claims were evaluated solely against tracked code, active test execution, directory layouts, configuration files, and runtime behavior.
- **Evidence-Based Classification:** Claims are classified using the following normative tags:
  - `VERIFIED`: Directly confirmed by code inspection and verified successful execution or automated test.
  - `CODE-VERIFIED`: Implementation code is complete and fully inspected, but full runtime behavior under production-like infrastructure has not been verified.
  - `PARTIAL`: Functional logic exists, but critical production requirements or related subsystems are missing.
  - `SCAFFOLDED`: Structural files, class declarations, or function signatures exist containing only `TODO` comments or stub returns.
  - `PLANNED`: Documented in roadmap/specifications, but no implementation code exists.
  - `BLOCKED`: Cannot be executed or verified due to missing external dependencies or unconfigured infrastructure.
  - `CONTRADICTED`: Conflicts identified between code, tests, documentation, or previous completion reports.
  - `UNKNOWN`: Insufficient evidence to establish veracity.

---

## 2. Product and Architecture Overview

### 2.1 The Problem SWM-ICS Solves
Municipal solid waste management in growing urban centers suffers from inefficient fixed-schedule collection routes. Trucks visit partially empty bins while overflowing bins create environmental hazards, pest infestation, and public dissatisfaction. 

SWM-ICS solves this by providing:
1. Continuous real-time IoT monitoring of waste bin fill levels.
2. Server-authoritative fill percentage calculations using versioned calibration metrics.
3. Automated priority ranking and threshold alerting for operations supervisors.
4. Future dynamic vehicle route optimization based on live bin urgency and vehicle capacities.
5. Verifiable driver collection workflows with geofencing and OTP verification.

### 2.2 Primary Actors and Roles
- **Super Admin:** Global municipal management, user and role assignment, fleet configuration, system settings, calibration approvals, and audit log inspection.
- **Operator (Supervisor):** Operational monitoring of smart bins and service areas, alert acknowledgment/resolution, manual candidate approval, route generation dispatch, and collection verification overrides.
- **Driver:** Vehicle operator who receives assigned collection routes, acknowledges departure, records geofenced arrival, submits OTP verification, and completes physical pickups.

### 2.3 System Context and Data Flow

```mermaid
graph TD
    subgraph IoT Edge
        HW[ESP32 Microcontroller] -->|Ultrasonic Distance| S1[HC-SR04 Sensor]
        HW -->|Load Cell Mass| S2[HX711 ADC]
        HW -->|Temp / Humidity| S3[BME280 / DHT22]
    end

    subgraph Messaging Layer
        HW -.->|MQTT over TLS:8883| BRK[Mosquitto Broker]
    end

    subgraph Backend Core
        BRK -.->|MQTT Topic Subscription| WRK[Standalone MQTT Worker]
        REST_SIM[Simulated Telemetry /demo/reading] -->|HTTP POST| API[FastAPI Uvicorn API]
        WRK -->|1. Validate Schema & Identity| TEL[Telemetry Service]
        WRK -->|2. Deduplicate| DEDUP[boot_id + sequence]
        WRK -->|3. Calculate Fill %| CALC[Authoritative Calibration]
        WRK -->|4. Persist| DB[(PostgreSQL + PostGIS / SQLite)]
        API --> DB
    end

    subgraph Frontend Operations
        API -->|HTTPS JSON REST /api/v1| FE[Vite / Vanilla JS Dashboard]
        FE -->|View Bins & Priority Queue| OP[Operations Dashboard]
        FE -->|Acknowledge / Resolve| ALT[Alerts Ledger]
    end
```

### 2.4 Non-Negotiable System Invariants
1. **REST-Only Frontend:** Browser clients communicate exclusively with the FastAPI backend over HTTPS REST; the browser never connects directly to MQTT or the database.
2. **Process Separation:** The MQTT ingestion worker is a standalone supervised daemon; it is never embedded into FastAPI lifespan handlers.
3. **Identity Decoupling:** Physical `bin_id` (e.g. `BIN-001`) and hardware `device_id` (e.g. `ESP32-DEMO-001`) are strictly decoupled. The server resolves device-to-bin mappings via the `device_bin_assignments` table.
4. **Message Deduplication:** Telemetry messages are deduplicated on `(device_id, boot_id, sequence)`.
5. **Authoritative Calculation:** Firmware reports raw sensor distance in centimeters. The backend calculates fill percentage using approved calibration:
   $$\text{fill\_percent} = \text{clamp}\left(\frac{\text{empty\_distance\_cm} - \text{distance\_cm}}{\text{empty\_distance\_cm} - \text{full\_distance\_cm}} \times 100, 0, 100\right)$$
6. **Nullability Integrity:** Sensor failures, out-of-range readings, and missing values produce `null`, never `0`.
7. **Collection Evidence Authority:** The driver client never submits reading IDs or fill values to mark collection complete. The backend independently selects before-and-after sensor readings.

---

## 3. Database Audit (Mandatory and Detailed)

### 3.1 Current Database Implementation
- **Current Local Engine:** **SQLite 3** (`sqlite:///./demo.db`).
- **Configuration Source:** `backend/.env` containing `DATABASE_URL=sqlite:///./demo.db`, which overrides the default PostgreSQL connection string in `backend/app/core/config.py`.
- **Database File Location:** `backend/demo.db` (503,808 bytes on disk).
- **Git Tracking Status:** `backend/demo.db` is **actively tracked in Git** (committed in commit `4eb8681`). Running seed operations or local testing mutates the binary and dirties the Git working tree. The root `.gitignore` excludes `.env` and `*.pyc`, but fails to exclude `*.db`.
- **Alembic Status:** `backend/demo.db` contains the table `alembic_version` with single row `0001_initial_schema`. Migration `0001_initial_schema.py` was executed to create the database schema.
- **PostgreSQL Availability on Host:** A Windows service named `postgresql-x64-18` is installed and actively listening on port 5432 (PID 7756). However, authentication attempts using the project default credentials (`swm_ics:change_me`) fail with `FATAL: password authentication failed for user "swm_ics"`.
- **Verification Status:** SWM-ICS has been verified **only against SQLite**. It has never executed an online end-to-end test against a live PostgreSQL server.

### 3.2 Temporary vs. Intended Database Architecture

| Dimension | Current Local / Demo Setup | Target Production Architecture | Architectural Trade-offs & Migration Impact |
| :--- | :--- | :--- | :--- |
| **Database Engine** | SQLite 3 | PostgreSQL 16 + PostGIS 3.4 | SQLite lacks native spatial functions, concurrent write scaling, and JSONB indexation. PostGIS is required for production spatial queries. |
| **Spatial Types** | GeoAlchemy2 types compiled to `TEXT` via SQLite compiler hooks in `app/db/base.py` | Native PostGIS `GEOGRAPHY(POINT, 4326)` and `GEOMETRY(MULTIPOLYGON, 4326)` | Geofence calculations (`ST_DWithin`) and spatial clustering (`ST_ClusterDBSCAN`) cannot run in SQLite. |
| **Migrations** | Alembic migration `0001_initial_schema.py` executed once | Automated CI/CD pipeline executing `alembic upgrade head` | Migration `0001` contains dialect branching (`if op.get_context().dialect.name == "postgresql"`). In offline mode, `env.py` forces PostgreSQL DDL. |
| **Data Isolation** | Prefix-based logical isolation (`BIN-DEMO-*`, `AREA-DEMO-*`) | Physical database separation between staging and production environments | Demo seeding/reset endpoints must be disabled in production configurations (`DEMO_MODE=false`). |
| **Test Fixtures** | `sqlite:///:memory:` with `StaticPool` | Ephemeral test containers using Testcontainers or Docker Compose | Fast unit test execution (5.6s), but zero test validation of PostgreSQL-specific features or constraints. |

### 3.3 Complete Schema & ORM Model Inventory

An audit of `backend/app/models/` and `backend/demo.db` confirms exactly 24 domain tables plus `alembic_version`.

| # | Table Name | Purpose | Primary Key | Critical Foreign Keys & Unique Constraints | Spatial / Special Types | Status |
|---|---|---|---|---|---|---|
| 1 | `users` | User registry & role mapping | `id` (UUID) | `firebase_uid` (UQ), `email` (UQ) | `role` (Enum) | `CODE-VERIFIED` (0 rows) |
| 2 | `areas` | Municipal operational zones | `id` (UUID) | `area_id` (UQ) | `boundary` (`Geometry(MULTIPOLYGON, 4326)`) | `VERIFIED` (1 row) |
| 3 | `smart_bins` | Physical bin assets | `id` (UUID) | `bin_id` (UQ), `area_id` -> `areas.id` | `location` (`Geography(POINT, 4326)`) | `VERIFIED` (5 rows) |
| 4 | `devices` | IoT hardware units | `id` (UUID) | `device_id` (UQ) | `lifecycle_state`, `reported_state`, `sensor_health` | `VERIFIED` (5 rows) |
| 5 | `device_bin_assignments` | Active & historical device-bin links | `id` (UUID) | `device_id` -> `devices.id`, `bin_id` -> `smart_bins.id` | Partial UQ: active device / active bin | `VERIFIED` (5 rows) |
| 6 | `sensor_configurations` | Versioned bin calibration parameters | `id` (UUID) | `bin_id` -> `smart_bins.id`, UQ `(bin_id, calibration_version)` | Check: `empty > full > 0` | `VERIFIED` (5 rows) |
| 7 | `sensor_readings` | Append-only raw telemetry | `id` (UUID) | UQ `(device_id, boot_id, sequence)`, FKs: `bin_id`, `device_id` | JSON array `sensor_faults`, `quality_flags` | `VERIFIED` (27 rows) |
| 8 | `bin_latest_state` | Latest state projection per bin | `bin_id` (PK, FK) | FK `latest_reading_id` -> `sensor_readings.id` | `fill_percent`, `priority`, `is_stale` | `VERIFIED` (5 rows) |
| 9 | `alerts` | System alerts & notification ledger | `id` (UUID) | `alert_id` (UQ), FKs: `bin_id`, `device_id`, `job_id` | `type`, `severity`, `status`, JSON `details` | `VERIFIED` (2 rows) |
| 10 | `vehicles` | Fleet collection vehicles | `id` (UUID) | `vehicle_id` (UQ) | `vehicle_type`, `capacity_kg`, `status` | `SCAFFOLDED` (0 rows) |
| 11 | `drivers` | Fleet drivers & license records | `id` (UUID) | `driver_id` (UQ), `user_id` (UQ FK -> `users.id`) | `status` | `SCAFFOLDED` (0 rows) |
| 12 | `depots` | Vehicle dispatch origins / depots | `id` (UUID) | `depot_id` (UQ) | `location` (`Geography(POINT, 4326)`) | `SCAFFOLDED` (0 rows) |
| 13 | `collection_jobs` | Work orders for bin emptying | `id` (UUID) | `job_id` (UQ), `bin_id` -> `smart_bins.id` | `source`, `status`, `priority` | `SCAFFOLDED` (0 rows) |
| 14 | `routes` | Vehicle collection routes | `id` (UUID) | `route_id` (UQ), FKs: `depot_id`, `vehicle_id`, `driver_id` | `status`, `objective`, `distance_m` | `SCAFFOLDED` (0 rows) |
| 15 | `route_stops` | Sequenced route stops | `id` (UUID) | UQ `(route_id, sequence_no)`, FKs: `route_id`, `collection_job_id` | `planned_arrival_at`, `distance_m` | `SCAFFOLDED` (0 rows) |
| 16 | `collection_verifications` | Audit evidence for pickups | `id` (UUID) | `job_id` (UQ FK), FKs: `before_reading_id`, `after_reading_id` | `fill_before_pct`, `fill_after_pct`, `outcome` | `SCAFFOLDED` (0 rows) |
| 17 | `driver_location_points` | High-frequency driver GPS tracking | `id` (UUID) | FKs: `driver_id`, `route_id` | `location` (`Geography(POINT, 4326)`) | `SCAFFOLDED` (0 rows) |
| 18 | `background_tasks` | Async job tracker | `id` (UUID) | `task_id` (UQ) | `status`, `progress`, JSON `result_ref` | `SCAFFOLDED` (0 rows) |
| 19 | `system_settings` | Dynamic runtime settings | `key` (TEXT PK) | None | JSON `value`, JSON `validation` | `SCAFFOLDED` (0 rows) |
| 20 | `audit_events` | Immutable security audit log | `id` (UUID) | FK: `actor_id` -> `users.id` | JSON `before_diff`, JSON `after_diff` | `SCAFFOLDED` (0 rows) |
| 21 | `idempotency_records` | Mutating REST request replays | `id` (UUID) | UQ `(actor_id, key)` | JSON `response_body` | `SCAFFOLDED` (0 rows) |
| 22 | `rejected_telemetry_events` | Quarantined malformed payloads | `id` (UUID) | None | JSON `payload_redacted`, `reason_code` | `CODE-VERIFIED` (0 rows) |
| 23 | `predictions` | ML fill forecasts | `id` (UUID) | FK: `bin_id` -> `smart_bins.id` | `predicted_fill_percent`, `confidence` | `SCAFFOLDED` (0 rows) |
| 24 | `model_registry` | ML model version artifacts | `id` (UUID) | `model_version` (UQ) | JSON `metrics`, `artifact_uri` | `SCAFFOLDED` (0 rows) |

### 3.4 Database Compatibility & Migration Risks
- **Cross-Dialect GeoAlchemy2 Shims (`backend/app/db/base.py`):** The application relies on custom SQLAlchemy `@compiles` decorators that compile `Geography` and `Geometry` columns to `TEXT` on SQLite. In addition, an engine connection listener injects dummy Python functions into SQLite for spatial functions like `ST_GeogFromText` and `ST_AsBinary`. While effective for local development and testing, this setup masks potential production PostGIS syntax errors.
- **Missing Manifest Dependency:** `geoalchemy2` is imported by `backend/app/db/base.py` and `0001_initial_schema.py`, but is missing from `backend/pyproject.toml`. Fresh installations without an existing virtual environment fail on import.

---

## 4. Backend Architecture and Implementation Status

### 4.1 FastAPI Application Initialization
- **Entry Point:** `backend/app/main.py`.
- **CORS Configuration:** Modified locally to allow origins: `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:5500`, `http://127.0.0.1:5500`, `http://localhost:3000`, `http://127.0.0.1:3000`.
- **Router Inclusions:**
  - `health_router` mounted at `/health` and `/api/v1/health`.
  - `api_router` mounted at `/api/v1`.

### 4.2 Module Inventory: Working vs. Scaffolded Code

Inspection of the filesystem reveals a sharp divide between fully functional vertical slice modules and empty scaffold files containing only 1-line `TODO` docstrings.

```
Total Python files in backend/app: 98
Implemented files (> 150 bytes): 39 (includes models, telemetry, endpoints, config)
Scaffolded stub files (50 - 80 bytes): 59 (empty modules with TODO docstrings)
```

| Module / Package | File / Location | Byte Size | Actual Behavior | Status |
| :--- | :--- | :--- | :--- | :--- |
| **API Endpoints: Bins** | `app/api/v1/endpoints/bins.py` | 10,423 | Implements `/bins`, `/bins/summary`, `/bins/{id}`, `/bins/{id}/readings` | `VERIFIED` |
| **API Endpoints: Alerts** | `app/api/v1/endpoints/alerts.py` | 11,258 | Implements `/alerts`, `/alerts/{id}/acknowledge`, `/resolve`, `/collection/priority` | `VERIFIED` |
| **API Endpoints: Demo** | `app/api/v1/endpoints/demo.py` | 20,328 | Implements `/demo/seed`, `/demo/reset`, `/demo/status`, `/demo/reading` | `VERIFIED` |
| **API Endpoints: Health** | `app/api/v1/endpoints/health.py` | 518 | Implements `/health/live`, `/health/ready` | `VERIFIED` |
| **Telemetry Validation** | `app/telemetry/validation.py` | 11,951 | Validates JSON schema, deduplication keys, sensor ranges, timestamps | `VERIFIED` |
| **Telemetry Fill Math** | `app/telemetry/fill_calculation.py` | 4,248 | Implements canonical clamping formula and exact priority boundaries | `VERIFIED` |
| **Telemetry Service** | `app/telemetry/service.py` | 20,295 | End-to-end ingestion pipeline: validation, dedup, calibration, persistence, alert creation | `VERIFIED` |
| **MQTT Worker Daemon** | `app/workers/mqtt_worker.py` | 7,007 | Standalone Paho MQTT client subscribing to telemetry and status topics | `PARTIAL` |
| **Authentication** | `app/auth/*.py` | ~70 ea. | Stubs: `firebase.py`, `dependencies.py`, `permissions.py`, `service.py` | `SCAFFOLDED` |
| **Collections State Machine** | `app/collections/*.py` | ~75 ea. | Stubs: `service.py`, `state_machine.py`, `otp.py`, `verification.py`, `evidence.py` | `SCAFFOLDED` |
| **Route Optimization** | `app/routes/*.py` | ~72 ea. | Stubs: `service.py`, `assignment.py`, `optimization.py`, `router.py` | `SCAFFOLDED` |
| **Analytics & Hotspots** | `app/analytics/*.py` | ~74 ea. | Stubs: `service.py`, `hotspots.py`, `router.py`, `schemas.py` | `SCAFFOLDED` |
| **Predictions & ML** | `app/predictions/*.py` | ~76 ea. | Stubs: `service.py`, `eligibility.py`, `router.py`, `schemas.py` | `SCAFFOLDED` |
| **Settings & Audit** | `app/settings/`, `app/audit/` | ~70 ea. | Stubs: `settings/service.py`, `audit/service.py`, `events.py` | `SCAFFOLDED` |
| **External Routing Engine** | `routing/src/*.py` | ~40 ea. | Stubs: `optimizer.py`, `matrix.py`, `osrm_client.py` | `SCAFFOLDED` |
| **ML Training & Inference** | `ml/src/**/*.py` | ~50 ea. | Stubs: `training/train.py`, `inference/predict.py`, `features/build.py` | `SCAFFOLDED` |

---

## 5. Complete API Registry & Operational Audit

Inspection of FastAPI's active OpenAPI registry reveals **19 registered endpoints**.

| HTTP Method | Path | Summary / Responsibility | Auth Required | Request Model | Response Model | Tested in E2E Suite? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | API metadata and documentation link | None | None | `{"name","version","docs"}` | `VERIFIED` |
| `GET` | `/health` | Operational health check (root alias) | None | None | `HealthResponse` | `VERIFIED` |
| `GET` | `/health/live` | Process liveness check | None | None | `HealthResponse` (`status="ok"`) | `VERIFIED` |
| `GET` | `/health/ready` | Database readiness check | None | None | `HealthReadyResponse` | `VERIFIED` |
| `GET` | `/api/v1/health` | Prefixed health check | None | None | `HealthResponse` | `VERIFIED` |
| `GET` | `/api/v1/health/live`| Prefixed process liveness check | None | None | `HealthResponse` | `VERIFIED` |
| `GET` | `/api/v1/health/ready`| Prefixed database readiness check | None | None | `HealthReadyResponse` | `VERIFIED` |
| `GET` | `/api/v1/bins` | Paginated bin listing with latest state | None | Query params (`page`, `priority`, etc.) | `PaginatedBinsResponse` | `VERIFIED` |
| `GET` | `/api/v1/bins/summary` | Aggregate bin metrics for KPI cards | None | None | `BinSummaryResponse` | `VERIFIED` |
| `GET` | `/api/v1/bins/{bin_id}`| Single bin details + last 20 readings | None | Path param `bin_id` | `BinDetailResponse` | `VERIFIED` |
| `GET` | `/api/v1/collection/priority` | Bins sorted by collection priority | None | Query params (`priority`, `area_id`) | `PriorityQueueResponse` | `VERIFIED` |
| `GET` | `/api/v1/alerts` | Paginated alerts ledger | None | Query params (`status`, `severity`) | `PaginatedAlertsResponse` | `VERIFIED` |
| `GET` | `/api/v1/alerts/{alert_id}` | Single alert detail record | None | Path param `alert_id` | `AlertResponse` | `VERIFIED` |
| `POST` | `/api/v1/alerts/{alert_id}/acknowledge` | Transition OPEN -> ACKNOWLEDGED | None | Path param `alert_id` | `AlertResponse` | `VERIFIED` |
| `POST` | `/api/v1/alerts/{alert_id}/resolve` | Transition OPEN/ACK -> RESOLVED | None | Path param `alert_id` | `AlertResponse` | `VERIFIED` |
| `GET` | `/api/v1/demo/status` | Check if demo dataset is loaded | None | None | `DemoStatusResponse` | `VERIFIED` |
| `POST` | `/api/v1/demo/seed` | Seed 5 demo bins, readings, & alerts | None | None | `SeedResponse` | `VERIFIED` |
| `DELETE` | `/api/v1/demo/reset` | Delete all demo-tagged records | None | None | `ResetResponse` | `VERIFIED` |
| `POST` | `/api/v1/demo/reading` | Inject simulated reading & compute fill | None | `DemoReadingRequest` | `DemoReadingResponse` | `VERIFIED` |

---

## 6. Frontend Audit

### 6.1 Architecture & Stack
- **Framework & Build System:** Pure Vanilla JavaScript (ES6+ Modules), HTML5, Vanilla CSS3, built and served with **Vite 6.4.4**. No heavy component frameworks (React, Vue) or Tailwind build dependencies are used.
- **Entry Points:** `frontend/index.html` loads `frontend/src/main.js` and imports `frontend/src/styles/main.css`.
- **Proxy Configuration:** `frontend/vite.config.js` configures reverse proxies for `/api` and `/health` targeting `http://127.0.0.1:8000`, eliminating local browser CORS issues.

### 6.2 Screen Implementation Analysis
The frontend is a dedicated municipal waste operations dashboard comprising three primary views:

1. **Dashboard View (`showDashboard`):**
   - KPI Row: Total Bins, Active Bins, Needs Collection, Critical Count, High Priority Count, Simulated Count.
   - Dual Column Ledger: "Needs Attention" list (top 5 priority bins) and "Recent Alerts" list.
   - One-click demo seeder trigger if the database is unpopulated.
2. **Smart Bins View (`showBins`):**
   - Paginated bin table displaying Bin ID, Name, Area, Fill Level Bar, Priority Badge, Operational Status, Sensor Health, Last Reading timestamp, and Stale Reading warning indicators.
   - Filtering controls by Priority (`CRITICAL`, `HIGH`, `MEDIUM`, `NORMAL`, `UNKNOWN`) and Status (`ACTIVE`, `INACTIVE`, `MAINTENANCE`, `DRAFT`, `RETIRED`).
   - Interactive Detail Drawer (`openBinDetail`): Sliding panel with complete bin metadata, calibration thresholds, full-width fill meter, and recent readings history table with a bar chart visualization.
   - Reading Simulation Modal (`openSimModal`): Allows selecting a demo bin, entering distance (cm), submitting to `POST /api/v1/demo/reading`, and reviewing the server-calculated fill and priority.
3. **Collection Priority & Alerts View (`showPriority`):**
   - Collection Queue: Real-time list of bins sorted from `CRITICAL` down to `NORMAL`, displaying fill meters, open alert badges, and area names.
   - Alerts Ledger: Filterable ledger (`OPEN`, `ACKNOWLEDGED`, `ALL`) with real-time interactive buttons to acknowledge or resolve active alerts via the REST API.

### 6.3 Frontend Verification & Test Status
- **Build Verification:** Running `npm run build` succeeds in 379ms, outputting production assets to `frontend/dist/`.
- **Test Verification:** Running `npm test` fails with code 1 (`vitest run: No test files found`). No automated frontend unit or integration tests exist.
- **Git Tracking Status:** The current frontend code exists **only locally in the working tree** as uncommitted changes to `frontend/index.html`, `frontend/src/main.js`, `frontend/src/styles/main.css`, and untracked `frontend/vite.config.js`.

---

## 7. Hardware and MQTT Audit

### 7.1 Hardware Architecture (Beginner-Friendly Explanation)
In SWM-ICS, physical smart bins are monitored by an IoT hardware controller mounted on the underside of the bin lid.
- **ESP32 Microcontroller:** The processing unit with built-in Wi-Fi and cryptographic hardware acceleration for TLS.
- **HC-SR04 / JSN-SR04T Ultrasonic Sensor:** Emits high-frequency sound pulses toward the waste surface and measures echo transit time to determine distance in centimeters.
- **HX711 ADC + Load Cells:** Measures mechanical force exerted on the base of the bin to estimate mass in kilograms.
- **BME280 / DHT22 Sensor:** Measures ambient temperature and relative humidity to detect biological decomposition, overheating, or combustion risks.

### 7.2 Telemetry Ingestion Flow
1. **Sensor Measurement:** The ESP32 measures distance (cm) using a median filter over 3–5 pulses to reject acoustic outliers.
2. **Envelope Assembly:** The firmware packs raw measurements into `mqtt-telemetry-v1.schema.json` with a persistent boot UUID and monotonic sequence number.
3. **Transmission:** The device publishes to `smartwaste/device/{device_id}/telemetry` over TLS (port 8883).
4. **Broker & ACL:** The Mosquitto broker verifies device credentials and enforces topic-level publish ACLs.
5. **Worker Processing:** The standalone worker validates payload structure, resolves the active bin assignment, verifies deduplication, loads bin calibration, and calculates fill percentage.
6. **Persistence & Side Effects:** The reading is appended to `sensor_readings`, `bin_latest_state` is updated, and threshold alerts are evaluated idempotently.

### 7.3 Actual Hardware & MQTT Status
- **Physical Firmware:** `firmware/esp32/src/main.cpp` contains 5 lines of placeholder code (`void setup() { Serial.begin(115200); } void loop() { delay(1000); }`). No sensor drivers, TLS stacks, or NVS boot UUID logic are implemented.
- **Local Broker:** Network port scans on ports 1883 and 8883 confirm no MQTT broker is running on the local host.
- **Synthetic Testing:** The script `scripts/publish_test_telemetry.py` provides a synthetic Paho MQTT publisher for local development, but does not substitute for hardware verification.

---

## 8. Advanced Features Audit: Routing, Collection, Analytics & ML

| Subsystem | Planned Capability | Actual Implementation State | Status |
| :--- | :--- | :--- | :--- |
| **Route Optimization** | OSRM road distance/duration matrix + Google OR-Tools CVRP solver; async task execution | `backend/app/routes/` and `routing/src/` contain only stub files with `TODO` docstrings. | `SCAFFOLDED` |
| **Driver Collection Workflow** | State machine: `PENDING -> ASSIGNED -> EN_ROUTE -> ARRIVED -> COLLECTING -> VERIFIED/ANOMALY` | `backend/app/collections/` contains only stub files. | `SCAFFOLDED` |
| **Arrival Geofence & OTP** | Geofence verification (100m radius) + OTP delivery to facility contact | `app/collections/otp.py` is an empty stub file. | `SCAFFOLDED` |
| **Collection Evidence Verification** | Backend captures before/after readings, evaluates fill/weight reduction | `app/collections/verification.py` is an empty stub file. | `SCAFFOLDED` |
| **Spatial Analytics & Hotspots** | Area aggregation + PostGIS DBSCAN spatial clustering | `app/analytics/` contains only stub files. | `SCAFFOLDED` |
| **ML Fill Forecasting** | XGBoost fill-level forecasting with chronological train/test splits | `ml/src/` contains only stub files; 0 tests exist in `ml/tests`. | `SCAFFOLDED` |

---

## 9. Security, Reliability & Testing Audit

### 9.1 Security & Access Control
- **Authentication:** Documented as Firebase ID token validation mapped to internal roles (`SUPER_ADMIN`, `OPERATOR`, `DRIVER`). In the current codebase, all endpoints in `backend/app/api/v1/` are completely unauthenticated.
- **Secret Handling:** Credentials and secrets are omitted from Git. The committed `.env.example` files use safe development placeholders.
- **Input Validation:** Incoming JSON telemetry and REST request bodies are strictly validated using Pydantic schemas and JSON Schema specifications (`schemas/mqtt-telemetry-v1.schema.json`).

### 9.2 Automated Test Suite Results
- **Backend Test Suite:** Executed via `pytest` in `backend/`:
  - 63 tests collected, 63 passed (100% success rate in 5.64s).
  - All tests utilize SQLite in-memory fixtures (`sqlite:///:memory:`).
- **Untested Layers:**
  - `routing/tests`: 0 tests (exits code 1).
  - `ml/tests`: 0 tests (exits code 1).
  - `frontend`: 0 tests (`npm test` exits code 1).
  - Live PostgreSQL / PostGIS: 0 tests executed.
  - Live MQTT Broker: 0 tests executed.

---

## 10. Deployment and Environment Inventory

### 10.1 Configuration Matrix

| Variable / Setting | Purpose | Source File | Current Local Value | Production Requirement |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | Primary database connection string | `backend/.env` | `sqlite:///./demo.db` | `postgresql+psycopg://user:pass@host:5432/swm_ics` |
| `CORS_ALLOWED_ORIGINS` | Permitted browser origins | `backend/app/core/config.py` | `http://localhost:5173,http://127.0.0.1:5173,...` | Restricted production domain URL |
| `MQTT_BROKER_HOST` | Hostname of MQTT broker | `backend/app/core/config.py` | `localhost` | Managed MQTT broker host |
| `MQTT_BROKER_PORT` | Port of MQTT broker | `backend/app/core/config.py` | `8883` | `8883` (TLS) |
| `MQTT_CLIENT_ID` | Client ID for worker connection | `backend/app/core/config.py` | `swm-ics-worker-local` | Supervised worker identifier |
| `OSRM_BASE_URL` | Routing service endpoint | `backend/app/core/config.py` | `https://router.project-osrm.org` | Self-hosted internal OSRM container |
| `OTP_DEMO_MODE` | Exposes OTP in demo API responses | `backend/app/core/config.py` | `False` | Must remain `False` in production |
| `LOG_LEVEL` | Logging verbosity | `backend/app/core/config.py` | `INFO` | `INFO` or `WARNING` |

### 10.2 Infrastructure Services
- **Docker Compose (`docker-compose.yml`):** Defines `postgis/postgis:16-3.4` and `eclipse-mosquitto:2`. Docker Desktop is not currently running on the host system.

---

## 11. Comparison of Actual Code Against Features Roadmap

| Roadmap Phase | Stated Objective | Current Implementation State | Classification | Evidence | Remaining Work |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 0: Baseline & Guardrails** | Repository structure, CI checks, contracts | `docs/integration.md` finalized; GitHub workflows configured | `PARTIAL` | Workflows pass, but lack PostgreSQL/MQTT service containers | Add frontend tests and multi-service CI |
| **Phase 1: Database Foundation** | 24 domain models, PostGIS support, migrations | All 24 models implemented; Alembic migration `0001` exists | `PARTIAL` | `backend/app/models/`, `backend/demo.db` (24 tables) | Verify against live PostgreSQL; add `geoalchemy2` to pyproject |
| **Phase 2: Config & Observability** | Settings precedence, DB settings table, health checks | Config precedence verified; health endpoints operational; settings table is a stub | `PARTIAL` | `app/core/config.py`, `app/api/v1/endpoints/health.py` | Implement DB-backed runtime settings service |
| **Phase 3: Telemetry Ingestion** | Validation, deduplication, fill math, worker daemon | Validation, math, and service verified; worker tested with mocks | `VERIFIED` (Service) / `PARTIAL` (Worker) | 26 unit tests passing in `tests/unit/test_telemetry_*.py` | Connect worker to live MQTT broker |
| **Phase 4: Device Lifecycle** | Pairing, offline detection, last-will, replacement | Models exist; offline detection and pairing logic are stubs | `SCAFFOLDED` | `app/devices/`, `app/monitoring/` contain TODO stubs | Implement offline detection daemon and pairing APIs |
| **Phase 5: Backend API & Auth** | API shell, Firebase auth, role enforcement, entity CRUD | Core monitoring/demo APIs verified; auth and CRUD routers are stubs | `PARTIAL` | 19 OpenAPI routes functional; `app/auth/` is stubbed | Implement Firebase auth and remaining routers |
| **Phase 6: Frontend Dashboard** | Operations dashboard, smart bin monitoring, priority queue | 3 functional views implemented in Vanilla JS/CSS; reverse proxy active | `VERIFIED` | `frontend/src/main.js`, `index.html`, `vite.config.js` | Add map visualization and driver views |
| **Phase 7: ESP32 Firmware** | Sensor acquisition, TLS MQTT, config ACK, last-will | 5-line placeholder in `firmware/esp32/src/main.cpp` | `SCAFFOLDED` | PlatformIO source inspection | Complete PlatformIO C++ firmware |
| **Phase 8: Collection Workflow** | Candidates, dispatch, OTP, geofence, verification | All collection and evidence modules are stubs | `SCAFFOLDED` | `app/collections/*.py` files contain TODO stubs | Build collection state machine and verification |
| **Phase 9: Route Optimization** | OSRM road matrix, OR-Tools solver, async task queue | Routing modules and task queue are stubs; 0 tests | `SCAFFOLDED` | `routing/src/` and `app/routes/` contain TODO stubs | Implement VRP solver and task worker |
| **Phase 10: Analytics & ML** | PostGIS hotspots, trend aggregation, XGBoost model | Analytics and ML modules are stubs; 0 tests | `SCAFFOLDED` | `app/analytics/` and `ml/src/` contain TODO stubs | Build feature engineering and training pipelines |
| **Phase 11: Reports & Audit** | Immutable audit logs, CSV exports, operational reports | Audit and report modules are stubs | `SCAFFOLDED` | `app/audit/` and `app/reports/` contain TODO stubs | Implement audit middleware and report aggregators |
| **Phase 12: E2E Release** | Docker Compose multi-service deployment, verification | `docker-compose.yml` exists; Docker daemon not running | `BLOCKED` | Docker daemon unavailable on dev host | Full integration testing in containerized stack |

---

## 12. Contradictions and Technical Debt Register

### Discrepancy 1: Committed Database Binary Mutating Working Tree
- **Conflicting Claims:** The repository claims to follow clean Git practices, but `backend/demo.db` is actively tracked in Git.
- **Evidence:** `git status` shows `modified: backend/demo.db`; `git ls-files backend/demo.db` returns the tracked path.
- **Authoritative Rule:** Data artifacts, temporary SQLite databases, and test databases must never be tracked in Git (`.gitignore`).
- **Impact:** Any test run or demo seed dirties the Git working tree and risks merge conflicts.
- **Recommended Resolution:** Untrack `backend/demo.db` via `git rm --cached backend/demo.db` and add `*.db` to `.gitignore`.

### Discrepancy 2: Missing Package Dependency in Manifest
- **Conflicting Claims:** `backend/pyproject.toml` defines backend dependencies, omitting `geoalchemy2`.
- **Evidence:** `backend/app/db/base.py` imports `geoalchemy2.Geography`. Local environment has `geoalchemy2==0.20.0` installed manually.
- **Authoritative Rule:** All direct dependencies must be declared in `pyproject.toml`.
- **Impact:** New developers and CI pipelines executing `pip install -e "backend[dev]"` will encounter `ModuleNotFoundError: No module named 'geoalchemy2'`.
- **Recommended Resolution:** Add `"geoalchemy2>=0.14.0"` to `backend/pyproject.toml`.

### Discrepancy 3: Uncommitted Frontend Implementation
- **Conflicting Claims:** Previous reports implied the frontend replacement was complete.
- **Evidence:** `git status` reveals `frontend/index.html`, `frontend/src/main.js`, and `frontend/src/styles/main.css` are modified, while `frontend/vite.config.js` is untracked.
- **Authoritative Rule:** Working code must be committed to source control to prevent accidental data loss.
- **Impact:** Local changes risk being overwritten or lost during branch switching.
- **Recommended Resolution:** Stage and commit the operational frontend assets.

### Discrepancy 4: Missing Frontend Tests Causing Script Failure
- **Conflicting Claims:** `frontend/package.json` defines a test script `"test": "vitest run"`.
- **Evidence:** Running `npm test` fails with code 1 (`No test files found`).
- **Authoritative Rule:** Package scripts must not fail on default execution.
- **Impact:** Any CI job or pre-commit hook executing `npm test` fails immediately.
- **Recommended Resolution:** Add baseline component/utility tests in `frontend/src/tests/`.

---

## 13. Audit Conclusion & Final Verdict

The SWM-ICS project has achieved a **fully functional, verified presentation vertical slice**:
- The core data model (24 tables), authoritative telemetry validation, calibration calculation, and core REST APIs are sound, tested, and passing 63 automated tests.
- The frontend operations dashboard is functional, responsive, and communicating with the backend via a reverse proxy.
- **However, the project is not complete.** The database currently runs on SQLite rather than PostgreSQL/PostGIS, the MQTT worker lacks a live broker, the ESP32 firmware is a scaffold, and advanced capabilities (routing, collection workflow, ML, analytics, auth) remain entirely unimplemented TODO stubs.

The next phase of work must focus on **foundation hardening and infrastructure provisioning** before beginning advanced feature development.
