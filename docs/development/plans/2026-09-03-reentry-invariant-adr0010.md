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
## Task 3 Audit Findings (generated 2026-09-03)

_Method: One-off, uncommitted script `/tmp/opencode/reentry_audit.py` (not committed) enumerates the shipped set via `paxman/api/bootstrap.py:list_shipped_capabilities()` and reads each contract's `OFFERED_OUTPUT_FORMATS` sorted via `factory.create_contract().OFFERED_OUTPUT_FORMATS` (contract-relative, same contract used for re-entry). For each of the 17 capabilities it reuses the verified-good fixture inputs from `tests/property/test_reentry_invariant.py:98-145` (`ROWS`), iterates `formats = ("", "default", *sorted(offered))`, executes `first = canonicalize(input, C)` with the default contract (`suppress_common_words=False`, snapshot-scoped via `VersionStamp` `paxman_version='0.3.1'` + `recognition_revision` per `paxman/core/discovery.py:190-192` — hash of compiled matcher set plus `paxman/shared_data/*_snapshot.json` SHAs), then if `first.status is SUCCESS` probes re-entry with `second = canonicalize(first.canonicalized_value, C)` under the identical `C` and checks `second.status is SUCCESS` and `second.canonicalized_value == first.canonicalized_value`. The second call's provenance `first.candidates[0].recognition_rule` is recorded as the producing grammar; the grammar expected to recognize the rendered `V` is cited by `paxman/capabilities/<Name>/grammar/*.py` line (lexicon/regex/scanner definition). The script covers the full `("", "default", *sorted(offered))` matrix — 63 param cases (29 offered) plus the hypothesis whitespace variant (total 64 tests in `tests/property/test_reentry_invariant.py`)._

**Classification definitions**

- **(a) re-recognizable (test gap):** a grammar exists that accepts the rendered `V` and re-entry would succeed; the failure is a test harness gap, fixable test-side only.
- **(b) not recognized by any shipped grammar (`MISSING`):** no shipped grammar accepts `V` as a mention; fix-or-de-offer (extend grammar or remove from `OFFERED_OUTPUT_FORMATS`). 
- **(c) recognized but resolves differently (`INVALID`/`AMBIGUOUS` or `SUCCESS` with `W != V`):** grammar accepts `V` but validation fails or canonicalizes to a different value; rule-side, treated as **(b)** per task brief.

