"""MacAddress capability package."""

from __future__ import annotations

from paxman.capabilities.MacAddress.capability import MacAddressCapability
from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.notation import MacAddressNotation

MacAddress = MacAddressCapability

__all__ = [
    "MacAddress",
    "MacAddressCapability",
    "MacAddressContract",
    "MacAddressNotation",
]
