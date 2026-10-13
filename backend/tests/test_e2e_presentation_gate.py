"""End-to-End Presentation Readiness Gate Test Suite.

Verifies the complete Emergency Demo Sprint implementation for tomorrow's presentation:
- Database initialization and schema readiness
- 12-step end-to-end operational sequence using real TestClient
- Real IDs returned by the seed endpoint (no fabrication)
- Calibration inspection and math verification
- Failure cases and boundary conditions
- Operational data isolation during demo reset
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models.area import Area
from app.models.smart_bin import SmartBin
from app.models.device import Device
from app.models.calibration import SensorConfiguration
from app.models.enums import BinStatus, BinType, DeviceLifecycleState, DeviceReportedState, SensorHealth


@pytest.fixture(scope="module")
def test_env():
    """Set up an isolated test database and client for the entire presentation gate."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {
        "client": client,
        "engine": engine,
        "session_factory": TestingSessionLocal,
    }

    app.dependency_overrides.clear()


# ── Step 1: Database Initialization ──────────────────────────────────────────

def test_step_01_db_initialization(test_env):
    """Step 1: Verify database tables initialized according to domain models."""
    engine = test_env["engine"]
    assert len(Base.metadata.tables) == 24, "All 24 domain tables must be present"
    with engine.connect() as conn:
        from sqlalchemy import text
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1


# ── Failure Case: Empty Dataset Behavior ──────────────────────────────────────

def test_failure_empty_dataset_behavior(test_env):
    """Check behavior when no demo data is seeded."""
    client = test_env["client"]

    # Status check
    r_status = client.get("/api/v1/demo/status")
    assert r_status.status_code == 200
    assert r_status.json()["seeded"] is False
    assert r_status.json()["bin_count"] == 0

    # Summary
    r_sum = client.get("/api/v1/bins/summary")
    assert r_sum.status_code == 200
    assert r_sum.json()["total"] == 0
    assert r_sum.json()["active_count"] == 0

    # List
    r_bins = client.get("/api/v1/bins")
    assert r_bins.status_code == 200
    assert r_bins.json()["items"] == []
    assert r_bins.json()["total"] == 0

    # Alerts
    r_alerts = client.get("/api/v1/alerts")
    assert r_alerts.status_code == 200
    assert r_alerts.json()["items"] == []


# ── Step 2: Seed Demo Dataset ─────────────────────────────────────────────────

def test_step_02_seed_demo_dataset(test_env):
    """Step 2: Seed the demo dataset and capture returned results."""
    client = test_env["client"]
    r = client.post("/api/v1/demo/seed")
    assert r.status_code == 200
    data = r.json()
    assert data["seeded"] is True
    assert data["bins_created"] == 5
    assert data["readings_inserted"] == 25
    assert data["alerts_created"] >= 2


# ── Failure Case: Repeated Seeding Idempotency ────────────────────────────────

def test_failure_repeated_seeding_idempotent(test_env):
    """Repeated demo seeding should be idempotent and not create duplicate bins."""
    client = test_env["client"]
    r = client.post("/api/v1/demo/seed")
    assert r.status_code == 200
    data = r.json()
    assert data["seeded"] is True
    assert data["bins_created"] == 0, "Second seed should skip existing bins"


# ── Step 3: Fetch Bin Summary ─────────────────────────────────────────────────

def test_step_03_fetch_bin_summary(test_env):
    """Step 3: Fetch bin summary for dashboard KPI cards."""
    client = test_env["client"]
    r = client.get("/api/v1/bins/summary")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert data["active_count"] == 5
    assert data["simulated_count"] == 5
    assert "CRITICAL" in data["by_priority"]
    assert "HIGH" in data["by_priority"]
    assert "MEDIUM" in data["by_priority"]
    assert "NORMAL" in data["by_priority"]
    assert "UNKNOWN" in data["by_priority"]
    assert data["by_priority"]["CRITICAL"] >= 1


# ── Step 4: Fetch Bin List ────────────────────────────────────────────────────

def test_step_04_fetch_bin_list(test_env):
    """Step 4: Fetch paginated bin list and verify structure."""
    client = test_env["client"]
    r = client.get("/api/v1/bins?page=1&page_size=20")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert len(data["items"]) == 5

    bin_ids = {b["bin_id"] for b in data["items"]}
    assert "BIN-DEMO-001" in bin_ids
    assert "BIN-DEMO-002" in bin_ids
    assert "BIN-DEMO-003" in bin_ids
    assert "BIN-DEMO-004" in bin_ids
    assert "BIN-DEMO-005" in bin_ids

    # All demo bins must be flagged is_simulated = True
    for item in data["items"]:
        assert item["is_simulated"] is True
        assert item["area"]["area_id"] == "AREA-DEMO-001"


