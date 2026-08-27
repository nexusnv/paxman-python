# Recognition Strategy Study — Beyond Regex & Lexicon

**Date:** 2026-08-24
**Scope:** Primary-source audit of every shipped grammar in `paxman-python` at `main` (≈ `0.1.0`, 14 capabilities, 33 grammars), the staged pipeline in `paxman/core/grammar/`, the engine in `paxman/engine/orchestrator.py`, and the secondary literature (`HOW_TO_ADD_NEW_CAPABILITY.md` extended strategies, ADR-0008, `capability_homogeneity_audit.md`, 9 canonicalization research docs, 28 plan files). No source code, tests, or configuration were modified.
**Evidence basis:** Source at `main` — `paxman/capabilities/*/grammar/*.py` (33 files) + `paxman/core/grammar/{stages,boundary,lexicon,pipeline,composer}.py` + `paxman/core/domain.py` + `paxman/engine/orchestrator.py` + `docs/adr/0008-staged-recognition-pipeline.md` + `HOW_TO_ADD_NEW_CAPABILITY.md` §4 extended strategies table + `HOW_TO_ADD_NEW_GRAMMAR.md` + `ARCHITECTURE.md` + `paxman/shared_data/` + all `docs/development/{plans,research}/` files. Sub-agent audits via `hermes` opencode harness (4-way fan-out: grammar inventory, future-need gaps, staged-pipeline deep-dive, external-strategy survey) — this document is the synthesised human-authored report.
**Conventions grounding this report:** `HOW_TO_ADD_NEW_CAPABILITY.md`, `HOW_TO_ADD_NEW_GRAMMAR.md`, `ARCHITECTURE.md`, ADR-0001/0003/0004/0007/0008, `paxman/capabilities/AGENTS.md`, `paxman/core/AGENTS.md`.

---

## Executive Summary

Paxman ships **33 grammars across 14 capabilities** (Country 4, Currency 3, Date 4, Email 3, BIC 1, IBAN 1, IP 2, ISBN 2, ISSN 1, ORCID 1, Money 3, Phone 4, SIUnit 3, URL 1) behind a single `Grammar[NotationT].recognize(text) -> list[RecognitionMatch]` surface. Every `recognize()` is now a declarative `PipelineGrammar` walking a **fixed-order pipeline with optional stages** `pre → regex → lexicon → composer → post` (ADR-0008, accepted 2026-08-20). The pipeline made recognition auditable: `BoundaryGuard` replaces 11 hard-coded lookarounds, `LexiconAlternation` replaces 5 `re.escape+join` copies, `AmountComposer` replaces 3 `SYMBOL ? AMOUNT | AMOUNT ? SYMBOL` copies, and the engine owns `RecognitionMatch[start,end,raw_text]`-bearing dedup/ordering.

That design covers **five realised strategy-instances** well:

* **S1** Pure shape — 18 `pre+regex` grammars
* **S2** Whole-input membership — 1 `WholeInputLookup` (Country `name_recognition`)
* **S3** Lexicon-driven regex — 4 `LexiconStage` grammars
* **S4** Compositional span-merge — 4 (Money 3 via `AmountComposer`, SIUnit `compound` via regex composition)
* **S5** Post-trim / refine — 3 `PostStage` grammars (Phone `e164` 15-digit window, URL paren-balance)

The **gap** is not that these five are wrong — they already ship all 14 capabilities cleanly, byte-identical via `tests/property/test_grammar_stage_parity.py`. The gap is that **the two sanctioned strategies (Regex, Lexicon) plus the three composed stages already strain at the edges**, and every primary-source plan for the next capabilities says so explicitly:

* **Language** (BCP 47 / ISO 639, plan only, not yet implemented) cannot be expressed as a maintainable regex — its ABNF is `language ["-" script] ["-" region]* ("-" variant)* ("-" extension) ["-" privateuse] | …` and its lexicon is 7000+ ISO 639-3 keys plus 8000+ IANA registry subtags with `Prefix` constraints (`sl-nedis` is valid only if `sl` is present). The 913-line Language research calls this "not maintainable as a regex".
* **URL** is a permissive shape (`scheme: body`) plus a `PostStage` paren-balance trim; the rule layer owns WHATWG `parse_and_serialize()` — the grammar would be clearer as a scanner.
* **SIUnit / Country / Currency** vocabularies (820 symbol tokens, 650 name tokens, 270 country names, 67 currency symbols) are served today by `re.escape`-joined alternations `longest_first, qualified_first` — which the `HOW_TO` extended-strategies table itself prescribes an **Aho–Corasick automaton** for when they degenerate.
* **IBAN / BIC / ORCID / ISBN / ISSN label handling** duplicates `[\s:-]+` vs `[\s:-]*` vs `[\s:-]+` never-zero-width logic with no unified `LabelStage`.
* **Underscore tolerance (`en_US` → `en-US`), tab/newline stripping (URL), NFKC folding (`²`→`2`, `µ` → `μ`), accent stripping (Country `normalize_name`)** are all one-off grammar-file concerns — the `StandardPre` is today just `empty_guard`, and `PipelineState.scratch` (the ADR's normalized-view hook) is never populated.

`HOW_TO_ADD_NEW_CAPABILITY.md:282` already catalogues the missing ensemble — *scanner, format-candidate, parser combinators, parser generator (Lark), Unicode-property, automaton* — as "what the architecture can absorb before forcing a representation into a regex that fights it". This study turns that catalogue from **documented but unimplemented** into **prioritised, scoped proposals with stage APIs and capability mappings**, and adds two cross-cutting gaps the catalogue misses: **normalized-view threading** and **generic prefix-constrained composition**.

**Bottom line:** Keep S1–S5. Do **not** add ML/NLP NER or fuzzy/approximate matching (rejected below on determinism/provenance). **Do** add, in priority order, (P1) a `NormalizedView` Pre stage that threads through `scratch`, (P2) an `AutomatonStage` (Trie/Aho–Corasick) for large lexicons, (P3) a `ScannerStage` for delimiter-balanced / context-sensitive shapes, (P4) a `UnicodePropertyStage` / generated range table, (P5) a `FormatCandidateStage` for enumerated strict formats, and (P6) a generic `ComposerStage` replacing `AmountComposer`'s single-separator assumption. Each unlocks both **shipped-capability cleanup** (URL paren-balance from PostStage to Scanner, SIUnit symbol lookup from regex alternation to automaton, Phone E.164 15-digit window from PostStage to scanner with limit, Currency/Country lexicon acceleration) **and future-capability feasibility** (Language BCP47 ABNF, IBAN per-country BBAN regex registry, ISIN/CUSIP planned palette).

---

## 1. How Recognition Works Today

### 1.1 The staged pipeline (ADR-0008, now shipped)

```
text ──► 1. Pre (StandardPre) ──► 2. Regex (RegexStage) ──► 3. Lexicon (LexiconStage / WholeInputLookup)
                                   │                            │
                                   └──────── 4. Composer (AmountComposer) ─────┐
                                                                                ▼
                                                                       5. Post (PostStage) ──► list[RecognitionMatch]
```

* `Stage[NotationT]` Protocol: `run(PipelineState) -> PipelineState` where `PipelineState = {text: str (immutable), matches: list[RecognitionMatch], scratch: dict}`. `text` must not mutate (spans remain relative to original input); `scratch` is the ADR's normalized-view hook — currently **never written or read** (dead code).
* `PipelineGrammar[NotationT]` (in `paxman/core/grammar/pipeline.py`) extends `Grammar[NotationT]` (`name: str`, `semantics: ClassVar[str]`, `single_value: ClassVar[bool]`, `recognize(text) -> list[RecognitionMatch]` in `paxman/core/domain.py`). It declares `pre / regex / lexicon / composer / post: Stage | None = None` and walks them in fixed order.
* All 33 shipped grammars declare `pre = StandardPre(empty_guard=True)` — i.e. the identical one-liner `if not text.strip(): return []`.
* Engine (`paxman/engine/orchestrator.py:run_capability`) calls `grammar.recognize(text)`, validates `0 <= start <= end <= len(text)` and `raw_text == text[start:end]` (raises `RecognitionError` otherwise), runs `_dedup_spans` (within-grammar "longer wins", cross-grammar preserved), sorts by `(start, end, active_grammars index, grammar name)` (total document order), then affine-routes `target_semantics` and formats via `Capability.format_value()`.

Parity guarantee: `tests/property/test_grammar_stage_parity.py` asserts `old.recognize(text) == new.recognize(text)` as `(start,end,raw_text,notation)` for every migration PR; benchmark `benchmarks/harness.py` is informational non-blocking (50 iterations in CI per `benchmarks/README.md`).

### 1.2 Five realised strategy-instances (verified 2026-08-24; ADR-0008 counted 17/1/4/4/4=30 — now 18/1/4/4/3≈30 over 33 grammars)

| Strategy | Mechanism | Stage(s) | Count | Examples |
|----------|-----------|----------|-------|----------|
| **S1** Pure shape | `RegexStage.finditer` | `pre+regex` | 18 | BIC, IBAN, ORCID, IP v4/v6, ISBN 10/13, ISSN, Date ×4 (`digit` guard), Email ×3 (`\b`), Phone national/tel/00, SIUnit compound, URL base |
| **S2** Whole-input membership | `WholeInputLookup(keys, normalizer)` | `pre+lexicon:WIL` | 1 | Country `name_recognition` — `normalize(trimmed) in _KNOWN_NAME_KEYS` (union of 4 locale sets), emits `raw_text=trimmed` not normalized key |
| **S3** Lexicon-driven regex | `LexiconStage` via `LexiconAlternation + BoundaryGuard.wrap` | `pre+lexicon` | 4 | Currency symbol/word (`word_sign`, `IGNORECASE`), SIUnit symbol/name (`degree_word_sign`, longest-first + qualified-first) |
| **S4** Compositional | `AmountComposer` (fused either-order) / compound regex | `pre+composer` or `pre+regex` fused | 4 | Money code/symbol/word `lex ? amt | amt ? lex`; SIUnit `compound` `UNIT(SEP UNIT){1,3}` with `UNIT=°?[A-Za-zµΩÅ][A-Za-z0-9]*[exponent]*`, `SEP=[/·⋅]` |
| **S5** Post-trim / refine | `PostStage(RM→RM|None)` | `pre+regex+post` | 3 (+ inline) | Phone `e164` 15-digit `_trim_to_e164_boundary`, URL `parens balance + bare-scheme drop`; inline classifiers Money `classify_amount_shape`, SIUnit `split_symbol_prefix`/`split_word_prefix` (inside `notation_fn`, not `PostStage`) |

### 1.3 BoundaryGuard — 11 factories, one open-ended family

Replaces 8 legacy literals (ADR counted 8; audit finds 11 today). All via `BoundaryGuard.wrap(alternation, flags) -> re.Pattern`:

| Factory | `lookbehind` | `lookahead` | Capability home |
|---------|--------------|-------------|-----------------|
| `word_sign()` | `(?<![\w\-+\u2212])` | `(?![\w\-+\u2212])` | Currency/Money `word_sign`, SIUnit compound |
| `degree_word_sign()` | `(?<![°\w\-+\u2212/·⋅])` | same | SIUnit symbol/name (preserves `°`) |
| `digit()` | `(?<!\d)` | `(?!\d)` | Date ×4, ISSN right |
| `word_only()` | `(?<!\w)` | `(?!\w)` | BIC, Country α2/α3/numeric, IBAN, ORCID, Phone tel, ISSN left |
| `e164()` | `(?<![\w:.])` | `""` | Phone `e164` |
| `e164_00()` | `(?<![\w:.+])` | `""` | Phone `00` |
| `scheme_char()` | `(?<![A-Za-z0-9+.\-])` | `""` | URL |
| `phone_national()` | 4-chain `(?<![\d+])(?<![\d+][\s.\-])…` | `(?!\d)` | Phone national |
| `ipv6_token()` | `(?:^|(?<=[\s,;([ ]))` consuming | `(?:$|(?=[\s,;().\]]))` | IP v6 (`RegexStage` only) |
| `isbn_trail()` | `(?<![\s:-])` | `""` | legacy (now `isbn10_lead` only) |
| `isbn10_lead()` | `(?<!\d)(?<!\d[ -])` | `""` | ISBN-10 |

Email/IPv4 still use verbatim `\b` (ADR carved out). `ipv6_token` is consuming not zero-width — not interchangeable with `LexiconStage.wrap`.

### 1.4 Grammar data — where the vocabulary lives

| Data file | Tokens | Source | Consumed by |
|-----------|--------|--------|-------------|
| `Country/data/english_names.py` | `ENGLISH_NAME_KEYS` ≈ 270 (`USA/U S A/AMERICA`, `UK/GB/BRITAIN/ENGLAND`, `HOLLAND/TÜRKIYE…`) | ISO 3166-1 | `WholeInputLookup` union |
| `Country/data/chinese_names.py` | `CHINESE_NAME_KEYS` ≈ 80 | hand key set | same union |
| `Country/data/historical_names.py` | `HISTORICAL_NAME_KEYS` ≈ 33 (`BURMA/YUGOSLAVIA/USSR…`) | ISO 3166-3 | same union |
| `Country/data/localized_names.py` | `LOCALIZED_NAME_KEYS` ≈ 215 (zh+es+fr) | CLDR v45 | same union |
| `Currency/data/currency_symbols.py` + `Money/data/currency_symbols.py` | `SYMBOL_TOKENS` 67 (`CFPF/CA$/US$ → $,£,¥…`) | `regenerate_currency_data.py` ← `shared_data/currency_snapshot.json` CLDR v47 | `LexiconStage` / `AmountComposer` |
| `Currency/data/currency_words.py` + `Money/data/currency_words.py` | `WORD_TOKENS` 80/77 (`boliviano…euro…yen`) | same | `LexiconStage`/`AmountComposer` |
| `SIUnit/data/unit_symbol_tokens.py` | `SYMBOL_TOKENS` ≈ 820 (`m/kg/Pa/°C/bar/mbar…km/MHz…`) | `regenerate_si_prefix_data.py` ← BIPM 9th ed | `RegexStage` |
| `SIUnit/data/unit_name_tokens.py` | `NAME_TOKENS` ≈ 650 (`metre/degree celsius/millimetre of mercury…`) | same | `RegexStage` |
| `SIUnit/data/prefix_tokens.py` | `PREFIX_WORD_TOKENS` 24, `PREFIX_SYMBOL_TOKENS` 22 | BIPM Table 5 | split detectors |
| `SIUnit/data/compound_tokens.py` | `COMPOUND_SEPARATORS="/·⋅"`, `EXPONENT_CHARACTERS="0-9⁻⁰¹²³…"`, … | BIPM §5.4 | compound regex |

Money `AMOUNT_PATTERN = (?:\([0-9][0-9.,\u202f]*\)|[0-9][0-9.,\u202f]*)` stays in `Money/grammar/__init__.py`; `classify_amount_shape` (`accounting|space_decimal|dot_decimal|comma_decimal|integer`) is passed into `AmountComposer` — core never imports capability data (import-linter leaf).

### 1.5 Notation, contract, engine guarantees

* `RecognitionMatch[NotationT](notation, start, end, raw_text)` — `len(raw_text)==end-start`, half-open, enforced in `__post_init__`; `NotationT` is a frozen-`slots` dataclass, one `str` field per component (shape discriminator when needed).
* `CapabilityContract` base class demoted `Contract` Protocol to engine-internal (`core/_engine_contract.py`) per ADR-0007 — no `getattr(extra_grammars)` probes; `active_grammars: None` (run every shipped grammar) vs conditional list; `requires_features` routes authority gating inside `_filter_rules` (false→`INVALID`, not re-cast inside `matches()`).
* `_dedup_spans` — within-grammar "longer wins" (sorted `(start, -(length))`), cross-grammar preserved so Date US/European ambiguity `01/02/2026` survives.
* `_filter_rules` — `pinned → excluded → year → requires_features(last)`; `_validate_affinity` fails fast on unknown `target_semantics`.
* `format_value(value, output_format, notation)` — sole presentation seam, engine-applied after `normalize()`; rules never read `output_format` (CI-scanned `tests/unit/test_rule_output_format_purity.py`).

---

## 2. What HOW_TO Already Documents but We Don't Ship

`HOW_TO_ADD_NEW_CAPABILITY.md:282` lists **six** extended strategies after the sanctioned Regex/Lexicon pair, with a verbatim table (abridged):

| Strategy | Recognizes by | Reach for it when … |
|----------|---------------|---------------------|
| **Hand-written scanner** (state machine / recursive descent) | balanced delimiters, escapes, lookahead-dependent tokenization | pattern becomes an unreadable regex |
| **Format-candidate** | a small set of formally enumerated strict formats — first accepting candidate wins | spec enumerates exact formats (ISO variants, `strptime`-style) rather than one loose shape |
| **Parser combinators** (pyparsing) | composing small recognizers into one grammar — `scan_string()` yields `(tokens,start,end)` | format decomposes into orthogonal pieces |
| **Parser generator** (Lark) | EBNF grammar compiled to parser — `Lark.scan()` yields `ScanMatch(range=(start,end))` | recursive or ambiguous-by-design syntax |
| **Unicode-property** | `\p{Sc}`, `\p{Script=Han}` | open Unicode class defines the category |
| **Multi-key automaton** (Aho–Corasick) | many literal keys in one pass — prefilter when `(key1|key2|…) becomes slow or unwieldy` | large literal vocabulary (units, codes, stopwords) |

All six are cited to ecosystem precedent (Flex, `parse`, `pyparsing.urlExtractor`, `CleverCSV`, `pyahocorasick`, QUIC's Ragel) — and **none** is realized as a `Stage`. Contributors are today told "consult this table before forcing it into a regex that fights it" but have no stage to reach for.

The audit finds two more gaps the table misses: **normalized-view threading** (ADR-0008 proposed a `Pre` with unicode/normalizer/case policy but shipped only `empty_guard`) and **generic prefix-constrained composition** (`AmountComposer` is not generic; SIUnit `compound` is a one-off regex; Language `variant Prefix` like `sl-nedis` needs `Prefix.contains("sl")` gating not expressible as a regex alone).

---

## 3. Gap Analysis — What's Missing and What to Do About It

Each candidate below is judged on the three Paxman invariants (determinism, provenance-first, zero runtime deps) plus evidence from shipped capability pain and future-capability feasibility. A missing strategy is **recommendable** only if it unlocks a shipped enhancement **and/or** a clearly planned future capability without violating those invariants.

### 3.1 [P1] Normalized-View Pre Stage — the cross-cutting hole

**Today:** `StandardPre` is one bool (`empty_guard`); `PipelineState.text` is immutable per spec but `PipelineState.scratch` is never populated. Every capability hand-rolls syntax normalization differently:

* Country `name_recognition` → `normalize_name` (NFKD → strip accents → lower → separator→space → punctuation strip → whitespace collapse) shared with rules — but only `WholeInputLookup` threads it (as `normalizer` argument), not `LexiconStage`/`RegexStage`.
* Phone `_common.strip_separators` (`" ().-"` → compact digits) + `isascii` filter in BIC/ORCID/IBAN (`(?ai:…)` restricting to ASCII vs `K`-style homoglyphs).
* SI `²`→`2` / `µ` normalization, Currency `WORD_TOKENS` lower-fold, URL tab/newline and `IDNA_STATUS/MAPPED` (UTS #46) vendored tables, BIC `compact = filter alnum upper`, Language `_`→`-` underscore-tolerance.

Language's plan calls for a `Pre` that replaces `en_US → en-US` while preserving original `raw_text` span — but the stage protocol forbids mutating `text`, and `RegexStage`/`WholeInputLookup` don't read `scratch`. The workaround in the plan is to mutate `PipelineState.text` inside `Pre`, violating the ADR.

**Proposed:** `NormalizedViewStage` (or generalised `StandardPre`):

```python
@dataclass(frozen=True, slots=True)
class NormalizedViewStage(Generic[NotationT]):
    normalizer: Callable[[str], str]  # pure function: text -> normalized_text

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        state.scratch["normalized"] = self.normalizer(state.text)
        return state
```

Stages that need the normalized view (`RegexStage`, `LexiconStage`, `WholeInputLookup`) gain an optional `source: Literal["text","normalized"] = "text"` parameter (default `"text"` preserves parity). The `scratch` contract is: Pre populates `scratch["normalized"]`; downstream stages declare which view they scan — but emitted `RecognitionMatch.start/end/raw_text` **always refer to the original `text`**, with translation via an offset map when normalization changes length (e.g. NFKC decomposition). For length-preserving normalizers (`lower`, `_→-`, accent stripping via precomputed table) the map is identity and costs nothing; for NFKC-expanding cases the stage stores an `offsets: list[int]` mapping.

**Shipped enhancement:** eliminates duplicated `strip_separators` / `lower` / `filter` inside each `notation_fn`, makes SI `²→2` and BIC `isascii` declarative, lets URL IDNA be a Pre stage rather than per-rule helper.
**Future enablement:** Language `en_US` tolerance, Country accent-insensitive lookup without duplicated `normalize_name` call, SI name case fold from grammar-file `IGNORECASE` flag to Pre declaration.
**Fit:** pure, zero-dep, deterministic if `normalizer` is pure; import-linter leaf stays clean (capability supplies the normalizer as a callable, core holds only the stage shell).
**Risk:** offset translation for length-changing normalizations — complexity real, but shipped grammars all have length-preserving needs first, so stage can ship with `require_length_preserving=True` and defer general translation.

**Recommendation: P1 — land in the next staged-pipeline PR. Cost: one new stage + one field on existing stages. No new dependency.**

---

### 3.2 [P1] Automaton / Trie / Aho–Corasick — the large-lexicon answer

**Today:** `LexiconAlternation` sorts tokens `(-len, -is_qualified, token)` and emits `re.escape`-joined alternation consumed by `BoundaryGuard.wrap` → `re.compile(...).finditer`. For 67 currency symbols and 80 words this is fast; for SIUnit's 820 symbols + 650 names (and SIUnit capability wires them as **two long regex alternations** `SYMBOL_TOKENS`/`NAME_TOKENS` plus a split-prefix alt) it's the largest compiled regex in the tree, and Country's `WholeInputLookup` union is 600+ keys.

Future Language makes this an order-of-magnitude worse: 7000+ ISO 639-3 alpha-3 keys, 500+ ISO 639-2 keys, 8000+ IANA `Type: language` keys, plus CLDR display names gated by `include_localized`. The Language plan and `HOW_TO`'s automaton footnote both anticipate compiling `re.escape`-joined 7000-token alternations — which is precisely the "degenerates" case the table prescribes `pyahocorasick` for.

**Evidence:** `SIUnit/data/unit_symbol_tokens.py` (≈ 820) and `unit_name_tokens.py` (≈ 650) are already generated via `tools/regenerate_si_prefix_data.py` — the build-time regeneration precedent that an automaton stage can reuse. `benchmarks/harness.py` (50 iterations, informational) can measure the crossover; our augmented audit never reached threshold arguments but `benchmarks/baseline.json` is the arbiter.

**Proposed:** `AutomatonStage` (stdlib-only):

Paxman's zero-dep constraint rules out `pyahocorasick` as a runtime dep, but a pure-Python Trie in `paxman/core/grammar/` (evergreen: `datrie`-style but stdlib) satisfies "deterministic, provenance-first, zero runtime deps" — or a hybrid: `LexiconStage` remains the default, `AutomatonStage` shares its `boundary` + `notation_fn` interface but inserts a Trie scan:

```python
@dataclass(frozen=True, slots=True)
class AutomatonStage(Generic[NotationT]):
    tokens: frozenset[str] | set[str] | list[str] | tuple[str, ...]
    boundary: BoundaryGuard
    longest_first: bool = True  # longest wins = Trie deepest leaf wins
    notation_fn: Callable[[str], NotationT] | None = None
    flags: int = 0  # IGNORECASE thread via lowercased Trie keys

    _trie: Trie = field(init=False)  # built in __post_init__, pure

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        src = state.scratch.get("normalized", state.text)  # P1 hook
        for hit in self._trie.scan(src):  # yields (token, start, end)
            if not self.boundary.allows(src, hit.start, hit.end):
                continue
            ...
```

For whole-input lookup the same Trie replaces the `frozenset.__contains__(key)` pattern with `hit.end==len(trimmed)` guard.

**Shipped enhancement:** SIUnit symbol/name recognition becomes a single Trie scan (650+ alternations → O(n) scan once), Phone/Country/Currency latency remains unchanged (small lexicons stay on `LexiconStage` — no migration needed).
**Future enablement:** Language ISO 639-3 / IANA registry (7000+ + 8000 keys) — the single case where Regex/Lexicon cannot cover a planned capability without performance regression or maintainability debt.
**Fit:** deterministic (Trie traversal order is total: deeper/longer first, then lex order mirrors `LexiconAlternation`); zero-dep if pure-Python; no provenance leak (keys stay key-only).
**Risk:** stdlib Trie slower than C `re` for small vocabularies — mitigate by size threshold (e.g. `AutomatonStage` only for grammars whose `grammar/data/` exceeds `threshold=200` tokens, else `LexiconStage` remains cheaper). Keep parity gate: `AutomatonStage.finditer` must yield byte-identical `RecognitionMatch` sequence as the equivalent `LexiconStage`.

**Recommendation: P1 (paired with P1 normalized view). Land as opt-in stage — existing lexicon grammars unchanged, Language adopts it. No dep added; build-time `Trie` like `regenerate_si_prefix_data.py` remains parity-proven.**

---

### 3.3 [P2] Scanner / Char-State Stage — for structured delimiting

**Today:** URL (`RegexStage` loose `scheme: body` → `PostStage` `_url_trim` counting `")"` vs `"("`, dropping bare scheme `scheme_end+1`) and Phone `e164` (`RegexStage` `\+\d … (?<=\d)` → `PostStage` `_trim_to_e164_boundary` scanning `re.finditer(r"\d+", raw)` with 15-digit window and LRU cache) are both **scanner problems disguised as regex+post**. The scan loop is already a tiny hand-written automaton — just buried inside a `PostStage` closure. Bicycle handling confirms the pattern: BIC's `_COUNTRY_CODES frozenset` (250 entries) duplicates the rule table so the grammar can `negative lookahead` a BIC-prefixed valid-country bank without swallowing `BICXUS…`.

A `ScannerStage` walks `text` character-by-character, tracking state (inside-paren depth, digit-run length, separator skipping), emitting spans deterministically — the `libc`-style `ipaddress`, `tomllib`, `email.headerregistry` precedent cited in `HOW_TO`.

**Proposed:**

```python
@dataclass(frozen=True, slots=True)
class ScannerStage(Generic[NotationT]):
    scan: Callable[[str, int], tuple[int, int, NotationT] | None]

    # called per start index: pure function, returns (start,end,notation) or None to advance by 1
    # grammar file supplies the scan closure capturing capability constants
    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]: ...
```

Unlike `RegexStage`'s `finditer`, the scanner advances non-overlapping (`intellectually` `phonenumbers.PhoneNumberMatcher`'s `self._search_index = last_match.end`); per-grammar containment dedup then becomes unnecessary (the scanner already produces maximal non-overlapping spans). In practice the stage still emits into `PipelineState.matches` and the engine's `_dedup_spans` no-op safely.

**Shipped enhancement:** URL paren-balance from imperative `PostStage` loop (excess=`)` count) to stateful scan with depth counter (handles nested `https://example.com/a(b(c)d)e`) without regex back-tracking; Phone `e164` 15-digit window as bounded scan instead of regex overshoot + trim + LRU cache.
**Future enablement:** ISIN/CUSIP planned palettes (ISIN 12-char, CUSIP 9-char with `*`/`@`/`#` special trailing check), DOI/URN (`doi:10.1234/...` balanced `/` tokenization), Timezone `tzdata` URIs, any capability where validation requires character-class aware delimiting (IBAN paper groups-of-four is today's near-scanner case).
**Fit:** pure scan, no dep, deterministic (single pass, longest match at each position); evidence from `docs/development/research/2026-08-23-orcid-canonicalization.md` (ORCID label `[\\s:-]+` never zero-width) suggests label-aware scan would replace lookahead duplication.
**Risk:** hand-rolled scan is test-intensive — but `Phone/e164` already carries its tricky corpus (contains `+1 425 882-8080`'s `_trim` LRU, national's 4-lookbehind chain). Migration gate stays byte-identical.

**Recommendation: P2 — land after P1 pair. URL + Phone are the pilot migrants (both already have `PostStage` scaffolding so parity harness exists).**

---

### 3.4 [P2] Unicode-Property / Generated-Range Stage

**Today:** `re` has no `\p{…}`. `HOW_TO`'s footnote cites `CleverCSV (\p{Sc})`, `python-textile` (hand-rolled ranges), `TensorFlow Text (\p{Sm}, \P{L})`, `emoji` (key-set over `\p{Emoji}` because the property is too broad). Paxman handles Unicode today by **either** curating a lexicon (Currency symbol table as fallback for `\p{Sc}`) **or** by build-time generation (`regenerate_si_prefix_data.py` for `SYMBOL_TOKENS`, `regenerate_isbn_range_data.py` for `range_message.py`'s 2026 Range Message, `regenerate_idna_uts46_data.py` for IDNA's `IDNA_STATUS/MAPPED` vendored snapshot, `regenerate_currency_data.py` from `shared_data/currency_snapshot.json` CLDR snapshot).

That generation is the right pattern — but there's no stage for "recognize any `Currency_Symbol` / `Script=Han` / `ID_Start`" token. Future Language's Han-script detection, SIUnit `µ`/`Ω`/`Å` variants, BIC `isascii` guard, and the entire Extended-Language concept (`zh-Hans-CN` script Title) are property problems currently forced through ASCII-only `(?ai:…)` with explicit letter tables.

**Proposed:** `UnicodePropertyStage` as a **thin** alternation over a generated range:

* The source of truth remains a build-time generator writing into `grammar/data/` (e.g. `tools/regenerate_unicode_property_data.py` pulling from `unicode.org` or vendored `PropList.txt`), emitting a frozen `frozenset[str]` or `range` table exactly like `regenerate_isbn_range_data.py`.
* The stage itself is just another `LexiconStage`-shaped alternation over that frozen table, or a direct character-class tuple `[\uXXXX-\uYYYY…]` compiled once. No `regex` module at runtime.

**Shipped enhancement:** SIUnit `°`/`µ`/`Ω`/`Å` and Currency `SYMBOL_TOKENS` vs missing `\p{Sc}` become auditable (generated range vs hand-curated CLDR snapshot parity test doubles as equivalence gate).
**Future enablement:** Language script subtag validation (`Hans` must be `Script` type per IANA), Currency generic `any currency symbol` scanner, Emoji / Symbol domains if ever considered — handled as property not vocabulary.
**Risk:** over-broad property (again `\p{Emoji}` is too broad per `emoji` lib) — so property remains opt-in per grammar, not generic lexicon replacement.

**Recommendation: P2 as build-time generator + `UnicodePropertyStage` type alias over `LexiconStage`/`RegexStage` with generated class. Reach for tables first; add the stage only when the same property recurs twice (Language is the second after SIUnit).**

---

### 3.5 [P3] Format-Candidate Stage — enumerated strict formats

**Today:** Date fabricates format-candidate logic across **four separate grammars** (`iso8601_recognition`, `slash_iso_recognition`, `european_recognition`, `us_recognition`) whose `semantics` is coalesced for `iso8601_calendar_date` but still costs 4 `PipelineGrammar` instances. ISBN similarly splits `isbn10_recognition` vs `isbn13_recognition` (two semantics, `include_isbn10` gating). The engine's `target_semantics` routing and `(start,end,active_grammars index,grammar name)` ordering already behave like a candidate loop — but each candidate carries its own `BoundaryGuard`, its own `notation` mapping, and its own test file.

A `FormatCandidateStage` is the stdlib precedent `strptime(format1) else strptime(format2)` / `parse` library `compile(fmt).search` with per-candidate spans exposed — useful when the spec enumerates **exact formats** (ISO variants, `strptime`-style patterns) rather than one loose shape. ADR-0008's migration step 5 anticipates this ("migrate remaining S1 grammars — mechanical") and the extended-strategies table names it as the spec-enumerated-format answer.

**Proposed:**

```python
@dataclass(frozen=True, slots=True)
class FormatCandidateStage(Generic[NotationT]):
    candidates: tuple[
        RegexStage[NotationT], ...
    ]  # each candidate is a tiny RegexStage with its own pattern/guard/notation_fn
    strategy: Literal["first"] = (
        "first"  # first accepting span wins; "all" keeps ambiguity observable
    )

    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        for cand in self.candidates:
            for m in cand._compiled.finditer(state.text):
                # deduplicate across candidates per grammar (same span → keep first candidate)
                ...
```

A single grammar `date_recognition` would then list `candidates = (iso8601, slash_iso, european, us)` with coalesced vs distinct semantics per candidate, trading 4 grammars for 1 grammar with 4 candidates. Byte-identical `RecognitionMatch` sequence is the migration gate (the Date grammars' `DateNotation(N1,N2,N3)` positional convention makes candidates differ only in `N1/N2/N3` mapping plus digit-guards which already share `digit`).

**Shipped enhancement:** Date's 4 files → 1 file (less `BoundaryGuard` duplication, one `name="date_recognition"` still routed to two semantics per candidate), ISBN's two grammars remain two grammars (semantics differ + gating differs — not a candidate case).
**Future enablement:** RFC 3339 / ISO 8601 extended variants (`YYYY-MM-DD [T ] hh:mm:ss[.frac][Z|±hh:mm]`), Phone national formats per-country (NANP vs E.164 vs national masks enumerated in NTT plans), IBAN per-country BBAN `regex` registry (90 `regex` rows as `FORMAT_CANDIDATES: dict[country_code, Pattern]` behind a single `iban_recognition` grammar — similar to BIC's embedded country set but candidate-scoped).
**Fit:** deterministic (candidate list order is total); provenance unchanged (rule sees same `Notation`); zero dep.
**Risk:** candidate count grows (RFC3339 is 6+ variants) — parity harness protects, but documentation must keep each candidate's authoritative section cited.

**Recommendation: P3 — after P1/P2. Pilot on Date (4→1) where the corpus and harness already exist, then IBAN registry as the forcing function for the registry-entry pattern.**

---

### 3.6 [P3] Parser-Combinator / Generic Composer — composable grammar

**Today:** `AmountComposer` is the only S4 composer and it is **not generic**: it hardcodes `[A-Z]{3}` when `lexicon_tokens=None`, exactly ` ?` (one optional ASCII space) as separator, and fails on named-group `pattern` (MUST be `(?:…)`). SIUnit `compound` `UNIT(SEP UNIT){1,3}` and SIUnit prefix-split `PREFIX \s+ UNIT → split_*` are both compositional but implemented as bespoke regex alternations inside `notation_fn`, not through `AmountComposer`. Language's BCP47 `variant Prefix` (`sl-nedis` is valid only as a suffix of `sl`/`sl-rozaj`) is compositional with a **prefix-constrained lexicon** — not expressible as `lex ? amount`.

The `pyparsing` and Lark `scan_string`/`Lark.scan` precedent in `HOW_TO`'s table (with `propagate_positions` for span-bearing tree nodes) is the evidence that composable grammars matter — but `paxman` will keep zero deps, so the design is a **hand-rolled combinator stage in `core/grammar/`** rather than a vendored Lark.

**Proposed:** `GenericComposerStage`:

```python
@dataclass(frozen=True, slots=True)
class GenericComposerStage(Generic[NotationT]):
    lex_left: LexiconStage | RegexStage | None
    lex_right: LexiconStage | RegexStage | None
    separator: re.Pattern[str] | None   # e.g. re.compile(r"[\\s:-]+") vs literal " ?"
    order: Literal["either","prefix","suffix"]
    predicate: Callable[[str, str], bool] | None  # prefix constraint, e.g. (tag, variant) -> prefix_ok
    notation_fn: Callable[[str, str], NotationT] | None
    boundary: BoundaryGuard
    def run(...) -> PipelineState[NotationT]: ...
```

Under the hood it fuses the same `(?P<a>ALT)sep(?P<b>PAT) | (?P<b>PAT)sep(?P<a>ALT)` shape as `AmountComposer` but parametrized. `AmountComposer` becomes a thin documented alias over `GenericComposerStage(pattern=_AMOUNT_CORE, separator=one_space, …)` and remains the Money-specific import.

**Shipped enhancement:** SIUnit `compound` becomes `GenericComposerStage(left=UNIT, right=UNIT, separator=one_of("/·⋅"), order="either", predicate=is_compound_factor)` rather than `UNIT(SEP UNIT){1,3}` — recursive `FACTOR = UNIT | "(" UNIT (SEP UNIT){0,3} ")"` stays as the UNIT regex, composition is only sequencing.
**Future enablement:** Language `sl-nedis` variant (`variant` token adjacent to `language` token with IANA `Prefix: sl, sl-rozaj …` set test), Money multi-currency prefix disambiguation beyond longest-first.
**Risk:** combinator order interacts with `lexicon→composer→post` fixed order — the generic composer must declare whether it **consumes** lexicon matches or **scans text directly** (fused vs pipeline). The ADR's `AmountComposer` fused the two by holding the lexicon tokens itself; generic version should be explicit: `source="text"` fused (scan text) vs `source="matches"` (consume prior `matches`).

**Recommendation: P3 — derives from P1 normalized view + P2 automaton for lexicon tokens. Pilot on Language variant `Prefix` (the one case where today's `LexiconAlternation` alone is insufficient), then fold SIUnit compound into it.**

---

### 3.7 What We Explicitly Do **Not** Recommend

#### Rejected — ML / NLP NER (named-entity recognition)

Representations like "OpenAI", "Berlin", "EUR/USD" are disambiguated by context windows and trained weights, not by an authority-backed spec. They violate every Paxman invariant: **non-deterministic** (model outputs depend on weights, temperature, beam); **no provenance** (nearest-neighbor embedding, not a Registry/RFC); **no canonical value** (there is no single true answer — "EUR/USD" is an observation, not a canonicalized identifier); **needs world-knowledge** (date "tomorrow" is clock-dependent). The recognition pipeline is `text → spans`, not `text → embeddings → logits → guess`. Any capability that looks like it needs NER (e.g. "detect people/places") is out-of-scope for `paxman` today — it belongs in a caller-side extractor that feeds Paxman a segmented field.

#### Rejected — Fuzzy / approximate matching (Levenshtein, edit distance, Soundex)

Paxman's determinism guarantee (given same input, same contract, same snapshot → same output) would be preserved by a fixed edit-distance threshold, but **provenance would degrade**: `lev("BRMA", "BURMA")==1` being "close enough" has no authority — there's no ISO clause authorizing typo tolerance. The grammar/validation split is specifically designed to emit `INVALID` rather than guess ("no guessing" in `ARCHITECTURE.md`). A caller who needs typo-tolerant search should build an index over canonical forms Paxman returns, not ask Paxman to accept typos.

#### Rejected — Checksum-fused recognition

Tempting to short-circuit `INVALID` earlier by folding a rule's `mod97==1` (IBAN), `MOD-11-2` (ORCID), or `weights×digits % 11` check into the grammar. Resist: the staged pipeline is intentionally **recognition lenient, validation strict** (comparison to `python-stdnum`'s `is_possible vs is_valid` and `phonenumbers`' `_find` vs `_extract_match`). Early checksum rejection would (a) change `MISSING` vs `INVALID` semantics (important for _dedup_candidates_ provenance tracking), (b) require duplicating checksum tables inside grammar files rather than in `rules/data/`, breaking IP's `try: ipaddress… except: return False` precedent. Checks stay in `Rule.matches`.

---

## 4. Cross-Cutting Issues

### 4.1 Ordering & dedup are now correct — protect them

ADR-0008's engine changes (`_dedup_spans` longer-wins within-grammar, total order `(start, end, active index, grammar name)`, cross-grammar preserved) resolved `capability_homogeneity_audit.md` Tier-2 #2/#3. Verbatim `\b` in Email/IPv4 remains an intentional carve-out (ADR-0008 D5). Any new stage must preserve: (a) `RecognitionMatch.raw_text == text[start:end]` at the boundary, (b) containment dedup within-grammar only, (c) `single_value=True` enforcement in `_enforce_single_value_invariant`.

### 4.2 Label separator inconsistency

IBAN `[\s:-]+` never zero-width (glued `IBANDE89…` → `MISSING`), BIC same, ORCID same (`[\\s:-]+` + glued guard), ISSN `[\s:-]*` zero-or-more (glued `ISSN03178471` matches). This is documented behavior (ISSN plan Oracle fix) but no `LabelStage` unifies it. A future `LabelStage(label=alt, separator=Pattern)` stage would deduplicate, but until a second capability hits the same ambiguity (DOIs with `DOI:` vs `doi:`) the inconsistency is tolerable — priority P4.

### 4.3 Shared-data snapshot pattern (M8)

`shared_data/currency_snapshot.json` + `regenerate_currency_data.py` → per-capability `grammar/data/` + `rules/data/` dedup **works**: IP linter layers `api→engine→capabilities→core` remain intact, and drift is gated by `tests/unit/test_currency_data_regeneration.py`. The same snapshot-generator hook should be generalized: `BIC _COUNTRY_CODES` (250, duplicates `rules/iso_9362_ed2022.COUNTRY_CODES`), IBAN SWIFT Registry (Release 100, 90 country rows `length+BBAN regex`, research fielded in `docs/development/research/2026-08-22-iban-canonicalization.md:7` deferred), Language IANA registry (File-Date 2026-08-08, 7990 `Type:language` rows) — all promise drift if hand-copied.

### 4.4 `single_value` semantics annotation

Every shipped grammar today is `single_value=True`. `HOW_TO_ADD_NEW_GRAMMAR.md` clarifies this is the grammar-level annotation for `_enforce_single_value_invariant` (two distinct ISSN/ISBN/IBAN mentions → `AMBIGUOUS/MultipleMentionsError`). A future `FormatCandidateStage` candidate should inherit the parent grammar's `single_value`; a var-len scanner emitting multiple spans per `recognize()` must set `single_value=False` deliberately.

### 4.5 Performance: benchmark is informational, migration gate is parity

`benchmarks/harness.py` (50 iterations CI, informational) does not gate migration; `test_grammar_stage_parity.py` (byte-identical `RecognitionMatch` equality) does (ADR-0008 §4.1). The trie/automaton crossover should be measured via the informational harness but not become a hard gate until an ADR says so.

---

## 5. What This Unlocks — Capability Mapping

| Capability — shipped enhancement | Current workaround | Alternative strategy & why it helps |
|---------------------------------|--------------------|--------------------------------------|
| **URL** — paren-balance goes scanner, not PostStage | `PostStage` loop `count(")")-count("(")` | **Scanner** — depth-aware scan with `(…)`, `[…]`, quotes, `<>` |
| **Phone e164** — 15-digit window as scan | regex overshoot + `_trim_to_e164_boundary` LRU | **Scanner** — bounded digit-run scan |
| **Country name** — 600+ `WholeInputLookup` keys | `frozenset.normalize` membership | **Automaton** — Trie whole-input (parity gate) + **Normalized-view** (`normalize_name` once in Pre) |
| **Currency / Money symbols** — 67 tokens | `LexiconStage` alternation (`longest, qualified`) | stays `LexiconStage` now — automaton only if snapshot grows |
| **SIUnit symbols/names** — 820/650 alternation + `split_*` | regex alternation + inline split classifier | **Automaton** (Trie scan O(n)) + **Generic composer** for `compound` |
| **BIC / IBAN / ORCID / ISSN** — glued label + country gate + `[\\s:-]+` variants | grammar-embedded `frozenset` + `lookahead` | **Normalized-view** + **FormatCandidate** for registries |
| **ISBN** — digit extraction hyphen-tolerant | lookahead `(?=((?:\d[ -]?){12}\d)(?!\\d))\\1` | stays — already regex-native per ADR-0008 §1 |

| Capability — future / planned | What today's pipeline forces | Alternative strategy & why required |
|-------------------------------|------------------------------|---------------------------------------|
| **Language** — BCP47 ABNF + 7000+ ISO 639-3 + 8000 IANA + `Prefix` gating + `_`→`-` | unmaintainable regex + 7000-alternation lexicon | **Scanner or Parser-combinator** for ABNF fields + **Automaton** for large lexicons + **Generic composer** for `Prefix` + **Normalized-view** (`_`→`-`, NFKD) — the only future where Regex/Lexicon alone is insufficient |
| **IBAN registry** — 90 country-specific BBAN `regex` + `length` | `regex` with `mod97` fallback; glued tail absorbed | **FormatCandidate** keyed by `CC` (2-letter) + **Scanner** for paper groups-of-four |
| **ISIN** (`docs/development/research/2026-08-24-isin-canonicalization.md`) — 12-char `(countryCode=ISIN country prefix?)` + 9 alnum + check digit `convert A→10, %10` | regex but check-digit shares `AmountComposer`-style separator | **Regex S1** covers recognition — no new stage, validate via PSS/CSS |
| **CUSIP / LEI / FIGI** — 8+check, 20 `990…`, `BBG…G*` families | character-class driven | Regex S1 already fits |
| **Timestamp / Datetime** — RFC 3339 zoned | loose regex today's Date 4 grammars pattern | **FormatCandidate** (enumerated RFC 3339 strict) |
| **Postal / VAT ID** — per-country width/charset | one-shape regex + country-code dispatch | Regex S1 + LEXICON disambig; large registry → **Automaton** |
| **DOI / URN** — `10.prefix/suffix` with balancing | delimiter-balanced | **Scanner** for balanced token |

---

## 6. Recommendation Tiers

| Tier | Deliverable | Scope | Pilot | Risk | New dep? |
|------|-------------|-------|-------|------|----------|
| **P1a — NormalizedView Pre** | `NormalizedViewStage` + `source: text|normalized` on downstream stages + offset map for length-changing | `paxman/core/grammar/{stages,pipeline}.py`, one new stage file | Phone `strip_separators`, Country `normalize_name`, Language `_→-` (plan Step 1) | Low — length-preserving first; offset deferred | None |
| **P1b — Automaton** | `AutomatonStage(Trie)` stdlib, size-threshold-guarded | `paxman/core/grammar/automaton.py` | SIUnit symbol (820) lexicon harness parity vs `LexiconStage` | Medium — perf crossover measured via informational harness; threshold avoids small-lex regression | None (pure-Python Trie) |
| **P2 — Scanner** | `ScannerStage(scan: (text, index)->(start,end,notation) | None)` | `paxman/core/grammar/scanner.py` | URL paren-balance, Phone e164 15-digit, ISIN check-digit decomposition | Medium — test corpus for nested parens; but migrated from existing `PostStage` loops which already encode the corpus | None |
| **P2 — UnicodeProperty** | generator + `UnicodePropertyStage` alias | `tools/regenerate_unicode_property_data.py` + `grammar/data/unicode_ranges.py` | SIUnit `µΩÅ` coverage vs `\p{Sc}` hand table; Language Han | Low — builds on `regenerate_*` precedent | Build-time source only — vendored ranges at Runtime |
| **P3 — FormatCandidate** | `FormatCandidateStage(candidates: tuple[RegexStage], strategy: "first"|"all")` | `paxman/core/grammar/candidate.py` | Date 4→1 grammar consolidation (parity harness) | Low — but cite each candidate's authoritative section | None |
| **P3 — GenericComposer** | `GenericComposerStage(left, right, separator: Pattern, order, predicate)`; `AmountComposer` becomes alias | `paxman/core/grammar/composer.py` generalization | Language `sl-nedis` Prefix-constrained variant, SIUnit compound | Medium — fuse-vs-consume semantics explicit | None |
| **P4 — LabelStage** | `LabelStage(label: alt, separator: Pattern, fuse: bool)` | `paxman/core/grammar/label.py` | ISBN `ISBN[-13|10]` vs ISSN `ISSN[-L|-H]` vs BIC `BIC|SWIFT` | Low — but inconsistency is documented; defer until DOI third locus | None |

**Rejected (document here so the next contributor doesn't reopen them):** `ML/NLP NER`, `Fuzzy/approximate (Levenshtein/Soundex)`, `Checksum-fused recognition`.

Ordering rationale: P1a+b unblock Language (the only future that genuinely cannot ship without alternatives) and pay for themselves in shipped cleanup; P2 pair migrate the two `PostStage` loops that already are scanners; P3 pair formalize what's currently manual file proliferation; P4 formalizes an inconsistency that remains tolerable without a stage.

---

## 7. Implementation Sketches (per ADR-0008's gate: byte-identical `RecognitionMatch`)

### 7.1 NormalizedView Pre (P1a)

```python
# paxman/core/grammar/stages.py — new
@dataclass(frozen=True, slots=True)
class NormalizedViewStage(Generic[NotationT]):
    normalizer: Callable[[str], str]
    offsets: tuple[int, ...] | None = field(init=False, default=None)

    def __post_init__(self) -> None: ...
    def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
        state.scratch["__normalized"] = self.normalizer(state.text)
        # length-preserving: offsets identity; else store map for downstream translate()
        return PipelineState(
            text=state.text, matches=state.matches, scratch=dict(state.scratch)
        )


# Downstream opt-in: LexiconStage/RegexStage add `source="text"|"__normalized"`
@dataclass(frozen=True, slots=True)
class RegexStage(Generic[NotationT]):
    pattern: str
    notation_fn: Callable[[re.Match[str]], NotationT] | None
    flags: int = 0
    source: str = "text"  # or "__normalized" — view selector, R/O in run()

    def run(self, state):
        subject = (
            state.scratch.get(self.source, state.text)
            if self.source != "text"
            else state.text
        )
        for m in self._compiled.finditer(subject):
            start, end = (
                translate(m.start(), m.end(), offsets)
                if self.source != "text"
                else (m.start(), m.end())
            )
            ...
```

Contribution rule: capability grammar `pre = NormalizedViewStage(normalizer=normalize_name)` then `lexicon = WholeInputLookup(..., source="__normalized")`.

### 7.2 Automaton (P1b) — Trie subset satisfying the lease

Pure-Python Trie with `scan(text) -> list[(token,start,end)]`, longest-at-position-wins (tie → lex order). Alignment with `LexiconAlternation(-len, -is_qualified(token))` means Money/Currency `qualified-first` can stay on `LexiconStage`; automaton's `longest_first=True` covers SIUnit/Country/Language.

### 7.3 Scanner (P2)

```python
@dataclass(frozen=True, slots=True)
class ScannerStage(Generic[NotationT]):
    scan_one: Callable[[str, int], tuple[int, int, NotationT] | None]

    def run(self, state):
        n = len(state.text)
        i = 0
        out = list(state.matches)
        while i < n:
            hit = self.scan_one(state.text, i)
            if hit is not None:
                start, end, notation = hit
                out.append(
                    RecognitionMatch(
                        notation=notation,
                        start=start,
                        end=end,
                        raw_text=state.text[start:end],
                    )
                )
                i = end
            else:
                i += 1
        return PipelineState(text=state.text, matches=out, scratch=dict(state.scratch))
```

Grammar-file closure pattern (mirrors today's `strip_separators` locality):

```python
def _url_scan(text: str, i: int) -> tuple[int, int, URLNotation] | None:
    # scheme_char guard, then balanced-parens track with depth, bare-scheme drop
    ...


class AbsoluteURIRecognition(PipelineGrammar[URLNotation]):
    scanner = ScannerStage(scan_one=_url_scan)
```

### 7.4 FormatCandidate (P3)

Collapses Date's 4 files to one `PatternCandidateStage`-hosting grammar; ISBN splits **not** collapsed (semantics/gating differ — `target_semantics` would diverge per candidate).

### 7.5 Migration mechanics (per ADR-0008 §4 incremental, capability-at-a-time)

* Land `paxman/core/grammar/{normalized_view,automaton,scanner,candidate,composer}.py` with unit tests; add `tests/property/test_grammar_stage_parity_{automaton,scanner}.py` harness shards — probing as informative benchmark, parity as hard gate.
* Migrate pilot capability (Language first, then SIUnit+Currency, then URL+Phone, then Date) — each PR runs `ruff + ruff format --check + pyright + import-linter + pytest` per `.github/workflows/ci.yml` (authoritative gate) + parity/assert.

---

## 8. Verification & Gates

* **Parity harness** (`tests/property/test_grammar_stage_parity.py`) — byte-identical `list[RecognitionMatch]` (`start,end,raw_text,notation`) per grammar × corpus + Hypothesis inputs — **is the migration gate** (ADR-0008 §4.1). Extend shards for each new stage.
* **Benchmark harness** (`benchmarks/harness.py`, informational 50 iterations) — use to choose `LexiconAlternation` vs `AutomatonStage` threshold; does **not** gate CI.
* **Semantic scan** — `tests/unit/test_rule_output_format_purity.py` analog: new stages must not import `rules/*`; `paxman.core.grammar → (no paxman.capabilities import)` leaf preserved; `grammar/data` key-only invariant via `tests/capabilities/<cap>/test_consistency_*.py` pattern.
* **Coverage** — `fail_under=95` `branch=true`; `omit=[tests/*, benchmarks/*]`; new `paxman/core/grammar/*` stages counted.

---

## 9. Open Questions

1. **Fixed order as hard limit?** `PipelineGrammar` today fixes `pre→regex→lexicon→composer→post`. Scanner and automaton are *stage types* inside the fixed order — they don't need reordering. If a future grammar needed `lexicon before regex` for prefilter semantics, would it be a new stage kind within the fixed order or an escape hatch to a bespoke `recognize()`? Default per ADR-0008 §Open Questions: extend fixed order before adding escape hatch; the `NormalizedViewStage` already answers that by being a `pre`.
2. **`scratch` vs `text` branching?** Ship P1a with `require_length_preserving=True` (no offset map) and advance to general offsets only when a capability proves it needs NFKC-expanding translation (SI `²`→`2` is length-preserving — not forced).
3. **Threshold for automaton crossover?** Choose `200` tokens as the Lexicon→Automaton heuristic after measuring `benchmarks/baseline.json` (p50 over word/compound corpora) — revisit when Language ships.
4. **Do we collapse Date's 4 grammars under FormatCandidate or leave them as 4 grammars for `target_semantics` routing clarity?** Either gate passes; collapsing trades 3 files for 1 grammar with 4 candidates but the `active_grammars` surface still shows one name. Keep both options documented; decide at P3 review.
5. **Benchmark gating?** ADR-0008 clarifies `benchmarks/harness.py` is informational non-blocking. Aspirational p50 regression >5% gate is out-of-scope; would be a separate ADR/CI change if ever desired (cf. ADR-0008 benchmarks note).

---

## 10. Detailed Inventory Appendix (supplements §1)

For a 26KB exhaustive per-grammar inventory (every file's `Stages | Pattern | Guard | Tokens | Composition | Post-processing | Notation` plus `BoundaryGuard` catalogue and `grammar/data` catalog), see **sub-agent audit artifact** `subagent-summary-0` (retained verbatim below for provenance, paged to `subagent-summary-0` cache and summarized in the project memory). Key take-aways captured above: 33 grammars, 11 `BoundaryGuard` factories, 18 S1 / 1 S2 / 4 S3 / 4 S4 / 3 S5, all `single_value=True`, `StandardPre(empty_guard=True)` unanimous, `AmountComposer` group-free constraint, duplicate `Currency`/`Money` `word_sign` gating, SIUnit split-prefix inside `notation_fn` not `PostStage`, IBAN paper-groups regex, Phone `e164` LRU trim, URL paren-balance.

---

## 11. What the Sub-Agent Gaps Analysis Found (appendix, verbatim tail)

> *From* `subagent-summary-2` *(future/gaps lane)*: Pre is empty_guard-only while Language needs `__normalized` view; BIC's 250 `_COUNTRY_CODES` duplicates the rule table so `BICXUS…` banks aren't false-blocked; IBAN variable-length greed absorbs glued tail only via downstream `mod97!=1 → INVALID`; Language ABNF regex would be unreadable (needs scanner/Lark); 7000-token lexicons need `Aho-Corasick`; `BoundaryGuard` proliferated 8→11; `WholeInputLookup` is whole-input only; `AmountComposer` not generic; URL `ucschar` grammar would be clearer as scanner; `shared_data/currency_snapshot.json` precedent (M8) must generalize to BIC country/ IBAN registry / IANA registry; feature gating matrix spans `active_grammars` + `requires_features` with language collective/private/grandfathered flags; label separator `[\s:-]+` vs `*` inconsistency.

> *From* `subagent-summary-3` *(staged-pipeline deep-dive)*: 5 optional slots, 6 shipped combos; `text` immutable + `scratch` unused; `RegexStage` 1:1 `Match→Notation`; `LexiconStage`/`AmountComposer` always `finditer(text)`; `AmountComposer` must be group-free, hardcodes `[A-Z]{3}`, separator exactly ` ?`; `WholeInputLookup` whole-input only; `PostStage` per-match cannot merge/split or see neighbors; no recursion/parser combinators.

Both appended for auditability; body above already synthesizes them into the six recommendations.

---

## 12. References

* Survey: `paxman/capabilities/*/grammar/**` (33 grammars, ≈56+ files) + `paxman/core/grammar/**` (6 files) — verified 2026-08-24
* `HOW_TO_ADD_NEW_CAPABILITY.md:250–294` — Regex/Lexicon sanctioned pair and "Beyond the core" extended-strategies table (scanner, format-candidate, pyparsing/Lark, Unicode-property, Aho–Corasick) + `grammar/data` vs `rules/data` purity gate, consistency-test requirement
* `HOW_TO_ADD_NEW_GRAMMAR.md` — adding a grammar to an existing capability
* `ARCHITECTURE.md` — deterministic, provenance-first, recognition/validation split, recognition pipeline contract (`_dedup_spans` longer-wins, total order `(start,end,active_grammars index,grammar name)`, `single_value`), capability isolation
* `paxman/capabilities/AGENTS.md` / `paxman/core/AGENTS.md` — unanimous surface, hard rules, legacy exceptions
* `docs/adr/0008-staged-recognition-pipeline.md` Rev.1 — 5-stage fixed-order pipeline with optional stages, `BoundaryGuard` family, `LexiconAlternation` (longest-first qualified-first D4), `AmountComposer(amount_pattern passed by grammar)`, `PipelineState(scratch)`, migration harness, benchmark informational note, capability-agnostic core (capability `AMOUNT_PATTERN`/`classify_amount_shape` supplied by caller)
* `docs/adr/0007-contract-surface-unification.md` — `CapabilityContract` as sole public base, `Contract` demoted to `_engine_contract`, `getattr(extra_grammars)` probes removed
* `docs/adr/0001-clean-architecture-pipeline.md`, `0003-semantic-affinity-routing.md` (`target_semantics`), `0004-single-value-invariant.md`
* `paxman/core/domain.py` — `Grammar`/`Rule` ABC `__init_subclass__` import-time metadata enforcement (`name`, `strategy`, `provenance`, `target_semantics: frozenset[str]` non-empty, `requires_features: frozenset[str]`, `semantics: str`)
* `paxman/engine/orchestrator.py` — `_recognize` span validation + within-grammar dedup + total order, `_collect_candidates` `target_semantics` routing, `_filter_rules` `pinned→excluded→year→requires_features(last)`, `_validate_affinity`, `_enforce_single_value_invariant`, `_dedup_candidates`
* `paxman/core/grammar/{stages,lexicon,boundary,pipeline,composer}.py` — stage implementations; `PipelineGrammar` base
* `capability_homogeneity_audit.md` — Tier-2 #1–#3 recognition divergences (now resolved via staged migration + engine `_dedup_spans`/total order)
* `docs/development/reports/recognition-handling-library-research.md` (2026-08-04, python-stdnum `compact→validate→format`, phonenumbers `PhoneNumberMatcher(start,end,raw_string)` spans + `_search_index=last_match.end` non-overlap, Lark terminal precedence tuple) — basis for span-first, priority-table recommendations already landed
* `docs/development/research/*` — 10 research docs (ISBN, Money, URL, SI-unit, ISSN, IBAN, BIC, Language, ORCID, ISIN): per-capability primary-source surveys, shape tables, provenance splits, canonical vectors, plan stubs
* Build-time precedent: `tools/regenerate_isbn_range_data.py`, `tools/regenerate_si_prefix_data.py` (`SYMBOL_TOKENS`/`NAME_TOKENS`/`PREFIX_TOKENS`), `tools/regenerate_idna_uts46_data.py` (UTS #46 `IDNA_STATUS/MAPPED` vendored), `tools/regenerate_currency_data.py` (`shared_data/currency_snapshot.json` → Currency+Money `SYMBOL_TOKENS`/`WORD_TOKENS` + `CLDR`/`ISO4217` tables, isolation via snapshot)
* `benchmarks/harness.py` + `benchmarks/README.md` + `benchmarks/baseline.json` — informational, non-blocking per README
* `tests/property/test_grammar_stage_parity.py` — migration **byte-identical `RecognitionMatch`** gate (hard), with `tests/unit/test_rule_output_format_purity.py` (output_format scan) and `tests/capabilities/<cap>/test_consistency_*.py` (grammar/data ↔ rules/data) as supporting gates

*(End of file — 2026-08-24, synthesised from exhaustive audit + 4-way sub-agent fan-out)*
