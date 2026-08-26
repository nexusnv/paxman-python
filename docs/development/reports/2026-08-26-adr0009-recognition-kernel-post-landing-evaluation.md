# ADR-0009 Recognition Kernel — Post-Landing Independent Evaluation

**Date:** 2026-08-26
**Reviewed tree:** `main` @ `7ea4ba1` (15 capabilities, 36 grammars, pyproject 0.2.0 in tree, pre-release)
**Reviewer scope:** Independent evaluation of the direction taken by the ADR-0009 refactor of the
recognition layer and pipeline — is the architecture the right one for this project, or was a better
implementation missed? All claims below were verified against source or measured live on this tree;
reproduction snippets in the Appendix.
**Nature:** Post-landing review. Praise and criticism are both earned by evidence in the repo. One
finding from the review's own first draft was retracted after verification (R6 — see the correction
note); it is recorded here so the same mistake is not repeated.
**Inputs:** `docs/adr/0009-recognition-kernel.md` (Rev.3), `docs/adr/0008-staged-recognition-pipeline.md`
(Obsolete), the landed kernel (`paxman/core/grammar/{scan_context,engine_loop,matcher_spec,anchors,
boundary_spec,normalizers}.py`, `paxman/core/grammar/matchers/*`), the three migrated grammars
(Country `name_recognition`, SIUnit `symbol_recognition`, SIUnit `name_recognition`), the parity
shards (`tests/property/{grammar_kernel_parity,test_lexicon_parity,test_scanner_parity,
test_view_parity,test_combinator_parity}.py`), `paxman/api/scan.py`, `paxman/engine/orchestrator.py`,
`paxman/core/discovery.py`, `benchmarks/{harness,scenarios}.py` + `baseline.json`, and the CLI.

---

## 1. Executive Summary

**Verdict: the architectural direction is correct and worth keeping; the landed first slice has
quantified execution defects that currently make the kernel slower and less complete than the ADR
promises — all fixable inside the kernel's own design. No fundamentally better architecture was
missed, but two implementation designs were.**

- The ADR's **diagnosis** was right: F1 (`"Ship to United States please"` → silent `SUCCESS "TO"`)
  was reproduced as structural, and F2/F4/F5 (per-grammar rescan, the `_BCP47RegexStage` private
  fork, boundary lookarounds) are all real in the tree.
- The ADR's **central measurement** (trie beats alternation at lexicon scale) is validated at the
  matcher level: an isolated word-anchored trie over 19,530 tokens scans 2.2 KB in **2.5 ms** vs
  **10.4 ms** for the legacy 844-token alternation.
- The **F1 fix is genuinely honest**: prose now raises `MultipleMentionsError`, and `paxman.scan()`
  returns both mentions with spans. The breaking-change discipline (0.2.0 banner, migration table,
  `recognition_revision` signal) is exemplary.
- But the **production kernel path is currently slower than what it replaced**, and the shipped
  benchmark now measures the wrong thing: the si_unit scenario's p50 went from **124.8 µs to
  61.4 ms (~490×)** because `freeze_registry()` re-hashes a 19,530-token lexicon (~40 ms) whenever
  the registry resets, and the boundary checker does an O(n) string slice plus a module-cached
  regex search per candidate hit (~89% of trie scan time).
- Only **3 of 36 grammars** are on the kernel path; `combinator`/`candidates`/`label` raise
  `NotImplementedError`, `property` has empty generated data, and the flagship readability win
  (deleting `_BCP47RegexStage`) has not happened.
- **Recommendation: finish, don't revert.** Every defect is fixable within the kernel's design,
  mostly by implementing what the ADR already specifies (§10 hit-position checks, §13 freeze-time
  compilation) or by deleting what should not have shipped yet (stub kinds, plan-reference
  comments). A remediation plan accompanies this report:
  `docs/development/plans/2026-08-26-adr0009-kernel-remediation.md`.

---

## 2. What Holds Up (validated)

