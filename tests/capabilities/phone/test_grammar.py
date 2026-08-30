"""Tests for Phone recognition grammars."""

from paxman.capabilities.Phone.grammar.e164_recognition import E164Grammar
from paxman.capabilities.Phone.grammar.international_00_recognition import (
    International00Grammar,
)
from paxman.capabilities.Phone.grammar.national_recognition import NationalGrammar
from paxman.capabilities.Phone.grammar.tel_uri_recognition import TelUriGrammar


class TestE164Grammar:
    """Tests for E164Grammar."""

    def setup_method(self) -> None:
        self.grammar = E164Grammar()

    def test_recognizes_valid_input(self) -> None:
        """Happy path: grammar finds e164 pattern."""
        results = self.grammar.recognize("+15551234567")
        assert len(results) == 1
        assert results[0].notation.shape == "e164"
        assert results[0].notation.value == "15551234567"

    def test_recognizes_with_spaces(self) -> None:
        """Edge case: spaces between digit groups."""
        results = self.grammar.recognize("+1 555 123 4567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_with_dashes(self) -> None:
        """Edge case: dashes between digit groups."""
        results = self.grammar.recognize("+44-20-7946-0958")
        assert len(results) == 1
        assert results[0].notation.value == "442079460958"

    def test_recognizes_with_dots(self) -> None:
        """Edge case: dots between digit groups."""
        results = self.grammar.recognize("+1.555.123.4567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_with_parens(self) -> None:
        """Edge case: parentheses around area code."""
        results = self.grammar.recognize("+1 (555) 123-4567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_in_text(self) -> None:
        """Input contains e164 number within surrounding text."""
        results = self.grammar.recognize("Call me at +15551234567 today")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_multiple(self) -> None:
        """Input contains multiple e164 matches."""
        results = self.grammar.recognize("+15551234567 or +442079460958")
        assert len(results) == 2

    def test_ignores_number_without_plus(self) -> None:
        """Grammar does not match numbers without the + prefix."""
        results = self.grammar.recognize("15551234567")
        assert len(results) == 0

    def test_ignores_national_format(self) -> None:
        """Grammar does not match national (no +) formatting."""
        results = self.grammar.recognize("(555) 123-4567")
        assert len(results) == 0

    def test_ignores_plus_after_word_char(self) -> None:
        """A "+" preceded by a letter/digit must not match.

        Regression for false positives: email plus-tags ("user+123@..."),
        algebra ("x+11"), and arithmetic ("1+11") are not phone numbers.
        """
        for text in ("user+123@example.com", "a+123", "x+11=y", "1+11=12"):
            results = self.grammar.recognize(text)
            assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("Call +1 555 123 4567 now")
        assert len(results) == 1
        assert results[0].start == 5
        assert results[0].end == 20
        assert results[0].raw_text == "+1 555 123 4567"

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "e164_recognition"

    def test_spaced_15_digit_with_two_char_separators(self) -> None:
        """(#65) 15-digit spaced with 2-char gaps must not be truncated."""
        # 2-char gaps: " -" (space+dash) => 15 digits +14*2 +1 =44
        spaced2 = "+" + " -".join("123456789012345")
        assert len(spaced2) == 44
        results = self.grammar.recognize(spaced2)
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 44
        assert results[0].raw_text == spaced2
        assert results[0].notation.value == "123456789012345"

    def test_spaced_15_digit_with_three_char_separators(self) -> None:
        """(#65) 15-digit with 3-char gaps must not be truncated."""
        # 3-char gaps: " - " (space+dash+space) => 15+14*3+1 =58
        spaced3 = "+" + " - ".join("123456789012345")
        assert len(spaced3) == 58
        results = self.grammar.recognize(spaced3)
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 58
        assert results[0].raw_text == spaced3
        assert results[0].notation.value == "123456789012345"


class TestTelUriGrammar:
    """Tests for TelUriGrammar."""

    def setup_method(self) -> None:
        self.grammar = TelUriGrammar()

    def test_recognizes_global_number(self) -> None:
        """Happy path: tel: URI with global number."""
        results = self.grammar.recognize("tel:+15551234567")
        assert len(results) == 1
        assert results[0].notation.shape == "rfc3966"
        assert results[0].notation.value == "15551234567"

    def test_recognizes_with_dashes(self) -> None:
        """Edge case: dashes in URI number."""
        results = self.grammar.recognize("tel:+1-201-555-0123")
        assert len(results) == 1
        assert results[0].notation.value == "12015550123"

    def test_recognizes_with_extension(self) -> None:
        """Edge case: ;ext= parameter."""
        results = self.grammar.recognize("tel:+15551234567;ext=890")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"
        assert results[0].notation.extension == "890"

    def test_recognizes_in_text(self) -> None:
        """Input contains tel: URI within surrounding text."""
        results = self.grammar.recognize("Reach me at tel:+15551234567 now")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_uppercase_scheme(self) -> None:
        """Edge case: uppercase TEL: scheme."""
        results = self.grammar.recognize("TEL:+15551234567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_ignores_plain_number(self) -> None:
        """Grammar does not match numbers without tel: scheme."""
        results = self.grammar.recognize("+15551234567")
        assert len(results) == 0

    def test_ignores_local_number_without_plus(self) -> None:
        """No-plus tel: URIs are local numbers, not global numbers.

        Regression for RFC 3966 §3.1: global-number-digits requires a
        leading "+". Without it the URI is a local number (out of scope),
        so the grammar must NOT extract a global-shaped notation from it.
        """
        for text in ("tel:2125550123", "tel:15551234567", "tel:44 20 7946 0958"):
            results = self.grammar.recognize(text)
            assert len(results) == 0

    def test_ignores_scheme_inside_word(self) -> None:
        """The tel: scheme must not match inside another word."""
        for text in ("hotel:+15551234567", "xtel:+15551234567"):
            results = self.grammar.recognize(text)
            assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("tel:+15551234567")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 16
        assert results[0].raw_text == "tel:+15551234567"
        assert results[0].notation.extension == ""

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "tel_uri_recognition"


class TestInternational00Grammar:
    """Tests for International00Grammar."""

    def setup_method(self) -> None:
        self.grammar = International00Grammar()

    def test_recognizes_valid_input(self) -> None:
        """Happy path: 00-prefixed international number."""
        results = self.grammar.recognize("00 44 20 7946 0958")
        assert len(results) == 1
        assert results[0].notation.shape == "e164"
        assert results[0].notation.value == "442079460958"

    def test_recognizes_compact(self) -> None:
        """Edge case: compact digits."""
        results = self.grammar.recognize("00442079460958")
        assert len(results) == 1
        assert results[0].notation.value == "442079460958"

    def test_recognizes_in_text(self) -> None:
        """Input contains 00 number within surrounding text."""
        results = self.grammar.recognize("Dial 00 44 20 7946 0958 from abroad")
        assert len(results) == 1
        assert results[0].notation.value == "442079460958"

    def test_ignores_number_with_plus(self) -> None:
        """Grammar does not match +-prefixed numbers."""
        results = self.grammar.recognize("+442079460958")
        assert len(results) == 0

    def test_ignores_single_zero(self) -> None:
        """Grammar does not match a single leading zero."""
        results = self.grammar.recognize("0 44 20 7946 0958")
        assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("00 44 20 7946 0958")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 18
        assert results[0].raw_text == "00 44 20 7946 0958"

    def test_does_not_swallow_sentence_punctuation(self) -> None:
        """Trailing sentence punctuation is not part of the match.

        The trailing (?<=\\d) lookbehind forces the match to end on a digit,
        so the sentence-ending period is excluded from span and raw_text.
        """
        results = self.grammar.recognize("00 44 20 7946 0958.")
        assert len(results) == 1
        assert results[0].notation.value == "442079460958"
        assert results[0].start == 0
        assert results[0].end == 18
        assert results[0].raw_text == "00 44 20 7946 0958"
        assert (
            results[0].raw_text
            == "00 44 20 7946 0958."[results[0].start : results[0].end]
        )

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "international_00_recognition"


class TestNationalGrammar:
    """Tests for NationalGrammar."""

    def setup_method(self) -> None:
        self.grammar = NationalGrammar()

    def test_recognizes_parenthesized(self) -> None:
        """Happy path: (NPA) NXX-XXXX format."""
        results = self.grammar.recognize("(555) 123-4567")
        assert len(results) == 1
        assert results[0].notation.shape == "national"
        assert results[0].notation.value == "5551234567"

    def test_recognizes_dashes(self) -> None:
        """Edge case: NPA-NXX-XXXX format."""
        results = self.grammar.recognize("555-123-4567")
        assert len(results) == 1
        assert results[0].notation.value == "5551234567"

    def test_recognizes_dots(self) -> None:
        """Edge case: NPA.NXX.XXXX format."""
        results = self.grammar.recognize("555.123.4567")
        assert len(results) == 1
        assert results[0].notation.value == "5551234567"

    def test_recognizes_spaces(self) -> None:
        """Edge case: space-separated format."""
        results = self.grammar.recognize("555 123 4567")
        assert len(results) == 1
        assert results[0].notation.value == "5551234567"

    def test_recognizes_with_trunk(self) -> None:
        """Edge case: leading trunk 1 preserved."""
        results = self.grammar.recognize("1-555-123-4567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_trunk_with_parens(self) -> None:
        """Edge case: trunk with parenthesized NPA."""
        results = self.grammar.recognize("1 (555) 123-4567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"

    def test_recognizes_in_text(self) -> None:
        """Input contains national number within surrounding text."""
        results = self.grammar.recognize("Call (555) 123-4567 today")
        assert len(results) == 1
        assert results[0].notation.value == "5551234567"

    def test_ignores_international(self) -> None:
        """Grammar does not match +-prefixed numbers."""
        results = self.grammar.recognize("+15551234567")
        assert len(results) == 0

    def test_ignores_international_with_separators(self) -> None:
        """Grammar does not match inside separated E.164 numbers.

        Regression for spec review: the lookbehind must reject matches whose
        preceding characters belong to an E.164 number ("+1-555-123-4567"
        belongs to the e164 grammar), not just compact "+15551234567".
        """
        for text in ("+1-555-123-4567", "+1 555 123 4567", "+1.555.123.4567"):
            results = self.grammar.recognize(text)
            assert len(results) == 0

    def test_ignores_international_with_parens(self) -> None:
        """Grammar does not match inside parenthesized E.164 numbers."""
        results = self.grammar.recognize("+1 (555) 123-4567")
        assert len(results) == 0

    def test_ignores_tel_uri(self) -> None:
        """Grammar does not match inside tel: URIs."""
        for text in (
            "tel:+1-201-555-0123",
            "tel:+15551234567",
            "tel:+1 (555) 123-4567",
        ):
            results = self.grammar.recognize(text)
            assert len(results) == 0

    def test_ignores_short_number(self) -> None:
        """Grammar does not match 7-digit local-only numbers."""
        results = self.grammar.recognize("555-1234")
        assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("(555) 123-4567")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 14
        assert results[0].raw_text == "(555) 123-4567"

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "national_recognition"


class TestGrammarDedup:
    """Span-bearing behavior across grammars (same value via different formats)."""

    def setup_method(self) -> None:
        self.e164 = E164Grammar()
        self.tel_uri = TelUriGrammar()
        self.i00 = International00Grammar()
        self.national = NationalGrammar()

    def test_e164_returns_same_value_at_distinct_spans(self) -> None:
        """The same number in two formats yields two span-bearing matches.

        Grammar-level value dedup is removed; the engine collapses identical
        candidates at the candidate stage.
        """
        results = self.e164.recognize("Call +1 555 123 4567 or +15551234567")
        assert len(results) == 2
        assert [r.notation.value for r in results] == [
            "15551234567",
            "15551234567",
        ]
        assert [(r.start, r.end) for r in results] == [(5, 20), (24, 36)]

    def test_e164_does_not_swallow_following_number(self) -> None:
        """A space-separated run after an E.164 match is not merged into it.

        Regression: the trailing character class of _E164_PATTERN consumed
        separators AND following digit runs, so "+15551234567 5551234567"
        yielded one 20-digit match. recognize() now trims the raw match at
        the last digit-run group within the 15-digit E.164 limit, so the
        match stops at "+15551234567" and the national-format run is left
        for other grammars.
        """
        results = self.e164.recognize("+15551234567 5551234567")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"
        assert (results[0].start, results[0].end) == (0, 12)
        assert results[0].raw_text == "+15551234567"

    def test_e164_oversized_run_not_truncated(self) -> None:
        """A digit run longer than 15 digits is left whole, not truncated.

        The boundary trim keeps the full raw match when the first run alone
        exceeds _MAX_E164_DIGITS, so validation rejects the oversized value
        (INVALID) instead of silently recognizing a 15-digit prefix.
        """
        results = self.e164.recognize("+12345678901234567890")
        assert len(results) == 1
        assert results[0].notation.value == "12345678901234567890"

    def test_tel_uri_multiple_matches(self) -> None:
        """Multiple distinct tel: URIs are all returned."""
        results = self.tel_uri.recognize("tel:+15551234567 and tel:+442079460958")
        assert len(results) == 2

    def test_i00_multiple_matches(self) -> None:
        """Multiple distinct 00-prefixed numbers are all returned."""
        results = self.i00.recognize("00 44 20 7946 0958 or 00 1 555 234 5678")
        assert len(results) == 2

    def test_national_multiple_matches(self) -> None:
        """Multiple distinct national numbers are all returned."""
        results = self.national.recognize("Call (555) 123-4567 today or (212) 234-5678")
        assert len(results) == 2

    def test_e164_trailing_period_still_digit_correct(self) -> None:
        """A trailing sentence period is stripped, value stays digit-only."""
        results = self.e164.recognize("End of +15551234567.")
        assert len(results) == 1
        assert results[0].notation.value == "15551234567"


class TestInternational00Boundary:
    """Boundary cases for the 00-prefix lookbehind."""

    def setup_method(self) -> None:
        self.grammar = International00Grammar()

    def test_ignores_00_embedded_in_digits(self) -> None:
        """'100442079460958' must NOT match (00 preceded by digit)."""
        results = self.grammar.recognize("100442079460958")
        assert len(results) == 0

    def test_ignores_00_after_plus(self) -> None:
        """'+00442079460958' is contradictory input; 00 grammar skips it."""
        # The e164 grammar may match it; the 00 grammar must not treat
        # '+00...' as a 00-prefixed number.
        results = self.grammar.recognize("+00442079460958")
        assert len(results) == 0

    def test_ignores_00_after_word_char_or_dot(self) -> None:
        """A '00' preceded by a letter or '.' must not match.

        Regression for false positives: '0.00442079460958' (decimal) and
        'user00123@example.com' (email local part) are not phone numbers.
        """
        for text in ("0.00442079460958", "user00123@example.com", "x0044 20 7946 0958"):
            results = self.grammar.recognize(text)
            assert len(results) == 0
