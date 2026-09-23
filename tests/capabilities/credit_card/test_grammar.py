"""Tests for PAN recognition grammar (scanner kind + four guards)."""

import pytest

from paxman.capabilities.CreditCard.grammar.pan_recognition import (
    PANRecognitionGrammar,
)
from paxman.core.domain import Grammar, RecognitionMatch

pytestmark = [pytest.mark.capability]


@pytest.fixture
def grammar() -> Grammar:
    return PANRecognitionGrammar()


def test_name_semantics_single_value(grammar: Grammar) -> None:
    assert grammar.name == "pan_recognition"
    assert grammar.semantics == "pan_recognition"
    assert grammar.single_value is True


def test_compact_16_span(grammar: Grammar) -> None:
    text = "4111111111111111"
    m = grammar.recognize(text)
    assert len(m) == 1
    assert m[0].notation.digits == "4111111111111111"
    assert m[0].notation.compact == "4111111111111111"
    assert (m[0].start, m[0].end) == (0, 16)


def test_amex_15_and_diners_14_span(grammar: Grammar) -> None:
    m15 = grammar.recognize("378282246310005")
    assert len(m15) == 1
    assert m15[0].notation.digits == "378282246310005"
    assert (m15[0].start, m15[0].end) == (0, 15)
    m14 = grammar.recognize("36050234196908")
    assert len(m14) == 1
    assert m14[0].notation.digits == "36050234196908"
    assert (m14[0].start, m14[0].end) == (0, 14)


def test_spaced_dashed_mixed_grouping(grammar: Grammar) -> None:
    cases = [
        ("4111 1111 1111 1111", "4111111111111111"),
        ("4716-2210-5188-5662", "4716221051885662"),
        ("4444-3333 2222 1111", "4444333322221111"),
        ("3782 822463 10005", "378282246310005"),  # Amex 4-6-5 grouping
    ]
    for text, digits in cases:
        m = grammar.recognize(text)
        assert len(m) == 1, text
        assert m[0].notation.digits == digits, text
        assert m[0].raw_text == text, text
    # grouped input = same digits as its compact twin (grouping-agnostic)
    grouped = grammar.recognize("3782 822463 10005")
    compact = grammar.recognize("378282246310005")
    assert grouped[0].notation == compact[0].notation


def test_label_variants(grammar: Grammar) -> None:
    cases = [
        ("pan: 4111 1111 1111 1111", "pan"),
        ("PAN: 4111111111111111", "PAN"),
        ("CC: 4111111111111111", "CC"),
        ("card number: 4111111111111111", "card number"),
        ("credit card 4111111111111111", "credit card"),
    ]
    for text, label in cases:
        m = grammar.recognize(text)
        assert len(m) == 1, text
        assert m[0].notation.digits == "4111111111111111", text  # label-free
        assert m[0].start == 0, text  # span includes label
        assert m[0].raw_text.startswith(label), text
        assert m[0].raw_text == text[: m[0].end], text


def test_glued_label_missing(grammar: Grammar) -> None:
    assert grammar.recognize("PAN4111111111111111") == []


def test_quoted_bracketed_adjacent(grammar: Grammar) -> None:
    for text in [
        '"4111111111111111"',
        "(4111111111111111)",
        "[4111 1111 1111 1111]",
        "value '4111-1111-1111-1111' end",
    ]:
        m = grammar.recognize(text)
        assert len(m) == 1, text
        assert m[0].notation.digits == "4111111111111111", text


def test_two_mention_pairs(grammar: Grammar) -> None:
    pairs = [
        "4111111111111111 5555555555554444",
        "4111111111111111-5555555555554444",
        "4111111111111111/5555555555554444",
        "4111111111111111, 5555555555554444",
    ]
    for text in pairs:
        m = grammar.recognize(text)
        assert len(m) == 2, text
        assert m[0].notation.digits == "4111111111111111", text
        assert m[1].notation.digits == "5555555555554444", text


def test_expiry_span_only(grammar: Grammar) -> None:
    text = "4111111111111111 12/27"
    m = grammar.recognize(text)
    assert len(m) == 1
    assert m[0].notation.digits == "4111111111111111"
    assert m[0].raw_text == "4111111111111111"  # excludes " 12/27"
    assert (m[0].start, m[0].end) == (0, 16)
    # expiry word form untouched: only the PAN claims
    m2 = grammar.recognize("4111111111111111 exp 01/28")
    assert len(m2) == 1
    assert m2[0].raw_text == "4111111111111111"


def test_cvv_tail_19_claim(grammar: Grammar) -> None:
    # CVV tail " 123" is soft-joined and below the 20-run ceiling: the whole
    # 19-digit run is claimed atomically (19 <= 19), never carved to 16.
    m = grammar.recognize("4111111111111111 123")
    assert len(m) == 1
    assert m[0].notation.digits == "4111111111111111123"
    assert len(m[0].notation.digits) == 19


