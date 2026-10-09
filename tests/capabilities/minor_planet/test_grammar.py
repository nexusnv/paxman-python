"""Tests for MinorPlanet recognition grammar."""

import re

import pytest

from paxman.capabilities.MinorPlanet.grammar.minor_planet_recognition import (
    MinorPlanetRecognitionGrammar,
)
from paxman.core.domain import Grammar


@pytest.mark.capability
class TestMinorPlanetRecognition:
    """Grammar: minor_planet_recognition."""

    def setup_method(self) -> None:
        self.grammar: Grammar = MinorPlanetRecognitionGrammar()

    def test_semantics(self) -> None:
        assert self.grammar.semantics == "minor_planet_recognition"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_name(self) -> None:
        assert self.grammar.name == "minor_planet_recognition"

    def test_pattern_compiles(self) -> None:
        from paxman.capabilities.MinorPlanet.grammar import (
            minor_planet_recognition as mod,
        )

        re.compile(mod._MP_PATTERN, re.ASCII)

    @pytest.mark.parametrize(
        "text,designation,form",
        [
            ("1995 XA", "1995 XA", "provisional"),
            ("2007 TA418", "2007 TA418", "provisional"),
            ("1992 QB1", "1992 QB1", "provisional"),
            ("2003 cp20", "2003 CP20", "provisional"),
            ("1995 xa", "1995 XA", "provisional"),
            ("1995_XA", "1995 XA", "provisional"),
            ("A904 OA", "A904 OA", "provisional"),
            ("A/2017 U1", "A/2017 U1", "provisional"),
            ("J95X00A", "J95X00A", "packed"),
            ("K07Tf8A", "K07Tf8A", "packed"),
            ("K99AJ3Z", "K99AJ3Z", "packed"),
            ("_QC0000", "_QC0000", "extended"),
            ("2040 P-L", "2040 P-L", "survey"),
            ("3138 T-1", "3138 T-1", "survey"),
            ("PLS2040", "PLS2040", "survey_packed"),
            ("T1S3138", "T1S3138", "survey_packed"),
            ("(433)", "(433)", "number"),
            ("(274301)", "(274301)", "number"),
            ("(15396335)", "(15396335)", "number"),
            ("03202", "03202", "packed_number"),
            ("A0345", "A0345", "packed_number"),
            ("a0017", "a0017", "packed_number"),
            ("K3289", "K3289", "packed_number"),
            ("~000z", "~000z", "packed_number"),
            ("~AZaz", "~AZaz", "packed_number"),
        ],
    )
    def test_recognize_lanes(self, text: str, designation: str, form: str) -> None:
        matches = self.grammar.recognize(text)
        assert len(matches) == 1
        assert matches[0].notation.designation == designation
        assert matches[0].notation.form == form
        assert matches[0].raw_text == text
        assert matches[0].end - matches[0].start == len(text)

    def test_trailing_name_outside_span(self) -> None:
        matches = self.grammar.recognize("(433) Eros")
        assert len(matches) == 1
        assert matches[0].raw_text == "(433)"
        assert matches[0].notation.designation == "(433)"

    def test_equation_two_mentions(self) -> None:
        matches = self.grammar.recognize("1997 RO4 = 2007 FK34")
        assert len(matches) == 2

    @pytest.mark.parametrize(
        "text",
        [
            "1995XA",
            "433",
            "1892 A",
            "C/1995 O1",
            "Eros",
            "1995 SA₁",
            "199 XA",
            "19955 XA",
            "J95X00",
        ],
    )
    def test_negatives(self, text: str) -> None:
        assert self.grammar.recognize(text) == []

    def test_glued_lowercase_missing(self) -> None:
        assert self.grammar.recognize("2003cp20") == []

    def test_phone_area_code_overclaim_documented(self) -> None:
        # Known v1 overclaim (research §4.4): area codes match the number
        # lane; the future registry disambiguates. Caller segments phones.
        matches = self.grammar.recognize("(555) 123-4567")
        assert len(matches) == 1
        assert matches[0].raw_text == "(555)"

    def test_bare_five_digit_overclaim_documented(self) -> None:
        # Known v1 overclaim: ZIP/price runs match packed_number lane.
        matches = self.grammar.recognize("03202")
        assert len(matches) == 1
        assert matches[0].notation.form == "packed_number"
