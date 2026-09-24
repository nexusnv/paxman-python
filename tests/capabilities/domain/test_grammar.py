"""Tests for the ASCII hostname recognition grammar (scaffold)."""

import pytest

from paxman.capabilities.Domain.grammar.ascii_hostname import (
    AsciiHostnameGrammar,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestAsciiHostnameGrammar:
    """Grammar: ascii_hostname."""

    def setup_method(self) -> None:
        self.grammar: Grammar = AsciiHostnameGrammar()

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "ascii_hostname"

    def test_single_value_false(self) -> None:
        assert self.grammar.single_value is False

    def test_recognize_returns_empty(self) -> None:
        assert self.grammar.recognize("anything") == []
