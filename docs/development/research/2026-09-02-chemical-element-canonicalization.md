# Chemical Element Canonicalization Research — paxman-python

**Date:** 2026-09-02
**Scope:** Primary-source survey of the IUPAC element-nomenclature corpus (Red Book 2005 Chapter IR-3, the IUPAC Periodic Table of the Elements, CIAAW atomic-weight reports, and the Pure and Applied Chemistry element-naming recommendation series), ecosystem canonicalization practice (pymatgen, mendeleev, periodictable, chempy, RDKit, npm `chemical-elements`, plus the verified absence of any element validator in validator.js and python-stdnum), and Paxman's grammar/rule/provenance architecture, to ground the design of a future `element` capability (MILESTONE row 22). No source code, tests, or configuration were modified.
**Evidence basis:** IUPAC Periodic Table of the Elements page + 04 May 2022 PDF (fetched), CIAAW Standard Atomic Weights table + publications page (fetched), IUPAC naming announcements 8 June 2016 and 28 November 2016 (fetched), naming-archives page (fetched), "On the discovery of new elements" 2018 page (fetched), Red Book 2005 full PDF — Chapter IR-3 and Tables I/II extracted verbatim (fetched via Internet Archive snapshot of `old.iupac.org`), QMUL nomenclature bibliography (fetched), Brief Guide to the Nomenclature of Inorganic Chemistry PDF (fetched); ecosystem source for pymatgen `periodic_table.py`, mendeleev `mendeleev.py`, periodictable `core.py`, chempy `util/periodic.py`, RDKit `PeriodicTable.h`/`atomic_data.cpp`, cheminfo `mass-tools` `chemical-elements` (all fetched 2026-09-02); validator.js and python-stdnum checked and confirmed to ship **no** element validator (negative finding); shipped Paxman precedents MacAddress (most recent single-grammar capability), Country/Currency/Language (LOOKUP_TABLE + data-module pattern), SIUnit (kernel multi-matcher lexicon precedent), ISBN/ISSN/BIC research reports. Repo state: `dev @ 92c1d94` — engine owns per-grammar containment dedup (`_dedup_spans`), total recognition ordering, `Grammar.single_value` enforcement (`MultipleMentionsError`), and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md (Step 0 scaffolder, §5 one-file-per-publication, §7 contract, §10 test strategy), HOW_TO_ADD_NEW_GRAMMAR.md (strategy chooser; kernel matcher kinds), ARCHITECTURE.md, and the research precedents `2026-08-21-issn-canonicalization.md`, `2026-08-22-iban-canonicalization.md`, `2026-08-23-bic-canonicalization.md`, `2026-08-23-language-canonicalization.md`, and `2026-08-31-mac-address-canonicalization.md` (the heading skeleton mirrored here).

---

## Executive Summary

Chemical element is a **strong** fit for a Paxman capability: it has an unambiguous canonical form (**the IUPAC element symbol, 1–2 letters, first uppercase and second lowercase — e.g. `Fe`**), an extremely stable standard corpus (**IUPAC Nomenclature of Inorganic Chemistry — IUPAC Recommendations 2005 ("Red Book"), Chapter IR-3**, RSC, ISBN 0-85404-438-8, still current) with the IUPAC Inorganic Chemistry Division (historically the Commission on Nomenclature of Inorganic Chemistry, CNIC) and CIAAW as the naming/registry authorities, a small, closed, authoritative registry (**the IUPAC Periodic Table of the Elements, latest release dated 4 May 2022 — exactly 118 elements, none added since nihonium/moscovium/tennessine/oganesson were approved on 28 November 2016**), and a well-understood human surface (proper-case symbol, lowercase English common-noun name, and the Red-Book-sanctioned "element 118" atomic-number designation). The domain mirrors Paxman's value proposition for Country/Currency/Language: recognizing tolerant human surface, validating strictly against authority, returning a canonical compact value with provenance. **There is no checksum** — unlike IBAN/ISBN/ISSN, element designations carry no check character; membership in the 118-entry registry *is* the entire validity criterion (structure plus registry, the BIC model).

Key findings that shape the design:

1. **Canonical form is the IUPAC symbol** (`Fe`, `Og`) — a bijection with atomic number 1–118 fixed since 2016 (element 119/120 remain undiscovered as of 2026-09-02; RIKEN and JINR searches ongoing). Every current element has a permanent name and symbol; the Red Book's temporary systematic designators (`Uut`, `Uue`) are retired for all 118 and are a documented REJECT class.
2. **One grammar (`element_recognition`), three kernel matchers** — two `LexiconMatcher`s (symbol keys: canonical + all-lowercase spellings; name keys: lowercase + capitalized English names including both IUPAC-sanctioned alternative spellings) plus one `RegexMatcher` for the fused atomic-number labels (`element 26`, `atomic number 26`, `Z = 26`) attested verbatim in Red Book IR-3.1.1 and Table II footnote b. A lexicon-keyed grammar is mandatory, not stylistic: a regex claiming arbitrary 1–2-letter or 3–13-letter word runs would turn every English word into an `INVALID`, whereas lexicon keys emit only genuine element designations (SIUnit `symbol_recognition` and Country `name_recognition` precedent).
3. **Validation is LOOKUP_TABLE-level** — the Red Book IR-3.1 rule (kind `specification`) validates symbol/name tokens against the IUPAC symbol and English-name tables and normalizes to the canonical symbol; the Periodic Table registry rule (kind `registry`, snapshot 04 May 2022) validates atomic-number tokens (Z 1–118) and resolves Z → symbol. There is **no third "issued/live" level**: unlike ISBN (allocated ranges) or ISSN (Register membership), every IUPAC-listed element is by definition live; the only staleness axis is a future 119th element (Provenance version stamp).
4. **The collision surface is the design's hard problem, and Paxman already ships the answer** — 13 two-letter element symbols (`al, am, as, at, be, ca, cd, co, he, in, la, no, re`) are also high-frequency English words and are already in the shipped 67-word `COMMON_WORDS` table (`paxman/core/grammar/data/common_words.py`); symbol/name lexicons ship `suppressible=True` so `suppress_common_words=True` (contract flag, default `False` like every shipped capability) removes the worst prose false positives. Residual risk concentrates in the single-letter symbols (`I` → iodine vs the English pronoun) and rare interjections (`Er`, `Ta`, `Pa`, `Ho`, `Mo`) — documented, not hidden.
5. **Provenance is cleanly split per HOW_TO_ADD_NEW_CAPABILITY.md §5** — one file per publication: `rules/iupac_red_book_2005.py` (IR-3.1 names and symbols; kind `specification`, year 2005) and `rules/iupac_periodic_table_ed2022.py` (the 04 May 2022 registry snapshot; kind `registry`), sharing one `rules/data/periodic_table_ed2022.py` data module (118 symbols, name→symbol map including the Red-Book-footnoted `aluminum`/`cesium` alternative spellings, Z→symbol map). CIAAW atomic weights (2021 report; 2024 revisions) are explicitly out of scope — the capability canonicalizes designations, not nuclear properties.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---

## 1. Target User

| Persona | Why they need element canonicalization | Typical context |
|---------|----------------------------------------|-----------------|
| Materials-science / cheminformatics data engineer | Lab notebooks, instrument exports, and CSVs mix `Fe`, `iron`, `IRON`, `26`, `Z=26` for the same element; downstream schemas want one symbol key | LIMS ingestion, materials databases (pymatgen/Materials Project style), spectroscopy metadata |
| Scientific LLM-output normalizer | Model output references elements inconsistently ("Iron (Fe, Z=26)"); structured extraction needs canonical tokens with provenance | Agent pipelines, RAG indexers over chemistry corpora |
| Education-platform developer | Quiz and flashcard content writes element names in prose; grading needs symbol-canonical answers | Periodic-table tutors, chemistry homework graders |
| Regulatory / safety-sheet processor | SDS and hazard statements write "lead", "Pb", "element 82" interchangeably; compliance mapping wants the symbol | SDS parsing, ELN/ERP integration |
| Bibliographic / patent indexer | Text mentions elements by name and symbol; faceted search wants a normalized element facet | Patent classifiers, journal indexing |

