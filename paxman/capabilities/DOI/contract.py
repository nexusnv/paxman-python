"""DOI contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class DOIContract(CapabilityContract):
    """User-facing configuration for the DOI capability.

    Formats (ADR-0011 classes): ``url`` — encoding (``https://doi.org/``
    prefix; re-enters under the default contract).

    Attributes:
        capability_name: Fixed to "doi" (not user-settable).
        output_format: Canonical output format — "doi" is the default
            (bare ``10.registrant/suffix``); "url" renders the
            ``https://doi.org/`` resolver link. Optional —
            None/"default"/"doi" all resolve to "doi".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "doi"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"url"})

    capability_name: str = field(default="doi", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
