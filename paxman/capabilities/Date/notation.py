"""Date notation — position-sensitive intermediate representation for date values."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DateNotation:
    """Position-sensitive date notation with N1, N2, N3 components.

    The positional mapping depends on which grammar produced this notation:
    - ISO 8601:  N1=year, N2=month, N3=day  (YYYY-MM-DD)
    - US:        N1=month, N2=day, N3=year   (MM/DD/YYYY)
    - European:  N1=day, N2=month, N3=year    (DD/MM/YYYY)

    Attributes:
        N1: First component (year or month or day depending on grammar).
        N2: Second component (month or day).
        N3: Third component (day or year).
    """

    N1: str
    N2: str
    N3: str
