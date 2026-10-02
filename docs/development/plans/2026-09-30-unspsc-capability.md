# UNSPSC Capability Implementation Plan

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a 29th capability, `UNSPSC`, that canonicalizes UNSPSC mentions (bare 8-digit, zero-padded parents, 6-digit class alias, `UNSPSC`-labelled, `UNSPSC000.` MDM IDs, 10-digit +BFI) to the 8-digit zero-padded wire stem with UNDP v26.0801 provenance.

**Architecture:** Single `PipelineGrammar` (`unspsc_recognition`, `RegexStage`, longest-first 10/8/6 alternation, `single_value=True`) feeding four rules in three publication files (two always-active PARSERs for structure/padding, one always-active LOOKUP_TABLE for codeset membership at the pinned snapshot, one gated PARSER for the BFI suffix); contract offers `segmented` + `labeled` + `native` encodings via the `format_value()` seam only. No `paxman/core` or `paxman/engine` change.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `paxman/core/grammar` staged pipeline, `paxman/capabilities/UNSPSC`.

**References:** `docs/development/research/2026-09-30-unspsc-canonicalization.md` (§2.1 inventory, §4.2 pattern, §5.2 rule map, §7 vectors, §13 decisions; review-corrected 2026-09-30), `paxman/capabilities/GTIN/` (notation facets `notation.py:20-22`, grammar `grammar/gtin_recognition.py:44-61,95`), `paxman/capabilities/ISBN/` (grammar `grammar/isbn13_recognition.py:15-40`, registry rule `rules/isbn_range_message_ed2026.py:13-33`, data `rules/data/range_message.py:14,30,2253`), `paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py:30`, HOW_TO_ADD_NEW_CAPABILITY.md Steps 0–10, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md (Recognition Pipeline Contract, formatting seam), ADR-0010 (re-entry), ADR-0011 (offered-format classes), ADR-0012 (parser corroboration — N/A here: membership is LOOKUP_TABLE).

**Branch:** `feature/unspsc-capability` (research committed as `4e8c0ac`; implementation continues on this branch per this plan).

---

## File Structure

- Create (scaffold via Task 0): `paxman/capabilities/UNSPSC/__init__.py`, `notation.py`, `contract.py`, `capability.py`, `grammar/__init__.py`, `grammar/unspsc_recognition.py`, `rules/__init__.py`, `rules/undp_unspsc_structure_ed2025.py` (Task 5), `rules/undp_unspsc_codeset_ed2023.py` (Task 6), `rules/unece_bfi_ed2005.py` (Task 7), `rules/data/__init__.py`, `rules/data/unspsc_codeset.py`, plus test stubs under `tests/capabilities/unspsc/`
- Create (data lifecycle): `paxman/shared_data/unspsc_snapshot.json`, `tools/regenerate_unspsc_data.py` (with `--check`)
- Modify: `paxman/capabilities/__init__.py` (lazy export `UNSPSC` + `__all__`), `paxman/api/bootstrap.py:43-71` (`_SHIPPED`, alphabetical: after `URL`, before `UtcOffset`)
- Create (tests): `tests/capabilities/unspsc/test_{notation,contract,grammar,rules,capability}.py`, `tests/integration/test_unspsc_pipeline.py`
- Modify (tests): `tests/property/test_reentry_invariant.py` (UNSPSC rows), `tests/property/test_output_format_preservation.py` (UNSPSC rows), `tests/unit/test_capability_exports.py` (29th export; check how it enumerates)
- Modify (docs): `README.md` (regenerate table), `CONTEXT.md` (Notation + table + tree), `docs/user/capabilities/unspsc.md` (create), `docs/user/capabilities/index.md`, `docs/user/api-reference.md`, `docs/user/concepts/capabilities.md`, `docs/user/glossary.md`, `docs/user/citations.md`, `docs/user/index.md`, `docs/user/migration.md` (Unreleased entry), `CHANGELOG.md` (Unreleased entry), `docs/development/MILESTONE.md` (§1 row 29), `benchmarks/scenarios.py` + `benchmarks/baseline.json`

No `paxman/core` change; no second shipped grammar; no `rules/data/` outside the codeset module; no titles in the snapshot (stems only — v1 never renders names).

## Design locks (from research — do not re-derive)

