# Implementation roadmap

1. Repository, local environment, CI and database health.
2. Alembic/PostGIS baseline; users, roles, areas, bins, devices, assignments, calibration, settings and audit.
3. One-bin telemetry vertical slice: broker, separate worker, validation, deduplication, authoritative fill and dashboard.
4. Device health, offline detection, alerts, registry and calibration.
5. Fleet, OSRM matrix, OR-Tools tasks, driver browser workflow, OTP and evidence verification.
6. Analytics/hotspots, then ML only after data sufficiency and time-aware evaluation.
7. Deployment hardening, TLS, ACLs, backups, monitoring and retention.
