# MinorPlanet Capability Implementation Plan (research-driven — no issue)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a `minor_planet` capability that recognizes unpacked/packed/survey/numbered minor-planet lanes and validates them structure-only (PARSER, no registry) to the unpacked canonical (`1995 XA`, `2040 P-L`, `(433)`), with `packed` as the offered wire encoding.

**Architecture:** Single `minor_planet_recognition` grammar (lane alternation, one dedup key) + five PARSER rules across three publications (unpacked, packed, numbering) + `MinorPlanetContract` (`designation` default / `packed` offered) + `format_value` seam. Pack/unpack codec lives in rules-owned shared module imported by rules and capability, never the grammar. No registry at v1; valid-vs-issued collapses honestly with a named MPCORB upgrade path.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `paxman/core/grammar` kernel (`RegexMatcher` + `BoundarySpec.WORD` preferred; legacy `PipelineGrammar` + `RegexStage` accepted with note), `paxman/capabilities/MinorPlanet`.

**References:** `docs/development/research/2026-10-07-minor-planet-designation-canonicalization.md` §§2–13 (fixed 2026-10-07: compilable pattern, `A/` 1-2 letters, spaced-lowercase lanes, phone/ZIP overclaims documented, decode in rules/capability), `HOW_TO_ADD_NEW_CAPABILITY.md` Steps 0–7, `paxman/core/domain.py:243-289` (Rule metadata), `paxman/core/domain.py:291-322` (Grammar metadata), `paxman/engine/orchestrator.py:750-789` (ADR-0012 vacuity), `paxman/engine/orchestrator.py:625-684` (single-value), `paxman/engine/orchestrator.py:882-893` (MISSING/INVALID), `paxman/capabilities/ISSN/capability.py:47-56` (shipped `create_contract` block), `paxman/capabilities/ISSN/contract.py:10-33` (contract shape + ADR-0011 docstring), `paxman/capabilities/GTIN/notation.py:9-22` (notation facet precedent), `docs/adr/0012-candidate-qualification.md:67-75` (vacuity), `docs/adr/0011-output-format-information-preservation.md` (encoding class), `paxman/capabilities/UNSPSC/grammar/unspsc_recognition.py:20-36` (staged-pipeline pattern precedent).

**Branch:** `feature/minor-planet-capability` (cut from current `feature/unspsc-capability` HEAD; rebase as needed)

---

## File Structure

- Create via scaffolder then fill: `paxman/capabilities/MinorPlanet/__init__.py`, `paxman/capabilities/MinorPlanet/notation.py`, `paxman/capabilities/MinorPlanet/contract.py`, `paxman/capabilities/MinorPlanet/capability.py`, `paxman/capabilities/MinorPlanet/grammar/__init__.py`, `paxman/capabilities/MinorPlanet/grammar/minor_planet_recognition.py`, `paxman/capabilities/MinorPlanet/rules/__init__.py`, `paxman/capabilities/MinorPlanet/rules/mpc_unpacked_designation.py`, `paxman/capabilities/MinorPlanet/rules/mpc_packed_designation.py`, `paxman/capabilities/MinorPlanet/rules/mpc_numbering.py`, `paxman/capabilities/MinorPlanet/rules/mpc_codec.py`
- Create tests: `tests/capabilities/minor_planet/__init__.py`, `tests/capabilities/minor_planet/test_notation.py`, `tests/capabilities/minor_planet/test_grammar.py`, `tests/capabilities/minor_planet/test_rules.py`, `tests/capabilities/minor_planet/test_capability.py`, `tests/capabilities/minor_planet/test_integration.py` (new; pipeline + determinism vectors)
- Modify (registration + surface): `paxman/capabilities/__init__.py` (`_LAZY` + `TYPE_CHECKING` + `__all__`), `paxman/api/bootstrap.py` (`_SHIPPED` + contract factory branch), `paxman/cli.py` (capability branch), `tools/generate_readme_table.py` (if capability-indexed), `tests/unit/test_capability_surface.py` (`_CAPABILITY_SURFACES` entry, via scaffolder)
- Modify (docs sweep per `tools/new_capability.py` output): `docs/user/capabilities/minor_planet.md` (create), `docs/user/capabilities/index.md`, `docs/user/concepts/capabilities.md`, `docs/user/api-reference.md`, `docs/user/citations.md`, `docs/user/glossary.md`, `docs/user/migration.md`, `README.md` tables, `CONTEXT.md` Notation/table entries, root `AGENTS.md` counts (27 → 28 shipped; verify current number at implementation)
- No `paxman/core` change. No `rules/data/` at v1 (no registry).

