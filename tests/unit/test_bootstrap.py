"""Unit tests for the register_all_shipped bootstrap helper."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities import Email
from paxman.core.discovery import (
    get_capability,
    is_registry_frozen,
    register_capability,
    reset_registry,
)


@pytest.fixture
def _clean_registry() -> Iterator[None]:
    reset_registry()
    yield
    reset_registry()


@pytest.mark.unit
def test_registers_all_ten_shipped(_clean_registry) -> None:
    names = paxman.register_all_shipped()
    expected = (
        "bic",
        "country",
        "currency",
        "date",
        "email",
        "iban",
        "ip",
        "isbn",
        "issn",
        "money",
        "phone",
        "si_unit",
        "url",
    )
    assert names == expected
    for name in expected:
        assert get_capability(name).name == name


@pytest.mark.unit
def test_idempotent_second_call_registers_nothing(_clean_registry) -> None:
    paxman.register_all_shipped()
    assert paxman.register_all_shipped() == ()


@pytest.mark.unit
def test_preserves_caller_registration(_clean_registry) -> None:
    mine = Email()
    register_capability(mine)
    names = paxman.register_all_shipped()
    assert "email" not in names
    assert len(names) == 12
    assert get_capability("email") is mine


@pytest.mark.unit
def test_does_not_freeze_registry(_clean_registry) -> None:
    paxman.register_all_shipped()
    assert is_registry_frozen() is False


@pytest.mark.unit
def test_raises_after_freeze(_clean_registry) -> None:
    """Natural freeze: one canonicalize() call freezes the registry; a later
    bootstrap with anything left to register must surface the error."""
    register_capability(Email())
    contract = Email.create_contract()
    paxman.canonicalize("user@example.com", contract)  # freezes naturally
    assert is_registry_frozen() is True
    # "url" was never registered, so the helper still has work to do — it
    # must raise (via register_capability's frozen check), never swallow.
    with pytest.raises(paxman.CapabilityError):
        paxman.register_all_shipped()
