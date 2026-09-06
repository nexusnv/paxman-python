"""ADR-0011 Corollary 1–2 preservation matrix (output-format equality).

Registry exception (fourth documented; mirrors ``test_money_properties.py``
and ``tests/property/test_reentry_invariant.py``): property tests normally
stay off the registry and the frozen pipeline (tests/AGENTS.md,
CONVENTIONS), driving grammars/rules/``format_value`` directly. The
information-preservation invariant (ADR-0011,
``docs/adr/0011-output-format-information-preservation.md``, Formal
Statement, Corollaries 1–2) is a full-pipeline invariant over
``canonicalize()``: Corollary 2 requires the rendered value ``W`` to
re-enter the **default (param-free) contract** — no format may need the
contract parameter that produced it to make its own output readable — so
the suite must feed the pipeline's own emissions back through recognition,
validation, and ``format_value``. Like the Money and re-entry suites, this
module therefore uses a local ``_fresh_registry`` autouse fixture
(``reset_registry()`` + ``register_all_shipped()``) around each test.

The matrix (Corollary 2, per offered format class):

- **encoding** — ``canonicalize(W, default) == V`` (string-exact pre-image);
- **same-entity expansion** — ``canonicalize(W, default)`` yields ``V'`` with
  ``F(V') == F(V)`` (entity-preserving merge; the expansion spelling is a
  fixed point under the producing format);
- **documented quantization** — bounded drift ≤ ½ declared render quantum
  (Coordinates ``dms``/``dm``; the drift itself is locked by
  ``tests/property/test_coordinates_quantization.py`` — here only SUCCESS
  and param-free recovery are re-pinned);
- **waived projection** — excluded from the matrix; own-contract fixed
  points are locked in the capability suite
  (``tests/capabilities/language/test_capability.py::TestLanguageExtendedTagCarry``).
  The waived set is asserted exactly: Language ``alpha3``/``alpha3-bib``/
  ``name`` (ADR-0011 Consequences amendment, 2026-09-06) — no silent misses.

``CLASS_MAP`` is the **measured** classification table (Phase 4 Task 1):
every ``capability × offered format`` row was run through
``canonicalize(W, default)`` and assigned its class empirically; a row that
fit no class would have been a finding, not silently classified. The
module-level gate below fails loudly when an offered format lands without
a ``CLASS_MAP`` entry (or an entry goes stale), so a future offered format
cannot ship unclassified.

Rows and expected defaults are reused verbatim from
``tests/property/test_reentry_invariant.py`` (``ROWS``): the ADR-0010
suite is the per-capability fixture table, and plain test-to-test imports
inside the property layer are the established pattern — same layer, no
registry coupling beyond the shared ``_fresh_registry`` pattern.

Cross-entity injectivity (Corollary 1) is pinned by an explicit pairs
table (``_INJECTIVITY_PAIRS``): mandatory distinct-entity pairs per
ADR-0011 Consequences obligation 4, rendered under the named format,
asserting distinct strings. Quantized formats are excluded from injectivity
by their class — sub-quantum neighbors may share a rendering there.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from paxman.api.bootstrap import register_all_shipped
from paxman.api.canonicalize import canonicalize
from paxman.capabilities import (
    BIC,
    IBAN,
    ISBN,
    ISSN,
    ORCID,
    Coordinates,
    Country,
    Date,
    Element,
    Language,
    MacAddress,
    Money,
    Phone,
)
from paxman.core.capability import ContractFactory
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution
from tests.property.test_reentry_invariant import ROWS, _ReEntryRow

pytestmark = pytest.mark.property


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register all shipped capabilities around each test.

    Registration happens once per test, before any canonicalize() call;
    ``run_capability`` freezes the registry on the first example, which is
    fine because every shipped capability is already present (same exception
    pattern as ``test_money_properties.py`` / ``test_reentry_invariant.py``
    — see module docstring).
    """
    reset_registry()
    register_all_shipped()
    yield
    reset_registry()


def _default_kwargs(row: _ReEntryRow) -> dict[str, object]:
    """The row's contract kwargs minus ``output_format`` (the default contract)."""
    kwargs = dict(row.contract_kwargs) if row.contract_kwargs else {}
    kwargs.pop("output_format", None)
    return kwargs


