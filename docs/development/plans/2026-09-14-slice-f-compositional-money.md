# Slice F — Compositional Wave 2 (#148) + Money $ Constrain (#15)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Broaden the compositional description tables from the 3-entry minimum (traditional/simplified/singapore) to a curated Wave 2 of major scripts + single-token regions (closing #148 under an updated completeness contract), and constrain Money's `dollar_sign_currency` to the symbol's own candidate codes per the ratified #15 ruling (parity with Currency).

**Architecture:** Data-only Language extension through the existing slot machinery (no grammar/rule logic changes: new keys flow through `_match_backward/_match_forward` ≤2-token slots into `SectionIANARegistryDescription` via `DESCRIPTION_DISPLAY_MAP`, pinned by `TestDescriptionDisplayDataCovered`); Money gets the two-line membership guard mirroring Currency's `candidate in codes` locus. No contract/engine/core changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest, IANA Language Subtag Registry Descriptions (File-Date 2026-08-08, per-entry verification by implementer).

**References:** Issues #148 (Wave 2), #15 (ratified constrain ruling — decision comment 2026-09-14); `paxman/capabilities/Language/grammar/language_description_recognition.py:39-40,61-64` (extension rule + 2-token slot cap); `grammar/data/script_names.py:13-22` + `region_names.py:13-22` (Wave-2 follow-up pointers); `rules/data/description_display_map.py:23-25` (pairing rule); `rules/data/iana_script_subtags.py` / `iana_region_subtags.py` (shipped-set membership authority); `tests/capabilities/language/test_data_consistency.py:117-146` (pairing/normalization/membership pins); `paxman/capabilities/Money/rules/cldr_currencies_ed2025.py:70-75,98-105` (unguarded resolvers); `Currency/rules/cldr_currencies_ed2025.py:63-64` (guard precedent); `tests/capabilities/money/test_rules.py`, `test_capability.py`, `tests/integration/test_money_pipeline.py` (locked vectors); `README.md:319,336-337,504`, `docs/user/capabilities/money.md:18-20,58,65,72-80,98` (divergence prose + examples).

**Branch:** `feature/slice-f-compositional-money` (cut from `dev` — already exists).

---

## File Structure

- Modify: `paxman/capabilities/Language/grammar/data/script_names.py` — Wave-2 script keys (data only).
- Modify: `paxman/capabilities/Language/grammar/data/region_names.py` — Wave-2 single-token region keys (data only).
- Modify: `paxman/capabilities/Language/rules/data/description_display_map.py` — mirror entries (data only).
- Modify: `paxman/capabilities/Money/rules/cldr_currencies_ed2025.py:75,105` — candidate-membership guard (2 lines).
- Test: `tests/capabilities/language/test_grammar.py` / `test_rules.py` — Wave-2 phrase vectors + collision-class pins.
- Test: `tests/capabilities/money/test_rules.py`, `test_capability.py`, `tests/integration/test_money_pipeline.py` — `$`+non-candidate → INVALID updates.
- Docs: `docs/user/capabilities/language.md` (recognized forms + statuses), `docs/user/capabilities/money.md:20,65` (parity rewrite), `README.md:336-337,504` (opt-in semantics), `CHANGELOG.md`.
- No grammar/rule/contract/engine/core logic changes.

---

## Background the implementer needs

### Current state (verbatim)

#148 tables are the 3-entry minimum. `SCRIPT_DISPLAY_KEYS = {"traditional", "simplified"}` → Hant/Hans; `REGION_DISPLAY_KEYS = {"singapore"}` → SG. Both file headers declare curated-subset completeness and point Wave-2 at #148. Extension machinery is proven: keys (≤2 normalized tokens — `_MAX_SLOT_TOKENS = 2`, `:61-64`) flow through positional slots into `SectionIANARegistryDescription`, which maps via `DESCRIPTION_DISPLAY_MAP` and validates against the shipped IANA sets; `TestDescriptionDisplayDataCovered` (`:117-146`) pins key↔entry pairing, normalized form, and shipped-set membership. Any key without a map entry fails loudly; any map value outside shipped sets fails loudly.

