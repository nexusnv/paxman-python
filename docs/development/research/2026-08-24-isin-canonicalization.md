# ISIN Canonicalization Research — paxman-python

**Date:** 2026-08-24
**Scope:** Primary-source survey of the ISIN standard (ISO 6166:2021, ANNA Registration Authority and ISIN Guidelines, ISO 3166-1 country-code handling, national numbering agencies and NSIN carriers), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `ISIN` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue and news pages (iso.org `standard/78502.html`, `news/ref2616.html`, ISO/TC 68 "What is ISIN" PDF), national standards-body mirrors (BSI Knowledge, Serbian ISS RS, Genorma, SIS, Standard Norge) for edition/lifecycle corroboration, ANNA identifiers page and ISIN Guidelines PDFs (Dec 2025 Amendment, June 2023 v21), isin.org education/about/convert pages, Wikipedia ISIN article (secondary, worked examples), and eight ecosystem validators fetched verbatim (python-stdnum `stdnum/isin.py`, validator.js `isISIN.js`, Apache Commons Validator `ISINValidator.java` + `ISINCheckDigit.java`, Symfony `Isin.php` + `IsinValidator.php`, floydspace/isin-validator, JonaMX/js-isin-validator, djmarland/isin, moshejs/instrument-identifiers, plus isvalid.dev docs). Shipped Paxman capabilities (ISBN, ISSN, IBAN, BIC, ORCID, Country, Phone) as architectural precedents. Repo state: `main` @ `09a8709` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](2026-08-21-issn-canonicalization.md) plus the IBAN precedent [`docs/development/research/2026-08-22-iban-canonicalization.md`](2026-08-22-iban-canonicalization.md) and BIC/ORCID precedents [`docs/development/research/2026-08-23-bic-canonicalization.md`](2026-08-23-bic-canonicalization.md) / [`docs/development/research/2026-08-23-orcid-canonicalization.md`](2026-08-23-orcid-canonicalization.md).
**Review (2026-09-20, `research/isin-canonicalization-review` @ `a529264`):** re-verified against `dev` — grammar/staged-pipeline precedent (`PipelineGrammar` + `StandardPre` + `RegexStage`, `BoundaryGuard.word_only()`) still current per DOI/UUID; updated stale orchestrator/domain line cites to symbol-only references, moved the contract import to canonical `paxman.core.capability_contract`, added `suppress_common_words` + tuple-style `create_contract` per DOI/UUID, recorded ADR-0010/0011/0012 standing, and fixed the second rule name to the `Section`-prefixed convention. No primary-source findings changed.
**Independent source audit (2026-09-20):** re-fetched every §15 URL + raw validator sources + ANNA Guidelines PDFs (V25 Dec 2025 / V21 Jun 2023) + ISO catalogue (78502/44811) + TC68 briefing PDF + isvalid guides + IANA registry and recomputed all check digits via python-stdnum oracle. Findings resolved in place: corrected two checksum-invalid example vectors (`XS0931417178` → `XS0931417173`, `PL0000503135` → `PL0000503132` with real-Orlen `PLPKN0000018` noted), replaced checksum-confounded prefix test vectors with checksum-valid isolations (`XX0378331005`, `ZZ0378331001`), fixed the ISO 6166:2013 catalogue URL (`59351.html` 404 → `44811.html`, Edition 7, 2013-07) + early lineage (no 1993 edition; first publication 1986 per TC68 briefing; Standard Norge history: 1981/1983/1986/1987/1994/2001/2013/2021), updated stage `90.20` → `90.60` Close of review 2026-06-05, corrected Guidelines title to Version 25 (superseded by V26 Jun 2026) and narrowed its attested prefix set to `{EU, XS, XA–XD, XT}` (§5/§7/§1/§3.10) with `EZ` via TC68 briefing/ANNA identifiers + DSB and `XF/XK/QS/QT/ZZ/QW` via validator snapshots + ISO 3166 user-assigned ranges, flagged Apache `SPECIALS` as a 355-entry near-exhaustive list (country check near-vacuous) and isvalid.dev example vectors as checksum-invalid, and recorded NNA-count drift (briefing 116/220+ vs current ASB 120+/200+). Validation logic (structure + expanded-string Luhn + prefix membership split) is otherwise airtight and unchanged.

---

## Executive Summary

ISIN is a strong fit for a Paxman capability: it has an unambiguous canonical form (**compact, uppercase, exactly 12 chars**: `CC + NSIN + C` where `CC` is a 2-letter prefix (ISO 3166-1 alpha-2 or a special ANNA/DSB prefix), `NSIN` is 9 alphanumeric characters zero-padded from the national number, and `C` is one numeric check digit computed by the modulus 10 **Double-Add-Double** (Luhn) formula), a stable single-part standard (**ISO 6166:2021**, 8th edition, published 2021-02-02, stage `90.60` Close of review 2026-06-05 — `90.20` was 2026-01-15 — publisher **ISO/TC 68/SC 8** Reference data for financial services, revises ISO 6166:2013 Edition 7, ICS 03.060, 15 pages) with **ANNA (Association of National Numbering Agencies)** as ISO Registration Authority operating through a federated model of **116 NNAs across 220+ jurisdictions per the TC68 briefing (2021 era; current ASB page: 120+ NNAs, 200+ jurisdictions, ~1M new ISINs/month)** plus the **Derivatives Service Bureau (DSB)** as single global NNA for OTC derivatives, a maintained authoritative registry layer (**ANNA Service Bureau** — single-point access to ISIN/CFI/FISN, free ISIN Lookup Service; ISIN Guidelines current as of Version 26 Jun 2026, superseding Version 25 Dec 2025), and a well-understood human-readable presentation (**space-grouped display** `US 037833 100 5`, presentation-only — Paxman `grouped` convention `CC NNNNNN NNN C`, not spec-defined). The domain mirrors Paxman's value proposition for IBAN/BIC/ISSN: recognizing the tolerant human surface (case, whitespace, optional `ISIN` label), validating strictly against the authority (structure + letter-expanded Luhn + country/prefix membership), and returning a canonical compact value with full provenance. Unlike BIC, ISIN has a real checksum (modulus 10 over the letter-expanded digit string, `A=10…Z=35`); unlike IBAN's MOD 97-10, it is a single decimal check digit with a documented weakness against adjacent letter transposition.

Key findings that shape the design:

1. **Canonical form is compact, uppercase, exactly 12 chars** (`US0378331005`, `AU0000XVGZA3`, `GB0002634946`). Regex consensus across all eight ecosystem validators is `^[A-Z]{2}[A-Z0-9]{9}[0-9]$` — 12 only, never 11 or 13, check digit strictly numeric (no letter `X` analogue). Space-grouped display (`US 037833 100 5`) is readability-only. This maps onto Paxman's presentational-only invariant: `format_value()` renders `isin` (compact, default) vs `grouped` (2+6+3+1 spaces) without touching validity.

2. **One grammar suffices.** Unlike ISBN (two lexical lengths → two grammars with `include_isbn10` gating), ISIN has one lexical length (12). A single `ISINRecognitionGrammar` with Regex (structural pattern matching) strategy is correct: optional fused `ISIN` label (`[\s:-]+`, never zero-width, IBAN/BIC precedent), contiguous alternative plus single-space-tolerant alternative, `BoundaryGuard.word_only()` on both sides, and a BIC-style glued-label negative lookahead so `ISINUS0378331005` yields `MISSING` instead of a false-positive carve.