# ── Step 5: Fetch Detail and Reading History of a Seeded Bin ──────────────────

def test_step_05_fetch_bin_detail_and_history(test_env):
    """Step 5: Fetch detail and reading history of a seeded bin using its actual bin_id."""
    client = test_env["client"]
    # Test BIN-DEMO-002 (seeded as CRITICAL)
    r = client.get("/api/v1/bins/BIN-DEMO-002")
    assert r.status_code == 200
    b = r.json()
    assert b["bin_id"] == "BIN-DEMO-002"
    assert b["name"] == "Bus Stand East"
    assert b["latest_state"]["priority"] == "CRITICAL"
    assert b["latest_state"]["fill_percent"] is not None
    assert b["latest_state"]["fill_percent"] > 95.0
    assert len(b["recent_readings"]) == 5

    # Test BIN-DEMO-005 (seeded with sensor fault / null fill)
    r5 = client.get("/api/v1/bins/BIN-DEMO-005")
    assert r5.status_code == 200
    b5 = r5.json()
    assert b5["latest_state"]["priority"] == "UNKNOWN"
    assert b5["latest_state"]["fill_percent"] is None
    assert b5["latest_state"]["sensor_health"] == "FAULT"


# ── Step 6: Fetch Collection-Priority View ────────────────────────────────────

def test_step_06_fetch_collection_priority(test_env):
    """Step 6: Fetch collection-priority view and verify descending urgency ordering."""
    client = test_env["client"]
    r = client.get("/api/v1/collection/priority")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    items = data["items"]

    # Verify order: CRITICAL must appear before HIGH, MEDIUM, NORMAL, UNKNOWN
    priorities = [it["priority"] for it in items]
    priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "NORMAL": 3, "UNKNOWN": 4}
    rankings = [priority_order[p] for p in priorities]
    assert rankings == sorted(rankings), f"Priority rankings not sorted: {priorities}"

    # First item must be CRITICAL
    assert items[0]["priority"] == "CRITICAL"
    assert items[0]["bin_id"] == "BIN-DEMO-002"


# ── Step 7: Fetch Alerts List ─────────────────────────────────────────────────

def test_step_07_fetch_alerts_list(test_env):
    """Step 7: Fetch alerts list and verify seeded alerts."""
    client = test_env["client"]
    r = client.get("/api/v1/alerts?status=OPEN")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 2
    alert_ids = [a["alert_id"] for a in data["items"]]
    assert "ALERT-DEMO-BIN-DEMO-002" in alert_ids


# ── Step 8, 9, 10: Manual Reading Submission & State Propagation ──────────────

def test_step_08_09_10_manual_reading_flow(test_env):
    """Steps 8, 9, 10: Submit manual reading, verify agreement, and check collection priority."""
    client = test_env["client"]

    # Check BIN-DEMO-003 baseline state (NORMAL at ~45%)
    r_initial = client.get("/api/v1/bins/BIN-DEMO-003")
    assert r_initial.status_code == 200
    assert r_initial.json()["latest_state"]["priority"] == "NORMAL"

    # Calibration for demo bins: empty_distance_cm = 100, full_distance_cm = 5 (span = 95)
    # Choose distance_cm = 6.0:
    # fill = ((100 - 6) / 95) * 100 = (94 / 95) * 100 = 98.95% -> CRITICAL (> 95%)
    r_inject = client.post("/api/v1/demo/reading", json={
        "bin_id": "BIN-DEMO-003",
        "distance_cm": 6.0,
        "weight_kg": 72.5,
        "temperature_c": 28.0,
    })
    assert r_inject.status_code == 200
    inj = r_inject.json()
    assert inj["bin_id"] == "BIN-DEMO-003"
    assert inj["fill_percent"] == 98.95
    assert inj["priority"] == "CRITICAL"
    assert inj["sensor_health"] == "OK"

    # Step 9: Verify persisted reading, latest bin state, and derived priority agree
    r_detail = client.get("/api/v1/bins/BIN-DEMO-003")
    assert r_detail.status_code == 200
    b_detail = r_detail.json()
    latest = b_detail["latest_state"]
    assert latest["fill_percent"] == 98.95
    assert latest["priority"] == "CRITICAL"
    assert latest["weight_kg"] == 72.5

    # Check recent readings history has new reading at head
    recent = b_detail["recent_readings"]
    assert len(recent) == 6
    assert recent[0]["fill_percent"] == 98.95
    assert recent[0]["distance_cm"] == 6.0
    assert recent[0]["weight_kg"] == 72.5

    # Step 10: Fetch collection-priority view again and verify BIN-DEMO-003 is now in CRITICAL band
    r_prio = client.get("/api/v1/collection/priority")
    assert r_prio.status_code == 200
    prio_items = r_prio.json()["items"]

    critical_bins = [it["bin_id"] for it in prio_items if it["priority"] == "CRITICAL"]
    assert "BIN-DEMO-003" in critical_bins
    assert "BIN-DEMO-002" in critical_bins


