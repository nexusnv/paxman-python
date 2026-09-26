# ISNI Capability Implementation Plan

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a 28th capability, `ISNI`, that canonicalizes ISNI mentions (spaced/compact/hyphenated/`isni.org`/labelled/`urn:isni:`) to the spaced display `XXXX XXXX XXXX XXXC` with ISO 27729:2024 provenance.

**Architecture:** Single `PipelineGrammar` (`isni_recognition`, `RegexStage`, `word_only` guards, `single_value=True`) feeding two full-conjunction PARSER rules in one fused file (`rules/iso_27729_ed2024.py`); contract offers `compact` + `urn` encodings via the `format_value()` seam only. No LOOKUP_TABLE registry rule in v1 (CC0 lag; liveness ≠ validity). Nothing in `paxman/core` or `paxman/engine` changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `paxman/core/grammar` staged pipeline, `paxman/capabilities/ISNI`.

**References:** `docs/development/research/2026-09-26-isni-canonicalization.md` (§2.1 inventory, §4.2 pattern, §5.2 rule map, §7 vectors, §13 decisions), `paxman/capabilities/ORCID/` (verbatim precedent: `grammar/orcid_recognition.py`, `rules/iso_27729_ed2024.py`, `notation.py`, `contract.py`, `capability.py`), HOW_TO_ADD_NEW_CAPABILITY.md Steps 0–10, ARCHITECTURE.md (Recognition Pipeline Contract, formatting seam), ADR-0010 (re-entry), ADR-0011 (offered-format classes), ADR-0012 (parser corroboration).

**Branch:** `research/isni-canonicalization` (research committed there; implementation continues on this branch per this plan).

---

## File Structure

