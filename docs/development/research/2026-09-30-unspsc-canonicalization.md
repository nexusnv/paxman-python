# UNSPSC Canonicalization Research — paxman-python

**Date:** 2026-09-30
**Scope:** Primary-source survey of the UNSPSC standard (United Nations Standard Products and Services Code, owner UNDP, current release v26.0801 2023-08-14, no ISO edition, no checksum), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `UNSPSC` capability. No source code, tests, or configuration were modified.
**Evidence basis:** UNDP owner page (undp.org/unspsc) with codeset download link, UNGM Help Center structure article (2025-07-08), DCMI Metadata Standards Index UNSPSC entry, Wikidata Property P2167 (mandatory regex `\d{8}(\d{2})?`, examples 25101703/11101803/11101709), python-stdnum absence survey + NACE/EAN/GS1-128/CUSIP/ISIN/BIC/IBAN/LEI sibling index, validator.js absence survey, PyPI `unspsc-fr` lookup + search + export package (GitHub-verified; PyPI page bot-gated), SAP Business Network commodity-code doc (6/8-digit only, v25.9 lane) + SAP Ariba procurement doc (snippet-level; exact CSV row unverified), USPS supplier QRG (existence confirmed, quote unverified) + PA/Jaggaer 6-digit search lane (snippet-confirmed; exact `22100000|22101500` rows unverified), O*NET UNSPSC reference (Decimal(8,0)), Stibo STEP UNSPSC format (UNSPSC000. prefix), UNECE Classification Guidelines v2.04 (BFI suffix; direct PDF fetch 403, corroborated via secondary), Cornell procurement buyer guide + cheat sheet, CA DGS UNSPSC page, WisePIM taxonomy guide (stale: GS1-maintained, ~100k codes — label/prose lanes only), HP/Lexmark/SHI-class datasheet label lane (substance confirmed as `UNSPSC: 44103103` / `UNSPSC 44103103` / `UNSPSC #43211507`; pipe-form `UNSPSC Code | 44103103` unverified verbatim), Wikipedia UNSPSC version table (secondary, flagged where sole source), and shipped Paxman capabilities (GTIN, ISBN, ISIN, Country, Currency) as architectural precedents. Repo state: `dev` @ `6fac372` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Review corrections (2026-09-30):** `44103103` is printer/facsimile toner (not printer hardware); v24→v25→v26 strict succession not asserted (v25.0901 is a sector/SAP lane; chronology inverts if read as global majors); v26 delta arithmetic (449+56≠511) flagged secondary; BFI rental/lease values + 79pp unverified; `unspsc-fr` is lookup + FTS search + export.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN research precedent `docs/development/research/2026-08-21-issn-canonicalization.md` plus the IBAN precedent `docs/development/research/2026-08-22-iban-canonicalization.md` and the BIC precedent `docs/development/research/2026-08-23-bic-canonicalization.md`.

> Note on the name: the user asked about "UNSPC". The standard is **UNSPSC** (United Nations Standard Products and Services Code) — one S for Standard, one S for Services, one P for Products. There is no "UNSPC" standard. This report treats "UNSPC" as UNSPSC throughout. Registry name: `unspsc`. Package name: `UNSPSC`. Export alias: `UNSPSC`.

---

## Executive Summary

UNSPSC is a strong fit for a Paxman capability: it has an unambiguous canonical form (**8 ASCII digits, purely numeric, zero-padded hierarchy**: `SSFFCCMM` — Segment + Family + Class + Commodity, each one pair; e.g. `44121706` wooden pencils, `43211503`, `10101501` cats, `25101703` ambulance, `11101803` platinum, `11101709` antimony), a stable single-owner standard (**UNDP-owned**, ex GS1 US 2003-2024, current release **v26.0801 2023-08-14 (latest fetched 2026-09-30; no fixed release cadence published)**, `158,448` items, 14 languages, free XLSX download, no new global major observed through fetch date) with UNDP as Registration Authority since 2025-01-01, a maintained authoritative codeset (**UNDP XLSX `unspsc-english-v260801.1.xlsx`** + searchable **UNGM `https://www.ungm.org/Public/UNSPSC`**), and a well-understood human-readable presentation (**bare digits on the wire; label-prefixed `UNSPSC 44103103` / `UNSPSC: 44103103` / `UNSPSC000.44103103` in datasheets/MDM; pair-grouped `43 21 15 03` in prose explainers only**, all presentation-only). The domain mirrors Paxman's value proposition for GTIN and ISBN: recognizing tolerant human surface, validating strictly against authority, returning canonical compact value with provenance. UNSPSC has **no checksum** — validity is pure codeset membership plus hierarchy consistency, exactly like NACE in python-stdnum and like ISBN's registrant-range rule without the check-digit companion.

Key findings that shape the design:

1. **Canonical form is 8 digits, zero-padded, no separators** (regex `\d{8}`, optional 10-digit `SSFFCCMMBB` business-function form `\d{8}(\d{2})?` per Wikidata mandatory constraint). Zero-padding is structural, not cosmetic: segment `43000000`, family `43210000`, class `43211500` are valid codes in their own right. The 6-digit class shorthand (`441217`) is a SAP/California-accepted alias for the `00`-padded class, not a distinct canonical form. Internal separators (dots, hyphens, spaces) are unattested on the wire and must be rejected — the opposite of ISBN/Phone, where separators are stripped.
2. **One grammar suffices, with label prefix and level-aware alternation.** Unlike ISBN which needs two grammars (ISBN-13 vs ISBN-10), UNSPSC's 8-digit commodity/parent codes and 10-digit business-function form are a single optional-suffix group `(\d{2})?` inside one pattern, plus a fused `UNSPSC` label prefix and a 6-digit class-shorthand branch. A single `UNSPSCRecognitionGrammar` with Regex strategy is correct. Using two grammars (8-digit + 10-digit) would create cross-grammar containment where a 10-digit code contains an 8-digit prefix, producing spurious `AMBIGUOUS` (longer-wins is per-grammar only, cross-grammar is preserved per `orchestrator:_dedup_spans`). Single grammar with optional group avoids this.
3. **Validation is two-level lookup, no checksum.** Level 1: generic structure — exactly 8 digits (or 6-digit alias, or 10-digit with BFI suffix), ASCII digits only, hierarchy `00`-padding consistent (a claimed family code must end `0000`, a class `00`; `00101501`-style mid-zero is structural nonsense and must fail). Level 2: codeset membership against the versioned snapshot (158,448 rows at v26.0801) plus level-consistency (every pair-prefix must itself be a live node). No MOD-97, no Luhn, no Verhoeff, no per-country table like IBAN. Business-function suffix values (e.g. retail/wholesale per Wikipedia/Manutan secondary; rental/lease value mapping unverified, UNECE PDF direct-fetch blocked) are informative only and must not cause rejection.
4. **Zero-padded parents are distinct valid codes, not prefixes.** `43000000` (segment), `43210000` (family), `43211500` (class), `43211503` (commodity) are four different canonical values, not coalesced. Formatting may offer `segmented` (`43-21-15-03` pair-hyphenated) and `labeled` (`UNSPSC 43211503`) as presentational expansions, but validation treats every level as its own identity. The truncated prose forms (`43`, `4321`, `432115` without padding) are exposition, never data — SAP explicitly accepts only 6/8-digit, O*NET stores `Decimal(8,0)`.
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): UNDP codeset release `v26.0801` (`kind="registry"`, rolling periodic) owns membership + hierarchy; UNGM structure article owns the four-level positional definition; UNECE Classification Guidelines v2.04 owns the optional business-function suffix. NOT an ISO standard — there is no ISO catalogue entry to cite, and ISO 22745/8000 are dictionary-infrastructure siblings, not parents.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---

## 1. Target User

