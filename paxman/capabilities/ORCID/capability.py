"""ORCID capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ORCID.contract import ORCIDContract
from paxman.capabilities.ORCID.grammar.orcid_recognition import (
    ORCIDRecognitionGrammar,
)
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import (
    Section4OrcidStructure,
    SectionAnnexAMod11Dash2,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ORCIDCapability", "ORCIDContract", "ORCIDNotation"]


class ORCIDCapability(Capability[ORCIDNotation]):
    """ORCID canonicalization capability.

    Canonicalizes ORCID input to the hyphenated form XXXX-XXXX-XXXX-XXXC per
    ISO 27729:2024 (ISNI-compatible, MOD 11-2 check) with full provenance.
    """

    name = "orcid"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[ORCIDNotation]]:
        return [ORCIDRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ORCIDNotation]]:
        return [Section4OrcidStructure(), SectionAnnexAMod11Dash2()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> ORCIDContract:
        """Factory for contracts with proper defaults."""
        return ORCIDContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ORCIDNotation,
    ) -> str:
        """Render the hyphenated canonical value in the requested format.

        The default ``"orcid"`` path is identity. ``"uri"`` prepends the
        canonical https host; ``"compact"`` strips the hyphens. Never affects
        candidate identity or provenance.
        """
        if output_format == "uri":
            return f"https://orcid.org/{notation.hyphenated}"
        if output_format == "compact":
            return notation.compact
        return value
