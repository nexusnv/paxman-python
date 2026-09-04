"""User-facing contract for the Element capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ElementContract(CapabilityContract):
    """User-facing contract for the Element capability.

    ``symbol`` (IUPAC proper case, e.g. ``Fe``) is the canonical default;
    ``name`` (lowercase English name, e.g. ``iron``) is the only offered
    alternative. No grammar-toggle fields: the single shipped grammar is
    always active (base ``active_grammars is None``).

    ``atomic_number`` is deliberately not offered: rendering ``Fe`` as bare
    ``"26"`` cannot re-enter — bare integers are unclaimable by design, so
    ``canonicalize("26")`` is ``MISSING`` and the value would not be a
    fixed point. Per ADR-0010 an offered format must re-enter as itself,
    so the view is not offered. Use the default ``symbol`` form for
    round-trippable storage.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "symbol"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"name"})

    capability_name: str = field(default="element", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