1. Canonical value is the 8-digit stem. Grammar pads 6-digit alias `+ "00"` and records `native_length`; every rule's `normalize()` returns the 8-digit stem so `_dedup_candidates` coalesces (`paxman/engine/orchestrator.py:815-847`).
2. Single grammar with longest-first alternation (10 before 8 before 6). Two grammars would create cross-grammar containment (10-digit stem contains 8-digit prefix) that the engine preserves as AMBIGUOUS (`orchestrator.py:463-476` is per-grammar only).
3. Zero-padded parents (`43000000`/`43210000`/`43211500`) are distinct valid codes, not prefixes. Truncated prose (`43`, `4321`), dotted (`43.21.15.03`), hyphenated (`43-21-15-03`), and space-grouped (`43 21 15 03`) never match at v1 → MISSING. Space-grouped is a named future `extra_grammars` extension (`unspsc_grouped_recognition`), not silent scope.
4. BFI suffix is informative-only: any `00`–`99` passes when `include_business_function=True`; no value table is cited (UNECE PDF direct-fetch blocked).
5. Grammar imports come from the package root (`from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre` per `isbn13_recognition.py:15`); boundary guards follow HOW_TO_ADD_NEW_GRAMMAR.md raw lookarounds / current `BoundarySpec` API — verify against the tree at implementation time, do not copy the research sketch blindly.
6. `create_contract()` lives on the Capability with `Sequence[str] | None = None` common block (HOW_TO_ADD_NEW_CAPABILITY.md:502-519, `tools/new_capability.py:134-141`), not on the Contract.
7. Test-vector correction: `44103103` is printer/facsimile toner (class `44103100` lane), not printer hardware. `43211503` is notebook computers; `44121706` wooden pencils; `25101703` ambulance; `11101803` platinum; `11101709` antimony.

---

### Task 0: Scaffold the skeleton

**Files:** `tools/new_capability.py` run; `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`

**Goal:** Generate the 13-file skeleton and wire registration.

- [ ] Run (flags verified at `tools/new_capability.py:442-452`):
  `uv run python tools/new_capability.py UNSPSC --name unspsc --authority "United Nations Development Programme" --spec-name "UNSPSC Codeset Release" --spec-url "https://www.undp.org/unspsc" --publication-year 2023 --spec-version "v26.0801 (2023-08-14)" --default-format unspsc`
  then insert `UNSPSC` into `_SHIPPED` (`paxman/api/bootstrap.py:43-71`, alphabetical position) and the lazy export in `paxman/capabilities/__init__.py`. Verify: `uv run python -c "from paxman.api.bootstrap import list_shipped_capabilities; print(list_shipped_capabilities())"` shows `unspsc`; `uv run pytest tests/unit/test_capability_exports.py -q` → PASS (update the expected count/table if it enumerates 28).
- [ ] Commit: `feat(unspsc): scaffold UNSPSC capability skeleton`.

### Task 1: Notation — frozen+slots facet record

**Files:** `paxman/capabilities/UNSPSC/notation.py`, `tests/capabilities/unspsc/test_notation.py`

**Goal:** `UNSPSCNotation(digits, level, function, native_length)` per research §3.1. Depends on: nothing.

- [ ] Failing test first: `test_frozen_slots_hashable` + `test_level_derivation` (segment/family/class/commodity from trailing-`00` lattice) + `test_native_length_lane` (6/8/10). Implement: `@dataclass(frozen=True, slots=True)` with `digits: str` (8 ASCII digits), `level: str` (free str, not Literal — snapshot owns hierarchy truth), `function: str` (`""` or 2 digits), `native_length: int`. Verify: `uv run pytest tests/capabilities/unspsc/test_notation.py -v` → PASS.

### Task 2: Contract — wire encoding + three expansions

**Files:** `paxman/capabilities/UNSPSC/contract.py`, `tests/capabilities/unspsc/test_contract.py`

**Goal:** `UNSPSCContract` with `DEFAULT_OUTPUT_FORMAT = "unspsc"`, `OFFERED = {segmented, labeled, native}`, `include_business_function=True`, `include_live_membership=False`. Depends on: Task 1 (notation shape for `native` docs only).

- [ ] Failing test first: `test_default_and_offered_formats` (default `"unspsc"`; offered excludes default; `resolve_output_format` round-trips) + `test_capability_contract_inheritance` (inherits `CapabilityContract`, `@dataclass(frozen=True)` without slots) + `test_feature_flags` (defaults True/False). Implement contract + `Capability.create_contract()` factory with the HOW_TO common block (`excluded_rules/pinned_rules: Sequence[str] | None`, `year`, `output_format`, `extra_grammars`) then capability-specific flags. Verify: `uv run pytest tests/capabilities/unspsc/test_contract.py -v` → PASS.

