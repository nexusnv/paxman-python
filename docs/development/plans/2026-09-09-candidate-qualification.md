# Candidate Qualification (ADR-0012) + Language Pilot Implementation Plan (issues #147, #71)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Unregistered-but-well-formed tags stop yielding canonical values: `Serbo-Croatian` → `SUCCESS sh`, `xx-yyyyy` → `INVALID`, with no rule ranking, scoring, or weights introduced; closes #147-B1/B3 and the #71 dedup-scoping slice that shares the same code.

**Architecture:** New ADR-0012 states the undocumented principle (no confidence scoring; no authority-less ranking; ordering must be structural, total, authority-grounded) and derives the corroboration invariant: a `RuleStrategy.PARSER` candidate survives only when a `RuleStrategy.LOOKUP_TABLE` rule validates the *same* `RecognizedRep`. The filter slots into `paxman/engine/orchestrator.py` after `_collect_candidates` (`:548`), which already pairs each `Candidate` with its source rep. Genuine multi-lookup disagreements still yield `AMBIGUOUS` via the untouched `_determine_status` (`:752`). No grammar, contract, or `format_value` changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: integration/property), `paxman/engine/orchestrator.py`, `paxman/capabilities/Language`.

**References:** Issues #147 (B1/B3), #71 (dedup scoping), #132; `paxman/engine/orchestrator.py:548-604` (`_collect_candidates` pairing), `:731-763` (dedup + status), `paxman/core/domain.py:19-24` (`RuleStrategy`), `paxman/capabilities/Language/rules/bcp47_rfc5646_ed2009.py:91-94` (PARSER, `bcp47_tag`), `paxman/capabilities/Language/rules/iana_language_subtag_registry_ed2026.py:132-138` (LOOKUP_TABLE, `bcp47_tag`), `paxman/capabilities/Language/rules/iso_639_1_ed2002.py:70-73` (LOOKUP_TABLE, `language_name`), `docs/adr/0011-output-format-information-preservation.md`, `tests/property/test_reentry_invariant.py`.