**User-visible contract:** The caller supplies raw human text (one mention per `canonicalize()` call) and an `ElementContract`; Paxman returns one canonical element symbol (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation to the Red Book and the IUPAC Periodic Table. This mirrors Country/Currency ergonomics, but the canonical default is the **proper-case IUPAC symbol** (`Fe`), with lowercase-name and atomic-number rendering offered as presentation-only formats.

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

The inventory below is specific to the element domain (the set is **not** ORCID's hyphen/compact/URI taxonomy nor Language's tag/code/name taxonomy): the element surface is *symbol spellings × name spellings × atomic-number designations*, plus retired placeholder names and isotope notation that must be explicitly rejected. Symbol evidence: IUPAC Periodic Table of the Elements, 4 May 2022 (all 118 symbols, proper case); ecosystem case handling per the table in §2.2. Name evidence: Red Book 2005 Table I ("Names, symbols and atomic numbers of the elements" — names printed lowercase as English common nouns, with footnotes a and c sanctioning the alternative spellings `aluminum` and `cesium`). Atomic-number-designation evidence: Red Book IR-3.1.1 verbatim — "Such elements may be referred to by their atomic numbers, as in 'element 120' for example" — and Table II footnote b — "One may also write, for example, 'element 112'"; sustained in practice for named elements (Wikipedia, *Ununennium*: superheavy-element scientists "call it 'element 119', with the symbol E119, (119) or 119").

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Canonical symbol (proper case) | `Fe`, `Og`, `C` | IUPAC Periodic Table 04May22 (official display); accepted by all six ecosystem libraries (pymatgen, mendeleev, periodictable, chempy, RDKit, npm chemical-elements) | canonical | **RECOGNIZE** | symbol lexicon keys (canonical spellings) |
| All-lowercase symbol | `fe`, `og`, `c` | MILESTONE row 22 ("fe" → "Fe"); chempy `atomic_number()` (`.capitalize()` fold); lowercase chemical-formula/URL contexts | common (informal/digital) | **RECOGNIZE** | symbol lexicon keys (lowercase spellings) |
| English name, lowercase | `iron`, `gold`, `carbon` | Red Book Table I (names listed lowercase); periodictable stores names lowercase; chempy `lower_names` | common (prose) | **RECOGNIZE** | name lexicon keys (lowercase) |
| English name, capitalized / uppercase | `Iron`, `IRON` | pymatgen `from_name()` (`.capitalize()` match); headings, tables, sentence-initial prose | common | **RECOGNIZE** | name lexicon keys (capitalized + uppercase folded at emit) |
| Alternative IUPAC spellings | `caesium`/`cesium`, `aluminium`/`aluminum` | Red Book Table I footnotes a & c verbatim: "The alternative spelling 'aluminum' is commonly used." / "The alternative spelling 'cesium' is commonly used."; ecosystem split (pymatgen/mendeleev/periodictable ship US; chempy/RDKit/npm ship IUPAC; pymatgen maps UK→US) | common (regional) | **RECOGNIZE both spellings** | name lexicon alias keys → same canonical symbol |
| `element N` designation | `element 26`, `Element 118` | Red Book IR-3.1.1 ("referred to by their atomic numbers, as in 'element 120'") + Table II footnote b; press and superheavy-element literature | common | **RECOGNIZE** | fused label branch `element` + 1–3 digits (RegexMatcher) |
| `Z = N` designation | `Z=26`, `Z = 92`, `Z:8` | Red Book IR-3.2 (atomic number as symbol index); CIAAW table column `Z`; ubiquitous nuclear/atomic physics prose | common (physics) | **RECOGNIZE** | fused label branch `Z` + separator class + 1–3 digits |
| `atomic number N` designation | `atomic number 26`, `atomic number 118` | Chemistry textbooks/encyclopedias (Britannica list: "Each element is followed by its atomic number") | common | **RECOGNIZE** | fused label branch `atomic\s+number` + digits |
| All-caps two-letter symbol | `FE`, `NO`, `IN` | chempy only (`.capitalize()` folds it); all-caps posters/engineering drawings | occasional | **DEFER** (community `extra_grammars` case-insensitive lexicon) | would need all-caps keys — collides catastrophically with acronym/ALL-CAPS prose (`NO SMOKING`, `IN CASE OF FIRE`) |
| Inverted-case symbol | `fE`, `fE` | No validator accepts; never spec-sanctioned | rare (typo) | **REJECT** | outside lexicon keys (typo, not convention) |
| Abbreviated atomic-number labels | `at. no. 26`, `atomic no. 26` | Textbook/table shorthand | occasional | **DEFER** | label variant with dot tolerance — extra_grammars candidate |
| Latin/traditional element names | `ferrum`, `natrium`, `wolfram`, `stibium` | Red Book Table I footnotes g, k, m, o, p, b (symbol-deriving names: "The element symbol Fe derives from the name ferrum" etc.); everyday in several European languages | occasional | **DEFER** | name-lexicon alias keys via community extension (not IUPAC English names) |
| `sulphur` spelling | `sulphur` | UK traditional usage (Britannica/older texts); IUPAC resolved to `sulfur` (Red Book Table I lists `sulfur`, no footnote) | occasional | **REJECT** | not a sanctioned spelling; accepting it is fuzzy autocorrection (community alias if ever demanded) |
| Isotope / nuclide notation | `Fe-56`, `iron-56`, `56Fe`, `²³⁸U` | Red Book IR-3.2 (mass number as left upper index); nuclear physics prose | common (physics) | **REJECT as element mention** (nuclide ≠ element — different domain) | word guard + isotope-suffix guard keep `Fe-56`/`56Fe` unclaimed (see §8 rows 15–16, §13 D6) |
| Temporary systematic names/symbols | `ununtrium`, `Uut`, `Uue`, `element 119` (unnamed) | Red Book IR-3.1.1 + Table II ("used only when the permanent name has not yet been assigned"); all retired for Z 1–118 since 28 Nov 2016 | legacy | **REJECT** | not lexicon keys (3-letter symbols cannot match 1–2-letter keys); `element 119` label would be claimed and ruled `INVALID` — correct (no such IUPAC element yet) |
| Bare atomic number | `26` | Databases, spread-sheets | common (typed data) | **REJECT** | no distinct shape — any integer would claim; use the labeled forms (`element 26`, `Z = 26`) |
| Deuterium/tritium letters | `D`, `T` | Red Book IR-3.1 + Table I footnote f: "the symbols D and T may be used for the hydrogen isotopes"; pymatgen even ships `Element.D` | occasional (physics) | **REJECT** | nuclide designators, not element symbols; hydrogen canonicalizes to `H` |
| Element symbols inside chemical formulas | `Fe2O3`, `NaCl`, `CO2`, `H2O` | Chemistry corpora everywhere | very common | **REJECT (out of scope)** | word-boundary guard: glued to digits/letters → never claimed → `MISSING` (formula parsing is a future sibling domain) |
| Localized non-English names | `Eisen`, `hierro`, `sølv` | Red Book IR-3.1: other languages have "well-established and very different names" | occasional | **DEFER** | localized-alias lexicon via community extension (Language `LOCALIZED_LANGUAGE_KEYS` precedent) |
| Group / period / block references | `group 8`, `period 4`, `p-block` | Red Book IR-3.5 (elements in the periodic table); textbooks | common (prose) | **REJECT** | designates a *class* of elements, not one element — not a mention |

A v1 that does NOT recognize a commonly attested form must state that explicitly here AND raise it as an Open Decision (§13). The two deliberate scope cuts above are: all-caps two-letter symbols (D3) and abbreviated `at. no.` labels (D7); both are DEFER rows with named mechanisms.

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical symbol | `Fe`, `Og`, `Au` | Registry master form; lexicon key |
| 2 | Lowercase symbol | `fe`, `au` | MILESTONE-mandated; second lexicon key set |
| 3 | ALL-CAPS symbol | `FE`, `AU` | Deferred (D3): in caps prose `NO`/`IN`/`AS`/`AT`/`BE`/`HE`/`AM`/`CA`/`CO`/`LA`/`CD` are acronyms/words, not elements |
| 4 | Inverted case | `fE`, `aU` | Never valid; REJECT (typo class) |
| 5 | Name, any case | `iron`, `Iron`, `IRON` | Case-folded keys; names have no common-word collisions (`tin`, `lead`, `iron` genuinely name elements) |
| 6 | Alternative spelling | `caesium`, `cesium`, `aluminium`, `aluminum` | Both fold to `Cs` / `Al` — Red Book footnote authority |
| 7 | Fused label, space | `element 26`, `atomic number 8` | Span includes label (ISSN/BIC/MAC precedent); notation carries digits only |
| 8 | Fused label, `=` / `:` | `Z=26`, `Z: 26`, `Z = 8` | Separator class `[\s:=]+`, never zero-width |
| 9 | Irregular whitespace | `element  26`, `Z\t26` | `[\s:=]+` tolerates runs; single-value grammar still one mention |
| 10 | Over-long / under-long number | `element 0`, `element 1000`, `Z = 12 34` | Grammar claims 1–3 digits; rule rejects outside 1–118 → `INVALID`; `1000` is 4 digits → not claimed by the 1–3-digit branch → residue → `MISSING` |
| 11 | Trailing annotation | `Fe (iron)`, `element 26 (iron)` | Span excludes parenthetical; core canonicalizes; annotation is residue |
| 12 | Isotope suffix | `Fe-56`, `U-235` | Isotope-suffix guard (right `-\d` forbidden) → unclaimed → `MISSING` (D6); silently returning `Fe` for a nuclide mention would be lossy |
| 13 | Left-index isotope | `56Fe`, `²³⁸U` | Left glue (digit/letter before symbol) fails word guard → `MISSING` |
| 14 | Formula context | `Fe2O3`, `NaCl`, `CO2` | Right glue (digit/letter) fails word guard → `MISSING` — no spurious element SUCCESS inside compounds |
| 15 | Prose word collisions | `in`, `no`, `at`, `as`, `be`, `he`, `am`, `al`, `ca`, `co`, `la`, `cd`, `re` | 13 of the shipped 67 `COMMON_WORDS` are element symbols; `suppressible=True` lexicons + `suppress_common_words=True` suppress (default off — documented risk, §13 D5) |
| 16 | Single-letter pronoun | `I am here` | `I` → iodine is the top residual false positive (not in `COMMON_WORDS`); documented, single-value grammar yields one mention |
| 17 | OCR / homoglyph | `F€`, `О` (Cyrillic O), `K` (Kelvin sign U+212A) | ASCII-only lexicon keys → `MISSING`; no autocorrection (BIC K-guard precedent) |
| 18 | Multiple per line | `Fe, Cr, and Ni` | 3 distinct mentions → `MultipleMentionsError` (single_value=True; segmentation intended) |
| 19 | Co-reference | `Iron (Fe)` | Two mentions, one canonical value → coalesced `SUCCESS Fe` (engine single-value clustering: distinct_values == 1) |
| 20 | Quoted / bracketed | `"Fe"`, `[Og]` | Word guards pass (punctuation is non-word); SUCCESS with span inside quotes |
| 21 | Invalid symbol shape | `Xx`, `Jq`, `Qq` | Not lexicon keys → `MISSING` (J and Q appear in no IUPAC symbol); contrast the label branch which yields `INVALID` for out-of-range numbers |
| 22 | Placeholder names | `ununtrium`, `Uuo` | Retired 2016; not keys → `MISSING` (never silently re-canonicalized to Nh/Og) |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| pymatgen `Element` (Enum) | `Element("Fe")` — exact-case Enum lookup; `Element("fe")`/`Element("FE")` **fail**. `from_name()` is case-insensitive: `name.capitalize()` match against US-spelling data, with `uk_to_us = {"aluminium": "aluminum", "caesium": "cesium"}` mapping both spellings in. `from_Z(26)` resolves by atomic number |
| mendeleev `element()` | `len(ids) <= 3 and ids.lower() != "tin"` → SQL `Element.symbol == ids` else `Element.name == ids` — case-sensitive both ways (`"fe"`, `"iron"` **fail**); `"tin"` special-cased to the name path; `element(26)` by atomic number |
| periodictable | `setattr(self, symbol, element)` attribute lookup — `table.symbol("Fe")` works, `"fe"` fails; names stored lowercase, `table.name("iron")` works, `"Iron"` fails; `table[26]` by Z |
| chempy `atomic_number()` | `symbols.index(name.capitalize())` with fallback `lower_names.index(name.lower())` — the **only** ecosystem library with fully case-insensitive symbol lookup (`fe`/`FE`/`Fe` all resolve); ships IUPAC spellings (`Aluminium`, `Caesium`) |
| RDKit `PeriodicTable` | `byname.find(elementSymbol)` — case-sensitive `std::map`; names are IUPAC (`Aluminium` Z=13, `Caesium` Z=55); no name→Z API |
| npm `chemical-elements` | `elementsObject[element.symbol]` — case-sensitive object keys; IUPAC spellings; no case-insensitive path |
| validator.js | **Negative finding:** full validator export list (`isISBN`, `isISSN`, `isISO4217`, `isBIC`, …) contains no element/periodic-table validator |
| python-stdnum | **Negative finding:** module index ships no element module — the library is scoped to check-digit identifiers, which element designations are not |

**Normalization contract (reuse ISBN/ISSN/MAC pattern):**

```python
# Symbol branch (lexicon keys already constrain the input; the emit folds case):
#   matched token is "Fe" or "fe"  ->  token = t[0].upper() + (t[1].lower() if len(t) == 2 else "")
# Name branch:
#   matched token is "Iron"/"iron"/"IRON" ->  token = t.lower()
# Atomic-number branch:
#   matched digits "026"/"26" ->  token = str(int(digits))
# Then rule-side lookup: SYMBOLS / NAME_TO_SYMBOL / Z_TO_SYMBOL -> canonical "Fe".
# No separators exist to strip (symbols and names are single tokens); isalnum
# collapsing is unnecessary and would corrupt nothing — keys are pure ASCII
# letters/digits by construction.
```

### 2.3 What input is NOT a element mention

- **Chemical formulas and compounds** — `Fe2O3`, `NaCl`, `H2O`, `CO2`: the element capability does not extract elements from compounds; word-boundary guards make these `MISSING`. A future chemistry-formula domain would parse them wholesale.
- **Nuclides and isotopes** — `Fe-56`, `56Fe`, `D`, `T`: a nuclide is a (Z, A) pair, not an element; canonicalizing to the bare element silently drops the mass number. `MISSING` by guards (§13 D6).
- **Bare integers** — `26`: no shape of its own; only labeled designations claim numbers.
- **Placeholder designations** — `ununtrium`, `Uut`, `Uue`: retired for all 118 named elements; `element 119`+ is not yet an IUPAC element (claims under assessment per the 2018 IUPAC/IUPAP JWG provisional report).
- **Classes of elements** — `group 8`, `transition metal`, `lanthanoid`, `period 4`: not a single element.
- **Sibling identifier domains** — CAS Registry Numbers (`50-00-0`), InChI strings, UN numbers: different syntaxes, no overlap with 1–2-letter keys or the label branches.

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md; `docs/recipes/segmentation.md`, ADR-0004). The element grammar sets `single_value = True` (MacAddress/BIC/ISSN precedent): two distinct mentions (`Fe and Cu`, `Fe, Cr, Ni`) raise `MultipleMentionsError` with the split-then-canonicalize pointer; identical canonical values coalesce — `Iron (Fe)` is one logical mention-cluster resolving to `Fe` and returns `SUCCESS` (engine `_enforce_single_value_invariant` merges overlapping clusters and only raises when distinct values > 1). Co-reference between a name and its symbol in one slice is therefore not an error; co-reference between *different* elements is un-segmented input.

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — token plus shape discriminator

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ElementNotation:
    """Chemical element notation — grammar-normalized token plus shape.

    ``token`` is the grammar-folded designation:
      - shape ``"symbol"``: 1-2 ASCII letters in IUPAC case convention
        (first uppercase, optional second lowercase), e.g. ``"FE"``-shaped
        input cannot occur — keys are ``"Fe"`` and ``"fe"`` spellings only;
        ``token`` is the canonical-case fold (``"fe"`` -> ``"Fe"``).
      - shape ``"name"``: lowercase ASCII English element name, e.g. ``"iron"``
        (Red Book Table I lists names as lowercase common nouns).
      - shape ``"atomic_number"``: 1-3 ASCII digits, e.g. ``"26"``, from the
        fused-label branch (``element 26`` / ``atomic number 26`` / ``Z = 26``);
        the label itself is NOT carried — it lives only in the raw span.

    The grammar never validates registry membership or resolves names/numbers
    to symbols; rules own that (grammar/rule boundary per
    HOW_TO_ADD_NEW_GRAMMAR.md). ``shape`` discriminates the three surfaces,
    mirroring the MacAddress ``shape`` / Currency ``shape`` precedents.
    """

    token: str  # "Fe" (symbol) | "iron" (name) | "26" (atomic_number)
    shape: str  # "symbol" | "name" | "atomic_number"
