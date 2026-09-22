# LEI Capability Implementation Plan (MILESTONE §2A row 6 / research 2026-09-22)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a `lei` capability (24th) that canonicalizes compact/lowercase/single-spaced/`LEI:`-labeled/`urn:lei:`-carried LEI mentions to compact uppercase 20-char `LOU4+entity14+check2` with ISO 17442-1:2020 + GLEIF LOU-prefix provenance — structure+MOD-97-10 PARSER plus prefix LOOKUP_TABLE, offered `urn` carrier.

**Architecture:** Minimal-surface two-rule capability (1 grammar + 2 rules, ISIN shape): single `PipelineGrammar` RegexStage grammar (`lei_recognition`, fused `LEI[\s:-]+` label, optional `urn:lei:` carrier branch, fixed-count single-space interleave, full-shape glued-label guard, `word_only` both sides); PARSER rule for structure + whole-string MOD 97-10 (ISO 17442-1:2020, ISO/IEC 7064 cited normatively); LOOKUP_TABLE rule for accredited-LOU prefix against an append-only snapshot; `format_value` renders `urn:lei:<compact>` as carrier-only re-encoding. Issued/live membership deferred. Nothing in `paxman/core` or `paxman/engine` changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `tools/new_capability.py` scaffolder, `paxman/core/grammar` PipelineGrammar + StandardPre + RegexStage + BoundaryGuard.

**References:** `docs/development/MILESTONE.md:58` (row 6 — prose claims "no check digit", contradicted by research §5.1/§7.1), `docs/development/research/2026-09-22-lei-canonicalization.md` (§§2–16, five mod97-verified vectors, §4.2 pattern, §5.2 rule map, §6 contract), `paxman/capabilities/ISIN/grammar/isin_recognition.py:20-34,37-46` (body/guard/notation_fn precedent), `paxman/capabilities/ISIN/rules/iso_6166_ed2021.py:56-90` (PARSER shape), `paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py:57-92` (LOOKUP full-conjunction precedent), `paxman/capabilities/ISIN/contract.py:37-40` + `paxman/capabilities/ISIN/capability.py:32-44,45-79,81-96` (contract/wiring/format precedent), `paxman/capabilities/ORCID/capability.py:58-74` + `paxman/capabilities/ORCID/contract.py:19-22` (`uri`/`compact` offered-format precedent), `paxman/capabilities/ORCID/grammar/orcid_recognition.py:22-35` (label+carrier+guard precedent), `paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py:50-62` (mod97 accumulator shape — copy, never import), `paxman/capabilities/IBAN/grammar/iban_recognition.py:76-84` (glued-reject precedent), `paxman/core/domain.py:236-271` (Rule six-attr enforcement), `paxman/engine/orchestrator.py:456,543,621-673,811` (dedup/affinity/single-value/candidate-dedup), `paxman/capabilities/__init__.py:15-39,41-71`, `paxman/api/bootstrap.py:38-62`, `paxman/cli.py:193-200` (language→mac_address insertion point), `HOW_TO_ADD_NEW_CAPABILITY.md` Steps 0/3/5/6/7/10, `docs/development/plans/2026-09-21-isin-capability.md` (procedural precedent).

**Branch:** `feature/lei-capability` cut from `dev`. PR targets `dev`.

---

## File Structure

