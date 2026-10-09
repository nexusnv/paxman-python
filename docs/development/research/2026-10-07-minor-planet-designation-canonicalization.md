# Minor Planet Designation Canonicalization Research — paxman-python

**Date:** 2026-10-07
**Scope:** Primary-source survey of the IAU Minor Planet Center designation system (unpacked provisional designations, packed designations incl. the extended LSST-era scheme, Palomar-Leiden/Trojan survey designations, permanent numbers, and the naming process), ecosystem parsing practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `MinorPlanet` capability. No source code, tests, or configuration were modified.
**Evidence basis:** MPC "New- And Old-Style Minor Planet Designations" (DesDoc, fetched 2026-10-07), MPC "Packed Provisional and Permanent Designations" (PackedDes, fetched 2026-10-07), MPC "How Are Minor Planets Named?" (HowNamed), MPC provisional-designation definition + cometary-designation system + dual-status objects ops-docs pages, MPC designation-identifier API docs, MPC 80-column optical-observation format (OpticalObs), MPC NEO Confirmation Page (live examples), IAU ADES `submit.xsd` (`PermIDType`/`BaseProvIDType`/`OldProvIDType`, fetched 2026-10-07), WGSBN naming rules (snippet-sourced), JPL SBDB API + Horizons Lookup API accepted-input docs, `sbpy.data.Names` parser/packer (reference-quality), `astroquery.mpc` target parser, `rlseaman/MPC_designations` multi-language library + SPECIFICATION.md, `jorbit.utils.mpc`, Project Pluto find_orb pack/unpack + `packed.htm` + `pack.txt` proposal, Rubin/LSST PPDB schema (fields, no validator), Wikidata Property P5736 (mandatory regex `[A-Z0-9][A-Z0-9/ ()-]{0,11}`, fetched 2026-10-07), python-stdnum absence survey, validator.js absence survey, Wikipedia provisional/minor-planet-designation pages (secondary, flagged where sole source), and shipped Paxman capabilities (ISBN, ISSN, GTIN, Country, ISIN) as architectural precedents. Repo state: `feature/unspsc-capability` @ `6e23075` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN research precedent `docs/development/research/2026-08-21-issn-canonicalization.md` plus the IBAN precedent `docs/development/research/2026-08-22-iban-canonicalization.md` and the BIC precedent `docs/development/research/2026-08-23-bic-canonicalization.md`.

> Note on scope: "astronomy and astrophysics" admits many identifiers (constellation abbreviations, comet designations, Messier/NGC numbers, spectral types). This report covers **minor-planet designations only** (provisional + packed + survey + permanent numbers), the richest strict-grammar surface with a single stable authority (MPC/IAU). Comets, natural satellites, and bare names are surveyed as explicit DEFER/REJECT dispositions, not silent gaps. Registry name: `minor_planet`. Package name: `MinorPlanet`. Export alias: `MinorPlanet`.

---

## Executive Summary

Minor-planet designations are a strong fit for a Paxman capability: they have an unambiguous canonical form (**unpacked designation, uppercase, single-space**: `YYYY LL[n]` provisionals such as `1995 XA` / `2007 TA418`, `NNNN P-L` / `NNNN T-n` surveys such as `2040 P-L`, parenthesized permanent numbers such as `(433)`), a stable single-authority standard (**IAU Minor Planet Center**, hosted by the Center for Astrophysics | Harvard & Smithsonian and funded by NASA, current system in force since **1925**, packed forms documented without version break), a machine-compact wire encoding (**7-character packed provisionals** `J95X00A`, 5-character packed numbers `03202`/`A0345`/`a0017`/`~000z`, survey packs `PLS2040`, LSST-era extended `_`-prefixed base-62 packs), and a well-understood human-readable presentation (**unpacked with single space on the wire; lowercase and underscore tolerated from resolver/API lanes; packed case is significant** — `a0017` ≠ `A0345`). The domain mirrors Paxman's value proposition for ISBN and UNSPSC: recognizing tolerant human surface (case/underscore/packed variants), validating strictly against authority letter-sets and positional decode coherence, returning one canonical unpacked value with provenance. Minor-planet designations have **no checksum** — validity is pure syntax (year lane + half-month/second letter sets + cycle coherence + packed positional decode), exactly like BIC (structure is all there is) and like UUID (structure-only v1 with no registry).

Key findings that shape the design:

1. **Canonical form is the unpacked designation, uppercased, single-spaced** (provisional `1995 XA`; survey `2040 P-L`; number `(433)` with parentheses). The packed form (`J95X00A`) is the same-entity wire encoding, not a distinct identity — exactly the ISBN compact/hyphenated pair, and the offered `packed` format re-enters through the packed branch. Parentheses are load-bearing for numbers: bare `433` is unclaimable in free text (parens required), while JPL's bare-number search lane is resolution, not grammar.
2. **One grammar suffices, with lane-aware alternation.** Unpacked provisional (+ `A8xx`/`A9xx` retrospective lane, `A/`-prefixed lane, underscore lane), packed 7-char (case-sensitive), extended `_` base-62 (case-sensitive), survey unpacked + packed, parenthesized numbers, and packed numbers are disjoint shapes inside one alternation — no cross-grammar containment, no spurious `AMBIGUOUS` (longer-wins is per-grammar only, `orchestrator:_dedup_spans`). Comets get a future second grammar with a distinct semantics id (disjoint namespace), never a coalesced one.
3. **Validation is structure-only at v1, no checksum, no registry.** Level 1: unpacked shape (year lane `A[89]\d{2}|19\d{2}|20\d{2}`, single space/underscore, half-month `[A-HJ-Y]` with I omitted and Z unused, second letter `[A-HJ-Z]` with I omitted, optional cycle digits). Level 2: packed decode coherence (century `IJK` = 18/19/20, cycle letter value A=10…Z=35/a=36…z=61 ×10 + units, tilde base-62 number−620000 arithmetic, survey-pack codes). Level 3: permanent-number shape (`(433)`: positive integer, no leading zeros). All PARSER, always-active; the ADR-0012 vacuity exception covers PARSER-without-LOOKUP exactly as it does ISSN's check-digit rule. "Issued" (actually assigned by MPC) is unknowable without a registry, so v1 collapses valid-vs-issued honestly — a future MPCORB-snapshot LOOKUP_TABLE is the named upgrade path, not silent overclaim.
4. **Case is lane-relative, not global.** Unpacked input folds to uppercase (`2003 cp20` → `2003 CP20`; glued `2003cp20` without separator stays MISSING — JPL resolution liberality, not grammar); packed case is significant and must never be folded (`a0017` = 360017 vs `A0345` = 100345; extended-scheme lowercase carries cycle magnitude). The pattern therefore compiles **without** `re.IGNORECASE`: unpacked classes are explicit `[A-Za-z]`, packed classes are exact-case. One flag decision, enforced by construction.
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): MPC unpacked-designation definition (DesDoc) owns provisional structure + survey forms; MPC packed-designation spec (PackedDes) owns packed/extended/tilde decode coherence; MPC naming/numbering process (HowNamed) owns the permanent-number rule. NOT an ISO standard — there is no ISO catalogue entry to cite, and ADES (IAU XML schema with normative `provID` regexes) is corroborating ecosystem evidence, not a rule publication at v1.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---

## 1. Target User

