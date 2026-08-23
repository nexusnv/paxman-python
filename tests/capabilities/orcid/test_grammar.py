"""Tests for ORCID recognition grammar (scaffold)."""

import pytest

from paxman.capabilities.ORCID.grammar.orcid_recognition import (
    ORCIDRecognition,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestORCIDRecognition:
    """Grammar: orcid_recognition."""

    def setup_method(self) -> None:
        self.grammar: Grammar = ORCIDRecognition()

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "orcid_recognition"

    def test_single_value_false(self) -> None:
        assert self.grammar.single_value is False

    def test_recognize_returns_empty(self) -> None:
        assert self.grammar.recognize("anything") == []
