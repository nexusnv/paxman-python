"""Tests for ISIN recognition grammar."""

import pytest

from paxman.capabilities.ISIN.grammar.isin_recognition import (
    ISINRecognition,
    ISINRecognitionGrammar,
)

pytestmark = [pytest.mark.capability]

GRAMMAR = ISINRecognitionGrammar()


def test_compact_span() -> None:
    m = GRAMMAR.recognize("US0378331005")
    assert len(m) == 1
    assert m[0].raw_text == "US0378331005"
    assert (m[0].start, m[0].end) == (0, 12)
    assert m[0].end - m[0].start == len(m[0].raw_text)
    n = m[0].notation
    assert n.country_code == "US"
    assert n.nsin == "037833100"
    assert n.check_digit == "5"
    assert n.compact == "US0378331005"


def test_lowercase_fold() -> None:
    m = GRAMMAR.recognize("us0378331005")
    assert len(m) == 1
    assert m[0].notation.compact == "US0378331005"
    assert m[0].notation.country_code == "US"


def test_spaced_groupings() -> None:
    for txt, expected in [
        ("US 037833 100 5", "US0378331005"),
        ("US037833 1005", "US0378331005"),
        ("PL0000 503132", "PL0000503132"),
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        assert m[0].notation.compact == expected, txt
        assert (m[0].start, m[0].end) == (0, len(txt)), txt
        assert m[0].raw_text == txt, txt


def test_outer_whitespace() -> None:
    m = GRAMMAR.recognize("  US0378331005  ")
    assert len(m) == 1
    assert (m[0].start, m[0].end) == (2, 14)
    assert m[0].raw_text == "US0378331005"
    assert m[0].notation.compact == "US0378331005"


def test_label_variants() -> None:
    for txt in [
        "ISIN: US0378331005",
        "ISIN US0378331005",
        "isin - us0378331005",
        "ISIN-US0378331005",
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        # Span includes the label; compact is bare.
        assert (m[0].start, m[0].end) == (0, len(txt)), txt
        assert m[0].raw_text == txt, txt
        assert m[0].notation.compact == "US0378331005", txt


def test_quoted_bracketed() -> None:
    for txt, expected in [
        ('"US0378331005"', "US0378331005"),
        ("(US0378331005)", "US0378331005"),
        ("[GB0002634946]", "GB0002634946"),
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        assert m[0].notation.compact == expected, txt
        assert m[0].raw_text == expected, txt
        assert m[0].end - m[0].start == len(expected), txt


def test_glued_label_missing() -> None:
    assert GRAMMAR.recognize("ISINUS0378331005") == []


def test_iceland_lookalike() -> None:
    # IS + digit-led NSIN is Iceland, not a glued "ISIN" label — recognized.
    m = GRAMMAR.recognize("IS0000000008")
    assert len(m) == 1
    assert m[0].notation.compact == "IS0000000008"
    assert m[0].notation.country_code == "IS"


def test_hyphen_missing() -> None:
    assert GRAMMAR.recognize("US037833-1005") == []
    assert GRAMMAR.recognize("US-0378331005") == []


def test_11_13_missing() -> None:
    assert GRAMMAR.recognize("US037833100") == []  # 11
    assert GRAMMAR.recognize("US03783310055") == []  # 13


def test_letter_check_missing() -> None:
    assert GRAMMAR.recognize("US037833100A") == []


def test_glued_runs_missing() -> None:
    assert GRAMMAR.recognize("XUS0378331005") == []
    assert GRAMMAR.recognize("US0378331005Y") == []


def test_homoglyph_missing() -> None:
    assert GRAMMAR.recognize("\uff35\uff33" + "0378331005") == []  # fullwidth US
    assert GRAMMAR.recognize("US037833100" + "\uff15") == []  # fullwidth check


def test_name_semantics_single_value() -> None:
    assert GRAMMAR.name == "isin_recognition"
    assert GRAMMAR.semantics == "isin_recognition"
    assert GRAMMAR.single_value is True
    # Scaffolder/capability seam: ISINRecognition stays a valid alias.
    assert ISINRecognition is ISINRecognitionGrammar
