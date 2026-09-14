"""Tests for UtcOffset recognition grammar (Task 5: offset regex).

Human-notation offsets (``UTC|GMT`` prefix optional, ``±HH[:MM]`` /
``±HHMM``, ``Z``) with word guards plus a slash-aware lookbehind so no
offset is carved out of a zone key (``Etc/GMT+5``). Emit normalizes to
canonical ``+HH:MM`` (``Z`` → ``+00:00``); ``-00:00`` is emitted here —
the rule refuses it.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.UtcOffset.grammar.utc_offset_recognition import (
    UtcOffsetGrammar,
)


@pytest.mark.capability
class TestUtcOffsetGrammarIdentity:
    def setup_method(self) -> None:
        self.grammar = UtcOffsetGrammar()

    def test_name(self) -> None:
        assert self.grammar.name == "utc_offset_recognition"

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "utc_offset"

    def test_single_value(self) -> None:
        assert self.grammar.single_value is True


@pytest.mark.capability
class TestUtcOffsetRecognition:
    """Research §8 rows 5-8 + span checks + glued negatives."""

    def setup_method(self) -> None:
        self.grammar = UtcOffsetGrammar()

    def test_utc_prefixed_single_digit(self) -> None:
        (match,) = self.grammar.recognize("UTC+5")
        assert (match.start, match.end) == (0, 5)
        assert match.raw_text == "UTC+5"
        assert match.notation.compact == "+05:00"

    def test_lowercase_prefix_human_semantics(self) -> None:
        (match,) = self.grammar.recognize("utc+5")
        assert match.notation.compact == "+05:00"

    def test_gmt_prefixed_with_minutes(self) -> None:
        (match,) = self.grammar.recognize("GMT-05:30")
        assert (match.start, match.end) == (0, 9)
        assert match.notation.compact == "-05:30"

    def test_utc_prefixed_colon_minutes(self) -> None:
        (match,) = self.grammar.recognize("UTC+05:30")
        assert match.notation.compact == "+05:30"

    def test_basic_form_normalizes_to_extended(self) -> None:
        (match,) = self.grammar.recognize("+0530")
        assert (match.start, match.end) == (0, 5)
        assert match.notation.compact == "+05:30"

    def test_reduced_hour_only_form(self) -> None:
        (match,) = self.grammar.recognize("+05")
        assert match.notation.compact == "+05:00"

    def test_negative_extended(self) -> None:
        (match,) = self.grammar.recognize("-08:00")
        assert match.notation.compact == "-08:00"

    @pytest.mark.parametrize("token", ["Z", "z"])
    def test_z_designator_is_zero(self, token: str) -> None:
        (match,) = self.grammar.recognize(token)
        assert (match.start, match.end) == (0, 1)
        assert match.notation.compact == "+00:00"

    def test_unknown_offset_shape_still_emitted(self) -> None:
        """-00:00 is claimed here (shape); the rule refuses it (INVALID)."""
        (match,) = self.grammar.recognize("-00:00")
        assert (match.start, match.end) == (0, 6)
        assert match.notation.compact == "-00:00"

    def test_etc_key_yields_no_offset(self) -> None:
        """Slash-aware lookbehind: no mid-key extraction from Etc/GMT+5 —
        the key belongs solely to the Timezone name grammar."""
        assert self.grammar.recognize("Etc/GMT+5") == []

    def test_glued_prefix_missing(self) -> None:
        assert self.grammar.recognize("XUTC+5") == []

    def test_glued_suffix_missing(self) -> None:
        assert self.grammar.recognize("UTC+5X") == []

    def test_zulu_word_missing(self) -> None:
        assert self.grammar.recognize("Zulu") == []

    def test_glued_z_missing(self) -> None:
        assert self.grammar.recognize("AZ") == []

    def test_zoneinfo_path_missing(self) -> None:
        assert self.grammar.recognize("/usr/share/zoneinfo/America/New_York") == []

    def test_partial_minutes_missing(self) -> None:
        """Truncated minute fragments must not emit a shorter prefix (#162)."""
        assert self.grammar.recognize("+05:60") == []
        assert self.grammar.recognize("+05:6") == []
        assert self.grammar.recognize("+5:60") == []
        assert self.grammar.recognize("UTC+5:60") == []
        assert self.grammar.recognize("+05:00:00") == []
        assert self.grammar.recognize("++05:00") == []
        assert self.grammar.recognize("--05:00") == []

    def test_embedded_offset_span(self) -> None:
        (match,) = self.grammar.recognize("meeting at +05:30 tomorrow")
        assert (match.start, match.end) == (11, 17)
        assert match.notation.compact == "+05:30"

    def test_empty_missing(self) -> None:
        assert self.grammar.recognize("") == []
