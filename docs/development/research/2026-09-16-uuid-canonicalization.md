# UUID Canonicalization Research — paxman-python

**Date:** 2026-09-16
**Scope:** Primary-source survey of the UUID standard (RFC 9562, obsoleting RFC 4122), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `UUID` capability. No source code, tests, or configuration were modified.
**Evidence basis:** RFC 9562 full text (fetched 2026-09-16), validator.js `isUUID.js` verbatim (fetched 2026-09-16), Python 3.14 `uuid` stdlib docs (fetched 2026-09-16), GitHub API listing of python-stdnum proving no UUID module exists (fetched 2026-09-16), plus shipped-capability precedent surveyed verbatim from the tree (ISBN/ISSN/IBAN/ORCID/MacAddress, `paxman/engine/orchestrator.py`, `paxman/core/domain.py`). Repo state: `dev @ 26b7844` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN (2026-08-21), IBAN (2026-08-22), BIC (2026-08-23), ORCID (2026-08-23) research precedents.

---

## Executive Summary

UUID is a **strong** fit for a Paxman capability: it has an unambiguous canonical form (**lowercase hex-and-dash `8-4-4-4-12`**), a stable single-part standard (**RFC 9562**, May 2024, Standards Track, IETF) with **no registration authority and no registry to snapshot** (uniqueness is algorithmic, not assigned), and a well-understood human-readable presentation (hyphenated display, presentation-only). The domain mirrors Paxman's value proposition for ORCID/MacAddress: recognizing tolerant human surface, validating strictly against structure, returning canonical compact value with provenance. **There is no checksum**: RFC 9562 defines no check digit anywhere — unlike ISBN/ISSN/ORCID/IBAN/LEI, structure (length + charset + field positions) is all there is, proved in §5.1 with two independent sources.

Key findings that shape the design:
1. **Canonical form is lowercase hyphenated `8-4-4-4-12`** (36 chars; RFC ABNF §4 is case-insensitive, Python `str()` renders lowercase — §5.1, §7).
2. **One grammar**, RegexStage with optional brace/URN groups + bare-32 alternation (ORCID precedent) — avoids cross-grammar containment spurious AMBIGUOUS; generation≠storage (§4.2) means version/variant bits are *informative*, never validity gates.
3. **Validation is PARSER-only, single rule** — no LOOKUP_TABLE exists (no registry; ADR-0012 vacuity exception, §5.4); Nil/Max are SUCCESS by structure.
4. **No branch/variant equivalence question** — unlike BIC XXX or ISBN-10→13, every 128-bit value is its own identity; `urn:`/`{braces}`/bare are carriers, not identities (§14).
5. **Provenance is a single publication** (RFC 9562) — one rule file, one PUBLICATION constant, one Rule class (HOW_TO_ADD_NEW_CAPABILITY.md Step 5).

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---
## 1. Target User

| Persona | Why they need UUID canonicalization | Typical context |
|---|---|---|
| Backend engineer | Log lines, API dumps, and DB exports mix braced/URN/bare/upper forms of the same id | Deduplicating event pipelines keyed by request id |
| Data engineer | Join keys arrive hyphenated from one source, bare-hex from another | Warehouse ingestion joining on `order_id` |
| Support/on-call | Customers paste ids from Windows dialogs (`{GUID}`), `curl` output, dashboards | Pasting into runbooks and lookup tools |
| DBA / storage engineer | Sortable v6/v7 ids vs random v4 in indexes (RFC §2.1 motivation) | Diagnosing index-locality complaints keyed by id shape |
| Security analyst | Indicator lists carry mixed-case, prefixed, or truncated UUID-like strings | Triage: real id (SUCCESS) vs truncated noise (MISSING) |

