"""Integration tests for Coordinates capability through the full pipeline."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from paxman.api import canonicalize
from paxman.capabilities.Coordinates.capability import CoordinatesCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry() -> Iterator[None]:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestCoordinatesPipeline:
    """Full-pipeline tests for the Coordinates capability."""

    @pytest.mark.integration
    def test_success_decimal_pair(self) -> None:
        """Decimal pair resolves to canonical lat-first decimal."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        text = "48.8577, 2.295"
        result = canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "48.8577, 2.295"
        assert result.span is not None
        assert len(result.candidates) >= 1
        # span-bearing
        start, end = result.span
        assert 0 <= start < end <= len(text)
        assert (
            end - start == len(result.candidates[0].value)
            or text[start:end] == text[result.span[0] : result.span[1]]
        )
        assert text[result.span[0] : result.span[1]] == "48.8577, 2.295"
        # provenance lists ISO (and IETF is valid for other shapes)
        authorities = {p.authority for c in result.candidates for p in c.provenance}
        assert "ISO" in authorities
        assert authorities <= {"ISO", "IETF"}
        # candidate span matches result span
        assert result.candidates[0].span == result.span

    @pytest.mark.integration
    def test_success_dms_coalesces_with_decimal(self) -> None:
        """Same point in decimal and DMS spellings dedups to one candidate."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        # 48.8577 = 48°51′27.72″N ; 2.295 = 2°17′42″E  (quantized to 6dp)
        text = "48.8577,2.295 and 48°51′27.72″N, 2°17′42″E"
        result = canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "48.8577, 2.295"
        # dedup: same canonical value from two spellings collapses to one candidate
        assert len(result.candidates) == 1
        assert result.candidates[0].value == "48.8577, 2.295"
        assert {p.authority for p in result.candidates[0].provenance} == {"ISO"}

    @pytest.mark.integration
    def test_success_geojson_input(self) -> None:
        """Lon-first GeoJSON pair flips to lat-first canonical."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        text = "[2.295, 48.8577]"
        result = canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "48.8577, 2.295"
        assert result.span == (0, len(text))
        assert text[result.span[0] : result.span[1]] == text
        authorities = {p.authority for c in result.candidates for p in c.provenance}
        assert "IETF" in authorities
        assert result.candidates[0].provenance[0].specification_name == "RFC 7946"

    @pytest.mark.integration
    def test_success_geo_uri_input(self) -> None:
        """Geo URI 2-D resolves to decimal canonical."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        text = "geo:48.8566,2.3522"
        result = canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "48.8566, 2.3522"
        assert result.span == (0, len(text))
        assert result.candidates[0].provenance[0].specification_name == "RFC 5870"
        assert result.candidates[0].provenance[0].authority == "IETF"

    @pytest.mark.integration
    def test_success_iso_input(self) -> None:
        """ISO 6709 string expression with trailing solidus resolves."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        text = "+48.52+002.20/"
        result = canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "48.52, 2.2"
        assert result.span == (0, len(text))
        authorities = {p.authority for c in result.candidates for p in c.provenance}
        assert "ISO" in authorities

    @pytest.mark.integration
    def test_invalid_out_of_range(self) -> None:
        """Latitude > 90 is recognized but no rule validates → INVALID."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        result = canonicalize("geo:94,0", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_invalid_hemisphere_contradiction(self) -> None:
        """Sign and hemisphere that contradict is INVALID (grammar sentinel + range)."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        result = canonicalize("-41.5 N, 2.295", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_invalid_foreign_crs(self) -> None:
        """Foreign CRS label is encoded as 91 sentinel so rule reports INVALID."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        result = canonicalize("+27.59+002.29CRSPS56/", contract)

        assert result.status == Resolution.INVALID
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_missing_single_component(self) -> None:
        """A single latitude without longitude is not recognized → MISSING."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        result = canonicalize("48.8566", contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    @pytest.mark.parametrize(
        "text",
        ["$48.86", "48.86 kg", "2024-09-01"],
    )
    def test_missing_sibling_shapes(self, text: str) -> None:
        """Sibling capability shapes are MISSING for coordinates."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        result = canonicalize(text, contract)

        assert result.status == Resolution.MISSING
        assert result.canonicalized_value is None
        assert result.candidates == ()

    @pytest.mark.integration
    def test_ambiguous_two_distinct_points(self) -> None:
        """Two distinct WGS 84 points in one slice raise MultipleMentionsError."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        with pytest.raises(MultipleMentionsError):
            canonicalize("48.8577,2.295 and 40.7128,-74.0060", contract)

    @pytest.mark.integration
    def test_determinism_version_stamp(self) -> None:
        """Same input twice yields identical version_stamp."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        a = canonicalize("48.8577, 2.295", contract)
        b = canonicalize("48.8577, 2.295", contract)

        assert a.status == b.status == Resolution.SUCCESS
        assert a.canonicalized_value == b.canonicalized_value == "48.8577, 2.295"
        assert a.version_stamp == b.version_stamp
        assert a.version_stamp.paxman_version == b.version_stamp.paxman_version
        assert (
            a.version_stamp.recognition_revision == b.version_stamp.recognition_revision
        )
        assert isinstance(a.version_stamp.paxman_version, str)
        assert isinstance(a.version_stamp.recognition_revision, str)

    @pytest.mark.integration
    def test_output_format_geojson_round_trip(self) -> None:
        """Decimal canonical with geojson_pair output emits lon-first bracketed pair."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract(output_format="geojson_pair")
        result = canonicalize("48.8577, 2.295", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "[2.295, 48.8577]"
        assert result.contract.output_format == "geojson_pair"
        # candidates carry the formatted value, provenance still present
        assert len(result.candidates) == 1
        assert result.candidates[0].value == "[2.295, 48.8577]"

    @pytest.mark.integration
    def test_output_format_iso6709(self) -> None:
        """Decimal canonical with iso6709 output emits signed padded ISO 6709 string."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract(output_format="iso6709")
        result = canonicalize("48.8577, 2.295", contract)

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+48.8577+002.295/"
        assert result.contract.output_format == "iso6709"

    @pytest.mark.integration
    def test_span_half_open(self) -> None:
        """ExecutionResult span is half-open and raw_text equals slice."""
        register_capability(CoordinatesCapability())
        contract = CoordinatesCapability.create_contract()
        text = "prefix 48.8577, 2.295 suffix"
        result = canonicalize(text, contract)

        assert result.status == Resolution.SUCCESS
        assert result.span is not None
        start, end = result.span
        # half-open invariants
        assert 0 <= start < end <= len(text)
        assert end - start == len(text[start:end])
        # raw_text equality: slice equals the decimal pair (with exact input spelling)
        assert text[start:end] == "48.8577, 2.295"
        assert len(text[start:end]) == end - start
        # candidate span mirrors result span for single-value SUCCESS
        assert result.candidates[0].span == result.span
        assert result.candidates[0].span is not None
        cs, ce = result.candidates[0].span  # type: ignore[union-attr]
        assert text[cs:ce] == "48.8577, 2.295"
