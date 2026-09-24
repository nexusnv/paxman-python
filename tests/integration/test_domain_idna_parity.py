"""Integration tests for the Domain/IDNA pipeline."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities import Domain
from paxman.capabilities.Domain.capability import DomainCapability
from paxman.capabilities.Domain.rules.iana_root_zone_membership import (
    IanaRootZoneMembership,
)
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestDomainIdnaParity:
    """UTS #46 fixed points, non-transitional pins, and LOOKUP qualification."""

    @pytest.mark.integration
    def test_nfc_nfd_convergence(self) -> None:
        register_capability(DomainCapability())
        contract = Domain.create_contract()
        assert (
            canonicalize("mu\u0308nchen.de", contract).canonicalized_value
            == canonicalize("münchen.de", contract).canonicalized_value
            == "xn--mnchen-3ya.de"
        )

    @pytest.mark.integration
    def test_uts46_mapping_fixed_point(self) -> None:
        register_capability(DomainCapability())
        contract = Domain.create_contract()
        value = canonicalize("münchen.DE.", contract).canonicalized_value
        assert value == "xn--mnchen-3ya.de"
        assert (
            canonicalize(value, Domain.create_contract()).canonicalized_value == value
        )

    @pytest.mark.integration
    def test_non_transitional_sharp_s_pin(self) -> None:
        register_capability(DomainCapability())
        contract = Domain.create_contract()
        assert (
            canonicalize("straße.de", contract).canonicalized_value
            == "xn--strae-oqa.de"
        )
        assert (
            canonicalize("straße.de", contract).canonicalized_value
            != canonicalize("STRASSE.DE", contract).canonicalized_value
        )

    @pytest.mark.integration
    def test_root_zone_provenance_version(self) -> None:
        assert (
            IanaRootZoneMembership.provenance.version == "IANA tlds-alpha v2026092300"
        )
        register_capability(DomainCapability())
        result = canonicalize("example.com", Domain.create_contract())
        assert any(
            "IANA tlds-alpha v2026092300" in str(provenance)
            for candidate in result.candidates
            for provenance in candidate.provenance
        )

    @pytest.mark.integration
    def test_ace_u_label_convergence(self) -> None:
        register_capability(DomainCapability())
        contract = Domain.create_contract()
        assert (
            canonicalize("münchen.de", contract).canonicalized_value
            == canonicalize("XN--MNCHEN-3YA.de", contract).canonicalized_value
            == "xn--mnchen-3ya.de"
        )

    @pytest.mark.integration
    def test_lookup_vacuity_flip(self) -> None:
        register_capability(DomainCapability())
        default = canonicalize("foo.unknowntld-xyz", Domain.create_contract())
        assert default.status == Resolution.INVALID
        assert default.canonicalized_value is None
        vacuous = canonicalize(
            "foo.unknowntld-xyz",
            Domain.create_contract(excluded_rules=("root-zone-membership",)),
        )
        assert vacuous.status == Resolution.SUCCESS
        assert vacuous.canonicalized_value == "foo.unknowntld-xyz"
