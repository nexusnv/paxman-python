"""Re-entry (fixed-point) invariant property suite — ADR-0010, Property 2.

Registry exception (mirrors ``test_money_properties.py``): property tests
normally stay off the registry and the frozen pipeline (tests/AGENTS.md,
CONVENTIONS), driving grammars/rules/``format_value`` directly. Re-entry
cannot be observed that way — it is a full-pipeline invariant over
``canonicalize()``: the suite must feed the pipeline its own emitted value
back through recognition, validation, and ``format_value``. Like the Money
suite, this module therefore uses a local ``_fresh_registry`` autouse fixture
(``reset_registry()`` + ``register_all_shipped()``) around each test; it is
the second documented exception to the property-layer registry ban.

The invariant (docs/adr/0010-re-entry-fixed-point-invariant.md, Formal
Statement, Property 2): if ``R = canonicalize(I, C)`` has
``R.status == SUCCESS`` and ``R.canonicalized_value == V``, then
``canonicalize(V, C)`` must have ``R'.status == SUCCESS`` and
``R'.canonicalized_value == V`` — irrespective of the ``output_format`` in
``C`` that produced ``V`` (default or offered). Scope is contract-relative:
``V`` re-enters under the same contract ``C`` that produced it, and the
round trip must land exactly on ``V`` (a re-entry resolving to some
``W != V`` would split one entity into two).

Rows are per capability: one verified-good input, the default contract
(``output_format`` unset, then the literal ``"default"``, which resolve
identically), and every offered format from that contract's
``OFFERED_OUTPUT_FORMATS``. A failing row is an ADR-0010 violation to fix in
the capability (extend recognition/validation so the rendered form
re-enters) or to remove by de-offering the format with a migration note —
never silently accepted.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.api.bootstrap import (
    list_shipped_capabilities,
    register_all_shipped,
)
from paxman.api.canonicalize import canonicalize
from paxman.capabilities import (
    BIC,
    IBAN,
    IP,
    ISBN,
    ISSN,
    ORCID,
    URL,
    Coordinates,
    Country,
    Currency,
    Date,
    Email,
    Language,
    MacAddress,
    Money,
    Phone,
    SIUnit,
)
from paxman.core.capability import ContractFactory
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution

pytestmark = pytest.mark.property


@dataclass(frozen=True)
class _ReEntryRow:
    """One shipped capability's re-entry row (ADR-0010 per-capability suite)."""

    name: str
    factory: ContractFactory
    input: str
    expected_default: str
    formats: tuple[str, ...]


def _row(capability: ContractFactory, text: str, expected_default: str) -> _ReEntryRow:
    """Build a row: unset + "default" + every offered format (sorted, stable)."""
    contract = capability.create_contract()
    return _ReEntryRow(
        name=contract.capability_name,
        factory=capability,
        input=text,
        expected_default=expected_default,
        formats=("", "default", *sorted(contract.OFFERED_OUTPUT_FORMATS)),
    )


