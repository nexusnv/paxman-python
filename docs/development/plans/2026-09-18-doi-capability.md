# DOI Capability Implementation Plan (MILESTONE row 11 / research 2026-09-18)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Ship a `doi` capability (22nd) that canonicalizes bare/case-variant/resolver-URL/`doi:`-label/`urn:doi:`/`info:doi/` DOI mentions to bare lowercase `10.registrant/suffix` with ISO 26324:2025 provenance — PARSER-only, no registry, no checksum.

**Architecture:** Minimal-surface capability (1 grammar + 1 rule, IBAN/ISSN/UUID shape): single `RegexStage` grammar with bare core + carrier groups (resolver host incl. `www.`, `doi:` label, `urn:doi:`/`info:doi/`), `word_only` guards, trailing-punctuation lookahead, and an ASCII-only fold (`_ascii_lower`, Handbook PDF-confirmed — never `str.lower()`); one PARSER rule (`Section 4-doi-syntax`); offered format `url` re-enters. Proxy URN-colon form DEFERRED, shortDOI REJECTED. Nothing in `paxman/core` or `paxman/engine` changes; no `rules/data/`, no `grammar/data/`.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `tools/new_capability.py` scaffolder, `paxman/core/grammar` RegexStage + BoundaryGuard (legacy pipeline, ORCID precedent).

**References:** `docs/development/MILESTONE.md:23` (row 11), `docs/development/research/2026-09-18-doi-canonicalization.md` (§§2–16, all vectors/tables), `docs/development/research/DOIHandbook_2025.pdf.md` (Ch.3 case rule:1557-1592, no-checksum:1594-1612, URN-colon proxy:2292-2307), `paxman/capabilities/ORCID/grammar/orcid_recognition.py:22-67` (carrier precedent), `HOW_TO_ADD_NEW_CAPABILITY.md` Steps 0/5/7/10, `docs/development/plans/2026-09-17-uuid-capability.md` (procedural precedent).

**Branch:** `feature/doi-capability` cut from `dev`. PR targets `dev`.

---

## File Structure

- Create (scaffolder, then fill): `paxman/capabilities/DOI/notation.py` — `DOINotation(prefix, suffix, canonical)` frozen+slots; `contract.py` — DEFAULT `doi`, OFFERED `{"url"}`; `capability.py` — wiring + `format_value`; `grammar/doi_recognition.py` — `_ascii_lower` + carrier pattern + trailing-punct lookahead; `rules/iso_26324_ed2025.py` — `Section4DOISyntax` PARSER + module `PUBLICATION`.
- Create (tests): `tests/capabilities/doi/test_notation.py`, `test_contract.py`, `test_grammar.py`, `test_rules.py`, `test_capability.py`, `tests/integration/test_doi_pipeline.py`, `tests/property/test_doi_properties.py`.
- Modify: `paxman/capabilities/__init__.py` (import + `__all__` + `_LAZY`), `paxman/api/bootstrap.py` (`_SHIPPED` import + tuple, alphabetical), `paxman/cli.py` (`doi` branch, alphabetical between date and element), `tests/property/test_reentry_invariant.py` (DOI ROWS entry per ADR-0010), `tests/property/test_output_format_preservation.py` (`("doi","url")`Kind + injectivity pair per ADR-0011), `docs/user/capabilities/doi.md` (new) + chooser/index/concepts/api-reference/citations/glossary/migration rows, `README.md` + `CONTEXT.md` tables/Notation, `AGENTS.md` + `paxman/capabilities/AGENTS.md` + `tests/AGENTS.md` counts (21→22), `CHANGELOG.md` (`## [Unreleased]`), README table via `tools/generate_readme_table.py`.
- No `paxman/core`, engine, `rules/data/`, or `grammar/data/` changes.

---

## Background the implementer needs

### Current state (verbatim)

No DOI code exists (`paxman/capabilities/__init__.py:17-38` lists 21 exports; no `DOI` entry; `paxman/api/bootstrap.py:36-57` `_SHIPPED` has no DOI). Closest shipped shape is ORCID: fused label `[\s:-]+` + host group (`orcid_recognition.py:22-35`), notation pre-computing carriers (`:46-52`), `format_value` selection-only. DOI differs: lowercase canonical, prefix/suffix split notation, ASCII-only fold, single rule, no registry.

### Design decisions (locked, from research §13 + PDF confirmation)