| Persona | Why they need minor-planet canonicalization | Typical context |
|---------|---------------------------------------------|-----------------|
| **Survey alert-broker engineers** | Normalize `2003 cp20` vs `2003 CP20` vs `K03C20P` to one key for cross-match joins across ZTF/LSST/MPC feeds | Rubin/LSST, ZTF, Pan-STARRS alert pipelines; NEOCP ingestion |
| **Orbit-computation / data engineers** | Roll packed MPCORB columns, unpacked MPEC strings, and API search strings up to one canonical designation with span-bearing provenance | find_orb/digest2-adjacent ETL, MPCORB snapshot joins, observation-archive dedup |
| **Observation planners / follow-up tools** | Validate user-supplied designations at form ingest; reject structurally invalid vs unresolvable input with `MISSING`/`INVALID` semantics | NEO follow-up report forms, telescope target lists, MPChecker-style UX |
| **Catalog / cross-reference librarians** | Pin `1997 RO4` vs `2007 FK34` as distinct designations (same body, different mentions) while expanding packed↔unpacked losslessly | JPL SBDB ↔ MPC ↔ Wikidata (P5736) joins, dual-status bookkeeping |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many designations) and a contract; Paxman returns one canonical designation (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ISBN (compact/display same-entity encodings) and UNSPSC (digits-only wire, presentation-only variants) ergonomics, but the canonical default is the **unpacked human-readable form** (`1995 XA`, `(433)`), with `packed` as the offered wire encoding.

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

Surveyed from MPC DesDoc/PackedDes/HowNamed (spec), ADES `submit.xsd` pattern facets (schema), ecosystem parser strip logic (`sbpy`/`astroquery` regexes, JPL SBDB/Horizons accepted-input docs, MPC identifier-API accepted inputs), and real-world carriers (MPEC strings, MPCORB packed columns, NEOCP temp IDs, db_search equation headings). There is no resolver-URI lane for individual designations (Wikidata P5736 formatter URLs are link-shaped search links, and Horizons is space-sensitive) and no prose-label lane (`MPC:`/`DES:` unattested) — unlike ISBN/ORCID, the carrier set is pure structure, not labels.

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Unpacked provisional | `1995 XA`, `2007 TA418` | DesDoc (canonical definition); MPC db_search headings; sbpy; ADES `BaseProvIDType` | canonical, dominant | RECOGNIZE | main pattern body |
| Lowercase unpacked | `2003 cp20`, `1995 xa` | JPL SBDB (spaced lowercase accepted); general prose | common (APIs, prose) | RECOGNIZE | explicit `[A-Za-z]` classes, fold-upper in notation |
| Underscore separator | `1995_XA` | sbpy + astroquery patterns (`[ _]`); JPL-adjacent lanes | common in code | RECOGNIZE | `[ _]` separator class |
| Retrospective A-prefix | `A904 OA` (= Jul 1904, 2nd half) | DesDoc (pre-1925 extension); ADES `OldProvIDType` (`A[89]\d{2} …`) | rare, official | RECOGNIZE | year-lane alternation `A[89]\d{2}` |
| `A/`-prefixed provisional | `A/2017 U1` | MPC designation-identifier API (accepted as minor-planet input) | rare, official | RECOGNIZE | `A/`-prefix branch |
| Packed 7-char | `J95X00A`, `K07Tf8A` | PackedDes (normative); MPCORB columns; JPL `K03C20P`; Rubin PPDB char fields | canonical wire, dominant in data | RECOGNIZE | case-sensitive branch |
| Extended packed | `_QC0000` (= `2026 CA620`) | MPC ops docs (Oct-2023 newsletter scheme, LSST-era) + sbpy `from_packed` | rare today, growing | RECOGNIZE | `_` + base-62 branch (exact year-letter mapping verified at implementation) |
| Survey unpacked | `2040 P-L`, `3138 T-1` | DesDoc; sbpy; ADES (`\d{4} (P-L\|T-[123])`) | official, closed set | RECOGNIZE | number + identifier branch |
| Survey packed | `PLS2040`, `T1S3138` | PackedDes; sbpy `PLS…/T1S…` | wire form | RECOGNIZE | literal-prefix branch |
| Parenthesized number | `(433)`, `(274301)` | MPC display (`(274301) Wikipedia = …`); WGSBN bulletins | canonical for numbered | RECOGNIZE | parens branch (parens load-bearing) |
| Packed number | `03202`, `A0345`, `a0017`, `K3289`, `~000z` | PackedDes (normative, with base-62 arithmetic); MPCORB columns | wire form | RECOGNIZE | case-sensitive branch (see §4) |
| Trailing-name citation | `(433) Eros`, `(274301) Wikipedia` | MPC headings; WGSBN citations (number+name pairing) | common in prose | RECOGNIZE (number span only; name outside span) | parens branch + word boundary (name is trailing annotation) |
| Glued `1995XA` | — (unattested as valid) | sbpy requires `[ _]`; ADES requires literal space | none valid | REJECT | documented negative test (SBDB liberality is resolution, not grammar) |
| Bare number `433` | JPL search lane only | JPL SBDB `des`/`sstr` (resolution); never MPC display | data/API only | REJECT | documented negative test; parens required (JPL lane deferred) |
| Old-style `1892 A`, `1914 VV`, `1915 a`, SIGMA/Greek | Historical corpora | DesDoc old-style section (superseded 1925) | archival only | REJECT | documented negative test (distinct dead grammar) |
| Comet forms `C/1995 O1`, `1P/Halley`, `1994 P1-B` | MPC comet lists; JPL | live, disjoint namespace | DEFER | named `comet_recognition` second grammar (distinct semantics) |
| Satellite/ring `S/2000 J 11`, `R/…` | JPL discovery tables; MPC NatSats | live, disjoint namespace | REJECT | documented negative (not minor-planet namespace) |
| Interstellar `1I/2017 U1` | MPC/JPL | live, `I/` namespace | DEFER | with comets (not minor-planet lane) |
| Bare names `Eros`, `Chiron` | MPC headings (always number-paired); JPL search | common in prose | REJECT | documented negative (names are not designations; unbounded vocabulary) |
| Subscript cycle `1995 SA₁` | Print typography only | DesDoc ("should be subscript when possible") | print only | REJECT | ASCII-only wire (plain digits in all machine records) |

A v1 that does NOT recognize bare numbers states that explicitly here AND raises it as Open Decision §13 row 11: JPL's bare-number search lane (`des=4`, `sstr=163693`) is the one commonly seen form left out, because unparenthesized digit runs are unclaimable in free text without a registry — unhandled-at-v1 is a documented scope cut, not a blind spot.

### 2.2 Wild variants — adversarial mutations of each inventoried form

Enumerated from DesDoc/PackedDes/HowNamed, ADES XSD facets, NEOCP live examples, and parser regexes; stress-test every §2.1 RECOGNIZE form:

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical unpacked | `1995 XA`, `2007 TA418`, `1992 QB1` | Spec master form; space significant |
| 2 | Lowercase / mixed case | `2003 cp20`, `1995 xa`, `2007 ta418` | Fold-upper in notation (unpacked lane only; glued `2003cp20` without separator stays MISSING — JPL resolution liberality, not grammar) |
| 3 | Underscore separator | `1995_XA`, `2040_P-L` | `[ _]` class; span includes separator |
| 4 | A-prefix retrospective | `A904 OA`, `A801 AA` | `A[89]\d{2}` year lane; same two-letter tail |
| 5 | `A/`-prefixed | `A/2017 U1` | Slash-prefix branch; rare official |
| 6 | High-cycle unpacked | `2008 AA360`, `1998 SQ108` | `\d*` tail; subscript-in-print is plain digits on wire |
| 7 | Packed 7-char | `J95X00A`, `K07Tf8A`, `J95X01L`, `K99AJ3Z` | Case-sensitive; cycle letter×10+digit; never fold case |
| 8 | Packed lowercase trap | `a0017` (= 360017) vs `A0345` (= 100345) | Distinct values; case fold would merge them — must not |
| 9 | Extended packed | `_QC0000`, `_QCzzzz` | `_` + year-letter + half-month + 4×base-62 |
| 10 | Survey both spellings | `2040 P-L` / `PLS2040`, `3138 T-1` / `T1S3138` | Same entity, two encodings (ADR-0011) |
| 11 | Parenthesized number | `(433)`, `(274301)` | Parens load-bearing; span includes parens |
| 12 | Packed number | `03202`, `50000`, `A0345`, `a0017`, `K3289`, `~0000`, `~000z`, `~AZaz`, `~zzzz` | 5-char exact; tilde base-62 arithmetic |
| 13 | Trailing-name citation | `(433) Eros`, `(274301) Wikipedia = 1997 RO4` | Number span only; `=`-equations are multi-mention (segmentation) |
| 14 | Multiple per line | `1997 RO4 = 2007 FK34`, `1995 XA, 1995 XB` | 2+ matches; distinct values → AMBIGUOUS under single_value |
| 15 | Quoted / bracketed | `"1995 XA"`, `[(433)]`, `(see 2007 TA418)` | Inside punctuation; guards must still fire |
| 16 | Over-long / under-long | `199 XA` (3-digit year), `19955 XA` (5-digit), `J95X00` (6-char pack) | Year/branch length guards; never partial |
| 17 | X-glued runs | `X1995 XA`, `1995 XAY`, `QJ95X00A` | Longer alphanum token must not yield inner designation; `(?<!\w)`/`(?!\w)` + letter guards |
| 18 | Invalid letter slots | `1995 XI` (I half-month), `1995 IZ`, `1995 XZ` (Z half-month) | Grammar claims broad `[A-Za-z]`; rule rejects → INVALID (MISSING-vs-INVALID teeth) |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| ADES `submit.xsd` `BaseProvIDType` (normative facets) | `\d{4} [A-HJ-Y][A-HJ-Z]\d*` + `\d{4} (P-L\|T-[123])` + `[ADCPX]/\d{4} [A-Z]{1,2}\d*(-[A-Z])?` + `S/…` satellite branch — space-only, strict letter sets |
| ADES `OldProvIDType` | `A[89]\d{2} [A-HJ-Y][A-HJ-Z]` — retrospective lane, no cycle |
| ADES `PermIDType` | `\d+([IPD](-[A-Z]{1,2})?)?` + planet/parenthesized-satellite branches — bare numbers + periodic-comet suffixes |
| `sbpy.data.Names.parse_asteroid` | `(([1A][8-9][0-9]{2}[ _][A-Z]{2}[0-9]{0,3}\|20[0-9]{2}[ _][A-Z]{2}[0-9]{0,3})\|([1-9][0-9]{3}[ _](P-L\|T-[1-3])))` + packed `([IJKL][0-9]{2}[A-Z][0-9a-z][0-9][A-Z]\|PLS…\|T1S…\|T2S…\|T3S…)` + packed-number + name + bare-number branches; `from_packed('J95A01A')` → `'1995 AA1'`, `from_packed('_RD0aEM')` → `'2027 DZ6190'`, `to_packed` implements extended `_` + `~` schemes |
| `astroquery.mpc` target parser | `(^[0-9]*$)` number \| `(^[0-9]{1,3}[PDI](-[A-Z]{0,2})?$)` numbered comet \| `(^[PDCXA]/[- 0-9A-Za-z]*)(-[A-Z]{0,2})?$` comet \| `(^([1A][8-9][0-9]{2}[ _][A-Z]{2}[0-9]{0,3}$\|^20[0-9]{2}[ _][A-Z]{2}[0-9]{0,3}$)\|(^[1-9][0-9]{3}[ _](P-L\|T-[1-3]))$)` — unpacked-only input ("no packed designations are allowed"), packed handled on decode |
| MPC designation-identifier API | Accepts unpacked (`1984 KB`, `A/2017 U1`, `S/1900 J 10`), packed (`J84K00B`, `AK17U010`, `SJ00J100`), names, permanent IDs (`6063`, `1I`, `Jupiter X`), packed permanent (`06063`, `0001I`, `J010S`); returns `packed_*`/`unpacked_*` pairs (`2020 AB1` → `K20A01B`) |
| JPL SBDB API `sstr` | "designation in various forms (including MPC packed form) or case-insensitive name; any provisional designation associated with the object may be used" — e.g. `atira`, `2003 CP20`, `2003cp20`, `K03C20P`, `163693`; wildcard `*` allowed |
| JPL SBDB API `des` | "object designation (e.g., `2015 AB`, `141P`, `73P-C`, `1995 O1`) or IAU number (e.g., `4`); unnumbered comet designations do not require a prefix" — resolution, not grammar |
| JPL Horizons Lookup `sstr` | "name, designation, SPK-ID, IAU number, or MPC packed-format designation" (e.g. `sstr=J89A00C`); "The search is space sensitive. For example, `sstr='1990MU'` will not match." |
| MPC 80-column optical format | "Temporary designations … preferably no more than six (6) characters … absolute maximum seven (7) … must consist of alphanumeric characters only: do not include spaces" — packed lives in cols 6–12 |
| Wikidata P5736 format constraint | `[A-Z0-9][A-Z0-9/ ()-]{0,11}` (mandatory) — loose directory-key shape, not a designation grammar; examples `2060`, `18374`, `37572`; siblings P717 (observatory code), P716 (JPL SPK-ID) |
| NEOCP live page (examples only) | `P22r91d`, `ZTF10Ge`, `6K61821`, `W000001` — per-survey temp IDs coexist pre-designation; no published regex |
| Rubin PPDB schema | `packed_primary_provisional_designation` / `unpacked_primary_provisional_designation` plain char fields — fields, not validators |
| python-stdnum (negative) | Full module index (~200 formats): no minor-planet/packed/MPC/astronomy module and no coordinate module at all; scope statement ("any number or code that has some validation mechanism") explains the absence — no check digit exists |
| validator.js (negative) | Full validators table (~90): no astronomy validator of any kind; closest `isISIN`/`isISBN`/`isISSN`/`isLatLong` |
| astropy core (qualified negative) | No designation-parsing module (substrate `Time`/`Coordinates`/`Quantity` only) |
| digest2 / mpcorbfile (negative by design) | Consumers of packed columns / 80-col records (`parse_mpc80`), not standalone parsers |

**Normalization contract (2026-10-07 review fix — decode lives in rules/capability, not the grammar):**

```python
# Grammar (syntax only): fold unpacked case/space, preserve spelled packed.
if packed_lane:
    designation = spelled  # preserved byte-for-byte; rules run mpc_unpack coherence
    packed = spelled
else:
    designation = re.sub(r"\s+", " ", raw).strip().upper()  # "1995_XA" -> "1995 XA"
    packed = ""  # no packed claimed; capability renders mpc_pack(designation)
# Rules: mpc_unpack(spelled) coherence + normalize() -> canonical unpacked.
# Capability.format_value(packed): mpc_pack(value) shared with rules.
```

### 2.3 What input is NOT a minor-planet mention

- Comet designations (`C/1995 O1`, `1P/Halley`, `73P-C`, fragments `-B`) — disjoint namespace, DEFERRED grammar, never MISSING-vs-INVALID confusion (see §9).
- Satellite/ring designations (`S/2000 J 11`, `R/…`, `(87) Sylvia I`) — different authority branch, REJECT.
- Bare names (`Eros`, `Chiron`, `Wikipedia`) — not designations; MISSING (names lane deferred, §13 row 11).
- Bare numbers (`433`, `274301`) — JPL search lane only; MISSING without parens (real designation is `(433)`).
- Old-style provisionals (`1892 A`, `1914 VV`, `1915 a`, `SIGMA 27`, Greek letters) — superseded 1925 system; MISSING.
- Phone parenthesized fragments (`(555) 123-4567` — v1 overclaims the `(555)` area code as a number; caller segments phone contexts, future registry disambiguates), M49 numerics, GTIN runs (packed letters disambiguate; bare `\d{5}` overlaps ZIP/price runs — caller routes per §13 row 8).
- Subscript-cycle print (`1995 SA₁`) — non-ASCII tail; MISSING (ASCII-only wire).
- NEOCP temp IDs (`P22r91d`, `ZTF10Ge`) — per-survey internal IDs, not designations; MISSING.

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). MPC equation headings (`(274301) Wikipedia = 1997 RO4 = 2007 FK34`) and multi-designation lines (`1995 XA, 1995 XB`) carry 2+ distinct designations → `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True`; identical packed/unpacked spellings of one designation coalesce to `SUCCESS` (same canonical value, ADR-0011 same-entity encodings).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — canonical unpacked plus packed facet

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MinorPlanetNotation:
    """Minor-planet notation — grammar-normalized designation form.

    ``designation`` is the canonical unpacked reading (uppercased,
    single-spaced: ``1995 XA``; surveys ``2040 P-L``; numbers
    parenthesized ``(433)``; ``A/``-prefixed ``A/2017 U1``).
    ``form`` is the recognized lane (``provisional`` | ``packed`` |
    ``extended`` | ``survey`` | ``survey_packed`` | ``number`` |
    ``packed_number``) — a free str, not a Literal (lanes may grow with
    future packing schemes; the rules, not the type, own lane truth).
    ``packed`` is the spelled packed form, case-EXACT, for packed lanes
    (``J95X00A``; ``a0017`` lowercase preserved) and "" for unpacked/`A/`
    lanes. Rules own decode coherence (`mpc_unpack`); the capability owns
    `mpc_pack` rendering for the offered ``packed`` format, so the grammar
    never consults century/base-62 tables.
    """

    designation: str
    form: str
    packed: str
