"""SI Unit capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.grammar.compound_recognition import CompoundRecognition
from paxman.capabilities.SIUnit.grammar.name_recognition import NameRecognition
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.bipm_si_brochure_ed2019 import (
    SectionBaseUnits,
    SectionDerivedUnits,
    SectionNames,
    SectionNonSiUnits,
    SectionPrefixes,
)
from paxman.capabilities.SIUnit.rules.iso_80000_ed2022 import SectionCompounds
from paxman.capabilities.SIUnit.rules.split_prefixes import SectionSplitWordPrefixes
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["SIUnitCapability", "SIUnitContract", "SIUnitNotation"]


class SIUnitCapability(Capability[SIUnitNotation]):
    """SI unit canonicalization capability.

    Canonicalizes SI unit expressions — a unit symbol, a unit name, or a
    product/quotient compound — to the canonical symbol form, with full
    provenance. Identity-only: no quantities, no magnitudes, no
    name-compounds ("metre per second" does not resolve as a compound —
    its words are recognized separately, yielding AMBIGUOUS; "25°C" is
    MISSING). Strategy: BIPM SI Brochure (9th ed., 2019) + ISO 80000-1.
    """

    name = "si_unit"

    def get_grammars(self) -> list[Grammar[SIUnitNotation]]:
        """Return all grammar instances.

        Returns:
            List of 3 grammars: symbol, name, compound.
        """
        return [SymbolRecognition(), NameRecognition(), CompoundRecognition()]

    def get_rules(self) -> list[Rule[SIUnitNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 7 rules: 5 BIPM sections (base, derived, non-SI,
            prefixes, names), 1 ISO 80000-1 compound section, and 1
            split-word-prefix rescue rule (opt-in via the contract flag).
        """
        return [
            SectionBaseUnits(),
            SectionDerivedUnits(),
            SectionNonSiUnits(),
            SectionPrefixes(),
            SectionNames(),
            SectionCompounds(),
            SectionSplitWordPrefixes(),
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
        allow_multi_solidus: bool = False,
        allow_split_word_prefixes: bool = False,
    ) -> SIUnitContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"symbol" resolve to "symbol".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            allow_multi_solidus: When True, preserve the legacy behavior of
                accepting compounds with more than one top-level solidus
                (e.g. "kg/m/s"). Defaults to False, which rejects such
                compounds per ISO 80000-1 §6.6.2.
            allow_split_word_prefixes: When True, merge a word prefix split
                from its unit by whitespace (e.g. "kilo gram" -> "kg").
                Defaults to False, which rejects such input (a space
                between a prefix word and unit is not standard SI).

        Returns:
            Configured SIUnitContract instance.
        """
        return SIUnitContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            allow_multi_solidus=allow_multi_solidus,
            allow_split_word_prefixes=allow_split_word_prefixes,
        )

    # format_value: NOT overridden — the canonical value IS the "symbol"
    # format, and there are no offered alternatives. The Capability base
    # provides the identity formatter.