# Measured classification table (Phase 4 Task 1) — (capability, format) ->
# class. Keys are exactly the shipped offered-format surface (gate below);
# every non-encoding entry carries its rationale.
CLASS_MAP: dict[tuple[str, str], str] = {
    # -- BIC -----------------------------------------------------------------
    # bic11: same-entity expansion — appends the head-office ``XXX`` branch
    # to an 8-char BIC (ISO 9362 implicit branch code). Identity render for
    # an 11-char canonical (the measured fixture), so V2 == V there; the
    # merge-and-fixpoint fixture below pins the 8/11 spelling pair.
    ("bic", "bic11"): "expansion",
    ("bic", "grouped"): "encoding",
    # -- Coordinates ---------------------------------------------------------
    # dms/dm: documented quantizations (CoordinatesContract, Phase 0) —
    # render quantum 1″ / 0.001′, bounded drift locked by
    # tests/property/test_coordinates_quantization.py. Measured: the dms
    # re-entry of the 51.5074 fixture drifts to 51.5075 (within ½″); the dm
    # re-entry happens to be quantum-exact for this fixture.
    ("coordinates", "dms"): "quantization",
    ("coordinates", "dm"): "quantization",
    ("coordinates", "geo_uri"): "encoding",
    ("coordinates", "geojson_pair"): "encoding",
    ("coordinates", "iso6709"): "encoding",
    # -- Country -------------------------------------------------------------
    # alpha3/numeric/name: 1:1 ISO 3166-1 table encodings; each rendering
    # re-enters via its own grammar to the alpha-2 canonical (measured:
    # "UNITED STATES" -> "US").
    ("country", "alpha3"): "encoding",
    ("country", "name"): "encoding",
    ("country", "numeric"): "encoding",
    # -- Date ----------------------------------------------------------------
    ("date", "US"): "encoding",
    # -- Element -------------------------------------------------------------
    # name: 1:1 symbol<->English-name map; the lowercase rendering re-enters
    # through the name path to the proper-case symbol.
    ("element", "name"): "encoding",
    # -- IBAN / ISBN / ISSN / ORCID ------------------------------------------
    ("iban", "paper"): "encoding",
    ("isbn", "hyphenated"): "encoding",
    ("issn", "compact"): "encoding",
    ("issn", "urn"): "encoding",
    ("orcid", "compact"): "encoding",
    ("orcid", "uri"): "encoding",
    # -- Language ------------------------------------------------------------
    # alpha2: maps the primary subtag and carries remaining subtags verbatim
    # (ADR-0011 Phase 3) — encoding with exact pre-image.
    ("language", "alpha2"): "encoding",
    # alpha3 / alpha3-bib / name: waived projections (ADR-0011 Consequences
    # amendment) — primary-only render for extended tags; own-contract
    # fixed points are locked in TestLanguageExtendedTagCarry.
    ("language", "alpha3"): "waived",
    ("language", "alpha3-bib"): "waived",
    ("language", "name"): "waived",
    # -- MacAddress ----------------------------------------------------------
    # eui64: same-entity expansion — EUI-48 -> EUI-64 ``FF:FE`` insertion,
    # identity for an EUI-64 canonical (measured V2 == W).
    ("mac_address", "eui64"): "expansion",
    ("mac_address", "bare"): "encoding",
    ("mac_address", "cisco"): "encoding",
    ("mac_address", "hyphen"): "encoding",
    # -- Money / Phone -------------------------------------------------------
    ("money", "compact"): "encoding",
    ("phone", "rfc3966"): "encoding",
    ("phone", "split"): "encoding",
}

_CLASS_VALUES: frozenset[str] = frozenset(
    {"encoding", "expansion", "quantization", "waived"}
)
_WAIVED_SET: frozenset[tuple[str, str]] = frozenset(
    {("language", "alpha3"), ("language", "alpha3-bib"), ("language", "name")}
)

