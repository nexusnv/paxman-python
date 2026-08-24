# ISIN Canonicalization Research — paxman-python

**Date:** 2026-08-24
**Scope:** Primary-source survey of the ISIN standard (ISO 6166:2021, ANNA Registration Authority and ISIN Guidelines, ISO 3166-1 country-code handling, national numbering agencies and NSIN carriers), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `ISIN` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue and news pages (iso.org `standard/78502.html`, `news/ref2616.html`, ISO/TC 68 "What is ISIN" PDF), national standards-body mirrors (BSI Knowledge, Serbian ISS RS, Genorma, SIS, Standard Norge) for edition/lifecycle corroboration, ANNA identifiers page and ISIN Guidelines PDFs (Dec 2025 Amendment, June 2023 v21), isin.org education/about/convert pages, Wikipedia ISIN article (secondary, worked examples), and eight ecosystem validators fetched verbatim (python-stdnum `stdnum/isin.py`, validator.js `isISIN.js`, Apache Commons Validator `ISINValidator.java` + `ISINCheckDigit.java`, Symfony `Isin.php` + `IsinValidator.php`, floydspace/isin-validator, JonaMX/js-isin-validator, djmarland/isin, moshejs/instrument-identifiers, plus isvalid.dev docs). Shipped Paxman capabilities (ISBN, ISSN, IBAN, BIC, ORCID, Country, Phone) as architectural precedents. Repo state: `main` @ `09a8709` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](2026-08-21-issn-canonicalization.md) plus the IBAN precedent [`docs/development/research/2026-08-22-iban-canonicalization.md`](2026-08-22-iban-canonicalization.md) and BIC/ORCID precedents [`docs/development/research/2026-08-23-bic-canonicalization.md`](2026-08-23-bic-canonicalization.md) / [`docs/development/research/2026-08-23-orcid-canonicalization.md`](2026-08-23-orcid-canonicalization.md).

---

## Executive Summary

ISIN is a strong fit for a Paxman capability: it has an unambiguous canonical form (**compact, uppercase, exactly 12 chars**: `CC + NSIN + C` where `CC` is a 2-letter prefix (ISO 3166-1 alpha-2 or a special ANNA/DSB prefix), `NSIN` is 9 alphanumeric characters zero-padded from the national number, and `C` is one numeric check digit computed by the modulus 10 **Double-Add-Double** (Luhn) formula), a stable single-part standard (**ISO 6166:2021**, 8th edition, published 2021-02, `90.20` under periodical review, publisher **ISO/TC 68/SC 8** Reference data for financial services, cancels ISO 6166:2013, ICS 03.060) with **ANNA (Association of National Numbering Agencies)** as ISO Registration Authority operating through a federated model of **~116 National Numbering Agencies across 220+ jurisdictions** plus the **Derivatives Service Bureau (DSB)** as single global NNA for OTC derivatives, a maintained authoritative registry layer (**ANNA Service Bureau** — single-point access to ISIN/CFI/FISN, free ISIN Lookup Service; ISIN Guidelines current as of the December 2025 amendment), and a well-understood human-readable presentation (**space-grouped display** `US 037833 100 5`, presentation-only). The domain mirrors Paxman's value proposition for IBAN/BIC/ISSN: recognizing the tolerant human surface (case, whitespace, optional `ISIN` label), validating strictly against the authority (structure + letter-expanded Luhn + country/prefix membership), and returning a canonical compact value with full provenance. Unlike BIC, ISIN has a real checksum (modulus 10 over the letter-expanded digit string, `A=10…Z=35`); unlike IBAN's MOD 97-10, it is a single decimal check digit with a documented weakness against adjacent letter transposition.

Key findings that shape the design:

1. **Canonical form is compact, uppercase, exactly 12 chars** (`US0378331005`, `AU0000XVGZA3`, `GB0002634946`). Regex consensus across all eight ecosystem validators is `^[A-Z]{2}[A-Z0-9]{9}[0-9]$` — 12 only, never 11 or 13, check digit strictly numeric (no letter `X` analogue). Space-grouped display (`US 037833 100 5`) is readability-only. This maps onto Paxman's presentational-only invariant: `format_value()` renders `isin` (compact, default) vs `grouped` (2+6+3+1 spaces) without touching validity.

2. **One grammar suffices.** Unlike ISBN (two lexical lengths → two grammars with `include_isbn10` gating), ISIN has one lexical length (12). A single `ISINRecognitionGrammar` with Regex (structural pattern matching) strategy is correct: optional fused `ISIN` label (`[\s:-]+`, never zero-width, IBAN/BIC precedent), contiguous alternative plus single-space-tolerant alternative, `BoundaryGuard.word_only()` on both sides, and a BIC-style glued-label negative lookahead so `ISINUS0378331005` yields `MISSING` instead of a false-positive carve.

