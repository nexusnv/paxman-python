# IBAN Canonicalization Research — paxman-python

**Date:** 2026-08-22
**Scope:** Primary-source survey of the IBAN standard (ISO 13616-1:2020, ISO 13616-2:2020, ISO/IEC 7064:2003 MOD 97-10, SWIFT IBAN Registry), the country-specific BBAN registry mechanism, ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `IBAN` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org) for 13616-1:2020, 13616-2:2020, and 7064:2003, SWIFT IBAN Registry (swift.com) Release 100 Oct 2025 + Registration Procedures, ECBS TR 201 legacy, TCMB IBAN communique, IANA URN Namespaces, ISSN/ISBN/Country/Phone shipped Paxman capabilities as architectural precedents. Repo state: `feature/CURRENCY-capability` successor branch — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](../research/2026-08-21-issn-canonicalization.md).

---

## Executive Summary

IBAN is a strong fit for a Paxman capability: it has an unambiguous canonical form (**electronic format** — compact, no spaces, uppercase, `15–34` chars: `CCDD BBAN` where `CC` is ISO 3166-1 alpha-2, `DD` is two check digits, `BBAN` is `1–30` alphanum with **fixed length and structure per country**), a stable two-part standard (**ISO 13616-1:2020** structure + **ISO 13616-2:2020** Registration Authority + **ISO/IEC 7064:2003 MOD 97-10** check character system), a maintained authoritative registry (**SWIFT IBAN Registry**, current Release 100 Oct 2025, free PDF+TXT, appointed RA under ISO 13616-2), and a well-understood human-readable presentation (**paper format** — groups of four characters separated by spaces, last group variable — presentation-only). The domain mirrors Paxman's value proposition for ISSN/ISBN: recognizing the tolerant human surface (case, whitespace, optional `IBAN` label, paper groups), validating strictly against the authority (mod-97 + country-specific length/BBAN structure), and returning a canonical electronic value with full provenance.

Key findings that shape the design:

1. **Canonical form is electronic (compact) with no spaces, uppercase** (`DE89370400440532013000`, `GB29NWBK60161331926819`). Paper format (`DE89 3704 0044 0532 0130 00`) is readability-only, exactly like ISSN's hyphen or ISBN's Range Message hyphenation. This maps onto Paxman's presentational-only `output_format` invariant: `format_value()` renders `electronic` (default, compact) vs `paper` (groups of four) without touching validity.

2. **One grammar suffices, but length is country-dependent (15–34).** Unlike ISSN's fixed `8` chars, IBAN has **variable total length per country** (e.g. `NO15`, `DE22`, `FR27`, `MT31`, `BR29`), with the two check digits always at positions 3–4. A single `IBANRecognitionGrammar` with Regex (structural pattern matching) strategy is the correct choice — a finite country-length table is needed for strict recognition, but the grammar's job is only to find plausible `CCDD + BBAN` runs and strip/normalize them; strict country-length and BBAN-structure validation belongs to rules.

3. **Check digits are the definitive structural validation** — ISO/IEC 7064 MOD 97-10: move first 4 chars to end, convert letters `A=10 … Z=35`, compute `mod 97`; valid iff remainder `1`. Generation uses `98 − (remainder of 00-placeholder)`. This one algorithm covers all countries; no per-country check-digit variant is needed for IBAN itself (national check digits inside BBAN are a different layer, out-of-scope for generic validation).

4. **Country-specific BBAN structure is relational, not universal.** The SWIFT IBAN Registry defines per-country BBAN length (`15–34 minus 4`), BBAN structure (`!n` numeric, `!a` upper alpha, `!c` alphanum, exact positions for bank/branch identifier), IBAN length, and examples in both electronic and print formats. This is the **registry layer** — a `LOOKUP_TABLE` rule behind `requires_features` (mirrors ISBN's `include_range_validation=False` and Country's `include_localized`), with a `rules/data/` snapshot and refresh procedure; the always-active structural rule validates generic shape + mod-97 alone.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 13616-1:2020` (active, current) owns structure + electronic/paper distinction + reference to ISO 7064; `ISO/IEC 7064:2003` (active) owns MOD 97-10; `SWIFT IBAN Registry` (`kind="registry"`, Release 100 Oct 2025) owns per-country BBAN/IBAN lengths and structures; ECBS TR 201 (legacy, `superseded`) documents lineage only. No URN namespace (negative evidence: IANA lists `issn`/`isbn`/`swift`/`lei` but no `iban`).

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need IBAN canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Payments / treasury engineers** | Normalize `DE89 3704 0044 0532 0130 00` vs `de89370400440532013000` vs `IBAN DE89…` to one electronic form for deduplication, ledger keys, and SEPA/SWIFT wire validation before submission | Core banking, payment hubs, SEPA Credit Transfer / Direct Debit, SWIFT FIN/MT, treasury management systems |
| **Fintech / e-commerce onboarding** | Validate user-supplied IBAN at form ingest; reject structurally invalid vs country-mismatched vs mod-97-failed input with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | KYC flows, payout setup (marketplace sellers), beneficiary-registration, invoice parsers |
| **Data engineering / reconciliation** | Extract and canonicalize IBANs from free-text references, PDFs, emails, or scraped HTML with span-bearing provenance; join on electronic canonical key | ETL pipelines, bank-statement parsers, Open Banking aggregation, LLM extraction post-processing |
| **Risk / compliance / search teams** | Use IBAN as a stable account-work key alongside BIC/SWIFT and national account numbers; detect duplicate accounts across formatted variants | Fraud screening, AML monitoring, entity resolution, knowledge-graph account matching |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many IBAN mentions) and a contract; Paxman returns one canonical IBAN (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ISSN (`XXXX-XXXX` hyphenated default) and ISBN (`isbn13` bare digits) ergonomics, but the canonical default is **electronic** (no spaces).

---

## 2. Shape of Input (Human Surface)

### 2.1 Wild variants — enumerated from spec, SWIFT IBAN Registry, SEPA/fintech corpora, and real validators

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical electronic** | `DE89370400440532013000`, `GB29NWBK60161331926819` | Spec master form — no spaces, uppercase, full length; `format_value()` default target |
| 2 | **Canonical paper** | `DE89 3704 0044 0532 0130 00`, `GB29 NWBK 6016 1331 9268 19` | SWIFT Registry § print format: groups of four characters separated by single spaces, last group variable; presentation-only, must be recognized and collapsed |
| 3 | **Lowercase / mixed case** | `de89370400440532013000`, `gb29 nwbk 6016 1331 9268 19`, `De89 3704 0044 0532 0130 00` | Permitted characters are `0-9` + `A-Z` case-insensitive; canonical is uppercase — grammar must accept `(?i)` and normalize via `.upper()` |
| 4 | **Label with colon/space/hyphen** | `IBAN: DE89 3704 0044 0532 0130 00`, `IBAN DE89370400440532013000`, `iban: gb29nwbk60161331926819`, `IBAN - DE89…` | Many forms and exports prefix `IBAN`; examples in corpora include `IBAN:` plus paper groups; prefix handling must be case-insensitive, colon/space/hyphen tolerant; span should include label when present (`raw_text` preserves it) or exclude it and emit only the IBAN value — decision documented in §4 |
| 5 | **Irregular whitespace** | `DE89  3704    0044 0532 0130 00`, `DE89\t3704 0044`, `\nGB29 NWBK 6016 1331 9268 19\n` | Users paste with double spaces, tabs, line breaks; SWIFT Registry uses single spaces in paper examples but real input is noisy — grammar must tolerate `\s` between characters (or strip all whitespace in `notation_fn`) |
| 6 | **No spaces at all** | `DE89370400440532013000`, `FR1420041010050500013M02606` | Most API/DB field value — compact is canonical |
| 7 | **Truncated / partial paste** | `DE89 3704 0044`, `GB29 NWBK` | Incomplete IBAN — either `MISSING` (no 15+ char run) or `INVALID` (recognized prefix but mod-97/length fails) depending on grammar scope; must not silently pad |
| 8 | **Country code case edge** | `de89…`, `De89…`, `dE89…` | Same as row 3 — two-letter ISO 3166-1 alpha-2 prefix is case-insensitive on input, always uppercase canonical |
| 9 | **With bank identifier visible** | `IBAN DE89 3704 0044 0532 0130 00 (BLZ 37040044)` | Free-text often annotates bank/branch; extraction must emit one span per IBAN, not swallow `(BLZ …)` |
| 10 | **Multiple per line** | `DE89 3704 0044 0532 0130 00 / GB29 NWBK 6016 1331 9268 19`, `IBANs: DE89…, FR14…` | Payment batches, beneficiary lists, SEPA pain.001 files — free-text → 2+ matches, not one coalesced string |
| 11 | **Over-long / under-long for country** | `DE89 3704 0044 0532 0130 0` (21 chars vs DE 22), `FR14 2004 1010 0505 0001 3M02 6069` (29 vs FR 27) | Country-specific length violation — either `INVALID` (recognized but country rule rejects) or `MISSING` if grammar length guards strictly; paper groups mask the count |
| 12 | **Non-alphanum separators** | `DE89-3704-0044-0532-0130-00`, `DE89.3704.0044` | Hyphens/dots pasted from PDFs or redacted displays; SWIFT spec allows only spaces in paper format — but real copy-paste hits these; decision: recognize hyphen-minus only as separator tolerance or reject — document (§8 edge 16 analogue) |

**Real-world regex / validation snippets (GitHub / ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| `Savory/validatte` `isIBAN.ts` (and `validator.js` `isIBAN`) | `^([A-Z]{2}\d{2}[A-Z0-9]{1,30})$` + per-country length map + MOD-97 (`iban.replace(/[A-Z]/g, c=>c.charCodeAt(0)-55)` then mod97) |
| `arthurdejong/python-stdnum` `stdnum/iban.py` | `compact(number)` → strip non-alphanum, upper; `calc_check_digits` via `mod97` (piece-wise); `validate` checks country in registry, length matches, then `mod97 == 1`; BBAN structure via country registry table |
| `JohnPeel/iban` `registry.txt` (verified mirror) | Machine `registry.txt` per SWIFT: `country_code|iban_length|bban_structure|bban_regex|…` — used to build dynamic per-country regex (replaces `socialpaymentsbv/iban-structures` — GitHub 404 per Oracle) |
| `js-iban` / `ibantools` (JS) | `electronicFormat(iban) = iban.replace(/[^0-9A-Z]/ig,"").toUpperCase()`; `isValidBBAN` tests country BBAN regex before mod97 |
| `ronanguilloux/IsoCodes` `Iban.php` | `Utils::mod97(ibanRearranged)` (rearrange first 4 to end, expand letters, iterative `%97`) |
| `postgres` (no native `iban` type) | Community extension `iban` type validates via `iban_in` C with mod97 — parallels `isn` `issn_in` pattern |
| `iban.com` / `iban-calculator` validators | Pre-check: strip spaces, upper, country length lookup, BBAN charset, then MOD97 — invalid length → INVALID without mod97 |
| `zotero/utilities` analogue for ISSN | ISSN's `cleanISSN` strips `[\x2D\xAD\u2010-\u2015\u2043\u2212]` — IBAN analog is stripping `[\s]` (and optionally `[-.]`) before check |

**Normalization contract (reuse ISBN/ISSN pattern):**

```python
# SWIFT / python-stdnum pattern — strip separators, upper, then MOD-97
compact = re.sub(
    r"[^0-9A-Za-z]", "", raw
).upper()  # → 15-34 chars: [A-Z]{2}\d{2}[A-Z0-9]{1,30}
# or more narrowly: re.sub(r"[\s-]", "", raw).upper()  # spaces + hyphens only
```

### 2.2 What input is NOT an IBAN mention

- National account numbers without country prefix (BBAN alone, e.g. `370400440532013000`) — country code + check digits are structurally required; grammar must not claim a bare 18-char BBAN as IBAN.
- BIC/SWIFT codes (`DEUTDEFF`, `DEUTDEFF500`) — distinct shape (8 or 11 alphanum, 4-letter bank + 2-letter country + 2 alphanum location + optional 3 branch), different provenance (ISO 9362 / SWIFT BIC Directory).
- Credit-card / ISIN / LEI alphanum runs that accidentally contain `CCDD` at start — e.g. `US0378331005` (ISIN) looks like country `US` + `03` but is 12 chars and different registry; cross-capability guard is country-length + mod97 (IBAN-specific).
- Short alphanumeric runs (`AB12`, `DE89`) — `MISSING` vs `INVALID` boundary (see §9 Resolution map).

### 2.3 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md — segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct IBANs that normalize to different electronic values is `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` with `single_value=True` enforcement); the caller-owned segmentation path (split → canonicalize each slice) is the intended multi-entity pattern for beneficiary batches, pain.001 lists, or statement-line items with origin + destination IBANs. Identical IBAN mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact + structured decomposition

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IBANNotation:
    """IBAN notation — grammar-normalized compact form.

    ``country_code`` is the 2-letter ISO 3166-1 alpha-2 prefix, uppercased.
    ``check_digits`` is the 2-digit string at positions 3-4.
    ``bban`` is the remainder (1-30 alphanum, uppercased, spaces stripped).
    ``compact`` is the full electronic string (country_code + check_digits + bban).

    The grammar never computes or validates the check digits (mod-97);
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md §4).
    """

    country_code: str  # e.g. "DE", "GB" — always length 2, A-Z
    check_digits: str  # e.g. "89", "29" — always length 2, 0-9
    bban: str  # e.g. "370400440532013000" — 1-30 alphanum
    compact: (
        str  # e.g. "DE89370400440532013000" — 15-34, ≡ country_code+check_digits+bban
    )
```

