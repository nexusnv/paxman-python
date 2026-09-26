"""Tests for ISNIContract."""

import pytest

from paxman.capabilities.ISNI.capability import ISNICapability
from paxman.capabilities.ISNI.contract import ISNIContract
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestISNIContract:
    """Contract defaults, offered formats, and common-block forwarding."""

    def test_defaults(self) -> None:
        contract = ISNIContract()
        assert contract.capability_name == "isni"
        assert contract.output_format == "isni"
        assert contract.excluded_rules == ()
        assert contract.pinned_rules is None
        assert contract.year is None
        assert contract.extra_grammars == ()
        assert contract.suppress_common_words is False

    def test_offered_formats(self) -> None:
        assert ISNIContract.DEFAULT_OUTPUT_FORMAT == "isni"
        assert frozenset({"compact", "urn"}) == ISNIContract.OFFERED_OUTPUT_FORMATS
        assert (
            ISNICapability.create_contract(output_format="compact").output_format
            == "compact"
        )
        assert (
            ISNICapability.create_contract(output_format="urn").output_format == "urn"
        )

    def test_rejects_unknown_format(self) -> None:
        with pytest.raises(ContractError):
            ISNICapability.create_contract(output_format="bogus")

    def test_forwards_common_block(self) -> None:
        contract = ISNICapability.create_contract(
            excluded_rules=("Section 4-isni-structure",),
            year=2024,
            suppress_common_words=True,
        )
        assert contract.excluded_rules == ("Section 4-isni-structure",)
        assert contract.year == 2024
        assert contract.suppress_common_words is True
