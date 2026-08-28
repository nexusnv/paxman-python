"""Tests for Country recognition grammars."""

from paxman.capabilities.Country.grammar.alpha2_recognition import Alpha2Grammar
from paxman.capabilities.Country.grammar.alpha3_recognition import Alpha3Grammar
from paxman.capabilities.Country.grammar.name_recognition import NameGrammar
from paxman.capabilities.Country.grammar.numeric_recognition import NumericGrammar
from paxman.capabilities.Country.notation import CountryNotation, normalize_name


class TestAlpha2Grammar:
    """Tests for Alpha2Grammar."""

    def setup_method(self) -> None:
        self.grammar = Alpha2Grammar()

    def test_recognizes_valid_input(self) -> None:
        """Happy path: grammar finds alpha2 pattern."""
        results = self.grammar.recognize("US")
        assert len(results) == 1
        assert results[0].notation.shape == "alpha2"
        assert results[0].notation.value == "US"

    def test_recognizes_lowercase(self) -> None:
        """Edge case: lowercase input is uppercased."""
        results = self.grammar.recognize("gb")
        assert len(results) == 1
        assert results[0].notation.value == "GB"

    def test_recognizes_mixed_case(self) -> None:
        """Edge case: mixed case input is uppercased."""
        results = self.grammar.recognize("Us")
        assert len(results) == 1
        assert results[0].notation.value == "US"

    def test_recognizes_with_whitespace(self) -> None:
        """Edge case: whitespace is trimmed."""
        results = self.grammar.recognize("  US  ")
        assert len(results) == 1
        assert results[0].notation.value == "US"

    def test_recognizes_multiple(self) -> None:
        """Input contains multiple alpha2 matches."""
        results = self.grammar.recognize("US and GB")
        assert len(results) == 2

    def test_rejects_alpha3(self) -> None:
        """Grammar does not match 3-letter codes."""
        results = self.grammar.recognize("USA")
        assert len(results) == 0

    def test_rejects_numeric(self) -> None:
        """Grammar does not match digits."""
        results = self.grammar.recognize("12")
        assert len(results) == 0

    def test_rejects_single_letter(self) -> None:
        """Grammar does not match single letter."""
        results = self.grammar.recognize("U")
        assert len(results) == 0

    def test_rejects_long_string(self) -> None:
        """Grammar does not match strings > 2 chars."""
        results = self.grammar.recognize("United")
        assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "alpha2_recognition"

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("  US  ")
        assert len(results) == 1
        assert results[0].start == 2
        assert results[0].end == 4
        assert results[0].raw_text == "US"
        assert results[0].notation == CountryNotation(shape="alpha2", value="US")


class TestAlpha3Grammar:
    """Tests for Alpha3Grammar."""

    def setup_method(self) -> None:
        self.grammar = Alpha3Grammar()

    def test_recognizes_valid_input(self) -> None:
        """Happy path: grammar finds alpha3 pattern."""
        results = self.grammar.recognize("USA")
        assert len(results) == 1
        assert results[0].notation.shape == "alpha3"
        assert results[0].notation.value == "USA"

    def test_recognizes_lowercase(self) -> None:
        """Edge case: lowercase input is uppercased."""
        results = self.grammar.recognize("gbr")
        assert len(results) == 1
        assert results[0].notation.value == "GBR"

    def test_recognizes_with_whitespace(self) -> None:
        """Edge case: whitespace is trimmed."""
        results = self.grammar.recognize("  USA  ")
        assert len(results) == 1
        assert results[0].notation.value == "USA"

    def test_recognizes_multiple(self) -> None:
        """Input contains multiple alpha3 matches."""
        results = self.grammar.recognize("USA GBR")
        assert len(results) == 2

    def test_rejects_alpha2(self) -> None:
        """Grammar does not match 2-letter codes."""
        results = self.grammar.recognize("US")
        assert len(results) == 0

    def test_rejects_numeric(self) -> None:
        """Grammar does not match digits."""
        results = self.grammar.recognize("123")
        assert len(results) == 0

    def test_rejects_long_string(self) -> None:
        """Grammar does not match strings > 3 chars."""
        results = self.grammar.recognize("United")
        assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "alpha3_recognition"

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("  USA  ")
        assert len(results) == 1
        assert results[0].start == 2
        assert results[0].end == 5
        assert results[0].raw_text == "USA"
        assert results[0].notation == CountryNotation(shape="alpha3", value="USA")


