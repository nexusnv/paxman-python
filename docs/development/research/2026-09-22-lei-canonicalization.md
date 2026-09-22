# LEI Canonicalization Research — paxman-python

**Date:** 2026-09-22
**Scope:** Primary-source survey of the LEI standard (ISO 17442-1:2020 assignment, ISO 17442-2:2020 digital-certificate embedding, ISO/IEC 7064:2003 MOD 97-10, GLEIF Global LEI System and daily data pool), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `LEI` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org) for ISO 17442-1:2020, ISO 17442-2:2020, ISO 17442:2019, ISO 17442:2012, and ISO/IEC 7064:2003; GLEIF pages (introducing-LEI, LEI namespace/URN, GLEIF API, LEI search, concatenated files); IANA URN namespace registry (`lei` formal); python-stdnum `stdnum/lei.py`; McZen LEI-Validator; three secondary online validators; validator.js negative evidence (no `isLEI`); Wikipedia as secondary; shipped Paxman capabilities (ISIN, IBAN, ORCID) as architectural precedents. Repo state: `dev` @ `d15375a` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN research precedent `docs/development/research/2026-08-21-issn-canonicalization.md` plus the IBAN/BIC precedents (`2026-08-22`, `2026-08-23`) and the ISIN precedent (`2026-08-24`).

---

## Executive Summary

LEI is a strong fit for a Paxman capability: it has an unambiguous canonical form (**compact, no separators, uppercase, exactly 20 chars**: `4 LOU prefix + 14 entity block + 2 MOD 97-10 check digits`, i.e. `^[A-Z0-9]{18}[0-9]{2}$`), a stable multi-part standard (**ISO 17442-1:2020** Part 1 assignment, Edition 1, 2020-08, `90.93 Confirmed` 2026-01-21, ICS 03.060, publisher ISO/TC 68/SC 8, superseding the withdrawn single-part ISO 17442:2019 ← ISO 17442:2012) operated at global scale by **GLEIF** (supranational not-for-profit foundation, Basel/Frankfurt, backed by the G20 and the Financial Stability Board, overseen by the LEI Regulatory Oversight Committee, ~2M+ LEIs by 2022) through ~100 accredited **LOUs** (Local Operating Units) publishing daily into one open data pool, and a well-understood human-readable presentation (**compact run**, plus `LEI:`-labeled prose and the IANA-registered `urn:lei:` carrier — all wrapping-only). The domain mirrors Paxman's value proposition for ISIN/IBAN/BIC: recognizing tolerant human surface, validating strictly against authority, returning canonical compact value with provenance. Checksum is **ISO/IEC 7064 MOD 97-10 over the whole string** (same algorithm as IBAN, no rearrangement — check digits sit at the end), verified locally against five authority-attested vectors.

