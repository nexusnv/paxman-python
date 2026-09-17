# UUID Capability Implementation Plan (#168-track / research 2026-09-16)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a `uuid` capability (21st) that canonicalizes hyphenated/bare/braced/URN UUID mentions to lowercase `8-4-4-4-12` with IETF RFC 9562 provenance — structure-only validation, no registry, no checksum.

**Architecture:** Minimal-surface capability (1 grammar + 1 rule, IBAN/ISSN shape): single `RegexStage` grammar with dashed|bare alternation plus optional brace/URN carrier groups and an ISBN-family trailing guard; one PARSER rule (`Section 4-uuid-format`); version/variant nibbles informative only (generation≠storage); offered formats `compact`/`braced`/`urn` all re-enter. Nothing in `paxman/core` or `paxman/engine` changes; no `rules/data/`, no `grammar/data/`.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `tools/new_capability.py` scaffolder, `paxman/core/grammar` RegexStage + BoundaryGuard (legacy pipeline, ORCID/ISBN precedent).

**References:** #168 (v0.6.0 parent — capability lands on `dev`, releases via promotion), `docs/development/research/2026-09-16-uuid-canonicalization.md` (§§2–16, all vectors/tables), `paxman/capabilities/ORCID/grammar/orcid_recognition.py:22-67` (alternation + carrier precedent), `paxman/capabilities/ISSN/grammar/issn_recognition.py:34-59` (trailing-guard precedent), `HOW_TO_ADD_NEW_CAPABILITY.md` Step 0, `CONTRIBUTING.md` § Branching and release.

