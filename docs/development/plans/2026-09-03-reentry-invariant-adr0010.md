# Re-entry Fixed-Point Invariant — ADR-0010 + Property Test + Offered-Format Audit (issue #123)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Mandate the re-entry (fixed-point) invariant — `canonicalize(V, C) == SUCCESS V` for every canonical value `V` paxman emits under contract `C`, irrespective of the `output_format` that produced `V` — via ADR-0010, an executable property test over all 15 shipped capabilities, and an offered-format audit that fixes or de-offers any format that fails.

**Architecture:** No engine or grammar changes in this plan unless the audit finds a violating format (then: fix the format's re-recognizability or de-offer it via `OFFERED_OUTPUT_FORMATS`). ADR-0010 locks the formal statement and scope conditions (contract-relative, default contracts guaranteed, snapshot-scoped). The property test is the enforcement mechanism (CI), not a runtime assertion. Suppression interaction (`suppress_common_words=True`) is **out of scope here** — it is decided and implemented by #122 (A0 whole-input exemption); ADR-0010 records the interaction, #122's branch carries the code.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: `property`, `integration`, `unit`), hypothesis "ci" profile (`max_examples=100`, `deadline=None`), no new dependencies.

**References:**
- Issue #123 (this plan), issue #122 (suppression decision A0 — cross-dependency)
- `paxman/engine/orchestrator.py:63-71` (`ExecutionResult` shape), `paxman/engine/orchestrator.py:736-747` (`_determine_status`)
- `paxman/api/canonicalize.py:6-12` (`canonicalize()` returning `ExecutionResult` to callers), `paxman/core/capability_contract.py:45-56` (contract format class vars)
- `docs/adr/0004-single-value-invariant.md` (invariant-ADR style precedent), `docs/adr/0009-recognition-kernel.md` (current ADR numbering; next is 0010)
- `docs/recipes/segmentation.md`, `docs/user/migration.md` (docs to cross-link)
- Offered formats inventory: `paxman/capabilities/*/contract.py` `OFFERED_OUTPUT_FORMATS` (see Task 3 table)
- Plan conventions: `docs/development/plans/2026-08-30-versioned-docs.md` (docs+test shape), `docs/development/plans/2026-08-30-kernel-hardening-2.md` (Medium shape)

**Branch:** `feature/reentry-invariant-adr0010` (already cut from `dev`; not a hotfix — no worktree needed)

**Milestone:** `v0.4.0`. **Gate:** no new capability lands before this plan closes #123 (per issue #123 / #122 decision thread).

---

## Background the implementer needs

### The invariant (verbatim, from issue #123 + decision chat 2026-09-03)

Two distinct properties; only the second is new:

1. **Determinism (already mandated, root `AGENTS.md` anti-patterns):** same `I + C + library snapshot` → same `ExecutionResult`.
2. **Re-entry / fixed-point (this ADR):** if `R = canonicalize(I, C)` has `R.status == SUCCESS` and `R.canonicalized_value == V`, then `R' = canonicalize(V, C)` must have `R'.status == SUCCESS` and `R'.canonicalized_value == V` — **irrespective of the `output_format` in `C` that produced `V`** (default or offered). An `output_format` whose rendered value does not re-enter (degrades to `MISSING`/`INVALID`/`AMBIGUOUS`) must not be offered.

### Current state (verified 2026-09-03)

- Nothing codifies re-entry. The only "round-trip" in docs is ADR-0009's *view-offset* round-trip (`docs/adr/0009-recognition-kernel.md:955`), an internal offset-mapping property — unrelated.
- No test asserts re-entry for canonical or offered formats anywhere in `tests/`.
- Known structural violator under `suppress_common_words=True`: canonical values that are themselves common words (`Country TO/IN/CA/NO/US`, `Language en/ca/id/…`, `Currency ALL`, `SIUnit cd`) re-enter as `MISSING` (`paxman/core/grammar/engine_loop.py:144-150`). **Resolved by #122 A0** (whole-input exemption, decision recorded in #122 body + comment). This plan's property tests run under **default contracts** (`suppress_common_words=False`), so they are green before #122 lands; the `suppress=True` re-entry case is asserted in #122's implementation, not here.
- Offered-format inventory (from `paxman/capabilities/*/contract.py`):

