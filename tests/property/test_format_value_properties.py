"""Property coverage for ``Capability.format_value()``.

Formatting is the sole presentation seam: rules emit default canonical values
and the capability renders them in the requested format. These properties lock
the mathematical invariants of that seam with independently derived expected
values:

- default-format rendering is the identity for every built-in capability;
- valid ISO dates convert to valid US dates;
- every current alpha-2 code formats to alpha-3/numeric values that
  round-trip through the authoritative reverse tables, and the name output is
  a non-empty presentation string, with literal expectations locking the
  exact values for representative codes;
- localized names use the current mapping while former codes pass through.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.Country.capability import CountryCapability
from paxman.capabilities.Country.contract import CountryContract
from paxman.capabilities.Country.notation import CountryNotation
from paxman.capabilities.Country.rules.data.cldr_ed2025 import LOCALIZED_TO_ALPHA2
from paxman.capabilities.Country.rules.data.iso_3166_ed2020_part3 import (
    FORMER_NAME_TO_ALPHA2,
)
from paxman.capabilities.Country.rules.data.iso_3166_ed2024 import (
    ALPHA2_CODES,
    ALPHA3_TO_ALPHA2,
    NUMERIC_TO_ALPHA2,
)
from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Email.capability import EmailCapability
from paxman.capabilities.Email.contract import EmailContract
from paxman.capabilities.Email.notation import EmailNotation
from paxman.capabilities.IP.capability import IPCapability
from paxman.capabilities.IP.contract import IPContract
from paxman.capabilities.IP.notation import IPNotation
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.core.capability import Capability
from paxman.core.domain import NotationT

# Former codes that are currently assigned (AI, GE, SK) are not passthrough
# cases: they map through the current tables. Only codes absent from the
# current tables pass through unchanged.
_FORMER_PASSTHROUGH_NAMES = sorted(
    name for name, code in FORMER_NAME_TO_ALPHA2.items() if code not in ALPHA2_CODES
)


def _identity_formatter(
    capability: Capability[NotationT],
    notation: NotationT,
    default_format: str,
) -> Callable[[str], str]:
    """Return a typed formatter rendering in the capability's default format.

    ``Capability.format_value`` is generic in the notation type, so each
    closure binds a concrete capability and notation at construction time.
    The identity property asserts that rendering in the default format
    returns the canonical value unchanged.
    """

    def format_default(value: str) -> str:
        return capability.format_value(value, default_format, notation)

    return format_default


_IDENTITY_SAMPLES = [
    pytest.param(
        _identity_formatter(
            EmailCapability(),
            EmailNotation(local_part="user", domain_part="example.com"),
            EmailContract.DEFAULT_OUTPUT_FORMAT,
        ),
        "user@example.com",
        id="email",
    ),
    pytest.param(
        _identity_formatter(
            DateCapability(),
            DateNotation(N1="2026", N2="01", N3="15"),
            DateContract.DEFAULT_OUTPUT_FORMAT,
        ),
        "2026-01-15",
        id="date",
    ),
    pytest.param(
        _identity_formatter(
            CountryCapability(),
            CountryNotation(shape="alpha2", value="DE"),
            CountryContract.DEFAULT_OUTPUT_FORMAT,
        ),
        "DE",
        id="country",
    ),
    pytest.param(
        _identity_formatter(
            IPCapability(),
            IPNotation(address="192.0.2.1"),
            IPContract.DEFAULT_OUTPUT_FORMAT,
        ),
        "192.0.2.1",
        id="ip",
    ),
    pytest.param(
        _identity_formatter(
            PhoneCapability(),
            PhoneNotation(shape="e164", value="15551234567"),
            PhoneContract.DEFAULT_OUTPUT_FORMAT,
        ),
        "+15551234567",
        id="phone",
    ),
]

_LOCALIZED_SAMPLES = (
    ("Alemania", "DE", "DEU", "276", "GERMANY"),
    ("中国", "CN", "CHN", "156", "CHINA"),
)

# Independent literal presentation values for representative current codes.
# These are real expected outputs, not derived from the forward tables the
# formatter consumes — a shared regression in those tables cannot mask itself.
_CURRENT_FORMAT_LITERALS = (
    ("DE", "DEU", "276", "GERMANY"),
    ("US", "USA", "840", "UNITED STATES"),
    ("CN", "CHN", "156", "CHINA"),
    ("MY", "MYS", "458", "MALAYSIA"),
)

_HISTORICAL_SAMPLES = (
    ("USSR", "SU"),
    ("BURMA", "BU"),
    ("ZAIRE", "ZR"),
)


@pytest.mark.property
@pytest.mark.parametrize(
    "format_default,canonical",
    _IDENTITY_SAMPLES,
)
def test_format_value_default_is_identity(
    format_default: Callable[[str], str],
    canonical: str,
) -> None:
    """format_value(value, default_format, notation) == value."""
    assert format_default(canonical) == canonical


@pytest.mark.property
@given(
    year=st.integers(min_value=1900, max_value=2100),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),
)
def test_date_iso_to_us_matches_independent_derivation(
    year: int, month: int, day: int
) -> None:
    """A valid ISO value renders as the independently derived MM/DD/YYYY."""
    cap = DateCapability()
    iso_value = f"{year:04d}-{month:02d}-{day:02d}"
    notation = DateNotation(N1=str(year), N2=str(month), N3=str(day))
    expected = f"{month:02d}/{day:02d}/{year:04d}"
    assert cap.format_value(iso_value, "US", notation) == expected


@pytest.mark.property
def test_country_every_current_alpha2_round_trips_independently() -> None:
    """Every current alpha-2 code formats to reverse-consistent current values.

    For each of the 249 assigned alpha-2 codes plus XK the formatter's alpha-3
    outputs must round-trip, and for the 249 ISO-assigned codes (all except XK,
    which has no M49 code) the numeric output must also round-trip. The name
    output must be a non-empty presentation string. Exact presentation values
    are locked separately for representative codes.
    """
    cap = CountryCapability()
    for alpha2 in sorted(ALPHA2_CODES):
        notation = CountryNotation(shape="alpha2", value=alpha2)
        alpha3 = cap.format_value(alpha2, "alpha3", notation)
        numeric = cap.format_value(alpha2, "numeric", notation)
        name = cap.format_value(alpha2, "name", notation)
        assert ALPHA3_TO_ALPHA2[alpha3] == alpha2
        if alpha2 == "XK":
            # XK is user-assigned with no M49 numeric code — numeric format
            # passes through the alpha-2 code unchanged by design.
            assert numeric == "XK"
        else:
            assert NUMERIC_TO_ALPHA2[numeric] == alpha2
        assert isinstance(name, str) and name != ""


@pytest.mark.property
@pytest.mark.parametrize(
    ("alpha2", "alpha3", "numeric", "name"),
    _CURRENT_FORMAT_LITERALS,
)
def test_country_representative_codes_render_independent_literals(
    alpha2: str, alpha3: str, numeric: str, name: str
) -> None:
    """Representative current codes render the literal presentation values."""
    cap = CountryCapability()
    notation = CountryNotation(shape="alpha2", value=alpha2)
    assert cap.format_value(alpha2, "alpha3", notation) == alpha3
    assert cap.format_value(alpha2, "numeric", notation) == numeric
    assert cap.format_value(alpha2, "name", notation) == name


@pytest.mark.property
@given(localized=st.sampled_from(sorted(LOCALIZED_TO_ALPHA2)))
def test_country_localized_names_use_current_mapping(localized: str) -> None:
    """A localized-resolved alpha-2 formats through the current mapping.

    The alpha-3 and numeric outputs must round-trip back to the resolved
    alpha-2 through the authoritative reverse tables, proving the localized
    name formats through a current mapping; exact values for representative
    codes are covered by the literal expectations.
    """
    cap = CountryCapability()
    alpha2 = LOCALIZED_TO_ALPHA2[localized]
    notation = CountryNotation(shape="name", value=localized)
    alpha3 = cap.format_value(alpha2, "alpha3", notation)
    numeric = cap.format_value(alpha2, "numeric", notation)
    name = cap.format_value(alpha2, "name", notation)
    assert ALPHA3_TO_ALPHA2[alpha3] == alpha2
    assert NUMERIC_TO_ALPHA2[numeric] == alpha2
    assert isinstance(name, str) and name != ""


@pytest.mark.property
@pytest.mark.parametrize(
    ("localized", "alpha2", "alpha3", "numeric", "name"),
    _LOCALIZED_SAMPLES,
)
def test_country_localized_samples_use_current_mapping(
    localized: str, alpha2: str, alpha3: str, numeric: str, name: str
) -> None:
    """Known localized names resolve through the current alpha-2 mapping."""
    cap = CountryCapability()
    notation = CountryNotation(shape="name", value=localized)
    assert cap.format_value(alpha2, "alpha3", notation) == alpha3
    assert cap.format_value(alpha2, "numeric", notation) == numeric
    assert cap.format_value(alpha2, "name", notation) == name


@pytest.mark.property
@given(former_name=st.sampled_from(_FORMER_PASSTHROUGH_NAMES))
def test_country_former_codes_pass_through(former_name: str) -> None:
    """Former codes absent from the current tables pass through unchanged."""
    cap = CountryCapability()
    alpha2 = FORMER_NAME_TO_ALPHA2[former_name]
    notation = CountryNotation(shape="name", value=former_name)
    assert alpha2 not in ALPHA2_CODES
    assert cap.format_value(alpha2, "alpha3", notation) == alpha2
    assert cap.format_value(alpha2, "numeric", notation) == alpha2
    assert cap.format_value(alpha2, "name", notation) == alpha2


@pytest.mark.property
@pytest.mark.parametrize(("former_name", "alpha2"), _HISTORICAL_SAMPLES)
def test_country_historical_samples_pass_through(former_name: str, alpha2: str) -> None:
    """Known former names pass through unchanged for every alternative format."""
    cap = CountryCapability()
    notation = CountryNotation(shape="name", value=former_name)
    assert cap.format_value(alpha2, "alpha3", notation) == alpha2
    assert cap.format_value(alpha2, "numeric", notation) == alpha2
    assert cap.format_value(alpha2, "name", notation) == alpha2
