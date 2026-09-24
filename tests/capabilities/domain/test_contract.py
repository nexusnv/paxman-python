"""Tests for DomainContract — user-facing configuration."""

import dataclasses

import pytest

from paxman.capabilities.Domain.contract import DomainContract
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestDomainContract:
    """Contract defaults, format resolution, and shipped-scope pins."""

    def test_default_output_format_is_ascii(self) -> None:
        assert DomainContract().output_format == "ascii"

    def test_offered_output_formats_is_unicode(self) -> None:
        assert frozenset({"unicode"}) == DomainContract.OFFERED_OUTPUT_FORMATS

    def test_output_format_resolution_variants(self) -> None:
        from paxman.capabilities.Domain.capability import DomainCapability

        assert DomainCapability.create_contract().output_format == "ascii"
        none_format = DomainCapability.create_contract(output_format=None).output_format
        assert none_format == "ascii"
        assert (
            DomainCapability.create_contract(output_format="default").output_format
            == "ascii"
        )
        assert (
            DomainCapability.create_contract(output_format="ascii").output_format
            == "ascii"
        )
        assert (
            DomainCapability.create_contract(output_format="unicode").output_format
            == "unicode"
        )

    def test_unknown_format_contract_error(self) -> None:
        from paxman.capabilities.Domain.capability import DomainCapability

        with pytest.raises(ContractError):
            DomainCapability.create_contract(output_format="json")

    def test_capability_name_is_domain(self) -> None:
        assert DomainContract().capability_name == "domain"

    def test_contract_is_frozen(self) -> None:
        contract = DomainContract()
        with pytest.raises(dataclasses.FrozenInstanceError):
            contract.output_format = "unicode"  # type: ignore[misc]

    def test_suppress_common_words_default_false(self) -> None:
        assert DomainContract().suppress_common_words is False

    def test_scope_knobs_not_shipped(self) -> None:
        contract = DomainContract()
        assert not hasattr(contract, "allow_single_label")
        assert not hasattr(contract, "allow_underscore")
        assert not hasattr(contract, "transitional")

    def test_unicode_class_encoding_declared(self) -> None:
        import inspect

        paragraphs = (inspect.getdoc(DomainContract) or "").split("\n\n")
        assert sum("unicode" in para and "encoding" in para for para in paragraphs) == 1
        assert all("projection" not in para for para in paragraphs)
