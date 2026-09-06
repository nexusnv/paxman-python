# Language Extended-Tag Carry — ADR-0011 Phase 3 (option b, code formats)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Remediate Language's projection violation (ADR-0011 baseline audit) for the three **code formats** — `alpha2`, `alpha3`, `alpha3-bib` now map only the primary subtag and **carry the remaining subtags through unchanged** (`en-US` → `en-US`, `zh-Hant-TW` → `zho-Hant-TW` under `alpha3`), making them encodings with exact param-free pre-image re-entry; `name` is kept under a **documented waiver** (it cannot preserve subtags re-enterably — Background decision 3).

**Architecture:** Renderer-only change in `LanguageCapability.format_value` (`paxman/capabilities/Language/capability.py:153-231`): today every offered format first calls `_primary_language(value)` (:57-61 — split before first hyphen, lower) and renders **only** the mapped primary, silently dropping region/script/variant/extension/privateuse subtags (`en-US` → `en`). The fix splits the canonical into `(primary, rest)` once, maps `primary` through each format's existing table lookups unchanged, and re-attaches `rest` with a single hyphen. Notation, grammars, rules, and the mapping tables are untouched — `rest` is copied verbatim, so anything the BCP 47 grammar recognized and the IANA rules validated re-enters unchanged.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: `capability`, `property`), no new dependencies.

**References:**
- ADR: `docs/adr/0011-output-format-information-preservation.md` (audit ledger — Language VIOLATION row; Consequences — Language remediation option (b) scheduled; Scope decision 3 — declared-quantization/pre-image corollaries)
- Research (plan-side citation only): `docs/development/research/2026-09-05-output-format-information-preservation.md` §7.1 (the projection + remediation options; recommendation (b))
- Violation being removed: `paxman/capabilities/Language/capability.py:57-61` (`_primary_language`), `:184-231` (`format_value` — `primary = _primary_language(value)` then primary-only mapping in all four branches)
- Canonical-space facts: `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py:54-148` (`_notation_from_tag` — compact preserves language+extlang+script+region+variant+extension+privateuse), IANA validation of region/script/variant: `paxman/capabilities/Language/rules/iana_language_subtag_registry_ed2026.py` + `rules/data/iana_{region,script,variant}_subtags.py`
- Mapping tables consumed unchanged: `capability.py:52-54` (`_ALPHA2_TO_T`, `_TERM_TO_BIB`, `_CANONICAL_TO_ENGLISH` — derived from rule data)
- Test surfaces: `tests/capabilities/language/test_capability.py`, `tests/property/test_reentry_invariant.py` (Language row + the ROWS/SUPPRESS_ROWS structural gate at :171-173)
- Docs: `CONTEXT.md` (new `### Language` subsection after `### Coordinates`/`### Phone`), `CHANGELOG.md` `### Changed`, ADR-0011 dated amendment note (name waiver)

**Branch:** `feature/adr0011-information-preservation` (continues Phase 2; same branch)

**Sequencing:** Phase 3 of the ADR-0011 sequencing; independent of Phase 2 (different capability, no shared code) but planned to land after it on the same branch. Phase 4 (suite hardening) follows both.

---

## Background the implementer needs

### The violation being removed (verified 2026-09-06)

For canonical `en-US`, `format_value(..., "alpha2")` returns `"en"`: the region subtag — which BCP 47 syntax (`SectionBCP47Syntax`) and IANA-registry validation (`SectionIANARegistry` + region/script/variant data tables) both consume — is dropped before rendering. Worse than Phone: the truncated value is itself a valid smaller entity, so `canonicalize("en", C(alpha2))` succeeds and lands on `"en"` — ADR-0010's `V→V` passes while the entity silently changed (`en-US` ≠ `en`; `F(en-US) == F(en-GB) == "en"` collides). The same projection runs in all four offered formats via the shared `primary = _primary_language(value)` step (:184).

### The fix (option b) — map primary, carry the rest

