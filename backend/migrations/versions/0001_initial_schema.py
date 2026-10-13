"""Initial schema: Core domain models for SWM-ICS

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-13 15:47:00

Normative source: docs/database.md and docs/integration.md.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from geoalchemy2 import Geography, Geometry

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension on PostgreSQL
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # 1. users table
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("firebase_uid", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("SUPER_ADMIN", "OPERATOR", "DRIVER", name="user_role_enum"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firebase_uid"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"])
    op.create_index("idx_users_email", "users", ["email"])

    # 2. areas table
    op.create_table(
        "areas",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("area_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "boundary",
            Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=True,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("area_id"),
    )
    op.create_index("idx_areas_area_id", "areas", ["area_id"])
    op.create_index(
        "idx_areas_boundary", "areas", ["boundary"], postgresql_using="gist"
    )

    # 3. smart_bins table
    op.create_table(
        "smart_bins",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "bin_type",
            sa.Enum(
                "MUNICIPAL",
                "RECYCLING",
                "ORGANIC",
                "HAZARDOUS",
                "OTHER",
                name="bin_type_enum",
            ),
            nullable=False,
            server_default="MUNICIPAL",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "ACTIVE",
                "INACTIVE",
                "MAINTENANCE",
                "RETIRED",
                name="bin_status_enum",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("area_id", sa.Uuid(), nullable=True),
        sa.Column("capacity_kg", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "nominal_full_bin_weight_kg",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.Column(
            "warning_threshold_pct",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="70.00",
        ),
        sa.Column(
            "critical_threshold_pct",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="95.00",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["area_id"], ["areas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bin_id"),
        sa.CheckConstraint(
            "capacity_kg >= 0", name="ck_smart_bins_capacity_kg_positive"
        ),
        sa.CheckConstraint(
            "nominal_full_bin_weight_kg IS NULL OR nominal_full_bin_weight_kg >= 0",
            name="ck_smart_bins_nominal_weight_positive",
        ),
        sa.CheckConstraint(
            "warning_threshold_pct >= 0 AND warning_threshold_pct < critical_threshold_pct AND critical_threshold_pct <= 100",
            name="ck_smart_bins_thresholds",
        ),
    )
    op.create_index("idx_smart_bins_bin_id", "smart_bins", ["bin_id"])
    op.create_index("idx_smart_bins_area_id", "smart_bins", ["area_id"])
    op.create_index(
        "idx_smart_bins_location",
        "smart_bins",
        ["location"],
        postgresql_using="gist",
    )

    # 4. devices table
    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=False),
        sa.Column(
            "lifecycle_state",
            sa.Enum(
                "UNPROVISIONED",
                "PAIRED",
                "ACTIVE",
                "INACTIVE",
                "RETIRED",
                name="device_lifecycle_state_enum",
            ),
            nullable=False,
            server_default="UNPROVISIONED",
        ),
        sa.Column(
            "reported_state",
            sa.Enum(
                "ONLINE",
                "OFFLINE",
                "FAULT",
                "MAINTENANCE",
                name="device_reported_state_enum",
            ),
            nullable=False,
            server_default="OFFLINE",
        ),
        sa.Column("firmware_version", sa.String(length=32), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_rssi_dbm", sa.Integer(), nullable=True),
        sa.Column(
            "sensor_health",
            sa.Enum("OK", "DEGRADED", "FAULT", name="sensor_health_enum"),
            nullable=False,
            server_default="OK",
        ),
        sa.Column("credential_ref", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id"),
    )
    op.create_index("idx_devices_device_id", "devices", ["device_id"])

    # 5. device_bin_assignments table
    op.create_table(
        "device_bin_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_device_bin_assignments_device_id", "device_bin_assignments", ["device_id"]
    )
    op.create_index(
        "idx_device_bin_assignments_bin_id", "device_bin_assignments", ["bin_id"]
    )
    # Partial unique indexes for active 1-to-1 pairing
    op.create_index(
        "uq_active_device_assignment",
        "device_bin_assignments",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.create_index(
        "uq_active_bin_assignment",
        "device_bin_assignments",
        ["bin_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    # 6. sensor_configurations table
    op.create_table(
        "sensor_configurations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column("calibration_version", sa.Integer(), nullable=False),
        sa.Column("empty_distance_cm", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("full_distance_cm", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "sampling_interval_seconds",
            sa.Integer(),
            nullable=False,
            server_default="60",
        ),
        sa.Column(
            "effective_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bin_id", "calibration_version", name="uq_bin_calibration_version"
        ),
        sa.CheckConstraint(
            "empty_distance_cm > full_distance_cm AND full_distance_cm > 0",
            name="ck_sensor_config_distances",
        ),
        sa.CheckConstraint(
            "sampling_interval_seconds > 0",
            name="ck_sensor_config_sampling_interval",
        ),
    )
    op.create_index(
        "idx_sensor_configurations_bin_id", "sensor_configurations", ["bin_id"]
    )

    # 7. sensor_readings table
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "timestamp_quality",
            sa.Enum(
                "DEVICE_SYNCED",
                "SERVER_RECEIVED_FALLBACK",
                name="timestamp_quality_enum",
            ),
            nullable=False,
        ),
        sa.Column("boot_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.String(length=128), nullable=False),
        sa.Column("calibration_version", sa.Integer(), nullable=True),
        sa.Column("distance_cm", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("fill_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("raw_hx711_count", sa.BigInteger(), nullable=True),
        sa.Column("temperature_c", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("humidity_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("rssi_dbm", sa.Integer(), nullable=True),
        sa.Column("battery_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "sensor_health",
            sa.Enum("OK", "DEGRADED", "FAULT", name="sensor_health_enum"),
            nullable=False,
            server_default="OK",
        ),
        sa.Column(
            "sensor_faults",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "quality_flags",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "eligible_for_operations",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("eligibility_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_id",
            "boot_id",
            "sequence",
            name="uq_sensor_readings_device_boot_sequence",
        ),
        sa.CheckConstraint(
            "distance_cm IS NULL OR distance_cm >= 0",
            name="ck_sensor_readings_distance_positive",
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg >= 0",
            name="ck_sensor_readings_weight_positive",
        ),
        sa.CheckConstraint(
            "fill_percent IS NULL OR (fill_percent >= 0 AND fill_percent <= 100)",
            name="ck_sensor_readings_fill_bounds",
        ),
        sa.CheckConstraint(
            "humidity_percent IS NULL OR (humidity_percent >= 0 AND humidity_percent <= 100)",
            name="ck_sensor_readings_humidity_bounds",
        ),
        sa.CheckConstraint(
            "battery_percent IS NULL OR (battery_percent >= 0 AND battery_percent <= 100)",
            name="ck_sensor_readings_battery_bounds",
        ),
    )
    op.create_index(
        "idx_sensor_readings_bin_timestamp",
        "sensor_readings",
        ["bin_id", sa.text("timestamp DESC")],
    )
    op.create_index(
        "idx_sensor_readings_device_timestamp",
        "sensor_readings",
        ["device_id", sa.text("timestamp DESC")],
    )

    # 8. bin_latest_state table
    op.create_table(
        "bin_latest_state",
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column("latest_reading_id", sa.Uuid(), nullable=True),
        sa.Column("latest_event_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fill_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "priority",
            sa.Enum(
                "UNKNOWN",
                "NORMAL",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="fill_priority_enum",
            ),
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column(
            "predicted_priority",
            sa.Enum(
                "NONE",
                "PREDICTED_HIGH",
                "PREDICTED_CRITICAL",
                name="predicted_priority_enum",
            ),
            nullable=False,
            server_default="NONE",
        ),
        sa.Column(
            "sensor_health",
            sa.Enum("OK", "DEGRADED", "FAULT", name="sensor_health_enum"),
            nullable=False,
            server_default="OK",
        ),
        sa.Column(
            "device_reported_state",
            sa.Enum(
                "ONLINE",
                "OFFLINE",
                "FAULT",
                "MAINTENANCE",
                name="device_reported_state_enum",
            ),
            nullable=False,
            server_default="OFFLINE",
        ),
        sa.Column(
            "is_stale",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["latest_reading_id"], ["sensor_readings.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("bin_id"),
    )
    op.create_index(
        "idx_bin_latest_state_priority", "bin_latest_state", ["priority"]
    )

    # 9. vehicles table
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.String(length=64), nullable=False),
        sa.Column(
            "vehicle_type",
            sa.Enum("VAN", "TRUCK", "COMPACTOR", "OTHER", name="vehicle_type_enum"),
            nullable=False,
            server_default="TRUCK",
        ),
        sa.Column("capacity_kg", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "ACTIVE",
                "INACTIVE",
                "MAINTENANCE",
                "RETIRED",
                name="vehicle_status_enum",
            ),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("registration_no", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vehicle_id"),
        sa.CheckConstraint(
            "capacity_kg > 0", name="ck_vehicles_capacity_kg_positive"
        ),
    )
    op.create_index("idx_vehicles_vehicle_id", "vehicles", ["vehicle_id"])

    # 10. drivers table
    op.create_table(
        "drivers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("license_no", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INACTIVE", "ON_LEAVE", name="driver_status_enum"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("driver_id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_drivers_driver_id", "drivers", ["driver_id"])

    # 11. depots table
    op.create_table(
        "depots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("depot_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("depot_id"),
    )
    op.create_index("idx_depots_depot_id", "depots", ["depot_id"])
    op.create_index(
        "idx_depots_location", "depots", ["location"], postgresql_using="gist"
    )

    # 12. routes table
    op.create_table(
        "routes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.String(length=64), nullable=False),
        sa.Column("depot_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=True),
        sa.Column("driver_id", sa.Uuid(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "OPTIMIZED",
                "ASSIGNED",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
                name="route_status_enum",
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column(
            "objective",
            sa.Enum(
                "MIN_DISTANCE",
                "MIN_DURATION",
                "DISTANCE_WITH_PRIORITY",
                name="route_objective_enum",
            ),
            nullable=False,
            server_default="MIN_DISTANCE",
        ),
        sa.Column("distance_m", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("duration_s", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "capacity_safety_factor",
            sa.Numeric(precision=3, scale=2),
            nullable=False,
            server_default="0.90",
        ),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["depot_id"], ["depots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("route_id"),
        sa.CheckConstraint(
            "capacity_safety_factor > 0 AND capacity_safety_factor <= 1.0",
            name="ck_routes_safety_factor",
        ),
    )
    op.create_index("idx_routes_route_id", "routes", ["route_id"])
    op.create_index("idx_routes_depot_id", "routes", ["depot_id"])

    # 13. collection_jobs table
    op.create_table(
        "collection_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("THRESHOLD", "PREDICTION", "MANUAL", name="job_source_enum"),
            nullable=False,
            server_default="THRESHOLD",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "ASSIGNED",
                "EN_ROUTE",
                "ARRIVED",
                "COLLECTING",
                "VERIFIED",
                "ANOMALY",
                "CANCELLED",
                "FAILED",
                name="job_status_enum",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "priority",
            sa.Enum(
                "UNKNOWN",
                "NORMAL",
                "MEDIUM",
                "HIGH",
                "CRITICAL",
                name="fill_priority_enum",
            ),
            nullable=False,
            server_default="NORMAL",
        ),
        sa.Column("route_stop_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("en_route_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collecting_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("idx_collection_jobs_job_id", "collection_jobs", ["job_id"])
    op.create_index("idx_collection_jobs_bin_id", "collection_jobs", ["bin_id"])
    op.create_index(
        "idx_collection_jobs_status_priority",
        "collection_jobs",
        ["status", "priority"],
    )

    # 14. route_stops table
    op.create_table(
        "route_stops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=False),
        sa.Column("collection_job_id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("planned_arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "distance_from_previous_m",
            sa.Numeric(precision=10, scale=2),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["collection_job_id"], ["collection_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_job_id"),
        sa.UniqueConstraint(
            "route_id", "sequence_no", name="uq_route_stops_route_sequence"
        ),
    )
    op.create_index("idx_route_stops_route_id", "route_stops", ["route_id"])
    op.create_index("idx_route_stops_bin_id", "route_stops", ["bin_id"])

    # 15. collection_verifications table
    op.create_table(
        "collection_verifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("before_reading_id", sa.Uuid(), nullable=True),
        sa.Column("after_reading_id", sa.Uuid(), nullable=True),
        sa.Column("otp_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("arrival_lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("arrival_lon", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("finish_lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("finish_lon", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("verify_lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("verify_lon", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("fill_before_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("fill_after_pct", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("weight_before_kg", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("weight_after_kg", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column(
            "outcome",
            sa.Enum("VERIFIED", "ANOMALY", name="verification_outcome_enum"),
            nullable=False,
        ),
        sa.Column(
            "reason_codes",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("overridden_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["after_reading_id"], ["sensor_readings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["before_reading_id"], ["sensor_readings.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["collection_jobs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["overridden_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index(
        "idx_collection_verifications_job_id",
        "collection_verifications",
        ["job_id"],
    )

    # 16. alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.String(length=64), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                "BIN_THRESHOLD",
                "DEVICE_OFFLINE",
                "DEVICE_FAULT",
                "PREDICTED_CRITICAL",
                "AREA_HOTSPOT",
                "COLLECTION_OVERDUE",
                "ROUTE_FAILURE",
                "TELEMETRY_REJECTED",
                "SENSOR_ANOMALY",
                "GPS_OUTSIDE_GEOFENCE",
                "OTP_FAILURE",
                "COLLECTION_ANOMALY",
                "LOW_BATTERY",
                "VEHICLE_OVERLOAD",
                "COMMUNICATION_FAILURE",
                name="alert_type_enum",
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            sa.Enum("INFO", "WARNING", "ERROR", "CRITICAL", name="alert_severity_enum"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "OPEN",
                "ACKNOWLEDGED",
                "RESOLVED",
                "DISMISSED",
                name="alert_status_enum",
            ),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column("bin_id", sa.Uuid(), nullable=True),
        sa.Column("device_id", sa.Uuid(), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "details",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("acknowledged_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_by", sa.Uuid(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["job_id"], ["collection_jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )
    op.create_index("idx_alerts_alert_id", "alerts", ["alert_id"])
    op.create_index("idx_alerts_bin_id", "alerts", ["bin_id"])
    op.create_index("idx_alerts_device_id", "alerts", ["device_id"])
    op.create_index(
        "idx_alerts_status_severity", "alerts", ["status", "severity"]
    )

    # 17. system_settings table
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column(
            "value",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=False,
        ),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column(
            "validation",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("key"),
    )

    # 18. background_tasks table
    op.create_table(
        "background_tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "QUEUED",
                "RUNNING",
                "SUCCEEDED",
                "FAILED",
                "CANCELLED",
                name="background_task_status_enum",
            ),
            nullable=False,
            server_default="QUEUED",
        ),
        sa.Column(
            "progress",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "result_ref",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("idx_background_tasks_task_id", "background_tasks", ["task_id"])

    # 19. idempotency_records table
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column(
            "response_body",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_id", "key", name="uq_idempotency_records_actor_key"
        ),
    )
    op.create_index(
        "idx_idempotency_records_expires_at", "idempotency_records", ["expires_at"]
    )

    # 20. rejected_telemetry_events table
    op.create_table(
        "rejected_telemetry_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=64), nullable=True),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "payload_redacted",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("request_trace_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_rejected_telemetry_events_device_id",
        "rejected_telemetry_events",
        ["device_id"],
    )
    op.create_index(
        "idx_rejected_telemetry_events_received_at",
        "rejected_telemetry_events",
        ["received_at"],
    )

    # 21. driver_location_points table
    op.create_table(
        "driver_location_points",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("driver_id", sa.Uuid(), nullable=False),
        sa.Column("route_id", sa.Uuid(), nullable=True),
        sa.Column(
            "location",
            Geography(geometry_type="POINT", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="GPS"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_driver_location_points_location",
        "driver_location_points",
        ["location"],
        postgresql_using="gist",
    )
    op.create_index(
        "idx_driver_location_points_captured",
        "driver_location_points",
        ["driver_id", sa.text("captured_at DESC")],
    )

    # 22. audit_events table
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "before_diff",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "after_diff",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_audit_events_action", "audit_events", ["action"])
    op.create_index("idx_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index(
        "idx_audit_events_entity", "audit_events", ["entity_type", "entity_id"]
    )

    # 23. predictions table
    op.create_table(
        "predictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bin_id", sa.Uuid(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "horizon_minutes", sa.Integer(), nullable=False, server_default="120"
        ),
        sa.Column(
            "predicted_fill_percent",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
        ),
        sa.Column(
            "predicted_priority",
            sa.Enum(
                "NONE",
                "PREDICTED_HIGH",
                "PREDICTED_CRITICAL",
                name="predicted_priority_enum",
            ),
            nullable=False,
            server_default="NONE",
        ),
        sa.Column("confidence", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="AVAILABLE"),
        sa.ForeignKeyConstraint(["bin_id"], ["smart_bins.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_predictions_bin_id", "predictions", ["bin_id"])

    # 24. model_registry table
    op.create_table(
        "model_registry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=64), nullable=False),
        sa.Column(
            "trained_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("data_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metrics",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
        sa.Column("artifact_uri", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_version"),
    )
    op.create_index("idx_model_registry_model_version", "model_registry", ["model_version"])


def downgrade() -> None:
    # Drop tables in reverse topological order
    op.drop_table("model_registry")
    op.drop_table("predictions")
    op.drop_table("audit_events")
    op.drop_table("driver_location_points")
    op.drop_table("rejected_telemetry_events")
    op.drop_table("idempotency_records")
    op.drop_table("background_tasks")
    op.drop_table("system_settings")
    op.drop_table("alerts")
    op.drop_table("collection_verifications")
    op.drop_table("route_stops")
    op.drop_table("collection_jobs")
    op.drop_table("routes")
    op.drop_table("depots")
    op.drop_table("drivers")
    op.drop_table("vehicles")
    op.drop_table("bin_latest_state")
    op.drop_table("sensor_readings")
    op.drop_table("sensor_configurations")
    op.drop_table("device_bin_assignments")
    op.drop_table("devices")
    op.drop_table("smart_bins")
    op.drop_table("areas")
    op.drop_table("users")

    # Drop custom PostgreSQL enums
    enums_to_drop = [
        "user_role_enum",
        "bin_type_enum",
        "bin_status_enum",
        "device_lifecycle_state_enum",
        "device_reported_state_enum",
        "sensor_health_enum",
        "timestamp_quality_enum",
        "fill_priority_enum",
        "predicted_priority_enum",
        "vehicle_type_enum",
        "vehicle_status_enum",
        "driver_status_enum",
        "route_status_enum",
        "route_objective_enum",
        "job_source_enum",
        "job_status_enum",
        "verification_outcome_enum",
        "alert_type_enum",
        "alert_severity_enum",
        "alert_status_enum",
        "background_task_status_enum",
    ]
    for enum_name in enums_to_drop:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