| Claim | Verdict | Evidence |
|---|---|---|
| F1 was a real, structural correctness defect | **Confirmed** | Pre-kernel: only recognition on `"Ship to United States please"` was `alpha2 'to' → TO` (Tonga) — a confident, provenance-backed, wrong `SUCCESS`. Now: `MultipleMentionsError(['TO','US'])` + two `scan()` mentions. |
| Word-anchored trie beats alternation at scale | **Confirmed at matcher level** | Isolated, 2.2 KB prose: trie (19,530 tokens) **2.46 ms** / alternation (844 tokens) **10.4 ms** — and the trie's cost is independent of token count. The ADR's F3 ratios hold. |
| F1 fix + `scan()` is honest and well-gated | **Confirmed** | `scan()` returns `Mention(span=(5,7), grammar='alpha2_recognition', …)` and `Mention(span=(8,21), grammar='name_recognition', …)`; `docs/user/migration.md` carries the old→new table. |
| Rejected alternatives (DAG/parallel, external engines, ML/NER, fuzzy, checksum-fused) | **Agree with all** | Each rejection is grounded in a project invariant (GIL + total order; zero-dep; determinism/provenance; `MISSING` vs `INVALID`). Re-litigating them would need a new invariant, not a new argument. |
| Layering survived the migration | **Confirmed** | `paxman.core.grammar` imports nothing from capabilities; import-linter green; 3,360 tests pass at 95% coverage. |
| ADR-0008's durable wins were inherited, not discarded | **Confirmed** | Parity harness, declarative grammar surface, core-agnostic layering all present and extended. |

---

## 3. Findings

Severity: **P0** = regression or correctness/UX defect in shipped code; **P1** = undelivered value
the ADR's cost was paid for; **P2** = process/verification gap.

### R1 (P0) — Boundary checks are O(text) per candidate hit, not O(1) at hit positions

`check_boundary` (`paxman/core/grammar/boundary_spec.py:36`) does `prefix = subject[:start]` (an
O(n) slice copy) and `re.search(pat + r"\Z", prefix)` per candidate hit — the exact anti-pattern
ADR §10 forbids ("checks at hit positions … never as lookarounds evaluated at scan positions").
The spec's `left`/`right` fields store **regex strings**, so membership cannot be a frozenset test.

Measured (2.2 KB prose, 19,530-token SIUnit symbol lexicon, 100 iterations):

| Configuration | Scan time | Emitted spans |
|---|---|---|
| trie, no boundary | 2.46 ms | 224 candidates |
| trie, `DEGREE_WORD_SIGN` boundary (production) | 23.11 ms | 16 |

The boundary check is ~89% of production scan time. Net effect at the grammar level: SIUnit
`symbol_recognition` runs **19.7 ms** on 2.2 KB vs the legacy alternation grammar's **~6.6 ms**
(ADR F3 measurement) — the kernel migration made the largest lexicon scan **~3× slower**, inverting
the ADR's projected ~4× *improvement*. On the 68-char benchmark-class input, all-grammar
recognition is 1.39 ms (vs the ADR's 1.30 ms pre-kernel) — parity at best.

**Root cause:** the check inspects the immediately adjacent characters but pays for a full-prefix
slice + regex dispatch to do it. The substrate already computes `word_spans` once per call and the
checker never uses it.

### R2 (P0) — `recognition_revision` re-hashes the lexicon at every freeze (~40 ms)

`freeze_registry()` (`paxman/core/discovery.py:63`) rebuilds the revision by sorting and joining
every matcher's token set and hashing it — every time the registry freezes. Measured:

- SIUnit-only freeze: **49.7 ms** (dominated by sorting/joining/hashing 19,530 tokens: ~40 ms per
  hash; snapshot-file hashing is negligible at 0.8 ms).
- Full 15-capability freeze: **75.8 ms** — paid once per process, on the first `canonicalize()`.

Because `benchmarks/harness.py` calls `reset_registry()` inside its timing loop, the si_unit
scenario's p50 went from the committed baseline's **124.8 µs** to **61.4 ms (~490×)** — the
informational benchmark now measures freeze cost, not scan cost. The baseline signal is corrupted.

### R3 (P0) — Per-call `inspect.signature()` and match-time feature filtering in the engine loop

`_run_matchers_with_context` (`paxman/core/grammar/engine_loop.py:104-113`) validates the emit
callable's signature with `inspect.signature()` **per matcher per call** (~40 µs each; 25% of
steady-state whole-pipeline time on the 2-char input `"kg"`), and filters `requires_features` per
call (the "compat shim") instead of compiling per §13. Steady-state
`canonicalize("kg", si_unit_contract)` is ~0.64 ms vs the 124.8 µs baseline p50 (~5×), of which
`inspect.signature` is a quarter.

### R4 (P0) — SIUnit split-prefix is materialized into the lexicon (19,530 tokens), not composed

