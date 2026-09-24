"""Tests for the ASCII hostname recognition grammar (Task 4)."""

import pytest

from paxman.capabilities.Domain.grammar.ascii_hostname import (
    AsciiHostnameGrammar,
)
from paxman.capabilities.Domain.grammar.idn_hostname import (
    IdnHostnameGrammar,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestAsciiHostnameGrammar:
    """Grammar: ascii_hostname."""

    def setup_method(self) -> None:
        self.grammar: Grammar = AsciiHostnameGrammar()

    def test_semantics_and_name(self) -> None:
        assert self.grammar.name == "ascii_hostname"
        assert self.grammar.semantics == "ascii_hostname"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_recognizes_simple_fqdn(self) -> None:
        results = self.grammar.recognize("example.com")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 11
        assert results[0].raw_text == "example.com"
        assert results[0].notation.labels == ("example", "com")
        assert results[0].notation.tld == "com"
        assert results[0].notation.raw == "example.com"

    def test_recognizes_uppercase_input(self) -> None:
        results = self.grammar.recognize("EXAMPLE.COM")
        assert len(results) == 1
        assert results[0].notation.labels == ("example", "com")
        assert results[0].raw_text == "EXAMPLE.COM"

    def test_recognizes_trailing_dot(self) -> None:
        results = self.grammar.recognize("example.com.")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 12
        assert results[0].notation.labels == ("example", "com")

    def test_misses_in_container(self) -> None:
        results = self.grammar.recognize("visit example.com today")
        assert [(r.start, r.end) for r in results] == [(0, 5), (6, 17), (18, 23)]

    def test_misses_left_dot_neighbor(self) -> None:
        assert self.grammar.recognize(".example.com") == []

    def test_misses_non_ascii_only_input(self) -> None:
        assert self.grammar.recognize("münchen.de") == []


@pytest.mark.capability
class TestIdnHostnameGrammar:
    """Grammar: idn_hostname."""

    def setup_method(self) -> None:
        self.ascii_grammar: Grammar = AsciiHostnameGrammar()
        self.grammar: Grammar = IdnHostnameGrammar()

    def test_idn_semantics_and_name(self) -> None:
        assert self.grammar.name == "idn_hostname"
        assert self.grammar.semantics == "idn_hostname"

    def test_idn_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_idn_recognizes_unicode_labels(self) -> None:
        results = self.grammar.recognize("münchen.de")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 10
        assert results[0].notation.labels == ("münchen", "de")
        assert results[0].notation.tld == "de"

    def test_idn_recognizes_fullwidth_dot(self) -> None:
        results = self.grammar.recognize("ｅxample。ｊｐ")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 10
        assert results[0].notation.labels == ("example", "jp")

    def test_idn_misses_ascii_punctuation(self) -> None:
        assert self.grammar.recognize("[::1]") == []
        assert self.grammar.recognize("user@example.com") == []
        assert self.grammar.recognize("https://example.com/") == []

    def test_ascii_idn_overlap_dedup(self) -> None:
        ascii_results = self.ascii_grammar.recognize("example.com")
        idn_results = self.grammar.recognize("example.com")
        assert len(ascii_results) == len(idn_results) == 1
        assert ascii_results[0].start == idn_results[0].start
        assert ascii_results[0].end == idn_results[0].end