**Branch:** `feature/adr0012-candidate-qualification` (cut from `origin/dev` @ `21bf5d4`, post-#138)

---

## Background the implementer needs

### Current state (verbatim)

`_collect_candidates` returns `(Candidate, RecognizedRep)` pairs but nothing consumes the pairing for qualification — every validated candidate survives to `_determine_status`, so a PARSER echo (`serbo-croatian` from `Section 2.1-syntax`) ties a LOOKUP denotation (`sh` from `Section-english-name-mapping`) and two distinct values → `AMBIGUOUS`. Worse, a lone ghost (`xx-yyyyy`, no registry entry anywhere) yields `SUCCESS` on syntax alone (verified 2026-09-09: `canonicalize('xx-yyyyy')` → `SUCCESS 'xx-yyyyy'` via `Section 2.1-syntax` only).

### Design decisions (locked)

1. **Disqualification, not ranking.** No rule is superior to another; no scores/weights/priority fields anywhere. A PARSER candidate is *provisional structure*, kept iff a LOOKUP_TABLE rule validates the same recognition. Rationale: unregistered tags denote nothing — the multi-candidate extension of the existing recognized-but-unvalidated → `INVALID` rule (`_determine_status`: no candidates + recognitions → `INVALID`).
2. **Same-recognition corroboration (span-level rejected).** Corroboration keys on recognition identity, not span overlap: a `language_name` hit must not corroborate an unrelated `bcp47_tag` shape on the same span, or B1 survives. `en-US` keeps both candidates (syntax + registry validate the same BCP47 rep, same value → dedup → `SUCCESS`).
3. **#71 travels in this ADR but ships as its own filter.** Per-grammar `keep_duplicate_spans` scoping (today capability-wide at `:135-141`, correct only because Date is the sole `strategy=="all"` user) is the same "attribute candidates to their source" problem using the same pairing; design it in ADR-0012, implement after corroboration lands, gated by a two-grammar unit test (one `all`, one `first`, shared span).
4. **Honest AMBIGUOUS preserved.** Two LOOKUP-backed distinct values on one mention still yield `AMBIGUOUS`. No behavior change for any capability whose candidates are all LOOKUP-backed (everything except BCP47-shaped ghosts — Language pilot only).
5. **No grammar/contract/format changes.** Recognition still emits both matches; `Section 2.1-syntax` keeps its Prefix guard and citation; the Prefix-impurity tech debt is *explained* by the ADR (syntax corroboration is structural, Prefix stays documented) rather than removed.

---

## File Structure

- Create: `docs/adr/0012-candidate-qualification.md` — principle + corroboration invariant + #71 scoping design + rejected alternatives (per-rule precedence, span-level corroboration, confidence scoring).
- Modify: `paxman/engine/orchestrator.py` — post-`_collect_candidates` corroboration filter (new `_require_lookup_corroboration`, called at `:142` before `_dedup_candidates`).
- Test: `tests/integration/test_language_capability.py` — `test_syntax_ghost_never_denotes` (`xx-yyyyy` → `INVALID`), `test_serbo_croatian_resolves_to_sh` (`Serbo-Croatian` → `SUCCESS sh`; spaced form unchanged), `test_valid_tag_keeps_both_validations` (`en-US` candidates still carry both rules).
- Test: `tests/property/test_reentry_invariant.py` — extend Language row with `serbo-croatian` exclusion note (ghost no longer a value; `sh` fixed point already covered).
- Docs: `docs/user/capabilities/language.md` — Statuses row `Serbo-Croatian` → `SUCCESS sh` (name rule; BCP47 ghost disqualified per ADR-0012); `CHANGELOG.md` — Fixed entry under Unreleased.
- Test (Task 5): engine unit for per-grammar `keep_duplicate_spans` scoping (new `tests/unit/test_dedup_scoping.py`, two-grammar fixture).

No new capability modules; no `paxman/core` changes; no generated-data changes.

---

### Task 1: ADR-0012 — write the principle down

**Files:** `docs/adr/0012-candidate-qualification.md` (create)

**Goal:** The undocumented no-heuristics principle becomes reviewable law, with corroboration as its first application.

- [ ] Write the ADR: status Proposed; Context (B1 ghost candidates, `xx-yyyyy` SUCCESS evidence, #71 same-region problem); Decision (no scores/weights/per-rule precedence; PARSER provisional until same-recognition LOOKUP corroboration; honest AMBIGUOUS for multi-lookup disagreement; #71 scoping design); Consequences (Language pilot, `Serbo-Croatian` → `sh`, lone ghosts → `INVALID`, no other capability changes behavior); Rejected (per-rule precedence with rationale "cites no authority", span-level corroboration with rationale "cross-semantics leakage", confidence scoring). Verify: `paxman-momus-review` on the ADR → OKAY. Commit: `docs(adr): ADR-0012 candidate qualification — no authority-less ranking`.

### Task 2: Red tests — ghosts disqualified, valid tags untouched

**Files:** `tests/integration/test_language_capability.py`

**Goal:** Prove the new invariant fails today.

- [ ] Add `test_syntax_ghost_never_denotes` (`xx-yyyyy` → `INVALID`, candidates empty), `test_serbo_croatian_resolves_to_sh` (`Serbo-Croatian` → `SUCCESS sh`), `test_valid_tag_keeps_both_validations` (`en-US` → `SUCCESS`, both `Section 2.1-syntax` + `Section-iana-registry` in candidate rules). Run: `uv run pytest tests/integration/test_language_capability.py -q` → Expected: first two FAIL (ghost SUCCESS / AMBIGUOUS today), third PASS.

### Task 3: Corroboration filter in the orchestrator

**Files:** `paxman/engine/orchestrator.py:142` (call site), new `_require_lookup_corroboration` beside `_dedup_candidates`

**Goal:** Drop PARSER candidates no LOOKUP rule corroborates on the same recognition; pure function of (candidate, rep, rule strategies), no ordering, no scores.

- [ ] Implement: group collected pairs by recognition identity; keep a PARSER-strategy candidate iff any LOOKUP_TABLE-strategy candidate shares its recognition; LOOKUP candidates always kept; strategy read from the rule objects already in scope in `run_capability` (thread `all_rules` strategy map into the filter — do not re-derive or import capability code). Verify: Task 2 tests → PASS; `uv run pytest tests/integration -q` → PASS (no other capability changes status); commit: `fix(engine): disqualify uncorroborated PARSER candidates (ADR-0012)`.

### Task 4: Language pilot docs + changelog + re-entry row

**Files:** `docs/user/capabilities/language.md`, `CHANGELOG.md`, `tests/property/test_reentry_invariant.py`

**Goal:** User surfaces state the new invariant; fixed-point suite stays exact.

- [ ] Update Statuses `Serbo-Croatian` row to `SUCCESS sh` with ADR-0012 note; append CHANGELOG Fixed entry (`Serbo-Croatian` ghost disqualified; lone well-formed-unregistered tags → `INVALID`); extend the re-entry note so the ghost value is never used as a fixture. Verify: `uv run pytest tests/property/test_reentry_invariant.py tests/capabilities/language -q` → PASS.

### Task 5: #71 per-grammar dedup scoping (same pairing, separate filter)

**Files:** `paxman/engine/orchestrator.py:135-142`, `tests/unit/test_dedup_scoping.py` (create)

**Goal:** `keep_duplicate_spans` scoped to the producing grammar, not the capability.

- [ ] Failing test first: two-grammar fixture (one `CandidatesMatcher strategy=="all"`, one `"first"`, shared span) asserting AMBIGUOUS preserved only for the `all` grammar while the other dedups; Date `01/02/2026` parity pinned. Implement scoping via the existing `(Candidate, rep)` pairing. Verify: new test PASS; `uv run pytest tests/unit tests/property/test_bcp47_scanner_parity.py -q` → PASS.

### Task 6: Full gates + parity + coverage

**Files:** none (verification only)

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green, coverage ≥95 (`--fail-under=95`). Parity suites named: `test_reentry_invariant`, `test_bcp47_scanner_parity`, `test_output_format_preservation`, grammar `test_data_consistency` for Language. Commit: docs + tests already committed per-task; no version bump, no release.

---

Plan saved. Execute task-by-task via `tdd`; review with `paxman-momus-review` then `paxman-oracle-review`.
