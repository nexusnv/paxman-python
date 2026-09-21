"""ISO 6166:2021 Section 4 — ISIN structure plus check digit."""

from __future__ import annotations

import re

from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 6166:2021",
    kind="specification",
    reference_url="https://www.iso.org/standard/78502.html",
    version="2021",
    lifecycle="active",
    publication_year=2021,
)

# Mirrors the grammar charset: 2 letters + 9 alphanumerics + 1 numeric check
# digit = exactly 12. Intentional defense-in-depth (the rule must not trust
# the grammar); not shared via import.
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def _expand(compact: str) -> str:
    """Expand each character to its numeric value (digits stay, A=10 ... Z=35)."""
    parts: list[str] = []
    for ch in compact:
        if "0" <= ch <= "9":
            parts.append(ch)
        else:
            parts.append(str(ord(ch) - 55))
    return "".join(parts)


def _luhn_valid(expanded: str) -> bool:
    """Validate an expanded digit string with modulus 10 Double-Add-Double.

    Weights alternate over the expanded string from the rightmost digit:
    every second digit (indices 1, 3, 5, ... from the right) is doubled,
    products above 9 contribute their digit sum. The total must be 0 mod 10.
    """
    total = 0
    for index, digit in enumerate(reversed(expanded)):
        value = ord(digit) - 48
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


class Section4IsinStructureCheckDigit(Rule[ISINNotation]):
    """ISO 6166:2021 Section 4 — ISIN structure plus check digit.

    Validates length exactly 12, charset per position, head/tail
    consistency with the decomposed fields, and the modulus 10
    Double-Add-Double check digit over the letter-expanded payload.
    """

    name = "Section 4-isin-structure-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = (
        "Structure clause + normative check-digit annex (modulus 10 Double-Add-Double)"
    )
    target_semantics = frozenset({"isin_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISINNotation, contract: Contract) -> bool:
        compact = notation.compact
        if not isinstance(compact, str):
            return False
        if len(compact) != 12:
            return False
        if _ISIN_RE.match(compact) is None:
            return False
        if not notation.country_code.isalpha():
            return False
        if not notation.check_digit.isdigit():
            return False
        if compact != (notation.country_code + notation.nsin + notation.check_digit):
            return False
        return _luhn_valid(_expand(compact))

    def normalize(self, notation: ISINNotation, contract: Contract) -> str:
        return notation.compact
