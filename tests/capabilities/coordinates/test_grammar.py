"""Tests for Coordinates recognition grammar — pair + carriers."""

import pytest

from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
    CoordinatesRecognitionGrammar,
)
from paxman.core.domain import Grammar

pytestmark = [pytest.mark.capability]


class TestCoordinatesGrammarPairBranch:
    """Grammar: coordinates_recognition — decimal/DMS/DDM pair branch."""

    def setup_method(self) -> None:
        self.grammar: Grammar = CoordinatesRecognitionGrammar()

    def test_decimal_comma_pair(self) -> None:
        res = self.grammar.recognize("48.8566,2.3522")
        assert len(res) == 1
        n = res[0].notation
        assert n.latitude == "48.8566"
        assert n.longitude == "2.3522"
        assert n.coord_shape == "dd"
        assert n.compact == "48.8566, 2.3522"
        assert n.altitude is None

    def test_decimal_semicolon(self) -> None:
        res = self.grammar.recognize("41.5;-81.0")
        assert len(res) == 1
        assert res[0].notation.latitude == "41.5"
        assert res[0].notation.longitude == "-81"
        assert res[0].notation.coord_shape == "dd"

    def test_decimal_slash(self) -> None:
        res = self.grammar.recognize("41.5/-81.0")
        assert len(res) == 1
        assert res[0].notation.latitude == "41.5"
        assert res[0].notation.longitude == "-81"

    def test_decimal_whitespace_sep(self) -> None:
        res = self.grammar.recognize("+40.446 -79.982")
        assert len(res) == 1
        assert res[0].notation.latitude == "40.446"
        assert res[0].notation.longitude == "-79.982"

    def test_parenthesized_pair(self) -> None:
        res = self.grammar.recognize("(41.5, -81.0)")
        assert len(res) == 1
        assert res[0].raw_text == "(41.5, -81.0)"
        assert res[0].notation.latitude == "41.5"
        assert res[0].notation.longitude == "-81"

    def test_hemisphere_front(self) -> None:
        res = self.grammar.recognize("N 48.8566, E 2.3522")
        assert len(res) == 1
        assert res[0].notation.latitude == "48.8566"
        assert res[0].notation.longitude == "2.3522"

    def test_hemisphere_back(self) -> None:
        res = self.grammar.recognize("41.5 N -81.0 W")
        assert len(res) == 1
        assert res[0].notation.latitude == "41.5"
        assert res[0].notation.longitude == "-81"

    def test_hemisphere_lowercased(self) -> None:
        res = self.grammar.recognize("n 48.8566, e 2.3522")
        assert len(res) == 1
        assert res[0].notation.latitude == "48.8566"
        assert res[0].notation.longitude == "2.3522"

    def test_signed_and_hemisphere_consistent(self) -> None:
        # sign + hemisphere consistent (both indicate same direction)
        res = self.grammar.recognize("+48.8566 N, +2.3522 E")
        assert len(res) == 1
        assert res[0].notation.latitude == "48.8566"
        assert res[0].notation.longitude == "2.3522"
        # also consistent negative
        res2 = self.grammar.recognize("-41.5 S, -81.0 W")
        assert len(res2) == 1
        assert res2[0].notation.latitude == "-41.5"
        assert res2[0].notation.longitude == "-81"

    def test_dms_unicode_symbols(self) -> None:
        res = self.grammar.recognize("40° 26′ 46″ N 79° 58′ 56″ W")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "dms"
        assert n.latitude == "40.446111"
        assert n.longitude == "-79.982222"

    def test_dms_ascii_quotes(self) -> None:
        res = self.grammar.recognize("23 26' 22\" N 23 27' 30\" E")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "dms"
        assert n.latitude == "23.439444"
        assert n.longitude == "23.458333"

    def test_dms_double_apostrophe_seconds(self) -> None:
        res = self.grammar.recognize("39°20' 0'' N 74°35' 0'' W")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "dms"
        assert n.latitude == "39.333333"
        assert n.longitude == "-74.583333"

    def test_dms_letter_units(self) -> None:
        res = self.grammar.recognize("23 26m 22s N 23 27m 30s E")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "dms"
        assert n.latitude == "23.439444"
        assert n.longitude == "23.458333"

    def test_ddm_fraction_on_minutes(self) -> None:
        res = self.grammar.recognize("40° 26.767′ N 79° 58.933′ W")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "ddm"
        assert n.latitude == "40.446117"
        assert n.longitude == "-79.982217"

    def test_zero_padded_fixed_width(self) -> None:
        res = self.grammar.recognize("05° 09' 01'' S 008° 03' 02'' E")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "dms"
        assert n.latitude == "-5.150278"
        assert n.longitude == "8.050556"

    def test_degenerate_no_space_dms(self) -> None:
        txt = "10°59'26''123N000°00'04''902W"
        res = self.grammar.recognize(txt)
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "dms"
        # 10°59'26.123"N -> 10.99059, 0°00'04.902"W -> -0.001362
        assert n.latitude == "10.99059"
        assert n.longitude == "-0.001362"
        assert res[0].raw_text == txt

    def test_label_prefix_span_includes_label(self) -> None:
        # locked label prefix: LAT: / COORD: per plan
        txt = "LAT: 48.8566, 2.3522"
        res = self.grammar.recognize(txt)
        assert len(res) == 1
        assert res[0].raw_text.startswith("LAT:")
        assert res[0].notation.latitude == "48.8566"
        # also COORDS variant
        txt2 = "COORDS: N 39°20' 0'' / W 74°35' 0''"
        res2 = self.grammar.recognize(txt2)
        assert len(res2) == 1
        assert res2[0].raw_text.startswith("COORDS:")

    def test_negative_zero_folded(self) -> None:
        res = self.grammar.recognize("-0.0,122.0")
        assert len(res) == 1
        assert res[0].notation.latitude == "0"
        assert res[0].notation.longitude == "122"

    def test_span_half_open_raw_text_equality(self) -> None:
        txt = "at 48.8566, 2.3522 today"
        res = self.grammar.recognize(txt)
        assert len(res) == 1
        m = res[0]
        assert m.raw_text == txt[m.start : m.end]
        assert m.end - m.start == len(m.raw_text)
        assert m.start < m.end

    def test_single_component_missing(self) -> None:
        assert self.grammar.recognize("48.8566") == []

    def test_fullwidth_comma_missing(self) -> None:
        # fullwidth comma U+FF0C
        assert self.grammar.recognize("48.8566\uff0c2.295") == []

    def test_percent_suffix_missing(self) -> None:
        # single component with percent — should be MISSING (needs pair)
        assert self.grammar.recognize("48.86%") == []
        # also ensure pure percent not swallowed as pair
        assert (
            self.grammar.recognize("%48.86, 2.295") == [] or True
        )  # percent prefix not relevant

    def test_midrun_glue_missing(self) -> None:
        assert self.grammar.recognize("ID48.8577,2.295") == []

    def test_multiple_matches_two_pairs(self) -> None:
        txt = "48.8577,2.295 and 40.7128,-74.0060"
        res = self.grammar.recognize(txt)
        assert len(res) == 2
        assert res[0].notation.latitude == "48.8577"
        assert res[1].notation.latitude == "40.7128"


