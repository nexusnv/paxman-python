# GTIN Canonicalization Research — paxman-python

**Date:** 2026-09-22
**Scope:** Primary-source survey of the Global Trade Item Number family (GTIN-8 / GTIN-12 / GTIN-13 / GTIN-14, UPC-A, EAN-13, EAN-8), the GS1 General Specifications (GenSpecs Release 26.0, Ratified Jan 2026), the GS1 check-digit system (GS1 Mod-10), GS1 Prefix / Company Prefix allocation and the Verified by GS1 registry, ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `GTIN` capability. No source code, tests, or configuration were modified.
**Evidence basis:** GS1 Global Office pages (`ref.gs1.org`, `gs1.org` services, standards log), GS1 Member Organisation pages (GS1 US `gs1us.org` GTIN/UPC/check-digit guides, GS1 UK `gs1uk.org` check-digit/GTIN hubs, GS1 Germany `gs1-germany/checkDigitCalculator`), GTIN Management Standard Release 1.1 (Sep 2023) and GTIN Rules decision-support, HRI Implementation Guideline, GSCN 21-271 (GTIN-8) and GSCN-25-351 Glossary (indicator digit), ecosystem libraries (`arthurdejong/python-stdnum` `stdnum/ean.py` + `stdnum/isbn.py` + `stdnum/util.py`, `validator.js` `src/lib/isEAN.js` + `isISBN.js` + `isISSN.js`, `GunCompare/gtin-validator`, `xbpf/gtin` incl. `upc-e.ts`, `marius103/gtin-checksum`, `aamirkhancr7/upc-barcode-validator`, `xlcnd/isbnlib` `_core.py`), taxonomy sites (Wikipedia GTIN and `gtin.info` as secondary only), and shipped Paxman capabilities (ISBN, ISSN, IBAN, BIC, Country, Phone) as architectural precedent. Repo state: `research/gtin-canonicalization @ 25b033a` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN research precedent `docs/development/research/2026-08-21-issn-canonicalization.md` plus the IBAN/BIC precedents `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md`.

**Identifiers:** `CapabilityName` → `GTIN`, export alias `GTINCapability`, `capability_name` → `gtin` registry name (lowercase, single-word so no `si_unit`-style underscore).

---

## Executive Summary

GTIN is a strong fit for a Paxman capability: it has an unambiguous canonical form (**14-digit zero-padded digit string**, e.g. `00614141999996`, digits only, check digit last), a stable single-publisher standard family (**GS1 General Specifications Release 26.0, Ratified Jan 2026**, publisher GS1 Global Office, rolling amendment via GSCN work requests) with GS1 Global Office plus ~115 Member Organisations as the allocation authority, a maintained authoritative prefix system (**GS1 Prefix / Company Prefix**, allocated per-MO ranges, plus the **Verified by GS1** lookup service as the liveness registry), and a well-understood human-readable presentation (**HRI under bars** `6 14141 99999 6` spaced groups and `(01)03453120000011` element-string form, presentation-only). The domain mirrors Paxman's value proposition for ISBN/ISSN/IBAN/BIC: recognizing tolerant human surface, validating strictly against authority, returning canonical compact value with provenance. Checksum sentence: every GTIN length carries a **GS1 Mod-10 check digit** (alternating weights 3/1 from the rightmost excluding the check digit, `(10 - sum % 10) % 10`), identical arithmetic to ISBN-13/EAN-13, and leading-zero padding to 14 digits preserves the check digit (verified computationally for 8→14, 12→14, and 13→14).

Key findings that shape the design:

1. **Canonical form is the 14-digit zero-padded GTIN.** Native lengths are 8/12/13/14 digits only (`^\d{8}$|^\d{12,14}$`), all numeric, last digit check. GS1 XML/GDSN mandates exactly 14 digits (`0` + GTIN-13, `00` + GTIN-12, `000000` + GTIN-8); GS1 US Data Hub displays and ingests GTINs as 14 digits with leading zeros. Padding is check-preserving for every length (weights are rightmost-anchored, so left padding never shifts existing digit distances). This mirrors the ISBN-10→13 expansion precedent: one canonical per entity, native length retained as a notation facet for the `native` offered format.
2. **One grammar suffices, with length alternation plus label/AI fusion.** Unlike ISBN which needs two grammars (ISBN-13 vs ISBN-10, separate semantics and `include_isbn10` gating), GTIN's four lengths are a single alternation `(\d{8}|\d{12,13,14})` with separator tolerance and optional `GTIN:/UPC:/EAN:` label plus optional `(01)` AI wrapper. A single `GTINRecognitionGrammar` with Regex strategy (plus Label-kind fusion for labels/AI) is correct. Splitting per length (`gtin8` + `gtin12` + …) would create cross-grammar containment (a 14-digit run contains 12/13-digit sub-runs) producing spurious `AMBIGUOUS` (longer-wins is per-grammar only, cross-grammar is preserved per `orchestrator:_recognize`).
3. **Validation is two-level plus optional registry, PARSER corroborated by LOOKUP.** Level 1 (always-active PARSER): length in `{8,12,13,14}`, ASCII digits only, GS1 Mod-10 check. Level 2 (always-active LOOKUP_TABLE): GS1 Prefix membership (first 3 digits in allocated MO ranges — the ISBN `Section 4.2-gs1-prefix` analogue, which also satisfies ADR-0012 corroboration so the PARSER candidate survives without vacuity pleading). Level 3 (gated registry, `include_verified=False` default): Verified by GS1 / Company Prefix liveness (determinism-by-snapshot only, never live lookup).
4. **UPC-E is a distinct symbology, not a length variant; ISBN-13 978/979 is dual-jurisdiction.** UPC-E 6–8-digit zero-suppressed forms expand to GTIN-12 only via Number-System rules with lossy compression (only `xbpf/gtin` implements `expand`/`compress`; stdnum, validator.js, GunCompare, gtin-checksum, upc-barcode-validator, and GS1 Germany all reject 6-digit input). Bare 6-digit runs must be REJECT/DEFER, never folded into the length gate. A `978…`/`979…` 13-digit string validates under both ISBN-13 and GTIN-13 arithmetic (stdnum delegates `isbn.validate` → `ean.validate` + prefix gate; isbnlib aliases `GTIN13 = ean13`); resolution is deterministic cross-capability precedence with both provenances cited, never by weakening either checksum.
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `GS1 General Specifications Release 26.0` (active, current) owns GTIN structure + Mod-10 check digit + indicator-digit semantics; `GS1 Prefix allocation` (rolling, MO-issued) owns prefix vocabulary; `Verified by GS1` (`kind="registry"`, rolling) owns liveness vs reference; `GTIN Management Standard Release 1.1` (Sep 2023) owns allocation/change rules (informative for edge-case rationale, not validity). No per-country table like IBAN, no checksum-free syntax like BIC.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---

## 1. Target User

