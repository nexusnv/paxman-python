"""Tests for Date validation rules."""

from __future__ import annotations

import pytest

from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Date.rules.en_50160_ed2010 import Section4DateFormat
from paxman.capabilities.Date.rules.iso_8601_ed2019 import Section431CalendarDate
from paxman.capabilities.Date.rules.us_federal_rules_ed2023 import (
    Section1DateFormat,
)
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestSection431CalendarDate:
    """ISO 8601 Section 5.2.1.1 — calendar date rule tests."""

    def test_matches_valid_input(self) -> None:
        rule = Section431CalendarDate()
        notation = DateNotation(N1="2026", N2="07", N3="26")
        contract = DateContract()
        assert rule.matches(notation, contract) is True

    def test_rejects_invalid_input(self) -> None:
        rule = Section431CalendarDate()
        notation = DateNotation(N1="2026", N2="13", N3="32")
        contract = DateContract()
        assert rule.matches(notation, contract) is False

    def test_normalize_produces_canonical(self) -> None:
        rule = Section431CalendarDate()
        notation = DateNotation(N1="2026", N2="07", N3="26")
        contract = DateContract()
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_provenance_attributes(self) -> None:
        rule = Section431CalendarDate()
        assert rule.provenance.authority == "ISO"
        assert rule.provenance.specification_name == "ISO 8601"
        assert rule.provenance.publication_year == 2019
        assert rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        rule = Section431CalendarDate()
        assert rule.name == "Section 5.2.1.1-calendar-date"

    def test_strategy_is_parser(self) -> None:
        rule = Section431CalendarDate()
        assert rule.strategy == RuleStrategy.PARSER


@pytest.mark.capability
class TestSection1DateFormat:
    """Derived convention — US locale date format rule tests."""

    def test_matches_valid_input(self) -> None:
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="2026")
        contract = DateContract()
        assert rule.matches(notation, contract) is True

    def test_two_digit_year_with_base_year(self) -> None:
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="26")
        contract = DateContract(two_digit_base_year=2000)
        assert rule.matches(notation, contract) is True
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_two_digit_year_default_base(self) -> None:
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="26")
        contract = DateContract()
        assert rule.matches(notation, contract) is True
        # Default base year is 2000, so 26 -> 2026
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_two_digit_year_explicit_zero_base_year(self) -> None:
        """An explicit zero base year is honored, not collapsed to 2000."""
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="26")
        contract = DateContract(two_digit_base_year=0)
        assert rule.matches(notation, contract) is True
        # Base year 0 is a configured value: 26 -> 0026, not 2026.
        assert rule.normalize(notation, contract) == "0026-07-26"

    def test_two_digit_year_defensive_with_non_date_contract(self) -> None:
        """Two-digit years default to base 2000 even without a DateContract."""
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="26")
        assert rule.matches(notation, PhoneContract()) is True
        assert rule.normalize(notation, PhoneContract()) == "2026-07-26"

    def test_output_format_iso(self) -> None:
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="2026")
        contract = DateContract(output_format="ISO")
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_output_format_us_still_returns_iso(self) -> None:
        """Rules emit the default ISO canonical form even when US is requested."""
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="2026")
        contract = DateContract(output_format="US")
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_output_format_default_is_iso(self) -> None:
        rule = Section1DateFormat()
        notation = DateNotation(N1="07", N2="26", N3="2026")
        contract = DateContract()
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_provenance_attributes(self) -> None:
        rule = Section1DateFormat()
        assert rule.provenance.authority == "Derived convention"
        assert rule.provenance.specification_name == "US locale — MM/DD/YYYY"
        assert rule.provenance.publication_year == 2025
        assert rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        rule = Section1DateFormat()
        assert rule.name == "Derived-US-date-format"

    def test_strategy_is_parser(self) -> None:
        rule = Section1DateFormat()
        assert rule.strategy == RuleStrategy.PARSER


@pytest.mark.capability
class TestEN50160Section4DateFormat:
    """Derived convention — European locale date format rule tests."""

    def test_valid_european_date(self) -> None:
        """Valid European date is accepted."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="26", N2="07", N3="2026")
        contract = DateContract()
        assert rule.matches(notation, contract) is True

    def test_normalize_to_iso(self) -> None:
        """European date is normalized to ISO format by default."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="26", N2="07", N3="2026")
        contract = DateContract(output_format="ISO")
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_output_format_us_still_returns_iso(self) -> None:
        """Rules emit the default ISO canonical form even when US is requested."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="26", N2="07", N3="2026")
        contract = DateContract(output_format="US")
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_invalid_date(self) -> None:
        """Invalid European date is rejected."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="31", N2="02", N3="2026")
        contract = DateContract()
        assert rule.matches(notation, contract) is False

    def test_two_digit_year(self) -> None:
        """Two-digit year uses contract base year."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="26", N2="07", N3="26")
        contract = DateContract(two_digit_base_year=2000)
        assert rule.matches(notation, contract) is True
        assert rule.normalize(notation, contract) == "2026-07-26"

    def test_two_digit_year_explicit_zero_base_year(self) -> None:
        """An explicit zero base year is honored, not collapsed to 2000."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="26", N2="07", N3="26")
        contract = DateContract(two_digit_base_year=0)
        assert rule.matches(notation, contract) is True
        # Base year 0 is a configured value: 26 -> 0026, not 2026.
        assert rule.normalize(notation, contract) == "0026-07-26"

    def test_two_digit_year_defensive_with_non_date_contract(self) -> None:
        """Two-digit years default to base 2000 even without a DateContract."""
        rule = Section4DateFormat()
        notation = DateNotation(N1="26", N2="07", N3="26")
        assert rule.matches(notation, PhoneContract()) is True
        assert rule.normalize(notation, PhoneContract()) == "2026-07-26"

    def test_provenance_attributes(self) -> None:
        """Provenance is correctly set."""
        rule = Section4DateFormat()
        assert rule.provenance.authority == "Derived convention"
        assert rule.provenance.specification_name == "European locale — DD/MM/YYYY"
        assert rule.provenance.publication_year == 2025
        assert rule.provenance.lifecycle == "active"

    def test_rule_name(self) -> None:
        """Rule name is correct."""
        rule = Section4DateFormat()
        assert rule.name == "Derived-European-date-format"

    def test_strategy_is_parser(self) -> None:
        """Strategy is PARSER."""
        rule = Section4DateFormat()
        assert rule.strategy == RuleStrategy.PARSER
