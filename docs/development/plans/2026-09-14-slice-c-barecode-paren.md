# Slice C — Bare-Code Narrowing + Paren Descriptions + Hygiene (issues #147 B4, #148 remainder, #107 SC, #154 flake hunt)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Finish Language recognition hardening: bare 5–8 letter runs stop claiming (MISSING not INVALID), parenthesized descriptions resolve, SC range confusion gets its regression pin, and the e2e order flake gets a timeboxed hunt.

**Architecture:** Deletion-led narrowing (the only two valid 5–8 IANA codes are hyphenated `no-bok`/`no-nyn`, unreachable by a letter-run regex — so the branch is dead weight, not a tunable); paren forms extend the description tokenizer with structural tokens; no rule/contract/engine changes anywhere.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest, `paxman/capabilities/Language`, `HOW_TO_ADD_NEW_GRAMMAR.md` Steps 2/5/6.

**References:** Issues #147 (B4), #148 (remainder), #107 (SC pin), #154 (flake); `paxman/capabilities/Language/grammar/language_code_recognition.py:1-54`; `paxman/capabilities/Language/grammar/language_description_recognition.py:52-206`; `tests/capabilities/language/test_grammar.py:110-131,205-230`; `tests/unit/test_unicode_property_stage.py` (`test_sc_snapshot_correctness` per #107); `docs/user/capabilities/language.md:11-24`.

**Branch:** `feature/slice-c-barecode-paren` (cut from `dev` — already exists).

---

## File Structure