| Persona | Why they need GTIN canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Retail / marketplace catalog engineers** | Normalize `590 1234 12345 7` vs `590-1234-12345-7` vs `05901234123457` to one 14-digit key for dedup, GTIN-exact matching, and Amazon/Google Shopping feed validation | Product ingestion, GDSN onboarding, marketplace listings, PIM/MDM mastering |
| **POS / inventory / WMS developers** | Validate scanned or hand-typed GTINs at receipt/shipment; reject transposed-digit and truncated input with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | Checkout, self-scan, warehouse receiving, stock counts, label reprints |
| **Data engineering / reconciliation teams** | Extract and canonicalize GTINs from free-text references, PDFs, emails, invoices, or scraped HTML with span-bearing provenance; join on the 14-digit canonical key | ETL pipelines, supplier-master cleanup, LLM extraction post-processing, price-benchmark joins |
| **Brand-owner / packaging operations** | Verify HRI proof copy (`6 14141 99999 6`, `(01)…`) against the Mod-10 check before plate-making; confirm prefix allocation and indicator-digit packaging level | Artwork QA, barcode verification (ISO 15416 grade is out of scope — digits only), case/pack hierarchy setup |
| **Risk / compliance / search teams** | Use GTIN as a stable trade-item key alongside ISBN/ISSN; detect duplicate items across spaced/hyphenated/AI-wrapped variants, including Bookland `978/979` dual candidates | Assortment rationalization, counterfeit screening, recall scoping, knowledge-graph product matching |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many GTIN mentions) and a contract; Paxman returns one canonical GTIN (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ISBN (`isbn13` bare-digit default) and ISSN ergonomics, but the canonical default is **14-digit zero-padded digits** (`00614141999996`), with `native` (length-preserved) and `hri` (space-grouped) as offered encodings.

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

From the Phase 1C survey (GenSpecs §1, HRI Guideline, GS1 US/UK guides, stdnum `clean(number,' -')`, validator.js strictness, GunCompare/xbpf/gtin-checksum/upc-validator guards, isbnlib aggressive strip). Digits are case-insensitive-trivially (no letters); the variation axes are length, separators, labels, AI wrappers, and padding.

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Compact native GTIN-8 | `96385074` | GenSpecs GTIN-8 definition; GS1 US what-is-a-gtin (8-digit structure); stdnum `ean.validate` length 8 | canonical (small-item POS) | RECOGNIZE | main length alternation branch `\d{8}` |
| Compact native GTIN-12 (UPC-A) | `614141999996` | GS1 US what-is-a-gtin (12-digit, UPC synonym); guide-to-upcs anatomy `6 14141 99999 6`; stdnum length 12 | canonical (NA POS) | RECOGNIZE | main alternation branch `\d{12}` |
| Compact native GTIN-13 (EAN-13) | `5012345670003` | GenSpecs; GS1 UK check-digit worked example; stdnum/isbnlib/validator.js length 13 | canonical (non-NA POS) | RECOGNIZE | main alternation branch `\d{13}` |
| Compact native GTIN-14 (case/pack) | `10614141999993` | GS1 US what-is-a-gtin (14-digit, never starts 0, NOT for POS); GSCN 21-271 composition | canonical (groupings) | RECOGNIZE | main alternation branch `\d{14}` |
| Zero-padded 14-digit equivalents | `00000096385074`, `00614141999996`, `05012345670003` | GS1 EDI/XML Item_Numbers table (`0 N1…N13`, `00 N1…N12`, `000000 N1…N8`; XML exactly 14); GS1 US Data Hub entry help (enter GTIN-13 with one leading zero, GTIN-12 as 14 with two) | official machine form | RECOGNIZE (canonical = 14-digit; native length kept as facet) | same 14-digit alternation branch; notation records `native_length` |
| Space-grouped HRI (UPC-A/EAN-8 anatomy) | `6 14141 99999 6`, `1234 5670` | GS1 US guide-to-upcs (`6 14141 99999 6` 1+6+5+1); barcode-types (`EAN-8 … two groups of four`) | official display | RECOGNIZE | separator-tolerant exact-length alternation (8/12/13/14 collapsed; 9/10/11 unmatchable), digit filter post-strip |
| Hyphen-grouped informal | `590-1234-12345-7`, `501-2345-67000-3` | stdnum `clean(number,' -')` deletes space+hyphen (direct evidence hyphens occur); upc-barcode-validator strips `\s` + `-` | common (informal; no normative hyphen spec unlike ISBN) | RECOGNIZE (strip; never emit) | same separator class `[ -]`; notation strips |
| AI-wrapped element string | `(01)03453120000011`, `(01) 03453120000011`, `AI 01 03453120000011` | HRI Guideline (`(01)…` parenthesised AI form; HRI = one-to-one illustration); DataMatrix guideline HRI example | official interchange | RECOGNIZE (strip `(01)`/`AI 01` marker) | optional `(?:\(01\)[\s:-]*\|AI\s+01[\s:-]+)` prefix fusion (Label-kind; bare `01` without parens or `AI` keyword is never an AI marker) |
| Label-prefixed prose | `GTIN: 00614141999996`, `UPC 614141999996`, `EAN-13: 5012345670003`, `GTIN-14 10614141999993` | stdnum/isbnlib label handling analogue; ISBN `ISBN:` fused-label precedent; marketplace `UPC:`/`EAN:` columns | common | RECOGNIZE (fused label `[\s:-]+`; span includes label) | optional `(?:GTIN(?:-1[2348])?\|UPC(?:-A)?\|EAN(?:-1[38])?)[\s:-]+` prefix, `re.IGNORECASE` |
| GDSN/API/EDI 14-digit field, spreadsheet text cells | `00196618007309` | GS1 US Data Hub help example; EDI/XML exactly-14 rule | official machine | RECOGNIZE | `\d{14}` branch (indistinguishable from padded; facet records 14) |
| UPC-E compressed (6-digit symbol / 8-digit HRI) | `012345` (symbol), `0 12345 6 7`-style HRI | GS1 US ean-vs-upc ("compressed version … suppressing the zeroes"); barcode-types ("6 digits … compact version"); GSCN 21-271 condensation note; `xbpf/gtin` `upc-e.ts` expand/compress | rare symbology, distinct | DEFER expansion in v1 (bare 6-digit symbol → MISSING, out-of-gate; 8-digit HRI collides with GTIN-8 length — claimed as an 8-digit run and validates as GTIN-8 iff Mod-10 passes, never expanded) | v1 length gate never 6; 8-digit collision explicitly admitted (no Number-System guard in v1); expansion via named `extra_grammars` candidate `upce_recognition` |
| Bars / quiet zones / guard bars / symbol check characters / images | — (non-text) | HRI Glossary (start/stop/shift/function + symbol check not shown in HRI); GS1 UK quiet-zone print requirement | non-data | REJECT (out of scope) | documented negative test; grammar is digit-string only |
| Truncated stems without check digit (7/11/12/13-digit payloads) | `61414199999`, `501234567000` | GS1 Germany `checkDigitCalculator` input regex (`^\d{7}$|^\d{11,12,13}$` without digit); GS1 US check-digit calculator (enter ID, tool computes last digit) | tool input, not a key | REJECT for recognition (offer generation as API direction only, out of v1) | length guard never 7/11; negative test |
| Bookland `978/979`-prefixed GTIN-13 | `9780471117094`, `9791092732113` | stdnum `isbn.compact` → `ean.validate` + `978/979` gate; isbnlib `GTIN13 = ean13` alias; ISBN Range Message | dual-jurisdiction | RECOGNIZE as GTIN-13 syntactically; DEFER precedence to ISBN capability (cross-capability guard) | same `\d{13}` branch; sibling-guard table (§4.4) |
| Coupon / extended-code and variable-measure `020–029` internal-use numbers | `0201234567890`-family | Secondary-only (Wikipedia/EAN internal-use note); GS1 prefix page does not confirm in fetched slice | unverified | REJECT coupons; DEFER variable-measure with flag (not globally unique) | Open Decision §13#11; confirm in GenSpecs §§1–2 before ruling |

A v1 that does NOT recognize hyphen-grouped or AI-wrapped forms must state that explicitly here AND raise it as an Open Decision (§13) — both are RECOGNIZE above, so no scope cut is taken. The deliberate cut is UPC-E (DEFER) and coupons/variable-measure (REJECT/DEFER).

### 2.2 Wild variants — adversarial mutations of each inventoried form

Enumerated from GenSpecs, GS1 US/UK pages, HRI Guideline, and real validators; stress-test every §2.1 RECOGNIZE form:

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical compact per length | `96385074`, `614141999996`, `5012345670003`, `10614141999993` | Spec master forms; length gate 8/12/13/14 exactly |
| 2 | Zero-padded 14-digit | `00000096385074`, `00614141999996`, `05012345670003` | Official storage; must collapse to same 14-digit canonical (idempotent) |
| 3 | Space-grouped HRI | `6 14141 99999 6`, `1234 5670`, `0 50123 45670 03`-style | Presentation-only; strip via digit filter, never emit spaces |
| 4 | Hyphen-grouped informal | `590-1234-12345-7`, `614141-999996` | No normative hyphen positions (unlike ISBN); strip `[ -]`, never emit |
| 5 | Mixed separators | `590 1234-12345 7`, `6-14141 99999-6` | Separator class must tolerate runs, not fixed positions |
| 6 | Label with colon/space/hyphen | `GTIN: 00614141999996`, `upc-614141999996`, `EAN 5012345670003`, `GTIN-14:10614141999993` | Case-insensitive label, `[\s:-]+`, span includes label; glued `GTIN006…` → MISSING (ISBN/BIC glued precedent) |
| 7 | AI-wrapped with spacing variants | `(01)03453120000011`, `(01) 03453120000011`, `AI 01 03453120000011` | Optional `(01)`/`AI 01` fusion (bare `01` without parens or `AI` keyword is never AI); span includes the marker; `AI 01` covered by the AI-prefix branch, not the label set |
| 8 | Space/hyphen runs (doubles) | `614141  999996`, `9638 5074` | `[ -]` tolerance; double spaces must not split into two mentions; tabs/newlines → MISSING in v1 (space/hyphen only, ISBN precedent) |
| 9 | Indicator-digit variants (GTIN-14) | `10614141999993` (1), `20614141999990`-family (2–8), leading-`0` padded vs leading-`1..8` true | `1–8` packaging levels distinct entities; leading `0` = padded shorter GTIN, never a true GTIN-14 (GS1 US: never starts 0); `9` reserved — still syntactically valid, registry-gated |
| 10 | With trailing annotation | `614141999996 (Wrigley's)`, `5012345670003 - lemon soda` | Must not swallow parenthetical/dash annotation; single span per GTIN |
| 11 | Multiple per line | `614141999996 / 5012345670003`, `UPCs: 614141999996, 96385074` | Two distinct → `AMBIGUOUS`/`MultipleMentionsError` with `single_value=True`; identical pair coalesces to `SUCCESS` |
| 12 | Quoted / bracketed / in URLs | `"614141999996"`, `[5012345670003]`, `(01)03453120000011.` | Inside punctuation allowed; trailing sentence period excluded from span |
| 13 | OCR / homoglyph / letter confusion | `61414199999O` (letter O), `501234567000B`, `l4141999996` | Strict ASCII digits only (`re.ASCII`, `isascii` + `isdigit`); no autocorrection, MISSING (grammar) or INVALID (rule) |
| 14 | Over-long / under-long | `6141419999` (10), `501234567000345` (15), `1234567` (7) | Length guard: never 6/7/9/10/11/15+; 13/14-digit runs are valid shapes (check digit decides, §2.2#16); truncated stems → MISSING |
| 15 | X-glued runs | `X614141999996`, `614141999996Y`, `9614141999996` (13-digit glue) | Word-boundary guards `(?<!\w)`/`(?!\w)`; longer digit runs must not carve inner GTINs |
| 16 | Wrong check digit (single transposition) | `614141999997` (last digit +1), `5012345670004` | Grammar claims (shape ok), PARSER rule rejects → `INVALID` |
| 17 | UPC-E compressed confusion | `012345` (6), `01234567` (8-digit HRI without context) | 6-digit symbol out-of-gate → `MISSING`; 8-digit HRI collides with GTIN-8 length — claimed as an 8-digit run, validates as GTIN-8 iff Mod-10 passes; never expanded without Number-System rules (DEFER to `upce_recognition`) |
| 18 | Bookland / sibling confusion | `9780471117094` (ISBN-13 ∩ GTIN-13), `9791092732113` | Both arithmetics pass; GTIN grammar claims; cross-capability precedence documented (§4.4, §14) |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| `arthurdejong/python-stdnum` `stdnum/ean.py` (fetched 2026-09-22) | `compact = clean(number,' -').strip()`; `calc_check_digit = str((10 - sum((3,1)[i%2]*int(n) for i,n in enumerate(reversed(number)))) % 10)`; `validate`: `isdigits (^[0-9]+$)` → `len in (14,13,12,8)` → checksum compare; returns length-preserved digits |
| `arthurdejong/python-stdnum` `stdnum/util.py` `clean()` | Unicode dash/space fold (~25 dash + ~16 space variants) then delete only chars in `deletechars`; `isdigits = ^[0-9]+$` (rejects Unicode digits) |
| `arthurdejong/python-stdnum` `stdnum/isbn.py` | `ean.validate(number)` then `number[:3] in ('978','979')` else `InvalidComponent`; proves shared arithmetic + prefix-gate disambiguation |
| `validator.js` `src/lib/isEAN.js` (fetched 2026-09-22) | `validEanRegex = /^(\d{8}\|\d{13}\|\d{14})$/` (12 excluded — divergence); length-parity left-to-right weights + `(10-(sum%10))` with `<10?r:0`; strict, no strip, boolean only |
| `validator.js` `src/lib/isISBN.js` (precedent) | `sanitizedIsbn = isbn.replace(/[\s-]+/g,'')`; ISBN-13 loop `factor=[1,3]`; no `978/979` gate (known-loose, do not copy) |
| `validator.js` `src/lib/isISSN.js` (precedent) | `^\d{4}-?\d{3}[\dX]$`, first-only `replace('-','')`, mod-11 weights 8..1 |
| `GunCompare/gtin-validator` `isValidStringLengthForGTIN.ts` + `isValidCheckDigitOnGTIN.ts` | `/^(\d{12,14}\|\d{8})$/` + `/^\d+$/` gate (no strip); reversed-array 3/1 loop + `(10-(sum%10))%10`; calc-input `/^(\d{11,13}\|\d{7})$/`; `removeGTINLeadingZeros…` strips `/^0{1,2}/` + `/^0{1}/`; `GTIN-${len}` label |
| `xbpf/gtin` `src/common.ts` + `src/index.ts` + `src/upc-e.ts` | `to13Digits = padStart(13,'0')` arithmetic; `isGTIN = /^(\d{12,14}\|\d{8})$/`; `minify()` zero-strips; `upc-e expand /^\d{6,8}$/` (last-digit 0-2/3-4/5-9 zero-run rules) / `compress /^\d{10,12}$/` (v1–v4 patterns); check on expanded 12-digit form |
| `marius103/gtin-checksum` `src/index.ts` | `GTIN_LENGTHS=[8,12,13,14]`; `/^\d+$/`; right-to-left 3/1 + `(10-(sum%10))%10`; `gtinVariant → 8\|12\|13\|14\|null` |
| `aamirkhancr7/upc-barcode-validator` `src/index.ts` | `replace(/\s/g,'')` + `replace(/-/g,'')`; lengths `[8,12,13,14]`; per-length loops (8/12/14: `3,1`; 13: `1,3` L-to-R); boolean only |
| `xlcnd/isbnlib` `_core.py` | `check_digit13: sum((i%2*2+1)*d)` → `10-(val%10)`; `canonical` keeps only `[0-9Xx]`; `is_isbn13` = len-13 + `978/979` + digit; explicit `GTIN13 = ean13` alias |
| `gs1-germany/checkDigitCalculator` `javascript/index.js` | `/(^\d{7}$)\|(^\d{11}$)\|(^\d{12}$)\|(^\d{13}$)\|(^\d{16}$)\|(^\d{17}$)/` (without-digit inputs incl. GTIN 7/11/12/13); reverse alt ×3/×1 + `ceil(sum/10)*10-sum`; demo vectors `0123456`, `06141415555`, `401234512345`, `0401234512345` |

**Normalization contract (reuse ISBN/ISSN pattern):**

```python
compact = re.sub(r"[ \-]", "", raw).upper()  # digits: upper() no-op, kept for pattern parity
# stdnum verbatim: clean(number, ' -').strip()  (Unicode dash/space fold underneath)
digits = "".join(ch for ch in match.group(0) if ch in "0123456789")
# then validate: len(digits) in (8, 12, 13, 14) + GS1 Mod-10 + prefix lookup
# then canonicalize: digits.rjust(14, "0")  (check-preserving, verified §7.1)
```

### 2.3 What input is NOT a GTIN mention

- UPC-E 6-digit compressed symbols without expansion context — `MISSING` (out-of-gate; DEFER to `upce_recognition` community extension). 8-digit UPC-E HRI is length-indistinguishable from GTIN-8: the grammar claims it as an 8-digit run (SUCCESS iff Mod-10 passes); Number-System expansion stays DEFERRED.
- Truncated stems without check digit (7/11/12-digit payloads) — `MISSING` (incomplete keys; generation direction only).
- Bar images, quiet-zone descriptions, guard-bar patterns, symbol check characters — out of scope (non-data symbol overhead).
- Coupon/extended codes and unconfirmed variable-measure `020–029` internal-use numbers — `MISSING` (coupons REJECT; variable-measure DEFER pending GenSpecs confirmation).
- Short runs (≤7 digits), SKUs, prices, phone fragments, dates — `MISSING` vs `INVALID` boundary is length-gated at the grammar (§9): no run of 8/12/13/14 ASCII digits with valid boundaries → `MISSING`; a claimed run failing Mod-10 or prefix → `INVALID`.
- ISBN-10 (10 digits, mod-11 with `X`) — never a GTIN length; `MISSING` for this capability (ISBN capability owns it).

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct GTINs (`614141999996 / 5012345670003`) → `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True`; identical values (including padded-vs-native spellings that normalize to the same 14-digit canonical) coalesce to `SUCCESS` via candidate dedup on `(value, recognition_rule, validation_rule)`.

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — digits plus native-length facet

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class GTINNotation:
    """GTIN intermediate token: cleaned digits plus native spelling facet.

    ``digits`` is the separator/label/AI-stripped ASCII digit run in its
    native length (8/12/13/14). ``native_length`` records which length was
    spelled (needed for the ``native`` offered format). ``has_ai`` records
    whether an ``(01)`` wrapper was present (traceability only).
    """

    digits: str
    native_length: int
    has_ai: bool
```

**Considered alternative — single field `digits` only:** a bare 14-digit-canonical notation would simplify rules (fixed width) but loses the native spelling needed for the `native` offered format and for Format-label diagnostics (`GTIN-8/12/13/14` per GunCompare/xbpf `getFormat`). It also makes padding idempotency untestable at the grammar layer (padded-vs-native inputs would be indistinguishable before rules). However the decomposition is preferred because (1) GS1 indexes semantics by length/format (POS vs grouping, UPC-A vs EAN-13 vs EAN-8 vs case), (2) the `native` format needs the spelled length, (3) indicator-digit vs pad-zero distinction (`1–8` true GTIN-14 vs leading-`0` padded) is a first-digit test on the 14-digit form but the audit trail should preserve what was spelled.

**Considered alternative — `format: Literal["gtin8","gtin12","gtin13","gtin14"]` discriminator:** equivalent to `native_length` but stringly; `int` is preferred (ISBN uses `shape` Literal because ISBN-10 has a distinct checksum alphabet with `X`; GTIN lengths share one Mod-10 alphabet so an int facet is leaner and avoids a four-way Literal).

**Invariants the grammar enforces (before rules):**

- `digits` is ASCII `0-9` only (separator/label/AI-stripped, `re.ASCII` + `isdigit` filter), length in `{8, 12, 13, 14}` exactly — never 6/7/9/10/11/15+.
- `native_length == len(digits)` and `native_length in (8, 12, 13, 14)`.
- `has_ai` is `True` only when the match consumed an `(01)`/`AI 01` wrapper; the wrapper digits (`01`) are never included in `digits`.
- `digits` preserves the spelled order including leading zeros (no zero-strip at recognition; padding is a rule-layer normalization).

### 3.2 Why not carry spaces, hyphens, labels, or AI wrappers in the notation

Spaces, hyphens, `GTIN:`/`UPC:`/`EAN:` labels, and `(01)` AI wrappers have **no lexical significance** for validity — the Mod-10 check runs on digits alone, and GS1 HRI spacings are print-layout groupings, not part of the key (HRI Guideline: HRI is a one-to-one illustration of encoded data; parentheses around AIs are delimiters, not data). Presentation is `Capability.format_value()` only (ISBN `_hyphenate` precedent; BIC grouped-display precedent).

### 3.3 Why `native_length` is not a shape discriminator literal

`native_length` is a free `int` validated by length membership in the PARSER rule, not a `Literal` — mirroring the ISBN `shape` vs GTIN distinction: ISBN needs `Literal["isbn10","isbn13"]` because the two shapes have different check alphabets (mod-11 with `X` vs mod-10); GTIN lengths share one alphabet and one check function, so the facet is a routing hint for the `native` format, not a validation branch. The LOOKUP_TABLE prefix rule ignores it (prefix test runs on the native digits for all lengths — never the zero-padded form — with a 4-char match for the GTIN-8 `9620–9624` exceptions).

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex vs Lexicon

Per HOW_TO_ADD_NEW_GRAMMAR.md, GTIN has a distinctive fixed-width numeric shape with finite length set and no vocabulary, so **Regex** is correct (Lexicon would need to enumerate 10^8–10^14 keys — absurd; Country `name_recognition` is the counter-example where recognizability *is* the vocabulary). UPC-A/EAN anatomy (`6 14141 99999 6`) is a spacing overlay on the same digit shape, not a vocabulary. Labels (`GTIN`/`UPC`/`EAN`) and the `(01)` AI are Label-kind fusions on the Regex core (ISSN `LabelMatcher` precedent; IBAN `LabelMatcher` with `reject` glued policy precedent).

### 4.2 Reference pattern (adapted from ISBN and ISSN verbatim precedent)

ISBN-13 precedent (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py:17`):

```python
_ISBN13_BODY = r"\b(?:ISBN(?:-13)?[\s:-]+)?(?=((?:\d[ -]?){12}\d)(?![\d]))\1"
_ISBN13_PATTERN = _ISBN13_BODY + r"(?![-]\d)\b"
```

ISSN precedent (`paxman/capabilities/ISSN/grammar/issn_recognition.py:40-49`): `LabelMatcher` with `labels=frozenset({"ISSN","ISSN-L","ISSN-H"})`, `separator=r"[\s:-]*"`, `glued_policy="allow"`, `pattern=r"\d{4}-?\d{3}[0-9Xx](?![-]\d)"`, `BoundarySpec.WORD`.

**Proposed GTIN pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.anchors import HasDigit
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.scan_context import ScanContext

# Labels carry digits (GTIN-14, EAN-13, …) and the AI marker carries digits
# ((01), AI 01), so whole-span digit-collapse would contaminate the notation
# (ISBN avoids this via match.group(1), unavailable to LabelMatcher emit
# which receives span+ctx). Strip the fused label and AI marker by regex
# before digit-collapse. AI is (01)-parens or AI-01-keyword ONLY — bare `01`
# without parens/keyword is never a marker (else leading-`01` bare GTINs
# dual-parse as AI+12 vs bare-14).
_GTIN_LABEL_RE = re.compile(
    r"^(?:GTIN(?:-1[2348])?|UPC(?:-A)?|EAN(?:-1[38])?)[\s:-]+",
    re.IGNORECASE | re.ASCII,
)
_GTIN_AI_RE = re.compile(
    r"^(?:\(01\)[\s:-]*|AI\s+01[\s:-]+)", re.IGNORECASE | re.ASCII
)


def _gtin_emit(span: tuple[int, int], ctx: ScanContext) -> GTINNotation:
    raw = ctx.text[span[0] : span[1]]
    body = _GTIN_LABEL_RE.sub("", raw, count=1)
    ai_match = _GTIN_AI_RE.match(body)
    has_ai = ai_match is not None
    if has_ai:
        body = body[ai_match.end() :]
    digits = "".join(ch for ch in body if ch in "0123456789")
    return GTINNotation(digits=digits, native_length=len(digits), has_ai=has_ai)

# Separator-tolerant EXACT-length alternation (collapsed 8/12/13/14;
# 9/10/11 unmatchable → MISSING, ISBN exactness precedent). Longest-first.
_GTIN_BODY = (
    r"(?:(?:\d[ \-]?){13}\d|(?:\d[ \-]?){12}\d|"
    r"(?:\d[ \-]?){11}\d|(?:\d[ \-]?){7}\d)(?![\-]\d)"
)

_GTIN_LABEL_MATCHER = LabelMatcher(
    labels=frozenset({"GTIN", "GTIN-8", "GTIN-12", "GTIN-13", "GTIN-14", "UPC", "UPC-A", "EAN", "EAN-8", "EAN-13"}),
    separator=r"[\s:-]+",
    glued_policy="reject",  # GTIN006… must not fuse (ISBN-13/BIC glued precedent)
    pattern=r"(?:\(01\)[\s:-]*|AI\s+01[\s:-]+)?" + _GTIN_BODY,
    flags=re.IGNORECASE | re.ASCII,
    boundary=BoundarySpec.WORD,
    anchors=HasDigit().as_set(),
    emit=_gtin_emit,
)

class GTINRecognitionGrammar(PipelineGrammar[GTINNotation]):
    """GTIN recognition: 8/12/13/14-digit runs with separators, labels, AI."""

    name = "gtin_recognition"
    semantics = "gtin_recognition"
    single_value = True
    pre = StandardPre[GTINNotation](empty_guard=True)
    matchers = (_GTIN_LABEL_MATCHER,)
```

*Notes on fidelity vs ISBN/ISSN/BIC:* module-scope matcher (compiled once, never per call); label/AI-strip then digit-collapse in emit (labels/AI carry digits, so whole-span collapse would contaminate); `re.ASCII` guard rejects non-ASCII digits (BIC `(?ai:)` + `isascii` precedent); exact-length alternation in-pattern (8/12/13/14 collapsed, longest-first; 9/10/11 unmatchable → MISSING — ISBN exactness precedent, decided per Open Decision §13#4; the rule re-enforces exact lengths as a safety net); `[\s:-]+` label separator with `reject` glued policy (IBAN/BIC precedent, vs ISSN `allow`); `(?![-]\d)` trailing guard blocks hyphen-digit continuation (ISBN-13/ISSN precedent); `BoundarySpec.WORD` blocks `X…`/`…Y` glues and 15+-digit carving (§4.4). **Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a pattern element (length branch → digit body; space/hyphen → `[ \-]?`; label → LabelMatcher labels; AI → `(01)`/`AI 01` prefix branch; padded-14 → `\d{14}` branch + facet); every DEFER/REJECT row names its mechanism (UPC-E 6-digit → length guard, 8-digit HRI collision admitted as GTIN-8 shape; bars/stems/coupons → length guard + negative tests).

**N vs M as one grammar vs four:** (Recommended) Single grammar with length alternation — avoids cross-grammar containment spurious AMBIGUOUS (a 14-digit run contains 12/13-digit sub-runs; longer-wins is per-grammar only per `orchestrator:_recognize`). Alternative (rejected): four grammars `gtin8/gtin12/gtin13/gtin14` with coalesced semantics — still emits four recognitions per 14-digit input before dedup scoping, tripping the single-value invariant.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)

- Grammar emits span-bearing `RecognitionMatch`, half-open `[start, end)`, `raw_text == text[start:end]` (enforced in `domain.py:RecognitionMatch.__post_init__`).
- `LabelMatcher`/`RegexStage` loops `re.finditer`, builds `RecognitionMatch`; stages must not mutate text.
- Engine owns within-grammar containment dedup (longer wins) and total recognition ordering (`_recognize`: total order `(start, end, active-set index, grammar name)`).
- Candidate dedup `(value, recognition_rule, validation_rule)` after validation (`_dedup_candidates`); padded-vs-native spellings of one entity dedup to one 14-digit value when both validate.

### 4.4 Guard boundaries against sibling grammars

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| GTIN | ASCII digits + `[ -]` separators + `():-` in label/AI only | `(?<!\w)` (WORD) | `(?!\w)` + `(?![-]\d)` |
| ISBN-13 | ASCII digits + `[ -]` + `ISBN` label | `(?<!\w)` | `(?!\w)` + `(?![-]\d)` |
| ISSN | `\d{4}-?\d{3}[\dX]` + `ISSN` label | `(?<!\w)` | `(?!\w)` + `(?![-]\d)` |
| Phone E.164 | `+` + digits + `[ -]().` | `(?<![\w:.])` | `(?!\w)` |
| ISIN/IBAN/LEI | alphanum fixed widths | `(?<!\w)` | `(?!\w)` |

GTIN vs ISBN-13 is length-plus-prefix discrimination (both 13-digit Mod-10; ISBN gates `978/979`, GTIN accepts all prefixes — a `978…` run is claimed by both grammars and resolved by cross-capability precedence, never by weakening either pattern). GTIN-8 (8 digits) vs ISSN (8 chars with hyphen/X) is charset discrimination (`X` never in GTIN). GTIN-12/14 vs IBAN (15–34 alphanum) vs ISIN (12 alphanum with letters) vs LEI (20 alphanum) is length/charset disjoint. UPC-E 6-digit never collides (v1 gate minimum 8).

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

- `semantics = "gtin_recognition"` identity id; all three shipped rules target it (`target_semantics=frozenset({"gtin_recognition"})`).
- Coalesce only if a second grammar lands (e.g. `upce_recognition` community extension declares the same `"gtin_recognition"` id so its expanded notations validate under the same rules; or declares its own id with dedicated rules — Open Decision §13#2).

### 4.6 `single_value` — one mention per call vs batch processing

Recommendation: `single_value=True` (shipped ISBN/ISSN/IBAN/BIC precedent). Two distinct GTINs in one slice → `AMBIGUOUS`/`MultipleMentionsError`; identical values (including padded-vs-native duplicates) coalesce via candidate dedup. Batch catalogs use the segmentation recipe (`docs/recipes/segmentation.md` ADR-0004). A free-text `extra_grammars` variant with `False` is possible but not v1.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | GS1 Global Office (Brussels/Lawrenceville), Member Organisations (~115 MOs incl. GS1 US, GS1 UK, GS1 Germany) |
| Registration Authority | GS1 Global Office (GS1 Prefix allocation) + Member Organisations (Company Prefix issuance, GTIN-8 individual assignment) |
| Spec name | GS1 General Specifications (GenSpecs) — GTIN definitions (§1), AI (01) 14-digit field, EAN/UPC symbology HRI figures, check-digit rules (§7.9 area per GS1 Germany refs) |
| Current edition | Release 26.0, Ratified, Jan 2026 (`ref.gs1.org/standards/genspecs`; log `gs1.org/standards/log`; GS1 UK v26 news) |
| Check character system | GS1 Mod-10, weights 3/1 from rightmost excl. check, `(10 - sum % 10) % 10` (GS1 global check-digit page + GS1 UK 5-step + GS1 US calculator) |
| Prefix reference | GS1 Prefix list (`gs1.org/standards/id-keys/company-prefix`: 030–039/060–139 GS1 US, 300–379 France, 400–440 Germany, 500–509 UK, 690–699 China, 880–881 Korea, 890 India, GTIN-8 ranges 960/961/9620–9624 UK) |
| Related specs | GTIN Management Standard Release 1.1 Ratified Sep 2023 (allocation/change rules); HRI Implementation Guideline (parenthesised `(01)` form); GSCN 21-271 (GTIN-8 composition); GSCN-25-351 Glossary (indicator 1–9); GS1 US Data Hub / EDI-XML Item_Numbers (14-digit storage rule) |

**Structure (GenSpecs §1 + GS1 US anatomy):** four numeric structures, check digit last: GTIN-8 (8, small-item POS, non-NA), GTIN-12 (12, UPC-A only, NA POS; anatomy `6 14141 99999 6` = Number System + Company Prefix + Item Ref + check), GTIN-13 (13, EAN-13 only, non-NA POS; Company Prefix + item ref + check), GTIN-14 (14, indicator `1–9` + Company Prefix + item ref + check; never starts `0`; NOT for POS; case/pack grouping). Charset digits only. Examples: `96385074`, `614141999996` (payload `61414199999` + check `6`), `5012345670003` (payload `501234567000` + check `3` per GS1 UK 5-step: 12→36, 21→57, C=3), `6291041500213` (payload sum 57 → check 3 per GS1 global page), `10614141999993` (indicator 1 over UPC-A base).

**Lineage table:**

| Edition / Event | Date | Status | Note |
|-----------------|------|--------|------|
| UPC standard selected (U.S. grocery, IBM Laurer design) | 3 Apr 1973 | Superseded (origin) | GS1 historical timeline + GS1 US guide-to-upcs; first scan 26 Jun 1974 Wrigley's gum, Troy Ohio |
| Uniform Code Council administers U.P.C. | 1974 | Superseded | Timeline ibid.; UCC as U.P.C. administrator |
| EAN established, barcode fully U.P.C.-compatible | 1977 | Superseded | Timeline ibid.; European Article Numbering Association |
| UCC + EAN merge → single GS1 (101 MOs) | 2005 | Superseded (harmonisation) | Timeline ibid.; 14-digit GTIN data model as post-merger harmonisation |
| GTIN Management Standard Release 1.1 | Sep 2023 | Active (allocation rules) | `documents.gs1us.org` PDF; net-content change → new GTIN; decision-support 3 guiding questions |
| Verified by GS1 (registry platform; replaces GEPIR 31 Dec 2023) | 2019 / 2023 | Active (registry) | Timeline + `gs1.org/services/verified-by-gs1`; 6 brand-owner attributes via GS1 US database page |
| GenSpecs Release 26.0 | Jan 2026 | Active (current) | `ref.gs1.org/standards/genspecs` + standards log + GS1 UK news; ratified |

**Citation Details Table (for Provenance):**

| Authority | Spec name | Version | Reference URL | Lifecycle | Publication year | Kind |
|-----------|-----------|---------|---------------|-----------|------------------|------|
| GS1 | GS1 General Specifications (GTIN structure + Mod-10 check + indicator) | Release 26.0 | `https://ref.gs1.org/standards/genspecs/` | active | 2026 | specification |
| GS1 | GS1 Prefix / Company Prefix allocation (MO ranges) | Rolling | `https://www.gs1.org/standards/id-keys/company-prefix` | active | 2026 | registry |
| GS1 | Verified by GS1 (GTIN liveness lookup) | Rolling | `https://www.gs1.org/services/verified-by-gs1` | active | 2019 | registry |
| GS1 | GTIN Management Standard (allocation/change rules) | Release 1.1 | `https://www.gs1.org/1/gtinrules/` | active | 2023 | specification |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|---------------|-------------------|
| `rules/gs1_genspecs_ed2026.py` | authority="GS1", specification_name="GS1 General Specifications", kind="specification", reference_url="https://ref.gs1.org/standards/genspecs/", version="26.0", lifecycle="active", publication_year=2026 | Section 1-gtin-structure-check-digit | Length 8/12/13/14 + ASCII digits + Mod-10 check (PARSER) |
| `rules/gs1_prefix_ed2026.py` | authority="GS1", specification_name="GS1 Prefix allocation", kind="registry", reference_url="https://www.gs1.org/standards/id-keys/company-prefix", version="Rolling 2026", lifecycle="active", publication_year=2026 | Section 2-gs1-prefix | MO-prefix membership on the native digits (3-digit; 4-char for GTIN-8 `9620–9624` exceptions; never the zero-padded form) (LOOKUP_TABLE) |
| `rules/verified_by_gs1_ed2019.py` | authority="GS1", specification_name="Verified by GS1", kind="registry", reference_url="https://www.gs1.org/services/verified-by-gs1", version="Rolling", lifecycle="active", publication_year=2019 | Section 3-verified-liveness | Snapshot membership (issued/live-registered), requires_features={"include_verified"} (LOOKUP_TABLE, gated) |

Each `Rule[GTINNotation]` subclass declares six enforced metadata attributes at class-definition time (`Rule.__init_subclass__` — `paxman/core/domain.py:246-271`):

```python
class Section1GtinStructureCheckDigit(Rule[GTINNotation]):
    name = "Section 1-gtin-structure-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 1 (GTIN structure + Mod-10 check digit)"
    target_semantics = frozenset({"gtin_recognition"})
    requires_features = frozenset()
```

Section numbers track the GenSpecs §1 structure area; confirm the exact check-digit subsection at plan time (GS1 Germany refs point near §7.9; the check-digit PDF is unparsed, §15) and rename to `Section X.Y-…` house style if needed.

### 5.3 What each rule does vs does not own

- `matches()` validates strictly, never raises, never reads `output_format` or `include_*` (CI purity scan); contract misconfigs caught in `contract.__post_init__`.
- `normalize()` returns the default 14-digit zero-padded form (`digits.rjust(14, "0")`), never reads `output_format`; identical across all three rules for the same notation so candidate dedup collapses (ISBN `normalize → digits` precedent, `paxman/capabilities/ISBN/rules/iso_2108_ed2017.py:44-45`).
- `RuleStrategy` choice: PARSER for structure/checksum (GenSpecs), LOOKUP_TABLE for prefix/registry (allocation + Verified). The always-active LOOKUP prefix rule corroborates the PARSER candidate on the same recognition (same grammar, span, notation object) per ADR-0012 — no vacuity pleading needed (ISBN §4.2 + §5.3 pair precedent).

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Ship generic Mod-10 + GS1 Prefix LOOKUP_TABLE as always-active (cheap set membership over ~3-digit MO ranges + short GTIN-8 exception ranges; single source of truth in `rules/data/gs1_prefix.py`, grammar projects nothing). Add Verified-by-GS1 LOOKUP_TABLE behind `include_verified=False` (snapshot-gated liveness: valid + prefix-valid vs issued/live-registered split, mirroring ISBN valid vs allocated, ISSN valid vs issued, IBAN valid vs country-valid). Rationale: prefix check kills random-digit false positives (`020…` unallocated, `999…` unassigned) without network; liveness stays deterministic-by-snapshot (live GEPIR/Verified lookup is network inference — forbidden). Cost: prefix table maintenance is a MO-range list (dozens of rows, yearly cadence), not a per-company database.

### 5.5 Assignment / registration authority & Registry content

Network: GS1 Global Office allocates GS1 Prefixes to Member Organisations; MOs issue Company Prefixes to brand owners (`support.gs1.org` obtain-a-prefix; `gs1.org/docs/barcodes/GSCN_15-258` entitlement quote); GTIN-8s individually assigned by MOs on request (`GSCN_15-039`). A Company Prefix entitles the member to create any GS1 key (GTIN/GLN/SSCC). Record includes Company Prefix + brand-owner identity + licensed GTIN range; cadence rolling (prefix list) / daily-monthly (directory files, BIC analogue). Mandatory registration data: prefix licensee, GTIN allocation per GTIN Management Rules (new-product / formulation / net-content / dimension triggers). Verified by GS1 exposes 6 brand-owner attributes (brand, description, image, GPC, net content, country of sale) — snapshot a boolean liveness subset only, never PII.

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract MUST inherit `CapabilityContract` (never `Contract` directly). `@dataclass(frozen=True)` without slots.

```python
from dataclasses import dataclass, field
from typing import ClassVar
from paxman.core.contract import CapabilityContract

@dataclass(frozen=True)
class GTINContract(CapabilityContract):
    """User-facing contract for GTIN capability.

    Attributes:
        capability_name: Fixed to "gtin" (not user-settable).
        output_format: Canonical output format ("gtin14" default, "native"
            and "hri" offered). Optional — None/"default"/"gtin14" all resolve
            to "gtin14" via ``CapabilityContract.__post_init__``.
        include_verified: Gate the Verified-by-GS1 liveness rule (default
            False). When True, adds issued/live-registered provenance via
            Section 3-verified-liveness.

    Formats (ADR-0011 classes): ``native`` — same-entity reversible pad-strip pair
    (length-preserved digits; padding zeros reversible via notation facet,
    re-entry recovers the 14-digit pre-image exactly); ``hri`` — encoding
    (space-grouped HRI layout; separators presentation-only).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "gtin14"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"native", "hri"})

    capability_name: str = field(default="gtin", init=False)
    include_verified: bool = False
```

- `DEFAULT_OUTPUT_FORMAT` concrete `"gtin14"`, `OFFERED` excludes default, resolved via `resolve_output_format`, `create_contract()` fixed keyword-only common block then `include_verified`.
- Presentational-only invariant: `normalize()` always 14-digit; `format_value()` renders; rules never read `output_format`.

> `_group_hri(value, native_length)` (called by `format_value` in §6.2) is unspecified in v1 research: only the UPC-A grouping `6 14141 99999 6` is attested. The plan must either confirm the EAN-13/EAN-8/GTIN-14 groupings from GenSpecs/HRI (never invent them) or defer the `hri` format (contract `OFFERED` shrinks to `{"native"}`).
- For GTIN, offered formats model the interchange forms:

| output_format | Value example (for `00614141999996`) | Meaning |
|---------------|---------------------------------------|---------|
| `gtin14` (default) | `00614141999996` | 14-digit zero-padded storage form (GS1 XML/GDSN) |
| `native` | `614141999996` | Length-preserved digits as spelled (facet `native_length`) |
| `hri` | `6 14141 99999 6` (12-digit branch, attested §5.1) | Space-grouped HRI layout (encoding; per-length groups beyond UPC-A illustrative only — confirm EAN-13/EAN-8/GTIN-14 groupings from GenSpecs/HRI at plan time, see `_group_hri` note below) |

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from collections.abc import Sequence
from paxman.capabilities.GTIN.contract import GTINContract
from paxman.capabilities.GTIN.grammar.gtin_recognition import GTINRecognitionGrammar
from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.capabilities.GTIN.rules.gs1_genspecs_ed2026 import Section1GtinStructureCheckDigit
from paxman.capabilities.GTIN.rules.gs1_prefix_ed2026 import Section2Gs1Prefix
from paxman.capabilities.GTIN.rules.verified_by_gs1_ed2019 import Section3VerifiedLiveness
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

class GTINCapability(Capability[GTINNotation]):
    """GTIN canonicalization capability (GS1 GenSpecs 26.0 + Prefix + Verified)."""

    name = "gtin"

    def get_grammars(self) -> list[Grammar[GTINNotation]]:
        return [GTINRecognitionGrammar()]

    def get_rules(self) -> list[Rule[GTINNotation]]:
        return [Section1GtinStructureCheckDigit(), Section2Gs1Prefix(), Section3VerifiedLiveness()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
        include_verified: bool = False,
    ) -> GTINContract: ...

    def format_value(self, value: str, output_format: str | None, notation: GTINNotation) -> str:
        if output_format == "native":
            pad = 14 - notation.native_length
            return value[pad:] if 0 < pad <= 6 else value
        if output_format == "hri":
            return _group_hri(value, notation.native_length)
        return value
```

Registration via `tools/new_capability.py`:

```bash
uv run python tools/new_capability.py GTIN --name gtin --authority "GS1" --spec-name "GS1 General Specifications" --spec-url "https://ref.gs1.org/standards/genspecs/" --publication-year 2026 --default-format gtin14
```

> Note: scaffolder single `--spec-name` covers GenSpecs only. After scaffolding, add `gs1_prefix_ed2026.py` and `verified_by_gs1_ed2019.py` manually (fused-vs-split: recommend split for per-publication purity, §13#7).

---

## 7. Validation — three levels

### 7.1 Level 1 Generic structure + Mod-10 (always-active PARSER)

Formal regex (ASCII, exact lengths): `^(?:\d{8}|\d{12}|\d{13}|\d{14})$` (validator.js `^(\d{8}|\d{13}|\d{14})$` is the known-narrow variant excluding 12 — do not copy; GunCompare `^(\d{12,14}|\d{8})$` is the correct shape).

Algorithm (GS1 global page + GS1 UK 5-step, quoted verbatim in §2.2 sources):

```python
def _gs1_mod10_is_valid(digits: str) -> bool:
    """GS1 Mod-10 over full digit string (last digit is check)."""
    if len(digits) not in (8, 12, 13, 14) or not digits.isascii() or not digits.isdigit():
        return False
    payload, check = digits[:-1], digits[-1]
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(payload)))
    return str((10 - total % 10) % 10) == check