ADR §9.4 specifies split-prefix as `alt(seq(prefix, unit))` via the combinator. The landed
implementation instead builds `f"{p} {s}"` for 24 prefixes × 820 symbols and unions it into the
lexicon (`symbol_recognition.py:34-37`) → 19,530 tokens. This inflates the trie, the freeze digest
(R2), and the benchmark pathology, and leaves the combinator kind with zero customers.

### R5 (P0) — `CountryNameFold` is 3.7× slower than the `normalize_name` it replaced

`normalizers.py:123-169` calls `unicodedata.normalize("NFD", ch)` **per character** plus
per-char category filters. Measured on 2.2 KB: **3.95 ms** vs legacy whole-string
`normalize_name` **1.06 ms**. A single whole-string NFD pass removes the gap.

### R6 (P1, corrected) — Mention spans/values include trailing punctuation; pre-existing, now exposed at scale

**Correction:** the review's first draft called this a kernel regression ("old path emitted trimmed
spans"). That was wrong — verified against the legacy grammar: `LegacyNameGrammar().recognize(
"United States.")` → `(0, 14, 'United States.', 'United States.')`. The old whole-input semantics
**also** included trailing punctuation in span and value; the kernel preserves it byte-identically.

What *is* new: `scan()` exposes this pre-existing quisk at scale as an extraction API —
`scan("Ship to the United States of America, total 45.50 USD, weight 3.5 kg")` returns the country
name mention as `value='United States of America,'` (trailing comma inside the mention). For
whole-input `canonicalize()` this is harmless (rules normalize); for `scan()` mentions it is a
legitimate span-quality question that the F1 parity exemption meant nobody had to answer. The
two-array offset fix (see R6a below) makes word-boundary-aligned mention spans *possible*; whether
to change the observable semantics is a decision, not a bug fix.

**R6a (root cause, technical):** `View.original_span` implements the ADR D3 single-array invariant
`(offsets[s], offsets[e])`, where `offsets[e]` is the sentinel "where the source of subject[e]
would begin." When a normalizer *drops* source characters (CountryNameFold drops punctuation;
StripSeparators drops `" ().-"`; IDNAFold drops tabs), the sentinel attributes the dropped tail to
the preceding subject char, over-extending the translated span end. The invariant is lossy by
construction for dropping normalizers; a two-array (source-start, source-end) model is needed for
exact end translation. This is a genuine ADR spec defect, not just an implementation bug.

### R7 (P1) — `scan()` output on prose is noise-dominated; the suppression table was deferred

On the one-entity sentence above, `paxman scan` reports **9 country mentions** (`'to'`→Tonga,
`'the'`→alpha3, `'45'/'50'/'3'/'5'`→numeric codes, `'kg'`→Kyrgyzstan, …), **2 currency mentions**
(`'the'`, `'USD'`), and ≥1 language mention (`'to'`). The ADR's own answer to this class
(§16 suppression data, the libphonenumber date-guard pattern) was demoted to "deferred and
non-binding" — so the F1 breaking-change cost landed while its constructive payoff (a usable
extraction API) did not. Roughly 80% of mentions on ordinary prose are lexical noise.

### R8 (P0) — Production path emits a `DeprecationWarning` on every Country canonicalization

Country's shipped matcher declares `view="normalized"`; `_resolve_view` warns
("view='normalized' is ambiguous") each call. 68 warnings in the full test suite. The qualified
name `country_normalized` already exists in `_VIEW_REGISTRY` — the shipped grammar just doesn't
use it.

### R9 (P1) — Most of the spine is scaffolding; the flagship wins have not happened

- Kernel path adoption: **3 of 36 grammars** (all `lexicon` kind): Country name, SIUnit symbol,
  SIUnit name.
- `combinator`, `candidates`, `label` raise `NotImplementedError` in production core.
- `property` is implemented but its generated data is empty (`UNICODE_RANGES = ()`).
- `_BCP47RegexStage` and the ~160-line `_bcp47_notation` callback still exist
  (`Language/grammar/bcp47_tag_recognition.py`, 276 lines) — the ADR's flagship readability win
  ("deleting the fork") is unclaimed.
- URL paren-balance and Phone E.164 still live in `PostStage` transforms.

This is exactly the over-generalization risk ADR-0008's Risk section warned about, inverted:
machinery shipped ahead of customers.

### R10 (P0) — Two recognition paths per kernel grammar; the parity gate gates the dead one

Kernel-migrated grammars carry hand-rolled `recognize()` bodies that the engine **never calls**
(`orchestrator.py:250-259` short-circuits to `run_matchers_with_context` when `matchers` is
truthy). `assert_kernel_parity` compares `old.recognize()` vs `new.recognize()` — i.e. it gates
the hand-rolled body, not the kernel loop production actually executes. The two paths currently
agree (the hand-rolled body replicates the kernel), but nothing would catch future divergence of
the engine loop. The migrated grammars are also ~60 lines of dead duplicate logic each.

### R11 (P0) — Governance drift: ADR status and code references

- ADR-0009's status is still **"Proposed — Draft"** while its implementation is merged to `main`
  and ADR-0008 is marked Obsolete against it.
- Production code comments cite `D5`, `D7`, `D8` and "plan Task 7/8/11"
  (`matchers/{scanner,candidates,combinator,label,property}.py`, `discovery.py`, `engine_loop.py`).
  The ADR defines **D1–D3 only**; those numbers come from the implementation plan. This violates
  `docs/development/AGENTS.md` ("code … must NOT reference these documents — neither by filename
  nor by quoting or paraphrasing any part of their contents").
- `paxman/core/AGENTS.md` still describes `grammar/` as the ADR-0008 surface
  (BoundaryGuard/stages/composer) with no mention of the kernel modules.

### R12 (P2) — Verification gaps

- Parity shards are 3–25 hand-picked strings each; the ADR's Part V stratum 3 (Hypothesis-generated
  substrate-equivalence and `raw_text == text[start:end]` corpora) is not realized for the kernel.
- The benchmark harness conflates freeze cost with scan cost (see R2) and has no recognition-only
  scenario family (ADR Part IV promised 64 B / 2 KB / 16 KB scenarios).
- The committed `baseline.json` is no longer comparable to current-tree numbers.

---

## 4. Was a Better Implementation Missed?

**At the architecture level: no.** Substrate + declarative matcher kinds + centralized assembly is
the right spine for a provenance-first, zero-dependency, determinism-by-construction library with a
30-capability roadmap. The external precedents the ADR borrows from (Lucene's offset-correctness
rule, HF tokenizers' offset maps, libphonenumber's bounds and advance discipline, Hyperscan's
prefilter decomposition) are used for the right lessons, and the rejected-dependency discipline is
correct for this project. Two independent design reviews converging on the same shape, plus the
measured validation above, make this the highest-confidence part of the whole exercise.

**At the implementation level: yes, two things:**

1. **The substrate's own data is unused where it matters most.** `ScanContext.word_spans` is
   computed once per call, yet the boundary checker — the single hottest operation in the new
   pipeline — re-derives adjacency from string slices and regex dispatch instead of testing
   membership against precompiled character sets and word-span alignment. This one miss is R1,
   and it inverts the performance story of the entire migration.
2. **Value-first sequencing.** The delivered user value (F1 fix + `scan()`) did not require the
   full spine — an in-text trie plus mention clustering (~300 LOC) on top of ADR-0008 would have
   shipped it. The spine's remaining value (scanner/combinator/candidates/label) is entirely
   unrealized (R9). The project paid the migration cost ahead of the benefit; the benefit must now
   be collected, or the unreached parts deleted.

**Alternatives re-checked and still rejected:** reverting to ADR-0008's pipeline (reintroduces F1's
honesty problem and the fork/class of workarounds); adopting `regex`/`pyahocorasick`/Rust regex
(violates zero-dep; leftmost-winner collapses observable ambiguity); keeping the alternation for
SIUnit (measured slower at the matcher level once boundary checks are O(1)).

---

## 5. Recommendations

**P0 — fix the regressions inside the kernel's design (no architecture change):**
1. Compile `BoundarySpec` char classes to frozensets at construction; check the immediately
   adjacent character(s) with membership tests; use word-span alignment for the trie; bounded
   windows only for genuinely multi-char patterns (`ISBN10_LEAD`). (R1)
2. Memoize per-matcher digests (compute once per process); `freeze_registry` concatenates
   precomputed digests. Fix the harness to freeze outside the timed region and add a separately
   reported freeze-cost scenario. (R2, R12)
3. Validate emit signatures once per matcher (construction/freeze), not per call; keep the cheap
   match-time `requires_features` filter and document the deviation from §13's "at freeze"
   (freeze cannot know the contract). (R3)
4. Land the combinator for SIUnit split-prefix; shrink the lexicon from 19,530 tokens back to ~820.
   (R4)
5. Single-pass NFD in `CountryNameFold`. (R5)
6. Two-array offset maps (`source_starts`/`source_ends`); `original_span` end = `ends[e-1]`;
   amend ADR D3. Then decide — as a separate, regression-locked behavior change — whether in-text
   mention spans snap to word boundaries for `scan()`. (R6, R6a)
7. Country matcher → `view="country_normalized"`; drop the legacy alias and its warning. (R8)
8. Make `PipelineGrammar.recognize()` delegate to the engine loop when `matchers` is declared;
   delete the dead hand-rolled bodies; the parity gate then gates the production path. (R10)
9. ADR-0009 → Accepted with a Rev.4 changelog (D3 amendment, deviations, reference policy);
   replace plan-D/plan-Task references in code with ADR § references; sync `core/AGENTS.md`. (R11)

**P1 — collect the value the cost was paid for:**
10. Ship the suppression table (§16) before promoting `scan()` — the table is small and auditable
    (the intersection of a curated common-English-word list with the ISO 3166/4217/639 code sets),
    off by default, provenance-neutral. (R7)
11. Land the migrations that justify the spine: scanner (BCP-47 — delete the fork; URL paren
    balance; Phone E.164), combinator (SIUnit split-prefix), candidates (Date 4→1), label (ISSN
    `glued=allow`, IBAN `glued=reject`). (R9, R4)
12. Decision gate: any kind still without a customer after those migrations (property is the
    candidate) gets deleted or populated — no `NotImplementedError` stubs ship in 0.2.0. (R9)

**P2 — close the gate gaps:**
13. Hypothesis-generated corpora for the parity shards; kernel-loop parity in CI (automatic once
    item 8 lands). (R12)
14. Recognition-only benchmark scenarios (64 B / 2 KB / 16 KB); re-baseline with a note that
    pre-remediation numbers are incomparable. (R12)

---

## 6. Bottom Line

ADR-0009 made the right call on the three questions that matter: replace per-grammar scanning with
a shared substrate, make matching declarative data, keep assembly and authority in the engine. The
diagnosis was honest, the external evidence was measured rather than asserted, and the rejected
alternatives were rejected for durable reasons. I would make the same architecture decision again.

What I would not repeat is merging the foundation, a breaking behavior change, and a new public API
while the spine's payoff is unrealized and its hot paths are unmeasured — the project paid the
migration cost and is temporarily running slower and noisier than the pipeline it superseded. The
gap is execution, not direction: every defect above is fixable inside the kernel's own design,
mostly by implementing what the ADR already specifies. Finish the kernel; do not revert it.

---

## Appendix — Reproduction Snippets

All run with `uv run python` on `main` @ `7ea4ba1`, CPython 3.13, this machine, 2026-08-26.
Numbers are indicative of magnitude; re-measure before/after remediation with
`benchmarks/harness.py` (post-fix) plus the snippets below.

```python
# F1 honesty (fixed):
#   paxman.canonicalize("Ship to United States please", CountryContract())
#   -> MultipleMentionsError(['TO', 'US'])
#   paxman.api.scan(...) -> mentions at spans (5,7) alpha2 and (8,21) name

