# DOI Canonicalization Research — paxman-python

**Date:** 2026-09-18
**Scope:** Primary-source survey of the Digital Object Identifier system (ISO 26324:2025, DOI Handbook, Handle System RFC 3650, Crossref display guidelines), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `DOI` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO 26324:2025 + 2022 catalogue pages (fetched 2026-09-18), doi.org What-is-a-DOI + Handbook landing (fetched 2026-09-18), RFC 3650 full text (fetched 2026-09-18), RFC 4452 `info`-scheme text (fetched 2026-09-18), Crossref March-2017 display guidelines (fetched 2026-09-18), validator.js `isDOI.js` 404 + stdnum dir listing proving no `doi.py` (fetched 2026-09-18), Wikidata P356 URL-match pattern P8966 + P1793 format + P7470 URN formatter (secondary, fetched 2026-09-18), DataCite DOI basics + mEDRA FAQ case rules (RA sources, fetched 2026-09-18), scholid structural-only validator (secondary, fetched 2026-09-18), plus shipped-capability precedent surveyed verbatim from the tree (ISBN/ISSN/IBAN/ORCID/MacAddress, `paxman/engine/orchestrator.py`, `paxman/core/domain.py`). Repo state: `dev @ 3ca44a0` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN (2026-08-21), IBAN (2026-08-22), BIC (2026-08-23), ORCID (2026-08-23), UUID (2026-09-16) research precedents.

---

## Executive Summary

DOI is a **strong** fit for a Paxman capability: it has an unambiguous canonical form (**bare `10.`-prefixed name, lowercase**), a stable single-part standard (**ISO 26324:2025**, Edition 3, current; DOI Foundation + Registration Agencies as the social infrastructure), a well-understood human-readable presentation (resolvable `https://doi.org/` link, presentation-only), and an ORCID-shaped carrier surface (bare/label/URI forms). The domain mirrors Paxman's value proposition for ORCID/ISBN: recognizing tolerant human surface, validating strictly against structure, returning canonical compact value with provenance. **There is no checksum**: the Handbook states affirmatively 'The DOI System does not itself make use of check digits. This is deliberate' (§4.3.5, PDF-confirmed) — unlike ISBN/ISSN/ORCID/IBAN/LEI, prefix shape + suffix presence is all there is (per-application EIDR checksums excepted, and ignored by the PARSER); proved in §5.1 three ways.

Key findings that shape the design:
1. **Canonical form is bare lowercase `10.registrant/suffix`** (Crossref: display as full URL, but the *identifier* is the `10.` name; MILESTONE row 11 already prescribes strip-`doi:` + lowercase). **PDF-confirmed 2026-09-18**: Handbook Ch.3 'Case Insensitivity of the DOI Name' makes equivalence Basic-Latin-only with no normalization — so the v1 fold is ASCII-only (`A–Z`→`a–z`), non-Latin code points byte-preserved, no NFC/NFD anywhere.
2. **One grammar**, RegexStage with bare core + resolver-URL/legacy-`doi:`/label carrier groups (ORCID precedent) — avoids cross-grammar containment spurious AMBIGUOUS.
3. **Validation is PARSER-only, single rule** — no vendored registry is feasible (~479M names per the Wikidata P356 count of 478,744,969 at 2026-06-30, sourced to doi.org; Handbook Preface Sept 2025: 'over 300 million DOI names' resolved 'over 12 billion times a year'; live APIs are network, breaking determinism-by-snapshot); ADR-0012 vacuity exception (§5.4), same standing as UUID.
4. **Carriers resolve, modern display is canonical** — lowercase `doi:` is the Foundation's prescribed visual form (Handbook §4.4.1: 'should be preceded by a lowercase `doi:`', 'not part of the DOI name value'); uppercase `DOI:`, `http://dx.doi.org/` (deprecated per Handbook §4.4.4/§6.3.1 footnote, still resolving per Crossref 'indefinitely'), and `http://doi.org/` all still resolve but render canonically as `https://doi.org/`; shortDOI (`10/xxxx`) is NOT a DOI (Handbook §6.5 primary: 'not themselves DOI names', plus Crossref) → REJECT; proxy URN-colon form (`https://doi.org/urn:doi:10.123:456`, Handbook §6.3.1) → DEFER (v1).
5. **Provenance is a single publication** (ISO 26324:2025) — one rule file, one PUBLICATION constant, one Rule class (HOW_TO_ADD_NEW_CAPABILITY.md Step 5). The Handbook (2025; imprint Sept 2025; version-of-record PDF read via local markdown conversion 2026-09-18) is now fetched primary background for namespace syntax (Ch.3), the case rule, check-digit negation (§4.3.5), carriers (§4.4/§6.3.1), and shortDOI (§6.5); the Handle RFC stays cited background.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---
## 1. Target User

| Persona | Why they need DOI canonicalization | Typical context |
|---|---|---|
| Researcher/librarian | Reference lists mix bare names, `doi:` prefixes, and resolver links for one paper | Normalizing bibliographies to canonical links |
| Publisher tooling | Crossref deposits and landing pages must emit the canonical display form | Validating `https://doi.org/10.xxxx` rendering in HTML/PDF pipelines |
| Support/on-call | Users paste truncated, prefixed, or legacy-`dx` links from old PDFs | Pasting into lookup tools and runbooks |
| Data engineer | Citation graphs join keys arriving as URLs from one source, bare names from another | Deduplicating edges keyed by work id |

