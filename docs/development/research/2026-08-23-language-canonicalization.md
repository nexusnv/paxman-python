# Language Canonicalization Research — paxman-python

**Date:** 2026-08-23
**Scope:** Primary-source survey of the Language standards (ISO 639-1:2002, ISO 639-2:1998, ISO 639-3:2007, ISO 639-5:2008, BCP 47 RFC 5646 / RFC 4647, IANA Language Subtag Registry), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `Language` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org) for ISO 639 family lineage (1988, 1998, 2002, 2007, 2008, 2023), Library of Congress ISO 639-2 RA pages, SIL International ISO 639-3 RA pages, IANA Language Subtag Registry (iana.org/assignments/language-subtag-registry, 2026-08-08 snapshot), RFC 5646 (BCP 47, September 2009) plus RFC 4647 matching, python pycountry `pycountry.languages`, langcodes `Language.get()`, iso639 Python package, validator.js `isISO6391`, arthurdejong/python-stdnum negative (no language), Wikipedia secondary, and shipped Paxman capabilities (Country 4 grammars, Currency 3 grammars, ISBN/ISSN/IBAN/BIC staged PipelineGrammar, ORCID) as architectural precedents. Repo state: `main` @ `95aa753` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](../research/2026-08-21-issn-canonicalization.md) plus the IBAN precedent [`docs/development/research/2026-08-22-iban-canonicalization.md`](../research/2026-08-22-iban-canonicalization.md) and BIC precedent [`docs/development/research/2026-08-23-bic-canonicalization.md`](../research/2026-08-23-bic-canonicalization.md) plus ORCID precedent [`docs/development/research/2026-08-23-orcid-canonicalization.md`](../research/2026-08-23-orcid-canonicalization.md).

---

## Executive Summary

Language is a strong fit for a Paxman capability: it has an unambiguous canonical form for codes (**lowercase alpha-2 when available, else lowercase alpha-3 Terminology**; BCP 47 tag canonicalized as `language[-script][-region][-variant]` with `language` lower, `script` Title, `region` Upper, `variant` lower, separators hyphen only, grandfathered tags replaced by preferred values), a stable multi-part standard family (**ISO 639-1:2002** alpha-2 184 codes, **ISO 639-2:1998** alpha-3 487 codes with Terminology/Bibliographic split, **ISO 639-3:2007** comprehensive alpha-3 7,000+ languages, **ISO 639-5:2008** families/groups, all `90.92` Confirmed/Published) with **Library of Congress** (639-2) and **SIL International** (639-3/5) as Registration Authorities, and **IANA Language Subtag Registry** as the operative authority (BCP 47) with rolling updates via Language Subtag Reviewer (weekly cadence, File-Date 2026-08-08), and a well-understood human-readable presentation (**BCP 47 tag** `en-US`, `zh-Hans-CN`, `sl-nedis`; bare codes `de`, `eng`; display names `German`→`de`). The domain mirrors Paxman's value proposition for Country and Currency: recognizing tolerant human surface (case, underscore vs hyphen, language names, bib vs term codes, grandfathered tags), validating strictly against authority (alpha-2/alpha-3 membership plus BCP 47 subtag validity), and returning a canonical compact value with full provenance. Language has **no checksum** (syntactic plus lexicon membership only, per IANA registry "stability" §3.4).

Key findings that shape the design:

1. **Canonical form is BCP 47 canonical tag (lower/title/upper) or bare lowest-available ISO 639 code.** Regex consensus for bare codes is `^[a-z]{2}$` (639-1) and `^[a-z]{3}$` (639-2/3), but BCP 47 tag consensus is the full RFC 5646 ABNF `language ["-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse]` with private-use fallback `^x(-[a-z0-9]{1,8})+$`. Primary language subtag preferred is 639-1 when exists, else 639-2/T else 639-3; grandfathered `i-cherokee`→`chr`, `en-GB-oed`→`en-GB-oxendict` etc. Display names `German`, `Deutsch`, `Allemagne` are lexicon-membership only and canonicalize to `de` via lookup. Separator `_` (`fr_FR`) is tolerant but canonical is `-` (`fr-FR`). This maps onto Paxman's presentational-only invariant: `format_value()` renders `bcp47` (default, case-canonicalized tag), `alpha2` (2-letter if exists else preferred alpha-3), `alpha3` (Terminology), `name` without touching validity.

2. **Three grammars suffice, mirroring Country's 4-grammar split.** Unlike ISBN which needs two grammars for ISBN-10 vs 13 semantics, Language needs **one Regex for BCP 47 tags**, **one Regex for bare alpha-2/alpha-3 codes**, and **one Lexicon for language display names** (`language_name_recognition`). Each declares distinct `semantics` (`bcp47_tag`, `language_code`, `language_name`) so rules route by semantics. A single grammar attempting to cover bare `en` + `en-US` + `German` via alternation would conflate token-to-value routing; the Country precedent (alpha2/alpha3/name) proves the clean split. Cross-grammar containment is beneficial, not harmful: `de` inside `de-AT` will be recognized by both but engine longer-wins per grammar keeps tag intact, and distinct semantics prevents spurious `AMBIGUOUS`.

3. **Validation is three-level lexicon lookup, no checksum.** Level 1: generic structure (ABNF well-formed, `2*3ALPHA` or `5*8ALPHA` primary, script `4ALPHA`, region `2ALPHA|3DIGIT`, variant `5*8alphanum|DIGIT3alphanum`, extension, privateuse, grandfathered table). Level 2: language subtag membership against IANA registry `Type: language` records (7990+ entries) plus ISO 639-1/2/3 snapshot equality (246 codes vs 7000+). Level 3: dependent subtag validity (script from ISO 15924, region from ISO 3166-1 plus UN M.49, variant prefix constraints, deprecated → Preferred-Value chain). No MOD-97, no Luhn, no country-length table. The registry `Deprecated` + `Preferred-Value` pair is the analogue of ISSN's X→`X` and ISBN's check: a single linear fallback (`iw`→`he`, `in`→`id`, `ji`→`yi`, `jw`→`jv`, `mo`→`ro`, `sh` collective vs individual).

