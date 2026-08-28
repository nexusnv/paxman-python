"""ISSN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISSN.contract import ISSNContract
from paxman.capabilities.ISSN.grammar.issn_recognition import ISSNRecognitionGrammar
from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.capabilities.ISSN.rules.iso_3297_ed2022 import Section4CheckDigit
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ISSNCapability", "ISSNContract", "ISSNNotation"]


class ISSNCapability(Capability[ISSNNotation]):
    """ISSN canonicalization capability.

    Canonicalizes ISSN input to the hyphenated form XXXX-XXXX
    per ISO 3297:2022 with full provenance.
    """

    name = "issn"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[ISSNNotation]]:
        return [ISSNRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISSNNotation]]:
        return [Section4CheckDigit()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> ISSNContract:
        """Factory for contracts with proper defaults."""
        return ISSNContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ISSNNotation,
    ) -> str:
        """Render the hyphenated canonical value in the requested format.

        The default ``"hyphenated"`` path is identity. ``"compact"`` strips
        the hyphen; ``"urn"`` wraps ``urn:issn:``. Never affects candidate
        identity or provenance.
        """
        if output_format == "compact":
            return value.replace("-", "")
        if output_format == "urn":
            return f"urn:issn:{value}"
        return value