| Persona | Why they need UNSPSC canonicalization | Typical context |
|---------|---------------------------------------|-----------------|
| **Procurement / source-to-pay engineers** | Normalize `unspsc 44103103` vs `44103103` vs `UNSPSC000.44103103` vs `44 10 31 03` to one 8-digit key for catalog joins, spend cubes, and supplier matching | SAP Ariba / Business Network imports, PA/Jaggaer-class catalog feeds, UNGM registration, MDM (Stibo STEP) pipelines |
| **Spend-analytics / data engineering teams** | Roll line-items up the Segment→Family→Class→Commodity tree from free-text POs, invoices, and scraped datasheets with span-bearing provenance | ETL pipelines, lakehouse spend marts, LLM extraction post-processing, O*NET-style reference joins |
| **Supplier onboarding / marketplace operators** | Validate user-supplied codes at form ingest; reject structurally invalid vs not-in-codeset input with `MISSING`/`INVALID` semantics and preserve span for UX highlighting | UNGM supplier registration, USPS supplier QRG flows, PA supplier search, e-catalog publishing |
| **Gov / compliance / catalog librarians** | Pin a versioned snapshot (v26.0801 today, v27+ tomorrow) so `43211503` resolves identically across audits; detect moved/inactivated codes between releases | CA DGS custom-list maintenance, USDA specialty-crops inspection, WHO device nomenclature, version-drift review |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many UNSPSC mentions) and a contract; Paxman returns one canonical UNSPSC code (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors GTIN (digits-only canonical default) and ISBN (registry-gated issued-ness) ergonomics, but the canonical default is **8-digit zero-padded compact** (no label, no separators, parents preserved as given).

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

Surveyed from UNDP/UNGM/MSI/Wikidata (spec and schema), ecosystem validator strip logic (Wikidata regex, SAP digit rules, O*NET decimal storage, `unspsc-fr` float→int normalisation, Stibo ID prefix), and real-world carriers (datasheet labels, MDM IDs, SAP CSV columns, Jaggaer rows, prose explainer grouping). UNSPSC is a flat-digit taxonomy: the carrier set is labels + padding + one optional suffix, not resolver URIs (there is no `https://unspsc.org/…` resolver for individual codes that survives — the Wikidata formatter URLs are link-rot).

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| 8-digit compact commodity | `44103103`, `43211503`, `10101501`, `25101703` | Every primary: WHO deck, SAP docs, Wikidata examples, HP/Lexmark/SHI datasheets | canonical, dominant (>99% of wire mentions) | RECOGNIZE | main pattern body `\d{8}` |
| 8-digit zero-padded parent (segment/family/class) | `43000000`, `43210000`, `43211500`, `10101500`, `10000000` | Cornell cheat sheet ("if the Commodity level is not specified, then the last 2-digits will be zero"), Wikipedia/MSI tables, O*NET, CA DGS, PA/Jaggaer-class catalog rows (exact `22100000`/`22101500` row values unverified verbatim) | official, high (catalogs, gov lists, spend rollups) | RECOGNIZE | same `\d{8}` body; level derived in notation, not pattern |
| 6-digit class shorthand | `441217` (= class Writing instruments; full `44121700`) | SAP Business Network ("supports only 6-digit or 8-digit"), CA DGS ("composed of both 6 and 8 digit codes") | common in SAP/California/food-procurement lanes | RECOGNIZE | alternation branch `\d{6}` → notation pads `+ "00"` |
| Label-prefixed prose | `UNSPSC 44103103`, `UNSPSC: 44103103`, `UNSPSC #43211507`, `unspsc,43211509` (CSV-shape lane) | CDW/Xerox/BarcodesInc listings + Lexmark reseller pages (substance confirmed); WisePIM guide; Ariba CSV mapping docs (exact `unspsc,43211509,custom,...` row unverified) | very high in datasheets/MDM/CSVs | RECOGNIZE | fused label `(?:UNSPSC(?:\s+code)?[\s:#.\-]+)?` |
| MDM system-ID prefixed | `UNSPSC000.44103103` | Stibo STEP UNSPSC format doc ("`UNSPSC000.` is the default text prefixed to the ID") | medium (Stibo/MDM estates) | RECOGNIZE | label-branch extension `(?:UNSPSC0*\.?)?` |
| 10-digit + business-function suffix | `XXXXXXXXBB` (`SSFFCCMMBB`) | Wikidata mandatory regex `(\d{2})?` + URL patterns, UNECE Guidelines (BFI optional 2-digit suffix; direct PDF fetch 403, retail/wholesale corroborated via secondary, rental/lease mapping unverified), CA DGS `SSFFKKCCBB` (noted "California doesn't use") | rare on the wire, official in schema | RECOGNIZE | optional suffix group `(\d{2})?`; notation splits `commodity`/`function` |
| Space-grouped pairs (display) | `43 21 15 03`, `44 12 00 00`, `10 10 15 01` | Wikipedia/MSI explainer tables, Cornell breakdown tables | docs/prose only, never CSVs/APIs/DBs | DEFER | named `extra_grammars` community extension (`unspsc_grouped_recognition`); v1 rejects internal spaces |
| Truncated 2/4-digit prose prefix | `43` (= segment 43), `4321` (= family) | WisePIM ("Segment 43 … Family 4321"), Cornell breakdowns | prose exposition only | REJECT | documented negative test; `43` alone → MISSING (real code is `43000000`) |
| Dotted `43.21.15.03` | — (no attestation) | None found in official docs, SAP/Ariba, Wikidata, PyPI, GitHub | none observed | REJECT | documented negative test; `.` inside → no match |
| Hyphenated `43-21-15-03` / `4410-3103` | — (no attestation) | None found (unlike ISBN/Phone, UNSPSC has no hyphen convention) | none observed | REJECT | documented negative test; `-` inside → no match |

A v1 that does NOT recognize space-grouped pairs states that explicitly here AND raises it as Open Decision §13 row 11: prose-explainer grouping (`43 21 15 03`) is the one commonly seen form left to a community extension, because no validator strips internal spaces and storage is `Decimal(8,0)`.

### 2.2 Wild variants — adversarial mutations of each inventoried form

Enumerated from UNDP/UNGM/MSI pages, Cornell/CA-DGS guides, SAP/Ariba/PA-Jaggaer corpora, and validator strip logic; stress-test every §2.1 RECOGNIZE form:

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical compact commodity | `44103103`, `43211503`, `10101501`, `25101703` | Spec master form; 8 digits, all pairs significant |
| 2 | Zero-padded parents | `43000000`, `43210000`, `43211500`, `10101500`, `10000000` | Trailing-`00` pairs mark level; must validate as codes, not prefixes |
| 3 | 6-digit class shorthand | `441217`, `432115`, `101015` | SAP/CA alias; canonicalise to `44121700` etc. |
| 4 | 10-digit business-function | `4410310314`-shape (`XXXXXXXXBB`) | Optional suffix; split 8+2, suffix informative only |
| 5 | Label with colon/space/hash | `UNSPSC: 44103103`, `UNSPSC 44103103`, `UNSPSC #43211507` (attested); pipe-form `UNSPSC Code | 44103103` unverified verbatim | Case-insensitive `UNSPSC`, optional `code`, `[\s:#|\-]+` tolerant; span includes label |
| 6 | MDM system-ID prefix | `UNSPSC000.44103103` | Stibo default prefix; strip `UNSPSC0*\.?` lane |
| 7 | CSV header lane | `unspsc,43211509` (shape; exact full Ariba row unverified) | Ariba mapping-row shape; comma is a field separator, not part of code |
| 8 | Lowercase label | `unspsc 44103103`, `unspsc code 43211503` | Label case-insensitive; digits unaffected |
| 9 | Irregular whitespace around label | `UNSPSC   44103103`, `UNSPSC\tcode\t44103103` | `\s+` tolerance between label and digits only — never inside digits |
| 10 | Internal space (grouped display) | `43 21 15 03`, `44 12 00 00` | v1: no match (DEFER to community extension); must not carve `4321`/`1503` fragments |
| 11 | Internal dot/hyphen | `43.21.15.03`, `4410-3103`, `44103103-14` | v1: no match (REJECT); dot/hyphen are not UNSPSC separators |
| 12 | With trailing annotation | `44103103 (Printers)`, `43211503 - Docking stations` | Must emit one span per code, not swallow parenthetical |
| 13 | Multiple per line | `44103103, 43211503`, `codes: 22100000, 22101500` (illustrative shapes; exact Jaggaer pipe-row unverified) | 2+ matches; distinct values → AMBIGUOUS under single_value |
| 14 | Quoted / bracketed | `"44103103"`, `[43211503]`, `(UNSPSC: 10101501)` | Inside punctuation; word-boundary guards must still fire |
| 15 | Over-long / under-long | `4410310` (7), `441031031` (9), `44103103144` (11) | Only 6/8/10 valid; 7/9/11 must not match |
| 16 | X-glued runs | `X44103103`, `44103103Y`, `A4410310314B` | Longer alphanum token must not yield inner code via carving; `(?<!\d)(?!\d)` + alpha guards |
| 17 | Float-mangled CSV export | `44103103.0`, `10101501.0` | `unspsc-fr` README attests source CSVs carry floats; v1: match `44103103`, leave `.0` outside span (REJECT the dotted tail) |
| 18 | Invalid hierarchy padding | `00101501`, `43001503`, `10100001`-shape mid-zero anomalies | Grammar claims 8 digits; rule rejects: non-`00` parent pairs must still prefix-match a live node |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Wikidata P2167 mandatory format constraint | `\d{8}(\d{2})?` — digits only, 8 + optional 2; URL patterns `^https?://(?:www\.)?unspsc\.org/search-code/\?CSS=(\d{8}(\d{2})?)` and `search-code-result?titleSearch=&codeSearch=(\d{8}(\d{2})?)` |
| Wikidata examples | `25101703` ambulance, `11101803` platinum, `11101709` antimony — all bare 8-digit |
| SAP Business Network commodity codes | "supports only 6-digit or 8-digit UNSPSC codes" + "SAP Business Network uses UNDP version - UNSPSC v25.9 by default" (snippet-level; direct help.sap.com HTML fetch empty, PDF-gated) + "codes that are eight-digit numbers. Each code consists of four pairs of digits" (pairing sentence corroborated on the sibling Ariba doc, not isolated verbatim on the BN page) |
| SAP Ariba procurement doc | "UNSPSC … uses codes that are eight-digit numbers" (snippet-level) + illustrative Ariba CSV shape `unspsc,43211509,...` (exact `unspsc,43211509,custom,30153013,"Laptop, Notebook, Tablet"` row unverified — zero hits on targeted search; do not cite verbatim without the source PDF) |
| O*NET `unspsc_reference` | `commodity_code Decimal(8,0)`, `class_code Decimal(8,0)` — integer storage, no separators |
| PyPI `unspsc-fr` README (via GitHub; PyPI page bot-gated) | "`scripts/build.py` normalise les codes en entiers (le CSV source contient des flottants du type `10101501.0`)" — float→int is the only cleaning; lookup + FTS search + SQLite/JSON/Parquet export (`get(10101501)`, `children(10100000)`, `ancestors(10101501)`, `search(...)`) over 149,849 commodities at v26.0801 (not lookup-only) |
| Stibo STEP UNSPSC format | "`UNSPSC000.` is the default text prefixed to the ID" — system IDs `UNSPSC000.44103103` |
| Cornell cheat sheet | "all UNSPSCs are 8-digits, if the Commodity level is not specified, then the last 2-digits will be zero" |
| UNECE Guidelines v2.04 | "Business Function Identifiers (BFIs) are an optional 2-digit suffix to the UNSPSC Commodity code number" |
| Classification-event decks (att illustrative) | 8-digit UNSPSC commodity lane (e.g. GS1 classification-event PDFs; the exact `WHO/GS1 deck "UNSPSC Code: 8 digits, e.g. 44103103"` line was not located — do not cite verbatim; find the actual deck URL or drop) |
| python-stdnum (negative) | No `stdnum/unspsc.py`; closest lookup-only sibling `stdnum/eu/nace.py` proves taxonomy-without-checksum is eligible but uncontributed |
| validator.js (negative) | No `isUNSPSC` in the README validator table (full table fetched; `src/lib/` file-level listing not enumerated in fetched HTML — absence rests on table, no counter-evidence) |

**Normalization contract (digits-only — the inverse of ISBN/Phone):**

```python
import re

# UNSPSC normalization: strip ONLY the label lane and surrounding space.
# Internal separators are never stripped (no validator attests them).
compact = re.sub(
    r"(?i)^\s*UNSPSC(?:0*\.?)?(?:\s+code)?[\s:#|\-.]*",
    "",
    raw,
).strip()
# then validate: compact.isascii() and compact.isdigit()
# and len(compact) in {6, 8, 10}; 6-digit pads +"00" before lookup
```

### 2.3 What input is NOT a UNSPSC mention

- GTINs (`05901234123457`, 8/12/13/14 digits with GS1 Mod-10) — overlapping 8-digit length with GTIN-8 is the one real collision; disambiguation is authority-level (codeset membership vs check digit), not length-level. See §4.4 and §14.
- Phone fragments / M49 country numerics (`004`, `44`, `1`) — too short or wrong lane; bare `43` is prose, not segment `43000000`.
- Single pairs / prose prefixes (`43`, `4321`, `432115` unpadded-class context) — exposition, MISSING vs INVALID boundary (see §9).
- Dotted/decimal numbers (`43.21`, `44103103.0` as a whole) — the `.0` float tail is CSV damage, not part of the code.
- Trademark/class shorthands from other taxonomies (NACE `46.51`, CPV `30213100-6` with check hyphen, eCl@ss `19-02-01-01`) — different provenance, different separators.
- Bare business-function suffixes (`14`, `retail`) — meaningless without the 8-digit stem.

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct UNSPSC codes in one slice (catalog line `44103103, 43211503`, multi-code catalog row shape) → `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS`.

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact plus structured decomposition

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UNSPSCNotation:
    """UNSPSC notation — grammar-normalized digit form.

    ``digits`` is the 8-digit zero-padded code (6-digit class shorthand
    is padded +"00" by the grammar; 10-digit input keeps its 8-digit
    stem here).
    ``level`` is one of "segment" | "family" | "class" | "commodity",
    derived from trailing-00 pairs (no authority lookup).
    ``function`` is the 2-digit business-function suffix, or "" when the
    input was 6/8 digits (trace-only, never affects validity).
    ``native_length`` is the spelled digit length (6, 8, or 10),
    retained as a facet for the ``native`` offered format.
    """

    digits: str
    level: str
    function: str
    native_length: int
```

**Considered alternative — single field `digits` only:** a bare 8-digit string would carry the pipeline, since rules do membership lookup on the stem. However the decomposition is preferred because (1) the UNDP/UNGM spec indexes authority by level (Segment/Family/Class/Commodity are distinct citable rows), (2) the 6-vs-8-vs-10 routing key (`native_length` + `function`) decides which rule branch validates without re-parsing, and (3) level semantics (`segment` rollups vs `commodity` leaves) drive `format_value()` grouping and spend-analysis UX. This mirrors GTIN's `digits + native_length + has_ai` facet pattern (`paxman/capabilities/GTIN/notation.py`).

**Invariants the grammar enforces (before rules):**

- `digits` is exactly 8 ASCII digits (`compact.isascii() and compact.isdigit()`), zero-padded as spelled (6-digit input pads right with `"00"`).
- `level` is derived purely syntactically: endswith `"000000"` → segment; `"0000"` → family; `"00"` → class; else commodity.
- `function` is `""` or exactly 2 ASCII digits (the 9th–10th input digits); `native_length` in `{6, 8, 10}` and `== spelled digit count`.

### 3.2 Why not carry spaces, dots, or labels in the notation

Spaces, pair-grouping, dots, hyphens, and `UNSPSC`/`UNSPSC000.` labels have **no lexical significance** for validity — the wire form is digits-only per every primary (Wikidata regex, SAP "eight-digit numbers", O*NET `Decimal(8,0)`). Presentation is `Capability.format_value()` only.

### 3.3 Why `level` is not a shape discriminator literal

`level` is a free `str` computed from padding, validated implicitly by the membership rule (a claimed `family` code must exist as a family node in the snapshot), not a `Literal` — mirroring Country/ISIN precedent where the grammar emits the widest syntactic shape and the LOOKUP_TABLE rule owns vocabulary truth. A `Literal["segment", ...]` would freeze the four UNGM levels into the type while the codeset occasionally moves nodes between releases (v24 moved 6, deleted 1); the rule snapshot, not the type, is the versioned truth.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex vs Lexicon

Per HOW_TO_ADD_NEW_GRAMMAR.md, UNSPSC has a distinctive fixed-width numeric shape (6/8/10 ASCII digits with a fused optional label), so **Regex** is correct. Lexicon is wrong: the vocabulary is ~158k rows, not a finite hand-keyed token table, and recognition must fire before (and without) consulting the snapshot.

### 4.2 Reference pattern (adapted from GTIN and ISBN verbatim precedent)

GTIN precedent (`paxman/capabilities/GTIN/grammar/gtin_recognition.py`): exact-length alternation, longest-first (14/13/12/8), so lengths never carve each other. ISBN-13 precedent (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py`): module-scope body string compiled by `RegexStage`, lookarounds that reject digit continuation, fused label `[\s:-]+`, `PipelineGrammar` with `StandardPre(empty_guard=True)`.

