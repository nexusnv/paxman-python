"""ISO 27729:2024 rules: ISNI structure plus MOD 11-2 check character.

Both rule classes validate the full conjunction (structure AND check digit):
each Paxman rule is an independent authority producing its own candidate, so
a partial validator would let checksum-invalid input resolve SUCCESS. The two
classes mirror ORCID's iso_27729 pair and exist for dual provenance on SUCCESS.
"""

from __future__ import annotations

from paxman.capabilities.ISNI.notation import ISNINotation
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

    ISO/IEC 7064 MOD 11-2 recurrence (M=11, r=2), local copy — capabilities
    never import checksum helpers across capability boundaries (ORCID owns
    the identical helper; duplication is intentional).
    Precondition: base15 must be 15 ASCII digits (guarded by callers).
    """
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)


def _is_valid_isni(notation: ISNINotation) -> bool:
    """Full conjunction: 16 chars, ASCII-digit base, matching check char."""
    if len(notation.compact) != 16:
        return False
    base, check = notation.compact[:15], notation.compact[15]
    if not base.isascii() or not base.isdigit():
        return False
    if check not in "0123456789X":
        return False
    if notation.check != check:
        return False
    return check == _mod_11_2_check(base)


def _normalize(notation: ISNINotation) -> str:
    """Return the spaced display XXXX XXXX XXXX XXXC form."""
    compact = notation.compact.upper()
    return f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"


class Section4IsniStructure(Rule[ISNINotation]):
    """ISO 27729:2024 Section 4 — ISNI structure (16 chars + check char)."""

    name = "Section 4-isni-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (16 chars: 15 digits + MOD 11-2 check character)"
    target_semantics = frozenset({"isni_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISNINotation, contract: Contract) -> bool:
        """Check whether the notation is a valid ISNI structure."""
        return _is_valid_isni(notation)

    def normalize(self, notation: ISNINotation, contract: Contract) -> str:
        """Normalize to the spaced display form."""
        return _normalize(notation)


class SectionAMod11Dash2(Rule[ISNINotation]):
    """ISO 27729:2024 Annex A — MOD 11-2 over the first 15 decimal digits."""

    name = "Section A-mod11-2-check-character"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Annex A (MOD 11-2 over the first 15 decimal digits)"
    target_semantics = frozenset({"isni_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISNINotation, contract: Contract) -> bool:
        """Check whether the MOD 11-2 check character holds."""
        return _is_valid_isni(notation)

    def normalize(self, notation: ISNINotation, contract: Contract) -> str:
        """Normalize to the spaced display form."""
        return _normalize(notation)