- Modify: `paxman/capabilities/Language/grammar/language_code_recognition.py` — drop the 5–8 alternative (B4a).
- Modify: `paxman/capabilities/Language/grammar/language_description_recognition.py` — paren forms + structural tokens (B4b? no — #148 remainder).
- Test: `tests/capabilities/language/test_grammar.py` — rewrite 5–8 pins, paren vectors.
- Test: `tests/unit/test_unicode_property_stage.py` — FDFC/FE0C asserts (#107).
- Docs: `docs/user/capabilities/language.md` (does-not column + paren row), `CHANGELOG.md`.
- No rule/contract/engine/core changes. No new data tables (paren forms reuse Task-2 key sets).

---

## Background the implementer needs

### Current state (verbatim)

Bare-code matcher (`language_code_recognition.py:36-43`):

```python
_MATCHER = RegexMatcher(
    pattern=r"[A-Za-z]{5,8}|[A-Za-z]{2,3}",
    boundary=BoundarySpec.WORD_SIGN,
    ...
    suppressible=True,
)
```

Executed on HEAD: the shipped `IANA_LANGUAGE_SUBTAGS` contains exactly two 5–8 entries (`no-bok`, `no-nyn`), both hyphenated — a hyphenless letter-run regex can never emit them. Every bare 5–8 hit (`Xenon`, `hello`, `script`) therefore dies in validation: `INVALID` instead of `MISSING`. The 2–3 branch (real ISO 639-1/2/3 codes) is untouched.

Pin tests encoding the bug (`test_grammar.py:116,219`): `recognize("Xenon")` currently returns the whole-word match with a comment admitting it; `test_boundary_guard_rejects_4_letters` documents the 2-3|5-8 split. Both get rewritten, not deleted.

### Design decisions (locked)

1. **B4a = deletion, not narrowing-to-keys.** Reachable valid set is empty (see above), so a key-set filter and branch deletion are behavior-identical; deletion is one line + docstring. If IANA ever registers a hyphenless 5–8 primary, re-add then (code comment says so).
2. **B4b (`in`→`id` under the default contract) = decision, zero code.** `in` is a genuine deprecated ISO code; whole-input `canonicalize("in")` must stay SUCCESS (A0). Disambiguation in prose is the sanctioned `suppress_common_words` mechanism (repo philosophy per #3-invalid; compositional grammar now gives it something to resolve to). Record as a decision comment on #147; default stays AMBIGUOUS. No code, no tests.
3. **Paren forms reuse everything.** `<Language> (<Script>[, <Region>])` and `<Language> (<Region>)` — e.g. `Chinese (Traditional, Singapore)` → `zh-Hant-SG`, `Chinese (Simplified)` → `zh-Hans`. Tokenizer gains structural tokens `(`/`,`/`)`; slot logic unchanged; gaps may contain paren/comma structure; the trailing-noun follower gate, outer-glue guard, and full-phrase-span invariant apply unchanged (a `)` closes the phrase like end-of-input). Region-prefix form (`Singapore Chinese (...)`) stays excluded, mirroring the `in`-form rule.
4. **#154 hunt is timeboxed (15 min / 10 combined loops).** Deliverable is repro-or-documented-non-repro; the issue stays open either way. Not a gate for the slice.
5. **#107 SC pin rides along** (two asserts in the existing `test_sc_snapshot_correctness`): `U+FDFC` ∈ Sc, `U+FE0C` ∉ Sc. Docstring-chasing half of #107 stays deferred (repo gates don't include docstring coverage).

### Deferral → issue map

| Deferred matter | Home issue |
|---|---|
| B4b default-contract `in` narrowing (decision, no code) | #147 (comment) |
| Broader script/region tables | #148 (stays open) |
| #107 docstring coverage | #107 (stays open) |
| #154 if unreproduced | #154 (stays open, attempt logged) |
| #15/#150 code, #71.3-4, #73 L3, guides | Untouched by this slice (their issues) |

---

### Task 1: B4a — delete the bare 5–8 branch

**Files:** `paxman/capabilities/Language/grammar/language_code_recognition.py:1-54`, `tests/capabilities/language/test_grammar.py:110-131,205-230`

**Goal:** Bare 5–8 letter runs are MISSING (unclaimed), never INVALID.

- [ ] Failing tests first: `recognize("Xenon") == []`, `recognize("hello") == []`, `recognize("script") == []` (bare script-word is not a code); rewrite `test_boundary_guard_word_only` (Xenon host → assert `[]`, keep a carve-guard with a 2–3 host, e.g. embedded `en` stays unclaimed inside a longer run); keep `enUS`/`abcd` MISSING, `en fr de` triple, `Xen` 3-letter match. Run: `uv run pytest tests/capabilities/language/test_grammar.py -q` → FAIL on the new vectors.
- [ ] Implement: pattern → `r"[A-Za-z]{2,3}"`; module docstring (`bare 2-3|5-8` → `bare 2-3` + why: reachable 5–8 set empty, hyphenated only, re-add if IANA registers hyphenless). Nothing else in the file changes (boundary, suppressible, emit all stay). Verify: targeted PASS; `uv run pytest tests/capabilities/language tests/unit/test_b1_common_word_suppression.py -q` → PASS (suppression/A0 guard: `in`/`is` whole-input behavior unchanged).

### Task 2: Paren description forms

**Files:** `paxman/capabilities/Language/grammar/language_description_recognition.py:52-206`, `tests/capabilities/language/test_grammar.py`

**Goal:** `Chinese (Traditional, Singapore)` → one full-span match `(zh, Hant, SG)`; same validation path as `in`-forms (rule untouched — display slots + `language_description` id).

- [ ] Failing tests: `Chinese (Traditional, Singapore)` span `(0, 32)` notation slots `(chinese, traditional, singapore)`; `Chinese (Simplified)` → `(zh-Hans equivalent slots)`; `Chinese (Singapore)`; negatives: `Chinese (Traditional` (unbalanced) → `[]`, `Chinese ()` → `[]`, `Chinese (Traditional dress)` → `[]` (follower gate applies inside parens too). Run: targeted → FAIL.
- [ ] Implement: structural tokens for parens/comma in the tokenizer; `_parse_at`-parallel paren parse after a language slot (reuse `_match_forward/backward`, gap rules extended for paren/comma structure, follower gate + outer-glue guard unchanged; `)` closes like end-of-input). Depends on: nothing (independent of Task 1 — different files? Task 1 touches language_code_recognition + same test file test_grammar.py: coordinate via separate test class names, no overlapping edits). Verify: new tests PASS; full `tests/capabilities/language` green; pipeline spot-check (default AMBIGUOUS/suppressed SUCCESS pattern holds for paren forms — verify, don't assume).

### Task 3: Hygiene ride-along (#107 pin) + docs + CHANGELOG

**Files:** `tests/unit/test_unicode_property_stage.py`, `docs/user/capabilities/language.md:11-24`, `CHANGELOG.md`

- [ ] SC pin: extend `test_sc_snapshot_correctness` — `stage.matches(chr(0xFDFC))` True (Rial Sign is Sc), `not stage.matches(chr(0xFE0C))` (VS-13 is not). Docs: does-not column gains bare 5–8 runs (`hello`, `Xenon` → MISSING — no hyphenless 5–8 primary in the shipped set); recognized-forms table gains the paren row; every added snippet claim executed. CHANGELOG Unreleased/Fixed entries for B4a + parens.
- [ ] Verify: `uv run pytest tests/unit/test_unicode_property_stage.py tests/capabilities/language -q` → PASS.

### Task 4: #154 flake hunt (timeboxed, non-gating)

**Files:** none (or the fix, if found)

- [ ] Loop the combined property+e2e selection up to 10x (15-min cap): if `test_cli_scan_default_all_json` trips, isolate (bisect selection, registry/tmp-cwd/shared-state suspects) and fix or file findings back to #154; if green throughout, log the attempt on #154 and move on. QA: issue comment posted either way.

### Task 5: Full gate + close-out

**Files:** none new

- [ ] Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest` → green; coverage ≥95 on the four packages. Record B4b decision comment on #147. Commit per task.
