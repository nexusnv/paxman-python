"""Email canonicalization capability."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Email.contract import EmailContract
from paxman.capabilities.Email.grammar.localhost_recognition import (
    LocalhostEmailGrammar,
)
from paxman.capabilities.Email.grammar.obfuscated_recognition import (
    ObfuscatedEmailGrammar,
)
from paxman.capabilities.Email.grammar.standard_recognition import (
    StandardEmailGrammar,
)
from paxman.capabilities.Email.notation import EmailNotation
from paxman.capabilities.Email.rules.rfc_5322_ed2008 import Section341AddrSpec
from paxman.capabilities.Email.rules.rfc_6761_ed2012 import Section63localhost
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["EmailCapability", "EmailContract", "EmailNotation"]


class EmailCapability(Capability[EmailNotation]):
    """Email canonicalization capability."""

    name = "email"

    def get_grammars(self) -> list[Grammar[EmailNotation]]:
        return [
            StandardEmailGrammar(),
            ObfuscatedEmailGrammar(),
            LocalhostEmailGrammar(),
        ]

    def get_rules(self) -> list[Rule[EmailNotation]]:
        return [
            Section341AddrSpec(),
            Section63localhost(),
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
        include_obfuscated: bool = False,
        include_localhost: bool = True,
    ) -> EmailContract:
        """Create an EmailContract with the given configuration."""
        return EmailContract(
            include_obfuscated=include_obfuscated,
            include_localhost=include_localhost,
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )
