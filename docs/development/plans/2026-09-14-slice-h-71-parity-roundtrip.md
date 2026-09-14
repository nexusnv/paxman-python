# Slice H — #71 Closeout: Parity Fix + Roundtrip/HealthCheck Tightening

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Close #71 fully: fix the `zh-min-nan` scanner parity mismatch blocking items 3–4, then tighten the view round-trip asserts (item 3) and narrow the HealthCheck suppression (item 4) with 10 consecutive green property runs. Items 1–2 already landed (verified in-tree); item 5 stays INVALID by triage.

**Architecture:** Grammar-correctness fix first (BCP47 scanner vs legacy snapshot on variant subtags — behavior converges, no new semantics), then test-only tightening (exact-inverse asserts, narrowed suppression). No contract/engine/rule changes; orchestrator items 1–2 need no code (per-grammar `keep_duplicate_spans_for` + span-keyed flat pairing already shipped).

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (`-m property`, hypothesis "ci" profile: `max_examples=100`), `paxman/core/grammar` scanner + `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py`.

**References:** Issue #71 (items 3–4 + acceptance); `tests/property/test_hypothesis_parity_corpora.py:75,410` (suppression + `test_language_bcp47_hypothesis_parity`); `tests/property/test_hypothesis_view_roundtrip.py:28,65-68,167-180` (suppression + permissive asserts); `tests/property/test_hypothesis_trie_parity.py:35`; `tests/property/_legacy_language_grammars.py:16` (legacy prefix-matches `zh-min` inside `zh-min-nan00`); `tests/property/test_bcp47_scanner_parity.py:84-86,107-121` (corpus + longest-valid-prefix pin); `paxman/engine/orchestrator.py:782-827` (`_keep_duplicate_span_grammars`, item 1 landed via `9ec0080`); `:400-412` (span-keyed flat pairing, item 2 landed).

**Branch:** `feature/slice-h-71-orchestrator-parity` (cut from `dev` — already exists).

---

## File Structure

- Modify (TBD by repro, likely): `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py` — variant-subtag parity fix (grammar correctness, converges to legacy).
- Test: `tests/property/test_bcp47_scanner_parity.py` — deterministic minimal repro pin(s).
- Modify: `tests/property/test_hypothesis_view_roundtrip.py:65-68,167-180` — exact-inverse asserts (item 3).
- Modify: `test_hypothesis_parity_corpora.py:75`, `test_hypothesis_view_roundtrip.py:28`, `test_hypothesis_trie_parity.py:35` — narrow suppression to `[too_slow, data_too_large]` (item 4).
- Docs: `CHANGELOG.md`.
- Verify-only: items 1–2 landed code, item 5 INVALID standing.
- No contract/engine/rule-behavior changes beyond the parity convergence.

---

## Background the implementer needs

### Current state (verbatim)

Items 1–2 are in-tree. `_keep_duplicate_span_grammars` (`orchestrator.py:782-800`, landed `9ec0080` "fix(engine): per-grammar keep_duplicate_spans scoping (#71, ADR-0012)") scopes dedup-skip per grammar + candidate names; `_dedup_candidates` (`:808-831`) keeps the legacy capability-wide path only when the frozenset is `None`. Flat pairing is span-keyed via deque (`:400-412`, comment cites future IBAN/ISBN), and ordering uses one key space `(start, end, grammar_index, name)` (`:426`). Date `01/02/2026` parity unchanged (full suite green).

