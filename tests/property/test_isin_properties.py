"""Hypothesis property tests for the ISIN capability.

Each property locks a pipeline-level invariant using an independently
derived expectation:

- a synthesized valid ISIN (prefix from the ISO 3166-1 alpha-2 plus
  ANNA special-prefix union, random 9-alnum NSIN, independently computed
  mod-10 check digit) always resolves to itself (fixed point);
- random printable input never raises and resolves to a well-formed
  status (MISSING/INVALID bias — most strings are not ISINs);
- spaced and compact spellings of one value resolve identically;
- the ``grouped`` rendering round-trips through the compact pivot.

Self-canonicalization fixed points live in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 encoding
lives in ``tests/property/test_output_format_preservation.py``
CLASS_MAP. This module pins only the fuzz-robustness half.

Registry posture: the fuzz properties drive the full pipeline
(robustness cannot be observed off-pipeline), so this module uses a
local ``_fresh_registry`` fixture registering only ISIN — the documented
``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

import string
from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.ISIN.capability import ISINCapability
from paxman.capabilities.ISIN.rules.data.country_codes import (
    ISO_3166_1_ALPHA_2,
    SPECIAL_PREFIXES,
)
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Reset the registry and register ISIN around each test."""
    reset_registry()
    register_capability(ISINCapability())
    yield
    reset_registry()


_PREFIXES = sorted(ISO_3166_1_ALPHA_2 | SPECIAL_PREFIXES)
_NSIN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def _expand(compact: str) -> str:
    """Expand each character to digits (digits stay, A=10 ... Z=35).

    Derived independently from ISO 6166:2021's normative check-digit
    annex — duplicates the rule's expansion so the generator cannot
    pass by sharing the implementation under test.
    """
    parts: list[str] = []
    for ch in compact:
        if "0" <= ch <= "9":
            parts.append(ch)
        else:
            parts.append(str(ord(ch) - 55))
    return "".join(parts)


def _luhn_valid(expanded: str) -> bool:
    """Modulus 10 Double-Add-Double over the expanded digit string."""
    total = 0
    for index, digit in enumerate(reversed(expanded)):
        value = ord(digit) - 48
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _compute_check_digit(prefix_plus_nsin: str) -> str:
    """Find the check digit making the 12-char ISIN Luhn-valid."""
    for candidate in "0123456789":
        if _luhn_valid(_expand(prefix_plus_nsin + candidate)):
            return candidate
    raise AssertionError(f"no check digit for {prefix_plus_nsin!r}")


def test_check_digit_helper_matches_known_vector() -> None:
    """The test-local Luhn helper agrees with the Apple reference ISIN."""
    assert _compute_check_digit("US037833100") == "5"


@given(
    prefix=st.sampled_from(_PREFIXES),
    nsin=st.text(alphabet=_NSIN_ALPHABET, min_size=9, max_size=9),
)
def test_synthesized_valid_isins_self_canonicalize(prefix: str, nsin: str) -> None:
    """Any synthesized valid ISIN resolves to itself byte-identically."""
    compact = prefix + nsin + _compute_check_digit(prefix + nsin)
    result = canonicalize(compact, ISINCapability.create_contract())
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == compact


@given(text=st.text(alphabet=string.printable, max_size=40))
def test_random_ascii_never_raises(text: str) -> None:
    """Random printable input never raises; non-ISINs stay MISSING/INVALID."""
    contract = ISINCapability.create_contract()
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


@given(
    prefix=st.sampled_from(_PREFIXES),
    nsin=st.text(alphabet=_NSIN_ALPHABET, min_size=9, max_size=9),
)
def test_spaced_vs_compact_same_value(prefix: str, nsin: str) -> None:
    """Spaced groupings of one ISIN resolve to the compact canonical."""
    compact = prefix + nsin + _compute_check_digit(prefix + nsin)
    grouped = f"{compact[0:2]} {compact[2:8]} {compact[8:11]} {compact[11:]}"
    contract = ISINCapability.create_contract()
    r_compact = canonicalize(compact, contract)
    r_spaced = canonicalize(grouped, contract)
    assert r_compact.status == Resolution.SUCCESS
    assert r_spaced.status == Resolution.SUCCESS
    assert r_spaced.canonicalized_value == r_compact.canonicalized_value
    assert r_compact.canonicalized_value == compact


def test_grouped_round_trip_strips_to_compact() -> None:
    """The grouped rendering re-enters the default contract onto compact."""
    text = "US0378331005"
    rendered = canonicalize(
        text, ISINCapability.create_contract(output_format="grouped")
    )
    assert rendered.status == Resolution.SUCCESS
    assert rendered.canonicalized_value == "US 037833 100 5"
    stripped = (rendered.canonicalized_value or "").replace(" ", "")
    assert stripped == text
    reentry = canonicalize(stripped, ISINCapability.create_contract())
    assert reentry.status == Resolution.SUCCESS
    assert reentry.canonicalized_value == text
