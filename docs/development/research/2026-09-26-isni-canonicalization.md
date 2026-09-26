# ISNI Canonicalization Research — paxman-python

**Date:** 2026-09-26
**Scope:** Primary-source survey of the ISNI standard (ISO 27729:2024, Edition 2), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `ISNI` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO 27729:2024 catalogue entry + withdrawn 2012 edition; IANA `urn:isni:` formal registration (2025-10-15); isni.org FAQ / governance / linked-data / technical-documentation pages; ORCID support page (ISNI-compatible structure, MOD 11-2 Java reference); ORCID/ISNI joint statement (2013); python-stdnum `stdnum/isni.py` + `stdnum/iso7064/mod_11_2.py`; Wikidata Property P213 (regex + formatter); shipped ORCID capability (`paxman/capabilities/ORCID/`) as verbatim precedent. Repo state: `research/isni-canonicalization @ 989f54b` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ORCID research precedent (`docs/development/research/2026-08-23-orcid-canonicalization.md`) plus the IBAN/BIC precedents (`docs/development/research/2026-08-22-iban-canonicalization.md`, `docs/development/research/2026-08-23-bic-canonicalization.md`).

---

## Executive Summary

ISNI is a **strong** fit for a Paxman capability: it has an unambiguous canonical form (**spaced quads `XXXX XXXX XXXX XXXC`**), a stable single-part standard (**ISO 27729:2024**, Edition 2, 2024-11, Published, ISO TC 46/SC 9) with the **ISNI International Agency Ltd (ISNI-IA)** as Registration Authority, a maintained authoritative directory (**16.6M assigned identities**, CC0 Linked Data dumps refreshed every 6 months), and a well-understood human-readable presentation (**spaced quads preceded by `ISNI`**, presentation-only). The domain mirrors Paxman's value proposition for ORCID/ISBN/ISSN: recognizing tolerant human surface, validating strictly against authority, returning canonical display value with provenance. **Checksum: ISO/IEC 7064 MOD 11-2 over the first 15 decimal digits, check character `0-9` or `X` (=10) — the identical algorithm already shipped and pinned for ORCID, reusable verbatim.**

Key findings that shape the design:
1. **Canonical form is the spaced display `XXXX XXXX XXXX XXXC`** (ISO 27729 §4 human-readable rule + stdnum `format()`), not compact and not hyphenated — the inverse of ORCID, whose canonical is hyphenated.
2. **One grammar** (`isni_recognition`, `PipelineGrammar` + `RegexStage`, `single_value=True`): spaced quads, compact 16-char, hyphen-tolerant, `ISNI`-labeled, `isni.org` URI, and `urn:isni:` carrier branches in a single alternation — avoids cross-grammar containment spurious AMBIGUOUS.
3. **Validation is PARSER-only in v1** (structure + MOD 11-2, full conjunction in each of two rule classes for dual provenance); no LOOKUP_TABLE registry rule — CC0 dumps lag 6 months and liveness is not validity (LEI/ISBN precedent).
4. **Hyphenated input is claimed and normalized, not rejected**: hyphens are ORCID's presentation, but stdnum strips them and validation is identical — presentation, not identity.
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file `rules/iso_27729_ed2024.py`, one PUBLICATION constant, one Rule class per section).

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---

## 1. Target User

| Persona | Why they need ISNI canonicalization | Typical context |
|---|---|---|
| Metadata librarian | Authority control: deduplicate creator/org strings against ISNI before MARC ingest | `024 $a` fields, VIAF reconciliation columns |
| Research-information manager | Affiliation strings ("MIT", "Max Planck") resolve to org ISNIs for reporting | ROR-adjacent workflows, funder compliance |
| Data engineer | Normalize mixed ISNI spellings (spaced/compact/URI) in dumps and API payloads | Wikidata P213 values, VIAF `ISNI\|…` pipes, CC0 RDF |
| Rights/provenance analyst | Cite the persistent public-identity ID behind a name with checkable provenance | Methods sections, rights clearance |