```

**Considered alternative — single field `designation` only:** a bare canonical string would carry the pipeline, since rules could re-derive the lane. However the decomposition is preferred because (1) the MPC spec indexes authority by lane (unpacked definition vs packed spec vs numbering process are three citable publications), (2) the lane (`form` + case-exact `packed`) decides which rule branch validates without re-parsing, and (3) pack/unpack is a total positional transcoding (like ISBN separator-stripping, writ large) — not validation. This mirrors GTIN's `digits + native_length + has_ai` facet pattern (`paxman/capabilities/GTIN/notation.py:20-22`).

**On the grammar/rule boundary for pack/unpack transcoding (2026-10-07 review fix):** the capabilities governance (`paxman/capabilities/AGENTS.md`) reserves token→canonical mapping to rules, and pack/unpack needs authority tables (century `IJK`, cycle/base-62 values in `PackedDes`). The grammar therefore performs syntax-only normalization (case/space fold, lane dispatch, spelled-form preservation) and never decodes. Validity judgments (letter sets, decode coherence, tilde arithmetic) live in rules; `mpc_pack` rendering lives in the capability's `format_value()`. The notation carries the spelled lane facets; no vocabulary is consulted in the grammar.

**Invariants the grammar enforces (before rules):**

- `designation` is the syntax-normalized spelled form (unpacked lanes uppercased, single-spaced, ASCII; packed lanes preserved byte-for-byte, case-exact).
- `form` is one of the seven lane ids, derived purely syntactically from which alternation branch fired.
- `packed` carries the spelled packed form for packed lanes only; unpacked/`A/` lanes carry `""` (no packed mapping claimed in the grammar; the capability renders `packed` from the validated designation).

### 3.2 Why not carry spaces variants, case, or names in the notation

Separator variants (`_` vs space), input case, and trailing names (`(433) Eros` — name outside the span) have **no lexical significance** for validity — the canonical unpacked form is upper/space-normalized per DesDoc, and presentation of names is out of scope (names lane deferred). Presentation beyond case/space normalization is `Capability.format_value()` only.

### 3.3 Why `form` is not a shape discriminator literal

`form` is a free `str` naming the fired branch, lane-checked by rules (a claimed `packed` notation must decode coherently; a claimed `survey` must carry a valid survey identifier) — mirroring UNSPSC's free-`str` `level` (the evolving spec, not the type, is the versioned truth; here the extended `_` scheme of 2023 proves packing lanes still grow). A `Literal[...]` would freeze the seven lanes into the type while MPC adds schemes on LSST timescales.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex vs Lexicon

Per HOW_TO_ADD_NEW_GRAMMAR.md, minor-planet designations have distinctive fixed-width structural shapes (year+letters, 7-char packed, survey codes, parenthesized numbers), so **Regex** is correct. Lexicon is wrong: provisionals are an open-ended stream (tens of thousands per half-month in the LSST era), not a finite hand-keyed token table, and recognition must fire before (and without) consulting any registry.

### 4.2 Reference pattern (adapted from ISBN and ISSN verbatim precedent)

ISBN-13 precedent (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py:30-40`): staged `PipelineGrammar` + `StandardPre(empty_guard=True)` + `RegexStage` with module-scope pattern, fused label, digit-continuation lookarounds, `single_value=True`. ISSN precedent (`paxman/capabilities/ISSN/grammar/issn_recognition.py:41-60`): one grammar covering hyphenated-vs-compact via optional separator at the canonical position, `LabelMatcher` with `glued_policy`, `BoundarySpec.WORD`, `re.IGNORECASE | re.ASCII`.

**Proposed minor-planet pattern (single grammar, staged pipeline):**

```python
import re
from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.core.grammar import PipelineGrammar, RegexStage, StandardPre

# No re.IGNORECASE: unpacked lanes fold case explicitly ([A-Za-z] +
# .upper()), packed lanes are case-SIGNIFICANT (a0017 vs A0345).
# Single `year` group: the `A/` prefix is an optional `aprefix` group on the
# same branch (2026-10-07 review fix — separate `_APREFIX + _UNPACKED`
# alternation redefined `year`/`hm`/`second`/`cycle` and `re.compile`
# raised `redefinition of group name 'year'`).
_YEAR = r"(?:A[89]\d{2}|19\d{2}|20\d{2})"
_UNPACKED = (
    r"(?P<year>" + _YEAR + r")[ _]"
    r"(?P<hm>[A-Za-z])(?P<second>[A-Za-z])(?P<cycle>\d*)"
)
# `A/` lane allows 1-2 letters per ADES `[ADCPX]/\d{4} [A-Z]{1,2}\d*`
# (e.g. `A/2017 U1` has a single letter + cycle). Distinct group names —
# reusing `year`/`hm` here reintroduced the duplicate-group compile error.
_APREFIX = (
    r"A/(?P<ayear>" + _YEAR + r")[ _]"
    r"(?P<ahm>[A-Za-z])(?P<asecond>[A-Za-z])?(?P<acycle>\d*)"
)
_SURVEY = r"(?P<surveynum>[1-9]\d{0,3})[ _](?P<survey>[Pp]-[Ll]|[Tt]-[123])"
_PACKED7 = r"(?P<packed7>[IJK]\d{2}[A-Z][0-9A-Za-z]\d[A-Z])"
_EXTENDED = r"(?P<extended>_[A-Z][A-Z][0-9A-Za-z]{4})"
_SURVEYPACKED = r"(?P<surveypacked>(?:PLS|T[123]S)\d{3,4})"
_PACKEDNUM = r"(?P<packednum>(?:\d{5}(?![ _][A-Za-z])|[A-Za-z]\d{4}|~[0-9A-Za-z]{4}))"
# 8-digit headroom: tilde decodes to 15396335 (2026-10-07 review fix —
# `\d{1,7}` capped below the `~zzzz` max).
_NUMBER = r"\((?P<number>\d{1,8})\)"
_MP_BODY = (
    _APREFIX + r"|" + _UNPACKED + r"|" + _SURVEY + r"|"
    + _PACKED7 + r"|" + _EXTENDED + r"|" + _SURVEYPACKED + r"|"
    + _PACKEDNUM + r"|" + _NUMBER
)
_MP_PATTERN = r"(?<!\w)(?:" + _MP_BODY + r")(?!\w)(?![-]\d)"


def _notation(match: re.Match[str]) -> MinorPlanetNotation:
    (...)  # lane dispatch on named groups; unpack folds upper/single-space
    # and preserves the spelled lane. Pack/unpack decode lives in RULES and
    # the capability (2026-10-07 review fix per
    # paxman/capabilities/AGENTS.md governance): the grammar performs
    # syntax-only normalization and never consults century/base-62 tables.
    # `packed` facet carries the spelled packed form for packed lanes and
    # "" for unpacked/`A/` lanes; rules own `mpc_unpack` coherence and the
    # capability owns `mpc_pack` rendering for the offered `packed` format.


class MinorPlanetRecognitionGrammar(PipelineGrammar[MinorPlanetNotation]):
    """Minor-planet recognition: unpacked/packed/survey/number lanes.

    New-code preference is the kernel `RegexMatcher` + `BoundarySpec.WORD`
    spelling of this pattern; legacy `PipelineGrammar` + `RegexStage` below
    remains accepted (BIC/UNSPSC precedent). Either way compile ASCII-only
    without `re.IGNORECASE`.
    """

    name = "minor_planet_recognition"
    semantics = "minor_planet_recognition"
    single_value = True
    pre = StandardPre[MinorPlanetNotation](empty_guard=True)
    regex = RegexStage[MinorPlanetNotation](
        pattern=_MP_PATTERN, notation_fn=_notation, flags=re.ASCII
    )
```

