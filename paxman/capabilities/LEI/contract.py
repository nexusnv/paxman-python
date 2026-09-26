"""LEI contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class LEIContract(CapabilityContract):
    """User-facing configuration for the LEI capability.

    Default ``lei`` is the compact uppercase 20-character
    ``LOU+entity+check`` form. ``urn`` renders ``urn:lei:<compact>`` via
    ``LEICapability.format_value`` — the only presentation seam.

    Formats (ADR-0011 classes): ``urn`` — encoding (carrier-only
    re-encoding; the grammar's ``urn:lei:`` carrier branch re-recognizes
    the rendering to the same compact pre-image, so it re-enters
    exactly).

    Attributes:
        capability_name: Fixed to "lei" (not user-settable).
        output_format: Canonical output format — "lei" is the default
            (compact); "urn" renders the ``urn:lei:`` carrier form.
            Optional — None/"default"/"lei" all resolve to "lei".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "lei"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"urn"})

    capability_name: str = field(default="lei", init=False)

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