Split once at the first hyphen: `primary, rest = value.split("-", 1)` (with `rest = ""` when no hyphen). Every branch's existing primary mapping logic is unchanged; the return value becomes `mapped + ("-" + rest if rest else "")`. Worked rows (canonical → rendered):

| Canonical | `alpha2` | `alpha3` | `alpha3-bib` | `name` (waived — unchanged) |
|---|---|---|---|---|
| `en` | `en` | `eng` | `eng` | `English` |
| `en-US` | `en-US` | `eng-US` | `eng-US` | `English` *(projection, waived)* |
| `zh-Hant-TW` | `zh-Hant-TW` | `zho-Hant-TW` | `zho-Hant-TW` | `Chinese` *(waived)* |
| `de-CH-1901` | `de-CH-1901` | `deu-CH-1901` | `ger-CH-1901` | `German` *(waived)* |
| `x-foo` | `x-foo` | `x-foo` | `x-foo` | unchanged behavior *(see decision 3)* |
| `deu` | `de` *(today's behavior, kept)* | `deu` | `ger` | unchanged |

Why each code-format rendering re-enters (the compliance argument for the contract docstring): the mapped primary plus verbatim subtags is itself a BCP 47 tag the shipped `BCP47TagGrammar` recognizes and `SectionBCP47Syntax`/`SectionIANARegistry` validate — `canonicalize(W, default_contract)` returns `W`'s canonical **exactly** (encodings: exact pre-image, ADR-0011 Corollary 2). Injectivity: `en-US` and `en-GB` render distinctly (the GB/MY analogue at code level).

### Design decisions (locked)

1. **Carry is verbatim** — `rest` is never re-normalized, re-cased, or validated by the renderer; it is canonical input copied through. If it re-enters (it does — the canonical space is closed under the BCP 47 grammar), the rendering re-enters.
2. **Private-use and irregular shapes ride along**: `x-foo` — today `alpha2` renders `"x"` (the bare `x` primary misses every table); with carry it renders `x-foo` (identity — strictly better and re-enterable via the private-use path). Grandfathered tags canonicalize to their **preferred** value per `GRANDFATHERED_PREFERRED` (e.g. `i-klingon` → `tlh`), so by the time `format_value` runs there are usually no irregular subtags left; Task 1's empirical step confirms the two shipped examples before any test row pins them. `zh-cmn`-style extlang compacts are confirmed empirically in Task 1 rather than assumed (extlang preferred-value folding may collapse them — pin only what the run shows).
3. **`name` is a documented waiver, not option (b)**: carrying subtags into the English name (`English-US`) fails re-entry — it is not a `LanguageNameGrammar` lexicon key (WholeInputLookup) and `english` is not a registered primary subtag, so `canonicalize("English-US")` → `INVALID`, an ADR-0010 Property 2 violation worse than the projection. `name` therefore keeps today's primary-name rendering for extended tags: compliant for bare codes (injective, re-enterable), a **waived projection** for extended tags under the ADR-0011 soft mandate (waivers cite the audit, §8.2). The waiver is recorded in the contract/capability docstrings, `CONTEXT.md`, a dated amendment note on ADR-0011, and flagged for the hard-mandate promotion ADR (decision then: de-offer vs. a locale-aware name grammar).
4. **Re-entry suite gains an extended-tag Language row**: `_row(Language, "en-US", "en-US")` added beside the existing bare row — safe under the current suite (Property 2 is `W→W`, which holds for every format including the waived `name`: `canonicalize("English", C(name))` → `"en"` → renders `"English"` again), and it pins the new carry behavior for the code formats. The structural gate (`{row.name for row in ROWS} == shipped set`, :171-173) is set-based — duplicate capability names are fine.
5. **TDD order**: extended-tag render tests first (red — today they return projected values), then the renderer change (green).
6. **No shipped file references `docs/development/*`** — docstrings cite ADR-0011 and `tests/` artifacts only.

---

## File Structure

- Modify: `paxman/capabilities/Language/capability.py` — `format_value` carry-rest for `alpha2`/`alpha3`/`alpha3-bib`; docstrings (class + `format_value`) documenting carry + the `name` waiver
- Modify: `paxman/capabilities/Language/contract.py` — class docstring: offered formats, carry semantics, waiver note
- Test: `tests/capabilities/language/test_capability.py` — extended-tag carry suite + name-waiver lock + injectivity pair
- Test: `tests/property/test_reentry_invariant.py` — extended-tag Language row
- Docs: `CONTEXT.md` (`### Language` subsection), `CHANGELOG.md` (`### Changed` entry), `docs/adr/0011-output-format-information-preservation.md` (dated amendment note)

No changes: `Language/grammar/**`, `Language/rules/**`, notation, README (no format column).

---

### Task 1: Confirm canonical-space facts empirically + red tests

**Files:** `tests/capabilities/language/test_capability.py`

**Goal:** Pin no assumption; the carry tests encode verified behavior.

- [ ] Empirical step (paste output into PR description):

  ```bash
  uv run python -c "
  from paxman.api.bootstrap import register_all_shipped
  from paxman.core.discovery import reset_registry
  from paxman.api.canonicalize import canonicalize
  from paxman.capabilities import Language
  reset_registry(); register_all_shipped()
  for text in ('en-US', 'zh-Hant-TW', 'de-CH-1901', 'x-foo', 'zh-cmn', 'i-klingon'):
      r = canonicalize(text, Language.create_contract())
      print(repr(text), r.status.name, repr(r.canonicalized_value))
  "
  ```

  Expect: `en-US`/`zh-Hant-TW`/`de-CH-1901`/`x-foo` canonicalize to themselves; `i-klingon` → its preferred value (e.g. `tlh`); `zh-cmn` → whatever the shipped rules produce (pin only what this prints).
- [ ] Red: add `TestLanguageExtendedTagCarry` — for the canonicals confirmed above (minimum: `en-US`, `zh-Hant-TW`, `de-CH-1901`, `x-foo`): `alpha2`/`alpha3`/`alpha3-bib` renderings equal the Background table's carry rows (e.g. `canonicalize("zh-Hant-TW", C("alpha3"))` → `zho-Hant-TW`); `test_carry_reenters_param_free` — `canonicalize(W, default contract)` → `SUCCESS`, canonical == W for each carried rendering; `test_carry_injective_en_us_en_gb` — `alpha2` renderings of `en-US` and `en-GB` differ; `test_name_waived_projection_locked` — `name` of `en-US` is `English` (today's behavior, waiver comment citing ADR-0011); `test_bare_codes_unchanged` — `en`→`en`/`eng`, `deu`→`de`/`deu`/`ger` under the three code formats. Run: `uv run pytest tests/capabilities/language/test_capability.py -k ExtendedTagCarry -v` → FAIL (carry rows render projected values today; `name`/bare rows PASS already).

