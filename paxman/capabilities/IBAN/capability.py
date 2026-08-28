"""IBAN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.IBAN.contract import IBANContract
from paxman.capabilities.IBAN.grammar.iban_recognition import IBANRecognitionGrammar
from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import Section4IBANStructureMOD97
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["IBANCapability", "IBANContract", "IBANNotation"]


class IBANCapability(Capability[IBANNotation]):
    """IBAN canonicalization — electronic compact with paper presentation."""

    name = "iban"

    def get_grammars(self) -> list[Grammar[IBANNotation]]:
        return [IBANRecognitionGrammar()]

    def get_rules(self) -> list[Rule[IBANNotation]]:
        return [Section4IBANStructureMOD97()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> IBANContract:
        """Factory method for creating contracts with proper defaults."""
        return IBANContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: IBANNotation
    ) -> str:
        if output_format == "paper":
            return " ".join(value[i : i + 4] for i in range(0, len(value), 4))
        return value