1. Canonical bare `doi` lowercase; `url` offered (`https://doi.org/<canonical>`), re-enters under default contract.
2. Registrant bound `10\.\d{4,9}(\.\d+)*` (P1793/scholid/Gilmartin consensus); shortDOI + 10-digit over-long excluded by construction. Spec tension recorded: Handbook allows unbounded lengths and future non-`10.` directories — v1 encodes current allocation practice; revisit on allocation change.
3. **Fold MUST be ASCII-only** (`_ascii_lower`, defined once in `grammar/doi_recognition.py`, used by `_doi_notation`): Handbook equivalence is Basic-Latin-only with no normalization — full-Unicode `str.lower()`/`casefold()` would conflate Handbook-distinct `Á`/`á`. No NFC/NFD anywhere in the DOI path.
4. Suffix may contain further `/` (split core on first `/`); `%2F` retained literally, never decoded (Handbook §4.7 per-part encoding).
5. EIDR-style suffixed check chars accepted structurally, never validated (Handbook §4.3.5 per-application exception).
6. Proxy URN-colon form (`https://doi.org/urn:doi:10.123:456`) DEFERRED — documented negative test, own carrier group later. `urn:doi:`/`info:doi:`/`www.` RECOGNIZED. Lowercase `doi:` is Foundation-current visual form (§4.4.1), not legacy.
7. DOI-vs-URL resolver overlap documented-not-solved (ORCID-URI precedent, per-contract resolution); `10.1000/182` pinned clean against Phone/Date.

---

### Task 1: Scaffold + Notation

**Files:** scaffolder output; fill `paxman/capabilities/DOI/notation.py`, `tests/capabilities/doi/test_notation.py`

- [ ] Run: `uv run python tools/new_capability.py DOI --name doi --authority "ISO" --spec-name "ISO 26324" --spec-url "https://www.iso.org/standard/88862.html" --publication-year 2025 --spec-version "2025" --default-format doi`. Failing test first: `test_frozen_slots_hash` + `test_canonical_split` (`10.1038/nature12345` → prefix/suffix/canonical) → FAIL (no module). Implement `DOINotation` per research §3.1. Verify: `uv run pytest tests/capabilities/doi/test_notation.py -v` → PASS.

### Task 2: Contract

**Files:** `paxman/capabilities/DOI/contract.py`, `tests/capabilities/doi/test_contract.py`

- [ ] Failing test: `test_default_doi_offered_url` + `test_unknown_format_contract_error` → FAIL. Implement `DOIContract` (research §6.1; `@dataclass(frozen=True)` without slots; `DEFAULT_OUTPUT_FORMAT = "doi"`, `OFFERED_OUTPUT_FORMATS = frozenset({"url"})`; no capability-specific params; fixed keyword-only common block on `create_contract`). Verify: `uv run pytest tests/capabilities/doi/test_contract.py -v` → PASS.

### Task 3: Grammar

**Files:** `paxman/capabilities/DOI/grammar/doi_recognition.py`, `tests/capabilities/doi/test_grammar.py`

- [ ] Failing tests: `test_bare_span`, `test_uppercase_ascii_fold` (`10.1038/NATURE12345` → `10.1038/nature12345`), `test_nonlatin_case_preserved` (`Á…` vs `á…` distinct canonicals), `test_no_unicode_normalization` (precomposed vs decomposed non-coalescence), `test_resolver_url_span`, `test_www_host_span`, `test_dx_http_hosts`, `test_doi_label_span`, `test_urn_info_carriers`, `test_handbook_case_vector` (`10.5594/SMPTE.ST2067-21.2020` ≡ `10.5594/sMPTE.sT2067-21.2020`), `test_trailing_punct_excluded` (`.`/`)`/`,` per terminator), `test_percent2f_literal`, `test_missing_suffix_slash_prefix`, `test_shortdoi_missing`, `test_overlong_registrant_missing` (10 digits), `test_urn_colon_form_missing` (DEFER negative), `test_left_glued_runs_missing`, `test_right_glue_merges_opaque_suffix` (variable-width suffix absorbs trailing alnum — research §8 row 17 refined during TDD), `test_name_semantics_single_value` → FAIL. Implement pattern per research §4.2 (`_DOI_PREFIX` 4–9 + dotted tail, quoteless `\S+` suffix, label/host/`info:doi`/`urn:doi` groups, `word_only` both sides, trailing-punct lookahead, `_ascii_lower` in `_doi_notation`). Verify: `uv run pytest tests/capabilities/doi/test_grammar.py -v` → PASS.

### Task 4: Rule

**Files:** `paxman/capabilities/DOI/rules/iso_26324_ed2025.py`, `tests/capabilities/doi/test_rules.py`