- Create (scaffolder, then fill/rename): `paxman/capabilities/LEI/__init__.py`, `notation.py` — `LEINotation(lou_prefix, entity_block, check_digits, compact)` frozen+slots; `contract.py` — DEFAULT `lei`, OFFERED `{"urn"}`; `capability.py` — wiring + `format_value`; `grammar/__init__.py`, `grammar/lei_recognition.py` — pattern + guard + `_lei_notation` + `LEIRecognitionGrammar` (+ `LEIRecognition` alias); `rules/__init__.py`, `rules/iso_17442_1_ed2020.py` — `Section4LEIStructureMOD9710` PARSER + `PUBLICATION` (renamed from scaffolder `rules/iso_ed2020.py`); `rules/gleif_lou_prefix_list_ed2026.py` — `Section1LOUPrefixMembership` LOOKUP_TABLE + `PUBLICATION`; `rules/data/__init__.py`, `rules/data/lou_prefixes.py` — `ACCREDITED_LOU_PREFIXES` append-only frozenset with per-prefix provenance comments + refresh procedure.
- Create (tests): `tests/capabilities/lei/__init__.py`, `test_notation.py`, `test_contract.py` (full contract file; scaffolder emits only capability-level contract-defaults), `test_grammar.py`, `test_rules.py`, `test_capability.py`, `tests/integration/test_lei_pipeline.py`, `tests/property/test_lei_properties.py`.
- Modify: `paxman/capabilities/__init__.py` (import + `__all__` + `_LAZY` + TYPE_CHECKING, alphabetical between Language and MacAddress), `paxman/api/bootstrap.py` (`_SHIPPED` import + tuple, alphabetical between Language and MacAddress), `paxman/cli.py` (`lei` branch in `_create_contract`, alphabetical between language and mac_address), `tests/unit/test_capability_surface.py` (scaffolder-wired; verify), `tests/property/test_reentry_invariant.py` (LEI ROWS per ADR-0010), `tests/property/test_output_format_preservation.py` (`("lei","urn")` encoding + injectivity pair per ADR-0011), `docs/user/capabilities/lei.md` (new) + chooser/index/concepts/api-reference/citations/glossary/migration rows, `README.md` + `CONTEXT.md` tables/Notation, `AGENTS.md` + `paxman/capabilities/AGENTS.md` + `tests/AGENTS.md` counts (23→24), `CHANGELOG.md` (`## [Unreleased]`), `docs/development/MILESTONE.md:58` (row 6 prose correction), README table via `tools/generate_readme_table.py`.
- No `paxman/core`, engine, or `grammar/data/` changes.

---

## Background the implementer needs

### Current state (verbatim)

No LEI code exists (`paxman/capabilities/__init__.py:15-39` lists 23 exports BIC..UtcOffset with no `LEI` entry; `_LAZY:41-71` has no LEI; `paxman/api/bootstrap.py:38-62` `_SHIPPED` has no LEI; `paxman/cli.py:193-200` has language/mac_address branches with no lei). Closest shipped shapes: ISIN single-grammar fused label + glued-label guard + `notation_fn` isascii/isalnum/upper split (`isin_recognition.py:20-46`); ISIN four-field sanitized decomposition (`ISINNotation(country_code, nsin, check_digit, compact)`); ISIN one-file-per-publication PARSER+LOOKUP pair with full-conjunction LOOKUP (`iso_6166_ed2021.py:56-90`, `anna_isin_guidelines_ed2025.py:57-92`); ORCID label+carrier+guard with `uri` offered format (`orcid_recognition.py:22-35`, `ORCID/capability.py:58-74`); IBAN whole-string-adjacent mod97 accumulator (`iso_13616_1_ed2020.py:50-62`, rearranged — LEI copies the shape without rearrangement). Scaffolder emits 13 files plus `__init__.py`/surface wiring with `--default-format` default `canonical` (`tools/new_capability.py:451,706-749`).

### Design decisions (locked, from research)