**Proposed UNSPSC pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

# Boundary guards: HOW_TO_ADD_NEW_GRAMMAR.md teaches raw lookarounds
# (e.g. (?<!\d)); GTIN ships LabelMatcher + BoundarySpec. The
# BoundaryGuard.word_only() form below is illustrative — align with the
# current grammar package root at implementation time.
try:
    from paxman.core.grammar.boundary import BoundaryGuard

    _LOOKBEHIND = BoundaryGuard.word_only().lookbehind
    _LOOKAHEAD = BoundaryGuard.word_only().lookahead
except ImportError:  # fall back to the documented raw lookarounds
    _LOOKBEHIND = r"(?<!\d)(?<![A-Za-z])"
    _LOOKAHEAD = r"(?!\d)(?![A-Za-z])"

_UNSPSC_LABEL = r"(?:UNSPSC(?:0*\.?)?(?:\s+code)?[\s:#|\-.]*?)?"
_UNSPSC_BODY = (
    r"(?P<ten>\d{8}(?P<function>\d{2}))"
    r"|(?P<eight>\d{8})"
    r"|(?P<six>\d{6})"
)
_UNSPSC_PATTERN = (
    _LOOKBEHIND
    + _UNSPSC_LABEL
    + r"(?P<code>"
    + _UNSPSC_BODY
    + r")"
    + _LOOKAHEAD
)


def _notation(match: re.Match[str]) -> UNSPSCNotation:
    raw = re.sub(r"\D", "", match.group("code"))
    if len(raw) == 6:
        raw = raw + "00"
    stem = raw[:8]
    function = raw[8:10] if len(raw) == 10 else ""
    if stem.endswith("000000"):
        level = "segment"
    elif stem.endswith("0000"):
        level = "family"
    elif stem.endswith("00"):
        level = "class"
    else:
        level = "commodity"
    return UNSPSCNotation(
        digits=stem,
        level=level,
        function=function,
        native_length=len(re.sub(r"\D", "", match.group("code"))),
    )


class UNSPSCRecognitionGrammar(PipelineGrammar[UNSPSCNotation]):
    """UNSPSC recognition: 6/8/10-digit codes with optional UNSPSC label."""

    name = "unspsc_recognition"
    semantics = "unspsc_recognition"
    single_value = True
    pre = StandardPre[UNSPSCNotation](empty_guard=True)
    regex = RegexStage[UNSPSCNotation](
        pattern=_UNSPSC_PATTERN, notation_fn=_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs GTIN/ISBN:* module-scope strings compiled by `RegexStage`; longest-first alternation (10 before 8 before 6) so a 10-digit code never carves an 8-digit prefix within one grammar; ASCII guard via `\d` + `isascii` check in `_notation` (ISBN uses explicit ASCII guard; UNSPSC digits admit no Unicode-digit lane); fused label `[\s:#|\-.]*?` (ISBN fuses `ISBN` + `[\s:-]+`; UNSPSC adds `#`, `|`, `.` for the `UNSPSC000.` MDM lane and attested `UNSPSC #…` / `UNSPSC: …` datasheet lanes; pipe-form `Code |` is unverified verbatim); boundary guards per HOW_TO_ADD_NEW_GRAMMAR.md raw lookarounds (`(?<!\d)` etc.; GTIN ships `LabelMatcher` + `BoundarySpec`) so `X44103103` never carves; `StandardPre(empty_guard=True)` rejects empty slices. **Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a pattern element — compact + parents to `\d{8}`, class shorthand to `\d{6}`, label prose to `_UNSPSC_LABEL`, MDM prefix to the `(?:0*\.?)?` lane, BFI suffix to `(?P<ten>\d{8}(?P<function>\d{2}))`; the DEFER row (space-grouped) names `unspsc_grouped_recognition` as its future mechanism; the REJECT rows (dotted/hyphenated/truncated) are excluded by construction (no separator class inside the digit body).

**8 vs 10 as one grammar vs two:** (Recommended) Single grammar with optional suffix — avoids cross-grammar containment spurious AMBIGUOUS where a 10-digit BFI code contains an 8-digit stem. Alternative (rejected): two grammars (`unspsc8` + `unspsc10`) with coalesced semantics — heavier surface for zero semantic difference, since the suffix is informative-only.

**6-digit branch vs normalize-in-rule:** (Recommended) Grammar pads `+ "00"` and records `native_length=6`, so the rule sees one 8-digit stem shape. Alternative (rejected): grammar emits 6-digit stems and the rule pads — splits one syntactic fact across two layers and complicates candidate dedup keys.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)