4. **BCP 47 tag vs bare code are distinct values but same language identity.** `en` (bare) and `en-US` (tag with region) are **different canonical strings** (lexicographically distinct, like BIC8 vs BIC11), not coalesced via dedup. `eng` (alpha-3) and `en` (alpha-2) for English are **alternative canonical forms of the same language** but remain distinct values unless mapping rule collapses (`eng`→`en` via 639-1 existence); the mapping is rule-driven (LOOKUP_TABLE) not grammar-driven, so `eng` and `en` produce two candidates that may be resolved as `AMBIGUOUS` if both semantics validate, unless contract chooses `alpha2` as single default. Grandfathered `i-cherokee`→`chr` is canonicalized to preferred value via registry, not distinct identity.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 639-1:2002` (active, confirmed) owns alpha-2 codes; `ISO 639-2:1998` owns alpha-3 bibliographic/terminologic plus RA duties (Library of Congress); `ISO 639-3:2007` owns comprehensive language inventory (SIL); `ISO 639-5:2008` owns families/groups; `BCP 47 RFC 5646` (Sept 2009, BCP: 47, obsoletes 4646, category Best Current Practice, authors Phillips & Davis) plus **IANA Language Subtag Registry** (`kind="registry"`, rolling, File-Date) owns operative subtag validity (language/script/region/variant/grandfathered). No registry-gated liveness beyond IANA updates.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need Language canonicalization | Typical context |
|---------|------------------------------------------|-----------------|
| **i18n / frontend engineers** | Normalize `EN_us`, `fr_FR`, `ENG`, `German`, `deu` to one BCP 47 key for `Accept-Language`, HTML `lang`, locale file selection, and CLDR data lookup; deduplicate user preferences with span provenance | Web frameworks (Next.js, Django, Rails), mobile apps, CMS locale negotiation, translation management (Crowdin, Phrase, Lokalise) |
| **Data engineering / ML teams** | Validate language tags at dataset ingest; reject syntactically invalid vs registry-invalid tags with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | NLP corpora, LLM training data (Common Crawl language ID), HuggingFace datasets, ETL pipelines that carry `lang` fields |
| **Content / publishing platforms** | Canonicalize BCP 47 tags from free-text metadata, PDFs, emails, or scraped HTML with span-bearing provenance; join on canonical key for search facets and filtering | Publishing workflows (JATS `xml:lang`), digital libraries, SEO `hreflang`, knowledge-graph language matching |
| **Compliance / accessibility teams** | Use language tag as stable key alongside Country; detect duplicate language attributions across formatted variants, including script/region presentation and grandfathered tags | WCAG language of page/parts, screen-reader language switching, legal document language identification, corporate CMS audit |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many language mentions) and a contract; Paxman returns one canonical Language value (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors Country (`alpha2` default) and Currency (`alpha3` default) ergonomics, but the canonical default is **BCP 47 canonical tag** (`en`, `en-US`, `zh-Hans-CN`) with `alpha2`/`alpha3`/`name` as offered alternatives.

---

## 2. Shape of Input (Human Surface)

### 2.1 Wild variants — enumerated from spec, IANA registry, CLDR, and real validators

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical BCP 47 tag** | `en`, `fr-FR`, `zh-Hans-CN`, `sr-Latn-RS`, `en-CA-x-ca` | Spec master form, lower/title/upper cased, hyphen-separated; `format_value()` default target |
| 2 | **Bare alpha-2 code** | `en`, `de`, `fr`, `ja`, `EN`, `DE` | 2 letters, case-insensitive, canonical lower; must map to 639-1 registry |
| 3 | **Bare alpha-3 code (639-2/3)** | `eng`, `deu`, `fra`, `jpn`, `ENG`, `DEU`, `ger` (bib, deprecated) | 3 letters, case-insensitive, bib vs term (`ger` vs `deu`, `fre` vs `fra`), 7000+ codes in 639-3 |
| 4 | **Language display name (English)** | `German`, `English`, `French`, `Japanese`, `GERMAN`, `german` | Free-form name, case-insensitive, lexicon membership; `normalize_name` lower + strip; canonicalizes to `de`/`en` |
| 5 | **Language name (localized)** | `Deutsch`, `Français`, `Español`, `中文`, `Alemán` (if CLDR gating added) | Non-English names, requires localized lexicon, handled via `include_localized` flag (like Country) |
| 6 | **BCP 47 with underscore separator** | `fr_FR`, `en_US`, `zh_Hans_CN`, `EN_us`, `de_AT` | Users paste from POSIX locales `fr_FR.UTF-8`, programming locales; grammar must tolerate `_` and normalize to `-` plus case-fold |
| 7 | **Irregular case BCP 47** | `EN-US`, `FR-fr`, `ZH-hans-cn`, `en-us`, `SR-latn-rs` | Case-insensitive per RFC 5646 §2.1.1, but canonical is `en-US`, `zh-Hans-CN` (language lower, script title, region upper) |
| 8 | **BCP 47 with script** | `zh-Hans`, `zh-Hant`, `sr-Cyrl`, `sr-Latn`, `und-Latn` | Script 4 letters titlecase per ISO 15924, position after language, before region; `und` undetermined language |
| 9 | **BCP 47 with variant** | `sl-nedis`, `de-CH-1996`, `en-GB-oxendict`, `zh-cmn-Hans-CN` (extlang) | Variant 5-8 alphanum or digit+3alphanum, may repeat, prefix-constrained (e.g., `nedis` prefix `sl`) |
| 10 | **BCP 47 with extension/privateuse** | `en-a-myext-b-another`, `x-fr-CH`, `en-US-x-twain`, `de-DE-u-co-phonebk` (UTS35) | Singleton `a-w,y,z,0-9` introduces extension; `x` introduces privateuse; Paxman v1 must recognize but may validate as well-formed only |
| 11 | **Grandfathered tags** | `i-cherokee`, `i-klingon`, `en-GB-oed`, `art-lojban`, `zh-min-nan`, `no-bok`, `sgn-BE-FR` | Irregular vs regular per RFC 5646 Fig.1; irregular 17 fixed deprecated, regular 9 deprecated; must map via Preferred-Value when Deprecated |
| 12 | **Deprecated code with Preferred-Value** | `iw`→`he`, `in`→`id`, `ji`→`yi`, `jw`→`jv`, `mo`→`ro`, `sh`→`sr/hr/bs`, `bh`→`bih` | Old 639-1 codes deprecated 1989/2008, preferred alpha-2; pycountry and langcodes follow this; must normalize deprecated to preferred |
| 13 | **With trailing annotation** | `en (English)`, `fr-FR — French`, `German: de`, `lang: en-US` | Free-text often annotates language; extraction must emit one span per tag, not swallow parenthetical |
| 14 | **Multiple per line** | `en, fr, de`, `languages: en-US / fr-FR`, `de, fr, ja` | Translation lists, hreflang alternates — free-text may contain 2+ language mentions |
| 15 | **Quoted / bracketed** | `"en-US"`, `[fr-FR]`, `(de)`, `<html lang="en">`, `Content-Language: en` | Scraped HTML/headers and JSON fragments wrap tags in quotes/brackets or attribute syntax |
| 16 | **Collective code** | `aus` (Australian languages), `afa` (Afro-Asiatic), `bih` (Bihari) | ISO 639-2 scope `collection`, not an individual language; whether collective validates is a scope decision (§5.4) |
| 17 | **Over-long / malformed tag** | `en-US-123456789` (too long), `en--US`, `en_US_` (trailing), `123` (no language) | Must not be recognized; length guard max 8 per subtag, no empty subtags |
| 18 | **Invalid subtag for type** | `xx` (no language), `en-XX` (no region), `en-Qaaa` (private script in tag) | Grammar may still claim shape, rule rejects via registry lookup; `XX` private region vs `ZZ` |
| 19 | **Private-use primary** | `qaa`, `qtz`, `x-default`, `en-x-private` | `qaa`–`qtz` reserved private language, `x` primary private; valid per BCP 47 but maybe INVALID if Paxman scope is "assigned languages only" |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| RFC 5646 ABNF (§2.1 Fig.1) | `Language-Tag = langtag / privateuse / grandfathered ; langtag = language ["-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse] ; language = 2*3ALPHA ["-" extlang] / 4ALPHA / 5*8ALPHA ; extlang = 3ALPHA *2("-" 3ALPHA) ; script = 4ALPHA ; region = 2ALPHA / 3DIGIT ; variant = 5*8alphanum / (DIGIT 3alphanum)` |
| Generic consensus (CLDR, langcodes) | `^[a-z]{2,3}(?:-[a-z0-9]{2,8})*$` loose plus registry lookup; canonicalize via `Language.get(tag).to_tag()` |
| `pycountry` `pycountry.languages` | Lookup via `pycountry.languages.get(alpha_2='en')` or `alpha_3='eng'` or `name='English'` against ISO 639 database (639-2/3 fusion); no BCP47 parsing, code-only |
| `langcodes` `Language.get()` | `Language.get('en-US').to_tag()` → `en-US`; `Language.get('fr_FR').to_tag()` → `fr-FR`; handles `iw`→`he` deprecated, `_`→`-`, case folding, tag assembly; registry via `data/language-subtag-registry.txt` |
| `iso639` Python package | `Lang('en').pt1` / `pt2b` / `pt3`; `Lang('German').pt1 == 'de'`; validates via bundled ISO 639-3 table (~7900 rows), case-insensitive name lookup |
| `validator.js` `isISO6391` / `isBCP47` | `isISO6391: /^[a-z]{2}$/i + lookup set of 184 codes` ; `isBCP47` implements RFC 5646 ABNF then registry check (if available) |
| `CLDR` language display-name data | `en.json` `"de": "German"` etc; `de.json` localized names; used for localized lexicon if `include_localized` |
| `IANA registry` File-Date 2026-08-08 | `Type: language` records 7790+, `Type: region` 300+, `Type: script` ~200+, `Type: variant` 80+, `Type: grandfathered` 26 entries with `Deprecated` + `Preferred-Value` |

**Normalization contract (reuse Country/Currency pattern):**

```python
# langcodes / pycountry pattern — case-fold, underscore to hyphen, then lookup
import re

def _normalize_lang(raw: str) -> str:
    s = raw.strip().replace("_", "-")
    # BCP 47 canonical casing is applied after validation
    # language lower, script title, region upper, variant lower
    # so grammar folds via lower then formatter restores canonical
    return s.lower()

# Bare code path — strip separators, lower
bare = re.sub(r"[^A-Za-z]", "", raw).lower()
# then validate: len in {2,3, 5-8} and lookup in registry

# BCP 47 path — RFC 5646 §2.1.1: treat case-insensitively, but presentation is:
# language lower, script Title, region Upper, variant lower
# e.g. "EN-us" -> "en-US", "zh-HANS-cn" -> "zh-Hans-CN"
```

### 2.2 What input is NOT a Language mention

- Country codes alone (`US`, `DE`, `GB`) without language context — 2-letter country is `Country` alpha2, not `Language` alone; but `en-US` region `US` overlaps — disambiguation is by position (language first) and registry prefix (`US` as region after language+hyphen)
- Script codes alone (`Latn`, `Cyrl`, `Hans`) — too short without language prefix; `MISSING` vs `INVALID` boundary (see §9)
- Private numeric region codes (`419`, `001`) alone — `MISSING`, not Language
- Currency codes (`USD`, `EUR`) — 3-letter but not ISO 639 language, different registry
- Arbitrary 2-3 letter runs (`xyz`, `ab`) that are not in IANA language registry — `MISSING` vs `INVALID` depends on grammar: Lexicon name grammar claims only known names, Regex code grammar claims any 2-3 letters but rule rejects non-registry as `INVALID`
- Locale with encoding suffix (`en_US.UTF-8`, `fr_FR@euro`) — `en_US` part may be valid, suffix is `MISSING` (not swallowed)

### 2.3 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct language mentions that normalize to different canonical values is `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` with `single_value=True` enforcement); the caller-owned segmentation path (split then canonicalize each slice) is the intended multi-entity pattern for `Accept-Language: en, fr, de` or hreflang alternates. Identical mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — BCP 47 decomposition plus bare canonical

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LanguageNotation:
    """Language notation — grammar-normalized BCP 47 or bare code/name form.

    ``language`` is the primary language subtag, lowercased (2-8 letters).
    ``extlang`` is extended language subtags hyphen-joined or "" when absent.
    ``script`` is the 4-letter script subtag titlecased or "" when absent.
    ``region`` is the 2-letter alpha-2 or 3-digit region uppercased or "".
    ``variant`` is hyphen-joined variant subtags lowercased or "".
    ``extension`` is hyphen-joined extension sequences or "".
    ``privateuse`` is the private-use tail including leading "x-" or "".
    ``grandfathered`` is the raw grandfathered tag lowercased or "".
    ``compact`` is the BCP 47 canonical form (case-restored per §2.1.1) or
    bare code/name lowercased (separator hyphens, case folding).
    ``raw_value`` is the original trimmed token lowercased (for name lookup).

    The grammar never validates registry membership or deprecated→preferred;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    """

    language: str  # e.g. "en", "zh", "sr", "" when grandfathered/privateuse-only
    extlang: str  # e.g. "cmn", "" when absent (zh-cmn)
    script: str  # e.g. "Hans", "Latn", "" when absent
    region: str  # e.g. "US", "CN", "419", "" when absent
    variant: str  # e.g. "nedis", "1996", "" when absent
    extension: str  # e.g. "a-myext", "" when absent
    privateuse: str  # e.g. "x-private", "" when absent
    grandfathered: str  # e.g. "i-cherokee", "" when well-formed langtag
    compact: str  # e.g. "en-US", "zh-Hans-CN", "de", "en-GB-oxendict"
    raw_value: str  # e.g. "German", "EN_us" trimmed lower for lexicon
```

**Considered alternative — single field `compact` only:** `ORCIDNotation` style with `value` only plus BCP47 parsing in rules. Single `compact` would suffice for bare code rules (which operate on the whole tag via parsing), and script/region/variant handling can be derived via `compact.split("-")`. However the decomposition is preferred because:

1. The RFC 5646 ABNF indexes by position (language is `2*3ALPHA` at start, script is `4ALPHA` after, region `2ALPHA|3DIGIT`, variant `5*8alphanum`) — rules need field-level routing to validate each subtag's type via registry lookup, exactly like `BICNotation` `country_code` routing for ISO 3166-1 and `IBANNotation` `country_code` plus `bban`.
2. `variant` Prefix constraints (`sl-nedis` requires prefix `sl`) and `Suppress-Script` handling (`en` suppresses `Latn`) are field-aware; decomposition makes prefix checks first-class.
3. `grandfathered` vs `privateuse` vs `language` discrimination is structural, not stringly typed; a single string would force reparsing in every rule.

**Invariants the grammar enforces (before rules):**

- `language` is `2-8` letters lowercased when present (from `[A-Za-z]{2,8}`), empty only for grandfathered/privateuse irregular `i-*` / `x-*`
- `script` is `4` letters titlecased (`Latn`, `Hans`) or empty
- `region` is `2` letters uppercased or `3` digits or empty
- `variant` is `0..N` hyphen-joined lowercased variants, each `5-8` alphanum or `digit+3alphanum`
- `compact` canonicalizes case per §2.1.1 (language lower, script title, region upper, variant/extension/private lower) and `_`→`-`; separators between fields added when fields present
- `raw_value` preserves trimmed original lowercased (for Lexicon name lookup), not case-restored

### 3.2 Why not carry separator variants or EDI-style labels in the notation

Underscore `_` (`fr_FR`), slash/prefix labels (`Language: en-US`, `lang="en"`), and `locale=fr_FR.UTF-8@euro` encoding/charset suffixes have **no lexical significance** for validity — presentation is `Capability.format_value()` only. `en-US` and `en_US` have same identity regardless of input separator, dedup operates on `compact`. HTML `lang` attribute quoting and HTTP header `Content-Language:` prefix are extraction concerns, not notation fields; the grammar strips surrounding punctuation via `BoundaryGuard.word_only()`.

### 3.3 Why `language` is not a shape discriminator literal

Like `BICNotation.country_code` and `CountryNotation.shape`, `language` is free `str` validated by `LOOKUP_TABLE` against IANA registry snapshot plus ISO 639 snapshots, not `Literal`. Modeling 7,000+ languages as `Literal` would be brittle; validation is `LOOKUP_TABLE` against the registry, mirroring `Country`'s lexicon-key pattern where the registry, not the type system, owns the vocabulary. No `shape` field like Country's `alpha2/alpha3/name` is needed beyond `semantics` routing — the grammar's `semantics` already discriminates `language_code` vs `bcp47_tag` vs `language_name`; within BCP47, field presence discriminates.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Mixed Lexicon + Regex (structural + vocabulary)

Per HOW_TO_ADD_NEW_GRAMMAR.md and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, shipped grammars are **Regex** (distinctive shape) or **Lexicon** (finite vocabulary). Language has both: bare codes and BCP47 tags have distinctive shapes (fixed widths per position), while language names (`German`, `English`) are free-form vocabulary. So **Lexicon** for names, **Regex** for codes/tags — exactly like Country ships `alpha2/alpha3/numeric` (Regex) plus `name_recognition` (Lexicon). No single strategy covers both.

### 4.2 Reference pattern (adapted from Country and BIC verbatim precedent)

Country alpha2 precedent (`paxman/capabilities/Country/grammar/alpha2_recognition.py`):
```python
_GUARD = BoundaryGuard.word_only()
_ALPHA2_PATTERN = _GUARD.lookbehind + r"[A-Za-z]{2}" + _GUARD.lookahead
```

BIC single-grammar precedent (§4.2):
```python
_BIC_BODY = r"(?:(?:BIC|SWIFT)[\s:-]+)?(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)"
_BIC_PATTERN = BoundaryGuard.word_only().lookbehind + _BIC_BODY + BoundaryGuard.word_only().lookahead
```

Country name precedent (Lexicon):
```python
_KNOWN_NAME_KEYS = frozenset(ENGLISH_NAME_KEYS | LOCALIZED_NAME_KEYS | ...)
lexicon = WholeInputLookup[CountryNotation](keys=_KNOWN_NAME_KEYS, normalizer=normalize_name, ...)
```

**Proposed Language patterns (three grammars, staged pipeline):**

```python
import re
from paxman.capabilities.Language.notation import LanguageNotation, normalize_name
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

_GUARD = BoundaryGuard.word_only()

# Grammar 1 — BCP 47 tag (longest shape first; engine orders by start, then grammar index)
# ABNF-approximate: language [ "-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse]
# plus grandfathered and privateuse-only alternatives
# Per RFC 5646 §2.1, language is 2*3ALPHA (or 5*8ALPHA) optionally with extlang
# Script is 4ALPHA, region is 2ALPHA|3DIGIT, variant is 5*8alphanum|DIGIT3alphanum
_BCP47_BODY = (
    r"(?P<tag>"
    r"(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}"  # language + extlang
    r"(?:-[A-Za-z]{4})?"  # script
    r"(?:-(?:[A-Za-z]{2}|\d{3}))?"  # region
    r"(?:-(?:[A-Za-z0-9]{5,8}|\d[A-Za-z0-9]{3}))*"  # variant
    r"(?:-[A-Wa-wy-zY-Z0-9](?:-[A-Za-z0-9]{2,8})+)*"  # extension
    r"(?:-x(?:-[A-Za-z0-9]{1,8})+)?"  # privateuse
    r"|x(?:-[A-Za-z0-9]{1,8})+"  # privateuse-only
    r"|(?:en-GB-oed|i-(?:ami|bnn|default|enochian|hak|klingon|lux|mingo|navajo|pwn|tao|tay|tsu)"
    r"|sgn-(?:BE-FR|BE-NL|CH-DE)|art-lojban|cel-gaulish|no-(?:bok|nyn)"
    r"|zh-(?:guoyu|hakka|min|min-nan|xiang))"  # grandfathered
    r")"
)
_BCP47_PATTERN = _GUARD.lookbehind + _BCP47_BODY + _GUARD.lookahead
# Underscore tolerance: pre-stage replaces _ with - before regex, or allow [\s_-] in pattern
# Keep v1 hyphen-only with word_only guards; add underscore Pre if demanded

def _bcp47_notation(match: re.Match[str]) -> LanguageNotation:
    tag = match.group("tag")
    # Normalize _ to - and case-fold for parsing, then case-restore per §2.1.1
    # Actual decomposition uses split and position-length heuristics (script 4, region 2|3, variant 5-8)
    lower = tag.replace("_", "-")
    parts = lower.split("-")
    # ... heuristic split into language/extlang/script/region/variant/extension/privateuse/grandfathered
    # See RFC 5646 §2.2 type inference: length+position+content disambiguates script vs region vs variant
    # Return compact as case-canonicalized tag (language lower, script Title, region Upper)
    ...

class BCP47TagGrammar(PipelineGrammar[LanguageNotation]):
    name = "bcp47_tag_recognition"
    semantics = "bcp47_tag"
    single_value = True
    pre = StandardPre[LanguageNotation](empty_guard=True)
    regex = RegexStage[LanguageNotation](pattern=_BCP47_PATTERN, notation_fn=_bcp47_notation, flags=re.IGNORECASE)

# Grammar 2 — Bare language code (2 or 3 letters, or 5-8 for registered primary)
_CODE_PATTERN = _GUARD.lookbehind + r"(?P<code>[A-Za-z]{2,3}|[A-Za-z]{5,8})" + _GUARD.lookahead

def _code_notation(match: re.Match[str]) -> LanguageNotation:
    code = match.group("code")
    return LanguageNotation(
        language=code.lower(),
        extlang="", script="", region="", variant="",
        extension="", privateuse="", grandfathered="",
        compact=code.lower(), raw_value=code.lower(),
    )

class LanguageCodeGrammar(PipelineGrammar[LanguageNotation]):
    name = "language_code_recognition"
    semantics = "language_code"
    single_value = True
    pre = StandardPre[LanguageNotation](empty_guard=True)
    regex = RegexStage[LanguageNotation](pattern=_CODE_PATTERN, notation_fn=_code_notation, flags=re.IGNORECASE)

# Grammar 3 — Language name (Lexicon, whole-input lookup)
from paxman.capabilities.Language.grammar.data.english_names import ENGLISH_LANGUAGE_KEYS
from paxman.capabilities.Language.grammar.data.localized_names import LOCALIZED_LANGUAGE_KEYS  # optional

_KNOWN_LANGUAGE_KEYS = frozenset(ENGLISH_LANGUAGE_KEYS | LOCALIZED_LANGUAGE_KEYS)

class LanguageNameGrammar(PipelineGrammar[LanguageNotation]):
    name = "language_name_recognition"
    semantics = "language_name"
    single_value = True
    pre = StandardPre[LanguageNotation](empty_guard=True)
    lexicon = WholeInputLookup[LanguageNotation](
        keys=_KNOWN_LANGUAGE_KEYS,
        normalizer=normalize_name,
        notation_fn=lambda trimmed: LanguageNotation(
            language="", extlang="", script="", region="", variant="",
            extension="", privateuse="", grandfathered="",
            compact=trimmed.lower(), raw_value=trimmed,
        ),
    )
```

*Notes on fidelity vs Country/Currency/BIC:*

- Ship as module-scope **string** patterns; `RegexStage` compiles in `paxman/core/grammar/stages.py` (like `Country/alpha2_recognition.py`). Do not double-compile via `re.compile(...).pattern`.
- `BoundaryGuard.word_only()` (`(?<!\w)` and `(?!\w)`) blocks letter-glued runs (`Xen`, `enUS`, `Germanic` carving `German`); Country alpha2 uses word_only both sides for bare codes, BCP47 tag needs same to avoid `en-US` inside `xxen-USyy`.
- Underscore tolerance: POSIX locales `fr_FR` must be recognized but canonical is `fr-FR`; options are (a) `Pre` stage replacing `_`→`-` before regex (like IBAN paper-space), or (b) fused `[\s_-]` in pattern. Keep minimal for v1 contiguous hyphen-only; document underscore as post-grammar normalization if needed, parallel to BIC grouped display tolerance.
- Grammar ordering: `bcp47_tag` before `language_code` in `get_grammars()` so `en-US` (7 chars) wins over `en` (2) at same start via engine total ordering `(start, -(end-start))` per `_dedup_spans` longer-wins within same semantics affinity; distinct semantics preserves both but longer tag is the caller-expected recognition.
- Uses `PipelineGrammar` plus `StandardPre` plus `RegexStage`/`WholeInputLookup` because that is the staged pipeline Country actually ships (HOW_TO bare `Grammar` recipe is minimal teaching form; shipped grammars use `PipelineGrammar`).

**One vs three grammars:**

- **(Recommended) Three grammars** with distinct semantics (`bcp47_tag`, `language_code`, `language_name`) — mirrors Country's alpha2/alpha3/name split, enables rule routing: `language_code` validates bare 2-3 codes against ISO 639-1/2 snapshot, `bcp47_tag` validates full tag structure then subtag registry lookup, `language_name` validates display-name→code mapping. Single grammar with alternation would conflate `shape` routing.
- **Alternative:** Single grammar with `([A-Za-z]{2,3}(?:-[A-Za-z0-9]+)*|[A-Za-z ]+)` — unmaintainable, loses semantics routing, breaks `Rule.target_semantics` purity.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md Recognition Pipeline Contract)

- Grammar emits **span-bearing** `RecognitionMatch[LanguageNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))`, span is the regex slice. `WholeInputLookup` emits at most one match covering full trimmed input when normalizer key exists. Stages must not mutate `text` (`PipelineState` scratch only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups — `bcp47_tag` `en-US` and `language_code` `en` at same start are both preserved for affinity routing, but rule level will select the tag's provenance.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

### 4.4 Guard boundaries against sibling grammars

Language vs sibling grammars: Language bare `en` (2) overlaps with Country `US` (2) and Currency `USD` is 3 vs Language 3 but registry disjoint; BCP47 `en-US` region `US` overlaps Country alpha2 but position (after hyphen+language) disambiguates.

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| Language bcp47_tag | `2-3+...` with hyphens, `lang[-script][-region]...` | language `2*3ALPHA` at start | `(?!\w)` prevents claiming prefix of longer alphanum; hyphen is internal, not glue |
| Language code | `2-3` or `5-8` `[A-Za-z]{2,3}` | word boundary | `(?!\w)` prevents `en` inside `ens` or `eng`; only exact 2-3 vs 5-8 |
| Language name | `free text` lexicon keys (`German`, `very long language names with spaces`) | trimmed whole input | `WholeInputLookup` only when normalized key in `_KNOWN_LANGUAGE_KEYS`; not substring-scanned |
| Country alpha2 | `2` `[A-Za-z]{2}` | word boundary | Same shape as Language code 2 — disambiguation is by registry: `US` is Country `US` but Language `us` is not a valid language subtag (no `us` primary in IANA); `de` is Language `de` but also informal country confusion minimal |
| Country name | `free text` lexicon | whole input | Distinct lexicon key sets; `German` vs `Germany` disambiguate by language vs country name tables |

BCP47 `en-US` where `en` is valid language and `US` is valid region must not be confused with Country `US` standalone; the hyphen plus language-before-region position guarantees recognition as Language tag, not Country.

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

The new grammars declare non-empty `semantics` strings; every validating `Rule` declares `target_semantics: frozenset[str]` naming the semantics ids it validates. Engine `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. For Language:

- `semantics = "bcp47_tag"` (BCP 47 tag, longest shape)
- `semantics = "language_code"` (bare 2-3/5-8 code)
- `semantics = "language_name"` (Lexicon name)

Recommendation: start with three identity semantics; coalescing is unnecessary unless a community extension adds e.g. `posix_locale_recognition` that should reuse `bcp47_tag` validation.

### 4.6 `single_value` — one mention per call vs batch processing

Shipped capabilities (ISBN, Country, Money, Phone) all set `single_value=True`, consistent with Paxman "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). Language lists legitimately contain 2+ mentions (`en, fr, de` or `Accept-Language: en-US, en;q=0.9, fr;q=0.8`) so batch extraction will want multiple.

Recommendation: **initial `single_value=True`** (matches shipped precedent and the single-tag field use-case), with a documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A separate free-text community grammar with `single_value=False` can be offered via `extra_grammars` for batch callers (like `Accept-Language` header mining) when needed.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec and lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO** — International Organization for Standardization, Technical Committee **ISO/TC 37** (Language and terminology) for ISO 639 family, plus **IETF** for BCP 47 (RFC 5646). ISO 639-1 RA is **Infoterm** (Vienna), ISO 639-2 RA is **Library of Congress** (Washington), ISO 639-3/5 RA is **SIL International** (Dallas). IANA Language Subtag Registry is maintained by **IANA** with Language Subtag Reviewer ( ietf-languages@iana.org ). |
| **Registration Authority (RA)** | **Library of Congress** (ISO 639-2, since 1998, `https://www.loc.gov/standards/iso639-2/`), **SIL International** (ISO 639-3 since 2007, `https://iso639-3.sil.org/code_tables/639/data`), **IANA** (BCP 47 subtag registry, `https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry`). ISO 639-1 originally Infoterm, now ISO 639 MA via Library of Congress. |
| **Spec name** | `ISO 639 — Codes for the representation of names of languages` (Parts 1,2,3,5) plus `BCP 47 — Tags for Identifying Languages` (RFC 5646, September 2009, BCP: 47) plus `IANA Language Subtag Registry` |
| **Current editions** | **ISO 639-1:2002** (2nd ed., 2002-07-17, `Codes -- Part 1: Alpha-2 code`, ICS 01.140.20, TC 37, Confirmed 2023) — 184 alpha-2 codes; **ISO 639-2:1998** (1st ed., 1998, `Alpha-3 code` plus Amendments, ICS 01.140.20, TC 37/SC 2) — 487 codes (21 with T/B pairs like `deu/ger`, `fra/fre`); **ISO 639-3:2007** (1st ed., 2007-02-05, `Alpha-3 code for comprehensive coverage`, ICS 01.140.20, TC 37/SC 2) — 7,000+ codes; **ISO 639-5:2008** (1st ed., 2008-05-15, `Alpha-3 code for language families and groups`, 115 codes); **RFC 5646** (Sept 2009, BCP: 47, obsoletes RFC 4646, category Best Current Practice, authors A. Phillips & M. Davis); **IANA Registry** File-Date 2026-08-08 rolling monthly/weekly. |
| **Check character system** | None — Language has no checksum (like BIC). Validation is syntactic (ABNF) plus lexicon membership. IANA registry §3.4 "Stability of IANA Registry Entries" describes no check digit. |
| **Language code reference** | `ISO 639-1 alpha-2`, `ISO 639-2 alpha-3` (T/B), `ISO 639-3` comprehensive; `ISO 15924` (script), `ISO 3166-1` (region alpha-2), `UN M.49` (region numeric) normatively referenced by BCP 47 §2.2.3/§2.2.4. |
| **Related specs** | `RFC 5646` (BCP 47) obsoletes `RFC 4646` (BCP 47, Sept 2006) which obsoleted `RFC 3066` (BCP 47, Jan 2001) which replaced `RFC 1766` (Mar 1995); `RFC 4647` (Matching of Language Tags, Sept 2006) — lookup/filtering; `RFC 5234` (ABNF); `RFC 2119` (key words); `RFC 2781` (UTF-16); `ISO 15924` script; `ISO 3166-1` region; `UN M.49` numeric region; `Unicode CLDR` locale data for display names. |

