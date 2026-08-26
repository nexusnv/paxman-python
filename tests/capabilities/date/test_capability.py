"""Tests for DateNotation and DateCapability."""

from __future__ import annotations

import pytest

from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.capability import Capability
from paxman.core.errors import ContractError

# --- DateNotation tests ---


@pytest.mark.capability
class TestDateNotation:
    """Tests for DateNotation."""

    def test_creates_with_fields(self) -> None:
        notation = DateNotation(N1="2026", N2="07", N3="26")
        assert notation.N1 == "2026"
        assert notation.N2 == "07"
        assert notation.N3 == "26"

    def test_is_frozen(self) -> None:
        notation = DateNotation(N1="2026", N2="07", N3="26")
        with pytest.raises(AttributeError):
            notation.N1 = "2025"  # type: ignore[misc]

    def test_equality(self) -> None:
        n1 = DateNotation(N1="2026", N2="07", N3="26")
        n2 = DateNotation(N1="2026", N2="07", N3="26")
        assert n1 == n2

    def test_hashable(self) -> None:
        notation = DateNotation(N1="2026", N2="07", N3="26")
        assert hash(notation) is not None


# --- DateCapability tests ---


@pytest.mark.capability
class TestDateCapability:
    """Tests for DateCapability."""

    def test_is_capability_subclass(self) -> None:
        cap = DateCapability()
        assert isinstance(cap, Capability)

    def test_name(self) -> None:
        cap = DateCapability()
        assert cap.name == "date"

    def test_get_grammars_returns_all(self) -> None:
        cap = DateCapability()
        assert len(cap.get_grammars()) == 4

    def test_get_grammars_includes_slash_iso(self) -> None:
        """The slash-ISO grammar is wired into the capability."""
        cap = DateCapability()
        names = {g.name for g in cap.get_grammars()}
        assert "slash_iso_recognition" in names

    def test_get_rules_returns_all(self) -> None:
        cap = DateCapability()
        assert len(cap.get_rules()) == 3


@pytest.mark.capability
class TestDateCapabilityFormatValue:
    """Tests for DateCapability.format_value()."""

    NOTATION = DateNotation(N1="2026", N2="07", N3="26")

    def test_iso_format_is_identity(self) -> None:
        """The default ISO path returns the canonical value unchanged."""
        cap = DateCapability()
        assert cap.format_value("2026-07-26", "ISO", self.NOTATION) == "2026-07-26"

    def test_default_format_is_identity(self) -> None:
        """An unset output format returns the canonical value unchanged."""
        cap = DateCapability()
        assert cap.format_value("2026-07-26", None, self.NOTATION) == "2026-07-26"

    def test_us_format_converts_iso_canonical(self) -> None:
        """US rendering converts a validated YYYY-MM-DD value to MM/DD/YYYY."""
        cap = DateCapability()
        assert cap.format_value("2026-07-26", "US", self.NOTATION) == "07/26/2026"

    def test_us_format_converts_other_dates(self) -> None:
        """US rendering handles dates outside the notation sample."""
        cap = DateCapability()
        notation = DateNotation(N1="1999", N2="12", N3="31")
        assert cap.format_value("1999-12-31", "US", notation) == "12/31/1999"

    def test_us_format_preserves_four_digit_early_year(self) -> None:
        """US rendering keeps zero-padding for years before 1000."""
        cap = DateCapability()
        notation = DateNotation(N1="0001", N2="01", N3="01")
        assert cap.format_value("0001-01-01", "US", notation) == "01/01/0001"

    def test_us_format_rejects_arbitrary_strings(self) -> None:
        """US rendering must not accept arbitrary strings as valid dates."""
        cap = DateCapability()
        with pytest.raises(ValueError):
            cap.format_value("not-a-date", "US", self.NOTATION)

    def test_us_format_rejects_non_fixed_width_values(self) -> None:
        """US rendering rejects values that are not fixed-shape YYYY-MM-DD."""
        cap = DateCapability()
        with pytest.raises(ValueError):
            cap.format_value("2026-1-5", "US", self.NOTATION)


# --- DateContract tests ---


@pytest.mark.capability
class TestDateContract:
    """Tests for DateContract."""

    def test_defaults(self) -> None:
        contract = DateContract()
        assert contract.capability_name == "date"
        assert contract.pinned_rules is None
        assert contract.output_format == "ISO"
        assert contract.two_digit_base_year is None

    def test_with_parameters(self) -> None:
        contract = DateContract(output_format="ISO", two_digit_base_year=2000)
        assert contract.output_format == "ISO"
        assert contract.two_digit_base_year == 2000

    def test_empty_pinned_rules_are_preserved(self) -> None:
        contract = DateContract(pinned_rules=())
        assert contract.pinned_rules == ()

    def test_output_format_default_resolves_to_iso(self) -> None:
        """'default' reverts to the default ISO rendering."""
        contract = DateContract(output_format="default")
        assert contract.output_format == "ISO"

    @pytest.mark.parametrize("fmt", ["none", "", "e164", "alpha2"])
    def test_invalid_output_format_raises_contract_error(self, fmt: str) -> None:
        """Unoffered output_format values raise ContractError."""
        with pytest.raises(ContractError):
            DateContract(output_format=fmt)


@pytest.mark.capability
class TestDateContractLegacyAndYear:
    """Regression for legacy rule-name aliases and year filtering."""

    def test_legacy_section_1_resolves_to_canonical(self) -> None:
        c = DateContract(pinned_rules=("Section 1-date-format",))
        assert c.pinned_rules == ("Derived-US-date-format",)

    def test_legacy_section_4_resolves_to_canonical(self) -> None:
        c = DateContract(pinned_rules=("Section 4-date-format",))
        assert c.pinned_rules == ("Derived-European-date-format",)

    def test_legacy_section_431_resolves_to_canonical(self) -> None:
        c = DateContract(pinned_rules=("Section 4.3.1-calendar-date",))
        assert c.pinned_rules == ("Section 5.2.1.1-calendar-date",)

    def test_legacy_excluded_resolves(self) -> None:
        c = DateContract(excluded_rules=("Section 1-date-format",))
        assert c.excluded_rules == ("Derived-US-date-format",)

    def test_canonical_names_unchanged(self) -> None:
        c = DateContract(pinned_rules=("Derived-US-date-format",))
        assert c.pinned_rules == ("Derived-US-date-format",)

    def test_year_2024_includes_both_regional_rules(self) -> None:
        import paxman
        from paxman.core.discovery import register_capability, reset_registry

        reset_registry()
        register_capability(DateCapability())
        try:
            contract = DateContract(year=2024)
            r_us = paxman.canonicalize("07/26/2024", contract)
            r_eu = paxman.canonicalize("26/07/2024", contract)
            assert r_us.candidates and r_eu.candidates
            # Both regional rules have publication_year <=2024 (2023 and 2010)
            # so both should be active; US input is ambiguous (2 values)
            # but must not be MISSING/INVALID due to year filtering.
            assert r_us.candidates[0].provenance[0].publication_year <= 2024
        finally:
            reset_registry()
