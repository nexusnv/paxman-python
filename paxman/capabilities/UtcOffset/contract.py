"""UtcOffset contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class UtcOffsetContract(CapabilityContract):
    """User-facing configuration for the UtcOffset capability.

    Attributes:
        capability_name: Fixed to "utc_offset" (not user-settable).
        output_format: Canonical output format — "extended" (``+HH:MM``)
            is the default; "basic" (``+HHMM``) is offered as a
            presentation-only re-encoding. Optional — None/"default"/
            "extended" all resolve to "extended".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "extended"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"basic"})

    capability_name: str = field(default="utc_offset", init=False)

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
