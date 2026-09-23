# GTIN Capability Implementation Plan (MILESTONE row 14 / research 2026-09-22)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a `gtin` capability (25th) that canonicalizes compact/space-grouped/hyphenated/labeled/AI-wrapped GTIN-8/12/13/14 mentions to 14-digit zero-padded canonical with GS1 GenSpecs 26.0 + Prefix provenance — Mod-10 PARSER plus always-active prefix LOOKUP_TABLE, offered `native` + `hri`, Verified-liveness LOOKUP_TABLE gated behind `include_verified=False`.

**Architecture:** Minimal-surface three-rule capability (1 grammar + 3 rules, ISBN shape): single `PipelineGrammar` LabelMatcher grammar (`gtin_recognition`, separator-tolerant exact-length alternation, fused `GTIN/UPC/EAN` labels + `(01)`/`AI 01` branch, label/AI-strip emit, glued-`reject`, WORD guards); PARSER GenSpecs structure + Mod-10; always-active LOOKUP prefix on native digits (never padded); gated LOOKUP Verified snapshot; `normalize()` returns `rjust(14,"0")` from all three rules; `format_value` renders `native` via the facet and `hri` via confirmed groupings (narrow to `{"native"}` if EAN groupings stay unconfirmed — Task 6 decides, no invented groupings). Nothing in `paxman/core` or `paxman/engine` changes.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `tools/new_capability.py` scaffolder, `paxman/core/grammar` PipelineGrammar + StandardPre + LabelMatcher + BoundarySpec.

**References:** `docs/development/MILESTONE.md:73` (row 14 — example `590 1234 12345 7`→`5901234123457` is 13-digit; research decides 14-digit canonical `05901234123457`, Mod-10-verified), `docs/development/research/2026-09-22-gtin-canonicalization.md` (§§2–16; §4.2 pattern + emit, 28-case simulation; §5.2 rule map; §6 contract/capability; §7.2 prefix; all vectors Mod-10-verified), `paxman/capabilities/ISBN/grammar/isbn13_recognition.py:17-40` (fused label + `(?![-]\d)` precedent), `paxman/capabilities/ISSN/grammar/issn_recognition.py:40-49` (LabelMatcher + emit precedent), `paxman/capabilities/ISBN/rules/iso_2108_ed2017.py:19-72` (local check helper + PARSER/LOOKUP pair precedent), `paxman/capabilities/ISBN/contract.py:40-47` + `paxman/capabilities/ISBN/capability.py:38-64,130-144` (contract/wiring/format precedent), `paxman/core/domain.py:236-271` (Rule six-attr enforcement), `paxman/capabilities/__init__.py:21-24,53-56,84-86` + `paxman/api/bootstrap.py:38-49` + `paxman/cli.py:169-173` (Email→GTIN→IBAN insertion points), `tests/property/test_output_format_preservation.py:118-125,205-236,239-276` (CLASS_MAP gate + matrix), `tests/property/test_reentry_invariant.py:95-110` (`_row` shape), `HOW_TO_ADD_NEW_CAPABILITY.md` Steps 0/3/5/6/7/10, `docs/development/plans/2026-09-22-lei-capability.md` (procedural precedent; LEI since landed — 24 shipped).

**Branch:** `feature/gtin-capability` cut from `dev`. PR targets `dev`.

---

## File Structure

- Create (scaffolder, then fill/rename): `paxman/capabilities/GTIN/__init__.py`, `notation.py` — `GTINNotation(digits, native_length, has_ai)` frozen+slots; `contract.py` — DEFAULT `gtin14`, OFFERED `{"native","hri"}` (Task 6 may narrow), `include_verified=False`; `capability.py` — wiring + `format_value` + `_group_hri`; `grammar/__init__.py`, `grammar/gtin_recognition.py` — `_GTIN_LABEL_RE`/`_GTIN_AI_RE` + `_gtin_emit` + `_GTIN_BODY` + `GTINRecognitionGrammar`; `rules/__init__.py`, `rules/gs1_genspecs_ed2026.py` — `Section1GtinStructureCheckDigit` PARSER + `PUBLICATION` (renamed from scaffolder file; exact subsection confirmed at build time, research §5.2 note); `rules/gs1_prefix_ed2026.py` — `Section2Gs1Prefix` LOOKUP_TABLE + `PUBLICATION`; `rules/verified_by_gs1_ed2019.py` — `Section3VerifiedLiveness` LOOKUP_TABLE + `PUBLICATION`, `requires_features={"include_verified"}`; `rules/data/__init__.py`, `rules/data/gs1_prefix.py` — `GS1_MO_RANGES` + `GS1_GTIN8_EXCEPTIONS` with per-row source comments + refresh procedure; `rules/data/verified_snapshot.py` — `ISSUED_GTINS` (empty shipped frozenset) + add-only refresh procedure.
- Create (tests): `tests/capabilities/gtin/__init__.py`, `test_notation.py`, `test_contract.py`, `test_grammar.py`, `test_rules.py`, `test_data.py`, `test_capability.py`, `tests/integration/test_gtin_pipeline.py`, `tests/property/test_gtin_properties.py`.
- Modify: `paxman/capabilities/__init__.py` (import + `__all__` + `_LAZY` + TYPE_CHECKING, alphabetical Email→GTIN→IBAN), `paxman/api/bootstrap.py` (`_SHIPPED` import + tuple, alphabetical), `paxman/cli.py` (`gtin` branch between email:169 and iban:173), `tests/property/test_reentry_invariant.py` (GTIN ROWS per ADR-0010), `tests/property/test_output_format_preservation.py` (`("gtin","native")` expansion + `("gtin","hri")` encoding per ADR-0011, or native-only if Task 6 defers hri), `docs/user/capabilities/gtin.md` (new) + chooser/index/concepts/api-reference/citations/glossary/migration rows, `README.md` + `CONTEXT.md` tables/Notation, `AGENTS.md` + `paxman/capabilities/AGENTS.md` + `tests/AGENTS.md` counts (24→25), `CHANGELOG.md` (`## [Unreleased]`), `docs/development/MILESTONE.md:73` (row 14 canonical → 14-digit `05901234123457`).
- No `paxman/core`, engine, or `grammar/data/` changes.
  - **Deviation (sanctioned, 2026-09-23 — pre-merge UX sweep):** `paxman/engine/orchestrator.py` *does* change. The sweep found `format_value()` ran inside `_collect_candidates()` — before the single-value invariant, dedup, status, and the span condition — so a notation-keyed offered format leaked into candidate identity: `00614141999996 and 614141999996` raised `MultipleMentionsError` under `output_format="native"` while the default contract coalesced to `SUCCESS` (status varying by format violates the ambiguity-contract preservation an offered format must keep). Approved fix, test-first: identity decisions (invariant, dedup key, status, span) now read canonical pre-format values; `_dedup_candidates` threads `(candidate, rep)` pairs through; a new `_format_candidates()` applies the presentation seam exactly once at `ExecutionResult` assembly, rebuilding each survivor with unchanged rule names/provenance/span and rendering with the source recognition's notation. Public surface unchanged (`ExecutionResult.candidates[].value` and `canonicalized_value` stay format-resolved). `paxman/core` remains untouched. Two latent engine twins surfaced by the same defect class were fixed alongside (Phone `rfc3966` extension pair; the format-seam test pinned format-before-identity as intended), and `ARCHITECTURE.md`, `HOW_TO_ADD_NEW_CAPABILITY.md`, and the ADR-0010 code pointer were updated to the new ordering. Full gate re-run green.

---

## Background the implementer needs

### Current state (verbatim)

