# ADR-0011 Phase 4 — Suite Hardening + Deferred Fold-ins

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Complete the ADR-0011 soft mandate: lock the Corollary 2 matrix (param-free pre-image / same-entity merge / bounded-drift / waiver fixed-point, per format class) and the cross-entity injectivity pairs in CI, codify the class-declaration obligation (scan + HOW_TO), and fold in every deferred review finding — while explicitly **not** promoting the hard mandate (deferred until all capabilities comply and a new capability ships clean; separate ADR later).

**Architecture:** Mostly tests + docs. One new property module (`tests/property/test_output_format_preservation.py`) locks the ADR-0011 Corollary 2 matrix + injectivity pairs over the existing `ROWS` fixtures; one new unit scan (`tests/unit/test_offered_format_class_declarations.py`) enforces class declarations at the contract seam; small fold-ins: a symmetric DMS range clamp mirroring DM's, Phone `__post_init__` docstring truthing, CHANGELOG supersession annotations + the Phase 0 `### Fixed` entry, HOW_TO checklist paragraph. No grammar/rule/engine changes; no format surface changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: `property`, `unit`, `capability`), hypothesis "ci" profile. No new dependencies.

**References:**
- ADR: `docs/adr/0011-output-format-information-preservation.md` — Formal Statement Corollary 1 (entity-relative injectivity) + Corollary 2 (param-free pre-image; bounded-drift for declared quantizations) + Consequences (soft-mandate obligations: class declaration, suite expectations, promotion criteria **recorded, not enacted**)
- Harness precedent: `tests/property/test_reentry_invariant.py:90-105` (`_row`/`_ReEntryRow` — reuse `ROWS` inputs/expected defaults as the V source), `:206-218` (`_fresh_registry`), `:171-173` (structural gate)
- Quantization locks (already landed, referenced not duplicated): `tests/property/test_coordinates_quantization.py`
- Waiver record: ADR-0011 Consequences amendment (Language `alpha3`/`alpha3-bib`/`name` waived projections; `alpha2` encoding) + `tests/capabilities/language/test_capability.py::TestLanguageExtendedTagCarry` (own-contract fixed-point locks)
- Expansions: `paxman/capabilities/BIC/capability.py:49-70` (`bic11` appends `XXX`), `paxman/capabilities/MacAddress/capability.py` (`eui64` inserts `FF:FE`) — same-entity merges per ADR-0011 Definitions
- DMS/DM clamp asymmetry: `paxman/capabilities/Coordinates/capability.py:39-57` (`_decimal_to_dms_parts` — no clamp) vs `:60-78` (`_decimal_to_dm_parts` — `>90`/`>180` clamps)
- Review findings being folded in (oracle/thermo-nuclear 2026-09-06): `CHANGELOG.md:21,31` (contradictory superseded `national` bullets), `CHANGELOG.md` missing `### Fixed` entry for the Phase 0 zero-hemisphere fold, `paxman/capabilities/Phone/contract.py:78-100` (`__post_init__` docstring says "base resolution first" but pre-checks at :93; exact-match note; national-masks-`default_country` note)
- Purity-scan precedent for the new scan: `tests/unit/test_rule_output_format_purity.py`; contract seam: `paxman/core/capability_contract.py`; `HOW_TO_ADD_NEW_CAPABILITY.md` (offered-formats step to extend)
- Sequencing: `docs/development/research/2026-09-05-output-format-information-preservation.md` §13 Phase 4 (plan-side citation only; nothing shipped may reference `docs/development/*`)

**Branch:** `feature/adr0011-information-preservation` (continues Phases 0–3)

**Out of scope (explicit):** the hard-mandate promotion ADR + CI gates (static `format_value` param-branching scan, sampled entity-injectivity gate as a merge-blocking check, de-offer deadlines). Per decision: promotion waits until every capability complies and a new capability lands clean under the invariant. This plan records readiness, it does not promote.

---

## Background the implementer needs

### The four property classes (what the matrix asserts, per ADR-0011)