- Grammar emits span-bearing `RecognitionMatch`, half-open `[start, end)`, `raw_text == text[start:end]` (label included in span when present, digits-only in notation).
- `RegexStage` loops `re.finditer`, builds `RecognitionMatch`; stages must not mutate text.
- Engine owns within-grammar containment dedup (longer wins) and total recognition ordering `(start, end, active-set index, grammar name)`.
- Candidate dedup `(value, recognition_rule, validation_rule)` after validation, on the pre-format canonical value.

### 4.4 Guard boundaries against sibling grammars

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| UNSPSC (this) | 6/8/10 ASCII digits, optional UNSPSC label | `(?<!\d)(?<![A-Za-z])` via `word_only` | `(?!\d)(?![A-Za-z])` via `word_only`; float tail `.0` stays outside span |
| GTIN-8 | exactly 8 ASCII digits, optional `(01)` AI marker | same word guards | same; GTIN-8 vs UNSPSC-8 overlap resolved at validation (check digit vs codeset), not recognition |
| Phone fragments | `+\d`, `(0)`, `-`-joined runs | `+`/paren lane | dash continuation |
| Country numeric (M49) | 1–3 digits | same | same; length + codeset disjoint in practice |
| CreditCard | 13–19 digits, Luhn | same | same; length-disjoint from 6/8/10 except 16-vs-10 — no overlap |
| Date numeric | 4/6/8-digit date runs with `/-` separators | separator lane | separator lane; UNSPSC never contains separators |

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

- `semantics = "unspsc_recognition"` identity id; the deferred grouped-pairs extension (`unspsc_grouped_recognition`) would coalesce to the same id so both route to the same rules.
- No second shipped grammar at v1; `target_semantics` on all three rules claims exactly this id.

### 4.6 `single_value` — one mention per call vs batch processing

Recommendation: `single_value=True` at v1 (shipped precedent: GTIN, ISBN, ISIN, Country all set it). Catalog lines and Jaggaer multi-code rows use the caller-owned segmentation path (split then canonicalize each slice). A batch `extra_grammars` free-text variant with `False` is available as a community extension if MDM estates need whole-column scans.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | United Nations Development Programme (UNDP) since 2025-01-01; GS1 US 2003-05 → 2024-12-31; ECCMA 1999 → 2003-03; UNDP/IAPSO + Dun & Bradstreet 1998-09-29 MoU |
| Registration Authority | UNDP — `info.unspsc@undp.org`, codeset download `unspsc-english-v260801.1.xlsx`, search `https://www.ungm.org/Public/UNSPSC` |
| Spec name | United Nations Standard Products and Services Code (UNSPSC) — NOT an ISO standard; no `iso.org/standard/` entry exists |
| Current release | v26.0801 (2023-08-14), 158,448 items, 14 languages (EN FR DE ES IT JA KO NL ZH PT DA NO SV HU) |
| Check character system | NONE — purely positional numeric coding; Wikidata mandatory regex has no check facet; all 8/10 positions are hierarchy |
| Hierarchy reference | UNGM structure article: `XX000000` Segment, `XXXX0000` Family, `XXXXXX00` Class, `XXXXXXXX` Commodity; UNECE v2.04 for optional `BB` business function |
| Related specs | UNCCS (replaced 2012), CPV (EU sibling), ECLASS, GS1 GPC, NAICS, HS, ISO 22745/8000 (dictionary-infrastructure siblings, not parents) |

**Structure (UNGM Help Center 2025-07-08, verbatim):** "The UNSPSC code structure represents a four-level hierarchy with each level represented by two digits. The structure is hierarchical and the coding is purely numeric." Bullets: "`XX000000` the first pair of digits identifies the relevant Segment; `XXXX0000` the first and second pair of digits, combined, indicate the Family; `XXXXXX00` the first three pairs of digits identify the Class; `XXXXXXXX` combined the four pairs of digits indicate the Commodity." Charset is ASCII digits only; examples across primaries: `10101501` cats, `10101502` dogs, `10101516` cattle, `44121706` wooden pencils, `43211602` docking stations, `44103103` printer/facsimile toner (class `44103100` is printer/facsimile/photocopier supplies; not printer hardware), `25101703` ambulance, `11101803` platinum, `11101709` antimony, `10000000` segment 10, `10100000` family 10-10, `10101500` class Livestock. Note: UNDP owner page says "five-level" (counts the optional BFI suffix); UNGM/Wikipedia/MSI say "four-level" (+ optional fifth) — same structure, different counting.

**Lineage table:**

| Release | Date | Status | Note |
|---------|------|--------|------|
| MoU UNDP/IAPSO + Dun & Bradstreet | 1998-09-29 (signed) / 1998-11-01 | Superseded | First version under Peter R. Benson; Delphi-method code-management procedure |
| ECCMA stewardship | 1999 → 2003-03 (last v6.0315) | Superseded | Non-profit management; spun out eOTD → ISO 22745/8000 lineage |
| GS1 US code manager | 2003-05 → 2024-12-31 | Superseded | Appointed by UNDP; member Excel + change-request era |
| v08.1201 → v09.0501 → v14.0801 | 2008-12 → 2009-05 → 2014-08 | Superseded | 19,038 → 21,718 → 49,069 items (Wikipedia version table, secondary) |
| v17.1001 → v19.0501 → v20.0601 | 2017-10 → 2019-05 → 2020-06 | Superseded | 77,350 → 83,196 → 87,477 items (secondary) |
| v22.0601 → v23.0701 | 2022-06 → 2023-07 | Superseded | 156,478 → 156,936 items; v23 cited by O*NET 27.0–29.0 dictionaries |
| v24.0301 | 2024-03 | Superseded | 157,116 items; 740 changes (721 new, 12 edited, 6 moved, 1 deleted); new segment `57`000000 Humanitarian Relief (UNGM request); USDA specialty-crops additions |
| v25.0901 | 2025-09 (sector/SAP lane: GS1-AU healthcare requirement + SAP Business Network "UNDP version - UNSPSC v25.9 by default", snippet-level) | Superseded (lane, not proven global major) | Do NOT read as global successor of v24: version-ID chronology inverts if v26.0801 (2023-08-14) is the global latest. Treat as sector/SAP snapshot pending UNDP changelog |
| v26.0801 | 2023-08-14 (version-ID date reads 08-01; MSI lists modified 2023-08-14) | Active (latest fetched 2026-09-30, not latest-possible) | 158,448 items (primary; one vendor secondary reads 158,449 — off-by-one, primary wins); delta "511 changes (449 new, 56 edits)" is secondary-only (grihasoft/vendor + LinkedIn) and arithmetically incomplete (449+56=505≠511, moved/deleted unaccounted) — do not cite as verified; 14 languages; UNDP free XLSX `unspsc-english-v260801.1.xlsx` |
| UNDP stewardship | 2025-01-01 → present | Active | GS1 US reverted; UNDP owns change requests, revisions, scheduled updates, special projects. Note: takeover postdates latest-fetched release by ~17 months — UNDP inherited the 2023 codeset and had cut no new global major through fetch date; "periodic scheduled updates" is expectation, not observed cadence |

**Citation Details Table (for Provenance):**

