# Slice B — Compositional Language + BIC Filter + Decision Notes (issues #148, #106, #15, #150)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Close the two recognition-correctness holes where grammars misread ordinary English (`Singapore Chinese in traditional script` → `id`; bare `call me at` → BIC) and record the two behavior rulings gating future Money work (`$` policy, single-separator grouping).

**Architecture:** One new Language grammar (`language_description_recognition`, custom `recognize()` on `PipelineGrammar` per the BIC precedent — slot-filling over three vocabularies fits no kernel matcher kind) declaring the shipped `bcp47_tag` semantics id (HOWTO Option A: zero rule-logic edits; `SectionIANARegistry`/`SectionBCP47Syntax` already validate fielded notations and assemble identical tags); BIC fix stays inside `recognize()` post-filter with word lists derived from `COMMON_WORDS`; #15/#150 ship as researched ruling comments (no code).

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration), `paxman/capabilities/Language`, `paxman/capabilities/BIC`, `HOW_TO_ADD_NEW_GRAMMAR.md` Steps 2–7.

**References:** Issues #148, #106, #15, #150, #147 (B4 follow-up), #145 (guide row); `paxman/capabilities/Language/grammar/language_code_recognition.py:36-54`; `paxman/capabilities/Language/notation.py:23-50`; `paxman/capabilities/Language/capability.py:94-100`; `paxman/capabilities/BIC/grammar/bic_recognition.py:42-99,140-188`; `paxman/core/grammar/engine_loop.py:146-166` (A0 exemption); `HOW_TO_ADD_NEW_GRAMMAR.md` Steps 1/4/5; `docs/user/capabilities/language.md:11-175`; `docs/user/capabilities/money.md:18-20`.

**Branch:** `feature/slice-b-compositional-bic` (cut from `dev` — already exists).

---

## File Structure