For `W = format_value(V, F, notation)` under a capability's default contract:

| Class | Assertion in the matrix | Landed examples |
|---|---|---|
| **encoding** | `canonicalize(W, default) == V` (string-exact pre-image) | IBAN `paper`, ISBN `hyphenated`, ISSN `compact`/`urn`, ORCID `uri`/`compact`, BIC `grouped`, Money `compact`, Date `US`, Element `name`(?), Country `alpha3`/`numeric`/`name`(?), MacAddress `hyphen`/`bare`/`cisco`, Phone `rfc3966`/`split`, Language `alpha2`, Coordinates `iso6709`/`geo_uri`/`geojson_pair` |
| **same-entity expansion** | `canonicalize(W, default)` = `V'` with `F(V') == F(V)` (merge is entity-preserving; `V'` may be the expanded spelling, not `V`) | BIC `bic11`, MacAddress `eui64` |
| **documented quantization** | bounded drift ≤ ½ declared render quantum | Coordinates `dms`/`dm` (already locked — referenced) |
| **waived projection** | excluded from the param-free matrix; own-contract fixed point instead | Language `alpha3`/`alpha3-bib`/`name` (ADR-0011 amendment) |

Entries marked `(?` above are to be **measured, not assumed** — Task 1 measures every capability × offered format and produces the classification table the tests encode. Any measured row that fits no class is a finding: fix in the capability or record a waiver citation — never silently classified.

### Deferred fold-ins (all reviewed 2026-09-06; the hard mandate is the only exclusion)

1. **CHANGELOG supersession** — `[Unreleased]` currently contains the new Phase 2 entry ("`national` raises, `split` offered") beside the older bullets ("`national` remains offered with `default_country='US'`" at :21, and the old `### Fixed` bullet describing the deleted preservation branch at :31). Annotate the two superseded bullets in place (append "(superseded by the ADR-0011 Phase 2 entry above — `national` is now de-offered)"); do not move or rewrite shipped history.
2. **Phase 0 `### Fixed` entry** — the zero-hemisphere fold (`0, -0.000001` rendered `0°0′0″W`/`S` and re-entered `E`/`N`; now folds post-quantization zero to `N`/`E`) shipped without a CHANGELOG line. Add it under `### Fixed`.
3. **Phone `__post_init__` docstring truthing** — :78-82 says "Calls the base resolution first" but the national pre-check runs before `super().__post_init__()` (:93 before :100), the sole intentional exception to the base's super-first MUST (all other contracts comply). Document: pre-check → base resolution → `default_country` validation; note the pre-check is exact-match (case variants get the base's generic unsupported-format error — acceptable, matches the base resolver's exactness) and that a removed-format rejection precedes `default_country` validation (so `national` + `default_country="USA"` reports the migration error, not the alpha-2 error).
4. **DMS range clamp symmetry** — DM clamps carry overflow at 90/180 (:72-77); DMS does not. Unreachable for validated canonicals (max `89.999999` → exactly `90°0′0″N`), reachable only via hand-built notations where `format_value` catches `InvalidOperation` but not range. Add the symmetric clamp to `_decimal_to_dms_parts` (mirror DM: post-carry `deg > 90`/`> 180` → clamp with zeroed remainder) + a unit test.
5. **Class declarations + checklist** — ADR-0011's classification clause requires every offered format's class declared at the contract seam. Language/Phone/Coordinates carry declarations; the rest are audited in Task 3 and completed where missing, then enforced by scan; HOW_TO gains the review-checklist paragraph.

### Design decisions (locked)

