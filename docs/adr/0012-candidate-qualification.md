# ADR-0012: Candidate Qualification — PARSER Candidates Require LOOKUP Corroboration

## Status

**Proposed — 2026-09-09.** Tracked as issue #147 (B1 ghost candidates, with the
issue #71 dedup-scoping problem folded in). Joins the invariant family ADR-0004 began
(Single-Value Invariant) and ADR-0010/ADR-0011 continued: a correctness property
of the pipeline as a whole, held by construction and enforced by tests, never by
hot-path heuristics.

## Context

Paxman forbids heuristic pipelines, confidence scoring, and rule ranking: every
candidate must cite an authority (`Rule.provenance`), and the engine never
prefers one authority over another. Issue #147-B1 shows a gap in that posture.
`canonicalize("Serbo-Croatian", Language)` returns `AMBIGUOUS` between a ghost
value `serbo-croatian` — accepted on BCP 47 syntax alone
(`Section 2.1-syntax`, `RuleStrategy.PARSER` in
`paxman/capabilities/Language/rules/bcp47_rfc5646_ed2009.py`) — and the real
value `sh` from the English-name mapping (`Section-english-name-mapping`,
`RuleStrategy.LOOKUP_TABLE` in
`paxman/capabilities/Language/rules/iso_639_1_ed2002.py`, semantics
`language_name`). The ghost cites no registry entry for what it claims; the
syntax rule merely confirms the string is well-formed.

The degenerate case is worse than ambiguity: a lone ghost such as `xx-yyyyy`
yields `SUCCESS` on syntax alone (verified) — no IANA subtag
(`Section-iana-registry`, `RuleStrategy.LOOKUP_TABLE` in
`paxman/capabilities/Language/rules/iana_language_subtag_registry_ed2026.py`,
semantics `bcp47_tag`) backs any part of it, yet the pipeline emits it as a
canonical value. A well-formedness check is standing in for authority validation.

The qualification hook already exists in shape: `_collect_candidates`
(`paxman/engine/orchestrator.py:548`) pairs each `Candidate` with its source
`RecognizedRep`, and `_determine_status` (`paxman/engine/orchestrator.py:752`)
decides `SUCCESS`/`AMBIGUOUS` purely on distinct values. What is missing is the
qualification step between them. Rule strategies (`RuleStrategy`, `paxman/core/domain.py`) already distinguish
`PARSER` (shape) from `LOOKUP_TABLE` (authority membership) — the engine just
does not act on the distinction.

The same region of the engine carries the #71 problem: the `keep_duplicate_spans`
escape hatch is computed globally (`paxman/engine/orchestrator.py:135-142` — any
`CandidatesMatcher` with strategy `"all"` sets `keep_dup` for the whole call),
so one grammar's opt-in disables span dedup for every grammar. Both problems are
decided here because both are engine-level candidate-set policy.

## Decision

**Disqualification, not ranking: a `PARSER` candidate survives only when a
`LOOKUP_TABLE` rule validates the same `RecognizedRep`. No scores, no weights,
no per-rule precedence.**

### Formal Statement

> **Candidate qualification.** After `_collect_candidates` and before
> `_determine_status`: a candidate whose validation rule has strategy `PARSER`
> is *provisional*. It survives if and only if at least one candidate from a
> `LOOKUP_TABLE` rule was produced from the **same `RecognizedRep`** (same
> grammar, same span, same notation object). `LOOKUP_TABLE` candidates are never
> provisional — each cites authority membership directly. `REGEX` is out of
> scope (no shipped Language rule uses it).
>
> **Vacuity.** The filter applies to a recognition only when at least one
> *active* `LOOKUP_TABLE` rule (post contract filtering: `pinned_rules`,
> `excluded_rules`, `year`, `requires_features` gating) targets its semantics.
> Where no authority is in force — all-`PARSER` capabilities (Date, URL,
> Coordinates, IP, ORCID, MacAddress, ISSN, BIC), or contracts that filter the
> lookup authority out (e.g. Language `year=2009`, which drops the 2026 IANA
> rule) — there is nothing that could corroborate, so `PARSER` stands as today.
> This is still disqualification, not ranking: corroboration is demanded only
> where an authority exists to give or withhold it.

Corollaries:

