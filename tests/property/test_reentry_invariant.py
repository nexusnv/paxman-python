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

The ``SUPPRESS_ROWS`` section below is the #122 A0 cross-link to #123:
canonical values that collide with ``COMMON_WORDS`` must satisfy Property 2
with ``suppress_common_words=True`` on. This module is already the
documented registry exception per tests/AGENTS.md, so the suppression rows
reuse the same ``_fresh_registry`` full-pipeline pattern.
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
    DOI,
    GTIN,
    IBAN,
    IP,
    ISBN,
    ISIN,
    ISSN,
    LEI,
    ORCID,
    URL,
    UUID,
    ChemicalElement,
    Coordinates,
    Country,
    CreditCard,
    Currency,
    Date,
    Domain,
    Email,
    Language,
    MacAddress,
    Money,
    Phone,
    SIUnit,
    Timezone,
    UtcOffset,
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
    contract_kwargs: dict[str, object] | None = None


def _row(
    capability: ContractFactory,
    text: str,
    expected_default: str,
    **contract_kwargs: object,
) -> _ReEntryRow:
    """Build a row: unset + "default" + every offered format (sorted, stable)."""
    contract = capability.create_contract(**contract_kwargs)  # type: ignore[arg-type]
    return _ReEntryRow(
        name=contract.capability_name,
        factory=capability,
        input=text,
        expected_default=expected_default,
        formats=("", "default", *sorted(contract.OFFERED_OUTPUT_FORMATS)),
        contract_kwargs=dict(contract_kwargs) if contract_kwargs else None,
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
    # CreditCard: tests/capabilities/credit_card/test_capability.py
    # ::test_format_value_grouped_rechunk — spaced input collapses to the
    # compact canonical; the offered grouped rendering re-enters via the
    # separator-interleave branch (the 15-digit row pins the Amex re-chunk:
    # renders "3782 8224 6310 005" — groups of 4, never brand 4-6-5 — and
    # re-enters string-exact).
    _row(CreditCard, "4111 1111 1111 1111", "4111111111111111"),
    _row(CreditCard, "378282246310005", "378282246310005"),
    # Currency: tests/capabilities/currency/test_capability.py
    # ::test_code_is_identity
    _row(Currency, "USD", "USD"),
    # Date: tests/capabilities/date/test_capability.py
    # ::test_default_format_is_identity (ISO)
    _row(Date, "2026-01-15", "2026-01-15"),
    # DOI: tests/capabilities/doi/test_capability.py
    # ::test_format_value_url_reenters — bare canonical; the offered url
    # rendering re-enters via the resolver-host carrier group.
    _row(DOI, "10.1038/nature12345", "10.1038/nature12345"),
    # Domain: tests/capabilities/domain/test_capability_wild_variants.py
    # (W1/W3-style inputs → A-label canonicals, all covered by the corpus).
    _row(Domain, "example.com", "example.com"),
    _row(Domain, "EXAMPLE.COM.", "example.com"),
    _row(Domain, "münchen.de", "xn--mnchen-3ya.de"),
    # Email: tests/e2e/test_bootstrap.py
    # ::test_bootstrap_then_canonicalize_round_trip
    _row(Email, "user@example.com", "user@example.com"),
    # ChemicalElement: tests/capabilities/chemical_element/test_capability.py
    # (symbol "Fe"; offered "name" renders lowercase "iron" which re-enters)
    _row(ChemicalElement, "Iron", "Fe"),
    # GTIN: tests/capabilities/gtin/test_capability.py — 14-digit canonical;
    # the offered native rendering re-enters via the spelled-length slice
    # (identity for a true GTIN-14).
    _row(GTIN, "00614141999996", "00614141999996"),
    # GTIN indicator-1 variant: prefix 061 read at view[1:4] (the GTIN-14
    # prefix sits after the indicator digit); check digit hand-verified.
    _row(GTIN, "10614141999993", "10614141999993"),
    # IBAN: tests/capabilities/iban/test_capability.py
    # ::test_format_value_paper_roundtrip (electronic)
    _row(IBAN, "GB29NWBK60161331926819", "GB29NWBK60161331926819"),
    # IP: tests/capabilities/ip/test_capability.py (identity "ip" format)
    _row(IP, "10.0.0.1", "10.0.0.1"),
    # ISBN: tests/capabilities/isbn/test_capability.py
    # ::test_format_value_identity (isbn13)
    _row(ISBN, "9780306406157", "9780306406157"),
    # ISIN: tests/capabilities/isin/test_capability.py — compact canonical;
    # the offered grouped rendering re-enters via the spaced-carrier group
    # (measured: "US 037833 100 5" strips to compact, re-renders grouped).
    _row(ISIN, "US0378331005", "US0378331005"),
    # LEI: tests/capabilities/lei/test_capability.py — compact canonical;
    # the offered urn rendering re-enters via the urn:lei: carrier branch
    # (measured: "urn:lei:5493000IBP32UQZ0KL24" strips to compact).
    _row(LEI, "5493000IBP32UQZ0KL24", "5493000IBP32UQZ0KL24"),
    # LEI non-00 pin: positions 5-6 carry "FZ", never rejected.
    _row(LEI, "7LTWFZYICNSX8D621K86", "7LTWFZYICNSX8D621K86"),
    # ISSN: tests/capabilities/issn/test_capability.py
    # ::test_format_value_hyphenated_identity
    _row(ISSN, "2049-3630", "2049-3630"),
    # Language: tests/capabilities/language/test_capability.py
    # ::test_bcp47_identity
    # ADR-0012: the BCP 47 syntax-only ghost "serbo-croatian" is disqualified
    # (Serbo-Croatian → SUCCESS "sh"), so it is never a canonical value and
    # must never be used as a fixture here — Language rows stay
    # registry-backed ("en", "en-US").
    _row(Language, "en", "en"),
    # Language extended-tag surface (ADR-0011 Phase 3): code formats carry
    # subtags, so "en-US" pins the extended path beside the bare row. The
    # suite is W->W, which holds for every format including the waived
    # "name" projection ("English" re-renders "English").
    _row(Language, "en-US", "en-US"),
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
    # Fixture is a valid NANP number (212-555-1234, not the fictional
    # 555-01xx range). The row is param-free per ADR-0011 — pre-image
    # recovery under the default contract is locked by the Phase 4 suite
    # hardening.
    _row(Phone, "+12125551234", "+12125551234"),
    # SIUnit: tests/capabilities/si_unit/test_capability.py (symbol "kg")
    _row(SIUnit, "kg", "kg"),
    # URL: WHATWG canonical form appends the path "/"; cf.
    # tests/e2e/test_canonicalize.py::TestURLCapabilityE2E (HTTPS://Example.COM:443)
    _row(URL, "https://example.com", "https://example.com/"),
    # Timezone: tests/capabilities/timezone/test_capability.py
    # ::TestTimezoneCapabilityPipeline::test_canonical_key_identity (iana)
    _row(Timezone, "America/New_York", "America/New_York"),
    # Timezone link-resolved surface: US/Eastern canonicalizes to
    # America/New_York, which is its own fixed point (same suite,
    # test_link_resolved_value_reenters). Folded mentions
    # (america/new_york) ride the case_ws_variants below.
    _row(Timezone, "US/Eastern", "America/New_York"),
    # UtcOffset: tests/capabilities/utc_offset/test_capability.py
    # ::test_basic_form_normalizes_to_extended — the basic-form input
    # canonicalizes to extended +05:30; the offered "basic" rendering
    # (+0530) re-enters under its own contract (test formats below).
    _row(UtcOffset, "+0530", "+05:30"),
    # UUID: tests/capabilities/uuid/test_capability.py
    # ::TestUUIDCapabilityPipeline::test_format_value_round_trips — every
    # offered carrier (compact/braced/urn) re-enters to the hyphenated
    # canonical under the default contract.
    _row(
        UUID,
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    ),
)

