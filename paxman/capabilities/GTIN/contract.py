"""GTIN contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class GTINContract(CapabilityContract):
    """User-facing configuration for the GTIN capability.

    Default ``gtin14`` is the 14-digit zero-padded storage form (GS1 XML/GDSN).
    ``native`` renders the spelled length via the notation facet slice.

    Formats (ADR-0011 classes): ``native`` — encoding (zero-strip/zero-pad
    reversible without side input; string-exact param-free pre-image;
    identity for true GTIN-14).

    Note: ``hri`` (space-grouped HRI layout) is deferred to a follow-up —
    only the UPC-A (``6 14141 99999 6``) and EAN-8 (``1234 5670``) groupings
    are attested; EAN-13/GTIN-14 groupings are unconfirmed in the fetched
    sources, and groupings are never invented. Contract OFFERED is
    ``{"native"}`` until the HRI Guideline/GenSpecs figures confirm them.

    Attributes:
        capability_name: Fixed to "gtin" (not user-settable).
        output_format: Canonical output format — "gtin14" default,
            "native" offered. Optional — None/"default"/"gtin14"
            all resolve to "gtin14".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
        suppress_common_words: Suppress common-word boundary claims.
        include_verified: Enable Verified by GS1 liveness lookup (default
            False). When True, adds snapshot-liveness provenance via
            Section 3-verified-liveness.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "gtin14"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"native"})

    capability_name: str = field(default="gtin", init=False)

    include_verified: bool = False

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