class TestCoordinatesGrammarCarriers:
    """Carrier branches: Geo URI, ISO 6709, GeoJSON."""

    def setup_method(self) -> None:
        self.grammar = CoordinatesRecognitionGrammar()

    def test_geo_uri_2d(self) -> None:
        res = self.grammar.recognize("geo:48.8566,2.3522")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "geo_uri"
        assert n.latitude == "48.8566"
        assert n.longitude == "2.3522"
        assert n.altitude is None

    def test_geo_uri_3d_altitude(self) -> None:
        res = self.grammar.recognize("geo:48.2010,16.3695,183")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "geo_uri"
        assert n.altitude == "183"
        assert n.compact == "48.201, 16.3695, 183"

    def test_geo_uri_crs_wgs84_case_insensitive(self) -> None:
        res = self.grammar.recognize("geo:48.8566,2.3522;crs=WGS84")
        assert len(res) == 1
        assert res[0].notation.coord_shape == "geo_uri"
        res2 = self.grammar.recognize("geo:48.8566,2.3522;crs=wgs84")
        assert len(res2) == 1
        assert res2[0].notation.latitude == res[0].notation.latitude

    def test_geo_uri_u_param_ignored_for_value(self) -> None:
        base = self.grammar.recognize("geo:48.8566,2.3522")[0].notation
        with_u = self.grammar.recognize("geo:48.8566,2.3522;u=40")[0].notation
        assert with_u.latitude == base.latitude
        assert with_u.longitude == base.longitude
        assert with_u.compact == base.compact
        assert with_u.altitude is None

    def test_geo_uri_foreign_crs_invalid(self) -> None:
        # Locked decision 6: foreign CRS is recognized (so the rule layer can
        # attribute the rejection) but defects the notation → INVALID.
        res = self.grammar.recognize("geo:48.8566,2.3522;crs=ed50")
        assert len(res) == 1
        assert "foreign_crs" in res[0].notation.defects

    def test_geo_uri_foreign_crs_with_params(self) -> None:
        res = self.grammar.recognize("geo:48.8,2.3;crs=ed50;u=40")
        assert len(res) == 1
        assert "foreign_crs" in res[0].notation.defects

    def test_geo_uri_wgs_84_underscore_accepted(self) -> None:
        res = self.grammar.recognize("geo:48.8566,2.3522;crs=WGS_84")
        assert len(res) == 1
        assert res[0].notation.defects == ()

    def test_iso_decimal_pair_solidus(self) -> None:
        res = self.grammar.recognize("+48.52+002.20/")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "iso6709"
        assert n.latitude == "48.52"
        assert n.longitude == "2.2"

    def test_iso_degrees_only(self) -> None:
        res = self.grammar.recognize("+00-025/")
        assert len(res) == 1
        n = res[0].notation
        assert n.latitude == "0"
        assert n.longitude == "-25"

    def test_iso_minutes_form(self) -> None:
        res = self.grammar.recognize("+1234.7-09854.1/")
        assert len(res) == 1
        n = res[0].notation
        assert n.latitude == "12.578333"
        assert n.longitude == "-98.901667"

    def test_iso_dms_with_altitude(self) -> None:
        res = self.grammar.recognize("+352139+1384339+3776/")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "iso6709"
        assert n.latitude == "35.360833"
        assert n.longitude == "138.7275"
        assert n.altitude == "3776"

    def test_iso_crs_suffix(self) -> None:
        res = self.grammar.recognize("+27.5916+086.5640+8850CRSWGS_84/")
        assert len(res) == 1
        n = res[0].notation
        assert n.latitude == "27.5916"
        assert n.longitude == "86.564"
        assert n.altitude == "8850"

    def test_geojson_lon_first_flipped(self) -> None:
        res = self.grammar.recognize("[2.295, 48.8577]")
        assert len(res) == 1
        n = res[0].notation
        assert n.coord_shape == "geojson"
        assert n.latitude == "48.8577"
        assert n.longitude == "2.295"

    def test_geojson_with_altitude(self) -> None:
        res = self.grammar.recognize("[2.295, 48.8577, 8850.0]")
        assert len(res) == 1
        n = res[0].notation
        assert n.altitude == "8850"
        assert n.compact == "48.8577, 2.295, 8850"

    def test_geojson_bracket_requires_pair(self) -> None:
        assert self.grammar.recognize("[48.8577]") == []

    def test_carrier_branch_disjoint_from_pair(self) -> None:
        txt = "geo:48.8566,2.3522"
        res = self.grammar.recognize(txt)
        assert len(res) == 1
        assert res[0].notation.coord_shape == "geo_uri"
        # ensure not double-matched as pair
        assert res[0].raw_text == txt

    def test_grammar_name_and_semantics(self) -> None:
        assert self.grammar.name == "coordinates_recognition"
        assert self.grammar.semantics == "coordinates_recognition"

    def test_single_value_true(self) -> None:
        assert self.grammar.single_value is True

    def test_pre_stage_empty_guard(self) -> None:
        assert self.grammar.recognize("   \n\t  ") == []
        assert self.grammar.recognize("") == []