No GTIN code exists (24 shipped: BIC..UUID plus LEI; `paxman/capabilities/__init__.py:21-24` `__all__` has `"Email"` then `"IBAN"` with no `GTIN`; `_LAZY:53-56` same gap; TYPE_CHECKING imports `:84-86` same gap; `paxman/api/bootstrap.py:38-49` `_SHIPPED` has no GTIN; `paxman/cli.py:169-173` has email/iban branches with no gtin). Closest shipped shapes: ISBN-13 fused label + `(?![-]\d)` + digit-collapse (`isbn13_recognition.py:17-27`); ISSN LabelMatcher + span/ctx emit + WORD guards (`issn_recognition.py:34-49`); ISBN PARSER/LOOKUP pair sharing one semantics with local check helper and `normalize → digits` (`iso_2108_ed2017.py:19-72`); ISBN contract `DEFAULT/OFFERED` + `include_*` flags (`contract.py:40-47`); ISBN `_hyphenate` presentation-only + identity default (`capability.py:38-64,130-144`). Scaffolder emits 13 files plus wiring (`tools/new_capability.py`).

### Design decisions (locked, from research)

1. Canonical `gtin14`: 14-digit zero-padded (`digits.rjust(14,"0")`, check-preserving — verified for 8→14/12→14/13→14). Offered `native` renders spelled length via the facet slice (`value[14-native_length:]`); offered `hri` renders space groups (UPC-A `6 14141 99999 6` attested; EAN-13/8 + GTIN-14 groups confirmed or deferred in Task 6). ADR-0011: `native` = expansion (pad-strip merge; identity for true GTIN-14), `hri` = encoding.
2. One grammar `gtin_recognition`, `single_value=True`, no `active_grammars` (base `None` runs it). Exact-length alternation longest-first (`{13}\d|{12}\d|{11}\d|{7}\d` collapsed with `[ \-]?`, `(?![-]\d)`, WORD both sides) — 6/7/9/10/11/15+ unmatchable → MISSING (research §4.2 simulation: 28/28 claim-count cases). Fused labels `GTIN(-8/12/13/14)?/UPC(-A)?/EAN(-8/-13)?` + `[\s:-]+`, glued-`reject`; AI branch `(01)`-parens or `AI 01`-keyword only (bare `01` never a marker); emit strips label then AI by regex before digit-collapse (labels/AI carry digits).
3. Three rules, same `target_semantics=frozenset({"gtin_recognition"})`: PARSER `Section 1-gtin-structure-check-digit` (GenSpecs 26.0, `https://ref.gs1.org/standards/genspecs/`, version `26.0`, active, 2026, `kind="specification"`) owns length/charset/Mod-10 (`(10-sum%10)%10`, weights 3/1 rightmost-anchored, local helper — never import ISBN); LOOKUP_TABLE `Section 2-gs1-prefix` (Prefix allocation, company-prefix URL, version `Rolling 2026`, active, 2026, `kind="registry"`, always-active → ADR-0012 corroboration, no vacuity) owns native-digit prefix (3-char; 4-char for `9620–9624`); LOOKUP_TABLE `Section 3-verified-liveness` (Verified by GS1, services URL, version `Rolling`, active, 2019, `kind="registry"`, `requires_features={"include_verified"}`) owns snapshot liveness, reads `ISSUED_GTINS` at call time (monkeypatchable), shipped empty.
4. Prefix table is real MO ranges with per-row source comments + refresh procedure; full-list confirmation at build time (retry the gs1.org primary — research fetch was 403/WAF). Every suite vector's native prefix (001/034/106/206/501/614/629/963/978 + GTIN-8 exceptions) must resolve to an MO row; `999` stays the miss fixture. If any flagship vector's prefix is unallocated, replace the vector (keep Mod-10-valid) — never weaken the rule. Never hand-invent rows.
5. Checksum-verified vectors only: `96385074`, `614141999996`, `5012345670003`, `6291041500213`, `10614141999993`, `03453120000011`, `00196618007309`, `9780471117094` (Bookland dual — SUCCESS as GTIN-13, ISBN precedence is cross-capability), indicator-2 `2061414199993`; bad-check `614141999997`; bad-prefix `9991414199996` (check-valid). MILESTONE row 14 keeps its example, canonical corrected to `05901234123457`.
6. UPC-E 6-digit → MISSING (out-of-gate); 8-digit HRI collides with GTIN-8 (claimed, validates iff Mod-10 passes, never expanded — v1 admits the collision); hyphens/spaces stripped never emitted; tabs/newlines/dots/slashes → MISSING; glued `GTIN006…` → MISSING; full-width digits → MISSING; truncated stems → MISSING; two distinct → `MultipleMentionsError`/AMBIGUOUS; identical (incl. padded-vs-native) coalesce.
7. `normalize()` returns the 14-digit form from all three rules; rules contain zero `output_format` tokens; `format_value` is the only seam; ADR-0012 standard corroborated case.