```

**Considered alternative — single field `compact` only:** a bare `"Fe"`/`"iron"`/`"26"` string cannot be routed: the rules must know whether `26` is an atomic number or the digits of something else, and whether `iron` should be name-looked-up. The decomposition is preferred because (1) each shape has a distinct authority table (symbol set / name map / Z map), (2) rule routing keys off `shape` exactly like Currency (`shape != "code"` → `False`) and Country (`shape != "alpha2"` → `False`), and (3) provenance differs by shape — symbol/name mentions cite the Red Book rule, atomic-number mentions cite the Periodic Table registry rule.

**Invariants the grammar enforces (before rules):**
- `symbol` token is 1–2 ASCII letters, IUPAC case convention (`[A-Z][a-z]?`) — enforced by the lexicon key sets themselves (keys are `Fe`-style and `fe`-style spellings; `FE`/`fE` are not keys).
- `name` token is a lowercase ASCII English element name — keys are lowercase + capitalized; emit folds to lowercase.
- `atomic_number` token is 1–3 ASCII digits, no leading-zero preservation (`"026"` → `"26"`); range 1–118 is **not** grammar business — the registry rule owns it.

### 3.2 Why not carry labels or whitespace in the notation

The fused labels (`element`, `atomic number`, `Z`) and separator runs have **no lexical significance** for validity — the Red Book sanctions the *designation*, not a spelling of the label. As in ISSN (`ISSN:`), BIC (`BIC:`/`SWIFT:`), and MAC (`MAC`), the raw span **includes** the label while the notation is label-free; presentation (`format_value`) never re-derives labels. Whitespace between label and digits is `[\s:=]+`, one-or-more — a glued `element26` cannot match (label branch requires a separator), and `Z26` likewise does not claim (deliberate: glued Z+number is too ambiguous with identifier codes).

### 3.3 Why `shape` is a free `str`, not a `Literal`

`shape` is a routing key for rules, not a promise to callers — exactly the MacAddress decision (`"eui48"`/`"eui64"` free `str`, "mirroring the ISBN two-length precedent") and Currency (`"code"`). A `Literal` would freeze the vocabulary against future community shapes (`"latin_name"` via `extra_grammars`, §2.1 DEFER rows) and buys no safety the rule-side tables don't already enforce.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Lexicon for symbols and names, Regex for labeled numbers

Per HOW_TO_ADD_NEW_CAPABILITY.md's recognition-strategy chooser, element *names* are a finite vocabulary (118 + 2 sanctioned alternative spellings) → **Lexicon**; element *symbols* are likewise a finite vocabulary once case convention is enforced by key sets (236 keys) → **Lexicon**; the fused atomic-number designations are a distinctive syntactic shape → **Regex**. HOW_TO's chooser says "codes *and* names → one grammar per strategy"; the shipped kernel path supersedes that split: one `PipelineGrammar` may declare a **matcher tuple** spanning kinds (regex/lexicon/scanner/combinator/candidates/label per `paxman/core/grammar/matchers/__init__.py`), and SIUnit's `SymbolRecognition` is the shipped multi-matcher precedent (`matchers = (_BASE_MATCHER, _COMBINATOR_MATCHER)`). A lexicon-keyed grammar is **mandatory** for correctness here, not preference: a regex `[A-Za-z]{1,2}` symbol branch would claim every 1–2-letter word (`or`, `of`, `to`, `we`) and a `[A-Za-z]{3,13}` name branch every word in the sentence — recognition would succeed on all English text and every non-element word would surface `INVALID`. Lexicon keys emit **only** genuine designations; unknown words are `MISSING` (nothing recognized), which is the correct MISSING/INVALID boundary (§9).

### 4.2 Reference pattern (adapted from SIUnit `symbol_recognition`, Country `name_recognition`, BIC and ISSN verbatim precedent)

SIUnit's shipped multi-matcher grammar (verbatim shape — `LexiconMatcher` with case-exact keys, `BoundarySpec`, `RegexMatcher`, `emit` functions building the notation, `matchers` tuple, `run_matchers` delegation with longer-wins dedup) is the direct template:

```python
"""Element recognition — symbol lexicon, name lexicon, fused atomic-number label."""

from __future__ import annotations

from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.grammar.data.element_keys import (
    ATOMIC_NUMBER_LABEL_PATTERN,
    NAME_KEYS,
    SYMBOL_KEYS,
)
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.lexicon import LexiconMatcher
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

# Symbol keys: canonical IUPAC spellings ("Fe") plus all-lowercase ("fe").
# ALL-CAPS ("FE") and inverted case ("fE") are deliberately NOT keys (§2.1, D3):
# 13 two-letter symbols collide with high-frequency English words and all-caps
# prose ("NO SMOKING", "IN CASE OF FIRE") is acronym territory.
# Boundary: word-only both sides; the right side additionally forbids a
# hyphen-followed-by-digit run (isotope suffix: "Fe-56" is a nuclide mention,
# not an element mention — §8 row 15, D6). "56Fe" / "Fe2O3" fail the left /
# right \w guard naturally.
_ELEMENT_SYMBOL_BOUNDARY = BoundarySpec(
    left=("\\w",), right=("\\w", "-\\d"), mode="zero_width"
)


def _emit_symbol(span: tuple[int, int], ctx: ScanContext) -> ElementNotation:
    s, e = span
    t = ctx.text[s:e]
    token = t[0].upper() + (t[1].lower() if len(t) == 2 else "")
    return ElementNotation(token=token, shape="symbol")


def _emit_name(span: tuple[int, int], ctx: ScanContext) -> ElementNotation:
    s, e = span
    return ElementNotation(token=ctx.text[s:e].lower(), shape="name")


def _emit_z(span: tuple[int, int], ctx: ScanContext) -> ElementNotation:
    # Span includes the fused label ("element 26"); notation carries digits only.
    # The digits capture group is projected via the emit span contract — at
    # implementation, project the group start/end exactly as the kernel emit
    # validation requires (mirror SIUnit/LabelMatcher wiring; verify the
    # RegexMatcher group-projection seam at plan time).
    raise NotImplementedError  # TODO(scaffold): replace with group-span emit


_SYMBOL_MATCHER = LexiconMatcher(
    tokens=SYMBOL_KEYS,
    boundary=_ELEMENT_SYMBOL_BOUNDARY,
    view=None,
    emit=_emit_symbol,
    representation="auto",
    suppressible=True,  # 13 COMMON_WORDS symbols: in/no/at/as/be/he/am/al/ca/co/la/cd/re
)

