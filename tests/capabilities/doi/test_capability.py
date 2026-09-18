"""Tests for the DOI capability wiring (ISO 26324:2025)."""

import pytest

from paxman.api.bootstrap import list_shipped_capabilities
from paxman.capabilities.DOI.capability import DOICapability
from paxman.capabilities.DOI.contract import DOIContract
from paxman.capabilities.DOI.grammar.doi_recognition import (
    DOIRecognitionGrammar,
)
from paxman.capabilities.DOI.notation import DOINotation


@pytest.mark.capability
class TestDOICapability:
    """Capability wiring — grammars, rules, factory, formats."""

    def setup_method(self) -> None:
        self.capability = DOICapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "doi"

    def test_wiring_counts(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["doi_recognition"]
        assert all(g.semantics == "doi_recognition" for g in grammars)
        assert [r.name for r in self.capability.get_rules()] == ["Section 4-doi-syntax"]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, DOIContract)
        assert contract.output_format == "doi"

    def test_format_value_default_identity(self) -> None:
        notation = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        assert (
            self.capability.format_value("10.1038/nature12345", None, notation)
            == "10.1038/nature12345"
        )

    def test_format_value_url(self) -> None:
        notation = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        assert (
            self.capability.format_value("10.1038/nature12345", "url", notation)
            == "https://doi.org/10.1038/nature12345"
        )

    def test_format_value_url_reenters(self) -> None:
        # ADR-0010: the offered url output re-recognizes under the grammar.
        notation = DOINotation(
            prefix="10.1038",
            suffix="nature12345",
            canonical="10.1038/nature12345",
        )
        rendered = self.capability.format_value("10.1038/nature12345", "url", notation)
        results = DOIRecognitionGrammar().recognize(rendered)
        assert len(results) == 1
        assert results[0].notation == notation

    def test_cli_doi_branch(self) -> None:
        from paxman.cli import _create_contract

        contract = _create_contract("doi")
        assert contract.capability_name == "doi"
        assert contract.output_format == "doi"

    def test_shipped_contains_doi(self) -> None:
        assert "doi" in list_shipped_capabilities()
