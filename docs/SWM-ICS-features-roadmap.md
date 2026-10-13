# SWM-ICS --- Component Build Roadmap

> **Purpose:** This document defines the implementation order for the
> entire Smart Waste Management & Intelligent Collection System
> (SWM-ICS) repository. It is a build plan, not merely a list of
> user-facing features.
>
> **Source of truth:** `docs/integration.md` is the normative
> cross-layer contract. Use the architecture, database, API, hardware,
> frontend, deployment, testing, security, decisions, and schema
> documents alongside it. If documents conflict, do not silently invent
> a rule: record the conflict and resolve it before implementing the
> affected component.
>
> **Current baseline:** The repository audit found a substantial
> documentation and scaffold foundation, but most business modules
> remain TODOs. A compiling stub or successful frontend build does not
> count as an implemented component.

## How to use this roadmap

-   Work through the phases in order unless a documented dependency
    justifies a change.
-   Implement and verify one coherent vertical slice at a time.
-   Keep the architecture invariant: the MQTT ingestion worker is a
    separate process from FastAPI/Uvicorn.
-   Do not claim a component is complete merely because its files exist.
-   For each component, record its code, tests, configuration,
    documentation changes, and evidence of verification.
-   Mark each item **NOT STARTED**, **IN PROGRESS**, **BLOCKED**, or
    **VERIFIED**. Use **VERIFIED** only when its acceptance checks
    actually pass.
-   Do not use production credentials, destructive migrations, or
    real-device operations in automated tests.

------------------------------------------------------------------------

## Phase 0 --- Repository baseline and engineering guardrails

### 0.1 Confirm repository structure and contracts

-   [ ] Reconcile the actual repository tree with
    `PROJECT-STRUCTURE.txt` and `docs/folders.md`.
-   [ ] Decide and document the canonical module layout; update
    conflicting structure documentation.
-   [ ] Confirm `docs/integration.md` and the four MQTT schemas are the
    shared contract for firmware, worker, tests, and examples.
-   [ ] Identify every TODO/stub and map it to a roadmap item.
-   [ ] Record unresolved contract decisions instead of guessing.

**Depends on:** Existing repository and Documentation v2.

**Acceptance checks:** Structure documentation matches the repository;
each major subsystem has a roadmap item; contract conflicts are
recorded.

### 0.2 Establish reproducible developer checks

-   [ ] Define consistent commands for backend, routing, ML, frontend,
    firmware, schema validation, and formatting.
-   [ ] Ensure CI does not fail merely because a test directory contains
    no tests; add meaningful tests rather than empty test placeholders.
-   [ ] Configure frontend lint/format tools if their scripts are
    retained.
-   [ ] Verify `.gitignore`, environment examples, and secret-handling
    guidance.
-   [ ] Add or update CI checks as each component becomes testable.

**Depends on:** 0.1.

**Acceptance checks:** A contributor can identify the supported checks;
CI failures clearly distinguish real failures from unavailable
tools/services.

------------------------------------------------------------------------

## Phase 1 --- Database foundation

### 1.1 Implement SQLAlchemy models and relationships

Implement the documented domain models, including at minimum: - \[ \]
Smart bins and stable public bin identifiers. - \[ \] Devices and stable
public device identifiers. - \[ \] Device-to-bin assignments and
active-assignment rules. - \[ \] Calibration records/versions. - \[ \]
Append-only sensor readings. - \[ \] Latest state per bin. - \[ \] Users
and internal roles. - \[ \] System settings. - \[ \] Rejected telemetry
events. - \[ \] All additional entities required by the database
contract, including alerts, collection jobs, routes, vehicles, drivers,
tasks, OTP/evidence, audit records, and analytics/model records where
specified.

Implement UUID keys, foreign keys, nullability, uniqueness, indexes,
checks, and relationships from the contract. Keep `device_id` distinct
from `bin_id`.

### 1.2 Implement PostGIS support

-   [ ] Add documented geographic types and spatial indexes.
-   [ ] Define coordinate validation and storage conventions.
-   [ ] Ensure tests can run against a supported PostgreSQL/PostGIS
    instance.

### 1.3 Configure Alembic and initial migrations