**User-visible contract:** The caller supplies raw human text and a contract; Paxman returns one canonical bare DOI name (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors ORCID ergonomics, but the canonical default is the **bare `10.` name** (not a URI), with the resolver URL offered.

---
## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Bare name | `10.1038/nature12345` | doi.org (prefix/suffix split, `10.1000/182` example) | canonical | RECOGNIZE | main pattern body |
| Bare uppercase/mixed | `10.1038/NATURE12345` | Handbook Ch.3 'Case Insensitivity' (primary, PDF-confirmed: Basic-Latin equivalence, Ex.1 `10.5594/SMPTE.ST2067-21.2020` ≡ `10.5594/sMPTE.sT2067-21.2020`); Wikidata P356 all-caps characteristic (`10.1371/JOURNAL.PONE.0029797`); DataCite/mEDRA (RAs, insensitive) | common | RECOGNIZE | ASCII-only fold + lowercase canonical |
| Resolver URL (current) | `https://doi.org/10.1038/nature12345` | Crossref display guidelines Mar 2017 (canonical display) | official display | RECOGNIZE | optional host group (ORCID host precedent) |
| Resolver URL http | `http://doi.org/10.1038/nature12345` | Crossref (works indefinitely) | legacy-common | RECOGNIZE | scheme-tolerant host group |
| Legacy dx host | `http://dx.doi.org/10.1038/nature12345` | Crossref (dropped 2017, still resolves) | legacy | RECOGNIZE | `dx.`-tolerant host group |
| `www.` host variant | `https://www.doi.org/10.1038/nature12345` | Wikidata P8966 URL-match pattern `(?:dx\.\|www\.)?doi\.org` | rare | RECOGNIZE | `www.`-tolerant host group |
| `doi:` label prefix | `doi:10.1038/nature12345` | Handbook §4.4.1 visual media (primary: 'should be preceded by a lowercase `doi:`', 'not part of the DOI name value', e.g. `doi:10.1006/jmbi.1998.2354`); Crossref-deprecated but resolving | common (Foundation-prescribed; Crossref-deprecated) | RECOGNIZE | fused label `[\s:-]+` (ISBN label precedent) |
| `DOI:` label prefix | `DOI: 10.1038/nature12345` | uppercase variant of the §4.4.1 visual form (folded at match) | legacy-common | RECOGNIZE | same fused label, folded |
| `info:doi/` URI namespace | `info:doi/10.1038/nature12345` | `info` scheme + registry mechanism per RFC 4452 (primary); `info:doi/$1` namespace formatter on Wikidata P356; older XML repository exports | rare/legacy | RECOGNIZE | optional `info:doi/` carrier group |
| `urn:doi:` URN carrier | `urn:doi:10.1038/nature12345` | Handbook §4.4.3 URN form (primary: 'doi' namespace per the DOI Namespace Registration); Wikidata P7470 formatter corroborates | rare/legacy | RECOGNIZE | optional `urn:doi:` carrier group |
| Proxy URN-colon form | `https://doi.org/urn:doi:10.123:456` | Handbook §6.3.1 NOTE (primary: proxy 'understand[s] the substitution of a colon in place of the initial slash'; multi-slash suffixes must hex-encode as `%2F`, e.g. `10.123/456ABC/zyz` → `…:456ABC%2Fzyz`) | rare/workflow | DEFER (v1) | future carrier group (colon→slash mapping + `%2F` rule); documented negative test |
| Bracketed/quoted URL | `[https://doi.org/10.1038/nature12345]` | reference lists, markdown | common | RECOGNIZE | boundary-exterior punctuation (no group needed) |
| shortDOI | `10/gf2p3c` via `https://doi.org/10/gf2p3c` | Handbook §6.5 (primary: 'shortDOIs are not themselves DOI names and therefore do not conform to the ISO standard syntax'; 'can only be created for an existing DOI name'); Crossref ('not really actual DOIs', recommends against) | rare/discouraged | REJECT (v1) | documented negative test |
| Bare suffix only | `nature12345` | unresolvable without prefix | invalid | REJECT | no prefix → no claim (MISSING) |
| Truncated (`10.1038/`, `10.103`) | cut-paste damage | length/shape guard | invalid | REJECT | `/` + suffix required |
| Non-`10.` handles | `20.500.1234/abc` | Handle namespace (non-DOI authorities exist); Handbook §4.3.2 reserves future non-`10.` directory indicators ('usually equal to `10`', others 'may be used in the future') | out of scope (revisit if allocated) | REJECT | `10.` literal gate |
| Whitespace inside | `10.1038 / nature12345` | unattested | invalid | REJECT | no intra-name whitespace |

Silence audit: v1 answers every spec-, RA-, or validator-attested form (bare/case/URL incl. `www.` variant/legacy dx+http/label incl. `urn:doi:`/`info:doi/` carriers); cuts (shortDOI, proxy URN-colon form [DEFER v1], suffix-only, non-`10.` handles incl. future directory indicators, inner whitespace) are dispositioned here and in §13 rows 11–12.

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical bare | `10.1038/nature12345` | Spec master form |
| 2 | Uppercase bare | `10.1038/NATURE12345` | fold, lowercase canonical |
| 3 | Dotted sub-registrant | `10.13003/5jchdy`, `10.64000/gyw3h-trd87` | `(?:\.\d+)*` prefix tail |
| 4 | Suffix with dots/slashes | `10.7774/cevr.2016.5.1.19` | suffix charset includes `.` |
| 5 | Suffix with `%2F` | `10.xxxx/a%2Fb` | literal `%2F` tolerated (Wikidata consensus) |
| 6 | Resolver https | `https://doi.org/10.1038/nature12345` | canonical display carrier |
| 7 | Resolver http/dx/www | `http://dx.doi.org/10.1038/nature12345`, `https://www.doi.org/10.1038/…` | legacy + `www.` host variants |
| 8 | `doi:` fused label | `doi:10.1038/nature12345` | `[\s:-]+` separator |
| 9 | `DOI:` spaced label | `DOI: 10.1038/nature12345` | folded label + space |
| 10 | Trailing punctuation | `…nature12345.` / `…)` | sentence punctuation excluded from span |
| 11 | Trailing annotation | `10.1038/nature12345 (2026)` | span covers name only |
| 12 | Multiple per line | two DOIs, one line | 2 matches; single_value → MultipleMentionsError |
| 13 | Quoted/bracketed | `"10.1038/…"`, `[https://doi.org/…]` | inside punctuation |
| 14 | X-glued runs | `x10.1038/…`, `…12345x` | word-boundary guards → MISSING |
| 15 | Missing suffix | `10.1038/` | `/` + non-empty suffix required → MISSING |
| 16 | Missing slash | `10.1038nature12345` | no claim → MISSING |
| 17 | Wrong directory | `20.500.1234/abc` | `10.` gate → MISSING |
| 18 | shortDOI shape | `10/gf2p3c` | REJECT per §2.1 (registrant too short + policy) |
| 19 | `urn:doi:` URN carrier | `urn:doi:10.1038/nature12345` | rare URN form (Handbook §4.4.3 primary); strip carrier, same canonical |
| 20 | Proxy URN-colon form | `https://doi.org/urn:doi:10.123:456` | DEFER v1 (colon-mapping + `%2F` rule need their own carrier group); no claim → MISSING |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| Wikidata P356 URL-match pattern P8966 + P1793 format + Crossref-regex clarifications (secondary, fetched 2026-09-18) | P8966 `^https?://(?:dx\.\|www\.)?doi\.org/(10\.[0-9]{4,}(?:\.[0-9]+)*(?:\/\|%2F)(?:(?![\"&'])\S)+)`; P1793 `10\.\d{4,9}/.+`; Gilmartin (Crossref) modern `(?i)10\.\d{4,9}/[-._;()/:A-Z0-9]+` (≈74.4M/74.9M Crossref DOIs), early `(?i)10\.\d{4,9}/[^\s]+` — registrant lower bound 4 in P8966 (unbounded above) vs 4–9 in P1793/scholid/Gilmartin, which the v1 grammar follows; dotted registrant tail; `/` or literal `%2F` separator; quoteless non-space suffix |
| scholid `is_scholid()` DOI (secondary, fetched 2026-09-18) | `^10\.\d{4,9}/\S+$` — "DOI validation is structural only. There is no checksum. Registry existence is not checked." Prefix `10.` + 4–9-digit registrant + `/` + non-whitespace suffix; suffix "Case-sensitive in theory" |
| validator.js | **No `isDOI` module** (404 on `src/lib/isDOI.js`, 2026-09-18) — same gap class as stdnum/uuid |
| python-stdnum | **No `doi.py`** (dir listing: `isbn/isin/issn/lei` present, doi absent, 2026-09-18) — ecosystem gap; adjacent `isin.py`/`lei.py` are check-digit analogues only |
| Crossref display (primary RA) | canonical `https://doi.org/10.xxxx/xxxxx`; never `doi:`/`DOI:`-prefixed; never `dx.`; HTTPS |
| RFC 3650 §3 (primary) | `<Handle> ::= <Naming Authority> "/" <Local Name>`; printable UCS-2/UTF-8; case-sensitivity per-service (default sensitive) |

**Normalization contract (ORCID/ISBN pattern):**
```python
core = re.sub(r"^(?:https?://(?:dx\.|www\.)?doi\.org/|doi:[\s:-]*)?", "", raw, flags=re.IGNORECASE)
core = re.sub(r"^(?:info:doi/|urn:doi:)", "", core, flags=re.IGNORECASE)
prefix, _, suffix = core.partition("/")
canonical = f"{_ascii_lower(prefix)}/{_ascii_lower(suffix)}"  # ASCII-only fold per Handbook case rule (§4.2 def, §13.3); non-Latin preserved, no normalization
# then validate: prefix ^10\.\d{4,9}(\.\d+)*$ + non-empty suffix, no whitespace/quotes
```

**Percent-encoding rule:** percent-escapes are retained literally, never decoded. Decoding `%2F` would inject a structural `/` indistinguishable from the prefix/suffix split, breaking deterministic hashing. Primary footing: Handbook §4.7 percent-encodes prefix and suffix *separately* then joins with `/` (so a suffix `/` is *authored* as `%2F`), and §6.3.1 requires multi-slash suffixes in the URN-colon form to 'be hex-encoded rather than replaced with a colon' (`10.123/456ABC/zyz` → `…:456ABC%2Fzyz`). Retaining also matches the Wikidata literal-`%2F` consensus (P8966) and the UUID POSIX-sign-as-authored precedent. Pinned by test (`10.xxxx/a%2Fb` canonicalizes to `10.xxxx/a%2fb` — hex letters ASCII-folded like all Basic Latin, never decoded — and re-enters byte-identical). Layering note: the DOI *proxy* decodes before resolution (Handbook §6.3.1 step 2); Paxman's canonicalization layer does not — determinism-by-snapshot hashes the authored string.

### 2.3 What input is NOT a DOI mention
- Non-`10.` handles (`20.500.1234/abc`) — MISSING at grammar (`10.` literal gate)
- Suffix-only strings, bare words — MISSING (no grammar claims)
- shortDOI (`10/xxxx`) — MISSING by design (registrant `\d{4,9}` gate doubles as the policy)
- ISBN/ISSN digit runs (no `10.`+slash shape), Phone runs (suffix letters/slash break digit runs) — MISSING vs INVALID boundary (§9)

### 2.4 Single-mention vs multi-mention input
Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct DOIs → `MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS`.

---
## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — prefix/suffix decomposition
```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class DOINotation:
    """DOI prefix/suffix split; canonical is ASCII-folded prefix + '/' + ASCII-folded suffix."""
    prefix: str       # e.g. "10.1038" — 10.<registrant>, case-folded
    suffix: str       # e.g. "nature12345" — as-written (see §13.3)
    canonical: str    # prefix + "/" + suffix, the default-format value
```

**Considered alternative — single field `compact` only:** rejected. The split mirrors IBAN (`country_code`/`check_digits`/`bban`/`compact`): the prefix is the rule-routing key (registrant shape validated separately from suffix presence), and `canonical` pre-computation keeps `format_value` selection-only (ORCID precedent).

**Invariants the grammar enforces (before rules):**
- prefix matches `10\.\d{4,9}(\.\d+)*`, ASCII-folded (`A–Z`→`a–z` only — never `str.lower()`/`casefold()`, which would conflate Handbook-distinct non-Latin pairs like `Á`/`á`)
- suffix is non-empty, no whitespace, no `"'&` (Wikidata consensus; Handbook Graphic-type control exclusion falls out of the no-whitespace rule); ASCII-folded; percent-escapes retained literally, never decoded (§2.2 rule)
- no Unicode normalization is performed anywhere (NFC/NFD forbidden — Handbook: 'no normalization, as defined in ISO/IEC 10646, is performed')
- canonical is `prefix + "/" + suffix`; carriers (scheme/host/label) never survive

### 3.2 Why not carry resolver host or label in the notation
Hosts, schemes, and `doi:` labels have **no lexical significance** for validity — presentation is `Capability.format_value()` only.

### 3.3 Suffix case handling (PDF-confirmed)
Suffix case policy is §13.3's confirmed row: v1 canonicalizes via ASCII-only lowercase fold over the full string (MILESTONE row-11 + APA + URL-safety) while matching case-insensitively per the Handbook equivalence rule. Non-Latin suffix case is preserved byte-identical (`Á…` ≠ `á…`); no NFC/NFD normalization. The DataCite/Wikidata upper-casing counter-evidence is weighed in §13.3 and concerns registry storage/display, not resolution identity.

---
## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex with optional carrier groups
Per HOW_TO_ADD_NEW_GRAMMAR.md, DOI has a fixed `10.`-anchored shape with a small documented carrier set, so **RegexStage** (legacy pipeline, ORCID precedent) is correct. Lexicon is wrong (unbounded suffix space); scanner is unnecessary.

### 4.2 Reference pattern (ORCID verbatim precedent, adapted)
```python
import re
from paxman.capabilities.DOI.notation import DOINotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

_DOI_PREFIX = r"10\.[0-9]{4,9}(?:\.[0-9]+)*"
_DOI_SUFFIX = r"(?:(?![\"&'])\S)+"
_DOI_LABEL = r"(?:(?ai:DOI)[\s:-]+)?"
_DOI_HOST = r"(?:(?ai:https?://(?:dx\.|www\.)?doi\.org)/)?"
_DOI_INFO = r"(?:(?ai:info:doi)/)?"
_DOI_URN = r"(?:(?ai:urn:doi):)?"
_DOI_BODY = rf"{_DOI_LABEL}{_DOI_HOST}{_DOI_INFO}{_DOI_URN}(?P<core>{_DOI_PREFIX}/{_DOI_SUFFIX})"
_DOI_PATTERN = (
    BoundaryGuard.word_only().lookbehind + _DOI_BODY + BoundaryGuard.word_only().lookahead
)

def _ascii_lower(value: str) -> str:
    """Basic-Latin-only fold: U+0041–U+005A → U+0061–U+007A; all else preserved.

    Handbook Ch.3 'Case Insensitivity' (PDF-confirmed 2026-09-18): equivalence only,
    Basic-Latin only, no normalization. Full-Unicode str.lower()/casefold() would wrongly
    conflate e.g. U+00C1/U+00E1, which the Handbook declares NOT equivalent.
    """
    return "".join(chr(ord(ch) + 32) if "A" <= ch <= "Z" else ch for ch in value)


def _doi_notation(match: re.Match[str]) -> DOINotation:
    core = match.group("core")
    prefix, _, suffix = core.partition("/")
    prefix, suffix = _ascii_lower(prefix), _ascii_lower(suffix)
    return DOINotation(prefix=prefix, suffix=suffix, canonical=f"{prefix}/{suffix}")

class DOIRecognitionGrammar(PipelineGrammar[DOINotation]):
    name = "doi_recognition"
    semantics = "doi_recognition"
    single_value = True
    pre = StandardPre[DOINotation](empty_guard=True)
    regex = RegexStage[DOINotation](pattern=_DOI_PATTERN, notation_fn=_doi_notation)
```
*Notes on fidelity vs ORCID:* single grammar, bare core + carrier prefixes (re-entry: offered `url` output re-recognized); suffix `\S+` minus quotes is the Wikidata-P8966-measured consensus with the 4–9-digit registrant bound per P1793/scholid/Gilmartin; **trailing sentence punctuation needs explicit handling**: unlike UUID's hex-only charset (dots never match), DOI suffixes legitimately contain dots (`10.7774/cevr.2016.5.1.19`), so a greedy `\S+` would swallow a sentence-final `.`/`)` and the `word_only` lookahead (`(?!\w)`) would wave it through. The pattern therefore terminates the suffix on a lookahead class — `(?=[\s\"&')\].,;:!?]|$)` — with an explicit test per terminator (`…12345.` → span excludes the dot; `…12345)` → excludes the paren; interior dots retained). **Form-coverage traceability:** bare→body, resolver-url→host group, legacy-dx + `www.`→host variants, doi-label→label group, `urn:doi:`/`info:doi/`→carrier groups, upper/mixed→ASCII-only fold (Basic Latin; non-Latin preserved, no normalization); shortDOI→nothing (REJECT by the 4–9 bound + policy, now Handbook-primary §6.5); proxy URN-colon form→nothing (DEFER v1, own carrier group); suffix-only→no element (REJECT). Homoglyph/lookalike code points (U+002D vs U+2212 vs U+2013; precomposed vs decomposed `á`) are distinct names — no confusable-folding (Handbook §4.4.1 NOTE + no-normalization rule).

**One grammar, not two:** bare vs URL-carrier in one pattern avoids cross-grammar containment spurious AMBIGUOUS (the URL string contains the bare name; one grammar keeps `_dedup_spans` longer-wins deciding carrier-inclusive span vs bare inner span deterministically).

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)
- Grammar emits span-bearing RecognitionMatch, half-open [start,end), raw_text == text[start:end] (span includes carrier prefix/host when present — ORCID label/URI precedent)
- RegexStage loops re.finditer, builds RecognitionMatch, Stages must not mutate text
- Engine owns within-grammar containment dedup (longer wins: carrier-inclusive beats bare inner) and total recognition ordering
- Candidate dedup (value, recognition_rule, validation_rule) after validation

### 4.4 Guard boundaries against sibling grammars
| Grammar | Chars | Risk | Guard outcome |
|---------|-------|------|---------------|
| DOI bare (`10.1038/…`) | digits/dots/slash/letters | URL: resolver-URL forms ARE absolute URIs — **overlap real** (same class as ORCID URIs; no guards either way, per-capability resolution, caller disambiguates) | documented, not solved |
| DOI bare | `10.1038/…` | Phone E.164 (≤15 digits)? Suffix letters + `/` break digit runs; pure-numeric suffix (`10.1000/182`) — 10.1000/182: digits+dots+slash, no leading `+`, exceeds national shapes | disjoint in practice; suite pins `10.1000/182` clean |
| DOI bare | `10.7774/…` | Money (`$500`)? No currency symbol | disjoint by shape |
| DOI bare | `10.03…` | Date (`01/02/2026`)? Date needs month/day/year digit groups; DOI suffix letters break it; all-digit short DOI (`10.1000/182`) vs short dates — slash positions differ (`10.1000/182` has one slash; dates need two) | disjoint by shape; suite pins |
| DOI `doi:` label | `doi:10.…` / `urn:doi:10.…` | ISSN `urn:`? Scheme-disjoint (`doi:`/`urn:doi:` vs `urn:issn:`) | disjoint by literal |

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)
- semantics = `"doi_recognition"` identity id; a future fused shortDOI variant (if policy flips) would carry a distinct id, never coalesce (different identity class per Crossref)

### 4.6 `single_value` — one mention per call vs batch processing
Recommendation: `single_value=True` (universal shipped precedent for fixed-shape identifiers), segmentation path for batches.

---
## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publisher | ISO (TC 46/SC 9, ICS 01.140.20) + DOI Foundation (social infrastructure) |
| Registration Authority | DOI Registration Agencies (Crossref, DataCite, mEDRA…) — mint under allocated prefixes; no single value directory vendored |
| Spec name | ISO 26324, Digital object identifier system |
| Current edition | **2025, Edition 3, Published** (2025-03-13) |
| Check character system | **None** — no check digit in any edition's scope (proved §5.1-negative below) |
| Country code reference | N/A (no geography in the value) |
| Related specs | DOI Handbook 2025 (imprint Sept 2025; PDF is version of record; full text read via local markdown conversion 2026-09-18 — Ch.3 namespace, Ch.5 resolution), RFC 3650 Handle (namespace tech), Crossref display guidelines Mar 2017 |

**Structure:** `prefix "/" suffix` (Handbook Ch.3 primary: 'ordered sequence of code points of the Graphic type … arranged in a DOI prefix and a DOI suffix separated by U+002F SOLIDUS'; 'no defined limit on the length of the DOI name, or of the DOI prefix or DOI suffix'). Prefix = directory indicator + registrant code (in-doc §4.3.2: directory 'usually equal to `10`' but others 'may be used in the future'; registrant is 'sequences of digits … separated by U+002E', always present when directory is `10`; e.g. `10.5594`, hypothetical `10.500.100`). Suffix = registrant-chosen Unicode sequence, unique per prefix, may embed another scheme's identifier (in-doc §4.3.3: `10.1000/123456`, `10.1038/issn.1476-4687`). The DOI name is 'an opaque string' (§4.8.2, Glossary) — no meaning inferred by inspection, backing the PARSER-only/no-registry scope (§5.4).
**Lineage table:**

| Edition | Date | Status | Note |
|---|---|---|---|
| ISO 26324:2012 | 2012-05 | Superseded | Edition 1 (MILESTONE row 11 cites this; stale) |
| ISO 26324:2022 | 2022-08 | Withdrawn 2025-03-13 | Edition 2, 18 pages |
| ISO 26324:2025 | 2025-03 | **Current, Published** | Edition 3, 17 pages; TC 46/SC 9; ICS 01.140.20 |

**No-checksum proof (affirmative primary + two independents):** (1) Handbook §4.3.5 states affirmatively: 'The DOI System does not itself make use of check digits. This is deliberate' — three reasons (embed existing identifier strings unaltered; per-resolution checksum cost; URL/TCP precedent) — with a scoped exception proving the rule: per-application checksums 'may be introduced as a rule of that application by the Registration Agency concerned' (EIDR: check char computed 'only over the DOI suffix', prefix validated separately by the registry). Paxman's PARSER therefore accepts EIDR-style suffixed names structurally and validates no digit — correct per spec. (2) The ISO abstracts (all three editions) scope the standard to 'syntax, description and resolution functional components' plus 'general principles for creation, registration and administration' — no validation-code component exists. (3) Ecosystem matching is purely structural: the Wikidata URL-match pattern (P8966) checks shape only, no stdnum/validator.js DOI module exists to mine a check algorithm from, and scholid states verbatim: 'DOI validation is structural only. There is no checksum. Registry existence is not checked.' Contrast ISBN/ISSN/ORCID/IBAN/LEI, all of which name an algorithm.
**Citation Details Table (for Provenance):**

| authority | spec_name | version | reference_url | lifecycle | publication_year | kind |
|---|---|---|---|---|---|---|
| ISO | ISO 26324 | 2025 | https://www.iso.org/standard/88862.html | active | 2025 | specification |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)
| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|----------------|-------------------|
| rules/iso_26324_ed2025.py | authority="ISO", specification_name="ISO 26324", kind="specification", reference_url="https://www.iso.org/standard/88862.html", version="2025", lifecycle="active", publication_year=2025 | Section 4-doi-syntax | Prefix shape + `/` + non-empty suffix (PARSER, always-active) |

Single publication → single file → single class. The Handbook/Crossref/Handle sources are cited background (carrier evidence), not validation authorities.

Each Rule[DOINotation] subclass declares six enforced metadata attributes at class-definition time (Rule.__init_subclass__):

```python
class Section4DOISyntax(Rule[DOINotation]):
    name = "Section 4-doi-syntax"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (DOI name syntax: prefix/suffix)"
    target_semantics = frozenset({"doi_recognition"})
    requires_features = frozenset()
