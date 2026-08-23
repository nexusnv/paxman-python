"""BIC contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class BICContract(CapabilityContract):
    """User-facing contract for BIC capability.

    Default ``bic`` is compact uppercase 8 or 11, branch as matched.
    ``grouped`` renders ``AAAA BB CC [XXX]`` for readability.
    ``bic11`` always 11, appending ``XXX`` head office when branch absent,
    lossy expansion documented as such.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "bic"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped", "bic11"})

    capability_name: str = field(default="bic", init=False)

    def __post_init__(self) -> None:
        super().__post_init__()