-   [ ] Ensure all intended models are imported into metadata.
-   [ ] Create and manually review the initial migration.
-   [ ] Include required extensions, indexes, and constraints.
-   [ ] Verify upgrade/downgrade behavior against a disposable database
    where available.
-   [ ] Never reset or drop an existing user database.

### 1.4 Test database invariants

-   [ ] Test model metadata and required tables.
-   [ ] Test active assignment uniqueness.
-   [ ] Test nullable measurements and append-only reading design.
-   [ ] Test calibration/version relationships and system settings
    persistence.
-   [ ] Test spatial columns/indexes and migrations with
    PostgreSQL/PostGIS when available.

**Depends on:** Phase 0.

**Acceptance checks:** Schema can be created from migrations; metadata
includes every required model; key constraints are tested; no business
logic relies on an uncreated table.

------------------------------------------------------------------------

## Phase 2 --- Configuration, runtime settings, and observability

### 2.1 Configuration contract

-   [ ] Implement typed application settings and safe local-development
    defaults.
-   [ ] Add the documented MQTT topic templates and other missing
    contract settings.
-   [ ] Keep secrets out of source control.
-   [ ] Validate required production settings at startup.
-   [ ] Document environment variables and their purpose.

### 2.2 Database-backed runtime settings

-   [ ] Seed initial setting values from environment defaults once.
-   [ ] Read runtime values from `system_settings` after initialization.
-   [ ] Add validation for units, ranges, and allowed values.
-   [ ] Record actor, timestamp, and before/after changes in the audit
    trail.
-   [ ] Define behavior if the database or a required setting is
    unavailable.

### 2.3 Logging and health checks

-   [ ] Keep `/health/live` lightweight.
-   [ ] Make `/health/ready` reflect required dependency readiness.
-   [ ] Add structured logs and correlation identifiers where
    appropriate.
-   [ ] Avoid logging credentials, OTPs, or unnecessary personal data.

**Depends on:** Phase 1 for database-backed settings and audit records;
basic configuration work can begin earlier.

**Acceptance checks:** Settings are validated, secret-safe, auditable,
and consistently consumed by components.

------------------------------------------------------------------------

## Phase 3 --- MQTT contract and telemetry ingestion vertical slice

This is the first end-to-end operational slice. Begin with a simulator
or controlled test publisher; connect physical hardware after the
message contract and worker are verified.

### 3.1 Broker and access control

-   [ ] Configure a local MQTT broker for development.
-   [ ] Define TLS and certificate-verification requirements for
    deployed environments.
-   [ ] Configure broker authentication and per-device topic ACLs.
-   [ ] Ensure devices cannot publish or subscribe to another device's
    protected topics.
-   [ ] Document broker hostname, port, credentials mechanism, and topic
    permissions as deployment configuration---not source-code constants.

### 3.2 MQTT payload contract and test fixtures

-   [ ] Validate all canonical JSON Schemas.
-   [ ] Create valid and invalid sample payload fixtures.
-   [ ] Test required fields, types, nullable sensor values, and
    forbidden fields.
-   [ ] Validate topic/payload `device_id` agreement.
-   [ ] Ensure payloads do not assert authoritative `bin_id` or
    `fill_percent`.

### 3.3 Standalone MQTT ingestion worker

-   [ ] Implement a separate worker process using Paho MQTT or the
    approved MQTT client.
-   [ ] Subscribe to the configured telemetry and status topics.
-   [ ] Implement connection, reconnect, shutdown, and broker error
    handling.
-   [ ] Validate payload schema and topic identity.
-   [ ] Deduplicate on `(device_id, boot_id, sequence)`.
-   [ ] Treat QoS 1 delivery as at-least-once; ensure duplicates do not
    create duplicate readings or side effects.
-   [ ] Quarantine invalid, unknown-device, or otherwise rejected
    telemetry with a reason.
-   [ ] Do not run the MQTT subscription loop inside FastAPI/Uvicorn
    lifespan.

### 3.4 Authoritative fill calculation and calibration

-   [ ] Validate calibration constraints:
    `empty_distance_cm > full_distance_cm > 0`.