---

### Task 1: Scaffold + Notation

**Files:** scaffolder output; fill `paxman/capabilities/GTIN/notation.py`, `tests/capabilities/gtin/test_notation.py`

- [ ] Run `uv run python tools/new_capability.py GTIN --name gtin --authority "GS1" --spec-name "GS1 General Specifications" --spec-url "https://ref.gs1.org/standards/genspecs/" --publication-year 2026 --spec-version "26.0" --default-format gtin14`, then rename the scaffolder GenSpecs rule file to `rules/gs1_genspecs_ed2026.py` (fix the capability import). Failing test first: `test_frozen_slots_hash` + `test_facet_shape` (`GTINNotation("614141999996", 12, False)`, `native_length == len(digits)`, `has_ai` trace-only) → FAIL. Implement `GTINNotation` per decision 1 (`@dataclass(frozen=True, slots=True)`, `digits: str`, `native_length: int`, `has_ai: bool`). Verify: `uv run pytest tests/capabilities/gtin/test_notation.py -v` → PASS.

### Task 2: Contract

**Files:** `paxman/capabilities/GTIN/contract.py`, `tests/capabilities/gtin/test_contract.py`

- [ ] Failing tests: `test_default_gtin14_offered_native_hri` + `test_include_verified_default_false` + `test_unknown_format_contract_error` + `test_suppress_common_words_default_false` + `test_adr0011_classes_declared` (docstring names native-expansion + hri-encoding) → FAIL. Implement `GTINContract` (`@dataclass(frozen=True)` without slots; `DEFAULT_OUTPUT_FORMAT="gtin14"`, `OFFERED_OUTPUT_FORMATS=frozenset({"native","hri"})`, `capability_name="gtin"` init=False, `include_verified: bool = False`, fixed keyword-only common block first in `create_contract`). Verify: `uv run pytest tests/capabilities/gtin/test_contract.py -v` → PASS.

### Task 3: Grammar

**Files:** `paxman/capabilities/GTIN/grammar/gtin_recognition.py`, `tests/capabilities/gtin/test_grammar.py`
Depends on: Task 1 Notation.

- [ ] Failing tests: `test_compact_per_length` (8/12/13/14), `test_padded_14`, `test_hri_spaced` (`6 14141 99999 6`, `1234 5670`), `test_hyphen_grouped`, `test_labels` (`GTIN:`/`upc-`/`EAN-13:`/`GTIN-14`, span includes label, digits label-free — incl. `GTIN-14 10614141999993` decontamination), `test_ai_wrapped` (`(01)`/`(01) `/`AI 01`, `has_ai=True`, span includes marker), `test_stacked_label_ai` (`GTIN: (01)…`), `test_leading01_bare_not_stripped` (`01345678901234` → 14-digit, `has_ai=False`), `test_exact_lengths_only` (9/10/11/7/6/15-digit → 0 matches), `test_upce8_collision_shape` (`01234567` claimed as 8-digit), `test_glued_label_missing`, `test_fullwidth_missing`, `test_quoted_bracketed`, `test_trailing_period_excluded`, `test_name_semantics_single_value` → FAIL. Implement `_GTIN_LABEL_RE`/`_GTIN_AI_RE` + `_gtin_emit` + `_GTIN_BODY` + `GTINRecognitionGrammar` per decision 2 (PipelineGrammar + StandardPre empty_guard + single LabelMatcher, module scope, `re.IGNORECASE | re.ASCII`, `BoundarySpec.WORD`, `HasDigit`). Verify: `uv run pytest tests/capabilities/gtin/test_grammar.py -v` → PASS.

