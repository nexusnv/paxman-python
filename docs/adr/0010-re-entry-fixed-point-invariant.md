# ADR-0010: Re-Entry (Fixed-Point) Invariant — Canonical Values Are Fixed Points

## Status

**Accepted — 2026-09-03.** Tracked as issue #123, which also fixes the decision as hard
(see Scope decision 1).

## Context

Paxman's pipeline contract has always been deterministic: the same input, the same
contract, and the same library snapshot yield the same `ExecutionResult` — determinism by
construction, restated as a binding first principle of the recognition kernel (ADR-0009,
§5). Determinism constrains *repeating* a call with the *same* input. It says nothing
about the call a caller is most likely to make next: feeding the pipeline its own output.

Canonical values are data. Callers store them, persist them, export and re-import them,
deduplicate records against them, and re-validate stored values under a newer release.
The natural expectation on every one of those paths is the fixed-point property: if
`canonicalize(I, C)` resolved input `I` to `V`, then `canonicalize(V, C)` must resolve `V`
to itself. A canonical value that fails to re-enter is a value the library produced but
cannot consume — its own output lies outside the domain its grammars recognize or its
rules validate. The status vocabulary makes the failure modes exact
(`_determine_status`, `paxman/engine/orchestrator.py`): `MISSING` (nothing recognized),
`INVALID` (recognized, but no rule accepts it), `AMBIGUOUS` (recognized, competing values).
Any of the three on re-entry means the first call returned a value that the same contract
rejects as input.

The contract surface makes this a live risk rather than a hypothetical one. On `SUCCESS`,
`ExecutionResult.canonicalized_value` is the value rendered through the capability's
`format_value()` seam under the contract's resolved `output_format`
(`_collect_candidates`, `paxman/engine/orchestrator.py`), and every contract declares a
`DEFAULT_OUTPUT_FORMAT` plus an `OFFERED_OUTPUT_FORMATS` set, resolved once in
`CapabilityContract.__post_init__` (`paxman/core/capability_contract.py`). Nothing in the
engine requires that a rendered value still be recognizable by the contract's
`active_grammars`, or still validated by the rules that survive
`pinned_rules`/`excluded_rules`/`year` filtering. A format can therefore be offered whose
rendered values the same contract no longer recognizes — a booby trap installed by the
library itself.

Issue #123 asked for this guarantee to be locked as an ADR; issue #122 surfaced the one
shipped interaction (common-word suppression) that must be recorded alongside it. This ADR
joins the invariant family ADR-0004 began (Single-Value Invariant): a correctness property
of the pipeline as a whole, held by construction and enforced by tests, never by hot-path
runtime checks.

## Decision

**The Re-Entry (Fixed-Point) Invariant:** every canonical value paxman produces under a
contract must re-enter the pipeline under that same contract and resolve to itself.

### Formal Statement

Two properties, over `canonicalize(I, C) -> ExecutionResult`
(`paxman/engine/orchestrator.py`; statuses are the `Resolution` values of
`paxman/core/domain.py`):

1. **Determinism (already mandated; restated for context).** The same input `I`, the same
   contract `C`, and the same library snapshot produce the same `ExecutionResult`. This is
   the project's existing determinism-by-construction guarantee (ADR-0009 §5); this ADR
   adds nothing to it.
2. **Re-entry / fixed-point (new — this ADR).** If `R = canonicalize(I, C)` has
   `R.status == SUCCESS` and `R.canonicalized_value == V`, then `R' = canonicalize(V, C)`
   must have `R'.status == SUCCESS` and `R'.canonicalized_value == V` — irrespective of
   the `output_format` in `C` that produced `V` (default or offered). An `output_format`
   whose rendered value does not re-enter (degrades to `MISSING`/`INVALID`/`AMBIGUOUS`)
   must not be offered.

Property 2 makes every `SUCCESS` value a fixed point of the pipeline under the contract
that produced it. The guarantee is `R'.canonicalized_value == V`, not merely
`R'.status == SUCCESS`: a re-entry that succeeded by resolving `V` to some other canonical
form `W ≠ V` would let deduplication split one entity into two, so the value must
round-trip exactly.

### Scope Decisions