- Create (scaffold): `paxman/capabilities/ISNI/__init__.py`, `notation.py`, `contract.py`, `capability.py`, `grammar/__init__.py`, `grammar/isni_recognition.py`, `rules/__init__.py`, `rules/iso_27729_ed2024.py` + test stubs under `tests/capabilities/isni/` via `tools/new_capability.py` (Task 0)
- Modify: `paxman/capabilities/__init__.py` (export `ISNI` + `__all__`), `paxman/api/bootstrap.py` (`_SHIPPED`), `paxman/cli.py` (dispatch, if name-mapped), `tools/generate_readme_table.py` (no change — reads `_SHIPPED`)
- Create (tests): `tests/capabilities/isni/test_{notation,contract,grammar,rules,capability}.py`, integration rows in `tests/integration/test_isni_pipeline.py` (create), property rows (modify `tests/property/test_reentry_invariant.py`, `test_output_format_preservation.py`)
- Modify (docs): `README.md` (regenerate table), `CONTEXT.md` (Notation + table + tree), `docs/user/capabilities/isni.md` (create), `docs/user/capabilities/index.md`, `docs/user/api-reference.md`, `docs/user/concepts/capabilities.md`, `docs/user/glossary.md`, `docs/user/citations.md`, `docs/user/index.md`, `docs/user/migration.md` (Unreleased entry), `CHANGELOG.md` (Unreleased entry), `docs/development/MILESTONE.md` (§1 row + strike §2B #19), `benchmarks/scenarios.py` + `benchmarks/baseline.json`

No new modules outside the capability package + its tests; no `paxman/core` change; no `rules/data/` or `grammar/data/` in v1.

---

### Task 0: Scaffold the skeleton

**Files:** `tools/new_capability.py` run; `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`

**Goal:** Generate the 13-file skeleton and wire registration so `register_all_shipped()` lists 28 names.

- [ ] Run: `uv run python tools/new_capability.py ISNI --name isni --authority "ISO" --spec-name "ISO 27729:2024" --spec-url "https://www.iso.org/standard/87177.html" --publication-year 2024 --default-format isni` → Expected: PASS (files created, `__init__.py` + `_SHIPPED` wired). Then rename the scaffolded rule stub `paxman/capabilities/ISNI/rules/iso_ed2024.py` → `rules/iso_27729_ed2024.py` (scaffolder derives the stem from `--authority`; the plan's per-publication name is `iso_27729_ed2024`). Verify: `uv run pytest tests/unit/test_capability_exports.py tests/unit/test_bootstrap.py -q` → PASS; `paxman --list` shows `isni`.

---

### Task 1: Notation — five-field frozen dataclass

**Files:** `paxman/capabilities/ISNI/notation.py`, `tests/capabilities/isni/test_notation.py`

**Goal:** `ISNINotation(compact, spaced, uri, check, is_uri)` — all `str`, frozen+slots, `compact == spaced.replace(" ", "")`, `check == compact[15]` (research §3.1).

- [ ] Failing test: `test_field_invariants` (spaced regroups compact; uri is `https://isni.org/isni/` + compact) → FAIL. Implement: dataclass per research §3.1. Verify: `uv run pytest tests/capabilities/isni/test_notation.py -v` → PASS.

---

### Task 2: Grammar — `isni_recognition` (TDD)

**Files:** `paxman/capabilities/ISNI/grammar/isni_recognition.py`, `tests/capabilities/isni/test_grammar.py`

**Goal:** Single `PipelineGrammar` recognizing every §2.1 RECOGNIZE row: spaced quads, compact 16, hyphenated 4-4-4-4, `ISNI` label (`[\s:-]+`, never zero-width), `isni.org` host (scheme/`www.` optional), `urn:isni:` carrier; `word_only` guards both sides; glued-label guard `(?!(?ai:ISNI[0-9]))`; inline `(?ai:)` ASCII; single spaces between quads only (research §4.2).

- [ ] Failing tests: one positive vector per RECOGNIZE row (`ISNI 0000 0001 2103 2683`, `0000000121032683`, `0000-0001-2103-2683`, `https://isni.org/isni/…`, `urn:isni:…`, `…955x`) + negatives (glued label, double spaces, fullwidth digits, 15/17-char runs) + span invariants + `name`/`semantics`/`single_value` pins → FAIL. Implement: staged pattern + `_isni_notation` (research §4.2). Verify: `uv run pytest tests/capabilities/isni/test_grammar.py -q` → PASS.

---

### Task 3: Rules — fused `iso_27729_ed2024.py` with two full-conjunction classes (TDD)

**Files:** `paxman/capabilities/ISNI/rules/iso_27729_ed2024.py`, `tests/capabilities/isni/test_rules.py`

**Goal:** `Section4IsniStructure` + `SectionAMod11Dash2` (both PARSER, shared PUBLICATION: ISO 27729:2024, Ed. 2, 2024-11, https://www.iso.org/standard/87177.html, active, 2024); each validates structure AND MOD 11-2; `normalize()` returns spaced display; local MOD 11-2 copy (never import from ORCID); `target_semantics = frozenset({"isni_recognition"})` (research §5.2, §7).

- [ ] Failing tests: valid vectors (`…2683`, `…955X`, `…438X`, `…1960`, `…4701`), wrong-check INVALID, short/long/non-ASCII INVALID-or-MISSING per §9 map, provenance attrs, strategy pins → FAIL. Implement: two classes + `_mod_11_2_check` (research §7.2). Verify: `uv run pytest tests/capabilities/isni/test_rules.py -q` → PASS.

---

### Task 4: Contract + Capability wiring (TDD)

**Files:** `paxman/capabilities/ISNI/contract.py`, `paxman/capabilities/ISNI/capability.py`, `tests/capabilities/isni/test_contract.py`, `tests/capabilities/isni/test_capability.py`

**Goal:** `ISNIContract` (`DEFAULT_OUTPUT_FORMAT = "isni"`, `OFFERED = {"compact", "urn"}`, `capability_name = "isni"`, frozen without slots); `ISNICapability` wiring (1 grammar, 2 rules) + `format_value()` (`compact` strip, `urn` carrier, default identity); `create_contract()` common-block-only (no v1 flags) (research §6).

- [ ] Failing tests: defaults/offered pins, `ContractError` on `output_format="hyphenated"`, wiring counts, `format_value` round-trips (`compact`/`urn` re-enter under default contract), frozen-dataclass pins → FAIL. Implement both files. Verify: `uv run pytest tests/capabilities/isni/test_contract.py tests/capabilities/isni/test_capability.py -q` → PASS.

---

### Task 5: Bootstrap registration + CLI dispatch (TDD)

**Files:** `paxman/api/bootstrap.py`, `paxman/capabilities/__init__.py`, `paxman/cli.py`, `tests/unit/test_bootstrap.py`, `tests/unit/test_capability_exports.py`, `tests/e2e/test_bootstrap.py`

**Goal:** `register_all_shipped()` returns 28 names; `paxman isni "…"` and `paxman scan -c isni` dispatch; export alias `ISNI` in `__all__` (N814 scoped per-file-ignore precedent).

- [ ] Failing tests: shipped-count 28, `isni` in `--list`, CLI smoke `paxman isni "ISNI 0000 0001 2103 2683"` → `0000 0001 2103 2683` → FAIL. Implement wiring. Verify: `uv run pytest tests/unit/test_bootstrap.py tests/unit/test_capability_exports.py tests/e2e/test_bootstrap.py -q` → PASS.

---

### Task 6: Integration — resolution map + temporal filtering (TDD)

**Files:** `tests/integration/test_isni_pipeline.py` (create)

**Goal:** Pin research §9 map end-to-end: SUCCESS rows (spaced/compact/hyphen/URI/urn/lowercase-x), INVALID (bad check), MISSING (glued/double-space/pipes/short-long), `MultipleMentionsError` (two distinct), `year=2023` → INVALID (2024 rules dropped), `pinned_rules`/`excluded_rules` behavior, `_clean_registry` fixture.

- [ ] Failing tests: one test per §9 row → FAIL. Implement: no source change expected (pipeline owns it); fix capability on failure. Verify: `uv run pytest tests/integration/test_isni_pipeline.py -q` → PASS.

---

### Task 7: Property tests — hypothesis + shared matrices (TDD-light)

**Files:** `tests/property/test_isni_properties.py` (create), `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py` (modify)

**Goal:** Random 15-digit base + computed check → self-canonicalization; random strings → INVALID/MISSING with high probability; spaced/compact/hyphen/urn equivalence; re-entry rows for `isni` default + `compact`/`urn` (ADR-0010); preservation-matrix rows for `compact`/`urn` (ADR-0011).

- [ ] Failing tests: property suite + new matrix rows → FAIL. Implement tests (and fix capability on failure). Verify: `uv run pytest tests/property/test_isni_properties.py -q` → PASS; full property file green for the touched matrices.

---

### Task 8: Docs sync — every surface that lists capabilities

**Files:** `README.md` (via generator), `CONTEXT.md`, `docs/user/capabilities/isni.md` (create, mirroring `orcid.md` sections), `docs/user/capabilities/index.md`, `docs/user/api-reference.md` (output-format table + quick lookup), `docs/user/concepts/capabilities.md`, `docs/user/glossary.md`, `docs/user/citations.md` (ISO 27729 row), `docs/user/index.md`, `docs/user/migration.md`, `CHANGELOG.md`, `docs/development/MILESTONE.md`, `benchmarks/scenarios.py` + `benchmarks/baseline.json`

**Goal:** 28th capability visible everywhere the other 27 are; README table regenerated (not hand-edited); MILESTONE §1 gains the ISNI row and §2B #19 is struck.

- [ ] Checklist: generator run `uv run python tools/generate_readme_table.py` shows ISNI row; user guide with recognized-forms/statuses/notebook/provenance; citations ISO row; migration + CHANGELOG Unreleased entries; benchmark scenario (`ISNI 0000 0001 2103 2683`, verified SUCCESS) + refreshed baseline. Verify: `git status` shows all listed paths touched; `uv run pytest -m benchmark -q` → PASS.

---

### Task 9: Full quality gate

**Files:** none (verification only)

**Goal:** Merge-ready tree.

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest` → all green, coverage ≥95. Commit per task already done; final commit message `feat(isni): ISNI capability (ISO 27729:2024 + MOD 11-2)`.

---

Plan saved. Execute task-by-task via `tdd`; review with `paxman-momus-review` then `paxman-oracle-review`.
