"""Unit tests for standalone MQTT worker lifecycle, callbacks, and independence from FastAPI.

Normative source: docs/integration.md §2, §16, §17; docs/testing.md §2.
"""
from unittest.mock import MagicMock, patch
import pytest

from app.workers.mqtt_worker import MQTTWorker


def test_mqtt_worker_can_be_imported_independently():
    """Verify that worker can be imported and instantiated without connecting to a broker."""
    worker = MQTTWorker(
        broker_host="127.0.0.1",
        broker_port=1883,
        client_id="test-worker-import",
    )
    assert worker.broker_host == "127.0.0.1"
    assert worker.broker_port == 1883
    assert worker.telemetry_topic_filter == "smartwaste/device/+/telemetry"
    assert worker.status_topic_filter == "smartwaste/device/+/status"
    assert worker._running is False


def test_fastapi_independence_from_mqtt():
    """Verify that FastAPI application and health check can be imported and executed without MQTT."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"



def test_worker_on_connect_subscribes_to_required_topics():
    worker = MQTTWorker(
        broker_host="127.0.0.1",
        broker_port=1883,
        client_id="test-worker-sub",
        qos=1,
    )
    mock_client = MagicMock()
    # Call _on_connect with reason_code 0 (Success)
    worker._on_connect(mock_client, None, None, 0)

    # Verify both subscriptions were issued with QoS 1
    mock_client.subscribe.assert_any_call("smartwaste/device/+/telemetry", qos=1)
    mock_client.subscribe.assert_any_call("smartwaste/device/+/status", qos=1)


def test_worker_on_message_dispatches_telemetry():
    worker = MQTTWorker(
        broker_host="127.0.0.1",
        broker_port=1883,
    )
    mock_msg = MagicMock()
    mock_msg.topic = "smartwaste/device/ESP32-A123/telemetry"
    mock_msg.payload = b'{"sample": "data"}'

    with patch("app.workers.mqtt_worker.process_telemetry_message") as mock_process:
        mock_process.return_value = MagicMock(outcome="ACCEPTED", reading_id="123")
        worker._on_message(None, None, mock_msg)
        assert mock_process.called
        args, _ = mock_process.call_args
        # First arg is db session, second is topic, third is payload
        assert args[1] == "smartwaste/device/ESP32-A123/telemetry"
        assert args[2] == b'{"sample": "data"}'


def test_worker_on_message_handles_exceptions_gracefully():
    worker = MQTTWorker()
    mock_msg = MagicMock()
    mock_msg.topic = "smartwaste/device/ESP32-A123/telemetry"
    mock_msg.payload = b'{"malformed"'

    with patch("app.workers.mqtt_worker.process_telemetry_message", side_effect=RuntimeError("DB exploded")):
        # Must not raise / crash the worker
        worker._on_message(None, None, mock_msg)


def test_worker_shutdown_stops_client():
    worker = MQTTWorker()
    worker.client = MagicMock()
    worker._running = True

    worker.stop()
    assert worker._running is False
    worker.client.disconnect.assert_called_once()
    worker.client.loop_stop.assert_called_once()