**User-visible contract:** The caller supplies raw human text (`"ISNI 0000 0001 2103 2683"`, `"0000000121032683"`, `"https://isni.org/isni/0000000121032683"`) and a contract; Paxman returns one canonical ISNI (`"0000 0001 2103 2683"`, or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ORCID ergonomics, but the canonical default is the **spaced display form**.

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form

From the Phase 1C survey (isni.org pages, IANA URN registration, MARC/LOC practice, Wikidata/VIAF dumps, stdnum strip logic):

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Spaced quads + `ISNI` prefix (canonical display) | `ISNI 0000 0001 2103 2683` | ISO 27729 §4 human-readable rule; IANA (`ISNI 0000 0001 2124 1960`); LOC MARC `024 $aISNI …$2isni` | canonical | RECOGNIZE | main pattern body + fused label |
| Spaced quads, bare | `0000 0001 2103 2683` | TAP glossary; authority boxes; stdnum `validate('0000 0001 2281 955X')` | common | RECOGNIZE | spaced branch, no label |
| Compact 16-char | `0000000121032683` | Wikipedia infobox; stdnum docstring; Wikidata P213 stored values; VIAF dumps `ISNI\|000000012146438X` | common | RECOGNIZE | compact alternation branch |
| Hyphenated 4-4-4-4 | `0000-0001-2103-2683` | ORCID presentation (not ISNI); stdnum `compact()` strips `-` | occasional (cross-confusion) | RECOGNIZE | hyphen branch, normalize to spaced |
| `isni.org` resolver URI | `https://isni.org/isni/000000012146438X` | isni.org linked-data page; Wikipedia format section | common | RECOGNIZE | optional host prefix |
| Legacy `www.` / `http` URI | `http://www.isni.org/isni/000000012146438X` | Wikipedia format section | occasional | RECOGNIZE | scheme + `www.` optional in host group |
| `urn:isni:` carrier | `urn:isni:0000000121241960` | IANA urn-formal/isni (2025-10-15) | official carrier | RECOGNIZE | optional carrier prefix (ties to offered `urn` format) |
| `ISNI:` / `ISNI -` label variants | `ISNI: 0000 0001 2103 2683` | Authority boxes (`ISNI : …`); MARC `$0ISNI …` | common | RECOGNIZE | fused label `[\s:-]+` |
| Lowercase `x` check | `0000 0001 2281 955x` | IANA ("strictly non-conformant but may treat as upper-case") | rare | RECOGNIZE | inline `(?ai:)` + `.upper()` fold |
| MARC `(isni)…` / VIAF `ISNI\|…` pipes | `(isni)1234567899999799`, `ISNI\|000000012146438X` | Wikipedia format section; VIAF dumps | rare | DEFER (no dedicated wrapper pattern; the inner compact still resolves as an embedded mention) | `extra_grammars` community extension for wrapper-aware spans |
| Bare short runs / truncated | `0000 0001 2281` (12) | stdnum `InvalidLength` | reject-shape | REJECT (MISSING) | length guard, never 12/15/17 |

A v1 that does NOT recognize hyphenated input must state that explicitly — it does not: hyphenated is claimed because validation (not separators) decides identity, and stdnum consensus strips hyphens.

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical spaced display | `ISNI 0000 0001 2103 2683` | Spec master form |
| 2 | Bare spaced quads | `0000 0001 2103 2683` | No label required |
| 3 | Compact 16-char | `0000000121032683` | DB/API dumps, Wikidata |
| 4 | Lowercase label / mixed case | `isni 0000 0001 2103 2683` | case-insensitive label, `.upper()` |
| 5 | Lowercase `x` check | `0000 0001 2281 955x` | fold to `X` (IANA tolerance) |
| 6 | Hyphenated (ORCID-style) | `0000-0001-2103-2683` | claimed, normalized to spaced |
| 7 | Double spaces / tabs between quads | `0000  0001 2103 2683` | single-space only → MISSING (bounded absorption) |
| 8 | Label with colon/hyphen | `ISNI: …`, `ISNI-…` | `[\s:-]+`, span includes label |
| 9 | Glued label | `ISNI0000000121032683` | glued-label guard → MISSING |
| 10 | Resolver URI + trailing path | `https://isni.org/isni/…/about` | host branch, span covers identifier |
| 11 | `urn:isni:` carrier | `urn:isni:0000000121241960` | carrier branch |
| 12 | Embedded in prose | `see ISNI 0000 0001 2103 2683 (Shakespeare)` | word-boundary guards, span covers mention |
| 13 | Multiple per line | two distinct ISNIs | two matches → `MultipleMentionsError` (`single_value`) |
| 14 | Quoted / bracketed | `"…"`, `[…]` | inside punctuation, guards hold |
| 15 | Wrong check digit | `…2684` (expect `3`) | grammar claims → INVALID |
| 16 | Over-long / under-long | 15- / 17-char runs | length guard → MISSING |
| 17 | X-glued runs | `X0000…`, `…2683Y` | `word_only` guards → MISSING |
| 18 | Fullwidth / homoglyph digits | `００００…` | ASCII-only `(?ai:)` → MISSING, no autocorrection |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| python-stdnum `isni.py` | `compact = clean(number, ' -').strip().upper()`; length 16; `isdigits(number[:-1])`; `mod_11_2.validate(number)`; `format = ' '.join(quads)` |
| stdnum `iso7064/mod_11_2.py` | `check = (2*check + digit) % 11` per char; valid iff `checksum == 1`; `calc_check_digit: (1 - 2*checksum) % 11`, `10 → 'X'` |
| Wikidata P213 | format regex `[0]{7}[0-9]{8}[0-9X]`; formatter `https://isni.org/isni/$1`; URL-match `^https?:\/\/(?:www\.)?isni\.org\/isni\/(\d{4})(\d{4})(\d{4})(\d{3}[\dX])$` |
| ORCID MOD 11-2 (Java, orcid.org) | `total = (total + digit) * 2` per base char; `result = (12 - total % 11) % 11`; `10 → 'X'` — identical math |
| IANA urn-formal/isni | `URN-ISNI = "urn:isni:" 15DIGIT (DIGIT / %x58)`; lowercase `x` tolerated as upper |

**Normalization contract (reuse ORCID pattern):**
```python
compact = "".join(ch for ch in raw if ch.isascii() and ch.isalnum()).upper()
spaced = f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"
# then validate: len == 16 and MOD 11-2 over first 15 digits
```

### 2.3 What input is NOT an ISNI mention
- ORCID-shaped hyphenated strings ARE claimed (same 16-digit family; each resolves under its own contract — cross-capability overlap is normal, cf. UUID/IBAN bare-32 note).
- 15-char runs, 12-char truncations, `X` mid-run — MISSING (length/charset guard, never carved).
- `ISNI|` pipes / `(isni)` MARC wrappers — no dedicated wrapper pattern in v1 (DEFERRED extension); the inner compact resolves as an embedded mention.
- Bare names ("Shakespeare") — different domain entirely (no name grammar; ISNI assigns opaque numbers).

### 2.4 Single-mention vs multi-mention input
Paxman resolves **one mention per `canonicalize()` call** (`docs/recipes/segmentation.md`, ADR-0004). Two distinct ISNIs → `MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS`.

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact plus spaced decomposition
```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISNINotation:
    """ISNI normalized display form.

    ``compact`` is the 16-char separator-free uppercase string: 15 digits
    plus a check character ``0-9`` or ``X`` (value 10).
    ``spaced`` is the ``XXXX XXXX XXXX XXXC`` canonical display (three
    ASCII spaces, ``X`` uppercase) per ISO 27729 §4 human-readable rule.
    ``uri`` is ``https://isni.org/isni/`` + ``compact`` (always https,
    even when the raw input carried ``http://`` or ``www.``).
    ``check`` is the single check character at position 16.
    ``is_uri`` is ``"true"`` when the raw span carried an ``isni.org``
    prefix or ``urn:isni:`` carrier, else ``"false"`` (string-encoded so
    every field stays ``str``).
    The grammar never computes or validates the MOD 11-2 check digit;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_CAPABILITY.md
    Step 4).
    """

    compact: str
    spaced: str
    uri: str
    check: str
    is_uri: str
```

**Considered alternative — single field `compact` only:** rejected. The decomposition is preferred because (1) ISO 27729 indexes validity by the spaced display blocks, (2) `spaced` is the canonical output the rules normalize to, (3) `uri`/`is_uri` preserve carrier provenance for the offered formats — mirroring shipped ORCID precedent field-for-field.

**Invariants the grammar enforces (before rules):**
- `compact` is exactly 16 chars `[0-9]{15}[0-9X]` uppercased from ASCII alphanumerics.
- `spaced` is `compact` regrouped `4-4-4-4` with spaces; `compact == spaced.replace(" ", "")` always.
- `check == compact[15]`; `uri == "https://isni.org/isni/" + compact`.

### 3.2 Why not carry spaces or labels in the notation
Spaces, grouping, and `ISNI:` labels have **no lexical significance** for validity — presentation is `Capability.format_value()` only. The notation stores the normalized spaced display, never the as-written separators.

### 3.3 Why `check` is not a shape discriminator literal
Free `str` validated by the MOD 11-2 PARSER rule against the computed check character, not a `Literal` — mirroring ORCID precedent (`check` is data, the rule owns the verdict).

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex (structural pattern matching)
Per HOW_TO_ADD_NEW_GRAMMAR.md, ISNI has a distinctive fixed-width 16-char shape with a small set of carrier variants, so **Regex** (staged `PipelineGrammar`) is correct — the same choice as ORCID/ISBN/ISSN, not Lexicon (no finite vocabulary).

### 4.2 Reference pattern (adapted from ORCID verbatim precedent)
ORCID precedent (`paxman/capabilities/ORCID/grammar/orcid_recognition.py`): module-scope string, `BoundaryGuard.word_only()` both sides, inline `(?ai:)` ASCII flags, optional `[\s:-]+` label, optional host carrier, glued-label guard, two-branch payload alternation, `notation_fn` building all five fields.

**Proposed ISNI pattern (single grammar, staged pipeline):**
```python
import re

from paxman.capabilities.ISNI.notation import ISNINotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Canonical spaced quads; compact 16-char; hyphen tolerance (ORCID-style
# input normalizes to spaced — separators are presentation, §3.2).
# Single spaces only between quads (bounded absorption; double spaces and
# tabs stay MISSING). (?ai:) ASCII restriction rejects fullwidth digits
# while BoundaryGuard.word_only() stays Unicode-aware (no global re.ASCII).
_ISNI_QUAD = r"(?ai:\d{4}(?: \d{4}){3}|\d{16}|\d{4}(?:-\d{4}){3})"
_ISNI_TAIL = r"(?ai:\d{3}[\dX])"
_ISNI_BODY = (
    r"(?:(?ai:ISNI)[\s:-]+)?"
    r"(?:(?ai:(?:https?://)?(?:www\.)?isni\.org/isni/))?"
    r"(?:(?ai:urn:isni:))?"
    rf"(?P<isni>{_ISNI_QUAD[:-1]}... )"  # sketch: payload + check tail
)
```

Concretely (to be pinned in the plan): payload = `(?:\d{4}(?: \d{4}){2} \d{3}[\dX] | \d{15}[\dX] | \d{4}(?:-\d{4}){2}-\d{3}[\dX])` with the label/host/carrier prefixes above, `word_only` guards both sides, and a glued-label guard `(?!(?ai:ISNI[0-9]))` mirroring ORCID's `(?!(?ai:(?:ORCID|ISNI)[0-9]))`.

```python
def _isni_notation(match: re.Match[str]) -> ISNINotation:
    raw = match.group("isni").upper()
    compact = "".join(ch for ch in raw if ch.isascii() and ch.isalnum())
    spaced = f"{compact[:4]} {compact[4:8]} {compact[8:12]} {compact[12:]}"
    return ISNINotation(
        compact=compact,
        spaced=spaced,
        uri=f"https://isni.org/isni/{compact}",
        check=compact[-1],
        is_uri="true"
        if ("isni.org" in match.group(0).lower() or "urn:isni:" in match.group(0).lower())
        else "false",
    )


class ISNIRecognitionGrammar(PipelineGrammar[ISNINotation]):
    """ISNI recognition — spaced display with compact/hyphen/URI carriers."""

    name = "isni_recognition"
    semantics = "isni_recognition"
    single_value = True
    pre = StandardPre[ISNINotation](empty_guard=True)
    regex = RegexStage[ISNINotation](
        pattern=_ISNI_PATTERN, notation_fn=_isni_notation, flags=re.IGNORECASE
    )
```

*Notes on fidelity vs ORCID:* same module-scope string discipline, same `isalnum()+upper` collapse, same `(?ai:)` ASCII guard, same fused `[\s:-]+` label (never zero-width: glued `ISNI0000…` must not fuse), same `word_only` guards. **Form-coverage traceability:** every §2.1 RECOGNIZE row maps to a pattern element above (spaced body / compact branch / hyphen branch / label group / host group / carrier group); MARC-pipe DEFER rows name `extra_grammars`; MISSING rows are bounded by the guards.

**One grammar, not two:** single `isni_recognition` with alternation branches — avoids cross-grammar containment spurious AMBIGUOUS (a spaced and compact reading of one mention would otherwise compete). No second grammar is foreseen; carrier variants are prefix groups, not separate meanings.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)
- Grammar emits span-bearing `RecognitionMatch`, half-open `[start, end)`, `raw_text == text[start:end]` (label/URI/carrier included in the span).
- `RegexStage` loops `re.finditer`, builds matches; stages never mutate text.
- Engine owns within-grammar containment dedup (longer wins) and total recognition ordering.
- Candidate dedup `(value, recognition_rule, validation_rule)` after validation.

