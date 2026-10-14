# SWM-ICS Frontend Integration Guide

> **Living document** — last updated to match Emergency Demo Sprint implementation.
> Maintained by the backend team. Frontend engineer: read this before wiring any API call.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Running the Backend Locally](#2-running-the-backend-locally)
3. [Complete API Registry](#3-complete-api-registry)
4. [Data Dictionary & Field Semantics](#4-data-dictionary--field-semantics)
5. [Dashboard Cards & Statistics Data Sources](#5-dashboard-cards--statistics-data-sources)
6. [Demo Data Workflow](#6-demo-data-workflow)
7. [Priority & Status Display Rules](#7-priority--status-display-rules)
8. [Frontend State Guide](#8-frontend-state-guide)
9. [Frontend Decision Log](#9-frontend-decision-log)
10. [Implemented vs Planned Capabilities](#10-implemented-vs-planned-capabilities)
11. [Decisions Requiring Frontend Confirmation](#11-decisions-requiring-frontend-confirmation)

---

## 1. Project Overview

**SWM-ICS** (Smart Waste Management & Intelligent Collection System) is a real-time waste-bin
monitoring platform. The backend exposes a REST API. The frontend consumes it.

For the college presentation demo, **no physical ESP32 hardware is required**. The backend
includes a full demo-data workflow (Section 6) that seeds realistic simulated bins and readings.

**Two independently demonstrable features are implemented:**

| Feature | Description |
|---|---|
| **Feature 1 — Smart Bin Monitoring** | View all bins with live fill %, priority, health status, and last reading timestamp |
| **Feature 2 — Collection Priority & Alerts** | View bins sorted by urgency (CRITICAL first), filter by area/priority, see active alerts |

---

## 2. Running the Backend Locally

### Prerequisites
- Python 3.11 or 3.12, virtual environment activated
- Database choice:
  - **Option A (Zero-dependency SQLite for Demo):** No external database required. Recommended for tomorrow's presentation.
  - **Option B (PostgreSQL + PostGIS):** Requires Docker or a local PostgreSQL instance with PostGIS enabled.

### Quick Start (Option A — SQLite Demo Mode)

```powershell
cd backend
# Create backend/.env with SQLite configuration:
"DATABASE_URL=sqlite:///./demo.db" | Out-File -Encoding utf8 .env

# Run database migrations (creates all 24 domain tables):
alembic upgrade head

# Start the development server:
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Quick Start (Option B — PostgreSQL Mode)

```powershell
cd backend
cp ../.env.example .env     # configure PostgreSQL credentials in .env
alembic upgrade head        # run migrations
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Interactive API Docs
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:**      `http://localhost:8000/redoc`

### Authentication & CORS Policy

- **Authentication (Current Development State):**
  All current sprint endpoints (`/bins/*`, `/alerts/*`, `/collection/*`, `/demo/*`) require **no authentication token**. The frontend does not need to send `Authorization: Bearer ...` headers.
  *(Planned for Milestone 3: Firebase ID token verification will be attached to production operational routes. Do not implement fake auth on the frontend now.)*

- **CORS Allowed Origins:**
  By default, `backend/app/core/config.py` allows:
  `http://localhost:5173`, `http://127.0.0.1:5173`, `http://localhost:5500`, `http://127.0.0.1:5500`, `http://localhost:3000`, `http://127.0.0.1:3000`.
  In addition, `frontend/vite.config.js` configures a reverse proxy forwarding `/api` and `/health` to `http://127.0.0.1:8000`, eliminating browser CORS issues in development.

---

## 3. Complete API Registry

Base URL: `http://localhost:8000/api/v1`

### Health Check Endpoints

> **Note:** Health check endpoints are mounted at both the server root (`/health/*`) and under the API namespace (`/api/v1/health/*`).

| Method | Path | Description | Response Example |
|--------|------|-------------|------------------|
| `GET` | `/health` or `/api/v1/health` | Liveness check (alias) | `{"status": "ok"}` |
| `GET` | `/health/live` or `/api/v1/health/live` | Canonical liveness check | `{"status": "ok"}` |
| `GET` | `/health/ready` or `/api/v1/health/ready` | Database readiness check | `{"status": "ready", "database": "ok"}` |

### Feature 1 — Smart Bin Monitoring

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/bins/summary` | Dashboard KPI card data: total bins, counts by priority and status |
| `GET` | `/bins` | Paginated bin list with latest state joined |
| `GET` | `/bins/{bin_id}` | Single bin detail + last 20 readings |

#### `/bins` query parameters

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `page` | int | `1` | >= 1 |
| `page_size` | int | `20` | 1-100 |
| `priority` | string | (all) | `CRITICAL` `HIGH` `MEDIUM` `NORMAL` `UNKNOWN` |
| `status` | string | (all) | `ACTIVE` `INACTIVE` `DRAFT` `MAINTENANCE` `RETIRED` |
| `area_id` | string | (all) | Area's `area_id` field (e.g. `AREA-DEMO-001`) |

### Feature 2 — Collection Priority & Alerts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/alerts` | Paginated alerts (default: OPEN only) |
| `GET` | `/alerts/{alert_id}` | Single alert detail |
| `POST` | `/alerts/{alert_id}/acknowledge` | Acknowledge an OPEN alert |
| `POST` | `/alerts/{alert_id}/resolve` | Resolve an alert |
| `GET` | `/collection/priority` | Bins ordered CRITICAL to NORMAL for dispatch view |

#### `/alerts` query parameters

| Param | Type | Default | Values |
|-------|------|---------|--------|
| `status` | string | `OPEN` | `OPEN` `ACKNOWLEDGED` `RESOLVED` `DISMISSED` `ALL` |
| `severity` | string | (all) | `INFO` `WARNING` `ERROR` `CRITICAL` |
| `bin_id` | string | (all) | Bin's `bin_id` string |

#### `/collection/priority` query parameters

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `priority` | string | (all) | Filter by fill priority |
| `area_id` | string | (all) | Filter by area |
| `exclude_stale` | bool | `false` | Skip bins with stale readings |

### Feature 3 — Demo Data

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/demo/status` | Check if demo data is seeded |
| `POST` | `/demo/seed` | Create 5 demo bins with historical readings and alerts |
| `DELETE` | `/demo/reset` | Remove all demo data (safe — never touches real data) |
| `POST` | `/demo/reading` | Inject a single manual simulated reading |

---

## 4. Data Dictionary & Field Semantics

### Bin object (`BinListItem`)

| Field | Type | Semantics |
|-------|------|-----------|
| `id` | UUID | Internal primary key — do not display |
| `bin_id` | string | Human-readable ID e.g. `BIN-DEMO-001` — use in URLs and labels |
| `name` | string | Display name for the bin location |
| `bin_type` | enum | `MUNICIPAL` `RECYCLING` `ORGANIC` `HAZARDOUS` `OTHER` |
| `status` | enum | Operational lifecycle — see Section 7 |
| `area` | object or null | `{ area_id, name }` — the service zone |
| `capacity_kg` | float | Maximum load capacity in kilograms |
| `warning_threshold_pct` | float | Fill % at which WARNING alerts fire (default 70) |
| `critical_threshold_pct` | float | Fill % at which CRITICAL alerts fire (default 95) |
| `is_simulated` | bool | Always `true` for demo bins — show a SIM badge |
| `latest_state` | object or null | Snapshot of the most recent reading — see below |
| `created_at` | ISO8601 datetime | When the bin was registered |

### Latest State object (`LatestStateOut`)

| Field | Type | Semantics |
|-------|------|-----------|
| `fill_percent` | float or null | Fill level 0-100. `null` = no valid reading. **Never show 0 when null.** |
| `weight_kg` | float or null | Load-cell weight in kg (optional hardware) |
| `priority` | enum | `UNKNOWN` `NORMAL` `MEDIUM` `HIGH` `CRITICAL` — see Section 7 |
| `predicted_priority` | enum | `NONE` `PREDICTED_HIGH` `PREDICTED_CRITICAL` |
| `sensor_health` | enum | `OK` `DEGRADED` `FAULT` — see Section 7 |
| `device_reported_state` | enum | `ONLINE` `OFFLINE` `FAULT` `MAINTENANCE` |
| `is_stale` | bool | `true` when no reading within the stale threshold |
| `latest_event_at` | ISO8601 or null | Timestamp of the most recent reading |
| `updated_at` | ISO8601 | When this state was last written |

### Sensor Reading object (`ReadingBrief`)

| Field | Type | Semantics |
|-------|------|-----------|
| `id` | UUID | Reading identifier |
| `timestamp` | ISO8601 | Effective measurement time |
| `distance_cm` | float or null | Raw ultrasonic distance from sensor to waste surface |
| `fill_percent` | float or null | Server-calculated authoritative fill percentage |
| `weight_kg` | float or null | Load cell reading (optional) |
| `temperature_c` | float or null | Ambient temperature |
| `humidity_percent` | float or null | Ambient humidity |
| `battery_percent` | float or null | Device battery level |
| `sensor_health` | enum | `OK` `DEGRADED` `FAULT` |
| `sensor_faults` | string[] | Fault codes e.g. `["ULTRASONIC_TIMEOUT"]` |
| `quality_flags` | string[] | Data quality annotations e.g. `["CALIBRATION_MISSING"]` |
| `eligible_for_operations` | bool | Whether this reading affects collection priority |

### Alert object (`AlertOut`)

| Field | Type | Semantics |
|-------|------|-----------|
| `id` | UUID | Internal PK |
| `alert_id` | string | Human-readable unique ID — use this in API calls |
| `type` | enum | `BIN_THRESHOLD` `DEVICE_OFFLINE` `SENSOR_ANOMALY` etc. |
| `severity` | enum | `INFO` `WARNING` `ERROR` `CRITICAL` |
| `status` | enum | `OPEN` `ACKNOWLEDGED` `RESOLVED` `DISMISSED` |
| `bin_id` | UUID or null | FK to the bin |
| `bin_label` | string or null | The bin's `bin_id` string for quick display |
| `message` | string | Human-readable alert description |
| `details` | object or null | Structured metadata (fill%, priority, etc.) |
| `opened_at` | ISO8601 | When the alert was raised |
| `resolved_at` | ISO8601 or null | When the alert was resolved |

### Priority Bin Item (`PriorityBinItem` — collection view)

| Field | Type | Semantics |
|-------|------|-----------|
| `bin_id` | string | Bin identifier |
| `name` | string | Display name |
| `area_name` | string or null | Area display name |
| `fill_percent` | float or null | Current fill level |
| `priority` | enum | Current fill priority |
| `sensor_health` | enum | Current sensor health |
| `device_reported_state` | enum | Device connectivity status |
| `is_stale` | bool | Whether the reading is stale |
| `latest_event_at` | ISO8601 or null | Last reading timestamp |
| `open_alert_count` | int | Number of open alerts for this bin |

---

## 5. Dashboard Cards & Statistics Data Sources

### Summary cards (top of dashboard)

Call: `GET /api/v1/bins/summary`

| Card Title | Field Path | Example |
|---|---|---|
| Total Bins | `total` | 5 |
| Active Bins | `active_count` | 5 |
| Critical | `by_priority.CRITICAL` | 1 |
| High Priority | `by_priority.HIGH` | 1 |
| Normal | `by_priority.NORMAL` | 1 |

### Bin monitoring table

Call: `GET /api/v1/bins?page=1&page_size=50`

Recommended columns:
- Bin ID (`bin_id`) + Name (`name`)
- Area (`area.name`)
- Fill % bar (`latest_state.fill_percent`)
- Priority badge (`latest_state.priority`) — color-coded per Section 7
- Sensor health icon (`latest_state.sensor_health`)
- Device status (`latest_state.device_reported_state`)
- Last reading (`latest_state.latest_event_at`) — show "No reading" if null
- SIM badge (`is_simulated`)

### Collection priority table

Call: `GET /api/v1/collection/priority`

Bins are returned pre-sorted CRITICAL to NORMAL. Display:
- Priority badge (color per Section 7)
- Fill % with progress bar
- Area name
- Open alerts count badge (`open_alert_count`)
- Last seen timestamp

### Active alerts panel

Call: `GET /api/v1/alerts` (default: OPEN only)

Display per row:
- Severity icon + color
- Alert type label
- Bin label (`bin_label`)
- Message text
- Time since opened (`opened_at`)
- Acknowledge / Resolve action buttons

### Bin detail fill chart

Call: `GET /api/v1/bins/{bin_id}` — use `recent_readings` array

Plot `fill_percent` vs `timestamp` for the last 20 readings.
Show a gap (not zero) for null `fill_percent` values — these indicate sensor faults.

---

## 6. Demo Data Workflow

### Step 1 — Seed demo data (run once before the presentation)

```
POST /api/v1/demo/seed
```

Response:
```json
{
  "seeded": true,
  "bins_created": 5,
  "readings_inserted": 25,
  "alerts_created": 2,
  "message": "Demo data seeded: 5 bins, 25 readings, 2 alerts."
}
```

This creates **5 demo bins** with realistic fill levels:

| Bin ID | Name | Fill % | Priority | Note |
|--------|------|--------|----------|------|
| `BIN-DEMO-001` | Main Market North | ~92% | HIGH | Near critical |
| `BIN-DEMO-002` | Bus Stand East | ~97% | CRITICAL | Immediate action |
| `BIN-DEMO-003` | City Park Entrance | ~45% | NORMAL | All clear |
| `BIN-DEMO-004` | Hospital Road | ~78% | MEDIUM | Monitor |
| `BIN-DEMO-005` | Old Town Square | null | UNKNOWN | Sensor fault |

### Step 2 — Live demo: inject a manual reading

```
POST /api/v1/demo/reading
Content-Type: application/json

{
  "bin_id": "BIN-DEMO-003",
  "distance_cm": 8.0
}
```

8 cm distance with demo calibration (empty=100cm, full=5cm) gives ~96% fill → CRITICAL.
The dashboard reflects the new state on next poll.

### Manual reading field reference

| Field | Required | Range | Effect |
|-------|----------|-------|--------|
| `bin_id` | YES | `BIN-DEMO-*` prefix only | Which bin to update |
| `distance_cm` | no | 1-400 cm | Primary fill driver. Omit to simulate sensor fault |
| `weight_kg` | no | >= 0 | Optional supplementary metric |
| `temperature_c` | no | any float | Environmental reading |
| `humidity_percent` | no | 0-100 | Environmental reading |
| `battery_percent` | no | 0-100 | Device battery level |

### Fill calculation lookup table

Demo calibration: `empty_cm = 100`, `full_cm = 5`

| distance_cm sent | fill_percent result | priority |
|-----------------|--------------------|---------  |
| 100 | 0% | NORMAL |
| 56 | ~46% | NORMAL |
| 33 | ~70% | MEDIUM |
| 20 | ~84% | MEDIUM |
| 12 | ~93% | HIGH |
| 6 | ~99% | CRITICAL |
| omitted / null | null | UNKNOWN |

### Step 3 — Reset (clean up after demo)

```
DELETE /api/v1/demo/reset
```

Only deletes rows with `BIN-DEMO-*` and `AREA-DEMO-*` prefixes. Real data is untouched.
Safe to call at any time. Idempotent.

---

## 7. Priority & Status Display Rules

### Fill Priority — color mapping

| Value | Hex color | Usage |
|-------|-----------|-------|
| `CRITICAL` | `#EF4444` | Solid red badge, flashing indicator |
| `HIGH` | `#F97316` | Orange bold badge |
| `MEDIUM` | `#F59E0B` | Amber standard badge |
| `NORMAL` | `#22C55E` | Green subtle badge |
| `UNKNOWN` | `#6B7280` | Gray muted text, dashed border |

### Priority bands (for tooltips / legend)

- **NORMAL**: fill < 70%
- **MEDIUM**: 70% <= fill <= 85%
- **HIGH**: 85% < fill <= 95%
- **CRITICAL**: fill > 95%
- **UNKNOWN**: null fill (sensor fault or no reading yet)

### Sensor Health — icon mapping

| Value | Icon | Meaning |
|-------|------|---------|
| `OK` | Green circle check | Sensor functioning normally |
| `DEGRADED` | Amber warning triangle | Minor faults but fill data is usable |
| `FAULT` | Red X | Ultrasonic failure — fill_percent will be null |

### Device State — icon mapping

| Value | Icon / color | Meaning |
|-------|-------------|---------|
| `ONLINE` | Green dot | Device actively reporting |
| `OFFLINE` | Gray dot | No recent heartbeat |
| `FAULT` | Red dot | Device reported a fault |
| `MAINTENANCE` | Amber wrench | Device under maintenance |

### Bin Status display

| Value | Display color | Note |
|-------|--------------|------|
| `ACTIVE` | Green | Normal operation |
| `INACTIVE` | Gray | Not collecting data |
| `DRAFT` | Blue | Provisioned but not live |
| `MAINTENANCE` | Amber | Temporarily offline |
| `RETIRED` | Muted red | Decommissioned |

### Alert Severity — badge colors

| Value | Hex color | Style |
|-------|-----------|-------|
| `CRITICAL` | `#EF4444` | Solid red |
| `ERROR` | `#F97316` | Orange |
| `WARNING` | `#F59E0B` | Amber |
| `INFO` | `#3B82F6` | Blue |

### Null fill_percent display rules

> **CRITICAL:** Do NOT show `0%` when `fill_percent` is `null`. They mean different things.

| `fill_percent` | Display |
|---|---|
| `null` | Show `—` or `N/A` in gray; sensor fault icon |
| `0.0` | Show `0%` in green (bin is genuinely empty) |
| `100.0` | Show `100%` in red (bin is full) |

### Stale reading display

When `is_stale = true`:
- Show warning icon next to timestamp
- Mute the fill_percent value (gray text)
- Tooltip: "Reading may be outdated"

---

## 8. Frontend State Guide

### Polling strategy

The backend does not push WebSocket events. Poll these endpoints:

| Endpoint | Interval | Purpose |
|----------|----------|---------|
| `GET /bins/summary` | 10 s | Dashboard KPI cards |
| `GET /bins` | 15 s | Bin monitoring table |
| `GET /alerts` | 10 s | Active alerts panel |
| `GET /collection/priority` | 15 s | Collection dispatch view |

### Loading states

- Show skeleton rows (not full-page spinners) while fetching
- After first successful fetch, update table rows in-place without flickering

### Error handling

| HTTP Status | Meaning | UI Response |
|-------------|---------|-------------|
| `200` | Success | Render data |
| `400` | Bad query parameter | Show inline validation error |
| `404` | Bin or alert not found | Empty state with message |
| `409` | Conflict (already acknowledged/resolved) | Toast: "Already resolved" |
| `422` | Pydantic validation error | Parse `detail` array for field errors |
| `500` | Server error | Toast: "Backend error — try again" |

### Pagination

All list endpoints return: `{ items, total, page, page_size }`

```js
const totalPages = Math.ceil(response.total / response.page_size);
// Pass: ?page=N&page_size=20
```

---

## 9. Frontend Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01 | `bin_id` string used as URL segment, not UUID | Human-readable, stable, matches MQTT topic structure |
| 2025-01 | `null` fill never coerced to `0%` | Sensor fault vs. empty bin are semantically distinct states |
| 2025-01 | `/bins/summary` is a dedicated endpoint | Avoids loading all bin records just for KPI card counts |
| 2025-01 | `/collection/priority` sorts server-side | Avoids JS sorting on potentially thousands of bins |
| 2025-01 | Demo bins carry `is_simulated: true` | Frontend should show a SIM badge to distinguish from real hardware |
| 2025-01 | Manual readings restricted to `BIN-DEMO-*` | Safety guard: prevents accidental injection into real operational bins |
| 2025-01 | Alert state transitions via POST (not PATCH) | Simpler for demo; no JSON body required for a pure state transition |
| 2025-01 | CORS default: `http://localhost:5500` | Matches VS Code Live Server default port |

---

## 10. Implemented vs Planned Capabilities

| Capability Area | Current Status (Ready for Presentation) | Planned (Future Roadmap Milestones) |
|-----------------|-----------------------------------------|-------------------------------------|
| **Bin Monitoring** | Real-time REST endpoints (`/bins/summary`, `/bins`, `/bins/{bin_id}`) with fill %, priority, and last 20 readings | WebSocket / Server-Sent Events push stream |
| **Priority View** | Authoritative server-side priority sorting (`/collection/priority`) CRITICAL → NORMAL | Automated vehicle route optimization with OSRM (Milestone 4) |
| **Alert Workflow** | OPEN alerts, acknowledge, resolve with optimistic state checks (`/alerts/*`) | Push notifications, SMS/Email dispatching, driver mobile alerts |
| **Demo & Simulation**| In-memory & DB demo seeding (`/demo/seed`), reset isolation (`/demo/reset`), manual simulated injection (`/demo/reading`) | Live multi-device continuous hardware simulation loop script |
| **Authentication** | Unauthenticated for rapid local demo & development | Firebase Auth Bearer token verification with SuperAdmin/Operator/Driver roles (Milestone 3) |
| **Database Support**| PostgreSQL + PostGIS (Production) and SQLite (Local presentation zero-config) | Read-replicas, partitioning on `sensor_readings` |

---

## 11. Decisions Requiring Frontend Confirmation

The following architectural and design decisions require alignment with the frontend engineer:

1. **Local Development Port Alignment:**
   - The backend currently allows CORS from `http://localhost:5500` and `http://127.0.0.1:5500` by default.
   - *Confirmation needed:* If you are using Vite (default port `5173`), Create React App (`3000`), or Next.js (`3000`), confirm your preferred local origin so it can be added to default configuration.

2. **Polling Frequency vs. Rate Limits:**
   - Recommended frontend polling intervals:
     - Dashboard Summary: 10 seconds (`GET /bins/summary`)
     - Bin Table: 15 seconds (`GET /bins`)
     - Active Alerts: 10 seconds (`GET /alerts`)
     - Collection Priority: 15 seconds (`GET /collection/priority`)
   - *Confirmation needed:* Confirm if these polling rates are acceptable for the demo browser experience without causing UI flicker.

3. **Stale Reading & Fault Badge Design:**
   - When `is_stale == true`, readings should display a subtle clock/warning badge.
   - When `fill_percent == null` (sensor fault), the UI must display a "Fault / No Signal" badge rather than "0%".
   - *Confirmation needed:* Confirm UI components adhere to this null-safety rule to avoid misleading the evaluation committee.

4. **Alert Action Feedback:**
   - Acknowledging and resolving alerts are immediate HTTP `POST` operations returning `{ "alert_id", "status", "message" }`.
   - *Confirmation needed:* Does the frontend prefer immediate optimistic row updates in the alerts table or a re-fetch of `GET /alerts` after action button clicks?

---

*For backend API questions, browse `/docs` (Swagger UI) or contact the backend engineer.*
