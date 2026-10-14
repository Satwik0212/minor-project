# SWM-ICS — Feature and Module Implementation Status

**Audit Date:** 2026-10-14  
**Classification Standard:** Normative tags (`VERIFIED`, `CODE-VERIFIED`, `PARTIAL`, `SCAFFOLDED`, `PLANNED`, `BLOCKED`, `CONTRADICTED`, `UNKNOWN`).

---

## 1. Domain Models & Database Layer

| Component / Table | Implementation Location | Current Behavior | Status | Verification Evidence | Remaining Work | Dependencies | Responsible Layer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Declarative Base & Shims** | `backend/app/db/base.py` | Defines `Base`, compiles GeoAlchemy2 types to `TEXT` on SQLite, registers dummy SQLite spatial UDFs | `VERIFIED` | `tests/unit/test_models.py`, `tests/unit/test_constraints.py` passing | Add `geoalchemy2` to `pyproject.toml` | SQLAlchemy, GeoAlchemy2 | Backend |
| **Session Management** | `backend/app/db/session.py` | Configures engine with `check_same_thread=False` for SQLite and `pool_pre_ping=True`, yields session in `get_db()` | `VERIFIED` | Dependency override in `tests/test_e2e_presentation_gate.py` | Configure connection pooling for PostgreSQL | SQLAlchemy | Backend |
| **User & Role Model** | `backend/app/models/user.py` | `users` table: UUID PK, `firebase_uid`, `email`, `role`, `active` | `CODE-VERIFIED` | Model imports in `tests/unit/test_models.py` | User management endpoints and role checks | None | Backend |
| **Area Model** | `backend/app/models/area.py` | `areas` table: UUID PK, `area_id` (UQ), `name`, `boundary` (MultiPolygon) | `VERIFIED` | 1 row in `demo.db` (`AREA-DEMO-001`), verified in e2e gate tests | PostGIS polygon boundary queries | GeoAlchemy2 | Backend |
| **Smart Bin Model** | `backend/app/models/smart_bin.py` | `smart_bins` table: UUID PK, `bin_id` (UQ), `name`, `status`, `capacity_kg`, thresholds | `VERIFIED` | 5 rows in `demo.db` (`BIN-DEMO-001`–`005`), e2e tests | Area assignment validation | Models | Backend |
| **Device Model** | `backend/app/models/device.py` | `devices` table: UUID PK, `device_id` (UQ), `lifecycle_state`, `reported_state`, `sensor_health` | `VERIFIED` | 5 rows in `demo.db` (`ESP32-DEMO-001`–`005`) | Provisioning APIs | Models | Backend |
| **Device-Bin Assignment** | `backend/app/models/device_bin_assignment.py` | `device_bin_assignments` table: partial unique active index per device and bin | `VERIFIED` | Active assignment unique constraint verified in `tests/unit/test_constraints.py` | Device swap & replacement workflow | Bins, Devices | Backend |
| **Sensor Configuration** | `backend/app/models/calibration.py` | `sensor_configurations` table: versioned calibration (`empty_distance_cm > full_distance_cm > 0`) | `VERIFIED` | Check constraint verified in `tests/unit/test_constraints.py` | Recalculation API & audit logging | Smart Bins | Backend |
| **Sensor Readings** | `backend/app/models/sensor_reading.py` | `sensor_readings` table: append-only telemetry, deduplication UQ `(device_id, boot_id, sequence)` | `VERIFIED` | 27 rows in `demo.db`; dedup verified in `test_constraints.py` | Retention and partitioning policy | Telemetry | Backend |
| **Latest Bin State** | `backend/app/models/bin_latest_state.py` | `bin_latest_state` table: latest fill projection, priority, health, `is_stale` | `VERIFIED` | 5 rows in `demo.db`; verified in e2e presentation gate tests | Real-time event bus / websockets | Readings | Backend |
| **Alerts Model** | `backend/app/models/alert.py` | `alerts` table: UUID PK, `alert_id` (UQ), `type`, `severity`, `status`, `details` JSONB | `VERIFIED` | 2 rows in `demo.db`; verified in e2e tests | Alert rule engine for all 15 alert types | Bins, Devices | Backend |
| **Vehicles & Drivers** | `backend/app/models/vehicle.py`, `driver.py` | `vehicles`, `drivers`, `driver_location_points` tables | `CODE-VERIFIED` | Tables created in `demo.db` (0 rows) | Fleet CRUD and live GPS location stream | Users | Backend |
| **Depots & Routes** | `backend/app/models/depot.py`, `route.py`, `route_stop.py` | `depots`, `routes`, `route_stops` tables | `CODE-VERIFIED` | Tables created in `demo.db` (0 rows) | Route generation & assignment sync | Vehicles, Jobs | Backend |
| **Collection Workflow Models** | `backend/app/models/collection_job.py`, `collection_evidence.py` | `collection_jobs`, `collection_verifications` tables | `CODE-VERIFIED` | Tables created in `demo.db` (0 rows) | State machine transitions and OTP verification | Smart Bins | Backend |
| **Background Tasks & Audit** | `backend/app/models/background_task.py`, `audit_event.py`, `idempotency_record.py` | `background_tasks`, `audit_events`, `idempotency_records` tables | `CODE-VERIFIED` | Tables created in `demo.db` (0 rows) | Task queue integration, audit interceptor | None | Backend |
| **ML & Settings Models** | `backend/app/models/prediction.py`, `model_registry.py`, `system_setting.py`, `rejected_telemetry_event.py` | `predictions`, `model_registry`, `system_settings`, `rejected_telemetry_events` tables | `CODE-VERIFIED` | Tables created in `demo.db` (0 rows) | Model training runner, settings API | None | Backend |
| **Alembic Migration** | `backend/migrations/versions/0001_initial_schema.py` | Generates complete PostgreSQL DDL offline; applies schema online | `VERIFIED` (Offline) / `PARTIAL` | `tests/unit/test_migrations.py` passing | Live online verification against PostgreSQL | PostgreSQL | Backend |