**Considered alternative — single field `compact` only:** `MoneyNotation` style with multi-field validation in `__post_init__`, and `PhoneNotation` `value`-only shape. A single `compact` field would suffice for the generic mod-97 rule (which operates on the whole string), and country-specific BBAN structure can be derived via slicing `compact[4:]`. However the three-field decomposition is preferred because:

1. The SWIFT Registry's per-country specification indexes by `country_code` (lookup key) and describes `bban` structure/length separately from the 2 check digits — the rule table is naturally keyed by `country_code`.
2. `Phone`'s `shape` discriminator pattern (`e164`/`national`) shows the value of exposing the prefix as a typed field for rule routing; IBAN's `country_code` serves the same indexing role.
3. `ISBNNotation`'s `shape` + `digits` split proves the pattern of exposing the prefix that determines length semantics — IBAN's `country_code` determines total length and BBAN regex, so it deserves a first-class field.

The notation is therefore **isomorphic to Money/Phone per-grammar sanitized forms** and satisfies `Grammar[IBANNotation].recognize()` → `Rule[IBANNotation].matches()` typing. Every field is `str` (HOW_TO_ADD_NEW_CAPABILITY.md §3 requires all notation fields be `str`).

**Invariants the grammar enforces (before rules):**
- `country_code` is exactly 2 `A-Z` (uppercased by grammar from `[A-Za-z]`).
- `check_digits` is exactly 2 digits `0-9`.
- `bban` is `1–30` alphanum `[A-Z0-9]` (uppercased, spaces stripped).
- `compact` is `15–34` total (`4 + len(bban)`), equals `country_code + check_digits + bban`; `compact == re.sub(r"[^A-Z0-9]", "", raw_text).upper()` modulo the optional `IBAN` label stripping.
- `raw_text` preserves original span (label + spacing + case); the notation is the syntax-normalized token.

### 3.2 Why not carry paper spaces in the notation

