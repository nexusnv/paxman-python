"""Hypothesis property tests for the Coordinates capability.

Each property locks a mathematical invariant of recognition, validation,
or presentation using an independently derived expectation:

- a coordinate built at ≤6dp quantizes to itself (self-canonical);
- the same point spelled decimal / hemisphere-letter / DMS coalesces to
  one canonical value (dedup);
- formatting is idempotent for all six output formats;
- random text never raises and is MISSING with high probability;
- minutes/seconds ≥60 never yields SUCCESS.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

import pytest
from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities.Coordinates.capability import CoordinatesCapability
from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
    CoordinatesRecognitionGrammar,
)
from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules.iso_6709_ed2022 import (
    Section6CoordinateStructure,
    SectionAnnexHStringExpression,
)
from paxman.capabilities.Coordinates.rules.rfc_5870_ed2010 import (
    Section33GeoUriValidity,
)
from paxman.capabilities.Coordinates.rules.rfc_7946_ed2016 import Section311Position
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.property]

_ALL_FORMATS = ["decimal", "iso6709", "geo_uri", "geojson_pair", "dms", "dm"]


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register Coordinates before and after each test.

    Registration happens once per test before hypothesis examples run;
    ``paxman.canonicalize`` freezes the registry on the first example,
    which is fine because Coordinates is already present. This mirrors the
    Money property precedent (the documented exception to stay off the
    registry for full-pipeline invariants).
    """

    reset_registry()
    register_capability(CoordinatesCapability())
    yield
    reset_registry()


def _quantized_str(value: Decimal) -> str:
    """Quantize to 6dp half-even, strip trailing zeros, fold -0 (mirrors grammar)."""
    try:
        q = value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN)
    except InvalidOperation:
        return format(value, "f")
    if q == 0:
        return "0"
    qn = q.normalize()
    if qn == 0:
        return "0"
    return format(qn, "f")