---

## 2. Telemetry Ingestion & Business Logic

| Component | Implementation Location | Current Behavior | Status | Verification Evidence | Remaining Work | Dependencies | Responsible Layer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Fill Level Math** | `backend/app/telemetry/fill_calculation.py` | Calculates fill percentage with clamping and exact priority boundaries | `VERIFIED` | 5 unit tests passing in `tests/unit/test_fill_calculation.py` | None (canonical math complete) | None | Backend |
| **Telemetry Validation** | `backend/app/telemetry/validation.py` | Validates JSON schemas, deduplication keys, sensor plausibility, timestamps | `VERIFIED` | 13 unit tests passing in `tests/unit/test_telemetry_validation.py` | None | jsonschema | Backend |
| **Telemetry Service** | `backend/app/telemetry/service.py` | Resolves active bin, loads calibration, persists readings, updates latest state | `VERIFIED` | 8 unit tests passing in `tests/unit/test_telemetry_service.py` | Connect to live MQTT worker loop | Models, DB | Backend |
| **MQTT Ingestion Worker** | `backend/app/workers/mqtt_worker.py` | Standalone Paho MQTT daemon subscribing to telemetry and status topics | `PARTIAL` | 6 unit tests passing in `tests/unit/test_mqtt_worker.py` with mock client | Run with live broker; handle reconnects | Mosquitto | Infrastructure / Backend |
| **Device Offline Detection** | `backend/app/monitoring/health_rules.py` | Evaluates device silence against `device_offline_after_seconds` | `SCAFFOLDED` | 80-byte stub file with TODO docstring | Implement periodic scheduled worker | Telemetry, DB | Backend |
| **Collection Verification Rule** | `backend/app/collections/verification.py` | Evaluates arrival geofence + OTP + before/after sensor drop | `SCAFFOLDED` | 81-byte stub file with TODO docstring | Implement verification engine | Collections | Backend |

---

## 3. API Routers & Endpoints