#15 divergence is two unguarded lines. Money `_resolve_symbol_code` (`:75`) and `_resolve_name_code` (`:105`) return `contract.dollar_sign_currency` unchecked, so `$500`+`MYR` → `SUCCESS "MYR 500.00"` while Currency's identical opt-in shape guards with `candidate if candidate in codes else None` (`Currency/rules/cldr_currencies_ed2025.py:63-64`), so `$`+`MYR` → `INVALID`. The ratified ruling (issue comment, Sep 2026): Money mirrors Currency — resolution only to the token's own candidate codes. `money.md:20` documents the divergence with a #15 link and must be rewritten to parity; `money.md:65,72-80,98` + `README.md:336-337` show `MYR` resolving and must flip.

### Design decisions (locked)

1. **Wave 2 = curated, not full-registry.** Scripts: latin→Latn, cyrillic→Cyrl, arabic→Arab, devanagari→Deva, greek→Grek, hebrew→Hebr (unambiguous majors, all pre-shipped in `iana_script_subtags.py`) PLUS the armenian→Armn collision-class pin (script display name identical to a language name — positional slots disambiguate; explicit test required). `thai→Thai` is EXCLUDED from Wave 2: `Thai` is absent from the shipped script set, and admitting it would require extending the validation authority (newly validating `th-Thai`-family tags — behavior beyond descriptions), so it stays on #148 with the multi-token regions. Regions: at least 8 single-token majors (e.g. germany→DE, france→FR, japan→JP, china→CN, india→IN, brazil→BR, canada→CA, australia→AU). Every entry verified against the IANA Registry Description by the implementer (File-Date 2026-08-08); mapped values must already sit in the shipped IANA sets (consistency tests enforce it — no new authority).
2. **Collision audit per candidate, three lists.** Each Wave-2 key is checked against (a) `COMMON_WORDS` (67), (b) `ENGLISH_LANGUAGE_KEYS` + `LOCALIZED_LANGUAGE_KEYS` (same-string collisions like armenian get explicit positional tests, never silent admission), (c) existing display keys across both sets (script/region overlap like a future "georgian" stays out unless disambiguated by test). Any hit is either an explicit test or a rejection with reason logged on #148.
3. **Multi-token regions deferred with reason.** `united states`→US and kin stay out: 2-token keys are legal for slots but the string carries Country-sentinel history (`test_derived_keys.py` pins it out of name keys) — admitting it into region slots needs its own disambiguation design, not a drive-by. Logged on #148, not orphaned.
4. **Paren forms ride free, tested anyway.** New keys automatically work in `(<Script>[, <Region>])` / `(<Region>)` via shared slots (`:17-18`); each task includes one paren vector per new key class (e.g. `German (Latin)`, `Japanese (Japan)` — success only if the composition validates; implementer runs, never assumes).
5. **Money guard mirrors Currency's locus exactly.** Membership tested against the token's own `codes` tuple (not the global code set); non-member → `None` → `INVALID`. Single-candidate definitiveness, `None`-default → INVALID, and contract-shape `ContractError`s unchanged. Re-entry: `MYR 500.00` (qualified code form) still re-enters; only the bare-`$`+opt-in path changes status.
6. **#148 closes on Wave 2.** File headers update counts + completeness contract (curated Wave 2, subset semantics unchanged: uncovered displays stay `MISSING`, never false-negative). Further entries follow the header extension rule with no issue needed. #150 stays out (wontfix-pending), #71.3-4/#73 L3 stay out (design-gated), #154 stays out (monitor-only).

### Deferral → issue map

| Deferred matter | Home issue |
|---|---|
| Multi-token regions (`united states`→US), `thai→Thai` (needs validation-authority expansion), further scripts/regions | #148 (logged at close-out; header extension rule governs) |
| Money single-separator heuristic | #150 (untouched) |
| Orchestrator/view tightenings, combinator L3 | #71 / #73 (design-gated) |
| Flake | #154 (monitor-only) |
| Tracker bookkeeping | #146 (release-time) |

