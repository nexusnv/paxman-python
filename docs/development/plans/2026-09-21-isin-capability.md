# ISIN Capability Implementation Plan (MILESTONE row 17 / research 2026-08-24, audited 2026-09-20)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship an `isin` capability (23rd) that canonicalizes compact/lowercase/space-grouped/label-prefixed ISIN mentions to compact uppercase 12-char `CC+NSIN+C` with ISO 6166:2021 + ANNA Guidelines V25 provenance — structure+Luhn PARSER plus prefix LOOKUP_TABLE, offered `grouped` display.

**Architecture:** Minimal-surface two-rule capability (1 grammar + 2 rules, BIC/IBAN shape): single `PipelineGrammar` RegexStage grammar (`isin_recognition`, fused `ISIN[\s:-]+` label, single-space-tolerant fixed-count body, BIC-style glued-label guard, `word_only` both sides); PARSER rule for structure + expanded-string Luhn (ISO 6166:2021 Annex C); LOOKUP_TABLE rule for ISO 3166-1 + special prefixes with per-prefix strength split (`ZZ` provisional); `format_value` renders `grouped` 2+6+3+1 as encoding. Registry liveness deferred. Nothing in `paxman/core` or `paxman/engine` changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `tools/new_capability.py` scaffolder, `paxman/core/grammar` PipelineGrammar + StandardPre + RegexStage + BoundaryGuard.

**References:** `docs/development/MILESTONE.md:29` (row 17), `docs/development/research/2026-08-24-isin-canonicalization.md` (§§2–16, audited vectors/tables 2026-09-20), `paxman/capabilities/BIC/grammar/bic_recognition.py:17-48,143-180` (label/guard/pipeline precedent), `paxman/capabilities/BIC/notation.py:9-24`, `paxman/capabilities/BIC/contract.py:12-27`, `paxman/capabilities/BIC/capability.py:23-70`, `paxman/capabilities/BIC/rules/iso_9362_ed2022.py:11-19,283-320`, `paxman/capabilities/IBAN/notation.py:9-34`, `paxman/capabilities/__init__.py:15-38,40-69`, `paxman/api/bootstrap.py:37-60`, `paxman/cli.py:139-230`, `HOW_TO_ADD_NEW_CAPABILITY.md` Steps 0/3/5/6/7/10, `docs/development/plans/2026-09-18-doi-capability.md` (procedural precedent).

**Branch:** `feature/isin-capability` cut from `dev`. PR targets `dev`.

---

## File Structure

- Create (scaffolder, then fill): `paxman/capabilities/ISIN/__init__.py`, `notation.py` — `ISINNotation(country_code, nsin, check_digit, compact)` frozen+slots; `contract.py` — DEFAULT `isin`, OFFERED `{"grouped"}`; `capability.py` — wiring + `format_value`; `grammar/__init__.py`, `grammar/isin_recognition.py` — pattern + guard + `_isin_notation`; `rules/__init__.py`, `rules/iso_6166_ed2021.py` — `Section4IsinStructureCheckDigit` PARSER + `PUBLICATION`; `rules/anna_isin_guidelines_ed2025.py` — `Section5CountryAndSpecialPrefix` LOOKUP_TABLE + `PUBLICATION`; `rules/data/__init__.py`, `rules/data/country_codes.py` — `ISO_3166_1_ALPHA_2` + `SPECIAL_PREFIXES` with strength comments.
- Create (tests): `tests/capabilities/isin/__init__.py`, `test_notation.py`, `test_grammar.py`, `test_rules.py`, `test_capability.py`, `tests/integration/test_isin_pipeline.py`, `tests/property/test_isin_properties.py`.
- Modify: `paxman/capabilities/__init__.py` (import + `__all__` + `_LAZY` + TYPE_CHECKING, alphabetical between IBAN and IP), `paxman/api/bootstrap.py` (`_SHIPPED` import + tuple, alphabetical), `paxman/cli.py` (`isin` branch in `_create_contract`, alphabetical between iban and ip), `tests/unit/test_capability_surface.py` (scaffolder-wired; verify), `tests/property/test_reentry_invariant.py` (ISIN ROWS per ADR-0010), `tests/property/test_output_format_preservation.py` (`("isin","grouped")` encoding + injectivity pair per ADR-0011), `docs/user/capabilities/isin.md` (new) + chooser/index/concepts/api-reference/citations/glossary/migration rows, `README.md` + `CONTEXT.md` tables/Notation, `AGENTS.md` + `paxman/capabilities/AGENTS.md` + `tests/AGENTS.md` counts (22→23), `CHANGELOG.md` (`## [Unreleased]`), README table via `tools/generate_readme_table.py`.
- No `paxman/core`, engine, or `grammar/data/` changes.

