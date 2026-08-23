"""CLDR Language Display Names — localized language name mapping."""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.capabilities.Language.rules.data.english_language_map import (
    LOCALIZED_NAME_TO_CANONICAL,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Unicode CLDR",
    specification_name="CLDR Language Display Names",
    kind="registry",
    reference_url="https://www.unicode.org/cldr/charts/46/summary/root.html",
    version="46",
    lifecycle="active",
    publication_year=2025,
)

_NORMALIZED: dict[str, str] = {
    normalize_name(k): v for k, v in LOCALIZED_NAME_TO_CANONICAL.items()
}


class SectionLocalizedNames(Rule[LanguageNotation]):
    """CLDR Language Display Names — localized names → canonical code."""

    name = "Section-localized-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v46 localized language display names"
    target_semantics = frozenset({"language_name"})
    requires_features = frozenset({"include_localized"})

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check localized name membership."""
        key = (
            normalize_name(notation.raw_value)
            if notation.raw_value
            else normalize_name(notation.compact)
        )
        return key in _NORMALIZED

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return canonical lower code for localized name."""
        key = (
            normalize_name(notation.raw_value)
            if notation.raw_value
            else normalize_name(notation.compact)
        )
        return _NORMALIZED.get(key, notation.compact.lower())
