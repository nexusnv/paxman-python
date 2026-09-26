"""ISNI capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISNI.contract import ISNIContract
from paxman.capabilities.ISNI.grammar.isni_recognition import (
    ISNIRecognitionGrammar,
)
from paxman.capabilities.ISNI.notation import ISNINotation
from paxman.capabilities.ISNI.rules.iso_27729_ed2024 import (
    Section4IsniStructure,
    SectionAMod11Dash2,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class ISNICapability(Capability[ISNINotation]):
    """ISNI canonicalization capability (ISO 27729:2024, MOD 11-2).

    Recognizes spaced, compact, hyphenated, labeled, URI, and URN-carried
    ISNI mentions; validates structure plus check digit; canonicalizes to
    the spaced display form.
    """

    name = "isni"

    def get_grammars(self) -> list[Grammar[ISNINotation]]:
        """Return the shipped ISNI grammars in declaration order."""
        return [ISNIRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISNINotation]]:
        """Return the shipped ISNI rules in declaration order."""
        return [Section4IsniStructure(), SectionAMod11Dash2()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> ISNIContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"isni" resolve to "isni".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word boundary claims.

        Returns:
            Configured ISNIContract instance.
        """
        return ISNIContract(
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
        notation: ISNINotation,
    ) -> str:
        """Render spaced (default), compact, or urn:isni: carrier.

        The default "isni" path is identity. "compact" strips the spaces;
        "urn" prepends the IANA-registered carrier. Both re-enter under
        the default contract (ADR-0010 fixed-point).
        """
        if output_format == "compact":
            return notation.compact
        if output_format == "urn":
            return f"urn:isni:{notation.compact}"
        return value
