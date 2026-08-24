# ADR-0009: Staged Pipeline Extensions — Normalized View, Automaton, Scanner, and Composable Candidates for v0.2.0

## Status

Proposed — Draft 2026-08-24

## Changelog

| Version | Date | Author | Summary of change |
|---------|------|--------|-------------------|
| Draft | 2026-08-24 | Sisyphus | Initial draft — extends ADR-0008's fixed-order pipeline (`pre→regex→lexicon→composer→post`) with six new stage types (P1a NormalizedView, P1b Automaton/Trie, P2 Scanner, P2 UnicodeProperty, P3 FormatCandidate, P3 GenericComposer, P4 LabelStage) to unblock Language (BCP 47 / ISO 639) and adjacent milestones. Staggered delivery within a single `v0.2.0` release train. Rejected ML/NER, fuzzy, checksum-fused recognition documented. |

## Context

ADR-0008 (accepted 2026-08-20) migrated Paxman's recognition layer from 29 bespoke `Grammar.recognize()` loops to a declarative **fixed-order pipeline with optional stages**:

```
pre → regex → lexicon → composer → post
```

`PipelineGrammar` walks `PipelineState(text, matches, scratch)`; `BoundaryGuard` unified 8 distinct lookarounds, `LexiconAlternation` de-duplicated `re.escape` joins, and `AmountComposer` absorbed `SYMBOL ? AMOUNT | AMOUNT ? SYMBOL`. Migration is gated by byte-identical `RecognitionMatch` parity (`tests/property/test_grammar_stage_parity.py` — hard), `benchmarks/harness.py` informational (50 iter, non-blocking).

`docs/development/research/2026-08-24-recognition-strategy-study.md` (4-way audit at `main` ≈ `0.1.0`, 33 grammars / 14 capabilities) found:

* Five realised strategy-instances S1–S5 ship cleanly but already strain at edges (820 SIUnit symbol tokens, `PostStage` paren-balance and e164 15-digit window as hand-rolled scans).
* `HOW_TO_ADD_NEW_CAPABILITY.md:282` lists six extended strategies — `scanner`, `format-candidate`, `parser combinators (pyparsing)`, `parser generator (Lark)`, `Unicode-property`, `automaton (Aho–Corasick)` — cited to ecosystem precedent (`ipaddress`, `CleverCSV`, `pyahocorasick`) but with **no `Stage` to reach for**. Contributors are told to "consult this table before forcing it into a regex that fights it" with nothing concrete to adopt.
* Two gaps the table misses: **normalized-view threading** (ADR-0008's `scratch` is never written; `StandardPre` is `empty_guard`-only) and **generic prefix-constrained composition** (`AmountComposer` is not generic; Language `sl-nedis` needs `Prefix.contains("sl")` gating).

The next milestone in `docs/development/MILESTONE.md` (`Language` #2 — BCP 47: `language ["-" script] ["-" region]* …`) makes this blocking: its ABNF is not maintainable as a regex and its lexicon (7000+ ISO 639-3 + 8000+ IANA `Type:language`) degenerates `re.escape` alternation — the `HOW_TO` footnote's stated automaton trigger.

This ADR extends ADR-0008 **within the same pipeline and invariants** (determinism, provenance-first, zero runtime deps, `grammar/data` key-only, `rules/data` authority, capability-agnostic `paxman.core.grammar` leaf, byte-identical parity gate) to land the missing stages. It does not change the engine contract (`Grammar` ABC surface, `RecognitionMatch`, `Rule`, `Provenance`, `Resolution`, `get_grammars()` wiring, community extension `extra_grammars` path).

## Decision

Adopt **six new stage types** plus one cross-cutting threading change — all as new `paxman/core/grammar/*` modules — and deliver them **staggered within a single `v0.2.0` release train**. Stage order stays fixed per ADR-0008; new types slot into the existing positions — no grammar reorders stages, only declares which to include.

### 1. Staggered delivery for `v0.2.0`

All six tiers are **approved for `v0.2.0`** but land as sequenced waves on `main` to preserve reviewability and parity coverage. Each wave is an independent PR (or PR pair) with its own proof harness shard; `v0.2.0` is cut when the last wave merges.

| Wave | Tier(s) | Stage(s) | Pilot capability | What it unlocks in `v0.2.0` |
|------|---------|----------|----------------|------------------------------|
| **W1** | P1a + P1b | `NormalizedViewStage` + `source` threading; `AutomatonStage(Trie)` stdlib, threshold 200 | Language `_ → -` + `en` lower, Country `normalize_name` dedup, SIUnit 820 symbols, Phone `strip_separators` | Language becomes buildable; SIUnit largest regex → single Trie pass |
| **W2** | P2 Scanner | `ScannerStage(scan_one: (str,int)→…)` | URL paren-balance, Phone e164 15-digit window, ISIN/CUSIP 12-/9-char | Replaces the two `PostStage` loops that are already scanners |
| **W3** | P2 UnicodeProperty | `UnicodePropertyStage` + `tools/regenerate_unicode_property_data.py` | SI `µΩÅ` audit, Language Han `Script=Han` | Second property locus — build on W1 generators |
| **W4** | P3 FormatCandidate + GenericComposer | `FormatCandidateStage` , `GenericComposerStage(predicate)`  | Date 4→1 grammar collapse; IBAN 90-country BBAN registry `dict[CC,Pattern]`; Language `sl-nedis` `Prefix` gating; SIUnit compound `UNIT(SEP UNIT){1,3}` | Enumerated formats + prefix-constrained composition (depends on W1a/b) |
| **W5** | P4 LabelStage | `LabelStage(label, separator, fuse)` | ISBN `ISBN[-13]` / ISSN `ISSN[-L]` / BIC `BIC|SWIFT` unify `[\s:-]+` vs `*` | Deduplicates glued-label `[\s:-]+` never-zero-width logic (tolerable inconsistency today) |

W1 is the `v0.2.0` headline (Language's critical path); W2–W5 are tracked as sub-issues of `#47` and may reorder within the train without a re-ADR if parity holds.

### 2. P1a — NormalizedViewStage (cross-cutting Pre)

*New `paxman/core/grammar/normalized_view.py` (or generalized `StandardPre`).*

```python
@dataclass(frozen=True, slots=True)
class NormalizedViewStage(Generic[NotationT]):
    normalizer: Callable[[str], str]  # pure; capability supplies it
    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        state.scratch["__normalized"] = self.normalizer(state.text)
        return state
```

Downstream `RegexStage` / `LexiconStage` / `WholeInputLookup` gain `source: "text" | "__normalized" = "text"` (default preserves parity). `PipelineState.text` stays immutable — emitted `RecognitionMatch.start/end/raw_text` always refer to the **original** input. Length-preserving normalizers (`lower`, `_→-`, accent strip via table, `strip_separators` table) use an identity offset map (zero cost); NFKC-expanding translation (`ﬁ→fi`) is deferred behind `require_length_preserving=True` (offset `list[int]` map added when a capability proves it needs it).

*Why this stage:* ADR-0008's `PipelineState.scratch` is dead code; `Language` underscore tolerance (`en_US` → `en-US`), `Country.normalize_name` (NFKD→lower→punct strip), and `Phone.strip_separators` / `BIC isascii` / SI `²→2` are all length-preserving syntax normalizations duplicated across grammars.

### 3. P1b — AutomatonStage (Trie / Aho–Corasick, stdlib-only)

*New `paxman/core/grammar/automaton.py`.*

```python
@dataclass(frozen=True, slots=True)
class AutomatonStage(Generic[NotationT]):
    tokens: frozenset[str] | ...
    boundary: BoundaryGuard
    longest_first: bool = True        # Trie deepest leaf wins; tie → lex order mirrors LexiconAlternation
    notation_fn: Callable[[str], NotationT] | None
    flags: int = 0
    _trie: Trie = field(init=False)        # built in __post_init__, pure
    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]: ...
```

Pure-Python Trie, deterministic traversal, parity-gated byte-identical vs `LexiconStage` for the same token set. Threshold-gated: `AutomatonStage` only for `len(tokens) ≥ 200` (SIUnit 820/650, Country 600 union, Language 7000+ IANA); `LexiconStage` remains cheaper for Currency 67/80.

*Why now:* `LexiconAlternation(-len, -is_qualified)` degenerates at SIUnit/Country scale and at Language 7000+ IANA scale; `HOW_TO`'s footnote prescribes `pyahocorasick` for this locus — Paxman keeps zero runtime deps by vendoring a stdlib Trie (same precedent as `regenerate_si_prefix_data.py`).

### 4. P2 — ScannerStage (char-state)

*New `paxman/core/grammar/scanner.py`.*

```python
@dataclass(frozen=True, slots=True)
class ScannerStage(Generic[NotationT]):
    scan_one: Callable[[str, int], tuple[int,int,NotationT] | None]
    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]: ...
# walks while i<n: hit=scan_one(text,i) → emit → i=end else i+=1 (non-overlapping, phonenumbers precedent)
```

Grammar-file closures capture capability constants (depth, `e164` 15-digit window, ISIN 12-char check). Replaces URL paren-balance and Phone e164 `PostStage` loops that are already scans; enables DOI/URN `doi:10.1234/...`, Timezone `tzdata` URIs.

### 5. P2 — UnicodePropertyStage (build-time generator + range alias)

*New generator `tools/regenerate_unicode_property_data.py` → `grammar/data/unicode_ranges.py` (frozen `frozenset`/`range` table).* `UnicodePropertyStage` is a thin type alias over `LexiconStage`/`RegexStage` with a `[\uXXXX-\uYYYY…]` generated class. No `regex` (third-party) dep at runtime. Build-time source only; vendored ranges at runtime — same pattern as `regenerate_si_prefix_data.py`, `regenerate_idna_uts46_data.py`.

### 6. P3 — FormatCandidateStage (enumerated strict formats) + GenericComposerStage (predicate-gated)

```python
@dataclass(frozen=True, slots=True)
class FormatCandidateStage(Generic[NotationT]):
    candidates: tuple[RegexStage[NotationT], ...]
    strategy: Literal["first","all"] = "all"   # "all" keeps Date US vs European ambiguity observable

@dataclass(frozen=True, slots=True)
class GenericComposerStage(Generic[NotationT]):
    lex_left: LexiconStage|RegexStage|None
    lex_right: LexiconStage|RegexStage|None
    separator: re.Pattern[str]|None
    order: Literal["either","prefix","suffix"]
    predicate: Callable[[str,str], bool]|None   # e.g. variant Prefix: (tag,variant) -> prefix_ok
    notation_fn: Callable | None
    boundary: BoundaryGuard
```

* `FormatCandidateStage` collapses `Date` 4 grammars → 1 (`iso8601/slash_iso/european/us` per-candidate spans; byte-identical gate). `ISBN` `isbn10/13` stay split (semantics + `include_isbn10` gating differ).
* `GenericComposerStage` generalizes `AmountComposer` (which remains as a documented alias over it: `AmountComposer(pattern=AMOUNT_PATTERN, separator=one_space)`). Needed for Language `sl-nedis` variant (`variant` token gated by IANA `Prefix: sl, sl-rozaj`) and SIUnit `compound` `UNIT(SEP UNIT){1,3}`.

### 7. P4 — LabelStage (unified label handling)

*New `paxman/core/grammar/label.py`.*

```python
LabelStage(label: alt, separator: Pattern, fuse: bool)
```

Unifies `IBAN/BIC/ORCID` `[\s:-]+` never-zero-width (glued `IBANDE89…` → `MISSING`) vs `ISSN` `[\s:-]*` (glued `ISSN03178471` matches) — intentional Oracle-fix behavior. Low priority; deferred to W5.

### 8. What is not changing / not adding

* `Grammar` ABC surface (`name`, `semantics: ClassVar[str]` non-empty, `single_value`, `recognize` signature), `RecognitionMatch` / `Notation` / `Rule` / `Provenance` / `Resolution` / `ExecutionResult`, engine `_recognize` / `_collect_candidates` / `_enforce_single_value_invariant` / `_filter_rules` / `_validate_affinity`, `grammar/data` key-only vs `rules/data` authority boundary, determinism / frozen-library guarantees, `get_grammars()` wiring, community extension `extra_grammars` path — all untouched (inherits ADR-0008 §5).
* Rejected and documented here so not reopened (study §3.7): **`ML/NLP NER`**, **`Fuzzy/Levenshtein/Soundex`**, **`Checksum-fused recognition`** (keep `MISSING` vs `INVALID` split; rules own `mod97`/`MOD-11-2`).
* `getattr(extra_grammars)` probes remain removed per ADR-0007; `active_grammars: None` default remains; `single_value` stays a `Grammar` class attribute (FormatCandidate candidates inherit the parent grammar's value; Scanner emitting multiple spans per `recognize()` sets `single_value=False` deliberately — study §4.4).

### 9. Migration — incremental, parity-gated, per ADR-0008 §4

1. Land `paxman/core/grammar/{normalized_view,automaton,scanner,unicode_ranges,candidate,composer,label}.py` with unit tests.
2. Add `tests/property/test_grammar_stage_parity_{automaton,scanner,candidate,composer}.py` shards — **byte-identical `list[RecognitionMatch](start,end,raw_text,notation)`** (hard gate). Extend shards per wave.
3. Migrate per wave per table in §1 — Language first (W1 value proven), then SIUnit/Country (W1 payoff), then URL+Phone (W2), then Date/IBAN registry/Language Prefix (W4), then labels (W5). Each PR: `ruff + ruff format --check + pyright + import-linter + pytest` per `.github/workflows/ci.yml` (authoritative gate).
4. No silent divergence: if byte-identical is unreachable without semantic change, the PR is aborted and the grammar stays bespoke until the stage contract is extended.

`benchmarks/harness.py` (50 iter CI, informational per `benchmarks/README.md`) is **not** a gate. It is used to choose the `LexiconAlternation` vs `AutomatonStage` 200-token threshold and to track `SIUnit` scan latency; a hard p50 regression gate would be a separate ADR/CI change.

## Consequences

### Positive
* Duct-tape removed across all 33 grammars (`StandardPre`, `strip_separators`, `isascii`, `IGNORECASE` scattered) into one typed `NormalizedView`.
* Declarative grammars: Language's next grammar is ~15 lines + a Trie, not a mega-regex; review focuses on *what* is recognized.
* Staged composition: Language ABNF fields become scannable; SIUnit 820-token alternation becomes O(n) single pass; Date 4 files become 1 declaration.
* Tests stratify: stage unit tests (Trie scan, offset map, Scanner depth) + parity differential tests replace re-covering the same regex corpus.

### Negative
* Abstraction cost: 6 new stage modules touch installable surface; each migration PR must prove parity (mitigated: W1–W5 are independent, each bypassable).
* `get_grammars()` no longer implies "is a regex": contributors read `paxman/core/grammar/stages.py` plus `HOW_TO`. Mitigated: `HOW_TO_ADD_NEW_CAPABILITY.md` remains the entry point and references each stage.
* Wrong-stage risk: a capability could pick Scanner where Regex suffices. Mitigated: `HOW_TO` guidance + parity gate + `HOW_TO:282` precedent table remains the chooser.

### Risks
* **Over-generalization / threshold choice** — 200-token Trie crossover may drift; benchmark informs but does not gate until an ADR says so.
* **Stage order as hard limit** — fixed order `pre→regex→lexicon→composer→post` (with Scanner/Automaton as stage *types* inside it) holds for all 33 shipped grammars and W1–W5 pilots; if a future grammar needs `lexicon before regex` prefilter semantics, extend fixed order *before* adding an escape hatch to bespoke `recognize()` (ADR-0008 §Open Questions #1).
* **Performance indirection** — stages compile once at import time (same as today); `scratch` dict allocation is per `recognize()` and trivial.

## Alternatives Considered

Per study §6 and ADR-0008 §Alternatives (recapped for this extension):

1. **Keep bespoke `recognize()` (status quo 33 grammars).** Rejected — duplication already measured (5× alternation, 8→11 BoundaryGuard variants, 2× post-trim) and Language cannot be expressed without unbounded regex alternation.
2. **Single shared `recognize()` parameterized by capability config.** Rejected — collapses 14 notations into one function with capability branches; loses per-grammar `name/semantics` audit identity.
3. **Add `pyahocorasick` / third-party `regex` at runtime.** Rejected — Paxman keeps zero runtime deps; stdlib Trie / generated range cover the locus.
4. **Hold all six tiers for a later major.** Rejected — P1a+b are Language's critical path for `v0.2.0` milestone `#2` per `MILESTONE.md`; staggering within one train defers only the cleanups (FormatCandidate, LabelStage) that can wait.
5. **Seven separate ADRs (one per tier).** Rejected — tiers are sequenced extensions of one decision (ADR-0008 §Open Questions #1). Single ADR with sub-issues `#47` tracks delivery.

## References

* ADR-0008: Staged Recognition Pipeline (2026-08-20, Accepted) — pipeline shape, `PipelineState(scratch)`, `BoundaryGuard`, `AmountComposer` layering, parity harness
* Study: `docs/development/research/2026-08-24-recognition-strategy-study.md` (4-way audit — grammar inventory, future-need gaps, staged-pipeline deep-dive, external-strategy survey)
* Previous canonicalization research (10): ISBN, Money, URL, SI-unit, ISSN, IBAN, BIC, Language, ORCID, ISIN (`docs/development/research/`)
* `HOW_TO_ADD_NEW_CAPABILITY.md:250–294` — sanctioned Regex/Lexicon pair + extended-strategies table + `grammar/data` vs `rules/data` purity gate
* `HOW_TO_ADD_NEW_GRAMMAR.md`, `ARCHITECTURE.md` (determinism, provenance-first, `MISSING`/`INVALID`/`AMBIGUOUS` split, Recognition Pipeline Contract)
* `paxman/core/grammar/{pipeline,stages,boundary,lexicon,composer}.py` (531L at `main`); `paxman/core/domain.py` (`Grammar/Rule` `__init_subclass__` metadata); `paxman/engine/orchestrator.py` (`_dedup_spans`, `_filter_rules`, `_validate_affinity`)
* `capability_homogeneity_audit.md` — Tier-2 #2/#3 dedup/ordering divergences now resolved via ADR-0008 engine changes
* `benchmarks/harness.py` + `benchmarks/README.md` (informational 50 iter) + `tests/property/test_grammar_stage_parity.py` (hard parity gate)
* Issues: `#47` (master), `#48` P1a NormalizedView, `#49` P1b Automaton, `#50` P2 Scanner, `#51` P2 UnicodeProperty, `#52` P3 FormatCandidate, `#53` P3 GenericComposer, `#54` P4 LabelStage — all labeled `v0.2.0` + `enhancement`

