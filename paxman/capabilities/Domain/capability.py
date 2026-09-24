"""Domain capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Domain.contract import DomainContract
from paxman.capabilities.Domain.grammar.ascii_hostname import (
    AsciiHostnameGrammar,
)
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.iana_root_zone_membership import (
    IanaRootZoneMembership,
)
from paxman.capabilities.Domain.rules.rfc_1034_name_syntax import Rfc1034NameSyntax
from paxman.capabilities.Domain.rules.rfc_1035_label_length import (
    Rfc1035LabelLength,
)
from paxman.capabilities.Domain.rules.rfc_5893_bidi_context import (
    Rfc5893BidiContext,
)
from paxman.capabilities.Domain.rules.unicode_uts46_statuses import (
    UnicodeUts46Statuses,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class DomainCapability(Capability[DomainNotation]):
    """Domain canonicalization capability (scaffold).

    TODO(scaffold): describe what this capability recognizes and the
    authoritative specification(s) it validates against.
    """

    name = "domain"

    def get_grammars(self) -> list[Grammar[DomainNotation]]:
        """Return the default grammar instances."""
        return [AsciiHostnameGrammar()]

    def get_rules(self) -> list[Rule[DomainNotation]]:
        """Return the default validation rule instances."""
        return [
            Rfc1034NameSyntax(),
            Rfc1035LabelLength(),
            UnicodeUts46Statuses(),
            Rfc5893BidiContext(),
            IanaRootZoneMembership(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> DomainContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"ascii" resolve to "ascii".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).

        Returns:
            Configured DomainContract instance.
        """
        return DomainContract(
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
