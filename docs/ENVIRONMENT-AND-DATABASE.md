# SWM-ICS — Environment, Database & Operations Guide

**Audit Date:** 2026-10-14  
**Authoritative Basis:** Codebase inspection, SQLAlchemy models, Alembic migrations, and local runtime verification.

---

## 1. Database Architecture & Setup

### 1.1 Current Local Development & Presentation Setup
- **Configured Engine:** **SQLite 3** via SQLAlchemy dialect `sqlite:///./demo.db`.
- **Database File:** Located at `backend/demo.db` (503 KB on disk).
- **Configuration Source:** Defined in `backend/.env` as:
  ```env
  DATABASE_URL=sqlite:///./demo.db
  CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000,http://127.0.0.1:3000
  ```
- **Why SQLite is Used Today:**
  - **Zero-Dependency Portability:** Enables immediate local demonstration, evaluator review, and automated unit testing without requiring active Docker daemons or local PostgreSQL services.
  - **Embedded Performance:** Instant startup and teardown for the 63-test automated test suite.
- **Why SQLite is Strictly Temporary:**
  - **No Native Spatial Support:** SQLite does not natively support PostGIS spatial types or indexes (`ST_DWithin`, `ST_ClusterDBSCAN`). SWM-ICS emulates these types via GeoAlchemy2 `@compiles` shims in `backend/app/db/base.py` that convert `Geography`/`Geometry` columns to SQLite `TEXT`.
  - **Concurrency Limitations:** SQLite enforces table-level write locks, which cannot support high-frequency concurrent MQTT ingestion alongside operational supervisor traffic.
  - **JSON Processing:** PostgreSQL `JSONB` binary storage and GIN indexing are simulated on SQLite using plain text JSON.

### 1.2 Target Production Architecture
- **Canonical Engine:** **PostgreSQL 16 + PostGIS 3.4**.
- **Driver:** `psycopg` (Version 3) using connection string format:
  ```text
  postgresql+psycopg://<username>:<password>@<host>:<port>/<dbname>
  ```
- **Spatial Geometry:** Native SRID 4326 (`WGS 84`) coordinates stored as `GEOGRAPHY(POINT, 4326)` for bin locations and `GEOMETRY(MULTIPOLYGON, 4326)` for municipal area boundaries.
- **Spatial Indexing:** GiST indexes on all spatial columns to enable sub-millisecond geofence checks and proximity clustering.

### 1.3 Local vs. Production Comparison Matrix

| Attribute | Current Development Setup | Target Production Setup |
| :--- | :--- | :--- |
| **Database Engine** | SQLite 3 | PostgreSQL 16.x |
| **Spatial Extension** | Emulated (`base.py` shims to `TEXT`) | PostGIS 3.4+ |
| **Driver** | Built-in Python `sqlite3` | `psycopg` 3.2+ (`psycopg[binary]`) |
| **Connection String** | `sqlite:///./demo.db` | `postgresql+psycopg://swm_ics:pass@host:5432/swm_ics` |
| **Default Port** | N/A (embedded file) | `5432` |
| **Storage Location** | `backend/demo.db` | Docker volume `swm_ics_pgdata` or Cloud Managed DB |
| **Concurrent Writers** | Single writer (file locked) | Multi-process connection pool (`pool_pre_ping=True`) |
| **JSON Support** | Standard `TEXT` JSON | Binary indexed `JSONB` |

---

## 2. Configuration Precedence & Settings

Configuration is managed via Pydantic Settings in `backend/app/core/config.py`.

### Precedence Hierarchy (Highest to Lowest)
1. **Operating System Environment Variables:** (e.g. `$env:DATABASE_URL` in PowerShell or CI secrets).
2. **Local Environment Files:** `backend/.env`, falling back to parent directory `../.env`.
3. **Pydantic Model Defaults:** Default attribute values declared in `Settings` class (`app/core/config.py`).
4. **Database-Backed Dynamic Settings:** Target design for `system_settings` table (values in database override environment defaults after initial boot; currently scaffolded).

### Complete Environment Variable Reference

| Variable Name | Purpose | Default Value in Code | Production Requirement |
| :--- | :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg://swm_ics:change_me@localhost:5432/swm_ics` | Mandatory Secret |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed CORS origins | `http://localhost:5173,http://127.0.0.1:5173,...` | Restricted production domain |
| `MQTT_BROKER_HOST` | Hostname of the MQTT broker | `localhost` | Production broker hostname |
| `MQTT_BROKER_PORT` | Port of the MQTT broker | `8883` | `8883` (TLS) |
| `MQTT_USERNAME` | Username for MQTT worker client | `""` (anonymous / unauthenticated) | Mandatory Secret |
| `MQTT_PASSWORD` | Password for MQTT worker client | `""` | Mandatory Secret |
| `MQTT_CA_CERT_PATH` | Path to TLS CA certificate file | `""` | Valid path to CA bundle |
| `MQTT_CLIENT_ID` | Client identifier for MQTT session | `swm-ics-worker-local` | Unique service worker ID |
| `FIREBASE_PROJECT_ID`| Firebase project for token verification | `""` | Municipal project ID |
| `OSRM_BASE_URL` | URL of the OSRM routing engine | `https://router.project-osrm.org` | Internal self-hosted OSRM |
| `OTP_DEMO_MODE` | Exposes OTP in demo API responses | `False` | **Must be False** in production |
| `LOG_LEVEL` | Log verbosity | `INFO` | `INFO` or `WARNING` |

---

## 3. Database Migration Process

