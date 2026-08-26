"""Language capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Language.contract import LanguageContract
from paxman.capabilities.Language.grammar.bcp47_tag_recognition import (
    BCP47TagGrammar,
)
from paxman.capabilities.Language.grammar.language_code_recognition import (
    LanguageCodeGrammar,
)
from paxman.capabilities.Language.grammar.language_name_recognition import (
    LanguageNameGrammar,
)
from paxman.capabilities.Language.notation import LanguageNotation
from paxman.capabilities.Language.rules.bcp47_rfc5646_ed2009 import (
    SectionBCP47Syntax,
)
from paxman.capabilities.Language.rules.cldr_language_display_name_ed2025 import (
    SectionLocalizedNames,
)
from paxman.capabilities.Language.rules.data.english_language_map import (
    NAME_TO_CANONICAL,
)
from paxman.capabilities.Language.rules.data.iso_639_1 import ISO6391_CODES
from paxman.capabilities.Language.rules.data.iso_639_2 import (
    ISO6392_BIB_TO_TERM,
    ISO6392_T_TO_ALPHA2,
)
from paxman.capabilities.Language.rules.iana_language_subtag_registry_ed2026 import (
    SectionIANARegistry,
    SectionIANARegistryPrivate,
)
from paxman.capabilities.Language.rules.iso_639_1_ed2002 import (
    SectionAlpha2Code,
    SectionEnglishNameMapping,
)
from paxman.capabilities.Language.rules.iso_639_2_ed1998 import SectionAlpha3Code
from paxman.capabilities.Language.rules.iso_639_3_ed2007 import (
    SectionComprehensiveAlpha3,
    SectionPrivateAlpha3,
)
from paxman.capabilities.Language.rules.iso_639_5_ed2008 import SectionCollectiveCode
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["LanguageCapability", "LanguageContract", "LanguageNotation"]

# Reverse mappings for format_value — derived from rule data, not hard-coded.
_ALPHA2_TO_T: dict[str, str] = {v: k for k, v in ISO6392_T_TO_ALPHA2.items()}
_TERM_TO_BIB: dict[str, str] = {v: k for k, v in ISO6392_BIB_TO_TERM.items()}
_CANONICAL_TO_ENGLISH: dict[str, str] = {v: k for k, v in NAME_TO_CANONICAL.items()}


def _primary_language(value: str) -> str:
    """Extract primary language subtag lower (before first hyphen)."""
    if not value:
        return ""
    return value.split("-")[0].lower()


class LanguageCapability(Capability[LanguageNotation]):
    """Language canonicalization capability.

    Canonicalizes language identifiers (bare codes, BCP 47 tags, display names)
    to BCP 47 canonical tag with full provenance. Alternative output formats
    via ``format_value``: alpha2, alpha3, alpha3-bib, name.

    Display-name completeness (v1.0.0): English language names are a curatorial
    subset (60 entries from ISO 639 English Descriptions + IANA Registry; see
    ``language_snapshot.json`` _meta) — not the full IANA Registry Description
    set (7,900+). Localized (CLDR) names are a subset (24 entries, en/fr/de/es latn)
    gated by ``include_localized`` (``requires_features``). Names outside these
    subsets are ``MISSING`` (grammar emits no match), not ``INVALID``, so no
    false negative occurs under the current completeness contract. Full IANA
    Description / CLDR v46 root coverage will be generated from the respective
    registry snapshots in a follow-up; unsupported provenance is documented in
    ``paxman/shared_data/language_snapshot.json`` and rule/grammar data headers.
    """

    name = "language"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[LanguageNotation]]:
        """Return the default grammar instances."""
        return [
            BCP47TagGrammar(),
            LanguageCodeGrammar(),
            LanguageNameGrammar(),
        ]

    def get_rules(self) -> list[Rule[LanguageNotation]]:
        """Return the default validation rule instances."""
        return [
            SectionAlpha2Code(),
            SectionEnglishNameMapping(),
            SectionAlpha3Code(),
            SectionComprehensiveAlpha3(),
            SectionPrivateAlpha3(),
            SectionCollectiveCode(),
            SectionBCP47Syntax(),
            SectionIANARegistry(),
            SectionIANARegistryPrivate(),
            SectionLocalizedNames(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
        include_localized: bool = False,
        include_collective: bool = False,
        include_private: bool = False,
    ) -> LanguageContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"bcp47" resolve to "bcp47".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            include_localized: Enable CLDR localized names.
            include_collective: Enable ISO 639-5 collective codes.
            include_private: Enable private-use language codes.

        Returns:
            Configured LanguageContract instance.
        """
        return LanguageContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            include_localized=include_localized,
            include_collective=include_collective,
            include_private=include_private,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: LanguageNotation,
    ) -> str:
        """Render a default canonical value in the requested format.

        The default ``"bcp47"`` path is identity (rule-produced canonical tag
        unchanged). ``"alpha2"`` maps via ISO 639-1 else T→alpha2 else term
        itself (``ger``→``de``). ``"alpha3"`` returns Term lower (``deu``),
        ``"alpha3-bib"`` returns Bib lower (``ger``), ``"name"`` returns
        English Description title.

        Args:
            value: The default canonical value produced by ``Rule.normalize()``
                (BCP 47 canonical tag or bare lower code).
            output_format: The contract's resolved output format.
            notation: The original language notation (retained for interface
                compatibility; not used for formatting beyond value).

        Returns:
            The value rendered in the requested format.
        """
        if (
            output_format is None
            or output_format == "bcp47"
            or output_format == "default"
        ):
            return value

        primary = _primary_language(value)

        if output_format == "alpha2":
            if primary in ISO6391_CODES:
                return primary
            term = ISO6392_BIB_TO_TERM.get(primary, primary)
            mapped = ISO6392_T_TO_ALPHA2.get(term)
            if mapped is not None:
                return mapped
            return term

        if output_format == "alpha3":
            if len(primary) == 2:
                mapped = _ALPHA2_TO_T.get(primary)
                if mapped is not None:
                    return mapped
                return ISO6392_BIB_TO_TERM.get(primary, primary)
            return ISO6392_BIB_TO_TERM.get(primary, primary)

        if output_format == "alpha3-bib":
            if len(primary) == 2:
                term = _ALPHA2_TO_T.get(primary, primary)
                return _TERM_TO_BIB.get(term, term)
            term = ISO6392_BIB_TO_TERM.get(primary, primary)
            return _TERM_TO_BIB.get(term, term)

        if output_format == "name":
            # Normalize primary to canonical code for name lookup
            if primary in ISO6391_CODES:
                canonical = primary
            else:
                term = ISO6392_BIB_TO_TERM.get(primary, primary)
                alpha2 = ISO6392_T_TO_ALPHA2.get(term)
                canonical = alpha2 if alpha2 is not None else term
            # Reverse lookup: canonical lower -> English normalized key -> Title
            raw = _CANONICAL_TO_ENGLISH.get(canonical)
            if raw is None:
                # Try term fallback
                term_fb = ISO6392_BIB_TO_TERM.get(primary, primary)
                raw = _CANONICAL_TO_ENGLISH.get(term_fb)
            if raw is None:
                raw = _CANONICAL_TO_ENGLISH.get(primary)
            if raw is not None:
                # raw is normalized lower with spaces; title-case each word
                return raw.title()
            return value

        return value