_NAME_MATCHER = LexiconMatcher(
    tokens=NAME_KEYS,
    boundary=BoundarySpec.WORD,
    view=None,
    emit=_emit_name,
    representation="auto",
    suppressible=True,  # harmless today; future alias keys may need it
)

# Fused label branch — Red Book IR-3.1.1 sanctions "element 120"; Table II
# footnote b: "One may also write, for example, 'element 112'." Separator
# class [\s:=]+ one-or-more, never zero width (BIC/ISSN/MAC label precedent):
# "element26" cannot fuse; "Z26" (glued) deliberately does not claim.
_Z_PATTERN = rf"(?ai:(?:(?:{ATOMIC_NUMBER_LABEL_PATTERN})[\s:=]+)(?P<z>[0-9]{{1,3}}))(?![0-9])"

_Z_MATCHER = RegexMatcher(
    pattern=_Z_PATTERN,
    boundary=BoundarySpec.WORD,
    view=None,
    emit=_emit_z,
)

assert len(SYMBOL_KEYS) == 236, "symbol keys must be 118 canonical + 118 lowercase"
assert len(NAME_KEYS) >= 476, "name keys must cover lower+capitalized + 2 alt spellings"


class ElementRecognitionGrammar(PipelineGrammar[ElementNotation]):
    """Grammar: element_recognition — symbol/name lexicons + Z-label regex.

    Lexicon-keyed by construction: arbitrary words are never claimed (no
    INVALID-on-prose); non-member designations are MISSING at recognition.
    Case convention for symbols is enforced by the key sets; names fold to
    lowercase at emit. Registry membership, Z range, and canonical mapping
    are rule-owned. single_value=True: one element per canonicalize() call.
    """

    name = "element_recognition"
    semantics = "element_recognition"
    single_value = True

    pre = StandardPre[ElementNotation](empty_guard=True)
    matchers = (_Z_MATCHER, _SYMBOL_MATCHER, _NAME_MATCHER)

    def recognize(self, text: str) -> list[RecognitionMatch[ElementNotation]]:
        from paxman.core.grammar.engine_loop import run_matchers

        matches = run_matchers(text, [self])
        # Longer-wins dedup within grammar (mirrors _dedup_spans / SIUnit):
        # the label branch span ("element 26") is longer than any lexicon span
        # it could overlap; digits-only is never a lexicon key, so overlap is
        # not expected — the dedup is a determinism safety net.
        ordered = sorted(matches, key=lambda m: (m.start, -(m.end - m.start)))
        kept: list[RecognitionMatch[ElementNotation]] = []
        for m in ordered:
            if any(o.start <= m.start and m.end <= o.end for o in kept):
                continue
            kept.append(m)
        kept.sort(key=lambda m: (m.start, m.end))
        return kept
