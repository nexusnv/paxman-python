import pytest

from paxman.capabilities.BIC.grammar.bic_recognition import BICRecognitionGrammar

pytestmark = [pytest.mark.capability]

GRAMMAR = BICRecognitionGrammar()


def test_valid_electronic():
    for compact in ["DEUTDEFF", "BNPAFRPP", "CHASUS33", "BARCGB22", "NEDSZAJJ"]:
        m = GRAMMAR.recognize(compact)
        assert len(m) == 1, compact
        n = m[0].notation
        assert n.compact == compact
        assert n.bank_code == compact[0:4]
        assert n.country_code == compact[4:6]
        assert n.location_code == compact[6:8]
        assert n.branch_code == ""
        assert m[0].raw_text == compact
        assert m[0].end - m[0].start == len(m[0].raw_text)
    for compact in [
        "DEUTDEFF500",
        "BNPAFRPPXXX",
        "SOGEFRPPBRE",
        "DSBACNBXSHA",
        "NEDSZAJJXXX",
    ]:
        m = GRAMMAR.recognize(compact)
        assert len(m) == 1, compact
        assert m[0].notation.compact == compact
        assert m[0].notation.branch_code == compact[8:11]
        assert len(m[0].notation.compact) == 11


def test_case_insensitive_and_label():
    for txt, expected in [
        ("deutdeff", "DEUTDEFF"),
        ("DeUtDeFf500", "DEUTDEFF500"),
        ("BIC: DEUTDEFF", "DEUTDEFF"),
        ("SWIFT: BNPAFRPPXXX", "BNPAFRPPXXX"),
        ("BIC DEUTDEFF500", "DEUTDEFF500"),
        ("bic - NEDSZAJJ", "NEDSZAJJ"),
        ("SWIFT  DSBACNBXSHA", "DSBACNBXSHA"),
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        assert m[0].notation.compact == expected, txt
    # swift-code is NOT a BIC/SWIFT label (label is BIC or SWIFT only); it
    # falls through to bare match at offset after the hyphen, so raw_text is
    # bare CHASUS33, not "swift-code: CHASUS33". Compact still resolves.
    m_swift_code = GRAMMAR.recognize("swift-code: CHASUS33")
    assert len(m_swift_code) == 1
    assert m_swift_code[0].notation.compact == "CHASUS33"
    assert m_swift_code[0].raw_text == "CHASUS33"


def test_word_guard_blocks_left_and_label_glue():
    # Left glue: (?<!\w) lookbehind rejects carving out of longer token
    assert GRAMMAR.recognize("XDEUTDEFF") == []
    assert GRAMMAR.recognize("ADEUTDEFF500B") == []
    assert GRAMMAR.recognize("DEUTDEFFY") == []
    # Glued label: separator is [\s:-]+ never zero width
    assert GRAMMAR.recognize("BICDEUTDEFF") == []
    assert GRAMMAR.recognize("SWIFTDEUTDEFF500") == []
    assert GRAMMAR.recognize("BICDEUTDEFF500") == []


def test_length_bounds():
    # Only 8 or 11 valid, 7/9/10/12 must not be recognized as BIC
    assert GRAMMAR.recognize("DEUTDEF") == []  # 7
    assert GRAMMAR.recognize("DEUTDEFF5") == []  # 9
    assert GRAMMAR.recognize("DEUTDEFF50") == []  # 10
    assert GRAMMAR.recognize("DEUTDEFF5000") == []  # 12
    # valid 8 and 11 are accepted
    assert len(GRAMMAR.recognize("DEUTDEFF")) == 1
    assert len(GRAMMAR.recognize("DEUTDEFF500")) == 1
    # 7 plus valid 8 needs word guard: XDEUTDEF is not valid anyway
    assert GRAMMAR.recognize("DEUTDEFF50000") == []  # 13 alnum glued, no word break


def test_multiple_matches():
    txt = "DEUTDEFF / BNPAFRPPXXX"
    m = GRAMMAR.recognize(txt)
    assert len(m) == 2
    assert m[0].notation.compact == "DEUTDEFF"
    assert m[1].notation.compact == "BNPAFRPPXXX"
    txt2 = "BICs: DEUTDEFF500, CHASUS33"
    assert len(GRAMMAR.recognize(txt2)) == 2


def test_semantics_and_name():
    assert GRAMMAR.name == "bic_recognition"
    assert GRAMMAR.semantics == "bic_recognition"
    assert GRAMMAR.single_value is True


def test_span_invariants():
    txt = "Please remit to BIC DEUTDEFF (Deutsche Bank)"
    m = GRAMMAR.recognize(txt)
    # BIC pattern is 8/11 alphanum and will also match "Deutsche" (8 letters) as a
    # standalone token; grammar is syntax-only and over-matches, rules filter.
    # Assert at least one BIC DEUTDEFF with label is present.
    assert any(
        x.raw_text == "BIC DEUTDEFF" and x.notation.compact == "DEUTDEFF" for x in m
    )
    # primary labelled span invariants
    labelled = next(x for x in m if x.notation.compact == "DEUTDEFF")
    assert txt[labelled.start : labelled.end] == labelled.raw_text
    assert 0 <= labelled.start < labelled.end <= len(txt)
    assert labelled.raw_text == "BIC DEUTDEFF"
    assert labelled.notation.compact == "DEUTDEFF"
    # bare without label
    m2 = GRAMMAR.recognize("Pay to DEUTDEFF now")[0]
    assert m2.raw_text == "DEUTDEFF"


def test_empty_and_quoted():
    assert GRAMMAR.recognize("") == []
    m = GRAMMAR.recognize('"DEUTDEFF"')
    assert len(m) == 1 and m[0].notation.compact == "DEUTDEFF"
    m2 = GRAMMAR.recognize("[BNPAFRPPXXX]")
    assert len(m2) == 1 and m2[0].notation.compact == "BNPAFRPPXXX"
