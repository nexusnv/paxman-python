"""Date contract for Date capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract
from paxman.core.errors import ContractError

# Legacy rule-name aliases — preserve pinned_rules/excluded_rules selection
# after the audit renames (Section 1/4 → Derived, 4.3.1 → 5.2.1.1).
# Canonical names are the derived/5.2.1.1 forms; the Section-form identifiers
# are resolved here so existing contracts keep working.
_LEGACY_RULE_NAME_MAP: dict[str, str] = {
    "Section 1-date-format": "Derived-US-date-format",
    "Section 4-date-format": "Derived-European-date-format",
    "Section 4.3.1-calendar-date": "Section 5.2.1.1-calendar-date",
}


@dataclass(frozen=True)
class DateContract(CapabilityContract):
    """User-facing contract for Date capability.

    Date's default canonical output is ``"ISO"``. Accepted ``output_format``
    values are ``None`` (unset), ``"default"``, ``"ISO"`` (the default), and
    the offered alternative ``"US"``; anything else raises
    :class:`ContractError` from the base ``__post_init__``.

    Attributes:
        two_digit_base_year: Base year for interpreting two-digit years.
            ``None`` defaults to 2000; explicit ``0`` is honored (year 26 → 0026).
            Must be in ``0 <= year <= 9999`` when set — out-of-range raises
            ``ContractError``.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "ISO"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"US"})

    capability_name: str = field(default="date", init=False)
    two_digit_base_year: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        # Resolve legacy rule names so pinned_rules / excluded_rules remain
        # compatible with contracts that used Section-form identifiers.
        if self.pinned_rules is not None:
            mapped = tuple(_LEGACY_RULE_NAME_MAP.get(n, n) for n in self.pinned_rules)
            if mapped != self.pinned_rules:
                object.__setattr__(self, "pinned_rules", mapped)
        if self.excluded_rules != ():
            mapped_ex = tuple(
                _LEGACY_RULE_NAME_MAP.get(n, n) for n in self.excluded_rules
            )
            if mapped_ex != self.excluded_rules:
                object.__setattr__(self, "excluded_rules", mapped_ex)
        if self.two_digit_base_year is not None:
            base = self.two_digit_base_year
            if not 0 <= base <= 9999:
                raise ContractError(
                    f"two_digit_base_year must be in 0..9999, got {base!r}"
                )
