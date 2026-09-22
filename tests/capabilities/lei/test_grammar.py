"""Tests for LEI recognition grammar — TDD per plan Task 3."""

import pytest

from paxman.capabilities.LEI.grammar.lei_recognition import (
    LEIRecognition,
    LEIRecognitionGrammar,
)

pytestmark = [pytest.mark.capability]

GRAMMAR = LEIRecognitionGrammar()

VALID = "213800KUD8LAJWSQ9D15"
OTHER = "5493000IBP32UQZ0KL24"


def test_compact_span() -> None:
    m = GRAMMAR.recognize(VALID)
    assert len(m) == 1
    assert m[0].raw_text == VALID
    assert (m[0].start, m[0].end) == (0, 20)
    assert m[0].end - m[0].start == len(m[0].raw_text)
    n = m[0].notation
    assert n.lou_prefix == "2138"
    assert n.entity_block == "00KUD8LAJWSQ9D"
    assert n.check_digits == "15"
    assert n.compact == VALID


def test_lowercase_fold() -> None:
    m = GRAMMAR.recognize("5493000ibp32uqz0kl24")
    assert len(m) == 1
    assert m[0].notation.compact == OTHER
    assert m[0].notation.lou_prefix == "5493"
    m2 = GRAMMAR.recognize("7ltwfzyicnsx8d621k86")
    assert len(m2) == 1
    assert m2[0].notation.compact == "7LTWFZYICNSX8D621K86"


def test_single_spaced() -> None:
    for txt, expected in [
        ("5493 000IBP32UQZ0KL24", OTHER),
        ("2138 00KU D8LA JWSQ 9D15", VALID),
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        assert m[0].notation.compact == expected, txt
        assert (m[0].start, m[0].end) == (0, len(txt)), txt
        assert m[0].raw_text == txt, txt


def test_outer_whitespace() -> None:
    m = GRAMMAR.recognize(f"  {VALID}  ")
    assert len(m) == 1
    assert (m[0].start, m[0].end) == (2, 22)
    assert m[0].raw_text == VALID
    assert m[0].notation.compact == VALID


def test_label_variants() -> None:
    for txt in [
        f"LEI: {VALID}",
        f"lei {VALID}",
        f"LEI-{VALID}",
        f"LEI:{VALID}",
        f"LEI {OTHER}",
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        # Span includes the label; compact is bare.
        assert (m[0].start, m[0].end) == (0, len(txt)), txt
        assert m[0].raw_text == txt, txt
        expected = VALID if VALID in txt else OTHER
        assert m[0].notation.compact == expected, txt


def test_urn_carrier() -> None:
    for txt in [
        f"urn:lei:{VALID}",
        f"URN:LEI:{OTHER}",
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        # Span includes the carrier.
        assert (m[0].start, m[0].end) == (0, len(txt)), txt
        expected = VALID if VALID in txt else OTHER
        assert m[0].notation.compact == expected, txt


def test_quoted_bracketed_csv() -> None:
    for txt, expected in [
        (f'"{VALID}"', VALID),
        (f"[{OTHER}]", OTHER),
        (f"a;b;{VALID};", VALID),
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) >= 1, txt
        assert m[0].notation.compact == expected, txt


def test_glued_label_missing() -> None:
    assert GRAMMAR.recognize(f"LEI{OTHER}") == []


def test_bare_lei_prefix_code() -> None:
    # A bare 20-char code whose own prefix starts "LEI" is still a code.
    bare = "LEI" + "0" * 17
    assert len(bare) == 20
    m = GRAMMAR.recognize(bare)
    assert len(m) == 1
    assert m[0].notation.compact == bare
    assert m[0].notation.lou_prefix == "LEI0"


def test_double_space_tab_missing() -> None:
    assert GRAMMAR.recognize("5493  000IBP32UQZ0KL24") == []
    assert GRAMMAR.recognize("5493\t000IBP32UQZ0KL24") == []


def test_hyphen_missing() -> None:
    assert GRAMMAR.recognize("5493-000I-BP32-UQZ0-KL24") == []


def test_19_21_missing() -> None:
    assert GRAMMAR.recognize(VALID[:-1]) == []  # 19
    assert GRAMMAR.recognize(VALID + "5") == []  # 21


def test_glued_runs_missing() -> None:
    assert GRAMMAR.recognize("X" + VALID) == []
    assert GRAMMAR.recognize(VALID + "Y") == []


def test_homoglyph_missing() -> None:
    # Fullwidth digit 5 and fullwidth letter O never match the ASCII body.
    assert GRAMMAR.recognize("213800KUD8LAJWSQ9D1\uff15") == []
    assert GRAMMAR.recognize("\uff15493000IBP32UQZ0KL24") == []


def test_name_semantics_single_value() -> None:
    assert GRAMMAR.name == "lei_recognition"
    assert GRAMMAR.semantics == "lei_recognition"
    assert GRAMMAR.single_value is True
    # Scaffolder/capability seam: LEIRecognition stays a valid alias.
    assert LEIRecognition is LEIRecognitionGrammar