class TestNumericGrammar:
    """Tests for NumericGrammar."""

    def setup_method(self) -> None:
        self.grammar = NumericGrammar()

    def test_recognizes_valid_input(self) -> None:
        """Happy path: grammar finds numeric pattern."""
        results = self.grammar.recognize("840")
        assert len(results) == 1
        assert results[0].notation.shape == "numeric"
        assert results[0].notation.value == "840"

    def test_recognizes_single_digit(self) -> None:
        """Edge case: single digit."""
        results = self.grammar.recognize("4")
        assert len(results) == 1
        assert results[0].notation.value == "4"

    def test_recognizes_two_digits(self) -> None:
        """Edge case: two digits."""
        results = self.grammar.recognize("82")
        assert len(results) == 1
        assert results[0].notation.value == "82"

    def test_recognizes_with_whitespace(self) -> None:
        """Edge case: whitespace is trimmed."""
        results = self.grammar.recognize("  840  ")
        assert len(results) == 1
        assert results[0].notation.value == "840"

    def test_preserves_leading_zeros(self) -> None:
        """Edge case: leading zeros are preserved."""
        results = self.grammar.recognize("004")
        assert len(results) == 1
        assert results[0].notation.value == "004"

    def test_rejects_four_digits(self) -> None:
        """Grammar does not match 4+ digits."""
        results = self.grammar.recognize("1234")
        assert len(results) == 0

    def test_rejects_letters(self) -> None:
        """Grammar does not match letters."""
        results = self.grammar.recognize("abc")
        assert len(results) == 0

    def test_rejects_alphanumeric(self) -> None:
        """Grammar does not match alphanumeric."""
        results = self.grammar.recognize("12a")
        assert len(results) == 0

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "numeric_recognition"

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("  840  ")
        assert len(results) == 1
        assert results[0].start == 2
        assert results[0].end == 5
        assert results[0].raw_text == "840"
        assert results[0].notation == CountryNotation(shape="numeric", value="840")