### 4.4 Guard boundaries against sibling grammars
| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| ISNI spaced/compact | `[0-9X ]` + label/URI | `word_only` lookbehind | `word_only` lookahead |
| ORCID hyphenated | `[0-9X-]` | `word_only` | `word_only` |
| UUID bare-32 | `[0-9a-f]` | `word_only` | `word_only` |
| IBAN | `[A-Z0-9 ]` | `word_only` | `word_only` |

Hyphenated 16-digit strings are claimed by both ISNI and ORCID grammars — each resolves under its own contract (same-meaning overlap across capabilities is normal; within ISNI there is exactly one grammar so no spurious AMBIGUOUS). Compact 16-digit all-numeric strings additionally overlap UUID-bare-32/IBAN shapes; length + MOD 11-2 validation discriminate (cf. UUID/IBAN sibling note).

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)
- `semantics = "isni_recognition"` identity id; both rule classes declare `target_semantics = frozenset({"isni_recognition"})`. No coalescing (single grammar).

### 4.6 `single_value` — one mention per call vs batch processing
`single_value = True` initially (shipped precedent: ORCID/ISBN/ISSN all opt in). Two distinct ISNIs in one call raise `MultipleMentionsError`; identical values coalesce. Segmentation recipe for batches.

---

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | ISO (TC 46/SC 9 — Information and documentation) |
| Registration Authority | ISNI International Agency Ltd (ISNI-IA), UK Co. no. 07476425, c/o EDItEUR London — appointed/charged by ISO |
| Spec name | ISO 27729 — Information and documentation — International standard name identifier (ISNI) |
| Current edition | Edition 2, 2024-11, Status Published (Stage 60.60), ICS 01.140.20 |
| Check character system | ISO/IEC 7064 MOD 11-2 (Annex A); check `0-9` or `X` (=10) |
| Related specs | ISO/IEC 7064:2003 (check systems); IANA `urn:isni:` registration v1.0 (2025-10-15); ORCID structure page (compatible subset) |