1. **Status is Accepted, not Proposed.** The decision is hard — issue #123: "This is a
   hard decision (not open for debate)". An invariant that defines what *offered* means
   cannot be adopted tentatively: a Proposed status would invite exactly the drift (offer
   the format now, guarantee re-entry later) the invariant exists to prevent.

2. **Scope is contract-relative.** The invariant binds `V` to the *same* contract `C` that
   produced it; it makes no claim that `V` re-enters under a different contract. The
   guarantee is unconditional for the **default contracts** of all shipped capabilities
   (property-tested in CI via `tests/property/test_reentry_invariant.py`, landing
   separately). For non-default contracts it holds conditionally under the
   **recognize-own-output condition**: `C`'s `active_grammars` must include a grammar that
   recognizes every format in `C`'s output chain (its resolved `output_format`), and `C`'s
   rule set (`pinned_rules`/`excluded_rules`/`year`) must not remove the rules that
   validate that form. The engine does *not* enforce the condition at runtime (no hot-path
   cost); the CI property suite plus a one-time offered-format audit are the enforcement.
   Rationale: a guarantee across arbitrary contracts is unachievable in general — a caller
   can always assemble a contract whose `active_grammars` exclude the grammar recognizing
   a given format — so paxman guarantees the defaults outright and reduces the narrowed
   case to a checkable condition instead of a vague hope.

3. **Offered formats are guaranteed, not audited-only.** Every format in a capability's
   `OFFERED_OUTPUT_FORMATS` must re-enter under the same contract; a violation is either
   fixed (recognition or validation extended so the rendered form re-enters) or the format
   is de-offered with rationale. Rationale: offering a format is an API promise; an
   offered format that fails re-entry is a booby trap on the library's own output, and an
   audit-only posture would leave the guarantee dependent on review diligence rather than
   structure.

4. **Snapshot scope.** Like determinism, re-entry is scoped to a library snapshot —
   `VersionStamp.paxman_version` + `recognition_revision`, stamped on every
   `ExecutionResult` (`paxman/engine/orchestrator.py:136-138`). A data-table update (a
   regenerated authority snapshot) may change *which* `V` a given `I` produces, but must
   never make a produced `V` un-re-enterable within the same snapshot. Rationale:
   authority data evolves (ISO tables, currency snapshots); the invariant is
   self-consistency of one snapshot, not immutability of data across snapshots — the
   cross-snapshot story remains the existing versioning signal
   (`recognition_revision`, ADR-0009 §13).

5. **Suppression interaction.** With `suppress_common_words=False` (the contract default)
   re-entry is unconditional. With `suppress_common_words=True`, the violator set today —
   canonical values that re-enter as `MISSING` because the suppression hit swallows the
   entire input, which *is* the canonical word — is *defined by* the intersection of
   (word-bounded suppressible-matcher hit) ∩ (common English word) ∩ (no non-suppressible
   rescue path). As of the shipped `COMMON_WORDS` table its membership is large, not a
   handful: 26 of the 250 ISO 3166-1 α2 codes (`TO`, `DE`, `CD`, `IT`, …) for Country,
   50 ISO 639 codes (`en`, `de`, `no`, …) for Language, and 3 of the 178 ISO 4217 codes
   (`ALL`, `TRY`, `TOP`) for Currency re-enter as `MISSING`. At the input level, 53
   common-word inputs collapse onto these 50 Language codes (`in` and `id` both
   canonicalize to `id`), and two inputs — `may` → `ms`, `per` → `fa` — canonicalize to
   non-common-word codes and are rescued (re-entry `SUCCESS`). Two notable survivors show
   the mechanism matters: Country `US` re-enters via the country *name* grammar
   (`name_recognition`), which carries no `suppressible` mark — suppression is
   per-matcher (`matcher.suppressible`), not per-capability, so a non-suppressible
   path rescues the value. SIUnit `cd` re-enters because no SIUnit matcher is marked
   `suppressible`; the capability is entirely outside suppression's reach today. A
   capability can opt out of suppression (by leaving its matchers unmarked) or gain
   rescue paths, moving values across this intersection — which is exactly why issue
   #122's adopted decision A0 (whole-input exemption in the recognition engine loop — a
   word-bounded suppression hit may never suppress the entire trimmed input) must hold
   for the whole class, not a curated list. This ADR records the interaction and
   cross-references #122; it does not implement it. Rationale: the invariant must state
   honestly where it is conditionally violated today, and the fix belongs to the
   suppression decision that introduced the flag — not to a second enforcement mechanism
   invented here.