```

### 5.3 What each rule does vs does not own
- matches() validates strictly (prefix regex + `/` + suffix charset, never raises); contract misconfigs caught in contract.__post_init__
- normalize() returns ASCII-folded bare `prefix/suffix` (Handbook equivalence rule; non-Latin preserved, no normalization), never reads output_format (CI purity scan), identical across rules for dedup
- RuleStrategy: PARSER (structure only). No LOOKUP_TABLE exists — ADR-0012 vacuity exception documented in §5.4 (same standing as UUID)

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)
No registrant/prefix registry is vendored: RAs allocate prefixes continuously (Handbook Preface: infrastructure 'used over 12 billion times a year to resolve over 300 million DOI names'), so any snapshot rots on arrival and live lookup is network (determinism-by-snapshot forbids it). Consequences: (a) no `include_*` registry flag; (b) PARSER-only rule set survives ADR-0012 via the vacuity clause, exactly UUID's standing; (c) prefix `10.` + registrant-digit shape is the entire authority check — a structurally valid but unallocated prefix (e.g. `10.99999/x`) reads SUCCESS, same class as UUID's unminted-but-storable values.

### 5.5 Assignment / registration authority & Registry content
RAs (Crossref/DataCite/…) mint under DOI-Foundation-allocated prefixes ('prefixes are created … as a block of sequential numbers that have no special meaning'; 'No reserved prefixes may be requested' — Handbook Ch.8 prefix-allocation policy) with community metadata; cadence is continuous. Scale (Handbook Preface, Sept 2025): 300M+ names, 12B+ resolutions/year. No directory is vendored (§5.4). This section records the negative so planners do not go looking.

---
## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)
Every contract MUST inherit CapabilityContract (never Contract directly). @dataclass(frozen=True) without slots.

```python
from dataclasses import dataclass, field
from typing import ClassVar
from paxman.core.capability_contract import CapabilityContract