**Structure (ISO 27729 §4, via iTeh preview + IANA quotation of the ISO rule):** ISNI is 16 characters: 15 decimal digits + check character (`0-9`/`X`); a "dumb" number (no embedded meaning). Human-readable presentation: preceded by letters `ISNI` + space, split into four blocks of four — EXAMPLE `ISNI 1422 4586 3573 0476`. Check via ISO/IEC 7064 MOD 11-2 (Annex A).

**Lineage table:**

| Edition | Date | Status | Note |
|---|---|---|---|
| ISO 27729:2012 (Ed. 1) | 2012-03-15 | Withdrawn (replaced) | First edition; ISNI introduced (isni.org launch 2012) |
| ISO 27729:2012/Cor 1 | 2013 | Withdrawn (folded into Ed. 2) | Technical corrigendum |
| ISO 27729:2024 (Ed. 2) | 2024-11 | Published (current) | Second edition; same 16-digit MOD 11-2 structure |

**Citation Details Table (for Provenance):**

| Publication | authority | spec_name | version | reference_url | lifecycle | publication_year | kind |
|---|---|---|---|---|---|---|---|
| ISO 27729:2024 | ISO | ISO 27729:2024 | 2024-11 | https://www.iso.org/standard/87177.html | active | 2024 | specification |

Single publication → single rule file (fused, two Rule classes — ORCID precedent). No registry publication in v1 (see §5.4).

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|----------------|-------------------|
| `rules/iso_27729_ed2024.py` | authority="ISO", specification_name="ISO 27729:2024", kind="specification", reference_url="https://www.iso.org/standard/87177.html", version="2024-11", lifecycle="active", publication_year=2024 | `Section 4-isni-structure` | 16-char structure: 15 ASCII digits + check char |
| (same file) | (same PUBLICATION) | `Section A-mod11-2-check-character` | MOD 11-2 over the first 15 decimal digits |

Each `Rule[ISNINotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`): `name`, `strategy` (both PARSER), `provenance`, `citation`, `target_semantics = frozenset({"isni_recognition"})`, `requires_features = frozenset()`.

