"""Tests for the ISIN capability wiring (ISO 6166:2021 + ANNA V25)."""

from __future__ import annotations

import inspect
from inspect import Parameter

import pytest

from paxman.api import canonicalize
from paxman.api.bootstrap import list_shipped_capabilities
from paxman.capabilities.ISIN.capability import ISINCapability
from paxman.capabilities.ISIN.contract import ISINContract
from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.mark.capability
class TestISINCapability:
    """Capability wiring — grammars, rules, factory, formats."""

    def setup_method(self) -> None:
        self.capability = ISINCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "isin"

    def test_wiring_counts(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["isin_recognition"]
        assert all(g.semantics == "isin_recognition" for g in grammars)
        assert [r.name for r in self.capability.get_rules()] == [
            "Section 4-isin-structure-check-digit",
            "Section 5-country-and-special-prefix",
        ]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, ISINContract)
        assert contract.capability_name == "isin"
        assert contract.output_format == "isin"
        assert contract.excluded_rules == ()
        assert contract.pinned_rules is None
        assert contract.year is None
        assert contract.extra_grammars == ()
        assert contract.suppress_common_words is False

    def test_create_contract_common_block(self) -> None:
        """The unanimous common block passes through in order with defaults."""
        parameters = list(
            inspect.signature(ISINCapability.create_contract).parameters.values()
        )
        assert [p.name for p in parameters[:6]] == [
            "excluded_rules",
            "pinned_rules",
            "year",
            "output_format",
            "extra_grammars",
            "suppress_common_words",
        ]
        assert all(p.kind == Parameter.KEYWORD_ONLY for p in parameters)
        contract = ISINCapability.create_contract(
            excluded_rules=["Section 4-isin-structure-check-digit"],
            pinned_rules=["Section 5-country-and-special-prefix"],
            year=2021,
            output_format="grouped",
            extra_grammars=["first", "second"],
            suppress_common_words=True,
        )
        assert contract.excluded_rules == ("Section 4-isin-structure-check-digit",)
        assert contract.pinned_rules == ("Section 5-country-and-special-prefix",)
        assert contract.year == 2021
        assert contract.output_format == "grouped"
        assert contract.extra_grammars == ("first", "second")
        assert contract.suppress_common_words is True

    def test_format_value_grouped(self) -> None:
        notation = ISINNotation(
            country_code="US",
            nsin="037833100",
            check_digit="5",
            compact="US0378331005",
        )
        assert (
            self.capability.format_value("US0378331005", "grouped", notation)
            == "US 037833 100 5"
        )
        # default identity paths remain unchanged
        assert self.capability.format_value("US0378331005", None, notation) == (
            "US0378331005"
        )
        assert self.capability.format_value("US0378331005", "isin", notation) == (
            "US0378331005"
        )
        assert self.capability.format_value("US0378331005", "default", notation) == (
            "US0378331005"
        )

    def test_cli_isin_branch(self) -> None:
        from paxman.cli import _create_contract

        contract = _create_contract("isin")
        assert isinstance(contract, ISINContract)
        assert contract.capability_name == "isin"
        assert contract.output_format == "isin"

    def test_shipped_contains_isin(self) -> None:
        assert "isin" in list_shipped_capabilities()


@pytest.mark.capability
class TestISINCapabilityPipeline:
    """End-to-end: scaffold probe resolves to MISSING."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_scaffold_probe_missing(self) -> None:
        register_capability(ISINCapability())
        contract = ISINCapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
