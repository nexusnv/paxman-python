"""ISIN contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class ISINContract(CapabilityContract):
    """User-facing configuration for the ISIN capability.

    Default ``isin`` is the compact uppercase 12-character ``CC+NSIN+C``
    form. ``grouped`` renders ``CC NNNNNN NNN C`` (2+6+3+1) for readability
    via ``ISINCapability.format_value`` — the only presentation seam.

    Formats (ADR-0011 classes): ``grouped`` — encoding (single-space
    grouping is presentation-only; validation runs on the stripped
    compact form, so the rendering re-enters exactly).

    Attributes:
        capability_name: Fixed to "isin" (not user-settable).
        output_format: Canonical output format — "isin" is the default
            (compact); "grouped" renders the space-separated display
            form. Optional — None/"default"/"isin" all resolve to
            "isin".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isin"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped"})

    capability_name: str = field(default="isin", init=False)

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
