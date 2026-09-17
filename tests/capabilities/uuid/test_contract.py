"""Tests for UUIDContract (RFC 9562 presentation seam)."""

import pytest

from paxman.capabilities.UUID.capability import UUIDCapability
from paxman.capabilities.UUID.contract import UUIDContract
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestUUIDContract:
    """Hyphenated default; compact/braced/urn offered; rest rejected."""

    def test_default_hyphenated_offered_three(self) -> None:
        assert UUIDContract.DEFAULT_OUTPUT_FORMAT == "hyphenated"
        offered = UUIDContract.OFFERED_OUTPUT_FORMATS
        assert offered == frozenset({"compact", "braced", "urn"})
        contract = UUIDCapability.create_contract()
        assert contract.output_format == "hyphenated"

    def test_offered_formats_resolve(self) -> None:
        for fmt in ("compact", "braced", "urn"):
            contract = UUIDCapability.create_contract(output_format=fmt)
            assert contract.output_format == fmt

    def test_unknown_format_contract_error(self) -> None:
        with pytest.raises(ContractError):
            UUIDCapability.create_contract(output_format="upper")
