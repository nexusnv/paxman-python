"""ISIN notation — grammar-normalized compact form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISINNotation:
    """ISIN notation — compact plus structured decomposition.

    ``country_code`` 2-letter prefix, uppercased (ISO 3166-1 alpha-2 or
      a special ANNA/DSB prefix such as XS/EU/EZ/XT).
    ``nsin`` 9-character alphanumeric national security identifier,
      uppercased, leading zeros preserved.
    ``check_digit`` single numeric check character at position 12.
    ``compact`` full 12-char string, equals country_code+nsin+check_digit.
    The grammar never computes or validates the check digit and never
      validates prefix membership; rules own both.
    """

    country_code: str  # e.g. "US" — length 2, A-Z
    nsin: str  # e.g. "037833100" — length 9, A-Z0-9
    check_digit: str  # e.g. "5" — length 1, 0-9
    compact: str  # e.g. "US0378331005" — exactly 12, equals cc+nsin+check