**Complete matrix — 63 rows (17 capabilities × `("", "default", *sorted(offered))`; `default` and `unset` resolve identically to `DEFAULT_OUTPUT_FORMAT` and are listed separately per Task 2's parametrisation; `suppress_common_words=False`)**

| Capability | Format | First input → V | Re-entry status | Classification | Grammar expected | Note |
|---|---|---|---|---|---|---|
| bic | unset | `DEUTDEFF500` → `DEUTDEFF500` | SUCCESS `DEUTDEFF500` | PASS | `paxman/capabilities/BIC/grammar/bic_recognition.py:125` `BICRecognitionGrammar` (`_BIC_COMPACT` line 25) | default identity |
| bic | default | `DEUTDEFF500` → `DEUTDEFF500` | SUCCESS `DEUTDEFF500` | PASS | `paxman/capabilities/BIC/grammar/bic_recognition.py:125` | same as unset |
| bic | bic11 | `DEUTDEFF500` → `DEUTDEFF500` | SUCCESS `DEUTDEFF500` | PASS | `paxman/capabilities/BIC/grammar/bic_recognition.py:125` (`_BIC_COMPACT` 8/11) ; `capability.py:66-69` `bic11` appends `XXX` when 8-char | 11-char input already bic11, identity |
| bic | grouped | `DEUTDEFF500` → `DEUT DE FF 500` | SUCCESS `DEUT DE FF 500` | PASS | `paxman/capabilities/BIC/grammar/bic_recognition.py:125` (`_BIC_GROUPED` line 26 `AAAA BB CC [XXX]` single-space) ; `capability.py:62-65` | grouped re-recognized via same regex's grouped branch |
| coordinates | unset | `51.5074, -0.1278` → `51.5074, -0.1278` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` `CoordinatesRecognitionGrammar` | decimal identity |
| coordinates | default | `51.5074, -0.1278` → `51.5074, -0.1278` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` | same |
| coordinates | dm | `51.5074, -0.1278` → `51°30.444′N 0°7.668′W` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` ; `capability.py:134-146` `_format_dm` | DM re-recognized via same single grammar (all 6 forms in one regex) |
| coordinates | dms | `51.5074, -0.1278` → `51°30′27″N 0°7′40″W` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` ; `capability.py:125-131` `_format_dms` | |
| coordinates | geo_uri | `51.5074, -0.1278` → `geo:51.5074,-0.1278` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` ; `capability.py:203-206` | geo URI |
| coordinates | geojson_pair | `51.5074, -0.1278` → `[-0.1278, 51.5074]` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` ; `capability.py:208-211` | |
| coordinates | iso6709 | `51.5074, -0.1278` → `+51.5074-000.1278/` | SUCCESS | PASS | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:502` ; `capability.py:91-122` `_format_iso` | |
| country | unset | `United States` → `US` | SUCCESS | PASS | `paxman/capabilities/Country/grammar/name_recognition.py:60` `NameGrammar` (lexicon) | via name → alpha2 canonical |
| country | default | `United States` → `US` | SUCCESS | PASS | `paxman/capabilities/Country/grammar/name_recognition.py:60` | |
| country | alpha3 | `United States` → `USA` | SUCCESS `USA` | PASS | `paxman/capabilities/Country/grammar/alpha3_recognition.py:33` `Alpha3Grammar` (`[A-Za-z]{3}` line 24) ; `capability.py:146-147` | re-entry via alpha3 grammar |
| country | name | `United States` → `UNITED STATES` | SUCCESS `UNITED STATES` | PASS | `paxman/capabilities/Country/grammar/name_recognition.py:60` | uppercased name re-recognized |
| country | numeric | `United States` → `840` | SUCCESS `840` | PASS | `paxman/capabilities/Country/grammar/numeric_recognition.py:34` `NumericGrammar` (`\d{1,3}` line 25) ; `capability.py:148-149` | |
| currency | unset | `USD` → `USD` | SUCCESS | PASS | `paxman/capabilities/Currency/grammar/code_recognition.py:34` `CodeRecognition` (`[A-Za-z]{3}`) | identity |
| currency | default | `USD` → `USD` | SUCCESS | PASS | `paxman/capabilities/Currency/grammar/code_recognition.py:34` | |
| date | unset | `2026-01-15` → `2026-01-15` | SUCCESS | PASS | `paxman/capabilities/Date/grammar/date_recognition.py:103` `DateGrammar` (`ISO_MATCHER` `(\d{4})-(\d{2})-(\d{2})` line 46) | ISO identity |
| date | default | `2026-01-15` → `2026-01-15` | SUCCESS | PASS | `paxman/capabilities/Date/grammar/date_recognition.py:103` | |
| date | US | `2026-01-15` → `01/15/2026` | SUCCESS `01/15/2026` | PASS | `paxman/capabilities/Date/grammar/date_recognition.py:103` (`US_MATCHER` `(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})` line 61-67, semantics `us_calendar_date` line 96) ; `capability.py:98-105` | US slash re-recognized via same CandidatesMatcher (all-strategy) |
| email | unset | `user@example.com` → `user@example.com` | SUCCESS | PASS | `paxman/capabilities/Email/grammar/standard_recognition.py:32` `StandardEmailGrammar` | |
| email | default | `user@example.com` → `user@example.com` | SUCCESS | PASS | `paxman/capabilities/Email/grammar/standard_recognition.py:32` | |
| iban | unset | `GB29NWBK60161331926819` → `GB29NWBK60161331926819` | SUCCESS | PASS | `paxman/capabilities/IBAN/grammar/iban_recognition.py:87` `IBANRecognitionGrammar` | electronic compact identity |
| iban | default | `GB29NWBK60161331926819` → `GB29NWBK60161331926819` | SUCCESS | PASS | `paxman/capabilities/IBAN/grammar/iban_recognition.py:87` | |
| iban | paper | `GB29NWBK60161331926819` → `GB29 NWBK 6016 1331 9268 19` | SUCCESS `GB29 NWBK 6016 1331 9268 19` | PASS | `paxman/capabilities/IBAN/grammar/iban_recognition.py:87` (paper quartets branch, single-space groups) ; `capability.py:60-61` | paper re-recognized via same grammar's paper form |
| ip | unset | `10.0.0.1` → `10.0.0.1` | SUCCESS | PASS | `paxman/capabilities/IP/grammar/ipv4_recognition.py:29` `IPv4Grammar` | |
| ip | default | `10.0.0.1` → `10.0.0.1` | SUCCESS | PASS | `paxman/capabilities/IP/grammar/ipv4_recognition.py:29` | |
| isbn | unset | `9780306406157` → `9780306406157` | SUCCESS | PASS | `paxman/capabilities/ISBN/grammar/isbn13_recognition.py:27` `ISBN13RecognitionGrammar` | bare 13 identity |
| isbn | default | `9780306406157` → `9780306406157` | SUCCESS | PASS | `paxman/capabilities/ISBN/grammar/isbn13_recognition.py:27` | |
| isbn | hyphenated | `9780306406157` → `978-0-306-40615-7` | SUCCESS `978-0-306-40615-7` | PASS | `paxman/capabilities/ISBN/grammar/isbn13_recognition.py:27` (hyphen-tolerant pattern) ; `capability.py:44-70` `_hyphenate` Range Message | hyphens stripped by notation, re-recognized |
| issn | unset | `2049-3630` → `2049-3630` | SUCCESS | PASS | `paxman/capabilities/ISSN/grammar/issn_recognition.py:30` `ISSNRecognitionGrammar` (`LabelMatcher` pattern `\d{4}-?\d{3}[0-9Xx]` line 22) | hyphenated identity |
| issn | default | `2049-3630` → `2049-3630` | SUCCESS | PASS | `paxman/capabilities/ISSN/grammar/issn_recognition.py:30` | |
| issn | compact | `2049-3630` → `20493630` | SUCCESS `20493630` | PASS | `paxman/capabilities/ISSN/grammar/issn_recognition.py:30` (hyphen optional `-?` so compact matches) ; `capability.py:65-66` | |
| issn | urn | `2049-3630` → `urn:issn:2049-3630` | SUCCESS `urn:issn:2049-3630` | PASS | `paxman/capabilities/ISSN/grammar/issn_recognition.py:30` — no explicit `urn:issn:` prefix in grammar; re-entry succeeds because the inner `2049-3630` substring is matched by the same `LabelMatcher` pattern (boundary `WORD` line 24) | prefix is not a dedicated matcher, but substring recognition suffices; not a violation |
| language | unset | `en` → `en` | SUCCESS | PASS | `paxman/capabilities/Language/grammar/language_code_recognition.py:46` `LanguageCodeGrammar` (`[A-Za-z]{5,8}|[A-Za-z]{2,3}` line 37) and `bcp47_tag_recognition.py:301` `BCP47TagGrammar` scanner | bcp47 identity |
| language | default | `en` → `en` | SUCCESS | PASS | `paxman/capabilities/Language/grammar/language_code_recognition.py:46` | |
| language | alpha2 | `en` → `en` | SUCCESS `en` | PASS | `paxman/capabilities/Language/grammar/language_code_recognition.py:46` ; `capability.py:186-193` | rendered `en` re-recognized as code |
| language | alpha3 | `en` → `eng` | SUCCESS `eng` | PASS | `paxman/capabilities/Language/grammar/language_code_recognition.py:46` (3-letter) ; `capability.py:195-201` | `eng` term |
| language | alpha3-bib | `en` → `eng` | SUCCESS `eng` | PASS | `paxman/capabilities/Language/grammar/language_code_recognition.py:46` ; `capability.py:203-208` | `eng` bib==term for `en` |
| language | name | `en` → `English` | SUCCESS `English` | PASS | `paxman/capabilities/Language/grammar/language_name_recognition.py:35` `LanguageNameGrammar` ; `capability.py:210-229` | English display name re-recognized via name lexicon |
| mac_address | unset | `00:1A:2B:3C:4D:5E` → `00:1A:2B:3C:4D:5E` | SUCCESS | PASS | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` `MacAddressRecognitionGrammar` (`_EUI48_COLON` line 23) | colon default |
| mac_address | default | `00:1A:2B:3C:4D:5E` → `00:1A:2B:3C:4D:5E` | SUCCESS | PASS | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` | |
| mac_address | bare | `00:1A:2B:3C:4D:5E` → `001A2B3C4D5E` | SUCCESS `001A2B3C4D5E` | PASS | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` (`_BARE12` line 33) ; `capability.py:69-70` | 12-hex bare |
| mac_address | bit_reversed | `00:1A:2B:3C:4D:5E` → `00:58:D4:3C:B2:7A` | SUCCESS but `W=00:1A:2B:3C:4D:5E != V` | **(c) → (b)** | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` handles colon but doc line 89 explicitly: "Bit-reversed spellings are recognized as themselves; no bit-order reinterpretation anywhere." ; `capability.py:78-79` `_bit_reverse_octet` per-octet swap, `format_value` re-applies `bit_reversed` on re-entry so second render flips back to original (involution) | Grammar recognizes `V` as a normal MAC, rule normalizes to `V`'s colon form, then `format_value` with same `bit_reversed` transforms again → `W`. Fix-or-de-offer required (Task 4). |
| mac_address | cisco | `00:1A:2B:3C:4D:5E` → `001A.2B3C.4D5E` | SUCCESS `001A.2B3C.4D5E` | PASS | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` (`_EUI48_DOT` `_HEXTET` line 27) ; `capability.py:71-73` | cisco dot |
| mac_address | eui64 | `00:1A:2B:3C:4D:5E` → `00:1A:2B:FF:FE:3C:4D:5E` | SUCCESS `00:1A:2B:FF:FE:3C:4D:5E` | PASS | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` (`_EUI64_COLON` line 24) ; `capability.py:74-77` inserts `FF:FE` | EUI-64 8-octet |
| mac_address | hyphen | `00:1A:2B:3C:4D:5E` → `00-1A-2B-3C-4D-5E` | SUCCESS `00-1A-2B-3C-4D-5E` | PASS | `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:81` (`_EUI48_HYPHEN` line 25) ; `capability.py:67-68` | |
| money | unset | `45.50 USD` → `USD 45.50` | SUCCESS | PASS | `paxman/capabilities/Money/grammar/code_recognition.py:33` `CodeRecognition` (`AmountComposer` with `AMOUNT_PATTERN`, `BoundaryGuard.word_sign()` line 56) | code_amount identity (`CODE + " " + amount`) |
| money | default | `45.50 USD` → `USD 45.50` | SUCCESS | PASS | `paxman/capabilities/Money/grammar/code_recognition.py:33` | |
| money | compact | `45.50 USD` → `USD45.50` | SUCCESS `USD45.50` | PASS | `paxman/capabilities/Money/grammar/code_recognition.py:33` ; `capability.py:127-131` `replace(" ", "", 1)` — `AmountComposer` accepts `USD500`/`USD 500`/`500 USD` either-order, so `USD45.50` is still a code+amount token; `paxman/capabilities/Money/grammar/__init__.py:AMOUNT_PATTERN` plus `code_recognition.py:51-57` | compact re-recognized despite stripped ASCII space (only ASCII space is separator; `U+202F` narrow NBSP amount shape unaffected) |
| orcid | unset | `0000-0002-1825-0097` → `0000-0002-1825-0097` | SUCCESS | PASS | `paxman/capabilities/ORCID/grammar/orcid_recognition.py:47` `ORCIDRecognitionGrammar` (`_ORCID_BODY` `(\d{4}-\d{4}-\d{4}-\d{3}[\dX])` line 24, `BoundaryGuard.word_only()` line 29) | hyphenated identity |
| orcid | default | `0000-0002-1825-0097` → `0000-0002-1825-0097` | SUCCESS | PASS | `paxman/capabilities/ORCID/grammar/orcid_recognition.py:47` | |
| orcid | compact | `0000-0002-1825-0097` → `0000000218250097` | **MISSING** | **(b)** | `paxman/capabilities/ORCID/grammar/orcid_recognition.py:47` expects hyphenated `(?P<hyphenated>(?ai:\d{4}-\d{4}-\d{4}-\d{3}[\dX]))` line 24 — compact 16-char `0000000218250097` without hyphens does not match; `capability.py:72-73` `notation.compact` strips hyphens; no shipped grammar accepts bare 16-digit ORCID | Fix-or-de-offer required (Task 4). URI precedent `https://orcid.org/...` is recognized via `_ORCID_HOST` line 20. |
| orcid | uri | `0000-0002-1825-0097` → `https://orcid.org/0000-0002-1825-0097` | SUCCESS `https://orcid.org/0000-0002-1825-0097` | PASS | `paxman/capabilities/ORCID/grammar/orcid_recognition.py:47` (`_ORCID_HOST` `(?:https?://)?(?:www\.)?orcid\.org` line 20 + hyphenated body) ; `capability.py:70-71` | URI re-recognized via host prefix |
| phone | unset | `+12125550123` → `+12125550123` | SUCCESS | PASS | `paxman/capabilities/Phone/grammar/e164_recognition.py:113` `E164Grammar` (`ScannerMatcher` `_E164_SCANNER` line 105, `max_window=64` line 41, `BoundarySpec.E164_LEFT`) | E.164 identity |
| phone | default | `+12125550123` → `+12125550123` | SUCCESS | PASS | `paxman/capabilities/Phone/grammar/e164_recognition.py:113` | |
| phone | national | `+12125550123` → `2125550123` | **INVALID** | **(c) → (b)** | Grammar `paxman/capabilities/Phone/grammar/national_recognition.py:45` `NationalGrammar` (`_NATIONAL_BODY` `(?:1[\s.\-]?)?\(?([2-9]\d{2})\)?...` line 35, `BoundaryGuard.phone_national()` line 36) **does** recognize `2125550123` as NANP national shape, but rule `paxman/capabilities/Phone/rules/nanp_ed2024.py:Section1_1NANPStructure` requires `default_country` (contract `default_country=None` line 71 `PhoneContract`) to resolve national-shaped input — original E.164 carried `+1` in digits so `national` output was possible without `default_country` via `split_country_code`, yet bare `2125550123` carries no country code and is `INVALID` without it. `capability.py:148-153` strips `+` and `split_country_code` to produce NSN. | Fix-or-de-offer required (Task 4): either national re-entry must carry country context or be de-offered for country-agnostic contracts. `rfc3966` via `tel_uri_recognition.py:40` `TelUriGrammar` (`tel:+...`) re-enters via `+` so it passes. |
| phone | rfc3966 | `+12125550123` → `tel:+12125550123` | SUCCESS `tel:+12125550123` | PASS | `paxman/capabilities/Phone/grammar/tel_uri_recognition.py:40` `TelUriGrammar` (`_TEL_URI_PATTERN` `tel:`) and `e164_recognition.py:113` (fallback) ; `capability.py:143-147` | `tel:` URI re-recognized |
| si_unit | unset | `kg` → `kg` | SUCCESS | PASS | `paxman/capabilities/SIUnit/grammar/symbol_recognition.py:91` `SymbolRecognition` | symbol identity |
| si_unit | default | `kg` → `kg` | SUCCESS | PASS | `paxman/capabilities/SIUnit/grammar/symbol_recognition.py:91` | |
| url | unset | `https://example.com` → `https://example.com/` | SUCCESS | PASS | `paxman/capabilities/URL/grammar/absolute_uri_recognition.py:115` `AbsoluteUriRecognition` (`ScannerMatcher` `_URL_SCANNER` line 107, `IDNAFold` view) | WHATWG appends `/` |
| url | default | `https://example.com` → `https://example.com/` | SUCCESS | PASS | `paxman/capabilities/URL/grammar/absolute_uri_recognition.py:115` | |