**Language structure (RFC 5646 §2.1 + ISO 639 §):**

```
Language-Tag = langtag / privateuse / grandfathered
langtag = language ["-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse]
language = 2*3ALPHA ["-" extlang] / 4ALPHA / 5*8ALPHA
extlang = 3ALPHA *2("-" 3ALPHA)  ; reserved, includes zh-cmn etc
script = 4ALPHA          ; ISO 15924 (Latn, Hans, Cyrl)
region = 2ALPHA / 3DIGIT ; ISO 3166-1 alpha-2 or UN M.49 numeric (419 for Latin America)
variant = 5*8alphanum / (DIGIT 3alphanum) ; e.g. nedis, 1996, oxendict
extension = singleton 1*("-" (2*8alphanum)) ; singleton 0-9, A-W, Y-Z, a-w, y-z
privateuse = "x" 1*("-" (1*8alphanum))
grandfathered = irregular / regular ; fixed 26 tags, all deprecated in favor of modern

ISO 639-1: alpha-2 2 letters lower, e.g. en, de, fr (184)
ISO 639-2: alpha-3 3 letters lower, 487, T vs B: Terminology vs Bibliographic
  e.g. German: T=deu (639-2/T, 639-3), B=ger (639-2/B only); French: fra/fre; Chinese: zho/chi
ISO 639-3: alpha-3 comprehensive, 7000+, superset of 639-2 (all 639-2 codes appear)
  Adds: extlang subtags zh-cmn etc via 639-3 macrolanguage envelope
IANA registry: Type: language records 7790+, Type: script ~200+, Type: region 300+, Type: variant 80+, Type: grandfathered 26

Concrete IANA record (language):
%%
Type: language
Subtag: de
Description: German
Added: 2005-10-16
Suppress-Script: Latn
%%

Formal charset: Bare code `^[A-Za-z]{2,3}$` plus registered `5*8ALPHA`; BCP 47 tag ABNF per Fig.1; canonical per §2.1.1 lower/title/upper (language lower, script Title, region Upper, variant lower, grandfathered lower→preferred lower)
Region at position after script, variant after region; deprecated fields carry Preferred-Value (iw→he etc.)
Examples from evidence: `en`, `en-US`, `fr-FR`, `zh-Hans-CN`, `sr-Latn-RS`, `sl-nedis`, `de-CH-1996`, `en-GB-oxendict`, `zh-cmn`, `i-klingon`→deprecated but valid, `x-fr-CH` privateuse
```

Quoted IANA registry stability (RFC 5646 §3.4):
> "The IANA Language Subtag Registry is expected to be stable; subtags MUST NOT be removed... Deprecated subtags remain valid but carry Preferred-Value for canonicalization."

- Formal ABNF: language is `2*3ALPHA` (shortest ISO 639 code) or `4ALPHA` reserved or `5*8ALPHA` registered; script `4ALPHA`; region `2ALPHA|3DIGIT`
- Preferred-Value resolution: `iw` (Deprecated 1989)→`he`, `in`→`id`, `ji`→`yi`, `jw`→`jv`, `mo`→`ro`, `bh` (Bihari 2026-06-14 Deprecated)→`bih`, `sh` macrolanguage remains but individual `sr/hr/bs` preferred for modern uses
- Suppress-Script (`en`→`Latn` etc) indicates script adds no distinguishing value but is not a reject signal
- Examples from evidence: `de` (German, suppress Latn), `zh` (Chinese macrolanguage, `Scope: macrolanguage`), `sr` (Serbian, macrolanguage `sh`), `zh-Hans-CN` (Chinese Han Simplified China), `yue` (Cantonese, extended `zh-yue` but preferred `yue`)

**Lineage table (ISO 639 + BCP 47 editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 639:1988 | 1988 | withdrawn | First unified ISO 639 (alpha-2 + alpha-3), 136 languages; RA Infoterm |
| ISO 639-2:1998 | 1998 | current, confirmed | First split into Part 2 alpha-3, 487 codes, T/B pairs, RA Library of Congress; ICS 01.140.20 |
| RFC 1766 | 1995-03 | obsoleted by 3066 | First BCP 47 predecessor, simple lang+country |
| RFC 3066 | 2001-01 | obsoleted by 4646 | Introduced script subtag, IANA registry concept |
| ISO 639-1:2002 | 2002-07-17 | current, confirmed 2023 | Alpha-2 184 codes, 2nd ed., RA Infoterm/LoC; stability note frozen against later 639-2 additions per RFC 5646 §2.2.1 |
| RFC 4646 | 2006-09 | obsoleted by 5646 | First formal registry format, introduced extlang, File-Date tracking |
| ISO 639-3:2007 | 2007-02-05 | current | Comprehensive alpha-3 7,000+ languages, RA SIL International; all 639-2 codes retained |
| ISO 639-5:2008 | 2008-05-15 | current | Families/groups 115 codes (e.g., `afa` Afro-Asiatic, `aus` Australian) |
| RFC 5646 | 2009-09 | current, BCP:47 | Current BCP 47, obsoletes 4646, adds stability guarantees §3.4, 26 grandfathered, extensions registry |
| ISO 639:2023 | 2023 (proposed) | draft | Unified revision consolidating 639-1/2/3/5 into single ISO 639:2023 (work in progress, not yet Published) |

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 37) | `ISO 639-1:2002` | `2002-07` (2nd ed., confirmed 2023, 184 codes) | `https://www.iso.org/standard/22109.html` | `active` — confirmed | `2002` | `specification` |
| ISO (ISO/TC 37/SC 2) | `ISO 639-2:1998` | `1998` (1st ed., 487 codes, T/B, Amendments) | `https://www.iso.org/standard/4767.html` | `active` — confirmed | `1998` | `specification` |
| ISO (ISO/TC 37/SC 2) | `ISO 639-3:2007` | `2007-02` (1st ed., 7,000+ codes, SIL RA) | `https://www.iso.org/standard/39534.html` | `active` | `2007` | `specification` |
| ISO (ISO/TC 37) | `ISO 639-5:2008` | `2008-05` (1st ed., 115 families) | `https://www.iso.org/standard/39536.html` | `active` | `2008` | `specification` |
| IETF (Phillips & Davis, Lab126/Google) | `BCP 47 RFC 5646` | `2009-09` (BCP:47, obsoletes 4646, category Best Current Practice) | `https://www.rfc-editor.org/rfc/rfc5646.txt` | `active` — BCP | `2009` | `specification` |
| IANA (Language Subtag Reviewer) | `IANA Language Subtag Registry` | `Rolling` (File-Date 2026-08-08) | `https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry` | `active` — rolling weekly | `2026` | `registry` |
| Library of Congress | `ISO 639-2 RA` | `Rolling` (code tables) | `https://www.loc.gov/standards/iso639-2/php/code_list.php` | `active` | `2026` | `registry` |
| SIL International | `ISO 639-3 RA` | `Rolling` (code_tables 639/data) | `https://iso639-3.sil.org/code_tables/639/data` | `active` | `2026` | `registry` |
| IETF (IAB) / Unicode | `RFC 4647 Matching of Language Tags` | `2006-09` (companion to 5646 for Lookup/Filter) | `https://www.rfc-editor.org/rfc/rfc4647.txt` | `active` | `2006` | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical Language rule citing a withdrawn edition (e.g., RFC 3066 or ISO 639:1988) would carry `lifecycle="withdrawn"` or `"superseded"`. For Language, initial rules are expected `active`. The IANA registry is `kind="registry"` `lifecycle="active"` (rolling). Historical T/B disambiguation (`ger` vs `deu`) where `ger` is deprecated in favor of `deu` in IANA still carries `lifecycle active` but record `Deprecated` plus `Preferred-Value`.

