# ADR-0008: Staged Recognition Pipeline — From Bespoke Grammars to Declarative Stages

## Status

Accepted — Approved 2026-08-20

## Changelog

| Version | Date | Author | Summary of change |
|---------|------|--------|-------------------|
| Draft | 2026-08-20 | initial author | Initial draft — proposed staged pipeline over bespoke `recognize()` methods (30 grammars, 5 strategies, 4 boundary variants, benchmark-gated migration). |
| Rev.1 | 2026-08-20 | Sisyphus (Oracle review `ses_fe24b48daffeCucuRVJMF2OWlL`) | **Corrects factual blockers and closes architectural gaps before acceptance.** Grammar count 30 → **29** verified (`Grammar[NotationT]` subclasses); strategy counts reframed as **strategy-instances** (30 instances across 29 grammars) with corrected recount S1≈17/S2=1/S3=4/S4=4/S5=4 (was 19/1/5/4/5=34); boundary variants 4 → **8 distinct** lookarounds unified behind a **parameterized `BoundaryGuard` family** (was "single guard"); remove `IsbnDigitStrip` from hand-rolled post-trim list (ISBN digit extraction is regex-native); benchmark harness is **informational, non-blocking** per `benchmarks/README.md` — not a gate — and remove erroneous ADR-0007 cross-ref; `amount.py` layering clarified — `AMOUNT_PATTERN`/`classify_amount_shape` **stay in `Money`** and composer accepts a caller-supplied pattern (core stays capability-agnostic per `paxman/core/AGENTS.md`); sketch **Stage Protocol** + `PipelineState`; clarify `WholeInputLookup` emits **original `trimmed`** value; add `single_value` to examples; add **Migration Proof Harness** (differential `RecognitionMatch` equality gate) and **Open Questions**; polish references. |
| Accepted | 2026-08-20 | Sisyphus | Status → **Accepted** (approved for implementation). No normative changes; Rev.1 body is the implementation baseline. |

> **How to read Rev.1:** All normative fixes are already folded into the body below. This table is the audit trail; reviewers need not diff Draft vs Rev.1 separately. The body is the current proposal.

## Context

Paxman ships 10 capabilities and **29 grammars** (verified 2026-08-20 by enumerating `Grammar[NotationT]` subclasses and `name =` declarations under `paxman/capabilities/*/grammar/**`; `README.md` lists 31 by including two planned-but-unimplemented `SIUnit/split_word_prefix` and `SIUnit/split_symbol_prefix` grammars that have no `recognize` in code). Every grammar conforms to the same interface (`Grammar[NotationT].recognize(text) -> list[RecognitionMatch]`, `name`, `semantics`, `single_value`), but the *internals* have diverged into bespoke scripts.

The 2026-08-20 recognition-strategy survey (29 grammars, 56 files under `paxman/capabilities/*/grammar/**`) finds 5 realized strategies behind a single `re` surface. Counts below are **strategy-instances** — a grammar may use several stages (e.g., `SIUnit/symbol_recognition` is lexicon + post-trim, `Money/symbol_recognition` is lexicon + composition + post). The 30 instances span 29 grammars:

| Strategy | Mechanism | Instances | Example |
|----------|-----------|-----------|---------|
| **S1** Pure Regex — shape matching | Fixed `re.compile(...).finditer` | 17 | Date `iso8601_recognition`, Email `standard_recognition`, IP, Phone |
| **S2** Lexical membership | `normalize(text) in frozenset` whole-input lookup | 1 | Country `name_recognition` |
| **S3** Lexicon-driven regex | `"\|".join(re.escape(t) for t in TOKENS)` alternation | 4 | Currency `symbol`/`word`, SIUnit `symbol`/`name` |
| **S4** Compositional | `LEXICON ? AMOUNT \| AMOUNT ? LEXICON` / `UNIT(SEP UNIT){1,3}` | 4 | Money `code`/`symbol`/`word`, SIUnit `compound` |
| **S5** Post-trim / refine | Python post-pass after regex overshoot | 4 | Phone `e164_trim(15)`, URL paren-balance, SIUnit split-prefix classifier, Money `classify_amount_shape` |