---

## Background the implementer needs

### Current state (verbatim)

No ISIN code exists (`paxman/capabilities/__init__.py:15-38` lists 22 exports BIC..UtcOffset with no `ISIN` entry; `_LAZY:40-69` has no ISIN; `paxman/api/bootstrap.py:37-60` `_SHIPPED` has no ISIN; `paxman/cli.py:139-230` `_create_contract` has iban/ip branches with no isin). Closest shipped shapes: BIC single-grammar fused label + glued-label guard + `notation_fn` isascii/isalnum/upper split (`bic_recognition.py:17-48,143-180,151-164`); IBAN four-field sanitized decomposition (`IBANNotation(country_code, check_digits, bban, compact)`); BIC one-file structure+country rule (`iso_9362_ed2022.py:283-320`); DOI minimal-surface plan (1 grammar + 1 rule, 8 tasks).

### Design decisions (locked, from audited research)

1. Canonical compact `isin` uppercase 12 (`CC+NSIN+C`); offered `grouped` renders `CC NNNNNN NNN C` 2+6+3+1 as Paxman presentation convention (not spec-defined), ADR-0011 class **encoding**, re-enters under default contract.
2. One grammar `isin_recognition`, `single_value=True`, no `active_grammars` (always-active; base `None` runs it). Body `[A-Z]{2}(?: ?[A-Z0-9]){9} ?[0-9]` fixed-count; `(?ai:)` ASCII + `re.IGNORECASE`; fused label `(?:(?ai:ISIN)[\s:-]+)?` never zero-width; glued-label guard `(?!(?ai:ISIN[A-Z]{2}[A-Z0-9]{9}[0-9]))` Iceland-safe (`IS…` suffix starts with digit); `word_only` both sides; `notation_fn` strips via `isascii()+isalnum()` + `.upper()`, splits `compact[0:2]/[2:11]/[11]`.
3. Two rules, same `target_semantics=frozenset({"isin_recognition"})`, `requires_features=frozenset()`: PARSER `Section 4-isin-structure-check-digit` (ISO 6166:2021, `https://www.iso.org/standard/78502.html`, version `2021`, active, 2021) owns length/charset/head/tail + expanded-string Luhn (`A=10…Z=35`, weights over expanded string, `(10-sum%10)%10`); LOOKUP_TABLE `Section 5-country-and-special-prefix` (ANNA Guidelines V25 Dec 2025, `.../2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf`, version `2025-12 (V25; superseded by V26 Jun 2026)`, active, 2025, `kind="policy"`) owns prefix set with strength split — Guidelines-attested `EU/XS/XA/XB/XC/XD/XT`, RA-attested `EZ` (briefing + identifiers + DSB), validator/user-assigned `XF/XK/QS/QT` (`XA–XZ`, `QM–QZ`), provisional `ZZ` (no RA source; mark provisional in code comment or exclude from v1). `QW`/retired `CS/YU/SU` excluded.
4. Checksum-verified vectors only: valid `US0378331005`, `AU0000XVGZA3`, `GB0002634946`, `XS0931417173`, `XTV15WLZJMF0`, `FR0000120271`, `PL0000503132` / real `PLPKN0000018`, flaw pair `AU0000VXGZA3`, Iceland `IS0000000008`; invalid checksum `US0378331003`; prefix isolations `XX0378331005`, `ZZ0378331001`. Never use `XS0931417178`, `PL0000503135`, `XX0000XVGZA3`, `ZZ0378331005`, `ISIN03783100`, or isvalid vectors `PL000PKN0RH16`/`DE000A0MR4U4`/`XS1234567890` as valid.
5. Hyphen input → MISSING v1 (zero code-level tolerance); glued `ISINUS0378331005` → MISSING; 11/13-char and letter-check → MISSING; multi-distinct → `MultipleMentionsError`/AMBIGUOUS; registry liveness deferred behind `requires_features` if ever added.
6. `normalize()` returns compact for both rules; rules contain zero `output_format` tokens; `format_value` is the only seam; both rules agree so dedup stays SUCCESS; ADR-0012 standard corroborated case.

---

### Task 1: Scaffold + Notation

**Files:** scaffolder output; fill `paxman/capabilities/ISIN/notation.py`, `tests/capabilities/isin/test_notation.py`

