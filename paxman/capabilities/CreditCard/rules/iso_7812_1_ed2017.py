"""ISO/IEC 7812-1:2017 Section 5 — PAN structure plus Luhn check."""

from __future__ import annotations

import re

from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO/IEC",
    specification_name="ISO/IEC 7812-1:2017",
    kind="specification",
    reference_url="https://www.iso.org/standard/70484.html",
    version="2017",
    lifecycle="active",
    publication_year=2017,
)

# Mirrors the grammar charset: contiguous ASCII digits, 12-19 long.
# Intentional defense-in-depth (the rule must not trust the grammar);
# not shared via import (ISIN _ISIN_RE precedent).
_PAN_RE = re.compile(r"^[0-9]{12,19}$")


def _luhn_valid(digits: str) -> bool:
    """Validate a digit string with modulus 10 Double-Add-Double.

    Weights alternate from the rightmost digit: every second digit
    (indices 1, 3, 5, ... from the right) is doubled, products above 9
    contribute 9 (digit sum via -9). The total must be 0 mod 10.
    """
    total = 0
    for index, digit in enumerate(reversed(digits)):
        value = ord(digit) - 48
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


class Section5PANStructureLuhn(Rule[PANNotation]):
    """ISO/IEC 7812-1:2017 Section 5 — PAN structure plus Luhn check.

    Validates the 12-19 contiguous-ASCII-digit range, notation integrity
    (compact == digits, defense-in-depth), and the modulus 10
    Double-Add-Double check digit (Annex B).
    """

    name = "Section 5-pan-structure-luhn"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "ISO/IEC 7812-1:2017 Section 5 (structure) + Annex B (Luhn MOD-10)"
    target_semantics = frozenset({"pan_recognition"})
    requires_features = frozenset()

    def matches(self, notation: PANNotation, contract: Contract) -> bool:
        digits = notation.digits
        compact = notation.compact
        if not isinstance(digits, str) or not isinstance(compact, str):
            return False
        # Defense-in-depth: the notation is tampered if the two fields
        # disagree (they are built identical by the grammar's emit).
        if compact != digits:
            return False
        if _PAN_RE.match(digits) is None:
            return False
        return _luhn_valid(digits)

    def normalize(self, notation: PANNotation, contract: Contract) -> str:
        return notation.digits