Paper spaces have **no lexical significance** for validity (ISO 13616-1 electronic vs print format — described in Wikipedia/ECBS lineage as *"when transmitted electronically however spaces are omitted … In order to facilitate reading by humans, IBANs are traditionally expressed in groups of four characters separated by spaces"* — verbatim Wikipedia, absent from R99/R100 PDFs; Paxman adopts groups-of-four as its canonical `paper` rendering). Electronic and paper forms of the same `compact` have the same identity regardless of input spacing — dedup and status logic operate on `compact`. Presentation is `Capability.format_value()` only. *Note:* the SWIFT Registry itself lists per-country print exceptions — e.g. **EG** (`EG38…1800 02`, unspaced in the registry's own print example) and Wikipedia notes BI/LY/SV as additional unspaced-print cases; Paxman's `paper` groups-of-four is therefore a Paxman presentation choice, not a per-country print fidelity. See Oracle P2.

### 3.3 Why `country_code` is not a shape discriminator literal

ISBN uses `shape: Literal["isbn10","isbn13"]` because two lexical lengths map to distinct notations that later converge on one canonical 13-digit value. IBAN has one canonical electronic value per country, but the country set itself is `~89` values (Release 100 Oct 2025) — modeling each as a `Literal` would be brittle. Instead `country_code` is a free `str` validated by `LOOKUP_TABLE` rules against `SWIFT IBAN Registry` snapshot, mirroring `Country`'s lexicon-key pattern where the registry, not the type system, owns the vocabulary.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md §1 and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape — delimiters, fixed widths, character classes) or **Lexicon** (finite vocabulary — Country names, Currency words). IBAN has a distinctive fixed-width-per-country shape (`CCDD + 1–30 alphanum`, total `15–34`), plus optional `IBAN` label, so **Regex** is the correct strategy. No lexicon table is involved at recognition — the lexicon for valid country codes lives in the registry rule (lookup), not the grammar key set.

### 4.2 Reference pattern (adapted from ISBN/ISSN verbatim precedent)

ISBN-13 precedent (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py`):
```python
_ISBN13_PATTERN = r"\b(?:ISBN(?:-13)?[\s:-]+)?(?=((?:\d[ -]?){12}\d)(?![\d]))\1\b"
```
ISSN precedent (`docs/development/research/2026-08-21-issn-canonicalization.md` §4.2):
```python
_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]*)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN = (
    BoundaryGuard.isbn10_lead().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.digit().lookahead
)
```

**Proposed IBAN pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope string pattern — compiled by RegexStage (never inside recognize())
_IBAN_BODY = r"(?:IBAN[\s:-]*)?(?P<compact>[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})"
# 15 total = 4 + 11 minimum BBAN; 34 total = 4 + 30 maximum BBAN
# Wrapped with word-boundary guards — IBAN is [A-Z0-9] glued, so word_only prevents
# carving a valid run out of a longer token like "XDE89 3704..." or "DE89…Y"
_IBAN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _IBAN_BODY
    + BoundaryGuard.word_only().lookahead
)


def _iban_notation(match: re.Match[str]) -> IBANNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isalnum()).upper()
    # compact is now 15-34 alphanum; split structurally
    country_code = compact[0:2]
    check_digits = compact[2:4]
    bban = compact[4:]
    return IBANNotation(
        country_code=country_code, check_digits=check_digits, bban=bban, compact=compact
    )


class IBANRecognitionGrammar(PipelineGrammar[IBANNotation]):
    """IBAN recognition — CCDD + BBAN with optional IBAN label and paper spacing."""

    name = "iban_recognition"
    semantics = "iban_recognition"
    single_value = True
    pre = StandardPre[IBANNotation](empty_guard=True)
    regex = RegexStage[IBANNotation](
        pattern=_IBAN_PATTERN, notation_fn=_iban_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs ISSN/ISBN:*

- Ship as module-scope **string** pattern; `RegexStage` compiles in `paxman/core/grammar/stages.py:72` (mirrors ISBN's `_ISBN13_PATTERN = r"..."`). Do not double-compile via `re.compile(...).pattern`.
- Strip in `notation_fn` via `isalnum()` + `.upper()` (ISSN precedent `x→X` is `isalnum`+`upper` for IBAN; ISBN is digit-only).
- Minimum run guard: `(?:[ ]?[A-Z0-9]){11,30}` guarantees at least `11` BBAN chars → `15` total minimum (smallest IBAN is `NO15`); upper bound `30` BBAN → `34` total (largest per spec). Exact country length is **not** enforced in the grammar — that is the registry rule's job.
- Leading `BoundaryGuard.word_only()` (`(?<!\w)` / `(?!\w)`) blocks letter/digit-glued runs (`XDE89…`, `DE89…Y`, `IBANDE89…` without space). Shipped `ISSN/grammar/issn_recognition.py` actually uses `BoundaryGuard.word_only().lookbehind` (verified — strengthens this report's recommendation; earlier draft cited `isbn10_lead` `(?<!\d)(?<!\d[ -])` as the ISSN analogue, which is the ISBN pattern, not the shipped ISSN). IBAN's alphabet includes digits, so word-boundary is the natural analogue. Alternative is `BoundaryGuard.digit().lookahead` only if you want to block digit-tail gluing but allow letter gluing — word_only is stricter and preferred for alphanum.
- **Label handling:** `(?:IBAN[\s:-]*)?` is fused (like ISSN's `ISSN(?:-L|-H)?` and ISBN's `ISBN(?:-13)?`). The `notation_fn` maps only the `compact` group (without label), so `raw_text` includes the label+spacing when matched, but `notation.compact` is the bare IBAN. Whether `raw_text` includes the label is a design choice — either include via `m.group(0)` semantics (like ISSN) or attribute only the `compact` group; document in §8.
- **Whitespace tolerance:** `[ ]?` between BBAN alphanum characters tolerates single spaces (paper groups of four are `XXXX XXXX XXXX ...`). Multiple spaces/tabs are collapsed by `isalnum()` filtering, so `DE89  3704` still normalizes correctly, but the regex only matches single-space interleaving; a `Pre` stage that collapses `\s+` to single space would widen tolerance — document as narrow-at-grammar vs `Pre`-normalized widening (parallel to ISSN's hyphen strictness debate §13#5).
- Uses `PipelineGrammar` + `StandardPre` + `RegexStage` because that is the staged pipeline ISBN actually ships (HOW_TO_ADD_NEW_GRAMMAR.md's bare-`Grammar` recipe is the minimal teaching form; shipped grammars use `PipelineGrammar`).

**Paper/electronic as one grammar vs two:**

Like ISSN's URN variant (§4.2), the paper-space groups are a second *presentation* of the same value, not a second *meaning*. Options:

- **(Recommended) Single grammar** with `[ ]?` paper-space tolerance — minimal containment complexity (`_dedup_spans` no-op within one grammar), single `semantics` id.
- **Alternative:** Two grammars `iban_electronic_recognition` + `iban_paper_recognition` with coalesced `semantics = "iban_recognition"` (HOW_TO_ADD_NEW_GRAMMAR.md §4 option A — reuse shipped semantics id so existing ISO 13616-1 rule validates both without edit). Only introduce if you want to record provenance that the input was paper-formatted vs electronic (not needed — provenance is the authority, not the presentation).

### 4.3 Recognition pipeline contract (ARCHITECTURE.md §"Recognition Pipeline Contract")

- Grammar emits **span-bearing** `RecognitionMatch[IBANNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))` — span is the regex slice. Stages must not mutate `text` (`PipelineState` scratch only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups — two grammars agreeing on the same span are both preserved for ambiguity observation. For IBAN (single shipped grammar initially), this dedup is inert but structurally present.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

### 4.4 Guard boundaries against sibling grammars

IBAN vs sibling alphanum grammars: IBAN `15–34` vs BIC `8/11` vs ISIN `12` vs LEI `20` — length + charset + mod-97 split disambiguates most.

Concrete length discrimination table:

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| IBAN | `15–34` `[A-Z]{2}\d{2}[A-Z0-9]+` | `CC` is `A-Z`, `DD` is `\d` | `(?!\w)` prevents claiming prefix of longer alphanum; country-length rule further restricts |
| BIC | `8` or `11` `[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?` | Similar `CC` at positions 5–6 | BIC at 8/11 is shorter than any IBAN (≥15), so IBAN prefix of `DEUTDEFF` (8) cannot be mistaken for IBAN — country check + length mismatch + mod97 will reject |
| ISIN | `12` `[A-Z]{2}[A-Z0-9]{9}\d` | Also `CC` + country | ISIN `US0378331005` (12) looks like a short IBAN (`US03…`) — country registry will mark `US` length mismatch (IBAN registry has no `US` entry; US has no IBAN) → `INVALID` not `MISSING` if recognized; ideally grammar distinguishes via length range |
| LEI | `20` `[A-Z0-9]{20}` | No `CCDD` pattern | No IBAN `CCDD` at fixed 20 → not confused |

Prefix-aware IBAN detection (`IBAN` label) does not clash with sibling labels (`BIC:`, `LEI:`, `ISBN`); case-insensitive `IBAN` substring is distinct from `BIC`/`ISBN`. For an IBAN-like run `DE89…` where `DE` is a valid SWIFT Registry country (length 22), recognition should claim; where `US` is not an IBAN country (no registry entry), the generic structural grammar may still claim a `15–34` run, but the registry rule will correctly report `INVALID` (or grammar could filter non-registry countries — see §13#3).

Concrete engine check (`orchestrator:_dedup_spans`):

```python
ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
# longer wins within SAME grammar; across grammars never deduped
```

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md §1, ARCHITECTURE.md §"Community Extensions")

The new grammar declares a non-empty `semantics` string; every validating `Rule` declares `target_semantics: frozenset[str]` naming the semantics ids it validates. The engine's `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. For a single shipped IBAN grammar, the natural ids are:

- `semantics = "iban_recognition"` (identity id).

Recommendation: start with identity `iban_recognition`; the registry LOOKUP rule and the structural MOD-97 rule both target this one id, coalescing only if a second grammar (e.g. `iban_paper_recognition`) is later added — coalescing is option A in HOW_TO_ADD_NEW_GRAMMAR.md §4.

### 4.6 `single_value` — one mention per call vs batch processing

Shipped capabilities (ISBN, Country, Money, Phone) all set `single_value=True` — consistent with Paxman's "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). Payment batches, pain.001 XML, and reconciliation statements legitimately contain 2+ IBANs per document (`Origin IBAN: DE89… / Beneficiary IBAN: GB29…`; BibTeX/CSV exports), so batch extraction will want free-text mining of multiple mentions.

Recommendation: **initial `single_value=True`** (matches shipped precedent and the single-beneficiary field use-case), with a documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A separate free-text community grammar with `single_value=False` can be offered via `extra_grammars` for batch-processing callers when needed.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO** — International Organization for Standardization, Technical Committee **ISO/TC 68/SC 8** (Reference data for financial services), subcommittee SC 8 responsible for ISO 13616 series. Check-character system governed by **ISO/IEC JTC 1/SC 27** (Information security, cybersecurity and privacy protection) for ISO/IEC 7064. |
| **Registration Authority (RA)** | **SWIFT (Society for Worldwide Interbank Financial Telecommunication)** — appointed by ISO under ISO 13616-2 (designated **2006** per SWIFT Registry text; ISO catalogue shows Part 2 first edition 2007 — report hedges 2006/2007; reconfirmed 2020) as the sole Registration Authority. Responsible for receiving registration requests from National Competent Authorities (national central banks / ISO national bodies), validating them, and publishing the IBAN Registry. Address: SWIFT, Avenue Adèle 1, B-1310 La Hulpe, Belgium. |
| **Spec name** | `ISO 13616-1 — Financial services — International bank account number (IBAN) — Part 1: Structure of the IBAN` and `ISO 13616-2 — Part 2: Role and responsibilities of the Registration Authority` |
| **Current edition (Part 1)** | **ISO 13616-1:2020 (2nd ed., published 2020-09-29)** — current, `90.93 Confirmed` (reviewed 2026-01-21). 8 pages. Withdraws ISO 13616-1:2007 (published 2007-03 per ISO catalogue; earlier draft cited 2007-02-23 — hedged, withdrawn 2020-09-29). That in turn superseded the single-part ISO 13616:2003 (withdrawn 2007-02-23), which superseded ISO 13616:1997 (first edition). See lineage table below. |
| **Current edition (Part 2)** | **ISO 13616-2:2020 (2nd ed., published 2020-09 per ISO catalogue; earlier draft cited 2020-10-01 — corrected)** — current, `90.93 Confirmed`. 3 pages. Withdraws ISO 13616-2:2007. Describes RA responsibilities, registration procedures, and registry structure. |
| **Check character system** | `ISO/IEC 7064:2003 — Information technology — Security techniques — Check character systems` (Edition 1, published 2003-02, `90.93 Confirmed`, ICS 35.030). Withdraws ISO 7064:1983. Defines MOD 97-10 (pure system, modulus 97, base 10, three character sets: numeric/alphabetic/alphanum). |
| **Related / legacy** | `ECBS TR 201 / EBS 204 / SIG 203 — IBAN: International Bank Account Number` (Technical Report V3, 1998/2001) — slimmed-down ECBS fixed-length version before ISO adoption (1997). Now **superseded**; retained only as historical lineage (see §5.5). |
| **Country code reference** | `ISO 3166-1 alpha-2` — two-letter country codes referenced normatively by ISO 13616-1 for the `CC` prefix; maintained by ISO 3166 Maintenance Agency. |

**IBAN structure (ISO 13616-1:2020 §4, SWIFT IBAN Registry Introduction):**

```
CC DD  BBAN
│  │   └── 1-30 alphanumeric [A-Z0-9], fixed length per country, bank/branch identifier at fixed position/length per country
│  └────── 2 check digits (02-98; 00/01/99 never assigned), computed via MOD 97-10
└───────── 2-letter ISO 3166-1 alpha-2 country code
         Total length 15-34 (4 + 1-30), CC upper, paper spaces presentation-only.
```

- Formal charset: `[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}` compact; paper: groups of four separated by single space, last group variable (`DE89 3704 0044 0532 0130 00`), `(?i)` accepted, canonical `upper`.
- Examples from SWIFT Registry (Release 100 Oct 2025): `AD12 0001 2030 2003 5910 0100` (AD, 24), `DE89 3704 0044 0532 0130 00` (DE, 22), `GB29 NWBK 6016 1331 9268 19` (GB, 22), `FR14 2004 1010 0505 0001 3M02 606` (FR, 27).

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 68/SC 8) | `ISO 13616-1:2020` | `2020-09` (2nd ed., current) | `https://www.iso.org/standard/81090.html` | `active` — supersedes 2007 | `2020` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 13616-1:2007` | `2007-03` (1st ed., split; earlier draft 2007-02-23 — corrected per ISO catalogue) | `https://www.iso.org/standard/41031.html` | `withdrawn` 2020-09-29 | `2007` | `specification` |
| ISO (pre-split) | `ISO 13616:2003` | `2003` | `https://www.iso.org/standard/38213.html` (lifecycle link) | `withdrawn` 2007-02-23 | `2003` | `specification` |
| ISO (pre-split) | `ISO 13616:1997` | `1997` | (ISO record withdrawn — cited via SWIFT procedures doc & Wikipedia Background ref 4) | `withdrawn` | `1997` | `specification` |
| ISO (ISO/TC 68/SC 8) + SWIFT (RA) | `ISO 13616-2:2020` | `2020-09` (2nd ed., current; earlier draft 2020-10-01 — corrected) | `https://www.iso.org/standard/81091.html` | `active` — supersedes 2007 | `2020` | `specification` |
| ISO/IEC JTC 1/SC 27 | `ISO/IEC 7064:2003` | `2003-02` (1st ed., MOD 97-10) | `https://www.iso.org/standard/31531.html` | `active` (confirmed 2006-09-14) | `2003` | `specification` |
| ECBS (legacy) | `ECBS TR 201 — IBAN: International Bank Account Number` | `V3 ~2001` (orig. 1998) | (Historical — cited via SWIFT procedures doc, archived via ECBS) | `superseded` (withdrawn) | `2001` | `specification` |
| SWIFT (ISO RA) | `SWIFT IBAN Registry` | `Release 100 – Oct 2025` (rolling) | `https://www.swift.com/standards/data-standards/iban-international-bank-account-number` + PDF `https://www.swift.com/sites/default/files/files/iban-registry-100.pdf` | `active` — updated within 5 working days of valid registration | `2025` | `registry` |
| ISO 3166 MA | `ISO 3166-1 alpha-2` | (referenced normatively by 13616-1) | `https://www.iso.org/iso-3166-country-codes.html` | `active` | — | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical IBAN rule citing a withdrawn edition (e.g. ISO 13616:2003) would carry `lifecycle="withdrawn"` or `"superseded"` (cf. ISBN's `isbn_users_manual_ed2012` `superseded` lifecycle for ISBN-10). For IBAN, the initial rule is expected `active`.

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_13616_1_ed2020.py` | `authority="ISO"`, `specification_name="ISO 13616-1:2020"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/81090.html"`, `version="2020"`, `lifecycle="active"`, `publication_year=2020` | `Section 4-iban-structure` + `Section 5-iban-check-digits-via-iso7064` (structure + MOD 97-10; may be two classes or one combined — see §7) | Generic structure: total length `15–34`, charset `[A-Z0-9]`, `CC` is letters, `DD` is digits, `DD` in `02–98` (reject `00`/`01`/`99`), and mod-97 `== 1`; `normalize()` returns electronic `compact` |
| `rules/iso_7064_ed2003.py` *(optional — split or fused)* | `authority="ISO/IEC JTC 1/SC 27"`, `specification_name="ISO/IEC 7064:2003"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/31531.html"`, `version="2003"`, `lifecycle="active"`, `publication_year=2003` | `Section *-mod97-10-check-character` | MOD 97-10 algorithm itself (pure system, base 10) — if split from 13616-1 structural class, owns the `(rearrange + letter-expansion + mod97 == 1)` step |
| `rules/swift_iban_registry_ed2024.py` *(optional — gated)* | `authority="SWIFT (ISO RA)"`, `specification_name="SWIFT IBAN Registry"`, `kind="registry"`, `reference_url="https://www.swift.com/sites/default/files/files/iban-registry-100.pdf"`, `version="Release 100 – Oct 2025"`, `lifecycle="active"`, `publication_year=2025` | `Section *-iban-registry-country-bban-structure` (per-country length + BBAN regex/positions) | Whether the 6-char prefix's country is in the registry, whether total length matches country's registered IBAN length, and whether BBAN matches country's registered structure (numeric/alpha/alphanum positions); `requires_features={"include_registry_validation"}` or `{"include_country_validation"}` |
| `rules/ecbs_tr201_ed2001.py` *(not shipped — lineage only)* | `authority="ECBS"`, `specification_name="ECBS TR 201"`, `kind="specification"`, `reference_url="(historical)"`, `version="V3"`, `lifecycle="superseded"`, `publication_year=2001` | — | Historical lineage; not shipped as a rule. If a legacy compatibility rule were ever needed, it would carry `superseded` lifecycle and mirror ECBS's fixed-length assumptions. |

*This mirrors ISBN's three-authority split (ISO 2108 // ISBN Users' Manual // ISBN Range Message, each one `PUBLICATION` per file) and ISSN's single-mandatory-plus-optional split (ISO 3297:2022 // RFC 3044 // ISSN Register). For IBAN, only ISO 13616-1:2020 + ISO/IEC 7064:2003 are mandatory; the SWIFT IBAN Registry layer is optional, gated via `requires_features`, exactly like ISBN's `Section 4-registrant-range` gated by `include_range_validation` / Country's `include_localized`.*

Each `Rule[IBANNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`):

```python
class Section4IBANStructure(Rule[IBANNotation]):
    name = "Section 4-iban-structure-mod97"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4-5 (structure + MOD 97-10)"
    target_semantics = frozenset({"iban_recognition"})
    requires_features = frozenset()

    def matches(self, notation: IBANNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: IBANNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO 13616-1:2020 + 13616-2:2020** lineage confirmed via `https://www.iso.org/standard/81090.html` (current, `90.93 Confirmed`, withdraws 13616-1:2007) and `https://www.iso.org/standard/81091.html` (Part 2 current) plus withdrawn chain `https://www.iso.org/standard/41031.html`.