### 5.2 Rule and publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_639_1_ed2002.py` | `authority="ISO"`, `specification_name="ISO 639-1:2002"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/22109.html"`, `version="2002"`, `lifecycle="active"`, `publication_year=2002` | `Section 4-alpha-2-code` (2-letter codes, 184 entries) | Bare alpha-2 validation: length `2`, `^[a-z]{2}$`, membership in ISO 639-1 alpha-2 plus IANA `Type: language 2-letter` set; `normalize()` returns lower |
| `rules/iso_639_2_ed1998.py` | `authority="ISO"`, `specification_name="ISO 639-2:1998"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/4767.html"`, `version="1998"`, `lifecycle="active"`, `publication_year=1998` | `Section 4-alpha-3-terminology` (487 codes, T) + `Section 4-alpha-3-bibliographic` (B) | Bare alpha-3 validation: T vs B distinction; B codes like `ger` deprecated but still `INVALID` unless preferred-value resolution applied; `normalize()` returns `deu` for both |
| `rules/iso_639_3_ed2007.py` | `authority="SIL International (ISO 639-3 RA)"`, `specification_name="ISO 639-3:2007"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/39534.html"`, `version="2007"`, `lifecycle="active"`, `publication_year=2007` | `Section 4-comprehensive-alpha-3` (7000+ codes, including extlang) | Bare alpha-3 comprehensive: all 639-3 codes plus `qaa-qtz` private reserved handling; `POSIT` collective? `normalize()` lower |
| `rules/bcp47_rfc5646_ed2009.py` | `authority="IETF"`, `specification_name="BCP 47 RFC 5646"`, `kind="specification"`, `reference_url="https://www.rfc-editor.org/rfc/rfc5646.txt"`, `version="2009-09"`, `lifecycle="active"`, `publication_year=2009` | `Section 2.1-syntax` (ABNF well-formed plus grandfathered table), `Section 2.2.1-primary-language` (language validity vs private), `Section 4.5-canonicalization` (case restoration), `Section 3.4-stability` (deprecated→preferred) | BCP 47 tag structure: well-formed per ABNF, grandfathered validity (26 fixed tags), privateuse validity, extension singleton handling, case canonicalization via `normalize()` (language lower, script Title, region Upper) |
| `rules/iana_language_subtag_registry_ed2026.py` | `authority="IANA"`, `specification_name="IANA Language Subtag Registry"`, `kind="registry"`, `reference_url="https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry"`, `version="Rolling File-Date 2026-08-08"` | `Section *-language-subtag-membership` (Type: language 7790+), `Section *-script-subtag-membership` (Type: script via ISO 15924), `Section *-region-subtag-membership` (Type: region via ISO 3166-1 + UN M.49), `Section *-variant-subtag-membership` (prefix-constrained) | Registry membership: every subtag's existence plus scope/deprecated/preferred handling plus suppress-script; `requires_features` not needed for base validation (always active) but gated for `include_private` or `include_grandfathered` variants |
| `rules/cldr_language_display_name_ed2025.py` *(optional — gated, localized names)* | `authority="Unicode CLDR"`, `specification_name="CLDR Language Display Names"`, `kind="registry"`, `reference_url="https://www.unicode.org/cldr/charts/46/summary/root.html"` | `Section *-language-display-name` (localized name→code) | Localized display names (e.g., `Deutsch`→`de`, `Allemagne` irrelevant) gated via `requires_features={"include_localized"}` |

*This mirrors Country four-rule split (ISO 3166 plus CLDR localized) and ISBN three-authority split (ISO 2108 // Users Manual // Range Message). For Language, ISO 639-1 + IANA registry are mandatory; CLDR localized is optional, gated via `requires_features`, exactly like Country `include_localized`.*

Each `Rule[LanguageNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`):

```python
class Section4Alpha2Codes(Rule[LanguageNotation]):
    name = "Section 4-alpha-2-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (alpha-2 code, 184 entries)"
    target_semantics = frozenset({"language_code"})
    requires_features = frozenset()

    def matches(self, notation: LanguageNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: LanguageNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO 639 lineage** confirmed via `https://www.iso.org/standard/6506.html` (639:1988), `https://www.iso.org/standard/4767.html` (639-2:1998), `https://www.iso.org/standard/22109.html` (639-1:2002), `https://www.iso.org/standard/39534.html` (639-3:2007), `https://www.iso.org/standard/39536.html` (639-5:2008) plus LOC `https://www.loc.gov/standards/iso639-2/php/code_list.php` listing 487 codes with T/B columns.
- **BCP 47 as RA-page:** `https://www.rfc-editor.org/rfc/rfc5646.txt` (BCP: 47, Sept 2009, 77 pages, obsoletes 4646, category Best Current Practice, authors Phillips & Davis) plus IANA registry `https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry` (File-Date header 2026-08-08, 26 grandfathered, Suppress-Script fields, Deprecated+Preferred-Value pairs, `Type: language` 7790+).
- **Structure quote** from RFC 5646 Fig.1 ABNF (see §5.1 box) plus IANA record example `Type: language Subtag: de Description: German Added: 2005-10-16 Suppress-Script: Latn` (verbatim fetch §5.1).
- **Country nuance analogue:** Language region set equals ISO 3166-1 alpha-2 plus UN M.49 numeric plus private `AA QM-QZ XA-XZ ZZ` (per RFC 5646 §2.2.4), script set is ISO 15924 4ALPHA (via IANA `Type: script`), both normative references in BCP 47 §2.2.3/2.2.4.
- **No checksum:** RFC 5646 §3.4 stability plus IANA registry stability clause proves negative — no check digit, syntactic plus registry only.

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. ISO 639-1 rule checks: bare 2-letter code existence in 184 set (plus IANA 2-letter language records). ISO 639-2 rule checks: bare 3-letter code in 487 set, distinguishing T vs B where both exist (validates `deu` T, treats `ger` B as Deprecated with Preferred-Value `deu`). ISO 639-3 rule checks: 7000+ comprehensive set including macrolanguage `zh`, extlang `cmn` etc. BCP 47 rule checks: tag is well-formed per ABNF (`language ["-" script] ["-" region] *("-" variant) ...`) plus each subtag's type inference via length/position/content per §2.2, plus grandfathered enumerated list (irregular 17 + regular 9). IANA registry rule checks: each subtag exists in registry with correct Type (`language` vs `script` vs `region` vs `variant`) plus Prefix constraints for variant (`sl-nedis` requires prefix `sl` per registry `Prefix: sl`), plus Suppress-Script informative handling, plus Deprecated→Preferred-Value chain. CLDR localized rule checks: display name→code mapping only when `include_localized`. All return `False` for any invalid input, never raise, not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO Step 7).
- **`normalize()`** — returns the **default BCP 47 canonical form** (per RFC 5646 §2.1.1 case conventions: language lower, script Title, region Upper, variant/extension/private lower, grandfathered lower→preferred). For bare codes, `normalize()` returns lower (or preferred lower if deprecated: `iw`→`he`). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability `format_value()` seam only. Both the generic and the language-specific rules must return the **same** default string for the same valid notation for dedup.
- **`RuleStrategy` choice:** Country precedent uses `LOOKUP_TABLE` for membership (alpha2 name), ISBN uses `PARSER` for check digit. For Language, bare code rules are `LOOKUP_TABLE` (membership in ISO snapshots), BCP47 well-formed rule is `PARSER` (ABNF parse), registry membership rule is `LOOKUP_TABLE`.

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Whether Language validation is bare-code-only vs full BCP 47 tag, with scope cost/benefit.

**Recommendation for an initial Language capability:** ship **bare code validation as always-active LOOKUP_TABLE** against ISO 639-1 plus IANA language subtag set (2-letter and 3-letter plus 5-8 registered), plus **BCP 47 well-formed PARSER as always-active** against RFC 5646 ABNF (well-formed check is cheap and stablest guarantee). Add **IANA registry LIVENESS (subtag existence per Type) as always-active LOOKUP_TABLE** against rolling registry snapshot (weekly updates, 7790+ languages, cheap set membership, no per-subtag length variant like IBAN). Collective codes (`aus`, `afa`) are `Scope: collection` per ISO 639-2 — whether collection validates as language is an open decision: recommendation is **reject Scope: collection as individual language** (return `INVALID`), valid only when `include_collective=False` (default) vs optional opt-in, because collections are not languages (they are groupings). Private-use `qaa-qtz` and `x-*` are valid per BCP 47 but may be gated behind `include_private=True` (default False).

Analogy: Country `LOOKUP_TABLE` for alpha2; BIC country field same class; Language language subtag is same membership property, not a check-digit transform.

### 5.5 Assignment / registration authority & Registry content

Network: **IANA** as RA with **Language Subtag Reviewer** (currently Michael Everson per RFC 5646 §3.2) plus **assigning authorities** per subtag type: ISO 639/RA-JAC (language), ISO 15924 RA (script via Unicode Consortium), ISO 3166 MA (region alpha-2), UN Statistics Division (region numeric M.49), and ad-hoc variant registration via ietf-languages@iana.org. Record includes per `%%
Type: language
Subtag: de
Description: German
Added: 2005-10-16
Suppress-Script: Latn
Scope: macrolanguage
Macrolanguage: zh (for yue etc)
Deprecated: ... / Preferred-Value: ... when deprecated
Prefix: ... for variants
Comments: ...`

Each record includes: `Type`, `Subtag`/`Tag` (for grandfathered), `Description` (one or more), `Added`, plus optional `Deprecated`, `Preferred-Value`, `Suppress-Script`, `Scope`, `Macrolanguage`, `Prefix`, `Comments`. Registry notes:

- *"Grandfathered tags"* (irregular + regular) are fixed 26 that do not match `langtag` production but are valid tags (all Deprecated, Preferred-Value points to modern); e.g. `i-cherokee`→`chr`, `en-GB-oed`→`en-GB-oxendict`, `zh-min-nan`→`nan`, `art-lojban`→`jbo`.
- *Suppress-Script* indicates when script adds no distinguishing value (e.g., `en` Suppress `Latn`) but is not a reject signal.
- Rolling activation, File-Date header updated on each IANA publication; no monthly activation weekend like BIC, continuous rolling per RFC 5646 §3.3/§3.8.

