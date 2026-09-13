"""Tests for Language recognition grammars — 3 PipelineGrammars."""

import pytest

from paxman.capabilities.Language.contract import LanguageContract
from paxman.capabilities.Language.grammar.bcp47_tag_recognition import (
    BCP47TagGrammar,
)
from paxman.capabilities.Language.grammar.data.english_names import (
    ENGLISH_LANGUAGE_KEYS,
)
from paxman.capabilities.Language.grammar.language_code_recognition import (
    LanguageCodeGrammar,
)
from paxman.capabilities.Language.grammar.language_description_recognition import (
    LanguageDescriptionGrammar,
)
from paxman.capabilities.Language.grammar.language_name_recognition import (
    LanguageNameGrammar,
)
from paxman.capabilities.Language.rules.data.description_display_map import (
    DESCRIPTION_DISPLAY_MAP,
)
from paxman.capabilities.Language.rules.data.english_language_map import (
    NAME_TO_CANONICAL,
)
from paxman.capabilities.Language.rules.iana_language_subtag_registry_ed2026 import (
    SectionIANARegistryDescription,
)

pytestmark = [pytest.mark.capability]

# ---------------------------------------------------------------------------
# BCP47 Tag Recognition
# ---------------------------------------------------------------------------


class TestBCP47TagGrammar:
    def setup_method(self) -> None:
        self.grammar = BCP47TagGrammar()

    def test_semantics_and_name(self) -> None:
        assert self.grammar.name == "bcp47_tag_recognition"
        assert self.grammar.semantics == "bcp47_tag"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_valid_simple_en(self) -> None:
        # Bare "en" is language_code domain, not BCP47 (requires hyphen).
        # BCP47 must not match bare.
        results = self.grammar.recognize("en")
        assert len(results) == 0

    def test_valid_zh_hans_cn(self) -> None:
        results = self.grammar.recognize("zh-Hans-CN")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 10
        assert results[0].raw_text == "zh-Hans-CN"
        assert results[0].notation.language == "zh"
        assert results[0].notation.script == "Hans"
        assert results[0].notation.region == "CN"
        assert results[0].notation.compact == "zh-Hans-CN"

    def test_valid_en_us_mixed_case(self) -> None:
        results = self.grammar.recognize("EN-us")
        assert len(results) == 1
        assert results[0].notation.language == "en"
        assert results[0].notation.region == "US"
        assert results[0].notation.compact == "en-US"
        assert results[0].raw_text == "EN-us"

    def test_underscore_span_invariant(self) -> None:
        results = self.grammar.recognize("fr_FR")
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 5
        assert results[0].raw_text == "fr_FR"
        assert results[0].notation.compact == "fr-FR"
        assert results[0].notation.language == "fr"
        assert results[0].notation.region == "FR"

    def test_underscore_zh_hans_cn(self) -> None:
        results = self.grammar.recognize("zh_Hans_CN")
        assert len(results) == 1
        assert results[0].raw_text == "zh_Hans_CN"
        assert results[0].notation.compact == "zh-Hans-CN"
        assert results[0].notation.language == "zh"
        assert results[0].notation.script == "Hans"
        assert results[0].notation.region == "CN"

    def test_multiple_matches(self) -> None:
        # Bare "en" not BCP47, only fr-FR matches
        results = self.grammar.recognize("en fr-FR")
        assert len(results) == 1
        assert results[0].raw_text == "fr-FR"

    def test_quoted_bracketed(self) -> None:
        for txt in ('"en-US"', "[fr-FR]"):
            # extract at least one mention — quoted/bracketed hyphenated tags
            # still find span
            results = self.grammar.recognize(txt)
            assert len(results) >= 1, f"failed for {txt!r}: {results}"
        # Bare codes like "(de)" are not BCP47 domain
        assert self.grammar.recognize("(de)") == []
        assert self.grammar.recognize('<html lang="en">') == []

    def test_boundary_guard_rejects_glue(self) -> None:
        # enUS glued without hyphen should not be recognized as bcp47 tag
        assert self.grammar.recognize("enUS") == []

    def test_boundary_guard_word_only(self) -> None:
        # word_only: "en" inside "Xenon" should not produce "en" as separate tag
        results = self.grammar.recognize("Xenon")
        # Xenon is 5 letters (5-8 language subtag), but should not carve "en"
        for r in results:
            assert r.raw_text.lower() != "en"

    def test_empty_and_whitespace(self) -> None:
        assert self.grammar.recognize("") == []
        assert self.grammar.recognize("   ") == []

    def test_span_invariant_with_surrounding(self) -> None:
        txt = "lang: fr-FR here"
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        m = results[0]
        assert txt[m.start : m.end] == m.raw_text
        assert m.start == txt.index("fr-FR")
        assert m.end == m.start + len("fr-FR")

    def test_variant_sl_nedis(self) -> None:
        results = self.grammar.recognize("sl-nedis")
        assert len(results) == 1
        assert results[0].notation.language == "sl"
        assert results[0].notation.variant == "nedis"
        assert results[0].notation.compact == "sl-nedis"

    def test_script_region_case_canonical(self) -> None:
        results = self.grammar.recognize("ZH-HANS-CN")
        assert len(results) == 1
        assert results[0].notation.compact == "zh-Hans-CN"

    def test_privateuse(self) -> None:
        results = self.grammar.recognize("x-private")
        assert len(results) == 1
        assert results[0].notation.privateuse == "x-private"
        assert results[0].notation.compact == "x-private"

    def test_grandfathered(self) -> None:
        results = self.grammar.recognize("i-cherokee")
        assert len(results) == 1
        assert results[0].notation.grandfathered == "i-cherokee"
        assert results[0].notation.compact == "i-cherokee"

    def test_region_numeric(self) -> None:
        results = self.grammar.recognize("es-419")
        assert len(results) == 1
        assert results[0].notation.language == "es"
        assert results[0].notation.region == "419"
        assert results[0].notation.compact == "es-419"