### Task 2: Renderer — carry the rest (green)

**Files:** `paxman/capabilities/Language/capability.py`

**Goal:** The three code formats become encodings.

- [ ] In `format_value` (:153-231): after the identity early-return, replace `primary = _primary_language(value)` with `primary, rest = value.split("-", 1) if "-" in value else (value, "")` (lowercase `primary` as `_primary_language` does — reuse it for the lowercase half: `primary = _primary_language(value)` stays, plus `rest = value.split("-", 1)[1] if "-" in value else ""`); in the `alpha2`, `alpha3`, and `alpha3-bib` branches, wrap each return: `mapped + (f"-{rest}" if rest else "")`. The `name` branch is untouched — add the waiver comment (Background decision 3) above it. `_primary_language` itself is unchanged.
- [ ] Docstrings: `format_value` — document carry semantics + compliance argument (re-enters exactly; cite ADR-0011) + the `name` waiver; class docstring (:64-81) — one sentence on offered-format carry.
- [ ] `contract.py`: class docstring — default `bcp47`; offered `alpha2`/`alpha3`/`alpha3-bib` (map the primary subtag, carry the remaining subtags verbatim — encodings per ADR-0011) and `name` (English name of the primary subtag; **waived projection for extended tags** per ADR-0011 soft mandate — extension-preservation would break re-entry; revisit at the hard-mandate promotion).
- [ ] Run: `uv run pytest tests/capabilities/language -q` → PASS (red rows green; no bare-code/name regressions). Commit: `feat(language): alpha2/alpha3/alpha3-bib carry extended subtags (ADR-0011 Phase 3)`.