3. **Validation is two-level, both mandatory, cleanly split by authority.** Level 1: generic structure + letter-expanded Luhn (`PARSER`, publication `ISO 6166:2021`, Annex C normative). Level 2: country/prefix membership (`LOOKUP_TABLE`, always-active as a Paxman design choice per the BIC §5.4 precedent — cheap set membership, high correctness value — not an ecosystem mandate: only 4/8 validators check prefixes at all and they disagree): ISO 3166-1 alpha-2 **plus special prefixes** — Guidelines-attested `EU`, `XS`, `XA–XD`, `XT` (V25 §§1–2/3.10/5/7) plus validator/ISO-3166-user-assigned practice `EZ` (TC68 briefing + ANNA identifiers page + DSB; absent from Guidelines text), `XF`, `XK`, `QS`, `QT` (python-stdnum + floydspace/Apache; `XK` single-curated + `XA–XZ` user-assigned; `QS/QT` in `QM–QZ` user-assigned), and provisional `ZZ` (no RA doc; only Apache's 355-entry near-exhaustive `SPECIALS` + `ZZ` user-assigned — see §5.4). No per-country length table (contrast IBAN), no registrant-range (contrast ISBN), no directory liveness for initial `SUCCESS`.

4. **Same-value surface collapses; identity is the compact string.** Lowercase, inner/outer whitespace, labels, and grouped spacing are presentations of one value — dedup operates on `compact`. Hyphen-separated input (`US-037833100-5`) has **zero code-level ecosystem tolerance** (all eight validators' code paths reject `-`; isvalid guides' code strips spaces only — Python `replace(" ","")`, Node `replace(/\s/g,'')` — hyphen removal appears only in generic integration prose) → `MISSING` in v1, DEFER to community extension. The transposed-letter checksum flaw (`AU0000XVGZA3` ↔ `AU0000VXGZA3` both validate — verified via python-stdnum oracle) is a property of the modulus-10 algorithm, not a recognition/validation concern — documented, never corrected.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 6166:2021` (`active`) owns structure + check-digit annex (Annex C normative); `ANNA ISIN Guidelines` Version 25 Dec 2025 (`kind="policy"`, superseded by V26 Jun 2026) owns the Guidelines-attested prefix vocabulary (`EU/XS/XA–XD/XT`); the extended validator-practice prefixes (`EZ/XF/XK/QS/QT` + provisional `ZZ`) are documented in the same LOOKUP_TABLE data snapshot with per-prefix strength notes (§5.4) rather than misattributed to the Guidelines; an ANNA Service Bureau / ISIN Lookup Service liveness layer (`kind="registry"`) is explicitly deferred behind `requires_features` if ever wanted.

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
| Inner-space grouped (any grouping) | `US 037833 100 5`, `US037833 1005`, `PL0000 503132` | python-stdnum `clean(number,' ')` removes ALL spaces; isvalid.dev Python `replace(" ","")` + Node `replace(/\s/g,'')` + API whitespace stripping (`pl 0000 503135`-style input handled); Wikipedia/isin.org walkthroughs render spaced groups | common in prose/PDF | **RECOGNIZE** | single-space-tolerant body `(?: ?[A-Z0-9]){9} ?[0-9]` |
| Label-prefixed prose | `ISIN: US0378331005`, `ISIN US0378331005`, `isin - us0378331005` | Prospectuses, research notes, vendor exports; label convention extrapolated from shipped `IBAN:`/`BIC:`/`ORCID:` precedents (no ISIN-specific label corpus cited — design choice, low risk) | common | **RECOGNIZE** | fused optional `(?:(?ai:ISIN)[\s:-]+)?` label |
| Glued label without separator | `ISINUS0378331005` | No validator tolerates; BIC shipped precedent blocks glued label via negative lookahead | rare (typo) | **REJECT** (→ `MISSING`) | BIC-style glued-label negative lookahead, fired only when the suffix after `ISIN` is itself a complete valid shape (protects genuine `IS…` Iceland codes) |
| Hyphen-grouped | `US-037833100-5` | Code strips spaces only in every validator (`clean(...,' ')`, `replace(" ","")`, `/\s/g`); **zero code-level hyphen tolerance in any of the 8 validators** (python-stdnum `-` fails its alphabet check; hyphen removal appears only in isvalid generic integration prose, not ISIN validation code) | occasional | **DEFER** (→ `MISSING` in v1) | none in v1; community `extra_grammars` Pre-stage candidate (Open Decision §13#9) |
| Quoted / bracketed | `"US0378331005"`, `[GB0002634946]` | Scraped JSON/BibTeX fragments; punctuation is non-word so guards hold | common | **RECOGNIZE** | `BoundaryGuard.word_only()` transparent to non-word delimiters |
| Embedded in sentence with annotation | `Apple ISIN US0378331005 (NASDAQ: AAPL)` | Free-text extraction target; parenthetical must not be swallowed | common | **RECOGNIZE** | span-bearing match; fixed 12-char bound prevents absorption |

No other written form is attested: ISIN has no resolver URI convention (unlike DOI/ORCID), no URN namespace (negative evidence: IANA urn-namespaces lists `issn`/`isbn`/`swift`/`lei`, not `isin`), no per-country print exception (unlike IBAN EG/BI/LY/SV), and no check-character letter analogue (unlike ISSN/ISBN-10/ORCID `X` — the ISIN check digit is strictly numeric per all eight validators' final `[0-9]`).

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical compact** | `US0378331005`, `AU0000XVGZA3`, `GB0002634946` | Spec master form — 12 chars, uppercase; `format_value()` default target |
| 2 | **Lowercase / mixed case** | `us0378331005`, `Us0378331005`, `gb0002634946` | Permitted chars case-insensitive; canonical uppercase — grammar `(?ai:)` + `IGNORECASE` + `.upper()` |
| 3 | **Inner-space grouped** | `US 037833 100 5`, `PL0000 503132`, `US037833 1005` | Attested by python-stdnum + isvalid.dev strip logic; single-space tolerance collapsed in `notation_fn`. Audit note: isvalid guides' `PL0000503135` (spaced `PL0000 503135`) is checksum-INVALID (correct check is `2`, real Orlen ISIN is `PLPKN0000018` per GPW) — do not use `...135` as a valid vector |
| 4 | **Irregular whitespace** | `US  037833 100 5`, tabs/newlines inside the run | Only *single* spaces interleaved in-pattern; multi-space runs break the 12-char window → `MISSING` (Pre-collapse widening documented §13#5) |
| 5 | **Label with colon/space/hyphen** | `ISIN: US0378331005`, `isin-US0378331005`, `ISIN - US0378331005` | Case-insensitive label, `[\s:-]+` one-or-more never zero-width (glued fusion blocked, ISBN-13/IBAN/BIC precedent); `raw_text` includes label, `notation.compact` does not. Label tolerance is a Paxman design extrapolation from sibling capabilities (no ISIN-specific label corpus cited) |
| 6 | **Glued label** | `ISINUS0378331005` | Negative lookahead fires when suffix after literal `ISIN` is a complete valid shape → no claim → `MISSING`; genuine Iceland `IS…` codes unaffected (suffix after `ISIN` there starts with a digit, not `[A-Z]{2}`). Audit note: §8#6's `ISIN03783100` is checksum-INVALID (`ISIN0378310` → check `8`, not `0`); use checksum-valid `IS0000000008` for a positive Iceland-shape test |
| 7 | **Over-long / under-long** | `US03783310055` (13), `US037833100` (11), `US037833100X` (letter check) | Exactly 12 enforced by pattern quantifier + trailing `word_only`; letter check digit impossible (`[0-9]` consensus across all validators) |
| 8 | **X-glued runs** | `XUS0378331005`, `US0378331005Y`, `AUS0378331005B` | `BoundaryGuard.word_only()` both sides — no carving out of longer alphanum tokens |
| 9 | **Invalid checksum** | `US0378331003` (should end 5; stdnum doctest raises `InvalidChecksum`) | Grammar claims (shape ok), rule rejects via Luhn → `INVALID` |
| 10 | **Invalid country/prefix** | `XX0378331005`, `ZZ0378331001` (checksum-valid, prefix-invalid isolations — verified `InvalidComponent` via stdnum oracle) | Shape-valid + checksum-valid; country/prefix rule rejects → `INVALID` (with rule active) vs false `SUCCESS` if excluded (§14). Audit note: earlier drafts used `ZZ0378331005` / `XX0000XVGZA3`, which are *also* checksum-INVALID (`ZZ037833100` → `1` not `5`; `XX0000XVGZA` → `9` not `3`) and therefore confound the two failure modes — do not use them as pure prefix vectors |
| 11 | **Special prefixes** | `XS0931417173` (international clearing, corrected check), `EZ…` OTC derivatives, `QS`/`QT` agency-internal, `XT…` digital tokens | Prefix set beyond ISO 3166-1 must be accepted; membership rule owns the union set. Audit note: `XS0931417178` (prior draft) is checksum-INVALID (`XS093141717` → `3`, not `8`) |
| 12 | **Transposed-letter flaw** | `AU0000VXGZA3` vs `AU0000XVGZA3` | Both pass Luhn (parity-preserving adjacent letter swap, Wikipedia "Check-digit flaw" section) — algorithm limitation, documented; both resolve to themselves, never corrected |
| 13 | **OCR / homoglyphs** | `USO378331005` (letter O for zero), fullwidth `ＵＳ…` | Strict ASCII `(?ai:)` charset; no autocorrection → `MISSING` (not claimed) |
| 14 | **Hyphen separators** | `US-037833100-5` | Zero ecosystem code tolerance → `MISSING` in v1 (DEFER, §13#9) |
| 15 | **Multiple per line** | `US0378331005 / GB0002634946`, `ISINs: XS0931417173, FR0000120271` | Free-text → 2+ span-bearing matches; single-slice resolution semantics apply (§2.4) |
| 16 | **Trailing annotation** | `US0378331005 (CUSIP 037833100)` | Fixed-length body + `(?!\w)` stops before `(`; CUSIP in parens is 9 chars — never claimed |
| 17 | **Quoted / bracketed** | `"US0378331005"`, `(GB0002634946)` | Non-word delimiters transparent to `word_only` guards |
| 18 | **Sibling-shaped runs** | CUSIP `037833100` (9), WKN `BAY41N` (6), SEDOL `B0YBJL7` (7), LEI `5493001KJTIIGC8Y1R12` (20) | Length discrimination: none is 12 with `[A-Z]{2}` head + numeric tail; LEI 20-char runs cannot yield an inner 12-carve due to guards |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Consensus regex (all 8 validators) | `^[A-Z]{2}[0-9A-Z]{9}[0-9]$` — 2 letters + 9 alnum + 1 numeric check = 12 |
| `arthurdejong/python-stdnum` `stdnum/isin.py` | No regex: `_alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'` membership + `len==12` else `InvalidLength` + `number[:2] in _country_codes` (251-entry `_iso_3116_1_country_codes` incl. retired `CS`/`AN` + `{EU, QS (listed twice), QT, XA, XB, XC, XD, XF, XK, XS}` — notably **no `EZ/ZZ/XT`**) else `InvalidComponent` + `calc_check_digit(number[:-1]) != number[-1]` else `InvalidChecksum`. `compact(): return clean(number, ' ').strip().upper()` — strips ASCII spaces only. Check: expand via `_alphabet.index` (`A=10…Z=35`), reverse, multiply alternating `(2,1)[i%2]`, sum digits, `(10 - sum) % 10` |
| `validator.js` `src/lib/isISIN.js` | `/^[A-Z]{2}[0-9A-Z]{9}[0-9]$/` — **no preprocessing, no country check** (strict canonical only). Backward pass from `str.length-2`: letters `charCodeAt(0)-55` split into lo/hi digits, `double` toggling, `digit>=5 → 1+(digit-5)*2 else digit*2`; final `check = trunc((sum+9)/10)*10 - sum` compared against last char |
| `apache/commons-validator` `ISINValidator.java` + `ISINCheckDigit.java` | `ISIN_REGEX = "([A-Z]{2}[A-Z0-9]{9}[0-9])"` via `CodeValidator(..., 12, ISIN_CHECK_DIGIT)`; `Character.getNumericValue` (`A=10…Z=35`), `POSITION_WEIGHT={2,1}`, `weightedValue = sumDigits(charValue * weight)`; optional country check `getInstance(true)` over `Locale.getISOCountries()` + `SPECIALS[]` — **audit correction: `SPECIALS` is a 355-entry near-exhaustive list (AA–ZZ incl. `EU/EZ/XT/XK/XS/QS/QT/QW/XA–XF/XX/ZZ/CS/YU/SU`), so the Apache country check is near-vacuous and must NOT be cited as support for a tight prefix set** |
| Symfony `Isin.php` + `IsinValidator.php` | `VALIDATION_LENGTH = 12`; `VALIDATION_PATTERN = '/[A-Z]{2}[A-Z0-9]{9}[0-9]{1}/'`; `strtoupper($value)` only (**no country check**); letters via `intval($char, 36)` then delegates the expanded string to Symfony's shared `Luhn` validator |
| `floydspace/isin-validator` `src/index.ts` | Length `!==12` error; explicit letter table `'A'→[1,0] … 'Z'→[3,5]` pushed as two digits; weights `i%2===0?2:1` reversed over the expanded array; `crossSum += calcCrossSum(nums[i]*weights[i])` (`calcCrossSum` sums decimal digits); `diff=10-(crossSum%10)`, `diff===10 → 0`. Country: `PSEUDO_COUNTRY_CODES={XS,XA,XB,XC,XD,XF,QS,QT,QW,EU}` + `i18n-iso-countries` lookup (**no `EZ/ZZ/XT/XK`** — `QW` attested here + Apache permissive only) |
| `JonaMX/js-isin-validator` `lib/index.js` | `/^([a-zA-Z]{2})((?![a-zA-Z]{10}\b)[a-zA-Z0-9]{9})([0-9])$/` wrapped with `R.toUpper` so lowercase tolerated; expansion `charCode > 57 ? charCode-55 : charCode`; reverse, double even indices, sum, `(10-(sum%10))%10`. Country: `data/countries.json` (244 entries; includes `XS` as "International Securities" + `CS`, but **no `EU/EZ/ZZ/XT/XA/XK/QS/QT/QW`**) |
| `djmarland/isin` PHP `Validator.php` (+ `ISIN.php`) | `strtoupper(trim($input))` then length==12 + `/[A-Z]{2}[A-Z0-9]{9}[0-9]{1}/` (**no country check**); parity-based doubling: `$p=count(numbers)%2` then alternate `num*=2; num=array_sum(str_split(num))`; `(10-($sum%10))%10` |
| `moshejs/instrument-identifiers` `src/index.ts` | `norm(value)=value.trim().toUpperCase()` (**no country check** — `countryCode` comment notes "or XS etc." but `isValidIsin` enforces pattern + checksum only); `charValue`: `48–57→code-48`, `65–90→code-55`; `isinLuhnSum` expands letters into two digits then doubles from rightmost (`i%2===0` over reversed index), digit-sum each product; `isinCheckDigit=(10-(sum%10))%10` |
| `isvalid.dev` docs (Python/Node guides + API) | `re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')` / JS equivalent + `replace(" ","").upper()` (Python, spaces only) / `replace(/\s/g,'').toUpperCase()` (Node) preprocessing + API-side whitespace stripping; documents `XT` prefix for digital tokens (`XTV15WLZJMF0` — checksum-VALID, verified). **Audit correction: guide/API example vectors are unreliable as valid vectors** — `PL0000503135` is checksum-INVALID (correct `PL0000503132`; real Orlen `PLPKN0000018`), `PL000PKN0RH16` is 13 chars (invalid length), `DE000A0MR4U4`/`XS1234567890` are checksum-INVALID (correct `DE000A0MR4U0`/`XS1234567896`). Cite isvalid only for strip logic + `XT` taxonomy, never for example validity |

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

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct ISINs at separate (non-overlapping) spans raises `MultipleMentionsError` under `single_value=True` enforcement (`orchestrator.py:_enforce_single_value_invariant`); overlapping parses of one mention yielding several values stay `AMBIGUOUS`. The caller-owned segmentation path (split → canonicalize each slice) is the intended multi-entity pattern for portfolio holdings, index constituent lists, or statement lines with multiple instruments. Identical ISIN mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

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
    nsin: str  # e.g. "037833100" — always length 9, A-Z0-9
    check_digit: str  # e.g. "5" — always length 1, 0-9
    compact: str  # e.g. "US0378331005" — exactly 12, equals cc+nsin+check
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

IBAN precedent (`paxman/capabilities/IBAN/grammar/iban_recognition.py`):
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
- Strip in `notation_fn` via `isascii() and isalnum()` filter + `.upper()` — the BIC shipped precedent (`bic_recognition.py`) verbatim; rejects fullwidth digits and `K`-style homoglyphs while guards stay Unicode-aware.
- `(?: ?[A-Z0-9]){9} ?[0-9]` tolerates single spaces between body characters at any grouping (`US 037833 100 5`, `US037833 1005`, `PL0000 503132`). The quantifier is **fixed-count**, so unlike IBAN's variable-length paper alternative there is no unbounded absorption window: the match ends after exactly 12 characters regardless of trailing prose.
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
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`orchestrator.py:_dedup_spans`). Cross-grammar containment never dedups. For ISIN (single shipped grammar), within-grammar dedup resolves overlapping claims like a labeled span vs a bare sub-run at the same start.
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
| **Governing publisher** | **ISO** — International Organization for Standardization, Technical Committee **ISO/TC 68** (Financial services), Subcommittee **SC 8** (Reference data for financial services), secretariat held by SNV (Swiss member). Confirmed by ISO news release `news/ref2616.html` ("published by ISO technical committee ISO/TC 68, Financial services, subcommittee SC 8") and the TC 68 "What is ISIN" briefing PDF (3 pages, fetched 2026-09-20). |
| **Registration Authority (RA)** | **ANNA — Association of National Numbering Agencies** (global member association; Brussels). Per ANNA identifiers page: *"ANNA is the registration authority for two ISO standards: the International Securities Identification Number (ISIN (ISO 6166)) … as well as the Financial Instrument Short Name (FISN (ISO 18774))"*. Assignment is federated: 116 NNAs across 220+ jurisdictions per the TC68 briefing (2021 era; current ASB page: 120+ NNAs, 200+ jurisdictions, ~1M new ISINs/month — record the as-of date) (central securities depositories, exchanges, central banks, vendors, regulators) plus the **Derivatives Service Bureau (DSB)** as single global NNA for OTC-derivative ISINs (briefing: "single global numbering agency"; Guidelines V25 §1: competence split NNAs/DSB; OTC detail defers to DSB guidelines at anna-dsb.com). |
| **Spec name** | `ISO 6166 — Financial services — International securities identification number (ISIN)` (title renamed at the 2021 edition; 2013 edition titled `Securities and related financial instruments — International securities identification numbering system (ISIN)` per the withdrawn `/standard/44811.html` catalogue entry, Edition 7, 2013-07, 11 pages). Scope statement (ISO pages + Genorma/SIS/ISS mirrors verbatim): *"provides a uniform structure for the identification of financial instruments as well as referential instruments (see Annex A) using a unique identification code and associated minimum descriptive data (see Annex B)."* |
| **Current edition** | **ISO 6166:2021 (8th ed., published 2021-02-02)** — current; ISO stage `90.60` Close of review 2026-06-05 (`90.20` systematic review was 2026-01-15 per the ISO lifecycle + ISS RS/Genorma mirrors). ICS 03.060. 15 pages (SIS/Genorma/ISS RS). Revises **ISO 6166:2013** (withdrawn 2021-02-02; ISO "Previously/Revised by" links). Main changes vs 2013 (ISO news + briefing): scope explicitly covers financial *and* referential instruments; new instrument types added to which ISINs can be allocated — **OTC derivatives**, baskets, emission allowances and carbon credits; new minimum descriptive elements in Annex B. Audit note: the 2021 change log names instrument *types*, not prefixes — `EZ` comes from the TC68 briefing ("custom alpha prefix of 'EZ'") + ANNA identifiers page ("initial two digits will use a custom 'EZ' code"), not from the ISO news text; `ZZ` has no RA source (see §5.4). |
| **Check character system** | Not a separate ISO publication — the modulus 10 **Double-Add-Double** formula is defined normatively inside ISO 6166 itself (Guidelines V25 §7 cites *"ISO 6166 (Annex C – Normative) - Formula for computing modulus 10 'Double-Add-Double' check digit"* — extracted verbatim from the Dec 2025 PDF p.22); algorithmically it is the Luhn mod-10 applied over the letter-expanded digit string (`A=10 … Z=35`). Single decimal check digit — no letter analogue, no two-check-digit MOD 97 variant. |
| **Country code reference** | `ISO 3166-1 alpha-2` for the first two characters (ANNA identifiers page verbatim: *"The first two characters are taken up by the alpha-2 country code as issued in accordance with the international standard ISO 3166"*; briefing: "alpha-2 country code prefix, as issued per ISO 3166-1"), maintained by the ISO 3166 Maintenance Agency — **plus special prefixes** outside ISO 3166 official assignments that ecosystem practice accepts (§5.4). Note the ISO 3166 user-assigned structure (iso.org country-codes page): `AA`, `QM–QZ` (covers `QS/QT/QW`), `XA–XZ` (covers `XA–XD/XF/XK/XS/XT`), `ZZ` are available for private use; `EU` is exceptionally reserved; `EZ` is ANNA/DSB-custom (not ISO 3166). |
| **Related specs / registries** | ANNA **ISIN Guidelines** — actual title Version 25, December 2025 (Implementation 1 Jan 2026; 26 pages; fetched via curl 2026-09-20; superseded by Version 26 Jun 2026 per the live ANNA identifiers page) — uniform assignment process among NNAs; **ANNA Service Bureau** (single-point access to ISIN/CFI/FISN reference data since 2001; free ISIN Lookup Service); **DSB** for OTC derivatives; CFI (ISO 10962) and FISN (ISO 18774) as sibling ANNA-RA standards (identifiers-page tabs + briefing); LEI (ISO 17442) linkage initiative (ANNA–GLEIF Apr 2019) + DTI (ISO 24165) `XT-ISIN` tab on the identifiers page. |

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

**Lineage table (ISO 6166 editions — corrected 2026-09-20 via Standard Norge history + ISO "Previously" links + TC68 briefing):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 6166:1981 | 1981-01 | withdrawn | Legacy paper document (Standard Norge history) |
| ISO 6166:1983 | 1983-01 | withdrawn | Legacy paper document (Standard Norge history) |
| ISO 6166:1986 | 1986-02 | withdrawn | First ISO publication as a standard per TC68 briefing ("first publication … was in 1986") |
| ISO 6166:1987 | 1987-11 | withdrawn | `Securities — International securities identification numbering system (ISIN)` title generation (Standard Norge) |
| ISO 6166:1994 | 1994-03 | withdrawn | `Securities — International securities identification numbering system (ISIN)` (Standard Norge; **no 1993 edition exists — prior draft's 1993 row was unattested and is removed**) |
| ISO 6166:2001 | 2001-03 (`/standard/33446.html` via 2013 page "Previously" link) | withdrawn | `Securities and related financial instruments — International securities identification numbering system (ISIN)` title generation |
| ISO 6166:2013 | 2013-07-23 (Edition 7, 11 pages) | withdrawn 2021-02-02 (superseded) | Last edition under the securities title (`/standard/44811.html`); basis of most ecosystem documentation |
| ISO 6166:2021 | 2021-02-02 (8th ed., 15 pages) | **current**, stage `90.60` Close of review 2026-06-05 | Title renamed "Financial services — …"; referential instruments in scope; OTC-derivative/basket/emission-allowance/carbon-credit instrument types; Annex B minimum descriptive data extended |

*Hedge note (updated 2026-09-20):* iso.org catalogue pages were fetched successfully via browser-UA webfetch on 2026-09-20 (`78502.html` current + `44811.html` withdrawn 2013; `59351.html` returns 404 — the prior draft's `59351.html` cite for 2013 was wrong and is corrected to `44811.html`). Pre-2013 internal clause numbers remain paywalled (spec purchase required); structure + Annex C cites are corroborated via the TC68 briefing, ANNA identifiers page, and Guidelines V25 §7. Prior draft's "pre-2001 editions distributed via CD-ROM" gloss misattributes Wikipedia: the CD-ROM sentence describes ISIN *information* distribution, not edition lineage.

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 68/SC 8) | `ISO 6166:2021` | `2021-02-02` (8th ed., current, 15 pp.) | `https://www.iso.org/standard/78502.html` | `active` — revises 2013 | `2021` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 6166:2013` | `2013-07-23` (Edition 7, 11 pp.) | `https://www.iso.org/standard/44811.html` (corrected 2026-09-20; prior draft's `59351.html` is 404) | `withdrawn` | `2013` | `specification` |
| ISO | `ISO 6166:2001` | `2001-03` | `https://www.iso.org/standard/33446.html` (via 2013 page "Previously" link) | `withdrawn` | `2001` | `specification` |
| ISO | `ISO 6166:1981/1983/1986/1987/1994` | `1981–1994` | (Standard Norge history + TC68 briefing "first publication 1986"; no 1993 edition) | `withdrawn` | `1981`–`1994` | `specification` |
| ANNA (ISO RA) | `ANNA ISIN Guidelines` | `Version 25, December 2025` (Implementation 1 Jan 2026; superseded by Version 26 Jun 2026) | `https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf` (HTTP 200, 26 pp., fetched via curl 2026-09-20; live page now links `.../2026/06/ISIN-Guidelines-Version-26-Jun-2026.pdf`) + `https://anna-web.org/wp-content/uploads/2023/06/ISIN-Guidelines-Version-21_June-2023.pdf` (HTTP 200, 27 pp.; cover header reads "Uniform Guidelines 2022") | `active` | `2025` | `policy` |
| ANNA (ISO RA) | `ANNA Service Bureau / ISIN Lookup Service` | Rolling | `https://anna-web.org/about-the-anna-service-bureau/` + `https://anna-web.org/identifiers/` | `active` — rolling | `2026` | `registry` |
| ISO 3166 MA | `ISO 3166-1 alpha-2` | (referenced normatively by 6166) | `https://www.iso.org/iso-3166-country-codes.html` | `active` | — | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* historical rules citing withdrawn editions would carry `lifecycle="withdrawn"`/`"superseded"`; the initial shipped rules are expected `active`. The Service Bureau layer, if ever shipped, is `kind="registry"` rolling.

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_6166_ed2021.py` | `authority="ISO"`, `specification_name="ISO 6166:2021"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/78502.html"`, `version="2021"`, `lifecycle="active"`, `publication_year=2021` | `Section 4-isin-structure-check-digit` (PARSER) | Generic structure: length exactly 12, charset `[A-Z0-9]`, head letters, terminal numeric digit, and the modulus 10 Double-Add-Double checksum over the letter-expanded payload (`calc_check_digit(compact[:11]) == compact[11]`, weights over the *expanded* string per Guidelines §7 / regit-identifiers); `normalize()` returns the uppercase compact form |
| `rules/anna_isin_guidelines_ed2025.py` | `authority="ANNA"`, `specification_name="ANNA ISIN Guidelines"`, `kind="policy"`, `reference_url="https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf"`, `version="2025-12 (V25; superseded by V26 Jun 2026)"`, `lifecycle="active"`, `publication_year=2025` | `Section 5-country-and-special-prefix` (LOOKUP_TABLE) | Whether `country_code` ∈ ISO 3166-1 alpha-2 snapshot ∪ special prefixes `{EU, XS, EZ, ZZ, XT, XA, XB, XC, XD, XF, XK, QS, QT}` (data in `rules/data/country_codes.py` with documented refresh procedure). Audit note: only `{EU, XS, XA, XB, XC, XD, XT}` are verbatim in Guidelines V25 text (§§1–2/3.10/5/7, PDF-extracted 2026-09-20); `EZ` is RA-attested outside the Guidelines (TC68 briefing + ANNA identifiers page + DSB); `XF/XK/QS/QT` (+ provisional `ZZ`, single-curated `QW` excluded) rest on validator snapshots + ISO 3166 user-assigned ranges (`XA–XZ`, `QM–QZ`, `ZZ`) — see §5.4 strength table. Provenance comment in the data module must record this split, not attribute the full set to the Guidelines |
| `rules/anna_service_bureau_ed2026.py` *(not shipped — deferred liveness layer)* | `authority="ANNA"`, `specification_name="ANNA Service Bureau"`, `kind="registry"`, `reference_url="https://anna-web.org/about-the-anna-service-bureau/"`, `version="Rolling"`, `lifecycle="active"`, `publication_year=2026` | `Section *-isin-registry-membership` (issued-ness) | Whether the 12-char ISIN exists in an ASB/Lookup-Service snapshot (`requires_features={"include_registry_validation"}`); explicitly out of scope for v1 |

Each `Rule[ISINNotation]` subclass declares the six enforced metadata attributes at class-definition time (`paxman/core/domain.py:Rule.__init_subclass__` enforces `name`, `strategy`, `provenance`, `citation`, `target_semantics`, `requires_features`; empty `target_semantics` rejected at import):

```python
class Section4IsinStructureCheckDigit(Rule[ISINNotation]):
    name = "Section 4-isin-structure-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = (
        "Structure clause + normative check-digit annex (modulus 10 Double-Add-Double)"
    )
    target_semantics = frozenset({"isin_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISINNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: ISINNotation, contract: Contract) -> str: ...
```

Name-convention note: the prefix rule carries the mandatory `Section`-prefixed name (`Section 5-country-and-special-prefix`); the final clause number is pinned to the Guidelines' prefix-vocabulary section at implementation (HOW_TO_ADD_NEW_CAPABILITY.md Step 5, `test_rule_name` convention — cf. ISBN's `Section 4-registrant-range` LOOKUP_TABLE precedent).

Evidence basis (re-verified 2026-09-20):
- **Edition/lifecycle:** `https://www.iso.org/standard/78502.html` (Edition 8, 2021-02-02, 15 pp., stage `90.60` Close of review 2026-06-05; Previously `44811.html`), `https://www.iso.org/standard/44811.html` (Edition 7, 2013-07-23, 11 pp., withdrawn 2021-02-02; Previously `33446.html` = 2001), ISO News `https://www.iso.org/news/ref2616.html` (2021-02-03: TC 68/SC 8 secretariat SNV, scope financial + referential instruments, OTC-derivative/basket/emission-allowance/carbon-credit types, Annex B elements — no prefix strings), Genorma + ISS RS + SIS + Standard Norge mirrors (edition/pages/ICS 03.060/scope/stage corroborated; Standard Norge history supplies 1981/1983/1986/1987/1994/2001 lineage). BSI Knowledge page is JS-gated (fetch returned title only 2026-09-20) — the "supersedes 2013" claim is corroborated via ISO Previously/Revised-by links instead; do not cite BSI for `EZ/ZZ` strings.
- **RA role:** `https://anna-web.org/identifiers/` ("ANNA is the registration authority for … ISIN (ISO 6166)"; structure decomposition verbatim incl. zero-padding + Double-Add-Double + `EZ` OTC sentence; NNA table incl. CUSIP Global Services for US + AG/BM/BS/BZ/GD/KY/LC/MH/PH/PR/TT/VC/VG, LSE for GB+GG/IM/JE, SIX for CH/LI; `XT-ISIN`/DTI tab) and ISO/TC 68 briefing PDF (fetched + text-extracted 2026-09-20: 12-char decomposition, `EZ` custom prefix + random 9 alnum + DSB single global NNA, 116 NNAs / 220+ jurisdictions, substitute agencies, Guidelines + free Lookup, FISN/CFI/LEI/20022, ANNA–GLEIF Apr 2019, first publication 1986). Guidelines V25 Dec 2025 PDF (26 pp.) + V21 Jun 2023 PDF (27 pp.) fetched via curl (HTTP 200) and text-extracted: §5 XA (CGS)/XB (NSD Russia)/XC (WM)/XD (SIX), §7 12-char + Annex C Double-Add-Double, §§1–2/3.10 `XT` crypto-referential + Designated Numbering Agency, §2.2 `EU`/`XS` ICSD rules — with **zero hits for `EZ/ZZ/QS/QT/QW/XK/XF`** in either PDF.
- **Check digit:** isin.org education page (conversion table + VALUE−SUM walkthrough, Apple SUM 45 → 5), Wikipedia worked examples (Apple sum 45 → check 5; Treasury Corp Victoria sum 27 → check 3; transposition flaw both sum 27 → 3 — all recomputed via stdnum oracle 2026-09-20), regit-identifiers Rust docs (weights over the expanded string, Apple body check 5), all eight validator implementations agreeing on expanded-string Luhn (only 4/8 check prefixes; see corrected snippet table).

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. The ISO 6166 PARSER rule checks: `len(compact) == 12`, charset `[A-Z0-9]` (already grammar-guaranteed but re-asserted defensively), `country_code.isalpha()`, `check_digit.isdigit()`, and `calc_check_digit(country_code + nsin) == check_digit` where expansion is `ord(ch) - 55` for letters / `ord(ch) - ord('0')` for digits, weights alternate over the expanded digit string from the right. The ANNA LOOKUP_TABLE rule checks membership of `country_code` in the embedded union set. All return `False` for any invalid input, never raise — not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** — returns the **default compact form** (uppercase, no separators, 12 chars). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any presentation token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability's `format_value()` seam only. Both rules must return the **same** compact string for the same valid notation — candidate dedup `(value, recognition_rule, validation_rule)` ensures agreement stays `SUCCESS`.
- **`RuleStrategy` choice:** ISBN's `iso_2108_ed2017` uses `PARSER` for the weighted check digit; IBAN's `iso_13616_1_ed2020` fuses structure + MOD 97 into one `PARSER`; BIC splits structure `PARSER` from country `LOOKUP_TABLE`. For ISIN the same split applies: structure+checksum is `PARSER` (ISO 6166:2021 Annex C), prefix vocabulary is `LOOKUP_TABLE` (Guidelines-attested `EU/XS/XA–XD/XT` + RA-attested `EZ` + validator/ISO-3166-user-assigned `XF/XK/QS/QT` + provisional `ZZ` — see §5.4; not all from the Guidelines text). Candidate qualification (ADR-0012): the `PARSER` candidate survives with `LOOKUP_TABLE` corroboration on the same `isin_recognition` semantics — the standard corroborated case (contrast DOI/UUID's `PARSER`-only vacuity exception, which ISIN never needs).

### 5.4 Country/prefix scope decision

The first two characters are ISO 3166-1 alpha-2 **for ordinary securities**, but the live identifier space includes non-3166 prefixes that every serious consumer must accept:

| Prefix | Meaning | Evidence (strength) |
|--------|---------|---------------------|
| `EU` | European Union (e.g. EU bonds) | **Strong:** Guidelines V25 §2.2 (`EU` prefix ISINs for ICSD/dual-note structures, 13 hits) + python-stdnum + floydspace + Apache permissive |
| `XS` | International securities (clearing-org allocated, e.g. Euroclear/Clearstream) | **Strong:** Guidelines V25 §2.2 (`XS` prefix ISINs, 10 hits) + python-stdnum + floydspace + JonaMX ("International Securities") + Apache |
| `EZ` | OTC derivatives (DSB allocation) | **Medium (RA-attested, outside Guidelines):** TC68 briefing ("custom alpha prefix of 'EZ'" + DSB single global NNA) + ANNA identifiers page ("initial two digits will use a custom 'EZ' code") + DSB guidelines (deferred to by V25 §1) + Apache permissive. Absent from Guidelines V25/V21 text and from stdnum/floydspace/JonaMX snapshots |
| `ZZ` | Claimed OTC-derivative second prefix | **Weak/provisional:** NO RA source found (briefing + identifiers page + both Guidelines PDFs name `EZ` only; 0 hits for `ZZ`). Only Apache's 355-entry permissive `SPECIALS` + ISO 3166 `ZZ` user-assigned availability. Recommend **exclude from v1** or carry explicitly as provisional with a TODO to produce an RA/DSB cite; `ZZ`-prefixed test vectors must not be presented as RA-attested |
| `XT` | Digital tokens (DTI, ISO 24165 / DTIF) | **Strong:** Guidelines V25 §§1/3.10 + footnote 6 (`XT` crypto-referential, Designated Numbering Agency, 3 hits) + ANNA identifiers `DTI ISO 24165 XT-ISIN` tab + isvalid.dev taxonomy (`XTV15WLZJMF0`, checksum-VALID verified). Absent from stdnum/floydspace/JonaMX snapshots (predate XT) + Apache permissive |
| `XA`, `XB`, `XC`, `XD` | Substitute agencies (CGS, NSD Russia, WM Datenservice, SIX) | **Strong:** Guidelines V25 §5 verbatim ("prefix XA, XB, XC or XD (XA used by CUSIP Global Services, XB by NSD Russia, XC by WM Datenservice Germany and XD by SIX…)") + python-stdnum comments + floydspace + Apache; ISO 3166 `XA–XZ` user-assigned |
| `XF` | Internally assigned, not-unique numbers | **Medium (validator practice):** python-stdnum comments + floydspace + Apache; ISO 3166 `XA–XZ` user-assigned; absent from Guidelines text |
| `XK` | Kosovo (user-assigned code) | **Medium-weak (single-curated):** python-stdnum only (+ Apache permissive); ISO 3166 `XA–XZ` user-assigned covers `XK`; absent from Guidelines/floydspace/JonaMX. Prior draft's "validator.js XK precedent (IBAN issue 2045 analogue)" is cross-capability analogy, not ISIN evidence — do not cite as ISIN attestation |
| `QS`, `QT` | Agency-internal (Euroclear France; Switzerland) | **Medium (validator practice):** python-stdnum comments + floydspace + Apache; ISO 3166 `QM–QZ` user-assigned covers both; absent from Guidelines text |
| `QW` | floydspace-internal | **Weak:** floydspace `PSEUDO` + Apache permissive + `QM–QZ` user-assigned only; no Guidelines/stdnum/JonaMX. Excluded from v1 (Open Decision §13#6) — wording corrected: two code sources but only one curated, no RA doc |
| Retired `CS`, `YU`, `SU`, … | Historical jurisdictions | stdnum `_iso` list retains `CS`/`AN`, JonaMX retains `CS`, Apache retains `CS/YU/SU` (back-compat); ISO 3166-3 formerly-used + 50-year reuse bar. Excluded from v1 (Open Decision §13#6) |

**Recommendation:** treat prefix validation as **always-active `LOOKUP_TABLE`** over `ISO 3166-1 ∪ {EU, XS, EZ, XT, XA, XB, XC, XD, XF, XK, QS, QT}` **plus provisional `ZZ` only with an explicit provisional flag/TODO**, or exclude `ZZ` from v1 until an RA/DSB cite is produced — the BIC §5.4 rationale as a Paxman design choice (not an ecosystem mandate: 4/8 validators check prefixes and they disagree; Apache's check is near-vacuous). Cost is a frozenset membership test; benefit is rejecting `XX`-style junk at `INVALID` instead of false `SUCCESS`. Snapshot lives in `rules/data/country_codes.py` (plain module-level frozenset, ISBN `range_message.py` pattern) with a documented refresh procedure keyed to Guidelines version (currently V25, superseded by V26) + DSB guidelines + ISO 3166-1/user-assigned ranges; the module docstring must record the per-prefix strength split above. Callers wanting raw structural validation only can `excluded_rules=["Section 5-country-and-special-prefix"]` — no flag proliferation needed for v1. A registry liveness layer stays deferred behind `requires_features={"include_registry_validation"}` if ever demanded (staleness concerns; determinism-by-snapshot preserved via `Provenance.version`).

### 5.5 Assignment / registration authority & Registry content

Network: **ANNA** (RA, Brussels) + **116 NNAs across 220+ jurisdictions per the TC68 briefing (2021 era; current ASB page: 120+ NNAs, 200+ jurisdictions, ~1M new ISINs/month)** (central securities depositories, exchanges, central banks, vendors, regulators), plus the **Derivatives Service Bureau (DSB)** as the single global numbering utility for OTC-derivative ISINs. Assignment rules (ISO/TC 68 briefing verbatim): securities other than debt → NNA where the issuer is incorporated/domiciled ("legally registered or … legal domicile"); debt securities → NNA of the place of deposit ("place of deposit"); no-NNA countries → designated substitute agencies (Guidelines V25 §5: `XA–XD`); OTC derivatives → free DSB registration ("free registration with the DSB").

Registry: the **ANNA Service Bureau** provides single-point access to global identifiers (ISIN, CFI, FISN) with a **free ISIN Lookup Service** for search/retrieval; the linked **LEI initiative** (ANNA–GLEIF) connects issuers to issues. Record content (per Annex B minimum descriptive data): ISIN, CFI classification, FISN short name, currency of trading, status, and related reference fields — far beyond Paxman's identity-only scope. Only official NNAs can issue valid ISINs; most do not charge for allocation (cost-recovery exceptions permitted under ANNA's RA obligations).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.capability_contract`, re-exported by `paxman.core.contract`) — never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base's `super()` pattern).

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class ISINContract(CapabilityContract):
    """User-facing contract for ISIN capability.

    Formats (ADR-0011 classes): ``grouped`` — encoding (whitespace
    insertion; re-enters under the default contract per ADR-0010).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isin"  # cf. IBAN "electronic" / BIC "bic"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped"})

    capability_name: str = field(default="isin", init=False)
    # No grammar-toggle flags for the initial single-grammar design.
    # If the registry liveness layer is ever added:
    # include_registry_validation: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For ISIN there is one always-active grammar,
    # so the property is omitted — base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For ISIN, `isin` (compact) is the machine canonical form; `grouped` is the human 2+6+3+1 rendering.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format` — `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`) in that order, then capability-specific params (if any — none for v1).

**Presentational-only invariant (hard rule — ARCHITECTURE.md §"The Formatting Seam"):**

- `output_format` is a **representation transform, never a recognition/validation signal**. Rules never read it; `normalize()` always returns compact; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup / status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance**.

For ISIN, the offered formats model the two interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"isin"` (default) | `US0378331005` / `GB0002634946` | Compact, uppercase, no separators — DB key, settlement-message payload, vendor-feed join key |
| `"grouped"` | `US 037833 100 5` | Space-grouped human display (`CC NNNNNN NNN C`), presentation-only Paxman convention (not spec-defined; cf. IBAN groups-of-four); whitespace tolerance in validators motivates but does not define the 2+6+3+1 grouping. ADR-0011 class: **encoding** (whitespace insertion, no information loss); a `grouped` rendering re-canonicalizes to its compact pre-image under the default contract (ADR-0010 re-entry) |

*Do not add a `with_label` format — the `ISIN` label is not part of the identifier; report renderers add it. Do not add an `nsin` format exposing the bare national number — that leaks a different identifier domain.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISIN.contract import ISINContract
from paxman.capabilities.ISIN.grammar.isin_recognition import ISINRecognitionGrammar
from paxman.capabilities.ISIN.notation import ISINNotation
from paxman.capabilities.ISIN.rules.anna_isin_guidelines_ed2025 import (
    Section5CountryAndSpecialPrefix,
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
            Section5CountryAndSpecialPrefix(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> ISINContract:
        return ISINContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
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
- **prefix-valid** — structural plus `country_code` ∈ ISO 3166-1 ∪ special-prefix snapshot (§5.4 strength table; Guidelines-attested `EU/XS/XA–XD/XT` + RA-attested `EZ` + validator/user-assigned `XF/XK/QS/QT` + provisional `ZZ`). Always-active LOOKUP_TABLE as a Paxman design choice (BIC §5.4 precedent), not an ecosystem mandate.
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
| 6 | Glued-label lookalike `IS0000000008` (Iceland `IS` + checksum-valid body) | `SUCCESS` if prefix rule accepts `IS` (it does — ISO 3166-1) | Lookahead does NOT fire — suffix after literal `ISIN` starts with a digit, so genuine `IS…` codes survive. (Prior draft's `ISIN03783100` is checksum-INVALID — `ISIN0378310` → `8` — do not use as a positive vector) |
| 7 | Over-long `US03783310055` (13) | `MISSING` for full run | Fixed-count quantifier + trailing `(?!\w)`; no partial claim of first 12 because position 13 is a word char |
| 8 | Under-long `US037833100` (11, calculator body) | `MISSING` | Terminal `[0-9]` after 9 alnum cannot bind; bodies alone never claimed |
| 9 | Letter check digit `US037833100X` | `MISSING` | Terminal class is `[0-9]`; no `X` analogue exists (unlike ISSN/ISBN-10/ORCID) |
| 10 | Bad checksum `US0378331003` | `INVALID` | Shape claimed; PARSER rule rejects via Luhn (stdnum doctest vector) |
| 11 | Invalid prefix `XX0378331005` / `ZZ0378331001` (checksum-valid isolations) | `INVALID` (with prefix rule active) vs false `SUCCESS` if excluded | LOOKUP_TABLE membership; exclusion path documented §14. (`ZZ` is provisional per §5.4 — its `INVALID` rests on the snapshot choice, not an RA cite) |
| 12 | Special prefixes `XS0931417173`, `EZ…` OTC, `XT…` token (`XTV15WLZJMF0` verified) | `SUCCESS` | Union set includes attested specials; per-prefix provenance §5.4 (`EZ` RA-attested outside Guidelines; `ZZ` provisional) |
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
| Unknown prefix (`XX0378331005`, junk `ZZ0378331001` — both checksum-valid isolations) | `INVALID` | LOOKUP_TABLE membership rejects (rule active by default). `ZZ` rejection is snapshot-provisional (no RA cite — §5.4) |
| Special prefix (`XS/EZ/XT/XK/QS/QT/XA–XD/XF/EU` + provisional `ZZ`) | `SUCCESS` | Union set membership per §5.4 strength table (Guidelines + RA + validator/user-assigned layers) |
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
"""ISO 3166-1 alpha-2 plus ANNA/validator special prefixes.

Refresh procedure: re-derive ISO 3166-1 alpha-2 from the OBP Country Codes
Collection plus ISO 3166 user-assigned ranges (AA, QM-QZ, XA-XZ, ZZ); re-derive
special prefixes from the current ANNA ISIN Guidelines (currently V25 Dec 2025,
superseded by V26 Jun 2026 — Guidelines text attests EU/XS/XA-XD/XT only) plus
the TC68 briefing / ANNA identifiers page for EZ (+ DSB guidelines for OTC) and
validator snapshots (python-stdnum 251-entry list, floydspace PSEUDO, JonaMX
244-entry list, Apache permissive 355-entry SPECIALS — the latter near-vacuous,
do not cite as tight-set support) for XF/XK/QS/QT (+ provisional ZZ, single
weak source). Record the Guidelines version + snapshot date in the rule's
Provenance.version. Never hand-edit entries without a source; ZZ stays
provisional until an RA/DSB cite is produced (or exclude from v1).
"""

ISO_3166_1_ALPHA_2: frozenset[str] = frozenset(
    {
        # ~249 official + user-assigned alpha-2 entries (snapshot)
    }
)

SPECIAL_PREFIXES: frozenset[str] = frozenset(
    {
        "EU",  # Guidelines V25 §2.2 + stdnum/floydspace/Apache
        "XS",  # Guidelines V25 §2.2 + stdnum/floydspace/JonaMX/Apache
        "EZ",  # RA-attested outside Guidelines: TC68 briefing + ANNA identifiers + DSB
        "ZZ",  # PROVISIONAL — no RA source; Apache permissive + ZZ user-assigned only
        "XT",  # Guidelines V25 §§1/3.10 + ANNA DTI page + isvalid (XTV15WLZJMF0 verified)
        "XA",
        "XB",
        "XC",
        "XD",  # Guidelines V25 §5 substitute agencies (CGS / NSD / WM / SIX)
        "XF",  # validator practice (stdnum/floydspace/Apache) + XA-XZ user-assigned
        "XK",  # single-curated (stdnum) + Apache + XA-XZ user-assigned
        "QS",  # validator practice (stdnum/floydspace/Apache) + QM-QZ user-assigned
        "QT",  # validator practice (stdnum/floydspace/Apache) + QM-QZ user-assigned
    }
)
```

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md §10 and shipped precedents)

- **Grammar tests** (`test_grammar.py`): valid compact (`US0378331005`); every §2.1 RECOGNIZE form as a positive vector (lowercase, inner-space groupings `US 037833 100 5` / `PL0000 503132` style, outer whitespace, label variants `ISIN:`/`isin -`, quoted/bracketed, embedded-with-annotation); multiple matches per text; incompatible formats (11-char body, 13-char run, letter check digit, hyphenated input, glued label, homoglyphs) return empty; empty input returns empty; span invariants (`raw_text == text[start:end]`, half-open bounds, label included in span); name/semantics conventions; boundary-guard negatives (`XUS0378331005`, `US0378331005Y`); Iceland lookalike positive (`IS0000000008`-shaped genuine `IS` code, 12 chars, checksum-valid, not blocked by lookahead — not `ISIN03783100`, which is checksum-INVALID).
- **Rule tests** (`test_rules.py`): PARSER rule — valid vectors (`US0378331005`, `AU0000XVGZA3`, `GB0002634946`, `XS0931417173` corrected, `XTV15WLZJMF0` verified), invalid checksum (`US0378331003`), transposed-letter flaw pair both accepted, letter-expansion edge (high-value letters Z=35 producing two-digit expansion), normalize exact compact, provenance attributes (authority ISO, lifecycle active, year 2021), name/strategy conventions, leading-zero NSIN preserved; LOOKUP_TABLE rule — valid prefixes (US, GB, XS, EZ, XK), invalid checksum-valid isolations (`XX0378331005`, `ZZ0378331001` — not the confounded `XX0000XVGZA3`/`ZZ0378331005`), `QW` rejected, normalize agreement with PARSER (identical compact output), strategy/provenance kind assertions.
- **Capability tests** (`test_capability.py`): notation frozen/hashable/slots, wiring counts (1 grammar, 2 rules), grammar/rule naming conventions, `format_value` round-trips (identity default, grouped `US 037833 100 5` exact string — each offered format re-enters under the default contract, ADR-0010), `create_contract` factory common block including `suppress_common_words` default `False`, contract immutability, invalid `output_format` raises `ContractError`.
- **Integration**: MISSING (no candidate runs, hyphenated, glued label) / INVALID (bad checksum, bad prefix) / SUCCESS (all surface variants coalesce) / AMBIGUOUS or `MultipleMentionsError` (two distinct ISINs); excluded-rules path (prefix rule excluded → structurally-valid junk resolves, documented false-positive posture); pinned_rules; year temporal filtering (year=2013 drops nothing material but exercises the filter); autouse `_clean_registry`; determinism/VersionStamp across repeated runs; span-bearing match integrity; candidate dedup of identical mentions.
- **Property tests (hypothesis)**: generate valid ISINs by picking a prefix from the union set + random alnum NSIN + computed check digit → must canonicalize to itself; random strings over `[A-Za-z0-9 ]` → overwhelmingly MISSING/INVALID with no crash; spaced vs compact inputs of the same payload yield identical canonical values; `format_value(grouped)` round-trip strips back to compact.
- **Consistency tests**: every shipped semantics covered by both rules' `target_semantics`; every special prefix exercised by at least one test vector; export completeness via `tests/unit/test_capability_exports.py`.
- **Presentation purity**: rules modules contain no presentation token (CI source scan passes).
- **Common-word suppression**: no-op by construction — the 67 `COMMON_WORDS` are at most 3 chars, so no fixed 12-char `[A-Z]{2}[A-Z0-9]{9}[0-9]` span can collide and the A0 whole-input exemption never triggers; the contract still exposes the inherited base `suppress_common_words` flag (default `False`), covered by a default-off assertion.
- **Real vectors (all checksum-verified via stdnum oracle 2026-09-20):** Apple `US0378331005`; Treasury Corp Victoria `AU0000XVGZA3`; BAE `GB0002634946`; stdnum doctest failure `US0378331003`; flaw pair `AU0000XVGZA3`/`AU0000VXGZA3`; international `XS0931417173` (not `...178`); token `XTV15WLZJMF0`; Poland `PL0000503132` spaced `PL0000 503132` (not `...135`) plus real Orlen `PLPKN0000018`; prefix-isolation invalids `XX0378331005` / `ZZ0378331001`. Do NOT use isvalid.dev vectors as valid: `PL0000503135`, `PL000PKN0RH16` (13 chars), `DE000A0MR4U4`, `XS1234567890` are all INVALID (correct: `PL0000503132`, `DE000A0MR4U0`, `XS1234567896`).

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT naming | `"isin"` (compact identity), offer `"grouped"` | Wire form is the machine key (IBAN `"electronic"`/BIC `"bic"` precedent); grouped display is the only attested alternative presentation |
| 2 | Single grammar vs N | Single `isin_recognition` initially; defer any hyphen-tolerant split to community extension with coalesced semantics | One lexical length; avoids cross-grammar containment spurious AMBIGUOUS |
| 3 | Prefix validation always-active vs gated | Always-active LOOKUP_TABLE; callers exclude via `excluded_rules` if they want structure-only | BIC §5.4 precedent verbatim: cheap set membership, rejects junk at INVALID instead of false SUCCESS; no flag proliferation |
| 4 | Grammar length strictness | Grammar enforces exactly 12 via fixed-count quantifier + terminal `[0-9]`; never 11/13 | All eight validators agree; keeps recognition cheap and definitive |
| 5 | Case/space normalization locus | Grammar folds case and strips single inter-character spaces; rules validate uppercase alnum only | Syntax-not-semantics boundary; multi-space Pre-collapse widening explicitly deferred (keeps v1 narrow, mirrors ISSN hyphen-strictness decision) |
| 6 | Special-prefix set composition | Include `{EU, XS, EZ, XT, XA–XD, XF, XK, QS, QT}` + provisional `ZZ` (or exclude `ZZ` from v1); exclude `QW` (floydspace + Apache permissive only, no RA doc) and retired `CS/YU/SU` | Per-prefix strength table §5.4: Guidelines text attests `EU/XS/XA–XD/XT` only; `EZ` RA-attested outside Guidelines; `XF/XK/QS/QT` validator + ISO-3166-user-assigned; `ZZ` provisional (no RA source) — prior draft's "≥2-source bar met for all" was overstated; Apache's retired codes serve back-compat, not live identification — revisit on demand |
| 7 | Publication split vs fuse | Two files (`iso_6166_ed2021.py` PARSER + `anna_isin_guidelines_ed2025.py` LOOKUP_TABLE); fuse rejected | Special prefixes come from RA policy, not the base standard's ISO 3166 reference; separate provenance lets each evolve on its own cadence |
| 8 | single_value for batch | True initially; segmentation recipe for multi-entity docs; optional community grammar with False later | Consistent with every shipped identifier capability |
| 9 | Hyphen tolerance | Reject in v1 (MISSING); DEFER to community `extra_grammars` Pre-stage | Zero code-level ecosystem tolerance (python-stdnum strips spaces only; `-` fails its alphabet check); documentary recommendation ≠ attested surface |
| 10 | Label span inclusion | Include label in `raw_text` span (fused regex), `notation.compact` label-free | Mirrors ISSN/ISBN/IBAN/BIC shipped behavior |
| 11 | Grouped-format definition | Fixed `CC NNNNNN NNN C` (2+6+3+1) rendering | Deterministic single choice; arbitrary regroupings would make `format_value` non-deterministic per caller taste — document as Paxman presentation convention like IBAN groups-of-four |
| 12 | Common-word suppression posture | Inherit base `suppress_common_words` (default off); no ISIN-specific suppression logic | No-op by construction: 67 `COMMON_WORDS` peak at 3 chars, so no 12-char fixed-shape span collides and the A0 whole-input exemption never triggers — the flag exists for surface homogeneity only |

---
## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent ISIN-vs-ISIN ambiguity.** One grammar, one lexical length, deterministic decomposition — the positional ambiguity Date exhibits (US vs European readings) has no analogue. Two distinct ISINs in one slice are authorial choice, handled by segmentation, not ambiguity resolution.
- **Unknown prefix is INVALID, not ambiguity.** `XX0378331005` (checksum-valid isolation) produces exactly one recognized value that one rule rejects — there is no competing canonical value. Without the prefix rule the same input falsely succeeds; that is a configuration consequence (documented §9 row 10), never a competing interpretation. (Prior draft's `XX0000XVGZA3` confounded checksum + prefix failure — do not use.)
- **Length discrimination prevents cross-capability confusion.** ISIN 12 vs BIC 8/11 vs LEI 20 vs IBAN 15–34 vs CUSIP 9/WKN 6/SEDOL 7 are pairwise disjoint; `word_only` guards eliminate inner carving from longer runs (LEI cannot yield a 12-window).
- **Presentation vs identity.** Lowercase, spacing, labels, and grouping collapse to one compact identity — dedup guarantees SUCCESS across variants; no format ever creates or destroys candidates (presentational-only invariant).
- **Staleness is not ambiguity.** A future ANNA amendment adding a prefix changes the data snapshot, not the pipeline; determinism-by-construction scopes results to a fixed snapshot with versioned provenance. The transposed-letter checksum weakness is likewise not ambiguity: both spellings resolve to themselves as distinct values; Paxman corrects nothing.

---
## 15. URL Reference (authoritative, fetched 2026-08-24)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 6166:2021 catalogue (Edition 8, 2021-02-02, 15 pp., stage 90.60) | https://www.iso.org/standard/78502.html | primary (fetched 2026-09-20 via webfetch) |
| ISO 6166:2013 catalogue (Edition 7, 2013-07-23, withdrawn — correct URL) | https://www.iso.org/standard/44811.html | primary (fetched 2026-09-20; prior draft's `59351.html` is 404) |
| ISO news: ISIN standard updated (TC 68/SC 8 secretariat SNV, scope + instrument types, no prefixes) | https://www.iso.org/news/ref2616.html | primary |
| ISO/TC 68 briefing "What is ISIN" (3 pp.: 12-char decomposition, EZ custom + DSB, 116 NNAs/220+ jurisdictions, substitute agencies, first publication 1986) | https://committee.iso.org/files/live/sites/tc68/files/Robin%20Doyle/What%20is%20ISIN-Final.pdf | primary (fetched + text-extracted 2026-09-20) |
| BSI BS ISO 6166:2021 (JS-gated — supersession corroborated via ISO links, not BSI text) | https://knowledge.bsigroup.com/products/financial-services-international-securities-identification-number-isin | mirror (title-only fetch 2026-09-20; do not cite for EZ/ZZ) |
| Serbian ISS RS stage 90.60 (effective 2026-06-05; 90.20 was 2026-01-15) | https://iss.rs/en/project/show/iso:proj:78502 | primary mirror |
| Genorma edition/stage corroboration (90.60, 15 pp., ICS 03.060, scope) | https://genorma.com/en/standards/iso-6166-2021 | secondary mirror |
| SIS product data (edition 8, 15 pages, replaces 2013) | https://www.sis.se/en/produkter/sociology-services-company-organization/finances-banking-monetary-systems-insurance/iso-61662021/ | primary mirror |
| Standard Norge history (1981/1983/1986/1987/1994/2001/2013/2021; no 1993) | https://online.standard.no/en/iso-6166-2021 | primary mirror |
| ANNA identifiers page (RA role, structure + EZ sentence, NNA table, XT-ISIN tab; now links V26 Jun 2026) | https://anna-web.org/identifiers/ | primary |
| ANNA ISIN Guidelines Version 25 Dec 2025 PDF (26 pp., HTTP 200) | https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf | primary (curl-fetched + text-extracted 2026-09-20; §5 XA–XD, §7 Annex C, §§1–2/3.10 XT/EU/XS; zero hits EZ/ZZ/QS/QT/QW/XK/XF) |
| ANNA ISIN Guidelines v21 June 2023 PDF (27 pp., HTTP 200; header reads "2022") | https://anna-web.org/wp-content/uploads/2023/06/ISIN-Guidelines-Version-21_June-2023.pdf | primary (curl-fetched + text-extracted 2026-09-20) |
| ANNA ISIN Guidelines Version 26 Jun 2026 (current) | https://anna-web.org/wp-content/uploads/2026/06/ISIN-Guidelines-Version-26-Jun-2026.pdf | primary (HTTP 200 HEAD 2026-09-20; supersedes V25) |
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
| isvalid.dev ISIN API + guides (strip logic + XT taxonomy ONLY — example vectors invalid, see below) | https://isvalid.dev/docs/isin (+ /guides/isin-validation-python, /guides/isin-validation-nodejs) | secondary (fetched 2026-09-20; code: Python `replace(" ","")`, Node `replace(/\s/g,'')`; `XTV15WLZJMF0` valid; `PL0000503135`/`PL000PKN0RH16`/`DE000A0MR4U4`/`XS1234567890` all INVALID — do not use as valid vectors) |
| regit-identifiers Rust check-digit docs (expanded-string weights) | https://docs.rs/regit-identifiers/latest/regit_identifiers/checkdigit/fn.isin_check_digit.html | secondary |
| Paxman conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary |
| Shipped precedents | paxman/capabilities/{IBAN,BIC,ISSN,ISBN,ORCID}/…, paxman/engine/orchestrator.py, paxman/core/domain.py, paxman/core/capability_contract.py | primary |

---
## 16. Evidence Completion — Resolved

This report's ISIN-specific authoritative evidence has been fetched and cited (2026-08-24; independently re-verified 2026-09-20 via webfetch/curl/raw-github + stdnum-oracle recomputation + PDF text extraction):
- [x] ISO catalogue entry: ISO 6166:2021 (8th ed., 2021-02-02, 15 pp., current, stage `90.60` Close of review 2026-06-05) revising 2013 Edition 7 (`44811.html`, 11 pp.; prior draft's `59351.html` was 404) plus 2001 (`33446.html`) and 1981/1983/1986/1987/1994 lineage (no 1993 edition; first publication 1986 per briefing); TC 68/SC 8 secretariat SNV; ICS 03.060; citation anchored to structure clause + normative Annex C (Guidelines V25 §7 verbatim; paywalled internal clause numbers still hedged)
- [x] RA and registry provenance: ANNA authority, ISIN Guidelines Version 25 Dec 2025 (`kind="policy"`, 26 pp., superseded by V26 Jun 2026) with PDF-extracted attestation split (Guidelines text: `EU/XS/XA–XD/XT`; `EZ` via briefing/identifiers/DSB; `XF/XK/QS/QT` validator + ISO-3166-user-assigned; `ZZ` provisional), Service Bureau/Lookup Service as deferred `kind="registry"` (ASB: 120+ NNAs, 200+ jurisdictions current vs briefing 116/220+ as-of)
- [x] Structure: 12 chars, `CC + NSIN(9) + C(1)`, zero-padded NSIN, strictly numeric check digit (briefing + identifiers + Guidelines §7 verbatim)
- [x] Checksum algorithm proved: modulus 10 Double-Add-Double (Luhn) over letter-expanded string `A=10…Z=35` with weights over the *expanded* string, worked examples US0378331005→5 and AU0000XVGZA3→3 verified against two independent walkthroughs plus eight implementations plus stdnum-oracle recomputation; transposed-letter flaw (`AU0000VXGZA3` also →3) documented; invalid guide vectors (`PL0000503135`, `XS0931417178`, `DE000A0MR4U4`, `XS1234567890`, 13-char `PL000PKN0RH16`) identified and corrected (`PL0000503132`/`PLPKN0000018`, `XS0931417173`, `DE000A0MR4U0`, `XS1234567896`)
- [x] Country nuance: ISO 3166-1 alpha-2 plus special prefixes with per-prefix strength (`EU/XS/XA–XD/XT` Guidelines-strong; `EZ` RA-medium; `XF/XK/QS/QT` validator-medium with `XK` single-curated; `ZZ` provisional-weak; `QW`/retired excluded) and corrected validator snapshot details (stdnum 251-entry + no `EZ/ZZ/XT`; floydspace no `EZ/ZZ/XK/XT`; JonaMX 244-entry + `XS` only; Apache 355-entry near-vacuous; 4/8 check prefixes at all)
- [x] Ecosystem regex consensus: eight validators extracted verbatim from raw sources (Python/JS/Java/PHP/TS) with strip-logic evidence for whitespace-only tolerance (no code-level hyphen tolerance)
- [x] Recognition-surface inventory complete (§2.1): nine attested forms with RECOGNIZE/DEFER/REJECT dispositions — no silently unhandled form (label tolerance noted as sibling-extrapolated design choice)
- [x] Wild input shapes validated (§2.2, 18 rows) against spec + RA pages + validators with checksum-valid isolations (`XX0378331005`, `ZZ0378331001`, `IS0000000008`)
- [x] Label scope decision (fused `[\s:-]+`, glued-label lookahead with Iceland-safe guard)
- [x] No branch/head-office equivalence question exists (unlike BIC XXX); no URN namespace (IANA registry fetched 2026-09-20: `issn`/`isbn`/`swift`/`lei` present, `isin` absent) and no resolver URI convention
- [x] Registry liveness scope decision (deferred behind requires_features)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ISSN, IBAN, BIC and ORCID Capabilities Teach ISIN (verbatim precedent)

> The following precedent is **sourced from the codebase as fetched 2026-08-24** (not speculative) and anchors the proposal to what Paxman already ships. Key excerpts verified in source: `paxman/capabilities/BIC/grammar/bic_recognition.py` (label `[\s:-]+` comment, `(?ai:)`, mirrored country frozenset, glued-label lookahead), `paxman/capabilities/IBAN/grammar/iban_recognition.py` (label + paper-alternative body, word_only guards), `paxman/capabilities/IBAN/notation.py` (country_code/check_digits/bban/compact decomposition), `paxman/engine/orchestrator.py` (`_dedup_spans`, `_validate_affinity`, `_enforce_single_value_invariant`), `paxman/core/domain.py` (`Rule.__init_subclass__` six enforced attributes), `paxman/core/capability_contract.py` (frozen-no-slots base, `resolve_output_format`, `active_grammars=None` default).

The five architectural lessons for ISIN:

1. **Grammar strips, rule validates, capability formats.** IBAN's `notation_fn` filters alnum + uppercases before any rule sees the token; ISBN's PARSER computes the check digit; `Capability.format_value` renders `paper` groups-of-four. ISIN copies all three seams verbatim with its own charset (`[A-Z]{2}[A-Z0-9]{9}[0-9]`) and its own grouped rendering (`CC NNNNNN NNN C`).

2. **One file per provenance, one class per section.** BIC ships `iso_9362_ed2022.py` + country lookup; ISBN ships three authorities in three files. ISIN ships two: `iso_6166_ed2021.py` (PARSER, structure+Luhn) and `anna_isin_guidelines_ed2025.py` (LOOKUP_TABLE, prefix vocabulary with per-prefix strength split per §5.4 — Guidelines-attested `EU/XS/XA–XD/XT` + RA-attested `EZ` + validator/user-assigned `XF/XK/QS/QT` + provisional `ZZ`) — because the special-prefix annex spans RA policy + validator practice, not base-spec content alone, and must carry its own evolving `Provenance.version`.

3. **No presentation tokens in rules, ever.** The CI source scan makes the formatting seam the only render path; `normalize()` returns bare compact for both ISIN rules so candidate dedup sees identical values regardless of which rule validated.

4. **Single grammar with fused optional label avoids spurious AMBIGUOUS; glued labels get a shape-aware negative lookahead.** BIC's shipped review note blocks `BICDEUTDEFF` fusion only when the suffix is a complete valid BIC — ISIN ports this so `ISINUS0378331005` goes MISSING while genuine Iceland `IS…` codes survive.

5. **Fixed-count quantifiers bound absorption risk.** Unlike IBAN's variable-length paper alternative (which motivated groups-of-four), ISIN's `(?: ?[A-Z0-9]){9} ?[0-9]` is count-bounded at 12 characters — whitespace tolerance cannot swallow trailing prose, so the simpler tolerant form is safe here.

---

*Report saved to `docs/development/research/` per MILESTONE guidance for ISIN (roadmap entry #17). It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md`. For implementation, start from the `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0, then fill the domain per §4–§7 above.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