Key findings that shape the design:
1. **Canonical form is compact uppercase 20-char** (`213800KUD8LAJWSQ9D15`, `5493000IBP32UQZ0KL24`, `7LTWFZYICNSX8D621K86`). Length is strictly `20` only, never `19` or `21`. Regex consensus is `^[A-Z0-9]{18}[0-9]{2}$` (folk pattern corroborated by McZen's documented validation rules and stdnum's `mod_97_10.validate` path). There is **no official grouped/hyphenated display** (unlike IBAN paper or ISBN hyphens) — spacing in the wild is noise that validators strip, not a display convention. This maps onto Paxman's presentational-only invariant: `format_value()` renders `lei` (compact, default) vs `urn` (`urn:lei:…`, same-entity expansion) without touching validity.
2. **One grammar suffices, fixed-count by construction.** Unlike ISBN (two lengths) or IBAN (country-dependent 15–34), LEI has exactly one length, so a single `LEIRecognitionGrammar` with Regex strategy and a fixed-count single-space interleave (`(?: ?[A-Z0-9]){18} ?[0-9]`, ISIN precedent) covers compact + spaced + labeled + URN-carried forms. Single-space discipline keeps free-text absorption bounded; double spaces, tabs, and hyphens stay `MISSING` (hyphen deferred to a community extension — only stdnum's strip attests it).
3. **Validation is three-level, checksum-anchored.** Level 1: generic structure + MOD 97-10 (always-active PARSER, ISO 17442-1 + normative ISO/IEC 7064 reference, fused in one file per the IBAN precedent). Level 2: LOU-prefix allowlist (always-active LOOKUP_TABLE against an append-only GLEIF-derived snapshot — the ISIN/ANNA-prefix analogue; prefixes are never removed because LEI codes survive LOU retirement and transfer). Level 3: issued/live membership in the GLEIF data pool (deferred — snapshot size in the millions, daily churn, and liveness≠validity; same scope cut IBAN made for BBAN structure).
4. **Positions 5–6 carry no enforceable constraint.** Ecosystem folklore says "reserved zeros," but GLEIF's own URN worked example `7LTWFZYICNSX8D621K86` (mod97-valid) carries `FZ` at 5–6. Enforcement would fabricate a constraint the authority's own example violates — record as informative only (BIC location-second-char precedent).
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 17442-1:2020` (active, current) owns structure + check digits; `GLEIF LOU prefix list` (`kind="registry"`, Rolling) owns prefix membership; `ISO/IEC 7064:2003` is cited normatively inside the ISO file (IBAN fused-file precedent) rather than split. The two-rule PARSER+LOOKUP pair satisfies ADR-0012 corroboration by construction (ISIN dual-rule precedent).

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---
## 1. Target User

| Persona | Why they need LEI canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Payments / treasury engineers** | Normalize `lei: 5493000ibp32uqz0kl24` vs `5493000IBP32UQZ0KL24` vs `urn:lei:5493000IBP32UQZ0KL24` to one compact key for EMIR/MiFIR reporting, KYC joins, and pre-submission validation | Core banking, payment hubs, ISO 20022 (LEI in creditor/debtor blocks), treasury systems |
| **Risk / compliance teams** | Validate counterparty LEIs at ingest; distinguish structurally-invalid (`INVALID`) from never-seen runs (`MISSING`) with span-preserving provenance; resolve entities alongside BIC/ISIN (GLEIF publishes BIC-to-LEI and ISIN-to-LEI mapping files) | AML screening, entity resolution, knowledge-graph institution matching, corporate ERP vendor master |
| **Data engineering / reconciliation** | Extract and canonicalize LEIs from free-text filings, PDFs, emails, XBRL facts, or scraped HTML with span-bearing provenance; join on compact canonical key against concatenated-file dumps | ETL pipelines, filing parsers, Open Corporates aggregation, LLM extraction post-processing |
| **Fintech / onboarding flows** | Validate user-supplied LEI at form ingest; reject typos via MOD 97-10 before hitting the GLEIF API (offline-first, no network in the validation path) | KYC flows, marketplace seller verification, invoice parsers carrying LEI beside IBAN/BIC |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many LEI mentions) and a contract; Paxman returns one canonical LEI (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ISIN (compact-12 default, `grouped` offered) and IBAN (`electronic` default, `paper` offered) ergonomics, but the canonical default is **compact 20-char** with an offered **`urn`** expansion instead of a grouped display (no grouping convention is attested).

---
## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

From the Phase 1C survey (ISO catalogue pages, GLEIF namespace/API/search/concatenated-files pages, IANA registry, stdnum strip logic, McZen rules, secondary validators, concatenated-file dumps):

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Compact canonical | `213800KUD8LAJWSQ9D15` | ISO 17442-1 pattern; stdnum `validate()`; all validators; concatenated files | canonical | RECOGNIZE | main pattern body `[A-Z0-9]{18}[0-9]{2}` |
| Lowercase / mixed case | `5493000ibp32uqz0kl24`, `7ltwfzyicnsx8d621k86` | stdnum `.upper()` fold; GLEIF search case-insensitive | common | RECOGNIZE | `(?ai:)` + `.upper()` fold |
| Single-space separated | `5493 000I BP32 UQZ0 KL24` | stdnum `clean(number, ' -')` strips spaces | common | RECOGNIZE | fixed-count `(?: ?…)` interleave, single-space only |
| Hyphen separated | `5493-000I-BP32-UQZ0-KL24` | stdnum `clean` strips `-` (single validator) | rare | DEFER | community `extra_grammars` candidate |
| Labeled prose | `LEI: 5493000IBP32UQZ0KL24`, `LEI 213800KUD8LAJWSQ9D15`, `lei-7LTWFZYICNSX8D621K86` | prose convention (`LEI:` + code, cf. GLEIF's own `(LEI): 506700GE1G29325QX363` display); IBAN/ORCID label precedent | common | RECOGNIZE | fused label `[\s:-]+`, glued reject |
| URN carrier | `urn:lei:7LTWFZYICNSX8D621K86` | IANA formal `lei` namespace (`urn-formal/lei`, GLEIF); GLEIF namespace page format + worked example | official, rare in prose | RECOGNIZE | optional carrier branch, case-insensitive |
| GLEIF-URL embedded | `https://search.gleif.org/#/record/5493000IBP32UQZ0KL24` | resolver links on the web (LEI search tool) | occasional | RECOGNIZED | URL-path-embedded LEI → SUCCESS (34, 54) via word_only boundaries (ISIN precedent); URL-level semantics remain the URL capability's ownership — amended per oracle review 2026-09-22 |
| vLEI credential strings | (distinct credential format) | vLEI governance framework (separate family) | out of scope | REJECT | different spec; documented negative |
| Truncated / over-long | 19-char / 21-char runs | length guard (McZen: exactly 20) | invalid | REJECT | never 19/21 (`MISSING`) |
| Lapsed-renewal LEIs | structurally valid, registry-stale | Wikipedia validity (code unchanged on renewal/transfer) | valid input | RECOGNIZE | status is not checked (liveness ≠ validity) |

A v1 that does NOT recognize hyphen-grouped or URL-embedded forms states that explicitly here AND raises it as an Open Decision (§13 rows 9/11) so downstream planners see the deliberate scope cut.

### 2.2 Wild variants — adversarial mutations of each inventoried form

Enumerated from GLEIF pages, concatenated-file dumps, and real validators; stress-test every §2.1 RECOGNIZE form:

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical compact | `213800KUD8LAJWSQ9D15`, `5493000IBP32UQZ0KL24` | Spec master form |
| 2 | Lowercase / mixed case | `213800kud8lajwsq9d15`, `7LtWfZyIcNsX8D621K86` | case-insensitive, `.upper()` |
| 3 | Single-space separated | `5493 000IBP32UQZ0KL24`, `2138 00KU D8LA JWSQ 9D15` | fixed-count interleave, single-space only |
| 4 | Label with colon/space/hyphen | `LEI: 5493000IBP32UQZ0KL24`, `lei 213800KUD8LAJWSQ9D15`, `LEI-7LTWFZYICNSX8D621K86` | case-insensitive, `[\s:-]+`, span includes label |
| 5 | URN carrier | `urn:lei:7LTWFZYICNSX8D621K86`, `URN:LEI:5493000IBP32UQZ0KL24` | case-insensitive carrier, span includes carrier |
| 6 | Irregular whitespace | `5493  000I…` (double), `5493\t000I…` (tab) | NOT tolerated → `MISSING` (single-space discipline) |
| 7 | Hyphen separated | `5493-000I-…` | v1 `MISSING` (deferred extension) |
| 8 | Trailing annotation | `5493000IBP32UQZ0KL24 (BBC)`, `…D15, LEI` | not swallow parenthetical/comma tail |
| 9 | Multiple per line | `213800KUD8LAJWSQ9D15 / 5493000IBP32UQZ0KL24` | 2+ matches |
| 10 | Quoted / bracketed / CSV | `"213800KUD8LAJWSQ9D15"`, `[…D15]`, `a;b;5493…24;` | inside punctuation |
| 11 | OCR / homoglyph | `0` vs `O`, `1` vs `I` swaps | strict charset, no autocorrection |
| 12 | Over-long / under-long | 19-char, 21-char, 20+glued-letter (21-class) | length guard, never 19/21 |
| 13 | X-glued runs | `X5493000IBP32UQZ0KL24`, `…KL24Y` | word-boundary guards |
| 14 | Invalid checksum (substitution) | `213800KUD8LXJWSQ9D15` (mod97=55) | grammar claims, rule rejects |
| 15 | Transposed pair | adjacent-swap of a valid LEI | MOD 97-10 detects nearly all single transpositions → `INVALID` |
| 16 | Unknown LOU prefix, checksum valid | fabricated `ZZZZ…` + valid check | grammar claims, LOU rule rejects |
| 17 | Retired-LOU prefix, checksum valid | old issuer block, valid check | SUCCESS (snapshot never removes) |
| 18 | GLEIF-URL embedded | `…/record/5493000IBP32UQZ0KL24` | v1 `MISSING` for the LEI capability (deferred) |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Folk consensus (validators, McZen rules) | `^[A-Z0-9]{18}[0-9]{2}$` — 18 alphanum + 2 numeric check |
| `arthurdejong/python-stdnum` `stdnum/lei.py` | `compact(number) = clean(number, ' -').strip().upper()` then `mod_97_10.validate(number)`; `is_valid()` wraps `ValidationError`; docstring vectors `213800KUD8LAJWSQ9D15` (valid) / `213800KUD8LXJWSQ9D15` (InvalidChecksum) |
| McZen `LEI-Validator` `index.js` (README) | Length exactly 20; charset uppercase alphanum; parts `louPrefix[0:4]` / `entityPart[4:18]` / `checkDigits[18:20]`; MOD 97-10 check; `generateCheckDigits(first18)` (example `213800D1L3R2MWV39G` → `88`, independently verified 2026-09-22) |
| Point Nine LEI validator (secondary) | ISO 17442 pattern + checksum + real-time GLEIF cross-reference (three-level consensus corroboration) |
| NanoUtil / ValidateFin (secondary) | 20-char format + recomputed ISO 7064 MOD 97-10 check digits |
| `validator.js` | **Negative evidence:** no `isLEI` module exists (searched 2026-09-22) — LEI lacks the one-line-regex treatment ISBN/IBAN enjoy, consistent with checksum + registry-gated validation |

**Normalization contract (reuse ISIN pattern):**
```python
# stdnum pattern — strip separators, upper, then MOD-97-10
import re

compact = re.sub(r"[ \-]", "", raw).strip().upper()  # spaces + hyphens only
# then validate: len == 20 and ^[A-Z0-9]{18}[0-9]{2}$ and mod97(expand(compact)) == 1
```

### 2.3 What input is NOT a LEI mention
- IBANs (`DE89 3704 0044 0532 0130 00`, 15–34 with `CCDD` head) — different length class (except 20-char IBANs, see §14), rearranged-mod97, per-country registry (ISO 13616).
- BICs (`DEUTDEFF`, 8/11) and ISINs (`US0378331005`, 12) — fixed lengths disjoint from 20; no whole-string checksum confusion.
- UUIDs (32/36), ORCIDs (16/19 with hyphens), DOIs (`10.` prefix) — disjoint shapes; ORCID compact 16 never reaches 20.
- Short alphanumeric runs, bare LOU prefixes (`5493`), 19/21-char runs — `MISSING` vs `INVALID` boundary (see §9).
- GLEIF URLs as URLs — URL-path-embedded LEIs are recognized via word_only boundaries (ISIN precedent); URL-level semantics remain the URL capability's ownership.

### 2.4 Single-mention vs multi-mention input
Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct LEIs (counterparty pair) → `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS`.

---
## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact plus structured decomposition
```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LEINotation:
    """LEI notation — grammar-normalized compact form.

    ``lou_prefix`` is the 4-char issuer block, uppercased.
    ``entity_block`` is the 14-char entity-specific block (positions
      5-18), uppercased, leading zeros preserved. Positions 5-6 carry
      no enforceable constraint (often but not always ``00``).
    ``check_digits`` is the 2-digit string at positions 19-20.
    ``compact`` is the full 20-char string, uppercased, separators
      stripped, equals lou_prefix+entity_block+check_digits.

    The grammar never computes the check digits (MOD 97-10) and never
    validates LOU membership; rules own both (grammar/rule boundary
    per HOW_TO_ADD_NEW_GRAMMAR.md).
    """

    lou_prefix: str  # e.g. "2138", "5493", "7LTW" — length 4, A-Z0-9
    entity_block: str  # e.g. "00KUD8LAJWSQ9D" — length 14, A-Z0-9
    check_digits: str  # e.g. "15" — length 2, 0-9
    compact: str  # e.g. "213800KUD8LAJWSQ9D15" — exactly 20, ≡ parts
```

**Considered alternative — single field `compact` only:** sufficient for the MOD-97-10 rule (whole-string operation), and the LOU slice `compact[0:4]` is derivable. However the four-field decomposition is preferred because:
1. The ISO structure indexes by LOU prefix (rule table keyed by `lou_prefix`, ISIN `country_code` analogue).
2. `IBANNotation`'s prefix-split precedent proves the value of exposing the routing field for LOOKUP rules.
3. `check_digits` as a first-class field lets the rule pin the numeric-check invariant (`compact[18:20].isdigit()`) without re-slicing magic numbers in two files.

Every field is `str` (HOW_TO_ADD_NEW_CAPABILITY.md requires all notation fields be `str`).

**Invariants the grammar enforces (before rules):**
- `lou_prefix` is exactly 4 `A-Z0-9` (uppercased from `[A-Za-z0-9]`).
- `entity_block` is exactly 14 `A-Z0-9` (uppercased, leading zeros preserved).
- `check_digits` is exactly 2 digits `0-9`.
- `compact` is exactly 20, equals `lou_prefix + entity_block + check_digits`; `compact == strip-spaces-and-label(raw_text).upper()`.
- `raw_text` preserves original span (label/carrier + spacing + case); the notation is the syntax-normalized token.

### 3.2 Why not carry spaces, labels, or carriers in the notation
Spaces, `LEI:` labels, and `urn:lei:` carriers have **no lexical significance** for validity (concatenated files store bare compact; URN is a naming wrapper per the GLEIF namespace page). Compact and wrapped forms of the same LEI share identity; dedup and status logic operate on `compact`. Presentation is `Capability.format_value()` only.

### 3.3 Why `lou_prefix` is not a shape discriminator literal
The accredited-LOU set is ~100 four-char codes and grows by accreditation (plus never-removed retired blocks) — modeling each as a `Literal` would be brittle. Instead `lou_prefix` is a free `str` validated by a `LOOKUP_TABLE` rule against the append-only snapshot, mirroring IBAN `country_code` and ISIN `_VALID_PREFIXES`.

---
## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)
Per HOW_TO_ADD_NEW_GRAMMAR.md and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, LEI has a distinctive fixed-width shape (exactly 20, `[A-Z0-9]{18}[0-9]{2}`, optional `LEI` label, optional `urn:lei:` carrier), so **Regex** is correct. No lexicon table at recognition — the LOU vocabulary lives in the rule layer.

### 4.2 Reference pattern (adapted from ISIN, IBAN, ORCID verbatim precedent)
ISIN precedent (`paxman/capabilities/ISIN/grammar/isin_recognition.py`):
```python
_ISIN_BODY = (
    r"(?:(?ai:ISIN)[\s:-]+)?"
    r"(?P<compact>(?ai:[A-Z]{2}(?: ?[A-Z0-9]){9} ?[0-9]))"
)
```
IBAN precedent (`paxman/capabilities/IBAN/grammar/iban_recognition.py`): LabelMatcher with `labels=frozenset({"IBAN"})`, `separator=r"[\s:-]+"`, `glued_policy="reject"`.
ORCID precedent (`paxman/capabilities/ORCID/grammar/orcid_recognition.py`): fused label + host carrier + glued guard + `word_only` both sides.

**Proposed LEI pattern (single grammar, label kind with carrier branch):**
```python
import re
from paxman.capabilities.LEI.notation import LEINotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope string pattern - compiled by RegexStage (never inside recognize()).
# Core: 18 alphanum + a 2-digit check tail = exactly 20 payload chars, never
# 19 or 21. The ISIN single-trailing-digit shape does NOT transfer: LEI has
# TWO check digits, so the tail is (?: ?[0-9]){2}, not a lone ?[0-9] - the
# latter claims 19 chars and, under word_only().lookahead, matches nothing.
# Single-space interleave (ISIN precedent) tolerates stdnum-attested spacing
# while the fixed count bounds absorption; double spaces/tabs stay MISSING.
# Label fused (IBAN/ORCID precedent, glued reject); URN carrier optional
# (IANA-registered form, GLEIF worked example). (?ai:) ASCII restriction
# rejects fullwidth digits and non-ASCII homoglyphs while
# BoundaryGuard.word_only() stays Unicode-aware.
_LEI_CORE = r"(?ai:[A-Z0-9](?: ?[A-Z0-9]){17}(?: ?[0-9]){2})"
_LEI_BODY = (
    r"(?:(?ai:LEI)[\s:-]+)?"
    r"(?:(?ai:urn:lei:))?"
    rf"(?P<compact>{_LEI_CORE})"
)
# Glued-label guard: fires only when a COMPLETE 20-char LEI shape follows
# literal "LEI" with no separator ("LEI5493..." = 23+ chars), mirroring ISIN's
# full-shape _GLUED_LABEL_GUARD. Two traps avoided (both verified): a
# one-alnum guard would reject a bare LEI whose own prefix starts "LEI", and
# putting "urn:lei:" in the guard makes the carrier branch unreachable - the
# carrier is correct glued form, not glue; a carrier-inclusive guard fires
# exactly when the branch would match and truncates the span to "lei:...".
# Length separates the two cases: glued label = 3 + 20 chars, bare code = 20.
_LEI_GLUED_GUARD = r"(?!(?ai:LEI[A-Z0-9]{18}[0-9]{2}))"
_LEI_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _LEI_GLUED_GUARD
    + _LEI_BODY
    + BoundaryGuard.word_only().lookahead
)


def _lei_notation(match: re.Match[str]) -> LEINotation:
    raw_compact = match.group("compact")
    compact = "".join(
        ch for ch in raw_compact if ch.isascii() and ch.isalnum()
    ).upper()
    # compact is now exactly 20 alphanum ending in 2 digits; split structurally
    return LEINotation(
        lou_prefix=compact[0:4],
        entity_block=compact[4:18],
        check_digits=compact[18:20],
        compact=compact,
    )


class LEIRecognitionGrammar(PipelineGrammar[LEINotation]):
    """LEI recognition — compact 20-char with label and URN carrier."""

    name = "lei_recognition"
    semantics = "lei_recognition"
    single_value = True
    pre = StandardPre[LEINotation](empty_guard=True)
    regex = RegexStage[LEINotation](
        pattern=_LEI_PATTERN, notation_fn=_lei_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs ISIN/IBAN/ORCID:*
- Ship as module-scope **string** pattern; `RegexStage` compiles (mirrors ISIN `_ISIN_BODY`). Do not double-compile.
- Strip in `notation_fn` via `isascii()` + `isalnum()` + `.upper()` (ISIN precedent line 39). The `(?ai:)` body plus ASCII filter rejects Kelvin-sign and Unicode-digit homoglyphs.
- Fixed count (`{17}` interleave + `(?: ?[0-9]){2}` check tail) guarantees exactly 20 payload chars — 18 alphanum + 2 digits — never 19/21; a trailing `(?!\w)`-class guard comes from `BoundaryGuard.word_only().lookahead` (ISIN/ORCID precedent). The pattern above was executed against every §2.1 RECOGNIZE form and all §8 edge rows before publication (compact/lowercase/spaced/labeled/URN all match with the claimed spans; 19/21/double-space/tab/hyphen/glue all stay `MISSING`; glued label rejected while a bare 20-char code starting `LEI`+alnum still matches).
- **Label handling:** `(?:LEI)[\s:-]+` fused with one-or-more separator, never zero-width; glued `LEI5493…` (23 chars: label + complete code) rejected by `_LEI_GLUED_GUARD`, while a bare 20-char code that itself starts `LEI`+alnum still matches — the full-shape guard separates the two by length (ISIN `_GLUED_LABEL_GUARD` precedent). `raw_text` includes label/carrier when matched; `notation.compact` is bare.
- **Carrier handling:** `(?:urn:lei:)?` fused, case-insensitive (Gatt-level: the namespace page states the format is "not case sensitive"). The carrier is deliberately excluded from `_LEI_GLUED_GUARD`: including it would fire the guard in exactly the case the branch exists to match, making the branch dead code and dropping `urn` from the span (verified). The `urn` offered format (§6.1) re-enters through this branch (ADR-0010 fixed-point, ORCID `uri` precedent).
- **Whitespace tolerance:** single ASCII spaces only, interleaved with fixed count — `5493  000I` (double) and tab-separated stay `MISSING` (IBAN paper single-space discipline precedent). Hyphens are NOT interleaved in v1 (deferred, §2.1).
- Uses `PipelineGrammar` + `StandardPre` + `RegexStage` (shipped-grammar stack, not the bare-`Grammar` teaching form).

**Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a pattern element (compact→core, lowercase→`(?ai:)`+fold, spaced→interleave, labeled→label group, URN→carrier branch); every DEFER/REJECT row names its mechanism (§13 rows 9/11).

**One grammar vs two:** Single grammar — there is exactly one length and one meaning. A split (e.g. `lei_compact` + `lei_spaced`) would create cross-grammar containment with no semantic distinction (worse than BIC 8/11, which at least differ in branch presence).

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)
- Grammar emits **span-bearing** `RecognitionMatch[LEINotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize`).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))`. Stages must not mutate `text`.
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** (`_dedup_spans`, `paxman/engine/orchestrator.py:456`). Cross-grammar containment never dedups.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`, `paxman/engine/orchestrator.py:811`).

### 4.4 Guard boundaries against sibling grammars
LEI `20` vs IBAN `15–34` vs ISIN `12` vs BIC `8/11` vs ORCID `16/19` vs UUID `32/36` — length plus positional-checksum discrimination:

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| LEI | `20` `[A-Z0-9]{18}[0-9]{2}` | any alphanum | `(?!\w)` blocks carving from longer runs; checksum is whole-string mod97 |
| IBAN | `15–34` `[A-Z]{2}\d{2}[A-Z0-9]+` | `CC` alpha + `DD` digits | 20-char IBANs (where registered) overlap in length — disambiguated by positional `CCDD` + per-country length + rearranged-mod97 vs plain-mod97 (§14) |
| ISIN | `12` `[A-Z]{2}[A-Z0-9]{9}\d` | `CC` + 9 + check | shorter; LEI run contains no 12-char claim unless separately matched by ISIN grammar (per-capability resolution) |
| BIC/ORCID/UUID | `8/11`, `16/19`, `32/36` | fixed shapes | disjoint lengths; UUID 32-char run contains no 20-char LEI sub-claim inside one capability's scan |

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)
- `semantics = "lei_recognition"` (identity id). Both validating rules declare `target_semantics = frozenset({"lei_recognition"})`; engine `_validate_affinity` (`paxman/engine/orchestrator.py:543`) fails fast if a rule names an unclaimed id.
- Hyphen-tolerant community extension later coalesces on the same id (HOW_TO_ADD_NEW_GRAMMAR.md option A).

### 4.6 `single_value` — one mention per call vs batch processing
Recommendation: **initial `single_value=True`** (ISIN/IBAN/ORCID precedent; `paxman/engine/orchestrator.py:621-673` enforcement; counterparty-pair documents use the caller-owned segmentation path `docs/recipes/segmentation.md`).

---
## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO** — Technical Committee **ISO/TC 68/SC 8** (Reference data for financial services), the same subcommittee behind ISO 9362 (BIC) and ISO 13616 (IBAN). ICS **03.060**. |
| **System operator (RA-analogue)** | **GLEIF** (Global Legal Entity Identifier Foundation) — supranational not-for-profit, operational manager of the Global LEI System since 2014 (established under Swiss law; Frankfurt/Basel). Overseen by the **LEI ROC** (Regulatory Oversight Committee, coalition of regulators/central banks); chartered by the **G20/FSB** post-2008-crisis. Accredits **LOUs**, publishes the daily data pool, runs LEI search + API. |
| **Spec name** | `ISO 17442-1 — Financial services — Legal entity identifier (LEI) — Part 1: Assignment` (+ Part 2: Application in digital certificates, X.509/ISO/IEC 9594-8 embedding) |
| **Current edition** | **ISO 17442-1:2020 (Ed.1, published 2020-08-18)** — current, `90.93 Confirmed` (review closed 2026-01-21). 8 pages. Withdraws ISO 17442:2019. See lineage table below. |
| **Check character system** | `ISO/IEC 7064:2003` MOD 97-10 (pure system, modulus 97, base 10, alphanum set) — same algorithm family as IBAN, applied whole-string without rearrangement. |
| **Country code reference** | None — by design. The LEI is "neutral, with no embedded intelligence or country codes" (ISO TC 68). Jurisdiction lives in Level 1 reference data (legal jurisdiction code list), not in the code. |
| **Related specs** | `ISO 17442-2:2020` (X.509 embedding); GLEIF Common Data File formats (LEI-CDF 3.1 Level 1, RR-CDF 2.1 Level 2); IANA `urn:lei:` namespace (RFC 8141 family); ISO 20275 (entity legal forms), ISO 5009 (organizational roles) code lists. |

**LEI structure (ISO 17442-1 assignment clause, GLEIF code-structure documentation, Wikipedia code-structure table):**

```
LOU prefix | entity block      | check
1-4        | 5-18 (14 chars)   | 19-20 (2 digits)
4!c        | 14!c              | 2!n  (MOD 97-10 over the whole string)
Total exactly 20, charset [A-Z0-9], canonical uppercase.
```

- Formal charset: `^[A-Z0-9]{18}[0-9]{2}$` compact; `(?i)` accepted, canonical `upper`.
- Positions 5–6 are *often* `00` (stdnum: "2 digits that are often 0") but carry **no enforceable constraint** — GLEIF's own URN example `7LTWFZYICNSX8D621K86` has `FZ` (§7.1 worked vectors). Informative only.
- Check digits 19–20: generated as `98 − mod97(first-18 + "00")`, validated as whole-string `mod97 == 1` (McZen generation example `213800D1L3R2MWV39G` → `88` independently verified 2026-09-22). **Correction flag for downstream planning:** `docs/development/MILESTONE.md` row 6 claims the LEI has "no check digit" — that roadmap claim is wrong (both directions above verify, and every attested vector carries 2 valid check digits); correct the MILESTONE row when the LEI plan lands.
- Real vectors (all mod97-verified locally 2026-09-22): `213800KUD8LAJWSQ9D15` (stdnum docstring), `5493000IBP32UQZ0KL24` + `213800WSGIIZCXF1P572` (Wikipedia structure table), `506700GE1G29325QX363` (GLEIF introducing-LEI page), `7LTWFZYICNSX8D621K86` (GLEIF URN namespace page).

**Lineage table (ISO 17442 editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 17442:2012 | 2012-05-29 (Ed.1) | withdrawn 2019-04-12 | First edition, post-G20-endorsement; 6 pages |
| ISO 17442:2019 | 2019-04-12 (2nd ed.) | withdrawn 2020-08-18 | Revised single-part; immediately superseded by the Part 1/Part 2 split |
| ISO 17442-1:2020 | 2020-08-18 (Ed.1 Part 1) | current, 90.93, confirmed 2026-01-21 | Assignment; minimum elements of the LEI scheme; cancels 2019 |
| ISO 17442-2:2020 | 2020-08-18 (Ed.1 Part 2) | current, 90.93, confirmed 2026-01-20 | X.509/ISO/IEC 9594-8 certificate embedding (out of scope for recognition, cited for lineage) |

**Citation Details Table (for `Provenance`):**

| `authority` | `specification_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 68/SC 8) | `ISO 17442-1:2020` | `2020-08` (Ed.1 Part 1, current) | `https://www.iso.org/standard/78829.html` | `active` — supersedes 2019 | `2020` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 17442-2:2020` | `2020-08` (Ed.1 Part 2, current) | `https://www.iso.org/standard/79917.html` | `active` | `2020` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 17442:2019` | `2019-04` (2nd ed.) | `https://www.iso.org/standard/75998.html` | `withdrawn` 2020-08-18 | `2019` | `specification` |
| ISO (ISO/TC 68/SC 8) | `ISO 17442:2012` | `2012-06` (1st ed.) | `https://www.iso.org/standard/59771.html` | `withdrawn` 2019-04-12 | `2012` | `specification` |
| ISO/IEC JTC 1/SC 27 | `ISO/IEC 7064:2003` | `2003-02` (Ed.1, MOD 97-10) | `https://www.iso.org/standard/31531.html` | `active` (confirmed 2006-09-14) | `2003` | `specification` |
| GLEIF (system operator) | `GLEIF LOU prefix list` | `Rolling` (accredited-LOU directory + concatenated files) | `https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file` | `active` — rolling | `2026` | `registry` |
| IANA (via GLEIF) | `URN namespace lei` | `urn-formal/lei` | `https://www.iana.org/assignments/urn-namespaces/urn-namespaces.xhtml` | `active` | — | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical rule citing ISO 17442:2012/2019 would carry `lifecycle="withdrawn"`. The v1 ISO rule is `active`; the GLEIF prefix list is `kind="registry"` `lifecycle="active"` (rolling).

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_17442_1_ed2020.py` | `authority="ISO"`, `specification_name="ISO 17442-1:2020"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/78829.html"`, `version="2020"`, `lifecycle="active"`, `publication_year=2020` | `Section 4-lei-structure-mod97-10` (20-char structure + whole-string MOD 97-10; cites ISO/IEC 7064:2003 normatively, IBAN fused-file precedent) | Generic structure: exactly 20, `^[A-Z0-9]{18}[0-9]{2}$`, decomposition consistency, `mod97 == 1`; `normalize()` returns compact `upper` |
| `rules/gleif_lou_prefix_list_ed2026.py` | `authority="GLEIF"`, `specification_name="GLEIF LOU prefix list"`, `kind="registry"`, `reference_url="https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file"`, `version="Rolling"`, `lifecycle="active"`, `publication_year=2026` | `Section *-lou-prefix-membership` (LOU block in accredited set) | Whether `lou_prefix` is in the append-only snapshot; full-conjunction re-validation (structure + checksum + prefix, ISIN dual-rule precedent for one-directional ADR-0012 corroboration) |

Each `Rule[LEINotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`, `paxman/core/domain.py:236-271`):

