"""Timezone authority-data consistency (Task 4: vendored tzdb snapshot).

Every identifier the name grammar can claim must be backed by the
vendored rule-data tables, link targets must resolve to canonical keys
in the identifier set, and the abbreviation carve/refusal sets must stay
disjoint from canonical membership. Tables are a curated tzdb 2026d
subset (see module headers); unlisted keys are MISSING, never INVALID.
"""

from __future__ import annotations

import re

import pytest

from paxman.capabilities.Timezone.rules.data.abbreviation_map import (
    CARVED_LINKS,
    REFUSAL_SET,
)
from paxman.capabilities.Timezone.rules.data.iana_fixed_zones import (
    IANA_FIXED_ZONES,
)
from paxman.capabilities.Timezone.rules.data.iana_zone_identifiers import (
    IANA_ZONE_IDENTIFIERS,
)
from paxman.capabilities.Timezone.rules.data.iana_zone_links import (
    IANA_ZONE_LINKS,
)

pytestmark = [pytest.mark.capability]

_SHORT_CAPS_RE = re.compile(r"^[A-Z]{2,5}$")


class TestIdentifierMembership:
    """Canonical keys live in the identifier set, canonical-case exact."""

    @pytest.mark.parametrize(
        "key",
        [
            "America/New_York",
            "America/Chicago",
            "Asia/Kolkata",
            "Australia/Sydney",
            "Europe/Brussels",
            "America/Panama",
            "America/Phoenix",
            "Pacific/Honolulu",
            "UTC",
        ],
    )
    def test_canonical_key_in_identifiers(self, key: str) -> None:
        assert key in IANA_ZONE_IDENTIFIERS

    def test_case_exactness_folding_happens_in_grammar(self) -> None:
        assert "America/New_York" in IANA_ZONE_IDENTIFIERS
        assert "america/new_york" not in IANA_ZONE_IDENTIFIERS

    def test_unknown_key_absent(self) -> None:
        assert "America/Narnia" not in IANA_ZONE_IDENTIFIERS
        assert "Mars/Olympus" not in IANA_ZONE_IDENTIFIERS

    def test_no_bare_short_caps_in_identifiers_except_utc_gmt(self) -> None:
        """Carve rule: short-caps backward Links live in the abbreviation
        family, never in the name identifier set (UTC/GMT excepted)."""
        offenders = sorted(
            k
            for k in IANA_ZONE_IDENTIFIERS
            if _SHORT_CAPS_RE.fullmatch(k) and k not in {"UTC", "GMT"}
        )
        assert not offenders, f"short-caps keys must be carved out: {offenders}"


class TestLinkTable:
    """Lowered link sources resolve to canonical-case targets."""

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            ("us/eastern", "America/New_York"),
            ("asia/calcutta", "Asia/Kolkata"),
            ("australia/act", "Australia/Sydney"),
            ("cet", "Europe/Brussels"),
            ("est", "America/Panama"),
            ("mst", "America/Phoenix"),
            ("hst", "Pacific/Honolulu"),
        ],
    )
    def test_link_resolves_to_canonical(self, source: str, target: str) -> None:
        assert IANA_ZONE_LINKS[source] == target

    def test_link_keys_are_lowered(self) -> None:
        for source in IANA_ZONE_LINKS:
            assert source == source.lower(), f"link key not lowered: {source!r}"

    def test_every_link_target_is_canonical(self) -> None:
        uncovered = sorted(
            t for t in set(IANA_ZONE_LINKS.values()) if t not in IANA_ZONE_IDENTIFIERS
        )
        assert not uncovered, f"link targets missing from identifiers: {uncovered}"

    def test_unknown_link_absent(self) -> None:
        assert "xyz" not in IANA_ZONE_LINKS


class TestFixedZones:
    """Etcetera fixed zones plus bare UTC/GMT."""

    @pytest.mark.parametrize("key", ["Etc/UTC", "Etc/GMT", "UTC", "GMT"])
    def test_fixed_zone_present(self, key: str) -> None:
        assert key in IANA_FIXED_ZONES

    def test_unknown_fixed_absent(self) -> None:
        assert "xyz" not in IANA_FIXED_ZONES


class TestAbbreviationSets:
    """Carved backward Links refused; ambiguous abbreviations refused."""

    @pytest.mark.parametrize("token", ["est", "mst", "hst", "cet"])
    def test_carved_link_refused(self, token: str) -> None:
        assert token in CARVED_LINKS

    @pytest.mark.parametrize("token", ["ist", "cst", "pst"])
    def test_ambiguous_abbreviation_refused(self, token: str) -> None:
        assert token in REFUSAL_SET

    def test_carve_and_refusal_disjoint(self) -> None:
        assert not (CARVED_LINKS & REFUSAL_SET), (
            f"carve/refusal overlap: {sorted(CARVED_LINKS & REFUSAL_SET)}"
        )

    def test_unverified_abbreviations_omitted_unlisted_is_missing(self) -> None:
        """jst/wet/eet/msk are out of the v1 curated subset: absent from
        both sets, so the grammar claims nothing (MISSING, never INVALID)."""
        for token in ("jst", "wet", "eet", "msk"):
            assert token not in REFUSAL_SET, f"{token} must stay unlisted"
            assert token not in CARVED_LINKS, f"{token} must stay unlisted"

    def test_unknown_abbreviation_in_neither_set(self) -> None:
        assert "xyz" not in REFUSAL_SET
        assert "xyz" not in CARVED_LINKS