`paxman/capabilities/AGENTS.md` sanctions only two strategies — *"Regex (shape) and Lexicon (key-only tables in `grammar/data/`)"* — while `HOW_TO_ADD_NEW_CAPABILITY.md` lists an extended set (`scanner`, `format-candidate`, `parser combinators`, `Unicode-property`, `automaton`) none of which is realized. The survey shows the gap is filled by copy-pasted concerns:

- **Boundary guards** — 8 distinct lookarounds reimplemented per file (not 4): `(?<![\w\-+\u2212])`, `(?<![\w\-+\u2212/·⋅])`, `(?<![\s:-])`, `(?<![\w:.])`, `(?<![\w:.+])`, `(?<![\d+])`, `(?<![\w])`, `(?<![A-Za-z0-9+.\-])` — semantically different (word+sign, word+sign+degree+middot, whitespace:colon:dash, word+colon, word+digit, word-only, scheme-char). Current prose counted only 4.
- **Alternation building** — `"\|".join(re.escape(t) for t in TOKENS)` rebuilt in 5 files; `SYMBOL_TOKENS` duplicated between `Currency` and `Money`.
- **Post-trims** — `E164Trim`, `UrlParenBalance` each hand-rolled. ISBN digit extraction is **not** a hand-rolled post-trim — `ISBN/grammar/isbn13_recognition.py:10-11,26` extracts digits regex-natively via `(?=((?:\d[ -]?){12}\d)(?![\d]))\1` + `m.group(1)`.
- **Split-prefix handling** — `SIUnit` symbol/name both embed `(PREFIX)\s+(UNIT)` and classify `split_*` in `recognize()`.

Each grammar today inlines pre-processing + extraction + lexicon + composition + post-processing in one `finditer` loop. Adding a new strategy (scanner, automaton) means forking the pattern again. The intent of `ADR-0001` (clean pipeline) and `ADR-0003` (semantic affinity) is preserved at the capability/engine seam, but *inside* the recognition layer the seam is informal.

We need to decide whether recognition should remain 29 bespoke `recognize()` methods or become a **staged pipeline** where each grammar *declares* which stages it needs and the pipeline *executes* them.

## Decision

Adopt a **Staged Recognition Pipeline** inside the recognition layer. The pipeline does not change the engine contract, the `Grammar` ABC surface, or the `RecognitionMatch` / `Notation` types. It structures *how* `recognize()` is implemented. The design is a **fixed-order pipeline with optional stages** (not classic Template Method — stages are included by declaration, not always invoked).

### 1. Pipeline shape

```
Input text
  │
  ├─► 1. Pre-processing          — all grammars
  │     empty/whitespace early-exit, Unicode normalize, case policy (exact vs fold)
  │
  ├─► 2. Regex Parser            — S1 grammars (if self.regex is not None)
  │     pure shape scan: regex.finditer(text) → raw spans
  │
  ├─► 3. Lexicon Parser          — S3 grammars (if self.lexicon is not None)
  │     alternation from grammar/data tokens (longest-first, qualified-first D4)
  │     boundary guard injected here via parameterized BoundaryGuard family
  │
  ├─► 4. Composition / Structural Parser — S4 grammars (if self.composer is not None)
  │     fuses prior outputs: AMOUNT_PATTERN either-order, UNIT(SEP UNIT) compound
  │     capability-specific constants (e.g. AMOUNT_PATTERN) are supplied by the
  │     grammar as a parameter — core does not embed them (see §2)
  │
  ├─► 5. Post-processing         — S5 grammars (if self.post_processor is not None)
  │     E164Trim(15), UrlParenBalance, SiSplitPrefixClassifier, AmountShapeClassifier
  │     span fixup (start+len(raw) vs match.end()), shape assignment
  │
  └─► list[RecognitionMatch[NotationT]]
```

Every stage is `Optional[Stage]`. A grammar declares the stages it needs; stages it does not declare are skipped. This keeps `Country:name_recognition` (S2, whole-input `frozenset` lookup) from being forced through a regex it does not need.

### 2. Where the code lives

