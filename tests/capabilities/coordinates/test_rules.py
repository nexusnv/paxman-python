"""Tests for Coordinates rules (Tasks 5-7) — ISO 6709, RFC 5870, RFC 7946."""

from __future__ import annotations

from pathlib import Path

import pytest

from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
    CoordinatesRecognitionGrammar,
)
from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules.iso_6709_ed2022 import (
    PUBLICATION as PUBLICATION_ISO,
)
from paxman.capabilities.Coordinates.rules.iso_6709_ed2022 import (
    Section6CoordinateStructure,
    SectionAnnexHStringExpression,
)
from paxman.capabilities.Coordinates.rules.rfc_5870_ed2010 import (
    PUBLICATION as PUBLICATION_5870,
)
from paxman.capabilities.Coordinates.rules.rfc_5870_ed2010 import (
    Section33GeoUriValidity,
)
from paxman.capabilities.Coordinates.rules.rfc_7946_ed2016 import (
    PUBLICATION as PUBLICATION_7946,
)
from paxman.capabilities.Coordinates.rules.rfc_7946_ed2016 import (
    Section311Position,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]


def _grammar_notation(text: str) -> CoordinatesNotation | None:
    """Return the first notation recognized for *text*, or None if no match."""
    grammar = CoordinatesRecognitionGrammar()
    matches = grammar.recognize(text)
    if not matches:
        return None
    return matches[0].notation


class TestPublicationProvenance:
    """Each publication's Provenance citation must be exact."""

    def test_iso_6709_ed2022_provenance(self) -> None:
        p = PUBLICATION_ISO
        assert p.authority == "ISO"
        assert p.specification_name == "ISO 6709"
        assert p.kind == "specification"
        assert p.reference_url == "https://www.iso.org/standard/75147.html"
        assert p.version == "2022"
        assert p.lifecycle == "active"
        assert p.publication_year == 2022
        # also via rule provenance
        r1 = Section6CoordinateStructure()
        r2 = SectionAnnexHStringExpression()
        assert r1.provenance == p
        assert r2.provenance == p

    def test_rfc_5870_ed2010_provenance(self) -> None:
        p = PUBLICATION_5870
        assert p.authority == "IETF"
        assert p.specification_name == "RFC 5870"
        assert p.kind == "specification"
        assert p.reference_url == "https://www.rfc-editor.org/rfc/rfc5870.txt"
        assert p.version == "5870"
        assert p.lifecycle == "active"
        assert p.publication_year == 2010
        r = Section33GeoUriValidity()
        assert r.provenance == p

    def test_rfc_7946_ed2016_provenance(self) -> None:
        p = PUBLICATION_7946
        assert p.authority == "IETF"
        assert p.specification_name == "RFC 7946"
        assert p.kind == "specification"
        assert p.reference_url == "https://www.rfc-editor.org/rfc/rfc7946.txt"
        assert p.version == "7946"
        assert p.lifecycle == "active"
        assert p.publication_year == 2016
        r = Section311Position()
        assert r.provenance == p


class TestRuleNamesConvention:
    """Rule names follow Section {X}-{description} convention."""

    def test_rule_names(self) -> None:
        assert Section6CoordinateStructure().name == "Section 6-coordinate-structure"
        assert (
            SectionAnnexHStringExpression().name == "Section Annex-h-string-expression"
        )
        assert Section33GeoUriValidity().name == "Section 3.3-geo-uri-validity"
        assert Section311Position().name == "Section 3.1.1-position"


class TestStrategyParser:
    """All four coordinates rules are PARSER."""

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_strategy_is_parser(self, rule: object) -> None:
        assert rule.strategy is RuleStrategy.PARSER


class TestTargetSemantics:
    """All rules target the single recognition grammar."""

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_target_semantics_routes_grammar(self, rule: object) -> None:
        assert rule.target_semantics == frozenset({"coordinates_recognition"})


class TestRequiresFeaturesEmpty:
    """All rules declare requires_features == frozenset()."""

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_requires_features_empty(self, rule: object) -> None:
        assert rule.requires_features == frozenset()


