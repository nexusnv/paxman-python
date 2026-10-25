"""ISO 639-1:2002 validation rules.

Bare alpha-2 184 membership plus English name mapping.

Two of the three rules emit a canonical for a *name* or *deprecated form*
rather than for a code the caller wrote, so both must respect the collection
gate that ``Section 4-collective-code`` (ISO 639-5) already carries: an
emitted canonical whose only authority is gated off would be a value the
capability refuses as input (ADR-0010 Property 2, experiment finding E2).
The gate is per-entry authority filtering inside ``matches``/``normalize``,
not whole-rule gating — ``requires_features`` remains the only mechanism
that disables a rule entirely (same form as ``Country/rules/iso_3166_ed2024``
refusing localized keys).
"""

from __future__ import annotations

from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.capabilities.Language.rules.data.english_language_map import (
    NAME_TO_CANONICAL,
)
from paxman.capabilities.Language.rules.data.iana_deprecated_map import DEPRECATED_MAP
from paxman.capabilities.Language.rules.data.iso_639_1 import ISO6391_CODES
from paxman.capabilities.Language.rules.data.iso_639_5 import ISO6395_CODES
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

# Canonical values whose only authority is the include_collective-gated
# ISO 639-5 collection lane. Emitting one of these under a contract that
# does not opt in produces a canonical this capability refuses as input.
_GATED_TARGETS = ISO6395_CODES

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
        """Return lower canonical alpha-2, resolving deprecated.

        A deprecation that points into a gated collection stops at the source
        code: ``bh`` stays ``bh`` unless ``include_collective`` is on, because
        its Preferred-Value ``bih`` is reachable only through the gated
        ISO 639-5 rule. The source is canonical under this rule's own
        ISO 639-1:2002 provenance, so no information is lost.
        """
        lang = notation.language.lower()
        target = DEPRECATED_MAP.get(lang, lang)
        if target in _GATED_TARGETS and not getattr(
            contract, "include_collective", False
        ):
            return lang
        return target


class SectionEnglishNameMapping(Rule[LanguageNotation]):
    """ISO 639-1:2002 English language name → canonical code mapping.

    Completeness: English display names are a curatorial subset (60 entries)
    — not the full IANA Registry Description set (7,900+). Names outside the
    subset yield MISSING (grammar emits no match), not INVALID; see
    ``language_snapshot.json`` _meta and grammar/rules data headers.

    A name whose only canonical is collection-scoped is refused unless the
    contract opts into ``include_collective``: the code ``bih`` is INVALID
    under that contract, so accepting the name would emit a canonical the
    capability refuses as input (E2).
    """

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
        target = _NAME_TO_CANONICAL_NORMALIZED.get(key)
        if target is None:
            return False
        if target in _GATED_TARGETS:
            return bool(getattr(contract, "include_collective", False))
        return True

    def normalize(self, notation: LanguageNotation, contract: Contract) -> str:
        """Return canonical lower code for English name."""
        key = (
            normalize_name(notation.raw_value)
            if notation.raw_value
            else normalize_name(notation.compact)
        )
        return _NAME_TO_CANONICAL_NORMALIZED.get(key, notation.compact.lower())