3. **Validation is two-level, both mandatory, cleanly split by authority.** Level 1: generic structure + letter-expanded Luhn (`PARSER`, publication `ISO 6166:2021`). Level 2: country/prefix membership (`LOOKUP_TABLE`, always-active per the BIC §5.4 precedent — cheap set membership, high correctness value): ISO 3166-1 alpha-2 **plus special prefixes** attested across validators and the RA corpus — `EU`, `XS` (international), `EZ`/`ZZ` (OTC derivatives, named in the 2021 edition's own change log), `XT` (digital tokens, DTIF/ISO 24165), `XA–XD`, `XF` (substitute agencies), `QS`/`QT` (Euroclear France / Switzerland internal), `XK` (Kosovo). No per-country length table (contrast IBAN), no registrant-range (contrast ISBN), no directory liveness for initial `SUCCESS`.

4. **Same-value surface collapses; identity is the compact string.** Lowercase, inner/outer whitespace, labels, and grouped spacing are presentations of one value — dedup operates on `compact`. Hyphen-separated input (`US-037833100-5`) has **zero code-level ecosystem tolerance** (documentary recommendation only) → `MISSING` in v1, DEFER to community extension. The transposed-letter checksum flaw (`AU0000XVGZA3` ↔ `AU0000VXGZA3` both validate) is a property of the modulus-10 algorithm, not a recognition/validation concern — documented, never corrected.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 6166:2021` (`active`) owns structure + check-digit annex; `ANNA ISIN Guidelines` (`kind="policy"`, December 2025 amendment) owns the country + special-prefix vocabulary; an ANNA Service Bureau / ISIN Lookup Service liveness layer (`kind="registry"`) is explicitly deferred behind `requires_features` if ever wanted.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need ISIN canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Post-trade / settlement engineers** | Normalize `us0378331005` vs `US 037833 100 5` vs `ISIN: US0378331005` to one compact key for clearing, reporting, and settlement message construction (ISO 20022 `FinInstrmId`, SWIFT MT535/536/537 holdings) | Custody systems, CSD interfaces, corporate-actions processing, reconciliation engines |
| **Regulatory-reporting / compliance teams** | Validate user-supplied ISINs at ingest for MiFID II / SFTR / EMIR / Solvency II filings; reject structurally invalid vs checksum-failed vs unknown-prefix input with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | Transaction reporting (ARM/APA), EMIR ref-data, Solvency II XBRL (EIOPA filing rules require ISIN), SEC/NMS |
| **Data engineering / reference-data pipelines** | Extract and canonicalize ISINs from free-text research notes, PDFs, prospectuses, or scraped HTML with span-bearing provenance; join on compact canonical key across vendor feeds | ETL pipelines, market-data vendor normalization (Refinitiv/Bloomberg mapping tables), LLM extraction post-processing |
| **Quant / portfolio & risk platforms** | Use ISIN as the stable instrument key alongside CUSIP (US 9-char subset), SEDOL, WKN, ticker, FIGI; detect duplicate instruments across formatted variants | Portfolio accounting, risk aggregation, fund NAV systems, index construction |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many ISIN mentions) and a contract; Paxman returns one canonical ISIN (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors IBAN (`electronic` compact default) and BIC (`bic` compact default) ergonomics, but the canonical default is **compact 12** (no spaces, uppercase, check digit as given — never recomputed into the output).

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

Attested written representations of one ISIN value, from the spec/RA corpus, ecosystem validator strip logic (removed separators are direct evidence of wild forms), and real corpora:

| Form | Example (Apple Inc.) | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|----------------------|----------------|------------|--------------------|-------------------|
| Canonical compact | `US0378331005` | ISO 6166 structure (via ANNA identifiers page); all 8 validators' regexes enclose exactly this | canonical (spec master) | **RECOGNIZE** | main pattern body |
| Lowercase | `us0378331005` | python-stdnum `.upper()`; Symfony `strtoupper`; djmarland/moshejs/JonaMX `toUpper` wrappers; isvalid.dev | common (user paste) | **RECOGNIZE** | `re.IGNORECASE` + `notation_fn` `.upper()` |
| Outer whitespace | `"  US0378331005\n"` | python-stdnum `strip()`; djmarland `trim()`; moshejs `trim()` | common | **RECOGNIZE** | `word_only` guards tolerate boundary whitespace; engine span excludes it |
| Inner-space grouped (any grouping) | `US 037833 100 5`, `US037833 1005`, `PL0000 503135` | python-stdnum `clean(number,' ')` removes ALL spaces; isvalid.dev Python `replace(" ","")` + Node `replace(/\s/g,'')`; Wikipedia/isin.org walkthroughs render spaced groups | common in prose/PDF | **RECOGNIZE** | single-space-tolerant body `(?: ?[A-Z0-9]){9} ?[0-9]` |
| Label-prefixed prose | `ISIN: US0378331005`, `ISIN US0378331005`, `isin - us0378331005` | Prospectuses, research notes, vendor exports; label convention parallel to shipped `IBAN:`/`BIC:`/`ORCID:` precedents | common | **RECOGNIZE** | fused optional `(?:(?ai:ISIN)[\s:-]+)?` label |
| Glued label without separator | `ISINUS0378331005` | No validator tolerates; BIC shipped precedent blocks glued label via negative lookahead | rare (typo) | **REJECT** (→ `MISSING`) | BIC-style glued-label negative lookahead, fired only when the suffix after `ISIN` is itself a complete valid shape (protects genuine `IS…` Iceland codes) |
| Hyphen-grouped | `US-037833100-5` | Documentary recommendation only (isvalid.dev guides say strip hyphens); **zero code-level tolerance in any of the 8 validators** (python-stdnum `clean(...,' ')` strips spaces only; `-` fails its alphabet check) | occasional | **DEFER** (→ `MISSING` in v1) | none in v1; community `extra_grammars` Pre-stage candidate (Open Decision §13#9) |
| Quoted / bracketed | `"US0378331005"`, `[GB0002634946]` | Scraped JSON/BibTeX fragments; punctuation is non-word so guards hold | common | **RECOGNIZE** | `BoundaryGuard.word_only()` transparent to non-word delimiters |
| Embedded in sentence with annotation | `Apple ISIN US0378331005 (NASDAQ: AAPL)` | Free-text extraction target; parenthetical must not be swallowed | common | **RECOGNIZE** | span-bearing match; fixed 12-char bound prevents absorption |

No other written form is attested: ISIN has no resolver URI convention (unlike DOI/ORCID), no URN namespace (negative evidence: IANA urn-namespaces lists `issn`/`isbn`/`swift`/`lei`, not `isin`), no per-country print exception (unlike IBAN EG/BI/LY/SV), and no check-character letter analogue (unlike ISSN/ISBN-10/ORCID `X` — the ISIN check digit is strictly numeric per all eight validators' final `[0-9]`).

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical compact** | `US0378331005`, `AU0000XVGZA3`, `GB0002634946` | Spec master form — 12 chars, uppercase; `format_value()` default target |
| 2 | **Lowercase / mixed case** | `us0378331005`, `Us0378331005`, `gb0002634946` | Permitted chars case-insensitive; canonical uppercase — grammar `(?ai:)` + `IGNORECASE` + `.upper()` |
| 3 | **Inner-space grouped** | `US 037833 100 5`, `PL0000 503135`, `US037833 1005` | Attested by python-stdnum + isvalid.dev strip logic; single-space tolerance collapsed in `notation_fn` |
| 4 | **Irregular whitespace** | `US  037833 100 5`, tabs/newlines inside the run | Only *single* spaces interleaved in-pattern; multi-space runs break the 12-char window → `MISSING` (Pre-collapse widening documented §13#5) |
| 5 | **Label with colon/space/hyphen** | `ISIN: US0378331005`, `isin-US0378331005`, `ISIN - US0378331005` | Case-insensitive label, `[\s:-]+` one-or-more never zero-width (glued fusion blocked, ISBN-13/IBAN/BIC precedent); `raw_text` includes label, `notation.compact` does not |
| 6 | **Glued label** | `ISINUS0378331005` | Negative lookahead fires when suffix after literal `ISIN` is a complete valid shape → no claim → `MISSING`; genuine Iceland `IS…` codes unaffected (suffix after `ISIN` there starts with a digit, not `[A-Z]{2}`) |
| 7 | **Over-long / under-long** | `US03783310055` (13), `US037833100` (11), `US037833100X` (letter check) | Exactly 12 enforced by pattern quantifier + trailing `word_only`; letter check digit impossible (`[0-9]` consensus across all validators) |
| 8 | **X-glued runs** | `XUS0378331005`, `US0378331005Y`, `AUS0378331005B` | `BoundaryGuard.word_only()` both sides — no carving out of longer alphanum tokens |
| 9 | **Invalid checksum** | `US0378331003` (should end 5; stdnum doctest raises `InvalidChecksum`) | Grammar claims (shape ok), rule rejects via Luhn → `INVALID` |
| 10 | **Invalid country/prefix** | `ZZ0378331005`, `XX0000XVGZA3` | Shape-valid; country/prefix rule rejects → `INVALID` (with rule active) vs false `SUCCESS` if excluded (§14) |
| 11 | **Special prefixes** | `XS0931417178` (international clearing), `EZ…`/`ZZ…` OTC derivatives, `QS`/`QT` agency-internal, `XT…` digital tokens | Prefix set beyond ISO 3166-1 must be accepted; membership rule owns the union set |
| 12 | **Transposed-letter flaw** | `AU0000VXGZA3` vs `AU0000XVGZA3` | Both pass Luhn (parity-preserving adjacent letter swap, Wikipedia "Check-digit flaw" section) — algorithm limitation, documented; both resolve to themselves, never corrected |
| 13 | **OCR / homoglyphs** | `USO378331005` (letter O for zero), fullwidth `ＵＳ…` | Strict ASCII `(?ai:)` charset; no autocorrection → `MISSING` (not claimed) |
| 14 | **Hyphen separators** | `US-037833100-5` | Zero ecosystem code tolerance → `MISSING` in v1 (DEFER, §13#9) |
| 15 | **Multiple per line** | `US0378331005 / GB0002634946`, `ISINs: XS0931417178, FR0000120271` | Free-text → 2+ span-bearing matches; single-slice resolution semantics apply (§2.4) |
| 16 | **Trailing annotation** | `US0378331005 (CUSIP 037833100)` | Fixed-length body + `(?!\w)` stops before `(`; CUSIP in parens is 9 chars — never claimed |
| 17 | **Quoted / bracketed** | `"US0378331005"`, `(GB0002634946)` | Non-word delimiters transparent to `word_only` guards |
| 18 | **Sibling-shaped runs** | CUSIP `037833100` (9), WKN `BAY41N` (6), SEDOL `B0YBJL7` (7), LEI `5493001KJTIIGC8Y1R12` (20) | Length discrimination: none is 12 with `[A-Z]{2}` head + numeric tail; LEI 20-char runs cannot yield an inner 12-carve due to guards |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Consensus regex (all 8 validators) | `^[A-Z]{2}[0-9A-Z]{9}[0-9]$` — 2 letters + 9 alnum + 1 numeric check = 12 |
| `arthurdejong/python-stdnum` `stdnum/isin.py` | No regex: `_alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'` membership + `len==12` else `InvalidLength` + `number[:2] in _country_codes` (ISO 3166-1 ≈242 entries + `{EU, QS, QT, XA, XB, XC, XD, XF, XK, XS}`) else `InvalidComponent` + `calc_check_digit(number[:-1]) != number[-1]` else `InvalidChecksum`. `compact(): return clean(number, ' ').strip().upper()` — strips ASCII spaces only. Check: expand via `_alphabet.index` (`A=10…Z=35`), reverse, multiply alternating `(2,1)[i%2]`, sum digits, `(10 - sum) % 10` |
| `validator.js` `src/lib/isISIN.js` | `/^[A-Z]{2}[0-9A-Z]{9}[0-9]$/` — **no preprocessing whatsoever** (strict canonical only). Backward pass from `str.length-2`: letters `charCodeAt(0)-55` split into lo/hi digits, `double` toggling, `digit>=5 → 1+(digit-5)*2 else digit*2`; final `check = trunc((sum+9)/10)*10 - sum` compared against last char |
| `apache/commons-validator` `ISINValidator.java` + `ISINCheckDigit.java` | `ISIN_REGEX = "([A-Z]{2}[A-Z0-9]{9}[0-9])"` via `CodeValidator(..., 12, ISIN_CHECK_DIGIT)`; `Character.getNumericValue` (`A=10…Z=35`), `POSITION_WEIGHT={2,1}`, `weightedValue = sumDigits(charValue * weight)`; optional country check `getInstance(true)` over `Locale.getISOCountries()` + `SPECIALS[]` (incl. `QS`,`QT`,`XA–XK`,`XS` plus retired `CS,YU,SU`) via binary search |
| Symfony `Isin.php` + `IsinValidator.php` | `VALIDATION_LENGTH = 12`; `VALIDATION_PATTERN = '/[A-Z]{2}[A-Z0-9]{9}[0-9]{1}/'`; `strtoupper($value)` only; letters via `intval($char, 36)` then delegates the expanded string to Symfony's shared `Luhn` validator |
| `floydspace/isin-validator` `src/index.ts` | Length `!==12` error; explicit letter table `'A'→[1,0] … 'Z'→[3,5]` pushed as two digits; weights `i%2===0?2:1` reversed over the expanded array; `crossSum += calcCrossSum(nums[i]*weights[i])` (`calcCrossSum` sums decimal digits); `diff=10-(crossSum%10)`, `diff===10 → 0`. Country: `PSEUDO_COUNTRY_CODES={XS,XA,XB,XC,XD,XF,QS,QT,QW,EU}` + `i18n-iso-countries` lookup |
| `JonaMX/js-isin-validator` `lib/index.js` | `/^([a-zA-Z]{2})((?![a-zA-Z]{10}\b)[a-zA-Z0-9]{9})([0-9])$/` (negative lookahead rejects all-letter NSIN) wrapped with `R.toUpper` so lowercase tolerated; expansion `charCode > 57 ? charCode-55 : charCode`; reverse, double even indices, sum, `(10-(sum%10))%10` |
| `djmarland/isin` PHP `Validator.php` | `strtoupper(trim($input))` then length==12 + `/[A-Z]{2}[A-Z0-9]{9}[0-9]{1}/`; parity-based doubling: `$p=count(numbers)%2` then alternate `num*=2; num=array_sum(str_split(num))`; `(10-($sum%10))%10` |
| `moshejs/instrument-identifiers` `src/index.ts` | `norm(value)=value.trim().toUpperCase()`; `charValue`: `48–57→code-48`, `65–90→code-55`; `isinLuhnSum` expands letters into two digits then doubles from rightmost (`i%2===0` over reversed index), digit-sum each product; `isinCheckDigit=(10-(sum%10))%10` |
| `isvalid.dev` docs (Python/Node guides) | `re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')` / JS equivalent + `replace(/\s/g,'').toUpperCase()` preprocessing (explicit inner-whitespace tolerance, e.g. `PL0000 503135` passes); documents `XT` prefix for digital tokens (`XTV15WLZJMF0`) |

**Normalization contract (reuse ISBN/IBAN pattern):**

```python
# python-stdnum pattern — strip whitespace, upper, then structure + Luhn
compact = "".join(ch for ch in raw if ch.isascii() and ch.isalnum()).upper()
# → exactly 12 chars matching [A-Z]{2}[A-Z0-9]{9}[0-9]
# hyphens intentionally NOT stripped in v1 (zero code-level ecosystem tolerance)
```

### 2.3 What input is NOT an ISIN mention

- CUSIP alone (`037833100`, 9 chars) — the NSIN carrier without `CC` prefix and check digit; grammar requires the full 12-char shape.
- WKN (`BAY41N`, 6), SEDOL (`B0YBJL7`, 7), VALOR — other national identifiers; none is 12 chars.
- LEI (`5493001KJTIIGC8Y1R12`, 20) — longer; word-boundary guards prevent inner carving.
- IBAN (`DE89370400440532013000`, 15–34) — starts `CCDD` with digits at positions 3–4; ISIN's position 12 must be a digit but positions 3–4 are free alnum; lengths are disjoint anyway (12 vs ≥15).
- BIC (`DEUTDEFF`, 8/11) — shorter than 12.
- Bare 11-char payloads (`US037833100` — the check-digit-less body used in calculators) — `MISSING`; the grammar requires the terminal digit.
- Short alphanum runs — `MISSING` vs `INVALID` boundary (see §9).

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct ISINs that normalize to different compact values is `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` under `single_value=True` enforcement, `orchestrator.py:_enforce_single_value_invariant`); the caller-owned segmentation path (split → canonicalize each slice) is the intended multi-entity pattern for portfolio holdings, index constituent lists, or statement lines with multiple instruments. Identical ISIN mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact plus structured decomposition

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISINNotation:
    """ISIN notation — grammar-normalized compact form.

    ``country_code`` is the 2-letter prefix, uppercased (ISO 3166-1 alpha-2 or
    a special ANNA/DSB prefix such as XS/EU/EZ/ZZ/XT).
    ``nsin`` is the 9-character alphanumeric national security identifier,
    uppercased, leading zeros preserved.
    ``check_digit`` is the single numeric check character at position 12.
    ``compact`` is the full 12-char string, ≡ country_code + nsin + check_digit.

    The grammar never computes or validates the Luhn check digit and never
    validates prefix membership; rules own both
    (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    """

    country_code: str  # e.g. "US", "XS", "EZ" — always length 2, A-Z
    nsin: str          # e.g. "037833100" — always length 9, A-Z0-9
    check_digit: str   # e.g. "5" — always length 1, 0-9
    compact: str       # e.g. "US0378331005" — exactly 12, equals cc+nsin+check
```

**Considered alternative — single field `compact` only:** `ISSNNotation` `digits`-only shape. A single `compact` field would suffice for the combined structure+Luhn rule, but the four-field decomposition is preferred because:

1. The country/prefix rule (`LOOKUP_TABLE`) is naturally keyed by `country_code` — the same indexing role `IBANNotation.country_code` and `BICNotation.country_code` play for their registry/country rules.
2. `nsin` deserves a first-class field because Paxman must never re-derive it by slicing in rules; the NSIN's zero-padding semantics (national numbers shorter than 9 chars are zero-padded on the left per ISO 6166 / ANNA identifiers page) live in the grammar's normalization story, not in a rule-side slice.
3. `check_digit` as its own field lets the PARSER rule assert `calc_check_digit(country_code + nsin) == check_digit` without positional magic strings.

The notation is therefore **isomorphic to IBAN/BIC per-grammar sanitized decompositions** and satisfies `Grammar[ISINNotation].recognize()` → `Rule[ISINNotation].matches()` typing. Every field is `str` (HOW_TO_ADD_NEW_CAPABILITY.md §3 requires all notation fields be `str`).

**Invariants the grammar enforces (before rules):**
- `country_code` is exactly 2 `A-Z` (uppercased from `[A-Za-z]`; ASCII-only via `(?ai:)`).
- `nsin` is exactly 9 `[A-Z0-9]` (uppercased; whitespace stripped).
- `check_digit` is exactly one `0-9`.
- `compact` is exactly 12 total and equals the concatenation; `compact == re.sub(r"[^A-Z0-9]", "", raw_body).upper()` modulo optional label stripping.
- Leading zeros inside `nsin` are significant and preserved (`GB0002634946` keeps `000263494`, never truncated).
- `raw_text` preserves original span (label + spacing + case); the notation is the syntax-normalized token.

### 3.2 Why not carry spaces or labels in the notation

Spaces, grouping, and `ISIN:` labels have **no lexical significance** for validity — they are presentation-only, exactly like IBAN paper groups and BIC grouped display. Compact and spaced forms of the same value have identical identity regardless of input spacing — dedup and status logic operate on `compact`. Presentation is `Capability.format_value()` only. No validator carries separators into its canonical representation: python-stdnum returns the compacted string, validator.js returns boolean over strict input, Symfony validates then passes through.

### 3.3 Why `country_code` is not a shape discriminator literal

IBAN uses free `str` for `country_code` because the country set (~89 registered) would be brittle as a `Literal`; BIC mirrors this for ISO 3166-1 plus XK. ISIN follows suit: the accepted prefix set is ISO 3166-1 alpha-2 (~249 official/user-assigned entries) **plus** a special-prefix annex (`EU`, `XS`, `EZ`, `ZZ`, `XT`, `XA–XD`, `XF`, `XK`, `QS`, `QT`) that evolves with ANNA/DSB practice (e.g. `XT` for digital tokens arrived with DTI/ISO 24165). Modeling each as a `Literal` would be brittle. Instead `country_code` is a free `str` validated by `LOOKUP_TABLE` against an embedded snapshot (`rules/data/country_codes.py`), mirroring Country's lexicon-key pattern where the registry, not the type system, owns the vocabulary. No `shape` field is needed — there is exactly one lexical length (12) and one meaning.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md §1 and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape — delimiters, fixed widths, character classes) or **Lexicon** (finite vocabulary — Country names, Currency words). ISIN has a distinctive fixed-width shape (`2 letters + 9 alnum + 1 digit`, total exactly 12), plus optional `ISIN` label, so **Regex** is the correct strategy. No lexicon table is involved at recognition — the vocabulary of valid prefixes lives in the country/prefix rule (lookup), never in the grammar key set.

### 4.2 Reference pattern (adapted from IBAN/BIC verbatim precedent)

IBAN precedent (`paxman/capabilities/IBAN/grammar/iban_recognition.py:23-32`):
```python
_IBAN_BODY = (
    r"(?:(?ai:IBAN)[\s:-]+)?"  # [\s:-]+ never zero-width — glued IBANDE89 blocked
    r"(?P<compact>(?ai:(?:[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}"
    r"|[A-Z]{2}[0-9]{2}(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,4})?)))"
)
_IBAN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _IBAN_BODY
    + BoundaryGuard.word_only().lookahead
)
```
BIC precedent (glued-label negative lookahead with mirrored country set):
```python
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + rf"(?!(?ai:(?:BIC|SWIFT){_BIC_SUFFIX_RE}\b))"  # glued label without separator
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)
```

**Proposed ISIN pattern (single grammar, staged pipeline):**

```python
import re

