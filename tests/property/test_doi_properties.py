"""Hypothesis robustness properties for the DOI capability.

Each property locks a pipeline-level invariant using independently derived
expectations:

- a generated valid DOI (4-9-digit registrant, quoteless suffix) always
  resolves to itself (fixed point);
- carrier variants (upper/URL/www/label/urn/info) of one value all resolve
  to the same canonical;
- random printable input never raises (besides ``MultipleMentionsError``)
  and SUCCESS implies a literal ``10.`` shape in the input (MISSING bias).

Self-canonicalization fixed points live in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 encoding
lives in ``tests/property/test_output_format_preservation.py`` CLASS_MAP.
This module pins only the fuzz-robustness half.

Registry posture: the fuzz properties drive the full pipeline (robustness
cannot be observed off-pipeline), so this module uses a local
``_fresh_registry`` fixture registering only DOI — the documented
``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

import string
from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.DOI.capability import DOICapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Reset the registry and register DOI around each test."""
    reset_registry()
    register_capability(DOICapability())
    yield
    reset_registry()


_digits = st.text(alphabet="0123456789", min_size=4, max_size=9)
_dotted_tail = st.lists(
    st.text(alphabet="0123456789", min_size=1, max_size=3), max_size=2
)
# Interior may use the full opaque alphabet; the final character stays
# alphanumeric so no trailing-punctuation trim applies and the generated
# value is already canonical (fixed point).
_suffix_interior = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789.-_%/", max_size=12
)
_suffix_final = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=3
)


def _bare(registrant: str, tail: list[str], suffix: str) -> str:
    prefix = "10." + registrant + "".join(f".{t}" for t in tail)
    return f"{prefix}/{suffix}"


@given(
    registrant=_digits,
    tail=_dotted_tail,
    interior=_suffix_interior,
    final=_suffix_final,
)
def test_generated_valid_dois_self_canonicalize(
    registrant: str, tail: list[str], interior: str, final: str
) -> None:
    """Any shaped DOI name resolves to itself byte-identically."""
    text = _bare(registrant, tail, interior + final)
    result = canonicalize(text, DOICapability.create_contract())

    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == text


@given(
    registrant=_digits,
    suffix=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=10
    ),
)
def test_carrier_variants_agree(registrant: str, suffix: str) -> None:
    """Case/URL/label/URN spellings of one value share one canonical."""
    canon = f"10.{registrant}/{suffix}"
    variants = [
        canon,
        canon.upper(),
        f"https://doi.org/{canon}",
        f"https://www.doi.org/{canon}",
        f"doi:{canon}",
        f"DOI: {canon}",
        f"urn:doi:{canon}",
        f"info:doi/{canon}",
    ]
    contract = DOICapability.create_contract()

    seen = set()
    for variant in variants:
        result = canonicalize(variant, contract)
        assert result.status == Resolution.SUCCESS, variant
        seen.add(result.canonicalized_value)
    assert seen == {canon}


@given(text=st.text(alphabet=string.printable, max_size=40))
def test_random_ascii_status_well_formed(text: str) -> None:
    """Random ASCII never raises; SUCCESS implies a literal 10. shape."""
    contract = DOICapability.create_contract()
    try:
        result = canonicalize(text, contract)
    except MultipleMentionsError:
        return

    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )
    if result.status != Resolution.SUCCESS:
        assert result.candidates == ()
    else:
        assert result.canonicalized_value is not None
        assert "10." in text


def test_overlong_registrant_missing() -> None:
    """A 10-digit registrant never claims (ecosystem 4-9 bound)."""
    result = canonicalize("10.1234567890/x", DOICapability.create_contract())
    assert result.status == Resolution.MISSING


def test_url_round_trip() -> None:
    """The url rendering re-enters the default contract onto bare."""
    text = "10.1038/nature12345"
    rendered = canonicalize(text, DOICapability.create_contract(output_format="url"))
    assert rendered.status == Resolution.SUCCESS
    assert rendered.canonicalized_value == f"https://doi.org/{text}"
    reentry = canonicalize(
        rendered.canonicalized_value or "", DOICapability.create_contract()
    )
    assert reentry.status == Resolution.SUCCESS
    assert reentry.canonicalized_value == text
