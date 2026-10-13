"""Central export of all SWM-ICS domain models and canonical enums.

Normative source: docs/database.md.
"""
from app.models.alert import Alert
from app.models.area import Area
from app.models.audit_event import AuditEvent
from app.models.background_task import BackgroundTask
from app.models.bin_latest_state import BinLatestState
from app.models.calibration import Calibration, SensorConfiguration
from app.models.collection_evidence import CollectionVerification
from app.models.collection_job import CollectionJob
from app.models.depot import Depot
from app.models.device import Device
from app.models.device_bin_assignment import DeviceBinAssignment
from app.models.driver import Driver, DriverLocationPoint
from app.models.enums import (
    AlertSeverity,
    AlertStatus,
    AlertType,
    BackgroundTaskStatus,
    BinStatus,
    BinType,
    DeviceLifecycleState,
    DeviceReportedState,
    DriverStatus,
    FillPriority,
    JobSource,
    JobStatus,
    PredictedPriority,
    RouteObjective,
    RouteStatus,
    SensorHealth,
    TimestampQuality,
    UserRole,
    VehicleStatus,
    VehicleType,
    VerificationOutcome,
)
from app.models.idempotency_record import IdempotencyRecord
from app.models.model_registry import ModelRegistry
from app.models.prediction import Prediction
from app.models.rejected_telemetry_event import RejectedTelemetryEvent
from app.models.route import Route
from app.models.route_stop import RouteStop
from app.models.sensor_reading import SensorReading
from app.models.smart_bin import SmartBin
from app.models.system_setting import SystemSetting
from app.models.user import User
from app.models.vehicle import Vehicle

__all__ = [
    # Models
    "User",
    "Area",
    "SmartBin",
    "Device",
    "DeviceBinAssignment",
    "SensorConfiguration",
    "Calibration",
    "SensorReading",
    "BinLatestState",
    "Vehicle",
    "Driver",
    "DriverLocationPoint",
    "Depot",
    "CollectionJob",
    "Route",
    "RouteStop",
    "CollectionVerification",
    "Alert",
    "BackgroundTask",
    "IdempotencyRecord",
    "AuditEvent",
    "RejectedTelemetryEvent",
    "SystemSetting",
    "Prediction",
    "ModelRegistry",
    # Enums
    "UserRole",
    "BinType",
    "BinStatus",
    "DeviceLifecycleState",
    "DeviceReportedState",
    "SensorHealth",
    "TimestampQuality",
    "FillPriority",
    "PredictedPriority",
    "VehicleType",
    "VehicleStatus",
    "DriverStatus",
    "JobSource",
    "JobStatus",
    "RouteStatus",
    "RouteObjective",
    "VerificationOutcome",
    "AlertSeverity",
    "AlertStatus",
    "AlertType",
    "BackgroundTaskStatus",
]
