"""UTC offset notation - grammar-normalized canonical offset form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UtcOffsetNotation:
    """One UTC offset mention: canonical ``+HH:MM`` carrier.

    ``compact`` is the normalized candidate in canonical extended form
    (e.g. "+05:30"; "Z" normalizes to "+00:00").
    """

    compact: str  # e.g. "+05:30" - canonical extended form +HH:MM