1. **New property module, fourth registry exception.** `tests/property/test_output_format_preservation.py` (marker `property`) with the `_fresh_registry` pattern documented in its module docstring; `tests/AGENTS.md`'s exception sentence extends three → four. The ADR-0010 file stays focused on `W→W` re-entry; this module is ADR-0011 Corollaries 1–2.
2. **The matrix reuses `ROWS` fixtures** (inputs + expected defaults) rather than inventing inputs; the module imports `ROWS` from `test_reentry_invariant` (test-to-test import inside the property layer is acceptable — same layer, no registry coupling beyond the shared fixture pattern; keep it a plain import to avoid drift).
3. **Classification map is measured first** (Task 1), then encoded as a frozen fixture map `(capability_name, format) -> class` with a rationale comment per non-`encoding` row. Unknown rows fail loudly (KeyError → test error) so a future offered format cannot land unclassified.
4. **Injectivity pairs table is explicit** (mandatory cross-entity pairs per ADR-0011 Consequences): Language `en-US`/`en-GB` (alpha2), Phone GB `+4412341234`/MY `+6012341234` (split), Coordinates sub-quantum neighbors `51.507400`/`51.507412` (`decimal` + `iso6709` — the quantized formats are excluded from injectivity by their class), Country US/GB across `alpha2`/`alpha3`/`numeric`/`name`, Date `2026-01-15`/`2026-02-03` (`US`), Element `Fe`/`Au` (`name`), BIC `DEUTDEFF`/`BNPAFRPP` (`grouped`, `bic11` — note `bic11` merges `DEUTDEFF`/`DEUTDEFFXXX` by design, so the pair must be *different entities*), MacAddress `00:1A:2B:3C:4D:5E`/`FF:EE:DD:CC:BB:AA` (`hyphen`/`bare`/`cisco`; `eui64` pair must be distinct entities), IBAN GB29…/FR14… (`paper`), ISBN 978-0-306-40615-7-class distinct (`hyphenated`), ISSN distinct (`compact`/`urn`), ORCID distinct (`uri`/`compact`), Money `USD 45.50`/`EUR 10.00` (`compact`). For each: render both under the format, assert distinct strings.
5. **Waivers stay out of the matrix**; their own-contract fixed-point locks already exist (`TestLanguageExtendedTagCarry::test_waived_projection_fixed_point`). The matrix's class map marks them `waived` with the ADR-0011 amendment as citation, and the module asserts exactly the waived set is excluded (no silent misses).
6. **The scan enforces presence, not prose quality**: for every capability with non-empty `OFFERED_OUTPUT_FORMATS`, every format name must appear in the contract class docstring, and the docstring must mention at least one class term (`encoding`/`expansion`/`quantization`/`projection`). This is the codified review checklist a reviewer can point to; HOW_TO tells contributors what to write.
7. **TDD posture**: matrix rows are expected green (measured first); the scan is expected red until Task 3 completes missing declarations; the DMS clamp test is red until the clamp lands.

---

## File Structure

- Create: `tests/property/test_output_format_preservation.py`
- Create: `tests/unit/test_offered_format_class_declarations.py`
- Modify: `tests/AGENTS.md` — registry-exception sentence three → four
- Modify: `paxman/capabilities/Coordinates/capability.py` — symmetric DMS clamp (2 branches + comment)
- Modify: `paxman/capabilities/Phone/contract.py` — `__post_init__` docstring truthing
- Modify: `tests/capabilities/coordinates/test_coverage_95.py` — clamp unit test
- Modify: contracts missing class declarations (Task 3 findings — expected candidates: `Country/contract.py`, `Date/contract.py`, `Element/contract.py`, `IBAN/contract.py`, `ISBN/contract.py`, `ISSN/contract.py`, `Money/contract.py`, `ORCID/contract.py`, `BIC/contract.py`, `MacAddress/contract.py` — docstring-only)
- Modify: `HOW_TO_ADD_NEW_CAPABILITY.md` — offered-format checklist paragraph
- Modify: `CHANGELOG.md` — supersession annotations + `### Fixed` entry
- Modify: `docs/adr/0011-output-format-information-preservation.md` — dated amendment note recording the Phase 4 locks (suite + scan landed; promotion readiness, not promotion)

No changes: `paxman/core/**`, engine, grammars, rules, notation, README (no format column), versioned user docs.

---

### Task 1: Measure the matrix — empirical classification inventory

**Files:** none (script + PR-description notes).