- [ ] Run `uv run python tools/new_capability.py ISIN --name isin --authority "ISO" --spec-name "ISO 6166:2021" --spec-url "https://www.iso.org/standard/78502.html" --publication-year 2021 --spec-version "2021" --default-format isin`. Failing test first: `test_frozen_slots_hash` + `test_compact_decomposition` (`US0378331005` → country `US`/nsin `037833100`/check `5`/compact; `GB0002634946` zeros preserved) → FAIL. Implement `ISINNotation` per research §3.1 (`@dataclass(frozen=True, slots=True)`, all `str`). Verify: `uv run pytest tests/capabilities/isin/test_notation.py -v` → PASS.

### Task 2: Contract

**Files:** `paxman/capabilities/ISIN/contract.py`, `tests/capabilities/isin/test_contract.py` (new; scaffolder emits only `test_capability.py` contract-defaults — add full contract file)

- [ ] Failing tests: `test_default_isin_offered_grouped` + `test_grouped_class_encoding_declared` + `test_unknown_format_contract_error` + `test_suppress_common_words_default_false` → FAIL. Implement `ISINContract` (research §6.1; `@dataclass(frozen=True)` without slots; `DEFAULT_OUTPUT_FORMAT="isin"`, `OFFERED_OUTPUT_FORMATS=frozenset({"grouped"})`, `capability_name="isin"` init=False, no capability-specific params, `__post_init__` calls super; docstring declares `grouped` as encoding). Verify: `uv run pytest tests/capabilities/isin/test_contract.py tests/capabilities/isin/test_capability.py -v` → PASS.

### Task 3: Grammar

**Files:** `paxman/capabilities/ISIN/grammar/isin_recognition.py`, `tests/capabilities/isin/test_grammar.py`
Depends on: Task 1 Notation.

- [ ] Failing tests: `test_compact_span`, `test_lowercase_fold`, `test_spaced_groupings` (`US 037833 100 5`, `US037833 1005`, `PL0000 503132`), `test_outer_whitespace`, `test_label_variants` (`ISIN:`/`isin -`, span includes label, compact bare), `test_quoted_bracketed`, `test_glued_label_missing` (`ISINUS0378331005`), `test_iceland_lookalike` (`IS0000000008` recognized), `test_hyphen_missing`, `test_11_13_missing`, `test_letter_check_missing`, `test_glued_runs_missing` (`XUS…`/`…Y`), `test_homoglyph_missing`, `test_name_semantics_single_value` → FAIL. Implement pattern/`_isin_notation`/`ISINRecognitionGrammar` per decision 2 (PipelineGrammar + StandardPre empty_guard + RegexStage, module-scope string pattern). Verify: `uv run pytest tests/capabilities/isin/test_grammar.py -v` → PASS.

### Task 4: Prefix data table

**Files:** `paxman/capabilities/ISIN/rules/data/__init__.py`, `paxman/capabilities/ISIN/rules/data/country_codes.py`

- [ ] Failing test: `test_prefix_sets_present` (imports `ISO_3166_1_ALPHA_2` + `SPECIAL_PREFIXES`; asserts `{"EU","XS","EZ","XT","XA","XB","XC","XD","XF","XK","QS","QT"}` subset with `ZZ` provisional-marked or absent per decision 3; asserts `QW` absent) → FAIL. Implement plain module-level frozensets with per-prefix provenance comments + refresh procedure (Guidelines V25→V26 + DSB + ISO 3166 OBP + validator snapshots; `ZZ` provisional note). Verify: `uv run pytest tests/capabilities/isin/test_rules.py -k prefix_sets -v` → PASS (full file green in Task 5).

### Task 5: Rules (both publications)

**Files:** `paxman/capabilities/ISIN/rules/iso_6166_ed2021.py`, `paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py`, `tests/capabilities/isin/test_rules.py`
Depends on: Tasks 1, 4.

- [ ] Failing tests: `test_parser_valid` (`US0378331005`, `AU0000XVGZA3`, `GB0002634946`, `XS0931417173`, `XTV15WLZJMF0`), `test_parser_bad_checksum` (`US0378331003`), `test_flaw_pair_both_valid`, `test_z35_expansion`, `test_lookup_valid_prefixes` (US/GB/XS/EZ/XK), `test_lookup_rejects_isolations` (`XX0378331005`, `ZZ0378331001`), `test_lookup_rejects_qw`, `test_normalize_agreement`, `test_provenance_attrs` (ISO/6166:2021/78502/2021/specification/active; ANNA/Guidelines/V25/policy/2025), `test_strategy_six_attrs`, `test_no_output_format_token` → FAIL. Implement both Rule classes (research §5.2 names/citations; `matches`/`normalize` never raise; `normalize` returns compact). Verify: `uv run pytest tests/capabilities/isin/test_rules.py tests/unit/test_rule_output_format_purity.py -v` → PASS.