from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one-or-more, never zero-width: a glued
# "ISINUS0378331005" must not fuse into a mention (ISBN-13/IBAN/BIC precedent).
# Body: CC + 9 alnum + 1 digit = exactly 12, never 11 or 13.
# Two alternatives: contiguous (canonical) and single-space-tolerant
# (attested by python-stdnum clean(...,' ') and isvalid.dev /\s/g strip logic;
# fixed count prevents unbounded absorption — no IBAN-style greedy tail risk).
# (?ai:) ASCII restriction rejects fullwidth digits and non-ASCII homoglyphs
# while BoundaryGuard.word_only() stays Unicode-aware (no global re.ASCII).
_ISIN_BODY = (
    r"(?:(?ai:ISIN)[\s:-]+)?"
    r"(?P<compact>(?ai:[A-Z]{2}(?: ?[A-Z0-9]){9} ?[0-9]))"
)
# Glued-label guard: block only when what follows literal "ISIN" is itself a
# complete valid-shape ISIN (mirrors shipped BIC grammar review note); genuine
# Iceland codes ("IS" + NSIN starting with digits) are unaffected because the
# suffix after "ISIN" then starts with a digit, not [A-Z]{2}.
_GLUED_LABEL_GUARD = r"(?!(?ai:ISIN[A-Z]{2}[A-Z0-9]{9}[0-9]))"
_ISIN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _GLUED_LABEL_GUARD
    + _ISIN_BODY
    + BoundaryGuard.word_only().lookahead
)


def _isin_notation(match: re.Match[str]) -> ISINNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    # compact is now exactly 12 alphanum ending in a digit; split structurally
    return ISINNotation(
        country_code=compact[0:2],
        nsin=compact[2:11],
        check_digit=compact[11],
        compact=compact,
    )


