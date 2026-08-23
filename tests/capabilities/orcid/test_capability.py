"""ORCID capability wiring — ORCIDCapability + format_value seam."""

import pytest

from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestORCIDCapability:
    def test_capability_name_version(self) -> None:
        assert ORCIDCapability.name == "orcid"
        assert ORCIDCapability.version == "1.0.0"

    def test_get_grammars(self) -> None:
        grammars = ORCIDCapability().get_grammars()
        assert len(grammars) == 1
        assert {g.name for g in grammars} == {"orcid_recognition"}

    def test_get_rules(self) -> None:
        rules = ORCIDCapability().get_rules()
        assert len(rules) == 2
        assert {r.name for r in rules} == {
            "Section 4-orcid-structure",
            "Section A-mod11-2-check-character",
        }

    def test_create_contract_defaults(self) -> None:
        c = ORCIDCapability.create_contract()
        assert c.output_format == "orcid"
        assert c.capability_name == "orcid"
        assert c.excluded_rules == ()
        assert c.pinned_rules is None
        assert c.year is None
        assert c.extra_grammars == ()
        assert c.active_grammars is None  # no gating: engine runs all shipped

    def test_create_contract_output_formats(self) -> None:
        assert (
            ORCIDCapability.create_contract(output_format="uri").output_format == "uri"
        )
        assert (
            ORCIDCapability.create_contract(output_format="compact").output_format
            == "compact"
        )
        with pytest.raises(ContractError):
            ORCIDCapability.create_contract(output_format="isni")

    def test_format_value_default_identity(self) -> None:
        cap = ORCIDCapability()
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert cap.format_value("0000-0002-1825-0097", None, notation) == (
            "0000-0002-1825-0097"
        )
        assert cap.format_value("0000-0002-1825-0097", "default", notation) == (
            "0000-0002-1825-0097"
        )
        assert cap.format_value("0000-0002-1825-0097", "orcid", notation) == (
            "0000-0002-1825-0097"
        )

    def test_format_value_uri_always_https(self) -> None:
        cap = ORCIDCapability()
        notation = ORCIDNotation(
            compact="000000021694233X",
            hyphenated="0000-0002-1694-233X",
            uri="https://orcid.org/0000-0002-1694-233X",
            check="X",
            is_uri="true",
        )
        assert cap.format_value("0000-0002-1694-233X", "uri", notation) == (
            "https://orcid.org/0000-0002-1694-233X"
        )

    def test_format_value_compact(self) -> None:
        cap = ORCIDCapability()
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert cap.format_value("0000-0002-1825-0097", "compact", notation) == (
            "0000000218250097"
        )