# ---------------------------------------------------------------------------
# Language Code Recognition
# ---------------------------------------------------------------------------


class TestLanguageCodeGrammar:
    def setup_method(self) -> None:
        self.grammar = LanguageCodeGrammar()

    def test_semantics_and_name(self) -> None:
        assert self.grammar.name == "language_code_recognition"
        assert self.grammar.semantics == "language_code"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_valid_2_letters(self) -> None:
        results = self.grammar.recognize("en")
        assert len(results) == 1
        assert results[0].notation.language == "en"
        assert results[0].notation.compact == "en"
        assert results[0].raw_text == "en"

    def test_valid_3_letters(self) -> None:
        results = self.grammar.recognize("eng")
        assert len(results) == 1
        assert results[0].notation.language == "eng"
        assert results[0].notation.compact == "eng"

    def test_valid_5_8_letters(self) -> None:
        for code in ("cherokee", "bihari"):
            results = self.grammar.recognize(code)
            assert len(results) == 1, code
            assert results[0].notation.language == code
            assert results[0].notation.compact == code

    def test_lowercase_folding(self) -> None:
        results = self.grammar.recognize("EN")
        assert len(results) == 1
        assert results[0].notation.language == "en"
        assert results[0].notation.compact == "en"

    def test_multiple_matches(self) -> None:
        results = self.grammar.recognize("en fr de")
        assert len(results) == 3

    def test_boundary_guard_rejects_4_letters(self) -> None:
        # 4 letters is neither 2-3 nor 5-8 -> MISSING
        assert self.grammar.recognize("enUS") == []
        assert self.grammar.recognize("abcd") == []

    def test_boundary_guard_word_only(self) -> None:
        # glued inside longer token should not carve
        results = self.grammar.recognize("Xenon")
        # "Xenon" is 5 letters -> it IS 5-8, so grammar will match "Xenon" itself
        # but "en" inside "Xenon" should not be separate
        # we check that we don't get "en" as separate match inside Xenon
        for r in results:
            assert r.start == 0 and r.end == 5  # whole word only
        # prefix glue
        assert self.grammar.recognize("Xen") != []  # 3 letters isolated -> should match
        # but glued word "enUS" is 4 letters -> no match
        assert self.grammar.recognize("enUS") == []

    def test_empty(self) -> None:
        assert self.grammar.recognize("") == []

    def test_span_invariant(self) -> None:
        txt = "code en here"
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        assert txt[results[0].start : results[0].end] == results[0].raw_text

    def test_quoted(self) -> None:
        results = self.grammar.recognize('"en"')
        assert len(results) == 1
        assert results[0].raw_text == "en"


# ---------------------------------------------------------------------------
# Language Name Recognition
# ---------------------------------------------------------------------------