| Authority | Spec name | Version | Reference URL | Lifecycle | Publication year | Kind |
|-----------|-----------|---------|---------------|-----------|------------------|------|
| UNDP | UNSPSC Code Structure (UNGM Help Center) | Four-level positional definition, updated 2025-07-08 | https://help.ungm.org/hc/en-us/articles/360012816160-What-are-UNSPSC-codes- | active | 2025 | specification |
| UNDP | UNSPSC Codeset Release v26.0801 | v26.0801, 2023-08-14, 158,448 items, `unspsc-english-v260801.1.xlsx` | https://www.undp.org/unspsc | active | 2023 | registry |
| UNECE | Classification Guidelines (BFI suffix) | v2.04 (page count unverified; direct PDF fetch returns 403 — BFI-as-optional-2-digit-suffix corroborated via Wikipedia/Manutan/Qvalia secondary) | https://unece.org/fileadmin/DAM/trade/agr/meetings/ge.11/2005/2005_i04_UNSPSC.pdf | active | 2005 | specification |
| Wikidata (secondary mirror) | Property P2167 format constraint | mandatory `\d{8}(\d{2})?`, edited 2026-09-29 | https://www.wikidata.org/wiki/Property:P2167 | active | 2026 | specification (mirror) |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|---------------|-------------------|
| `rules/undp_unspsc_structure_ed2025.py` | authority="United Nations Development Programme", specification_name="UNSPSC Code Structure (UNGM Help Center)", kind="specification", reference_url="https://help.ungm.org/hc/en-us/articles/360012816160-What-are-UNSPSC-codes-", version="2025-07-08", lifecycle="active", publication_year=2025 | Section 1-hierarchy-structure, Section 2-level-padding | Positional shape: 6/8/10 length lane, ASCII digits, `00`-padding level consistency (PARSER) |
| `rules/undp_unspsc_codeset_ed2023.py` | authority="United Nations Development Programme", specification_name="UNSPSC Codeset Release", kind="registry", reference_url="https://www.undp.org/unspsc", version="v26.0801 (2023-08-14)", lifecycle="active", publication_year=2023 | Section 3-codeset-membership | Stem exists in the versioned snapshot; every pair-prefix is a live node (LOOKUP_TABLE) |
| `rules/unece_bfi_ed2005.py` | authority="United Nations Economic Commission for Europe", specification_name="Classification Guidelines (Business Function Identifiers)", kind="specification", reference_url="https://unece.org/fileadmin/DAM/trade/agr/meetings/ge.11/2005/2005_i04_UNSPSC.pdf", version="v2.04", lifecycle="active", publication_year=2005 | Section 4-business-function-suffix | 10-digit suffix is well-formed and informative-only; never rejects on BFI value (PARSER) |

Each `Rule[UNSPSCNotation]` subclass declares six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`, `paxman/core/domain.py`):

```python
name: str  # "Section {N}-{slug}"
strategy: RuleStrategy  # PARSER or LOOKUP_TABLE
provenance: Provenance  # == module PUBLICATION
citation: str  # spec section anchor
target_semantics: frozenset[str]  # {"unspsc_recognition"}
requires_features: frozenset[str]  # frozenset() or {"include_live_membership"}
```

### 5.3 What each rule does vs does not own

- `matches()` validates strictly, never raises, never reads contract `include_*` flags directly (gating is `requires_features`, enforced by the engine). `normalize()` returns the default 8-digit compact stem, never reads `output_format` (CI purity scan enforced). Cross-rule `normalize()` identity (same 8-digit stem from every rule) is engine dedup behavior, not a stated rule contract — implement it that way so `_dedup_candidates` coalesces.
- `RuleStrategy` choice: PARSER for structure/padding/suffix-shape (no authority table needed), LOOKUP_TABLE for codeset membership + prefix-liveness (snapshot needed).
- Hierarchy truth lives in the snapshot, not the type: `Section 3` checks stem membership AND that each `00`-truncated ancestor (`SS000000`, `SSFF0000`, `SSFFCC00`) is itself a live row — this is what makes `43001503`-style mid-zero anomalies INVALID rather than merely unknown.

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Whether codeset-membership validation is always-active vs gated. Recommendation: ship structure (PARSER, always-active) + codeset membership (LOOKUP_TABLE, always-active at the pinned v26.0801 snapshot) as the default; add a rolling-liveness interpretation behind `include_live_membership=False` default-off that downstream planners can wire to a fresher snapshot without changing the default verdict. Rationale: the snapshot is 158k rows (large but static, ISBN-range-message precedent proves this ships fine), staleness between UNDP releases is months not days, and an always-active membership rule gives the sharp valid-vs-unknown split (GTIN prefix / ISBN range precedent) while the flag preserves determinism-by-snapshot for estates that track UNDP HEAD.

Cost/benefit: snapshot adds ~2–4 MB codeset table (English titles optional; membership needs stems only — titles ship only if `format_value` ever renders names, which v1 does not). Benefit: `44103103` (issued) vs `44103199` (well-formed, unissued) resolve differently instead of both succeeding. Per-release moved/inactivated codes (v24: 6 moved, 1 deleted) become INVALID-under-pinned-snapshot with a clear provenance version, not silent SUCCESS.

### 5.5 Assignment / registration authority & registry content

Owner: UNDP (`info.unspsc@undp.org`). Assigning flow: code change requests + revisions + scheduled updates + special projects, all via UNDP since 2025-01-01 (previously GS1 US member change-request process). Record content: 8-digit code + English title + level + version-effectivity (new/edited/moved/inactivated deltas per release, e.g. v24 721 new + 12 edited + 6 moved + 1 deleted; v26 deltas secondary-only, see lineage table). Cadence: no fixed-calendar promise published; history does NOT read as strict semiannual majors (v26.0801 2023-08-14 postdated by v24.0301 2024-03 and the v25.0901 SAP/sector lane — do not assert v23→v24→v25→v26 succession without a UNDP changelog). Search: `https://www.ungm.org/Public/UNSPSC` (search + Export to Excel). Download: `https://www.undp.org/sites/g/files/zskgke326/files/2025-03/unspsc-english-v260801.1.xlsx` (English, no paywall). Languages: 14 (EN FR DE ES IT JA KO NL ZH PT DA NO SV HU).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract MUST inherit `CapabilityContract` (never `Contract` directly). `@dataclass(frozen=True)` without slots.

```python
from dataclasses import dataclass, field
from typing import ClassVar
from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class UNSPSCContract(CapabilityContract):
    """User-facing configuration for UNSPSC capability.

    Formats (ADR-0011 classes): ``unspsc`` is the wire encoding
    (8-digit compact, default); ``segmented`` is the same-entity
    expansion (``SS-FF-CC-MM`` pair-hyphenated display);
    ``labeled`` is the same-entity expansion (``UNSPSC <stem>``);
    ``native`` is the spelling-preserving encoding (6-digit stays
    6-digit, 10-digit keeps its suffix).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "unspsc"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"segmented", "labeled", "native"}
    )

    capability_name: str = field(default="unspsc", init=False)

    # Capability-specific fields
    include_business_function: bool = True
    include_live_membership: bool = False
```

Per HOW_TO_ADD_NEW_CAPABILITY.md:502-519 and `tools/new_capability.py:134-141`,
the `create_contract()` factory lives on the Capability (not the Contract),
with the common block as keyword-only `Sequence[str] | None = None`. See §6.2.

- `DEFAULT_OUTPUT_FORMAT` concrete string `"unspsc"`, `OFFERED_OUTPUT_FORMATS` excludes default, resolved via `resolve_output_format`; `create_contract()` fixed keyword-only common block then capability-specific params.
- Presentational-only invariant: rules never see `output_format`; `normalize()` always returns the 8-digit stem.
- For UNSPSC, offered formats model the interchange forms:

| output_format | Value example | Meaning |
|---------------|---------------|---------|
| `unspsc` (default) | `43211503` | 8-digit zero-padded wire form |
| `labeled` | `UNSPSC 43211503` | Label-prefixed display encoding (same entity) |
| `native` | `441217` / `4410310314` | Spelling-preserving encoding (6-digit alias unpadded, 10-digit with suffix) |

> **Implementation note (2026-09-30):** the `segmented` (`SS-FF-CC-MM`)
> display form proposed here was dropped before implementation — the
> grammar rejects internal hyphens by design, so a segmented rendering
> could never re-enter (ADR-0010 fixed-point). Offered: `labeled` +
> `native` only.

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from collections.abc import Sequence
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.UNSPSC.contract import UNSPSCContract
from paxman.capabilities.UNSPSC.grammar.unspsc_recognition import (
    UNSPSCRecognitionGrammar,
)
from paxman.capabilities.UNSPSC.notation import UNSPSCNotation
from paxman.capabilities.UNSPSC.rules.undp_unspsc_codeset_ed2023 import (
    Section3CodesetMembership,
)
from paxman.capabilities.UNSPSC.rules.undp_unspsc_structure_ed2025 import (
    Section1HierarchyStructure,
    Section2LevelPadding,
)
from paxman.capabilities.UNSPSC.rules.unece_bfi_ed2005 import (
    Section4BusinessFunctionSuffix,
)


