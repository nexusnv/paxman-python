"""Hypothesis robustness properties for the UUID capability.

Each property locks a pipeline-level invariant using independently derived
expectations:

- random 128-bit values render hyphenated and self-canonicalize;
- carrier variants (upper/bare/braced/URN) of one value all resolve to the
  same canonical;
- random printable input never raises (besides ``MultipleMentionsError``)
  and always resolves to a well-formed status.

Self-canonicalization fixed points live in
``tests/property/test_reentry_invariant.py`` ROWS; the ADR-0011 encodings
live in ``tests/property/test_output_format_preservation.py`` CLASS_MAP.
This module pins only the fuzz-robustness half.

Registry posture: the fuzz properties drive the full pipeline (robustness
cannot be observed off-pipeline), so this module uses a local
``_fresh_registry`` fixture registering only UUID — the documented
``test_money_properties.py`` exception pattern.
"""

from __future__ import annotations

import string
import uuid as stdlib_uuid

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.UUID.capability import UUIDCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register UUID around each test."""
    reset_registry()
    register_capability(UUIDCapability())
    yield
    reset_registry()


def _hyphenated(raw: bytes) -> str:
    return str(stdlib_uuid.UUID(bytes=raw))


@given(raw=st.binary(min_size=16, max_size=16))
def test_random_128bit_self_canonicalizes(raw: bytes) -> None:
    """Any 128-bit value renders hyphenated and resolves to itself."""
    text = _hyphenated(raw)
    contract = UUIDCapability.create_contract()
    result = canonicalize(text, contract)

    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == text


@given(raw=st.binary(min_size=16, max_size=16))
def test_carrier_variants_agree(raw: bytes) -> None:
    """Upper/bare/braced/URN spellings of one value share one canonical."""
    canon = _hyphenated(raw)
    compact = canon.replace("-", "")
    variants = [canon, canon.upper(), compact, "{" + canon + "}", "urn:uuid:" + canon]
    contract = UUIDCapability.create_contract()

    seen = {canonicalize(v, contract).canonicalized_value for v in variants}
    assert seen == {canon}


@given(text=st.text(alphabet=string.printable, max_size=40))
def test_random_ascii_status_well_formed(text: str) -> None:
    """Random ASCII never raises; non-SUCCESS carries no candidates."""
    contract = UUIDCapability.create_contract()
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
