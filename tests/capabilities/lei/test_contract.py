"""Tests for LEIContract — TDD per plan Task 2."""

from __future__ import annotations

import pytest

from paxman.capabilities.LEI.capability import LEICapability
from paxman.capabilities.LEI.contract import LEIContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_default_lei_offered_urn() -> None:
    assert LEIContract.DEFAULT_OUTPUT_FORMAT == "lei"
    assert frozenset({"urn"}) == LEIContract.OFFERED_OUTPUT_FORMATS
    contract = LEICapability.create_contract()
    assert isinstance(contract, LEIContract)
    assert contract.output_format == "lei"
    assert contract.capability_name == "lei"
    urn = LEIContract(output_format="urn")
    assert urn.output_format == "urn"
    via_factory = LEICapability.create_contract(output_format="urn")
    assert via_factory.output_format == "urn"


def test_urn_class_encoding_declared() -> None:
    doc = LEIContract.__doc__
    assert doc is not None
    assert "urn" in doc
    assert "encoding" in doc


def test_unknown_format_contract_error() -> None:
    with pytest.raises(ContractError):
        LEIContract(output_format="compact")
    with pytest.raises(ContractError):
        LEICapability.create_contract(output_format="grouped")


def test_suppress_common_words_default_false() -> None:
    assert LEIContract().suppress_common_words is False
    assert LEICapability.create_contract().suppress_common_words is False
