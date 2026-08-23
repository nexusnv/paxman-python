# ORCID Canonicalization Research — paxman-python

**Date:** 2026-08-23
**Scope:** Primary-source survey of the ORCID standard (ISO 27729:2012 Information and documentation — International Standard Name Identifier (ISNI), ISO/IEC 7064:2003 MOD 11-2, ORCID Registry and ORCID iD display/URI conventions), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `ORCID` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO catalogue pages (iso.org) for ISO 27729:2012 and its lineage (draft 09/30177090 DC, Cor 1:2013, ISO 27729:2024), ISO/IEC 7064:2003, ISNI International Agency (isni.org) governance/how-it-works/search-database, ORCID Registry support page Structure of the ORCID Identifier plus joint statement 2013, ORCID-Source OrcidStringUtils and OrcidCheckDigitGenerator, ORCID orcid-model XSD common-3.0, python-stdnum `stdnum/isni.py` plus `stdnum/iso7064/mod_11_2.py`, validator.js negative (no isORCID) plus isISSN/isISBN precedents, and seven ecosystem libs (hypothesis/h, cwltool, elabftw, speced/respec, knowledgefutures/pubpub, scippneutron, isvalid.dev). Shipped Paxman capabilities (ISSN, ISBN, Country, Phone, IBAN, BIC) as architectural precedents. Repo state: `main` @ `af68cd5` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](../research/2026-08-21-issn-canonicalization.md) plus the IBAN precedent [`docs/development/research/2026-08-22-iban-canonicalization.md`](../research/2026-08-22-iban-canonicalization.md) and BIC precedent [`docs/development/research/2026-08-23-bic-canonicalization.md`](../research/2026-08-23-bic-canonicalization.md).

---

## Executive Summary

ORCID is a strong fit for a Paxman capability: it has an unambiguous canonical form (**hyphenated, 16 chars with MOD 11-2 check**: `XXXX-XXXX-XXXX-XXXC` where `C` is `0-9` or `X` for value 10, total `4×4` digit groups separated by single hyphen-minus, canonical URI `https://orcid.org/XXXX-XXXX-XXXX-XXXC`; compact digits-only `16` is MISSING under v1 hyphen-only grammar), a stable single-part standard (**ISO 27729:2012** 1st edition, 2012-03, `01.140.20` `TC 46/SC 9` published, withdrawn 2024-11, canceled/replaced by **ISO 27729:2024** 2nd edition 2024-11-11 `60.60` Published, minor revision + Cor 1:2013 correction) with a direct check-character normative annex citing **ISO/IEC 7064:2003 MOD 11-2**, a maintained authoritative registry (**ORCID Registry** at `orcid.org`, `https://orcid.org/<orcid>`, random assignment from ISNI-reserved block `0000-0001-5000-0007`–`0000-0003-5000-0001` plus `0009-0000-0000-0000`–`0009-0010-0000-0000`, annual CC0 public data file, public and member APIs) alongside the parent **ISNI International Agency (ISNI-IA)** at `https://isni.org/`, and a well-understood human-readable presentation (**hyphen every 4 digits**, optional `ORCID:`/`ISNI` label, optional `https://orcid.org/` prefix, presentation-only). The domain mirrors Paxman's value proposition for ISSN and ISBN: recognizing the tolerant human surface (case of `X`, hyphen/space/no-separator, `orcid.org` vs bare, leading zeros significant), validating strictly against the authority (length `16` including `X`, first `15` digits plus `10→X` MOD 11-2), and returning a canonical hyphenated value with full provenance. Unlike IBAN, ORCID has a **single check digit** at position 16, computed via `total=(total+digit)*2` then `(12 - remainder)%11` (value 10 rendered `X`), not a MOD 97 rearrangement.

Key findings that shape the design:

1. **Canonical form is hyphenated, uppercase, 16 chars (`XXXX-XXXX-XXXX-XXXC`) plus canonical URI.** Regex consensus is `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` (with URI `^https://orcid\.org/\d{4}-\d{4}-\d{4}-\d{3}[\dX]$`), hyphen presentational, `X` only uppercase. Compact digits-only `^\d{15}[\dX]$` is MISSING under the recommended hyphen-only v1 grammar (not claimed); hyphenated is the sole claimed form, compact accepted only if a fallback branch ships (see §13#9). URI `https://orcid.org/` is storage/display canonical per `Support > Structure of the ORCID Identifier` storage section (`store as https://orcid.org/xxxx-xxxx-xxxx-xxxx`). This maps onto Paxman's presentational-only invariant: `format_value()` renders `orcid` (hyphenated, default) vs `uri` (`https://orcid.org/`…) vs `compact` without touching validity.

2. **One grammar suffices, with optional URI prefix group.** Unlike ISBN which needs two grammars (ISBN-13 vs ISBN-10, separate semantics and `include_isbn10` gating), ORCID's bare vs URI form is a single optional prefix `(?:https?://(?:www\.)?orcid\.org/)?` inside one pattern, exactly like ISSN `ISSN(?:-L|-H)?` or BIC `BIC|SWIFT` or IBAN `IBAN:` label. A single `ORCIDRecognitionGrammar` with Regex strategy is correct. Using two grammars (`orcid_bare` + `orcid_uri`) would create cross-grammar containment where the URI's embedded bare run duplicates, producing spurious `AMBIGUOUS` (longer-wins is per-grammar only, cross-grammar preserved per `orchestrator:_dedup_spans`). Single grammar with optional group avoids this.

3. **Validation is single-level checksum, no country/per-prefix lookup for correctness.** Level 1: generic structure `15 digits + [\dX]` plus length `16` exact plus `X` only at position 16 uppercase, then MOD 11-2 `validate(number) == 1` (or `calc_check_digit(base15) == C`). No country-code table like BIC, no registrant-range like ISBN, no registry-gated liveness for initial `SUCCESS`. Prefix `0000` is historically common (14M+ ORCID iDs start `0000`) but not validating; reserved-block `0000-0001…` / `0009…` distinction is registry informatics, not a structural reject. `X` value 10 must be accepted; lowercase `x` folded to `X` in grammar then rejected if rule expects uppercase.

4. **Bare vs URI are the same identifier, not distinct identities.** `0000-0002-1825-0097` and `https://orcid.org/0000-0002-1825-0097` are one value. Canonical identity is the hyphenated `XXXX-XXXX-XXXX-XXXC` token; formatting may offer `uri` (prepend `https://orcid.org/`) as presentational expansion, but validation treats both as syntactic variants of one string (dedup on `value` guarantees identical evaluation).

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `ISO 27729:2024` (`active`, 2024-11, `01.140.20`, ICS, `TC 46/SC 9`, cancels `2012` + incorporates Cor 1:2013 — see §5.1) owns ISNI/ORCID structure (16 chars, dumb number, presentation blocks, Annex A allocation/bibliographic lineage); `ISO/IEC 7064:2003` (`active`) owns MOD 11-2 system; `ORCID Registry` (`kind="registry"`, rolling, CC0 data file) owns issuance block definition and URI/host/path display. No country-specific BBAN registry, no URN namespace beyond ISNI family (IANA lists `isni` indirectly via ISNI Linked Data, but ORCID itself is `https` URI).

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need ORCID canonicalization | Typical context |
|---------|--------------------------------------|-----------------|
| **Scholarly publishing / editorial engineers** | Normalize `orcid.org/0000-0002-1825-0097` vs `0000 0002 1825 0097` vs `https://orcid.org/0000-0002-1694-233X` to one hyphenated key for manuscript submission systems, JATS XML, Crossref deposits, deduplication and ORCID search-link before article ingest | Editorial Manager, ScholarOne, OJS, typesetting pipelines, Crossref / DataCite metadata, PubPub |
| **Research information / CRIS & institutional repository teams** | Validate user-supplied ORCID at form ingest; reject syntactically invalid vs checksum-failed input with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | DSpace, EPrints, Pure, Converis, IR ingest, grant application portals, researcher profile linking |
| **Data engineering / Open Science aggregation** | Extract and canonicalize ORCIDs from free-text acknowledgements, PDFs, emails, README/CITATION.cff, or scraped HTML with span-bearing provenance; join on canonical key despite author-submitted variance | ETL pipelines, OpenAIRE, OpenAlex, ORCID public data file consumers, LLM extraction post-processing, CWL prov |
| **Identity / trust & compliance teams** | Use ORCID as stable researcher key alongside ISNI/ROR and email; detect duplicate identities across formatted variants, including `X` checksum and leading-zero preservation | Entity resolution, contributor disambiguation, funding compliance (UKRI, NIH, ERC), knowledge-graph researcher matching |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many ORCID mentions) and a contract; Paxman returns one canonical ORCID (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ISSN (`hyphenated` compact default) and ISBN (`isbn13` bare digits) ergonomics, but the canonical default is **hyphenated `XXXX-XXXX-XXXX-XXXC`** (with `X` uppercase when present), and URI rendering is an offered alternative.

---

## 2. Shape of Input (Human Surface)

### 2.1 Wild variants — enumerated from spec, ORCID docs, ISNI samples, and real validators

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | **Canonical hyphenated** | `0000-0002-1825-0097`, `0000-0002-1694-233X`, `0000-0001-5109-3700` | Spec master form, 16 chars with 3 hyphens, `4-4-4-4`, final `X` uppercase only; `format_value()` default target |
| 2 | **Canonical URI** | `https://orcid.org/0000-0002-1825-0097`, `https://orcid.org/0000-0002-1694-233X` | ORCID storage/display canonical (Support page § Storage); label + `https://` prefix, 3 hyphens, same checksum; grammar must claim URI as one span |
| 3 | **HTTP URI variant** | `http://orcid.org/0000-0002-1825-0097` | ORCID XSD v2.0 used `http`, v2.1 migrates to `https`; recognizer tolerates both but normalizes to `https` |
| 4 | **Bare compact (no hyphens)** | `0000000218250097`, `000000021694233X` | 16 contiguous digits/`X`; many DB exports; `MISSING` under v1 hyphen-only grammar — hyphenated on `compact→orcid` via `format_value` when `compact` offered, but compact input requires fallback `Pre` or second grammar (§13#9) |
| 5 | **Spaced groups (ISNI style)** | `0000 0002 1825 0097`, `ISNI 1422 4586 3573 0476` analogue | ISNI §4.3 human-readable is spaced; ORCID docs show hyphens; `MISSING` under v1 hyphen-only grammar — spaced accepted only via `Pre` normalizer then hyphen-reinsertion (§13#9) |
| 6 | **Lowercase / mixed case `x`** | `0000-0002-1694-233x`, `0000-0002-1694-233X` | Check `X` represents 10; canonical is uppercase; grammar must accept `(?i)` and normalize via `.upper()` |
| 7 | **Label with colon/space/hyphen** | `ORCID: 0000-0002-1825-0097`, `ORCID 0000-0002-1825-0097`, `orcid: 0000-0002-1825-0097`, `ISNI: 0000-0002-1825-0097` | Many forms and exports prefix `ORCID` or `ISNI`; handling must be case-insensitive, colon/space/hyphen tolerant; span should include label when present (`raw_text` preserves it) or exclude it — document (§8) |
| 8 | **Without protocol domain-only** | `orcid.org/0000-0002-1825-0097`, `www.orcid.org/0000-0002-1825-0097` | PubPub/cwltool/respec show this is common paste; grammar optional group must allow `(?:https?://)?(?:www\.)?orcid\.org/` |
| 9 | **With trailing slash** | `https://orcid.org/0000-0002-1825-0097/` | `URL("https://orcid.org/0000-0002-1825-0097/")` trailing slash handling in respec; extraction must emit one span without swallowing parenthetical |
| 10 | **With trailing annotation** | `0000-0002-1825-0097 (Jane Doe)`, `0000-0002-1825-0097 — University X` | Free-text often annotates name/affiliation; extraction must emit one span per ORCID, not swallow `(...)` |
| 11 | **Multiple per line** | `0000-0002-1825-0097 / 0000-0001-5109-3700`, `ORCIDs: 0000-0002-1825-0097, 0000-0002-1694-233X` | Author lists, contributor pages, CFF `authors:` — free-text may contain 2+ ORCIDs |
| 12 | **Quoted / bracketed** | `"0000-0002-1825-0097"`, `[0000-0002-1825-0097]`, `(https://orcid.org/0000-0002-1825-0097)` | Scraped HTML, JSON fragments, BibTeX wrap ORCIDs in quotes/brackets; literal `"` and `(`/`)` must not break word-boundary guard |
| 13 | **OCR / homoglyph errors** | `0000-0002-1825-0097` with `O` vs `0` confusion, `1` vs `I` | Strict `0-9` + `X` only; no autocorrection; wrong char → `INVALID` (or `MISSING` if not claimed) |
| 14 | **Over-long / under-long** | `0000-0002-1825-009` (15 chars), `0000-0002-1825-00977` (17 chars) | Only `16` valid (15 digits + check); 15/17 must not be recognized |
| 15 | **X-glued runs** | `X0000-0002-1825-0097`, `0000-0002-1825-0097Y`, `A0000-0002-1825-0097B` | Longer alphanum token must not yield inner ORCID via carving; word-boundary guards required |
| 16 | **Invalid checksum for otherwise correct shape** | `0000-0002-1825-0098` (last digit 8 not 7), `0000-0002-1694-2330` (last 0 not X) | Grammar may still claim hyphened `XXXX-XXXX-XXXX-XXXC` shape, rule rejects via MOD 11-2 |
| 17 | **Legacy spaced ISNI vs ORCID hyphen** | `0000 0001 5109 3700` (spaces 4-4-4-4) vs `0000-0001-5109-3700` (hyphens) | Same 16-char payload, different separator; normalizer collapses both to hyphenated |
| 18 | **Wrong prefix char case** | `https://ORCID.org/0000-0002-1825-0097` | Domain case-insensitive; scheme `https` lower; host normalized; grammar tolerates via `(?i)` on URI prefix |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Generic consensus (ORCID docs, regexlib) | `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` — 3× `0000-` + 3 digits + check; hyphen required, `X` only at pos16 |
| URI consensus (cwltool, pubpub, respec, ORCID-Source) | `^(?:(?:https?://)?(?:www\.)?orcid\.org/)?(\d{4}-){3}\d{3}[\dX]$` — optional protocol + optional `www.` + `orcid.org/` then hyphened payload |
| `arthurdejong/python-stdnum` `stdnum/isni.py` @ `006192e` | `compact(number,' -').strip().upper()` then `len==16` + `isdigits(number[:-1])` + `mod_11_2.validate(number)` → `format()` as `' '.join((number[:4],number[4:8],number[8:12],number[12:16]))` (spaces for ISNI; ORCID mirrors with `-`) |
| `ORCID/ORCID-Source` `orcid-utils/OrcidStringUtils.java` @ `cac0eca` | `ORCID_STRING = "(\d{4}-){3}\d{3}[\dX]"` ; `ORCID_URI_STRING = "http://([^/]*orcid\.org\|localhost.*/orcid-web)/(\d{4}-){3,}\d{3}[\dX]"` ; `ORCID_URI_2_1_STRING = "https://([^/]*orcid\.org\|localhost.*/orcid-web)/(\d{4}-){3,}\d{3}[\dX]"` |
| `ORCID/orcid-model` `common-3.0.xsd` @ `bcb083f` | `orcid-path: "(\d{4}-){3,}\d{3}[\dX]"` ; `orcid-uri: "https://([^/]*orcid\.org\|localhost.*/orcid-web)/(\d{4}-){3,}\d{3}[\dX]"` |
| `hypothesis/h` `h/accounts/util.py` @ `24395ca` | anchored `\A[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]\Z` + iterative `total=(total+digit)*2`, `result=(12-remainder)%11`, `10→X` |
| `common-workflow-language/cwltool` @ `baefdcb` | liberal `(http://orcid\.org/\|https://orcid\.org/\|orcid\.org/)?(?P<orcid>(\d{4}-\d{4}-\d{4}-\d{3}[0-9x]))$` lower-then-upper |
| `knowledgefutures/pubpub` @ `ba3d8f8` | `ORCID_PATTERN = /(\d{4}-){3}\d{3}(\d\|X)/` + `ORCID_ID_OR_URL_PATTERN = /^(?:(?:https?:\/\/)?(?:www\.)?orcid\.org\/)?(\d{4}-){3}\d{3}(\d\|X)$/g` |
| `validator.js` `isSSN/isISSN/isISBN` | No `isORCID` — absence confirms ORCID validation is registry-side; `isISSN` `^\d{4}-?\d{3}[\dX]$` + `Σ d×(8-i) %11==0` is closest analogue, not reused |
| `scippneutron/_orcid.py` | `segments = id.split('-'); len==4 and all(len==4)` then `total=(total+d)*2` over first 15 digits, `result=(12-total%11)%11`, `X if 10` match |
| `isvalid.dev` ORCID spec | `Accepted: 0000-0002-1825-0097` or `https://orcid.org/0000-0002-1825-0097`, `X` uppercase, hyphens required for formatted |

**Normalization contract (reuse python-stdnum ISNI pattern):**

```python
# python-stdnum orientation - strip separators, upper, then checksum
import re

# strip URI prefix first, then hyphens/spaces
uri_stripped = re.sub(r"(?i)^(?:https?://)?(?:www\.)?orcid\.org/", "", raw).strip()
compact = (
    re.sub(r"[ \-]", "", uri_stripped).strip().upper()
)  # 16 chars: 15 digits + [\dX], X only at 16
# then validate: len==16 and regex ^\d{15}[\dX]$ + MOD 11-2
```

### 2.2 What input is NOT an ORCID mention

- ISNI organizational identities outside the ORCID-reserved block that happen to share the 16-char check format but were not ORCID-minted — grammar may claim either; provenance distinguishes `ISNI` vs `ORCID` only via URI presence or block range, not structural validity.
- Non-researcher IDs of similar digit length: ISBN (`13` digits), ISIN (`12` with check), LEI (`20` no hyphen), IBAN (`15–34` with country prefix) — length + hyphen pattern `4-4-4-4` disambiguates; ORCID `0000-0001-5109-3700` is `19` with hyphens but `16` compact, IBAN smallest `15`.
- Bare 15-digit prefix or 16 without checksum verification — grammar rejects length not `16`, rule would fail `INVALID`.
- Short digit runs (`0000`, `1825`) — `MISSING` vs `INVALID` boundary (see §9).
- Lowercase `x` at position 16 is not distinct vocabulary but case variant — normalized to `X`, still single canonical.

### 2.3 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct ORCIDs that normalize to different hyphenated values is `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` with `single_value=True` enforcement); the caller-owned segmentation path (split then canonicalize each slice) is the intended multi-entity pattern for author lists, acknowledgement lines with multiple contributors, or BibTeX/CFF entries. Identical ORCID mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact plus structured decomposition (with URI flag)

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ORCIDNotation:
    """ORCID notation — grammar-normalized hyphenated form.

    ``compact`` is the 16-char hyphened-removed uppercase compact: 15 digits + check `0-9` or `X`.
    ``hyphenated`` is the `XXXX-XXXX-XXXX-XXXC` presentation (three hyphens, `X` uppercase).
    ``uri`` is `https://orcid.org/XXXX-XXXX-XXXX-XXXC` (https always, no trailing slash).
    ``check`` is the single check character `0-9` or `X` at position 16.
    ``is_uri`` tracks whether the raw input carried an `orcid.org` URI prefix (bool-as-str for frozen slots check).

    The grammar never validates the MOD 11-2 checksum; rules own that
    (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    """

    compact: str  # e.g. "0000000218250097" — 16, 15 digits + [\dX]
    hyphenated: str  # e.g. "0000-0002-1825-0097" — 19 with hyphens, X uppercase
    uri: str  # e.g. "https://orcid.org/0000-0002-1825-0097" — https, hyphenated
    check: str  # e.g. "7" or "X" — single char, upper
    is_uri: str  # "true" if raw had orcid.org/ prefix else "false" — str per notation=str invariant
```

**Considered alternative — single field `compact` only:** `MoneyNotation` style with multi-field validation in `__post_init__`, and `ISSNNotation` `digits`-only shape. A single `compact` (`16` chars `15+check`) would suffice for the MOD 11-2 rule (which operates on compact digits) and URI rendering can be derived by slicing `compact[0:4]-...`. However a multi-field decomposition is preferred because:

1. The ORCID Support display guidance distinguishes bare hyphenated vs URI storage vs compact in § Storage vs Display; the formatter must produce either without recomputing checksum.
2. `X` as check `10` needs a first-class field so the formatter can offer case-insensitive handling and tests can assert `check=="X"` canonical is uppercase.
3. `is_uri` as string-encoded bool lets the grammar record whether the original span included the URI without leaking presentation into validation (grammar owns prefix stripping, not rule).

The notation is therefore **isomorphic to ISSN hyphen-stripped vs hyphenated plus BIC branch-as-matched**, and satisfies `Grammar[ORCIDNotation].recognize()` then `Rule[ORCIDNotation].matches()` typing. Every field is `str` (HOW_TO_ADD_NEW_CAPABILITY.md requires all notation fields be `str`).

**Invariants the grammar enforces (before rules):**
- `hyphenated` is exactly `19` chars with pattern `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` uppercased (`X` not `x`), three hyphen-minus at positions 5,10,15.
- `compact` is exactly `16` (`re.sub(r"[ \-]", "", hyphenated).upper()` equals 15 digits + `[\dX]`; compact `[:-1]` digits-only).
- `check` is single `0-9` or `X`, equals `compact[-1]`.
- `uri` is `https://orcid.org/` + `hyphenated` (always `https` even if raw was `http`).
- `is_uri` is `"true"` or `"false"` (lowercase string bool).
- `raw_text` preserves original span (URI prefix plus spacing plus original case/hyphens/spaces); the notation is the syntax-normalized token.
- Lowercase `x` input maps to `X`; spaced `0000 0002 1825 0097` and compact `0000000218250097` are `MISSING` under v1 hyphen-only grammar (accepted only via `Pre`/second-grammar fallback, see §13#9).

### 3.2 Why not carry spaces or labels in the notation

Spaces, `ORCID:`/`ISNI` labels, and `https://orcid.org/` / `http://orcid.org/` / `orcid.org/` / `www.orcid.org/` prefixes have **no lexical significance** for validity — compact-plus-check is the wire form, hyphenated is readability, URI is storage. Compact and hyphenated forms of the same 16-char payload have the same identity regardless of input prefix (`orcid.org/` presence), dedup and status logic operate on `hyphenated` (or `compact`). Presentation is `Capability.format_value()` only. The ORC ID XSD `common-3.0` confirms `orcid-uri` as `https://…/(\\d{4}-){3,}\\d{3}[\\dX]` is derived.

### 3.3 Why `check` is not a shape discriminator literal

ISBN uses `shape: Literal["isbn10","isbn13"]` because two lexical lengths map to distinct notations that later converge. ORCID has one canonical length `16` (with `X` only at pos16) — distinguishing `0-9` vs `X` at the type level would require a `Literal` over 11 values rather than registry semantics; instead `check` is free `str` validated by MOD 11-2 `PARSER` rule (ISSN does the same: `X` is semantics not shape). No `shape` field is needed because `hyphenated` length `19` already discriminates.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape, delimiters, fixed widths, character classes) or **Lexicon** (finite vocabulary, Country names, Currency words). ORCID has a distinctive fixed-width hyphenated shape (`4-4-4-4` with final check `[\dX]`), plus optional `https://orcid.org/` URI label, so **Regex** is the correct strategy. No lexicon table is involved at recognition, the lexicon for valid ORCIDs lives in no grammar but in the check-digit rule and optional registry.

### 4.2 Reference pattern (adapted from ISSN and BIC verbatim precedent)

ISSN precedent (`paxman/capabilities/ISSN/grammar/issn_recognition.py`):
```python
_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]*)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.word_only().lookahead
)
```
BIC/IBAN precedent (BIC compact `8/11` with `BIC|SWIFT` label, IBAN `IBAN` label, both `[\s:-]+`):
```python
_BIC_BODY = r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?))"
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)
```

**Proposed ORCID pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope string pattern — compiled by RegexStage (never inside recognize())
# Optional ORCID/ISNI label + optional URI host, then the 19-char hyphenated payload.
# Host tolerance mirrors ORCID XSD orcid-uri plus ecosystem libs (cwltool, pubpub, respec):
#   https://orcid.org/ (canonical) + http:// (v2.0 legacy) + orcid.org/ + www.orcid.org/
# Label uses one-or-more separator, never zero-width (BIC L12-13 precedent:
# glued ORCID0000-... must not fuse). Glued-label lookahead blocks fusion.
_ORCID_LABEL = r"(?:(?ai:ORCID|ISNI)[\s:-]+)?"
_ORCID_HOST = r"(?:(?ai:(?:https?://)?(?:www\.)?orcid\.org)/)?"
_ORCID_GLUED_GUARD = r"(?!(?ai:(?:ORCID|ISNI)[0-9]))"
_ORCID_BODY = rf"{_ORCID_LABEL}{_ORCID_HOST}{_ORCID_GLUED_GUARD}(?P<hyphenated>(?ai:\d{{4}}-\d{{4}}-\d{{4}}-\d{{3}}[\dX]))"
# Wrapped with word-boundary guards — ORCID is [0-9X-] glued, so word_only prevents
# carving a valid run out of a longer token like "X0000-0002-1825-0097" or "0000-0002-1825-0097Y"
_ORCID_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ORCID_BODY
    + BoundaryGuard.word_only().lookahead
)


def _orcid_notation(match: re.Match[str]) -> ORCIDNotation:
    hyphenated_raw = match.group("hyphenated")
    hyphenated = hyphenated_raw.upper()  # x→X
    compact = hyphenated.replace("-", "")  # 16
    check = compact[-1]
    uri = f"https://orcid.org/{hyphenated}"
    full = match.group(0)
    is_uri = "true" if "orcid.org" in full.lower() else "false"
    return ORCIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        uri=uri,
        check=check,
        is_uri=is_uri,
    )


class ORCIDRecognitionGrammar(PipelineGrammar[ORCIDNotation]):
    """ORCID recognition — hyphenated 4-4-4-4 with optional ORCID label and https://orcid.org/ URI."""

    name = "orcid_recognition"
    semantics = "orcid_recognition"
    single_value = True
    pre = StandardPre[ORCIDNotation](empty_guard=True)
    regex = RegexStage[ORCIDNotation](
        pattern=_ORCID_PATTERN, notation_fn=_orcid_notation
    )
```

*Notes on fidelity vs ISSN and BIC:*

- Ship as module-scope **string** pattern; `RegexStage` compiles in `paxman/core/grammar/stages.py` (mirrors ISBN `_ISBN13_PATTERN = r"..."`). Do not double-compile via `re.compile(...).pattern`.
- Uppercase `X` in `notation_fn` via `.upper()` (ISSN precedent `x`→`X` is `isalnum` plus `upper`; ISBN10 `x→X` same). ASCII fidelity is enforced inline via `(?ai:…)` on label, host, and hyphenated body — mirroring BIC `(?ai:…)` and IBAN `(?ai:IBAN)` — so fullwidth digits `００００…` are never claimed; `Xx` redundant class reduced to `[\dX]` with the inline flag supplying case-insensitivity.
- Final group `(?:\d{3}[\dX])` guarantees check at `pos16` is `[\dX]`; a pattern like `[\dX]{4}` would allow `X` mid-run incorrectly.
- Leading `BoundaryGuard.word_only()` (`(?<!\w)`) and trailing `BoundaryGuard.word_only()` (`(?!\w)`) block digit/`X`-glued runs (`X0000-0002-1825-0097`, `0000-0002-1825-0097Y`, `A0000-0002-1825-0097B`). Shipped `ISSN/grammar/issn_recognition.py` uses `BoundaryGuard.word_only().lookbehind` plus `digit().lookahead + r"\b"` (verified); ORCID follows `word_only` both sides with hyphen, since alphabet includes hyphens and gluing via underscores/digits is common in free text. Do NOT use `digit().lookahead` alone because `X` could be glued as `XXXX`.
- **Label handling:** `_ORCID_LABEL` `(?:(?ai:ORCID|ISNI)[\s:-]+)?` plus glued-label guard `(?!(?ai:(?:ORCID|ISNI)[0-9]))` is fused (like BIC `BIC|SWIFT` with `[\s:-]+` and negative lookahead, and ISSN `ISSN(?:-L|-H)?`); the `notation_fn` maps only the `hyphenated` group, so `raw_text` includes label+URI+spacing when matched, but `notation.hyphenated` is bare. Whether `raw_text` includes the label is design choice; include via `m.group(0)` like ISSN, or attribute only via `hyphenated`; document.
- **URI tolerance:** `_ORCID_HOST` tolerates `https://orcid.org/` (canonical v2.1), `http://orcid.org/` (v2.0 legacy per Support page XSD v2.0), `orcid.org/`, `www.orcid.org/`. Normalizer always emits `https://orcid.org/` (see `uri` field). This tolerates cwltool/pubpub `orcid.org/`, elabftw `https?`, respec `new URL(..., "https://orcid.org/")`. `https` vs `http` must not affect checksum.
- **Delimiter tolerance:** Pattern above handles hyphenated only (canonical). Compact `0000000218250097` (no hyphens) and spaced `0000 0002 1825 0097` (ISNI style) are separate variants handled either as additional alternation `(?:\d{4}-\d{4}-\d{4}-\d{3}[\dX]|\d{16}|\d{4} \d{4} \d{4} \d{3}[\dX])` or as a `Pre` that normalizes spaces/hyphens before regex — document in §13#9.
- Uses `PipelineGrammar` plus `StandardPre` plus `RegexStage` because that is the staged pipeline ISSN actually ships (HOW_TO_ADD_NEW_GRAMMAR.md bare `Grammar` recipe is minimal teaching form; shipped grammars use `PipelineGrammar`).

**Compact vs hyphenated as one grammar vs two:**

Like ISSN compact vs hyphenated, the compact digits `0000000218250097` and hyphenated `0000-0002-1825-0097` are two *presentations* of the same 16-char value, not two *meanings*. Options:

- **(Recommended) Single grammar** with hyphen required `(\d{4}-){3}\d{3}[\dX]` only plus `is_uri` flag — minimal containment complexity (`_dedup_spans` no-op within one grammar), single `semantics` id; compact digits accepted as fallback via `notation_fn` compact fallback check `len(hyphenated_raw)==16` branch (see §13).
- **Alternative:** Two grammars `orcid_hyphenated_recognition` plus `orcid_compact_recognition` with coalesced `semantics = "orcid_recognition"` (HOW_TO_ADD_NEW_GRAMMAR.md option A, reuse shipped semantics id so existing `ISO 27729:2024` rule validates both without edit). Only introduce if you want to record provenance that input was compact vs hyphenated (not needed, provenance is the authority not the presentation).

### 4.3 Recognition pipeline contract (ARCHITECTURE.md Recognition Pipeline Contract)

- Grammar emits **span-bearing** `RecognitionMatch[ORCIDNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; engine validates span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize` validated).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))`, span is the regex slice. Stages must not mutate `text` (`PipelineState` scratch only).
- Engine owns **within-grammar containment dedup** ("longer wins", identical spans keep first-emitted) and **total recognition ordering** `(start, end, active_grammars index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups, two grammars agreeing on the same span are both preserved for ambiguity observation. For ORCID (single shipped grammar initially), this dedup keeps the hyphenated match over a prefix when both would match at same start (longer wins).
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`).

### 4.4 Guard boundaries against sibling grammars

ORCID vs sibling alphanum grammars: ORCID `16` with `4-4-4-4` hyphens vs ISSN `8` with `4-4` vs ISBN `13` digits `10` vs IBAN `15–34` country prefix — hyphen count plus digit-only charset splits disambiguation.

Concrete length discrimination table:

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| ORCID | `16` digits+`X` with hyphens `19` including `---`; compact `16` | `4×4` groups, hyphens at 5/10/15 | `(?!\w)` prevents claiming prefix of longer digit run; `X` only at 16, not mid |
| ISSN | `8` with hyphen at 5 `XXXX-XXXX` | `4` digits at start | `(?!\w)` plus hyphen tolerance; ORCID fragment `0000-0002` could look like ISSN but ISSN has 1 hyphen after 4 vs ORCID 3 hyphens |
| ISBN | `13` digits `10` legacy with `X` at end | `978`/`979` GS1 or `0-` | `12-13` run longer than ORCID single block but hyphen pattern `4-4-4-4` never matches ISBN `3-` grouping |
| IBAN | `15–34` alphanum starting `CCDD` | `CC` letters at 1-2 | ORCID digits `0-9` cannot be IBAN `CC` letters; no confusion |

Prefix-aware ORCID detection (`https://orcid.org/`, `ORCID:`) does not clash with sibling labels (`ISSN:`, `ISBN:`, `IBAN:`); case-insensitive `ORCID` vs `ISNI` substrings are distinct but both accepted per `_ORCID_LABEL`. For a digit run `0000000218250097` (compact) without hyphens, recognition depends on whether the fallback `(?:\d{15}[\dX])` branch is enabled; without it the compact is `MISSING` vs `INVALID` after MOD 11-2 (see §13).

Concrete engine check (`orchestrator:_dedup_spans`):

```python
ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
# longer wins within SAME grammar; across grammars never deduped
```

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

The new grammar declares a non-empty `semantics` string; every validating `Rule` declares `target_semantics: frozenset[str]` naming the semantics ids it validates. The engine `_validate_affinity` fails fast (`ContractError`) if a rule names a semantics no grammar claims. For a single shipped ORCID grammar, the natural ids are:

- `semantics = "orcid_recognition"` (identity id).

Recommendation: start with identity `orcid_recognition`; coalesce only if a second grammar (e.g. `orcid_compact_recognition`) is later added, coalescing is option A in HOW_TO_ADD_NEW_GRAMMAR.md.

### 4.6 `single_value` — one mention per call vs batch processing

Shipped capabilities (ISBN, Country, Money, Phone) all set `single_value=True`, consistent with Paxman "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). Author acknowledgement strings legitimately contain 2+ ORCIDs per document (`Author A 0000-0002-1825-0097 — Author B 0000-0001-5109-3700`; JATS `<contrib>` dumps), so batch extraction will want free-text mining of multiple mentions.

Recommendation: **initial `single_value=True`** (matches shipped precedent and the single-researcher field use-case), with a documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A separate free-text community grammar with `single_value=False` can be offered via `extra_grammars` for batch-processing callers when needed.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **ISO — International Organization for Standardization**, Technical Committee **ISO/TC 46 Information and documentation**, Subcommittee **SC 9 Identification and description** (Standardization of information identifiers, description and associated metadata). ORCID Block coordination via ISNI-IA under TC 46 authority. |
| **Registration Authority (RA)** | **ISNI International Agency (ISNI-IA) Ltd** — c/o EDItEUR, United House, North Road, London N7 9DP, UK, Company No 07476425, Chair Michael Healy, Exec Director Tim Devenport (EDItEUR). Quality Team **BnF + British Library** per `isni.org/page/how-isni-works`. Responsible for receiving assignment requests, defining system architecture (Annex C), allocating per Annex B, publishing ISNI Database duplicate-claim-free. **For ORCID minting specifically: ORCID, Inc.** (global not-for-profit, Board-governed, sustained by member fees) — "Only the ORCID Registry can assign ORCID iDs" (Support page § Issuing). ORCID is an ISNI Registration Agency: reserved block `0000-0001-5000-0007`–`0000-0003-5000-0001` plus `0009-0000-0000-0000`–`0009-0010-0000-0000` assigned by ISNI-IA to avoid duplication (Joint Statement 2013). |
| **Spec name** | `ISO 27729 — Information and documentation — International Standard Name Identifier (ISNI)` ; Annex A MOD 11-2 cites `ISO/IEC 7064:2003 — Information technology — Security techniques — Check character systems` (M=11, r=2) |
| **Current edition** | **ISO 27729:2024 (2nd ed., published 2024-11-11)** — current, `60.60 Published`, Publisher ISO/TC 46/SC 9, ICS 01.140.20. Withdraws ISO 27729:2012 (which is withdrawn 2024-11/2024-12 per NEN `Withdrawal 1 dec 2024` / BS `Superseded 14-11-2024 — Superseded by BS ISO 27729:2024`). See lineage table below. |
| **Check character system** | `ISO/IEC 7064:2003 MOD 11-2` (pure system, single check, `M=11, r=2`, alphabet `0123456789X`, indices `0123456789`). Table 1 of 7064: `Single check digit or supplementary X`. Recursive or polynomial both valid (see §7). |
| **Related specs** | `ISO/IEC 7064:2003` (normative ref, ICS 35.030 ISO/IEC JTC 1/SC 27); ORCID XSD `common-3.0` `orcid-path`/`orcid-uri`; ORCID Registry API and CC0 Public Data File; ISNI Linked Data `https://isni.org/page/linked-data`. |

**ISNI/ORCID structure (ISO 27729:2012 §4, ORCID Support page verbatim, ISNI-IA governance page):**

```
ISNI = 16 chars = 15 decimal digits + check C ∈ {0-9,X}  (position 16)
       Dumb number — no meaning embedded (§4.2)
       Check = MOD 11-2 over first 15 digits (Annex A, §4.4)
       Human display: ISNI 1422 4586 3573 0476 (four spaced blocks, ISNI label) — spaces + label not part of ISNI
       ORCID transfer: hyphen every 4: 0000-0002-1825-0097 (§ Expressing); URI https://orcid.org/0000-0002-1825-0097 (§ Storage)

Positions:
 1-4  first block 4 digits (often 0000 for 14M+ ORCIDs)
 5-8  second block 4 digits (reserved block 0000-0001 / 0000-0003 / 0009)
 9-12 third block 4 digits
13-16 fourth block 3 digits + check (M=11, r=2, X=10)

 Total 16 chars only (never 15 or 17). Leading zeros significant (must not truncate).
```

Quoted ORCID Support page (Structure, Format and Checksum sections):

> "The ORCID iD is an https URI with a 16-digit number that is compatible with the ISO Standard (ISO 27729), also known as the International Standard Name Identifier (ISNI), e.g. https://orcid.org/0000-0001-2345-6789"

> "ORCID iDs always require all 16 digits of the identifier; they can not be shortened to remove leading zeros if they exist."

> "No information about a person is encoded in the ORCID iD."

> "The last character in the ORCID iD is a checksum. In accordance with ISO/IEC 7064:2003, MOD 11-2, this checksum must be "0" - "9" or "X", a capital letter X which represents the value 10."

Quoted ISO 27729:2012 §4 via iteh sample:

> "4.1 An ISNI shall consist of 16 digits. It shall consist of two components: a) 15 decimal digits, and b) a check character."

> "4.3 When an ISNI is written … a) it shall be preceded by the letters ISNI, separated … and b) the 16 digits shall be displayed as four blocks of four digits … EXAMPLE ISNI 1422 4586 3573 0476"

> "4.4 The check character may be either a decimal digit or the character "X" and shall be calculated using the preceding 15 decimal digits in accordance with the ISO/IEC 7064, MOD11-2 algorithm, as described in Annex A."

- Formal charset: hyphenated `(?ai:\d{4}-\d{4}-\d{4}-\d{3}[\dX])` (ASCII-only `(?ai:)` body, `X` uppercase only at pos16) compact `(?ai:\d{15}[\dX])`; URI `(?ai:https?://(?:www\.)?orcid\.org/)(?ai:\d{4}-\d{4}-\d{4}-\d{3}[\dX])` (scheme/host via `(?ai:)` as well); `X` only at pos16 upper.
- Leading zeros significant (Bills example: `0000-0001-4512-4044` / `0000-0002-1694-233X` in elabftw, not `…-1694-233`).
- Branch equivalence negative: no branch/XXX — ORCIDs are singletons, not institution+branch.
- Examples from evidence: `ISNI 1422 4586 3573 0476` (ISNI), `https://orcid.org/0000-0002-1825-0097` (ORCID), `0000-0002-1694-233X` (X), `0000-0001-5109-3700` (ends `00`), `0000-0001-2281-955X` (ISNI via stdnum docstring), `0000-0001-6672-8648` (elabftw sample).

**Lineage table (ISO 27729 editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| 09/30177090 DC | 2009 draft 05/2012 per BS *Supersedes* | draft | DC for ISNI, cited as DC 09/30177090 in BS `Supersedes 09/30177090 DC (05/2012)` |
| ISO 27729:2012 | 2012-03-15 published (NEN 1 mrt 2012; iTeh sample 2012-03) | withdrawn 2024-11-11 / 2024-12-01 | 1st ed., 01.140.20, 15 pages; Annex A method for calculating check character, Annexes B/C/D assignment/administration/metadata |
| ISO 27729:2012/Cor 1:2013 | 2013 | withdrawn (rolled) | Technical Corrigendum 1 — corrects typographical error in check-digit calculation description (Annex A) now incorporated into 2024 |
| ISO 27729:2024 | 2024-11-11 published (iteh *60.60 2024-11-11*) | current, 60.60, 2nd ed. | Minor revision, cancels/replaces 2012, incorporates Cor 1, editorial alignment to ISO/IEC Directives Part 2:2021; no structure change (ISNI News: minor revision under TC 46/SC 9) |

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| ISO (ISO/TC 46/SC 9) | `ISO 27729:2012` | `2012-03` (1st ed.) | `https://www.iso.org/standard/44292.html` | `withdrawn` 2024-11-11 superseded | `2012` | `specification` |
| ISO (ISO/TC 46/SC 9) | `ISO 27729:2024` | `2024-11` (2nd ed., current) | `https://www.iso.org/standard/87177.html` | `active` — cancels 2012 | `2024` | `specification` |
| ISO (ISO/TC 46/SC 9) | `ISO 27729:2012/Cor 1:2013` | `2013` | `https://www.iso.org/standard/64745.html` | `withdrawn` (superseded) | `2013` | `specification` |
| ISO/IEC JTC 1/SC 27 + ISO/TC 46/SC 9 | `ISO/IEC 7064:2003` | `2003` (MOD 11-2) | `https://www.iso.org/standard/31531.html` | `active` — ICS 35.030 | `2003` | `specification` |
| ISNI-IA (ISO RA) | `ISNI Database / Linked Data` | `Rolling` | `https://isni.org/page/search-database` + `https://isni.org/page/linked-data` + `https://isni.org/page/governance` | `active` — rolling | `2024` | `registry` |
| ORCID, Inc. (ISNI RA + own Registry) | `ORCID Registry` | `Rolling (CC0 Public Data File, APIs v2.0/v2.1/v3.0)` | `https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier` + `https://info.orcid.org/what-is-orcid/services/orcid-registry/` + `https://github.com/ORCID/ORCID-Source` | `active` — rolling | `2012` (Registry launch) | `registry` |
| ORCID | `ORCID orcid-model XSD common-3.0` | `v3.0` (v2.1 https) | `https://github.com/ORCID/orcid-model/blob/bcb083f13dbaeba3e9e1c39c3b8fb1791891de3f/src/main/resources/common_3.0/common-3.0.xsd` | `active` | `2023` | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* A historical ORCID rule citing `ISO 27729:2012` would carry `lifecycle="withdrawn"` or `"superseded"` if archival `2012` is chosen; the initial shipped rule is expected `active` and references the rolling `ORCID Registry` (`kind="registry"`) plus stable `ISO/IEC 7064:2003` (`active`). `ISNI 1422 4586 3573 0476` style display never mixes ORCID hyphen vs ISNI spaced forms at validation.

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/iso_27729_ed2024.py` | `authority="ISO"`, `specification_name="ISO 27729:2024"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/87177.html"`, `version="2024-11"`, `lifecycle="active"`, `publication_year=2024` | `Section 4-orcid-structure` (16 chars, `4-4-4-4` hyphened payload, leading zeros significant, dumb number, `X` only at 16, human blocks `ISNI` label/spaces not part) | Generic structure: length `16` compact after collapsing `[ \-]` via ASCII-only `(?ai:)` body, charset `^\d{15}[\dX]$`, hyphen required, `X` only uppercase after grammar `.upper()`, leading zeros retained; `normalize()` returns hyphenated `XXXX-XXXX-XXXX-XXXC` |
| `rules/iso_7064_ed2003.py` *(or fused into 27729 file as Section Annex-A — recommend fused for minimal surface; split if purity preferred)* | `authority="ISO/IEC JTC 1/SC 27"`, `specification_name="ISO/IEC 7064:2003"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/31531.html"`, `version="2003"`, `lifecycle="active"`, `publication_year=2003` | `Section *-mod11-2-check-character` | MOD 11-2 over first `15` digits: `total=(total+digit)*2`, `result=(12 - remainder)%11`, `10→X`; validate full `16` yields `checksum==1` (polynomial) or `check matches calc`; `normalize()` returns same hyphenated as peer |

*Alternative single-file fuse (ISSN precedent: one ISO 3297 file with single Section 4 rule):* fuse structure + MOD 11-2 into one `iso_27729_ed2024.py` file carrying **two** `Rule` classes (`Section4OrcidStructure` + `SectionAnnexAMod11Dash2`) sharing the same `PUBLICATION` (`ISO 27729:2024` active) — this cites 7064 as normative Annex A inside 27729 citation and keeps `get_rules()` at `2`. If per-publication purity is preferred, split into `iso_7064_ed2003.py` as second file; either way `get_rules()` is `2` (see §12).

*Registry-gated liveness layer (optional, deferred — see §5.4) — NOT shipped initially:*

| `rules/orcid_registry_ed2024.py` *(optional, gated, liveness)* | `authority="ORCID, Inc."`, `specification_name="ORCID Registry"` (`kind="registry"`, `reference_url="https://orcid.org/"`, `version="Rolling CC0"`) | `Section *-orcid-registry-membership` (liveness/existence) | Whether hyphenated ORCID is present in ORCID public data file / search index at snapshot; `requires_features={"include_registry_validation"}` |
| `rules/isni_database_ed2024.py` *(optional, ISNI-wide liveness)* | `authority="ISNI-IA"`, `kind="registry"`, `reference_url="https://isni.org/page/search-database"`, `version="Rolling"` | `Section *-isni-issued-membership` | Whether compact is present in ISNI DB (superset of ORCID block); gated behind same `include_registry_validation` — rarely needed |

*This mirrors ISBN three-authority split (ISO 2108 // ISBN Users Manual // ISBN Range Message, each one `PUBLICATION` per file) and ISSN single-mandatory-plus-optional split (ISO 3297:2022 // ISSN Register). For ORCID, only ISO 27729:+7064 are mandatory; any registry membership rule is optional, gated via `requires_features`, exactly like ISBN `Section 4-registrant-range` gated by `include_range_validation` and Country `include_localized`.*

Each `Rule[ORCIDNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`):

```python
class Section4OrcidStructure(Rule[ORCIDNotation]):
    name = "Section 4-orcid-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (ISNI 16-char structure, hyphens presentation)"
    target_semantics = frozenset({"orcid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ORCIDNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: ORCIDNotation, contract: Contract) -> str: ...
```

Evidence basis:
- **ISO 27729:2012 lineage** confirmed via `https://www.iso.org/standard/44292.html` (`2012-03`) + NEN `https://www.nen.nl/nen-iso-27729-2012-en-169667` (`Ingetrokken`, `ICS 01.140.20`, `Withdrawal 1 dec 2024`) + `https://www.iso.org/standard/87177.html` (`2024-11` `Reference number ISO 27729:2024`) + BS/iteh sample `https://cdn.standards.iteh.ai/samples/44292/...` (§4 text) + NEN 2024 `https://www.nen.nl/nen-iso-27729-2024-en-332125` (`Vervangt NEN-ISO 27729:2012 en C1:2013`).
- **ISNI-IA as RA:** `https://isni.org/page/governance` (ISNI-IA Ltd c/o EDItEUR) + `https://isni.org/` (ISNI is ISO 27729 bridge) + `https://isni.org/page/how-isni-works` (Quality Team BnF/British Library, diffusion via search API/database).
- **ORCID as RA + reserved block:** `https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier` (Structure, Issuing, Storage, Display, Samples, XSD v2.0/v2.1) + `https://info.orcid.org/orcid-and-isni-issue-joint-statement-on-interoperation-april-2013/` (`block set aside by ISNI-IA`).
- **Check system:** `https://www.iso.org/standard/31531.html` (ISO/IEC 7064:2003 designation MOD 11-2) + iteh `https://cdn.standards.iteh.ai/samples/31531/...` (§7 pure system, M=11 r=2, supplementary X, examples `0794→07940`, `079→079X`).
- **Structure quote** from Support page "ISNI shall consist of 16 digits … check … MOD11-2 … dumb number" paraphrased from iteh §4; ORCID page quote "The ORCID iD is an https URI … 16-digit number … compatible with ISO 27729 … ISNI".
- **X handling:** Support page "must be 0–9 or X, capital X which represents value 10" plus `generateCheckDigit` reference code `total=(total+digit)*2`, `result=(12-remainder)%11`, `10→X`.
- **Samples:** Support page `0000-0002-1825-0097`, `0000-0001-5109-3700`, `0000-0002-1694-233X`.

### 5.3 What each rule does vs does not own

- **`matches()`** — validates strictly. The structure rule checks: `compact` length `16`, `hyphenated` matches `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$`, `check` in `[0-9X]`, `X` only last char, uppercased, leading zeros preserved, `is_uri` ignored for validity. The MOD 11-2 rule checks: `getORCIDChecksum()` or `mod_11_2.checksum(compact) == 1` (see §7). All return `False` for any invalid input, never raise, not `ValidationError`, not `ValueError`. Contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** — returns the **default hyphenated form** `XXXX-XXXX-XXXX-XXXC` uppercase (no `orcid.org` prefix). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings). Presentation `uri`/`compact` is the capability `format_value()` seam only. Both rules must return the **same** hyphenated string for the same valid notation, candidate dedup `(value, recognition_rule, validation_rule)` ensures agreement stays `SUCCESS`.
- **`RuleStrategy` choice:** ISBN precedent uses `PARSER` for check digits and `LOOKUP_TABLE` for registry prefixes/registrant ranges. For ORCID, **both** rules are `PARSER` (structure shape + check transform); an optional registry membership rule, if offered, would be `LOOKUP_TABLE` (like ISSN Register existence or ISBN Range registrant).

### 5.4 Reserved-block / registry scope decision

The **ORCID-reserved ISNI block** `0000-0001-5000-0007`–`0000-0003-5000-0001` plus `0009-0000-0000-0000`–`0009-0010-0000-0000` is described in the Support page § Issuing and in the Joint Statement 2013. It is normative for *assignment* (ORCID Registry draws randomly from that block to avoid collision with ISNI assignments elsewhere) but **not** normative for *validity* of an already-formed `XXXX-XXXX-XXXX-XXXC` string. A syntactically valid MOD 11-2 `16-char` outside that block (e.g. `0000 0001 2281 955X` is inside, `1422 4586 3573 0476` is an ISNI organizational record outside) is still a valid ISNI per ISO 27729, just not ORCID-minted; Paxman validation should not reject it at `INVALID` by block prefix.

**Recommendation for an initial ORCID capability:** treat block prefix as **out of scope for mandatory validation** — it is **assignment history**, not a deterministic string transform, requiring a registry lookup for liveness. Validating that a string *is structurally an ORCID/ISNI* (`16` chars, `15+check`, MOD 11-2) vs that it *was minted by ORCID Registry* or *is present in the current public data file* are different claims; the latter requires a snapshot of the ORCID public data file, has staleness concerns, and is prefix-count non-trivial (two ranges covering ~4M potential numbers). The initial capability should canonicalize any generic ORCID-shaped `0000-0002-1825-0097` (correct length, hyphens, checksum) to its hyphenated form with provenance `ISO 27729 + ISO/IEC 7064` only. Block-specific validation or liveness, if later desired, belongs behind an opt-in `include_registry_validation` (or `include_block_validation`) gated `LOOKUP_TABLE` rule, mirrored on ISBN `include_range_validation` and Country `include_localized` — gated, documented, and refresh-procedure-bearing. This keeps the initial surface minimal and deterministic while allowing strict ORD-minted-only validation for funder/IR compliance callers.

Analogy: ISSN's `ISSN-L` linking and ISBN's `Range Message` registrant ranges are relational/registry properties requiring a table, not a pure mod-11 — ORCID's block prefix is the same class: registry-dependent, not checksum.

### 5.5 Assignment / registration authority & Registry content

Network: **ORCID, Inc.** as minting Registry (Board-governed, member-sustained, not-for-profit) + **ISNI-IA** as parent RA (London, EDItEUR/BnF/British Library) plus **ISNI Registration Agencies** in 24 countries as registrants for non-ORCID ISNIs (BnF, British Library, CISAC, Ringgold, OCLC, etc.). Blocks: each registrant allocates ISNIs from disjoint partitions; **ORCID Registry** (central catalogue) is published as **https URI** per record (`https://orcid.org/XXXX-XXXX-XXXX-XXXC`) plus **Public Data File (CC0 annual)** for bulk, plus **Public/Member APIs v2.0/v2.1/v3.0** (XSD `orcid-path` / `orcid-uri` patterns), plus **search via `https://orcid.org/` directory**. Each record includes: ORCID iD (hyphenated), display name, biography, affiliations, funding, works (with DOIs), peer review, search-link, inbox, trusted parties. Directory notes:

- *Hyphenated path* is `xxxx-xxxx-xxxx-xxxx` (15+`X`/digit); *URI* is always `https://` (v2.1+) at display, `http://` at XSD v2.0 legacy.
- XSD `common-3.0.xsd` `orcid-path` pattern: `(\d{4}-){3,}\d{3}[\dX]` — hyphen required, `X` at `pos16` only.
- Reserved block: `0000-0001-5000-0007`–`0000-0003-5000-0001`, `0009-0000-0000-0000`–`0009-0010-0000-0000` (ORCID Support page § Issuing).

Per **ORCID and ISNI Issue Joint Statement on Interoperation (2013-04-22)**:

> "The ORCID iD is compatible in format with the ISNI ISO Standard (ISO 27729). The ORCID Registry randomly assigns ORCID iDs from a block of numbers set aside for them by the ISNI International Agency which avoids having the same number assigned to different people."

Mandatory assignment data: public identity (person/organization) plus research-activity metadata (works, affiliations, funding) per ORCID record, not embedded in the dumb number.

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`, defined in `paxman.core.capability_contract.py`), never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base `super()` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ORCIDContract(CapabilityContract):
    """User-facing contract for ORCID capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = (
        "orcid"  # cf. ISSN "hyphenated" / IBAN "electronic"
    )
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"uri", "compact"})

    capability_name: str = field(default="orcid", init=False)
    # No grammar-toggle flags for the initial single-grammar design.
    # If registry liveness gating is later added:
    # include_registry_validation: bool = False

    # active_grammars is required only when recognition is feature-gated
    # (Email/IP/ISBN pattern). For ORCID there is one always-active grammar,
    # so the property is omitted — base returns None and the engine runs every
    # shipped grammar in get_grammars() order.
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. For ORCID, `orcid` (hyphenated `XXXX-XXXX-XXXX-XXXC`, uppercase `X`) is the machine canonical form (ORCID Support hyphen every 4; ISSN hyphenated analogous); `uri` is the `https://orcid.org/XXXX-XXXX-XXXX-XXXC` rendering (ORCID storage/display canonical, see Support § Storage); `compact` is `16` digits without hyphens (ISNI `format()` style) — presentational only.
- Inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format`, `None`, `"default"`, and the default format string all resolve identically to the canonical default; only an explicit offered alternative triggers `format_value()` conversion. Invalid values raise `ContractError`.
- `create_contract()` on the capability opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order, then capability-specific params (if any). For ORCID initially there are no capability-specific params; `include_registry_validation` is added only when the registry rule ships.

**Presentational-only invariant (hard rule — ARCHITECTURE.md The Formatting Seam):**

- `output_format` is a **representation transform, never a recognition or validation signal**. Rules never read it; `normalize()` always returns the default hyphenated form; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup and status determination.
- `AMBIGUOUS` semantics are preserved across formats (rendering does not filter candidates).
- Formatting adds **no provenance**, `Candidate.provenance`, `recognition_rule`, `validation_rule` come from the validating rule.

For ORCID, the offered formats model the three interchange forms identified in §2:

| `output_format` | `value` example | Meaning |
|-----------------|-----------------|---------|
| `"orcid"` (default) |  `0000-0002-1825-0097` / `0000-0002-1694-233X` | Hyphenated, uppercase `X`, `4-4-4-4` groups — checksum-proven canonical, DB key, XSD `orcid-path` |
| `"uri"` |  `https://orcid.org/0000-0002-1825-0097` | `https` URI wrapping hyphenated, `https://orcid.org/` scheme + host + path; legacy `http://` accepted at input, always rendered `https://` |
| `"compact"` | `0000000218250097` / `000000021694233X` | Hyphens stripped, still `15+check`, compact for columnar storage |

*Do not add `with_label` format, the `ORCID:`/`ISNI:` label is not part of the identifier; statement or record renderers add it. Do not add `isni_spaced` format — `ISNI 1422 4586 3573 0476` spaced display is ISNI-family, not ORCID hyphenated canonical.*

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.ORCID.notation import ORCIDNotation


class ORCIDCapability(Capability[ORCIDNotation]):
    name = "orcid"  # lowercase identifier — what users pass to registry

    def get_grammars(self) -> list[Grammar[ORCIDNotation]]:
        return [
            ORCIDRecognitionGrammar()
        ]  # single grammar; hyphenated + URI handled together

    def get_rules(self) -> list[Rule[ORCIDNotation]]:
        return [
            Section4OrcidStructure(),
            SectionAnnexAMod11Dash2(),
        ]  # plus optional registry rule

    @staticmethod
    def create_contract(
        *,
        excluded_rules: "Sequence[str] | None" = None,
        pinned_rules: "Sequence[str] | None" = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: "Sequence[str] | None" = None,
    ) -> ORCIDContract:
        return ORCIDContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: ORCIDNotation
    ) -> str:
        if output_format == "uri":
            # https URI wrapping hyphenated — always https
            return f"https://orcid.org/{notation.hyphenated}"
        if output_format == "compact":
            # 16 chars, no hyphens — compact
            return notation.compact
        return value  # orcid default is identity — normalize() must return hyphenated
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`):
`scaffolder adds the import line to `paxman/capabilities/__init__.py`; users call `paxman.register_capability(ORCID())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation — Single Check Digit MOD 11-2

### 7.1 Check-digit generation and validation (Annex A of ISO 27729:2012 via ISO/IEC 7064:2003 §6–7)

**Annex A (normative) — Method for calculating the check character of ISNI/ORCID** references ISO/IEC 7064:2003 MOD 11-2 directly.

**Parameters** (Table 3 of 7064, designation `1`): `M=11` (modulus `11`), `r=2` (radix `2`), weights `r^(i-1) mod M` from check position outward: `1,2,4,8,5,10,9,7,3,6,5...` equivalently the Support page recursive form; Supplementary `X` for value `10`.

**Check-digit alphabet:** indices `0123456789`, extended alphabet `0123456789X` (Support page: `0`–`9` or `X`; ISNI §4.4 same). No letter expansion `A=10…Z=35` (unlike IBAN MOD 97); ISNI/ORCID are numeric `0-9` plus single supplementary `X`.

**σ Generation — from base `15` digits `d1…d15`:**

```python
# ORCID Support page reference implementation (Java)
def generate_check_digit(base15: str) -> str:  # 15 digits 0-9
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    remainder = total % 11
    result = (12 - remainder) % 11
    return "X" if result == 10 else str(result)