class UNSPSCCapability(Capability[UNSPSCNotation]):
    """UNSPSC capability — wiring + presentation seam."""

    name = "unspsc"

    def get_grammars(self) -> list[Grammar[UNSPSCNotation]]:
        """Return the shipped recognizers."""
        return [UNSPSCRecognitionGrammar()]

    def get_rules(self) -> list[Rule[UNSPSCNotation]]:
        """Return the shipped validators."""
        return [
            Section1HierarchyStructure(),
            Section2LevelPadding(),
            Section3CodesetMembership(),
            Section4BusinessFunctionSuffix(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        include_business_function: bool = True,
        include_live_membership: bool = False,
    ) -> UNSPSCContract:
        """Create the default UNSPSC contract (common block first, specific after)."""
        return UNSPSCContract(
            excluded_rules=frozenset(excluded_rules or ()),
            pinned_rules=frozenset(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars or ()),
            include_business_function=include_business_function,
            include_live_membership=include_live_membership,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: UNSPSCNotation,
    ) -> str:
        """Render the 8-digit stem in the requested format.

        The default ``"unspsc"`` path is the identity. ``"segmented"``
        pair-hyphenates, ``"labeled"`` prefixes ``UNSPSC ``, ``"native"``
        restores the spelled length (6-digit alias or 10-digit suffix).
        Never affects candidate identity or provenance.
        """
        if output_format == "segmented":
            return f"{value[0:2]}-{value[2:4]}-{value[4:6]}-{value[6:8]}"
        if output_format == "labeled":
            return f"UNSPSC {value}"
        if output_format == "native":
            if notation.native_length == 6:
                return value[:6]
            if notation.native_length == 10:
                return value + notation.function
            return value
        return value
```

Registration via `tools/new_capability.py` (see §10.1).

---

## 7. Validation — three levels

### 7.1 Level 1 Generic structure, Level 2 Level-padding, Level 3 Codeset membership (+ BFI suffix)

**Level 1 — generic structure (`Section1HierarchyStructure`, PARSER, always-active).** Formal regex on the grammar-normalized stem: `^[0-9]{8}$` with `native_length in {6, 8, 10}` recorded at recognition. Worked examples: `44103103` ✓ (8 digits); `441217` ✓ (6-digit lane, pads to `44121700` before Level 2); `4410310314`-shape ✓ (10-digit lane, stem `44103103` + function `14`); `4410310` (7) ✗ never reaches rules (grammar rejects); `43.21.15.03` ✗ never reaches rules (grammar rejects internal separators). Letter-expansion table: none — digits only, no `A=10…Z=35` mapping exists (contrast IBAN/ISIN/LEI).

**Level 2 — level-padding consistency (`Section2LevelPadding`, PARSER, always-active).** The `00`-pair lattice must be well-formed: a code ending `000000` claims segment; `0000` family; `00` class; else commodity. Mid-zero anomalies (`00101501`, `43001503`) fail here even if every digit is ASCII — the padding lattice is positional law, not vocabulary. Worked examples: `43000000` → segment ✓; `43210000` → family ✓; `43211500` → class ✓; `43211503` → commodity ✓; `43001503` → INVALID (family pair `00` followed by non-zero class pair breaks the lattice).

**Level 3 — codeset membership (`Section3CodesetMembership`, LOOKUP_TABLE, always-active at pinned v26.0801).** Stem must exist in the snapshot AND every pair-prefix ancestor must be a live node (`43…` → `43000000` live; `4321…` → `43210000` live; `432115…` → `43211500` live). This is the ISBN-`Section4RegistrantRange` shape: hierarchical longest-match against a shipped table, `requires_features=frozenset()` at v1, optional `include_live_membership` interpretation for fresher snapshots. Worked examples: `44103103` (printer/facsimile toner) ✓ issued; `25101703` (ambulance) ✓; `11101803` (platinum) ✓; `44103199` (well-formed, unissued — illustrative) → INVALID; `99999999` (no segment 99) → INVALID.

**BFI suffix (`Section4BusinessFunctionSuffix`, PARSER, gated by `include_business_function=True`).** The 10-digit lane splits stem + 2-digit function; any `00`–`99` function value passes (BFI values informative only; UNECE PDF direct-fetch blocked so no value table is cited as verified). With `include_business_function=False`, 10-digit recognitions route to no validating rule for their full length → INVALID (recognized, no authority validates the suffix lane), while the 8-digit stem in isolation would still validate — this is the intended two-locus gating semantic (grammar runs, rule dropped → INVALID, never MISSING).

### 7.2 What makes a code "valid" vs "well-formed" vs "issued/live"

- **Well-formed (generic + padding)** — correct length lane, ASCII digits, lattice-consistent padding; always-active PARSER pair. Analogous to ISBN structurally-valid or IBAN generic-valid.
- **Issued (codeset member at pinned snapshot)** — well-formed plus stem in v26.0801 plus live ancestors; always-active LOOKUP_TABLE at v1. Analogous to ISBN allocated or ISSN issued.
- **Live-registered (at rolling HEAD)** — issued plus present in the freshest UNDP release the estate tracks; gated `include_live_membership` interpretation. Analogous to BIC Directory liveness or ISBN range-message rolling refresh. Determinism is by snapshot: the same input + contract + library snapshot always yields the same verdict; across snapshots a moved/inactivated code (v24 moved 6, deleted 1) flips SUCCESS → INVALID with the new provenance version.

Like ISBN valid vs allocated, ISSN valid vs issued, IBAN valid vs country-valid.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase label | `unspsc 44103103` → SUCCESS `44103103` | Label lane is case-insensitive; digits unaffected |
| 2 | Zero-padded parent segment | `43000000` → SUCCESS (level segment) | Valid code in its own right, not a prefix |
| 3 | Zero-padded parent family/class | `43210000` / `43211500` → SUCCESS | Same; `00`-pairs mark level per UNGM/Cornell |
| 4 | 6-digit class shorthand | `441217` → SUCCESS `44121700` | SAP + CA attested alias; grammar pads, rule looks up padded stem |
| 5 | 10-digit BFI suffix | `XXXXXXXXBB` → SUCCESS stem (function trace-only) | Wikidata + UNECE attested; suffix informative only |
| 6 | Label present | `UNSPSC 44103103` / `UNSPSC: 44103103` → SUCCESS, span includes label | Fused pattern; notation holds digits only |
| 7 | MDM system-ID prefix | `UNSPSC000.44103103` → SUCCESS `44103103` | Stibo default ID lane; prefix stripped |
| 8 | CSV header lane | `unspsc,43211509` (shape; exact full row unverified) → SUCCESS `43211509` | Comma is a field separator; word guards split correctly |
| 9 | Over-long (9/11 digits) | `441031031` / `44103103144` → MISSING | Length guard; only 6/8/10 ever match |
| 10 | Under-long (7 digits) | `4410310` → MISSING | Same; grammar admits exactly 6/8/10 |
| 11 | Internal spaces/dots/hyphens | `43 21 15 03` / `43.21.15.03` / `4410-3103` → MISSING | No separator tolerance at v1 (digits-only wire); grouped display is DEFER/red |
| 12 | Float-mangled export | `44103103.0` → SUCCESS `44103103` (span excludes `.0`) | `unspsc-fr` attests `.0` CSV damage; word guard leaves the tail outside |
| 13 | Invalid hierarchy padding | `43001503` → INVALID | Lattice violation (Level 2 PARSER rejects) |
| 14 | Well-formed but unissued | `44103199`-shape → INVALID | Membership claimed by Level 3 LOOKUP_TABLE |
| 15 | Truncated prose prefix | `43` / `4321` alone → MISSING | Exposition, not data; real codes are `43000000` / `43210000` |
| 16 | Embedded in sentence | `Printers (44103103) approved` → SUCCESS with span | Word-boundary guards; parenthetical not swallowed |
| 17 | Two distinct in one slice | `44103103, 43211503` → AMBIGUOUS / MultipleMentionsError | Single-slice ambiguity; use segmentation |
| 18 | GTIN-8 collision | `12345678`-shape valid in both lanes → SUCCESS per contracting capability | Same-span cross-capability readings are caller-routed (one `canonicalize()` call = one capability); within UNSPSC the verdict is membership, within GTIN the verdict is check digit |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid commodity/parent at pinned snapshot | SUCCESS → 8-digit stem | Structure + padding + membership all pass |
| Valid 6-digit alias / label / MDM prefix / BFI form | SUCCESS (same 8-digit stem) | Presentation/alias-only dedup; `native` format restores spelling |
| Space-grouped pairs `43 21 15 03` | MISSING | No grammar claims internal-space form at v1 (DEFER extension) |
| Dotted/hyphenated `43.21.15.03` | MISSING | Never a UNSPSC form (REJECT); no grammar claims |
| Truncated `43` / over-long 9-digit | MISSING | No grammar claims wrong-length digit runs |
| Well-formed but unissued / bad padding / unknown segment | INVALID | Claimed by grammar, rejected by Level 2/3 rules |
| No digit runs of length 6/8/10 | MISSING | No grammar recognized |
| Two distinct valid in one slice | AMBIGUOUS / MultipleMentionsError | Single-slice ambiguity, use segmentation |
| Inactivated/moved code at rolling HEAD with `include_live_membership=True` | INVALID | Authority feature gating (dropped/changed row in fresher snapshot) |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py UNSPSC --name unspsc --authority "United Nations Development Programme" --spec-name "UNSPSC Codeset Release" --spec-url "https://www.undp.org/unspsc" --publication-year 2023 --spec-version "v26.0801 (2023-08-14)" --default-format unspsc
```

Creates 13 files + one edit: `paxman/capabilities/UNSPSC/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance. After scaffolding, add the UNGM-structure file (`rules/undp_unspsc_structure_ed2025.py`) and the UNECE-BFI file (`rules/unece_bfi_ed2005.py`) manually, splitting the placeholder rule into Section 1/2/4, and add the codeset snapshot under `rules/data/`.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[UNSPSCRecognitionGrammar()]`; `active_grammars` omitted at v1 (base `None` runs every shipped grammar — UNSPSC has no input-shape feature to gate).
- Each grammar carries `name = "unspsc_recognition"` and non-empty `semantics = "unspsc_recognition"`; every rule's `target_semantics = frozenset({"unspsc_recognition"})`.
- `include_business_function` gates the BFI rule via `requires_features={"include_business_function"}` (dropped rule → INVALID for 10-digit inputs); `include_live_membership` gates the rolling-liveness interpretation (default `False`).

### 10.3 Cross-cutting invariants (fail review if violated)

- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports (import only from `paxman.core`, import-linter enforced) — GTIN/ISBN/Country tables are precedent to read, never to import.
- No `output_format` token in any `paxman/capabilities/*/rules/` module (source-scan) — `segmented`/`labeled`/`native` live in `capability.py:format_value()` only.
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts.
- Deterministic by construction: same input + contract + library snapshot → same output (codeset version pinned in `Provenance.version`).

---

## 11. Recommended File Layout (mirrors ISBN and GTIN)

```
paxman/capabilities/UNSPSC/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── unspsc_recognition.py
└── rules/
    ├── __init__.py
    ├── undp_unspsc_structure_ed2025.py
    ├── undp_unspsc_codeset_ed2023.py
    ├── unece_bfi_ed2005.py
    └── data/
        ├── __init__.py
        └── unspsc_codeset.py
```

Per-registry data module shape (parallel to ISBN `rules/data/range_message.py`):

```python
# rules/data/unspsc_codeset.py
"""Generated UNSPSC codeset snapshot — do not edit by hand.

Source: UNDP English XLSX (v26.0801, 2023-08-14).
Regenerate via tools/regenerate_unspsc_data.py from
paxman/shared_data/unspsc_snapshot.json.
"""

CODESET_VERSION: str = "v26.0801 (2023-08-14)"
LIVE_STEMS: frozenset[str] = frozenset({...})  # 8-digit stems, ~158k
```

A `tools/regenerate_unspsc_data.py` + `paxman/shared_data/unspsc_snapshot.json` pair (Currency/ISBN/BIC/IBAN precedent) keeps the snapshot refreshable without hand-editing the generated module.

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISBN §9)