1. Canonical compact `lei` uppercase 20 (`LOU4+entity14+check2`, `^[A-Z0-9]{18}[0-9]{2}$`); offered `urn` renders `urn:lei:<compact>` as carrier-only re-encoding, ADR-0011 class **encoding** (exact pre-image via the carrier branch; matches `("uuid","urn")`/`("issn","urn")`/`("orcid","uri")` precedent — research §6.1 wording says "expansion" but the measured behavior is carrier-only re-encoding, so classify as encoding).
2. One grammar `lei_recognition`, `single_value=True`, no `active_grammars` (always-active; base `None` runs it). Core `[A-Z0-9](?: ?[A-Z0-9]){17}(?: ?[0-9]){2}` fixed-count (1+17+2 = 20 payload chars, never 19/21); `(?ai:)` ASCII + `re.IGNORECASE`; fused label `(?:(?ai:LEI)[\s:-]+)?` never zero-width; optional carrier `(?:(?ai:urn:lei:))?`; full-shape glued-label guard `(?!(?ai:LEI[A-Z0-9]{18}[0-9]{2}))` (23-char glued label blocked, bare 20-char code starting `LEI` unaffected); `word_only` both sides; `notation_fn` strips via `isascii()+isalnum()` + `.upper()`, splits `compact[0:4]/[4:18]/[18:20]`.
3. Two rules, same `target_semantics=frozenset({"lei_recognition"})`, `requires_features=frozenset()`: PARSER `Section 4-lei-structure-mod97-10` (ISO 17442-1:2020, `https://www.iso.org/standard/78829.html`, version `2020`, active, 2020, `kind="specification"`) owns length/charset/decomposition + whole-string MOD 97-10 (`A=10…Z=35`, iterative `% 97 == 1`, no rearrangement; ISO/IEC 7064:2003 cited normatively in the module docstring, not split); LOOKUP_TABLE `Section 1-lou-prefix-membership` (GLEIF LOU prefix list, concatenated-file download URL, version `Rolling`, active, 2026, `kind="registry"`) owns prefix membership with full-conjunction re-validation (ADR-0012 one-directional corroboration). Positions 5–6 never reject (`7LTWFZYICNSX8D621K86` carries `FZ`). Checksum helper is a local copy, never an IBAN import.
4. LOU snapshot `ACCREDITED_LOU_PREFIXES` is append-only (codes survive LOU retirement/transfer; never delete). Seed by GLEIF accredited-LOU directory + concatenated-file prefix census at build time; `2138`/`5493`/`5067`/`7LTW` must be present; never hand-invent prefixes. Refresh procedure in the data-module header (re-census, add-only).
5. Checksum-verified vectors only: valid `213800KUD8LAJWSQ9D15`, `5493000IBP32UQZ0KL24`, `213800WSGIIZCXF1P572`, `506700GE1G29325QX363`, `7LTWFZYICNSX8D621K86` (non-`00` pin); generation `213800D1L3R2MWV39G`→`88`; invalid checksum `213800KUD8LXJWSQ9D15` (remainder 55). MILESTONE row 6 example compact `5493001KJTIIGC8Y1R12` stays; only its "no check digit" prose is corrected.
6. Hyphen input → MISSING v1 (deferred to community `extra_grammars`); double-space/tab → MISSING; glued `LEI5493…` → MISSING; 19/21-char → MISSING; multi-distinct → `MultipleMentionsError`/AMBIGUOUS; issued/live membership deferred (liveness≠validity).
7. `normalize()` returns compact for both rules; rules contain zero `output_format` tokens; `format_value` is the only seam; both rules agree so dedup stays SUCCESS; ADR-0012 standard corroborated case.

---

### Task 1: Scaffold + Notation

**Files:** scaffolder output; fill `paxman/capabilities/LEI/notation.py`, `tests/capabilities/lei/test_notation.py`

- [ ] Run `uv run python tools/new_capability.py LEI --name lei --authority "ISO" --spec-name "ISO 17442-1:2020" --spec-url "https://www.iso.org/standard/78829.html" --publication-year 2020 --spec-version "2020" --default-format lei`, then rename scaffolder `rules/iso_ed2020.py` to `rules/iso_17442_1_ed2020.py` (fix the capability import). Failing test first: `test_frozen_slots_hash` + `test_compact_decomposition` (`213800KUD8LAJWSQ9D15` → lou `2138`/entity `00KUD8LAJWSQ9D`/check `15`/compact; `5493000IBP32UQZ0KL24` zeros preserved) → FAIL. Implement `LEINotation` per decision 2 (`@dataclass(frozen=True, slots=True)`, all `str`). Verify: `uv run pytest tests/capabilities/lei/test_notation.py -v` → PASS.

### Task 2: Contract

**Files:** `paxman/capabilities/LEI/contract.py`, `tests/capabilities/lei/test_contract.py`

- [ ] Failing tests: `test_default_lei_offered_urn` + `test_urn_class_encoding_declared` + `test_unknown_format_contract_error` + `test_suppress_common_words_default_false` → FAIL. Implement `LEIContract` (`@dataclass(frozen=True)` without slots; `DEFAULT_OUTPUT_FORMAT="lei"`, `OFFERED_OUTPUT_FORMATS=frozenset({"urn"})`, `capability_name="lei"` init=False, no capability-specific params, `__post_init__` calls super; docstring declares `urn` as encoding). Verify: `uv run pytest tests/capabilities/lei/test_contract.py tests/capabilities/lei/test_capability.py -v` → PASS.

