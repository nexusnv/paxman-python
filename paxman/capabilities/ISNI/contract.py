"""ISNI contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class ISNIContract(CapabilityContract):
    """User-facing configuration for the ISNI capability.

    Default ``isni`` is the spaced display ``XXXX XXXX XXXX XXXC``.
    ``compact`` strips the spaces; ``urn`` renders ``urn:isni:<compact>``
    via ``ISNICapability.format_value`` — the only presentation seam.

    Formats (ADR-0011 classes): ``compact`` — encoding (space strip; MOD
    11-2 runs on the digits, unaffected); ``urn`` — encoding (IANA
    ``urn:isni:`` carrier; the carrier branch re-recognizes the rendering
    to the same compact pre-image, so it re-enters exactly).

    Attributes:
        capability_name: Fixed to "isni" (not user-settable).
        output_format: Canonical output format — "isni" is the default
            (spaced display); "compact" and "urn" are offered as
            presentation-only re-encodings. Optional — None/"default"/
            "isni" all resolve to "isni".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isni"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact", "urn"})

    capability_name: str = field(default="isni", init=False)

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
