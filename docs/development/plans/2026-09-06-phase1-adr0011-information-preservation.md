# Information-Preservation Invariant — ADR-0011 (Phase 1, must-implement)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Lock the Information-Preservation (Output-Format Equality) invariant as **ADR-0011** — offered formats must be encodings, same-entity expansions, or documented quantizations, never projections over recognition/validation information, with entity-relative injectivity and a param-free (or bounded-drift) pre-image corollary — and wire its cross-references into ADR-0010, root `AGENTS.md`, and `CONTEXT.md`.

**Architecture:** Docs-only change. No source, test, or configuration change. The ADR records the decision, the four-class format taxonomy, the formal statement (verbatim, locked in Task 2), the all-18 baseline audit as a self-contained ledger, the soft mandate (new formats comply now; Phone `national` directed de-offer and Language option (b) are sequenced follow-ups, not this plan), and the hard-promotion criteria for a future CI-gate ADR. The binding relationship to ADR-0010 is "strengthens, does not amend": re-entry stays required; injectivity and pre-image recovery are added on top.

**Tech Stack:** Markdown ADR only. Verification is the standard gate (ruff/format/pyright/import-linter/pytest) plus two content greps; no behavior surface is touched.

**References:**
- Research (origin document, plan-side citation only): `docs/development/research/2026-09-05-output-format-information-preservation.md` — §2 (entity + four-class taxonomy), §8 (formal statement, soft/hard mandate), §6 (baseline audit table to embed), §13 (sequencing; this plan is Phase 1)
- Predecessor ADR (structure + invariant-family precedent): `docs/adr/0010-re-entry-fixed-point-invariant.md` (Accepted 2026-09-03; scope-decision and Consequences style mirrored), `docs/adr/0004-single-value-invariant.md` (invariant-family root)
- Phase 0 evidence the ADR cites (must have landed first): `tests/property/test_coordinates_quantization.py` (dms/dm fixpoint + bounded drift), `docs/development/plans/2026-09-06-phase0-coordinates-quantization-obligations.md`
- Violation evidence (cited from the ADR as codebase primaries): `paxman/capabilities/Phone/capability.py:142-160` (national render + preservation branch), `paxman/capabilities/Phone/contract.py:103-110` (construction gate), `tests/property/test_reentry_invariant.py:155-161` (Phone row's `default_country` crutch), `paxman/capabilities/Language/capability.py:153-231` (`_primary_language` projection), `paxman/capabilities/Coordinates/capability.py:39-78` (dms/dm quanta), `paxman/core/capability_contract.py` (`resolve_output_format` seam)
- Numbering: `docs/adr/` currently ends at `0010` — `0011` is free (verified 2026-09-06)
- Docs self-containment rule: `docs/development/AGENTS.md` hard guidance — the ADR is shipped-adjacent durable documentation and **must not reference `docs/development/*`**; it embeds its own audit ledger instead

**Branch:** `feature/adr0011-information-preservation`

**Sequencing:** Phase 1 of the output-format invariant sequencing; depends on Phase 0 (Coordinates quantization obligations) having landed. Phases 2 (Phone de-offer), 3 (Language remediation), and 4 (suite hardening) are separate plans that cite this ADR — they are explicitly **out of scope here**.

---

## Background the implementer needs

### Current state (verified 2026-09-06)

- No invariant governs output-format *equality*. ADR-0010 guarantees re-entry (`canonicalize(V, C) == V`) but is **contract-relative**: Phone `national` satisfies it only because its contract carries the missing country code as `default_country` (`contract.py:103-110`; suite row crutch at `test_reentry_invariant.py:161`), and Language `alpha2`/`alpha3`/`alpha3-bib`/`name` pass it while silently changing the entity (`en-US` → `en` — the truncated value is itself a valid smaller entity, so nothing flags the change).
- The invariant family is ADR-0004 (Single-Value) → ADR-0010 (Re-entry). ADR-0011 extends it with the value-relative property: what a rendered format may *be*, relative to the canonical value it represents.
- Phase 0 landed `tests/property/test_coordinates_quantization.py`, which pins the dms/dm documented-quantization properties the ADR's Corollary 2 exception relies on.

### The formal statement (verbatim — this exact text goes into the ADR)

> **Information-Preservation (output-format equality).** For every capability, for every `F ∈ OFFERED_OUTPUT_FORMATS`, for every default canonical `V` the capability can produce: `W = format_value(V, F, notation)` must preserve every bit of `V` used by any shipped grammar to recognize `V`'s form or any shipped rule to validate `V` — recoverable from `W` alone under the default (param-free) contract. Corollaries:
>
> 1. **Entity-relative injectivity.** For all canonicals `V1 ≠ V2` denoting **different entities** (§2), `F(V1) ≠ F(V2)`. Same-entity spelling merges are permitted only as documented same-entity expansions (`AAAABBCC`/`AAAABBCCXXX` under `bic11`) and must be fixed-point. String-level injectivity is deliberately *not* required — it would condemn the audit's own PASS verdicts for `bic11`/`eui64` (§7.3).
> 2. **Param-free pre-image re-entry** (stronger than ADR-0010's same-contract `V→V`): `canonicalize(W, default_contract)` succeeds and returns the pre-image `V` — **exact** for encodings and same-entity expansions, **bounded-drift** (within ½ of the declared render quantum, deterministic) for documented quantizations. No offered format may require a contract parameter to make its own output readable.
>
> Classification clause: every offered format belongs to exactly one class — encoding, same-entity expansion, or documented quantization — declared in the capability (contract docstring), with the class's obligations attached. Projections are not offered.

In the ADR, the §-references above resolve to the ADR's own Definitions and Audit sections (the ADR is self-contained; the research report is ephemeral and is **not** cited anywhere in it).

### Design decisions (locked)

1. **Status: Accepted, not Proposed** — mirroring ADR-0010 Scope decision 1: an invariant that defines what *offered* means cannot be adopted tentatively. Adoption of the invariant and taxonomy is hard. Scope decision 1 in the ADR records honestly that enforcement against **pre-existing** surfaces is sequenced: Phone `national` is a directed de-offer (Phase 2, breaking per ADR-0010 Consequences), Language is waived-with-migration-plan until option (b) lands (Phase 3), Coordinates `dms`/`dm` are compliant documented quantizations once Phase 0's declarations + property locks are in (they are a prerequisite of this plan).
2. **The ADR embeds the baseline audit table** (all 18 capabilities, every offered format, PASS/VIOLATION verdict + class + mechanism) copied verbatim from the amended research report §6 — the ADR is the durable home because `docs/development/` may be removed without notice. The ADR must not reference the report by filename or content.
3. **Entity-relative injectivity, explicitly not string-level.** The definitions section defines *entity* (authority-relative: ISO 9362 implicit `XXX`, IEEE EUI-48→EUI-64 derivation vs. BCP 47 subtags changing the tag's identity) and the four format classes verbatim from research §2. This is the one correction without which the ADR contradicts its own audit table.
4. **Soft mandate now, hard gates later** — Consequences records: (a) new offered formats must ship with a class declaration + param-free pre-image/injectivity argument (or declared-quantization obligations: quantum documented + fixpoint/bounded-drift property tests); (b) `Phone national` is directed to de-offer with a migration note (Phase 2 plan); (c) Language remediation option (b) — map the primary subtag, carry remaining subtags — is scheduled (Phase 3 plan); (d) the suite hardening obligations (param-free rows, same-entity expansion fixtures, cross-entity injectivity pairs) land via the Phase 4 plan; (e) hard CI gates (static `format_value` param-branching scan; sampled entity-injectivity gate; de-offer deadlines) are recorded as **promotion criteria** for a future ADR, not obligations of this one.
5. **Inputs are out of scope** — the invariant constrains *outputs*; `default_country`-gated recognition for domestic input remains legitimate. Stated in Scope decisions to block reviewer over-reach (research risk #5).
6. **Engine enforces nothing at runtime** — off-hot-path CI enforcement per ADR-0010 Consequences precedent; `run_capability()` carries no invariant bookkeeping.
7. **Cross-references are additive one-liners** — ADR-0010's References list gains one line; root `AGENTS.md` gains one sentence in the existing re-entry bullet's neighborhood; `CONTEXT.md`'s "### Presentation: format_value and output_format" section gains one sentence. No other doc churn.

---

## File Structure

- Create: `docs/adr/0011-output-format-information-preservation.md`
- Modify: `docs/adr/0010-re-entry-fixed-point-invariant.md` — one References line
- Modify: `AGENTS.md` — one sentence appended to the ANTI-PATTERNS re-entry bullet (root file, line ~"Re-entry (fixed-point): … ADR-0010")
- Modify: `CONTEXT.md` — one sentence in `### Presentation: format_value and output_format` (line ~408-413)

No source/test/config change; no `CHANGELOG.md` entry (no shipped behavior).

---

### Task 1: File the tracking issue

**Files:** none (GitHub issue).

**Goal:** The ADR's References and the follow-up phase plans need a citable number.

- [ ] File an issue titled "Information-preservation (output-format equality) invariant — ADR-0011" describing: the invariant (entity-relative injectivity + param-free/bounded-drift pre-image), the four-class taxonomy, the baseline audit outcome (Phone `national` violation → directed de-offer; Language violation → option (b) remediation; Coordinates `dms`/`dm` documented quantization → compliant), and the phase sequencing (ADR → Phone → Language → suite hardening → promotion ADR). Paste the number into this plan's header, the ADR's References, and the commit messages.

### Task 2: Write ADR-0011

**Files:** `docs/adr/0011-output-format-information-preservation.md` (create)

**Goal:** The binding decision record. Structure mirrors ADR-0010 (Status / Context / Decision / Formal Statement / Scope Decisions / Consequences / Alternatives Considered / References).

- [ ] Front matter: `# ADR-0011: Information-Preservation (Output-Format Equality) Invariant — Offered Formats Are Encodings, Same-Entity Expansions, or Documented Quantizations`; Status block: `**Accepted — <execution date>.** Tracked as issue #<N>. Phase 1 of the output-format invariant sequencing (after Phase 0, the Coordinates quantization obligations).`
- [ ] **Context** section: state the ADR-0010 gap in the report's precise terms — re-entry is contract-relative; Phone `national` passes only via the `default_country` crutch (cite `contract.py:103-110`, `capability.py:142-160`, `test_reentry_invariant.py:155-161`); Language's projection changes the entity silently and passes `V→V` because the truncated value is itself a valid smaller entity (cite `Language/capability.py:153-231`); the harm class is identity confusion, not style.
- [ ] **Decision + Formal Statement**: embed the verbatim statement from this plan's Background (the full quote block including both corollaries and the classification clause).
- [ ] **Definitions** section: *canonical value*, *entity* (authority-relative; the `AAAABBCC` ≡ `AAAABBCCXXX` / EUI-64 vs. `en-US` ≁ `en` contrast), *format classes* (encoding / same-entity expansion / documented quantization / projection — verbatim from research §2), *render quantum*.
- [ ] **Scope Decisions** (numbered, mirroring ADR-0010's style):
  1. Status Accepted; enforcement sequencing for pre-existing surfaces (Decision 1 above).
  2. Entity-relative injectivity — string-level injectivity deliberately not required; same-entity merges allowed only as documented expansions with merge-fixpoint fixtures; rationale: the audit's `bic11`/`eui64` verdicts and a implementable CI gate both require it.
  3. Declared-quantization exception in Corollary 2 — exact pre-image for encodings/expansions, bounded-drift (≤ ½ declared render quantum) for documented quantizations; the quantum must be declared at the contract seam and the fixpoint/bounded-drift properties pinned in CI (cite `tests/property/test_coordinates_quantization.py` as the charter lock); `W→W` never stands in for `W→V'`.
  4. Outputs only — `default_country`-gated input recognition is legitimate and untouched; the invariant constrains what a format may *render*, never what context an *input* may need.
  5. Snapshot-relative + entity authority-relative (like determinism/re-entry; authority-table evolution may change which `V`s exist and which spellings denote one entity, never whether `F` preserves them).
  6. Engine never raises at runtime — CI property tests + review are the enforcement (ADR-0010 Consequences precedent).
- [ ] **Baseline audit (2026-09-06)** section: copy the amended research report §6 verdict table verbatim (all 18 capability rows, mechanism + verdict + class columns, its header line "Verdict per offered format against the invariant (removed ∩ (recognition ∪ validation) = ∅ required; injectivity assessed entity-relative)"), plus the §7.3 non-violator notes (Country name/alpha3/numeric; BIC `bic11`/MacAddress `eui64` entity-relative carve-out; Money `compact`) and the Appendix's latent-collision note. This section is the ledger future formats are judged against.
- [ ] **Consequences** section: the five soft-mandate obligations from Design decision 4 (new-format class declaration + property argument; directed Phone de-offer with migration note — the `ContractError` message must name the shipped successors; Language option (b) scheduled; suite hardening expectations — param-free rows for every offered format, same-entity expansion fixtures asserting merge-and-fixpoint, mandatory cross-entity pairs: Language `en-US`/`en-GB`, Phone GB/MY for any future NSN-style format, Coordinates sub-quantum neighbors; promotion criteria for a future hard-mandate ADR: static `format_value` param-branching scan, sampled entity-injectivity gate, de-offer deadlines for waived violations). Also: de-offering a format is a breaking change requiring a migration note (ADR-0010 precedent, restated).
- [ ] **Alternatives Considered** section, four entries, each with the rejection reason:
  1. *String-level injectivity* — rejected: condemns the audit's own PASS verdicts for `bic11`/`eui64`; the principled line is entity-relative (§ Definitions).
  2. *Runtime assertion in `run_capability()`* — rejected: hot-path cost, duplicates what CI property tests prove per snapshot (ADR-0010 Alternative 1 precedent).
  3. *Main clause only, no injectivity corollary* — rejected: the corollary is what forces per-format class declarations and catches identity collisions that involve no recognition/validation bits; without it the taxonomy has no enforcement hook.
  4. *De-offer `dms`/`dm`* — rejected: their obligations are closed and cheap (quantum-ratio stability proof + bounded drift, pinned by Phase 0's suite); de-offer remains the documented fallback only if the obligations later break.
- [ ] **References** section: issue #\<N\>; ADR-0004 and ADR-0010 (invariant family); the Phase 0 plan is **not** cited — instead cite its landed artifact `tests/property/test_coordinates_quantization.py`; codebase primaries from this plan's References (Phone contract/capability/suite row, Language capability, Coordinates capability/contract, `paxman/core/capability_contract.py`).
- [ ] Self-containment check: `rg -n "docs/development" docs/adr/0011-output-format-information-preservation.md` → 0 hits. Commit: `docs(adr): 0011 information-preservation (output-format equality) invariant (#<N>)`.

### Task 3: Cross-references (one line each)

**Files:** `docs/adr/0010-re-entry-fixed-point-invariant.md`, `AGENTS.md`, `CONTEXT.md`

**Goal:** The invariant family is discoverable from every existing entry point.

- [ ] `docs/adr/0010-re-entry-fixed-point-invariant.md`, References section: append one line — `- ADR-0011 (Information-Preservation / output-format equality) — strengthens this invariant: re-entry stays required; entity-relative injectivity and param-free (or bounded-drift) pre-image recovery are added value-relative corollaries.`
- [ ] Root `AGENTS.md`, ANTI-PATTERNS section, the `**Re-entry (fixed-point):**` bullet: append one sentence — `Output-format information preservation (ADR-0011): every offered format is an encoding, same-entity expansion, or documented quantization — never a projection over recognition/validation information; injectivity is entity-relative and re-entry of a rendered format under the default contract recovers its pre-image exactly (bounded-drift for declared quantizations).`
- [ ] `CONTEXT.md`, `### Presentation: format_value and output_format` (line ~408): after the existing "offered formats must preserve the capability's ambiguity contract" sentence (line ~413), add — `Per ADR-0011, every offered format is an encoding, a same-entity expansion, or a documented quantization (declared in the capability's contract docstring); projections are not offered.`
- [ ] Verify: `uv run pytest tests/property tests/unit -q` → PASS (no behavior change; guards against accidental edits to cited files). Commit: `docs: cross-reference ADR-0011 from the invariant family (#<N>)`.

### Task 4: Full gate

**Files:** none.

- [ ] `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q` → all green (docs-only change; the gate proves it).
- [ ] PR description carries: the issue number, the ADR's five Consequences obligations, and the explicit out-of-scope note (Phases 2–4 are separate plans citing this ADR).

---

## Out of scope (deliberate — sequenced follow-ups that cite this ADR)

- Phase 2: Phone `national` de-offer + successor formats (breaking; own plan; own migration note).
- Phase 3: Language option (b) subtag-preserving remediation.
- Phase 4: `test_reentry_invariant.py` hardening (param-free rows, same-entity fixtures, cross-entity pairs) and the review-checklist codification.
- Hard-mandate promotion ADR + CI gates (§8.3 criteria recorded in Consequences; promoted later).
