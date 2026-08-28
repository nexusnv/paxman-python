# ADR-0009 Recognition Kernel — Remediation Plan

| | |
|---|---|
| **Title** | Kernel remediation — fix the landed ADR-0009 regressions, collect the deferred value, close the verification gaps |
| **Date** | 2026-08-26 |
| **Status** | Draft — REVISE applied (2026-08-26): A4b locked to Option 1, B3→B3a/b/c, B4→B4a/b, perf targets recorded-not-gating, B1/C1 budgets quantified, A0/A7 gates hardened — for review |
| **Branch** | `fix/adr0009-kernel-remediation` (create before Task A0; one commit per task, linear history) |
| **Findings source** | `docs/development/reports/2026-08-26-adr0009-recognition-kernel-post-landing-evaluation.md` (findings R1–R12) |
| **Authoritative spec** | `docs/adr/0009-recognition-kernel.md` — where this plan and the ADR disagree, the ADR wins; the one deliberate ADR amendment (D3 offset invariant, Task A4) is recorded as ADR Rev.4 |
| **Related** | `docs/development/plans/2026-08-24-recognition-kernel.md` (original implementation plan — **do not** cite it from code; see Task A8), ADR-0004 (single-value invariant), ADR-0008 (Obsolete) |
| **Release target** | 0.2.0 (already the in-tree version; nothing here adds a new breaking surface beyond what 0.2.0 already declares) |
| **Revision** | 2026-08-26 REVISE — Oracle GO WITH CHANGES + Momus REVISE (A4b locked, B3/B4 split, A0/A7 hardened, perf recorded, B1/C1 quantified) |

> **For agentic workers — REQUIRED SUB-SKILLS:** `test-driven-development` (RED → GREEN → refactor
> per task), `verification-before-completion` (run the verify command; evidence before claims).
> Every task ends with the scoped verify command and an atomic commit whose message is given in
> the task header. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Standing rule:** no behavior change in Part A except where a task explicitly declares one and
> locks it with a regression test. Part A is *make the landed kernel as fast and as honest as the
> ADR says it already is*. Part B is *collect the value*. Part C is *close the gates*.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | A0 — measurement first: fix the benchmark ruler, record pre-remediation numbers | ☐ pending | |
> | A1 — BoundarySpec compiled form (O(1) hit-position checks) | ☐ pending | |
> | A2 — memoize per-matcher digests; freeze cost → ~ms | ☐ pending | |
> | A3 — emit-signature validation once; drop per-call `inspect` | ☐ pending | |
> | A4 — two-array offset maps; fix span-end translation (ADR D3 amendment) | ☐ pending | |
> | A5 — `CountryNameFold` single-pass NFD | ☐ pending | |
> | A6 — `view="country_normalized"`; remove legacy alias + warning | ☐ pending | |
> | A7 — single recognition path; parity gate gates production | ☐ pending | |
> | A8 — ADR-0009 → Accepted (Rev.4); de-reference plan docs from code; sync AGENTS.md | ☐ pending | |
> | B1 — suppression table + `suppress_common_words` flag | ☐ pending | |
> | B2 — combinator kind + SIUnit split-prefix (19,530 → 820 tokens) | ☐ pending | |
> | B3a — scanner kind: Language BCP-47 migration (delete the fork) | ☐ pending | |
> | B3b — scanner kind: URL paren-balance migration | ☐ pending | |
> | B3c — scanner kind: Phone E.164 migration | ☐ pending | |
> | B4a — candidates kind + Date 4→1 | ☐ pending | |
> | B4b — label kind + ISSN/IBAN | ☐ pending | |
> | B5 — stub-kind decision gate (property: populate or delete) | ☐ pending | |
> | C1 — Hypothesis corpora for parity shards | ☐ pending | |
> | C2 — re-baseline + recognition-only benchmark family; docs sync | ☐ pending | |

**Goal:** make the landed Recognition Kernel match its own ADR: hit-position boundary checks,
freeze-time compilation economics, exact span translation, one recognition path per grammar, no
plan-doc references in code — then collect the deferred value (suppression for a usable `scan()`,
the scanner/combinator/candidates/label migrations that justify the spine, starting with the
flagship BCP-47 fork deletion) — then harden the gates (property corpora, honest benchmarks).

**Findings → task mapping:**

| Finding (report §3) | Tasks |
|---|---|
| R1 boundary O(n) per hit | A1 |
| R2 freeze re-hashes lexicon; corrupted benchmark | A0, A2 |
| R3 per-call `inspect.signature` / match-time filtering | A3 |
| R4 split-prefix materialized (19,530 tokens) | B2 |
| R5 `CountryNameFold` 3.7× slow | A5 |
| R6/R6a span end over-extension; mention span quality | A4 (+ A4b decision) |
| R7 `scan()` noise; suppression deferred | B1 |
| R8 production `DeprecationWarning` | A6 |
| R9 stub kinds; flagship migrations unclaimed | B2, B3a, B3b, B3c, B4a, B4b, B5 |
| R10 dual recognition path; parity gates dead path | A7 |
| R11 ADR status Proposed; plan refs in code; AGENTS.md drift | A8 |
| R12 hand-picked parity corpora; no recognition-only benchmarks; stale baseline | A0, C1, C2 |