class TestMatchesValidAllShapes:
    """Each coord_shape's valid notation matches its owning rule."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()
        self.annex = SectionAnnexHStringExpression()
        self.r5870 = Section33GeoUriValidity()
        self.r7946 = Section311Position()

    def test_section6_matches_dd(self) -> None:
        n = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        )
        assert self.s6.matches(n, self.contract) is True

    def test_section6_matches_ddm_via_grammar(self) -> None:
        # DDM example from grammar tests: 40° 26.767′ N
        n = _grammar_notation("40° 26.767′ N 79° 58.933′ W")
        assert n is not None
        assert n.coord_shape == "ddm"
        assert self.s6.matches(n, self.contract) is True

    def test_section6_matches_dms_via_grammar(self) -> None:
        n = _grammar_notation("40° 26′ 46″ N 79° 58′ 56″ W")
        assert n is not None
        assert n.coord_shape == "dms"
        assert self.s6.matches(n, self.contract) is True

    def test_section6_matches_iso6709_via_grammar(self) -> None:
        n = _grammar_notation("+48.52+002.20/")
        assert n is not None
        assert n.coord_shape == "iso6709"
        assert self.s6.matches(n, self.contract) is True

    def test_section6_matches_ddm_direct(self) -> None:
        n = CoordinatesNotation(
            latitude="40.446117",
            longitude="-79.982217",
            altitude=None,
            coord_shape="ddm",
            compact="40.446117, -79.982217",
        )
        assert self.s6.matches(n, self.contract) is True

    def test_section6_matches_dms_direct(self) -> None:
        n = CoordinatesNotation(
            latitude="40.446111",
            longitude="-79.982222",
            altitude=None,
            coord_shape="dms",
            compact="40.446111, -79.982222",
        )
        assert self.s6.matches(n, self.contract) is True

    def test_section6_rejects_geo_uri_shape(self) -> None:
        n = CoordinatesNotation(
            latitude="48.8566",
            longitude="2.3522",
            altitude=None,
            coord_shape="geo_uri",
            compact="48.8566, 2.3522",
        )
        assert self.s6.matches(n, self.contract) is False

    def test_section6_rejects_geojson_shape(self) -> None:
        n = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="geojson",
            compact="48.8577, 2.295",
        )
        assert self.s6.matches(n, self.contract) is False

    def test_annex_h_matches_iso6709(self) -> None:
        n = _grammar_notation("+48.52+002.20/")
        assert n is not None
        assert self.annex.matches(n, self.contract) is True

    def test_annex_h_matches_iso6709_with_crs_and_altitude(self) -> None:
        n = _grammar_notation("+27.5916+086.5640+8850CRSWGS_84/")
        assert n is not None
        assert n.coord_shape == "iso6709"
        assert self.annex.matches(n, self.contract) is True

    def test_annex_h_rejects_other_shapes(self) -> None:
        for shape in ("dd", "ddm", "dms", "geo_uri", "geojson"):
            n = CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape=shape,
                compact="48.8577, 2.295",
            )
            assert self.annex.matches(n, self.contract) is False

    def test_rfc5870_matches_geo_uri_2d(self) -> None:
        n = _grammar_notation("geo:48.8566,2.3522")
        assert n is not None
        assert n.coord_shape == "geo_uri"
        assert self.r5870.matches(n, self.contract) is True

    def test_rfc5870_matches_geo_uri_3d_with_altitude(self) -> None:
        n = _grammar_notation("geo:48.2010,16.3695,183")
        assert n is not None
        assert n.coord_shape == "geo_uri"
        assert n.altitude == "183"
        assert self.r5870.matches(n, self.contract) is True

    def test_rfc5870_matches_geo_uri_with_crs_wgs84(self) -> None:
        n = _grammar_notation("geo:48.8566,2.3522;crs=wgs84")
        assert n is not None
        assert self.r5870.matches(n, self.contract) is True
        n2 = _grammar_notation("geo:48.8566,2.3522;crs=WGS84")
        assert n2 is not None
        assert self.r5870.matches(n2, self.contract) is True

    def test_rfc5870_rejects_other_shapes(self) -> None:
        for shape in ("dd", "dms", "iso6709", "geojson"):
            n = CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape=shape,
                compact="48.8577, 2.295",
            )
            assert self.r5870.matches(n, self.contract) is False

    def test_rfc7946_matches_geojson_2d(self) -> None:
        n = _grammar_notation("[2.295, 48.8577]")
        assert n is not None
        assert n.coord_shape == "geojson"
        assert self.r7946.matches(n, self.contract) is True

    def test_rfc7946_matches_geojson_3d_with_altitude(self) -> None:
        n = _grammar_notation("[2.295, 48.8577, 8850.0]")
        assert n is not None
        assert n.coord_shape == "geojson"
        assert self.r7946.matches(n, self.contract) is True

    def test_rfc7946_rejects_other_shapes(self) -> None:
        for shape in ("dd", "dms", "iso6709", "geo_uri"):
            n = CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape=shape,
                compact="48.8577, 2.295",
            )
            assert self.r7946.matches(n, self.contract) is False


class TestRejectsHemisphereContradiction:
    """Hemisphere/sign contradiction is recorded as a defect and rejected.

    The grammar treats the hemisphere as authoritative, so the recognized
    value stays faithful to the input; the rule layer rejects the defect.
    """

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()

    def test_rejects_hemisphere_contradiction_via_grammar_lat(self) -> None:
        # -41.5 N : sign '-' contradicts N (north implies positive)
        n = _grammar_notation("-41.5 N, 81.0 E")
        assert n is not None
        assert n.latitude == "41.5"
        assert "sign_hemisphere_conflict" in n.defects
        assert self.s6.matches(n, self.contract) is False

    def test_rejects_hemisphere_contradiction_via_grammar_lon(self) -> None:
        # -81.0 E : E implies positive, '-' contradicts
        n = _grammar_notation("41.5 N, -81.0 E")
        assert n is not None
        assert n.longitude == "81"
        assert "sign_hemisphere_conflict" in n.defects
        assert self.s6.matches(n, self.contract) is False
        n2 = _grammar_notation("48.8577 N, -2.3522 E")
        assert n2 is not None
        assert n2.longitude == "2.3522"
        assert "sign_hemisphere_conflict" in n2.defects
        assert self.s6.matches(n2, self.contract) is False

    def test_rejects_both_hemisphere_contradictions(self) -> None:
        n = _grammar_notation("-41.5 N, -81.0 E")
        assert n is not None
        assert "sign_hemisphere_conflict" in n.defects
        assert self.s6.matches(n, self.contract) is False


class TestRejectsHemisphereAxisMismatch:
    """E/W on the latitude component or N/S on longitude has no
    authoritative reading and is rejected."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()

    def test_rejects_lon_hemisphere_on_latitude(self) -> None:
        n = _grammar_notation("81.0 W, 41.5 N")
        assert n is not None
        assert "hemisphere_axis_mismatch" in n.defects
        assert self.s6.matches(n, self.contract) is False

    def test_rejects_lat_hemisphere_on_longitude(self) -> None:
        n = _grammar_notation("48.8577, 2.295 N")
        assert n is not None
        assert "hemisphere_axis_mismatch" in n.defects
        assert self.s6.matches(n, self.contract) is False

    def test_accepts_axis_consistent_hemispheres(self) -> None:
        n = _grammar_notation("UT: N 39°20' 0'' / W 74°35' 0''")
        assert n is not None
        assert n.defects == ()
        assert self.s6.matches(n, self.contract) is True


