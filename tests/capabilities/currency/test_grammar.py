"""Tests for Currency recognition grammars.

Grammars are exercised directly (no rules): each test drives
Grammar.recognize() against raw text and asserts the emitted spans —
half-open [start, end) offsets, raw_text, and the CurrencyNotation
text/shape — mirroring Money's grammar test structure. Case folding is
grammar-owned (codes uppercase, words lowercase, symbols verbatim);
validity is the rules' job, so unknown shapes are still matched.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.Currency.grammar.code_recognition import CodeRecognition
from paxman.capabilities.Currency.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.Currency.grammar.word_recognition import WordRecognition
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.core.domain import RecognitionMatch

pytestmark = [pytest.mark.capability, pytest.mark.currency]

# Expected-span tuple: (raw_text, start, end, notation_text, shape).
Span = tuple[str, int, int, str, str]


def _assert_span_invariants(
    text: str, match: RecognitionMatch[CurrencyNotation]
) -> None:
    """Verify the RecognitionMatch span contract (half-open [start, end))."""
    assert 0 <= match.start <= match.end
    assert len(match.raw_text) == match.end - match.start
    assert match.raw_text == text[match.start : match.end]


def _assert_spans(
    text: str,
    expected: list[Span],
    results: list[RecognitionMatch[CurrencyNotation]],
) -> None:
    """Compare results against (raw_text, start, end, text, shape) tuples."""
    assert len(results) == len(expected)
    for match, (raw_text, start, end, notation_text, shape) in zip(
        results, expected, strict=True
    ):
        _assert_span_invariants(text, match)
        assert match.raw_text == raw_text
        assert match.start == start
        assert match.end == end
        assert match.notation.text == notation_text
        assert match.notation.shape == shape


class TestCodeRecognition:
    """Tests for CodeRecognition."""

    def setup_method(self) -> None:
        self.grammar = CodeRecognition()

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("USD", [("USD", 0, 3, "USD", "code")]),
            (" usd ", [("usd", 1, 4, "USD", "code")]),
            (
                "GBP, EUR",
                [("GBP", 0, 3, "GBP", "code"), ("EUR", 5, 8, "EUR", "code")],
            ),
        ],
    )
    def test_recognizes(self, text: str, expected_spans: list[Span]) -> None:
        """Standalone alpha-3 code shapes match, folded to uppercase (D3)."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("US$", []),
            ("xUSD", []),
            ("USD-500", []),
            ("USD500", []),
            ("123", []),
            ("", []),
        ],
    )
    def test_rejects(self, text: str, expected_spans: list[Span]) -> None:
        """Amount/sign-glued codes and inside-token codes do not match."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))


class TestSymbolRecognition:
    """Tests for SymbolRecognition."""

    def setup_method(self) -> None:
        self.grammar = SymbolRecognition()

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("US$", [("US$", 0, 3, "US$", "qualified_symbol")]),
            ("€", [("€", 0, 1, "€", "symbol")]),
            (
                "A$ is the Australian dollar",
                [("A$", 0, 2, "A$", "qualified_symbol")],
            ),
        ],
    )
    def test_recognizes(self, text: str, expected_spans: list[Span]) -> None:
        """Standalone symbol tokens match; qualified forms carry their shape."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("US$5", []),
            ("$500", []),
            ("x€", []),
            ("€5", []),
        ],
    )
    def test_rejects(self, text: str, expected_spans: list[Span]) -> None:
        """Amount-glued and inside-token symbols do not match."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("CA$", [("CA$", 0, 3, "CA$", "qualified_symbol")]),
        ],
    )
    def test_precedence(self, text: str, expected_spans: list[Span]) -> None:
        """Longest-first/qualified-first: "CA$" matches before bare "$" (D4)."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("us$", []),
            ("ca$", []),
            ("a$", []),
            ("Lei", []),
            ("Kr", []),
            ("RM", [("RM", 0, 2, "RM", "qualified_symbol")]),
            ("rm", []),
        ],
    )
    def test_case_exact(self, text: str, expected_spans: list[Span]) -> None:
        """Qualified and letter-symbols are case-exact (D4): lowercase is MISSING."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))


class TestWordRecognition:
    """Tests for WordRecognition."""

    def setup_method(self) -> None:
        self.grammar = WordRecognition()

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("euro", [("euro", 0, 4, "euro", "word")]),
            ("Euro", [("Euro", 0, 4, "euro", "word")]),
            ("EURO", [("EURO", 0, 4, "euro", "word")]),
            ("US Dollar", [("Dollar", 3, 9, "dollar", "word")]),
        ],
    )
    def test_recognizes(self, text: str, expected_spans: list[Span]) -> None:
        """Standalone display-name words match, folded to lowercase (D4)."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))

    @pytest.mark.parametrize(
        ("text", "expected_spans"),
        [
            ("Dollars", []),
            ("euro500", []),
            ("the", []),
            ("", []),
        ],
    )
    def test_rejects(self, text: str, expected_spans: list[Span]) -> None:
        """Plurals, amount-glued words, and non-token words do not match."""
        _assert_spans(text, expected_spans, self.grammar.recognize(text))
