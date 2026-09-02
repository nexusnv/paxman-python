"""Tests for ISSN recognition grammar."""

from __future__ import annotations

import pytest

from paxman.capabilities.ISSN.grammar.issn_recognition import ISSNRecognitionGrammar

pytestmark = [pytest.mark.capability]


class TestISSNRecognitionGrammar:
    """ISSN recognition: strict hyphen at pos 4, optional label, BoundaryGuard."""

    def test_bare_hyphenated(self) -> None:
        grammar = ISSNRecognitionGrammar()
        results = grammar.recognize("0317-8471")
        assert len(results) == 1
        assert results[0].notation.digits == "03178471"
        assert results[0].start == 0
        assert results[0].end == 9
        assert results[0].raw_text == "0317-8471"

    def test_bare_compact(self) -> None:
        grammar = ISSNRecognitionGrammar()
        results = grammar.recognize("03178471")
        assert len(results) == 1
        assert results[0].notation.digits == "03178471"
        assert results[0].raw_text == "03178471"
        assert results[0].start == 0
        assert results[0].end == 8

    def test_label_issn(self) -> None:
        grammar = ISSNRecognitionGrammar()
        for text in ("ISSN 0317-8471", "ISSN: 0317-8471"):
            results = grammar.recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation.digits == "03178471"
            assert results[0].raw_text == text
            assert results[0].start == 0
            assert results[0].end == len(text)

    def test_label_variants(self) -> None:
        grammar = ISSNRecognitionGrammar()
        cases = [
            ("ISSN-L 0264-2875", "02642875"),
            ("ISSN-H 1365-201X", "1365201X"),
        ]
        for text, expected_digits in cases:
            results = grammar.recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation.digits == expected_digits
            assert results[0].raw_text == text

    def test_lowercase_label_and_x_fold(self) -> None:
        grammar = ISSNRecognitionGrammar()
        results = grammar.recognize("issn 1050-124x")
        assert len(results) == 1
        assert results[0].notation.digits == "1050124X"
        assert results[0].raw_text == "issn 1050-124x"

    def test_leading_zeros_preserved(self) -> None:
        grammar = ISSNRecognitionGrammar()
        results = grammar.recognize("0000-0019")
        assert len(results) == 1
        assert results[0].notation.digits == "00000019"

    def test_embedded_in_prose(self) -> None:
        grammar = ISSNRecognitionGrammar()
        text = "see ISSN 0317-8471 (print)"
        results = grammar.recognize(text)
        assert len(results) == 1
        assert results[0].raw_text == "ISSN 0317-8471"
        assert results[0].start == text.index("ISSN 0317-8471")
        assert results[0].end == results[0].start + len("ISSN 0317-8471")

    def test_glued_label_matches(self) -> None:
        # Current pattern uses [\s:-]* so glued label IS matched as ISSN03178471.
        # The strict variant with [\s:-]+ would reject it; we document the
        # actual behavior and assert the match is present with full span.
        grammar = ISSNRecognitionGrammar()
        results = grammar.recognize("ISSN03178471")
        assert len(results) == 1
        assert results[0].raw_text == "ISSN03178471"
        assert results[0].notation.digits == "03178471"

    def test_wrong_hyphen_placement(self) -> None:
        grammar = ISSNRecognitionGrammar()
        assert grammar.recognize("12-345679") == []

    def test_tolerant_space_hyphen_rejects(self) -> None:
        grammar = ISSNRecognitionGrammar()
        assert grammar.recognize("1234 - 5679") == []
        assert grammar.recognize("1234 5679") == []

    def test_unicode_dash_missing(self) -> None:
        grammar = ISSNRecognitionGrammar()
        # Hyphen-minus only: en/em dashes break digit contiguity -> MISSING.
        assert grammar.recognize("1234\u20135679") == []
        assert grammar.recognize("1234\u20145679") == []

    def test_digit_glued_rejects(self) -> None:
        grammar = ISSNRecognitionGrammar()
        # 9-digit run must not yield an inner 8-char ISSN
        assert grammar.recognize("912345679") == []
        # trailing letter glued without word boundary
        assert grammar.recognize("1234-5679a") == []
        # letter-preceded must be rejected via word boundary
        assert grammar.recognize("a0317-8471") == []

    def test_rejects_hyphen_digit_continuation(self) -> None:
        grammar = ISSNRecognitionGrammar()
        # Hyphen-digit continuation must not yield truncated prefix.
        # WORD alone sees "-" as non-\w, so "0317-8471-2" would otherwise
        # match "0317-8471" at 0; trailing (?![-]\d) blocks it.
        assert grammar.recognize("0317-8471-2") == []
        assert grammar.recognize("03178471-2") == []
        assert grammar.recognize("ISSN 0317-8471-2") == []
        # Hyphen alone or hyphen+space/punct is fine (prefix is isolated).
        assert len(grammar.recognize("0317-8471.")) == 1
        assert len(grammar.recognize("0317-8471, next")) == 1
        assert len(grammar.recognize("0317-8471 ")) == 1
        assert grammar.recognize("0317-8471- 2")[0].raw_text == "0317-8471"

    def test_multiple_spans(self) -> None:
        grammar = ISSNRecognitionGrammar()
        text = "0317-8471 0378-5955"
        results = grammar.recognize(text)
        assert len(results) == 2
        assert results[0].start < results[1].start
        for m in results:
            assert len(m.raw_text) == m.end - m.start

    def test_span_invariants(self) -> None:
        grammar = ISSNRecognitionGrammar()
        texts = [
            "0317-8471",
            "ISSN 0317-8471",
            "see ISSN 0317-8471 (print)",
            "0317-8471  0378-5955",
        ]
        for text in texts:
            for m in grammar.recognize(text):
                assert 0 <= m.start <= m.end <= len(text)
                assert m.raw_text == text[m.start : m.end]
                assert len(m.raw_text) == m.end - m.start

    def test_empty(self) -> None:
        grammar = ISSNRecognitionGrammar()
        assert grammar.recognize("") == []
        assert grammar.recognize("   ") == []

    def test_name_and_semantics(self) -> None:
        grammar = ISSNRecognitionGrammar()
        assert grammar.name == "issn_recognition"
        assert grammar.semantics == "issn_recognition"
        assert grammar.semantics != ""
