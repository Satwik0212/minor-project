# SWM-ICS Documentation v2 — Review Notes

This revision applies the re-check report to the documentation bodies, schemas, and sequence diagrams rather than leaving fixes in a precedence-only addendum.

## Main resolutions

- Rewrote `integration.md` as the canonical cross-layer contract.
- Rewrote the feature, API, hardware, database, architecture, frontend, folder, testing, deployment, decisions, and README documents to match that contract.
- Updated telemetry/status schemas and added config/ack schemas.
- Replaced all three sequence diagrams and added `system-context.mmd`.
- Fixed the collection flow: `depart → arrive → otp/issue → start → finish → verify`; backend selects evidence, and operator override is explicit and audited.
- Standardized IDs, roles, topic naming, fill calculation, priority bands, alert types, task IDs, setting precedence, and worker topology.
- Retired `contract-fixes.md` as an authority; it now points to the canonical docs.

## Deliberately proposed, not validated operational facts

The defaults in `decisions.md` (sampling, thresholds, OTP, geofence, evidence windows, load-estimation assumptions, retention) need team sign-off and hardware testing. Three bins are enough to demonstrate the pipeline but not to claim reliable ML performance or statistically robust hotspot detection.
