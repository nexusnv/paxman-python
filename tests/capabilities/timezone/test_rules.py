"""Tests for Timezone validation rules (Task 6).

IANA Time Zone Database snapshot 2026d: zone-key membership, backward Link
resolution, SystemV flag gating, and abbreviation refusal (carved Links and
ambiguous abbreviations alike — recognized but never resolved).
"""

import pytest

from paxman.capabilities.Timezone.contract import TimezoneContract
from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.capabilities.Timezone.rules.data.abbreviation_map import (
    CARVED_LINKS,
    REFUSAL_SET,
)
from paxman.capabilities.Timezone.rules.iana_tz_abbreviations_ed2026 import (
    SectionAbbreviationRefusal,
)
from paxman.capabilities.Timezone.rules.iana_tzdb_ed2026 import (
    SectionLinkResolution,
    SectionSystemVZones,
    SectionZoneKeyMembership,
)
from paxman.core.domain import RuleStrategy


def _name(key: str) -> TimezoneNotation:
    """Build a name-family notation carrying ``key`` as written."""
    return TimezoneNotation(key=key, family="name", compact=key)


def _abbreviation(token: str) -> TimezoneNotation:
    """Build an abbreviation-family notation carrying ``token`` as written."""
    return TimezoneNotation(key=token, family="abbreviation", compact=token)


@pytest.mark.capability
class TestZoneKeyMembership:
    """Section zone-key-membership — LOOKUP_TABLE over the vendored set."""

    def setup_method(self) -> None:
        self.rule = SectionZoneKeyMembership()
        self.contract = TimezoneContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section zone-key-membership"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"timezone_name"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.citation != ""

    def test_provenance(self) -> None:
        provenance = self.rule.provenance
        assert provenance.authority == "IANA"
        assert provenance.specification_name == "Time Zone Database"
        assert provenance.kind == "registry"
        assert provenance.reference_url == "https://www.iana.org/time-zones"
        assert provenance.version == "2026d"
        assert provenance.lifecycle == "active"
        assert provenance.publication_year == 2026

    def test_canonical_key_matches(self) -> None:
        assert self.rule.matches(_name("America/New_York"), self.contract) is True

    def test_bare_gmt_fixed_zone_matches(self) -> None:
        """Bare GMT resolves like UTC (#161 — was omitted from identifiers)."""
        assert self.rule.matches(_name("GMT"), self.contract) is True
        assert self.rule.normalize(_name("gmt"), self.contract) == "GMT"

    def test_normalize_canonical_key_is_identity(self) -> None:
        assert (
            self.rule.normalize(_name("America/New_York"), self.contract)
            == "America/New_York"
        )

    def test_folded_mention_restores_canonical_case(self) -> None:
        assert self.rule.matches(_name("america/new_york"), self.contract) is True
        assert (
            self.rule.normalize(_name("america/new_york"), self.contract)
            == "America/New_York"
        )

    def test_upper_folded_mention_restores_canonical_case(self) -> None:
        assert self.rule.matches(_name("AMERICA/NEW_YORK"), self.contract) is True
        assert (
            self.rule.normalize(_name("AMERICA/NEW_YORK"), self.contract)
            == "America/New_York"
        )

    def test_unknown_key_rejected(self) -> None:
        assert self.rule.matches(_name("America/Narnia"), self.contract) is False

    def test_link_source_owned_by_link_rule(self) -> None:
        assert self.rule.matches(_name("US/Eastern"), self.contract) is False

    def test_abbreviation_family_rejected(self) -> None:
        assert self.rule.matches(_abbreviation("EST"), self.contract) is False

    def test_systemv_key_excluded(self) -> None:
        assert self.rule.matches(_name("EST5EDT"), self.contract) is False

    def test_matches_never_raises(self) -> None:
        assert self.rule.matches(_name(""), self.contract) is False
        assert isinstance(
            self.rule.normalize(_name("America/Narnia"), self.contract), str
        )


@pytest.mark.capability
class TestLinkResolution:
    """Section link-resolution — backward Links resolve to canonical keys."""

    def setup_method(self) -> None:
        self.rule = SectionLinkResolution()
        self.contract = TimezoneContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section link-resolution"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"timezone_name"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.citation != ""

    def test_provenance(self) -> None:
        provenance = self.rule.provenance
        assert provenance.authority == "IANA"
        assert provenance.publication_year == 2026
        assert provenance.version == "2026d"

    def test_us_eastern_resolves_to_new_york(self) -> None:
        assert self.rule.matches(_name("US/Eastern"), self.contract) is True
        assert (
            self.rule.normalize(_name("US/Eastern"), self.contract)
            == "America/New_York"
        )

    def test_lowered_link_resolves(self) -> None:
        assert self.rule.matches(_name("us/eastern"), self.contract) is True
        assert (
            self.rule.normalize(_name("us/eastern"), self.contract)
            == "America/New_York"
        )

    def test_asia_calcutta_resolves_to_kolkata(self) -> None:
        assert self.rule.matches(_name("Asia/Calcutta"), self.contract) is True
        assert (
            self.rule.normalize(_name("Asia/Calcutta"), self.contract) == "Asia/Kolkata"
        )

    def test_canonical_key_owned_by_membership_rule(self) -> None:
        assert self.rule.matches(_name("America/New_York"), self.contract) is False

    def test_carved_short_caps_never_resolved(self) -> None:
        # Short-caps backward Links live in the abbreviation family.
        assert self.rule.matches(_name("EST"), self.contract) is False
        assert self.rule.matches(_name("CET"), self.contract) is False

    def test_unknown_key_rejected(self) -> None:
        assert self.rule.matches(_name("America/Narnia"), self.contract) is False

    def test_abbreviation_family_rejected(self) -> None:
        assert self.rule.matches(_abbreviation("EST"), self.contract) is False