**Branch:** `feature/uuid-capability` cut from `dev`. PR targets `dev`; closes the capability issue on merge (open one or fold into #168 scope when starting).

---

## File Structure

- Create (scaffolder, then fill): `paxman/capabilities/UUID/notation.py` — `UUIDNotation(compact, hyphenated, urn, version)` frozen+slots; `contract.py` — DEFAULT `hyphenated`, OFFERED `{compact, braced, urn}`; `capability.py` — wiring + `format_value`; `grammar/uuid_recognition.py` — body/branch/carrier pattern + trailing guard; `rules/rfc_9562_ed2024.py` — `Section4UUIDFormat` PARSER.
- Create (tests): `tests/capabilities/uuid/test_notation.py`, `test_contract.py`, `test_grammar.py`, `test_rules.py`, `test_capability.py`, `tests/integration/test_uuid_pipeline.py`, `tests/property/test_uuid_properties.py`.
- Modify: `paxman/capabilities/__init__.py` (import + `__all__`), `tests/property/test_reentry_invariant.py` (extend per ADR-0010), `tests/property/test_output_format_preservation.py` (compact/braced/urn matrix per ADR-0011), `docs/user/capabilities/uuid.md` (new) + chooser/index/citations/glossary/migration rows, `README.md` + `CONTEXT.md` tables, `AGENTS.md` counts, `CHANGELOG.md` (`## [Unreleased]`).
- No `paxman/core`, engine, `rules/data/`, or `grammar/data/` changes.

---

## Background the implementer needs

### Current state (verbatim)

No UUID code exists (`paxman/capabilities/__init__.py:15-36` lists 20; no `UUID` entry). Closest shipped shape is ORCID: 5-field notation pre-computing all carriers (`orcid_recognition.py:48-67`), `format_value` selecting from notation fields (`capability.py:58-74`), dual PARSER rules. UUID differs: one rule (single publication), lowercase canonical, `version` informative field instead of `check`.

### Design decisions (locked, from research §13)

1. Canonical `hyphenated` lowercase; version/variant never gate (ABNF silence + generation≠storage).
2. Nil/Max SUCCESS by structure, no dedicated rule.
3. `UUID:`/`GUID:` labels DEFERRED to `extra_grammars` (unattested); integer dumps REJECTED.
4. IBAN LLDD-32 overlap documented-not-solved (validation decides); URN-form vs URL grammar overlap pinned by a sibling test.
5. Trailing `(?![-][0-9A-Fa-f])` guard after the body (ISBN/ISSN precedent).

---

### Task 1: Scaffold + Notation

**Files:** scaffolder output; fill `paxman/capabilities/UUID/notation.py`, `tests/capabilities/uuid/test_notation.py`

- [ ] Run: `uv run python tools/new_capability.py UUID --name uuid --authority "IETF" --spec-name "RFC 9562" --spec-url "https://www.rfc-editor.org/rfc/rfc9562" --publication-year 2024 --spec-version "May 2024" --default-format hyphenated`. Failing test first: `test_frozen_slots_hash` + `test_version_values` (`compact[12]` digit, `"nil"`, `"max"`) → FAIL (no module). Implement `UUIDNotation` per research §3.1. Verify: `uv run pytest tests/capabilities/uuid/test_notation.py -v` → PASS.

### Task 2: Contract

**Files:** `paxman/capabilities/UUID/contract.py`, `tests/capabilities/uuid/test_contract.py`

- [ ] Failing test: `test_default_hyphenated_offered_three` + `test_unknown_format_contract_error` → FAIL. Implement `UUIDContract` (research §6.1; frozen, no slots; no capability-specific params). Verify: `uv run pytest tests/capabilities/uuid/test_contract.py -v` → PASS.

### Task 3: Grammar

**Files:** `paxman/capabilities/UUID/grammar/uuid_recognition.py`, `tests/capabilities/uuid/test_grammar.py`

- [ ] Failing tests: `test_canonical_span`, `test_bare_32_span`, `test_braced_span_includes_braces`, `test_urn_span_includes_prefix`, `test_uppercase_fold`, `test_nil_max_spans`, `test_33hex_missing`, `test_37char_missing`, `test_hyphen_suffix_no_prefix_fallback` (`…c8-12` → `[]`), `test_glued_runs_missing`, `test_name_semantics_single_value` → FAIL. Implement pattern per research §4.2 (dashed|bare + brace/URN groups + trailing guard, `word_only` both sides). Verify: `uv run pytest tests/capabilities/uuid/test_grammar.py -v` → PASS.

### Task 4: Rule

**Files:** `paxman/capabilities/UUID/rules/rfc_9562_ed2024.py`, `tests/capabilities/uuid/test_rules.py`

- [ ] Failing tests: `test_valid_structures` (all carriers), `test_normalize_exact_lowercase_hyphenated`, `test_version_nibble_informative` (v0/v9 still match), `test_provenance_attrs` (IETF/RFC 9562/May 2024/specification/2024), `test_strategy_parser` → FAIL. Implement `Section4UUIDFormat` (research §5.2–5.3; `matches`/`normalize` never raise; no `output_format` token). Verify: `uv run pytest tests/capabilities/uuid/test_rules.py -v` → PASS.

### Task 5: Capability wiring + registration

**Files:** `paxman/capabilities/UUID/capability.py`, `paxman/capabilities/__init__.py`, `tests/capabilities/uuid/test_capability.py`

- [ ] Failing tests: `test_wiring_counts` (1 grammar, 1 rule), `test_format_value_round_trips` (compact/braced/urn outputs re-recognized), `test_exports_complete` → FAIL. Implement `get_grammars`/`get_rules`/`create_contract`/`format_value` (research §6.2; pre-computed notation fields) + `__init__.py` import/`__all__`. Verify: `uv run pytest tests/capabilities/uuid/test_capability.py tests/unit/test_capability_exports.py -v` → PASS.

### Task 6: Integration + invariants

**Files:** `tests/integration/test_uuid_pipeline.py`, `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py`

- [ ] Failing tests: pipeline SUCCESS rows (Fig 1 vector, Python uuid3/uuid5-DNS vectors, Nil/Max), MISSING rows (bad length/charset), `MultipleMentionsError` on two distinct ids, `test_iban_overlap_uuid_success` (LLDD-32 → UUID SUCCESS + IBAN INVALID), `test_urn_form_url_overlap_documented`, `year=2020` → INVALID → FAIL. Extend re-entry suite (all 4 formats fixed points) + preservation matrix (compact/braced/urn). Verify: `uv run pytest tests/integration/test_uuid_pipeline.py tests/property/test_reentry_invariant.py tests/property/test_output_format_preservation.py -q` → PASS.

### Task 7: Property + docs

**Files:** `tests/property/test_uuid_properties.py`, `docs/user/capabilities/uuid.md`, `CHANGELOG.md`, `README.md`, `CONTEXT.md`, `AGENTS.md`

- [ ] Failing property tests: random-128-bit self-canonicalization, random-string MISSING bias, carrier-equivalence, format round-trips → FAIL, then pass via Tasks 3–5 code (no new impl expected; documents fuzz robustness). Docs: guide (recognition table, statuses incl. IBAN/URL overlaps, executed snippet, provenance) + chooser/index/citations/glossary/migration rows + README/CONTEXT tables + AGENTS counts + CHANGELOG `Unreleased` Added entry. Verify: `uv run pytest tests/property/test_uuid_properties.py -q` → PASS; snippet outputs executed, not assumed.

### Task 8: Full gate + PR

**Files:** none (verify + handoff).

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q && uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → all green (pre-existing ruff findings on `dev` excluded by comparison with stashed baseline). Commit `feat(uuid): UUID capability (RFC 9562)`, review with `paxman-oracle-review` then thermo-nuclear, open PR against `dev`.

---

Plan saved to docs/development/plans/2026-09-17-uuid-capability.md — 8 tasks.

Execute task-by-task via tdd (failing test first). After impl, run paxman-momus-review on the plan file, then paxman-oracle-review on the branch diff before PR handoff.
