# ISSN Canonicalization Research — paxman-python

**Date:** 2026-08-21
**Scope:** Primary-source survey of the ISSN standard (ISO 3297), the ISSN Register / ISSN-L linking mechanism, ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `ISSN` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org), ISSN International Centre (issn.org / portal.issn.org), IANA URN registration, ISSN Manual (May 2025), RFC 3044, and shipped Paxman capabilities (ISBN, Country, Phone, Date) as architectural precedents. Repo state: `feature/CURRENCY-capability` @ `7a4017c` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISBN research precedent [`docs/development/research/2026-08-05-isbn-canonicalization.md`](../research/2026-08-05-isbn-canonicalization.md).

**Revision — 2026-08-22 (Oracle review `docs/development/research/2026-08-22-iban-canonicalization.md`):** Verification pass against shipped `paxman/capabilities/ISSN/grammar/issn_recognition.py:11-16`. **§4.2** corrected from `BoundaryGuard.isbn10_lead().lookbehind` to shipped `BoundaryGuard.word_only().lookbehind + BoundaryGuard.digit().lookahead + r"\b"` (see §4.2 and §4.4); this strengthens the report's earlier `word_only` recommendation per Oracle P2. **Appendix** confirmed no `IBAN`-label copy-paste typo (ISSN report unaffected; IBAN report Appendix line 822 typo `ISSN strips "IBAN" label` → `ISSN strips "ISSN" label` applies to the IBAN report only). Other IBAN-review P1s (registry Release 99 vs 100 URL mismatch, SC vector, 31-vs-32 max length, NO structure, Wikipedia misattribution, date/RA precisions) were audited and have **no analogue** in this ISSN report — ISSN provenance URLs/versions remain self-consistent and ISSN has fixed 8-char length.

---

## Executive Summary

ISSN is a strong fit for a Paxman capability: it has an unambiguous canonical form (`XXXX-XXXX`, 8 chars with hyphen after the fourth), a single authoritative standard (**ISO 3297:2022**, 7th ed., current) with a deterministic **mod-11 weights 8→2** check-digit algorithm, a maintained registry (**ISSN Register / ISSN Portal** at `portal.issn.org`) managed by the **ISSN International Centre (CIEPS, Paris)** as ISO Registration Authority, and a well-understood human-readable presentation (hyphen for readability, `ISSN` label when presented). The domain is narrower than ISBN or Country, but the same grammar/rule/provenance separation that makes Paxman valuable for ISBN applies directly — recognizing the tolerant human surface, validating strictly against the authority, and returning a canonical value with full provenance.

Key findings that shape the design:

1. **Canonical form is `XXXX-XXXX` with hyphen** (machine-readable presentation also hyphenated per ISSN Manual §4; prefix `ISSN` and space are presentation-only when rendered for human perception). This maps onto Paxman's presentational-only `output_format` invariant: `format_value()` renders `hyphenated` (default) vs `compact` (`XXXXXXXX` without hyphen) vs `urn` (`urn:issn:XXXX-XXXX`) without touching validity.

2. **One lexical length (8 chars), one grammar suffices.** Unlike ISBN's two lengths (10 legacy + 13 current), ISSN has a single 8-char shape (final char may be `X`=10). A single `ISSNRecognitionGrammar` with Regex (structural pattern matching) strategy is the correct choice (HOW_TO_ADD_NEW_GRAMMAR.md §1; HOW_TO_ADD_NEW_CAPABILITY.md Step 4 — Lexicon is for finite vocabularies like Country names).

