"""Timezone notation - grammar-normalized zone mention plus family discriminator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TimezoneNotation:
    """One timezone mention: canonical-shape carrier plus input family.

    ``key`` is the as-written mention (case-preserved); ``family`` records
    which grammar produced it ("name" or "abbreviation") so rules route
    without re-parsing (documented values only, not Literal-enforced).
    ``compact`` is the normalized candidate (identifier key as-written).
    Offsets live in the sibling UtcOffset capability.
    """

    key: str  # e.g. "America/New_York" or "EST" - as-written, case-preserved
    family: str  # "name" or "abbreviation" - routing discriminator
    compact: str  # normalized candidate (identifier key as-written)
