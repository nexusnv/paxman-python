"""Tests for the CreditCard capability wiring (grammar/rule counts, seams)."""

import inspect
from inspect import Parameter

import pytest

from paxman.api.bootstrap import list_shipped_capabilities
from paxman.capabilities.CreditCard.capability import CreditCardCapability
from paxman.capabilities.CreditCard.contract import CreditCardContract
from paxman.capabilities.CreditCard.grammar.pan_recognition import (
    PANRecognitionGrammar,
)
from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.capabilities.CreditCard.rules.brand_prefix_ed2026 import (
    Section1BrandPrefixMembership,
)
from paxman.capabilities.CreditCard.rules.iso_7812_1_ed2017 import (
    Section5PANStructureLuhn,
)

pytestmark = [pytest.mark.capability]


@pytest.fixture
def capability() -> CreditCardCapability:
    return CreditCardCapability()


def test_wiring_counts_two_rules(capability: CreditCardCapability) -> None:
    # 1 grammar + 2 rules (revises Task 5: ISO PARSER + gated brand LOOKUP).
    assert len(capability.get_grammars()) == 1
    assert isinstance(capability.get_grammars()[0], PANRecognitionGrammar)
    assert len(capability.get_rules()) == 2
    assert isinstance(capability.get_rules()[0], Section5PANStructureLuhn)
    assert isinstance(capability.get_rules()[1], Section1BrandPrefixMembership)
    assert capability.name == "credit_card"


def test_create_contract_forwards_brand_flag() -> None:
    contract = CreditCardCapability.create_contract(include_brand_validation=True)
    assert contract.include_brand_validation is True
    assert CreditCardCapability.create_contract().include_brand_validation is False


def test_create_contract_common_block() -> None:
    parameters = list(
        inspect.signature(CreditCardCapability.create_contract).parameters.values()
    )
    assert [p.name for p in parameters] == [
        "excluded_rules",
        "pinned_rules",
        "year",
        "output_format",
        "extra_grammars",
        "suppress_common_words",
        "include_brand_validation",
    ]
    assert all(p.kind == Parameter.KEYWORD_ONLY for p in parameters)
    contract = CreditCardCapability.create_contract()
    assert isinstance(contract, CreditCardContract)
    assert contract.output_format == "pan"
    assert contract.suppress_common_words is False
    assert contract.include_brand_validation is False


def test_format_value_pan_identity(capability: CreditCardCapability) -> None:
    notation = PANNotation(digits="4111111111111111", compact="4111111111111111")
    assert (
        capability.format_value("4111111111111111", "pan", notation)
        == "4111111111111111"
    )
    # None (unresolved) is identity too.
    assert capability.format_value("4111111111111111", None, notation) == (
        "4111111111111111"
    )


def test_format_value_grouped_rechunk(capability: CreditCardCapability) -> None:
    # Decision 1 pins: groups of 4 from the left, last group takes the
    # remainder. Amex 15 renders 4-4-4-3, NEVER brand 4-6-5 — presentation
    # never sniffs brand.
    cases = [
        ("4111111111111111", "4111 1111 1111 1111"),  # 16 -> 4-4-4-4
        ("378282246310005", "3782 8224 6310 005"),  # 15 -> 4-4-4-3, not 4-6-5
        ("36050234196908", "3605 0234 1969 08"),  # 14 -> 4-4-4-2
        ("4111111111111111110", "4111 1111 1111 1111 110"),  # 19 -> 4-4-4-4-3
    ]
    for value, expected in cases:
        notation = PANNotation(digits=value, compact=value)
        assert capability.format_value(value, "grouped", notation) == expected, value


def test_grouped_reentry_identical(capability: CreditCardCapability) -> None:
    # Rendered grouped re-recognizes and re-renders string-exact (encoding).
    for digits in ["4111111111111111", "378282246310005", "36050234196908"]:
        notation = PANNotation(digits=digits, compact=digits)
        rendered = capability.format_value(digits, "grouped", notation)
        matches = PANRecognitionGrammar().recognize(rendered)
        assert len(matches) == 1, rendered
        assert matches[0].notation.digits == digits
        again = capability.format_value(
            matches[0].notation.digits, "grouped", matches[0].notation
        )
        assert again == rendered


def test_cli_credit_card_branch() -> None:
    from paxman.cli import _create_contract

    contract = _create_contract("credit_card")
    assert isinstance(contract, CreditCardContract)
    assert contract.output_format == "pan"


def test_shipped_contains_credit_card() -> None:
    assert "credit_card" in list_shipped_capabilities()
