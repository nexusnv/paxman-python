# Locale Recognition Support — Cross-Capability Abstraction Study — paxman-python

**Date:** 2026-09-02
**Scope:** Cross-cutting architecture study, not a single-capability canonicalization survey. It inventories every place Paxman already performs **locale recognition support** — recognizing localized (non-English / endonym / exonym) spellings of a capability's values ("Alemania" → `DE`, "euro" → `EUR`, "deutsch" → `de`) — extracts the recurring pattern, surveys the external authority landscape (Unicode CLDR, IANA/BCP 47, ISO, IUPAC, ecosystem libraries), and evaluates whether locale support can be promoted to a **first-class, streamlined mechanism** in `paxman.core` that any capability can adopt — or whether the domain-to-domain dispersion makes consolidation infeasible. No source code, tests, or configuration were modified.

**Evidence basis:** Shipped-code dossiers of Country, Currency, Money, Language, SIUnit (negative case) and the incoming Chemical Element research (`docs/development/research/2026-09-02-chemical-element-canonicalization.md`); kernel machinery read verbatim from `paxman/core/grammar/` (`normalizers.py`, `scan_context.py`, `matcher_spec.py`, `matchers/lexicon.py`, `engine_loop.py`) and `paxman/engine/orchestrator.py`; conventions docs `HOW_TO_ADD_NEW_CAPABILITY.md`, `ARCHITECTURE.md`, `docs/adr/0009-recognition-kernel.md`, `paxman/shared_data/README.md`; data-volume measurements executed against the live tree (counts below). External primary sources fetched 2026-09-02: Unicode CLDR release notes (cldr.unicode.org), `unicode.org/policies/locales_stability.html`, CLDR currency-names page, RFC 5646 (rfc-editor.org), Unicode License V3 (`unicode.org/license.txt`), pycountry 26.2.16 (PyPI), `i18n-iso-countries` (GitHub). Secondary: npm `language-tags` docs, translatewiki/Drupal CLDR references. **Repo state: `dev @ 28f229e`** — engine owns per-grammar containment dedup, two-loci feature gating (rule locus in `_filter_rules`, matcher locus in `engine_loop`), `Grammar.single_value` enforcement, and `Capability.format_value()` as the presentational seam.

**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md (§ grammar strategy, § authority features / `requires_features`), ARCHITECTURE.md (recognition/validation boundary, provenance, determinism), ADR-0009 Recognition Kernel (lexicon as data, matcher feature omission), HOW_TO_ADD_NEW_GRAMMAR.md, the research precedents (`2026-08-22-iban-canonicalization.md`, `2026-08-23-bic-canonicalization.md`, `2026-08-23-language-canonicalization.md`, `2026-09-02-chemical-element-canonicalization.md`), and `paxman/shared_data/README.md` (M8: shared vocabularies regenerate into per-capability tables, never imported across capabilities).

---

## Executive Summary

Locale recognition support — recognizing the same authoritative value spelled in more than one natural language — is a **recurring, five-part pattern** that has already been re-implemented, with drift, in four shipped capabilities (Country, Currency, Money, Language), deferred in one planned capability (Chemical Element), and absent in one that could plausibly use it (SI Unit). The question studied here: can it be abstracted as a **first-class citizen** of Paxman?

**Verdict: yes — but as a mechanism-level seam, not a data-owning "locale engine."** The repetition is real, and it is *streamlinable*: the recognition kernel already contains ~90% of the reusable machinery (normalized views, `LexiconMatcher`, `WholeInputLookup`, two-loci feature gating, provenance stamping, snapshot→generated-data workflow). What is missing is a thin shared vocabulary — locale-tagged alias tables, one pinned CLDR snapshot, a named set of precedence/ambiguity policies, and a homogenized contract convention — plus the documentation (an ADR) that makes the pattern deliberate instead of emergent. What must **not** be centralized is exactly what Paxman's architecture already forbids centralizing: the authority mappings themselves (token→canonical value), the per-domain ambiguity policy, and the per-domain locale-subset choice. The dispersion observed across capabilities is dispersion in *policy*, not in *mechanism* — and Paxman's layer discipline was built for precisely that split.

Key findings that shape the recommendation:

