# BIC Canonicalization Research - paxman-python

**Date:** 2026-08-23
**Scope:** Primary-source survey of the BIC standard (ISO 9362:2022, SWIFT BIC Directory and Registration Authority, ISO 3166-1 country-code handling), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `BIC` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org) for ISO 9362:2022 and its lineage (1987, 1994, 2009, 2014), SWIFT BIC pages (swift.com BIC overview, SWIFTRef BIC Directory, BIC search, registration procedures 2021), python-stdnum `stdnum/bic.py`, validator.js `isBIC` plus issue 2045 (Kosovo XK), schwifty (BIC type properties), BankValidor taxonomy, Wikipedia as secondary, and shipped Paxman capabilities (ISSN, ISBN, Country, Phone) as architectural precedents. Repo state: `chores/pre-release-housekeeping` @ `d7737f0` - engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](../research/2026-08-21-issn-canonicalization.md) plus the IBAN precedent [`docs/development/research/2026-08-22-iban-canonicalization.md`](../research/2026-08-22-iban-canonicalization.md).

---

## Executive Summary

BIC is a strong fit for a Paxman capability: it has an unambiguous canonical form (**compact, no separators, uppercase, 8 or 11 chars**: `4!c institution + 2!a country + 2!c location + 3!c branch optional`, where `!c` is alphanumeric `A-Z0-9` and `!a` is alphabetic `A-Z`), a stable single-part standard (**ISO 9362:2022** 5th edition, 2022-04-12, `60.60 Published`, cancels 2014, ICS 03.060, publisher ISO/TC 68/SC 8) with SWIFT as Registration Authority since industry origin around 1975, a maintained authoritative directory (**SWIFT BIC Directory**, 107k+ BICs, 49k+ connected, 227 countries point-in-time, monthly activation weekend, daily vs monthly file, broadcast MT074 for out-of-cycle), and a well-understood human-readable presentation (**grouped display** `AAAA BB CC [XXX]` or with `BIC:` label, presentation-only). The domain mirrors Paxman's value proposition for IBAN and ISSN: recognizing the tolerant human surface (case, whitespace, separators, optional `BIC`/`SWIFT` label, `XXX` head-office suffix), validating strictly against the authority (structure + country-code membership), and returning a canonical compact value with full provenance. Unlike IBAN, BIC has **no checksum** (syntactic only, per codeswap.net "BIC has no checksum, unlike IBAN, structure is all there is").

Key findings that shape the design:

1. **Canonical form is compact, no separators, uppercase** (`DEUTDEFF`, `DEUTDEFF500`, `BNPAFRPP`, `CHASUS33`, `NEDSZAJJ`). Length is strictly `8` or `11` only, never `9` or `10`. Regex consensus is `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` (generic fallback `^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$`). Presentation grouping (`AAAA BB CC [XXX]`) is readability-only, exactly like IBAN groups-of-four or ISSN hyphen. This maps onto Paxman's presentational-only invariant: `format_value()` renders `bic` (compact, default) vs `grouped` vs `bic11` without touching validity.

2. **One grammar suffices, with optional branch group.** Unlike ISBN which needs two grammars (ISBN-13 vs ISBN-10, separate semantics and `include_isbn10` gating), BIC's `8` vs `11` is a single optional suffix `([A-Z0-9]{3})?` inside one pattern. A single `BICRecognitionGrammar` with Regex strategy is the correct choice. Using two grammars (`bic8` + `bic11`) would create cross-grammar containment where an 11-char BIC contains an 8-char prefix, producing spurious `AMBIGUOUS` (longer-wins is per-grammar only, cross-grammar is preserved per `orchestrator:_dedup_spans`). Single grammar with optional group avoids this.

3. **Validation is two-level syntactic, no checksum.** Level 1: generic structure, charset per position, length in `{8,11}`. Level 2: country-code lookup against ISO 3166-1 alpha-2 plus `XK` (Kosovo user-assigned, per validator.js issue 2045 fix and python-stdnum including `XK` plus `AQ` etc). No MOD-97, no check digit, no per-country length table like IBAN (IBAN varies 15 to 34 per country, BIC length is fixed 8 or 11 for every country). Location second-char semantics (`0` test, `1` passive, `2` reverse billing) are informative only and must not cause rejection, though schwifty exposes them as type properties.

4. **Branch `XXX` is head office but distinct string.** `BIC8` and `BIC8+XXX` are functionally equivalent for routing (both denote head office) but lexicographically distinct. Canonical identity is the literal compact string, so `NEDSZAJJ` and `NEDSZAJJXXX` are different canonical values, not coalesced. Formatting may offer `bic11` (always 11, appending `XXX` when branch absent) as presentational expansion, but validation treats both as syntactic variants.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 9362:2022` (active, current) owns BIC structure (BIC8 definition plus branch identifier optional); `SWIFT BIC Directory` (`kind="registry"`, rolling monthly) owns liveness vs reference; `ISO 3166-1` owns country-code vocabulary (normatively referenced). No country-specific BBAN registry, no check-character system, no URN namespace needed.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need BIC canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Payments / treasury engineers** | Normalize `deutdeff` vs `DEUT DE FF` vs `BIC: DEUTDEFF500` to one compact key for SWIFT message headers, deduplication, and wire validation before submission | Core banking, payment hubs, SWIFT FIN/MT and ISO 20022, treasury management systems |
| **Fintech / e-commerce onboarding** | Validate user-supplied BIC at form ingest; reject syntactically invalid vs country-invalid input with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | KYC flows, payout setup, beneficiary registration, invoice parsers that carry both IBAN and BIC |
| **Data engineering / reconciliation** | Extract and canonicalize BICs from free-text references, PDFs, emails, or scraped HTML with span-bearing provenance; join on compact canonical key | ETL pipelines, bank-statement parsers, Open Banking aggregation, LLM extraction post-processing |
| **Risk / compliance / search teams** | Use BIC as a stable institution key alongside IBAN and LEI; detect duplicate institutions across formatted variants, including `XXX` head-office equivalence | Fraud screening, AML monitoring, entity resolution, knowledge-graph institution matching, corporate ERP vendor master |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many BIC mentions) and a contract; Paxman returns one canonical BIC (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors IBAN (`electronic` compact default) and ISSN (`XXXX-XXXX` hyphenated) ergonomics, but the canonical default is **compact 8 or 11** (no spaces, no label, uppercase, branch preserved as given).

---

## 2. Shape of Input (Human Surface)

### 2.1 Wild variants - enumerated from spec, SWIFT BIC pages, SEPA/fintech corpora, and real validators

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical compact 8** | `DEUTDEFF`, `BNPAFRPP`, `CHASUS33`, `BARCGB22` | Spec master form, 8 chars, `4!c+2!a+2!c` |
| 2 | **Canonical compact 11** | `DEUTDEFF500`, `BNPAFRPPXXX`, `SOGEFRPPBRE`, `DSBACNBXSHA`, `NEDSZAJJXXX` | 11 chars, branch `3!c` present |
| 3 | **Lowercase / mixed case** | `deutdeff`, `DeUtDeFf500`, `bnpa frpp` | Permitted chars case-insensitive; canonical is uppercase, grammar must accept `(?i)` and normalize via `.upper()` |
| 4 | **Grouped display** | `DEUT DE FF`, `DEUT DE FF 500`, `BNPA FR PP`, `BNPA FR PP XXX` | SWIFT paper grouping `AAAA BB CC [XXX]` presentation-only, must be recognized and collapsed |
| 5 | **Label with colon/space/hyphen** | `BIC: DEUTDEFF`, `SWIFT: BNPAFRPPXXX`, `BIC DEUTDEFF500`, `swift-code: CHASUS33`, `BIC - NEDSZAJJ` | Many forms and exports prefix `BIC` or `SWIFT`; handling must be case-insensitive, colon/space/hyphen tolerant; span should include label when present (`raw_text` preserves it) |
| 6 | **Irregular whitespace** | `DEUT  DEFF`, `DEUT\tDEFF500`, `BNPA  FR  PP` | Users paste with double spaces, tabs; grammar must tolerate `\s` between characters or strip via `notation_fn` |
| 7 | **No spaces, separators included** | `DEUT-DEFF`, `DEUT.DEFF500`, `DEUT_DEFF` | Hyphens, dots, underscores pasted from PDFs; SWIFT spec allows only spaces in grouped display, but real copy-paste hits these; decision: recognize hyphen-minus only as separator tolerance or reject - document (§8) |
| 8 | **Head office `XXX`** | `NEDSZAJJ`, `NEDSZAJJXXX`, `BNPAFRPP` vs `BNPAFRPPXXX` | Branch `XXX` denotes head office. Both are syntactically valid. `BIC8` and `BIC8+XXX` are functionally equivalent but distinct strings; do not coalesce at validation |
| 9 | **With bank name trailing** | `DEUTDEFF (Deutsche Bank)`, `BNPAFRPP - BNP Paribas` | Free-text often annotates institution; extraction must emit one span per BIC, not swallow parenthetical |
| 10 | **Multiple per line** | `DEUTDEFF / BNPAFRPP`, `BICs: DEUTDEFF500, CHASUS33` | Payment batches, correspondent lists - free-text may contain 2+ BICs |
| 11 | **Quoted / bracketed** | `"DEUTDEFF"`, `[BNPAFRPPXXX]`, `(BIC: DEUTDEFF)` | Scraped HTML and JSON fragments wrap BICs in quotes or brackets |
| 12 | **OCR / homoglyph errors** | `DEUTDEFF` with `O` vs `0` confusion, `1` vs `I` | Not a recognition variant per se, but explains why charset must be strict `A-Z0-9` and not allow lowercase `l` confusion; no autocorrection, just `INVALID` if wrong char |
| 13 | **Over-long / under-long** | `DEUTDEF` (7 chars), `DEUTDEFF50` (10 chars), `DEUTDEFF5000` (12 chars) | Only `8` or `11` valid; 9, 10, 12 must not be recognized as BIC; length guard essential |
| 14 | **X-glued runs** | `XDEUTDEFF`, `DEUTDEFFY`, `ADEUTDEFF500B` | Longer alphanum token must not yield inner BIC via carving; word-boundary guards required |
| 15 | **Invalid country for BIC** | `DEUTXXFF`, `BNPAQQPP`, `CHASZZ33` | Country `XX`, `QQ`, `ZZ` are not ISO 3166-1 alpha-2 plus `XK`; `XX` is user-assigned range, not a country; grammar may still claim 8 or 11, rule rejects via country lookup |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Generic consensus (SWIFT docs, BankValidor) | `^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$` - 6 letters + 2 alphanum + optional 3 alphanum |
| Precise consensus (swift.com structure quote, python-stdnum) | `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` - 4 institution + 2 country + 2 location + optional 3 branch |
| `arthurdejong/python-stdnum` `stdnum/bic.py` | `clean(number,' -').strip().upper()` then `^[A-Z]{4}(?P<country_code>[A-Z]{2})[0-9A-Z]{2}([0-9A-Z]{3})?$` + `country in _country_codes` (includes `XK`, `AQ` etc), exceptions `InvalidLength`/`InvalidFormat`/`InvalidComponent` |
| `validator.js` `isBIC` | `/^[A-Za-z]{6}[A-Za-z0-9]{2}([A-Za-z0-9]{3})?$/` + `CountryCodes.has(countryCode) || countryCode === 'XK'` (fix for issue 2045) |
| `schwifty` (Python BIC lib) | Type properties for `0`/`1`/`2` second-char semantics (test vs passive vs reverse billing), formatted display `AAAA BB CC [XXX]` |
| `BankValidor` taxonomy | BIC structure table per position, location code semantics informative |
| `codeswap.net` / `Genfy` docs | "BIC has no checksum, unlike IBAN, structure is all there is" - syntactic only |

**Normalization contract (reuse IBAN/ISSN pattern):**

```python
# python-stdnum pattern - strip separators, upper, then structure check
import re

