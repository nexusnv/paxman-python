"""Domain contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class DomainContract(CapabilityContract):
    """User-facing configuration for the Domain capability.

    Attributes:
        capability_name: Fixed to "domain" (not user-settable).
        output_format: Canonical output format — "ascii" is the only
            format. Optional — None/"default"/"ascii" all resolve to
            "ascii".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "ascii"
    # TODO(scaffold): offer alternative output formats here.
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="domain", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
