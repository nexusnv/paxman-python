"""ORCID capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ORCID.contract import ORCIDContract
from paxman.capabilities.ORCID.grammar.orcid_recognition import (
    ORCIDRecognition,
)
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import ORCIDRule
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class ORCIDCapability(Capability[ORCIDNotation]):
    """ORCID canonicalization capability (scaffold).

    TODO(scaffold): describe what this capability recognizes and the
    authoritative specification(s) it validates against.
    """

    name = "orcid"

    def get_grammars(self) -> list[Grammar[ORCIDNotation]]:
        """Return the default grammar instances."""
        return [ORCIDRecognition()]

    def get_rules(self) -> list[Rule[ORCIDNotation]]:
        """Return the default validation rule instances."""
        return [ORCIDRule()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> ORCIDContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"orcid" resolve to "orcid".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).

        Returns:
            Configured ORCIDContract instance.
        """
        return ORCIDContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    # format_value: NOT overridden — the canonical value IS the default
    # format, and there are no offered alternatives. The Capability base
    # provides the identity formatter. TODO(scaffold): override if you offer
    # alternative output formats.