```
paxman/core/grammar/               # new — recognition-layer internals, no capability imports
  stages.py                        # Stage Protocol + 5 concrete stage types
  boundary.py                      # BoundaryGuard family — parameterized (replaces 8 distinct lookarounds)
  lexicon.py                       # LexiconAlternation builder (longest-first, qualified-first)
  pipeline.py                      # PipelineGrammar base — fixed-order pipeline with optional stages
  # NOTE: no amount.py in core — AMOUNT_PATTERN and classify_amount_shape stay in Money
  # (see layering note below). Core may define a generic AmountToken abstraction
  # that Money specializes, but must not embed Money-specific regexes.

paxman/capabilities/*/grammar/     # grammars shrink to declarations
  *_recognition.py                 # ~15 lines: tokens/regex/composer/post references
  data/                            # unchanged — key-only tables
```

`PipelineGrammar[NotationT]` extends `Grammar[NotationT]` and implements `recognize()` by walking the declared stages in fixed order. Existing grammars migrate by replacing their `recognize()` body with stage declarations. The engine (`paxman/engine/orchestrator.py`) is unchanged — it still calls `grammar.recognize(text)`.

**Layering note (addresses Oracle A1):** `paxman/core/AGENTS.md` mandates core is capability-agnostic ("owns domain vocabulary + `Rule`/`Grammar` ABCs, never imports from capabilities"). `AMOUNT_PATTERN` and `classify_amount_shape` are Money-specific and **remain in `Money/grammar/__init__.py`**; the composer accepts them as constructor arguments (`AmountComposer(pattern=AMOUNT_PATTERN, classify=classify_amount_shape)`). This keeps `paxman/core/grammar` capability-agnostic and import-linter clean. An `amount.py` in core, if ever added, would contain only a generic `AmountToken` abstraction — not Money's regex.

Import-linter layers:

```
paxman.core.grammar → (no imports from paxman.capabilities)
paxman.capabilities.*.grammar → (can import from paxman.core.grammar + paxman.core.domain)
```

This preserves `paxman.core` → no capability imports and keeps `grammar/data/` as the only lexicon source. Adding `paxman/core/grammar` as a subpackage of `paxman.core` inherits core's leaf status — no new import-linter layer entry is expected (to be confirmed when landed).

### 2.1 Stage Protocol

`stages.py` defines the inter-stage contract explicitly (addresses Oracle A3):

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PipelineState:
    """Mutable-through-replacement state threaded through stages."""

    text: str
    # Matches produced so far; composer consumes lexicon output, post consumes all prior.
    matches: list[RecognitionMatch[NotationT]]
    # Stage-local scratch (e.g. normalized text, lexicon hit offsets).
    scratch: dict[str, object]


class Stage(Protocol[NotationT]):
    def run(self, state: PipelineState) -> PipelineState: ...