class TestRejectsDmsUnitOverflow:
    """Minutes >=60 or seconds >=60 are recorded as a defect and rejected."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()

    def test_rejects_dms_minute_overflow_via_grammar(self) -> None:
        n = _grammar_notation("40° 75′ N 79° 58′ 56″ W")
        assert n is not None
        # value stays faithful: 40° + 75′ = 41.25°
        assert n.latitude == "41.25"
        assert "dms_unit_overflow" in n.defects
        assert self.s6.matches(n, self.contract) is False

    def test_rejects_dms_second_overflow_via_grammar(self) -> None:
        # 40° 26′ 75″ N -> seconds 75 >=60
        n = _grammar_notation("40° 26′ 75″ N 79° 58′ 56″ W")
        assert n is not None
        assert n.latitude == "40.454167"
        assert "dms_unit_overflow" in n.defects
        assert self.s6.matches(n, self.contract) is False

    def test_rejects_dms_lon_overflow_via_grammar(self) -> None:
        n = _grammar_notation("40° 26′ 46″ N 79° 75′ 56″ W")
        assert n is not None
        assert n.longitude == "-80.265556"
        assert "dms_unit_overflow" in n.defects
        assert self.s6.matches(n, self.contract) is False


class TestRejectsOutOfRange:
    """Lat in [-90,90], lon in [-180,180]; out-of-range is INVALID."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()
        self.r5870 = Section33GeoUriValidity()
        self.r7946 = Section311Position()
        self.annex = SectionAnnexHStringExpression()

    @pytest.mark.parametrize(
        ("lat", "lon"),
        [
            ("91", "2"),
            ("91.0", "2.0"),
            ("-91", "0"),
            ("90.000001", "0"),
        ],
    )
    def test_section6_rejects_lat_out_of_range(self, lat: str, lon: str) -> None:
        n = CoordinatesNotation(
            latitude=lat,
            longitude=lon,
            altitude=None,
            coord_shape="dd",
            compact=f"{lat}, {lon}",
        )
        assert self.s6.matches(n, self.contract) is False

    @pytest.mark.parametrize(
        ("lat", "lon"),
        [
            ("48.8577", "181"),
            ("48.8577", "181.0"),
            ("0", "180.000001"),
            ("0", "-181"),
        ],
    )
    def test_section6_rejects_lon_out_of_range(self, lat: str, lon: str) -> None:
        n = CoordinatesNotation(
            latitude=lat,
            longitude=lon,
            altitude=None,
            coord_shape="dd",
            compact=f"{lat}, {lon}",
        )
        assert self.s6.matches(n, self.contract) is False

    def test_rfc5870_rejects_lat_out_of_range(self) -> None:
        n = CoordinatesNotation(
            latitude="94",
            longitude="0",
            altitude=None,
            coord_shape="geo_uri",
            compact="94, 0",
        )
        assert self.r5870.matches(n, self.contract) is False

    def test_rfc5870_rejects_lon_out_of_range(self) -> None:
        n = CoordinatesNotation(
            latitude="0",
            longitude="181",
            altitude=None,
            coord_shape="geo_uri",
            compact="0, 181",
        )
        assert self.r5870.matches(n, self.contract) is False

    def test_rfc7946_rejects_lat_out_of_range(self) -> None:
        n = CoordinatesNotation(
            latitude="91",
            longitude="0",
            altitude=None,
            coord_shape="geojson",
            compact="91, 0",
        )
        assert self.r7946.matches(n, self.contract) is False

    def test_rfc7946_rejects_lon_out_of_range(self) -> None:
        n = CoordinatesNotation(
            latitude="0",
            longitude="181",
            altitude=None,
            coord_shape="geojson",
            compact="0, 181",
        )
        assert self.r7946.matches(n, self.contract) is False

    def test_iso6709_out_of_range_direct_notation(self) -> None:
        # direct notation out-of-range; the range check rejects
        n = CoordinatesNotation(
            latitude="91",
            longitude="2.2",
            altitude=None,
            coord_shape="iso6709",
            compact="91, 2.2",
        )
        assert self.s6.matches(n, self.contract) is False
        assert self.annex.matches(n, self.contract) is False