*Notes on fidelity vs ISBN/ISSN:* module-scope strings compiled by `RegexStage` (or kernel `RegexMatcher`); longest-alternation discipline (packed-7 before packed-number before bare runs, so `J95X00A` never carves); ASCII-only via `re.ASCII` **without** `re.IGNORECASE` (packed case significance — the one flag decision, enforced by construction); `(?<!\w)/(?!\w)` word guards both ends (kernel `BoundarySpec.WORD` spelling preferred for new code); `(?![-]\d)` trailing guard mirrors ISBN-13/UNSPSC (no hyphen-joined suffix carving); `StandardPre(empty_guard=True)` rejects empty slices. Known overclaims at v1 (2026-10-07 review fix): `(NNN)` matches phone area codes such as `(555)` in `(555) 123-4567`, and bare `\d{5}` matches ZIP/price runs — word guards do not disambiguate these lanes; §4.4 and §13 row 8 record the caller-routes + future-registry mitigation, not guard safety. **Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a pattern element — unpacked + underscore to `_UNPACKED`, `A/`-prefix (1-2 letters) to `_APREFIX` with distinct `a*` groups, packed/extended/survey-packed/packed-number to their branches, surveys to `_SURVEY`, numbers to `_NUMBER` (parens load-bearing, 8-digit headroom for the tilde max); the DEFER row (comets) names `comet_recognition` as its future mechanism with a distinct semantics id (disjoint namespace, never coalesced); the REJECT rows (glued/bare-number/old-style/satellites/names/subscripts) are excluded by construction (separator class, parens requirement, year-lane bounds, ASCII).

**One grammar vs N:** (Recommended) Single `minor_planet_recognition` with lane alternation — packed and unpacked are same-entity encodings (one dedup key via identical `normalize()`), so splitting would create cross-grammar containment with zero semantic difference. Alternative (rejected): per-lane grammars (`minor_planet_provisional` + `minor_planet_packed` + …) with coalesced semantics — heavier surface, same candidates.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)

- Grammar emits span-bearing `RecognitionMatch`, half-open `[start, end)`, `raw_text == text[start:end]` (`paxman/core/domain.py:78-86`).
- `RegexStage` loops `re.finditer`, builds `RecognitionMatch`; stages must not mutate text.
- Engine owns within-grammar containment dedup, longer-wins, same grammar only (`paxman/engine/orchestrator.py:463-492`), and total recognition ordering `(start, end, active-set index, grammar name)` (`orchestrator.py:431-442`).
- Candidate dedup `(value, recognition_rule, validation_rule)` after validation (`orchestrator.py:843-847`): packed and unpacked spellings of one designation share the canonical value and coalesce under `single_value`.

### 4.4 Guard boundaries against sibling grammars (2026-10-07 review fix: overclaim lanes marked)

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| MinorPlanet (this) | year+letters / 7-char packed / survey codes / `(N+)` / bare `\d{5}` | `(?<!\w)` (`BoundarySpec.WORD` preferred) | `(?!\w)` + `(?![-]\d)`; packed lowercase significant |
| Phone national | `(NNN)` 3-digit + 3-3-4 groups | phone-specific lookbehinds | group continuation; **overlaps `(NNN)` — v1 overclaims `(555)`-shaped area codes as numbers; caller segments phone contexts, future registry disambiguates** |
| Date ISO | 4-digit year + month/day required | separator lane | separator lane; `1995 XA` has letters, unclaimable |
| GTIN runs | pure digits, exact 8/12/13/14 | word guards | `(?!\w)`; packed letters/parens disambiguate, **bare `\d{5}` overlaps ZIP/price runs — caller routes, registry revisits** |
| CreditCard | 12–19 digits, Luhn | word guards | word guards; packed-7/5 lengths disjoint |
| Country numeric (M49) | 1–3 digits | word guards | word guards; year+letters disjoint in practice |
| Coordinates | decimal/sexagesimal + hemispheres | sign/letter lane | unit lane; no designation overlap |

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

- `semantics = "minor_planet_recognition"` identity id; the deferred comet grammar takes a distinct id (`comet_recognition`) because comet/minor-planet namespaces are disjoint — never coalesced.
- No second shipped grammar at v1; `target_semantics` on all five rules claims exactly the minor-planet id.

### 4.6 `single_value` — one mention per call vs batch processing

Recommendation: `single_value=True` at v1 (shipped precedent: ISBN, ISSN, GTIN, UNSPSC all set it). MPC equation headings and multi-designation lines use the caller-owned segmentation path (split then canonicalize each slice).

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | International Astronomical Union (IAU) via its Minor Planet Center |
| Registration Authority | Minor Planet Center (MPC) — hosted by the Center for Astrophysics \| Harvard & Smithsonian, funded by NASA; "single worldwide location" for minor planets, comets, and outer irregular satellites |
| Spec name | Minor-planet designation system (unpacked provisional definition; packed provisional/permanent spec; numbering/naming process) — NOT an ISO standard; no `iso.org/standard/` entry exists |
| Current edition | New-style provisional system in force since 1925; packed forms per undated living spec; extended `_` packing announced Oct 2023 (LSST era) |
| Check character system | NONE — positional encoding only; exhaustive column specs (PackedDes all 7+5 positions; 80-column format all 80 columns) define no check field |
| Vocabulary reference | Half-month `[A-HJ-Y]` (I omitted, Z unused); second letter `[A-HJ-Z]` (I omitted); century `IJK` = 18/19/20; base-62 `0-9A-Za-z` (A=10…Z=35/a=36…z=61) |
| Related specs | IAU cometary designation system (sibling, deferred); ADES astrometry schema (corroborating XSD facets, not a rule publication); JPL SBDB/Horizons accepted-input docs (resolution behavior, not grammar) |

**Structure (DesDoc, verbatim):** "a 4-digit number indicating the year; a space; a letter to show the half-month; another letter to show the order within the half-month; and an optional number to indicate the number of times the second letter has been repeated in that half-month period." Half-month table A=Jan 1–15 … Y=Dec 16–31 with "**I is omitted and Z is unused**"; second-letter order A=1st … Z=25th with "**I is omitted**"; cycle scheme "`1995 SA, 1995 SB, ..., 1995 SY, 1995 SZ, 1995 SA1, …, 1995 SZ1, 1995 SA2, …`"; "When possible, these additional numbers should be indicated using subscript characters." Surveys: "a number (identifing the order within that survey), a space and a survey identifier" — `2040 P-L, 3138 T-1, 1010 T-2 and 4101 T-3`. Space significance: "a space between the year and the letter in order to distinguish this designation from the old-style comet designation 1915a". Retrospective: "replacement of the initial digit of the year by the letter `A'" (`A904 OA`).

**Packed structure (PackedDes, verbatim):** "The first two digits of the year are packed into a single character in column 1 (I = 18, J = 19, K = 20). Columns 2-3 contain the last two digits of the year. Column 4 contains the half-month letter and column 7 contains the second letter. The cycle count … is coded in columns 5-6, using a letter in column 5 when the cycle count is larger than 99. The uppercase letters are used, followed by the lowercase letters." Survey packs: "Columns 1-3 contain the code indicating the survey and columns 4-7 contain the number" (`2040 P-L = PLS2040`). Permanent: "If the minor-planet number is less than 100000, then the number is stored as a zero-padded right-justified string. E.g., (3202) is stored as `03202`" … "When the number is above 99999, the number MOD 10000 is stored in columns 2-5 … and the number DIV 10000 is represented by the letters A-Z (if between 10 and 35, inclusive) or a-z (if between 36 and 61, inclusive)" … tilde scheme: "The subsequent 4 characters will all be base-62 (0-9, then A-Z if between 10 and 35 inclusive, then a-z if between 36 and 61 inclusive) and used to store the target number MINUS 620,000" (`~000z` = 620061; `~AZaz` = 3140113; `~zzzz` = 15396335 — arithmetic verified).

**Numbering/naming (HowNamed, verbatim):** "Names and citations proposed by discoverers are judged by the Working Group Small Bodies Nomenclature (WGSBN)… Names become official when they appear in the WGSBN Bulletin"; discoverers hold "the privilege of proposing a name for ten years after an object is numbered" (WGSBN rules, snippet-sourced, corroborated by HowNamed).

**Lineage table:**