-   [ ] Calculate fill server-side using the active calibration.
-   [ ] Clamp valid calculations to 0--100%.
-   [ ] Return/store `null` fill when distance or calibration is
    invalid; never convert missing readings to zero.
-   [ ] Store raw measurements, event/received timestamps, calibration
    version, and quality flags.
-   [ ] Keep raw readings append-only.
-   [ ] Update `bin_latest_state` transactionally after accepting a
    valid reading.
-   [ ] Audit any historical recalculation after calibration changes.

### 3.5 Telemetry integration tests

-   [ ] Test valid telemetry from publish to database persistence.
-   [ ] Test duplicate delivery and device reboot with a new `boot_id`.
-   [ ] Test malformed JSON, schema violations, unknown devices, topic
    mismatch, missing distance, and invalid calibration.
-   [ ] Test draft/inactive/maintenance device or bin readings are
    stored with operational eligibility handled according to the
    contract.
-   [ ] Test quarantine and idempotent side effects.

**Depends on:** Phases 1 and 2; Phase 3.1 and 3.2 can proceed while
database work is finishing.

**Acceptance checks:** A test publisher can send one message through the
broker; the standalone worker validates it, deduplicates it, computes
fill where valid, and persists it correctly. Invalid messages are safely
rejected/quarantined. FastAPI remains independent of the MQTT loop.

------------------------------------------------------------------------

## Phase 4 --- Device lifecycle and monitoring

### 4.1 Device registry and assignment operations

-   [ ] Implement device create/update/retire and lifecycle transitions.
-   [ ] Implement bin/device assignment and reassignment with
    transaction-safe constraints.
-   [ ] Require recent valid diagnostics before activation, as
    specified.
-   [ ] Ensure device replacement revokes old credentials/ACLs and
    records actor and reason.

### 4.2 Device status and health derivation

-   [ ] Track reported state, derived sensor health, last seen, RSSI,
    firmware version, fault codes, and battery when available.
-   [ ] Derive `OK`, `DEGRADED`, or `FAULT` according to the contract.
-   [ ] Process status messages and MQTT Last-Will signals.
-   [ ] Implement offline timeout checks using the configured threshold.
-   [ ] Create/update one open `DEVICE_OFFLINE` alert idempotently and
    resolve it when the device resumes.

### 4.3 Alerts and priority rules

-   [ ] Implement current fill priority: `UNKNOWN`, `NORMAL`, `MEDIUM`,
    `HIGH`, `CRITICAL`.
-   [ ] Test exact boundaries: 70%, 85%, and 95%.
-   [ ] Keep predicted priority separate from current priority.
-   [ ] Implement configured per-bin warning/critical thresholds without
    changing standard priority bands.
-   [ ] Implement alert lifecycle, deduplication, acknowledgement,
    resolution, and audit fields.
-   [ ] Add tests for threshold, offline, fault, rejected telemetry, and
    sensor-anomaly alerts.

**Depends on:** Phases 1--3.

**Acceptance checks:** Device state is derived consistently; repeated
events do not create duplicate open alerts; priority boundary tests
pass.

------------------------------------------------------------------------

## Phase 5 --- Backend API, authentication, and authorization

### 5.1 API foundations

-   [ ] Register routers under `/api/v1`.
-   [ ] Keep `/health/live` and `/health/ready` at their documented
    paths.
-   [ ] Apply consistent Pydantic request/response schemas,
    `snake_case`, pagination, error responses, and status codes.
-   [ ] Implement idempotency for mutating operations where the contract
    requires `Idempotency-Key`.
-   [ ] Ensure API responses do not expose internal secrets or untrusted
    raw fields unnecessarily.

### 5.2 Firebase authentication and internal roles

-   [ ] Verify Firebase ID tokens server-side using the approved
    Firebase Admin SDK.
-   [ ] Map verified Firebase identities to local user records.
-   [ ] Enforce `SUPER_ADMIN`, `OPERATOR`, and `DRIVER` permissions.
-   [ ] Deny by default; do not trust role claims supplied by the
    browser.
-   [ ] Test missing, invalid, expired, and unauthorized tokens/roles.