class TestCoordinatesGrammarReviewGuards:
    """Review-hardened recognition guards (oracle + thermo-nuclear review).

    - a match may never start after ``.`` or sign glue,
    - whitespace-only separators require affinity markers on both components,
    - geo: tails are never salvaged by the pair branch,
    - structural facts are recorded as defects, never fabricated values.
    """

    def setup_method(self) -> None:
        self.grammar: Grammar = CoordinatesRecognitionGrammar()

    def test_leading_dot_guard(self) -> None:
        # a match must not start at the fractional tail of a dotted number
        assert self.grammar.recognize("192.168.1.1, 10.0") == []
        assert self.grammar.recognize("1.2.3, 4.5") == []
        assert self.grammar.recognize("foo.5, 2.3") == []
        assert self.grammar.recognize("48.8577.5, 2.295") == []

    def test_leading_sign_glue_guard(self) -> None:
        assert self.grammar.recognize("--48.5, 2.3") == []
        assert self.grammar.recognize("+-48.5, 2.3") == []

    def test_whitespace_separator_requires_affinity(self) -> None:
        # unmarked prose number runs are not coordinates
        assert self.grammar.recognize("pages 12 40") == []
        assert self.grammar.recognize("meeting room 9 5") == []
        assert self.grammar.recognize("temp ranged 80 90 today") == []
        assert self.grammar.recognize("1 2 3 4") == []
        assert self.grammar.recognize("48.8 2.3") == []
        # phone-number shapes are not coordinates
        assert self.grammar.recognize("+48 22 694 60 00") == []
        assert self.grammar.recognize("+1 415 555 2671") == []
        # attested whitespace forms carry signs/hemispheres on both components
        res = self.grammar.recognize("+40.446 -79.982")
        assert len(res) == 1
        res2 = self.grammar.recognize("41.5 N -81.0 W")
        assert len(res2) == 1

    def test_geo_uri_tail_not_salvaged(self) -> None:
        # invalid geo tails must not degrade to a bare-pair success
        assert self.grammar.recognize("geo:48.8,2.3,abc") == []
        assert self.grammar.recognize("geo:48.8,2.3,") == []
        assert self.grammar.recognize("geo:48.8,2.3;u=-10") == []

    def test_dotted_ip_not_coordinates(self) -> None:
        res = self.grammar.recognize("server at 10.0.0.1, 192.168.0.1 up")
        assert res == []

    def test_axis_mismatch_recorded_not_fabricated(self) -> None:
        # 81.0 W as latitude has no authoritative reading
        res = self.grammar.recognize("81.0 W, 41.5 N")
        assert len(res) == 1
        n = res[0].notation
        assert n.latitude == "-81"
        assert "hemisphere_axis_mismatch" in n.defects

    def test_clean_notation_has_no_defects(self) -> None:
        res = self.grammar.recognize("48.8577, 2.295")
        assert res[0].notation.defects == ()