- **ISO/IEC 7064:2003** catalogue: `https://www.iso.org/standard/31531.html` (current, MOD 97-10, `90.93 Confirmed`, ICS 35.030, JTC 1/SC 27).
- **SWIFT as RA:** `https://www.swift.com/standards/data-standards/iban-international-bank-account-number` (landing: *"Swift publishes the ISO 13616 IBAN Registry"*) + PDF `https://www.swift.com/sites/default/files/files/iban-registry-100.pdf` (intro text: structure `CC+DD+BBAN`, bank identifier position/length per country) + Registration Procedures `https://www.swift.com/sites/default/files/files/swift_standards_guidelines_ibanregitrationprocedures-1.pdf` (RA appointed by ISO, publish within 5 working days).
- **ECBS lineage:** `https://en.wikipedia.org/wiki/International_Bank_Account_Number` Background (ISO 13616:1997 ← ECBS slimmed version, split 2007) + SWIFT procedures doc which supersedes ECBS TR 201.
- **IANA negative evidence for URN:** `https://www.iana.org/assignments/urn-namespaces/urn-namespaces.xhtml` (lists `issn`, `isbn`, `swift`, `lei` — no `iban`) + RFC 3615 (SWIFT URN namespace, not IBAN) + RFC 8141 (URN Syntax, no IBAN).

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* The SWIFT IBAN Registry is `kind="registry"` `lifecycle="active"` (rolling release); a historical ECBS rule would carry `superseded`. For IBAN, the initial mandatory rule is expected `active`.

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. The generic ISO 13616-1 / ISO/IEC 7064 rule checks: length `15–34`, charset `[A-Z0-9]`, country-code letters, check-digits in `02–98`, and `mod97(compact) == 1` (see §7). The registry rule checks: country in SWIFT Registry, total length equals country's registered IBAN length, BBAN matches country's registered structure pattern (`!n`/`!a`/`!c` positions). All return `False` for any invalid input, never raise — not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md §5b Step 7).
- **`normalize()`** — returns the **default electronic form** (`compact`, no spaces, uppercase, per `CapabilityContract.DEFAULT_OUTPUT_FORMAT`; see §6). Never reads `contract.output_format` — the CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability's `format_value()` seam only. Both the generic and the registry rule must return the **same** default string for the same valid notation — candidate dedup `(value, recognition_rule, validation_rule)` ensures agreement stays `SUCCESS`.
- **`RuleStrategy` choice:** ISBN precedent uses `PARSER` for check digits and `LOOKUP_TABLE` for registry prefixes/registrant ranges. For IBAN, the mod-97 + generic structure rule is `PARSER`; the SWIFT Registry per-country length/BBAN-structure rule is `LOOKUP_TABLE` (parallel to ISBN Range Message `LOOKUP_TABLE`).

### 5.4 Country-specific BBAN structure — scope decision

The **SWIFT IBAN Registry** defines per-country BBAN structure: fixed total IBAN length, BBAN length (`IBAN length − 4`), BBAN structure pattern (e.g. `DE: 8!n10!n` — 8 numeric + 10 numeric; `GB: 4!a6!n8!n` — 4 upper-alpha + 6 numeric + 8 numeric; `FR: 5!n5!n11!c2!n` — 5 numeric + 5 numeric + 11 alphanum + 2 numeric), bank-identifier position/length within BBAN (`position + length`), example IBANs in electronic and print formats, and national example fields. Currently **~89 countries** (Release 100 Oct 2025) have registered IBAN formats; new registrations arrive via National Competent Authorities and are published within 5 working days.

**Recommendation for an initial IBAN capability:** treat per-country BBAN structure as **out of scope for mandatory validation** — it is a **registry lookup** that requires a snapshot of the SWIFT IBAN Registry, not a deterministic string transform. Validating that a string *is structurally an IBAN* (generic length/charset/mod-97) vs that it *is a country-valid IBAN for that country's BBAN structure* are different claims; the latter requires the registry table, has staleness concerns (new countries, SEPA scope changes), and is country-count non-trivial (~89 entries with structure regexes). The initial capability should canonicalize any generic IBAN (correct length, charset, `02–98`, mod-97) to its electronic form with provenance `ISO 13616-1:2020 + ISO/IEC 7064:2003` only. Country-specific length/BBAN validation, if later desired, belongs behind an opt-in `include_registry_validation` (or `include_country_validation`) gated `LOOKUP_TABLE` rule, mirrored on ISBN `include_range_validation` and Country `include_localized` — gated, documented, and refresh-procedure-bearing. This keeps the initial surface minimal and deterministic while allowing strict country-aware validation for payments compliance callers.

Analogy: ISSN's `ISSN-L` linking and ISBN's `Range Message` registrant ranges are relational/registry properties requiring a table, not a pure mod-11 — IBAN's BBAN structure is the same class of registry-dependent property.

### 5.5 Assignment / registration authority & Registry content

Network: **SWIFT** as RA (La Hulpe, Belgium) + **National Competent Authorities** (national central banks / ISO national standards bodies) per country as registrants. Blocks: each country defines one national IBAN format (IBAN length + BBAN structure) and registers it; the **IBAN Registry** (central catalogue) is published as **PDF** (human, free download — primary authority) and **TXT** (pipe-separated, machine mirror — secondary but widely mirrored at `github.com/.../registry.txt`). Each record includes: country name + ISO 3166-1 `CC` + IBAN structure + IBAN length + BBAN structure (SWIFT `!` notation) + BBAN length + bank identifier position/length within BBAN + example bank identifier + example domestic account + example BBAN + examples of IBAN in both electronic and print formats + effective date + contact authority (central bank/payment association) + SEPA membership flag (per-country page notes).

Per **ISO 13616-2 / Registration Procedures**:

- *"The RA is the designated entity appointed by ISO that is responsible for receiving the registration requests, validating them, registering the IBAN formats and publishing them in the IBAN Registry in accordance with the requirements set out in ISO 13616."*
- *"Each time an update is received and determined as valid by the RA, a new version of the IBAN Registry is published by the RA within five working days."*
- *"IBAN data records are made publicly and freely available online … with a clear reference to the ISO 13616 standard."*