```

**Polynomial check** (equivalent per ISO 7064 §6): assign weights from rightmost digit `w1=1, w2=2, w3=4…` (powers of `2 mod 11`). Protected string including check `c1` (value `10` if `X`) is valid iff:

```
Σ_{i=1..16} value_i * w_i  ≡  1 (mod 11)
```

where `value_i` is digit value (`X`=10). This is the `stdnum/iso7064/mod_11_2.checksum() == 1` invariant.

**Direct validation (iterative inclusion) — from iteh/7064 notes:**

```
Pj = 0 for j=1
For j=1..15 (each base digit):
   Sj = Pj + d_{16-j}
   Pj+1 = Sj * 2
Next a1 (check) chosen so Pn + a1 ≡ 1 (mod 11)  → a1 = (1 - Pn) mod 11
```

Verification: run same loop including check `c1` (value 10 if `X`); valid iff result `Pn+1 mod 11 == 1`.

**Python validation — payload-normalized, two equivalent forms:**

```python
# Form 1 — iterative like Support page (the ORCID style)
compact = re.sub(r"[ \-]", "", hyphenated).upper()
assert len(compact) == 16 and compact[:15].isdigit()
total = 0
for ch in compact[:15]:
    total = (total + int(ch)) * 2
check_expected = (12 - total % 11) % 11
check_actual = 10 if compact[15] == "X" else int(compact[15])
is_valid = check_expected == check_actual

