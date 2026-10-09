"""MinorPlanet capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.MinorPlanet.contract import MinorPlanetContract
from paxman.capabilities.MinorPlanet.grammar.minor_planet_recognition import (
    MinorPlanetRecognitionGrammar,
)
from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.capabilities.MinorPlanet.rules.mpc_codec import mpc_pack
from paxman.capabilities.MinorPlanet.rules.mpc_numbering import (
    Section5PermanentNumber,
)
from paxman.capabilities.MinorPlanet.rules.mpc_packed_designation import (
    Section3PackedProvisional,
    Section4PackedNumber,
)
from paxman.capabilities.MinorPlanet.rules.mpc_unpacked_designation import (
    Section1UnpackedProvisionalStructure,
    Section2SurveyDesignation,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class MinorPlanetCapability(Capability[MinorPlanetNotation]):
    """Minor-planet canonicalization capability.

    Recognizes unpacked/packed/survey/numbered minor-planet lanes via
    :class:`MinorPlanetRecognitionGrammar` and validates structure-only
    (PARSER, no registry) against MPC DesDoc/PackedDes/HowNamed, with full
    provenance. Canonical form is the unpacked designation
    (``1995 XA`` / ``2040 P-L`` / ``(433)``); ``packed`` is the offered
    same-entity wire encoding.
    """

    name = "minor_planet"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[MinorPlanetNotation]]:
        """Return the default grammar instances."""
        return [MinorPlanetRecognitionGrammar()]

    def get_rules(self) -> list[Rule[MinorPlanetNotation]]:
        """Return the default validation rule instances."""
        return [
            Section1UnpackedProvisionalStructure(),
            Section2SurveyDesignation(),
            Section3PackedProvisional(),
            Section4PackedNumber(),
            Section5PermanentNumber(),
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
    ) -> MinorPlanetContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"designation" resolve to "designation".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word spans.

        Returns:
            Configured MinorPlanetContract instance.
        """
        return MinorPlanetContract(
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
        notation: MinorPlanetNotation,
    ) -> str:
        """Render the canonical designation in the requested format.

        The default ``"designation"`` path is the identity. ``"packed"``
        renders via the shared ``mpc_pack`` helper owned by rules/capability
        (the ``A/`` lane defines no packed mapping and falls back to the
        designation). Never affects candidate identity or provenance.
        """
        if output_format == "packed":
            try:
                rendered = mpc_pack(value)
                if rendered is not None:
                    return rendered
                if notation.packed:
                    return notation.packed
            except (TypeError, AttributeError, ValueError):
                pass
            return value
        return value
