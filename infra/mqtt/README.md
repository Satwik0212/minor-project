# SWM-ICS MQTT Infrastructure & Ingestion Worker

## 1. Local Development Broker Setup

Start the local Mosquitto MQTT broker using Docker Compose:

```bash
docker compose up -d broker
```

This starts an `eclipse-mosquitto:2` container listening on `localhost:1883` using [mosquitto.local.conf](file:///c:/Users/asus/Downloads/SWM-ICS/infra/mqtt/mosquitto.local.conf).

## 2. Standalone Ingestion Worker

The MQTT worker runs independently from FastAPI/Uvicorn as a separate supervised process.

### Startup Command

```bash
# From repository root or backend/ directory with Python path configured
python -m app.workers.mqtt_worker
```

### Environment Variables

| Variable | Default (Local) | Purpose |
|---|---|---|
| `MQTT_BROKER_HOST` | `localhost` | MQTT Broker hostname or IP |
| `MQTT_BROKER_PORT` | `1883` (dev) / `8883` (TLS) | MQTT Broker port |
| `MQTT_CLIENT_ID` | `swm-ics-worker-local` | Worker client identifier |
| `MQTT_USERNAME` | *(empty)* | Broker service username |
| `MQTT_PASSWORD` | *(empty)* | Broker service password |
| `MQTT_CA_CERT_PATH` | *(empty)* | Path to CA bundle for TLS verification |
| `MQTT_TELEMETRY_TOPIC_TEMPLATE` | `smartwaste/device/{device_id}/telemetry` | Telemetry topic template |
| `MQTT_STATUS_TOPIC_TEMPLATE` | `smartwaste/device/{device_id}/status` | Status topic template |
| `MQTT_TELEMETRY_QOS` | `1` | Subscription QoS (at-least-once) |
| `MQTT_KEEPALIVE_SECONDS` | `60` | Client keepalive interval |
| `DATABASE_URL` | `postgresql+psycopg://...` | Database connection string |

## 3. Synthetic Test Publisher (Local Development)

To test the end-to-end ingestion pipeline without physical hardware:

```bash
# Publish canonical schema-valid telemetry
python scripts/publish_test_telemetry.py --host localhost --port 1883 --device-id ESP32-A123 --distance 55.0

# Publish device status event
python scripts/publish_test_telemetry.py --host localhost --port 1883 --device-id ESP32-A123 --type status --state ONLINE
```

> **Note:** The test publisher emits simulated readings for software verification. It does **not** originate from physical hardware.

## 4. Hardware Teammate Integration Requirements

Before live physical ESP32 devices can connect to a production or staging broker, the hardware teammate must provide / confirm:

1. **Broker Connectivity:**
   - Hostname / IP address of the shared broker.
   - Production port (normally `8883` with TLS).
   - CA Certificate bundle for server authentication.
2. **Device Authentication & Credentials:**
   - Authentication mechanism: Username/Password per device vs. mTLS client certificates (`X.509`).
   - Provisioned credentials for each deployed device ID.
3. **Broker ACLs:**
   - Device ACLs must enforce:
     - `smartwaste/device/{device_id}/telemetry` (write only)
     - `smartwaste/device/{device_id}/status` (write only)
     - `smartwaste/device/{device_id}/ack` (write only)
     - `smartwaste/device/{device_id}/config` (read only)
   - Worker service credentials must have read access to `smartwaste/device/+/telemetry` and `smartwaste/device/+/status`.
4. **Last-Will and Testament (LWT):**
   - Configured on connect to topic `smartwaste/device/{device_id}/status` with payload conforming to `mqtt-status-v1.schema.json`:
     `{"schema_version": 1, "device_id": "{device_id}", "boot_id": "...", "event": "FAULT", "reason_code": "MQTT_UNEXPECTED_DISCONNECT", ...}`

## 5. Known Limitations & Architecture Invariants

- Plain MQTT does not support Kafka-style consumer groups. Horizontal scaling in multi-worker setups requires MQTT 5 shared subscriptions (`$share/group/...`) and relying on the database unique constraint `(device_id, boot_id, sequence)` for concurrency-safe deduplication.
- Live hardware integration has not yet been executed because the physical ESP32 and remote broker credentials have not yet been provided by the hardware teammate.