# Structural gate: CLASS_MAP keys are exactly the shipped offered-format
# surface as sampled through the ROWS fixtures (whose own gate pins ROWS to
# the shipped capability list — transitively, an offered format cannot land
# without a class). Values are exactly the four ADR-0011 classes.
_ALL_OFFERED: frozenset[tuple[str, str]] = frozenset(
    (row.name, fmt)
    for row in ROWS
    for fmt in sorted(
        row.factory.create_contract(**_default_kwargs(row)).OFFERED_OUTPUT_FORMATS
    )
)
assert set(CLASS_MAP) == _ALL_OFFERED, (
    "ADR-0011 gate: every offered format must have exactly one measured "
    f"classification; unclassified/stale rows: "
    f"missing={sorted(_ALL_OFFERED - set(CLASS_MAP))} "
    f"stale={sorted(set(CLASS_MAP) - _ALL_OFFERED)}"
)
assert set(CLASS_MAP.values()) <= _CLASS_VALUES, (
    "ADR-0011 gate: unknown class values: "
    f"{sorted(set(CLASS_MAP.values()) - _CLASS_VALUES)}"
)

# The matrix parametrizes offered formats only (the ADR-0010 suite covers
# the default contract); waived projections are excluded from the matrix —
# their own-contract fixed points live in the Language capability suite.
_MATRIX_PARAMS: list[pytest.param] = [
    pytest.param(row, fmt, id=f"{row.name}-{row.input}-{fmt}")
    for row in ROWS
    for fmt in row.formats
    if fmt not in ("", "default") and CLASS_MAP[(row.name, fmt)] != "waived"
]


@pytest.mark.parametrize(("row", "output_format"), _MATRIX_PARAMS)
def test_param_free_preimage_matrix(row: _ReEntryRow, output_format: str) -> None:
    """Corollary 2: every offered format recovers its pre-image param-free.

    Per class: encodings land string-exact on the row's default canonical;
    expansions land on the same entity (the expansion spelling re-renders
    identically); quantizations recover SUCCESS with drift bounded by the
    declared render quantum (locked by the Phase 0 suite). Waived
    projections are excluded — asserted exactly, no silent misses.
    """
    assert {
        (cap, fmt) for (cap, fmt), cls in CLASS_MAP.items() if cls == "waived"
    } == _WAIVED_SET, (
        "ADR-0011 gate: the waived set must be exactly Language "
        "alpha3/alpha3-bib/name (ADR-0011 Consequences amendment)"
    )
    fmt_kwargs = _default_kwargs(row)
    fmt_kwargs["output_format"] = output_format
    fmt_contract = row.factory.create_contract(**fmt_kwargs)  # type: ignore[arg-type]
    rendered = canonicalize(row.input, fmt_contract)
    assert rendered.status is Resolution.SUCCESS
    w = rendered.canonicalized_value
    assert w is not None
    default_contract = row.factory.create_contract(**_default_kwargs(row))  # type: ignore[arg-type]
    reentry = canonicalize(w, default_contract)
    assert reentry.status is Resolution.SUCCESS
    v2 = reentry.canonicalized_value
    assert v2 is not None
    klass = CLASS_MAP[(row.name, output_format)]
    if klass == "encoding":
        # Exact string pre-image: the rendering re-enters the default
        # contract onto the row's canonical value.
        assert v2 == row.expected_default
    elif klass == "expansion":
        # Same-entity merge: re-rendering the re-entered value under the
        # producing format reproduces the rendering (F(V2) == F(V)).
        again = canonicalize(v2, fmt_contract)
        assert again.status is Resolution.SUCCESS
        assert again.canonicalized_value == w
    else:
        assert klass == "quantization"
        # Bounded drift (<= 1/2 declared render quantum, deterministic) is
        # locked by tests/property/test_coordinates_quantization.py; here
        # we pin param-free SUCCESS (the assertion above) only.


@dataclass(frozen=True)
class _InjectivityPair:
    """One mandatory cross-entity pair (ADR-0011 Consequences obligation 4)."""

    name: str
    factory: ContractFactory
    output_format: str | None  # None = the default contract (default format)
    first: str
    second: str
    note: str = ""


