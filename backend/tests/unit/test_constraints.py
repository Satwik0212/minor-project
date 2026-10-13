"""Unit tests verifying constraints, indexes, and relationship integrity.

Normative source: docs/database.md §3, docs/integration.md §2, §3, §4, §9.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Area,
    Device,
    DeviceBinAssignment,
    SensorConfiguration,
    SensorReading,
    SmartBin,
    User,
)
from app.models.enums import (
    BinStatus,
    BinType,
    DeviceLifecycleState,
    DeviceReportedState,
    SensorHealth,
    TimestampQuality,
    UserRole,
)


def test_device_bin_assignment_partial_indexes_metadata():
    """Verify that partial unique indexes exist in table args for active assignments."""
    table = DeviceBinAssignment.__table__
    index_names = {idx.name: idx for idx in table.indexes}

    assert "uq_active_device_assignment" in index_names
    assert "uq_active_bin_assignment" in index_names

    dev_idx = index_names["uq_active_device_assignment"]
    bin_idx = index_names["uq_active_bin_assignment"]

    assert dev_idx.unique is True
    assert bin_idx.unique is True
    assert str(dev_idx.dialect_options["postgresql"]["where"]) == "ended_at IS NULL"
    assert str(bin_idx.dialect_options["postgresql"]["where"]) == "ended_at IS NULL"


def test_smart_bin_check_constraints_metadata():
    """Verify check constraints on smart_bins for capacity, nominal weight, and thresholds."""
    table = SmartBin.__table__
    constraint_names = {ck.name for ck in table.constraints if hasattr(ck, "sqltext")}

    assert "ck_smart_bins_capacity_kg_positive" in constraint_names
    assert "ck_smart_bins_nominal_weight_positive" in constraint_names
    assert "ck_smart_bins_thresholds" in constraint_names


def test_calibration_check_constraints_metadata():
    """Verify check constraints on sensor_configurations for valid geometry and sampling interval."""
    table = SensorConfiguration.__table__
    constraint_names = {ck.name for ck in table.constraints if hasattr(ck, "sqltext")}

    assert "ck_sensor_config_distances" in constraint_names
    assert "ck_sensor_config_sampling_interval" in constraint_names


def test_sensor_reading_unique_deduplication_constraint():
    """Verify unique constraint on (device_id, boot_id, sequence) for telemetry deduplication."""
    table = SensorReading.__table__
    unique_constraints = [
        c for c in table.constraints if c.name == "uq_sensor_readings_device_boot_sequence"
    ]
    assert len(unique_constraints) == 1
    cols = [col.name for col in unique_constraints[0].columns]
    assert cols == ["device_id", "boot_id", "sequence"]


def test_in_memory_persistence_and_relationships():
    """Test full model instantiation, persistence, and relationships in an in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Create user
        admin = User(
            id=uuid.uuid4(),
            firebase_uid="fb_test_admin_123",
            email="admin@swm-ics.test",
            role=UserRole.SUPER_ADMIN,
        )
        session.add(admin)

        # Create area
        area = Area(
            id=uuid.uuid4(),
            area_id="AREA-001",
            name="Zone A - Downtown",
        )
        session.add(area)

        # Create smart bin
        bin_obj = SmartBin(
            id=uuid.uuid4(),
            bin_id="BIN-001",
            name="Downtown South",
            bin_type=BinType.MUNICIPAL,
            status=BinStatus.ACTIVE,
            location="POINT(75.8577 22.7196)",
            area_id=area.id,
            capacity_kg=Decimal("150.00"),
            warning_threshold_pct=Decimal("70.00"),
            critical_threshold_pct=Decimal("95.00"),
        )
        session.add(bin_obj)

        # Create device
        device = Device(
            id=uuid.uuid4(),
            device_id="ESP32-A123",
            lifecycle_state=DeviceLifecycleState.ACTIVE,
            reported_state=DeviceReportedState.ONLINE,
            firmware_version="0.1.0",
        )
        session.add(device)

        # Create assignment
        assignment = DeviceBinAssignment(
            id=uuid.uuid4(),
            device_id=device.id,
            bin_id=bin_obj.id,
            assigned_by=admin.id,
            reason="Initial deployment",
        )
        session.add(assignment)

        # Create versioned calibration
        calib = SensorConfiguration(
            id=uuid.uuid4(),
            bin_id=bin_obj.id,
            calibration_version=1,
            empty_distance_cm=Decimal("100.00"),
            full_distance_cm=Decimal("10.00"),
            sampling_interval_seconds=60,
            created_by=admin.id,
        )
        session.add(calib)

        # Create append-only reading
        boot_id = uuid.uuid4()
        reading = SensorReading(
            id=uuid.uuid4(),
            bin_id=bin_obj.id,
            device_id=device.id,
            timestamp=datetime.now(timezone.utc),
            timestamp_quality=TimestampQuality.DEVICE_SYNCED,
            boot_id=boot_id,
            sequence=0,
            message_id=f"ESP32-A123:{boot_id}:0",
            calibration_version=1,
            distance_cm=Decimal("55.00"),
            fill_percent=Decimal("50.00"),
            weight_kg=Decimal("25.40"),
            sensor_health=SensorHealth.OK,
            sensor_faults=[],
            quality_flags=[],
            eligible_for_operations=True,
        )
        session.add(reading)
        session.commit()

        # Query back and verify relationships
        queried_bin = session.query(SmartBin).filter_by(bin_id="BIN-001").one()
        assert queried_bin.area.name == "Zone A - Downtown"
        assert len(queried_bin.assignments) == 1
        assert queried_bin.assignments[0].device.device_id == "ESP32-A123"
        assert len(queried_bin.sensor_configurations) == 1
        assert queried_bin.sensor_configurations[0].empty_distance_cm == Decimal("100.00")
        assert len(queried_bin.readings) == 1
        assert queried_bin.readings[0].fill_percent == Decimal("50.00")