### 3.1 Migration Architecture (Alembic)
- **Configuration File:** `backend/alembic.ini`.
- **Environment Script:** `backend/migrations/env.py`.
- **Migration Directory:** `backend/migrations/versions/`.
- **Initial Migration:** `0001_initial_schema.py` (45 KB, 1,267 lines) defining all 24 domain tables.

### 3.2 Offline vs. Online Migrations
- **Offline DDL Rendering:** Running `alembic upgrade head --sql` generates raw SQL statements without touching a live database. In `backend/migrations/env.py`, offline execution automatically overrides SQLite URLs with a dummy PostgreSQL URL so that full PostgreSQL/PostGIS DDL is rendered to standard output.
- **Online Migration Execution:** Running `alembic upgrade head` connects directly to the configured `DATABASE_URL`.
  - When running against PostgreSQL, migration `0001` executes `CREATE EXTENSION IF NOT EXISTS postgis` and creates native PostGIS columns and partial unique indexes.
  - When running against SQLite, GeoAlchemy2 columns compile to `TEXT` via hooks in `app/db/base.py`, and indexes are created safely without PostGIS.

### 3.3 Safe Migration Commands (PowerShell)

```powershell
cd backend

# View rendered SQL statements without modifying the database (Safe Dry-Run):
alembic upgrade head --sql

# Inspect current database revision:
alembic current

# Apply migrations to the target database:
alembic upgrade head
```

---

## 4. Demo Data & Operational Data Isolation

### 4.1 Logical Isolation Pattern
Demo data and production operations share the same relational schema, but are strictly isolated using identity conventions:
- **Demo Entity Prefixes:** All demo entities use prefix `BIN-DEMO-*` (e.g. `BIN-DEMO-001`), `AREA-DEMO-*` (`AREA-DEMO-001`), and `ESP32-DEMO-*` (`ESP32-DEMO-001`).
- **Simulated Flag:** Demo bins set `is_simulated = true` in `smart_bins`.
- **Safe Reset Endpoint (`DELETE /api/v1/demo/reset`):** The reset endpoint executes targeted SQL queries deleting **only** records where `bin_id LIKE 'BIN-DEMO-%'` and `area_id = 'AREA-DEMO-001'`. Real municipal operational records are never modified or purged.

### 4.2 Seed Dataset Contents
The `POST /api/v1/demo/seed` endpoint generates:
- 1 Municipal Service Area: `Demo Zone` (`AREA-DEMO-001`).
- 5 Smart Bins (`BIN-DEMO-001` through `005`) with diverse capacities (50 kg to 200 kg) and warning/critical thresholds.
- 5 Paired IoT Devices (`ESP32-DEMO-001` through `005`).
- 5 Approved Calibrations (`empty_distance_cm = 100.0`, `full_distance_cm = 5.0`).
- 25 Historical Telemetry Readings across the bins.
- 2 Active Threshold Alerts for bins exceeding high fill levels.

---

## 5. Test Database Strategy

1. **Unit & Fast Presentation Gate Testing:**
   - Framework: `pytest` with `fastapi.testclient.TestClient`.
   - Engine: In-memory SQLite with `StaticPool` (`sqlite:///:memory:`).
   - Fixture Setup: `Base.metadata.create_all(engine)` executes in-memory in ~50ms.
   - Result: 63 out of 63 tests pass in 5.6 seconds.
2. **Target Integration Testing Strategy:**
   - PostgreSQL integration tests will use Testcontainers (`testcontainers-python`) or Docker Compose to spin up an ephemeral PostGIS container during CI.
   - Ensures native spatial queries (`ST_DWithin`) and PostgreSQL-specific partial indexes are exercised prior to production deployment.

---

## 6. Verified Startup Commands (Local Windows Development)

### 6.1 Backend API Server

Open a PowerShell terminal in the repository root:

```powershell
cd backend

# 1. Activate virtual environment (if using virtualenv):
# .\venv\Scripts\Activate.ps1

# 2. Ensure dependencies are installed:
pip install -e ".[dev]"

# 3. Start Uvicorn development server:
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Base URL: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health Liveness: `http://127.0.0.1:8000/health/live`

### 6.2 Frontend Operations Dashboard

Open a second PowerShell terminal in the repository root:

```powershell
cd frontend

# 1. Install Node dependencies (if not already installed):
npm install

# 2. Start Vite development server:
npm run dev
```
- Dashboard URL: `http://localhost:5173`
- The Vite reverse proxy forwards all `/api/*` and `/health/*` calls to `http://127.0.0.1:8000`.

### 6.3 Standalone MQTT Ingestion Worker (When Broker is Active)

Open a third PowerShell terminal:

```powershell
cd backend
python -m app.workers.mqtt_worker
```

---

## 7. Known Environment Limitations & Gotchas

1. **Docker Desktop Inactive:** Running `docker ps` fails on this machine because Docker Desktop is not started. PostgreSQL and Mosquitto container services cannot be launched via `docker compose up -d` until Docker Desktop is running.
2. **Local PostgreSQL Authentication:** A local PostgreSQL 18 service is running on port 5432, but credentials for user `swm_ics` fail. The application runs on SQLite until local credentials or a dedicated database are configured.
3. **No Active MQTT Broker:** Ports 1883 and 8883 are closed locally. Running `python -m app.workers.mqtt_worker` will log connection retry attempts until Mosquitto is started.
4. **Committed Database Binary:** `backend/demo.db` is tracked in git. Any write operation or test execution will modify this file and produce an uncommitted git change. Use `git checkout backend/demo.db` to restore baseline if needed.