### 5.3 Core read/write APIs

Implement and test APIs for: - \[ \] Bins, locations, current states,
and readings. - \[ \] Devices, statuses, assignments, and
calibrations. - \[ \] Alerts and alert lifecycle. - \[ \] System
settings and audit history. - \[ \] User/role administration as
authorized. - \[ \] Tasks and operational status.

### 5.4 API contract tests

-   [ ] Test authorization for each role and resource.
-   [ ] Test validation failures, not-found responses, conflicts, and
    idempotency.
-   [ ] Verify API schemas agree with documented examples and frontend
    needs.

**Depends on:** Phases 1--4. Some read-only health/API scaffolding can
exist earlier, but domain endpoints depend on models and services.

**Acceptance checks:** Protected endpoints enforce server-verified
identity and role permissions; core resources can be read and changed
through tested APIs.

------------------------------------------------------------------------

## Phase 6 --- Frontend application shell and operational views

### 6.1 Frontend foundation

-   [ ] Keep the browser-only HTML/CSS/JavaScript/Vite approach unless
    an approved decision changes it.
-   [ ] Build a centralized API client with consistent errors,
    authentication, timeout, and request handling.
-   [ ] Add environment-based API configuration.
-   [ ] Add routing/navigation, loading states, empty states, and error
    states.
-   [ ] Keep broker credentials and database access out of the browser.

### 6.2 Authentication and role-based navigation

-   [ ] Integrate Firebase client authentication.
-   [ ] Send ID tokens to the backend as bearer tokens.
-   [ ] Render role-appropriate navigation while relying on backend
    authorization for actual security.
-   [ ] Handle session expiry and unauthorized responses.

### 6.3 Operations dashboard and live map

-   [ ] Build a real dashboard from backend data.
-   [ ] Show bin location, fill, priority, last reading, and device
    health.
-   [ ] Add Leaflet with OpenStreetMap tiles for the live map.
-   [ ] Show stale/unknown data distinctly from valid zero fill.
-   [ ] Add filters for area, status, priority, and device health.
-   [ ] Do not represent mocked readings as live hardware telemetry.

### 6.4 Registry, alert, and settings screens

-   [ ] Build bin/device registry and assignment views.
-   [ ] Build alert list, details, acknowledgement, and resolution
    views.
-   [ ] Build calibration/settings forms with validation and audit
    context.
-   [ ] Add responsive layout and accessible interaction states.

### 6.5 Frontend tests

-   [ ] Test API client behavior, role navigation, loading/error states,
    and critical workflows.
-   [ ] Ensure `npm test` runs meaningful tests rather than failing
    because no test files exist.

**Depends on:** Phases 5.1--5.3 for real domain data; visual scaffolding
can begin earlier.

**Acceptance checks:** Users can sign in, view real bins/readings/alerts
on the dashboard and map, and perform only the operations allowed by
their role.

------------------------------------------------------------------------

## Phase 7 --- Physical ESP32 firmware integration

The MQTT pipeline should already work with a simulator before firmware
is integrated.

### 7.1 Hardware and sensor drivers

-   [ ] Confirm actual ESP32 board, sensor models, pin assignments,
    voltage requirements, and wiring.
-   [ ] Implement ultrasonic distance acquisition and validity checks.
-   [ ] Implement load cell/HX711 acquisition and calibration if used.
-   [ ] Implement BME280/DHT22 acquisition as applicable to the actual
    hardware.
-   [ ] Handle sensor timeouts, invalid values, and hardware faults
    without fabricating zeros.

### 7.2 Device identity and message generation

-   [ ] Configure stable `device_id` separately from physical `bin_id`.
-   [ ] Generate a new UUID `boot_id` per boot.
-   [ ] Increment `sequence` per message.
-   [ ] Generate timestamps from a synchronized clock where supported;
    document behavior when time is unavailable.
-   [ ] Serialize telemetry using the canonical JSON schema.
-   [ ] Keep authoritative fill calculation on the backend.

### 7.3 Secure MQTT transport and reliability

-   [ ] Configure Wi-Fi, TLS certificate validation, and broker
    authentication.