class TestIsoRejectsWrongDigitWidth:
    """ISO digit-width: lat 2/4/6, lon 3/5/7 integer digits; others are defective."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.s6 = Section6CoordinateStructure()
        self.annex = SectionAnnexHStringExpression()

    @pytest.mark.parametrize(
        "text",
        [
            "+123+002.20/",  # lat 3 digits invalid
            "+12345+002.20/",  # lat 5 digits invalid
            "+1234567+002.20/",  # lat 7 digits invalid
            "+12+02.20/",  # lon 2 digits invalid (needs 3/5/7)
            "+48.52+02.20/",  # lon 2 digits invalid -> iso_digit_width defect
        ],
    )
    def test_iso_wrong_width_via_grammar_is_invalid(self, text: str) -> None:
        n = _grammar_notation(text)
        assert n is not None, f"grammar should recognize {text!r} but got no match"
        # both ISO rules must reject width-invalid sentinels
        assert self.s6.matches(n, self.contract) is False
        assert self.annex.matches(n, self.contract) is False

    def test_iso_valid_widths_match(self) -> None:
        # 2-digit lat, 3-digit lon valid
        n = _grammar_notation("+48.52+002.20/")
        assert n is not None
        assert self.s6.matches(n, self.contract) is True
        assert self.annex.matches(n, self.contract) is True
        # 4-digit lat (DDMM), 5-digit lon
        n2 = _grammar_notation("+1234.7-09854.1/")
        assert n2 is not None
        assert self.s6.matches(n2, self.contract) is True
        assert self.annex.matches(n2, self.contract) is True
        # 6-digit lat, 7-digit lon (DMS)
        n3 = _grammar_notation("+352139+1384339+3776/")
        assert n3 is not None
        assert self.s6.matches(n3, self.contract) is True


class TestAnnexHRejectsMissingSolidus:
    """Annex H requires trailing solidus; missing is recorded as a defect."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.annex = SectionAnnexHStringExpression()
        self.s6 = Section6CoordinateStructure()

    def test_rejects_missing_solidus_via_grammar(self) -> None:
        n = _grammar_notation("+48.52+002.20")
        assert n is not None
        # missing solidus recorded as a defect; the value stays faithful
        assert n.latitude == "48.52"
        assert "iso_missing_solidus" in n.defects
        assert self.annex.matches(n, self.contract) is False
        assert self.s6.matches(n, self.contract) is False

    def test_accepts_with_solidus(self) -> None:
        n = _grammar_notation("+48.52+002.20/")
        assert n is not None
        assert self.annex.matches(n, self.contract) is True
        assert self.s6.matches(n, self.contract) is True

    def test_direct_iso_notation_missing_solidus_carries_no_defect(
        self,
    ) -> None:
        # Direct notation (not built by the grammar) carries no defects, so
        # the rule accepts in-range values; the pipeline path always carries
        # the grammar-recorded defect and is rejected (asserted above).
        n_direct = CoordinatesNotation(
            latitude="48.52",
            longitude="2.2",
            altitude=None,
            coord_shape="iso6709",
            compact="48.52, 2.2",
        )
        assert self.s6.matches(n_direct, self.contract) is True