@dataclass(frozen=True)
class DOIContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "doi"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"url"})
    capability_name: str = field(default="doi", init=False)
```

- DEFAULT_OUTPUT_FORMAT `"doi"` (bare `10.xxxx/suffix`, the identifier itself — MILESTONE row 11); OFFERED excludes default; resolved via base `__post_init__`; `create_contract()` fixed keyword-only common block, no capability-specific params (no registry flags exist)
- Presentational-only invariant, output_format never in rules
- Offered formats (re-enter — grammar answers the carrier):

| output_format | Renders | Example |
|---|---|---|
| *(default)* `doi` / `None` / `"default"` | Bare `10.` name | `10.1038/nature12345` |
| `url` | Resolver link | `https://doi.org/10.1038/nature12345` |

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)
```python
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.DOI.notation import DOINotation

class DOICapability(Capability[DOINotation]):
    name = "doi"
    def get_grammars(self) -> list[Grammar[DOINotation]]: return [DOIRecognitionGrammar()]
    def get_rules(self) -> list[Rule[DOINotation]]: return [Section4DOISyntax()]
    @staticmethod
    def create_contract(...) -> DOIContract: ...
    def format_value(self, value: str, output_format: str | None, notation: DOINotation) -> str:
        if output_format == "url":
            return f"https://doi.org/{notation.canonical}"
        return value
```