### Task 4: Authority data tables

**Files:** `paxman/capabilities/GTIN/rules/data/__init__.py`, `paxman/capabilities/GTIN/rules/data/gs1_prefix.py`, `paxman/capabilities/GTIN/rules/data/verified_snapshot.py`, `tests/capabilities/gtin/test_data.py`

- [ ] Failing tests: `test_prefix_table_shape` (ranges sorted/non-overlapping, `start<=end`; 4-char GTIN-8 exceptions separate set), `test_suite_prefixes_resolve` (001/034/106/206/501/614/629/963/978 per decision 4, else replace vector), `test_prefix_source_comments` (every row cites GS1 origin + refresh procedure present), `test_verified_snapshot_empty_shipped` (`ISSUED_GTINS == frozenset()` + add-only refresh header) → FAIL. Implement both data modules per decisions 3–4 (plain module-level tables, no logic). Verify: `uv run pytest tests/capabilities/gtin/test_data.py -v` → PASS.

### Task 5: Rules (three publications)

**Files:** `paxman/capabilities/GTIN/rules/gs1_genspecs_ed2026.py`, `paxman/capabilities/GTIN/rules/gs1_prefix_ed2026.py`, `paxman/capabilities/GTIN/rules/verified_by_gs1_ed2019.py`, `tests/capabilities/gtin/test_rules.py`
Depends on: Tasks 1, 4.

- [ ] Failing tests: `test_parser_valid_all_lengths` (decision-5 vectors + `05901234123457` padding invariance), `test_parser_bad_check` (`614141999997`), `test_parser_wrong_length_nonascii`, `test_lookup_valid_prefix` (`501…`→UK + all suite prefixes), `test_lookup_miss_unallocated` (`9991414199996`), `test_lookup_native_not_padded` (`05012345670003` tests `501`), `test_lookup_gtin8_four_char` (`9620–9624` need 4-char match), `test_normalize_agreement` (all three rules → identical 14-digit), `test_provenance_attrs` (three exact PUBLICATIONs per decision 3), `test_strategy_six_attrs`, `test_no_output_format_token`, `test_verified_gate_off_dropped` (default contract → SUCCESS path unaffected), `test_verified_gate_on_absent_invalid`, `test_verified_gate_on_present_success` (monkeypatched `ISSUED_GTINS`) → FAIL. Implement the three Rule classes per decision 3 (`matches`/`normalize` never raise; local `_gs1_mod10_is_valid`; call-time snapshot read). Verify: `uv run pytest tests/capabilities/gtin/test_rules.py tests/unit/test_rule_output_format_purity.py -v` → PASS.

### Task 6: Capability wiring + registration + format seam

**Files:** `paxman/capabilities/GTIN/capability.py`, `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`, `paxman/cli.py`, `tests/capabilities/gtin/test_capability.py`
Depends on: Tasks 1–3, 5.

- [ ] Failing tests: `test_wiring_counts` (1 grammar, 3 rules), `test_create_contract_common_block` (excluded/pinned/year/output/extra/suppress order + `include_verified`), `test_format_native` (`00614141999996`→`614141999996`; true-14 identity), `test_format_hri_upca` (`00614141999996`→`6 14141 99999 6`) + `test_hri_reentry` (rendering re-enters to the 14-digit pre-image), `test_cli_gtin_branch`, `test_shipped_contains_gtin` → FAIL. Implement `get_grammars`/`get_rules`/`create_contract`/`format_value` + `_group_hri` + registration (`__init__` import/`__all__`/`_LAZY`/TYPE_CHECKING, `_SHIPPED` import/tuple, cli branch — all alphabetical Email→GTIN→IBAN). `_group_hri` rule: confirm EAN-13/8 + GTIN-14 groupings from the HRI Guideline/GenSpecs figures at build time (UPC-A attested); if unconfirmed, narrow `OFFERED_OUTPUT_FORMATS` to `{"native"}` in `contract.py`, drop hri tests/CLASS_MAP entry in Task 8, and note it in `gtin.md` — never invent groupings. Verify: `uv run pytest tests/capabilities/gtin/test_capability.py tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v` → PASS.