3. **Check digit is the definitive structural validation** — weights `8,7,6,5,4,3,2` over the first 7 digits, `check = (11 - S mod 11) mod 11`, `10→X`, `11→0`. Case folding `x→X` is syntax (grammar), `X`=10 is semantics (rule). No registrant-range or prefix lookup is structurally required (contrast ISBN's GS1 `978`/`979` and Range Message registrant ranges). An optional `LOOKUP_TABLE` registry rule for issued-ness behind `requires_features` mirrors ISBN's `include_range_validation=False` pattern but is safely deferred.

4. **ISSN-L (Linking ISSN) and ISSN-H (History ISSN) are relational, not lexical.** ISSN-L (`ISSN-L XXXX-XXXX`, Cluster ISSN per ISO 3297:2020 §3.4.4) collates medium-specific ISSNs sharing one `ISSN-L` (the first-assigned in the ISSN Register); ISSN-H groups successive title history (to be implemented 2024). Both are out-of-scope for an initial capability's single-string validation — they require a Register lookup, not a string transform.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION`: `Provenance` constant, one `Rule` class per section): `ISO 3297:2022` (active, current) owns structure + check digit; `RFC 3044` (IETF, 2001-01, informational) + IANA `urn:issn` registration owns the URN lexical equivalence (`x→X`, hyphen optional in URN NSS, `urn:ISSN:` prefix case-insensitive); `ISSN Manual` (May 2025) implements assignment/display detail. The Register (`portal.issn.org`) is an optional `kind="registry"` authority.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need ISSN canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Librarians / cataloguers** | Normalize `ISSN 1234-5679` vs `12345679` vs `urn:issn:1234-5679` to one form for deduplication and MARC field `022$a` validation (legacy `022 $l` → now `023 $a` with indicator 0 for ISSN-L) | ILS, OCLC WorldCat, library discovery layers |
| **Publisher / platform engineers** | Validate user-supplied ISSN at ingest; link print/electronic variants via ISSN-L (portal.issn.org) | Manuscript submission systems, Crossref, DOAJ, repository harvesters |
| **Bibliographic data engineers** | Extract and canonicalize ISSNs from free-text references, PDFs, or scraped HTML with span-bearing provenance | Citation parsers, OpenAlex / CrossRef pipelines, LLM extraction post-processing |
| **Knowledge-graph / search teams** | Use ISSN as a stable serial-work key (journal-level identifier) alongside ISBN (monograph-level) | Scholarly knowledge graphs, journal matching, holdings checks |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many ISSN mentions) and a contract; Paxman returns one canonical ISSN (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ISBN (`isbn13` bare digits) and Email (`user@example.com`) ergonomics.

---

## 2. Shape of Input (Human Surface)

### 2.1 Wild variants — enumerated from spec, ISSN.org, MARC 022/023, bibliography corpora (CrossRef/PubMed/DOAJ) and real validators

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical display** | `ISSN 1234-5679` | Spec mandates `ISSN` + space + `XXXX-XXXX` when presented for human perception (ISSN Manual §2). `paxman` must recognize both with and without label; `format_value()` decides presentation. |
| 2 | **Bare hyphenated** | `1234-5679`, `0378-5955` (Nature) | Most DB field value. MARC 022 `$a` stores with hyphen, without `ISSN` prefix. |
| 3 | **Bare compact** | `12345679`, `0317847X` | IsValid API explicitly accepts `03785955` (no hyphen). `validatte` regex `^\d{4}-?\d{3}[\dX]$` allows optional hyphen. Must be recognized. |
| 4 | **Label with colon/space/hyphens** | `ISSN: 1234-5679`, `ISSN:1234-5679`, `ISSN - 1234-5679`, `issn 1234-5679` | Catalog exports (`ERIC.js` does `replace(/ISSN-/,"")`). ISSN.org resolver example shows `URN:ISSN:1234-1231` case-mixing → prefix handling must be case-insensitive, colon/space/hyphen tolerant. |
| 5 | **URN** | `urn:issn:1234-5679`, `URN:ISSN:1234-5679`, `urn:ISSN:0317-8471`, `https://urn.issn.org/urn:issn:2639-5983` | IANA `urn:issn` namespace (RFC 3044 → draft-ietf-urnbis-rfc3044bis, rev. 2017-06-22). Syntax: `urn:issn:xxxx-xxxx` hyphen required in URN NSS but SHOULD-tolerant; namespace token case-insensitive in practice (`UrN:IsSn:` examples). Often embedded in RDF/DC `urn:issn:` (Sigil, bibtex-ruby). |
| 6 | **ISSN-L / ISSN-H labelled** | `ISSN-L 0264-2875`, `ISSN-H 1365-201X` | Labels denote Cluster ISSNs (linking vs history). Lexically identical 8 chars; semantic distinction only. Grammar may optionally tolerate `ISSN(?:-L|-H)?` prefix. |
| 7 | **Whitespace variants** | ` ISSN 1234-5679 `, `1234 - 5679`, `1234 5679` | Postgres `isn` strips `['-',' ']` (`Utils::luhnWithWeights(..., ['-',' '])`). Users paste with spaces around hyphen. |
| 8 | **Unicode dash tolerance** | `1234–5679` (en-dash U+2013), `1234—5679` (em-dash) | Zotero `utilities.js#L595` `cleanISSN` strips `[\x2D\xAD\u2010-\u2015\u2043\u2212]` (hyphen-minus through U+2015, minus sign). Real copy-paste hits these. **Decision: recognize hyphen-minus only in grammar; normalize exotic dashes in a rule or reject — but document.** |
| 9 | **Check-digit `X` case** | `0378-5955`, `0317-847X`, `0317-847x`, `0000-0019` | Last char may be `X` (value 10 in MOD-11). Canonical is uppercase `X`. `validatte` has `case_sensitive` flag; IsValid always returns uppercase. Must accept `x`/`X`, emit `X`. |
| 10 | **Label + paren qualifier** | `ISSN 1562-6865 (Online)`, `ISSN 1063-7710 (Print)` | ISSN.org example for multiple media. Free-text extraction must emit one span per ISSN, not swallow `(Online)`. |
| 11 | **Multiple per line** | `ISSN 0264-2875 (print) / ISSN 1750-0095 (online)`, `p-ISSN 1234-5679, e-ISSN 1234-5687`, `issn = {0162-8822, 2160-9292, 1939-3539}` (BibTeX) | Serials on 2-3 media each have own ISSN + one linking `ISSN-L` (e.g. `ISSN-L 0264-2875` groups `0264-2875`+`1750-0095`). E.g. `ISSN-L 1188-1534` etc. Free-text → 2 matches, not one. |

**Real-world regex / validation snippets (GitHub evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| `Savory/validatte` `behaviors/common/isISSN.ts` | `const issn = '^\d{4}-?\d{3}[\dX]$'` with `require_hyphen` & `case_sensitive` flags; then MOD-11 |
| `AndyBRoswell/cs-first-aid` `CSL_data.ts` | `^(?:ISSN\s)?(\d{4})-(\d{3}[\dX])$/i` + weighted sum `8→2`, `11-rem`, `10→X` |
| `zotero/utilities` `utilities.js#L595` | `issnStr.toUpperCase().replace(/[\x2D\xAD\u2010-\u2015\u2043\u2212]+/g,'')` → strip all Unicode hyphens before check |
| `zotero/utilities` `cleanISSN()` | `if (!/^\d{7}[\dX]$/) return false; sum 8→2, check %11==0` |
| `symfony/symfony` `IssnValidator.php` (3.4) | Removes hyphen at `[4]` only, `length==8`, `ctype_digit(substr 0,7)`, last `digit\|x\|X`, checksum `sum %11==0` |
| `ronanguilloux/IsoCodes` `Issn.php` | `Utils::luhnWithWeights(issn, 8, [8,7,6,5,4,3,2], 11, ['-',' '])` |
| `postgres/postgres` `contrib/isn/isn--1.1.sql` | `issn_in(cstring)` → C `issn_in`, exposes `issn`/`issn13` (EAN-13 for ISSN) types |

**Normalization contract (reuse ISBN pattern):**
```python
# IsValid / Zotero pattern — strip spaces/hyphens, upper, then MOD-11
digits = re.sub(r"[-\s]", "", raw).upper()  # → 8 chars: \d{7}[\dX]
```

### 2.2 What input is NOT an ISSN mention

- ISBN-13 / ISBN-10 digit runs (longer, different length, different check algorithm) — length + prefix + check-digit split disambiguates.
- ISSN-L / ISSN-H are structurally identical to an ISSN (8 chars, mod-11) — they are roles, not shapes, so lexical disambiguation is impossible. Disambiguation is semantic (see §5.3).
- Bare 8-digit runs that are not `MISSING` vs `INVALID` boundary (see §9 Resolution map).

### 2.3 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md — segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct ISSNs (e.g. print + electronic) that normalize to different values is `AMBIGUOUS` in the single-slice semantics; the caller-owned segmentation path (split → canonicalize each slice) is the intended multi-entity pattern. Identical ISSN mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — single shape

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISSNNotation:
    """ISSN notation — grammar-normalized digit string.

    ``digits`` is the 8-character string, hyphen/space stripped, uppercased
    (``x`` → ``X``). The grammar never computes or validates the check digit;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md §4).
    """

    digits: str  # e.g. "12345679" or "1234567X" — always length 8 after grammar
```

**Considered alternative — shape discriminator:** ISBN uses `shape: Literal["isbn10", "isbn13"]` because two lexical lengths map to distinct notations that later converge on one canonical 13-digit value. ISSN has one lexical length (8), so a discriminator is unnecessary. If the future `ISSN-L` linking semantics becomes a second notation meaning (same lexical shape, different provenance), a `Literal["issn", "issn-l"]` discriminator or a second semantics id is a possible extension — but for an initial capability a single `digits` field suffices. This keeps the notation isomorphic to ISBN's per-grammar sanitized string and satisfies `Grammar[ISSNNotation].recognize()` → `Rule[ISSNNotation].matches()` typing.

**Invariants the grammar enforces (before rules):**
- Exactly 8 characters after stripping separators.
- Only `[0-9Xx]`; `X`/`x` allowed only as final character (validated strictly by rules; grammar may permit eagerly and let rules reject — ISBN-10 precedent).
- `raw_text` preserves original span (hyphenated, labelled, or bare); `digits` is the syntax-normalized token.

### 3.2 Why not carry hyphen in the notation

Hyphens have **no lexical significance** for validity (ISSN Manual §4 / ISBN precedent ISO 2108 §4.1: hyphens are readability). In ISSN's machine-readable presentation the hyphen should be included (some applications expect it), but it does not affect identity. The grammar strips separators for `digits`; presentation is `Capability.format_value()` only. Every candidate with the same 8 chars has the same identity regardless of input hyphens — dedup and status logic operate on the normalized `digits`.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md §1 and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape — delimiters, fixed widths, character classes) or **Lexicon** (finite vocabulary — Country names, Currency words). ISSN has a distinctive fixed-width shape (`8` chars, hyphen after 4th, optional `ISSN` label), so **Regex** is the correct strategy. No lexicon table is involved.

### 4.2 Reference pattern (adapted from ISBN verbatim precedent)

ISBN-13 precedent (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py`):
```python
_ISBN13_PATTERN = r"\b(?:ISBN(?:-13)?[\s:-]+)?(?=((?:\d[ -]?){12}\d)(?![\d]))\1\b"
```
ISBN-10 (`paxman/capabilities/ISBN/grammar/isbn10_recognition.py`):
```python
_ISBN10_PATTERN = (
    BoundaryGuard.isbn10_lead().lookbehind
    + r"(?:ISBN(?:-10)?[\s:-]+)?(?=((?:\d[ -]?){9}[0-9Xx])(?![\d]))\1\b"
)
```

**Proposed ISSN pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope string pattern — compiled by RegexStage (never inside recognize())
# Per paxman/capabilities/ISBN/grammar/isbn13_recognition.py:17 — ship as str, not re.compile().pattern
_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]*)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN: str = (
    BoundaryGuard.word_only().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.digit().lookahead
    + r"\b"
)
# word_only = r"(?<!\w)" — blocks letter/digit/underscore-glued `a1234-5679` (stronger than
# isbn10_lead `(?<!\d)(?<!\d[ -])` which only blocks digit-glued and "1 12345679" glue);
# trailing (?!\d) via BoundaryGuard.digit().lookahead plus \b blocks prefix of 9-digit runs
# (shipped `paxman/capabilities/ISSN/grammar/issn_recognition.py:11-16` — Oracle 2026-08-22
# notes this strengthens the report's earlier word_only recommendation; cite shipped).
# Note: hyphen tolerance is intentionally narrow here (`-?` at canonical position 4);
# tolerant "1234 - 5679" / "1234 5679" are documented in §2.1 row 7 but normalized at a higher
# layer or rejected as MISSING — see edge #4/§13#5 for the contradiction resolution.


