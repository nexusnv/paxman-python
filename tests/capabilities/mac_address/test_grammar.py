# tests/capabilities/mac_address/test_grammar.py
import pytest

from paxman.capabilities.MacAddress.grammar import MacAddressRecognitionGrammar

pytestmark = [pytest.mark.capability]


def spans(text):
    return MacAddressRecognitionGrammar().recognize(text)


def compacts(text):
    return [m.notation.compact for m in spans(text)]


# --- positive: one vector per Research section 2.1 RECOGNIZE form ---


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # colon 48 (research 2.1 row 1)
        ("00:1A:2B:3C:4D:5E", "001A2B3C4D5E"),
        # hyphen 48 (row 2, IEEE display)
        ("00-1A-2B-3C-4D-5E", "001A2B3C4D5E"),
        # cisco tri-dot (row 3)
        ("001A.2B3C.4D5E", "001A2B3C4D5E"),
        # bare 12 (row 4)
        ("001A2B3C4D5E", "001A2B3C4D5E"),
        # case folding (row 17)
        ("00:1a:2b:3c:4d:5e", "001A2B3C4D5E"),
        ("De:Ad:Be:Ef:Ca:Fe", "DEADBEEFCAFE"),
        # EUI-64 colon/hyphen/dot/bare (rows 5-8)
        ("00:1A:2B:3C:4D:5E:66:77", "001A2B3C4D5E6677"),
        ("00-1A-2B-3C-4D-5E-66-77", "001A2B3C4D5E6677"),
        ("001A.2B3C.4D5E.6677", "001A2B3C4D5E6677"),
        ("001A2B3C4D5E6677", "001A2B3C4D5E6677"),
        # modified EUI-64 / Zigbee (row 9)
        ("84:71:27:ff:fe:93:17:24", "847127FFFE931724"),
        # bit-reversed Token-Ring spelling (row 10) - recognized as itself
        ("48-2C-6A-1E-59-3D", "482C6A1E593D"),
        # MAC label fused (row 14)
        ("MAC: 00:1A:2B:3C:4D:5E", "001A2B3C4D5E"),
        ("MAC:00:1A:2B:3C:4D:5E", "001A2B3C4D5E"),
        ("mac - 001a.2b3c.4d5e", "001A2B3C4D5E"),
        # RFC 7042 documentation value
        ("00-00-5E-00-53-01", "00005E005301"),
        # sentinels are valid (research 7.1)
        ("FF:FF:FF:FF:FF:FF", "FFFFFFFFFFFF"),
        ("00:00:00:00:00:00", "000000000000"),
        ("01:80:C2:00:00:00", "0180C2000000"),
        ("33:33:00:00:00:01", "333300000001"),
        # quoted / embedded (research 8 edge 15)
        ('"00:1A:2B:3C:4D:5E"', "001A2B3C4D5E"),
        ("eth0 ether 00:1b:77:49:54:fd", "001B774954FD"),
        # residue policy (research 8 edge 12): 4-hex and 1-hex residues claim
        ("00:1A:2B:3C:4D:5E:6677", "001A2B3C4D5E"),
        ("00:1A:2B:3C:4D:5E-3", "001A2B3C4D5E"),
        ("001A2B3C4D5E:6677", "001A2B3C4D5E"),
        # word suffix does not block
        ("device 00:1A:2B:3C:4D:5E-end up", "001A2B3C4D5E"),
        # HA {ieee}-{endpoint} EUI-64 + endpoint (truncation-guard exemption)
        ("84:71:27:ff:fe:93:17:24-11", "847127FFFE931724"),
    ],
)
def test_recognizes(text, expected):
    result = spans(text)
    assert len(result) == 1
    assert result[0].notation.compact == expected
    assert result[0].notation.shape == ("eui64" if len(expected) == 16 else "eui48")


def test_span_invariants():
    text = "addr 00:1A:2B:3C:4D:5E end"
    result = spans(text)
    assert len(result) == 1
    m = result[0]
    assert m.raw_text == "00:1A:2B:3C:4D:5E"
    assert m.raw_text == text[m.start : m.end]
    assert len(m.raw_text) == m.end - m.start


def test_label_included_in_raw_text():
    m = spans("MAC: 00:1A:2B:3C:4D:5E")[0]
    assert m.raw_text == "MAC: 00:1A:2B:3C:4D:5E"
    assert m.notation.compact == "001A2B3C4D5E"


def test_embedded_eui48_in_eui64_single_longest_match():
    assert compacts("x 00:1A:2B:3C:4D:5E:66:77 y") == ["001A2B3C4D5E6677"]


def test_bare_16_before_12():
    assert compacts("001A2B3C4D5E6677") == ["001A2B3C4D5E6677"]


def test_multiple_mentions():
    text = "src=00:1A:2B:3C:4D:5E dst=00-1B-77-49-54-FD"
    assert compacts(text) == ["001A2B3C4D5E", "001B774954FD"]
    assert len(spans("permit 001a.2b3c.4d5e 001a.2b3c.4d5f")) == 2


# --- negatives: research 2.2 / 8 ---


@pytest.mark.parametrize(
    "text",
    [
        "MAC001A2B3C4D5E",  # glued label
        "00:1A-2B:3C-4D:5E",  # mixed separators
        "001A.2B3C:4D5E",  # mixed separator families
        "00:1A:2B:3C:4D:5E:66",  # 7 octets - truncated final octet
        "00:1A:2B:3C:4D:5E-66",
        "001A2B3C4D5E-66",
        "001A.2B3C.4D5E.66",
        "001A2B3C4D5E6",  # 13 hex
        "001A2B3C4D5",  # 11 hex
        "001A2B3C4D5E667",  # 15 hex
        "X001A2B3C4D5E",  # left glue
        "001A2B3C4D5EY",  # right glue
        "A001A2B3C4D5E6677B",
        "0:1b:77:49:54:fd",  # 1-digit octets DEFER
        "08002b:010203",  # 24-bit word DEFER
        "08002b:0102030405",
        "00 1A 2B 3C 4D 5E",  # whitespace separator DEFER
        "fe80::1",  # IPv6 compressed
        "00:1A:2B:3C:4D:0G",  # invalid charset
        "００:1A:2B:3C:4D:5E",  # fullwidth digits
        "550e8400-e29b-41d4-a716-446655440000",  # UUID
        "aabbccddeeff00112233",  # 20-hex (git full-SHA length)
        "1:00:1A:2B:3C:4D:5E",  # 7-octet 1-digit-first run, tail claim
        "",
        "   ",
        "\t\n",
    ],
)
def test_ignores(text):
    assert spans(text) == []


def test_nine_octet_claims_complete_eui64_with_residue():
    # documented policy (research 8 edge 12 / 14): a complete valid form
    # followed by junk residue claims the form
    assert compacts("00:1A:2B:3C:4D:5E:66:77:88") == ["001A2B3C4D5E6677"]


def test_grammar_metadata():
    g = MacAddressRecognitionGrammar()
    assert g.name == "mac_address_recognition"
    assert g.semantics == "mac_address_recognition"
    assert g.single_value is True
