"""Item 5 — contract surface unification.

CapabilityContract is the single source of truth. These tests drive Task 3:
they will FAIL until the engine removes getattr probes and Contract is demoted
from public exports.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit


def test_contract_not_exported_from_core_public_api() -> None:
    """After unification, `Contract` must NOT be exported from public surfaces."""
    import paxman
    import paxman.core as core

    assert not hasattr(core, "Contract"), (
        "Contract must not be re-exported from paxman.core"
    )
    assert not hasattr(paxman, "Contract"), (
        "Contract must not be re-exported from paxman (ADR-0007)"
    )


def test_capability_contract_is_only_public_base() -> None:
    """Every shipped contract must inherit CapabilityContract (homogeneity mandate)."""
    from paxman.capabilities.Country.contract import CountryContract
    from paxman.capabilities.Currency.contract import CurrencyContract
    from paxman.capabilities.Date.contract import DateContract
    from paxman.capabilities.Email.contract import EmailContract
    from paxman.capabilities.IP.contract import IPContract
    from paxman.capabilities.ISBN.contract import ISBNContract
    from paxman.capabilities.Money.contract import MoneyContract
    from paxman.capabilities.Phone.contract import PhoneContract
    from paxman.capabilities.SIUnit.contract import SIUnitContract
    from paxman.capabilities.URL.contract import URLCapabilityContract as URLContract
    from paxman.core.capability_contract import CapabilityContract

    for cls in [
        CountryContract,
        CurrencyContract,
        DateContract,
        EmailContract,
        IPContract,
        ISBNContract,
        MoneyContract,
        PhoneContract,
        SIUnitContract,
        URLContract,
    ]:
        assert issubclass(cls, CapabilityContract), (
            f"{cls.__name__} must inherit CapabilityContract"
        )


def test_recognize_requires_extra_grammars() -> None:
    """_recognize fails fast with ContractError when contract lacks extra_grammars."""

    from dataclasses import dataclass
    from typing import cast

    from paxman.core.capability_contract import CapabilityContract
    from paxman.core.errors import ContractError
    from paxman.engine.orchestrator import _recognize

    @dataclass(frozen=True)
    class _BadContract:
        capability_name: str = "email"
        # NOTE: no extra_grammars attribute at all

    with pytest.raises(ContractError):
        _recognize("hello", [], [], cast(CapabilityContract, _BadContract()))


def test_activated_rules_requires_extra_grammars() -> None:
    """_activated_rules fails fast without extra_grammars."""

    from dataclasses import dataclass
    from typing import cast

    from paxman.capabilities.Email.capability import EmailCapability
    from paxman.core.capability_contract import CapabilityContract
    from paxman.core.errors import ContractError
    from paxman.engine.orchestrator import _activated_rules

    @dataclass(frozen=True)
    class _BadContract:
        capability_name: str = "email"
        # NOTE: no extra_grammars attribute at all

    with pytest.raises(ContractError):
        _activated_rules(
            EmailCapability(), cast(CapabilityContract, _BadContract()), {}
        )


def test_engine_requires_extra_grammars_attribute() -> None:
    """A contract without extra_grammars fails fast with ContractError (ADR-0007)."""
    from dataclasses import dataclass
    from typing import cast

    from paxman.core.capability_contract import CapabilityContract
    from paxman.core.errors import ContractError
    from paxman.engine.orchestrator import _extra_grammars_of

    @dataclass(frozen=True)
    class _BadContract:
        capability_name: str = "email"
        # NOTE: no extra_grammars attribute at all

    with pytest.raises(ContractError):
        _extra_grammars_of(cast(CapabilityContract, _BadContract()))

    # A proper CapabilityContract resolves to its default empty tuple.
    from paxman.capabilities.Email.contract import EmailContract

    assert _extra_grammars_of(EmailContract()) == ()


def test_contract_factory_docstring_mentions_ten() -> None:
    """ContractFactory docstring must say fifteen, not five."""
    from paxman.core.capability import ContractFactory

    assert ContractFactory.__doc__ is not None
    assert "five" not in ContractFactory.__doc__.lower(), "stale 'five' must be fixed"
    assert "fifteen" in ContractFactory.__doc__.lower(), (
        "docstring must mention fifteen"
    )