compact = re.sub(r"[^A-Za-z0-9]", "", raw).upper()  # strip separators
# or more narrowly, mirroring stdnum clean(number,' -'):
compact = re.sub(r"[ \-]", "", raw).strip().upper()  # spaces + hyphens only
# then validate: len in {8,11} and regex ^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$
```

### 2.2 What input is NOT a BIC mention

- IBANs (`DE89 3704 0044 0532 0130 00`, `GB29 NWBK 6016 1331 9268 19`) - longer (15 to 34), start with country code plus check digits, different provenance (ISO 13616). Length 8 or 11 vs 15+ disambiguates.
- National account numbers or sort codes without BIC structure - missing 4-char institution prefix or country at positions 5 to 6.
- LEI (`5493001KJTIIGC8Y1R12`, 20 chars) and ISIN (`US0378331005`, 12 chars) - different lengths, LEI has no country at fixed 5 to 6, ISIN check different.
- Short alphanumeric runs (`AB12`, `DEUT`) - `MISSING` vs `INVALID` boundary (see §9).
- Bare country codes (`DE`, `FR`) - too short, grammar must not claim.

### 2.3 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct BICs that normalize to different compact values is `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` with `single_value=True` enforcement); the caller-owned segmentation path (split then canonicalize each slice) is the intended multi-entity pattern for correspondent lists or statement lines with origin plus destination BICs. Identical BIC mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation - compact plus structured decomposition

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BICNotation:
    """BIC notation - grammar-normalized compact form.

    ``bank_code`` is the 4-char institution prefix, uppercased.
    ``country_code`` is the 2-letter ISO 3166-1 alpha-2 plus XK, uppercased.
    ``location_code`` is the 2-char location suffix, uppercased.
    ``branch_code`` is the 3-char branch, uppercased, or empty string when BIC8.
    ``compact`` is the full BIC string, 8 or 11 chars, uppercased, separators stripped.

    The grammar never validates country membership or liveness;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    """

    bank_code: str  # e.g. "DEUT", "BNPA" - always length 4, A-Z0-9 (pre-2014 A-Z only)
    country_code: str  # e.g. "DE", "FR" - always length 2, A-Z
    location_code: str  # e.g. "FF", "PP" - always length 2, A-Z0-9
    branch_code: str  # e.g. "500", "XXX", "" - length 0 or 3, A-Z0-9
    compact: str  # e.g. "DEUTDEFF" or "DEUTDEFF500" - 8 or 11, equals bank+country+location+branch
```

**Considered alternative - single field `compact` only:** `MoneyNotation` style with multi-field validation in `__post_init__`, and `PhoneNotation` `value`-only shape. A single `compact` field would suffice for the generic structure rule (which operates on the whole 8 or 11 string via regex), and country-specific branch handling can be derived via slicing `compact[4:6]`. However the five-field decomposition is preferred because:

1. The SWIFT BIC structure table indexes by `country_code` (lookup key at positions 5 to 6) and describes `bank_code` and `location_code` separately - the rule table is naturally keyed by `country_code`.
2. `IBANNotation`'s `country_code` plus `bban` split proves the value of exposing the prefix that determines validation routing; BIC's `country_code` serves the same indexing role for the country lookup rule.
3. `branch_code` being empty vs `XXX` is semantically meaningful (head office implicit vs explicit) and deserves a first-class field so the formatter can offer `bic11` expansion deterministically.

The notation is therefore **isomorphic to IBAN per-grammar sanitized forms** and satisfies `Grammar[BICNotation].recognize()` then `Rule[BICNotation].matches()` typing. Every field is `str` (HOW_TO_ADD_NEW_CAPABILITY.md requires all notation fields be `str`).

**Invariants the grammar enforces (before rules):**
- `bank_code` is exactly 4 `A-Z0-9` (uppercased by grammar from `[A-Za-z0-9]`), though pre-2014 it was `4!a` letters only.
- `country_code` is exactly 2 `A-Z` (uppercased by grammar from `[A-Za-z]`).
- `location_code` is exactly 2 `A-Z0-9` (uppercased).
- `branch_code` is `0` or `3` `A-Z0-9` (uppercased), `XXX` allowed and preserved.
- `compact` is `8` or `11` total, equals `bank_code + country_code + location_code + branch_code`; `compact == re.sub(r"[^A-Z0-9]", "", raw_text).upper()` modulo optional `BIC`/`SWIFT` label stripping.
- `raw_text` preserves original span (label plus spacing plus case); the notation is the syntax-normalized token.

### 3.2 Why not carry spaces or labels in the notation

Spaces, grouping, and `BIC:`/`SWIFT:` labels have **no lexical significance** for validity (ISO 9362 electronic vs grouped display, described as presentation-only). Compact and grouped forms of the same BIC have the same identity regardless of input spacing, dedup and status logic operate on `compact`. Presentation is `Capability.format_value()` only. The BIC directory itself lists BICs in compact form; grouped display `AAAA BB CC [XXX]` is a Paxman presentation choice for human readability, not a per-country variant.

### 3.3 Why `country_code` is not a shape discriminator literal

IBAN uses free `str` for `country_code` because the country set is around 90 values, modeling each as a `Literal` would be brittle, and validation is `LOOKUP_TABLE` against SWIFT IBAN Registry. BIC mirrors this: BIC country set is ISO 3166-1 plus `XK`, also around 250 entries if counting user-assigned. Modeling each as `Literal` would be brittle. Instead `country_code` is a free `str` validated by `LOOKUP_TABLE` rules against an ISO 3166-1 snapshot (plus `XK`), mirroring `Country` lexicon-key pattern where the registry, not the type system, owns the vocabulary. No `shape` field is needed because `len(compact)` in `{8,11}` and `branch_code == ""` already discriminate BIC8 vs BIC11, and no second notation meaning exists.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice - Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape, delimiters, fixed widths, character classes) or **Lexicon** (finite vocabulary, Country names, Currency words). BIC has a distinctive fixed-width shape (`4!c+2!a+2!c` plus optional `3!c`, total `8` or `11`), plus optional `BIC`/`SWIFT` label, so **Regex** is the correct strategy. No lexicon table is involved at recognition, the lexicon for valid country codes lives in the country rule (lookup), not the grammar key set.

### 4.2 Reference pattern (adapted from ISSN and IBAN verbatim precedent)

ISSN precedent (`paxman/capabilities/ISSN/grammar/issn_recognition.py`):
```python
_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]+)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.word_only().lookahead
)
```
IBAN precedent (this report §4.2, single grammar with paper tolerance):
```python
_IBAN_BODY = r"(?:IBAN[\s:-]+)?(?P<compact>[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})"
_IBAN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _IBAN_BODY
    + BoundaryGuard.word_only().lookahead
)
```

**Proposed BIC pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope string pattern - compiled by RegexStage (never inside recognize())
_BIC_BODY = r"(?:(?:BIC|SWIFT)[\s:-]+)?(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)"
# 8 chars = 4+2+2; 11 chars = 8+3 branch; only 8 or 11 via optional group, never 9 or 10
# Wrapped with word-boundary guards - BIC is [A-Z0-9] glued, so word_only prevents
# carving a valid run out of a longer token like "XDEUTDEFF" or "DEUTDEFFY"
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)


def _bic_notation(match: re.Match[str]) -> BICNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isalnum()).upper()
    # compact is now 8 or 11 alphanum; split structurally
    bank_code = compact[0:4]
    country_code = compact[4:6]
    location_code = compact[6:8]
    branch_code = compact[8:11] if len(compact) == 11 else ""
    return BICNotation(
        bank_code=bank_code,
        country_code=country_code,
        location_code=location_code,
        branch_code=branch_code,
        compact=compact,
    )


