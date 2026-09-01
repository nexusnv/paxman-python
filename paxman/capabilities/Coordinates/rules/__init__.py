"""Coordinates validation rules."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

__all__ = [
    "component_in_range",
    "fold_compact",
    "components_valid",
    "normalize_compact",
]


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


def components_valid(notation: object) -> bool:
    """Shared string/Decimal/finite/range gate used by every coordinates rule.

    Validates that latitude/longitude are finite decimal strings within
    their WGS 84 envelopes and that altitude, when present, is a finite
    decimal string. Never raises.
    """

    try:
        lat_str = notation.latitude  # type: ignore[attr-defined]
        lon_str = notation.longitude  # type: ignore[attr-defined]
        if not isinstance(lat_str, str) or not isinstance(lon_str, str):
            return False
        d_lat = Decimal(lat_str)
        d_lon = Decimal(lon_str)
        if not d_lat.is_finite() or not d_lon.is_finite():
            return False
        alt = getattr(notation, "altitude", None)
        if alt is not None:
            if not isinstance(alt, str):
                return False
            d_alt = Decimal(alt)
            if not d_alt.is_finite():
                return False
    except (InvalidOperation, ValueError, AttributeError, TypeError):
        return False
    if not component_in_range(lat_str, "-90", "90"):
        return False
    return component_in_range(lon_str, "-180", "180")


def normalize_compact(notation: object) -> str:
    """Shared never-raise ``normalize()`` used by every coordinates rule."""

    try:
        return fold_compact(notation.compact)  # type: ignore[attr-defined]
    except (InvalidOperation, ValueError, TypeError, AttributeError):
        pass
    try:
        return str(getattr(notation, "compact", ""))
    except Exception:
        return ""