- Modify: `paxman/capabilities/BIC/grammar/bic_recognition.py` — derive `_COMMON_SHORT_WORDS` from `COMMON_WORDS`, end-of-text English filter (#106).
- Test: `tests/capabilities/bic/test_grammar.py`, `tests/integration/test_bic_grouped.py` — end-of-text + punctuation vectors.
- Create: `paxman/capabilities/Language/grammar/language_description_recognition.py` — compositional grammar, identity semantics `language_description`, display-valued fields (#148).
- Modify: `paxman/capabilities/Language/rules/iana_language_subtag_registry_ed2026.py` — add `SectionIANARegistryDescription` rule class (same publication).
- Test: `tests/capabilities/language/test_grammar.py`, new/updated rule tests for the description rule, `test_data_consistency.py` (extend key↔map coverage).
- Create: `paxman/capabilities/Language/grammar/data/script_names.py`, `region_names.py` — hand-maintained display-name KEY sets (unmarked files: edited directly per capabilities governance; IANA provenance headers).
- Create: `paxman/capabilities/Language/rules/data/description_display_map.py` — hand-maintained display→subtag authority mapping (keys live in grammar/data; mapping lives here — english_language_map.py precedent, but that file is GENERATED-locked so this is a separate file).
- Modify: `paxman/capabilities/Language/capability.py:94-100` — append grammar to `get_grammars()`.
- Test: `tests/capabilities/language/test_grammar.py`, `test_data_consistency.py` (extend key↔map coverage), `tests/integration/test_language_capability.py`.
- Docs: `docs/user/capabilities/language.md` (recognized-forms row + AMBIGUOUS-under-default note), `docs/user/capabilities/money.md:20` (one-line divergence truth), `CHANGELOG.md`.
- No new modules outside Language/BIC. No `paxman/core` changes. No contract-flag changes.

---

## Background the implementer needs

### Current state (verbatim)

Bare-code matcher claims 2–3 letters anywhere (`language_code_recognition.py:36-43`):

```python
_MATCHER = RegexMatcher(
    pattern=r"[A-Za-z]{5,8}|[A-Za-z]{2,3}",
    boundary=BoundarySpec.WORD_SIGN,
    ...
    suppressible=True,
)
```

`in` validates via the deprecated map (`rules/iso_639_2_ed1998.py:54-56` → `DEPRECATED_MAP[lang]`, LOOKUP strategy), so the sentence yields `SUCCESS id` even post-ADR-0012. The IANA rule validates fielded notations directly (`iana_language_subtag_registry_ed2026.py:176-195` script/region set checks) and assembles tags from fields (`:226-260`); `SectionBCP47Syntax.normalize` returns `compact` verbatim (`bcp47_rfc5646_ed2009.py:365+`) — so a composed notation with canonical-case `compact` plus matching fields validates identically under both rules with no rule edits.

Suppression (the sanctioned prose mechanism) lives only on the kernel path with the A0 whole-input exemption (`engine_loop.py:146-166`); `LanguageCodeGrammar` rides it via `matchers`, `in`/`is`/`at`/`me` are all in `COMMON_WORDS` (67, verified), `call`/`xenon`/`noon` are not.

BIC filter gap (`bic_recognition.py:175-186`): the English-phrase branch requires `after.startswith(" ") and after.lstrip()[:1].isalnum()`, so end-of-text and punctuation-terminated trigrams slip through; `_COMMON_SHORT_WORDS` (31 hardcoded) drifts from `COMMON_WORDS` (67).

### Design decisions (locked)

1. **#148 default-contract outcome is AMBIGUOUS (pinned, documented) — not SUCCESS.** The engine preserves cross-grammar matches (no precedence layer; B1 established that needs an ADR) and ADR-0012 corroboration keeps the deprecated-map `id` (LOOKUP-backed). Compositional + `id` therefore resolve AMBIGUOUS under the default contract — recorded as progress (no false provenance) with `suppress_common_words=True` yielding `SUCCESS zh-Hant-SG`. Default-contract narrowing stays in #147 (B4). Both outcomes pinned by integration tests.
2. **HOWTO Option B — new rule class in the IANA file (amended 2026-09-13: Option A rejected at implementation).** Option A required the grammar to emit code-valued fields, which forced a display→code mirror into grammar code — authority data in the recognition layer, contradicting capabilities governance with no shipped precedent (BIC/Currency grammars never map token→canonical). Instead: the grammar declares identity semantics `language_description` and emits display-valued fields; new class `SectionIANARegistryDescription` (`name = "Section-iana-registry-description"`) in `rules/iana_language_subtag_registry_ed2026.py` (same publication, one-file-per-publication rule) maps via `description_display_map` + validates against the IANA sets and normalizes to the canonical tag (strategy LOOKUP_TABLE, `requires_features` empty). Zero duplication (single map, real consumer), no dual-rule agreement problem (only the new rule targets the new id). Span erratum: full-phrase span of the acceptance sentence is `(0, 39)`, not `(0, 38)`.
3. **Custom `recognize()` on `PipelineGrammar` (BIC precedent).** Slot-filling over three vocabularies with word-order variants fits no kernel matcher kind (HOWTO Step 1 table). Supported forms: `<Language> in <Script> [script]`, `<Language> in <Region>`, `<Region> <Language> in <Script> [script]`. Parenthesized `<Language> (<Script>, <Region>)` deferred (stays in #148). New grammar emits full-phrase spans only — never bare-word spans — so it needs no suppression machinery of its own; it must not disturb the A0 exemption (guard: `tests/unit/test_b1_common_word_suppression.py` green).
4. **Curated-subset tables, same completeness contract as the 60-name set.** Script keys `{traditional, simplified}`, region keys `{singapore}` — the acceptance-required minimum, IANA-sourced, extension = add key pair + consistency test stays green. Grammar/data holds KEYS only; subtag mappings live in the new rules/data file (separation gate enforced). `english_names.py` and `english_language_map.py` are GENERATED-locked — do not touch; new files are hand-maintained. Synthetic `names.py` fixtures (B7) must not leak into the new key sets.
5. **#106 keeps the `isupper()` gate.** Only the end-of-text/punctuation hole is fixed; `CALL ME AT` (structurally valid BIC: bank CALL, country ME) keeps its status quo. Rationale: minimal delta — the reported bug is the unguarded tail, not the case policy. Record the considered alternative on #106.
6. **#15/#150 ship as ruling comments, zero code.** Money/Currency divergence (Currency guards `candidate in codes`, `cldr_currencies_ed2025.py:64`; Money accepts any minor-units code) and single-separator always-decimal (`parsing.py:41-56` + locked `test_data.py` table) are maintainer decisions with locale/provenance trade-offs. Deliverable: researched ruling text posted to each issue (+ `money.md:20` one-line truth fix for #15). Any resulting code change is a later slice.

### Deferral → issue map (every deferral has a home)

| Deferred matter | Home issue (stays open, linked back) |
|---|---|
| Default-contract sentence still AMBIGUOUS; `Xenon`-class bare-code narrowing (B4) | #147 (B4 item, already tracked) |
| Parenthesized description forms; broader script/region tables | #148 itself (partial completion noted on close-out) |
| `isupper()` removal / exotic-BIC trade-off | #106 (decision recorded in close-out comment) |
| Combinator unambiguous-leaf constraint on the new grammar (L3) | #73 (L3, already tracked) |
| `language.md` compositional row if docs task slips | #145 (guides umbrella, already tracked) |
| Code changes implementing #15/#150 rulings | #15 / #150 themselves |

---

### Task 1: #106 — end-of-text English filter + word-list unification

**Files:** `paxman/capabilities/BIC/grammar/bic_recognition.py:42-99,175-186`, `tests/capabilities/bic/test_grammar.py`, `tests/integration/test_bic_grouped.py`

**Goal:** Bare and punctuated English trigrams stop recognizing; valid BICs byte-identical.

- [ ] Failing tests: `recognize("call me at") == []`, `recognize("BIC call me at") == []`, `recognize("call me at.") == []`; guards: `recognize("deut de ff today")` keeps 1 match, `canonicalize("please call me at noon")` stays MISSING, full current grouped vectors unchanged. Run: `uv run pytest tests/capabilities/bic tests/integration/test_bic_grouped.py -q` → FAIL on the new three.
- [ ] Implement: import `COMMON_WORDS` from `paxman.core.grammar.data.common_words`; derive `_COMMON_SHORT_WORDS` as the COMMON_WORDS short-word subset UNION an explicit documented remainder (prove zero delta: existing suites green); extend the English-phrase branch with an end-of-text/punctuation-only `after` arm (`after.strip(" .,:;!?") == ""`); keep the `isupper()` gate per decision 5. Verify: new tests PASS; `uv run pytest tests/capabilities/bic tests/integration -q` → PASS; ruff/pyright clean.

### Task 2: #148 — display-name data tables + consistency coverage

**Files:** `paxman/capabilities/Language/grammar/data/script_names.py`, `region_names.py` (create), `paxman/capabilities/Language/rules/data/description_display_map.py` (create), `tests/capabilities/language/test_data_consistency.py`

**Goal:** Separated key↔mapping tables with provenance, every key backed by a mapping.

- [ ] Failing test: extend `test_data_consistency.py` — every key in the new script/region key sets has a mapping entry; every mapping value is in the shipped IANA script/region sets; grammar/data imports nothing from rules (separation assertion mirrors the existing module). Run: targeted test → FAIL (files missing).
- [ ] Implement: `SCRIPT_DISPLAY_KEYS = {"traditional", "simplified"}`, `REGION_DISPLAY_KEYS = {"singapore"}` (normalize_name-keyed, IANA provenance headers, subset disclaimer + extension rule); `DESCRIPTION_DISPLAY_MAP = {"traditional": "Hant", "simplified": "Hans", "singapore": "SG"}` in rules/data with IANA registry provenance header (hand-maintained — NOT via the locked generator). Verify: consistency tests PASS; `uv run pytest tests/capabilities/language/test_data_consistency.py -q` → PASS.

### Task 3: #148 — compositional grammar + description rule (HOWTO Option B)

**Files:** `paxman/capabilities/Language/grammar/language_description_recognition.py` (create/rework), `paxman/capabilities/Language/rules/iana_language_subtag_registry_ed2026.py` (append rule class), `paxman/capabilities/Language/capability.py:94-100`, `tests/capabilities/language/test_grammar.py`, `tests/capabilities/language/test_rules.py`

**Goal:** Full-phrase description recognition with display-valued fields, validated by a dedicated same-publication rule.

- [ ] Failing grammar tests: `Singapore Chinese in traditional script` → one match, span `(0, 39)`, notation carrying display slots (language `chinese`, script `traditional`, region `singapore`); `Chinese in simplified script`; `Chinese in Singapore`; negatives: `Xenon is a gas` → `[]`, bare `in` → `[]`, lone `Chinese` → `[]`. Failing rule tests: `Section-iana-registry-description` maps slots via `description_display_map`, validates codes against the IANA script/region/language sets, normalizes to `zh-Hant-SG`; unknown display slot → no match. Run: targeted tests → FAIL.
- [ ] Implement: `LanguageDescriptionGrammar(PipelineGrammar[LanguageNotation])`, `name = "language_description_recognition"`, `semantics = "language_description"` (identity id); custom `recognize()` doing normalized slot parse (normalize_name on segments; language slot against `ENGLISH_LANGUAGE_KEYS`; `in` as literal separator; optional trailing `script`); emit full-phrase spans only, NO display→code mirror tables in grammar code (grammar tables stay key-only); rule class with the six enforced metadata attrs (`name = "Section-iana-registry-description"`, strategy LOOKUP_TABLE, same-file PUBLICATION, `target_semantics = {"language_description"}`, `requires_features` empty); wire grammar into `get_grammars()` and rule into `get_rules()`. Depends on: Task 2 tables. Verify: grammar + rule tests PASS; `test_b1_common_word_suppression.py` + full `tests/capabilities/language` green.

### Task 4: #148 — integration outcomes + `language.md` row

**Files:** `tests/integration/test_language_capability.py`, `docs/user/capabilities/language.md` (recognized-forms table)

**Goal:** Pin both contract modes; document the compositional forms.

- [ ] Failing integration tests: default contract `Singapore Chinese in traditional script` → AMBIGUOUS (decision 1, pinned); `suppress_common_words=True` → `SUCCESS zh-Hant-SG`; same-flag `Xenon is a gas` → INVALID (claimed-but-unvalidated — `xenon`/`gas` match the bare-code shape but no rule validates them; MISSING requires zero recognitions; narrowing in #147); `zh-Hant-SG` re-entry fixed point; `Chinese` → `SUCCESS zh` unchanged. Run: `uv run pytest tests/integration/test_language_capability.py -q` → FAIL.
- [ ] Implement: no source change expected (wiring from Task 3 should suffice — if any test fails beyond the AMBIGUOUS/SUCCESS split, stop and re-analyze rather than bending the grammar); docs row: compositional forms + per-contract outcome table. Depends on: Task 3. Verify: integration PASS; snippet claims (if any added) executed via `uv run python`.

### Task 5: Decision notes #15 + #150 (+ `money.md:20` truth fix)

**Files:** none (issue comments) + `docs/user/capabilities/money.md:20` (one line)

**Goal:** Researched, evidence-linked rulings a maintainer can ratify or redirect.

- [ ] Post to #15: ruling note covering (a) constrain Money to candidate codes, (b) relax Currency, (c) document divergence — with evidence cites (`cldr_currencies_ed2025.py:64` vs Money `:75-116`, `money.md:18-20`), provenance argument, and recommended option + resulting code sketch for the later slice. Post to #150: ruling note covering locale-free grouping heuristic vs wontfix (locale ambiguity with no locale input, locked `test_data.py` table, determinism, existing Limitations section) with recommendation. Fix `money.md:20` ("same semantics" → documented divergence + issue link); verify wording against observed `$`+MYR behavior under both capabilities via `uv run python`.
- [ ] QA: both comments posted (links recorded here on completion); `money.md` claim re-verified by execution; no source diff. Code changes (if any option wins) are explicitly out — they stay in #15/#150.

### Task 6: CHANGELOG + full gate

**Files:** `CHANGELOG.md` (Unreleased/Fixed)

- [ ] Entries: #106 filter fix, #148 compositional grammar (incl. default-AMBIGUOUS contract note), #15/#150 ruling notes. Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest` → all green (note: pre-existing `learnings/serve.py` F401s are out of scope — gate on `paxman/ tests/` per Tasks 1–4, full-repo `ruff check .` reported separately); coverage ≥95 on `paxman/core, paxman/capabilities, paxman/engine, paxman/api`. Commit per task; close-out comments on #106/#148 (with deferral links per the map above) when landing.