# Explicit pairs table (Phase 4 plan, Background decision 4; inputs verified
# empirically). Quantized formats (Coordinates dms/dm) are deliberately
# absent: sub-quantum neighbors may share a rendering there (their class).
_INJECTIVITY_PAIRS: tuple[_InjectivityPair, ...] = (
    # Language alpha2 carries subtags, so distinct regions stay distinct.
    _InjectivityPair(
        "language", Language, "alpha2", "en-US", "en-GB", "region subtags"
    ),
    # Phone: the latent GB/MY NSN collision (ADR-0011 Context) — split
    # renders CC + NSN, keeping the country codes distinct.
    _InjectivityPair(
        "phone", Phone, "split", "+4412341234", "+6012341234", "GB vs MY NSN"
    ),
    # Coordinates sub-quantum neighbors under the exact encodings.
    _InjectivityPair(
        "coordinates",
        Coordinates,
        None,
        "51.507400, -0.1278",
        "51.507412, -0.1278",
        "decimal (default)",
    ),
    _InjectivityPair(
        "coordinates",
        Coordinates,
        "iso6709",
        "51.507400, -0.1278",
        "51.507412, -0.1278",
        "Annex H string expression",
    ),
    # Country: same two entities across every rendering (alpha2 is the
    # default format — not in OFFERED_OUTPUT_FORMATS — hence None here).
    _InjectivityPair(
        "country", Country, None, "United States", "United Kingdom", "alpha2"
    ),
    _InjectivityPair(
        "country", Country, "alpha3", "United States", "United Kingdom", ""
    ),
    _InjectivityPair(
        "country", Country, "numeric", "United States", "United Kingdom", ""
    ),
    _InjectivityPair("country", Country, "name", "United States", "United Kingdom", ""),
    _InjectivityPair("date", Date, "US", "2026-01-15", "2026-02-03", ""),
    _InjectivityPair("element", Element, "name", "Fe", "Au", ""),
    # BIC: different entities — NOT the DEUTDEFF/DEUTDEFFXXX merge pair
    # (that pair is same-entity by design and lives in the expansion fixture).
    _InjectivityPair("bic", BIC, "bic11", "DEUTDEFF", "BNPAFRPP", ""),
    _InjectivityPair("bic", BIC, "grouped", "DEUTDEFF", "BNPAFRPP", ""),
    _InjectivityPair(
        "mac_address",
        MacAddress,
        "hyphen",
        "00:1A:2B:3C:4D:5E",
        "FF:EE:DD:CC:BB:AA",
        "",
    ),
    _InjectivityPair(
        "mac_address", MacAddress, "bare", "00:1A:2B:3C:4D:5E", "FF:EE:DD:CC:BB:AA", ""
    ),
    _InjectivityPair(
        "mac_address",
        MacAddress,
        "cisco",
        "00:1A:2B:3C:4D:5E",
        "FF:EE:DD:CC:BB:AA",
        "",
    ),
    # eui64 injectivity pair must be distinct entities (not the EUI-48/EUI-64
    # merge pair, which shares a rendering by design).
    _InjectivityPair(
        "mac_address",
        MacAddress,
        "eui64",
        "00:1A:2B:3C:4D:5E",
        "FF:EE:DD:CC:BB:AA",
        "",
    ),
    _InjectivityPair(
        "iban",
        IBAN,
        "paper",
        "GB29NWBK60161331926819",
        "FR1420041010050500013M02606",
        "",
    ),
    _InjectivityPair("isbn", ISBN, "hyphenated", "9780306406157", "9781566199094", ""),
    _InjectivityPair("issn", ISSN, "compact", "2049-3630", "1234-5679", ""),
    _InjectivityPair("issn", ISSN, "urn", "2049-3630", "1234-5679", ""),
    _InjectivityPair(
        "orcid",
        ORCID,
        "uri",
        "0000-0002-1825-0097",
        "0000-0002-1694-233X",
        "",
    ),
    _InjectivityPair(
        "orcid",
        ORCID,
        "compact",
        "0000-0002-1825-0097",
        "0000-0002-1694-233X",
        "",
    ),
    _InjectivityPair("money", Money, "compact", "45.50 USD", "10.00 EUR", ""),
)

