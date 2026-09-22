"""GTIN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.GTIN.contract import GTINContract
from paxman.capabilities.GTIN.grammar.gtin_recognition import GTINRecognition
from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.capabilities.GTIN.rules.gs1_genspecs_ed2026 import (
    Section1GtinStructureCheckDigit,
)
from paxman.capabilities.GTIN.rules.gs1_prefix_ed2026 import Section2Gs1Prefix
from paxman.capabilities.GTIN.rules.verified_by_gs1_ed2019 import (
    Section3VerifiedLiveness,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class GTINCapability(Capability[GTINNotation]):
    """GTIN canonicalization — 14-digit zero-padded form.

    Recognizes compact/space-grouped/hyphenated/labeled/AI-wrapped
    GTIN-8/12/13/14 mentions via :class:`GTINRecognitionGrammar` and
    validates via GS1 GenSpecs structure + Mod-10
    (:class:`Section1GtinStructureCheckDigit`) plus GS1 Prefix membership
    (:class:`Section2Gs1Prefix`), with Verified by GS1 snapshot liveness
    (:class:`Section3VerifiedLiveness`) gated behind ``include_verified``.
    Single-value: two distinct GTINs raise ``MultipleMentionsError``.
    ``format_value`` renders ``native`` as the spelled-length slice;
    ``gtin14`` (default) is the 14-digit identity.
    """

    name = "gtin"

    def get_grammars(self) -> list[Grammar[GTINNotation]]:
        """Return the default grammar instances."""
        return [GTINRecognition()]

    def get_rules(self) -> list[Rule[GTINNotation]]:
        """Return the default validation rule instances."""
        return [
            Section1GtinStructureCheckDigit(),
            Section2Gs1Prefix(),
            Section3VerifiedLiveness(),
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
        include_verified: bool = False,
    ) -> GTINContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"gtin14" resolve to "gtin14"; "native"
                renders the spelled length.
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word matches via WORD guard.
            include_verified: Enable Verified by GS1 liveness lookup
                (default False).

        Returns:
            Configured GTINContract instance.
        """
        return GTINContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            include_verified=include_verified,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: GTINNotation,
    ) -> str:
        """Render the 14-digit canonical value in the requested format.

        The default ``"gtin14"`` path is identity. ``"native"`` strips
        leading padding via the notation facet slice
        (``value[14-native_length:]``; identity for true GTIN-14).
        Never affects candidate identity or provenance.
        """
        if output_format == "native":
            return value[14 - notation.native_length :]
        return value
