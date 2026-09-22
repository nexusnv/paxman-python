# LEI Post-Implementation Review Fixes (oracle review FAIL, 2 blocking + 3 minor findings)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Turn the `feature/lei-capability` oracle verdict from FAIL to PASS by (1) fixing the CRITICAL all-digit-LEI `INVALID` bug that makes the property suite red, (2) resolving the GLEIF-URL-embedded contradiction as **recognized — amend docs** (user decision), (3) fixing the three minor docs findings, and (4) filing one GitHub Issue per purposefully-deferred LEI behavior so nothing deferred is lost track of.

**Architecture:** Two `Rule.matches()` guards change (`isupper()` half removed — `_LEI_RE`'s `[A-Z0-9]` already enforces uppercase; `isascii` kept). No grammar, contract, notation, engine, or core change. Docs amendments align plan/research/guide text with the already-measured `word_only` URL-embedded SUCCESS behavior (ISIN precedent). Deferred behaviors are externalized as tracked GitHub Issues, referenced from the guide and research. `format_value`, provenance, and registration are untouched.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `gh` CLI for issue filing.

**References:** `docs/development/plans/2026-09-22-lei-capability.md` (Task 7 MISSING row being amended; decision 2 `word_only`), `docs/development/research/2026-09-22-lei-canonicalization.md` §2 row (DEFER), §2.1 (scope-cut must be stated in guide), §8 row 18 (URL-embedded → v1 MISSING), §15 (does-not-carve claim), `paxman/capabilities/LEI/rules/iso_17442_1_ed2020.py:88`, `paxman/capabilities/LEI/rules/gleif_lou_prefix_list_ed2026.py:83`, `tests/property/test_lei_properties.py:97-105` (`test_synthesized_valid_leis_self_canonicalize`, currently FAIL: `prefix='1128', entity='00000000000000'`), `tests/integration/test_lei_pipeline.py:145` (glued-URL surrogate row), `docs/user/capabilities/lei.md` (recognition table + statuses), `CONTEXT.md:89-91`, `AGENTS.md` / `paxman/capabilities/AGENTS.md` prose lists + `paxman/capabilities/AGENTS.md:4`, ISIN precedent `paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py:81`, ADR-0012, ADR-0010.

**Branch:** `fix/lei-post-review` cut from `feature/lei-capability` (same PR before handoff), PR targets `dev`.

---

## File Structure

- Modify: `paxman/capabilities/LEI/rules/iso_17442_1_ed2020.py` — remove `not compact.isupper()` from `matches()` (line 88), keep `isascii`
- Modify: `paxman/capabilities/LEI/rules/gleif_lou_prefix_list_ed2026.py` — same fix (line 83)
- Test: `tests/capabilities/lei/test_rules.py` — `test_parser_digit_only_lei_accepted`, `test_lookup_digit_only_lei_accepted`
- Test: `tests/integration/test_lei_pipeline.py` — `test_digit_only_lei_success` (SUCCESS row) + replace glued-URL MISSING row context and add `test_gleif_url_embedded_success` (exact research §2 URL)
- Test: `tests/property/test_lei_properties.py` — no edit; must pass from a clean `.hypothesis` state
- Modify: `docs/development/plans/2026-09-22-lei-capability.md` — Task 7 MISSING row "GLEIF-URL-embedded" corrected to SUCCESS
- Modify: `docs/development/research/2026-09-22-lei-canonicalization.md` — §2 row, §8 row 18, §15 sentence, §13 row 9/11 note
- Modify: `docs/user/capabilities/lei.md` — URL-embedded recognized row + composition statement + deferred-issues links
- Modify: `CONTEXT.md` — LEI table row moved below ISSN
- Modify: `AGENTS.md`, `paxman/capabilities/AGENTS.md` — `Language, LEI, MacAddress` order; `paxman/capabilities/AGENTS.md:4` py-file count
- Modify: `CHANGELOG.md` — Fixed entry for the digit-only bug
- Create: GitHub Issues via `gh` (2 deferred-behavior tracking issues, no repo files)

No `paxman/core`, engine, grammar, contract, or notation change.

---

## Background the implementer needs

### Finding 1 — CRITICAL (verbatim reproducer)

```python
compact = "1128" + "0" * 14 + "02"   # prefix "1128" ∈ ACCREDITED_LOU_PREFIXES,
                                      # MOD 97-10 remainder == 1, regex passes
compact.isupper()                     # → False  (no cased characters!)
```

Both `Rule.matches()` do `if not compact.isascii() or not compact.isupper(): return False`.
`str.isupper()` is `False` for digit-only strings, so a spec-valid all-numeric LEI
(ISO 17442-1 charset `[A-Z0-9]` requires NO letters) fails both rules → pipeline
`INVALID`. 145 of 17,846 snapshot prefixes are digit-only, so the cell is reachable.
Proof: `uv run pytest tests/property/test_lei_properties.py -q` → FAIL
(`prefix='1128', entity='00000000000000'`); full suite `1 failed, 5590 passed`.

Why the ISIN copy is safe and LEI is not: ISIN always contains a 2-letter country
code, so `isupper()` is always `True` there (`anna_isin_guidelines_ed2025.py:81`).
LEI has no such guaranteed cased character. The guard is redundant regardless —
`_LEI_RE = ^[A-Z0-9]{18}[0-9]{2}$` already rejects lowercase, and the grammar
uppercases; keep only the `isascii()` half (defense against e.g. fullwidth digits
that a stray direct call could pass).

### Finding 2 — MAJOR, resolution LOCKED (user decision: recognized — amend docs)

Measured on `feature/lei-capability`:

| Input | Status | Span |
|---|---|---|
| `https://search.gleif.org/#/record/5493000IBP32UQZ0KL24` (research §2 example) | `SUCCESS` `5493000IBP32UQZ0KL24` | (34, 54) |
| `https://lei.bloomberg.com/lei/5493000IBP32UQZ0KL24` | `SUCCESS` | (30, 50) |
| `https://www.isin.org/detail.html/?isin=US0378331005` (ISIN precedent) | `SUCCESS` | (39, 51) |
| `https://www.gleif.org/lei-data213800KUD8LAJWSQ9D15` (current test row) | `MISSING` (glued label — unrelated to URL) | — |

Locked decision: `word_only` boundaries (plan decision 2) stand; `/` and `#` are
word boundaries, so URL-path-embedded LEIs are recognized, matching ISIN precedent
and the URL-capability composition story. The plan Task 7 row, research §8 row 18,
and research §15 "does not carve" sentence are amended to say **recognized**;
`lei.md` gains the recognition row + composition statement (research §2.1 requires
the treatment be stated explicitly either way). The glued-URL test row stays as a
glued-label case (relabel its comment) and a new SUCCESS row pins the exact
research §2 URL so the measured behavior is locked, not drift-able.

### Design decisions (locked)

1. Fix = delete the `not compact.isupper()` clause in BOTH rule files; keep `not compact.isascii()`. No regex, grammar, or normalization change. `_LEI_RE` remains the uppercase authority.
2. URL-embedded = recognized; amend texts, add SUCCESS test; no grammar change.
3. Deferred behaviors get GitHub Issues NOW (user requirement), each linked from `lei.md` statuses and cited in the research §13 open-decision note: (a) hyphen-grouped LEI recognition via community `extra_grammars`, (b) issued/live (liveness) membership. Each issue body records the research citation, the v1 status (`MISSING`/deferred), and the extension seam.
4. Provenance, contract, `format_value`, registration, and counts are untouched by this plan (they passed the oracle review).

---

### Task 1: Reproduce + fix the digit-only `isupper()` bug

**Files:** `tests/capabilities/lei/test_rules.py`, `paxman/capabilities/LEI/rules/iso_17442_1_ed2020.py:88`, `paxman/capabilities/LEI/rules/gleif_lou_prefix_list_ed2026.py:83`

- [ ] Failing tests first: `test_parser_digit_only_lei_accepted` — build `LEINotation` for `"1128" + "0"*14 + "02"` (prefix in snapshot, remainder 1; assert `_mod97_10_valid` in the test setup so the fixture is self-evident) → assert `Section4LEIStructureMOD9710().matches(n, LEIContract()) is True` → FAIL (current `isupper()` gate). `test_lookup_digit_only_lei_accepted` — same notation → assert `Section1LOUPrefixMembership().matches(...) is True` → FAIL. Run: `uv run pytest tests/capabilities/lei/test_rules.py -k digit_only -v` → Expected: FAIL ×2.
- [ ] Fix both rules: replace `if not compact.isascii() or not compact.isupper():` with `if not compact.isascii():` (line 88 in `iso_17442_1_ed2020.py`, line 83 in `gleif_lou_prefix_list_ed2026.py`); add a one-line comment: `# isascii only — isupper() is False for digit-only LEIs, which [A-Z0-9] permits (review finding 1)`.
- [ ] Verify: `uv run pytest tests/capabilities/lei/test_rules.py -k digit_only -v` → PASS; `uv run pytest tests/capabilities/lei -q` → PASS.

### Task 2: Pipeline + property green (end-to-end proof)

**Files:** `tests/integration/test_lei_pipeline.py`

- [ ] Failing integration test first: `test_digit_only_lei_success` — `paxman.canonicalize("11280000000000000002", contract)` → `Resolution.SUCCESS`, value `"11280000000000000002"` → FAIL before Task 1's fix, PASS after. Run: `uv run pytest tests/integration/test_lei_pipeline.py::TestLEIPipelineSuccess -k digit_only -v` → PASS (add to the success parametrize list or as its own test — own test, since it carries the review-finding comment).
- [ ] Prove the property suite recovers from scratch: `rm -rf .hypothesis && uv run pytest tests/property/test_lei_properties.py -q` → PASS (all 5, including `test_synthesized_valid_leis_self_canonicalize`).
- [ ] Run the previously-red full suite: `uv run pytest -q` → PASS (was `1 failed, 5590 passed`).
- [ ] Commit: `fix(lei): accept digit-only valid LEIs — isupper() guard rejected cased-less strings`.

### Task 3: URL-embedded — align tests with the locked decision

**Files:** `tests/integration/test_lei_pipeline.py:131-149`

- [ ] Relabel the existing MISSING row comment at line 145 from `# glued URL` to `# glued label inside a URL — MISSING via the glued-label guard, not URL context` (behavior unchanged: still `MISSING`).
- [ ] Add `test_gleif_url_embedded_success` (in `TestLEIPipelineSuccess`): `paxman.canonicalize("https://search.gleif.org/#/record/5493000IBP32UQZ0KL24", contract)` → `SUCCESS`, value `5493000IBP32UQZ0KL24`, `span == (34, 54)` — the exact research §2 example, so the recognized-by-design behavior is pinned.
- [ ] Verify: `uv run pytest tests/integration/test_lei_pipeline.py -q` → PASS.

### Task 4: Amend plan + research + guide texts

**Files:** `docs/development/plans/2026-09-22-lei-capability.md`, `docs/development/research/2026-09-22-lei-canonicalization.md`, `docs/user/capabilities/lei.md`

- [ ] `2026-09-22-lei-capability.md` Task 7: change the MISSING row list entry `GLEIF-URL-embedded` to a SUCCESS row note: "URL-path-embedded LEI → SUCCESS (word_only decision 2; ISIN precedent) — amended per oracle review 2026-09-22".
- [ ] Research §2 row (line ~50): DEFER → RECOGNIZED with the measured evidence; §8 row 18: `v1 MISSING` → `v1 SUCCESS (word_only boundary; URL capability composes on top)`; §15 line ~107: replace "the LEI capability in v1 does not carve codes out of them" with "URL-path-embedded LEIs are recognized via word_only boundaries (ISIN precedent); URL-level semantics remain the URL capability's ownership"; §13 row 11: append resolution note "URL-embedded half resolved 2026-09-22 — RECOGNIZED (oracle review finding 2); hyphen half remains DEFER per row 9".
- [ ] `lei.md`: add recognition-table row `URL-path-embedded (`https://search.gleif.org/#/record/5493000IBP32UQZ0KL24`)` under Recognizes; add statuses row `URL-path-embedded LEI | defaults | SUCCESS | carved at the `/`/`#` boundary — URL-level semantics belong to the URL capability`; in the deferred section link the two GitHub Issues from Task 5 (hyphen-grouped, issued/live). Re-execute the guide snippet + new row values and paste measured output (no assumed values).
- [ ] Verify: `rg -n "docs/development" docs/user/capabilities/lei.md` → 0 hits (guide never cites dev docs — its AGENTS.md rule; issue links are GitHub issue URLs, which are allowed); snippet executed via `uv run python`.

### Task 5: GitHub Issues for every purposefully-deferred LEI behavior

**Files:** none in repo (gh CLI only); links land in `lei.md` (Task 4)

- [ ] `gh issue create --repo nexusnv/paxman-python --title "LEI: recognize hyphen-grouped forms via community extra_grammars" --body "Deferred from LEI v1 (research 2026-09-22-lei-canonicalization §13 row 9 — 'Hyphen tolerance | DEFER to community extension' — and §13 row 11 / §2.1; plan 2026-09-22-lei-capability decision 6). v1 status: MISSING (e.g. 5493-000I-BP32-UQZ0-KL24). Extension seam: community grammar via contract extra_grammars (paxman/core/extensions.py register_grammar). No grouping convention attested in ISO 17442-1 — implementation must cite attestation before shipping in-tree." --label enhancement` → record issue URL.
- [ ] `gh issue create --repo nexusnv/paxman-python --title "LEI: issued/live membership validation (liveness-aware contract feature)" --body "Deferred from LEI v1 (research 2026-09-22-lei-canonicalization §5.4 — 'Recommendation: deferred behind a future include_issued_validation-gated LOOKUP_TABLE (mirrors ISIN #179)' — and §7.2; plan 2026-09-22-lei-capability decision 6). v1 stance: liveness is not validity — structure + MOD 97-10 + accredited-prefix snapshot → SUCCESS regardless of issue status. Any liveness check needs a requires_features-gated rule + snapshot refresh story; must not add network inference to the deterministic pipeline (AGENTS.md determinism rule)." --label enhancement` → record issue URL.
- [ ] Verify: `gh issue list --repo nexusnv/paxman-python --search "LEI in:title" --state open` shows both; URLs pasted into `lei.md` (Task 4).

### Task 6: Minor docs findings + changelog + full gate

**Files:** `CONTEXT.md:89-91`, `AGENTS.md`, `paxman/capabilities/AGENTS.md:4`, `CHANGELOG.md`

- [ ] `CONTEXT.md`: move the `| **LEI** | Legal entity identifiers | ISO 17442-1:2020 |` row from between ISIN (89) and ISSN (91) to after `Language` (92), matching README's order.
- [ ] Prose lists in `AGENTS.md` (OVERVIEW + NOTES) and `paxman/capabilities/AGENTS.md` OVERVIEW: reorder `…, ISSN, LEI, Language, MacAddress, …` → `…, ISSN, Language, LEI, MacAddress, …` (case-insensitive order those lists already used; matches README table and `bootstrap._SHIPPED`).
- [ ] `paxman/capabilities/AGENTS.md:4`: recount — `find paxman/capabilities -name "*.py" | wc -l` and write that number (325 at review time) instead of `303`.
- [ ] `CHANGELOG.md` `## [Unreleased]` → `### Fixed` bullet: digit-only valid LEIs no longer resolve `INVALID` (the `isupper()` guard); plus a `### Docs` note for the URL-embedded clarification.
- [ ] Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q && uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → all green (repo-wide `uv run ruff check .` still fails 11 pre-existing `learnings/serve.py` findings from `dev` — excluded per baseline comparison; do not fix them in this branch).
- [ ] Commit: `fix(lei): review follow-ups — digit-only guard, URL-embedded docs, deferred-issue links`. Re-run `paxman-oracle-review` on the branch diff; verdict expected PASS, then PR against `dev`.

---

## Self-review

- Spec coverage: CRITICAL finding → Tasks 1-2; MAJOR finding → Tasks 3-4; user's deferred-issue requirement → Task 5; three MINOR findings + changelog → Task 6. ✔
- Placeholder scan: no `TBD`/`TODO`/`appropriate`/`similar to Task N`. ✔
- Type consistency: no signature changes anywhere; `LEINotation`/`LEIContract` untouched. ✔
- Momus dry-run: every reference exists with file:line; every QA block names a command + expected outcome; branch declared; both decisions locked. ✔
