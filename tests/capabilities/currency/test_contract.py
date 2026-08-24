# tests/capabilities/currency/test_contract.py
"""CurrencyContract configuration tests."""

from __future__ import annotations

from typing import cast

import pytest

from paxman.capabilities.Currency.capability import CurrencyCapability
from paxman.capabilities.Currency.contract import CurrencyContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability, pytest.mark.currency]


def test_capability_name() -> None:
    assert CurrencyContract().capability_name == "currency"


def test_active_grammars_defaults_to_all_shipped() -> None:
    """No override: the engine runs every shipped grammar (fallback)."""
    assert CurrencyContract().active_grammars is None
    assert [g.name for g in CurrencyCapability().get_grammars()] == [
        "code_recognition",
        "symbol_recognition",
        "word_recognition",
    ]


def test_default_output_format_resolution() -> None:
    assert CurrencyContract().output_format == "code"
    assert CurrencyContract(output_format=None).output_format == "code"
    assert CurrencyContract(output_format="default").output_format == "code"
    assert CurrencyContract(output_format="code").output_format == "code"


def test_unsupported_output_format_rejected() -> None:
    with pytest.raises(ContractError):
        CurrencyContract(output_format="compact")  # Money's format, not offered here


def test_default_currency_default_is_none() -> None:
    assert CurrencyContract().default_currency is None


@pytest.mark.parametrize("value", ["usd", "US", "USDD", "U5D", 123, ""])
def test_invalid_default_currency(value: object) -> None:
    with pytest.raises(ContractError):
        # cast keeps the deliberately-invalid input type-safe at the
        # boundary; runtime validation rejects non-str/improper values.
        CurrencyContract(default_currency=cast(str, value))


def test_valid_default_currency() -> None:
    assert CurrencyContract(default_currency="USD").default_currency == "USD"


def test_common_block() -> None:
    c = CurrencyContract(
        excluded_rules=("Section-code",),
        pinned_rules=None,
        year=2020,
    )
    assert c.excluded_rules == ("Section-code",)
    assert c.year == 2020