class ISINRecognitionGrammar(PipelineGrammar[ISINNotation]):
    """ISIN recognition — 12-char CC+NSIN+C with optional ISIN label and single-space tolerance."""

    name = "isin_recognition"
    semantics = "isin_recognition"
    single_value = True
    pre = StandardPre[ISINNotation](empty_guard=True)
    regex = RegexStage[ISINNotation](
        pattern=_ISIN_PATTERN, notation_fn=_isin_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs IBAN/BIC/ISSN:*

- Ship as module-scope **string** pattern; `RegexStage` compiles it (mirrors `_ISBN13_PATTERN = r"..."`). Do not double-compile via `re.compile(...).pattern`.
- Strip in `notation_fn` via `isascii() and isalnum()` filter + `.upper()` — the BIC shipped precedent (`bic_recognition.py:93`) verbatim; rejects fullwidth digits and `K`-style homoglyphs while guards stay Unicode-aware.
- `(?: ?[A-Z0-9]){9} ?[0-9]` tolerates single spaces between body characters at any grouping (`US 037833 100 5`, `US037833 1005`, `PL0000 503135`). The quantifier is **fixed-count**, so unlike IBAN's variable-length paper alternative there is no unbounded absorption window: the match ends after exactly 12 characters regardless of trailing prose.
- Trailing char class is `[0-9]` — a letter check digit is impossible; `US037833100X` cannot match even under `IGNORECASE`.
- Leading `BoundaryGuard.word_only()` (`(?<!\w)`) and trailing `(?!\w)` block glued runs (`XUS0378331005`, `US0378331005Y`) — ISSN/IBAN/BIC shipped convention for alphanum identifiers.
- **Label handling:** `(?:(?ai:ISIN)[\s:-]+)?` fused, separator one-or-more (never zero-width). `notation_fn` maps only the `compact` group, so `raw_text` includes label+spacing when matched while `notation.compact` is bare — mirrors ISSN/IBAN/BIC.
- **Glued-label negative lookahead:** without it, `ISINUS0378331005` would carve `IS|INUS0378331|…`-shaped false positives (the first two letters `IS` satisfy the head class). The BIC-style guard fires only when the text after literal `ISIN` is itself a complete valid shape, preserving genuine `IS…` (Iceland) codes whose post-`ISIN` suffix starts with a digit. This is a direct port of the shipped BIC review note (`bic_recognition.py` comments).
- Uses `PipelineGrammar` + `StandardPre` + `RegexStage` because that is the staged pipeline every shipped identifier capability actually runs (HOW_TO_ADD_NEW_GRAMMAR.md's bare-`Grammar` recipe is the minimal teaching form).

**Form-coverage traceability (§2.1 → pattern):**

| §2.1 row | Pattern element |
|----------|-----------------|
| Canonical compact | main body alternative (contiguous path of `(?: ?…)`) |
| Lowercase | `(?ai:)` inline flag + `re.IGNORECASE` + `.upper()` |
| Outer whitespace | `word_only` guards (non-word boundary transparent) |
| Inner-space grouped | ` ?` interleaving inside the fixed-count quantifier |
| Label-prefixed prose | fused `(?:(?ai:ISIN)[\s:-]+)?` |
| Glued label | `_GLUED_LABEL_GUARD` negative lookahead |
| Hyphen-grouped | none — DEFER row, community extension (§13#9) |
| Quoted/bracketed + annotation | `word_only` guards + fixed 12-char bound |

**Single grammar vs N:** One grammar, one `semantics = "isin_recognition"` identity id. A second grammar (e.g. hyphen-tolerant) would coalesce semantics per HOW_TO_ADD_NEW_GRAMMAR.md option A if ever added; nothing today justifies the cross-grammar containment complexity.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md §"Recognition Pipeline Contract")

- Grammar emits **span-bearing** `RecognitionMatch[ISINNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))`. Stages must not mutate `text` (`PipelineState` scratch only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`orchestrator.py:_dedup_spans`, L244–261). Cross-grammar containment never dedups. For ISIN (single shipped grammar), within-grammar dedup resolves overlapping claims like a labeled span vs a bare sub-run at the same start.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

Concrete engine check:
```python
ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
# longer wins within SAME grammar; across grammars never deduped
```

### 4.4 Guard boundaries against sibling grammars

ISIN vs sibling financial/internet alphanum grammars — length + charset + terminal-digit split disambiguates everything:

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| ISIN | exactly `12`: `[A-Z]{2}[A-Z0-9]{9}[0-9]` | 2 letters | `(?!\w)` prevents claiming a prefix of longer alphanum; terminal digit mandatory |
| BIC | `8` or `11` | 4-char institution | Shorter than 12 — disjoint |
| IBAN | `15–34`, positions 3–4 digits | 2 letters then 2 digits | Longer than 12 — disjoint |
| LEI | `20` `[A-Z0-9]{20}` | no fixed shape | Longer; `word_only` blocks inner carving |
| CUSIP | `9` | digit or letter issuer code | Shorter; bare CUSIP lacks `CC` head + check tail |
| WKN / SEDOL | `6` / `7` | various | Shorter than 12 |

Label affinity: case-insensitive `ISIN` substring is distinct from sibling labels (`BIC`, `SWIFT`, `IBAN`, `ISBN`, `ISSN`, `ORCID`); no overlap conflicts. Within-capability ambiguity does not exist (one grammar, deterministic notation).

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md §1, ARCHITECTURE.md §"Community Extensions")

The grammar declares `semantics = "isin_recognition"` (identity id); both validating rules declare `target_semantics = frozenset({"isin_recognition"})`. Engine `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. Coalescing to a shared domain id becomes relevant only when a second grammar (community hyphen-tolerant variant) is actually added.

### 4.6 `single_value` — one mention per call vs batch processing

Shipped capabilities all set `single_value=True` (ISBN/ISSN/IBAN/BIC/ORCID verified in source), consistent with Paxman's one-canonical-value-per-call invariant (`MultipleMentionsError` via `_enforce_single_value_invariant` when distinct recognized mentions resolve differently; identical values coalesce). Portfolio holdings and index files legitimately contain 2+ ISINs per document, so batch extraction will want free-text mining.

Recommendation: **initial `single_value=True`** (shipped precedent, single-instrument field use-case), documented caller-owned segmentation path (`docs/recipes/segmentation.md`); a community `extra_grammars` variant with `False` can serve batch callers later.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO** — International Organization for Standardization, Technical Committee **ISO/TC 68** (Financial services), Subcommittee **SC 8** (Reference data for financial services), secretariat held by SNV (Swiss member). Confirmed by ISO news release `news/ref2616.html` ("published by ISO technical committee ISO/TC 68, Financial services, subcommittee SC 8") and the TC 68 "What is ISIN" briefing PDF. |
| **Registration Authority (RA)** | **ANNA — Association of National Numbering Agencies** (global member association; Brussels). Per ANNA identifiers page: *"ANNA is the registration authority for two ISO standards: the International Securities Identification Number (ISIN (ISO 6166)) … as well as the Financial Instrument Short Name (FISN (ISO 18774))"*. Assignment is federated: ~116 NNAs across 220+ jurisdictions (central securities depositories, exchanges, central banks, vendors, regulators) plus the **Derivatives Service Bureau (DSB)** as single global NNA for OTC-derivative ISINs. |
| **Spec name** | `ISO 6166 — Financial services — International securities identification number (ISIN)` (title renamed at the 2021 edition; earlier editions titled `Securities and related financial instruments — International securities identification numbering system (ISIN)` per ISO catalogue lineage). Scope statement (ISO page): *"provides a uniform structure for the identification of financial instruments as well as referential instruments (see Annex A) using a unique identification code and associated minimum descriptive data (see Annex B)."* |
| **Current edition** | **ISO 6166:2021 (8th ed., published 2021-02)** — current; ISO stage `90.20` (standard under periodical review, review effective 2026-01-15 per Serbian ISS RS mirror; Genorma shows close of review 2026-06-05). ICS 03.060. Withdraws/supersedes **ISO 6166:2013** (BSI: "BS ISO 6166:2021 supersedes BS ISO 6166:2013"). Main changes vs 2013 (BSI + ISO news): scope explicitly covers financial *and* referential instruments; new instrument types added to which ISINs can be allocated — **OTC derivatives (EZ and ZZ prefixes)**, baskets, emission allowances and carbon credits; new minimum descriptive elements in Annex B. 15 pages (SIS product data). |
| **Check character system** | Not a separate ISO publication — the modulus 10 **Double-Add-Double** formula is defined normatively inside ISO 6166 itself (ANNA Guidelines cite it as *"ISO 6166 (Annex C – Normative) – Formula for computing modulus 10 'Double-Add-Double' check digit"*); algorithmically it is the Luhn mod-10 applied over the letter-expanded digit string (`A=10 … Z=35`). Single decimal check digit — no letter analogue, no two-check-digit MOD 97 variant. |
| **Country code reference** | `ISO 3166-1 alpha-2` for the first two characters (ANNA identifiers page verbatim: *"The first two characters are taken up by the alpha-2 country code as issued in accordance with the international standard ISO 3166"*), maintained by the ISO 3166 Maintenance Agency — **plus special prefixes** outside ISO 3166 that ecosystem validators and RA practice accept (§5.4). |
| **Related specs / registries** | ANNA **ISIN Guidelines** (Version 21 June 2023; December 2025 Amendment PDF) — uniform assignment process among NNAs; **ANNA Service Bureau** (single-point access to ISIN/CFI/FISN reference data; free ISIN Lookup Service); **DSB** for OTC derivatives; CFI (ISO 10962) and FISN (ISO 18774) as sibling ANNA-RA standards; LEI (ISO 17442) linkage initiative (ANNA–GLEIF). |

**ISIN structure (ISO 6166 via ANNA identifiers page, verbatim decomposition):**

```
CC NNNNNNNNN C
│ │         └── 1 numeric check digit — modulus 10 "Double-Add-Double"
│ │             over the letter-expanded 11-char payload
│ └─────────── 9 alphanumeric NSIN — national number zero-padded on the
│              left to fill all nine spaces when shorter
└───────────── 2-letter prefix — ISO 3166-1 alpha-2 of the issuer's country
               (securities other than debt) or of the allocating NNA (debt);
               depository receipts use the receipt issuer's country;
               plus special prefixes (XS international, EZ/ZZ OTC derivatives,
               XT digital tokens, XA–XD/XF substitute agencies, QS/QT internal)
        Total length exactly 12 characters, [A-Z0-9], canonical uppercase.
```

Quoted ANNA identifiers page:
> "The final character is a check digit computed according to the modulus 10 'Double-Add-Double' formula."

> "Where the national number consists of fewer than nine characters, zeros are inserted in front of the number so that the full nine spaces are used."

Formal charset: `[A-Z]{2}[A-Z0-9]{9}[0-9]` compact; spaced display presentation-only; `(?i)` accepted, canonical upper.
Examples from evidence: `US0378331005` (Apple, from CUSIP `037833100`), `AU0000XVGZA3` (Treasury Corporation of Victoria), `GB0002634946` (BAE Systems, from SEDOL `000263494` zero-padded), `XS…` international securities, `EZ…`/`ZZ…` OTC derivatives (DSB).

**Lineage table (ISO 6166 editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 6166:1993 | 1993 | withdrawn | Early single-part edition under the securities title (catalogue lineage; pre-2001 editions distributed via CD-ROM era per Wikipedia History) |
| ISO 6166:2001 | 2001 | withdrawn | `Securities and related financial instruments — International securities identification numbering system (ISIN)` title generation |
| ISO 6166:2013 | 2013 | withdrawn (superseded 2021-02) | Last edition under the securities title; basis of most ecosystem documentation |
| ISO 6166:2021 | 2021-02 (8th ed.) | **current**, stage `90.20` under periodical review | Title renamed "Financial services — …"; referential instruments in scope; EZ/ZZ OTC derivative prefixes; baskets/emission allowances/carbon credits; Annex B minimum descriptive data extended |

*Hedge note:* pre-2013 edition dates are cited from standards-body catalogue mirrors fetched 2026-08-24 (BSI, Genorma, SIS, Standard Norge); iso.org itself returns HTTP 403 to automated fetch, so the primary catalogue URL is cited from Wikipedia's reference (`https://www.iso.org/standard/78502.html`) corroborated by four mirrors showing identical edition/date/stage metadata.

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 68/SC 8) | `ISO 6166:2021` | `2021-02` (8th ed., current) | `https://www.iso.org/standard/78502.html` | `active` — supersedes 2013 | `2021` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 6166:2013` | `2013` | `https://www.iso.org/standard/59351.html` (lineage; cited via BSI supersession) | `withdrawn` | `2013` | `specification` |
| ISO | `ISO 6166:2001` | `2001` | (ISO record withdrawn — cited via catalogue mirrors) | `withdrawn` | `2001` | `specification` |
| ISO | `ISO 6166:1993` | `1993` | (ISO record withdrawn — cited via catalogue mirrors) | `withdrawn` | `1993` | `specification` |
| ANNA (ISO RA) | `ANNA ISIN Guidelines` | `December 2025 Amendment` (prev. Version 21, June 2023) | `https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf` + `https://anna-web.org/wp-content/uploads/2023/06/ISIN-Guidelines-Version-21_June-2023.pdf` | `active` | `2025` | `policy` |
| ANNA (ISO RA) | `ANNA Service Bureau / ISIN Lookup Service` | Rolling | `https://anna-web.org/about-the-anna-service-bureau/` + `https://anna-web.org/identifiers/` | `active` — rolling | `2026` | `registry` |
| ISO 3166 MA | `ISO 3166-1 alpha-2` | (referenced normatively by 6166) | `https://www.iso.org/iso-3166-country-codes.html` | `active` | — | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* historical rules citing withdrawn editions would carry `lifecycle="withdrawn"`/`"superseded"`; the initial shipped rules are expected `active`. The Service Bureau layer, if ever shipped, is `kind="registry"` rolling.

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_6166_ed2021.py` | `authority="ISO"`, `specification_name="ISO 6166:2021"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/78502.html"`, `version="2021"`, `lifecycle="active"`, `publication_year=2021` | `Section 4-isin-structure-check-digit` (PARSER) | Generic structure: length exactly 12, charset `[A-Z0-9]`, head letters, terminal numeric digit, and the modulus 10 Double-Add-Double checksum over the letter-expanded payload (`calc_check_digit(compact[:11]) == compact[11]`); `normalize()` returns the uppercase compact form |
| `rules/anna_isin_guidelines_ed2025.py` | `authority="ANNA"`, `specification_name="ANNA ISIN Guidelines"`, `kind="policy"`, `reference_url="https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf"`, `version="2025-12"`, `lifecycle="active"`, `publication_year=2025` | `Guidelines-country-and-special-prefix` (LOOKUP_TABLE) | Whether `country_code` ∈ ISO 3166-1 alpha-2 snapshot ∪ special prefixes `{EU, XS, EZ, ZZ, XT, XA, XB, XC, XD, XF, XK, QS, QT}` (data in `rules/data/country_codes.py` with documented refresh procedure); always-active per BIC §5.4 precedent |
| `rules/anna_service_bureau_ed2026.py` *(not shipped — deferred liveness layer)* | `authority="ANNA"`, `specification_name="ANNA Service Bureau"`, `kind="registry"`, `reference_url="https://anna-web.org/about-the-anna-service-bureau/"`, `version="Rolling"`, `lifecycle="active"`, `publication_year=2026` | `Section *-isin-registry-membership` (issued-ness) | Whether the 12-char ISIN exists in an ASB/Lookup-Service snapshot (`requires_features={"include_registry_validation"}`); explicitly out of scope for v1 |

