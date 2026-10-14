## Description
<!-- Provide a clear, concise summary of the changes introduced in this pull request -->

## Motivation & Context
<!-- Why is this change required? What issue or feature does it address? Link relevant issues: e.g. Fixes #123 -->

## Type of Change
- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing contracts/APIs to change)
- [ ] Architecture / Refactoring (no functional API changes)
- [ ] Documentation update
- [ ] CI/CD or Infrastructure update

## Architectural Invariants Verification
- [ ] **Browser Isolation:** Browser interacts only via HTTPS REST (no MQTT or DB credentials exposed)
- [ ] **Decoupled Identity:** `bin_id` and `device_id` remain strictly decoupled
- [ ] **Authoritative Fill Math:** Fill percentages remain server-calculated using versioned calibration
- [ ] **Deduplication:** Telemetry messages adhere to `(device_id, boot_id, sequence)` deduplication
- [ ] **Process Separation:** Ingestion workers remain decoupled from web/API lifespans

## Quality & Testing Checklist
- [ ] Contract compliance with `docs/integration.md` reviewed and maintained
- [ ] Database migration included (if schema modified)
- [ ] Backend automated tests pass (`pytest`): `63+ passed`
- [ ] Frontend automated tests pass (`npm test`): `17+ passed`
- [ ] Frontend builds cleanly (`npm run build`)
- [ ] MQTT schemas validated (`python scripts/validate_mqtt_schemas.py`)
- [ ] Zero secrets, private keys, or credentials committed
- [ ] Documentation and environment examples (`.env.example`) updated
