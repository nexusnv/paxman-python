"""ORCID contract configuration."""

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ORCIDContract(CapabilityContract):
    """Contract for the ORCID capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "orcid"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"uri", "compact"})

    capability_name: str = field(default="orcid", init=False)
