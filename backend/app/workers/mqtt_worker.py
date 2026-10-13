"""Standalone supervised MQTT ingestion worker process.

Normative source: docs/integration.md §2, §16, §17; docs/deployment.md §1, §2.
Runs independently from FastAPI / Uvicorn.
"""
import logging
import os
from pathlib import Path
import signal
import sys
import time
from typing import Optional

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion

from app.core.config import settings
from app.db.session import SessionLocal
from app.telemetry.service import process_status_message, process_telemetry_message

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("mqtt_worker")


class MQTTWorker:
    """Supervised MQTT consumer service subscribing to device telemetry and status topics."""

    def __init__(
        self,
        broker_host: Optional[str] = None,
        broker_port: Optional[int] = None,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        ca_cert_path: Optional[str] = None,
        qos: Optional[int] = None,
    ):
        self.broker_host = broker_host or settings.mqtt_broker_host
        self.broker_port = broker_port or settings.mqtt_broker_port
        self.client_id = client_id or settings.mqtt_client_id
        self.username = username or settings.mqtt_username
        self.password = password or settings.mqtt_password
        self.ca_cert_path = ca_cert_path or settings.mqtt_ca_cert_path
        self.qos = qos if qos is not None else settings.mqtt_telemetry_qos

        self.telemetry_topic_filter = "smartwaste/device/+/telemetry"
        self.status_topic_filter = "smartwaste/device/+/status"

        self._running = False
        self.client: mqtt.Client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2,
            client_id=self.client_id,
            protocol=mqtt.MQTTv311,
        )

        self._configure_client()

    def _configure_client(self) -> None:
        """Setup client authentication, TLS, and event callbacks."""
        if self.username:
            self.client.username_pw_set(self.username, self.password)

        if self.ca_cert_path:
            ca_path = Path(self.ca_cert_path)
            if ca_path.exists():
                logger.info("Enabling TLS verification with CA certificate: %s", self.ca_cert_path)
                self.client.tls_set(ca_certs=str(ca_path))
            else:
                logger.warning(
                    "Configured MQTT CA cert path does not exist: %s. Proceeding without TLS.",
                    self.ca_cert_path,
                )

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_subscribe = self._on_subscribe

    def _on_connect(self, client: mqtt.Client, userdata: any, flags: any, reason_code: any, properties: any = None) -> None:
        """Handle connection established to broker."""
        if reason_code == 0:
            logger.info(
                "Connected to MQTT broker at %s:%d (client_id: %s)",
                self.broker_host,
                self.broker_port,
                self.client_id,
            )
            # Subscribe to authorized telemetry and status topics
            client.subscribe(self.telemetry_topic_filter, qos=self.qos)
            client.subscribe(self.status_topic_filter, qos=self.qos)
            logger.info("Subscribed to %s and %s with QoS %d", self.telemetry_topic_filter, self.status_topic_filter, self.qos)
        else:
            logger.error("Failed to connect to MQTT broker, reason_code: %s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata: any, flags: any, reason_code: any, properties: any = None) -> None:
        """Handle disconnection from broker."""
        logger.warning("Disconnected from MQTT broker, reason_code: %s", reason_code)

    def _on_subscribe(self, client: mqtt.Client, userdata: any, mid: int, reason_codes: any, properties: any = None) -> None:
        """Handle topic subscription confirmation."""
        logger.debug("Subscription confirmed: mid=%s, reason_codes=%s", mid, reason_codes)

    def _on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage) -> None:
        """Handle received MQTT message from broker."""
        topic = msg.topic
        payload = msg.payload
        logger.debug("Received MQTT message on %s (%d bytes)", topic, len(payload))

        db = SessionLocal()
        try:
            if topic.endswith("/telemetry"):
                res = process_telemetry_message(db, topic, payload)
                logger.info("Processed telemetry from %s: outcome=%s, reading_id=%s", topic, res.outcome, res.reading_id)
            elif topic.endswith("/status"):
                res = process_status_message(db, topic, payload)
                logger.info("Processed status from %s: outcome=%s", topic, res.outcome)
            else:
                logger.warning("Received message on unhandled topic: %s", topic)
        except Exception as exc:
            logger.error("Unhandled exception processing message on %s: %s", topic, exc, exc_info=True)
        finally:
            db.close()

    def start(self, blocking: bool = True) -> None:
        """Connect to broker and start processing loop."""
        logger.info("Starting MQTT Worker connecting to %s:%d...", self.broker_host, self.broker_port)
        self._running = True
        try:
            self.client.connect(
                self.broker_host,
                self.broker_port,
                keepalive=settings.mqtt_keepalive_seconds,
            )
        except Exception as exc:
            logger.error("Could not establish initial connection to MQTT broker: %s", exc)
            if blocking:
                raise

        if blocking:
            self.client.loop_forever()
        else:
            self.client.loop_start()

    def stop(self) -> None:
        """Gracefully disconnect and stop worker loop."""
        logger.info("Stopping MQTT Worker...")
        self._running = False
        try:
            self.client.disconnect()
            self.client.loop_stop()
        except Exception as exc:
            logger.debug("Error during client shutdown: %s", exc)
        logger.info("MQTT Worker stopped successfully.")


def run_worker() -> None:
    """CLI entrypoint for standalone supervised worker process."""
    worker = MQTTWorker()

    def handle_signal(sig, frame):
        logger.info("Received signal %s, initiating graceful shutdown...", sig)
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        worker.start(blocking=True)
    except KeyboardInterrupt:
        worker.stop()


if __name__ == "__main__":
    run_worker()
