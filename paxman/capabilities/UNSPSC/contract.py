"""UNSPSC contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class UNSPSCContract(CapabilityContract):
    """User-facing configuration for the UNSPSC capability.

    Formats (ADR-0011 classes): ``unspsc`` is the wire encoding
    (8-digit compact, default); ``labeled`` is the label-carrier encoding
    (``UNSPSC <stem>``, 1:1 reversible); ``native`` is the
    spelling-preserving encoding (6-digit stays 6-digit, 10-digit keeps
    its suffix; injective across length lanes).

    ``segmented`` (pair-hyphenated display) is deliberately NOT offered:
    the grammar rejects internal hyphens by design, so a segmented
    rendering could never re-enter (ADR-0010 fixed-point).

    Attributes:
        capability_name: Fixed to "unspsc" (not user-settable).
        output_format: Canonical output format — "unspsc" is the default
            8-digit wire stem; "labeled" and "native" are offered as
            presentation-only re-encodings. Optional —
            None/"default"/"unspsc" all resolve to "unspsc".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
        include_business_function: Gate for the 10-digit business-function
            suffix rule (default True; dropped rule → INVALID for 10-digit
            inputs, never MISSING).
        include_live_membership: Rolling-liveness interpretation selector
            (default False; pinned v26.0801 snapshot is the default truth).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "unspsc"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"labeled", "native"})

    capability_name: str = field(default="unspsc", init=False)
    include_business_function: bool = True
    include_live_membership: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
