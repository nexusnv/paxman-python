# Element Capability Implementation Plan

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship the `element` capability (MILESTONE row 22): canonicalize human element designations (symbols, English names, labeled atomic numbers) to the proper-case IUPAC symbol with Red Book + Periodic Table provenance, closing the Chemical-element milestone row.

**Architecture:** One `PipelineGrammar` (`element_recognition`, `single_value=True`) with a 3-matcher tuple — case-exact symbol `LexiconMatcher`, casefolded-view name `LexiconMatcher`, and a label-required `RegexMatcher` Z-branch (ISSN-style emit idiom) — routed by `shape` to two `LOOKUP_TABLE` rules (one file per publication: Red Book 2005 specification + 04 May 2022 registry snapshot sharing one `rules/data` module). Contract offers `symbol` (default) + `name` only: `atomic_number` is deliberately **not** offered (ADR-0010 fixed-point violation — bare `26` is unclaimable by design). No `paxman/core` changes; no custom `recognize()` override (base delegation + engine `_dedup_spans`).

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `paxman/core/grammar` kernel (`LexiconMatcher`, `LabelMatcher`, `BoundarySpec`, `PipelineGrammar`), `tools/new_capability.py` scaffold.

**References:** Research `docs/development/research/2026-09-02-chemical-element-canonicalization.md` (§2.1 inventory, §5 lineage, §8 edge cases, §9 states, §13 decisions); `HOW_TO_ADD_NEW_CAPABILITY.md` Steps 0–10; `ARCHITECTURE.md`; ADR-0009 Rev.5 (A0 exemption), ADR-0010 (re-entry gate); `docs/development/MILESTONE.md` row 22; `paxman/capabilities/ISSN/grammar/issn_recognition.py:40-49`, `paxman/capabilities/IBAN/grammar/iban_recognition.py:58-84`, `paxman/capabilities/SIUnit/grammar/symbol_recognition.py:39-106`, `paxman/capabilities/Country/grammar/name_recognition.py:33-57`, `paxman/capabilities/Country/rules/iso_3166_ed2024.py:41-63`, `paxman/capabilities/MacAddress/contract.py:29-34`, `paxman/core/grammar/engine_loop.py:82-160`, `paxman/core/grammar/matchers/label.py:27-43`, `paxman/core/domain.py:19-64`, `paxman/engine/orchestrator.py:62-79`, `tests/property/test_reentry_invariant.py:89-194`.

**Branch:** `feature/element`

---

## Background the implementer needs

### Research-vs-codebase review (2026-09-04; report frozen at `dev @ 92c1d94`, now `dev @ df63833`)

The report's domain evidence (Red Book IR-3 corpus, 118-closed registry, ecosystem table, §2.1 inventory, §5 lineage) is unaffected. Five structural deltas change the implementation shape:

