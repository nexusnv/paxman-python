"""Tests for DOIContract (bare-doi default, url offered)."""

import pytest

from paxman.capabilities.DOI.capability import DOICapability
from paxman.capabilities.DOI.contract import DOIContract
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestDOIContract:
    """Bare-doi default; url offered; rest rejected."""

    def test_default_doi_offered_url(self) -> None:
        assert DOIContract.DEFAULT_OUTPUT_FORMAT == "doi"
        offered = DOIContract.OFFERED_OUTPUT_FORMATS
        assert offered == frozenset({"url"})
        contract = DOICapability.create_contract()
        assert contract.output_format == "doi"

    def test_offered_format_resolves(self) -> None:
        contract = DOICapability.create_contract(output_format="url")
        assert contract.output_format == "url"

    def test_unknown_format_contract_error(self) -> None:
        with pytest.raises(ContractError):
            DOICapability.create_contract(output_format="upper")