### Task 3: Codeset snapshot + regenerate tool

**Files:** `paxman/shared_data/unspsc_snapshot.json` (create), `tools/regenerate_unspsc_data.py` (create), `paxman/capabilities/UNSPSC/rules/data/__init__.py`, `paxman/capabilities/UNSPSC/rules/data/unspsc_codeset.py` (generated), `tests/capabilities/unspsc/test_codeset_data.py` (create)

**Goal:** Pinned, refreshable membership table. Currency precedent: `tools/regenerate_currency_data.py:31` reads `SNAPSHOT`; ISBN precedent: generated header in `rules/data/range_message.py:1-8`.

- [ ] Failing test first: `test_codeset_loads_and_covers_known_stems` (asserts `44103103`, `43211503`, `10101501`, `25101703`, `11101803`, `11101709`, `43000000`, `43210000`, `43211500` ∈ `LIVE_STEMS`; asserts `44103199`-shape ∉; asserts every stem is 8 ASCII digits) + `test_regenerate_check_is_clean` (`--check` passes on the committed snapshot). Implement: download UNDP `unspsc-english-v260801.1.xlsx`, extract 8-digit stems (+ ancestor rows as shipped — parents are rows in their own right) into `unspsc_snapshot.json` with `CODESET_VERSION = "v26.0801 (2023-08-14)"`; generator emits `LIVE_STEMS: frozenset[str]` with the GENERATED header + `--check` mode. Stems only, no titles. If the XLSX is unfetchable in this environment, record the exact manual step in the tool docstring and land a curated stem set covering all test vectors + full level lattice, flagged in the plan review — do not silently ship a partial table as complete (name it `LIVE_STEMS` only when it is the full 158,448; otherwise `CURATED_STEMS` + a Task 3b follow-up). Verify: `uv run python tools/regenerate_unspsc_data.py --check` → clean; `uv run pytest tests/capabilities/unspsc/test_codeset_data.py -v` → PASS; spot-check import time/memory of the generated module and note both in the commit message.

### Task 4: Grammar — single recognition grammar

**Files:** `paxman/capabilities/UNSPSC/grammar/unspsc_recognition.py`, `tests/capabilities/unspsc/test_grammar.py`

**Goal:** `UNSPSCRecognitionGrammar` (`name`/`semantics = "unspsc_recognition"`, `single_value=True`, `StandardPre(empty_guard=True)`, `RegexStage`) per research §4.2 with the Task-3-corrected imports. Depends on: Task 1 (notation ctor).

- [ ] Failing test first, one vector per research §2.1 RECOGNIZE row: bare commodity (`44103103`, `43211503`, `10101501`, `25101703`), parents (`43000000`, `43210000`, `43211500`), 6-digit alias (`441217` → `digits == "44121700"`, `native_length == 6`), labels (`UNSPSC 44103103`, `UNSPSC: 44103103`, `UNSPSC #43211507`, lowercase `unspsc 44103103`), MDM (`UNSPSC000.44103103` → `44103103`), 10-digit split (stem + `function`, `native_length == 10`), CSV shape (`unspsc,43211509`), span invariants (`raw_text` includes label, `notation.digits` excludes it), `name`/`semantics`; negatives: `43`, `4321`, `43 21 15 03`, `43.21.15.03`, `4410-3103`, 7/9/11-digit runs, `X44103103`, `44103103Y`, `44103103.0` (matches `44103103` only, `.0` outside span), multi-match row (2 spans). Implement: module-scope label/body strings, longest-first alternation, fused label, 6-digit `+"00"` pad + level derivation in `notation_fn`, ASCII-digit enforcement. Verify: `uv run pytest tests/capabilities/unspsc/test_grammar.py -v` → PASS.

### Task 5: Structure + padding PARSERs

**Files:** `paxman/capabilities/UNSPSC/rules/undp_unspsc_structure_ed2025.py`, `tests/capabilities/unspsc/test_rules.py` (structure section)

**Goal:** `Section1HierarchyStructure` + `Section2LevelPadding` (both PARSER, always-active), `PUBLICATION` = UNGM structure article (`kind="specification"`, `version="2025-07-08"`).

