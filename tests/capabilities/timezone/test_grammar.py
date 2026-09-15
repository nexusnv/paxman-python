"""Tests for Timezone recognition grammars (Task 5: name + abbreviation).

Name grammar: lexicon over lowered identifier keys (folded ``casefolded``
view), slash-aware edges (``[\\w/]`` — no mid-path extraction), carve
exclusion (short-caps Links belong to the abbreviation family).
Abbreviation grammar: UPPER-exact lexicon over carved + refusal sets,
WORD guards, no folding.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.Timezone.grammar.timezone_abbreviation_recognition import (
    ABBREVIATION_TOKENS,
    TimezoneAbbreviationGrammar,
)
from paxman.capabilities.Timezone.grammar.timezone_name_recognition import (
    NAME_TOKENS,
    TimezoneNameGrammar,
)
from paxman.capabilities.Timezone.rules.data.abbreviation_map import (
    CARVED_LINKS,
    REFUSAL_SET,
)
from paxman.capabilities.Timezone.rules.data.iana_fixed_zones import (
    IANA_FIXED_ZONES,
)
from paxman.capabilities.Timezone.rules.data.iana_zone_identifiers import (
    IANA_ZONE_IDENTIFIERS,
)
from paxman.capabilities.Timezone.rules.data.iana_zone_links import (
    IANA_ZONE_LINKS,
)


@pytest.mark.capability
class TestTimezoneNameGrammarIdentity:
    def setup_method(self) -> None:
        self.grammar = TimezoneNameGrammar()

    def test_name(self) -> None:
        assert self.grammar.name == "timezone_name_recognition"

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "timezone_name"

    def test_single_value(self) -> None:
        assert self.grammar.single_value is True


@pytest.mark.capability
class TestTimezoneNameRecognition:
    """Research §8 rows 1-2, 5, 14, 16 + span checks + glued negatives."""

    def setup_method(self) -> None:
        self.grammar = TimezoneNameGrammar()

    def test_canonical_key_exact_span(self) -> None:
        (match,) = self.grammar.recognize("America/New_York")
        assert (match.start, match.end) == (0, 16)
        assert match.raw_text == "America/New_York"
        assert match.notation.key == "America/New_York"
        assert match.notation.family == "name"
        assert match.notation.compact == "America/New_York"

    def test_legacy_link_span(self) -> None:
        (match,) = self.grammar.recognize("US/Eastern")
        assert (match.start, match.end) == (0, 10)
        assert match.raw_text == "US/Eastern"
        assert match.notation.family == "name"

    @pytest.mark.parametrize(
        ("text", "span"),
        [
            ("Canada/Eastern", (0, 14)),
            ("US/PACIFIC", (0, 10)),
            ("Etc/GMT-8", (0, 9)),
        ],
    )
    def test_wave2_link_span(self, text: str, span: tuple[int, int]) -> None:
        """Wave-2 first cut (#170): new links/fixed zone claimed whole."""
        (match,) = self.grammar.recognize(text)
        assert (match.start, match.end) == span
        assert match.raw_text == text
        assert match.notation.family == "name"

    def test_lowercase_fold_claims_span(self) -> None:
        (match,) = self.grammar.recognize("america/new_york")
        assert (match.start, match.end) == (0, 16)
        assert match.raw_text == "america/new_york"
        assert match.notation.key == "america/new_york"

    def test_uppercase_fold_claims_span(self) -> None:
        (match,) = self.grammar.recognize("AMERICA/NEW_YORK")
        assert (match.start, match.end) == (0, 16)
        assert match.raw_text == "AMERICA/NEW_YORK"

    def test_etc_fixed_zone_solely_key(self) -> None:
        """Etc/GMT+5 is claimed whole by the name grammar (sign kept as
        authored); the UtcOffset grammar must claim nothing inside it."""
        (match,) = self.grammar.recognize("Etc/GMT+5")
        assert (match.start, match.end) == (0, 9)
        assert match.raw_text == "Etc/GMT+5"

    def test_bare_utc_fixed_zone(self) -> None:
        (match,) = self.grammar.recognize("UTC")
        assert (match.start, match.end) == (0, 3)
        assert match.notation.family == "name"

    def test_bare_gmt_fixed_zone(self) -> None:
        (match,) = self.grammar.recognize("GMT")
        assert (match.start, match.end) == (0, 3)
        assert match.notation.family == "name"

    def test_offset_continuation_no_prefix_fallback(self) -> None:
        """Etc/GMT+5X must not fall back to the Etc/GMT prefix (#162 family)."""
        assert self.grammar.recognize("Etc/GMT+5X") == []
        assert self.grammar.recognize("Etc/GMT-8X") == []

    def test_embedded_link_sentence_span(self) -> None:
        (match,) = self.grammar.recognize("visit US/Eastern tomorrow")
        assert (match.start, match.end) == (6, 16)
        assert match.raw_text == "US/Eastern"

    def test_trailing_annotation_span_covers_key_only(self) -> None:
        (match,) = self.grammar.recognize("America/New_York (EDT)")
        assert (match.start, match.end) == (0, 16)

    def test_glued_left_missing(self) -> None:
        assert self.grammar.recognize("XUS/Eastern") == []

    def test_glued_right_missing(self) -> None:
        assert self.grammar.recognize("US/EasternX") == []

    def test_zoneinfo_path_missing(self) -> None:
        assert self.grammar.recognize("/usr/share/zoneinfo/America/New_York") == []

    def test_space_for_underscore_rejected(self) -> None:
        assert self.grammar.recognize("America/New York") == []

    def test_windows_name_missing(self) -> None:
        assert self.grammar.recognize("Eastern Standard Time") == []

    def test_two_mentions_both_claimed(self) -> None:
        """Grammar claims both spans; single_value enforcement (AMBIGUOUS)
        is the engine's job."""
        matches = self.grammar.recognize("US/Eastern then America/Chicago")
        assert [(m.start, m.end) for m in matches] == [(0, 10), (16, 31)]

    def test_empty_and_blank_missing(self) -> None:
        assert self.grammar.recognize("") == []
        assert self.grammar.recognize("   ") == []

    @pytest.mark.parametrize("token", ["EST", "CET", "MST", "HST"])
    def test_carved_short_caps_missing_in_name(self, token: str) -> None:
        """Carve rule: short-caps backward Links are abbreviation-family
        tokens; the name lexicon must not claim them."""
        assert self.grammar.recognize(token) == []

    @pytest.mark.parametrize(
        "token", ["EST5EDT", "est5edt", "CST6CDT", "MST7MDT", "PST8PDT"]
    )
    def test_systemv_tokens_claimed_as_shape(self, token: str) -> None:
        """SystemV Zones are claimed here (shape); the rule gates them
        (default INVALID, +flag SUCCESS)."""
        (match,) = self.grammar.recognize(token)
        assert (match.start, match.end) == (0, len(token))
        assert match.raw_text == token
        assert match.notation.family == "name"

    def test_name_tokens_match_authority_tables(self) -> None:
        """Grammar token set is exactly lowered(identifiers | link sources
        | fixed zones) minus carved Links, plus the SystemV Zones (claimed
        for shape; the rule gates them) — keys only, no mapping."""
        expected = (
            {k.lower() for k in IANA_ZONE_IDENTIFIERS}
            | set(IANA_ZONE_LINKS)
            | {k.lower() for k in IANA_FIXED_ZONES}
            | {"est5edt", "cst6cdt", "mst7mdt", "pst8pdt"}
        ) - {c.lower() for c in CARVED_LINKS}
        assert expected == NAME_TOKENS

    def test_carve_exclusion_over_token_set(self) -> None:
        for carved in ("est", "mst", "hst", "cet"):
            assert carved not in NAME_TOKENS


@pytest.mark.capability
class TestTimezoneAbbreviationGrammarIdentity:
    def setup_method(self) -> None:
        self.grammar = TimezoneAbbreviationGrammar()

    def test_name(self) -> None:
        assert self.grammar.name == "timezone_abbreviation_recognition"

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "timezone_abbreviation"

    def test_single_value(self) -> None:
        assert self.grammar.single_value is True


@pytest.mark.capability
class TestTimezoneAbbreviationRecognition:
    """Research §8 rows 9-10, 14 + span checks + glued negatives."""

    def setup_method(self) -> None:
        self.grammar = TimezoneAbbreviationGrammar()

    @pytest.mark.parametrize("token", ["EST", "MST", "HST", "CET", "IST", "CST", "PST"])
    def test_curated_tokens_claimed_with_spans(self, token: str) -> None:
        (match,) = self.grammar.recognize(token)
        assert (match.start, match.end) == (0, len(token))
        assert match.raw_text == token
        assert match.notation.key == token
        assert match.notation.family == "abbreviation"
        assert match.notation.compact == token

    def test_embedded_abbreviation_span(self) -> None:
        (match,) = self.grammar.recognize("arrive CET tomorrow")
        assert (match.start, match.end) == (7, 10)
        assert match.raw_text == "CET"

    def test_quoted_abbreviation_span_excludes_quotes(self) -> None:
        (match,) = self.grammar.recognize('"CET"')
        assert (match.start, match.end) == (1, 4)

    def test_glued_word_missing(self) -> None:
        assert self.grammar.recognize("ESTIMATE") == []

    def test_glued_left_missing(self) -> None:
        assert self.grammar.recognize("XEST") == []

    @pytest.mark.parametrize("token", ["est", "Est", "cet"])
    def test_case_exact_lowercase_missing(self, token: str) -> None:
        assert self.grammar.recognize(token) == []

    @pytest.mark.parametrize("token", ["XYZ", "JST", "ABC"])
    def test_unlisted_missing(self, token: str) -> None:
        assert self.grammar.recognize(token) == []

    @pytest.mark.parametrize("token", ["UTC", "GMT"])
    def test_fixed_zones_not_abbreviations(self, token: str) -> None:
        """UTC/GMT are zone-defined fixed zones, exempt from the carve —
        the abbreviation lexicon must not claim them."""
        assert self.grammar.recognize(token) == []

    def test_abbreviation_tokens_match_authority_tables(self) -> None:
        expected = {t.upper() for t in (CARVED_LINKS | REFUSAL_SET)}
        assert expected == ABBREVIATION_TOKENS

    def test_empty_missing(self) -> None:
        assert self.grammar.recognize("") == []