```

*Notes on fidelity vs shipped precedent:* the matcher-tuple + `run_matchers` delegation + longer-wins dedup is copied from SIUnit `symbol_recognition.py` verbatim; `BoundarySpec.WORD` and the multi-fragment `left`/`right` constructor style follow `boundary_spec.py` presets (`ISBN10_LEAD` uses `left=("\\d", "\\d[ -]")` — the isotope guard `right=("\\w", "-\\d")` is the same mechanism); `suppressible` flows to the engine loop's common-word check verbatim (`engine_loop.py` skips the matcher hit when `contract.suppress_common_words` and `matcher.suppressible` and the hit lowercased is in `COMMON_WORDS`); the fused-label separator class and span-includes-label decision follow BIC/ISSN/MAC. **Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a concrete element — canonical+lowercase symbols → `_SYMBOL_MATCHER` keys; names/alternative spellings → `_NAME_MATCHER` keys; the three label forms → `_Z_PATTERN` alternation; every DEFER/REJECT row names the mechanism that declined it (all-caps keys absent → D3; isotope suffix → right guard → D6; placeholders/placeholders-3-letter/bare numbers → no keys; `sulphur`/`fE` → not keys, no autocorrection). One wiring detail is deliberately flagged `NotImplementedError`: the exact group-span projection seam for the labeled-number emit must be copied from the kernel's emit-validation contract at plan time — the research report pins the *design*, not an unverified signature.

**One grammar, not N:** symbol and name keys live in one grammar so a mention cluster containing both (`Iron (Fe)`) is intra-grammar — the engine's single-value clustering coalesces same-value mentions without cross-grammar spurious `AMBIGUOUS` (the MacAddress one-grammar-owns-both-lengths argument, applied to name-vs-symbol co-reference). A second grammar would preserve cross-grammar containment and manufacture ambiguity out of co-reference.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)

- The grammar emits span-bearing `RecognitionMatch`s, half-open `[start, end)`, `raw_text == text[start:end]`; the fused-label span includes `element`/`atomic number`/`Z` and the separator run.
- The engine owns within-grammar containment dedup (longer wins, `_dedup_spans`) and total recognition ordering; the grammar-level dedup above mirrors SIUnit for byte-identical parity.
- Candidate dedup is by `(value, recognition_rule, validation_rule)` after validation; identical values from the symbol and name branches of one mention-cluster coalesce to one resolution value.

### 4.4 Guard boundaries against sibling grammars

| Grammar family | Chars | Start guard | End guard |
|----------------|-------|-------------|-----------|
| Element symbols | 1–2 ASCII letters (`Fe`/`fe` keys) | `(?<!\w)` via `BoundarySpec.WORD` left | `(?!\w)` plus `-\d` isotope guard via `right=("\\w", "-\\d")` |
| Element names | 3–13 ASCII letters (lexicon keys only) | word-only left (no `eelement` glue) | word-only right (no `irony` claim — `iron` inside `irony` is glued `\w` → rejected) |
| Atomic-number label | `element`/`atomic number`/`Z` + `[\s:=]+` + 1–3 digits | word-only left (no `Zzz=26`); label word-anchored | `(?![0-9])` right digit guard |
| SIUnit symbols (sibling capability) | `K`, `C`, `s`, `m`, `g`, `Pa`, … | Cross-capability, not cross-grammar: `K` is kelvin in SIUnit and potassium in Element — resolved by the caller's capability choice, not by guards; document, never guess |
| Date (sibling) | `May`, month names | No lexical overlap with element keys; no guard needed |

Within the element composition there is exactly one grammar, so the guard table's job is to keep the three matchers out of each other's way and out of prose: lexicon keys are disjoint (symbols ≤2 letters vs names ≥3 letters), and the label branch requires an explicit separator after `element`/`Z`.

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

`semantics = "element_recognition"` — a single affinity id for all three matchers, matching the one-grammar design. Both rules declare `target_semantics = frozenset({"element_recognition"})`; `_validate_affinity` fails fast if a community grammar's semantics were referenced without being composed. A future community extension (all-caps lexicon, Latin-name aliases, `at. no.` labels) declares its own semantics id and is opted in via `extra_grammars` (Contract `extra_grammars` tuple; engine appends after shipped grammars).

### 4.6 `single_value` — one mention per call vs batch processing

Recommendation: `single_value = True` (every shipped single-entity capability). Free-text paragraphs (`The steel contains Fe, Cr and Ni`) are the segmentation recipe's job: split, then canonicalize per mention. A community batch variant (`single_value = False`) could enumerate steel compositions later without contract changes.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | IUPAC (International Union of Pure and Applied Chemistry) — "the world authority on chemical nomenclature, terminology, standardized methods of measurement, atomic weights and many other critically evaluated data" (IUPAC press release, 28 Nov 2016) |
| Naming authority | IUPAC Inorganic Chemistry Division (Division II); historically the Commission on Nomenclature of Inorganic Chemistry (CNIC) — since 1947 only CNIC/Division II recommends names to the IUPAC Council (Red Book IR-3.1, verbatim) |
| Discovery validation | Joint IUPAC/IUPAP Working Party (JWP); criteria from the 1991 Transfermium Working Group (PAC 63, 879-886) revised by the 2018 JWG provisional report "On the discovery of new elements" (Hofmann et al.) |
| Spec name | Nomenclature of Inorganic Chemistry — IUPAC Recommendations 2005 ("Red Book"; Connelly, Damhus, Hartshorn, Hutton, RSC, ISBN 0-85404-438-8) — Chapter IR-3 "Elements", §IR-3.1 "Names and symbols of atoms", §IR-3.2 "Indication of mass, charge and atomic number using indexes", Table I (names/symbols/Z, elements 1–111) and Table II (temporary systematic names/symbols) |
| Current registry | IUPAC Periodic Table of the Elements, latest release dated **4 May 2022** (PDF: `IUPAC_Periodic_Table-04May22_CRA.pdf`), embedding CIAAW Standard Atomic Weights 2021 (PAC, AOP 4 May 2022, doi 10.1515/pac-2019-0603); **118 elements, Z 1–118**; none added since 28 Nov 2016 |
| Check character system | **None.** Element designations carry no checksum — proved by absence across the Red Book (IR-3.1 defines names/symbols with no check machinery), the IUPAC periodic table, and all six ecosystem libraries (pure table membership). Structure + registry membership is all there is (the BIC model) |
| Alternative spellings authority | Red Book Table I footnotes a & c: `aluminum` and `cesium` are "commonly used" alternatives to the IUPAC `aluminium` and `caesium` |
| Related specs | Green Book (quantities/symbols — `Z` notation); CIAAW atomic-weight reports (deferred); Brief Guide to the Nomenclature of Inorganic Chemistry (PAC 87, 1039-1049, doi 10.1515/pac-2015-0505) |

**Structure (Red Book IR-3.1, verbatim):** "For use in chemical formulae, each atom is represented by a unique symbol in upright type as shown in Table I. In addition, the symbols D and T may be used for the hydrogen isotopes of mass numbers two and three, respectively" — 118 unique symbols, each 1–2 letters (first uppercase, second lowercase per every symbol in Table I and the 04May22 table). IR-3.2: "The mass, charge and atomic number of a nuclide are indicated by means of three indexes… left upper index = mass number; left lower index = atomic number" — the authority for treating `56Fe`/`Fe-56` as *nuclide* notation, not element mention. IR-3.1.1 (systematic temporary nomenclature, roots `nil/un/bi/tri/quad/pent/hex/sept/oct/enn` + `ium`, three-letter symbols): "Such elements may be referred to by their atomic numbers, as in 'element 120' for example" — the authority for the `element N` recognition branch; Table II footnote b: "One may also write, for example, 'element 112'."

**Lineage table (naming corpus):**

| Edition / instrument | Date | Status | Note |
|----------------------|------|--------|------|
| PAC 51(2) 381-384 — systematic nomenclature & three-letter symbols for elements Z > 100 | 1979 | active (mechanism; dormant — all Z ≤ 118 named) | Source of `Uut`-style designators; REJECT class today |
| Red Book (2nd ed., 1970 rules) | 1971 | superseded | Table I then 1–103 |
| Red Book 1990 (Leigh, Blackwell) | 1990 | superseded | Settled `sulfur` spelling; 1–109 era |
| PAC 66(12) 2419-2421 / PAC 69(12) 2471-2473 — transfermium names | 1994 / 1997 | superseded by Red Book 2005 absorption | 101–109 final names after the transfermium dispute |
| PAC 75(10) 1613-1615 — darmstadtium | 2003 | absorbed | Z 110 |
| PAC 76(12) 2101-2103 — roentgenium | 2004 | absorbed | Z 111 (Red Book 2005's table end) |
| **Red Book 2005 (Connelly et al., RSC)** | **2005** | **active (current)** | **IR-3.1 + Table I (1–111) + Table II; Rule 1's publication** |
| PAC 82(3) 753-755 — copernicium | 2010 | absorbed | Z 112 |
| PAC 84(7) 1669-1672 — flerovium, livermorium | 2012 | absorbed | Z 114, 116 |
| PAC 88(4) 401-405 — naming procedure revision (group 17 `-ine`, group 18 `-on`) | 2016 | active (procedure) | With PAC 74(5) 787-791 (2002): naming rules |
| PAC 88(1-2) 139-153 / 155-160 — discovery of 113/115/117/118 | 2016 | absorbed | JWP priority assignments |
| PAC 88(9) 1225-1229 — names/symbols 113, 115, 117, 118 (nihonium, moscovium, tennessine, oganesson) | 2016 | absorbed | Completed period 7 on 28 Nov 2016 |
| IUPAC Periodic Table of the Elements — **04 May 2022 release** | 2022 | **active (current)** | **118 elements; Rule 2's registry snapshot** |
| CIAAW Standard Atomic Weights 2021 (PAC 94, doi 10.1515/pac-2019-0603; Gd/Lu/Zr revised 2024) | 2022/2024 | active (informative) | Deferred: atomic weights are nuclear data, not designations |

**Citation Details Table (for Provenance):**

| authority | specification_name | version | reference_url | lifecycle | publication_year | kind |
|-----------|--------------------|---------|---------------|-----------|------------------|------|
| IUPAC | Nomenclature of Inorganic Chemistry (IUPAC Recommendations 2005), Chapter IR-3 | 2005 | https://iupac.qmul.ac.uk/RedBook2005.pdf | active | 2005 | specification |
| IUPAC | IUPAC Periodic Table of the Elements | 04 May 2022 | https://iupac.org/wp-content/uploads/2022/07/IUPAC_Periodic_Table-04May22_CRA.pdf | active | 2022 | registry |
| IUPAC | Pure Appl. Chem. 88(9) 1225-1229 — Names and symbols of the elements with atomic numbers 113, 115, 117 and 118 | 2016 | https://doi.org/10.1515/pac-2016-0501 | absorbed | 2016 | specification (fused into Rule 1 citation) |
| CIAAW | Standard Atomic Weights of the Elements 2021 | 2021 (revisions 2024) | https://ciaaw.org/atomic-weights.htm | active | 2022 | registry (deferred — no v1 rule) |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|----------------|-------------------|
| `rules/iupac_red_book_2005.py` | `authority="IUPAC"`, `specification_name="Nomenclature of Inorganic Chemistry (IUPAC Recommendations 2005), Chapter IR-3"`, `kind="specification"`, `reference_url="https://iupac.qmul.ac.uk/RedBook2005.pdf"`, `version="2005"`, `lifecycle="active"`, `publication_year=2005` | `SectionIR31NamesAndSymbols` (name `"Section IR-3.1-names-and-symbols"`, strategy `LOOKUP_TABLE`) | Symbol tokens ∈ 118-symbol set; name tokens ∈ name map (IUPAC names + `aluminum`/`cesium` alternatives per Table I footnotes a/c); normalizes both to the canonical symbol. Citation string scopes the table "as extended by the IUPAC recommendations for elements 112 (2010), 114/116 (2012), 113/115/117/118 (2016)" — the Currency "as amended" pattern, since Table I stops at 111 |
| `rules/iupac_periodic_table_ed2022.py` | `authority="IUPAC"`, `specification_name="IUPAC Periodic Table of the Elements"`, `kind="registry"`, `reference_url="https://iupac.org/wp-content/uploads/2022/07/IUPAC_Periodic_Table-04May22_CRA.pdf"`, `version="04 May 2022"`, `lifecycle="active"`, `publication_year=2022` | `SectionPtoeRegistry` (name `"Section PTOE-element-registry"`, strategy `LOOKUP_TABLE`) | `atomic_number` tokens: Z integer in 1–118, resolves Z → canonical symbol via the registry snapshot. Always active — the 118-entry set is tiny, closed, and free of per-row cost |

Each `Rule[ElementNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`): `name`, `strategy`, `provenance` (= the module `PUBLICATION`), `citation`, `target_semantics` (frozenset), `requires_features` (frozenset).

### 5.3 What each rule does vs does not own

- `matches()` validates strictly against the shipped tables and **never raises**; contract misconfigurations are caught in `CapabilityContract.__post_init__` / `_filter_rules`, not in rule bodies.
- `normalize()` returns the canonical IUPAC symbol (proper case) for all three shapes; it never reads `output_format` (CI source-scan enforced), and both rules normalize the same input to the same value so candidate coalescing is value-identical.
- Both rules use `RuleStrategy.LOOKUP_TABLE` — membership + mapping against module-level tables (`rules/data/periodic_table_ed2022.py`). No `PARSER` rule is needed: there is no checksum to compute and no date arithmetic; the only "parse" work (case folding, digit normalization) is syntax and lives in the grammar's emit functions.
- Rules do **not** own: symbol case convention (grammar key sets), label recognition (grammar), atomic-weight/nuclide data (out of scope), presentation (capability seam).

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Whether registry validation is always-active vs gated: **always-active** for both rules. The registry is 118 rows, immutable in practice (last change 2016; next change gated on a confirmed discovery + a 5-month public review + Council approval — years of notice), and carries none of the staleness/cost concerns that gated SWIFT/ISSN directories have. A CIAAW atomic-weight layer would be the only plausible `include_*` candidate (per-row floating intervals, periodic revisions) — deferred (§13 D9); per the two-loci rule, a future gated atomic-weight rule would be `requires_features={"include_atomic_weights"}` on the rule (dropped rule → `INVALID` avoided by it being additive, never load-bearing) — the element's *validity* never depends on it.

### 5.5 Assignment / registration authority & Registry content

Elements are not "registered" like BICs — they are **discovered, validated, and named**: (1) a laboratory claim is assessed by the joint IUPAC/IUPAP JWP against the 1991/2018 discovery criteria; (2) priority is assigned; (3) the acknowledged discoverers propose a name (allowed sources: mythological concept/character including astronomical objects, mineral, place/region, property, scientist) and symbol; (4) the Inorganic Chemistry Division reviews; (5) a 5-month public review runs; (6) the IUPAC Council/ratification formalizes, published in Pure and Applied Chemistry (procedure: PAC 74(5) 787-791 (2002) as revised by PAC 88(4) 401-405 (2016)). Only the discoverers may propose (2016 release: "under the current guidelines only the discoverers have the right to propose names and symbols"). Record content per element (periodic table 04May22 cell): atomic number, symbol, name, standard atomic weight (interval or uncertainty) or bracketed mass number of the longest-lived nuclide. Cadence: the table PDF is reissued with CIAAW atomic-weight revisions (2018, 2021, 2022-05-04); **names/symbols are added only on confirmed discovery** — the 118-entry set is the registry Paxman snapshots. Placeholder designations exist only for unnamed elements (Table II) and are retired the moment a name is assigned — hence their REJECT disposition.

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract MUST inherit `CapabilityContract` (never `Contract` directly). `@dataclass(frozen=True)` **without** slots (base `__post_init__` incompatibility).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ElementContract(CapabilityContract):
    """User-facing contract for the element capability.

    ``symbol`` (proper-case IUPAC symbol) is the canonical default; the
    offered formats are presentation-only re-renderings of the
    rule-normalized symbol (``name`` is the Red Book Table I lowercase
    common noun; ``atomic_number`` is the registry Z). No grammar-toggle
    fields: the single shipped grammar is always active (base
    ``active_grammars is None``). ``suppress_common_words`` stays the base
    default (False) — every shipped capability does (§13 D5).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "symbol"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"name", "atomic_number"}
    )

    capability_name: str = field(default="element", init=False)
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string, excluded from `OFFERED_OUTPUT_FORMATS`; resolution via the shared `resolve_output_format` policy (`None`/`"default"`/`"symbol"` → `"symbol"`; offered values → themselves; anything else → `ContractError`).
- `create_contract()` keeps the unanimous common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`) keyword-only; no capability-specific fields in v1.
- Presentational-only invariant: `output_format` never appears in any `rules/` module.

For element, the offered formats model the interchange forms:

| output_format | value example | Meaning |
|---------------|---------------|---------|
| `symbol` (default) | `Fe` | IUPAC symbol, proper case — the wire/canonical form (identity) |
| `name` | `iron` | Red Book Table I English common noun, lowercase (IUPAC display convention) |
| `atomic_number` | `26` | Registry Z as decimal string (CIAAW/periodic-table column) |

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    SYMBOL_TO_NAME,
    SYMBOL_TO_Z,
)


