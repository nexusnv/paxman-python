"""Date contract for Date capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract
from paxman.core.errors import ContractError


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
        if self.two_digit_base_year is not None:
            base = self.two_digit_base_year
            if not 0 <= base <= 9999:
                raise ContractError(
                    f"two_digit_base_year must be in 0..9999, got {base!r}"
                )
