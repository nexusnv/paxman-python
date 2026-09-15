"""Integration tests for the Timezone capability through the full pipeline.

Research acceptance corpus: ``docs/development/research/2026-09-14-timezone-
canonicalization.md`` §8 edge table (timezone rows) + §9 resolution-state
map + post-review semantic matrix. Every vector below was executed against
the pipeline (``register_all_shipped`` + ``canonicalize``); statuses are
observed, not assumed. One deliberate divergence from the research table
is pinned with rationale:

- unknown key (``America/Narnia``): the research §8 row 12 assumes a
  shape-claiming grammar (INVALID), but the shipped design is a lexicon
  over the curated subset — unlisted keys are unclaimable and therefore
  MISSING ("Unlisted keys are MISSING at the grammar, never INVALID",
  ``iana_zone_identifiers.py`` header; ``test_data_consistency.py``).
  An INVALID outcome would need a shape-claiming matcher (out of scope).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities.Timezone.capability import TimezoneCapability
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError, MultipleMentionsError

_MEMBERSHIP_RULE = "Section zone-key-membership"
_LINK_RULE = "Section link-resolution"
_SYSTEMV_RULE = "Section systemv-zones"


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestTimezonePipelineSuccess:
    """§8 rows 1-2, 5 + §9 valid key/link/case-variant rows (§12 vectors)."""

    @pytest.mark.integration
    @pytest.mark.parametrize(
        ("text", "expected_value", "expected_rule", "expected_span"),
        [
            ("America/New_York", "America/New_York", _MEMBERSHIP_RULE, (0, 16)),
            ("america/new_york", "America/New_York", _MEMBERSHIP_RULE, (0, 16)),
            ("AMERICA/NEW_YORK", "America/New_York", _MEMBERSHIP_RULE, (0, 16)),
            ("US/Eastern", "America/New_York", _LINK_RULE, (0, 10)),
            ("Canada/Eastern", "America/Toronto", _LINK_RULE, (0, 14)),
            ("US/PACIFIC", "America/Los_Angeles", _LINK_RULE, (0, 10)),
            ("Etc/GMT-8", "Etc/GMT-8", _MEMBERSHIP_RULE, (0, 9)),
            ("us/eastern", "America/New_York", _LINK_RULE, (0, 10)),
            ("Asia/Calcutta", "Asia/Kolkata", _LINK_RULE, (0, 13)),
            ("Australia/ACT", "Australia/Sydney", _LINK_RULE, (0, 13)),
            ("Etc/GMT+5", "Etc/GMT+5", _MEMBERSHIP_RULE, (0, 9)),
            ("Etc/UTC", "Etc/UTC", _MEMBERSHIP_RULE, (0, 7)),
            ("Etc/GMT", "Etc/GMT", _MEMBERSHIP_RULE, (0, 7)),
            ("UTC", "UTC", _MEMBERSHIP_RULE, (0, 3)),
            ("GMT", "GMT", _MEMBERSHIP_RULE, (0, 3)),
            ("gmt", "GMT", _MEMBERSHIP_RULE, (0, 3)),
        ],
    )
    def test_success_rows(
        self,
        text: str,
        expected_value: str,
        expected_rule: str,
        expected_span: tuple[int, int],
    ) -> None:
        """Canonical keys, folds, links, and fixed zones canonicalize."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected_value
        assert result.span == expected_span
        assert len(result.candidates) >= 1
        assert {c.value for c in result.candidates} == {expected_value}
        for candidate in result.candidates:
            assert candidate.validation_rule == expected_rule
            assert candidate.provenance[0].authority == "IANA"

    @pytest.mark.integration
    def test_embedded_link_span(self) -> None:
        """§8 row 14: the link span excludes surrounding prose."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("visit US/Eastern tomorrow", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "America/New_York"
        assert result.span == (6, 16)

    @pytest.mark.integration
    def test_trailing_annotation_span_covers_key_only(self) -> None:
        """§2.2 row 13: the parenthetical abbreviation is not fused."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("America/New_York (EDT)", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "America/New_York"
        assert result.span == (0, 16)

    @pytest.mark.integration
    def test_padded_input_trimmed(self) -> None:
        """§2.2 row 12: surrounding whitespace is trimmed (A0 exemption)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("  America/New_York  ", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "America/New_York"
        assert result.span == (2, 18)


class TestTimezonePipelineSystemV:
    """§8 rows 3-4 + §9 gated-off row + semantic matrix SystemV row."""

    @pytest.mark.integration
    def test_systemv_gated_off_invalid(self) -> None:
        """EST5EDT is claimed (shape) but rule-gated: INVALID by default."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("EST5EDT", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_systemv_gated_on_success(self) -> None:
        """EST5EDT + flag → SUCCESS EST5EDT (fixed-rule zone, valid key)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract(include_systemv=True)
        result = paxman.canonicalize("EST5EDT", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "EST5EDT"
        assert result.span == (0, 7)
        assert {c.value for c in result.candidates} == {"EST5EDT"}
        assert {c.validation_rule for c in result.candidates} == {_SYSTEMV_RULE}


class TestTimezonePipelineRefusal:
    """§8 rows 9-10, 14 + §9 short-caps/ambiguous rows + matrix row."""

    @pytest.mark.integration
    @pytest.mark.parametrize("token", ["EST", "MST", "HST", "CET"])
    def test_carved_abbreviations_invalid(self, token: str) -> None:
        """Carved short-caps Links read as abbreviations: never resolved."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize(token, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize("token", ["IST", "CST", "PST"])
    def test_ambiguous_abbreviations_invalid(self, token: str) -> None:
        """Ambiguous abbreviations are recognized but refused, never picked."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize(token, contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_embedded_abbreviation_invalid(self) -> None:
        """§8 row 14: bare CET in prose is refused everywhere."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("arrive CET tomorrow", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.integration
    def test_quoted_abbreviation_invalid(self) -> None:
        """§2.2 row 15: quotes do not rescue a refused abbreviation."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize('"CET"', contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.integration
    def test_refused_pair_stays_invalid(self) -> None:
        """§2.4: EST then CET is INVALID+INVALID — refused mentions do not
        compete, so no MultipleMentionsError."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("EST then CET", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None


class TestTimezonePipelineMissing:
    """§8 rows 11, 13, 16, 18 + §9 no-shape row + matrix Windows row."""

    @pytest.mark.integration
    @pytest.mark.parametrize("text", ["XYZ", "JST", "hello world"])
    def test_unlisted_abbreviations_and_prose_missing(self, text: str) -> None:
        """Unlisted abbreviations claim nothing (MISSING, never INVALID);
        JST is out of the v1 curated subset by design."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_unknown_key_missing(self) -> None:
        """§8 row 12 executed: America/Narnia is unclaimable under the
        lexicon-over-subset design, hence MISSING (see module docstring)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("America/Narnia", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_windows_name_missing(self) -> None:
        """§8 row 13: Windows names are deferred entirely (no v1 grammar)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("Eastern Standard Time", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_zulu_word_missing(self) -> None:
        """§8 row 18: Zulu is not a tzdb key (verified raises upstream)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("Zulu", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "text", ["XUS/Eastern", "US/EasternX", "/usr/share/zoneinfo/America/New_York"]
    )
    def test_glued_runs_and_paths_missing(self, text: str) -> None:
        """§8 row 16: the slash-aware boundary forbids mid-path extraction;
        zoneinfo paths must be split first by the caller."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_offset_continuation_no_prefix_fallback_missing(self) -> None:
        """Etc/GMT+5X must not fall back to the Etc/GMT prefix (#162 family)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        result = paxman.canonicalize("Etc/GMT+5X", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()


class TestTimezonePipelineContract:
    """§9 year/output_format rows + ambiguity + determinism."""

    @pytest.mark.integration
    def test_two_distinct_zones_raise(self) -> None:
        """§8 row 15: two distinct zones fail fast (single_value=True)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("US/Eastern then America/Chicago", contract)

    @pytest.mark.integration
    def test_year_filter_invalid(self) -> None:
        """§9: year=2020 drops the tzdb-2026 rules (MacAddress precedent)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract(year=2020)
        result = paxman.canonicalize("America/New_York", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None

    @pytest.mark.integration
    @pytest.mark.parametrize("output_format", ["abbreviation", "link"])
    def test_unoffered_format_contract_error(self, output_format: str) -> None:
        """§9: abbreviation/link outputs are never offered (ADR-0011) —
        the contract constructor raises ContractError."""
        paxman.register_all_shipped()
        with pytest.raises(ContractError):
            TimezoneCapability.create_contract(output_format=output_format)

    @pytest.mark.integration
    def test_determinism_spot_check(self) -> None:
        """Same input + contract + snapshot → same output (no clock)."""
        paxman.register_all_shipped()
        contract = TimezoneCapability.create_contract()
        first = paxman.canonicalize("US/Eastern", contract)
        second = paxman.canonicalize("US/Eastern", contract)

        assert first.status == Resolution.SUCCESS
        assert (second.status, second.canonicalized_value, second.span) == (
            first.status,
            first.canonicalized_value,
            first.span,
        )
