"""UNSPSC capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.capabilities.UNSPSC.grammar.unspsc_recognition import (
    UNSPSCRecognitionGrammar,
)
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.capabilities.UNSPSC.rules.undp_unspsc_codeset_ed2026 import (
    Section3CodesetMembership,
)
from paxman.capabilities.UNSPSC.rules.undp_unspsc_structure_ed2025 import (
    Section1HierarchyStructure,
    Section2LevelPadding,
)
from paxman.capabilities.UNSPSC.rules.unece_bfi_ed2005 import (
    Section4BusinessFunctionSuffix,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class UNSPSCCapability(Capability[UNSPSCNotation]):
    """UNSPSC canonicalization capability.

    Recognizes 6/8/10-digit UNSPSC mentions (bare, labelled, MDM
    ``UNSPSC000.`` IDs) and validates them against the UNGM structure
    article, the UNDP codeset snapshot, and the UNECE BFI guidelines.
    """

    name = "unspsc"

    def get_grammars(self) -> list[Grammar[UNSPSCNotation]]:
        """Return the default grammar instances."""
        return [UNSPSCRecognitionGrammar()]

    def get_rules(self) -> list[Rule[UNSPSCNotation]]:
        """Return the default validation rule instances."""
        return [
            Section1HierarchyStructure(),
            Section2LevelPadding(),
            Section3CodesetMembership(),
            Section4BusinessFunctionSuffix(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        include_business_function: bool = True,
        include_live_membership: bool = False,
    ) -> UNSPSCContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"unspsc" resolve to "unspsc".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            include_business_function: Gate the BFI-suffix rule.
            include_live_membership: Rolling-liveness interpretation.

        Returns:
            Configured UNSPSCContract instance.
        """
        return UNSPSCContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            include_business_function=include_business_function,
            include_live_membership=include_live_membership,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: UNSPSCNotation,
    ) -> str:
        """Render the 8-digit stem in the requested format.

        The default ``"unspsc"`` path is the identity. ``"labeled"``
        prefixes ``UNSPSC ``, ``"native"`` restores the spelled length
        (6-digit alias or 10-digit suffix). Never affects candidate
        identity or provenance.
        """
        if output_format == "labeled":
            return f"UNSPSC {value}"
        if output_format == "native":
            if notation.native_length == 6:
                return value[:6]
            if notation.native_length == 10:
                return value + notation.function
            return value
        return value
