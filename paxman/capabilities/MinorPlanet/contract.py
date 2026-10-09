"""MinorPlanet contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class MinorPlanetContract(CapabilityContract):
    """User-facing configuration for the MinorPlanet capability.

    Formats (ADR-0011 classes): ``designation`` is the unpacked canonical
    (``1995 XA`` / ``(433)`` / ``2040 P-L``, default); ``packed`` is the
    same-entity wire encoding — encoding (``J95X00A`` / ``03202`` /
    ``PLS2040``, case-exact, re-enters through the packed branch).

    Attributes:
        capability_name: Fixed to "minor_planet" (not user-settable).
        output_format: Canonical output format — "designation" by default,
            "packed" offered. Optional — None/"default"/"designation" all
            resolve to "designation".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
        suppress_common_words: Suppress common-word spans (inherited).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "designation"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"packed"})

    capability_name: str = field(default="minor_planet", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