### 5.3 What each rule does vs does not own
- `matches()` validates strictly (structure AND check digit — full conjunction in each class, so a partial validator can never let checksum-invalid input through alone), never raises, never reads `output_format` (CI purity scan).
- `normalize()` returns the spaced display `XXXX XXXX XXXX XXXC` (the default canonical), identical across both rules so dedup coalesces to one value.
- `RuleStrategy.PARSER` for both (structure + checksum computation, no table); no LOOKUP_TABLE in v1.

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)
No registry-membership rule in v1. Rationale: (1) the CC0 bulk dumps refresh every 6 months (stale by construction); (2) liveness is not validity — an unassigned-but-shaped number with a correct check digit is storable (UUID precedent: "no checksum, no registry → unallocated-but-shaped reads SUCCESS"); (3) the MOD 11-2 check already rejects random strings with ~91% probability per digit. A `Section-registry-membership` LOOKUP_TABLE against a vendored CC0 snapshot remains a future option (Open Decision §13.3) but must be gated (`include_registry`) so the default contract stays snapshot-independent.

### 5.5 Assignment / registration authority & directory content
ISNI-IA appoints Registration Agencies (sole issuers / user interface): founding agencies include BnF (since 2014), Bowker (founding, rejoined Jan 2025, US book portal ISNI.Bowker.com May 2026), WIPO (Nov 2024), YouTube (2018), Ringgold, MVB, CBL. Assignment runs through VIAF-based matching with a BnF/British Library Quality Team. Directory: 16.6M identities (14.5M individuals incl. 2.9M researchers, 2.05M organisations, ~100 sources). Agencies hold unlimited read-only DB access; public bulk access is the 6-monthly CC0 Linked Data dumps (persons + organisations, RDF/JSON-LD, no SPARQL endpoint) plus Ringgold Open ISNI (organisations only, ~770k, ~2-hourly refresh).

