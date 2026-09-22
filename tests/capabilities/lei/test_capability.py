"""Tests for the LEI capability wiring (ISO 17442-1:2020 + GLEIF prefix list)."""

from __future__ import annotations

import inspect
from inspect import Parameter

import pytest

from paxman.api import canonicalize
from paxman.api.bootstrap import list_shipped_capabilities
from paxman.capabilities.LEI.capability import LEICapability
from paxman.capabilities.LEI.contract import LEIContract
from paxman.capabilities.LEI.grammar.lei_recognition import LEIRecognitionGrammar
from paxman.capabilities.LEI.notation import LEINotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

VALID = "5493000IBP32UQZ0KL24"


def _notation(compact: str = VALID) -> LEINotation:
    return LEINotation(
        lou_prefix=compact[0:4],
        entity_block=compact[4:18],
        check_digits=compact[18:20],
        compact=compact,
    )


@pytest.mark.capability
class TestLEICapability:
    """Capability wiring — grammars, rules, factory, formats."""

    def setup_method(self) -> None:
        self.capability = LEICapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "lei"

    def test_wiring_counts(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["lei_recognition"]
        assert all(g.semantics == "lei_recognition" for g in grammars)
        assert [r.name for r in self.capability.get_rules()] == [
            "Section 4-lei-structure-mod97-10",
            "Section 1-lou-prefix-membership",
        ]

    def test_get_rules(self) -> None:
        names = {r.name for r in self.capability.get_rules()}
        assert names == {
            "Section 4-lei-structure-mod97-10",
            "Section 1-lou-prefix-membership",
        }

    def test_get_grammars(self) -> None:
        names = {g.name for g in self.capability.get_grammars()}
        assert names == {"lei_recognition"}

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, LEIContract)
        assert contract.capability_name == "lei"
        assert contract.output_format == "lei"
        assert contract.excluded_rules == ()
        assert contract.pinned_rules is None
        assert contract.year is None
        assert contract.extra_grammars == ()
        assert contract.suppress_common_words is False

    def test_create_contract_common_block(self) -> None:
        """The unanimous common block passes through in order with defaults."""
        parameters = list(
            inspect.signature(LEICapability.create_contract).parameters.values()
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
        contract = LEICapability.create_contract(
            excluded_rules=["Section 4-lei-structure-mod97-10"],
            pinned_rules=["Section 1-lou-prefix-membership"],
            year=2020,
            output_format="urn",
            extra_grammars=["first", "second"],
            suppress_common_words=True,
        )
        assert contract.excluded_rules == ("Section 4-lei-structure-mod97-10",)
        assert contract.pinned_rules == ("Section 1-lou-prefix-membership",)
        assert contract.year == 2020
        assert contract.output_format == "urn"
        assert contract.extra_grammars == ("first", "second")
        assert contract.suppress_common_words is True

    def test_format_value_urn(self) -> None:
        notation = _notation()
        assert (
            self.capability.format_value(VALID, "urn", notation) == f"urn:lei:{VALID}"
        )
        # default identity paths remain unchanged
        assert self.capability.format_value(VALID, None, notation) == VALID
        assert self.capability.format_value(VALID, "lei", notation) == VALID
        assert self.capability.format_value(VALID, "default", notation) == VALID

    def test_urn_reentry_via_carrier(self) -> None:
        rendered = self.capability.format_value(VALID, "urn", _notation())
        assert rendered == f"urn:lei:{VALID}"
        grammar = LEIRecognitionGrammar()
        matches = grammar.recognize(rendered)
        assert len(matches) == 1
        assert matches[0].notation.compact == VALID

    def test_cli_lei_branch(self) -> None:
        from paxman.cli import _create_contract

        contract = _create_contract("lei")
        assert isinstance(contract, LEIContract)
        assert contract.capability_name == "lei"
        assert contract.output_format == "lei"

    def test_shipped_contains_lei(self) -> None:
        assert "lei" in list_shipped_capabilities()


@pytest.mark.capability
class TestLEICapabilityPipeline:
    """End-to-end: scaffold probe resolves to MISSING."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_scaffold_probe_missing(self) -> None:
        register_capability(LEICapability())
        contract = LEICapability.create_contract()
        result = canonicalize("scaffold probe", contract)
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
