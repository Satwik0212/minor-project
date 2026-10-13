# Contributing
- Read `docs/integration.md` before changing API paths, MQTT payloads, units, enums, or state transitions.
- Add migrations and tests with database changes.
- Keep MQTT subscriptions in the separate worker, not FastAPI lifespan.
- Never commit secrets, real personal data, production telemetry, or trained artifacts without approval.
- Update documentation and acceptance criteria alongside implementation.
