"""IBAN contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class IBANContract(CapabilityContract):
    """User-facing contract for IBAN capability.

    Default output is ``electronic`` (compact, e.g. ``DE89...00``).
    ``paper`` renders groups-of-four (e.g. ``DE89 3704 ... 00``) via
    ``IBANCapability.format_value`` — the only presentation seam.
    No feature-gated grammars (single ``iban_recognition``), so
    ``active_grammars`` is the base ``None`` (all shipped).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "electronic"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"paper"})

    capability_name: str = field(default="iban", init=False)
