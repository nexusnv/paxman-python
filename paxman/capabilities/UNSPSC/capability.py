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
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class UNSPSCCapability(Capability[UNSPSCNotation]):
    """UNSPSC canonicalization capability (scaffold).

    TODO(scaffold): describe what this capability recognizes and the
    authoritative specification(s) it validates against.
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

    # format_value: NOT overridden — the canonical value IS the default
    # format, and there are no offered alternatives. The Capability base
    # provides the identity formatter. TODO(scaffold): override if you offer
    # alternative output formats.