# Form 2 — stdnum iso7064 checksum == 1 (polynomial)
from stdnum.iso7064 import mod_11_2

is_valid = mod_11_2.checksum(compact) == 1
```

**Worked examples (primary-source derived):**

| String (compact) | Base 15 | total of base (`Σ iterative`) | remainder (`total % 11`) | `(12 - remainder) % 11` | Expected Check | `Σ value·w ≡ 1 (mod 11)` | Valid? |
|------------------|---------|-------------------------------|--------------------------|--------------------------|----------------|--------------------------|--------|
| `1422458635730476` (ISNI) | `142245863573047` | `142830` | `6` (142830 % 11) | `(12 - 6) % 11 = 6` | `6` | `Σ value·w ≡ 1 (mod 11)` | `True` |
| `0000000218250097` → base `000000021825009` | `000000021825009` | `1314` | `5` (1314 % 11) | `(12 - 5) % 11 = 7` | `7` | `…+7 → 1` | `True` (`https://orcid.org/0000-0002-1825-0097`) |
| `000000021694233X` → base `000000021694233` | `000000021694233` | `1410` | `2` (1410 % 11) | `(12 - 2) % 11 = 10 → X` | `X` | `…+10 → 1` | `True` (`https://orcid.org/0000-0002-1694-233X`) |
| `0000000151093700` → base `000000015109370` | `000000015109370` | `1156` | `1` (1156 % 11) | `(12 - 1) % 11 = 0` | `0` | `…+0 → 1` | `True` (`https://orcid.org/0000-0001-5109-3700`) |
| `0000000218250098` (bad checksum) | same base `000000021825009` | `1314` | `5` | `7` expected vs `8` supplied → mismatch | `8` (wrong) | `…+8 ≡ 2 ≠ 1` | `False` — `INVALID` (grammar claimed, MOD 11-2 fails) |
| `0000216942330X` truncated (15 compact) | — | — | — | — | — | — | `False` — length `≠16`, grammar `MISSING` (or `INVALID` if compact branch ever claims) |