def test_cvv4_missing(grammar: Grammar) -> None:
    # 16 + 4 CVV = 20-digit run: over ceiling, no 16-carve.
    assert grammar.recognize("4111111111111111 1234") == []


def test_over_ceiling_missing(grammar: Grammar) -> None:
    over = [
        "41111111111111111227",  # compact 20
        "4111 1111 1111 1111 0000",  # spaced 20
        "4111-1111-1111-1111-0000",  # hyphen 20
    ]
    for text in over:
        assert grammar.recognize(text) == [], text


def test_under_floor_missing(grammar: Grammar) -> None:
    assert grammar.recognize("41111111111") == []  # 11 digits
    assert grammar.recognize("41111111") == []  # 8 digits


def test_letter_digit_glued_missing(grammar: Grammar) -> None:
    assert grammar.recognize("X4111111111111111") == []
    assert grammar.recognize("4111111111111111Y") == []
    assert grammar.recognize("A4111111111111111B") == []


def test_double_space_tab_missing(grammar: Grammar) -> None:
    # Documented non-recognition: irregular whitespace (double space/tab).
    assert grammar.recognize("4111  1111 1111 1111") == []
    assert grammar.recognize("4111\t1111\t1111\t1111") == []


def test_digit_glued_17_whole_claim(grammar: Grammar) -> None:
    m = grammar.recognize("41111111111111111")
    assert len(m) == 1
    assert (m[0].start, m[0].end) == (0, 17)  # whole run, never a 16-carve
    assert m[0].notation.digits == "41111111111111111"


def test_prose_predecessor_18_claim(grammar: Grammar) -> None:
    # Documented trade-off: a same-line sub-floor predecessor joins the run
    # -> the whole 18-digit run is one claim (atomic whole-run discipline).
    m = grammar.recognize("order 12 4111111111111111")
    assert len(m) == 1
    assert m[0].notation.digits == "124111111111111111"
    assert len(m[0].notation.digits) == 18
    # line break is a hard boundary -> the 16-digit PAN claims alone
    m2 = grammar.recognize("total 12\n4111111111111111")
    assert len(m2) == 1
    assert m2[0].notation.digits == "4111111111111111"


def test_homoglyph_fullwidth_missing(grammar: Grammar) -> None:
    fullwidth = "".join(chr(0xFF10 + int(ch)) for ch in "4111111111111111")
    assert grammar.recognize(fullwidth) == []
    # fullwidth digit glued before an ASCII run is also not a mention
    assert grammar.recognize(fullwidth + "4111111111111111") == []


def test_unicode_digit_never_fabricated(grammar: Grammar) -> None:
    # ASCII-only recognition: a non-ASCII digit (Arabic-Indic, full-width)
    # inside or beside a run must never be silently dropped to fabricate a
    # PAN that was not written. Before the [0-9] body fix, Unicode \d matched
    # these digits and _pan_emit filtered them out, yielding a Luhn-valid
    # value (e.g. "3٠78282246310005" -> "378282246310005") from input that
    # never contained it — a fabrication that violated the no-fabrication
    # invariant and the documented ASCII-only contract.
    assert grammar.recognize("3٠78282246310005") == []  # Arabic-Indic zero
    assert grammar.recognize("PAN: ４111111111111111") == []  # full-width 4
    assert grammar.recognize("411111111111111٣") == []  # Arabic-Indic three


def test_left_soft_run_caps_at_twelve() -> None:
    # Perf regression guard: the backward walk caps at 12 because the caller
    # only distinguishes 0 / 1-11 / >=12 (frag >= 12 is a separate mention,
    # never blocked). Without the cap, a long digit run was rescanned in full
    # at every scan position — O(n^2): 20k digits took ~40s through
    # canonicalize(). The cap keeps recognition linear; the guard decision is
    # unchanged because 12 and any larger count both fall outside 1..11.
    from paxman.capabilities.CreditCard.grammar.pan_recognition import (
        _left_soft_run_digits,
    )

    assert _left_soft_run_digits("1" * 5000, 5000) == 12  # capped, not 5000
    assert _left_soft_run_digits("1" * 11, 11) == 11  # under cap: exact
    assert _left_soft_run_digits("1 2 3", 5) == 3  # separators counted out
    assert _left_soft_run_digits("", 0) == 0  # empty: no run


def test_span_invariants(grammar: Grammar) -> None:
    texts = [
        "4111111111111111",
        "4111 1111 1111 1111",
        "pan: 4111 1111 1111 1111",
        "4111111111111111 12/27",
        "order 12 4111111111111111",
    ]
    for text in texts:
        for match in grammar.recognize(text):
            assert isinstance(match, RecognitionMatch)
            assert match.raw_text == text[match.start : match.end]
            assert len(match.raw_text) == match.end - match.start
    # label-inclusive span
    label = grammar.recognize("pan: 4111 1111 1111 1111")
    assert label[0].raw_text.startswith("pan:")