Per **RFC 5646 §3.5 Registration Procedure**:
- RA (IANA) receives registration requests via ietf-languages@iana.org, validates against underlying ISO standards where applicable, two-week review period, and publishes in registry.
- Publication schedule per §3.3 Maintenance: registry is a text file `language-subtag-registry` with `File-Date: YYYY-MM-DD` header, updated within days of approval.

Mandatory registration data: Subtag, Type, Description, Added date, plus optional Deprecated, Preferred-Value, Prefix, Suppress-Script, Scope, Macrolanguage.

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman.core.capability_contract.py`), never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class LanguageContract(CapabilityContract):
    """User-facing contract for Language capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "bcp47"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"alpha2", "alpha3", "alpha3-bib", "name"}
    )

    capability_name: str = field(default="language", init=False)
    # Grammar-toggle flags for Lexicon vs Regex needs
    include_localized: bool = False  # CLDR localized names (Deutsch, Français)
    include_collective: bool = False  # Scope: collection codes like aus, afa
    include_private: bool = False  # qaa-qtz and x- privateuse
    include_grandfathered: bool = True  # grandfathered tags are valid but deprecated

    # active_grammars is optional — Language has no input-shape gating initially
    # so omit; base returns None and engine runs every shipped grammar.
    # If you want to disable name recognition by default, add active_grammars.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For Language, `bcp47` (canonical tag, case-restored per §2.1.1) is the machine canonical form (BCP 47 registry tag); `alpha2` is 2-letter when available else preferred alpha-3, `alpha3` is Terminology (deu), `alpha3-bib` is Bibliographic (ger), `name` is English display name.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format`, `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order, then capability-specific params (if any). For Language, `include_localized`, `include_collective`, `include_private`, `include_grandfathered` follow.

**Presentational-only invariant (hard rule — ARCHITECTURE.md The Formatting Seam):**

- `output_format` is a **representation transform, never a recognition or validation signal**. Rules never read it; `normalize()` always returns the default `bcp47` canonical tag (lower/title/upper); the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup and status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance**, `Candidate.provenance`, `recognition_rule`, `validation_rule` come from the validating rule.

For Language, the offered formats model the three interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"bcp47"` (default) | `en`, `en-US`, `zh-Hans-CN`, `sl-nedis` | BCP 47 canonical tag, case per §2.1.1 (language lower, script Title, region Upper, variant lower), hyphen only |
| `"alpha2"` | `en`, `de`, `fr`, `zh` (for `zh-Hans-CN` -> `zh`) | Bare alpha-2 when exists else preferred alpha-3 lower; primary language subtag extraction |
| `"alpha3"` | `eng`, `deu`, `fra`, `zho` | Terminology alpha-3 (T) lower; for languages with both, T is preferred (deu over ger) |
| `"alpha3-bib"` | `eng`, `ger`, `fre`, `chi` | Bibliographic alpha-3 (B) lower; only for languages where T/B differ |
| `"name"` | `English`, `German`, `French` | English display name per ISO 639 Description field (first Description), titlecased |

*Do not add `with_script` or `with_region` formats, script/region are part of the bcp47 tag's value; `bcp47` already renders them case-canonically. Do not add `und` formatting.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.Language.notation import LanguageNotation


class LanguageCapability(Capability[LanguageNotation]):
    name = "language"

    def get_grammars(self) -> list[Grammar[LanguageNotation]]:
        return [
            BCP47TagGrammar(),
            LanguageCodeGrammar(),
            LanguageNameGrammar(),
        ]  # 3 grammars; BCP 47 longest first, then bare code, then name lexicon

    def get_rules(self) -> list[Rule[LanguageNotation]]:
        return [
            Section4Alpha2Code(),
            Section4Alpha3Terminology(),
            Section4Alpha3Bibliographic(),
            Section4ComprehensiveAlpha3(),
            Section21Syntax(),  # BCP 47 well-formed
            SectionLanguageSubtagMembership(),
            SectionScriptSubtagMembership(),
            SectionRegionSubtagMembership(),
            SectionVariantSubtagMembership(),
            # plus optional CLDR localized rule
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: "Sequence[str] | None" = None,
        pinned_rules: "Sequence[str] | None" = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: "Sequence[str] | None" = None,
        include_localized: bool = False,
        include_collective: bool = False,
        include_private: bool = False,
        include_grandfathered: bool = True,
    ) -> LanguageContract:
        return LanguageContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
            include_localized=include_localized,
            include_collective=include_collective,
            include_private=include_private,
            include_grandfathered=include_grandfathered,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: LanguageNotation
    ) -> str:
        if output_format == "alpha2":
            # language lower; if alpha-2 exists via mapping, return it else preferred alpha-3
            # Uses rules/data iso_639_1 snapshot for mapping
            return _to_alpha2(value, notation)
        if output_format == "alpha3":
            return _to_alpha3_term(value, notation)
        if output_format == "alpha3-bib":
            return _to_alpha3_bib(value, notation)
        if output_format == "name":
            return _to_display_name(value, notation)
        return value  # bcp47 default is identity — normalize() must return canonical bcp47 tag
```

Registration (HOW_TO §9 / `tools/new_capability.py`):
`scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(Language())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation — Syntactic, Registry, Collective

### 7.1 Three-level validation (well-formed → membership → preferred)

**Level 1 Generic structure (PARSER):** Check tag is well-formed per RFC 5646 ABNF without registry (syntactic shape only). Length per subtag `1-8` (privateuse) / `2-8` language / `4` script / `2|3` region / `5-8|1+3` variant, separators are single hyphens, no leading/trailing hyphen, no empty subtags, no whitespace. Grandfathered tags matched against fixed table 26 entries (irregular `i-*` + `sgn-*` + regular `art-lojban` etc.) plus privateuse `x-*`. This is analogous to IBAN generic structure and BIC `8|11` length.

Formal regex (well-formed, not yet registry-valid):
```
well_formed = ^(?:[A-Za-z]{2,3}(?:-[A-Za-z]{3}){0,3}(?:-[A-Za-z]{4})?(?:-(?:[A-Za-z]{2}|\d{3}))?(?:-(?:[A-Za-z0-9]{5,8}|\d[A-Za-z0-9]{3}))* (?:-[A-Wa-wy-z0-9](?:-[A-Za-z0-9]{2,8})+)* (?:-x(?:-[A-Za-z0-9]{1,8})+)?|x(?:-[A-Za-z0-9]{1,8})+|(?:en-GB-oed|...grandfathered))$
```
Worked valid: `en`, `en-US`, `zh-Hans-CN`, `sl-nedis`, `de-CH-1996`, `en-GB-oxendict`, `zh-cmn`, `x-fr-CH`, `sr-Latn-RS`
Worked invalid: `en--US` (empty), `en-` (trailing), `-en` (leading), `e` (too short language), `en-US-123456789` (variant too long 9), `12-en` (starts with digit not language)

**Level 2 Registry membership (LOOKUP_TABLE):** Check every subtag exists in IANA registry with correct `Type`. Primary language must be `Type: language` where `Subtag` equals lowercased language (`en`, `zh`, `yue`, `cmn`). Script must be `Type: script` (`Latn`, `Hans`, `Cyrl`). Region must be `Type: region` (`US`, `CN`, `419`, `RS`). Variant must be `Type: variant` with `Prefix` field containing the tag prefix (e.g., `nedis` has `Prefix: sl`, `1996` has multiple prefixes, `oxendict` has `Prefix: en-GB`). This mirrors BIC country lookup and Country alpha-2 lookup.

Letter conversion table for BCP 47 is trivial (case-insensitive per §2.1.1, `A=a`); no MOD arithmetic.

**Level 3 Preferred / deprecated handling:** Deprecated subtags (`iw`, `in`, `ji`, `mo`, `sh` variant etc.) carry `Deprecated: <date>` plus `Preferred-Value: <code>` in registry. Rule returns `False` for deprecated subtag unless it normalizes via `Preferred-Value` chain — mirroring ISBN's `X`→`X` single alternate and ORCID's `x`→`X` case fold. Preferred chain is linear: `iw` (1989-01-01) → `he`, `in`→`id`, `ji`→`yi`, `jw` (2001-08-13)→`jv`, `mo` (2008-11-22)→`ro`, `bh` (2026-06-14)→`bih`, `i-cherokee`→`chr`. The rule's `normalize()` must apply chain recursively.

### 7.2 What makes Language "valid" vs "registered" vs "canonical"

- **valid (generic, well-formed)** — correct ABNF syntax, optionally including privateuse/grandfathered shapes; always-active PARSER; `en-XX` passes well-formed but fails membership
- **registered (registry-valid)** — valid plus every subtag exists in IANA registry with correct Type and Prefix/Scope; always-active LOOKUP_TABLE; `en-US` is registered, `en-ZZ` is well-formed but `ZZ` not in registry `Type: region` → `INVALID`
- **canonical (preferred)** — registered plus Deprecated→Preferred-Value applied (`iw` valid generic but canonical is `he`); presentational not validity
- **display-name valid** — lexicon name plus English Description lookup; bare `German`→`de` via table; `INVALID` if name not in English keys and `include_localized=False`

