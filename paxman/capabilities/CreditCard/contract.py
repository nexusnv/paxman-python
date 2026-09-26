"""CreditCard contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class CreditCardContract(CapabilityContract):
    """User-facing configuration for the CreditCard capability.

    Default ``pan`` is the compact contiguous 12-19 ASCII-digit form.
    ``grouped`` renders the same digits in groups of four from the left
    (last group takes the remainder) — a grouping-agnostic re-chunk, so an
    Amex 15-digit renders ``3782 8224 6310 005``, never the brand 4-6-5
    layout: presentation never sniffs brand.

    Formats (ADR-0011 classes): ``grouped`` — encoding (the same digits,
    re-chunked; string-exact parametric pre-image, bijective on the
    canonical value, no information is lost or invented).

    Attributes:
        capability_name: Fixed to "credit_card" (not user-settable).
        output_format: Canonical output format — "pan" default,
            "grouped" offered. Optional — None/"default"/"pan" all
            resolve to "pan".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
        suppress_common_words: Suppress common-word boundary claims.
        include_brand_validation: Also require the PAN prefix to be a
            member of the brand-prefix allowlist (default False). Gates
            Section 1-brand-prefix-membership via requires_features.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "pan"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped"})

    capability_name: str = field(default="credit_card", init=False)

    include_brand_validation: bool = False

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
