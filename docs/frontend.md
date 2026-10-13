# SWM-ICS Frontend Specification

## 1. Stack and design

Responsive browser-only app using HTML5, CSS3, JavaScript, Tailwind CSS, Leaflet and OpenStreetMap-compatible tile provider. Use no native mobile app. Driver panel is mobile-responsive in browser.

Visual style: clean civic/operations dashboard, light neutral canvas, dark slate text, teal primary action, restrained green/amber/red status colors, consistent 8px spacing scale, clear typography and dense but readable data tables. Suggested colors: primary teal `#0B6E70` (white-text contrast approximately 6:1), warning text `#8F5F10` (white contrast approximately 5.5:1), danger `#B42318`, neutral text `#1F2937`, surface `#FFFFFF`, background `#F3F4F6`. Verify final palette with automated WCAG contrast checks. Never communicate status by color alone; include text/icon.

Buttons: primary for one main action per page; secondary for alternatives; destructive actions require confirmation and reason; disabled buttons explain why. Show loading, empty, stale, offline, error and success states. Tables need search/filter/sort/pagination; forms show field-level validation and units.

## 2. Roles and navigation

Wire roles: `SUPER_ADMIN`, `OPERATOR`, `DRIVER`.
- Super Admin: full admin, users/roles, settings, audit.
- Operator: bins/devices, monitoring, alerts, analytics, fleet, collections, route planning, reports.
- Driver: assigned route/stops, depart, arrive, OTP start, finish pickup, verify status, own location.

“Admin” can be a display label for SUPER_ADMIN, but APIs use the actual role enum. Operator is a defined role, not optional.

## 3. Page inventory

### Shared
1. Login/session initialization.
2. Access denied/not found.
3. Global app shell with responsive navigation, role-aware menu, notification count and user profile.

### Operator/Super Admin
4. Dashboard — total/active bins, critical/high counts, offline devices, open alerts, pending candidates, active routes; small trends and recent events.
5. Live Map — bins, vehicles and routes; filters by area, status and priority; selected-bin side panel.
6. Bin List — search, area/type/status/priority filters; create/edit/activate/deactivate actions.
7. Bin Detail — latest measurements with units, historical chart, calibration version, device link, health, alert history.
8. Device Registry — pairing, last seen, reported state, derived sensor health, firmware, RSSI, fault codes, replacement flow.
9. Analytics — area/bin/trend summaries, time filters, stale-data disclosure.
10. Hotspots — map clusters, method/time range and cluster counts.
11. Predictions — forecast horizon, model status/version, prediction confidence only if calibrated, data sufficiency warnings.
12. Alerts — severity/type/status filters, acknowledge/resolve/dismiss and audit notes.
13. Vehicles — capacity kg, type, status, assigned route.
14. Drivers — status, assignment, latest location while on duty; access restricted.
15. Depots — map location, create/edit.
16. Collection Queue — candidate source/priority, reason, status, assign/cancel.
17. Route Planner — choose candidates/vehicles/depot/objective; async progress; map/list preview; capacity usage; approve/assign/re-optimize with reason.
18. Route Detail — ordered stops, planned/actual timing, route metrics, linked jobs and status.
19. Reports — collection history, fleet usage, overflow/alert summaries and export.
20. Settings — runtime thresholds, stale timeout, geofence, OTP limits, evidence windows, capacity factor; units, validation, audit.
21. Audit Log — Super Admin; filters by actor/action/entity/date.

### Driver (mobile browser)
22. My Route — assigned route, vehicle, progress and next stop.
23. Stop Detail — bin location, current priority, directions link, arrival/depart controls.
24. Arrival/OTP — GPS permission, geofence status, OTP request/start form; never display production OTP.
25. Pickup Verification — before-reading status, finish-pickup action, waiting-for-new-reading state, verify action and anomaly reasons.
26. Route History/Profile — own completed stops and safe profile/session actions.

## 4. API data mapping

Use `integration.md` and `api.md` as the contract. Important distinctions:
- `fill_percent`: number or null, percent.
- `distance_cm`: number or null, cm.
- `weight_kg`: number or null, kg.
- `temperature_c`: number or null, °C.
- `humidity_percent`: number or null, percent RH.
- `priority` is current priority; `predicted_priority` is separate.
- `reported_state` is device-reported/inferred connectivity; `lifecycle_state` is registry state.
- Timestamps display in local timezone but send UTC ISO-8601.
- Do not infer `0` from null; display “Unavailable”.
- Every response list uses `{items, next_cursor}`.

## 5. Driver collection UI state machine

Only show the action allowed by the current state:
- ASSIGNED → “Start route” (`depart`)
- EN_ROUTE → “Confirm arrival” (`arrive`)
- ARRIVED → “Request OTP” then “Start collection” (`otp/issue`, `start`)
- COLLECTING → show before evidence; “Finish pickup” (`finish`); after fresh telemetry arrives, “Verify collection” (`verify`)
- VERIFIED → success summary
- ANOMALY → reason list and “Request operator review”; no driver override
- CANCELLED/FAILED → terminal message

Disable duplicate clicks while requests are in flight and send idempotency keys. On `409`, refresh job state before offering retry.

## 6. Async tasks

Route optimization and model training return `202` with `task_id`; poll `GET /api/v1/tasks/{task_id}` with bounded backoff. Statuses: QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED. Display actionable errors such as OSRM unavailable or infeasible vehicle capacity.

## 7. Error and accessibility behavior

Handle 400/401/403/404/409/422/429/5xx distinctly. 401 offers re-authentication; 403 shows access denied; 404 offers back navigation; 409 refreshes current state; 422 maps field errors; 429 shows retry-after; 5xx shows retry/correlation ID. Keyboard support, visible focus, labels, semantic headings, screen-reader status announcements and WCAG AA contrast are required.