class ElementCapability(Capability[ElementNotation]):
    name = "element"  # lowercase registry name — MILESTONE "Chemical element"

    def get_grammars(self) -> list[Grammar[ElementNotation]]:
        return [ElementRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ElementNotation]]:
        return [SectionIR31NamesAndSymbols(), SectionPtoeRegistry()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: tuple[str, ...] | Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> ElementContract: ...

    def format_value(
        self, value: str, output_format: str | None, notation: ElementNotation
    ) -> str:
        if output_format == "name":
            return SYMBOL_TO_NAME[value]
        if output_format == "atomic_number":
            return str(SYMBOL_TO_Z[value])
        return value  # "symbol" default is identity — normalize() returns the symbol
```

Registration via `tools/new_capability.py` (§10.1); export wiring adds `"Element"` between `"Email"` and `"IBAN"` in `paxman/capabilities/__init__.py.__all__` (scaffolder does this automatically in sorted position).

---

## 7. Validation — Structure, Registry

### 7.1 Level 1 designation form (Red Book IR-3.1), Level 2 registry membership (04May22 snapshot), Level 3 — none

**Level 1 — designation form.** Enforced by the grammar's key sets and emit folds rather than a PARSER rule: symbols are 1–2 letters in IUPAC case convention (keys `Fe`/`fe` — `FE`/`fE` cannot match); names are English element names (case-folded); the labeled designations carry 1–3 digits after an explicit separator. The Red Book's structural contribution is the *sanction* of each surface: symbols "in upright type as shown in Table I", names per Table I (with the footnoted alternative spellings), atomic-number designations per IR-3.1.1/Table II footnote b.

**Level 2 — registry membership.** `SectionIR31NamesAndSymbols` (symbol/name shapes) and `SectionPtoeRegistry` (atomic-number shape) are exact `LOOKUP_TABLE` lookups over `rules/data/periodic_table_ed2022.py`:

```python
SYMBOLS: frozenset[str]               # 118 canonical symbols, "H" .. "Og"
NAME_TO_SYMBOL: dict[str, str]        # 118 IUPAC names + "aluminum", "cesium" (footnotes a/c)
Z_TO_SYMBOL: dict[int, str]           # 1 -> "H" .. 118 -> "Og"
SYMBOL_TO_NAME: dict[str, str]        # presentation seam (format_value "name")
SYMBOL_TO_Z: dict[str, int]           # presentation seam (format_value "atomic_number")
```

`matches()` for the symbol/name rule: `shape in {"symbol", "name"}` and `token in SYMBOLS` / `NAME_TO_SYMBOL` respectively; for the registry rule: `shape == "atomic_number"`, `int(token)` in 1–118 (reject `element 119`, `Z = 0`, `Z = 300`). `normalize()` maps to the canonical symbol in both.

**Level 3 — directory membership: not applicable.** Unlike ISBN (Range Message allocated registrants), ISSN (Register records), or BIC (SWIFT directory), the element registry has no liveness dimension — an element designation is valid **iff** it is in the 118-entry table; there is no valid-but-unissued state to model, and no registry-gated layer. The only temporal axis is forward: a future Z = 119 extends `Z_TO_SYMBOL` and the symbol/name key sets when IUPAC acts (determinism by snapshot; Provenance `version="04 May 2022"` records the basis).

### 7.2 What makes an element "valid" vs "shape-valid" vs "named"

- **shape-valid** — a token that looks like a designation (e.g. `Xx`, `element 300`): grammar keys/label regex may or may not claim it; claiming without membership is `INVALID` (label branch) and non-claiming is `MISSING` (lexicon branches) — the deliberate asymmetry of §9.
- **valid** — member of the registry: correct shape **and** in the 118-entry table (the only validity level the domain has; there is no per-country/per-LOU refinement).
- **named** — every member of the current table is named (none has carried a placeholder since 2016); the valid-vs-named distinction is historical only (pre-2016 tables had placeholder rows) and is recorded in the lineage table, not in the rule model.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase symbol `fe` | SUCCESS → `Fe` | lowercase lexicon key; emit folds to IUPAC case |
| 2 | Canonical symbol `Fe` | SUCCESS → `Fe` | canonical key; identity fold |
| 3 | ALL-CAPS symbol `FE` | MISSING | deliberate D3 cut: all-caps keys collide with caps prose (`NO`, `IN`); community extension path |
| 4 | Inverted case `fE` | MISSING | never a sanctioned spelling; typo class, no autocorrection |
| 5 | Name `Iron` / `iron` / `IRON` | SUCCESS → `Fe` | name keys case-folded; Red Book Table I authority |
| 6 | Alternative spelling `aluminum` / `caesium` | SUCCESS → `Al` / `Cs` | Red Book Table I footnotes a & c; alias keys |
| 7 | Label `element 26` | SUCCESS → `Fe`, span includes label | fused-label branch; Red Book IR-3.1.1 sanction |
| 8 | Label `Z = 26` / `Z=26` | SUCCESS → `Fe` | `[\s:=]+` separator class; notation digits-only |
| 9 | Label `atomic number 118` | SUCCESS → `Og` | multi-word label alternation |
| 10 | Bare `26` | MISSING | no claim without a label (any integer would claim otherwise) |
| 11 | Out-of-range `element 119`, `Z = 0`, `Z = 300` | INVALID | label branch claims (distinctive shape), registry rule rejects — correct INVALID, not MISSING |
| 12 | `element 1000` | MISSING | 4 digits exceed the 1–3-digit branch → no claim (vs row 11's 3-digit INVALID) |
| 13 | Invalid symbol `Xx`, `Jq`, `Qq` | MISSING | not lexicon keys; J and Q appear in no IUPAC symbol; lexicon design keeps prose free of INVALID noise |
| 14 | Prose collision, flag off: `in`, `no`, `at` | SUCCESS → `In`, `No`, `At` | default `suppress_common_words=False` preserves byte-identical shipped behavior; documented risk (D5) |
| 15 | Prose collision, flag on: same input | MISSING | `suppressible=True` matchers + `COMMON_WORDS` (13 symbol words covered); provenance-neutral suppression |
| 16 | Pronoun `I` (`I am here`) | SUCCESS → `I` (iodine) | top residual false positive even flag-on (`i` not in COMMON_WORDS); single mention → coalesces; documented, not hidden |
| 17 | Formula context `Fe2O3`, `NaCl`, `CO2` | MISSING | word guard: symbol glued to digit/letter never claims |
| 18 | Isotope suffix `Fe-56` / left-index `56Fe` | MISSING | isotope right-guard (`-\d`) / left-glue guard; nuclide ≠ element (D6) |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| `Fe`, `iron`, `element 26`, `Z = 26` | SUCCESS → `Fe` | recognized + registry member; one canonical via authority table |
| `IRON`, `aluminum`, `element 026` | SUCCESS → `Fe` (as `Al`) | case/zero/spelling variants fold to the same canonical — presentation-only dedup |
| `Xx` (shape-valid, not a key) | MISSING | lexicon design: non-members are never claimed (no INVALID noise in prose) |
| `element 119` / `Z = 300` | INVALID | label branch claims the distinctive shape; registry rule rejects (claimed-but-invalid is the correct INVALID signal) |
| `hello world` | MISSING | no grammar claimed any span |
| `Fe and Cu` | MultipleMentionsError | two distinct mentions, distinct values; single_value=True; segmentation recipe |
| `Iron (Fe)` | SUCCESS → `Fe` | co-reference coalesces (one value across the mention cluster) |
| `in` (flag on) / `FE` (D3) / `Fe-56` (D6) / `ununtrium` | MISSING | suppressed / key-set cuts / isotope guard / retired placeholder |
| `element 26 (iron)` | SUCCESS → `Fe` | two mentions, one canonical value; span excludes parenthetical |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py Element --name element \
    --authority "IUPAC" \
    --spec-name "Nomenclature of Inorganic Chemistry (IUPAC Recommendations 2005)" \
    --spec-url "https://iupac.qmul.ac.uk/RedBook2005.pdf" \
    --publication-year 2005
```

Creates 13 files + one edit: `paxman/capabilities/Element/{__init__,notation,contract,capability}.py`, `grammar/__init__.py`, `grammar/element_recognition.py`, `rules/__init__.py`, `rules/iupac_ed2005.py`, four test stubs under `tests/capabilities/element/`, and the `paxman/capabilities/__init__.py` wiring (`_LAZY`, `TYPE_CHECKING`, `__all__` — `"Element"` lands between `"Email"` and `"IBAN"`). TODO(scaffold) markers guide replacement.

> Note: the scaffolder's single `--spec-name` covers one provenance. After scaffolding: rename the rule file to `iupac_red_book_2005.py`, replace the placeholder `Section 1-overview` REGEX rule with `SectionIR31NamesAndSymbols` (LOOKUP_TABLE), and add the second rule file `iupac_periodic_table_ed2022.py` + `rules/data/periodic_table_ed2022.py` manually — the Currency two-view data-module and Country `rules/data/iso_3166_ed2024.py` are the layout precedents.

### 10.2 Contract & grammar wiring

- `get_grammars()` returns `[ElementRecognitionGrammar()]`; `active_grammars` omitted (base `None` — no feature gating in v1); grammar `name`/`semantics` both `"element_recognition"`; `single_value = True`.
- `get_rules()` returns `[SectionIR31NamesAndSymbols(), SectionPtoeRegistry()]`; both `target_semantics = frozenset({"element_recognition"})`; `_validate_affinity` passes (semantics composed).
- Matcher tuple order `(_Z_MATCHER, _SYMBOL_MATCHER, _NAME_MATCHER)` — the shape-distinct branches are disjoint, so order is presentation only; keep it fixed for determinism.

### 10.3 Cross-cutting invariants (fail review if violated)

- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source.
- No cross-capability imports; the capability imports only from `paxman.core` (import-linter enforced).
- No `output_format` token in any `paxman/capabilities/Element/rules/` module (CI source-scan).
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` **without** slots contract; `target_semantics`/`requires_features` as `frozenset`.
- Deterministic by construction: same input + contract + registry snapshot (04 May 2022 tables) → same output; no clock, no environment-dependent ordering, no fuzzy matching (`sulphur` ≠ `sulfur` is a decision, not a typo-tolerance).
- Data modules are plain module-level tables (`rules/data/`), separated from rule logic; grammar keys live in `grammar/data/` — never the reverse (authority data in grammar/data is the flagged anti-pattern).

---

## 11. Recommended File Layout (mirrors ISSN/IBAN/BIC and the Country data-module pattern)

```
paxman/capabilities/Element/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   ├── element_recognition.py          # PipelineGrammar: matchers tuple (Z regex, symbol lex, name lex)
│   └── data/
│       └── element_keys.py             # SYMBOL_KEYS (236), NAME_KEYS (476+), label pattern — grammar-owned keys only
└── rules/
    ├── __init__.py
    ├── iupac_red_book_2005.py           # PUBLICATION (specification, 2005) + SectionIR31NamesAndSymbols
    ├── iupac_periodic_table_ed2022.py   # PUBLICATION (registry, 04 May 2022) + SectionPtoeRegistry
    └── data/
        └── periodic_table_ed2022.py     # SYMBOLS, NAME_TO_SYMBOL, Z_TO_SYMBOL, SYMBOL_TO_NAME, SYMBOL_TO_Z
```

Per-registry data module shape (parallel to Country `rules/data/iso_3166_ed2024.py` and Language `rules/data/iso_639_1.py`):

```python
# rules/data/periodic_table_ed2022.py
"""IUPAC Periodic Table of the Elements — registry snapshot 04 May 2022.

Names/symbols per Table I of the Red Book 2005 (elements 1-111) as extended
by the IUPAC recommendations for elements 112 (2010), 114/116 (2012), and
113/115/117/118 (2016). Alternative spellings per Red Book Table I footnotes
a ("aluminum") and c ("cesium"). 118 elements; none added since 2016-11-28.
"""

SYMBOLS: frozenset[str] = frozenset({"H", "He", ..., "Og"})          # 118
NAME_TO_SYMBOL: dict[str, str] = {"hydrogen": "H", ..., "cesium": "Cs", "aluminum": "Al", ...}
Z_TO_SYMBOL: dict[int, str] = {1: "H", ..., 118: "Og"}
SYMBOL_TO_NAME: dict[str, str] = {v: k for k, v in NAME_TO_SYMBOL.items() if k == v.lower() or ...}
SYMBOL_TO_Z: dict[str, int] = {v: k for k, v in Z_TO_SYMBOL.items()}
```

(The inverse maps are materialized explicitly rather than comprehension-derived at import so the file stays a plain data table per the project's data-module convention; the exact inverse-filtering for the two alias spellings — keeping the IUPAC name as the canonical `name` rendering — is a plan-phase detail. The 118-row body is hand-authored data, not a generated artifact: the set changes only when IUPAC names a new element, at which point a `tools/regenerate_element_data.py` fed by a periodic-table snapshot JSON would be the Currency-pattern option — §13 D10.)

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md §10 and the ISSN/BIC/MAC reports)

- **Grammar tests** (`tests/capabilities/element/test_grammar.py`): one positive vector per §2.1 RECOGNIZE form — canonical symbol, lowercase symbol, 1-letter symbol, name ×3 cases, both alternative spellings, `element N` (space/`=`/`:`), `Z = N`, `atomic number N`; multiple matches; incompatible formats ignored; empty/whitespace-only → empty; span invariants (half-open, `raw_text == text[start:end]`, label inside span for label branch); name/semantics conventions; `single_value` attr; boundary negatives — `irony` (name glue), `Fe2O3`/`NaCl` (right glue), `56Fe` (left glue), `Fe-56` (isotope guard), `element26` (no separator), `K` (non-ASCII), `FE`/`fE` (non-keys), placeholder `Uut`/`ununtrium`; matcher attrs (`suppressible=True`, key-set size asserts 236 / 476+).
- **Rule tests** (`test_rules.py`): symbol/name rule — valid members, invalid non-members (`Xx`, `D`, `T`), `normalize` exact canonical symbol for case/spelling variants, provenance attributes (authority IUPAC, year 2005, kind `specification`, lifecycle `active`), name/strategy conventions (`Section IR-3.1-names-and-symbols`, `LOOKUP_TABLE`); registry rule — Z 1–118 membership including 1/118 boundaries, out-of-range rejection (`0`, `119`, `300`), non-integer digits, `normalize` Z→symbol agreement with `SYMBOL_TO_Z`, provenance kind `registry`, version `04 May 2022`; consistency — every `SYMBOLS` member resolves from all three shapes to the same canonical value.
- **Capability tests** (`test_capability.py`): notation frozen/hashable/slots; wiring counts (1 grammar, 2 rules); name conventions; `format_value` round-trips (`Fe`→`iron`→`Fe`, `Fe`→`26`→`Fe`); `create_contract` defaults and `ContractError` on unknown format; registry name `element`.
- **Integration** (`tests/integration/`): `SUCCESS`/`MISSING`/`INVALID` per §9 rows; `MultipleMentionsError` for `Fe and Cu`; co-reference coalescing for `Iron (Fe)`; suppression on/off for the 13 COMMON_WORDS symbols (parametrized over `suppress_common_words`); `_clean_registry` autouse fixture; capability registered inside test methods; determinism/`VersionStamp`; span-bearing candidate assertions.
- **Property tests** (hypothesis): sampled symbol/name/Z from the registry tables → canonicalizes to itself; random ASCII strings → `MISSING` with high probability (lexicon design) and `INVALID` only via the label branch; `format_value` round-trip identity across all three formats; case-variant equivalence (`fe`/`Fe`/`iron`/`IRON`/`element 26` → same value).
- **Presentation purity:** output_format source scan over `paxman/capabilities/Element/rules/` (CI).
- **Real vectors:** the MILESTONE row-22 examples verbatim — `"Iron" → "Fe"`, `"fe" → "Fe"`, `"Gold" → "Au"`, `"Al" → "Al"`, `"Carbon" → "C"` — plus `element 118 → Og`, `Z = 92 → U`, `atomic number 79 → Au`.

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT — `symbol` vs `name` vs `atomic_number` | `symbol` (proper case), offer `{"name", "atomic_number"}` | wire-canonical like MAC colon/Currency code; name is the human display (lowercase common noun per Table I); MILESTONE examples all canonicalize to symbols |
| 2 | Identity: `Element`/`element` vs `ChemicalElement`/`chemical_element` | `Element` / `element` | domain vocabulary ("chemical element" is the MILESTONE label; the value is an *element*); matches terse shipped names (`URL`, `IP`, `ISBN`); scaffolder accepts both — shorter wins |
| 3 | ALL-CAPS two-letter symbols (`FE`, `NO`, `IN`) | DEFER — not in v1 keys; community `extra_grammars` case-insensitive lexicon | all-caps prose is acronym territory (`NO SMOKING`, `IN CASE OF FIRE`); only chempy folds caps; MILESTONE requires lowercase only |
| 4 | Single-letter symbols and the `I` pronoun | RECOGNIZE all 1-letter symbols; document the `I` residual; no special-casing | C/H/N/O/S/P/K/U/W/Y/V/B/F/I are core chemistry surface; suppressing `I` would break legitimate iodine mentions; single_value + coalescing keep the noise bounded |
| 5 | `suppress_common_words` default for element | Keep base default `False`; ship `suppressible=True` matchers; recommend `True` in docs for free-text callers | every shipped capability defaults `False` (byte-identical invariant, common_words.py header); the 67-word list already covers 13 symbol words; an element-specific word list is an `extra_grammars`/future-contract question |
| 6 | Isotope suffix (`Fe-56`, `U-235`) | Guard it out (`MISSING`) via right `-\d` boundary fragment | silently returning the bare element for a nuclide mention drops the mass number — lossy; BIC-style trailing-annotation SUCCESS would be wrong semantics here; revisit if a nuclide capability ever lands |
| 7 | `Z` label case and `at. no.` variants | `Z` label case-insensitive in v1; `at. no.`/`atomic no.` DEFER | `z = 26` lowercase is rare-but-plausible; dot-tolerant abbreviations complicate the label alternation for marginal prevalence |
| 8 | Both spellings (`caesium`/`cesium`, `aluminium`/`aluminum`) | RECOGNIZE both as alias keys; canonical `name` rendering uses the IUPAC spelling | Red Book Table I footnotes a/c sanction the alternatives; ecosystem is split (US camp vs IUPAC camp, only pymatgen maps both) — Paxman can be the library that accepts both, deterministically |
| 9 | CIAAW atomic-weight layer | Deferred; no `include_*` field in v1 contract | weights are nuclear data, revised periodically (2024 Gd/Lu/Zr), irrelevant to designation validity; if ever shipped, additive rule with `requires_features={"include_atomic_weights"}` so validity never depends on it |
| 10 | Registry data authoring | Hand-authored `rules/data/periodic_table_ed2022.py` (plain tables); optional `tools/regenerate_element_data.py` later | 118 rows change only on a new naming event; Currency's generator pattern exists if a snapshot JSON workflow is wanted |
| 11 | Labeled-number branch scope | RECOGNIZE `element N`, `atomic number N`, `Z = N` in v1 | `element N` is verbatim Red Book IR-3.1.1/Table II; `atomic number N` is the encyclopedic form; `Z = N` is the physics form (CIAAW column) — all one mechanism, all deterministic |
| 12 | Grammar shape: one grammar + 3 kernel matchers vs separate grammars | One grammar (`element_recognition`), matcher tuple | intra-grammar co-reference (`Iron (Fe)`) coalesces without cross-grammar spurious AMBIGUOUS (MacAddress one-grammar argument); SIUnit is the shipped multi-matcher precedent |

---

## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent element-vs-element ambiguity.** The Z ↔ symbol ↔ IUPAC-name mapping is a bijection over a closed 118-element set: no positional or structural ambiguity of the kind Date exhibits, no 8-vs-11 branch equivalence of the kind BIC tolerates. Two designations in one slice (`Fe and Cu`) are authorial choice — the segmentation recipe's domain — and co-referential designations (`Iron (Fe)`) resolve to one value, so neither single-slice case is genuine ambiguity.
- **Symbol-vs-name-vs-Z is presentation, not identity.** `Fe`, `iron`, and `element 26` are three surface forms of one identity; the candidate dedup and single-value clustering coalesce them to `Fe`. This mirrors the ISBN grouped-vs-compact and BIC 8-vs-11 head-office equivalences: distinct identity vs presentation is decided by the canonical-value equality, never by surface form.
- **Word collisions are recognition noise, not validation ambiguity.** `in` (indium), `no` (nobelium), `I` (iodine) in prose are false *recognition* claims — the registry cannot reject them because they are genuine members. This is the one axis where the element domain differs sharply from BIC/IBAN (whose charsets make prose claims rare): the mitigation locus is the grammar (lexicon keys + `suppressible` + `COMMON_WORDS`), not the rules — two loci, two statuses: with the flag on the hit is suppressed (→ `MISSING`, provenance-neutral); with the flag off it is `SUCCESS` (documented behavior). It is never `AMBIGUOUS`, because a competing *value* never exists for the same span.
- **Nuclide/compound context is a domain boundary, not ambiguity.** `Fe-56` is not "iron plus noise": the mass number is semantically load-bearing (Red Book IR-3.2 makes `⁵⁶₂₆Fe` a nuclide designation), so the isotope guard yields `MISSING` rather than a lossy `SUCCESS Fe`. Likewise `Fe2O3` claims nothing — a compound mention is not an element mention with residue.
- **Staleness and the eighth period are versioning, not ambiguity.** A future Z = 119/120 will extend the registry (JWG criteria → naming procedure → PAC publication); Paxman's answer is the same determinism-by-snapshot discipline as ISSN/SWIFT: `Z_TO_SYMBOL` grows, Provenance `version` records the table date, and `element 119` remains `INVALID` (correctly — not yet an IUPAC element) until the snapshot that contains it. Placeholder designations (`Uue`) are never competing values — they are retired the day a name is assigned, which is why they are REJECT-class rather than DEFER-class.

---

## 15. URL Reference (authoritative, fetched 2026-09-02)

| Claim | URL | Kind |
|-------|-----|------|
| IUPAC Periodic Table of the Elements (latest release dated 4 May 2022; CIAAW 2021 weights; naming/authority links) | https://iupac.org/what-we-do/periodic-table-of-elements/ | primary |
| IUPAC Periodic Table PDF — 04 May 2022 (registry snapshot; 118 cells fetched) | https://iupac.org/wp-content/uploads/2022/07/IUPAC_Periodic_Table-04May22_CRA.pdf | primary |
| CIAAW Standard Atomic Weights table (118 rows; IUPAC spellings; 2024 Gd/Lu/Zr revisions) | https://ciaaw.org/atomic-weights.htm | primary |
| CIAAW publications (Atomic Weights 2021 report citation, Prohaska et al., PAC 94) | https://ciaaw.org/publications.htm | primary |
| IUPAC announcement — names approved 28 Nov 2016 (Nh, Mc, Ts, Og; naming criteria; Ts/tosyl note) | https://iupac.org/iupac-announces-the-names-of-the-elements-113-115-117-and-118/ | primary |
| IUPAC announcement — provisional names 8 Jun 2016 (criteria a–e; ending rules) | https://iupac.org/iupac-is-naming-the-four-new-elements-nihonium-moscovium-tennessine-and-oganesson/ | primary |
| Naming the Elements — archives (per-element PAC citations 101–112; transfermium 1997; criteria 1991) | https://iupac.org/what-we-do/periodic-table-of-elements/naming-the-elements-archives/ | primary |
| On the discovery of new elements (2018 JWG provisional report, Hofmann et al.) | https://iupac.org/on-the-discovery-of-new-elements/ | primary |
| QMUL Inorganic Chemistry Division bibliography (Red Book editions; Brief Guide; naming PDFs) | https://iupac.qmul.ac.uk/bibliog/inorg.html | primary |
| Red Book 2005 full PDF (IR-3.1, IR-3.2, Table I incl. footnotes a/c/g–p, Table II — extracted verbatim) | https://iupac.qmul.ac.uk/RedBook2005.pdf (fetched via Internet Archive snapshot of http://old.iupac.org/publications/books/rbook/Red_Book_2005.pdf) | primary |
| Brief Guide to the Nomenclature of Inorganic Chemistry (PAC 87, 1039-1049) | https://iupac.org/wp-content/uploads/2016/07/Inorganic-Brief-Guide-V1-1.pdf | primary |
| PAC 2016 naming recommendations doi (10.1515/pac-2016-0501), naming procedure (10.1515/pac-2015-0802), atomic weights 2021 (10.1515/pac-2019-0603), systematic naming 1979 (10.1351/pac197951020381) | as cited within the fetched IUPAC/CIAAW/QMUL pages above | primary (via fetched pages) |
| pymatgen `Element` (Enum case-sensitivity; `from_name` UK→US map; `from_Z`) | https://github.com/materialsproject/pymatgen-core (src/pymatgen/core/periodic_table.py) | primary (code) |
| mendeleev `_get_element` (len≤3 heuristic; "tin" special case; case-sensitive SQL) | https://github.com/lmmentel/mendeleev (mendeleev/mendeleev.py) | primary (code) |
| periodictable (symbol attribute lookup; lowercase names; Z indexing) | https://github.com/python-periodictable/periodictable (periodictable/core.py) | primary (code) |
| chempy `atomic_number` (capitalize→lower fallback; IUPAC spellings) | https://github.com/bjodah/chempy (chempy/util/periodic.py) | primary (code) |
| RDKit `PeriodicTable` (case-sensitive symbol map; IUPAC names) | https://github.com/rdkit/rdkit (Code/GraphMol/PeriodicTable.h, atomic_data.cpp) | primary (code) |
| npm `chemical-elements` (symbol-keyed object; IUPAC spellings) | https://github.com/cheminfo/mass-tools (packages/chemical-elements) | primary (code) |
| validator.js — negative finding (no element validator in export list) | https://github.com/validatorjs/validator.js (src/index.js) | primary (code) |
| python-stdnum — negative finding (no element module) | https://github.com/arthurdejong/python-stdnum (stdnum/__init__.py) | primary (code) |
| List of chemical elements / Chemical symbol / Ununennium (118 confirmed; symbol convention; "element 119" usage) | https://en.wikipedia.org/wiki/List_of_chemical_elements, https://en.wikipedia.org/wiki/Chemical_symbol, https://en.wikipedia.org/wiki/Ununennium | secondary |
| Britannica list of chemical elements ("each element is followed by its atomic number") | https://www.britannica.com/topic/list-of-chemical-elements-2026117 | secondary |
| ISSN/IBAN/BIC/Language/MAC research precedents | docs/development/research/2026-08-21-issn-canonicalization.md … 2026-08-31-mac-address-canonicalization.md | primary (repo) |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, docs/development/MILESTONE.md | primary (repo) |
| Shipped precedent code | paxman/capabilities/SIUnit/grammar/symbol_recognition.py, paxman/capabilities/Country/grammar/name_recognition.py, paxman/core/grammar/matchers/lexicon.py, paxman/core/grammar/matchers/regex.py, paxman/core/grammar/boundary_spec.py, paxman/core/grammar/data/common_words.py, paxman/engine/orchestrator.py | primary (repo) |

---

## 16. Evidence Completion — Resolved

This report's element-specific authoritative evidence has been fetched and cited (2026-09-02):

- [x] Governing corpus: Red Book 2005 (current; RSC; ISBN 0-85404-438-8) — Chapter IR-3.1/IR-3.2 and Tables I & II extracted verbatim from the full 377-page PDF (Internet Archive snapshot of `old.iupac.org`); QMUL bibliography for edition lineage.
- [x] Registry authority: IUPAC Periodic Table of the Elements, latest release 4 May 2022 (page + PDF fetched); 118 elements confirmed; CIAAW 2021 weights embedded; CIAAW 2024 revisions noted (Gd, Lu, Zr).
- [x] Structure: symbol = 1–2 letters, IUPAC case convention, 118 symbols; name = English common noun (Table I lowercase) with sanctioned alternative spellings (footnotes a, c); D/T are hydrogen-isotope symbols, not element symbols (IR-3.1 + Table I footnote f); mass/charge/Z index positions (IR-3.2).
- [x] No checksum proved: absence across Red Book IR-3.1, the periodic table, and all six ecosystem libraries — membership is the entire criterion.
- [x] Designation sanction: "element N" verbatim in IR-3.1.1 and Table II footnote b; systematic placeholder mechanism (1979) and its retirement for all 118 named elements; naming procedure (2002/2016), criteria (1991/2018), discoverer-rights (1947 origin, 2016 restatement).
- [x] Current frontier: elements 119/120 undiscovered as of 2026-09-02 (RIKEN experiment ongoing; JINR run began May 2026, results expected Sep–Oct 2026) — the registry is closed at 118.
- [x] Ecosystem consensus table: pymatgen / mendeleev / periodictable / chempy / RDKit / npm chemical-elements case-handling and spelling camps extracted verbatim; validator.js and python-stdnum negative findings recorded.
- [x] Recognition-surface inventory complete (§2.1): 18 inventoried forms, each with evidence and an explicit RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form; the two deliberate v1 scope cuts (all-caps symbols, `at. no.` labels) are DEFER rows with named mechanisms and Open Decision entries.
- [x] Wild input shapes validated (§2.2) — 22 categories including the 13-symbol COMMON_WORDS collision analysis and the `I`-pronoun residual.
- [x] Label scope decision (§13 D11), spelling-alias decision (D8), isotope-guard decision (D6), placeholder disposition, atomic-weight deferral (D9).
- [x] Rule/publication map (§5.2), file layout (§11), and test strategy (§12) frozen for implementation, pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.

---

## Appendix — What the Shipped SIUnit, Country, Currency, MacAddress and BIC Capabilities Teach Element (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

Refer to `paxman/capabilities/SIUnit/grammar/symbol_recognition.py` (kernel multi-matcher grammar: `matchers = (_BASE_MATCHER, _COMBINATOR_MATCHER)`, `LexiconMatcher(tokens=..., boundary=..., emit=...)`, `RegexMatcher(pattern=..., boundary=...)`, `run_matchers` delegation with longer-wins dedup), `paxman/capabilities/Country/rules/iso_3166_ed2024.py` + `rules/data/iso_3166_ed2024.py` (LOOKUP_TABLE rule over a plain data module with normalized lookup views), `paxman/capabilities/Currency/rules/iso_4217_ed2015.py` (the "specification as amended" citation pattern this report reuses for the Red Book's 1–111 + 2010/2012/2016 extensions), `paxman/capabilities/MacAddress/` (single grammar, `single_value = True`, `format_value` presentation seam, deferred registry layer comment pattern), and `paxman/engine/orchestrator.py` (`_dedup_spans`, `_enforce_single_value_invariant`, `_validate_affinity`). The five architectural lessons for Element:

1. **Lexicon keys are recognition; tables are validation.** SIUnit matches case-*exact* unit tokens via `LexiconMatcher` and lets rules own canonicalization; Element matches case-*conventional* symbol keys and name keys the same way — the grammar's key set never maps to canonical values (HOW_TO §5's "the grammar's key set must never do that").
2. **One file per publication, one class per section.** `rules/iupac_red_book_2005.py` (IR-3.1) and `rules/iupac_periodic_table_ed2022.py` (registry) mirror `iso_9362_ed2022.py` + the BIC country-data split; the shared `rules/data/periodic_table_ed2022.py` is the single source of truth both rules import.
3. **No `output_format` in rules, ever.** `format_value` is the only presentation seam (MAC/BIC/ISSN verbatim pattern); the `name`/`atomic_number` renderings are value transforms over `SYMBOL_TO_NAME`/`SYMBOL_TO_Z`, never candidate identity.
4. **One grammar avoids cross-grammar spurious AMBIGUOUS.** MAC's one-grammar-owns-both-lengths argument becomes: one grammar owns symbol+name+Z so `Iron (Fe)` coalesces; the engine's `_enforce_single_value_invariant` only raises when distinct values appear across separate mention clusters.
5. **Suppression is provenance-neutral and off by default.** `COMMON_WORDS` (67 words, size-frozen) already covers 13 element symbols; `MatcherSpec.suppressible=True` + `contract.suppress_common_words` skip the hit without ever canonicalizing it (`common_words.py`: "Suppression removes a recognition; it never canonicalizes") — the exact machinery Element's prose-collision problem needs, with the default preserved for byte-identical shipped behavior.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for Chemical element (row 22). It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md`, and the kernel-era multi-matcher precedent of `docs/development/research/2026-08-31-mac-address-canonicalization.md`. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
