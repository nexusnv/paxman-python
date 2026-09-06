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
            Input-only: it plays no role in output rendering.
        output_format: Canonical output format ("e164" default, "rfc3966",
            or "split" rendering "+CC NSN", e.g. "+1 2125551234"). Optional —
            None/"default"/"e164" all resolve to "e164".
            ``"national"`` was de-offered per ADR-0011 (it dropped the
            country code and could not re-enter under the default contract);
            requesting it raises ``ContractError`` with a migration message
            naming ``"split"``. ``"split"`` preserves every field (CC, NSN,
            "+" sigil; the space is presentation-only and stripped on
            re-entry) and re-enters param-free via the existing E.164
            grammar; ``CC + space + NSN`` is a bijection over the canonical
            space (entity-relative injectivity).
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
        year: Year for temporal filtering.

    Formats (ADR-0011 classes): ``rfc3966`` — encoding (``tel:`` scheme
    wrap; every digit preserved); ``split`` — encoding (``CC NSN``
    bijection over the canonical space; param-free re-entry via the E.164
    grammar). ``national`` was a projection and is de-offered (see
    ``output_format`` above).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "e164"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"rfc3966", "split"})

    capability_name: str = field(default="phone", init=False)

    # Capability-specific fields
    default_country: str | None = None

    def __post_init__(self) -> None:
        """Validate contract configuration.

        Pre-checks removed ``national`` for a migration error, then calls
        base resolution, then validates ``default_country``. This is the
        sole intentional exception to the base's super-first ordering (all
        other contracts call ``super().__post_init__()`` first).

        Two consequences of that ordering: the ``national`` pre-check is an
        exact match on ``output_format == "national"`` — case variants
        (e.g. ``"NATIONAL"``) fall through to the base resolution's generic
        unsupported-format error instead of the migration message
        (acceptable: it matches the base resolver's exactness) — and the
        removed-format rejection precedes ``default_country`` validation,
        so ``PhoneContract(output_format="national",
        default_country="USA")`` reports the migration error, not the
        alpha-2 error.

        ``output_format="national"`` was de-offered per ADR-0011 and is
        rejected here with a migration message naming ``"split"`` before
        the base class raises its generic unsupported-format error.

        Raises:
            ContractError: If output_format is unsupported (including the
                removed "national"), or default_country is present but not
                an uppercase alpha-2 code.
        """
        if self.output_format == "national":
            raise ContractError(
                "output_format 'national' was removed per ADR-0011 — it dropped "
                "the country code and could not re-enter without default_country. "
                "Use output_format='split' (renders '+1 2125551234') or the "
                "default 'e164'."
            )
        super().__post_init__()
        _validate_alpha2(self.default_country)
