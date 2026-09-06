"""ORCID contract configuration."""

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ORCIDContract(CapabilityContract):
    """Contract for the ORCID capability.

    Formats (ADR-0011 classes): ``compact`` — encoding (hyphen strip; MOD
    11-2 runs on the digits, unaffected); ``uri`` — encoding
    (``https://orcid.org/`` prefix; both re-enter under the default
    contract).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "orcid"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"uri", "compact"})

    capability_name: str = field(default="orcid", init=False)
