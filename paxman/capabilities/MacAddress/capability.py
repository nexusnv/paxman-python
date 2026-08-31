"""MacAddress capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.grammar.mac_address_recognition import (
    MacAddressRecognition,
)
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_ed2024 import MacAddressRule
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class MacAddressCapability(Capability[MacAddressNotation]):
    """MacAddress canonicalization capability (scaffold).

    TODO(scaffold): describe what this capability recognizes and the
    authoritative specification(s) it validates against.
    """

    name = "mac_address"

    def get_grammars(self) -> list[Grammar[MacAddressNotation]]:
        """Return the default grammar instances."""
        return [MacAddressRecognition()]

    def get_rules(self) -> list[Rule[MacAddressNotation]]:
        """Return the default validation rule instances."""
        return [MacAddressRule()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> MacAddressContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"colon" resolve to "colon".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).

        Returns:
            Configured MacAddressContract instance.
        """
        return MacAddressContract(
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
