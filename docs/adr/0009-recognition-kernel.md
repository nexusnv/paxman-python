# ADR-0009: Recognition Kernel — A Unified, Stable Spine for the Recognition Layer

## Status

**Accepted — 2026-08-26 (Rev.4).** This ADR **supersedes**:

- **ADR-0008** (Staged Recognition Pipeline, Accepted 2026-08-20) — the fixed-order
  `pre → regex → lexicon → composer → post` pipeline becomes **Obsolete** (see its status
  change and changelog).
- **The prior ADR-0009 draft** ("Staged Pipeline Extensions", withdrawn before acceptance;
  preserved in git history) — the seven staged-extension proposal (NormalizedView, Automaton,
  Scanner, UnicodeProperty, FormatCandidate, GenericComposer, LabelStage). Its taxonomy is
  re-derived here as matcher *kinds* over a shared substrate, not as additional pipeline
  *stages*.

> **⚠ BREAKING CHANGE (intentional, scoped).** This ADR fixes a correctness defect: inputs
> in which a whole-input vocabulary match is invisible today and a short code is validated in
> its place — e.g. `canonicalize("Ship to United States please", Country)` currently returns
> `SUCCESS "TO"` (Tonga) — will raise `MultipleMentionsError` under a `single_value`
> contract, with all mentions exposed via the new `paxman.scan()` API. Target release:
> **0.2.0** (pre-1.0 minor bump). Full old→new behavior table and migration guidance:
> Part VII "Compatibility".

This ADR synthesises two independent from-scratch design reviews of the working tree
(2026-08-24, conducted without cross-communication), which converged on the same diagnosis
and target architecture. The reviews' working notes are ephemeral by policy; accordingly,
**this ADR is self-contained** — every load-bearing measurement, design rule, and capability
mapping is carried here as ADR-owned data, and no ephemeral document is cited.

The durable wins of ADR-0008 — the declarative `Grammar` surface, parameterized boundary
handling, the byte-identical parity harness as the hard migration gate, and the
core-is-capability-agnostic layering — are **inherited and re-based** onto the kernel, not
discarded.

## Changelog