class TestLanguageNameGrammar:
    def setup_method(self) -> None:
        self.grammar = LanguageNameGrammar()

    def test_semantics_and_name(self) -> None:
        assert self.grammar.name == "language_name_recognition"
        assert self.grammar.semantics == "language_name"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_valid_german(self) -> None:
        results = self.grammar.recognize("German")
        assert len(results) == 1
        assert results[0].raw_text == "German"
        # compact lower
        assert results[0].notation.compact == "german"

    def test_case_insensitive(self) -> None:
        for variant in ("GERMAN", "german", "GeRmAn"):
            results = self.grammar.recognize(variant)
            assert len(results) == 1, variant
            assert results[0].raw_text == variant

    def test_normalized_case_insensitive_via_nfkd(self) -> None:
        # normalize_name handles accents, but stub keys are ascii -> test serbo croatian
        results = self.grammar.recognize("Serbo Croatian")
        assert len(results) == 1
        assert results[0].notation.compact == "serbo croatian"

    def test_with_outer_whitespace(self) -> None:
        results = self.grammar.recognize("  German  ")
        assert len(results) == 1
        assert results[0].start == 2
        assert results[0].end == 8
        assert results[0].raw_text == "German"

    def test_rejects_unknown(self) -> None:
        assert self.grammar.recognize("Klingonish") == []
        assert self.grammar.recognize("XYZ") == []

    def test_empty(self) -> None:
        assert self.grammar.recognize("") == []
        assert self.grammar.recognize("   ") == []

    def test_span_invariant(self) -> None:
        txt = "  German  "
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        assert txt[results[0].start : results[0].end] == results[0].raw_text

    def test_multiple_via_single_value(self) -> None:
        # WholeInputLookup is single_value but whole input only one match;
        # multiple names in one string should be MISSING (not lexicon multi)
        assert self.grammar.recognize("German French") == []

    def test_lexicon_keys(self) -> None:
        # spot check stub keys
        for name in ("english", "french", "cherokee", "yiddish"):
            assert self.grammar.recognize(name) != []
            assert self.grammar.recognize(name.upper()) != []


# ---------------------------------------------------------------------------
# Language Description Recognition (compositional phrases)
# ---------------------------------------------------------------------------


class TestLanguageDescriptionGrammar:
    def setup_method(self) -> None:
        self.grammar = LanguageDescriptionGrammar()

    def test_semantics_and_name(self) -> None:
        assert self.grammar.name == "language_description_recognition"
        assert self.grammar.semantics == "language_description"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_region_language_script_form(self) -> None:
        txt = "Singapore Chinese in traditional script"
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        m = results[0]
        assert m.start == 0
        assert m.end == 39
        assert m.raw_text == txt
        assert m.notation.language == "chinese"
        assert m.notation.script == "traditional"
        assert m.notation.region == "singapore"
        assert m.notation.compact == "chinese-traditional-singapore"
        assert m.notation.raw_value == txt.lower()

    def test_language_script_form(self) -> None:
        txt = "Chinese in simplified script"
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        m = results[0]
        assert m.start == 0
        assert m.end == 28
        assert m.raw_text == txt
        assert m.notation.language == "chinese"
        assert m.notation.script == "simplified"
        assert m.notation.region == ""
        assert m.notation.compact == "chinese-simplified"
        assert m.notation.raw_value == txt.lower()

    def test_language_region_form(self) -> None:
        txt = "Chinese in Singapore"
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        m = results[0]
        assert m.start == 0
        assert m.end == 20
        assert m.raw_text == txt
        assert m.notation.language == "chinese"
        assert m.notation.script == ""
        assert m.notation.region == "singapore"
        assert m.notation.compact == "chinese-singapore"
        assert m.notation.raw_value == txt.lower()

    def test_trailing_script_word_optional(self) -> None:
        for txt, compact, script in (
            ("Chinese in traditional", "chinese-traditional", "traditional"),
            (
                "Singapore Chinese in traditional",
                "chinese-traditional-singapore",
                "traditional",
            ),
        ):
            results = self.grammar.recognize(txt)
            assert len(results) == 1, txt
            assert results[0].raw_text == txt
            assert results[0].notation.script == script
            assert results[0].notation.compact == compact

    def test_case_insensitive(self) -> None:
        results = self.grammar.recognize("CHINESE IN SINGAPORE")
        assert len(results) == 1
        assert results[0].raw_text == "CHINESE IN SINGAPORE"
        assert results[0].notation.language == "chinese"
        assert results[0].notation.region == "singapore"
        assert results[0].notation.compact == "chinese-singapore"

    def test_span_invariant_with_surrounding(self) -> None:
        txt = "say Singapore Chinese in traditional script ok"
        results = self.grammar.recognize(txt)
        assert len(results) == 1
        m = results[0]
        assert txt[m.start : m.end] == m.raw_text
        assert m.raw_text == "Singapore Chinese in traditional script"
        assert m.start == txt.index("Singapore Chinese in traditional script")
        assert m.end == m.start + len("Singapore Chinese in traditional script")

    def test_negative_xenon_sentence(self) -> None:
        assert self.grammar.recognize("Xenon is a gas") == []

    def test_negative_bare_in(self) -> None:
        assert self.grammar.recognize("in") == []

    def test_negative_lone_language(self) -> None:
        assert self.grammar.recognize("Chinese") == []

    def test_negative_bare_display_words(self) -> None:
        # Full-phrase spans only — never bare-word spans.
        assert self.grammar.recognize("traditional") == []
        assert self.grammar.recognize("Singapore") == []
        assert self.grammar.recognize("script") == []

    def test_negative_missing_slot(self) -> None:
        assert self.grammar.recognize("Chinese in") == []
        assert self.grammar.recognize("in Singapore") == []

    def test_negative_glued_tokens(self) -> None:
        # Phrase tokens must be whitespace-separated words.
        assert self.grammar.recognize("Chinese2 in Singapore") == []
        assert self.grammar.recognize("Chinese-in-Singapore") == []

    def test_empty_and_whitespace(self) -> None:
        assert self.grammar.recognize("") == []
        assert self.grammar.recognize("   ") == []


