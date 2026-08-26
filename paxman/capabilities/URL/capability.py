"""URL capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.URL.contract import URLCapabilityContract
from paxman.capabilities.URL.grammar.absolute_uri_recognition import (
    AbsoluteUriRecognition,
)
from paxman.capabilities.URL.notation import URLNotation
from paxman.capabilities.URL.rules.whatwg_url_standard import WhatwgUrlStandard
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["URLCapability"]


class URLCapability(Capability[URLNotation]):
    """URL canonicalization capability.

    One grammar (absolute-URI recognition) and one rule (the WHATWG URL
    Standard). URL offers no alternative output formats — the WHATWG
    serialization is the canonical value (D14), so the base identity
    formatter is inherited rather than overridden.
    """

    name = "url"

    def get_grammars(self) -> list[Grammar[URLNotation]]:
        return [
            AbsoluteUriRecognition(),
        ]

    def get_rules(self) -> list[Rule[URLNotation]]:
        return [
            WhatwgUrlStandard(),
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
    ) -> URLCapabilityContract:
        """Create a URLCapabilityContract with the given configuration."""
        return URLCapabilityContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )
