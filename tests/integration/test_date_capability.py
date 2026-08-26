"""Integration tests for Date capability."""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities import Date
from paxman.capabilities.Date.capability import DateCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset and register Date capability before each test."""
    reset_registry()
    register_capability(DateCapability())
    yield
    reset_registry()


@pytest.mark.integration
class TestDateCapabilityIntegration:
    """Integration tests for Date capability pipeline."""

    def test_iso8601_date_recognized_and_canonicalized(self) -> None:
        """ISO 8601 date is recognized and canonicalized to ISO format."""
        contract = Date.create_contract()
        result = paxman.canonicalize("2026-07-26", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-07-26"

    def test_us_date_with_output_format_iso(self) -> None:
        """US date with output_format=ISO is canonicalized to ISO format."""
        contract = Date.create_contract(output_format="ISO")
        result = paxman.canonicalize("07/26/2026", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-07-26"

    def test_us_date_with_output_format_us(self) -> None:
        """US date with output_format=US is canonicalized to US format."""
        contract = Date.create_contract(output_format="US")
        result = paxman.canonicalize("07/26/2026", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "07/26/2026"

    def test_european_date_with_output_format_iso(self) -> None:
        """European date with output_format=ISO is canonicalized to ISO format."""
        contract = Date.create_contract(output_format="ISO")
        result = paxman.canonicalize("26/07/2026", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-07-26"

    def test_two_digit_year_with_base_year(self) -> None:
        """Two-digit year with base_year is interpreted correctly."""
        contract = Date.create_contract(two_digit_base_year=2000)
        result = paxman.canonicalize("07/26/26", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-07-26"

    def test_two_digit_year_without_base_year(self) -> None:
        """Two-digit year without base_year uses default (2000)."""
        contract = Date.create_contract()
        result = paxman.canonicalize("07/26/26", contract)
        assert result.status == Resolution.SUCCESS
        # Default base year is 2000, so 26 -> 2026
        assert result.canonicalized_value == "2026-07-26"

    def test_date_in_text_recognized(self) -> None:
        """Date embedded in text is recognized."""
        contract = Date.create_contract()
        result = paxman.canonicalize("Meeting on 2026-07-26", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-07-26"

    def test_multiple_dates_ambiguous(self) -> None:
        """Two dates in one input fail fast (single-value invariant).

        Two dates are un-segmented multi-entity input, so the engine raises
        MultipleMentionsError instead of returning AMBIGUOUS.
        """
        contract = Date.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("2026-07-26 and 2025-12-31", contract)

    def test_no_date_missing(self) -> None:
        """No date in text produces MISSING status."""
        contract = Date.create_contract()
        result = paxman.canonicalize("No dates here", contract)
        assert result.status == Resolution.MISSING

    def test_invalid_date_invalid(self) -> None:
        """Invalid date (e.g., February 30) produces INVALID status."""
        contract = Date.create_contract()
        result = paxman.canonicalize("2026-02-30", contract)
        assert result.status == Resolution.INVALID

    def test_us_vs_european_date_ambiguity(self) -> None:
        """Input '07/02/2026' is ambiguous between US (July 2) and European (Feb 7)."""
        contract = Date.create_contract()
        result = paxman.canonicalize("07/02/2026", contract)
        assert result.status == Resolution.AMBIGUOUS
        values = {c.value for c in result.candidates}
        assert "2026-07-02" in values  # US interpretation
        assert "2026-02-07" in values  # European interpretation

    def test_pinned_iso_rule_with_us_output_format(self) -> None:
        """A pinned ISO rule with output_format=US renders MM/DD/YYYY.

        The ISO rule emits its default canonical ISO value; the capability
        formatter then renders it in the requested US format.
        """
        contract = Date.create_contract(
            pinned_rules=["Section 5.2.1.1-calendar-date"], output_format="US"
        )
        result = paxman.canonicalize("2026-01-15", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "01/15/2026"
        assert result.candidates[0].value == "01/15/2026"

    def test_slash_iso_date_resolves(self) -> None:
        """YYYY/MM/DD input resolves via the slash-ISO grammar.

        Before this grammar shipped, "2024/01/01" was not recognized by any
        Date grammar (US/European require a leading month/day, ISO requires
        dashes) and resolved MISSING; the slash-ISO grammar makes it SUCCESS.
        """
        contract = Date.create_contract()
        result = paxman.canonicalize("2024/01/01", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2024-01-01"
        assert result.candidates[0].recognition_rule == "slash_iso_recognition"

    def test_slash_iso_single_digit_components(self) -> None:
        """Single-digit month/day are zero-padded in the canonical value."""
        contract = Date.create_contract()
        result = paxman.canonicalize("2024/1/5", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2024-01-05"

    def test_slash_iso_invalid_month_invalid(self) -> None:
        """A slash-ISO shape with an impossible month is INVALID, not resolved."""
        contract = Date.create_contract()
        result = paxman.canonicalize("2024/13/01", contract)
        assert result.status == Resolution.INVALID

    def test_slash_iso_does_not_disturb_us_ambiguity(self) -> None:
        """US/European slash formats still resolve exactly as before."""
        contract = Date.create_contract()
        result = paxman.canonicalize("07/26/2026", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "2026-07-26"

    def test_year_2024_includes_both_regional_rules(self) -> None:
        """Year filter 2024 keeps both US and European rules active."""
        contract = Date.create_contract(year=2024)
        r_us = paxman.canonicalize("07/26/2024", contract)
        r_eu = paxman.canonicalize("26/07/2024", contract)
        assert r_us.status == Resolution.SUCCESS
        assert r_eu.status == Resolution.SUCCESS
        assert r_us.canonicalized_value == "2024-07-26"
        assert r_eu.canonicalized_value == "2024-07-26"
        # Both regional rules have publication_year <= 2024 (US 2023 and European 2010)
        # so both should be active (regression for 2025→2023 year restore).
        # 07/26/2024 is unambiguous (EU month 26 invalid) but proves US rule active;
        # 26/07/2024 proves EU rule active; together they prove both survive
        # year=2024 filtering.
        assert r_us.candidates[0].provenance[0].publication_year <= 2024
        assert r_eu.candidates[0].provenance[0].publication_year <= 2024