- [ ] Failing tests: `test_valid_structures` (bare/carrier/Handbook vectors), `test_normalize_exact_ascii_bare`, `test_eidr_suffix_accepted_unvalidated`, `test_provenance_attrs` (ISO/ISO 26324/2025/specification/2025), `test_strategy_parser_six_attrs`, `test_no_output_format_token` → FAIL. Implement `Section4DOISyntax` (research §5.2–5.3; `name = "Section 4-doi-syntax"`, `target_semantics = frozenset({"doi_recognition"})`, `requires_features = frozenset()`; `matches`/`normalize` never raise; normalize returns ASCII-folded `prefix/suffix`). Verify: `uv run pytest tests/capabilities/doi/test_rules.py tests/unit/test_rule_output_format_purity.py -v` → PASS.

### Task 5: Capability wiring + registration

**Files:** `paxman/capabilities/DOI/capability.py`, `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`, `paxman/cli.py`, `tests/capabilities/doi/test_capability.py`

- [ ] Failing tests: `test_wiring_counts` (1 grammar, 1 rule), `test_format_value_url_reenters` (`url` output re-recognized under default contract), `test_cli_doi_branch`, `test_shipped_contains_doi` → FAIL. Implement `get_grammars`/`get_rules`/`create_contract`/`format_value` (research §6.2; `url` → `f"https://doi.org/{notation.canonical}"`) + `__init__.py` import/`__all__`/`_LAZY` + `_SHIPPED` import/tuple (alphabetical) + cli.py `doi` branch (alphabetical). Verify: `uv run pytest tests/capabilities/doi/test_capability.py tests/unit/test_capability_exports.py -v` → PASS.

### Task 6: Integration + invariants

**Files:** `tests/integration/test_doi_pipeline.py`, `tests/property/test_reentry_invariant.py`, `tests/property/test_output_format_preservation.py`

- [ ] Failing tests: pipeline SUCCESS rows (research §7.1 worked normalizations + §12 real vectors), MISSING rows (no-`10.`/slash/suffix, shortDOI, URN-colon DEFER, over-long registrant), `MultipleMentionsError` on two distinct DOIs, `test_bare_numeric_sibling_clean` (`10.1000/182` vs Phone/Date), `test_resolver_url_overlap_documented` (DOI-vs-URL per-contract), `year=2020` → INVALID → FAIL. Extend re-entry ROWS (`_row(DOI, "10.1038/nature12345", "10.1038/nature12345")` — `url` fixed point rides the auto-derived formats) + preservation matrix (`("doi", "url"): "encoding"` + `_InjectivityPair("doi", DOI, "url", "10.1038/nature12345", "10.1000/182", "")`). Verify: `uv run pytest tests/integration/test_doi_pipeline.py tests/property/test_reentry_invariant.py tests/property/test_output_format_preservation.py -q` → PASS.

### Task 7: Property + docs

**Files:** `tests/property/test_doi_properties.py`, `docs/user/capabilities/doi.md`, `CHANGELOG.md`, `README.md`, `CONTEXT.md`, `AGENTS.md`

- [ ] Failing property tests: registrant synthesis (`10.` + 4–9 digits + dotted tail; 10-digit negative) × suffix alphabet (alnum + `.-_%/` incl. `%2F`) self-canonicalization, carrier-equivalence (bare/URL/`www.`/label/`urn:doi:`/`info:doi/`), random-printable MISSING bias, `url` round-trip → FAIL, then pass via Tasks 3–5 code (no new impl expected; documents fuzz robustness; `_fresh_registry` pattern per tests AGENTS.md only if driving the pipeline). Docs: `doi.md` guide (recognition table, statuses incl. URL overlap + DEFER/REJECT rows, executed snippet, ISO 26324 provenance) + chooser/index/concepts/api-reference/citations/glossary/migration rows + `tools/generate_readme_table.py` run (diff limited to DOI row) + README/CONTEXT tables (`| **DOI** | Digital object identifiers | ISO 26324:2025 |` + Notation subsection mirroring ORCID) + AGENTS counts 21→22 + CHANGELOG `Unreleased` Added entry. Verify: `uv run pytest tests/property/test_doi_properties.py -q` → PASS; snippet outputs executed, not assumed.

### Task 8: Full gate + PR

**Files:** none (verify + handoff).

- [ ] Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q && uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95` → all green (pre-existing findings on `dev` excluded by comparison with stashed baseline). Commit `feat(doi): DOI capability (ISO 26324:2025)`, review with `paxman-oracle-review` then open PR against `dev`.

---

Plan saved to docs/development/plans/2026-09-18-doi-capability.md — 8 tasks.

Execute task-by-task via tdd (failing test first). After impl, run paxman-momus-review on the plan file, then paxman-oracle-review on the branch diff before PR handoff.
