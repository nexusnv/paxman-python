"""BIC notation — grammar-normalized compact form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BICNotation:
    """BIC notation — compact plus structured decomposition.

    ``bank_code`` 4-char institution prefix, uppercased, A-Z0-9.
    ``country_code`` 2-letter ISO 3166-1 alpha-2 plus XK, uppercased, A-Z.
    ``location_code`` 2-char location suffix, uppercased, A-Z0-9.
    ``branch_code`` 3-char branch, uppercased, A-Z0-9, or empty when BIC8.
    ``compact`` full BIC 8 or 11, uppercased, equals bank+country+location+branch.
    The grammar never validates country membership or liveness, rules own that.
    """

    bank_code: str  # e.g. "DEUT" — length 4, A-Z0-9
    country_code: str  # e.g. "DE" — length 2, A-Z
    location_code: str  # e.g. "FF" — length 2, A-Z0-9
    branch_code: str  # e.g. "500", "XXX", "" — length 0 or 3, A-Z0-9
    compact: str  # e.g. "DEUTDEFF" or "DEUTDEFF500" — 8 or 11