# ADR-0010, Consequences: a new capability cannot land without a re-entry row
# here — the gate is structural, not procedural.
assert {row.name for row in ROWS} == set(list_shipped_capabilities()), (
    "ADR-0010 gate: every shipped capability must have a re-entry row in ROWS"
)


# Suppression re-entry rows (#122 A0 cross-link to #123): canonical values
# that collide with COMMON_WORDS must re-enter with suppress_common_words on.
# Kept as a SEPARATE table so the ROWS == shipped structural gate above is
# untouched. Covers every suppressible matcher family plus a not-suppressible
# control (SIUnit "cd").
SUPPRESS_ROWS: tuple[_ReEntryRow, ...] = (
    # Country α2 (alpha2_recognition, suppressible)
    _row(Country, "TO", "TO", suppress_common_words=True),
    _row(Country, "IN", "IN", suppress_common_words=True),
    _row(Country, "US", "US", suppress_common_words=True),
    _row(Country, "ST", "ST", suppress_common_words=True),
    # Language ISO 639-1 (language_code_recognition, suppressible)
    _row(Language, "en", "en", suppress_common_words=True),
    _row(Language, "ca", "ca", suppress_common_words=True),
    # Currency ISO 4217 (code_recognition, suppressible — only ALL collides)
    _row(Currency, "ALL", "ALL", suppress_common_words=True),
    # Country α3 offered format (alpha3_recognition, suppressible): the
    # pre-A0 posture had 6 α3 violators (AGO, AND, ARE, CAN, MAR, PER) —
    # lock the offered-format surface too, not just the default α2.
    _row(Country, "AGO", "AGO", output_format="alpha3", suppress_common_words=True),
    # SIUnit control: no SIUnit matcher is suppressible — must already pass
    _row(SIUnit, "cd", "cd", suppress_common_words=True),
    # ChemicalElement "In" (indium): the symbol matcher is suppressible and "in" is
    # a common word — canonical-case input re-enters whole-input-exempt
    # (lowercase "in" would trip the suite's value == input identity assert
    # since in -> In).
    _row(ChemicalElement, "In", "In", suppress_common_words=True),
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
    kwargs: dict[str, object] = dict(row.contract_kwargs) if row.contract_kwargs else {}
    kwargs["output_format"] = output_format or None
    contract = row.factory.create_contract(**kwargs)  # type: ignore[arg-type]
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
    kwargs: dict[str, object] = (
        dict(variant.row.contract_kwargs) if variant.row.contract_kwargs else {}
    )
    contract = variant.row.factory.create_contract(**kwargs)  # type: ignore[arg-type]
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


_SUPPRESS_CASES: list[pytest.param] = [
    pytest.param(row, id=f"{row.name}-{row.input}") for row in SUPPRESS_ROWS
]


@pytest.mark.parametrize("row", _SUPPRESS_CASES)
def test_reentry_under_suppression(row: _ReEntryRow) -> None:
    """Property 2 with suppress_common_words on (#122 A0 cross-link to #123).

    Single-token canonicals are their own fixed point: the first call *is*
    the re-entry of an emitted ``V``, so it must succeed and land on itself.
    """
    kwargs: dict[str, object] = dict(row.contract_kwargs) if row.contract_kwargs else {}
    kwargs["suppress_common_words"] = True
    contract = row.factory.create_contract(**kwargs)  # type: ignore[arg-type]
    first = canonicalize(row.input, contract)
    assert first.status is Resolution.SUCCESS
    value = first.canonicalized_value
    assert value is not None
    assert value == row.expected_default
    assert value == row.input
    second = canonicalize(value, contract)
    assert second.status is Resolution.SUCCESS
    assert second.canonicalized_value == value


_SUPPRESS_WS_CASES: list[pytest.param] = [
    pytest.param(row, label, text, id=f"{row.name}-{row.input}-{label}")
    for row in SUPPRESS_ROWS
    for label, text in (
        ("padded", f"  {row.input}  "),
        ("newline", f"{row.input}\n"),
    )
]


@pytest.mark.parametrize(("row", "label", "text"), _SUPPRESS_WS_CASES)
def test_reentry_under_suppression_padded_variants(
    row: _ReEntryRow, label: str, text: str
) -> None:
    """Property 2 under suppression survives padding (#122 A0 trimmed region).

    The exempt hit lands exactly on the trimmed region, so padded and
    newline-terminated whole inputs must reach the same fixed point.
    """
    kwargs: dict[str, object] = dict(row.contract_kwargs) if row.contract_kwargs else {}
    kwargs["suppress_common_words"] = True
    contract = row.factory.create_contract(**kwargs)  # type: ignore[arg-type]
    first = canonicalize(text, contract)
    assert first.status is Resolution.SUCCESS
    value = first.canonicalized_value
    assert value is not None
    assert value == row.expected_default
    second = canonicalize(value, contract)
    assert second.status is Resolution.SUCCESS
    assert second.canonicalized_value == value


def test_a0_whole_input_common_word_domain() -> None:
    """A0 whole-input exemption keeps bare-word recognition for Domain (#122).

    ``de`` is a common word, but as the whole input it stays recognized;
    single-label scope then fails lookup qualification → INVALID (a MISSING
    regression would mean the A0 exemption was bypassed).
    """
    result = canonicalize("de", Domain.create_contract(suppress_common_words=True))
    assert result.status == Resolution.INVALID
    assert result.canonicalized_value is None