| Endpoint | Router / File | Responsibility | Status | Verification Evidence | Remaining Work | Responsible Layer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `GET /health/live`, `/health/ready` | `backend/app/api/v1/endpoints/health.py` | Operational liveness & DB readiness checks | `VERIFIED` | `tests/unit/test_health.py` passing | None | Backend |
| `GET /api/v1/bins` | `backend/app/api/v1/endpoints/bins.py` | Paginated bin listing with priority & status filters | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_02_bins_endpoint_returns_seeded_bins` | Area boundary joining | Backend |
| `GET /api/v1/bins/summary` | `backend/app/api/v1/endpoints/bins.py` | Aggregate counts by priority and status for KPI cards | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_03_bins_summary_counts` | None | Backend |
| `GET /api/v1/bins/{bin_id}` | `backend/app/api/v1/endpoints/bins.py` | Detailed bin view with last 20 readings | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_04_bin_detail_endpoint` | None | Backend |
| `GET /api/v1/collection/priority` | `backend/app/api/v1/endpoints/alerts.py` | Priority queue ordered from CRITICAL to NORMAL | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_05_collection_priority_ordering` | Add vehicle capacity constraints | Backend |
| `GET /api/v1/alerts` | `backend/app/api/v1/endpoints/alerts.py` | Filterable alerts ledger | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_06_alerts_endpoint` | Alert generation rules | Backend |
| `POST /api/v1/alerts/{id}/acknowledge` | `backend/app/api/v1/endpoints/alerts.py` | Transition alert OPEN -> ACKNOWLEDGED | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_07_alert_acknowledgement` | Role check | Backend |
| `POST /api/v1/alerts/{id}/resolve` | `backend/app/api/v1/endpoints/alerts.py` | Transition alert -> RESOLVED | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_08_alert_resolution` | Role check | Backend |
| `GET /api/v1/demo/status` | `backend/app/api/v1/endpoints/demo.py` | Check demo seeding state | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_01_demo_seed_endpoint` | None | Backend |
| `POST /api/v1/demo/seed` | `backend/app/api/v1/endpoints/demo.py` | Seeds 5 bins, 5 devices, 25 readings, 2 alerts | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_01_demo_seed_endpoint` | Disable in production | Backend |
| `DELETE /api/v1/demo/reset` | `backend/app/api/v1/endpoints/demo.py` | Deletes only `DEMO-` prefixed records | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_12_demo_reset_endpoint` | Disable in production | Backend |
| `POST /api/v1/demo/reading` | `backend/app/api/v1/endpoints/demo.py` | Manual reading simulation with server fill calculation | `VERIFIED` | `test_e2e_presentation_gate.py::test_step_09_manual_simulated_reading_injection` | None | Backend |
| `POST /api/v1/collections/*` | `backend/app/collections/router.py` | Collection dispatch, departure, arrival, OTP, verification | `SCAFFOLDED` | 75-byte stub file with TODO docstring | Complete router implementation | Backend |
| `POST /api/v1/routes/*` | `backend/app/routes/router.py` | Route optimization request and assignment approval | `SCAFFOLDED` | 70-byte stub file with TODO docstring | Complete router implementation | Backend |
| `GET /api/v1/tasks/{task_id}` | `backend/app/tasks/router.py` | Polling for async background job execution | `SCAFFOLDED` | 69-byte stub file with TODO docstring | Complete router implementation | Backend |
| `GET /api/v1/analytics/*` | `backend/app/analytics/router.py` | Historical fill trends and PostGIS hotspot clustering | `SCAFFOLDED` | 73-byte stub file with TODO docstring | Complete router implementation | Backend |
| `POST /api/v1/auth/*` | `backend/app/auth/` | Firebase token verification and session exchange | `SCAFFOLDED` | 70-byte stub files with TODO docstrings | Complete auth module | Backend |

---

## 4. Frontend Application

