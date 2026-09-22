"""Tests for GTIN recognition grammar."""

import pytest

from paxman.capabilities.GTIN.grammar.gtin_recognition import GTINRecognition
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestGTINRecognition:
    def setup_method(self) -> None:
        self.grammar: Grammar = GTINRecognition()

    def test_name_semantics_single_value(self) -> None:
        assert self.grammar.name == "gtin_recognition"
        assert self.grammar.semantics == "gtin_recognition"
        assert self.grammar.single_value is True

    def test_compact_per_length(self) -> None:
        for text, digits in [
            ("96385074", "96385074"),
            ("614141999996", "614141999996"),  # GTIN-12 (UPC-A flagship)
            ("5012345670003", "5012345670003"),
            ("10614141999993", "10614141999993"),
        ]:
            matches = self.grammar.recognize(text)
            assert len(matches) == 1, text
            assert matches[0].notation.digits == digits
            assert matches[0].notation.native_length == len(digits)

    def test_padded_14(self) -> None:
        matches = self.grammar.recognize("00614141999996")
        assert len(matches) == 1
        assert matches[0].notation.digits == "00614141999996"
        assert matches[0].notation.native_length == 14

    def test_hri_spaced(self) -> None:
        m1 = self.grammar.recognize("6 14141 99999 6")
        assert len(m1) == 1
        assert m1[0].notation.digits == "614141999996"
        m2 = self.grammar.recognize("1234 5670")
        assert len(m2) == 1
        assert m2[0].notation.digits == "12345670"

    def test_hyphen_grouped(self) -> None:
        m = self.grammar.recognize("590-1234-12345-7")
        assert len(m) == 1
        assert m[0].notation.digits == "5901234123457"

    def test_labels(self) -> None:
        for text, digits in [
            ("GTIN: 00614141999996", "00614141999996"),
            ("upc-614141999996", "614141999996"),
            ("EAN-13: 5012345670003", "5012345670003"),
            ("GTIN-14 10614141999993", "10614141999993"),
        ]:
            matches = self.grammar.recognize(text)
            assert len(matches) == 1, text
            assert matches[0].notation.digits == digits
            # span includes label
            assert (matches[0].start, matches[0].end) == (0, len(text))
            # digits label-free: the emitted digits appear verbatim in the
            # input (label digits like the "14" in "GTIN-14" are stripped)
            assert digits in text, text

    def test_gtin14_label_decontamination(self) -> None:
        # "GTIN-14" label carries digits "14" — emit must strip them.
        m = self.grammar.recognize("GTIN-14 10614141999993")
        assert len(m) == 1
        assert m[0].notation.digits == "10614141999993"
        assert len(m[0].notation.digits) == 14

    def test_ai_wrapped(self) -> None:
        for text in [
            "(01)03453120000011",
            "(01) 03453120000011",
            "AI 01 03453120000011",
        ]:
            matches = self.grammar.recognize(text)
            assert len(matches) == 1, text
            assert matches[0].notation.digits == "03453120000011"
            assert matches[0].notation.has_ai is True
            assert (matches[0].start, matches[0].end) == (0, len(text))

    def test_stacked_label_ai(self) -> None:
        m = self.grammar.recognize("GTIN: (01)03453120000011")
        assert len(m) == 1
        assert m[0].notation.digits == "03453120000011"
        assert m[0].notation.has_ai is True

    def test_leading01_bare_not_stripped(self) -> None:
        m = self.grammar.recognize("01345678901234")
        assert len(m) == 1
        assert m[0].notation.digits == "01345678901234"
        assert m[0].notation.has_ai is False

    def test_compact_runon_two_mentions(self) -> None:
        # Single-space adjacency must not let the 14-digit arm run on into
        # the next mention: the run-on candidate is boundary-rejected, and
        # a shorter parse at the same start must still win (otherwise the
        # FIRST mention is silently lost and two-entity input returns a
        # false single-entity SUCCESS).
        m = self.grammar.recognize("5012345670003 614141999996")
        assert [(x.notation.digits, x.start, x.end) for x in m] == [
            ("5012345670003", 0, 13),
            ("614141999996", 14, 26),
        ]

    def test_hri_pair_single_space(self) -> None:
        # Two HRI-grouped mentions separated by one space: each arm must
        # stop at its own mention end.
        m = self.grammar.recognize("6 14141 99999 6 96385074")
        assert [(x.notation.digits, x.start, x.end) for x in m] == [
            ("614141999996", 0, 15),
            ("96385074", 16, 24),
        ]

    def test_runon_letter_adjacent_shorter_wins(self) -> None:
        # Same start-loss with a letter after the run-on: the whole first
        # GTIN must still be recognized.
        m = self.grammar.recognize("5012345670003 6x")
        assert [(x.notation.digits, x.start, x.end) for x in m] == [
            ("5012345670003", 0, 13),
        ]

    def test_exact_lengths_only(self) -> None:
        for text in [
            "012345",  # 6-digit UPC-E
            "1234567",  # 7-digit stem
            "614141999",  # 9-digit
            "6141419999",  # 10-digit
            "61414199999",  # 11-digit stem
            "501234567000345",  # 15-digit
        ]:
            assert self.grammar.recognize(text) == [], text

    def test_upce8_collision_shape(self) -> None:
        m = self.grammar.recognize("01234567")
        assert len(m) == 1
        assert m[0].notation.digits == "01234567"

    def test_glued_label_missing(self) -> None:
        assert self.grammar.recognize("GTIN00614141999996") == []

    def test_fullwidth_missing(self) -> None:
        assert self.grammar.recognize("６１４１４１９９９９９６") == []

    def test_quoted_bracketed(self) -> None:
        for text in ['"5012345670003"', "[5012345670003]", "(01)03453120000011."]:
            m = self.grammar.recognize(text)
            assert len(m) == 1, text

    def test_trailing_period_excluded(self) -> None:
        m = self.grammar.recognize("Batch 5012345670003 shipped.")
        assert len(m) == 1
        s, e = m[0].start, m[0].end
        assert m[0].notation.digits == "5012345670003"
        assert "." not in "Batch 5012345670003 shipped."[s:e]