1. **ADR-0010 landed (Accepted 2026-09-03, issue #123): offered `atomic_number` must go.** Rendering `Fe` as bare `"26"` cannot re-enter — bare integers are unclaimable by design (report §2.1 REJECTs them, correctly) → re-entry `MISSING`. Scope decision 3 is hard: an offered format that fails re-entry must be fixed or de-offered. There is no contract-relative rescue (unlike Phone `national` + `default_country`): bare numbers can never be claimed without turning every integer into a mention. Labeled rendering (`"element 26"`) would round-trip but leaks recognition syntax into the value domain — rejected (every shipped offered format is a bare value). Precedent is MacAddress `bit_reversed` de-offering (`paxman/capabilities/MacAddress/contract.py:21-26`, CHANGELOG Breaking). **Locked: `OFFERED_OUTPUT_FORMATS = frozenset({"name"})`.**
2. **ADR-0010 gate is structural:** a new capability cannot land without a row in `tests/property/test_reentry_invariant.py` (`_row` helper builds unset + `"default"` + every offered format; `assert {row.name} == set(list_shipped_capabilities())`). Plus `SUPPRESS_ROWS` for common-word canonicals (whole-input, suppress on). The report's §12 predates this — Tasks 11 covers it.
3. **A0 whole-input exemption landed (#122, ADR-0009 Rev.5).** `engine_loop.py:146-160`: a suppressible word-bounded hit covering the entire trimmed input is never suppressed; `ExecutionResult` carries `suppressed_count`/`suppressed_spans` (`orchestrator.py:62-79`). The report's §8 rows 14–15, §9, §13 D5, §14 describe the pre-A0 posture (`in` + flag → `MISSING`). Current posture: whole-input `in` + flag → `SUCCESS In` (exempt); embedded mentions still suppressed. Report's claim "13 two-letter symbols ∈ COMMON_WORDS" verified verbatim against `paxman/core/grammar/data/common_words.py:44-116` (67 frozen) — still true.
4. **Z-branch matcher: label-required `RegexMatcher` (ISSN/IBAN emit idiom).** The report's §4.2 `RegexMatcher` sketch is retained for one reason `LabelMatcher` cannot satisfy: `LabelMatcher` always makes the label optional (`combined = (?:(?:labels)sep)?pattern`, `matchers/label.py:56-64`), so bare `26` would be claimed and canonicalize to `Fe` — contradicting the §2.1 bare-number REJECT and Task 10's `26 → MISSING` row. Use `RegexMatcher(pattern=r"(?ai:(?:element|atomic number|Z)[\s:=]+[0-9]{1,3})(?![0-9])", boundary=WORD)` with ISSN-style emit (re-search the raw span for the digit core — `issn_recognition.py:34-37` pattern; `int()`-fold leading zeros). The #130 resume hazard (raw `finditer` swallowing a valid match inside a boundary-rejected span, `matchers/label.py:110-132`) is unreachable for a label-required pattern: no valid match can start inside a rejected `element 26`-shaped span without its own label. Separator `[\s:=]+` is never zero-width, so `element26`/`Z26` stay unclaimed (glued-reject parity with IBAN).
5. **Two sketch defects to not copy:** (a) custom `recognize()` with manual longer-wins dedup copies SIUnit's legacy-parity shim — new grammars (ISSN/IBAN) use `PipelineGrammar` base delegation (`pipeline.py:36-41`) + engine `_dedup_spans` (`orchestrator.py:442-474`); no overlap exists between the Z-label spans and lexicon spans anyway. (b) Name-key casing is internally inconsistent (§2.1 promises `IRON`; §4.2 says keys are "lowercase + capitalized" yet asserts `>= 476` — arithmetic never closes: 120 names × 2 cases = 240, × 3 = 360; 476 is the combined symbol+name total). Fix: name matcher on `view="casefolded"` (`CaseFold.normalize = text.lower()`, `normalizers.py:205-213`; Country `name_recognition.py:41-42` precedent) with 120 lowercase keys — matches MILESTONE row 22 "case-insensitive name matching" exactly, including mixed case. Symbol matcher stays `view=None` case-exact (236 keys) so `FE` stays `MISSING`, never `INVALID`.

### Design decisions (locked)

1. Package `Element`, registry name `element` (report §13 D2; MILESTONE label is "Chemical element", value is an *element*; terse-name precedent `URL`/`IP`).
2. Notation `ElementNotation(token, shape)`, `shape ∈ {"symbol","name","atomic_number"}` free `str` (MacAddress/Currency routing-key precedent; future community shapes via `extra_grammars`).
3. Isotope guard `BoundarySpec(left=("\\w",), right=("\\w", "-\\d"))` — the `-\\d` fragment rides the multi-char path (`boundary_spec.py:217-249`, width-2 `\A-\d`); left `\w` rejects `56Fe`/formulas, right `\w` rejects `Fe2O3`, `-\d` rejects `Fe-56` → all `MISSING` (report §13 D6).
4. Symbol matcher `suppressible=True`; name matcher `suppressible=False` (no element name intersects COMMON_WORDS — verified: none of the 67 words is an element name — so the flag is dead weight there, and leaving it unmarked keeps a non-suppressible rescue path per ADR-0010 Scope 5); Z-label matcher not suppressible.
5. Registry data hand-authored `rules/data/periodic_table_ed2022.py` (118 rows; changes only on an IUPAC naming event — report §13 D10; no generator script in v1).
6. `atomic_number` rendering stays out of `format_value` (unoffered formats are rejected at contract construction; dead branches are removed per the MAC `bit_reversed` precedent). Data module ships `SYMBOLS`, `NAME_TO_SYMBOL`, `Z_TO_SYMBOL`, `SYMBOL_TO_NAME` (no `SYMBOL_TO_Z` — no consumer).

---

## File Structure

- Create (scaffold, then fill): `paxman/capabilities/Element/__init__.py`, `notation.py`, `contract.py`, `capability.py`, `grammar/__init__.py`, `grammar/element_recognition.py`, `grammar/data/__init__.py`, `grammar/data/element_keys.py`, `rules/__init__.py`, `rules/iupac_red_book_2005.py`, `rules/iupac_periodic_table_ed2022.py`, `rules/data/__init__.py`, `rules/data/periodic_table_ed2022.py`
- Create (tests): `tests/capabilities/element/test_notation.py`, `test_contract.py`, `test_grammar.py`, `test_rules.py`, `test_capability.py`, `test_data_consistency.py`
- Modify: `paxman/capabilities/__init__.py` (lazy wiring, `__all__`), `paxman/api/bootstrap.py` (`_SHIPPED`, `element` between `Date` and `Email`), `tests/property/test_reentry_invariant.py` (ROWS + SUPPRESS_ROWS), `tests/integration/` (element pipeline module or extend per convention), `CONTEXT.md` (Notation/table entries), `README.md` (via `tools/generate_readme_table.py`), `CHANGELOG.md` (Unreleased/Added)
- No `paxman/core` change. No generator script. No `output_format` token inside `rules/` (CI-scanned).

---

### Task 1: Scaffold + registration skeleton

**Files:** `tools/new_capability.py` output (13 files), `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py:31-50`

**Goal:** Generate the skeleton with correct identity (`Element` / `element`) and wire registration so the suite's shipped-set gates see the new member.

- [ ] Run `uv run python tools/new_capability.py Element --name element --authority "IUPAC" --spec-name "Nomenclature of Inorganic Chemistry (IUPAC Recommendations 2005)" --spec-url "https://iupac.qmul.ac.uk/RedBook2005.pdf" --publication-year 2005 --default-format symbol`; rename the placeholder rule file to `rules/iupac_red_book_2005.py`; add `Element` to `paxman/capabilities/__init__.py` (`_LAZY`, `TYPE_CHECKING`, `__all__` sorted position) and to `bootstrap.py _SHIPPED` between `Date` and `Email`. Verify: `uv run pytest tests/unit/test_capability_exports.py tests/unit/test_bootstrap.py -q` → PASS (scaffold stubs must at least import; fill in Tasks 2–8).

### Task 2: Notation — frozen + slots token/shape

**Files:** `paxman/capabilities/Element/notation.py`, `tests/capabilities/element/test_notation.py`

**Goal:** Land `ElementNotation(token: str, shape: str)` with `symbol` tokens in IUPAC case (`Fe`), `name` tokens lowercase (`iron`), `atomic_number` tokens bare digits (`26`).

- [ ] Failing test first: frozen/hashable/slots, per-shape token convention (`test_frozen_slots_hash`, `test_shape_token_conventions`). Implement the dataclass (report §3.1 minus its `FE`-shaped docstring typo). Verify: `uv run pytest tests/capabilities/element/test_notation.py -v` → PASS.

### Task 3: Contract — symbol default, name offered, atomic_number de-offered

**Files:** `paxman/capabilities/Element/contract.py`, `tests/capabilities/element/test_contract.py`

**Goal:** `ElementContract` with `DEFAULT_OUTPUT_FORMAT = "symbol"`, `OFFERED_OUTPUT_FORMATS = frozenset({"name"})`, unanimous `create_contract()` block, and a docstring recording the ADR-0010 `atomic_number` de-offer (MacAddress `contract.py:21-26` pattern).

- [ ] Failing test first: defaults resolve (`None`/`"default"`/`"symbol"` → `"symbol"`), `"name"` resolves, `"atomic_number"` raises `ContractError`, unknown format raises `ContractError`, `suppress_common_words` defaults `False`. Implement per report §6.1 with the offered set reduced to `{"name"}`. Verify: `uv run pytest tests/capabilities/element/test_contract.py -v` → PASS.

### Task 4: Authority tables — 118-row registry snapshot

**Files:** `paxman/capabilities/Element/rules/data/periodic_table_ed2022.py`, `tests/capabilities/element/test_data_consistency.py` (skeleton asserts here, full cross-checks in Task 9)

**Goal:** Hand-authored plain tables: `SYMBOLS` (118, `H`..`Og`), `NAME_TO_SYMBOL` (118 IUPAC lowercase + `aluminum`/`cesium` aliases per Red Book Table I footnotes a/c → 120 entries), `Z_TO_SYMBOL` (1→`H`..118→`Og`), `SYMBOL_TO_NAME` (IUPAC spelling canonical — aliases resolve but never render).

- [ ] Failing test first: `test_registry_counts` (118 / 120 / 118), `test_aliases_resolve_to_canonical` (`aluminum`→`Al`, `cesium`→`Cs`), `test_z_boundaries` (1→`H`, 118→`Og`, no 0/119), `test_symbol_name_z_bijection` (every symbol reachable from all three maps). Transcribe from the IUPAC 04May22 table (report §15 URLs); verify counts against the report's inventory before writing rules. Verify: `uv run pytest tests/capabilities/element/test_data_consistency.py -v` → PASS.

### Task 5: Grammar keys — key-only tables, correct views

**Files:** `paxman/capabilities/Element/grammar/data/element_keys.py`

**Goal:** `SYMBOL_KEYS` (236 = 118 canonical + 118 lowercase, case-exact for `view=None`), `NAME_KEYS` (120 lowercase for `view="casefolded"`) — plain key sets, no mappings (grammar/rule boundary; capabilities AGENTS.md governance). The Z-branch label alternation lives inline in the Task 6 `RegexMatcher` pattern (label-required by construction).

- [ ] Failing test first (in `test_grammar.py`): `test_key_set_sizes` (`SYMBOL_KEYS == 236`, `NAME_KEYS == 120`), `test_no_allcaps_symbol_keys` (`FE`/`NO`/`IN` absent — report §13 D3), `test_no_retired_keys` (`Uut`/`ununtrium`/`sulphur` absent). Derive mechanically from the Task 4 tables (symbols: `{s, s.lower()}` — note single-letter lowercases collide with nothing; names: lowercase IUPAC + 2 aliases). Verify key asserts green before wiring matchers.

### Task 6: Grammar — one grammar, three kernel matchers

**Files:** `paxman/capabilities/Element/grammar/element_recognition.py`, `tests/capabilities/element/test_grammar.py`

**Goal:** `ElementRecognitionGrammar(name = semantics = "element_recognition", single_value=True, pre=StandardPre(empty_guard=True))` with matcher tuple `(_Z_MATCHER, _SYMBOL_MATCHER, _NAME_MATCHER)`: symbol `LexiconMatcher(view=None, boundary=isotope-guard, suppressible=True, emit folds `fe`→`Fe`)`; name `LexiconMatcher(view="casefolded", boundary=WORD, emit lowercases)`; Z `RegexMatcher` with label-required pattern per Background item 4 (NOT the report's group-projection emit — ISSN-style digit re-search; no custom `recognize()` override — base delegation).

- [ ] Failing test first, per report §2.1 RECOGNIZE rows: `Fe`/`fe`/`C`/`Og`, `iron`/`Iron`/`IRON`, `aluminium`/`aluminum`/`caesium`/`cesium`, `element 26` / `Z=26` / `Z = 92` / `atomic number 118` (span includes label, notation digits-only), plus boundary negatives `irony`, `Fe2O3`, `NaCl`, `56Fe`, `Fe-56`, `element26`, `Z26`, `FE`, `fE`, `Xx`, `Uut`, `element 1000` (4-digit → no claim), empty/whitespace → empty, span invariants (`raw_text == text[start:end]`), `single_value` attr, matcher attrs (`suppressible` flags). Implement matchers; Z emit follows the ISSN raw-research pattern (`_re.search(r"[0-9]{1,3}", raw)` → digits, `int()`-fold leading zeros). Verify: `uv run pytest tests/capabilities/element/test_grammar.py -v` → PASS.

### Task 7: Rules — one file per publication, LOOKUP_TABLE ×2

**Files:** `paxman/capabilities/Element/rules/iupac_red_book_2005.py` (`PUBLICATION` specification/2005 + `SectionIR31NamesAndSymbols`, name `"Section IR-3.1-names-and-symbols"`), `paxman/capabilities/Element/rules/iupac_periodic_table_ed2022.py` (`PUBLICATION` registry/`04 May 2022` + `SectionPtoeRegistry`, name `"Section PTOE-element-registry"`), `tests/capabilities/element/test_rules.py`

**Goal:** Shape-routed membership + normalization to the canonical symbol; `matches()`/`normalize()` never raise; `target_semantics = frozenset({"element_recognition"})`, `requires_features = frozenset()`; no `output_format` token anywhere under `rules/` (purity scan).

- [ ] Failing test first: symbol/name rule accepts all 118 symbols + 120 names and rejects `Xx`/`D`/`T`/`sulphur` (shape-gated `False` for `atomic_number` notations); registry rule accepts Z 1–118 incl. boundaries and rejects `0`/`119`/`300` (shape-gated `False` for symbol/name); `normalize` agreement across all three shapes for every row (`Fe`/`iron`/`26` → `Fe`); provenance attrs (authority `IUPAC`, kinds `specification`/`registry`, years 2005/2022, lifecycles `active`, citation scoping "as extended by 2010/2012/2016 recommendations" per report §5.2). Verify: `uv run pytest tests/capabilities/element/test_rules.py tests/unit/test_rule_output_format_purity.py -v` → PASS.

### Task 8: Capability seam — wiring + `format_value`

**Files:** `paxman/capabilities/Element/capability.py`, `tests/capabilities/element/test_capability.py`

**Goal:** `ElementCapability(name="element")`, `get_grammars()` → 1, `get_rules()` → 2, unanimous `create_contract()`, `format_value` identity for `symbol` + `SYMBOL_TO_NAME` lookup for `name` (no `atomic_number` branch — Background decision 6).

- [ ] Failing test first: wiring counts, registry name, `format_value` round-trips (`Fe`→`iron`→`Fe` via re-canonicalization in Task 10), `create_contract` defaults + `ContractError` parity with Task 3, notation frozen/slots re-asserted at the seam. Verify: `uv run pytest tests/capabilities/element/test_capability.py -v` → PASS.

### Task 9: Consistency + registration gates

**Files:** `tests/capabilities/element/test_data_consistency.py`, `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`

**Goal:** Prove the grammar/rule boundary and close the shipped-set gates: every lexicon key resolves in rule data; every rule-data member is reachable from some key; exports + bootstrap + re-entry-set membership see `element`.

- [ ] Extend Task 4's module: `test_every_symbol_key_in_symbols`, `test_every_name_key_in_name_map`, `test_every_z_in_range_recognizable` (label branch is generative — assert rule-side coverage 1–118), `test_no_grammar_key_maps_to_canonical` (keys carry no values — boundary audit). Verify: `uv run pytest tests/capabilities/element/ tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -q` → PASS.

### Task 10: Pipeline integration — amended §9 states under A0

**Files:** `tests/integration/test_element_pipeline.py` (new; follows per-capability integration convention with autouse `_clean_registry`)

**Goal:** Lock the report's §9 map as amended by A0: `Fe`/`IRON`/`aluminum`/`element 026`/`Z = 26` → `SUCCESS Fe`; `Xx` → `MISSING`; `element 119`/`Z = 300` → `INVALID`; `hello world`/`26`/`FE`/`Fe-56`/`ununtrium` → `MISSING`; `Fe and Cu` → `MultipleMentionsError`; `Iron (Fe)` → `SUCCESS Fe` (co-reference coalesces); `element 26 (iron)` → `SUCCESS Fe`.

- [ ] Failing test first, parametrized per row above, each asserting status + canonical value + single-value provenance (Red Book vs registry rule per shape) + span; plus suppression matrix: `in` flag-off → `SUCCESS In`, `in` flag-on whole-input → `SUCCESS In` with `suppressed_count == 0` (A0 exempt), single-value embedded prose flag-on (`Fe in water`) → `SUCCESS Fe` with `suppressed_count >= 1` and the `in` span observable in `suppressed_spans` (two distinct values such as `Fe` + `Cu` in one call stay `MultipleMentionsError` — never use multi-element prose for the suppression matrix). Verify: `uv run pytest tests/integration/test_element_pipeline.py -v` → PASS.

### Task 11: Re-entry gate + property suite (ADR-0010)

**Files:** `tests/property/test_reentry_invariant.py`, `tests/property/test_element_properties.py` (new, hypothesis `ci` profile — no registry except the re-entry module's documented `_fresh_registry` exception)

**Goal:** Structural landing gate plus ADR-0010 Property 2 coverage for the new member.

- [ ] Add ROWS entry `_row(Element, "Iron", "Fe")` (covers unset + `"default"` + offered `"name"`: re-entry of `"iron"` under the `name` contract must land on `"iron"` exactly) and SUPPRESS_ROWS `_row(Element, "In", "In", suppress_common_words=True)` (canonical-case input — lowercase `"in"` would trip the suite's `value == input` identity assert since `in`→`In`). Add hypothesis properties: sampled symbol/name/Z rows → self-canonicalization; `fe`/`Fe`/`iron`/`IRON`/`element 26` → same value; `format_value` identity across `symbol`/`name`; random ASCII → `MISSING` with high probability, `INVALID` only via the label branch. MILESTONE vectors verbatim (`Iron`→`Fe`, `fe`→`Fe`, `Gold`→`Au`, `Al`→`Al`, `Carbon`→`C`, `element 118`→`Og`, `Z = 92`→`U`, `atomic number 79`→`Au`) asserted in integration/property, not just unit. Verify: `uv run pytest tests/property/ -q` → PASS (re-entry suite covers all shipped rows).

### Task 12: Docs + changelog

**Files:** `CONTEXT.md`, `README.md` (`tools/generate_readme_table.py`), `CHANGELOG.md`, `docs/development/MILESTONE.md` row 22 (status cell only — `docs/development/` is ephemeral per its AGENTS.md)

**Goal:** Keep the three shipped surfaces in sync (root AGENTS.md: CONTEXT.md Notation/table entries update with every capability; README table is generated, never hand-edited).

- [ ] CONTEXT.md: `ElementNotation(token, shape)` glossary entry + capability table row (IUPAC Red Book 2005 + Periodic Table 04May22) + package-tree line; README: regenerate table; CHANGELOG `Unreleased/Added`: Element entry (coverage, canonical `symbol`, offered `name`, A0-correct suppression note, `atomic_number` deliberately unoffered per ADR-0010 with forward path). Verify: `uv run python tools/generate_readme_table.py --check` (or the tool's documented check mode) → clean; `git diff --stat` shows only the listed files.

### Task 13: Full gates + coverage

**Files:** repo-wide (no edits expected; fix fallout only)

**Goal:** Merge-blocking suite green per `.github/workflows/ci.yml`.

- [ ] Run `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green; then `uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q` with `coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → ≥95. Commit per task (`feature/element`); no `# type: ignore` / `# noqa` in `paxman/` source.

---

## Self-review (done before saving)

1. **Spec coverage:** MILESTONE vectors → Tasks 6/10/11; §2.1 every RECOGNIZE row → Task 6 tests; every DEFER/REJECT row names its mechanism (D3 all-caps keys absent, D6 isotope guard, placeholders/bare numbers no keys, `sulphur`/`fE` not keys) → Tasks 5–6; §5 provenance → Task 7; §6 contract/capability → Tasks 3/8; §9 states (A0-amended) → Task 10; §12 strategy + ADR-0010 gate → Tasks 10/11; open decisions D1/D2/D5/D6/D8/D11 locked in Background, D3/D7/D9/D10 carried as documented v1 scope (all-caps + `at. no.` → `extra_grammars` future; CIAAW weights deferred, no `include_*`; hand-authored data).
2. **Placeholder scan:** self-review list is clean — every task names files, test names, and the exact `uv run` verify.
3. **Type consistency:** `ElementNotation(token: str, shape: str)` everywhere; contract `symbol`/`{name}`; provenance (specification/2005, registry/04 May 2022); `target_semantics = {"element_recognition"}` on both rules; `format_value(value, output_format, notation) -> str` with identity + `name` only.
4. **Momus dry-run:** each task is startable in order (scaffold → notation → contract → data → keys → grammar → rules → seam → consistency → pipeline → re-entry → docs → gates); QA per task names tool + steps + expected PASS; references exist at the cited paths:lines.