- [ ] Failing test first: `test_section1_accepts_6_8_10_lanes` + `test_section1_rejects_non_ascii_and_bad_shapes` + `test_section2_accepts_lattice_levels` (`43000000`→segment, `43210000`→family, `43211500`→class, `43211503`→commodity) + `test_section2_rejects_mid_zero` (`43001503`, `00101501` → no match) + provenance attrs (`authority/kind/version/lifecycle/publication_year`), `name == "Section {N}-{slug}"`, `target_semantics == frozenset({"unspsc_recognition"})`, `requires_features == frozenset()`, `normalize()` == 8-digit stem. Implement both `Rule[UNSPSCNotation]` classes (six enforced attrs per `paxman/core/domain.py:253-278`; `matches()` never raises, never reads contract flags; no `output_format` token anywhere in the file). Verify: `uv run pytest tests/capabilities/unspsc/test_rules.py -v` → PASS.

### Task 6: Codeset-membership LOOKUP_TABLE

**Files:** `paxman/capabilities/UNSPSC/rules/undp_unspsc_codeset_ed2023.py`, `tests/capabilities/unspsc/test_rules.py` (membership section)

**Goal:** `Section3CodesetMembership` (LOOKUP_TABLE, always-active), `PUBLICATION` = UNDP codeset (`kind="registry"`, `version="v26.0801 (2023-08-14)"`). Depends on: Task 3 (table).

- [ ] Failing test first: `test_section3_accepts_issued` (all Task 3 known stems) + `test_section3_rejects_unissued` (`44103199`-shape, `99999999`) + `test_section3_requires_live_ancestors` (stem whose pair-prefix ancestor is absent → no match; use a synthetic stem against a fixture table, not the full snapshot) + `strategy == LOOKUP_TABLE`, `kind == "registry"`, `normalize()` == stem. Implement stem lookup + ancestor-liveness walk (`SS000000`, `SSFF0000`, `SSFFCC00` live). `include_live_membership` rolling interpretation: document as wiring-ready (`requires_features={"include_live_membership"}` on a future rule or snapshot swap) but do not ship a second rule in v1. Verify: `uv run pytest tests/capabilities/unspsc/test_rules.py -v` → PASS.

### Task 7: BFI-suffix PARSER (gated)

**Files:** `paxman/capabilities/UNSPSC/rules/unece_bfi_ed2005.py`, `tests/capabilities/unspsc/test_rules.py` (BFI section)

**Goal:** `Section4BusinessFunctionSuffix` (PARSER, `requires_features={"include_business_function"}`), `PUBLICATION` = UNECE guidelines (`kind="specification"`, `version="v2.04"`; no page count, no value table — direct-fetch blocked).

- [ ] Failing test first: `test_section4_passes_any_suffix` (10-digit inputs pass regardless of `00`–`99` value) + `test_section4_ignores_6_8_digit` (no suffix lane → vacuous pass or abstain per engine gating semantics; assert the implemented behavior explicitly) + `requires_features` gate test (contract with `include_business_function=False` → 10-digit input resolves INVALID, never MISSING). Implement suffix split + informative-only pass. Verify: `uv run pytest tests/capabilities/unspsc/test_rules.py -v` → PASS.

### Task 8: Capability wiring + presentation seam + registration

**Files:** `paxman/capabilities/UNSPSC/capability.py`, `tests/capabilities/unspsc/test_capability.py`

**Goal:** `UNSPSCCapability` (`get_grammars` → 1, `get_rules` → 4 in order 1/2/3/4), `format_value()` four ways, live registration. Depends on: Tasks 1–2, 4–7.

- [ ] Failing test first: `test_wiring_counts` (1 grammar, 4 rules; grammar/rule name conventions) + `test_format_value_round_trips` (`unspsc` identity; `segmented` → `43-21-15-03`; `labeled` → `UNSPSC 43211503`; `native` restores `441217` / 10-digit `stem+function` / 8-digit identity) + `test_canonicalize_smoke` (register + `canonicalize("UNSPSC 44103103")` → SUCCESS `44103103`). Implement `format_value()` (presentation only — never affects identity) + `create_contract()` per Task 2. Verify: `uv run pytest tests/capabilities/unspsc/test_capability.py -v` → PASS.

### Task 9: Integration — resolution-state map

**Files:** `tests/integration/test_unspsc_pipeline.py` (create)

**Goal:** Research §9 rows end-to-end with the `_clean_registry` fixture.

- [ ] Failing test first: SUCCESS (commodity/parent/alias/label/MDM/BFI), MISSING (spaced/dotted/hyphenated/truncated/wrong-length/empty), INVALID (bad padding `43001503`, unissued `44103199`-shape, BFI-gated-off 10-digit), AMBIGUOUS-or-`MultipleMentionsError` (two distinct stems, `single_value=True`), determinism + `VersionStamp` + span-bearing match + candidate dedup (label vs bare dedup to one SUCCESS). Verify: `uv run pytest tests/integration/test_unspsc_pipeline.py -v` → PASS.

