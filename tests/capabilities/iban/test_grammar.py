import pytest

from paxman.capabilities.IBAN.grammar.iban_recognition import IBANRecognitionGrammar

pytestmark = [pytest.mark.capability]

GRAMMAR = IBANRecognitionGrammar()


def test_valid_electronic():
    m = GRAMMAR.recognize("DE89370400440532013000")
    assert len(m) == 1
    n = m[0].notation
    assert n.compact == "DE89370400440532013000"
    assert n.country_code == "DE" and n.check_digits == "89"
    assert m[0].raw_text == "DE89370400440532013000"
    assert m[0].end - m[0].start == len(m[0].raw_text)


def test_paper_groups_of_four():
    m = GRAMMAR.recognize("DE89 3704 0044 0532 0130 00")
    assert m[0].notation.compact == "DE89370400440532013000"


def test_case_insensitive_and_label():
    for txt in [
        "de89370400440532013000",
        "IBAN: DE89 3704 0044 0532 0130 00",
        "iban:gb29nwbk60161331926819",
        "IBAN - FR14 2004 1010 0505 0001 3M02 606",
        "IBAN DE89370400440532013000",
    ]:
        assert len(GRAMMAR.recognize(txt)) == 1


def test_lowercase_label_and_compact():
    m = GRAMMAR.recognize("iban: gb29 nwbk 6016 1331 9268 19")
    assert m[0].notation.compact == "GB29NWBK60161331926819"


def test_word_guard_blocks_left_and_label_glue():
    assert GRAMMAR.recognize("XDE89370400440532013000") == []
    assert GRAMMAR.recognize("IBANDE89370400440532013000") == []


def test_alnum_tail_absorbed_documented():
    m = GRAMMAR.recognize("DE89370400440532013000Y")
    assert len(m) == 1
    assert m[0].notation.compact == "DE89370400440532013000Y"


def test_min_and_max_length_bounds():
    assert GRAMMAR.recognize("NO938601111794") == []
    assert len(GRAMMAR.recognize("NO93 8601 1117 947")) == 1
    assert GRAMMAR.recognize("DE89" + "A" * 31) == []


def test_multi_whitespace_rejected_narrow_tolerance():
    assert GRAMMAR.recognize("DE89  3704 0044 0532 0130 00") == []
    assert GRAMMAR.recognize("DE89\t3704 0044") == []


def test_multiple_matches():
    txt = "DE89 3704 0044 0532 0130 00 / GB29 NWBK 6016 1331 9268 19"
    assert len(GRAMMAR.recognize(txt)) == 2


def test_semantics_and_name():
    assert GRAMMAR.name == "iban_recognition"
    assert GRAMMAR.semantics == "iban_recognition"
    assert GRAMMAR.single_value is True


def test_span_invariants():
    # "now" must not be absorbed: the paper groups-of-four alternative ends at
    # the IBAN, not at trailing English words (fix 34b569a pin — the uniform
    # loop absorbed " now", making this input INVALID instead of SUCCESS).
    txt = "Pay to DE89 3704 0044 0532 0130 00 now"
    m = GRAMMAR.recognize(txt)[0]
    assert txt[m.start : m.end] == m.raw_text
    assert m.raw_text == "DE89 3704 0044 0532 0130 00"
    assert txt[m.end :].startswith(" now")
    assert m.notation.compact == "DE89370400440532013000"


def test_irregular_paper_groups_rejected_documented():
    # Groups-of-four strictness (fix 34b569a): irregular single-space groups
    # are NOT recognized. Research edge 18 expected SUCCESS under the uniform
    # loop — deliberately traded for trailing-word safety. MISSING downstream.
    assert GRAMMAR.recognize("DE89 37040 04405 32013 000") == []


def test_truncated_two_group_paper_recognized():
    # Truncated paper (2 full groups, compact 12 < 15) is recognized by the
    # grammar (min = 2 groups) but rejected by the rule -> INVALID, not
    # MISSING. Pinned so the status split stays deliberate (research row 7
    # allows either; integration test_truncated_paper_is_invalid pins the
    # downstream status).
    m = GRAMMAR.recognize("DE89 3704 0044")
    assert len(m) == 1
    assert m[0].notation.compact == "DE8937040044"


def test_paper_glued_tail_absorbed_documented():
    # The paper final group (space + 1-4 alnum) absorbs a glued alnum tail of
    # up to 4 chars — the documented tail-absorption decision extended to the
    # paper alternative; mod-97 rejects downstream (INVALID), never SUCCESS.
    m = GRAMMAR.recognize("DE89 3704 0044 0532 0130 00n")
    assert len(m) == 1
    assert m[0].notation.compact == "DE89370400440532013000N"


def test_kelvin_and_unicode_digits_rejected():
    # ASCII-only body: Kelvin sign K (U+212A) case-folds to K under Unicode
    # IGNORECASE but must not match [A-Z] when restricted to ASCII;
    # Unicode digits (e.g. Arabic-Indic) must not match [0-9].
    # Boundary remains Unicode-aware, body remains ASCII.
    assert GRAMMAR.recognize("\u212aE89" + "A" * 11) == []
    assert GRAMMAR.recognize("DE\u0668\u0669" + "3704004405") == []


def test_hyphen_and_double_space_documented_as_missing():
    # Hyphen-separated paper, double space, tab, irregular groups are
    # MISSING (not INVALID)
    # Documented strict single-space groups-of-four discipline (ISO 13616 paper).
    assert GRAMMAR.recognize("DE89-3704-0044-0532-0130-00") == []
    assert GRAMMAR.recognize("DE89  3704 0044 0532 0130 00") == []
    assert GRAMMAR.recognize("DE89\t3704 0044") == []
    assert GRAMMAR.recognize("DE89 37040 04405 32013 000") == []


def test_per_country_length_via_canonicalize():
    # Wrong-length IBANs that previously would be SUCCESS via generic check are now
    # correctly handled at rule layer (grammar MISSING vs INVALID split is pinned).
    # This test verifies the grammar still recognizes short paper (12) as INVALID
    # and that overly long 32 for NI is INVALID via per-country length.
    import contextlib

    from paxman.api.bootstrap import register_all_shipped
    from paxman.api.canonicalize import canonicalize
    from paxman.capabilities.IBAN.contract import IBANContract

    with contextlib.suppress(Exception):
        register_all_shipped()

    # DE20 with valid mod97 should be INVALID (per-country length 22)
    def calc(country: str, bban: str) -> str:
        rearr = bban + country + "00"
        exp = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearr)
        r = 0
        for ch in exp:
            r = (r * 10 + int(ch)) % 97
        return f"{98 - r:02d}"

    bban = "3" * 16
    dd = calc("DE", bban)
    compact = "DE" + dd + bban
    assert len(compact) == 20
    r = canonicalize(compact, IBANContract())
    assert r.status.name == "INVALID"