**Goal:** No assumed class survives; the table the tests encode is measured.

- [ ] Run the inventory (paste full output into the PR description):

  ```bash
  uv run python -c "
  from paxman.api.bootstrap import register_all_shipped, list_shipped_capabilities
  from paxman.core.discovery import reset_registry
  from paxman.api.canonicalize import canonicalize
  from paxman.capabilities import *
  reset_registry(); register_all_shipped()
  CASES = {'bic': ('DEUTDEFF500',), 'coordinates': ('51.5074, -0.1278',), 'country': ('United States',), 'currency': ('USD',), 'date': ('2026-01-15',), 'email': ('user@example.com',), 'iban': ('GB29NWBK60161331926819',), 'ip': ('10.0.0.1',), 'isbn': ('9780306406157',), 'issn': ('2049-3630',), 'language': ('en-US',), 'mac_address': ('00:1A:2B:3C:4D:5E',), 'money': ('45.50 USD',), 'orcid': ('0000-0002-1825-0097',), 'phone': ('+12125551234',), 'element': ('Fe',), 'si_unit': ('kg',), 'url': ('https://example.com',)}
  for name in sorted(list_shipped_capabilities()):
      cap = globals()[{'bic':'BIC','coordinates':'Coordinates','country':'Country','currency':'Currency','date':'Date','email':'Email','iban':'IBAN','ip':'IP','isbn':'ISBN','issn':'ISSN','language':'Language','mac_address':'MacAddress','money':'Money','orcid':'ORCID','phone':'Phone','element':'Element','si_unit':'SIUnit','url':'URL'}[name]]
      c0 = cap.create_contract()
      r0 = canonicalize(CASES[name][0], c0)
      v = r0.canonicalized_value
      print(f'== {name}: V={v!r}')
      for fmt in sorted(cap.create_contract().OFFERED_OUTPUT_FORMATS):
          c = cap.create_contract(output_format=fmt)
          w = canonicalize(CASES[name][0], c).canonicalized_value
          d = canonicalize(w, c0)
          print(f'   {fmt}: W={w!r} default-reentry={d.status.name} V2={d.canonicalized_value!r} exact={d.canonicalized_value == v}')
  "
  ```

  (`element` canonical is the symbol — if the import name differs, adjust; keep the script's output verbatim in the PR description.)
- [ ] Produce the classification table: per `(capability, format)` assign `encoding` (V2 == V), `expansion` (V2 == W and F(V2) == F(V) — verify the merge property with one extra render call), `quantization` (dms/dm only), or `waived` (Language `alpha3`/`alpha3-bib`/`name` — W does not satisfy the default contract but re-enters under its own; verify own-contract fixed point in the output). Any row outside these four classes = STOP and report as a finding.
- [ ] Note (no file change): Country/Element-class surprises (e.g. `name` renderings that re-enter through their own grammars vs. normalizing to the default) are recorded with the measured `V2`, which Task 2's fixtures pin verbatim.

### Task 2: The preservation property module

**Files:** `tests/property/test_output_format_preservation.py` (create), `tests/AGENTS.md`

**Goal:** ADR-0011 Corollaries 1–2 as CI enforcement.

- [ ] Module skeleton: `pytestmark = pytest.mark.property`; docstring documenting the ADR-0011 matrix, the fourth registry exception (mirroring the module docstring pattern of `test_reentry_invariant.py`), and the class table from Task 1; autouse `_fresh_registry` fixture verbatim; `from tests.property.test_reentry_invariant import ROWS` (plain import — same layer).
- [ ] `CLASS_MAP: dict[tuple[str, str], str]` — the measured table from Task 1 as frozen fixture: `("phone", "split"): "encoding"`, `("bic", "bic11"): "expansion"`, `("language", "alpha3"): "waived"`, `("coordinates", "dms"): "quantization"`, … with a rationale comment on every non-`encoding` entry (ADR-0011 amendment for waivers; audit for expansions; Phase 0 locks for quantizations). Empty-offered capabilities (currency/email/ip/si_unit/url) need no entries.
- [ ] `test_param_free_preimage_matrix` — parametrized over `(row, fmt, class)`: build `C(fmt)` from the row's factory + kwargs, `W = canonicalize(row.input, C(fmt))` assert `SUCCESS`; `default = row.factory.create_contract()` (row kwargs minus `output_format`); `V2 = canonicalize(W, default)`:
  - `encoding`: assert `V2.status is SUCCESS` and `V2.canonicalized_value == row.expected_default` (the row's default canonical — the pre-image);
  - `expansion`: assert `SUCCESS` and `F(canonicalize(W, default)) == F(W)` — i.e. re-render under `C(fmt)` of `V2` equals `W` (entity-preserving merge);
  - `quantization`: assert `SUCCESS` (drift is locked by `test_coordinates_quantization.py` — cross-reference comment);
  - `waived`: assert excluded — the test must compute the waived set from `CLASS_MAP` and assert it matches `{("language", f) for f in ("alpha3", "alpha3-bib", "name")}` exactly (no silent misses; the ADR-0011 amendment is the citation).
- [ ] `test_cross_entity_injectivity_pairs` — parametrized over the explicit pairs table (Background decision 4; extend with per-capability pairs discovered in Task 1): for each pair, render both under the named format, assert both `SUCCESS` and distinct strings.
- [ ] `test_expansion_fixtures_merge_and_fixpoint` — `("DEUTDEFF500", "DEUTDEFF500XXX")` under BIC `bic11` and the eui64 pair under MacAddress `eui64`: assert the two spellings render identically (same entity) and each rendering re-enters to itself under the same contract (merge-and-fixpoint per ADR-0011 Definitions).
- [ ] `tests/AGENTS.md`: extend the registry-exception sentence three → four (`test_output_format_preservation.py` — ADR-0011 Corollary 1–2 matrix, full-pipeline).
- [ ] Run: `uv run pytest tests/property/test_output_format_preservation.py -q` → PASS (rows measured in Task 1; any red = finding, stop). Commit: `test(property): ADR-0011 preservation matrix + injectivity pairs (Phase 4)`.

### Task 3: Class-declaration scan + missing declarations

**Files:** `tests/unit/test_offered_format_class_declarations.py` (create), contract docstrings as flagged, `HOW_TO_ADD_NEW_CAPABILITY.md`

**Goal:** The classification clause becomes checkable; contributors get the checklist.

- [ ] Red: create the scan — iterate `tests.unit`-style over all shipped capabilities (import from `paxman.capabilities` + `list_shipped_capabilities`): for each contract class, `inspect.getdoc(contract_class)`; for each `fmt` in `OFFERED_OUTPUT_FORMATS` assert `fmt` in the docstring; assert at least one of `encoding`/`expansion`/`quantization`/`projection` appears. Run: `uv run pytest tests/unit/test_offered_format_class_declarations.py -q` → FAIL with the list of capabilities lacking declarations (expected: most pre-ADR capabilities beyond Language/Phone/Coordinates).
- [ ] Green: add/extend contract class docstrings for every flagged capability — declare each offered format's class per the Task 1 table (citing ADR-0011; keep existing content, append a "Formats (ADR-0011 classes): …" paragraph). Docstring-only; no behavior. Run: scan → PASS.
- [ ] `HOW_TO_ADD_NEW_CAPABILITY.md`: in the offered-formats step (search the doc's `OFFERED_OUTPUT_FORMATS` section), append the checklist: a new offered format must (a) declare its class in the contract docstring (`encoding` / `same-entity expansion` / `documented quantization`; projections are not offered), (b) carry a param-free pre-image (or bounded-drift/merge-fixpoint) argument in the capability's tests, (c) add its row to `tests/property/test_output_format_preservation.py`'s `CLASS_MAP` + a cross-entity injectivity pair — the scan makes (a) structural; cite ADR-0011.
- [ ] Run: `uv run pytest tests/unit -q` → PASS. Commit: `test(unit)+docs: offered-format class declarations enforced (Phase 4)`.

### Task 4: Fold-ins — clamp, docstring truthing, CHANGELOG

**Files:** `paxman/capabilities/Coordinates/capability.py`, `tests/capabilities/coordinates/test_coverage_95.py`, `paxman/capabilities/Phone/contract.py`, `CHANGELOG.md`

**Goal:** Every reviewed deferred item lands or is explicitly documented.

- [ ] Red: `test_dms_parts_clamps_range_overflow` in `test_coverage_95.py` — `_decimal_to_dms_parts("90.500000", True)` → `(90, 0, 0, "N")` and `("180.500000", False)` → `(180, 0, 0, "E")` (mirroring DM's clamp semantics). Run → FAIL (no clamp).
- [ ] Green: `_decimal_to_dms_parts` — after the 60-carry chain, add `if is_lat and deg > 90: deg, minute, sec = 90, 0, 0` / `if not is_lat and deg > 180: deg, minute, sec = 180, 0, 0` with a comment (mirrors `_decimal_to_dm_parts`; unreachable for validated canonicals — carry-overflow from ≤ 90.0/≤ 180.0 lands exactly on the boundary — defensive for hand-built notations). Run → PASS; `uv run pytest tests/property/test_coordinates_quantization.py -q` → PASS (clamp is post-carry, outside the fixpoint path).
- [ ] `Phone/contract.py` `__post_init__` docstring: first line → "Pre-checks removed `national` for a migration error, then calls base resolution, then validates `default_country`."; add two clauses — the pre-check is exact-match (case variants fall through to the base's generic unsupported-format error) and removed-format rejection precedes `default_country` validation (so `national` + invalid country reports the migration error). Code unchanged.
- [ ] `CHANGELOG.md`: annotate the two superseded `national` bullets (Background 1) in place; add under `### Fixed` the Phase 0 entry — Coordinates `dms`/`dm` rendered negative sub-quantum components as `S`/`W` zero-magnitude and broke re-entry (`0, -0.000001` → `0°0′0″W` re-entered `E`); post-quantization zero now folds to `N`/`E` (parity with the recognition `-0` fold), locked by `test_dms_dm_zero_hemisphere_fold` + the quantization property suite.
- [ ] Verify: `uv run pytest tests/capabilities/coordinates tests/capabilities/phone tests/unit -q` → PASS. Commit: `fix(coordinates)+docs: DMS clamp symmetry, docstring truthing, CHANGELOG fold-ins (Phase 4)`.

### Task 5: ADR amendment + full gate

**Files:** `docs/adr/0011-output-format-information-preservation.md`

- [ ] Append a dated amendment note to Consequences: *Phase 4 landed* — the Corollary 1–2 matrix (`test_output_format_preservation.py`), cross-entity injectivity pairs, expansion merge-and-fixpoint fixtures, the class-declaration scan (`test_offered_format_class_declarations.py`), and the HOW_TO checklist. All shipped formats are classified; waived set = Language `alpha3`/`alpha3-bib`/`name` (amended above). **Promotion readiness, not promotion**: the hard mandate (static param-branching scan, sampled injectivity gate as a merge blocker, de-offer deadlines) waits until every capability complies and a new capability ships clean under the invariant — promoted by a future ADR per Consequences.
- [ ] Full gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green; `uv run pytest --cov=paxman --cov-report=term-missing -q` → coverage ≥ 95; `rg -n "docs/development" paxman/ CONTEXT.md CHANGELOG.md docs/adr/ tests/` → 0 hits. Commit: `docs(adr): ADR-0011 Phase 4 amendment — soft mandate complete (promotion deferred)`.

---

## Out of scope (explicit)

- **Hard-mandate promotion** (its own future ADR): CI gates as merge blockers, de-offer deadlines for the Language waivers, static `format_value` param-branching scan. Trigger: all capabilities compliant + a new capability lands clean.
- New formats, surface changes, grammar/rule/engine changes.
- Moving/rewriting shipped CHANGELOG history (annotations only).