## Consequences

- **The engine never raises on a re-entry violation.** Unlike ADR-0004's
  `MultipleMentionsError` (a fail-fast usage signal at pipeline time), re-entry is
  enforced entirely off the hot path — the CI property suite plus the one-time
  offered-format audit. A violation is a capability data or grammar defect to fix in the
  capability, never a runtime exception for callers to catch, and `run_capability()`
  carries no invariant bookkeeping.
- **New capabilities must add a re-entry row to `tests/property/test_reentry_invariant.py`
  before landing.** The suite is organized as per-capability rows (default contract plus
  offered formats); a capability without its row cannot land. This makes the "no new
  capabilities until the invariant lands" gate structural rather than procedural.
- **De-offering a format is a breaking change requiring a migration note.** Once a format
  is offered, callers may render values in it; removing it from `OFFERED_OUTPUT_FORMATS`
  changes the contract surface — callers still passing the format begin to receive
  `ContractError` (`CapabilityContract.__post_init__`) — and must ship with a migration
  note.

## Rejected Alternatives

1. **Runtime assertion in `run_capability()`.** The engine would re-canonicalize the
   rendered value of every successful call and fail on violation. Rejected — it doubles
   recognition and validation work on the hot path for every `SUCCESS`, and duplicates
   what CI property tests prove per snapshot. The invariant is a property of the
   capability's data and grammar set, not of an individual call; re-proving it per call
   buys nothing.
2. **Invariant scoped to default formats only.** The guarantee would cover
   `DEFAULT_OUTPUT_FORMAT` and leave offered formats at best effort. Rejected — it
   silently permits un-re-recognizable offered formats, which is exactly the failure the
   origin issue (#123) rules out: an offered format is part of the promise, and a
   guarantee narrower than the offered surface is weaker than the API implies.
3. **A1 suppression fallback** ("if suppression would leave 0 mentions, keep the
   unsuppressed set"). Evaluated and rejected in issue #122: as a general mechanism it is
   hypothetical for the shipped capability set — the whole-input-suppressed class is
   *defined by* the suppressible ∩ common-word ∩ no-rescue-path intersection of Scope
   decision 5 (current membership: the counts given there), which A0 exempts
   mechanically — and a fallback that resurrects suppressed mentions re-admits the
   short-code-in-prose false positives the flag exists to prevent. The adopted decision
   A0 (whole-input exemption) is the narrower fix.

## References

- Issue #123 — origin of this ADR: the re-entry invariant requirement and the
  hard-decision scoping (Scope decision 1).
- Issue #122 — common-word suppression decision record: A0 (whole-input exemption)
  adopted, A1 fallback rejected (Scope decision 5; Rejected Alternative 3).
- ADR-0004 (Single-Value Invariant) — invariant-family precedent: an engine-level
  correctness property enforced by tests rather than hot-path checks.
- ADR-0009 (Recognition Kernel) — determinism first principles (§5), snapshot identity via
  `VersionStamp.recognition_revision` (§13), and the suppression machinery
  (`COMMON_WORDS` + `suppress_common_words`) whose interaction is recorded here.
- `paxman/engine/orchestrator.py` — `run_capability()`, `ExecutionResult`,
  `_determine_status()`, `_collect_candidates()` (the `format_value()` call site), and the
  `VersionStamp` construction (lines 136-138).
- `paxman/core/capability_contract.py` — `DEFAULT_OUTPUT_FORMAT`, `OFFERED_OUTPUT_FORMATS`,
  `output_format` resolution, `active_grammars`, `pinned_rules`/`excluded_rules`/`year`,
  `suppress_common_words`.
- `paxman/core/domain.py` — `Resolution` (`SUCCESS`/`MISSING`/`INVALID`/`AMBIGUOUS`).
- `paxman/core/capability.py` — the `format_value()` presentation seam.
- `tests/property/test_reentry_invariant.py` — the CI property suite (landing separately)
  and the per-capability re-entry gate.