| Release | Date | Status | Note |
|---------|------|--------|------|
| AN single-letter provisionals | 1892 | Superseded | Year + single letter (`1892 A`, I omitted); Berliner Jahrbuch numbers for computed orbits (DesDoc, primary) |
| Double-letter provisionals | 1893 → 1916 (`ZZ`, restart `AA`) | Superseded | Continuous across years (`1894 AQ` after `1893 AP`); wartime Simëis/SIGMA/Greek-letter improvisations 1914–1918 (DesDoc, primary) |
| Current year+half-month system | 1925 → present | Active | Half-month + second letter + cycle scheme; pre-1925 retrospective `A`-prefix (DesDoc, primary) |
| Palomar-Leiden/Trojan surveys | 1960 → 1977 | Active (closed sets) | `P-L`, `T-1`, `T-2`, `T-3` designations (DesDoc, primary) |
| Comet year/Roman-numeral reform | Agreed 1994-08 (IAU Hague), effective 1995-01 | Active (sibling) | Comets adopt minor-planet-like `1995 D3` + `P/C/X/D` (+ later `A/I`) prefixes (MPC cometary-designation ops doc) |
| Extended `_` packed scheme | Announced Oct 2023 | Active | Base-62 tail for >15,500/half-month LSST volumes; not for pre-2010 discoveries (MPC ops docs) |

**Citation Details Table (for Provenance):**

| Authority | Spec name | Version | Reference URL | Lifecycle | Publication year | Kind |
|-----------|-----------|---------|---------------|-----------|------------------|------|
| Minor Planet Center | Unpacked provisional designation definition (DesDoc) | Living document, four-level letter tables + cycle/survey rules, fetched 2026-10-07 | https://minorplanetcenter.net/iau/info/DesDoc.html | active | 2026 | specification |
| Minor Planet Center | Packed provisional/permanent spec (PackedDes) | Living document, 7-/5-char layouts + tilde base-62, fetched 2026-10-07 | https://minorplanetcenter.net/iau/info/PackedDes.html | active | 2026 | specification |
| Minor Planet Center | Numbering/naming process (HowNamed) | Living document, WGSBN Bulletin officiality, fetched 2026-10-07 | https://minorplanetcenter.net/iau/info/HowNamed.html | active | 2026 | specification |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|---------------|-------------------|
| `rules/mpc_unpacked_designation.py` | authority="Minor Planet Center", specification_name="Unpacked provisional designation definition", kind="specification", reference_url="https://minorplanetcenter.net/iau/info/DesDoc.html", version="living document (fetched 2026-10-07)", lifecycle="active", publication_year=2026 | Section 1-unpacked-provisional-structure, Section 2-survey-designation | Year lane + separator + half-month/second letter sets + cycle digits; survey number + identifier (PARSER) |
| `rules/mpc_packed_designation.py` | authority="Minor Planet Center", specification_name="Packed provisional/permanent spec", kind="specification", reference_url="https://minorplanetcenter.net/iau/info/PackedDes.html", version="living document (fetched 2026-10-07)", lifecycle="active", publication_year=2026 | Section 3-packed-provisional, Section 4-packed-number | 7-char decode coherence (century/cycle/second, incl. extended `_` shape) + 5-char number decode coherence incl. tilde arithmetic (PARSER) |
| `rules/mpc_numbering.py` | authority="Minor Planet Center", specification_name="Numbering/naming process", kind="specification", reference_url="https://minorplanetcenter.net/iau/info/HowNamed.html", version="living document (fetched 2026-10-07)", lifecycle="active", publication_year=2026 | Section 5-permanent-number | Parenthesized positive integer, no leading zeros (PARSER) |

Each `Rule[MinorPlanetNotation]` subclass declares six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`, `paxman/core/domain.py:253-278`):

```python
name: str  # "Section {N}-{slug}"
strategy: RuleStrategy  # PARSER (all five at v1; see §5.4)
provenance: Provenance  # == module PUBLICATION
citation: str  # spec section anchor
target_semantics: frozenset[str]  # {"minor_planet_recognition"}
requires_features: frozenset[str]  # frozenset() at v1 (no gated registry)
```

### 5.3 What each rule does vs does not own

- `matches()` validates strictly, never raises, never reads contract `include_*` flags directly (no capability-specific flags ship at v1 — the `include_live_membership` placebo lesson from UNSPSC review applies: no flag without a consuming rule). `normalize()` returns the canonical unpacked `designation`, never reads `output_format` (CI purity scan enforced), identical across rules for candidate dedup.
- `RuleStrategy` choice: PARSER for all five (letter-set membership and positional decode coherence need no authority table). Packed decode is validation of *coherence* (century ∈ IJK, half-month ∈ set, cycle letter×10+digit arithmetic, tilde value ≥ 0), not registry lookup.
- Lane truth lives in the rules, keyed off `notation.form`: Section 1 matches `provisional` only (so packed inputs carry no DesDoc provenance); Section 3 matches `packed`/`extended`/`survey_packed`; Section 5 matches `number`. Full-conjunction-per-rule discipline follows the GTIN Section-2 precedent (`gs1_prefix_ed2026.py:96-109` re-checks length/ASCII/check-digit before prefix lookup) and ISNI's documented rationale — a partial validator would let off-lane garbage resolve SUCCESS under pinned contracts.

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Whether to ship a registry (issued-designation) LOOKUP_TABLE at v1. Recommendation: **PARSER-only v1, no registry** — like UUID/BIC structure-only posture, not like ISBN's range-message table. Rationale: (1) there is no small authority table to vendor — MPCORB holds hundreds of thousands of designations on a monthly cadence, and provisional designations are a high-churn stream (tens of thousands per half-month in the LSST era); a snapshot would be stale on arrival and enormous beside the 158k-row UNSPSC precedent. (2) Staleness semantics would be actively misleading: an unissued-but-well-formed `2026 ZZ99` resolving SUCCESS-today/INVALID-tomorrow is worse than honest well-formed-only SUCCESS. (3) The ADR-0012 vacuity exception covers PARSER-without-LOOKUP exactly as it does ISSN's check-digit rule. Cost of deferral: `2026 ZZ99`-shaped never-assigned inputs resolve SUCCESS (well-formed) instead of INVALID — disclosed in §8/§9, and the named upgrade is an MPCORB-snapshot `Section 6-mpcorb-membership` LOOKUP_TABLE behind a default-off `include_mpcorb_membership` flag (never ship the flag first — placebo-flag lesson recorded).

### 5.5 Assignment / registration authority & registry content

Owner/RA: Minor Planet Center — "single worldwide location" for minor planets, comets, and outer irregular natural satellites (mpc.html); hosted by the Center for Astrophysics | Harvard & Smithsonian, funded by NASA (site footer). Assigning flow: provisional designation on ≥2 nights of unidentified observations → permanent number once the orbit is secure/recoverable → optional name by discoverer proposal judged by WGSBN, official only on WGSBN Bulletin publication (10-year proposal privilege). Record content per designation: packed + unpacked forms, orbit, observations (80-column / ADES), discovery asterisk. Cadence: nightly MPECs; monthly MPCORB snapshots; Bulletins as needed. Search: `https://www.minorplanetcenter.net/db_search` (+ machine `designation-identifier` API returning `packed_*`/`unpacked_*` pairs). Related: JPL SBDB/Horizons (resolution mirrors, not authorities), WGSBN (names), IAU Division F (dynamical context, not cited).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract MUST inherit `CapabilityContract` (never `Contract` directly). `@dataclass(frozen=True)` without slots.

```python
from dataclasses import dataclass, field
from typing import ClassVar
from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class MinorPlanetContract(CapabilityContract):
    """User-facing configuration for the MinorPlanet capability.

    Formats (ADR-0011 classes): ``designation`` is the unpacked canonical
    (``1995 XA`` / ``(433)`` / ``2040 P-L``, default); ``packed`` is the
    same-entity wire encoding — encoding (``J95X00A`` / ``03202`` /
    ``PLS2040``, case-exact, re-enters through the packed branch).
    Unpacked/`A/` lanes have no spelled packed form; the capability renders
    `packed` from the validated designation, falling back to the
    designation only for the `A/` lane which defines no packed mapping.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "designation"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"packed"})

    capability_name: str = field(default="minor_planet", init=False)

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> MinorPlanetContract:
        """Create a MinorPlanet contract (shipped common block at v1)."""
        ...
```

- `DEFAULT_OUTPUT_FORMAT` concrete string `"designation"`, `OFFERED_OUTPUT_FORMATS` excludes default, resolved via `resolve_output_format`; `create_contract()` uses the shipped keyword-only common block (`Sequence[str] | None`, plus `extra_grammars` and `suppress_common_words` per `paxman/capabilities/ISSN/capability.py:47-56`).
- No capability-specific flags at v1 (placebo-flag lesson). `year` temporal filtering applies naturally (living-doc publications carry `publication_year=2026`; a future dated revision would make `year` meaningful — document, don't gate).
- Presentational-only invariant: rules never see `output_format`; `normalize()` always returns the unpacked `designation`.
- For MinorPlanet, offered formats model the interchange forms:

| output_format | Value example | Meaning |
|---------------|---------------|---------|
| `designation` (default) | `1995 XA` | Unpacked canonical (upper, single space, parens for numbers) |
| `packed` | `J95X00A` | Same-entity wire encoding (case-exact; re-enters) |

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from collections.abc import Sequence

from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.MinorPlanet.contract import MinorPlanetContract
from paxman.capabilities.MinorPlanet.grammar.minor_planet_recognition import (
    MinorPlanetRecognitionGrammar,
)
from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.capabilities.MinorPlanet.rules.mpc_numbering import (
    Section5PermanentNumber,
)
from paxman.capabilities.MinorPlanet.rules.mpc_packed_designation import (
    Section3PackedProvisional,
    Section4PackedNumber,
)
from paxman.capabilities.MinorPlanet.rules.mpc_unpacked_designation import (
    Section1UnpackedProvisionalStructure,
    Section2SurveyDesignation,
)


class MinorPlanetCapability(Capability[MinorPlanetNotation]):
    """Minor-planet capability — wiring + presentation seam."""

    name = "minor_planet"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[MinorPlanetNotation]]:
        """Return the shipped recognizers."""
        return [MinorPlanetRecognitionGrammar()]

    def get_rules(self) -> list[Rule[MinorPlanetNotation]]:
        """Return the shipped validators."""
        return [
            Section1UnpackedProvisionalStructure(),
            Section2SurveyDesignation(),
            Section3PackedProvisional(),
            Section4PackedNumber(),
            Section5PermanentNumber(),
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
    ) -> MinorPlanetContract:
        """Create the default MinorPlanet contract (shipped common block)."""
        ...

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: MinorPlanetNotation,
    ) -> str:
        """Render the canonical designation in the requested format.

        The default ``"designation"`` path is the identity. ``"packed"``
        renders via the shared `mpc_pack` helper owned by rules/capability
        (never recomputed from grammar tables); the `A/` lane has no packed
        mapping and falls back to the designation. Never affects candidate
        identity or provenance.
        """
        if output_format == "packed":
            return notation.packed or mpc_pack(value) or value
        return value