class TestNameGrammar:
    """Tests for NameGrammar (lookup-table-based recognition)."""

    def setup_method(self) -> None:
        self.grammar = NameGrammar()

    def test_recognizes_full_name(self) -> None:
        """Happy path: grammar recognizes full ISO English name, token preserved."""
        results = self.grammar.recognize("United States")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "United States"

    def test_recognizes_variant(self) -> None:
        """Variant names are recognized, trimmed input token preserved."""
        results = self.grammar.recognize("USA")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "USA"

    def test_recognizes_alpha2_as_name(self) -> None:
        """Alpha-2-like name 'US' is recognized, trimmed input token preserved."""
        results = self.grammar.recognize("US")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "US"

    def test_recognizes_lowercase(self) -> None:
        """Lowercase input still recognized, trimmed input token preserved."""
        results = self.grammar.recognize("canada")
        assert len(results) == 1
        assert results[0].notation.value == "canada"

    def test_recognizes_mixed_case(self) -> None:
        """Mixed case input recognized, trimmed input token preserved."""
        results = self.grammar.recognize("fRAnce")
        assert len(results) == 1
        assert results[0].notation.value == "fRAnce"

    def test_recognizes_with_whitespace(self) -> None:
        """Outer whitespace is trimmed, internal spacing preserved."""
        results = self.grammar.recognize("  United   Kingdom  ")
        assert len(results) == 1
        assert results[0].notation.value == "United   Kingdom"

    def test_recognizes_with_accents(self) -> None:
        """Accented input is recognized, trimmed input token preserved."""
        results = self.grammar.recognize("Côte d'Ivoire")
        assert len(results) == 1
        assert results[0].notation.value == "Côte d'Ivoire"

    def test_recognizes_chinese_name(self) -> None:
        """Chinese names are recognized, trimmed input token preserved."""
        results = self.grammar.recognize("马来西亚")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "马来西亚"

    def test_recognizes_chinese_name_simple(self) -> None:
        """Chinese name '中国' recognized, trimmed input token preserved."""
        results = self.grammar.recognize("中国")
        assert len(results) == 1
        assert results[0].notation.value == "中国"

    def test_recognizes_historical_name(self) -> None:
        """Historical name recognized, trimmed input token preserved."""
        results = self.grammar.recognize("Burma")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "Burma"

    def test_recognizes_spanish_name(self) -> None:
        """Spanish (CLDR) name recognized, trimmed input token preserved."""
        results = self.grammar.recognize("Alemania")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "Alemania"

    def test_recognizes_french_name(self) -> None:
        """French (CLDR) name recognized, trimmed input token preserved."""
        results = self.grammar.recognize("Allemagne")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "Allemagne"

    def test_recognizes_accented_localized_name(self) -> None:
        """Accented Spanish (CLDR) name recognized, trimmed token preserved."""
        results = self.grammar.recognize("États-Unis")
        assert len(results) == 1
        assert results[0].notation.shape == "name"
        assert results[0].notation.value == "États-Unis"

    def test_recognizes_historical_ussr(self) -> None:
        """Historical name 'USSR' recognized, trimmed input token preserved."""
        results = self.grammar.recognize("USSR")
        assert len(results) == 1
        assert results[0].notation.value == "USSR"

    def test_recognizes_synonym_via_english_table(self) -> None:
        """Synonym 'Holland' recognized, trimmed input token preserved."""
        results = self.grammar.recognize("Holland")
        assert len(results) == 1
        assert results[0].notation.value == "Holland"

    def test_recognizes_hyphenated_official_names(self) -> None:
        """Official hyphenated names (Guinea-Bissau, Timor-Leste) are recognized."""
        for text in ("Guinea-Bissau", "Timor-Leste"):
            results = self.grammar.recognize(text)
            assert len(results) == 1
            assert results[0].notation.shape == "name"
            assert results[0].notation.value == text

    def test_recognizes_separator_variants(self) -> None:
        """Hyphen, space, en dash, and slash variants share one recognition key."""
        for text in (
            "Guinea-Bissau",
            "Guinea Bissau",
            "Guinea\u2013Bissau",
            "Guinea/Bissau",
            "Timor-Leste",
            "Timor Leste",
        ):
            results = self.grammar.recognize(text)
            assert len(results) == 1, text
            assert results[0].notation.shape == "name"

    def test_recognizes_france_metropolitan_official_form(self) -> None:
        """Official ISO 3166-3 spelling 'France, Metropolitan' is recognized."""
        results = self.grammar.recognize("France, Metropolitan")
        assert len(results) == 1
        assert results[0].notation.value == "France, Metropolitan"

    def test_recognizes_viet_nam_democratic_republic_official_form(self) -> None:
        """Official ISO 3166-3 spelling is recognized, token preserved."""
        text = "Viet-Nam, Democratic Republic of"
        results = self.grammar.recognize(text)
        assert len(results) == 1
        assert results[0].notation.value == text

    def test_recognizes_yemen_democratic_official_form(self) -> None:
        """Official ISO 3166-3 spelling is recognized, token preserved."""
        text = "Yemen, Democratic"
        results = self.grammar.recognize(text)
        assert len(results) == 1
        assert results[0].notation.value == text

    def test_rejects_numeric(self) -> None:
        """Numeric input is not a name pattern."""
        results = self.grammar.recognize("840")
        assert len(results) == 0

    def test_rejects_unknown_name(self) -> None:
        """Unknown name returns empty list."""
        results = self.grammar.recognize("XYZ")
        assert len(results) == 0

    def test_rejects_gibberish(self) -> None:
        """Gibberish input returns empty list."""
        results = self.grammar.recognize("asdfghjkl")
        assert len(results) == 0

    def test_rejects_partial_name(self) -> None:
        """Partial name not in any table returns empty list."""
        results = self.grammar.recognize("United")
        assert len(results) == 0

    def test_rejects_empty_string(self) -> None:
        """Empty string returns empty list."""
        results = self.grammar.recognize("")
        assert results == []

    def test_rejects_whitespace_only(self) -> None:
        """Whitespace-only input returns empty list."""
        results = self.grammar.recognize("   ")
        assert results == []

    def test_strips_punctuation(self) -> None:
        """Punctuation is stripped for membership, raw token preserved."""
        results = self.grammar.recognize("U.S.A.")
        assert len(results) == 1
        # trailing punctuation is dropped per two-array exact-end (ADR D3 Rev.4)
        assert results[0].notation.value == "U.S.A"
        assert results[0].start == 0
        assert results[0].end == 5
        assert results[0].raw_text == "U.S.A"

    def test_strips_apostrophes(self) -> None:
        """Apostrophes are stripped for membership, raw token preserved."""
        results = self.grammar.recognize("Cote d'Ivoire")
        assert len(results) == 1
        assert results[0].notation.value == "Cote d'Ivoire"

    def test_preserves_english_alias_token(self) -> None:
        """Grammar preserves the trimmed input token for English aliases."""
        results = self.grammar.recognize("USA")
        assert len(results) == 1
        assert results[0].notation == CountryNotation(shape="name", value="USA")

    def test_preserves_localized_token(self) -> None:
        """Grammar preserves the trimmed input token for localized names."""
        results = self.grammar.recognize("马来西亚")
        assert len(results) == 1
        assert results[0].notation == CountryNotation(shape="name", value="马来西亚")

    def test_normalizes_only_for_membership(self) -> None:
        """Normalization decides membership; the trimmed token survives."""
        results = self.grammar.recognize("  Côte d'Ivoire  ")
        assert len(results) == 1
        assert results[0].notation == CountryNotation(
            shape="name", value="Côte d'Ivoire"
        )

    def test_name(self) -> None:
        """Verify grammar name."""
        assert self.grammar.name == "name_recognition"

    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("  United States  ")
        assert len(results) == 1
        assert results[0].start == 2
        assert results[0].end == 15
        assert results[0].raw_text == "United States"
        assert results[0].notation == CountryNotation(
            shape="name", value="United States"
        )

    def test_span_invariant_with_outer_whitespace(self) -> None:
        """Leading/trailing whitespace is trimmed from the span.

        The invariant ``text[start:end] == raw_text`` must hold for
        whitespace-padded input: the match starts after the leading
        whitespace and ends before the trailing whitespace.
        """
        results = self.grammar.recognize("  United States  ")
        assert len(results) == 1
        assert "  United States  "[results[0].start : results[0].end] == (
            results[0].raw_text
        )