### Task 3: Grammar

**Files:** `paxman/capabilities/LEI/grammar/lei_recognition.py`, `tests/capabilities/lei/test_grammar.py`
Depends on: Task 1 Notation.

- [ ] Failing tests: `test_compact_span`, `test_lowercase_fold`, `test_single_spaced` (`5493 000IBP32UQZ0KL24`), `test_outer_whitespace`, `test_label_variants` (`LEI:`/`lei `/`LEI-`, span includes label, compact bare), `test_urn_carrier` (`urn:lei:`/`URN:LEI:`, span includes carrier), `test_quoted_bracketed_csv`, `test_glued_label_missing` (`LEI5493000IBP32UQZ0KL24`), `test_bare_lei_prefix_code` (`LEI…` 20-char still recognized), `test_double_space_tab_missing`, `test_hyphen_missing`, `test_19_21_missing`, `test_glued_runs_missing` (`X…`/`…Y`), `test_homoglyph_missing`, `test_name_semantics_single_value` → FAIL. Implement pattern/guard/`_lei_notation`/`LEIRecognitionGrammar` per decision 2 (PipelineGrammar + StandardPre empty_guard + RegexStage, module-scope string pattern, `LEIRecognition` alias). Verify: `uv run pytest tests/capabilities/lei/test_grammar.py -v` → PASS.

### Task 4: LOU prefix data table

**Files:** `paxman/capabilities/LEI/rules/data/__init__.py`, `paxman/capabilities/LEI/rules/data/lou_prefixes.py`

- [ ] Failing test: `test_prefix_set_present` (imports `ACCREDITED_LOU_PREFIXES`; asserts `{"2138","5493","5067","7LTW"}` subset; asserts append-only header documents re-census + never-delete) → FAIL. Implement plain module-level frozenset with per-prefix provenance comments + refresh procedure (GLEIF directory + concatenated-file census, add-only; no hand-invented entries). Verify: `uv run pytest tests/capabilities/lei/test_rules.py -k prefix_set -v` → PASS (full file green in Task 5).

### Task 5: Rules (both publications)

**Files:** `paxman/capabilities/LEI/rules/iso_17442_1_ed2020.py`, `paxman/capabilities/LEI/rules/gleif_lou_prefix_list_ed2026.py`, `tests/capabilities/lei/test_rules.py`
Depends on: Tasks 1, 4.

- [ ] Failing tests: `test_parser_valid` (all five §vectors), `test_parser_non00_accepted` (`7LTWFZYICNSX8D621K86`), `test_parser_bad_checksum` (`213800KUD8LXJWSQ9D15`), `test_parser_generation_vector` (`213800D1L3R2MWV39G88` valid), `test_lookup_valid_prefixes` (2138/5493/5067/7LTW), `test_lookup_rejects_unknown_prefix` (checksum-valid fabricated prefix), `test_lookup_rejects_bad_checksum_valid_prefix`, `test_normalize_agreement`, `test_provenance_attrs` (ISO/17442-1:2020/78829/2020/specification/active; GLEIF/prefix-list/Rolling/registry/2026), `test_strategy_six_attrs`, `test_no_output_format_token` → FAIL. Implement both Rule classes per decisions 3/7 (`matches`/`normalize` never raise; `normalize` returns compact; local `_expand`/`_mod97_10_valid`, no cross-capability import). Verify: `uv run pytest tests/capabilities/lei/test_rules.py tests/unit/test_rule_output_format_purity.py -v` → PASS.

### Task 6: Capability wiring + registration

**Files:** `paxman/capabilities/LEI/capability.py`, `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`, `paxman/cli.py`, `tests/capabilities/lei/test_capability.py`
Depends on: Tasks 1–3, 5.

