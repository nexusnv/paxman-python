# Suppression A0 — Whole-Input Exemption Implementation Plan (issue #122)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Land the decided A0 policy from #122 — under `suppress_common_words=True`, a suppressible word-bounded hit that covers the entire trimmed input is **never suppressed** (`canonicalize("to", Country, suppress=True)` → `SUCCESS "TO"`) — plus a suppression signal on `ExecutionResult`, the ADR-0009 §16 amendment, and the re-entry-under-suppression cross-link to #123.

**Architecture:** One condition added to the existing suppression guard in the kernel engine loop (`paxman/core/grammar/engine_loop.py:144-150`) — no new machinery, no matcher/grammar changes. Suppressed hits become observable via a keyword-only collector threaded from `run_capability()` through `_recognize()` into the engine loop, surfaced as two new defaulted fields on the frozen `ExecutionResult` dataclass. Both `canonicalize()` and `scan()` share the engine loop, so the exemption applies to whole-input mentions on both surfaces (embedded prose mentions stay suppressed, locked by the existing B1 scan snapshot). Provenance-neutral by construction: suppressed recognition is still never emitted, never validated, never canonicalized.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/property/integration). Touches `paxman/core/grammar` (kernel) and `paxman/engine` (orchestrator); no `paxman/core` import-direction change; no capability packages.

**References:**
- Issue #122 (decision: A0 adopted, A1 rejected; sub-task list) — this plan implements all four sub-tasks.
- `paxman/core/grammar/engine_loop.py:87` (`text = context.text`), `:109-118` (hit → `view.original_span`), `:137-139` (stripped-chars re-absorption), `:144-150` (B1 suppression block — the edit site).
- `paxman/core/grammar/matcher_spec.py:53` (`suppressible: bool = False`); suppressible matchers: `paxman/capabilities/Country/grammar/alpha2_recognition.py:31`, `alpha3_recognition.py:29`, `numeric_recognition.py:30`, `paxman/capabilities/Language/grammar/language_code_recognition.py:42`, `paxman/capabilities/Currency/grammar/code_recognition.py:30` — all `view=None` (identity view; no stripped-chars interaction today).
- `paxman/core/grammar/data/common_words.py:44-118` (`COMMON_WORDS` 67, lowercase frozenset, size guard).
- `paxman/engine/orchestrator.py:62-71` (`ExecutionResult`), `:106` + `:140-151` (`run_capability` recognition call + result construction), `:194` (`run_scan` call — untouched), `:237-303` (`_recognize`, engine-loop call at `:303`).
- `paxman/core/capability_contract.py:56` (`suppress_common_words: bool = False`).
- `docs/adr/0009-recognition-kernel.md` — revision history (Rev.4 row at line 43) + §16 (line 788+); `docs/adr/0010-re-entry-fixed-point-invariant.md` (untouched; cross-referenced).
- `tests/unit/test_b1_common_word_suppression.py:105-116` (locked `MISSING` behavior — updated by Task 1), `:58-102` (scan snapshots — must keep passing).
- `tests/property/test_reentry_invariant.py:105-163` (ROWS table), `:166-178` (`_fresh_registry` — documented registry exception; extended in place per `tests/AGENTS.md`).
- Monkeypatch safety: direct `_recognize`/`_run_matchers_with_context` callers pass positionally (`tests/unit/test_coverage_remediation.py::test_recognize_error_paths` ~:1050-1130, `tests/unit/test_contract_surface.py:75`), so the keyword-only `suppressed_out` addition (default `None`) keeps them passing; no test patches `run_matchers_with_context` with a strict signature (nearest monkeypatch is `CandidatesMatcher → None`).

**Branch:** `feature/suppression-a0-whole-input` (cut from `dev` @ 450f87b — 15 commits behind current `dev` @ 096e340 at review time; rebase before implementing; not a hotfix — no worktree).

---

## Background the implementer needs

### Decided policy (issue #122, locked)

**A0 — whole-input exemption, no A1 fallback.** `paxman/core/grammar/engine_loop.py:144-150` suppression (`contract.suppress_common_words and matcher.suppressible and text[o_s:o_e].lower() in COMMON_WORDS`) is **skipped when the hit span equals the trimmed whole input** (`text.strip()`). Case-insensitive suppression (via `.lower()`) over per-hit word-bounded `BoundarySpec.WORD` hits only. **A1** (`x→0` fallback: if suppression would leave 0 mentions, keep the unsuppressed set) is evaluated and **rejected** in the issue — delta `A1−A0` is a synthetic code-list-with-suppress or English fragment (`"to and is"`) where suppression-to-`MISSING` is the desired noise reduction; do not implement A1.