class TestAnnexHRejectsForeignCrs:
    """Annex H: CRSWGS_84 OK, foreign CRS is INVALID."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.annex = SectionAnnexHStringExpression()
        self.s6 = Section6CoordinateStructure()

    def test_accepts_crswgs84(self) -> None:
        n = _grammar_notation("+27.5916+086.5640+8850CRSWGS_84/")
        assert n is not None
        assert self.annex.matches(n, self.contract) is True
        assert self.s6.matches(n, self.contract) is True

    def test_accepts_crswgs84_case_insensitive(self) -> None:
        n = _grammar_notation("+27.5916+086.5640+8850crsWGS_84/")
        assert n is not None
        assert self.annex.matches(n, self.contract) is True

    def test_accepts_crswgs84_without_underscore(self) -> None:
        n = _grammar_notation("+27.5916+086.5640+8850CRSWGS84/")
        assert n is not None
        assert self.annex.matches(n, self.contract) is True

    def test_rejects_foreign_crs_via_grammar(self) -> None:
        for crs in ("CRSPS56", "CRSNAD83", "CRSET50"):
            text = f"+27.5916+086.5640+8850{crs}/"
            n = _grammar_notation(text)
            assert n is not None, f"grammar should recognize {text}"
            assert "foreign_crs" in n.defects
            assert self.annex.matches(n, self.contract) is False
            assert self.s6.matches(n, self.contract) is False

    def test_rejects_foreign_crs_ps56_specifically(self) -> None:
        n = _grammar_notation("+27.5916+086.5640+8850CRSPS56/")
        assert n is not None
        assert self.annex.matches(n, self.contract) is False


class TestNormalizeAgreement:
    """All four rules' normalize return identical compact for same point."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()
        self.rules = [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ]

    @pytest.mark.parametrize(
        ("lat", "lon", "alt"),
        [
            ("48.8577", "2.295", None),
            ("-41.5", "81", None),
            ("0", "0", None),
            ("27.5916", "86.564", "8850"),
            ("48.8577", "2.295", "100"),
        ],
    )
    def test_normalize_agreement_same_point(
        self, lat: str, lon: str, alt: str | None
    ) -> None:
        compact = f"{lat}, {lon}" + (f", {alt}" if alt is not None else "")
        notations = [
            CoordinatesNotation(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                coord_shape="dd",
                compact=compact,
            ),
            CoordinatesNotation(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                coord_shape="iso6709",
                compact=compact,
            ),
            CoordinatesNotation(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                coord_shape="geo_uri",
                compact=compact,
            ),
            CoordinatesNotation(
                latitude=lat,
                longitude=lon,
                altitude=alt,
                coord_shape="geojson",
                compact=compact,
            ),
        ]
        # Each rule's normalize should be compact (folded)
        results = []
        for rule in self.rules:
            # s6 for dd/iso, 5870 for geo_uri, 7946 for geojson
            # Agreement: all normalize same dd compact identically
            results.append(rule.normalize(notations[0], self.contract))
        # all four should agree
        assert len(set(results)) == 1
        assert results[0] == compact

    def test_normalize_agreement_across_shapes_via_grammar(self) -> None:
        # Same point via different carrier grammars should normalize to same compact
        grammars_points = [
            _grammar_notation("48.8577, 2.295"),
            _grammar_notation("geo:48.8577,2.295"),
            _grammar_notation("[2.295, 48.8577]"),
            _grammar_notation("+48.8577+002.2950/"),
        ]
        assert all(n is not None for n in grammars_points)
        # All should have same compact "48.8577, 2.295"
        compacts = [n.compact for n in grammars_points if n is not None]  # type: ignore[union-attr]
        assert len(set(compacts)) == 1
        contract = CoordinatesContract()
        rules = [
            Section6CoordinateStructure(),
            Section33GeoUriValidity(),
            Section311Position(),
            SectionAnnexHStringExpression(),
        ]
        for n in grammars_points:
            assert n is not None
            for rule in rules:
                assert rule.normalize(n, contract) == n.compact


