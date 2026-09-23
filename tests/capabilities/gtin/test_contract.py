"""Tests for GTINContract."""

import pytest

from paxman.capabilities.GTIN.contract import GTINContract
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestGTINContract:
    def test_default_gtin14_offered_native_hri(self) -> None:
        c = GTINContract()
        assert c.output_format == "gtin14"
        assert GTINContract.DEFAULT_OUTPUT_FORMAT == "gtin14"
        # hri deferred (Task 6): EAN-13/GTIN-14 groupings unconfirmed.
        assert frozenset({"native"}) == GTINContract.OFFERED_OUTPUT_FORMATS
        assert GTINContract(output_format="native").output_format == "native"

    def test_include_verified_default_false(self) -> None:
        assert GTINContract().include_verified is False
        assert GTINContract(include_verified=True).include_verified is True

    def test_unknown_format_contract_error(self) -> None:
        with pytest.raises(ContractError):
            GTINContract(output_format="bogus")

    def test_suppress_common_words_default_false(self) -> None:
        assert GTINContract().suppress_common_words is False

    def test_adr0011_classes_declared(self) -> None:
        doc = GTINContract.__doc__ or ""
        # native is an encoding, not an expansion: GTIN has one canonical
        # per entity, so no two distinct canonicals exist for an
        # expansion to merge (ADR-0011 Definitions).
        assert "native" in doc and "encoding" in doc
        assert "expansion" not in doc
