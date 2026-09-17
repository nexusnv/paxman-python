"""Tests for the UUID capability wiring (RFC 9562)."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.UUID.capability import UUIDCapability
from paxman.capabilities.UUID.contract import UUIDContract
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.engine.orchestrator import ExecutionResult


@pytest.mark.capability
class TestUUIDCapability:
    """Capability wiring — grammars, rules, factory, formats."""

    def setup_method(self) -> None:
        self.capability = UUIDCapability()

    def test_metadata(self) -> None:
        assert self.capability.name == "uuid"

    def test_get_grammars(self) -> None:
        grammars = self.capability.get_grammars()
        assert [g.name for g in grammars] == ["uuid_recognition"]
        assert all(g.semantics == "uuid_recognition" for g in grammars)

    def test_get_rules(self) -> None:
        assert [r.name for r in self.capability.get_rules()] == [
            "Section 4-uuid-format"
        ]

    def test_create_contract_defaults(self) -> None:
        contract = self.capability.create_contract()
        assert isinstance(contract, UUIDContract)
        assert contract.output_format == "hyphenated"


@pytest.mark.capability
class TestUUIDCapabilityPipeline:
    """End-to-end: carriers resolve; format outputs re-enter (ADR-0010)."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self) -> None:
        reset_registry()
        register_capability(UUIDCapability())
        yield
        reset_registry()

    def _canonicalize(
        self, text: str, output_format: str | None = None
    ) -> ExecutionResult:
        return canonicalize(
            text, UUIDCapability.create_contract(output_format=output_format)
        )

    def test_hyphenated_success(self) -> None:
        result = self._canonicalize("6ba7b810-9dad-11d1-80b4-00c04fd430c8")
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    def test_format_value_round_trips(self) -> None:
        """Every offered format re-enters as a fixed point (ADR-0010)."""
        expected = {
            "compact": "6ba7b8109dad11d180b400c04fd430c8",
            "braced": "{6ba7b810-9dad-11d1-80b4-00c04fd430c8}",
            "urn": "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        }
        for fmt, value in expected.items():
            result = self._canonicalize("6ba7b810-9dad-11d1-80b4-00c04fd430c8", fmt)
            assert result.status == Resolution.SUCCESS
            assert result.canonicalized_value == value
            reentry = self._canonicalize(value)
            assert reentry.status == Resolution.SUCCESS
            assert reentry.canonicalized_value == "6ba7b810-9dad-11d1-80b4-00c04fd430c8"

    def test_probe_missing(self) -> None:
        result = self._canonicalize("scaffold probe")
        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