# R1 boundary dominance (2.2 KB prose, 19,530-token lexicon, 100 iters):
#   LexiconMatcher(..., boundary=None)                -> 2.46 ms, 224 candidate spans
#   LexiconMatcher(..., boundary=DEGREE_WORD_SIGN)    -> 23.11 ms, 16 emitted spans
#   grammar-level kernel path                         -> ~19.7 ms (vs legacy alternation ~6.6 ms)

# R2 freeze cost:
#   SIUnit-only freeze_registry() ~49.7 ms; full 15-cap ~75.8 ms
#   sha256("|".join(sorted(tokens))) of 19,530 tokens ~40 ms per call
#   benchmarks/harness.py si_unit p50: baseline 124.8 µs -> current 61.4 ms

# R3 per-call overhead:
#   cProfile over 50x canonicalize("kg", si_unit): inspect.signature = 25% of cumulative

# R5 normalizer:
#   CountryNameFold().normalize(2.2KB) 3.95 ms vs normalize_name(2.2KB) 1.06 ms

# R6 (correction evidence):
#   LegacyNameGrammar().recognize("United States.")
#   -> [(0, 14, 'United States.', 'United States.')]   # old path ALSO kept the period

# R7 scan noise:
#   paxman scan "Ship to the United States of America, total 45.50 USD, weight 3.5 kg"
#   -> 9 country mentions + 2 currency mentions + language 'to'

# R8 warning: canonicalize("Germany", CountryContract()) emits DeprecationWarning
#   ("view='normalized' is ambiguous") — 68 occurrences across the test suite
```
