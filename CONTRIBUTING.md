# Contributing to SWM-ICS

Thank you for your interest in contributing to the **Smart Waste Management & Intelligent Collection System (SWM-ICS)**!

This guide outlines our development workflow, engineering standards, and the non-negotiable architectural invariants required across the monorepo.

---

## 1. Non-Negotiable Architectural Invariants

Before writing or modifying any code, familiarize yourself with [`docs/integration.md`](docs/integration.md). Every PR must adhere to these core principles:

1. **Browser Network Isolation:** The frontend browser dashboard interacts exclusively via HTTPS REST with the FastAPI backend. It **never** connects directly to the MQTT broker, PostgreSQL database, or internal caches.
2. **Identity Decoupling:** Physical `bin_id` (e.g., `BIN-001`) and hardware `device_id` (e.g., `ESP32-DEMO-001`) are strictly decoupled. The server resolves active device-to-bin mappings via the `device_bin_assignments` table.
3. **Server-Authoritative Calculations:** Firmware reports raw sensor distance in centimeters. The backend calculates authoritative fill percentage using approved, versioned calibration thresholds. Drivers and browser clients cannot submit arbitrary fill values.
4. **Append-Only Telemetry & Nullability:** Raw sensor readings are immutable and append-only. Invalid, timed-out, or missing sensor values are recorded as `null`, never `0`.
5. **Deduplication:** Telemetry messages are deduplicated on `(device_id, boot_id, sequence)`.
6. **Process Separation:** The MQTT ingestion worker is a standalone supervised daemon; it is **never** embedded into FastAPI lifespan handlers.
7. **Collection Evidence Authority:** The driver client never submits reading IDs or fill values to mark collection complete. The backend independently selects before-and-after sensor readings to verify waste removal.

---

## 2. Local Development Setup

### Prerequisites
- **Python:** 3.11 or 3.12
- **Node.js:** 20.x or 22.x
- **Docker & Docker Compose:** Optional for local SQLite demo, required for full PostgreSQL + PostGIS and Mosquitto testing.

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate a virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install backend dependencies in editable mode with dev tools
pip install -e ".[dev]"

# Configure environment variables
cp .env.example .env
# Edit .env to set DATABASE_URL (defaults to sqlite:///./demo.db for local dev)

# Run database migrations (creates all 24 domain tables)
alembic upgrade head

# Start FastAPI development server with auto-reload
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server with proxy to backend (port 8000)
npm run dev
# Dashboard available at http://localhost:5173
```

---

## 3. Testing & Verification

Always run the full automated verification suite before opening a pull request:

### Backend Tests
```bash
# Run pytest test suite (63+ automated tests)
cd backend
pytest

# Validate MQTT schema definitions
cd ..
python scripts/validate_mqtt_schemas.py

# Verify Python syntax compilation
python -m compileall -q backend/app
```

### Frontend Tests & Production Build
```bash
cd frontend

# Run Vitest unit tests
npm test

# Verify production bundle build
npm run build
```

---

## 4. Git Commit & Branching Guidelines

- **Branch Naming:**
  - `feat/feature-name` (New capability or feature)
  - `fix/bug-description` (Bug fix)
  - `docs/doc-update` (Documentation changes)
  - `refactor/subsystem-name` (Code refactoring without behavioral change)
- **Conventional Commits:**
  We follow the [Conventional Commits](https://www.conventionalcommits.org/) convention:
  - `feat(telemetry): add humidity threshold alert evaluation`
  - `fix(frontend): correct fill bar color clamping at boundaries`
  - `docs(readme): add system context architecture diagram`
  - `test(backend): add test for device replacement audit event`
  - `chore(deps): update geoalchemy2 requirement`
- **Secrets & Sensitive Files:**
  - Never commit `.env`, `*.pem`, `*.key`, `*.db`, or service account keys.
  - Review `git status` and `git diff` before committing to ensure no unintended binary artifacts are staged.

---

## 5. Pull Request Process

1. Fork or branch from `main`.
2. Follow the architectural invariants and coding standards.
3. Ensure all backend tests, frontend tests, schema validations, and builds pass.
4. Fill out the [Pull Request Template](.github/pull_request_template.md) completely, including the invariant verification checklist.
5. Submit your PR and request a review from project maintainers.
