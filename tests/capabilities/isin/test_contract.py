"""Tests for ISINContract — TDD per plan Task 2."""

from __future__ import annotations

import pytest

from paxman.capabilities.ISIN.capability import ISINCapability
from paxman.capabilities.ISIN.contract import ISINContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_default_isin_offered_grouped() -> None:
    assert ISINContract.DEFAULT_OUTPUT_FORMAT == "isin"
    assert frozenset({"grouped"}) == ISINContract.OFFERED_OUTPUT_FORMATS
    contract = ISINCapability.create_contract()
    assert isinstance(contract, ISINContract)
    assert contract.output_format == "isin"
    assert contract.capability_name == "isin"
    grouped = ISINContract(output_format="grouped")
    assert grouped.output_format == "grouped"
    via_factory = ISINCapability.create_contract(output_format="grouped")
    assert via_factory.output_format == "grouped"


def test_grouped_class_encoding_declared() -> None:
    doc = ISINContract.__doc__
    assert doc is not None
    assert "grouped" in doc
    assert "encoding" in doc


def test_unknown_format_contract_error() -> None:
    with pytest.raises(ContractError):
        ISINContract(output_format="paper")
    with pytest.raises(ContractError):
        ISINCapability.create_contract(output_format="upper")


def test_suppress_common_words_default_false() -> None:
    assert ISINContract().suppress_common_words is False
    assert ISINCapability.create_contract().suppress_common_words is False
