# Timezone Canonicalization Research — paxman-python

**Date:** 2026-09-14
**Scope:** Primary-source survey of the timezone-identifier domain (IANA Time Zone Database as de-facto identifier standard, ISO 8601 / RFC 3339 numeric offsets, CLDR metazone and Windows-zone data), ecosystem resolution practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `Timezone` capability. No source code, tests, or configuration were modified.
**Evidence basis:** IANA tzdb pages and data files (iana.org/time-zones, theory.html, zone1970.tab, zone.tab, backward, releases), RFC 9636 (TZif, obsoletes 8536), RFC 6557 (tzdb maintenance), RFC 3339 (offsets), ISO 8601-1:2019 catalogue page, CLDR TR35 (time-zone names, metazones, primary/windows zones), Python zoneinfo/pytz/dateutil/moment-timezone/pandas/Django/tzlocal docs and sources, python-stdnum absence survey, one wild normalizer (vellum date-context.ts), and shipped Paxman precedent (MacAddress, Country, Language, Date, ISBN) plus HOWTOs, ARCHITECTURE, and ADRs 0009/0010/0011/0012. Repo state: `dev @ e8eab36` — 18 shipped capabilities, kernel kinds regex/lexicon/scanner/combinator/candidates/label, engine owns per-grammar containment dedup + total recognition ordering, `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN (2026-08-21), IBAN (2026-08-22), BIC (2026-08-23), and MacAddress (2026-08-31) research precedents.

---

## Executive Summary

Timezone is a **strong** fit for a Paxman capability and the highest unbuilt MILESTONE entry (#3): it has an unambiguous canonical form for the common case (**IANA zone key**, e.g. `America/New_York`), a stable de-facto single-part standard (IANA Time Zone Database, rolling releases, current `2026d` of 2026-09-11) with a maintenance procedure (RFC 6557) and interchange format (RFC 9636 TZif), a maintained authoritative directory (**zone1970.tab**, ~310 canonical Zones; **backward**, ~250 Links), and a messy human surface (legacy links, `Etc/GMT±X`, `UTC+5:30`, bare abbreviations, Windows names) that is exactly Paxman's recognize-tolerant/validate-strict value proposition. There is **no checksum** — keys are names, structure is membership plus offset-range arithmetic (proven below).

Key findings that shape the design:
1. **Canonical form is the IANA zone key, case-sensitive** (`America/New_York`); Links resolve to canonical (`US/Eastern` → `America/New_York`, art-lojban→jbo precedent) **as registry-declared aliases in the pinned snapshot** — never by comparing transitions. Numeric offsets are a **separate capability** (`UtcOffset`, §7.4/§13.1): a zone plus a timestamp yields an offset, irreversibly — `EDT` ↛ `America/New_York`, `-04:00` ↛ `America/New_York`. That irreversibility is the paper's conceptual centerpiece: Paxman canonicalizes provable equivalence, never interprets intent.
2. **Two grammars (+ one deferred) for `Timezone`, one for `UtcOffset`**: `timezone_name_recognition` (lexicon over vendored identifier keys **excluding** short-caps backward Links, case-insensitive recognize / case-exact validate), `timezone_abbreviation_recognition` (lexicon over the curated set; rule resolves nothing silently — short-caps Links and ambiguous abbreviations alike go INVALID, §10–11). No coalescing — disjoint rules. Offsets live in `UtcOffset` with their own regex grammar.
3. **Validation is two-level**: PARSER for offset structure/range (|offset| ≤ 14:00) in `UtcOffset`; LOOKUP_TABLE for key membership against a vendored identifier set (zone1970 geographic subset + etcetera/UTC + backward Links — **never zone1970.tab alone**) in `Timezone`. Bare short-caps Links (`EST`, `CET`) go INVALID via the abbreviation family even though the identical string exists in `backward`: identifier equivalence ≠ lexical abbreviation equivalence (§10–11). Ambiguous ones (`IST`, `CST`) INVALID — recognized but refused, the Coordinates foreign-CRS refusal precedent. No silent pick, ever.
4. **Link-vs-canonical is IANA Link equivalence (snapshot-bound)** → `link` as an offered output is DOWNGRADED to an open alternative (OFFERED={`link`}→recommended OFFERED={} for v1): choosing *which* alias to render is arbitrary policy, and alias-rendering is transformation, not canonicalization. Offsets/abbreviations as outputs stay rejected (lossy or time-dependent). Windows names (`Eastern Standard Time`) are territory-sensitive CLDR policy mappings, not identities → DEFERRED with no v1 flag (future capability or territory-aware contract).
5. **Provenance splits cleanly** per HOWTO Step 5: IANA tzdb (registry kind, rolling version) for keys/links/abbreviation table; ISO 8601 (representations) + RFC 3339 (timestamp-compatible subset) + documented Paxman human forms for offset syntax; CLDR (cited, deferred) for Windows names.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---
## 1. Target User

| Persona | Why they need timezone canonicalization | Typical context |
|---|---|---|
| Data-pipeline engineer | Log/API timestamps arrive with `EST`, `UTC+5`, `US/Eastern`, `PST` in free text; downstream joins need one key per zone | ETL cleaning loops, pandas `tz_localize` prep |
| App/platform developer | Config values (`TIME_ZONE = "america/new_york"`, `"EST"`) must be validated before `ZoneInfo()` raises at runtime | Django `TIME_ZONE`, tzlocal, container env |
| Travel/calendar UX | Users type `CET`, `Tokyo time`, `GMT+8`; the UI must resolve or honestly refuse | Search boxes, scheduling forms |
| API ingestion | Partner payloads carry Windows names (`Eastern Standard Time`) or POSIX strings; storage needs IANA keys | ETL + Django `activate()` |

**User-visible contract:** The caller supplies raw human text and a contract; Paxman returns one canonical timezone (IANA key) or `MISSING`/`INVALID`/`AMBIGUOUS` with citation (offsets: sibling `UtcOffset` capability). This mirrors Country/Language ergonomics, but the canonical default is the **case-sensitive IANA zone key**.

---
## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| IANA canonical key | `America/New_York`, `Asia/Kolkata` | zone1970.tab (~310 rows); zoneinfo `ZoneInfo(key)`; Django `TIME_ZONE` | canonical | RECOGNIZE | name lexicon (folded view, exact validate) |
| Legacy Link key | `US/Eastern`, `Asia/Calcutta` | tzdb `backward` (~250 Links); pytz `all_timezones`; `ZoneInfo("US/Eastern")` (PEP 615 discussion) | common | RECOGNIZE (resolves to canonical) | name lexicon, rule maps via link table |
| IANA backward-compat POSIX-style zone | `EST5EDT`, `CST6CDT` | tzdb `backward` (4 SystemV Zones on `USback` rules) | rare | RECOGNIZE always; rule gated (`include_systemv=False` → INVALID) | name lexicon; `requires_features` (no syntactic basis for a split grammar — cf. `include_private` precedent) |
| `Etc/*` + `UTC` | `Etc/GMT+5`, `Etc/UTC`, `UTC` | tzdb `etcetera`; probed `ZoneInfo("UTC")`/`ZoneInfo("Etc/GMT+5")` OK 2026-09-14 (implementer re-verifies `Etc/UTC`, bare `GMT` at snapshot build) | common | RECOGNIZE | name lexicon |
| `UTC`/`GMT` offset token | `UTC+5`, `GMT-05:30`, `UTC+05:30` | vellum `UTC_GMT_OFFSET_TOKEN_RE`; Intl validation pipelines; moment `Etc/GMT±X` docs | common | MOVED to `UtcOffset` — RECOGNIZE there under documented *human* semantics (`GMT+5`→`+05:00`; POSIX TZ expressions rejected, §7.4) | offset regex (`UTC|GMT[+-]H[:MM]`) |
| Bare numeric offset | `+0530`, `-08:00`, `+05:30` | dateutil `parse` (`tzoffset`); `strptime %z`; RFC 3339 `time-numoffset`; ISO 8601 basic/reduced forms | common | MOVED to `UtcOffset` — RECOGNIZE there (→ `+05:30`) | offset regex branch |
| `Z` designator | `Z` (alone, not in a timestamp) | RFC 3339 `time-offset`; military Zulu | occasional | MOVED to `UtcOffset` — RECOGNIZE there (→ `+00:00`) | offset regex branch |
| Bare abbreviation, backward Link spelled | `EST`, `MST`, `HST`, `CET` | tzdb `backward` (`EST`→`America/Panama`, `MST`→`America/Phoenix`, `HST`→`Pacific/Honolulu`, `CET`→`Europe/Brussels`) | common | RECOGNIZE → INVALID (carved out of the name lexicon into the abbreviation family: identifier equivalence ≠ lexical abbreviation equivalence, §10–11) | abbreviation lexicon; rule refuses (name lexicon excludes short-caps Links) |
| Bare abbreviation, ambiguous | `IST` (India/Ireland/Israel), `CST` (Chicago/Shanghai/Havana) | theory.html ("IST can refer to India, Ireland or Israel"); RFC 9636 §5 (CST×3); timeanddate IST/CST pages (secondary) | common | RECOGNIZE → INVALID (refused, never silent pick) | abbreviation lexicon; rule resolves Links, refuses the rest |
| Bare abbreviation, unlisted | `XYZ`, `ABC` | — (negative space) | — | MISSING (grammar emits nothing) | absent from lexicon |
| Windows zone name | `Eastern Standard Time` | CLDR `windowsZones` (`Eastern Standard Time` ↔ `America/New_York`); Windows `gettz` | common on Windows-origin data | DEFER, no v1 flag (territory-sensitive CLDR policy mapping, not an identity — needs a contextual discriminator or separate capability, §12) | future `WindowsTimezone` or territory-aware contract |
| Lowercase key | `america/new_york`, `utc` | pytz case-fold (`us/eastern` succeeds); BIC fold precedent | common | RECOGNIZE (fold; validate canonical case) | lowered view, rule restores case |
| `TZ:`/`Timezone:` label | `TZ: America/New_York` | weak attestation (no spec/validator consensus found) | rare | DEFER (community `extra_grammars`) | fused label `[\s:-]+` (BIC precedent) if ever built |
| Space-for-underscore | `America/New York` | common typo, no authority | occasional | REJECT (indistinguishable from prose; `_` normative per theory POSIX rules) | documented negative test |
| Full POSIX rule string | `EST5EDT,M3.2.0/2` | dateutil `gettz` accepts (tzstr) | rare | REJECT (rule syntax, not an identifier; SystemV *names* already covered) | documented negative test |
| Military single letters | `A` (=+1), `N` (=-1) | nonstandard, ambiguous | rare | REJECT (nonstandard, ambiguous) | documented negative test |
| `Zulu` word | `Zulu` | military/aviation usage; NOT a tzdb key (verified: `ZoneInfo("Zulu")` raises) | occasional | REJECT (not an identifier; `Z`/`UTC` cover the instant) | documented negative test |

A v1 that ignored bare abbreviations would ship a permanent blind spot on one of the most-written forms (`EST`/`PST`/`CET` in logs); the RECOGNIZE→refuse design covers them honestly.

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|---|---|---|
| 1 | Canonical key | `America/New_York` | master form, exact case |
| 2 | Lowercase / mixed case | `america/new_york`, `AMERICA/NEW_YORK` | fold + validate canonical case (pytz-insensitive vs zoneinfo-strict variance) |
| 3 | Legacy link | `US/Eastern`, `Asia/Calcutta` | resolve to canonical (`America/New_York`, `Asia/Kolkata`) |
| 4 | SystemV name | `EST5EDT` | rule-gated flag; INVALID when off (recognized, unvalidated) |
| 5 | `Etc/GMT` sign trap | `Etc/GMT+5` (= UTC−5, POSIX-inverted) | no reinterpretation; key validates as itself |
| 6 | UTC/GMT offsets | `UTC+5`, `GMT-05:30`, `UTC+05:30` | `H` 1–2 digits, `MM` exactly 2, range ≤14:00 |
| 7 | Bare numeric offsets | `+0530`, `-08:00`, `+05` | RFC 3339 `±HH:MM`; ISO basic `±HHMM`; reduced `±HH` |
| 8 | `Z` alone | `Z` | → `+00:00` in `UtcOffset`; not confused with Zulu word (REJECT) |
| 9 | Abbreviations | `IST`, `CST`, `EST`, `CET` → INVALID (ambiguous + carved alike) | refused, never resolved; carve rule §10–11 |
| 10 | Windows names | `Eastern Standard Time` | gated; MISSING by default |
| 11 | Label with colon/space | `TZ: EST` | DEFERRED form; v1 MISSING |
| 12 | Irregular whitespace | `  America/New_York  ` | trimmed input (A0 whole-input exemption, #122) |
| 13 | Trailing annotation | `America/New_York (EDT)` | span covers key only, not parenthetical |
| 14 | Multiple per line | `US/Eastern then America/Chicago` | two mentions → AMBIGUOUS/MultipleMentionsError (`single_value=True`) |
| 15 | Quoted / bracketed | `"CET"`, `[JST]` | inside punctuation, span excludes quotes |
| 16 | `US/`-glued runs | `XUS/Eastern`, `US/EasternX` | custom `/`-aware boundary (mac_midrun precedent) |
| 17 | Over-long / under-long | `America/`, `/New_York`, `U` | length/shape guard → MISSING |
| 18 | Unknown key | `America/Narnia`, `Mars/Olympus` | grammar claims shape, rule rejects → INVALID |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| vellum date-context.ts (wild normalizer) | `UTC_GMT_OFFSET_TOKEN_RE = /^(?:UTC\|GMT)([+-])(\d{1,2})(?::?(\d{2}))?$/i` + range-check ≤14:00 + `Etc/GMT±H` POSIX-sign flip for whole hours; `TIMEZONE_ABBREVIATIONS = {PST:…, EST:"America/New_York", CET:"Europe/Paris", IST: ambiguous…}` then `Intl.DateTimeFormat(timeZone)` validation |
| pytz `__init__.py` | `_case_insensitive_zone_lookup`: `_all_timezones_lower_to_standard.get(zone.lower()) or zone`; `UnknownTimeZoneError` on miss; `UTC` upper-fold singleton |
| Python zoneinfo (PEP 615) | `ZoneInfo(key)`: POSIX-path join on TZPATH; `ValueError` on bad shape; `ZoneInfoNotFoundError(KeyError)` on miss; case-sensitive; Links resolve as distinct keys |
| dateutil `gettz` | IANA/file/POSIX-TZ/Windows-name acceptance; `gettz("EST")` → fixed `-05:00` tzfile (NOT US Eastern DST); `GMT+0530` POSIX-sign-reversed (known gotcha) |
| moment-timezone | `zone.abbr(timestamp)` timestamp-dependent (`PST`↔`PDT`); docs: abbreviations "not globally unique" (`CST` Chicago vs Shanghai); no-abbr fallback `"+11"`/`"+0530"` |
| pandas `tz_localize` | `ambiguous='raise'`, `nonexistent='raise'` — validates DST edge semantics, not names |
| Django 4.0+ | `TIME_ZONE` must be a valid `ZoneInfo` key; `activate()` accepts string via `ZoneInfo()` |
| python-stdnum | **No timezone module** (~200 formats, none tz) — weak validator consensus, recognition must come from IANA/CLDR, not ecosystem |

**Normalization contract (BIC fold precedent; offset half lives in `UtcOffset`):**
```python
key = raw.strip()
candidate = _CASE_FOLD.get(key.lower(), key)  # rule restores canonical case
offset = _normalize_offset(raw)  # 'UTC+5' -> '+05:00', '+0530' -> '+05:30'
# (human-notation semantics, never POSIX)
```

### 2.3 What input is NOT a timezone mention
- Month/day words (`May`, `March`) — no tz meaning → MISSING (no grammar claims them).
- Country/place prose (`Greenwich village`, `Jordan` the country vs `Asia/Amman`) — MISSING unless an exact key matches.
- `GMT` the place vs offset prefix: bare `GMT`/`UTC` → SUCCESS fixed (`Etc/GMT` semantics, +00:00, in `Timezone`); `GMT+0530` human token → `+05:30` in `UtcOffset` (POSIX trap documented — POSIX would read −05:30, which is why the grammar is explicitly human-semantics, never sign-flipped by us).
- Single letters (`A`, `Z` the letter in prose) — `Z` alone is claimed ONLY as offset designator by the offset grammar with boundary guards; prose `Z` (e.g. "Model Z") → MISSING via word guards.
- Durations (`+05:30` as a UTC offset vs a time arithmetic fragment) — offset grammar claims with boundary + range guards; ambiguous prose stays the caller's segmentation problem.

### 2.4 Single-mention vs multi-mention input
Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, `docs/recipes/segmentation.md` ADR-0004). Two distinct zones (`US/Eastern then America/Chicago`) → `AMBIGUOUS`/`MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS`. (`EST then CET` is INVALID+INVALID → INVALID — refused mentions do not compete.)

---
## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — key plus family discriminator
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TimezoneNotation:
    """One timezone mention: canonical-shape carrier + input family.

    ``key`` is the as-written mention (case-preserved); ``family`` records
    which grammar produced it (``name`` | ``abbreviation``)
    so rules route without re-parsing. ``compact`` is the normalized
    candidate (identifier key as-written). Offsets live in `UtcOffset`
    with their own notation (canonical +HH:MM).
    """

    key: str
    family: str
    compact: str
```

**Considered alternative — single field `compact` only:** loses the family routing the rules need (key membership vs abbreviation table are disjoint validations sharing one `matches` would re-parse). The decomposition is preferred because 1. rules route by family without re-parsing, 2. abbreviation refusal reasons differ by family (`backward`-Link carve vs ambiguous).

**Invariants the grammar enforces (before rules):**
- `family` is exactly one of `name`/`abbreviation`.
- name `key` matches `[A-Za-z0-9_+\-]+(/[A-Za-z0-9_+\-]+)+` or is in the flat-name set (`UTC`, `Etc/*`, single-component legacy) — always slash-joined or bare; short-caps `backward` Links are excluded here (abbreviation family, §10–11).
- abbreviation `key` is `[A-Z]{2,5}` as-written (uppercased from `[A-Za-z]{2,5}`).

### 3.2 Why not carry spaces or labels in the notation
Spaces, `TZ:` labels, and case variants have **no lexical significance** — presentation is `Capability.format_value()` only (MacAddress compact precedent).

### 3.3 Why `family` is not a shape discriminator literal
Free `str` validated by rule routing (each rule's `target_semantics` selects its family), mirroring how `shape` routes MacAddress EUI-48/64 and SIUnit split/base — grammar honesty without Literal rigidity.

---
## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Lexicon ×2 (+ Regex ×1 in `UtcOffset`)
Per HOW_TO_ADD_NEW_GRAMMAR.md, `Timezone` proper is a **vocabulary** capability: IANA keys + abbreviations are finite vocabularies (Lexicon ×2, disjoint semantics ids, no coalescing). Offsets are fixed-shape syntax (Regex ×1) but live in the separate `UtcOffset` capability (§7.4/§13.1) — one grammar per semantic domain. Scanner/combinator/candidates/label kinds fit no family (no running-text scan, no slot composition, no same-meaning alternation set).

### 4.2 Reference pattern (MacAddress verbatim precedent, new-kernel matchers form)
MacAddress precedent (`paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:69-98`):
```python
_MAC_GUARD = BoundaryGuard.mac_midrun()
_MAC_PATTERN = _MAC_GUARD.lookbehind + _MAC_BODY + _MAC_GUARD.lookahead
```
New-kernel form (`paxman/capabilities/Country/grammar/name_recognition.py:33-57`): `LexiconMatcher(tokens=..., boundary=BoundarySpec.WORD, view="country_normalized", representation="trie")` with keys-only emit.

**Proposed Timezone patterns:**
```python
import re
from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.core.grammar import AnchorSet
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.data.common_words import COMMON_WORDS
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.pipeline import PipelineGrammar

_TIMEZONE_NAME_TOKENS: frozenset[str] = frozenset(...)  # lowered IANA keys+Links
_TIMEZONE_ABBR_TOKENS: frozenset[str] = frozenset(...)  # UPPER abbreviations
_OFFSET_BODY = r"(?:[Uu][Tt][Cc]|[Gg][Mm][Tt])?[+-](?:[01]?\d|14)(?::?[0-5]\d)?|[Zz]"


class TimezoneNameGrammar(PipelineGrammar[TimezoneNotation]):
    name = "timezone_name_recognition"
    semantics = "timezone_name"
    single_value = True
    matchers = (
        LexiconMatcher(
            tokens=_TIMEZONE_NAME_TOKENS,
            boundary=BoundaryGuard.timezone_slash_only(),  # NEW: single internal `/`
            view="timezone_folded",  # lowered view; rule restores canonical case
        ),
    )
```
*Notes on fidelity:* lowered-view + rule-restores-case mirrors BIC fold-then-validate; the `/`-aware boundary is new (mac_midrun precedent: `XUS/Eastern`/`US/EasternX` must not fuse — `/` is otherwise prose); abbreviation lexicon is case-exact UPPER (abbreviations are uppercase by convention; lowercase `est` the word is Estonian — MISSING is correct); offsets live in `UtcOffset` (see §7.4).

**Offset matcher sketch (lives in `UtcOffset`, same kernel idiom):**
```python
_OFFSET_BODY = (
    r"(?:[Uu][Tt][Cc]|[Gg][Mm][Tt])?[+-](?:1[0-4]|0?\d)(?::?[0-5]\d)?"
    r"|[Zz]"
)


class UtcOffsetGrammar(PipelineGrammar[UtcOffsetNotation]):
    name = "utc_offset_recognition"
    semantics = "utc_offset"
    single_value = True
    matchers = (
        RegexMatcher(
            pattern=BoundaryGuard.word_only().lookbehind
            + _OFFSET_BODY
            + BoundaryGuard.word_only().lookahead,
            view=None,
            emit=_offset_emit,  # zero-pads + colons (canonical +HH:MM; Z gives +00:00)
        ),
    )


class TimezoneAbbreviationGrammar(PipelineGrammar[TimezoneNotation]):
    name = "timezone_abbreviation_recognition"
    semantics = "timezone_abbreviation"
    single_value = True
    matchers = (
        LexiconMatcher(
            tokens=_TIMEZONE_ABBR_TOKENS,  # UPPER only; curated §7.3 set
            boundary=BoundarySpec.WORD,
            view=None,  # case-exact: no folded view by design
        ),
    )
```
**Form-coverage traceability:** every §2.1 RECOGNIZE row maps to one of the three matchers; DEFER (`TZ:` label) awaits a label matcher; REJECT rows are documented negatives. `suppress_common_words`: name/abbreviation matchers set `suppressible=False` — the only COMMON_WORDS intersection found is `us` (a path component of `US/*` links, never a standalone mention), and suppressing inside a key would corrupt spans.

**One grammar vs three:** three (recommended) — disjoint vocabularies/rules; a single grammar would need alternation across unrelated shapes and shared semantics, muddying rule routing. No cross-grammar containment (key vs offset vs abbreviation shapes are disjoint — no spurious AMBIGUOUS).

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)
- Grammar emits span-bearing `RecognitionMatch`, half-open `[start,end)`, `raw_text == text[start:end]`.
- Engine owns within-grammar containment dedup (longer wins) and total recognition ordering `(start,end,active-idx,name)`.
- Candidate dedup `(value, recognition_rule, validation_rule)` after validation; `single_value=True` → multi-mention `MultipleMentionsError`.

### 4.4 Guard boundaries against sibling grammars
| Grammar | Chars | Boundary behavior |
|---|---|---|
| timezone_name | `A-Za-z0-9_+-,/` | custom: single internal `/` allowed; edges exclude alnum AND `/` (no mid-path extraction) |
| utc_offset (`UtcOffset`) | `+-:0-9Zz, UTCGMTutc` | word guards + slash-aware lookbehind (no mid-key extraction from `Etc/GMT+5`) + `MM<60`, `|HH|≤14` range guards |
| timezone_abbreviation | `A-Z` (2–5) | WORD guards both sides (bare `EST` in prose claims; `ESTIMATE` must not) |
| Sibling (Country `IN`, Language `en`) | — | length/case discrimination: 2–5 UPPER + tz-table membership decides |

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)
- `timezone_name` / `timezone_abbreviation` — two identity ids, one rule family each. A future Windows capability would be separate (territory-contextual), not Option B here.

### 4.6 `single_value` — one mention per call vs batch processing
`single_value=True` initially (shipped precedent); `US/Eastern then America/Chicago` → `MultipleMentionsError`; segmentation recipe for batches.

### 4.7 Evidence classes for equivalence (hard rule for this and future capabilities)

| Class | Meaning | Timezone example | May canonicalize? |
|---|---|---|---|
| A — Normative registry equivalence | Authority declares X IS Y | `US/Eastern` Link→`America/New_York` (backward) | YES |
| B — Normative representation equivalence | Standard defines the rendering | `+0530` basic form → `+05:30` (ISO 8601); POSIX component rules | YES |
| C — Explicit compatibility alias | Authority ships alias map | backward Links incl. short-caps (`CET`) | YES (as class A in practice) |
| D — Ecosystem convention | Libraries tolerate, authority silent | pytz case-folding; dateutil fixed-`EST` | Only with a construction guarantee (see below) |
| E — Heuristic interpretation | Commonly meant, not established | `GMT+5`→`+05:00` as POSIX; `IST`→`Asia/Kolkata` | NO — reject or separate policy |

Hard rule: only A/B/C participate in canonicalization. Class D is admissible **iff** the authority's namespace construction makes the mapping injective — the tzdb POSIX component rules forbid case-variant collisions, so case-folding is presentation (same justification as BIC's uppercase alphabet, shipped precedent). Class E never canonicalizes (documented human-notation grammars like `utc_offset_human` state their convention explicitly instead of claiming standard semantics).

### 4.8 Equivalence proofs (semantic freeze checklist for implementation)

### `US/Eastern → America/New_York`
Evidence: tzdb 2026d `backward`: `Link America/New_York US/Eastern`. Therefore: Equivalent = YES. Basis = class A (registry-defined alias, snapshot-bound).

### `america/new_york → America/New_York`
Evidence: tzdb POSIX component rules forbid case-variant collisions (theory.html); zoneinfo strictness is implementation choice (filesystem), pytz folding is convenience. Therefore: Equivalent = YES. Basis = class D admitted by construction guarantee (injective namespace — no two keys differ by case alone). Counter-proof obligation on implementer: assert it over the vendored set.

### `EST → INVALID` (not `America/Panama`)
Evidence: `backward` defines the Link (class A for the *identifier* reading), but the bare token's dominant reading is the human abbreviation, which is ambiguous (theory.html, RFC 9636 §5). The name lexicon carves short-caps Links into the abbreviation family, whose rule refuses. Therefore: Equivalent = NO (as abbreviation). Basis = §10–11 carve rule; the literal-Link seeker writes `America/Panama`.

### `GMT+5 → +05:00` (in `UtcOffset`)
Evidence: NOT POSIX (POSIX would read UTC−05:00) — documented *human* notation per the vellum/Intl convention. Therefore: Equivalent = YES within the explicitly human-semantics grammar. Basis = class E promoted by explicit capability policy (`UtcOffset` documents human semantics in grammar + guide, §7.4).

---
## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | IANA (PTI/ICANN) — de-facto identifier standard; no ISO zone-ID standard exists (ISO 8601-1:2019 covers representations only) |
| Registration Authority | IANA Time Zone Database community (coordinators Eggert/Parenti), procedure RFC 6557 |
| Spec name | IANA Time Zone Database, release `2026d` (2026-09-11); interchange RFC 9636 (TZif v1–v4, obsoletes RFC 8536) |
| Current edition | Rolling; File-Date-pinned snapshot vendored (precedent: `File-Date: 2026-08-08` headers) |
| Check character system | **None** — keys are names; structure is membership + offset arithmetic (proven: theory.html defines no check digits; zone files contain transitions, not checksums) |
| Country code reference | zone1970.tab col 1 = ISO 3166 codes (most-populous first) |
| Related specs | ISO 8601-1:2019 / RFC 3339 (offsets), CLDR TR35 (metazones, windowsZones — deferred use) |

**Structure (tzdb):** Zone records (`Zone NAME STDOFF RULES FORMAT [UNTIL]`), Link records (`Link TARGET LINK-NAME`), `backward` = old/merged names + SystemV + abbreviation Links (`EST→America/Panama`, `CET→Europe/Brussels`, `MST→America/Phoenix`, `HST→Pacific/Honolulu`), `etcetera` (`Etc/*`, `UTC`), POSIX component rules (≤14 chars, ASCII, no digits/case-variants), `Etc/Unknown` reserved (2025a).

**Lineage table:**

| Edition / event | Date | Status | Note |
|---|---|---|---|
| Olson stewardship (tzcode/tzdata, FTP) | 1986–2011 | Superseded | Arthur David Olson founding maintainer |
| IANA adoption, RFC 6557 (BCP 175) procedures | 2011–2012 | Active | Normative reference for protocol values; `tz@iana.org` list |
| `backzone` split (2014g) | 2014 | Active | Pre-1970-only differences out of tzdb proper |
| Australia abbreviation fix (2014f) | 2014 | Active | `AEST/AEDT` replace bare `EST` — evidence abbreviations mutate |
| `zonenow.tab` added (2023d) | 2023 | Active | Coarse now-and-future partition |
| RFC 9636 TZif v4 (obsoletes 8536) | 2024 | Active | Truncatable leap tables; format only, not identifiers |
| `Etc/Unknown` reserved (2025a) | 2025 | Active | Unknown/invalid marker |
| Release `2026d` (NWT Canada → permanent −06) | 2026-09-11 | Current | Snapshot candidate File-Date |

**ISO 8601 offset lineage:** 1988 (first) → 2000 → 2004 → 2019-1/-2 (current, Published) — representations of UTC time shifts only, never zone identifiers.

**Citation Details Table (for Provenance):**

| authority | spec_name | version | reference_url | lifecycle | publication_year | kind |
|---|---|---|---|---|---|---|
| IANA | Time Zone Database | 2026d (rolling) | https://www.iana.org/time-zones | active | 2026 | registry |
| IETF | RFC 9636 (TZif) | 2024 (obsoletes 8536) | https://www.rfc-editor.org/info/rfc9636 | active | 2024 | specification |
| IETF | RFC 3339 (timestamps) | 2002 | https://www.rfc-editor.org/info/rfc3339 | active | 2002 | specification |
| Unicode | CLDR windowsZones/metaZones | 47+ (deferred use) | https://unicode.org/reports/tr35/tr35-dates.html | active | 2025 | registry |

### 5.2 Rule / publication map (one file per publication — HOW_TO Step 5)
| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|----------------|-------------------|
| rules/iana_tzdb_ed2026.py | authority="IANA", specification_name="Time Zone Database", kind="registry", reference_url="https://www.iana.org/time-zones", version="2026d", lifecycle="active", publication_year=2026 | Section zone-key-membership; Section link-resolution | Key in vendored set (case-exact after fold); Links resolve to canonical (backward table) |
| rules/iso8601_offset_ed2019.py (`UtcOffset` capability) | authority="ISO", specification_name="ISO 8601-1", kind="specification", reference_url="https://www.iso.org/standard/70907.html", version="2019", lifecycle="active", publication_year=2019 (RFC 3339 §5.6 cited per-section for the timestamp-compatible `±HH:MM`/`Z` subset) | Section 3-offset-representations | Offset shape + range (\|HH\|≤14, MM<60); normalize to `+HH:MM`; `-00:00` refused |
| rules/iana_tz_abbreviations_ed2026.py | authority="IANA", specification_name="Time Zone Database", kind="registry", reference_url="https://data.iana.org/time-zones/theory.html", version="2026d", lifecycle="active", publication_year=2026 | Section abbreviation-exact; Section abbreviation-ambiguous | Exact-name zones SUCCESS as themselves; ambiguous abbreviations INVALID (never silent pick) |

Each `Rule[TimezoneNotation]` subclass declares the six enforced metadata attributes (`Rule.__init_subclass__`, `paxman/core/domain.py:236-271`).

**Rule subclass template (MacAddress §8.2 shape, LOOKUP variant shown):**
```python
from paxman.capabilities.Timezone.notation import TimezoneNotation
from paxman.capabilities.Timezone.rules.data.iana_zone_identifiers import (
    IANA_ZONE_IDENTIFIERS,
)
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IANA",
    specification_name="Time Zone Database",
    kind="registry",
    reference_url="https://www.iana.org/time-zones",
    version="2026d",
    lifecycle="active",
    publication_year=2026,
)


class SectionZoneKeyMembership(Rule[TimezoneNotation]):
    """IANA identifier membership (case-exact after grammar fold)."""

    name = "Section zone-key-membership"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "zone1970.tab col 3 + backward Links + etcetera (vendored File-Date)"
    target_semantics = frozenset({"timezone_name"})
    requires_features = frozenset()

    def matches(self, notation: TimezoneNotation, contract: object) -> bool:
        return notation.compact in IANA_ZONE_IDENTIFIERS

    def normalize(self, notation: TimezoneNotation, contract: object) -> str:
        return notation.compact
```

### 5.3 What each rule does vs does not own
- `matches()` validates strictly, never raises; contract misconfigs caught in `contract.__post_init__`.
- `normalize()` returns the default canonical (identifier key / link target), never reads `output_format` (CI purity scan `tests/unit/test_rule_output_format_purity.py`).
- `RuleStrategy`: PARSER for offset structure, LOOKUP_TABLE for key membership + abbreviation table.
- `include_systemv` gates via `requires_features` (dropped rule → INVALID); grammar toggles via contract flags (disabled → MISSING). Never gate inside `matches()`.

### 5.4 Scope decision (Timezone analogue of IBAN §5.4 / BIC §5.4)
Paxman validates identifier membership against a pinned edition (valid-in-snapshot-X); temporal applicability is never evaluated — liveness needs a clock. What ships: name validity (always-active) + link resolution (always-active; Links are current registry-declared aliases) + SystemV behind its flag (Windows deferred entirely). Snapshot File-Date + `Provenance.version` (rolling `2026d`) carry staleness, exactly like currency-snapshot precedent.

### 5.5 Assignment / registration authority & registry content
IANA distributes; zone assignments reflect on-the-ground consensus via `tz@iana.org` (RFC 6557 §3–4, ~20 releases/year historically, politics-driven). **Timezone canonicalization is registry-version dependent** — results are valid-in-snapshot-X, never timelessly (cf. 2026d behavior changes). Vendored snapshot: zone1970.tab (~310 canonical geographic Zones — a subset, not the universe) + `backward` Links (~250, incl. abbreviation Links) + `etcetera`/`UTC` + curated abbreviation table (backward-abbrev Links + documented-ambiguous refusal set from theory.html + CLDR metazones). `backzone` (pre-1970-only) excluded — out of tzdb proper scope. Table roles: zone1970.tab (geography, most-populous-first ISO codes) vs zone.tab (older compatibility, one country/row, col-3 may be a Link) vs zonenow.tab (coarse now-and-future partition). Environment tzdata varies: in one minimal container probed 2026-09-14, `zoneinfo.available_timezones()` returned 486 keys yet `ZoneInfo("US/Eastern")` raised `ZoneInfoNotFoundError` (backward Links not compiled in) — direct motivation for vendoring the snapshot instead of reading environment tzdata.

---
## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO §7)
```python
from dataclasses import dataclass, field
from typing import ClassVar
from paxman.core.contract import CapabilityContract

@dataclass(frozen=True)
class TimezoneContract(CapabilityContract):
    """IANA key default; no offered formats in v1 (`link` rendering stays
    an open alternative — alias choice has no authority, §13.7).

    Offsets live in `UtcOffset`; abbreviations are never offered
    (lossy or time-dependent); Windows names are deferred entirely
    (territory-sensitive, §12).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "iana"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()
    capability_name: str = field(default="timezone", init=False)
    include_systemv: bool = False
```

- `DEFAULT_OUTPUT_FORMAT = "iana"` (canonical identifier key).
- OFFERED = `{}` for v1; `link` rendering stays an open alternative (§13.7) because alias choice has no authority. Offset/abbreviation/Windows outputs REJECTED: family-distinct entities, lossy/time-dependent readings, and territory-sensitive policy mappings respectively (IANA: "use numeric offsets").
- `create_contract()` fixed keyword-only common block (`excluded_rules, pinned_rules, year, output_format, extra_grammars, suppress_common_words`) then `include_systemv`. `year` filters by `publication_year` (tzdb 2026 → `year=2020` drops the key rule → INVALID, MacAddress §8.2 precedent).
- Presentational-only invariant; `output_format` never in rules.

| output_format | value example | Meaning |
|---|---|---|
| *(default)* `iana` / `None` / `"default"` | `America/New_York` | canonical identifier key (identity) |

### 6.2 Capability (HOW_TO §6)
```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.Timezone.notation import TimezoneNotation

class TimezoneCapability(Capability[TimezoneNotation]):
    name = "timezone"
    def get_grammars(self) -> list[Grammar[TimezoneNotation]]: return [...]
    def get_rules(self) -> list[Rule[TimezoneNotation]]: return [...]
    @staticmethod
    def create_contract(...) -> TimezoneContract: ...
    def format_value(self, value: str, output_format: str | None, notation: TimezoneNotation) -> str: ...
```

Registration via `tools/new_capability.py` (`Step 0`); `__all__` + bootstrap wiring.

---
## 7. Validation — key-valid vs link-resolved vs abbreviation vs offset

### 7.1 Level 1 Key membership (LOOKUP_TABLE, always-active)
Folded mention restores canonical case via map (namespace-guaranteed injective — POSIX component rules forbid case variants, §4.7 class D); membership in the vendored identifier set (case-exact). `america/new_york` → `America/New_York` SUCCESS (BIC fold precedent); `America/Narnia` → INVALID.

### 7.2 Level 2 Link resolution (LOOKUP_TABLE, always-active)
`backward` map: `US/Eastern` → `America/New_York`, `Asia/Calcutta` → `Asia/Kolkata`, `CET` → `Europe/Brussels`. Mechanically like Language `DEPRECATED_MAP` (Preferred-Value) but semantically distinct: Links are *current* aliases, valid keys where tzdata ships `backward` (`zoneinfo` accepts `US/Eastern` on full installs, PEP 615 — but minimal containers may omit Links entirely, cf. §5.5 probe), and canonicalization resolves them for one-value-per-entity (art-lojban→jbo precedent).

### 7.3 Level 3 Abbreviations (LOOKUP_TABLE, always-active; curated table)
Abbreviation tokens that are `backward` Links (`EST`, `MST`, `HST`, `CET` — verified in-file) are carved out of the name lexicon into the abbreviation family (§10–11) → INVALID, exactly like ambiguous abbreviations with no Link (`IST`, `CST`, …). Unlisted (`XYZ`) → MISSING at grammar. Rationale: identifier equivalence ≠ lexical abbreviation equivalence; the literal-Link seeker writes the canonical key.

**Curated abbreviation starter table** (implementer verifies each against `backward` + theory.html; `*` = refusal set with contender zones documented):

| Abbreviation | Disposition | Target / contenders |
|---|---|---|
| `EST` * | Carved → INVALID (Link to `America/Panama`; seeker writes the canonical) | `America/Panama` |
| `MST` * | Carved → INVALID (Link to `America/Phoenix`) | `America/Phoenix` |
| `HST` * | Carved → INVALID (Link to `Pacific/Honolulu`) | `Pacific/Honolulu` |
| `CET` * | Carved → INVALID (Link to `Europe/Brussels`) | `Europe/Brussels` |
| `IST` * | Refuse → INVALID | `Asia/Kolkata`, `Europe/Dublin`, `Asia/Jerusalem` |
| `CST` * | Refuse → INVALID | `America/Chicago`, `Asia/Shanghai`, `America/Havana` |
| `PST` * | Refuse → INVALID | `America/Los_Angeles` + historical Philippine use (theory.html) |
| `JST`/`WET`/`EET`/`MSK`… | Implementer verifies | admit as Link if in `backward`, else refusal set or MISSING |

### 7.4 Level 4 Offsets — moved to `UtcOffset` (PARSER, always-active there)
Shape `UTC|GMT[+-]H[:MM]` (documented *human* notation — NOT POSIX: POSIX `GMT+5` would read UTC−05:00, so the grammar is explicitly human-semantics, §6) / `Z` / `±HHMM` / `±HH:MM`; range `|HH| ≤ 14` (Kiritimati precedent, vellum range-check), `MM < 60`; `Z` → `+00:00`; POSIX TZ rule strings (`EST5EDT,M3.2.0/2`) REJECTED (rule syntax, not an identifier). `±HH`/`±HHMM` provenance: ISO 8601 basic/reduced forms; `±HH:MM`/`Z`: ISO 8601 extended + RFC 3339 timestamp-compatible subset (RFC 3339 governs timestamps, not standalone values — syntax sources mapped per form, not blanket-attributed). `-00:00` (RFC 3339 unknown-offset) → INVALID: it states ignorance of the offset, a different entity from zero — Paxman has no unknown-offset information state in v1.

### 7.5 What makes a mention "zone-valid" vs "link-resolved" vs "offset"
- zone-valid — identifier in the vendored set (zone1970 geographic subset + etcetera/UTC + backward; never zone1970.tab alone, §3) → canonical key.
- link-resolved — key in backward map (IANA Link equivalence, snapshot-bound, §4.8) → canonical target.

- membership, not liveness — valid-in-snapshot-X vs absent; no temporal applicability is evaluated.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|---|---|---|
| 1 | Lowercase key | `america/new_york` → SUCCESS `America/New_York` | fold + exact validate (BIC precedent) |
| 2 | Legacy link | `US/Eastern` → SUCCESS `America/New_York` | backward resolution, snapshot-bound alias |
| 3 | SystemV gated off | `EST5EDT` default → INVALID | rule dropped (`requires_features`), shape still claimed |
| 4 | SystemV gated on | `EST5EDT` + flag → SUCCESS `EST5EDT` | fixed-rule zone, valid key |
| 5 | Etc/GMT sign trap | `Etc/GMT+5` → SUCCESS `Etc/GMT+5` (UTC−5, as authored) in `Timezone`; under `UtcOffset` → MISSING (slash-glued guard rejects mid-key extraction) | never reinterpret POSIX inversion; slash-aware lookbehind |
| 6 | Offset family | `UTC+5` → SUCCESS `+05:00`, `+0530` → `+05:30` (in `UtcOffset`) | zero-pad + colon normalize, human semantics; ISO basic form |
| 7 | `Z` alone | `Z` → SUCCESS `+00:00` (in `UtcOffset`) | zero designator |
| 8 | Unknown offset | `-00:00` → INVALID | RFC 3339 unknown-offset is ignorance, not zero — no such entity in v1 |
| 9 | Carved abbreviation | `EST` → INVALID (Link to `America/Panama` exists, but bare short-caps reads as abbreviation, §10–11) | carve rule; seeker writes the canonical |
| 10 | Ambiguous abbreviation | `IST` → INVALID (India/Ireland/Israel) | recognized, refused — no silent pick |
| 11 | Unknown abbreviation | `XYZ` → MISSING | not in lexicon |
| 12 | Unknown key | `America/Narnia` → INVALID | shape claimed, membership failed |
| 13 | Windows name | `Eastern Standard Time` → MISSING | deferred entirely (no v1 grammar; territory-sensitive) |
| 14 | Embedded in sentence | `arrive CET tomorrow` → INVALID (`CET` refused everywhere bare) / `visit US/Eastern tomorrow` → SUCCESS `America/New_York` span | WORD guards; carve rule vs path link |
| 15 | Two distinct in one slice | `US/Eastern then America/Chicago` → AMBIGUOUS/MultipleMentionsError | `single_value=True` |
| 16 | Glued runs + paths | `XUS/Eastern` → MISSING; `/usr/share/zoneinfo/America/New_York` → MISSING (path context; split first) | `/`-aware boundary: edges exclude alnum and `/` |
| 17 | Out-of-range offset | `UTC+15:00` → INVALID | \|HH\| ≤ 14 |
| 18 | `Zulu` word | `Zulu` → MISSING | not a tzdb key (verified raises) |

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

(`Timezone` rows; `UtcOffset` outcomes in brackets.)

| Input | Status | Why |
|-------|--------|-----|
| Valid key / link | SUCCESS → canonical | registry-declared alias/membership, snapshot-bound |
| Case variants (`america/new_york`) | SUCCESS (same canonical) | fold safe by namespace construction (§4.7 class D) |
| Short-caps Link spelled bare (`EST`) | INVALID | abbreviation-family refusal (§10–11 carve rule) |
| Ambiguous abbreviation (`IST`) | INVALID | recognized, refused — genuine ambiguity without timestamp |
| Unknown key (`America/Narnia`) | INVALID | structural failure, rule rejects |
| No tz shape (`hello world`) | MISSING | no grammar recognized |
| Two distinct zones in one slice | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity, use segmentation |
| Gated-off form (`EST5EDT` default) | INVALID | rule dropped (`requires_features`), shape claimed |
| `year=2020` filtering tzdb-2026 rule | INVALID | temporal rule filtering (MacAddress precedent) |
| `output_format="abbreviation"` | raises `ContractError` | lossy projection, never offered (ADR-0011) |

**Post-review semantic matrix (normative summary):**

| Input | Result | Reason |
|---|---|---|
| `America/New_York` | SUCCESS → `America/New_York` | canonical IANA identifier |
| `US/Eastern` | SUCCESS → `America/New_York` | explicit IANA Link (class A) |
| `Etc/GMT+5` | SUCCESS → `Etc/GMT+5` | canonical fixed zone, sign kept |
| `EST5EDT` (+flag) | SUCCESS → `EST5EDT` | IANA backward-compat zone (gated) |
| `america/new_york` | SUCCESS → `America/New_York` | fold safe by namespace construction |
| `EST` / `CST` / `IST` / `PST` | INVALID | abbreviation, no silent pick (§10–11) |
| `Eastern Standard Time` | MISSING | Windows namespace deferred, no context |
| `UTC+05:30` / `+0530` / `Z` | `UtcOffset` → `+05:30` / `+00:00` | fixed offset, human notation |
| `-00:00` | INVALID | unknown-offset ≠ zero; no such entity in v1 |
| `GMT+5` | `UtcOffset` → `+05:00` | documented human notation (not POSIX) |
| `America/Narnia` / `Zulu` | INVALID / MISSING | unregistered / not an identifier |

---
## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOWTO Step 0)
```bash
uv run python tools/new_capability.py Timezone --name timezone --authority "IANA" --spec-name "Time Zone Database" --spec-url "https://www.iana.org/time-zones" --publication-year 2026
```
Creates 13 files + one edit: `paxman/capabilities/Timezone/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance. After scaffolding `Timezone`, add the abbreviation rule file manually; scaffold `UtcOffset` separately (HOWTO Step 0 per capability).

### 10.2 Contract & grammar wiring
- `get_grammars()` returns the two grammars; `active_grammars` omitted entirely (base `None` runs all); each grammar carries `*_recognition` name + non-empty semantics; `include_systemv` is rule-level `requires_features` (Language `include_private` precedent — vocabulary subset, not input shape, so Option B over `active_grammars`).

### 10.3 Cross-cutting invariants (fail review if violated)
- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports (only `paxman.core`; import-linter enforced).
- No `output_format` token in any `rules/` module (source-scan).
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts.
- Deterministic by construction: same input + contract + library snapshot → same output (no clock, no DST lookups, no environment tzdata — vendored snapshot only).

---
## 11. Recommended File Layout (mirrors ISSN and IBAN)

```
paxman/capabilities/Timezone/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   ├── timezone_name_recognition.py
│   └── timezone_abbreviation_recognition.py
└── rules/
    ├── __init__.py
    ├── iana_tzdb_ed2026.py
    ├── iana_tz_abbreviations_ed2026.py
    └── data/
        ├── iana_zone_identifiers.py # canonical Zones + fixed zones + Links (frozenset;
        │                             zone1970.tab is the geographic subset, not the universe)
        ├── iana_zone_links.py       # backward Link → canonical (dict)
        ├── iana_fixed_zones.py      # etcetera fixed-offset zones (Etc/*, UTC)
        └── abbreviation_map.py      # short-caps Link carve list + ambiguous-abbr refusal set

paxman/capabilities/UtcOffset/          # separate capability (§7.4, §13.1)
├── __init__.py
├── capability.py                     # DEFAULT `extended` (+HH:MM), OFFERED {`basic`} (+HHMM)
├── contract.py
├── notation.py                       # UtcOffsetNotation(compact)
├── grammar/
│   ├── __init__.py
│   └── utc_offset_recognition.py
└── rules/
    ├── __init__.py
    └── iso8601_offset_ed2019.py      # representations + range; -00:00 refused
```

Per-registry data module shape (parallel to ISBN `rules/data/range_message.py`):
```python
# rules/data/iana_zone_links.py
ZONE_LINKS: dict[str, str] = {"us/eastern": "America/New_York", ...}
```

---
## 12. Test Strategy (mirrors HOWTO and ISSN §9)

- Grammar tests: canonical key / link / SystemV / Etc / offset forms / Z / abbreviations / lowercase fold / multiple matches / glued runs / empty / span invariants / name+semantics / boundary negatives — plus one positive vector per §2.1 RECOGNIZE form.
- Rule tests: key membership valid/fold/invalid + link resolution + exact-vs-ambiguous abbreviation + offset range/normalize + provenance attributes + names/strategies + `requires_features` gates.
- Capability tests: notation frozen/hashable/slots, wiring counts, `create_contract` factories (`UtcOffset`: `basic`-form re-entry).
- Integration: MISSING/INVALID/SUCCESS/AMBIGUOUS + MultipleMentionsError, flag gating, `year` filtering, `_clean_registry`, determinism/VersionStamp, span-bearing match, dedup.
- Property tests (hypothesis): valid keys canonicalize to themselves; random strings → MISSING/INVALID with high probability; `format_value` round-trip (ADR-0011 preservation matrix + injectivity pairs, `UtcOffset` basic/extended).
- Consistency test: every shipped key covered by rule mappings; every abbreviation key in the refusal/carve table (+ name-lexicon carve assertion: no `^[A-Z]{2,5}$` backward Link in name keys); semantics↔target affinity.
- Presentation purity: `output_format` source scan.
- Real vectors: `US/Eastern`→`America/New_York`, `utc+5`→`+05:00` (`UtcOffset`), `IST`→INVALID, `Z`→`+00:00` (`UtcOffset`), `EST`→INVALID + carve note, `-00:00`→INVALID.

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | Timezone vs UtcOffset split (offsets were §2-rounded into Timezone) | Split: `Timezone` = identifiers only; `UtcOffset` = offsets (`+HH:MM` canonical, `Z`→`+00:00`) | Zone+timestamp→offset is irreversible; one-canonical-shape per capability; `-00:00`→INVALID |
| 2 | Single grammar vs two (+`UtcOffset`) | Two (name/abbreviation), disjoint semantics; offsets in `UtcOffset` | disjoint rules; avoids alternation muddle + spurious AMBIGUOUS |
| 3 | Abbreviation refusal vs AMBIGUOUS fan-out | Refuse (INVALID); fan-out needs grammar-side mapping (separation breach) or rule fan-out (machinery absent — `_collect_candidates` yields one candidate per rule) | Coordinates refusal precedent; honest without new machinery |
| 4 | Short-caps Links (`EST`/`MST`/`HST`/`CET`) in name vs abbreviation family | Abbreviation family → INVALID (carve rule: `backward` Links matching `^[A-Z]{2,5}$`, except Zone-defined `UTC`/`GMT`) | Identifier equivalence ≠ lexical abbreviation equivalence; the dominant reading is ambiguous-human, and the literal-Link seeker writes the canonical key |
| 5 | Case handling | Recognize folded, validate canonical case | BIC precedent; zoneinfo-strict vs pytz-lax variance resolved toward tolerance + exactness |
| 6 | `/`-boundary | Custom guard: single internal `/`; edges exclude alnum AND `/`; offset lookbehind additionally excludes `/` (new `BoundaryGuard` variant) | mac_midrun precedent; `/` is prose otherwise; blocks mid-key (`Etc/GMT+5`) and mid-path extraction |
| 7 | `link` offered format | Recommended OFFERED={} for v1; `link` rendering stays an open alternative | alias choice has no authority; rendering aliases is transformation, not canonicalization |
| 8 | Windows names | DEFER with no v1 flag (future capability or territory-aware contract) | territory-sensitive CLDR policy mapping, not an identity; a flag without a discriminator cannot determine |
| 9 | SystemV default | Recognize but flag-gated off (`include_systemv=False`, `backward`-optional theory) | obscure zones; INVALID by default is safe |
| 10 | `single_value` for batch | True initially, segmentation for multi | shipped precedent |
| 11 | Space-underscore / POSIX-strings / military letters | REJECT all three with documented negatives | lossy / rule-syntax / nonstandard; revisit via `extra_grammars` on evidence |

---
## 14. Ambiguity Analysis (Paxman-specific)

- The irreversibility centerpiece: `America/New_York` + timestamp → `-04:00`, but `-04:00` ↛ `America/New_York` and `EDT` ↛ `America/New_York` without additional information. Identifier, offset, and abbreviation form a one-way ladder (zone ⇒ offset given time ⇒ abbreviation given locale rules), never reversible. Timezone is Paxman's identity case precisely because the arrows do not reverse — canonicalize what is provably equivalent, never interpret intent.
- Paxman timezone law: **an abbreviation is not a timezone identifier merely because it is commonly used as one.** `EST` spelled identically to a `backward` Link is still refused — the carve rule (§10–11) keeps short-caps Links in the abbreviation family.
- Abbreviation collision is refused ambiguity, not hidden ambiguity — `IST`→INVALID with rule reason is the Coordinates foreign-CRS refusal pattern: the library declines to guess where IANA itself says "use numeric offsets." This differs from Date `01/02/2026` AMBIGUOUS only in that no timestamp-scoped reading exists to offer.
- Link-vs-canonical is not ambiguity — `US/Eastern` is a registry-declared alias of `America/New_York` in the pinned snapshot (IANA Link equivalence, §4.8); canonicalization resolves aliases, full stop. No transition comparison is performed or needed.
- Offset-vs-zone is not ambiguity — `+05:00` (fixed shift, `UtcOffset`) and `America/New_York` (rule set) are distinct entities in distinct capabilities that never compete for one span.
- DST time-dependence is not ambiguity, it is excluded world-knowledge — zone→offset needs a timestamp (clock), so offsets are never *derived*, only *read* as authored (RFC 3339 steers clear for the same reason).
- The `Etc/GMT` sign trap is not ambiguity — `Etc/GMT+5` keeps its registry meaning (UTC−5); human `GMT+5` tokens belong to `UtcOffset` under documented human semantics. Neither flips signs. No cross-capability conflict exists (`Timezone` and `UtcOffset` never run in one call), and within `UtcOffset` the slash-aware lookbehind refuses mid-key extraction, so one input can never yield both readings from one contract.
- Snapshot membership, not liveness — Paxman validates identifier membership against a pinned tzdb edition; it does not evaluate temporal applicability. Renames demote to Links (theory.html Rule 2) and `Provenance.version` carries the edition — that is the whole staleness story.

---
## 15. URL Reference (authoritative, fetched 2026-09-14)

| Claim | URL | Kind |
|-------|-----|------|
| IANA tzdb overview, coordinators, cadence, 2026d (2026-09-11) | https://www.iana.org/time-zones | primary |
| tzdb releases (2014f AEST fix, 2021b/2022b merges, 2023d zonenow, 2025a Etc/Unknown) | https://www.iana.org/time-zones/releases | primary |
| theory.html (abbreviations, Rule 2 renames, stability, `-00`, POSIX names) | https://data.iana.org/time-zones/theory.html | primary |
| zone1970.tab (~310 rows, columns) | https://raw.githubusercontent.com/eggert/tz/main/zone1970.tab | primary |
| zone.tab (backward-compat, one country/row) | https://raw.githubusercontent.com/eggert/tz/main/zone.tab | primary |
| backward (252 Links + 4 Zones verified 2026-09-14: EST/MST/HST/CET/WET links; no IST/CST/PST/JST; EST5EDT-class are Zones) | https://raw.githubusercontent.com/eggert/tz/main/backward | primary |
| RFC 9636 TZif v4 (obsoletes 8536) | https://www.rfc-editor.org/info/rfc9636 | primary |
| RFC 6557 tzdb maintenance procedures | https://www.rfc-editor.org/info/rfc6557 | primary |
| RFC 3339 offsets (`Z`, `±HH:MM`), §1/§4 steer-clear | https://www.rfc-editor.org/info/rfc3339 | primary |
| ISO 8601-1:2019 catalogue (representations only) | https://www.iso.org/standard/70907.html | primary |
| CLDR TR35 time-zone names/metazones/primary/windows | https://unicode.org/reports/tr35/tr35-dates.html | primary |
| CLDR metaZones.xml (America_Eastern, Europe_Central) | https://raw.githubusercontent.com/unicode-org/cldr/main/common/supplemental/metaZones.xml | primary |
| Python zoneinfo (`ZoneInfo(key)`, case-sensitive, Links) | https://docs.python.org/3/library/zoneinfo.html | primary |
| PEP 615 (`US/Eastern` link discussion) | https://peps.python.org/pep-0615/ | primary |
| pytz (`_case_insensitive_zone_lookup`, `UnknownTimeZoneError`, common/all lists) | https://github.com/stub42/pytz/blob/master/src/pytz/__init__.py | primary |
| dateutil `gettz` (IANA/POSIX/Windows, EST fixed-hole, 2.7.0 caching) | https://dateutil.readthedocs.io/en/stable/tz.html | primary |
| moment-timezone (`abbr(timestamp)`, CST collision, `Etc/GMT` sign, counts) | https://momentjs.com/timezone/docs/ | primary |
| pandas `tz_localize` ambiguous/nonexistent | https://pandas.pydata.org/docs/reference/api/pandas.Series.tz_localize.html | primary |
| Django time zones (`ZoneInfo` key validation) | https://docs.djangoproject.com/en/5.0/topics/i18n/timezones/ | primary |
| tzlocal (env-file resolution, never abbreviations) | https://github.com/regebro/tzlocal | primary |
| python-stdnum (absence of tz module) | https://github.com/arthurdejong/python-stdnum | primary (absence) |
| Wikipedia 2026d tz list (counts compilation) | https://en.wikipedia.org/wiki/List_of_tz_database_time_zones | secondary |
| timeanddate IST/CST/EST/AEST pages (collisions) | https://www.timeanddate.com/time/zones/ist | secondary |
| BIC research precedent (template) | docs/development/research/2026-08-23-bic-canonicalization.md | primary (repo) |
| IBAN research precedent (checksum depth) | docs/development/research/2026-08-22-iban-canonicalization.md | primary (repo) |
| MacAddress research precedent (latest capability) | docs/development/research/2026-08-31-mac-address-canonicalization.md | primary (repo) |
| HOWTO capability/grammar, ARCHITECTURE, ADRs | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, docs/adr/ | primary (repo) |

---
## 16. Evidence Completion — Resolved

This report's Timezone-specific authoritative evidence has been fetched and cited (2026-09-14):
- [x] tzdb overview: rolling releases, current 2026d, coordinators, cadence; TC/SC n/a (IANA, not ISO); version lifecycle + publication_year pinned for Provenance
- [x] RA and registry provenance: IANA distributorship, zone1970.tab (~310) + backward (~250 Links) + etcetera + `version` file; RFC 6557 procedures
- [x] Structure: Zone/Link records, POSIX name rules, `Etc/Unknown` reservation, zone.tab vs zone1970.tab roles
- [x] No checksum proved (names + offset arithmetic; theory.html defines no check system)
- [x] Abbreviation nuance: theory.html + RFC 9636 §5 + RFC 3339 §4.2 collisions (IST×3, CST×3, EST/AEST correction, MST/PST double duty)
- [x] Ecosystem regex consensus: vellum offset regex verbatim + range/sign-flip handling; pytz fold code; zoneinfo strictness; dateutil EST hole + GMT-sign gotcha; moment timestamp-abbr; stdnum absence
- [x] Recognition-surface inventory complete (§2.1): 18 forms with evidence and RECOGNIZE/DEFER/REJECT dispositions — no silently unhandled form
- [x] Wild input shapes validated (§2.2) against tzdb + CLDR + validators (18 categories + snippets table)
- [x] Label scope decision (§2.1 DEFER + §13.11)
- [x] Link/canonical equivalence decision (§4.8/§5.2/§7.2; §13.7 downgraded link-output)
- [x] Abbreviation refusal + carve decision (§7.3/§13.3/§13.4, §10–11)
- [x] Offset canonical-shape decision (split: `UtcOffset` `+HH:MM`, `Z`→`+00:00`, `-00:00`→INVALID; human-vs-POSIX semantics explicit)
- [x] Abbreviation carve rule (short-caps Links → abbreviation family → INVALID; `EST`/`CET` no longer resolve)
- [x] Evidence classes A–E + construction-guarantee carve-out (§4.7) with equivalence proofs (§4.8)
- [x] `backward` verified live (252 Links + 4 Zones; EST/MST/HST/CET/WET link lines confirmed; no IST/CST/PST/JST links)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ISSN, Country, Phone, MacAddress, and Language Capabilities Teach Timezone (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships (precedent-mining brief, 2026-09-14).

Refer to `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:69-98` (BoundaryGuard + notation strip), `paxman/capabilities/Country/grammar/name_recognition.py:33-57` (lexicon keys-only emit + trie), `paxman/capabilities/Date/grammar/date_recognition.py:82-111` (CandidatesMatcher `strategy="all"` → AMBIGUOUS), `paxman/capabilities/Language/rules/iso_639_1_ed2002.py:49-57` (DEPRECATED_MAP resolution), `paxman/core/domain.py:236-271` (six Rule attrs), `paxman/core/grammar/engine_loop.py:146-157` (suppression + A0 exemption), `docs/adr/0011-output-format-information-preservation.md:30-40` (offered-format admissibility), `docs/adr/0012-candidate-qualification.md:49-71` (provisional PARSER candidates) — see deep-dive summary in §4.2 / §5 / §6 above. The four architectural lessons for Timezone:
1. **Grammar strips, rule validates, capability formats.** Lexicon emits folded keys; LOOKUP_TABLE owns membership; `format_value` renders `iana` (v1 has no offered formats).
2. **One file per provenance, one class per section.** tzdb / RFC 3339 / abbreviation rule files with module `PUBLICATION`s.
3. **No `output_format` in rules, ever.** Offsets/abbreviations refused as outputs at the contract, not in rules.
4. **Separate semantics per family avoids spurious AMBIGUOUS; refusal beats silent picks.** Name/abbreviation ids stay disjoint (offsets in `UtcOffset`); ambiguous abbreviations go INVALID (foreign-CRS precedent), never guessed.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for Timezone. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md`. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
