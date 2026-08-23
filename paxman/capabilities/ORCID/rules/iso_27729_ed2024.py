"""ISO 27729:2024 rules: ORCID/ISNI structure plus MOD 11-2 check character.

Both rule classes validate the full conjunction (structure AND check digit):
each Paxman rule is an independent authority producing its own candidate, so
a partial validator would let checksum-invalid input resolve SUCCESS. The two
classes mirror ISBN's iso_2108 pair and exist for dual provenance on SUCCESS.
"""

from __future__ import annotations

from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 27729:2024",
    kind="specification",
    reference_url="https://www.iso.org/standard/87177.html",
    version="2024-11",
    lifecycle="active",
    publication_year=2024,
)


def _mod_11_2_check(base15: str) -> str:
    """Compute the MOD 11-2 check char for 15 ASCII digits (X = 10).

    Precondition: base15 must be 15 ASCII digits (guarded by ``_is_valid_orcid``).
    """
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)


def _is_valid_orcid(notation: ORCIDNotation) -> bool:
    """Full conjunction: 16 chars, ASCII-digit base, matching check char."""
    if len(notation.compact) != 16:
        return False
    base, check = notation.compact[:15], notation.compact[15]
    if not base.isascii() or not base.isdigit():
        return False
    return check == _mod_11_2_check(base)


def _normalize(notation: ORCIDNotation) -> str:
    compact = notation.compact.upper()
    return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:]}"


class Section4OrcidStructure(Rule[ORCIDNotation]):
    """ISO 27729:2024 Section 4 - ISNI/ORCID structure (with Annex A check)."""

    name = "Section 4-orcid-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (16 chars: 15 digits + MOD 11-2 check character)"
    target_semantics = frozenset({"orcid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ORCIDNotation, contract: Contract) -> bool:
        return _is_valid_orcid(notation)

    def normalize(self, notation: ORCIDNotation, contract: Contract) -> str:
        return _normalize(notation)


class SectionAnnexAMod11Dash2(Rule[ORCIDNotation]):
    """ISO 27729:2024 Annex A - MOD 11-2 check character (with S4 structure)."""

    name = "Section A-mod11-2-check-character"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Annex A (MOD 11-2 over the first 15 decimal digits)"
    target_semantics = frozenset({"orcid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ORCIDNotation, contract: Contract) -> bool:
        return _is_valid_orcid(notation)

    def normalize(self, notation: ORCIDNotation, contract: Contract) -> str:
        return _normalize(notation)
