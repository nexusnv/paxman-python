"""Verified by GS1 — Section 3 verified liveness (snapshot-gated)."""

from __future__ import annotations

from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.capabilities.GTIN.rules.data import verified_snapshot
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="GS1",
    specification_name="Verified by GS1",
    kind="registry",
    reference_url="https://www.gs1.org/services/verified-by-gs1",
    version="Rolling",
    lifecycle="active",
    publication_year=2019,
)


def _gs1_mod10_is_valid(digits: str) -> bool:
    """GS1 Mod-10 check (local copy — never import across capabilities)."""
    if len(digits) < 2:
        return False
    total = sum(
        int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1]))
    )
    return int(digits[-1]) == (10 - total % 10) % 10


class Section3VerifiedLiveness(Rule[GTINNotation]):
    """Verified by GS1 — Section 3 verified liveness (snapshot-gated)."""

    name = "Section 3-verified-liveness"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 3 (Verified by GS1 liveness)"
    target_semantics = frozenset({"gtin_recognition"})
    requires_features = frozenset({"include_verified"})

    def matches(self, notation: GTINNotation, contract: Contract) -> bool:
        digits = notation.digits
        if not isinstance(digits, str):
            return False
        if len(digits) not in (8, 12, 13, 14):
            return False
        if notation.native_length != len(digits):
            return False
        if not digits.isascii() or not digits.isdigit():
            return False
        if not _gs1_mod10_is_valid(digits):
            return False
        canonical = digits.rjust(14, "0")
        return canonical in verified_snapshot.ISSUED_GTINS

    def normalize(self, notation: GTINNotation, contract: Contract) -> str:
        return notation.digits.rjust(14, "0")
