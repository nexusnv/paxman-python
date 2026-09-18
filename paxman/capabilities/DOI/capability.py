"""DOI capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.DOI.contract import DOIContract
from paxman.capabilities.DOI.grammar.doi_recognition import (
    DOIRecognitionGrammar,
)
from paxman.capabilities.DOI.notation import DOINotation
from paxman.capabilities.DOI.rules.iso_26324_ed2025 import Section4DOISyntax
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class DOICapability(Capability[DOINotation]):
    """DOI canonicalization capability.

    Recognizes bare/case-variant/resolver-URL/``doi:``-label/``urn:doi:``/
    ``info:doi/`` DOI mentions and validates them structurally against
    ISO 26324:2025 (no checksum, no registry). Canonical form is the
    ASCII-folded bare ``10.registrant/suffix`` name.
    """

    name = "doi"

    def get_grammars(self) -> list[Grammar[DOINotation]]:
        """Return the default grammar instances."""
        return [DOIRecognitionGrammar()]

    def get_rules(self) -> list[Rule[DOINotation]]:
        """Return the default validation rule instances."""
        return [Section4DOISyntax()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> DOIContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"doi" resolve to "doi".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word matches.

        Returns:
            Configured DOIContract instance.
        """
        return DOIContract(
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
        notation: DOINotation,
    ) -> str:
        """Render the bare canonical value in the requested format.

        The default ``"doi"`` path is identity. ``"url"`` prepends the
        canonical https resolver host. Never affects candidate identity
        or provenance.
        """
        if output_format == "url":
            return f"https://doi.org/{notation.canonical}"
        return value