class TestNormalizeDefaultIsDecimalPair:
    """Normalize returns notation.compact (decimal pair) after -0 fold."""

    def setup_method(self) -> None:
        self.contract = CoordinatesContract()

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_normalize_returns_compact(self, rule: object) -> None:
        n = CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        )
        # for iso/geo shapes, the compact is still decimal pair
        assert rule.normalize(n, self.contract) == n.compact

    def test_normalize_ignores_shape_returns_compact(self) -> None:
        contract = CoordinatesContract()
        for shape in ("dd", "iso6709", "geo_uri", "geojson"):
            n = CoordinatesNotation(
                latitude="0",
                longitude="0",
                altitude=None,
                coord_shape=shape,
                compact="0, 0",
            )
            r = Section6CoordinateStructure()
            # even if shape mismatched for rule, normalize still folds compact
            assert r.normalize(n, contract) == "0, 0"


class TestNormalizeFoldsNegativeZero:
    """Normalize folds -0.0 components to 0."""

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_folds_negative_zero(self, rule: object) -> None:
        contract = CoordinatesContract()
        # Shape per rule; normalize is shape-agnostic
        shape = "dd"
        if rule.name == "Section 3.3-geo-uri-validity":
            shape = "geo_uri"
        elif rule.name == "Section 3.1.1-position":
            shape = "geojson"
        elif rule.name == "Section Annex-h-string-expression":
            shape = "iso6709"
        n = CoordinatesNotation(
            latitude="-0.0",
            longitude="122.0",
            altitude=None,
            coord_shape=shape,
            compact="-0.0, 122.0",
        )
        result = rule.normalize(n, contract)
        assert result == "0, 122"

    def test_folds_negative_zero_both_components(self) -> None:
        contract = CoordinatesContract()
        rule = Section6CoordinateStructure()
        n = CoordinatesNotation(
            latitude="-0.0",
            longitude="-0.0",
            altitude=None,
            coord_shape="dd",
            compact="-0.0, -0.0",
        )
        assert rule.normalize(n, contract) == "0, 0"

    def test_folds_negative_zero_with_altitude(self) -> None:
        contract = CoordinatesContract()
        rule = Section6CoordinateStructure()
        n = CoordinatesNotation(
            latitude="-0.0",
            longitude="122.0",
            altitude="-0.0",
            coord_shape="dd",
            compact="-0.0, 122.0, -0.0",
        )
        assert rule.normalize(n, contract) == "0, 122, 0"

    def test_grammar_negative_zero_folded_before_rule(self) -> None:
        # Grammar already folds -0.0 to 0; rule should keep it folded
        n = _grammar_notation("-0.0,122.0")
        assert n is not None
        assert n.latitude == "0"
        contract = CoordinatesContract()
        for rule in [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ]:
            # Normalize folds even for non-matching shapes
            shape = "dd"
            if rule.name == "Section 3.3-geo-uri-validity":
                shape = "geo_uri"
            elif rule.name == "Section 3.1.1-position":
                shape = "geojson"
            elif rule.name == "Section Annex-h-string-expression":
                shape = "iso6709"
            n2 = CoordinatesNotation(
                latitude="-0.0",
                longitude="122.0",
                altitude=None,
                coord_shape=shape,
                compact="-0.0, 122.0",
            )
            assert rule.normalize(n2, contract) == "0, 122"