```

Registration via `tools/new_capability.py` (see §10.1).

---

## 7. Validation — three levels

### 7.1 Level 1 Unpacked structure, Level 2 Packed decode coherence, Level 3 Permanent-number shape

**Level 1 — unpacked structure (`Section1UnpackedProvisionalStructure`, PARSER, always-active).** Year lane `A[89]\d{2}|19\d{2}|20\d{2}`, single space-or-underscore separator, half-month ∈ `[A-HJ-Y]`, second ∈ `[A-HJ-Z]`, cycle `\d*` (lenient on leading zeros — sbpy `[0-9]{0,3}` and ADES `\d*` agree; strictness would invent rejections both validators decline). `A/`-prefixed lane same tail. Worked examples: `1995 XA` ✓; `2007 TA418` ✓ (cycle 418); `A904 OA` ✓ (retrospective lane); `A/2017 U1` ✓; `1995 XI` ✗ (I excluded from half-month); `1995 IZ` ✗ (I excluded everywhere); `1995 XZ` ✓ (Z is a legal *second* letter — the asymmetric exclusion is the classic trap); `1892 A` ✗ never reaches rules (single-letter old-style; grammar needs two letters).

**Level 2 — packed decode coherence (`Section3PackedProvisional` + `Section4PackedNumber`, PARSER, always-active).** Provisional: century ∈ `{I,J,K}`; half-month ∈ `[A-HJ-Y]`; cycle = two digits (00–99) or letter×10+digit with letter value A=10…Z=35/a=36…z=61 (so `J=19` → `J3`=193, `f=41` → `f8`=418); second ∈ `[A-Z]` (col 7 uppercase — lowercase col-7 is the comet-fragment lane, deferred); extended `_` = year-letter + half-month + 4×base-62 (shape-validated; exact year-letter mapping verified against sbpy/MPC examples at implementation). Number: `\d{5}` any (zero-padded lane); `[A-Za-z]\d{4}` with case preserved (`A0345`→100345 vs `a0017`→360017 — the report's canonical case-trap pair); `~` + 4×base-62 with value = decode − 620000 ≥ 0 (`~000z`→620061; `~AZaz`→3140113; `~zzzz`→15396335 — arithmetic verified against PackedDes). Worked: `J95X00A`→`1995 XA` ✓; `K07Tf8A`→`2007 TA418` ✓; `K99AJ3Z`→`2099 AZ193` ✓; `03202`→`(3202)` ✓; `~0000`→`(620000)` ✓; `Q95X00A` ✗ (Q not a century); `J95I00A` ✗ (I half-month).

**Level 3 — permanent-number shape (`Section5PermanentNumber`, PARSER, always-active).** Paren contents match `^[1-9]\d{0,7}$` (positive integer, no leading zeros, 8-digit headroom covering the tilde max 15396335). Worked: `(433)` ✓; `(274301)` ✓; `(15396335)` ✓ (tilde-max shape); `(0433)` ✗ (leading zero — MPC never pads unpacked numbers); `(0)` ✗. Names are not validated (lane deferred — `(433) Eros` validates on `(433)`; `Eros` alone never reaches rules).

### 7.2 What makes a designation "valid" vs "issued"

- **Valid (well-formed)** — correct lane shape, ASCII, letter-set/decode coherent; always-active PARSERs. This is the v1 verdict ceiling.
- **Issued (actually assigned by MPC)** — valid plus present in MPC records; unknowable at v1 without a registry. A well-formed never-assigned `2026 ZZ99` resolves SUCCESS (well-formed), not INVALID — disclosed honestly, not silently overclaimed. Analogous to UUID (structure-only) and to BIC before its directory rule; the recorded upgrade is an MPCORB-snapshot LOOKUP_TABLE (§13 row 9).
- **Named** — orthogonal to validity; names are never validated at v1 (WGSBN officiality is a publication event, not a string property).

Like ISBN valid vs allocated, ISSN valid vs issued — except the issued half is explicitly unshipped.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase unpacked | `2003 cp20` → SUCCESS `2003 CP20` | Unpacked lane folds upper; spaced lowercase attested (glued `2003cp20` → MISSING) |
| 2 | Underscore separator | `1995_XA` → SUCCESS `1995 XA` | `[ _]` class; sbpy + astroquery agree |
| 3 | Packed case preserved | `a0017` → SUCCESS `(360017)`; `A0345` → SUCCESS `(100345)` | Case-sensitive lane; folding would merge distinct values |
| 4 | Extended packed | `_QC0000` → SUCCESS (unpacked extended reading) | Normative LSST-era scheme; shape + base-62 validated |
| 5 | Survey both spellings | `2040 P-L` / `PLS2040` → SUCCESS same canonical | Same entity, two encodings (ADR-0011) |
| 6 | A-prefix retrospective | `A904 OA` → SUCCESS | ADES `OldProvIDType` agrees |
| 7 | `A/`-prefixed | `A/2017 U1` → SUCCESS `A/2017 U1` | MPC identifier-API input contract; packed facet "" |
| 8 | Trailing-name citation | `(433) Eros` → SUCCESS `(433)` (name outside span) | Number span only; mirrors trailing-annotation handling |
| 9 | Over-long year/pack | `19955 XA` / `J95X00` → MISSING | Year-lane / 7-char length guards |
| 10 | Invalid letter slots | `1995 XI` → INVALID | Claimed by grammar (broad letters), rejected by Section 1 |
| 11 | Leading-zero number | `(0433)` → INVALID | Rule rejects; MPC never pads unpacked numbers |
| 12 | Glued `1995XA` | MISSING | No separator; sbpy + ADES require one |
| 13 | Bare number `433` | MISSING | Parens load-bearing (JPL lane deferred) |
| 14 | Old-style `1892 A` | MISSING | Superseded system; two-letter minimum |
| 15 | Comet `C/1995 O1` / fragment | MISSING (at v1) | Disjoint namespace; deferred grammar |
| 16 | Embedded in sentence | `see 1995 XA (Alcathoe)` → SUCCESS with span | Word guards; parenthetical not swallowed |
| 17 | Two distinct in one slice | `1997 RO4 = 2007 FK34` → AMBIGUOUS / MultipleMentionsError | Same body, distinct designations — authorial choice, segmentation |
| 18 | Packed+unpacked same object | `J95X00A = 1995 XA` → SUCCESS `1995 XA` | Identical canonical via both lanes; candidates dedup |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid unpacked/packed/survey/number at v1 rules | SUCCESS → unpacked canonical | Lane shape + letter/decode coherence all pass |
| Valid lowercase/underscore/`A/`/trailing-name variants | SUCCESS (same canonical) | Presentation/spelling-only dedup; packed facet case-exact |
| Invalid letter slot / bad half-month / leading-zero number / mid-shape violation | INVALID | Claimed by grammar (broad letter classes), rejected by lane rule; bad-century packs (`Q95X00A`) are MISSING (century is lane-defining in the grammar) |
| Glued / bare-number / old-style / names / subscripts / satellites | MISSING | No grammar claims these shapes at v1 |
| Comet/interstellar (`C/`, `P/`, `I/`, fragments) | MISSING | Deferred namespace; no grammar claims |
| No designation-shaped runs | MISSING | No grammar recognized |
| Two distinct designations in one slice | AMBIGUOUS / MultipleMentionsError | Single-slice ambiguity, use segmentation |
| Well-formed but never assigned (`2026 ZZ99`-shape) | SUCCESS (well-formed) | No registry at v1 — honest collapse, disclosed in §7.2 |
| Packed and unpacked spellings of one designation | SUCCESS (one value) | Same-entity encodings; dedup coalesces |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py MinorPlanet --name minor_planet --authority "Minor Planet Center" --spec-name "Unpacked provisional designation definition" --spec-url "https://minorplanetcenter.net/iau/info/DesDoc.html" --publication-year 2026 --spec-version "living document (fetched 2026-10-07)" --default-format designation
```