-   [ ] Publish only to authorized device-specific topics.
-   [ ] Handle disconnect/reconnect and bounded buffering or documented
    drop behavior.
-   [ ] Implement configuration messages and acknowledgements if
    required by the contract.
-   [ ] Publish device status and Last-Will behavior.
-   [ ] Avoid committing real credentials or private keys.

### 7.4 Firmware validation

-   [ ] Compile with the documented PlatformIO/ESP-IDF environment.
-   [ ] Test JSON output against shared schema fixtures.
-   [ ] Test sensor failure and broker-disconnect behavior.
-   [ ] Conduct hardware-in-the-loop checks before calling firmware
    integration complete.

**Depends on:** Phases 3.1--3.2 and actual hardware availability; can
proceed in parallel with later backend/frontend work once the contract
is stable.

**Acceptance checks:** A real device publishes schema-valid readings
securely; the worker stores them correctly and reports device health.

------------------------------------------------------------------------

## Phase 8 --- Collection candidates and operational workflow

### 8.1 Candidate generation

-   [ ] Create/update idempotent `PENDING` collection candidates from
    threshold, prediction, or manual sources.
-   [ ] Preserve candidate reason and source reading/prediction.
-   [ ] Do not automatically dispatch a vehicle when a candidate is
    created.
-   [ ] Prevent duplicate candidates for the same bin/rule/window.

### 8.2 Vehicles, drivers, depots, and eligibility

-   [ ] Implement vehicle, driver, depot, availability, and capacity
    records.
-   [ ] Validate coordinates and vehicle capacity units.
-   [ ] Derive load estimates from valid measured weight where
    available.
-   [ ] Otherwise use configured nominal full-bin waste mass and fill
    percentage only when explicitly defined.
-   [ ] Never assume bin volume/capacity is equivalent to waste mass.
-   [ ] Exclude stops with indefensible load estimates from
    capacity-constrained optimization or require an audited operator
    override.

### 8.3 Collection state machine and evidence

-   [ ] Implement documented transitions:
    `PENDING → ASSIGNED → EN_ROUTE → ARRIVED → COLLECTING → VERIFIED` or
    `ANOMALY`.
-   [ ] Enforce authorization, allowed transitions, and conflict
    responses.
-   [ ] Implement depart, arrive, OTP issue, start, finish, verify,
    cancellation/failure, and audited override.
-   [ ] Enforce geofence checks and capture GPS accuracy/time.
-   [ ] Deliver OTP to the registered facility contact; never return
    production OTPs to the driver.
-   [ ] Enforce OTP expiry, attempt limits, rate limits, and audit.
-   [ ] Backend selects before/after readings; clients cannot submit
    trusted reading IDs or measurement values.
-   [ ] Check configured freshness windows and the documented
    fill/weight reduction criteria.
-   [ ] Record anomaly reason codes and audit every override.

### 8.4 Driver and operator screens

-   [ ] Add route/stop assignment views for drivers.
-   [ ] Add navigation, arrival, OTP, start, finish, and verification
    status flows.
-   [ ] Add operator assignment, approval, anomaly review, and override
    interfaces.
-   [ ] Clearly distinguish pending, in-progress, verified, and
    anomalous work.

**Depends on:** Phases 1, 4, and 5; frontend workflow depends on Phase
6.

**Acceptance checks:** Unauthorized/out-of-order transitions are
rejected; evidence is selected server-side; every override is justified
and audited.

------------------------------------------------------------------------

## Phase 9 --- Routing and asynchronous task processing

### 9.1 Task abstraction

-   [ ] Implement persistent or otherwise reliable task records and
    lifecycle.
-   [ ] Expose task status/result/error APIs.
-   [ ] Return `202 Accepted` and a `task_id` for optimization requests.
-   [ ] Define retries, timeout, cancellation, and failure behavior.
-   [ ] Choose the worker/queue technology based on deployment
    constraints and document the decision.

### 9.2 OSRM integration

-   [ ] Implement an OSRM client for road distance/duration matrices.
-   [ ] Validate coordinates and matrix completeness.
-   [ ] Handle service timeouts, unavailable service, invalid
    coordinates, and partial matrices.
-   [ ] Never fabricate route distances or durations.