| View / Component | Implementation Location | Current Behavior | Status | Verification Evidence | Remaining Work | Responsible Layer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Application Shell** | `frontend/index.html`, `frontend/src/main.js` | Topbar with connectivity indicator, sidebar navigation, toast notifications | `VERIFIED` | Interactive SPA execution; `vite build` succeeds | Add responsive mobile drawer toggle | Frontend |
| **Vite Reverse Proxy** | `frontend/vite.config.js` | Proxies `/api` and `/health` requests to `http://127.0.0.1:8000` | `VERIFIED` | Network requests resolve without CORS errors | Commit to Git repository | Frontend |
| **Operations Dashboard** | `frontend/src/main.js` (`showDashboard`) | 6 KPI tiles, top attention bins list, recent open alerts list, seed shortcut | `VERIFIED` | Live rendering against backend API | Visual sparkline graphs | Frontend |
| **Smart Bins View** | `frontend/src/main.js` (`showBins`) | Paginated bin table, priority & status filters, fill meter bars | `VERIFIED` | Filtering, pagination, and sorting functional | Leaflet map view integration | Frontend |
| **Bin Detail Drawer** | `frontend/src/main.js` (`openBinDetail`) | Sliding side panel with full metadata, fill meter, readings history & chart | `VERIFIED` | Tested with live and simulated readings | Calibration parameter editing | Frontend |
| **Reading Simulation Modal**| `frontend/src/main.js` (`openSimModal`) | Modal form submitting simulated distance to backend calculation API | `VERIFIED` | Live submissions update bin fill % and priority | Add weight/temp simulation inputs | Frontend |
| **Priority Queue & Alerts**| `frontend/src/main.js` (`showPriority`) | Ordered collection queue and alerts ledger with acknowledge/resolve buttons | `VERIFIED` | Interactive alert state transitions functional | Bulk action controls | Frontend |
| **Frontend Automated Tests**| `frontend/src/tests/` | None | `SCAFFOLDED` | `npm test` fails with code 1 (`No test files found`) | Add Vitest component and helper tests | Frontend |

---

## 5. IoT Hardware & Firmware

| Subsystem | Implementation Location | Current Behavior | Status | Verification Evidence | Remaining Work | Responsible Layer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ESP32 Firmware Core** | `firmware/esp32/src/main.cpp` | 5 lines: empty `setup()` and `loop()` with 1000ms delay | `SCAFFOLDED` | File inspection (168 bytes) | Implement full sensor and Wi-Fi logic | Hardware / Firmware |
| **Ultrasonic Driver** | `firmware/esp32/` | Not implemented | `PLANNED` | No driver code exists | HC-SR04 driver with median pulse filter | Firmware |
| **Load Cell Driver** | `firmware/esp32/` | Not implemented | `PLANNED` | No driver code exists | HX711 calibration and taring routines | Firmware |
| **TLS MQTT Client** | `firmware/esp32/` | Not implemented | `PLANNED` | No MQTT code in firmware | Paho / PubSubClient with certificate pinning | Firmware |
| **NVS Boot UUID & Seq** | `firmware/esp32/` | Not implemented | `PLANNED` | No NVS storage routines | Generate persistent boot UUID, increment sequence | Firmware |
| **Synthetic MQTT Publisher** | `scripts/publish_test_telemetry.py`| CLI tool publishing schema-valid test telemetry over MQTT | `VERIFIED` | Script code inspection (6,042 bytes) | None (utility complete) | Infrastructure |

---

## 6. Optimization, Analytics & Machine Learning

| Subsystem | Implementation Location | Current Behavior | Status | Verification Evidence | Remaining Work | Responsible Layer |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OSRM Client** | `routing/src/osrm_client.py` | 43-byte stub file with TODO docstring | `SCAFFOLDED` | File inspection | HTTP client for distance/duration matrix | Backend / Routing |
| **OR-Tools VRP Solver** | `routing/src/optimizer.py` | 41-byte stub file with TODO docstring | `SCAFFOLDED` | File inspection | Implement CVRP solver with capacity constraints | Backend / Routing |
| **Async Task Runner** | `backend/app/jobs/runner.py` | 56-byte stub file with TODO docstring | `SCAFFOLDED` | File inspection | Background worker for long-running VRP jobs | Backend |
| **Spatial Hotspots** | `backend/app/analytics/hotspots.py` | 75-byte stub file with TODO docstring | `SCAFFOLDED` | File inspection | PostGIS spatial clustering query | Backend / Analytics |
| **ML Feature Engineering** | `ml/src/features/` | Empty stub directories | `SCAFFOLDED` | Directory inspection | Lag and rolling window feature extraction | Data / ML |
| **ML Training Pipeline** | `ml/src/training/train.py` | 49-byte stub file with TODO docstring | `SCAFFOLDED` | File inspection | XGBoost fill-forecasting script | Data / ML |
| **Model Registry** | `ml/artifacts/` | Empty directory with `.gitkeep` | `SCAFFOLDED` | Directory inspection | Artifact storage and model version tracking | Data / ML |
