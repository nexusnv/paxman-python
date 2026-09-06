"""Language contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class LanguageContract(CapabilityContract):
    """Contract for the Language capability.

    Default ``bcp47`` (case-canonical tag). Offered ``alpha2`` maps the
    primary subtag through the ISO 639 tables and carries the remaining
    subtags verbatim — an encoding per ADR-0011. Offered ``alpha3`` /
    ``alpha3-bib`` map the primary subtag only for mapped primaries
    (identity-mapped primaries such as private-use ``x`` carry the rest
    verbatim — the rendering is the canonical itself); both are waived
    projections for extended tags: a mapped primary plus carried rest
    emits tags the authority rejects — variant Prefix is primary-relative,
    deprecated / macrolanguage resolution is primary-relative). Offered
    ``name`` is the English name of the primary subtag — same waiver class
    per the ADR-0011 soft mandate (revisit at the hard-mandate promotion).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "bcp47"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"alpha2", "alpha3", "alpha3-bib", "name"}
    )
    capability_name: str = field(default="language", init=False)
    include_localized: bool = False
    include_collective: bool = False
    include_private: bool = False
