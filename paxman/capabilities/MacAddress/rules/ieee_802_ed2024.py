"""IEEE Std 802-2024 - EUI-48/EUI-64 MAC address structure (Section 8.2).

Structure is clause "8.2 Universal addresses" per IEEE Std 802-2014
numbering, the clause the Bluetooth Core Specification cites normatively for
BD_ADDR; verify the clause number against the 802-2024 text (free via the
IEEE GET Program) at implementation. MAC addresses have no checksum and no
check character (Research section 5.1 - proved by absence across IEEE 802,
RFC 7042, and all ecosystem validators): structure is all there is.
"""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IEEE",
    specification_name="IEEE Std 802-2024",
    kind="specification",
    reference_url="https://standards.ieee.org/ieee/802/10894",
    version="2024",
    lifecycle="active",
    publication_year=2024,
)

_VALID_LENGTHS = frozenset({12, 16})
_HEX = frozenset("0123456789ABCDEF")
_SHAPE_BY_LENGTH = {12: "eui48", 16: "eui64"}


class Section82EUIStructure(Rule[MacAddressNotation]):
    """EUI-48/EUI-64 structure per IEEE Std 802 (Section 8.2, 802-2014 numbering).

    Length exactly 12 or 16 uppercase hex digits, shape agreeing with length.
    The I/G bit (0x01, unicast/group) and U/L bit (0x02, universal/local) are
    informative predicates - broadcast, nil, multicast, locally administered,
    FF-FE/FF-FF mid-address markers, and all sentinels are valid. Bit-order
    provenance (Token-Ring/FDDI MSB display) is not detectable and is never
    reinterpreted (Research section 13 decision 10).
    """

    name = "Section 8.2-eui-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 8.2 (Universal addresses; EUI-48/EUI-64, I/G and U/L bits)"
    target_semantics: ClassVar[frozenset[str]] = frozenset({"mac_address_recognition"})
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: MacAddressNotation, contract: Contract) -> bool:
        compact = notation.compact
        if len(compact) not in _VALID_LENGTHS:
            return False
        if any(ch not in _HEX for ch in compact):
            return False
        return notation.shape == _SHAPE_BY_LENGTH[len(compact)]

    def normalize(self, notation: MacAddressNotation, contract: Contract) -> str:
        compact = notation.compact
        return ":".join(compact[i : i + 2] for i in range(0, len(compact), 2))


# Deferred: OUI registry layer — not implemented in v1
# (mirrors BIC SWIFT Directory deferral).
# Planned: ieee_oui_registry_ed2026.py (LOOKUP_TABLE,
#   requires_features={"include_oui_validation"}),
# rules/data/oui_registry.py MA-L snapshot (24-bit OUIs to uppercase
#   6-hex keys, Local bit zero by assignment policy),
# universal-addresses-only with U/L-bit-1 exemption per
# python-stdnum validate_manufacturer precedent.
# Refresh: download IEEE public listing from
# https://regauth.standards.ieee.org/, project MA-L entries to
# 6-hex keys, regenerate via future
# tools/regenerate_oui_registry_data.py. Not implemented.