Rationale: calling `canonicalize()` with a contract **asserts the kind** — "a canonical value is derivable from this input" — so suppressing the whole input contradicts the asserted intent (`MISSING` indistinguishable from `canonicalize("")`). `scan()` is the prose surface where embedded-noise suppression is legitimate. Canonical values that are themselves common words (`TO`, `IN`, `CA`, `NO`, `US`, `ID`, `ST` / `en`, `ca`, `id`, `la`, `et`, `be`, `my`, `no` / `ALL` / `cd`) must re-enter (ADR-0010 fixed point, #123).

### Current suppression block (verbatim, `engine_loop.py:140-150`)

```python
                # ADR §16 common-word suppression (B1): short-code matchers marked
                # suppressible are skipped when contract requests it and the
                # word-bounded hit is a high-frequency English function word.
                # Provenance-neutral: suppressed recognition never canonicalizes.
                if (
                    contract is not None
                    and bool(getattr(contract, "suppress_common_words", False))
                    and bool(getattr(matcher, "suppressible", False))
                    and text[o_s:o_e].lower() in COMMON_WORDS
                ):
                    continue
```

At this point in the loop `(o_s, o_e)` are already original-text coordinates: `view.original_span` ran at `:118` and stripped-char re-absorption at `:137-139`. The edit site is correct as-is — **no code moves**; the guard only gains the exemption condition and the collector append.

### Empirical baseline (verified on `dev` @ 450f87b, 2026-09-03)

| Input | Contract | Today (pre-A0) | Post-A0 expected |
|---|---|---|---|
| `to` | Country, suppress=True | `MISSING` | `SUCCESS "TO"` |
| `TO` | Country, suppress=True | `MISSING` | `SUCCESS "TO"` |
| `  to  ` (padded) | Country, suppress=True | `MISSING` | `SUCCESS "TO"` |
| `in/` (2≠3 chars) | Country, suppress=True | `MISSING` | `MISSING`, suppressed_count=1 |
| `in56` / `2in` | Country, suppress=True | `MISSING` | `MISSING`, suppressed_count=0 (`\w` boundary → never recognized) |
| `999` | Country, suppress=True | `INVALID` | `INVALID`, suppressed_count=0 |
| `to and 999` | Country, suppress=True | `INVALID` | `INVALID`, suppressed_count=2 |
| `to and usa` | Country, suppress=True | `SUCCESS "US"` | unchanged (embedded `to`/`and` *and* the α3 `usa` hit stay suppressed — `usa` ∈ `COMMON_WORDS`; survival is via the non-suppressible `name_recognition` hit at the same span, verified: suppress-ON scan shows only `((7,10), 'name_recognition')`) |
| `ALL` | Currency, suppress=True | `MISSING` | `SUCCESS "ALL"` |
| `en` | Language, suppress=True | `MISSING` | `SUCCESS "en"` |
| `cd` | SIUnit, suppress=True | `SUCCESS "cd"` | unchanged (no SIUnit matcher is `suppressible`) |
| `scan("to", [Country supp])` | Country | 0 mentions | 1 mention (whole input exempt) |
| `scan(TEXT)` b1 suite (embedded `to`) | Country/Currency | locked snapshots | unchanged |

Fact behind the `to and 999` row: recognition matchers are shape-based (word-bounded 3-letter tokens), so `and` **is** hit by the α3 matcher and suppressed — recognition ≠ validation. Locked by the existing scan snapshot asserting `the` (8,11) remains a mention.

### Design decisions (locked)

1. **Exemption comparison — raw slice equality:** suppress only when `text[o_s:o_e] != text.strip()`. Both sides derive from `text`, so equality holds iff the hit covers exactly the trimmed region; case plays no role. Matches the issue's phrasing ("hit span equals the trimmed whole input via `view.original_span` after re-absorption"). Padded inputs (`"  to  "`) are exempt — the hit lands exactly on the trimmed region.
2. **Compute `text.strip()` once per call, only when the flag is on** (lazy: `None` when flag off) — zero cost on the default path, no per-hit recompute.
3. **Collector, not a return-type change:** `_run_matchers_with_context` / `run_matchers_with_context` gain a keyword-only `suppressed_out: list[tuple[int, int]] | None = None`. `run_matchers` / `_run_matchers` (no contract → suppression can never fire) stay unchanged, so `PipelineGrammar.recognize` delegation (`paxman/core/grammar/pipeline.py:41`), SIUnit's internal call (`paxman/capabilities/SIUnit/grammar/symbol_recognition.py:111`), the parity property suites, and `benchmarks/` are untouched.
4. **`_recognize` threads the collector** via keyword-only param (return type unchanged — direct positional callers in `tests/unit/test_coverage_remediation.py::test_recognize_error_paths` and `tests/unit/test_contract_surface.py:75` keep passing). `run_scan` does **not** pass a collector (scan's signal is the absence of mentions; explicit non-goal).
5. **`ExecutionResult` gains two defaulted frozen fields:** `suppressed_count: int = 0` and `suppressed_spans: tuple[tuple[int, int], ...] = ()`. Populated **unconditionally** when suppression fires (covers `MISSING` *and* `INVALID`, per the issue's "not just MISSING"); `0`/`()` when the flag is off. Spans deduplicated order-preserving (`dict.fromkeys`) because two matchers could in principle suppress the identical span.
6. **CLI unchanged:** `_print_json` builds its payload from an explicit field list (`paxman/cli.py:269-300`); the issue scopes the signal to `ExecutionResult`. Documented as a non-goal, not an oversight.
7. **No `recognition_revision` bump:** the revision digest covers matcher/table data (ADR-0009 §13), not engine cross-match policy; the guard is flag-gated and off by default. `benchmarks/grammar_stage_parity.py` drives no contract → suppression never fires there.
8. **ADR-0009 amended in place (Rev.5)** rather than a successor ADR — §16 is the suppression home and already carries the Rev.4 shipped-off-by-default amendment. ADR-0010 (re-entry) is referenced, not edited.
9. **`in/` semantics stay MISSING-by-suppression** (only the whole input is exempt) — this is exactly the diagnostic case the new signal exists for: `MISSING` + `suppressed_count == 1` ≠ `MISSING` + `suppressed_count == 0`.

---

## File Structure

- Modify: `paxman/core/grammar/engine_loop.py` — A0 exemption condition + `suppressed_out` collector (+ `run_matchers_with_context` alias signature)
- Modify: `paxman/engine/orchestrator.py` — `ExecutionResult` +2 fields; `_recognize` kw-only param; `run_capability` collector wiring
- Test: `tests/unit/test_b1_common_word_suppression.py` — update locked `test_canonicalize_to_off_vs_on`; add A0 + signal cases
- Test: `tests/property/test_reentry_invariant.py` — suppression re-entry rows (cross-link #123)
- Docs: `docs/adr/0009-recognition-kernel.md` (Rev.5 + §16 amendment), `README.md` (:472, :665-666), `CONTEXT.md` (:12, :902), `docs/user/migration.md`, `docs/user/api-reference.md` (:223), `docs/user/concepts/execution-result.md`, `CHANGELOG.md`

No new modules; no capability packages; no contract field changes.

---

### Task 1: A0 whole-input exemption — RED then GREEN

**Files:** `tests/unit/test_b1_common_word_suppression.py`, `paxman/core/grammar/engine_loop.py`

**Goal:** Whole-input suppressible hits are never suppressed; embedded ones still are.

- [ ] Update the locked test `test_canonicalize_to_off_vs_on` (`:105-116`): the `on` half now asserts `SUCCESS` / `"TO"` (rename to `test_canonicalize_to_off_vs_on_whole_input_exempt`). Keep the `off` half byte-identical (`SUCCESS "TO"`).
- [ ] Add A0 cases (Country contracts, `suppress_common_words=True`, each with `reset_registry()` + `register_all_shipped()` per the file's existing pattern):
  - `test_whole_input_exempt_variants`: `"to"`, `"TO"`, `"  to  "`, `"to\n"` → `SUCCESS "TO"` (covers trimmed-region equality incl. padding).
  - `test_embedded_still_suppressed`: `"in/"` → `MISSING`; `"to and usa"` → `SUCCESS "US"` (embedded exemption must not leak).
  - `test_boundary_never_recognized`: `"in56"`, `"2in"` → `MISSING` (no recognition at all — `\w` boundary; distinct from suppression).
- [ ] Add a scan whole-input case: `scan("to", [Country suppress=True])` → exactly 1 country mention with span `(0, 2)`. Existing scan snapshot tests (`:58-102`) must keep passing unchanged.
- [ ] Implement in `engine_loop.py`: hoist `suppress_on` / `trimmed_input = text.strip() if suppress_on else None` above the matcher loop; extend the guard at `:144-150` with `and text[o_s:o_e] != trimmed_input`; reword the block comment to cite A0/#122. Do not move the block (it must stay after `original_span` `:118` and re-absorption `:137-139`).
- [ ] Run: `uv run pytest tests/unit/test_b1_common_word_suppression.py -v` → Expected: PASS (new cases green, snapshots untouched). Commit: `feat(kernel): A0 whole-input suppression exemption (#122)`.

### Task 2: Suppression signal on `ExecutionResult` — RED then GREEN

**Files:** `paxman/engine/orchestrator.py`, `tests/unit/test_b1_common_word_suppression.py`

**Goal:** Callers can distinguish "nothing recognized" from "recognized but suppressed" for `MISSING` and `INVALID`.

- [ ] Failing tests first (same file, new section):
  - `test_suppression_signal_defaults`: a `suppress_common_words=False` run (e.g. `canonicalize("to", Country)`) → `suppressed_count == 0`, `suppressed_spans == ()`.
  - `test_suppression_signal_missing`: `canonicalize("in/", Country suppress=True)` → `MISSING`, `suppressed_count == 1`, `suppressed_spans == ((0, 2),)`.
  - `test_suppression_signal_invalid`: `canonicalize("to and 999", Country suppress=True)` → `INVALID`, `suppressed_count == 2`, `set(suppressed_spans) == {(0, 2), (3, 6)}` (set-form assertion: cross-grammar emission order is deterministic but not what this test locks).
  - `test_suppression_signal_success_embedded`: `canonicalize("to and usa", Country suppress=True)` → `SUCCESS`, `suppressed_count == 3`, `set(suppressed_spans) == {(0, 2), (3, 6), (7, 10)}` (signal populated regardless of status; embedded `to`/`and` suppressed while `usa` survives via `name_recognition` — note the α3 `usa` hit at `(7, 10)` IS itself suppressed since `usa` ∈ `COMMON_WORDS`, so the count is 3, not 2).
- [ ] Implement:
  - `ExecutionResult` (`orchestrator.py:62-71`): add `suppressed_count: int = 0` and `suppressed_spans: tuple[tuple[int, int], ...] = ()` after `span`, with a docstring line citing ADR-0009 §16 + #122 (diagnostic for `MISSING`/`INVALID` under `suppress_common_words=True`; `0`/`()` when the flag is off).
  - `_run_matchers_with_context` + `run_matchers_with_context` (`engine_loop.py`): keyword-only `suppressed_out: list[tuple[int, int]] | None = None`; append `(o_s, o_e)` inside the suppression branch before `continue`. `run_matchers`/`_run_matchers` signatures unchanged.
  - `_recognize` (`orchestrator.py:237`): keyword-only `suppressed_out: list[tuple[int, int]] | None = None`, forwarded to the `run_matchers_with_context` call at `:303`. Return type unchanged; `run_scan` call at `:194` passes nothing.
  - `run_capability` (`:106`): create `suppressed: list[tuple[int, int]] = []`, pass `suppressed_out=suppressed`, then `suppressed_unique = tuple(dict.fromkeys(suppressed))` and set both new fields from it in the `ExecutionResult(...)` construction at `:140-151`.
- [ ] Run: `uv run pytest tests/unit/test_b1_common_word_suppression.py tests/unit/test_coverage_remediation.py -q` → Expected: PASS (direct `_recognize` callers pass positionally, so the keyword-only addition is compatible). Commit: `feat(engine): suppression observability on ExecutionResult (#122)`.

### Task 3: Re-entry under suppression (cross-link #123)

**Files:** `tests/property/test_reentry_invariant.py`

**Goal:** Canonical values that collide with `COMMON_WORDS` re-enter as fixed points under `suppress_common_words=True` — the ADR-0010 invariant extended to the suppressed surface.

- [ ] Extend the module docstring with one paragraph: the `SUPPRESS_ROWS` section is the #122 A0 cross-link to #123 — common-word canonical values must satisfy Property 2 with the suppression flag on (this file is already the documented registry exception, `tests/AGENTS.md` CONVENTIONS).
- [ ] Add `SUPPRESS_ROWS` reusing the module's `_row` factory with the suppression flag as contract kwarg (e.g. `_row(Country, "TO", "TO", suppress_common_words=True)`), covering every suppressible matcher family plus the not-suppressible control. Keep it a **separate** table from `ROWS` so the `assert ROWS == shipped` structural gate is untouched:
  - `(Country, "TO")`, `(Country, "IN")`, `(Country, "US")`, `(Country, "ST")` (α2)
  - `(Language, "en")`, `(Language, "ca")` (ISO 639-1)
  - `(Currency, "ALL")` (ISO 4217 — the only suppressed α3 currency)
  - `(SIUnit, "cd")` (control: matcher not suppressible — must already pass)
- [ ] Add `test_reentry_under_suppression` (`@pytest.mark.parametrize` over `SUPPRESS_ROWS` with ids): build `factory.create_contract(suppress_common_words=True)`, assert `canonicalize(value, contract)` → `SUCCESS` with `canonicalized_value == value` (single-token canonicals are their own fixed point; the first call *is* the re-entry of an emitted `V`).
- [ ] Add padded-variant coverage: parametrize the same rows over `("  " + value + "  ", value + "\n")` asserting the same fixed point (exempt hit lands on the trimmed region; mirrors the suite's `case_ws_variants` style — no hypothesis needed, explicit rows).
- [ ] Run: `uv run pytest tests/property/test_reentry_invariant.py -q` → Expected: PASS, including all pre-existing rows. Commit: `test(property): re-entry under suppression — #123 cross-link (#122)`.

### Task 4: ADR-0009 Rev.5 amendment — §16 records A0

**Files:** `docs/adr/0009-recognition-kernel.md`

**Goal:** The decision (A0 adopted, A1 rejected) and its consequences are recorded where §16 suppression lives.

- [ ] Add revision-history row: `Rev.5 | 2026-09-03 | <author> | §16 amendment (#122): A0 whole-input exemption — suppressible word-bounded hits covering the trimmed whole input are never suppressed; A1 (x→0 fallback) evaluated and rejected; ExecutionResult gains suppressed_count/suppressed_spans; re-entry under suppression locked in the ADR-0010 property suite.` (mirror the Rev.4 row's style/linking).
- [ ] In §16, after the suppression bullet, add a dated "Amendment (Rev.5, #122)" paragraph: the intent model (`canonicalize()` asserts the kind), the exemption semantics (trimmed whole input via `view.original_span` + re-absorption, word-bounded, case as matched), the canonical-value collision table it fixes (`TO/IN/CA/NO/US/ID/ST`, `en/ca/id/la/et/be/my/no`, `ALL`, `cd`), the explicit A1 rejection rationale, the new `ExecutionResult` signal, and the cross-reference to ADR-0010/#123 for the fixed-point guarantee.
- [ ] Run: `grep -n "Rev.5" docs/adr/0009-recognition-kernel.md` → row present; no ADR-0010 edits (`git diff --stat docs/adr/0010-re-entry-fixed-point-invariant.md` → empty). Commit: `docs(adr): ADR-0009 Rev.5 — §16 A0 amendment (#122)`.

### Task 5: Docs + changelog sync

**Files:** `README.md`, `CONTEXT.md`, `docs/user/migration.md`, `docs/user/api-reference.md`, `docs/user/concepts/execution-result.md`, `CHANGELOG.md`

**Goal:** User-facing surfaces describe the new behavior and the new fields; the #122-pending note in CONTEXT.md is retired.

- [ ] `README.md:484` contract-table row → describe the exemption: suppresses common-word noise on scan/prose **except** when the whole input is the word (A0, #122); default `False` (ADR-0009 §16).
- [ ] `README.md:677-678` prose → reword the "bare `canonicalize("to")` stays `SUCCESS "TO"` when the flag is off" sentence: it now holds with the flag on too (whole-input exempt), while `scan()` prose still drops embedded `to`.
- [ ] `docs/user/migration.md` → new "0.4.0 — Whole-input suppression exemption (A0, #122)" section before the 0.2.0 suppression note: behavior-change table (`MISSING` → `SUCCESS` for `to/TO/padded/ALL/en` under the flag), the new `ExecutionResult` fields with a `MISSING`+`suppressed_count` diagnostic example, A1 rejection note, link to ADR-0009 Rev.5.
- [ ] `docs/user/api-reference.md:223` (`class ExecutionResult`) → add the two fields with types/defaults/meaning; `docs/user/concepts/execution-result.md` → add a short "Suppression signal" subsection (when populated, what it distinguishes).
- [ ] `CONTEXT.md:12` re-entry note → replace "or `suppress_common_words=True` for whole-input common words may break this until #122 A0 lands" with the landed guarantee (whole-input canonical values re-enter; enforced by the extended property suite). `CONTEXT.md:902` suppression line → append A0 + signal mention.
- [ ] `CHANGELOG.md` → unreleased/0.4.0 entries: **Changed** (whole-input exemption under `suppress_common_words=True`), **Added** (`suppressed_count`/`suppressed_spans` on `ExecutionResult`), **Docs** (ADR-0009 Rev.5).
- [ ] Run: `grep -rn "until #122" CONTEXT.md README.md docs/` → no stale pending-state text. Commit: `docs: A0 exemption + suppression signal across user surfaces (#122)`.

### Task 6: Full gate

- [ ] `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint` → all green (no new ignores; root AGENTS.md ban).
- [ ] `uv run pytest -q` → full suite green; `uv run pytest tests/property/test_reentry_invariant.py tests/unit/test_b1_common_word_suppression.py -v` explicitly confirmed.
- [ ] `uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q` then `uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → ≥95 with the new `engine_loop`/`orchestrator` branches covered by Tasks 1-2.
- [ ] `uv run python -m paxman country "to" --suppress-common-words` → CLI smoke: `status: SUCCESS`, `value: TO` (behavior change visible end-to-end; CLI output format itself unchanged).

---

## Explicit non-goals (per issue #122 — do not implement)

1. **A1 `x→0` fallback** — rejected in the issue; `"to and is"` under `suppress=True` stays `MISSING` (with `suppressed_count == 3` making the why visible).
2. **`scan()`/CLI suppression signal** — issue scopes the observability sub-task to `ExecutionResult`; scan callers see suppression as absent mentions. CLI `--json` payload stays as-is (explicit field list).
3. **`recognition_revision` bump / benchmark changes** — flag-gated engine policy, off by default; parity suites and `benchmarks/` drive no contract.
4. **New capabilities** (Element et al.) — out of scope for this plan; sequencing note: the issue's "blocked on #123" gate is spent (#123 closed with ADR-0010 merged), so capability work resumes under the ADR-0010 `ROWS` gate, not this issue.
5. **Version bump to 0.4.0** — release chore, separate from this issue.

## QA scenarios (post-implementation spot checks)

| Input | Contract | Expected |
|---|---|---|
| `canonicalize("to", C)` | Country, suppress on | `SUCCESS "TO"`, suppressed 0/() |
| `canonicalize("  ALL  ", C)` | Currency, suppress on | `SUCCESS "ALL"` |
| `canonicalize("in/", C)` | Country, suppress on | `MISSING`, count 1, spans `((0,2),)` |
| `canonicalize("to and is", C)` | Country, suppress on | `MISSING`, count 3 (A1 rejected — visible, not hidden) |
| `canonicalize("to and usa", C)` | Country, suppress on | `SUCCESS "US"`, count 3, spans `{(0,2),(3,6),(7,10)}` (α3 `usa` suppressed; survives via `name_recognition`) |
| `canonicalize("to", C)` | Country, suppress off | `SUCCESS "TO"`, count 0 (byte-identical default path) |
| `scan("Ship to United States", [C])` | Country, suppress on | 1 mention `(8, 21)` = "United States" — embedded `to` suppressed |
| `canonicalize("cd", C)` | SIUnit, suppress on | `SUCCESS "cd"` (not suppressible — unchanged) |

## Risks / notes

- **Behavior change is intentional and regression-locked:** the pre-A0 `MISSING` for whole-input common words is locked by a test today; Task 1 rewrites that lock (issue: "test updated"). Called out in migration docs (mirrors the §16 Rev.4 "from wrong to right" precedent).
- **Shared engine loop ⇒ `scan()` whole-input mentions appear** (0 → 1 for `scan("to")`). Intended (a whole-input mention is not prose noise); covered by a Task 1 test so it cannot regress silently.
- **Determinism:** collector order follows the engine loop's fixed grammar×matcher×hit order; `dict.fromkeys` dedup is order-preserving; tests assert sets where cross-grammar order is incidental.
- **Coverage gate:** new branches are exercised by Tasks 1-2 tests; no `# type: ignore` / `# noqa` permitted in `paxman/` source.
