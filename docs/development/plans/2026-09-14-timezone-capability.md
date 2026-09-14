# Timezone + UtcOffset Capabilities Implementation Plan (MILESTONE #3)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl). DO NOT implement until explicitly told.

**Goal:** Ship `Timezone` (IANA identifiers: keys resolve, Links resolve to canonical, abbreviations refused) and `UtcOffset` (numeric offsets → `+HH:MM`) capabilities with full provenance, closing MILESTONE roadmap #3.

**Architecture:** Two scaffolder-built packages sharing no code (file-disjoint, parallelizable): `Timezone` = 2 lexicon grammars (name with custom `/`-aware boundary + folded view; abbreviation UPPER-exact) + 2 LOOKUP_TABLE rules (membership/link-resolution, abbreviation refusal) over vendored tzdb snapshot data; `UtcOffset` = 1 regex grammar (human-notation offsets + slash-aware lookbehind) + 1 PARSER rule (shape/range, `-00:00` refused). No contract/engine/core changes (one new `BoundaryGuard` variant lives in the capability, mac_midrun precedent — or `BoundarySpec` composition if the kernel already expresses it; implementer checks first).

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property), `tools/new_capability.py`, `paxman/core/grammar` matchers.

**References:** MILESTONE #3 (no tracking issue yet — suggested title `[New] Timezone + UtcOffset capabilities`); `docs/development/research/2026-09-14-timezone-canonicalization.md` §§2–16 (entity split §7.4/§13.1, carve rule §10–11, evidence classes §4.7, proofs §4.8, guard table §4.4, file layout §11); `paxman/capabilities/MacAddress/` (newest-capability precedent: notation/contract/grammar/rule shape); `paxman/capabilities/Country/grammar/name_recognition.py:33-57` (lexicon keys-only + trie + folded view); `paxman/capabilities/Language/rules/iso_639_1_ed2002.py:49-57` (deprecated-map resolution mechanics); HOW_TO_ADD_NEW_CAPABILITY.md Steps 0/5/7/10; HOW_TO_ADD_NEW_GRAMMAR.md (Option B new semantics ids).

**Branch:** `feature/timezone-capability` (already exists — research committed).

---

## File Structure

- Create via scaffold: `paxman/capabilities/Timezone/` + `paxman/capabilities/UtcOffset/` (each: `__init__.py`, `notation.py`, `contract.py`, `capability.py`, `grammar/`, `rules/`, `rules/data/`) + `tests/capabilities/timezone/` + `tests/capabilities/utc_offset/` + `paxman/capabilities/__init__.py` wiring (Step 0 command in Task 1).
- Create data: `Timezone/rules/data/iana_zone_identifiers.py`, `iana_zone_links.py`, `iana_fixed_zones.py`, `abbreviation_map.py` (File-Date 2026d snapshot lines per research §5.5/§7.3 table).
- Create docs: `docs/user/capabilities/timezone.md`, `docs/user/capabilities/utcoffset.md` (7-section guide precedent), `docs/user/capabilities/index.md` rows.
- Docs: `CHANGELOG.md`.
- No `paxman/core`, engine, contract-base, or sibling-capability changes.

---

## Background the implementer needs

### Current state (verbatim)

Greenfield: no timezone code exists in-tree (`grep timezone paxman/capabilities/__init__.py` empty). All design answers live in the research report; the load-bearing ones: (1) split — `Timezone` identifiers only, `UtcOffset` offsets (`+HH:MM` canonical, `basic` offered, `-00:00` INVALID); (2) carve — name lexicon excludes short-caps backward Links (`EST`/`CET`/… → INVALID via abbreviation family); (3) folding safe by namespace construction (POSIX rules forbid case variants — assert over vendored set); (4) OFFERED={} for Timezone v1; (5) membership = full identifier set (zone1970 geographic subset + etcetera/UTC + backward; never zone1970.tab alone); (6) vendored snapshot, never environment tzdata (minimal containers omit Links — probed 2026-09-14).

### Design decisions (locked)

1. Scaffold both packages with Step 0 first; bodies per research §§3–7 (no pasted bodies in this plan — report is the spec).
2. TDD per task below; goldens: §8 edge table (18 rows) + §9 matrix + §12 vectors are the acceptance corpus — every row becomes a named test.
3. `BoundaryGuard.timezone_slash_only()` (or equivalent `BoundarySpec` composition — implementer checks kernel first, mac_midrun precedent).
4. Re-entry: every SUCCESS canonical re-canonicalizes (incl. link-resolved keys, folded case, `basic` offset form); `test_reentry_invariant.py` extended per ADR-0010.
5. Deferrals stay deferred: Windows (no flag, no grammar), POSIX strings, military letters, space-underscore, `link` output, `TZ:` labels (community `extra_grammars` on evidence only).

---

### Task 1: Scaffold both packages (HOWTO Step 0)

**Files:** `tools/new_capability.py` invocation; `paxman/capabilities/__init__.py` wiring

**Goal:** 13-file skeletons + wiring compile; all TODO(scaffold) markers visible.