# ── Step 11: Alert Acknowledge & Resolve Operations ───────────────────────────

def test_step_11_alert_ack_and_resolve(test_env):
    """Step 11: Exercise alert acknowledge and resolve workflow."""
    client = test_env["client"]

    alert_id = "ALERT-DEMO-BIN-DEMO-002"

    # Verify initial state is OPEN
    r_get = client.get(f"/api/v1/alerts/{alert_id}")
    assert r_get.status_code == 200
    assert r_get.json()["status"] == "OPEN"

    # Acknowledge
    r_ack = client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert r_ack.status_code == 200
    assert r_ack.json()["status"] == "ACKNOWLEDGED"

    # Cannot acknowledge again (conflict)
    r_ack_dup = client.post(f"/api/v1/alerts/{alert_id}/acknowledge")
    assert r_ack_dup.status_code == 409

    # Resolve
    r_res = client.post(f"/api/v1/alerts/{alert_id}/resolve")
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "RESOLVED"

    # Cannot resolve again (conflict)
    r_res_dup = client.post(f"/api/v1/alerts/{alert_id}/resolve")
    assert r_res_dup.status_code == 409

    # Check alert detail reflects resolution
    r_final = client.get(f"/api/v1/alerts/{alert_id}")
    assert r_final.status_code == 200
    assert r_final.json()["status"] == "RESOLVED"
    assert r_final.json()["resolved_at"] is not None


# ── Step 12: Reset Demo Data and Verify Isolation ─────────────────────────────

def test_step_12_reset_demo_data_isolation(test_env):
    """Step 12: Reset demo data and verify that unrelated operational records remain intact."""
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # 1. Insert real operational records with non-demo prefixes
    with SessionLocal() as db:
        prod_area = Area(
            id=uuid.uuid4(),
            area_id="AREA-PROD-999",
            name="Production Metro Zone",
            active=True,
        )
        db.add(prod_area)
        db.flush()

        prod_bin = SmartBin(
            id=uuid.uuid4(),
            bin_id="BIN-PROD-999",
            name="Downtown Commercial Bin",
            bin_type=BinType.MUNICIPAL,
            status=BinStatus.ACTIVE,
            location="POINT(78.0 20.0)",
            area_id=prod_area.id,
            capacity_kg=Decimal("120.00"),
            nominal_full_bin_weight_kg=Decimal("90.00"),
            warning_threshold_pct=Decimal("70.00"),
            critical_threshold_pct=Decimal("95.00"),
        )
        db.add(prod_bin)

        prod_device = Device(
            id=uuid.uuid4(),
            device_id="ESP32-PROD-999",
            lifecycle_state=DeviceLifecycleState.ACTIVE,
            reported_state=DeviceReportedState.ONLINE,
            sensor_health=SensorHealth.OK,
        )
        db.add(prod_device)
        db.commit()

    # 2. Execute demo reset
    r_reset = client.delete("/api/v1/demo/reset")
    assert r_reset.status_code == 200
    reset_data = r_reset.json()
    assert reset_data["deleted_bins"] == 5
    assert reset_data["deleted_areas"] == 1

    # 3. Verify demo bins are gone
    r_demo_bins = client.get("/api/v1/bins?area_id=AREA-DEMO-001")
    assert r_demo_bins.status_code == 200
    assert r_demo_bins.json()["total"] == 0

    # 4. Verify production operational bin and area are completely untouched
    with SessionLocal() as db:
        still_exists_bin = db.query(SmartBin).filter(SmartBin.bin_id == "BIN-PROD-999").first()
        assert still_exists_bin is not None, "Real operational bin must NOT be deleted by demo reset"
        assert still_exists_bin.name == "Downtown Commercial Bin"

        still_exists_area = db.query(Area).filter(Area.area_id == "AREA-PROD-999").first()
        assert still_exists_area is not None, "Real operational area must NOT be deleted by demo reset"

        still_exists_device = db.query(Device).filter(Device.device_id == "ESP32-PROD-999").first()
        assert still_exists_device is not None, "Real operational device must NOT be deleted by demo reset"

    # Clean up test operational records
    with SessionLocal() as db:
        db.query(SmartBin).filter(SmartBin.bin_id == "BIN-PROD-999").delete()
        db.query(Device).filter(Device.device_id == "ESP32-PROD-999").delete()
        db.query(Area).filter(Area.area_id == "AREA-PROD-999").delete()
        db.commit()


