# Slice E — Suite Hygiene (#154 hunt) + Docstring Closeout (#107)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Hunt the `test_cli_scan_default_all_json` flake (#154) with a time-boxed loop repro and fix it iff a suite-hygiene root cause is found, and close out the #107 docstring debt with a regression-pinned docstring pass — no behavior changes either way.

**Architecture:** Docs-only-plus-tests slice: docstrings on the exact public functions CodeRabbit flagged (stages, scanner, regen tool), pinned by a new docstring-presence unit test; flake hunt is investigation-first (loop repro → isolate ordering/shared-state → minimal hygiene fix or evidence report). No grammar/rule/contract/engine/core logic changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (`-m property`, e2e `tests/e2e/test_cli_scan.py`), `tools/regenerate_unicode_property_data.py --check`.

**References:** Issues #154 (flake), #107 (docstrings + SC triage); `paxman/core/grammar/stages.py:197-224` (`__post_init__`/`run` undocumented); `paxman/core/grammar/matchers/scanner.py:68` (`match` undocumented); `tools/regenerate_unicode_property_data.py:28,36,69,76,109` (5 helpers undocumented); `paxman/capabilities/BIC/grammar/bic_recognition.py:1,182` (module + `recognize` already documented — verify-only); `tests/unit/test_unicode_property_stage.py:101-106` (SC FDFC/FE0C pin already landed in Slice C — verify-only); `tests/e2e/test_cli_scan.py:42-52` (flake site, dual-span `or` at :52).

**Branch:** `feature/slice-e-suite-hygiene` (cut from `dev` — already exists).

---

## File Structure

- Modify: `paxman/core/grammar/stages.py:197-224` — docstrings for `UnicodePropertyStage.__post_init__` + `run` (class + `matches` already documented).
- Modify: `paxman/core/grammar/matchers/scanner.py:68` — docstring for `ScannerMatcher.match` (right-gap deferral behavior).
- Modify: `tools/regenerate_unicode_property_data.py:28,36,69,76,109` — docstrings for `_load_snapshot`, `_parse_ranges`, `_format_ranges`, `_render`, `main`.
- Create: `tests/unit/test_docstring_presence.py` — regression pin asserting every public function/method in the three files above has a docstring.
- Modify (iff root-caused): `tests/e2e/test_cli_scan.py` and/or suite hygiene (`tests/conftest.py`, e2e helpers) — minimal ordering/shared-state fix only.
- Docs: `CHANGELOG.md`.
- Verify-only (no edits): `bic_recognition.py` docs, SC pin test, `tools/regenerate_unicode_property_data.py --check` drift guard.
- No grammar/rule/contract/engine/core logic changes.

---

## Background the implementer needs

### Current state (verbatim)

#107 docstrings — the flagged functions are still bare. `stages.py:197-224`: class `UnicodePropertyStage` has a class docstring and `matches` has one, but `__post_init__` (range→regex build) and `run` (finditer→matches) have none. `scanner.py:68`: `match` has extensive inline comments (right-gap deferral rationale) but no docstring. Regen tool `:28,36,69,76,109`: all five module functions bare. BIC needs nothing: module docstring (`:1`) + `recognize` docstring (`def :182`, docstring `:183`) already present; helper constants are module data, not functions, so there is no further coverage-countable gap. SC triage needs nothing: `tests/unit/test_unicode_property_stage.py:105-106` already asserts `U+FDFC ∈ Sc` and `U+FE0C ∉ Sc` (landed Slice C); `unicode_ranges.py:26` keeps `(0xFDFC, 0xFDFC)` correctly.

#154 flake — `test_cli_scan_default_all_json` (`tests/e2e/test_cli_scan.py:42-52`) failed once in a combined property+e2e run during Slice B, green in isolation and in repeats (with and without slice changes); Slice C logged 10 hunt loops without repro. The suspect is line 52: `assert (8, 21) in country_spans or (9, 22) in country_spans` — a dual-span `or` that tolerates two "United States" spans (leading-space inclusion), i.e. the test itself documents a span nondeterminism it cannot pin. Candidate causes: cross-test registry pollution, tmp-cwd interaction, hypothesis profile interaction, or genuine ordering nondeterminism in `scan()` mention spans.

### Design decisions (locked)