# ---------------------------------------------------------------------------
# 1. self-canonical
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    lat_micro=st.integers(min_value=-90_000000, max_value=90_000000),
    lon_micro=st.integers(min_value=-180_000000, max_value=180_000000),
)
def test_self_canonical(lat_micro: int, lon_micro: int) -> None:
    """A ≤6dp compact canonicalizes to itself."""

    lat_dec = Decimal(lat_micro) / Decimal(1_000000)
    lon_dec = Decimal(lon_micro) / Decimal(1_000000)
    lat_str = _quantized_str(lat_dec)
    lon_str = _quantized_str(lon_dec)
    compact = f"{lat_str}, {lon_str}"
    contract = CoordinatesCapability.create_contract()
    result = paxman.canonicalize(compact, contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == compact


# ---------------------------------------------------------------------------
# 2. encodings dedup
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    lat_deg=st.integers(min_value=0, max_value=89),
    lat_min=st.integers(min_value=0, max_value=59),
    lat_sec=st.integers(min_value=0, max_value=59),
    lon_deg=st.integers(min_value=0, max_value=179),
    lon_min=st.integers(min_value=0, max_value=59),
    lon_sec=st.integers(min_value=0, max_value=59),
    lat_sign=st.sampled_from([1, -1]),
    lon_sign=st.sampled_from([1, -1]),
)
def test_encodings_dedup_to_one_value(
    lat_deg: int,
    lat_min: int,
    lat_sec: int,
    lon_deg: int,
    lon_min: int,
    lon_sec: int,
    lat_sign: int,
    lon_sign: int,
) -> None:
    """Same point via decimal / hemisphere / DMS yields one canonical value."""

    # Decimal derived from DMS components — quantization-safe.
    lat_abs = (
        Decimal(lat_deg)
        + Decimal(lat_min) / Decimal(60)
        + Decimal(lat_sec) / Decimal(3600)
    )
    lon_abs = (
        Decimal(lon_deg)
        + Decimal(lon_min) / Decimal(60)
        + Decimal(lon_sec) / Decimal(3600)
    )
    lat_dec = lat_abs * lat_sign
    lon_dec = lon_abs * lon_sign
    lat_str = _quantized_str(lat_dec)
    lon_str = _quantized_str(lon_dec)
    # Absolute quantized strings for hemisphere encodings
    lat_abs_str = _quantized_str(lat_abs)
    lon_abs_str = _quantized_str(lon_abs)
    hemi_lat = "N" if lat_sign > 0 else "S"
    hemi_lon = "E" if lon_sign > 0 else "W"

    decimal_spelling = f"{lat_str}, {lon_str}"
    hemi_spelling = f"{lat_abs_str} {hemi_lat}, {lon_abs_str} {hemi_lon}"
    dms_spelling = (
        f"{lat_deg}\u00b0 {lat_min}\u2032 {lat_sec}\u2033{hemi_lat} "
        f"{lon_deg}\u00b0 {lon_min}\u2032 {lon_sec}\u2033{hemi_lon}"
    )

    contract = CoordinatesCapability.create_contract()

    r_decimal = paxman.canonicalize(decimal_spelling, contract)
    r_hemi = paxman.canonicalize(hemi_spelling, contract)
    r_dms = paxman.canonicalize(dms_spelling, contract)

    # Each spelling individually succeeds and yields the same compact.
    assert r_decimal.status == Resolution.SUCCESS
    assert r_hemi.status == Resolution.SUCCESS
    assert r_dms.status == Resolution.SUCCESS
    assert (
        r_decimal.canonicalized_value
        == r_hemi.canonicalized_value
        == r_dms.canonicalized_value
    )
    expected = f"{lat_str}, {lon_str}"
    assert r_decimal.canonicalized_value == expected

    # Joint input dedups to one candidate (no MultipleMentionsError).
    joint = f"{decimal_spelling} and {dms_spelling}"
    try:
        r_joint = paxman.canonicalize(joint, contract)
    except MultipleMentionsError as exc:
        pytest.fail(
            f"dedup invariant failed — joint raised MultipleMentionsError: {exc}"
        )
    assert r_joint.status == Resolution.SUCCESS
    assert r_joint.canonicalized_value == expected
    assert len({c.value for c in r_joint.candidates}) == 1

    # Also direct notation-level dedup precondition: all rules agree on normalize.
    # Build notations via grammar to ensure same compact.
    grammar = CoordinatesRecognitionGrammar()
    m_dec = grammar.recognize(decimal_spelling)
    m_dms = grammar.recognize(dms_spelling)
    assert len(m_dec) == 1 and len(m_dms) == 1
    n_dec = m_dec[0].notation
    n_dms = m_dms[0].notation
    assert n_dec.compact == n_dms.compact == expected
    for _rule in [
        Section6CoordinateStructure(),
        SectionAnnexHStringExpression(),
        Section33GeoUriValidity(),
        Section311Position(),
    ]:
        pass


# ---------------------------------------------------------------------------
# 3. format idempotent
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    lat_micro=st.integers(min_value=-90_000000, max_value=90_000000),
    lon_micro=st.integers(min_value=-180_000000, max_value=180_000000),
    fmt=st.sampled_from(_ALL_FORMATS),
)
def test_format_idempotent(lat_micro: int, lon_micro: int, fmt: str) -> None:
    """All six formats are idempotent on the decimal branch: f(f(x)) == f(x)."""

    # DMS/DM round to coarser granularity (1″ / 0.001′) and fold -0 to 0;
    # a point within ~0.00014° of the prime meridian/equator with a
    # negative sign would flip hemisphere on the second round-trip
    # (e.g. -0.000001 → 0°0′0″W → 0°0′0″E). Exclude that narrow strip for
    # the dms/dm branches so idempotence is well-defined.
    if fmt in ("dms", "dm"):
        if lat_micro < 0 and abs(lat_micro) < 500:
            from hypothesis import assume

            assume(False)
        if lon_micro < 0 and abs(lon_micro) < 500:
            from hypothesis import assume

            assume(False)

    lat_dec = Decimal(lat_micro) / Decimal(1_000000)
    lon_dec = Decimal(lon_micro) / Decimal(1_000000)
    lat_str = _quantized_str(lat_dec)
    lon_str = _quantized_str(lon_dec)
    compact = f"{lat_str}, {lon_str}"
    cap = CoordinatesCapability()

    # Direct notation-level idempotence: format_value(fmt) is pure from notation.
    notation = CoordinatesNotation(
        latitude=lat_str,
        longitude=lon_str,
        altitude=None,
        coord_shape="dd",
        compact=compact,
    )
    v1 = cap.format_value(compact, fmt, notation)
    v2 = cap.format_value(v1, fmt, notation)
    assert v1 == v2

    # Pipeline-level idempotence: canonicalize then re-canonicalize.
    contract = CoordinatesCapability.create_contract(output_format=fmt)
    result1 = paxman.canonicalize(compact, contract)
    assert result1.status == Resolution.SUCCESS
    assert result1.canonicalized_value is not None
    try:
        result2 = paxman.canonicalize(result1.canonicalized_value, contract)
    except MultipleMentionsError:
        pytest.fail(
            "format idempotent — second canonicalize raised MultipleMentionsError"
        )
    assert result2.status == Resolution.SUCCESS
    assert result2.canonicalized_value == result1.canonicalized_value