_INJECTIVITY_PARAMS: list[pytest.param] = [
    pytest.param(pair, id=f"{pair.name}-{pair.output_format or 'default'}")
    for pair in _INJECTIVITY_PAIRS
]


@pytest.mark.parametrize("pair", _INJECTIVITY_PARAMS)
def test_cross_entity_injectivity_pairs(pair: _InjectivityPair) -> None:
    """Corollary 1: distinct entities render distinct strings under a format.

    Renders both entities of each mandatory pair under the named format and
    asserts both succeed and differ. Quantized formats are excluded by
    class (their renderings may merge sub-quantum neighbors).
    """
    kwargs: dict[str, object] = {}
    if pair.output_format is not None:
        kwargs["output_format"] = pair.output_format
    contract = pair.factory.create_contract(**kwargs)  # type: ignore[arg-type]
    first = canonicalize(pair.first, contract)
    second = canonicalize(pair.second, contract)
    assert first.status is Resolution.SUCCESS
    assert second.status is Resolution.SUCCESS
    assert first.canonicalized_value is not None
    assert second.canonicalized_value is not None
    assert first.canonicalized_value != second.canonicalized_value, (
        f"ADR-0011 Corollary 1 violation ({pair.name} "
        f"{pair.output_format or 'default'}): distinct entities "
        f"{pair.first!r} / {pair.second!r} render identically"
        + (f" ({pair.note})" if pair.note else "")
    )


# Same-entity expansion fixtures (ADR-0011 Definitions + Consequences
# obligation 4): two spellings of one entity, asserted merge-and-fixpoint.
# NOTE: the Phase 4 plan's literal BIC pair ("DEUTDEFF500",
# "DEUTDEFF500XXX") is a 14-character string and not a valid BIC
# (canonicalize -> MISSING); the same-entity pair per the ISO 9362 implicit
# branch semantics is the 8-char head-office spelling and its XXX-expanded
# 11-char form.
_EXPANSION_FIXTURES: list[pytest.param] = [
    pytest.param(
        BIC,
        "bic11",
        ("DEUTDEFF", "DEUTDEFFXXX"),
        "DEUTDEFFXXX",
        id="bic-bic11",
    ),
    pytest.param(
        MacAddress,
        "eui64",
        ("00:1A:2B:3C:4D:5E", "00:1A:2B:FF:FE:3C:4D:5E"),
        "00:1A:2B:FF:FE:3C:4D:5E",
        id="mac_address-eui64",
    ),
]


@pytest.mark.parametrize(
    ("factory", "output_format", "spellings", "expanded"), _EXPANSION_FIXTURES
)
def test_expansion_fixtures_merge_and_fixpoint(
    factory: ContractFactory,
    output_format: str,
    spellings: tuple[str, str],
    expanded: str,
) -> None:
    """Expansions merge same-entity spellings and are fixed points.

    The two spellings canonicalize to distinct default canonical strings
    (distinct spellings, one entity), render identically under the
    expansion format (the merge), and each rendering re-enters to itself
    under the same contract (the fixpoint) — ADR-0011 Definitions
    ("same-entity expansion") and Consequences obligation 4.
    """
    fmt_contract = factory.create_contract(output_format=output_format)  # type: ignore[arg-type]
    default_contract = factory.create_contract()  # type: ignore[arg-type]
    canonicals = [canonicalize(s, default_contract) for s in spellings]
    for c in canonicals:
        assert c.status is Resolution.SUCCESS
    v1, v2 = canonicals[0].canonicalized_value, canonicals[1].canonicalized_value
    assert v1 is not None and v2 is not None
    assert v1 != v2, "same-entity spellings must canonicalize distinctly"
    renders = [
        canonicalize(v, fmt_contract).canonicalized_value
        for v in (v1, v2)
        if v is not None
    ]
    assert renders == [expanded, expanded], (
        f"same-entity spellings must merge onto one rendering under {output_format}"
    )
    for rendering in renders:
        fixpoint = canonicalize(rendering, fmt_contract)
        assert fixpoint.status is Resolution.SUCCESS
        assert fixpoint.canonicalized_value == rendering, (
            "each expansion rendering must re-enter to itself under the "
            "same contract (merge-and-fixpoint)"
        )
