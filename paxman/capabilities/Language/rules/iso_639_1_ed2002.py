"""ISO 639-1:2002 validation rules.

Bare alpha-2 184 membership plus English name mapping.
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.capabilities.Language.rules.data.english_language_map import (
    NAME_TO_CANONICAL,
)
from paxman.capabilities.Language.rules.data.iana_deprecated_map import DEPRECATED_MAP
from paxman.capabilities.Language.rules.data.iso_639_1 import ISO6391_CODES
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 639-1:2002",
    kind="specification",
    reference_url="https://www.iso.org/standard/22109.html",
    version="2002",
    lifecycle="active",
    publication_year=2002,
)

# Normalized English name view — keys normalized via shared normalizer
_NAME_TO_CANONICAL_NORMALIZED: dict[str, str] = {
    normalize_name(k): v for k, v in NAME_TO_CANONICAL.items()
}


class SectionAlpha2Code(Rule[LanguageNotation]):
    """ISO 639-1:2002 Section 4 — alpha-2 code (184 entries)."""

    name = "Section 4-alpha-2-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (alpha-2 code, 184 entries)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check bare alpha-2 membership, including deprecated Preferred-Value."""
        # Bare code grammar ensures 2-3 letters; this rule validates 2-letter ISO 639-1
        lang = notation.language.lower()
        if len(lang) != 2:
            return False
        if lang in ISO6391_CODES:
            return True
        # Deprecated codes like iw→he are accepted via ISO 639-1 lifecycle
        return lang in DEPRECATED_MAP

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return lower canonical alpha-2, resolving deprecated."""
        lang = notation.language.lower()
        return DEPRECATED_MAP.get(lang, lang)


class SectionEnglishNameMapping(Rule[LanguageNotation]):
    """ISO 639-1:2002 English language name → canonical code mapping."""

    name = "Section-english-name-mapping"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (English language names → alpha-2)"
    target_semantics = frozenset({"language_name"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check English name membership via normalized lookup."""
        key = (
            normalize_name(notation.raw_value)
            if notation.raw_value
            else normalize_name(notation.compact)
        )
        return key in _NAME_TO_CANONICAL_NORMALIZED

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return canonical lower code for English name."""
        key = (
            normalize_name(notation.raw_value)
            if notation.raw_value
            else normalize_name(notation.compact)
        )
        return _NAME_TO_CANONICAL_NORMALIZED.get(key, notation.compact.lower())