class BICRecognitionGrammar(PipelineGrammar[BICNotation]):
    """BIC recognition - 8 or 11 alphanum with optional BIC/SWIFT label."""

    name = "bic_recognition"
    semantics = "bic_recognition"
    single_value = True
    pre = StandardPre[BICNotation](empty_guard=True)
    regex = RegexStage[BICNotation](
        pattern=_BIC_PATTERN, notation_fn=_bic_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs ISSN and IBAN:*

- Ship as module-scope **string** pattern; `RegexStage` compiles in `paxman/core/grammar/stages.py` (mirrors ISBN `_ISBN13_PATTERN = r"..."`). Do not double-compile via `re.compile(...).pattern`.
- Strip in `notation_fn` via `isalnum()` plus `.upper()` (ISSN precedent `x` to `X` is `isalnum` plus `upper` for BIC). For ASCII fidelity wrap body in `(?ai:...)` and filter with `ch.isascii() and ch.isalnum()` to reject non-ASCII like `K` or Unicode digits while `BoundaryGuard.word_only()` stays Unicode-aware (mirrors `paxman/capabilities/IBAN/grammar/iban_recognition.py:25` `(?ai:(?:[A-Z]` pattern).
- Optional branch `(?:[A-Z0-9]{3})?` guarantees only `8` or `11` total, never `9` or `10`. A pattern like `[A-Z0-9]{0,3}` would incorrectly match 9 or 10.
- Leading `BoundaryGuard.word_only()` (`(?<!\w)`) and trailing `BoundaryGuard.word_only()` (`(?!\w)`) block letter/digit-glued runs (`XDEUTDEFF`, `DEUTDEFFY`, `BICDEUTDEFF` without space). Shipped `ISSN/grammar/issn_recognition.py` uses `BoundaryGuard.word_only().lookbehind` (verified), IBAN uses word_only both sides - BIC follows same, since alphabet includes digits and gluing is common in free text.
- **Label handling:** `(?:(?:BIC|SWIFT)[\s:-]+)?` is fused (like ISSN `ISSN(?:-L|-H)?` and ISBN `ISBN(?:-13)?`). The `notation_fn` maps only the `compact` group (without label), so `raw_text` includes the label plus spacing when matched, but `notation.compact` is the bare BIC. Whether `raw_text` includes the label is a design choice, either include via `m.group(0)` semantics (like ISSN) or attribute only the `compact` group; document in §8.
- **Whitespace tolerance:** BIC grouped display tolerates single space between `AAAA`, `BB`, `CC`, `XXX`. The compact regex above handles contiguous; grouped tolerance `DEUT DE FF` would require `[ ]?` interleaving or a `Pre` stage that collapses `\s+` before regex. Keep minimal for v1 (contiguous only), document grouped as presentation, add tolerant `Pre` later if demanded - parallel to IBAN paper-space tolerance debate.
- Uses `PipelineGrammar` plus `StandardPre` plus `RegexStage` because that is the staged pipeline ISBN actually ships (HOW_TO_ADD_NEW_GRAMMAR.md bare `Grammar` recipe is the minimal teaching form; shipped grammars use `PipelineGrammar`).

**Eight vs eleven as one grammar vs two:**

Like IBAN paper vs electronic, the 8-char and 11-char forms are two *presentations* of the same institution family, but lexicographically distinct (unlike IBAN where paper spaces do not change the string, branch `XXX` does). Options:

- **(Recommended) Single grammar** with `(?:[A-Z0-9]{3})?` branch tolerance - minimal containment complexity (`_dedup_spans` no-op within one grammar), single `semantics` id.
- **Alternative:** Two grammars `bic8_recognition` plus `bic11_recognition` with coalesced `semantics = "bic_recognition"` (HOW_TO_ADD_NEW_GRAMMAR.md option A, reuse shipped semantics id so existing ISO 9362 rule validates both without edit). Only introduce if you want to record provenance that the input was BIC8 vs BIC11 (not needed, provenance is the authority, not the length).

### 4.3 Recognition pipeline contract (ARCHITECTURE.md Recognition Pipeline Contract)

- Grammar emits **span-bearing** `RecognitionMatch[BICNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))`, span is the regex slice. Stages must not mutate `text` (`PipelineState` scratch only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups, two grammars agreeing on the same span are both preserved for ambiguity observation. For BIC (single shipped grammar initially), this dedup keeps the 11-char match over an 8-char prefix when both would match at same start (longer wins).
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

### 4.4 Guard boundaries against sibling grammars

BIC vs sibling alphanum grammars: BIC `8/11` vs IBAN `15 to 34` vs ISIN `12` vs LEI `20` - length plus charset plus country lookup splits disambiguation.

Concrete length discrimination table:

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| BIC | `8` or `11` `[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?` | 4-char institution at start | `(?!\w)` prevents claiming prefix of longer alphanum; only 8 or 11 accepted |
| IBAN | `15 to 34` `[A-Z]{2}\d{2}[A-Z0-9]+` | `CC` is `A-Z`, `DD` is `\d` | Longer than any BIC, so BIC `DEUTDEFF` (8) cannot be mistaken for IBAN; country check plus length mismatch will reject |
| ISIN | `12` `[A-Z]{2}[A-Z0-9]{9}\d` | Also `CC` at start | ISIN `US0378331005` (12) is longer than BIC8 and different from BIC11; charset overlap but length guard plus country at different position disambiguates |
| LEI | `20` `[A-Z0-9]{20}` | No fixed `CC` at 5 to 6 | No BIC `4+2+2` pattern at fixed 20, not confused |

Prefix-aware BIC detection (`BIC:` or `SWIFT:` label) does not clash with sibling labels (`IBAN:`, `LEI:`, `ISBN`); case-insensitive `BIC` vs `IBAN` substrings are distinct. For a BIC-like run `DEUTDEFF` where `DE` is a valid BIC country at positions 5 to 6, recognition should claim; where `XX` is not a BIC country (no ISO 3166-1 entry plus XK), the generic structural grammar may still claim 8 chars, but the country rule will correctly report `INVALID`.

Concrete engine check (`orchestrator:_dedup_spans`):

```python
ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
# longer wins within SAME grammar; across grammars never deduped
```

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

The new grammar declares a non-empty `semantics` string; every validating `Rule` declares `target_semantics: frozenset[str]` naming the semantics ids it validates. The engine `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. For a single shipped BIC grammar, the natural ids are:

- `semantics = "bic_recognition"` (identity id).

Recommendation: start with identity `bic_recognition`; coalesce only if a second grammar (e.g. `bic_grouped_recognition`) is later added, coalescing is option A in HOW_TO_ADD_NEW_GRAMMAR.md.

### 4.6 `single_value` - one mention per call vs batch processing

Shipped capabilities (ISBN, Country, Money, Phone) all set `single_value=True`, consistent with Paxman "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). Correspondent banking lists legitimately contain 2+ BICs per document (`Origin BIC: DEUTDEFF / Beneficiary BIC: BNPAFRPPXXX`), so batch extraction will want free-text mining of multiple mentions.

Recommendation: **initial `single_value=True`** (matches shipped precedent and the single-beneficiary field use-case), with a documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A separate free-text community grammar with `single_value=False` can be offered via `extra_grammars` for batch-processing callers when needed.

---

## 5. Provenance - the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec and lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO** - International Organization for Standardization, Technical Committee **ISO/TC 68/SC 8** (Reference data for financial services), subcommittee SC 8 responsible for ISO 9362 series. BIC data record concept introduced 2014. |
| **Registration Authority (RA)** | **SWIFT (Society for Worldwide Interbank Financial Telecommunication)** - Avenue Adele 1, B-1310 La Hulpe, Belgium. Designated RA for ISO 9362. Responsible for receiving registration requests, validating BIC assignments, and publishing the BIC Directory. Industry origin around 1975. |
| **Spec name** | `ISO 9362 - Banking - Banking telecommunication messages - Business identifier code (BIC)` |
| **Current edition** | **ISO 9362:2022 (5th ed., published 2022-04-12)** - current, `60.60 Published`, Publisher ISO/TC 68/SC 8, ICS 03.060. Withdraws ISO 9362:2014 (published 2014-12-01, withdrawn 2022-04-12). See lineage table below. |
| **Check character system** | None - BIC has no checksum (codeswap.net, Genfy). Unlike IBAN MOD 97-10, BIC validation is syntactic only. |
| **Country code reference** | `ISO 3166-1 alpha-2` - two-letter country codes referenced normatively by ISO 9362 for positions 5 to 6; maintained by ISO 3166 Maintenance Agency. Plus `XK` (Kosovo, user-assigned, BIC ecosystem exception per validator.js issue 2045 and python-stdnum). |
| **Related specs** | `ISO 3166-1 alpha-2` country codes; SWIFT BIC Directory and BIC Policy; SWIFTRef BIC search; BIC publication schedule PDF; BIC registration procedures 2021. |

**BIC structure (ISO 9362:2022 §5, SWIFT BIC overview page):**

```
BIC = BIC8 [Branch]
BIC8 = 4!c business party prefix + 2!a country + 2!c location = 8 chars
Branch = 3!c optional = 3 chars → 11 total when present
      Total length 8 or 11 only (never 9 or 10)

Positions:
1-4   institution (business party prefix) 4!c  A-Z0-9  (pre-2014 4!a A-Z only)
5-6   country 2!a ISO 3166-1 plus XK       A-Z
7-8   location 2!c alphanumeric            A-Z0-9  (second char 0/1/2 semantics informative only)
9-11  branch 3!c optional alphanumeric     A-Z0-9  (XXX = head office)
      BIC is 8 char code defined as business party identifier, branch identifier is 3 char optional.
```

Quoted SWIFT definition (swift.com BIC page):
> "The BIC is an 8 character code, defined as business party identifier, consisting of the business party prefix (4 alphanumeric), the country code as defined in ISO 3166-1 (2 alphabetic), and the business party suffix (2 alphanumeric). The branch identifier is a 3 character optional element..."

- Formal charset: `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` compact; grouped display `AAAA BB CC [XXX]` spaces presentation-only, `(?i)` accepted, canonical `upper`.
- Second char of location (position 8) semantics: `0` test BIC, `1` passive participant, `2` reverse billing, informative only, must not reject.
- Branch `XXX` denotes head office, `BIC8` and `BIC8+XXX` are functionally equivalent for routing but distinct strings.
- Examples from evidence: `DEUTDEFF` (Deutsche Bank DE FF), `DEUTDEFF500`, `BNPAFRPP` and `BNPAFRPPXXX` (BNP FR), `CHASUS33`, `BARCGB22`, `NEDSZAJJ` and `NEDSZAJJXXX`, `SOGEFRPPBRE`, `DSBACNBXSHA`.

**Lineage table (ISO 9362 editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 9362:1987 | 1987 | withdrawn | First edition, SWIFT industry origin around 1975 |
| ISO 9362:1994 | 1994 | withdrawn | Second edition |
| ISO 9362:2009 | 2009 | withdrawn | Third edition, expanded non-financial scope |
| ISO 9362:2014 | 2014-12-01 | withdrawn 2022-04-12 | Fourth edition, `4!a` to `4!c` (letters to alphanumeric), introduced BIC data record |
| ISO 9362:2022 | 2022-04-12 | current, 60.60, 5th ed. | Minor revision, cancels 2014, ICS 03.060, ISO/TC 68/SC 8 |

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 68/SC 8) | `ISO 9362:2022` | `2022-04` (5th ed., current) | `https://www.iso.org/standard/84108.html` | `active` - supersedes 2014 | `2022` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 9362:2014` | `2014-12` (4th ed.) | `https://www.iso.org/standard/60390.html` | `withdrawn` 2022-04-12 | `2014` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 9362:2009` | `2009` (3rd ed.) | `https://www.iso.org/standard/17047.html` | `withdrawn` | `2009` | `specification` |
| ISO | `ISO 9362:1994` | `1994` (2nd ed.) | (ISO record withdrawn - cited via lineage) | `withdrawn` | `1994` | `specification` |
| ISO | `ISO 9362:1987` | `1987` (1st ed.) | (ISO record withdrawn - cited via lineage) | `withdrawn` | `1987` | `specification` |
| SWIFT (ISO RA) | `SWIFT BIC Directory` | `Rolling monthly` (e.g. Release Oct 2025) | `https://www.swift.com/standards/data-standards/bic-business-identifier-code` plus `https://www.swift.com/products/swiftref-bic-directory` plus `https://www.swiftref.com/en/bicsearch` | `active` - rolling | `2025` | `registry` |
| SWIFT | `SWIFT BIC Registration Procedures` | `2021` | `https://www.swift.com/sites/default/files/files/swift_bic_registration_procedures_2021.pdf` | `active` | `2021` | `specification` |
| ISO 3166 MA | `ISO 3166-1 alpha-2` | (referenced normatively by 9362) | `https://www.iso.org/iso-3166-country-codes.html` plus RA landing `https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html` | `active` | - | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical BIC rule citing a withdrawn edition (e.g. ISO 9362:2014) would carry `lifecycle="withdrawn"` or `"superseded"`. For BIC, the initial rule is expected `active`. The SWIFT BIC Directory is `kind="registry"` `lifecycle="active"` (rolling).

### 5.2 Rule and publication map (one file per publication - HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_9362_ed2022.py` | `authority="ISO"`, `specification_name="ISO 9362:2022"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/84108.html"`, `version="2022"`, `lifecycle="active"`, `publication_year=2022` | `Section 5-bic-structure` (BIC8 plus branch optional, charset per position, length in 8 or 11, `XXX` head office, location second-char informative) | Generic structure: length `8` or `11`, charset per position (`4!c` etc), `XXX` branch handling, location `0`/`1`/`2` not rejected; `normalize()` returns compact `upper` |
| `rules/iso_3166_ed2022.py` *(optional split - or fused into iso_9362 file)* | `authority="ISO 3166 MA"`, `specification_name="ISO 3166-1"`, `kind="specification"`, `reference_url="https://www.iso.org/iso-3166-country-codes.html"`, `version="2022"` | `Section *-bic-country-code` (country at positions 5 to 6 must be ISO 3166-1 alpha-2 plus XK) | Whether the 2-char country field is in ISO 3166-1 plus `XK`; `requires_features` not needed for country check (always active) or gated if you want to allow XK only opt-in |
| `rules/swift_bic_directory_ed2025.py` *(optional - gated, liveness)* | `authority="SWIFT (ISO RA)"`, `specification_name="SWIFT BIC Directory"`, `kind="registry"`, `reference_url="https://www.swift.com/products/swiftref-bic-directory"`, `version="Rolling monthly"` | `Section *-bic-directory-membership` (connected vs non-connected, liveness) | Whether the 8 or 11 BIC is present in the SWIFT BIC Directory (live data file in `rules/data/`); `requires_features={"include_directory_validation"}` |

*This mirrors ISBN three-authority split (ISO 2108 // ISBN Users Manual // ISBN Range Message, each one `PUBLICATION` per file) and ISSN single-mandatory-plus-optional split (ISO 3297:2022 // ISSN Register). For BIC, only ISO 9362:2022 plus ISO 3166-1 country lookup are mandatory; the SWIFT BIC Directory liveness layer is optional, gated via `requires_features`, exactly like ISBN `Section 4-registrant-range` gated by `include_range_validation` and Country `include_localized`.*

Each `Rule[BICNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`):

```python
class Section5BICStructure(Rule[BICNotation]):
    name = "Section 5-bic-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 5 (BIC structure, branch optional)"
    target_semantics = frozenset({"bic_recognition"})
    requires_features = frozenset()

    def matches(self, notation: BICNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: BICNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO 9362:2022 lineage** confirmed via `https://www.iso.org/standard/84108.html` (current, 5th ed., 2022-04-12, 60.60, ICS 03.060, cancels 2014) and `https://www.iso.org/standard/60390.html` (2014, 4!a to 4!c, BIC data record) plus `https://www.iso.org/standard/17047.html` (2009).
- **SWIFT as RA:** `https://www.swift.com/standards/data-standards/bic-business-identifier-code` (landing: "BIC is an 8 character code... branch identifier is 3 character optional") plus BIC Directory `https://www.swift.com/products/swiftref-bic-directory` (107k+ BICs, 49k+ connected, 227 countries) plus search `https://www.swiftref.com/en/bicsearch` plus RA landing `https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html` (lists SWIFT as RA for 9362) plus registration procedures `https://www.swift.com/sites/default/files/files/swift_bic_registration_procedures_2021.pdf`.
- **Structure quote** from swift.com BIC page: “The BIC is an 8 character code, defined as business party identifier, consisting of the business party prefix (4 alphanumeric), the country code as defined in ISO 3166-1 (2 alphabetic), and the business party suffix (2 alphanumeric). The branch identifier is a 3 character optional element…” plus directory note: 107k+ BICs, 49k+ connected, 227 countries.
- **Country nuance:** BIC country set equals ISO 3166-1 plus `XK` (Kosovo user-assigned), per validator.js issue 2045 fix and python-stdnum `bic.py` including `XK` plus `AQ` etc. IBAN country set is subset (~80); BIC shares ISO 3166-1 but adds `XK`.
- **No checksum:** codeswap.net "BIC has no checksum, unlike IBAN, structure is all there is", Genfy docs, Schwifty type properties for `0`/`1`/`2` but no check digit.

### 5.3 What each rule does vs does not own

- **`matches()`** - validates strictly. The generic ISO 9362 rule checks: length in `{8,11}`, charset per position (`4!c` etc, `A-Z0-9` upper), `XXX` handling, location second-char `0`/`1`/`2` not rejected (informative only). The country rule checks: country field at positions 5 to 6 is in ISO 3166-1 alpha-2 plus `XK` (and optionally `AQ` etc if mirroring stdnum). The directory rule checks: BIC present in SWIFT BIC Directory snapshot (connected vs non-connected distinction out-of-scope for `INVALID` vs `SUCCESS` unless directory gating enabled). All return `False` for any invalid input, never raise, not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** - returns the **default compact form** (uppercase, no spaces, branch preserved as matched, per contract default). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability `format_value()` seam only. Both the generic and the country rule must return the **same** default string for the same valid notation, candidate dedup `(value, recognition_rule, validation_rule)` ensures agreement stays `SUCCESS`.
- **`RuleStrategy` choice:** Country precedent uses `LOOKUP_TABLE` for membership (alpha-2), ISBN uses `PARSER` for check digit. For BIC, the generic structure rule is `PARSER`; the country-code rule is `LOOKUP_TABLE` (parallel to Country alpha-2 `LOOKUP_TABLE`); the directory membership rule if offered is `LOOKUP_TABLE`.

### 5.4 Country-code scope decision

The **ISO 3166-1 alpha-2** code at BIC positions 5 to 6 is the country discriminator. BIC country set equals **ISO 3166-1 plus `XK`** (Kosovo, user-assigned `XK`, `X` range). This is broader than IBAN country set (around 80 IBAN-registered countries) because BIC exists for non-IBAN jurisdictions as well. IBAN validator.js had bug 2045 where `XK` was missing from IBAN country map and was fixed; python-stdnum `bic.py` includes `XK` plus `AQ` (Antarctica) etc in `_country_codes`.

**Recommendation for an initial BIC capability:** treat country-code validation as **always-active `LOOKUP_TABLE`** against an embedded ISO 3166-1 alpha-2 snapshot plus `XK`, not gated behind an `include_*` flag. Unlike IBAN BBAN registry (90-entry table with per-country regex and length), BIC country check is a simple set membership with no per-country length variant (every BIC is 8 or 11 regardless of country). Cost is minimal and correctness benefit is high (rejecting `XX`/`ZZ` etc at `INVALID` rather than false `SUCCESS`). If `XK` handling is contested, offer it as included by default with a note, exactly as python-stdnum and validator.js now do. `AQ` and other rarely-used ISO codes can be included if mirroring stdnum, no harm.

Analogy: Country capability `LOOKUP_TABLE` for alpha-2; BIC country field is the same class of membership property, not a check-digit transform.

### 5.5 Assignment and registration authority and Directory content

Network: **SWIFT** as RA (La Hulpe, Belgium) plus **assigning institutions** per country (financial institutions that request BICs). Blocks: each institution defines one or more BICs (BIC8 head office plus optional branch BIC11s); the **BIC Directory** (central catalogue) is published as **monthly file** (full) plus **daily delta**, searchable via **SWIFTRef BIC search** at `https://www.swiftref.com/en/bicsearch` and via **SWIFT BIC Directory** product at `https://www.swift.com/products/swiftref-bic-directory`. Each record includes: BIC (8 or 11), institution name, branch name if branch, city, country, connected vs non-connected flag, and effective dates. Directory notes:

- *"Connected BICs"* are header-valid in SWIFT messages, *"non-connected BICs"* are reference-only, always published, free, cannot appear in header.
- Monthly activation weekend, daily vs monthly file, broadcast MT074 for out-of-cycle updates.
- 107k+ BICs, 49k+ connected, 227 countries (point-in-time claim).

Per **SWIFT BIC Registration Procedures 2021** (`https://www.swift.com/sites/default/files/files/swift_bic_registration_procedures_2021.pdf`):

- RA receives registration requests, validates BIC structure and institution, and publishes in the Directory.
- Publication schedule PDF describes monthly activation and daily delta cadence.

Mandatory registration data: institution name, BIC (8 or 11), country, location, branch if any, contact authority.

---

## 6. Presentation Seam - Contract and Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman.core.capability_contract.py`), never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class BICContract(CapabilityContract):
    """User-facing contract for BIC capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = (
        "bic"  # cf. ISSN "hyphenated" / IBAN "electronic"
    )
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped", "bic11"})

    capability_name: str = field(default="bic", init=False)
    # No grammar-toggle flags for the initial single-grammar design.
    # If directory liveness gating is later added:
    # include_directory_validation: bool = False

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For BIC there is one always-active grammar,
    # so the property is omitted - base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For BIC, `bic` (compact, uppercase, branch as matched) is the machine canonical form (SWIFT compact); `grouped` is the human `AAAA BB CC [XXX]` rendering; `bic11` is always 11 (append `XXX` when branch absent).
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format`, `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order, then capability-specific params (if any). For BIC initially there are no capability-specific params; `include_directory_validation` is added only when the directory rule ships.

**Presentational-only invariant (hard rule - ARCHITECTURE.md The Formatting Seam):**

- `output_format` is a **representation transform, never a recognition or validation signal**. Rules never read it; `normalize()` always returns the default compact form; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup and status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance**, `Candidate.provenance`, `recognition_rule`, `validation_rule` come from the validating rule.

For BIC, the offered formats model the three interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"bic"` (default) | `DEUTDEFF` or `DEUTDEFF500` / `BNPAFRPPXXX` | Compact, no spaces, uppercase, branch as matched, DB key, SWIFT header payload |
| `"grouped"` | `DEUT DE FF` or `DEUT DE FF 500` | Groups `AAAA BB CC [XXX]` separated by single spaces, readability for docs and statements |
| `"bic11"` | `DEUTDEFFXXX` (from `DEUTDEFF`) or `DEUTDEFF500` (already 11) | Always 11, append `XXX` head office when branch absent; lossy expansion but deterministic |

*Do not add `with_label` format, the `BIC:`/`SWIFT:` label is not part of the identifier; statement or report renderers add it. Do not add `test_bic` or `passive_bic` formatting, location second-char `0`/`1`/`2` semantics are informative only, not presentation.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.BIC.notation import BICNotation


class BICCapability(Capability[BICNotation]):
    name = "bic"  # lowercase identifier - what users pass to registry

    def get_grammars(self) -> list[Grammar[BICNotation]]:
        return [BICRecognitionGrammar()]  # single grammar; 8 and 11 handled together

    def get_rules(self) -> list[Rule[BICNotation]]:
        return [
            Section5BICStructure(),
            SectionCountryCode(),
        ]  # plus optional directory rule

    @staticmethod
    def create_contract(
        *,
        excluded_rules: "Sequence[str] | None" = None,
        pinned_rules: "Sequence[str] | None" = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: "Sequence[str] | None" = None,
    ) -> BICContract:
        return BICContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: BICNotation
    ) -> str:
        if output_format == "grouped":
            # SWIFT grouped display: AAAA BB CC [XXX]
            if len(value) == 11:
                return f"{value[0:4]} {value[4:6]} {value[6:8]} {value[8:11]}"
            return f"{value[0:4]} {value[4:6]} {value[6:8]}"
        if output_format == "bic11":
            # Always 11, append XXX when branch absent
            if len(value) == 8:
                return value + "XXX"
            return value
        return value  # bic default is identity - normalize() must return compact
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`):
`scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(BIC())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation - Syntactic, Country, Registry

### 7.1 Syntactic validation (no checksum - three-level model)

BIC has **no checksum**, no MOD 97, no mod-11. Validation is purely syntactic plus country membership plus optional directory lookup. Three conceptual levels, but only two are mandatory for a Paxman initial capability:

**Level 1 - Generic structure (`PARSER`, always active):**
- Length in `{8,11}` only. `9` or `10` is syntactically invalid and must be `INVALID` if recognized via tolerant regex or `MISSING` if length-gated regex rejects.
- Charset per position: positions 1 to 4 `4!c` `A-Z0-9` (pre-2014 strict `4!a` `A-Z` only, but 2022 allows digits), positions 5 to 6 `2!a` `A-Z`, positions 7 to 8 `2!c` `A-Z0-9`, positions 9 to 11 `3!c` `A-Z0-9` when present.
- Branch `XXX` is not special-cased, it is valid `3!c` like any branch, but `format_value(bic11)` treats it as head office marker.
- Location second-char `0`/`1`/`2` semantics (test, passive, reverse billing) are informative only. Schwifty exposes them as `is_test_bic`, `is_passive_bic`, but validation must not reject `0`/`1`/`2` at position 8. A rule that rejected `CHASGB2L` because second location char is `2` would be wrong.
- Formal regex: `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` compact; `(?i)` accepted on input, canonical `upper`.

**Level 2 - Country-code lookup (`LOOKUP_TABLE`, always active recommended):**
- Country at positions 5 to 6 must be ISO 3166-1 alpha-2 plus `XK`. `XK` is user-assigned for Kosovo, not an ISO-assigned code, but required for BIC ecosystem correctness (validator.js issue 2045, stdnum includes it).
- python-stdnum includes `XK` plus `AQ` (Antarctica) and others in `_country_codes`; BIC Directory lists 227 countries point-in-time, which includes territories.
- `XX`, `QQ`, `ZZ`, `OO` are user-assigned or not assigned and must be `INVALID` (grammar may still claim 8 or 11, rule rejects).
- Digit in country position (e.g. `DEUT1EFF`) is charset failure at Level 1, already `INVALID` before country lookup.

**Level 3 - Directory membership (`LOOKUP_TABLE`, gated, optional):**
- SWIFT BIC Directory lookup: is this BIC present as connected or non-connected entry, live vs stale. Determinism-by-snapshot per ARCHITECTURE.md, not ambiguity; document snapshot version in `Provenance.version`.
- Connected vs non-connected distinction: connected is header-valid, non-connected is reference-only, always published, free, cannot appear in header. `INVALID` vs `SUCCESS` split for non-connected is a policy decision, for Paxman syntactic level 1 plus 2 is `SUCCESS`, directory liveness is opt-in `include_directory_validation` (like ISBN `include_range_validation` / IBAN `include_registry_validation`).

**What makes a BIC "valid" vs "country-valid" vs "live-registered":**

- **valid BIC (generic)** - correct total length `8` or `11`, charset per position, `XXX` allowed, `0`/`1`/`2` at pos 8 not rejected. This is the always-active `PARSER` rule, analog to ISBN valid vs ISSN valid.
- **country-valid BIC** - generic-valid plus `country_code` at 5 to 6 is in ISO 3166-1 plus `XK`. This is the always-active `LOOKUP_TABLE` country rule (or fused into one PARSER plus lookup). Without it, `DEUTXXFF` would be false `SUCCESS`; with it, `INVALID`.
- **live-registered BIC** - actually present in SWIFT BIC Directory snapshot, connected vs non-connected. Paxman does not and should not validate liveness against live SWIFTRef search without a snapshot; country-valid is the deepest deterministic layer for initial capability.

Like IBAN valid-vs-country-valid split (15 to 34 plus mod97 vs SWIFT Registry length and BBAN structure), BIC valid-vs-country-valid is the same gated split, but BIC country-valid is a simple set membership, far cheaper than IBAN per-country BBAN regex.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase: `deutdeff` vs `DEUTDEFF` vs `DeUtDeFf` | `SUCCESS` → `DEUTDEFF` (grammar folds, rule validates structure) | Grammar `notation_fn` `.upper()`, canonical always uppercase, like IBAN case folding |
| 2 | Grouped spacing: `DEUT DE FF` vs `DEUTDEFF` | `SUCCESS` → same compact canonical | Spaces presentation-only; grammar `isalnum()` collapses, dedup by compact value |
| 3 | Multiple spaces or tabs: `DEUT  DEFF`, `DEUT\tDEFF500` | `SUCCESS` → same canonical (if grammar `[ ]?` or `isalnum` collapse handles it; otherwise `MISSING` with strict) | Grouped display is single spaces; real paste is noisy, document narrow vs `Pre`-normalized widening |
| 4 | Label present: `BIC: DEUTDEFF`, `SWIFT: BNPAFRPPXXX`, `BIC DEUTDEFF500` | `SUCCESS`, span includes label plus value if fused pattern; `raw_text == text[start:end]` includes label | Optional `(?:BIC|SWIFT)[\s:-]+` prefix, `re.IGNORECASE`; `notation.compact` is label-free |
| 5 | Head office `XXX`: `NEDSZAJJ` vs `NEDSZAJJXXX` | Both `SUCCESS` → distinct canonical values (`NEDSZAJJ` vs `NEDSZAJJXXX`); `bic11` format renders `NEDSZAJJXXX` from either | `XXX` is valid branch, functionally head office but lexicographically distinct; do not coalesce |
| 6 | BIC8 plus `XXX` formatted as grouped: `NEDS ZAJJ XXX` vs compact `NEDSZAJJXXX` | `SUCCESS` → same compact `NEDSZAJJXXX` | Grouped rendering of 11-char is `AAAA BB CC XXX` four groups |
| 7 | Over-long or under-long for BIC: `DEUTDEF` (7), `DEUTDEFF50` (10), `DEUTDEFF5000` (12) | `MISSING` (no BIC grammar claims 7/10/12) or `INVALID` if inner 8-char sub-run matched but country fails | Only 8 or 11 valid, 7/9/10/12 must not be recognized |
| 8 | Non-registry country: `DEUTXXFF`, `BNPAQQPP`, `CHASZZ33` | Without country rule: `SUCCESS` (generic structure passes, false positive); with country rule: `INVALID` | Country lookup is membership gate, `XX` etc in user-assigned range, not ISO 3166-1 plus `XK` |
| 9 | Digit in institution: `D3UTDEFF` vs `DEUTDEFF` | `SUCCESS` for `D3UTDEFF` under 2022 `4!c` (alphanumeric), but would be `INVALID` under pre-2014 `4!a` (letters only) | Structural allowance changed 2014, 4!a to 4!c |
| 10 | Test vs passive vs reverse billing at pos 8: `DEUTDE0F`, `BARCGB1L`, `CHASGB2L` | `SUCCESS` - location second-char `0`/`1`/`2` informative only, must not reject | schwifty exposes type property but validation must not gate on it; document |
| 11 | BIC embedded in sentence: `Please remit to BIC DEUTDEFF (Deutsche Bank)` | `SUCCESS` with span; `raw_text` includes `BIC` prefix if fused, or just BIC body | Free-text recognition, span-bearing match, not whole-string; `\b` / `(?<!\w)` / `(?!\w)` ensures `DEUTDEFF` inside longer alphanum is not carved |
| 12 | Two distinct BICs in one slice: `DEUTDEFF / BNPAFRPPXXX` | `AMBIGUOUS` (two candidates, different compact values) or `MultipleMentionsError` with `single_value=True`; segmentation recommended | Caller-owned segmentation for multi-BIC input; identical BICs in one slice still coalesce to `SUCCESS` |
| 13 | BIC vs IBAN confusion: `DEUTDEFF` (BIC, 8) near `DE89 3704 0044 0532 0130 00` | `MISSING` for BIC on the IBAN run (too long), `SUCCESS` for BIC only on correct 8 or 11 run | Length discrimination, BIC 8/11 vs IBAN 15+ |
| 14 | Leading or trailing alphanum glue: `XDEUTDEFF`, `DEUTDEFFY`, `ADEUTDEFF500B` | `MISSING` (or `INVALID` if inner run matched but country fails) | Leading `(?<!\w)` keeps BIC from being carved out of a longer identifier |
| 15 | Quoted or bracketed: `"DEUTDEFF"`, `[BNPAFRPPXXX]`, `(BIC: DEUTDEFF)` | `SUCCESS` with span inside quotes or brackets | Word-boundary guards plus alphanum token still match inside punctuation |
| 16 | Non-alphanum separators: `DEUT-DEFF`, `DEUT.DEFF500` | `MISSING` in grammar (spaces only, hyphen not allowed), unless tolerant `[ -.]?` per-group - document decision | Keep minimal for v1; `StandardPre` could host `[-.]` normalization if desired |
| 17 | Invalid charset: `DEUT*EFF`, `DEUT E_FF`, `DEUT#EFF` | `MISSING` (no BIC grammar claims, special char breaks token) | Only `A-Z0-9` plus `BIC:` label allowed |
| 18 | Country `XK` for Kosovo: `BANKXK22`, `CBKIXKPRXXX` | `SUCCESS` - `XK` is valid BIC country, must be accepted | validator.js issue 2045 fix and python-stdnum include; IBAN country set subset would reject `XK` if reused |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid BIC (generic plus country, 8 or 11, country in ISO 3166-1 plus XK): `DEUTDEFF`, `DEUTDEFF500`, `BNPAFRPP`, `BNPAFRPPXXX`, `CHASUS33`, `BARCGB22`, `NEDSZAJJ`, `NEDSZAJJXXX`, `SOGEFRPPBRE`, `DSBACNBXSHA`, lowercase or grouped variants, `BIC:` label | `SUCCESS` → `DEUTDEFF` or `DEUTDEFF500` (`bic` default, compact) | Single compact canonical value via ISO 9362:2022 plus ISO 3166-1 country lookup |
| Valid BIC, alternative input spacing or case or label | `SUCCESS` (same compact) | Spaces, case, label are presentation-only; candidate dedup by compact value |
| Invalid country or bad charset or wrong length: `DEUTXXFF`, `DEUTDEFF50` (10), `DEUTDEFF5000` (12), `DEUT*EFF`, `DEUTDEF` (7) | `INVALID` (recognized, no authority validates) or `MISSING` if length-gated regex rejects | Definitive structural failure, generic or country rule rejects |
| Length 9 or 10 or 12 alphanum: `DEUTDEFF50` (10), `DEUTDEFF5000` (12) | `MISSING` (no BIC grammar claims) or `INVALID` (sub-run recognized but country fails) depending on grammar scope | Length-guarded grammar `8/11` only plus `(?!\w)` prevents partial claims; word-glued guard `(?<!\w)` prevents `XDEUTDEFF` yielding `DEUTDEFF` |
| No alphanum runs of length 8 or 11 in text | `MISSING` | No grammar recognized anything |
| Two distinct valid BICs in one slice (e.g. `DEUTDEFF / BNPAFRPPXXX`) | `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True` (different compact values) | Single-slice ambiguity, use segmentation |
| `XK` country BIC (`BANKXK22`) | `SUCCESS` | `XK` is valid BIC country, included via ecosystem fix |
| `XX` or `ZZ` country BIC (`DEUTXXFF`, `DEUTZZFF`) | `INVALID` when country rule rejects (without country rule: would be `SUCCESS` false positive) | Country membership claimed by ISO 9362 country lookup rule |
| Directory-gated input (if `include_directory_validation=True` and BIC not in Directory) | `INVALID` when only the directory rule would validate | Authority feature gating, enabled yields `INVALID` rather than `MISSING`, like Country localized without `include_localized` or ISBN Range without `include_range_validation` |
| Test or passive or reverse billing BIC (`DEUTDE0F`, `BARCGB1L`, `CHASGB2L` at pos 8 second location char `0`/`1`/`2`) | `SUCCESS` | Informative only, not validation failure |
| BIC8 plus `XXX` vs BIC8 (`NEDSZAJJXXX` vs `NEDSZAJJ`) | Both `SUCCESS` but distinct values, not coalesced; `bic11` format renders `NEDSZAJJXXX` from either | Head office equivalence is routing, not string identity |

---

## 10. Scaffolding and Repo Integration

### 10.1 Generated skeleton (`tools/new_capability.py` - HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py BIC --name bic \
    --authority "ISO" --spec-name "ISO 9362:2022" --spec-url "https://www.iso.org/standard/84108.html" \
    --publication-year 2022
```

Creates 13 files plus one edit (per Step 0 checklist): `paxman/capabilities/BIC/{notation,contract,capability,grammar/bic_recognition,rules/iso_9362_ed2022}` , tests stubs, and `paxman/capabilities/__init__.py` alphabetical wiring. The `TODO(scaffold)` markers then guide replacing the placeholder grammar pattern with the BIC Regex (§4.2), renaming `Section 1-overview` to `Section 5-bic-structure`, shaping the notation beyond placeholder `value` into `bank_code`/`country_code`/`location_code`/`branch_code`/`compact`, and adding `rules/data/` only if the directory layer is adopted.

> Note: The scaffolder single `--spec-name` covers one provenance. After scaffolding, add the second provenance file `rules/iso_3166_ed2022.py` (country lookup) manually, or fuse both into one `iso_9362_ed2022.py` file with a note referencing ISO 3166-1 as the country vocabulary, either pattern satisfies "one file per publication" as long as each file carries one `PUBLICATION` and one `Rule` class per section.

### 10.2 Contract and grammar wiring

- `get_grammars()` returns `[BICRecognitionGrammar()]` (single grammar handles both 8 and 11 via optional branch).
- `active_grammars` omitted for initial design (base `None` → runs every shipped grammar). Only introduce if recognition becomes feature-gated (e.g. `include_grouped` grouped-space grammar) - the Email/IP/ISBN pattern.
- Each grammar carries `name = "bic_recognition"` (snake_case `_recognition` suffix) and non-empty `semantics` - engine composes shipped plus `extra_grammars` community extensions in order, failing fast on name collisions (`CapabilityError`) or dangling `target_semantics` (`ContractError`).

### 10.3 Cross-cutting invariants (fail review if violated)

- **No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source** - fix root cause or use scoped `per-file-ignores` (sanctioned in `pyproject.toml`).
- **No cross-capability imports** - import only from `paxman.core` (import-linter enforced). BIC must not import Currency or Country country-code tables or Money amount regex.
- **No `output_format` token in any `paxman/capabilities/*/rules/` module** (code, comments, or docstrings) - source-scan `tests/unit/test_rule_output_format_purity.py` fails otherwise. Presentation is `Capability.format_value()` only.
- `@dataclass(frozen=True, slots=True)` for domain objects and notation; `@dataclass(frozen=True)` **without** `slots` for contracts.
- Deterministic by construction: same input plus contract plus library snapshot (version plus registry plus rule-data tables) → same canonical output; no network, clock, or environment-dependent ordering.

---

## 11. Recommended File Layout (mirrors ISSN and IBAN)

```
paxman/capabilities/BIC/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── bic_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_9362_ed2022.py               # primary - generic structure (PARSER)
    ├── iso_3166_ed2022.py               # country lookup (LOOKUP_TABLE) - or fused into iso_9362 file
    ├── swift_bic_directory_ed2025.py    # directory LOOKUP_TABLE (gated) - sibling to iso_9362
    └── data/                            # only if SWIFT Directory layer adopted
        └── bic_directory.py             # SWIFT BIC Directory snapshot (LOOKUP_TABLE; rolling monthly)
# Alternative fused layout (single mandatory file):
#   rules/iso_9362_ed2022.py             # structure plus country lookup in one file (one PUBLICATION, one Rule class)
#   rules/swift_bic_directory_ed2025.py  # directory (kind="registry", requires_features={"include_directory_validation"})
```

Per-country directory data module shape (parallel to `paxman/capabilities/ISBN/rules/data/range_message.py`):

```python
# rules/data/bic_directory.py - machine-readable SWIFT BIC Directory snapshot
# Source: https://www.swift.com/products/swiftref-bic-directory  (SWIFTRef search https://www.swiftref.com/en/bicsearch)
# File format: monthly full plus daily delta; this snapshot is point-in-time.
# Generated or hand-curated; update via tools/regenerate_bic_directory_data.py if automated.

BIC_DIRECTORY: frozenset[str] = frozenset(
    {
        "DEUTDEFF",
        "DEUTDEFF500",
        "BNPAFRPP",
        "BNPAFRPPXXX",
        "CHASUS33",
        "BARCGB22",
        "NEDSZAJJ",
        "NEDSZAJJXXX",
        "SOGEFRPPBRE",
        "DSBACNBXSHA",
        # ... 107k+ BICs (connected plus non-connected), 227 countries point-in-time
    }
)
# Plus liveness flag if needed: dict[str, dict[str, object]] with connected flag, but set suffices for membership.
# Completeness invariant: every SWIFT-registered BIC present; non-registered BIC absent.
```

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- **Grammar tests** (`tests/capabilities/bic/test_grammar.py`): valid compact 8, valid compact 11, variant inputs (lowercase, mixed case, `BIC:` label, `SWIFT:` label, `BIC-` label, multiple spaces or tabs collapsed, grouped `AAAA BB CC`, no label bare BIC), multiple matches in one text, incompatible format (IBAN 15+, ISIN 12, LEI 20, bare country code 2, 7/9/10/12 length), empty input; span invariants `len(raw_text) == end - start` and `raw_text == text[start:end]`; `name` and `semantics` checks; boundary guard negative tests (`XDEUTDEFF` word-glued, `DEUTDEFFY` tail-glued, `ADEUTDEFF500B` both sides).
- **Rule tests** (`test_rules.py`):
  - *Generic structural rule* (`iso_9362_ed2022`): per-rule `matches()` valid/variant/invalid (`DEUTDEFF` compact vs `deutdeff` lowercase, `DEUTDEFFXXX` head office, `DEUTDE0F` test type not rejected, `DEUTDEFF50` 10-char wrong length rejected, `D3UTDEFF` digit in institution allowed under 2022, `DEUTXXFF` country invalid only if country rule active, `NEDSZAJJ` 8 vs `NEDSZAJJXXX` 11 both valid), `normalize()` exact compact output (grouped `DEUT DE FF` → `DEUTDEFF` including `country_code` uppercase), provenance attributes (`authority="ISO"`, `specification_name="ISO 9362:2022"`, `publication_year=2022`, `lifecycle="active"`), name/strategy conventions (`strategy=PARSER`), leading positions preserved.
  - *Country LOOKUP rule* (`iso_3166_ed2022`): `matches()` valid country (`DE` Germany, `FR` France, `XK` Kosovo, `GB` UK, `NL` Netherlands, `CN` China) plus `XXX` branch, invalid country (`XX`, `ZZ`, `QQ` user-assigned) fails lookup, `normalize()` exact same compact string (country rule must agree with generic rule value - dedup invariant); `strategy=LOOKUP_TABLE`; provenance `kind="specification"` (`authority="ISO 3166 MA"`, `specification_name="ISO 3166-1"`).
  - *Directory LOOKUP rule* (`swift_bic_directory_ed2025`): `matches()` valid directory membership (`DEUTDEFF` connected, `BNPAFRPP` present), unknown BIC not in snapshot fails, `normalize()` exact same compact; `requires_features={"include_directory_validation"}` gate; `strategy=LOOKUP_TABLE`; provenance `kind="registry"` (`authority="SWIFT (ISO RA)"`, `specification_name="SWIFT BIC Directory"`).
- **Capability tests** (`test_capability.py`): notation `frozen`/`hashable`/`slots` (attempt mutation raises `FrozenInstanceError`, `hash` stable, `__slots__` present); wiring counts (`get_grammars` len 1, `get_rules` len 1 mandatory plus country, plus optional directory gated count); grammar/rule name conventions (`bic_recognition`, `Section 5-…`); `format_value()` `bic` ↔ `grouped` ↔ `bic11` round-trips (`DEUTDEFF` ↔ `DEUT DE FF` via grouping, `DEUTDEFF` → `DEUTDEFFXXX` via `bic11`); `create_contract` factories for default (`bic`, no directory), `output_format="grouped"`, `output_format="bic11"`, `extra_grammars` path.
- **Integration** (`tests/integration/test_bic_capability.py`): `MISSING`/`INVALID`/`SUCCESS`/`AMBIGUOUS` (or `MultipleMentionsError` with `single_value=True`); country gating (`DEUTXXFF` → `INVALID` with country rule, would be `SUCCESS` on generic alone), `year` temporal filtering (`year=2014` excludes 2022 rule if pinned); `_clean_registry` fixture; determinism and `VersionStamp`; span-bearing `RecognitionMatch` and `Candidate.span`; compact vs grouped dedup (same compact from two grouped spacings → `SUCCESS`, not `AMBIGUOUS`).
- **Property tests (hypothesis):** generate valid BICs by: pick `bank_code` 4!c `A-Z0-9`, pick valid country `CC` from ISO 3166-1 plus `XK`, pick `location_code` 2!c `A-Z0-9`, optional branch `3!c` or `XXX` → assemble `CC` plus rest → must canonicalize to itself via compact; random 8 or 11 alphanum strings → `INVALID` with high probability when country not in set; grouped vs compact → identical compact canonical value; `format_value(grouped) → compact → grouped` is losslessly round-trip via compact as pivot (grouped re-grouping is deterministic, `bic11` expansion `XXX` is deterministic).
- **Consistency test (grammar/rule boundary):** every shipped recognition `semantics` is covered by at least one `Rule.target_semantics`; if directory data adopted, every shipped BIC in `BIC_DIRECTORY` tested for length and structure agreement; keep grammar and rule data in separate files with a consistency test that asserts every SWIFT directory BIC `CC` at positions 5 to 6 is exercised by country rule and every BIC is 8 or 11.
- **Presentation purity:** the `output_format` source scan already applies to any new `rules/` module (`tests/unit/test_rule_output_format_purity.py`) - `swift_bic_directory_ed2025.py` and `iso_9362_ed2022.py` must contain no `output_format` token.
- **Real BIC vectors (candidates; point-in-time SWIFT Directory):**
  - Valid generic plus country: `DEUTDEFF` (DE), `DEUTDEFF500` (DE branch), `BNPAFRPP` (FR), `BNPAFRPPXXX` (FR head office), `CHASUS33` (US, location `S3` plus branch `3`-char numeric), `BARCGB22` (GB), `NEDSZAJJ` (ZA), `NEDSZAJJXXX` (ZA head office), `SOGEFRPPBRE` (FR branch BRE), `DSBACNBXSHA` (CN branch SHA).
  - Lowercase and case variants: `deutdeff`, `bnpa frpp`, `chusas33` lower.
  - Label variants: `BIC: DEUTDEFF`, `SWIFT: BNPAFRPPXXX`, `bic: chasus33`.
  - Grouped variants: `DEUT DE FF`, `DEUT DE FF 500`, `BNPA FR PP`, `BNPA FR PP XXX`.
  - Invalid structure: `DEUTDEF` (7), `DEUTDEFF50` (10), `DEUTDEFF5000` (12), `DEUT*EFF` (special).
  - Invalid country: `DEUTXXFF` (XX user-assigned), `BNPAZZPP` (ZZ), `DEUTQQFF` (QQ).
  - Test, passive, reverse billing at pos 8: `BARCGB21` (passive would be `1` at pos 8, but example `BARCGB22` has `2` reverse billing, also valid).

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | **`DEFAULT_OUTPUT_FORMAT`** - `bic` vs `grouped` vs `compact` | **`bic` default (compact, no spaces, uppercase, branch as matched); `grouped` and `bic11` offered** | SWIFT compact is the wire and DB canonical key; Paxman `grouped` `AAAA BB CC [XXX]` is a canonical Paxman rendering for human readability. Either way the seam is presentational-only, decision is about defaults, not validity. |
| 2 | **Single grammar vs BIC8 plus BIC11 grammars** | **Single `bic_recognition` initially; handle branch via `(?:[A-Z0-9]{3})?` optional group**; defer split `bic8_recognition` and `bic11_recognition` to community extension with coalesced `semantics = "bic_recognition"` | Keeps initial surface minimal; branch is not a second meaning but an optional suffix. Futures coalesced semantics viable (HOW_TO_ADD_NEW_GRAMMAR.md option A, no rule edit). Two grammars would cause cross-grammar containment where 11 contains 8 as prefix, producing spurious `AMBIGUOUS`. |
| 3 | **Country lenience vs strict** | **Ship generic structure plus country `LOOKUP_TABLE` as always-active**; add `SWIFT BIC Directory` `LOOKUP_TABLE` rule behind `include_directory_validation` - `False` by default | Mirrors IBAN valid vs country-valid split but simpler: BIC country check is cheap set membership (no per-country length regex), so always-active is low cost. Directory liveness is the truly optional, staleness-prone layer, like ISBN `include_range_validation=False`. |
| 4 | **Grammar length strictness** | **Grammar enforces `8` or `11` exactly via `(?:[A-Z0-9]{3})?` optional branch, never `9` or `10`** | Keeps grammar cheap and definitive; country-exact not needed (every country same 8/11), so length is fully grammar-enforceable, unlike IBAN where per-country 15 to 34 requires table. |
| 5 | **Case and space normalization in grammar vs rule** | **Grammar folds case (`isalnum` plus `.upper()`) and strips separators; rules validate upper alphanum only** | Case folding is syntax, not semantics (HOW_TO_ADD_NEW_CAPABILITY.md); same as ISSN `x` to `X` and IBAN hyphen stripping - grammar strips, rule validates. |
| 6 | **Test, passive, reverse billing at pos 8 (`0`/`1`/`2`)** | **Informative only, do not reject; expose via `format_value` documentation or schwifty type property, not validation** | SWIFT semantics are routing hints, not validity; rejecting `0` at pos 8 would incorrectly mark valid test BICs as `INVALID`. Schwifty exposes as type property, but Paxman rule must pass them. |
| 7 | **Single `PUBLICATION` vs split 9362 plus 3166** | **Either is acceptable; recommend fused or split but consistent:** fused `iso_9362_ed2022.py` owning structure plus country lookup with a docstring citation to ISO 3166-1 is minimal; split `iso_9362_ed2022.py` (structure) plus `iso_3166_ed2022.py` (country) is more faithful to "one file per publication" | ISO 3166-1 is a normative reference of 9362, like ISO/IEC 7064 for IBAN; fused keeps `get_rules()` small; split gives cleaner provenance per-file but doubles wiring. Both pass `Rule.__init_subclass__`, recommend fused for v1, split only if reviewers want per-publication purity. |
| 8 | **`single_value` for batch processing** | **`True` initially (shipped precedent); document segmentation recipe for multi-BIC documents; offer `extra_grammars` free-text variant with `False` if needed for batch and ETL callers** | Consistent with ISSN, IBAN, Country; `MultipleMentionsError` is the correct signal for `DEUTDEFF / BNPAFRPPXXX` in one slice. |
| 9 | **Non-space separator tolerance (`-`, `.`, `_`)** | **Grammar handles contiguous only; hyphens, dots, underscores normalize in a `Pre` stage or document as unsupported** | SWIFT spec allows only spaces in grouped display; keep minimal for v1; `StandardPre` could host `[-.]` normalization if demanded. |
| 10 | **Label span inclusion (`BIC:` / `SWIFT:`)** | **Include label in `raw_text` span (fused regex with label) - `notation.compact` is label-free; `raw_text` includes prefix when present** | Mirrors ISSN `ISSN 1234-5679` and ISBN `ISBN 978…` and IBAN `IBAN: DE89…` label-in-span behavior; useful for highlighting the full mention; `format_value` ignores label. |

---

## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent BIC-vs-BIC ambiguity.** Like IBAN and ISSN, BICs are unique by design; the fixed `8` or `11` structure eliminates the positional ambiguity Date exhibits (`DD/MM` vs `MM/DD`). Two distinct BICs in one slice are an authorial choice (origin vs beneficiary, correspondent lists), not a parsing ambiguity, segmentation is the intended path. Different grouped spacings or casings of the same compact value are the same canonical value; formatting must not affect status.
- **BIC vs non-BIC country is not lexical ambiguity** - a `DEUTXXFF` alphanum run that passes generic `8` structure but is not in ISO 3166-1 plus `XK` is still `INVALID` when the country rule runs, not a competing value. Without the country rule it would be a false-positive `SUCCESS`, valid vs country-valid is a feature-gated validity distinction, not a multi-value ambiguity. The `XK` inclusion makes `BANKXK22` `SUCCESS` rather than `INVALID`, a deliberate ecosystem exception.
- **BIC vs IBAN, ISIN, LEI length discrimination** prevents cross-capability ambiguity - BIC `8/11`, IBAN `15 to 34`, ISIN `12`, LEI `20` are disjoint enough that compact BIC at 8 or 11 cannot be mistaken for IBAN; ISIN `US0378331005` (12) is one digit longer than 11 and lives in a different capability grammar and contract entirely, so no single-capability ambiguity arises (cross-capability disambiguation is out-of-scope, each capability validates its own domain).
- **BIC8 vs BIC11-XXX is not ambiguity, it is distinct identity.** `NEDSZAJJ` and `NEDSZAJJXXX` denote the same head office for routing but are distinct canonical strings. `bic11` formatting expands `NEDSZAJJ` to `NEDSZAJJXXX`, but validation treats both as syntactic variants, not coalesced. A caller that wants head-office-blind grouping can normalize via `bic11` and then dedup themselves, but Paxman canonical identity is literal compact.
- **Directory staleness is not ambiguity.** A newly-assigned BIC not yet in an embedded snapshot would be `INVALID` under a stale snapshot but `SUCCESS` under a fresh one when directory validation is enabled, this is determinism-by-snapshot per ARCHITECTURE.md, not ambiguity; document snapshot version in `Provenance.version` (e.g. `Rolling monthly` or `Release 2025-08`).
- **Test vs passive vs reverse billing is not ambiguity.** A BIC with `0` at position 8 is a test BIC, but still a valid BIC string; passive `1` and reverse billing `2` similarly do not create competing values. Schwifty exposes them as type properties; Paxman treats them as `SUCCESS`.

---

## 15. URL Reference (authoritative, fetched 2026-08-23)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 9362:2022 (5th ed., 2022-04-12, `60.60 Published`, current) | <https://www.iso.org/standard/84108.html> | primary |
| ISO 9362:2014 (4th ed., withdrawn 2022-04-12, 4!a to 4!c) | <https://www.iso.org/standard/60390.html> | primary |
| ISO 9362:2009 (3rd ed., non-financial scope) | <https://www.iso.org/standard/17047.html> | primary |
| ISO 3166 Maintenance Agency and SWIFT as RA listing | <https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html> | primary |
| SWIFT BIC overview (structure quote, BIC is 8 plus branch optional) | <https://www.swift.com/standards/data-standards/bic-business-identifier-code> | primary |
| SWIFTRef BIC Directory (107k+ BICs, 49k+ connected, 227 countries, monthly activation) | <https://www.swift.com/products/swiftref-bic-directory> | primary |
| SWIFTRef BIC search (free search) | <https://www.swiftref.com/en/bicsearch> | primary |
| SWIFT BIC Registration Procedures 2021 (RA duties) | <https://www.swift.com/sites/default/files/files/swift_bic_registration_procedures_2021.pdf> | primary |
| ISO 3166-1 alpha-2 country codes | <https://www.iso.org/iso-3166-country-codes.html> | primary |
| ISSN research precedent (provenance and file-layout model) | [`docs/development/research/2026-08-21-issn-canonicalization.md`](../research/2026-08-21-issn-canonicalization.md) | primary |
| IBAN research precedent (syntactic plus registry split, paper seam) | [`docs/development/research/2026-08-22-iban-canonicalization.md`](../research/2026-08-22-iban-canonicalization.md) | primary |
| Paxman scaffolder and conventions | [`HOW_TO_ADD_NEW_CAPABILITY.md`](../../HOW_TO_ADD_NEW_CAPABILITY.md), [`HOW_TO_ADD_NEW_GRAMMAR.md`](../../HOW_TO_ADD_NEW_GRAMMAR.md), [`ARCHITECTURE.md`](../../ARCHITECTURE.md) | primary |
| python-stdnum BIC (`stdnum/bic.py`, clean plus regex plus country lookup, XK) | <https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/bic.py> | primary |
| validator.js isBIC (regex plus CountryCodes.has plus XK) | <https://github.com/validatorjs/validator.js/blob/master/src/lib/isBIC.js> | primary |
| validator.js issue 2045 (Kosovo XK fix) | <https://github.com/validatorjs/validator.js/issues/2045> | primary |
| schwifty (BIC type properties, formatted display) | <https://github.com/mdomke/schwifty> | primary |
| BankValidor BIC taxonomy (structure, location semantics) | <https://bankvalidor.com/bic> | secondary |
| codeswap.net BIC has no checksum (vs IBAN) | <https://codeswap.net/bic> | secondary |
| Genfy BIC docs (no checksum) | <https://genfy.com/bic> | secondary |
| Wikipedia BIC (secondary only, lineage 1975 etc) | <https://en.wikipedia.org/wiki/ISO_9362> | secondary |
| Paxman shipped BIC-adjacent precedent (Country lexicon, ISSN single grammar, IBAN paper seam, ISBN two grammars) | `paxman/capabilities/ISBN/grammar/` plus `paxman/capabilities/ISSN/grammar/` plus `paxman/capabilities/Country` plus `paxman/capabilities/IBAN` plus `paxman/engine/orchestrator.py` | primary |

---

## 16. Evidence Completion - Resolved

This report BIC-specific authoritative evidence has been fetched and cited (2026-08-23):

- [x] ISO catalogue entry: **ISO 9362:2022 (5th ed., 2022-04-12, current, `60.60 Published`)** superseding **ISO 9362:2014 (withdrawn 2022-04-12)** plus lineage **ISO 9362:2009 (non-financial scope)** plus **ISO 9362:1994** plus **ISO 9362:1987 (first edition)**; TC 68/SC 8; ICS 03.060; 5th edition cancels 2014; URLs `https://www.iso.org/standard/84108.html` and `https://www.iso.org/standard/60390.html` and `https://www.iso.org/standard/17047.html`; `version="2022"` `lifecycle="active"` `publication_year=2022`; `citation` anchored to ISO 9362:2022 §5 (BIC structure).
- [x] SWIFT as RA and Directory provenance: `authority="SWIFT (ISO RA)"` `specification_name="SWIFT BIC Directory"` `kind="registry"` `reference_url="https://www.swift.com/products/swiftref-bic-directory"` plus BIC overview `https://www.swift.com/standards/data-standards/bic-business-identifier-code` plus search `https://www.swiftref.com/en/bicsearch` plus registration procedures `https://www.swift.com/sites/default/files/files/swift_bic_registration_procedures_2021.pdf` plus RA landing `https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html`; intro quote "The BIC is an 8 character code, defined as business party identifier, consisting of the business party prefix (4 alphanumeric), the country code as defined in ISO 3166-1 (2 alphabetic), and the business party suffix (2 alphanumeric). The branch identifier is a 3 character optional element…"; `version="Rolling monthly"` `lifecycle="active"`; 107k+ BICs, 49k+ connected, 227 countries.
- [x] BIC structure: `BIC8 [Branch]` where `BIC8 = 4!c plus 2!a plus 2!c = 8 chars`, branch `3!c` optional → `11` total, lengths in `{8,11}` only; pos 1 to 4 `4!c` `A-Z0-9` (pre-2014 `4!a` letters only), pos 5 to 6 `2!a` ISO 3166-1 plus `XK`, pos 7 to 8 `2!c` alphanumeric with second-char `0`/`1`/`2` informative only (test, passive, reverse billing), pos 9 to 11 `3!c` alphanumeric, `XXX=head office` (BIC8 and BIC8+XXX functionally equivalent but distinct strings).
- [x] No checksum: BIC has no checksum, unlike IBAN, structure is all there is (codeswap.net "BIC has no checksum"), Genfy etc, schwifty type property for `0`/`1`/`2` but no mod, syntactic only.
- [x] Country nuance: BIC country set equals ISO 3166-1 plus `XK` (Kosovo user-assigned), IBAN country set is subset (~80); validator.js bug 2045 fix for `XK`, python-stdnum `bic.py` pattern `^[A-Z]{4}(?P<country_code>[A-Z]{2})[0-9A-Z]{2}([0-9A-Z]{3})?$` plus `country in _country_codes` including `XK` plus `AQ` etc, exceptions `InvalidLength`/`InvalidFormat`/`InvalidComponent`.
- [x] Ecosystem regex consensus: generic `^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$` plus precise `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` plus stdnum `clean(number,' -').strip().upper()` plus validator.js `/^[A-Za-z]{6}[A-Za-z0-9]{2}([A-Za-z0-9]{3})?$/` plus `CountryCodes.has(countryCode) || 'XK'`.
- [x] Wild input shapes validated (§2.1) against ISO 9362 plus SWIFT BIC pages plus SEPA and fintech corpora plus validators (python-stdnum, validator.js, schwifty, BankValidor) and grammar label pattern extended to `(?:BIC|SWIFT)[\s:-]+` case-insensitive plus word guards.
- [x] `BIC:` / `SWIFT:` label scope decision (§4.2 / §8 edge 4 / §13 decision 10): label is presentation-only, fused via `(?:(?:BIC|SWIFT)[\s:-]+)?` into single regex; label outside `notation.compact`, inside `raw_text` span when present; case-insensitive; not a separate semantics.
- [x] BIC8 vs BIC11-XXX equivalence decision (§5.1 / §7 / §8 edge 5 / §13 / §14): `XXX` branch denotes head office, `BIC8` and `BIC8+XXX` functionally equivalent for routing but lexicographically distinct canonical values; `bic11` presentational expansion offered, but validation treats both as syntactic variants of same structure.
- [x] Second-char `0`/`1`/`2` at position 8 decision (§5.1 / §7 / §8 edge 10 / §13 decision 6): informative only, test vs passive vs reverse billing, must not reject; schwifty exposes as type properties, Paxman rule must pass.
- [x] Directory liveness scope decision (§5.5 / §7 / §13 decision 3): SWIFT BIC Directory is rolling monthly with daily delta, 107k+ BICs, connected vs non-connected, out-of-scope for initial `SUCCESS` vs `INVALID` unless `include_directory_validation` gated; determinism-by-snapshot per ARCHITECTURE.md.

File Layout and Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix - What the Shipped ISBN, ISSN, Country and Phone Capabilities Teach BIC (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the BIC proposal to what Paxman already ships.

Refer to `paxman/capabilities/ISBN/`, `paxman/capabilities/ISSN`, `paxman/capabilities/Country`, `paxman/capabilities/Phone`, `paxman/capabilities/IBAN` design notes plus `paxman/engine/orchestrator.py` and `paxman/core/domain.py` - see deep-dive summary in §4.2 / §5 / §6 above and the explore-verified notation, grammar, and rule excerpts. The four architectural lessons for BIC:

1. **Grammar strips, rule validates, capability formats.** ISBN grammars compile at module scope, `RegexStage` then `re.finditer()` then strip `[ -]` and label then bare notation; ISSN grammar strips `-` and space plus `ISSN` label and folds `x` to `X`; Country grammars are zero-registry (alpha2, alpha3, numeric, name); IBAN grammar extracts `country_code` but never validates (rule does); rules enforce check digits or length or charset (`PARSER` plus `LOOKUP_TABLE`); `format_value` reintroduces presentation (ISBN Range Message hyphenation via longest-match; ISSN `value.replace("-", "")` for compact; IBAN groups-of-four). **BIC mirrors this exact split** - grammar tolerant (case, spaces, `BIC`/`SWIFT` label, `XXX` preserved) then `BICNotation(bank_code, country_code, location_code, branch_code, compact)` plus `compact.upper()`; rule `PARSER` for generic structure (`4!c+2!a+2!c` plus optional `3!c`, length in 8/11, `XXX` allowed) plus `LOOKUP_TABLE` for country-code membership (ISO 3166-1 plus `XK`); formatter `grouped` is a trivial `AAAA BB CC [XXX]` reinsertion and `bic11` is append-`XXX` when branch absent.

2. **One file per provenance, one class per section.** ISBN ships `iso_2108_ed2017` (PARSER check-digit plus LOOKUP_TABLE for GS1 prefix), `isbn_users_manual_ed2012` (PARSER mod-11, `X=10`, `lifecycle superseded`), `isbn_range_message_ed2026` (`LOOKUP_TABLE` registrant ranges, `requires_features={"include_range_validation"}`). ISSN mandatory file is `iso_3297_ed2022` with `PARSER` check-digit (`lifecycle active`); any registry layer is a second file `issn_register_ed2025` gated by `requires_features={"include_register_validation"}`. IBAN mandatory file is `iso_13616_1_ed2020` (fused with `iso_7064_ed2003` MOD 97-10) with `PARSER` mod97 (`lifecycle active`); any SWIFT registry layer is a second file `swift_iban_registry_ed2024` (`kind registry`, `lifecycle active`, `requires_features={"include_registry_validation"}`). Country lexicon is `LOOKUP_TABLE` for alpha2 etc. **BIC mandatory file is `iso_9362_ed2022` (`PARSER` structure, `lifecycle active`); country lookup if split is `iso_3166_ed2022` (`LOOKUP_TABLE`); any SWIFT directory layer is a second file `swift_bic_directory_ed2025` (`kind registry`, `lifecycle active`, `requires_features={"include_directory_validation"}`) with `rules/data/bic_directory.py` snapshot.**

3. **No `output_format` in rules, ever.** CI scan `tests/unit/test_rule_output_format_purity.py` rejects the token in `paxman/capabilities/*/rules/` (code, comments, docstrings). `normalize()` returns the default compact form (`bic`); `format_value` renders `grouped` or `bic11`. This presentational-only invariant is non-negotiable for BIC as well, the country `LOOKUP_TABLE` rule must also return compact, not grouped.

4. **Single grammar with optional group avoids spurious AMBIGUOUS; cross-grammar containment is preserved.** ISBN needs two grammars ISBN13 and ISBN10 with separate semantics and feature-gated `active_grammars` `include_isbn10`; engine `_dedup_spans` per-grammar longer-wins, cross-grammar preserved, so ISBN avoids 10 vs 13 overlap by distinct semantics. IBAN and ISSN use single always-active grammar, no `active_grammars` override. Country grammars are zero-registry (four grammars, each lexicon). **BIC must use single grammar with optional branch group `(?:[A-Z0-9]{3})?` to avoid spurious `AMBIGUOUS` where 11 contains 8 as prefix (longer-wins is per-grammar only, cross-grammar is preserved per `orchestrator:_dedup_spans`).** Single grammar keeps the 11-char match over an 8-char prefix at same start via longer-wins, without cross-grammar duplication. Country lookup is `LOOKUP_TABLE` over a frozen set, `PARSER` over structure, same as Country alpha2 pattern.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for BIC. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-21-issn-canonicalization.md` and the deeper ISBN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` - not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*

