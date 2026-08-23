"""Hypothesis property tests for the BIC capability.

Locks invariants of structure, country gating, and presentation:

- ``matches()`` never raises on any 8 or 11 alphanumeric string;
- a BIC built from a country in ``COUNTRY_CODES`` is always valid;
- random strings with invalid country are INVALID;
- ``grouped`` round-trips via compact pivot deterministically;
- ``bic11`` expansion is lossy but deterministic.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.BIC.capability import BICCapability
from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.BIC.notation import BICNotation
from paxman.capabilities.BIC.rules.iso_9362_ed2022 import (
    COUNTRY_CODES,
    Section5BICStructureCountry,
)

RULE = Section5BICStructureCountry()
CONTRACT = BICContract()
COUNTRIES = sorted(COUNTRY_CODES)
CAP = BICCapability()


def _make_notation(compact: str) -> BICNotation:
    c = compact.upper()
    return BICNotation(
        bank_code=c[0:4],
        country_code=c[4:6],
        location_code=c[6:8],
        branch_code=c[8:11] if len(c) == 11 else "",
        compact=c,
    )


@pytest.mark.property
@given(
    st.text(min_size=8, max_size=11, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
)
def test_random_strings_never_raise(s: str) -> None:
    """matches() never raises on any 8 or 11 alnum string."""
    if len(s) not in (8, 11):
        return
    n = _make_notation(s)
    assert RULE.matches(n, CONTRACT) in (True, False)


@pytest.mark.property
@given(
    st.sampled_from(COUNTRIES),
    st.text(min_size=4, max_size=4, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    st.text(min_size=2, max_size=2, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
)
def test_all_countries_in_set_are_valid(country: str, bank: str, location: str) -> None:
    """Any country in COUNTRY_CODES with valid structure is accepted."""
    compact = bank + country + location
    n = BICNotation(
        bank_code=bank,
        country_code=country,
        location_code=location,
        branch_code="",
        compact=compact,
    )
    assert RULE.matches(n, CONTRACT) is True


@pytest.mark.property
@given(st.text(min_size=4, max_size=4, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
def test_generated_valid_country_is_valid(bank: str) -> None:
    """A hand-built valid BIC with known country is valid."""
    country = "DE"
    location = "FF"
    branch = "500"
    compact = bank + country + location + branch
    n = BICNotation(
        bank_code=bank,
        country_code=country,
        location_code=location,
        branch_code=branch,
        compact=compact,
    )
    # bank may contain digits? No, we restrict to A-Z, still valid
    assert RULE.matches(n, CONTRACT) is True


def test_grouped_roundtrip_via_compact() -> None:
    """Grouped rendering round-trips through compact pivot."""
    for bic in ["DEUTDEFF", "DEUTDEFF500", "BNPAFRPPXXX", "NEDSZAJJ"]:
        n = _make_notation(bic)
        grouped = CAP.format_value(bic, "grouped", n)
        compact2 = grouped.replace(" ", "")
        assert compact2 == bic, bic


def test_bic11_expansion_deterministic() -> None:
    """bic11 always 11, appending XXX when branch absent."""
    for bic8, bic11 in [
        ("DEUTDEFF", "DEUTDEFFXXX"),
        ("BNPAFRPP", "BNPAFRPPXXX"),
        ("NEDSZAJJ", "NEDSZAJJXXX"),
    ]:
        n = _make_notation(bic8)
        assert CAP.format_value(bic8, "bic11", n) == bic11
    # Already 11 stays identity
    n2 = _make_notation("DEUTDEFF500")
    assert CAP.format_value("DEUTDEFF500", "bic11", n2) == "DEUTDEFF500"


@pytest.mark.property
@given(st.text(min_size=2, max_size=2, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
def test_invalid_country_rejected(country: str) -> None:
    """A country not in COUNTRY_CODES is rejected (when structure otherwise valid)."""
    if country in COUNTRY_CODES:
        return
    compact = "DEUT" + country + "FF"
    # Need to ensure charset passes: bank DEUT ok, location FF ok
    # But bank_code is DEUT, country is random, location FF, total 8
    # For 8-char test, country is at 4:6
    # Build notation with those slices correctly
    n = BICNotation(
        bank_code="DEUT",
        country_code=country,
        location_code="FF",
        branch_code="",
        compact="DEUT" + country + "FF",
    )
    assert compact == n.compact
    assert RULE.matches(n, CONTRACT) is False