Like ISBN valid vs allocated, ISSN valid vs issued, IBAN valid vs country-valid.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase bare code (`en`, `deu`, `eng`) | SUCCESS → lower same | grammar folds lower, rule validates membership |
| 2 | Uppercase bare (`EN`, `DEU`, `ENG`) | SUCCESS → lower | case-insensitive per RFC 5646 §2.1.1, canonical lower |
| 3 | Grouped underscore locale (`fr_FR`, `EN_us`, `zh_Hans_CN`) | SUCCESS → `fr-FR`, `en-US`, `zh-Hans-CN` | underscore tolerance, canonical hyphen + case per §2.1.1 |
| 4 | BCP 47 canonical case (`zh-Hans-CN`, `sr-Latn-RS`) | SUCCESS → same | language lower, script Title, region Upper, already canonical |
| 5 | Mixed case tag (`EN-us`, `ZH-hans-CN`) | SUCCESS → `en-US`, `zh-Hans-CN` | case fold then case-restore via format_value |
| 6 | Grandfathered tag (`i-cherokee`, `en-GB-oed`, `zh-min-nan`) | SUCCESS → `chr`, `en-GB-oxendict`, `nan` (preferred) | Deprecated+Preferred-Value chain; without `include_grandfathered` may be `INVALID` |
| 7 | Deprecated code (`iw`→`he`, `in`→`id`, `mo`→`ro`) | SUCCESS → preferred lower | Deprecated→Preferred-Value; both valid but canonical is preferred |
| 8 | Collective code (`aus`, `afa`, `bih` scope collection) | `INVALID` by default, `SUCCESS` with `include_collective` | Scope: collection not individual language; gate via requires_features |
| 9 | Private-use primary (`qaa`, `x-fr-CH`, `en-x-private`) | `INVALID` by default, `SUCCESS` with `include_private` | Reserved `qaa-qtz` and `x` are valid per ABNF but private |
| 10 | Variant with prefix constraint (`sl-nedis` valid, `de-nedis` invalid) | `sl-nedis` SUCCESS, `de-nedis` INVALID | Variant `nedis` Prefix: `sl` per registry |
| 11 | Two distinct tags in one slice (`en, fr`) | AMBIGUOUS / MultipleMentionsError | segmentation intended, single-slice ambiguity |
| 12 | Sibling confusion (`EN` 2-letter country vs language) | SUCCESS if `en` is language, `US` alone MISSING (no language) | Position + registry Type disambiguates language vs country |
| 13 | Leading/trailing glue (`Xen`, `enUS`, `myen`) | MISSING | `(?<!\w)` / `(?!\w)` word-boundary guards block letter/digit-glued runs |
| 14 | Quoted/bracketed (`"en-US"`, `[fr-FR]`) | SUCCESS | inside punctuation, word_only boundary with quote is non-word so recognized |
| 15 | Over-long subtag (`abcdefghij` 10 chars) | MISSING | max 8 per subtag, regex never claims |
| 16 | Invalid subtag type (`en-Qaaa` private script as region) | INVALID | `Qaaa` is `Type: script` reserved private, not `Type: region`; membership fails |
| 17 | Script Suppress (`en-Latn` where en suppresses Latn) | SUCCESS (still valid) | Suppress-Script informative only, not reject (like BIC location 0/1/2) |
| 18 | Empty vs whitespace only (`""`, `"   "`) | MISSING | `StandardPre(empty_guard=True)` filters empties before lexicon/regex |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid bare code `en` (alpha2) or `eng` (alpha3) | SUCCESS → `en` or `eng` lower via language_code/language_name | single canonical via ISO 639 membership |
| Valid BCP47 tag `en-US`, `zh-Hans-CN`, `sl-nedis` | SUCCESS → `en-US` etc. case-canonicalized | single canonical via BCP47 well-formed + registry membership |
| Valid alternative case/underscore (`EN-US`, `fr_FR`→`fr-FR`) | SUCCESS (same `bcp47` compact) | presentation-only dedup, case/underscore normalization |
| Grandfathered `i-cherokee` preferred `chr` | SUCCESS → `chr` (or `en-GB-oed`→`en-GB-oxendict`) | Deprecated→Preferred-Value, distinct from distinct-identity branch |
| Deprecated code `iw`→`he` | SUCCESS → `he` | same pattern, preferred chain |
| Invalid language `xx`, `zzj` not in registry | INVALID | structural length ok but registry rejects |
| Invalid region `en-XX` where `XX` not Type: region | INVALID | language valid, region membership fails |
| Invalid variant prefix `de-nedis` | INVALID | variant exists but prefix mismatch `sl` vs `de` |
| No runs of required shape (`!` `#` numbers only) | MISSING | no grammar recognized (2-3 letters or bcp47 or name) |
| Two distinct valid in one slice (`en, fr` or `de fr`) | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity, use segmentation |
| Private code `qaa` with default flags | INVALID (MISSING if grammar gated) | valid per ABNF but dropped by `include_private=False` → INVALID |
| Collective `aus` with default flags | INVALID | Scope collection gate |
| Deprecated valid without preferred handling | INVALID if strict no-chain | chain-aware rule returns preferred, otherwise INVALID for deprecated raw |
| Test/private at pos `x-` or `Qaaa` | INVALID by default (private) or SUCCESS if `include_private` | informative but gated |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)
```bash
uv run python tools/new_capability.py Language --name language --authority "IETF" --spec-name "BCP 47 RFC 5646" --spec-url "https://www.rfc-editor.org/rfc/rfc5646.txt" --publication-year 2009
```
Creates 13 files + one edit: `paxman/capabilities/Language/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance. After scaffolding, add second provenance file manually (ISO 639-1, ISO 639-2, IANA registry each get their own `rules/*.py`).

### 10.2 Contract & grammar wiring
- `get_grammars()` returns `[BCP47TagGrammar(), LanguageCodeGrammar(), LanguageNameGrammar()]`, `active_grammars` omitted for initial design (base `None` runs every grammar), each grammar carries `name` `*_recognition` and non-empty `semantics` distinct (`bcp47_tag`, `language_code`, `language_name`)

### 10.3 Cross-cutting invariants (fail review if violated)
- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source
- No cross-capability imports (import only from `paxman.core`, import-linter enforced)
- No `output_format` token in any `paxman/capabilities/*/rules/` module (source-scan)
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts
- Deterministic by construction: same input + contract + library snapshot → same output

---

## 11. Recommended File Layout (mirrors Country and IBAN)

```
paxman/capabilities/Language/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   ├── bcp47_tag_recognition.py      # BCP 47 Regex, ABNF-approximate, longest shape
│   ├── language_code_recognition.py  # Bare code Regex 2-3/5-8
│   ├── language_name_recognition.py  # Display-name Lexicon
│   └── data/
│       ├── __init__.py
│       ├── english_names.py          # English Description keys (ISO 639/Iana)
│       ├── localized_names.py        # CLDR localized (optional, gated)
│       └── bcp47_keys.py             # key set for BCP47 well-formed fast-path (optional)
└── rules/
    ├── __init__.py
    ├── iso_639_1_ed2002.py
    ├── iso_639_2_ed1998.py
    ├── iso_639_3_ed2007.py
    ├── bcp47_rfc5646_ed2009.py
    ├── iana_language_subtag_registry_ed2026.py
    ├── cldr_language_display_name_ed2025.py  # optional gated
    └── data/
        ├── __init__.py
        ├── iso_639_1.py              # frozenset of 184 alpha-2
        ├── iso_639_2.py              # dict alpha-3 Term/Biblio
        ├── iso_639_3.py              # frozenset 7000+ + dict
        ├── iana_language_subtags.py  # frozenset Type: language
        ├── iana_region_subtags.py    # frozenset Type: region
        ├── iana_script_subtags.py    # frozenset Type: script
        ├── iana_variant_subtags.py   # dict variant→set(prefixes)
        └── iana_grandfathered.py     # dict grandfathered→preferred
