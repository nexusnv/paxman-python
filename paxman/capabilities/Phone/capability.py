"""Phone capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.grammar.e164_recognition import E164Grammar
from paxman.capabilities.Phone.grammar.international_00_recognition import (
    International00Grammar,
)
from paxman.capabilities.Phone.grammar.national_recognition import NationalGrammar
from paxman.capabilities.Phone.grammar.tel_uri_recognition import TelUriGrammar
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.capabilities.Phone.rules.data.e164_country_codes import (
    split_country_code,
)
from paxman.capabilities.Phone.rules.e164_ed2010 import (
    Section6_1InternationalNumber,
    Section6_2CountryCode,
)
from paxman.capabilities.Phone.rules.nanp_ed2024 import (
    Section1_1NANPStructure,
    Section1_2ServiceNPA,
)
from paxman.capabilities.Phone.rules.rfc_3966_ed2004 import Section3TelUri
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["PhoneCapability", "PhoneContract", "PhoneNotation"]


def _format_split(value: str) -> str:
    """Render an E.164 canonical value as "+CC NSN" (single ASCII space)."""
    digits = value[1:] if value.startswith("+") else value
    country_code = split_country_code(digits)
    if country_code is None:
        # unreachable post-matches(); defensive best-effort
        return value
    return f"+{country_code} {digits[len(country_code):]}"


class PhoneCapability(Capability[PhoneNotation]):
    """Phone canonicalization capability.

    Canonicalizes phone numbers (E.164 international, NANP national,
    RFC 3966 tel-URI) to E.164 format with full provenance.
    """

    name = "phone"

    def get_grammars(self) -> list[Grammar[PhoneNotation]]:
        """Return all grammar instances.

        Returns:
            List of 4 grammars: e164, tel-URI, international-00, national.
        """
        return [
            E164Grammar(),
            TelUriGrammar(),
            International00Grammar(),
            NationalGrammar(),
        ]

    def get_rules(self) -> list[Rule[PhoneNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 5 rules: E.164 structure, E.164 country code,
            RFC 3966 tel-URI, NANP structure, NANP service NPA.
        """
        return [
            Section6_1InternationalNumber(),
            Section6_2CountryCode(),
            Section3TelUri(),
            Section1_1NANPStructure(),
            Section1_2ServiceNPA(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
        default_country: str | None = None,
    ) -> PhoneContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"e164" resolve to "e164", or one of the
                offered alternatives "rfc3966"/"split". ``"national"`` was
                removed per ADR-0011 (see the ``ContractError`` migration
                message); ``default_country`` is input-only.
            extra_grammars: Community grammar names (opt-in) to run alongside
                the shipped grammars, in order.
            default_country: ISO 3166-1 alpha-2 country code used to resolve
                national-shaped input (e.g., "US"). Input-only; it plays no
                role in output rendering.

        Returns:
            Configured PhoneContract instance.
        """
        return PhoneContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            default_country=default_country,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: PhoneNotation,
    ) -> str:
        """Render a default E.164 canonical value in the requested format.

        The default ``"e164"`` path is the identity: the rule-produced
        ``+CCNSN`` canonical value is returned unchanged. ``"rfc3966"``
        wraps the value in a ``tel:`` URI, appending ``;ext=<extension>``
        only when the notation carries an RFC 3966 extension. ``"split"``
        renders ``"+" + CC + " " + NSN`` (single ASCII space, uniform for
        every country code — e.g. ``+1 2125551234``, ``+44 12341234``);
        ``notation.extension`` is ignored (the canonical value does not
        carry it; ``rfc3966`` is the only extension-preserving format —
        appending an extension would break re-entry since the E.164
        grammar ends its span at the last digit).

        Compliance: no field is removed (CC, NSN, and the ``+`` sigil all
        survive; the space is presentation-only, stripped by
        ``strip_separators`` on re-entry), so every ``split`` value
        re-enters param-free under the default contract via the existing
        E.164 grammar, and ``CC + space + NSN`` is a bijection over the
        canonical space (entity-relative injectivity).

        Args:
            value: The default canonical value produced by ``Rule.normalize()``
                (a leading-``+`` E.164 number).
            output_format: The contract's resolved output format (``"e164"``,
                ``"rfc3966"``, or ``"split"``).
            notation: The original phone notation that produced the canonical
                value; its ``extension`` is retained for RFC 3966 rendering.

        Returns:
            The number rendered in the requested format.
        """
        if output_format == "split":
            return _format_split(value)
        if output_format != "rfc3966":
            return value
        rendered = f"tel:{value}"
        if notation.extension:
            rendered = f"{rendered};ext={notation.extension}"
        return rendered
