"""Authoritative server-side fill percentage calculation and priority determination.

Normative source: docs/integration.md §4, §6, §7; docs/testing.md §3.
"""
from decimal import Decimal, InvalidOperation
import math
from typing import Any, List, Optional

from app.models.enums import FillPriority, SensorHealth

CRITICAL_SENSOR_FAULTS = {
    "ULTRASONIC_TIMEOUT",
    "ULTRASONIC_OUT_OF_RANGE",
}


def is_finite_number(val: Any) -> bool:
    """Check if value is a real finite numeric value (not NaN or Inf)."""
    if val is None:
        return False
    try:
        f = float(val)
        return not math.isnan(f) and not math.isinf(f)
    except (ValueError, TypeError, OverflowError):
        return False


def calculate_fill_percent(
    distance_cm: Optional[Any],
    empty_distance_cm: Any,
    full_distance_cm: Any,
) -> Optional[Decimal]:
    """Calculate authoritative fill percentage from ultrasonic distance and calibration.

    Formula:
        fill_percent = clamp(((empty_distance_cm - distance_cm) / (empty_distance_cm - full_distance_cm)) * 100, 0, 100)

    Requirements:
        - empty_distance_cm > full_distance_cm > 0 (finite positive values)
        - distance_cm must be positive and finite
        - Returns None when measurement or calibration is invalid/missing (never coerces to 0)
        - Output is clamped to [0.00, 100.00] and quantized to 2 decimal places.
    """
    if distance_cm is None:
        return None

    if not is_finite_number(distance_cm) or not is_finite_number(empty_distance_cm) or not is_finite_number(full_distance_cm):
        return None

    try:
        dist = Decimal(str(distance_cm))
        empty = Decimal(str(empty_distance_cm))
        full = Decimal(str(full_distance_cm))
    except (InvalidOperation, ValueError, TypeError):
        return None

    # Validate calibration constraints
    if full <= 0 or empty <= full:
        return None

    # Validate distance measurement range (must be positive)
    if dist <= 0:
        return None

    # Calculate fill percentage
    try:
        raw_fill = ((empty - dist) / (empty - full)) * Decimal("100")
        clamped = max(Decimal("0.00"), min(Decimal("100.00"), raw_fill))
        return clamped.quantize(Decimal("0.01"))
    except (InvalidOperation, ZeroDivisionError):
        return None


def determine_current_priority(fill_percent: Optional[Any]) -> FillPriority:
    """Determine current fill priority according to canonical band rules.

    Canonical bands from docs/integration.md §7:
        - null / invalid -> UNKNOWN
        - fill < 70 -> NORMAL
        - 70 <= fill <= 85 -> MEDIUM (at exact 85, priority is MEDIUM)
        - 85 < fill <= 95 -> HIGH (at exact 95, priority is HIGH)
        - fill > 95 -> CRITICAL
    """
    if fill_percent is None or not is_finite_number(fill_percent):
        return FillPriority.UNKNOWN

    try:
        fill = Decimal(str(fill_percent))
    except (InvalidOperation, ValueError, TypeError):
        return FillPriority.UNKNOWN

    if fill < Decimal("70"):
        return FillPriority.NORMAL
    elif fill <= Decimal("85"):
        return FillPriority.MEDIUM
    elif fill <= Decimal("95"):
        return FillPriority.HIGH
    else:
        return FillPriority.CRITICAL


def derive_sensor_health(
    distance_cm: Optional[Any],
    sensor_faults: Optional[List[str]] = None,
) -> SensorHealth:
    """Derive sensor health from distance availability and reported sensor faults.

    Normative rules from docs/integration.md §6:
        - OK when no faults and distance is usable.
        - DEGRADED when at least one optional sensor fault exists, but distance/fill is usable.
        - FAULT when fill-critical ultrasonic data is unavailable or critical faults reported.
    """
    faults = set(sensor_faults or [])

    # If critical ultrasonic faults are reported or distance is missing
    if distance_cm is None or not is_finite_number(distance_cm) or float(distance_cm) <= 0:
        return SensorHealth.FAULT

    if bool(faults & CRITICAL_SENSOR_FAULTS):
        return SensorHealth.FAULT

    # If non-critical faults exist (e.g. load cell, env sensor)
    if len(faults) > 0:
        return SensorHealth.DEGRADED

    return SensorHealth.OK
