"""Timezone contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class TimezoneContract(CapabilityContract):
    """User-facing configuration for the Timezone capability.

    Attributes:
        capability_name: Fixed to "timezone" (not user-settable).
        output_format: Canonical output format — "iana" is the only
            format. Optional — None/"default"/"iana" all resolve to
            "iana".
        include_systemv: Include SystemV zones (``EST5EDT`` and kin) in
            validation. Optional — defaults to False (recognized but
            INVALID unless opted in).
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "iana"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="timezone", init=False)
    include_systemv: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