Each `Rule[ISINNotation]` subclass declares the six enforced metadata attributes at class-definition time (`paxman/core/domain.py:Rule.__init_subclass__` enforces `name`, `strategy`, `provenance`, `citation`, `target_semantics`, `requires_features`; empty `target_semantics` rejected at import):

```python
class Section4IsinStructureCheckDigit(Rule[ISINNotation]):
    name = "Section 4-isin-structure-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Structure clause + normative check-digit annex (modulus 10 Double-Add-Double)"
    target_semantics = frozenset({"isin_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISINNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: ISINNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **Edition/lifecycle:** `https://www.iso.org/standard/78502.html` (Edition 8, 2021-02, referenced by Wikipedia ref 4), ISO News `https://www.iso.org/news/ref2616.html` (2021-02-03: TC 68/SC 8, changes vs 2013), BSI `https://knowledge.bsigroup.com/products/financial-services-international-securities-identification-number-isin` (supersedes BS ISO 6166:2013; EZ/ZZ prefixes; Annex B additions), Serbian ISS RS `https://iss.rs/en/project/show/iso:proj:78502` (stage 90.20, effective 2026-01-15), Genorma `https://genorma.com/en/standards/iso-6166-2021` (90.60 close of review), SIS (edition 8, 15 pages), Standard Norge (published 2 February 2021).
- **RA role:** `https://anna-web.org/identifiers/` ("ANNA is the registration authority for … ISIN (ISO 6166)"; structure decomposition verbatim; NNA table incl. CUSIP Global Services for US + AG/BM/BS/BZ/GD/KY/LC/MH/PH/PR/TT/VC/VG, LSE for GB+GG/IM/JE, SIX for CH/LI) and ISO/TC 68 briefing `https://committee.iso.org/files/live/sites/tc68/files/Robin%20Doyle/What%20is%20ISIN-Final.pdf` (116 NNAs, 220+ jurisdictions, DSB, EZ prefix for OTC).
- **Check digit:** isin.org education page (conversion table + VALUE−SUM walkthrough), Wikipedia worked examples (Apple sum 45 → check 5; Treasury Corp Victoria sum 27 → check 3; transposition flaw), regit-identifiers Rust docs (weights assigned over the expanded digit string, not original characters), all eight validator implementations agreeing.

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. The ISO 6166 PARSER rule checks: `len(compact) == 12`, charset `[A-Z0-9]` (already grammar-guaranteed but re-asserted defensively), `country_code.isalpha()`, `check_digit.isdigit()`, and `calc_check_digit(country_code + nsin) == check_digit` where expansion is `ord(ch) - 55` for letters / `ord(ch) - ord('0')` for digits, weights alternate over the expanded digit string from the right. The ANNA LOOKUP_TABLE rule checks membership of `country_code` in the embedded union set. All return `False` for any invalid input, never raise — not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** — returns the **default compact form** (uppercase, no separators, 12 chars). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any presentation token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability's `format_value()` seam only. Both rules must return the **same** compact string for the same valid notation — candidate dedup `(value, recognition_rule, validation_rule)` ensures agreement stays `SUCCESS`.
- **`RuleStrategy` choice:** ISBN's `iso_2108_ed2017` uses `PARSER` for the weighted check digit; IBAN's `iso_13616_1_ed2020` fuses structure + MOD 97 into one `PARSER`; BIC splits structure `PARSER` from country `LOOKUP_TABLE`. For ISIN the same split applies: structure+checksum is `PARSER` (ISO 6166:2021), prefix vocabulary is `LOOKUP_TABLE` (ANNA Guidelines policy), mirroring how the special prefixes (`XS`, `EZ`, …) come from RA practice rather than the base standard's ISO 3166 reference.

### 5.4 Country/prefix scope decision

The first two characters are ISO 3166-1 alpha-2 **for ordinary securities**, but the live identifier space includes non-3166 prefixes that every serious consumer must accept:

