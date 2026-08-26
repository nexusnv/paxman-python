"""ISBN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISBN.contract import ISBNContract
from paxman.capabilities.ISBN.grammar.isbn10_recognition import (
    ISBN10RecognitionGrammar,
)
from paxman.capabilities.ISBN.grammar.isbn13_recognition import (
    ISBN13RecognitionGrammar,
)
from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.capabilities.ISBN.rules.data.range_message import (
    EAN_PREFIX_RULES,
    GROUP_RULES,
)
from paxman.capabilities.ISBN.rules.isbn_range_message_ed2026 import (
    Section4RegistrantRange,
)
from paxman.capabilities.ISBN.rules.isbn_users_manual_ed2012 import (
    Section6Isbn10CheckDigit,
)
from paxman.capabilities.ISBN.rules.iso_2108_ed2017 import (
    Section42Gs1Prefix,
    Section53Isbn13CheckDigit,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ISBNCapability", "ISBNContract", "ISBNNotation"]


def _find_length(rules: tuple[tuple[str, str, int], ...], digits: str) -> int | None:
    """Length of the first rule whose 7-digit window covers the digit prefix."""
    window = (digits + "0" * 7)[:7]
    for start, end, length in rules:
        if start <= window <= end:
            return length
    return None


def _hyphenate(value: str) -> str:
    """Render a 13-digit ISBN with Range Message hyphens (memo §4.3).

    Unregistered prefixes/groups/registrants pass through unchanged (bare
    digits) — hyphenation is presentation, never a validity signal.
    """
    if len(value) != 13:
        return value
    prefix = value[:3]
    rest = value[3:]
    prefix_rules = EAN_PREFIX_RULES.get(prefix)
    if prefix_rules is None:
        return value
    group_len = _find_length(prefix_rules, rest)
    if group_len is None:
        return value
    group = rest[:group_len]
    registrant_rules = GROUP_RULES.get(f"{prefix}-{group}")
    if registrant_rules is None:
        return value
    registrant_len = _find_length(registrant_rules, rest[group_len:])
    if registrant_len is None:
        return value
    registrant = rest[group_len : group_len + registrant_len]
    publication = rest[group_len + registrant_len : 9]
    check = rest[9]
    return f"{prefix}-{group}-{registrant}-{publication}-{check}"


class ISBNCapability(Capability[ISBNNotation]):
    """ISBN canonicalization capability.

    Canonicalizes ISBN-13 and legacy ISBN-10 input to the bare 13-digit
    form with full provenance.
    """

    name = "isbn"

    def get_grammars(self) -> list[Grammar[ISBNNotation]]:
        return [ISBN13RecognitionGrammar(), ISBN10RecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISBNNotation]]:
        return [
            Section53Isbn13CheckDigit(),
            Section42Gs1Prefix(),
            Section6Isbn10CheckDigit(),
            Section4RegistrantRange(),
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
        include_isbn10: bool = True,
        include_range_validation: bool = False,
    ) -> ISBNContract:
        """Factory method for creating contracts with proper defaults."""
        return ISBNContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            include_isbn10=include_isbn10,
            include_range_validation=include_range_validation,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ISBNNotation,
    ) -> str:
        """Render the bare 13-digit canonical value in the requested format.

        The default ``"isbn13"`` path is the identity. ``"hyphenated"``
        applies Range Message longest-match hyphenation. Never affects
        candidate identity or provenance.
        """
        if output_format == "hyphenated":
            return _hyphenate(value)
        return value