```

- `Pre` produces a normalized view and early-exit.
- `RegexStage` appends `match → RecognitionMatch` with `start=m.start()` / `end=m.end()`.
- `LexiconStage` (including `WholeInputLookup` as a lexicon variant for whole-input membership) appends alternation hits with the parameterized `BoundaryGuard`.
- `ComposerStage` **consumes `state.matches`** from prior stages plus `state.text` to fuse adjacent tokens (e.g., `lexicon hit ± amount`) and must reproduce the **exact combined `[start, end)`** the current single-regex grammars produce (see Migration Proof Harness).
- `PostStage` refines `state.matches` in place (span fixup, shape assignment, `E164Trim`, `UrlParenBalance`, `SiSplitPrefixClassifier`).

Stage order is fixed in `PipelineGrammar` (pre → regex → lexicon → composer → post); a grammar cannot reorder stages, only declare which to include.

### 3. Grammar declaration examples

**S1 — Date ISO8601** (pure shape):
```python
class ISO8601DateGrammar(PipelineGrammar[DateNotation]):
    name = "iso8601_recognition"
    semantics = "iso8601_calendar_date"
    single_value = False
    pre = StandardPre(empty_guard=True)
    regex = RegexStage(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
```

**S3 — Currency symbol** (lexicon-driven):
```python
class SymbolRecognition(PipelineGrammar[CurrencyNotation]):
    name = "symbol_recognition"
    semantics = "symbol_recognition"
    single_value = False
    pre = StandardPre(empty_guard=True, case="exact")
    lexicon = LexiconStage(
        tokens=SYMBOL_TOKENS, boundary=CurrencyBoundary, longest_first=True
    )
    post = QualifyPost(is_qualified=_is_qualified)
```

**S4 — Money symbol** (compositional — pattern stays in Money):
```python
from paxman.capabilities.Money.grammar import AMOUNT_PATTERN, classify_amount_shape


class SymbolRecognition(PipelineGrammar[MoneyNotation]):
    name = "symbol_recognition"
    semantics = "symbol_recognition"
    single_value = False
    pre = StandardPre(empty_guard=True)
    lexicon = LexiconStage(tokens=SYMBOL_TOKENS, boundary=MoneyBoundary)
    composer = AmountComposer(
        pattern=AMOUNT_PATTERN, order="either", lexicon_first=True
    )
    post = AmountShapePost(classify=classify_amount_shape)
```

> **Span-merge contract for composers:** `AmountComposer` must reconstruct the **exact combined span** `[min(symbol_start, amount_start), max(symbol_end, amount_end))` that the current single-regex `SYMBOL ? AMOUNT | AMOUNT ? SYMBOL` grammars produce (`Money/grammar/symbol_recognition.py:26-31`, `code_recognition.py:19-24`), including the ` ?` optional-space handling. Byte-identical `RecognitionMatch.start/end/raw_text` is the migration invariant; see Proof Harness below.

**S2 — Country name** (bypasses regex — WholeInputLookup is a lexicon variant):
```python
class NameGrammar(PipelineGrammar[CountryNotation]):
    name = "name_recognition"
    semantics = "name_recognition"
    single_value = True
    pre = StandardPre(empty_guard=True, normalizer=normalize_name)
    # Whole-input membership — a LexiconStage variant, not a separate stage kind.
    # Emits value=trimmed (original case), not the normalized key — matches
    # Country/name_recognition.py:70,76-80. No regex stage.
    lexicon = WholeInputLookup(keys=_KNOWN_NAME_KEYS)
```

`single_value` is a `Grammar` class attribute and must be carried through `PipelineGrammar` — examples above are explicit so contributors do not drop it (Country `name_recognition`, Phone `e164`, URL, ISBN all set it).

### 4. Migration — incremental, capability-at-a-time

1. **Land core stages + proof harness** — land `paxman/core/grammar/*` with unit tests; add `tests/property/test_grammar_stage_parity.py` (or `tests/unit/test_pipeline_parity.py`) — the **Migration Proof Harness** (see §4.1) — no grammar migration yet, full pre-PR gate green.
2. **Migrate Currency + Money** — highest duplication (shared SYMBOL/WORD_TOKENS) and the hardest composer case (either-order `SYMBOL ? AMOUNT`); proves S3→S4 and the span-merge contract.
3. **Migrate SIUnit** — proves S3+S5 split-prefix + S4 compound.
4. **Migrate Phone + URL** — proves S5 trims in isolation (`E164Trim(15)` span fixup `start+len(trimmed)` vs `match.end()`, URL paren-balance `start+len(trimmed)`).
5. **Migrate remaining S1 grammars** — mechanical (Date, Email, IP, ISBN); each PR runs `ruff + pyright + import-linter + pytest` per `.github/workflows/ci.yml`.
6. **Retire legacy helpers** — `Phone/grammar/common.py:strip_separators` and `Country/name_normalization.py` become stage internals or are deleted (flagged in `capabilities/AGENTS.md` as non-patterns).

Each step is behavior-preserving — `RecognitionMatch` output is byte-identical; engine routing (`semantics`) and candidate dedup are untouched.

#### 4.1 Migration Proof Harness (new — required gate)

Every migration PR must prove **byte-identical `list[RecognitionMatch[NotationT]]`** (span, `raw_text`, notation) between the old bespoke `recognize()` and the new `PipelineGrammar` declaration. This is **the** migration gate — lint/tests alone are insufficient.

- **Harness:** `tests/property/test_grammar_stage_parity.py` (or `tests/unit/test_pipeline_parity.py`) — parametrized over grammars and a curated corpus plus property-generated inputs. For each `(text)` pair, assert:

  ```python
  assert old_grammar.recognize(text) == new_grammar.recognize(text)
  # where equality is (start, end, raw_text, notation) per RecognitionMatch
  ```

- **Corpus must cover the tricky cases:** `Country/name_recognition` normalized-key vs original-case value, `Phone/e164` `E164Trim` (`end = start + len(trimmed)`), `URL` paren-balance (`end = start + len(trimmed)`), `Money` either-order `SYMBOL ? AMOUNT` span-merge, `SIUnit` split-prefix classifier, ISBN hyphen/space tolerance.
- **CI:** harness runs on every migration PR; failure blocks merge. The harness is **not** the benchmark harness.

**Benchmark note (clarifies B5):** `benchmarks/harness.py` is **informational, non-blocking** per `benchmarks/README.md` ("Baseline is tracked but not gated. CI runs 50 iterations informational (non-blocking)."). It does **not** gate migration. If a hard performance gate is desired (e.g., "no >5% p50 regression at 200 iterations"), it must be added as a separate ADR/CI change; this ADR does not introduce it.

**Abort criteria:** if a grammar cannot be made byte-identical without changing semantics, the migration PR is aborted and the grammar stays bespoke until the stage contract is extended — no silent divergence.

### 5. What is not changing

- `Grammar` ABC surface (`name`, `semantics`, `single_value`, `recognize` signature).
- `RecognitionMatch`, `Notation`, `Rule`, `Provenance`, `Resolution`, `ExecutionResult`.
- Engine pipeline (`_recognize` → `_collect_candidates` → `_enforce_single_value_invariant`).
- `grammar/data/` vs `rules/data/` boundary — authority mappings stay in `rules/data/`.
- Determinism and frozen-library guarantees.
- `get_grammars()` wiring — it will return `PipelineGrammar` instances with no caller change.
- Community extensions — `README.md`'s `Grammar[NotationT]` subclass example remains valid; shipped grammars may adopt the pipeline, but community extensions are **not** forced into it.

## Consequences

### Positive

- **Duct-tape removed.** Boundary guards (8 distinct lookarounds → parameterized `BoundaryGuard` family), alternation building, and post-trims (`E164Trim`, `UrlParenBalance`) have one definition each.
- **Declarative grammars.** A new grammar is ~15 lines of declaration, not a new `finditer` script. Review focuses on *what* the grammar recognizes, not *how* the loop is written.
- **Extended strategies become pluggable.** `ScannerStage`, `AutomatonStage`, or `UnicodePropertyStage` slot into step 4 without touching existing grammars — directly enabling `HOW_TO`'s unrealized strategies.
- **Tests stratify.** Stage unit tests (boundary, alternation ordering, E164 trim) + grammar declaration tests (token table + stage wiring) + the Proof Harness differential test replace 29 regex integration tests that currently re-cover the same logic.
- **No breaking change.** Engine, contracts, and public API (`paxman.canonicalize`, `register_capability`) are untouched; this is an internal recognition-layer refactor.

### Negative

- **Abstraction cost.** 29 working grammars are touched; each migration PR must prove byte-identical `RecognitionMatch` output via the Proof Harness. Mitigated by incremental capability-at-a-time migration.
- **Country name is the exception.** It skips the regex stage entirely — the pipeline must explicitly allow `regex=None`. A pipeline that forced every input through a regex would reintroduce the duct-tape it was meant to remove.
- **New indirection for contributors.** A contributor adding a grammar now reads `paxman/core/grammar/stages.py` in addition to `HOW_TO_ADD_NEW_CAPABILITY.md`. Mitigated by keeping `HOW_TO` as the entry point and referencing stages from there.

### Risks

- **Over-generalization.** A pipeline that tries to cover a future `automaton` before it is needed will overfit. Mitigation: ship only the stages needed for the 29 existing grammars (S1–S5); add new stage types when a capability actually needs them.
- **Wrong stage ordering.** Composition before lexicon would break Money. Mitigation: stage order is fixed in `PipelineGrammar` (pre → regex → lexicon → composer → post); a grammar cannot reorder stages, only declare which to include.
- **Performance regression.** Indirection could cost microseconds per `finditer`. Mitigation: stages compile regexes once at import time (same as today); `benchmarks/harness.py` provides an **informational** baseline (`benchmarks/README.md` — 50 iterations non-blocking, 200 locally) — it does **not** gate the PR. A gating benchmark would require a separate decision.
- **Composer span-merge divergence.** Lexicon+composer decomposition of `SYMBOL ? AMOUNT` could produce a different combined span than the current single regex if the composer's adjacency rule is imprecise. Mitigation: the Proof Harness's byte-identical gate + the explicit span-merge contract in §3.

## Alternatives Considered

1. **Keep 29 bespoke `recognize()` methods (status quo).** Rejected — duplication is already measurable (5× alternation, 8× boundary variants, 2× post-trim) and blocks `HOW_TO`'s extended strategies. Cost grows with each new capability.
2. **Inheritance hierarchy (`RegexGrammar`, `LexiconGrammar`, `CompoundGrammar`).** Rejected — forces a grammar into one bucket; Money needs lexicon *and* composition *and* post (`classify_amount_shape`), SIUnit needs lexicon *and* post-trim. Optional stages compose; subclasses do not.
3. **Middleware / decorator chain.** Rejected — order becomes implicit in decoration order; a fixed-order pipeline with optional stages is auditable and matches the pipeline mental model in the decision. (This ADR's design is a pipeline with optional stages, not classic Template Method — the Alternatives wording is aligned.)
4. **Single shared `recognize()` function parameterized by capability config.** Rejected — collapses 10 notations into one function with capability-specific branches; loses per-grammar `name`/`semantics` audit identity and `get_grammars()` wiring.

## Open Questions

1. **Fixed order as hard limit?** `PipelineGrammar` fixes order to pre → regex → lexicon → composer → post. No shipped grammar needs a different order; if a future grammar did, should it be a new stage kind within the fixed order or an escape hatch to bespoke `recognize()`? Default: extend the fixed order before adding an escape hatch.
2. **`get_grammars()` and community extensions?** Shipped grammars will return `PipelineGrammar` instances; community `Grammar` subclasses (per `README.md` "Community Extensions") are unaffected and not required to adopt the pipeline.
3. **Benchmark gating?** Should `benchmarks/harness.py` ever become a hard gate (e.g., p50 regression >5% fails CI)? Out of scope for this ADR; would be a separate ADR/CI change.

## References

- Survey: `paxman/capabilities/*/grammar/**` (29 grammars, 56 files) — 2026-08-20 recognition-strategy analysis (Rev.1 corrected; Draft erroneously stated 30 grammars and 19/1/5/4/5=34 instances)
- `paxman/capabilities/AGENTS.md` — sanctioned strategies (Regex + Lexicon key-only), hard rules, legacy exceptions
- `paxman/core/AGENTS.md` — core is capability-agnostic (no capability imports, domain vocabulary ownership) — anchors §2 layering
- `HOW_TO_ADD_NEW_CAPABILITY.md` — extended recognition-strategy section (scanner, format-candidate, parser combinators, Unicode-property, automaton)
- ADR-0001 — Clean Architecture Pipeline (Recognition vs Validation seam)
- ADR-0003 — Semantic Affinity Routing (`semantics` as routing key, `target_semantics`)
- ADR-0004 — Single-Value Invariant (`single_value`, span clustering)
- `paxman/core/domain.py` — `Grammar`, `RecognitionMatch`, `Rule`, `Provenance`
- `paxman/engine/orchestrator.py` — `_recognize`, `_collect_candidates`, `_enforce_single_value_invariant` (`recognize` at L185)
- `paxman/capabilities/Money/grammar/__init__.py` — `AMOUNT_PATTERN`, `classify_amount_shape` (remain in Money; passed to composer as parameter — Rev.1 layering fix)
- `benchmarks/harness.py` + `benchmarks/README.md` — **informational, non-blocking** (50 iterations in CI, baseline tracked not gated) — not a migration gate (Rev.1 clarification)

(End of file — Rev.1, 2026-08-20)