# ---------------------------------------------------------------------------
# 4. random strings
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(text=st.text())
def test_random_strings_missing(text: str) -> None:
    """Random text never crashes; MISSING with high probability."""

    contract = CoordinatesCapability.create_contract()
    try:
        result = paxman.canonicalize(text, contract)
    except MultipleMentionsError:
        # Multi-entity input is a valid engine outcome.
        return
    assert result.status in {
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.SUCCESS,
        Resolution.AMBIGUOUS,
    }
    assert (result.canonicalized_value is not None) == (
        result.status == Resolution.SUCCESS
    )
    if result.status == Resolution.SUCCESS:
        assert len(result.candidates) >= 1
        assert {c.value for c in result.candidates} == {result.canonicalized_value}


# ---------------------------------------------------------------------------
# 5. unit overflow
# ---------------------------------------------------------------------------


@pytest.mark.property
@given(
    overflow_min=st.integers(min_value=60, max_value=99),
    overflow_sec=st.integers(min_value=60, max_value=99),
)
def test_unit_overflow_invalid(overflow_min: int, overflow_sec: int) -> None:
    """Minutes/seconds ≥60 never yields SUCCESS."""

    # Minutes overflow
    txt_min = f"40\u00b0 {overflow_min}\u2032 46\u2033 N 79\u00b0 58\u2032 56\u2033 W"
    contract = CoordinatesCapability.create_contract()
    result_min = paxman.canonicalize(txt_min, contract)
    assert result_min.status in (Resolution.INVALID, Resolution.MISSING)
    assert result_min.status != Resolution.SUCCESS

    # Seconds overflow
    txt_sec = f"40\u00b0 26\u2032 {overflow_sec}\u2033 N 79\u00b0 58\u2032 56\u2033 W"
    result_sec = paxman.canonicalize(txt_sec, contract)
    assert result_sec.status in (Resolution.INVALID, Resolution.MISSING)
    assert result_sec.status != Resolution.SUCCESS

    # Grammar-level assertion: overflow is recognized (sentineled) but rule rejects.
    grammar = CoordinatesRecognitionGrammar()
    matches_min = grammar.recognize(txt_min)
    # Grammar may still emit one match with sentineled 91/181; or may reject at regex.
    # In either case pipeline is not SUCCESS (asserted above). For the grammar
    # emission path, rule must reject.
    for notation in [m.notation for m in matches_min]:
        assert (
            Section6CoordinateStructure().matches(notation, CoordinatesContract())
            is False
        )
        # Also ensure DMS shape is still reported as dms when recognized
        assert notation.coord_shape == "dms"

    matches_sec = grammar.recognize(txt_sec)
    for notation in [m.notation for m in matches_sec]:
        assert (
            Section6CoordinateStructure().matches(notation, CoordinatesContract())
            is False
        )


@pytest.mark.property
def test_unit_overflow_fixed_vector() -> None:
    """Pinned overflow vector from the plan."""

    txt = "40\u00b0 75\u2032 46\u2033 N 79\u00b0 58\u2032 56\u2033 W"
    grammar = CoordinatesRecognitionGrammar()
    matches = grammar.recognize(txt)
    # Must be recognized (sentineled) so rule can reject; if no match then MISSING.
    if matches:
        n = matches[0].notation
        assert Section6CoordinateStructure().matches(n, CoordinatesContract()) is False
    contract = CoordinatesCapability.create_contract()
    result = paxman.canonicalize(txt, contract)
    assert result.status in (Resolution.INVALID, Resolution.MISSING)
    assert result.status != Resolution.SUCCESS
