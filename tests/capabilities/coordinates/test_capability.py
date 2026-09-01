"""Tests for Coordinates capability wiring and format_value."""

from __future__ import annotations

import dataclasses
import inspect
from inspect import Parameter

import pytest

from paxman.capabilities.Coordinates.capability import CoordinatesCapability
from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

CAP = CoordinatesCapability()


def _notation(
    lat: str = "48.8577",
    lon: str = "2.295",
    alt: str | None = None,
    shape: str = "dd",
) -> CoordinatesNotation:
    compact = f"{lat}, {lon}"
    if alt is not None:
        compact += f", {alt}"
    return CoordinatesNotation(
        latitude=lat,
        longitude=lon,
        altitude=alt,
        coord_shape=shape,
        compact=compact,
    )


def test_metadata() -> None:
    assert CoordinatesCapability.name == "coordinates"
    assert CAP.name == "coordinates"


def test_get_grammars() -> None:
    grammars = CAP.get_grammars()
    assert len(grammars) == 1
    names = {g.name for g in grammars}
    assert names == {"coordinates_recognition"}


def test_get_rules() -> None:
    rules = CAP.get_rules()
    names = {r.name for r in rules}
    assert names == {
        "Section 6-coordinate-structure",
        "Section Annex-h-string-expression",
        "Section 3.3-geo-uri-validity",
        "Section 3.1.1-position",
    }


def test_get_rules_strategies_all_parser() -> None:
    for rule in CAP.get_rules():
        assert rule.strategy == RuleStrategy.PARSER


def test_target_semantics_all_coordinates_recognition() -> None:
    for rule in CAP.get_rules():
        assert rule.target_semantics == frozenset({"coordinates_recognition"})


def test_grammar_and_rule_names_convention() -> None:
    for rule in CAP.get_rules():
        assert rule.name.startswith("Section"), rule.name
    for grammar in CAP.get_grammars():
        # grammar names are snake_case lower
        assert grammar.name == grammar.name.lower()
        assert grammar.name == "coordinates_recognition"
        assert grammar.semantics == "coordinates_recognition"
        assert grammar.semantics


def test_notation_frozen_hashable_slots() -> None:
    assert dataclasses.is_dataclass(CoordinatesNotation)
    assert hasattr(CoordinatesNotation, "__slots__")
    n = _notation()
    with pytest.raises(dataclasses.FrozenInstanceError):
        n.latitude = "0"  # type: ignore[misc]
    # hashable and deduplicates
    s = {_notation(), _notation()}
    assert len(s) == 1
    assert hash(n) is not None


def test_create_contract_defaults() -> None:
    c = CAP.create_contract()
    assert isinstance(c, CoordinatesContract)
    assert c.output_format == "decimal"
    assert c.capability_name == "coordinates"
    # module-level factory also
    from paxman.capabilities.Coordinates.contract import create_contract

    c2 = create_contract()
    assert isinstance(c2, CoordinatesContract)
    assert c2.output_format == "decimal"


def test_create_contract_keyword_only() -> None:
    with pytest.raises(TypeError):
        CAP.create_contract("iso6709")  # type: ignore[misc]
    from paxman.capabilities.Coordinates.contract import create_contract

    with pytest.raises(TypeError):
        create_contract("iso6709")  # type: ignore[misc]
    # signature is keyword-only
    sig = inspect.signature(CAP.create_contract)
    params = list(sig.parameters.values())
    assert all(p.kind == Parameter.KEYWORD_ONLY for p in params)
    sig2 = inspect.signature(create_contract)
    assert all(p.kind == Parameter.KEYWORD_ONLY for p in sig2.parameters.values())


def test_format_value_decimal_identity() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    # direct capability call with compact as value
    assert CAP.format_value(n.compact, "decimal", n) == n.compact
    assert CAP.format_value("48.8577, 2.295", "decimal", n) == "48.8577, 2.295"
    assert CAP.format_value("48.8577, 2.295", None, n) == "48.8577, 2.295"
    # None should resolve to decimal identity
    assert CAP.format_value(n.compact, None, n) == n.compact


def test_format_value_iso6709() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    result = CAP.format_value(n.compact, "iso6709", n)
    assert result == "+48.8577+002.295/"
    assert result.endswith("/")
    assert "48.8577" in result
    assert "002.295" in result
    # lon padded to 3 integer digits
    # with altitude
    n_alt = _notation(lat="48.8577", lon="2.295", alt="8850")
    result_alt = CAP.format_value(n_alt.compact, "iso6709", n_alt)
    assert result_alt == "+48.8577+002.295+8850/"
    assert result_alt.endswith("/")
    assert "8850" in result_alt
    assert "48.8577" in result_alt
    assert "002.295" in result_alt