### 9.3 OR-Tools optimization

-   [ ] Implement CVRP/VRP inputs, vehicles, stops, depot, and
    constraints.
-   [ ] Enforce usable capacity using the configured safety factor,
    proposed default `0.90`.
-   [ ] Support documented objectives: `MIN_DISTANCE`, `MIN_DURATION`,
    and `DISTANCE_WITH_PRIORITY`.
-   [ ] Handle infeasible solutions as structured task failures.
-   [ ] Persist a draft route only when a feasible solution exists.
-   [ ] Preserve route stop order and assign linked jobs/vehicle/driver
    transactionally.
-   [ ] Require operator approval before dispatch.

### 9.4 Routing tests and UI

-   [ ] Test capacity boundaries, infeasible routes, invalid
    coordinates, and OSRM failure.
-   [ ] Test task polling and failure responses.
-   [ ] Add operator route review/approval UI and driver route display.

**Depends on:** Phases 8.1--8.2, 5.4, and task infrastructure; basic
OSRM/solver unit tests can be built with fixtures earlier.

**Acceptance checks:** A valid optimization request returns a task ID; a
feasible solution produces a draft route; failures are explicit and do
not create fabricated routes.

------------------------------------------------------------------------

## Phase 10 --- Analytics, hotspots, and ML

### 10.1 Operational analytics

-   [ ] Aggregate eligible current bin states by area.
-   [ ] Compute counts, mean/median fill, priority counts, and
    stale-device counts.
-   [ ] Aggregate readings into time buckets using event time.
-   [ ] Preserve missing intervals as gaps rather than treating missing
    readings as zero.

### 10.2 Spatial hotspots

-   [ ] Implement documented PostGIS spatial clustering or a documented
    grid/DBSCAN method.
-   [ ] Configure radius/minimum-points parameters and record cluster
    timestamps.
-   [ ] Exclude ineligible/stale data according to the contract.
-   [ ] Avoid claiming meaningful statistical hotspot performance from
    only three prototype bins.

### 10.3 Prediction data pipeline

-   [ ] Select quality-filtered, eligible readings.
-   [ ] Resample by bin/time and create lag/rolling features.
-   [ ] Use chronological train/validation/test splits to avoid leakage.
-   [ ] Establish a simple persistence baseline.
-   [ ] Train and evaluate XGBoost only when data sufficiency criteria
    are met.
-   [ ] Record dataset window, model version, metrics, and training
    configuration.

### 10.4 Prediction serving and model lifecycle

-   [ ] Gate prediction on data coverage and validation quality.
-   [ ] Return `NOT_AVAILABLE` when evidence is insufficient.
-   [ ] Store prediction horizon, timestamp, model version, and
    quality/status.
-   [ ] Test feature parity, leakage prevention, and data-sufficiency
    gates.
-   [ ] Treat a small demo dataset as an integration demonstration, not
    proof of predictive accuracy.

**Depends on:** Phases 1, 3, and 4; ML model work requires adequate
validated history.

**Acceptance checks:** Analytics use eligible data and preserve gaps; ML
does not emit unsupported forecasts; all reported metrics are
reproducible.

------------------------------------------------------------------------

## Phase 11 --- Reports, audit, and operational hardening

### 11.1 Reports and exports

-   [ ] Collection history and verification outcomes.
-   [ ] Route distance/duration and vehicle utilization.
-   [ ] Overflow incidents and bin priority history.
-   [ ] Device uptime, offline periods, and alert resolution.
-   [ ] Define authorized exports and protect sensitive fields.

### 11.2 Audit coverage

-   [ ] Audit settings and role changes.
-   [ ] Audit calibration changes and device/bin assignment/replacement.
-   [ ] Audit route approval, dispatch, cancellation/failure, and
    verification overrides.
-   [ ] Ensure audit records identify actor, time, action, target, and
    meaningful before/after values.

### 11.3 Security and reliability review

-   [ ] Enforce non-default production secrets and fail-safe
    configuration.
-   [ ] Review Firebase verification, RBAC, broker ACLs, TLS, CORS, and
    API input validation.