def _issn_notation(match: re.Match[str]) -> ISSNNotation:
    raw_body = match.group("body")
    digits = "".join(ch for ch in raw_body if ch in "0123456789Xx").upper()
    return ISSNNotation(digits=digits)


class ISSNRecognitionGrammar(PipelineGrammar[ISSNNotation]):
    """ISSN recognition — 8-char identifier with optional label/hyphen tolerance."""

    name = "issn_recognition"
    semantics = "issn_recognition"
    single_value = True
    pre = StandardPre[ISSNNotation](empty_guard=True)
    regex = RegexStage[ISSNNotation](
        pattern=_ISSN_PATTERN, notation_fn=_issn_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs ISBN:*
- Ship as module-scope **string** pattern; `RegexStage` compiles in `paxman/core/grammar/stages.py:72` (mirrors ISBN's `_ISBN13_PATTERN = r"..."`). Do not double-compile via `re.compile(...).pattern`.
- Strip in `notation_fn` via `join(... in "0123456789Xx")` + `.upper()` (ISBN-10 precedent `x→X`).
- Leading `BoundaryGuard.word_only()` (`(?<!\w)`) blocks letter/digit/underscore-glued `a1234-5679` — strictly stronger than `isbn10_lead` (`(?<!\d)(?<!\d[ -])` which only blocks digit-glued and `"1 12345679"` glue) and matches shipped `issn_recognition.py:12`; trailing `BoundaryGuard.digit().lookahead` (`(?!\d)`) plus `\b` keeps from claiming a prefix of `123456790` (9 digits). Solitary `(?<!\d)` alone would leak `a1234-5679`.
- **Hyphen scope:** `-?` at the canonical hyphen position only (narrow). Tolerant variants `1234 - 5679` / `1234 5679` (§2.1 row 7) are either pre-normalized via a `Pre` stage or treated as `MISSING` — the tolerant `[\s-]?` per digit (ISBN-style) is deliberately not used because ISSN's hyphen is fixed at position 4. Update edge #4 / §13#5 to match the chosen strictness.
- Uses `PipelineGrammar` + `StandardPre` + `RegexStage` because that is the staged pipeline ISBN actually ships (HOW_TO_ADD_NEW_GRAMMAR.md's bare-`Grammar` recipe is the minimal teaching form; shipped grammars use `PipelineGrammar`).

**URN variant — combine or separate?**

The ISBN precedent fuses the optional `ISBN` label via `(?:ISBN...)?` into a single regex with lookahead/backreference (`(?=((?:\d[ -]?){12}\d)...\1`). For ISSN, the `urn:issn:` prefix is a second syntax (`urn:issn:XXXX-XXXX`, hyphen required but `SHOULD`-tolerant per IANA, prefix case-insensitive). Options:

- **(Recommended) Fuse into one regex** with an `(?:urn:issn:[\s]*)?` alternative preceding the `ISSN` label alternative — single grammar, minimal containment complexity (`_dedup_spans` no-op within one grammar).
- **Alternative:** Second grammar `urn_issn_recognition` with coalesced `semantics = "issn_recognition"` (HOW_TO_ADD_NEW_GRAMMAR.md §4 option A — reuse shipped semantics id so existing `ISO 3297` rule validates both without edit). Only introduce if the `urn:` scheme arguably belongs to URL capability (`absolute-uri`) and warrant a distinct `semantics`.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md §"Recognition Pipeline Contract")

- Grammar emits **span-bearing** `RecognitionMatch[ISSNNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))` — span is the regex slice. Stages must not mutate `text` (`PipelineState` scratch only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups — two grammars agreeing on the same span are both preserved for ambiguity observation. For ISSN (single shipped grammar initially), this dedup is inert but structurally present.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

### 4.4 Guard boundaries against sibling grammars / ISBN

ISSN vs ISBN length discrimination is the main sibling guard: ISSN `8` chars vs ISBN-10 `10` vs ISBN-13 `13` — no natural span equality. A trailing `(?!\d)` + `\b` (via `BoundaryGuard.digit().lookahead` + `\b` as shipped) keeps an ISSN from matching as a prefix of an ISBN-13 run (`1234567901234`). Prefix-aware ISBN detection (`ISBN` label) does not clash with `ISSN` label; case-insensitive `ISSN` vs `ISBN` substrings are distinct. For a 13-digit EAN run `9771234567000` (ISSN-as-EAN) an ISSN grammar must not claim an inner 8-char window — the `(?<!\w)` front guard (`BoundaryGuard.word_only().lookbehind` as shipped) blocks `97712345...` from yielding `7123-4567`.

Concrete engine check (`orchestrator:_dedup_spans`):
```python
ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
# longer wins within SAME grammar; across grammars never deduped
```

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md §1, ARCHITECTURE.md §"Community Extensions")

The new grammar declares a non-empty `semantics` string; every validating `Rule` declares `target_semantics: frozenset[str]` naming the semantics ids it validates. The engine's `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. For a single shipped ISSN grammar, the natural ids are:

- `semantics = "issn_recognition"` (identity id), or
- a coalesced domain id such as `"issn_identifier"` if future communities add URN/variant grammars that share the same meaning.

Recommendation: start with identity `issn_recognition`; coalesce only when a second grammar (e.g. `urn_issn_recognition`) is actually added — coalescing is option A in HOW_TO_ADD_NEW_GRAMMAR.md §4.

### 4.6 `single_value` — one mention per call vs citation mining

Shipped capabilities (ISBN, Country, Money, Phone) all set `single_value=True` — consistent with Paxman's "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). Bibliographic records legitimately list 2 ISSNs (print + electronic, e.g. `ISSN 0264-2875 (print) / ISSN 1750-0095 (online)`; BibTeX `issn = {0162-8822, 2160-9292, 1939-3539}`), so citation mining will want free-text extraction of multiple mentions.

Recommendation: **initial `single_value=True`** (matches shipped precedent and the single-ISSN field use-case), with a documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A separate free-text community grammar with `single_value=False` can be offered via `extra_grammars` for citation-mining callers when needed.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO** — International Organization for Standardization, Technical Committee **ISO/TC 46/SC 9** (Information & documentation — Identification and description) |
| **Registration Authority (RA)** | **ISSN International Centre (CIEPS)** — Centre International d'Enregistrement des Publications en Série, Paris, designated by ISO via Registration Authority Agreement (Oct 2018) for ISO 3297 + ISO 4. Intergovernmental organisation under UNESCO/France statutes. |
| **Spec name** | `ISO 3297 — Information and documentation — International Standard Serial Number (ISSN)` |
| **Current edition** | **ISO 3297:2022 (7th ed., published 2022-06)** — current, `60.60 Published` at `https://www.iso.org/standard/84536.html`. Withdraws ISO 3297:2020 (published 2020-10-01, withdrawn 2022-07-01). Previous stable: ISO 3297:2007 (superseded). Note: no 2017 edition exists — `2020` was the edition before `2022`. |
| **Related specs** | `RFC 3044` — *Using The ISSN as URN within an ISSN-URN Namespace* (IETF, Informational, 2001-01; updated by `draft-ietf-urnbis-rfc3044bis-issn-urn-01`, IANA `urn:issn` formal rev. 2017-06-22). `ISSN Manual` (May 2025, `Manual-ISSN_ENG-marc21_May2025.pdf`) — practical implementation of ISO 3297 by ISSN International Centre. MARC 21 `022` (ISSN) + `023` (Cluster ISSN) — Library of Congress. |

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|
| ISSN International Centre (ISO RA) | `ISO 3297:2022` | `2022-06` (7th ed., current) | `https://www.iso.org/standard/84536.html` | `active` — supersedes 2020 | `2022` |
| ISSN International Centre (ISO RA) | `ISO 3297:2020` | `2020-10` (6th ed.) | `https://www.iso.org/standard/73846.html` | `withdrawn` 2022-07-01 | `2020` |
| ISSN International Centre (ISO RA) | `ISO 3297:2007` | `2007` (5th ed.) | `https://www.issn.org/understanding-the-issn/standardization/` | `superseded` | `2007` |
| IETF (ISSN-IC registrant) | `RFC 3044 — Using The ISSN as URN` | `2001-01` | `https://www.rfc-editor.org/rfc/rfc3044.html` + IANA formal `https://www.iana.org/assignments/urn-formal/issn` | `active` | `2001` |
| ISSN International Centre | `ISSN Manual` (implementation of ISO 3297) | `2025-05` | `https://www.issn.org/wp-content/uploads/2025/05/Manual-ISSN_ENG-marc21_May2025.pdf` | `active` | `2025` |

**ISSN structure (ISO 3297 §4, ISSN Manual §4, RFC 3044 §2.2, LOC MARC 022):**

```
NNNN-NNNC
```
- Length: **8 characters**, presented as two groups of 4 with hyphen `U+002D` between p4–p5 for readability.
- Charset: `U+0030..U+0039` (0–9) for p1–p7; p8 `C` = `0-9` or `X` (`U+0058`, uppercase, value 10).
- Formal regex: `^\d{4}-\d{3}[\dxX]$` canonical, `^\d{7}[\dxX]$` bare; PCRE: `[0-9]{4}-[0-9]{3}[0-9X]`.
- Opaque identifier — no meaning to be inferred about origin or contents.
- Examples: `0317-8471`, `1050-124X`, `0000-0019`, `1560-1560` (RFC 3044); `0264-2875` / `1750-0095` (Dance research linking example).

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_3297_ed2022.py` | `authority="ISSN International Centre"`, `specification_name="ISO 3297:2022"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/84536.html"`, `version="2022"`, `lifecycle="active"`, `publication_year=2022` | `Section 4-issn-check-digit` (structure + check digit) | 8-char form; mod-11 weighted 8..2; `X`=10; `normalize()` returns canonical hyphenated per `DEFAULT_OUTPUT_FORMAT` |
| `rules/rfc_3044_ed2001.py` *(optional — URN variant)* | `authority="IETF"`, `specification_name="RFC 3044"`, `kind="specification"`, `reference_url="https://www.rfc-editor.org/rfc/rfc3044.html"`, `version="2001"`, `lifecycle="active"`, `publication_year=2001` | `Section 2.2-issn-urn-lexical-equivalence` | URN `urn:issn:` prefix case-insensitive, hyphen optional in URN NSS, `x→X` translation, Q/R components omitted |
| `rules/issn_register_ed2025.py` *(optional — gated)* | `authority="ISSN International Centre"`, `specification_name="ISSN Register"`, `kind="registry"`, `reference_url="https://portal.issn.org/"`, `version="2025-05"`, `lifecycle="active"`, `publication_year=2025` | `Section *-issn-register-membership` (issued-ness) | Whether the 8 chars are allocated in the ISSN Register (data file in `rules/data/`); `requires_features={"include_register_validation"}` |

*This mirrors ISBN's three-authority split (ISO 2108 // ISBN Users' Manual // ISBN Range Message, each one `PUBLICATION` per file). For ISSN, only ISO 3297:2022 is mandatory; the URN and Register layers are optional, the latter gated via `requires_features`, exactly like ISBN's `Section 4-registrant-range` gated by `include_range_validation` / Country's `include_localized`.*

Each `Rule[ISSNNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`):

```python
class Section4CheckDigit(Rule[ISSNNotation]):
    name = "Section 4-issn-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (check digit)"
    target_semantics = frozenset({"issn_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISSNNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: ISSNNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO 3297:2022** lineage confirmed via `https://www.iso.org/standard/84536.html` (current, `60.60 Published`, allows grouping into clusters via separately-prefixed ISSN — enabling ISSN-L/ISSN-H) and `https://www.iso.org/standard/73846.html` (2020 withdrawn).
- **RA designation:** `https://www.issn.org/understanding-the-issn/standardization/` + `https://www.issn.org/iso-signs-two-registration-authority-agreements-with-the-issn-international-centre-october-2018/` + `https://www.issn.org/wp-content/uploads/2025/05/Manual-ISSN_ENG-marc21_May2025.pdf` p.1.
- **IANA URN registration:** `https://www.iana.org/assignments/urn-formal/issn` (rev. 2017-06-22, states based on ISO 3297:2007 + ISSN-L rules).
- **RFC 3044:** `https://www.rfc-editor.org/rfc/rfc3044.html`.

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical ISSN rule citing a withdrawn edition (e.g. ISO 3297:2020) would carry `lifecycle="withdrawn"` or `"superseded"` (cf. ISBN's `isbn_users_manual_ed2012` `superseded` lifecycle for ISBN-10). For ISSN, the initial rule is expected `active`.

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly (length 8, char classes, mod-11). Returns `False` for any invalid input, never raises — not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md §5b Step 7).
- **`normalize()`** — returns the **default canonical form** (hyphenated per `CapabilityContract.DEFAULT_OUTPUT_FORMAT`; see §6). Never reads `contract.output_format` — the CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation is the capability's `format_value()` seam only.
- **`RuleStrategy` choice:** ISBN precedent uses `PARSER` for check digits and `LOOKUP_TABLE` for registry prefixes/registrant ranges. For ISSN, the check-digit rule is `PARSER`; a registry-membership rule (if offered) is `LOOKUP_TABLE`.

### 5.4 ISSN-L (Linking ISSN) — scope decision

The ISSN International Centre defines **ISSN-L** (Linking ISSN, Cluster ISSN per ISO 3297:2020 §3.4.4): one designated ISSN per serial title that collates the work's medium-specific ISSNs (print, electronic, CD-ROM) for linking. ISSN-L is itself an ISSN (same 8-char shape, same mod-11), **chosen as the first ISSN assigned in the ISSN Register** to any medium version of the resource; it applies to all media versions even if single-medium publication still gets `ISSN-L == ISSN`. Example: Print `0264-2875` / Online `1750-0095` → `ISSN-L 0264-2875` (Dance research). Three-media example: `1188-1534` (print), `1911-1479` (online), `1911-1460` (CD-ROM) → `ISSN-L 1188-1534`.

**Newer sibling: ISSN-H** (History ISSN) — cluster for successive title history (predecessor/successor over time), **distinct** from member ISSNs (newly assigned, not reusing a member), introduced via ISO 3297:2020 allowance for clusters, to be implemented 2024 per LOC `023` proposal / ISSN Manual §7.1 (`ISSN-H XXXX-XXXX`).

**Recommendation for an initial ISSN capability:** treat ISSN-L/ISSN-H as **out of scope for recognition/validation** — they are **relational** properties (which ISSN is the linker for this work?) requiring the ISSN Register / ISSN Portal as a live table, not a deterministic string transform. Validating that a string *is* an ISSN vs that it *is the ISSN-L for this work* are different claims; the latter is a `LOOKUP_TABLE` over an incomplete embedded snapshot if attempted, with staleness concerns. The initial capability should canonicalize any ISSN (print or electronic) to its own canonical form, with provenance ISO 3297:2022 only. ISSN-L linking, if later desired, belongs behind an opt-in `include_issn_l_resolution` or as a second `output_format` (`"issn-l"`), gated and documented as lossy when the input is a medium-specific ISSN — mirroring Phone's lossy `national` documentation obligation (ARCHITECTURE.md §"The Formatting Seam").

Display: prefixed `ISSN-L` / `ISSN-H` + space + `NNNN-NNNC` (e.g. `ISSN-L 1188-1534`); in MARC, `022 $l` (legacy) → now `023 $a` with indicator 0 (ISSN-L).

### 5.5 Assignment / registration authority & Register

Network: **ISSN International Centre (CIEPS, Paris)** + **89 ISSN National Centres** + centres for international organisations. Blocks of ISSN allocated by International Centre to National Centres; the **ISSN Register** (central DB >2M records) is published via **ISSN Portal** at `https://portal.issn.org/` (subscriber API SRU + free partial access). Each record includes medium-specific ISSN + ISSN-L + key title + linking fields.

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman.core.capability_contract.py`) — never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base's `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ISSNContract(CapabilityContract):
    """User-facing contract for ISSN capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = (
        "hyphenated"  # cf. ISBN "isbn13" / Date "ISO"
    )
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact", "urn"})

    capability_name: str = field(default="issn", init=False)
    # No grammar-toggle flags for the initial single-grammar design.
    # If registry gating is later added:
    # include_register_validation: bool = False

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For ISSN there is one always-active grammar,
    # so the property is omitted — base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format` — `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order, then capability-specific params (if any).

**Presentational-only invariant (hard rule — ARCHITECTURE.md §"The Formatting Seam"):**

- `output_format` is a **representation transform, never a recognition/validation signal**. Rules never read it; `normalize()` always returns the default canonical form; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup / status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance** — `Candidate.provenance`, `recognition_rule`, `validation_rule` come from the validating rule.

For ISSN, the offered formats model the three canonical interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"hyphenated"` (default) | `1234-5679` / `0317-847X` | Human-readable / MARC-compatible interchange form (hyphen after 4th char; some applications expect it per ISSN Manual §4) |
| `"compact"` | `12345679` | Machine key form (no hyphen, useful for DB keys, ISSN-L table join, EAN merge) |
| `"urn"` | `urn:issn:1234-5679` | RDF/DC `isPartOf`, Europe PMC, resolver `https://urn.issn.org/urn:issn:XXXX-XXXX` (RFC 3044; namespace case-insensitive but canonical lowercase, hyphen preserved, `X` uppercase) |

*Do not add `with_label` format — the `ISSN` label is not part of the identifier; citation renderers add it.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.ISSN.notation import ISSNNotation


class ISSNCapability(Capability[ISSNNotation]):
    name = "issn"  # lowercase identifier — what users pass to registry

    def get_grammars(self) -> list[Grammar[ISSNNotation]]:
        return [ISSNRecognitionGrammar()]  # add URN grammar later if needed

    def get_rules(self) -> list[Rule[ISSNNotation]]:
        return [Section4CheckDigit()]  # plus optional RFC3044 / register rule

    @staticmethod
    def create_contract(
        *,
        excluded_rules: "Sequence[str] | None" = None,
        pinned_rules: "Sequence[str] | None" = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: "Sequence[str] | None" = None,
    ) -> ISSNContract:
        return ISSNContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: ISSNNotation
    ) -> str:
        if output_format == "compact":
            return value.replace("-", "")
        if output_format == "urn":
            return f"urn:issn:{value}"  # value is hyphenated; X already uppercase
        return (
            value  # hyphenated default is identity — normalize() must return XXXX-XXXX
        )
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`):
`scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(ISSN())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation — Check Digit, Authority, Provenance

### 7.1 Mod-11, weights 8→2 (ISO 3297 §4; LOC `loc.gov/issn/check.html`; python-stdnum)

The ISSN check digit is computed over the first 7 digits with weights 8, 7, 6, 5, 4, 3, 2:

```
S = Σ (digit_i × (8 - i))  for i = 0..6  — i.e. 8..2
check = (11 - (S mod 11)) mod 11
  if check == 10 → "X"
  if check == 11 → "0"  (i.e. S mod 11 == 0)
```

Verification: `(S + check_weighted) mod 11 == 0` when `X` = 10, equivalently `sum(d*weight for d in 8..1 where X=10) % 11 == 0`. This mirrors ISBN-10 (`10..2` over 9 digits), with a shorter weight window.

**Worked example — `0317-8471` (LOC `check.html`):**
- First 7 digits: `0 3 1 7 8 4 7`
- Weights:        `8 7 6 5 4 3 2`
- Products:       `0 21 6 35 32 12 14`
- Sum = 120; `120 mod 11 = 10`; `11 - 10 = 1` → check `1` → `0317-8471`.
- If remainder is 10 → substitute uppercase `X`; if no remainder → `0`.
- Compact alternative (python-stdnum): `check = (11 - sum((8-i)*int(n) for i,n in enumerate(number))) % 11; return 'X' if check==10 else str(check)`.

**Case handling of X:**
- Canonical: **uppercase `X` only** (`U+0058`). ISSN Manual, IANA, LOC, RFC 3044 all prescribe uppercase.
- Input tolerance: RFC 3044 / IANA / draft-urnbis state lexical equivalence: *"if 'x' is found it must be translated to X"* and hyphens dropped before comparison. For Paxman: accept `x`/`X` on input (grammar folds via `.upper()`), normalize to `X` on output.
- Only valid at position 8 and only when computed value is 10; regex alone insufficient — must validate via mod-11.

**RFC 3044 / IANA lexical equivalence (for URN):**
> Check digit `X` case-sensitive → translate `x`→`X`; hyphen between 4th/5th can be omitted; for URN `URN:ISSN:` prefix case-insensitive; Q/R components if present must be omitted; hyphen SHOULD be inserted if stored without.

### 7.2 What makes an ISSN "valid" vs "issued"

- **valid ISSN** — correct length (8), charset, and mod-11 per ISO 3297:2022.
- **issued ISSN** — actually allocated by the ISSN International Centre / national centre (ISSN Register membership).

Like ISBN's valid-vs-issued split (`isbnlib` valid vs Range Message allocated), ISSN should offer the strict check-digit validation always and the issued-ness check as an opt-in registry rule (§5.2). Embedding the Register as `rules/data/` would mirror ISBN's `rules/data/range_message.py` snapshot pattern — deterministic and replay-safe, with a documented refresh procedure and `MessageDate` in provenance.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Leading zeros significant : `0317-8471` vs `317-8471` | `03178471` distinct from `3178471` (→ `MISSING` vs canonical `0317-8471`) | ISSN is an 8-char string, not an integer; `0000-0019` is a valid ISSN (RFC 3044 example). |
| 2 | Lowercase `x` : `1234-567x` | `SUCCESS` → `1234-567X` (grammar folds, rule validates `X`=10) | Grammar's `notation_fn` `.upper()` — mirrors ISBN-10 `x→X`. Canonical always uppercase. |
| 3 | Invalid check digit: `0378-5954` (bad mod-11) vs valid `0378-5955` | `INVALID` (recognized, no authority validates) | `matches()` fails mod-11 — definitive structural failure. Test vector from `bootstrapValidator`: `0032-147X` invalid. |
| 4 | Wrong hyphen placement: `12-345679`, `123456-79` | `MISSING` (no ISSN grammar claims non-canonical hyphen) — tolerant variants `1234 - 5679` / `1234 5679` likewise `MISSING` unless a `Pre` normalizer is added | Strict grammar `-?` at canonical position only (Oracle fix 3); `§2.1` row 7 tolerant forms documented as human typos but intentionally not recognized — keeps recognition purely syntactic at the fixed position and lets a future `StandardPre` handle normalization if desired. Canonical hyphen is readability, but tolerant per-digit `[ -]?` would leak ISBN-style over-matching. |
| 5 | No hyphen at all: `12345679` | `SUCCESS` → `1234-5679` (`hyphenated` default) or `12345679` per `DEFAULT_OUTPUT_FORMAT` | Grammar hyphen-tolerant (`-?` at position 4); `normalize()` inserts hyphen at 4. |
| 6 | ISSN label present: `ISSN 1234-5679`, `ISSN: 1234-5679` | `SUCCESS`, span includes label+value; `raw_text == text[start:end]` | Optional `(?:ISSN(?:-L|-H)?[\s:-]*)?` prefix, `re.IGNORECASE`. |
| 7 | URN form: `urn:issn:1234-5679`, `URN:ISSN:1234-5679` | `SUCCESS` if URN grammar shipped (fused or second grammar with coalesced `semantics`); otherwise `MISSING` vs `INVALID` depending on pattern | Namespace case-insensitive, hyphen optional in NSS but SHOULD-be-included (IANA). `urn:` scheme prefix arguably belongs to URL capability's `absolute-uri` — recommend community extension if not fused. |
| 8 | ISSN embedded in citation: `Nature 1234-5679 (2024)` | `SUCCESS` with span; `raw_text="1234-5679"` | Free-text recognition — span-bearing match, not whole-string; `\b` before `(` ensures `0172-9926` prefix of BIBLID `0172-9926(1994)...` is extractable. |
| 9 | 7-digit or 9-digit runs: `1234-567`, `123456789` | `MISSING` (no ISSN grammar claims) or `INVALID` if a sub-run matches but check fails | Grammar length guard `\d{4}-?\d{3}[0-9Xx]` + `(?!\d)` prevents partial claims; digit-glued guard `(?<!\d)(?<!\d[ -])` prevents `912345679` → `1234-5679`. |
| 10 | Multiple distinct ISSNs in one slice: `1234-5679 / 8765-4321` | `AMBIGUOUS` (two candidates, different canonical values) — or `MultipleMentionsError` with `single_value=True`; segmentation recommended (`docs/recipes/segmentation.md`) | Caller-owned segmentation for multi-entity input. |
| 11 | ISSN vs ISBN confusion: `978-3-16-148410-0 ISSN 1234-5679` on same page | `MISSING` for ISSN on the 13-digit run; `SUCCESS` for ISBN | Length discrimination — ISSN 8 vs ISBN 13/10; EAN `9771234567000` (ISSN-as-EAN) must not yield an ISSN hit. |
| 12 | Leading `X` or mid-string `X`: `X234-5679`, `12X4-5679` | `INVALID` (recognized if grammar eager, rules reject; or `MISSING` if grammar filters) | `X` allowed only as final char; `matches()` enforces `isdigits(number[:-1])`. |
| 13 | Digit-glued runs: `912345679`, `ID: 0123456790` | `MISSING` (or `INVALID`) | Leading `(?<!\d)(?<!\d[ -])` keeps an 8-char run from being carved out of a longer ID. |
| 14 | ISSN-L as a value: `ISSN-L 1234-5679` | Treat as ISSN (same shape) — note that it *is* an ISSN chosen as linker, not a different lexical type | Linking is a registry lookup on which ISSN is linker for this title — not a grammar shape distinction. |
| 15 | Historical / reassigned ISSNs | Defer — like Country's `include_historical` (`BU`/`SU`), would be a registry `LOOKUP_TABLE` over time, gated by `year` if modelled | `year` filtering already structurally available via `Provenance.publication_year`. |
| 16 | Unicode dashes (en-dash/em-dash) pasted from PDFs | `MISSING` in grammar (hyphen-minus only), unless rule normalizes exotic dashes (`zotero` strips `[\x2D\xAD\u2010-\u2015\u2043\u2212]`) | Document decision: exotic dashes are syntax noise; either pre-normalize or reject and document. |

---

## 9. Resolution-State Map (ARCHITECTURE.md §"Resolution Semantics")

| Input | Status | Why |
|-------|--------|-----|
| Valid ISSN (check digit OK) : `1234-5679`, `12345679`, `ISSN 1234-5679`, `1234-567x`→`1234-567X` (e.g. `0378-5955`, `0317-8471`, `1050-124X`, `0000-0019`) | `SUCCESS` → `1234-5679` (`hyphenated` default) | Single canonical value via ISO 3297:2022 rule |
| Valid ISSN, alternative input hyphens / spaces | `SUCCESS` (same canonical) | Hyphens/spaces presentation-only; candidate dedup by value |
| Invalid check digit : `0378-5954` (should be `0378-5955`) | `INVALID` (recognized, no authority validates) | Definitive structural failure — mirrors ISBN `INVALID` |
| Bad characters / length: 7 or 9 chars | `MISSING` (no grammar) or `INVALID` (sub-run recognized but check fails) depending on grammar scope | Length-guarded grammar; rules reject |
| 8 chars with mid-string X | `INVALID` | Rule rejects non-final X |
| No 8-char digit runs in text | `MISSING` | No grammar recognized anything |
| Two distinct valid ISSNs in one slice (e.g. `0264-2875 / 1750-0095`) | `AMBIGUOUS` / `MultipleMentionsError` with `single_value=True` (different canonical values) | Single-slice ambiguity — use segmentation |
| `urn:issn:1234-5679` (if URN grammar not shipped) | `MISSING` vs `INVALID` depending on pattern | Scope decision — URN prefix claimed by URL capability or second ISSN grammar (§4.2) |
| Registry-gated input (if `include_register_validation=True` and ISSN not in Register) | `INVALID` when only the registry rule would validate | Authority feature gating — enabled yields `INVALID` rather than `MISSING`, like Country localized without `include_localized` |
| EAN `9771234567000` (ISSN-as-GTIN) | `MISSING` for ISSN | Not an ISSN lexical form — do not parse as ISSN |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (`tools/new_capability.py` — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py ISSN --name issn \
    --authority "ISSN International Centre" --spec-name "ISO 3297:2022" --spec-url "https://www.iso.org/standard/84536.html" \
    --publication-year 2022
```

Creates 13 files + one edit (per Step 0 checklist): `paxman/capabilities/ISSN/{notation,contract,capability,grammar/issn_recognition,rules/iso_3297_ed2022}` , tests stubs, and `paxman/capabilities/__init__.py` alphabetical wiring. The `TODO(scaffold)` markers then guide replacing the placeholder grammar pattern with the ISSN Regex (§4.2), renaming `Section 1-overview` to `Section 4-issn-check-digit`, shaping the notation beyond placeholder `value`, and adding `rules/data/` only if the registry layer is adopted.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[ISSNRecognitionGrammar()]` (append URN variant at the end if later added, maintaining deterministic `get_grammars()` order).
- `active_grammars` omitted for initial design (base `None` → runs every shipped grammar). Only introduce if recognition becomes feature-gated (Email/IP/ISBN pattern).
- Each grammar carries `name = "issn_recognition"` (snake_case `_recognition` suffix) and non-empty `semantics` — engine composes shipped + `extra_grammars` community extensions in order, failing fast on name collisions (`CapabilityError`) or dangling `target_semantics` (`ContractError`).

### 10.3 Cross-cutting invariants (fail review if violated)

- **No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source** — fix root cause or use scoped `per-file-ignores` (sanctioned in `pyproject.toml`).
- **No cross-capability imports** — import only from `paxman.core` (import-linter enforced).
- **No `output_format` token in any `paxman/capabilities/*/rules/` module** (code, comments, or docstrings) — source-scan `tests/unit/test_rule_output_format_purity.py` fails otherwise.
- `@dataclass(frozen=True, slots=True)` for domain objects / notation; `@dataclass(frozen=True)` **without** `slots` for contracts.
- Deterministic by construction: same input + contract + library snapshot (version + registry + rule-data tables) → same canonical output; no network, clock, or environment-dependent ordering.

---

## 11. Recommended File Layout (mirrors ISBN — §7 in ISBN research)

```
paxman/capabilities/ISSN/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── issn_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_3297_ed2022.py           # primary — structure + MOD-11
    ├── rfc_3044_ed2001.py           # optional — URN lexical equivalence
    └── data/                        # only if registry layer adopted
        └── issn_register.py         # ISSN Register snapshot (LOOKUP_TABLE)
```

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md §10 and ISBN §9)

- **Grammar tests** (`tests/capabilities/issn/test_grammar.py`): valid input, variants (separators, `ISSN`/`ISSN-L`/`ISSN-H` label, `x` vs `X`, `ISSN:` / `ISSN-` ), multiple matches, incompatible format (ISBN length), empty input; span invariants `len(raw_text) == end - start` and `raw_text == text[start:end]`; `name` / `semantics` checks; boundary guard negative tests (`912345679` not inside 9-digit ID).
- **Rule tests** (`test_rules.py`): per-rule `matches()` valid/variant/invalid, `normalize()` exact canonical output (hyphenated canonical, including `X` preservation), provenance attributes, name/strategy conventions, never read `output_format`; leading zeros `0000-0019` preserved.
- **Capability tests** (`test_capability.py`): notation frozen/hashable/`slots`; wiring counts (`get_grammars` / `get_rules`); grammar/rule name conventions; `format_value()` `hyphenated`↔`compact`↔`urn` round-trips; `create_contract` factories.
- **Integration** (`tests/integration/test_issn_capability.py`): `MISSING`/`INVALID`/`SUCCESS`/`AMBIGUOUS` (or `MultipleMentionsError`); `include_register_validation` gating; `year` temporal filtering; `_clean_registry` fixture; determinism / `VersionStamp`; span-bearing `RecognitionMatch` and `Candidate.span`.
- **Property tests (hypothesis):** generate valid ISSNs from mod-11 → canonicalize round-trips; random 8-char strings → `INVALID` with high probability; hyphenated vs bare → identical canonical value.
- **Consistency test (grammar/rule boundary):** every shipped recognition `semantics` is covered by at least one `Rule.target_semantics`; if registry data adopted, every shipped recognition key's data coverage tested separately. Keep grammar and rule data in separate files with a consistency test that asserts every shipped recognition key is covered by at least one rule-data mapping (if `LOOKUP_TABLE` over Register).
- **Presentation purity:** the `output_format` source scan already applies to any new `rules/` module (`tests/unit/test_rule_output_format_purity.py`).
- **Real ISSN vectors:** `0378-5955` (Hearing Research), `0028-0836` (Nature), `2041-1723` (Nature Communications), `0317-8471`, `0317-847X`-family `x` case, `0000-0019` (leading zeros), `1560-1560`, `urn:issn:0259-000X` (with/without hyphen, lowercase x); invalid `0378-5954`, `0032-147X`.

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | **`DEFAULT_OUTPUT_FORMAT`** — `hyphenated` vs `compact` | **`hyphenated` default, `compact` + `urn` offered** | ISBN precedent is `isbn13` bare; but ISSN's human-readable and machine-exchange form is hyphenated in MARC/catalogues (ISSN Manual §4: *"exchanged between systems with hyphen"*), and some consumers expect it. Either way the seam is presentational-only — decision is about defaults, not validity. |
| 2 | **Single grammar vs URN grammar** | **Single `issn_recognition` initially; defer `urn_issn_recognition` to community extension (`extra_grammars`) or fuse `urn:issn:` into the same regex** | Keeps initial surface minimal; URN parsing arguably belongs to URL capability's `absolute-uri` scope. A coalesced `semantics = "issn_recognition"` can unify them later (HOW_TO_ADD_NEW_GRAMMAR.md §4 option A, no rule edit). |
| 3 | **Registry / ISSN-L/H validation** | **Defer — ship only ISO 3297:2022 structural validation; add `ISSN Register` `LOOKUP_TABLE` rule behind `include_register_validation` + `rules/data/` snapshot when needed** | Mirrors ISBN `include_range_validation=False` default (`valid` vs `issued` split). ISSN lacks a public range-message equivalent as machine-readable as ISBN's — staleness risk higher; linking requires live portal lookup. |
| 4 | **`X` normalization in grammar vs rule** | **Grammar folds `x→X` in `notation_fn` (syntax-level case folding, like ISBN-10), rules validate final-char-only** | Case folding is syntax, not semantics (HOW_TO_ADD_NEW_CAPABILITY.md §4.2); mapping canonical display `X` is rule-owned — but folding case is grammar-owned. |
| 5 | **Hyphen strictness** | **Strict in grammar (`-?` at canonical position 4), canonical in `normalize()`/`format_value()`** — tolerant `1234 - 5679` / `1234 5679` are `MISSING` unless a `Pre` normalizer is added | Oracle fix 3: strict prevents per-digit `[ -]?` over-matching (ISSN hyphen is fixed, unlike ISBN's every-digit tolerance); `normalize()`/`format_value()` still enforces `XXXX-XXXX`. Tolerant variants documented in §2.1 row 7 as human typos intentionally not recognized. |
| 6 | **`single_value` for free-text mining** | **`True` initially (shipped precedent); document segmentation recipe for multi-ISSN records; offer `extra_grammars` free-text variant with `False` if needed** | Consistent with Money/Country/ISBN; `MultipleMentionsError` is the correct signal for `0264-2875 / 1750-0095` in one slice. |
| 7 | **Unicode dash handling** | **Grammar handles `U+002D` hyphen-minus only; exotic dashes (`\xAD`, U+2010–2015, U+2212) normalize in a Pre stage or document as unsupported** | `zotero` strips broader set — but Paxman's staged `StandardPre` could host Unicode dash normalization if desired; keep minimal for v1. |

---

## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent ISSN-vs-ISSN ambiguity.** Like ISBN, ISSNs are unique by design; the mod-11 check digit eliminates the positional ambiguity Date exhibits (`DD/MM` vs `MM/DD`). Two distinct ISSNs in one slice are an authorial choice (print + electronic), not a parsing ambiguity — segmentation is the intended path.
- **ISSN vs ISSN-L/H is not lexical ambiguity** — all are 8-char ISSNs; distinguishing the linker/history cluster is a registry lookup, not a string rewrite.
- **Hyphenation is never an ambiguity signal.** Differently-hyphenated forms of the same digits are the same canonical value; formatting must not affect status.
- **URN prefix is a routing question**, not an ISSN ambiguity: `urn:issn:...` arguably resolves through URL's `absolute-uri` grammar rather than ISSN's; if fused, it is a coalesced semantics, not a competing value.
- **ISBN vs ISSN length discrimination** prevents cross-capability ambiguity — `977` EAN prefix for ISSN-as-GTIN (`9771234567000`) is not an ISSN hit.

---

## 15. URL Reference (authoritative, fetched 2026-08-21)

| Claim | URL |
|-------|-----|
| ISO 3297:2022 (current, 7th ed., `60.60 Published`) | <https://www.iso.org/standard/84536.html> |
| ISO 3297:2020 (6th ed., withdrawn 2022-07-01) | <https://www.iso.org/standard/73846.html> |
| ISO/TC 46/SC 9 & ISSN RA designation / standardization lineage | <https://www.issn.org/understanding-the-issn/standardization/> |
| What is an ISSN? (structure, scope, opaque identifier) | <https://www.issn.org/understanding-the-issn/what-is-an-issn/> |
| ISSN Manual (May 2025, implementation of ISO 3297) | <https://www.issn.org/wp-content/uploads/2025/05/Manual-ISSN_ENG-marc21_May2025.pdf> |
| MOD-11 calculation (LOC/NSDP, worked example `0317-8471`) | <https://www.loc.gov/issn/check.html> |
| IANA URN formal `issn` (rev. 2017-06-22, states ISO 3297:2007 + ISSN-L rules) | <https://www.iana.org/assignments/urn-formal/issn> |
| RFC 3044 — *Using The ISSN as URN* (RFC 3044) | <https://www.rfc-editor.org/rfc/rfc3044.html> |
| draft-ietf-urnbis-rfc3044bis (URN-bis update) | <https://datatracker.ietf.org/doc/html/draft-ietf-urnbis-rfc3044bis-issn-urn-01> |
| ISSN-L assignment rules (1/2/3 media, ISSN-L = first-assigned) | <https://www.issn.org/understanding-the-issn/assignment-rules/the-issn-l-for-publications-on-multiple-media/> |
| ISSN Register / ISSN Portal (central DB >2M records, SRU API) | <https://portal.issn.org/> |
| ISSN Network & National Centres (89 centres) | <https://www.issn.org/the-centre-and-the-network/our-mission/the-international-centre-for-the-registration-of-serial-publications-cieps/> |
| MARC 21 Format: 022 (ISSN) | <https://www.loc.gov/marc/bibliographic/bd022.html> |
| MARC 21 Format: 023 (Cluster ISSN — ISSN-L/H) | <https://www.loc.gov/marc/bibliographic/bd023.html> |
| ISBN research precedent (provenance/file-layout model) | [`docs/development/research/2026-08-05-isbn-canonicalization.md`](../research/2026-08-05-isbn-canonicalization.md) |
| Paxman scaffolder & conventions | [`HOW_TO_ADD_NEW_CAPABILITY.md`](../../HOW_TO_ADD_NEW_CAPABILITY.md), [`HOW_TO_ADD_NEW_GRAMMAR.md`](../../HOW_TO_ADD_NEW_GRAMMAR.md), [`ARCHITECTURE.md`](../../ARCHITECTURE.md) |
| Paxman shipped ISSN-adjacent precedent (valid vs issued, check-digit `X`, hyphen handling) | `paxman/capabilities/ISBN/rules/` — `iso_2108_ed2017`, `isbn_users_manual_ed2012`, `isbn_range_message_ed2026` + `paxman/capabilities/ISBN/grammar/` |
| Ecosystem validator evidence (all fetched via GitHub) | `Savory/validatte` `behaviors/common/isISSN.ts`, `zotero/utilities` `utilities.js#L595` `cleanISSN`, `symfony/symfony` `IssnValidator.php`, `ronanguilloux/IsoCodes` `Issn.php`, `postgres/postgres` `contrib/isn/isn--1.1.sql` |
| python-stdnum ISSN (compact MOD-11 reference impl) | <https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/issn.py> |

---

## 16. Evidence Completion — Resolved

This report's ISSN-specific authoritative evidence has been fetched and cited (2026-08-21):

- [x] ISO catalogue entry: **ISO 3297:2022 (7th ed., 2022-06, current, `60.60 Published`)** superseding **ISO 3297:2020 (withdrawn 2022-07-01)** superseding ISO 3297:2007; TC 46/SC 9; RA ISSN International Centre via Oct 2018 RA Agreement; URL `https://www.iso.org/standard/84536.html`; `version="2022"` `lifecycle="active"` `publication_year=2022`; `citation` anchored to ISO 3297 §4.
- [x] ISSN hyphen display rule: ISSN Manual §4 — *"when presented for human perception, be preceded by prefix ISSN + space and hyphen"*; machine exchange hyphen should be included (some apps expect it); hyphen has no semantic value for identity.
- [x] ISSN mod-11 weighted **8..2** algorithm (LOC `0317-8471` worked example); `X`=10 semantics; case equivalence `x→X` per RFC 3044 / IANA lexical equivalence.
- [x] ISSN-L definition (ISO 3297:2020 §3.4.4, Cluster ISSN; first-assigned in Register; single-medium `ISSN-L == ISSN`; multi-medium one shared ISSN-L; ISSN-H for history, to be implemented 2024); table lookup — not derivable offline.
- [x] ISSN Register / portal provenance: `authority="ISSN International Centre"` `kind="registry"` `reference_url="https://portal.issn.org/"`; network 89 National Centres + CIEPS Paris.
- [x] Wild input shapes validated (§2.1) against ISSN Manual / RFC 3044 / ISSN.org resolver / MARC 022/023 / validators (validatte, zotero, symfony, postgres) and adjusted grammar label pattern to `ISSN(?:-L|-H)?` + `urn:issn:` alternative.
- [x] `urn:ISSN` scope decision (§4.2 / §8 edge 7 / §13 decision 2): `urn:issn` namespace case-insensitive, hyphen optional in NSS but SHOULD-be-included; prefix arguably belongs to URL's `absolute-uri` — fused regex or community `extra_grammars`; coalesced semantics viable.
- [x] **2026-08-22 Oracle alignment:** Shipped `paxman/capabilities/ISSN/grammar/issn_recognition.py:11-16` verified to use `BoundaryGuard.word_only().lookbehind + BoundaryGuard.digit().lookahead + r"\b"` (not `isbn10_lead`). Report §4.2/§4.4 updated to match; `word_only` strengthens the earlier recommendation per Oracle P2. ISBN-vs-ISSN sibling-guard discussion updated to `(?<!\w)`. Appendix typo audit: ISSN report has no `IBAN`-label copy-paste error (that typo was in the IBAN report Appendix line 822 only). IBAN-review P1/P2 items (release 99-vs-100 URL/version mismatch, SC/NO/LC/NI vectors, Wikipedia misattribution, RA/year precisions) audited — no analogue in ISSN (fixed 8-char, ISO catalogue URLs version-pinned, provenance rows self-consistent).

File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN Capability Teaches ISSN (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the ISSN proposal to what Paxman already ships.

Refer to `paxman/capabilities/ISBN/` — see deep-dive summary in §4.2 / §5 / §6 above and the librarian-verified notation/grammar/rule excerpts. The three architectural lessons for ISSN:

1. **Grammar strips, rule validates, capability formats.** ISBN grammars compile at module scope, `RegexStage` → `re.finditer()` → strip `[ -]` and label → bare-digit notation; rules enforce prefix + mod-10/mod-11 (`PARSER` + `LOOKUP_TABLE`); `format_value("hyphenated")` reintroduces Range Message hyphenation via `EAN_PREFIX_RULES`/`GROUP_RULES` longest-match. ISSN mirrors this exact split — grammar tolerant (label/ hyphen/space/ `x` case) → `ISSNNotation(digits)`; rule `PARSER` mod-11 weights 8..2; formatter `hyphenated`/`compact`/`urn` is a trivial slice (`value.replace("-", "")` / `f"urn:issn:{value}"`).

2. **One file per provenance, one class per section.** ISBN ships `iso_2108_ed2017` (PARSER check-digit + LOOKUP_TABLE for GS1 prefix), `isbn_users_manual_ed2012` (PARSER mod-11, `X`=10, `lifecycle superseded`), `isbn_range_message_ed2026` (`LOOKUP_TABLE` registrant ranges, `requires_features={"include_range_validation"}`). ISSN's mandatory file is `iso_3297_ed2022` with `PARSER` check-digit (`lifecycle active`); any registry layer is a second file `issn_register_ed2025` gated by `requires_features={"include_register_validation"}`.

3. **No `output_format` in rules, ever.** CI scan `tests/unit/test_rule_output_format_purity.py` rejects the token in `paxman/capabilities/*/rules/` (code, comments, docstrings). `normalize()` returns the default canonical form (`hyphenated`); `format_value` renders `compact`/`urn`. This presentational-only invariant is non-negotiable for ISSN as well.

---

*Report saved per request to `docs/development/reports/` (this directory) and cross-references the ISBN research precedent in `docs/development/research/`. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*
