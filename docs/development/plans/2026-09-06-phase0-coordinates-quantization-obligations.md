# Coordinates dms/dm Quantization Obligations — Pre-ADR-0011 (Phase 0)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Lock the two properties that make Coordinates `dms`/`dm` compliant *documented quantizations* — full-pipeline render→parse→render fixpoint and bounded-drift pre-image recovery — and declare the render quanta at the contract seam and in CONTEXT.md, so ADR-0011 (Phase 1 of the output-format invariant sequencing) classifies `dms`/`dm` as evidenced rather than asserted.

**Architecture:** No shipped behavior change. The `dms`/`dm` renderers (`paxman/capabilities/Coordinates/capability.py:39-78`) and the recognition-time 6 dp quantize (`paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:139-143`) are consumed as-is; this plan adds one property-test module pinning the quantum-ratio stability argument, docstring-only declarations on `CoordinatesContract`/`CoordinatesCapability`, a CONTEXT.md capability subsection, and the third documented registry exception in `tests/AGENTS.md`. Nothing in `paxman/core`, the engine, or any other capability changes.

**Tech Stack:** Python 3.11+, `decimal.Decimal` (stdlib), uv, ruff, strict pyright, import-linter, pytest (marker: `property`), hypothesis "ci" profile (`max_examples=100`, `deadline=None`). No new dependencies.

