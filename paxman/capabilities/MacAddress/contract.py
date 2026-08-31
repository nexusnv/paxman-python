"""MacAddress contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class MacAddressContract(CapabilityContract):
    """User-facing configuration for the MacAddress capability.

    Attributes:
        capability_name: Fixed to "mac_address" (not user-settable).
        output_format: Canonical output format — "colon" is the only
            format. Optional — None/"default"/"colon" all resolve to
            "colon".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "colon"
    # TODO(scaffold): offer alternative output formats here.
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="mac_address", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
