"""MinorPlanet pipeline integration tests."""

import pytest

from paxman.api import canonicalize
from paxman.capabilities.MinorPlanet.capability import MinorPlanetCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    reset_registry()
    yield
    reset_registry()


@pytest.mark.integration
class TestMinorPlanetPipeline:
    """End-to-end resolution states per research §§8–9."""

    def setup_method(self) -> None:
        register_capability(MinorPlanetCapability())

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("1995 XA", "1995 XA"),
            ("2007 TA418", "2007 TA418"),
            ("2003 cp20", "2003 CP20"),
            ("1995_XA", "1995 XA"),
            ("A904 OA", "A904 OA"),
            ("A/2017 U1", "A/2017 U1"),
            ("J95X00A", "1995 XA"),
            ("K07Tf8A", "2007 TA418"),
            ("2040 P-L", "2040 P-L"),
            ("PLS2040", "2040 P-L"),
            ("3138 T-1", "3138 T-1"),
            ("T1S3138", "3138 T-1"),
            ("(433)", "(433)"),
            ("(274301)", "(274301)"),
            ("(433) Eros", "(433)"),
            ("03202", "(3202)"),
            ("A0345", "(100345)"),
            ("a0017", "(360017)"),
            ("~000z", "(620061)"),
            ("see 1995 XA (Alcathoe)", "1995 XA"),
        ],
    )
    def test_success(self, text: str, expected: str) -> None:
        result = canonicalize(text, MinorPlanetCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected

    @pytest.mark.parametrize(
        "text",
        [
            "1995 XI",
            "1995 IZ",
            "J95I00A",
            "(0433)",
            "(0)",
            "00000",  # packed-number zero: no valid permanent number
            "1995 XA0",  # degenerate cycle digits (leading zero)
            "2007 TA05",
        ],
    )
    def test_invalid(self, text: str) -> None:
        result = canonicalize(text, MinorPlanetCapability.create_contract())
        assert result.status == Resolution.INVALID

    @pytest.mark.parametrize(
        "text",
        [
            "1995XA",
            "433",
            "1892 A",
            "C/1995 O1",
            "Eros",
            "1995 SA₁",
            "Q95X00A",
            "no designations",
        ],
    )
    def test_missing(self, text: str) -> None:
        result = canonicalize(text, MinorPlanetCapability.create_contract())
        assert result.status == Resolution.MISSING

    def test_two_distinct_mentions_raise(self) -> None:
        with pytest.raises(MultipleMentionsError):
            canonicalize(
                "1997 RO4 = 2007 FK34", MinorPlanetCapability.create_contract()
            )

    def test_packed_unpacked_same_value_dedups(self) -> None:
        # Same entity, two encodings in one slice: one cluster, one value.
        result = canonicalize(
            "J95X00A = 1995 XA", MinorPlanetCapability.create_contract()
        )
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "1995 XA"

    def test_packed_format_roundtrip(self) -> None:
        packed_contract = MinorPlanetCapability.create_contract(output_format="packed")
        result = canonicalize("1995 XA", packed_contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "J95X00A"
        reentry = canonicalize("J95X00A", MinorPlanetCapability.create_contract())
        assert reentry.status == Resolution.SUCCESS
        assert reentry.canonicalized_value == "1995 XA"

    def test_deterministic_version_stamp(self) -> None:
        contract = MinorPlanetCapability.create_contract()
        first = canonicalize("1995 XA", contract)
        second = canonicalize("1995 XA", contract)
        assert first.canonicalized_value == second.canonicalized_value
        assert first.version_stamp == second.version_stamp
        assert first.span == (0, 7)

    def test_known_overclaims_documented(self) -> None:
        # v1 overclaims without a registry (research §4.4): phone area
        # codes and bare 5-digit runs match shape lanes. The future
        # MPCORB LOOKUP_TABLE disambiguates; caller segments these contexts.
        phone = canonicalize("(555) 123-4567", MinorPlanetCapability.create_contract())
        assert phone.status == Resolution.SUCCESS
        assert phone.canonicalized_value == "(555)"
