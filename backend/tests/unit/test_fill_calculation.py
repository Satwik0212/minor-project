"""Unit tests for authoritative server-side fill percentage calculation and priority bands.

Normative source: docs/integration.md §4, §6, §7; docs/testing.md §3.
"""
from decimal import Decimal
import math
import pytest

from app.models.enums import FillPriority, SensorHealth
from app.telemetry.fill_calculation import (
    calculate_fill_percent,
    derive_sensor_health,
    determine_current_priority,
)


def test_fill_calculation_boundaries():
    empty = 100.0
    full = 10.0

    # At empty distance: 0% fill
    fill_empty = calculate_fill_percent(100.0, empty, full)
    assert fill_empty == Decimal("0.00")

    # At full distance: 100% fill
    fill_full = calculate_fill_percent(10.0, empty, full)
    assert fill_full == Decimal("100.00")

    # At midpoint (55 cm): 50% fill
    fill_mid = calculate_fill_percent(55.0, empty, full)
    assert fill_mid == Decimal("50.00")


def test_fill_calculation_clamping():
    empty = 100.0
    full = 10.0

    # Distance beyond empty (waste level below bottom): clamped to 0.00%
    fill_below = calculate_fill_percent(120.0, empty, full)
    assert fill_below == Decimal("0.00")

    # Distance closer than full (heap overflowing top): clamped to 100.00%
    fill_overflow = calculate_fill_percent(5.0, empty, full)
    assert fill_overflow == Decimal("100.00")


def test_fill_calculation_invalid_or_missing_inputs():
    # Missing distance must return None (never zero)
    assert calculate_fill_percent(None, 100.0, 10.0) is None

    # Negative distance is physically invalid
    assert calculate_fill_percent(-5.0, 100.0, 10.0) is None

    # Invalid calibration: empty <= full
    assert calculate_fill_percent(50.0, 10.0, 100.0) is None
    assert calculate_fill_percent(50.0, 50.0, 50.0) is None

    # Invalid calibration: full <= 0
    assert calculate_fill_percent(50.0, 100.0, 0.0) is None
    assert calculate_fill_percent(50.0, 100.0, -10.0) is None

    # Non-finite inputs
    assert calculate_fill_percent(float("nan"), 100.0, 10.0) is None
    assert calculate_fill_percent(float("inf"), 100.0, 10.0) is None
    assert calculate_fill_percent(50.0, float("nan"), 10.0) is None
    assert calculate_fill_percent(50.0, 100.0, float("inf")) is None


def test_exact_priority_thresholds():
    """Verify priority bands matching docs/testing.md §3."""
    # null -> UNKNOWN
    assert determine_current_priority(None) == FillPriority.UNKNOWN

    # fill < 70 -> NORMAL
    assert determine_current_priority(0.0) == FillPriority.NORMAL
    assert determine_current_priority(69.99) == FillPriority.NORMAL

    # 70 <= fill <= 85 -> MEDIUM
    assert determine_current_priority(70.0) == FillPriority.MEDIUM
    assert determine_current_priority(80.0) == FillPriority.MEDIUM
    assert determine_current_priority(85.0) == FillPriority.MEDIUM  # exact 85 is MEDIUM

    # 85 < fill <= 95 -> HIGH
    assert determine_current_priority(Decimal("85.01")) == FillPriority.HIGH
    assert determine_current_priority(90.0) == FillPriority.HIGH
    assert determine_current_priority(95.0) == FillPriority.HIGH  # exact 95 is HIGH

    # fill > 95 -> CRITICAL
    assert determine_current_priority(Decimal("95.01")) == FillPriority.CRITICAL
    assert determine_current_priority(100.0) == FillPriority.CRITICAL


def test_sensor_health_derivation():
    # Clean distance with no faults -> OK
    assert derive_sensor_health(20.4, []) == SensorHealth.OK
    assert derive_sensor_health(20.4, None) == SensorHealth.OK

    # Non-critical fault with usable distance -> DEGRADED
    assert derive_sensor_health(20.4, ["LOAD_CELL_NOT_READY"]) == SensorHealth.DEGRADED
    assert derive_sensor_health(20.4, ["ENV_SENSOR_READ_FAILED"]) == SensorHealth.DEGRADED

    # Missing distance -> FAULT
    assert derive_sensor_health(None, []) == SensorHealth.FAULT

    # Critical ultrasonic fault -> FAULT
    assert derive_sensor_health(20.4, ["ULTRASONIC_TIMEOUT"]) == SensorHealth.FAULT
    assert derive_sensor_health(20.4, ["ULTRASONIC_OUT_OF_RANGE"]) == SensorHealth.FAULT
