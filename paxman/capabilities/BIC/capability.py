"""BIC capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.BIC.grammar.bic_recognition import BICRecognitionGrammar
from paxman.capabilities.BIC.notation import BICNotation
from paxman.capabilities.BIC.rules.iso_9362_ed2022 import Section5BICStructureCountry
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["BICCapability", "BICContract", "BICNotation"]


class BICCapability(Capability[BICNotation]):
    """BIC canonicalization — compact with grouped and bic11 presentation."""

    name = "bic"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[BICNotation]]:
        return [BICRecognitionGrammar()]

    def get_rules(self) -> list[Rule[BICNotation]]:
        return [Section5BICStructureCountry()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> BICContract:
        """Factory method for creating contracts with proper defaults."""
        return BICContract(
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
        notation: BICNotation,
    ) -> str:
        """Render BIC value in the requested output format.

        - ``grouped``: ``AAAA BB CC [XXX]`` with space separation.
        - ``bic11``: always 11 chars, appending ``XXX`` when branch absent
          (lossy expansion, head-office equivalence like Phone national).
        - ``bic`` / ``None`` / ``default``: identity (compact).
        """
        if output_format == "grouped":
            if len(value) == 11:
                return f"{value[0:4]} {value[4:6]} {value[6:8]} {value[8:11]}"
            return f"{value[0:4]} {value[4:6]} {value[6:8]}"
        if output_format == "bic11":
            if len(value) == 8:
                return value + "XXX"
            return value
        return value
