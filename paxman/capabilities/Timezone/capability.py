"""Timezone capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Timezone.contract import TimezoneContract
from paxman.capabilities.Timezone.grammar.timezone_abbreviation_recognition import (
    TimezoneAbbreviationGrammar,
)
from paxman.capabilities.Timezone.grammar.timezone_name_recognition import (
    TimezoneNameGrammar,
)
from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.capabilities.Timezone.rules.iana_tz_abbreviations_ed2026 import (
    SectionAbbreviationRefusal,
)
from paxman.capabilities.Timezone.rules.iana_tzdb_ed2026 import (
    SectionLinkResolution,
    SectionSystemVZones,
    SectionZoneKeyMembership,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class TimezoneCapability(Capability[TimezoneNotation]):
    """IANA time zone identifier canonicalization.

    Recognizes zone keys and legacy Links (name family, case-folded) plus
    bare abbreviations (recognized but refused, never resolved); validates
    key membership and Link resolution against the vendored tzdb 2026d
    snapshot, with POSIX SystemV Zones behind the ``include_systemv`` flag.
    """

    name = "timezone"

    def get_grammars(self) -> list[Grammar[TimezoneNotation]]:
        """Return the default grammar instances (name + abbreviation)."""
        return [TimezoneNameGrammar(), TimezoneAbbreviationGrammar()]

    def get_rules(self) -> list[Rule[TimezoneNotation]]:
        """Return the default validation rule instances."""
        return [
            SectionZoneKeyMembership(),
            SectionLinkResolution(),
            SectionSystemVZones(),
            SectionAbbreviationRefusal(),
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
        include_systemv: bool = False,
    ) -> TimezoneContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"iana" resolve to "iana".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress whole-input common-word
                mentions (no-op here: no Timezone matcher is suppressible).
            include_systemv: Include POSIX SystemV Zones (``EST5EDT`` and
                kin) in validation. Optional — defaults to False
                (recognized but INVALID unless opted in).

        Returns:
            Configured TimezoneContract instance.
        """
        return TimezoneContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
            include_systemv=include_systemv,
        )

    # format_value: NOT overridden — the canonical value IS the default
    # format, and OFFERED_OUTPUT_FORMATS is empty (identity default). The
    # Capability base provides the identity formatter; any non-default
    # output_format already raises ContractError at contract construction.