---

### Task 1: #15 — constrain `dollar_sign_currency` to own candidates

**Files:** `paxman/capabilities/Money/rules/cldr_currencies_ed2025.py:75,105`, `tests/capabilities/money/test_rules.py`, `test_capability.py`, `tests/integration/test_money_pipeline.py`, `README.md:336-337,504`, `docs/user/capabilities/money.md:20,65,72-80,98`

**Goal:** `$`+non-candidate opt-in → `INVALID`; `$`+candidate, single-candidate, and default-`None` paths unchanged.

- [ ] Failing tests first: `$500`+`dollar_sign_currency="MYR"` → `INVALID` (FAILS today as `SUCCESS "MYR 500.00"`); `$500`+`"USD"` → `SUCCESS "USD 500.00"` (already green, pinned); qualified `RM500`+`MYR` → `SUCCESS` (green, pinned). Run targeted → RED on the MYR vector.
- [ ] Implement: membership guard in both resolvers (`candidate = contract.dollar_sign_currency; return candidate if candidate in codes else None`). Update locked vectors + README opt-in example (`MYR`→`USD` at :336-337) + `money.md:20` divergence note rewritten to parity (+:65 semantics, :72-80 snippet, statuses). Verify: `uv run pytest tests/capabilities/money tests/integration/test_money_pipeline.py -q` → PASS; `uv run pytest -m property -q -k "money or reentry"` → PASS; ruff/pyright clean.

### Task 2: #148 — Wave-2 script table

**Files:** `grammar/data/script_names.py`, `rules/data/description_display_map.py`, `tests/capabilities/language/test_grammar.py` / `test_rules.py`

**Goal:** `German in Latin script` → `SUCCESS de-Latn`-family composition (exact tag per rule mapping); `Armenian in Armenian script` → deterministic composition without language/script confusion; uncovered scripts (`Mongolian in Runic`?) stay `MISSING`.

- [ ] Failing tests first: `in`-form + paren-form vectors for each new script key (the 6 majors + armenian pin) → FAIL as `MISSING` today. Collision audit table (COMMON_WORDS × name keys × display keys) recorded in test comments or #148 thread.
- [ ] Implement: keys + map entries (IANA-verified each) + header count/contract update. Verify: `uv run pytest tests/capabilities/language tests/unit/test_derived_keys.py -q` → PASS; description re-entry spot-checks green; ruff/pyright clean.

### Task 3: #148 — Wave-2 single-token region table

**Files:** `grammar/data/region_names.py`, `rules/data/description_display_map.py`, `tests/capabilities/language/test_grammar.py` / `test_rules.py`

**Goal:** `German in Germany` → `SUCCESS de-DE`-family composition; `Japanese (Japan)` paren form → `SUCCESS`; multi-token `German in United States` stays `MISSING` (deferred by design).

- [ ] Failing tests first: `in`-form + paren vectors for each of the ≥8 region keys → FAIL as `MISSING` today; `united-states` deferral vector asserting `MISSING` (already green, pinned as design).
- [ ] Implement: keys + map entries (IANA-verified each) + header update. Verify: same suites → PASS; consistency pins green; ruff/pyright clean.

### Task 4: Integrate + gate + close-out

**Files:** `docs/user/capabilities/language.md`, `CHANGELOG.md`

- [ ] `language.md`: recognized-forms rows for Wave-2 scripts/regions (+ collision-class note for armenian-type overlaps), statuses table additions (all vectors executed). CHANGELOG Unreleased/Fixed: #148 Wave 2 + #15 constrain. Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest` → green; coverage ≥95. Close-out comments: #148 (Wave-2 entry list + audit log + multi-token deferral — closable), #15 (guard locus + flipped vectors — closable). Commit per task.