**Summary**

Total param cases exercised: 63 (`("", "default", *sorted(offered))` for each of 17 shipped capabilities; matches `tests/property/test_reentry_invariant.py`'s 63 parametrized rows + 1 hypothesis `test_reentry_case_whitespace_variants` = 64 tests). Total offered formats: 29, passing: 26, failing: 3 (list: `mac_address:bit_reversed`, `orcid:compact`, `phone:national`), default-format failures: 0 (must be 0 per ADR-0010 — satisfied).

Offered-format coverage is complete: every element of `("", "default", *sorted(offered))` for every shipped capability appears above (17 × formats = 63 rows). No offered format omitted. The shipped set is 17 (not 15) — `coordinates` and `mac_address` landed after the plan's Background table was written; both are now included and their offered formats are audited.

**Cross-ref Task 2's 3 red rows**

Task 2 (`uv run pytest tests/property/test_reentry_invariant.py -q` → `3 failed, 61 passed` plus the hypothesis variant) reported exactly the same three failures with identical `V` and status:

- `mac_address-bit_reversed`: `V=00:58:D4:3C:B2:7A`, re-entry `SUCCESS` but `W=00:1A:2B:3C:4D:5E != V` (this audit shows same `V` and the same mismatch via `second.canonicalized_value`).
- `orcid-compact`: `V=0000000218250097`, re-entry `MISSING` (this audit: same `V`, `MISSING`).
- `phone-national`: `V=2125550123`, re-entry `INVALID` (this audit: same `V`, `INVALID` — recognized by `NationalGrammar` but rule-rejected without `default_country`).

No delta: the audit re-derived the full matrix with the same methodology Task 2 uses (same `ROWS` fixtures, same `canonicalize(I,C)` → `canonicalize(V,C)` probe, same default contracts `suppress_common_words=False`) and reproduced the three violations byte-for-byte. No additional suspect format from the plan's Background list (`ISSN urn`, `Date US`, `Money compact`, `Coordinates` non-decimal) failed — those four were green in both Task 2 and this audit (ISSN `urn` via substring match, Date `US` via `DateGrammar` candidates, Money `compact` via `AmountComposer`, Coordinates `dm`/`dms`/`geo_uri`/`geojson_pair`/`iso6709` via single grammar). All other 26 offered formats also passed; all 34 default/unset rows passed.

**Task 4 handoff**

The three (b)/(c)→(b) findings above require Task 4 action per ADR-0010 Consequences: either extend recognition/validation so the rendered form re-enters (e.g., ORCID compact: add 16-digit bare branch to `orcid_recognition.py:22-24` or make `compact` a presentation that re-enters via hyphenated substring; Phone `national`: make re-entry carry country context or restrict `national` to contracts with `default_country`; MacAddress `bit_reversed`: de-offer or make `format_value` idempotent/fixed-point) or de-offer the format from `OFFERED_OUTPUT_FORMATS` with migration note. Passing formats require no Task 4 change.

