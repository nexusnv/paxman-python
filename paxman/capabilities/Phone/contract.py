"""Phone contract — user-facing configuration for Phone capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, cast

from paxman.core.contract import CapabilityContract
from paxman.core.errors import ContractError


def _validate_alpha2(value: str | None) -> None:
    """Validate an ISO 3166-1 alpha-2 country code.

    Args:
        value: Country code to validate (None is allowed — means "no default").

    Raises:
        ContractError: If the value is present but not an uppercase
            2-letter ASCII ISO 3166-1 alpha-2 code (or not a str at all).
    """
    if value is None:
        return
    candidate = cast(object, value)
    if not isinstance(candidate, str):
        raise ContractError(
            "default_country must be an uppercase ISO 3166-1 alpha-2 code, "
            f"got {value!r}"
        )
    if (
        len(candidate) != 2
        or not candidate.isascii()
        or not candidate.isalpha()
        or not candidate.isupper()
    ):
        raise ContractError(
            "default_country must be an uppercase ISO 3166-1 alpha-2 code, "
            f"got {value!r}"
        )


@dataclass(frozen=True)
class PhoneContract(CapabilityContract):
    """User-facing configuration for Phone capability.

    Attributes:
        capability_name: Fixed to "phone" (not user-settable).
        default_country: ISO 3166-1 alpha-2 country code used to interpret
            national-shaped input (e.g., "US" for "(555) 234-5678"). When None,
            national-shaped input is recognized but never validated (status
            INVALID) — national-shaped numbers carry no country code in their
            digits and so cannot be resolved without a default country.
            Required when ``output_format="national"`` (see ``__post_init__``).
        output_format: Canonical output format ("e164" default, "rfc3966",
            or "national" for the national significant number). Optional —
            None/"default"/"e164" all resolve to "e164". ``"national"``
            requires ``default_country`` to be a NANP country (currently ``"US"``)
            so the rendered NSN can re-enter (ADR-0010).
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
        year: Year for temporal filtering.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "e164"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"rfc3966", "national"}
    )

    capability_name: str = field(default="phone", init=False)

    # Capability-specific fields
    default_country: str | None = None

    # Mirrors nanp_ed2024.py:34 _NANP_COUNTRIES = {"US"}.
    # Kept inline to avoid import cycle (contract -> rules -> contract).
    # TODO: keep in sync with nanp_ed2024._NANP_COUNTRIES when expanded
    # beyond US (ADR-0010).
    PHONE_NATIONAL_COUNTRIES: ClassVar[frozenset[str]] = frozenset({"US"})

    def __post_init__(self) -> None:
        """Validate contract configuration.

        Calls the base resolution first, then enforces Phone-specific rules:
        default_country must be an uppercase alpha-2 code when present.

        ``output_format="national"`` requires ``default_country`` to be a NANP
        country (currently ``"US"`` — see ``PHONE_NATIONAL_COUNTRIES``,
        mirroring ``nanp_ed2024._NANP_COUNTRIES``). Without a country the
        rendered NSN (bare digits, no country code) cannot re-enter under the
        same contract (ADR-0010 Scope decision 2 — unconditional for default
        contracts). The NANP rules already gate ``matches()`` on
        ``default_country``, but the contract now rejects the non-re-enterable
        configuration at construction so a default (country-less) contract can
        never produce a non-re-enterable ``national`` V.

        Raises:
            ContractError: If output_format is unsupported, default_country is
                present but not an uppercase alpha-2 code, or
                output_format is "national" without a NANP default_country.
        """
        super().__post_init__()
        _validate_alpha2(self.default_country)
        if (
            self.output_format == "national"
            and self.default_country not in self.PHONE_NATIONAL_COUNTRIES
        ):
            raise ContractError(
                "output_format 'national' requires default_country to be a "
                f"NANP country (e.g. 'US') for re-entry; got {self.default_country!r}"
            )
