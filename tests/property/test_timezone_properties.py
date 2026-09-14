"""Hypothesis robustness properties for the Timezone + UtcOffset capabilities.

Each property locks a pipeline-level invariant using independently derived
expectations:

- random printable input never raises (besides ``MultipleMentionsError``)
  and always resolves to a well-formed status (SUCCESS / MISSING / INVALID
  / AMBIGUOUS); non-SUCCESS outcomes carry no candidates.

Self-canonicalization (fixed points, incl. link-resolved, folded, and
basic forms) lives in ``tests/property/test_reentry_invariant.py`` ROWS;
the ADR-0011 basic-encoding pre-image lives in
``tests/property/test_output_format_preservation.py`` CLASS_MAP. This module
pins only the fuzz-robustness half of the Task 8 property obligation.

Registry posture: the fuzz properties drive the full pipeline (robustness
cannot be observed off-pipeline), so this module uses a local
``_fresh_registry`` fixture registering only Timezone + UtcOffset — the
documented ``test_money_properties.py`` exception pattern (pipeline
invariants cannot be observed off-pipeline; cf. ``test_reentry_invariant``
module docstring).
"""

from __future__ import annotations

import string

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.Timezone.capability import TimezoneCapability
from paxman.capabilities.UtcOffset.capability import UtcOffsetCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError
from paxman.engine.orchestrator import run_capability

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register Timezone + UtcOffset around each test.

    Registration happens once per test, before the hypothesis examples run;
    ``run_capability`` freezes the registry on the first example, which is
    fine because both capabilities are already present.
    """
    reset_registry()
    register_capability(TimezoneCapability())
    register_capability(UtcOffsetCapability())
    yield
    reset_registry()


@given(text=st.text(alphabet=string.printable, max_size=40))
def test_timezone_random_ascii_status_well_formed(text: str) -> None:
    """Random ASCII never raises; non-SUCCESS carries no candidates.

    INVALID legitimately arises from any curated/refused abbreviation
    surfacing in the noise (EST/IST/CST/...) — no narrower constraint.
    """
    contract = TimezoneCapability.create_contract()
    try:
        result = run_capability(text, contract)
    except MultipleMentionsError:
        return
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )
    if result.status in (Resolution.MISSING, Resolution.INVALID):
        assert result.candidates == ()


@given(text=st.text(alphabet=string.printable, max_size=40))
def test_utc_offset_random_ascii_status_well_formed(text: str) -> None:
    """Random ASCII never raises; non-SUCCESS carries no candidates.

    Single "Z"/"z" noise legitimately resolves to +00:00 (SUCCESS); glued
    or out-of-range noise is MISSING (unclaimed) or INVALID (refused).
    """
    contract = UtcOffsetCapability.create_contract()
    try:
        result = run_capability(text, contract)
    except MultipleMentionsError:
        return
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )
    if result.status in (Resolution.MISSING, Resolution.INVALID):
        assert result.candidates == ()
