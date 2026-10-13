# SWM-ICS Deployment and Operations

## 1. Services

Prototype `docker-compose.yml` should include:
- `api`: FastAPI/Uvicorn REST service.
- `mqtt-worker`: separate supervised MQTT consumer process.
- `db`: PostgreSQL + PostGIS.
- `broker`: Mosquitto or managed MQTT broker (if self-hosted, TLS and ACL configured).
- `task-worker`: background optimization/training worker.
- `osrm`: optional self-hosted OSRM service; otherwise configure a trusted OSRM endpoint.

Do not start MQTT subscriptions from each Uvicorn worker. Plain MQTT has no Kafka consumer groups. Run one worker initially; scale only with MQTT 5 shared subscriptions where supported and idempotent database writes.

## 2. Environment variables

Required deployment variables:
- `DATABASE_URL`
- `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `MQTT_CA_CERT_PATH`, `MQTT_CLIENT_ID`
- `MQTT_TELEMETRY_TOPIC_TEMPLATE`, `MQTT_STATUS_TOPIC_TEMPLATE`, `MQTT_CONFIG_TOPIC_TEMPLATE`, `MQTT_ACK_TOPIC_TEMPLATE`
- `FIREBASE_PROJECT_ID`
- `CORS_ALLOWED_ORIGINS`
- `OSRM_BASE_URL`
- `OTP_DEMO_MODE` (false in production)
- `LOG_LEVEL`

Operational settings such as sampling interval, offline timeout, geofence, OTP TTL/attempts, evidence windows, thresholds and capacity safety factor are stored in `system_settings`. `DEFAULT_*` environment values may seed the DB only on first initialization; the database value wins afterwards. Secrets and service URLs remain environment-managed.

## 3. TLS and secrets

- Use TLS for browser/API and MQTT broker connections.
- Verify MQTT broker certificates; never disable TLS verification in production.
- Store secrets in deployment secret manager or protected environment; do not commit `.env`.
- Provision unique per-device credentials and topic ACLs. Rotate/revoke on replacement.
- Use least-privilege database users per service if practical.
- Firebase ID tokens must be verified server-side; role claims alone from client storage are not trusted.

## 4. Health and monitoring

- `/health/live`: process alive; no dependency checks.
- `/health/ready`: DB and required service readiness.
- Monitor MQTT connected state, last received telemetry, accepted/duplicate/rejected counts, DB errors, task queue age, OSRM failures and route infeasibility.
- Device offline status is inferred from Last-Will or stale telemetry using DB-backed settings.
- Redact tokens, OTPs, passwords and credentials from logs.

## 5. Data and backups

- Back up PostgreSQL on a tested schedule; periodically test restore.
- Keep sensor readings append-only. Calibration corrections are audited derived recalculations.
- Driver location: proposed minimum 10-second interval; detailed route points retained 30 days, then deleted/anonymized. Verification evidence retention is set by team policy.
- Never persist OTP plaintext or raw broker credentials.

## 6. OSRM and maps

For self-hosted OSRM, maintain `ops/osrm/README.md` and preparation scripts, including data region, refresh procedure and licensing. If using external OSRM, handle timeouts, rate limits and failures. The browser loads map tiles directly from a suitable provider; public OSM tile servers are not guaranteed for heavy production traffic.

## 7. Deployment checklist

- Migrations applied and indexes created.
- Schemas validated in CI.
- MQTT ACLs tested with a device credential and denied cross-device topic access.
- Worker runs once independently of API replicas.
- `system_settings` seeded and audit logging verified.
- OTP delivery configured; demo mode disabled in production.
- `/health/live` and `/health/ready` tested.
- OSRM unavailable and infeasible route cases tested.
- Backups and restore procedure verified.
