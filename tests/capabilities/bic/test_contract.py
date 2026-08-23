"""Tests for BICContract — TDD per plan Task 2."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from paxman.capabilities.BIC.contract import BICContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_default_output_format_resolves() -> None:
    c = BICContract()
    assert c.output_format == "bic"
    assert c.capability_name == "bic"
    assert BICContract.DEFAULT_OUTPUT_FORMAT == "bic"
    assert frozenset({"grouped", "bic11"}) == BICContract.OFFERED_OUTPUT_FORMATS


def test_offered_grouped() -> None:
    c = BICContract(output_format="grouped")
    assert c.output_format == "grouped"


def test_bic11_offered() -> None:
    c = BICContract(output_format="bic11")
    assert c.output_format == "bic11"


def test_default_alias_via_none_and_default_string() -> None:
    for alias in (None, "default", "bic"):
        c = BICContract(output_format=alias)
        assert c.output_format == "bic"


def test_invalid_output_format_raises() -> None:
    with pytest.raises(ContractError):
        BICContract(output_format="hyphenated")  # ISSN ism, not BIC
    with pytest.raises(ContractError):
        BICContract(output_format="paper")  # IBAN ism, not BIC
    with pytest.raises(ContractError):
        BICContract(output_format="compact")  # not offered


def test_frozen_contract() -> None:
    c = BICContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "grouped"  # type: ignore[misc]
