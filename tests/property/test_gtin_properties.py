"""Hypothesis property tests for the GTIN capability.

Each property locks a pipeline-level invariant using an independently
derived expectation:

- a synthesized valid GTIN (prefix sampled from the GS1 MO allocation
  table at the length's documented key position, random payload,
  independently computed GenSpecs Mod-10 check digit) resolves to its
  14-digit zero-padded canonical (re-padding fixed point);
- flipping the check digit of a synthesized valid GTIN is
  deterministically INVALID (exactly one check digit validates a body);
- random digit input never raises and resolves to a well-formed status;
- single-space and hyphen groupings of one value resolve identically to
  the compact spelling;
- the ``native`` rendering of a UPC-A spelling re-enters the default
  contract onto its 14-digit pre-image (identity for a true GTIN-14).

Fixture-row self-canonicalization lives in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 class
lives in ``tests/property/test_output_format_preservation.py``
CLASS_MAP. This module pins the fuzz-robustness half — the
``test_lei_properties.py`` precedent.

Registry posture: the fuzz properties drive the full pipeline
(robustness cannot be observed off-pipeline), so this module uses a
local ``_fresh_registry`` fixture registering only GTIN — the
documented ``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.GTIN.capability import GTINCapability
from paxman.capabilities.GTIN.rules.data.gs1_prefix import GS1_MO_RANGES
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> Iterator[None]:
    """Reset the registry and register GTIN around each test."""
    reset_registry()
    register_capability(GTINCapability())
    yield
    reset_registry()


def _check_digit(body: str) -> str:
    """GS1 Mod-10 check digit (weights 3/1, rightmost-anchored).

    Derived independently from the GenSpecs rule statement — duplicates
    the rule's arithmetic so the generator cannot pass by sharing the
    implementation under test — and anchored below against published
    check-digit vectors.
    """
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return str((10 - total % 10) % 10)


def test_check_digit_helper_matches_known_vectors() -> None:
    """The test-local Mod-10 helper agrees with published suite vectors."""
    assert _check_digit("590123412345") == "7"  # GS1 example EAN-13
    assert _check_digit("1234567") == "0"  # suite GTIN-8
    assert _check_digit("0061414199999") == "6"  # suite UPC-A, padded


def _allocated(prefix: int) -> bool:
    """MO membership for a numeric prefix (the published range table)."""
    return any(start <= prefix <= end for start, end, _ in GS1_MO_RANGES)


# Per-length prefix pools at the documented key positions (8 -> view[:3],
# 12 -> "0" + view[:2], 13 -> view[:3], 14 -> view[1:4] after the
# indicator digit). The test re-derives the keying instead of importing
# the rule's private helpers, so a keying regression fails synthesis
# rather than being echoed by it. Views never start with "0", so the
# zero-strip view normalization never fires and the key position above
# is the one exercised. GTIN-8 excludes 962 (its key resolves at 4 chars
# through the exceptions table — rule-suite territory).
_POOL_8 = tuple(f"{p:03d}" for p in range(100, 1000) if _allocated(p) and p != 962)
_POOL_12 = tuple(f"{p:02d}" for p in range(10, 100) if _allocated(p))
_POOL_13 = tuple(f"{p:03d}" for p in range(100, 1000) if _allocated(p))
_POOL_14 = tuple(f"{p:03d}" for p in range(1, 1000) if _allocated(p))

_CASES: tuple[tuple[int, str], ...] = (
    tuple((8, p) for p in _POOL_8)
    + tuple((12, p) for p in _POOL_12)
    + tuple((13, p) for p in _POOL_13)
    + tuple((14, p) for p in _POOL_14)
)


def _synthesize(case: tuple[int, str], payload: str, indicator: str) -> str:
    """Build a valid GTIN: prefix + payload + computed check digit."""
    length, prefix = case
    if length == 14:
        body = indicator + prefix + payload
    elif length in (12, 13):
        body = prefix + payload[:9]
    else:  # length == 8
        body = prefix + payload[:4]
    return body + _check_digit(body)


@given(
    case=st.sampled_from(_CASES),
    payload=st.text(alphabet="0123456789", min_size=9, max_size=9),
    indicator=st.sampled_from("12345678"),
)
def test_synthesized_valid_gtins_self_canonicalize(
    case: tuple[int, str], payload: str, indicator: str
) -> None:
    """Any synthesized valid GTIN resolves to its 14-digit padded canonical."""
    digits = _synthesize(case, payload, indicator)
    result = canonicalize(digits, GTINCapability.create_contract())
    assert result.status is Resolution.SUCCESS
    assert result.canonicalized_value == digits.rjust(14, "0")


@given(
    case=st.sampled_from(_CASES),
    payload=st.text(alphabet="0123456789", min_size=9, max_size=9),
    indicator=st.sampled_from("12345678"),
)
def test_mutated_check_digit_is_deterministically_invalid(
    case: tuple[int, str], payload: str, indicator: str
) -> None:
    """Flipping the check digit is deterministically INVALID.

    Exactly one digit validates a given body (Mod-10 is a bijection over
    the check position), so the mutated mention is recognized but fails
    every active rule — no candidates, hence INVALID, every time.
    """
    digits = _synthesize(case, payload, indicator)
    mutated = digits[:-1] + str((int(digits[-1]) + 1) % 10)
    result = canonicalize(mutated, GTINCapability.create_contract())
    assert result.status is Resolution.INVALID


@given(text=st.text(alphabet="0123456789", min_size=1, max_size=40))
def test_random_digit_input_never_raises(text: str) -> None:
    """Random digit input never raises; non-GTINs stay MISSING/INVALID."""
    contract = GTINCapability.create_contract()
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
    if result.status is not Resolution.SUCCESS:
        assert result.candidates == ()
    else:
        assert result.canonicalized_value is not None


def _group(digits: str, sep: str) -> str:
    """Group digits in chunks of three with the given separator."""
    return sep.join(digits[i : i + 3] for i in range(0, len(digits), 3))


@given(
    case=st.sampled_from(_CASES),
    payload=st.text(alphabet="0123456789", min_size=9, max_size=9),
    indicator=st.sampled_from("12345678"),
)
def test_grouped_and_compact_spellings_resolve_identically(
    case: tuple[int, str], payload: str, indicator: str
) -> None:
    """Single-space and hyphen groupings resolve to the compact canonical."""
    digits = _synthesize(case, payload, indicator)
    contract = GTINCapability.create_contract()
    expected = digits.rjust(14, "0")
    compact = canonicalize(digits, contract)
    assert compact.status is Resolution.SUCCESS
    assert compact.canonicalized_value == expected
    for grouped in (_group(digits, " "), _group(digits, "-")):
        result = canonicalize(grouped, contract)
        assert result.status is Resolution.SUCCESS
        assert result.canonicalized_value == expected


def test_native_render_reenters_to_padded_pre_image() -> None:
    """A UPC-A spelling's native rendering re-enters as its 14-digit pre-image."""
    spelled = "614141999996"
    rendered = canonicalize(
        spelled, GTINCapability.create_contract(output_format="native")
    )
    assert rendered.status is Resolution.SUCCESS
    assert rendered.canonicalized_value == spelled
    reentry = canonicalize(
        rendered.canonicalized_value or "",
        GTINCapability.create_contract(),
    )
    assert reentry.status is Resolution.SUCCESS
    assert reentry.canonicalized_value == "00614141999996"


def test_native_render_is_identity_for_true_gtin14() -> None:
    """A true GTIN-14 renders identically under native (full-length slice)."""
    padded = "00614141999996"
    rendered = canonicalize(
        padded, GTINCapability.create_contract(output_format="native")
    )
    assert rendered.status is Resolution.SUCCESS
    assert rendered.canonicalized_value == padded
