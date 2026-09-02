"""Cover api package to restore per-package 95% gate."""

import pytest

import paxman
from paxman.capabilities import Email
from paxman.core.discovery import reset_registry


def test_canonicalize_rejects_non_str():
    paxman.register_all_shipped()
    contract = Email.create_contract()
    with pytest.raises(TypeError, match="expects str"):
        paxman.canonicalize(None, contract)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="expects str"):
        paxman.canonicalize(123, contract)  # type: ignore[arg-type]


def test_list_shipped_and_registered():
    # reset to test both
    reset_registry()
    try:
        shipped = paxman.list_shipped_capabilities()
        assert "email" in shipped
        assert "iban" in shipped
        assert "issn" in shipped
        assert "language" in shipped
        assert len(shipped) == 17
        registered = paxman.list_registered_capabilities()
        assert isinstance(registered, tuple)
        # after register, registered should equal shipped
        paxman.register_all_shipped()
        registered2 = paxman.list_registered_capabilities()
        assert set(registered2) == set(shipped)
    finally:
        reset_registry()
        paxman.register_all_shipped()
