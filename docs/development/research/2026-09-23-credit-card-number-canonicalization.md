# Credit Card PAN Canonicalization Research — paxman-python

**Date:** 2026-09-23
**Scope:** Primary-source survey of the credit-card Primary Account Number (PAN) standard (ISO/IEC 7812-1:2017 Numbering system + ISO/IEC 7812-2:2017 Application and registration procedures, Luhn check per Annex B / US Patent 2,950,048), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `CreditCard` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org) for ISO/IEC 7812-1:2017 (current, Ed.5) and its lineage (1993, 2000, 2006, 2015) plus ISO/IEC 7812-2:2017 (current, Ed.5); US Patent 2,950,048 (Luhn, primary); PCI SSC official blog on 8-digit BINs + PCI DSS masking/truncation guidance (handling caveat, not authority); python-stdnum `stdnum/luhn.py` (generic Luhn, no PAN module); validator.js `isCreditCard.js` + `isLuhnNumber.js` plus test fixtures; braintree `card-validator` + `credit-card-type` (brand/length/gap tables); dldevinc `django-credit-cards` (strip-all + Luhn + Chromium brand table); thephpleague `omnipay-common` (strip-all + Luhn + 12–19 gate); Wikipedia ISO/IEC 7812 / Luhn algorithm / Payment card number as secondary only; and shipped Paxman capabilities (GTIN, ISIN, ISBN, IBAN, LEI) as architectural precedents. Repo state: `dev @ 08fbd0d` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN research precedent `docs/development/research/2026-08-21-issn-canonicalization.md` plus the IBAN precedent `docs/development/research/2026-08-22-iban-canonicalization.md` and the BIC precedent `docs/development/research/2026-08-23-bic-canonicalization.md`, with GTIN (`2026-09-22-gtin-canonicalization.md`), LEI (`2026-09-22-lei-canonicalization.md`), and ISIN (`2026-08-24-isin-canonicalization.md`) as check-digit siblings.

---

## Executive Summary

Credit-card PAN is a strong fit for a Paxman capability: it has an unambiguous canonical form (**contiguous ASCII digits, no separators, 12–19 digits, Luhn-valid**: `IIN (6 or 8 incl. MII) + individual account identifier (variable) + 1 Luhn check digit`, ceiling 19 per ISO/IEC 7812-1), a stable two-part standard (**ISO/IEC 7812-1:2017** 5th edition, 2017-01-03, `Published` + confirmed 2022-10-27, cancels 2015, ICS 35.240.15, publisher ISO/IEC JTC 1/SC 17) with the **American Bankers Association (ABA)** as IIN Registration Authority (BIN administration handoff to CUSIP Global Services formalized Feb 2024, secondary), a **non-public** authoritative register (the ISO Register of IINs is licence-only — no redistributable authority table exists), and a well-understood human-readable presentation (**space/hyphen-grouped** `4111 1111 1111 1111`, Amex `4-6-5`, presentation-only). The domain mirrors Paxman's value proposition for GTIN/ISBN/ISIN: recognizing tolerant human surface, validating strictly against authority (structure + Luhn), returning canonical compact digits with provenance. The checksum sentence: PAN carries a **Luhn MOD-10 double-add-double check digit** (ISO/IEC 7812-1:2017 Annex B, public-domain US 2,950,048) — full-PAN `sum mod 10 == 0` — unlike BIC (no checksum) and like ISIN/ISBN/GTIN (check-digit-gated).

Key findings that shape the design:

