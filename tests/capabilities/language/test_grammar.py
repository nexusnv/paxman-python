"""Tests for Language recognition grammar (scaffold)."""

import pytest

from paxman.capabilities.Language.grammar.language_recognition import (
    LanguageRecognition,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestLanguageRecognition:
    """Grammar: language_recognition."""

    def setup_method(self) -> None:
        self.grammar: Grammar = LanguageRecognition()

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "language_recognition"

    def test_single_value_false(self) -> None:
        assert self.grammar.single_value is False

    def test_recognize_returns_empty(self) -> None:
        assert self.grammar.recognize("anything") == []
