"""Pydantic schemas for telemetry data transfer and processing outcomes.

Normative source: docs/integration.md §3, §5, §13.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DeviceReportedState, FillPriority, SensorHealth, TimestampQuality


class ProcessingOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    REJECTED = "REJECTED"
    IGNORED = "IGNORED"


class TelemetryMeasurementsSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    distance_cm: Optional[Decimal] = None
    weight_kg: Optional[Decimal] = None
    temperature_c: Optional[Decimal] = None
    humidity_percent: Optional[Decimal] = None


class TelemetryHealthSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reported_state: DeviceReportedState
    sensor_faults: List[str] = Field(default_factory=list)
    rssi_dbm: Optional[int] = None
    battery_percent: Optional[Decimal] = None


class TelemetryMessageSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    message_id: str
    device_id: str
    boot_id: uuid.UUID
    sequence: int
    timestamp: Optional[datetime] = None
    time_synced: bool
    firmware_version: str
    measurements: TelemetryMeasurementsSchema
    health: TelemetryHealthSchema


class TelemetryProcessingResult(BaseModel):
    outcome: ProcessingOutcome
    reading_id: Optional[uuid.UUID] = None
    bin_id: Optional[uuid.UUID] = None
    device_id: Optional[str] = None
    boot_id: Optional[uuid.UUID] = None
    sequence: Optional[int] = None
    fill_percent: Optional[Decimal] = None
    current_priority: Optional[FillPriority] = None
    sensor_health: Optional[SensorHealth] = None
    reason_code: Optional[str] = None
    detail: Optional[str] = None
