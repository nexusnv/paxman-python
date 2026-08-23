"""ISO 639-3:2007 validation rules.

Comprehensive alpha-3 7000+ (Terminology only).
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.data.iso_639_2 import ISO6392_T_TO_ALPHA2
from paxman.capabilities.Language.rules.data.iso_639_3 import ISO6393_CODES
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="SIL International (ISO 639-3 RA)",
    specification_name="ISO 639-3:2007",
    kind="specification",
    reference_url="https://www.iso.org/standard/39534.html",
    version="2007",
    lifecycle="active",
    publication_year=2007,
)


def _is_private_qaa(lang: str) -> bool:
    return len(lang) == 3 and "qaa" <= lang <= "qtz"


class SectionComprehensiveAlpha3(Rule[LanguageNotation]):
    """ISO 639-3:2007 Section 4 — comprehensive alpha-3."""

    name = "Section 4-comprehensive-alpha-3"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (comprehensive alpha-3, 7000+ entries)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check comprehensive membership with private reservation gating."""
        lang = notation.language.lower()
        if len(lang) != 3:
            return False
        if _is_private_qaa(lang):
            include_private = bool(getattr(contract, "include_private", False))
            return bool(include_private)
        return lang in ISO6393_CODES

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return lower canonical; alpha-2 preferred when available."""
        lang = notation.language.lower()
        alpha2 = ISO6392_T_TO_ALPHA2.get(lang)
        if alpha2 is not None:
            return alpha2
        return lang
