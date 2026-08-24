# The Recognition Kernel — A Ground-Up Redesign of Paxman's Recognition Pipeline

**Date:** 2026-08-24
**Author:** Independent architecture review (first exposure to this repository)
**Mandate:** Revamp the recognition pipeline from scratch. Research alternative, better, scalable, universal, and future-proof recognition strategies by studying comparable libraries (not limited to Python), disregarding existing ADRs governing the recognition pipeline, and propose the target architecture — including changes outside the recognition layer where they produce a better Paxman. No source code was modified; all measurements were run read-only against the working tree.
**Evidence basis:**
- **Local source** (read, cited with file:line): `paxman/core/grammar/{pipeline,stages,boundary,lexicon,composer}.py`, `paxman/core/domain.py`, `paxman/engine/orchestrator.py`, all 15 capability `grammar/` packages (33+ grammars), `ARCHITECTURE.md`, `HOW_TO_ADD_NEW_CAPABILITY.md` §4, `docs/development/MILESTONE.md`, `benchmarks/baseline.json`, the in-flight `docs/adr/0009-staged-pipeline-extensions.md` draft (reviewed as an artifact, explicitly *not* treated as binding).
- **Measurements** (this review, reproducible — see Appendix A): whole-input lexicon restriction live-behavior probes; per-grammar scan cost across all 15 shipped capabilities; regex-alternation vs pure-Python dict-trie at real Paxman lexicon scales (650/820 tokens), including build cost and hit-dense corpora; Language lexicon table sizes.
- **External primary sources** (fetched 2026-08-24, cited inline): libphonenumber source at pinned commit; Hyperscan/Vectorscan, RE2, Rust `regex`/`regex-automata`/`RegexSet`, Go `regexp` docs; Aho–Corasick 1975 CACM paper, pyahocorasick, FlashText paper+benchmarks, ahocorapy, marisa-trie/datrie; UIMA OASIS spec, GATE user guide, spaCy docs + Explosion engineering blog, Lucene analysis package docs; ICU user guide + ICU4X design docs + docs.rs; Ragel guide, re2c manual, WHATWG URL Standard, pyparsing/Lark/nom/winnow/pest docs, tree-sitter docs; dateparser/chrono/dateutil/python-stdnum source; rustc dev guide (query system).

---

## Executive Summary

Paxman's recognition layer is **architecturally sound at its seams and structurally limited at its core**. The engine contract — span-bearing `RecognitionMatch`, within-grammar containment dedup, total document ordering, cross-grammar ambiguity preserved, semantics-routed validation with provenance — is correct and matches the best prior art in the field (it is, factually, a stricter version of what libphonenumber, UIMA, and GATE do). What limits the system is everything *below* that contract:

1. **Every grammar is an isolated program that rescans the full text.** There is no shared scan substrate — no tokenization, no normalized views with offset maps, no candidate positions. Fifteen capabilities × 33 grammars cost **~1.3 ms of pure recognition for a 68-character input** (measured), scaling linearly in text length and grammar count. The MILESTONE roadmap lists 30 capabilities; at current per-capability recognition cost (~87 µs average, si_unit at 376 µs) that trajectory is ~2.6 ms per short input before validation even starts.
2. **The lexicon story stops at ~800 tokens and at whole-input matching.** `WholeInputLookup` cannot see a country name embedded in prose — measured live: `"Ship to United States please"` resolves to **`SUCCESS "TO"` (Tonga)** because the name grammar is whole-input-only and the alpha-2 grammar fires on the preposition "to". Meanwhile regex alternation, the only in-text lexicon mechanism, degenerates measurably: a 650-token SI-unit alternation costs **6.6 ms on a 2.2 KB text** — 6.5× slower than a pure-Python dict trie over the same keys (measured, byte-identical semantics).
3. **The five-slot staged pipeline (`pre→regex→lexicon→composer→post`) forces every new recognition shape into one of five molds.** The evidence is in the tree: `Language/grammar/bcp47_tag_recognition.py` contains a 160-line positional parser inside a regex callback and a *duplicated private stage class* (`_BCP47RegexStage`) that exists solely to work around the pipeline's inability to scan a normalized view; URL and Phone smuggle scanners inside `PostStage` transforms; `PipelineState.scratch` — the ADR-designated channel for normalized views — is never written or read by any shipped stage.
4. **`stdlib re` is a ceiling, not a floor**: no `\p{...}` classes, no multi-pattern sets, backtracking semantics, and a giant alternation is O(alternatives × positions) in practice. All escape hatches (`regex`, `google-re2`, Hyperscan bindings, Rust `regex` via PyO3) are compiled extensions that violate the zero-runtime-dependency constraint.

The proposal — **the Recognition Kernel** — replaces "each grammar walks its own stage pipeline" with a three-layer model that every surveyed mature system converges on:

> **Scan once into a shared substrate; match with declarative matcher specs (regex / trie / scanner / combinator / property, all first-class); assemble centrally under the existing engine policy.**