Creates 13 files + one edit: `paxman/capabilities/MinorPlanet/{notation,contract,capability,grammar/*,rules/*}`, tests stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance. After scaffolding, add the packed-spec file (`rules/mpc_packed_designation.py`) and the numbering file (`rules/mpc_numbering.py`) manually, splitting the placeholder rule, and delete or repurpose the placeholder — no `rules/data/` at v1 (no registry).

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[MinorPlanetRecognitionGrammar()]`; `active_grammars` omitted at v1 (base `None` runs every shipped grammar).
- Grammar carries `name = "minor_planet_recognition"` and non-empty `semantics = "minor_planet_recognition"`; every rule's `target_semantics = frozenset({"minor_planet_recognition"})`.
- No capability-specific contract flags at v1 (placebo-flag lesson: `include_mpcorb_membership` arrives only with its LOOKUP_TABLE).

### 10.3 Cross-cutting invariants (fail review if violated)

- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports (import only from `paxman.core`, import-linter enforced).
- No `output_format` token in any `paxman/capabilities/*/rules/` module (source-scan) — `packed` lives in `capability.py:format_value()` only.
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contracts.
- Deterministic by construction: same input + contract + library snapshot → same output (no registry at v1, so snapshot = code + packed tables, both static).

---

## 11. Recommended File Layout (mirrors ISSN and ISBN)

```
paxman/capabilities/MinorPlanet/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── minor_planet_recognition.py
└── rules/
    ├── __init__.py
    ├── mpc_unpacked_designation.py
    ├── mpc_packed_designation.py
    └── mpc_numbering.py
```

No `rules/data/` at v1 (no registry — differs from ISBN deliberately; like ISNI's v1 which shipped no lookup tables). A future `rules/data/mpcorb_snapshot.py` + `tools/regenerate_mpcorb_data.py` + `paxman/shared_data/mpcorb_snapshot.json` pair follows the Currency/UNSPSC snapshot+regenerate lifecycle when the LOOKUP_TABLE upgrade lands (§13 row 9).

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- Grammar tests: pattern compiles (no duplicate group names — regression for the 2026-10-07 `redefinition of group name 'year'` failure); unpacked canonical + high-cycle, lowercase fold, underscore lane, A-prefix retrospective, `A/`-prefix via optional `aprefix` group, packed 7-char (+ lowercase-trap pair `a0017`/`A0345`), extended `_`, survey both spellings, parens number incl. 8-digit tilde-max shape, packed-number lanes (digit/letter/tilde), trailing-name span, MPC-equation multi-match, quoted/bracketed, glued/bare-number/old-style/comet/satellite/name/subscript negatives, 3-/5-digit-year and 6-char-pack negatives, X-glued runs, span invariants (`raw_text` includes parens/label-equivalents, `notation.designation` excludes case/space variance), name/semantics, boundary-guard negatives — plus one positive vector per §2.1 RECOGNIZE form. Document `(555)`-in-phone and bare-`\d{5}`-as-ZIP as known v1 overclaims, not guard negatives.
- Rule tests: Section-1 valid/variant/invalid (year lanes, `XI`/`IZ` invalid, `XZ` valid, cycle leniency), Section-2 survey valid + bad-identifier invalid, Section-3 packed valid + bad-century/invalid-half-month + extended shape + tilde arithmetic vectors (`~000z`→620061, `~AZaz`→3140113), Section-4 packed-number valid + case-trap pair, Section-5 number valid + leading-zero/zero invalid; `normalize()` exact unpacked canonical everywhere; provenance attributes (`authority`, `kind`, `version`, `lifecycle`, `publication_year`); name/strategy conventions (`Section N-*`, all PARSER); `target_semantics == frozenset({"minor_planet_recognition"})`.
- Capability tests: notation frozen/hashable/slots, wiring counts (1 grammar, 5 rules), grammar/rule name conventions, `format_value` round-trips (`designation` identity, `packed` case-exact incl. lowercase lanes, `A/`-lane packed identity), `create_contract` factories.
- Integration: MISSING (glued/bare/old-style/comet/name/subscript), INVALID (bad letter slots, bad century, leading-zero number), SUCCESS (all lanes incl. packed+unpacked same-value dedup), AMBIGUOUS or MultipleMentionsError (equation headings, two distinct), `_clean_registry` fixture, determinism/`VersionStamp`, span-bearing match, dedup.
- Property tests (hypothesis): valid lane-directed generation (year from lane + letters from legal sets + cycle digits → must canonicalize to itself); packed round-trip (`mpc_pack`∘`mpc_unpack` identity on legal lanes); random alphanum strings → INVALID-or-MISSING, never raise; case-fold stability (lower(input) ≡ input post-`normalize()`); `format_value` round-trip (`packed` → re-parse → same canonical); tilde arithmetic spot-checks.
- Consistency test: every `target_semantics` claimed by a rule is produced by the shipped grammar; pack/unpack helpers agree on the §7 worked vectors.
- Presentation purity: `output_format` source scan over `rules/`.
- Real vectors: `1995 XA`, `2007 TA418`, `1992 QB1`, `2003 CP20` (lowercase input), `A904 OA`, `A/2017 U1`, `J95X00A`, `K07Tf8A`, `K99AJ3Z`, `_QC0000`, `2040 P-L` / `PLS2040`, `3138 T-1` / `T1S3138`, `(433)`, `(274301)`, `(433) Eros` (number span), `03202`, `A0345`, `a0017`, `K3289`, `~000z`, `~AZaz`, `1995 XI` (INVALID), `(0433)` (INVALID), `1995XA` (MISSING), `433` (MISSING), `C/1995 O1` (MISSING at v1).

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `designation` vs `packed` vs `bare` | Default `designation` (unpacked canonical); offer `packed` | Human-readable citable form first (MPC display practice); packed is the wire encoding, presentationally secondary (ADR-0011) |
| 2 | Single grammar vs N grammars | Single `minor_planet_recognition` with lane alternation | Same-entity encodings share one dedup key; avoids cross-grammar containment spurious AMBIGUOUS |
| 3 | Bare names (`Eros`) | REJECT at v1 (MISSING) | Names are not designations (MPC always number-pairs them); vocabulary unbounded without a names snapshot |
| 4 | Comets as second grammar | DEFER to `comet_recognition` with distinct semantics id | Disjoint namespace (C/P/D/X + periodic numbers + fragments); coalescing would merge distinct authorities |
| 5 | Glued `1995XA` | REJECT (MISSING) | sbpy + ADES both require the separator; JPL liberality is resolution, not grammar |
| 6 | Underscore `1995_XA` | RECOGNIZE (`[ _]` class) | sbpy + astroquery agree; JPL-adjacent code lane |
| 7 | Packed case-sensitivity | Enforce exact case (no `re.IGNORECASE`; unpacked classes explicit) | `a0017` vs `A0345` are distinct values; folding merges them — enforced by construction |
| 8 | Bare packed numbers (`03202` in free text) + `(NNN)` area-code overlap | RECOGNIZE with word guards; document both as known v1 overclaims — caller routes ZIP/phone contexts, registry revisits (§13 row 9) | MPCORB-dump lane and `(433)`-shaped numbers need the lanes; guards cannot disambiguate `\d{5}` vs ZIPs or `(555)` vs area codes without membership |
| 9 | Registry LOOKUP_TABLE future | DEFER to MPCORB-snapshot `Section 6` + default-off `include_mpcorb_membership` (flag ships WITH its rule, never before) | Hundreds of thousands of rows on monthly cadence; v1 honest collapse per §7.2 |
| 10 | Label span inclusion | No label lane at v1 (no `MPC:`/`DES:` convention attested) | Differs from ISBN/ORCID deliberately — structure-only carriers |
| 11 | Which alternative written forms does v1 recognize (bare numbers `433`, subscript cycles, old-style systems, satellite `S/` forms)? | REJECT all at v1 with written rationale above; JPL bare-number lane is the documented scope cut | Unparenthesized runs unclaimable without registry; dead systems need distinct grammars; each cut cites §2.1 |

---

## 14. Ambiguity Analysis (Paxman-specific)

- No inherent designation-vs-designation positional ambiguity — fixed lane shapes eliminate the reordering ambiguity Date exhibits; longest-alternation inside one grammar resolves pack-vs-number nesting, and two distinct designations in one slice are authorial choice (segmentation intended), not lexical ambiguity.
- Same body, distinct designations is not ambiguity — `1997 RO4` and `2007 FK34` (both body 274301) are different canonical values with different provenance rows, exactly as UNSPSC parent-vs-commodity codes share digits but not identity; linkage is MPC orbit knowledge, not syntax, so no rule may merge them.
- Packed vs unpacked is not ambiguity — `J95X00A` and `1995 XA` normalize to one canonical value with one dedup key (ADR-0011 same-entity encodings); the `packed` format restores the spelling, like UNSPSC `native`.
- Case variance is not ambiguity — `2003 cp20` folds to `2003 CP20` deterministically on the unpacked lane, while packed case is preserved deterministically; lane-relative, never a coin flip.
- Staleness is not ambiguity — a designation's meaning is fixed at assignment (unlike UNSPSC code moves); determinism needs no snapshot because there is no registry at v1, and the future registry pins its `Provenance.version` when it lands.

---

## 15. URL Reference (authoritative, fetched 2026-10-07 unless noted)

| Claim | URL | Kind |
|-------|-----|------|
| Unpacked provisional syntax, letter tables, cycle scheme, surveys, old-style systems, retrospective A-prefix | https://minorplanetcenter.net/iau/info/DesDoc.html | primary |
| Packed provisional/permanent layouts, century codes, cycle letters, survey packs, tilde base-62, comet/satellite columns | https://minorplanetcenter.net/iau/info/PackedDes.html | primary |
| Numbering/naming process, WGSBN Bulletin officiality, 10-year privilege | https://minorplanetcenter.net/iau/info/HowNamed.html | primary |
| Unpacked provisional definition (normative prose mirror) | https://minorplanetcenter.net/mpcops/documentation/provisional-designation-definition/ | primary |
| Cometary designation system (sibling, deferred) | https://docs.minorplanetcenter.net/mpc-ops-docs/designations/cometary-designation-system | primary |
| Dual-status objects (`2060` Chiron, `4015` Wilson-Harrington) | https://docs.minorplanetcenter.net/mpc-ops-docs/designations/dual-status-objects | primary |
| Provisional-designation docs mirror + extended `_` scheme (Oct-2023 newsletter) | https://docs.minorplanetcenter.net/mpc-ops-docs/designations/provisional-designations | primary |
| 80-column optical format (all 80 columns allocated; packed cols 6–12) | https://minorplanetcenter.net/iau/info/OpticalObs.html | primary |
| Designation-identifier API (accepted inputs, packed/unpacked pairs) | https://minorplanetcenter.net/mpcops/documentation/designation-identifier-api/ | primary |
| MPC as single worldwide location (minor planets, comets, outer satellites) | https://minorplanetcenter.net/iau/mpc.html | primary |
| Live equation heading `(274301) Wikipedia = 1997 RO4 = …` | https://www.minorplanetcenter.net/db_search/show_object?object_id=274301 | primary |
| WGSBN naming rules (10-year privilege, Bulletin officiality) | https://www.wgsbn-iau.org/documentation/NamesAndCitations.pdf | primary (snippet-sourced; PDF unfetchable) |
| IAU naming themes page (naming authority context) | https://iauarchive.eso.org/public/themes/naming | primary (snippet-sourced; live page 404) |
| ADES `submit.xsd` (`PermIDType`, `BaseProvIDType`, `OldProvIDType` facets) | https://raw.githubusercontent.com/IAU-ADES/ADES-Master/master/xsd/submit.xsd | primary (schema) |
| ADES format info page | https://minorplanetcenter.net/iau/info/ADES.html | primary |
| JPL SBDB API accepted inputs (`sstr`, `des`) | https://ssd-api.jpl.nasa.gov/doc/sbdb.html | primary (resolution behavior) |
| JPL Horizons Lookup API (`sstr`, space-sensitivity) | https://ssd-api.jpl.nasa.gov/doc/horizons_lookup.html | primary (resolution behavior) |
| JPL planetary satellite discovery table (`S/2000 J11`) | https://ssd.jpl.nasa.gov/sats/discovery.html | primary (sibling namespace) |
| `sbpy.data.Names` parser/packer (reference-quality regex + round-trips) | https://sbpy.readthedocs.io/en/latest/_modules/sbpy/data/names.html | primary |
| `sbpy.data.Names` docs | https://sbpy.readthedocs.io/en/latest/sbpy/data/names.html | primary |
| `astroquery.mpc` target parser (unpacked-only input) | https://astroquery.readthedocs.io/en/latest/_modules/astroquery/mpc/core.html | primary |
| `astroquery.mpc` docs | https://astroquery.readthedocs.io/en/latest/mpc/mpc.html | primary |
| `astroquery.jplhorizons` pass-through + packed case footgun (#3220) | https://github.com/astropy/astroquery/blob/main/astroquery/jplhorizons/core.py | primary |
| `rlseaman/MPC_designations` library + SPECIFICATION.md (closest stdnum analogue) | https://github.com/rlseaman/MPC_designations | primary |
| PyPI `mpc-designation` | https://pypi.org/project/mpc-designation/ | primary |
| `jorbit.utils.mpc` pack/unpack | https://jorbit.readthedocs.io/en/latest/core/misc/mpc.html | primary |
| find_orb `mpc_obs.cpp` (pack/unpack/normalize suite) | https://github.com/Bill-Gray/find_orb/blob/master/mpc_obs.cpp | primary |
| Project Pluto packed-format explainer | https://projectpluto.com/packed.htm | secondary |
| Project Pluto `pack.txt` cycle>620 proposal | https://www.projectpluto.com/pack.txt | secondary |
| MPC NEOCP confirmation page (live temp-ID examples) | https://minorplanetcenter.net/iau/NEO/toconfirm_tabular.html | primary (examples) |
| Rubin PPDB schema (packed/unpacked char fields) | https://sdm-schemas.lsst.io/ppdb.html | primary (fields, not validator) |
| Wikidata P5736 (mandatory `[A-Z0-9][A-Z0-9/ ()-]{0,11}`, examples 2060/18374/37572) | https://www.wikidata.org/wiki/Property:P5736 | primary (constraint mirror) |
| python-stdnum docs index (no MPC/astronomy module; scope statement) | https://arthurdejong.org/python-stdnum/doc/ | primary (negative) |
| validator.js repo (no astronomy validator) | https://github.com/validatorjs/validator.js | primary (negative) |
| Wikipedia provisional designation (lineage + dual-status examples — secondary) | https://en.wikipedia.org/wiki/Provisional_designation_in_astronomy | secondary |
| Wikipedia minor-planet designation (Gould history, JPL-vs-MPC display — secondary) | https://en.wikipedia.org/wiki/Minor-planet_designation | secondary |
| ISSN research precedent (single-grammar) | docs/development/research/2026-08-21-issn-canonicalization.md | primary (repo) |
| IBAN research precedent (checksum-depth complement) | docs/development/research/2026-08-22-iban-canonicalization.md | primary (repo) |
| BIC research precedent (template) | docs/development/research/2026-08-23-bic-canonicalization.md | primary (repo) |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary (repo) |
| Paxman shipped precedent: ISBN grammar + rules + notation | paxman/capabilities/ISBN/grammar/isbn13_recognition.py, paxman/capabilities/ISBN/rules/isbn_range_message_ed2026.py, paxman/capabilities/ISBN/notation.py | primary (repo) |
| Paxman shipped precedent: ISSN grammar + rules + contract | paxman/capabilities/ISSN/grammar/issn_recognition.py, paxman/capabilities/ISSN/rules/iso_3297_ed2022.py, paxman/capabilities/ISSN/contract.py | primary (repo) |
| Paxman shipped precedent: GTIN notation + prefix rule, engine dedup + domain attrs | paxman/capabilities/GTIN/notation.py, paxman/capabilities/GTIN/rules/gs1_prefix_ed2026.py, paxman/engine/orchestrator.py, paxman/core/domain.py | primary (repo) |

---

## 16. Evidence Completion — Resolved

This report's minor-planet-specific authoritative evidence has been fetched and cited (2026-10-07):

- [x] Owner + RA pages: MPC (IAU; CfA-hosted, NASA-funded) owns provisional/packed/numbering; UNGM-style search (`db_search`) + machine identifier API; lineage 1892 → 1893 → 1916 → 1925 → surveys → 1994 comet reform → 2023 extended packing (packed-introduction date honestly unknown)
- [x] NOT-an-ISO-standard proved (no catalogue entry; ADES is an IAU XML schema sibling, not a parent) with related-scheme map (comets/satellites/JPL mirrors/WGSBN names)
- [x] Structure: unpacked `YYYY LL[n]` + half-month/second letter tables + cycle/subscript scheme + survey forms + A-prefix retrospective, ASCII, space-significant, ≥8 worked examples across all lanes
- [x] No checksum proved (PackedDes all-position exhaustiveness + 80-column exhaustiveness — two independent sources, zero check algorithms published; third-party pack tools concur)
- [x] Packed decode coherence: century `IJK`, cycle letter×10+digit (A=10…Z=35/a=36…z=61, verified against `K99AJ3Z`/`K07Tf8A`), tilde base-62 minus-620000 (arithmetic verified against `~AZaz`/`~zzzz`), survey packs, extended `_` shape (year-letter mapping flagged for implementation-time verification)
- [x] Case-lane finding: unpacked folds, packed case-significant (`a0017` vs `A0345` trap pair), enforced by omitting `re.IGNORECASE`
- [x] Ecosystem regex consensus: ADES XSD facets + sbpy + astroquery + MPC identifier API + JPL SBDB/Horizons + Wikidata P5736 (plus stdnum/validator.js/astropy confirmed absence, digest2/mpcorbfile consumer-only)
- [x] Recognition-surface inventory complete (§2.1): 19 rows, every spec/schema/≥2-validator form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form
- [x] Wild input shapes validated (§2.2, 18 categories) against DesDoc/PackedDes/HowNamed + ADES + NEOCP + sbpy/astroquery/JPL/MPC-API
- [x] Label scope decision (no label lane — structure-only carriers, deliberate ISBN/ORCID difference)
- [x] Same-entity (packed↔unpacked) vs distinct-identity (linkages, parents-vs-numbers) decisions
- [x] Separator decision (space + underscore RECOGNIZE; glued/dotted/hyphenated REJECT with evidence — ISBN/Phone analogy applied, not assumed)
- [x] Registry scope decision (PARSER-only v1 + named MPCORB LOOKUP_TABLE upgrade; placebo-flag lesson recorded)
- [x] File layout / rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

---

## Appendix — What the Shipped ISBN, ISSN, GTIN and Country Capabilities Teach MinorPlanet (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (explored 2026-10-07 on `feature/unspsc-capability`, not speculative) and anchors the proposal to what Paxman already ships.

ISBN (`paxman/capabilities/ISBN/grammar/isbn13_recognition.py:30-40`) teaches the single-grammar staged pipeline (`PipelineGrammar` + `StandardPre(empty_guard=True)` + `RegexStage` with module-scope pattern, fused label, lookarounds, `single_value=True`). ISSN (`paxman/capabilities/ISSN/grammar/issn_recognition.py:41-60`) teaches one grammar covering two spellings (optional separator at the canonical position, `LabelMatcher`, `BoundarySpec.WORD`, `re.IGNORECASE | re.ASCII`) — and, by contrast, why MinorPlanet omits `IGNORECASE` (packed case significance). ISSN's rule (`rules/iso_3297_ed2022.py:48-53`, `Section 4-issn-check-digit`, PARSER, `target_semantics`/`requires_features` frozensets) is the direct model for MinorPlanet's five PARSER rules, including the ADR-0012 vacuity posture. GTIN (`notation.py:20-22`) teaches the notation facet pattern (`digits` + `native_length` + trace-only `has_ai`; MinorPlanet analog: `designation` + `form` + case-exact `packed`), and GTIN's Section-2 rule (`rules/gs1_prefix_ed2026.py:96-109`, full shape re-check before prefix lookup) is the model for lane-strict `matches()`. The engine (`paxman/engine/orchestrator.py`: `_dedup_spans` per-grammar longer-wins at `:463-492`, total order at `:431-442`, `_dedup_candidates` on `(value, recognition_rule, validation_rule)` at `:843-847`, `_enforce_single_value_invariant` at `:625-683`, MISSING-vs-INVALID at `:882-889`) teaches that packed/unpacked same-value candidates coalesce and that dropped-rule vs unclaimed-shape produce INVALID vs MISSING. The domain (`paxman/core/domain.py`: six enforced attrs at `:253-278`, `RecognitionMatch` half-open spans at `:78-86`) fixes the rule/span contract. The four architectural lessons for MinorPlanet:

1. **Grammar strips, rule validates, capability formats.** Case/space normalization and pack/unpack transcoding are syntax (grammar facets); letter-sets and decode coherence are semantics (rules); packed rendering is display (`format_value`). No layer borrows another's job.
2. **One file per provenance, one class per section.** Unpacked-definition + packed-spec + numbering stay in three files with three `PUBLICATION` constants; `Section N-*` naming throughout.
3. **No `output_format` in rules, ever.** `packed` appears only in `capability.py`; `normalize()` always returns the unpacked `designation`.
4. **Single grammar with lane alternation avoids spurious AMBIGUOUS; full-conjunction rules avoid vacuous SUCCESS.** The packed-contains-number nesting is handled inside one pattern; each rule re-checks its full lane so pinned contracts cannot validate off-lane garbage.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for MinorPlanet. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the deeper ISBN precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
