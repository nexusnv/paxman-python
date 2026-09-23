"""Tests for the ISO/IEC 7812-1:2017 structure+Luhn PARSER rule."""

from pathlib import Path

import pytest

from paxman.capabilities.CreditCard.contract import CreditCardContract
from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.capabilities.CreditCard.rules.brand_prefix_ed2026 import (
    Section1BrandPrefixMembership,
)
from paxman.capabilities.CreditCard.rules.iso_7812_1_ed2017 import (
    Section5PANStructureLuhn,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

# Public test PANs (decision 8 / fixture hygiene) — all Luhn-valid.
_VALID_VECTORS = [
    "4111111111111111",  # visa 16
    "5555555555554444",  # mastercard 16
    "378282246310005",  # amex 15
    "371449635398431",  # amex 15
    "6011111111111117",  # discover 16
    "3530111333300000",  # jcb 16
    "36050234196908",  # diners 14
    "36227206271667",  # diners 14
    "4222222222222",  # visa 13
    "4716221051885662",  # visa 16
    "4929722653797141",  # visa 16
]

# One Luhn-valid vector per length 12..19 (precomputed generation direction);
# the 12-vector carries a leading zero to pin leading-zero handling.
_PER_LENGTH = {
    12: "011111111115",
    13: "4111111111119",
    14: "41111111111114",
    15: "411111111111116",
    16: "4111111111111111",
    17: "41111111111111113",
    18: "411111111111111118",
    19: "4111111111111111110",
}


def _n(digits: str, compact: str | None = None) -> PANNotation:
    return PANNotation(digits=digits, compact=compact if compact else digits)


@pytest.fixture
def rule() -> Section5PANStructureLuhn:
    return Section5PANStructureLuhn()


@pytest.fixture
def contract() -> CreditCardContract:
    return CreditCardContract()


def test_parser_valid_vectors(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    for digits in _VALID_VECTORS:
        assert rule.matches(_n(digits), contract) is True, digits


def test_luhn_helper_refs_below_floor(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    # Luhn-math reference fixtures (patent + Luhn article) — Luhn-valid but
    # below the 12-floor: the length gate rejects them, they are never
    # recognition or matches() fixtures.
    for digits in ["79927398713", "17893729974", "48721484"]:
        assert rule.matches(_n(digits), contract) is False, digits


def test_luhn_flip_invalid(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    for digits in ["4111111111111112", "5398228707871528"]:
        assert rule.matches(_n(digits), contract) is False, digits


def test_length_bounds(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    # Luhn-valid but out of the 12-19 range -> False on the length gate.
    assert rule.matches(_n("44444444440"), contract) is False  # 11 digits
    assert rule.matches(_n("44444444444444444444"), contract) is False  # 20 digits
    # In-range Luhn-valid -> True.
    assert rule.matches(_n(_PER_LENGTH[12]), contract) is True
    assert rule.matches(_n(_PER_LENGTH[19]), contract) is True


def test_compact_digits_mismatch_tamper(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    # Defense-in-depth: compact != digits means the notation was tampered
    # with after recognition — reject (ISIN precedent).
    tampered = PANNotation(digits="4111111111111111", compact="4111111111111112")
    assert rule.matches(tampered, contract) is False


def test_non_digit_false(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    assert rule.matches(_n("411111111111111X"), contract) is False
    assert rule.matches(_n(""), contract) is False


def test_normalize_identity(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    assert rule.normalize(_n("4111111111111111"), contract) == "4111111111111111"
    assert rule.normalize(_n(_PER_LENGTH[15]), contract) == _PER_LENGTH[15]


def test_every_length_12_19_has_valid_vector(
    rule: Section5PANStructureLuhn, contract: CreditCardContract
) -> None:
    # Consistency: each in-range length has at least one valid PAN.
    for length, digits in _PER_LENGTH.items():
        assert len(digits) == length, digits
        assert rule.matches(_n(digits), contract) is True, digits


def test_provenance_attrs() -> None:
    from paxman.capabilities.CreditCard.rules.iso_7812_1_ed2017 import PUBLICATION

    assert PUBLICATION.authority == "ISO/IEC"
    assert PUBLICATION.specification_name == "ISO/IEC 7812-1:2017"
    assert PUBLICATION.reference_url == "https://www.iso.org/standard/70484.html"
    assert PUBLICATION.version == "2017"
    assert PUBLICATION.kind == "specification"
    assert PUBLICATION.lifecycle == "active"
    assert PUBLICATION.publication_year == 2017


def test_strategy_six_attrs() -> None:
    rule = Section5PANStructureLuhn()
    assert rule.strategy is RuleStrategy.PARSER
    assert isinstance(rule.target_semantics, frozenset)
    assert rule.target_semantics == frozenset({"pan_recognition"})
    assert isinstance(rule.requires_features, frozenset)
    assert rule.requires_features == frozenset()
    assert rule.name == "Section 5-pan-structure-luhn"
    assert rule.citation  # non-empty


def test_no_output_format_token() -> None:
    source = Path(
        "paxman/capabilities/CreditCard/rules/iso_7812_1_ed2017.py"
    ).read_text()
    assert "output_format" not in source


# --- Brand-prefix membership (gated secondary LOOKUP_TABLE) ---


@pytest.fixture
def brand() -> Section1BrandPrefixMembership:
    return Section1BrandPrefixMembership()


def test_brand_data_present() -> None:
    from paxman.capabilities.CreditCard.rules.data import brand_prefix
    from paxman.capabilities.CreditCard.rules.data.brand_prefix import BRAND_PREFIXES

    eight = {
        "visa",
        "mastercard",
        "american-express",
        "discover",
        "diners-club",
        "jcb",
        "china-unionpay",
        "maestro",
    }
    assert set(BRAND_PREFIXES) == eight
    assert BRAND_PREFIXES["visa"][1] == frozenset({13, 16, 19})
    assert BRAND_PREFIXES["american-express"][1] == frozenset({15})
    assert BRAND_PREFIXES["mastercard"][1] == frozenset({16})
    doc = brand_prefix.__doc__ or ""
    # header documents secondary-never-ISO + refresh procedure + deferred-others
    assert "SECONDARY" in doc
    assert "never ISO" in doc
    assert "refresh" in doc.lower()
    assert "Others" in doc


def test_brand_matches_known_vectors() -> None:
    from paxman.capabilities.CreditCard.rules.brand_prefix_ed2026 import (
        matching_brands,
    )

    # decision-8 vectors route to their brand (membership, exact pin)
    expect = [
        ("4111111111111111", "visa"),
        ("4222222222222", "visa"),
        ("4716221051885662", "visa"),
        ("4929722653797141", "visa"),
        ("5555555555554444", "mastercard"),
        ("378282246310005", "american-express"),
        ("371449635398431", "american-express"),
        ("6011111111111117", "discover"),
        ("3530111333300000", "jcb"),
        ("36050234196908", "diners-club"),
        ("36227206271667", "diners-club"),
        ("6200000000000005", "china-unionpay"),
    ]
    for digits, brand_key in expect:
        assert matching_brands(digits) == frozenset({brand_key}), digits


def test_brand_unknown_prefix_false(
    brand: Section1BrandPrefixMembership,
    rule: Section5PANStructureLuhn,
    contract: CreditCardContract,
) -> None:
    # Luhn-valid 99... run: no allowlisted brand -> brand rule False while
    # the ISO structure+Luhn rule stays True (generic-valid off-gate).
    unknown = "9999999999999995"
    assert rule.matches(_n(unknown), contract) is True
    assert brand.matches(_n(unknown), contract) is False


def test_brand_duplicate_luhn_no_waiver(
    brand: Section1BrandPrefixMembership,
    rule: Section5PANStructureLuhn,
    contract: CreditCardContract,
) -> None:
    # No braintree UnionPay bypass (decision 5): Luhn-invalid 62-prefix
    # fails BOTH rules; Luhn-valid 62-prefix passes BOTH (ADR-0012
    # corroboration, never a waiver).
    bad = _n("6200000000000001")
    good = _n("6200000000000005")
    assert rule.matches(bad, contract) is False
    assert brand.matches(bad, contract) is False
    assert rule.matches(good, contract) is True
    assert brand.matches(good, contract) is True
    # normalize identical to the ISO rule so candidate dedup keeps SUCCESS
    assert brand.normalize(good, contract) == rule.normalize(good, contract)
    assert brand.normalize(good, contract) == "6200000000000005"


def test_brand_gate_frozenset() -> None:
    rule = Section1BrandPrefixMembership()
    assert rule.requires_features == frozenset({"include_brand_validation"})
    assert rule.target_semantics == frozenset({"pan_recognition"})
    assert rule.strategy is RuleStrategy.LOOKUP_TABLE
    assert rule.name == "Section 1-brand-prefix-membership"
    assert rule.citation  # non-empty


def test_brand_provenance_secondary() -> None:
    from paxman.capabilities.CreditCard.rules.brand_prefix_ed2026 import PUBLICATION

    assert PUBLICATION.kind == "registry"
    assert PUBLICATION.authority == "Brand networks"
    assert "ISO" not in PUBLICATION.authority
    assert "ISO" not in PUBLICATION.specification_name
    assert PUBLICATION.version == "Rolling 2026"
    assert (
        PUBLICATION.reference_url == "https://en.wikipedia.org/wiki/Payment_card_number"
    )