# Fixture table — one row per shipped capability. Inputs and expected default
# canonical values verified against the capability suites
# (tests/capabilities/<name>/) and an empirical canonicalize() run under the
# default contract.
ROWS: tuple[_ReEntryRow, ...] = (
    # BIC: tests/capabilities/bic/test_capability.py::test_format_value_bic11
    _row(BIC, "DEUTDEFF500", "DEUTDEFF500"),
    # Coordinates: tests/capabilities/coordinates/test_capability.py
    # ::test_format_value_decimal_identity
    _row(Coordinates, "51.5074, -0.1278", "51.5074, -0.1278"),
    # Country: tests/capabilities/country/test_capability.py (alpha2 canonical)
    _row(Country, "United States", "US"),
    # Currency: tests/capabilities/currency/test_capability.py
    # ::test_code_is_identity
    _row(Currency, "USD", "USD"),
    # Date: tests/capabilities/date/test_capability.py
    # ::test_default_format_is_identity (ISO)
    _row(Date, "2026-01-15", "2026-01-15"),
    # Email: tests/e2e/test_bootstrap.py
    # ::test_bootstrap_then_canonicalize_round_trip
    _row(Email, "user@example.com", "user@example.com"),
    # IBAN: tests/capabilities/iban/test_capability.py
    # ::test_format_value_paper_roundtrip (electronic)
    _row(IBAN, "GB29NWBK60161331926819", "GB29NWBK60161331926819"),
    # IP: tests/capabilities/ip/test_capability.py (identity "ip" format)
    _row(IP, "10.0.0.1", "10.0.0.1"),
    # ISBN: tests/capabilities/isbn/test_capability.py
    # ::test_format_value_identity (isbn13)
    _row(ISBN, "9780306406157", "9780306406157"),
    # ISSN: tests/capabilities/issn/test_capability.py
    # ::test_format_value_hyphenated_identity
    _row(ISSN, "2049-3630", "2049-3630"),
    # Language: tests/capabilities/language/test_capability.py
    # ::test_bcp47_identity
    _row(Language, "en", "en"),
    # MacAddress: tests/capabilities/mac_address/test_capability.py
    # ::test_format_value_identity_default (colon)
    _row(MacAddress, "00:1A:2B:3C:4D:5E", "00:1A:2B:3C:4D:5E"),
    # Money: tests/capabilities/money/test_capability.py
    # ::test_code_amount_is_identity (canonical "CODE amount")
    _row(Money, "45.50 USD", "USD 45.50"),
    # ORCID: tests/capabilities/orcid/test_capability.py
    # ::test_format_value_default_identity (hyphenated)
    _row(ORCID, "0000-0002-1825-0097", "0000-0002-1825-0097"),
    # Phone: e164 canonical; cf. tests/e2e/test_canonicalize.py phone tests
    _row(Phone, "+12125550123", "+12125550123"),
    # SIUnit: tests/capabilities/si_unit/test_capability.py (symbol "kg")
    _row(SIUnit, "kg", "kg"),
    # URL: WHATWG canonical form appends the path "/"; cf.
    # tests/e2e/test_canonicalize.py::TestURLCapabilityE2E (HTTPS://Example.COM:443)
    _row(URL, "https://example.com", "https://example.com/"),
)

# ADR-0010, Consequences: a new capability cannot land without a re-entry row
# here — the gate is structural, not procedural.
assert {row.name for row in ROWS} == set(list_shipped_capabilities()), (
    "ADR-0010 gate: every shipped capability must have a re-entry row in ROWS"
)


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


_PARAM_CASES: list[pytest.param] = [
    pytest.param(row, fmt, id=f"{row.name}-{fmt or 'unset'}")
    for row in ROWS
    for fmt in row.formats
]


@pytest.mark.parametrize(("row", "output_format"), _PARAM_CASES)
def test_default_contract_reentry(row: _ReEntryRow, output_format: str) -> None:
    """Property 2 under the default contract and every offered format.

    The first call must succeed, the default format must render the
    documented canonical value, and the emitted value must re-enter the same
    contract as a fixed point.
    """
    contract = row.factory.create_contract(output_format=output_format or None)
    first = canonicalize(row.input, contract)
    assert first.status is Resolution.SUCCESS
    value = first.canonicalized_value
    assert value is not None
    if output_format in ("", "default"):
        # Both resolve to DEFAULT_OUTPUT_FORMAT: pin the canonical value.
        assert value == row.expected_default
    second = canonicalize(value, contract)
    assert second.status is Resolution.SUCCESS
    assert second.canonicalized_value == value


@dataclass(frozen=True)
class _CaseVariant:
    """A case/whitespace-perturbed input, tagged with its capability row."""

    row: _ReEntryRow
    label: str
    text: str


# Explicit variant list — no random free text (arbitrary strings legitimately
# MISSING and would test nothing): case + padding forms of each row's input.
case_ws_variants: list[_CaseVariant] = [
    _CaseVariant(row=row, label=label, text=text)
    for row in ROWS
    for label, text in (
        ("upper", row.input.upper()),
        ("lower", row.input.lower()),
        ("title", row.input.title()),
        ("padded", f"  {row.input}  "),
        ("newline", f"{row.input}\n"),
    )
]


@given(variant=st.sampled_from(case_ws_variants))
def test_reentry_case_whitespace_variants(variant: _CaseVariant) -> None:
    """Property 2 survives case/padding perturbation of each row's input."""
    contract = variant.row.factory.create_contract()
    first = canonicalize(variant.text, contract)
    if first.status is not Resolution.SUCCESS:
        # Property 2 is conditional on the first call succeeding: a variant
        # the pipeline does not recognize (e.g. money "45.50 usd", si_unit
        # "KG") never produced a canonical value, so it cannot violate
        # re-entry.
        return
    value = first.canonicalized_value
    assert value is not None
    second = canonicalize(value, contract)
    assert second.status is Resolution.SUCCESS
    assert second.canonicalized_value == value
