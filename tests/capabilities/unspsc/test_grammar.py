"""Tests for UNSPSC recognition grammar (scaffold)."""

import pytest

from paxman.capabilities.UNSPSC.grammar.unspsc_recognition import (
    UNSPSCRecognition,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestUNSPSCRecognition:
    """Grammar: unspsc_recognition."""

    def setup_method(self) -> None:
        self.grammar: Grammar = UNSPSCRecognition()

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "unspsc_recognition"

    def test_single_value_false(self) -> None:
        assert self.grammar.single_value is False

    def test_recognize_returns_empty(self) -> None:
        assert self.grammar.recognize("anything") == []
