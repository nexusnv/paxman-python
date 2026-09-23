"""CreditCard notation — the recognized PAN (primary account number)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PANNotation:
    """A recognized primary account number.

    Attributes:
        digits: The PAN as contiguous ASCII digits (12-19), the canonical
            payload this notation carries.
        compact: Separator-free copy of ``digits``; always equals
            ``digits`` (re-checked by the structure rule as
            defense-in-depth).
    """

    digits: str
    compact: str
