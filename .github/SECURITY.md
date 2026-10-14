# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Invariants & Principles

SWM-ICS enforces the following non-negotiable security principles across all layers:

1. **Browser Network Isolation:** The frontend browser dashboard interacts exclusively via authenticated HTTPS REST APIs with the FastAPI backend. It never connects directly to the MQTT broker, the PostgreSQL database, or internal caches.
2. **Transport Layer Security:** All IoT devices publish telemetry over TLS (port 8883) with per-device credentials and broker ACL enforcement.
3. **Payload Identity & Validation:** Telemetry messages are strictly validated against JSON Schema definitions (`docs/schemas/`) and deduplicated on `(device_id, boot_id, sequence)`.
4. **Server-Authoritative Calculation:** Fill levels and priority assignments are strictly server-calculated from calibrated sensor readings. Clients and drivers cannot inject arbitrary fill percentages or reading IDs.
5. **Driver OTP & Geofencing:** Driver collection actions require physical geofence arrival (100m radius) and time-limited, rate-limited OTP verification.
6. **No Secrets in Code:** Never commit passwords, private keys (`.pem`, `.key`), certificates, Firebase service account keys, or production environment files.

## Reporting a Vulnerability

If you discover a security vulnerability within SWM-ICS:

1. **Do not disclose the issue publicly** in GitHub issues, pull requests, or public forums.
2. Please report the issue privately by opening a [GitHub Security Advisory](https://github.com/satwik0212/minor-project/security/advisories/new) or contacting the maintainers directly.
3. Provide a detailed summary including:
   - Affected component(s) (backend, firmware, frontend, routing, MQTT).
   - Clear steps or proof-of-concept to reproduce the behavior.
   - Any potential impact on municipal data or IoT devices.
4. Maintainers will acknowledge receipt within 48 hours and work on a coordinated fix and disclosure schedule.
