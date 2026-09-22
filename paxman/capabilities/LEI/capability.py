"""LEI capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.LEI.contract import LEIContract
from paxman.capabilities.LEI.grammar.lei_recognition import (
    LEIRecognition,
)
from paxman.capabilities.LEI.notation import LEINotation
from paxman.capabilities.LEI.rules.gleif_lou_prefix_list_ed2026 import (
    Section1LOUPrefixMembership,
)
from paxman.capabilities.LEI.rules.iso_17442_1_ed2020 import (
    Section4LEIStructureMOD9710,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class LEICapability(Capability[LEINotation]):
    """LEI canonicalization — compact 20-char LOU+entity+check.

    Recognizes compact/lowercase/single-spaced ``LEI:``-labeled and
    ``urn:lei:``-carried mentions via :class:`LEIRecognitionGrammar` and
    validates via ISO 17442-1:2020 structure + whole-string MOD 97-10
    (:class:`Section4LEIStructureMOD9710`) plus GLEIF accredited-LOU
    prefix membership (:class:`Section1LOUPrefixMembership`). Single-value:
    two distinct LEIs in one call raise ``MultipleMentionsError``.
    ``format_value`` renders ``urn`` as ``urn:lei:<compact>``; ``lei``
    (default) is the compact identity.
    """

    name = "lei"

    def get_grammars(self) -> list[Grammar[LEINotation]]:
        """Return the default grammar instances."""
        return [LEIRecognition()]

    def get_rules(self) -> list[Rule[LEINotation]]:
        """Return the default validation rule instances."""
        return [Section4LEIStructureMOD9710(), Section1LOUPrefixMembership()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> LEIContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"lei" resolve to "lei"; "urn" renders the
                ``urn:lei:`` carrier.
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word boundary claims.

        Returns:
            Configured LEIContract instance.
        """
        return LEIContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )

    # format_value is overridden in the presentation task — see the class's
    # ``urn`` offered format (LEIContract.OFFERED_OUTPUT_FORMATS).
    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: LEINotation,
    ) -> str:
        """Render the compact canonical value in the requested format.

        The default ``"lei"`` path is identity. ``"urn"`` renders
        ``urn:lei:<compact>`` as a carrier-only re-encoding that
        re-enters exactly via the grammar's ``urn:lei:`` carrier branch.
        Never affects candidate identity or provenance.
        """
        if output_format == "urn":
            return f"urn:lei:{value}"
        return value