| Capability | DEFAULT | OFFERED | Default fixture input |
|---|---|---|---|
| BIC | `bic` (identity, compact) | `grouped`, `bic11` | `DEUTDEFF500` |
| Coordinates | `decimal` | see `Coordinates/contract.py:11` | `51.5074, -0.1278` |
| Country | `alpha2` | `alpha3`, `numeric`, `name` | `United States` |
| Currency | `code` | — (empty) | `USD` |
| Date | `ISO` | `US` | `2026-01-15` |
| Email | `address` | — (empty) | `user@example.com` |
| IBAN | `compact` | `paper` | `GB29NWBK60161331926819` |
| IP | `ip` | — (empty) | `10.0.0.1` |
| ISBN | `isbn13` | `hyphenated` | `9780306406157` |
| ISSN | `hyphenated` | `compact`, `urn` | `2049-3630` |
| Language | `bcp47` | see `Language/contract.py:16` | `en` |
| MacAddress | `colon` | see `MacAddress/contract.py:24` | `00:1A:2B:3C:4D:5E` |
| Money | `code_amount` | `compact` | `45.50 USD` |
| ORCID | `orcid` | `uri`, `compact` | `0000-0002-1825-0097` |
| Phone | `e164` | see `Phone/contract.py:64` | `+12125550123` |
| SIUnit | see `SIUnit/contract.py` (confirm) | — (empty) | `kg` |
| URL | `url` | — (empty) | `https://example.com` |

Fixture inputs above are verified-good defaults from each capability's docs/tests; Task 3 confirms each against `tests/capabilities/<name>/` before relying on it.

### Design decisions (locked)

1. **ADR-0010 status: Accepted** (not Proposed) — the decision is hard, per issue #123 ("This is a hard decision (not open for debate)").
2. **Scope: contract-relative.** The invariant binds `V` to the *same* `C` that produced it. Guaranteed unconditionally for **default contracts** of all shipped capabilities (property-tested in CI). For non-default contracts it holds conditionally under the **recognize-own-output condition**: `C`'s `active_grammars` must include a grammar that recognizes every format in `C`'s output chain (its `output_format`), and `C`'s rule set (`pinned_rules`/`excluded_rules`/`year`) must not remove the rules that validate that form. The engine does **not** enforce this at runtime (no cost on the hot path); CI property tests + the Task-3 audit are the enforcement.
3. **Offered formats: guaranteed, not audited-only.** Every format in `OFFERED_OUTPUT_FORMATS` must re-enter under the same contract; violations are fixed or de-offered with rationale (Task 4).
4. **Snapshot scope.** Like determinism, re-entry is scoped to a library snapshot (`VersionStamp.paxman_version` + `recognition_revision`, `paxman/engine/orchestrator.py:136-138`). A data-table update may change which `V` a given `I` produces, but must never make a produced `V` un-re-enterable within the same snapshot.
5. **Suppression interaction.** ADR-0010 records: with `suppress_common_words=False` (default) re-entry is unconditional; with `suppress_common_words=True` re-entry of a suppressed-word canonical value is restored by #122's A0 whole-input exemption (`canonicalize("TO", suppress=True)` → `SUCCESS "TO"` once #122 lands). Cross-link, don't implement.
6. **Test placement:** `tests/property/test_reentry_invariant.py`, marker `property`, hypothesis for case/whitespace variants of the fixture inputs (no registry violation — `tests/AGENTS.md` says property tests stay off the registry; **exception documented like `test_money_properties.py`**: re-entry is a full-pipeline invariant, so this module carries a local `_fresh_registry` fixture with a module docstring note, mirroring `tests/property/test_money_properties.py`).
7. **No runtime changes** to `paxman/engine/orchestrator.py` or `paxman/core/` in Tasks 1-3. Task 4 touches capability contracts/grammars only if the audit finds violations.

---

## File Structure

- Create: `docs/adr/0010-re-entry-fixed-point-invariant.md`
- Create: `tests/property/test_reentry_invariant.py`
- Modify (only on audit findings): `paxman/capabilities/<Name>/contract.py` (de-offer), `paxman/capabilities/<Name>/grammar/*.py` (add recognition), and their `tests/capabilities/<name>/test_capability.py`
- Modify: `AGENTS.md` (invariant list), `CONTEXT.md` (glossary entry), `docs/recipes/segmentation.md` + `docs/user/migration.md` (one cross-reference line each)