```

Per-registry data module shape (parallel to Country `rules/data/iso_3166_ed2024.py`):
```python
# rules/data/iana_language_subtags.py
IANA_LANGUAGE_SUBTAGS: frozenset[str] = frozenset({"aa", "ab", ..., "zu", "aaa", ...})
IANA_DEPRECATED_MAP: dict[str, str] = {"iw": "he", "in": "id", "ji": "yi", "jw": "jv", "mo": "ro", ...}
IANA_GRANDFATHERED_PREFERRED: dict[str, str] = {"i-cherokee": "chr", "en-gb-oed": "en-GB-oxendict", ...}
```

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and Country/ISBN §9)

- Grammar tests: valid bcp47 `zh-Hans-CN`, bare `en`/`eng`, name `German`, underscore `fr_FR`, mixed case `EN-us`, multiple matches `en, fr`, incompatible `US` alone, empty, span invariants, name/semantics, boundary guard negatives (`Xen`, `enUS`, `Germanic`)
- Rule tests: bare code rule valid/variant/invalid (`en` valid, `xx` invalid, `EN` variant lower), bcp47 well-formed valid/invalid (`en-US` valid, `en--US` invalid), registry membership valid subtag/invalid subtag/prefix constraint (`sl-nedis` valid, `de-nedis` invalid), deprecated→preferred mapping exact, provenance attributes, name/strategy conventions, leading positions preserved; locale CLDR LOOKUP rule valid membership, requires_features gate, strategy LOOKUP_TABLE, kind registry
- Capability tests: notation frozen/hashable/slots, wiring counts (3 grammars, ~10 rules), grammar/rule name conventions, format_value round-trips (`en`→`en`/`eng`/`English`), create_contract factories, active_grammars default None
- Integration: MISSING/INVALID/SUCCESS/AMBIGUOUS or MultipleMentionsError, locale-underscore, year temporal filtering, _clean_registry fixture, determinism/VersionStamp, span-bearing match, dedup
- Property tests (hypothesis): generate valid by picking language from 184 α2 set plus optional script from IANA script set plus optional region from IANA region set plus optional variant with correct prefix → must canonicalize to itself via case-restore; random strings → INVALID with high probability; `fr_FR` vs `fr-FR` identical; `bcp47` vs `alpha2` extraction round-trip for primary `de`
- Consistency test: every shipped language_name key against ISO/Iana rule-data mappings, every IANA Type: language exercised via at least one bare code test
- Presentation purity: output_format source scan (no token in rules/)
- Real vectors: valid generic bare `en`, `eng`, `deu` bibliographic `ger`; underscore `fr_FR` → `fr-FR`; deprecated `iw`→`he`; grandfathered `i-cherokee`→`chr`; collective `aus` INVALID default vs SUCCESS gated; variant prefix invalid `de-nedis`; case variants `EN-US`→`en-US`

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `bcp47` vs `alpha2` vs `alpha3` | `bcp47` (canonical tag) | BCP 47 is the wire format (Accept-Language, HTML lang); `alpha2` truncates region/script and is lossy for `en-US` vs `en-GB`; presentational-only, `alpha2` offered for callers who need bare code |
| 2 | Three grammars vs single grammar | Three (`bcp47_tag`, `language_code`, `language_name`) initially, distinct semantics | Mirrors Country precedent; enables rule routing per type; avoids conflating ABNF parse vs lexicon membership |
| 3 | Deprecated→Preferred chain: always apply vs strict | Always apply chain in `normalize()` (iw→he etc.), but `matches()` accepts both as valid (deprecated not rejected) | RFC 5646 §3.4 deprecated remains valid; stability guarantees callers depend on deprecated being accepted; chain makes canonical deterministic |
| 4 | Grammar length strictness | Regex enforces `2*3ALPHA` for language, `4ALPHA` script, `2ALPHA|3DIGIT` region, `5*8alphanum` variant exactly; never claim `1` or `9+` per subtag | Keeps grammar cheap and definitive; matches ABNF |
| 5 | Case/underscore normalization locus | Grammar folds lower and `_`→`-` for recognition; rules validate lower; `format_value()` restores canonical casing (lower/title/upper) | Syntax vs semantics boundary; rules never see raw underscore |
| 6 | Collective codes (Scope: collection) | Reject by default (`INVALID`), opt-in via `include_collective` | Collections are not individual languages; prevents `aus` false SUCCESS for language ID |
| 7 | Private-use `qaa-qtz` and `x-*` | Reject by default, opt-in via `include_private` | Private codes are valid per BCP 47 but not assigned languages; default should be "assigned only" |
| 8 | Grandfathered valid but deprecated | Accept as SUCCESS with preferred canonical by default (`include_grandfathered=True`) | 26 tags are deprecated but still valid; without this ETL would break on legacy corpora |
| 9 | Underscore separator tolerance | Grammar handles hyphen-only via `_GUARD` contiguous, but offer `Pre` underscore→hyphen for POSIX locales; document | Spec allows only `-` in tag, but real copy-paste hits `_`; minimal v1 could keep hyphen-only and document tolerance as extension |
| 10 | Single PUBLICATION vs split | Split per ISO publication: one file per ISO part plus BCP47 plus IANA registry (6 files) | Fused would hide lineage; per-publication purity demands split, though small language can ship fused `iso_639_ed202X` for brevity |

---

## 14. Ambiguity Analysis (Paxman-specific)

- No inherent language-tag vs language-tag positional ambiguity — fixed ABNF with hyphen separators eliminates Date-style positional ambiguity; two distinct tags in one slice (`en, fr`) is authorial choice (list), segmentation intended, not lexical ambiguity.
- Language code vs Country code is not lexical ambiguity — `en` (language) vs `US` (region) disambiguated by position: `en-US` language+region is one tag, bare `US` is Country not Language (registry Type distinguishes); `de` alone is Language `de` (German), not Country confusion.
- Bare `eng` vs `en` is not ambiguity but alternative canonical forms — same language identity, distinct strings; without contract `output_format` choice Paxman will produce two candidates (`language_code` semantics `eng`→`en` mapping plus `bcp47_tag` `en`) that may dedup to `SUCCESS` only if normalize coalesces to `en`, else `AMBIGUOUS`. Contract `alpha2` vs `alpha3` resolves via format, not via filtering.
- Deprecated vs preferred is not ambiguity — `iw` (deprecated) and `he` (preferred) are same language via registry Preferred-Value, `normalize()` chain makes them identical, so dedup succeeds not ambiguates.
- Staleness is not ambiguity — determinism-by-snapshot, IANA File-Date version in Provenance.version (`Rolling File-Date YYYY-MM-DD`); a tag valid in 2026-08-08 may be invalid in later snapshot but that is snapshot staleness, not authorial ambiguity.
- Suppressed script vs explicit script is not validity ambiguity — `en-Latn` where `en` suppresses `Latn` is still valid (informative, not reject), like BIC location `0`/`1`/`2`.

---

## 15. URL Reference (authoritative, fetched 2026-08-23)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 639-1:2002 (2nd ed., current, Confirmed 2023) | https://www.iso.org/standard/22109.html | primary |
| ISO 639-2:1998 (1st ed., current, 487 codes, T/B) | https://www.iso.org/standard/4767.html | primary |
| ISO 639-3:2007 (1st ed., current, 7000+ codes, SIL RA) | https://www.iso.org/standard/39534.html | primary |
| ISO 639-5:2008 (1st ed., current, families/groups) | https://www.iso.org/standard/39536.html | primary |
| ISO 639:1988 lineage (first unified) | https://www.iso.org/standard/6506.html (withdrawn lineage) | primary (secondary for lineage) |
| BCP 47 RFC 5646 (Sept 2009, BCP:47, obsoletes 4646, Phillips & Davis) | https://www.rfc-editor.org/rfc/rfc5646.txt | primary |
| BCP 47 RFC 4647 (Matching of Language Tags) | https://www.rfc-editor.org/rfc/rfc4647.txt | primary |
| IANA Language Subtag Registry (File-Date 2026-08-08, 7790+ languages) | https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry | primary |
| IANA Language Subtag Registry overview + maintenance | https://www.iana.org/assignments/language-subtag-registry/ | primary |
| ISO 639-2 RA code list (Library of Congress, T/B table) | https://www.loc.gov/standards/iso639-2/php/code_list.php | primary |
| ISO 639-2 RA English/French name changes | https://www.loc.gov/standards/iso639-2/php/code_changes.php | primary (secondary) |
| ISO 639-3 RA code tables (SIL International) | https://iso639-3.sil.org/code_tables/639/data | primary |
| SIL 639-3 download table (tab-delimited) | https://iso639-3.sil.org/sites/default/files/iso-639-3_Code_Tables/download_tables/20250123/iso-639-3.tab | primary (secondary fetch) |
| ISO 15924 script codes (normatively referenced for script subtag) | https://www.unicode.org/iso15924/iso15924-codes.html | primary |
| ISO 3166-1 region codes (normatively referenced for region subtag) | https://www.iso.org/iso-3166-country-codes.html | primary |
| UN M.49 numeric region codes (normatively referenced) | https://unstats.un.org/unsd/methodology/m49/ | primary |
| pycountry languages database (ISO 639 fusion) | https://github.com/pycountry/pycountry/blob/master/src/pycountry/databases/iso639-3.json | primary |
| langcodes Language.get canonicalization | https://github.com/LuminosoInsight/langcodes/blob/master/langcodes/__init__.py | primary |
| iso639 Python package (ISO 639-3 lookup) | https://github.com/miss-islington/iso639/blob/master/iso639/__init__.py | primary |
| validator.js isISO6391 | https://github.com/validatorjs/validator.js/blob/master/src/lib/isISO6391.js | primary |
| validator.js isBCP47 | https://github.com/validatorjs/validator.js/blob/master/src/lib/isBCP47.js | primary |
| CLDR language display names (Unicode CLDR charts) | https://www.unicode.org/cldr/charts/46/summary/root.html | primary (registry) |
| Wikipedia ISO 639 lineage (secondary) | https://en.wikipedia.org/wiki/ISO_639 | secondary |
| Paxman HOW_TO_ADD_NEW_CAPABILITY | ../../HOW_TO_ADD_NEW_CAPABILITY.md | primary |
| Paxman HOW_TO_ADD_NEW_GRAMMAR | ../../HOW_TO_ADD_NEW_GRAMMAR.md | primary |
| Paxman ARCHITECTURE | ../../ARCHITECTURE.md | primary |
| ISSN research precedent | docs/development/research/2026-08-21-issn-canonicalization.md | primary |
| IBAN research precedent | docs/development/research/2026-08-22-iban-canonicalization.md | primary |
| BIC research precedent | docs/development/research/2026-08-23-bic-canonicalization.md | primary |
| ORCID research precedent | docs/development/research/2026-08-23-orcid-canonicalization.md | primary |
| Paxman shipped precedent — Country alpha2/alpha3/name | paxman/capabilities/Country/grammar/alpha2_recognition.py etc. | primary |
| Paxman shipped precedent — Country rules + data | paxman/capabilities/Country/rules/iso_3166_ed2024.py etc. + paxman/engine/orchestrator.py | primary |
| Paxman shipped precedent — BIC staged PipelineGrammar | paxman/capabilities/BIC/grammar/bic_recognition.py + paxman/core/domain.py Rule.__init_subclass__ | primary |

---

## 16. Evidence Completion — Resolved

This report's Language-specific authoritative evidence has been fetched and cited (2026-08-23):
- [x] ISO catalogue entry: ISO 639-1:2002 (2nd ed., 184 codes, Confirmed) plus ISO 639-2:1998 (487, T/B, Library of Congress RA) plus ISO 639-3:2007 (7000+, SIL RA) plus ISO 639-5:2008 families plus lineage back to 639:1988; ICS 01.140.20; TC 37; version lifecycle publication_year; citation anchored to spec §4
- [x] BCP 47 RFC 5646 (BCP:47, Sept 2009, obsoletes 4646, Best Current Practice, Phillips & Davis, ABNF Fig.1) superseding RFC 4646 and RFC 3066 and RFC 1766, plus RFC 4647 Matching, plus ABNF RFC 5234
- [x] RA and Registry provenance: IANA Language Subtag Registry (File-Date 2026-08-08, rolling weekly), Language Subtag Reviewer, Type: language 7790+ plus region/script/variant/grandfathered, File-Date version, lifecycle active
- [x] Structure: alpha-2 2 letters / alpha-3 3 letters (T/B) / comprehensive 7000+ / BCP47 tag ABNF (language ["-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse]), grandfathered 26, privateuse `qaa-qtz` + `x-`
- [x] No checksum proved (syntactic + registry membership only, RFC 5646 §3.4 stability, IANA registry stability, like BIC has no checksum unlike IBAN)
- [x] Collective/private nuance: Scope: collection (`aus` etc.), `qaa-qtz` reserved private, `x` privateuse, gating decisions with include_* flags
- [x] Ecosystem regex consensus: RFC 5646 ABNF + pycountry lookup + langcodes `Language.get().to_tag()` + iso639 package + validator.js isISO6391/isBCP47
- [x] Wild input shapes validated (§2.1 19 categories) against spec + IANA registry + CLDR + validators (bare code, name English/localized, BCP47 with script/region/variant/extension/privateuse/grandfathered, underscore, case, deprecated preferred chain)
- [x] Grandfathered scope decision (26 tags, all deprecated, Preferred-Value replacement `i-cherokee`→`chr` etc.)
- [x] Deprecated→Preferred chain decision (iw→he etc., linear chain, always apply)
- [x] Private/collective liveness scope decision (gated via include_private/include_collective)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped Country, Currency, ISBN, and BIC Capabilities Teach Language (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

Refer to `paxman/capabilities/Country/` (4 grammars alpha2/alpha3/numeric/name, Lexicon via `WholeInputLookup` + `normalize_name` + `grammar/data/*_names.py` key sets), `paxman/capabilities/Currency/` (code/symbol/word, LOOKUP_TABLE), `paxman/capabilities/ISBN/` (Regex grammars isbn13/isbn10, PARSER check), `paxman/capabilities/IBAN/` (single grammar with paper tolerance, MOD 97), `paxman/capabilities/BIC/` (single grammar 8/11 optional group, 2-level syntactic, Lexicon country), `paxman/capabilities/ORCID/` (single grammar hyphenated vs URI optional group, MOD 11-2), plus `paxman/engine/orchestrator.py` (_dedup_spans longer-wins per grammar, _validate_affinity, single_value) and `paxman/core/domain.py` (Rule.__init_subclass__ six attributes, Grammar.__init_subclass__ semantics) — see deep-dive summary in §4.2 / §5 / §6 above and the explore-verified notation, grammar, and rule excerpts. The four architectural lessons for Language:
1. **Grammar strips, rule validates, capability formats.** Like Country `alpha2` strips via `isalnum().upper()` and rule `LOOKUP_TABLE` owns meaning, Language grammars strip case/underscore and registry owns meaning. `normalize()` returns default `bcp47` canonical; `format_value()` renders `alpha2/alpha3/name` without re-validation.
2. **One file per provenance, one class per section.** Like ISBN three files (ISO 2108, Users Manual, Range Message) and Country two (ISO 3166, CLDR), Language splits ISO 639-1/2/3, BCP 47, IANA registry each into its own `rules/*.py` with single `PUBLICATION` constant.
3. **No `output_format` in rules, ever.** Like BIC `PARSER` vs `LOOKUP_TABLE`, Language `LOOKUP_TABLE` for code membership and `PARSER` for BCP47 ABNF never read `output_format`; CI scan rejects it.
4. **Multiple grammars with distinct semantics avoid spurious AMBIGUOUS; cross-grammar containment is preserved.** Like Country's alpha2/alpha3 vs name lexicon, Language's bcp47_tag vs language_code vs language_name each has its own `target_semantics`; cross-grammar `en` inside `en-US` is preserved for affinity routing, not deduped.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for Language. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the ORCID precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