### Task 7: Integration + invariants

**Files:** `tests/integration/test_gtin_pipeline.py`

- [ ] Failing tests: SUCCESS rows (every research §2.1 RECOGNIZE form → one 14-digit, padded-vs-native dedup, indicator-1 `10614141999993` + indicator-2 `2061414199993`, Bookland `9780471117094` as GTIN-13), INVALID rows (bad check, bad prefix, verified-gated miss with `include_verified=True`), MISSING rows (no run, UPC-E `012345`, stems 7/9/10/11, glued label, full-width, bars-only), AMBIGUOUS/`MultipleMentionsError` (two distinct; identical pair coalesces), span integrity (label/AI in span), candidate dedup, determinism/VersionStamp → FAIL, then pass via Tasks 3/5/6 code (autouse `_clean_registry`). Verify: `uv run pytest tests/integration/test_gtin_pipeline.py -q` → PASS.

### Task 8: Property + re-entry + preservation

**Files:** `tests/property/test_gtin_properties.py`, `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py`

- [ ] Failing tests: synthesized-valid self-canonicalization (prefix sampled from `GS1_MO_RANGES` + random payload + computed check → `rjust(14)` self), random-digit-strings INVALID high-probability no-crash, grouped-vs-compact equivalence, `native`/`hri` round-trip; re-entry ROWS `_row(GTIN, "00614141999996", "00614141999996")` + `_row(GTIN, "10614141999993", "10614141999993")` (true-14 identity, bic11 8/11-pair analogue); preservation `CLASS_MAP[("gtin","native")]=expansion` (pad-strip merge rationale) + `("gtin","hri")=encoding` with rationale comments (hri entry only if Task 6 kept it) → FAIL, then pass (no new impl expected). Verify: `uv run pytest tests/property/test_gtin_properties.py tests/property/test_reentry_invariant.py tests/property/test_output_format_preservation.py -q` → PASS.

### Task 9: Docs + counts + MILESTONE correction

**Files:** `docs/user/capabilities/gtin.md`, chooser/index/concepts/api-reference/citations/glossary/migration, `README.md`, `CONTEXT.md`, `AGENTS.md`, `paxman/capabilities/AGENTS.md`, `tests/AGENTS.md`, `CHANGELOG.md`, `docs/development/MILESTONE.md:73`

- [ ] Guide `gtin.md` (recognition table with the decision-5 vectors, statuses incl. UPC-E collision + DEFER/REJECT rows, executed snippet, GenSpecs 26.0 + Prefix + Verified provenance, no code/shipped-doc refs to `docs/development/` per its AGENTS.md) + chooser/index/concepts/api-reference/citations/glossary/migration rows + `tools/generate_readme_table.py` run (diff limited to the GTIN row) + README/CONTEXT tables (`| **GTIN** | Trade item identifiers | GS1 General Specifications 26.0 |` + Notation subsection) + AGENTS counts 24→25 + CHANGELOG `Unreleased` Added entry + MILESTONE row 14 canonical fix (`590 1234 12345 7` → `05901234123457`; keep the Mod-10 note). Verify: snippet outputs executed not assumed; `uv run pytest tests/unit/test_capability_exports.py -q` → PASS.

### Task 10: Full gate + PR

**Files:** none (verify + handoff).

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q && uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → all green (pre-existing `dev` findings excluded by stashed-baseline comparison). Commit `feat(gtin): GTIN capability (GS1 GenSpecs 26.0 + Prefix + Verified snapshot)`, review with `paxman-oracle-review` then open PR against `dev`.

---

Plan saved to docs/development/plans/2026-09-22-gtin-capability.md — 10 tasks.

Execute task-by-task via tdd (failing test first). After impl, run paxman-momus-review on the plan file, then paxman-oracle-review on the branch diff before PR handoff.