### Task 10: Property, consistency, and purity gates

**Files:** `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py`, `tests/property/test_unspsc_properties.py` (create if hypothesis spot-checks needed), `tests/unit/test_rule_output_format_purity.py` (extend if enumerated per capability)

**Goal:** ADR-0010/ADR-0011 compliance + snapshot self-consistency.

- [ ] Add re-entry rows: one verified-good input × (default + literal `"default"` + each of `segmented/labeled/native`) — note `native` for a 6-digit alias re-enters as the alias spelling only if the grammar re-recognizes it (it does per Task 4); if any rendered form fails re-entry, fix the capability, never silence the row. Add preservation rows for all four formats. Add hypothesis checks: live stem from snapshot → self-canonicalizes; random 8-digit → INVALID with probability ≈ 1 − 158448/10⁸; 6-digit alias vs padded stem share `normalize()`; non-digit mutations → MISSING. Add consistency tests: prefix-liveness closure over the snapshot (every stem's ancestors present) + every `target_semantics` claimed is produced by the shipped grammar. Extend the `output_format` source scan to cover the new `rules/` tree (expect zero hits). Verify: `uv run pytest -m "property" -k unspsc -q` → PASS; `rg -n "output_format" paxman/capabilities/UNSPSC/rules/` → zero hits.

### Task 11: Docs, registry, and benchmarks

**Files:** `README.md`, `CONTEXT.md`, `docs/user/capabilities/unspsc.md` + `index.md` + `api-reference.md` + `concepts/capabilities.md` + `glossary.md` + `citations.md` + `index.md` + `migration.md`, `CHANGELOG.md`, `docs/development/MILESTONE.md`, `benchmarks/scenarios.py`, `benchmarks/baseline.json`

**Goal:** 29th-capability registry completeness (mirror the ISNI plan's doc list).

- [ ] Regenerate README table (`tools/generate_readme_table.py` if generator-driven); CONTEXT.md Notation/table/tree entries; user docs page (canonical `unspsc` default, `segmented`/`labeled`/`native` with ADR-0011 classes, MISSING-vs-INVALID boundary, `44103103`-toner example); citations page rows for the three `PUBLICATION`s (UNGM structure 2025-07-08, UNDP codeset v26.0801 2023-08-14, UNECE v2.04 — each marked with the research fetch-status qualifications); MILESTONE §1 row 29 (UNSPSC, UNDP v26.0801, toner example, research+plan links); benchmarks scenario + baseline rows. Verify: `uv run python tools/generate_readme_table.py --check` (if supported) → clean; `uv run pytest tests/unit/test_capability_exports.py benchmarks -q` → PASS.

### Task 12: Full gate + reviews

**Files:** none (verification only)

**Goal:** Merge-ready branch.

- [ ] Run the full pre-PR gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest` → all green; `uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q` with global `fail_under = 95` → PASS. Then `paxman-oracle-review` on the branch diff before PR handoff (this plan already passed `paxman-momus-review`; no re-review of the plan file).

---

## Self-review (pre-save, per skill)

- Spec coverage: every research §13 decision has an owning task (1 default-formats→T2/T8; 2 single-grammar→T4; 3 always-active membership→T6; 4 length strictness→T4; 5 grammar-vs-rule split→T4/T5; 6 BFI informative→T7; 7 three-file split→T5–T7; 8 single_value→T4/T9; 9 separator rejection→T4/T9; 10 label span→T4; 11 grouped DEFER→design lock 3, no task). No gap.
- Placeholder scan: no `TBD`/`TODO`/bare `appropriate` — Task 3 names the fallback (`CURATED_STEMS` + Task 3b) explicitly instead of a placeholder.
- Type consistency: `UNSPSCNotation(digits, level, function, native_length)` identical in T1/T4/T5–T8; `UNSPSCContract(include_business_function=True, include_live_membership=False)` identical in T2/T7–T8; `Provenance` versions pinned per publication (2025-07-08 / v26.0801 / v2.04).
- Momus dry-run: branch exists, references are file:line-grounded, each task names files + test + `uv run` verify, QA is tool+steps+expected. Passable.

---

Plan saved to `docs/development/plans/2026-09-30-unspsc-capability.md` — 13 tasks (0–12), Large tier.

Execute task-by-task via `tdd` (failing test first). After impl, run `paxman-momus-review` on this plan file, then `paxman-oracle-review` on the branch diff before PR handoff.