1. **Canonical form is contiguous digits, no separators** (`4111111111111111`, `378282246310005`, `6011111111111117` — note the Luhn article's `79927398713` is an 8/11-digit **algorithm reference below the 12-floor, never a PAN example**, §7.1). Length is a **range 12–19** for the payment-card scope (ISO-confirmed ceiling 19; lower bound is operational/brand policy, not ISO text — see §5.4). Charset is digits only; spaces/hyphens are presentation grouping. This maps onto the presentational-only invariant: `format_value()` renders `pan` (compact, default) vs `grouped` without touching validity; `masked`/`truncated` (first-6/last-4) are **projections and must never be offered** (ADR-0011).
2. **One grammar suffices, with separator-tolerant range alternation.** Unlike GTIN (four exact lengths 8/12/13/14) or ISBN (two grammars, ISBN-13 vs ISBN-10), PAN's 12–19 is a contiguous range of eight lengths sharing one meaning. A single `pan_recognition` grammar with Regex recognition strategy (longest-first range alternation, space/hyphen interleave, optional label branch, word guards, plus a trailing **date guard** and a **joined-run guard** — §4.2) is correct. On the kernel path the context-sensitive guards select the HOW_TO §4 `scanner` kind (shipped customers: Language BCP-47, URL, Phone E.164) rather than a bare regex stage (§4.2 machinery notes). Splitting per length or per brand would create cross-grammar containment producing spurious `AMBIGUOUS` (longer-wins is per-grammar only, cross-grammar preserved per `orchestrator:_dedup_spans`).
3. **Validation is two-level: generic+Luhn always-active, brand-prefix secondary-gated or deferred.** Level 1: structure (12–19 ASCII digits) + Luhn (`PARSER`, ISO/IEC 7812-1 Annex B). Level 2: brand/IIN-prefix membership (`LOOKUP_TABLE`, Visa/Mastercard/Amex/etc. ranges) is **brand data, not ISO** — the IIN Register is not public — so it must be a secondary-provenance gated rule (`include_brand_validation=False`) or a deferred community extension, never fused into the ISO rule. UnionPay Luhn divergence (braintree skips Luhn for UnionPay by default) confirms brand logic does not belong in the ISO check.
4. **IIN-6 vs IIN-8 is an interpretation, not a distinct identity; masked/truncated is not a PAN.** The 2017 revision extends IIN from fixed 6 to 6-or-8 digits; the same compact digits admit two IIN parses but one canonical value — do not coalesce or split, the canonical is the literal digit string. Masked (`XXXX XXXX XXXX 1234`), truncated (first-6/last-4), tokenized, and PCI redaction formats are **handling outputs, never valid input** — recognition must not claim them, validation must not pass them.
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO/IEC 7812-1:2017` (active, current) owns PAN structure + Luhn Annex B; `ISO/IEC 7812-2:2017` (active, current) owns application/registration procedures (no per-PAN validation logic — cite for RA/IIN-allocation context only); brand-prefix tables (if shipped) own a **secondary** gated file with `kind="registry"`-or-`"policy"` and explicit secondary citation, never ISO authority. PCI DSS owns **no validation provenance** — cite only as a handling caveat.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---
## 1. Target User

| Persona | Why they need PAN canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Payments / checkout engineers** | Normalize `4111 1111 1111 1111` vs `4111-1111-1111-1111` vs `4111111111111111` to one compact key for form validation, deduplication, and pre-tokenization checks before sending to a PSP | Checkout forms, card-on-file ingest, payment-hub ETL, PSP test-card fixtures |
| **Fraud / risk / reconciliation teams** | Join on compact canonical PAN (or its hash) across spaced/dashed/log variants; reject mistyped PANs early via Luhn before expensive authorization | Reconciliation pipelines, chargeback matching, entity resolution, LLM extraction post-processing |
| **Data engineering / migration teams** | Extract and canonicalize PANs from free-text notes, PDFs, emails, scraped HTML with span-bearing provenance; detect test-card fixtures vs live-like input | ETL pipelines, statement parsers, Open Banking aggregation, corpus cleaning |
| **Support / QA / docs teams** | Distinguish valid test PANs (`4111111111111111`, `378282246310005`) from invalid/masked/redacted strings; render grouped display for human readability without changing identity | Test matrices, docs examples, receipt renderers (grouped display only — masking is a separate redaction layer) |
| **Compliance-adjacent tooling** | Keep PAN handling explicit: canonicalize only full PANs, refuse masked/truncated/tokenized strings as `INVALID`/`MISSING`, never log or re-emit full PANs beyond the pipeline result | Pre-commit scanners, DLP helpers, audit log scrubbers (PCI DSS Req. 3 scope awareness — this capability does not confer PCI compliance) |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many PAN mentions) and a contract; Paxman returns one canonical PAN (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors GTIN (`gtin14` compact default) and ISIN (`isin` compact default) ergonomics, but the canonical default is **compact contiguous digits** (no spaces, no hyphens, no label).

> **Handling warning (not a feature):** PANs are cardholder data under PCI DSS. This capability canonicalizes the value it is given — it does not mask, truncate, tokenize, encrypt, or make storage safe. Callers must not log full PANs, must apply PCI masking/truncation/tokenization at the presentation/storage boundary, and must scope any persistence under PCI DSS Requirement 3/4. Test fixtures in §12 use only public test numbers.

---
## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

From the Phase 1C survey (spec abstracts + ecosystem strip logic + real-world carriers), every representation humans actually produce for a PAN value. Brand-length rows are secondary (brand specs, not ISO) and labeled as such.

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Compact continuous | `4111111111111111`, `378282246310005`, `6011111111111117` | Braintree test table (`developer.paypal.com/braintree/docs/guides/credit-cards/testing-go-live/php`); Adyen/Stripe compact variants; stdnum `luhn.validate` accepts only this form | canonical | RECOGNIZE | main pattern body (digit run 12–19) |
| Spaced 4-4-4-4 grouping | `4111 1111 1111 1111`, `4929 7226 5379 7141`, `4242 4242 4242 4242` | validator.js fixture `4929 7226 5379 7141` valid; Adyen docs `4111 1111 1111 1111`; Stripe `4242 4242 4242 4242`; braintree `gaps:[4,8,12]` | common | RECOGNIZE | separator-interleave `(?:[ \-]?\d)` bounded repetition |
| Dashed 4-4-4-4 grouping | `4716-2210-5188-5662`, `4444-3333-2222-1111` | validator.js fixture `4716-2210-5188-5662`; omnipay docstring `"4444-3333 2222 1111"`; django widget `pattern:[-\d\s]*` | common | RECOGNIZE | same separator class `[ \-]` (space+hyphen only) |
| Amex 4-6-5 grouping | `3782 822463 10005`, `3714 496353 98431` | Stripe/Memberstack test tables; braintree `gaps:[4,10]` encodes 4-6-5; compact twin `378282246310005` in Braintree tables | common (Amex) | RECOGNIZE | same interleave (grouping-agnostic: strip then length-guard) |
| 14-digit Diners grouping | `3622 720627 1667`, `36050234196908` | Stripe `3622 720627 1667`; validator.js `36050234196908` | occasional | RECOGNIZE | same interleave (14 in 12–19 range) |
| Mixed space/hyphen grouping | `4444-3333 2222 1111`, `4111 1111-1111 1111` | omnipay docstring mixed example; validator.js `/[- ]+/g` strips both uniformly | occasional | RECOGNIZE | separator class per gap (either char) |
| Label-prefixed prose | `card number: 4111 1111 1111 1111`, `PAN: 4111111111111111`, `CC: 378282246310005`, `credit card 5555555555554444` | Adyen POS `PAN` column header (`docs.adyen.com/point-of-sale/testing-pos-payments/test-card-v2`); checkout/receipt prose; django/omnipay setters strip labels implicitly (`/\D/`, `/[^\d]+/`) | common (forms/logs) | RECOGNIZE | fused optional label branch `(?:(?:credit[\s-]?card(?:[\s-]?number)?\|card[\s-]?number\|pan\|cc)[\s:-]+)?` with mandatory one-or-more separator, glued `reject` (§4.2 scan-time label) |
| Irregular whitespace (double space, tab) | `4111  1111 1111 1111`, `4111\t1111\t1111\t1111` | Pasted logs/exports; braintree `/-|\s/g` (`\s` includes tab); django `/[^\d]+/` collapses any run | occasional | **NOT recognized in v1 → `MISSING`** (documented non-recognition — Open Decision §13 #9) | body interleave stays single `[ \-]?`, so the origin claim cannot cross the double gap (branch guards fail), and the left joined-run guard (§4.2) blocks inner starts — claims nothing; no prefix carve, no `INVALID` |

A v1 that does NOT recognize a commonly attested form must state that explicitly here AND raise it as an Open Decision (§13). The deliberate scope cuts for v1 are: **dot/slash/underscore separators → DEFER** (only omnipay/django strip-all evidence, no brand-doc attestation as PAN grouping); **masked/truncated/tokenized → REJECT** (handling outputs, §2.3); **8–11-digit short PANs → REJECT** as non-payment scope (§5.4); **expiry/CVV-attached strings → REJECT as multi-field scope — recognize the PAN span only** (§2.3; `4111111111111111 12/27` → `SUCCESS` on the 16-digit span, §8 #13); **irregular whitespace (double-space/tab) → NOT recognized → `MISSING`** (row 8, Open Decision §13 #9).

**Deferred / rejected inventory (explicit):**

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Rationale |
|------|---------|----------------|------------|--------------------|-----------|
| Dot/underscore/slash grouping | `4111.1111.1111.1111`, `4111_1111_1111_1111`, `4111/1111/1111/1111` | Only omnipay `/\D/` + django `/[^\d]+/` strip-all side effect; no validator fixture, no brand-doc grouping | rare | DEFER to `extra_grammars` community extension | No primary/brand attestation as PAN grouping; space/hyphen covers all fixtures; extending the separator class widens false-positive surface (version strings, decimals) |
| Parenthesized / quoted / bracketed | `"4111111111111111"`, `[4111 1111 1111 1111]`, `(4111111111111111)` | Scraped HTML/JSON fragments (generic carrier, no PAN-specific attestation) | occasional (carrier) | RECOGNIZE via boundary policy (no pattern change) | Word-boundary guards already admit punctuation-adjacent runs; no fused-quote branch needed |
| Masked / redacted display | `XXXX XXXX XXXX 1234`, `4111-XXXX-XXXX-1111`, `•••• 1234` | PCI DSS Req. 3.3/3.4 masking baseline; omnipay `getNumberMasked()` producer | common as output | REJECT (never valid input) | Projection over PAN information (ADR-0011); contains non-digits; all surveyed validators reject; grammar charset guard excludes |
| Truncated storage/display | `411111...1111` (first-6/last-4), `... 4444` | PCI DSS truncation; Payment card number wiki PAN-truncation section | common as output | REJECT | Not a PAN (fewer than 12 digits survive); length guard excludes |
| Token / surrogate PAN | `tok_visa_1234`, `411111••••••1111` (format-preserving-encryption token) | Format-preserving encryption / tokenization docs (Payment card number wiki Security measures) | common in vaulted systems | REJECT | Different identifier domain; charset/length guards exclude |
| Expiry/CVV-attached | `4111111111111111 12/27 123`, `4111 1111 1111 1111 exp 01/28` | Checkout multi-field concatenation (no single-field attestation) | common in forms | REJECT (recognize PAN span only) | Multi-field scope; grammar must emit the PAN span without swallowing `12/27`/`123` (trailing-date guard, §4.2; verified §8 #13) |
| OCR / homoglyph | `4111 1111 1111 111I` (I-for-1), `4l11...` (l-for-1), `O`-for-`0` | Generic OCR-error class (no PAN corpus attestation) | rare | REJECT (no autocorrection) | Strict `\d` charset; Luhn would fail anyway; Paxman never guesses |

### 2.2 Wild variants — adversarial mutations of each inventoried form

Enumerated from spec abstracts, RA pages, brand tables (secondary), and real validators; stress-tests every §2.1 RECOGNIZE form:

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical compact 16 | `4111111111111111`, `5555555555554444`, `4242424242424242` | Spec-adjacent master form (digits only, Luhn-valid) |
| 2 | Canonical compact 15 (Amex) | `378282246310005`, `371449635398431` | 15-digit Amex, Luhn-valid |
| 3 | Canonical compact 13 (legacy Visa) | `4222222222222` | 13-digit Visa (secondary brand table; braintree omits — must still recognize shape, rule decides) |
| 4 | Canonical compact 16/19 | `6011111111111117` (16); 19-ceiling vectors are Luhn-completed constructions (§12 property tests), not attested fixtures | 19-digit ceiling (Discover/UnionPay secondary) |
| 5 | Lowercase label | `pan: 4111111111111111`, `card number: 378282246310005` | label case-insensitive, `[\s:-]+`, span includes label |
| 6 | Uppercase label | `PAN: 4111111111111111`, `CC: 5555555555554444` | same, `(?i)` label branch |
| 7 | Grouped paper display | `4111 1111 1111 1111`, `3782 822463 10005` | presentation-only, strip to compact |
| 8 | Dashed grouping | `4111-1111-1111-1111`, `4716-2210-5188-5662` | presentation-only, strip to compact |
| 9 | Mixed separators | `4444-3333 2222 1111` | per-gap class, not whole-string separator |
| 10 | Irregular whitespace | `4111  1111 1111 1111`, `4111\t1111 1111 1111` | v1 non-recognition: double-space/tab poison the joined run → `MISSING` (left joined-run guard, §4.2); must not prefix-claim or absorb surrounding prose; `\s`-widening remains Open Decision §13 #9 |
| 11 | With trailing annotation | `4111111111111111 (Visa)`, `378282246310005 - Amex test` | emit PAN span only, not parenthetical |
| 12 | Multiple per line | `4111111111111111 / 5555555555554444`, `cards: 4111111111111111, 378282246310005` | 2+ matches, segmentation path |
| 13 | Quoted / bracketed | `"4111111111111111"`, `[378282246310005]`, `(4111 1111 1111 1111)` | inside punctuation, span is digits+separators only (label excluded unless matched) |
| 14 | Over-long (20+) | `41111111111111111` (17), `41111111111111111111` (20) | length guard, never 20+; 20-digit runs (compact, spaced, dashed) refuse all carves via word guards + joined-run orphan guard → `MISSING` (§8 #7/#19) |
| 15 | Under-long (11 and below) | `41111111111` (11), `12345678` (8) | length guard, grammar must not claim; `MISSING` (not `INVALID`) |
| 16 | X-glued runs | `X4111111111111111`, `4111111111111111Y`, `A4111111111111111B` | word-boundary guards (`(?<!\w)`/`(?!\w)` or `BoundarySpec.WORD`) |
| 17 | Digit-glued runs | `14111111111111111` (17-digit super-run), `41111111111111110` (17) | whole 17-run claimed (longest-first, in-range) → `INVALID` (Luhn fails); never a 16-carve |
| 18 | Luhn-invalid same-length | `4111111111111112` (last digit flipped), `5398228707871528` (validator.js invalid fixture) | grammar claims shape, rule rejects → `INVALID` |
| 19 | Expiry-glued | `4111111111111111 12/27`, `41111111111111111227` | date guard `(?!\s\d+/)` (§4.2) claims the 16-digit PAN span only; second example is a digit-glued 20-run → `MISSING`, not a 16-carve |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| `arthurdejong/python-stdnum` `stdnum/luhn.py` (`checksum`/`validate`/`calc_check_digit`) | No strip, no length table, no brand table. `checksum = (sum(values[::2]) + sum(sum(divmod(i*2, n)) for i in values[1::2])) % n`; `validate` raises `InvalidFormat` on empty/non-alphabet, `InvalidChecksum` on `!= 0`. Spaced/dashed PANs → `InvalidFormat`. Proves compact-only at the Luhn layer. |
| `validator.js` `src/lib/isCreditCard.js` | `sanitized = card.replace(/[- ]+/g, '')` then per-provider regex (`amex:/^3[47][0-9]{13}$/`, `dinersclub:/^3(?:0[0-5]|[68][0-9])[0-9]{11}$/`, `discover:/^6(?:011|5[0-9][0-9])[0-9]{12,15}$/`, `jcb:/^(?:2131|1800|35\d{3})\d{11}$/`, `mastercard:/^5[1-5][0-9]{2}|(222[1-9]|…|2720)[0-9]{12}$/` — known `|`-precedence bug issue #2717, `unionpay:/^(6[27][0-9]{14}|^(81[0-9]{14,17}))$/`, `visa:/^(?:4[0-9]{12})(?:[0-9]{3,6})?$/`) then `isLuhnValid(card)`. Fixtures: `4716-2210-5188-5662` + `4929 7226 5379 7141` valid; `prefix…`/`…middle…`/`…suffix` invalid. |
| `validator.js` `src/lib/isLuhnNumber.js` | Re-strips `/[- ]+/g`, right-to-left double-alternate (`shouldDouble` toggle, `>= 10 → (tmpNum % 10) + 1`), `sum % 10 === 0 ? sanitized : false`. Non-digit → `NaN` → reject. |
| `braintree/card-validator` `src/card-number.ts` | `testCardValue = String(value).replace(/-|\s/g, "")`; `!/^\d*$/` → `(null,false,false)`; per-brand `lengths` + `patterns` from `credit-card-type` (visa `[16,18,19]`, mastercard `[16]`, amex `[15]`, diners `[14,16,19]`, discover `[16,19]`, jcb `[16,17,18,19]`, unionpay `[14–19]`, maestro `[12–19]`); `gaps:[4,8,12]` (4-4-4-4) vs amex `gaps:[4,10]` (4-6-5); Luhn skipped only for UnionPay by default. |
| `dldevinc/django-credit-cards` `utils.py` + `validators.py` + `types.py` | `re_non_digits = re.compile(r'[^\d]+')`; `get_digits` strips ALL non-digits; `LUHN_ODD_LOOKUP = (0,2,4,6,8,1,3,5,7,9)` table-driven Luhn; `CCNumberValidator: luhn(get_digits(value))` else `ValidationError`; brand `CC_TYPES` prefix-only (Chromium-derived: visa `^4`, amex `^3[47]`, mastercard `^(?:5[1-5]|222[1-9]|…)`, …); lengths form `MinLengthValidator(12)` / model `MinLengthValidator(13)`, `max_length=25` (separators pre-`to_python`). |
| `thephpleague/omnipay-common` `Helper.php` + `CreditCard.php` | `setNumber: preg_replace('/\D/', '', value)` (strips all non-digits; docstring blesses `"4444-3333 2222 1111"`); `validateLuhn` reverse-double digit-sum; `validate()`: Luhn gate + `preg_match('/^\d{12,19}$/i')` generic 12–19 gate; brand regexes ActiveMerchant-derived (visa `/^4\d{12}(\d{3})?$/`, mastercard 2-series alternation, amex `/^3[47]\d{13}$/`, …); `getNumberMasked()` producer proves masked forms are outputs. |

**Normalization contract (reuse GTIN/ISIN pattern):**
```python
import re

# v1: spaces + hyphens only (validator.js / braintree evidence).
# Strip-all (omnipay / django) is NOT adopted: it would fuse labels into
# digits ("PAN4111..." -> digits) and bless dot/underscore groupings
# without attestation. Labels are handled by the fused optional branch,
# not by stripping.
compact = re.sub(r"[ \-]", "", raw).strip()
# then validate: compact.isascii() and compact.isdigit() and 12 <= len <= 19 and luhn_valid(compact)
```

### 2.3 What input is NOT a PAN mention

- IMEI (`490154203237518`, 15 digits, Luhn per 3GPP TS 22.016) — same algorithm, same length band, different domain (device vs payment). Length/check discrimination cannot separate; domain is caller-selected via capability name. Not lexical ambiguity within the PAN capability.
- GTIN-12/13/14 (`5901234123457`, `614141999996`) — overlapping lengths 12–14 but different check (GS1 Mod-10 weights 3/1 vs Luhn double-add-double) and different meaning. A 12-digit string passing both checks is two domain readings, not one ambiguous PAN.
- IBAN (`DE89370400440532013000`, 15–34 alnum) / ISIN (`US0378331005`, 12 alnum with letters) / LEI (20 alnum) — charset (letters present) and length guards disambiguate; a 12–19 all-digit run is never an IBAN/ISIN/LEI mention.
- Phone E.164 (`+16502530000`, 11–15 with `+`) / national groups — `+`/parenthesis/parens carriers excluded by digit-separator-only pattern.
- Masked/truncated/tokenized (`XXXX XXXX XXXX 1234`, `411111...1111`, `tok_visa_1234`) — handling outputs, `MISSING` (grammar must not claim: charset guard) — never `INVALID`.
- Expiry/CVV/amount-attached (`4111111111111111 12/27`, `4111...1111 exp 123`) — multi-field scope; PAN span alone may still `SUCCESS` while the full slice is caller-segmented.
- Short runs / bare IIN / BIN (`411111`, `550000`, `378282`) — too short, grammar must not claim → `MISSING` vs `INVALID` boundary (see §9).
- Bare brand names (`Visa`, `Amex`) — vocabulary, not shape → `MISSING`.

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct PANs that normalize to different compact values are `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` with `single_value=True` enforcement); the caller-owned segmentation path (split then canonicalize each slice) is the intended multi-entity pattern for vault-migration lists or test-card tables. Identical PAN mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---
## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — atomic digits (IP precedent, not ISIN decomposition)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PANNotation:
    """PAN notation — grammar-normalized digit form.

    ``digits`` is the contiguous ASCII digit string with separators,
    labels, and whitespace stripped (length 12–19, ``isdigit`` only).
    ``compact`` repeats ``digits`` verbatim so rules can read the
    capability-wide ``compact`` facet name shared with ISIN/LEI/IBAN
    without re-slicing; the two fields are always equal.

    The grammar never validates Luhn or brand membership;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    """

    digits: str  # e.g. "4111111111111111" — 12–19 ASCII digits
    compact: str  # == digits, e.g. "4111111111111111"
```

**Considered alternative — decomposed `iin + account_identifier + check_digit`:** ISIN-style (`country_code + nsin + check_digit + compact`) and LEI-style (`lou_prefix + entity_block + check_digits + compact`) expose the spec's field split so rules route by prefix. For PAN this is rejected because the IIN split is **policy-ambiguous**: the same compact admits a 6-digit IIN parse (`compact[0:6]` + 5–12-digit account) and an 8-digit IIN parse (`compact[0:8]` + 3–10-digit account) under the 2017 revision, and the paid §4–5 text (not fetched — paywalled) is the only arbiter of which parse governs a given length. Enshrining `iin: str` in the notation would freeze a 6-vs-8 policy decision in the recognition layer, where it does not belong. The atomic form keeps the grammar policy-free; rules derive `compact[0:6]` / `compact[0:8]` / `compact[-1]` views locally without importing shared slicing (defense-in-depth, ISIN `_ISIN_RE` precedent).

**Second considered alternative — GTIN-style `native_length` facet:** GTIN retains `native_length` because `normalize()` zero-pads to GTIN-14 while `native` re-slices. PAN `normalize()` is identity (compact in, compact out), so `native_length == len(digits)` always and carries no information. Rejected.

**Invariants the grammar enforces (before rules):**
- `digits` is 12–19 ASCII digits only (`isascii()` + `isdigit()`), separators/labels stripped, no letters, no `X`, no `•`.
- `compact == digits` exactly (equality is checked by the structure rule as defense-in-depth, ISIN `compact != country+nsin+check` precedent).
- `raw_text` preserves the original span (grouping + label + case); the notation is the syntax-normalized token. `len(raw_text) == end - start` always holds.

### 3.2 Why not carry spaces, hyphens, or labels in the notation

Spaces, hyphens, grouping, and `PAN:`/`card number:` labels have **no lexical significance** for validity (ISO 7812-1 wire form is digits only; grouping is embossing/print convention). Compact and grouped forms of the same PAN have the same identity; dedup and status logic operate on `compact`. Presentation is `Capability.format_value()` only. Labels are routing hints for human readers, not part of the identifier — statement or report renderers add them.

### 3.3 Why `iin`/`mii` is not a shape discriminator literal

MII (first digit 0–9) and IIN (first 6 or 8) are informative routing families, not validity discriminators: every MII value 0–9 admits valid PANs (special ranges `00`/`80CCC`/`89EE`/`9CCC` are non-payment IIN uses under the same numbering system, secondary). Modeling each as a `Literal` would be brittle and would enshrine the 6-vs-8 policy in the type system. Instead the notation carries free `str` and `LOOKUP_TABLE` brand rules (if shipped) validate prefixes against secondary tables, mirroring the Country lexicon-key pattern where the registry — not the type system — owns the vocabulary. No `shape` field is needed because `len(digits)` in `12–19` plus Luhn already discriminates payment PANs, and no second notation meaning exists.

---
## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape) or **Lexicon** (finite vocabulary). PAN has a distinctive numeric-range shape (12–19 ASCII digits with space/hyphen grouping plus optional human label), so **Regex** is the correct strategy. No lexicon table is involved at recognition; the brand-prefix vocabulary (if ever shipped) lives in the brand rule (lookup), not the grammar key set. Luhn is semantic (rule-owned), never syntactic. "Regex strategy" fixes the *shape* decision only; HOW_TO §4's matcher-kinds table then picks the implementation, and PAN's contextual guards select the kernel `scanner` kind (§4.2).

### 4.2 Reference machinery (kernel `ScannerMatcher` + execution-verified guard set)

**Which machinery (HOW_TO §4 matcher-kinds table).** The shipped precedents split three ways: GTIN/ISSN/IBAN ship the kernel **`label`** kind (`LabelMatcher(...)` constructed at `gtin_recognition.py:77`, `issn_recognition.py:40`, `iban_recognition.py:76`), ISIN and most other legacy grammars still run a **`RegexStage`** (the unmigrated stage path), and the kernel **`scanner`** kind — `ScannerMatcher(scan=…, boundary=…, emit=…)` — ships in exactly three customers: Language `bcp47_tag_recognition.py:293`, URL `absolute_uri_recognition.py:107`, Phone `e164_recognition.py:105` (`paxman/core/grammar/matchers/scanner.py` — its module docstring still claims "no shipped grammar uses it on the kernel path yet"; stale as of those three). Neither `label` nor a bare regex stage can carry PAN's contextual guards: `LabelMatcher` fixes label + boundary + pattern up front, and on the legacy stage path `PostStage.transform` receives only the `RecognitionMatch` — it can trim the span from `raw_text` alone (E.164 15-digit window precedent, `stages.py:130-155`) but can never see text before `start` or after `end`, so the left-fragment guard and the trailing-date guard are impossible there. The kernel path also short-circuits the stages: when `matchers` is set, `PipelineGrammar.recognize` delegates straight to `run_matchers` and never enters the stage loop (`pipeline.py:36-41`) — hence no `pre`/`regex`/`post` attributes in the grammar below.

GTIN precedent (kernel `label` kind; `paxman/capabilities/GTIN/grammar/gtin_recognition.py:57-61` — exact-length alternation, longest-first, `(?!\w)(?![-]\d)` tail; matcher constructed at `:77`):
```python
_GTIN_BODY = (
    r"(?:(?:\(01\)[\s:-]*|AI\s+01[\s:-]+)?(?:\d[ \-]?){13}\d"
    r"|(?:\d[ \-]?){12}\d|(?:\d[ \-]?){11}\d|(?:\d[ \-]?){7}\d)"
    r"(?!\w)(?![-]\d)"
)
```
ISIN precedent (legacy `RegexStage` path; `paxman/capabilities/ISIN/grammar/isin_recognition.py:20-34` — label branch, glued-label guard, word guards; `RegexStage` at `:56`):
```python
_ISIN_BODY = r"(?:(?ai:ISIN)[\s:-]+)?(?P<compact>(?ai:[A-Z]{2}(?: ?[A-Z0-9]){9} ?[0-9]))"
_GLUED_LABEL_GUARD = r"(?!(?ai:ISIN[A-Z]{2}[A-Z0-9]{9}[0-9]))"
_ISIN_PATTERN = BoundaryGuard.word_only().lookbehind + _GLUED_LABEL_GUARD + _ISIN_BODY + BoundaryGuard.word_only().lookahead
```

**Proposed PAN grammar (single grammar, kernel `ScannerMatcher`):**
```python
import re
from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.core.grammar import BoundarySpec, ScannerMatcher
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.scan_context import ScanContext, View

# Label branch: human field labels only (card number / pan / cc / credit
# card), matched at scan time with a mandatory one-or-more separator — never
# zero-width (glued "PAN4111111111111111" stays MISSING, ISIN/IBAN/BIC
# precedent). Label separators are space/hyphen/colon; the BODY tolerates a
# single [ \-] per gap only (validator.js / braintree evidence); dots/
# underscores/slashes are NOT tolerated in v1 (DEFER, §2.1).
_PAN_LABEL_RE = re.compile(
    r"(?:(?ai:credit[\s-]?card(?:[\s-]?number)?|card[\s-]?number|pan|cc))[\s:-]+"
)

# Body: longest-first 19→12 alternation + guards, compiled once at module
# scope (never inside scan). Two tail guards:
#   _DATE_GUARD    — a branch may not end by absorbing the " 12" of
#                    " 12/27" (fires only when a space+digits group would
#                    terminate at "/", so 4-4-4-4 grouping, expiry words,
#                    and mention pairs are untouched);
#   _ORPHAN_GUARD  — a claim may not end with a 1–11-digit continuation in
#                    the same space/tab/hyphen run (a sub-floor fragment);
#                    a ≥12 continuation is a separate mention and is left
#                    for the next scan position (two matches).
_DATE_GUARD = r"(?!\s\d+/)"
_ORPHAN_GUARD = r"(?!(?:[ \t\-]?\d){1,11}(?![0-9/]))"
_PAN_BODY_RE = re.compile(
    BoundaryGuard.word_only().lookbehind
    + "(?:"
    + "|".join(
        rf"(?:\d{_DATE_GUARD}[ \-]?){{{n - 1}}}\d" for n in range(19, 11, -1)
    )
    + ")"
    + BoundaryGuard.word_only().lookahead
    + _ORPHAN_GUARD
)

_SOFT_RUN = frozenset("0123456789 \t-")


def _left_soft_run_digits(subject: str, body_start: int) -> int:
    """Digits in the space/tab/hyphen run ending just before ``body_start``."""
    i = body_start
    while i > 0 and subject[i - 1] in _SOFT_RUN:
        i -= 1
    return sum(1 for ch in subject[i:body_start] if "0" <= ch <= "9")


def _pan_scan(view: View, pos: int) -> tuple[int, str] | None:
    subject = view.subject
    label = _PAN_LABEL_RE.match(subject, pos)
    if label is not None:
        body_start = label.end()
    else:
        body_start = pos
        if not ("0" <= subject[pos] <= "9"):
            return None
    # Left joined-run guard: 1–11 soft-joined digits before the claim start
    # mean a longer run that must be judged from its own origin — never
    # carved from inside (double-space/tab inner starts, 20-run inner
    # starts). Python, because Python re has no variable-width lookbehind
    # (see notes).
    frag = _left_soft_run_digits(subject, body_start)
    if 1 <= frag <= 11:
        return None
    m = _PAN_BODY_RE.match(subject, body_start)
    if m is None:
        return None
    # Span starts at pos (label included when matched). The engine discards
    # this payload (scanner.match: end, _notation = res) and rebuilds
    # notation in _pan_emit — emit owns the digits filter.
    return (m.end(), m.group(0))


def _pan_emit(span: tuple[int, int], ctx: ScanContext) -> PANNotation:
    s, e = span
    digits = "".join(ch for ch in ctx.text[s:e] if "0" <= ch <= "9")
    return PANNotation(digits=digits, compact=digits)


_PAN_SCANNER = ScannerMatcher(
    scan=_pan_scan,
    boundary=BoundarySpec.WORD,
    emit=_pan_emit,
)


class PANRecognitionGrammar(PipelineGrammar[PANNotation]):
    """PAN recognition — 12–19 digits, space/hyphen grouped, optional label."""

    name = "pan_recognition"
    semantics = "pan_recognition"
    single_value = True
    matchers = (_PAN_SCANNER,)
```

*Notes on fidelity vs GTIN/ISIN (four guards; every claimed outcome in these notes is execution-verified — see "Execution verification" below):*

- **Machinery wiring:** scan/emit/`ScannerMatcher`/`matchers` shaped exactly like `bcp47_tag_recognition.py:249-309` (shipped `scanner` customer, same `boundary=BoundarySpec.WORD`). `_pan_scan` returns `(end, raw)` to satisfy the `ScanFn` contract, but `scanner.match` discards that payload (`end, _notation = res`) and the engine rebuilds notation via `emit_fn((o_s, o_e), context)` (`engine_loop.py:109-175`) — so `_pan_emit` is the single place the digit filter runs, and `validate_emit` enforces span/raw_text invariants at matcher construction.
- **Guard 1 — word guards:** leading `BoundaryGuard.word_only()` (`(?<!\w)`) + trailing `(?!\w)` in the body, plus `BoundarySpec.WORD` re-checked by `ScannerMatcher.match` at each hit (boundary rejection is treated as a miss — advance `pos+1`, span not consumed), block letter/digit-glued runs (`X4111…`, `4111…Y`, `A4111…B`). Glued *labels* (`PAN4111111111111111`) are blocked structurally: the label branch requires a mandatory `[\s:-]+` separator, and at the body start the lookbehind rejects a letter-preceded digit — this replaces the old explicit `_PAN_GLUED_GUARD` (ISIN/IBAN/BIC fused-label precedent, outcome unchanged: `MISSING`).
- **Guard 2 — trailing date guard** `(?!\s\d+/)` per repetition: a 17/18-branch over `4111111111111111 12/27` would absorb ` 12`; the guard fires only when a space+digits group terminates at `/`, so the 16-branch claims the PAN span alone. Groupings (no `/` follows), expiry *words* (`exp 01/28`), and spaced/hyphen/slash/comma mention pairs are untouched — all verified.
- **Guard 3 — joined-run orphan guard** `(?!(?:[ \t\-]?\d){1,11}(?![0-9/]))`: refusing to end a claim with a 1–11-digit continuation in the same soft run is what makes `4111 1111 1111 1111`, `4111\t1111\t1111\t1111`, `4111 1111 1111 1111 0000`, `4111-1111-1111-1111-0000`, and `4111111111111111 1234` `MISSING` instead of a false 16-`SUCCESS`. A continuation ≥12 digits is a separate mention (the scan resumes there → two matches), which is what admits hyphen/slash-adjacent pairs such as `4111111111111111-5555555555554444` — verified. This supersedes GTIN/ISBN's hyphen-only `(?![\-]\d)` anti-truncation tail: it is separator-general (space/tab/hyphen) and it no longer blocks mention pairs adjacent via hyphen or slash, which the old tail did. The `(?![0-9/])` terminator exempts date fragments — ` 12/27` keeps claiming via Guard 2 while a sub-floor ` 1234` orphan still fires.
- **Guard 4 — left joined-run guard (scan-side Python):** 1–11 digits in the space/tab/hyphen run ending at the claim start means we are starting *inside* a longer run (second-group starts of double-space/tab inputs, inner starts of 20-runs) → refuse; the run must be judged from its own origin, where the floor and the body guards decide. Python, because Python `re` forbids variable-width lookbehind (`re.error: look-behind requires fixed-width pattern` on `(?<!\d{1,11}[ \-])`); expressing this in-pattern would need every fragment length (1–11) × every gap shape enumerated as separate fixed-width (possibly nested) lookbehind clauses — dozens of clauses for no readability gain (nested fixed-width lookbehinds *do* compile, so this is an enumeration-cost argument, not a hard impossibility). Evaluated at `body_start` (after the label), not at label start.
- **Strip/Unicode discipline:** the ASCII-digit filter lives in `_pan_emit` (ISIN precedent `ch.isascii() and ch.isalnum()` narrowed to digits for PAN). `(?ai:...)` on the label branch plus `BoundaryGuard.word_only()` staying Unicode-aware mirrors IBAN `:25` ASCII discipline: fullwidth digits (`４１１１…`) and non-ASCII homoglyphs are rejected while word-boundary decisions stay exact vs `re` across the full codepoint space.
- **Longest-first alternation** (19 down to 12) guarantees only 12–19 total via branch structure, never 11 or 20 — GTIN `8/12/13/14` precedent generalized to a contiguous range. An unbounded `(?:\d[ \-]?){11,18}\d` repetition is equivalent but the explicit alternation documents the range and keeps the longer-wins backtrack path obvious; either is acceptable, the alternation is recommended for review clarity.
- **Whitespace tolerance:** single `[ \-]?` per inter-digit gap covers all attested groupings (4-4-4-4, 4-6-5, 6-6-4, ungrouped) because grouping is grouping-agnostic after stripping. Double-space/tab inputs are resolved by Guard 4: a claim may only start at the run's origin, and an origin claim over an irregular run fails the body guards → **nothing is claimed** (`MISSING`, no prefix carve, no false `INVALID`). The earlier draft's "second space left outside the span" description was wrong and is replaced by this; `\s`-widening stays an open decision (§13 row 9), consistent with GTIN's `HZ` double spaces staying `MISSING` for ISIN.
- **Kernel path only:** no `StandardPre`/`RegexStage` — with `matchers` set, `recognize()` delegates to `run_matchers` and never enters the stage loop (`pipeline.py:36-41`), so stage attributes would be dead fields. The `anchors` prefilter (`AnchorSet`, e.g. `HasDigit().as_set()` from `anchors.py`, honored by `engine_loop` before scanning) remains available if word-guard no-op positions ever show up in profiles.

**Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a concrete mechanism — compact/space/dash/Amex/Diners/mixed → separator-interleave alternation; label prose → `_PAN_LABEL_RE` at scan + ASCII-digit filter in `_pan_emit`; quoted/bracketed → word guards + `BoundarySpec.WORD` policy (verified: quoted/paren forms claim); expiry-attached → Guard 2 claims the PAN span only (verified ` 12/27` and ` exp 01/28`); multi-mention rows → non-overlapping scan advance (verified spaced/hyphen/slash/comma pairs). Every DEFER row (dot/underscore/slash) names the mechanism that would handle it (widen separator class to `[\s.\-/_]` in a community `extra_grammars` variant). Every REJECT row names the guard that excludes it: masked/truncated/token → charset + floor; OCR → strict `\d`; expiry-glued → Guard 2 span discipline; **irregular whitespace (double-space/tab) → Guard 4 — documented non-recognition (§2.1 row 8, Open Decision §13 #9)**.

**Execution verification:** the pattern + four guards above were executed against every row of §8 (scanner-loop emulation reproducing `ScannerMatcher.match` exactly: non-overlapping advance to `end` on hit, boundary rejection and miss both advance `pos+1` without consuming) — each §8 row's stated resolution is the observed output, together with the §2.1/§2.2 fixtures, prose cases, and newline-adjacent pairs. The two structural facts behind Guard 4's placement were also re-checked against `re`: variable-width lookbehind raises `re.error: look-behind requires fixed-width pattern`, nested fixed-width lookbehinds compile (hence "enumeration cost", not impossibility). The harness is throwaway; at implementation time these become the failing-first tests of §12.

**A documented trade-off (same-line prose predecessors):** a sub-floor fragment cannot split a soft run at the space — `12` has no in-range branch ending there — so `order 12 4111111111111111` claims the whole soft-joined 18-digit run from its origin → `INVALID` (Luhn), exactly symmetric with `4111111111111111 12` → 18-claim (§8 #23) and with a ≥12-floor predecessor splitting correctly (`123456789012345 4111111111111111` → two matches, verified). Only a `/`-terminated date fragment (Guard 2) or a floor-satisfying predecessor splits. A line break is a hard boundary (soft-run class excludes `\n`): `total 12\n4111111111111111` → `SUCCESS`, verified. Same-line prose digits therefore poison a PAN mention into `INVALID`, not into `MISSING` — deterministic, Luhn-gated, and worth an §8 row over an implicit silence.

**12–19 as one grammar vs many:**

- **(Recommended) Single grammar** with range alternation — minimal containment complexity (`_dedup_spans` longer-wins within one grammar handles prefix sub-runs), single `semantics` id, one rule affinity.
- **Alternative (rejected):** per-length grammars (`pan12_recognition` … `pan19_recognition`) with coalesced `semantics = "pan_recognition"` (HOW_TO_ADD_NEW_GRAMMAR.md option A). Only introduces eight wiring points to record provenance of the spelled length — not needed, provenance is the authority (ISO 7812-1), not the length. Per-brand grammars (visa/mc/amex) are rejected harder: brand is secondary data, and brand-prefix regexes overlap (e.g. `65` Discover vs `65` Troy co-brand), guaranteeing cross-grammar spurious `AMBIGUOUS`.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md Recognition Pipeline Contract)

- Grammar emits **span-bearing** `RecognitionMatch[PANNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `ScannerMatcher.match` walks positions calling `_pan_scan(subject, pos)`; on a hit it records `(pos, end)` (span start = scan position — the label is included when the label matched), enforces `BoundarySpec.WORD` at the hit (rejection is treated as a miss — advance `pos+1`, span not consumed), and advances to `end`; the engine then builds `RecognitionMatch(notation=_pan_emit(span, ctx), start, end, raw_text)` (`engine_loop.py:109-177`; the scan payload notation is discarded). Scan functions must not mutate `text` (`View`/`ScanContext` only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups. For PAN (single shipped grammar initially), dedup keeps the 19-digit match over any 12–18-digit prefix at the same start.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

### 4.4 Guard boundaries against sibling grammars

PAN vs sibling digit grammars: PAN `12–19 digits + Luhn` vs GTIN `8/12/13/14 + GS1 Mod-10` vs Phone E.164 `7–15 digits + leading +` vs IMEI `15 digits + Luhn` (future) vs ISIN `12 alnum with letters` vs IBAN `15–34 alnum with letters`.

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| PAN | `12–19` ASCII digits, `[ \-]?` interleave, optional human label | digit at start, `(?<!\w)` + scan-time left joined-run guard (§4.2 Guard 4) | `(?!\w)` + joined-run orphan guard `(?!(?:[ \t\-]?\d){1,11}(?![0-9/]))` + date guard `(?!\s\d+/)`; `BoundarySpec.WORD`; only 12–19 accepted |
| GTIN | `8/12/13/14` digits, `[ \-]?` interleave, `(01)`/label branch | digit or `(`/label at start | `(?!\w)(?![-]\d)`; 12–14 overlap with PAN is check-discriminated (GS1 Mod-10 vs Luhn), not length-discriminated |
| Phone E.164 | `7–15` digits with mandatory `+` (shipped `e164_recognition`) | `+` required | `+`-anchor means bare PAN runs never collide; grouped PAN with spaces vs national phone with spaces is capability-selected, not grammar-competing |
| IMEI (future) | `15` digits, Luhn | digit at start | Length/check-identical to 15-digit PANs — domain-selected (device vs payment), not lexically separable; document, do not guard |
| ISIN/IBAN/LEI | letters mandatory (`CC`/`[A-Z]`) | letter-anchored | All-digit PAN runs never match letter-anchored bodies; disjoint by charset |

Prefix-aware PAN detection (`PAN:`/`card number:` label) does not clash with sibling labels (`IBAN:`, `GTIN:`, `ISIN:`); case-insensitive `PAN` vs `AN` substrings are distinct under the glued-`reject` guard.

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

The new grammar declares a non-empty `semantics` string; every validating `Rule` declares `target_semantics: frozenset[str]` naming the semantics ids it validates. The engine `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. For a single shipped PAN grammar, the natural id is:

- `semantics = "pan_recognition"` (identity id).

Recommendation: start with identity `pan_recognition`; coalesce only if a second grammar (e.g. `pan_compact_recognition` for a future strict-compact variant) is later added — coalescing is option A in HOW_TO_ADD_NEW_GRAMMAR.md. Brand rules (if shipped) target the same id; they do not get their own semantics because brand is not a distinct recognition meaning (ADR-0012 corroboration pattern: PARSER + LOOKUP_TABLE on the same recognition).

### 4.6 `single_value` — one mention per call vs batch processing

Shipped capabilities (GTIN, ISIN, ISBN, IBAN, LEI) all set `single_value=True`, consistent with Paxman "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). Test-card tables and vault-migration lists legitimately contain N PANs per document, so batch extraction will want multi-mention mining.

Recommendation: **initial `single_value=True`** (matches shipped precedent and the single-field checkout use-case), with a documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A separate free-text community grammar with `single_value=False` can be offered via `extra_grammars` for batch-processing callers when needed.

---
## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO + IEC** — International Organization for Standardization jointly with the International Electrotechnical Commission, Technical Committee **ISO/IEC JTC 1/SC 17** (Cards and security devices for personal identification), subcommittee SC 17 responsible for the 7812 series. |
| **Registration Authority (RA)** | **American Bankers Association (ABA)** — designated RA for Issuer Identification Numbers (IINs). Responsible for receiving IIN applications, allocating IINs, and publishing the ISO Register of IINs (licence-only, not public). BIN administration handoff to **CUSIP Global Services** (US National Numbering Agency) formalized Feb 2024 (secondary: Digital Transactions report via Wikipedia citation). |
| **Spec name** | `ISO/IEC 7812 — Identification cards — Identification of issuers — Part 1: Numbering system` + `Part 2: Application and registration procedures` |
| **Current edition (Part 1)** | **ISO/IEC 7812-1:2017 (5th ed., published 2017-01-03)** — current, `90.93 Confirmed` (systematic review closed 2022-06-14, confirmed 2022-10-27), cancels 2015, ICS 35.240.15, 7 pages. See lineage table below. |
| **Current edition (Part 2)** | **ISO/IEC 7812-2:2017 (5th ed., published 2017-01-03)** — current, `90.93 Confirmed` 2022-10-27, 12 pages. Specifies application/registration procedures for IINs issued per Part 1. |
| **Check character system** | **Luhn MOD-10 double-add-double** (ISO/IEC 7812-1:2017 Annex B: "Luhn formula for computing modulus-10 'double-add-double' check digits"; US Patent 2,950,048, H. P. Luhn, filed 1954-01-06, granted 1960-08-23, expired, public domain). Final digit of PAN; valid iff full-PAN digit-sum `mod 10 == 0`. |
| **IIN/BIN reference** | IIN = first 6 or 8 digits incl. MII (2017 revision extends fixed-6 to 6-or-8); BIN = industry synonym (RFC 4949 §33, cited secondary via Payment card number wiki). ISO Register of IINs is licence-only. |
| **Related specs** | ISO/IEC 7812-2:2017 (registration); US 2,950,048 (check math); RFC 4949 §33 (BIN term); PCI DSS Req. 3/4 + PCI SSC 8-digit-BIN blog (handling caveat only, not validation authority). |

**Structure (spec abstract + secondary structural synthesis):**

ISO catalogue abstracts define scope only: Part 1 "specifies a numbering system for the identification of the card issuers, the format of the issuer identification number (IIN) and the primary account number (PAN)"; Part 2 "specifies the application and registration procedures for IINs issued in accordance with Part 1". Field decomposition below is SECONDARY (Wikipedia synthesis of the paywalled standard) — structurally stable across summaries and suitable as the capability hypothesis, but the paid §4–5 / Annex B text must be verified before freezing rule section numbers:

```
PAN = IIN (6 or 8 digits, incl. MII) + Individual Account Identifier (variable) + Check digit (1, Luhn)
Ceiling: max 19 digits total (unchanged by 2017 revision).
With 6-digit IIN: account field max 12 digits (6 + 12 + 1 = 19).
With 8-digit IIN: account field max 10 digits (8 + 10 + 1 = 19).
Charset: decimal digits 0–9 only. Spaces/hyphens are presentation grouping.
Check: Luhn double-add-double over the full digit string, sum mod 10 == 0.
```

- Formal charset: `^[0-9]{12,19}$` compact (payment scope; ISO ceiling 19, operational floor 12 — see §5.4); grouped display `(?:\d[ \-]?){11,18}\d` spaces/hyphens presentation-only, canonical stripped.
- MII (first digit) semantics: `0` ISO/TC 68 + industry, `1`–`2` airlines, `3` travel/entertainment, `4`–`5` banking/financial, `6` merchandising + banking, `7` petroleum + future, `8` healthcare/telecom + future, `9` national bodies — informative only, must not reject (secondary MII table, §5.4).
- Special IIN ranges (secondary, ISO 7812-1 §4.2 per Wikipedia): `00` non-issuer financial (ISO 8583-1), `80 CCC` healthcare (national RAs; EHIC appends 5-digit insurer id), `89 EE(E)` telecom/ITU-T (SIM ICCIDs; E.164 country), `9 CCC` national bodies (`CCC` = ISO 3166-1 numeric-3) — non-payment IIN uses, out of credit-card scope (§5.4).
- Luhn directionality: generation (payload → check: `(10 - (s mod 10)) mod 10`) vs validation (full PAN → verdict: `sum mod 10 == 0`); right-to-left doubling; zero-padding invariant (leading zeros do not change outcome).
- Worked vectors (secondary, Luhn article + patent): payload `1789372997` → check `4` → `17893729974` (sum 56); payload `7992739871` → check `3` → `79927398713`; patent payload `4872148` → sum 6 → check `4` → `48721484`. These are 8-/11-digit **algorithm references below the 12-floor** — Luhn-math units only, never PAN fixtures (§7.1).
- Examples from evidence: `4111111111111111` (Visa test), `5555555555554444` (Mastercard test), `378282246310005` (Amex test), `371449635398431` (Amex test 2), `6011111111111117` (Discover test), `3530111333300000` (JCB test), `36050234196908` (Diners 14), `4716461583322103` + `4716-2210-5188-5662` + `4929 7226 5379 7141` (validator.js fixtures).

**Lineage table (ISO/IEC 7812-1 editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 7812 (series, pre-split) | 1989 | withdrawn | First publication as single-part `ISO 7812` (secondary: Wikipedia) |
| ISO/IEC 7812-1:1993 | 1993 | withdrawn | 1st Part-1 edition (split into -1 Numbering / -2 Procedures) |
| ISO/IEC 7812-1:2000 | 2000-09-07 | withdrawn 2006-10-13 | 2nd ed., 6 pages; cancels/replaces 1993; + Cor 1:2001 (`/standard/36326.html`) |
| ISO/IEC 7812-1:2006 | 2006-10-13 | withdrawn 2015-07-31 | 3rd ed., 7 pages; cancels/replaces 2000; scope "issuers of cards that require an IIN to operate in interchange" |
| ISO/IEC 7812-1:2015 | 2015-07-31 | withdrawn 2017-01-03 | 4th ed., 6 pages; cancels/replaces 2006; fast-tracked to revision 2015-11-10 (~3 months after publication); catalogue abstract erroneously reads "7812-1:2012" (iso.org copy error, lifecycle fields authoritative) |
| ISO/IEC 7812-1:2017 | 2017-01-03 | current, 90.93 Confirmed 2022-10-27 | 5th ed., 7 pages; cancels/replaces 2015; key change: IIN 6 → 6-or-8 digits; DIS 2016-05-30→08-31, FDIS Nov–Dec 2016 |

Part 2 mirrors this (checked directly): ISO/IEC 7812-2:2015 (4th ed., withdrawn 2017-01-03) → ISO/IEC 7812-2:2017 (5th ed., 2017-01-03, current, confirmed 2022-10-27, 12 pages).

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO/IEC (JTC 1/SC 17) | `ISO/IEC 7812-1:2017` | `2017-01` (5th ed., current) | `https://www.iso.org/standard/70484.html` | `active` — supersedes 2015 | `2017` | `specification` |
| ISO/IEC (JTC 1/SC 17) | `ISO/IEC 7812-1:2015` | `2015-07` (4th ed.) | `https://www.iso.org/standard/66011.html` | `withdrawn` 2017-01-03 | `2015` | `specification` |
| ISO/IEC (JTC 1/SC 17) | `ISO/IEC 7812-1:2006` | `2006-10` (3rd ed.) | `https://www.iso.org/standard/39698.html` | `withdrawn` 2015-07-31 | `2006` | `specification` |
| ISO/IEC (JTC 1/SC 17) | `ISO/IEC 7812-1:2000` | `2000-09` (2nd ed.) | `https://www.iso.org/standard/31443.html` | `withdrawn` 2006-10-13 | `2000` | `specification` |
| ISO/IEC (JTC 1/SC 17) | `ISO/IEC 7812-2:2017` | `2017-01` (5th ed., current) | `https://www.iso.org/standard/70485.html` | `active` | `2017` | `specification` |
| ABA (ISO RA) | `ISO Register of IINs` | `Rolling (licence-only)` | `https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html` (RA listing context) | `active` — rolling, non-public | `2017` | `registry` |
| H. P. Luhn / USPTO (public domain) | `US Patent 2,950,048` | `1960-08-23` (filed 1954-01-06) | `https://patents.google.com/patent/US2950048A/en` | `active` (expired = public domain) | `1960` | `specification` |
| Brand networks (secondary) | `Brand IIN/length tables` | `Rolling` | `https://en.wikipedia.org/wiki/Payment_card_number` (secondary synthesis; brand specs authoritative per-network) | `active` — rolling, secondary | `2026` | `registry` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical PAN rule citing a withdrawn edition (e.g. ISO/IEC 7812-1:2006 for the fixed-6-digit IIN era) would carry `lifecycle="withdrawn"` or `"superseded"`. For PAN, the initial rule is expected `active` (2017). The IIN Register is `kind="registry"` `lifecycle="active"` (rolling, licence-only — no snapshot ships, so no rule cites it as shipped authority). Brand tables are secondary — if shipped they carry explicit secondary provenance, never ISO authority. PCI DSS carries **no** `Provenance` in this capability.

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_7812_1_ed2017.py` | `authority="ISO/IEC"`, `specification_name="ISO/IEC 7812-1:2017"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/70484.html"`, `version="2017"`, `lifecycle="active"`, `publication_year=2017` | `Section 5-pan-structure-luhn` (PAN structure: 12–19 digits + Luhn Annex B double-add-double; section number TBC against paid text) | Generic structure: length `12–19`, ASCII digits, `compact == digits` consistency, full-PAN Luhn `sum mod 10 == 0`; `normalize()` returns compact identity |
| `rules/brand_prefix_ed2026.py` *(optional — gated secondary, or deferred to community extension)* | `authority="Brand networks"`, `specification_name="Brand IIN/length tables (secondary)"`, `kind="registry"`, `reference_url="https://en.wikipedia.org/wiki/Payment_card_number"`, `version="Rolling 2026"` | `Section *-brand-prefix-membership` (IIN prefix + per-brand length allowlist) | Whether the PAN's leading digits + length match a known brand range (Visa `4`, Mastercard `51–55`/`2221–2720`, Amex `34/37`, …); `requires_features={"include_brand_validation"}`; duplicates Luhn as ADR-0012 corroboration (ISIN/GTIN LOOKUP precedent) — never a waiver of the ISO rule's verdict (§5.3, §7.2, §13 #12) |

*This mirrors ISIN two-file split (ISO 6166 // ANNA Guidelines, PARSER + gated LOOKUP_TABLE) and GTIN three-file split (GenSpecs PARSER // Prefix LOOKUP_TABLE // Verified gated LOOKUP_TABLE). For PAN, only ISO/IEC 7812-1 is mandatory; brand-prefix is optional secondary (exactly like GTIN Verified liveness: gated, snapshot-backed, off by default). ISO/IEC 7812-2 gets **no rule file** — it specifies IIN application/registration procedures, not per-PAN validation logic; citing it as a per-PAN `matches()` authority would be provenance fraud. It is cited in §5.5 context only.*

Each `Rule[PANNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__` in `paxman/core/domain.py:246-271`):

```python
class Section5PANStructureLuhn(Rule[PANNotation]):
    name = "Section 5-pan-structure-luhn"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "PAN structure + Annex B (Luhn double-add-double)"
    target_semantics = frozenset({"pan_recognition"})
    requires_features = frozenset()

    def matches(self, notation: PANNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: PANNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO/IEC 7812-1:2017 lineage** confirmed via `https://www.iso.org/standard/70484.html` (current, 5th ed., 2017-01-03, 90.93 Confirmed 2022-10-27, 7 pp., JTC 1/SC 17, ICS 35.240.15, MA/RA note) and `https://www.iso.org/standard/66011.html` (2015, 4th ed., withdrawn 2017-01-03, 6 pp.) plus `https://www.iso.org/standard/39698.html` (2006, 3rd ed., withdrawn 2015-07-31, 7 pp.) plus `https://www.iso.org/standard/31443.html` (2000, 2nd ed., withdrawn).
- **ISO/IEC 7812-2:2017** confirmed via `https://www.iso.org/standard/70485.html` (current, 5th ed., 2017-01-03, 90.93 Confirmed 2022-10-27, 12 pp., same TC/ICS, application/registration abstract).
- **RA is ABA:** `https://en.wikipedia.org/wiki/ISO/IEC_7812` (secondary: "The registration authority for IINs is the American Bankers Association") + IIN Register licence-only ("only available to institutions who hold IINs… financial networks and processors… sign a licensing agreement") + Feb 2024 CUSIP handoff (secondary). Implication: no public snapshot → no shipped IIN-lookup rule.
- **Luhn location:** `https://en.wikipedia.org/wiki/Luhn_algorithm` (secondary: "It is specified in ISO/IEC 7812-1" + ref "Annex B: Luhn formula for computing modulus-10 'double-add-double' check digits … ISO/IEC 7812-1:2017") + `https://patents.google.com/patent/US2950048A/en` (primary: filed 1954-01-06, granted 1960-08-23, substitution table, tens-complement generation, 0-mod-10 verification).
- **8-digit IIN change:** `https://en.wikipedia.org/wiki/ISO/IEC_7812` (secondary: "In 2015, ISO TC68/SC9 began work… 2017 revision… defined the new eight-digit IIN and outlined a timeline") + PCI SSC primary corroboration `https://blog.pcisecuritystandards.org/8-digit-bins-and-pci-dss-what-you-need-to-know` ("The ISO standard [7812-1:2017] now also defines a format for the use of 8-digit BINs… Some payment brands have already started using the first eight digits").
- **Brand lengths are secondary:** `https://en.wikipedia.org/wiki/Payment_card_number` (secondary IIN-range/length table: Visa 13/16/19, Mastercard 16, Amex 15, Discover 16–19, Diners 14–19, JCB 16–19, UnionPay 16–19, Maestro 12–19, …) — never cite as ISO.
- **Ecosystem Luhn consensus:** `https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/luhn.py` (generic `checksum`/`validate`/`calc_check_digit`, no strip/length/brand) + `https://raw.githubusercontent.com/validatorjs/validator.js/master/src/lib/isCreditCard.js` (strip `/[- ]+/g` + brand regexes + Luhn gate) + braintree/django/omnipay sources (§2.2 table).

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. The ISO 7812-1 rule checks: `digits` is `str`, `isascii()` + `isdigit()`, `12 <= len <= 19`, `compact == digits`, full-PAN Luhn `sum mod 10 == 0` (right-to-left double-alternate, `>9 → -9`). The brand rule (if shipped) checks: leading-digit/length pair in the secondary allowlist (prefix regex + length set per brand) **plus a duplicate Luhn pass** — intentional ADR-0012 corroboration, exactly like ISIN `Section5CountryAndSpecialPrefix` and GTIN `Section2Gs1Prefix` (whose duplicate Luhn/Mod-10 the `RuleStrategy` bullet below already records). Reconciled with §7.2: the brand rule never *reverses* the ISO verdict — braintree's `luhn:false` UnionPay bypass is documented divergence, not adopted — it re-derives the same Luhn result, so a Luhn-invalid UnionPay fails both rules → `INVALID` under every contract (§13 #12). All return `False` for any invalid input, never raise, not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** — returns the **default compact form** (`digits` identity). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability `format_value()` seam only. Both the ISO and the brand rule must return the **same** default string for the same valid notation; candidate dedup `(value, recognition_rule, validation_rule)` keeps agreement at `SUCCESS` (ADR-0012: PARSER + LOOKUP_TABLE on the same recognition corroborate; PARSER alone on LOOKUP-backed semantics would ghost — here the ISO PARSER carries the identity semantics, so the brand LOOKUP corroborates rather than qualifies).
- **`RuleStrategy` choice:** GTIN GenSpecs structure+Mod-10 is `PARSER`, ISIN structure+Luhn is `PARSER`, LEI structure+MOD-97 is `PARSER`; brand/prefix membership in all three is `LOOKUP_TABLE`. For PAN identically: the ISO structure+Luhn rule is `PARSER`; the brand-prefix rule (if shipped) is `LOOKUP_TABLE` (parallel to ISIN `Section5CountryAndSpecialPrefix` LOOKUP_TABLE + intentional duplicate Luhn, GTIN `Section2Gs1Prefix` LOOKUP_TABLE + intentional duplicate Mod-10).

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Three scope cuts, each with cost/benefit:

1. **Length floor 12 (payment scope), ceiling 19 (ISO).** ISO-confirmed fact is only the 19-digit ceiling + variable-length account field (secondary: "maximum total length of the PAN remains at 19 digits"). The commonly cited 8–19 range (Payment card number wiki: "composed of 8 to 19 digits") includes non-payment IIN uses (healthcare `80CCC`, telecom `89EE`, national `9CCC`, `00` ISO-8583). Cost of accepting 8–11: the grammar would claim healthcare/telecom identifiers as PAN candidates (false `INVALID` noise at best, false `SUCCESS` on Luhn-coincidence at worst). Benefit of floor 12: covers the narrowest observed payment PAN (Maestro 12, secondary: braintree `lengths [12…19]`, omnipay `^\d{12,19}$`, django form `MinLengthValidator(12)`). **Recommendation: grammar + ISO rule enforce 12–19; 8–11-digit runs stay `MISSING`.** Document the cut here and in §9; revisit only with paid §5 text confirming a payment-PAN floor.
2. **MII informative only, special ranges out of scope.** MII 0–9 + special `00`/`80CCC`/`89EE`/`9CCC` are IIN-allocation families, not PAN validity signals. The ISO rule must not reject any MII; the brand rule (if shipped) routes only on payment-brand prefixes and returns `False` (not "wrong MII") for non-payment prefixes. Healthcare/telecom 8–11-digit identifiers are already excluded by the length floor.
3. **IIN-6 vs IIN-8 duality is interpretation, not identity.** The 2017 revision admits both parses for the same digits. The ISO rule validates the full PAN (length + Luhn) without asserting an IIN boundary; the brand rule (if shipped) matches on prefix+length pairs that implicitly encode 6- vs 8-digit BINs per brand table (PCI SSC FAQ #1091 varies truncation by BIN length — consult brand per PAN). No notation field, no output format, and no second canonical value encodes the IIN boundary.

Analogy: GTIN `native_length` preserves spelled length because zero-padding changes the string; PAN has no padding transform, so no length-facet rule split is needed. ISIN country/prefix LOOKUP corroborates the PARSER on the same recognition; PAN brand LOOKUP would do the same.

### 5.5 Assignment / registration authority & Registry content

Network: **ABA** as RA (with CUSIP Global Services administering BINs since Feb 2024, secondary) plus **issuing institutions** per IIN (banks, airlines, petroleum, telecom, national bodies per MII) that request IINs and assign account identifiers. The **ISO Register of IINs** (central catalogue) is **licence-only**: available to IIN holders + financial networks/processors under agreement, not downloadable, not redistributable. Each record includes (secondary, IIN-application context): IIN (6 or 8), issuer name/country, contact authority, effective dates. There is no public "connected vs non-connected" liveness flag (unlike SWIFT BIC Directory) and no per-PAN issuance list (unlike ISBN Range Message) — a PAN is validated by algorithm, not by directory membership.

Per **ISO/IEC 7812-2:2017** (`https://www.iso.org/standard/70485.html`):

- RA receives IIN applications, validates issuer eligibility, allocates IINs, and maintains the Register.
- The 12-page text covers application/registration procedures only — no per-PAN check-digit or length-validation logic lives here, which is why Part 2 gets no rule file (§5.2).

Mandatory registration data (context, not validation): issuer identity, requested IIN block, MII justification, contact authority. None of this appears in `rules/data/` — there is no `rules/data/` for v1 (no redistributable authority table exists; brand tables are secondary and ship — if at all — as explicitly-secondary gated data).

---
## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman.core.capability_contract.py`), never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class CreditCardContract(CapabilityContract):
    """User-facing contract for CreditCard capability.

    Default ``pan`` is the compact contiguous digit string (ISO wire form).
    ``grouped`` re-inserts single-space grouping for human readability.

    Formats (ADR-0011 classes): ``grouped`` — encoding (strip/re-group
    reversible without side input; string-exact param-free pre-image:
    grouped output re-enters the default contract to the same compact).

    Masked (``XXXX XXXX XXXX 1234``), truncated (first-6/last-4), and
    tokenized forms are projections over PAN information and are never
    offered — a deliberately waived projection would need an ADR-recorded
    waiver instead (none exists).

    Attributes:
        capability_name: Fixed to "credit_card" (not user-settable).
        output_format: Canonical output format — "pan" default,
            "grouped" offered. Optional — None/"default"/"pan"
            all resolve to "pan".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
        suppress_common_words: Suppress common-word boundary claims.
        include_brand_validation: Enable secondary brand-prefix lookup
            (default False). When True, adds brand provenance via
            Section *-brand-prefix-membership.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "pan"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped"})

    capability_name: str = field(default="credit_card", init=False)
    include_brand_validation: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For PAN, `pan` (compact digits) is the machine canonical form (ISO wire, DB key, hash input); `grouped` is the human 4-4-4-4 / 4-6-5 rendering.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format`; `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order (first-five order is pinned by `tests/unit/test_capability_surface.py`), then `suppress_common_words: bool = False` (base field, `capability_contract.py:56` — shipped `create_contract` shapes forward it, GTIN `capability.py:57`), then capability-specific params (`include_brand_validation`). `include_brand_validation` is added only with the brand rule; a brand-less v1 omits the field.
- `active_grammars` is omitted (base returns `None`, engine runs every shipped grammar). PAN has one always-active grammar; there is no input-shape feature to gate.

**Presentational-only invariant (hard rule — ARCHITECTURE.md The Formatting Seam):**

- `output_format` is a **representation transform, never a recognition or validation signal**. Rules never read it; `normalize()` always returns the default compact form; the engine calls `Capability.format_value(value, output_format, notation)` at result assembly after dedup and status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance**; `Candidate.provenance`, `recognition_rule`, `validation_rule` come from the validating rule.

For PAN, the offered format models the single interchange grouping:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"pan"` (default) | `4111111111111111` / `378282246310005` | Compact, no separators, ASCII digits, DB key, hash input, ISO wire form |
| `"grouped"` | `4111 1111 1111 1111` / `3782 822463 10005` | Single-space grouping for readability: 4-4-4-4 for 16-digit, 4-6-5 for 15-digit Amex, 4-4-4-2/4-6-4 etc. by length (grouping-agnostic re-chunk: groups of 4 from the left, last group takes the remainder — deterministic, reversible) |

*Do not add `masked`, `truncated`, `last_four`, or `bin_plus_4` formats: first-6/last-4 display, `XXXX`-masking, and truncation are projections that discard PAN information (ADR-0011) — a redaction layer owns them, not this capability. Do not add `brand` as a format: brand is validation provenance, not presentation.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from collections.abc import Sequence
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.CreditCard.grammar.pan_recognition import (
    PANRecognitionGrammar,
)
from paxman.capabilities.CreditCard.notation import PANNotation
from paxman.capabilities.CreditCard.contract import CreditCardContract


class CreditCardCapability(Capability[PANNotation]):
    name = "credit_card"

    def get_grammars(self) -> list[Grammar[PANNotation]]:
        return [PANRecognitionGrammar()]

    def get_rules(self) -> list[Rule[PANNotation]]:
        return [Section5PANStructureLuhn()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
        include_brand_validation: bool = False,
    ) -> CreditCardContract:
        return CreditCardContract(
            excluded_rules=tuple(excluded_rules or ()),
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
            suppress_common_words=suppress_common_words,
            include_brand_validation=include_brand_validation,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: PANNotation
    ) -> str:
        if output_format == "grouped":
            # Grouping-agnostic re-chunk: groups of 4 from the left, last
            # group takes the remainder (16 -> 4-4-4-4, 15 -> 4-4-4-3,
            # Amex display 4-6-5 is a brand convention rendered identically
            # after strip; 19 -> 4-4-4-4-3). Deterministic + reversible.
            return " ".join(value[i : i + 4] for i in range(0, len(value), 4))
        return value
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md Step 0 / `tools/new_capability.py`): scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(CreditCard())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

> Note: `grouped` re-chunk above renders 15-digit Amex as `4-4-4-3`, not brand-canonical `4-6-5`. Brand-faithful grouping (`3782 822463 10005`) requires brand knowledge in the presentation layer — brand is secondary validation data, and presentation must not consult rule tables. Two compliant options: (a) ship grouping-agnostic re-chunk (recommended v1 — encoding, reversible, brand-blind); (b) defer `grouped` until brand data ships and render per-brand gaps (braintree `gaps` precedent) behind the same format name. Do not sniff brand from leading digits inside `format_value()` — that re-introduces secondary data into presentation. See §13 row 1.

---
## 7. Validation — Structure + Luhn (+ Optional Brand)

### 7.1 Level 1 — Generic structure + Luhn (always-active PARSER, ISO/IEC 7812-1:2017)

Algorithm (validation direction; generation is the inverse for fixtures):

```
Given notation.digits = d[0..n-1], 12 <= n <= 19, all ASCII 0-9:
  total = 0
  for i, ch in enumerate(reversed(digits)):   # i=0 is the check digit
      v = ord(ch) - 48
      if i % 2 == 1:                           # every second digit from the right
          v *= 2
          if v > 9:
              v -= 9                           # digit-sum of the product
      total += v
  valid iff total % 10 == 0
```

Formal regex (defense-in-depth, mirrors grammar charset — ISIN `_ISIN_RE` precedent, not shared via import):

```python
_PAN_RE = re.compile(r"^[0-9]{12,19}$")
```

Worked examples (secondary vectors, Luhn article + patent). The 8-/11-digit rows are **Luhn-math fixtures only** — below the 12-floor they fail both the grammar's range and `matches()`'s `12 <= len <= 19` gate, so they are never valid PAN fixtures (§12 keeps them as Luhn-helper tests, not recognition/`matches()` tests):

| Vector | Direction | Computation | Result |
|--------|-----------|-------------|--------|
| Payload `1789372997` → check | Generation | Reversed × 2,1,2,1…: 7→14→5, 9, 9→18→9, 2, 7→14→5, 3, 9→18→9, 8, 7→14→5, 1; sum 56; check `(10 - 6) mod 10` | `4` → full `17893729974` |
| Payload `7992739871` → check | Generation | Same procedure; check `(10 - s mod 10) mod 10` | `3` → full `79927398713` |
| Full `79927398713` | Validation | Double-alternate incl. check; total `mod 10` | `0` → valid |
| Full `4111111111111111` | Validation | Visa test PAN; total `mod 10` | `0` → valid |
| Full `378282246310005` | Validation | Amex test PAN (compact twin of `3782 822463 10005`); total `mod 10` | `0` → valid |
| Full `4111111111111112` | Validation | Last digit flipped | `mod 10 != 0` → `INVALID` |
| Patent `4872148` → `4` | Generation | Sum 6 → tens complement | Full `48721484` verifies to 0 |

Letter-free expansion: unlike ISIN (which expands `A=10…Z=35` before Luhn), PAN needs no expansion — the digit string is the Luhn input directly. Zero-padding invariance (Luhn article): leading zeros do not change the Luhn outcome — `00004111111111111111` has the same checksum as its unpadded form (the 20-digit padded string itself is outside the 12–19 gate and never reaches `SUCCESS` — the invariance is about the algorithm, not about a shippable fixture).

### 7.2 Level 2 — Brand/IIN-prefix membership (gated LOOKUP_TABLE, secondary — optional)

If shipped, validates `compact[0:k]` + `len(compact)` against the secondary brand allowlist (Payment card number wiki table + brand specs; braintree `patterns`/`lengths` shape):

| Brand (secondary) | Prefix (secondary) | Length (secondary) | Note |
|-------------------|--------------------|--------------------|------|
| Visa | `4` | 13, 16, 19 | braintree ships `[16,18,19]` (no 13) — divergence proves secondary status |
| Mastercard | `51–55`, `2221–2720` | 16 | 2-series live since 2016-10; validator.js `|`-precedence bug #2717 affects only this regex |
| American Express | `34`, `37` | 15 | 4-6-5 display |
| Discover | `6011`, `644–649`, `65`, `622126–622925` | 16–19 | CUP co-brand range |
| Diners Club Intl | `30`, `36`, `38`, `39` (+ `300–305` sub-ranges) | 14–19 | enRoute `no-validation` legacy excluded |
| JCB | `3528–3589` (+ `2131`/`1800` legacy) | 16–19 | validator.js `^(?:2131|1800|35\d{3})\d{11}$` |
| China UnionPay | `62` (+ `81…` omnipay/validator branch) | 16–19 (braintree `14–19`) | **Luhn divergence:** braintree skips Luhn for UnionPay by default; Paxman does **not** adopt the bypass — the brand rule duplicates Luhn as ADR-0012 corroboration (§5.2/§5.3), never waiving it. Consequence: real Luhn-invalid UnionPay PANs are permanently `INVALID` under every contract — open decision §13 #12 |
| Maestro | `5018/5020/5038/5893/6304/6759/6761–6763` + UK ranges | 12–19 | Narrowest payment floor (12) |
| Others (Mir `2200–2204`, RuPay `60/65/81/82/508`, Troy `9792`/`65`, UATP `1`/15, …) | various | mostly 16–19 | Re-verify per brand spec at implementation; brands change ranges |

Gating: `requires_features={"include_brand_validation"}` (default `False`), exactly like GTIN `include_verified` / ISBN `include_range_validation`. Unknown prefixes with valid Luhn → `SUCCESS` without the brand rule (generic-valid), `INVALID` with the brand rule opted in but unmatched (brand-invalid). This is the valid-vs-brand-valid split (§7.3).

### 7.3 What makes a PAN "valid" vs "brand-valid" vs "issued"

- **valid (generic)** — correct length (12–19) + ASCII digits + Luhn `mod 10 == 0`, always-active PARSER (ISO/IEC 7812-1). `4111111111111111` is valid even if brand tables shift.
- **brand-valid** — generic plus prefix+length in the secondary allowlist, gated LOOKUP_TABLE (`include_brand_validation=True`). `378282246310005` is Amex-brand-valid; a Luhn-valid `9999999999999995`-class run is generic-valid but brand-invalid.
- **issued/live-registered** — actually assigned to a cardholder by an issuer. **No Paxman status exists for this.** The IIN Register is licence-only and per-PAN issuance lists are never published; "issued" is not observable without network inference (forbidden). Like ISBN valid-vs-allocated and ISSN valid-vs-issued, but with the third tier permanently absent by design — document, do not approximate with brand data.

Like GTIN valid-vs-prefix-valid-vs-Verified, ISIN valid-vs-country-valid, IBAN valid-vs-country-valid.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase label | `pan: 4111111111111111` → `SUCCESS` compact | grammar folds label case (`(?ai:…)`), notation label-free |
| 2 | Grouped spacing | `4111 1111 1111 1111` → `SUCCESS` same compact | presentation-only, strip in `_pan_emit` |
| 3 | Dashed grouping | `4111-1111-1111-1111` → `SUCCESS` same compact | same separator class, strip |
| 4 | Amex 4-6-5 | `3782 822463 10005` → `SUCCESS` `378282246310005` | grouping-agnostic strip; same compact as twin |
| 5 | Label present | `PAN: 378282246310005` → `SUCCESS`, span includes label | fused `[\s:-]+` branch; `notation` label-free (ISSN/IBAN precedent) |
| 6 | Glued label | `PAN4111111111111111` → `MISSING` | glued-`reject` guard; no zero-width label fusion |
| 7 | Over-long (20+) | `41111111111111111111` (20) → `MISSING` | alternation ceiling (max 19): at the run origin every branch word-fails or orphan-fails, inner starts are left-guard-blocked → claims nothing |
| 8 | Under-long (11) | `41111111111` → `MISSING` | below floor; grammar claims nothing (not `INVALID` — nothing recognized) |
| 9 | Under-long (8, telecom-shaped) | `89123456` → `MISSING` | non-payment scope; length floor excludes |
| 10 | Luhn-invalid same length | `4111111111111112` → `INVALID` | grammar claims shape, ISO rule rejects (recognized-but-unvalidated) |
| 11 | Masked display | `XXXX XXXX XXXX 1234` → `MISSING` | charset guard (`X`/`•` not `\d`); never `INVALID` |
| 12 | Truncated first-6/last-4 | `411111...1111` (10 digits + dots) → `MISSING` | dots break digit runs; surviving runs under floor |
| 13 | Expiry-glued | `4111111111111111 12/27` → `SUCCESS`, span = PAN digits only | date guard `(?!\s\d+/)` refuses any branch that would absorb ` 12`; the 16-branch passes because the `/`-terminated continuation is exempt from the orphan guard; expiry is a separate capability's mention |
| 14 | Expiry-fused (20-digit run) | `41111111111111111227` → `MISSING` | digit-glued 20-run exceeds ceiling; word guards on every branch tail; no 16-carve |
| 15 | Two distinct in one slice | `4111111111111111 5555555555554444` → `AMBIGUOUS` / `MultipleMentionsError` | single-slice ambiguity; use segmentation |
| 16 | Digit-glued super-run | `14111111111111111` (17) → single 17-claim → `INVALID` (Luhn fails); `41111111111111110` likewise | whole in-range run claimed from its origin (longest-first), deterministic — never a 16-carve, never a hedge between `MISSING` and `INVALID` |
| 17 | Letter-glued run | `X4111111111111111` / `4111111111111111Y` → `MISSING` | `(?<!\w)`/`(?!\w)` + `BoundarySpec.WORD` (GTIN/ISIN precedent) |
| 18 | Hyphen continuation, over-ceiling | `4111-1111-1111-1111-0000` (20 digits) → `MISSING` | joined-run orphan guard refuses every 16-claim, word guards refuse 17–19, left guard blocks inner starts — supersedes `(?![\-]\d)` (which wrongly blocked hyphen-adjacent *pairs*, #24) |
| 19 | Over-ceiling spaced (20) | `4111 1111 1111 1111 0000` → `MISSING` | 16-claim blocked by the orphan guard (4-digit continuation), 17–19 word-fail, inner starts left-guard-blocked — never a false 16-`SUCCESS` |
| 20 | Double space | `4111  1111 1111 1111` → `MISSING` | body cannot cross the double gap; left guard blocks the second-group start — no prefix carve (never a false `INVALID`) |
| 21 | Tab-separated | `4111\t1111\t1111\t1111` → `MISSING` | tab not in the body separator class; left guard blocks inner starts — documented v1 non-recognition (§2.1 row 8, §13 #9) |
| 22 | PAN + CVV4 (soft-joined 20-run) | `4111111111111111 1234` → `MISSING` | 17–19 word-fail, 16 orphan-blocked (4-digit continuation), left guard blocks inner starts — refuse to carve |
| 23 | PAN + CVV3 / prose tail ≤3 (soft-joined ≤19) | `4111111111111111 123` → 19-claim → `INVALID` (Luhn fails on `…123`); `4111111111111111 12` → 18-claim; a Luhn-valid run here → `SUCCESS` | longest-first whole-run claim is indistinguishable from a genuine 19-PAN — Luhn arbitrates (documented trade-off, §4.2) |
| 24 | Hyphen-adjacent pair | `4111111111111111-5555555555554444` → `AMBIGUOUS` (2 matches) | orphan guard admits a ≥12 continuation as a separate mention — supersedes `(?![\-]\d)`, which blocked the first claim |
| 25 | Soft-joined prose predecessor | `order 12 4111111111111111` → 18-claim → `INVALID` | atomic joined-run claim (§4.2 trade-off); the same digits after a line break → `SUCCESS` (verified) |

Every row above is an **observed** outcome: the §4.2 pattern + guards were executed over this table (scanner-loop emulation of `ScannerMatcher.match` — non-overlapping advance, boundary rejection and miss both `pos+1`), together with the §2.1/§2.2 fixtures, label/quoted/prose variants, and newline-adjacent pairs (§4.2 "Execution verification").

---
## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid compact/grouped/dashed/labelled, Luhn passes | `SUCCESS` → compact digits | single canonical via ISO structure + Luhn |
| Valid alternative spacing/case/label (`4111 1111…`, `pan: …`) | `SUCCESS` (same compact) | presentation-only dedup (`compact` identity) |
| Luhn-invalid same-length (`4111111111111112`, `5398228707871528`) | `INVALID` | structural failure, ISO rule rejects; grammar claimed |
| No runs of 12–19 digits (`411111`, `Visa`, `XXXX…1234`) | `MISSING` | no grammar recognized anything |
| Two distinct valid in one slice | `AMBIGUOUS` / `MultipleMentionsError` | single-slice ambiguity, use segmentation |
| 12-digit Maestro-shape, Luhn-valid | `SUCCESS` | floor-inclusive payment scope |
| 8–11-digit runs (telecom/health-shaped) | `MISSING` | non-payment scope cut (§5.4), grammar claims nothing |
| 20+-digit runs (compact, spaced, dashed) | `MISSING` | ceiling + word guards + joined-run orphan guard; no 16-carve (§8 #7/#19/#18) |
| Brand-gated input (if `include_brand_validation=True` and prefix+length unmatched, Luhn-valid) | `INVALID` | secondary authority feature gating (dropped-rule vs kept-rule split) |
| UnionPay-shape with valid Luhn | `SUCCESS` (ISO rule) | brand rule duplicates Luhn as corroboration, same verdict — never waives (§5.3) |
| UnionPay-shape, Luhn-invalid (real legacy cards exist) | `INVALID` under every contract | ISO Luhn is brand-blind; braintree's `luhn:false` bypass not adopted — §13 #12 |
| Same-line soft-joined prose digits (`order 12 4111111111111111`) | `INVALID` (18-claim) or `SUCCESS` | atomic joined-run claim, Luhn arbitrates (§4.2 trade-off, §8 #25) |

---
## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py CreditCard --name credit_card --authority "ISO/IEC" --spec-name "ISO/IEC 7812-1:2017" --spec-url "https://www.iso.org/standard/70484.html" --publication-year 2017
```

Creates 13 files + one edit: `paxman/capabilities/CreditCard/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single `--spec-name` covers one provenance (Part 1). Part 2 gets no rule file (§5.2) — no second provenance to add. The optional brand-prefix file (secondary) is added manually with its own `PUBLICATION` when the gated rule ships, or deferred to a community extension.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[PANRecognitionGrammar()]`, `active_grammars` omitted for initial design (base `None` runs every shipped grammar), grammar carries `name = "pan_recognition"` and non-empty `semantics = "pan_recognition"`.
- `get_rules()` returns `[Section5PANStructureLuhn()]` (+ optional `SectionBrandPrefixMembership()` when the gated secondary ships).
- `create_contract()` opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) then `suppress_common_words: bool = False` (base field, forwarded) then `include_brand_validation: bool = False` (only when the brand rule ships) — same order and shape as GTIN `capability.py:50-59`.

### 10.3 Cross-cutting invariants (fail review if violated)

- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports (import only from `paxman.core`, import-linter enforced); no rule-layer imports in grammars (semantic purity gate).
- No `output_format` token in any `paxman/capabilities/*/rules/` module (source-scan `tests/unit/test_rule_output_format_purity.py`).
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts; `target_semantics` / `requires_features` are `frozenset` (exact type, not `set`).
- Deterministic by construction: same input + contract + library snapshot → same output. No network inference (IIN Register is never queried live).
- PCI handling: no full-PAN logging in tests beyond public test vectors; no masked/truncated acceptance; docs carry the §1 handling warning.

---
## 11. Recommended File Layout (mirrors GTIN and ISIN)

```
paxman/capabilities/CreditCard/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── pan_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_7812_1_ed2017.py
    ├── brand_prefix_ed2026.py        # optional gated secondary (or deferred)
    └── data/                         # only if brand layer adopted
        └── brand_prefix.py           # secondary prefix+length allowlist
```

Per-registry data module shape (parallel to GTIN `rules/data/gs1_prefix.py`, ISIN `rules/data/country_codes.py`):

```python
# rules/data/brand_prefix.py  (SECONDARY — brand specs, never ISO authority)
# Prefix ranges as (start, end) int intervals + allowed lengths per brand.
BRAND_PREFIXES: tuple[tuple[str, tuple[tuple[int, int], ...], frozenset[int]], ...] = (
    ("visa", ((4, 4),), frozenset({13, 16, 19})),
    ("mastercard", ((51, 55), (2221, 2720)), frozenset({16})),
    ("american-express", ((34, 34), (37, 37)), frozenset({15})),
)
```

Brand data ships only with the gated rule and explicit secondary citation; v1 without brand has no `rules/data/`.

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and GTIN §9)

- Grammar tests: valid compact 13/15/16/19, spaced 4-4-4-4, dashed, Amex 4-6-5, Diners 14, mixed separators, lowercase/uppercase labels (`pan:`/`PAN:`/`CC:`/`card number:`), glued-label negative (`PAN4111…` → `[]`), multiple matches, incompatible formats (masked `XXXX…`, truncated, token, 11-digit, 20-digit, letter-glued `X4111…`), empty input, span invariants (`start`/`end`/`raw_text`, label-inclusive span), `name`/`semantics`/`single_value`, boundary-guard negatives — plus one positive vector per §2.1 RECOGNIZE form; **guard-set negatives/positives from the §4.2 execution matrix**: double-space `4111  1111 1111 1111` → `[]`, tab `4111\t1111\t1111\t1111` → `[]`, compact/spaced/hyphen-20 → `[]`, `4111111111111111 1234` → `[]`, expiry `4111111111111111 12/27` → single 16-digit span (date excluded), `4111111111111111 123` → single 19-digit span, two-mention adjacency positives (space/hyphen/slash/comma-separated pairs → 2 matches), digit-glued 17-run → single 17-span, `order 12 4111111111111111` → single 18-span, and scanner-loop discipline (boundary rejection advances `pos+1` without consuming).
- Rule tests: ISO structure+Luhn valid vectors (`4111111111111111`, `378282246310005`, `6011111111111117`, `36050234196908`, `371449635398431`, `4222222222222`; the 8-/11-digit references `79927398713`/`17893729974`/`48721484` are **Luhn-helper fixtures only** — below the floor they fail `matches()`'s `12 <= len` gate), variant inputs (grouped/dashed/labelled normalize to identical compact), invalid (Luhn-flipped `4111111111111112`, validator.js `5398228707871528`, 11-digit, 20-digit, non-digit, `compact != digits` tamper), `normalize` exact compact identity, provenance attributes (`authority="ISO/IEC"`, `kind="specification"`, `lifecycle="active"`, `publication_year=2017`), `name`/`strategy=PARSER` conventions, `target_semantics`/`requires_features` frozenset types; brand LOOKUP rule (if shipped): prefix+length valid/invalid, duplicate-Luhn corroboration (Luhn-invalid UnionPay → `False` from **both** rules — no waiver, §5.3), `requires_features={"include_brand_validation"}` gate, `kind="registry"` secondary provenance.
- Capability tests: notation frozen/hashable/slots + `compact == digits` invariant, wiring counts (1 grammar, 1–2 rules), grammar/rule name conventions, `format_value` round-trips (`pan` identity, `grouped` re-chunk), `create_contract` factories (common block order + `suppress_common_words` default `False` + `include_brand_validation` default `False`).
- Integration: `MISSING` (short/masked/letter-glued/20-digit), `INVALID` (Luhn-fail, brand-gated mismatch), `SUCCESS` (compact + every §2.1 RECOGNIZE variant → same compact), `AMBIGUOUS` / `MultipleMentionsError` (two distinct PANs), `year` temporal filtering, `_clean_registry` fixture, determinism/`VersionStamp`, span-bearing match, candidate dedup (spaced + compact twins coalesce).
- Property tests (hypothesis): generate valid by Luhn-completing random 11–18-digit payloads → 12–19-digit claims that must canonicalize to themselves; random digit strings → `INVALID` with high probability (~90% Luhn-fail); grouped vs compact identical (`strip` equivalence); `format_value("grouped")` re-enters default contract to the same compact (ADR-0011 encoding round-trip); leading-zero invariance (Luhn outcome preserved).
- Consistency test: every shipped recognition length (12–19) exercised by at least one Luhn-valid vector; every brand allowlist entry (if shipped) exercised.
- Presentation purity: `output_format` source scan over `rules/`; `masked`/`truncated` absence test (no such format string anywhere in the capability).
- Real vectors: `4111111111111111` (Visa), `5555555555554444` (Mastercard), `378282246310005` / `3782 822463 10005` (Amex compact + 4-6-5 twins), `6011111111111117` (Discover), `3530111333300000` (JCB), `36050234196908` / `3622 720627 1667` (Diners 14), `4716-2210-5188-5662` + `4929 7226 5379 7141` (validator.js spaced/dashed), `4111111111111112` (Luhn-flip invalid), `5398228707871528` (validator.js invalid); plus `79927398713` + `17893729974` as **Luhn-math references only** (11 digits, below the floor — helper-function fixtures, never recognition/`matches()` fixtures).

> Fixture hygiene: all vectors above are public test numbers or below-floor algorithm references (Luhn-helper only), never live PANs. No expiry/CVV pairs in fixtures. Reviewers must reject any PR introducing non-test PAN-like fixtures without a public-test-number citation.

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | `DEFAULT_OUTPUT_FORMAT` — `pan` vs `compact` vs `digits` | `pan` (compact digits), offered `{"grouped"}` | `pan` names the domain value (Payment card number wiki term); `compact`/`digits` are mechanism words. Grouping-agnostic re-chunk v1 (brand-blind, reversible); brand-faithful 4-6-5 deferred until brand data ships — presentation must not sniff brand |
| 2 | Single grammar vs per-length / per-brand grammars | Single `pan_recognition` with range alternation; defer splits to community extension with coalesced semantics | Keeps surface minimal; avoids cross-grammar containment spurious `AMBIGUOUS` (GTIN single-grammar precedent for multi-length ranges) |
| 3 | Length floor — 12 vs 13 vs 8 | Grammar + ISO rule enforce **12–19**; 8–11 stay `MISSING` | 12 covers narrowest observed payment PAN (Maestro, omnipay, django-form); 8–11 are non-payment IIN uses (health/telecom/national special ranges, secondary). Paid §5 text is the only arbiter for lowering — verify before freezing |
| 4 | Brand-prefix validation — always-active vs gated vs deferred | Ship ISO PARSER always-active; brand LOOKUP_TABLE **gated `include_brand_validation=False`** or fully deferred to community extension | IIN Register is licence-only (no public snapshot); brand tables are secondary and divergent (braintree Visa `[16,18,19]` vs wiki `13/16/19`; UnionPay Luhn divergence). Fusing secondary data into the ISO rule would be provenance fraud |
| 5 | Case/space normalization in grammar vs rule | Grammar strips separators + labels and folds label case; rules validate ASCII digits only | Syntax not semantics (HOW_TO_ADD_NEW_GRAMMAR.md boundary); rules never re-strip |
| 6 | MII / special-range semantics | Informative only, never reject any MII; special `00`/`80`/`89`/`9CCC` out of payment scope via length floor, not via MII gate | MII is an allocation family, not a validity signal; rejecting MII would enshrine secondary policy in the ISO rule |
| 7 | IIN-6 vs IIN-8 duality | No notation field, no second canonical, no format encodes the boundary; rules derive `compact[0:6]`/`compact[0:8]` views locally | The same digits admit two parses (2017 revision); freezing one in notation would be recognition-layer policy. PCI FAQ #1091 BIN-length handling is caller/brand concern |
| 8 | Single `PUBLICATION` vs Part-1 + Part-2 split | Single `iso_7812_1_ed2017.py` (Part 1); Part 2 cited in §5.5 context only, no rule file | Part 2 specifies registration procedures, not per-PAN validation logic; a Part-2 `matches()` would be vacuous or fraudulent. Brand secondary (if shipped) is the only second file |
| 9 | Separator tolerance — single vs double-space/tab, dot/underscore | Grammar handles single space/hyphen per gap; double-space/tab **claim nothing in v1 → documented `MISSING` non-recognition** (left joined-run guard, §4.2; §2.1 row 8), with `\s`-widening left as an implementation-time decision (recommend single, document); dot/underscore/slash DEFER to `extra_grammars` | Single covers all fixtures (validator.js/braintree); widening risks absorbing prose gaps and would require re-deriving the guard set (the left guard and orphan guard are tuned to `[ \t-]`); dot/underscore lack attestation and widen false-positive surface |
| 10 | Label span inclusion | Include label in `raw_text` span (fused regex), `notation.digits` label-free | Mirrors ISSN/ISBN/IBAN/GTIN label policy; span aids UX highlighting while identity stays label-free |
| 11 | Which alternative written forms does v1 recognize (full §2.1 inventory: compact/spaced/dashed/Amex-465/Diners-14/mixed/labelled/irregular)? | RECOGNIZE the **seven** §2.1 rows attested by ≥2 validators or brand docs (rows 1–7: compact/spaced/dashed/Amex-465/Diners-14/mixed/labelled); **irregular whitespace (row 8) is documented non-recognition → `MISSING`** (decided under #9, stated explicitly per the §2.1 mandate); DEFER dot/underscore/slash via `extra_grammars`; REJECT masked/truncated/token/expiry-attached/OCR with written rationale | Unhandled *attested* forms are permanent `MISSING` blind spots; discovering them post-ship costs a grammar rewrite. Documented non-recognition is an allowed disposition when the form is unattested by the v1 evidence bar and its guard doctrine refuses to guess. The §2.1 table is the traceability contract for the §4.2 guards |
| 12 | UnionPay Luhn waiver (braintree `luhn:false` bypass) | Apply ISO Luhn to **all** brands under the default contract — no waiver anywhere; document that real Luhn-invalid UnionPay PANs are permanently `INVALID`. A waiver could only be built by excluding the ISO rule (`excluded_rules`/`pinned_rules`, caller-owned, never default) | The brand rule duplicates Luhn as ADR-0012 corroboration and must never re-derive a *different* verdict than the default contract (§5.3): braintree's bypass is secondary brand policy, not ISO, and letting a gated feature flag flip an ISO-Math verdict would make the same input's status depend on `include_brand_validation` in a way Luhn itself forbids (§7.2) |

Additional non-row guidance: `single_value=True` initially (shipped precedent), segmentation for multi-PAN slices; offer `extra_grammars` batch variant with `False` if demanded. PCI masking/truncation is a redaction-layer concern — any future `masked` render needs an ADR-0011 projection waiver (none exists; do not add).

---
## 14. Ambiguity Analysis (Paxman-specific)

- No inherent PAN-vs-PAN positional ambiguity — fixed digit-range structure eliminates the positional ambiguity Date exhibits (`01/02/2026` US-vs-European); two distinct PANs in one slice is authorial choice (test table, migration list), and segmentation is the intended path. Identical twins (spaced + compact + dashed of the same digits) coalesce via `compact` identity, never ambiguate.
- PAN vs GTIN overlap (12–14 digits) is not lexical ambiguity — a 12-digit run passing both Luhn and GS1 Mod-10 has two domain readings under two capabilities, but within the PAN capability there is one candidate value. Cross-capability selection is caller-owned (capability name), not engine-ambiguated. Within-capability, a 12-digit Luhn-valid run is `SUCCESS` regardless of its GTIN readability.
- PAN vs IMEI (15-digit Luhn) is the sharpest sibling collision — same alphabet, same length band, same algorithm, different domains (device vs payment). It is not resolvable by pattern, prefix, or check, and must not be "guarded" into resolvability: the grammar claims the shape, the ISO rule validates the math, and the domain (capability selection) decides the meaning. Document the collision; do not add IMEI-prefix heuristics to PAN rules.
- Brand-prefix overlap is not ambiguity — `65` Discover vs `65` Troy co-brand, `4` Visa vs `4` Visa-Electron legacy, `36` Diners vs `36` Mastercard-Canada alliance are the same digits with two brand labels. Brand is secondary provenance on one canonical value, not two competing canonicals; `AMBIGUOUS` requires different canonical values, and brand labels never change `compact`.
- Staleness is not ambiguity — brand ranges drift (2-series BINs 2016, 8-digit BIN migration ongoing, Maestro UK residual rules); determinism-by-snapshot pins the allowlist version in `Provenance.version`. A PAN brand-valid in snapshot N and brand-invalid in N+1 is two snapshots disagreeing, not one input ambiguating. The ISO Luhn verdict is snapshot-stable.
- Masking/truncation is not a reading — `XXXX XXXX XXXX 1234` and `411111...1111` are not competing values for the same PAN; they are projections that destroyed the value. Treating them as `INVALID` (recognized-but-unvalidated) would imply a PAN mention exists; they are `MISSING` (no PAN mention exists), and the redaction layer — not this capability — owns their meaning.

---
## 15. URL Reference (authoritative, fetched 2026-09-23 unless noted)

| Claim | URL | Kind |
|-------|-----|------|
| ISO/IEC 7812-1:2017 (5th ed., current, Published, confirmed 2022-10-27) | https://www.iso.org/standard/70484.html | primary |
| ISO/IEC 7812-2:2017 (5th ed., current, Published, confirmed 2022-10-27) | https://www.iso.org/standard/70485.html | primary |
| ISO/IEC 7812-1:2015 (4th ed., withdrawn 2017-01-03) | https://www.iso.org/standard/66011.html | primary |
| ISO/IEC 7812-1:2006 (3rd ed., withdrawn 2015-07-31) | https://www.iso.org/standard/39698.html | primary |
| ISO/IEC 7812-1:2000 (2nd ed., withdrawn) | https://www.iso.org/standard/31443.html | primary |
| ISO/IEC 7812-1:2000/Cor 1:2001 | https://www.iso.org/standard/36326.html | primary (lifecycle link target, not fetched) |
| ISO/IEC 7812-2:2015 (4th ed., withdrawn) | https://www.iso.org/standard/66012.html | primary (lifecycle link target, not fetched) |
| US Patent 2,950,048 (Luhn, filed 1954, granted 1960, expired) | https://patents.google.com/patent/US2950048A/en | primary |
| PCI SSC 8-digit BINs and PCI DSS (2021-09-02) | https://blog.pcisecuritystandards.org/8-digit-bins-and-pci-dss-what-you-need-to-know | primary (handling caveat, not validation authority) |
| python-stdnum `stdnum/luhn.py` (generic Luhn, no PAN module) | https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/luhn.py | primary |
| python-stdnum `stdnum/` index (no `creditcard.py`/`iso7812.py` — 404) | https://api.github.com/repos/arthurdejong/python-stdnum/contents/stdnum | primary (negative evidence) |
| validator.js `isCreditCard.js` (strip + brand regexes) | https://raw.githubusercontent.com/validatorjs/validator.js/master/src/lib/isCreditCard.js | primary |
| validator.js `isLuhnNumber.js` (Luhn gate) | https://raw.githubusercontent.com/validatorjs/validator.js/master/src/lib/isLuhnNumber.js | primary |
| validator.js fixtures + `prefix/middle/suffix` negatives | https://raw.githubusercontent.com/validatorjs/validator.js/master/test/validators.test.js | primary |
| validator.js Mastercard `\|`-precedence bug #2717 | https://github.com/validatorjs/validator.js/issues/2717 | primary (edge-case) |
| braintree `card-validator` `card-number.ts` (strip + lengths + UnionPay Luhn bypass) | https://raw.githubusercontent.com/braintree/card-validator/main/src/card-number.ts | primary |
| braintree `luhn-10.js` (Zakas Luhn) | https://raw.githubusercontent.com/braintree/card-validator/main/src/luhn-10.js | primary |
| braintree `credit-card-type` `card-types.ts` (patterns/lengths/gaps) | https://raw.githubusercontent.com/braintree/credit-card-type/master/src/lib/card-types.ts | primary |
| braintree test numbers (`4111111111111111`, `378282246310005`, …) | https://developer.paypal.com/braintree/docs/guides/credit-cards/testing-go-live/php | primary/secondary (test corpus) |
| django-credit-cards `utils.py`/`validators.py`/`types.py`/`forms.py` | https://raw.githubusercontent.com/dldevinc/django-credit-cards/master/creditcards/utils.py | primary |
| omnipay-common `Helper.php` (Luhn + `setNumber` strip-all) | https://raw.githubusercontent.com/thephpleague/omnipay-common/master/src/Common/Helper.php | primary |
| omnipay-common `CreditCard.php` (12–19 gate + brand regexes + `getNumberMasked`) | https://raw.githubusercontent.com/thephpleague/omnipay-common/master/src/Common/CreditCard.php | primary |
| ISO/IEC 7812 synthesis (MII table, IIN/account/check, 8-digit change, RA) | https://en.wikipedia.org/wiki/ISO/IEC_7812 | secondary |
| Luhn algorithm (Annex B citation, worked `1789372997→4`, pseudocode, weaknesses) | https://en.wikipedia.org/wiki/Luhn_algorithm | secondary |
| Payment card number (8–19 range, IIN/BIN, brand IIN/length table, PAN truncation) | https://en.wikipedia.org/wiki/Payment_card_number | secondary |
| GTIN research precedent | docs/development/research/2026-09-22-gtin-canonicalization.md | primary (repo) |
| LEI research precedent | docs/development/research/2026-09-22-lei-canonicalization.md | primary (repo) |
| ISIN research precedent | docs/development/research/2026-08-24-isin-canonicalization.md | primary (repo) |
| BIC research precedent (template) | docs/development/research/2026-08-23-bic-canonicalization.md | primary (repo) |
| IBAN research precedent (checksum-depth complement) | docs/development/research/2026-08-22-iban-canonicalization.md | primary (repo) |
| ISSN research precedent (single-grammar precedent) | docs/development/research/2026-08-21-issn-canonicalization.md | primary (repo) |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary (repo) |
| Paxman shipped precedent (GTIN grammar/rules/contract) | paxman/capabilities/GTIN/grammar/gtin_recognition.py + paxman/capabilities/GTIN/rules/gs1_genspecs_ed2026.py + paxman/capabilities/GTIN/contract.py + paxman/capabilities/GTIN/notation.py | primary (repo) |
| Paxman shipped precedent (ISIN Luhn rule + grammar) | paxman/capabilities/ISIN/rules/iso_6166_ed2021.py + paxman/capabilities/ISIN/grammar/isin_recognition.py | primary (repo) |
| Paxman domain + pipeline contract | paxman/core/domain.py + paxman/engine/orchestrator.py | primary (repo) |
| Roadmap priority (Credit card number §2A #7) | docs/development/MILESTONE.md | primary (repo) |

---
## 16. Evidence Completion — Resolved

This report's PAN-specific authoritative evidence has been fetched and cited (2026-09-23):

- [x] ISO catalogue entry: ISO/IEC 7812-1:2017 (5th ed., current, Published, confirmed 2022-10-27) superseding 2015 plus lineage (2006/2000/1993/1989); JTC 1/SC 17; ICS 35.240.15; version lifecycle + `publication_year=2017`; citation anchored to abstract + lifecycle stages
- [x] Part 2 + RA provenance: ISO/IEC 7812-2:2017 (5th ed., current) + ABA RA + licence-only IIN Register + CUSIP handoff (secondary); no public snapshot — no shipped IIN-lookup rule
- [x] Structure: digits-only, ceiling 19, payment floor 12 (operational/brand policy, ISO ceiling only), IIN 6-or-8 + MII informative + account variable + check 1
- [x] Luhn algorithm proved (Annex B double-add-double + US 2,950,048 substitution table + generation vs validation + `1789372997→4` / `7992739871→3` / patent `4872148→4` worked vectors — 8/11-digit algorithm references below the 12-floor, never PAN fixtures (§7.1) — + zero-padding invariance + weaknesses 09↔90 / twin errors)
- [x] IIN/BIN nuance: 6→8-digit 2017 change (PCI SSC primary corroboration), BIN synonym (RFC 4949 §33 secondary), MII table + `00`/`80CCC`/`89EE`/`9CCC` special ranges (secondary), non-payment scope cut
- [x] Ecosystem regex consensus: stdnum generic-Luhn (no strip) + validator.js strip + brand regexes + braintree strip + lengths/gaps + django strip-all + omnipay strip-all + 12–19 gate
- [x] Recognition-surface inventory complete (§2.1): every attested written form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form (compact/spaced/dashed/Amex-465/Diners-14/mixed/labelled RECOGNIZE; double-space/tab irregular → documented non-recognition `MISSING` (§13 #9); dot/underscore/slash DEFER; masked/truncated/token/expiry-attached/OCR REJECT)
- [x] Guard set execution-verified (§4.2/§8): the proposed `ScannerMatcher` pattern + date/orphan/left-run guards were executed over every §8 row and the §2.1/§2.2 fixtures before being written down; outcomes in §8 are observed, not predicted. Must be re-derived as failing-first tests at implementation (§12).
- [x] Wild input shapes validated (§2.2, 19 rows) against spec abstracts + brand tables (secondary) + all five validator families + test-card corpora
- [x] Label scope decision (fused optional branch, glued `reject`, span-includes-label, notation label-free)
- [x] IIN-6/8 equivalence decision (interpretation, not identity; no notation field)
- [x] MII/special-range semantics decision (informative only; scope via length floor)
- [x] Brand/registry liveness scope decision (gated secondary or deferred; PCI is handling caveat, never validation provenance)

File Layout / Rule provenance in §5.2 / §11 / §12 are **stable recommendations** for implementation, not frozen contracts (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0; paid ISO §4–5 / Annex B text verification is the one pre-implementation check that can renumber `Section 5-pan-structure-luhn`). Pre-implementation checklist: (1) the §4.2 guard set and every §8 outcome must be reproduced by failing-first tests before any grammar code is merged (they were execution-verified against a scanner-loop harness during research, not against the shipped engine); (2) re-verify §2.1 dispositions against the paid ISO text (floor 12 is operational, not ISO); (3) confirm the kernel-kind choice (`scanner`) still holds — `scanner.py`'s own docstring was stale about shipped customers, so re-check HOW_TO §4's kinds table at implementation time.

---

## Appendix — What the Shipped GTIN, ISIN, ISBN, IBAN and LEI Capabilities Teach PAN (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

Refer to `paxman/capabilities/GTIN/`, `ISIN`, `ISBN`, `IBAN`, `LEI` design notes plus `paxman/engine/orchestrator.py` and `paxman/core/domain.py` — see deep-dive summary in §4.2 / §5 / §6 above and the explore-verified notation, grammar, and rule excerpts. The four architectural lessons for PAN:

1. **Grammar strips, rule validates, capability formats.** GTIN `_gtin_emit` (`paxman/capabilities/GTIN/grammar/gtin_recognition.py:64-74`) strips labels/AI/separators to `digits`; `Section1GtinStructureCheckDigit.matches` (`paxman/capabilities/GTIN/rules/gs1_genspecs_ed2026.py:40-50`) enforces length + `isdigit` + GS1 Mod-10; `GTINCapability.format_value` renders `native` by slicing. PAN follows identically: `_pan_emit` strips to `digits` (scanner-kind emit, §4.2), `Section5PANStructureLuhn` enforces 12–19 + Luhn, `CreditCardCapability.format_value` re-chunks `grouped`.
2. **One file per provenance, one class per section.** GTIN splits GenSpecs (PARSER) // Prefix (LOOKUP_TABLE + `rules/data/gs1_prefix.py`) // Verified (gated LOOKUP_TABLE + snapshot); ISIN splits ISO 6166 (PARSER Luhn over `A=10…Z=35` expansion in `paxman/capabilities/ISIN/rules/iso_6166_ed2021.py:27-53`) // ANNA Guidelines (LOOKUP_TABLE + `rules/data/country_codes.py`); ISBN splits 2108 // Users Manual // Range Message (gated). PAN splits ISO/IEC 7812-1 (PARSER Luhn, no expansion needed) // brand-prefix (gated secondary LOOKUP_TABLE, if shipped at all).
3. **No `output_format` in rules, ever.** `tests/unit/test_rule_output_format_purity.py` fails any `output_format` token in `paxman/capabilities/*/rules/` (code, comments, docstrings). ISIN `normalize` (`paxman/capabilities/ISIN/rules/iso_6166_ed2021.py:89-90`) returns `notation.compact` unconditionally; GTIN `normalize` (`gs1_genspecs_ed2026.py:52-53`) returns `rjust(14,"0")`. PAN `normalize` returns `notation.digits` identity — grouping/masking never leak into rules.
4. **Single grammar with range alternation avoids spurious AMBIGUOUS; cross-grammar containment is preserved.** GTIN exact-length alternation longest-first (`gtin_recognition.py:57-61`) with `(?!\w)(?![-]\d)` tail; ISIN label branch + glued-label guard + `BoundaryGuard.word_only()` (`isin_recognition.py:20-34`); ISBN-13 hyphen-tolerance + `(?![-]\d)` anti-truncation. PAN composes these — longest-first 19→12 alternation + word guards — with GTIN/ISBN's hyphen-only `(?![\-]\d)` tail superseded by the separator-general joined-run orphan guard, plus the date guard and scan-time left guard, implemented as the kernel `scanner` kind (BCP-47/URL/E.164 precedent, §4.2). Six metadata attributes enforced at import (`paxman/core/domain.py:246-271`: `name`, `strategy`, `provenance`, `citation`, `target_semantics` non-empty `frozenset`, `requires_features` `frozenset`); `single_value=True` with engine `_enforce_single_value_invariant` + `_dedup_spans` longer-wins + total order `(start, end, active-set index, grammar name)`.

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for Credit card number (PAN). It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the deeper GTIN/ISIN check-digit precedents. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
