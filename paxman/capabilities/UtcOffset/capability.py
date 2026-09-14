"""UtcOffset capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.UtcOffset.contract import UtcOffsetContract
from paxman.capabilities.UtcOffset.grammar.utc_offset_recognition import (
    UtcOffsetGrammar,
)
from paxman.capabilities.UtcOffset.notation import UtcOffsetNotation
from paxman.capabilities.UtcOffset.rules.iso8601_offset_ed2019 import (
    SectionOffsetStructure,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class UtcOffsetCapability(Capability[UtcOffsetNotation]):
    """UTC offset canonicalization.

    Recognizes human-notation numeric offsets (``UTC``/``GMT`` prefix
    optional, ``±HH`` / ``±HHMM`` / ``±HH:MM``, ``Z``); validates shape
    plus the real-world total-minutes range against ISO 8601-1:2019 (the
    RFC 3339 unknown-offset ``-00:00`` is refused). Canonical form is
    extended ``+HH:MM``; ``basic`` is offered as a presentation-only
    re-encoding.
    """

    name = "utc_offset"

    def get_grammars(self) -> list[Grammar[UtcOffsetNotation]]:
        """Return the default grammar instances."""
        return [UtcOffsetGrammar()]

    def get_rules(self) -> list[Rule[UtcOffsetNotation]]:
        """Return the default validation rule instances."""
        return [SectionOffsetStructure()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> UtcOffsetContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"extended" resolve to "extended".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress whole-input common-word
                mentions (no-op here: the offset matcher is not
                suppressible).

        Returns:
            Configured UtcOffsetContract instance.
        """
        return UtcOffsetContract(
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
        notation: UtcOffsetNotation,
    ) -> str:
        """Render a canonical extended ``+HH:MM`` value in the format.

        The default ``"extended"`` path is the identity. ``"basic"``
        strips the colon (``+05:30`` → ``+0530``) — a presentation-only
        re-encoding that re-enters: the basic form normalizes back to the
        same extended canonical (ADR-0010).
        """
        if output_format == "basic":
            return value.replace(":", "")
        return value
