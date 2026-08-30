# paxman/capabilities/Currency/capability.py
"""Currency capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Currency.contract import CurrencyContract
from paxman.capabilities.Currency.grammar.code_recognition import CodeRecognition
from paxman.capabilities.Currency.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.Currency.grammar.word_recognition import WordRecognition
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.capabilities.Currency.rules.cldr_currencies_ed2025 import (
    SectionNames,
    SectionSymbols,
)
from paxman.capabilities.Currency.rules.iso_4217_ed2015 import SectionCode
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["CurrencyCapability", "CurrencyContract", "CurrencyNotation"]


class CurrencyCapability(Capability[CurrencyNotation]):
    """Currency canonicalization capability.

    Canonicalizes currency identifiers — an ISO 4217 alpha-3 code, a CLDR
    currency symbol, or a CLDR display-name word — to the uppercase
    alpha-3 code, with full provenance. Identifier-only: amounts are the
    Money capability's domain ("USD 500" resolves via its "USD" span;
    amount-glued tokens like "US$5" are not matched at all).

    Contract opt-in: ``default_currency`` (``str | None``, default ``None``)
    resolves shared bare symbols (``$``, ``¥``, ``£``, ``₩``, ``kr``,
    ``Rs``, ``L``) only when the code is one of that symbol's own
    candidates (gated against the symbol's candidate tuple, not the
    global 178-set). Definitive symbols (``€``→``EUR``) and qualified
    symbols (``US$``→``USD``) ignore ``default_currency``.
    """

    name = "currency"

    def get_grammars(self) -> list[Grammar[CurrencyNotation]]:
        """Return all grammar instances.

        Returns:
            List of 3 grammars: code, symbol, word.
        """
        return [CodeRecognition(), SymbolRecognition(), WordRecognition()]

    def get_rules(self) -> list[Rule[CurrencyNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 3 rules: ISO 4217 codes, CLDR symbols, CLDR names.
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
        default_currency: str | None = None,
    ) -> CurrencyContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"code" resolve to "code".
            extra_grammars: Community grammar names (opt-in) to run alongside
                the shipped grammars, in order.
            default_currency: ISO 4217 alpha-3 code (opt-in) used to
                resolve shared bare symbols (e.g. "$", "¥"). None (the
                default) makes a shared symbol INVALID (recognized, but
                no authority resolves it). Never remaps a definitive
                symbol (e.g. "€" -> EUR) or a qualified symbol ("US$").

        Returns:
            Configured CurrencyContract instance.
        """
        return CurrencyContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            default_currency=default_currency,
        )

    # format_value: NOT overridden — the canonical value IS the "code"
    # format (uppercase alpha-3), and there are no offered alternatives.
    # The Capability base provides the identity formatter.