**User-visible contract:** The caller supplies raw human text and a contract; Paxman returns one canonical lowercase hyphenated UUID (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ORCID ergonomics, but the canonical default is **lowercase hex-and-dash** (Python `str()` form), not uppercase.

---
## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Hyphenated canonical | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` | RFC 9562 §4 ABNF + Fig 1 | canonical | RECOGNIZE | main pattern body |
| Uppercase hyphenated | `6BA7B810-9DAD-11D1-80B4-00C04FD430C8` | RFC §4 (case-insensitive per RFC 5234 §2.3) | common | RECOGNIZE | explicit `[0-9A-Fa-f]` ranges + `.lower()` fold in emit |
| Mixed-case hyphenated | `6Ba7b810-9DAD-11d1-80b4-00c04FD430C8` | RFC §4 (same clause) | occasional | RECOGNIZE | same fold |
| Bare 32-hex | `6ba7b8109dad11d180b400c04fd430c8` | Python `UUID(hex=…)` accepts 32-hex (stdlib docs) + DB/API dumps | common | RECOGNIZE | alternation branch (ORCID compact precedent) |
| Braced | `{6ba7b810-9dad-11d1-80b4-00c04fd430c8}` | RFC §4 ("Python and Microsoft output … enclosed in curly braces") + Python `UUID('{…}')` | common | RECOGNIZE | optional `[{]`…`[}]` group |
| URN-prefixed | `urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8` | RFC §4 Fig 4 + Python `UUID('urn:uuid:…')` | common | RECOGNIZE | optional `urn:uuid:` group (ORCID host precedent) |
| Uppercase URN | `URN:UUID:6BA7…` | RFC §4 case-insensitivity + URN scheme case rules | rare | RECOGNIZE | same group, folded |
| Nil | `00000000-0000-0000-0000-000000000000` | RFC §5.9 + Python `uuid.NIL` + validator `nil` | official special | RECOGNIZE | structural (passes shape) |
| Max | `ffffffff-ffff-ffff-ffff-ffffffffffff` | RFC §5.10 + Python `uuid.MAX` + validator `max` | official special | RECOGNIZE | structural (passes shape) |
| Label-prefixed prose (`UUID:`/`GUID:`) | `UUID: 6ba7b810-…` | plausible in tickets/logs, **no primary attestation found** | unproven | DEFER (`extra_grammars`) | fused label — needs corpus evidence first |
| Space/dot-grouped | `6ba7b810 9dad 11d1 …` | **unattested** — no spec, schema, or validator strips these | unproven | REJECT (v1) | documented negative test |
| Binary/integer dumps | `329800735698586629295641978511506172918` | RFC Fig 3 (informational only) | rare/carrier | REJECT (v1) | not text-surface; decimal form collides with Money/Phone |
| Truncated/padded runs | 31- or 33-hex, 37-char hyphenated | length guard | invalid | REJECT | length guard, never 31/33/35/37 |
| OCR/homoglyph (`O` for `0`) | `6ba7b81O-…` | strict charset | invalid | REJECT | no autocorrection, ASCII hex only |

Silence audit: the v1 grammar answers every spec- or validator-attested form above; the only deliberate cuts (label prefix, exotic groupings, integer dumps) are dispositioned here and in §13 row 11.

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical hyphenated | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` | Spec master form |
| 2 | Uppercase | `6BA7B810-9DAD-11D1-80B4-00C04FD430C8` | fold upper, canonical lowercase |
| 3 | Mixed case | `6Ba7-B810-…` | fold, single canonical |
| 4 | Bare 32-hex | `6ba7b8109dad11d180b400c04fd430c8` | alternation branch, no separators |
| 5 | Bare uppercase | `6BA7B8109DAD11D180B400C04FD430C8` | fold + branch |
| 6 | Braced | `{6ba7b810-…-00c04fd430c8}` | optional brace group, span includes braces |
| 7 | Braced bare inside | `{6ba7b8109dad…}` | braces + bare combo (Python accepts) |
| 8 | URN lowercase | `urn:uuid:6ba7b810-…` | optional URN group, span includes prefix |
| 9 | URN uppercase/mixed | `URN:UUID:6BA7…` | folded group |
| 10 | Nil | `00000000-0000-0000-0000-000000000000` | SUCCESS (absence sentinel, still a value) |
| 11 | Max | `ffffffff-ffff-ffff-ffff-ffffffffffff` | SUCCESS (end sentinel) |
| 12 | Nil bare/braced | `00000000000000000000000000000000` | SUCCESS via bare branch |
| 13 | Version 1/6/7 time-based | `f81d4fae-7dec-11d0-a765-00a0c91e6bf6` (RFC Fig 1) | version digit informative only |
| 14 | With trailing annotation | `6ba7b810-… (request id)` | span covers id only |
| 15 | Multiple per line | two ids, one line | 2 matches; single_value → MultipleMentionsError |
| 16 | Quoted/bracketed | `"6ba7b810-…"`, `[6ba7b810-…]` | inside punctuation |
| 17 | X-glued runs | `x6ba7b810-…`, `…c8x` | word-boundary guards → MISSING |
| 18 | Over-long/under-long | 33-hex bare, 37-char dashed | length guard → MISSING |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| validator.js `isUUID` v4 (verbatim) | `/^[0-9A-F]{8}-[0-9A-F]{4}-4[0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/i` — version digit + variant `[89AB]` enforced per version 1–8 |
| validator.js `nil` / `max` / `loose` (verbatim) | `/^00000000-0000-0000-0000-000000000000$/i`, `/^ffffffff-ffff-ffff-ffff-ffffffffffff$/i`, `/^[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}$/i` |
| validator.js `all` (verbatim, after uuidjs) | `/^(?:[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\|00000000-0000-0000-0000-000000000000\|ffffffff-ffff-ffff-ffff-ffffffffffff)$/i` — versions 1–8 + nil + max; 0/9–F excluded |
| Python stdlib `uuid.UUID(hex=…)` | "curly braces, hyphens, and a URN prefix are all optional"; `str()` renders lowercase hyphenated; `.hex` is 32-char lowercase; `urn` property per RFC 9562 |
| python-stdnum | **No UUID module exists** (verified via GitHub API dir listing, 135 entries, 2026-09-16) — ecosystem gap, no strip-logic evidence to mine |
| RFC 9562 §4 ABNF (verbatim) | `UUID = 4hexOctet "-" 2hexOctet "-" 2hexOctet "-" 2hexOctet "-" 6hexOctet` — imposes **no** version/variant constraint on the string form |

**Normalization contract (ORCID/MacAddress pattern):**
```python
core = re.sub(r"^(?:urn:uuid:)?[{]?", "", raw, flags=re.IGNORECASE)
core = re.sub(r"[}]$", "", core)
compact = re.sub(r"-", "", core).lower()
# then validate: len(compact) == 32 and all ASCII hex; hyphenate 8-4-4-4-12
```

### 2.3 What input is NOT a UUID mention
- 32-hex runs that fail charset (non-hex letters) — MISSING at grammar (never INVALID: unclaimable shape)
- 16-hex runs — ORCID-compact territory (length-disjoint by construction; §4.4)
- 12/16-hex runs — MacAddress bare territory (length-disjoint)
- 13-digit runs — ISBN territory; ≤15-digit runs — Phone territory
- 32-hex starting `[A-Z]{2}[0-9]{2}` with total length 15–34 — IBAN-shape overlap (§4.4: validation decides, both candidates observable)
- Decimal integer dumps — Money/Phone territory → REJECT per §2.1
- Short runs, bare words — MISSING (no grammar claims)

### 2.4 Single-mention vs multi-mention input
Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct UUIDs → `MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS`.

---
## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — compact plus pre-computed presentations
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class UUIDNotation:
    """Hyphenated/compact/URN pre-computed; version digit informative."""
    compact: str      # 32-char lowercase hex, separators/prefix stripped
    hyphenated: str   # 8-4-4-4-12 lowercase canonical
    urn: str          # urn:uuid: + hyphenated (always lowercase scheme)
    version: str      # hex char at compact[12], or "nil"/"max" sentinels
```

**Considered alternative — `compact` only:** rejected. Pre-computing mirrors ORCID (`compact`/`hyphenated`/`uri`/`check`/`is_uri`) so `format_value` selects without recomputation, and `version` carries the informative digit for tests/vectors without re-parsing.

**Invariants the grammar enforces (before rules):**
- compact is exactly 32 ASCII hex chars, lowercased from `[0-9A-Fa-f]`
- hyphenated is `compact` regrouped 8-4-4-4-12; urn is `"urn:uuid:" + hyphenated`
- version is `compact[12]` (single hex char), except all-zero → `"nil"`, all-one → `"max"`
- braces/URN prefix/labels never survive into any field

### 3.2 Why not carry braces or URN prefix in the notation
Braces, grouping, and `urn:uuid:` have **no lexical significance** for validity — presentation is `Capability.format_value()` only (ORCID §7f precedent).

### 3.3 Why version is not a shape discriminator literal
Free `str` validated structurally, not `Literal` — version digits 0–F are all storable values (generation≠storage, §4.2); gating on them would turn storable input into INVALID against the RFC's own storage rules.

---
## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex with optional carrier groups
Per HOW_TO_ADD_NEW_GRAMMAR.md, UUID has a distinctive fixed-width shape with a small set of documented carriers, so **RegexStage** (legacy pipeline, ISBN/ORCID/MacAddress precedent) is correct. Lexicon is wrong (2¹²⁸ space); scanner is unnecessary (no multi-segment grammar).

### 4.2 Reference pattern (ORCID verbatim precedent, adapted)
```python
import re
from paxman.capabilities.UUID.notation import UUIDNotation
from paxman.core.grammar import BoundaryGuard, PipelineGrammar, StandardPre
from paxman.core.grammar.stages import RegexStage

_UUID_HEX = r"[0-9A-Fa-f]"
_UUID_DASHED = rf"(?:{_UUID_HEX}{{8}}-{_UUID_HEX}{{4}}-{_UUID_HEX}{{4}}-{_UUID_HEX}{{4}}-{_UUID_HEX}{{12}})"
_UUID_BARE = rf"{_UUID_HEX}{{32}}"
_UUID_BODY = (
    r"(?:[Uu][Rr][Nn]:[Uu][Uu][Ii][Dd]:)?"  # optional URN carrier (RFC §4 Fig 4)
    r"[{]?"                                 # optional brace (RFC §4 Python/Microsoft note)
    rf"(?P<core>{_UUID_DASHED}|{_UUID_BARE})"
    r"[}]?"
)
_UUID_PATTERN = (
    BoundaryGuard.word_only().lookbehind + _UUID_BODY + BoundaryGuard.word_only().lookahead
    + r"(?![-][0-9A-Fa-f])"  # ISBN/ISSN precedent: no truncated-hyphenated-prefix match
)
def _uuid_notation(match: re.Match[str]) -> UUIDNotation:
    compact = re.sub(r"-", "", match.group("core")).lower()
    hyphenated = f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}-{compact[16:20]}-{compact[20:]}"
    version = "nil" if compact == "0" * 32 else "max" if compact == "f" * 32 else compact[12]
    return UUIDNotation(compact=compact, hyphenated=hyphenated, urn=f"urn:uuid:{hyphenated}", version=version)

class UUIDRecognitionGrammar(PipelineGrammar[UUIDNotation]):
    name = "uuid_recognition"
    semantics = "uuid_recognition"
    single_value = True
    pre = StandardPre[UUIDNotation](empty_guard=True)
    regex = RegexStage[UUIDNotation](pattern=_UUID_PATTERN, notation_fn=_uuid_notation)
```
*Notes on fidelity vs ORCID:* single grammar with dashed|bare alternation (re-entry: every offered format re-recognized); ASCII hex class (no `(?ai:)` needed — explicit ranges); brace/URN groups optional; `word_only` guards both sides plus an ISBN/ISSN-family trailing guard against truncated-hyphenated prefixes (see pattern). Brace-guard dynamics verified: `{`/`}` are non-word, so guards pass on brace neighbors by construction — no false rejection. Empirically: `{uuid}` claims the full span; `{uuid`, `uuid}`, `}uuid`, `uuid{`, and `x{uuid}` claim nothing (brace-aware guards extend `word_only` with both braces on each side, so carriers match paired-or-absent only). Fixed 32/36 widths leave no MacAddress-style truncation shadow; a over-long-run guard test pins 33-hex MISSING). **Form-coverage traceability:** hyphenated→body, bare→branch, braced→brace group, URN→prefix group, upper/mixed→fold; DEFER label-prefix→`extra_grammars`, REJECT integer-dumps→no element.

**One grammar, not two:** dashed vs bare in one alternation avoids cross-grammar containment spurious AMBIGUOUS (a bare 32-hex is never contained in a dashed match and vice versa, but one grammar keeps `_dedup_spans` longer-wins semantics trivially correct).

**Version/variant string-position map** (where validator.js's positional checks come from; v1 grammar does NOT enforce these — informative only):

| Position | compact index | hyphenated index | Meaning | validator.js analogue |
|---|---|---|---|---|
| Version nibble | `compact[12]` | index 14 (`M` in `xxxx-Mxxx`) | `0`–`8` defined, `9`–`F` future | `[1-8]` in `all`/per-version |
| Variant nibble | `compact[16]` | index 19 (`N` in `Nxxx`) | `8/9/A/B` = this spec | `[89ab]` in `all`/per-version |
| Nil sentinel | all 32 `0` | `00000000-0000-…` | NCS-variant range (§5.9) | `nil` branch |
| Max sentinel | all 32 `f` | `ffff…` | future-variant range (§5.10) | `max` branch |

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)
- Grammar emits span-bearing RecognitionMatch, half-open [start,end), raw_text == text[start:end] (span includes braces/URN prefix when present — ORCID label/URI precedent)
- RegexStage loops re.finditer, builds RecognitionMatch, Stages must not mutate text
- Engine owns within-grammar containment dedup (longer wins) and total recognition ordering
- Candidate dedup (value, recognition_rule, validation_rule) after validation

### 4.4 Guard boundaries against sibling grammars
| Grammar | Chars | Risk | Guard outcome |
|---------|-------|------|---------------|
| UUID dashed (36) | hex+dash | Phone E.164 (≤15 digits, `+`/space separated)? No — dashes at fixed 8-4-4-4-12 break digit runs; a 36-char dashed run cannot match any phone branch | disjoint by shape |
| UUID dashed (36) | hex+dash | ISBN-13 (13 digits, `[ -]` separators)? No — 36 chars with 4 dashes matches neither isbn13 (12 seps-tolerant digits) nor isbn10 (9+X) branch | disjoint by shape |
| UUID dashed (36) | hex+dash | Date (`01/02/2026` slash forms)? No — `/` absent, `-` positions fixed | disjoint by shape |
| UUID bare (32 hex) | `[0-9A-Fa-f]{32}` | IBAN electronic (`[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}`, 15–34): only LLDD-prefixed runs are claimed — verified: `ab12…(32)` → IBAN span (0,32), while digit-leading, DDLL, and non-digit-at-index-2–3 runs → no claim | **overlap narrow and real**: claimed runs face IBAN MOD97 (≈1/97 random pass) + CC-registry + per-country length, so all but pathological inputs read INVALID there while UUID structural → SUCCESS. Engine preserves both (cross-grammar overlap kept); caller disambiguates. Documented, not solved — same class as Language `in`-form competition |
| UUID bare | 32 hex | ORCID compact (16), MAC bare (12/16), ISBN (13) | disjoint by exact length |
| UUID bare | 32 hex | Money symbol runs (`$500`)? No — `$`/digits, no 32-hex shape | disjoint by shape |
| UUID braced (38) | `{…}` | nothing claims braces | disjoint |
| UUID URN (45) | `urn:uuid:…` | ISSN `urn` format is `urn:issn:` — scheme-disjoint; URL capability (opaque/absolute URIs)? `urn:uuid:…` IS a valid URN — **overlap real**: URL grammar may claim the URN form as a URI while UUID claims the id. Both observable; validation decides per capability. Document for the plan's §4.4 sibling test | overlap real, caller disambiguates |

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)
- semantics = `"uuid_recognition"` identity id; a future fused `GUID:`-label variant would coalesce to the same id

### 4.6 `single_value` — one mention per call vs batch processing
Recommendation: `single_value=True` (universal shipped precedent for fixed-shape identifiers), segmentation path for batches.

---
## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | IETF (Standards Track) |
| Registration Authority | **None** — "requires no central registration process" (RFC §1); IANA holds only subtype/namespace registries (§7), not an id directory |
| Spec name | RFC 9562, Universally Unique IDentifiers (UUIDs) |
| Current edition | May 2024, Standards Track, obsoletes RFC 4122 |
| Check character system | **None** — no check digit in any section (proved §5.1-negative below) |
| Country code reference | N/A (no geography in the value) |
| Related specs | RFC 4122 (obsoleted), OSF DCE 1.1 (ancestor), ITU-T X.667 / ISO/IEC 9834-8 (aligned, compatible), RFC 8141 (URN) |

**Structure (RFC §4):** 128 bits, 16 octets, network byte order; string form is hex-and-dash `8-4-4-4-12`, case-insensitive; variant bits = octet 8 MSB (`10xx` = this spec); version nibble = octet 6 high (`0`–`8` defined, `9`–`F` reserved future); Nil = all-zero (§5.9, NCS-variant range); Max = all-one (§5.10, future-variant range).

**Variant table (RFC §4.1 Table 1, condensed):** `0xxx` → NCS backward-compat (includes Nil); `10xx` → this spec (octet-8 hex `8/9/A/B`); `110x` → Microsoft reserved; `111x` → future reserved (includes Max). Storage rule: bits 64–65 MUST be `10` for spec UUIDs — but the *string* ABNF constrains nothing, hence informative-only validation (§13.3).
**Version table (RFC §4.2 Table 2, condensed):** `0` unused; `1` Gregorian time; `2` DCE Security (definition out of scope, §5.2); `3` MD5 name; `4` random; `5` SHA-1 name; `6` reordered time; `7` Unix-ms time; `8` custom (122 impl bits, uniqueness NOT assumed); `9`–`F` reserved future.
**Lineage table:**

| Edition | Date | Status | Note |
|---|---|---|---|
| OSF DCE 1.1 (C309/C311) | 1990s | Historic ancestor | NCS Apollo origin; variant bits, DCE Security v2 |
| RFC 4122 (Leach/Mealling/Salz) | July 2005 | Obsoleted by 9562 | Versions 1–5 only; errata Err1957/3546/4975/4976/5560 |
| ITU-T X.667 / ISO/IEC 9834-8 | aligned w/ 4122 | Published, compatible | OID use of UUIDs; "fully technically compatible" (RFC 9562 §1) |
| RFC 9562 (Davis/Peabody/Leach) | May 2024 | **Current, Standards Track** | Adds v6/v7/v8, Nil/Max, generation-vs-storage split, IANA registries |

**No-checksum proof (two independent sources):** (1) RFC 9562 contains no check-digit/checksum section across §§4–5 — validity sections define only layout, version, variant; generation algorithms (random/hash/time) embed no redundancy. (2) Ecosystem validators enforce structure only: validator.js checks version digit + variant nibble positionally (no computation), Python stdlib parses without any check step. Contrast ISBN/ISSN/ORCID/IBAN/LEI, all of which name an algorithm.
**Citation Details Table (for Provenance):**

| authority | spec_name | version | reference_url | lifecycle | publication_year | kind |
|---|---|---|---|---|---|---|
| IETF | RFC 9562 | May 2024 | https://www.rfc-editor.org/rfc/rfc9562 | active | 2024 | specification |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)
| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|----------------|-------------------|
| rules/rfc_9562_ed2024.py | authority="IETF", specification_name="RFC 9562", kind="specification", reference_url="https://www.rfc-editor.org/rfc/rfc9562", version="May 2024", lifecycle="active", publication_year=2024 | Section 4-uuid-format | Length/charset/field structure (PARSER, always-active) |

Single publication → single file → single class. No country/registry split exists (no RA directory); no second publication to fuse.

Each Rule[UUIDNotation] subclass declares six enforced metadata attributes at class-definition time (Rule.__init_subclass__):

```python
class Section4UUIDFormat(Rule[UUIDNotation]):
    name = "Section 4-uuid-format"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (128-bit format; hex-and-dash ABNF)"
    target_semantics = frozenset({"uuid_recognition"})
    requires_features = frozenset()
```

### 5.3 What each rule does vs does not own
- matches() validates strictly (32-hex compact, ASCII hex only, exact length — after grammar strip), never raises; contract misconfigs caught in contract.__post_init__
- normalize() returns lowercase hyphenated form, never reads output_format (CI purity scan), identical across rules for dedup
- RuleStrategy: PARSER (structure only). No LOOKUP_TABLE exists — ADR-0012 vacuity exception documented in §5.4 (same standing as ORCID's PARSER-only pair)

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)
No registry validation is possible — there is no directory of issued UUIDs (uniqueness is probabilistic/algorithmic, §2 motivation). Consequences: (a) no `include_*` directory flag; (b) PARSER-only rule set survives ADR-0012 via the vacuity clause ("no lookup authority available"), exactly ORCID's standing; (c) version/variant gating rejected — generation rules (§5.x) constrain minting, storage rules (§4) constrain parsing, and RFC §2.1(6) explicitly separates the two.

### 5.5 Assignment / registration authority & Registry content
Not applicable — no RA, no directory, no cadence, no registration data. IANA §7 registries (subtype, namespace IDs) govern UUID *namespaces*, not values; vendoring them buys no validation. This section exists to record the negative so planners do not go looking.

---
## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)
Every contract MUST inherit CapabilityContract (never Contract directly). @dataclass(frozen=True) without slots.

```python
from dataclasses import dataclass, field
from typing import ClassVar
from paxman.core.capability_contract import CapabilityContract

@dataclass(frozen=True)
class UUIDContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "hyphenated"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact", "braced", "urn"})
    capability_name: str = field(default="uuid", init=False)
```

- DEFAULT_OUTPUT_FORMAT `"hyphenated"` (lowercase 8-4-4-4-12, Python `str()` form); OFFERED excludes default; resolved via base `__post_init__`; `create_contract()` fixed keyword-only common block, no capability-specific params (no registry flags exist)
- Presentational-only invariant, output_format never in rules
- Offered formats (all re-enter — grammar answers each carrier)

| output_format | Renders | Example |
|---|---|---|
| *(default)* `hyphenated` | lowercase 8-4-4-4-12 | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` |
| `compact` | 32-char lowercase hex | `6ba7b8109dad11d180b400c04fd430c8` |
| `braced` | hyphenated in `{}` | `{6ba7b810-9dad-11d1-80b4-00c04fd430c8}` |
| `urn` | RFC 9562 URN | `urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8` |

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)
```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.UUID.notation import UUIDNotation

class UUIDCapability(Capability[UUIDNotation]):
    name = "uuid"
    def get_grammars(self) -> list[Grammar[UUIDNotation]]: return [UUIDRecognitionGrammar()]
    def get_rules(self) -> list[Rule[UUIDNotation]]: return [Section4UUIDFormat()]
    @staticmethod
    def create_contract(...) -> UUIDContract: ...
    def format_value(self, value: str, output_format: str | None, notation: UUIDNotation) -> str:
        if output_format == "compact":
            return notation.compact
        if output_format == "braced":
            return "{" + notation.hyphenated + "}"
        if output_format == "urn":
            return notation.urn
        return value
```

Registration via tools/new_capability.py (`UUID --name uuid --authority "IETF" --spec-name "RFC 9562" --spec-url "https://www.rfc-editor.org/rfc/rfc9562" --publication-year 2024`).

```python
@staticmethod
def create_contract(
    *,
    excluded_rules: tuple[str, ...] = (),
    pinned_rules: tuple[str, ...] | None = None,
    year: int | None = None,
    output_format: str | None = None,
) -> UUIDContract:
    ...
```
No capability-specific params (no registry flags exist — §5.5). `year` temporal filtering applies generically (rules carry publication_year 2024; `year=2020` drops the rule → claimed input reads INVALID, Timezone §62 precedent).

---
## 7. Validation — single structural level

### 7.1 Level 1 Generic structure (the only level)
Algorithm: compact must be exactly 32 chars, all ASCII `[0-9a-f]` post-fold; regroup 8-4-4-4-12. Formal regex on compact: `^[0-9a-f]{32}$`. Worked: `6ba7b8109dad11d180b400c04fd430c8` → valid; `6ba7b8109dad11d180b400c04fd430c8` with `g` → grammar never claims (charset). Version nibble read (informative): `compact[12]` = `1` → v1.

**Version layouts that justify the informative `version` field** (RFC §5, all under variant `10xx`):

| Version | RFC section | 48-bit head | nibble `compact[12]` | Tail rule | Real vector |
|---|---|---|---|---|---|
| v1 Gregorian time | §5.1 | `time_low`+`time_mid` | `1` | 60-bit ts + clock_seq + node | `f81d4fae-7dec-11d0-a765-00a0c91e6bf6` (Fig 1) |
| v3 MD5 name | §5.3 | md5_high | `3` | MD5(ns+name), ver/varit stamped | `6fa459ea-ee8a-3ca4-894e-db77e160355e` (DNS+python.org) |
| v4 random | §5.4 | random_a (48b) | `4` | 122 random bits | `16fd2706-8baf-433b-82eb-8c7fada847da` |
| v5 SHA-1 name | §5.5 | sha1_high | `5` | SHA-1(ns+name) truncated | `886313e1-3b8a-5372-9b90-0c9aee199e5d` (DNS+python.org) |
| v6 reordered time | §5.6 | time_high+mid first | `6` | v1 bits, sortable order | `1f0799c0-98b9-62db-92c6-a0d365b91053` |
| v7 Unix-ms time | §5.7 | unix_ts_ms (48b) | `7` | ms + rand/counter | time-ordered, byte-comparable |
| v8 custom | §5.8 | custom_a | `8` | 122 impl bits | uniqueness NOT assumed |
| v2 DCE Security | §5.2 | — | `2` | out of scope (POSIX UID/GID embed) | recognized structurally, never interpreted |

**Worked normalizations (grammar → rule → canonical):**

| Raw input | Grammar strips to compact | Rule | Canonical |
|---|---|---|---|
| `{6BA7B810-9DAD-11D1-80B4-00C04FD430C8}` | `6ba7b8109dad11d180b400c04fd430c8` | structure ✓ | `6ba7b810-9dad-11d1-80b4-00c04fd430c8` |
| `urn:uuid:6fa459ea-ee8a-3ca4-894e-db77e160355e` | `6fa459eaee8a3ca4894edb77e160355e` | structure ✓ (v3 informative) | `6fa459ea-ee8a-3ca4-894e-db77e160355e` |
| `00000000-0000-0000-0000-000000000000` | same, version=`nil` | structure ✓ | itself |
| `6ba7b8109dad11d180b400c04fd430c` (31-hex) | unclaimed | — | MISSING |

### 7.2 What makes a UUID "valid" vs "well-formed" vs "registered"
- valid — 32-hex structure (the only gate; always-active PARSER)
- well-formed version/variant — informative, never gates (v0/v9–F storable per §4 ABNF silence)
- registered — **undefined**: no directory exists; any "issued/live" notion is out of scope by construction (§5.5)

Like ORCID valid vs issued, minus the registry half.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase hyphenated | SUCCESS → same | canonical form |
| 2 | Uppercase hyphenated | SUCCESS → lowercase | grammar folds |
| 3 | Mixed case | SUCCESS → lowercase | fold, single canonical |
| 4 | Bare 32-hex | SUCCESS → hyphenated | alternation branch |
| 5 | Braced | SUCCESS, span includes braces | optional group |
| 6 | URN prefixed | SUCCESS, span includes prefix | optional group |
| 7 | Nil UUID | SUCCESS → itself | sentinel, structural |
| 8 | Max UUID | SUCCESS → itself | sentinel, structural |
| 9 | Version 0 / 9–F digit | SUCCESS (version informative) | generation≠storage |
| 10 | Non-RFC variant nibble | SUCCESS (variant informative) | same |
| 11 | Embedded in sentence | SUCCESS with span | word-boundary guards |
| 12 | Two distinct in one slice | AMBIGUOUS / MultipleMentionsError | segmentation |
| 13 | 33-hex / 31-hex bare | MISSING | length guard |
| 14 | 37-char dashed | MISSING | length guard |
| 15 | X-glued runs | MISSING | `(?<!\w)`/`(?!\w)` |
| 16 | Quoted/bracketed | SUCCESS | inside punctuation |
| 17 | 32-hex LLDD-prefix (IBAN shape) | UUID SUCCESS + IBAN INVALID observable | validation decides (§4.4) |
| 18 | Non-hex letter (`g`, `O`-as-letter) | MISSING | ASCII hex only, no autocorrection |

---
## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid hyphenated any case | SUCCESS → lowercase hyphenated | fold + structure |
| Bare/braced/URN carriers | SUCCESS (same canonical) | presentation-only dedup |
| Nil / Max | SUCCESS → itself | structural sentinels |
| Any version/variant nibble | SUCCESS | informative, never gates |
| Wrong length / bad charset | MISSING | grammar claims nothing |
| No 32-hex/36-char runs | MISSING | no grammar recognized |
| Two distinct valid in one slice | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity, use segmentation |
| IBAN-shaped 32-hex | UUID SUCCESS; IBAN candidate INVALID | cross-grammar overlap preserved, validation decides |
| `UUID:`-labeled prose | MISSING (v1) | DEFERRED to extra_grammars (§13.11) |

---
## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)
```bash
uv run python tools/new_capability.py UUID --name uuid --authority "IETF" --spec-name "RFC 9562" --spec-url "https://www.rfc-editor.org/rfc/rfc9562" --publication-year 2024
```
Creates 13 files + one edit: paxman/capabilities/UUID/{notation,contract,capability,grammar/*,rules/*}, tests stubs, paxman/capabilities/__init__.py wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance (RFC 9562 — the only one). No second file needed.

### 10.2 Contract & grammar wiring
- get_grammars() returns [UUIDRecognitionGrammar], active_grammars omitted (no feature gates); grammar carries name `uuid_recognition` and non-empty semantics

### 10.3 Cross-cutting invariants (fail review if violated)
- No # type: ignore / # noqa / # pyright: ignore in paxman/ source
- No cross-capability imports (import only from paxman.core, import-linter enforced)
- No output_format token in any paxman/capabilities/*/rules/ module (source-scan)
- @dataclass(frozen=True, slots=True) notation; @dataclass(frozen=True) without slots contracts
- Deterministic by construction: same input + contract + library snapshot → same output

---
## 11. Recommended File Layout (mirrors ISSN and IBAN)

```
paxman/capabilities/UUID/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── uuid_recognition.py
└── rules/
    ├── __init__.py
    └── rfc_9562_ed2024.py     # Section 4-uuid-format (PARSER, always-active)
```

No `rules/data/` (no registry to vendor) and no `grammar/data/` (infinite value space — regex, not lexicon).

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- Grammar tests (`test_grammar.py`): `test_canonical_span`, `test_uppercase_fold`, `test_bare_32_span`, `test_braced_span_includes_braces`, `test_urn_span_includes_prefix`, `test_nil_span`, `test_max_span`, `test_33hex_missing`, `test_37char_missing`, `test_glued_left_missing`, `test_glued_right_missing`, `test_two_mentions_both_claimed`, `test_empty_missing`, `test_name`, `test_semantics`, `test_single_value` — one positive vector per §2.1 RECOGNIZE form
- Rule tests (`test_rules.py`): `test_valid_hyphenated`, `test_valid_bare_folded`, `test_valid_nil_max`, `test_version_nibble_informative` (v0/v9 structures still match), `test_normalize_exact_lowercase_hyphenated`, provenance attributes (IETF/RFC 9562/May 2024/specification/2024), `test_name_convention`, `test_strategy_parser`
- Capability tests (`test_capability.py`, `test_notation.py`, `test_contract.py`): notation frozen/hashable/slots + `version` values (`1`–`8`, `nil`, `max`); wiring counts (1 grammar, 1 rule); `format_value` round-trips compact→hyphenated→compact, braced→hyphenated, urn→hyphenated (each re-enters — ADR-0010); `create_contract` factories + `ContractError` on `output_format="upper"`
- Capability tests: notation frozen/hashable/slots, wiring counts, grammar/rule name conventions, format_value round-trips (compact/braced/urn re-enter — ADR-0010), create_contract factories
- Integration: MISSING/INVALID/SUCCESS/AMBIGUOUS + MultipleMentionsError, `_clean_registry` fixture, determinism/VersionStamp, span-bearing match, dedup; IBAN-overlap vector asserting UUID SUCCESS alongside IBAN INVALID
- Property tests (hypothesis): random 128-bit → hyphenated must canonicalize to itself; random strings → MISSING with high probability; carrier variants identical; format_value round-trip per offered format
- Consistency test: grammar semantics covered by Rule.target_semantics (no registry → membership-style consistency N/A; assert instead that every §2.1 RECOGNIZE form has a grammar test)
- Presentation purity: output_format source scan
- Real vectors: RFC Fig 1 `f81d4fae-7dec-11d0-a765-00a0c91e6bf6`, Python docs uuid3/uuid5-DNS (`6fa459ea-ee8a-3ca4-894e-db77e160355e`, `886313e1-3b8a-5372-9b90-0c9aee199e5d`), uuid4 `16fd2706-8baf-433b-82eb-8c7fada847da`, NIL, MAX

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT | `hyphenated` (lowercase) | Python `str()` form; most portable across DBs/logs; ISSN-hyphenated precedent |
| 2 | Single grammar vs N grammars | Single `uuid_recognition`, dashed\|bare alternation + optional carriers | avoids cross-grammar spurious AMBIGUOUS; ORCID precedent |
| 3 | Version/variant strictness | Informative only, never gates | RFC ABNF constrains nothing; generation≠storage (§2.1-6); validator `loose` agrees |
| 4 | Grammar length strictness | Exactly 32-hex / 36-char / 38 / 45 via groups, never 31/33/35/37 | keeps grammar cheap and definitive |
| 5 | Case/brace/URN normalization in grammar vs rule | Grammar folds/strips; rules see lowercase compact only | syntax not semantics |
| 6 | Nil/Max special-casing | SUCCESS by structure, no dedicated rule | sentinels are values; Python has NIL/MAX constants |
| 7 | Single PUBLICATION | Yes — RFC 9562 only | no second authority exists |
| 8 | single_value for batch | True initially, segmentation for multi | shipped precedent |
| 9 | Space/dot separator tolerance | Unsupported (REJECT) | unattested anywhere |
| 10 | Brace/URN span inclusion | Include carrier in raw_text span, notation carrier-free | ORCID label/URI precedent |
| 11 | Label-prefixed prose (`UUID:`/`GUID:`) | DEFER via extra_grammars pending corpus evidence | plausible but unattested; discovering post-ship costs a grammar rewrite either way, extra_grammars bounds it |

---
## 14. Ambiguity Analysis (Paxman-specific)

- No inherent UUID-vs-UUID ambiguity — fixed 128-bit structure eliminates positional ambiguity Date exhibits; two distinct in one slice is authorial choice, segmentation intended.
- UUID-vs-IBAN shape overlap is not lexical ambiguity — a 32-hex LLDD run is claimed by both grammars, but IBAN MOD97 rejects while UUID structure accepts; without the IBAN rule it would false-SUCCESS there, which is why validation (not grammar) decides. Cross-grammar overlap stays observable per `_dedup_spans`.
- UUID vs ORCID/MAC/ISBN/Phone is length discrimination — 32/36/38/45 vs 16/12/13/≤15 disjoint by exact length; no competition possible.
- Carrier vs identity is not ambiguity — braced/bare/URN are presentations of one value (dedup to single canonical), never distinct identities; unlike BIC XXX branch or ISBN-10→13 there is no equivalence mapping to maintain.
- Staleness is not ambiguity — no registry means no snapshot drift; Provenance.version pins the spec edition only.

---
## 15. URL Reference (authoritative, fetched 2026-09-16)

| Claim | URL | Kind |
|-------|-----|------|
| RFC 9562 (current, Standards Track, May 2024, obsoletes 4122) | https://www.rfc-editor.org/rfc/rfc9562 | primary |
| RFC 9562 plaintext (ABNF §4, Tables 1–2, §§5.1–5.10, App A) | https://www.rfc-editor.org/rfc/rfc9562.txt | primary |
| RFC 9562 status/errata | https://www.rfc-editor.org/info/rfc9562 | primary |
| RFC 4122 (obsoleted, v1–5) | https://www.rfc-editor.org/rfc/rfc4122 | primary (lineage, via 9562 header) |
| X.667 alignment (via RFC §1) | https://www.rfc-editor.org/rfc/rfc9562 (Section 1) | primary |
| Python uuid docs (tolerance, vectors, NIL/MAX, v6–v8) | https://docs.python.org/3/library/uuid.html | primary |
| validator.js isUUID (per-version/nil/max/loose/all) | https://github.com/validatorjs/validator.js/blob/master/src/lib/isUUID.js | primary |
| python-stdnum has no UUID module (ecosystem gap) | https://api.github.com/repos/arthurdejong/python-stdnum/contents/stdnum | primary (negative) |
| IBAN/BIC research precedents | docs/development/research/2026-08-22-iban-canonicalization.md, docs/development/research/2026-08-23-bic-canonicalization.md | primary |
| ISSN/ORCID precedents | docs/development/research/2026-08-21-issn-canonicalization.md, docs/development/research/2026-08-23-orcid-canonicalization.md | primary |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary |
| Shipped precedent (ORCID/MAC/ISBN) | paxman/capabilities/ORCID/grammar/orcid_recognition.py, paxman/capabilities/MacAddress/grammar/mac_address_recognition.py, paxman/engine/orchestrator.py:_dedup_spans, paxman/core/domain.py:Rule | primary |

---
## 16. Evidence Completion — Resolved

This report's UUID-specific authoritative evidence has been fetched and cited (2026-09-16):
- [x] RFC catalogue entry: RFC 9562 (Standards Track, current, May 2024) superseding RFC 4122 plus DCE/X.667 lineage; version lifecycle publication_year 2024
- [x] RA and Directory provenance: none exists — recorded as negative (§5.5) with RFC §1 cite
- [x] Structure: 128-bit, hex-and-dash ABNF, variant Table 1, version Table 2, Nil §5.9, Max §5.10
- [x] No checksum proved (RFC section silence + structural-only validators, two sources)
- [x] Country nuance: N/A — no geography (recorded, not skipped)
- [x] Ecosystem regex consensus: validator.js verbatim + Python stdlib tolerance + stdnum gap
- [x] Recognition-surface inventory complete (§2.1): every attested written form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form
- [x] Wild input shapes validated (§2.2, 18 rows) against spec + validators
- [x] Label scope decision (§13.11: DEFER with rationale)
- [x] Branch/XXX equivalence decision: N/A — every value its own identity (§14, recorded)
- [x] Flag semantics decision: N/A — version/variant informative (§13.3, recorded)
- [x] Directory liveness scope decision: N/A — no directory (§5.5, recorded)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ISSN, IBAN, ORCID and MacAddress Capabilities Teach UUID (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

1. **Grammar strips, rule validates, capability formats.** Every shipped fixed-shape capability strips separators and folds case in the grammar emit fn (`_orcid_notation` uppercases + regroups; `_mac_notation` filters `isascii()/isalnum()` + uppercases; `_isbn13_notation` keeps `0123456789`), rules receive normalized notation, `format_value` re-adds presentation. UUID follows identically.
2. **One file per provenance, one class per section.** ORCID's `iso_27729_ed2024.py` holds two PARSER classes (structure + MOD 11-2) under one PUBLICATION; UUID's `rfc_9562_ed2024.py` holds one (`Section 4-uuid-format`) — same shape, smaller content.
3. **No `output_format` in rules, ever.** ORCID `normalize()` always returns hyphenated; `format_value` selects `notation.compact`/`notation.hyphenated`/URI prefix. UUID mirrors with `notation.compact`/`hyphenated`/`urn`.
4. **Single grammar with alternation avoids spurious AMBIGUOUS; cross-grammar containment is preserved.** ORCID dashed|compact in one pattern; MacAddress 8-branch alternation longest-first; engine `_dedup_spans` (orchestrator.py:456-488) is within-grammar longer-wins while cross-grammar overlap stays observable — the exact machinery the UUID/IBAN 32-hex overlap relies on.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for UUID row 5. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the ORCID precedent. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
