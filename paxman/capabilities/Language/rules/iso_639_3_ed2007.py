"""ISO 639-3:2007 validation rules.

Comprehensive alpha-3 7000+ (Terminology only).
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.data.iana_deprecated_map import DEPRECATED_MAP
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
    """ISO 639-3:2007 Section 4 — comprehensive alpha-3 (non-private)."""

    name = "Section 4-comprehensive-alpha-3"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (comprehensive alpha-3, 7000+ entries)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check comprehensive (private qaa-qtz excluded) incl. deprecated."""
        lang = notation.language.lower()
        if len(lang) != 3:
            return False
        if _is_private_qaa(lang):
            return False
        if lang in ISO6393_CODES:
            return True
        return lang in DEPRECATED_MAP

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return lower canonical; alpha-2 if avail, resolving deprecated."""
        lang = notation.language.lower()
        if lang in DEPRECATED_MAP:
            return DEPRECATED_MAP[lang]
        alpha2 = ISO6392_T_TO_ALPHA2.get(lang)
        if alpha2 is not None:
            return alpha2
        return lang


class SectionPrivateAlpha3(Rule[LanguageNotation]):
    """ISO 639-3:2007 Section 4 — private-use qaa-qtz (engine-gated)."""

    name = "Section 4-private-alpha-3"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (private-use qaa-qtz)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset({"include_private"})

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Accept private-use qaa-qtz when include_private."""
        lang = notation.language.lower()
        if len(lang) != 3:
            return False
        return _is_private_qaa(lang)

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return lower private code."""
        return notation.language.lower()
