# Phone `national` De-Offer + `split` Successor — ADR-0011 Phase 2

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** De-offer Phone `output_format="national"` per ADR-0011 (directed breaking change) and ship the information-preserving successor `split` — `+CC NSN`, uniform for every country code — so Phone's offered surface complies with the Information-Preservation invariant: param-free pre-image re-entry, entity-relative injectivity, no field removal.

**Architecture:** Phone-capability-only change. `split` renders via the existing `split_country_code` table (`+CC` + single space + NSN digits) and re-enters through the **existing** `E164Grammar` with zero grammar changes (leading `+` required, separators `[().\-\s]` tolerated inside the digit run, `e164_recognition.py:79-96`). The `national` render branch, the non-NANP preservation branch (`capability.py:149-160`), the construction gate, and `PHONE_NATIONAL_COUNTRIES` (`contract.py:74-78, 103-110`) are deleted. `default_country` stays for **input** recognition (NANP grammars/rules untouched). Recognition, rules, and notation do not change.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: `capability`, `property`), no new dependencies.

**References:**
- ADR: `docs/adr/0011-output-format-information-preservation.md` (Formal Statement corollaries; Consequences — directed Phone de-offer; baseline audit ledger row for `national`)
- Precedent: ADR-0010 Consequences ("de-offering is a breaking change requiring a migration note"); CHANGELOG `### Breaking` `bit_reversed` de-offer entry (line 19 — the wording pattern to mirror)
- Violation being removed: `paxman/capabilities/Phone/capability.py:142-160` (national branch + non-NANP preservation branch), `paxman/capabilities/Phone/contract.py:74-78` (`PHONE_NATIONAL_COUNTRIES` mirror), `:103-110` (construction gate), `tests/capabilities/phone/test_capability.py:310-360` (`TestPhoneNationalOutput` + `test_national_requires_default_country`), `tests/property/test_reentry_invariant.py:155-161` (Phone row's `default_country="US"` crutch)
- Recognition facts (verified 2026-09-06, no grammar change needed): `paxman/capabilities/Phone/grammar/e164_recognition.py:79-96` (`+` required; separator-skipping window; digit-ending guard), `:117` (non-example: bare `"15551234567"` unclaimed), `:44-64` (`_trim_to_e164_boundary` — 15-digit run-aware trim)
- Renderer inputs: `paxman/capabilities/Phone/rules/data/e164_country_codes.py` (`split_country_code` — longest-prefix assigned CC; the same function validation uses)
- Re-entry harness: `tests/property/test_reentry_invariant.py:90-105` (`_row` auto-derives formats from `OFFERED_OUTPUT_FORMATS`), `:161` (the Phone row to de-crutch)
- Docs to update: `CONTEXT.md:441` (`Phone ("e164"/"rfc3966"/"national")` list), `CONTEXT.md` (new `### Phone` subsection, after `### Coordinates`), `CHANGELOG.md` `### Breaking` (line 17 section head)
- Cross-entity pair for injectivity tests: GB `+4412341234` vs MY `+6012341234` (ADR-0011 audit Appendix)

**Branch:** `feature/adr0011-information-preservation` (continues Phase 0–1 work; same branch)

**Sequencing:** Phase 2 of the ADR-0011 sequencing (`docs/development/research/2026-09-05-output-format-information-preservation.md` §13 — plan-side citation only; nothing shipped here may reference `docs/development/*`). Phases 3 (Language) and 4 (suite hardening) are separate plans.

---

## Background the implementer needs

### The violation being removed (verified 2026-09-06)

`national` strips the country code — the exact field `split_country_code` (recognition routing) and `valid_e164_value` (assigned-CC validation) use — and re-enters only because the contract carries the missing information as `default_country` (`contract.py:103-110` rejects `national` without a NANP country; the re-entry suite's Phone row passes `default_country="US"` for the same reason). Its live defects: the only offered format in the repo that cannot re-enter under its **default** contract, and value-dependent output shape (`+1…` renders bare NSN; `+44…` renders E.164 via the preservation branch, `capability.py:154-159`). The GB/MY collision (`+4412341234` and `+6012341234` → `12341234`) is latent — prevented only by the preservation branch refusing to render non-NANP values as NSN at all.

### Successor set decision (locked): `split` only

`split` definition — from canonical `+CCNSN`: `"+" + CC + " " + NSN` (single ASCII space; NSN is the compact digit string). Examples: `+12125551234` → `+1 2125551234`; `+4412341234` → `+44 12341234`; `+6012341234` → `+60 12341234`.

Compliance argument (goes into the contract docstring):
- **No field removed**: CC, NSN, and the `+` sigil all survive; the space is presentation-only (stripped by `strip_separators` on re-entry).
- **Param-free pre-image**: `canonicalize("+1 2125551234", default_contract)` → `SUCCESS` `+12125551234` via the existing `E164Grammar` + E.164 rules — no contract parameter, for **every** assigned CC (uniform shape, no preservation branch).
- **Entity-relative injectivity**: `CC + space + NSN` is a bijection over the canonical space; the GB/MY pair renders `+44 12341234` vs `+60 12341234` — distinct.

Rejected successors (rationale recorded here and in the contract docstring):
- **`compact`** (`CCNSN`, no `+`) — rejected. `E164Grammar` requires a leading `+` (`e164_recognition.py:79`; docstring non-example `:117`), so bare digits cannot re-enter through it; a new bare-digit grammar would co-claim 10-digit runs with `NationalGrammar` (AMBIGUOUS under a NANP `default_country` contract, INVALID under the default contract). Not implementable without a recognition redesign that creates cross-grammar ambiguity — the exact failure ADR-0011 exists to prevent.
- **`loose`** (`+CC` + grouped NSN) — rejected for now. Per-CC dialing-display grouping requires authority grouping tables (scope creep); a NANP-only grouping makes the format's shape value-dependent. Forward path: community `extra_grammars` (the Element `atomic_number` precedent).
- `rfc3966` is unchanged and already compliant (wraps, never strips).

### Locked semantics decisions

1. **Extension handling**: `split` ignores `notation.extension` (the canonical value does not carry it; `rfc3966` is the only extension-preserving format — appending an extension would break re-entry since `E164Grammar` ends its span at the last digit). Documented in `format_value`.
2. **Migration message**: `PhoneContract.__post_init__` pre-checks `output_format == "national"` **before** `super().__post_init__()` and raises `ContractError` naming `split` (e.g. `"output_format 'national' was removed per ADR-0011 — it dropped the country code and could not re-enter without default_country. Use output_format='split' (renders '+1 2125551234') or the default 'e164'."`). The base class would raise a generic unsupported-format error; the pre-check gives callers the migration target. This replaces the old NANP gate at the same call position.
3. **Re-entry suite row goes param-free**: `_row(Phone, "+12125551234", "+12125551234")` — `default_country` kwarg and the crutch comment (`test_reentry_invariant.py:155-161`) are deleted. `_row` auto-derives formats from the new `OFFERED_OUTPUT_FORMATS` (`""`, `"default"`, `"rfc3966"`, `"split"`).
4. **No `CHANGELOG.md` rewrite of history**: the existing `national`-requires-`default_country` entry (line 20) stays; the new Breaking entry supersedes it.
5. **TDD order per task**: contract-surface test changes first (red), then contract change (green); capability render tests first (red), then renderer (green).

---

## File Structure

- Modify: `paxman/capabilities/Phone/contract.py` — `OFFERED_OUTPUT_FORMATS`, delete `PHONE_NATIONAL_COUNTRIES` + gate, add national migration pre-check, docstrings
- Modify: `paxman/capabilities/Phone/capability.py` — `format_value` national branch + preservation branch deleted, `_format_split` added, docstrings (`create_contract`, `format_value`)
- Test: `tests/capabilities/phone/test_capability.py` — `TestPhoneNationalOutput` → `TestPhoneSplitOutput` + migration-rejection tests
- Test: `tests/capabilities/phone/test_grammar.py` — split-render re-entry pins (recognition unchanged; pins only)
- Test: `tests/property/test_reentry_invariant.py` — Phone row de-crutched
- Docs: `CONTEXT.md` (line 441 + new `### Phone` subsection), `CHANGELOG.md` (Breaking entry)

No changes: `paxman/core/**`, engine, `Phone/grammar/**`, `Phone/rules/**` (incl. `nanp_ed2024.py` — `default_country` input gating stays), notation, README (no format column).

---

### Task 1: Contract surface — de-offer `national`, offer `split` (TDD: red first)

**Files:** `tests/capabilities/phone/test_capability.py`, then `paxman/capabilities/Phone/contract.py`

**Goal:** The contract surface changes with its tests proving the migration path.

- [ ] Red: in `test_capability.py`, replace `TestPhoneNationalOutput` (310-360) with `TestPhoneSplitContract`: `test_national_removed_with_migration_message` — `PhoneContract(output_format="national")` and `PhoneContract(output_format="national", default_country="US")` both raise `ContractError` whose message contains `"split"`; `test_offered_formats_set` — `OFFERED_OUTPUT_FORMATS == frozenset({"rfc3966", "split"})`; `test_split_resolves` — `PhoneContract(output_format="split").output_format == "split"`. Run: `uv run pytest tests/capabilities/phone/test_capability.py -k TestPhoneSplitContract -v` → FAIL (national still offered).
- [ ] Green: `contract.py` — `OFFERED_OUTPUT_FORMATS = frozenset({"rfc3966", "split"})`; delete `PHONE_NATIONAL_COUNTRIES` and its mirror comment (74-78); delete the NANP gate block in `__post_init__` (103-110); add the national migration pre-check (Background decision 2) before `super().__post_init__()`; rewrite `__post_init__` docstring (drop the NANP-gate paragraphs, document the migration pre-check); update the class docstring if it names national. Sweep for hardcoded assertions of the old set before running: `rg -n "national" tests/unit tests/capabilities/phone tests/integration tests/property tests/e2e` — update any test asserting `OFFERED_OUTPUT_FORMATS` contents or national behavior beyond the re-entry row (fixed in Task 3). Run: `uv run pytest tests/capabilities/phone tests/unit -v` → new tests PASS, remaining suite green except capability-render tests touched in Task 2.
- [ ] Commit: `feat(phone): de-offer national, offer split successor (ADR-0011 Phase 2)`.

### Task 2: Renderer — delete national + preservation branch, add `_format_split`

**Files:** `tests/capabilities/phone/test_capability.py`, `paxman/capabilities/Phone/capability.py`

**Goal:** Uniform `+CC NSN` rendering for every CC; no value-dependent shape.

- [ ] Red: add `TestPhoneSplitOutput` (reuse the setup/teardown registry pattern from the old class): `test_split_nanp` — `canonicalize("+12125551234", C("split"))` → `SUCCESS`, value `+1 2125551234`; `test_split_non_nanp_uniform` — `+4412341234` → `+44 12341234` (no preservation branch — same shape as NANP); `test_split_extension_ignored` — canonicalize a `tel:+12125550123;ext=45` input under `split` → `+1 2125550123` (no `;ext=`); `test_split_round_trip` — `canonicalize("+1 2125551234", default C)` → `SUCCESS` `+12125551234` (param-free pre-image); `test_split_injective_across_country_codes` — `canonicalize("+4412341234", C("split"))` and `canonicalize("+6012341234", C("split"))` render distinctly (GB/MY pair); `test_format_value_split_identity_equivalence` — default contract unchanged. Run → FAIL (no `split` branch; national branch still present).
- [ ] Green: `capability.py` — in `format_value`, delete the national branch and the preservation branch (`:149-160`); add `split` handling via new module-level `_format_split(value: str) -> str`: strip leading `+`, `split_country_code(digits)`; `None` → return `value` unchanged (defensive, same posture as the old unreachable branch, comment kept); else `f"+{cc} {digits[len(cc):]}"`. Update `format_value` docstring (drop national/preservation paragraphs; document `split` semantics + the extension-ignored decision + the compliance argument from Background). Update `create_contract` docstring (88-98): offered = `rfc3966`/`split`; national → removed per ADR-0011, see migration message; `default_country` described as input-only. Run: `uv run pytest tests/capabilities/phone -q` → PASS.
- [ ] Commit: `feat(phone): split renderer — uniform +CC NSN, preservation branch deleted (ADR-0011 Phase 2)`.

### Task 3: Re-entry suite de-crutched + recognition pins

**Files:** `tests/property/test_reentry_invariant.py`, `tests/capabilities/phone/test_grammar.py`

**Goal:** The Phone row becomes param-free like every other capability; the successor's re-entry path is pinned at the grammar layer.

- [ ] `test_reentry_invariant.py:155-161`: rewrite the comment block (drop the "lossy national rendering" explanation; state the row is param-free per ADR-0011 — pre-image recovery under the default contract is locked by the Phase 4 suite hardening) and change the row to `_row(Phone, "+12125551234", "+12125551234")` (no kwargs). The `_row` helper auto-picks `("", "default", "rfc3966", "split")` from the new `OFFERED_OUTPUT_FORMATS`. Run: `uv run pytest tests/property/test_reentry_invariant.py -k phone -v` → all 4 params PASS.
- [ ] `test_grammar.py`: add `test_e164_recognizes_split_render` (`"+1 2125551234"` → claimed, `value == "+12125551234"` after `strip_separators`) and `test_e164_recognizes_split_render_grouped` (`"+44 12341234"` → `"+4412341234"`) — pins the re-entry path the renderer relies on (recognition itself unchanged). Run: `uv run pytest tests/capabilities/phone/test_grammar.py -k split_render -v` → PASS (expected green — pins, not bug reproduction).
- [ ] Commit: `test(phone): param-free re-entry row + split recognition pins (ADR-0011 Phase 2)`.

### Task 4: Shipped docs + migration note

**Files:** `CONTEXT.md`, `CHANGELOG.md`

**Goal:** Callers find the new surface and the migration target without reading source; ADR-0010's migration-note obligation is discharged.

- [ ] `CONTEXT.md:441`: change `Phone ("e164"/"rfc3966"/"national")` → `Phone ("e164"/"rfc3966"/"split")`.
- [ ] `CONTEXT.md`: add a `### Phone` subsection immediately after `### Coordinates` (mirroring its shape): default `e164` (`+CCNSN`); offered `rfc3966` (`tel:+CCNSN[;ext=]`) and `split` (`+CC NSN`, e.g. `+1 2125551234` — single space, uniform for every CC, extension carried only by `rfc3966`); `national` de-offered per ADR-0011 (dropped the CC; could not re-enter without `default_country`; `ContractError` message names `split`). Presentation via `Capability.format_value()` only.
- [ ] `CHANGELOG.md` `### Breaking`: add an entry mirroring the `bit_reversed` wording pattern (line 19): **Phone — de-offer `national`, offer `split` (ADR-0011 Phase 2)** — `PhoneContract(output_format="national")` now raises `ContractError` with a migration message (was `SUCCESS` rendering the bare NSN for NANP values, E.164 otherwise). The format removed the country code recognition/validation depend on and could not re-enter under the default contract (param dependence; value-dependent shape; latent GB/MY collision). Migrate: `output_format="split"` renders `+1 2125551234` for `+12125551234` (uniform for all CCs, param-free re-entry); `e164`/`rfc3966` unchanged; `default_country` still supported for domestic **input** recognition.
- [ ] Verify: `rg -n '"national"' paxman/ CONTEXT.md README.md tests/` → expected hits only in historical CHANGELOG entries and the new migration message/contract docstring (which must reference it only as removed). Commit: `docs(phone): split surface docs + migration note (ADR-0011 Phase 2)`.

### Task 5: Full gate

**Files:** none.

- [ ] `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green; coverage ≥ 95. Confirm `rg -n "docs/development" paxman/ CONTEXT.md CHANGELOG.md tests/` → 0 hits.

---

## Out of scope (deliberate)

- `default_country` input behavior (NANP recognition/validation untouched — ADR-0011 Scope decision 4).
- `loose`/`compact` successors (rejected — Background; community `extra_grammars` forward path).
- Phase 3 (Language), Phase 4 (suite hardening: param-free rows for all offered formats, same-entity fixtures, cross-entity pair mandates) — separate plans.
