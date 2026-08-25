"""Date canonicalization capability."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.grammar.european_recognition import (
    EuropeanDateGrammar,
)
from paxman.capabilities.Date.grammar.iso8601_recognition import (
    ISO8601DateGrammar,
)
from paxman.capabilities.Date.grammar.slash_iso_recognition import (
    SlashISODateGrammar,
)
from paxman.capabilities.Date.grammar.us_recognition import USDateGrammar
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Date.rules.en_50160_ed2010 import Section4DateFormat
from paxman.capabilities.Date.rules.iso_8601_ed2019 import Section431CalendarDate
from paxman.capabilities.Date.rules.us_federal_rules_ed2023 import (
    Section1DateFormat,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["DateCapability", "DateContract"]


class DateCapability(Capability[DateNotation]):
    """Date canonicalization capability.

    Recognizes strict ISO ``YYYY-MM-DD`` (dash, 2-digit month/day),
    lenient slash-ISO ``YYYY/MM/DD`` (1-2 digit month/day), and slash
    ``MM/DD/YYYY`` / ``DD/MM/YYYY`` with cross-grammar ambiguity handling.
    Validates via ISO 8601-1:2019 (strict) and US/European civilian
    conventions (GPO Style Manual / Unicode CLDR). Normalizes to ISO
    ``YYYY-MM-DD`` by default; ``output_format="US"`` renders ``MM/DD/YYYY``.

    Two-digit years use ``DateContract.two_digit_base_year`` (default 2000,
    explicit 0 honored, validated 0..9999).
    """

    name = "date"

    def get_grammars(self) -> list[Grammar[DateNotation]]:
        return [
            ISO8601DateGrammar(),
            USDateGrammar(),
            EuropeanDateGrammar(),
            SlashISODateGrammar(),
        ]

    def get_rules(self) -> list[Rule[DateNotation]]:
        return [
            Section431CalendarDate(),
            Section1DateFormat(),
            Section4DateFormat(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        two_digit_base_year: int | None = None,
    ) -> DateContract:
        """Create a DateContract with the given configuration."""
        return DateContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            two_digit_base_year=two_digit_base_year,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: DateNotation,
    ) -> str:
        """Render a default ISO canonical date in the requested format.

        The default ISO path is the identity: the rule-produced ``YYYY-MM-DD``
        canonical value is returned unchanged. An explicit ``"US"`` request
        converts a validated fixed-shape ``YYYY-MM-DD`` value to ``MM/DD/YYYY``
        by strict parsing; values that do not match the fixed-width shape
        (e.g. ``2026-1-5``) raise rather than being rendered as if they were
        valid.

        Args:
            value: The default canonical value produced by ``Rule.normalize()``.
            output_format: The contract's resolved output format (``"ISO"`` or
                ``"US"``).
            notation: The original date notation that produced the canonical
                value, retained for interface compatibility.

        Returns:
            The date rendered in the requested format.
        """
        if output_format != "US":
            return value
        if len(value) != 10 or value[4] != "-" or value[7] != "-":
            raise ValueError(
                f"Invalid ISO date {value!r}: expected fixed-shape YYYY-MM-DD"
            )
        parsed = datetime.strptime(value, "%Y-%m-%d")
        return f"{parsed.month:02d}/{parsed.day:02d}/{parsed.year:04d}"
