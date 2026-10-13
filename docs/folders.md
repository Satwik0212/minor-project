# SWM-ICS Repository Structure

```text
swm-ics/
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Makefile
├── docs/
│   ├── README.md
│   ├── features.md
│   ├── frontend.md
│   ├── api.md
│   ├── hardware.md
│   ├── integration.md
│   ├── architecture.md
│   ├── database.md
│   ├── testing.md
│   ├── deployment.md
│   ├── decisions.md
│   ├── schemas/
│   │   ├── mqtt-telemetry-v1.schema.json
│   │   ├── mqtt-status-v1.schema.json
│   │   ├── mqtt-config-v1.schema.json
│   │   └── mqtt-ack-v1.schema.json
│   └── diagrams/
│       ├── mqtt-ingestion-sequence.mmd
│       ├── collection-verification-sequence.mmd
│       └── route-optimization-sequence.mmd
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   └── app/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py
│       │   ├── permissions.py
│       │   ├── errors.py
│       │   └── logging.py
│       ├── db/
│       │   ├── session.py
│       │   ├── base.py
│       │   └── transaction.py
│       ├── models/
│       │   ├── user.py
│       │   ├── area.py
│       │   ├── smart_bin.py
│       │   ├── device.py
│       │   ├── device_bin_assignment.py
│       │   ├── sensor_configuration.py
│       │   ├── sensor_reading.py
│       │   ├── bin_latest_state.py
│       │   ├── vehicle.py
│       │   ├── driver.py
│       │   ├── depot.py
│       │   ├── collection_job.py
│       │   ├── route.py
│       │   ├── route_stop.py
│       │   ├── collection_verification.py
│       │   ├── alert.py
│       │   ├── prediction.py
│       │   ├── model_registry.py
│       │   ├── system_setting.py
│       │   ├── background_job.py
│       │   ├── idempotency_key.py
│       │   ├── rejected_telemetry_event.py
│       │   ├── driver_location_point.py
│       │   └── audit_log.py
│       ├── schemas/
│       │   ├── common.py
│       │   ├── auth.py
│       │   ├── bin.py
│       │   ├── device.py
│       │   ├── reading.py
│       │   ├── calibration.py
│       │   ├── area.py
│       │   ├── analytics.py
│       │   ├── prediction.py
│       │   ├── alert.py
│       │   ├── vehicle.py
│       │   ├── driver.py
│       │   ├── depot.py
│       │   ├── collection.py
│       │   ├── route.py
│       │   ├── settings.py
│       │   ├── reports.py
│       │   └── task.py
│       ├── api/
│       │   └── v1/
│       │       ├── router.py
│       │       └── endpoints/
│       │           ├── health.py
│       │           ├── auth.py
│       │           ├── dashboard.py
│       │           ├── bins.py
│       │           ├── devices.py
│       │           ├── readings.py
│       │           ├── telemetry.py
│       │           ├── areas.py
│       │           ├── analytics.py
│       │           ├── predictions.py
│       │           ├── alerts.py
│       │           ├── vehicles.py
│       │           ├── drivers.py
│       │           ├── depots.py
│       │           ├── collections.py
│       │           ├── routes.py
│       │           ├── settings.py
│       │           ├── reports.py
│       │           └── audit.py
│       ├── services/
│       │   ├── bin_service.py
│       │   ├── device_service.py
│       │   ├── calibration_service.py
│       │   ├── telemetry_service.py
│       │   ├── priority_service.py
│       │   ├── alert_service.py
│       │   ├── candidate_service.py
│       │   ├── collection_service.py
│       │   ├── verification_service.py
│       │   ├── fleet_service.py
│       │   ├── route_service.py
│       │   ├── analytics_service.py
│       │   ├── prediction_service.py
│       │   ├── settings_service.py
│       │   ├── audit_service.py
│       │   └── report_service.py
│       ├── integrations/
│       │   ├── mqtt_client.py
│       │   ├── firebase_auth.py
│       │   ├── osrm_client.py
│       │   ├── otp_delivery.py
│       │   └── map_geocoding.py
│       ├── jobs/
│       │   ├── queue.py
│       │   ├── task_runner.py
│       │   ├── optimize_route.py
│       │   ├── train_model.py
│       │   └── overdue_collection.py
│       └── workers/
│           ├── mqtt_consumer.py
│           └── mqtt_message_handler.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── .env.example
│   └── src/
│       ├── main.js
│       ├── app.js
│       ├── styles/
│       │   ├── tokens.css
│       │   └── app.css
│       ├── api/
│       │   ├── client.js
│       │   ├── auth.js
│       │   ├── bins.js
│       │   ├── readings.js
│       │   ├── analytics.js
│       │   ├── collections.js
│       │   ├── routes.js
│       │   ├── fleet.js
│       │   ├── settings.js
│       │   └── reports.js
│       ├── components/
│       │   ├── AppShell.js
│       │   ├── DataTable.js
│       │   ├── StatusBadge.js
│       │   ├── MetricCard.js
│       │   ├── MapView.js
│       │   ├── ChartCard.js
│       │   ├── ConfirmDialog.js
│       │   └── ErrorState.js
│       ├── pages/
│       │   ├── LoginPage.js
│       │   ├── DashboardPage.js
│       │   ├── LiveMapPage.js
│       │   ├── BinsPage.js
│       │   ├── BinDetailPage.js
│       │   ├── DevicesPage.js
│       │   ├── AnalyticsPage.js
│       │   ├── PredictionsPage.js
│       │   ├── AlertsPage.js
│       │   ├── VehiclesPage.js
│       │   ├── DriversPage.js
│       │   ├── DepotsPage.js
│       │   ├── CollectionsPage.js
│       │   ├── RoutePlannerPage.js
│       │   ├── DriverRoutePage.js
│       │   ├── ReportsPage.js
│       │   ├── SettingsPage.js
│       │   └── AuditPage.js
│       ├── auth/
│       │   ├── firebase.js
│       │   ├── AuthProvider.js
│       │   └── RequireRole.js
│       └── utils/
│           ├── formatters.js
│           ├── validators.js
│           └── enums.js
├── firmware/
│   └── esp32/
│       ├── platformio.ini
│       ├── include/
│       │   ├── config.h
│       │   └── secrets.example.h
│       ├── src/
│       │   ├── main.cpp
│       │   ├── sensors.cpp
│       │   ├── mqtt_transport.cpp
│       │   ├── telemetry_payload.cpp
│       │   ├── device_health.cpp
│       │   └── config_handler.cpp
│       └── test/
│           ├── test_fill_diagnostics.cpp
│           └── test_payload_contract.cpp
├── ops/
│   ├── mosquitto/
│   │   ├── mosquitto.conf
│   │   └── acl.example
│   └── osrm/
│       ├── README.md
│       └── download-and-prepare.sh
└── tests/
    ├── contract/
    ├── api/
    ├── integration/
    └── e2e/
```

## Folder rules

- `api/v1/endpoints/` contains HTTP routing and request/response validation only; domain logic belongs in `services/`.
- `workers/mqtt_consumer.py` is a standalone process. Do not start it in Uvicorn lifespan.
- `jobs/` is the only generic background-task system. `workers/` is only for persistent external consumers.
- `docs/schemas/` is the canonical firmware/backend payload contract; firmware tests should validate against matching fields.
- Frontend is vanilla JavaScript + Vite per the chosen HTML/CSS/JS/Tailwind stack; if the team later chooses React, update this file and dependencies consistently.
- No backend `map_tiles.py`: browser loads tiles directly from the chosen tile provider. OSRM is a backend routing service, not a map-tile service.