---

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)
Every contract MUST inherit `CapabilityContract` (never `Contract` directly). `@dataclass(frozen=True)` without slots.

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class ISNIContract(CapabilityContract):
    """User-facing configuration for the ISNI capability.

    Default ``isni`` is the spaced display ``XXXX XXXX XXXX XXXC``.
    ``compact`` strips the spaces; ``urn`` renders ``urn:isni:<compact>``
    via ``ISNICapability.format_value`` — the only presentation seam.

    Formats (ADR-0011 classes): ``compact`` — encoding (space strip; MOD
    11-2 runs on the digits, unaffected); ``urn`` — encoding (IANA
    ``urn:isni:`` carrier; the carrier branch re-recognizes the rendering
    to the same compact pre-image, so it re-enters exactly).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isni"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"compact", "urn"}
    )

    capability_name: str = field(default="isni", init=False)

    def __post_init__(self) -> None:
        """Validate the contract and resolve the output format."""
        super().__post_init__()
```

- `DEFAULT_OUTPUT_FORMAT = "isni"`, `OFFERED = {"compact", "urn"}` (both encodings per ADR-0011 §6.1 checklist: carrier-only re-encodings that re-enter exactly; hyphenated is NOT offered — it is ORCID's presentation, and offering it would misattribute).
- `create_contract()` fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`); no capability-specific flags in v1.
- Presentational-only invariant: `output_format` never appears in rules (CI-scanned).

| output_format | Renders | Example |
|---|---|---|
| *(default)* `isni` / `None` / `"default"` | Spaced display | `0000 0001 2103 2683` |
| `compact` | 16-char, no spaces | `0000000121032683` |
| `urn` | IANA carrier | `urn:isni:0000000121241960` |

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)
```python
from paxman.core.capability import Capability
from paxman.core.contract import Contract
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.ISNI.notation import ISNINotation


class ISNICapability(Capability[ISNINotation]):
    """ISNI capability — wiring plus spaced-display presentation seam."""

    name = "isni"

    def get_grammars(self) -> list[Grammar[ISNINotation]]:
        """Return the shipped ISNI grammars in declaration order."""
        from paxman.capabilities.ISNI.grammar.isni_recognition import (
            ISNIRecognitionGrammar,
        )

        return [ISNIRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISNINotation]]:
        """Return the shipped ISNI rules in declaration order."""
        from paxman.capabilities.ISNI.rules.iso_27729_ed2024 import (
            Section4IsniStructure,
            SectionAMod11Dash2,
        )

        return [Section4IsniStructure(), SectionAMod11Dash2()]

    @staticmethod
    def create_contract(...) -> ISNIContract: ...

    def format_value(
        self, value: str, output_format: str | None, notation: ISNINotation
    ) -> str:
        """Render spaced (default), compact, or urn:isni: carrier."""
        if output_format == "compact":
            return notation.compact
        if output_format == "urn":
            return f"urn:isni:{notation.compact}"
        return value
```

Registration via `tools/new_capability.py` (`ISNI --name isni --authority ISO --spec-name "ISO 27729:2024" --spec-url https://www.iso.org/standard/87177.html --publication-year 2024`); export alias `ISNI` (acronym → N814 scoped per-file-ignore precedent, cf. ISBN).

---

## 7. Validation — Structure plus Check Digit

### 7.1 Level 1 — Structure (`Section 4-isni-structure`, PARSER)
16 chars: 15 ASCII digits + check `0-9`/`X` (uppercased by the grammar; lowercase `x` tolerated per IANA). Rejects short/long runs, mid-run `X`, non-ASCII. Worked: `0000000121032683` (16, base all digits) passes shape.

### 7.2 Level 2 — MOD 11-2 (`Section A-mod11-2-check-character`, PARSER)
ISO/IEC 7064 MOD 11-2 over the first 15 digits (ORCID recurrence, verified §2.2 ecosystem table):

```python
def _mod_11_2_check(base15: str) -> str:
    """Compute the MOD 11-2 check char for 15 ASCII digits (X = 10)."""
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)
```

Worked (verified this session against both the ORCID recurrence and stdnum's `checksum() == 1` formulation):
- `000000012103268` → running totals `[0,0,0,0,0,0,0,2,8,18,36,78,160,332,680]`; `680 % 11 = 9`; `(12-9) % 11 = 3` → full `0000000121032683` ✓ (Shakespeare).
- `000000012281955` → check `X` (stdnum docstring vector) ✓.
- `000000012146438` → check `X` (Wikipedia infobox vector) ✓.
- `0000000121241960` → digit check (IANA/Elvis vector) ✓.
- `0000000122974701` → digit check (Wikidata P213 example) ✓.

### 7.3 What makes ISNI "valid" vs "assigned"
- **valid** — correct 16-char structure + MOD 11-2 holds (always-active PARSER pair). Unassigned-but-shaped numbers read SUCCESS (storable, UUID precedent).
- **assigned** — present in the ISNI-IA directory (deferred; would need a vendored CC0 snapshot + gated LOOKUP rule — see §5.4 and §13.3).

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase label + quads | SUCCESS → spaced | grammar folds upper |
| 2 | Compact 16-char | SUCCESS → spaced | compact branch |
| 3 | Hyphenated (ORCID-style) | SUCCESS → spaced | hyphen branch, separators presentation-only |
| 4 | `ISNI:` / `ISNI -` label | SUCCESS, span includes label | fused `[\s:-]+` pattern |
| 5 | Lowercase `x` check | SUCCESS → uppercase `X` | `(?ai:)` + `.upper()` (IANA tolerance) |
| 6 | Resolver URI | SUCCESS, span includes host | host branch |
| 7 | `urn:isni:` carrier | SUCCESS → spaced | carrier branch |
| 8 | Embedded in sentence | SUCCESS with span | word-boundary guards |
| 9 | Two distinct in one slice | `MultipleMentionsError` | `single_value=True`, segmentation |
| 10 | Glued label (`ISNI0000…`) | MISSING | label needs separator + glued guard |
| 11 | Double spaces / tabs in quads | MISSING | single-space only (bounded absorption) |
| 12 | Over-long / under-long (15/17) | MISSING | length guard, never 15/17 |
| 13 | `X` mid-run | MISSING | check position 16 only |
| 14 | Wrong check digit | INVALID | grammar claims, both rules reject |
| 15 | Fullwidth digits | MISSING | ASCII-only `(?ai:)`, no autocorrection |
| 16 | X-glued runs (`X0000…`, `…2683Y`) | MISSING | `word_only` guards |
| 17 | Quoted / bracketed | SUCCESS | inside punctuation |
| 18 | MARC `(isni)…` / `ISNI\|…` pipes | MISSING | DEFERRED to community extension |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| `ISNI 0000 0001 2103 2683` | SUCCESS → spaced | canonical display, both rules hold |
| `0000000121032683` / hyphenated twin | SUCCESS (same spaced) | presentation-only dedup |
| `https://isni.org/isni/…` / `urn:isni:…` | SUCCESS (same spaced) | carrier branches |
| `…2684` (bad check) | INVALID | recognized shape, MOD 11-2 fails |
| 15-/17-char runs, glued label | MISSING | guards reject, nothing claimed |
| Two distinct ISNIs in one slice | `MultipleMentionsError` | single-slice ambiguity, use segmentation |
| `0000 0001 2281 955x` | SUCCESS → `…955X` | lowercase-x tolerance |
| `ISNI\|000000012146438X` (pipe) | MISSING | DEFERRED pipe grammar |
| Pinned `Section 4` alone | SUCCESS (vacuity) | single PARSER rule, no LOOKUP authority in force |

Two deterministic PARSER rules over one single-value grammar yield at most one value per mention, so `AMBIGUOUS` is unreachable for this capability (same argument as ORCID/ISBN/LEI).

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (`tools/new_capability.py` — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)
```bash
uv run python tools/new_capability.py ISNI --name isni --authority "ISO" --spec-name "ISO 27729:2024" --spec-url "https://www.iso.org/standard/87177.html" --publication-year 2024 --default-format isni
```
Creates 13 files + one edit: `paxman/capabilities/ISNI/{notation,contract,capability,grammar/*,rules/*}`, test stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement. Rename the scaffolded `rules/iso_ed2024.py` stub to `rules/iso_27729_ed2024.py` (per-publication naming, §5.2).

> Note: scaffolder single `--spec-name` covers one provenance (ISO 27729). No second provenance file is needed in v1 (single fused rule file).

### 10.2 Contract & grammar wiring
- `get_grammars()` returns `[ISNIRecognitionGrammar()]`; `active_grammars` omitted (base `None` runs every shipped grammar — single grammar, nothing to gate).
- Grammar carries `name = "isni_recognition"` and non-empty `semantics = "isni_recognition"`.

### 10.3 Cross-cutting invariants (fail review if violated)
- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source (scoped per-file-ignores only; `ISNI` alias needs the N814 precedent).
- No cross-capability imports (import only from `paxman.core`, import-linter enforced) — MOD 11-2 is a local copy, never imported from ORCID.
- No `output_format` token in any `paxman/capabilities/ISNI/rules/` module (source-scan).
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contract; `frozenset` semantics/requires.
- Deterministic by construction: same input + contract + library snapshot → same output.

---

## 11. Recommended File Layout (mirrors ORCID and ISBN)

```
paxman/capabilities/ISNI/
├── __init__.py
├── capability.py            # ISNICapability (name = "isni", format_value spaced/compact/urn)
├── contract.py              # ISNIContract (DEFAULT "isni", OFFERED {"compact", "urn"})
├── notation.py              # ISNINotation (compact, spaced, uri, check, is_uri)
├── grammar/
│   ├── __init__.py
│   └── isni_recognition.py  # ISNIRecognitionGrammar (spaced/compact/hyphen + label/host/carrier)
└── rules/
    ├── __init__.py
    └── iso_27729_ed2024.py  # Section4IsniStructure + SectionAMod11Dash2 (shared PUBLICATION)
```

No `rules/data/` in v1 (no registry layer). No `grammar/data/` (regex shape, no lexicon).

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ORCID §9)

- Grammar tests: spaced/compact/hyphenated/URI/`urn:isni:`/labeled/lowercase-x vectors, glued-label and double-space negatives, fullwidth negatives, multiple matches, empty input, span invariants (`raw_text == text[start:end]`), name/semantics/single_value pins, boundary-guard negatives.
- Rule tests: structure rule valid/variant/invalid (short/long/mid-X/non-ASCII), MOD 11-2 valid + `X` vectors + wrong-check INVALID, `normalize()` exact spaced output, provenance attributes (ISO 27729:2024, 2024, specification), PARSER strategy on both, `target_semantics == {"isni_recognition"}`.
- Capability tests: notation frozen/hashable/slots + field invariants, wiring counts (1 grammar, 2 rules), `format_value` round-trips (`isni` identity, `compact` strip, `urn` carrier), `create_contract` factories + `ContractError` on bad `output_format`.
- Integration: MISSING/INVALID/SUCCESS + `MultipleMentionsError` two-distinct, year temporal filtering (`year=2023` drops the 2024 rules → INVALID), `_clean_registry` fixture, determinism/`VersionStamp`, per-candidate spans, dedup (spaced + compact inputs coalesce).
- Property tests (hypothesis): generate valid by random 15-digit base + computed check → must canonicalize to itself; random strings → INVALID/MISSING with high probability; spaced vs compact vs hyphenated identical; `format_value` round-trip incl. `urn`; extend `test_reentry_invariant.py` (ADR-0010) and `test_output_format_preservation.py` (ADR-0011) matrices.
- Consistency test: `isni_recognition` semantics covered by both rules' `target_semantics`.
- Presentation purity: `output_format` source scan over `rules/`.
- Real vectors: `ISNI 0000 0001 2103 2683`, `000000012281955X`, `0000-0001-2281-955X`, `https://isni.org/isni/000000012146438X`, `urn:isni:0000000121241960`, `…2684` INVALID, `ISNI0000…` MISSING.

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT | `isni` (spaced display) | ISO human-readable rule + stdnum `format()`; wire form is presentation |
| 2 | Offered formats | `{"compact", "urn"}`; NOT hyphenated | Both are exact re-encodings (ADR-0011); hyphenated is ORCID's presentation — offering it misattributes |
| 3 | Registry-membership LOOKUP rule | Defer; PARSER-only v1 | CC0 dumps lag 6 months; liveness ≠ validity (LEI/UUID precedent) |
| 4 | Single grammar vs split | Single `isni_recognition` with branches | Avoids cross-grammar spurious AMBIGUOUS |
| 5 | Hyphenated input disposition | RECOGNIZE, normalize to spaced | stdnum strips hyphens; validation decides identity |
| 6 | MARC/VIAF pipe forms | DEFER to `extra_grammars` | Rare, carrier-specific; community-extension shape |
| 7 | `ORCID`-labeled ISNI digits | RECOGNIZE (revised post-review: an `ORCID:`-labeled 16-digit string with valid MOD 11-2 is structurally a valid ISNI — ORCID iDs are ISNI-compatible by design per the 2013 joint statement — so the digits resolve with ISO 27729 provenance; the contract determines presentation, and cross-capability overlap is normal) | ORCID ⊂ ISNI-compatible space; symmetric with shipped ORCID claiming `ISNI:` labels; value and provenance are correct either way |
| 8 | `single_value` | `True` initially | Shipped precedent; segmentation for batches |
| 9 | Double-space/tab quad separators | MISSING (single-space only) | Bounded absorption (ISIN/LEI precedent) |
| 10 | Lowercase `x` | RECOGNIZE (fold to `X`) | IANA tolerance note; stdnum uppercases |
| 11 | Which alternative written forms v1 recognizes | All §2.1 RECOGNIZE rows (spaced/compact/hyphen/URI/urn/labels/lowercase-x) | Unhandled common forms are permanent MISSING blind spots |

---

## 14. Ambiguity Analysis (Paxman-specific)

- No inherent ISNI-vs-ISNI ambiguity — fixed 16-char structure eliminates positional ambiguity of the Date kind; two distinct ISNIs in one slice is authorial multi-entity input, hence `MultipleMentionsError` under `single_value=True`, not AMBIGUOUS.
- ISNI-vs-ORCID overlap is not ambiguity — a hyphenated 16-digit string is claimed by both grammars but each resolves under its own contract; within ISNI there is one grammar and at most one value.
- Hyphenated vs spaced vs compact is not ambiguity — three spellings, one MOD 11-2 identity; dedup coalesces to the spaced canonical.
- `urn:isni:` vs bare is not ambiguity — carrier-only re-encoding (ADR-0011), same pre-image.
- Staleness is not ambiguity — determinism-by-snapshot; CC0 drift affects only a future gated registry rule, with `version` in Provenance.
- Assigned-vs-unassigned is not ambiguity — unassigned-but-shaped reads SUCCESS (storable); assignment is a future LOOKUP concern, never a competing value.

---

## 15. URL Reference (authoritative, fetched 2026-09-26)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 27729:2024 (Ed. 2, current, Published, TC 46/SC 9, ICS 01.140.20) | https://www.iso.org/standard/87177.html | primary |
| ISO 27729:2012 (Ed. 1, withdrawn) | https://www.iso.org/standard/44292.html | primary |
| IANA `urn:isni:` formal registration v1.0 (2025-10-15, NSS grammar, `x` tolerance) | https://www.iana.org/assignments/urn-formal/isni | primary |
| isni.org FAQ (16-digit structure, `X` check, ISNI-IA governance) | https://isni.org/page/faqs | primary |
| isni.org governance (ISNI-IA appointment) | https://isni.org/page/governance | primary |
| isni.org linked data (CC0 dumps, 6-monthly, resolver URI forms) | https://isni.org/page/linked-data | primary |
| isni.org technical documentation (SRU/AtomPub APIs) | https://isni.org/page/technical-documentation | primary |
| ORCID structure page (ISNI-compatible 16-digit, MOD 11-2 Java reference) | https://support.orcid.org/hc/en-us/articles/360006897674-Structure-of-the-ORCID-Identifier | primary |
| ORCID/ISNI joint statement on interoperation (2013-04-22) | https://info.orcid.org/orcid-and-isni-issue-joint-statement-on-interoperation-april-2013 | primary |
| ISO 27729:2024 §4 preview (16-digit structure, spaced display, MOD 11-2) | https://standards.iteh.ai/catalog/standards/iso/ad745aea-8071-4698-8670-702140e744c9/iso-27729-2024 | primary-mirror |
| python-stdnum `isni.py` (compact/validate/format) | https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/isni.py | primary |
| python-stdnum `iso7064/mod_11_2.py` (checksum math) | https://raw.githubusercontent.com/arthurdejong/python-stdnum/master/stdnum/iso7064/mod_11_2.py | primary |
| stdnum iso7064 docs (calc_check_digit examples) | https://arthurdejong.org/python-stdnum/doc/1.17/stdnum.iso7064 | primary |
| Wikidata Property P213 (regex, formatter, URL-match) | https://www.wikidata.org/wiki/Property:P213 | primary |
| LOC MARC `024 $aISNI` practice | https://www.loc.gov/marc/marbi/2010/2010-dp03.html | primary |
| ORCID research precedent | docs/development/research/2026-08-23-orcid-canonicalization.md | primary (repo) |
| ORCID capability plan | docs/development/plans/2026-08-23-orcid-capability.md | primary (repo) |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary (repo) |
| Shipped ORCID precedent | paxman/capabilities/ORCID/ + paxman/engine/orchestrator.py + paxman/core/domain.py | primary (repo) |
| ISNI infobox (digits/check/example, secondary) | https://en.wikipedia.org/wiki/International_Standard_Name_Identifier | secondary |
| ORCID ranges (secondary) | https://en.wikipedia.org/wiki/ORCID | secondary |

---

## 16. Evidence Completion — Resolved

This report's ISNI-specific authoritative evidence has been fetched and cited (2026-09-26):
- [x] ISO catalogue entry: ISO 27729:2024 (Ed. 2, current, Published) superseding 2012 Ed. 1 + Cor 1:2013; TC 46/SC 9; ICS 01.140.20; version lifecycle publication_year 2024; citation anchored to §4/Annex A
- [x] RA and directory provenance: ISNI-IA (UK Co. 07476425); 16.6M identities; CC0 6-monthly dumps; assignment via Registration Agencies + VIAF matching
- [x] Structure: 16 chars, 15 digits + `0-9`/`X` check, spaced-quad display, `ISNI`-prefix human-readable rule
- [x] Checksum algorithm proved: ISO/IEC 7064 MOD 11-2 with letter table (`X`=10) and five worked vectors cross-checked against two formulations
- [x] Registry nuance: CC0 lag + liveness≠validity → PARSER-only v1, LOOKUP deferred (§5.4, §13.3)
- [x] Ecosystem regex consensus: stdnum compact/validate/format + Wikidata URL-match + ORCID Java reference (validator.js negative finding recorded)
- [x] Recognition-surface inventory complete (§2.1): every attested written form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form
- [x] Wild input shapes validated (§2.2) against spec + RA pages + dumps + validators
- [x] Label scope decision (§13.7: `ISNI` claimed, `ORCID` not poached)
- [x] Hyphen/compact equivalence decision (§13.5)
- [x] Check-`X` case decision (§13.10)
- [x] Directory liveness scope decision (§5.4)
File layout / rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ORCID, ISBN, ISSN, Country and Phone Capabilities Teach ISNI (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

Refer to `paxman/capabilities/ORCID/` (notation/contract/grammar/rules/capability — surveyed verbatim in the evidence pack), `paxman/capabilities/ISBN/` + `ISSN` (check-digit rule pairs, `format_value` hyphenation seam), `Country` (name lexicon + gated LOOKUP pattern for the deferred registry option), `Phone` (carrier/label discipline), `paxman/engine/orchestrator.py` (`_dedup_spans` longer-wins per grammar, `_validate_affinity`, `single_value` enforcement) and `paxman/core/domain.py` (`Rule.__init_subclass__` six attributes, `Grammar.__init_subclass__` semantics). The four architectural lessons for ISNI:
1. **Grammar strips, rule validates, capability formats.** Notation carries normalized spaced display; rules own MOD 11-2; `format_value()` owns compact/urn renderings.
2. **One file per provenance, one class per section.** Single `rules/iso_27729_ed2024.py` with `Section4IsniStructure` + `SectionAMod11Dash2`, shared PUBLICATION.
3. **No `output_format` in rules, ever.** Both `normalize()` methods return the spaced default; CI purity scan enforced.
4. **Single grammar with alternation branches avoids spurious AMBIGUOUS; cross-grammar containment is preserved.** Spaced/compact/hyphen/URI/carrier are branches of `isni_recognition`, never separate grammars.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for ISNI. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the ORCID precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
