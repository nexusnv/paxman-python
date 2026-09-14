# Slice G — Combinator Leaf Backtracking (#73 L3)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Make combinator `seq` explore every leaf alternative end at a start position (backtracking) instead of only the longest, so overlapping-leaf sequences (e.g. `seq(lex{a,ab}, regex b)` on `"ab"`) succeed — closing the last live item of #73 with SIUnit golden vectors byte-identical.

**Architecture:** Change `leaf_maps` values from max-end to sorted end-lists and thread multi-end branching through `_eval_expr`'s `seq` case (bounded: `seq` is ≤3 leaves per ADR §9.4, leaf spans finite); `alt`/`opt`/`rep`/`label` keep first-hit semantics via a wrapper so only `seq` gains branches. Single-file kernel change + unit tests. No contract/engine/grammar-shape changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/property), `paxman/core/grammar/matchers/combinator.py`.

**References:** Issue #73 (L3); `paxman/core/grammar/matchers/combinator.py:24-57` (`_collect_leaves`), `:60-170` (`_eval_expr`: `seq` `:74-84`, leaf lookup `:141-144`), `:211-244` (`match`: `leaf_maps` max-only build `:240-246`); `tests/property/test_combinator_red_golden.py:17-63` (SIUnit split-prefix goldens incl. `("m s",[])` + `("k g",[(0,3)])` — must stay byte-identical); ADR-0009 §9.4 (`seq` ≤3 leaves bound).

**Branch:** `feature/slice-g-combinator-backtracking` (cut from `dev` — already exists).

---

## File Structure

- Modify: `paxman/core/grammar/matchers/combinator.py` — `leaf_maps` to `dict[int, dict[int, list[int]]]`, branching in `seq` evaluation (bounded backtracking).
- Test: `tests/unit/test_combinator_backtracking.py` (create) — L3 acceptance vectors + bound guards.
- Regression: `tests/property/test_combinator_red_golden.py`, SIUnit capability/property suites, full gate.
- Docs: `CHANGELOG.md`.
- No grammar/rule/contract/engine changes; no new matcher kinds.

---

## Background the implementer needs

### Current state (verbatim)

`match()` builds `leaf_maps: dict[int, dict[int, int]]` (`:238-244`): `if s not in mp or e > mp[s]: mp[s] = e` keeps only the longest end per start. Leaf lookup in `_eval_expr` (`:148-153`) does `mp.get(pos)` — a single end. `seq` (`:78-88`) chains single ends with no fallback. Live repro (Sep 2026): `LexiconMatcher({'a','ab'})` on `"ab"` → `[(0,2)]`, so `seq(leaf, Regex('b'))` → `[]` although `(0,1)`+`b` is a valid parse. Latent today because SIUnit split-prefix leaves (`PREFIX_ONLY` + `SYMBOL_TOKENS`) are disjoint — but any overlapping-leaf `seq` silently fails.

### Design decisions (locked)

1. **End-lists, longest-first, `seq` enumerates combinations.** `leaf_maps` becomes `dict[int, dict[int, list[int]]]` (deduped, longest-first). `seq` enumerates every child-end combination level by level (depth-first over longest-first ends) and returns ends longest-first; `alt`/`opt`/`label` propagate all ends inward (`opt` also offers skip-`pos`), `rep` and top-level `match()` keep longest-first single-end. Top-level takes the longest end (greedy, consistent with `LexiconMatcher longest_first`).
2. **Blowup bound is structural, documented in code.** Branching factor = leaf ends at a position (finite: leaf span lists), depth = `seq` arity (≤3 per ADR §9.4); add a hard cap (e.g. total `seq` evaluations per start position, mirroring the existing `rep` 10000-iteration guard style) that degrades to no-match, never raises, never loops.
3. **SIUnit goldens are the no-regression oracle.** `("m s",[])`, `("k g",[(0,3)])`, and the full GOLDEN table must be byte-identical before/after; any golden delta = wrong fix, stop and re-think (dual-role `m s` must NOT start matching).
4. **#73 closes on L3.** L1/L2/`nfd_pos` landed Slice A; `View.offsets` + `check_boundary_compiled` intentionally kept (documented invariant). #150 stays out (needs ruling), #71 stays out (design-gated + parity-blocked), #154 stays out (monitor-only), #146 release-time.

### Deferral → issue map

| Deferred matter | Home issue |
|---|---|
| Money single-separator heuristic | #150 (needs ruling) |
| Orchestrator/view tightenings | #71 (design-gated) |
| Flake | #154 (monitor-only) |
| Tracker bookkeeping | #146 (release-time) |

---

### Task 1: L3 backtracking — failing test + fix

**Files:** `tests/unit/test_combinator_backtracking.py` (create), `paxman/core/grammar/matchers/combinator.py:60-170,211-244`

**Goal:** `seq(lex{a,ab}, regex b)` on `"ab"` → `[(0,2)]`; `seq(lex{a,ab}, regex c)` on `"ab"` → `[]`; overlapping-alternative explosion stays bounded.

- [ ] Failing tests first: `test_seq_uses_shorter_leaf_alternative` (`seq` on `"ab"` → `[(0,2)]`, FAILS today as `[]`); `test_seq_all_alternatives_miss` (`regex c` variant → `[]`, green already, pinned); `test_seq_backtracking_bounded` (crafted many-alternative leaf × 3-seq completes fast — green, pinned as guard). Run: `uv run pytest tests/unit/test_combinator_backtracking.py -q` → RED on the first.
- [ ] Implement: end-list `leaf_maps` + `seq` depth-first branching with evaluation cap. Verify: targeted → PASS; `uv run pytest tests/property/test_combinator_red_golden.py tests/capabilities/si_unit -q` → PASS byte-identical goldens; `uv run pytest -m property -q -k "combinator or si_unit"` → PASS; ruff/pyright clean.

### Task 2: Integrate + gate + close-out

**Files:** `CHANGELOG.md`

- [ ] CHANGELOG Unreleased/Fixed: #73 L3 backtracking (+ #73 closure note: L1/L2/`nfd_pos` Slice A, keeps intentional). Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest` → green; coverage ≥95. Close-out comment: #73 (L3 evidence + full-item ledger — closable). Commit per task.