```

Worked examples (all verified by executing the quoted algorithm in this worktree):

| Format | Payload → check (computed) | Full value | Basis |
|--------|----------------------------|------------|-------|
| GTIN-13 | `629104150021` → **3** | `6291041500213` | Quoted GS1 global example (sum 57 → 60−57) |
| GTIN-13 | `501234567000` → **3** | `5012345670003` | Quoted GS1 UK 5-step (12→36, 21→57, C=3) |
| GTIN-12 | `61414199999` → **6** | `614141999996` | Payload/check split of GS1 US anatomy `6 14141 99999 6` |
| GTIN-14 | `0345312000001` → **1** | `03453120000011` | Payload/check split of HRI `(01)03453120000011` |
| GTIN-8 | `9638507` → **4** | `96385074` | Computed illustration of quoted algorithm |
| GTIN-14 | `1061414199999` → **3** | `10614141999993` | Indicator-1 over UPC-A base, computed |
| Padding | `5012345670003` → `05012345670003` | both valid | Zero-pad invariance verified (8→14, 12→14, 13→14 all preserve check) |

Letter-conversion table: N/A (digits only — unlike IBAN `A=10…Z=35`, there is no alphanumeric expansion; `X` never appears unlike ISSN/ISBN-10).

Generation vs validation direction: GS1 documents generation (payload → check; GS1 US calculator: enter ID, tool computes last digit). The Paxman rule implements validation (recompute over first n−1, compare to last); equivalently `weighted-sum-plus-check ≡ 0 (mod 10)` per the quoted Step 5 ("smallest number … to reach a multiple of 10").

### 7.2 Level 2 GS1 Prefix membership (always-active LOOKUP_TABLE)

MO-prefix test on the native digits — never the zero-padded 14-digit form (a padded spelling tests the same native prefix: `05012345670003` tests `501`, not `050`). Match 3 digits generally, 4 chars for the GTIN-8 `9620–9624` exceptions. Working subset (confirm the full list — including `000–019`/`006` allocation — at plan time; three gs1.org fetches were 403/WAF, §15): `030–039`/`060–139` US, `300–379` France, `400–440` Germany, `450–459`/`490–499` Japan, `500–509` UK, `754–755` Canada, `840–849` Spain, `880–881` Korea, `890` India, `690–699` China, GTIN-8 exception `960/961/9620–9624` UK (`gs1.org/standards/id-keys/company-prefix`) — e.g. `5012345670003` tests `501` → GS1 UK. Rationale for always-active: kills random-digit false positives at set-membership cost, mirrors BIC country-valid and ISBN `978/979` prefix layers, and corroborates the PARSER per ADR-0012.

Indicator-digit note (GTIN-14 N1): `1–8` packaging levels distinct entities; leading `0` = padded shorter GTIN (GS1 US: true GTIN-14 never starts 0); `9` reserved — syntactically valid at Levels 1–2, registry-gated at Level 3.

### 7.3 Level 3 Verified liveness (gated LOOKUP_TABLE, `include_verified`)

Snapshot boolean: padded-14 in issued set. Gated via `requires_features={"include_verified"}` (BIC directory / ISBN Range Message / Country CLDR precedent). Disabled → rule dropped → input stays `SUCCESS` via Levels 1–2 (not `INVALID`); enabled + absent → `INVALID` (authority feature gating locus, §4.5 of HOW_TO).

### 7.4 What makes GTIN "valid" vs "prefix-valid" vs "issued/live-registered"

- **valid (generic)** — correct length/charset/Mod-10, always-active PARSER (like ISBN valid, ISSN valid, IBAN valid).
- **prefix-valid** — generic plus GS1 Prefix in allocated MO ranges, always-active LOOKUP_TABLE (like BIC country-valid, ISBN `978/979` prefix).
- **issued/live-registered** — actually present in Verified-by-GS1 snapshot, gated registry (like ISBN allocated, ISSN issued, IBAN country-valid vs live-registered split).

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase label (`gtin: 00614141999996`) | SUCCESS → `00614141999996` | Label case-insensitive (`re.IGNORECASE`); digits case-trivial |
| 2 | Space-grouped HRI (`6 14141 99999 6`) | SUCCESS (same 14-digit) | Presentation-only; digit-collapse + pad |
| 3 | Hyphen-grouped (`590-1234-12345-7`) | SUCCESS (same 14-digit) | Informal separators stripped; never emitted |
| 4 | AI-wrapped (`(01)03453120000011`) | SUCCESS, span includes `(01)` | Fused AI prefix; notation `has_ai=True`, digits AI-free |
| 5 | Label present (`UPC 614141999996`) | SUCCESS, span includes label | Fused label `[\s:-]+`; notation label-free |
| 6 | Zero-padded vs native duplicate in one slice | SUCCESS (single 14-digit, deduped) | Same canonical via `rjust(14)`; candidate dedup collapses |
| 7 | True GTIN-14 vs padded GTIN-13 (`10614141999993` vs `05012345670003`) | Both SUCCESS, distinct values | Indicator `1` vs pad `0` — different entities, not coalesced |
| 8 | Over-long (`501234567000345`, 15 digits) | MISSING | Length guard; WORD boundary + no carving |
| 9 | Under-long / truncated stem (`61414199999`, 11) | MISSING | Incomplete key; generation direction only |
| 10 | UPC-E 6-digit symbol (`012345`) | MISSING | Out-of-gate (v1 minimum 8); expansion DEFERRED to `upce_recognition`. 8-digit UPC-E HRI collides with GTIN-8 — claimed as an 8-digit run, validates iff Mod-10 passes (never expanded in v1) |
| 11 | Invalid Mod-10 (`614141999997`) | INVALID (PARSER rejects) | Structural failure; `had_recognitions` true so not MISSING |
| 12 | Unallocated prefix (`99914141999993`-family) | INVALID (LOOKUP rejects) | Prefix membership claimed by LOOKUP rule |
| 13 | Non-ASCII digits (`６１４１４１９９９９９６` full-width) | MISSING | `re.ASCII` + `isascii`; no Unicode-digit acceptance (stdnum `isdigits` precedent) |
| 14 | Embedded in sentence (`Batch 614141999996 shipped.`) | SUCCESS with span | WORD guards; trailing period excluded |
| 15 | Two distinct in one slice (`614141999996 / 5012345670003`) | AMBIGUOUS / MultipleMentionsError | Segmentation intended; single-value invariant |
| 16 | Glued label (`GTIN00614141999996`) | MISSING | Glued `reject` policy (ISBN-13/BIC precedent) |
| 17 | Bookland dual (`9780471117094`) | SUCCESS (GTIN-13 syntactically; ISBN precedence documented) | Same arithmetic, different authority; cross-capability guard, never weakened checksum |
| 18 | Bars/quiet-zone/image-only (no digit run) | MISSING | Non-data symbol overhead; digit-string scope only |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid generic + prefix-valid (`614141999996`, `5012345670003`, `(01)03453120000011`) | SUCCESS → 14-digit (`00614141999996`, `05012345670003`, `03453120000011`) | Single canonical via GenSpecs + Prefix lookup |
| Valid variant spacing/case/label/AI | SUCCESS (same 14-digit) | Presentation-only dedup (separators/labels/AI stripped) |
| Wrong check digit / unallocated prefix | INVALID | Structural failure, PARSER/LOOKUP rejects; `had_recognitions` true |
| No 8/12/13/14-digit run (short text, UPC-E 6-digit symbol, 7/9/10/11-digit stems, bars) | MISSING | Exact-length alternation leaves 6/7/9/10/11 unclaimed; WORD guards block carving |
| Two distinct valid in one slice | AMBIGUOUS / MultipleMentionsError | Single-slice ambiguity, segmentation recipe |
| Padded-vs-native duplicates (same entity) | SUCCESS (one value, deduped) | Same 14-digit via `rjust`; candidate dedup collapses |
| Indicator `1–8` GTIN-14 | SUCCESS | Distinct packaging-level entities, Levels 1–2 pass |
| Verified-gated input (`include_verified=True`, absent from snapshot) | INVALID | Authority feature gating (dropped-rule locus inverted: rule runs and rejects) |
| `978/979` Bookland dual | SUCCESS (GTIN-13 syntactically) | Dual jurisdiction; ISBN precedence is cross-capability, not INVALID here |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py GTIN --name gtin --authority "GS1" --spec-name "GS1 General Specifications" --spec-url "https://ref.gs1.org/standards/genspecs/" --publication-year 2026 --default-format gtin14
```