**References:**
- Research: `docs/development/research/2026-09-05-output-format-information-preservation.md` §7.2 (documented-quantization classification + closed proof), §8.1 Corollary 2 (bounded-drift pre-image), §13 Phase 0 (this plan's mandate). Plan-side citation only — per `docs/development/AGENTS.md` hard guidance, **no shipped code, docstring, or shipped doc created by this plan may reference `docs/development/*`**; docstrings cite the test module instead, and ADR-0011 (Phase 1) becomes the durable citation.
- `paxman/capabilities/Coordinates/capability.py:39-57` (`_decimal_to_dms_parts` — seconds integer, `ROUND_HALF_EVEN`, 60-carry), `:60-78` (`_decimal_to_dm_parts` — minutes 0.001, 60-carry), `:125-146` (`_format_dms`/`_format_dm` render shapes), `:184-222` (`format_value`/`_render` dispatch)
- `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:139-143` (`_quantize` — canonical quantum `Decimal("0.000001")`, `ROUND_HALF_EVEN`, `format(q, "f")`)
- `paxman/capabilities/Coordinates/contract.py:8-14` (`CoordinatesContract` — currently **no docstring**; the declaration seam this plan fills)
- `tests/capabilities/coordinates/test_coverage_95.py` — `test_dms_sec_and_minute_carry` (existing carry-path unit test this suite generalizes)
- Harness to mirror: `tests/property/test_reentry_invariant.py:90-105` (`_row`), `:206-218` (`_fresh_registry` autouse fixture), `:228-248` (full-pipeline fixpoint assertion shape)
- `tests/AGENTS.md` CONVENTIONS (registry-exception sentence currently naming **two** exceptions)
- `CONTEXT.md:42` (Coordinates Notation row — already documents 6 dp canonical), `:326` (`### ORCID` — anchor for the new subsection), `:377` (MacAddress offered-formats paragraph — the pattern to mirror), `:408` (`### Presentation: format_value and output_format`)

**Branch:** `feature/coordinates-quantization-obligations`

**Sequencing:** Phase 0 of the ADR-0011 sequencing (`…output-format-information-preservation.md` §13). Must land **before** ADR-0011; independent of Phases 2–4 (Phone/Language/suite hardening).

---

## Background the implementer needs

### Current state (verbatim, verified 2026-09-06)

`paxman/capabilities/Coordinates/contract.py:8-14` — the entire contract declaration, no docstring:

```python
@dataclass(frozen=True)
class CoordinatesContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "decimal"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"iso6709", "geo_uri", "geojson_pair", "dms", "dm"}
    )
    capability_name: str = field(default="coordinates", init=False)
```

Quantization sites (both pre-existing, unchanged by this plan):

- Canonical: `_quantize` (`coordinates_recognition.py:139-143`) quantizes latitude/longitude to `Decimal("0.000001")`, `ROUND_HALF_EVEN`, at **recognition** time — the canonical space is 6 dp by construction.
- `dms` render: `_decimal_to_dms_parts` (`capability.py:39-57`) quantizes seconds to **integer** half-even with 60-carry to minutes/degrees (`capability.py:51-56`).
- `dm` render: `_decimal_to_dm_parts` (`capability.py:60-78`) quantizes minutes to `Decimal("0.001")` half-even with 60-carry to degrees plus range clamps (`capability.py:69-77`).
- Render shapes: `_format_dms` → `51°30′27″N 0°7′40″W` (`°`=U+00B0, `′`=U+2032, `″`=U+2033); `_format_dm` → `51°30.445′N 0°7.6′W` (minutes always carry a decimal point, `capability.py:139-142`). Both append `, {alt}` only when the notation carries altitude (`capability.py:212-221`).

No shipped doc declares the `dms`/`dm` render quanta. CONTEXT.md line 42 documents the 6 dp *canonical* quantum but not the render quanta; README's Coordinates row (line 74) carries no format column and needs no change.

### The two properties being locked (with the closed proof this plan pins)

1. **Render stability (fixpoint), `W → W`.** For `W = format_value(V, "dms")` (resp. `"dm"`): `canonicalize(W, C_dms)` succeeds and `format_value(canonicalize(W, C_dms).canonicalized_value, "dms") == W`. Proof sketch being pinned: the canonical quantum (1e-6° ≈ 0.0036″) is three orders of magnitude below the half-second rounding boundary (0.5″), so a re-parse of an integer-second `W` lands within ±0.0018″ of that second and can never cross a render boundary; the same argument covers `dm` (render quantum 0.001′ = 0.06″ vs ≤ 3e-5° re-parse error). The argument depends on the **ratio** of the two quanta — a future canonical-quantum change (e.g. 7 dp) could silently break it, which is why it is pinned in CI rather than assumed.
2. **Bounded-drift pre-image, `V → W → V'`.** `canonicalize(W, default_contract)` does **not** return the pre-image `V` (e.g. `canonicalize("51°30′27″N")` = `51.5075`, not `51.507412`); the honest promise is drift bounded by half the render quantum plus half the canonical quantum:

   | Format | Render quantum | Drift bound used in tests | Derivation |
   |---|---|---|---|
   | `dms` | 1″ = 1/3600° ≈ 2.7778e-4° | `Decimal("0.00014")` | ½·(1/3600) + ½·1e-6 = 1.39389e-4 ≤ 1.4e-4 |
   | `dm` | 0.001′ = 1.6667e-5° | `Decimal("0.000009")` | ½·(0.001/60) + ½·1e-6 = 8.8333e-6 ≤ 9e-6 |

   The two carry/worst-case inputs in Task 2's fixture table sit deliberately at ~99% of each bound (`51.516528` drifts exactly 1.39e-4° under `dms`; `51.999992` drifts exactly 8e-6° under `dm`).

### Design decisions (locked)

1. **Test placement:** new module `tests/property/test_coordinates_quantization.py`, marker `property`, mirroring `test_reentry_invariant.py`'s `_fresh_registry` autouse fixture (module docstring documents the exception). `tests/AGENTS.md`'s registry-exception sentence is extended from two to three exceptions in Task 4. Rationale: the pre-image property is inherently full-pipeline (`canonicalize()` in → out), and the fixpoint-under-offered-format property is re-entry (ADR-0010 Property 2) evaluated over a broader input set than the single Coordinates row.
2. **Fixpoint assertions are self-contained** — no hardcoded expected canonical strings. `first = canonicalize(input, C(fmt))` must be `SUCCESS`; `second = canonicalize(first.canonicalized_value, C(fmt))` must be `SUCCESS` with `second.canonicalized_value == first.canonicalized_value`. Expected canonicals for the fixture inputs are confirmed empirically in Task 1 and pasted into the PR description, not asserted.
3. **`W→W` must never stand in for `W→V'`** — the two assertions live in separate test functions with separate docstrings (research §7.2 obligation 2).
4. **Quanta are declared at the contract seam**: `CoordinatesContract` class docstring (the declaration surface ADR-0011's classification clause names) plus `format_value`/`_format_dms`/`_format_dm` docstring notes. Declarations cite `tests/property/test_coordinates_quantization.py` as the lock — **never** `docs/development/*` (hard guidance in `docs/development/AGENTS.md`).
5. **Altitude is out of scope.** Renderers append `, {alt}` only when present; the quantization properties concern latitude/longitude. Fixture inputs carry no altitude.
6. **TDD posture is honesty-locking, not bug-reproducing.** The behavior already exists and is expected to pass on first run (the report's proof says it holds). The red-first obligation is satisfied the ADR-0010 way: the suite is the permanent CI enforcement, and any red run is a genuine finding to fix in the capability or escalate before ADR-0011 cites it (`…reentry-invariant-adr0010.md` Task 2 precedent).
7. **Boundary inputs include both carry cases** (60″ carry for `dms`, 60.000′ carry for `dm`) because the carry branches (`capability.py:51-56`, `:69-77`) are where a future quantum change would bite first.

---

## File Structure

- Create: `tests/property/test_coordinates_quantization.py`
- Modify: `paxman/capabilities/Coordinates/contract.py` — class docstring only (declaration seam)
- Modify: `paxman/capabilities/Coordinates/capability.py` — docstrings only (`format_value`, `_format_dms`, `_format_dm`)
- Modify: `CONTEXT.md` — new `### Coordinates` subsection before `### ORCID` (line 326)
- Modify: `tests/AGENTS.md` — registry-exception sentence, two → three exceptions

No `paxman/core` change; no engine change; no other capability change; no `pyproject.toml` change (marker `property` already registered).

---

### Task 1: File the tracking issue + confirm fixture values empirically

**Files:** none (GitHub issue + PR description scratch).

**Goal:** Give the plan a citable issue number and pin the expected canonical/render values for the fixture inputs before tests encode them.

- [ ] File an issue titled "Lock Coordinates dms/dm quantization obligations (pre-ADR-0011 Phase 0)" (label: `testing` or the repo's equivalent). Paste the number into this plan's header References and the Task 2 commit message.
- [ ] Run the empirical confirmation (paste output into the PR description):

  ```bash
  uv run python -c "
  from paxman.api.bootstrap import register_all_shipped
  from paxman.core.discovery import reset_registry
  from paxman.api.canonicalize import canonicalize
  from paxman.capabilities import Coordinates
  reset_registry(); register_all_shipped()
  for text in ('51.507412, -0.1278', '51.516528, -0.1278', '51.999992, -0.1278',
               '-33.868820, 151.215293', '0.000000, 0.000000', '89.999999, -179.999999'):
      for fmt in ('decimal', 'dms', 'dm'):
          r = canonicalize(text, Coordinates.create_contract(output_format=fmt))
          print(text, fmt, r.status.name, r.canonicalized_value)
  "
  ```

  Expected: `decimal` rows return the input's normalized canonical (`51.507412, -0.1278`, `51.516528, -0.1278`, `51.999992, -0.1278`, `-33.86882, 151.215293`, `0, 0`, `89.999999, -179.999999`); `dms`/`dm` rows return `SUCCESS` renderings (e.g. `51°30′27″N 0°7′24″W`, `51°31′0″N 0°7′36″W` carry case, `52°0.0′N 0°7.6′W` dm carry case). If any row is not `SUCCESS`, stop — that is a capability finding to resolve before Task 2.

### Task 2: Property module — fixpoint + bounded drift over boundary inputs

**Files:** `tests/property/test_coordinates_quantization.py` (create)

**Goal:** The executable obligations ADR-0011 will cite. Three tests, one module.

- [ ] Module skeleton: `pytestmark = pytest.mark.property`; module docstring documenting (a) the documented-quantization classification being locked, (b) the third registry exception mirroring `test_reentry_invariant.py`/`test_money_properties.py`, (c) the two properties with their bounds; autouse `_fresh_registry` fixture copied verbatim from `tests/property/test_reentry_invariant.py:206-218` (`reset_registry()` → `register_all_shipped()` → `yield` → `reset_registry()`).
- [ ] Fixture table (module-level tuple of `(label, input_text)` — the six Task-1 inputs, with the two carry/worst-case entries commented as such: `51.516528` = 59.5008″ → 60″ carry; `51.999992` = 59.99952′ → 60.000′ carry).
- [ ] Test `test_dms_dm_reentry_fixpoint` — parametrized `input × ("dms", "dm")` (12 cases): `contract = Coordinates.create_contract(output_format=fmt)`; `first = canonicalize(text, contract)`; assert `first.status is Resolution.SUCCESS`; `w = first.canonicalized_value`; `second = canonicalize(w, contract)`; assert `second.status is Resolution.SUCCESS` and `second.canonicalized_value == w`. Run: `uv run pytest tests/property/test_coordinates_quantization.py::test_dms_dm_reentry_fixpoint -v` → PASS (expected green; red = genuine capability finding, stop and fix before proceeding).
- [ ] Test `test_dms_dm_bounded_drift_preimage` — same 12 parametrized cases: `v = canonicalize(text, default).canonicalized_value` (default contract, no `output_format`); `w = canonicalize(text, c_fmt).canonicalized_value`; `v2 = canonicalize(w, default).canonicalized_value`; parse both as `lat_str, lon_str = value.split(", ")` → `Decimal` per component; assert `abs(lat - lat2) <= Decimal("0.00014")` and `abs(lon - lon2) <= Decimal("0.00014")` for `dms`, `Decimal("0.000009")` for both components for `dm` (bounds from the Background table; put the derivation comment in the test). Run: `…::test_dms_dm_bounded_drift_preimage -v` → PASS.
- [ ] Hypothesis test `test_dms_dm_fixpoint_random_decimals` — `@given(lat=st.decimals(min_value=-90, max_value=90, places=6), lon=st.decimals(min_value=-180, max_value=180, places=6))`; text = `f"{lat}, {lon}"`; run the fixpoint assertion for both formats (same shape as the parametrized test). Do not weaken the "ci" profile. Run: `uv run pytest tests/property/test_coordinates_quantization.py -q` → 3 passed.
- [ ] Commit: `test(property): lock coordinates dms/dm quantization fixpoint + bounded drift (#<issue>)`.

### Task 3: Declare the quanta at the contract seam (docstrings only)

**Files:** `paxman/capabilities/Coordinates/contract.py`, `paxman/capabilities/Coordinates/capability.py`

**Goal:** The declaration surface ADR-0011's classification clause names — a caller reading the contract learns `dms`/`dm` are precision-capped without reading research notes.

- [ ] `CoordinatesContract` class docstring (none exists today): state `DEFAULT_OUTPUT_FORMAT = "decimal"` (lat-first signed pair, 6 dp round-half-even) and the five offered formats with shapes (`iso6709` `+DD.DDDD+DDD.DDDD[/alt]/`, `geo_uri` `geo:lat,lon[,alt]`, `geojson_pair` `[lon, lat[, alt]]`, `dms` `51°30′27″N 0°7′40″W`, `dm` `51°30.445′N 0°7.6′W`); then the quantization declaration sentence — "`dms` renders seconds as integers (render quantum 1″ ≈ 2.78e-4°) and `dm` renders minutes to 0.001′; both are documented quantizations: sub-quantum canonical digits are not recoverable from the rendering, re-canonicalization is a fixed point, and pre-image recovery drifts by at most half a render quantum — locked by `tests/property/test_coordinates_quantization.py`." No reference to `docs/development/*`.
- [ ] `format_value` docstring (`capability.py:184`): add one sentence after the existing fallback paragraph — same declaration, pointing at the contract docstring.
- [ ] `_format_dms` / `_format_dm` docstrings (`capability.py:125`, `:134`): add "Render quantum: 1″ integer seconds" / "Render quantum: 0.001′" one-liners.
- [ ] Verify: `uv run pytest tests/capabilities/coordinates -q` → PASS (docstring-only change); `uv run pyright paxman/capabilities/Coordinates` → 0 errors. Commit: `docs(coordinates): declare dms/dm render quanta at the contract seam (#<issue>)`.

### Task 4: Shipped-docs declarations + third registry exception

**Files:** `CONTEXT.md`, `tests/AGENTS.md`

**Goal:** Callers and test authors find the classification without reading the contract source.

- [ ] CONTEXT.md: insert a `### Coordinates` subsection immediately before `### ORCID` (line 326), mirroring the MacAddress offered-formats paragraph shape (`:377`): "Default `decimal` (lat-first signed decimal pair, quantized 6 dp round-half-even, `-0` folded); offered `iso6709` (`+DD.DDDD+DDD.DDDD[/alt]/`), `geo_uri` (`geo:lat,lon[,alt]`), `geojson_pair` (`[lon, lat[, alt]]`, lon-first), `dms` (`51°30′27″N 0°7′40″W`), `dm` (`51°30.445′N 0°7.6′W`). `dms`/`dm` are documented quantizations: `dms` renders seconds as integers (render quantum 1″ ≈ 2.78e-4°), `dm` renders minutes to 0.001′ — sub-quantum digits are not recoverable; re-canonicalization is a fixed point and pre-image recovery drifts by at most half a render quantum (locked by `tests/property/test_coordinates_quantization.py`). Presentation is via `Capability.format_value()` only; rules always normalize to the default."
- [ ] `tests/AGENTS.md` CONVENTIONS, registry-hygiene bullet: extend "the two documented exceptions are `test_money_properties.py` and `tests/property/test_reentry_invariant.py`" to "the three documented exceptions are `test_money_properties.py`, `tests/property/test_reentry_invariant.py`, and `tests/property/test_coordinates_quantization.py` (declared-quantization fixpoint + bounded-drift pre-image — also a full-pipeline invariant)".
- [ ] Verify: `uv run pytest tests/property -q` → PASS. Commit: `docs: coordinates quantization declarations + third registry exception (#<issue>)`.

### Task 5: Full gate

**Files:** none.

- [ ] `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green; `uv run pytest --cov=paxman --cov-report=term-missing -q` → coverage ≥ 95 unchanged. Confirm `rg -n "docs/development" paxman/ CONTEXT.md tests/property/test_coordinates_quantization.py` → 0 hits (the hard-guidance check).
