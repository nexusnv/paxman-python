"""Country contract — user-facing configuration for Country capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Final

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class CountryContract(CapabilityContract):
    """User-facing configuration for Country capability.

    Attributes:
        capability_name: Fixed to "country" (not user-settable).
        output_format: Canonical output format ("alpha2" default, "alpha3",
            "numeric", or "name"). Optional — None/"default"/"alpha2" all
            resolve to "alpha2".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
        year: Year for temporal filtering.
        include_localized: Enable CLDR multilingual names.
        include_historical: Enable deprecated country names.

    Formats (ADR-0011 classes): ``alpha3`` — encoding (ISO 3166-1 alpha-3
    table map, 1:1 per entity; re-enters via its own grammar); ``numeric``
    — encoding (UN M49 numeric map); ``name`` — encoding (English
    short-name map; the rendering re-enters through the name grammar).
    Historical codes without a mapping pass through unchanged rather than
    mis-mapping.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "alpha2"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"alpha3", "numeric", "name"}
    )

    capability_name: str = field(default="country", init=False)

    # Capability-specific fields
    include_localized: bool = False
    include_historical: bool = False


VALID_OUTPUT_FORMATS: Final[frozenset[str]] = frozenset(
    {CountryContract.DEFAULT_OUTPUT_FORMAT, *CountryContract.OFFERED_OUTPUT_FORMATS}
)
