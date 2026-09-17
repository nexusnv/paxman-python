"""UUID capability — IETF RFC 9562 hex-and-dash identifiers."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.UUID.contract import UUIDContract
from paxman.capabilities.UUID.grammar.uuid_recognition import (
    UUIDRecognitionGrammar,
)
from paxman.capabilities.UUID.notation import UUIDNotation
from paxman.capabilities.UUID.rules.rfc_9562_ed2024 import Section4UUIDFormat
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class UUIDCapability(Capability[UUIDNotation]):
    """UUID canonicalization: hyphenated/bare/braced/URN → lowercase 8-4-4-4-12."""

    name = "uuid"

    def get_grammars(self) -> list[Grammar[UUIDNotation]]:
        """Return the default grammar instances."""
        return [UUIDRecognitionGrammar()]

    def get_rules(self) -> list[Rule[UUIDNotation]]:
        """Return the default validation rule instances."""
        return [Section4UUIDFormat()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> UUIDContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"hyphenated" resolve to "hyphenated".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word matches (no-op
                here — no UUID matcher is suppressible).

        Returns:
            Configured UUIDContract instance.
        """
        return UUIDContract(
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
        notation: UUIDNotation,
    ) -> str:
        """Select the pre-computed carrier (ORCID precedent); default identity."""
        if output_format == "compact":
            return notation.compact
        if output_format == "braced":
            return "{" + notation.hyphenated + "}"
        if output_format == "urn":
            return notation.urn
        return value