@pytest.mark.capability
class TestSystemVZones:
    """Section systemv-zones — backward Zones, engine-gated on the flag."""

    def setup_method(self) -> None:
        self.rule = SectionSystemVZones()
        self.default_contract = TimezoneContract()
        self.systemv_contract = TimezoneContract(include_systemv=True)

    def test_metadata(self) -> None:
        assert self.rule.name == "Section systemv-zones"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"timezone_name"})
        assert self.rule.requires_features == frozenset({"include_systemv"})
        assert self.rule.citation != ""

    def test_provenance(self) -> None:
        assert self.rule.provenance.authority == "IANA"
        assert self.rule.provenance.publication_year == 2026

    @pytest.mark.parametrize("key", ["EST5EDT", "CST6CDT", "MST7MDT", "PST8PDT"])
    def test_systemv_keys_match(self, key: str) -> None:
        assert self.rule.matches(_name(key), self.systemv_contract) is True
        assert self.rule.normalize(_name(key), self.systemv_contract) == key

    def test_folded_systemv_key_restores_canonical_case(self) -> None:
        assert self.rule.matches(_name("est5edt"), self.systemv_contract) is True
        assert self.rule.normalize(_name("est5edt"), self.systemv_contract) == "EST5EDT"

    def test_matches_ignores_flag_directly(self) -> None:
        # Activation is engine-owned via requires_features; matches() itself
        # validates membership only (Country historical precedent).
        assert self.rule.matches(_name("EST5EDT"), self.default_contract) is True

    def test_engine_drops_rule_without_flag(self) -> None:
        from paxman.engine.orchestrator import _filter_rules

        assert _filter_rules([self.rule], self.default_contract) == []
        assert _filter_rules([self.rule], self.systemv_contract) == [self.rule]

    def test_non_systemv_key_rejected(self) -> None:
        assert self.rule.matches(_name("America/New_York"), self.systemv_contract) is (
            False
        )
        assert self.rule.matches(_name("US/Eastern"), self.systemv_contract) is False

    def test_contract_flag_defaults_off(self) -> None:
        assert TimezoneContract().include_systemv is False
        assert TimezoneContract(include_systemv=True).include_systemv is True


@pytest.mark.capability
class TestAbbreviationRefusal:
    """Section abbreviation-refusal — recognized abbreviations never resolve."""

    def setup_method(self) -> None:
        self.rule = SectionAbbreviationRefusal()
        self.contract = TimezoneContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section abbreviation-refusal"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"timezone_abbreviation"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.citation != ""

    def test_provenance(self) -> None:
        provenance = self.rule.provenance
        assert provenance.authority == "IANA"
        assert provenance.specification_name == "Time Zone Database"
        assert provenance.kind == "registry"
        assert (
            provenance.reference_url == "https://data.iana.org/time-zones/theory.html"
        )
        assert provenance.version == "2026d"
        assert provenance.lifecycle == "active"
        assert provenance.publication_year == 2026

    @pytest.mark.parametrize("token", sorted(CARVED_LINKS))
    def test_carved_links_refused(self, token: str) -> None:
        # Short-caps backward Links (est/cet/...) read as abbreviations.
        assert self.rule.matches(_abbreviation(token.upper()), self.contract) is False

    @pytest.mark.parametrize("token", sorted(REFUSAL_SET))
    def test_ambiguous_abbreviations_refused(self, token: str) -> None:
        # Ambiguous abbreviations (ist/cst/pst) — no silent pick, ever.
        assert self.rule.matches(_abbreviation(token.upper()), self.contract) is False

    def test_est_and_ist_refused(self) -> None:
        assert self.rule.matches(_abbreviation("EST"), self.contract) is False
        assert self.rule.matches(_abbreviation("IST"), self.contract) is False

    def test_normalize_never_resolves(self) -> None:
        # Best-effort echo: the rule owns no resolution target.
        assert self.rule.normalize(_abbreviation("EST"), self.contract) == "EST"
        assert self.rule.normalize(_abbreviation("IST"), self.contract) == "IST"

    def test_name_family_rejected(self) -> None:
        assert self.rule.matches(_name("America/New_York"), self.contract) is False

    def test_matches_never_raises(self) -> None:
        assert self.rule.matches(_abbreviation(""), self.contract) is False
