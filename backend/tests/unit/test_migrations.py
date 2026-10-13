"""Unit tests verifying Alembic migration script consistency and DDL generation.

Normative source: docs/database.md.
"""
from pathlib import Path
from alembic.config import Config
from alembic import command
import importlib.util


def test_migration_version_file_exists():
    """Verify that the initial migration script exists in backend/migrations/versions."""
    versions_dir = Path(__file__).resolve().parents[2] / "migrations" / "versions"
    migration_files = list(versions_dir.glob("0001_*.py"))
    assert len(migration_files) == 1, "0001 migration file not found in migrations/versions"


def test_migration_revision_metadata():
    """Verify revision metadata in 0001_initial_schema.py."""
    versions_dir = Path(__file__).resolve().parents[2] / "migrations" / "versions"
    migration_file = list(versions_dir.glob("0001_*.py"))[0]

    spec = importlib.util.spec_from_file_location("migration_0001", migration_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.revision == "0001_initial_schema"
    assert mod.down_revision is None
    assert callable(mod.upgrade)
    assert callable(mod.downgrade)


def test_offline_migration_sql_generation(capsys):
    """Verify that Alembic generates complete PostgreSQL/PostGIS DDL without exceptions."""
    ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
    alembic_cfg = Config(str(ini_path))
    alembic_cfg.set_main_option(
        "script_location", str(Path(__file__).resolve().parents[2] / "migrations")
    )

    # Running offline upgrade renders DDL to stdout
    command.upgrade(alembic_cfg, "head", sql=True)
    captured = capsys.readouterr()
    full_sql = captured.out

    assert "CREATE TABLE smart_bins" in full_sql
    assert "CREATE TABLE sensor_readings" in full_sql
    assert "uq_active_device_assignment" in full_sql
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in full_sql