---

### Task 1: ADR-0010 — Re-entry (fixed-point) invariant

**Files:** `docs/adr/0010-re-entry-fixed-point-invariant.md`

**Goal:** Lock the formal statement, scope conditions, and rejected alternatives as an Accepted ADR, following `docs/adr/0004-single-value-invariant.md` structure (Context / Decision / Consequences / References).

- [ ] Write the ADR with exactly these sections:
  - **Formal statement** (the two-property quote from Background, verbatim semantics).
  - **Scope decisions** (locked decisions 2-5 above): contract-relative + default-contract guarantee; recognize-own-output condition for non-default contracts; offered formats guaranteed; snapshot scope via `VersionStamp`; suppression interaction pointing at #122 A0.
  - **Consequences:** engine never raises on re-entry violation (property tests + audit enforce); new capabilities must add a re-entry row to `tests/property/test_reentry_invariant.py` before landing (this is the "no new capabilities until #123" gate made structural); de-offering a format is a breaking change requiring a migration note.
  - **Rejected alternatives:** runtime assertion in `run_capability` (hot-path cost, duplicates CI); invariant scoped to default formats only (silently permits un-re-recognizable offered formats — violates the issue statement); A1 suppression fallback (covered by #122, rejected there as hypothetical).
- [ ] Front-matter: Status Accepted, Date 2026-09-03, References #123, #122, ADR-0004 (invariant family), ADR-0009 (kernel).
- [ ] Verify: `uv run ruff check docs/ 2>/dev/null; test -f docs/adr/0010-re-entry-fixed-point-invariant.md && echo OK`. Commit: `docs(adr): 0010 re-entry fixed-point invariant (#123)`.

### Task 2: Property test — re-entry over all 15 capabilities

**Files:** `tests/property/test_reentry_invariant.py` (create)

**Goal:** The executable mandate. Most shipped formats likely already re-enter; the suite's red state is **genuine violating formats** — any row that fails the fixed-point assertion is a Task-4 finding. If every row passes on first run, the suite still lands as the permanent CI enforcement (TDD red step is satisfied by whichever suspect formats fail; expected suspects listed at the Verify bullet).

- [ ] Module docstring documents the full-pipeline exception per `tests/AGENTS.md` (mirrors `test_money_properties.py`'s `_fresh_registry` note): autouse `_clean_registry` + `register_all_shipped()` inside the fixture, property layer stays registry-free elsewhere.
- [ ] Fixture table: `@dataclass(frozen=True)` per row — `capability` (imported class), `input`, `formats: tuple[str, ...]` = `("", "default") + offered`, `expected_default: str`. Populate all 15 rows from the Background table; confirm each `expected_default` against `tests/capabilities/<name>/test_capability.py` while writing the row.
- [ ] Parametrized test `test_default_contract_reentry(cap_row, fmt)`: build contract via `cap_row.capability.create_contract(output_format=fmt or None)`; `first = canonicalize(cap_row.input, contract)`; assert `first.status is Resolution.SUCCESS`; `second = canonicalize(first.canonicalized_value, contract)`; assert `second.status is Resolution.SUCCESS` and `second.canonicalized_value == first.canonicalized_value`. Run: `uv run pytest tests/property/test_reentry_invariant.py -v` → any failing/de-offered format surfaces here (feed findings to Task 4).
- [ ] Hypothesis test `test_reentry_case_whitespace_variants`: `@given(variant=st.sampled_from(case_ws_variants))` where `case_ws_variants` is the explicit list of upper/lower/title + padded `"  {input}  "` / `"{input}\n"` forms of each fixture input (drawn per capability, tagged with its row); assert the same fixed-point property. Random free text is deliberately avoided — arbitrary strings legitimately `MISSING`, which would test nothing. Run: `uv run pytest tests/property/test_reentry_invariant.py::test_reentry_case_whitespace_variants -v` → PASS (or findings → Task 4).
- [ ] Verify: `uv run pytest tests/property/test_reentry_invariant.py -q` → green **except** genuinely failing formats (expected suspects: `ISSN urn`, `Date US`, `Money compact`, `Coordinates` non-decimal — confirm, don't assume). Commit: `test(property): re-entry fixed-point suite for 15 capabilities (#123)`.

### Task 3: Offered-format audit

**Files:** no source changes — produces the findings list consumed by Task 4.

**Goal:** For every capability × offered format, decide re-recognizable vs violating, citing the grammar that must recognize the rendered form.

- [ ] For each row of the Task-2 output, record in the PR description: capability, format, rendered `V`, status of `canonicalize(V, C)`, and the grammar expected to recognize `V` (e.g. ISSN `urn` → does any grammar accept the `urn:issn:` prefix? `Date US` → does Date grammar accept `01/15/2026`? `Money compact` → which `Money/grammar/` stage?).
- [ ] Classify each finding: **(a)** re-recognizable (grammar exists, test gap) → Task 4 fix is test-side only; **(b)** not recognized by any shipped grammar → decide fix-or-de-offer; **(c)** recognized but resolves differently (AMBIGUOUS/INVALID) → rule-side, treat as (b).
- [ ] Verify: findings list complete for all 15 rows × all offered formats (inventory in Background table). Commit: `docs(plan): audit findings for offered-format re-entry (#123)` (append to PR description, no file).

### Task 4: Fix or de-offer violating formats

**Files:** per finding — `paxman/capabilities/<Name>/contract.py` and/or `paxman/capabilities/<Name>/grammar/<format>_recognition.py`, plus `tests/capabilities/<name>/test_capability.py`.

**Goal:** Zero failures in `tests/property/test_reentry_invariant.py`.

- [ ] For each **(a)** finding: no source change; the Task-2 suite is the fix. Mark the finding resolved in the audit list.
- [ ] For each **(b)** finding, decide by the issue's bar — "an output format paxman cannot itself re-recognize must not be offered":
  - If the format has a shipped recognition precedent elsewhere (e.g. ORCID `uri` — grammar already accepts `https://orcid.org/…` per research `docs/development/research/2026-08-23-orcid-canonicalization.md`), **fix**: extend the capability's grammar to recognize the rendered form (TDD: failing `tests/capabilities/<name>/test_grammar.py::test_<format>_reenters` first, minimal alternation/normalizer change, kernel-parity suites if `paxman/core/grammar` touched).
  - Else **de-offer**: remove the format from `OFFERED_OUTPUT_FORMATS` (contract frozen dataclass — direct edit), update the contract docstring + `docs/user/capabilities/<name>.md` table, note the removal in `CHANGELOG.md` under a breaking section. De-offer rationale recorded in ADR-0010 "Consequences".
- [ ] Verify: `uv run pytest tests/property/test_reentry_invariant.py tests/capabilities -q` → PASS. Commit: `fix(<cap>): re-recognize <format> output` / `feat(<cap>)!: de-offer <format>` per finding.

### Task 5: Cross-links + gate wiring

**Files:** `AGENTS.md`, `CONTEXT.md`, `docs/recipes/segmentation.md`, `docs/user/migration.md`

**Goal:** Make the invariant part of the documented invariant family and the new-capability gate.

- [ ] `AGENTS.md` — add re-entry to the invariant list next to the determinism bullet: "Re-entry (fixed-point): a SUCCESS canonical value `V` re-canonicalizes to `V` under the same contract, any `output_format` — enforced by `tests/property/test_reentry_invariant.py`; new capabilities must extend that suite (ADR-0010)."
- [ ] `CONTEXT.md` — glossary entry "Re-entry invariant" (one line, pointing at ADR-0010 + the test file).
- [ ] `docs/recipes/segmentation.md` + `docs/user/migration.md` — one sentence each: canonical output is safe to feed back (`#123`), with the `suppress_common_words=True` caveat pointing at #122 A0.
- [ ] Verify (full gate): `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green; `uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → ≥95. Commit: `docs: cross-link re-entry invariant (#123)`.

---

## Self-review notes

- Spec coverage: #123 deliverables 1-4 → Tasks 1 (ADR), 2 (property test), 3+4 (audit + fix/de-offer), 5 (cross-links incl. AGENTS.md). Suppression interaction = recorded decision + #122 pointer, matching the chat decision that #122 owns it.
- Type consistency: single contract construction path (`capability.create_contract(output_format=...)`) across Tasks 2/4; single fixture dataclass; no new Notation/Contract shapes introduced.
- Momus dry-run: every task names files, tests, and `uv run` verifies; no TBD/TODO; references cite file:line; branch named.
