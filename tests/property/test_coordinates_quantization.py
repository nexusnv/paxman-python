"""Coordinates dms/dm quantization obligations — documented-quantization lock.

Classification being locked: ``dms`` and ``dm`` are documented quantizations
of the 6 dp canonical space. ``dms`` renders seconds as integers (render
quantum 1 arcsecond ~= 2.78e-4 deg) and ``dm`` renders minutes to 0.001 arc
minutes; sub-quantum canonical digits are not recoverable from the rendering.

Registry exception (mirrors ``test_money_properties.py`` and
``tests/property/test_reentry_invariant.py``): property tests normally stay
off the registry and the frozen pipeline (tests/AGENTS.md, CONVENTIONS),
driving grammars/rules/``format_value`` directly. Both properties here are
inherently full-pipeline (``canonicalize()`` in to out) — the fixpoint feeds
the pipeline its own emitted rendering back through recognition, validation,
and ``format_value`` — so this module uses a local ``_fresh_registry``
autouse fixture (``reset_registry()`` + ``register_all_shipped()``) around
each test. It is the third documented exception to the property-layer
registry ban.

The two properties (bounds apply per lat/lon component):

1. Render stability (fixpoint), ``W -> W``: for
   ``W = canonicalize(text, C_fmt).canonicalized_value``,
   ``canonicalize(W, C_fmt)`` succeeds and returns ``W`` unchanged.
2. Bounded-drift pre-image, ``V -> W -> V'``: re-canonicalizing the
   rendering under the default contract drifts by at most half a render
   quantum plus half the canonical quantum — ``Decimal("0.00014")`` for
   ``dms``, ``Decimal("0.000009")`` for ``dm``.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.bootstrap import register_all_shipped
from paxman.api.canonicalize import canonicalize
from paxman.capabilities import Coordinates
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register all shipped capabilities around each test.

    Registration happens once per test, before the hypothesis examples run;
    ``run_capability`` freezes the registry on the first example, which is
    fine because every shipped capability is already present (same exception
    pattern as ``test_money_properties.py`` — see module docstring).
    """
    reset_registry()
    register_all_shipped()
    yield
    reset_registry()


# Fixture table — the six Task-1 empirical inputs (label, input_text).
FIXTURE_INPUTS: tuple[tuple[str, str], ...] = (
    ("london", "51.507412, -0.1278"),
    # 59.5008" -> 60" carry under dms; sits at ~99% of the dms drift bound.
    ("dms-carry", "51.516528, -0.1278"),
    # 59.99952' -> 60.000' carry under dm; sits at ~99% of the dm drift bound.
    ("dm-carry", "51.999992, -0.1278"),
    ("sydney", "-33.868820, 151.215293"),
    ("null-island", "0.000000, 0.000000"),
    ("extreme", "89.999999, -179.999999"),
)

_FORMATS: tuple[str, str] = ("dms", "dm")

_FIXPOINT_CASES: list[pytest.ParamSet] = [
    pytest.param(label, text, fmt, id=f"{label}-{fmt}")
    for label, text in FIXTURE_INPUTS
    for fmt in _FORMATS
]


@pytest.mark.parametrize(("label", "text", "output_format"), _FIXPOINT_CASES)
def test_dms_dm_reentry_fixpoint(label: str, text: str, output_format: str) -> None:
    """Render stability: a dms/dm rendering re-canonicalizes to itself.

    ``W = canonicalize(text, C_fmt)`` must succeed, and feeding ``W`` back
    through the same contract must succeed with
    ``second.canonicalized_value == W``. Self-contained: no hardcoded
    expected canonical strings are asserted.
    """
    del label
    contract = Coordinates.create_contract(output_format=output_format)
    first = canonicalize(text, contract)
    assert first.status is Resolution.SUCCESS
    w = first.canonicalized_value
    assert w is not None
    second = canonicalize(w, contract)
    assert second.status is Resolution.SUCCESS
    assert second.canonicalized_value == w


@pytest.mark.parametrize(("label", "text", "output_format"), _FIXPOINT_CASES)
def test_dms_dm_bounded_drift_preimage(
    label: str, text: str, output_format: str
) -> None:
    """Bounded drift: V -> W -> V' stays within half a render quantum.

    Derivation (per lat/lon component, half render quantum plus half the
    1e-6 deg canonical quantum):
    dms: 1/2 * (1/3600) + 1/2 * 1e-6 = 1.39389e-4 <= 1.4e-4;
    dm: 1/2 * (0.001/60) + 1/2 * 1e-6 = 8.8333e-6 <= 9e-6.
    """
    del label
    bound = Decimal("0.00014") if output_format == "dms" else Decimal("0.000009")
    default_contract = Coordinates.create_contract()
    fmt_contract = Coordinates.create_contract(output_format=output_format)
    v = canonicalize(text, default_contract).canonicalized_value
    assert v is not None
    w = canonicalize(text, fmt_contract).canonicalized_value
    assert w is not None
    v2 = canonicalize(w, default_contract).canonicalized_value
    assert v2 is not None
    lat_str, lon_str = v.split(", ")
    lat2_str, lon2_str = v2.split(", ")
    assert abs(Decimal(lat_str) - Decimal(lat2_str)) <= bound
    assert abs(Decimal(lon_str) - Decimal(lon2_str)) <= bound


@given(
    lat=st.decimals(min_value=-90, max_value=90, places=6),
    lon=st.decimals(min_value=-180, max_value=180, places=6),
)
def test_dms_dm_fixpoint_random_decimals(lat: Decimal, lon: Decimal) -> None:
    """Render stability holds for random 6 dp decimals, both formats."""
    text = f"{lat}, {lon}"
    for fmt in _FORMATS:
        contract = Coordinates.create_contract(output_format=fmt)
        first = canonicalize(text, contract)
        assert first.status is Resolution.SUCCESS
        w = first.canonicalized_value
        assert w is not None
        second = canonicalize(w, contract)
        assert second.status is Resolution.SUCCESS
        assert second.canonicalized_value == w
