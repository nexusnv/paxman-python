"""Tests for UUIDRecognitionGrammar (RFC 9562 §4 carriers)."""

import pytest

from paxman.capabilities.UUID.grammar.uuid_recognition import UUIDRecognitionGrammar


@pytest.mark.capability
class TestUUIDRecognitionGrammar:
    """One grammar answers every §2.1 RECOGNIZE carrier."""

    def setup_method(self) -> None:
        self.grammar = UUIDRecognitionGrammar()

    def test_name_semantics_single_value(self) -> None:
        assert self.grammar.name == "uuid_recognition"
        assert self.grammar.semantics == "uuid_recognition"
        assert self.grammar.single_value is True

    def test_canonical_span(self) -> None:
        (match,) = self.grammar.recognize("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        assert (match.start, match.end) == (0, 36)
        assert match.raw_text == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert match.notation.compact == "6ba7b8109dad11d180b400c04fd430c8"
        assert match.notation.hyphenated == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        assert match.notation.version == "1"

    def test_uppercase_fold(self) -> None:
        (match,) = self.grammar.recognize("6BA7B810-9DAD-11D1-80B4-00C04FD430C8")
        assert (match.start, match.end) == (0, 36)
        assert match.notation.compact == "6ba7b8109dad11d180b400c04fd430c8"

    def test_bare_32_span(self) -> None:
        (match,) = self.grammar.recognize("6ba7b8109dad11d180b400c04fd430c8")
        assert (match.start, match.end) == (0, 32)
        assert match.notation.hyphenated == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    def test_braced_span_includes_braces(self) -> None:
        (match,) = self.grammar.recognize("{6ba7b810-9dad-11d1-80b4-00c04fd430c8}")
        assert (match.start, match.end) == (0, 38)
        assert match.raw_text == "{6ba7b810-9dad-11d1-80b4-00c04fd430c8}"
        assert match.notation.compact == "6ba7b8109dad11d180b400c04fd430c8"

    def test_urn_span_includes_prefix(self) -> None:
        (match,) = self.grammar.recognize(
            "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        )
        assert (match.start, match.end) == (0, 45)
        assert match.notation.urn == "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    def test_nil_max_spans(self) -> None:
        (nil,) = self.grammar.recognize("00000000-0000-0000-0000-000000000000")
        assert nil.notation.version == "nil"
        (mx,) = self.grammar.recognize("ffffffff-ffff-ffff-ffff-ffffffffffff")
        assert mx.notation.version == "max"

    def test_embedded_sentence_span(self) -> None:
        (match,) = self.grammar.recognize("id 6ba7b810-9dad-11d1-80b4-00c04fd430c8 ok")
        assert (match.start, match.end) == (3, 39)

    def test_two_mentions_both_claimed(self) -> None:
        first = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        second = "6fa459ea-ee8a-3ca4-894e-db77e160355e"
        matches = self.grammar.recognize(f"{first} then {second}")
        assert [(m.start, m.end) for m in matches] == [(0, 36), (42, 78)]

    def test_33hex_missing(self) -> None:
        assert self.grammar.recognize("6ba7b8109dad11d180b400c04fd430c8a") == []

    def test_37char_dashed_missing(self) -> None:
        assert self.grammar.recognize("6ba7b810-9dad-11d1-80b4-00c04fd430c8a") == []

    def test_hyphen_suffix_no_prefix_fallback(self) -> None:
        """id + hyphenated suffix reads MISSING, not a truncated prefix."""
        assert self.grammar.recognize("6ba7b810-9dad-11d1-80b4-00c04fd430c8-12") == []

    def test_glued_runs_missing(self) -> None:
        assert self.grammar.recognize("x6ba7b810-9dad-11d1-80b4-00c04fd430c8") == []
        assert self.grammar.recognize("6ba7b810-9dad-11d1-80b4-00c04fd430c8x") == []

    @pytest.mark.parametrize(
        "text",
        [
            "{6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8}",
            "}6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8{",
            "x{6ba7b810-9dad-11d1-80b4-00c04fd430c8}",
        ],
    )
    def test_unbalanced_or_glued_braces_missing(self, text: str) -> None:
        """Braces match paired-or-absent only (brace-aware guards)."""
        assert self.grammar.recognize(text) == []

    def test_non_hex_missing(self) -> None:
        assert self.grammar.recognize("6ga7b810-9dad-11d1-80b4-00c04fd430c8") == []

    def test_empty_missing(self) -> None:
        assert self.grammar.recognize("") == []