-   [ ] Review rate limits for OTP and sensitive operations.
-   [ ] Review database pool behavior and readiness endpoint exposure.
-   [ ] Add backups/restore guidance, retention policy, and operational
    runbooks.
-   [ ] Check logs and errors for secret/OTP leakage.
-   [ ] Document threat assumptions and remaining risks.

**Depends on:** Core API, settings, collection, and routing components.

**Acceptance checks:** Sensitive operations are auditable; security
checks and recovery procedures are documented and tested where possible.

------------------------------------------------------------------------

## Phase 12 --- Deployment, end-to-end verification, and release

### 12.1 Local deployment stack

-   [ ] Extend Docker Compose incrementally to the documented required
    services: database, broker, API, MQTT worker, task worker, and OSRM
    where appropriate.
-   [ ] Add health checks, service dependencies, persistent volumes, and
    environment configuration.
-   [ ] Do not expose internal services publicly without a reason.
-   [ ] Document which services are optional or externally hosted.
-   [ ] Provide safe setup and teardown instructions that do not delete
    persistent data by default.

### 12.2 CI and test strategy

-   [ ] Backend unit and integration tests.
-   [ ] Database migration tests against PostgreSQL/PostGIS.
-   [ ] MQTT schema and broker/worker integration tests.
-   [ ] Frontend unit/build tests.
-   [ ] Routing unit tests and deterministic fixtures.
-   [ ] ML data/eligibility tests and reproducible evaluation.
-   [ ] Firmware compile/schema checks and hardware test checklist.
-   [ ] End-to-end tests for telemetry → database → API → dashboard and
    collection workflows.

### 12.3 Release readiness

-   [ ] Run migrations against a fresh disposable database.
-   [ ] Run all applicable test suites and record blocked tests
    honestly.
-   [ ] Verify secrets are absent from repository history and build
    artifacts to the extent feasible.
-   [ ] Verify API and schema compatibility across firmware, worker,
    backend, and frontend.
-   [ ] Verify a device reboot and duplicate MQTT delivery do not
    corrupt state.
-   [ ] Verify invalid telemetry cannot become a false zero-fill
    reading.
-   [ ] Verify routing failures and collection anomalies are visible and
    auditable.
-   [ ] Update README, deployment documentation, known limitations, and
    setup instructions.

**Depends on:** All release-critical components in Phases 1--11.

**Acceptance checks:** A clean environment can follow the documented
deployment procedure; the main end-to-end workflows pass; remaining
limitations are explicit.

------------------------------------------------------------------------

## Dependency overview

``` text
Repository/contract baseline
          |
          v
Database models + PostGIS + migrations
          |
          v
Configuration + runtime settings
          |
          v
MQTT broker + schemas + standalone ingestion worker
          |
          v
Authoritative fill + persisted latest state + device health
          |
          v
Core APIs + Firebase authentication/RBAC
          |
          v
Dashboard + live map + registry + alerts
          |
          v
Collection candidates + vehicles/drivers + verification
          |
          v
Task worker + OSRM + OR-Tools routing
          |
          v
Analytics + hotspots + data-gated ML
          |
          v
Hardening + deployment + end-to-end release verification
```

Firmware development can proceed in parallel once the MQTT contract and
broker requirements are stable. Frontend visual scaffolding can also
proceed in parallel, but integration with real data depends on the APIs.

## Recommended immediate milestone

**Milestone 1: Database foundation.**

Complete Phase 1 first: implement the required SQLAlchemy models,
register all metadata, create and review the initial Alembic migration,
and add meaningful tests. Do not begin the full MQTT worker until the
persistence model and contract-critical constraints are in place.

## Definition of completion for any roadmap item

A component is complete only when: 1. Its behavior is implemented---not
represented by a TODO/docstring stub. 2. Its dependencies and
configuration are documented. 3. Its relevant unit/integration tests are
meaningful and pass in the stated environment. 4. It respects
`docs/integration.md` and shared schemas. 5. Failure paths, invalid
data, and authorization are addressed where applicable. 6. The
completion report cites changed files and actual verification results.

**Never mark a component VERIFIED solely because it compiles, a UI
builds, or a placeholder test passes.**
