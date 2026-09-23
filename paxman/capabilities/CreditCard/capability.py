"""CreditCard capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.CreditCard.contract import CreditCardContract
from paxman.capabilities.CreditCard.grammar.pan_recognition import (
    PANRecognitionGrammar,
)
from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.capabilities.CreditCard.rules.brand_prefix_ed2026 import (
    Section1BrandPrefixMembership,
)
from paxman.capabilities.CreditCard.rules.iso_7812_1_ed2017 import (
    Section5PANStructureLuhn,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class CreditCardCapability(Capability[PANNotation]):
    """CreditCard canonicalization — compact 12-19-digit PAN.

    Recognizes compact/space-grouped/hyphen-grouped/labeled PAN mentions
    via :class:`PANRecognitionGrammar` (kernel scanner, four-guard set)
    and validates via ISO/IEC 7812-1:2017 structure + Luhn Annex B
    (:class:`Section5PANStructureLuhn`). Single-value: two distinct PANs
    raise ``MultipleMentionsError``. ``format_value`` renders ``pan``
    (default) as the compact identity and ``grouped`` as a
    grouping-agnostic re-chunk (groups of 4 from the left; an Amex
    15-digit renders ``3782 8224 6310 005``, never brand 4-6-5 —
    presentation never sniffs brand).
    """

    name = "credit_card"

    def get_grammars(self) -> list[Grammar[PANNotation]]:
        """Return the default grammar instances."""
        return [PANRecognitionGrammar()]

    def get_rules(self) -> list[Rule[PANNotation]]:
        """Return the default validation rule instances."""
        return [
            Section5PANStructureLuhn(),
            Section1BrandPrefixMembership(),
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
        include_brand_validation: bool = False,
    ) -> CreditCardContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"pan" resolve to "pan"; "grouped" renders
                groups of four from the left.
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word matches via WORD
                guard.
            include_brand_validation: Also require the PAN prefix to be a
                member of the brand-prefix allowlist (default False).

        Returns:
            Configured CreditCardContract instance.
        """
        return CreditCardContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            include_brand_validation=include_brand_validation,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: PANNotation,
    ) -> str:
        """Render the compact canonical PAN in the requested format.

        The default ``"pan"`` path is identity. ``"grouped"`` re-chunks
        the same digits into groups of four from the left (last group
        takes the remainder: 16 -> 4-4-4-4, 15 -> 4-4-4-3, 14 -> 4-4-4-2,
        19 -> 4-4-4-4-3) — grouping-agnostic, brand-blind. Never affects
        candidate identity or provenance.
        """
        if output_format == "grouped":
            return " ".join(value[i : i + 4] for i in range(0, len(value), 4))
        return value
