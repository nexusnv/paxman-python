"""Tests for MacAddress recognition grammar (scaffold)."""

import pytest

from paxman.capabilities.MacAddress.grammar.mac_address_recognition import (
    MacAddressRecognition,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestMacAddressRecognition:
    """Grammar: mac_address_recognition."""

    def setup_method(self) -> None:
        self.grammar: Grammar = MacAddressRecognition()

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "mac_address_recognition"

    def test_single_value_false(self) -> None:
        assert self.grammar.single_value is False

    def test_recognize_returns_empty(self) -> None:
        assert self.grammar.recognize("anything") == []