### Task 3: Re-entry suite + waiver governance

**Files:** `tests/property/test_reentry_invariant.py`, `docs/adr/0011-output-format-information-preservation.md`, `CHANGELOG.md`

**Goal:** The extended-tag surface is locked in CI; the waiver is on the ADR record.

- [ ] `test_reentry_invariant.py`: beside the existing Language row, add `_row(Language, "en-US", "en-US")` with a comment (extended-tag surface; code formats carry subtags per ADR-0011 Phase 3; `name` is the waived projection — `W→W` still holds). Run: `uv run pytest tests/property/test_reentry_invariant.py -k language -v` → PASS (12 params: 6 per row — `""`, `"default"`, 4 offered — × 2 rows).
- [ ] ADR-0011: append a dated amendment note to the Consequences section (ADR-0010's amendment style): *Amendment (execution date — ADR-0011 Phase 3).* Language option (b) landed for `alpha2`/`alpha3`/`alpha3-bib` (carry subtags; encodings, exact pre-image). `name` is retained under a documented waiver: subtag-carrying names do not re-enter (not lexicon keys; unregistered primary), so `name` stays a primary-name projection for extended tags — revisit (de-offer vs. locale-aware name grammar) at the hard-mandate promotion.
- [ ] `CHANGELOG.md` `### Changed`: entry — Language `alpha2`/`alpha3`/`alpha3-bib` of extended tags now carry the subtags (`en-US` → `en-US`, was `en`; `zh-Hant-TW` → `zho-Hant-TW` under `alpha3`) per ADR-0011 (the projection silently changed the entity). `name` is unchanged (waived projection, ADR-0011 amendment). Bare-code rendering unchanged.
- [ ] Verify: `uv run pytest tests/property/test_reentry_invariant.py -q` → PASS. Commit: `test(property)+docs: extended-tag re-entry row, ADR-0011 waiver amendment (Phase 3)`.

### Task 4: CONTEXT.md + full gate

**Files:** `CONTEXT.md`

- [ ] Add a `### Language` subsection after `### Phone` (mirroring its shape): default `bcp47` (case-canonical tag); offered `alpha2`/`alpha3`/`alpha3-bib` (map the primary subtag, carry region/script/variant/extension/privateuse verbatim — `en-US` → `en-US`, `zh-Hant-TW` → `zho-Hant-TW`) and `name` (English name of the primary subtag — `en-US` renders `English`; waived projection for extended tags per ADR-0011). Presentation via `Capability.format_value()` only.
- [ ] Full gate: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green; coverage ≥ 95; `rg -n "docs/development" paxman/ CONTEXT.md CHANGELOG.md docs/adr/0011-output-format-information-preservation.md tests/` → 0 hits. Commit: `docs(language): carry semantics in CONTEXT.md (ADR-0011 Phase 3)`.

---

## Out of scope (deliberate)

- `name` remediation (locale-aware name grammar or de-offer) — decided at the hard-mandate promotion ADR; waiver recorded in Task 3.
- Phase 4 suite hardening (param-free rows for all capabilities' offered formats, same-entity expansion fixtures, mandatory cross-entity pair matrix) — separate plan; the Language/Phone rows added here are precursors, not the matrix.
- Grammars/rules/table data — untouched; the canonical space and its validation are consumed as-is.