Registration via tools/new_capability.py (`DOI --name doi --authority "ISO" --spec-name "ISO 26324" --spec-url "https://www.iso.org/standard/88862.html" --publication-year 2025 --default-format doi`).

---
## 7. Validation — single structural level

### 7.1 Level 1 Generic structure (the only level)
Algorithm: prefix matches `^10\.\d{4,9}(\.\d+)*$`, exactly one mandatory `/` separator (the suffix itself may contain further `/` characters — split on the first `/` after the prefix; DataCite describes the display form as split by the first two slashes only because the proxy adds one), suffix non-empty without whitespace or `"'&`, printable code points only (Graphic-type). Formal core regex: `^10\.[0-9]{4,9}(?:\.[0-9]+)*/(?:(?![\"&'])\S)+$` plus a `str.isprintable()` gate (rejects Cc/Cf such as NUL, U+200B). Worked: `10.1038/nature12345` → valid; `10.1038` (no slash) → grammar never claims; `20.500.1234/abc` → grammar never claims (`10.` gate); `10/gf2p3c` → never claims (registrant too short — doubles as shortDOI policy); `10.1234567890/x` → never claims (registrant too long — 10 digits exceeds the 4–9 bound).

**Worked normalizations (grammar → rule → canonical):**

| Raw input | Grammar strips to core | Rule | Canonical |
|---|---|---|---|
| `DOI: 10.1038/NATURE12345` | `10.1038/NATURE12345` | structure ✓ | `10.1038/nature12345` |
| `https://doi.org/10.7774/cevr.2016.5.1.19` | `10.7774/cevr.2016.5.1.19` | structure ✓ | itself |
| `http://dx.doi.org/10.1000/182` | `10.1000/182` | structure ✓ | `10.1000/182` |
| `See 10.1038/nature12345.` | `10.1038/nature12345` (dot excluded) | structure ✓ | `10.1038/nature12345` |
| `doi:10.5594/SMPTE.ST2067-21.2020` | `10.5594/SMPTE.ST2067-21.2020` | structure ✓ (Handbook case Ex.1) | `10.5594/smpte.st2067-21.2020` |
| `10.26321/Á.GUTIÉRREZ…` vs `10.26321/á.gutiérrez…` | each as-written (ASCII fold preserves `Á`/`á`) | structure ✓ each, distinct values (Handbook case Ex.2: NOT equivalent) | two distinct canonicals, byte-preserved |