| Prefix | Meaning | Evidence |
|--------|---------|----------|
| `EU` | European Union (e.g. EU bonds) | python-stdnum `_country_codes`; floydspace `PSEUDO_COUNTRY_CODES`; apache SPECIALS |
| `XS` | International securities (clearing-org allocated, e.g. Euroclear/Clearstream) | python-stdnum; floydspace; ANNA identifiers page context |
| `EZ`, `ZZ` | OTC derivatives (DSB allocation) | BSI change log ("derivative products with EZ and ZZ prefix"); ISO/TC 68 briefing ("custom alpha prefix of 'EZ'" via DSB) |
| `XT` | Digital tokens (DTI, ISO 24165 / DTIF) | isvalid.dev taxonomy (`XTV15WLZJMF0`); ANNA digital-token integration announcements |
| `XA`, `XB`, `XC`, `XD` | Substitute agencies (CGS, NSD Russia, WM Datenservice, SIX) | python-stdnum comments; apache SPECIALS |
| `XF` | Internally assigned, not-unique numbers | python-stdnum comments |
| `XK` | Kosovo (user-assigned code) | python-stdnum; validator.js XK precedent family (IBAN issue 2045 analogue) |
| `QS`, `QT` | Agency-internal (Euroclear France; Switzerland) | python-stdnum comments; floydspace; apache |
| `QW` | Single-source only (floydspace) | Excluded from v1 set — insufficient corroboration (Open Decision §13#6) |
| Retired `CS`, `YU`, `SU`, … | Historical jurisdictions | apache SPECIALS includes them; excluded from v1 (Open Decision §13#6) |

**Recommendation:** treat prefix validation as **always-active `LOOKUP_TABLE`** over `ISO 3166-1 ∪ {EU, XS, EZ, ZZ, XT, XA, XB, XC, XD, XF, XK, QS, QT}` — the BIC §5.4 rationale verbatim: cost is a frozenset membership test, correctness benefit is rejecting `XX`/`ZZ`-style junk at `INVALID` instead of false `SUCCESS`. Snapshot lives in `rules/data/country_codes.py` (plain module-level frozenset, ISBN `range_message.py` pattern) with a documented refresh procedure keyed to the ANNA Guidelines amendment cadence. Callers wanting raw structural validation only can `excluded_rules=["Guidelines-country-and-special-prefix"]` — no flag proliferation needed for v1. A registry liveness layer stays deferred behind `requires_features={"include_registry_validation"}` if ever demanded (staleness concerns; determinism-by-snapshot preserved via `Provenance.version`).

### 5.5 Assignment / registration authority & Registry content

Network: **ANNA** (RA, Brussels) + **~116 National Numbering Agencies** (central securities depositories, exchanges, central banks, vendors, regulators) across **220+ jurisdictions**, plus the **Derivatives Service Bureau (DSB)** as the single global numbering utility for OTC-derivative ISINs. Assignment rules (ISO/TC 68 briefing): securities other than debt → NNA where the issuer is incorporated/domiciled; debt securities → NNA of the place of deposit or an international clearing organization; no-NNA countries → designated substitute agencies; OTC derivatives → free DSB registration.

Registry: the **ANNA Service Bureau** provides single-point access to global identifiers (ISIN, CFI, FISN) with a **free ISIN Lookup Service** for search/retrieval; the linked **LEI initiative** (ANNA–GLEIF) connects issuers to issues. Record content (per Annex B minimum descriptive data): ISIN, CFI classification, FISN short name, currency of trading, status, and related reference fields — far beyond Paxman's identity-only scope. Only official NNAs can issue valid ISINs; most do not charge for allocation (cost-recovery exceptions permitted under ANNA's RA obligations).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman/core/capability_contract.py`) — never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base's `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ISINContract(CapabilityContract):
    """User-facing contract for ISIN capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isin"  # cf. IBAN "electronic" / BIC "bic"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped"})

    capability_name: str = field(default="isin", init=False)
    # No grammar-toggle flags for the initial single-grammar design.
    # If the registry liveness layer is ever added:
    # include_registry_validation: bool = False

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For ISIN there is one always-active grammar,
    # so the property is omitted — base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For ISIN, `isin` (compact) is the machine canonical form; `grouped` is the human 2+6+3+1 rendering.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format` — `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order, then capability-specific params (if any — none for v1).

**Presentational-only invariant (hard rule — ARCHITECTURE.md §"The Formatting Seam"):**

- `output_format` is a **representation transform, never a recognition/validation signal**. Rules never read it; `normalize()` always returns compact; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup / status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance**.

For ISIN, the offered formats model the two interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"isin"` (default) | `US0378331005` / `GB0002634946` | Compact, uppercase, no separators — DB key, settlement-message payload, vendor-feed join key |
| `"grouped"` | `US 037833 100 5` | Space-grouped human display (`CC NNNNNN NNN C`), presentation-only; mirrors the spaced walkthroughs in RA/secondary literature and the whitespace tolerance ecosystem validators strip |

*Do not add a `with_label` format — the `ISIN` label is not part of the identifier; report renderers add it. Do not add an `nsin` format exposing the bare national number — that leaks a different identifier domain.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from typing import Sequence

from paxman.capabilities.ISIN.contract import ISINContract
from paxman.capabilities.ISIN.grammar.isin_recognition import ISINRecognitionGrammar
from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.capabilities.ISIN.rules.anna_isin_guidelines_ed2025 import (
    GuidelinesCountryAndSpecialPrefix,
)
from paxman.capabilities.ISIN.rules.iso_6166_ed2021 import (
    Section4IsinStructureCheckDigit,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class ISINCapability(Capability[ISINNotation]):
    name = "isin"  # lowercase identifier - what users pass to registry

    def get_grammars(self) -> list[Grammar[ISINNotation]]:
        return [ISINRecognitionGrammar()]  # single grammar; one lexical length

    def get_rules(self) -> list[Rule[ISINNotation]]:
        return [
            Section4IsinStructureCheckDigit(),
            GuidelinesCountryAndSpecialPrefix(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> ISINContract:
        return ISINContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: ISINNotation
    ) -> str:
        if output_format == "grouped":
            # Human display: CC NNNNNN NNN C (presentation-only)
            return f"{value[0:2]} {value[2:8]} {value[8:11]} {value[11]}"
        return value  # isin default is identity - normalize() must return compact
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`): the scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(ISIN())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---
## 7. Validation — Structure, Check Digit, Prefix Membership

### 7.1 Level 1: structure + modulus 10 Double-Add-Double (ISO 6166 normative annex)

The check digit is computed over the letter-expanded digit string of the first 11 characters:

```
1. Expand each character to its numeric value:
     digits stay themselves ('0'..'9' → 0..9)
     letters A=10, B=11, …, Z=35   (ASCII − 55; equivalently base-36 index)
   Concatenate the expansions into ONE digit string of length 11–22.
2. Starting from the RIGHTMOST digit of the expanded string, double every
   second digit (Luhn parity over the EXPANDED string — regit-identifiers:
   "the alternating Luhn weights are assigned over the expanded string, not
   the original characters").
3. Sum all resulting digits (a doubled value ≥10 contributes its two digits,
   e.g. 14 → 1+4).
4. check = (10 − (SUM mod 10)) mod 10.
   Validation direction: append the given check digit; the total must be
   ≡ 0 (mod 10).
```

**Worked example — `US0378331005` (Apple Inc.; Wikipedia/isin.org):**
- Body: `U S 0 3 7 8 3 3 1 0 0` → expand `30 28 037833100` → digit string `3028037833100`.
- Double every second from right; sum digits → SUM = 45.
- Next multiple of ten ≥ 45 is 50 → VALUE − SUM = 50 − 45 = **5** ✓ (matches terminal digit).

**Worked example — `AU0000XVGZA3` (Treasury Corporation of Victoria):**
- Body expands to `103000003331163510`; grouped sum → SUM = 27 → 30 − 27 = **3** ✓.

**Generation vs validation:** python-stdnum's `calc_check_digit(number[:-1]) == number[-1]` and `from_natid(country_code, natid)` (zero-pad NSIN to 9, append computed check) mirror ISBN-10→13 expansion semantics: Paxman validates only; it never rewrites the payload.

**Known algorithm limitation (documented, never corrected):** adjacent transposition of two letters at even distance parity can preserve the checksum — Wikipedia documents `AU0000XVGZA3` ↔ `AU0000VXGZA3` both validating. This is a property of single-decimal Luhn vs IBAN's MOD 97-10; Paxman reports both spellings as independently valid values (no correction, no flag).

### 7.2 What makes an ISIN "valid" vs "prefix-valid" vs "issued/live"

- **valid (structural)** — correct length (12), charset `[A-Z0-9]`, head letters, numeric tail, Luhn passes. Always-active PARSER (ISO 6166:2021).
- **prefix-valid** — structural plus `country_code` ∈ ISO 3166-1 ∪ ANNA special prefixes. Always-active LOOKUP_TABLE (ANNA ISIN Guidelines policy layer), BIC §5.4 precedent.
- **issued/live-registered** — actually present in the ANNA Service Bureau / ISIN Lookup Service. Deferred gated registry rule (`requires_features={"include_registry_validation"}`); determinism-by-snapshot with versioned Provenance if ever shipped.

Like ISBN valid-vs-allocated (Range Message) and ISSN valid-vs-issued (ISSN Register), ISIN separates the deterministic string claims from registry liveness.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase `us0378331005` | `SUCCESS` → `US0378331005` | Grammar `(?ai:)` + IGNORECASE + `.upper()` folds; identity preserved |
| 2 | Inner-space grouping `US 037833 100 5` | `SUCCESS` → same compact as row 1 | Single-space tolerance in fixed-count body; whitespace stripped in `notation_fn` |
| 3 | Irregular multi-space `US  0378331005` | `MISSING` | Only single spaces interleaved; double space breaks the 12-char window (Pre-collapse widening documented §13#5) |
| 4 | Label present `ISIN: US0378331005` | `SUCCESS`, span includes label | Fused `[\s:-]+` optional label; `raw_text` keeps it, `compact` does not |
| 5 | Glued label `ISINUS0378331005` | `MISSING` | Negative lookahead fires (suffix after `ISIN` is complete valid shape); no carve, no fuse |
| 6 | Glued-label lookalike `ISIN03783100` (Iceland-shaped) | `SUCCESS` if checksum+prefix pass | Lookahead does NOT fire — suffix after literal `ISIN` starts with a digit, so genuine `IS…` codes survive |
| 7 | Over-long `US03783310055` (13) | `MISSING` for full run | Fixed-count quantifier + trailing `(?!\w)`; no partial claim of first 12 because position 13 is a word char |
| 8 | Under-long `US037833100` (11, calculator body) | `MISSING` | Terminal `[0-9]` after 9 alnum cannot bind; bodies alone never claimed |
| 9 | Letter check digit `US037833100X` | `MISSING` | Terminal class is `[0-9]`; no `X` analogue exists (unlike ISSN/ISBN-10/ORCID) |
| 10 | Bad checksum `US0378331003` | `INVALID` | Shape claimed; PARSER rule rejects via Luhn (stdnum doctest vector) |
| 11 | Invalid prefix `ZZ…` (non-special ZZ context) / `XX0000XVGZA3` | `INVALID` (with prefix rule active) vs false `SUCCESS` if excluded | LOOKUP_TABLE membership; exclusion path documented §14 |
| 12 | Special prefixes `XS0931417178`, `EZ…`/`ZZ…` OTC, `XT…` token | `SUCCESS` | Union set includes attested specials; provenance ANNA Guidelines |
| 13 | Transposed letters `AU0000VXGZA3` | `SUCCESS` (flaw) | Parity-preserving swap defeats Luhn; algorithmic limitation documented §7.1 |
| 14 | OCR homoglyphs `USO378331005`, fullwidth | `MISSING` | Strict ASCII charset via `(?ai:)`; no autocorrection |
| 15 | Hyphen separators `US-037833100-5` | `MISSING` (v1) | Zero code-level ecosystem tolerance; DEFER to community extension (§13#9) |
| 16 | Two distinct ISINs in one slice | `AMBIGUOUS` / `MultipleMentionsError` | Single-slice invariant; segmentation recipe is caller-owned |
| 17 | Quoted/bracketed/embedded `"US0378331005"`, `(CUSIP 037833100)` | `SUCCESS` for the ISIN; CUSIP unclaimed | Non-word delimiters transparent to guards; 9-char sibling below threshold |
| 18 | Leading-zero NSIN `GB0002634946` | `SUCCESS`, zeros preserved | Zero-padding is spec-mandated NSIN semantics; notation keeps `nsin="000263494"` verbatim |

---
## 9. Resolution-State Map (ARCHITECTURE.md §"Resolution Semantics")

| Input | Status | Why |
|-------|--------|-----|
| Valid ISIN, any surface variant (case/spaces/label/grouped) | `SUCCESS` → compact 12 | Single canonical value via ISO 6166 + ANNA rules agreeing on identical `normalize()` output |
| Bad checksum (`US0378331003`) | `INVALID` | Recognized by grammar; PARSER rule rejects |
| Unknown prefix (`XX0000XVGZA3`, junk `ZZ`) | `INVALID` | LOOKUP_TABLE membership rejects (rule active by default) |
| Special prefix (`XS/EZ/ZZ/XT/XK/QS/QT/XA–XD/XF/EU`) | `SUCCESS` | Union set membership per Guidelines policy layer |
| No 12-char candidate runs in text | `MISSING` | No grammar recognized anything |
| Hyphenated input (`US-037833100-5`) | `MISSING` | Deliberate v1 scope cut (DEFER row §2.1) |
| Glued label (`ISINUS0378331005`) | `MISSING` | Negative lookahead blocks carve and fusion |
| Two distinct valid ISINs in one slice | `AMBIGUOUS` / `MultipleMentionsError` | Single-slice ambiguity — use segmentation |
| Registry-gated input (if `include_registry_validation=True` and absent from snapshot) | `INVALID` | Authority feature gating — enabled yields INVALID rather than MISSING (Country `include_localized` analogue) |
| Prefix rule excluded + structurally-valid junk | `SUCCESS` (false positive risk) | Caller-owned exclusion; mirrors BIC §14 analysis |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py ISIN --name isin \
    --authority "ISO" --spec-name "ISO 6166:2021" \
    --spec-url "https://www.iso.org/standard/78502.html" \
    --publication-year 2021
```

Creates 13 files plus one edit: `paxman/capabilities/ISIN/{__init__,notation,contract,capability}.py`, `grammar/isin_recognition.py`, `rules/iso_6166_ed2021.py`, four test stubs under `tests/capabilities/isin/`, and the alphabetical wiring edit to `paxman/capabilities/__init__.py` (`__all__` + `_LAZY` + TYPE_CHECKING import, PEP 562 lazy-export pattern). TODO(scaffold) markers guide replacement.

> Note: the scaffolder's single `--spec-name/--spec-url/--publication-year` covers one provenance file. After scaffolding, add `rules/anna_isin_guidelines_ed2025.py` (second publication, LOOKUP_TABLE) and `rules/data/country_codes.py` manually per HOW_TO_ADD_NEW_CAPABILITY.md §5 one-file-per-publication discipline.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[ISINRecognitionGrammar()]`; `active_grammars` omitted for the initial design (base `None` → engine runs every shipped grammar in order). Only introduce the property if recognition becomes feature-gated.
- Each grammar carries `name = "isin_recognition"` (snake_case `_recognition` suffix) and non-empty `semantics`; engine composes shipped + `extra_grammars` community extensions in order, failing fast on name collisions (`CapabilityError`) or dangling `target_semantics` (`ContractError`).
- Registration lands alphabetically between IBAN and IP in `_LAZY`/`__all__` (`tests/unit/test_capability_exports.py` enforces export completeness — update CONTEXT.md table alongside).

### 10.3 Cross-cutting invariants (fail review if violated)

- **No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source** — fix root cause or use scoped ruff `per-file-ignores` (sanctioned pattern).
- **No cross-capability imports** — ISIN imports only from `paxman.core` (import-linter enforced); the prefix snapshot is ISIN-owned data, never imported from Country.
- **No presentation token in any `paxman/capabilities/*/rules/` module** (code, comments, docstrings) — CI source scan fails otherwise.
- `@dataclass(frozen=True, slots=True)` for notation; `@dataclass(frozen=True)` **without** slots for contracts.
- Deterministic by construction: same input + contract + library snapshot → same output; prefix set evolution is a data-snapshot event recorded via `Provenance.version`.

---
## 11. Recommended File Layout (mirrors ISSN/IBAN/BIC)

```
paxman/capabilities/ISIN/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── isin_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_6166_ed2021.py
    ├── anna_isin_guidelines_ed2025.py
    └── data/
        ├── __init__.py
        └── country_codes.py   # frozenset union snapshot
tests/capabilities/isin/
├── __init__.py
├── test_notation.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py
```

Per-registry data module shape (parallel to ISBN `rules/data/range_message.py`):

```python
# rules/data/country_codes.py
"""ISO 3166-1 alpha-2 plus ANNA special prefixes.

Refresh procedure: re-derive from the current ANNA ISIN Guidelines amendment
plus ISO 3166-1 alpha-2 official list; record the Guidelines version in the
rule's Provenance.version. Never hand-edit entries without a source.
"""

ISO_3166_1_ALPHA_2: frozenset[str] = frozenset({
    # ~249 official + user-assigned alpha-2 entries (snapshot)
})

SPECIAL_PREFIXES: frozenset[str] = frozenset({
    "EU",  # European Union issues
    "XS",  # international securities (clearing-org allocated)
    "EZ",  # OTC derivatives (DSB)
    "ZZ",  # OTC derivatives (DSB)
    "XT",  # digital tokens (DTI / ISO 24165)
    "XA", "XB", "XC", "XD",  # substitute agencies (CGS / NSD / WM / SIX)
    "XF",  # internally assigned non-unique numbers
    "XK",  # Kosovo user-assigned
    "QS",  # Euroclear France internal
    "QT",  # Switzerland internal
})
```

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md §10 and shipped precedents)

- **Grammar tests** (`test_grammar.py`): valid compact (`US0378331005`); every §2.1 RECOGNIZE form as a positive vector (lowercase, inner-space groupings `US 037833 100 5` / `PL0000 503135` style, outer whitespace, label variants `ISIN:`/`isin -`, quoted/bracketed, embedded-with-annotation); multiple matches per text; incompatible formats (11-char body, 13-char run, letter check digit, hyphenated input, glued label, homoglyphs) return empty; empty input returns empty; span invariants (`raw_text == text[start:end]`, half-open bounds, label included in span); name/semantics conventions; boundary-guard negatives (`XUS0378331005`, `US0378331005Y`); Iceland lookalike positive (`ISIN03783100`-shaped genuine code, 12 chars, not blocked by lookahead).
- **Rule tests** (`test_rules.py`): PARSER rule — valid vectors (`US0378331005`, `AU0000XVGZA3`, `GB0002634946`, an `XS…` special-prefix vector), invalid checksum (`US0378331003`), transposed-letter flaw pair both accepted, letter-expansion edge (high-value letters Z=35 producing two-digit expansion), normalize exact compact, provenance attributes (authority ISO, lifecycle active, year 2021), name/strategy conventions, leading-zero NSIN preserved; LOOKUP_TABLE rule — valid prefixes (US, GB, XS, EZ, XK), invalid (XX, QW), normalize agreement with PARSER (identical compact output), strategy/provenance kind assertions.
- **Capability tests** (`test_capability.py`): notation frozen/hashable/slots, wiring counts (1 grammar, 2 rules), grammar/rule naming conventions, `format_value` round-trips (identity default, grouped `US 037833 100 5` exact string), `create_contract` factory common block, contract immutability, invalid `output_format` raises `ContractError`.
- **Integration**: MISSING (no candidate runs, hyphenated, glued label) / INVALID (bad checksum, bad prefix) / SUCCESS (all surface variants coalesce) / AMBIGUOUS or `MultipleMentionsError` (two distinct ISINs); excluded-rules path (prefix rule excluded → structurally-valid junk resolves, documented false-positive posture); pinned_rules; year temporal filtering (year=2013 drops nothing material but exercises the filter); autouse `_clean_registry`; determinism/VersionStamp across repeated runs; span-bearing match integrity; candidate dedup of identical mentions.
- **Property tests (hypothesis)**: generate valid ISINs by picking a prefix from the union set + random alnum NSIN + computed check digit → must canonicalize to itself; random strings over `[A-Za-z0-9 ]` → overwhelmingly MISSING/INVALID with no crash; spaced vs compact inputs of the same payload yield identical canonical values; `format_value(grouped)` round-trip strips back to compact.
- **Consistency tests**: every shipped semantics covered by both rules' `target_semantics`; every special prefix exercised by at least one test vector; export completeness via `tests/unit/test_capability_exports.py`.
- **Presentation purity**: rules modules contain no presentation token (CI source scan passes).
- **Real vectors**: Apple `US0378331005`; Treasury Corp Victoria `AU0000XVGZA3`; BAE `GB0002634946`; stdnum doctest failure `US0378331003`; flaw pair `AU0000XVGZA3`/`AU0000VXGZA3`; international `XS0931417178`; token `XTV15WLZJMF0`; Poland spaced paste `PL0000 503135`.

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT naming | `"isin"` (compact identity), offer `"grouped"` | Wire form is the machine key (IBAN `"electronic"`/BIC `"bic"` precedent); grouped display is the only attested alternative presentation |
| 2 | Single grammar vs N | Single `isin_recognition` initially; defer any hyphen-tolerant split to community extension with coalesced semantics | One lexical length; avoids cross-grammar containment spurious AMBIGUOUS |
| 3 | Prefix validation always-active vs gated | Always-active LOOKUP_TABLE; callers exclude via `excluded_rules` if they want structure-only | BIC §5.4 precedent verbatim: cheap set membership, rejects junk at INVALID instead of false SUCCESS; no flag proliferation |
| 4 | Grammar length strictness | Grammar enforces exactly 12 via fixed-count quantifier + terminal `[0-9]`; never 11/13 | All eight validators agree; keeps recognition cheap and definitive |
| 5 | Case/space normalization locus | Grammar folds case and strips single inter-character spaces; rules validate uppercase alnum only | Syntax-not-semantics boundary; multi-space Pre-collapse widening explicitly deferred (keeps v1 narrow, mirrors ISSN hyphen-strictness decision) |
| 6 | Special-prefix set composition | Include `{EU, XS, EZ, ZZ, XT, XA–XD, XF, XK, QS, QT}`; exclude `QW` (single-source) and retired `CS/YU/SU` | ≥2-source or RA-documentation bar met for included set; apache's retired codes serve back-compat, not live identification — revisit on demand |
| 7 | Publication split vs fuse | Two files (`iso_6166_ed2021.py` PARSER + `anna_isin_guidelines_ed2025.py` LOOKUP_TABLE); fuse rejected | Special prefixes come from RA policy, not the base standard's ISO 3166 reference; separate provenance lets each evolve on its own cadence |
| 8 | single_value for batch | True initially; segmentation recipe for multi-entity docs; optional community grammar with False later | Consistent with every shipped identifier capability |
| 9 | Hyphen tolerance | Reject in v1 (MISSING); DEFER to community `extra_grammars` Pre-stage | Zero code-level ecosystem tolerance (python-stdnum strips spaces only; `-` fails its alphabet check); documentary recommendation ≠ attested surface |
| 10 | Label span inclusion | Include label in `raw_text` span (fused regex), `notation.compact` label-free | Mirrors ISSN/ISBN/IBAN/BIC shipped behavior |
| 11 | Grouped-format definition | Fixed `CC NNNNNN NNN C` (2+6+3+1) rendering | Deterministic single choice; arbitrary regroupings would make `format_value` non-deterministic per caller taste — document as Paxman presentation convention like IBAN groups-of-four |

---
## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent ISIN-vs-ISIN ambiguity.** One grammar, one lexical length, deterministic decomposition — the positional ambiguity Date exhibits (US vs European readings) has no analogue. Two distinct ISINs in one slice are authorial choice, handled by segmentation, not ambiguity resolution.
- **Unknown prefix is INVALID, not ambiguity.** `XX0000XVGZA3` produces exactly one recognized value that one rule rejects — there is no competing canonical value. Without the prefix rule the same input falsely succeeds; that is a configuration consequence (documented §9 row 10), never a competing interpretation.
- **Length discrimination prevents cross-capability confusion.** ISIN 12 vs BIC 8/11 vs LEI 20 vs IBAN 15–34 vs CUSIP 9/WKN 6/SEDOL 7 are pairwise disjoint; `word_only` guards eliminate inner carving from longer runs (LEI cannot yield a 12-window).
- **Presentation vs identity.** Lowercase, spacing, labels, and grouping collapse to one compact identity — dedup guarantees SUCCESS across variants; no format ever creates or destroys candidates (presentational-only invariant).
- **Staleness is not ambiguity.** A future ANNA amendment adding a prefix changes the data snapshot, not the pipeline; determinism-by-construction scopes results to a fixed snapshot with versioned provenance. The transposed-letter checksum weakness is likewise not ambiguity: both spellings resolve to themselves as distinct values; Paxman corrects nothing.

---
## 15. URL Reference (authoritative, fetched 2026-08-24)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 6166:2021 catalogue (Edition 8, 2021-02, current) | https://www.iso.org/standard/78502.html | primary (via Wikipedia ref 4; direct fetch 403) |
| ISO news: ISIN standard updated (TC 68/SC 8, changes vs 2013) | https://www.iso.org/news/ref2616.html | primary |
| ISO/TC 68 briefing "What is ISIN" (116 NNAs, DSB, EZ prefix, assignment rules) | https://committee.iso.org/files/live/sites/tc68/files/Robin%20Doyle/What%20is%20ISIN-Final.pdf | primary |
| BSI BS ISO 6166:2021 (supersedes 2013; EZ/ZZ; Annex B changes) | https://knowledge.bsigroup.com/products/financial-services-international-securities-identification-number-isin | primary mirror |
| Serbian ISS RS stage 90.20 review dates | https://iss.rs/en/project/show/iso:proj:78502 | primary mirror |
| Genorma edition/stage corroboration | https://genorma.com/en/standards/iso-6166-2021 | secondary mirror |
| SIS product data (edition 8, 15 pages) | https://www.sis.se/en/produkter/sociology-services-company-organization/finances-banking-monetary-systems-insurance/iso-61662021/ | primary mirror |
| Standard Norge publication date | https://online.standard.no/en/iso-6166-2021 | primary mirror |
| ANNA identifiers page (RA role, structure decomposition, NNA table) | https://anna-web.org/identifiers/ | primary |
| ANNA ISIN Guidelines Dec 2025 Amendment PDF | https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf | primary |
| ANNA ISIN Guidelines v21 June 2023 PDF | https://anna-web.org/wp-content/uploads/2023/06/ISIN-Guidelines-Version-21_June-2023.pdf | primary |
| ANNA Service Bureau / free ISIN Lookup Service | https://anna-web.org/about-the-anna-service-bureau/ | primary |
| isin.org education (check-digit walkthrough, conversion table) | https://www.isin.org/education/ | secondary |
| isin.org about/convert (CUSIP↔ISIN context) | https://www.isin.org/about/ + https://www.isin.org/convert-cusip-to-isin/ | secondary |
| Wikipedia ISIN (worked examples, transposition flaw, lineage) | https://en.wikipedia.org/wiki/International_Securities_Identification_Number | secondary |
| python-stdnum `stdnum/isin.py` | https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/isin.py | primary (code) |
| validator.js `src/lib/isISIN.js` | https://github.com/validatorjs/validator.js/blob/master/src/lib/isISIN.js | primary (code) |
| Apache Commons `ISINValidator.java` | https://github.com/apache/commons-validator/blob/master/src/main/java/org/apache/commons/validator/routines/ISINValidator.java | primary (code) |
| Apache Commons `ISINCheckDigit.java` | https://github.com/apache/commons-validator/blob/master/src/main/java/org/apache/commons/validator/routines/checkdigit/ISINCheckDigit.java | primary (code) |
| Symfony `Isin.php` + `IsinValidator.php` | https://github.com/symfony/symfony/blob/8.2/src/Symfony/Component/Validator/Constraints/Isin.php (+ IsinValidator.php) | primary (code) |
| floydspace/isin-validator `src/index.ts` | https://github.com/floydspace/isin-validator/blob/master/src/index.ts | primary (code) |
| JonaMX/js-isin-validator `lib/index.js` | https://github.com/JonaMX/js-isin-validator/blob/master/lib/index.js | primary (code) |
| djmarland/isin `Validator.php` | https://github.com/djmarland/isin/blob/master/src/ISIN/Validator.php | primary (code) |
| moshejs/instrument-identifiers `src/index.ts` | https://github.com/moshejs/instrument-identifiers/blob/main/src/index.ts | primary (code) |
| isvalid.dev ISIN guides (whitespace tolerance, XT taxonomy) | https://isvalid.dev/docs/isin (+ /isin-validation-python, /isin-validation-nodejs) | secondary |
| regit-identifiers Rust check-digit docs (expanded-string weights) | https://docs.rs/regit-identifiers/latest/regit_identifiers/checkdigit/fn.isin_check_digit.html | secondary |
| Paxman conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary |
| Shipped precedents | paxman/capabilities/{IBAN,BIC,ISSN,ISBN,ORCID}/…, paxman/engine/orchestrator.py, paxman/core/domain.py, paxman/core/capability_contract.py | primary |

---
## 16. Evidence Completion — Resolved

This report's ISIN-specific authoritative evidence has been fetched and cited (2026-08-24):
- [x] ISO catalogue entry: ISO 6166:2021 (8th ed., current, stage 90.20) superseding 2013 plus 2001/1993 lineage; TC 68/SC 8; ICS 03.060; citation anchored to structure clause + normative check-digit annex (hedged where the paywalled spec's internal clause numbers are unverifiable without purchase)
- [x] RA and registry provenance: ANNA authority, ISIN Guidelines (Dec 2025 amendment) as `kind="policy"` layer, Service Bureau/Lookup Service as deferred `kind="registry"`
- [x] Structure: 12 chars, `CC + NSIN(9) + C(1)`, zero-padded NSIN, strictly numeric check digit
- [x] Checksum algorithm proved: modulus 10 Double-Add-Double (Luhn) over letter-expanded string `A=10…Z=35`, worked examples US0378331005→5 and AU0000XVGZA3→3 verified against two independent walkthroughs plus eight implementations; transposed-letter flaw documented
- [x] Country nuance: ISO 3166-1 alpha-2 plus special prefixes EU/XS/EZ/ZZ/XT/XA–XD/XF/XK/QS/QT enumerated with per-prefix evidence; QW and retired-code exclusions flagged
- [x] Ecosystem regex consensus: eight validators extracted verbatim (Python/JS/Java/PHP/TS) with strip-logic evidence for whitespace-only tolerance
- [x] Recognition-surface inventory complete (§2.1): nine attested forms with RECOGNIZE/DEFER/REJECT dispositions — no silently unhandled form
- [x] Wild input shapes validated (§2.2, 18 rows) against spec + RA pages + validators
- [x] Label scope decision (fused `[\s:-]+`, glued-label lookahead with Iceland-safe guard)
- [x] No branch/head-office equivalence question exists (unlike BIC XXX); no URN namespace (IANA negative evidence)
- [x] Registry liveness scope decision (deferred behind requires_features)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ISSN, IBAN, BIC and ORCID Capabilities Teach ISIN (verbatim precedent)

> The following precedent is **sourced from the codebase as fetched 2026-08-24** (not speculative) and anchors the proposal to what Paxman already ships. Key excerpts verified in source: `paxman/capabilities/BIC/grammar/bic_recognition.py` (label `[\s:-]+` comment, `(?ai:)`, mirrored country frozenset, glued-label lookahead), `paxman/capabilities/IBAN/grammar/iban_recognition.py:23-32` (label + paper-alternative body, word_only guards), `paxman/capabilities/IBAN/notation.py:9-22` (country_code/check_digits/bban/compact decomposition), `paxman/engine/orchestrator.py:244-261/316-332/393-451` (`_dedup_spans`, `_validate_affinity`, `_enforce_single_value_invariant`), `paxman/core/domain.py:189-225` (six enforced Rule attributes), `paxman/core/capability_contract.py:20-95` (frozen-no-slots base, `resolve_output_format`, `active_grammars=None` default).

The five architectural lessons for ISIN:

1. **Grammar strips, rule validates, capability formats.** IBAN's `notation_fn` filters alnum + uppercases before any rule sees the token; ISBN's PARSER computes the check digit; `Capability.format_value` renders `paper` groups-of-four. ISIN copies all three seams verbatim with its own charset (`[A-Z]{2}[A-Z0-9]{9}[0-9]`) and its own grouped rendering (`CC NNNNNN NNN C`).

2. **One file per provenance, one class per section.** BIC ships `iso_9362_ed2022.py` + country lookup; ISBN ships three authorities in three files. ISIN ships two: `iso_6166_ed2021.py` (PARSER, structure+Luhn) and `anna_isin_guidelines_ed2025.py` (LOOKUP_TABLE, prefix vocabulary) — because the special-prefix annex is RA policy, not base-spec content, and must carry its own evolving `Provenance.version`.

3. **No presentation tokens in rules, ever.** The CI source scan makes the formatting seam the only render path; `normalize()` returns bare compact for both ISIN rules so candidate dedup sees identical values regardless of which rule validated.

4. **Single grammar with fused optional label avoids spurious AMBIGUOUS; glued labels get a shape-aware negative lookahead.** BIC's shipped review note blocks `BICDEUTDEFF` fusion only when the suffix is a complete valid BIC — ISIN ports this so `ISINUS0378331005` goes MISSING while genuine Iceland `IS…` codes survive.

5. **Fixed-count quantifiers bound absorption risk.** Unlike IBAN's variable-length paper alternative (which motivated groups-of-four), ISIN's `(?: ?[A-Z0-9]){9} ?[0-9]` is count-bounded at 12 characters — whitespace tolerance cannot swallow trailing prose, so the simpler tolerant form is safe here.

---

*Report saved to `docs/development/research/` per MILESTONE guidance for ISIN (roadmap entry #17). It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md`. For implementation, start from the `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0, then fill the domain per §4–§7 above.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