```python
class Section4LEIStructureMOD9710(Rule[LEINotation]):
    name = "Section 4-lei-structure-mod97-10"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Assignment clause (20-char structure + MOD 97-10, via ISO/IEC 7064:2003)"
    target_semantics = frozenset({"lei_recognition"})
    requires_features = frozenset()

    def matches(self, notation: LEINotation, contract: Contract) -> bool: ...
    def normalize(self, notation: LEINotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO 17442 lineage** confirmed via `https://www.iso.org/standard/78829.html` (Part 1 current, 90.93, confirmed 2026-01-21, cancels 2019) and `https://www.iso.org/standard/79917.html` (Part 2 current, X.509) plus withdrawn chain `https://www.iso.org/standard/75998.html` → `https://www.iso.org/standard/59771.html` (2012-05-29, Ed.1, ICS 03.060, TC 68/SC 8).
- **ISO/IEC 7064:2003** catalogue: `https://www.iso.org/standard/31531.html` (Ed.1, pure systems incl. MOD 97-10, `90.93 Confirmed`, ICS 35.030, JTC 1/SC 27; detects all single substitutions, nearly all transpositions).
- **GLEIF as operator:** `https://www.gleif.org/en/about-lei/introducing-the-legal-entity-identifier-lei` (20-char code, four ISO 17442 principles, G20/FSB/ROC governance, example `506700GE1G29325QX363`) + concatenated files `https://www.gleif.org/en/lei-data/gleif-concatenated-file/about-the-concatenated-file` (daily, all LEIs + reference data, XML/ZIP, free, challenge facility) + search `https://www.gleif.org/en/lei-data/lei-search/about-lei-search` (free search, ownership, BIC/ISIN mapping) + API `https://www.gleif.org/en/lei-data/gleif-api` (Golden-Copy-backed, production fall 2020).
- **URN carrier:** `https://www.gleif.org/en/lei-data/lei-namespace` (`URN:LEI:[20-digit]`, not case sensitive, worked `urn:LEI:7LTWFZYICNSX8D621K86`) + `https://www.iana.org/assignments/urn-namespaces/urn-namespaces.xhtml` (formal `lei → urn-formal/lei → GLEIF`).
- **No country code by design:** ISO TC 68 "What is LEI" (via web search 2026-09-22) — neutral code, no embedded intelligence or country codes.
- **Checksum positive:** stdnum `mod_97_10.validate` path + McZen MOD 97-10 + generation example verified + five vectors mod97-verified locally (see §7.1).

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. The ISO rule checks: length exactly 20, charset `^[A-Z0-9]{18}[0-9]{2}$`, decomposition consistency (`compact == lou_prefix + entity_block + check_digits`), and whole-string `mod97 == 1`. The GLEIF rule checks the same full conjunction plus `lou_prefix` membership in the snapshot. Positions 5–6 content never rejects. All return `False` for any invalid input, never raise. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** — returns the **default compact form** (uppercase 20-char). Never reads the presentation field — the CI source-scan rejects any presentation token in `paxman/capabilities/*/rules/` modules. Presentation is the capability `format_value()` seam only. Both rules must return the **same** default string for the same valid notation — candidate dedup `(value, recognition_rule, validation_rule)` (`paxman/engine/orchestrator.py:811`) keeps agreement at `SUCCESS`.
- **`RuleStrategy` choice:** ISO structure+checksum is `PARSER` (ISIN `Section4IsinStructureCheckDigit` precedent, `paxman/capabilities/ISIN/rules/iso_6166_ed2021.py:56-90`); LOU membership is `LOOKUP_TABLE` (ISIN ANNA `Section5CountryAndSpecialPrefix` precedent). The PARSER+LOOKUP pair on shared semantics gives ADR-0012 corroboration by construction.

