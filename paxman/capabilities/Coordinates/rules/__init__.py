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


def fold_compact(compact: str) -> str:
    """Fold ``-0`` components in a compact pair string to ``0``.

    Shared -0 identity fold (RFC 5870 §3.3) applied by every rule's
    ``normalize()`` so candidate dedup sees one canonical form. Never
    raises: non-numeric components are passed through unchanged.
    """
    parts = [p.strip() for p in compact.split(",")]
    folded: list[str] = []
    for p in parts:
        try:
            d = Decimal(p)
        except (InvalidOperation, ValueError, AttributeError, TypeError):
            folded.append(p)
            continue
        if d == 0:
            folded.append("0")
        else:
            # normalize without scientific notation
            nd = d.normalize()
            if nd == 0:
                folded.append("0")
            else:
                folded.append(format(nd, "f"))
    return ", ".join(folded)
