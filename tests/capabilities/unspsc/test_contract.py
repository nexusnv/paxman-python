"""Tests for UNSPSCContract."""

import pytest

from paxman.capabilities.UNSPSC.capability import UNSPSCCapability
from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestUNSPSCContract:
    """Contract defaults, offered formats, and feature flags."""

    def test_defaults(self) -> None:
        contract = UNSPSCContract()
        assert contract.capability_name == "unspsc"
        assert contract.output_format == "unspsc"
        assert contract.excluded_rules == ()
        assert contract.pinned_rules is None
        assert contract.year is None
        assert contract.extra_grammars == ()
        assert contract.include_business_function is True

    def test_inherits_capability_contract(self) -> None:
        assert issubclass(UNSPSCContract, CapabilityContract)
        assert UNSPSCContract.__dataclass_params__.frozen is True
        assert "__slots__" not in UNSPSCContract.__dict__
        contract = UNSPSCContract()
        assert isinstance(contract, CapabilityContract)
        assert "__dict__" in dir(contract)

    def test_offered_formats(self) -> None:
        assert UNSPSCContract.DEFAULT_OUTPUT_FORMAT == "unspsc"
        assert frozenset({"labeled", "native"}) == (
            UNSPSCContract.OFFERED_OUTPUT_FORMATS
        )
        assert "unspsc" not in UNSPSCContract.OFFERED_OUTPUT_FORMATS
        assert (
            UNSPSCCapability.create_contract(output_format="labeled").output_format
            == "labeled"
        )
        assert (
            UNSPSCCapability.create_contract(output_format="native").output_format
            == "native"
        )

    def test_segmented_not_offered(self) -> None:
        with pytest.raises(ContractError):
            UNSPSCCapability.create_contract(output_format="segmented")

    def test_rejects_unknown_format(self) -> None:
        with pytest.raises(ContractError):
            UNSPSCCapability.create_contract(output_format="bogus")

    def test_forwards_common_block_and_flags(self) -> None:
        contract = UNSPSCCapability.create_contract(
            excluded_rules=("Section 1-hierarchy-structure",),
            year=2023,
            include_business_function=False,
        )
        assert contract.excluded_rules == ("Section 1-hierarchy-structure",)
        assert contract.year == 2023
        assert contract.include_business_function is False
