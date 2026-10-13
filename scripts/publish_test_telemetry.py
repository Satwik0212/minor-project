#!/usr/bin/env python3
"""CLI utility to publish schema-valid test telemetry and status messages to an MQTT broker.

Note: This is a synthetic local development testing utility.
These simulated readings do NOT originate from physical hardware.
Normative source: docs/integration.md §3, §5.
"""
import argparse
from datetime import datetime, timezone
import json
import sys
import uuid

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion


def build_telemetry_payload(
    device_id: str,
    boot_id: str,
    sequence: int,
    distance_cm: float | None = 20.4,
    weight_kg: float | None = 43.5,
    temperature_c: float | None = 31.5,
    humidity_percent: float | None = 61.0,
    reported_state: str = "ONLINE",
    sensor_faults: list[str] | None = None,
    rssi_dbm: int | None = -61,
    battery_percent: float | None = None,
    time_synced: bool = True,
    firmware_version: str = "0.1.0",
) -> dict:
    """Build a canonical telemetry dictionary conforming to mqtt-telemetry-v1.schema.json."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if time_synced else None
    message_id = f"{device_id}:{boot_id}:{sequence}"

    return {
        "schema_version": 1,
        "message_id": message_id,
        "device_id": device_id,
        "boot_id": boot_id,
        "sequence": sequence,
        "timestamp": now_iso,
        "time_synced": time_synced,
        "firmware_version": firmware_version,
        "measurements": {
            "distance_cm": distance_cm,
            "weight_kg": weight_kg,
            "temperature_c": temperature_c,
            "humidity_percent": humidity_percent,
        },
        "health": {
            "reported_state": reported_state,
            "sensor_faults": sensor_faults or [],
            "rssi_dbm": rssi_dbm,
            "battery_percent": battery_percent,
        },
    }


def build_status_payload(
    device_id: str,
    boot_id: str,
    event: str = "ONLINE",
    sensor_faults: list[str] | None = None,
    rssi_dbm: int | None = -61,
    firmware_version: str = "0.1.0",
    reason_code: str | None = None,
) -> dict:
    """Build a canonical status dictionary conforming to mqtt-status-v1.schema.json."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema_version": 1,
        "device_id": device_id,
        "boot_id": boot_id,
        "timestamp": now_iso,
        "event": event,
        "firmware_version": firmware_version,
        "sensor_faults": sensor_faults or [],
        "rssi_dbm": rssi_dbm,
    }
    if reason_code:
        payload["reason_code"] = reason_code
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Publish synthetic test telemetry/status messages to MQTT broker."
    )
    parser.add_argument("--host", default="localhost", help="MQTT broker host (default: localhost)")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port (default: 1883)")
    parser.add_argument("--device-id", default="ESP32-A123", help="Device identifier (default: ESP32-A123)")
    parser.add_argument("--boot-id", default=str(uuid.uuid4()), help="Boot session UUID")
    parser.add_argument("--sequence", type=int, default=0, help="Sequence number (default: 0)")
    parser.add_argument("--type", choices=["telemetry", "status"], default="telemetry", help="Message type")
    parser.add_argument("--distance", type=float, default=20.4, help="Distance in cm")
    parser.add_argument("--weight", type=float, default=43.5, help="Weight in kg")
    parser.add_argument("--temp", type=float, default=31.5, help="Temperature in C")
    parser.add_argument("--humidity", type=float, default=61.0, help="Humidity percentage")
    parser.add_argument("--state", default="ONLINE", choices=["ONLINE", "FAULT", "MAINTENANCE", "REBOOTED"])
    parser.add_argument("--faults", default="", help="Comma-separated sensor fault codes")
    parser.add_argument("--rssi", type=int, default=-61, help="RSSI in dBm")
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2], help="MQTT QoS")

    args = parser.parse_args()

    fault_list = [f.strip() for f in args.faults.split(",") if f.strip()]

    if args.type == "telemetry":
        topic = f"smartwaste/device/{args.device_id}/telemetry"
        payload = build_telemetry_payload(
            device_id=args.device_id,
            boot_id=args.boot_id,
            sequence=args.sequence,
            distance_cm=args.distance,
            weight_kg=args.weight,
            temperature_c=args.temp,
            humidity_percent=args.humidity,
            reported_state=args.state,
            sensor_faults=fault_list,
            rssi_dbm=args.rssi,
        )
    else:
        topic = f"smartwaste/device/{args.device_id}/status"
        payload = build_status_payload(
            device_id=args.device_id,
            boot_id=args.boot_id,
            event=args.state,
            sensor_faults=fault_list,
            rssi_dbm=args.rssi,
        )

    payload_json = json.dumps(payload, indent=2)

    print("=" * 60)
    print("SIMULATED TEST PUBLISHER (NOT originating from physical hardware)")
    print(f"Target Broker: {args.host}:{args.port}")
    print(f"Topic:         {topic} (QoS {args.qos})")
    print(f"Payload:\n{payload_json}")
    print("=" * 60)

    client = mqtt.Client(
        callback_api_version=CallbackAPIVersion.VERSION2,
        client_id=f"test-pub-{uuid.uuid4().hex[:8]}",
        protocol=mqtt.MQTTv311,
    )

    try:
        client.connect(args.host, args.port, keepalive=30)
        client.loop_start()
        info = client.publish(topic, payload_json.encode("utf-8"), qos=args.qos)
        info.wait_for_publish(timeout=5.0)
        print("Message published successfully.")
        client.loop_stop()
        client.disconnect()
    except Exception as exc:
        print(f"Failed to publish message: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