# ── Failure Cases: Input Validation, Nulls, Missing Calibration ───────────────

def test_failure_invalid_manual_reading_inputs(test_env):
    """Test rejection of invalid distance inputs."""
    client = test_env["client"]

    # Re-seed demo data for failure testing
    client.post("/api/v1/demo/seed")

    # Negative distance -> 422
    r_neg = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-DEMO-001", "distance_cm": -10.0})
    assert r_neg.status_code == 422

    # Zero distance (ge=1.0) -> 422
    r_zero = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-DEMO-001", "distance_cm": 0.0})
    assert r_zero.status_code == 422

    # Distance > 400 (le=400.0) -> 422
    r_huge = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-DEMO-001", "distance_cm": 450.0})
    assert r_huge.status_code == 422

    # Non-demo bin -> 400
    r_nondemo = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-REAL-001", "distance_cm": 20.0})
    assert r_nondemo.status_code == 400

    # Non-existent demo bin -> 404
    r_notfound = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-DEMO-999", "distance_cm": 20.0})
    assert r_notfound.status_code == 404


def test_failure_null_distance_simulates_fault(test_env):
    """Omission of distance_cm should simulate sensor fault with null fill and UNKNOWN priority."""
    client = test_env["client"]

    r = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-DEMO-001"})
    assert r.status_code == 200
    data = r.json()
    assert data["fill_percent"] is None
    assert data["priority"] == "UNKNOWN"
    assert data["sensor_health"] == "FAULT"

    # Verify latest state
    r_b = client.get("/api/v1/bins/BIN-DEMO-001")
    assert r_b.status_code == 200
    state = r_b.json()["latest_state"]
    assert state["fill_percent"] is None
    assert state["priority"] == "UNKNOWN"
    assert state["sensor_health"] == "FAULT"


def test_failure_invalid_query_parameters(test_env):
    """Test 400 errors on invalid query parameters."""
    client = test_env["client"]

    # Invalid priority on /bins
    r1 = client.get("/api/v1/bins?priority=SUPER_HIGH")
    assert r1.status_code == 400

    # Invalid status on /bins
    r2 = client.get("/api/v1/bins?status=INVALID_STATUS")
    assert r2.status_code == 400

    # Invalid status on /alerts
    r3 = client.get("/api/v1/alerts?status=UNKNOWN_STATUS")
    assert r3.status_code == 400

    # Invalid priority on /collection/priority
    r4 = client.get("/api/v1/collection/priority?priority=INVALID_PRIO")
    assert r4.status_code == 400

    # Non-existent bin detail -> 404
    r5 = client.get("/api/v1/bins/NON-EXISTENT-BIN")
    assert r5.status_code == 404

    # Non-existent alert detail -> 404
    r6 = client.get("/api/v1/alerts/NON-EXISTENT-ALERT")
    assert r6.status_code == 404


def test_failure_missing_calibration(test_env):
    """Verify behavior when a demo bin has no calibration."""
    client = test_env["client"]
    SessionLocal = test_env["session_factory"]

    # Delete calibration for BIN-DEMO-004
    with SessionLocal() as db:
        b4 = db.query(SmartBin).filter(SmartBin.bin_id == "BIN-DEMO-004").first()
        db.query(SensorConfiguration).filter(SensorConfiguration.bin_id == b4.id).delete()
        db.commit()

    # Manual reading injection should return 500
    r = client.post("/api/v1/demo/reading", json={"bin_id": "BIN-DEMO-004", "distance_cm": 25.0})
    assert r.status_code == 500
    assert "No calibration found" in r.json()["detail"]
