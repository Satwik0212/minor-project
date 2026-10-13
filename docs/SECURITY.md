# Security checklist
- Verify Firebase ID tokens and map to local roles; enforce resource-level authorization.
- Never expose DB/MQTT credentials in browser code.
- Use MQTT/TLS and per-device ACLs; revoke replaced device credentials.
- Validate topic identity, schema, units, timestamp and assignment.
- Bound/redact quarantined payloads; never store secrets.
- Rate-limit OTP; never expose production OTP to drivers.
- Audit settings, calibration, assignments and verification overrides.
- Keep secrets and personal data out of GitHub, logs and test fixtures.
- Test backup restoration and retention.
