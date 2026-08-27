import pytest

from paxman.capabilities.IBAN.contract import IBANContract
from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import (
    PUBLICATION,
    Section4IBANStructureMOD97,
)

pytestmark = [pytest.mark.capability]

RULE = Section4IBANStructureMOD97()
CONTRACT = IBANContract()


def n(compact: str) -> IBANNotation:
    return IBANNotation(
        country_code=compact[:2],
        check_digits=compact[2:4],
        bban=compact[4:],
        compact=compact,
    )


def test_provenance_metadata():
    assert PUBLICATION.authority == "ISO"
    assert PUBLICATION.specification_name == "ISO 13616-1:2020"
    assert PUBLICATION.reference_url == "https://www.iso.org/standard/81090.html"
    assert PUBLICATION.lifecycle == "active"
    assert PUBLICATION.publication_year == 2020
    assert PUBLICATION.kind == "specification"
    assert RULE.name == "Section 4-iban-structure-mod97"
    assert RULE.strategy.name == "PARSER"
    assert RULE.target_semantics == frozenset({"iban_recognition"})
    assert RULE.requires_features == frozenset()


def test_valid_vectors():
    for compact in [
        "DE89370400440532013000",
        "GB29NWBK60161331926819",
        "FR1420041010050500013M02606",
        "NO9386011117947",
        "MT84MALT011000012345MTLCAST001S",
        "SC18SSCB11010000000000001497USD",
        "LC55HEMM000100010012001200023015",
        "NI79BAMC00000000000003123123",
        "GB82WEST12345698765432",
    ]:
        compact = compact.replace(" ", "")
        assert RULE.matches(n(compact), CONTRACT) is True, compact
        assert RULE.normalize(n(compact), CONTRACT) == compact


def test_invalid_mod97_and_dd_range():
    assert RULE.matches(n("DE89370400440532013001"), CONTRACT) is False
    for bad_dd in [
        "DE00370400440532013000",
        "DE01370400440532013000",
        "DE99370400440532013000",
    ]:
        assert RULE.matches(n(bad_dd), CONTRACT) is False
    assert RULE.matches(n("DE8937040044053201300"), CONTRACT) is False
    assert RULE.matches(n("AB12"), CONTRACT) is False


def test_structure_edge_table():
    assert RULE.matches(n("DE89" + "A" * 31), CONTRACT) is False
    assert RULE.matches(n("NO938601111794"), CONTRACT) is False
    assert RULE.matches(n("1E89370400440532013000"), CONTRACT) is False
    assert RULE.matches(n("DEAB3704004405320130000"), CONTRACT) is False
    assert RULE.matches(n("de89370400440532013000"), CONTRACT) is False
    assert RULE.matches(n("DE89 3704 0044 0532 0130 00"), CONTRACT) is False


def test_unregistered_country_prefix_rejected():
    # ZZ is not in the SWIFT IBAN Registry (111 codes); even with a valid
    # MOD 97-10 checksum it must be rejected — registry, not bare ISO 3166-1.
    def calc_check(country: str, bban: str) -> str:
        rearr = bban + country + "00"
        exp = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearr)
        r = 0
        for ch in exp:
            r = (r * 10 + int(ch)) % 97
        return f"{98 - r:02d}"

    bban = "370400440532013000"
    cc = "ZZ"
    dd = calc_check(cc, bban)
    compact = cc + dd + bban
    # sanity: mod97 would be 1, but country check fails
    assert RULE.matches(n(compact), CONTRACT) is False
    # Also a US prefix (ISO but no IBAN) must be rejected even if mod97 passes
    cc2 = "US"
    dd2 = calc_check(cc2, bban)
    assert RULE.matches(n(cc2 + dd2 + bban), CONTRACT) is False


def test_per_country_length_enforced():
    """Per-country fixed lengths: wrong-length IBAN with correct mod97 is INVALID."""

    def calc(country: str, bban: str) -> str:
        rearr = bban + country + "00"
        exp = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearr)
        r = 0
        for ch in exp:
            r = (r * 10 + int(ch)) % 97
        return f"{98 - r:02d}"

    # DE fixed 22 — 20/21/23/24 with valid mod97 must be INVALID
    for bban_len, should_pass in [
        (16, False),
        (17, False),
        (18, True),
        (19, False),
        (20, False),
    ]:
        bban = "3" * bban_len
        dd = calc("DE", bban)
        compact = "DE" + dd + bban
        assert (len(compact) == 22) == should_pass
        assert RULE.matches(n(compact), CONTRACT) == should_pass, (
            f"DE bban_len {bban_len} {compact}"
        )

    # NO fixed 15 — 16 with valid mod97 must be INVALID
    bban = "1" * 12
    dd = calc("NO", bban)
    compact = "NO" + dd + bban
    assert len(compact) == 16
    assert RULE.matches(n(compact), CONTRACT) is False
    # correct NO15
    bban15 = "1" * 11
    dd15 = calc("NO", bban15)
    compact15 = "NO" + dd15 + bban15
    assert len(compact15) == 15
    assert RULE.matches(n(compact15), CONTRACT) is True


def test_registry_expanded_and_fp_removed():
    """Registry now 111 codes: new 2024 jurisdictions valid, FP removed."""
    from paxman.capabilities.IBAN.rules.data.iban_registry import (
        REGISTERED_IBAN_COUNTRY_CODES,
    )

    # FP must not be in registry (French Polynesia under FR)
    assert "FP" not in REGISTERED_IBAN_COUNTRY_CODES
    # New 2024 West/Central African + AO + DZ etc must be present
    for cc in [
        "AO",
        "BF",
        "BJ",
        "CF",
        "CG",
        "CI",
        "CM",
        "CV",
        "DZ",
        "GA",
        "GQ",
        "GW",
        "IR",
        "KM",
        "MA",
        "MG",
        "ML",
        "MZ",
        "NE",
        "SN",
        "TD",
        "TG",
    ]:
        assert cc in REGISTERED_IBAN_COUNTRY_CODES, cc
    assert len(REGISTERED_IBAN_COUNTRY_CODES) == 111

    # Verify AO/BF valid (previously MISSING) with correct mod97+length
    def calc(country: str, bban: str) -> str:
        rearr = bban + country + "00"
        exp = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in rearr)
        r = 0
        for ch in exp:
            r = (r * 10 + int(ch)) % 97
        return f"{98 - r:02d}"

    # AO 25, BF 28 — generate valid IBANs
    for cc, length in [("AO", 25), ("BF", 28), ("DZ", 24)]:
        bban_len = length - 4
        bban = "A" * bban_len
        dd = calc(cc, bban)
        compact = cc + dd + bban
        assert len(compact) == length
        assert RULE.matches(n(compact), CONTRACT) is True, f"{cc} {compact}"
    # FP with correct mod97 must now be INVALID (not registered)
    bban_fp = "A" * 20
    dd_fp = calc("FP", bban_fp)
    compact_fp = "FP" + dd_fp + bban_fp
    assert RULE.matches(n(compact_fp), CONTRACT) is False


def test_ni_length_corrected():
    # NI fixed 28 — old test vector NI92 32 must be INVALID, new NI79 28 is valid
    assert RULE.matches(n("NI92BAMC000000000000000003123123"), CONTRACT) is False
    assert RULE.matches(n("NI79BAMC00000000000003123123"), CONTRACT) is True