---

## Part A — P0 Remediation (surgical; no architecture change)

### Task A0 — Measurement first: fix the ruler, record the "before"

**Commit:** `fix(benchmarks): freeze outside timed region; add freeze-cost + recognition-only scenarios`

The benchmark harness currently resets the registry inside its timing loop, so every scenario
measures `freeze_registry()` (~50 ms for si_unit) instead of the pipeline. Fix the ruler before
changing the machine, and capture pre-remediation numbers so every later task's claim is
quantified.

- [ ] `benchmarks/harness.py::run_once`: move `reset_registry()` + `scenario["register"]()` +
      contract construction **before** `start = time.perf_counter()`; call
      `freeze_registry()` explicitly pre-timer so the timed region is scan+pipeline only. Keep the
      per-iteration reset (isolation), just not inside the timed window.
- [ ] Add a `"freeze"` scenario to `benchmarks/scenarios.py` for each registered capability set
      (or one whole-registry scenario): times `reset_registry(); register…; freeze_registry()`,
      reported separately. Freeze cost becomes visible and trackable instead of hiding inside
      p50s.
- [ ] Add the ADR Part IV recognition-only scenario family: per capability, three text sizes
      (64 B, 2 KB, 16 KB) running grammar recognition only (no rules, no contract machinery).
      These are the numbers Part A tasks must move.
- [ ] Record pre-remediation numbers in this plan's Progress table (or a sibling
      `benchmarks/preremediation-2026-08-26.json` kept out of the baseline slot): si_unit
      pipeline p50, si_unit recognition-only at 2 KB (~19.7 ms expected), freeze ms, suite warning
      count (68). **Do not** overwrite `benchmarks/baseline.json` yet — that is Task C2.
- [ ] RED first (falsifiable gate): `tests/unit/test_benchmark_harness_freeze.py` asserts the
      timed region excludes freeze — reads `benchmarks/harness.py` source and asserts
      `freeze_registry()` appears **before** `time.perf_counter()` in `run_once`, and that no
      `reset_registry()` / `scenario["register"]` call occurs between `start =` and the timed
      `canonicalize()` loop. Fails before the fix, passes after. The recorded numbers are the
      second proof.
- [ ] Re-run `uv run python -m benchmarks.harness --output /tmp/opencode/pre.json` and confirm
      si_unit p50 drops from ~61 ms to single-digit ms **before** any kernel change (proves the
      harness was the confound, per report R2).

**Verify:** `uv run pytest tests/unit/test_benchmark_harness_freeze.py -q` green;
`uv run python -m benchmarks.harness --output /tmp/opencode/pre.json` shows si_unit
p50 ≈ 2–3 ms (freeze removed from timing) and the freeze scenario reports ~50–75 ms; full gate
green.

### Task A1 — BoundarySpec compiled form: O(1) checks at hit positions

**Commit:** `perf(kernel): compile BoundarySpec to frozensets; O(1) hit-position checks (ADR §10)`

This is the single highest-impact fix (report R1: boundary checking is ~89% of SIUnit trie scan
time; the kernel is ~3× slower than the legacy alternation it replaced).

Design:

- [ ] Add a compiled form, built once per `BoundarySpec` (they are frozen singletons — compile in
      `__post_init__` via `object.__setattr__`, mirroring `AnchorSet._class_res`):
  - `left_chars: frozenset[str] | None` — when the pattern is a single-character class
    (`r"\w"`, `r"[\w\-+−]"`, …), membership is `subject[start-1] in left_chars`.
  - `right_chars: frozenset[str] | None` — same for the right side (`subject[end] in right_chars`).
  - `left_multi: tuple[tuple[int, re.Pattern[str]], ...]` — for genuinely multi-char patterns
    (`ISBN10_LEAD`'s `r"\d[ -]"`): `(window_width, compiled_pattern)` applied to the bounded
    window `subject[max(0, start-w):start]` with a right anchor. **Never** slice the full prefix.
- [ ] Keep the `left`/`right` regex-string fields as the declarative source of truth (data-in,
      compiled-out — the ADR §10 model); compilation happens once, not per hit.
- [ ] RED: property test `tests/property/test_boundary_compiled_parity.py` — exhaustive
      per-preset table: for **every** preset in the §10 table (including `ISBN10_LEAD`'s
      `r"\d[ -]"` two-char window and `WORD`/`WORD_SIGN` single-char classes), generated texts
      via Hypothesis `st.text()` seeded with alphabet mixes incl. `° µ Ω · ⋅ −` and the preset's
      class chars, assert `check_boundary(text, s, e, spec) ==
      check_boundary_compiled(text, s, e, spec)` for all `(s, e)` spans on each generated text.
      This is the no-behavior-change proof; keep `left`/`right` regex-string fields as source of
      truth, compiled `frozenset`/`left_multi` as derived.
- [ ] Performance recording (not gating): SIUnit `symbol_recognition` on the 2 KB
      recognition-only scenario from A0 drops from ~19.7 ms to ≤ 4 ms (trie-without-boundary
      measured 2.46 ms; compiled checks should add ≤ 1 ms). Record before/after in PR body;
      **no fail-on-threshold** — the gate is the property parity test, not wall-clock.
      Target is recorded evidence, not an automatable timeout.
- [ ] Out of scope: word-anchored trie fast-path (skip left check at `word_spans` starts for
      `WORD`/`WORD_SIGN` presets). If the ≤4 ms target is not met, file a follow-up task
      `perf(kernel): word-anchored left-check elision` — do **not** expand scope inside A1.
      Keep this task data-driven.

**Verify:** `uv run pytest tests/property/test_boundary_compiled_parity.py -q` green; full gate
green; recognition-only 2 KB si_unit number recorded in PR body (≤4 ms target informational,
not gating).

### Task A2 — Memoize per-matcher digests; freeze cost → ~ms

**Commit:** `perf(kernel): per-matcher digest memoization; freeze_registry concatenates digests (ADR §13)`

Report R2: every `freeze_registry()` sorts/joins/hashes the full token set (~40 ms for SIUnit's
19,530 tokens; 75.8 ms full registry). A compiled matcher is a pure function of `(spec, snapshot)`
per ADR §13 — its digest is therefore computable **once**.

- [ ] Add `digest: str` (or `_digest`) to each matcher (`LexiconMatcher`, `RegexMatcher`,
      `PropertyMatcher`, `ScannerMatcher`) computed in `__post_init__` exactly once at
      construction (import time — matchers are module-level singletons): for lexicons,
      `sha256("\x00".join(sorted(tokens)))`; for regex, the pattern + flags; for scanners, the
      scan callable `__qualname__` + `max_window` + boundary repr (current fallback shape, minus
      the per-freeze sort).
- [ ] `discovery.freeze_registry()` reads `matcher.digest` instead of re-deriving token reprs;
      keeps `kind`, `view`, `boundary`, `anchors`, `requires_features`, `_chosen` in the hashed
      parts (these are cheap attribute reads).
- [ ] Memoize the snapshot-file hashing too: module-level `_snapshot_hashes: dict[str, str]`
      keyed by `(path, size, mtime_ns)` with a content-hash fallback on hit (if `mtime_ns`
      granularity is coarse on the runner, re-hash and compare); content-stable within a process;
      a fresh interpreter re-reads (determinism across processes preserved). Document the
      one-time `recognition_revision` hash-format change in the PR body (pre-release signal).
- [ ] RED: `tests/unit/test_discovery_revision.py` (extend) — freeze twice; assert
      `recognition_revision` identical AND a `repeated_freeze_helper()` (freeze N times in a loop
      and assert the **second onward** use cached digests by checking `matcher.digest` identity
      / call-count, not wall-clock). Timing assertion `< 5 ms` is recorded in PR body as
      informational evidence, **not** a gating assertion — avoids CI flakiness.
- [ ] Confirm the digest for a matcher constructed twice from the same tokens is equal (purity of
      `(spec, snapshot)`), and that adding one token changes it (drift signal preserved — the
      report's R2 concern is cost, not semantics).

**Verify:** full gate green; freeze scenario from A0 drops to < 5 ms repeat (recorded,
not gating) / unchanged first-call cost; `recognition_revision` value documented — if the
encoding changes, note the one-time revision bump in the PR body (pre-release, expected).

### Task A3 — Emit-signature validation once; drop per-call `inspect`

**Commit:** `perf(kernel): validate emit signature once per matcher; drop per-call inspect (ADR §13)`

Report R3: `_run_matchers_with_context` calls `inspect.signature(emit_fn)` per matcher per call
(~40 µs; 25% of steady-state pipeline on `"kg"`).

- [ ] Move the two-argument-signature validation to a one-time check: a module-level
      `_validated: set[int]` of `id(emit_fn)` is fragile (id reuse); instead validate in each
      matcher's `__post_init__` (matchers are frozen singletons) via a shared
      `_validate_emit(fn)` helper in `paxman/core/grammar/matchers/__init__.py` or a small
      `_emit_validation.py`. The engine loop then assumes a validated callable.
- [ ] Keep the engine loop's `callable(emit)` guard (cheap) and drop the `inspect.signature`
      branch entirely.
- [ ] `requires_features` match-time filtering stays (it is cheap: one `getattr` + `any` over a
      frozenset) — but document the deviation from §13's "omitted at freeze" in the ADR Rev.4
      changelog (Task A8): the registry freezes without a contract, so contract-dependent omission
      cannot happen at freeze; the compiled-set omission applies to
      snapshot/registry-static facts only. Hoist the `getattr(matcher, "requires_features", …)`
      to a tuple precomputed alongside `matchers` if profiling still shows it.
- [ ] RED: `tests/unit/test_kernel_coverage_boost.py` (extend) — a matcher whose `emit` takes 1 or
      3 params raises `TypeError` at **construction**, not at match time.
- [ ] Record steady-state `canonicalize("kg", si_unit)` before/after in the PR body (expect
      ~0.64 ms → ~0.45 ms; recorded evidence only, not gating — the A0 recognition-only
      scenarios carry the headline).

**Verify:** full gate green; no `inspect` import remains in `engine_loop.py`; steady-state number
recorded.

### Task A4 — Two-array offset maps; exact span-end translation (ADR D3 amendment)

**Commit:** `fix(kernel): two-array offset maps — span end is the source end of the last matched char`

Report R6a: the single-array D3 invariant `(offsets[s], offsets[e])` over-extends the translated
end whenever a normalizer drops source characters (CountryNameFold drops punctuation;
StripSeparators drops `" ().-"`; IDNAFold drops tabs) — `offsets[e]` is the sentinel "where
subject[e]'s source would begin," which absorbs the dropped tail.

Design:

- [ ] `Normalizer.normalize` returns `(subject, source_starts, source_ends)` where
      `source_starts[i]`/`source_ends[i]` bound the source interval of `subject[i]`;
      `len(starts) == len(ends) == len(subject)`; length-preserving normalizers return
      `(subject, None, None)` (identity, zero cost — unchanged).
- [ ] `View.original_span(s, e)` → `(starts[s], ends[e-1])` when mapped, `(s, e)` when `None`.
      Empty subject: `(0, 0)` sentinel.
- [ ] Update `ScanContext.view` invariants (the current assertions check the single-array shape —
      replace with starts/ends checks: `0 <= starts[i] < ends[i] <= len(text)`; starts
      non-decreasing).
- [ ] Update `NormalizerSequence` composition to thread both arrays (`ends` composes like
      `starts`; the composition code already handles the chained case).
- [ ] Update `CountryNameFold`, `StripSeparators`, `IDNAFold` to emit both arrays (they already
      track per-char source indices — the ends array is the +1 they currently fold into the
      sentinel).
- [ ] RED: `tests/property/test_view_parity.py` (extend) + new cases:
      `"United States."` name match span is `(0, 14)` **today** — after this task it becomes
      `(0, 13)` with `raw_text == "United States"` per locked A4b Option 1. Assert
      `raw_text == text[start:end]` for every emitted match (engine invariant net).
- [ ] ADR-0009 gains Rev.4 (Task A8) amending the D3 translation rule: *"A half-open view span
      `[s, e)` translates to `[starts[s], ends[e-1])` — the source interval of the last matched
      subject char, never absorbing dropped source characters."*

**A4b — behavior decision — LOCKED: Option 1 (word-boundary-aligned mentions).** Exact-end
translation changes the emitted span for matches ending at a dropped/merged source char.

1. **Word-boundary-aligned mentions (LOCKED).** Trie/lexicon matches on dropping views snap
   to exact source ends: `"United States."` → span `(0,13)`, value `"United States"`; scan
   mentions stop carrying trailing punctuation (`'United States of America,'` →
   `'United States of America'`). This is a small observable change to `canonicalize()` spans and
   `scan()` mentions for name-shape inputs with trailing punctuation — pre-0.2.0, regression-locked,
   migration-note entry added. Whole-input exact-name inputs keep identical canonical results (the
   rules normalize; only span/raw_text presentation shifts). Dissent, if any, is recorded in
   ADR Rev.4 — no further PR debate.
2. **Preserve current spans (REJECTED).** Would keep sentinel semantics for ends, two arrays
   used only internally. No user-visible change; `scan()` mention quality issue (report R6)
   would remain open. Rejected because `scan()` is the API this refactor exists to enable.

**Locked decision:** Option 1. Add the regression test, the `docs/user/migration.md` row, and
the ADR Rev.4 D3 amendment note in this task's commit. Regenerate **all** parity shards
atomically in the same commit — do not let B migrations diverge across old/new offsets.

**Verify:** full gate green; `raw_text == text[start:end]` property test still passes everywhere
(engine boundary check enforces it regardless); view-parity shard green; decision recorded.

### Task A5 — `CountryNameFold` single-pass NFD

**Commit:** `perf(core): CountryNameFold single-pass NFD (parity with legacy normalize_name cost)`

Report R5: per-char `unicodedata.normalize("NFD", ch)` is 3.7× slower than the legacy whole-string
`normalize_name` (3.95 ms vs 1.06 ms on 2.2 KB).

- [ ] Rewrite `normalize` to one `unicodedata.normalize("NFD", text)` pass, then a single
      iteration building chars + starts/ends (post-A4 shape), preserving exact output equivalence.
- [ ] RED: golden-vector test — for a curated corpus (accented names, CJK, punctuation runs,
      multi-space runs, mixed), `CountryNameFold().normalize(t)` equals the current
      implementation's output captured before the rewrite (snapshot the vectors in the test).
- [ ] Record the 2.2 KB timing in the PR body; target ≤ 1.5× legacy `normalize_name`.

**Verify:** full gate green; golden vectors green; timing recorded.

### Task A6 — Country matcher → `view="country_normalized"`; remove the legacy alias

**Commit:** `fix(country): use qualified view name; drop 'normalized' alias and runtime warning`

Report R8: the shipped Country matcher declares `view="normalized"`, and `_resolve_view` emits a
`DeprecationWarning` on **every** Country canonicalization (68 warnings in the suite).

- [ ] `paxman/capabilities/Country/grammar/name_recognition.py`: `view="country_normalized"`
      (already registered in `_VIEW_REGISTRY`).
- [ ] Remove the `"normalized"` entry + warning branch from `_VIEW_REGISTRY`/`_resolve_view`
      (kernel API is pre-0.2.0 core-internal; community grammars subclass `Grammar`, not the
      view registry — no public seam breaks).
- [ ] Sweep tests for `view="normalized"` usages and update.
- [ ] RED first: `pytest -W error::DeprecationWarning tests/` subset over country
      capability tests fails before the fix, passes after.
- [ ] Suite warning count 68 → ~0 (verify with
      `uv run pytest -q 2>&1 | tail -1`; remaining warnings, if any, must be pre-existing and
      unrelated — list them in the PR body).

**Verify:** full gate green; `uv run pytest -q` reports no `view='normalized'` warnings.

### Task A7 — Single recognition path: `PipelineGrammar` delegates to the engine loop

**Commit:** `refactor(kernel): PipelineGrammar.recognize delegates to engine loop; delete dead hand-rolled bodies`

Report R10: kernel grammars carry hand-rolled `recognize()` bodies the engine never calls
(`orchestrator.py:250-259` short-circuits on `matchers`), and `assert_kernel_parity` gates the
dead path. This is drift risk plus ~60 dead lines per migrated grammar.

- [ ] `PipelineGrammar` declares `matchers: ClassVar[tuple[Any, ...] | None] = None`; when a
      subclass sets it, `recognize()` returns `run_matchers(text, [self])` (import
      `paxman.core.grammar.engine_loop` — no cycle: engine_loop does not import pipeline).
      Otherwise the stage loop runs unchanged (33 legacy grammars untouched).
- [ ] Delete the hand-rolled bodies in Country `name_recognition`, SIUnit
      `symbol_recognition`, SIUnit `name_recognition` — the declaration (class attrs +
      `matchers = (...)`) becomes the entire grammar, per the ADR's "~15 lines of declaration"
      promise.
- [ ] `assert_kernel_parity` (`tests/property/grammar_kernel_parity.py`) — add a **gating**
      assertion: for all three migrated grammars, `g.recognize(text) == run_matchers(text, [g])`
      on a generated corpus; fails if delegation is reverted. This is the falsifiable gate that
      locks the single-path invariant.
- [ ] RED: mutate a kernel grammar's matcher (e.g. change a token) in a test and assert
      `recognize()` output changes — proves the delegation is live, not the old body. Also assert
      the previous comment-only check is now a real `pytest` failure.
- [ ] Confirm the orchestrator's `getattr(grammar, "matchers", None)` branch remains (community
      `Grammar` subclasses without `matchers` keep their own `recognize`).

**Verify:** full gate green; the three migrated grammar files shrink to declarations; parity
shards green.

### Task A8 — ADR-0009 → Accepted (Rev.4); de-reference plan docs from code; sync AGENTS.md

**Commit:** `docs(adr): ADR-0009 Accepted + Rev.4 (D3 amendment, deviations); code cites ADR sections only`

Report R11. The ADR is merged in substance but still "Proposed — Draft"; code comments cite plan
D-numbers (D5/D7/D8) and "plan Task 7/8/11" that exist only in a `docs/development/` document the
tree's own policy forbids code from referencing.

- [ ] ADR-0009: Status → **Accepted (2026-08-26)**, superseding ADR-0008 (already marked). Add
      changelog Rev.4 recording: (a) acceptance after the post-landing evaluation + this
      remediation; (b) the D3 amendment from Task A4; (c) the §13 clarification
      (contract-dependent omission happens at match time — freeze has no contract; emit-signature
      validation at construction); (d) the split-prefix deviation note (lexicon materialization
      interim, combinator per §9.4 is the target — resolved by Task B2); (e) suppressed-`scan()`
      promotion is gated on the suppression table landing (Task B1).
- [ ] Replace every plan-reference in `paxman/` source comments with ADR section references:
      `grep -rn "plan Task\|D5\b\|D7\b\|D8\b" paxman/` → the scanner/combinator/candidates/label/
      property docstrings and `discovery.py`/`engine_loop.py` comments. `D3`/`D4` refs that mean
      the ADR's own D-numbers stay; the plan's numbering goes.
- [ ] `paxman/core/AGENTS.md`: update the `grammar/` description to the kernel surface
      (`ScanContext`, `MatcherSpec`, `engine_loop`, `matchers/`, `anchors`, `boundary_spec`,
      `normalizers`) — ADR-0008 machinery (`stages`, `pipeline`, `composer`, `lexicon`,
      `boundary`) remains as the legacy path for unmigrated grammars. **Incremental:** a minimal
      sync of this file also lands in Task A0's commit so Part B workers do not read stale docs;
      Task A8 completes the sweep.
- [ ] Root `AGENTS.md` / `ARCHITECTURE.md` sweep for statements contradicted by the kernel (e.g.
      grammar strategy lists) — minimal edits, pointer to ADR-0009. List exact files/sections
      changed in the commit body.

**Verify:** `grep -rn "plan Task" paxman/` empty; `grep -rn "D5\\b\\|D7\\b\\|D8\\b" paxman/` empty
for plan-D numbers (ADR D1–D3 stay); `uv run import-linter lint` green; full gate green (docs-only
+ comments, but run it anyway). Incremental `core/AGENTS.md` sync already green since A0.

---

## Part B — P1 Value Delivery (collect what the migration cost paid for)

Order matters: B1 makes `scan()` usable; B2–B4 land the kinds **with their first customers**
(the ADR's own discipline — no kind ships without one); B5 deletes whatever still has none.

### Task B1 — Suppression table + `suppress_common_words` flag

**Commit:** `feat(core): common-word suppression for short-code matchers (ADR-0009 §16)`

Report R7: `scan()` on ordinary prose is ~80% lexical noise (`'to'`→Tonga, `'the'`→alpha3,
`'kg'`→Kyrgyzstan). The ADR's own answer (§16, libphonenumber's date-guard pattern) was deferred.

Design (corpus-neutral, provenance-neutral, off by default — per ADR §16):

- [ ] Data: `paxman/core/grammar/data/common_words.py` — a **curated, hand-auditable**
      `frozenset[str]` of high-frequency English function words that collide with short-code
      vocabularies (the/ton…: `to, in, at, by, of, is, it, as, on, or, if, an, be, we, he, so, no,
      do, up, us, me, my, am, go, ax, …` plus 3-letter `the, and, for, not, you, but, all, can,
      her, was, one, our, out, day, get, has, him, his, how, man, new, now, old, see, two, way,
      who, …`). **Source frozen:** intersection of the Google 1000 most-common English words
      (https://github.com/first20hours/google-10000-english) with the shipped short-code key sets
      (ISO 3166 alpha-2/alpha-3 for Country, ISO 4217 for Currency, ISO 639 for Language) —
      enumerated, reviewable, stable. Size frozen at generation time; add
      `assert len(COMMON_WORDS) == <frozen>` guard + `assert "USD" not in COMMON_WORDS`
      (USD must never be suppressed). **No authority claim**: suppression removes a
      *recognition*, it never canonicalizes; a suppressed span is simply not emitted
      (provenance-neutral by construction).
- [ ] Mechanism: `suppress_common_words: bool = False` field on `CapabilityContract` (default off
      — byte-identical behavior for every existing caller). The engine loop consults it when a
      matcher's grammar opts in via a `suppressible: bool` marker on short-code matchers (the
      kernel matchers for alpha2/alpha3/numeric/currency-code/language-code shapes — declaration,
      not per-grammar code).
- [ ] RED: regression test — with the flag on,
      `scan("Ship to the United States of America, total 45.50 USD, weight 3.5 kg", [country])`
      returns exactly the one name mention (and `'USD'` for currency — USD is not a common word);
      with the flag off, today's full mention set (locked as the current-behavior snapshot).
      `canonicalize("to", country)` with the flag **off** still returns `SUCCESS "TO"` (Tonga is
      correct for a bare code input); with the flag on returns `MISSING`.
- [ ] Docs: `docs/user/migration.md` + README scan recipe gain the flag; the CLI `paxman scan`
      keeps default contracts (flag off) but documents `--suppress-common-words` (thin contract
      construction at the CLI layer only — the API stays the seam).
- [ ] ADR-0009 Rev.4 note: §16's "deferred" is superseded — the table ships in 0.2.0, off by
      default.

**Verify:** full gate green; scan-noise regression test green both ways; docs updated.

### Task B2 — Combinator kind + SIUnit split-prefix (19,530 → 820 tokens)

**Commit:** `feat(kernel): combinator kind; SIUnit split-prefix as first customer (ADR §9.4)`

Report R4. The split-prefix shape belongs to the combinator (`alt(seq(prefix, unit))`), not to a
materialized product of 24 × 820 tokens that inflates the trie and every digest.

- [ ] Implement `CombinatorMatcher.match` (currently `NotImplementedError`): the minimal
      expression tree `seq/alt/opt/rep/label` evaluated left-to-right over a view with span
      capture; ordered choice documented as deterministic-first-branch-wins (ADR §9.4). Emit spans
      follow A4's exact-end translation. Scope is frozen to `seq/alt/opt/rep/label` — no new
      combinator forms in this task.
- [ ] SIUnit `symbol_recognition` becomes two matchers: the base `lexicon` (820 tokens) and a
      `combinator` for `"k g"`-style split prefixes (`seq(prefix_lexicon, ws, unit_lexicon)`),
      emitting the `split_symbol_prefix` shape. Delete the `_SPACED_SYMBOL_TOKENS` product.
- [ ] Parity: extend `tests/property/test_combinator_parity.py` — the legacy corpus (split
      `"k g"`, `"M Hz"`, adjacency cases) must be byte-identical: same spans, same shapes, same
      order. The F3-class benchmark input re-measured: trie over 820 tokens ≈ proportionally
      cheaper; freeze digest shrinks (Task A2 digest of 820 tokens vs 19,530).
- [ ] RED: the parity test against the current (materialized) grammar output captured as golden
      vectors before the swap.

**Verify:** full gate green; combinator parity shard green; token count assertion
(`len(_ALL_SYMBOL_TOKENS) == 820` in `paxman/capabilities/SIUnit/grammar/symbol_recognition.py`
class guard test added so the product cannot silently return); freeze + scan numbers re-recorded
in PR body (recorded, not gating).

### Task B3a — Scanner kind: Language BCP-47 migration (delete the fork)

**Commit:** `feat(kernel): scanner kind — Language BCP-47 subtag walk (ADR §9.3)`

Report R9 — flagship readability win: deleting `_BCP47RegexStage` and the ~160-line
`_bcp47_notation` callback is unclaimed.

- [ ] Rewrite the BCP-47 subtag walk as a `ScannerMatcher` (`scan: (view, pos) → (end, Notation)
      | None`) on the `SeparatorFold` view — the state machine (langtag,
      extlang/script/region/variant/extension/privateuse, grandfathered) becomes a typed,
      unit-testable function. Delete `_BCP47RegexStage` and `_bcp47_notation`'s regex-callback
      form. Parity: the full legacy BCP-47 corpus (valid/invalid tags, case variants, underscore
      inputs, grandfathered tags) byte-identical.
- [ ] RED: golden vectors captured from the pre-migration grammar first (byte-identical parity
      gate per ADR-0008 discipline; abort criterion = grammar stays legacy on divergence).

**Verify:** full gate green; `grep -n "_BCP47RegexStage" paxman/` empty; scanner parity shard
green; `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py` shrinks materially
(target: declaration + scanner function, no private stage class).

### Task B3b — Scanner kind: URL paren-balance migration

**Commit:** `feat(kernel): scanner kind — URL paren-balance + bare-scheme drop (ADR §9.3)`

- [ ] Paren-balance (including nested `a(b(c)d)e`) + bare-scheme drop moves from `PostStage`
      to the scanner; `IDNAFold` view rides the A4 offset maps. Legacy corpus parity.
- [ ] RED: golden vectors captured from the pre-migration grammar first.

**Verify:** full gate green; URL legacy corpus parity; scanner parity shard green.

### Task B3c — Scanner kind: Phone E.164 migration

**Commit:** `feat(kernel): scanner kind — Phone E.164 bounded window (ADR §9.3)`

- [ ] E.164 15-digit bounded window moves from the `PostStage` LRU trim to a
      separator-skipping scanner with `max_window` as data. Legacy corpus parity
      (span fixup `end = start + len(trimmed)` preserved exactly).
- [ ] RED: golden vectors captured from the pre-migration grammar first.

**Verify:** full gate green; Phone legacy corpus parity; scanner parity shard green.

### Task B4a — Candidates kind + Date 4→1

**Commit:** `feat(kernel): candidates kind — Date 4→1 (ADR §9.6)`

Report R9. `candidates` raises `NotImplementedError`; its first customer is Date's US/European
ambiguity.

- [ ] Implement `CandidatesMatcher.match` (ordered `alt` over child specs; `strategy="first"`
      wins per span, `"all"` keeps ambiguity observable — Date's US vs European reading of
      `01/02/2026` must stay `AMBIGUOUS`; per-candidate `target_semantics` routing preserved:
      iso8601 candidates coalesce, us/european stay distinct).
- [ ] Date: 4 grammar files → 1 with four candidates; every behavior (spans, semantics, gating)
      byte-identical per the legacy corpora (the four legacy grammars already live in
      `tests/property/_legacy_remaining_grammars.py` — the parity corpus is ready).
- [ ] RED: golden vectors captured from the pre-migration grammar first.

**Verify:** full gate green; Date capability has one recognition grammar file; candidates parity
shard green.

### Task B4b — Label kind + ISSN/IBAN

**Commit:** `feat(kernel): label kind — ISSN/IBAN glued policies (ADR §9.7)`

Report R9. `label` raises `NotImplementedError`; its first customers are ISSN/IBAN's glued
policies.

- [ ] Implement `LabelMatcher.match` (labels + separator + glued policy as data;
      `matches_prefix` utility already tested); migrate ISSN (`glued="allow"`,
      `[\s:-]*`) and IBAN (`glued="reject"`, `[\s:-]+`) as the two declared policies; BIC/ORCID
      follow in the same pattern if time allows, else they stay legacy (no deadline pressure —
      the kinds now have customers proving the shape).
- [ ] RED: golden vectors captured from the pre-migration grammar first.

**Verify:** full gate green; label glued-policy table unit-tested (the ADR §9.7 unification);
parity shard green.

### Task B5 — Stub-kind decision gate

**Commit:** `chore(kernel): property kind decision — populate or delete; no NotImplementedError stubs ship`

Report R9. After B2–B4 every kind has a customer **except possibly `property`** (implemented,
bisect-based, but `UNICODE_RANGES = ()` and no second customer per the ADR's own trigger).

- [ ] Decide with evidence: if a real consumer exists in the 0.2.0 set (e.g. SIUnit
      specials migrating off `SymbolFold`, Language `Script=Han` validation), populate the
      generator (`tools/regenerate_unicode_property_data.py` exists) from
      `shared_data/unicode_property_snapshot.json` and land the customer. Criterion: at least
      one shipped grammar must import `property` data and have a parity corpus — otherwise **delete**
      `PropertyMatcher`, the empty data module, and the generator until the second customer
      arrives (git history preserves them; the `MatcherKind` literal shrinks — an internal
      core enum, pre-0.2.0, no public seam).
- [ ] Whatever remains: `grep -rn "NotImplementedError" paxman/core/grammar/` is empty — every
      shipped kind is live with a customer or deleted. This is the ADR-0008 over-generalization
      risk permanently closed.

**Verify:** full gate green; no `NotImplementedError` in `paxman/core/grammar/`.

---

## Part C — P2 Verification Hardening

### Task C1 — Hypothesis corpora for the parity shards

**Commit:** `test(kernel): hypothesis-generated parity corpora (ADR-0009 Part V stratum 3)`

Report R12: shards are 3–25 hand-picked strings.

- [ ] Per migrated grammar (post Part B: Country name, SIUnit symbol/name, Language, URL, Phone
      E.164, Date, ISSN/IBAN labels): Hypothesis strategies generating (a) random text over an
      alphabet seeded from the grammar's token tables, (b) token sequences with random
      separators/padding/case, (c) adversarial mixes (boundary chars, dropped-char classes from
      A4). Assert kernel-vs-legacy byte parity + `raw_text == text[start:end]` for every match.
      Budgets: `max_examples=200`, `deadline=None`, `phases=[generate, target, shrink]`,
      `derandomize=False`; per-shard wall-clock cap in CI. Keep examples cached
      (`--hypothesis-seed` stable) and assert `tests/property` total < 90s on the CI runner
      (record in PR body; not gating, but tracked).
- [ ] Trie-vs-alternation byte-parity on generated corpora (both representations over the same
      token set must emit identical span sequences — keeps the ~500-token auto-selection honest).
- [ ] View offset round-trip property (A4): for every length-changing view,
      `original_span` is the exact inverse translation per the amended D3 rule.

**Verify:** `uv run pytest tests/property -q` green with the new corpora; CI wall-clock
`tests/property` < 90s (bounded Hypothesis profiles); cached examples green on re-run.

### Task C2 — Re-baseline, recognition-only family, docs sync

**Commit:** `chore(benchmarks): re-baseline post-remediation; docs sync (README, HOW_TO, migration)`

- [ ] `uv run python -m benchmarks.harness --update-baseline` on the remediated tree; commit with
      a note that pre-2026-08-26 baselines are incomparable (freeze-in-timing confound, report
      R2/R12).
- [ ] Confirm the recognition-only family (A0) and freeze scenario are part of the default run;
      record the remediation before/after summary in the PR body (from A0's captured pre-numbers):
      si_unit 2 KB recognition, freeze repeat cost, steady-state `canonicalize("kg")`, suite
      warning count.
- [ ] `HOW_TO_ADD_NEW_CAPABILITY.md` §4 chooser: point at the real kinds with their landed
      customers (post Part B); `README.md` grammar/capability table sync; root `AGENTS.md` /
      `CONTEXT.md` sweep for kernel-era drift.
- [ ] Final full gate + coverage ≥ 95%.

**Verify:** `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run
import-linter lint && uv run pytest` — all green.

---

## Execution Notes

- **Order is load-bearing:** A0 → A1 → A2 → A3 (measure, then the three hot-path fixes) → A4/A5
  (correctness + normalizer cost) → A6/A7/A8 (hygiene) → B1 before promoting anything scan-shaped
  → B2 → B3a → B3b → B3c → B4a → B4b → B5 → C1/C2. Part A alone removes every measured
  regression; Part B alone pays the ADR's investment thesis; each task is independently mergeable
  and parity-gated (B3/B4 splits ensure one-commit-per-task, linear history per plan header).
- **Every migration in Part B follows the ADR-0008 discipline inherited by ADR-0009:** golden
  vectors from the pre-migration grammar **first** (RED), byte-identical parity gate, abort
  criterion = "grammar stays legacy until the contract is extended — no silent divergence."
- **Deviation register:** the two intentional deviations this plan adds to ADR Rev.4 are (1) the
  D3 two-array amendment (A4) and (2) the §13 clarification that contract-dependent matcher
  omission happens at match time (A3). Everything else implements the ADR as written.
- **What this plan deliberately does not do:** no new capability work; no contract-surface
  redesign (`extra_recognizers` stays deferred per ADR §15); no streaming (§17 stays deferred);
  no benchmark hard-gating (stays informational per both ADRs).

## Risks

| Risk | Mitigation |
|---|---|
| Compiled boundary form subtly diverges from regex lookarounds | A1's exhaustive per-preset property parity over generated text; presets are frozen singletons, so a single test table covers all shipped use |
| Two-array offset change alters spans beyond the intended cases | A4 golden vectors across every dropping normalizer; `raw_text == text[start:end]` engine check is the net for every emitted match; A4b decision is explicit and regression-locked |
| Suppression table drifts toward an authority claim | Module header states the derivation rule (intersection with code sets) and the neutrality invariant (suppression never canonicalizes); flag default off |
| Combinator/scanner migrations break byte-parity | Golden vectors captured before each migration; abort criterion returns the grammar to legacy — no silent divergence |
| Hypothesis corpora slow CI | Bounded profiles; corpus size tracked in the task PR |
| Fixing the harness hides a real regression | A0 records pre-remediation numbers first; every perf claim in Parts A/B cites before/after from the same harness |
