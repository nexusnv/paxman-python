"""GS1 General Specifications Release 26.0 — GTIN structure + Mod-10 check."""

from __future__ import annotations

from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="GS1",
    specification_name="GS1 General Specifications",
    kind="specification",
    reference_url="https://ref.gs1.org/standards/genspecs/",
    version="26.0",
    lifecycle="active",
    publication_year=2026,
)


def _gs1_mod10_is_valid(digits: str) -> bool:
    """GS1 Mod-10 check (weights 3/1 rightmost-anchored, check last)."""
    if len(digits) < 2:
        return False
    total = sum(
        int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1]))
    )
    return int(digits[-1]) == (10 - total % 10) % 10


class Section1GtinStructureCheckDigit(Rule[GTINNotation]):
    """GS1 GenSpecs Section 1 — GTIN structure plus Mod-10 check digit."""

    name = "Section 1-gtin-structure-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 1 (GTIN structure + Mod-10 check digit)"
    target_semantics = frozenset({"gtin_recognition"})
    requires_features = frozenset()

    def matches(self, notation: GTINNotation, contract: Contract) -> bool:
        """Check whether the notation is a valid GTIN with Mod-10 check."""
        digits = notation.digits
        if not isinstance(digits, str):
            return False
        if len(digits) not in (8, 12, 13, 14):
            return False
        if notation.native_length != len(digits):
            return False
        if not digits.isascii() or not digits.isdigit():
            return False
        return _gs1_mod10_is_valid(digits)

    def normalize(self, notation: GTINNotation, contract: Contract) -> str:
        """Normalize to the 14-digit zero-padded form."""
        return notation.digits.rjust(14, "0")