### Task 6: Capability wiring + registration

**Files:** `paxman/capabilities/ISIN/capability.py`, `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`, `paxman/cli.py`, `tests/capabilities/isin/test_capability.py`
Depends on: Tasks 1–3, 5.

- [ ] Failing tests: `test_wiring_counts` (1 grammar, 2 rules), `test_create_contract_common_block` (excluded/pinned/year/output/extra/suppress order + defaults), `test_format_value_grouped` (`US0378331005` → `US 037833 100 5`; default identity), `test_cli_isin_branch`, `test_shipped_contains_isin` → FAIL. Implement `get_grammars`/`get_rules`/`create_contract`/`format_value` (research §6.2) + `__init__` import/`__all__`/`_LAZY`/TYPE_CHECKING (alphabetical IBAN→ISIN→IP) + `_SHIPPED` import/tuple (alphabetical) + cli `isin` branch (alphabetical iban→isin→ip). Verify: `uv run pytest tests/capabilities/isin/test_capability.py tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v` → PASS.

### Task 7: Integration + invariants

**Files:** `tests/integration/test_isin_pipeline.py`

- [ ] Failing tests: SUCCESS rows (all §2 surface variants coalesce to compact), INVALID rows (bad checksum, `XX`/`ZZ` isolations), MISSING rows (no runs, hyphenated, glued label, 11/13, letter check, homoglyphs), AMBIGUOUS/`MultipleMentionsError` (two distinct ISINs; identical coalesce), `test_excluded_prefix_rule_false_success`, `test_pinned_year_filter`, span integrity, candidate dedup, determinism/VersionStamp → FAIL, then pass via Tasks 3/5/6 code (autouse `_clean_registry`). Verify: `uv run pytest tests/integration/test_isin_pipeline.py -q` → PASS.

### Task 8: Property + re-entry + preservation

**Files:** `tests/property/test_isin_properties.py`, `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py`

- [ ] Failing tests: synthesized-valid self-canonicalization (prefix from union set + random alnum NSIN + computed check), random-printable MISSING/INVALID no-crash, spaced-vs-compact equivalence, `grouped` round-trip strips to compact; re-entry ROWS (`_row(ISIN, "US0378331005", "US0378331005")` + grouped fixed point); preservation `CLASS_MAP[("isin","grouped")]=encoding` + injectivity pair → FAIL, then pass (no new impl expected). Verify: `uv run pytest tests/property/test_isin_properties.py tests/property/test_reentry_invariant.py tests/property/test_output_format_preservation.py -q` → PASS.

### Task 9: Docs + counts

**Files:** `docs/user/capabilities/isin.md`, chooser/index/concepts/api-reference/citations/glossary/migration, `README.md`, `CONTEXT.md`, `AGENTS.md`, `paxman/capabilities/AGENTS.md`, `tests/AGENTS.md`, `CHANGELOG.md`

- [ ] Guide `isin.md` (recognition table with corrected vectors, statuses incl. DEFER/REJECT rows, executed snippet, ISO 6166:2021 + Guidelines V25 provenance with strength split + V26 note, no code/shipped-doc refs to `docs/development/` per its AGENTS.md) + chooser/index/concepts/api-reference/citations/glossary/migration rows + `tools/generate_readme_table.py` run (diff limited to ISIN row) + README/CONTEXT tables (`| **ISIN** | International securities identification numbers | ISO 6166:2021 |` + Notation subsection) + AGENTS counts 22→23 + CHANGELOG `Unreleased` Added entry. Verify: snippet outputs executed not assumed; `uv run pytest tests/unit/test_capability_exports.py -q` → PASS.

### Task 10: Full gate + PR

**Files:** none (verify + handoff).

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q && uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → all green (pre-existing `dev` findings excluded by stashed-baseline comparison). Commit `feat(isin): ISIN capability (ISO 6166:2021 + ANNA V25)`, review with `paxman-oracle-review` then open PR against `dev`.

---

Plan saved to docs/development/plans/2026-09-21-isin-capability.md — 10 tasks.

Execute task-by-task via tdd (failing test first). After impl, run paxman-momus-review on the plan file, then paxman-oracle-review on the branch diff before PR handoff.