Mandatory registration data (§ When applying, items `a–k`): country name, CC, IBAN length (max 34), BBAN structure & length, bank/branch identifier position & length within BBAN, IBAN structure, effective date, example bank identifier, example domestic account number, example BBAN, examples of IBAN in both electronic and print formats; plus branch identification and SEPA flags (per PDF page).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman.core.capability_contract.py`) — never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base's `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class IBANContract(CapabilityContract):
    """User-facing contract for IBAN capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = (
        "electronic"  # cf. ISSN "hyphenated" / ISBN "isbn13"
    )
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"paper", "compact"})
    # "compact" is an alias to "electronic" — same no-space form; offer only one alternative
    # to keep OFFERED distinct from default. Prefer frozenset({"paper"}) with "electronic"
    # resolved from None/"default"/"electronic" and "compact" normalized to same value.

    capability_name: str = field(default="iban", init=False)
    # Optional registry gating (initially absent; added when SWIFT Registry rule ships):
    # include_registry_validation: bool = False
    # include_country_validation: bool = False  # alternative name
    # strict_country_validation: bool = False  # alternative stricter

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For IBAN there is one always-active grammar,
    # so the property is omitted — base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For IBAN, `electronic` (compact, no spaces) is the machine canonical form (SWIFT electronic format); `paper` is the human group-of-four rendering.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format` — `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order, then capability-specific params (if any). For IBAN initially there are no capability-specific params; `include_registry_validation` is added only when the registry rule ships.

**Presentational-only invariant (hard rule — ARCHITECTURE.md §"The Formatting Seam"):**

- `output_format` is a **representation transform, never a recognition/validation signal**. Rules never read it; `normalize()` always returns the default electronic compact form; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup / status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance** — `Candidate.provenance`, `recognition_rule`, `validation_rule` come from the validating rule.

For IBAN, the offered formats model the two interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"electronic"` (default) | `DE89370400440532013000` / `GB29NWBK60161331926819` | Compact, no spaces, uppercase — electronic transmission form (SWIFT Registry electronic format); DB key, wire payload, ledger key |
| `"paper"` | `DE89 3704 0044 0532 0130 00` / `GB29 NWBK 6016 1331 9268 19` | Groups of four characters separated by single spaces, last group variable — print/paper format for human perception and document exchange |
| `"compact"` *(alias)* | same as `electronic` | Alias for callers expecting `compact` nomenclature (if offered, maps to `"electronic"` in `resolve` or documents as synonym) |

*Do not add `with_label` format — the `IBAN` label is not part of the identifier; statement/report renderers add it. Do not add `country_specific` formatting — BBAN-internal bank-identifier grouping varies per country and is not a presentation concern for the IBAN itself.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.IBAN.notation import IBANNotation


class IBANCapability(Capability[IBANNotation]):
    name = "iban"  # lowercase identifier — what users pass to registry

    def get_grammars(self) -> list[Grammar[IBANNotation]]:
        return [
            IBANRecognitionGrammar()
        ]  # single grammar; paper/electronic handled together

    def get_rules(self) -> list[Rule[IBANNotation]]:
        return [Section4IBANStructureMOD97()]  # plus optional SWIFT Registry rule

    @staticmethod
    def create_contract(
        *,
        excluded_rules: "Sequence[str] | None" = None,
        pinned_rules: "Sequence[str] | None" = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: "Sequence[str] | None" = None,
    ) -> IBANContract:
        return IBANContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: IBANNotation
    ) -> str:
        if output_format == "paper":
            # SWIFT paper format: groups of 4, space-separated, last group variable
            return " ".join(value[i : i + 4] for i in range(0, len(value), 4))
        return value  # electronic / compact default is identity — normalize() must return compact
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`):
`scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(IBAN())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation — Check Digits, Authority, Provenance

### 7.1 MOD 97-10 (ISO/IEC 7064; ISO 13616-1 §5; ECBS TR 201 § check digits)

IBAN check digits use the **ISO/IEC 7064 MOD 97-10** pure system (single modulus, base 10) — the same family that validates ISTC/ISNI/LEI alphanum check systems, but with IBAN-specific letter expansion. Two directions — **validation** (remainder must be `1`) and **generation** (compute `98 − remainder`):

#### Validation — remainder == 1

```
Given IBAN compact string I = CCDDBBAN (e.g. DE89 3704 ... → DE89370400440532013000):

1. Check that total length is 15-34 and per-country if registry validation enabled.
   If not, the IBAN is invalid (fast reject).
2. Move the four initial characters to the end:  B = BBAN + CC + DD
   e.g. DE89 3704 0044 0532 0130 00 → 370400440532013000DE89
        GB29 NWBK 6016 1331 9268 19 → NWBK60161331926819GB29
3. Replace each letter in B with two digits, expanding the string, where
   A=10, B=11, C=12, D=13, E=14, F=15, G=16, H=17, I=18, J=19, K=20, L=21,
   M=22, N=23, O=24, P=25, Q=26, R=27, S=28, T=29, U=30, V=31, W=32, X=33,
   Y=34, Z=35.  Case-insensitive — a/A → 10.  Digits stay as one digit.
   Formally:  ord(upper) − 55  for A-Z.
   e.g. D=13, E=14, N=23, W=32, B=11, K=20  → suffix 1314 / 3223112060...
4. Interpret the expanded string N as a decimal integer and compute
   N mod 97.  (Piece-wise method for languages without arbitrary-precision —
   see below. SWIFT Registry: "calculated based on the scheme defined
   in ISO/IEC 7064 (MOD97-10)".)
   If remainder is 1, the check digit test is passed and the IBAN might be valid
   (might — per-country length/BBAN still required for full conformance).
```

**Letter conversion table (verbatim):**
`A=10 B=11 C=12 D=13 E=14 F=15 G=16 H=17 I=18 J=19 K=20 L=21 M=22 N=23 O=24 P=25 Q=26 R=27 S=28 T=29 U=30 V=31 W=32 X=33 Y=34 Z=35` — case-insensitive, both `a`/`A` → `10`. Equivalent to `ord(c.upper()) - ord('A') + 10` or `ord(c) - 55`.

**Piece-wise mod-97 computation (for languages without arbitrary-precision):**
> 1. Starting from the leftmost digit of N, construct a number using the first 9 digits and call it M.
> 2. Calculate M mod 97.
> 3. Construct a new 9-digit M by concatenating the above result (step 2) with the next 7 or 8 digits of N. If fewer than 7 digits remain but at least one, construct new M with less than 9 digits from result + remaining digits.
> 4. Repeat steps 2-3 until all digits processed. Result is N mod 97.

Equivalently (iterative): `remainder = 0; for ch in expanded: remainder = (remainder*10 + int(ch)) % 97` — handles arbitrary length without big integers.

**Generation — check digits 02-98 (preferred ECBS algorithm):**
> 1. Check total length policy correct.
> 2. Replace the two check digits by `00` (e.g. `GB00`, `DE00`).
> 3. Move the four initial characters to the end.
> 4. Replace letters with digits (`A/a=10 … Z/z=35`), expanding.
> 5. Convert to integer (ignore leading zeros).
> 6. Calculate mod-97 → remainder `r`.
> 7. Subtract remainder from `98` → `98 − r` = two check digits (pad single digit with leading `0`, e.g. `05`, `47`).

Valid check-digit range is `02–98`; `00`, `01`, `99` are **never assigned** as IBAN check digits — they will also give `mod97 == 1` when paired correctly but the standard prefers `02–98`; a validator should accept `00`/`01`/`99` that still passes `mod97 == 1` as technically mod-97-valid but note the preferred range. This mirrors ISSN's `X=10` semantics — only value `10` at position 8 maps to `X`; other positions never valid as `X`.

**Worked examples — validation (showing mod-97 == 1):**

*Example A — GB (UK, fictitious) — Wikipedia / SWIFT canonical:*
```
IBAN:       GB82 WEST 1234 5698 7654 32
Rearrange:  WEST12345698765432GB82
Convert:    3214282912345698765432161182      (W=32, E=14, S=28, T=29, G=16, B=11)
Compute:    3214282912345698765432161182 mod 97 = 1  ✓
```
Chunked piece-wise for same N:
```
M=321428291 → mod97=70
M=702345698 → mod97=29
M=297654321 → mod97=24
M=2461182   → mod97=1  → valid
```

*Example B — DE (Germany) — MILESTONE input:*
```
IBAN (electronic): DE89 3704 0044 0532 0130 00 → DE89370400440532013000
Rearrange:         370400440532013000DE89
Convert:           370400440532013000131489        (D=13, E=14, suffix 89 → 131489)
Compute:           370400440532013000131489 mod 97 = 1  ✓
```

*Example C — GB (MILESTONE input):*
```
IBAN:       GB29 NWBK 6016 1331 9268 19 → GB29NWBK60161331926819
Rearrange:  NWBK60161331926819GB29
Convert:    3223112060161331926819161129            (N=23, W=32, B=11, K=20, G=16, B=11, 29 stay)
Compute:    … mod 97 = 1  ✓  (verify via python-stdnum or iban-calc.io)
```

*Example D — TR (Turkey) — TCMB generation & validation:*
```
BBAN:       0000100100000350930001
Temp:       TR00 0000100100000350930001  (00 placeholder)
Rearrange+convert numeric → mod97 = 51 → check = 98−51 = 47
IBAN:       TR470000100100000350930001
Validation: 0000100100000350930001TR47 → numeric 0000100100000350930001292747 → mod97 = 1 ✓
```

**Case / space handling of validation:**
- Canonical: **uppercase only** (`A-Z`). SWIFT Registry, ISO 13616-1, and ISSN/IBAN precedent all prescribe uppercase.
- Input tolerance: RFC/ISO lexical equivalence — accept `a-z`/`A-Z` on input (grammar folds via `.upper()`), strip all whitespace before check, normalize to uppercase on output. Hyphen/dot tolerance is *not* part of the standard — it is ecosystem noise (§2.1 row 12).
- Only valid as part of the full `CCDD+BBAN` string; a `mod97 == 1` fragment carved from a longer token is not an IBAN — grammar word-boundary guards and country-length checks prevent it.

### 7.2 What makes an IBAN "valid" vs "country-valid" vs "issued"

- **valid IBAN (generic)** — correct total length `15–34`, charset `[A-Z0-9]`, `CC` is `A-Z`, `DD` is `02–98` (reject `00`/`01`/`99` as generation-invalid), and `mod97 == 1` per ISO 13616-1 + ISO/IEC 7064. This is the always-active `PARSER` rule — analog to ISBN's `valid` vs ISBN's `issued`, or ISSN's `valid` vs `issued`.
- **country-valid IBAN** — generic-valid *plus* `CC` is a registered country in the SWIFT IBAN Registry, total length equals that country's registered IBAN length, and BBAN matches that country's registered BBAN structure pattern (numeric/alpha/alphanum at fixed positions, including bank identifier position/length). This is the opt-in `LOOKUP_TABLE` registry rule.
- **issued IBAN** — actually allocated by a supervised institution in that country and present in that country's national account registry (live database). IBAN itself carries no de-issued/reassigned history (contrast Country's `BU`/`SU` / ISSN's reassigned history) — but a *country-valid* IBAN may still be an *unissued* account number (no bank has assigned it). Paxman does not and should not validate issued-ness against live bank databases; country-valid is the deepest deterministic layer.

Like ISBN's valid-vs-issued split (`isbnlib` valid vs Range Message allocated) and ISSN's valid-vs-issued split (mod-11 vs Register membership), IBAN should offer the strict mod-97 validation always and the country-BBAN check as an opt-in registry rule (§5.2). Embedding the Registry as `rules/data/` would mirror ISBN's `rules/data/range_message.py` snapshot pattern — deterministic and replay-safe, with a documented refresh procedure and `version` in provenance (Release 100 identifier). National check digits *inside* BBAN (per-country weighted MOD-97 variants, Luhn, etc.) are a different layer — they are country-specific, not ISO 13616-1 conformance, and must not be validated by the generic rule; they could be offered as a third opt-in layer if ever needed (§13#6).

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Leading country case variance: `de89370400440532013000` vs `DE89370400440532013000` vs `De89…` | `SUCCESS` → `DE89370400440532013000` (grammar folds, rule validates mod97) | Grammar's `notation_fn` `.upper()` — canonical always uppercase, like ISSN `x→X` / Country case folding |
| 2 | Paper spacing variations: `DE89 3704 0044 0532 0130 00` vs `DE89370400440532013000` | `SUCCESS` → same electronic canonical | Spaces presentation-only; grammar `isalnum()` collapses, dedup by electronic value |
| 3 | Multiple spaces / tabs: `DE89  3704\t0044` | `SUCCESS` → same canonical (if grammar `[ ]?` or `isalnum` collapse handles it; otherwise `MISSING` with strict `[ ]?` only) | SWIFT paper is single spaces; real paste is noisy — document narrow vs Pre-normalized widening (Oracle fix 3 analogue for ISSN) |
| 4 | IBAN label present: `IBAN: DE89 3704 0044 0532 0130 00`, `IBAN DE89370400440532013000` | `SUCCESS`, span includes label+value if fused pattern; `raw_text == text[start:end]` includes label | Optional `(?:IBAN[\s:-]*)?` prefix, `re.IGNORECASE`; `notation.compact` is label-free |
| 5 | Invalid check digits (bad mod-97): `DE89 3704 0044 0532 0130 01` (check `01` vs correct `89`) | `INVALID` (recognized, no authority validates) | `matches()` fails `mod97 == 1` — definitive structural failure; fast-reject `DD in {"00","01","99"}` is subcase |
| 6 | Wrong length for country: `DE89 3704 0044 0532 0130 0` (21 vs DE 22), `GB29 NWBK 6016 1331 9268 1` (21 vs GB 22) | Without registry rule: `INVALID` if mod97 fails or generic `15-34` passes → `SUCCESS` incorrectly; with `include_registry_validation=True`: `INVALID` when country-length rule rejects | Generic rule knows `15-34` only; country-specific length is registry rule — demonstrates valid vs country-valid split |
| 7 | Non-registry country: `US12 3456 7890 1234 5678 90` (US has no IBAN format — no registry entry) | Without registry rule: `SUCCESS` if generic `15-34` + mod97 passes (false positive); with registry rule and no `US` entry: `INVALID` | US has no IBAN registry entry; a generic-only validator would over-accept — registry rule is the country-membership gate |
| 8 | BBAN charset violation: `DE89 3704 0044 0532 013X 00` (`X` not alphanum? actually alphanum but country expects numeric-only), more explicit `DE89 3704 0044 0532 01AB 00` with `AB` where DE expects `!n` | Without registry rule: `SUCCESS` (generic alphanum passes); with registry rule: `INVALID` (BBAN structure pattern rejects letters where numeric required) | BBAN structure is per-country `!n`/`!a`/`!c` — only registry rule can reject |
| 9 | IBAN embedded in sentence: `Please transfer to IBAN DE89 3704 0044 0532 0130 00 (BIC DEUTDEFF)` | `SUCCESS` with span; `raw_text` includes `IBAN` prefix if fused, or just the IBAN body | Free-text recognition — span-bearing match, not whole-string; `\b` / `(?<!\w)` / `(?!\w)` ensures `DE89…` inside longer alphanum is not carved |
| 10 | Two distinct IBANs in one slice: `DE89… / GB29…` | `AMBIGUOUS` (two candidates, different electronic values) — or `MultipleMentionsError` with `single_value=True`; segmentation recommended (`docs/recipes/segmentation.md`) | Caller-owned segmentation for multi-beneficiary input; identical IBANs in one slice still coalesce to `SUCCESS` |
| 11 | IBAN vs BIC/ISIN/LEI confusion: `DEUTDEFF` (BIC, 8) inside `DE89 3704…` prefix | `MISSING` for IBAN on the BIC run (too short, mod97 fails); `SUCCESS` for IBAN only on correct length run | Length discrimination — IBAN ≥15 vs BIC 8/11 vs ISIN 12 vs LEI 20; `BIC: DEUTDEFF` label does not clash with `IBAN:` |
| 12 | Leading/trailing alphanum glue: `XDE89 3704…`, `DE89…Y`, `A DE89…` | `MISSING` (or `INVALID` if inner run matched but mod97 fails) | Leading `(?<!\w)` keeps an IBAN from being carved out of a longer identifier like `XDE89…` |
| 13 | IBAN as BBAN-only paste: `370400440532013000` (18-char BBAN without `CCDD`) | `MISSING` (no IBAN grammar claims BBAN-only) or `INVALID` if generic pattern somehow claims 18 alphanum as IBAN with implied `CC` | Grammar requires `CCDD` prefix; BBAN-only is not an IBAN |
| 14 | Check digits `00`/`01`/`99`: `DE00 3704…`, `DE01…`, `DE99…` | `INVALID` — never assigned per standard; generic rule should fast-reject before mod97 (preferred) or mod97 will fail for most but `00`/`01`/`99` can still give remainder 1 with specific BBANs | Generation rule states `02–98` only; cite `devtoys.pro`/`wikipedia` check-digit assignment note |
| 15 | Very short valid country (NO15): `NO93 8601 1117 947` (15 chars) | `SUCCESS` → `NO9386011117947` | Smallest IBAN; grammar minimum `11` BBAN ensures `15` total captured; paper `NO93 8601 1117 947` |
| 16 | Very long valid country (LC32, NI32 longest; MT31, SC31): `LC55 HEMM 0001 0001 0012 0012 0002 3015` (LC, 32), `NI92 BAMC 0000 0000 0000 0000 0312 3123` (NI, 32), `MT84 MALT 0110 0001 2345 MTLC AST0 01S` (MT, 31) | `SUCCESS` → compact | Longest IBANs are **32** (LC, NI per Release 100 registry — corrected from 31; spec max 34); grammar maximum `30` BBAN ensures `34` total not exceeded; must not truncate at 24 or split into two matches |
| 17 | Non-standard separators: `DE89-3704-0044-0532-0130-00`, `DE89.3704.0044` | `MISSING` in grammar (paper spaces only, hyphen-minus not allowed), unless rule has tolerant `[ -.]?` per-char — document decision: hyphens/dots are syntax noise; either pre-normalize in `Pre` or reject and document, like ISSN's Unicode dash handling | Keep minimal for v1; `StandardPre` could host `[-.]` normalization if desired — otherwise document as unsupported |
| 18 | Duplicate spaces produce correct electronic but wrong visual grouping: `DE89 37040 04405 32013 000` (irregular 5-char groups) | `SUCCESS` → electronic (groups irrelevant); paper re-render via `format_value` is always canonical groups-of-four regardless of input grouping | Paper grouping is not semantically significant — `format_value` recomposes groups deterministically |

---

## 9. Resolution-State Map (ARCHITECTURE.md §"Resolution Semantics")

| Input | Status | Why |
|-------|--------|-----|
| Valid IBAN (mod97 OK, generic length 15-34, DD 02-98) : `DE89 3704 0044 0532 0130 00` → `DE89370400440532013000`, `GB29 NWBK 6016 1331 9268 19` → `GB29NWBK60161331926819`, lowercase/irregular spacing variants, `IBAN DE89…` | `SUCCESS` → `DE89370400440532013000` (`electronic` default) | Single electronic canonical value via ISO 13616-1:2020 + ISO/IEC 7064:2003 mod97 rule |
| Valid IBAN, alternative input spacing / case / label | `SUCCESS` (same electronic) | Spaces/case/label are presentation-only; candidate dedup by electronic value |
| Invalid mod-97 / DD 00/01/99 / bad charset: `DE89 3704 0044 0532 0130 01`, `DE00…`, random `AB12 XXXX…` | `INVALID` (recognized, no authority validates) | Definitive structural failure — generic rule's `mod97 != 1` or `DD` fast-reject |
| Wrong country-length / BBAN charset for country (only with `include_registry_validation=True`): `DE` 21 chars, `FR` BBAN with letters where `!n` required, `US` no registry entry | `INVALID` when registry rule is the only length/structure authority and rejects (without registry rule: may be `SUCCESS` on generic check — valid vs country-valid split) | Authority feature gating — enabled yields `INVALID` rather than `MISSING`, like Country localized without `include_localized` or ISBN Range without `include_range_validation` |
| Bad characters / length <15 or >34: `AB12`, `DE89` short paste, `X`-glued too-short | `MISSING` (no IBAN grammar) or `INVALID` (sub-run recognized but mod97 fails) depending on grammar scope | Length-guarded grammar `15-34` + `(?!\w)` prevents partial claims; word-glued guard `(?<!\w)` prevents `XDE89…` → `DE89…` |
| No alphanum runs of length ≥15 in text | `MISSING` | No grammar recognized anything |
| Two distinct valid IBANs in one slice (e.g. `DE89… / GB29…`) | `AMBIGUOUS` / `MultipleMentionsError` with `single_value=True` (different electronic values) | Single-slice ambiguity — use segmentation |
| `US12…` / non-registry country short run (if registry grammar not requiring country membership) | `INVALID` for country-membership failure when registry rule is enabled; `SUCCESS` on generic rule alone (over-accept) | Scope decision — country-membership claimed by SWIFT Registry's registry rule, not the generic structural grammar |
| Registry-gated input (if `include_registry_validation=True` and country's BBAN structure mismatches) | `INVALID` when only the registry rule would validate country structure | Authority feature gating — enabled yields `INVALID` rather than `MISSING`, like ISBN registrant-range provenance |
| BIC/ISIN/LEI runs (`DEUTDEFF`, `US0378331005`, `5493001KJTIIGC8Y1R12`) | `MISSING` for IBAN (not an IBAN lexical form — too short or wrong `CCDD` Positions or mod97 fails) | Not an IBAN lexical form — do not parse as IBAN |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (`tools/new_capability.py` — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py IBAN --name iban \
    --authority "ISO" --spec-name "ISO 13616-1:2020" --spec-url "https://www.iso.org/standard/81090.html" \
    --publication-year 2020
```

Creates 13 files + one edit (per Step 0 checklist): `paxman/capabilities/IBAN/{notation,contract,capability,grammar/iban_recognition,rules/iso_13616_1_ed2020}` , tests stubs, and `paxman/capabilities/__init__.py` alphabetical wiring. The `TODO(scaffold)` markers then guide replacing the placeholder grammar pattern with the IBAN Regex (§4.2), renaming `Section 1-overview` to `Section 4-iban-structure-mod97` / `Section 5-mod97-check`, shaping the notation beyond placeholder `value` into `country_code`/`check_digits`/`bban`/`compact`, and adding `rules/data/` for the SWIFT registry layer.

> Note: The scaffolder's single `--spec-name` covers one provenance. After scaffolding, add the second provenance file `rules/iso_7064_ed2003.py` (MOD 97-10) manually, or fuse both citations into one `iso_13616_1_ed2020.py` file with a note referencing ISO/IEC 7064:2003 as the check algorithm authority — either pattern satisfies "one file per publication" as long as each file carries one `PUBLICATION` and one `Rule` class per section.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[IBANRecognitionGrammar()]` (single grammar handles both paper and electronic via whitespace tolerance).
- `active_grammars` omitted for initial design (base `None` → runs every shipped grammar). Only introduce if recognition becomes feature-gated (e.g. `include_paper` paper-space grammar or `include_bic` sibling grammar) — the Email/IP/ISBN pattern.
- Each grammar carries `name = "iban_recognition"` (snake_case `_recognition` suffix) and non-empty `semantics` — engine composes shipped + `extra_grammars` community extensions in order, failing fast on name collisions (`CapabilityError`) or dangling `target_semantics` (`ContractError`).

### 10.3 Cross-cutting invariants (fail review if violated)

- **No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source** — fix root cause or use scoped `per-file-ignores` (sanctioned in `pyproject.toml`).
- **No cross-capability imports** — import only from `paxman.core` (import-linter enforced). IBAN must not import Currency/Country country-code tables or Money amount regex.
- **No `output_format` token in any `paxman/capabilities/*/rules/` module** (code, comments, or docstrings) — source-scan `tests/unit/test_rule_output_format_purity.py` fails otherwise. Presentation is `Capability.format_value()` only.
- `@dataclass(frozen=True, slots=True)` for domain objects / notation; `@dataclass(frozen=True)` **without** `slots` for contracts.
- Deterministic by construction: same input + contract + library snapshot (version + registry + rule-data tables) → same canonical output; no network, clock, or environment-dependent ordering.

---

## 11. Recommended File Layout (mirrors ISSN/ISBN — §7 in ISBN research)

```
paxman/capabilities/IBAN/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── iban_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_13616_1_ed2020.py            # primary — generic structure + MOD 97-10 (fused) or split:
    ├── iso_7064_ed2003.py               # optional — pure MOD 97-10 algorithm provenance split
    └── data/                            # only if SWIFT Registry layer adopted
        └── iban_registry.py             # SWIFT IBAN Registry snapshot (LOOKUP_TABLE; Release 100 Oct 2025)
    └── swift_iban_registry_ed2024.py    # sibling to iso_13616_1 — per-country BBAN/length LOOKUP_TABLE (gated)
# Alternative fused layout (single mandatory file):
#   rules/iso_13616_1_ed2020.py           # structure + mod97 in one file (one PUBLICATION, one Rule class)
#   rules/swift_iban_registry_ed2024.py   # registry (kind="registry", requires_features={"include_registry_validation"})
```

Per-country registry data module shape (parallel to `paxman/capabilities/ISBN/rules/data/range_message.py`):

```python
# rules/data/iban_registry.py — machine-readable SWIFT Registry snapshot
# Source: https://www.swift.com/sites/default/files/files/iban-registry-100.pdf  Release 100 Oct 2025
# Generated or hand-curated; update via tools/regenerate_iban_registry_data.py if automated.

IBAN_REGISTRY: dict[str, dict[str, object]] = {
    "DE": {
        "iban_length": 22,
        "bban_structure": "8!n10!n",  # SWIFT ! notation
        "bban_regex": r"^\d{8}\d{10}$",  # derived regex for Python
        "bban_length": 18,
        "bank_position": 1,  # 1-indexed within BBAN
        "bank_length": 8,
        "example": "DE89 3704 0044 0532 0130 00",
        "electronic": "DE89370400440532013000",
    },
    "GB": {
        "iban_length": 22,
        "bban_structure": "4!a6!n8!n",
        "bban_regex": r"^[A-Z]{4}\d{6}\d{8}$",
        "bban_length": 18,
        "bank_position": 1,
        "bank_length": 4,
        "example": "GB29 NWBK 6016 1331 9268 19",
        "electronic": "GB29NWBK60161331926819",
    },
    # ... ~89 countries (AD, AE, AL, AO, AT, AZ, BA, BE, BG, BH, BI, BR, BY, CH, CR, CY, CZ, DE, DK, DO, DZ, EE, EG, ES, FI, FO, FR, GB, ... LY, MT, ... SC — full SWIFT Registry)
}
# Plus country-key completeness invariant: every SWIFT-registered CC present; non-registered CC absent (e.g. US not present).
```

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md §10 and ISSN §9)

- **Grammar tests** (`tests/capabilities/iban/test_grammar.py`): valid electronic, valid paper (single-space groups), variant inputs (lowercase, mixed case, `IBAN:` label, `IBAN-` label, `IBAN ` label, multiple spaces/tabs collapsed, no label bare IBAN), multiple matches in one text, incompatible format (BIC 8/11, ISIN 12, LEI 20, bare BBAN without CC, too-short `<15`, too-long `>34`), empty input; span invariants `len(raw_text) == end - start` and `raw_text == text[start:end]`; `name` / `semantics` checks; boundary guard negative tests (`XDE89370400440532013000` word-glued, `DE89370400440532013000Y` tail-glued, `DE89 3704…` split across groups).
- **Rule tests** (`test_rules.py`):
  - *Generic structural + MOD97 rule* (`iso_13616_1_ed2020` / `iso_7064_ed2003`): per-rule `matches()` valid/variant/invalid (`DE89 3704…` paper vs electronic, `gb29…` lowercase, `GB82 WEST…` check-positive, `GB82 WEST…` with one digit flipped, `DE00…`/`DE01…`/`DE99…` fast-reject, `DE89` short, `DE89…` too-long), `normalize()` exact electronic output (paper `DE89 3704…` → `DE89370400440532013000` including `country_code` uppercase), provenance attributes (`authority="ISO"`, `specification_name="ISO 13616-1:2020"`, `publication_year=2020`, `lifecycle="active"`), name/strategy conventions (`strategy=PARSER`), never read `output_format`; leading zeros preserved in BBAN; piece-wise mod97 vs big-int parity test.
  - *Registry LOOKUP rule* (`swift_iban_registry_ed2024`): `matches()` valid country/length/BBAN-regex triplet (`DE22 8!n10!n` passes, `FR27 5!n5!n11!c2!n` passes, `DE` with `GB` BBAN structure fails, `US` non-registered country fails lookup, `GB` BBAN with 4-digit branch length mismatch fails), `normalize()` exact same electronic string (registry rule must agree with generic rule's value — dedup invariant); `requires_features={"include_registry_validation"}` gate; `strategy=LOOKUP_TABLE`; provenance `kind="registry"` (`authority="SWIFT (ISO RA)"`, `specification_name="SWIFT IBAN Registry"`, `version="Release 100 – Oct 2025"`).
- **Capability tests** (`test_capability.py`): notation `frozen`/`hashable`/`slots` (attempt mutation raises `FrozenInstanceError`,  `hash` stable, `__slots__` present); wiring counts (`get_grammars` len 1, `get_rules` len 1 mandatory + optional registry gated count); grammar/rule name conventions (`iban_recognition`, `Section 4-…`); `format_value()` `electronic`↔`paper` round-trips (`DE89370400440532013000` ↔ `DE89 3704 0044 0532 0130 00` via group-of-four, last group variable, tested for `NO15`, `DE22`, `MT31` lengths); `create_contract` factories for default (`electronic`, no registry), `output_format="paper"`, `include_registry_validation=True` (when shipped), `extra_grammars` path.
- **Integration** (`tests/integration/test_iban_capability.py`): `MISSING`/`INVALID`/`SUCCESS`/`AMBIGUOUS` (or `MultipleMentionsError` with `single_value=True`); registry gating (`include_registry_validation` → `INVALID` for country-mismatch vs generic `SUCCESS`), `year` temporal filtering (`year=2001` excludes 2020 rule if pinned — edge case); `_clean_registry` fixture; determinism / `VersionStamp`; span-bearing `RecognitionMatch` and `Candidate.span`; paper vs electronic dedup (same electronic value from two paper spacings → `SUCCESS`, not `AMBIGUOUS`).
- **Property tests (hypothesis):** generate valid IBANs by: pick registered country `CC`, sample BBAN `bban` matching country's BBAN regex, compute `check_digits = 98 - mod97(bban+CC+"00")`, assemble `CC+check+BBAN` → must canonicalize to itself; random 15–34 alphanum strings → `INVALID` with high probability (mod97 random uniform); paper vs electronic → identical electronic canonical value; `format_value(paper) → electronic → paper` is losslessly round-trip via electronic aspivot (paper re-grouping is deterministic).
- **Consistency test (grammar/rule boundary):** every shipped recognition `semantics` is covered by at least one `Rule.target_semantics`; if registry data adopted, every shipped country's `CC` in `IBAN_REGISTRY` is covered by the registry rule's `LOOKUP_TABLE` and tested for length/structure agreement; keep grammar and rule data in separate files with a consistency test that asserts every SWIFT registry CC's `iban_length`/`bban_regex` is exercised by at least one positive and one negative vector.
- **Presentation purity:** the `output_format` source scan already applies to any new `rules/` module (`tests/unit/test_rule_output_format_purity.py`) — `swift_iban_registry_ed2024.py` and `iso_13616_1_ed2020.py` must contain no `output_format` token.
- **Real IBAN vectors (candidates; customize to Release 100 Oct 2025):**
  - Valid generic + registry: `DE89 3704 0044 0532 0130 00` (DE, 22, `8!n10!n`), `GB29 NWBK 6016 1331 9268 19` (GB, 22, `4!a6!n8!n`), `FR14 2004 1010 0505 0001 3M02 606` (FR, 27, `5!n5!n11!c2!n`), `NO93 8601 1117 947` (NO, 15, `4!n6!n1!n`), `MT84 MALT 0110 0001 2345 MTLC AST0 01S` (MT, 31, paper), `SC18 SSCB 1101 0000 0000 0000 1497 USD` (SC, 31 → `SC18SSCB11010000000000001497USD`, mod97=1 — corrected from `0149` per Oracle; see §16), `LC55 HEMM 0001 0001 0012 0012 0002 3015` (LC, 32, longest), `NI92 BAMC 0000 0000 0000 0000 0312 3123` (NI, 32, longest).
  - Lowercase/case variants: `de89 3704 0044 0532 0130 00`, `gb29 nwbk 6016 1331 9268 19`.
  - Label variants: `IBAN: DE89 3704 0044 0532 0130 00`, `iban:gb29nwbk60161331926819`.
  - Invalid mod97: `DE89 3704 0044 0532 0130 01` (check flipped), `GB29 NWBK 6016 1331 9268 18` (one digit).
  - Invalid registry: `DE88 3704 0044 0532 0130 00` (DD off), `US12 3704 0044 0532 0130 00` (US not registered), `DE89 3704 0044 0532 AB13 00` (BBAN letters where numeric required).
   - Length edges: `NO` 15 vs truncated `NO93 8601 1117 94` (14 — `MISSING`), `LC` 32 vs overlong 33, `MT` 31 vs `LC` 32 (both valid; longest is 32, spec max 34).

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | **`DEFAULT_OUTPUT_FORMAT`** — `electronic` vs `paper` vs `compact` | **`electronic` default (compact, no spaces, uppercase); `paper` offered** (`compact` as documented alias if desired) | Wikipedia/ECBS lineage phrase *"when transmitted electronically however spaces are omitted"* (absent from R99/R100 PDFs; SWIFT Registry describes electronic as compact and print as groups-of-four) — electronic is the wire/DB canonical key; Paxman `paper` groups-of-four is a canonical Paxman rendering (per-country print exceptions EG/BI/LY/SV exist — see §3.2). Either way the seam is presentational-only — decision is about defaults, not validity. |
| 2 | **Single grammar vs paper/electronic grammars** | **Single `iban_recognition` initially; handle paper spacing via `[ ]?` tolerance and `isalnum()` collapse**; defer split `iban_paper_recognition` to community extension with coalesced `semantics = "iban_recognition"` | Keeps initial surface minimal; paper spaces are not a second meaning but a second presentation of the same `compact`. Futures coalesced semantics viable (HOW_TO_ADD_NEW_GRAMMAR.md §4 option A, no rule edit). |
| 3 | **Country lenience vs strict registry** | **Ship generic structure + mod97 as always-active `PARSER`; add `SWIFT IBAN Registry` `LOOKUP_TABLE` rule behind `include_registry_validation` (or `include_country_validation`) — `False` by default** | Mirrors ISSN `include_register_validation=False` default and ISBN `include_range_validation=False` (valid vs country-valid vs issued split). Generic IBAN without registry still catches most errors via mod97; strict country compliance is opt-in for payments compliance callers. Non-registered `CC` (e.g. US) correctly becomes `SUCCESS` without registry but `INVALID` when registry gated — document. |
| 4 | **Grammar minimum/maximum length strictness** | **Grammar enforces `15–34` total (BBAN `11–30`) narrowly — country-exact length is registry rule, not grammar** | Keeps grammar cheap and country-agnostic; country-exact length varying from `15` (NO) to `31`/`34` cannot be proven without a table — belongs in rule. Grammar's `11–30` BBAN window prevents `<15` short claims and `>34` over-claims without needing per-country table at recognition. |
| 5 | **Case/space normalization in grammar vs rule** | **Grammar folds case (`isalnum` + `.upper()`) and strips all separators; rules validate upper alphanum only** | Case folding is syntax, not semantics (HOW_TO_ADD_NEW_CAPABILITY.md §4.2); same as ISSN `x→X` and ISBN hyphen stripping — grammar strips, rule validates. |
| 6 | **National BBAN check digits (per-country internal check)** | **Out of scope for initial capability; do not validate BBAN-internal check digits** | Many countries embed a national check digit inside BBAN (e.g. FR `2!n` at end is national check) — these are diverse, domestic, and not ISO 13616-1 conformance; validating them belongs to a third, explicitly country-scoped opt-in layer if ever needed. Initial capability validates only IBAN-level `DD` mod97. |
| 7 | **Single `PUBLICATION` vs split 13616-1 + 7064** | **Either is acceptable; recommend fused or split but consistent:** fused `iso_13616_1_ed2020.py` owning structure+mod97 with a docstring citation to `ISO/IEC 7064:2003` is minimal; split `iso_13616_1_ed2020.py` (structure/`02–98` range) + `iso_7064_ed2003.py` (pure mod97 algorithm) is more faithful to "one file per publication" | 7064 is a normative reference of 13616-1; fused keeps `get_rules()` at 1; split gives cleaner provenance per-file but doubles rule wiring. Both pass `Rule.__init_subclass__` — recommend fused for v1, split only if reviewers want per-publication purity. |
| 8 | **`single_value` for batch processing** | **`True` initially (shipped precedent); document segmentation recipe for multi-IBAN documents; offer `extra_grammars` free-text variant with `False` if needed for batch/ETL callers** | Consistent with ISSN/ISBN/Country; `MultipleMentionsError` is the correct signal for `DE89… / GB29…` in one slice; pain.001 batches are multi-slice by nature. |
| 9 | **Non-space separator tolerance (`-`, `.`)** | **Grammar handles ` ` (space) and `\s` only; hyphens/dots normalize in a `Pre` stage or document as unsupported** | SWIFT spec allows only spaces in paper format; `zotero` strips broader `[\x2D\xAD…]` for ISSN is a special case — IBAN has no hyphen semantic. Keep minimal for v1; a `StandardPre` could host `[-.]` normalization if demanded. |
| 10 | **`IBAN` label span inclusion** | **Include `IBAN` label in `raw_text` span (fused regex with label) — `notation.compact` is label-free; `raw_text` includes `IBAN:` prefix when present** | Mirrors ISSN `ISSN 1234-5679` and ISBN `ISBN 978…` label-in-span behavior; useful for highlighting the full mention; `format_value` ignores label. Alternative (label outside span) would complicate free-text highlighting. |

---

## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent IBAN-vs-IBAN ambiguity.** Like ISSN/ISBN, IBANs are unique by design; the mod-97 `DD` eliminates the positional ambiguity Date exhibits (`DD/MM` vs `MM/DD`). Two distinct IBANs in one slice are an authorial choice (origin vs beneficiary, batch entries), not a parsing ambiguity — segmentation is the intended path. Different paper spacings of the same electronic value are the same canonical value; formatting must not affect status.
- **IBAN vs non-IBAN country is not lexical ambiguity** — a `US12…` alphanum run that passes generic `15–34` + mod97 but is not in the SWIFT Registry is still `INVALID` when the registry rule is gated, not a competing value. Without the registry rule it would be a false-positive `SUCCESS` — valid vs country-valid is a feature-gated validity distinction, not a multi-value ambiguity.
- **IBAN vs BIC/ISIN/LEI length discrimination** prevents cross-capability ambiguity — BIC `8/11`, ISIN `12`, LEI `20`, IBAN `15–34` are disjoint enough that `CCDD+BBAN` at IBAN lengths cannot be mistaken for BIC; ISIN's `US0378331005` (12) may look like short IBAN `US03…` but ISIN lives in a different capability's grammar/contract entirely, so no single-capability ambiguity arises (cross-capability disambiguation is out-of-scope — each capability validates its own domain).
- **Paper spacing is never an ambiguity signal.** Differently-spaced or cased forms of the same electronic `compact` are the same canonical value; `output_format="paper"` merely re-groups the same `compact` deterministically — it cannot and must not decide which country's structure is "correct" (that is the registry rule's job).
- **Registry staleness is not ambiguity.** A newly-registered country (e.g. recently added to SWIFT Registry) whose IBAN length is not yet in an embedded snapshot would be `INVALID` under a stale snapshot but `SUCCESS` under a fresh one — this is determinism-by-snapshot per ARCHITECTURE.md, not ambiguity; document snapshot version (`Release 100 – Oct 2025`) in `Provenance.version`.

---

## 15. URL Reference (authoritative, fetched 2026-08-22)

| Claim | URL |
|-------|-----|
| ISO 13616-1:2020 (2nd ed., `90.93 Confirmed`, current) | <https://www.iso.org/standard/81090.html> |
| ISO 13616-1:2007 (1st ed., withdrawn 2020-09-29) | <https://www.iso.org/standard/41031.html> |
| ISO 13616:2003 (single-part predecessor, lifecycle link) | <https://www.iso.org/standard/38213.html> |
| ISO 13616-2:2020 (2nd ed., RA, current) | <https://www.iso.org/standard/81091.html> |
| ISO/IEC 7064:2003 (MOD 97-10, active) | <https://www.iso.org/standard/31531.html> |
| SWIFT IBAN Registry — landing (free PDF+TXT, RA Statement) | <https://www.swift.com/standards/data-standards/iban-international-bank-account-number> |
| SWIFT IBAN Registry — PDF (primary authority, structure intro) | <https://www.swift.com/sites/default/files/files/iban-registry-100.pdf> |
| SWIFT IBAN Registry — PDF mirror Release 99 Dec 2024 (verified R99; `iban-registry-99.pdf` at swift.com 404s) | <https://www.mobilefish.com/download/iban/IBAN_Registry.pdf> |
| SWIFT Registration Procedures (RA duties, 5 working days, mandatory items a–k) | <https://www.swift.com/sites/default/files/files/swift_standards_guidelines_ibanregitrationprocedures-1.pdf> |
| ISO 3166-1 alpha-2 (country code reference, CC in IBAN) | <https://www.iso.org/iso-3166-country-codes.html> |
| ISO/IEC 7064 OBP (official text, MOD 97-10) | <https://www.iso.org/obp/ui/#iso:std:iso-iec:7064:ed-1:v1:en> |
| ECBS lineage (ISO 13616:1997 ← ECBS slimmed version, split 2007) | <https://en.wikipedia.org/wiki/International_Bank_Account_Number> (Background, refs 4–5) |
| MOD-97 validation — Wikipedia `Validating the IBAN` (cites ECBS doc) | <https://en.wikipedia.org/wiki/International_Bank_Account_Number> (`Validating the IBAN`) |
| MOD-97 piece-wise computation (PayAdmin/Exact Software pattern) | <https://www.exactsoftware.com/docs/DocBinBlob.aspx?Download=0&Id=%7Bee5d7a17-5552-4e6f-817d-94b772c03992%7D> |
| TCMB IBAN communique (official — generation/validation appendices, TR example) | <https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB+EN/Bottom+Menu/IBAN/Communique> |
| isvalid.dev MOD-97 (with code, A=10…Z=35) | <https://isvalid.dev/check-digit-algorithms> (§3. MOD-97) |
| iban-calc.io guide (step-by-step, Algeria example) | <https://iban-calc.io/guide> |
| ibanchecker.cash / devtoys.pro (check-digit 00/01/99 never assigned) | <https://devtoys.pro/blog/iban-validation-guide> |
| IANA URN Namespaces — negative evidence (no `iban`, lists `issn`/`isbn`/`swift`/`lei`) | <https://www.iana.org/assignments/urn-namespaces/urn-namespaces.xhtml> |
| RFC 3615 — SWIFT URN namespace (not IBAN, informational) | <https://www.rfc-editor.org/rfc/rfc3615.html> |
| RFC 8141 — URN Syntax (generic, no IBAN) | <https://www.rfc-editor.org/rfc/rfc8141.html> |
| SWIFT IBAN Registry `registry.txt` mirror (machine, per-country fields) | <https://github.com/JohnPeel/iban/blob/main/registry.txt> |
| ISSN research precedent (provenance/file-layout model) | [`docs/development/research/2026-08-21-issn-canonicalization.md`](../research/2026-08-21-issn-canonicalization.md) |
| Paxman scaffolder & conventions | [`HOW_TO_ADD_NEW_CAPABILITY.md`](../../HOW_TO_ADD_NEW_CAPABILITY.md), [`HOW_TO_ADD_NEW_GRAMMAR.md`](../../HOW_TO_ADD_NEW_GRAMMAR.md), [`ARCHITECTURE.md`](../../ARCHITECTURE.md) |
| Paxman shipped IBAN-adjacent precedent (mod-97, valid vs registry, paper/electronic seam) | `paxman/capabilities/ISBN/rules/` — `iso_2108_ed2017`, `isbn_users_manual_ed2012`, `isbn_range_message_ed2026` + `paxman/capabilities/Country` registry pattern + `paxman/capabilities/ISSN` check-digit provenance |
| Ecosystem validator evidence (all fetched via GitHub/docs) | `validator.js` `isIBAN`, `Savory/validatte` `isIBAN.ts`, `arthurdejong/python-stdnum` `stdnum/iban.py`, `JohnPeel/iban` `registry.txt` (verified mirror — replaces `socialpaymentsbv/iban-structures` 404), `ronanguilloux/IsoCodes` `Iban.php`, `iban.com` |
| MILESTONE planning row (this capability) | [`docs/development/MILESTONE.md`](../MILESTONE.md) line 27 (corrected from line 15 per Oracle — row 15 is at file line 27) |

---

## 16. Evidence Completion — Resolved

This report's IBAN-specific authoritative evidence has been fetched and cited (2026-08-22):

- [x] ISO catalogue entry: **ISO 13616-1:2020 (2nd ed., 2020-09-29, current, `90.93 Confirmed`)** superseding **ISO 13616-1:2007 (withdrawn 2020-09-29)** ← **ISO 13616:2003 (withdrawn 2007-02-23)** ← **ISO 13616:1997 (first edition)**; TC 68/SC 8; RA SWIFT via ISO 13616-2; URL `https://www.iso.org/standard/81090.html`; `version="2020"` `lifecycle="active"` `publication_year=2020`; `citation` anchored to ISO 13616-1 §4-5 (structure + check digits via ISO/IEC 7064).
- [x] ISO/IEC 7064 lineage: **ISO/IEC 7064:2003 (MOD 97-10, `90.93 Confirmed`)** superseding **ISO 7064:1983 (withdrawn)**; JTC 1/SC 27; URL `https://www.iso.org/standard/31531.html`; pure system (`modulus 97, base 10`).
- [x] ISO 13616-2 RA: **ISO 13616-2:2020 (2nd ed., 2020-09 per ISO catalogue; earlier draft 2020-10-01 — corrected, current)** with SWIFT as appointed RA (designated 2006 per SWIFT Registry text; ISO catalogue shows Part 2 2007); registration procedures (receive → validate → register → publish within 5 working days); Registry structure § (CC, IBAN length, BBAN structure/length, bank position/length, electronic/print examples, effective date); URL `https://www.iso.org/standard/81091.html` + procedures PDF `https://www.swift.com/sites/default/files/files/swift_standards_guidelines_ibanregitrationprocedures-1.pdf`.
- [x] SWIFT IBAN Registry provenance: `authority="SWIFT (ISO RA)"` `specification_name="SWIFT IBAN Registry"` `kind="registry"` `reference_url="https://www.swift.com/sites/default/files/files/iban-registry-100.pdf"`; intro quote *"The IBAN structure is defined in ISO 13616-1 and consists of … CC + DD + 1–30 BBAN … bank identifier at fixed position/length per country … check digits via MOD97-10"*; `version="Release 100 – Oct 2025"` `lifecycle="active"` `publication_year=2025`; landing page `https://www.swift.com/standards/data-standards/iban-international-bank-account-number` (free PDF+TXT); mirror `https://www.mobilefish.com/download/iban/IBAN_Registry.pdf` (verified Release 99 mirror; swift.com `iban-registry-99.pdf` 404s — see P1 fix).
- [x] ECBS TR 201 lineage: `ECBS TR 201 / EBS 204 / SIG 203 — IBAN: International Bank Account Number (V3 ~2001)` — slimmed ECBS version before ISO adoption (1997), split 2007, now `superseded` by ISO 13616 + SWIFT Registry; cited via Wikipedia Background + SWIFT procedures doc.
- [x] IBAN paper vs electronic rule: Wikipedia/ECBS lineage — *"when transmitted electronically however spaces are omitted … In order to facilitate reading by humans, IBANs are traditionally expressed in groups of four characters separated by spaces, the last group being variable"* (verbatim Wikipedia, absent from R99/R100 PDFs; SWIFT Registry describes electronic as compact and shows per-country print groups, with EG print example unspaced); electronic is compact uppercase `CCDD+BBAN`, Paxman `paper` is canonical groups-of-four (presentational-only; per-country exceptions BI/LY/SV documented); both refer to same identity.
- [x] IBAN mod-97 algorithm: move first 4 to end, expand letters `A=10…Z=35` (`ord-55`), compute `mod 97`; valid iff `1` (validation) or generate via `98 − remainder` (preferred ECBS algorithm, `02–98` preferred range, `00/01/99` never assigned); piece-wise 9-digit chunk method; worked examples `GB82 WEST…`, `DE89…`, `TR47…` (TCMB), `DZ75…` (Algeria) verified; URLs Wikipedia `Validating the IBAN`, Exact Software, TCMB, isvalid.dev, iban-calc.io.
- [x] IBAN structure: total `15–34`, `[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}`, `CC` is ISO 3166-1 alpha-2, `DD` is `02–98` via MOD 97-10, `BBAN` `1–30` fixed length per country; SWIFT Registry per-country examples (`AD24`, `DE22`, `GB22`, `FR27`, `NO15`, `MT31`, `SC31`, `LC32`, `NI32`) and BBAN structure `!n`/`!a`/`!c` verified via `registry.txt` mirror (JohnPeel/iban); smallest `NO15`, largest `LC32/NI32` (corrected from `SC31/MT31` per Oracle — both 31 are valid but not maximal) / spec max `34`.
- [x] Wild input shapes validated (§2.1) against ISO 13616-1 / SWIFT Registry Registry pages / SEPA/payment corpora / validators (`validator.js`/`validatte`/`python-stdnum`/`JohnPeel/iban`) and grammar label pattern extended to `IBAN[\s:-]*` case-insensitive plus `[ ]?` paper-space tolerance and `(?<!\w)`/`(?!\w)` word guards.
- [x] `IBAN` label scope decision (§4.2 / §8 edge 4 / §13 decision 10): label is presentation-only, fused via `(?:IBAN[\s:-]*)?` into single regex; label outside `notation.compact`, inside `raw_text` span when present; case-insensitive `IBAN`; not a separate semantics (contrast ISSN's URN alternative — IBAN has no URN per negative IANA evidence).
- [x] IANA URN negative evidence: **no `iban` namespace** in IANA URN registry (`issn`, `isbn`, `swift`, `lei`, `isni` present, `iban` absent) + `RFC 3615` (SWIFT URN, not IBAN) + `RFC 8141` (generic URN syntax) — cited as negative evidence.

File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN/ISSN Capabilities Teach IBAN (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the IBAN proposal to what Paxman already ships.

Refer to `paxman/capabilities/ISBN/` and `paxman/capabilities/ISSN` design notes — see deep-dive summary in §4.2 / §5 / §6 above and the explore-verified notation/grammar/rule excerpts. The four architectural lessons for IBAN:

1. **Grammar strips, rule validates, capability formats.** ISBN grammars compile at module scope, `RegexStage` → `re.finditer()` → strip `[ -]` and label → bare notation; ISSN grammar strips `-`/space + `ISSN` label and folds `x→X`; rules enforce mod-10/mod-11/weighted sums (`PARSER` + `LOOKUP_TABLE`); `format_value` reintroduces presentation (ISBN Range Message hyphenation via longest-match; ISSN `value.replace("-", "")` for compact). **IBAN mirrors this exact split** — grammar tolerant (case, paper spaces, `IBAN` label) → `IBANNotation(country_code, check_digits, bban, compact)` + `compact.upper()`; rule `PARSER` mod-97 (`rearrange + A=10…Z=35 + mod97 == 1`) + `LOOKUP_TABLE` for per-country length/BBAN structure; formatter `paper` is a trivial `group-of-four` reinsertion (`" ".join(compact[i:i+4] for i in range(0, len(compact), 4))`).

2. **One file per provenance, one class per section.** ISBN ships `iso_2108_ed2017` (PARSER check-digit + LOOKUP_TABLE for GS1 prefix), `isbn_users_manual_ed2012` (PARSER mod-11, `X=10`, `lifecycle superseded`), `isbn_range_message_ed2026` (`LOOKUP_TABLE` registrant ranges, `requires_features={"include_range_validation"}`). ISSN's mandatory file is `iso_3297_ed2022` with `PARSER` check-digit (`lifecycle active`); any registry layer is a second file `issn_register_ed2025` gated by `requires_features={"include_register_validation"}`. **IBAN's mandatory file is `iso_13616_1_ed2020` (or fused with `iso_7064_ed2003` MOD 97-10) with `PARSER` mod97 (`lifecycle active`); any SWIFT registry layer is a second file `swift_iban_registry_ed2024` (`kind registry`, `lifecycle active`, `requires_features={"include_registry_validation"}`) with `rules/data/iban_registry.py` snapshot.**

3. **No `output_format` in rules, ever.** CI scan `tests/unit/test_rule_output_format_purity.py` rejects the token in `paxman/capabilities/*/rules/` (code, comments, docstrings). `normalize()` returns the default electronic form (`compact`); `format_value` renders `paper`. This presentational-only invariant is non-negotiable for IBAN as well — the registry LOOKUP rule must also return electronic `compact`, not paper groups.

4. **Valid vs country-valid vs issued — gated like ISBN range / Country localized.** ISBN `valid` (check-digit) vs `allocated` (Range Message); ISSN `valid` (mod-11) vs `issued` (Register); Country `valid` (ISO 3166-1) vs `localized` (CLDR); Phone `valid` (E.164 generic) vs `national` with `default_country`. **IBAN's `valid` (generic `15–34` + charset + `02–98` + mod97) vs `country-valid` (SWIFT Registry length + BBAN `!n`/`!a`/`!c`) is the same gated split — the generic rule always runs, the registry rule runs only when `include_registry_validation=True`, and the candidate set stays deterministic. Stale registry snapshots are determinism-by-snapshot (§14), not ambiguity.**

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for IBAN. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-21-issn-canonicalization.md` and the deeper ISBN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*
