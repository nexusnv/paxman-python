"""Tests for BIC capability wiring, create_contract, and format_value."""

from __future__ import annotations

import pytest

from paxman.capabilities.BIC.capability import BICCapability
from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]

CAP = BICCapability()


def test_wiring_counts() -> None:
    assert CAP.name == "bic"
    assert CAP.version == "1.0.0"
    assert len(CAP.get_grammars()) == 1
    assert CAP.get_grammars()[0].name == "bic_recognition"
    assert len(CAP.get_rules()) == 1
    assert CAP.get_rules()[0].name == "Section 5-bic-structure-country"


def test_create_contract_defaults() -> None:
    c = CAP.create_contract()
    assert c.output_format == "bic"
    assert c.capability_name == "bic"
    assert c.excluded_rules == ()
    assert c.pinned_rules is None
    assert c.extra_grammars == ()


def test_create_contract_output_format() -> None:
    # offered formats succeed
    c_grouped = CAP.create_contract(output_format="grouped")
    assert c_grouped.output_format == "grouped"
    c_bic11 = CAP.create_contract(output_format="bic11")
    assert c_bic11.output_format == "bic11"
    # bic/default aliases resolve to bic
    for alias in (None, "default", "bic"):
        c = CAP.create_contract(output_format=alias)
        assert c.output_format == "bic"
    # invalid formats raise ContractError
    with pytest.raises(ContractError):
        CAP.create_contract(output_format="hyphenated")
    with pytest.raises(ContractError):
        CAP.create_contract(output_format="paper")
    with pytest.raises(ContractError):
        CAP.create_contract(output_format="compact")


def test_format_value_grouped() -> None:
    cases: dict[str, str] = {
        "DEUTDEFF": "DEUT DE FF",
        "DEUTDEFF500": "DEUT DE FF 500",
        "BNPAFRPP": "BNPA FR PP",
        "BNPAFRPPXXX": "BNPA FR PP XXX",
        "CHASUS33": "CHAS US 33",
        "NEDSZAJJXXX": "NEDS ZA JJ XXX",
    }
    for bic, grouped in cases.items():
        n = BICNotation(
            bank_code=bic[0:4],
            country_code=bic[4:6],
            location_code=bic[6:8],
            branch_code=bic[8:11] if len(bic) == 11 else "",
            compact=bic,
        )
        assert CAP.format_value(bic, "grouped", n) == grouped
        # identity paths remain unchanged
        assert CAP.format_value(bic, None, n) == bic
        assert CAP.format_value(bic, "bic", n) == bic


def test_format_value_bic11() -> None:
    # 8 -> 11 lossy expansion appending XXX
    for bic8, bic11 in [
        ("DEUTDEFF", "DEUTDEFFXXX"),
        ("BNPAFRPP", "BNPAFRPPXXX"),
        ("NEDSZAJJ", "NEDSZAJJXXX"),
    ]:
        n = BICNotation(
            bank_code=bic8[0:4],
            country_code=bic8[4:6],
            location_code=bic8[6:8],
            branch_code="",
            compact=bic8,
        )
        assert CAP.format_value(bic8, "bic11", n) == bic11
    # already 11 stays identity (notation must match value)
    n2 = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="500",
        compact="DEUTDEFF500",
    )
    assert CAP.format_value("DEUTDEFF500", "bic11", n2) == "DEUTDEFF500"
    n3 = BICNotation(
        bank_code="BNPA",
        country_code="FR",
        location_code="PP",
        branch_code="XXX",
        compact="BNPAFRPPXXX",
    )
    assert CAP.format_value("BNPAFRPPXXX", "bic11", n3) == "BNPAFRPPXXX"


def test_format_value_identity() -> None:
    n = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="",
        compact="DEUTDEFF",
    )
    assert CAP.format_value("DEUTDEFF", "bic", n) == "DEUTDEFF"
    assert CAP.format_value("DEUTDEFF", None, n) == "DEUTDEFF"
    # default alias identity via contract resolution; unknown as identity
    assert CAP.format_value("DEUTDEFF", "default", n) == "DEUTDEFF"
