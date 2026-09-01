"""ISBN contract — user-facing configuration for ISBN capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ISBNContract(CapabilityContract):
    """User-facing configuration for ISBN capability.

    Attributes:
        capability_name: Fixed to "isbn" (not user-settable).
        output_format: Canonical output format ("isbn13" default, "hyphenated"
            offered). Optional — None/"default"/"isbn13" all resolve to
            "isbn13" via ``CapabilityContract.__post_init__``.
        excluded_rules: Tuple of rule names to exclude from validation.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering (unused for ISBN, present for
            contract uniformity).
        extra_grammars: Tuple of community grammar names to run alongside
            shipped grammars.
        suppress_common_words: Hide matches that are common English words
            (default False; uses BoundarySpec WORD guard).
        include_isbn10: Enable legacy ISBN-10 input recognition (default
            True). When False, ISBN-10 input yields MISSING.
        include_range_validation: Gate the Range Message validation rule
            (default False). When True, adds registrant-range provenance via
            Section 4-registrant-range.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isbn13"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"hyphenated"})

    capability_name: str = field(default="isbn", init=False)

    # Capability-specific fields
    include_isbn10: bool = True
    include_range_validation: bool = False

    @property
    def active_grammars(self) -> list[str]:
        """isbn13 grammar always active; isbn10 gated by include_isbn10.

        Returns:
            List of grammar names to activate.
        """
        grammars = ["isbn13_recognition"]
        if self.include_isbn10:
            grammars.append("isbn10_recognition")
        return grammars
