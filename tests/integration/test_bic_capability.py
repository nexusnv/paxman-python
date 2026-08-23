"""Integration tests for BIC capability — resolution map + pipeline."""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.BIC.capability import BICCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test (shipped ISSN and IBAN pattern)."""
    reset_registry()
    yield
    reset_registry()


class TestBICResolutionMap:
    """Resolution map for BIC (ISO 9362:2022 Section 5)."""

    @pytest.mark.integration
    def test_success_electronic_and_label_same_canonical(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        cases: list[tuple[str, str]] = [
            ("DEUTDEFF", "DEUTDEFF"),
            ("deutdeff", "DEUTDEFF"),
            ("DeUtDeFf500", "DEUTDEFF500"),
            ("BIC: DEUTDEFF", "DEUTDEFF"),
            ("SWIFT: DEUTDEFF500", "DEUTDEFF500"),
            ("BIC DEUTDEFF500", "DEUTDEFF500"),
            ("bic - NEDSZAJJ", "NEDSZAJJ"),
            ("DSBACNBXSHA", "DSBACNBXSHA"),
            ("CHASUS33", "CHASUS33"),
            ("BANKXK22", "BANKXK22"),
            ("CBKIXKPRXXX", "CBKIXKPRXXX"),
        ]
        for txt, expected in cases:
            r = paxman.canonicalize(txt, contract)
            assert r.status == Resolution.SUCCESS, txt
            assert r.canonicalized_value == expected, txt
            assert r.candidates[0].provenance[0].specification_name == "ISO 9362:2022"
            assert r.span is not None
            assert r.candidates[0].recognition_rule == "bic_recognition"
            assert r.candidates[0].validation_rule == "Section 5-bic-structure-country"

    @pytest.mark.integration
    def test_grouped_output_format(self) -> None:
        register_capability(BICCapability())
        r = paxman.canonicalize(
            "DEUTDEFF", BICCapability.create_contract(output_format="grouped")
        )
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DEUT DE FF"
        r2 = paxman.canonicalize(
            "DEUTDEFF500", BICCapability.create_contract(output_format="grouped")
        )
        assert r2.status == Resolution.SUCCESS
        assert r2.canonicalized_value == "DEUT DE FF 500"
        r3 = paxman.canonicalize(
            "BNPAFRPPXXX", BICCapability.create_contract(output_format="grouped")
        )
        assert r3.canonicalized_value == "BNPA FR PP XXX"

    @pytest.mark.integration
    def test_bic11_output_format(self) -> None:
        register_capability(BICCapability())
        r = paxman.canonicalize(
            "DEUTDEFF", BICCapability.create_contract(output_format="bic11")
        )
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DEUTDEFFXXX"
        r2 = paxman.canonicalize(
            "DEUTDEFF500", BICCapability.create_contract(output_format="bic11")
        )
        assert r2.canonicalized_value == "DEUTDEFF500"
        r3 = paxman.canonicalize(
            "BNPAFRPPXXX", BICCapability.create_contract(output_format="bic11")
        )
        assert r3.canonicalized_value == "BNPAFRPPXXX"

    @pytest.mark.integration
    def test_invalid_country_and_charset(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        # invalid country XX, QQ not in ISO 3166-1 plus XK
        assert paxman.canonicalize("DEUTXXFF", contract).status == Resolution.INVALID
        assert paxman.canonicalize("BNPAQQPP", contract).status == Resolution.INVALID
        # digit in country position fails charset (2!a must be A-Z) => grammar MISSING
        assert paxman.canonicalize("DEUT1EFF", contract).status == Resolution.MISSING
        assert paxman.canonicalize("DEUT12FF", contract).status == Resolution.MISSING

    @pytest.mark.integration
    def test_missing_short_and_wrong_length(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        assert paxman.canonicalize("AB12", contract).status == Resolution.MISSING
        assert (
            paxman.canonicalize("DEUTDEF", contract).status == Resolution.MISSING
        )  # 7
        assert (
            paxman.canonicalize("DEUTDEFF5", contract).status == Resolution.MISSING
        )  # 9
        assert (
            paxman.canonicalize("DEUTDEFF50", contract).status == Resolution.MISSING
        )  # 10
        assert (
            paxman.canonicalize("DEUTDEFF5000", contract).status == Resolution.MISSING
        )  # 12
        assert (
            paxman.canonicalize("call me at noon", contract).status
            == Resolution.MISSING
        )

    @pytest.mark.integration
    def test_tail_glue_word_guard(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        assert paxman.canonicalize("XDEUTDEFF", contract).status == Resolution.MISSING
        assert paxman.canonicalize("BICDEUTDEFF", contract).status == Resolution.MISSING
        assert (
            paxman.canonicalize("SWIFTDEUTDEFF500", contract).status
            == Resolution.MISSING
        )
        assert paxman.canonicalize("DEUTDEFFY", contract).status == Resolution.MISSING
        assert (
            paxman.canonicalize("BICDEUTDEFF500", contract).status == Resolution.MISSING
        )

    @pytest.mark.integration
    def test_two_distinct_bics_raise_multiple_mentions(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("DEUTDEFF / BNPAFRPP", contract)
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize("DEUTDEFF / BNPAFRPPXXX", contract)

    @pytest.mark.integration
    def test_span_word_guard(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        assert paxman.canonicalize("XDEUTDEFF", contract).status == Resolution.MISSING
        assert paxman.canonicalize("BICDEUTDEFF", contract).status == Resolution.MISSING
        # Valid span when surrounded by punctuation
        r = paxman.canonicalize('"DEUTDEFF"', contract)
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DEUTDEFF"

    @pytest.mark.integration
    def test_longest_vectors_both_8_and_11(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        for compact in ["DEUTDEFF", "DEUTDEFF500", "BNPAFRPPXXX", "NEDSZAJJXXX"]:
            r = paxman.canonicalize(compact, contract)
            assert r.status == Resolution.SUCCESS, compact
            assert r.canonicalized_value == compact

    @pytest.mark.integration
    def test_year_filter_excludes_rule(self) -> None:
        register_capability(BICCapability())
        contract_2022 = BICCapability.create_contract(year=2022)
        r_2022 = paxman.canonicalize("DEUTDEFF", contract_2022)
        assert r_2022.status == Resolution.SUCCESS
        assert r_2022.canonicalized_value == "DEUTDEFF"

        reset_registry()
        register_capability(BICCapability())
        contract_2021 = BICCapability.create_contract(year=2021)
        r_2021 = paxman.canonicalize("DEUTDEFF", contract_2021)
        assert r_2021.status == Resolution.INVALID
        assert r_2021.canonicalized_value is None
        assert len(r_2021.candidates) == 0

    @pytest.mark.integration
    def test_location_second_char_not_rejected(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        for bic in ["DEUTDE0F", "BARCGB1L", "CHASGB2L"]:
            assert paxman.canonicalize(bic, contract).status == Resolution.SUCCESS, bic

    @pytest.mark.integration
    def test_identical_bics_coalesce_to_success(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        r = paxman.canonicalize("DEUTDEFF and DEUTDEFF", contract)
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DEUTDEFF"

    @pytest.mark.integration
    def test_span_includes_label_when_present(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        txt = "Please remit to BIC DEUTDEFF (bank)"
        r = paxman.canonicalize(txt, contract)
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DEUTDEFF"
        assert r.span is not None
        assert txt[r.span[0] : r.span[1]] == "BIC DEUTDEFF"

    @pytest.mark.integration
    def test_trailing_word_not_part_of_mention(self) -> None:
        register_capability(BICCapability())
        contract = BICCapability.create_contract()
        r = paxman.canonicalize("Pay to DEUTDEFF now", contract)
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DEUTDEFF"
