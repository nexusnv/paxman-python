"""Money capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.grammar.code_recognition import CodeRecognition
from paxman.capabilities.Money.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.Money.grammar.word_recognition import WordRecognition
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.rules.cldr_currencies_ed2025 import (
    SectionNames,
    SectionSymbols,
)
from paxman.capabilities.Money.rules.iso_4217_ed2015 import SectionCode
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["MoneyCapability", "MoneyContract", "MoneyNotation"]


class MoneyCapability(Capability[MoneyNotation]):
    """Money canonicalization capability.

    Canonicalizes money amounts (ISO 4217 code, CLDR symbol, or CLDR name
    adjacent to an amount) to ``CODE + " " + amount`` padded to ISO 4217
    minor-unit precision, with full provenance.
    """

    name = "money"

    def get_grammars(self) -> list[Grammar[MoneyNotation]]:
        """Return all grammar instances.

        Returns:
            List of 3 grammars: code, symbol, word.
        """
        return [CodeRecognition(), SymbolRecognition(), WordRecognition()]

    def get_rules(self) -> list[Rule[MoneyNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 3 rules: ISO 4217 code + minor units, CLDR symbols,
            CLDR names.
        """
        return [SectionCode(), SectionSymbols(), SectionNames()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
        precision: Literal["strict", "truncate", "round"] = "strict",
        dollar_sign_currency: str | None = None,
    ) -> MoneyContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"code_amount" resolve to "code_amount", or the
                offered alternative "compact".
            extra_grammars: Community grammar names (opt-in) to run alongside
                the shipped grammars, in order.
            precision: Over-precision amount handling. "strict" rejects
                amounts exceeding the currency's minor-unit precision (the
                default); "truncate" cuts excess digits; "round" rounds
                half-to-even to the allowed precision.
            dollar_sign_currency: ISO 4217 alpha-3 code (opt-in) used to
                resolve bare or shared symbols (e.g. "$"). None (the default)
                makes a bare "$" INVALID (recognized, but no authority
                validates it).

        Returns:
            Configured MoneyContract instance.
        """
        return MoneyContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            precision=precision,
            dollar_sign_currency=dollar_sign_currency,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: MoneyNotation,
    ) -> str:
        """Render a default code_amount canonical value in the requested format.

        The default ``"code_amount"`` path is the identity: the rule-produced
        ``CODE + " " + amount`` canonical value is returned unchanged.
        ``"compact"`` removes the single ASCII space between the code and the
        amount (``"USD 500.00"`` -> ``"USD500.00"``).

        The removal is safe because the canonical value's only ASCII space is
        the code/amount separator: the space_decimal amount shape carries a
        NARROW NO-BREAK SPACE (U+202F) in its token, never an ASCII space, so
        ``replace(" ", "", 1)`` always strips exactly the separator.

        Args:
            value: The default canonical value produced by ``Rule.normalize()``
                (``CODE + " " + amount``, e.g. ``"USD 500.00"``).
            output_format: The contract's resolved output format (``"code_amount"``
                or ``"compact"``).
            notation: The original money notation that produced the canonical
                value, retained for interface compatibility.

        Returns:
            The value rendered in the requested format.
        """
        if output_format == "compact":
            # The amount never contains an ASCII space (space_decimal uses a
            # NARROW NO-BREAK SPACE, U+202F); the only ASCII space in the
            # canonical value is the code/amount separator.
            return value.replace(" ", "", 1)
        return value
