# paxman/capabilities/Money/contract.py
"""Money contract — user-facing configuration for Money capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Literal, cast

from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import ContractError

_PRECISION_VALUES = ("strict", "truncate", "round")


def _validate_alpha3(value: str | None) -> None:
    """Validate an ISO 4217 alpha-3 currency code.

    Args:
        value: Currency code to validate (None is allowed — means "no default").

    Raises:
        ContractError: If the value is present but not an uppercase
            3-letter ASCII ISO 4217 alpha-3 code (or not a str at all).
    """
    if value is None:
        return
    candidate = cast(object, value)
    if not isinstance(candidate, str):
        raise ContractError(
            "dollar_sign_currency must be an uppercase ISO 4217 alpha-3 code, "
            f"got {value!r}"
        )
    if (
        len(candidate) != 3
        or not candidate.isascii()
        or not candidate.isalpha()
        or not candidate.isupper()
    ):
        raise ContractError(
            "dollar_sign_currency must be an uppercase ISO 4217 alpha-3 code, "
            f"got {value!r}"
        )


@dataclass(frozen=True)
class MoneyContract(CapabilityContract):
    """User-facing configuration for Money capability.

    Attributes:
        capability_name: Fixed to "money" (not user-settable).
        precision: Amount normalization to ISO 4217 minor units — "strict"
            (over-precision → INVALID, decided by the rules' matches()),
            "truncate" (excess digits dropped), or "round" (half-to-even).
        dollar_sign_currency: ISO 4217 alpha-3 code (opt-in) used to resolve
            bare multi-candidate symbol input (e.g., "$500" with
            dollar_sign_currency="MYR" → "MYR 500.00"). Defaults to None:
            bare "$" is then recognized but never resolved (status INVALID).
            Never remaps a definitive symbol (e.g. "€" → EUR) or a qualified
            symbol ("US$" → USD).
        output_format: Canonical output format ("code_amount" default;
            "compact" removes the single space). Optional — None/"default"/
            "code_amount" all resolve to "code_amount".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
        year: Year for temporal filtering.

    Formats (ADR-0011 classes): ``compact`` — encoding (removes the single
    ASCII space separator; the amount's U+202F narrow no-break space is
    never touched, so code and amount both survive re-entry).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "code_amount"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact"})

    capability_name: str = field(default="money", init=False)

    # Capability-specific fields
    precision: Literal["strict", "truncate", "round"] = "strict"
    dollar_sign_currency: str | None = None

    def __post_init__(self) -> None:
        """Validate contract configuration.

        Calls the base output_format resolution first, then enforces
        Money-specific rules: precision must be one of "strict"/"truncate"/
        "round" and dollar_sign_currency must be an uppercase ISO 4217
        alpha-3 code when present.

        Raises:
            ContractError: If output_format is unsupported, precision is not
                one of the three, or dollar_sign_currency is present but not an
                uppercase alpha-3 code.
        """
        super().__post_init__()
        candidate = cast(object, self.precision)
        if candidate not in _PRECISION_VALUES:
            raise ContractError(
                "precision must be one of 'strict', 'truncate', or 'round', "
                f"got {self.precision!r}"
            )
        _validate_alpha3(self.dollar_sign_currency)