- Grammar tests: valid 8-digit commodity/segment/family/class, 6-digit alias (+`"00"` padding assertion), 10-digit split, lowercase label, `UNSPSC000.` MDM lane, CSV-comma lane, multiple matches, dotted/hyphenated/spaced negatives, 7/9/11-digit negatives, truncated `43` negative, float-tail span (`44103103.0` matches `44103103` only), span invariants (`raw_text` includes label, `notation.digits` excludes it), name/semantics, boundary-guard negatives (`X44103103`, `44103103Y`) — plus one positive vector per §2.1 RECOGNIZE form.
- Rule tests: Level-1 structural valid/variant/invalid, `normalize()` exact 8-digit stem, provenance attributes (`authority`, `kind`, `version`, `lifecycle`, `publication_year`), name/strategy conventions (`Section N-*`, PARSER vs LOOKUP_TABLE), `target_semantics == frozenset({"unspsc_recognition"})`; Level-2 padding lattice valid + mid-zero invalid; Level-3 membership valid member + well-formed-but-unissued + ancestor-liveness (`43001503`-shape) invalid, `strategy == LOOKUP_TABLE`, `kind == "registry"`; BFI rule 10-digit pass + `requires_features` gate + suffix trace-only.
- Capability tests: notation frozen/hashable/slots, wiring counts (1 grammar, 4 rules), grammar/rule name conventions, `format_value` round-trips (`unspsc` identity, `segmented` pair-hyphenation, `labeled` prefix, `native` 6/8/10 restoration), `create_contract` factories.
- Integration: MISSING (spaced/dotted/wrong-length/truncated), INVALID (bad padding, unissued, BFI-gated-off 10-digit), SUCCESS (commodity/parent/alias/label/MDM), AMBIGUOUS or MultipleMentionsError (two distinct), `_clean_registry` fixture, determinism/`VersionStamp`, span-bearing match, dedup.
- Property tests (hypothesis): pick live stem from snapshot → must canonicalize to itself; random 8-digit strings → INVALID with high probability (≈1 − 158448/10⁸); 6-digit alias vs padded stem identical post-`normalize()`; `format_value` round-trip (`segmented` → re-parse → same stem); non-digit mutations → MISSING.
- Consistency test: every snapshot stem's pair-prefix ancestors resolve in the snapshot (prefix-liveness closure); every `target_semantics` claimed by a rule is produced by a shipped grammar.
- Presentation purity: `output_format` source scan over `rules/`.
- Real vectors: `44103103` (toner), `43211503`, `10101501`, `25101703` (ambulance), `11101803` (platinum), `11101709` (antimony), `43000000`, `43210000`, `43211500`, `441217`, `UNSPSC 44103103`, `UNSPSC: 44103103`, `UNSPSC000.44103103`, `unspsc,43211509` (shape; exact row unverified), `43001503` (INVALID), `44103199`-shape (INVALID), `43 21 15 03` (MISSING at v1).

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `unspsc` vs `segmented` vs `labeled` | Default `unspsc` (8-digit compact); offer `segmented`, `labeled`, `native` | Wire vs human readability; SAP/O*NET/Wikidata all store bare digits; display forms are presentational-only (ADR-0011) |
| 2 | Single grammar vs N grammars | Single `unspsc_recognition` with longest-first alternation (10/8/6) + fused label | Keeps surface minimal; avoids cross-grammar containment spurious AMBIGUOUS (10-digit stem contains 8-digit prefix) |
| 3 | Membership lenience vs strict | Ship structure + padding PARSERs + membership LOOKUP_TABLE all always-active at pinned v26.0801 | Mirrors well-formed vs issued split; 158k-row set membership is cheap; snapshot pin preserves determinism |
| 4 | Grammar length strictness | Grammar enforces {6, 8, 10} exactly via alternation; never 7/9/11, never 2/4 | Keeps grammar cheap and definitive; SAP accepts only 6/8; Wikidata admits only 8(+2) |
| 5 | Case/separator normalization in grammar vs rule | Grammar folds label case and strips the label/MDM lane; rules validate digits only; internal separators never stripped | Syntax not semantics; digits-only wire is multiply attested, separator tolerance is unattested |
| 6 | Business-function suffix semantics | Informative only; any `00`–`99` passes when `include_business_function=True`; dropped rule → INVALID for 10-digit | UNECE defines values but no validity split; routing hint, not validity (BIC test/passive-flag precedent) |
| 7 | Single PUBLICATION vs split | Split three ways: UNGM-structure (spec) + UNDP-codeset (registry) + UNECE-BFI (spec) | One file per publication is the HOW_TO rule; fused would mix specification and registry lifecycles |
| 8 | `single_value` for batch | `True` initially; segmentation for multi-code rows; offer `extra_grammars` batch variant with `False` | Consistent with GTIN/ISBN/ISIN/Country precedent; catalog lines are multi-entity by authorial choice |
| 9 | Internal-separator tolerance | Contiguous digits only at v1; spaces/dots/hyphens → MISSING | No validator strips them; O*NET `Decimal(8,0)` proves storage has none; ISBN/Phone analogy explicitly rejected with evidence |
| 10 | Label span inclusion | Include label in `raw_text` span (fused regex); `notation.digits` label-free | Mirrors ISBN/ISSN/IBAN label handling; preserves UX highlighting without polluting identity |
| 11 | Which alternative written forms does v1 recognize (space-grouped pairs `43 21 15 03`)? | DEFER to `unspsc_grouped_recognition` community extension via `extra_grammars`, citing §2.1 | Prose-only attestation, zero wire validators; unhandled-at-v1 is a documented scope cut, not a blind spot — planners see it here |

---

## 14. Ambiguity Analysis (Paxman-specific)

- No inherent UNSPSC-vs-UNSPSC positional ambiguity — fixed 6/8/10 widths eliminate the reordering ambiguity Date exhibits; the longest-first alternation resolves the 10-contains-8 nesting inside one grammar, and two distinct codes in one slice are authorial choice (segmentation intended), not lexical ambiguity.
- UNSPSC vs GTIN-8 overlap is not lexical ambiguity — the same 8 digits may be a live UNSPSC stem and a check-valid GTIN-8 simultaneously (e.g. an illustrative `12345678`-shape). Each capability answers for its own authority in its own `canonicalize()` call (membership vs Mod-10); there is no cross-capability arbitration in the engine, so this is caller routing, not a coin flip.
- Parent vs commodity is not ambiguity — `43211500` (class) and `43211503` (commodity) share six digits but are distinct canonical values with distinct titles and levels; the padding lattice plus membership lookup keeps them apart exactly as ISBN prefix vs group vs registrant ranges stay apart.
- 6-digit alias vs 8-digit padded is not ambiguity — `441217` normalizes to `44121700` deterministically (right-pad `"00"`), and `native` format restores the spelling; same entity, two encodings (ADR-0011), one dedup key.
- Staleness is not ambiguity — a code moved/inactivated between UNDP releases (v24 moved 6, deleted 1) resolves against the pinned snapshot with its `Provenance.version`; determinism-by-snapshot plus `include_live_membership` gating turns version drift into a citable INVALID, not a competing reading.

---

## 15. URL Reference (authoritative, fetched 2026-09-30)