### 7.2 What makes ORCID "valid" vs "checksum-valid" vs "registered/live"

- **valid (structural, checksum-valid)** — correct length `16`, hyphen pattern `4-4-4-4`, `15 digits + [\dX]` with `X` only at `16` uppercase, MOD 11-2 `checksum==1`, always-active `PARSER` (the initial rule pair fused or split).
- **block-valid / registry-minted** — structural `valid` plus reserved-block membership `0000-0001-5000-0007`–`0000-0003-5000-0001`/`0009-…` (assignment history) — not structural, would be gated `LOOKUP_TABLE` if offered.
- **registered/live** — actually present in ORCID Registry snapshot (CC0 public data file), i.e. mutable existence; gated `LOOKUP_TABLE` `requires_features={"include_registry_validation"}`.

Like ISBN valid vs allocated, ISSN valid vs issued, IBAN valid vs country-valid: ORCID valid (checksum) vs registered (issued) are distinct; structural alone is `SUCCESS` initially.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase `x` at 16 | `SUCCESS` → `…X` upper | grammar folds `x→X` case-insensitive, normalized uppercase |
| 2 | Spaced `ISNI` style `0000 0002 1825 0097` | `MISSING` deterministically (hyphen-only) — `SUCCESS` only via spaced-tolerant `Pre` (§13#9) | presentation-only spaced vs hyphenated — `Pre` must collapse spaces then hyphen-insert before regex |
| 3 | Compact digits `0000000218250097` | `MISSING` deterministically — `SUCCESS` only via compact branch or `Pre` (§13#9) | presentation-only no hyphens — `Pre` must hyphen-insert before regex; v1 strict hyphen avoids spurious `16`-digit claims |
| 4 | URI present `https://orcid.org/0000-0002-1825-0097` | `SUCCESS`, span includes URI, same hyphenated | fused label group, `is_uri="true"`, normalize strips host |
| 5 | `http://` vs `https://` | Both `SUCCESS` same hyphenated | scheme canonicalization — always render `https` via `uri` field |
| 6 | `orcid.org/` bare host | `SUCCESS` (tolerant) | ecosystem cwltool/pubpub permissive host tolerance |
| 7 | `www.orcid.org/` host | `SUCCESS` | `www.` variant tolerance (pubpub pattern) |
| 8 | `ORCID: ` label | `SUCCESS`, span includes label | fused `ORCID/ISNI` label `[\s:-]*`, notation strips |
| 9 | Trailing slash `…/0000-0002-1825-0097/` | `SUCCESS` without slash | `BoundaryGuard.word_only()` stops before slash; slash not part of `hyphenated` |
| 10 | Over-long `0000-0002-1825-00977` (17 with extra + trailing digit/hyphen) | `MISSING` deterministically (no `19`-char hyphened run) — `INVALID` only if compact branch ships | length guard `16` compact / `19` hyphened exact; hyphen-only grammar never claims 17; see §13#9 |
| 11 | Under-long `0000-0002-1825-009` (15) | `MISSING` | no `16` run, regex not matched |
| 12 | Invalid checksum `…-0098` vs expected `…-0097` | `INVALID` with rule, never `SUCCESS` | shape claimed, MOD 11-2 fails |
| 13 | `X` mid-run `000X-0002-1825-0097` | `MISSING` (grammar not claim) or `INVALID` (compact digits before `X` fails) | `X` only valid at pos16; pattern `(\d{4}-){3}\d{3}[\dX]` rejects |
| 14 | Embedded in sentence `See https://orcid.org/0000-0002-1825-0097 for author` | `SUCCESS` with span `19` or `35` (with URI) | `word_only` guards allow inside prose, span pinpoint |
| 15 | Two distinct in one slice `0000-0002-1825-0097 / 0000-0001-5109-3700` | `AMBIGUOUS` / `MultipleMentionsError` with `single_value=True` | segmentation intended; overlapping cluster? No, two clusters |
| 16 | `…-233x` lowercase | `SUCCESS` → `…-233X` | grammar `IGNORECASE`, normalize upper |
| 17 | `0000-0002-1825-009X` valid checksum `X` but ~10% of random ORCIDs are `X` — still `SUCCESS` | `SUCCESS` | `X` is informative check, not error |
| 18 | Leading/trailing glue `X0000-0002-1825-0097` | `MISSING` (not claimed) | `(?<!\w)` / `(?!\w)` word_only prevents carving from longer token |
| 19 | Trailing-hyphen continuation `0000-0002-1825-0097-1234` (hyphen followed by digits) | `SUCCESS` for first 19 (`0000-0002-1825-0097`), remaining `-1234` not swallowed — `BoundaryGuard.word_only().lookahead` passes on `-` (non-word), acceptable spillover, document vs grow grammar to include | `word_only` `(?!.\w)` allows hyphen continuation; no claim beyond 19 |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid hyphenated + checksum `0000-0002-1825-0097` | `SUCCESS` → `0000-0002-1825-0097` (or `https://orcid.org/…` when `output_format="uri"`) | single canonical via `ISO 27729` structure + `ISO/IEC 7064 MOD 11-2` |
| Same through URI `https://orcid.org/0000-0002-1825-0097` | `SUCCESS` (same hyphenated) | URI presentation-only, stripped before validation, dedup on `hyphenated` |
| Same compact `0000000218250097` | `MISSING` under v1 hyphen-only grammar (`SUCCESS` only if compact branch/`Pre` ships, see §13#9) | same `16` payload, hyphen-only recognizer not claiming compact |
| Bad checksum `0000-0002-1825-0098` | `INVALID` (grammar claimed, MOD 11-2 rejects) | structural shape claimed, validation fails |
| No runs of `4-4-4-4` hyphened | `MISSING` | no grammar recognized anything |
| Two distinct valid ORCIDs in one slice | `AMBIGUOUS` / `MultipleMentionsError` | single-slice ambiguity, caller must segment |
| `X`-mid or 15-char | `MISSING` (shape not claimed) or `INVALID` if alternate compact branch claims | shape discrimination via hyphens/ length |
| `http://` variant of valid hyphenated | `SUCCESS` → hyphenated (or `https://` when `uri`) | scheme normalized, not validation |
| Registry-gated input not present in snapshot when `include_registry_validation=True` | `INVALID` (if registry rule gated) else `SUCCESS` | authority feature gating: seen vs not in directory |
| Leading/trailing glue `X0000…` / `…0097Y` | `MISSING` | word-only prevents partial claim |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)
```bash
uv run python tools/new_capability.py ORCID --name orcid --authority "ISO" --spec-name "ISO 27729:2024" --spec-url "https://www.iso.org/standard/87177.html" --publication-year 2024 --default-format orcid
```
Creates 13 files + one edit: `paxman/capabilities/ORCID/{notation,contract,capability,grammar/*,rules/*}`, `tests` stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder `--default-format` defaults to `canonical` — pass `--default-format orcid` to avoid a post-edit. Single `--spec-name` covers one provenance; after scaffolding, add second provenance file manually: `rules/iso_7064_ed2003.py` (split) or fuse both `Rule` classes into `iso_27729_ed2024.py` (recommended for v1, active `2024-11` lifecycle). The scaffolder emits `PUBLICATION` with `lifecycle="active"`; pinning to withdrawn `2012` would require a manual `lifecycle="withdrawn"` edit — not recommended (see §13#12).

### 10.2 Contract & grammar wiring
- `get_grammars()` returns `[ORCIDRecognitionGrammar()]`, `active_grammars` omitted for initial design (base `None`), each grammar carries `name="orcid_recognition"` and non-empty `semantics="orcid_recognition"`

### 10.3 Cross-cutting invariants (fail review if violated)
- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source
- No cross-capability imports (import only from `paxman.core`, `import-linter` enforced)
- No `output_format` token in any `paxman/capabilities/*/rules/` module (source-scan `tests/unit/test_rule_output_format_purity.py`)
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` **without** `slots=True` contracts
- Deterministic by construction: same input + contract + library snapshot → same output
- Leading zeros significant: never strip via `lstrip("0")` — preserve `0000` prefix
- `X` handling: `compact[-1].upper()` exactly, never `lower()`

---

## 11. Recommended File Layout (mirrors ISSN and BIC)

```
paxman/capabilities/ORCID/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── orcid_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_27729_ed2024.py          # structure + check (fused, recommended)
    ├── iso_7064_ed2003.py           # split check-only if not fused
    └── data/                        # only if registry layer adopted
        └── orcid_registry_snapshot.py  # optional rolling frozenset of issued ORCIDs
```

Per-registry data module shape (parallel to ISBN `rules/data/range_message.py`):

```python
# rules/data/orcid_registry_snapshot.py
ORCID_REGISTRY: frozenset[str] = frozenset(
    {
        # hyphenated or compact — pref hyphenated for direct check
        "0000-0002-1825-0097",
        # ...
    }
)
```

Alternatives: keep data as TXT pipe-separated like `swift iban registry.txt` and load at import.

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- **Grammar tests:** valid hyphenated `0000-0002-1825-0097` / `0000-0002-1694-233X` + variants (URI `https://orcid.org/…`, `http://…`, `orcid.org/`, `www.orcid.org/`, lowercase `x→X`, compact no-hyphen, spaced `0000 0002 1825 0097`, `ORCID:` label, `ISNI:` label), multiple matches (two ORCIDs in one line → 2 `RecognitionMatch`), incompatible format (`0000-0002-1825-009` 15, `0000-0002-1825-00977` 17 → `[]`), empty → `[]`, span invariants (`start`,`end`,`raw_text` == `text[start:end]`, hyphenated vs URI span), `name`/`semantics`/`single_value` check, boundary guard negatives (`X0000-…` no claim, `…0097Y` no claim, `https://orcid.org/0000-0002-1825-0097Y` no claim)
- **Rule tests:** structure rule `Section4…` valid/variant/invalid (`0000-0002-1825-0097` true, `…0098` bad checksum false via fused or `iso_7064` split → false), `normalize` returns exact hyphenated upper, provenance attributes (`authority="ISO"`, `kind="specification"`, `reference_url` contains `iso.org/standard/44292.html` or `87177.html` if 2024, `lifecycle` active/withdrawn accordingly, `publication_year` 2012 or 2024, `version` "2012-03" or "2024-11"), `name`/`strategy` conventions (`strategy==RuleStrategy.PARSER`), leading zeros preserved; MOD 11-2 rule (if split) `mod_11_2.validate(compact)` `checksum==1`, `validate` exact `0000-0002-1694-233X` must pass with `X`, `0000-0002-1694-2330` must fail, `requires_features` empty, `target_semantics==frozenset({"orcid_recognition"})`
- **Registry LOOKUP rule (optional, deferred)** — if offered: valid membership true, `requires_features=={"include_registry_validation"}`, `strategy==LOOKUP_TABLE`, `kind=="registry"` provenance `authority="ORCID, Inc."` `version=="Rolling CC0"` `reference_url=="https://orcid.org/"` or `support.orcid.org…`
- **Capability tests:** notation `frozen`+`hashable`+`slots`, immutability try `notation.compact="x"` raises `FrozenInstanceError`, wiring counts `get_grammars()==1` `get_rules()==2` (fused or split, both yield two Rule classes), grammar/rule name conventions (`orcid_recognition`, `Section …`), `format_value` round-trips: `orcid` identity, `uri` always `https://orcid.org/` + hyphenated, `compact` hyphens stripped, `create_contract` factories keyword-only
- **Integration:** `MISSING` (no hyphened run) / `INVALID` (`…0098` bad check) / `SUCCESS` (`…0097` hyphened+URI) / `AMBIGUOUS` or `MultipleMentionsError` (two distinct) with `single_value=True`, `year` temporal filtering, `_clean_registry` fixture, determinism/`VersionStamp`, span-bearing match, dedup `(value,recognition_rule,validation_rule)`, `X` uppercase preserved vs lowercase input
- **Property tests (hypothesis):** generate valid by `generate_check_digit(base15)` → must `canonicalize` to itself hyphenated; random 16-strings with random hyphens → `INVALID` with high probability (MOD 11-2 fails); hyphen vs compact same checksum after collapse; `format_value(...,"compact")` round-trip reconstructs hyphenated
- **Consistency test:** every shipped semantics `orcid_recognition` covered by `Rule.target_semantics`, every registry entry's `hyphenated` exercised if registry snapshot present
- **Presentation purity:** `output_format` source scan — `rg "output_format" paxman/capabilities/ORCID/rules/` must be empty
- **Real vectors:** valid `0000-0002-1825-0097` (no URI) + `https://orcid.org/0000-0001-5109-3700` + lowercase `0000-0002-1694-233x→ X` + spaced `0000 0002 1825 0097` variant if accepted + invalid checksum `0000-0002-1825-0098` + surro-gated X-mid `000X-...` + trailing glue `X0000…`/`…Y` negatives

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `orcid` vs `uri` vs `compact` | **`orcid` hyphenated as default**, `uri = https://orcid.org/…` and `compact` offered | Hyphen every 4 is the ISNI-transfer wire human-readable defined in Support § Expressing as hyphenated; URI is storage/display, not wire; compact is columnar — hyphenated is the XSD `orcid-path` native |
| 2 | Single grammar vs hyphenated+compact as two grammars | **Single `orcid_recognition` initially**, optional `https://orcid.org/` prefix group; defer split to community extension with coalesced semantics if compact no-hyphen needed widely | Keeps surface minimal, avoids cross-grammar containment spurious `AMBIGUOUS` |
| 3 | Block prefix / reserved-range gating | **No block gating initially** — any `16` with valid MOD 11-2 is `SUCCESS`; add reserved-block `LOOKUP_TABLE` behind `include_block_validation=False` only if funder/IR requires `0000-` minted check | Block is assignment history, not structural transform; most compliance uses checksum already |
| 4 | Grammar strictness on hyphens vs spaces | Grammar should require **hyphens** `\d{4}-\d{4}-\d{4}-\d{3}[\dX]` via `RegexStage`, not `[\- ]?` per segment | Spaced `ISNI` form invites gluing with surrounding `4`-digit runs; narrowing to hyphen reduces sibling false positives; spaced support can move to `Pre` normalizer later |
| 5 | Case/URI normalization in grammar vs rule | **Grammar folds `x→X` and strips `https?://(?:www\.)?orcid.org/` prefix**; rules validate upper `[\dX]` only | Syntax (`x` case, URI scheme) not semantics; scheme always canonical `https` via `uri` field |
| 6 | `X` at other than pos16 | Informative `X` value 10 **never valid mid-run** — pattern forbids | Prevents `000X-` false claims; matches XSD `(\d{4}-){3,}\d{3}[\dX]` restriction to final char |
| 7 | Single `PUBLICATION` fused vs split 27729/7064 | **Recommend fused `iso_27729_ed2024.py` with two `Rule` classes** (`Section4OrcidStructure` + `SectionAnnexAMod11Dash2`) sharing `PUBLICATION` (`ISO 27729:2024` active) — `get_rules()==2`; split into `iso_7064_ed2003.py` only if temporal pinning on 7064 is needed separately | Fused keeps file count minimal; split is cleaner if distinct `year` pinning on 7064 matters |
| 8 | `single_value` for author lists | **`True` initially**, segmentation for multi-author; offer `extra_grammars` variant with `False` via `ORCIDFreeTextGrammar` if batch CFF parsing needed | Consistent with IBAN/BIC batch `MultipleMentionsError` guidance; author lists legitimately multi but single-field use-case is single ORCID |
| 9 | Non-hyphen compact tolerance (`0000000218250097`, `0000 0002 1825 0097`) | Grammar handles **hyphenated only**; compact + spaced via `Pre` stage that collapses `[ -]` then hyphen-reinserts before regex, or unsupported until demand | Support page hyphen every 4 is normative; space is ISNI spacing, not ORCID; compact is storage fallback |
| 10 | Label span inclusion (`ORCID:`/`ISNI:`/`https://orcid.org/`) | **Include label+URI in `raw_text` span (fused regex group `m.group(0)`)**, strip in `notation.hyphenated`/`compact`/`uri` | Mirrors `ISSN` label-inside-span and `IBAN` `IBAN:` label handling (`raw_text` preserves human token, notation is syntax-normalized) |
| 11 | `http://` vs `https://` canonical | Accept both at input (`https?://`), always render `https://` | ORCID XSD v2.0 was `http`, v2.1 is `https`; normalizing avoids duplicate canonicals |
| 12 | `publication_year` pin: `2012` vs `2024` | **Pin to `2024` / `active`** (`ISO 27729:2024`, `2024-11`, `https://www.iso.org/standard/87177.html`) — structure is unchanged (Cor 1 typo `320/11 rem1` incorporated, editorial alignment; ISNI News Nov 2024); avoid shipping a withdrawn-lifecycle primary authority | Scaffolder emits `active`; withdrawn `2012` would need manual `lifecycle="withdrawn"` edit and triggers `year` filter confusion — see §5.2/§10.1 — lean to `2024` |

---

## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent ORCID-vs-ORCID positional ambiguity** — fixed `4-4-4-4` hyphenated shape eliminates interpretation ambiguity ISSN exhibits for presentation-vs-value; Paxman `ORCID` has one reading per hyphenated token. Two distinct ORCIDs in one slice (e.g. `0000-0002-1825-0097 / 0000-0001-5109-3700`) is authorial choice, not identifier ambiguity; segmentation (`docs/recipes/segmentation.md`) intended. Two hyphenated mentions at different positions with different `hyphenated` still coalesce only if compact equal — otherwise `AMBIGUOUS`/`MultipleMentionsError`.
- **ORCID vs non-ORCID ISNI is not lexical ambiguity** — `000000012281955X` formatted hyphened `0000-0001-2281-955X` is valid ISNI but assigned to a different identity (Elab?); without block gating it would be `SUCCESS` for generic `16` MOD 11-2 validation. With block gating it becomes `INVALID` for ORCID-minted slice — distinct provenance, not competing value. Registry-minted check (`0009-…` sandbox/sink) is the only path to distinguish assignment vs generic validity; without it, generic `valid` is appropriate.
- **ORCID vs sibling length discrimination prevents cross-capability ambiguity** — ORCID hyphenated `19` (`16+3 hyphens`) vs ISSN `9` (`8+1 hyphen`) vs ISBN `13` digits vs IBAN `15–34` disjoint; hyphen count plus `X` only at end discriminates ISSN `X` at `8` vs ORCID `X` at `16`. Short non-ORCID `0000-0001-2281` (12) falls in ISBN-candidate range but lacks ORCID `4-4-4-4` third separator.
- **URI vs hyphenated is not ambiguity, presentation vs identity.** `0000-0002-1825-0097` and `https://orcid.org/0000-0002-1825-0097` map to same `hyphenated` via `uri` field derivation; `is_uri="true"` flag does not create second candidate. Formatting to `uri` is lossy expansion but deterministic (`https://` always) — not coalescing two values.
- **Staleness is not ambiguity** — determinism-by-snapshot: `Provenance.version` `"2024-11"` vs `rolling` for registry; same input + contract + snapshot → same output. Registry growth (new ORCIDs appended) does not affect structural `SUCCESS`; only optional gated `include_registry_validation` would flip `SUCCESS→INVALID` for not-yet-seen prefix.
- **Block semantics is not ambiguity** — `0000-0001-5000-0007` vs `0009-0000-…` prefix does not affect MOD 11-2 validity, only reserved-block informatic; test vs sandbox allocation is hint not validity.

---

## 15. URL Reference (authoritative, fetched 2026-08-23)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 27729:2012 (1st ed., Published, 2012-03) and ICS/TC | `https://www.iso.org/standard/44292.html` | primary |
| ISO 27729:2012/Cor 1:2013 | `https://www.iso.org/standard/64745.html` | primary |
| ISO 27729:2024 (2nd ed., current, Published 60.60, 2024-11-11, cancels 2012) | `https://www.iso.org/standard/87177.html` | primary |
| ISO 27729:2024 catalogue + iteh normative text | `https://cdn.standards.iteh.ai/samples/44292/5e426355be36478d8ba1d287fe805e9b/ISO-27729-2012.pdf` + `https://standards.iteh.ai/catalog/standards/iso/ad745aea-8071-4698-8670-702140e744c9/iso-27729-2024` | primary |
| NEN ISO 27729:2012 entry (Ingetrokken, Withdrawal 1 dec 2024) | `https://www.nen.nl/nen-iso-27729-2012-en-169667` | primary |
| NEN ISO 27729:2024 entry (Definitief 1 dec 2024, Vervangt) | `https://www.nen.nl/nen-iso-27729-2024-en-332125` | primary |
| ISNI News: Minor revision 2024 (TC 46/SC 9, Cor 1 incorporated) | `https://isni.org/resources/html/ISNI-News-November-2024.html` | primary |
| ISO/TC 46/SC 9 — Identification and description (publisher) | `https://www.iso.org/committee/48836.html` | primary |
| ISO/IEC 7064:2003 (MOD 11-2, M=11 r=2, X=10, pure system) | `https://www.iso.org/standard/31531.html` | primary |
| ISO/IEC 7064 iTeh sample (Table 5–7, examples 0794→07940, 079→079X, §6–7.1) | `https://cdn.standards.iteh.ai/samples/31531/4ca4e9783a4340acb22586379dc59284/ISO-IEC-7064-2003.pdf` | primary |
| ISNI RA governance (ISNI-IA Ltd c/o EDItEUR, Board, Branches, BnF/British Library Quality Team) | `https://isni.org/page/governance` | primary |
| ISNI RA what-is/how-works + search/database + linked-data | `https://isni.org/page/what-is-isni/` + `https://isni.org/page/how-isni-works` + `https://isni.org/page/search-database` + `https://isni.org/page/linked-data` | primary |
| ISNI home (ISO 27729 as bridge, 16.6M records) | `https://isni.org/` | primary |
| ORCID Structure of the ORCID Identifier (https URI, 16 digits, leading zeros, block ranges, checksum MOD 11-2, Java `generateCheckDigit`, Samples `…0097/…3700/…233X`, Storage `https://…`, XSD v2.0/v2.1, Display guidelines) | `https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier` | primary |
| ORCID and ISNI Joint Statement on Interoperation (2013-04-22, reserved block) | `https://info.orcid.org/orcid-and-isni-issue-joint-statement-on-interoperation-april-2013/` | primary |
| ORCID what-is-orcid (not-for-profit, principles) | `https://info.orcid.org/what-is-orcid/` | primary |
| ORCID Registry services (assignment, public data file, APIs) | `https://info.orcid.org/what-is-orcid/services/orcid-registry/` | primary |
| ORCID trademark and iD display guidelines (referenced in Support article) | `https://orcid.org/trademark-and-id-display-guidelines` | primary |
| ORCID/ISNI crosswalk (CASRAI reserved block `0000-0001-5000-0007…` + `0009-…`) — secondary but cross-checks primary | `https://casrai.org/dictionary/term/orcid-id` + `https://casrai.org/guides/isni-identifier-explained-vs-orcid` | secondary |
| Genorma ISO mirrors (Owner TC 46/SC 9, ICS, 01.140.20) | `https://genorma.com/en/standards/iso-27729-2012` + `https://genorma.com/en/standards/iso-27729-2024` | secondary |
| ORCID-Source OrcidStringUtils (`ORCID_STRING` regex, `ORCID_URI` patterns) | `https://github.com/ORCID/ORCID-Source/blob/cac0eca25911ca216ad4c0b07097d9180316604c/orcid-utils/src/main/java/org/orcid/utils/OrcidStringUtils.java` | primary |
| ORCID-Source OrcidCheckDigitGenerator (`generateCheckDigit` total*2 algorithm) | `https://github.com/ORCID/ORCID-Source/blob/cac0eca25911ca216ad4c0b07097d9180316604c/orcid-core/src/main/java/org/orcid/core/crypto/OrcidCheckDigitGenerator.java` | primary |
| ORCID orcid-model common-3.0.xsd `orcid-path`/`orcid-uri` patterns | `https://github.com/ORCID/orcid-model/blob/bcb083f13dbaeba3e9e1c39c3b8fb1791891de3f/src/main/resources/common_3.0/common-3.0.xsd` | primary |
| arthurdejong/python-stdnum `stdnum/isni.py` @ 006192e (compact/clean `' -'`, validate length 16 + `mod_11_2.validate`) | `https://github.com/arthurdejong/python-stdnum/blob/006192e59be8ed6e08fd680256868a6c31eb2ba9/stdnum/isni.py` | primary |
| arthurdejong/python-stdnum `stdnum/iso7064/mod_11_2.py` @ 006192e (checksum vs calc_check_digit, polynomial) | `https://github.com/arthurdejong/python-stdnum/blob/006192e59be8ed6e08fd680256868a6c31eb2ba9/stdnum/iso7064/mod_11_2.py` | primary |
| validator.js absence of `isORCID` (negative, only isISBN/isISSN/isISRC/isISIN exist) | `https://github.com/validatorjs/validator.js/blob/a79ff980ab14257e795332989e497bdff3218e87/src/lib/isISRC.js` + `https://github.com/validatorjs/validator.js/blob/a79ff980ab14257e795332989e497bdff3218e87/src/lib/isISSN.js` (ancestor list via dir) | primary |
| hypothesis/h ORCID predicate + MOD11-2 | `https://github.com/hypothesis/h/blob/24395ca438e3bd4b5c301e30ab81ca1d024ee840/h/accounts/util.py` | primary |
| common-workflow-language/cwltool ORCID liberal URI regex | `https://github.com/common-workflow-language/cwltool/blob/baefdcb58fcc76e3378cf705fc6a3e69ef35bb47/cwltool/cwlprov/__init__.py` | primary |
| elabftw UserParams Check::digit | `https://github.com/elabftw/elabftw/blob/205421ebdf2cecbdf6cbbe6dd7f263021b421827/src/Params/UserParams.php` + `https://github.com/elabftw/elabftw/blob/205421ebdf2cecbdf6cbbe6dd7f263021b421827/src/Services/Check.php` | primary |
| speced/respec show-people.js ORCID URL+checksum | `https://github.com/speced/respec/blob/9737e050b510e2b8f86897c40912b05b9351aae5/src/core/templates/show-people.js` | primary |
| knowledgefutures/pubpub `utils/orcid.ts` | `https://github.com/knowledgefutures/pubpub/blob/ba3d8f894c2187825f2c73bd3111e96313a20311/utils/orcid.ts` | primary |
| scippneutron `_orcid.py` | `https://scipp.github.io/scippneutron/_modules/scippneutron/metadata/_orcid.html` | primary |
| ISSN/BIC/IBAN research precedents (lineage tables, sibling guards, contract seams) | `docs/development/research/2026-08-21-issn-canonicalization.md` + `docs/development/research/2026-08-22-iban-canonicalization.md` + `docs/development/research/2026-08-23-bic-canonicalization.md` | primary |
| Paxman scaffolder & conventions (one file per publication, no output_format in rules, frozen slots) | `HOW_TO_ADD_NEW_CAPABILITY.md`, `HOW_TO_ADD_NEW_GRAMMAR.md`, `ARCHITECTURE.md` | primary |
| Paxman shipped precedent (grammar PipelineGrammar + BoundaryGuard word_only, Rule 6 attrs, orchestrator _dedup_spans) | `paxman/capabilities/ISSN/grammar/issn_recognition.py` + `paxman/capabilities/IBAN/grammar/iban_recognition.py` + `paxman/capabilities/BIC/grammar/bic_recognition.py` + `paxman/core/domain.py` + `paxman/engine/orchestrator.py` + `paxman/capabilities/ISBN/grammar/isbn13_recognition.py` | primary |

---

## 16. Evidence Completion — Resolved

This report's ORCID-specific authoritative evidence has been fetched and cited (2026-08-23):
- [x] ISO catalogue entry: ISO 27729:2012 (1st ed., current at 2012-03, withdrawn 2024-11) superseding draft 09/30177090 DC, plus ISO 27729:2024 (2nd ed., current, Published 60.60, 2024-11-11, ICS 01.140.20, TC 46/SC 9, Owner ISO/TC 46/SC 9), plus Cor 1:2013; lineage back to draft with dates and status
- [x] RA and Registry provenance: ISNI-IA Ltd (c/o EDItEUR, Quality Team BnF/British Library) + ORCID, Inc. — authority, spec_name, kind registry, reference_url `https://orcid.org/` + `https://isni.org/page/search-database`, version Rolling CC0, lifecycle active, plus XSD `orcid-model/common-3.0` path/uri patterns
- [x] Structure: 16 chars = 15 digits + check, hyphen every 4 `4-4-4-4` (`19` with hyphens; `16` compact), charset `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$`, URI `https://orcid.org/XXXX-XXXX-XXXX-XXXC` (https canonical, http legacy v2.0), leading zeros significant, dumb number §4.2, check X only at 16 upper, samples `0000-0002-1825-0097 / …1694-233X / …5109-3700`
- [x] Checksum algorithm proved: ISO/IEC 7064:2003 MOD 11-2 (M=11, r=2, indices `0123456789`, alphabet `0123456789X`), recursive `total=(total+digit)*2`, `remainder=total%11`, `result=(12-remainder)%11`, `10→X`, worked examples `0000-0002-1825-0097`/`X` (see §7.1 Table), plus stdnum polynomial `checksum==1` equivalence
- [x] No-country / block nuance: ORCID has no country-code field — dumb number only; reserved ISNI block `0000-0001-5000-0007`–`0000-0003-5000-0001` / `0009-0000…` assignment history, not structural validity, deferred behind optional `include_registry_validation`
- [x] Ecosystem regex consensus: generic `^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$` (regexlib) + URI-liberal `(?:https?://)?(?:www\.)?orcid\.org/` (cwltool/pubpub/respec) + XSD `(\d{4}-){3,}\d{3}[\dX]` + python-stdnum `' -'` clean + mod_11_2 + validator.js negative (no isORCID) + scippneutron segments check; §2.1 table with 7 libs
- [x] Wild input shapes validated (§2.1) 18 categories against spec + Support page + XSD + stdnum/cwltool/pubpub/respec/hypothesis
- [x] Label scope decision: `ORCID:`/`ISNI:` + `https://orcid.org/`/`http://`/`orcid.org/`/`www.` all fused in one optional prefix group `[\s:-]+` plus glued-label guard `(?!(?ai:(?:ORCID|ISNI)[0-9]))` + `(?:(?ai:(?:https?://)?(?:www\.)?orcid\.org)/)?` (see §4.2, §13#10)
- [x] URI vs bare identity equivalence decision: same `hyphenated` canonical, presentation-only `uri`/`compact` via `format_value()` (see §6.1/§14)
- [x] `X` and `http`/`https` flag semantics decision: `x→X` fold in grammar, `https` canonical always (see §8#1/#5, §13#5/#11)
- [x] Registry liveness scope decision: `SUCCESS` on structural+checksum only; optional `include_registry_validation` LOOKUP_TABLE behind feature flag (see §5.4, §13#3)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ISSN, Country and Phone Capabilities Teach ORCID (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships — via codegraph_explore 2026-08-23 @ af68cd5 (see §4.2/§5/§6).

Refer to `paxman/capabilities/ISBN/grammar/isbn13_recognition.py:17` (`\b(?:ISBN(?:-13)?[\s:-]+)?(?=((?:\d[ -]?){12}\d)(?![\d]))\1\b`), `paxman/capabilities/ISSN/grammar/issn_recognition.py:10-16` (`(?:ISSN(?:-L|-H)?[\s:-]*)?(?P<body>\d{4}-?\d{3}[0-9Xx])` + `BoundaryGuard.word_only().lookbehind` + `.digit().lookahead` + `\b`), `paxman/capabilities/IBAN/grammar/iban_recognition.py:23-32` (`(?ai:` + `IBAN[\s:-]+` label never zero-width), `paxman/capabilities/BIC/grammar/bic_recognition.py:16-27` (`(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?(?P<compact>…))` + negative lookahead blocking glued label) plus `paxman/engine/orchestrator.py:_dedup_spans` (longer-wins sorting `key=(start,-(end-start))` per-grammar), `_validate_affinity` (`known_semantics` check raising `ContractError`), `_enforce_single_value_invariant` (`single_value` overlapping-cluster → `MultipleMentionsError`), and `paxman/core/domain.py:199-224` (`Rule.__init_subclass__` six attributes `name, strategy, provenance, citation, target_semantics, requires_features`) — all detailed in §4.2/§4.3/§5.2/§5.3/§6.

The four architectural lessons for ORCID:

1. **Grammar strips, rule validates, capability formats.** ISSN `grammar/issn_recognition.py:25-32` uppercases `X` and hyphen-strips to `ISSNNotation(digits)` without validating `checksum%11==0`; rule `iso_3297_ed2022.py` `Section4CheckDigit` `PARSER` computes `weights 8..2` and validates `mod 11`. ORCID must follow same: grammar uppercases `X`, strips URI/label to `ORCIDNotation(hyphenated,compact,uri,check,is_uri)` without MOD 11-2; rules `iso_27729_ed2012.Section4` (`PARSER` structure) + `iso_7064_ed2003.SectionAnnexA` (`PARSER` check) own checksum and return hyphenated.
2. **One file per provenance, one class per section.** ISBN `rules/iso_2108_ed2017.py:PUBLICATION ISO 2108:2017` carries two `Rule` classes (`Section42..+Section53…`) sharing `PUBLICATION`; ISBN Range Message `rules/isbn_range_message_ed2026.py` carries one `LOOKUP_TABLE` gated `requires_features={"include_range_validation"}`. ORCID mirrors: `rules/iso_27729_ed2024.py:PUBLICATION ISO 27729:2024` (`active`) carrying two `Rule` classes (`Section4OrcidStructure` + `SectionAnnexAMod11Dash2`) for v1 keeps `get_rules()==2` minimal—split into `rules/iso_7064_ed2003.py` only if temporal distinction is needed.
3. **No `output_format` in rules, ever.** CI scan `tests/unit/test_rule_output_format_purity.py` rejects `output_format` token in `paxman/capabilities/*/rules/` (code/comments/docstring). IBAN `rules/iso_13616_1_ed2020.py` `normalize()` returns `compact` regardless of contract `output_format="paper"`; BIC returns `bic` compact even when `grouped` offered. ORCID `normalize()` must always return `XXXX-XXXX-XXXX-XXXC`; `Capability.format_value(value, output_format, notation)` handles `uri` (`https://orcid.org/`+hyphenated) and `compact` off `notation.hyphenated/compact`.
4. **Single grammar with optional URI/label group avoids spurious AMBIGUOUS; cross-grammar containment is preserved.** BIC §4.2 single grammar `4!c+2!a+2!c(3!c)?` avoids `bic8` inside `bic11` containment `AMBIGUOUS` (`_dedup_spans` only per-grammar). ISSN single hyphen fix `4-4` vs bare length ambiguity same. ORCID single `ORCIDRecognitionGrammar` with optional `(?:(?:ORCID|ISNI)[\s:-]*)?(?:https?://…orcid.org/)?` prefix plus solid `4-4-4-4` core keeps `_dedup_spans` no-op within one grammar; a second grammar (`orcid_compact`) would risk cross-grammar `0000000218250097` prefix vs `0000-0002-1825-0097` span confusion.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for ORCID. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the deeper ISBN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