1. **The pattern is genuinely repeated, five parts each time.** (a) recognition-only key sets in `grammar/data/`, (b) authority token→canonical maps in `rules/data/` behind `LOOKUP_TABLE` rules with CLDR provenance, (c) a syntax normalizer shared between grammar keys and rule lookups, (d) feature gating at the rule locus (`include_localized` → recognized-but-unvalidated → `INVALID`), (e) a pinned data-source version in `Provenance`. See §2.2.
2. **The drift is real and measurable.** Three different pinned CLDR versions coexist today — Country: **CLDR v45** (2024, hand-curated zh/es/fr, 183 entries), Language: **CLDR v46** (2025, generated 24-entry subset), Currency/Money: **CLDR v47** (2025, generated en+es, 62 words / 67 symbols) — while upstream CLDR is at **v48.2.1** (2026-07-08). Three different syntax normalizers exist (`Country.normalize_name` upper-casing, `Language.normalize_name` lower-casing, Currency's lowercase fold). Three different multi-authority policies exist (single-authority precedence, dual-rule value agreement, candidate-tuple + contract opt-in). None of this is documented as a deliberate menu. See §2.3.
3. **Locale authority is domain-optional — the decisive fragmentation fact.** CLDR is the world's authority for localized country, currency, and language display names; it has **no authority status** for chemical element names in other languages (IUPAC publishes English only — the Element research DEFERs localized aliases to a community extension), SI unit names, CSS color names, or SPDX license names. Of the 30 MILESTONE roadmap rows, only **Timezone (#3)** adds a new locale-data consumer. A first-class abstraction must therefore be **opt-in per capability**, not a global assumption. See §3.4, §4.
4. **The IANA registry explicitly delegates localization to CLDR** — RFC 5646 §3.1.5: *"'Description' fields are not intended to be the localized English names for the subtags. Localization or translation of language tag and subtag descriptions is out of scope"*; §3.9: *"the registry does not contain translations for subtag descriptions … Sources for localized data based on the registry are generally available, notably [CLDR]."* There is exactly **one** authority to integrate for display-name localization, and its license (Unicode License V3) permits bundling derived data. See §3.1–3.3.
5. **Two meanings of "locale" must not be conflated** (§5.1): localized *spellings of a domain's values* (the subject of this report), and *locale identifiers as values* (already the Language capability's BCP 47 grammar's job). A third candidate — an "input locale" contract parameter that scopes recognition to one locale — is analyzed and **rejected** (§6 Option C): it changes the `MISSING`/`INVALID` polarity, makes recognition dependent on unknowable input metadata, and buys nothing the union-lexicon + gated-validation model already provides.
6. **The kernel already has an unused matcher-level gate** (`MatcherSpec.requires_features`, enforced in `engine_loop` per ADR-0009 §13; zero shipped grammars use it). A locale seam can thus offer the two gating polarities as a named choice: rule-gated (shipped default → `INVALID` when off) vs matcher-gated (→ `MISSING` when off). See §7.3.

Recommended target design (§7): a `LocaleAliasTable` frozen dataclass + lexicon-spec builder in `paxman.core`, one `paxman/shared_data/cldr_snapshot.json` with a single pinned CLDR version feeding per-capability regenerators (the existing `currency_snapshot.json` + M8 pattern, generalized), a documented `include_localized: bool = False` contract convention enforced by a homogeneity test rather than a base-class field, named precedence policies, and a shared data-consistency test convention generalized from the Country/Language exemplars. Open decisions and the CLDR re-pinning migration path are in §8–§9.

---

## 1. Target User

| Persona | Why they need locale recognition support | Typical context |
|---------|-------------------------------------------|-----------------|
| Data-entry operator (multilingual org) | Types `Alemania`, `euro`, `deutsch` from a German UI; the canonical answer must still be `DE`, `EUR`, `de` | CRM/address book cleanup, spend reports |
| Pipeline engineer | Cleans mixed-locale columns without knowing which locale each row is in; needs deterministic, provenance-carrying canonicalization | ETL over CSV/JSON dumps |
| Library contributor | Adds a new capability (Element, Timezone) and needs the locale-data workflow scaffolded instead of re-invented | `tools/new_capability.py` + plan flow |
| Community extension author | Wants to ship localized aliases for a domain Paxman defers (element names in German/Japanese) | `extra_grammars` / `register_grammar` seam |
| Paxman maintainer | Wants one CLDR pin, one regeneration workflow, one policy vocabulary — not per-capability drift | release housekeeping, `--check` CI |

**User-visible contract (unchanged by this study):** the caller supplies raw human text plus a contract; Paxman returns one canonical value with provenance. Locale support is invisible in the happy path (`"Alemania"` + `CountryContract(include_localized=True)` → `DE` with CLDR v45 provenance) and produces a defined status when disabled (`INVALID` under the shipped rule-locus policy) — §7.3 formalizes that polarity as a documented choice.

---

## 2. The Evidence: Where Locale Recognition Repeats Today

### 2.1 Per-capability dossiers (shipped + incoming)

**Country** (`paxman/capabilities/Country/`)

| Aspect | Finding | Evidence |
|---|---|---|
| Locale surfaces | English names/synonyms (ISO 3166-1), historical names (ISO 3166-3), **localized names zh/es/fr (CLDR v45)** | `grammar/data/{english,chinese,historical,localized}_names.py` |
| Recognition keys | ENGLISH 307, CHINESE 80, HISTORICAL 33, LOCALIZED 181 (measured; CJK ≈120, accented-Latin 17 e.g. `México`, `Perú`) | measured against live tree |
| Authority maps | `NAME_TO_ALPHA2` 254, `SYNONYM_TO_ALPHA2` 85, `FORMER_NAME_TO_ALPHA2` 33, `LOCALIZED_TO_ALPHA2` 183 | `rules/data/{iso_3166_ed2024,iso_3166_ed2020_part3,cldr_ed2025}.py` |
| Recognition grammar | one `NameGrammar` — union of all key sets into a single trie lexicon (`representation="trie"`, `view="country_normalized"`, `BoundarySpec.WORD`); emits raw span, no mapping | `grammar/name_recognition.py` |
| Gating | rule locus: `SectionLocalizedNames.requires_features = {"include_localized"}`; recognition **not** gated | `rules/cldr_localized_ed2025.py:48` |
| Multi-authority policy | **single-authority precedence**: ISO name rule *defers* when `include_localized` enabled and the key is CLDR-owned — a localized name never yields an ISO-provenance candidate | `rules/iso_3166_ed2024.py:195-224` |
| Normalizer | `normalize_name()` in `Country/notation.py` — NFKD, separator→space (hyphen/en-dash/slash), punctuation strip, **uppercase** | `Country/notation.py:38-68` |
| Provenance pin | CLDR **v45**, 2024, `kind="registry"`, gated | `rules/cldr_localized_ed2025.py:24-32` |
| Contract field | `include_localized: bool = False`, `include_historical: bool = False` | `Country/contract.py:35-36` |
| Consistency test | grammar keys ⊆ union of rule-data keys, one-directional, **per-authority ownership** (ISO owns English, ISO 3166-3 former, CLDR localized) | `tests/capabilities/country/test_data_consistency.py` |

**Language** (`paxman/capabilities/Language/`)

| Aspect | Finding | Evidence |
|---|---|---|
| Locale surfaces | BCP 47 tags (`SeparatorFold` view: `_`→`-`, BCP 47 §2.1 provenance), ISO 639 codes, English display names, **localized display names (CLDR v46 subset, 24 entries)** | `grammar/{bcp47_tag_recognition,language_name_recognition}.py`, `grammar/data/{names,english_names,localized_names}.py` |
| Recognition keys | ENGLISH 60 + LOCALIZED 24, generated from `paxman/shared_data/language_snapshot.json`; subset documented as curatorial, full IANA Description set (7,900+) and CLDR root "NOT YET MATERIALIZED" | measured; `shared_data/language_snapshot.json:_meta` |
| Authority maps | `NAME_TO_CANONICAL` 60 + `LOCALIZED_NAME_TO_CANONICAL` 24; plus ISO 639-1/2/3/5 and IANA subtag data modules | `rules/data/english_language_map.py`, `rules/data/iso_639_*.py`, `rules/data/iana_*.py` |
| Recognition grammar | `LanguageNameGrammar` — `WholeInputLookup` over union keys with `normalize_name` | `grammar/language_name_recognition.py` |
| Gating | rule locus: `SectionLocalizedNames.requires_features = {"include_localized"}`; in-subset localized names without the flag are `INVALID` (grammar recognizes, engine drops rule); out-of-subset names are `MISSING` (false-negative safety contract) | `rules/cldr_language_display_name_ed2025.py:27-42`; snapshot `_meta.completeness_note` |
| Multi-authority policy | **dual-rule value agreement**: `SectionEnglishNameMapping` and `SectionLocalizedNames` both target semantics `"language_name"`; no explicit precedence — keys that collide do so with the *same* canonical value, so engine dedup collapses them | `rules/iso_639_1_ed2002.py:60-73` vs `rules/cldr_language_display_name_ed2025.py:37-42` |
| Normalizer | `normalize_name()` in `Language/notation.py` — like Country's but **lowercase** | `Language/notation.py:8` |
| Provenance pin | CLDR **v46**, 2025 (charts summary URL), gated | `rules/cldr_language_display_name_ed2025.py:12-20` |
| Contract field | `include_localized: bool = False` (+ `include_collective`, `include_private`) | `Language/contract.py:18-21` |
| Consistency test | same convention as Country, snapshot-driven | `tests/capabilities/language/test_data_consistency.py` |

**Currency** (`paxman/capabilities/Currency/`)

| Aspect | Finding | Evidence |
|---|---|---|
| Locale surfaces | ISO 4217 alpha-3 codes; CLDR symbols (`$`, `US$`, `€`); **CLDR English display-name words** (`euro`, `dollar`, …); CLDR data extracted **en + es** | `grammar/{code,symbol,word}_recognition.py` |
| Recognition keys | `WORD_TOKENS` 62 — GENERATED from CLDR v47 English display names, lowercase, longest-first | `grammar/data/currency_words.py` |
| Authority maps | `NAME_TO_CODES` 62 (word → **tuple** of codes: `"dollar"` → 29 dollar-family codes; `"euro"` → `("EUR",)`), `SYMBOL_TO_CODES` 67, `CURRENCY_CODES` 178 | `rules/data/{cldr_currencies,iso4217_list_one}.py` |
| Recognition grammar | `WordRecognition` — `LexiconStage` alternation, `re.IGNORECASE`, `BoundaryGuard.word_sign()`, plural lookahead (`"Dollars"` no); emits lowercase `shape="word"` | `grammar/word_recognition.py` |
| Gating | **none** — CLDR words/symbols are always-active core surface (`requires_features = frozenset()`); no `include_localized` exists in CurrencyContract | `rules/cldr_currencies_ed2025.py:126,170` |
| Multi-authority policy | **candidate-tuple + contract opt-in**: single candidate definitive; multi-candidate resolved only via `contract.default_currency` guarded against the token's own candidate tuple; otherwise `INVALID`, never silently dropped | `rules/cldr_currencies_ed2025.py:35-109` |
| Normalizer | lowercase fold at emit (D4 divergence: Money keys are Title-Case, Currency lowercase — documented in the generated header) | `grammar/word_recognition.py:20-22`; `rules/data/cldr_currencies.py` header |
| Provenance pin | CLDR **v47**, 2025, `kind="specification"`, always active | `rules/cldr_currencies_ed2025.py:24-32` |
| Data flow | **generated** from `paxman/shared_data/currency_snapshot.json` via `tools/regenerate_currency_data.py` — one snapshot feeds **both** Currency and Money | `shared_data/README.md` |

**Money** (`paxman/capabilities/Money/`) — structurally a mirror of Currency (same three grammars, same two CLDR sections, same generated data), diverging only where its domain demands it: amount handling (`precision`), and `dollar_sign_currency` (vs `default_currency`) for resolving bare/shared symbols next to amounts. The pair is the repo's **existing cross-capability shared-snapshot precedent** — the exact shape a locale seam would generalize.

**SIUnit** (`paxman/capabilities/SIUnit/`) — **negative case.** Name recognition is an English-only lexicon (`CaseFold` view, trie; `grammar/name_recognition.py`); no localized unit names, no CLDR data, no `include_localized`. Unit names *do* exist in many languages in the wild (`Eisen`? no — but `kilo`, German `Kilogramm`, French `kilogramme`), and BIPM publishes the SI brochure in English and French only — yet no capability-level decision has ever been recorded for or against localized unit names. A first-class seam makes such decisions explicit (see §7.4) instead of silent.

**Chemical Element (incoming — research complete, unimplemented)** — `docs/development/research/2026-09-02-chemical-element-canonicalization.md` line 66 inventories `Localized non-English names` (`Eisen`, `hierro`, `sølv`) with disposition **DEFER**: *"localized-alias lexicon via community extension (Language `LOCALIZED_LANGUAGE_KEYS` precedent)"*. IUPAC publishes names in English only (Red Book IR-3.1; "well-established and very different names" in other languages, unstandardized). This is the first capability to plan for locale aliases **without any authority to cite** — and it instinctively reached for the Language capability's data-module shape as its precedent, confirming both the demand for and the informality of the pattern.

### 2.2 The recurring five-part motif (extracted pattern)

Every shipped locale consumer implements the same skeleton:

```text
┌─ 1. RECOGNITION KEYS      grammar/data/*_names.py | *_words.py     — key-only frozensets, no canonical mapping
├─ 2. AUTHORITY MAP         rules/data/*.py                          — token → canonical value(s), owned by a Rule
├─ 3. SYNTAX NORMALIZER     notation.normalize_name() | kernel view  — shared by (1) keys and (2) lookup keys
├─ 4. FEATURE GATE          Rule.requires_features={"include_localized"} — rule locus; recognition ungated
└─ 5. PROVENANCE PIN        Provenance(authority="Unicode", version="45"|"46"|"47", kind=registry|specification)
```

plus two *meta-mechanisms* that are already convention rather than code:

- **6. Data flow** — hand-curated (Country) or snapshot-generated (`shared_data/*.json` → `tools/regenerate_*.py`, `--check` in CI);
- **7. Consistency test** — recognition keys ⊆ union of authority keys, with per-authority ownership assertions (`tests/capabilities/{country,language}/test_data_consistency.py`).

Paxman's own conventions already codify parts 1–5 piecemeal: `HOW_TO_ADD_NEW_CAPABILITY.md` §"Choose Lexicon" (keys-only `grammar/data/` tables, syntax-only cleaning in grammar, semantic mapping in rules), §"Rules validate … and carry provenance" (CLDR listed among authority tables), and §"Authority features use `requires_features`" (*"A flag like `include_localized` gates the CLDR rule that validates localized names, not the grammar. Recognition still runs and produces a notation, but the engine drops the gated rule, so the recognized-but-unvalidated input yields `INVALID`."*). `ARCHITECTURE.md` (line 148) documents the presentation side: localized names format through the current conversion tables while retaining Unicode/CLDR provenance.

### 2.3 Divergence ledger — what drifted between implementations

| # | Dimension | Country | Language | Currency / Money | Consequence |
|---|-----------|---------|----------|------------------|-------------|
| 1 | CLDR pin | **v45** (2024) | **v46** (2025) | **v47** (2025) | three coexisting pins; upstream at v48.2.1; no single "our CLDR" statement |
| 2 | Locale subset | zh/es/fr, 183 entries, **hand-curated** | en/fr/de/es endonyms, 24 entries, **generated** | en(+es) words, 62, **generated** | no common subset-selection policy; Country's curated set predates the snapshot workflow |
| 3 | Key normalization | NFKD + separators + **upper** | accent-strip style + **lower** | **lowercase** fold | three normalizers; each rules-side map must re-derive the same view |
| 4 | Gating | rule-gated (`INVALID` when off) | rule-gated (`INVALID`; `MISSING` for out-of-subset) | **always active, ungated** | the flag exists in 2 of 4; is its absence in Currency a decision or an omission? (unrecorded) |
| 5 | Multi-authority policy | single-authority precedence (ISO defers to CLDR) | dual-rule value agreement (no explicit precedence) | candidate-tuple + `default_currency` opt-in | three policies; none named as such; a contributor must rediscover which applies |
| 6 | Cardinality | 1 key → 1 alpha-2 | 1 key → 1 code (curated) | 1 key → **N** codes (`dollar` → 29) | ambiguity handling is domain semantics — cannot be absorbed by a shared table shape, only declared alongside it |
| 7 | Matcher machinery | `LexiconMatcher` trie on kernel view | `WholeInputLookup` (whole-input surface) | legacy `LexiconStage` alternation | three idioms for the same job; kernel consolidation exists but adoption is uneven |
| 8 | Data flow | hand-edited files | snapshot JSON + generator | snapshot JSON + generator (shared pair) | Country remains the only hand-curated locale table |
| 9 | Surface type | mid-text lexicon (span-bearing) | whole-input only | mid-text alternation | whole-input vs scan-in-text is a real per-domain choice; both need locale keys |
| 10 | Suppression interplay | name matcher not suppressible | name grammar not suppressible | word matcher not suppressible | consistent in outcome, undocumented as policy |

### 2.4 Kernel machinery that already exists (the abstraction's foundation)

| Mechanism | Location | Locale-relevant role |
|---|---|---|
| `Normalizer` protocol + `NormalizerSequence` (no-expansion invariant, offset threading) | `paxman/core/grammar/normalizers.py` | the substrate for per-locale view composition |
| `CaseFold` / `AccentStrip` (carries **CLDR** provenance) / `SeparatorFold` (carries **BCP 47** provenance) | `paxman/core/grammar/normalizers.py:204-255` | locale-adjacent normalization is already provenance-stamped at the kernel |
| `View` + `ScanContext` (lazy per-name views, two-array offset mapping) | `paxman/core/grammar/scan_context.py` | one substrate, many normalized views — the "which view does this locale match on" answer |
| `LexiconMatcher` (trie > 500 tokens, alternation ≤ 500, FlashText-style word-anchored trie) | `paxman/core/grammar/matchers/lexicon.py` | the locale-lexicon workhorse; ADR-0009 §9 explicitly scopes it to "pure vocabulary" domains incl. future chemical elements |
| `WholeInputLookup` | `paxman/core/grammar/` (composer) | whole-input name surfaces (Language names) |
| `MatcherSpec.requires_features` + `suppressible` — **matcher-locus gating, currently unused by any shipped grammar** | `paxman/core/grammar/matcher_spec.py`; enforced in `engine_loop.py:66-91` | the second gating polarity (feature-off → grammar silent → `MISSING`) already exists in the engine |
| Rule-locus gating + dangling-feature fail-fast | `paxman/engine/orchestrator.py:494-510` (`ContractError` on unknown feature attr) | shipped locale gating; fail-fast on typos |
| `Provenance` / `VersionStamp` determinism | `paxman/core/domain.py` | pinned CLDR version is already a first-class provenance concept |
| Snapshot → generated-data workflow + M8 mandate | `paxman/shared_data/{currency,language}_snapshot.json`, `shared_data/README.md`, `tools/regenerate_*.py` | "shared vocabulary regenerates into per-capability tables, never imported across capabilities" — the exact constitutional rule a locale seam must respect |

### 2.5 What does *not* exist today (the gap a first-class seam closes)

- **No shared locale vocabulary.** `grep -ri "locale" paxman/core/` returns zero hits: `paxman.core` has no concept of a locale, a locale tag, or a locale-tagged key set. Every capability invents its own naming (`localized_names.py` × 3, `chinese_names.py`, `currency_words.py`) with different shapes (key `frozenset` vs `dict`).
- **No single CLDR pin** — version skew (§2.3 #1) is invisible until a cross-capability inconsistency appears.
- **No named policy menu** — precedence/ambiguity/gating decisions live in docstrings and one `getattr(contract, "include_localized", False)` seam in Country's ISO rule.
- **No scaffold support** — `tools/new_capability.py` cannot prewire a locale-alias grammar/data pair; the Element research had to hand-write its DEFER rationale by imitating Language.
- **No generalized consistency test** — the Country/Language exemplars are duplicated, not shared.

---

## 3. External Authority Survey (primary sources, fetched 2026-09-02)

### 3.1 Unicode CLDR — the single display-name authority

| Attribute | Finding |
|---|---|
| What it publishes | Localized display names for **territories (countries), currencies, languages, scripts, time zones (metazones + exemplar cities), units** — per locale, with short/standard/narrow variants and alt-marked alternates |
| Current version | **CLDR 48.2.1, 2026-07-08** (48.1 2026-01-08; 48.2 2026-03-17); LDML spec tr35-77/-78 |
| Locale coverage | **104 Modern + 13 Moderate + 57 Basic** locales (v48) — "Modern: suitable for full UI internationalization, including all CLDR locale names, country names, timezone names, currencies in use" |
| Distribution | GitHub `unicode-org/cldr-json` releases (e.g. tag `48.2.0`, patch `48.2.1` for tz 2026c compatibility) — machine-readable JSON exactly suited to snapshot extraction |
| Currency-name uniqueness | CLDR translation guideline: *"Currency Names must be Unique; the same name can't be used for two different currency codes"* — per-locale display names are unique, but a *single word* like "dollar" still appears inside many names, which is why Currency's word map carries **candidate tuples** |
| Stability | Unicode **Locales Stability Policy**: *"Deprecated elements remain and can be used, although their usage is strongly discouraged"* — data is append-mostly; identifiers stable; CLDR Data Retention Policy keeps deprecated territory data ≥ 5 years after IANA deprecation |
| License | **Unicode License V3** — copy/publish/sell permitted with notice; bundling derived snapshot data in Paxman is explicitly permitted |

**Implication:** a pinned-CLDR-snapshot workflow is legally and technically unproblematic, and CLDR's append-mostly stability matches Paxman's determinism-by-snapshot doctrine (`Provenance.version` = the pin).

### 3.2 IANA Language Subtag Registry — explicitly *not* a locale-name source

RFC 5646 (BCP 47), §3.1.5: *"'Description' fields are not intended to be the localized English names for the subtags. Localization or translation of language tag and subtag descriptions is out of scope of this document."* §3.9: *"the registry does not contain translations for subtag descriptions or for tags … Sources for localized data based on the registry are generally available, notably [CLDR]."* Multiple `Description` fields per record are synonyms for *identification* (e.g. `ro`: "Romanian", "Moldavian", "Moldovan" — mirrored in Paxman's `NAME_TO_CANONICAL`), not translations. §3.4 stability rule 3: Description fields "MUST NOT be changed in a way that would invalidate any existing tags."

**Implication:** Language's future "full English names from IANA Descriptions" plan (snapshot `_meta`) and its localized-name plan point at **two different authorities** (IANA for English synonym sets; CLDR for localization) — a distinction the current 24-entry subset blurs. A first-class seam should name both.

### 3.3 ISO 3166 / ISO 4217 / ISO 639 — code registries, not name authorities

The ISO registries define *codes*; their published name lists (ISO 3166-1 English/French short names upper case; ISO 4217 English currency names) are display conveniences, not localized-name repositories. This is why every Paxman locale consumer reaches for CLDR for anything non-English — and why Country's ISO↔CLDR precedence seam (§2.1) exists at all: English short names are owned by ISO 3166-1 *and* reproduced (sometimes identically) by CLDR.

### 3.4 Domains with **no** locale authority (the fragmentation boundary)

| Domain | Localized names in the wild | Authority status |
|---|---|---|
| Chemical element names | `Eisen`, `hierro`, `sølv`, `鉄` | **None.** IUPAC (Red Book IR-3.1) publishes English only; CLDR has no element names; national societies/Wikipedia are informal. Element research → DEFER to community extension |
| SI unit names | `Kilogramm`, `kilogramme` | None in practice; BIPM brochure is EN/FR; unstandardized beyond that |
| CSS color names | informal translations | None; W3C keywords are English |
| SPDX license names | n/a | None; SPDX identifiers are ASCII |
| MIME/charsets/TLD/semver/UUID/DOI/LEI/PAN | n/a | None |

**Implication:** any locale abstraction must treat localized aliases as an **optional, per-capability, sometimes authority-less** feature — never a pipeline assumption.

### 3.5 Ecosystem practice (secondary unless noted)

| Library | Model | Lesson for Paxman |
|---|---|---|
| `pycountry` 26.2.16 (PyPI, fetched) | wraps Debian `iso-codes`; ships **gettext translation catalogs** (`LOCALES_DIR`, domains `iso3166-1`…); 7.7 MB sdist; runtime fuzzy lookup | Bundled translations are a *size* decision — and 7.7 MB is what "just ship everything" costs. Paxman's curated-subset + snapshot workflow is the leaner, determinism-preserving alternative |
| `i18n-iso-countries` (npm, fetched) | **per-locale JSON packs** under `langs/`, explicit `registerLocale(...)` to control bundle size; official/alias `select` per name | The "locale pack with explicit opt-in" pattern — consumer-side model of what Paxman's `include_localized` + future per-locale scoping could formalize |
| Babel / ICU (`LocaleCanonicalizer`, UTS #35 Annex C) | runtime CLDR megadata | cited already in ADR-0009 as a *rejected* dependency class — Paxman's snapshot discipline is the deliberate counter-model |
| `python-stdnum` | no localized-name recognition | mainstream identifier validators ignore the surface Paxman treats as core |

---

## 4. Future-Capability Forecast (MILESTONE.md)

| MILESTONE row | Domain | Locale recognition needed? | Mechanism fit |
|---|---|---|---|
| #3 Timezone | IANA tz + CLDR | **Yes** — metazone/exemplar-city names are locale display data (CLDR); MILESTONE already cites "CLDR timezone data" | direct consumer of the proposed seam |
| #5 UUID, #7 MIME, #8 Charset, #11 DOI, #13 HTTP header, #14 Unicode norm, #18 LEI, #19 PAN, #21 SemVer, #24 TLD, #26 HTML tag, #27 Postal, #28 Coordinates, #30 BCP 47 tag | — | **No** (aliases yes — e.g. charset alias tables — but not *localized names*) | n/a |
| #20 SPDX | license list | No localized names; English synonyms only (registry `LicenseName`/aliases — an alias table, not locale data) | alias seam (non-locale) |
| #22 Chemical element | IUPAC | **Deferred** — localized aliases exist informally, no authority (§3.4) | community extension via `extra_grammars`; the seam should make that path cheap |
| #25 CSS color | W3C | No | n/a |

Also uncounted but real: **expansion of the shipped three** — Country to full CLDR coverage, Language to full IANA Descriptions + CLDR root, Currency/Money to more locales' words/symbols. Each is currently a hand-migration; each would be a snapshot bump under the proposed workflow.

**Quantified conclusion:** locale data consumers are scarce (≈1 new capability per roadmap cycle) but *recurring and cross-cutting* — exactly the profile where an unowned convention drifts (§2.3 is the receipt) and a small owned mechanism pays for itself.

---

## 5. Feasibility Analysis

### 5.1 Disambiguating "locale" — three different things

1. **Localized spellings of a domain's values** (this report's subject): `"Alemania"` → `DE`; `"euro"` → `EUR`; `"deutsch"` → `de`; `Eisen` → `Fe` (deferred). Recognition-side vocabulary.
2. **Locale identifiers as a value domain**: `fr_FR`, `zh-Hans-CN` — already the Language capability's BCP 47 grammar (with `SeparatorFold` for `_`→`-`). Not a new capability, and not this report's subject.
3. **The user's/input locale as a contract parameter**: *"only match Spanish spellings"*. Analyzed in §6 Option C — rejected for v1.

A first-class abstraction must name its scope precisely: **(1) only**, with (2) explicitly out of scope and (3) explicitly rejected.

### 5.2 What CAN be first-class (mechanism — consolidate this)

| Mechanism | Why it consolidates cleanly | Already present? |
|---|---|---|
| Locale-tagged alias-table data shape (keys-only, provenance-pinned) | pure dataclass; no authority knowledge; import-safe in `paxman.core` | No |
| Lexicon-spec builder from alias tables (view + boundary + emit choice) | kernel `MatcherSpec` is already "recognition as data"; the builder is a constructor | Half (hand-built today) |
| Named normalizer conventions (upper/lower/accent-strip) as *declared* view choices | kernel `Normalizer`s exist; per-capability `normalize_name` duplicates remain | Half |
| Two-loci feature gating with named polarity | engine + kernel enforce both loci today | **Yes** (matcher locus unused) |
| One pinned CLDR snapshot + per-capability regenerators + `--check` | M8 mandate + two working exemplars (currency, language) | Pattern yes, CLDR-wide no |
| Shared data-consistency test convention (keys ⊆ authority keys, per-authority ownership) | two duplicated exemplars ready to generalize | Half |
| Provenance pinning of locale publications | `Provenance` is core | **Yes** |
| Scaffold prewire for locale-alias pairs | `tools/new_capability.py` extension | No |

### 5.3 What CANNOT be first-class (policy/data — keep per-capability, by design)

| Constraint | Source | Consequence |
|---|---|---|
| **No cross-capability imports** | import-linter; AGENTS.md anti-patterns | a `paxman.core/locale` module can ship *shapes and factories*, never a country/currency/element table |
| **Grammars recognize only** — never map tokens to canonical values | HOW_TO_ADD_NEW_CAPABILITY.md §recognition/validation boundary; F3 plan | alias tables stay key-only; the canonical mapping is inviolably rule-side |
| **Authority data in `rules/data/`, recognition keys in `grammar/data/`** | research-skill hard rule / house convention | the seam must not blur the two loci it is trying to unify |
| **Determinism by snapshot** | AGENTS.md; ARCHITECTURE.md | no runtime CLDR, no environment-dependent locale lists; only pinned snapshots |
| **Ambiguity is domain semantics** | Currency's 1:N `dollar` vs Country's 1:1; CLDR uniqueness guarantee (§3.1) ≠ word-level uniqueness | precedence policies stay per-capability; the seam's job is to *name* them, not implement them |
| **Locale authority is optional** | §3.4 | the seam must be adoptable incrementally, with a community-extension route for authority-less domains |

### 5.4 Verdict

**The direction is feasible and worth doing — as a first-class *mechanism*, not a first-class *dataset*.** The user's two hypotheses are both half-right:

- *Feasible:* the five-part motif is real, the kernel already implements ~all reusable parts, two snapshot-driven exemplars exist, and exactly one external authority (CLDR) covers the localizable domains. A contributor-facing seam (dataclass + builder + snapshot workflow + named policies + consistency tests + ADR) removes the drift documented in §2.3 and makes Element/Timezone adoption a configuration exercise.
- *Not fully consolidable:* cardinality, ambiguity policy, gating polarity, locale-subset completeness, and — for element/unit/color domains — the very existence of an authority are irreducibly per-capability. Any abstraction that tried to own those would violate the recognition/validation boundary or the no-cross-capability-import rule. The correct end state is: **one mechanism, many policies, all named.**

---

## 6. Design Options Considered

| Option | Description | Assessment |
|---|---|---|
| **A — Status quo** | Keep per-capability implementations; document the pattern in HOW_TO_ADD_NEW_CAPABILITY.md only | Reject. Drift is active (three CLDR pins, three normalizers, three policies, two gating idioms); every new consumer re-decides §2.3's ten rows |
| **B — Core mechanism toolkit ("locale alias support")** *(recommended)* | `LocaleAliasTable` + lexicon-spec builder + named policies + consistency-test convention + scaffold prewire + ADR. Data stays per-capability; snapshots optionally unify per domain | **Recommended.** Fits layer discipline; incremental; small surface; directly serves Element (community route), Timezone (CLDR route), and the three expansions |
| **C — Full first-class Locale module with contract parameter** | `CapabilityContract.locales: frozenset[str]`; recognition scoped to selected locales; possibly a base `include_localized` field | Reject as v1 (with one caveat below). Scoping recognition to an *input locale* is unknowable from text alone (chicken-and-egg: you must recognize the language to know the locale); changes flag-off polarity (`INVALID`→`MISSING`) contract-wide; couples recognition to caller metadata that Paxman deliberately does not require; and a base-class field migrates 16 frozen contracts for no functional gain. *Caveat:* an **opt-in per-capability** `locales: frozenset[str]`-style narrowing (via the existing `active_grammars` override or matcher `requires_features`) remains available as a performance/completeness tool for a capability that wants it — supported, not standardized |
| **D — Single shared CLDR mega-snapshot only** | One `cldr_snapshot.json` + generators; no core code change | Partial-adopt (fold into B). Fixes pin skew and data flow; does nothing for vocabulary, policies, tests, or scaffold. B includes it |

---

## 7. Recommended Target Design (Option B, with D folded in)

> Illustrative shapes only — implementation would follow the TDD/scaffolding conventions; nothing below is currently in the tree.

### 7.1 The shared data shape — `LocaleAliasTable`

```python
"""Locale alias recognition tables — mechanism, not data (illustrative)."""
from dataclasses import dataclass
from paxman.core.domain import Provenance


@dataclass(frozen=True, slots=True)
class LocaleAliasTable:
    """Recognition-only, locale-tagged alias key set.

    Keys are syntax-normalized spellings in the locale named by ``locale``.
    A table NEVER maps a key to a canonical value — that is rule-layer
    authority data (recognition/validation boundary, F3). Provenance pins
    the publication the keys were extracted from (e.g. CLDR 48.2.1), so
    the alias surface is deterministic by snapshot.
    """

    locale: str                     # BCP 47 tag of the data's locale ("zh", "es", "fr")
    keys: frozenset[str]            # normalized recognition keys; no canonical mapping
    provenance: Provenance | None   # pinned publication, e.g. CLDR version

    def __post_init__(self) -> None:
        if not self.locale:
            raise ValueError("locale tag is required")
        if not self.keys:
            raise ValueError("alias table must not be empty")
```

```python
def lexicon_spec_from_tables(
    tables: tuple[LocaleAliasTable, ...],
    *,
    view: str,
    boundary: BoundarySpec,
    emit: EmitFn,
    representation: str = "auto",
    requires_features: frozenset[str] = frozenset[str](),
) -> MatcherSpec:
    """Build one kernel lexicon spec from per-locale alias tables.

    The union-lexicon model shipped today (Country `NameGrammar`) is the
    default: all locales' keys merge into one matcher, so recognition is
    locale-agnostic. Gating, when wanted, rides on ``requires_features``
    (matcher locus) — see §7.3.
    """
    tokens = frozenset(k.lower() for t in tables for k in t.keys)
    return MatcherSpec(
        kind="lexicon",
        payload=tokens,
        view=view,
        boundary=boundary,
        anchors=AnchorSet(),
        emit=emit,
        requires_features=requires_features,
    )
```

Per-capability `grammar/data/` modules then become declarations:

```python
# paxman/capabilities/Country/grammar/data/localized_names.py (target shape)
from paxman.core.locale import LocaleAliasTable

LOCALIZED_TABLES: tuple[LocaleAliasTable, ...] = (
    LocaleAliasTable(locale="zh", keys=CHINESE_KEYS, provenance=CLDR_PIN),
    LocaleAliasTable(locale="es", keys=SPANISH_KEYS, provenance=CLDR_PIN),
    LocaleAliasTable(locale="fr", keys=FRENCH_KEYS, provenance=CLDR_PIN),
)
```

### 7.2 Rule side — authority maps stay per-capability; policies get names

The authority mapping (`LOCALIZED_TO_ALPHA2`, `LOCALIZED_NAME_TO_CANONICAL`, `NAME_TO_CODES`…) remains rule-layer data owned by a `LOOKUP_TABLE` rule with the CLDR `Provenance`. What the seam adds is a **named policy vocabulary** (documented in the ADR and HOW_TO_ADD_NEW_CAPABILITY.md) so a contributor *declares* which regime they adopted:

| Policy (proposed name) | Shipped exemplar | Semantics |
|---|---|---|
| `single_authority_precedence` | Country ISO↔CLDR | when localized validation is on, keys owned by the locale authority are *exclusively* validated by it; the base-authority rule defers |
| `dual_authority_value_agreement` | Language ISO↔CLDR | two rules share `target_semantics`; correctness relies on colliding keys agreeing on the canonical value (engine dedup collapses them); must be paired with a data-consistency assertion that keys *do* agree |
| `candidate_tuple_opt_in` | Currency/Money symbol↔word | token → candidate tuple; single candidate definitive; multi resolved only by a contract opt-in guarded against the token's own tuple; else `INVALID` |
| `community_extension_deferral` | Element (planned) | no shipped authority; localized aliases ride `extra_grammars` / `register_rule` with their own provenance |

### 7.3 Gating polarity — a named choice, not an accident

| Flag state | Rule-locus gate (shipped default) | Matcher-locus gate (kernel-supported, currently unused) |
|---|---|---|
| `include_localized=True` | CLDR rule runs → `SUCCESS` with CLDR provenance | matcher runs → notation → rule → `SUCCESS` |
| `include_localized=False` | notation recognized, no rule validates → **`INVALID`** (HOW_TO_ADD_NEW_CAPABILITY.md §"Authority features use `requires_features`") | matcher omitted → **`MISSING`** (engine_loop omission, ADR-0009 §13) |

Convention to adopt: **rule-locus by default** (recognition surface stable regardless of flags — matches both shipped locale consumers and the false-negative-safety argument in Language's `_meta`); matcher-locus reserved for key sets whose unvalidated recognition is undesirable (huge, ambiguous, or authority-less). Dangling feature names already fail fast in both loci (`ContractError`).

Contract convention: keep **`include_localized: bool = False`** as the standard field *name* — already uniform in Country and Language — enforced by a homogeneity test (any capability whose grammar/data contains locale-tagged tables must either expose `include_localized` or document an always-active decision), rather than adding a base-class field to 16 frozen contracts.

### 7.4 One pinned snapshot — `paxman/shared_data/cldr_snapshot.json`

Generalize the `currency_snapshot.json` + M8 pattern to CLDR as a whole:

```json
{
  "_meta": {
    "authority": "Unicode CLDR",
    "cldr_version": "48.2.1",
    "citation": "https://cldr.unicode.org/downloads/cldr-48 ; github.com/unicode-org/cldr-json tag 48.2.1",
    "license": "Unicode License V3 (https://www.unicode.org/license.txt)",
    "completeness": "PER-DOMAIN SUBSET — see domains.*._completeness",
    "generated_by": "tools/_extract_cldr_snapshot.py"
  },
  "country":  { "_completeness": "zh/es/fr display names", "localized_names": { "zh": {"中国": "CN"}, "es": {"Alemania": "DE"} } },
  "language": { "_completeness": "en/fr/de/es endonym subset", "display_names": { "de": {"deutsch": "de"} } },
  "currency": { "_completeness": "en words + es/en symbols", "display_names": {}, "symbols": {} },
  "timezone": { "_completeness": "future — metazone/exemplar-city subset" }
}
```

- One `_meta.cldr_version` becomes **the** repo-wide CLDR pin → kills the v45/v46/v47 skew; bumping it is one snapshot change + per-capability regenerations + a provenance-version bump per capability (each capability's `Provenance` keeps citing the same version string).
- Per-domain extracts let each capability adopt at its own pace (full-CLDR Country is a *data* decision, not a code decision).
- Regenerators remain per-capability (`tools/regenerate_country_cldr_data.py`, …) or a shared `tools/regenerate_cldr_data.py` writing per-capability tables — never a cross-capability import (M8).
- Domainless-alias domains (Element) stay out of the snapshot until an authority exists; their community-extension route is unchanged.
- Also record the **non-authoritative domains** (SI unit names, CSS colors) in the ADR as "no locale authority — decision required per capability," so the SIUnit silence (§2.1) can't recur unnoticed.

### 7.5 Consistency-test convention, generalized

From the Country/Language exemplars, one shared statement (as a test helper or documented template — §8 OD-7):

1. every alias key in `grammar/data/` ∈ union of `rules/data/` authority keys (no recognition dead-ends);
2. per-locale ownership: each locale's keys are backed by the authority that owns that locale (CLDR owns localized, ISO owns English…);
3. completeness contract: subset tables must state out-of-subset → `MISSING` (not `INVALID`) in the generated header + snapshot `_meta`;
4. where two authorities share `target_semantics`, colliding keys must agree on canonical values (Language's implicit rule made explicit).

### 7.6 Provenance & determinism

- One `Provenance` per locale publication per capability rule file (`authority="Unicode"`, `specification_name="CLDR"`, `version="<snapshot pin>"`, `kind="registry"|"specification"` as today).
- `VersionStamp`/recognition-revision hashing already absorbs lexicon digests (`LexiconMatcher.digest`) and matcher specs — alias-table changes are automatically covered by the existing determinism machinery; nothing new is needed.
- Presentation stays with `format_value()` (ARCHITECTURE.md line 148 behavior unchanged: localized-name provenance retained through format conversion).

### 7.7 Proposed file layout (delta only — nothing moves today)

```text
paxman/core/
└── locale.py                        # NEW: LocaleAliasTable + lexicon_spec_from_tables + policy name constants
paxman/shared_data/
└── cldr_snapshot.json               # NEW: repo-wide CLDR pin (per-domain extracts)
tools/
└── regenerate_cldr_data.py          # NEW (or per-capability variants): snapshot → per-capability data modules
docs/adr/
└── 0010-locale-alias-recognition.md # NEW: the ADR formalizing §5.4/§7
paxman/capabilities/<Cap>/grammar/data/   # existing modules → LocaleAliasTable declarations (per capability, at its own pace)
paxman/capabilities/<Cap>/rules/data/     # unchanged — authority maps stay put
```

### 7.8 Migration path (per capability, no big-bang)

1. **ADR-0010** + HOW_TO_ADD_NEW_CAPABILITY.md section (the policy menu + gating polarity) — documentation first; zero code.
2. **CLDR snapshot** + regenerate Currency/Money/Language from the single pin (they are already snapshot-driven; lowest-risk first) → pins converge on one version.
3. **Country adoption**: convert `grammar/data/{chinese,localized}_names.py` to `LocaleAliasTable`s (regenerating from the same snapshot), keep hand-verified English/historical tables as-is; add the agree/ownership consistency assertions.
4. **Homogeneity test** for the `include_localized` convention + consistency-test helper shared by capability test suites.
5. **Scaffold prewire** (`tools/new_capability.py`) + `extra_grammars` recipe for authority-less domains (Element) and **Timezone** becomes the first greenfield consumer, validating the seam end-to-end.

### 7.9 Test strategy (delta)

- Unit: `LocaleAliasTable` frozen/slots, empty-key rejection, locale-tag validation; builder unions keys, forwards `requires_features`, view/boundary/emit.
- Per-capability: alias tables round-trip with generated files (snapshot `--check`); consistency assertions §7.5; flag polarity tests (`INVALID` rule-locus / `MISSING` matcher-locus) mirroring `tests/integration/test_feature_gating.py`.
- Property: union-lexicon recognition identical to per-table union of spans (order/dedup invariance); trie/alternation representation crossover at the 500-token gate with locale tables.
- Determinism: same snapshot + contract → byte-identical outputs (existing VersionStamp tests extended with a locale-data fixture).

---

## 8. Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | One CLDR pin forces simultaneous churn across capabilities on bump | per-domain extracts + per-capability regenerators; a capability may lag one pin (documented in its `Provenance.version`) while CI flags skew |
| 2 | Full-CLDR growth balloons package size (cf. pycountry's 7.7 MB, §3.5) | curated subsets remain the default; completeness contract (`MISSING` not `INVALID`) makes subsets safe; extras/optional locale packs if ever needed |
| 3 | `paxman.core.locale` name collides with stdlib `locale` mentally | package-qualified imports are safe; alternative names (`locale_aliases.py`, `alias_tables.py`) listed as open decision |
| 4 | Policy menu becomes cargo cult | ADR requires each capability to *declare* its policy + gating polarity in rule docstrings; consistency tests enforce the declared regime |
| 5 | Authority-less domains (Element) get silently absorbed into CLDR workflow | snapshot has no `element` domain; ADR states the community-extension route; `_meta` documents no-authority domains |
| 6 | Language's dual-rule agreement hides a future key collision | consistency assertion #4 (§7.5) turns the implicit invariant into a test |

---

## 9. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|---|---|---|
| 1 | ADR-0010 vs docs-only | **ADR** (mechanism is architectural; ADR-0009 §13 already anticipated matcher feature gating) | ADRs are the project's decision record; docs drift |
| 2 | Module name in core | `paxman/core/locale.py` (flag the stdlib-shadowing caveat) vs `locale_aliases.py` | decide at implementation; behavior identical |
| 3 | Base-class `include_localized` vs convention+test | **convention + homogeneity test** | no 16-contract migration; per-capability opt-in stays explicit; matches `CapabilityContract` "MAY override" style |
| 4 | Re-pin skew to which CLDR version | **48.2.x** at adoption time | current stable patch line; tz-2026c compatibility included |
| 5 | Country hand-curated tables → generated? | **yes, zh/es/fr via snapshot; keep English/historical hand-owned** (ISO-owned, not locale data) | eliminates the last hand-curated locale table; ownership stays correct per-authority |
| 6 | Always-active vs gated for *new* consumers (Timezone) | decide per capability via §7.3 table; document in plan | no global right answer; the menu is the deliverable |
| 7 | Shared consistency-test helper: shipped core function vs test-support module vs documented template | **test-support module under `tests/`** (not shipped API) | it is test infrastructure, not pipeline mechanism; keeps core minimal |
| 8 | Per-locale contract scoping (Option C caveat) | **defer**; keep union-lexicon default | no demonstrated need; `active_grammars`/matcher gates suffice if one appears |
| 9 | Locale packs as optional extras (size valve) | **defer**; revisit only if a full-CLDR consumer ships | current subsets are KB-scale |
| 10 | Element localized aliases: ship an authority-less curated set in-core? | **no — community extension** (affirms the Element research DEFER) | provenance-first doctrine: no authority, no shipped rule |

---

## 10. URL Reference (authoritative, fetched 2026-09-02)

| Claim | URL / path | Kind |
|---|---|---|
| CLDR 48 release note (48.1/48.2/48.2.1 dates; locale coverage 104/13/57; cldr-json tags) | https://cldr.unicode.org/downloads/cldr-48 | primary |
| CLDR downloads index (latest pointers) | https://cldr.unicode.org/index/downloads | primary |
| Unicode Locales Stability Policy ("Deprecated elements remain and can be used") | https://www.unicode.org/policies/locales_stability.html | primary |
| CLDR Data Retention Policy (5-year retention after IANA deprecation) | https://cldr.unicode.org/index/process/cldr-data-retention-policy | primary |
| CLDR currency names uniqueness guideline | https://cldr.unicode.org/translation/currency-names-and-symbols | primary |
| RFC 5646 §3.1.5/§3.4/§3.9 (Descriptions not localized; CLDR named as localized-data source; stability) | https://www.rfc-editor.org/info/rfc5646 | primary |
| Unicode License V3 (bundling permitted) | https://www.unicode.org/license.txt | primary |
| pycountry 26.2.16 (iso-codes + gettext catalogs; 7.7 MB; LGPL-2.1-only) | https://pypi.org/project/pycountry/ | primary |
| i18n-iso-countries (per-locale JSON packs; `registerLocale`; alias/official select) | https://github.com/michaelwittig/node-i18n-iso-countries | primary |
| npm `language-tags` (IANA Description synonyms e.g. `ro`: Romanian/Moldavian/Moldovan) | https://www.npmjs.com/package/language-tags | secondary |
| Country CLDR v45 rule + grammar/rule data | `paxman/capabilities/Country/rules/cldr_localized_ed2025.py`, `rules/data/cldr_ed2025.py`, `grammar/data/{localized,chinese}_names.py` | primary (code) |
| Country ISO↔CLDR precedence seam | `paxman/capabilities/Country/rules/iso_3166_ed2024.py:195-224` | primary (code) |
| Language CLDR v46 rule + snapshot | `paxman/capabilities/Language/rules/cldr_language_display_name_ed2025.py`; `paxman/shared_data/language_snapshot.json` | primary (code) |
| Currency/Money CLDR v47 rules + shared snapshot | `paxman/capabilities/{Currency,Money}/rules/cldr_currencies_ed2025.py`; `paxman/shared_data/currency_snapshot.json`; `shared_data/README.md` (M8) | primary (code) |
| Kernel normalizers/views/matchers/gating | `paxman/core/grammar/{normalizers,scan_context,matcher_spec,engine_loop}.py`, `matchers/lexicon.py`; `paxman/engine/orchestrator.py:494-510` | primary (code) |
| Conventions codifying the pattern | `HOW_TO_ADD_NEW_CAPABILITY.md` (lines 270, 313, 531); `ARCHITECTURE.md` (line 148); `docs/adr/0009-recognition-kernel.md` (lines 263, 883, 1185) | primary (docs) |
| Consistency-test exemplars | `tests/capabilities/{country,language}/test_data_consistency.py`; `tests/integration/test_feature_gating.py` | primary (code) |
| Element localized-name DEFER | `docs/development/research/2026-09-02-chemical-element-canonicalization.md` (line 66) | primary (docs) |
| Research precedents (report shape) | `docs/development/research/2026-08-22-iban-canonicalization.md`, `2026-08-23-bic-canonicalization.md`, `2026-08-23-language-canonicalization.md` | primary (docs) |

---

## 11. Evidence Completion — Resolved

- [x] Shipped-code inventory of every locale consumer (Country, Currency, Money, Language) with measured key/map counts and file-level citations (§2.1)
- [x] Negative + deferred cases documented (SIUnit unrecorded; Element DEFER with citation) (§2.1)
- [x] The recurring pattern extracted and checked against the project's own codified conventions (§2.2)
- [x] Drift ledger with ten concrete divergence rows (§2.3)
- [x] Kernel mechanism audit — what exists (views, matchers, both gating loci, provenance, snapshot workflow) vs what is missing (§2.4–2.5)
- [x] External authority survey: CLDR (version, coverage, distribution, uniqueness, stability, license), RFC 5646 localization out-of-scope quotes, ISO name-policy context (§3.1–3.3)
- [x] Authority-less domains enumerated (§3.4); ecosystem models surveyed with sizes (§3.5)
- [x] Future-capability forecast against MILESTONE (§4)
- [x] Feasibility verdict with the constraint ledger (import-linter, F3 boundary, determinism, data loci) (§5)
- [x] Four design options assessed; input-locale contract parameter explicitly rejected with reasons (§6)
- [x] Target design: data shape, builder, policy menu, gating polarity, snapshot workflow, consistency tests, layout, migration, tests (§7)
- [x] Risks and ten open decisions with recommendations (§8–9)

*Report saved to `docs/development/research/` per the research-report convention. Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs. No source code, tests, or configuration were modified for this study.*
