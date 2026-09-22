"""LEI notation — grammar-normalized compact form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LEINotation:
    """LEI notation — grammar-normalized compact form.

    ``lou_prefix`` is the 4-char issuer block (positions 1-4), uppercased.
    ``entity_block`` is the 14-char entity-specific block (positions 5-18),
    uppercased, leading zeros preserved. Positions 5-6 carry no enforceable
    constraint (often but not always ``00``).
    ``check_digits`` is the 2-digit MOD 97-10 check string (positions 19-20).
    ``compact`` is the full 20-char string, uppercased, separators stripped,
    equal to ``lou_prefix + entity_block + check_digits``.

    The grammar never computes or validates the check digits (MOD 97-10) and
    never validates LOU membership; rules own both (grammar/rule boundary).
    """

    lou_prefix: str  # e.g. "2138", "5493", "7LTW" — length 4, A-Z0-9
    entity_block: str  # e.g. "00KUD8LAJWSQ9D" — length 14, A-Z0-9
    check_digits: str  # e.g. "15" — length 2, 0-9
    compact: str  # e.g. "213800KUD8LAJWSQ9D15" — exactly 20, ≡ parts