class TestNormalizeName:
    """Tests for the shared Country name normalizer."""

    def test_normalize_name_is_syntax_only(self) -> None:
        """Normalizer strips syntax without assigning canonical meaning."""
        assert normalize_name("  Côte d'Ivoire  ") == "COTE DIVOIRE"
        assert normalize_name("马来西亚") == "马来西亚"

    def test_normalize_name_folds_case_and_strips_punctuation(self) -> None:
        """Normalizer uppercases and removes punctuation."""
        assert normalize_name("U.S.A.") == "USA"
        assert normalize_name("Cote d'Ivoire") == "COTE DIVOIRE"

    def test_normalize_name_collapses_and_trims_whitespace(self) -> None:
        """Normalizer collapses internal whitespace and trims outer whitespace."""
        assert normalize_name("  United   Kingdom  ") == "UNITED KINGDOM"

    def test_normalize_name_treats_separators_as_word_boundaries(self) -> None:
        """Hyphen, en dash, and slash become spaces; all variants share a key."""
        assert normalize_name("Guinea-Bissau") == "GUINEA BISSAU"
        assert normalize_name("Guinea\u2013Bissau") == "GUINEA BISSAU"
        assert normalize_name("Guinea/Bissau") == "GUINEA BISSAU"
        assert normalize_name("Guinea Bissau") == "GUINEA BISSAU"
        assert normalize_name("Timor-Leste") == "TIMOR LESTE"
        assert normalize_name("Timor Leste") == "TIMOR LESTE"

    def test_normalize_name_preserves_cjk_and_punctuation_removal(self) -> None:
        """CJK letters survive; other punctuation is still stripped."""
        assert normalize_name("马来西亚") == "马来西亚"
        assert normalize_name("Cote d'Ivoire") == "COTE DIVOIRE"
        assert normalize_name("U.S.A.") == "USA"
