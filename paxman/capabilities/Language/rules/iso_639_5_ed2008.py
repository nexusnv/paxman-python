"""ISO 639-5:2008 validation rules.

Scope collection 115 families/groups — gated via include_collective.
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.data.iso_639_5 import ISO6395_CODES
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 639-5:2008",
    kind="specification",
    reference_url="https://www.iso.org/standard/39536.html",
    version="2008",
    lifecycle="active",
    publication_year=2008,
)


class SectionCollectiveCode(Rule[LanguageNotation]):
    """ISO 639-5:2008 Section 4 — collective language codes."""

    name = "Section 4-collective-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (collective code, 115 entries)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset({"include_collective"})

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool:
        """Check collective scope membership."""
        lang = notation.language.lower()
        if len(lang) != 3:
            return False
        return lang in ISO6395_CODES

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return lower canonical collective code."""
        return notation.language.lower()
