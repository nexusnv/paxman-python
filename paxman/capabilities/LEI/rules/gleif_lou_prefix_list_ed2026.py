"""GLEIF LOU prefix list (registry) — Section 1 LOU prefix membership."""

from __future__ import annotations

import re

from paxman.capabilities.LEI.notation import LEINotation
from paxman.capabilities.LEI.rules.data.lou_prefixes import ACCREDITED_LOU_PREFIXES
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="GLEIF",
    specification_name="GLEIF LOU prefix list",
    kind="registry",
    reference_url=(
        "https://www.gleif.org/en/lei-data/gleif-concatenated-file/"
        "download-the-concatenated-file"
    ),
    version="Rolling",
    lifecycle="active",
    publication_year=2026,
)

# Defense-in-depth re-derivation of the ISO structure (the rule must not
# trust the grammar nor the sibling rule); not shared via import.
_LEI_RE = re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")


def _expand(compact: str) -> str:
    """Expand each character to its numeric value (digits stay, A=10 ... Z=35)."""
    parts: list[str] = []
    for ch in compact:
        if "0" <= ch <= "9":
            parts.append(ch)
        else:
            parts.append(str(ord(ch) - 55))
    return "".join(parts)


def _mod97_10_valid(compact: str) -> bool:
    """Whole-string ISO/IEC 7064 MOD 97-10 check (no rearrangement).

    Local copy — capabilities and their rule files never import checksum
    helpers across capability boundaries.
    """
    r = 0
    for digit in _expand(compact):
        r = (r * 10 + int(digit)) % 97
    return r == 1


class Section1LOUPrefixMembership(Rule[LEINotation]):
    """GLEIF LOU prefix list — Section 1 LOU prefix membership.

    Validates that the 4-char LOU prefix is in the append-only
    ``ACCREDITED_LOU_PREFIXES`` snapshot, plus the full ISO 17442-1
    conjunction (structure + decomposition + MOD 97-10). The duplicate
    checksum is intentional (ISIN ANNA Section 5 precedent): ADR-0012
    corroboration is one-directional — LOOKUP_TABLE candidates always
    survive — so a prefix-only lookup would let a checksum-broken input
    with a known prefix through as SUCCESS via this rule alone. Both
    provenances stay independently attributable.
    """

    name = "Section 1-lou-prefix-membership"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "LOU prefix vocabulary (accredited-LOU directory + concatenated-file census)"
    )
    target_semantics = frozenset({"lei_recognition"})
    requires_features = frozenset()

    def matches(self, notation: LEINotation, contract: Contract) -> bool:
        compact = notation.compact
        if not isinstance(compact, str):
            return False
        if len(compact) != 20:
            return False
        if _LEI_RE.match(compact) is None:
            return False
        # isascii only — isupper() rejects digit-only LEIs (finding 1)
        if not compact.isascii():
            return False
        if len(notation.lou_prefix) != 4 or len(notation.entity_block) != 14:
            return False
        if len(notation.check_digits) != 2 or not notation.check_digits.isdigit():
            return False
        if compact != (
            notation.lou_prefix + notation.entity_block + notation.check_digits
        ):
            return False
        if notation.lou_prefix not in ACCREDITED_LOU_PREFIXES:
            return False
        return _mod97_10_valid(compact)

    def normalize(self, notation: LEINotation, contract: Contract) -> str:
        return notation.compact