- A **substrate** (`ScanContext`): immutable text, one C-speed word-boundary pass, lazily-built normalized views carrying offset maps (Lucene `CharFilter` discipline), shared by all matchers of a capability (and optionally all capabilities in one `scan()` call).
- **Matcher specs as data**: a frozen descriptor (`kind`, payload, declarative boundary, view selector, anchors, emit function) compiled once at registration freeze. The six stage types proposed by the in-flight ADR-0009 (NormalizedView, Automaton, Scanner, UnicodeProperty, FormatCandidate, GenericComposer, LabelStage) all become *special cases* of `{view × kind × combinator}` — one mechanism instead of seven.
- **A performance ladder** (libphonenumber's real lesson): anchor prefilter → shape match on substrate → notation construction → (existing) rule validation, with an optional `is_possible`-style cheap tier for diagnostics.
- **Measured, not assumed, matcher selection**: trie matchers for lexicons ≥ ~500 tokens (3–6.5× faster than alternation at shipped scales, with build cost parity); regex alternation for small/symbol lexicons; scanners for delimiter-balanced and window-bounded shapes; combinators for compositional shapes (BCP 47, SI compounds, Money adjacency).
- **Outside the recognition layer** (explicitly requested): a batch `scan()` API + first-class mention model that makes `"Ship to United States please"` produce *two observable mentions* instead of a silent wrong answer; compiled-capability semantics at registry freeze (rustc query-system discipline); snapshot→generate→verify data pipeline generalized ICU4X-style with version stamps and CI freshness gates; grammar-side lexicons *derived* from authority snapshots to kill the Currency/Money and BIC data duplication class.

Everything that is right today — the `Grammar`/`Rule` ABC surfaces, `RecognitionMatch`, semantics routing, ambiguity preservation, provenance-first validation, determinism — is kept untouched. The kernel is a replacement for *how recognition executes*, not for *what recognition promises*.

---

## Part I — Ground Truth: How Recognition Works Today, and Where It Breaks

### 1.1 The current shape (verified in source)

```
canonicalize(text, contract)
  └─ run_capability()                     paxman/engine/orchestrator.py
       └─ _recognize(text, all_grammars)  for each grammar: grammar.recognize(text)
            └─ PipelineGrammar.recognize  paxman/core/grammar/pipeline.py
                 state = PipelineState(text, matches=[], scratch={})
                 pre → regex → lexicon → composer → post   (fixed order, optional slots)
       └─ _dedup_spans (within-grammar longer-wins)
       └─ total order (start, end, active-index, grammar-name)
       └─ _collect_candidates (semantics-routed rule dispatch)
```

Each grammar is a `PipelineGrammar` subclass declaring at most one stage per slot (`paxman/core/grammar/pipeline.py:21-45`). Lexicon scanning compiles an `re.escape`-joined, longest-first alternation wrapped in lookaround guards (`paxman/core/grammar/lexicon.py:35-42`, `boundary.py`). `WholeInputLookup` (`stages.py:158-195`) tests the *entire trimmed input* against a normalized key set. `AmountComposer` fuses lexicon+amount either-order (`composer.py`). `PostStage` maps each match through a transform (`stages.py:130-155`).

### 1.2 Failure catalog

Each failure below is either measured in this review (marked **[M]**, Appendix A) or verified directly in source (marked **[S]**).

**F1 [M] — Whole-input lexicon matching cannot see embedded values, and short-code grammars silently fill the void.**

```
paxman.canonicalize("United States", Country.create_contract())
  → SUCCESS "US"                                   # whole-input lookup hits
paxman.canonicalize("Ship to United States please", Country.create_contract())
  → SUCCESS "TO"                                   # ← Tonga. Not AMBIGUOUS. Not an error.
```

Mechanism (verified by running the grammars directly): on the second input the *only* recognition is `alpha2_recognition, span=(5,7), raw='to' → CountryNotation(shape='alpha2', value='TO')`. The name grammar (`WholeInputLookup`) never fires because the input is not exactly a name; the two-letter preposition is a shape-valid alpha-2 code and ISO 3166 validates Tonga. The same probe on Language:

```
paxman.canonicalize("German", Language.create_contract())          → SUCCESS "de"
paxman.canonicalize("She speaks German fluently", ...)             → INVALID   # "She" matched as a 3-letter code shape; the name is invisible
```

This is the single most important finding of this review. It is not a performance issue or a style issue: **the current strategy gives a confident, provenance-backed, wrong answer on ordinary prose**, because (a) vocabulary matching is restricted to whole input and (b) nothing distinguishes a short code in running text from a short word. Any redesign that does not fix in-text vocabulary matching has missed the point.

**F2 [M] — O(grammars × text) rescan model.** Every grammar independently `finditer`s the full text; nothing is shared. Measured recognition-only cost for a 68-char input, all 15 capabilities: **~1.30 ms** (si_unit 376 µs / 3 grammars; language 175 µs; country 142 µs; …; url 11 µs). The committed `benchmarks/baseline.json` shows whole-pipeline p50s of 0.09–0.24 ms per capability — recognition is already the dominant fraction of several. Cost grows linearly with text length and with capability count; the roadmap adds 15+ more capabilities, several of them lexicon-heavy (Timezone abbreviations, MIME types, charsets, SPDX licenses, chemical elements, CSS colors, TLDs).

**F3 [M] — Regex alternation degenerates at lexicon scale.** Measured, SI-unit tables, semantics byte-identical (sanity cross-check passed):

| Corpus | regex alternation (650 names) | dict trie | ratio | regex alternation (820 symbols) | dict trie | ratio |
|---|---|---|---|---|---|---|
| 50 chars, no hits | 165 µs | 42 µs | 3.9× | 168 µs | 55 µs | 3.0× |
| 430 chars, hit-dense | 545 µs | 156 µs | 3.5× | 1,051 µs | 442 µs | 2.4× |
| 2.2 KB prose | 6,637 µs | 1,020 µs | 6.5× | 6,609 µs | 1,049 µs | 6.3× |

Build cost at 650 tokens: regex compile 3.8 ms vs trie build 3.1 ms — parity. So at *today's* largest shipped lexicon, a naive pure-Python trie already wins 2.4–6.5×, and the gap **widens** with text length and lexicon size (alternation is O(positions × alternatives); trie scan is O(text) with word-start anchoring). This independently corroborates the published FlashText crossover (~500 keywords, below which regex wins — [FlashText paper](https://ar5iv.labs.arxiv.org/html/1711.00046), [Alibaba Cloud summary](https://www.alibabacloud.com/blog/data-analysis-flashtex-or-regex_594835)). Note the previous in-repo study's pessimism about pure-Python tries is not supported at Paxman's actual scales when the trie is word-anchored (FlashText's own model — iterate word starts, not characters — which is exactly what makes it pure-Python-fast).

