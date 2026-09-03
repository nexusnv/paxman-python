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
    an EUI-64; deterministic value transform). No grammar-toggle fields: the
    single shipped grammar is always active (base ``active_grammars is None``).

    ``bit_reversed`` (RFC 2469 per-octet bit swap) was removed in 0.4.0:
    its rendering is an involution (``f(f(x)) == x``) and therefore not a
    fixed point — ``canonicalize(V, bit_reversed)`` flips again to ``W != V``.
    Per ADR-0010 an offered format must re-enter as itself, so the view is
    no longer offered. Use the default ``colon`` form for round-trippable
    storage.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "colon"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"hyphen", "bare", "cisco", "eui64"}
    )

    capability_name: str = field(default="mac_address", init=False)
    # OUI registry layer deferred: include_oui_validation: bool = False