| Claim | URL | Kind |
|-------|-----|------|
| UNDP owns UNSPSC; open global standard; free codeset download `unspsc-english-v260801.1.xlsx`; contact `info.unspsc@undp.org` | https://www.undp.org/unspsc | primary |
| Four-level hierarchy, purely numeric; `XX000000`/`XXXX0000`/`XXXXXX00`/`XXXXXXXX`; replaced UNCCS 2012; search + Export to Excel | https://help.ungm.org/hc/en-us/articles/360012816160-What-are-UNSPSC-codes- | primary |
| UNSPSC search (live directory) | https://www.ungm.org/Public/UNSPSC | primary |
| DCMI MSI entry: MoU 1998, ECCMA→GS1 US→UNDP lineage, structure table, v26.0801 158,448 items, 14 languages, implementations, related standards | https://msi.dublincore.org/standards/unspsc | primary (index) |
| Wikidata P2167: mandatory `\d{8}(\d{2})?`, URL patterns, examples 25101703/11101803/11101709, link-rot on unspsc.org formatter, live source UNGM | https://www.wikidata.org/wiki/Property:P2167 | primary (constraint mirror) |
| Wikidata item Q1361569 (UNSPSC scheme identity) | https://www.wikidata.org/wiki/Q1361569 | secondary |
| SAP Business Network commodity codes: 8-digit lane, 6/8-digit only, v25.9 lane (snippet-level), `44121706` example | https://help.sap.com/docs/business-network-for-procurement/managing-network-catalog/commodity-codes | primary (snippet-level; direct HTML fetch empty) |
| Stibo STEP UNSPSC format: `UNSPSC000.` default ID prefix | https://doc.stibosystems.com/doc/version/2026.1/web/content/dataexc/datafmt/unspsc_format.html | primary |
| UNECE Classification Guidelines v2.04: BFI optional 2-digit suffix (direct PDF fetch 403; corroborated via secondary) | https://unece.org/fileadmin/DAM/trade/agr/meetings/ge.11/2005/2005_i04_UNSPSC.pdf | primary (citation; direct-quote verification blocked) |
| Cornell procurement buyer guide: `44121706` wooden pencils, eight-digits-four-classifications | https://finance.cornell.edu/procurement/buyers/unspsc | primary |
| CA DGS UNSPSC page: `SSFFKKCCBB`, `43211602` docking stations, 6+8-digit custom lists, BFI unused | https://www.dgs.ca.gov/PD/Resources/Page-Content/Procurement-Division-Resources-List-Folder/United-Nations-Standard-Products-and-Services-Code-UNSPSC | primary |
| O*NET UNSPSC reference: `Decimal(8,0)` storage | https://www.onetcenter.org/dictionary/27.2/mssql/unspsc_reference.html | primary |
| `unspsc-fr`: lookup + search + export, float→int normalisation, v26.0801, 149,849 commodities (GitHub-verified; PyPI bot-gated) | https://pypi.org/project/unspsc-fr | primary (index; body via repo) |
| `unspsc-fr` repo: `get`/`children`/`ancestors` + `search` API, SQLite/JSON/Parquet export | https://github.com/codebysaadbouh/unspsc-fr | primary |
| python-stdnum docs index: no UNSPSC; NACE/EAN/GS1-128/CUSIP/ISIN/BIC/IBAN/LEI siblings | https://arthurdejong.org/python-stdnum/doc/ | primary (negative) |
| validator.js repo: no `isUNSPSC` in README validator table (file-level `src/lib/` listing not enumerated; no counter-evidence) | https://github.com/validatorjs/validator.js | primary (negative) |
| Wikipedia UNSPSC: version table, lineage, segment-57, BFI level (sole source for pre-v26 counts — secondary) | https://en.wikipedia.org/wiki/UNSPSC | secondary |
| WisePIM taxonomy guide: label lanes, segment/family/class prose breakdowns (stale governance/counts — prose lanes only) | https://wisepim.com/guides/product-taxonomy/unspsc | secondary (stale) |
| BIC research precedent (template) | docs/development/research/2026-08-23-bic-canonicalization.md | primary (repo) |
| IBAN research precedent (checksum-depth complement) | docs/development/research/2026-08-22-iban-canonicalization.md | primary (repo) |
| ISSN research precedent (concise single-grammar) | docs/development/research/2026-08-21-issn-canonicalization.md | primary (repo) |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary (repo) |
| Paxman shipped precedent: GTIN grammar/rules/data + notation | paxman/capabilities/GTIN/grammar/gtin_recognition.py, paxman/capabilities/GTIN/rules/gs1_prefix_ed2026.py, paxman/capabilities/GTIN/rules/data/gs1_prefix.py, paxman/capabilities/GTIN/notation.py | primary (repo) |
| Paxman shipped precedent: ISBN range-message registry rule + data + grammar | paxman/capabilities/ISBN/rules/isbn_range_message_ed2026.py, paxman/capabilities/ISBN/rules/data/range_message.py, paxman/capabilities/ISBN/grammar/isbn13_recognition.py | primary (repo) |
| Paxman shipped precedent: ISIN prefix allowlist, Country/Currency tables, engine dedup | paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py, paxman/capabilities/Country/rules/iso_3166_ed2024.py, paxman/engine/orchestrator.py, paxman/core/domain.py | primary (repo) |

---

## 16. Evidence Completion — Resolved

This report's UNSPSC-specific authoritative evidence has been fetched and cited (2026-09-30):

- [x] Owner + RA pages: UNDP ownership (ex GS1 US 2003–2024, UNDP since 2025-01-01), `info.unspsc@undp.org`, free XLSX `unspsc-english-v260801.1.xlsx`, UNGM search + Export to Excel; lineage table back to 1998 MoU (ECCMA v6.0315 → GS1 US → UNDP, v08.1201 → v26.0801)
- [x] NOT-an-ISO-standard proved (no catalogue entry; ISO 22745/8000 are dictionary-infrastructure siblings) with related-scheme map (UNCCS/CPV/ECLASS/GPC/NAICS/HS)
- [x] Structure: 4-level `SSFFCCMM` positional pairs + optional `BB` business function, ASCII digits, zero-padding is structural, ≥6 worked examples across all levels
- [x] No checksum proved (UNGM "purely numeric" partition + Cornell 4×2 partition + CA DGS `SSFFKKCCBB` + Wikidata bare digit-count regex — four independent sources, zero check algorithms published)
- [x] Codeset size + versioning: v26.0801 158,448 (2023-08-14) + v24.0301 157,116 with deltas + new segment 57 + 14 languages + periodic cadence (pre-v26 counts flagged secondary)
- [x] Ecosystem regex consensus: Wikidata `\d{8}(\d{2})?` + SAP 6/8-digit + O*NET `Decimal(8,0)` + `unspsc-fr` float→int + Stibo `UNSPSC000.` lane (plus stdnum/validator.js confirmed absence)
- [x] Recognition-surface inventory complete (§2.1): 10 rows, every spec/schema/≥2-validator form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form
- [x] Wild input shapes validated (§2.2, 18 categories) against UNDP/UNGM/MSI + Cornell/CA-DGS + SAP/Ariba/PA-Jaggaer + Wikidata/PyPI/MDM
- [x] Label scope decision (fused `UNSPSC` + `code` + `:#|-.` + `UNSPSC000.` MDM lane, span includes label)
- [x] Parent/alias equivalence decision (parents distinct codes; 6-digit pads to `+00`; BFI splits 8+2 informative-only)
- [x] Separator decision (digits-only wire; spaces/dots/hyphens REJECT at v1 with evidence — ISBN/Phone analogy refused in writing)
- [x] Registry liveness scope decision (always-active pinned v26.0801 + `include_live_membership` rolling interpretation)
- [x] File layout / rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

---

## Appendix — What the Shipped GTIN, ISBN, ISIN, Country and Currency Capabilities Teach UNSPSC (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (explored 2026-09-30, not speculative) and anchors the proposal to what Paxman already ships.

GTIN (`paxman/capabilities/GTIN/notation.py:8-22`) teaches the notation facet pattern: `digits` plus `native_length` plus a trace-only marker (`has_ai`; UNSPSC analog: `function`). ISBN (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py:30-40`) teaches the single-grammar staged pipeline (`PipelineGrammar` + `StandardPre(empty_guard=True)` + `RegexStage` with module-scope pattern, fused label, digit-continuation lookarounds). ISBN's `Section4RegistrantRange` (`paxman/capabilities/ISBN/rules/isbn_range_message_ed2026.py:13-33`, data in `rules/data/range_message.py` with `EAN_PREFIX_RULES`/`GROUP_RULES` longest-match via `find_registrant_length`) is the direct model for UNSPSC Level-3 membership: hierarchical table walk, `LOOKUP_TABLE`, `kind="registry"`, `requires_features={"include_range_validation"}` gating when rolling. ISIN (`paxman/capabilities/ISIN/rules/anna_isin_guidelines_ed2025.py`) teaches the small-allowlist alternative (`_VALID_PREFIXES`) — rejected for UNSPSC because 158k stems need a full snapshot, not a prefix set. Country/Currency (`rules/data/*.py` plain `frozenset` tables; Currency snapshot + `tools/regenerate_currency_data.py` from `paxman/shared_data/currency_snapshot.json`) teach the snapshot+regenerate lifecycle the UNSPSC codeset must follow. The engine (`paxman/engine/orchestrator.py`: `_enforce_single_value_invariant`, `_dedup_candidates` on `(value, recognition_rule, validation_rule)`, `_determine_status` MISSING-vs-INVALID split, `_format_candidates` after dedup) teaches that `output_format` never affects identity — the ADR-0011 guarantee the `segmented`/`labeled`/`native` formats rely on. The four architectural lessons for UNSPSC:

1. **Grammar strips, rule validates, capability formats.** The label/MDM lane and 6-digit padding are syntax (grammar); padding-lattice and membership are semantics (rules); pair-hyphenation and labeling are display (`format_value`). No layer borrows another's job.
2. **One file per provenance, one class per section.** UNGM-structure (spec) + UNDP-codeset (registry) + UNECE-BFI (spec) stay in three files with three `PUBLICATION` constants; `Section N-*` naming throughout.
3. **No `output_format` in rules, ever.** `segmented`/`labeled`/`native` appear only in `capability.py`; `normalize()` always returns the 8-digit stem.
4. **Single grammar with optional group avoids spurious AMBIGUOUS; cross-grammar containment is preserved.** The 10-contains-8 nesting that would poison a two-grammar split is handled longest-first inside one pattern — the BIC-8-vs-11 lesson applied to digits.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for UNSPSC. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the deeper ISBN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