1. **Docstrings = prose only, zero behavior delta.** One-line-or-short-paragraph `"""..."""` describing contract (args/returns/invariants), matching surrounding style. No refactoring while touching these functions; no signature changes.
2. **Presence test is the TDD vehicle.** Docstrings have no runtime behavior to red/green on, so Task 1's failing test is `tests/unit/test_docstring_presence.py` (asserts `__doc__` non-empty for the exact public callables listed) — FAILS on current tree, passes after the prose lands, and pins the debt shut.
3. **Flake hunt is time-boxed, fix-iff-root-caused.** Budget: 20 combined `property + test_cli_scan.py` loop iterations. If it trips, isolate (bisect ordering: `-p no:randomly` if applicable, single-worker, registry-reset audit) and fix only suite hygiene (test isolation, deterministic spans) — never production logic to satisfy a test. If green after 20, post the loop log as an evidence comment on #154 and leave it open; the slice still ships Task 1.
4. **#15/#150 code stays out** (rulings unratified — constraining Money to candidate codes / wontfixing the default need owner sign-off, not implementer initiative); **#71.3-4/#73 L3 stay out** (design-gated; #71.4 is blocked on the `zh-min-nan` scanner parity mismatch); **#148 remainder stays out** (broader tables need their own research-sized plan).

### Deferral → issue map

| Deferred matter | Home issue |
|---|---|
| Money single-separator code change / $ parity code change | #150 / #15 (awaiting ruling ratification) |
| Broader script/region tables, paren follow-ups | #148 (open, needs research plan) |
| Orchestrator per-grammar scoping, view roundtrip tightening, HealthCheck narrowing | #71 (open, design-gated) |
| Combinator leaf backtracking (L3) | #73 (open, design-gated) |
| ADR-0011 hard-mandate promotion | #139 (awaits future ADR) |
| Tracker bookkeeping | #146 (release-time) |
| Flake if unreproduced after budget | #154 (stays open with loop log) |

---

### Task 1: #107 closeout — docstring presence pin + prose

**Files:** `tests/unit/test_docstring_presence.py` (create), `paxman/core/grammar/stages.py:197-224`, `paxman/core/grammar/matchers/scanner.py:68`, `tools/regenerate_unicode_property_data.py:28,36,69,76,109`

**Goal:** Every public function/method CodeRabbit flagged carries a docstring, pinned against regression; SC pin and BIC docs confirmed green without edits.

- [ ] Failing test first: `test_docstring_presence.py` asserting non-empty `__doc__` for `UnicodePropertyStage.__post_init__`, `UnicodePropertyStage.run`, `ScannerMatcher.match`, and the five regen-tool functions (`_load_snapshot`, `_parse_ranges`, `_format_ranges`, `_render`, `main`). Run: `uv run pytest tests/unit/test_docstring_presence.py -q` → FAIL (7 missing).
- [ ] Implement: add prose docstrings only (contract/args/returns/invariants; scanner `match` documents the right-gap deferral + engine re-check). Verify: targeted → PASS; `uv run python tools/regenerate_unicode_property_data.py --check` green; `uv run pytest tests/unit/test_unicode_property_stage.py tests/capabilities/bic -q` → PASS (SC pin + BIC untouched); ruff/pyright clean on touched files.

### Task 2: #154 flake hunt — loop repro, fix iff hygiene cause

**Files:** investigation-first; edits (if any) confined to `tests/e2e/test_cli_scan.py`, `tests/conftest.py`, or e2e helpers

**Goal:** Reproduce the intermittent failure and fix its suite-hygiene cause, or bank a 20-loop green log as evidence on #154.

- [ ] Loop: `uv run pytest tests/property tests/e2e/test_cli_scan.py -q` × 20 (sequential, log each exit code + tail). If a trip occurs: capture full output, bisect (isolation vs combined, ordering seed, registry state via `_clean_registry` audit), fix test isolation only (e.g. pin the span assertion if the dual-span `or` hides real nondeterminism — only with evidence the span variance is illegitimate), re-loop 10× green.
- [ ] Either way: post loop log as evidence comment on #154 (fix PR reference if fixed; "unreproduced in 20, stays open" if not). Verify: `uv run pytest tests/e2e/test_cli_scan.py -q` → PASS; no production (`paxman/`) diff from this task.

### Task 3: Integrate + gate + close-out

**Files:** `CHANGELOG.md`

- [ ] CHANGELOG Unreleased/Fixed: #107 docstring closeout (+ #154 outcome: fixed or hunt-logged). Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest` → green; coverage ≥95. Close-out comments: #107 (per-function list — closable), #154 (loop log — closable only if root-caused). Commit per task.
