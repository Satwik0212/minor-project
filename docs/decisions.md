# SWM-ICS Decisions and Sign-off Register

## Binding project decisions

| Topic | Decision |
|---|---|
| Product | Smart Waste Management & Intelligent Collection System (SWM-ICS) |
| Frontend | Browser-based responsive web application; no dedicated native app |
| Frontend stack | HTML5, CSS3, JavaScript, Tailwind CSS, Leaflet |
| Backend | Python + FastAPI + SQLAlchemy + Pydantic |
| Authentication | Firebase ID-token verification + local role mapping |
| Database | PostgreSQL + PostGIS |
| IoT | ESP32 sensors → MQTT over TLS → separate MQTT worker |
| Telemetry format | JSON, validated against `schemas/mqtt-telemetry-v1.schema.json` |
| Fill authority | Backend computes fill from distance + versioned calibration |
| Device/bin identity | Separate IDs; server-side active assignment |
| Deduplication | `(device_id, boot_id, sequence)` |
| Roles | `SUPER_ADMIN`, `OPERATOR`, `DRIVER`; Operator is a defined role |
| Routing | OSRM road matrix + OR-Tools optimization |
| ML | XGBoost prediction only when sufficient clean history exists |
| REST base | `/api/v1`; operational health endpoints `/health/live`, `/health/ready` |
| Async work | `task_id`, `GET /api/v1/tasks/{task_id}` |
| Collection evidence | Backend selects before/after readings; explicit `/finish` event |

## Proposed defaults requiring team approval

| Setting | Proposed value | Why confirm it |
|---|---:|---|
| Sampling interval | 60 s | Battery/network/storage trade-off |
| Device offline timeout | 180 s | 3× sampling interval; tune for missed packets |
| Warning threshold | 70% | Alert sensitivity |
| Critical threshold | 95% | Operational definition of critical |
| Priority bands | NORMAL <70; MEDIUM 70–85 inclusive; HIGH >85–95 inclusive; CRITICAL >95 | Align UI, tests, reports and alert policy |
| Geofence radius | 100 m | GPS accuracy/site geometry |
| OTP TTL | 300 s | Delivery latency and abuse risk |
| OTP maximum attempts | 5 | Security/usability trade-off |
| Before reading max age | 900 s | Must be aligned to sampling cadence |
| After-reading window | 900 s | Sensor update interval and pickup duration |
| Capacity safety factor | 0.90 | Reserves 10% of nominal vehicle capacity |
| Fill reduction for verification | ≥10 percentage points | Sensor noise / bin geometry |
| Weight reduction for verification | max(2 kg, 10% of before weight) | Load-cell noise and tare error |
| Driver location interval | 10 s minimum | Battery, bandwidth, privacy |
| Detailed driver route retention | 30 days | Privacy and operational audit |

## OTP delivery decision

Production OTP goes to a configured facility contact through a delivery provider selected by the team. Driver requests issue; driver does not receive the OTP through the API. `OTP_DEMO_MODE=true` may expose OTP only in a controlled local demo, never production.

## Remaining team sign-offs

1. Select and configure the OTP delivery channel/provider.
2. Confirm actual sensor models and their plausible measurement ranges, especially ultrasonic blind zone/outdoor enclosure.
3. Confirm sampling interval and offline timeout after a real hardware test.
4. Confirm retention policy for audit, verification locations, and driver location points.
5. Confirm whether weight and environmental sensors are mandatory for activation or optional with null readings.
6. Choose a production map-tile provider; do not assume public OSM tile servers support heavy traffic.
7. Confirm the chosen deployment target and whether OSRM is self-hosted.
8. Confirm if photos are needed for collection proof; photo storage/retention is not in scope until approved.
9. Collect sufficient historical data before claiming ML accuracy or statistically robust hotspot detection.