The blocker is the parity mismatch behind item 4: under narrowed suppression, `test_language_bcp47_hypothesis_parity` flakes 10%→40% on `zh-min-nan00` / `zh-min-nanA` variant mismatch (legacy snapshot 6 vs scanner 12 on hypothesis-composited texts). Bare/direct probes agree today (`zh-min-nan00` → 1v1 `(0,12)`; `zh-min-nanA` → 1v1; corpus `test_bcp47_scanner_parity_byte_identical` green incl. the #90 longest-valid-prefix pin `:107-121`), and the legacy helper documents prefix-matching `zh-min` inside `zh-min-nan00` (`_legacy_language_grammars.py:16`) — so the divergence needs hypothesis-shaped context (case variants, separators, neighbors) to surface, and the fix must preserve the #90 pin (grandfathered exact-only + longest-valid-prefix-wins).

Round-trip permissiveness (item 3) lives in the per-character loop at :167-180: `country_normalized` accepts `subj_ch in stripped or stripped.strip()` and `compact` accepts mismatched chars. (Boundary-span exactness is already pinned at :65-73 via `assert sub_view.subject == subject[s:e]`; the task extends exactness into the per-char branches.)

### Design decisions (locked)

1. **Parity fix converges scanner → legacy, never the reverse.** The legacy snapshot is the pinned past behavior plus the #90 honest-behavior pin; any fix that changes `test_bcp47_grandfathered_prefix_longest_valid_prefix_wins` outcomes is wrong — stop and re-think. Repro first: hunt the minimal failing text with narrowed suppression (seed loop), pin it deterministically in `test_bcp47_scanner_parity.py`, then fix.
2. **Tightening is exact-inverse per the issue, no weaker.** `country_normalized`: `subj_ch == stripped` precisely (plus the documented space-folding); `compact`: `subj_ch != src` mismatch allowance removed (only separator-drop mapping remains, asserted exactly); `idna`: assert the recomputed `sub_view.subject` equals the slice (replacing the bare `continue`). Corpus tuning allowed (strategy tweaks, never weakening asserts); `filter_too_much` stays enabled throughout.
3. **Narrowing is all three files at once + 10× proof.** `suppress_health_check=[too_slow, data_too_large]` in parity_corpora, view_roundtrip, trie_parity; then 10 consecutive `uv run pytest -m property -q` green, logged. Any flake → fix cause (tune corpus/strategy), never re-broaden suppression to greenwash.
4. **#71 closes on items 3–4.** Close-out ledger cites 1–2 landed commits, 5 INVALID standing. #154 stays out (monitor-only), #146 release-time, #150 closed.

### Deferral → issue map

| Deferred matter | Home issue |
|---|---|
| Flake | #154 (monitor-only) |
| Tracker bookkeeping | #146 (release-time) |
| Items 1–2 rework | none (landed; ledger in close-out) |

---

### Task 1: Parity repro + fix (items 3–4 enabler)

**Files:** `tests/property/test_bcp47_scanner_parity.py` (repro pins), BCP47 scanner or legacy-snapshot file per repro (TBD — likely `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py`)

**Goal:** Minimal failing text identified, pinned, fixed; full parity green including the #90 pin.

- [ ] Repro: seed-loop `test_language_bcp47_hypothesis_parity` with narrowed suppression until trip (or hypothesis-found minimal via `--hypothesis-seed` sweep); reduce to minimal text; add deterministic pin(s) to `test_bcp47_scanner_parity.py` → FAIL. Hard evidence of the 6-vs-12 shape required before touching grammar code.
- [ ] Implement: minimal scanner correction converging to legacy (grandfathered exact-only + longest-valid-prefix preserved — `test_bcp47_grandfathered_prefix_longest_valid_prefix_wins` must stay green). Verify: `uv run pytest tests/property/test_bcp47_scanner_parity.py tests/capabilities/language -q` → PASS; `uv run pytest -m property -q -k "bcp47 or parity" --hypothesis-seed=0..4` (5 seeds) → PASS; ruff/pyright clean.

### Task 2: Item 3 — exact-inverse round-trip asserts

**Files:** `tests/property/test_hypothesis_view_roundtrip.py:65-68,167-180`

**Goal:** Permissive branches replaced by exact asserts; suite green with `filter_too_much` enabled.

- [ ] Implement: per-character exactness — `country_normalized` asserts `subj_ch == stripped` precisely (+ documented space rule); `compact` removes the `subj_ch != src` mismatch allowance (only the exact separator-drop mapping remains). Boundary spans already exact (`:73`); this extends the guarantee per char. Tune corpus/strategy only if green demands it (no assert weakening). Verify: `uv run pytest tests/property/test_hypothesis_view_roundtrip.py -q` → PASS; 3 consecutive runs green (flake watch).

### Task 3: Item 4 — narrow suppression + 10× proof

**Files:** the three `_HYP_SETTINGS` blocks (`parity_corpora.py:75`, `view_roundtrip.py:28`, `trie_parity.py:35`)

**Goal:** `suppress_health_check=[too_slow, data_too_large]` everywhere; 10 consecutive full-property runs green, logged.

- [ ] Implement: narrow all three; run `uv run pytest -m property -q` × 10 sequentially, logging each exit code. Any trip → root-cause (tune, never re-broaden) and restart the count. Verify: 10/10 green log banked for the close-out comment.

### Task 4: Integrate + gate + close-out

**Files:** `CHANGELOG.md`

- [ ] CHANGELOG Unreleased/Fixed: #71 items ledger (1–2 landed earlier + 3–4 this slice + parity fix). Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest` → green; coverage ≥95. Close-out comment: #71 (per-item evidence — closable). Commit per task.
