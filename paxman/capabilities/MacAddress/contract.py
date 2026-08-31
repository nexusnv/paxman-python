"""User-facing contract for the MacAddress capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class MacAddressContract(CapabilityContract):
    """User-facing contract for the MacAddress capability.

    ``colon`` (uppercase octets) is the canonical default; the offered
    formats are presentation-only re-insertions onto the rule-normalized
    colon form (``eui64`` inserts FF:FE from an EUI-48 and is identity for
    an EUI-64; ``bit_reversed`` is the RFC 2469 per-octet swap; both are
    deterministic value transforms). No grammar-toggle fields: the single
    shipped grammar is always active (base ``active_grammars is None``).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "colon"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"hyphen", "bare", "cisco", "eui64", "bit_reversed"}
    )

    capability_name: str = field(default="mac_address", init=False)
    # Deferred with the OUI registry layer (Research section 5.4 / 13
    # decision 6): include_oui_validation: bool = False