- [ ] Failing tests: `test_wiring_counts` (1 grammar, 2 rules), `test_create_contract_common_block` (excluded/pinned/year/output/extra/suppress order + defaults), `test_format_value_urn` (`5493000IBP32UQZ0KL24` → `urn:lei:5493000IBP32UQZ0KL24`; default identity), `test_urn_reentry_via_carrier` (rendered URN re-recognizes to the same compact), `test_cli_lei_branch`, `test_shipped_contains_lei` → FAIL. Implement `get_grammars`/`get_rules`/`create_contract`/`format_value` + `__init__` import/`__all__`/`_LAZY`/TYPE_CHECKING (alphabetical Language→LEI→MacAddress) + `_SHIPPED` import/tuple (alphabetical) + cli `lei` branch (alphabetical language→lei→mac_address). Verify: `uv run pytest tests/capabilities/lei/test_capability.py tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v` → PASS.

### Task 7: Integration + invariants

**Files:** `tests/integration/test_lei_pipeline.py`

- [ ] Failing tests: SUCCESS rows (all §2 RECOGNIZE variants coalesce to compact, incl. label/URN spans), INVALID rows (bad checksum, unknown-prefix with valid checksum), MISSING rows (no runs, hyphenated, glued label, 19/21, double-space/tab, homoglyphs, GLEIF-URL-embedded), AMBIGUOUS/`MultipleMentionsError` (two distinct LEIs; identical coalesce), `test_excluded_lou_rule_false_success`, `test_pinned_year_filter` (`year=2019` filters the 2020 ISO rule → ADR-0012 vacuity), span integrity, candidate dedup, determinism/VersionStamp → FAIL, then pass via Tasks 3/5/6 code (autouse `_clean_registry`). Verify: `uv run pytest tests/integration/test_lei_pipeline.py -q` → PASS.

### Task 8: Property + re-entry + preservation

**Files:** `tests/property/test_lei_properties.py`, `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py`

- [ ] Failing tests: synthesized-valid self-canonicalization (prefix from snapshot + random 14-char block + computed check digits), random-20-char INVALID high-probability no-crash, spaced-vs-compact equivalence, `urn` round-trip strips to compact; re-entry ROWS (`_row(LEI, "5493000IBP32UQZ0KL24", "5493000IBP32UQZ0KL24")` + non-`00` row); preservation `CLASS_MAP[("lei","urn")]=encoding` + injectivity pair (`5493000IBP32UQZ0KL24` vs `213800KUD8LAJWSQ9D15`) + expansion-fixture non-membership → FAIL, then pass (no new impl expected). Verify: `uv run pytest tests/property/test_lei_properties.py tests/property/test_reentry_invariant.py tests/property/test_output_format_preservation.py -q` → PASS.

### Task 9: Docs + counts + MILESTONE correction

**Files:** `docs/user/capabilities/lei.md`, chooser/index/concepts/api-reference/citations/glossary/migration, `README.md`, `CONTEXT.md`, `AGENTS.md`, `paxman/capabilities/AGENTS.md`, `tests/AGENTS.md`, `CHANGELOG.md`, `docs/development/MILESTONE.md:58`

- [ ] Guide `lei.md` (recognition table with the five verified vectors, statuses incl. DEFER/REJECT rows, executed snippet, ISO 17442-1:2020 + GLEIF prefix-list provenance, no code/shipped-doc refs to `docs/development/` per its AGENTS.md) + chooser/index/concepts/api-reference/citations/glossary/migration rows + `tools/generate_readme_table.py` run (diff limited to LEI row) + README/CONTEXT tables (`| **LEI** | Legal entity identifiers | ISO 17442-1:2020 |` + Notation subsection) + AGENTS counts 23→24 + CHANGELOG `Unreleased` Added entry + MILESTONE row 6 prose fix ("20-char alphanumeric with LOU prefix and 2 MOD 97-10 check digits" + ISO 17442-1:2020; keep the example vector). Verify: snippet outputs executed not assumed; `uv run pytest tests/unit/test_capability_exports.py -q` → PASS.

### Task 10: Full gate + PR

**Files:** none (verify + handoff).

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q && uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → all green (pre-existing `dev` findings excluded by stashed-baseline comparison). Commit `feat(lei): LEI capability (ISO 17442-1:2020 + GLEIF LOU list)`, review with `paxman-oracle-review` then open PR against `dev`.

---

Plan saved to docs/development/plans/2026-09-22-lei-capability.md — 10 tasks.

Execute task-by-task via tdd (failing test first). After impl, run paxman-momus-review on the plan file, then paxman-oracle-review on the branch diff before PR handoff.