### 5.4 LOU-prefix and issued-membership scope decision

The **accredited-LOU prefix set** (~100 four-char blocks, e.g. observed `2138`, `5493`, `5067`, `7LTW` — stated without LOU-name attribution, which no fetched source provides) is the LEI analogue of ISIN's country/special-prefix allowlist: small, slow-changing, high-value (rejects never-assigned fabrications that pass the checksum). **Recommendation: always-active LOOKUP_TABLE** with an append-only snapshot (`rules/data/lou_prefixes.py`, never remove — LEI codes survive LOU retirement and transfer per the validity evidence) plus a refresh procedure (re-census GLEIF directory + concatenated files; add-only).

**Issued/live membership** (is this exact 20-char string present in the GLEIF Golden Copy / concatenated files, Level 1 + registration status) is the IBAN-BBAN-structure analogue: relational, millions of rows, daily churn, and — crucially — liveness is not validity (lapsed-renewal codes remain well-formed identifiers of their entity). **Recommendation: deferred** behind a future `include_issued_validation`-gated LOOKUP_TABLE (mirrors ISIN #179 registry-liveness deferral and ISBN `include_range_validation`). The v1 validity boundary is structure + checksum + LOU membership. Renewal status, Level 2 ownership, and entity-name resolution require network access and are permanently out of scope (determinism-by-construction; GLEIF API is evidence infrastructure, never a runtime dependency).

### 5.5 Assignment / registration authority & data-pool content

Network: **GLEIF** (operator, Basel/Frankfurt) + **LOUs** (~100 accredited issuers: exchanges, CSDs, data vendors) as registrars + **Registration/Validation Agents** as auxiliaries, under **ROC** oversight and **FSB/G20** charter. Blocks: each LOU mints LEIs in its 4-char prefix block and publishes Level 1 (who-is-who: legal name, registered address, jurisdiction, legal form, status) + Level 2 (who-owns-whom: direct/ultimate parents, exceptions) reference data; **GLEIF** consolidates into daily **concatenated files** (per-format central XML/ZIP, free, with challenge facility) and the **Golden Copy + deltas**, served via **LEI search** and the **GLEIF API** (fuzzy name/address matching, BIC/ISIN mapping).

Per the concatenated-files page: *"GLEIF publishes updated Concatenated Files daily. These include all current LEIs globally and all related LEI reference data … free of charge … XML in ZIP."* Mandatory registration data per LEI record: the 20-char code itself, Level 1 business-card fields, managing LOU, registration/renewal/next-renewal dates, status, and corroborating Register (RA) source — none of which the v1 capability reads (offline validity only).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`**, never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True`.

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class LEIContract(CapabilityContract):
    """User-facing contract for LEI capability.

    Default ``lei`` is the compact uppercase 20-character form.
    ``urn`` renders ``urn:lei:<compact>`` (lowercase scheme per the
    namespace page's ``urn:LEI:`` display, re-entering via the
    carrier branch) via ``LEICapability.format_value`` — the only
    presentation seam.

    Formats (ADR-0011 classes): ``urn`` — same-entity expansion
    (carrier is naming-only; validation runs on the stripped
    compact form, so the rendering re-enters exactly).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "lei"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"urn"})

    capability_name: str = field(default="lei", init=False)
    # No grammar-toggle flags for the initial single-grammar design.
    # If issued-membership gating is later added:
    # include_issued_validation: bool = False

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For LEI there is one always-active grammar,
    # so the property is omitted - base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string; `OFFERED_OUTPUT_FORMATS` excludes the default. For LEI, `lei` (compact) is the machine canonical form (concatenated-file form); `urn` is the IANA-registered naming wrapper.
- Inherited presentation field is resolved by `CapabilityContract.__post_init__` via the shared resolver — `None`, `"default"`, and the default string resolve identically; only `urn` triggers `format_value()`; anything else raises `ContractError`.
- `create_contract()` opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) plus the shipped `suppress_common_words: bool = False` flag (present in every shipped factory, e.g. `paxman/capabilities/ISIN/capability.py:53`), then capability-specific params (initially none).

**Presentational-only invariant (hard rule — ARCHITECTURE.md The Formatting Seam):**

- The presentation choice is a **representation transform, never a recognition or validation signal**. Rules never read it; `normalize()` always returns compact; the engine calls `Capability.format_value(value, output_format, notation)` after `normalize()` and before candidate dedup/status.
- `AMBIGUOUS` semantics are preserved across formats.
- Formatting adds **no provenance**.

For LEI, the offered formats:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"lei"` (default) | `5493000IBP32UQZ0KL24` | Compact, no spaces, uppercase — concatenated-file form, DB key |
| `"urn"` | `urn:lei:5493000IBP32UQZ0KL24` | IANA-registered naming wrapper, lowercase scheme; re-enters via the carrier branch |

*Do not add `grouped`: no 4/5-char grouping convention is attested (spacing in the wild is noise, not display). Do not add status-suffixed formats (lapsed/active are liveness, not presentation).*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.LEI.notation import LEINotation


class LEICapability(Capability[LEINotation]):
    name = "lei"  # lowercase identifier - what users pass to registry

    def get_grammars(self) -> list[Grammar[LEINotation]]:
        return [LEIRecognitionGrammar()]  # single grammar; one length, one meaning

    def get_rules(self) -> list[Rule[LEINotation]]:
        return [
            Section4LEIStructureMOD9710(),
            SectionLOUPrefixMembership(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: "Sequence[str] | None" = None,
        pinned_rules: "Sequence[str] | None" = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: "Sequence[str] | None" = None,
        suppress_common_words: bool = False,
    ) -> LEIContract:
        return LEIContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
            suppress_common_words=suppress_common_words,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: LEINotation
    ) -> str:
        if output_format == "urn":
            # IANA-registered naming wrapper - same-entity expansion,
            # re-enters via the carrier branch (ADR-0010 fixed-point).
            return f"urn:lei:{value}"
        return value  # lei default is identity - normalize() returns compact
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`): scaffolder adds the `LEI` import + `__all__` entry to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(LEI())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation — Three Levels

### 7.1 Level 1 Generic structure + MOD 97-10, Level 2 LOU lookup, Level 3 issued membership (deferred)

**Level 1 (always-active PARSER, ISO 17442-1):** length exactly 20, charset `^[A-Z0-9]{18}[0-9]{2}$`, decomposition consistency, whole-string MOD 97-10:

```python
def _expand(compact: str) -> str:
    """Expand each character to its numeric value (digits stay, A=10 ... Z=35)."""
    parts: list[str] = []
    for ch in compact:
        if "0" <= ch <= "9":
            parts.append(ch)
        else:
            parts.append(str(ord(ch) - 55))
    return "".join(parts)


def _mod97_10_valid(compact: str) -> bool:
    """Validate a 20-char LEI with ISO/IEC 7064 MOD 97-10 (no rearrangement)."""
    remainder = 0
    for digit in _expand(compact):
        remainder = (remainder * 10 + int(digit)) % 97
    return remainder == 1
```

Letter-expansion table (`A=10 … Z=35`): `A10 B11 C12 D13 E14 F15 G16 H17 I18 J19 K20 L21 M22 N23 O24 P25 Q26 R27 S28 T29 U30 V31 W32 X33 Y34 Z35` — identical to IBAN's table, opposite application point (whole string, no move-first-4-to-end).

Worked validation (`213800KUD8LAJWSQ9D15`, verified locally 2026-09-22): expand → `213800203013821101932282691315` (letters in order: K=20 U=30 D=13 L=21 A=10 J=19 W=32 S=28 Q=26 D=13) → iterative mod97 → `1` → valid. Mutation `…KUD8LX…` (X=33 for D=13) → remainder `55` → rejected. Generation direction (McZen): `check = 98 − mod97(first18 + "00")`, e.g. `213800D1L3R2MWV39G` → `88`, and the completed string validates to `1`.

**Level 2 (always-active LOOKUP_TABLE, GLEIF prefix list):** `lou_prefix in ACCREDITED_LOU_PREFIXES` plus the full Level-1 conjunction (ISIN one-directional-corroboration precedent). Retired blocks stay listed forever (append-only).

**Level 3 (deferred, gated LOOKUP_TABLE):** exact-string membership in the GLEIF data pool snapshot — deferred per §5.4 (size, churn, liveness≠validity).

### 7.2 What makes LEI "valid" vs "lou-valid" vs "issued/live"
- valid (generic) — correct length/charset/checksum, always-active PARSER (a never-assigned-LOU fabrication with a lucky checksum passes this level alone).
- lou-valid — generic plus LOU prefix in the accredited snapshot, always-active LOOKUP_TABLE (the v1 SUCCESS boundary).
- issued/live — actually present in the GLEIF data pool with a registration status, deferred gated rule (determinism-by-snapshot; renewal status never affects Levels 1–2).

Like ISIN valid vs prefix-attested, ISSN valid vs issued, IBAN valid vs country-valid: relational properties need tables, pure transforms do not.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase | SUCCESS → compact | grammar folds upper |
| 2 | Single-space separated | SUCCESS (same compact) | presentation noise, fixed-count strip |
| 3 | Label present (`LEI:`/`lei-`) | SUCCESS, span includes label | fused pattern, notation label-free |
| 4 | URN carrier (`urn:lei:`) | SUCCESS, span includes carrier | fused carrier branch, notation carrier-free |
| 5 | Double space / tab inside | MISSING | single-space discipline (IBAN-paper precedent) |
| 6 | Hyphen separated | MISSING (v1) | deferred to community extension (§2.1) |
| 7 | Over-long (21) / under-long (19) | MISSING | length guard, never 19/21 |
| 8 | Checksum-broken substitution | INVALID | rule rejects (mod97 ≠ 1) |
| 9 | Transposed adjacent pair | INVALID (nearly always) | MOD 97-10 detects nearly all single transpositions |
| 10 | Unknown LOU prefix, checksum valid | INVALID | LOU LOOKUP rejects (membership gate) |
| 11 | Retired-LOU prefix, checksum valid | SUCCESS | snapshot never removes (codes survive transfer) |
| 12 | Non-`00` at positions 5–6, checksum valid | SUCCESS | informative only (`FZ` precedent) |
| 13 | Embedded in sentence | SUCCESS with span | word-boundary guards |
| 14 | Two distinct in one slice | AMBIGUOUS / MultipleMentionsError | segmentation intended |
| 15 | Sibling confusion (20-char IBAN-shaped) | per-capability resolution | positional + algorithm discrimination (§14) |
| 16 | Leading/trailing glue (`X…`, `…Y`) | MISSING | `(?<!\w)` / `(?!\w)` |
| 17 | Quoted/bracketed/CSV-wrapped | SUCCESS | inside punctuation |
| 18 | GLEIF-URL embedded | SUCCESS (LEI capability, v1) | recognized via word_only boundary — URL-path-embedded LEI carved at the `/`/`#` boundary (34, 54); URL capability composes on top — amended per oracle review 2026-09-22 |

---
## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid compact (structure + checksum + LOU) | SUCCESS → compact | single canonical via ISO + GLEIF authorities |
| Valid variant (case/spacing/label/URN) | SUCCESS (same compact) | wrapping-only dedup |
| Checksum-broken / bad charset / wrong length-class | INVALID or MISSING | `INVALID` when a 20-char shape is claimed but checksum/charset fails; `MISSING` when no 20-char shape exists (length guard) |
| Unknown LOU prefix, checksum valid | INVALID | membership claimed by LOU lookup rule |
| No 20-char runs | MISSING | no grammar recognized |
| Two distinct valid in one slice | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity, use segmentation |
| Retired-LOU prefix, checksum valid | SUCCESS | liveness is not validity |
| Issued-gated input (if `include_issued_validation` true and absent) | INVALID | authority feature gating (deferred rule) |
| Non-`00` at 5–6, checksum valid | SUCCESS | informative only |

---
## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)
```bash
uv run python tools/new_capability.py LEI --name lei \
  --authority "ISO" --spec-name "ISO 17442-1:2020" \
  --spec-url "https://www.iso.org/standard/78829.html" \
  --publication-year 2020 --default-format lei
```
> `--default-format lei` matters: the scaffolder's default is `canonical` (`tools/new_capability.py:451`), which would contradict §6.1's `DEFAULT_OUTPUT_FORMAT = "lei"` on the first generated contract.
Creates 13 files + one edit: `paxman/capabilities/LEI/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance. After scaffolding, add the second provenance file manually: `rules/gleif_lou_prefix_list_ed2026.py` (GLEIF registry) plus `rules/data/lou_prefixes.py` (append-only snapshot) — or fuse MOD-97-10 citation into the ISO file (IBAN precedent) and add only the LOU file.

### 10.2 Contract & grammar wiring
- `get_grammars()` returns `[LEIRecognitionGrammar()]`, `get_rules()` returns both rule instances; `active_grammars` omitted for initial design (base None).
- Each grammar carries `name = "lei_recognition"` and non-empty `semantics = "lei_recognition"`; both rules declare `target_semantics = frozenset({"lei_recognition"})`.
- Export alias follows the ISIN/IBAN pattern: `LEICapability as LEI` in `paxman/capabilities/__init__.py`; registry name `"lei"`; CLI `paxman lei`; README/CONTEXT tables gain the LEI row; `paxman/api/bootstrap.py:_SHIPPED` gains `LEI` (alphabetical, between `Language` and `MacAddress`).

### 10.3 Cross-cutting invariants (fail review if violated)
- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports (import only from `paxman.core`, import-linter enforced) — copy the ~10-line `_mod97` accumulator; do not import IBAN's.
- No presentation-field token in any `paxman/capabilities/*/rules/` module (source-scan) — `normalize()` returns compact; `format_value()` owns `urn`.
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts.
- Deterministic by construction: same input + contract + library snapshot → same output. No network (GLEIF API is evidence infrastructure, never a runtime dependency).

---
## 11. Recommended File Layout (mirrors ISIN and IBAN)

```
paxman/capabilities/LEI/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── lei_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_17442_1_ed2020.py
    ├── gleif_lou_prefix_list_ed2026.py  # LOU LOOKUP_TABLE (always-active)
    └── data/                             # only if registry layer adopted (it is)
        └── lou_prefixes.py               # append-only frozenset snapshot
```

Per-registry data module shape (parallel to ISIN `rules/data/country_codes.py`):
```python
# rules/data/lou_prefixes.py
# Append-only: prefixes are never removed (LEI codes survive LOU
# retirement and transfer). Refresh: re-census GLEIF accredited-LOU
# directory + concatenated files, add new prefixes, never delete.
ACCREDITED_LOU_PREFIXES: frozenset[str] = frozenset({...})
```

LOU snapshot seeding (plan-agent task, not this report): derive the seed set from the GLEIF accredited-LOU directory plus a concatenated-file prefix census at build time; observed-in-verified-vectors prefixes (`2138`, `5493`, `5067`, `7LTW`) must be present. Do not hand-invent prefixes. Refresh procedure mirrors `tools/regenerate_iban_registry_data.py` (snapshot + `--check` drift gate) if the table grows large enough to warrant a generator; otherwise maintain in place with a consistency test asserting every snapshot prefix is exercised.

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISIN §9)

- Grammar tests: valid compact / lowercase / single-spaced / `LEI:`-labeled / `urn:lei:`-carried inputs, multiple matches, incompatible format (19/21-char, hyphenated, double-spaced, glued-label), empty, span invariants (`raw_text == text[start:end]`, label/carrier included in span), name/semantics, boundary-guard negatives — plus one positive vector per §2.1 RECOGNIZE form (compact/spaced/labeled/URN/lowercase).
- Rule tests: ISO structural rule valid/variant/invalid (incl. `7LTWFZYICNSX8D621K86` non-`00` acceptance pin + stdnum invalid `213800KUD8LXJWSQ9D15` rejection pin), normalize exact compact, provenance attributes, name/strategy conventions, decomposition-consistency rejection; LOU LOOKUP rule valid membership / unknown-prefix rejection / checksum-broken-with-valid-prefix rejection (one-directional-corroboration pin), strategy LOOKUP_TABLE, kind registry.
- Capability tests: notation frozen/hashable/slots, wiring counts (1 grammar, 2 rules), grammar/rule name conventions, `format_value` round-trips (`urn` re-enters via carrier branch; compact re-enters identically), `create_contract` factories.
- Integration: MISSING/INVALID/SUCCESS/AMBIGUOUS or MultipleMentionsError, year temporal filtering (`year=2019` filters the 2020 ISO rule → vacuity behavior per ADR-0012), `_clean_registry` fixture, determinism/VersionStamp, span-bearing match, dedup (spaced + compact + labeled inputs coalesce to one SUCCESS).
- Property tests (hypothesis): generate valid by picking LOU prefix from snapshot + random 14-char block + computed check digits → must canonicalize to itself; random 20-char strings → INVALID with high probability (≈96/97 checksum + LOU miss); spaced vs compact identical; `format_value` round-trip for `urn`.
- Consistency test: every shipped semantics covered by `Rule.target_semantics`; every snapshot LOU prefix exercised by at least one vector; no `00`-at-5-6 assumption anywhere (grep pin).
- Presentation purity: `output_format` source scan over `rules/` (existing gate covers the new files automatically).
- Real vectors: `213800KUD8LAJWSQ9D15` (stdnum), `5493000IBP32UQZ0KL24` + `213800WSGIIZCXF1P572` (Wikipedia), `506700GE1G29325QX363` (GLEIF), `7LTWFZYICNSX8D621K86` (GLEIF URN page, non-`00` pin), `213800KUD8LXJWSQ9D15` (INVALID checksum pin), 19/21-char MISSING pins, `LEI:`/`urn:lei:` carrier pins.

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `lei` vs `urn` | `lei` compact default, `urn` offered | concatenated-file form is the wire canonical; URN is a same-entity expansion (ORCID `uri` precedent) |
| 2 | Single grammar vs N grammars | Single `lei_recognition` initially; hyphen form deferred to community `extra_grammars` with coalesced semantics | fixed length 20 has no variants to split; avoids cross-grammar containment spurious AMBIGUOUS |
| 3 | LOU-prefix lenience vs strict | Ship LOU LOOKUP_TABLE as always-active (append-only snapshot) | small table, high value (never-assigned-prefix fabrications), slow accreditation cadence bounds staleness; mirrors ISIN prefix allowlist |
| 4 | Grammar length strictness | Exactly 20 alphanum via fixed-count interleave, never 19/21 | keeps grammar cheap and definitive; hyphen/double-space stay MISSING |
| 5 | Case/space normalization in grammar vs rule | Grammar folds case and strips single spaces; rules validate upper alphanum only | syntax not semantics (ISIN precedent) |
| 6 | Positions 5–6 content | Informative only, never reject | `FZ` in GLEIF-attested valid LEI; enforcement would fabricate a constraint |
| 7 | Single PUBLICATION vs split | Fuse MOD-97-10 citation into the ISO 17442-1 file (IBAN precedent); LOU registry always separate | fused keeps `get_rules` small; registry/specification kinds must not share a file |
| 8 | `single_value` for batch | True initially, segmentation for multi; offer `extra_grammars` variant with False | consistent with ISIN/IBAN/ORCID precedent |
| 9 | Hyphen tolerance | DEFER to community extension (tracked in https://github.com/nexusnv/paxman-python/issues/183) | single-validator evidence (stdnum strip), no official grouping attested; shipping it risks text absorption |
| 10 | Label/carrier span inclusion | Include label/carrier in `raw_text` span (fused regex), notation compact-only | mirrors ISIN/ORCID/IBAN label handling |
| 11 | Which alternative written forms does v1 recognize (GLEIF-URL-embedded, hyphen-grouped)? | RECOGNIZE every form attested by the spec/schema or ≥2 validators (compact/spaced/labeled/URN/lowercase) plus URL-path-embedded (word_only, ISIN precedent); DEFER hyphen via `extra_grammars`, citing §2.1. URL-embedded half resolved 2026-09-22 — RECOGNIZED (oracle review finding 2); hyphen half remains DEFER per row 9 (https://github.com/nexusnv/paxman-python/issues/183); liveness tracked in https://github.com/nexusnv/paxman-python/issues/184 | unhandled common forms are permanent MISSING blind spots; URL-embedded extraction is URL-capability composition, hyphen lacks a grouping convention |

---
## 14. Ambiguity Analysis (Paxman-specific)

- No inherent LEI-vs-LEI positional ambiguity — fixed 20-char structure with trailing check eliminates the Date-style multi-parse problem; two distinct LEIs in one slice is authorial choice (counterparty lists), and segmentation is the intended path (`single_value=True`, `MultipleMentionsError` on distinct values).
- LEI vs 20-char IBAN-shaped input is not lexical ambiguity but dual-validity: a 20-char run satisfying both LEI whole-string-mod97 and IBAN `CCDD`+per-country-length+rearranged-mod97 is genuinely both-shaped. Paxman resolves one capability per call, so no cross-capability dedup exists — each capability reports its own verdict honestly. The IBAN rule's rearranged checksum vs LEI's plain checksum makes dual-satisfaction cryptographically rare (≈1/97² for random strings); when it occurs, both SUCCESS values are authority-backed and the caller disambiguates by domain.
- LOU-membership failure is not ambiguity — checksum-valid but unknown-prefix input is `INVALID` with the LOU rule's attribution, not a competing value; without the LOU rule it would be false `SUCCESS` (the exact failure the two-rule design prevents).
- Spaced vs compact vs labeled vs URN is not ambiguity — four wrappings, one `compact` identity, deduped to a single candidate value before status determination.
- Staleness is not ambiguity — determinism-by-snapshot: a brand-new LOU prefix resolves `INVALID` until the snapshot refreshes, with the version pinned in `Provenance.version` (`Rolling`). The refresh procedure (§11) plus the never-remove policy bound this to new-LOU lag only.
- Renewal/lapse status is not validity — a lapsed-renewal LEI still checksums and still names its entity (code unchanged on renewal/transfer); status-gated rejection would confuse liveness with identity and is deferred with the issued-membership rule (§5.4).

---
## 15. URL Reference (authoritative, fetched 2026-09-22)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 17442-1:2020 (Ed.1 Part 1, current, Published, confirmed 2026-01-21) | https://www.iso.org/standard/78829.html | primary |
| ISO 17442-2:2020 (Ed.1 Part 2, current, Published, X.509 embedding) | https://www.iso.org/standard/79917.html | primary |
| ISO 17442:2019 (2nd ed., Withdrawn, revised by Parts 1+2) | https://www.iso.org/standard/75998.html | primary |
| ISO 17442:2012 (1st ed., Withdrawn) | https://www.iso.org/standard/59771.html | primary |
| ISO/IEC 7064:2003 (Ed.1, MOD 97-10, pure systems) | https://www.iso.org/standard/31531.html | primary |
| GLEIF introducing-LEI (20-char code, 4 principles, G20/FSB/ROC, example `506700GE1G29325QX363`) | https://www.gleif.org/en/about-lei/introducing-the-legal-entity-identifier-lei | primary |
| GLEIF LEI namespace (`URN:LEI:` format, `urn:LEI:7LTWFZYICNSX8D621K86`, IANA rationale) | https://www.gleif.org/en/lei-data/lei-namespace | primary |
| GLEIF API (Golden-Copy-backed, production fall 2020, mapping data) | https://www.gleif.org/en/lei-data/gleif-api | primary |
| GLEIF LEI search (free search, ownership, BIC/ISIN mapping, code lists) | https://www.gleif.org/en/lei-data/lei-search/about-lei-search | primary |
| GLEIF concatenated files (daily, XML/ZIP, free, challenge facility) | https://www.gleif.org/en/lei-data/gleif-concatenated-file/about-the-concatenated-file | primary |
| IANA URN namespaces (formal `lei` → GLEIF) | https://www.iana.org/assignments/urn-namespaces/urn-namespaces.xhtml | primary |
| python-stdnum `lei.py` (`clean ' -'`, `mod_97_10.validate`, `is_valid`, docstring vectors) | https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/lei.py | primary |
| McZen LEI-Validator (20/charset/4-14-2/MOD-97-10/generation `…39G` → `88`) | https://github.com/McZen-Technologies/LEI-Validator | primary |
| validator.js negative evidence: no `isLEI` module in `src/lib` (searched 2026-09-22) | https://github.com/validatorjs/validator.js/tree/master/src/lib | primary |
| LEI structure/history/validity/vectors (secondary) | https://en.wikipedia.org/wiki/Legal_Entity_Identifier | secondary |
| MOD 97-10 online checker consensus (secondary) | https://validatefin.com/en/tools/lei (via web search 2026-09-22) | secondary |
| Three-level validation consensus (secondary) | https://www.p9dt.com/knowledge-base/point-nine-legal-entity-identifier-lei-validator-lookup/ (via web search 2026-09-22) | secondary |
| Checksum-over-regex consensus (secondary) | https://nanoutil.com/validators/lei (via web search 2026-09-22) | secondary |
| ISIN research precedent | docs/development/research/2026-08-24-isin-canonicalization.md | primary |
| IBAN research precedent | docs/development/research/2026-08-22-iban-canonicalization.md | primary |
| BIC research precedent | docs/development/research/2026-08-23-bic-canonicalization.md | primary |
| ISSN research precedent | docs/development/research/2026-08-21-issn-canonicalization.md | primary |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary |
| Paxman shipped precedent (ISIN grammar/rules/contract) | paxman/capabilities/ISIN/grammar/isin_recognition.py, paxman/capabilities/ISIN/rules/iso_6166_ed2021.py, paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py, paxman/capabilities/ISIN/notation.py, paxman/capabilities/ISIN/contract.py, paxman/capabilities/ISIN/capability.py | primary |
| Paxman shipped precedent (IBAN grammar/rules) | paxman/capabilities/IBAN/grammar/iban_recognition.py, paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py, paxman/capabilities/IBAN/notation.py, paxman/capabilities/IBAN/contract.py | primary |
| Paxman shipped precedent (ORCID grammar/rules) | paxman/capabilities/ORCID/grammar/orcid_recognition.py, paxman/capabilities/ORCID/rules/iso_27729_ed2024.py | primary |
| Paxman engine (dedup/affinity/single-value) | paxman/engine/orchestrator.py:131-152,456,543,621-673,811 | primary |
| Paxman domain (Rule/Grammar enforcement) | paxman/core/domain.py:19-300 | primary |
| MILESTONE LEI row (**row 6**, not a separate #18 row; its "no check digit" claim is contradicted by §5.1/§7.1 — flagged for correction, see §5.1 check-digit bullet) | docs/development/MILESTONE.md | planning aid |

---
## 16. Evidence Completion — Resolved

This report's LEI-specific authoritative evidence has been fetched and cited (2026-09-22):
- [x] ISO catalogue entries: ISO 17442-1:2020 + ISO 17442-2:2020 (both Ed.1, current, Published, confirmed 2026-01) superseding ISO 17442:2019 plus 2012 lineage; TC 68/SC 8; ICS 03.060; version lifecycle publication_year 2020; citation anchored to assignment clause
- [x] RA/operator and data-pool provenance: GLEIF (operator), ROC (oversight), LOUs (issuers), concatenated files (daily XML/ZIP) + Golden Copy/API + LEI search; authority, specification_name, kind registry, reference_url, version Rolling, lifecycle active
- [x] Structure: exactly 20, `[A-Z0-9]{18}[0-9]{2}`, LOU 1–4 / entity 5–18 / check 19–20, 5–6 non-constraint proved by GLEIF-attested vector
- [x] Checksum algorithm proved positive (MOD 97-10 whole-string, letter table, generation + validation directions, worked examples verified locally)
- [x] LOU nuance: no country code by design; prefix allowlist design with never-remove policy; observed prefixes stated without LOU-name attribution
- [x] Ecosystem regex consensus: stdnum + McZen + folk 18+2 + three secondary validators + validator.js negative evidence
- [x] Recognition-surface inventory complete (§2.1): every attested written form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form
- [x] Wild input shapes validated (§2.2, 18 categories) against spec + GLEIF pages + dumps + validators
- [x] Label scope decision (fused `LEI`, glued reject)
- [x] URN-carrier equivalence decision (offered `urn`, same-entity expansion)
- [x] Positions-5–6 semantics decision (informative only)
- [x] Issued/liveness scope decision (deferred, §5.4)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISIN, IBAN, ORCID and Phone Capabilities Teach LEI (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

**1. Grammar strips, rule validates, capability formats.** ISIN's `notation_fn` strips spaces and uppercases (`paxman/capabilities/ISIN/grammar/isin_recognition.py:37-46`) while `Section4IsinStructureCheckDigit.matches` re-checks length, charset, decomposition, and checksum independently (`paxman/capabilities/ISIN/rules/iso_6166_ed2021.py:73-87`); `ISINCapability.format_value` renders `grouped` presentation-only (`paxman/capabilities/ISIN/capability.py:81-96`). LEI copies this three-way split exactly.

**2. One file per provenance, one class per section.** ISIN splits ISO 6166:2021 (specification, PARSER) from ANNA Guidelines (policy, LOOKUP_TABLE) with independent `PUBLICATION` constants and full-conjunction validation in both (`paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py:57-92`); ORCID documents why partial validators are forbidden (`paxman/capabilities/ORCID/rules/iso_27729_ed2024.py:1-7`). LEI's ISO PARSER + GLEIF LOOKUP pair follows both.

**3. Checksum helpers are copied, never imported.** ISIN duplicates `_expand`/`_luhn_valid` across its two rule files; IBAN's `_mod97` rearranges-then-accumulates piece-wise (`paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py:50-62`). LEI's whole-string accumulator is a third copy with no rearrangement — the no-cross-capability-imports rule leaves no alternative.

**4. Single grammar with fixed-count tolerance avoids spurious AMBIGUOUS; labels fuse with glued-reject.** ISIN's single grammar with `(?: ?…)` interleave and glued-label guard (`paxman/capabilities/ISIN/grammar/isin_recognition.py:20-34`), IBAN's LabelMatcher with `glued_policy="reject"` (`paxman/capabilities/IBAN/grammar/iban_recognition.py:76-84`), ORCID's fused label+host+guard (`paxman/capabilities/ORCID/grammar/orcid_recognition.py:22-35`) compose directly into the proposed LEI pattern (§4.2). Engine semantics — `_dedup_spans` longer-wins per grammar, `_validate_affinity` fail-fast, `single_value` invariant, `(value, recognition_rule, validation_rule)` candidate dedup (`paxman/engine/orchestrator.py:131-152,456,543,621-673,811`) — need no changes for LEI.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for LEI. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the deeper ISIN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