1. **Same-recognition corroboration, not span-level.** The corroborating lookup
   must validate the identical `RecognizedRep`, not merely an overlapping span.
   A name-grammar recognition corroborated by a tag-grammar lookup on the same
   characters would be cross-semantics leakage — one semantics vouching for
   another.
2. **Honest `AMBIGUOUS` survives.** Two `LOOKUP_TABLE`-backed distinct values
   still yield `AMBIGUOUS` via the unchanged `_determine_status`. Qualification
   removes authority-less ghosts; it never breaks ties between authorities.
3. **Per-grammar `keep_duplicate_spans` scoping (#71).** The `keep_dup` flag
   moves from a call-global boolean to per-grammar scope: only candidates whose
   source grammar opted in (strategy `"all"`) keep duplicate spans; every other
   grammar's output still passes through span dedup.

## Consequences

Language pilot (the only behavior change in this ADR):

- `Serbo-Croatian` → `sh` (`SUCCESS`): the `serbo-croatian` ghost (PARSER-only,
  no IANA corroboration on its rep) is disqualified; the `sh` lookup candidate
  stands alone.
- Lone ghosts (`xx-yyyyy` and kin) → `INVALID`: recognized but with no surviving
  candidate, per the existing `_determine_status` branch for empty candidates
  with recognitions present.
- `en-x-private` without `include_private` → `INVALID` (was `SUCCESS` via
  syntax alone): the gated-off authority speaks by its absence, and the
  two-locus model already resolves this class to `INVALID` (`qaa`/`aav`/
  `allemand` without flags). With `include_private=True` the private rule
  corroborates → `SUCCESS` unchanged.
- No other capability changes behavior: qualification is vacuous where no
  *active* `LOOKUP_TABLE` rule targets the recognition's semantics (all-`PARSER`
  capabilities; year/feature-filtered contracts), and the per-grammar dedup
  scoping preserves current results for grammars that never shared a call with
  an `"all"`-strategy grammar.

Enforcement follows the invariant-family precedent (ADR-0010/ADR-0011): CI
property tests plus review, no scores or ranking state in `run_capability()`.

## Alternatives Considered

1. **Per-rule precedence (syntax rule ranks below registry rules).** Rejected: a
   precedence order cites no authority — it is ranking by editorial judgment,
   the exact mechanism the no-heuristics principle forbids. Corroboration needs
   none: strategies are declared metadata, and the rule is uniform.
2. **Span-level corroboration (any lookup on an overlapping span rescues the
   parser candidate).** Rejected: cross-semantics leakage. Overlapping spans
   from different grammars carry different notations with different meanings
   (the engine deliberately keeps cross-grammar ambiguity observable —
   `_recognize`, `paxman/engine/orchestrator.py:250`); letting one semantics
   corroborate another would launder ghosts through adjacent recognitions.
3. **Confidence scoring (parser candidates survive with lower confidence).**
   Rejected: scores are heuristics with no authority behind them, and every
   consumer would need a threshold policy the library cannot ground. A ghost
   with score 0.1 is still a ghost presented as a candidate; disqualification
   states plainly what scoring only whispers.

## References

- Issue #147-B1 — ghost candidates: `Serbo-Croatian` AMBIGUOUS, `xx-yyyyy`
  SUCCESS on syntax alone.
- Issue #71 — folded into the Decision via per-grammar `keep_dup` scoping.
- `paxman/engine/orchestrator.py:548` (`_collect_candidates`), `:752`
  (`_determine_status`), `:135-142` (global `keep_dup`, issue #71).
- `paxman/core/domain.py` — `RuleStrategy` (`PARSER` vs `LOOKUP_TABLE`).
- `paxman/capabilities/Language/rules/bcp47_rfc5646_ed2009.py`
  (`Section 2.1-syntax`, PARSER, `bcp47_tag`).
- `paxman/capabilities/Language/rules/iana_language_subtag_registry_ed2026.py`
  (`Section-iana-registry`, LOOKUP_TABLE, `bcp47_tag`).
- `paxman/capabilities/Language/rules/iso_639_1_ed2002.py`
  (`Section-english-name-mapping`, LOOKUP_TABLE, `language_name`).
- ADR-0004 (Single-Value Invariant) — invariant-family root.
- ADR-0010 (Re-entry) / ADR-0011 (Information-Preservation) — structural
  precedent for this ADR's form and enforcement posture.