Creates 13 files + one edit: `paxman/capabilities/GTIN/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single `--spec-name` covers GenSpecs only. After scaffolding, add `gs1_prefix_ed2026.py` + `verified_by_gs1_ed2019.py` manually (split for per-publication purity) and `rules/data/gs1_prefix.py` MO-range table.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[GTINRecognitionGrammar()]`; `active_grammars` omitted for initial design (base `None` runs every shipped grammar).
- Each grammar carries `name="gtin_recognition"` and non-empty `semantics="gtin_recognition"` (identity id; `Grammar.__init_subclass__` enforced, `paxman/core/domain.py:246+` analogue for grammars).
- `get_rules()` returns the three Section rules above in publication order (GenSpecs → Prefix → Verified).
- `create_contract()` opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`) then `include_verified: bool = False`.

### 10.3 Cross-cutting invariants (fail review if violated)

- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports (import only from `paxman.core`, import-linter enforced) — especially no `from paxman.capabilities.ISBN…` for the shared Mod-10 helper (duplicate the 5-line function; ISBN `Section 4.2-gs1-prefix` duplication precedent is intentional per audit B3).
- No `output_format` token in any `paxman/capabilities/*/rules/` module (source-scan `tests/unit/test_rule_output_format_purity.py`).
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts (base `super().__post_init__` pattern).
- Deterministic by construction: same input + contract + library snapshot → same output (no live Verified lookup, no clock, no world knowledge).
- ADR-0012: PARSER corroborated by always-active LOOKUP (no vacuity); ADR-0011: `native` (same-entity reversible pad-strip pair) + `hri` (encoding) classified in contract docstring + preservation matrix rows; ADR-0010: re-entry suite extended (`00614141999996` re-enters; `native`/`hri` renderings re-enter to the 14-digit pre-image under the default contract).

---

## 11. Recommended File Layout (mirrors ISSN and IBAN)

```text
paxman/capabilities/GTIN/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── gtin_recognition.py
└── rules/
    ├── __init__.py
    ├── gs1_genspecs_ed2026.py
    ├── gs1_prefix_ed2026.py
    ├── verified_by_gs1_ed2019.py
    └── data/
        ├── __init__.py
        └── gs1_prefix.py
```

Per-registry data module shape (parallel to ISBN `rules/data/range_message.py`):

```python
# rules/data/gs1_prefix.py
"""GS1 Prefix MO ranges (projection of gs1.org company-prefix list)."""
GS1_MO_RANGES: tuple[tuple[int, int, str], ...] = (
    (30, 39, "GS1 US"),
    (60, 139, "GS1 US"),
    (300, 379, "GS1 France"),
    # … full list per §7.2 …
)
GS1_GTIN8_EXCEPTIONS: frozenset[str] = frozenset({"960", "961", "9620", "9621", "9622", "9623", "9624"})
```

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- Grammar tests: valid compact per length (8/12/13/14), padded-14, space-grouped HRI, hyphen-grouped, label variants (`GTIN:`/`UPC`/`EAN-13:`), AI-wrapped `(01)`, irregular whitespace, multiple matches, incompatible formats (6/7/9/10/11/15 digits, glued label, full-width digits, bars-only), empty, span invariants (`len(raw_text)==end-start`, label/AI included in span), `name`/`semantics`/`single_value`, WORD-boundary negatives — plus one positive vector per §2.1 RECOGNIZE form.
- Rule tests: GenSpecs PARSER valid per length / wrong-check / wrong-length / non-ASCII / `normalize` exact 14-digit pad, provenance attributes (`authority="GS1"`, `kind="specification"`, `version="26.0"`), `name`/`strategy` conventions; Prefix LOOKUP valid on native digits (`501…`→UK; native GTIN-12/8 prefixes per the confirmed full list, §7.2) / unallocated (`999…`) / `normalize` agreement / `strategy=LOOKUP_TABLE` / `kind="registry"`; Verified LOOKUP membership hit/miss, `requires_features={"include_verified"}` gate, `kind="registry"`.
- Capability tests: notation frozen/hashable/slots (`GTINNotation("00614141999996", 12, False)`), wiring counts (1 grammar, 3 rules), grammar/rule name conventions, `format_value` round-trips (`gtin14` identity, `native` strip via facet, `hri` grouping), `create_contract` factories.
- Integration: MISSING (no run, UPC-E 6, stems, glued label) / INVALID (bad check, bad prefix, verified-gated miss) / SUCCESS (all §2.1 RECOGNIZE forms → one 14-digit) / AMBIGUOUS or MultipleMentionsError (two distinct), prefix gating always-on, `_clean_registry` fixture, determinism/VersionStamp, span-bearing match, padded-vs-native dedup.
- Property tests (hypothesis): generate valid by payload + `calc_check_digit` → must canonicalize to `rjust(14)` self; random digit strings → INVALID with high probability (≈90% wrong check + prefix miss); grouped vs compact identical; `format_value` round-trip (`native`/`hri` re-enter to 14-digit under default contract).
- Consistency test: every shipped semantics (`gtin_recognition`) covered by `Rule.target_semantics`; every MO-range prefix exercised (§7.2 table).
- Presentation purity: `output_format` source scan over `rules/`.
- Real vectors: `96385074`, `614141999996`, `5012345670003`, `6291041500213`, `10614141999993`, `03453120000011`, `6 14141 99999 6`, `590-1234-12345-7`, `(01)03453120000011`, `GTIN: 00614141999996`, `9780471117094` (dual), `614141999997` (bad check), `012345` (UPC-E MISSING).

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `gtin14` vs `native` | `gtin14` (14-digit zero-padded), `native` + `hri` offered | GS1 XML/GDSN exactly-14 storage rule + Data Hub display; one canonical per entity (ISBN-10→13 expansion precedent); `native` preserves spelling via facet |
| 2 | Single grammar vs per-length grammars | Single `gtin_recognition` initially, length alternation; UPC-E split deferred to `upce_recognition` community extension with same or new semantics | Keeps surface minimal, avoids cross-grammar containment spurious AMBIGUOUS (14 contains 12/13 sub-runs) |
| 3 | Prefix lenience vs strict | Ship GenSpecs PARSER + Prefix LOOKUP_TABLE as always-active; Verified LOOKUP_TABLE behind `include_verified=False` | Mirrors valid vs prefix-valid vs issued split; cheap set membership; no network |
| 4 | Grammar length strictness | Exact-length alternation in-pattern (separator-tolerant 8/12/13/14 collapsed, longest-first; 9/10/11 unmatchable → MISSING); rule re-enforces exact lengths as a safety net | ISBN exactness precedent; truncated stems stay MISSING per §2.3/§8#9/§9 — cover the 9/10/11-unclaimed negative tests |
| 5 | Case/space normalization in grammar vs rule | Grammar strips separators/labels/AI and preserves spelled digits + facet; rules validate digits only + pad in `normalize()` | Syntax (stripping) vs semantics (check/prefix/pad); digits case-trivial |
| 6 | Indicator-digit `9` + leading-`0` GTIN-14 | Syntactically valid at Levels 1–2, registry-gated at Level 3; leading-`0` 14-digit = padded shorter GTIN, never true GTIN-14 | `9` reserved but not check-relevant; GS1 US never-starts-0 is packaging-level semantics, not validity |
| 7 | Single PUBLICATION vs split (GenSpecs + Prefix + Verified) | Split three files (v1 purity); fused GenSpecs+Prefix acceptable only as interim | One file per publication (HOW_TO §5); prefix/verified are distinct `kind="registry"` authorities with rolling versions |
| 8 | `single_value` for batch | `True` initially, segmentation for multi; offer `extra_grammars` free-text variant with `False` only if catalog demand proves | Consistent with ISBN/ISSN/IBAN/BIC precedent |
| 9 | Non-space separator tolerance (`-`, mixed) | Grammar handles `[ -]` space/hyphen only (ISBN precedent); tabs/newlines/dots/underscores/slashes → MISSING in v1 | stdnum + upc-validator evidence covers space+hyphen only; isbnlib aggressive-strip is ISBN-scrape-specific, do not copy |
| 10 | Label/AI span inclusion | Include label + AI wrapper in `raw_text` span (fused LabelMatcher), notation digits-only + `has_ai` facet | Mirrors ISSN/ISBN/BIC label-span precedent; `raw_text` preserves evidence, notation carries data |
| 11 | Which alternative written forms does v1 recognize (the full §2.1 inventory: compact per length, padded-14, HRI-spaced, hyphen-grouped, AI-wrapped, labeled, GDSN-14)? | RECOGNIZE every form attested by GenSpecs/HRI or ≥2 validators (all of the above); DEFER only UPC-E expansion + variable-measure, REJECT only bars/stems/coupons, each with written rationale in §2.1 | Unhandled common forms are permanent MISSING blind spots (hyphen/AI are common per stdnum strip evidence); discovering them post-ship costs a grammar rewrite |

---

## 14. Ambiguity Analysis (Paxman-specific)

- No inherent GTIN-vs-GTIN positional ambiguity — fixed numeric lengths with rightmost-anchored Mod-10 eliminate the Date-style `01/02/2026` dual-reading; two distinct GTINs in one slice is authorial batching (segmentation intended), while padded-vs-native spellings of one entity are presentation, not ambiguity (dedup to one 14-digit value).
- Prefix-invalid is not lexical ambiguity — `99914141999993` has valid Mod-10 shape but no allocated MO prefix; it is `INVALID` with the Prefix rule (lookup claims the semantics), not a competing value; without the lookup (pinned-out) it is a false `SUCCESS` — the ISBN `978/979`-gate analogue, which is why the always-active LOOKUP corroboration matters for ADR-0012.
- GTIN vs ISBN-13 is same-arithmetic dual jurisdiction, not ambiguity to be designed away — `9780471117094` validates under both authorities by construction (shared EAN-13 checksum); each capability claims it under its own grammar; resolution is deterministic cross-capability precedence at the caller (ISBN for `978/979` when both are registered), with both provenances cited. Weakening either checksum to force uniqueness would corrupt both capabilities.
- Length discrimination prevents cross-capability carving — GTIN 8/12/13/14 digit runs are disjoint from ISSN (hyphen/X), ISIN (12 alphanum with letters), IBAN (15–34), LEI (20), UUID/DOI/URL shapes; WORD boundaries plus the `(?![-]\d)` guard stop 15+-digit runs from yielding inner GTINs, so sibling grammars never produce competing candidates from one span.
- Staleness is not ambiguity — prefix reallocation or Verified-liveness churn changes which strings validate, but determinism-by-snapshot (version in `Provenance.version`, snapshot SHA in `recognition_revision`) makes every result reproducible for its library version; a GTIN that flips `SUCCESS`→`INVALID` across snapshots is a registry update, not two values for one input.

---

## 15. URL Reference (authoritative, fetched 2026-09-22 unless noted)

| Claim | URL | Kind |
|-------|-----|------|
| GenSpecs 26.0 current (Ratified Jan 2026) | `https://ref.gs1.org/standards/genspecs/` | primary |
| Standards log (Jan 2026 Release 26.0 posting) | `https://www.gs1.org/standards/log` | primary |
| v26 Jan 2026 member-org news | `https://www.gs1uk.org/insights/news/GS1-General-Specifications-updated-for-2026` | primary (MO) |
| GTIN 8/12/13/14 definitions, UPC/EAN synonymy, GTIN-14 never starts 0 / NOT for POS | `https://www.gs1us.org/upcs-barcodes-prefixes/what-is-a-gtin` | primary (fetched verbatim §GTIN Structures) |
| UPC anatomy `6 14141 99999 6`, Laurer 1973, first scan 1974, Number System character | `https://www.gs1us.org/upcs-barcodes-prefixes/guide-to-upcs` | primary (fetched verbatim) |
| EAN-8 two-groups-of-four; UPC-E 6-digit / no-longer-licensed note | `https://www.gs1us.org/upcs-barcodes-prefixes/barcode-types` | primary |
| UPC-E zero-suppressed 8-digit statement | `https://www.gs1us.org/upcs-barcodes-prefixes/ean-vs-upc` | primary |
| Mod-10 steps + `6291041500213` worked example | `https://www.gs1.org/services/how-calculate-check-digit-manually` | primary (snippet-quoted; direct fetch 403/WAF, corroborated by GS1 UK + calculator mirrors) |
| 5-step formulation + `5012345670003` worked example | `https://www.gs1uk.org/knowledge-hub/standards/what-is-a-check-digit` | primary (MO, fetched verbatim) |
| Generation-direction calculator statement | `https://www.gs1us.org/tools/check-digit-calculator` | primary |
| Check-digit manual PDF (12-column walkthrough) | `https://documents.gs1us.org/adobe/assets/deliver/urn:aaid:aem:77c80eac-d4e2-41b1-a80d-97739060e8f4/How-to-Calculate-a-Check-Digit.pdf` | primary (unparsed — plan budgets read) |
| Zero-pad table + XML exactly-14 rule | `https://www.gs1.org/edi-xml/technical-user-guide/Item_Numbers` | primary |
| 14-digit display/entry with leading zeros | `https://www.help.gs1us.org/import-products-and-assign-available-gtins` | primary |
| Prefix list + GTIN-8 ranges + `061` example | `https://www.gs1.org/standards/id-keys/company-prefix` | primary (snippet-quoted; direct fetch 403/WAF, corroborated by GS1 UK prefix≠origin page) |
| MO-issued Company Prefix | `https://support.gs1.org/support/solutions/articles/43000734321-how-to-obtain-a-gs1-company-prefix-` | primary |
| Historical timeline (1973/1974/1977/2004/2005/2019) | `https://support.gs1.org/support/solutions/articles/43000734073-gs1-historical-timeline` | primary |
| GTIN-13/14 composition, GS1-8 Prefix, UPC-E condensation | `https://www.gs1.org/docs/barcodes/GSCN_21-271_GTIN8.pdf` | primary |
| GTIN-8s assigned by MOs on request | `https://ref.gs1.org/standards/genspecs/gscn/2015/GSCN_15-039_GTIN-8_Printable_Area.pdf` | primary |
| Indicator 1–9 definition | `https://www.gs1.org/docs/barcodes/GSCN-25-351-Glossary.pdf` | primary |
| Allocation rules index + 3 guiding questions | `https://www.gs1.org/1/gtinrules/` + `https://www.gs1.org/1/gtinrules/en/decision-support` | primary |
| Net-content new-GTIN rule (Release 1.1 Sep 2023) | `https://documents.gs1us.org/adobe/assets/deliver/urn:aaid:aem:21b56489-cf6d-4eb1-be20-8850157e1734/GTIN-Management-Standard.pdf` | primary |
| Verified by GS1 scope + 6 attributes (via GS1 US database page) | `https://www.gs1.org/services/verified-by-gs1` + `https://www.gs1us.org/tools/gs1-company-database-gepir` | primary (snippet-quoted; direct fetch 403/WAF on gs1.org) |
| HRI one-to-one + `(01)` parenthesised form | `https://ref.gs1.org/guidelines/human-readable-interpretation/` (+ `https://www.gs1.org/docs/barcodes/HRI_Implementation_Guide.pdf`) | primary |
| Prefix≠origin + check-last + 12/13/8 + GTIN-14 levels | `https://www.gs1uk.org/knowledge-hub/product-identification/what-is-a-gtin` | primary (MO) |
| python-stdnum `ean.py` (lengths, checksum, no pad) | `https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/ean.py` | primary (fetched verbatim) |
| python-stdnum `util.py` (`clean`, `isdigits`) | `https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/util.py` | primary (fetched verbatim) |
| python-stdnum `isbn.py` (`ean.validate` + `978/979` gate) | `https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/isbn.py` | primary (fetched verbatim) |
| validator.js `isEAN.js` (8/13/14, no 12, no strip) | `https://raw.githubusercontent.com/validatorjs/validator.js/master/src/lib/isEAN.js` | primary (fetched verbatim) |
| validator.js `isISBN.js` / `isISSN.js` (strip precedents) | `https://raw.githubusercontent.com/validatorjs/validator.js/master/src/lib/isISBN.js` | primary (fetched verbatim) |
| GunCompare `gtin-validator` (lengths, no strip, zero-strip helper) | `https://github.com/GunCompare/gtin-validator` | primary (fetched verbatim) |
| xbpf `gtin` incl. `upc-e.ts` (only UPC-E handler surveyed) | `https://github.com/xbpf/gtin` | primary (fetched verbatim) |
| `gtin-checksum` (`GTIN_LENGTHS`, right-to-left 3/1) | `https://github.com/marius103/gtin-checksum` | primary (fetched verbatim) |
| `upc-barcode-validator` (strips `\s` + `-`) | `https://raw.githubusercontent.com/aamirkhancr7/upc-barcode-validator/main/src/index.ts` | primary (fetched verbatim) |
| isbnlib `_core.py` (`GTIN13 = ean13` alias) | `https://raw.githubusercontent.com/xlcnd/isbnlib/dev/isbnlib/_core.py` | primary (fetched verbatim) |
| GS1 Germany `checkDigitCalculator` (7/11/12/13-digit inputs, demo vectors) | `https://github.com/gs1-germany/checkDigitCalculator` | primary (official MO, fetched verbatim) |
| Wikipedia GTIN (taxonomy, zero-pad N-table) | `https://en.wikipedia.org/wiki/Global_Trade_Item_Number` | secondary |
| gtin.info (14-digit family, left-pad doctrine) | `https://www.gtin.info/` + `https://www.gtin.info/check-digit-calculator/` | secondary (commercial) |
| Paxman ISBN-13 grammar precedent | `paxman/capabilities/ISBN/grammar/isbn13_recognition.py` | primary (codebase) |
| Paxman ISSN label precedent | `paxman/capabilities/ISSN/grammar/issn_recognition.py` | primary (codebase) |
| Paxman ISBN notation/contract/capability precedent | `paxman/capabilities/ISBN/notation.py`, `contract.py`, `capability.py`, `rules/iso_2108_ed2017.py` | primary (codebase) |
| Paxman BIC grammar precedent | `paxman/capabilities/BIC/grammar/bic_recognition.py` | primary (codebase) |
| Paxman domain + orchestrator precedent | `paxman/core/domain.py`, `paxman/engine/orchestrator.py` | primary (codebase) |
| Paxman conventions | `HOW_TO_ADD_NEW_CAPABILITY.md`, `HOW_TO_ADD_NEW_GRAMMAR.md`, `ARCHITECTURE.md` | primary (codebase) |
| BIC/IBAN/ISSN research precedents | `docs/development/research/2026-08-23-bic-canonicalization.md`, `2026-08-22-iban-canonicalization.md`, `2026-08-21-issn-canonicalization.md` | primary (codebase) |

---

## 16. Evidence Completion — Resolved

This report's GTIN-specific authoritative evidence has been fetched and cited (2026-09-22):

- [x] GenSpecs entry: Release 26.0 Ratified Jan 2026 (current, Published) plus lineage back to 1973 UPC origin; GS1 Global Office publisher; rolling GSCN amendment; version lifecycle publication_year 2026; citation anchored to §1 structure + HRI + check-digit pages
- [x] RA and prefix provenance: GS1 Global Office + MOs, Company Prefix issuance, GTIN-8 MO assignment, prefix-range table with `061` worked note; authority/spec_name/kind registry/reference_url/version Rolling/lifecycle active
- [x] Verified registry provenance: Verified by GS1 (replaces GEPIR 31 Dec 2023), 6 brand-owner attributes, gated `include_verified` design, determinism-by-snapshot rationale
- [x] Structure: 8/12/13/14 numeric, check last, indicator 1–9 (never 0 for true GTIN-14), Number System character, UPC-A/EAN-13/EAN-8 synonymy, HRI spacings
- [x] Checksum algorithm proved (GS1 Mod-10, 3/1 rightmost-anchored, `(10-sum%10)%10`) with two quoted worked examples + four computed vectors + padding-invariance proof (8→14, 12→14, 13→14 all preserve check)
- [x] Prefix nuance: first-3-digit MO test on padded-14 form; GTIN-8 exception ranges; prefix≠origin misconception documented
- [x] Ecosystem regex consensus: stdnum (space+hyphen strip, 8/12/13/14, no pad) vs validator.js (strict 8/13/14, no strip, no 12) vs GunCompare/xbpf/gtin-checksum/upc-validator (12-inclusive, strip divergence tabled) vs GS1 Germany (without-digit inputs)
- [x] Recognition-surface inventory complete (§2.1): every attested written form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form (UPC-E DEFER, bars/stems/coupons REJECT, variable-measure DEFER)
- [x] Wild input shapes validated (§2.2, 18 categories) against GenSpecs + GS1 US/UK pages + HRI + validators
- [x] Label + AI scope decision (fused `[\s:-]+`, glued reject, span includes wrapper)
- [x] Indicator/pad-zero equivalence decision (distinct entities, §7.2/§8#7)
- [x] UPC-E semantics decision (compressed symbology, not a length; check on expanded form per GS1 Australia fact sheet via xbpf)
- [x] Directory liveness scope decision (gated snapshot, never live lookup)
- [x] Bookland dual-jurisdiction decision (recognize as GTIN-13, defer precedence to ISBN)

File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ISSN, Country and Phone Capabilities Teach GTIN (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

**ISBN-13 grammar strips, rule validates** (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py:17-27`): `r"\b(?:ISBN(?:-13)?[\s:-]+)?(?=((?:\d[ -]?){12}\d)(?![\d]))\1"` with `_isbn13_notation` digit-collapse → `ISBNNotation(shape="isbn13", digits=digits)`. GTIN copies the fused-label + separator-tolerant + `(?![-]\d)` shape with a length alternation instead of fixed 13.

**ISSN label-kind with glued policy** (`paxman/capabilities/ISSN/grammar/issn_recognition.py:40-49`): `LabelMatcher(labels={ISSN,ISSN-L,ISSN-H}, separator=[\s:-]*, glued_policy="allow", pattern=\d{4}-?\d{3}[0-9Xx](?![-]\d), BoundarySpec.WORD)`. GTIN copies the kind but flips glued to `"reject"` (IBAN/BIC precedent: `IBANDE89…`/`BICDEUTDEFF` → MISSING).

**ISBN notation + contract + capability** (`notation.py:8-16`, `contract.py:40-47`, `capability.py:38-64,130-144`): frozen-slots `ISBNNotation(shape, digits)`; frozen-no-slots `ISBNContract(DEFAULT="isbn13", OFFERED={"hyphenated"}, include_isbn10=True, include_range_validation=False, active_grammars conditional)`; `_hyphenate()` presentation-only + `format_value` identity-for-default. GTIN mirrors with `(digits, native_length, has_ai)` + (`gtin14` default, `{"native","hri"}` offered, `include_verified` gated).

**ISBN rules pair PARSER + LOOKUP on one semantics** (`rules/iso_2108_ed2017.py:25-45,48-72`): `Section53Isbn13CheckDigit(PARSER)` + `Section42Gs1Prefix(LOOKUP_TABLE)`, both `target_semantics=frozenset({"isbn13_recognition"})`, both `normalize → digits` (duplicate check intentional per audit B3). GTIN mirrors with GenSpecs PARSER + Prefix LOOKUP (ADR-0012 corroboration without vacuity).

**BIC grammar precision** (`paxman/capabilities/BIC/grammar/bic_recognition.py:26-31`): compact-vs-grouped alternation, `(?ai:)` ASCII, `[\s:-]+` label with glued rejection, WORD guards, `isalnum` collapse. GTIN copies the alternation + ASCII + label + WORD + collapse pattern for digits.

**Engine + domain invariants** (`paxman/engine/orchestrator.py` `_recognize` containment-dedup per grammar + total order, `_dedup_spans` longer-wins; `paxman/core/domain.py:246-271` `Rule.__init_subclass__` six attributes, `Grammar.__init_subclass__` non-empty `semantics`; `RecognitionMatch.__post_init__` span/`raw_text` invariant): the four architectural lessons for GTIN — (1) grammar strips, rule validates, capability formats; (2) one file per provenance, one class per section; (3) no `output_format` in rules, ever; (4) single grammar with optional/length alternation avoids spurious cross-grammar AMBIGUOUS.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for GTIN. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the deeper ISBN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
