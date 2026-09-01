"""IP contract for IP capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class IPContract(CapabilityContract):
    """User-facing contract for the IP capability.

    Controls which address families are recognized. The IPv4 grammar is always
    active; the IPv6 grammar is toggled via ``include_ipv6`` (disabled →
    ``MISSING``, not ``INVALID``). The capability has a single canonical
    output format ``"ip"`` (``OFFERED_OUTPUT_FORMATS`` is empty → identity
    ``format_value``). Input containing multiple distinct IPs raises
    ``MultipleMentionsError`` per ``single_value=True`` — see
    ``docs/recipes/segmentation.md``.

    Attributes:
        include_ipv6: When ``False`` only IPv4 is recognized; IPv6 inputs
            yield ``MISSING``.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "ip"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="ip", init=False)
    include_ipv6: bool = True

    @property
    def active_grammars(self) -> list[str]:
        grammars: list[str] = ["ipv4_recognition"]
        if self.include_ipv6:
            grammars.append("ipv6_recognition")
        return grammars
