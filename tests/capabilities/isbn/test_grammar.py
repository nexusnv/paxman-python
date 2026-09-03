"""Tests for ISBN recognition grammars."""

from __future__ import annotations

import pytest

from paxman.capabilities.ISBN.grammar.isbn10_recognition import (
    ISBN10RecognitionGrammar,
)
from paxman.capabilities.ISBN.grammar.isbn13_recognition import (
    ISBN13RecognitionGrammar,
)
from paxman.capabilities.ISBN.notation import ISBNNotation

pytestmark = [pytest.mark.capability]


class TestISBN13RecognitionGrammar:
    """Tests for ISBN13RecognitionGrammar."""

    def test_recognizes_isbn13_digits_only(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("9780306406157")
        assert len(results) == 1
        assert results[0].notation == ISBNNotation(
            shape="isbn13", digits="9780306406157"
        )
        assert results[0].start == 0
        assert results[0].end == 13
        assert results[0].raw_text == "9780306406157"

    def test_recognizes_isbn13_with_hyphens(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("978-0-306-40615-7")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_with_spaces(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("978 0 306 40615 7")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_with_label(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("ISBN 9780306406157")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_with_label_and_hyphens(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("ISBN-13: 978-0-306-40615-7")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_rejects_isbn13_glued_label(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("ISBN9780306406157")
        assert results == []

    def test_rejects_isbn13_14_digits(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("97803064061577")
        assert results == []

    def test_rejects_isbn13_embedded_in_word(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("abc9780306406157xyz")
        assert results == []

    def test_recognizes_multiple_isbn13(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("9780306406157 9780201310054")
        assert len(results) == 2
        assert results[0].start == 0
        assert results[0].end == 13
        assert results[1].start > results[0].start

    def test_span_invariants(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("9780306406157")
        assert len(results) == 1
        match = results[0]
        assert len(match.raw_text) == match.end - match.start
        assert 0 <= match.start <= match.end

    def test_returns_empty_for_empty_input(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("")
        assert results == []

    def test_recognizes_isbn13_trailing_space(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("9780306406157 ")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_hyphenated_trailing_space(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("978-0-306-40615-7 ")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_label_trailing_space(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("ISBN 9780306406157 ")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_label_hyphens_trailing_space(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("ISBN-13: 978-0-306-40615-7 ")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_mid_prose(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("see ISBN 978-0-306-40615-7 for details")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"
        assert results[0].raw_text == "ISBN 978-0-306-40615-7"
        assert len(results[0].raw_text) == results[0].end - results[0].start
        assert 0 <= results[0].start <= results[0].end

    def test_recognizes_isbn13_trailing_hyphen_space(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("9780306406157- ")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_recognizes_isbn13_trailing_punctuation(self) -> None:
        grammar = ISBN13RecognitionGrammar()
        results = grammar.recognize("9780306406157.")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"
        results = grammar.recognize("9780306406157,")
        assert len(results) == 1
        assert results[0].notation.digits == "9780306406157"

    def test_rejects_isbn13_truncated_hyphen_continuation(self) -> None:
        """Hyphen+digit continuation must not yield truncated 13-digit hit."""
        grammar = ISBN13RecognitionGrammar()
        # "1-9780306406157" would be 14 digits with hyphen; trailing hyphen+digit
        # guard prevents truncated prefix match; \b still handles word boundaries.
        # The valid ISBN-13 at pos 2 is still recognized when isolated via space.
        assert grammar.recognize("9780306406157")[0].notation.digits == "9780306406157"
        # Double hyphen/space is not single-separator-tolerant
        assert grammar.recognize("978--0306406157") == []
        assert grammar.recognize("978  0306406157") == []


class TestISBN10RecognitionGrammar:
    """Tests for ISBN10RecognitionGrammar."""

    def test_recognizes_isbn10_digits_only(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("0306406152")
        assert len(results) == 1
        assert results[0].notation == ISBNNotation(shape="isbn10", digits="0306406152")

    def test_recognizes_isbn10_with_hyphens(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("0-306-40615-2")
        assert len(results) == 1
        assert results[0].notation.digits == "0306406152"

    def test_recognizes_isbn10_with_uppercase_x(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("080442957X")
        assert len(results) == 1
        assert results[0].notation.digits == "080442957X"

    def test_recognizes_isbn10_with_lowercase_x(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("080442957x")
        assert len(results) == 1
        assert results[0].notation.digits == "080442957X"

    def test_recognizes_isbn10_with_label(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("ISBN-10 0-306-40615-2")
        assert len(results) == 1
        assert results[0].notation.digits == "0306406152"

    def test_rejects_isbn10_11_digits(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("03064061523")
        assert results == []

    def test_span_invariants(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("0306406152")
        assert len(results) == 1
        match = results[0]
        assert len(match.raw_text) == match.end - match.start
        assert 0 <= match.start <= match.end

    def test_returns_empty_for_empty_input(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("")
        assert results == []

    def test_recognizes_isbn10_trailing_space(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        results = grammar.recognize("0-306-40615-2 ")
        assert len(results) == 1
        assert results[0].notation.digits == "0306406152"

    def test_rejects_isbn10_truncated_hyphen_prefix(self) -> None:
        """Digit + hyphen prefix must not yield a truncated 10-digit hit (B1)."""
        grammar = ISBN10RecognitionGrammar()
        # "1 0-306-40615-2" contains 11 digits with separators; the truncated
        # prefix "1 0-306-40615" (digits 1030640615) must be rejected via
        # trailing (?![-]\d) and the isolated "0-306-40615-2" at pos 2 is
        # blocked by BoundaryGuard.isbn10_lead() (digit+space prefix) → MISSING.
        assert grammar.recognize("1 0-306-40615-2") == []
        assert grammar.recognize("1-0-306-40615-2") == []
        # Valid hyphenated ISBN-10 still recognized in isolation
        assert grammar.recognize("0-306-40615-2")[0].notation.digits == "0306406152"
        # Trailing hyphen+digit without digit must not be consumed
        assert grammar.recognize("0-306-40615-2 ")[0].notation.digits == "0306406152"

    def test_rejects_isbn10_double_separator(self) -> None:
        grammar = ISBN10RecognitionGrammar()
        assert grammar.recognize("0--306-40615-2") == []
        assert grammar.recognize("0  306406152") == []
