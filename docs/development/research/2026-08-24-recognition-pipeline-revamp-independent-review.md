# Recognition Pipeline Revamp — Independent Architecture Review (From-Scratch Proposal)

**Date:** 2026-08-24
**Reviewer:** Independent architecture review (first-time repo observer)
**Scope:** Full rethink of Paxman's recognition subsystem. No code was modified. All ADRs concerning the current `paxman/core/grammar/` staged pipeline (notably ADR-0008 `pre→regex→lexicon→composer→post`) were **deliberately disregarded** per brief, to avoid anchoring. Current source was read at `main` @ `0.1.0` (15 capabilities, 33 grammars, `paxman/core/domain.py`, `paxman/core/grammar/{pipeline,stages,boundary,lexicon,composer}.py`, `paxman/engine/orchestrator.py`, `paxman/capabilities/*/grammar/**`, `HOW_TO_ADD_NEW_CAPABILITY.md` §4 extended-strategy table, `ARCHITECTURE.md`, all `docs/development/research/*.md` for context only — not as constraints).
**Evidence basis:** Source audit at `main` + primary documentation + external ecosystem survey (see §2). Methods cited are production-proven in their home ecosystems, not speculative.
**Conventions grounding this report:** None of the staged-pipeline conventions are assumed. Only the project-wide invariants that survive any revamp are retained: determinism (same input + contract + snapshot → same output), provenance-first (`Provenance` attached to every `SUCCESS`), `RecognitionMatch[start,end,raw_text]` span-bearing contract, `format_value()` as sole presentation seam, zero runtime network/ML, layer discipline (`core` imports nothing from `capabilities`), frozen/slots domain objects, and import-linter leaf.

---

## Executive Summary

Paxman's value proposition — *ambiguous human input → what authoritative specs say it means, with full provenance* — lives or dies on **recognition**. Today's shipped pipeline is a linear, fixed-order `PipelineGrammar` walking `pre → regex → lexicon → composer → post` with a `PipelineState{text, matches, scratch}` threaded through `Stage.run()`. It ships all 15 capabilities correctly and has a byte-identical parity harness. It is also, by construction, the ceiling the owner already feels:

* **Large-lexicon matching is forced through `re.escape`-joined alternations.** `SIUnit` alone compiles ~820 + ~650 tokens into two giant regexes; `Country` unions ~600 keys via `WholeInputLookup`; `Currency`/`Money` carry 67 symbol + ~80 word alternations. The `HOW_TO` table itself concedes Aho–Corasick when the alternation "becomes slow or unwieldy" — but there is no automaton to reach for.
* **Regex is the only first-class shape language.** Delimiter-balanced (`URL` parens), length-bounded (`Phone` E.164 15-digit window), label-glued (`BIC`/`IBAN`/`ORCID` `[\s:-]+` vs `[\s:-]*`), compositional (`Money` `lex ? amount | amount ? lex`, `SIUnit` `UNIT(SEP UNIT){1,3}`), and Unicode-property (`\p{Sc}`, `Script=Han`) problems are all shoehorned into either a `RegexStage` pattern or a `PostStage` trim closure — the latter being a hand-rolled scanner disguised as post-processing.
* **The pipeline order is rigid and the normalized-view hook is dead.** `StandardPre` is today just `empty_guard`; `scratch["normalized"]` is never populated. Every capability hand-rolls its own normalization (`normalize_name`, `strip_separators`, `²→2`, `µ→μ`, `en_US→en-US`, UTS #46 `IDNA_STATUS/MAPPED`, CLDR lower-folding) inside `notation_fn` or a closure, duplicating logic and breaking auditability.
* **Composition is a single hardcoded composer.** `AmountComposer` assumes `[A-Z]{3}` lexicon, one optional ASCII space, and `(?:…)` non-capturing groups. `SIUnit` compound and any future `Language` `Prefix`-constrained composition (`sl-nedis` valid only if `sl` present) cannot be expressed without a new bespoke regex.
* **`BoundaryGuard` is an 11-factory family with no closure.** Each capability invents its own lookbehind/lookahead pair (`word_sign`, `degree_word_sign`, `digit`, `scheme_char`, `phone_national` 4-chain, `ipv6_token` consuming, `isbn10_lead`, …). Email/IPv4 still use verbatim `\b`. There is no uniform boundary declaration.

**This review proposes a from-scratch replacement** — not an incremental stage addition — built around three ideas borrowed from systems that already operate at 10× Paxman's scale:

1. **A uniform `Recognizer` protocol with explicit `InputView` threading** (inspired by Hugging Face `tokenizers`' `Normalization → Pre-tokenization → Model → Post-processing` pipeline and by Hyperscan's two-stage decomposition of regexes into string prefilter + NFA).
2. **A pluggable strategy kernel** where each recognition *strategy* is a first-class `Recognizer` — `Shape` (regex), `Lexicon` (Trie/Aho–Corasick), `Scanner` (character state machine), `Grammar` (PEG/combinator), `Property` (generated Unicode ranges), `Candidate` (enumerated strict formats) — selectable per grammar, composable via a generic `Composer`, and runnable in parallel where dependencies allow (inspired by spaCy's `Matcher` + `PhraseMatcher` duality, `nom`/`pest` combinator vs PEG tradeoffs, and `pyahocorasick`'s `O(N+L+Z)` guarantee).
3. **A recognition *plan* per capability** — a small DAG, not a fixed linear order — declared in the capability's `grammar/` module and executed by a new `RecognitionEngine` that owns view materialization, offset translation, dedup, and ordering. The engine, not each grammar file, enforces `raw_text == text[start:end]` and `single_value` invariants.

The proposal keeps every invariant that makes Paxman trustworthy (determinism, provenance, frozen domain objects, `format_value` seam) and removes the constraints the owner flagged, while adding explicit hooks for the next 100 capabilities (Language BCP 47 ABNF + 15k IANA subtag lexicon, IBAN per-country BBAN registry, ISIN/CUSIP/LEI/FIGI families, DOI/URN balancing, RFC 3339 timestamps, per-country postal/VAT registries).

**If the team prefers one sentence:** replace *one linear pipeline with five optional stage slots* by *a toolkit of six interchangeable recognizers sharing typed input views and a composer, wired per-capability as a tiny DAG*.

The report then argues that the revamp is incomplete without **four changes outside the recognition layer** (§6): engine streaming/incremental support, contract feature-flag redesign, generated-data snapshot generalization, and a parity-plus-property verification harness.

All rejected alternatives (ML/NER, fuzzy/Levenshtein, checksum-fused recognition) are documented so the next contributor does not reopen them.

---

## Table of Contents

1. [Methodology](#1-methodology)
2. [External Survey — How Others Solve the Same Problem](#2-external-survey--how-others-solve-the-same-problem)
3. [Autopsy of the Current Pipeline](#3-autopsy-of-the-current-pipeline)
4. [First Principles — What Recognition Must and Must Not Do](#4-first-principles--what-recognition-must-and-must-not-do)
5. [Proposed Architecture — Universal Pluggable Recognizer](#5-proposed-architecture--universal-pluggable-recognizer)
6. [Beyond Recognition — Four Required Companion Changes](#6-beyond-recognition--four-required-companion-changes)
7. [Capability Mapping — Shipped and Planned](#7-capability-mapping--shipped-and-planned)
8. [Phased Adoption — From Current to New Without Forking](#8-phased-adoption--from-current-to-new-without-forking)
9. [Verification & Performance Model](#9-verification--performance-model)
10. [Rejected Alternatives](#10-rejected-alternatives)
11. [Comparative Matrix](#11-comparative-matrix)
12. [Appendix — Sketches and References](#12-appendix--sketches-and-references)

---

## 1. Methodology

* **Read the repo cold.** No prior context, no ADR deference. Every claim about current behaviour was verified against `main` source, not secondary docs. `paxman/core/grammar/pipeline.py` (28 LOC `PipelineGrammar`), `paxman/core/grammar/stages.py` (180 LOC, five stage types), `paxman/core/domain.py` (`RecognitionMatch`, `Grammar`, `RuleStrategy`), `paxman/engine/orchestrator.py` (`run_capability`, `_dedup_spans`, `_filter_rules`, `format_value` call site) were read verbatim. `paxman/capabilities/*/grammar/**` (33 files) were sampled across the four archetypes: pure shape (`IBAN`, `BIC`, `ISBN`), lexicon-driven (`Currency`, `SIUnit`), whole-input (`Country` name), compositional (`Money`, `SIUnit` compound), post-trim (`Phone` E.164, `URL`).
* **Surveyed production analogues outside Python.** Selection criterion: systems that solve *deterministic span-bearing extraction with provenance or authority* at scale, not generic NLP. Each analogue was probed for its recognition strategy, scalability claim, and failure mode. Web searches and primary docs were fetched 2026-08-24 (see references).
* **Tested for scalability break points.** Asked: what happens at 10× capabilities, 10× lexicon size, 10× input length, and with a streaming caller? Where does the fixed-order pipeline force duplication or an unreadable regex?
* **No code was written or modified.** All sketches are illustrative; field names and module paths are proposals, not patches.

---

## 2. External Survey — How Others Solve the Same Problem

The survey deliberately spans regex engines, lexicon engines, tokenizer pipelines, and parser families. The pattern that emerges is consistent: **no successful system at scale uses one recognition language**. They all compose a small set of specialized matchers behind a uniform span contract.

### 2.1 Regex at Scale — RE2, Hyperscan, and the Prefilter Lesson

* **RE2 (Google)** guarantees linear-time matching via DFA/NFA simulation, trading backtracking features (no backrefs, no lookaround beyond fixed-width) for ReDoS immunity. Its `RE2::Set` API compiles *many* patterns into one automaton for multi-pattern matching — but memory explodes past ~30 patterns (peaks near 2 GB) and the DFA cache regresses. Paxman's `re.compile(join(escaped_tokens))` is RE2::Set's naive analogue without the DFA.
* **Hyperscan (Intel, 5k+ stars, NSDI'19)** solves the same problem by **decomposing each regex into literal string fragments + NFA islands**, running a SIMD-accelerated multi-string matcher first (Aho–Corasick-family `FDR` engine), and only entering NFA on candidate regions. On Snort's 1,300 Talos regexes, Hyperscan is 13.5× faster than `RE2::Set` and 183× faster than PCRE2 in multi-pattern mode; on Suricata's 2,800 `ET-Open` rules the speedup is 8.4× over `RE2::Set`. The lesson for Paxman is architectural, not "adopt Hyperscan": **split large alternations into a cheap literal prefilter plus precise validation**, rather than one giant alternation that pays NFA cost everywhere.
* **Takeaway for Paxman:** For `SIUnit` 820 + 650 tokens and future `Language` 15k IANA subtags, the current giant alternation is the worst point on the tradeoff curve. Even a pure-Python `Trie` scan is a 10–30× improvement in the literature for large lexicons; the win is not raw throughput but *decomposition* — longest-first Trie scan in `O(N+Z)` plus `BoundaryGuard` gate, with zero regex backtracking.

### 2.2 Large-Lexicon Matching — Aho–Corasick and the Trie Family

* **Aho–Corasick (1975)** builds a Trie with failure links that scans text in `O(N + L + Z)` where `N` is text length, `L` total pattern characters, `Z` matches — independent of dictionary size. The Toptal and CP-Algorithms summaries benchmark it at ~8 ms/MB vs 12–15 ms/MB for `KMP`/`Boyer-Moore` on 100 MB corpora; the CHPDA paper (VectorEdge, 2025) ranks it the optimal exact-match choice for PII/PHI glossary scanning among regex vs Aho–Corasick vs AI-NER hybrids, precisely because it scales to "many patterns against one blob of text".
* **Banlex #3 (2026)**, a recent lexicon library, proposes exactly the threshold-gated backend Paxman needs: *use simple matcher below a phrase-count threshold, auto-switch to Aho–Corasick above it*, keeping small-lexicon paths dependency-light.
* **Genomic k-mer detection (2025)** papers show the same pattern at extreme scale (`10^8` genome length, `10^4` patterns): classical Aho–Corasick is the baseline quantum-matching papers compete against, with `O(S·L)` gate-cost vs `O(log S)` QRAM access — confirming that Trie scanning is the standard answer for "many literals in one pass" until hardware changes.
* **Takeaway for Paxman:** The `HOW_TO` table's "Multi-key automaton (Aho–Corasick) when `(key1|key2|…)` becomes slow or unwieldy" is correct but undersells it. The threshold is not "slow" but *architectural*: any lexicon > ~200 tokens (today: SIUnit symbols 820, SIUnit names 650, Country union 600, Currency 67 — borderline) should default to Trie scan, not alternation, to preserve `O(N)` text scan and longest-first determinism. The `LONGEST_FIRST, QUALIFIED_FIRST` ordering in `LexiconAlternation` maps directly to "deepest Trie leaf wins, tie → lex order".

### 2.3 Tokenizer Pipelines — Hugging Face `tokenizers` as a Reference Architecture

Hugging Face `tokenizers` (Rust core, Python bindings) processes every call through four explicit stages: **`Normalization → Pre-tokenization → Model → Post-processing`**, each with a typed interface (`Normalizer`, `PreTokenizer`, `Model`, `Processor`). Key properties Paxman should steal:

* **Normalization is a first-class, composable stage** (`Sequence([NFD(), StripAccents(), Lowercase()])`), not a hand-rolled helper inside each model's `encode`. It produces a `NormalizedString` that tracks original→normalized offset maps so spans remain relative to original input — exactly the `scratch["normalized"] + offsets` problem Paxman's `PipelineState.scratch` was meant to solve but never does.
* **Pre-tokenization is pluggable** (`Whitespace()`, `Digits(individual_digits=True)`, `Sequence([...])`) and returns `[(token, (start,end))]` — the `RecognitionMatch` analogue — with zero-copy slices.
* **Model and post-processing are separate concerns** — the model does vocabulary lookup (lexicon), post-processing adds `[CLS]/[SEP]` templates (presentation). Paxman's `format_value()` already separates presentation, but recognition-side formatting leaks into `notation_fn` today.
* **Takeaway:** Paxman's `pre → regex → lexicon → composer → post` is a poor man's version of the same idea, but with fixed order, untyped `scratch: dict[str, object]`, and no offset map. Adopt the tokenizer pattern literally: a typed `InputView` (original text + zero-or-more materialized normalized views with offset maps), a `Normalizer` stage that populates views, and recognizers that declare which view they scan.

### 2.4 NLP Extraction at Scale — spaCy's Matcher Duality

* **spaCy** ships two matchers for the same span contract: **`Matcher`** (token-pattern, regex-like, `[{"TEXT": {"REGEX": "^[A-Z]+$"}}, {"TEXT": "-"}, {"IS_DIGIT": True}]`) and **`PhraseMatcher`** (literal phrase list, internally Aho–Corasick via hash-based lookups). The docs explicitly note *"Pattern matching runs faster than the neural NER because it uses hash-based lookups"* — the same duality Paxman needs between shape (`RegexStage`) and vocabulary (`LexiconStage`), except Paxman's current lexicon *is* a regex, so the duality collapses.
* **spaCy + Hugging Face pipelines** (`spacy-huggingface-pipelines`) compose deterministic matchers with transformer `TokenClassificationPipeline` for NER, but the deterministic layer stays `O(N)` and streamable, while the transformer layer is optional and bounded by `stride` windowing.
* **Takeaway:** Keep deterministic recognition deterministic. Offer `ShapeRecognizer` and `LexiconRecognizer` as distinct implementations behind one `Recognizer` protocol, with `PhraseMatcher`-style Trie acceleration for the lexicon side. Do not add a neural layer (see §10).

### 2.5 Low-Level Parser Families — PEG, Combinators, and Scanners

* **PEG (Parsing Expression Grammar, Ford 2004)** — prioritized choice (`/`), unlimited lookahead, packrat linear-time memoization, no ambiguity. Every PEG can be compiled to a recursive-descent parser with code generation (`pest` for Rust: grammar file → generated types + rule hierarchy). Good for *recursive or nested* syntax (balanced delimiters, `SIUnit` compound `UNIT(SEP UNIT){0,3}` with parentheses, `Language` BCP47 `language ["-" script] ["-" region]* ("-" variant)*`).
* **Parser combinators (`nom`, Rust)** — functions `Parser: &str → IResult<Remaining, Output>` composed via combinators (`opt`, `delimited`, `take_until`, `alt`). Zero-copy (returns slices, no heap alloc), explicit whitespace discipline ("each parser consumes trailing whitespace"). The Synacktiv SHH case study (2024) directly compares pest (PEG) vs nom (combinators) on `strace` output: PEG is grammar-centric, combinators are function-centric; both beat regex once the pattern acquires structure.
* **Hand-written scanners (Flex/Ragel, `libc` `ipaddress`, `tomllib`, `email.headerregistry`)** — single-pass character state machines for context-sensitive tokenization (separator skipping, digit-run bounding, paren-depth tracking). Paxman's `URL` paren-balance and `Phone` E.164 15-digit window are already scanners hidden inside `PostStage` closures — the audit calls them "scanner problems disguised as regex+post".
* **Lark (Python, EBNF → LALR/PEG)** — `Lark.scan()` yields `ScanMatch(range=(start,end))` with `propagate_positions`, useful for recursive grammars where a hand-rolled PEG would duplicate Lark's grammar.
* **Takeaway:** Paxman today forces every structured problem through regex. The external evidence says: **use scanners for delimiting/bounding, parser combinators for orthogonal pieces, PEG/Lark for recursive syntax, and regex only for pure shape**. The staged pipeline's `PostStage` is the symptom that scanners are missing.

### 2.6 Phone & Geo Analogues — libphonenumber and pycountry

* **Google libphonenumber** (Java/C++/JS) — the closest production analogue to Paxman's `Phone` capability. It separates `PhoneNumberUtil.findNumbers(text, region)` (recognition: lenient scan for `+`/`00`/national separators) from `isPossibleNumber` vs `isValidNumber` (validation: length vs range assignment), stores metadata as binary `PhoneNumberMetadata.xml` (≈ per-region `generalDesc`, `fixedLine`, `mobile`, `tollFree`, … with `nationalNumberPattern` regex + `possibleLengths` + `exampleNumber`), and exposes `findNumbers` as an *iterable of `PhoneNumberMatch` with `start()/end()/rawString()`* — the `RecognitionMatch` contract verbatim. Critically, **metadata is data-driven, not code-driven**: adding a new region is a data update, not a grammar rewrite. Paxman's `Country`/`Currency`/`Language` registries should follow the same data-driven pattern.
* **pycountry** (Python, ISO 3166/639/4217 wrapper around Debian `pkg-isocodes` JSON) — lazy-loads `countries`, `languages`, `currencies`, `scripts` databases with `db.indices` auto-built indexes and `query` via `get(alpha_2=…)`. The pattern is `Database[Record]` with indexed lookup, not regex scan. For Paxman, `Country`'s `WholeInputLookup` is the pycountry-style path done wrong: it should be a `LexiconRecognizer` over an indexed snapshot, not a frozenset membership test disguised as a grammar.

### 2.7 What the Survey Says Collectively

Every system that outgrew one recognition language arrived at the same shape:

> **A small, fixed set of matcher types (shape, lexicon, scanner, grammar), each optimal for a narrow class of problems, sharing a typed span contract and pluggable normalization, composed per-domain as a small DAG.**

Paxman is at that inflection point now — 15 capabilities is past the threshold where one language suffices.

---

## 3. Autopsy of the Current Pipeline

### 3.1 What Ships Today

```python
# paxman/core/grammar/pipeline.py
class PipelineGrammar(Grammar[NotationT]):
    pre: Stage[NotationT] | None = None
    regex: Stage[NotationT] | None = None
    lexicon: Stage[NotationT] | None = None
    composer: Stage[NotationT] | None = None
    post: Stage[NotationT] | None = None

    def recognize(self, text: str) -> list[RecognitionMatch[NotationT]]:
        state = PipelineState(text=text, matches=[], scratch={})
        if self.pre is not None:
            state = self.pre.run(state)
            if not state.text.strip() and not state.matches:
                return list(state.matches)
        for stage in (self.regex, self.lexicon, self.composer, self.post):
            if stage is not None:
                state = stage.run(state)
        return list(state.matches)
```

```python
# paxman/core/grammar/stages.py — five stage types
StandardPre(empty_guard=True)  # whitespace-only early exit, nothing else
RegexStage(pattern, notation_fn, flags)  # re.compile(pattern).finditer(text)
LexiconStage(
    tokens, boundary, ...
)  # BoundaryGuard.wrap(LexiconAlternation(tokens).alternation).finditer
WholeInputLookup(keys, normalizer, ...)  # trimmed in frozenset membership, single span
PostStage(transform)  # RM -> RM|None per match (trim/drop)
# plus LexiconAlternation, BoundaryGuard, AmountComposer (in composer.py)
```

Engine (`orchestrator.py:run_capability`) validates `raw_text == text[start:end]`, runs `_dedup_spans` (within-grammar longer-wins, cross-grammar preserved), sorts by `(start, end, active_grammars_index, grammar_name)` (total document order), routes `target_semantics`, then `_validate_affinity` + `_filter_rules` + `format_value`.

### 3.2 Strengths to Preserve

* **Span-bearing contract** — `RecognitionMatch[start,end,raw_text,notation]` with `__post_init__` length check is correct and must survive verbatim. It enables dedup, ordering, and caller-side segmentation.
* **Engine-owned dedup/ordering** — longer-wins within-grammar, cross-grammar preservation for ambiguity (`Date` US vs European), total document order — all correct and non-trivial to get right.
* **Parity harness** — `tests/property/test_grammar_stage_parity.py` byte-identical `(start,end,raw_text,notation)` gate is the only migration mechanism that scales. Keep it as the hard gate; keep `benchmarks/harness.py` informational.
* **Layer discipline** — `core` imports nothing from `capabilities`, per-capability `grammar/data/` + `rules/data/` separation, `shared_data/currency_snapshot.json` snapshot pattern.
* **Presentation seam** — `format_value()` as sole `output_format` site, CI-scanned `tests/unit/test_rule_output_format_purity.py`.

### 3.3 Constraints that Block Scale

| Constraint | Evidence | Why It Blocks |
|---|---|---|
| **Fixed linear order, optional slots** | `for stage in (regex, lexicon, composer, post)` — every grammar pays the same traversal whether it needs it or not; `composer` must run after `lexicon` even when it needs `regex` output. | Prevents per-capability DAG (e.g., `Language` needs `normalized_view → lexicon(Trie) → composer(Prefix-gated) → scanner(balanced)`, not the fixed order). Forces duplication (`AmountComposer` fuses lexicon+pattern because it cannot consume prior `lexicon` matches). |
| **Giant alternation for large lexicons** | `SIUnit` `SYMBOL_TOKENS` 820, `NAME_TOKENS` 650, `Country` union 600, future `Language` 15k — all via `re.escape`-joined alternation with `longest_first, qualified_first` sort. | `O(P·N)` regex backtracking risk, compilation cost proportional to `Σ len(token)`, no `O(N)` guarantee. RE2::Set memory pathology applies. |
| **Scanners disguised as PostStage** | `URL` paren-balance (`count(")")`), `Phone` E.164 15-digit window (`re.finditer(r"\d+")` + LRU cache + `end = start+len(trimmed)`). | Unreadable, untestable in isolation, duplicates scanning logic. Nested `https://x/a(b(c)d)e` already needs depth tracking the PostStage loop mishandles. |
| **Dead normalized-view hook** | `PipelineState.scratch: dict[str, object]` never populated; `StandardPre` is `empty_guard` only; every capability hand-rolls `normalize_name`, `strip_separators`, `²→2`, `µ`, `en_US→en-US`, IDNA `MAPPED` inside `notation_fn`/closures. | Normalization is capability-local, undocumented, unreused, and span-unsafe (length-changing normalizations would break `raw_text == text[start:end]`). |
| **Single hardcoded composer** | `AmountComposer(amount_pattern=(?:[0-9][0-9.,\u202f]*)`, `separator=" ?"`, `lexicon_tokens=[A-Z]{3}` fallback) | Cannot express `SIUnit` compound, `Language` `Prefix`-gated variant, or any separator other than ` ?` without a new bespoke regex. |
| **`BoundaryGuard` proliferation** | 11 factories (`word_sign`, `degree_word_sign`, `digit`, `scheme_char`, `phone_national` 4-chain, `ipv6_token` consuming, …) plus verbatim `\b` in Email/IPv4, plus `ipv6_token` consuming vs zero-width mismatch. | Each grammar invents its own boundary, no uniform declaration, no composability. Adding a capability copies a factory. |
| **Label separator inconsistency** | `BIC`/`IBAN`/`ORCID` `[\s:-]+` never-zero-width (glued `IBANDE89…` → `MISSING`), `ISSN` `[\s:-]*` zero-or-more (glued `ISSN03178471` matches), `ISBN` `(?<![\s:-])` + `isbn10_lead`. | No `LabelStage` abstraction; behaviour is per-file convention, tested only by corpus. |
| **`single_value` on every grammar** | All 33 grammars `single_value=True`; `HOW_TO_ADD_NEW_GRAMMAR.md` says future scanners must set `False` deliberately. | Scanner emitting multiple spans per `recognize()` would violate the current assumption without a new annotation. |

The deepest constraint is **not a bug in any one stage** — it is that the pipeline assumes *one text, one regex family* as the universal recognition language, with lexicon and composition as optional add-ons. The next 50 capabilities include at least three families where that assumption is false by construction (see §7).

---

## 4. First Principles — What Recognition Must and Must Not Do

These are the invariants the revamp must preserve or strengthen. Everything else is negotiable.

**Must:**

* **Determinism** — same `text + contract + snapshot + registry` → same `list[RecognitionMatch]` bit-for-bit, no clock, no network, no RNG, no world-knowledge ordering. This is the `ARCHITECTURE.md` guarantee; it survives any revamp.
* **Provenance-first** — recognition never decides validity; it only proposes spans. `Rule.matches()` owns authority. `MISSING` (no span) vs `INVALID` (span but no rule) is a load-bearing distinction for callers and must remain exact.
* **Span-bearing, zero-copy** — every `RecognitionMatch` carries `[start,end)` half-open into the *original* `text` and `raw_text == text[start:end]`. Callers depend on `result.span` and `Candidate.span` for segmentation. Scanners, normalizers, and lexicon matchers must all preserve this via offset maps, not by mutating `text`.
* **Provenance of normalization** — if `µ` → `μ` or `²` → `2` or `en_US` → `en-US` changes the surface, the provenance of that transformation (BIPM, UTS #46, BCP47) must be citeable, not silent.
* **Capability isolation** — `core` still imports nothing from `capabilities`; per-capability `grammar/data/` remains the home for vocabulary; `shared_data/` remains the snapshot seam.
* **Zero mandatory runtime deps** — stdlib-only by default; optional compiled acceleration (e.g., `hyperscan`-style or `pyahocorasick`) behind a feature flag that degrades gracefully to pure Python.
* **Testability per-recognizer** — each recognizer must be unit-testable in isolation with `text → list[RecognitionMatch]` without needing a full capability or engine.

**Must Not:**

* **No guessing** — no Levenshtein, no Soundex, no thresholded similarity. `lev("BRMA","BURMA")==1` being "close enough" has no authority clause.
* **No ML/NER** — no embeddings, no logits, no context windows. "Berlin" as a place vs a surname is not a Paxman question; the caller should segment and feed Paxman a field.
* **No checksum-fused recognition** — `mod97==1` (IBAN), `MOD 11-2` (ORCID), Luhn (ISIN/CUSIP) stay in `Rule.matches()`, not in the recognizer. Early rejection would collapse `MISSING` vs `INVALID` and duplicate checksum tables into grammar files.
* **No environment-dependent ordering** — no `dict` iteration order, no `set` hash order, no filesystem glob order. Total order must remain `(start, end, declaration_index, recognizer_name)`.

---

## 5. Proposed Architecture — Universal Pluggable Recognizer

### 5.1 Core Abstraction — `Recognizer` and `InputView`

Replace `Stage` + `PipelineState` + `PipelineGrammar` with two concepts:

```python
# paxman/core/recognition/views.py (new)
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputView:
    """A materialized view of the original text with offset map.

    `text` is the view's string (e.g., lowercased, NFKC-folded, underscore→hyphen).
    `offsets[i]` is the original-text offset of view offset i (len = len(text)+1).
    For length-preserving views offsets is None (identity, zero cost).
    """

    name: str  # "original" | "normalized" | "casefolded" | ...
    text: str
    offsets: tuple[int, ...] | None  # None = identity

    def original_span(self, v_start: int, v_end: int) -> tuple[int, int]:
        if self.offsets is None:
            return (v_start, v_end)
        return (self.offsets[v_start], self.offsets[v_end])


@dataclass(frozen=True, slots=True)
class RecognitionContext:
    """Threaded through recognizers — immutable, replacement-based."""

    original_text: str
    views: dict[str, InputView]  # populated by Normalizers, read by Recognizers
    matches: list[RecognitionMatch]  # accumulated, appended only


# paxman/core/recognition/recognizer.py (new)
from typing import Protocol


class Recognizer(Protocol[NotationT]):
    """Uniform recognizer contract — every strategy implements this."""

    name: str
    semantics: str  # target_semantics for engine routing
    view: str  # InputView name to scan (default "original")
    single_value: bool  # for _enforce_single_value_invariant
    boundary: BoundarySpec | None  # uniform boundary declaration (see §5.6)

    def recognize(
        self, ctx: RecognitionContext
    ) -> list[RecognitionMatch[NotationT]]: ...
```

Key differences from `Stage`:

* `Recognizer` is **self-contained**: it declares its `view`, `semantics`, `boundary`, and `single_value`. No hidden `scratch` dict, no `PipelineState.text` mutation contract to remember.
* `InputView` is **typed** with an explicit offset map. Normalizers materialize views; recognizers read them by name. Spans always translate back to `original_text` before constructing `RecognitionMatch`, enforcing `raw_text == original_text[start:end]` at the type boundary.
* The engine, not the recognizer, owns `InputView` materialization and offset translation.

### 5.2 Normalizer — First-Class, Composable, Provenance-Aware

```python
# paxman/core/recognition/normalizer.py (new)
from typing import Protocol


class Normalizer(Protocol):
    name: str
    provenance: Provenance | None  # citeable if transformation has authority

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]: ...

    # returns (normalized_text, offsets_or_None)


# Composable sequence — mirrors tokenizers.normalizers.Sequence
@dataclass(frozen=True, slots=True)
class NormalizerSequence:
    steps: tuple[Normalizer, ...]

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]: ...
```

Shipped normalizers (all pure, deterministic, no deps):

| Normalizer | View name | Purpose | Offsets | Provenance |
|---|---|---|---|---|
| `CaseFold` | `casefolded` | `lower()` / `casefold()` for case-insensitive lexicons (Currency words, SIUnit names) | identity | None (lexical) |
| `SeparatorFold` | `normalized` | `en_US → en-US`, `[\s_]+ → "-"` for Language BCP47 | length-preserving | BCP47 §2.1 |
| `AccentStrip` | `normalized` | NFKD → strip combining marks → lower → sep→space → punct strip (Country `normalize_name`) | identity if table-driven | CLDR / ISO 3166 |
| `SymbolFold` | `normalized` | `²→2`, `µ→μ`, `Ω→Ω`, `Å→Å`, `×→x` (SIUnit) | may expand (offsets) | BIPM SI Brochure |
| `IDNAFold` | `idna` | UTS #46 `MAPPED` + `IDNA_STATUS` + tab/newline strip (URL) | may expand | UTS #46 |
| `StripSeparators` | `compact` | `" ().-" → ""` compact digits (Phone) | compressing (offsets) | ITU-T E.164 |

Each capability declares its normalizer chain declaratively; the engine materializes each `InputView` once and shares it across recognizers. This eliminates the per-file `normalize_name` / `strip_separators` / `²→2` duplication and fixes the dead `scratch` hook.

### 5.3 Strategy Kernel — Six Recognizers, One Protocol

Every capability picks one or more recognizers from the kernel. Each is `O(N)` or `O(N+Z)` with stdlib-only implementation; each returns `list[RecognitionMatch]` with original-text spans.

#### R1 — `ShapeRecognizer` (regex, for pure shape)

*When to use:* the spec defines a syntactic shape with character classes, repetitions, and bounded separators — `IBAN` `^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$`, `BIC` `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$`, `IP` `v4/v6`, `ISSN` 8-char, `ISBN` 10/13.
*Implementation:* `re.compile(pattern, flags).finditer(view.text)` with `notation_fn: re.Match → NotationT`, offset-translated. Supports `RE2`-style linear-time subset by construction (no backrefs, no catastrophic patterns); a lint can flag `.*.*`-style pathologies.
*Scales to:* single-pattern shape. Not the answer for large lexicons.

#### R2 — `LexiconRecognizer` (Trie / Aho–Corasick, for large vocabularies)

*When to use:* the spec defines a *vocabulary* — `SIUnit` 820 symbols + 650 names, `Country` 600 names, `Currency` 67 symbols + 80 words, `Language` 7k ISO 639-3 + 8k IANA subtags, `Currency` display names gated by `include_localized`.
*Implementation:* pure-Python `Trie` with `scan(view.text) → list[(token, v_start, v_end)]`, longest-at-position-wins (deepest leaf), tie → lex order (mirrors `LexiconAlternation` `longest_first, qualified_first`). `BoundarySpec` gated after scan. Threshold-gated per Banlex #3: below ~200 tokens the recognizer compiles to a small alternation for speed; above it uses Trie scan (auto-selected, no capability config change).
*Scales to:* `O(N+Z)` independent of dictionary size; 15k IANA tags still one scan.

#### R3 — `ScannerRecognizer` (character state machine, for delimiting/bounding)

*When to use:* recognition needs character-by-character state — delimiter balancing (`URL` paren depth, `DOI` `10.prefix/suffix` with `/`), digit-run bounding (`Phone` E.164 ≤15 digits), separator skipping (`IBAN` paper groups-of-four), escaped delimiters.
*Implementation:* `scan_one: (view.text, index) → (v_start, v_end, notation) | None` — the `_url_scan` closure pattern, but as a first-class recognizer, not a `PostStage.transform`. The engine calls `scan_one` left-to-right, advancing `index` to `v_end` on hit else `index+1` — non-overlapping, no post-trim LRU.
*Scales to:* one pass, no regex backtracking, depth-aware (handles `https://x/a(b(c)d)e` correctly). Testable with a corpus of nested cases.

#### R4 — `GrammarRecognizer` (PEG / combinator, for recursive/structured syntax)

*When to use:* the spec is an ABNF or EBNF with recursion or ordered choice — `Language` BCP47 `language ["-" script] ["-" region]* ("-" variant)* ("-" extension) ["-" privateuse]`, `SIUnit` compound `FACTOR = UNIT | "(" FACTOR (SEP FACTOR)* ")"`, future `RFC 3339` `date [T time [zone]]`.
*Implementation:* hand-rolled combinator stage (zero-copy, return slices) or thin `Lark`-style EBNF compiled to `recognize`. The recognizer yields `list[RecognitionMatch]` with `propagate_positions`, so nested spans are flattened to top-level `RecognitionMatch`es. No mandatory dep: pure-Python combinators by default, optional `Lark` backend behind `extra` flag.
*Scales to:* structure that would be an unreadable regex. The ABNF is the grammar file.

#### R5 — `PropertyRecognizer` (generated Unicode ranges, for open classes)

*When to use:* the spec defines an open Unicode class — `\p{Sc}` (currency symbol), `\p{Script=Han}`, `\p{ID_Start}`, `\p{Sm}` — where enumerating tokens is wrong.
*Implementation:* build-time generator `tools/regenerate_unicode_property_data.py` pulls from `unicode.org` `PropList.txt` / `Scripts.txt` and emits `grammar/data/unicode_ranges.py` (`frozenset[range]` or `tuple[int,int]` intervals), consumed as a `PropertyRecognizer` that scans `view.text` for runs of characters in the range set. No `regex` module, no runtime Unicode DB.
*Scales to:* any property that recurs twice (today: SIUnit `µΩÅ`, `BIC` `isascii`, `Language` Han detection).

#### R6 — `CandidateRecognizer` (enumerated strict formats, for spec-enumerated variants)

*When to use:* the spec enumerates *exact formats* rather than one loose shape — `Date` 4 formats (`iso8601`, `slash_iso`, `us`, `european`), `ISBN` two lexical lengths, `IBAN` 90 per-country `length+BBAN regex` rows, `Phone` per-region `nationalNumberPattern` registry, `RFC 3339` 6+ variants.
*Implementation:* `candidates: tuple[Recognizer, ...]` each with its own `pattern`/`boundary`/`notation_fn`, tried in declaration order (`first` wins per span; `all` keeps ambiguity observable). A single `Date` grammar replaces today’s 4 grammars + coalesced semantics; `IBAN` registry becomes `dict[CC, CandidateRecognizer]` with one `IBAN` semantics.
*Scales to:* registry-style capabilities without file proliferation. Each candidate cites its authoritative section.

#### Composition — `ComposerRecognizer` (generic, for multi-field values)

*When to use:* a canonical value is *composed* of adjacent fields with a separator — `Money` `CODE ? AMOUNT | AMOUNT ? CODE` / `SYMBOL ? AMOUNT`, `Language` `variant` with `Prefix`-constraint (`sl-nedis` needs `sl`), `SIUnit` compound.
*Implementation:*

```python
@dataclass(frozen=True, slots=True)
class ComposerRecognizer(Generic[NotationT]):
    name: str
    semantics: str
    left: Recognizer | None  # lexicon or shape
    right: Recognizer | None  # shape (amount) or lexicon
    separator: re.Pattern[str] | None  # e.g. re.compile(r"\s?") vs r"[\s:-]+"
    order: Literal["either", "left_then_right", "right_then_left"]
    predicate: (
        Callable[[str, str], bool] | None
    )  # prefix constraint, e.g. Prefix.contains
    boundary: BoundarySpec | None
    view: str = "original"
```

`AmountComposer` becomes `ComposerRecognizer(left=LexiconRecognizer(tokens=CODE_TOKENS), right=ShapeRecognizer(pattern=AMOUNT_CORE), separator=ONE_SPACE, order="either")` — a documented alias, no behaviour change. Generic `predicate` handles `Language` `Prefix` gating without a second regex.

### 5.4 Recognition Plan — DAG, Not Linear Pipeline

Each capability declares a **recognition plan** — a DAG of recognizers and normalizers, not a fixed linear order:

```python
# paxman/capabilities/Language/grammar/__init__.py (illustrative)
from paxman.core.recognition import NormalizerSequence, SeparatorFold, AccentStrip
from paxman.core.recognition.recognizers import (
    LexiconRecognizer,
    ScannerRecognizer,
    GrammarRecognizer,
    ComposerRecognizer,
)

LANGUAGE_PLAN = RecognitionPlan(
    normalizers=NormalizerSequence(steps=(SeparatorFold(), AccentStrip())),
    recognizers=(
        LexiconRecognizer(
            name="language_code",
            semantics="bcp47_tag",
            view="normalized",
            tokens=ISO639_3_KEYS,
            boundary=WordBoundary,
        ),
        LexiconRecognizer(
            name="iana_variant",
            semantics="bcp47_tag",
            view="normalized",
            tokens=IANA_VARIANT_KEYS,
            boundary=HyphenBoundary,
        ),
        GrammarRecognizer(
            name="bcp47_tag",
            semantics="bcp47_tag",
            view="normalized",
            abnf=BCP47_ABNF,
            boundary=WordBoundary,
        ),
        ComposerRecognizer(
            name="prefix_constrained_variant",
            semantics="bcp47_tag",
            left=LexiconRecognizer(tokens=LANGUAGE_KEYS),
            right=LexiconRecognizer(tokens=VARIANT_KEYS),
            separator=HyphenSep,
            predicate=prefix_ok,
        ),
    ),
)
```

The `RecognitionEngine` executes the plan:

1. Materialize `InputView`s once (`original` always, `normalized` etc. on demand, with offset maps).
2. Run independent recognizers in parallel (no inter-dependency → parallel; dependent recognizers e.g. `Composer` after its `left`/`right` → ordered).
3. Offset-translate every `RecognitionMatch` to `original_text` spans.
4. Dedup (`_dedup_spans` — within-recognizer longer-wins, cross-recognizer preserved) and sort (`(start, end, declaration_index, recognizer_name)`) — owned by engine, unchanged from today.
5. Validate `raw_text == original_text[start:end]` at the boundary (raises `RecognitionError` on violation).

A capability with no normalizer and one `ShapeRecognizer` (today's `IBAN`) declares a one-node DAG — zero overhead.

### 5.5 Engine — `RecognitionEngine` Replaces `PipelineGrammar.recognize()`

```python
# paxman/core/recognition/engine.py (new)
@dataclass(frozen=True, slots=True)
class RecognitionEngine:
    plan: RecognitionPlan

    def recognize(self, text: str) -> list[RecognitionMatch]:
        views = self._materialize_views(text)  # 1
        all_matches: list[RecognitionMatch] = []
        for recognizer in self._topo_sort(self.plan.recognizers):  # 2
            view_text = views[recognizer.view].text
            raw_matches = recognizer.recognize(
                RecognitionContext(original_text=text, views=views, matches=[])
            )
            for m in raw_matches:
                v_start, v_end = m.start, m.end  # view offsets
                o_start, o_end = views[recognizer.view].original_span(
                    v_start, v_end
                )  # 3
                all_matches.append(
                    RecognitionMatch(
                        notation=m.notation,
                        start=o_start,
                        end=o_end,
                        raw_text=text[o_start:o_end],
                    )
                )
        return self._dedup_and_sort(all_matches)  # 4 + 5
```

The engine is capability-agnostic; `Capability.get_recognizers()` replaces `get_grammars()` (or wraps it with a compat shim during migration). `Capability` no longer needs `PipelineGrammar` subclasses — it returns a `RecognitionPlan`.

### 5.6 Uniform Boundary Declaration

Replace 11 `BoundaryGuard` factories + verbatim `\b` with a single `BoundarySpec`:

```python
@dataclass(frozen=True, slots=True)
class BoundarySpec:
    left: (
        str | re.Pattern[str] | None
    )  # lookbehind or consuming prefix; None = no constraint
    right: str | re.Pattern[str] | None  # lookahead or consuming suffix
    mode: Literal["zero_width", "consuming"] = "zero_width"
    # Shipped presets:
    WORD = BoundarySpec(left=r"(?<!\w)", right=r"(?!\w)")
    WORD_SIGN = BoundarySpec(left=r"(?<![\w\-+\u2212])", right=r"(?![\w\-+\u2212])")
    DIGIT = BoundarySpec(left=r"(?<!\d)", right=r"(?!\d)")
    # ... etc., plus capability-local custom specs
```

A recognizer declares `boundary=BoundarySpec.WORD` (or `None` for `Phone` E.164-style open boundary). The engine applies the boundary gate after view translation, keeping `LexiconRecognizer` and `ShapeRecognizer` comparable.

### 5.7 Label Handling — Unified

```python
@dataclass(frozen=True, slots=True)
class LabelSpec:
    labels: frozenset[str]  # e.g. {"IBAN","BIC","SWIFT","ORCID","ISSN"}
    separator: re.Pattern[str]  # e.g. re.compile(r"[\s:-]+") vs r"[\s:-]*"
    glued_policy: Literal[
        "reject", "allow"
    ]  # "IBANDE89…" → MISSING vs "ISSN03178471" → hit
```

`LabelSpec` wraps a `ShapeRecognizer` or `LexiconRecognizer` to fuse optional label + value, handling glued-input policy and bare-scheme drop in one place. This unifies `IBAN`/`BIC`/`ORCID` `[\s:-]+` never-zero-width vs `ISSN` `[\s:-]*` inconsistency without a fifth stage.

### 5.8 Why This Scales

* **Per-capability DAG → no forced order.** `Language` needs `normalized → lexicon(Trie) → composer(Prefix) → grammar(ABNF)`; `URL` needs `idna view → scanner(balanced)`; `IBAN` needs `shape + candidate registry`; each declares only what it needs.
* **`O(N)` lexicon scan → handles 15k+ vocabulary.** Threshold-gated Trie keeps small lexicons fast (alternation) and large lexicons linear.
* **Scanner as first-class → no PostStage hacks.** `URL` parens and `Phone` E.164 window become readable, testable scanners with depth/state, not trim closures with LRU caches.
* **Typed `InputView` → normalization is audit-grade.** Offset maps make length-changing normalizations span-safe; each view's provenance is citeable.
* **Parallel recognizers → latency-friendly.** Independent `LexiconRecognizer`s and `ShapeRecognizer`s scan different vocabularies in parallel (thread-safe, no shared mutable state — `RecognitionContext` is frozen, `views` is `dict[str,InputView]` read-only after materialization).

---

## 6. Beyond Recognition — Four Required Companion Changes

A recognition-only revamp that leaves the surrounding system untouched will create new seams that do not line up. Four changes outside `paxman/core/recognition/` are required for the revamp to be coherent.

### 6.1 Engine — Streaming and Incremental Recognition

**Today:** `run_capability(text, contract)` is a single `recognize(text) → matches → validate → resolve` call with `text` as a monolithic `str`. No caller can stream a 10 MB log, a multi-page document, or a Kafka chunk without buffering.

**Proposed:** `RecognitionEngine` supports `recognize_iter(chunks: Iterable[str]) → Iterable[list[RecognitionMatch]]` with incremental `InputView` materialization and a bounded lookbehind window (configurable per recognizer — `Phone` national may need `±20` chars of context, `ISIN` needs `12`). The engine stitches cross-chunk spans via a carry buffer (at most `max_pattern_len - 1` chars, trivial for fixed-length `ISIN` 12, bounded for `URL` via `max_url_len` config). This also unlocks the `docs/recipes/segmentation.md` caller-owned split-then-canonicalize pattern as an engine-owned option.

**Why it matters for scale:** 100 capabilities each scanning a 1 MB document naively is 100 MB of `finditer` passes. A streaming engine with shared `InputView` materialization scans once, fans out recognizers over the same `views`, and reuses offset maps.

### 6.2 Contract — Feature Flags Become Recognizer-Scoped

**Today:** `CapabilityContract` carries `excluded_rules`, `pinned_rules`, `year`, `requires_features`, `extra_grammars`, plus capability-specific flags (`include_localized`, `include_historical`, `allow_split_word_prefixes`, `allow_multi_solidus`, `default_currency`, …). `extra_grammars: tuple[str,…]` opts into community grammars by semantics id, with silent skip for unknown names and fail-fast for dangling `target_semantics`.

**Proposed:** Contracts declare `active_recognizers: frozenset[str] | None` (None = all shipped) instead of `active_grammars`, and recognizer-scoped feature flags (`features: frozenset[str]` where each recognizer declares its `requires_features`). The `extra_grammars` seam generalizes to `extra_recognizers: tuple[str,…]` with the same opt-in, silent-skip, and fail-fast semantics — preserving the community-extension contract verbatim but widening it to any `Recognizer` type, not just `Grammar`. Capability-specific flags remain (e.g., `allow_multi_solidus` becomes `features={"multi_solidus"}` consumed by `CompoundRecognizer`).

**Why it matters:** As recognizer types multiply, `extra_grammars` naming becomes misleading. A single `features` set avoids a combinatorial explosion of `include_*` booleans.

### 6.3 Data — Generalize the Snapshot Pattern

**Today:** `shared_data/currency_snapshot.json` + `tools/regenerate_currency_data.py` → per-capability `grammar/data/` + `rules/data/` dedup works (gated by `tests/unit/test_currency_data_regeneration.py`). Other large vocabularies (`BIC _COUNTRY_CODES` 250 duplicates `rules/`, `SIUnit` `SYMBOL_TOKENS` 820 generated via `regenerate_si_prefix_data.py`, `URL` IDNA `IDNA_STATUS/MAPPED` vendored, `ISBN` `range_message.py` 2026) follow the same generator pattern ad hoc.

**Proposed:** Formalize `Snapshot` as a core concept:

```python
@dataclass(frozen=True, slots=True)
class Snapshot:
    name: str  # "currency" | "iban_registry" | "iana_language" | "unicode_property"
    source_url: str  # authoritative fetch URL
    version: str  # e.g. "CLDR v47" | "SWIFT R100" | "IANA 2026-08-08"
    fetched_at: str  # ISO date
    data: object  # typed payload (frozen)
```

Each snapshot has a generator `tools/regenerate_<name>_data.py` that writes to `paxman/shared_data/<name>_snapshot.json` and per-capability `grammar/data/` + `rules/data/` views. Drift is gated by `tests/unit/test_<name>_snapshot_parity.py` (same pattern as currency). For `Language` IANA registry (7990 `Type: language` rows + `Prefix` constraints), `IBAN` SWIFT Registry (90 country rows `length + BBAN regex`), and `Unicode` property tables, this prevents hand-copied drift.

### 6.4 Verification — Extend the Gate, Keep the Promise

**Today:** `tests/property/test_grammar_stage_parity.py` (byte-identical `RecognitionMatch` equality) is the hard migration gate; `benchmarks/harness.py` (50 iterations, informational) is not a gate.

**Proposed:** Keep parity as the hard gate, but shard it per recognizer type:

* `test_shape_parity.py` — `ShapeRecognizer` vs legacy `RegexStage`
* `test_lexicon_parity.py` — `LexiconRecognizer` (Trie vs alternation) vs legacy `LexiconStage`
* `test_scanner_parity.py` — `ScannerRecognizer` vs legacy `PostStage` trim closures
* `test_view_parity.py` — `InputView` offset translation round-trip (`original_span` inverse)

Add `tests/property/test_recognition_properties.py` with Hypothesis strategies per recognizer:

* `raw_text == original_text[start:end]` for all returned matches (already enforced, but property-tested across random text).
* `longest_first` determinism: Trie scan and alternation agree on longest match at each position.
* `MISSING` vs `INVALID` non-collapse: no recognizer rejects a span that a rule would accept (fuzz `text` with valid + invalid probes).
* Streaming equivalence: `recognize(text) == flatten(recognize_iter(chunk(text)))` for chunked input.

Benchmark harness remains informational, but now measures the Trie crossover threshold (lexicon size where `Trie.scan` beats `alternation.finditer`) to keep the auto-selection honest.

---

## 7. Capability Mapping — Shipped and Planned

### 7.1 Shipped Capabilities — How Each Migrates

| Capability | Today (pipeline) | After (recognizer plan) | Why the new mapping is better |
|---|---|---|---|
| **BIC** | `pre+regex` (1 grammar, `(?ai:…)` ASCII guard, `_COUNTRY_CODES` frozenset negative lookahead) | `ShapeRecognizer` + `LabelSpec(labels={"BIC","SWIFT"}, sep=[\s:-]+, glued=reject)` + `Normalizer(CaseFold)` view `casefolded` | Label policy unified; ASCII guard becomes a `PropertyRecognizer` range or view filter, not inline `(?ai:…)` |
| **IBAN** | `pre+regex` (1 grammar, `[\s:-]+` label, paper groups-of-four absorbed) | `ShapeRecognizer` (compact) + `ScannerRecognizer` (paper groups-of-four) + `CandidateRecognizer(registry=dict[CC, ShapeRecognizer])` + `LabelSpec` | Per-country BBAN `regex` registry becomes a candidate set, not one loose `regex` + `mod97` fallback; glued tail like `IBANDE89…` handled by `LabelSpec.glued=reject` |
| **IP** (v4/v6) | `pre+regex` ×2, `ipv6_token` consuming boundary | `ShapeRecognizer` ×2 (v4, v6) with `BoundarySpec(WORD)` + shared `Normalizer` for `::` compression | Consuming vs zero-width boundary unified under `BoundarySpec(mode=…)` |
| **ISBN** (10/13) | `pre+regex` ×2, `isbn10_lead` lookahead + digit extraction | `CandidateRecognizer(candidates=(isbn13_shape, isbn10_shape))` + `LabelSpec(labels={"ISBN"}, sep=[\s:-]*)` | Two lexical lengths stay as candidates under one semantics when desired; hyphen tolerance stays regex-native but candidate-scoped |
| **ISSN** | `pre+regex` (1 grammar, `[\s:-]*` glued allowed) | `ShapeRecognizer` + `LabelSpec(labels={"ISSN","ISSN-L","ISSN-H"}, sep=[\s:-]*, glued=allow)` | Label consistency documented as `LabelSpec.glued` choice, not per-file convention |
| **ORCID** | `pre+regex` (1 grammar, `[\s:-]+` label, MOD 11-2 in rule) | `ShapeRecognizer` + `LabelSpec(labels={"ORCID"}, sep=[\s:-]+, glued=reject)` | Same as IBAN/BIC — unified label seam |
| **Country** (4 grammars) | `pre+lexicon:WIL` (whole-input name, 600 keys, `normalize_name` inside `WholeInputLookup`) + `pre+regex` ×3 (α2/α3/numeric) | `LexiconRecognizer(Trie, view=normalized)` (whole-input via `end==len(trimmed)` gate) + `ShapeRecognizer` ×3 + `NormalizerSequence(AccentStrip, SeparatorFold)` | `normalize_name` becomes a `Normalizer` view, not a `WholeInputLookup.normalizer` argument; 600 keys via Trie, not frozenset membership; no duplication between name vs code paths |
| **Currency** (3) / **Money** (3) | `pre+lexicon` (symbol/word via `LexiconAlternation+BoundaryGuard.word_sign`) + `AmountComposer` (fused `lex ? amt | amt ? lex` with ` ?` sep) | `LexiconRecognizer(Trie, boundary=WORD_SIGN)` + `ComposerRecognizer(left=LexiconRecognizer(tokens=CODE∪SYMBOL∪WORD), right=ShapeRecognizer(amount), separator=ONE_SPACE|None, order=either)` + `Normalizer(CaseFold)` | `AmountComposer` hardcoded ` ?` and `[A-Z]{3}` fallback become params; small lexicons stay alternation via threshold, large ones auto-Trie; single composer, not a second copy for Money |
| **Date** (4) | `pre+regex` ×4 (`iso8601`, `slash_iso`, `us`, `european`) coalesced for `iso8601_calendar_date` semantics | `CandidateRecognizer(candidates=(iso8601, slash_iso, us, european))` — 1 grammar with 4 candidates | 4 files → 1 file; `BoundaryGuard.digit()` shared; `target_semantics` per candidate kept (iso8601 candidates coalesce, us/european stay distinct so `01/02/2026` → `AMBIGUOUS`) |
| **Email** (3) | `pre+regex` ×3 (`standard`, `obfuscated`, `localhost` with `\b` verbatim) | `ShapeRecognizer` ×3 + `ScannerRecognizer` for `at`→`@` / `dot`→`.` obfuscation when needed | Verbatim `\b` becomes `BoundarySpec.WORD`; obfuscated recognition optionally a `ScannerRecognizer` that walks `at` tokens statefully rather than one giant regex |
| **Phone** (4) | `pre+regex` ×3 + `pre+regex+post` (`e164` 15-digit `_trim_to_e164_boundary` LRU + `national` 4-lookbehind + `tel_uri` + `00`) | `ScannerRecognizer` (E.164 bounded scan, ≤15 digits, no LRU) + `ShapeRecognizer` ×2 (tel_uri, 00) + `ShapeRecognizer` (national with `BoundarySpec(phone_national)`) + `Normalizer(StripSeparators)` view `compact` | PostStage LRU and 4-lookbehind chain become declarative scanner + normalizer; bounded scan handles `+1 425 882-8080`'s 15-digit window without overshoot+trim |
| **SIUnit** (3) | `pre+regex` ×3: symbol/name via 820/650 giant alternations + `compound` `UNIT(SEP UNIT){1,3}` + inline `split_symbol_prefix`/`split_word_prefix` classifiers inside `notation_fn` | `LexiconRecognizer(Trie, boundary=DEGREE_WORD_SIGN)` for symbol/name (820/650 → `O(N)` scan) + `ComposerRecognizer` for compound + `GrammarRecognizer` for parenthesized `FACTOR` + `Normalizer(SymbolFold)` | Giant alternation → Trie; `split_*` classifiers inside `notation_fn` become `ComposerRecognizer` with `predicate=prefix_ok`; `compound` regex becomes a composer, recursive parentheses a grammar recognizer |
| **URL** (1) | `pre+regex` (loose `scheme: body`) + `PostStage(_url_trim)` counting `")"` depth, bare-scheme drop | `ScannerRecognizer(scan_one=_url_scan)` with depth counter for `()`, `[]`, `""`, `<>`, plus bare-scheme `scheme_end+1` drop, over `InputView(idna)` via `Normalizer(IDNAFold)` | Paren-balance becomes depth-aware scan (handles `https://x/a(b(c)d)e`) without regex backtracking; IDNA `MAPPED` + tab/newline strip becomes a view, not per-rule helper |
| **Language** (planned) | Not yet implemented — plan says BCP47 ABNF `language ["-" script] ["-" region]* ("-" variant)* …` + 7k ISO 639-3 + 8k IANA subtags + `Prefix` gating + `_→-` tolerance as unmaintainable regex | `GrammarRecognizer(abnf=BCP47)` + `LexiconRecognizer(Trie, tokens=ISO639_3 ∪ IANA)` + `ComposerRecognizer(predicate=prefix_contains)` + `NormalizerSequence(SeparatorFold, AccentStrip)` view `normalized` | The only future that genuinely cannot ship without the new kernel — now feasible without a 15k-token alternation |

### 7.2 Planned / Future Families — Coverage

| Future capability | Recognition family | Required recognizers |
|---|---|---|
| **ISIN** (12-char `CC+NSIN+check` Luhn) | fixed-length shape + country-prefix prefix | `ShapeRecognizer("^[A-Z]{2}[A-Z0-9]{9}[0-9]$")` + `LexiconRecognizer(Trie, tokens=COUNTRY+SPECIAL_PREFIXES)` + `LabelSpec` |
| **CUSIP / FIGI / LEI** | 9/12/20 char alphanumeric + check | `ShapeRecognizer` (pure shape, fixed-length) |
| **RFC 3339 / ISO 8601 extended** | enumerated strict `YYYY-MM-DD [T hh:mm:ss[.frac][Z|±hh:mm]]` | `CandidateRecognizer(6+ candidates)` + optional `GrammarRecognizer` for recursive time+zone |
| **IBAN registry (full 90 countries)** | per-country `length+BBAN regex` dispatch | `CandidateRecognizer(registry=dict[CC, ShapeRecognizer])` — data-driven, not code-driven |
| **DOI / URN** | `10.prefix/suffix` with balancing | `ScannerRecognizer` (balanced `/`, `.`, `()` in suffix) |
| **Postal code / VAT ID** | per-country width/charset (`^[A-Z0-9 ]{3,10}$` dispatched by CC) | `ShapeRecognizer` + `LexiconRecognizer(Country CC Trie)` + `ComposerRecognizer` for CC+code |
| **Timezone / tzdata URI** | region/city lexicon + `±hh:mm` offset | `LexiconRecognizer(Trie, tokens=TZDB_KEYS 600+)` + `CandidateRecognizer` for offset variants |

All of these are shape or lexicon or scanner problems today — none requires ML.

---

## 8. Phased Adoption — From Current to New Without Forking

The revamp must not be a flag-day fork. Propose four phases, each shippable independently with the parity gate green.

### Phase 0 — Scaffolding (no behaviour change)

* Land `paxman/core/recognition/{views,recognizer,normalizer,engine,boundary,label}.py` with `Recognizer` protocol, `InputView`, `BoundarySpec`, `LabelSpec`, `Normalizer` + `NormalizerSequence`, `RecognitionEngine` (with streaming stub).
* Add one recognizer at a time behind a compat shim: `PipelineGrammar` gains a `recognizers: tuple[Recognizer,…] | None` field; if non-None, `recognize()` delegates to `RecognitionEngine(plan=RecognitionPlan(normalizers=…, recognizers=self.recognizers))` and translates spans; else it runs the old `pre→regex→lexicon→composer→post` loop. This preserves byte-identical parity during migration and keeps `tests/property/test_grammar_stage_parity.py` green.

### Phase 1 — Normalizer + Lexicon (P1, highest leverage)

* Ship `InputView` + `NormalizerSequence` and migrate `Country` `normalize_name`, `Phone` `strip_separators`, `SIUnit` `²→2/µ→μ`, `Language` `_→-` to views.
* Land `LexiconRecognizer` with threshold-gated Trie; pilot on `SIUnit` symbol (820) vs legacy alternation under `bench` harness — keep `LexiconStage` for small vocabularies, auto-switch above ~200 tokens.
* Parity shard `test_lexicon_parity.py` (Trie vs alternation longest-first equality).

### Phase 2 — Scanner (P2, fixes PostStage hacks)

* Land `ScannerRecognizer`; migrate `URL` paren-balance and `Phone` E.164 15-digit window from `PostStage` to scanners. Retire the `PostStage` class once both pilots are green.
* Parity shard `test_scanner_parity.py`; nested-paren corpus added to `tests/capabilities/url/`.

### Phase 3 — Candidate + Composer Generalization (P3, registry scale)

* Land `CandidateRecognizer` and `ComposerRecognizer`; collapse `Date` 4→1 grammar, formalize `IBAN` per-country registry as `dict[CC, ShapeRecognizer]` behind a candidate.
* Generalize `AmountComposer` to `ComposerRecognizer` as a thin alias — no Money behaviour change.
* Land `PropertyRecognizer` generator when a second Unicode property recurs (after SIUnit `µΩÅ`, Language Han is the trigger).
* Retire `PipelineGrammar` linear fields (`pre/regex/lexicon/composer/post`) once all shipped capabilities have a `RecognitionPlan`.

Each phase is one PR series, capability-at-a-time, with `ruff + ruff format --check + pyright + import-linter + pytest` as the `.github/workflows/ci.yml` gate, plus the parity shard for that recognizer type.

---

## 9. Verification & Performance Model

### Verification

* **Hard gate:** byte-identical `list[RecognitionMatch]` `(start,end,raw_text,notation)` per recognizer × corpus + Hypothesis random text. Extend the existing `tests/property/test_grammar_stage_parity.py` into per-recognizer shards (see §6.4). No new recognizer lands without its shard green.
* **Property gate:** Hypothesis `raw_text == original_text[start:end]`, `longest_first` Trie↔alternation determinism, `MISSING` vs `INVALID` non-collapse, streaming equivalence `recognize(text) == flatten(recognize_iter(chunk(text)))`.
* **Benchmark harness:** `benchmarks/harness.py` stays informational (CI 50 iterations), but now also reports Trie crossover size (tokens vs time) and scanner vs regex+PostStage wall time on `URL` nested-paren corpus. No benchmark gates CI — thresholds move as hardware does — but the harness informs the auto-selection threshold.
* **Drift gate:** `tests/unit/test_*_snapshot_parity.py` per snapshot (currency already, add `iban_registry`, `iana_language`, `unicode_property`).

### Performance Model (qualitative)

| Recognizer | Complexity | Constant factor | When it wins |
|---|---|---|---|
| `ShapeRecognizer` (regex) | `O(N)` per pattern via DFA | low (C `re` engine) | Single pure shape (BIC, ISBN, ISIN) |
| `LexiconRecognizer` alternation | `O(P·N)` compilation + `O(N)` scan but backtracking risk near large `P` | medium for small `P`, degrades for large `P` | Small vocabularies (< ~200 tokens) — remains the default below threshold |
| `LexiconRecognizer` Trie scan | `O(N + Z)` (Aho–Corasick), `Z` = matches | low-medium pure Python, very low with C extension | Large vocabularies (≥ ~200 tokens): SIUnit 820, Country 600, Language 15k |
| `ScannerRecognizer` | `O(N)` one pass | very low (single loop, no regex) | Delimiting/bounding (URL, Phone E.164, DOI) |
| `GrammarRecognizer` (combinator) | `O(N)` or `O(N)` packrat memoized | medium (function call per combinator) | Recursive ABNF (BCP47, RFC 3339, SIUnit compound) |
| `CandidateRecognizer` | `Σ O(N)` over candidates, short-circuit on `first` | linear in candidate count | Enumerated strict formats (Date 4, IBAN 90 — but IBAN dispatched by CC, so `O(1)` after prefix lookup) |

The current pipeline's giant alternations are `O(P·N)` with poor constants for large `P`; the proposed kernel trades one `O(P·N)` compilation for one `O(N)` scan per view — a structural, not incremental, win when `P` grows.

---

## 10. Rejected Alternatives

Documented so the next contributor does not reopen them.

### ML / NER (named-entity recognition)

Representations like "OpenAI", "Berlin", "EUR/USD" are disambiguated by context windows and trained weights, not by an authority-backed spec. They violate every Paxman invariant: non-deterministic (weights, beam, temperature), no provenance (embedding nearest-neighbour, not a registry/RFC), no canonical value (observation vs identifier), needs world-knowledge/clock. Recognition is `text → spans`, not `text → embeddings → logits → guess`. Any capability that looks like it needs NER (people/places detection) belongs in a caller-side extractor that feeds Paxman segmented fields.

### Fuzzy / Approximate Matching (Levenshtein, edit distance, Soundex)

A fixed edit-distance threshold preserves determinism, but provenance degrades: `lev("BRMA","BURMA")==1` being "close enough" has no authority — no ISO clause authorizes typo tolerance. The grammar/validation split intentionally emits `INVALID` rather than guessing (`ARCHITECTURE.md` "no guessing"). A caller needing typo-tolerant search should build an index over canonical forms Paxman returns.

### Checksum-Fused Recognition

Tempting to short-circuit `INVALID` earlier by folding `mod97==1` (IBAN), `MOD 11-2` (ORCID), Luhn (ISIN/CUSIP) into the recognizer. Resist: it would collapse `MISSING` vs `INVALID` semantics (important for provenance tracking), require duplicating checksum tables inside grammar files, and break the `ipaddress` `try/except` rule precedent. Checks stay in `Rule.matches()`.

### Adding a Mandatory Compiled Dep (e.g., `pyahocorasick`, `hyperscan`) as Core

Tempting for Trie speed, but it violates the zero-mandatory-dep invariant, complicates `uv` installs on ARM/Windows, and adds a native build to every CI run. The correct posture is: pure-Python Trie in `core` by default, optional C extension behind `paxman[trie]` extra with auto-fallback — same pattern as `hyperscan`'s own `pip install` being optional.

---

## 11. Comparative Matrix

| Dimension | Today (`PipelineGrammar`) | After (`RecognitionEngine` + kernel) |
|---|---|---|
| **Order** | Fixed linear `pre→regex→lexicon→composer→post`, optional slots | Per-capability DAG, parallel where independent |
| **Normalization** | `StandardPre(empty_guard)` only; `scratch` dead; per-file hand-rolled `normalize_name`/`strip_separators`/`²→2` | `InputView` + `NormalizerSequence` with offset maps, engine-materialized, provenance-aware |
| **Large lexicon** | `re.escape`-joined alternation (`longest_first, qualified_first`) — `O(P·N)` | `LexiconRecognizer` threshold-gated: alternation <200 tokens, Trie `O(N+Z)` above |
| **Balanced/delimited** | `RegexStage` loose shape + `PostStage` trim loop (URL parens, Phone 15-digit LRU) | `ScannerRecognizer` state machine, depth-aware, no LRU |
| **Recursive syntax** | Giant regex or compositional `UNIT(SEP UNIT){1,3}` inside `notation_fn` | `GrammarRecognizer` (PEG/combinator, EBNF for BCP47/RFC3339) |
| **Enumerated variants** | One file per variant (`Date` ×4, `IBAN` loose regex + fallback) | `CandidateRecognizer(registry=dict[…])` — one grammar, many candidates, per-candidate provenance |
| **Composition** | `AmountComposer` single-separator ` ?`, `[A-Z]{3}` fallback, fails on named groups | `ComposerRecognizer(left,right,separator,order,predicate)` — generic, prefix-gated |
| **Boundary** | 11 `BoundaryGuard` factories + verbatim `\b` + consuming `ipv6_token` | `BoundarySpec` uniform, zero-width vs consuming explicit |
| **Label** | Per-file `[\s:-]+` vs `[\s:-]*` vs `(?<![\s:-])` convention | `LabelSpec(labels, separator, glued_policy)` |
| **Streaming** | Monolithic `str` | `recognize_iter(chunks)` with bounded carry buffer |
| **Verification** | One `test_grammar_stage_parity.py` gate + informational bench | Per-recognizer parity shards + Hypothesis properties + streaming equivalence + snapshot drift gates |
| **Deps** | stdlib only | stdlib only by default; optional `paxman[trie]` C extension with fallback |

---

## 12. Appendix — Sketches and References

### A. `Recognizer` Sketch (illustrative, not a patch)

```python
# paxman/core/recognition/recognizer.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar
from paxman.core.domain import RecognitionMatch

NotationT = TypeVar("NotationT")


class Recognizer(Protocol[NotationT]):
    name: str
    semantics: str
    view: str
    single_value: bool

    def recognize(
        self, ctx: RecognitionContext
    ) -> list[RecognitionMatch[NotationT]]: ...


@dataclass(frozen=True, slots=True)
class RecognitionPlan(Generic[NotationT]):
    normalizers: NormalizerSequence | None = None
    recognizers: tuple[Recognizer[NotationT], ...] = ()
```

### B. Trie Sketch

```python
# paxman/core/recognition/trie.py (pure Python, stdlib-only)
from dataclasses import dataclass, field


@dataclass(slots=True)
class _Node:
    children: dict[str, _Node] = field(default_factory=dict)
    output: list[str] = field(default_factory=list)  # tokens ending here
    fail: _Node | None = None


class Trie:
    def __init__(self, tokens: set[str], casefold: bool = False) -> None:
        self._root = _Node()
        self._casefold = casefold
        for tok in tokens:
            self._insert(tok.casefold() if casefold else tok, tok)

    def _insert(self, key: str, token: str) -> None: ...
    def _build_failure_links(self) -> None: ...  # BFS, like CP-Algorithms
    def scan(self, text: str) -> list[tuple[str, int, int]]:  # (token, start, end)
        # walk text, follow fail links, emit longest at each position
        ...
```

### C. Scanner Sketch

```python
# urls.py — capability-local closure, no core import of capability data
def _url_scan(view_text: str, i: int) -> tuple[int, int, URLNotation] | None:
    if not _is_scheme_start(view_text, i):
        return None
    scheme_end = view_text.find(":", i)
    if scheme_end == -1:
        return None
    # scan body with depth counter for (), [], "", <>
    depth = 0
    j = scheme_end + 1
    while j < len(view_text) and not _is_boundary(view_text, j):
        if view_text[j] == "(":
            depth += 1
        elif view_text[j] == ")":
            if depth == 0:
                break
            depth -= 1
        j += 1
    if j == scheme_end + 1:  # bare scheme "https:" with no body
        return None
    raw = view_text[i:j]
    return (i, j, URLNotation(value=raw))
```

### D. Primary External References

* USENIX NSDI'19 — Wang et al., *Hyperscan: A Fast Multi-pattern Regex Matcher for Modern CPUs* — decomposition into string prefilter + NFA, Snort 8.7× speedup. <https://www.usenix.org/system/files/nsdi19-wang-xiang.pdf>
* Toptal — Vashchegin, *Conquer String Search with the Aho-Corasick Algorithm* — `O(N+L+Z)` analysis, Trie + failure-link construction. <https://www.toptal.com/developers/algorithms/aho-corasick-algorithm>
* CP-Algorithms — *Aho-Corasick algorithm* (2025-04-18). <https://cp-algorithms.com/string/aho_corasick.html>
* VectorEdge — Koli et al., *CHPDA — Context-Aware Hybrid Pattern Detection* (2025) — RE2 vs Aho–Corasick vs AI-NER benchmark, Aho–Corasick optimal for glossary scanning. <https://arxiv.org/html/2502.07815v1>
* Hugging Face `tokenizers` — *The tokenization pipeline* (`Normalization → Pre-tokenization → Model → Post-processing`), `Normalizer`, `PreTokenizer`, `NormalizedString` offset tracking. <https://huggingface.co/docs/tokenizers/v0.20.3/en/pipeline>
* spaCy — `Matcher` (token-pattern) vs `PhraseMatcher` (literal phrase, Aho–Corasick via hash), `spacy-huggingface-pipelines` for hybrid deterministic+transformer. <https://spacy.io/api/matcher>
* Synacktiv — Desbrus, *Battle of the parsers: PEG vs combinators* (2024) — `pest` (PEG, grammar file → codegen) vs `nom` (combinator, zero-copy `IResult`) on `strace` output. <https://www.synacktiv.com/en/publications/battle-of-the-parsers-peg-vs-combinators.html>
* Racket PEG — *PEG can be thought of as an advance over regex. It can match more languages (for example balanced brackets) and can be paired with semantic actions.* <https://docs.racket-lang.org/peg/index.html>
* Google libphonenumber — `PhoneNumberUtil.findNumbers(CharSequence, String) → Iterable<PhoneNumberMatch>` (`start()/end()/rawString()`), `PhoneNumberMetadata.xml` per-region regex + `possibleLengths`, `isPossibleNumber` vs `isValidNumber` split. <https://github.com/google/libphonenumber>
* pycountry — Debian `pkg-isocodes` JSON wrapper, `Database[Record]` with `db.indices` auto-index, `query` via `get(alpha_2=…)`. <https://github.com/pycountry/pycountry>
* `pyahocorasick` threshold pattern — Banlex #3 (2026) "Optional Aho-Corasick backend for large lexicons, selected automatically above a phrase-count threshold". <https://github.com/cognis-digital/banlex/issues/3>
* Intel Hyperscan vs RE2::Set — Branchfree / 01.org analysis of `RE2::Set` DFA cache explosion past ~30 patterns, Hyperscan's stable multi-pattern matching. <https://01.org/hyperscan/blogs/jpviiret/2017/regex-set-scanning-hyperscan-and-re2set>

---

## Closing Note to the Owner

The current pipeline is not *wrong* — it ships 15 capabilities correctly and its parity harness is the strongest asset to keep. It is *small*. It assumes "one text, one regex family" is the universal recognition language, with lexicon and composition as add-ons. That was the right starting shape. It is now the constraint you feel: every new capability that does not look like a regex-plus-optional-lexicon pays a workaround tax (PostStage trim, frozenset membership, inline `split_*` classifier, 4-file Date).

The proposal above does not ask you to believe a new abstraction is better because it is new. It asks you to observe that **every production system that outgrew one recognition language arrived at the same shape** — a small, fixed set of matcher types (shape, lexicon, scanner, grammar), each optimal for a narrow class, sharing a typed span contract and pluggable normalization, composed per-domain as a small DAG. Hugging Face `tokenizers`, spaCy, Hyperscan, libphonenumber, and `nom`/`pest` are not similar libraries; they are independent confirmations of the same architecture.

Land the scaffolding, then let each capability adopt the recognizer it actually is. The parity gate guarantees you never diverge.