class TestDescriptionDisplayFields:
    """Grammar emits display slots; the description rule maps them.

    Test-only cross-import (the grammar itself never imports rule data):
    display emission here must round-trip through
    ``SectionIANARegistryDescription`` to the canonical tag.
    """

    def setup_method(self) -> None:
        self.grammar = LanguageDescriptionGrammar()
        self.rule = SectionIANARegistryDescription()
        self.contract = LanguageContract()
        self.english_keys = ENGLISH_LANGUAGE_KEYS
        self.display_map = DESCRIPTION_DISPLAY_MAP
        self.name_to_canonical = NAME_TO_CANONICAL

    def test_every_english_key_composes_with_region(self) -> None:
        for key in sorted(self.english_keys):
            phrase = f"{key} in Singapore"
            matches = self.grammar.recognize(phrase)
            assert len(matches) == 1, phrase
            assert matches[0].notation.language == key, phrase
            assert matches[0].notation.region == "singapore", phrase
            assert matches[0].notation.compact == f"{key}-singapore", phrase
            expected = self.name_to_canonical[key]
            assert (
                self.rule.normalize(matches[0].notation, self.contract)
                == f"{expected}-SG"
            ), phrase

    def test_script_slots_are_display_valued(self) -> None:
        for phrase, display_key in (
            ("Chinese in traditional script", "traditional"),
            ("Chinese in simplified script", "simplified"),
        ):
            matches = self.grammar.recognize(phrase)
            assert len(matches) == 1, phrase
            assert matches[0].notation.script == display_key, phrase
            assert (
                self.rule.normalize(matches[0].notation, self.contract)
                == f"zh-{self.display_map[display_key]}"
            ), phrase


class TestDescriptionTrailingNounGuard:
    """Bare slots must not swallow a following content word (thermo HIGH-1)."""

    def setup_method(self) -> None:
        self.grammar = LanguageDescriptionGrammar()

    def test_bare_script_trailing_noun_rejected(self) -> None:
        assert self.grammar.recognize("Chinese in traditional dress") == []

    def test_bare_region_trailing_noun_rejected(self) -> None:
        assert self.grammar.recognize("Chinese in Singapore restaurants") == []

    def test_bare_script_connector_allowed(self) -> None:
        results = self.grammar.recognize("Chinese in traditional and simplified")
        assert len(results) == 1
        assert results[0].notation.script == "traditional"

    def test_closed_script_trailing_filler_allowed(self) -> None:
        results = self.grammar.recognize("Chinese in traditional script daily")
        assert len(results) == 1
        assert results[0].raw_text == "Chinese in traditional script"


class TestDescriptionOuterGlue:
    """Phrase edges must be word-bounded (coderabbit PR #153)."""

    def setup_method(self) -> None:
        self.grammar = LanguageDescriptionGrammar()

    def test_prefix_glue_rejected(self) -> None:
        assert self.grammar.recognize("2Chinese in Singapore") == []
        assert self.grammar.recognize("_Chinese in Singapore") == []

    def test_suffix_glue_rejected(self) -> None:
        assert self.grammar.recognize("Chinese in Singapore2") == []
        assert self.grammar.recognize("Chinese in Singapore_") == []

    def test_spaced_digits_still_recognized(self) -> None:
        assert len(self.grammar.recognize("2 Chinese in Singapore")) == 1
        assert len(self.grammar.recognize("Chinese in Singapore 2")) == 1