- [ ] Run: `uv run python tools/new_capability.py Timezone --name timezone --authority "IANA" --spec-name "Time Zone Database" --spec-url "https://www.iana.org/time-zones" --publication-year 2026 --default-format iana` and the `UtcOffset` equivalent (`--authority "ISO" --spec-name "ISO 8601-1" --spec-url "https://www.iso.org/standard/70907.html" --publication-year 2019 --default-format extended`). Verify: `uv run python -c "import paxman.capabilities.Timezone, paxman.capabilities.UtcOffset"` → PASS; scaffold test stubs collected (`uv run pytest tests/capabilities/timezone tests/capabilities/utc_offset --collect-only`).

### Task 2: Notations — frozen+slots (AGENTS.md Conventions)

**Files:** `paxman/capabilities/Timezone/notation.py`, `paxman/capabilities/UtcOffset/notation.py`, `tests/capabilities/timezone/test_notation.py`, `tests/capabilities/utc_offset/test_notation.py`

- [ ] Failing tests: `test_frozen_slots_hash` per package → FAIL. Implement: `TimezoneNotation(key, family, compact)` + `UtcOffsetNotation(compact)` per research §3.1 (family ∈ name/abbreviation only). Verify: both notation suites → PASS.

### Task 3: Contracts — frozen-no-slots, OFFERED discipline (ADR-0011)

**Files:** both `contract.py`, both `test_contract.py`

- [ ] Failing tests: default/offered resolution (`iana` default + `link`→ContractError; `extended` default + `basic` offered + `abbreviation`→ContractError) + `include_systemv` flag shape → FAIL. Implement: `TimezoneContract` (OFFERED empty, `include_systemv=False`) + `UtcOffsetContract` (DEFAULT `extended`, OFFERED {`basic`}) per research §6. Verify: both contract suites → PASS.

### Task 4: Authority data tables (vendored snapshot)

**Files:** `Timezone/rules/data/*.py` (4 modules per §11)

**Goal:** Identifier set + links + carve/refusal sets as plain tables with File-Date headers.

- [ ] Failing tests: consistency stubs (membership spot-checks: `America/New_York` ∈ identifiers, `us/eastern` ∈ links, `EST` ∈ carve set, `thai`-class absence n/a) → FAIL. Implement: tables from tzdb 2026d (zone1970 + backward + etcetera per research §5.5; abbreviation starter §7.3). Verify: `uv run pytest tests/capabilities/timezone/test_data_consistency.py -q` → PASS.

### Task 5: Grammars — name/abbreviation lexicons + slash guard + offset regex

**Files:** `Timezone/grammar/timezone_name_recognition.py`, `timezone_abbreviation_recognition.py`, `UtcOffset/grammar/utc_offset_recognition.py`, per-grammar tests

- [ ] Failing tests first per family: name (`America/New_York`, `US/Eastern` span, `america/new_york` fold, `XUS/Eastern` MISSING, zoneinfo-path MISSING), abbreviation (`EST`/`IST` claimed spans), offset (`UTC+5`, `+0530`, `Z`, `Etc/GMT+5`-span MISSING, `-00:00` shape behavior per rule) → FAIL. Implement: lexicons (folded view + carve exclusion; UPPER-exact) + custom slash guard + offset regex with slash lookbehind (research §4.2/§4.4). Verify: grammar suites → PASS; `uv run ruff check` clean.

### Task 6: Rules — membership/link/refusal/offset (one file per publication)

**Files:** `Timezone/rules/iana_tzdb_ed2026.py`, `iana_tz_abbreviations_ed2026.py`, `UtcOffset/rules/iso8601_offset_ed2019.py`, per-rule tests

- [ ] Failing tests: `US/Eastern`→`America/New_York`, `EST`→False, `IST`→False, `+0530`→`+05:30`, `-00:00`→False, provenance six-attrs present → FAIL. Implement: LOOKUP membership + link resolution + refusal table + PARSER range (research §§5.2/7). Verify: rule suites → PASS; purity scan green (no `output_format` in rules).

### Task 7: `format_value` seams + re-entry (ADR-0010/0011)

**Files:** both `capability.py` (`format_value`), `tests/capabilities/*/test_capability.py`

- [ ] Failing tests: `basic` re-entry (`+0530`→`+05:30`→`+0530`), link-resolved re-entry, fold re-entry; `link`/`abbreviation`-output ContractErrors → FAIL. Implement: seams only (identity default; `basic` encode). Verify: capability suites + `tests/property/test_reentry_invariant.py` (extended) → PASS.

### Task 8: Registration + consistency + pipeline/integration/property

**Files:** wiring (Task 1), `test_data_consistency.py`, integration + property suites

- [ ] Failing tests: §8 edge table (18 rows) + §9 matrix as named integration tests; hypothesis self-canonicalization property → FAIL. Implement: wire through green (no new code expected beyond fixes). Verify: `uv run pytest tests/capabilities/timezone tests/capabilities/utc_offset tests/integration -q` → PASS.

### Task 9: Guides + CHANGELOG + gate

**Files:** `docs/user/capabilities/timezone.md`, `utcoffset.md`, `index.md` (2 rows), `CHANGELOG.md`

- [ ] Guides mirror `mac_address.md` (7 sections; every snippet executed `uv run python`). CHANGELOG Added entries. Gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest` → green; coverage ≥95. Commit per task.
