"""Tests for BIC Section 5 rule."""

from __future__ import annotations

from pathlib import Path

import pytest

from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.BIC.notation import BICNotation
from paxman.capabilities.BIC.rules.iso_9362_ed2022 import (
    COUNTRY_CODES,
    PUBLICATION,
    Section5BICStructureCountry,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

RULE = Section5BICStructureCountry()
CONTRACT = BICContract()


def n(compact: str) -> BICNotation:
    c = compact.upper()
    return BICNotation(
        bank_code=c[0:4],
        country_code=c[4:6],
        location_code=c[6:8],
        branch_code=c[8:11] if len(c) == 11 else "",
        compact=c,
    )


def test_provenance_metadata() -> None:
    assert PUBLICATION.authority == "ISO"
    assert PUBLICATION.specification_name == "ISO 9362:2022"
    assert PUBLICATION.reference_url == "https://www.iso.org/standard/84108.html"
    assert PUBLICATION.lifecycle == "active"
    assert PUBLICATION.publication_year == 2022
    assert PUBLICATION.kind == "specification"
    assert PUBLICATION.version == "2022"
    assert RULE.name == "Section 5-bic-structure-country"
    assert RULE.strategy.name == "PARSER"
    assert RULE.strategy is RuleStrategy.PARSER
    assert RULE.target_semantics == frozenset({"bic_recognition"})
    assert RULE.requires_features == frozenset()
    assert "Section 5" in RULE.citation
    assert RULE.provenance is PUBLICATION


def test_valid_vectors() -> None:
    for compact in [
        "DEUTDEFF",
        "DEUTDEFF500",
        "BNPAFRPP",
        "BNPAFRPPXXX",
        "CHASUS33",
        "BARCGB22",
        "NEDSZAJJ",
        "NEDSZAJJXXX",
        "SOGEFRPPBRE",
        "DSBACNBXSHA",
        "RBOSGB2L",
        "CHASGB2L",
        "BANKXK22",
        "CBKIXKPRXXX",
        "BOFAXK2X",
    ]:
        assert RULE.matches(n(compact), CONTRACT) is True, compact
        assert RULE.normalize(n(compact), CONTRACT) == compact


def test_invalid_length_and_charset() -> None:
    # wrong lengths 7, 9, 10, 12
    assert (
        RULE.matches(
            BICNotation(
                bank_code="DEUT",
                country_code="DE",
                location_code="F",
                branch_code="",
                compact="DEUTDEF",
            ),
            CONTRACT,
        )
        is False
    )
    assert RULE.matches(n("DEUTDEFF5"), CONTRACT) is False
    assert RULE.matches(n("DEUTDEFF50"), CONTRACT) is False
    assert RULE.matches(n("DEUTDEFF5000"), CONTRACT) is False
    # digits in country position (2!a must be A-Z)
    assert RULE.matches(n("DEUT1EFF"), CONTRACT) is False
    assert RULE.matches(n("DEUT12FF"), CONTRACT) is False
    # lowercase compact fails isupper
    assert (
        RULE.matches(
            BICNotation(
                bank_code="deut",
                country_code="de",
                location_code="ff",
                branch_code="",
                compact="deutdeff",
            ),
            CONTRACT,
        )
        is False
    )
    # non-ascii
    assert (
        RULE.matches(
            BICNotation(
                bank_code="DEUT",
                country_code="DE",
                location_code="FF",
                branch_code="",
                compact="DEUTDEFF\u212a",
            ),
            CONTRACT,
        )
        is False
    )
    # non-alnum
    assert (
        RULE.matches(
            BICNotation(
                bank_code="DEUT",
                country_code="DE",
                location_code="FF",
                branch_code="",
                compact="DEUTDE-F",
            ),
            CONTRACT,
        )
        is False
    )
    # bank code must be 4 letters per GOAL; digits invalid
    # regex [A-Z]{4} catches digits in bank, so DE1T etc invalid
    assert RULE.matches(n("DE1TDEFF"), CONTRACT) is False
    assert RULE.matches(n("12UTDEFF"), CONTRACT) is False


def test_invalid_country() -> None:
    for bad in [
        "DEUTXXFF",
        "BNPAQQPP",
        "CHASZZ33",
        "DEUTQQFF",
        "DEUTXXFFXXX",
        "BNPAQQPPXXX",
    ]:
        assert RULE.matches(n(bad), CONTRACT) is False, bad
    # ensure country codes set is exhaustive
    assert "XK" in COUNTRY_CODES
    assert "AD" in COUNTRY_CODES
    assert "AQ" in COUNTRY_CODES
    assert "ZA" in COUNTRY_CODES
    assert "XX" not in COUNTRY_CODES
    assert "QQ" not in COUNTRY_CODES
    assert "ZZ" not in COUNTRY_CODES


def test_rule_conventions() -> None:
    assert RULE.name == "Section 5-bic-structure-country"
    assert RULE.strategy is RuleStrategy.PARSER
    assert RULE.strategy.name == "PARSER"
    assert RULE.target_semantics == frozenset({"bic_recognition"})
    assert RULE.requires_features == frozenset()
    assert isinstance(RULE.target_semantics, frozenset)
    assert isinstance(RULE.requires_features, frozenset)


def test_location_second_char_not_rejected() -> None:
    for compact in ["DEUTDE0F", "BARCGB1L", "CHASGB2L", "DEUTDEFF", "BARCGB22"]:
        assert RULE.matches(n(compact), CONTRACT) is True, compact


def test_branch_xxx_preserved() -> None:
    assert RULE.matches(n("NEDSZAJJXXX"), CONTRACT) is True
    assert RULE.normalize(n("NEDSZAJJXXX"), CONTRACT) == "NEDSZAJJXXX"
    assert RULE.matches(n("NEDSZAJJ"), CONTRACT) is True
    assert RULE.normalize(n("NEDSZAJJ"), CONTRACT) == "NEDSZAJJ"


def test_country_codes_exhaustive() -> None:
    # 250 entries: 249 ISO + XK
    assert len(COUNTRY_CODES) == 250
    assert isinstance(COUNTRY_CODES, frozenset)
    # spot checks
    for code in ["AD", "AE", "AF", "AQ", "XK", "ZA", "ZW", "US", "GB", "DE"]:
        assert code in COUNTRY_CODES


def test_no_output_format_token() -> None:
    source = Path("paxman/capabilities/BIC/rules/iso_9362_ed2022.py").read_text(
        encoding="utf-8"
    )
    assert "output_format" not in source


def test_compact_field_consistency_rejected() -> None:
    # compact must equal bank+country+location+branch
    bad = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="",
        compact="DEUTDEFF",
    )
    assert RULE.matches(bad, CONTRACT) is True
    inconsistent = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="500",
        compact="DEUTDEFF",
    )
    assert RULE.matches(inconsistent, CONTRACT) is False
