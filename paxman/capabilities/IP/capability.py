"""IP canonicalization capability."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.IP.contract import IPContract
from paxman.capabilities.IP.grammar.ipv4_recognition import IPv4Grammar
from paxman.capabilities.IP.grammar.ipv6_recognition import IPv6Grammar
from paxman.capabilities.IP.notation import IPNotation
from paxman.capabilities.IP.rules.rfc_791_ed1981 import Section3Dot2IPv4Address
from paxman.capabilities.IP.rules.rfc_5952_ed2010 import (
    Section4IPv6TextRepresentation,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["IPCapability", "IPContract", "IPNotation"]


class IPCapability(Capability[IPNotation]):
    """IP canonicalization capability — dotted-decimal IPv4 and RFC 5952 IPv6.

    Grammars:
        - ``ipv4_recognition`` (always active)
        - ``ipv6_recognition`` (gated by ``IPContract.include_ipv6``)

    Rules:
        - ``Section 3.2-ipv4-address`` (RFC 791 / RFC 1123)
        - ``Section 4-ipv6-text-representation`` (RFC 5952, arch RFC 4291)
    """

    name = "ip"

    def get_grammars(self) -> list[Grammar[IPNotation]]:
        return [
            IPv4Grammar(),
            IPv6Grammar(),
        ]

    def get_rules(self) -> list[Rule[IPNotation]]:
        return [
            Section3Dot2IPv4Address(),
            Section4IPv6TextRepresentation(),
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
        include_ipv6: bool = True,
    ) -> IPContract:
        """Create an IPContract with the given configuration.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: If set, only these rules run (overrides excluded).
            year: Unused (kept for uniform Contract shape).
            output_format: Must be ``None``, ``"default"`` or ``"ip"``.
            extra_grammars: Community grammars to run alongside shipped ones.
            suppress_common_words: Reserved (no effect for IP).
            include_ipv6: When ``False`` the IPv6 grammar is omitted →
                IPv6 inputs yield ``MISSING``.
        """
        return IPContract(
            include_ipv6=include_ipv6,
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )
