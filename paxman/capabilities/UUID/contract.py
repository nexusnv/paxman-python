"""UUID contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class UUIDContract(CapabilityContract):
    """User-facing configuration for the UUID capability.

    Formats (ADR-0011 classes): ``compact`` — encoding (hyphen strip);
    ``braced`` — encoding (``{}`` wrapper); ``urn`` — encoding
    (``urn:uuid:`` prefix; all three re-enter under the default contract).

    Attributes:
        capability_name: Fixed to "uuid" (not user-settable).
        output_format: Canonical output format — "hyphenated" (lowercase
            8-4-4-4-12) is the default; "compact", "braced", and "urn" are
            offered. Optional — None/"default"/"hyphenated" all resolve to
            "hyphenated".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "hyphenated"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"compact", "braced", "urn"}
    )

    capability_name: str = field(default="uuid", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