def test_format_value_geo_uri() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    assert CAP.format_value(n.compact, "geo_uri", n) == "geo:48.8577,2.295"
    n_alt = _notation(lat="48.8577", lon="2.295", alt="8850")
    assert CAP.format_value(n_alt.compact, "geo_uri", n_alt) == "geo:48.8577,2.295,8850"


def test_format_value_geojson_pair_lon_first() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    assert CAP.format_value(n.compact, "geojson_pair", n) == "[2.295, 48.8577]"
    n_alt = _notation(lat="48.8577", lon="2.295", alt="8850")
    expected = "[2.295, 48.8577, 8850]"
    assert CAP.format_value(n_alt.compact, "geojson_pair", n_alt) == expected
    # lon-first ordering: result starts with lon
    result = CAP.format_value(n.compact, "geojson_pair", n)
    assert result.startswith("[2.295")


def test_format_value_dms_unicode() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    result = CAP.format_value(n.compact, "dms", n)
    assert "°" in result
    assert "′" in result
    assert "″" in result
    assert "N" in result
    assert "E" in result
    # negative lat/lon contains S,W
    n2 = _notation(lat="-48.8577", lon="-2.295", alt=None)
    result2 = CAP.format_value(n2.compact, "dms", n2)
    assert "S" in result2
    assert "W" in result2
    assert "°" in result2
    assert "′" in result2
    assert "″" in result2
    # hemisphere letters immediately after digits
    # check structure: contains both lat and lon parts
    assert result.count("°") == 2
    assert result.count("′") == 2
    assert result.count("″") == 2


def test_format_value_dm() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    result = CAP.format_value(n.compact, "dm", n)
    assert "°" in result
    assert "′" in result
    assert "N" in result
    assert "E" in result
    n2 = _notation(lat="-48.8577", lon="-2.295", alt=None)
    result2 = CAP.format_value(n2.compact, "dm", n2)
    assert "S" in result2
    assert "W" in result2
    assert "°" in result2
    assert "′" in result2


def test_format_value_altitude_emitted_when_present() -> None:
    n_alt = _notation(lat="48.8577", lon="2.295", alt="8850")
    # decimal is identity — input value contains altitude
    assert "8850" in CAP.format_value(n_alt.compact, "decimal", n_alt)
    assert "8850" in CAP.format_value(n_alt.compact, None, n_alt)
    assert "8850" in CAP.format_value(n_alt.compact, "iso6709", n_alt)
    assert "8850" in CAP.format_value(n_alt.compact, "geo_uri", n_alt)
    assert "8850" in CAP.format_value(n_alt.compact, "geojson_pair", n_alt)
    assert "8850" in CAP.format_value(n_alt.compact, "dms", n_alt)
    assert "8850" in CAP.format_value(n_alt.compact, "dm", n_alt)


def test_format_value_altitude_omitted_when_none() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    assert "8850" not in CAP.format_value(n.compact, "decimal", n)
    assert "8850" not in CAP.format_value(n.compact, "iso6709", n)
    # iso without altitude should be +lat+lon/ only, no extra +
    assert CAP.format_value(n.compact, "iso6709", n).count("+") == 2
    assert "8850" not in CAP.format_value(n.compact, "geo_uri", n)
    assert CAP.format_value(n.compact, "geo_uri", n) == "geo:48.8577,2.295"
    assert "8850" not in CAP.format_value(n.compact, "geojson_pair", n)
    assert CAP.format_value(n.compact, "geojson_pair", n) == "[2.295, 48.8577]"
    assert "8850" not in CAP.format_value(n.compact, "dms", n)
    assert "8850" not in CAP.format_value(n.compact, "dm", n)


def test_format_value_round_trip() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    first = CAP.format_value(n.compact, "decimal", n)
    second = CAP.format_value(first, "decimal", n)
    assert first == second == n.compact
    # also check that formatting the result again with same notation is idempotent
    # (notation does not change, so second call same as first)
    n_alt = _notation(lat="48.8577", lon="2.295", alt="8850")
    first_alt = CAP.format_value(n_alt.compact, "decimal", n_alt)
    second_alt = CAP.format_value(first_alt, "decimal", n_alt)
    assert first_alt == second_alt


def test_format_value_unknown_returns_value() -> None:
    n = _notation(lat="48.8577", lon="2.295", alt=None)
    assert CAP.format_value("48.8577, 2.295", "unknown_format", n) == "48.8577, 2.295"
    assert CAP.format_value(n.compact, "bogus", n) == n.compact
    assert CAP.format_value(n.compact, "utm", n) == n.compact