Type lock (used identically in every task below): `MinorPlanetNotation(designation: str, form: str, packed: str)` with `packed` = spelled packed form for packed lanes else `""`; `MinorPlanetContract` with `DEFAULT_OUTPUT_FORMAT = "designation"`, `OFFERED_OUTPUT_FORMATS = frozenset({"packed"})`, `capability_name = "minor_planet"`, shipped common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`).

---

### Task 1: Scaffold — generate the skeleton

**Files:** scaffolder output listed above (`paxman/capabilities/MinorPlanet/*`, `tests/capabilities/minor_planet/*`)

**Goal:** Green skeleton with unanimous surface before any domain fill.

- [ ] Run `uv run python tools/new_capability.py MinorPlanet --name minor_planet --authority "Minor Planet Center" --spec-name "Unpacked provisional designation definition" --spec-url "https://minorplanetcenter.net/iau/info/DesDoc.html" --publication-year 2026 --spec-version "living document (fetched 2026-10-07)" --default-format designation` → 13 files + `paxman/capabilities/__init__.py` wiring. Verify: `uv run pytest tests/capabilities/minor_planet -q` → PASS (scaffold stubs). Commit: `feat(minor_planet): scaffold capability skeleton`.

Depends on: nothing (first).

### Task 2: Notation — frozen+slots facets

**Files:** `paxman/capabilities/MinorPlanet/notation.py`, `tests/capabilities/minor_planet/test_notation.py`

**Goal:** `MinorPlanetNotation` with `designation` (syntax-normalized spelled form), `form` (one of `provisional` | `packed` | `extended` | `survey` | `survey_packed` | `number` | `packed_number`), `packed` (spelled packed for packed lanes else `""`).

- [ ] Failing test first: `test_frozen_slots_hash` + `test_packed_empty_for_unpacked_lane` in `tests/capabilities/minor_planet/test_notation.py` → FAIL. Implement `@dataclass(frozen=True, slots=True)` with three `str` fields and docstring stating the `packed` lane rule. Verify: `uv run pytest tests/capabilities/minor_planet/test_notation.py -v` → PASS. Commit: `feat(minor_planet): shape notation facets`.

### Task 3: Codec — rules-owned pack/unpack tables (never grammar)

**Files:** `paxman/capabilities/MinorPlanet/rules/mpc_codec.py` (create; pure functions + tables), `tests/capabilities/minor_planet/test_rules.py` (codec vectors)

**Goal:** Single source of truth for century `IJK`=18/19/20, cycle letter values A=10…Z=35/a=36…z=61, base-62 decode, tilde minus-620000, survey-pack codes, extended-`_` shape. Grammar never imports this module (governance gate).

- [ ] Failing tests: `test_tilde_vectors` (`~0000`→620000, `~000z`→620061, `~AZaz`→3140113, `~zzzz`→15396335), `test_cycle_letter_values` (`J`=19→`J3`=193, `f`=41→`f8`=418), `test_pack_unpack_roundtrip` (`J95X00A`↔`1995 XA`, `K07Tf8A`↔`2007 TA418`, `K99AJ3Z`↔`2099 AZ193`, `03202`↔`(3202)`, `A0345`↔`(100345)`, `a0017`↔`(360017)`) → FAIL. Implement `mpc_unpack(spelled) -> str | None` (case-exact, `None` on incoherent) and `mpc_pack(designation) -> str | None` (`None` for the `A/` lane) with no imports from grammar. Verify: `uv run pytest tests/capabilities/minor_planet/test_rules.py -k "tilde or codec or roundtrip" -v` → PASS. Commit: `feat(minor_planet): add rules-owned pack/unpack codec`.

### Task 4: Contract — shipped common block + ADR-0011 class

**Files:** `paxman/capabilities/MinorPlanet/contract.py`, `tests/capabilities/minor_planet/test_capability.py` (contract factory asserts)

**Goal:** `MinorPlanetContract(CapabilityContract)` with `designation` default, `packed` offered, shipped `create_contract` signature from `paxman/capabilities/ISSN/capability.py:47-56`, ADR-0011 class paragraph naming `packed` as an encoding in the same docstring paragraph.

- [ ] Failing tests: `test_default_is_designation`, `test_packed_offered_reenters`, `test_unknown_format_raises_ContractError` → FAIL. Implement contract per the type lock + `tests/unit/test_offered_format_class_declarations.py` paragraph rule. Verify: `uv run pytest tests/capabilities/minor_planet/test_capability.py -k contract -v` → PASS. Commit: `feat(minor_planet): contract with packed encoding`.

### Task 5: Grammar — single lane-alternation recognizer

**Files:** `paxman/capabilities/MinorPlanet/grammar/minor_planet_recognition.py`, `tests/capabilities/minor_planet/test_grammar.py`

**Goal:** `minor_planet_recognition` / `minor_planet_recognition` semantics, `single_value=True`, kernel `RegexMatcher` + `BoundarySpec.WORD` spelling of the research §4.2 pattern as fixed (distinct `a*` groups for the `A/` 1-2-letter lane, `_NUMBER` `\d{1,8}`, ASCII without `IGNORECASE`); fallback to legacy `PipelineGrammar` + `RegexStage` only with a code comment if the kernel API blocks exact-case lanes.

- [ ] Failing tests first: positive vector per §2.1 RECOGNIZE row (`1995 XA`, `2007 TA418`, `2003 cp20` fold, `1995_XA`, `A904 OA`, `A/2017 U1`, `J95X00A`, `K07Tf8A`, `_QC0000`, `2040 P-L`/`PLS2040`, `3138 T-1`/`T1S3138`, `(433)`, `(274301)`, `(15396335)`, `03202`, `A0345`, `a0017`, `~000z`, `~AZaz`, `(433) Eros` number-span); negatives (`1995XA` glued, `433` bare, `1892 A` old-style, `C/1995 O1` comet, `Eros` name, `1995 SA₁` subscript, 3-/5-digit years, 6-char packs, X-glued runs); compile-regression test asserting `re.compile` succeeds (guards the duplicate-group failure); span invariants (`raw_text == text[start:end]`, parens inside span, name outside span). Document `(555)`-in-phone and bare-`\d{5}`-as-ZIP as known v1 overclaims in test comments, not guard negatives. Run `uv run pytest tests/capabilities/minor_planet/test_grammar.py -v` → FAIL then PASS after implement. Commit: `feat(minor_planet): lane-alternation grammar`.

Depends on: Task 2 Notation.

### Task 6: Rules — unpacked structure + surveys (Sections 1–2)

**Files:** `paxman/capabilities/MinorPlanet/rules/mpc_unpacked_designation.py`, `tests/capabilities/minor_planet/test_rules.py`

**Goal:** `Section1UnpackedProvisionalStructure` + `Section2SurveyDesignation`, PARSER, `target_semantics=frozenset({"minor_planet_recognition"})`, `requires_features=frozenset()`, DesDoc `PUBLICATION`, full-conjunction `matches()` (lane gate on `notation.form` + year lane + separator + half-month `[A-HJ-Y]` + second `[A-HJ-Z]` + cycle; survey number + identifier).

- [ ] Failing tests: valid (`1995 XA`, `2007 TA418`, `A904 OA`, `A/2017 U1`, `1995 XZ` second-letter-Z valid), invalid (`1995 XI`, `1995 IZ`, bad survey identifier), `normalize()` exact unpacked canonical, provenance attrs, `target_semantics` exact set → FAIL then PASS. Verify: `uv run pytest tests/capabilities/minor_planet/test_rules.py -k "Section1 or Section2" -v` → PASS. Commit: `feat(minor_planet): unpacked + survey rules`.

Depends on: Tasks 2–3.

### Task 7: Rules — packed coherence + tilde (Sections 3–4)

**Files:** `paxman/capabilities/MinorPlanet/rules/mpc_packed_designation.py`, `tests/capabilities/minor_planet/test_rules.py`

**Goal:** `Section3PackedProvisional` + `Section4PackedNumber`, PARSER, PackedDes `PUBLICATION`, full-conjunction `matches()` via `mpc_codec` (century ∈ IJK, half-month set, cycle letter×10+digit, extended shape, tilde arithmetic; packed-number case preserved with `a0017`→360017 vs `A0345`→100345 trap pair).

- [ ] Failing tests: valid packed vectors from Task 3 plus invalid (`Q95X00A` bad century, `J95I00A` bad half-month), extended shape vectors, case-trap pair asserting distinct normalizations → FAIL then PASS. Verify: `uv run pytest tests/capabilities/minor_planet/test_rules.py -k "Section3 or Section4" -v` → PASS. Commit: `feat(minor_planet): packed coherence rules`.

Depends on: Tasks 2–3.

### Task 8: Rules — permanent numbers (Section 5)

**Files:** `paxman/capabilities/MinorPlanet/rules/mpc_numbering.py`, `tests/capabilities/minor_planet/test_rules.py`

**Goal:** `Section5PermanentNumber`, PARSER, HowNamed `PUBLICATION`, `^[1-9]\d{0,7}$` on paren contents (no leading zeros, tilde-max headroom).

- [ ] Failing tests: `(433)`, `(274301)`, `(15396335)` valid; `(0433)`, `(0)` invalid; `(433) Eros` validates on the number lane (name outside notation) → FAIL then PASS. Verify: `uv run pytest tests/capabilities/minor_planet/test_rules.py -k Section5 -v` → PASS. Commit: `feat(minor_planet): permanent-number rule`.

Depends on: Task 2.

### Task 9: Capability — wiring + `format_value` seam

**Files:** `paxman/capabilities/MinorPlanet/capability.py`, `tests/capabilities/minor_planet/test_capability.py`

**Goal:** `get_grammars()` 1 grammar, `get_rules()` 5 rules, shipped `create_contract()` delegating to Task 4, `format_value()` identity for `designation` and `mpc_pack` render for `packed` (imports codec from `rules/mpc_codec.py`, never grammar tables), `version = "1.0.0"`.

- [ ] Failing tests: wiring counts, grammar/rule name conventions, `format_value` round-trips (`1995 XA`→`J95X00A`→re-parse→`1995 XA`; lowercase packed lanes case-exact; `A/`-lane `packed` falls back to designation with comment) → FAIL then PASS. Verify: `uv run pytest tests/capabilities/minor_planet/test_capability.py -v` → PASS. Commit: `feat(minor_planet): capability wiring and packed seam`.

Depends on: Tasks 2–8.

### Task 10: Registration + cross-layer consistency + purity

**Files:** `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`, `paxman/cli.py`, `tests/unit/test_capability_surface.py`, new consistency asserts in `tests/capabilities/minor_planet/test_capability.py`

**Goal:** Capability resolvable via `register_all_shipped` and CLI; every rule `target_semantics` produced by the shipped grammar; no `output_format` token in `paxman/capabilities/MinorPlanet/rules/`; grammar imports nothing from `rules/`.

- [ ] Failing tests: `test_target_semantics_covered`, purity scan (`rg -n output_format paxman/capabilities/MinorPlanet/rules/` → 0 hits), `test_surface_covers_minor_planet` → FAIL then PASS after wiring. Verify: `uv run pytest tests/capabilities/minor_planet/test_capability.py tests/unit/test_capability_surface.py -q` → PASS. Commit: `feat(minor_planet): register and lock consistency`.

Depends on: Task 9.

### Task 11: Pipeline + property + docs sweep + gates

**Files:** `tests/capabilities/minor_planet/test_integration.py`, property tests (extend or add `tests/property/test_minor_planet*.py` per repo layout), docs sweep paths in File Structure

**Goal:** End-to-end SUCCESS/INVALID/MISSING/AMBIGUOUS per research §§8–9; `_clean_registry` fixture; determinism + `VersionStamp`; `packed`→re-parse preservation-matrix entry (`CLASS_MAP` + injectivity pair in `tests/property/test_output_format_preservation.py`); hypothesis lane-directed generation, round-trips, never-raise on random alphanum, case-fold stability; docs sweep; full gates green.

- [ ] Failing integration tests first: SUCCESS all lanes incl. packed+unpacked same-value dedup (`J95X00A = 1995 XA` → one value); INVALID (bad letter slots, bad century, leading-zero number); MISSING (glued/bare/old-style/comet/name/subscript); AMBIGUOUS/`MultipleMentionsError` (equation headings, two distinct); overclaims asserted as documented SUCCESS with registry-upgrade comments. Property tests per research §12. Docs sweep per `tools/new_capability.py` step 5. Final verify: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green, coverage ≥95. Commit: `feat(minor_planet): pipeline, properties, docs sweep`.

Depends on: Tasks 1–10.

---

## Self-Review (done before saving)

- Spec coverage: every §2.1 RECOGNIZE row has a Task 5 positive vector; every REJECT/DEFER row has a negative; §§5/7 rule map matches Tasks 6–8; §6 contract/capability matches Tasks 4/9; §8/9 resolution map matches Task 11; §12 vectors distributed across Tasks 5–8/11.
- Placeholder scan: clean per `rg` (no placeholder tokens remain in task text).
- Type consistency: one Notation shape, one Contract shape, one codec owner, repeated verbatim in File Structure + Tasks 2–4/9.
- Momus dry-run: branch set, references carry paths:lines, each task names files + test names + `uv run` verify + commit, QA per task. Ready for `paxman-momus-review`.

Plan saved. Execute task-by-task via `tdd` (failing test first). After impl, run `paxman-momus-review` on this plan file, then `paxman-oracle-review` on the branch diff before PR handoff.
