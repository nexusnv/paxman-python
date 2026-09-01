"""Coordinates validation rules."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def component_in_range(value: str, lo: str, hi: str) -> bool:
    """Check whether *value* lies within [*lo*, *hi*] inclusive.

    Pure Decimal comparison. Returns False for non-numeric strings or
    any InvalidOperation, never raises.
    """
    try:
        v = Decimal(value)
        low = Decimal(lo)
        high = Decimal(hi)
        return low <= v <= high
    except (InvalidOperation, ValueError, AttributeError, TypeError):
        return False
