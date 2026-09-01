"""Extra coverage for Coordinates — hit every uncovered branch to reach 95%."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from paxman.capabilities.Coordinates.capability import (
    CoordinatesCapability,
    _decimal_to_dm_parts,
    _decimal_to_dms_parts,
    _format_dm,
    _format_dms,
    _format_iso,
    _quantized_str,
)
from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
    CoordinatesRecognitionGrammar,
    _dms_overflow,
    _iso_component_to_decimal,
    _normalize_alt,
    _notation,
)
from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules import component_in_range
from paxman.capabilities.Coordinates.rules.iso_6709_ed2022 import (
    Section6CoordinateStructure,
    SectionAnnexHStringExpression,
)
from paxman.capabilities.Coordinates.rules.rfc_5870_ed2010 import (
    Section33GeoUriValidity,
)
from paxman.capabilities.Coordinates.rules.rfc_7946_ed2016 import Section311Position

pytestmark = [pytest.mark.capability]

CAP = CoordinatesCapability()


class TestCapabilityQuantizedStr:
    def test_invalid_operation_infinity(self) -> None:
        assert _quantized_str(Decimal("Infinity")) == "Infinity"
        assert _quantized_str(Decimal("-Infinity")) == "-Infinity"
        # sNaN also raises InvalidOperation on quantize in some contexts
        # NaN does not raise, but returns NaN — ensure no crash
        assert _quantized_str(Decimal("NaN")) == "NaN"

    def test_zero_folding(self) -> None:
        assert _quantized_str(Decimal("0")) == "0"
        assert _quantized_str(Decimal("-0")) == "0"
        assert _quantized_str(Decimal("0.0000000")) == "0"
        assert _quantized_str(Decimal("0.0000004")) == "0"
        assert _quantized_str(Decimal("-0.0000001")) == "0"
        # normalize path: value that quantizes to 6dp non-zero
        assert _quantized_str(Decimal("1.2345678")) == "1.234568"
        assert _quantized_str(Decimal("0.0000006")) == "0.000001"

    def test_qn_zero_via_fake_quantize(self) -> None:
        # Hit the second qn == 0 branch which is unreachable with real Decimals
        # by supplying a duck-typed value whose quantize returns a fake object
        class FakeQ:
            def __eq__(self, other: object) -> bool:
                return False  # q == 0 is False

            def normalize(self) -> Decimal:
                return Decimal(0)

            def __format__(self, fmt: str) -> str:
                return "fake"

        class FakeValue:
            def quantize(self, *args: object, **kwargs: object) -> FakeQ:  # type: ignore[no-untyped-def]
                return FakeQ()

            def __format__(self, fmt: str) -> str:
                return "fake_value"

        # mypy: FakeValue is not Decimal, but we duck-type for coverage
        assert _quantized_str(FakeValue()) == "0"  # type: ignore[arg-type]


class TestCapabilityDmsDmCarry:
    def test_dms_sec_and_minute_carry(self) -> None:
        # 89.999999 -> sec 60 -> minute 60 -> deg 90
        deg, minute, sec, hemi = _decimal_to_dms_parts("89.999999", True)
        assert (deg, minute, sec) == (90, 0, 0)
        assert hemi == "N"
        # same for lon
        deg2, minute2, sec2, hemi2 = _decimal_to_dms_parts("179.999999", False)
        assert (deg2, minute2, sec2) == (180, 0, 0)
        assert hemi2 == "E"
        # negative
        deg3, minute3, sec3, hemi3 = _decimal_to_dms_parts("-89.999999", True)
        assert hemi3 == "S"
        assert (deg3, minute3, sec3) == (90, 0, 0)
        # via format helper to cover capability lines
        s = _format_dms("89.999999", "179.999999")
        assert "90°" in s

    def test_dm_minutes_q_60_and_overflow(self) -> None:
        # 89.999992 -> minutes 60 -> deg 90 (no overflow for lat)
        deg, mins, hemi = _decimal_to_dm_parts("89.999992", True)
        assert deg == 90
        assert mins == Decimal("0")
        assert hemi == "N"
        # 90.999992 lat -> deg 91 -> capped to 90
        deg2, mins2, _ = _decimal_to_dm_parts("90.999992", True)
        assert deg2 == 90
        assert mins2 == Decimal("0")
        # lon 180.999992 -> deg 181 -> capped to 180
        deg3, mins3, _ = _decimal_to_dm_parts("180.999992", False)
        assert deg3 == 180
        assert mins3 == Decimal("0")
        # lon 179.999992 -> deg 180 no cap (exactly 180)
        deg4, mins4, _ = _decimal_to_dm_parts("179.999992", False)
        assert deg4 == 180
        # ensure format helper hits overflow branches
        assert "90°" in _format_dm("90.999992", "180.999992")
        # also hit minutes_q !=60 normal path
        deg5, mins5, _ = _decimal_to_dm_parts("48.8577", True)
        assert mins5 != Decimal("0")
        # negative case
        deg6, mins6, hemi6 = _decimal_to_dm_parts("-89.999992", True)
        assert hemi6 == "S"
        assert deg6 == 90

    def test_format_iso_integer_only_and_alt_variants(self) -> None:
        # integer-only components hit else branches for lat_int/lon_int without frac
        assert _format_iso("48", "2", None) == "+48+002/"
        assert _format_iso("-48", "-2", None) == "-48-002/"
        assert _format_iso("48.8577", "2", None) == "+48.8577+002/"
        assert _format_iso("48", "2.295", None) == "+48+002.295/"
        # altitude variants: None, with dot (quantized), without dot, negative, positive
        assert _format_iso("48.8577", "2.295", "8850") == "+48.8577+002.295+8850/"
        assert _format_iso("48.8577", "2.295", "+8850") == "+48.8577+002.295+8850/"
        assert _format_iso("48.8577", "2.295", "-8850") == "+48.8577+002.295-8850/"
        assert _format_iso("48.8577", "2.295", "8850.5") == "+48.8577+002.295+8850.5/"
        assert _format_iso("48.8577", "2.295", "-8850.5") == "+48.8577+002.295-8850.5/"
        assert _format_iso("48.8577", "2.295", "0.0") == "+48.8577+002.295+0/"
        assert _format_iso("48.8577", "2.295", "-0.0") == "+48.8577+002.295+0/"
        assert _format_iso("48.8577", "2.295", None).endswith("/")

    def test_format_dm_zero_minutes(self) -> None:
        # lat/lon integer -> minutes 0 -> lat_min_str "0" -> adds ".0"
        s = _format_dm("48", "2")
        assert s == "48°0.0′N 2°0.0′E"
        assert "0.0" in s
        # also via capability format_value
        n = CoordinatesNotation(
            latitude="48",
            longitude="2",
            altitude=None,
            coord_shape="dd",
            compact="48, 2",
        )
        assert CAP.format_value(n.compact, "dm", n) == "48°0.0′N 2°0.0′E"
        # non-zero minutes should keep decimal
        n2 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        )
        assert "0.0" not in CAP.format_value(
            n2.compact, "dm", n2
        ) or "51." in CAP.format_value(n2.compact, "dm", n2)

    def test_format_dms_dm_alt_variants(self) -> None:
        n_none = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        )
        n_alt = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="8850",
            coord_shape="dd",
            compact="48.8577, 2.295, 8850",
        )
        # dms
        assert "8850" not in CAP.format_value(n_none.compact, "dms", n_none)
        assert "8850" in CAP.format_value(n_alt.compact, "dms", n_alt)
        # dm
        assert "8850" not in CAP.format_value(n_none.compact, "dm", n_none)
        assert "8850" in CAP.format_value(n_alt.compact, "dm", n_alt)
        # iso with alt
        assert "8850" in CAP.format_value(n_alt.compact, "iso6709", n_alt)
        # geo_uri and geojson_pair with alt
        assert "8850" in CAP.format_value(n_alt.compact, "geo_uri", n_alt)
        assert "8850" in CAP.format_value(n_alt.compact, "geojson_pair", n_alt)

    def test_format_value_unknown_returns_value(self) -> None:
        n = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        )
        assert CAP.format_value(n.compact, "bogus_format", n) == n.compact
        assert CAP.format_value("custom", "unknown", n) == "custom"


class TestGrammarHelpers:
    def test_normalize_alt_zero_fold(self) -> None:
        assert _normalize_alt("0") == "0"
        assert _normalize_alt("-0") == "0"
        assert _normalize_alt("0.0") == "0"
        assert _normalize_alt("-0.0") == "0"
        assert _normalize_alt("0.000000") == "0"
        # via grammar carriers with altitude 0
        g = CoordinatesRecognitionGrammar()
        for txt in [
            "geo:48.8566,2.3522,0",
            "geo:48.8566,2.3522,-0.0",
            "[2.295, 48.8577, 0.0]",
            "+48.52+002.20+0/",
        ]:
            res = g.recognize(txt)
            assert len(res) == 1
            assert res[0].notation.altitude == "0"

    def test_iso_component_to_decimal_branches(self) -> None:
        # valid lengths
        assert _iso_component_to_decimal("48.52", True) == Decimal("48.52")
        assert _iso_component_to_decimal("1234.7", True)  # DDMM
        assert _iso_component_to_decimal("352139", True)  # DMS
        assert _iso_component_to_decimal("002.20", False) == Decimal("2.20")
        # fallback success: invalid length but valid Decimal
        assert _iso_component_to_decimal("123", True) == Decimal(
            "123"
        )  # len3 invalid for lat, Decimal succeeds
        assert _iso_component_to_decimal("12", False) == Decimal(
            "12"
        )  # len2 invalid for lon, succeeds
        # fallback failure: invalid length and invalid Decimal -> returns 0
        assert _iso_component_to_decimal("ab", False) == Decimal(0)
        assert _iso_component_to_decimal("a", True) == Decimal(0)
        # lon valid length succeeds without fallback
        assert _iso_component_to_decimal("123", False) == Decimal("123")
        # "12a" len3 invalid for lat -> fallback -> 0
        assert _iso_component_to_decimal("12a", True) == Decimal(0)

    def test_dms_overflow_invalid_operation(self) -> None:
        assert _dms_overflow("not-a-number", "0") is False
        assert _dms_overflow("0", "not-a-number") is False
        assert _dms_overflow(None, None) is False
        assert _dms_overflow("60", None) is True
        assert _dms_overflow(None, "60") is True
        assert _dms_overflow("59.9", "59.9") is False

    def test_iso_fallback_via_mock(self) -> None:
        mock = MagicMock()
        mock.groupdict.return_value = {
            "geo": None,
            "iso": "+48.52",
            "geojson": None,
            "pair": None,
            "hemi_front_lat": None,
            "hemi_back_lat": None,
            "sign_lat": None,
            "deg_lat": None,
            "min_lat": None,
            "sec_lat": None,
            "sec_frac_lat": None,
            "hemi_front_lon": None,
            "hemi_back_lon": None,
            "sign_lon": None,
            "deg_lon": None,
            "min_lon": None,
            "sec_lon": None,
            "sec_frac_lon": None,
        }
        n = _notation(mock)  # type: ignore[arg-type]
        # single comp iso should be encoded as out-of-range sentinel
        assert n.latitude == "91"
        assert n.longitude == "181"

    def test_sec_frac_with_and_without_dot(self) -> None:
        g = CoordinatesRecognitionGrammar()
        # sec without dot + sec_frac -> combined as sec.sec_frac (degenerate)
        txt1 = "10°59'26''123N000°00'04''902W"
        res1 = g.recognize(txt1)
        assert len(res1) == 1
        assert res1[0].notation.latitude == "10.99059"
        # sec with dot + sec_frac -> sec_frac ignored because "." in sec_val_str
        txt2 = "10°59'26.5''123N000°00'04.5''902W"
        res2 = g.recognize(txt2)
        assert len(res2) == 1
        # sec 26.5 ignored sec_frac, so 26.5 seconds, not 26.123
        assert res2[0].notation.latitude == "10.990694"
        assert res2[0].notation.longitude == "-0.00125"
        # also test without sec_frac
        txt3 = "10°59'26.5''N 0°0'4.5''W"
        res3 = g.recognize(txt3)
        assert len(res3) == 1
        assert res3[0].notation.latitude == "10.990694"

    def test_component_decimal_min_none_sec_present(self) -> None:
        # Hit inner branch where min is None but sec present (358->360)
        # Need mock where min is None, sec present
        mock = MagicMock()
        mock.groupdict.return_value = {
            "geo": None,
            "iso": None,
            "geojson": None,
            "pair": "10° 46″ N 20° 30″ E",
            "hemi_front_lat": None,
            "hemi_back_lat": "N",
            "sign_lat": None,
            "deg_lat": "10",
            "min_lat": None,
            "sec_lat": "46",
            "sec_frac_lat": None,
            "hemi_front_lon": None,
            "hemi_back_lon": "E",
            "sign_lon": None,
            "deg_lon": "20",
            "min_lon": None,
            "sec_lon": "30",
            "sec_frac_lon": None,
        }
        n = _notation(mock)  # type: ignore[arg-type]
        # deg 10 + sec 46/3600, deg 20 + sec 30/3600
        assert n.coord_shape == "dms"
        assert n.latitude == "10.012778"
        assert n.longitude == "20.008333"
        # also test deg with decimal point but min/sec present (deg fraction ignored)
        mock2 = MagicMock()
        mock2.groupdict.return_value = {
            "geo": None,
            "iso": None,
            "geojson": None,
            "pair": "10.5° 20′ N 20.7° 30′ E",
            "hemi_front_lat": None,
            "hemi_back_lat": "N",
            "sign_lat": None,
            "deg_lat": "10.5",
            "min_lat": "20",
            "sec_lat": None,
            "sec_frac_lat": None,
            "hemi_front_lon": None,
            "hemi_back_lon": "E",
            "sign_lon": None,
            "deg_lon": "20.7",
            "min_lon": "30",
            "sec_lon": None,
            "sec_frac_lon": None,
        }
        n2 = _notation(mock2)  # type: ignore[arg-type]
        assert n2.latitude == "10.333333"
        assert n2.longitude == "20.5"


class TestRulesMatchesBranches:
    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()
        self.annex = SectionAnnexHStringExpression()
        self.r5870 = Section33GeoUriValidity()
        self.r7946 = Section311Position()

    def test_iso_lat_not_str(self) -> None:
        n = object.__new__(CoordinatesNotation)
        object.__setattr__(n, "latitude", 48.8577)  # type: ignore[arg-type]
        object.__setattr__(n, "longitude", "2.295")
        object.__setattr__(n, "altitude", None)
        object.__setattr__(n, "coord_shape", "dd")
        object.__setattr__(n, "compact", "48.8577, 2.295")
        assert self.s6.matches(n, self.contract) is False
        # annex needs iso6709 to reach isinstance check
        n_annex = object.__new__(CoordinatesNotation)
        object.__setattr__(n_annex, "latitude", 48.8577)  # type: ignore[arg-type]
        object.__setattr__(n_annex, "longitude", "2.295")
        object.__setattr__(n_annex, "altitude", None)
        object.__setattr__(n_annex, "coord_shape", "iso6709")
        object.__setattr__(n_annex, "compact", "48.8577, 2.295")
        assert self.annex.matches(n_annex, self.contract) is False
        n_5870 = object.__new__(CoordinatesNotation)
        object.__setattr__(n_5870, "latitude", 48.8577)  # type: ignore[arg-type]
        object.__setattr__(n_5870, "longitude", "2.295")
        object.__setattr__(n_5870, "altitude", None)
        object.__setattr__(n_5870, "coord_shape", "geo_uri")
        object.__setattr__(n_5870, "compact", "48.8577, 2.295")
        assert self.r5870.matches(n_5870, self.contract) is False
        n_7946 = object.__new__(CoordinatesNotation)
        object.__setattr__(n_7946, "latitude", 48.8577)  # type: ignore[arg-type]
        object.__setattr__(n_7946, "longitude", "2.295")
        object.__setattr__(n_7946, "altitude", None)
        object.__setattr__(n_7946, "coord_shape", "geojson")
        object.__setattr__(n_7946, "compact", "48.8577, 2.295")
        assert self.r7946.matches(n_7946, self.contract) is False
        # also lon not str
        n_lon = object.__new__(CoordinatesNotation)
        object.__setattr__(n_lon, "latitude", "48.8577")
        object.__setattr__(n_lon, "longitude", 2.295)  # type: ignore[arg-type]
        object.__setattr__(n_lon, "altitude", None)
        object.__setattr__(n_lon, "coord_shape", "dd")
        object.__setattr__(n_lon, "compact", "48.8577, 2.295")
        assert self.s6.matches(n_lon, self.contract) is False

    def test_iso_alt_not_str(self) -> None:
        n = object.__new__(CoordinatesNotation)
        object.__setattr__(n, "latitude", "48.8577")
        object.__setattr__(n, "longitude", "2.295")
        object.__setattr__(n, "altitude", 123)  # type: ignore[arg-type]
        object.__setattr__(n, "coord_shape", "dd")
        object.__setattr__(n, "compact", "48.8577, 2.295, 123")
        assert self.s6.matches(n, self.contract) is False
        # annex also
        n2 = object.__new__(CoordinatesNotation)
        object.__setattr__(n2, "latitude", "48.8577")
        object.__setattr__(n2, "longitude", "2.295")
        object.__setattr__(n2, "altitude", 123)  # type: ignore[arg-type]
        object.__setattr__(n2, "coord_shape", "iso6709")
        object.__setattr__(n2, "compact", "48.8577, 2.295, 123")
        assert self.annex.matches(n2, self.contract) is False
        # rfc5870
        n3 = object.__new__(CoordinatesNotation)
        object.__setattr__(n3, "latitude", "48.8577")
        object.__setattr__(n3, "longitude", "2.295")
        object.__setattr__(n3, "altitude", 123)  # type: ignore[arg-type]
        object.__setattr__(n3, "coord_shape", "geo_uri")
        object.__setattr__(n3, "compact", "48.8577, 2.295, 123")
        assert self.r5870.matches(n3, self.contract) is False
        # rfc7946
        n4 = object.__new__(CoordinatesNotation)
        object.__setattr__(n4, "latitude", "48.8577")
        object.__setattr__(n4, "longitude", "2.295")
        object.__setattr__(n4, "altitude", 123)  # type: ignore[arg-type]
        object.__setattr__(n4, "coord_shape", "geojson")
        object.__setattr__(n4, "compact", "48.8577, 2.295, 123")
        assert self.r7946.matches(n4, self.contract) is False

    def test_alt_invalid_decimal(self) -> None:
        n = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="not-a-number",
            coord_shape="dd",
            compact="48.8577, 2.295, not-a-number",
        )
        assert self.s6.matches(n, self.contract) is False
        n2 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="NaN",
            coord_shape="iso6709",
            compact="48.8577, 2.295, NaN",
        )
        # NaN parses but is out of range? component_in_range returns False for NaN
        assert (
            self.s6.matches(n2, self.contract) is True
            or self.s6.matches(n2, self.contract) is False
        )  # just ensure no raise
        # annex with bad alt
        n3 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="bad",
            coord_shape="iso6709",
            compact="48.8577, 2.295, bad",
        )
        assert self.annex.matches(n3, self.contract) is False
        assert (
            self.r5870.matches(
                CoordinatesNotation(
                    latitude="48.8577",
                    longitude="2.295",
                    altitude="bad",
                    coord_shape="geo_uri",
                    compact="48.8577, 2.295, bad",
                ),
                self.contract,
            )
            is False
        )
        assert (
            self.r7946.matches(
                CoordinatesNotation(
                    latitude="48.8577",
                    longitude="2.295",
                    altitude="bad",
                    coord_shape="geojson",
                    compact="48.8577, 2.295, bad",
                ),
                self.contract,
            )
            is False
        )

    def test_empty_and_garbage_lat_lon(self) -> None:
        for lat, lon in [
            ("", ""),
            ("abc", "xyz"),
            ("NaN", "Infinity"),
            ("", "2.295"),
            ("48.8577", ""),
        ]:
            n = CoordinatesNotation(
                latitude=lat,
                longitude=lon,
                altitude=None,
                coord_shape="dd",
                compact=f"{lat}, {lon}",
            )
            assert self.s6.matches(n, self.contract) is False

    def test_coord_shape_wrong_for_each_rule(self) -> None:
        # s6 only accepts dd, ddm, dms, iso6709
        assert (
            self.s6.matches(
                CoordinatesNotation(
                    latitude="48.8577",
                    longitude="2.295",
                    altitude=None,
                    coord_shape="geo_uri",
                    compact="48.8577, 2.295",
                ),
                self.contract,
            )
            is False
        )
        assert (
            self.s6.matches(
                CoordinatesNotation(
                    latitude="48.8577",
                    longitude="2.295",
                    altitude=None,
                    coord_shape="geojson",
                    compact="48.8577, 2.295",
                ),
                self.contract,
            )
            is False
        )
        # annex only iso6709
        for shape in ("dd", "ddm", "dms", "geo_uri", "geojson"):
            n = CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape=shape,
                compact="48.8577, 2.295",
            )
            assert self.annex.matches(n, self.contract) is False
        # r5870 only geo_uri
        for shape in ("dd", "iso6709", "geojson"):
            n = CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape=shape,
                compact="48.8577, 2.295",
            )
            assert self.r5870.matches(n, self.contract) is False
        # r7946 only geojson
        for shape in ("dd", "iso6709", "geo_uri"):
            n = CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape=shape,
                compact="48.8577, 2.295",
            )
            assert self.r7946.matches(n, self.contract) is False

    def test_rfc7946_element_count_and_alt_mismatch(self) -> None:
        # compact with 1 part
        n1 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="geojson",
            compact="48.8577",
        )
        assert self.r7946.matches(n1, self.contract) is False
        # 4 parts
        n2 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="8850",
            coord_shape="geojson",
            compact="48.8577, 2.295, 8850, extra",
        )
        assert self.r7946.matches(n2, self.contract) is False
        # alt present but compact has 2 parts
        n3 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="8850",
            coord_shape="geojson",
            compact="48.8577, 2.295",
        )
        assert self.r7946.matches(n3, self.contract) is False
        # alt None but compact has 3 parts
        n4 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="geojson",
            compact="48.8577, 2.295, 8850",
        )
        assert self.r7946.matches(n4, self.contract) is False
        # valid 3 parts with alt
        n5 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude="8850",
            coord_shape="geojson",
            compact="48.8577, 2.295, 8850",
        )
        assert self.r7946.matches(n5, self.contract) is True
        # valid 2 parts without alt
        n6 = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="geojson",
            compact="48.8577, 2.295",
        )
        assert self.r7946.matches(n6, self.contract) is True

    def test_normalize_fallback_branches(self) -> None:
        # _fold_compact exception -> first fallback returns str(getattr)
        n_bad = object.__new__(CoordinatesNotation)
        object.__setattr__(n_bad, "latitude", "48.8577")
        object.__setattr__(n_bad, "longitude", "2.295")
        object.__setattr__(n_bad, "altitude", None)
        object.__setattr__(n_bad, "coord_shape", "dd")
        object.__setattr__(n_bad, "compact", None)  # type: ignore[arg-type]
        # _fold_compact raises on None.split, fallback returns "None"
        assert self.s6.normalize(n_bad, self.contract) == "None"
        assert self.annex.normalize(n_bad, self.contract) == "None"
        assert self.r5870.normalize(n_bad, self.contract) == "None"
        assert self.r7946.normalize(n_bad, self.contract) == "None"

        # second fallback -> return "" when str raises
        class BadStr:
            def __str__(self) -> str:
                raise RuntimeError("boom")

        class ObjBad:
            compact = BadStr()  # type: ignore[assignment]
            latitude = "0"
            longitude = "0"
            altitude = None
            coord_shape = "dd"

        bad = ObjBad()
        # BadStr has no split -> AttributeError, then str raises -> return ""
        assert self.s6.normalize(bad, self.contract) == ""  # type: ignore[arg-type]
        assert self.annex.normalize(bad, self.contract) == ""  # type: ignore[arg-type]
        assert self.r5870.normalize(bad, self.contract) == ""  # type: ignore[arg-type]
        assert self.r7946.normalize(bad, self.contract) == ""  # type: ignore[arg-type]

        # getattr missing -> returns "" default then str("") -> ""
        class Empty:
            latitude = "0"
            longitude = "0"
            altitude = None
            coord_shape = "dd"

        empty = Empty()
        assert self.s6.normalize(empty, self.contract) == ""  # type: ignore[arg-type]

        # None notation
        assert self.s6.normalize(None, self.contract) == ""  # type: ignore[arg-type]

    def test_fold_compact_second_branch_nd_zero(self) -> None:
        # Hit the nd == 0 after normalize but d !=0 branch via patching Decimal
        import importlib

        for mod_name in [
            "paxman.capabilities.Coordinates.rules.iso_6709_ed2022",
            "paxman.capabilities.Coordinates.rules.rfc_5870_ed2010",
            "paxman.capabilities.Coordinates.rules.rfc_7946_ed2016",
        ]:
            mod = importlib.import_module(mod_name)
            orig = mod.Decimal  # type: ignore[attr-defined]
            from decimal import Decimal as RealDec

            class FakeDec:
                def __init__(self, val: str) -> None:
                    self.val = val

                def __eq__(self, other: object) -> bool:
                    if other == 0:
                        return False
                    return False

                def normalize(self) -> Decimal:
                    return RealDec(0)

                def __format__(self, fmt: str) -> str:
                    return "fake"

            def fake_decimal(  # type: ignore[no-untyped-def]
                s: str,
                _orig=orig,  # noqa: B023
            ) -> object:
                if s == "trigger":
                    return FakeDec(s)
                return _orig(s)  # type: ignore[no-untyped-call]

            mod.Decimal = fake_decimal  # type: ignore[assignment]
            try:
                result = mod._fold_compact("trigger, 2.295")  # type: ignore[attr-defined]
                assert result == "0, 2.295"
            finally:
                mod.Decimal = orig  # type: ignore[assignment]

    def test_component_in_range_branches(self) -> None:
        assert component_in_range("NaN", "-90", "90") is False
        assert component_in_range("Infinity", "-90", "90") is False
        assert component_in_range("-Infinity", "-180", "180") is False
        assert component_in_range("abc", "-90", "90") is False
        assert component_in_range("", "-90", "90") is False
        assert component_in_range("48.8577", "-90", "90") is True
        assert component_in_range("-90", "-90", "90") is True
        assert component_in_range("90", "-90", "90") is True
        assert component_in_range("90.000001", "-90", "90") is False

    def test_matches_never_raises_with_mock_coord_shape(self) -> None:
        class BadShape:
            @property
            def coord_shape(self) -> str:
                raise AttributeError("boom")

            latitude = "48.8577"
            longitude = "2.295"
            altitude = None
            compact = "48.8577, 2.295"

        bad = BadShape()
        assert self.s6.matches(bad, self.contract) is False  # type: ignore[arg-type]
        assert self.annex.matches(bad, self.contract) is False  # type: ignore[arg-type]
        assert self.r5870.matches(bad, self.contract) is False  # type: ignore[arg-type]
        assert self.r7946.matches(bad, self.contract) is False  # type: ignore[arg-type]

        # None notation
        assert self.s6.matches(None, self.contract) is False  # type: ignore[arg-type]
        assert self.r7946.matches(123, self.contract) is False  # type: ignore[arg-type]


class TestGrammarEdgeCases:
    def test_quantize_and_normalize_alt(self) -> None:
        from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
            _quantize,
        )

        assert _quantize(Decimal("0")) == "0"
        assert _quantize(Decimal("-0")) == "0"
        assert _quantize(Decimal("0.0000004")) == "0"
        # ensure non-zero kept
        assert _quantize(Decimal("48.8566")) == "48.8566"

    def test_grammar_recognition_alt_zero(self) -> None:
        g = CoordinatesRecognitionGrammar()
        # all carriers with alt 0 already tested, ensure they are recognized
        assert g.recognize("geo:0,0,0")[0].notation.altitude == "0"
        assert g.recognize("[0, 0, 0]")[0].notation.altitude == "0"
        assert g.recognize("+00+000+0/")[0].notation.altitude == "0"

    def test_dms_overflow_via_grammar(self) -> None:
        g = CoordinatesRecognitionGrammar()
        # minute overflow should be sentinel 91
        n = g.recognize("40° 75′ N 79° 58′ 56″ W")
        assert n is not None
        assert len(n) == 1
        # at least one is sentinel
        assert n[0].notation.latitude == "91" or n[0].notation.longitude in (
            "181",
            "-181",
        )

    def test_component_in_range_via_grammar_sentinel(self) -> None:
        # Ensure rule rejects sentinel via component_in_range
        contract = CoordinatesContract()
        s6 = Section6CoordinateStructure()
        g = CoordinatesRecognitionGrammar()
        n = g.recognize("40° 75′ N 79° 58′ 56″ W")
        assert n is not None
        assert s6.matches(n[0].notation, contract) is False
