"""ISIN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISIN.contract import ISINContract
from paxman.capabilities.ISIN.grammar.isin_recognition import (
    ISINRecognition,
)
from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.capabilities.ISIN.rules.anna_isin_guidelines_ed2025 import (
    Section5CountryAndSpecialPrefix,
)
from paxman.capabilities.ISIN.rules.iso_6166_ed2021 import (
    Section4IsinStructureCheckDigit,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class ISINCapability(Capability[ISINNotation]):
    """ISIN canonicalization — compact with grouped presentation.

    Recognizes the 12-character ``CC+NSIN+C`` form (bare, spaced groupings,
    ``ISIN``-labelled) and validates it against ISO 6166:2021 (structure +
    mod-10 check digit) and the ANNA ISIN Guidelines V25 (country/special
    prefix allowlist). Canonical form is the compact uppercase 12-character
    string; ``grouped`` renders ``CC NNNNNN NNN C`` for readability.
    """

    name = "isin"

    def get_grammars(self) -> list[Grammar[ISINNotation]]:
        """Return the default grammar instances."""
        return [ISINRecognition()]

    def get_rules(self) -> list[Rule[ISINNotation]]:
        """Return the default validation rule instances."""
        return [
            Section4IsinStructureCheckDigit(),
            Section5CountryAndSpecialPrefix(),
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
    ) -> ISINContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"isin" resolve to "isin".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word matches.

        Returns:
            Configured ISINContract instance.
        """
        return ISINContract(
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
        notation: ISINNotation,
    ) -> str:
        """Render the compact canonical value in the requested format.

        The default ``"isin"`` path is identity. ``"grouped"`` renders
        ``CC NNNNNN NNN C`` (2+6+3+1) for readability — a presentation-only
        encoding that re-enters exactly (validation runs on the stripped
        compact form). Never affects candidate identity or provenance.
        """
        if output_format == "grouped":
            return f"{value[0:2]} {value[2:8]} {value[8:11]} {value[11:]}"
        return value
