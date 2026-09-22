"""Tests for the GTIN capability wiring."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.GTIN.capability import GTINCapability
from paxman.capabilities.GTIN.contract import GTINContract
from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.mark.capability
class TestGTINCapability:
    def setup_method(self) -> None:
        self.capability = GTINCapability()

    def test_wiring_counts(self) -> None:
        assert [g.name for g in self.capability.get_grammars()] == ["gtin_recognition"]
        assert [r.name for r in self.capability.get_rules()] == [
            "Section 1-gtin-structure-check-digit",
            "Section 2-gs1-prefix",
            "Section 3-verified-liveness",
        ]

    def test_create_contract_common_block(self) -> None:
        c = self.capability.create_contract(
            excluded_rules=["x"],
            pinned_rules=None,
            year=2026,
            output_format="native",
            extra_grammars=[],
            suppress_common_words=True,
            include_verified=True,
        )
        assert isinstance(c, GTINContract)
        assert c.excluded_rules == ("x",)
        assert c.year == 2026
        assert c.output_format == "native"
        assert c.suppress_common_words is True
        assert c.include_verified is True

    def test_format_native(self) -> None:
        # 14-char canonical -> native spelling via the facet slice
        # value[14 - native_length:] (as-spelled-length rendering).
        n12 = GTINNotation("614141999996", 12, False)
        assert (
            self.capability.format_value("00614141999996", "native", n12)
            == "614141999996"
        )
        # true-14 identity: no padding to strip
        n14 = GTINNotation("10614141999993", 14, False)
        assert (
            self.capability.format_value("10614141999993", "native", n14)
            == "10614141999993"
        )

    def test_shipped_contains_gtin(self) -> None:
        from paxman.api.bootstrap import list_shipped_capabilities

        assert "gtin" in list_shipped_capabilities()

    def test_cli_gtin_branch(self) -> None:
        from paxman.cli import _create_contract

        c = _create_contract("gtin", False)
        assert isinstance(c, GTINContract)


@pytest.mark.capability
class TestGTINCapabilityPipeline:
    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        yield
        reset_registry()

    def test_pipeline_success(self) -> None:
        register_capability(GTINCapability())
        contract = GTINCapability.create_contract()
        result = canonicalize("5012345670003", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "05012345670003"

    def test_pipeline_upca_flagship(self) -> None:
        # UPC-A flagship: 12-digit spelling canonicalizes to its 14-char
        # padded form; prefix resolves via the EAN-13 view (061, GS1 US).
        register_capability(GTINCapability())
        contract = GTINCapability.create_contract()
        result = canonicalize("614141999996", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "00614141999996"