| Version | Date | Author | Summary of change |
|---------|------|--------|-------------------|
| Draft | 2026-08-24 | Sisyphus | Initial draft — Recognition Kernel as the recognition-layer spine. |
| Rev.1 | 2026-08-24 | Sisyphus | Expanded to a self-contained decision document: first-principles invariants; per-kind matcher contracts; `BoundarySpec` preset mapping; normalizer table; offset-map discipline; F1 fix + `scan()`/mention model; freeze compilation + `recognition_revision`; `Snapshot` data rails; shipped-capability mapping (15 capabilities / 36 grammars — corrected from the stale "33", which predated Language shipping); future-families mapping; performance model; verification strata; streaming design; comparative matrix. |
| Rev.2 | 2026-08-24 | Sisyphus | **Review-driven corrections.** (1) Removed every citation of ephemeral working notes — measurements and mappings are now ADR-owned data with no external document dependencies. (2) Added the BREAKING CHANGE banner (Status) and the Compatibility subsection (Part VII): old→new behavior table, migration snippet, semver guidance (0.1.0 → 0.2.0), `recognition_revision` as the same-snapshot diff signal. (3) Demoted streaming and the suppression table from binding constraints to deferred, non-binding designs. (4) Specified `MatcherSpec.requires_features` omission semantics (matcher omitted at freeze; zero-active-matcher grammar → `MISSING`). (5) Specified the consuming-boundary span rule (anchors consumed for advance, never part of the emitted span — parity with `ipv6_token`). (6) Stated the offset-map invariant precisely (`offsets[i]` bounds subject char `i`'s source; span `[s,e)` → `[offsets[s], offsets[e])`). (7) Defined anchor primitives (`HAS_DIGIT` ≡ `re.search(r"\d", text)`). (8) Split Part IV into **Measured** (pre-kernel tree) vs **Projected** (kernel; confirmed per phase, never a gate). (9) Added the grammar-count enumeration footnote. (10) Clarified `Normalizer.provenance` as declaration-level metadata — `Resolution.provenance` stays rule-owned. (11) Corrected the `degree_word_sign` preset row (asymmetric guards). |
| Rev.3 | 2026-08-24 | Sisyphus | **F1 parity exemption.** Clarified that `Country name_recognition` F1 migration is exempt from the byte-identical gate and is gated instead by the honest-behavior regression test (Part V abort criterion / Part VI Phase 1). |
| Rev.4 | 2026-08-26 | Sisyphus | **Accepted + remediation amendments.** (a) Status Proposed→Accepted after post-landing evaluation (2026-08-26, findings R1–R12) and kernel remediation Part A (A1–A7): boundary O(1) checks (§10), per-matcher digest memoization (§13), emit-signature validation at construction (§13), two-array offset maps (§6 D3), single-pass CountryNameFold, ``view="country_normalized"`` alias removal, single recognition path via ``PipelineGrammar.recognize`` delegation; ADR-0008 already Obsolete. (b) D3 amendment (A4): offset-map invariant now two-array — ``[s,e)`` in view → ``[starts[s], ends[e-1])`` in original (was ``[offsets[s], offsets[e])``), length-preserving views stay ``offsets=None`` identity; general maps land with URL IDNA as first length-changing customer per D3 phasing. (c) §13 clarification: contract-dependent ``requires_features`` omission happens at match time (engine_loop compat shim) not at freeze — registry freezes without a contract; emit-signature validation moves to matcher construction (``_emit_validation``), engine loop keeps only ``callable(emit)`` guard. (d) Split-prefix deviation note: SIUnit ``_SPACED_SYMBOL_TOKENS`` (24×820=19,530) materialized as interim lexicon; target is combinator ``seq(prefix, ws, unit)`` per §9.4 — resolved by B2 (``CombinatorMatcher`` + 820-token base lexicon). (e) Suppression §16 deferred→shipped: common-word suppression table (``common_words.py``) ships off-by-default gated by ``suppress_common_words`` (B1) — ``scan()`` promotion gated on B1 landing. |

## Contents

- **Part I — Context** (§1–§4): where recognition stands, the failure catalog with evidence,
  independent convergence on one architecture, the investment thesis.
- **Part II — Decision** (§5–§18): the kernel — substrate, normalizers, matcher spec, seven
  kinds, boundaries, anchor tier, assembly, F1 fix, freeze compilation, data rails,
  simplifications, deferred streaming, non-changes.
- **Part III — Capability mapping** (shipped 15/36 + future families).
- **Part IV — Performance model** (measured vs projected).
- **Part V — Verification.**
- **Part VI — Migration.**
- **Part VII–X** — Consequences (incl. **Compatibility / Breaking Change**), comparative
  matrix, alternatives, open questions.

---

# Part I — Context

## 1. Where recognition stands

Paxman ships **15 capabilities, 36 grammars**[^grammars] behind a single contract:
`Grammar[NotationT].recognize(text) -> list[RecognitionMatch]`, where a `RecognitionMatch`
carries the notation plus a half-open `[start, end)` span and `raw_text`. Per ADR-0008,
every grammar is a `PipelineGrammar` declaring optional stages in the **fixed order**
`pre → regex → lexicon → composer → post`, threading `PipelineState{text, matches, scratch}`.

[^grammars]: Verified 2026-08-24 by enumeration — BIC 1, Country 4, Currency 3, Date 4,
Email 3, IBAN 1, IP 2, ISBN 2, ISSN 1, Language 3, Money 3, ORCID 1, Phone 4, SIUnit 3,
URL 1. Reproduce: `grep -rE "class \w+\((Pipeline)?Grammar\[" paxman/capabilities/*/grammar/*.py`
→ 36 matches; cross-checks against the README capability table (grammar column sums to 36).
ADR-0008's "29 grammars" was correct for the 2026-08-20 tree (10 capabilities); the tree has
since grown to 15.

The engine owns all cross-match policy (ARCHITECTURE.md, "Recognition Pipeline Contract"):

- **Containment dedup (per grammar):** a match fully contained in a longer match from the
  *same* grammar is dropped ("longer wins"); identical spans keep the first-emitted.
  Dedup never runs across grammars, so two grammars agreeing on one span (US vs European
  reading of `01/02/2026`) are both preserved — ambiguity stays observable.
- **Total document ordering** `(start, end, active-set index, grammar name)`.
- **Semantics routing** (`target_semantics`), `single_value` enforcement, `MISSING` vs
  `INVALID` vs `AMBIGUOUS`, provenance-first validation, `format_value()` as the sole
  presentation seam, determinism by construction, zero runtime dependencies.

ADR-0008 was the right move: it replaced 29 bespoke `recognize()` scripts with a declarative
surface, unified eleven boundary lookarounds behind `BoundaryGuard`, absorbed the
`re.escape`-join copies into `LexiconAlternation`, and introduced the byte-identical parity
harness. **Those wins are the foundation this ADR builds on.** The five-slot pipeline made
recognition *auditable*; it did not make it *general*.

## 2. The failure catalog (verified in source or measured 2026-08-24)

**F1 [measured] — Whole-input vocabulary matching cannot see embedded values, and short-code
grammars silently fill the void.**

```
paxman.canonicalize("United States", Country.create_contract())
  → SUCCESS "US"                                    # whole-input lookup hits
paxman.canonicalize("Ship to United States please", Country.create_contract())
  → SUCCESS "TO"                                    # ← Tonga. Not AMBIGUOUS. Not an error.
paxman.canonicalize("German", Language.create_contract())   → SUCCESS "de"
paxman.canonicalize("She speaks German fluently", ...)      → INVALID
```

Mechanism (verified by running the grammars directly): on the Tonga input the *only*
recognition is `alpha2_recognition, span=(5,7), raw='to' → CountryNotation(shape='alpha2',
value='TO')`. The name grammar (`WholeInputLookup`) never fires because the input is not
exactly a name; the two-letter preposition is a shape-valid alpha-2 code and ISO 3166
validates Tonga. **A confident, provenance-backed, wrong answer on ordinary prose** — the
single most important defect in the layer, and it is structural: recognition keys are
restricted to whole input, and nothing distinguishes a short code in running text from a short
word.

**F2 [measured] — O(grammars × text) rescan.** Every grammar independently `finditer`s the
full text; nothing is shared — no tokenization, no normalized views, no candidate positions.
Recognition-only cost for a 68-char input across all 15 capabilities is **~1.30 ms**
(si_unit 376 µs / 3 grammars; language 175 µs; country 142 µs; …; url 11 µs). The committed
`benchmarks/baseline.json` shows whole-pipeline p50s of 0.09–0.24 ms per capability —
recognition is already the dominant fraction of several. Cost grows linearly with text length
and grammar count; the project roadmap targets 30 capabilities.

**F3 [measured] — Regex alternation degenerates at lexicon scale.** SIUnit tables,
semantics byte-identical (correctness cross-checked equal):

| Corpus | regex alternation (650 names) | dict trie | ratio | regex alternation (820 symbols) | dict trie | ratio |
|---|---|---|---|---|---|---|
| 50 chars, no hits | 165 µs | 42 µs | 3.9× | 168 µs | 55 µs | 3.0× |
| 430 chars, hit-dense | 545 µs | 156 µs | 3.5× | 1,051 µs | 442 µs | 2.4× |
| 2.2 KB prose | 6,637 µs | 1,020 µs | 6.5× | 6,609 µs | 1,049 µs | 6.3× |

Build cost at 650 tokens: regex compile 3.8 ms vs trie build 3.1 ms — parity. The trie is a
plain dict-of-dicts **without** failure links, **word-anchored** (entered only at word starts —
the FlashText model). Alternation is O(positions × alternatives); a word-anchored trie is
O(text). The gap **widens** with text length and lexicon size. This corrects the prior
in-repo pessimism about pure-Python tries.

**F4 [verified] — The fixed five-slot pipeline leaks.** Workarounds shipped in tree:

- `Language/grammar/bcp47_tag_recognition.py` — `_BCP47RegexStage`, a **private duplicate of
  `RegexStage`** that scans an underscore→hyphen-normalized copy while slicing `raw_text` from
  the original. It exists because `PipelineState.text` is immutable (correctly), `scratch` is
  never threaded (ADR-0008's normalized-view hook is dead code), and `RegexStage` cannot opt
  into another view.
- The same file — `_bcp47_notation`, a ~160-line hand-written positional parser
  (extlang/script/region/variant/extension/privateuse state machine) living inside a regex
  callback: a parser with no home — too complex for `notation_fn`, forbidden from being a
  stage (no slot fits), invisible to the type checker as a unit.
- URL paren-balance and Phone E.164 15-digit-window trimming both live in `PostStage`
  transforms — **scanners wearing a post-processor's coat**, mutating spans after the regex
  has over-matched.

**F5 [verified] — Boundaries are regex lookarounds compiled into patterns.** Eleven
`BoundaryGuard` factories (`paxman/core/grammar/boundary.py`) encode boundaries as
lookbehind/lookahead strings interleaved into every scanning pattern; boundaries are evaluated
by the regex engine at *scan positions* (not just hit positions), cannot be reasoned about as
data, and `ipv6_token` is already flagged "not interchangeable" with the lookaround mental
model; Phone `national` is a 4-lookbehind chain. Email and IPv4 still use verbatim `\b`.

**F6 [verified] — One mention per call is structural.** `_enforce_single_value_invariant` +
`MultipleMentionsError` (ADR-0004) mean multi-entity input must be split by the caller
(`docs/recipes/segmentation.md`). Combined with F1: the *only* way to find "United States"
inside prose is to know where it is beforehand.

**F7 [verified] — stdlib `re` is a ceiling, not a floor.** No `\p{...}` classes; no
multi-pattern sets; backtracking with ordered alternation. Every escape hatch (`regex`,
`google-re2`, Hyperscan, Rust `regex` via PyO3) is a compiled extension that violates the
zero-runtime-dependency constraint.

**F8 [verified] — Recognition keys are hand-duplicated projections of authority data.** BIC
`grammar` embeds a 250-entry `_COUNTRY_CODES` frozenset duplicating
`rules/iso_9362_ed2022.COUNTRY_CODES` (hand-maintained); Language's grammar-side name keys
(77) are a separate catalog from the rule-side ISO/IANA tables (995 + 420 + 215 entries);
Currency/Money symbol/word tokens are generated from the shared snapshot (good — generated)
but the pattern is not universal.

## 3. Independent convergence on one architecture

Two from-scratch design reviews of the working tree — conducted independently, without
cross-communication, both read-only — produced the **same diagnosis and the same target
shape**:

> **Scan once into a shared substrate; match with a small, fixed set of declarative matcher
> types; assemble centrally under the existing engine policy.**

Both grounded it in the same survey of mature systems, from which five convergent lessons
follow (every system that survived contact with scale does these):

1. **One shared substrate, computed once, never mutated** — UIMA's CAS, GATE's tokenise-once,
   spaCy's `Doc`, Lucene's `TokenStream`. Standoff annotations/views point into it with offset
   discipline.
2. **Matching behavior is data** — libphonenumber's per-region XML metadata, gazetteer lists,
   ICU `UnicodeSet` ranges, Hyperscan pattern databases. Adding a region/format/lexicon is a
   data change, not a code change.
3. **Cheap tiers before expensive tiers** — Hyperscan's literal prefilter + NFA islands,
   libphonenumber's `isPossibleNumber` before `isValidNumber`, length caps and `maxTries`
   bounds against degenerate input.
4. **Assembly policy is centralized and declarative** — spaCy `EntityRuler`'s "longer first,
   then earliest" as declared data; never distributed across matchers.
5. **Errors are diagnostics, not crashes** — WHATWG URL's non-fatal validation-error
   taxonomy; stdnum's typed exceptions converted to reasons. The pipeline keeps going and
   reports what it saw.

Load-bearing borrowings, by source system:

- **libphonenumber**: bounded patterns (every component length-capped — digit blocks
  ≤ 20); matcher-level suppression data (date-shaped/citation-shaped digit-run guards
  *inside* the matcher — the direct answer to the `to → Tonga` class); two-tier validation
  (`isPossible` length-check before `isValid`); non-overlapping advance (`index =
  lastMatch.end()`); all per-region behavior as data. Reject: single-best-match semantics
  (collapses ambiguity — Paxman's `AMBIGUOUS` must survive).
- **Hyperscan / RE2 / Rust `regex`**: the literal-prefilter + automaton decomposition and
  compile-the-union-at-build-time discipline. Reject: adopting any as a dependency (compiled
  extensions; leftmost-winner semantics).
- **Aho–Corasick / FlashText**: the word-anchored dict trie as the default lexicon matcher
  above the crossover (~500 keywords per FlashText's published benchmark; measured here at
  2.4–6.5× at 650–820 tokens). Reject: C-extension AC libraries.
- **UIMA / GATE / spaCy / Lucene**: shared substrate with standoff annotations; declared
  component contracts; Lucene's **offset-correctness rule** (char filters must track
  corrected offsets; token filters must not modify offsets) for every normalized view;
  EntityRuler's overlap policy as data. Reject: the framework weight.
- **ICU / ICU4X**: property classes as generated sorted-range data; alias-table
  canonicalization (UTS #35 Annex C — the industry analog of Paxman's Language capability);
  snapshot→generate→verify CI with version stamps. Reject: PyICU (C++ extension).
- **Ragel / re2c / WHATWG**: declarative scanners with actions; non-fatal validation errors
  as the model for recognition-layer diagnostics.
- **pyparsing / Lark / nom / winnow / pest**: span-preserving scanning APIs (`scan_string`,
  `Lark.scan` with `propagate_positions`) and the combinator model —
  `(input, pos) → (new_pos, value) | None` with span capture. Reject: as dependencies or
  whole-document parsers (wrong shape, performance envelope).
- **Hugging Face `tokenizers`**: normalization as a first-class composable stage
  (`Sequence([NFD(), StripAccents(), Lowercase()])`) producing a `NormalizedString` with
  original→normalized offset maps — the typed answer to the dead `scratch` hook.
- **dateparser / chrono-node / dateutil / python-stdnum**: the parser→refiner two-phase
  architecture with span-aware candidates; ordered-chain first-match-wins as an anti-pattern;
  stdnum's convention-over-framework as the counter-example validating Paxman's unified
  contract; dateutil's caller-supplied disambiguation flags (Paxman's contract flags are the
  same move).
- **rustc query system**: every derived artifact (compiled matcher, view, trie, word-span
  index) is a pure function of immutable inputs, computed once on demand and identified by
  its inputs — the formal skeleton for deterministic replay.
- **pycountry**: indexed database lookup as the correct model for registry-style
  capabilities (`Database[Record]` with auto-built indices, not regex scan).

**Where the two reviews' proposals diverged**, this ADR resolves each divergence explicitly
(§15, Part IX): the shared-substrate + measured matcher selection + anchor-prefilter design is
the **spine**; the recognizer taxonomy (candidates, label), typed input views, and normalizer
provenance are adopted as first-class kinds and data; DAG/parallel execution and a
contract-seam redesign are rejected with reasons; streaming is designed-for but deferred.

## 4. The investment thesis

This ADR deliberately accepts a **one-time, heavier migration** — harder to land now than
extending the five-slot pipeline — because it buys a **stable spine**: recognition stops being
a place where new capability shapes require new machinery or new workarounds, and becomes a
place where new capabilities are **data declarations** over an existing, proven kernel.

The cost is paid once. Every future capability — Language (BCP 47 at full IANA scale), the
IBAN per-country registry, ISIN/CUSIP/LEI/FIGI, RFC 3339, DOI/URN, Timezone, postal/VAT, and
the lexicon-heavy set (MIME, charset, SPDX, chemical elements, CSS colors, TLDs) — then lands
as configuration, not engineering. Developer experience, drift minimization, and future
scalability are the point; implementation difficulty is the accepted price of entry.

---

# Part II — Decision

Adopt the **Recognition Kernel** as the recognition-layer spine:

> **Scan once into a shared substrate; match with declarative matcher specs (regex / lexicon /
> scanner / combinator / property / candidates / label — all first-class); assemble centrally
> under the existing engine policy.**

The engine contract is untouched: `RecognitionMatch`, within-grammar dedup, total document
order, cross-grammar ambiguity preservation, semantics routing, `MISSING`/`INVALID`
distinction, provenance-first validation, `format_value()` presentation, determinism, zero
runtime deps, capability isolation. **The kernel replaces how recognition executes, not what
recognition promises.**

```
                      ┌────────────────────────────────────────────────────────┐
                      │  Registration freeze ("capability compile")            │
                      │  MatcherSpec (data) ──► compiled Matcher               │
                      │  (trie built, regex compiled, closures bound,          │
                      │   anchors/boundary resolved; pure fn of snapshot)     │
                      └────────────────────────────────────────────────────────┘

canonicalize(text, contract)
   │
   ▼
┌────────────────────────────── Recognition Kernel ──────────────────────────────┐
│  L0  Substrate (ScanContext)          — computed once per call                  │
│      text (immutable)                                                          │
│      word_spans   ← one C-speed \w+ pass (shared by all matchers)              │
│      views{}      ← lazily: ("casefolded" | "normalized" | "idna" | …)          │
│                     + offset map where the transform changes length             │
│                                                                                 │
│  L1  Match loop (engine-owned)                                                  │
│      for each active grammar's matcher:                                         │
│        T0 anchor prefilter   — necessary literals/classes present? (C-speed)    │
│        T1 shape match        — regex / trie / scanner / combinator on a view    │
│        T2 emit               — RecognitionMatch(notation, start, end, raw)      │
│           (spans always relative to ORIGINAL text; views carry offset maps)     │
│                                                                                 │
│  L2  Assembly (existing engine policy — unchanged)                              │
│      within-grammar containment dedup ("longer wins")                           │
│      total order (start, end, active-set index, grammar name)                   │
│      cross-grammar ambiguity preserved                                          │
└─────────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
  _collect_candidates → rules → provenance → format_value     (unchanged)
```

The key structural property: **the prior draft's seven stage types are exactly
`{view × kind × combinator}`** — three orthogonal axes instead of seven fixed slots. One
mechanism, fewer concepts, and nothing left that needs a private fork.

## 5. First principles — invariants the kernel must preserve

Every rule below is binding on all matcher kinds.

**Must:**

1. **Determinism** — same `text + contract + snapshot + registry` → same
   `list[RecognitionMatch]` bit-for-bit. No clock, no network, no RNG, no world-knowledge
   ordering, no `dict`/`set` iteration order in any observable position. Total order remains
   `(start, end, declaration index, grammar name)`.
2. **Provenance-first** — recognition never decides validity; it only proposes spans.
   `Rule.matches()` owns authority. `MISSING` (no span) vs `INVALID` (span, no rule) is
   load-bearing and must remain exact. **Including for normalization**: if `µ → μ` or
   `² → 2` or `en_US → en-US` changes the surface, the transformation's authority (BIPM,
   UTS #46, BCP 47) must be citeable, not silent (§7).
3. **Span-bearing, zero-copy** — every `RecognitionMatch` carries a half-open `[start, end)`
   into the *original* text with `raw_text == text[start:end]`, enforced at the engine
   boundary. Scanners, normalizers, and lexicon matchers preserve this via offset maps, never
   by mutating text.
4. **Capability isolation** — `paxman.core` imports nothing from `paxman.*` capabilities;
   per-capability `grammar/data/` remains the home for vocabulary (key-only, no authority
   mappings — those stay in `rules/data/`); `shared_data/` remains the snapshot seam.
5. **Zero runtime dependencies** — stdlib only. Optional compiled acceleration may never be
   required.
6. **Testability per matcher** — every matcher kind is unit-testable in isolation with
   `text → list[RecognitionMatch]` without a full capability or engine.
7. **No checksum-fused recognition** — `mod97` (IBAN), MOD 11-2 (ORCID), Luhn (ISIN/CUSIP)
   stay in `Rule.matches()`. Early rejection would collapse `MISSING` vs `INVALID` and
   duplicate authority tables into grammars.

**Must not:** ML/NER (non-deterministic, authority-less); fuzzy/approximate matching
(`lev("BRMA","BURMA")==1` has no authority clause); environment-dependent ordering; silent
divergence from the parity gate.

## 6. The substrate — `ScanContext`

The minimal shared structure, computed **once per `canonicalize()` call** (once per `scan()`
call across capabilities, §16), deliberately dumber than spaCy's `Doc` — no POS, no lemmas,
no vectors; determinism and zero-dep forbid:

```python
@dataclass(frozen=True, slots=True)
class ScanContext:
    text: str                                   # original, immutable
    word_spans: tuple[tuple[int, int], ...]     # one re.finditer(r"\w+") pass, C-speed
    _views: dict[str, View]                     # lazy, keyed by view name

    def view(self, name: str, normalizer: Normalizer) -> View: ...

# View = (subject: str, offsets: tuple[int, ...] | None)
#   length-preserving normalizers → offsets=None (identity, zero cost)
#   length-changing normalizers  → offsets map subject→original positions
```

Three binding design rules:

- **D1 — Word spans are the only eagerly-computed index.** A single `re.finditer(r"\w+")`
  pass is one C-level pass — a single `finditer` far cheaper than any individual shipped
  grammar's scan (its cost is measured and recorded at Phase 0 landing; Part IV lists it as
  projected until then). Every word-anchored matcher — tries, code grammars, name grammars —
  consumes it instead of re-deriving boundaries. This is GATE's "tokenise once" and
  FlashText's "iterate words, not chars."
- **D2 — Views are lazy and offset-disciplined** (Lucene `CharFilter` rule; the typed-view
  discipline from the recognizer-taxonomy design). A view is `(subject, offsets)`; matchers
  scan `subject` but emit spans translated to the **original** text. Length-preserving views
  (`lower`, `_→-`, table-driven accent strip) have `offsets=None` and cost nothing at emit
  time. `en_US → en-US`, Country `normalize_name`, SI `²→2`, URL IDNA stop being
  grammar-local mutations and become declared views. This **subsumes** the prior draft's
  `NormalizedViewStage` + `scratch["__normalized"]` + `source` threading with strictly less
  machinery: the view is an argument, not a hidden dict.
- **D3 — Offset-map invariant and phasing.** The general offset map is specified now but
  lands with the first capability that genuinely needs a length-changing view (URL
  IDNA/tab-strip is the expected first customer); v1 ships identity views plus the
  scanner-side alternative (a scanner can skip separators as inline state — Phone E.164
  needs no compacted view, Part III).

  **Offset-map invariant (binding whenever a view carries `offsets`):**

  - `len(offsets) == len(subject) + 1`.
  - `offsets[i]` is the original-text offset at which the **source of subject character
    `i` begins**: `text[offsets[i]:offsets[i+1]]` is the (non-empty) source interval of
    `subject[i]`.
  - A half-open view span `[s, e)` translates to the original span
    `[offsets[s], offsets[e])` — `offsets[e]` is the exclusive end by construction, since
    it is where the source of `subject[e]` would begin.
  - Degenerate case: length-preserving views carry `offsets=None`; there the translation
    is the identity and `text[o_start:o_end] == subject[s:e]` holds exactly.
  - The engine's existing `raw_text == text[start:end]` validation remains the net safety
    net for **every** emitted match, regardless of view.

## 7. Normalizers — first-class, composable, provenance-aware

Views are materialized by normalizers that carry citeable provenance:

```python
class Normalizer(Protocol):
    name: str
    provenance: Provenance | None   # citeable if the transform has authority
    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]: ...
    # returns (subject, offsets_or_None)

@dataclass(frozen=True, slots=True)
class NormalizerSequence:
    steps: tuple[Normalizer, ...]   # composable, mirrors HF tokenizers Sequence
```

**Provenance semantics (clarification):** `Normalizer.provenance` is **declaration-level
metadata** — it documents, on the declaration, the authority for a surface-changing transform
(BIPM, UTS #46, BCP 47 §2.1) and is citeable in diagnostics and documentation. It does **not**
alter result provenance: `Resolution.provenance` continues to come solely from validating
`Rule`s — recognition stays provenance-neutral and never decides validity.

Shipped set (all pure, deterministic, stdlib-only):

| Normalizer | View name | Purpose | Offsets | Provenance |
|---|---|---|---|---|
| `CaseFold` | `casefolded` | case-insensitive lexicons (Currency words, SIUnit names) | identity | lexical (none) |
| `SeparatorFold` | `normalized` | `_ → -`, BCP 47 §2.1 (`en_US → en-US`) | identity | BCP 47 |
| `AccentStrip` | `normalized` | table-driven accent strip + lower (Country `normalize_name`) | identity (table-driven) | CLDR / ISO 3166 |
| `SymbolFold` | `normalized` | `² → 2`, `µ → μ`, `Ω`, `Å` (SIUnit) | identity-first; general map per D3 | BIPM SI Brochure |
| `IDNAFold` | `idna` | UTS #46 `MAPPED` + tab/newline strip (URL) | **expanding — general map** | UTS #46 |
| `StripSeparators` | `compact` | `" ().-" → ""` compact digits (Phone) | **compressing** | ITU-T E.164 |

Each capability declares its normalizer chain declaratively; the kernel materializes each view
once and shares it across all of that capability's matchers. This eliminates the per-file
`normalize_name` / `strip_separators` / `²→2` duplication and makes every surface-changing
transform citeable.

## 8. `MatcherSpec` — recognition as data

A grammar becomes a thin declaration over matcher specs, with the recognizer taxonomy folded
in as kinds:

```python
@dataclass(frozen=True, slots=True)
class MatcherSpec(Generic[NotationT]):
    kind: Literal["regex", "lexicon", "scanner", "combinator",
                  "property", "candidates", "label"]
    payload: ...                      # per-kind, see §9
    view: str | None                  # None = original text; else view name (D2)
    boundary: BoundarySpec | None     # declarative, see §10
    anchors: AnchorSet                # necessary conditions, cheap tier, see §11
    emit: EmitFn                      # (raw_span, context) -> NotationT
    requires_features: frozenset[str] = frozenset()   # declared, mirrors Rule.requires_features
```

**`requires_features` semantics (binding):** a matcher whose `requires_features` is
unsatisfied under the contract is **omitted from the compiled set at freeze** — never a
freeze-time failure. A grammar left with zero active matchers recognizes nothing, so its
shapes resolve `MISSING` (not `INVALID` — that status is owned by rules). This mirrors
shipped grammar gating exactly (`include_ipv6=False` → IPv6 shapes `MISSING`).

Specs are **compiled at registry freeze** (§13): trie built, regex compiled, scanner closures
bound, boundary/anchor tables resolved. A compiled matcher is a pure function of
`(spec, snapshot)` — the rustc-query discipline; nothing observable is computed per-call that
could depend on call order.

## 9. The seven matcher kinds

Each kind is specified with: **when to use → implementation contract → scales to → shipped
migration → roadmap**. `candidates` and `label` are thin, ergonomic wrappers over
`combinator` (ordered `alt` with per-candidate semantics routing; `seq(label, separator,
core)` respectively) — they add *named* kinds without new machinery.

### 9.1 `regex` — pure shape

- **When:** the spec defines a syntactic shape — character classes, repetitions, bounded
  separators. BIC, IBAN, ISBN/ISSN cores, IP v4, Date, Email standard, Phone tel-URI/00.
- **Contract:** `re.compile(pattern, flags).finditer(view.subject)` with
  `notation_fn: re.Match → NotationT`, offset-translated at emit. Patterns must carry
  **bounds** (max digit-run, max repetition — libphonenumber's `digitBlockLimit` discipline)
  so worst-case work is linear on adversarial input. No backreferences; catastrophic
  constructions are linted.
- **Scales to:** single-pattern shape. *Not* the answer for large lexicons.
- **Migration:** mechanical from `RegexStage`; verbatim `\b` (Email, IPv4) becomes
  `BoundarySpec.WORD`.
- **Roadmap:** ISIN, CUSIP/FIGI/LEI, UUID, MAC, semver, credit card.

### 9.2 `lexicon` — vocabulary

- **When:** the spec defines a vocabulary — Country names (~600 union keys), SIUnit symbols
  (820) / names (650), Currency symbols (67) / words (80), Language ISO 639-3 names (995 →
  trie tier), future Timezone/MIME/charset/SPDX/elements/colors/TLDs.
- **Contract:** `payload: tokens` (key-only — authority mapping stays in `rules/data/`).
  **Representation is auto-selected by size** (measured, §2 F3): `≤ ~500` tokens → regex
  alternation (the C engine wins at small scale; FlashText crossover); `> ~500` →
  **word-anchored dict trie** (pure Python wins 2.4–6.5× at shipped scales). Symbol and
  other non-word lexicons pin `representation="alternation"`. Both representations must emit
  **byte-identical match sequences** (parity-tested) — the switch is invisible above the
  matcher.
- **Trie scan semantics (binding):** longest-match-at-word-start wins (deepest leaf);
  ties break by declaration order mirroring `LexiconAlternation`'s
  `(-len, -is_qualified, token)` sort. Multi-word keys span spaces via `word_spans`. The
  trie's first-level keys double as an anchor `frozenset[str]` prefilter (§11).
- **Scales to:** O(text) independent of dictionary size — 15k IANA subtags is still one scan.
- **Migration:** Country names (F1 fix), SIUnit symbol/name (largest scan cost), Language
  names; Currency/Money stay alternation (below threshold).
- **Roadmap:** every lexicon-heavy future capability is data-only.

### 9.3 `scanner` — character state machine

- **When:** recognition needs character-by-character state — delimiter balancing (URL paren
  depth, including nested `https://x/a(b(c)d)e`), digit-run bounding (Phone E.164 ≤ 15
  digits), separator skipping, escaped delimiters.
- **Contract:** `scan: (context, pos) → (end, NotationT) | None`. The kernel's loop: try the
  scanner at each candidate position, advance to `end` on hit, `pos + 1` on miss —
  libphonenumber's non-overlapping advance discipline. Scanners may consume views (D2) and
  read `word_spans`; they carry **bounds as data** (max window). The `_url_scan` closure
  pattern becomes a first-class, typed, unit-testable function — not a `PostStage` transform.
- **Scales to:** one pass, no regex backtracking, depth-aware.
- **Migration:** URL paren-balance + bare-scheme drop; Phone E.164 15-digit window (retiring
  `PostStage` and the LRU trim); IP v6 delimiter anchoring; the entire BCP-47 subtag walk
  (deleting `_BCP47RegexStage` and the 160-line callback — the flagship readability win).
- **Roadmap:** DOI/URN balanced suffixes; postal/VAT structured fields.

### 9.4 `combinator` — compositional and recursive shapes

- **When:** a canonical shape decomposes into orthogonal pieces — Money either-order
  `lexicon ± amount`, SIUnit compound `UNIT(SEP UNIT){1,3}` and split-prefix
  `PREFIX \s+ UNIT`, BCP 47 `langtag ["-" script] ["-" region]…`, future RFC 3339
  `date [T time [zone]]`.
- **Contract:** `payload: expr` — a minimal expression tree (`seq`, `alt`, `opt`, `rep`,
  `label`) over child specs, evaluated left-to-right with span capture (the nom/winnow
  `IResult` model rendered in Python). `alt` is **ordered choice, documented as
  deterministic-first-branch-wins** (pest's discipline). Combinator `alt` at the *grammar*
  level still routes to distinct semantics, so cross-branch ambiguity stays observable
  downstream. A `predicate: Callable[[str, str], bool]` hook gates composition on lexicon
  data — Language `sl-nedis` is valid only with `sl` present (IANA `Prefix` constraint),
  expressible as data, not regex.
- **Scales to:** structure that would be an unreadable regex. `AmountComposer`'s hardcoded
  ` ?` separator and `[A-Z]{3}` fallback become parameters; `AmountComposer` remains as a
  documented alias — **no Money behavior change**.
- **Migration:** Money ×3, SIUnit compound + split-prefix, Language tag assembly.
- **Roadmap:** RFC 3339 composition; any spec with an ABNF.

### 9.5 `property` — open Unicode classes

- **When:** the spec defines an open character class — `\p{Sc}`-like currency symbols,
  `Script=Han`, `ID_Start` — where enumerating tokens is wrong.
- **Contract:** `payload: ranges` — **generated sorted-range tuples**
  (`tools/regenerate_unicode_property_data.py` emits from unicode.org
  `PropList.txt`/`Scripts.txt` into `grammar/data/unicode_ranges.py`, ICU `UnicodeSet`
  discipline); membership is `bisect`. No `\p{...}` needed, no `regex` dependency, no runtime
  Unicode DB.
- **Scales to:** any property that recurs. Land the kind when the same property recurs twice
  (SIUnit `µ/Ω/Å/°` is the first; Language `Script=Han` the second — the trigger).
- **Migration:** SIUnit special symbols; BIC `isascii` guard.
- **Roadmap:** Language script subtag validation; any open-class domain.

### 9.6 `candidates` — enumerated strict formats and registries

- **When:** the spec *enumerates exact formats* rather than one loose shape — Date's four
  formats, ISBN's two lexical lengths, IBAN's per-country `length + BBAN regex` rows (90),
  RFC 3339's 6+ variants, per-country postal/VAT masks.
- **Contract:** `payload: candidates: tuple[MatcherSpec, ...]` each with its own
  pattern/boundary/notation route, plus `strategy: "first" | "all"` — `first` wins per span;
  **`all` keeps ambiguity observable** (Date US vs European on `01/02/2026` must stay
  `AMBIGUOUS`). Per-candidate `target_semantics` is preserved: iso8601 candidates coalesce,
  us/european stay distinct. Registry form: `payload: registry: dict[str, MatcherSpec]`
  dispatched by prefix (`dict[CC, spec]` for IBAN) — O(1) after a two-character lookup,
  data-driven, not code-driven (libphonenumber's per-region metadata and pycountry's indexed
  lookup are the precedents).
- **Scales to:** registry-style capabilities without file proliferation. Date 4 files → 1;
  each candidate cites its authoritative section.
- **Migration:** Date (4→1); IBAN registry (future); ISBN lexical lengths.
- **Roadmap:** RFC 3339, full IBAN SWIFT registry, postal/VAT per-country.

### 9.7 `label` — optional label + value fusion

- **When:** an optional label glues to a value with a separator — `IBAN GB82…`, `BIC DEUTDEFF`,
  `ORCID 0000-…`, `ISSN 0317-8471`, `ISBN 978…`, future `doi:10.…`.
- **Contract:** `payload: labels: frozenset[str], separator: Pattern, glued_policy:
  "reject" | "allow"`. This **unifies the shipped inconsistency as data**: IBAN/BIC/ORCID use
  `[\s:-]+` never-zero-width (glued `IBANDE89…` → `MISSING` — `glued="reject"`), ISSN uses
  `[\s:-]*` (glued `ISSN03178471` matches — `glued="allow"`). Today these are per-file
  conventions tested only by corpus; under `label` they are declared, documented, and
  unit-tested.
- **Scales to:** every identifier family; the URI-prefix forms (`https://orcid.org/…`) fold
  in as `alt` branches.
- **Migration:** IBAN, BIC, ORCID, ISSN, ISBN.
- **Roadmap:** DOI/URN prefixes.

## 10. Boundaries as data

`BoundarySpec` is declarative, not lookarounds compiled into scanning patterns:

```python
@dataclass(frozen=True, slots=True)
class BoundarySpec:
    left: tuple[str, ...] | None     # char-class membership; None = no constraint
    right: tuple[str, ...] | None
    mode: Literal["zero_width", "consuming"] = "zero_width"
```

The kernel resolves boundaries as **checks at hit positions**
(`context.check(start, end, spec)` — O(hits)), never as lookarounds evaluated at scan
positions (O(positions)).

**Consuming-mode span rule (binding):** in a `consuming` spec (or a scanner anchored on a
consumed delimiter), the anchor characters are consumed by the scan *advance* — so the scan
does not re-enter them — but are **never part of the emitted span**. The span is the inner
match only. This is parity with today: `ipv6_token`'s
`(?:^|(?<=[\s,;([ ]))` / `(?:$|(?=[\s,;().\]]))` are zero-width in span terms, and IPv6 spans
exclude delimiters today — they must continue to.

The eleven shipped `BoundaryGuard` factories (`paxman/core/grammar/boundary.py`) become a
table of preset values:

| Today (factory / verbatim) | Guards (verbatim) | Kernel preset |
|---|---|---|
| `word_sign()` | `(?<![\w\-+\u2212])` / `(?![\w\-+\u2212])` | `WORD_SIGN` |
| `degree_word_sign()` | `(?<![°\w\-+\u2212/·⋅])` / `(?![\w\-+\u2212/·⋅])` — note: `°` constrains the left side only | `DEGREE_WORD_SIGN` |
| `digit()` | `(?<!\d)` / `(?!\d)` | `DIGIT` |
| `word_only()` | `(?<!\w)` / `(?!\w)` | `WORD` |
| `e164()` | `(?<![\w:.])` / — | `E164_LEFT` |
| `e164_00()` | `(?<![\w:.+])` / — | `E164_00_LEFT` |
| `scheme_char()` | `(?<![A-Za-z0-9+.\-])` / — | `SCHEME_CHAR_LEFT` |
| `phone_national()` | `(?<![\d+])(?<![\d+][\s.\-])(?<![\d+][\s.\-]\()(?<![\d+]\()` / `(?!\d)` | `PHONE_NATIONAL` (as data) |
| `isbn10_lead()` | `(?<!\d)(?<!\d[ -])` / — | `ISBN10_LEAD` |
| `isbn_trail()` | `(?<![\s:-])` / — | `ISBN_TRAIL_LEFT` (legacy; consumer audit at migration) |
| `ipv6_token()` | `(?:^|(?<=[\s,;([ ]))` / `(?:$|(?=[\s,;().\]]))` — delimiter-anchored, zero-width in span terms | `scanner` kind or `IPV6_TOKEN` preset (consuming advance, **inner span only**) |
| verbatim `\b` (Email, IPv4) | `\b` | `WORD` |

## 11. The cheap tier and the performance ladder

Each matcher declares **anchors** — necessary conditions evaluated before T1:

- **Literal anchor** — a required substring: passes iff `literal in text` (C-speed).
  E.g. `":"` for URL, `"@"` for email standard.
- **Class anchor** — a required character class: passes iff one pre-compiled
  `re.search(class_pattern, text)` succeeds. `HAS_DIGIT` ≡ `re.search(r"\d", text)` — used
  by Phone, Money, Date.
- **Key-set anchor** — a lexicon's first-character set as a `frozenset[str]`: passes iff at
  least one word span in `word_spans` begins with a character in the set.

The kernel evaluates anchors with C-speed primitives and **skips the matcher entirely when
they fail**. This is the Hyperscan literal-acceleration insight in stdlib form, and it is what
makes the 30-capability roadmap affordable: most matchers on most texts cost one failed
`find`.

| Tier | What | Cost model | Failure mode |
|---|---|---|---|
| T0 | anchor prefilter | O(1) C-speed per matcher | matcher skipped |
| T1 | shape match (regex / trie / scanner / combinator on substrate) | O(text) or O(words), bounded by pattern caps | no match |
| T2 | notation emit | O(hits) | — |
| T3 | rule validation (existing) | per-candidate | `INVALID` |

An optional `possible` predicate per spec (length/shape quick check) surfaces
libphonenumber-style reason codes as diagnostics **without changing `MISSING`/`INVALID`
semantics** — the two-tier validation lesson, applied to diagnostics only.

## 12. Assembly — the engine contract unchanged

`_dedup_spans` (within-grammar longer-wins), the total order `(start, end, active-set index,
grammar name)`, cross-grammar ambiguity preservation, `single_value` and
`MultipleMentionsError` (ADR-0004), semantics routing, `_filter_rules`, provenance
collection, and `format_value()` are all **unchanged**. The kernel replaces only the
*production* of recognitions. The engine-owned match loop:

```python
# Illustrative — engine-owned, capability-agnostic
def _run_matchers(text: str, compiled: Sequence[CompiledGrammar]) -> list[RecognitionMatch]:
    context = ScanContext.of(text)                    # L0: word spans; views lazy
    out: list[RecognitionMatch] = []
    for grammar in compiled:                          # active set, fixed order
        for matcher in grammar.matchers:
            if not matcher.anchors.pass_(text):       # T0 — skip, C-speed
                continue
            view = context.view(matcher.view)         # lazy materialization (D2)
            for span in matcher.match(view):          # T1 — kind-specific
                o_start, o_end = view.original_span(*span)   # offset translate (D3)
                out.append(RecognitionMatch(
                    notation=matcher.emit(span, context),    # T2
                    start=o_start, end=o_end, raw_text=text[o_start:o_end]))
        # engine validates raw_text == text[start:end] at the boundary (existing check)
    return out                                          # → existing assembly (L2)
```

No DAG, no threading — see §15.

## 13. Compiled capabilities at registry freeze

At `freeze_registry()`, every active grammar's `MatcherSpec` compiles to a `Matcher` (trie
built, regex compiled, scanner closures bound, boundary/anchor tables resolved, unsatisfied
`requires_features` matchers omitted), and the compiled set is hashed into the snapshot
identity:

- A compiled matcher is a **pure function of `(spec, snapshot)`** — the rustc query-system
  discipline; the determinism guarantee becomes structural rather than aspirational.
- The `VersionStamp` gains a **`recognition_revision`** derived from the compiled set. Any
  change to recognition behavior — including the intentional F1 change (Part VII) — coincides
  with a `recognition_revision` change, giving callers a same-snapshot diff signal for
  exactly which capabilities' recognition changed.
- Community `register_grammar` extensions compile through the same seam — the extension path
  and the shipped path share one mechanism.

## 14. Data rails — Snapshot, generate/verify CI, derived recognition keys

**Formalize the snapshot pattern** (generalizing `shared_data/currency_snapshot.json` +
`regenerate_currency_data.py` + consistency-test into a rule):

```python
@dataclass(frozen=True, slots=True)
class Snapshot:
    name: str          # "currency" | "iban_registry" | "iana_language" | "unicode_property" | …
    source_url: str    # authoritative fetch URL
    version: str       # "CLDR v47" | "SWIFT R100" | "IANA 2026-08-08" | …
    fetched_at: str    # ISO date
    data: object       # typed frozen payload
```

- **Every generated module embeds `Source / Version / SHA` in its header; CI regenerates and
  diffs — fail on drift** (ICU4X data-management discipline).
- **New snapshots on this rail:** IANA language subtag registry (full registry, ~8k entries),
  ISO 639-2/-3, CLDR aliases (Language per UTS #35 Annex C), Unicode property ranges, the
  SWIFT IBAN registry (90 country rows), and the English-frequency/suppression table if §16's
  optional flag ever ships.
- **Derived recognition keys:** grammar-side lexicons that are projections of rule-side
  authority data become **generated projections with a single source of truth** — Currency/
  Money symbols-words from the CLDR snapshot (already generated); BIC `_COUNTRY_CODES` from
  ISO 9362 rule data (currently hand-duplicated — F8); Language name keys from CLDR display
  names. The grammar/rule semantic boundary is untouched (keys stay key-only); the
  duplication class of bugs disappears.

## 15. Considered and deliberately simplified

Two directions raised during design are **rejected as spine elements** — recorded so the
next contributor does not re-litigate them:

1. **Per-capability recognition plan as a DAG with parallel execution.** Rejected: (a) the
   total order `(start, end, active-set index, grammar name)` already defines everything a
   DAG would order — a flat, ordered tuple of matcher specs per capability is sufficient;
   (b) CPython's GIL neutralizes thread-parallel pure-Python scanning (tries, scanners), so
   parallelism buys no wall-clock for CPU-bound matching while adding threading
   non-determinism risk; (c) every shipped capability's "plan" is linear. A flat ordered
   tuple is simpler to declare, audit, and freeze.
2. **Contract feature-flag redesign** (`active_recognizers`, `features: frozenset[str]`,
   `extra_recognizers` replacing `extra_grammars`). Rejected **for now**: the community
   extension seam is a public contract; renaming it is a breaking change with no current
   forcing capability. The grammar remains the contract-facing unit (`active_grammars`
   unchanged); `MatcherSpec.requires_features` (§8) mirrors `Rule.requires_features` so
   sub-grammar gating exists without a seam change.

**Adopted into the spine from the recognizer-taxonomy direction:** `candidates` and `label`
as named kinds (§9.6–9.7), normalizer provenance (§7), the typed-view discipline (D2), and
the streaming design (§17, deferred and non-binding).

**Adopted from the substrate direction:** the anchor prefilter tier (§11), the `scan()` API +
mention model (§16), freeze-time compilation + `recognition_revision` (§13), boundary checks
at hit positions (§10), and the measured trie/alternation auto-selection (§9.2).

## 16. The F1 fix — in-text matching, mention model, `scan()` API

- **In-text vocabulary matching is first-class.** Country `name_recognition` migrates from
  `WholeInputLookup` to a `lexicon` trie over multi-word keys (longest-match at word starts,
  spanning spaces, on the `AccentStrip` view): `"United States"` inside prose **is
  recognized**, with its true span.
- **The `to → TO` false positive is addressed by making the competition visible.** The
  engine now sees two mentions; `single_value` raises `MultipleMentionsError` on a contract
  that asks for one value (honest failure), and the batch API returns both mentions with
  spans for caller-side adjudication:

  ```python
  paxman.scan(text, contracts: Sequence[CapabilityContract]) -> ScanResult
  # ScanResult carries per-capability Mention records:
  #   (span, grammar, notation, resolved candidates when a single-mention contract applies)
  ```

  One substrate pass serves all capabilities. A `Mention` is a maximal cluster of
  recognitions under the existing total order + containment policy — the concept
  `_enforce_single_value_invariant` already gestures at, now typed and exposed. This turns
  `docs/recipes/segmentation.md` from a caller obligation into an API, fixes the F1 × F6
  interaction, and is the natural CLI surface (`paxman scan file.txt`).
- **Optional suppression data** (libphonenumber's date-guard pattern): a generated
  high-frequency-English-word table consulted by short-code matchers as a contract-gated
  `suppress_common_words` flag — **deferred and non-binding**; if it ever ships it is off by
  default, provenance-neutral (a suppressed recognition is simply not emitted; nothing
  validates to a wrong answer silently), and corpus-neutral.

**This is a deliberate, regression-locked behaviour change**: prose inputs that today
silently resolve to a wrong `SUCCESS` (e.g. `"Ship to United States please"` → `"TO"`)
will produce an honest error or `scan()` mentions. It is a change *from wrong to right*,
locked by a regression test at Phase 1, and called out in release notes, `docs/user/migration.md`,
and the Compatibility subsection (Part VII).

## 17. Designed-for, deferred: streaming (non-binding)

Streaming is **deferred and non-binding**. The design, for whenever a streaming caller
exists (an additive PR, no ADR change): `recognize_iter(chunks: Iterable[str]) →
Iterable[list[RecognitionMatch]]` with incremental view materialization, a per-matcher
bounded lookbehind window (Phone national ±20 chars; fixed-length shapes trivially
bounded), and a carry buffer of at most `max_pattern_len - 1` characters stitched across
chunk boundaries. The equivalence property — `recognize(text) ==
flatten(recognize_iter(chunk(text)))` for any chunking — joins the property catalogue
(Part V) **when streaming lands**; it is **not** a Phase 0–5 acceptance criterion.

The only guidance carried forward is soft: Phase 0 *should not foreclose* streaming (e.g.
matcher entry points take the `ScanContext`, not a precomputed structure that assumes
single-pass whole-text semantics). A guideline, not a gate.

## 18. What is explicitly not changing

- `Grammar`/`Rule` ABC surfaces (`name`, `semantics`, `single_value`, `recognize` signature),
  `RecognitionMatch`, `Notation`, `Provenance`, `Resolution`, `ExecutionResult`.
- Engine pipeline: `_recognize` → `_collect_candidates` → `_enforce_single_value_invariant`
  → `_filter_rules` → `_validate_affinity` → `format_value`.
- The `MISSING` / `INVALID` / `AMBIGUOUS` semantics, determinism-by-construction, zero
  runtime dependencies.
- `grammar/data` key-only vs `rules/data` authority boundary; capability isolation;
  `paxman.core` imports nothing from `paxman.*`; import-linter layers.
- Community extensions: the `extra_grammars` opt-in path is preserved **verbatim** — a
  `Grammar` subclass (README "Community Extensions" example) keeps working; shipped grammars
  adopting the kernel changes nothing for them. `extra_recognizers` is deferred (§15).
- The parity harness as the hard migration gate; `benchmarks/harness.py` stays
  informational.
- `Capability.get_grammars()` wiring — the engine still calls `grammar.recognize(text)`;
  kernel adoption is internal to the grammar.

---

# Part III — Capability Mapping

## Shipped: 15 capabilities, 36 grammars

| Capability (grammars) | Today | Kernel mapping | Why it's better |
|---|---|---|---|
| **BIC** (1) | `pre+regex`, `(?ai:…)` ASCII guard, 250-entry `_COUNTRY_CODES` frozenset duplicated from rules | `regex` + `label` (`{"BIC","SWIFT"}`, `[\s:-]+`, glued=reject); ASCII guard via `property`; country set becomes a **derived projection** | Label unified; F8 duplication killed |
| **Country** (4) | 3×`regex` (α2/α3/numeric) + `WholeInputLookup` (~600 union keys, `normalize_name` inline) | 3×`regex`; names → **`lexicon` trie on the `AccentStrip` view — F1 fixed**; `normalize_name` becomes a declared normalizer | Embedded names recognized; honest competition; ~600 keys on the O(text) representation |
| **Currency** (3) | `regex` (code) + `lexicon` alternation (67 symbols + 80 words, `word_sign`, IGNORECASE) | `regex` + `lexicon` **alternation** (below threshold) on the `CaseFold` view | Unchanged cost; case policy declarative, not a flag |
| **Date** (4) | 4×`regex` with `digit` guards; semantics coalesced for iso8601, distinct us/european | **`candidates`** (iso8601, slash_iso, us, european; `strategy="all"`) — per-candidate semantics routing preserved | 4 files → 1; `01/02/2026` stays `AMBIGUOUS` |
| **Email** (3) | 3×`regex`, verbatim `\b`; obfuscated = giant regex | `regex` ×3 with `BoundarySpec.WORD` + **anchor `"@"`**; obfuscated → `combinator` over the word lexicon (or scanner) | Uniform boundary; obfuscation gets a real home; anchor skips most text |
| **IBAN** (1) | `regex` + label lookarounds; paper groups absorbed | `regex` core + `label` (`glued=reject`); future **`candidates` registry `dict[CC, spec]`** for the SWIFT 90-country BBAN rows | Registry-ready; label unified |
| **IP** (2) | `regex` ×2; `ipv6_token` delimiter-anchored guard | v4 `regex`; v6 **`scanner`** (delimiter-anchored advance natural) + anchor `":"` | The "not interchangeable" guard special case disappears into the scanner kind |
| **ISBN** (2) | `regex` ×2; `isbn10_lead` lookahead | **`candidates`** (isbn13, isbn10) + `label`; `include_isbn10` gating stays contract-level | Candidates unify; gating unchanged |
| **ISSN** (1) | `regex`; `[\s:-]*` glued-allow | `regex` + `label` (`{"ISSN","ISSN-L"}`, `[\s:-]*`, **glued=allow**) | Glued policy becomes declared data, documented and unit-tested |
| **Language** (3) | **`_BCP47RegexStage` private fork** + ~160-line parser callback + 77 name keys + word-code lookup | **Flagship migration:** `scanner`/`combinator` for the BCP-47 subtag walk on the `SeparatorFold` view; `lexicon` **trie** for ISO 639-3 names (995 keys → trie tier); `regex` for short codes | Deletes the fork and the callback; scales to the full IANA registry (~8k) as **data** |
| **Money** (3) | `lexicon` + `AmountComposer` (hardcoded ` ?`, `[A-Z]{3}` fallback) | `lexicon` alternation + **`combinator(seq(alt(lex, amount)))`** — separator and order as data; `AmountComposer` = documented alias; anchor `HAS_DIGIT` | Composition generic; predicate hook for future prefix gating; **no behavior change** |
| **ORCID** (1) | `regex` + label `[\s:-]+` + URI form | `regex` + `label` (`glued=reject`) + URI-prefix as `alt` branch | Label unified |
| **Phone** (4) | `regex` + **`PostStage` LRU trim** (e164 15-digit window), 4-lookbehind chain (national), tel_uri, 00 | **`scanner`** (E.164 bounded digit window with separator-skipping state — no compact view, no LRU) + `regex` (tel_uri, 00) + `regex` with `PHONE_NATIONAL` BoundarySpec; anchor `HAS_DIGIT` | LRU trim and lookbehind chains deleted; bounded scan is linear and testable |
| **SIUnit** (3) | **giant alternations (820/650)** + compound regex + inline `split_*` classifiers in `notation_fn` | **`lexicon` trie** (measured 2.4–6.5× win) + `combinator` for compound + `property` for `µ/Ω/Å/°` + `SymbolFold` view; split-prefix = `alt(seq(prefix, unit))` | Largest scan cost drops (projected ~×4, Part IV); classifiers become declarations |
| **URL** (1) | loose `regex` + `PostStage` paren trim + bare-scheme drop | **`scanner`** (WHATWG-style state walk: scheme, depth-counter parens incl. nested `a(b(c)d)e`, bare-scheme drop) + **anchor `":"`**; `IDNAFold` view per D3 phasing | Depth-correct nesting; scanner unit-testable; anchor makes URL ~free on non-URL text |

## Future families — zero new machinery

| Future capability | Recognition family | Kernel kinds |
|---|---|---|
| Timezone abbreviations, MIME types, charsets, SPDX licenses, chemical elements, CSS colors, TLDs | pure vocabulary | `lexicon` trie — **data-only** |
| ISIN, CUSIP, FIGI, LEI, UUID, MAC, semver, credit card | fixed shape (+ label) | `regex` + `label` |
| RFC 3339 / ISO 8601 extended | enumerated strict formats | `candidates` + `combinator` |
| IBAN full registry (90 countries) | per-country registry | `candidates` registry dispatch |
| DOI / URN | balanced suffix | `scanner` |
| Postal codes / VAT IDs | per-country width/charset | `candidates` + `lexicon` (CC trie) + `combinator` |
| Language at full IANA scale (~8k subtags) | vocabulary + ABNF + prefix gating | `lexicon` trie + `combinator` (predicate) + views |

---

# Part IV — Performance Model

## Measured (pre-kernel tree, 2026-08-24)

| Metric | Value |
|---|---|
| Recognition-only cost, 68-char input, all 15 capabilities | ~1.30 ms |
| Dominant per-capability terms | SIUnit 376 µs (3 grammars), Language 175 µs, Country 142 µs, URL 11 µs |
| Whole-pipeline p50 per capability (`benchmarks/baseline.json`) | 0.09–0.24 ms |
| Trie vs regex alternation (SIUnit 650/820-token tables) | trie 2.4–6.5× faster across 50-char / 430-char / 2.2 KB corpora (§2 F3 table) |
| Build cost at 650 tokens | trie 3.1 ms vs regex compile 3.8 ms — parity |

*Method: CPython via `uv run`, single process, `time.perf_counter`, 200–500 iterations,
min-of-mean; the trie's matches were cross-checked byte-equal against the alternation's. The
trie is a plain word-anchored dict-of-dicts without failure links — the numbers are a floor,
not a ceiling.*

## Projected (kernel — confirmed per phase, never a gate)

| Expectation | Basis | Confirmed at |
|---|---|---|
| SIUnit scan cost ~×4 lower | the measured 2.4–6.5× trie/alternation ratio at SIUnit's own token scale | Phase 1 |
| Per-matcher cost on non-matching text ≈ one failed C-speed `find` | T0 anchor design (§11) | Phase 0/1 |
| The shared `\w+` word-span pass is negligible vs any grammar scan | single C-level `finditer` | Phase 0 (measured at landing) |
| Recognition cost independent of lexicon size at Language scale (~15k keys) | O(text) word-anchored trie | Language migration |

**Projections are not gates.** `benchmarks/` stays informational (a hard p50 gate would be a
separate ADR/CI change, unchanged from ADR-0008). The benchmark suite gains a
recognition-only scenario family (scan cost per capability at 64 B / 2 KB / 16 KB) and tracks
the trie/alternation crossover size to keep the ~500-token auto-selection honest (§9.2).

## Per-kind complexity

| Kind | Complexity | Constant factor | When it wins |
|---|---|---|---|
| `regex` | O(text) per pattern via C engine | very low | Single pure shape (BIC, ISBN, ISIN) |
| `lexicon` (alternation) | O(text × alternatives) — bounded, small P | low (C engine) | Small vocabularies (≤ ~500 tokens): Currency 67/80 |
| `lexicon` (trie) | O(text) — word-anchored | low-medium pure Python; measured 2.4–6.5× vs alternation at 650–820 tokens, build parity | Large vocabularies: SIUnit 820/650, Country ~600, Language 995→15k |
| `scanner` | O(text), one pass | very low (single loop, no regex) | Delimiting/bounding (URL, Phone E.164, DOI) |
| `combinator` | O(text) with bounded per-branch backtracking | medium (function-call per node) | Compositional/recursive shapes (BCP 47, RFC 3339, Money) |
| `property` | O(text) + bisect per char | low | Open Unicode classes (SIUnit specials, Han) |
| `candidates` | Σ O(text) over candidates, O(1) registry prefix dispatch | linear in candidate count | Enumerated formats / registries (Date, IBAN) |

---

# Part V — Verification

**Strata:**

1. **Matcher unit tests** — per kind, in isolation (`text → list[RecognitionMatch]`, no
   engine): trie-vs-alternation byte-parity on golden corpora; scanner depth corpora (nested
   parens); combinator ordered-choice tables; label glued-policy tables; boundary presets
   (including the consuming-mode inner-span rule, §10).
2. **Kernel-vs-legacy parity per grammar** — extends `tests/property/test_grammar_stage_parity.py`
   (the ADR-0008 hard gate), sharded per kind:
   `test_lexicon_parity.py`, `test_scanner_parity.py`, `test_view_parity.py`,
   `test_combinator_parity.py`. **No new kind lands without its shard green.**
3. **Substrate equivalence properties** (Hypothesis, per shipped grammar): kernel recognition
   equals direct-scan recognition on generated inputs; **`raw_text == text[start:end]`** for
   every returned match across random text; **longest-first determinism** — trie and
   alternation agree on the longest match at each position; **`MISSING` vs `INVALID`
   non-collapse** — no matcher rejects a span a rule would accept (fuzz with valid + invalid
   probes); **view offset round-trip** — for every length-changing view,
   `original_span` is the inverse of translation per the D3 invariant.
4. **Drift gates** — `tests/unit/test_<name>_snapshot_parity.py` per snapshot (currency
   exists; add `iban_registry`, `iana_language`, `unicode_property`); CI regenerate-and-diff
   on generated modules (§14).
5. **Benchmarks** — informational; tracks the trie/alternation crossover size (§9.2) and the
   recognition-only scenario family (Part IV).

**Abort criterion (inherited from ADR-0008, binding):** if a grammar cannot be made
byte-identical without changing semantics, the migration PR is aborted and the grammar stays
on the legacy path until the kernel contract is extended — **no silent divergence**.
`Country name_recognition` F1 migration is exempt from the byte-identical gate; it is gated
by the honest-behavior regression test (`"Ship to United States please"` → `MultipleMentionsError` with competing mentions).

---

# Part VI — Migration — phased, parity-gated, reversible

Each phase is an independent PR series, capability-at-a-time, with the full pre-PR gate
(`ruff check && ruff format --check && pyright && import-linter lint && pytest`) plus the
applicable parity shard.

- **Phase 0 — Foundation (no behaviour change).** Land `ScanContext` (word spans + lazy
  views), `MatcherSpec`/compilation seam, `BoundarySpec` presets, the `Normalizer` set with
  provenance, and the engine-owned match loop **behind the existing `PipelineGrammar`** —
  compat shim: a grammar may declare `matchers` and delegate, or keep its stage loop. Parity
  shards land empty-and-green. The word-span pass cost is measured and recorded here (Part
  IV). Full CI gate green.
- **Phase 1 — The measured wins.** `lexicon` trie representation (size-gated); migrate
  Country `name_recognition` to the in-text trie — **F1 lands**, with the `"Ship to United
  States please"` case as a regression test asserting the new honest behaviour (exempt from the
  byte-identical gate per Part V; this is the intentionally breaking change) — and SIUnit
  symbol/name to the trie (largest scan cost; projected ~×4 per Part IV).
- **Phase 2 — Shape freedom.** `scanner` + `combinator` kinds; migrate URL paren-balance and
  Phone E.164 from `PostStage` (retiring `PostStage`), then **Language — deleting
  `_BCP47RegexStage` and the 160-line callback (the flagship readability win)**. General
  offset maps land here if URL's `IDNAFold` view needs them (D3).
- **Phase 3 — Registries and labels.** `candidates` (Date 4→1; IBAN registry when the SWIFT
  snapshot lands) and `label` (BIC/IBAN/ORCID/ISSN/ISBN glued-label unification).
  `AmountComposer` becomes an alias over `combinator`. Retire `PipelineGrammar`'s linear
  fields once all shipped grammars have a kernel declaration.
- **Phase 4 — Surface.** Batch `scan()` API + `Mention` model + CLI; freeze-time compilation
  and `recognition_revision`.
- **Phase 5 — Data rails.** snapshot/regenerate/verify CI for the new tables; derived
  recognition keys (BIC country set, Language names); the Unicode-property generator.

**Risks and mitigations:**

| Risk | Mitigation |
|---|---|
| Trie/alternation behavioral parity | Byte-identical gate + golden corpora; size threshold keeps small lexicons on the C engine |
| Scanner correctness | Each migrated scanner carries its legacy corpus forward; nested-paren and 15-digit-window corpora added |
| View offset bugs | Length-preserving-first (D3); identity maps cost nothing; `raw_text == text[start:end]` validated at the boundary for every match |
| Performance regression during migration | Recognition-only benchmarks per phase (informational); T0 anchors expected to more than compensate |
| Behavior change (F1) breaking consumers | Regression-locked from Phase 1; BREAKING CHANGE release note + `docs/user/migration.md` entry (Part VII); `scan()` ships as the constructive path |
| Over-generalization | `candidates`/`label`/`property` are wrappers over `combinator`/`regex` — ergonomics, not machinery |

The pending normalized-view-stage work is **re-based** onto Phase 0/1: its view threading
becomes the `ScanContext` view + `view` selector; its parity obligations carry over
unchanged.

---

# Part VII — Consequences

## Compatibility — intentional breaking change (F1)

`canonicalize()` observable behavior changes for exactly one input class: text in which a
whole-input vocabulary match was previously invisible and a short code was validated in its
place. Every other input is byte-identical under the parity gate.

| Input class | Before (ADR-0008 pipeline) | After (kernel) |
|---|---|---|
| Exact name, whole input (`"United States"`) | `SUCCESS "US"` | `SUCCESS "US"` — unchanged |
| Name embedded in prose (`"Ship to United States please"`) | `SUCCESS "TO"` — **wrong** (Tonga) | `MultipleMentionsError` under a `single_value` contract; both mentions (span, grammar, notation) via `paxman.scan()` |
| Short code as ordinary word (`"to"` in prose) | recognized and validated as alpha-2 — silent win | recognized; competes with the name mention — no silent win |
| All other inputs | — | byte-identical (parity gate) |

- **Semver guidance:** ship in a **minor bump 0.1.0 → 0.2.0** (pre-1.0 semver). Release
  notes carry a BREAKING CHANGE entry; `docs/user/migration.md` gains the table above and
  the migration snippet below.
- **Migration snippet:**

  ```python
  # Exact value — unchanged:
  paxman.canonicalize("United States", contract)            # SUCCESS "US"

  # Prose with embedded values — the new honest paths:
  try:
      result = paxman.canonicalize("Ship to United States please", contract)
  except MultipleMentionsError:
      mentions = paxman.scan("Ship to United States please", [contract])
      # → [Mention(span=(9, 22), grammar="name_recognition", …),
      #    Mention(span=(5, 7),  grammar="alpha2_recognition", …)]
  # Or segment first — docs/recipes/segmentation.md remains valid.
  ```

- **Determinism signal:** the F1 migration changes the compiled matcher set, so
  `recognition_revision` (§13) changes with it — callers comparing snapshots can see exactly
  which capabilities' recognition changed.

## Positive

- **A stable spine.** Recognition stops growing new machinery per capability. The next 30+
  capabilities are data declarations over seven existing kinds — the one-time investment that
  makes every future undertaking easier (the explicit rationale for the harder migration).
- **Correctness.** The F1 class of silent wrong answers is fixed and made honest; `scan()`
  turns multi-entity extraction into an API.
- **Developer experience.** A new grammar is ~15 lines of declaration + a token table or a
  testable scan function — not a regex script or a private stage fork. `candidates`/`label`/
  `property` are named, documented choices; `HOW_TO_ADD_NEW_CAPABILITY.md` §4 remains the
  chooser, now pointing at real kinds.
- **Drift minimized.** Snapshot→generate→verify CI with embedded `Source/Version/SHA`;
  derived recognition keys kill the F8 duplication class; freeze-time compilation makes
  determinism structural (`recognition_revision`).
- **Performance.** Shared substrate (one word-span pass), trie for large lexicons, T0 anchors
  — recognition cost per capability becomes independent of lexicon size and near-zero on
  non-matching text.
- **Fewer concepts.** Seven proposed stage types collapse to `{view × kind × combinator}`;
  tests stratify into per-kind shards instead of re-covering the same corpora.

## Negative

- **Migration cost.** Every one of the 36 grammars is touched; each migration PR must prove
  byte-identical `RecognitionMatch` output. This is the accepted one-time exercise.
- **Behaviour change (intentional, F1).** Prose inputs that today silently resolve to a wrong
  `SUCCESS` become honest errors or `scan()` mentions — see Compatibility above.
- **Offset-map complexity.** Length-changing views (IDNA, separator strip) need offset maps.
  Mitigated by D3 phasing (length-preserving first; general maps only when a migrated grammar
  needs them) and the boundary validation on every emitted span.

## Risks

See the table in Part VI.

---

# Part VIII — Comparative Matrix

| Dimension | Today (ADR-0008 pipeline) | After (Recognition Kernel) |
|---|---|---|
| Order | Fixed linear `pre→regex→lexicon→composer→post`, optional slots | Flat ordered tuple of matcher specs per grammar; engine-owned loop |
| Normalization | `StandardPre(empty_guard)`; `scratch` dead; per-file hand-rolled | Lazy `ScanContext` views + `NormalizerSequence` with offset discipline and citeable declaration-level provenance |
| Large lexicon | `re.escape`-joined alternation — O(positions × alternatives) | Size-gated: alternation ≤ ~500; **word-anchored trie O(text)** above — byte-identical parity |
| Embedded values (F1) | Invisible — whole-input lookup only; `to → Tonga` | **Recognized in-text**; honest `MultipleMentionsError` / `scan()` mentions |
| Balanced/delimited | `RegexStage` loose shape + `PostStage` trim loops | `scanner` state machine, depth-aware, no LRU |
| Recursive syntax | Giant regex or 160-line callback (`_BCP47RegexStage` fork) | `combinator` expression tree (IResult model) |
| Enumerated variants | One file per variant (Date ×4) | `candidates` / registry dispatch — one grammar, per-candidate provenance |
| Composition | `AmountComposer` single-separator, `[A-Z]{3}` fallback | `combinator(left, right, separator, order, predicate)` — generic |
| Boundary | 11 `BoundaryGuard` factories + verbatim `\b` + delimiter-anchored special cases | `BoundarySpec` data, checked at hit positions; presets table; consuming rule = inner span only |
| Labels | Per-file `[\s:-]+` vs `[\s:-]*` convention | `label` kind with declared `glued_policy` |
| Cost on non-matching text | Full `finditer` per grammar | **T0 anchor skip** — one failed C-speed find per matcher |
| Data pipeline | Ad-hoc generated modules; hand-duplicated keys | `Snapshot` + regenerate/verify CI; derived recognition keys |
| Determinism record | `VersionStamp` (library version) | + `recognition_revision` (hash of compiled matcher set) |
| Multi-entity input | Caller-side splitting (recipe doc) | `scan()` API + `Mention` model |
| Verification | One parity gate + informational bench | Parity shards per kind + property catalogue + drift gates + informational bench |

---

# Part IX — Alternatives Considered

1. **Status quo (ADR-0008 pipeline, 36 working grammars).** Rejected — duplication is
   measured (F2/F3/F4/F5/F8), the roadmap's shapes (Language at IANA scale, registries,
   balanced delimiters) don't fit the five slots, and F1 is a correctness defect.
2. **The prior ADR-0009 draft: seven more stage types inside the fixed pipeline.**
   Rejected — treats each symptom separately; keeps per-grammar independent scanning (F2
   unfixed), whole-input gating (F1 unfixed), boundary lookarounds (F5 unfixed); adds seven
   concepts instead of collapsing to three axes; its pure-Python-trie pessimism is
   contradicted by measurement (F3).
3. **The recognizer-taxonomy direction as the spine** (six recognizer types, DAG plans,
   parallel execution, contract-seam redesign). Rejected as the spine — more distinct
   abstractions, Country kept whole-input-gated (F1 unfixed), no anchor tier, GIL-neutral
   parallelism, breaking the community seam. Its best ideas are adopted as kinds/data
   (§§7, 9.6, 9.7, 17).
4. **External engine dependency (RE2, Hyperscan, Rust `regex`, `pyahocorasick`).**
   Rejected — compiled extensions violate zero-runtime-deps; leftmost-winner semantics
   collapse ambiguity; the architectural lesson (literal prefilter, compile-the-union) is
   adopted in stdlib form instead.
5. **ML/NER.** Rejected — non-deterministic, authority-less; "Berlin" as place vs surname is
   not a Paxman question.
6. **Fuzzy/approximate matching.** Rejected — no ISO clause authorizes typo tolerance;
   provenance degrades; callers needing typo-tolerant search should index canonical forms.
7. **Checksum-fused recognition.** Rejected — collapses `MISSING` vs `INVALID`; duplicates
   authority tables into grammars; checks stay in `Rule.matches()`.
8. **Adopting spaCy/pyparsing/Lark/UIMA wholesale.** Rejected — wrong shape (whole-input
   parsers, ML legs, framework weight) for a stdlib-only span scanner; the *patterns* are
   borrowed, the machinery is not.

---

# Part X — Open Questions

1. **`scan()` API shape** — exact `ScanResult`/`Mention` field set and its interaction with
   `MultipleMentionsError` guidance; resolved at Phase 4. The F1 regression test (Phase 1)
   locks the *behaviour* before the API lands.
2. **Suppression data** — whether `suppress_common_words` ever ships; if so, off by default
   and corpus-neutral (§16 — deferred, non-binding).
3. **Trie threshold drift** — the ~500-token crossover is measured on current hardware and
   tables; the benchmark tracks it (informational). Adjusting the constant is a patch, not
   an ADR.
4. **`extra_recognizers`** — deferred until a community capability needs sub-grammar
   extension; the seam design must not break `extra_grammars` semantics.
5. **Streaming timing** — `recognize_iter` lands when a streaming caller exists (§17,
   non-binding); only the soft "don't foreclose" guideline applies before then.
6. **Benchmark gating** — stays informational; a hard p50 gate would be a separate
   ADR/CI change (unchanged from ADR-0008).

---

## References

- **Superseded:** ADR-0008 (Staged Recognition Pipeline — now Obsolete); the prior
  ADR-0009 draft ("Staged Pipeline Extensions" — withdrawn before acceptance; preserved in
  git history).
- **Authoritative in-repo:** `ARCHITECTURE.md` (Recognition Pipeline Contract; determinism;
  provenance-first; layer discipline); `HOW_TO_ADD_NEW_CAPABILITY.md` §4 (extended
  strategies table); `HOW_TO_ADD_NEW_GRAMMAR.md` (`single_value`, boundary conventions);
  `README.md` (capability/grammar table, community-extension seam); `CONTEXT.md`;
  `docs/recipes/segmentation.md`; `docs/user/migration.md`; `benchmarks/baseline.json` +
  `benchmarks/README.md` (informational benchmark policy);
  `paxman/core/grammar/{pipeline,stages,boundary,lexicon,composer}.py`;
  `paxman/core/domain.py`; `paxman/engine/orchestrator.py`.
- **ADRs retained:** ADR-0001 (pipeline seam), ADR-0003 (semantic affinity), ADR-0004
  (single-value invariant), ADR-0005/0006 (SIUnit flags), ADR-0007 (contract surface).
- **Primary external sources:** libphonenumber `PhoneNumberMatcher`/`PhoneNumberUtil`/
  metadata XML (bounded patterns, suppression data, two-tier validation, advance discipline);
  Hyperscan (NSDI'19) / RE2 / Rust `regex-automata` (literal prefilter; rejected as deps);
  Aho–Corasick 1975 / FlashText (word-anchored trie, ~500 crossover); UIMA OASIS spec /
  GATE / spaCy `PhraseMatcher`+`EntityRuler` / Lucene analysis (substrate, standoff,
  offset-correctness, declared overlap policy); ICU/ICU4X (`UnicodeSet`,
  `LocaleCanonicalizer` UTS #35 Annex C, data management); WHATWG URL Standard (non-fatal
  errors); pyparsing `scan_string` / Lark `scan` / nom / winnow / pest (span-preserving
  combinators); Hugging Face `tokenizers` (normalizer pipeline with offset maps); rustc
  query system (memoized pure derivations); pycountry (indexed registry lookup);
  python-stdnum / dateparser / chrono / dateutil (convention vs framework; parser→refiner).
