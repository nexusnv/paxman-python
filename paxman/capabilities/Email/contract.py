"""Email contract for Email capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class EmailContract(CapabilityContract):
    """User-facing contract for Email capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "email"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="email", init=False)
    include_obfuscated: bool = False
    include_localhost: bool = True

    @property
    def active_grammars(self) -> list[str]:
        """Grammar names enabled by ``include_*`` flags."""
        grammar_rules: dict[str, bool] = {
            "standard_recognition": True,
            "obfuscated_recognition": self.include_obfuscated,
            "localhost_recognition": self.include_localhost,
        }
        return [name for name, active in grammar_rules.items() if active]
