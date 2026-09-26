"""ISO 17442-1:2020 Section 4 — LEI structure plus MOD 97-10 check digits.

ISO 17442-1:2020 (Assignment) defines the LEI as exactly 20 characters,
charset ``[A-Z0-9]``: 4-char LOU prefix + 14-char entity block + 2 check
digits. The check character system is ISO/IEC 7064:2003 MOD 97-10 (pure
system, base 10, alphanumeric set), cited normatively by ISO 17442-1 and
applied to the WHOLE string without rearrangement — the check digits sit at
positions 19-20, so there is no IBAN-style block rotation. Validation
expands A=10 … Z=35 and requires the iterative remainder == 1. Positions
5-6 carry no enforceable constraint (GLEIF's own worked example
``7LTWFZYICNSX8D621K86`` carries ``FZ``), so content there never rejects.
"""

from __future__ import annotations

import re

from paxman.capabilities.LEI.notation import LEINotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 17442-1:2020",
    kind="specification",
    reference_url="https://www.iso.org/standard/78829.html",
    version="2020",
    lifecycle="active",
    publication_year=2020,
)

# Mirrors the grammar charset: 18 alphanumerics + 2 numeric check digits =
# exactly 20. Intentional defense-in-depth (the rule must not trust the
# grammar); not shared via import (ISIN precedent).
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

    Iteratively fold the expanded digit string: the remainder must be 1.
    Local copy of the IBAN accumulator shape — capabilities never import
    from each other, and the LEI applies it without IBAN's rearrangement.
    """
    r = 0
    for digit in _expand(compact):
        r = (r * 10 + int(digit)) % 97
    return r == 1


class Section4LEIStructureMOD9710(Rule[LEINotation]):
    """ISO 17442-1:2020 Section 4 — LEI structure plus MOD 97-10 check digits.

    Validates length exactly 20, charset ``[A-Z0-9]{18}[0-9]{2}``,
    decomposition consistency with the notation fields, and the whole-string
    ISO/IEC 7064:2003 MOD 97-10 remainder == 1. Positions 5-6 content never
    rejects; LOU membership belongs to the GLEIF LOOKUP_TABLE rule.
    """

    name = "Section 4-lei-structure-mod97-10"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = (
        "Assignment clause (20-char structure + MOD 97-10, via ISO/IEC 7064:2003)"
    )
    target_semantics = frozenset({"lei_recognition"})
    requires_features = frozenset()

    def matches(self, notation: LEINotation, contract: Contract) -> bool:
        """Check whether the notation is a valid LEI structure."""
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
        return _mod97_10_valid(compact)

    def normalize(self, notation: LEINotation, contract: Contract) -> str:
        """Normalize to the compact LEI form."""
        return notation.compact