class TestMatchesNeverRaises:
    """Rules never raise — feed None, empty, garbage → False, no exception."""

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_matches_never_raises_on_none(self, rule: object) -> None:
        contract = CoordinatesContract()
        # Should not raise even when notation is None
        try:
            result = rule.matches(None, contract)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"{rule.name} raised on None: {exc!r}")
        assert result is False

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_matches_never_raises_on_garbage_strings(self, rule: object) -> None:
        contract = CoordinatesContract()
        garbage_notations = [
            CoordinatesNotation(
                latitude="", longitude="", altitude=None, coord_shape="dd", compact=", "
            ),
            CoordinatesNotation(
                latitude="abc",
                longitude="xyz",
                altitude=None,
                coord_shape="dd",
                compact="abc, xyz",
            ),
            CoordinatesNotation(
                latitude="NaN",
                longitude="Infinity",
                altitude=None,
                coord_shape="dd",
                compact="NaN, Infinity",
            ),
            CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude="not-a-number",
                coord_shape="dd",
                compact="48.8577, 2.295, not-a-number",
            ),
            CoordinatesNotation(
                latitude="48.8577",
                longitude="2.295",
                altitude=None,
                coord_shape="dd",
                compact="48.8577, 2.295",
            ),
        ]
        for n in garbage_notations:
            try:
                result = rule.matches(n, contract)
            except Exception as exc:  # pragma: no cover
                pytest.fail(f"{rule.name} raised on {n!r}: {exc!r}")
            assert result in (True, False)

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_matches_never_raises_on_wrong_type(self, rule: object) -> None:
        contract = CoordinatesContract()

        class Dummy:
            pass

        for bad in [Dummy(), 123, "string", {}, []]:  # type: ignore[list-item]
            try:
                result = rule.matches(bad, contract)  # type: ignore[arg-type]
            except Exception as exc:  # pragma: no cover
                pytest.fail(f"{rule.name} raised on bad type {bad!r}: {exc!r}")
            assert result is False

    @pytest.mark.parametrize(
        "rule",
        [
            Section6CoordinateStructure(),
            SectionAnnexHStringExpression(),
            Section33GeoUriValidity(),
            Section311Position(),
        ],
    )
    def test_normalize_never_raises_on_garbage(self, rule: object) -> None:
        contract = CoordinatesContract()
        garbage = CoordinatesNotation(
            latitude="not-a-number",
            longitude="also-bad",
            altitude=None,
            coord_shape="dd",
            compact="not-a-number, also-bad",
        )
        try:
            result = rule.normalize(garbage, contract)
        except Exception as exc:  # pragma: no cover
            pytest.fail(f"{rule.name} normalize raised: {exc!r}")
        assert isinstance(result, str)

    def test_matches_with_decimal_edge_values(self) -> None:
        # Decimal edge: very precise values, trailing zeros, scientific not needed
        contract = CoordinatesContract()
        rule = Section6CoordinateStructure()
        for lat, lon in [
            ("90", "180"),
            ("-90", "-180"),
            ("0.000001", "0.000001"),
            ("89.999999", "179.999999"),
            ("00.000", "000.000"),
        ]:
            n = CoordinatesNotation(
                latitude=lat,
                longitude=lon,
                altitude=None,
                coord_shape="dd",
                compact=f"{lat}, {lon}",
            )
            try:
                result = rule.matches(n, contract)
            except Exception as exc:  # pragma: no cover
                pytest.fail(f"raised on Decimal edge {lat},{lon}: {exc!r}")
            assert result in (True, False)


class TestOutputFormatTokenAbsent:
    """Rules must not contain the token output_format (purity scan)."""

    @pytest.mark.parametrize(
        "path_str",
        [
            "paxman/capabilities/Coordinates/rules/iso_6709_ed2022.py",
            "paxman/capabilities/Coordinates/rules/rfc_5870_ed2010.py",
            "paxman/capabilities/Coordinates/rules/rfc_7946_ed2016.py",
        ],
    )
    def test_output_format_token_absent(self, path_str: str) -> None:
        p = Path(path_str)
        assert p.exists(), f"rule file {path_str} does not exist"
        text = p.read_text(encoding="utf-8")
        assert "output_format" not in text, f"found forbidden token in {path_str}"