**F4 [S] — The fixed five-slot pipeline leaks.** Workarounds shipped in tree:
- `Language/grammar/bcp47_tag_recognition.py:225-261` — `_BCP47RegexStage`, a private duplicate of `RegexStage` that scans an underscore→hyphen-normalized copy of the text while slicing `raw_text` from the original. It exists because `PipelineState.text` is immutable (correctly), `scratch` is never threaded (the ADR's normalized-view hook is dead code), and `RegexStage` cannot opt into another view. The pipeline's contract forced a copy-paste fork of core machinery inside a capability.
- `Language/grammar/bcp47_tag_recognition.py:61-222` — `_bcp47_notation`, a ~160-line hand-written positional parser (extlang/script/region/variant/extension/privateuse state machine with three while-loops and defensive breaks) living inside a regex callback. This is a parser with no home: too complex for `notation_fn`, forbidden from being a stage (no slot fits), invisible to the type checker as a unit, and untestable except through regex matches.
- URL paren-balance and Phone E.164 15-digit-window trimming both live in `PostStage` transforms — they are scanners wearing a post-processor's coat (both mutate spans based on text content *after* the regex has already over-matched).

**F5 [S] — Boundary logic is regex lookarounds compiled into patterns.** Eleven `BoundaryGuard` factories (`paxman/core/grammar/boundary.py`) encode boundaries as lookbehind/lookahead strings interleaved into every scanning pattern. Consequences: boundaries are evaluated by the regex engine at scan positions (not just at hit positions); they cannot be reasoned about as data; two guards are already special-cased as "consuming, not zero-width, not interchangeable" (`ipv6_token`, `isbn10_lead`); and every new capability adds variants (Phone `national` is a 4-lookbehind chain).

**F6 [S] — One mention per call is structural.** `_enforce_single_value_invariant` + `MultipleMentionsError` (ADR-0004) mean multi-entity input must be split by the caller (`docs/recipes/segmentation.md`). Combined with F1 this produces the worst interaction: the *only* way today to find "United States" inside prose is to know where it is beforehand.

**F7 [S] — stdlib `re` is a hard ceiling.** No `\p{...}` Unicode property classes (open CPython issue [gh-95555](https://github.com/python/cpython/issues/95555); docs redirect to the third-party [`regex`](https://pypi.org/project/regex) module); no multi-pattern set execution; backtracking engine with left-to-right alternation (each scan position tries alternatives one by one — [ordered-choice semantics](https://learnbyexample.github.io/py_regular_expressions/alternation-and-grouping.html)); catastrophic-backtracking risk only partially mitigated by 3.11's atomic groups/possessive quantifiers ([What's New in 3.11](https://docs.python.org/3.11/whatsnew/3.11.html)). Every escape hatch adds a compiled extension: `regex` (backtracking, non-linear guarantees), `google-re2` (official binding, C++ toolchain, Windows unsupported — [PyPI](https://pypi.org/project/google-re2)), `pyre2` forks (abandoned 2019), Hyperscan/Vectorscan and Rust-`regex` bindings (no maintained mainstream Python exposure).

**F8 [S] — Data duplication between recognition keys and authority tables is manual.** `Currency` and `Money` each carry copies of `SYMBOL_TOKENS`/`WORD_TOKENS` generated from the shared snapshot (good — generated), but `BIC/grammar` embeds a 250-entry `_COUNTRY_CODES` frozenset duplicating `rules/iso_9362_ed2022.COUNTRY_CODES` (hand-maintained), and Language's grammar-side name keys (77) are a separate catalog from the rule-side ISO/IANA tables (995 + 420 + 215 entries). The consistency-test convention catches drift per capability, but the duplication itself is architectural: recognition keys are a *projection* of authority data and should be derived as such.

---

## Part II — Prior Art: What Eight Mature Systems Do Differently

### 2.1 libphonenumber — the canonical "find in free text → validate" pipeline

Source pinned at `17c9061a` ([google/libphonenumber](https://github.com/google/libphonenumber)); Python port [daviddrysdale/python-phonenumbers](https://github.com/daviddrysdale/python-phonenumbers).

- **Matcher = one bounded regex + verify + inner-match retry, with non-overlapping advance.** `PhoneNumberMatcher` scans with a single pre-compiled `PATTERN` whose every component is *length-capped* (leading punctuation ≤2, digit blocks ≤ `MAX_LENGTH_FOR_NSN + MAX_LENGTH_COUNTRY_CODE` = 20) precisely to bound worst-case work ([PhoneNumberMatcher.java L28-L146](https://github.com/google/libphonenumber/blob/17c9061/java/libphonenumber/src/com/google/i18n/phonenumbers/PhoneNumberMatcher.java)). Candidates then pass `extractMatch` → `parseAndVerify` → `extractInnerMatch` (retry on split pieces); on success the search index advances to `lastMatch.end()` ([L420-L430](https://github.com/google/libphonenumber/blob/17c9061/java/libphonenumber/src/com/google/i18n/phonenumbers/PhoneNumberMatcher.java)). Matches carry `(start, end=start+len(raw), raw_string)` — Paxman's exact `RecognitionMatch` shape, arrived at independently.
- **False-positive suppression is matcher-level data, not ad-hoc code**: `SLASH_SEPARATED_DATES`, `TIME_STAMPS` (+suffix lookahead), `PUB_PAGES`, `MATCHING_BRACKETS` guards reject date-shaped and citation-shaped digit runs *inside the matcher* ([L40-L80, L263-L291](https://github.com/google/libphonenumber/blob/17c9061/java/libphonenumber/src/com/google/i18n/phonenumbers/PhoneNumberMatcher.java)). This is the direct answer to Paxman's "to → Tonga" class of problem: suppression rules are declarative, testable matcher inputs.
- **All per-region behavior is data.** ~240 territories are `<territory>` XML rows with `generalDesc`/per-type `nationalNumberPattern` regexes, `possibleLengths` tables, and `availableFormats`; compiled to per-region protobufs loaded on demand. Zero per-region code paths ([PhoneNumberMetadata.xml](https://github.com/google/libphonenumber/blob/17c9061/resources/PhoneNumberMetadata.xml), [phonemetadata.proto](https://github.com/google/libphonenumber/blob/17c9061/resources/phonemetadata.proto)).
- **Two-tier validation**: `isPossibleNumber` (length-table check only — "much faster") vs `isValidNumber` (length + prefix-pattern) — a cheap prune tier *before* the authoritative decision ([PhoneNumberUtil.java L2378-L2742](https://github.com/google/libphonenumber/blob/17c9061/java/libphonenumber/src/com/google/i18n/phonenumbers/PhoneNumberUtil.java)).
- **Degenerate-input guards**: `maxTries` bounds candidate retries on adversarial text; `RegexCache(32/100)` avoids recompilation.

Borrow: bounded patterns, matcher-level suppression data, two-tier prune, non-overlap advance. Reject: single-best-match semantics (collapses ambiguity — Paxman's `AMBIGUOUS` must survive).

### 2.2 Multi-pattern engines — Hyperscan/Vectorscan, RE2, Rust `regex`

- **Single-pass many-pattern is real and proven** — by *compiling the union of patterns into one automaton at build time*, not by looping: Hyperscan compiles up to tens of thousands of patterns into a hybrid DFA/NFA/SIMD database with literal-acceleration skipping ([Vectorscan README](https://github.com/VectorCamp/vectorscan), [runtime docs](https://intel.github.io/hyperscan/dev-reference/runtime.html)); Rust `regex` achieves linear time via lazy DFA + NFA simulation ([regex-automata hybrid module](https://docs.rs/regex-automata/latest/regex_automata/hybrid/index.html)) and `RegexSet` matches many patterns in one haystack pass ([docs.rs](https://docs.rs/regex/latest/regex/struct.RegexSet.html)); RE2 excludes backtracking constructs outright ([syntax](https://github.com/google/re2)).
- **But all of them suppress ambiguity at the engine level.** Go/RE2/Rust default to leftmost-first (or POSIX leftmost-longest) — *one* winner per position ([Go regexp docs](https://pkg.go.dev/regexp)). `RegexSet` reports *which* patterns matched but not where, and its own docs recommend a second per-pattern pass for spans. Hyperscan reports every occurrence via callback, but is a C library.
- **Published numbers are scale numbers** (multi-Gbps DPI at 1,300–3,600 patterns — [NSDI'19 paper](https://www.usenix.org/system/files/nsdi19-wang-xiang.pdf)); at Paxman's haystack sizes (tens–thousands of chars) per-scan constants dominate, and the maintainers themselves say to benchmark your own workload.
- **Python reality:** no stdlib set-matching; every binding (`google-re2`, Hyperscan, Rust via PyO3) is a compiled extension incompatible with zero-dependency distribution.

Borrow: the *literal-prefilter + automaton* insight (a cheap necessary-condition test before an expensive matcher), and compile-the-union-at-build-time as a discipline (matcher compilation at registry freeze). Reject: adopting any of these engines as a dependency; leftmost-winner semantics.

### 2.3 The Aho–Corasick / trie family — large-lexicon matching

- Theory: Aho & Corasick 1975 — search O(n + z) independent of keyword count, build O(sum of keyword lengths) ([CACM](https://dl.acm.org/doi/10.1145/360825.360855)).
- FlashText (pure Python!) is the existence proof that matters here: a dict-based trie over *word tokens* with boundary markers, O(N) in text regardless of keyword count, 82× faster than regex at 15k keywords on a 10k-word document; published crossover ~500 keywords ([paper](https://ar5iv.labs.arxiv.org/html/1711.00046), [benchmark gist](https://gist.github.com/vi3k6i5/604eefd92866d081cfa19f862224e4a0)). Its speed comes from iterating words, not characters — the trie is only entered at word starts.
- pyahocorasick: C extension, overlapping by default, `iter_long` for longest-non-overlapping, picklable automata ([docs](https://pyahocorasick.readthedocs.io/en/latest/)). Pure-Python AC implementations are 5–10× slower than C on dense hits ([ahocorapy comparison](https://github.com/FrederikP/ahocorapy)) — but word-anchored dict tries (FlashText model) sidestep the per-character Python loop, which is why my measurement shows the pure-Python trie beating C regex alternation 2.4–6.5× at 650–820 tokens.
- marisa-trie/datrie: memory-optimized *membership* structures (50–100× smaller than dict), not scanners ([marisa-trie](https://github.com/pytries/marisa-trie), [datrie](https://pypi.org/project/datrie/)).

Borrow: word-anchored dict-trie scanning as the default lexicon matcher above ~500 tokens; keyword→canonical mapping as leaf payload (FlashText's `add_keyword(unclean, clean)` is prior art for the grammar-key → rule-mapping split done right). Reject: C-extension dependencies; word-boundary-only semantics for symbol lexicons (FlashText cannot match `$` inside `$100` — symbols stay on regex alternation).

### 2.4 Annotation frameworks — UIMA, GATE, spaCy, Lucene

- **UIMA**: the CAS is a shared standoff annotation store — the artifact is *never* mutated; typed annotations with `begin/end` point into a Sofa; annotators declare input/output types as metadata; indexes make span queries (`coveredBy`, `following`) cheap ([OASIS spec §3.1-4.3](https://docs.oasis-open.org/uima/v1.0/os/uima-spec-os.html)). Multiple *views* hold alternative representations of the artifact (raw vs detagged) — the sanctioned answer to normalized views.
- **GATE/ANNIE**: tokenise once → gazetteer lookup (compiled FSM over lists) → JAPE grammar over token+lookup annotations — each stage *adds* annotations, none rewrites text ([GATE user guide ch.4-6](https://gate.ac.uk/sale/tao/splitch4.html)).
- **spaCy**: `Doc` is the single shared substrate; components are `Doc → Doc` functions; `PhraseMatcher` matches large terminology lists by trie over token hashes (attr=`LOWER` for case folding) — "very fast" because matching is per-token, not per-character ([docs](https://spacy.io/api/phrasematcher), [Explosion blog](https://explosion.ai/blog/spacy-v2-2)); `EntityRuler` merges phrase lists + token patterns with an explicit overlap policy ("prioritizes longer patterns over shorter, and if equal the match occurring first" — [docs](https://spacy.io/api/entityruler)). Pitfalls are documented: ordering dependencies between components are real and must be declared.
- **Lucene**: the analysis chain is a *declared fixed order* `CharFilter* → Tokenizer → TokenFilter*` with a hard correctness rule — char filters must track corrected offsets; token filters must not modify offsets ([analysis package docs](https://lucene.apache.org/core/9_8_0/core/org/apache/lucene/analysis/package-summary.html)). Twenty-plus years of durability from exactly that discipline.

Borrow: the shared-substrate-with-standoff-annotations model; declared component contracts; Lucene's offset-correctness rule for every normalized view; EntityRuler's longest/earliest overlap policy as *declared data*. Reject: the framework weight (type systems, container models, ML legs).

### 2.5 ICU / ICU4X — data-driven canonicalization machinery

- **UnicodeSet**: property classes as *data* — sorted-range inversion lists with set algebra and `span()` — no regex engine involved ([ICU user guide](https://unicode-org.github.io/icu/userguide/strings/unicodeset.html)). ICU4X provides `CodePointInversionList` + `CodePointTrie` as zero-copy readers over baked data ([docs.rs/icu_collections](https://docs.rs/icu_collections/latest/icu_collections/codepointtrie/struct.CodePointTrie.html)).
- **LocaleCanonicalizer** — the closest industry analog to Paxman's Language capability — implements UTS #35 Annex C: parse into subtags, apply CLDR alias tables (`languageAlias`/`scriptAlias`/`territoryAlias`/`variantAlias`) with longest-match substitution and territory exceptions, then canonical syntax — a pure function over structured identifiers driven entirely by versioned data ([docs.rs](https://docs.rs/icu_locale/latest/icu_locale/struct.LocaleCanonicalizer.html), [UTS #35 Annex C](https://unicode.org/reports/tr35/#LocaleId_Canonicalization)).
- **DataProvider**: data payloads are baked-at-build (dead-code-eliminable), or postcard blobs, with a CI discipline of "check in data, verify freshness by re-generation diff" ([data management tutorial](https://icu4x.unicode.org/2_1/tutorials/data-management/)).
- Python stdlib `unicodedata` gives only per-code-point predicates — no sets, no tries, no CLDR ([docs](https://docs.python.org/3/library/unicodedata.html)); PyICU is a C++ extension. So build-time generated tables are the *correct* stdlib-only answer, exactly as Paxman's `tools/regenerate_*` precedent already does.

Borrow: property classes as generated range data; alias-table canonicalization for Language; snapshot→generate→verify CI discipline with embedded source+version stamps.

### 2.6 Scanner and parser machinery — Ragel, re2c, WHATWG, pyparsing/Lark, nom/winnow/pest

- **Ragel**: embeds user actions into DFA transitions — "state-chart compiler" ([guide](https://www.colm.net/files/ragel/ragel-guide-6.11.pdf)); **re2c**: generates switch-based DFA scanners used by PHP/Hack — the auditability win is that the scanner is a diffable, visualizable artifact ([re2c.org](https://re2c.org/)).
- **WHATWG URL Standard**: a pointer-based state machine over code-point classes with ~30 *non-fatal* validation-error types — errors are diagnostics that flow out with the parse, not exceptions ([url.spec.whatwg.org](https://url.spec.whatwg.org/)). This is prior art for Paxman's INVALID-with-provenance posture at the *recognition* layer.
- **pyparsing/Lark** both offer span-preserving scanning of embedded matches: `scan_string → (tokens, start, end)` ([docs](https://pyparsing-docs.readthedocs.io/en/latest/pyparsing.html)) and `Lark.scan → ScanMatch(range=(start,end))` LALR-only, silently skipping non-matches ([docs](https://lark-parser.readthedocs.io/en/latest/classes.html)). Both are pure-Python and slow at scale — but their *API shapes* are validated prior art for a first-class scan seam.
- **nom/winnow/pest**: the combinator model — small recognizers with signature `(input, pos) → (new_pos, value) | None`, composed by `alt/seq/opt/many`, with `span()`/`with_span()` wrappers capturing ranges as a first-class concern ([nom docs](https://docs.rs/nom/latest/nom/), [winnow Parser trait](https://docs.rs/winnow/latest/winnow/trait.Parser.html)).
- **tree-sitter**: borrow only the error-node discipline (useful partial results + cost metadata); incremental GLR reparsing is the wrong problem for a canonicalization library ([docs](https://tree-sitter.github.io/tree-sitter/)).

Borrow: declarative scanners with actions; non-fatal validation errors; combinator composition with span capture. Reject: code generation steps, C runtimes, full parse forests.

### 2.7 Multi-strategy parsers — dateparser, chrono-node, dateutil, stdnum

- **dateparser**: locale detection → translation tables → regex chain, with all per-locale data *generated* from CLDR JSON + YAML ([contributing docs](https://dateparser.readthedocs.io/en/latest/contributing.html)). Anti-pattern: ordered first-match-wins `PARSERS` with no emitted alternatives — outcomes depend silently on list position ([settings](https://dateparser.readthedocs.io/en/latest/settings.html)).
- **chrono-node**: the **parsers → refiners** two-phase architecture — independent parsers emit `(index, text, components)` candidates; fixed-order refiners cull overlaps (keep longer), merge adjacent date+time, enrich timezones late ([chrono.ts](https://github.com/wanasit/chrono/blob/master/src/chrono.ts), [OverlapRemovalRefiner](https://github.com/wanasit/chrono/blob/master/src/common/refiners/OverlapRemovalRefiner.ts)). Anti-pattern: merge refiners *rewrite* spans, erasing which parser produced what — provenance loss.
- **python-dateutil**: caller-supplied disambiguation flags (`dayfirst`/`yearfirst`) with closed, documented semantics — but `fuzzy=True` silently swallows unknown tokens and returns one result ([parser docs](https://dateutil.readthedocs.io/en/stable/parser.html)).
- **python-stdnum**: 200+ identifier formats as a *convention* (`compact/validate/is_valid/format` + typed error hierarchy) with almost no shared machinery — scale achieved by duplication; signatures and semantics drift across modules ([docs](https://arthurdejong.org/python-stdnum/), [iban.py](https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/iban.py)). The counter-example to Paxman's unified-contract approach — and validation of it.

### 2.8 rustc's query system — the compiler-grade architecture pattern

The Rust compiler replaced sequential passes with **memoized pure queries forming an explicit DAG**; results are cached by key, dependencies are recorded, and recomputation is demand-driven ([rustc dev guide](https://rustc-dev-guide.rust-lang.org/query.html), [query evaluation model](https://rustc-dev-guide.rust-lang.org/queries/query-evaluation-model-in-detail.html)). The transferable discipline for Paxman: **treat each derived artifact (compiled matcher, normalized view, trie, word-span index) as a pure function of immutable inputs (text, snapshot), computed once on demand and identified by its inputs** — the deterministic-replay story then has a formal skeleton. (Paxman already believes this — `VersionStamp`, frozen registry; the kernel makes recognition *structurally* conform.)

### 2.9 Synthesis — five convergent lessons

Every system that survived contact with scale does the same five things:

1. **One shared substrate, computed once, never mutated** (CAS, Doc, TokenStream, metadata protos). Standoff annotations/views point into it with offset discipline.
2. **Matching behavior is data** (metadata tables, gazetteer lists, UnicodeSet ranges, analyzer configs) — adding a region/format/lexicon is a data change, not a code change.
3. **Cheap tiers before expensive tiers** (literal prefilters, `is_possible`, quick-check spans) — with bounds everywhere (`maxTries`, length caps) against degenerate input.
4. **Assembly policy is centralized and declarative** (overlap/precedence rules as data — EntityRuler "longer first, then earliest"; Lark's total terminal sort) — never distributed across matchers.
5. **Errors are diagnostics, not crashes** (WHATWG validation errors; stdnum typed exceptions converted to reasons) — the pipeline keeps going and reports what it saw.

Paxman today has (5) partially (INVALID/MISSING/AMBIGUOUS) and none of (1)–(4) inside recognition.

---

## Part III — The Proposal: The Recognition Kernel

### 3.1 Design goals and non-goals

**Goals**
- G1 — Fix F1: in-text vocabulary matching, first-class.
- G2 — Fix F2/F3: shared scan substrate + measured matcher selection; recognition cost per capability independent of lexicon size.
- G3 — Fix F4: every recognition shape gets a first-class home — regex, lexicon/trie, scanner, combinator, property class — no more private stage forks or 160-line regex callbacks.
- G4 — Universal enough for all 30 roadmap capabilities without new machinery per capability.
- G5 — Zero runtime dependencies; deterministic; byte-identical-parity migratable.
- G6 — The engine contract stays: `RecognitionMatch`, dedup/order/ambiguity policy, semantics routing, provenance.

**Non-goals** — ML/NER, fuzzy matching, context-sensitivity beyond declarative suppression data, multi-pattern DFA engines as dependencies, tree-sitter-style incremental parsing. (Rejected with reasons in Part VI.)

### 3.2 Architecture overview

```
                         ┌────────────────────────────────────────────────┐
                         │  Registration freeze ("capability compile")    │
                         │  MatcherSpec (data) ──► compiled Matcher       │
                         │  (trie built, regex compiled, closures bound;  │
                         │   rustc-query discipline: pure fn of snapshot) │
                         └────────────────────────────────────────────────┘

canonicalize(text, contract)
   │
   ▼
┌───────────────────────────── Recognition Kernel ─────────────────────────────┐
│  L0  Substrate (ScanContext)          — computed once per call               │
│      text (immutable)                                                        │
│      word_spans   ← one C-speed \w+ pass (shared by all matchers)            │
│      views{}      ← lazily: ("lower" | "fold" | custom) + offset map         │
│                                                                               │
│  L1  Match loop (engine-owned)                                               │
│      for each active grammar's matcher:                                      │
│        T0 anchor prefilter   — necessary literals/classes present? (C-speed) │
│        T1 shape match        — regex / trie / scanner / combinator on view   │
│        T2 emit               — RecognitionMatch(notation, start, end, raw)   │
│           (spans always relative to ORIGINAL text; views carry offset maps)  │
│                                                                               │
│  L2  Assembly (existing engine policy — unchanged)                           │
│      within-grammar containment dedup ("longer wins")                        │
│      total order (start, end, active-index, grammar-name)                    │
│      cross-grammar ambiguity preserved                                       │
└───────────────────────────────────────────────────────────────────────────────┘
   │
   ▼
  _collect_candidates → rules → provenance → format_value     (unchanged)
```

### 3.3 The substrate — `ScanContext`

The minimal shared structure, deliberately *dumber* than spaCy's `Doc` (no POS, no lemmas, no vectors — determinism and zero-dep forbid):

```python
@dataclass(frozen=True, slots=True)
class ScanContext:
    text: str                                   # original, immutable
    word_spans: tuple[tuple[int, int], ...]     # one re.finditer(r"\w+") pass, C-speed
    _views: dict[str, View]                     # lazy, keyed by view name

    def view(self, name: str, normalizer: Callable[[str], str]) -> View: ...
    # View = (subject: str, offsets: tuple[int, ...] | None)
    #   length-preserving normalizers → offsets=None (identity, zero cost)
    #   length-changing normalizers  → offsets maps subject→original
```

Design decisions:

- **D1 — Word spans are the only eagerly-computed index.** A single `re.finditer(r"\w+")` over the text is one C-level pass costing ~1 µs per KB (measured: the `word_spans` pass is cheaper than any single shipped grammar's scan). Every word-anchored matcher — tries, code grammars, name grammars — consumes it instead of re-deriving boundaries. This is GATE's "tokenise once" and FlashText's "iterate words, not chars."
- **D2 — Normalized views are lazy and offset-disciplined** (Lucene `CharFilter` rule). A view is `(subject, offsets)`; matchers scan `subject` but emit `raw_text = text[translate(start):translate(end)]`. Length-preserving views (lower, `_→-`, accent-strip-by-table, separator-strip-by-table) have `offsets=None` and cost nothing at emit time. The Language `en_US→en-US` case, Country `normalize_name` lookup-key folding, and Phone `strip_separators` all become views instead of grammar-local mutations. This *subsumes* the in-flight "NormalizedViewStage + source threading" proposal with strictly less machinery (no `scratch` protocol, no per-stage `source` flags — the view is an argument).
- **D3 — One substrate per `canonicalize()` call** (v1, per capability — the contract gates which grammars run); one substrate per `scan()` call across capabilities (Part IV).

### 3.4 Matcher specs — recognition as data

A grammar becomes a thin declaration over matcher specs. One `MatcherSpec` kind per recognition strategy, all first-class:

```python
@dataclass(frozen=True, slots=True)
class MatcherSpec(Generic[NotationT]):
    kind: Literal["regex", "lexicon", "scanner", "combinator", "property"]
    payload: ...            # pattern: str | tokens: tuple[str, ...]
                            #   | scan: ScannerFn | expr: CombExpr
    view: str | None        # None = original text; else view name (D2)
    boundary: BoundarySpec  # declarative, see D4
    anchors: AnchorSet      # literal/class necessary conditions (D5)
    emit: EmitFn            # (raw_span, context) -> NotationT
```

- **D4 — `BoundarySpec` is data, not lookarounds.** `BoundarySpec(left=CharClass.WORD, right=CharClass.WORD | CharClass.DIGIT)` or `word_sign`, `digit`, custom class tuples. The kernel resolves boundaries as *checks at hit positions* (`context.check(start, end, spec)` — O(hits)), not as lookarounds compiled into scanning patterns (O(positions)). The eleven `BoundaryGuard` factories become a table of `BoundarySpec` values; the consuming-lookaround special cases (`ipv6_token`) become scanner-kind specs where consuming anchors are natural. Property classes for boundary/`property` specs come from **generated range tables** (the ICU UnicodeSet lesson): `tools/regenerate_unicode_property_data.py` emits sorted-range tuples; membership is `bisect` — no `\p{...}` needed, no `regex` dependency.
- **D5 — `anchors` are the cheap tier.** Each matcher declares necessary conditions: literal substrings (`":"` for URL, `"@"` for email), char-class presence (`HAS_DIGIT` for phone/money/date), or lexicon first-character sets (a trie's first-level keys double as a `frozenset[str]` membership prefilter). The kernel evaluates anchors with C-speed primitives (`str.find`, one `re.search` per class) and skips the matcher entirely when they fail. This is Hyperscan's literal-acceleration insight in stdlib form, and it is what makes 30-capability scale affordable: most matchers on most texts cost one failed `find`.
- **D6 — `lexicon` kind switches representation by size** (measured, F3): `≤ ~500` tokens → regex alternation (C engine wins at small scale — FlashText crossover); `> ~500` → word-anchored dict trie (pure Python wins 2.4–6.5× at 650–820 tokens, gap grows with size). Both representations emit byte-identical match sequences (parity-tested), so the switch is invisible above the matcher. Symbols and other non-word lexicons pin `representation="alternation"`. Leaf payloads carry keys only (the grammar/rule boundary is unchanged — authority mapping stays in `rules/data/`).
- **D7 — `scanner` kind gives complex shapes a home.** `ScannerFn = (context, pos) -> (end, NotationT) | None`. The kernel's loop: try scanner at each candidate position, advance to `end` on hit, `pos + 1` on miss (libphonenumber's advance discipline). URL paren-balance (depth counter), Phone E.164 15-digit window, IPv6 consuming delimiters, and the entire BCP-47 subtag walk become scanners — testable functions with typed inputs, no longer regex callbacks or `PostStage` transforms. Scanners may consume views (D2) and read `word_spans`.
- **D8 — `combinator` kind composes matchers.** A minimal expression tree (`seq`, `alt`, `opt`, `rep`, `label`) over child specs, evaluated left-to-right with span capture (the nom/winnow `IResult` model, rendered in Python). Money's either-order lexicon±amount, SIUnit's `UNIT(SEP UNIT){1,3}`, IBAN's optional label, and BCP-47's `langtag ["-" script] ["-" region]…` become combinator expressions. Ordered choice (`alt`) is *documented* as deterministic-first-branch-wins (pest's discipline), and — critically — combinator `alt` at the *grammar* level still routes to distinct semantics so cross-branch ambiguity stays observable downstream.

The key property: **the in-flight ADR-0009 taxonomy (NormalizedView, Automaton, Scanner, UnicodeProperty, FormatCandidate, GenericComposer, LabelStage) is exactly `{view × kind × combinator}`** — seven proposed stage types collapse into three orthogonal axes. One mechanism, fewer concepts, and nothing left that needs a private fork.

### 3.5 The performance ladder

libphonenumber's real lesson, generalized:

| Tier | What | Cost model | Failure mode |
|---|---|---|---|
| T0 | anchor prefilter | O(1) C-speed per matcher | matcher skipped |
| T1 | shape match (regex/trie/scanner/combinator on substrate) | O(text) or O(words), bounded by pattern caps | no match |
| T2 | notation emit | O(hits) | — |
| T3 | rule validation (existing) | per-candidate | INVALID |

Every pattern carries **bounds** (max digit-run, max repetition) as matcher data — the `digitBlockLimit` discipline that keeps libphonenumber linear on adversarial input. An optional `possible` predicate per spec (length/shape quick check) surfaces libphonenumber-style reason codes as diagnostics without changing MISSING/INVALID semantics.

### 3.6 Assembly — what stays exactly as-is

`_dedup_spans` (within-grammar longer-wins), the total order `(start, end, active-index, grammar-name)`, cross-grammar ambiguity preservation, `single_value`, semantics routing, `_filter_rules`, provenance collection, `format_value`. The kernel replaces only the *production* of recognitions. The parity harness (`tests/property/test_grammar_stage_parity.py`) remains the migration gate, now asserting kernel-vs-legacy byte equality per grammar.

### 3.7 The F1 fix, concretely

- Country `name_recognition` migrates from `WholeInputLookup` to a `lexicon` matcher over the multi-word key trie (longest-match at word starts, spanning spaces): `"United States"` inside prose **is recognized**, with its true span.
- The `to → TO` false positive is addressed by *making the competition visible*: the engine now sees two mentions; `single_value` raises `MultipleMentionsError` on a contract that asks for one value (honest failure), and the batch `scan()` API (Part IV) returns both mentions with spans for caller-side adjudication.
- Optionally, suppression data (libphonenumber's date-guard pattern): a generated high-frequency-English-word table consulted by *short-code* matchers as a contract-gated `suppress_common_words` flag. This is deterministic and auditable, but it is policy — so it ships off by default and is provenance-neutral (a suppressed recognition is simply not emitted; nothing validates to a wrong answer silently).

### 3.8 Capability mapping (all 33 grammars + roadmap)

| Capability | Today | Kernel mapping |
|---|---|---|
| Date ×4 | regex + digit guards | 4 `regex` specs under one grammar (or one `alt` combinator — semantics routing decides) |
| Email ×3 | regex + `\b` | `regex` + anchors (`"@"`); obfuscated = combinator over word lexicon |
| IP ×2 | regex | v4 `regex`; v6 `scanner` (consuming delimiters natural here) |
| ISBN/ISSN/ORCID/IBAN/BIC | regex + label lookarounds | `label` combinator (optional label + separator policy as data) + `regex` core |
| Country ×4 | 3 regex + whole-input lookup | 3 `regex`; names → `lexicon` trie (multi-word, view=`normalize_name`) — **F1 fixed** |
| Currency/Money ×6 | alternation + AmountComposer | small lexicons stay `regex`; Money adjacency → `combinator(seq(alt(lex, amount)))` |
| SIUnit ×3 | giant alternations + inline split-prefix | `lexicon` **trie** (820/650 tokens — measured win) + compound `combinator`; split-prefix = `alt` of `seq(prefix_view, unit)` |
| Phone ×4 | regex + PostStage LRU trim | `scanner` (bounded digit windows; window logic as scanner data) + anchors `HAS_DIGIT` |
| URL ×1 | regex + PostStage paren trim | `scanner` (WHATWG-style state walk: scheme, depth-counter parens, bare-scheme drop) + anchor `":"` |
| Language ×3 | private stage fork + 160-line callback | **the flagship migration**: `scanner` walking subtags over view(`_→-`) + `combinator` for tag assembly + `lexicon` trie for names (ISO 639-3 at 995 keys → trie tier) |
| Roadmap: Timezone, MIME, charset, SPDX, elements, colors, TLDs | (not built) | pure data: trie lexicons + registry snapshots — zero new machinery |
| Roadmap: UUID, MAC, semver, LEI, credit card | (not built) | `label`/`regex` specs — zero new machinery |

### 3.9 Relationship to the in-flight ADR-0008/0009 direction

The in-flight direction (seven new stage types inside the fixed five-slot pipeline) treats each symptom separately and keeps per-grammar independent scanning. The kernel subsumes all seven (§3.4 D-note) while additionally fixing what that direction does not touch: in-text lexicon matching (F1), the rescan model (F2), and boundary-as-lookaround (F5). Where this review's *measurements* contradict the in-flight study — pure-Python trie viability — the measured data (F3, 2.4–6.5× wins, build parity) should be treated as authoritative over both studies' priors.

---

## Part IV — Changes Outside the Recognition Layer (requested)

**4.1 Batch `scan()` API + first-class mention model.** `paxman.scan(text, contracts: Sequence[CapabilityContract]) -> ScanResult`, where `ScanResult` carries per-capability `Mention` records (span, grammar, notation, resolved candidates when a single-mention contract applies). One substrate pass serves all capabilities. This turns `docs/recipes/segmentation.md` from a caller obligation into an API, fixes the F1 interaction with `MultipleMentionsError` (the error becomes "use `scan()`" with the mentions already computed), and is the natural CLI surface (`paxman scan file.txt`). Mention = a maximal cluster of recognitions under the existing total order + containment policy — the concept `_enforce_single_value_invariant` already gestures at, now typed and exposed.

**4.2 Compiled capabilities at registry freeze.** At `freeze_registry()`, every active grammar's `MatcherSpec` compiles to a `Matcher` (trie built, regex compiled, scanner closures bound) and the compiled set is hashed into the snapshot identity. This formalizes the determinism guarantee structurally (rustc query discipline): a compiled matcher is a pure function of (spec, snapshot); the `VersionStamp` gains a `recognition_revision` derived from the compiled set. Community `register_grammar` extensions compile through the same seam.

**4.3 Data pipeline formalization (ICU4X pattern).** Generalize the `shared_data/` + `regenerate_*` + consistency-test precedent into one rule: **every generated module embeds `Source / Version / SHA` in its header; CI regenerates and diffs — fail on drift** ([ICU4X data-management tutorial](https://icu4x.unicode.org/2_1/tutorials/data-management/)). New snapshots on this rail: IANA language subtag registry, ISO 639-2/-3, CLDR aliases (for Language per UTS #35 Annex C), Unicode property ranges, and the English-frequency/suppression table if §3.7's flag ships.

**4.4 Recognition keys derived from authority tables.** Grammar-side lexicons that are projections of rule-side authority data (Currency/Money symbols-words from the CLDR snapshot — already generated; BIC `_COUNTRY_CODES` from ISO 9362 rule data — currently hand-duplicated; Language name keys from CLDR display names) become *generated projections* with a single source of truth. The grammar/rule semantic boundary is untouched (keys stay key-only); the duplication class of bugs (F8) disappears.

**4.5 Testing.** Three strata: (a) matcher unit tests (trie vs alternation byte-parity on golden corpora + property tests); (b) kernel-vs-legacy parity per grammar (extends the existing harness); (c) substrate equivalence property — for every shipped grammar, kernel recognition equals direct-scan recognition on Hypothesis-generated inputs. Performance: add a recognition-only scenario family to `benchmarks/` (scan-cost per capability at 64 B / 2 KB / 16 KB) — informational as today, but now measuring the right thing.

---

## Part V — Migration and Delivery

Phased, parity-gated, reversible:

- **Phase 0 (foundation):** land `ScanContext` (views + word spans) and `MatcherSpec`/compilation seam behind the existing `PipelineGrammar` — no grammar changes. Extend the parity harness. Full CI gate green.
- **Phase 1 (the measured wins):** `lexicon` trie representation + Country name matcher migration (F1 fix lands, with the `TO` case as a regression test asserting the new honest behavior); SIUnit migration (largest scan cost, 376 µs → expected ~×4 improvement from F3 data).
- **Phase 2 (shape freedom):** `scanner` + `combinator` kinds; migrate URL, Phone, and Language (deleting `_BCP47RegexStage` and the 160-line callback — the flagship readability win).
- **Phase 3 (surface):** `scan()` API + mention model + CLI; registry-freeze compilation and `recognition_revision`.
- **Phase 4 (data rails):** snapshot/regenerate/verify CI for the new tables; derived recognition keys.

Risks and mitigations: trie/alternation behavioral parity (byte-identical gate + golden corpora); scanner correctness (each migrated scanner carries the legacy corpus forward); view offset bugs (length-preserving-only in v1 — exactly the constraint every current normalizer satisfies; general offset maps deferred until a capability needs them); performance regressions (benchmarks measure recognition-only cost per phase).

---

## Part VI — Rejected Alternatives

| Alternative | Why rejected |
|---|---|
| ML/NLP NER, fuzzy/approximate matching | Non-deterministic or authority-less; violates provenance-first and the no-guessing contract (same verdict as prior in-repo studies — independently concurred). |
| Hyperscan/RE2/Rust-regex as dependencies | Compiled extensions; violate zero-runtime-dep; leftmost-winner semantics conflict with ambiguity preservation ([engine survey](https://docs.rs/regex/latest/regex/struct.RegexSet.html), [Go regexp](https://pkg.go.dev/regexp)). |
| Adopting spaCy/pyparsing/Lark wholesale | Wrong shape (whole-input parsers, ML legs, token-graph machinery) for a span scanner; performance envelope; dependency. |
| UIMA-style type-system framework | Framework weight (Ecore, containers, serialization) inappropriate for a stdlib-only library; the *pattern* (standoff + typed annotations + declared contracts) is borrowed instead. |
| tree-sitter | Incremental reparsing + GLR recovery + C external scanners solve editing-session problems Paxman does not have. |
| Keep extending the five-slot pipeline (ADR-0009 course) | Subsumed by the kernel with less machinery; does not address F1/F2/F5; measured evidence (F3) already contradicts its pure-Python-trie pessimism. |
| Checksum-fused recognition | Collapses MISSING/INVALID semantics and duplicates authority tables into grammars (stdnum isolates these correctly; Paxman's split is right). |

---

## Appendix A — Measurements (methodology and reproduction)

All measurements run against the working tree at `docs` commit state 2026-08-24, CPython via `uv run`, single process, `time.perf_counter`, 200–500 iterations, min-of-mean reported per table. Script: `/tmp/opencode/paxman_recognition_bench.py` (read-only; no repo files modified).

1. **Whole-input restriction probes** — direct `paxman.canonicalize` calls; grammar-level mechanism confirmed by running `capability.get_grammars()` recognizers directly on the probe strings and printing all matches (`alpha2_recognition span=(5,7) raw='to'` was the sole recognition on the Tonga input).
2. **Per-grammar scan cost** — for each shipped capability, `recognize()` across all its grammars on a fixed 68-char mixed-prose string, 200 iterations.
3. **Alternation vs trie** — SIUnit `NAME_TOKENS` (650) and `SYMBOL_TOKENS` (820): longest-first escaped alternation + `(?<!\w)(?:…)(?!\w)` + IGNORECASE vs a lowercase dict-trie with word-boundary anchoring and longest-match-at-position; correctness cross-checked equal on a mixed sample; measured on 50-char / hit-dense-430-char / 2.2 KB texts; build cost measured separately (20 reps). The first run of this benchmark under-measured regex (unconsumed `finditer` iterator); numbers reported here are from the corrected run that consumes matches.
4. **Lexicon sizes** — introspected Language data modules: grammar name keys 77; rule data ISO 639-3 = 995, ISO 639-2-T = 420, IANA language subtags = 215.

Caveats: single machine, warm caches, no statistical dispersion reported (ratios ≥2.4× are far beyond noise); the trie implementation is a straightforward dict-of-dicts without failure links — an Aho–Corasick or `str.translate`-accelerated variant only widens the gap.

## References (primary sources)

- libphonenumber: [PhoneNumberMatcher.java](https://github.com/google/libphonenumber/blob/17c9061/java/libphonenumber/src/com/google/i18n/phonenumbers/PhoneNumberMatcher.java), [PhoneNumberUtil.java](https://github.com/google/libphonenumber/blob/17c9061/java/libphonenumber/src/com/google/i18n/phonenumbers/PhoneNumberUtil.java), [PhoneNumberMetadata.xml](https://github.com/google/libphonenumber/blob/17c9061/resources/PhoneNumberMetadata.xml); Python port [phonenumbermatcher.py](https://github.com/daviddrysdale/python-phonenumbers/blob/dev/python/phonenumbers/phonenumbermatcher.py)
- Engines: [Hyperscan runtime](https://intel.github.io/hyperscan/dev-reference/runtime.html), [NSDI'19](https://www.usenix.org/system/files/nsdi19-wang-xiang.pdf), [Vectorscan](https://github.com/VectorCamp/vectorscan), [RE2](https://github.com/google/re2), [Rust regex-automata hybrid](https://docs.rs/regex-automata/latest/regex_automata/hybrid/index.html), [RegexSet](https://docs.rs/regex/latest/regex/struct.RegexSet.html), [Go regexp](https://pkg.go.dev/regexp), [CPython gh-95555](https://github.com/python/cpython/issues/95555), [What's New 3.11](https://docs.python.org/3.11/whatsnew/3.11.html)
- Lexicons: [Aho & Corasick 1975](https://dl.acm.org/doi/10.1145/360825.360855), [FlashText paper](https://ar5iv.labs.arxiv.org/html/1711.00046) + [benchmarks gist](https://gist.github.com/vi3k6i5/604eefd92866d081cfa19f862224e4a0), [pyahocorasick](https://pyahocorasick.readthedocs.io/en/latest/), [ahocorapy](https://github.com/FrederikP/ahocorapy), [marisa-trie](https://github.com/pytries/marisa-trie), [datrie](https://pypi.org/project/datrie/)
- Annotation frameworks: [UIMA OASIS spec](https://docs.oasis-open.org/uima/v1.0/os/uima-spec-os.html), [GATE user guide](https://gate.ac.uk/sale/tao/splitch4.html), [spaCy PhraseMatcher](https://spacy.io/api/phrasematcher) / [Matcher](https://spacy.io/api/matcher) / [EntityRuler](https://spacy.io/api/entityruler) / [pipelines](https://spacy.io/usage/processing-pipelines), [Explosion v2.2 blog](https://explosion.ai/blog/spacy-v2-2), [Lucene analysis](https://lucene.apache.org/core/9_8_0/core/org/apache/lucene/analysis/package-summary.html)
- ICU: [UnicodeSet guide](https://unicode-org.github.io/icu/userguide/strings/unicodeset.html), [CodePointTrie design](https://github.com/unicode-org/icu4x/blob/main/documents/design/properties_code_point_trie.md), [LocaleCanonicalizer](https://docs.rs/icu_locale/latest/icu_locale/struct.LocaleCanonicalizer.html), [UTS #35 Annex C](https://unicode.org/reports/tr35/#LocaleId_Canonicalization), [ICU4X data management](https://icu4x.unicode.org/2_1/tutorials/data-management/), [unicodedata docs](https://docs.python.org/3/library/unicodedata.html)
- Scanners/parsers: [Ragel guide](https://www.colm.net/files/ragel/ragel-guide-6.11.pdf), [re2c](https://re2c.org/), [WHATWG URL](https://url.spec.whatwg.org/), [pyparsing scan_string](https://pyparsing-docs.readthedocs.io/en/latest/pyparsing.html), [Lark classes](https://lark-parser.readthedocs.io/en/latest/classes.html), [nom](https://docs.rs/nom/latest/nom/), [winnow](https://docs.rs/winnow/latest/winnow/trait.Parser.html), [pest book](https://pest.rs/book/), [tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- Multi-strategy: [dateparser contributing](https://dateparser.readthedocs.io/en/latest/contributing.html) / [settings](https://dateparser.readthedocs.io/en/latest/settings.html), [chrono source](https://github.com/wanasit/chrono/blob/master/src/chrono.ts), [dateutil parser](https://dateutil.readthedocs.io/en/stable/parser.html), [python-stdnum](https://arthurdejong.org/python-stdnum/) ([iban.py](https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/iban.py))
- Compiler pattern: [rustc queries](https://rustc-dev-guide.rust-lang.org/query.html), [query evaluation model](https://rustc-dev-guide.rust-lang.org/queries/query-evaluation-model-in-detail.html)
- Local: `paxman/core/grammar/{pipeline,stages,boundary,lexicon,composer}.py`; `paxman/engine/orchestrator.py`; `paxman/capabilities/**/grammar/**`; `ARCHITECTURE.md` (Recognition Pipeline Contract); `HOW_TO_ADD_NEW_CAPABILITY.md` §4; `docs/development/MILESTONE.md`; `benchmarks/baseline.json`; `docs/adr/0008`, `docs/adr/0009` (reviewed as artifacts); `docs/development/research/2026-08-24-recognition-strategy-study.md` (reviewed as artifact); `docs/development/reports/recognition-handling-library-research.md` (reviewed as artifact)
