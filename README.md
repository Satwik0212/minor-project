# SWM-ICS — Smart Waste Management & Intelligent Collection System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue?logo=python)](backend/pyproject.toml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Vite](https://img.shields.io/badge/Frontend-Vite%20%2B%20Vanilla%20JS-646CFF.svg?logo=vite&logoColor=white)](frontend/)
[![Database: PostgreSQL + PostGIS / SQLite](https://img.shields.io/badge/Database-PostgreSQL%20%2B%20PostGIS%20%2F%20SQLite-336791.svg?logo=postgresql)](backend/app/models/)
[![Backend Checks](https://github.com/satwik0212/minor-project/actions/workflows/backend.yml/badge.svg)](.github/workflows/backend.yml)
[![Frontend Checks](https://github.com/satwik0212/minor-project/actions/workflows/frontend.yml/badge.svg)](.github/workflows/frontend.yml)

**SWM-ICS (Smart Waste Management & Intelligent Collection System)** is an IoT-enabled municipal waste management platform. It transforms traditional fixed-schedule collection routes into an intelligent, sensor-driven collection pipeline featuring continuous fill-level monitoring, authoritative calibration math, automated collection prioritization, alert management, and operational dispatch.

---

## 1. System Architecture & Data Flow

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
        BRK -.->|MQTT Topic Subscription| WRK[Standalone MQTT Ingestion Worker]
        REST_SIM[Simulated Telemetry /demo/reading] -->|HTTP POST| API[FastAPI REST API]
        WRK -->|1. Validate Schema & Identity| TEL[Telemetry Ingestion Service]
        WRK -->|2. Deduplicate| DEDUP[boot_id + sequence]
        WRK -->|3. Calculate Fill %| CALC[Authoritative Calibration Engine]
        WRK -->|4. Persist| DB[(PostgreSQL + PostGIS / SQLite)]
        API --> DB
    end

    subgraph Operations Dashboard
        API -->|HTTPS JSON REST /api/v1| FE[Vite / Vanilla JS Frontend]
        FE -->|Overview & KPI Metrics| OP[Operations Dashboard]
        FE -->|Inspect Bins & History| BINS[Smart Bins Drawer]
        FE -->|Acknowledge / Resolve| ALT[Alerts & Collection Queue]
    end
```

---

## 2. Core Architectural Invariants

Every subsystem strictly complies with the normative cross-layer contracts defined in [`docs/integration.md`](docs/integration.md):

- **Browser Network Isolation:** The browser client communicates exclusively with the backend via HTTPS REST. Browsers **never** connect directly to the MQTT broker or the database.
- **Identity Decoupling:** Physical `bin_id` (e.g. `BIN-001`) and hardware `device_id` (e.g. `ESP32-DEMO-001`) are strictly decoupled. The server dynamically resolves active assignments via the `device_bin_assignments` table.
- **Authoritative Fill Calculation:** Hardware devices only report raw sensor distance (cm). The backend calculates the authoritative fill percentage using versioned calibration thresholds:
  $$\text{fill\_percent} = \text{clamp}\left(\frac{\text{empty\_distance\_cm} - \text{distance\_cm}}{\text{empty\_distance\_cm} - \text{full\_distance\_cm}} \times 100, 0, 100\right)$$
- **Telemetry Immutability & Nullability:** Sensor readings are append-only. Invalid, timed-out, or missing values produce `null`, never `0`.
- **Deduplication:** Telemetry messages are deduplicated on `(device_id, boot_id, sequence)`.
- **Worker Process Separation:** The MQTT ingestion worker is a standalone supervised daemon, never embedded in web server request or lifespan loops.
- **Collection Evidence Authority:** The driver client never submits reading IDs or fill values to mark collection complete. The backend independently selects before-and-after readings to verify waste removal.

---

## 3. Implementation Status

| Subsystem | Scope / Capability | Current Implementation Status | Verification |
| :--- | :--- | :--- | :--- |
| **Domain Models & DB** | 24 domain tables (bins, readings, alerts, jobs, routes, etc.) | Complete (`backend/app/models/`), Alembic migrations | 63 automated tests passing |
| **Telemetry Ingestion** | Schema validation, deduplication, authoritative fill math | Complete (`backend/app/telemetry/`) | Verified in unit test suite |
| **Core REST APIs** | 19 registered endpoints for bins, alerts, health, demo | Complete (`backend/app/api/v1/`) | Verified in E2E presentation gate |
| **Operations Dashboard** | 3 responsive views: Overview, Bins Drawer, Priority/Alerts | Complete (`frontend/src/`) | 17 Vitest tests passing, Vite builds clean |
| **MQTT Worker Daemon** | Background subscriber for telemetry & status topics | Functional with mocks (`app/workers/mqtt_worker.py`) | Benchmarked via synthetic scripts |
| **ESP32 Firmware** | Sensor acquisition, TLS MQTT, config ACK | Scaffolded (`firmware/esp32/`) | Target Milestone 3 |
| **Route Optimization** | OSRM matrix + Google OR-Tools CVRP solver | Scaffolded (`routing/src/`, `app/routes/`) | Target Milestone 2 |
| **Driver OTP & Geofence**| Collection state machine, PostGIS geofence, OTP delivery | Scaffolded (`backend/app/collections/`) | Target Milestone 2 |
| **ML Fill Forecasting** | XGBoost time-series forecasting with rolling features | Scaffolded (`ml/src/`, `app/predictions/`) | Target Milestone 3 (Requires historical data) |

---

## 4. Monorepo Structure

```text
SWM-ICS/
├── .github/                 # GitHub Actions CI workflows, issue & PR templates, security policy
├── backend/                 # FastAPI REST application, SQLAlchemy ORM, Alembic migrations
│   ├── app/
│   │   ├── api/v1/          # Endpoints: bins, alerts, health, demo simulation
│   │   ├── core/            # App settings (Pydantic), logging, security
│   │   ├── db/              # Database session, base model, SQLite spatial shims
│   │   ├── models/          # 24 SQLAlchemy ORM domain models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── telemetry/       # Fill math, validation, ingestion service
│   │   └── workers/         # Standalone MQTT ingestion daemon
│   ├── migrations/          # Alembic database migration scripts
│   ├── tests/               # Pytest suite (63+ tests covering models, math, APIs)
│   └── pyproject.toml       # Backend Python dependencies and package metadata
├── docs/                    # Exhaustive architecture documentation & contracts
│   ├── integration.md       # Normative cross-layer API & MQTT contract
│   ├── architecture.md      # Subsystem architecture & context
│   ├── database.md          # 24-table database schema specification
│   ├── AUDIT-REPORT.md      # Comprehensive repo state audit & verification baseline
│   └── NEXT-STEPS.md        # Prioritized engineering implementation backlog
├── firmware/                # IoT firmware source code
│   └── esp32/               # PlatformIO C++ firmware project for ESP32
├── frontend/                # Operations Dashboard web application
│   ├── src/
│   │   ├── styles/          # Responsive CSS design system & component styles
│   │   ├── tests/           # Vitest unit tests for utilities & helpers
│   │   ├── utils/           # Time formatting, HTML escaping, priority badges
│   │   └── main.js          # Operations dashboard controller & API integration
│   ├── index.html           # Single-page application entry point
│   ├── vite.config.js       # Vite configuration with backend reverse proxy
│   └── package.json         # Frontend dependencies and test/build scripts
├── infra/                   # Infrastructure configuration (Mosquitto MQTT, Docker)
├── ml/                      # Machine learning training & feature engineering pipelines
├── routing/                 # OSRM road matrix & OR-Tools routing optimizer
├── scripts/                 # Schema validators, test data publishers, simulators
├── docker-compose.yml       # PostgreSQL 16 + PostGIS and Mosquitto broker setup
└── README.md                # Project documentation root
```

---

## 5. Quickstart Guide

### Prerequisites
- **Python:** 3.11 or 3.12
- **Node.js:** 20.x or 22.x (with `npm`)
- **Git**

---

### Option A: Instant Local Demo (Zero External Services)

Run the backend with SQLite and launch the frontend dashboard in under two minutes:

#### 1. Setup Backend
```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Install backend in editable mode with development dependencies
pip install -e ".[dev]"

# Copy development environment file (uses SQLite by default)
cp .env.example .env

# Run database migrations to initialize all tables
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
*API docs and OpenAPI interactive explorer available at `http://localhost:8000/docs`.*

#### 2. Setup Frontend Dashboard
```bash
# Open a new terminal and navigate to frontend
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
*Open your browser at `http://localhost:5173` to view the live dashboard.*

---

### Option B: Full Stack with Docker (PostgreSQL + PostGIS & MQTT Broker)

To run the production-target PostgreSQL 16 database and Mosquitto MQTT broker:

```bash
# Start PostGIS and Mosquitto containers in background
docker compose up -d

# Check container health
docker compose ps
```

In `backend/.env`, set:
```ini
DATABASE_URL=postgresql+psycopg://swm_ics:change_me_for_local_development@localhost:5432/swm_ics
```
Then execute:
```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

---

## 6. Interactive Demo Walkthrough

Once both backend (`:8000`) and frontend (`:5173`) are running:

1. **Seed Demo Dataset:**
   Click the **"Seed Demo Data"** button in the dashboard, or call the endpoint:
   ```bash
   curl -X POST http://localhost:8000/api/v1/demo/seed
   ```
   *This seeds 5 demo smart bins, assigned devices, versioned calibration profiles, readings, and alerts.*

2. **Simulate Real-Time Telemetry:**
   Click **"Simulate Reading"** in the top navigation bar, select a bin (e.g. `BIN-DEMO-001`), enter a sensor distance (e.g., `12` cm), and click **"Submit Reading"**.
   The backend immediately computes the authoritative fill level, updates priorities, and the dashboard reflects the changes in real-time.

3. **Manage Alerts:**
   Navigate to the **Collection Priority & Alerts** tab to inspect the priority queue, acknowledge open warnings, or resolve alerts.

---

## 7. Automated Testing Suite

Ensure software quality and prevent regressions by running the test suite:

### Backend Tests (pytest)
```bash
cd backend
pytest
```
*Result: 63 passed tests covering database constraints, migrations, telemetry validation, and API contracts.*

### Validate MQTT Schemas
```bash
python scripts/validate_mqtt_schemas.py
```
*Validates JSON Schema specifications for telemetry, status, config, and ack packets.*

### Frontend Unit Tests (Vitest)
```bash
cd frontend
npm test
```
*Result: 17 passed tests covering formatting, priority classification, and fill meters.*

### Frontend Production Build
```bash
cd frontend
npm run build
```

---

## 8. Configuration Reference

Key settings configurable via `.env` or system environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `sqlite:///./demo.db` | Database connection string (SQLite for demo, PostgreSQL for prod) |
| `API_PORT` | `8000` | FastAPI server port |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CORS_ALLOWED_ORIGINS`| `http://localhost:5173,...` | Comma-separated list of allowed browser origins |
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker hostname |
| `MQTT_BROKER_PORT` | `8883` | MQTT broker port (TLS: 8883, Plaintext: 1883) |
| `MQTT_CLIENT_ID` | `swm-ics-worker-local` | Ingestion worker MQTT client identifier |
| `OSRM_BASE_URL` | `https://router.project-osrm.org` | Open Source Routing Machine endpoint |
| `OTP_DEMO_MODE` | `false` | When `true`, returns driver OTP in debug responses |

---

## 9. Documentation Index

- [`docs/integration.md`](docs/integration.md) — Normative cross-layer API, MQTT schema, and enum contracts.
- [`docs/architecture.md`](docs/architecture.md) — Subsystem architecture, invariants, and sequence diagrams.
- [`docs/database.md`](docs/database.md) — Complete 24-table relational database schema and spatial types.
- [`docs/AUDIT-REPORT.md`](docs/AUDIT-REPORT.md) — Comprehensive repository status audit and verified capabilities.
- [`docs/NEXT-STEPS.md`](docs/NEXT-STEPS.md) — Prioritized engineering implementation backlog.
- [`docs/SECURITY.md`](docs/SECURITY.md) — Security checklist and vulnerability management guidelines.

---

## 10. Contributing & License

- Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) and [Security Policy](.github/SECURITY.md) before submitting a pull request.
- This project is licensed under the terms of the [MIT License](LICENSE).
