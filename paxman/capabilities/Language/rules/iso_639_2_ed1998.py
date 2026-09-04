"""ISO 639-2:1998 validation rules.

Bare alpha-3 487 T/B with B→T mapping via Library of Congress RA.
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.data.iana_deprecated_map import (
    DEPRECATED_MAP,
)
from paxman.capabilities.Language.rules.data.iso_639_2 import (
    ISO6392_B,
    ISO6392_BIB_TO_TERM,
    ISO6392_T,
    ISO6392_T_TO_ALPHA2,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 639-2:1998",
    kind="specification",
    reference_url="https://www.iso.org/standard/4767.html",
    version="1998",
    lifecycle="active",
    publication_year=1998,
)


class SectionAlpha3Code(Rule[LanguageNotation]):
    """ISO 639-2:1998 Section 4 — alpha-3 Terminology/Bibliographic."""

    name = "Section 4-alpha-3-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (alpha-3 code, 487 entries T/B)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check bare alpha-3 membership (T or B) incl. deprecated."""
        lang = notation.language.lower()
        if len(lang) != 3:
            return False
        if lang in ISO6392_T or lang in ISO6392_B:
            return True
        return lang in DEPRECATED_MAP

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return preferred Term (B→T), alpha-2 if avail, resolving deprecated."""
        lang = notation.language.lower()
        if lang in DEPRECATED_MAP:
            # Deprecated Preferred-Value is authoritative (e.g., scc→sr, scc 3→2)
            return DEPRECATED_MAP[lang]
        term = ISO6392_BIB_TO_TERM.get(lang, lang)
        alpha2 = ISO6392_T_TO_ALPHA2.get(term)
        if alpha2 is not None:
            return alpha2
        return term