**Test/documentation prefixes:** `10.1000` is the IDF's own registrant prefix (doi.org's live examples; Handbook DOI `10.1000/182`) — not a reserved documentation block. There is no RFC-2606 analogue in the DOI namespace (PID Forum: no designated documentation prefix exists; DataCite's former test prefix `10.5072` was retired in 2019 after production misuse). Separately, Wikidata marks `10.5555/*` as private-use (`^(?!10\.5555/)` constraint: "intended for private use"). All three shapes are structurally valid and read SUCCESS like any shaped prefix (§5.4); test suites should prefer real registered examples (`10.1000/182`, §12 vectors) for positives, use clearly-synthetic suffixes under unallocated-shaped prefixes for synthetic vectors, and avoid minting new `10.5555/*` vectors.

### 7.2 What makes a DOI "valid" vs "registered" vs "resolvable"
- valid — prefix/suffix structure (the only gate; always-active PARSER)
- registered — unallocated-but-shaped prefixes read SUCCESS (§5.4; storable, like UUID's unminted values)
- resolvable — network property, never tested (no live lookup; determinism forbids it)

Like UUID valid-vs-storable, minus even the nibble semantics.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase bare | SUCCESS → same | canonical form |
| 2 | Uppercase bare (Basic Latin) | SUCCESS → ASCII-lowercase | grammar ASCII-folds; non-Latin capitals (`Á`) byte-preserved per Handbook (distinct from `á`) |
| 3 | Dotted sub-registrant | SUCCESS | `(?:\.\d+)*` tail |
| 4 | Suffix dots/slashes | SUCCESS | opaque suffix |
| 5 | `%2F` in suffix | SUCCESS | literal tolerance |
| 6 | Resolver https URL | SUCCESS, span includes URL | carrier group |
| 7 | Resolver http/dx/www hosts | SUCCESS → canonical bare | legacy + `www.` carriers |
| 8 | `doi:`/`DOI:` labels, `urn:doi:`/`info:doi/` carriers | SUCCESS, span includes carrier | fused label / carrier groups |
| 9 | Trailing `.`/`)` | SUCCESS, span excludes punct | span trim (impl detail) |
| 10 | Bracketed/quoted | SUCCESS | inside punctuation |
| 11 | Embedded in sentence | SUCCESS with span | word-boundary guards |
| 12 | Two distinct in one slice | AMBIGUOUS / MultipleMentionsError | segmentation |
| 13 | Missing suffix (`10.1038/`) | MISSING | suffix required |
| 14 | Missing slash | MISSING | no claim |
| 15 | Non-`10.` prefix | MISSING | `10.` gate |
| 16 | shortDOI shape | MISSING | registrant-length policy + Handbook §6.5 ('not themselves DOI names') |
| 17 | X-glued runs | MISSING | `(?<!\w)`/`(?!\w)` |
| 18 | Bare suffix only | MISSING | prefix required |

---
## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid bare (Basic-Latin any case) | SUCCESS → ASCII-lowercase bare | fold + structure (Handbook equivalence rule) |
| URL/label/URN carriers | SUCCESS (same canonical) | presentation-only dedup |
| Legacy dx/http/www carriers | SUCCESS (same canonical) | backwards-compatible carriers |
| Unallocated-but-shaped prefix | SUCCESS | storable, no registry (§5.4) |
| No `10.`/slash/suffix | MISSING | grammar claims nothing |
| shortDOI / proxy URN-colon / suffix-only | MISSING | policy gates (shortDOI: Handbook §6.5; URN-colon: v1 DEFER) |
| Two distinct valid in one slice | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity, use segmentation |
| `doi:`-looking non-DOI (`doi:foo`) | MISSING | prefix shape fails after label |
| Year-filtered (`year=2020`) | INVALID | rules are 2025, dropped |

---
## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)
```bash
uv run python tools/new_capability.py DOI --name doi --authority "ISO" --spec-name "ISO 26324" --spec-url "https://www.iso.org/standard/88862.html" --publication-year 2025 --spec-version "2025" --default-format doi
```
Creates 13 files + one edit: paxman/capabilities/DOI/{notation,contract,capability,grammar/*,rules/*}, tests stubs, paxman/capabilities/__init__.py wiring. TODO(scaffold) markers guide replacement.

> Note: scaffolder single --spec-name covers one provenance (ISO 26324 — the only validation authority). Handbook/Crossref/Handle stay cited background.

### 10.2 Contract & grammar wiring
- get_grammars() returns [DOIRecognitionGrammar], active_grammars omitted (no feature gates); grammar carries name `doi_recognition` and non-empty semantics

### 10.3 Cross-cutting invariants (fail review if violated)
- No # type: ignore / # noqa / # pyright: ignore in paxman/ source
- No cross-capability imports (import only from paxman.core, import-linter enforced)
- No output_format token in any paxman/capabilities/*/rules/ module (source-scan)
- @dataclass(frozen=True, slots=True) notation; @dataclass(frozen=True) without slots contracts
- Deterministic by construction: same input + contract + library snapshot → same output

---
## 11. Recommended File Layout (mirrors ISSN and IBAN)

```
paxman/capabilities/DOI/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── doi_recognition.py
└── rules/
    ├── __init__.py
    └── iso_26324_ed2025.py       # Section 4-doi-syntax (PARSER, always-active)
```

No `rules/data/` (no registry vendored) and no `grammar/data/` (unbounded suffix space — regex, not lexicon).

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- Grammar tests: bare/upper/carrier/legacy-label vectors, `10.1000/182` minimal shape, multiple matches, missing-suffix/slash/prefix negatives, X-glued negatives, empty, span invariants (carrier-inclusive spans, trailing-punct exclusion), name/semantics/single_value — one positive vector per §2.1 RECOGNIZE form; Handbook case vectors (`10.5594/SMPTE.ST2067-21.2020` ≡ `10.5594/sMPTE.sT2067-21.2020` same canonical; `Á…` vs `á…` distinct canonicals); precomposed-vs-decomposed (`U+00E1` vs `U+0061+U+0301`) non-coalescence; proxy URN-colon documented negative
- Rule tests: structural valid/variant/invalid, normalize exact ASCII-lowercase-bare, provenance attributes (ISO/ISO 26324/2025/specification/2025), name/strategy conventions, shortDOI-shaped rejection, EIDR-style suffixed check char accepted structurally (no digit validated, Handbook §4.3.5)
- Capability tests: notation frozen/hashable/slots, wiring counts (1 grammar, 1 rule), `format_value` round-trips (`url` output re-enters — ADR-0010), create_contract factories
- Integration: MISSING/INVALID/SUCCESS/AMBIGUOUS + MultipleMentionsError, `year=2020` → INVALID, `_clean_registry` fixture, determinism/VersionStamp, span-bearing match, dedup
- Property tests (hypothesis): registrant synthesis (`10.` + 4–9 random digits + optional dotted tail, plus a 10-digit registrant negative) crossed with suffix alphabet (alnum + `.-_%/` sampled per the §2.2 wild rows, incl. a `%2F` case) → self-canonicalization; carrier-wrapping a subsample (bare/URL/`www.`/label/`urn:doi:`/`info:doi/`) → same canonical; random printable strings → MISSING bias; `url` round-trip
- Consistency test: grammar semantics covered by Rule.target_semantics (no registry → membership-style N/A; assert every §2.1 RECOGNIZE form has a grammar test)
- Presentation purity: `output_format` source scan (`tests/unit/test_rule_output_format_purity.py` — existing CI gate, no new harness needed)
- Real vectors: `10.1000/182`, `10.1000/123456`, `10.1038/issn.1476-4687` (Handbook suffix examples), `10.5594/SMPTE.ST2067-21.2020` (Handbook case-fold vector), `10.13003/5jchdy`, `10.3390/rel11010015`, `10.7774/cevr.2016.5.1.19`, `10.1002/eji.201040559`, `10.64000/gyw3h-trd87`

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT | `doi` (bare) | the identifier itself; MILESTONE row 11; URL is display |
| 2 | Single grammar vs N grammars | Single `doi_recognition`, bare core + carrier groups | avoids cross-grammar spurious AMBIGUOUS; ORCID precedent |
| 3 | Suffix case policy | Lowercase via ASCII-only fold (both parts); PDF check DISCHARGED 2026-09-18 | Handbook Ch.3 'Case Insensitivity' (version-of-record PDF via local conversion): equivalence-only ('equivalent if, and only if, their code point sequences are identical, except U+0041–U+005A ≡ U+0061–U+007A'), Basic-Latin-only ('only with respect to the Basic Latin Unicode block'), no normalization ('no normalization, as defined in ISO/IEC 10646, is performed'). Consequences: (a) fold MUST be ASCII-only — full-Unicode `str.lower()` would conflate Handbook-distinct `Á`/`á` (Ex.2); (b) no NFC/NFD anywhere; (c) lowercase-canonical choice stands (MILESTONE row 11 + APA + URL-safety; DataCite upper-casing and 'Uppercase recommended' are storage/display conventions, not resolution identity, which is insensitive per two RAs). Worked: `10.5594/SMPTE.ST2067-21.2020` ≡ `10.5594/sMPTE.sT2067-21.2020` (Ex.1). Fidelity caveat: verified against the md conversion (case section internally coherent — exact code-point ranges + two worked examples + rationale); conversion shows numbering noise elsewhere (Ch.3 body numbered §4.x; typos in §4.4.2–4.4.4 examples), so spot-check this one section against PDF bytes at implementation if in doubt. |
| 4 | Grammar strictness | Prefix `10\.\d{4,9}(\.\d+)*`, one mandatory `/` (suffix may contain further `/`), non-empty quoteless suffix | P1793/scholid/Gilmartin-measured consensus (4–9-digit registrant bound); shortDOI and 10-digit over-long excluded by construction. Known spec tension (Handbook Ch.3): 'no defined limit on the length of the DOI name, or of the DOI prefix or DOI suffix' + future non-`10.` directory indicators reserved — the {4,9} bound and `10.` gate encode *current allocation practice*, not spec maxima. If the Foundation allocates ≥10-digit registrants or non-`10.` directories, revisit (recognition_revision bump); until then the bound matches the entire observed corpus and every deployed validator. |
| 5 | Trailing-punctuation span trim | Exclude trailing `.`/`)`/`,` from span (explicit test) | sentence-embedding reality; Wikidata regex excludes quotes only — go one step further with reason |
| 6 | shortDOI | REJECT (no grammar element) | Crossref: not actual DOIs, discouraged |
| 7 | Single PUBLICATION | Yes — ISO 26324:2025 only | Handbook/Crossref/Handle are carrier evidence, not validation |
| 8 | single_value for batch | True initially, segmentation for multi | shipped precedent |
| 9 | Legacy carriers in grammar | RECOGNIZE (`doi:` label, dx/http hosts) | Lowercase `doi:` is Foundation-current visual form (Handbook §4.4.1), not legacy — only uppercase-`DOI:`, dx-host, and http-scheme are legacy-per-Crossref; all resolve indefinitely, refusing them strands old-PDF users |
| 10 | Label span inclusion | Include carrier in raw_text span, notation carrier-free | ORCID label/URI precedent |
| 11 | Which alternative written forms does v1 recognize? | Every §2.1 RECOGNIZE row (bare/case/URL incl. `www.`/legacy/label incl. `urn:doi:`/`info:doi/`); DEFER proxy URN-colon form only (needs colon→slash carrier group + `%2F` rule, workflow-rare); REJECT shortDOI/suffix-only/non-`10.` with rationale above | unhandled forms are permanent MISSING blind spots (§2.1 silence audit clean) |
| 12 | Suffix charset: permissive quoteless `\S+` (Wikidata P8966) vs DataCite reserved-char guidance | Permissive v1 | Real-world DOIs contain reserved characters (Wikidata carries comma-bearing exceptions to the quoteless pattern); rejecting them creates false MISSING. DataCite's list (`;/?:@&=+$,!`, no trailing slash) is minting advice for registrants, not validation law — record the tension, revisit only with corpus evidence |

---
## 14. Ambiguity Analysis (Paxman-specific)

- No inherent DOI-vs-DOI ambiguity — prefix/suffix structure eliminates positional ambiguity Date exhibits; two distinct in one slice is authorial choice, segmentation intended.
- DOI-vs-URL is real overlap, not solvable at grammar level — resolver URLs are valid absolute URIs; both capabilities claim, each resolves under its own contract (ORCID-URI precedent — shipped coexistence without guards).
- DOI vs ISBN/ISSN/Phone is length/shape discrimination — no `10.`+slash shape exists in those domains; `10.1000/182` pinned clean against Phone/Date.
- Non-DOI `10.*` handles are indistinguishable structurally — historic Handle-namespace residents under `10.` read SUCCESS; documented limitation, same class as UUID's unminted values.
- Staleness is not ambiguity — no registry means no snapshot drift; Provenance.version pins the spec edition only.
- Homoglyphs are distinct names, not ambiguity — U+002D vs U+2212 vs U+2013 and precomposed vs decomposed `á` render alike but are different code-point sequences (Handbook §4.4.1 NOTE; no-normalization rule); Paxman performs no confusable-folding, so near-duplicate renderings resolve as distinct values or MISSING, never coalesced.
- Future directory indicators are out-of-scope, not ambiguity — Handbook reserves non-`10.` indicators; v1's `10.` gate reads them MISSING by design until allocated.

---
## 15. URL Reference (authoritative, fetched 2026-09-18)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 26324:2025 (Ed 3, current, Published) | https://www.iso.org/standard/88862.html | primary |
| ISO 26324:2022 (withdrawn; lineage) | https://www.iso.org/standard/81599.html | primary |
| DOI prefix/suffix + RA system + Handle tech | https://www.doi.org/the-identifier/what-is-a-doi/ | primary |
| DOI Handbook Dec 2025 (PDF version of record) | https://www.doi.org/the-identifier/resources/handbook/ | primary |
| DOI Handbook Sept 2025 full text (Ch.3 namespace/case/no-checksum/carriers; Ch.5 proxy/shortDOI) — version-of-record PDF read via local markdown conversion | docs/development/research/DOIHandbook_2025.pdf.md | primary (local conversion; case section coherent, numbering noise elsewhere noted in §13.3) |
| Handle namespace + case rules (RFC 3650 §3) | https://www.rfc-editor.org/rfc/rfc3650.txt | primary |
| Crossref display guidelines Mar 2017 (canonical URL, legacy carriers, shortDOI) | https://www.crossref.org/display-guidelines/ | primary (RA) |
| validator.js has no isDOI (ecosystem gap) | https://raw.githubusercontent.com/validatorjs/validator.js/master/src/lib/isDOI.js (404) | primary (negative) |
| stdnum has isin/lei but no doi.py (gap) | https://api.github.com/repos/arthurdejong/python-stdnum/contents/stdnum | primary (negative) |
| Wikidata P356 URL-match pattern (P8966) + P1793 format + P7470 URN formatter + all-caps examples + dx/www formatters (shape consensus) | https://www.wikidata.org/wiki/Property:P356 | secondary |
| `info` URI scheme + registry mechanism (RFC 4452) | https://www.rfc-editor.org/rfc/rfc4452.txt | primary |
| `info:doi/` namespace formatter + legacy XML-export usage | https://www.wikidata.org/wiki/Property:P356 (`info:doi/$1` formatter) ; https://en.wikipedia.org/wiki/Digital_object_identifier (via search) | secondary |
| Crossref DOI regexes, modern vs early (Gilmartin: 4–9-digit registrant bound, 74.4M/74.9M coverage) | https://www.crossref.org/blog/dois-and-matching-regular-expressions/ | secondary (RA staff) |
| DOI case-insensitivity (DataCite + mEDRA, both RAs) + structural-only validator (scholid) | https://support.datacite.org/docs/doi-basics ; https://www.medra.org/en/DOI.htm ; https://cran.r-universe.dev/scholid/doc/scholid_definitions.html | secondary |
| Test-prefix policy (no designated documentation prefix; `10.5072` retired 2019) | https://pidforum.org/t/example-doi-prefix-best-practice-for-documentation-on-dois/1763 | secondary |
| DOI Handbook Dec 2025 PDF (version of record; confirmation pending) | https://www.doi.org/doi-handbook/DOIHandbook_2025.pdf | primary (existence verified; contents not fetched — PDF) |
| IBAN/BIC/ORCID/UUID precedents | docs/development/research/2026-08-22-iban-canonicalization.md, docs/development/research/2026-08-23-bic-canonicalization.md, docs/development/research/2026-08-23-orcid-canonicalization.md, docs/development/research/2026-09-16-uuid-canonicalization.md | primary |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary |
| Shipped precedent (ORCID grammar/contract) | paxman/capabilities/ORCID/grammar/orcid_recognition.py, paxman/engine/orchestrator.py:_dedup_spans, paxman/core/domain.py:Rule | primary |

---
## 16. Evidence Completion — Resolved

This report's DOI-specific authoritative evidence has been fetched and cited (2026-09-18):
- [x] ISO catalogue entry: ISO 26324:2025 (Ed 3, current, Published) superseding 2022 (withdrawn) and 2012; TC 46/SC 9; ICS 01.140.20
- [x] RA and Directory provenance: RAs mint continuously — recorded as non-vendored with rationale (§5.4/§5.5)
- [x] Structure: prefix/suffix split, `10.` gate, registrant digits, opaque suffix, Handle charset lineage
- [x] No checksum proved (Handbook §4.3.5 affirmative 'does not itself make use of check digits' + EIDR per-application exception scoped + ISO scope + scholid structural-only)
- [x] Country nuance: N/A — no geography (recorded, not skipped)
- [x] Ecosystem regex consensus: Wikidata P8966/P1793 verbatim (P8966 lower-bounds registrant at 4; 4–9 upper bound per P1793/scholid/Gilmartin, followed by v1) + scholid structural regex + Crossref carrier rules + double-negative (no validator.js, no stdnum module)
- [x] Recognition-surface inventory complete (§2.1): every attested written form listed with evidence and a RECOGNIZE/DEFER/REJECT disposition — incl. `www.` host variant, `urn:doi:` URN carrier (both now Handbook-primary), and proxy URN-colon DEFER — no silently unhandled form
- [x] Case-fold rule PDF-confirmed (Handbook Ch.3 case section: equivalence-only, Basic-Latin-only, no normalization; ASCII-only fold + no-NFC/NFD requirements recorded in §3.1/§4.2/§13.3)
- [x] Wild input shapes validated (§2.2, 18 rows) against spec + RA pages + resolver corpus
- [x] Label scope decision (§13.9–10: legacy labels RECOGNIZED with span rule)
- [x] Branch/XXX equivalence decision: N/A — every name its own identity (§14, recorded)
- [x] Flag semantics decision: N/A — no flags (§13, recorded)
- [x] Directory liveness scope decision: continuous-mint, non-vendored (§5.4, recorded)
File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped ISBN, ORCID, UUID and URL Capabilities Teach DOI (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

1. **Grammar strips, rule validates, capability formats.** ORCID `_orcid_notation` uppercases + regroups; UUID `_uuid_notation` lowercases + regroups; DOI `_doi_notation` partitions + lowercases — same three-step shape.
2. **One file per provenance, one class per section.** ORCID's `iso_27729_ed2024.py`, UUID's `rfc_9562_ed2024.py`; DOI's `iso_26324_ed2025.py` holds one (`Section 4-doi-syntax`) — same shape.
3. **No `output_format` in rules, ever.** ORCID `normalize()` returns hyphenated; UUID returns hyphenated; DOI returns bare — `format_value` alone renders `url`.
4. **Single grammar with carriers avoids spurious AMBIGUOUS; cross-capability URI overlap is shipped coexistence.** ORCID URIs vs URL absolute URIs already coexist guard-free; DOI resolver URLs join the same standing via engine `_dedup_spans` (within-grammar only) + per-contract resolution.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for DOI row 11. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the ORCID/UUID precedents. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
