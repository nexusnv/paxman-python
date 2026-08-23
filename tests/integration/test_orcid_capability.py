"""Integration tests for ORCID capability — resolution map + pipeline."""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test."""
    reset_registry()
    yield
    reset_registry()


def _contract(**kwargs: object):
    return ORCIDCapability.create_contract(**kwargs)


class TestORCIDResolutionMap:
    @pytest.mark.integration
    def test_bare_hyphenated_success(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-0097", _contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"
        assert len(result.candidates) == 2  # dual provenance, same value
        assert {c.validation_rule for c in result.candidates} == {
            "Section 4-orcid-structure",
            "Section A-mod11-2-check-character",
        }
        for candidate in result.candidates:
            assert candidate.recognition_rule == "orcid_recognition"
            assert candidate.provenance[0].specification_name == "ISO 27729:2024"
            assert candidate.span == (0, 19)
        assert result.span == (0, 19)

    @pytest.mark.integration
    def test_uri_input_same_canonical(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "https://orcid.org/0000-0002-1825-0097", _contract()
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"
        assert result.span == (0, len("https://orcid.org/0000-0002-1825-0097"))

    @pytest.mark.integration
    def test_label_input_span_includes_label(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("ORCID: 0000-0002-1825-0097", _contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"
        assert result.span == (0, len("ORCID: 0000-0002-1825-0097"))

    @pytest.mark.integration
    def test_lowercase_x_success_upper(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1694-233x", _contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1694-233X"

    @pytest.mark.integration
    def test_invalid_checksum_invalid(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-0098", _contract())

        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_underlong_missing(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-009", _contract())

        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_compact_digits_missing_v1(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000000218250097", _contract())

        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_two_distinct_mentions_raise(self) -> None:
        register_capability(ORCIDCapability())
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(
                "0000-0002-1825-0097 and 0000-0001-5109-3700", _contract()
            )

    @pytest.mark.integration
    def test_identical_mentions_coalesce_success(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "0000-0002-1825-0097 and 0000-0002-1825-0097", _contract()
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"

    @pytest.mark.integration
    def test_temporal_filter_drops_rules(self) -> None:
        """year < 2024 drops both rules -> recognized but INVALID."""
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-0097", _contract(year=2023))

        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_output_format_uri_rendering(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "0000-0002-1825-0097", _contract(output_format="uri")
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "https://orcid.org/0000-0002-1825-0097"

    @pytest.mark.integration
    def test_output_format_compact_rendering(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "https://orcid.org/0000-0002-1694-233X", _contract(output_format="compact")
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "000000021694233X"

    @pytest.mark.integration
    def test_register_all_shipped_includes_orcid(self) -> None:
        names = paxman.register_all_shipped()
        assert "orcid" in names
        assert names.index("money") < names.index("orcid") < names.index("phone")
