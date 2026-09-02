"""Tests for CoordinatesNotation."""

import dataclasses

import pytest

from paxman.capabilities.Coordinates.notation import CoordinatesNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash() -> None:
    assert dataclasses.is_dataclass(CoordinatesNotation)
    assert hasattr(CoordinatesNotation, "__slots__")
    n = CoordinatesNotation(
        latitude="48.8577",
        longitude="2.295",
        altitude=None,
        coord_shape="dd",
        compact="48.8577, 2.295",
    )
    # frozen
    with pytest.raises(dataclasses.FrozenInstanceError):
        n.latitude = "0"  # type: ignore[misc]
    # hashable
    s = {
        CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        ),
        CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
        ),
    }
    assert len(s) == 1


def test_valid_shapes_construct() -> None:
    for shape in ("dd", "ddm", "dms", "iso6709", "geo_uri", "geojson"):
        n = CoordinatesNotation(
            latitude="0",
            longitude="0",
            altitude=None,
            coord_shape=shape,
            compact="0, 0",
        )
        assert n.coord_shape == shape


def test_invalid_shape_raises_value_error() -> None:
    with pytest.raises(ValueError, match="invalid coord_shape"):
        CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="utm",
            compact="48.8577, 2.295",
        )


def test_compact_consistency() -> None:
    lat = "48.8577"
    lon = "2.295"
    compact = f"{lat}, {lon}"
    n = CoordinatesNotation(
        latitude=lat,
        longitude=lon,
        altitude=None,
        coord_shape="dd",
        compact=compact,
    )
    assert n.compact == f"{n.latitude}, {n.longitude}"


def test_minimal_fields() -> None:
    n = CoordinatesNotation(
        latitude="48.8577",
        longitude="2.295",
        altitude=None,
        coord_shape="dd",
        compact="48.8577, 2.295",
    )
    assert n.latitude == "48.8577"
    assert n.longitude == "2.295"
    assert n.altitude is None
    assert n.coord_shape == "dd"
    assert n.compact == "48.8577, 2.295"


def test_altitude_field() -> None:
    n = CoordinatesNotation(
        latitude="27.5916",
        longitude="86.564",
        altitude="8850",
        coord_shape="iso6709",
        compact="27.5916, 86.564, 8850",
    )
    assert n.altitude == "8850"


def test_defects_default_empty() -> None:
    n = CoordinatesNotation(
        latitude="48.8577",
        longitude="2.295",
        altitude=None,
        coord_shape="dd",
        compact="48.8577, 2.295",
    )
    assert n.defects == ()


def test_valid_defects_construct() -> None:
    n = CoordinatesNotation(
        latitude="41.5",
        longitude="81",
        altitude=None,
        coord_shape="dd",
        compact="41.5, 81",
        defects=("sign_hemisphere_conflict",),
    )
    assert n.defects == ("sign_hemisphere_conflict",)


def test_invalid_defect_raises_value_error() -> None:
    with pytest.raises(ValueError, match="invalid defect"):
        CoordinatesNotation(
            latitude="48.8577",
            longitude="2.295",
            altitude=None,
            coord_shape="dd",
            compact="48.8577, 2.295",
            defects=("sentinel_91",),
        )


def test_defects_participate_in_equality() -> None:
    base = dict(
        latitude="41.5",
        longitude="81",
        altitude=None,
        coord_shape="dd",
        compact="41.5, 81",
    )
    clean = CoordinatesNotation(**base)
    defective = CoordinatesNotation(**base, defects=("sign_hemisphere_conflict",))
    assert clean != defective
    assert hash(clean) != hash(defective)
