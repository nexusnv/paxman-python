"""Language contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class LanguageContract(CapabilityContract):
    """Contract for the Language capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "bcp47"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"alpha2", "alpha3", "alpha3-bib", "name"}
    )
    capability_name: str = field(default="language", init=False)
    include_localized: bool = False
    include_collective: bool = False
    include_private: bool = False
