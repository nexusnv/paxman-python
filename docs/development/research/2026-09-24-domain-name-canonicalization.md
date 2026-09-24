# Domain Name / IDN Canonicalization Research — paxman-python

- **Date:** 2026-09-24 (research fetches performed 2026-09-23 UTC)
- **Skill:** `paxman-capability-research` (Phase 3 deliverable)
- **Capability researched:** Domain Name / IDN — hostname and internationalized domain name canonicalization
- **Gold standards:** `docs/development/research/2026-08-23-bic-canonicalization.md`, `docs/development/research/2026-08-22-iban-canonicalization.md`
- **Repo state:** branch `dev` @ `7e0dea2`
- **Sources:** 25 primary URLs (fetched 2026-09-23), 9 secondary (labelled) — 34 citations total
- **Scope:** research only — no code, tests, or `pyproject.toml` changes
- **Revision:** 2026-09-24 (post-review) — §2.4 multi-mention semantics probe-corrected, §4.2 sketch made permissive/span-mode, §6 sketches aligned to the real `CapabilityContract`/`Capability` surfaces, W8/E6/E11/E14/E15/E18 statuses pinned, §7.3 snapshot spot-checked, D13 added

## EXECUTIVE FINDINGS

- Domain names have **one interoperable canonical direction: Unicode → lowercase ASCII A-label** (RFC 5890 §2.3, RFC 5891 §4); `münchen.de` canonically *is* `xn--mnchen-3ya.de`, and Unicode is a presentation form (`format_value()` seam), never the canonical value.
- Recognition needs **two correlated authorities**: a PARSER grammar (RFC 1034/1035/1123 shape + RFC 5890/5891 IDNA validity) and a **LOOKUP of the IANA root zone** (`tlds-alpha-by-domain.txt` v2026092300, 1,438 entries) — otherwise every candidate qualifies only under the ADR-0012 vacuity exception, which is exactly the URL capability's known weakness.
- **UTS #46 v18.0.0 is the only complete, citable processing specification** (mapping, NFC, STD3, bidi, context, statuses) covering real-world inputs (fullwidth letters, `。` dot variants, zero-width joins); RFC 5891 alone does not define the mapping table. That table must be a *shipped snapshot* — the cross-capability import ban forbids reusing URL's `rules/data/idna_uts46_mapping.py`.
- **Three structural tensions must be resolved before scaffolding:** (1) URL preserves trailing root dots while the MILESTONE row-10 intent is to strip them; (2) ADR-0010 re-entry / ADR-0011 information-preservation constrain any non-default `output_format` (`unicode` is safe — Punycode round-trips — but must be pinned, non-transitional, and injective per entity); (3) the bundled root zone is a *new generated-data pipeline* (snapshot + `tools/regenerate_*`), the newest instance of the registry-LOOKUP pattern the library already ships (IBAN registry, ISBN range message, Language IANA registry, LEI GLEIF LOU — `RuleStrategy.LOOKUP_TABLE` across ten capabilities).
- **Two scope questions have no primary-source answer and are pure product decisions:** underscore hosts (`_dmarc.example.com` — legal in DNS, illegal under STD3/IDNA) and single-label names (`localhost`) — both must be explicit DEFER/REJECT rows, not accidents. Honest gap: no ICANN/IETF prose prohibiting all-numeric TLDs was found; rejecting `foo.123` must rest on root-zone LOOKUP, not a quoted regex rule.

## Executive Summary

Paxman canonicalizes URLs (`paxman/capabilities/URL/`) but not the bare domain names inside them: `docs/development/MILESTONE.md` ranks **Domain name / IDN as roadmap row 1**, folding in the abandoned row-10 **TLD** sub-goal (trailing-dot strip, bare-TLD scope). Twenty-six capabilities ship today (`paxman/capabilities/__init__.py`); none accepts `münchen.de`, `example.com.`, or `EXAMPLE.COM` as a whole-input domain. The nearest neighbours — URL, Email, IP — each own only a *container* view of a host, and their contracts structurally cannot accept the bare form without whole-input rewriting, which paxman rules never do.

The authority stack is unusually well documented but layered: RFC 1034/1035 define label syntax; RFC 1123 §2.1 relaxes the first character to a digit; RFC 3492 defines Punycode; RFC 5890–5894 define IDNA2008 (A-label/U-label, validity, bidi, machine identifiers); RFC 5895 and UTS #46 define the mapping layer RFC 5891 deliberately left to operators; WHATWG URL specifies de-facto browser behaviour; the IANA root zone provides the authoritative TLD set. No single source covers the whole input surface — the canonical form must be assembled from a *pinned stack* (RFCs + UTS #46 v18.0.0 + IANA snapshot version), exactly like Currency's `shared_data` snapshot and IBAN's registry table.

The design centre: canonical value = **lowercase ASCII, no trailing dot, NFC-then-Punycode per UTS #46 non-transitional processing, TLD confirmed against a bundled root-zone list**; everything Unicode, decorated (`https://`), or ambiguous (`user@host`, `host:443`) is either rendered by `format_value()` or rejected/deferred. §4 fixes seven ambiguity axes, §8 works 18 edge cases, §9 resolves 8 recognition collisions, §13 leaves 13 decisions open for the plan — chief among them the trailing-dot asymmetry with URL and the underscore/single-label scope boundary. §15 records nine honest research gaps instead of inventing rules.

## 1. Target User

Who reaches for `canonicalize(…, "domain")`, and what they actually type:

| User | Situation | Input they paste | Wants |
|---|---|---|---|
| SRE / migration scripts | deduplicating host lists from DNS zones, load balancers, /etc/hosts | `EXAMPLE.COM.`, `Example.com`, `xn--mnchen-3ya.de` | one stable key per host |
| Security / threat-intel tooling | folding indicator-of-compromise feeds | `münchen.de`, mixed case, root-absolute names from dig `$ORIGIN` output | deterministic A-label keys for joining feeds |
| Registrars / RDAP clients | normalizing the `ldhName`/`unicodeName` pair | both forms interchangeably | one canonical, one display (§6) |
| Email/DKIM operators | domain-part handling, `_dmarc`/`_service` selectors | `user@example.com` (→ Email), `_dmarc.example.com` (D7) | clear scope boundary, not silent acceptance |
| Developers using the CLI | quick check in a terminal | `uv run python -m paxman domain "münchen.DE."` | JSON canonical + provenance |

**Capability gap (built vs promised):**

| Dimension | Finding | Evidence |
|---|---|---|
| Shipped capabilities | 26 (BIC … UUID); no Domain/IDN/TLD entry | `paxman/capabilities/__init__.py`; `tests/unit/test_capability_exports.py` |
| Roadmap position | **Row 1: "Domain name / IDN"**; row 10 "TLD" is a sub-goal of it | `docs/development/MILESTONE.md` |
| Nearest shipped neighbour | URL — recognizes absolute URIs; its *host* handling is internal, not an exposed capability | `paxman/capabilities/URL/parsing.py`, `grammar/absolute_uri_recognition.py` |
| IDNA machinery already in-tree | URL ships a generated UTS #46 mapping table | `paxman/capabilities/URL/rules/data/idna_uts46_mapping.py`; generator `tools/regenerate_idna_uts46_data.py` |
| Import constraint | capabilities import only `paxman.core` — **Domain cannot reuse URL's table directly** | `ARCHITECTURE.md` anti-patterns; `HOW_TO_ADD_NEW_CAPABILITY.md` |
| Shared-data precedent | cross-capability snapshots live in `paxman/shared_data/` | `paxman/shared_data/currency_snapshot.json` → Currency + Money |
| Ecosystem demand (secondary) | `isFQDN`/`isEmail`/`isURL` (validator.js), `tldts`, `peerigon/parse-domain`, Apache `DomainValidator`; **python-stdnum has no domain module** (negative result) | validator.js docs; stdnum index (labelled secondary, appendix) |

**Gap statement:** Paxman can canonicalize the *container* (`url`) but not the *name* (`domain`). Domain is the missing primitive that URL and Email each partially reimplement.

## 2. Shape of Input (Human Surface)

### 2.1 Wild variants — enumerated from RFCs, UTS #46, ICANN guidance, real feeds, and validator behaviour

Sixteen variants, each with expected pipeline outcome (the fixture set for §12; edge detail in §8):

| # | Variant | Class | Expected |
|---|---|---|---|
| W1 | `EXAMPLE.COM` | clean, uppercase | SUCCESS `example.com` |
| W2 | `münchen.DE` | clean IDN, mixed case | SUCCESS `xn--mnchen-3ya.de` (case-fold before encode) |
| W3 | `münchen.de.` | clean + root-absolute dot | SUCCESS `xn--mnchen-3ya.de` |
| W4 | `XN--MNCHEN-3YA.de` | clean A-label, uppercase ACE | SUCCESS `xn--mnchen-3ya.de` |
| W5 | `mu​̈nchen.de` | NFD (combining diaeresis) | SUCCESS `xn--mnchen-3ya.de` (NFC first; converges with W2) |
| W6 | `ｅxample。ｊｐ` | fullwidth letters + ideographic full stop | SUCCESS `example.jp` (UTS #46 mapped) |
| W7 | `straße.de` | deviation char (ß) | SUCCESS `xn--strae-oqa.de` (non-transitional, axis A4) |
| W8 | `exam--ple.com` | internal double hyphen (NOT at 3–4) | SUCCESS (NR-LDH — `--` outside the reserved 3rd/4th positions, RFC 5890 §2.3.2.1). The reserved case `ex--ample.com` (`--` at 3–4, R-LDH without `xn--`) → INVALID **iff D13 pins `CheckHyphens=true`** (UTS #46 §4.1 criterion 2 is conditional) |
| W9 | `www.example.com` | subdomain | SUCCESS — whole name canonicalized, **no PSL truncation** (D9: PSL deferred) |
| W10 | `foo.unknowntld-xyz` | shape-ok, TLD not in root zone | INVALID (LOOKUP, axis A6) |
| W11 | `ex..ample.com` | empty label | INVALID (RFC 1034 §3.1) |
| W12 | `-cdn.example.com` | leading hyphen at label edge | INVALID (RFC 1035 §2.3.1) |
| W13 | `example​.com` (U+200B) | invisible character | INVALID (UTS #46 status `disallowed`) |
| W14 | `user@example.com` | email container | MISSING — Email capability owns (§4.4 guards) |
| W15 | `https://example.com:8080/` | URL container | MISSING — URL capability owns |
| W16 | `*.example.com` | wildcard pattern | MISSING — pattern, not a name (`*` outside charset, no span) |

Ecosystem cleaning pattern for comparison (secondary — what validators do, for contrast with our pipeline):

```python
# validator.js isFQDN options (SECONDARY — https://github.com/validatorjs/validator.js)
# isFQDN("example.com.", { allow_trailing_dot: true, max: 253, require_tld: true })
# kjd/idna (SECONDARY — https://github.com/kjd/idna): idna.encode("münchen.de", uts46=True)
#   -> b"xn--mnchen-3ya.de"   # UTS #46 mapping + NFC + Punycode, non-transitional
# paxman instead: recognize (PARSER) -> validate (rules + LOOKUP) -> resolve -> hash
#   deterministic given the pinned snapshot (RFCs + UTS #46 v18 + tlds-alpha v2026092300)
```

### 2.2 Written-form taxonomy — every human-written representation, with disposition

RECOGNIZE = in-scope v1 · DEFER = later version or other capability · REJECT = invalid input (`INVALID`/`MISSING`).

| # | Written form | Example | Authority / evidence | Disposition |
|---|---|---|---|---|
| 1 | Bare ASCII FQDN, lowercase | `example.com` | RFC 1034 §3.1 (https://www.rfc-editor.org/rfc/rfc1034) | **RECOGNIZE** (canonical already) |
| 2 | Uppercase / mixed case | `EXAMPLE.COM` | RFC 1035 §3.1 case-insensitive (https://www.rfc-editor.org/rfc/rfc1035); RFC 4343 (https://www.rfc-editor.org/rfc/rfc4343) | **RECOGNIZE** (fold) |
| 3 | U-label (Unicode) | `münchen.de` | RFC 5890 §2.3 (https://www.rfc-editor.org/rfc/rfc5890) | **RECOGNIZE** (→ A-label) |
| 4 | A-label (Punycode) | `xn--mnchen-3ya.de` | RFC 5890 §2.3.2.1; RFC 3492 (https://www.rfc-editor.org/rfc/rfc3492) | **RECOGNIZE** (canonical form) |
| 5 | Root-absolute trailing dot | `example.com.` | RFC 1034 §2; MILESTONE row 10 | **RECOGNIZE** (strip — axis A1) |
| 6 | Unicode dot variants | `example。com`, `example．com`, `example｡com` | UTS #46 mapped chars `3002 FF0E FF61` (https://www.unicode.org/reports/tr46/) | **RECOGNIZE** (map to `.`) |
| 7 | Fullwidth / mapped characters | `ｍünchen.de` | UTS #46 mapping table (https://www.unicode.org/Public/idna/) | **RECOGNIZE** (map then process) |
| 8 | NFC vs NFD input | `münchen.de` vs `mu​̈nchen.de` | RFC 5891 §4.3 (https://www.rfc-editor.org/rfc/rfc5891); UTS #46 §4 | **RECOGNIZE** (same canonical) |
| 9 | URI-prefixed host | `https://example.com/p`, `//example.com` | WHATWG URL host parser (https://url.spec.whatwg.org/#concept-host-parser) | **DEFER** (URL owns containers) |
| 10 | Host with port / userinfo | `example.com:443`, `admin@example.com` | RFC 3986/2396 authority grammar (https://www.rfc-editor.org/rfc/rfc2396) | **DEFER/REJECT** as whole-input (§4 A7) |
| 11 | Email address | `user@example.com` | RFC 5322 — Email capability | **REJECT** (Email owns) |
| 12 | IP literal | `192.168.0.1`, `[2001:db8::1]` | RFC 1123 §2.1; IP capability | **REJECT** (IP owns) |
| 13 | Numeric TLD | `example.123` | IANA root zone has **no all-numeric TLD** (https://www.iana.org/domains/root/db); no prose rule found (§15 G4) | **REJECT** (LOOKUP-driven) |
| 14 | Single-label name | `localhost`, `intranet` | RFC 6761 special-use; no root-zone match | **DEFER** (D6) |
| 15 | Wildcard / pattern | `*.example.com` | zone-file pattern syntax, RFC 1034 §4.3.1 | **REJECT** (not a name) |
| 16 | Underscore host | `_dmarc.example.com` | DNS owner names legal (RFC 1035); STD3-illegal (UTS #46 `disallowed_STD3_valid`) | **DEFER** (D7) |
| 17 | Empty / repeated dots | `ex..ample.com`, `.example.com` | RFC 1034 §3.1 empty label not permitted | **REJECT** |
| 18 | Hyphen misuse | `-example.com`, `example-.com` | RFC 1035 §2.3.1 "must not … end with a hyphen"; RFC 1123 §2.1 digit-first relaxation | **REJECT** (`xn--` ACE exempt, form 4) |
| 19 | Invisible / zero-width chars | `example​.com` (ZWSP) | UTS #46 status `disallowed` for U+200B | **REJECT** |
| 20 | Surrounding whitespace | `" example.com "` | UTS #46 STD3 disallows space; trimming is policy | **REJECT raw** (D8: trim or reject) |
| 21 | Percent-encoded host | `exam%70le.com`, `%2eexample.com` | WHATWG percent-decodes hosts; UTS #46 has no percent step | **REJECT** (no percent-decoding) |
| 22 | Overlong label / name | 64-char label; 254-char name | RFC 1035 §2.3.4 (https://www.rfc-editor.org/rfc/rfc1035); validator.js `max:253` (secondary) | **REJECT** (axis A5) |

The taxonomy's diversity comes from **character repertoire** (Unicode vs ASCII), **decoration** (case, trailing dot, fullwidth), and **container ambiguity** (`@`, `:`, `/`) — not from grouping/prefix variants as with ISBN/ORCID; the inventory is therefore capability-specific, per the skill's taxonomy rule.

### 2.3 What is NOT a domain mention

- A URL or URI (`https://example.com/x`) — URL capability; guards in §4.4.
- An email address — Email capability (RFC 5322); the domain part is *its* rule input, not ours.
- An IP address literal — IP capability; `192.168.0.1` is LDH-shaped but resolves to no root-zone TLD (E14).
- A DNS *record* (MX/NS rdata may itself contain a name — but a full RR wire form is not input).
- A pattern (`*.example.com`), a selector (`_2023._domainkey.example.com` — D7), or a search path (`example.com,lab.example`).
- Free text containing a name ("visit example.com today") — span carving is guarded; see `word_only` precedent (`benchmarks/`, BIC §4.2) and §4.4.

### 2.4 Single-mention vs multi-mention input

One canonical domain per call (`single_value=True` — `paxman/engine/orchestrator.py:_enforce_single_value_invariant`, ADR-0004 `docs/adr/0004-single-value-invariant.md`): candidate spans cluster into mentions, and two *separate* mentions resolving to different values raise `MultipleMentionsError` (the error itself points at `docs/recipes/segmentation.md` — split, then canonicalize each slice), while identical values coalesce to `SUCCESS` (candidate dedup) and one mention with several values stays `AMBIGUOUS`. So `a.com;b.com` **raises** rather than joining or silently picking one — exactly the shipped behaviour verified on ISBN (2026-09-24 probe: `9780306406157 9780140449136` → `MultipleMentionsError`; the same value twice → `SUCCESS`). This keeps re-entry (ADR-0010) well-defined. Batch usage is the caller's loop.

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — canonical string plus structured decomposition

```python
# paxman/capabilities/Domain/notation.py (PROPOSED SKETCH — research only, not implemented)
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)          # domain objects: frozen + slots (project convention)
class DomainNotation:
    canonical: str            # lowercase ASCII A-label FQDN, no trailing dot
                               #   "xn--mnchen-3ya.de"  — THE canonical value
    labels: tuple[str, ...]   # ("xn--mnchen-3ya", "de") — post-IDNA, post-fold, post-strip
    tld: str                  # labels[-1] — LOOKUP key for rules/data/root_zone_tlds.py
                               #   NOT a shape discriminator (§3.3)
```

### 3.2 Why not carry the Unicode form, the trailing dot, or user case in the notation

RFC 5890 §2.3 makes the A-label the protocol form; carrying U-label in the notation would make the canonical value depend on presentation choice and break ADR-0011's "encoding, not projection" rule (the Unicode form *derives* from the canonical via a documented decode — §6). Carrying the trailing dot would fork the entity (`example.com.` vs `example.com` re-entry would fail ADR-0010). Carrying user case would make two DNS-equal names two entities (RFC 1035 §3.1: DNS is case-insensitive). Input-shape observations (trailing dot, Unicode arrival) are deliberately *not* notation fields: the notation holds only the components that route rules (`labels` for per-label checks, `tld` for the root-zone LOOKUP), and the recognition span's `raw_text` already IS the input — any test re-derives those facts from the input→canonical pair (§12) instead of duplicating them into identity, the same way BIC's notation keeps no paper spaces (gold standard §3.2).

### 3.3 Why `tld` is not a shape discriminator literal

BIC cannot use `country_code` as a discriminator because structure varies by country; Domain's `tld` has the same status, for three reasons: (a) TLD set is a *moving authority* — 1,438 entries at v2026092300, more later, so any grammar regex freezing today's set is stale-by-construction (and grammars must not carry rule-layer data, `HOW_TO_ADD_NEW_GRAMMAR.md`); (b) IDN TLDs exist only in A-label (`xn--p1ai`) and U-label (`рф`) presentations of one name — a literal match would double-count; (c) shape-validity is independent of existence — `foo.zzzzz` is LDH-perfect and TLD-absent (W10). Therefore `tld` is computed in the notation for the LOOKUP rule (§7.3), never pattern-matched in a grammar.

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — structural (regex/LDH) grammar + UTS #46-normalized IDNA grammar, with PARSER/LOOKUP classification

Needs classification (ADR-0012 vocabulary):

| Need | Kind | Supplies | Source |
|---|---|---|---|
| Label/FQDN shape | **PARSER** | span-bearing candidate `example.com` | RFC 1034 §3.1, RFC 1035 §2.3.1, RFC 1123 §2.1 |
| IDNA validity of Unicode labels | **PARSER** | candidate over U-label input | RFC 5891 §4; UTS #46 statuses |
| Bidi / context checks | rule (validation) | `INVALID` with reason, never raises | RFC 5893 (https://www.rfc-editor.org/rfc/rfc5893), RFC 5892 |
| TLD existence | **LOOKUP** | corroboration on the same recognition | IANA root-zone snapshot (§7.3) |
| Length limits (63/253) | rule | `INVALID` with reason | RFC 1035 §2.3.4 |
| Trailing-dot policy | resolution step | stripped canonical | RFC 1034 + MILESTONE row 10 |
| Underscore / single-label scope | **decision first** | in/out of v1 | none — §15 G6, D6/D7 |

ADR-0012 reading: with a bundled TLD LOOKUP, Domain candidates are **non-vacuous** (PARSER + LOOKUP corroboration on the same recognition) — better positioned than URL, whose TLD check is PARSER-regex and qualifies only under the vacuity exception ("no lookup authority available"). Shipping the root-zone table is a *new data-generation build*, which is why §16 leaves the `needs` checkbox open.

### 4.2 Reference pattern (ASCII path; Unicode path goes through normalizers, not regex)

```python
# paxman/capabilities/Domain/grammar/ascii_hostname.py (PROPOSED SKETCH)
# Module-scope patterns — compiled once, never inside recognize() (HOW_TO_ADD_NEW_GRAMMAR.md)
# Patterns are lowercase — case folding happens in the mapping step (axis A2) BEFORE match.
# Charset: RFC 1035 §2.3.1 (letters/digits/hyphen) + RFC 1123 §2.1 digit-first (NOT §2.3.1 — §15 G7).
_LABEL  = r"[a-z0-9-]+"                   # STRUCTURE ONLY — deliberately permissive: edge hyphens,
_LABEL0 = r"[a-z0-9-]*"                   #   over-length and empty labels are CARRIED to rules so
#   they resolve INVALID (W11/W12, E6/E8/E9/E10/E17), never silently vanish — recognizers never
#   validate (§4.5), which is also why 63/253 are NOT in the pattern (post-mapping lengths of
#   Unicode input are invisible to any regex — idn grammar below; rules own the bounds).
_FQDN   = rf"{_LABEL}(?:\.{_LABEL0})*\.?" # dotted name; ONE optional trailing root dot (stripped at
#   resolve, axis A1) — a second trailing dot degenerates to an empty final label -> INVALID (§4.4).
# "xn--…" is NOT a regex branch: the permissive label carries ACE shapes — including an empty
#   payload, "xn--.com" (E6) — to unicode_uts46_statuses for decode round-trip + hyphen
#   allocation (§7.2 step 4b).
# Boundary (SPAN mode): word edges + container-kill set [ @ : / \ ? # [ ] % ] and '.' adjacency
#   OUTSIDE the match (blocks leading-dot ".example.com" and partial backtracks such as "example"
#   inside "example.com:8080"); the ONE in-pattern trailing dot (axis A1) is part of the match.
#   So "user@example.com"/"https://example.com/" MISS instead of carving a sub-match, while
#   "visit example.com today" carves one guarded span (word_only precedent, §2.3).
#   NO ^…$ whole-input anchor: distinct spans must reach the single-value invariant (§2.4).
```

```python
# paxman/capabilities/Domain/grammar/idn_hostname.py (PROPOSED SKETCH)
# Unicode path: the regex only asserts "a dotted token whose ORIGINAL span contains >=1 non-ASCII
# code point" — deliberately permissive over Unicode, because UTS #46 leaves `disallowed` code
# points UNCHANGED in mapping (§4 Processing, Map step) and catches them at Convert/Validate: the
# matcher must still span them so unicode_uts46_statuses can return INVALID (W13/E16) instead of
# the input vanishing to MISSING. Same edge guards as ascii_hostname (§4.4).
# Heavy lifting is the shared kernel normalizer (paxman/core/grammar/normalizers.py) driven by our
# OWN UTS #46 v18 snapshot (grammar/data/idna_mapping.py — NOT URL's module; import ban, §11).
# Steps before match (full sequence in §7.2):
#   strip ONE trailing dot -> UTS #46 map (case fold, 。．｡ -> ., fullwidth -> ASCII) -> NFC
# After mapping, ASCII residue reuses the ASCII shape over the mapped VIEW (offsets map back to
# the original span — kernel normalizer, ADR-0009); surviving non-ASCII labels go to rule-layer
# UTS #46 statuses + per-label Punycode encode (§7.2 steps 4/6).
```

Strategy rationale: structural regex worked verbatim for ISBN/ISSN/IBAN/BIC (gold standards §4.1); Domain adds a *normalization pre-pass* — which is precisely what kernel normalizers + boundary spec exist for (`paxman/core/grammar/boundary_spec.py`, ADR-0009). No new matcher kind is required for v1.

### 4.3 Recognition pipeline contract (`ARCHITECTURE.md` §"Recognition Pipeline Contract") and per-form flows

Flows in kernel terms (ScanContext → matchers → anchors/boundary → candidates; dedup/affinity/`single_value` in `paxman/engine/orchestrator.py`):

1. **Bare ASCII FQDN (`example.com`)** — boundary guards (§4.4) → LDH matcher over the folded view → PARSER candidate → LOOKUP confirms `com` ∈ root zone → `single_value` → canonical `example.com`.
2. **Uppercase (`EXAMPLE.COM`)** — mapping step case-folds first (axis A2) → flow (1) → canonical lowercase; provenance records original span.
3. **Root-absolute (`example.com.`)** — shape accepts one trailing dot → strip at resolution → LOOKUP on rightmost label → canonical `example.com` (the span's `raw_text` retains the input form).
4. **U-label (`münchen.de`)** — Unicode normalizer (NFC) → UTS #46 map/status check (must not be `disallowed*`) → per-label Punycode encode (RFC 3492) → ASCII candidate → LOOKUP `de` → canonical `xn--mnchen-3ya.de`.
5. **A-label input (`XN--MNCHEN-3YA.DE`)** — case-fold → `xn--` shape + Punycode decode round-trip (RFC 3492) → LOOKUP → canonical `xn--mnchen-3ya.de`; decode failure → `INVALID` (E6).
6. **Mapped dots / fullwidth (`example。com`, `ｍünchen.de`)** — UTS #46 mapped class → ASCII → continue as (1)/(4).
7. **NFD input (`mu​̈nchen.de`)** — NFC before encode → same canonical as (4); W2/W5 fixture pair proves convergence.
8. **Reject paths** (`user@example.com`, `*.example.com`, `[::1]`, `foo.123`, `ex..ample.com`) — no candidate survives boundary/status/LOOKUP → `MISSING`/`INVALID` per `ARCHITECTURE.md` resolution semantics; rules never raise.

Affinity/dedup: ASCII and IDN grammars overlap on pure-ASCII input; the orchestrator dedups same-span-same-resolution matches to `single_value`, so overlap is safe but must be covered by fixtures W1–W4.

### 4.4 Guard boundaries against sibling grammars

| Sibling | Boundary rule | Fixture |
|---|---|---|
| URL | leading/trailing char of a Domain match must not be in `[ @ : / \ ? # [ ] % ]` or `-./`-glue — `https://example.com/` and `example.com:8080` MISS | W15, E13 |
| Email | `@` adjacency kills the match; Email's grammar owns `local@` | W14, E12 |
| IP | numeric-dotted names still run LOOKUP — no root-zone TLD matches `1`, so `192.168.0.1` cannot SUCCESS | E14 |
| Free text | `word_only`-style guards (BIC/IBAN precedent: longer/whole token wins, never carve glued runs) | §2.3 |
| Self (trailing dot) | at most ONE trailing dot in shape; `example.com..` empty-label REJECT | E1 |

### 4.5 Semantics affinity (`HOW_TO_ADD_NEW_GRAMMAR.md` §1, `ARCHITECTURE.md` §"Community Extensions")

Affinity = recognition-adjacent: Domain grammars recognize *names*, never validate (no length check inside `recognize()`), never map tokens to canonical values (IDNA encoding happens in resolution, not in the matcher), never read contracts. Rule-layer data (`root_zone_tlds.py`) is never imported by grammars — only `grammar/data/idna_mapping.py` (grammar-side processing table) may be referenced from the IDNA grammar, mirroring URL's split.

### 4.6 `single_value` — one mention per call vs batch processing

`single_value=True` for v1 (§2.4). A future `include_embedded_names` feature (DEFER) would flip affinity handling and needs `requires_features` declaration on whichever rules read it — rules must never gate ad hoc on `include_*` (project convention).

## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

```text
Spec stack pinned by this design (each line = a citation that survives review):
  RFC 1034 §3.1/§4  (1987)  name syntax, hierarchy, empty labels
  RFC 1035 §2.3.1   (1987)  label charset + "must not … end with a hyphen"
  RFC 1035 §2.3.4   (1987)  "total length of a domain name … restricted to 255 octets or less"
  RFC 1123 §2.1     (1987)  digit-first relaxation (the oft-mis-cited rule — §15 G7)
  RFC 3492          (2003)  Punycode — the ACE encoding inside "xn--"
  RFC 5890 §2.3     (2010)  A-label = protocol form; U-label = validated Unicode overlay
  RFC 5891 §4       (2010)  input validation: mapping (operator-defined), NFC, bidi, context
  RFC 5893          (2010)  Bidi algorithm for IDNA labels
  RFC 5895          (2010)  (Informational) casing/mapping for registries — non-transitional lean
  UTS #46 v18.0.0   (2025)  THE citable mapping/profile: statuses valid | mapped | ignored |
                            deviation | disallowed | disallowed_STD3_valid |
                            disallowed_STD3_mapped | disallowed_unassigned
  WHATWG URL        (live)  de-facto: "domain to ASCII" = Unicode To ASCII, beStrict=false,
                            failure on any non-VALID result — consulted, never pinned
  IANA tlds-alpha   v2026092300 — 1,438 entries (fetched 2026-09-23); Root Zone DB 1,595 (§15 G5)
  ICANN IDN Guidelines v3.0, 30 Jun 2023 — registry policy context (secondary to RFC/UTS #46)
```

Determinism consequence: given the same input, same contract, and same library snapshot (RFC text + UTS #46 table version + root-zone version), Domain yields the same canonical value — no network, no clock, no live IANA query (project determinism rule).

### 5.2 Rule / publication map (one file per publication — `HOW_TO_ADD_NEW_CAPABILITY.md` §5)

| Publication | Rule class responsibility | `kind` / features |
|---|---|---|
| `rfc_1034_name_syntax.py` (`"RFC 1034 §3.1"`) | hierarchy, empty labels, single-label scope (D6) | core |
| `rfc_1035_label_length.py` (`"RFC 1035 §2.3.4"`) | ≤63/label, ≤253 textual (D10) | core |
| `unicode_uts46_statuses.py` (`"UTS #46 v18.0.0"`) | disallowed/deviation/STD3 outcomes; non-transitional (D4) | core |
| `rfc_5893_bidi_context.py` (`"RFC 5893"`) | bidi + ContextJ/ContextO failures | core |
| `iana_root_zone_membership.py` (`"IANA tlds-alpha v2026092300"`) | rightmost label ∈ snapshot | `kind="registry"` (IBAN-registry precedent, `tools/regenerate_iban_registry_data.py`) |
| `scope_selectors.py` (if D6/D7 flip) | underscore / single-label opt-ins | `requires_features={"allow_underscore"}` etc. |

```text
paxman/capabilities/Domain/rules/
├── rfc_1034_name_syntax.py            # "RFC 1034 §3.1"        one PUBLICATION, one Rule class
├── rfc_1035_label_length.py           # "RFC 1035 §2.3.4"
├── unicode_uts46_statuses.py          # "UTS #46 v18.0.0"
├── rfc_5893_bidi_context.py           # "RFC 5893"
├── iana_root_zone_membership.py       # "IANA tlds-alpha v2026092300"   kind="registry"
└── data/
    └── root_zone_tlds.py              # GENERATED snapshot (§7.3) — never hand-edited
# Naming follows the project rule: rule file = ONE publication; rule `name` = "Section …" style
# (e.g. name="Section-3.1-name-syntax", "UTS46-statuses", "root-zone-membership").
# Rules never contain the token `output_format` (CI source-scan enforced), never raise,
# never gate on include_* except via declared requires_features.
```

### 5.3 What each rule does vs does not own

Owns: verdicts on one recognition (shape-valid, length-valid, IDNA-valid, TLD-present). Does not own: presentation (`format_value` only), case folding (mapping step, pre-recognition), trailing-dot policy (resolution step), container parsing (`@ : /` never reach rules — guards MISS first), country/registry semantics of ccTLDs (Domain never maps `.de` → Germany; that would be world-knowledge).

### 5.4 Scope decisions embedded in validation

Two scope-shaped questions are *validation* decisions, not grammar ones: (a) numeric TLD — implemented as LOOKUP miss, not a quoted regex rule, because no primary source prohibits all-numeric TLDs (§15 G4); (b) bare TLD input (`com`, D5) — rejected by requiring ≥2 labels in `rfc_1034_name_syntax.py` unless D5 flips. Both are listed again in §13 so the plan cannot lose them.

### 5.5 Assignment / registration authority & snapshot policy

| Authority layer | Source (primary unless noted) | Snapshot to pin | Regeneration path |
|---|---|---|---|
| Label syntax | RFC 1034 (https://www.rfc-editor.org/rfc/rfc1034), RFC 1035 (https://www.rfc-editor.org/rfc/rfc1035) | RFC text (immutable) | n/a — grammar constants |
| Host relaxation | RFC 1123 §2.1 (https://www.rfc-editor.org/rfc/rfc1123); history RFC 952 (https://www.rfc-editor.org/rfc/rfc952) | RFC text | n/a |
| Case-insensitivity | RFC 4343 (https://www.rfc-editor.org/rfc/rfc4343) | RFC text | n/a |
| Punycode | RFC 3492 (https://www.rfc-editor.org/rfc/rfc3492) | pure implementation (zero runtime deps, uv-only) | n/a |
| IDNA framework/algorithms | RFC 5890–5894 (https://www.rfc-editor.org/rfc/rfc5890 … rfc5894) | RFC text | n/a |
| Mapping profile | UTS #46 v18.0.0 (https://www.unicode.org/reports/tr46/); table (https://www.unicode.org/Public/idna/) | UTS #46 v18.0.0 table | `tools/regenerate_domain_idna_data.py` → `grammar/data/` (URL's `tools/regenerate_idna_uts46_data.py` is the pattern; **own module**) |
| Browser de-facto | WHATWG URL (https://url.spec.whatwg.org/#concept-domain-to-ascii) | consulted, not pinned | n/a |
| TLD set | IANA Root Zone DB (https://www.iana.org/domains/root/db); machine list (https://data.iana.org/TLD/tlds-alpha-by-domain.txt) | **v2026092300, 1,438 entries** | `tools/regenerate_root_zone_tld_data.py` → `rules/data/` + `paxman/shared_data/root_zone_snapshot.json` |
| IDN registry tables | IANA IDN tables (https://www.iana.org/domains/idn-tables) | optional corroboration | defer (D12) |
| IDN policy | ICANN IDN Guidelines v3.0 (https://www.icann.org/en/system/files/files/idn-guidelines-30jun23-en.pdf) | document version | n/a |
| Public suffix (deferred) | PSL (https://publicsuffix.org/list/public_suffix_list.dat) — 10,330 rules fetched 2026-09-23 | would require pinning (moving target) | defer (D9) |
| TLD history (context only) | RFC 1591 (https://www.rfc-editor.org/rfc/rfc1591) — **stale 1994 claim** (§15 G3) | context | n/a |
| Kernel machinery | `paxman/core/grammar/` (ScanContext, MatcherSpec, engine_loop, matchers, anchors, boundary_spec, normalizers); ADR-0009 | codebase @ 7e0dea2 | n/a |

## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (`HOW_TO_ADD_NEW_CAPABILITY.md` §7 — frozen dataclass, no slots)

```python
# paxman/capabilities/Domain/contract.py (PROPOSED SKETCH)
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract

@dataclass(frozen=True)                      # contracts: frozen, NO slots (project convention)
class DomainContract(CapabilityContract):
    """Canonical domain names: ASCII A-label canonical; Unicode is presentation only."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "ascii"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"unicode"})

    capability_name: str = field(default="domain", init=False)
    # output_format: inherited (str | None) — resolved against the two ClassVars by
    #   CapabilityContract.__post_init__; None/"default"/"ascii" -> canonical ASCII.
    # Offered formats (ADR-0011: every offered format is an ENCODING of the same entity):
    #   "ascii"   -> canonical value itself (default, NOT in OFFERED_OUTPUT_FORMATS)
    #   "unicode" -> Punycode-decode each label (RFC 3492); lossless round-trip, injective
    #                per entity -> re-entry holds under default contract (ADR-0010)
    # Non-default knobs, each DECLARED as requires_features on the rules that read them:
    #   allow_single_label: bool = False     # D6 — "localhost"/intranet scope
    #   allow_underscore:   bool = False     # D7 — DNS-legal vs STD3-illegal selectors
    #   transitional:       bool = False     # D4 — PINNED False: True changes canonicals
    #                                         #      (ß -> ss would break re-entry fixtures W7)
    # suppress_common_words: inherited       # A0 whole-input exemption applies to bare words
```

Contract notes: `output_format` appears only here and in `format_value()` — never in rules (CI source-scan). `transitional` is deliberately *not* exposed in v1: two processing modes would double the canonical surface and violate the "same input, same contract → same output" pin unless both were fixture-covered; keep it as a decision record (D4) rather than a knob.

### 6.2 Capability (`HOW_TO_ADD_NEW_CAPABILITY.md` §6 — `format_value()` is the ONLY presentation seam)

```python
# paxman/capabilities/Domain/capability.py (PROPOSED SKETCH)
from paxman.core.capability import Capability
from paxman.capabilities.Domain.notation import DomainNotation

class DomainCapability(Capability[DomainNotation]):
    """Recognition + validation + presentation for bare domain names (host names / IDN)."""

    name = "domain"

    def get_grammars(self): ...    # ascii_hostname, idn_hostname (§4.2)
    def get_rules(self): ...       # §5.2 publication set

    def format_value(
        self, value: str, output_format: str | None, notation: DomainNotation
    ) -> str:
        # value is ALWAYS lowercase ASCII, no trailing dot (axis A1/A2/A3); notation is passed
        #   through for components (labels/tld) if a format ever needs them
        if output_format == "unicode":
            # ADR-0011: this is an ENCODING (label-wise Punycode decode), not a projection —
            # decode(encode(x)) == x for every valid label; ADR-0010 re-entry: rendering
            # "unicode" and re-canonicalizing under the default contract recovers value.
            return ".".join(_punycode_decode(lbl) for lbl in value.split("."))
        return value            # "ascii": the canonical value itself — identity presentation
```

CLI surface (smoke-tested only via e2e — `paxman/cli.py` is coverage-exempt per `pyproject.toml`):

```bash
uv run python -m paxman domain "münchen.DE."
uv run python -m paxman --json domain "example.com."
echo "EXAMPLE.COM" | uv run python -m paxman domain
# expected JSON canonical: "example.com"   (W1);  E1 strips the root dot
```

## 7. Validation — Syntactic, IDNA, Root-Zone

### 7.1 Syntactic validation (no checksum — three-level model)

Domains have **no checksum** (unlike IBAN MOD-97 / BIC directory); validity is three-level:

1. **Shape-valid** — LDH/ACE regex + hyphen/empty-label rules (§4.2) — grammar-adjacent, verdict in rules.
2. **IDNA-valid** — every non-ASCII-bearing label passes UTS #46 statuses + RFC 5893 bidi/context (§7.2).
3. **Root-zone-real** — rightmost label ∈ snapshot (§7.3). Only all three ⇒ SUCCESS; `INVALID` names the failing level in provenance.

```python
# rules/rfc_1035_label_length.py constants (PROPOSED SKETCH)
MAX_LABEL_OCTETS = 63      # RFC 1035 §2.3.1 — label ≤ 63 octets (wire)
MAX_NAME_CHARS   = 253     # textual FQDN without trailing dot — DERIVED from RFC 1035 §2.3.4's
                           #   255-wire-octet total (length octets + root label); the textual form
                           #   is NOT stated in the RFC (secondary consensus: validator.js,
                           #   commons-validator use 253) -> recorded as D10 / §15 G9.
# Post-IDNA lengths are measured on the ASCII A-label form (after §7.2 step 6) — a Unicode
# input's code-point length is irrelevant to the wire limit.
```

### 7.2 IDNA validation — the pinned processing sequence

```text
IDNA processing sequence (RFC 5891 §4 as profiled by UTS #46 v18.0.0, NON-transitional):
  1. strip ONE trailing root dot (the input span retains the dot)  — axis A1, E1
  2. UTS #46 Map: case fold + mapped chars (。．｡ → ., fullwidth → ASCII)  — axis A2/A6, E5
  3. NFC normalize                                              — RFC 5891 §4.3, E5-NFD (W5)
  4. per-label status check:
       disallowed | disallowed_STD3_* | disallowed_unassigned  -> INVALID   — E16, W13
       deviation (ß, ς) kept as-is                              — NON-transitional, E18/W7
       mapped chars already applied in step 2
  4b. hyphen allocation: "--" at a label's 3rd/4th positions with NO "xn--"
       prefix (R-LDH) -> INVALID — RFC 5891 §4.2.3.1 (Hyphen Restrictions) +
       RFC 5890 §2.3.2.1 (R-LDH usable in IDNA-aware apps only as XN-labels);
       gated on D13's CheckHyphens pin (UTS #46 §4.1 criterion 2 is conditional)
  5. bidi check (RFC 5893) + ContextJ/ContextO (RFC 5892)       -> INVALID on failure
  6. labels with non-ASCII -> Punycode encode (RFC 3492) -> "xn--…"  — E3, W2
  7. length: ≤63 octets/label, ≤253 chars total                 — RFC 1035 §2.3.4, E8/E9
  8. lowercase everything                                       — RFC 1035 §3.1 + RFC 4343
  9. LOOKUP: rightmost label ∈ ROOT_ZONE_TLDS else INVALID      — IANA snapshot, E7/E10-W10
 10. canonical = ".".join(labels)  (no trailing dot, ever)
A-label-only inputs (step 0 variant): case-fold, then Punycode DECODE round-trip must
reproduce the label exactly (RFC 3492); failure -> INVALID (E6, "xn--.com").
```

### 7.3 Root-zone LOOKUP — the generated authority

```python
# paxman/capabilities/Domain/rules/data/root_zone_tlds.py (PROPOSED — GENERATED, never hand-edited)
# Source:      https://data.iana.org/TLD/tlds-alpha-by-domain.txt
# Snapshot:    v2026092300 — 1,438 entries (fetched 2026-09-23); list is UPPERCASE A-labels
# Cross-check: https://www.iana.org/domains/root/db shows 1,595 entries — reconcile in impl (§15 G5)
# Generator:   tools/regenerate_root_zone_tld_data.py (mirror tools/regenerate_iban_registry_data.py)
# Invariant:   every root-zone TLD present (lowercased); nothing absent from the snapshot present.
# Spot-check 2026-09-24: "XN--MNCHEN-3YA" is absent (it is münchen's SLD label, NOT a TLD);
#   "XN--P1AI" is present. Example entries below are real zone members.
ROOT_ZONE_TLDS: frozenset[str] = frozenset({
    "com", "org", "net", "de", "jp", "xn--p1ai", ...
})
SNAPSHOT_VERSION = "tlds-alpha-by-domain.txt@2026092300"   # stamped into VersionStamp/provenance
# Live queries are FORBIDDEN (determinism): the snapshot travels with the library version,
# exactly like paxman/shared_data/currency_snapshot.json travels with Currency + Money.
```

Candidate qualification under ADR-0012 (why this table exists):

```text
PARSER candidate (span = whole input, e.g. "foo.unknowntld-xyz")
  + LOOKUP (tld "unknowntld-xyz" ∉ ROOT_ZONE_TLDS, same recognition)
  => candidate does NOT qualify -> INVALID (W10)         # non-vacuous rejection

PARSER candidate ("example.com") + LOOKUP ("com" ∈ snapshot)
  => qualifies on the same recognition                    # non-vacuous success

WITHOUT the snapshot (pure-regex Domain, URL-style):
  => no lookup authority available -> vacuity exception fires for EVERY candidate
  => shipped capability would rest on the exception by design — rejected for v1 (D11)
```

### 7.4 What makes a domain "shape-valid" vs "real" vs "registered"

Shape-valid: passes §7.1 levels 1–2 (`foo.notatld` is shape-valid). Root-zone-real: level 3 (`foo.notatld` fails). **Registered** (a registrant owns `example.com` in a registry) requires live RDAP/whois — *out of scope forever*: world-knowledge, network-dependent, non-deterministic. This three-level model mirrors BIC's syntactic/registry split (gold §7) with the registry layer replaced by a static snapshot.

## 8. Edge Cases

| # | Input | Expected status | Canonical / behaviour | Authority |
|---|---|---|---|---|
| E1 | `example.com.` | SUCCESS | `example.com` (trailing dot stripped; the input span retains the original form) | RFC 1034; MILESTONE row 10 |
| E2 | `EXAMPLE.COM` | SUCCESS | `example.com` | RFC 1035 §3.1; RFC 4343 |
| E3 | `münchen.de` | SUCCESS | `xn--mnchen-3ya.de` | RFC 5890/5891; RFC 3492 |
| E4 | `XN--MNCHEN-3YA.DE` | SUCCESS | `xn--mnchen-3ya.de` | RFC 5890 §2.3.2.1 (ACE lowercase) |
| E5 | `example。com` (U+3002) | SUCCESS | `example.com` | UTS #46 mapped property |
| E6 | `xn--.com` / bad ACE payload | INVALID | candidate recognized; Punycode decode round-trip fails in `unicode_uts46_statuses` | RFC 3492; RFC 5891 §4 |
| E7 | `example.123` | INVALID | rightmost label ∉ root-zone snapshot | IANA root zone (§15 G4: no prose rule) |
| E8 | 64-char label `aaa…a.com` | INVALID | label > 63 octets | RFC 1035 §2.3.1 |
| E9 | 254-char name (no trailing dot) | INVALID | > 253 textual FQDN (255-wire derivation) | RFC 1035 §2.3.4; D10 |
| E10 | `-example.com` / `example-.com` | INVALID | hyphen at label edge | RFC 1035 §2.3.1; RFC 1123 §2.1 relaxes first char only |
| E11 | `localhost` / `intranet` | INVALID | single-label carried by shape, rejected by the ≥2-label scope rule (D6 off, §5.4) — same pattern as Timezone's bare abbreviations → INVALID, not MISSING | RFC 6761; §5.4 |
| E12 | `user@example.com` | MISSING | Email capability owns | boundary guards (§4.4); RFC 5322 |
| E13 | `https://example.com/` | MISSING | URL capability owns | WHATWG URL; §4.4 |
| E14 | `192.168.0.1` / `[::1]` | INVALID / MISSING | dotted quad → INVALID (root-zone LOOKUP miss on rightmost `1`, §4.4/O5); `[::1]` → MISSING (outside Domain charset) | IANA root zone; IP capability owns both |
| E15 | `*.example.com` | MISSING | pattern chars outside Domain charset — no candidate (RFC 1034 §4.3.1 is zone-file syntax, not a name) | RFC 1034 §4.3.1 |
| E16 | `example​.com` (U+200B) | INVALID | UTS #46 status `disallowed` | UTS #46 v18.0.0 |
| E17 | `ex..ample.com` | INVALID | empty label | RFC 1034 §3.1 |
| E18 | `com` (bare TLD) / `straße.de` | INVALID / SUCCESS | `com` → INVALID (D5 ≥2-label rule, §5.4); `straße.de` → `xn--strae-oqa.de` (D4 non-transitional pin) | PSL scope; UTS #46 `deviation` |

Every row becomes a pytest case (§12) and appears in the corpus (§2.1 pairs W1–W16).

## 9. Resolution-State Map (`ARCHITECTURE.md` §"Resolution Semantics")

| Case | Reading 1 | Reading 2 | Resolution | Authority |
|---|---|---|---|---|
| R1 `example.com.` | keep root-absolute (URL host behaviour) | strip (MILESTONE row 10) | **strip** in Domain; document asymmetry vs URL (O1) | RFC 1034 equivalence |
| R2 `EXAMPLE.COM` | preserve user case | fold | **fold lowercase** — DNS-equal names, one entity | RFC 1035 §3.1; RFC 4343 |
| R3 `münchen.de` vs `xn--mnchen-3ya.de` | two entities | one entity | **same canonical** — U-label is an overlay of the A-label | RFC 5890 §2.3 |
| R4 `münchen.de` vs `mu​̈nchen.de` | different strings | normalized equals | **same canonical** — NFC before encode | RFC 5891 §4.3; UTS #46 |
| R5 `straße.de` | transitional (`strasse`) | non-transitional (ß kept) | **non-transitional** `xn--strae-oqa.de` — pinned (A4/D4) | RFC 5891; UTS #46 `deviation`; RFC 5895 (info) |
| R6 `example。com` vs `example.com` | distinct separators | one dot | **map to `.`** | UTS #46 mapped class |
| R7 `_dmarc.example.com` | DNS-legal owner name | STD3-illegal label | **defer** — v1 INVALID via `disallowed_STD3_valid` unless D7 flips | UTS #46 STD3; §15 G6 |
| R8 `example.123` | shape-valid label | not a TLD | **INVALID** via root-zone LOOKUP (not a quoted regex) | IANA root zone DB |

## 10. Scaffolding & Repo Integration

Size estimate:

| Dimension | Estimate | Rationale |
|---|---|---|
| Grammars | 2 (`ascii_hostname`, `idn_hostname`) | §4.2; kernel matcher kinds suffice (ADR-0009) |
| Rule publications | 5–6 (§5.2) | one file per publication (`HOW_TO_ADD_NEW_CAPABILITY.md` §5) |
| Generated data modules | 2 | `grammar/data/idna_mapping.py`, `rules/data/root_zone_tlds.py` |
| New regenerator tools | 1–2 | mirror `tools/regenerate_idna_uts46_data.py` / `regenerate_iban_registry_data.py` |
| `output_format` options | `ascii` (default), `unicode` | §6; ADR-0011 encoding pair |
| Deferral candidates | PSL, scheme/port parsing, underscore, single-label | D6/D7/D9/D11 |
| Scaffolder fit | standard | `tools/new_capability.py` Step 0 |

### 10.1 Generated skeleton (`tools/new_capability.py` — `HOW_TO_ADD_NEW_CAPABILITY.md` Step 0)

```bash
uv run python tools/new_capability.py Domain
# then fill: notation.py (§3.1), contract.py (§6.1), capability.py (§6.2),
#            grammar/ (§4.2), rules/ (§5.2), grammar/data + rules/data generators (§7.2/§7.3)
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/
uv run pyright && uv run import-linter lint && uv run pytest
# full pre-PR gate: uv run ruff check . && uv run ruff format --check . && uv run pyright
#                   && uv run import-linter lint && uv run pytest
```

### 10.2 Contract & grammar wiring

- `CapabilityContract.__post_init__` resolves `output_format` (inherited); Domain adds no new resolution logic beyond §6.1 defaults.
- Grammars receive no contract flags — D6/D7 knobs reach rules only as `requires_features` (never read by grammars, never gated ad hoc).
- Registry: `paxman/core/discovery.py` registration happens via `register_all_shipped()` (`paxman/api/bootstrap.py`) — update the deterministic name list + `paxman/capabilities/__init__.py` (export completeness enforced by `tests/unit/test_capability_exports.py`).

### 10.3 Cross-cutting invariants (fail review if violated)

1. No `# type: ignore` / `# noqa` / `# pyright: ignore` anywhere in `paxman/` (project anti-pattern rule).
2. No cross-capability imports: Domain imports only `paxman.core` — **not** `paxman.capabilities.URL` (§11 O2).
3. Rules never contain the token `output_format`; grammars never import `rules/data/*`.
4. Rules never raise; recognizers never validate; `format_value()` is the only presentation seam.
5. Determinism: no network, no clock — snapshot version travels in provenance (`SNAPSHOT_VERSION`).
6. Re-entry (ADR-0010) + information preservation (ADR-0011) + non-vacuous candidates (ADR-0012) tested, not asserted in prose (§12).

## 11. Recommended File Layout (mirrors IBAN/ISSN and URL's IDNA split)

```text
paxman/capabilities/Domain/
├── notation.py                      # DomainNotation (§3.1): canonical + labels + tld (components only)
├── contract.py                      # DomainContract (§6.1): output_format ascii|unicode, pinned defaults
├── capability.py                    # format_value — ascii/unicode seam (§6.2)
├── grammar/
│   ├── ascii_hostname.py            # PARSER — RFC 1034/1035/1123 LDH shape (§4.2)
│   ├── idn_hostname.py              # PARSER — Unicode input via OWN UTS #46 snapshot (§4.2)
│   └── data/
│       └── idna_mapping.py          # GENERATED: UTS #46 v18.0.0 table — Domain's OWN module
│                                    #   (URL has rules/data/idna_uts46_mapping.py; the import ban
│                                    #    forbids reuse — long-term candidate for shared_data, O2)
└── rules/
    ├── rfc_1034_name_syntax.py      # "RFC 1034 §3.1"        empty labels, ≥2 labels (D5)
    ├── rfc_1035_label_length.py     # "RFC 1035 §2.3.4"      63/253 (D10)
    ├── unicode_uts46_statuses.py    # "UTS #46 v18.0.0"      statuses, non-transitional (D4)
    ├── rfc_5893_bidi_context.py     # "RFC 5893"             bidi + context
    ├── iana_root_zone_membership.py # "IANA tlds-alpha v2026092300"   kind="registry" (§7.3)
    └── data/
        └── root_zone_tlds.py        # GENERATED TLD snapshot + SNAPSHOT_VERSION stamp

paxman/shared_data/
└── root_zone_snapshot.json          # optional canonical source shared with any future consumer
                                      #   (mirrors currency_snapshot.json — Currency + Money pattern)

tools/
├── regenerate_domain_idna_data.py   # UTS #46 table -> grammar/data/idna_mapping.py
└── regenerate_root_zone_tld_data.py # tlds-alpha-by-domain.txt -> rules/data/root_zone_tlds.py

tests/capabilities/domain/
├── test_rfc_1034_name_syntax.py     # one file per rule publication (§5.2)
├── test_rfc_1035_label_length.py
├── test_unicode_uts46_statuses.py
├── test_rfc_5893_bidi_context.py
├── test_iana_root_zone_membership.py
└── test_capability_wild_variants.py # W1–W16 + E1–E18 golden rows (§2.1, §8)
tests/property/test_reentry_invariant.py   # EXTEND with Domain + output_format="unicode" (ADR-0010)
tests/integration/test_domain_idna_parity.py  # W2/W5 convergence, W7 non-transitional pin

# Alternative fused layout (single mandatory file) if review prefers BIC/IBAN style:
#   rules/iana_root_zone_membership.py  # registry + membership in ONE publication, kind="registry"
```

## 12. Test Strategy (mirrors `HOW_TO_ADD_NEW_CAPABILITY.md` §10 and BIC §12)

- **Unit per rule publication** (§5.2): shape accept/reject; 63/253 boundaries (E8/E9); hyphen edges (E10) + reserved 3rd/4th hyphens per D13 pin (W8); ACE decode failure (E6); root-zone membership positives/negatives (E7, W10); status-driven INVALID (E16/W13).
- **Grammar unit:** each §4.3 flow yields exactly one candidate span; ASCII/IDN affinity dedup covered (W1–W4); guard boundaries MISS on containers (W14/W15) and free text (§2.3).
- **Contract unit:** `output_format` resolution (`ascii` default → `unicode`); `requires_features` declared for every non-default knob; no rule source contains `output_format` (CI scan).
- **Property — re-entry (ADR-0010):** SUCCESS canonical re-canonicalizes to itself under the default contract *and* under `output_format="unicode"` (encode→decode→encode fixed point); **extend** `tests/property/test_reentry_invariant.py` per ADR-0010's new-capability mandate; A0 whole-input common-word exemption exercised (`suppress_common_words=True` on a whole-input word).
- **Property — information preservation (ADR-0011):** `unicode` is an encoding — `decode(encode(x)) == x` over generated valid U-label sets; no projection over recognition/validation information.
- **Integration — candidate qualification (ADR-0012):** assert every shipped SUCCESS candidate had LOOKUP corroboration (non-vacuous); assert the vacuity path is unreachable in v1.
- **Integration — golden corpus:** W1–W16 + E1–E18 through `canonicalize()`; W2 ≡ W5 convergence; W7 non-transitional pin; strip/Unicode-input proven by the input→canonical pairs themselves (`example.com.` → `example.com`, `münchen.de` → `xn--mnchen-3ya.de` — the notation carries no input-shape flags, §3.1); snapshot version asserted from the `iana_root_zone_membership` publication (`Provenance.version = "IANA tlds-alpha v2026092300"`, §5.2).
- **E2E CLI:** `uv run python -m paxman domain "münchen.DE."` → JSON canonical `xn--mnchen-3ya.de`; stdin and `--list` include `domain` (`paxman/cli.py`, coverage-exempt, smoke only).
- **Benchmarks:** add a Domain row to `benchmarks/harness.py` (CI-run); no legacy stages planned, so `benchmarks/grammar_stage_parity.py` is N/A (kernel-first, ADR-0009).
- **Coverage gate:** `fail-under = 95` over `paxman/core|capabilities|engine|api`; commands: `uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q`.
- **No skipped tests without justification** (project convention); test doubles stay local to the test file.

## 13. Open Decisions (with recommendations)

| # | Decision | Options | Recommendation | Blocking? |
|---|---|---|---|---|
| D1 | Capability name | `Domain` vs `DomainName` vs `Hostname` | `Domain` (MILESTONE wording: "Domain name / IDN") | scaffold |
| D2 | Canonical output | ASCII-only vs `ascii` + `unicode` formats | ASCII default + `unicode` (ADR-0011-safe, §6) | contract |
| D3 | Trailing root dot | strip (MILESTONE row 10) vs preserve (URL parity) | **strip**; document O1 asymmetry in both docs | grammar semantics |
| D4 | Transitional processing | non-transitional vs transitional | **non-transitional** (W7/E18 pin; RFC 5891 lean) | IDNA data module |
| D5 | Bare TLD input (`com`) | REJECT vs recognize | **REJECT** v1 (no PSL dependency, D9) | rules |
| D6 | Single-label names (`localhost`) | REJECT vs DEFER vs recognize | **DEFER** scope; v1 `INVALID` via the ≥2-label rule (E11, §5.4), opt-in feature later | scope |
| D7 | Underscore hosts (`_dmarc…`) | REJECT (STD3) vs recognize (DNS-legal) | **REJECT** v1; revisit for DKIM/SRV with `requires_features` | scope |
| D8 | Surrounding whitespace | reject raw vs trim-then-recognize | **reject raw** (determinism: trimming is Email/stdnum-style cleaning, offered later as a `clean` helper if demanded) | boundary spec |
| D9 | PSL involvement (public suffix vs registrable domain) | none vs bundled snapshot | **none** v1 — moving target, 10,330 rules, determinism cost | future |
| D10 | Textual length limit | 253 vs 255 chars | **253** (255-wire derivation, G9 documented) | length rule |
| D11 | Root-zone data pipeline | bundle machine list (+regenerator) vs pure PARSER regex | **bundle** — non-vacuous ADR-0012; avoids URL's vacuity-by-design (O3) | **needs build** |
| D12 | IDN TLD registry policy | UTS #46 only vs also IANA IDN tables | UTS #46 only v1 (tables = registry policy, D12 defer) | future |
| D13 | Reserved-hyphen profile (`ex--ample.com` — `--` at 3–4 without `xn--`) | `CheckHyphens=true` (INVALID — RFC 5890 §2.3.2.1 R-LDH usable only as XN-labels, RFC 5891 §4.2.3.1, registrar practice) vs `CheckHyphens=false` (accept — WHATWG/browser parity; real hosts such as `r3---sn-…` exist, UTS #46 §4.1 note) | **`true`** — UTS #46 §4.1 criterion 2 is conditional, so the flag MUST be pinned explicitly rather than left implicit; registry-correct side, costs one fixture | `unicode_uts46_statuses` (§7.2 step 4b) |

## 14. Ambiguity Analysis (Paxman-specific)

**Paragraph 1 — no single authority defines "a domain name".** The word names three overlapping objects: a DNS *name* (RFC 1034's tree label sequence, where `EXAMPLE.COM.` and `example.com.` are one node), a *host name* (RFC 952/1123 LDH discipline for ARPANET-lineage systems, narrower than DNS), and an *IDN label pair* (RFC 5890's A-label/U-label duality, where `xn--mnchen-3ya.de` and `münchen.de` are one entity only under validation). These specs were written twenty-three years apart for different audiences and disagree on underscores, single labels, and case. A canonicalizer must therefore *choose* an object: this report chooses the **DNS name in its A-label protocol form**, taking syntax from RFC 1034/1035/1123, identity from RFC 5890, and processing from UTS #46 — every other reading (host-with-port, URI authority, registered domain) is explicitly deferred or rejected rather than blurred into the value.

**Paragraph 2 — canonical direction is forced, presentation is not.** Only one direction preserves interoperability: Unicode → ASCII A-label, because protocols, zone files, and certificates carry A-labels (RFC 5890 §2.3.2.1), while U-labels exist only for display *with validation*. The reverse temptation — canonical Unicode — fails on three grounds: registry-published LDH strings would not round-trip without a decode step at every consumer, ADR-0011 forbids a canonical value that is a projection of the other (each must be an encoding of one entity), and mixed inputs (`XN--MNCHEN-3YA.DE` vs `münchen.de`) would fork identity. So the canonical value is lowercase ASCII without a trailing dot, and Unicode is reachable only through `format_value(output_format="unicode")`, whose losslessness is a property test (§12), not a hope. The DNS case-insensitivity argument (RFC 1035 §3.1) makes lowercasing identity-preserving rather than lossy, which is what lets A2 be a *fold* and not a decision between entities.

**Paragraph 3 — validity is three-layered, and the middle layer is the dangerous one.** Shape-validity is cheap and cited (RFC 1034/1035/1123); root-zone existence is citable only through a *snapshot* (IANA `tlds-alpha-by-domain.txt@2026092300`), and registry *registration* is unreachable without network world-knowledge. The tempting shortcut — a regex TLD alternation, as URL ships today — silently converts ADR-0012's vacuity exception from an emergency valve into the design's load-bearing wall, and it also invites an uncited "no numeric TLD" rule (G4) that no primary source actually states. Bundling the snapshot costs a generator tool and a version stamp but buys: non-vacuous candidate qualification, a citable rejection for `example.123` (LOOKUP miss, not invented prose), and determinism aligned with how IBAN and BIC already pin registry data. The remaining honest cost is drift: two IDNA tables inside one library (URL's and Domain's) must be pinned to the same UTS #46/Unicode version or the library contradicts itself (G8).

**Paragraph 4 — the capability boundary is drawn by containers, and neighbours disagree.** `user@example.com`, `https://example.com/`, `example.com:443`, `[::1]` are all *hosts in context*; each context already has a paxman owner (Email, URL, IP), and boundary guards (§4.4) make ownership decidable without rewriting input — a rule never strips `user@` to find a domain inside, and a container-adjacent span is never emitted. The one genuine neighbour disagreement is the trailing root dot: WHATWG URL preserves `example.com.` as a distinct host string, and URL's shipped behaviour follows it, while the MILESTONE row-10 intent for Domain is to strip. Stripping is right for Domain (re-entry, one entity per name, dig-`$ORIGIN` ergonomics) but creates a documented cross-capability asymmetry (O1): the same text canonicalizes differently depending on the capability asked — which is acceptable in paxman's model *only because* provenance records the strip and the two capabilities never feed each other's canonical values (import ban).

**Paragraph 5 — the remaining ambiguities are product decisions and must be pinned, not discovered.** Underscore hosts are simultaneously DNS-legal and STD3-illegal; single-label names are simultaneously essential (`localhost`) and root-zone-absent; whitespace trimming is simultaneously friendly and non-idempotent-prone; the public suffix list is simultaneously operationally essential and a non-normative, daily-changing community artifact. None of these have a primary-source answer for a *canonicalization library*, so each gets an explicit row (D5–D9) with a conservative v1 default (reject/defer, no PSL) and an opt-in path via `requires_features` when a real user asks. The cost of guessing wrong in the *liberal* direction is worse: silently accepting `_dmarc` selectors or registrable-domain truncation would bake policy into identity and break re-entry fixtures later, while guessing conservative costs only a documented `INVALID` and one roadmap row.

## 15. URL Reference (authoritative, fetched 2026-09-23)

Primary sources — what each one settles:

| # | URL | Settles |
|---|---|---|
| 1 | https://www.rfc-editor.org/rfc/rfc1034 | name syntax §3.1, empty labels, hierarchy, trailing-dot equivalence |
| 2 | https://www.rfc-editor.org/rfc/rfc1035 | §2.3.1 label charset/hyphen, §2.3.4 255-octet total, §3.1 case-insensitivity |
| 3 | https://www.rfc-editor.org/rfc/rfc1123 | §2.1 digit-first relaxation (the correct section — G7) |
| 4 | https://www.rfc-editor.org/rfc/rfc952 | original host-name LDH rules (history) |
| 5 | https://www.rfc-editor.org/rfc/rfc1591 | TLD delegation process (1994 — stale claim flagged, G3) |
| 6 | https://www.rfc-editor.org/rfc/rfc2396 | URI authority grammar — why `host:port`/`user@host` are containers |
| 7 | https://www.rfc-editor.org/rfc/rfc3490 | IDNA2003 (superseded — context only) |
| 8 | https://www.rfc-editor.org/rfc/rfc3491 | Nameprep (superseded — context only) |
| 9 | https://www.rfc-editor.org/rfc/rfc3492 | Punycode — ACE encoding, decode round-trip for E6 |
| 10 | https://www.rfc-editor.org/rfc/rfc3696 | clarifications on host naming practice |
| 11 | https://www.rfc-editor.org/rfc/rfc4343 | case-insensitivity rationale for folding |
| 12 | https://www.rfc-editor.org/rfc/rfc5890 | A-label/U-label definitions — canonical direction (A3) |
| 13 | https://www.rfc-editor.org/rfc/rfc5891 | input validation, operator-defined mapping, NFC (§7.2) |
| 14 | https://www.rfc-editor.org/rfc/rfc5892 | derived character properties, ContextJ/O (§7.2 step 5) |
| 15 | https://www.rfc-editor.org/rfc/rfc5893 | bidi rule for RTL labels |
| 16 | https://www.rfc-editor.org/rfc/rfc5894 | usage guidance, machine identifiers |
| 17 | https://www.rfc-editor.org/rfc/rfc5895 | casing/mapping (informational) — non-transitional lean |
| 18 | https://www.unicode.org/reports/tr46/ | UTS #46 v18.0.0 — statuses, processing, the citable profile |
| 19 | https://www.unicode.org/Public/idna/ | the mapping table itself (snapshot source) |
| 20 | https://url.spec.whatwg.org/#concept-domain-to-ascii | de-facto browser `domain to ASCII`; consulted, not pinned |
| 21 | https://www.iana.org/domains/root/db | authoritative TLD set (1,595 shown; G5) |
| 22 | https://data.iana.org/TLD/tlds-alpha-by-domain.txt | machine list v2026092300 — 1,438 entries → LOOKUP snapshot |
| 23 | https://www.iana.org/domains/idn-tables | registry IDN tables (replaces dead `/domains/idn-tlds`, G1) |
| 24 | https://www.icann.org/en/system/files/files/idn-guidelines-30jun23-en.pdf | ICANN IDN Guidelines v3.0 (2023) — policy context |
| 25 | https://publicsuffix.org/list/public_suffix_list.dat | PSL (10,330 rules) — deferred scope, D9 |

**Research gaps & citation hygiene (honest):**

| # | Gap | Why it matters | Closure |
|---|---|---|---|
| G1 | `https://www.iana.org/domains/idn-tlds` → **404** | dead citation found during research | cite https://www.iana.org/domains/idn-tables (live) |
| G2 | old ICANN guidelines URL (`idn-guidelines-2011-09-02-en`) → **404**; `publicsuffix.org/guide/` → use `/learn/` | policy freshness | cite v3.0 PDF (row 24) and https://publicsuffix.org/learn/ |
| G3 | RFC 1591's "no other TLDs" (1994) is **stale** — hundreds of gTLDs since 2012 | must not be cited as TLD-exclusivity authority | IANA root zone is the authority; RFC 1591 = process history only |
| G4 | **no primary source found** for "all-numeric TLD is forbidden" (no ICANN/IETF prose located) | `example.123` rejection would be uncited if regex-quoted | implement E7 as root-zone LOOKUP miss (§7.3) |
| G5 | Root Zone DB **1,595** vs machine list **1,438** (both fetched 2026-09-23) — unreconciled (A-label vs display counts likely) | snapshot completeness | diff both lists during implementation; stamp both counts |
| G6 | no authority decides **underscore hosts** / **single-label names** for a canonicalizer (DNS allows, STD3 forbids) | E11/R7 are product choices | resolve D6/D7 in the plan (§13) |
| G7 | RFC 1123 digit-first rule is **§2.1**, not RFC 1035 §2.3.1 (common mis-citation, incl. early notes of this research) | citation correctness | cite both: RFC 1035 §2.3.1 + RFC 1123 §2.1 |
| G8 | URL ships a UTS #46 table generated at some earlier Unicode version; Domain would ship v18.0.0 | two IDNA tables could drift inside one library | pin one UTS/Unicode version across both (D11/O2) |
| G9 | 253-char textual limit is a **derivation**, secondary consensus only (validator.js, commons-validator) | E9's number is not RFC prose | state derivation in rule docstring; D10 |

## 16. Evidence Completion — Resolved

- [x] Taxonomy — every written form of a domain name enumerated with RECOGNIZE/DEFER/REJECT disposition (§2.2, 22 rows)
- [x] Golden corpus specified — 16 wild variants (§2.1 W1–W16) + 18 edge fixtures (§8 E1–E18) as pytest rows (§12)
- [x] 14–18 wild variants — **16** (W1–W16)
- [x] Exactly 18 edge-case rows — **18** (E1–E18)
- [x] 20+ primary source URLs — **25** (§15 table; 34 citations incl. 9 labelled secondary)
- [x] 8+ tables — **17 tables** (§1×2, §2×2, §3×0, §4×2, §5×2, §8, §9, §10×2, §13, §15×2, appendix×1+)
- [x] 5+ code blocks — **11** (§2.1 pattern, §3.1 notation, §4.2 ×2, §5.1 spec stack, §5.2 layout, §6.1 contract, §6.2 capability + CLI, §7.1 limits, §7.2 sequence, §7.3 lookup + qualification, §10.1 bash, §11 tree)
- [x] 7–9 resolution-map rows — **8** (R1–R8)
- [x] 10+ open decisions — **13** (D1–D13)
- [x] 5-paragraph ambiguity analysis — §14 (paragraphs 1–5)
- [x] Cite-or-it-didn't-happen — every row/regex/length/example carries an RFC URL, UTS/IANA/ICANN URL, or codebase path; unanswerable questions declared as gaps (§15) instead of invented rules
- [ ] **needs — (requires infra/build decision):** the root-zone + IDNA snapshot pipeline (D11) and scope decisions D6/D7 are genuinely open; §16 leaves this unchecked by design

---

## Appendix A — Overlap & Cross-Capability Interaction (URL / Email / IP / TLD)

| # | Interaction | Nature | Handling |
|---|---|---|---|
| O1 | **URL** host trailing dot (`example.com.` preserved by WHATWG) vs Domain strip | behavioural asymmetry | document both sides; fixtures E1 (Domain) + URL host suite; probe 2026-09-24 confirms: `canonicalize("https://example.com./", URL)` → SUCCESS `https://example.com./` (dot preserved) |
| O2 | **URL** ships `rules/data/idna_uts46_mapping.py`; Domain needs the same table | duplicate data risk; **cross-capability import ban** | Domain ships its own generated module; long-term move to `paxman/shared_data/` (currency pattern) — plan item, not code now |
| O3 | **URL**'s TLD check is PARSER-regex → ADR-0012 vacuity | Domain can be stricter (root-zone LOOKUP) | Domain non-vacuous; note as URL follow-up, out of scope here |
| O4 | **Email** domain part | Email owns `user@host`; Domain rejects `@` whole-input | §4.4 guards; fixtures W14/E12 |
| O5 | **IP** literals | `192.168.0.1` is LDH-shaped | LOOKUP rejects it as a *name*; IP capability owns the literal (E14) |
| O6 | **TLD roadmap row 10** | sub-goal of this capability | folded into D3/D5 |
| O7 | **Country** (`.de` → Germany) | no overlap | Domain never maps TLD → country (world-knowledge ban) |

**Cross-capability triggers (conditions that would change this design):**

1. If URL later gains a root-zone LOOKUP, both consume one `shared_data` snapshot (Currency/Money precedent) — triggers O2/O3 merge.
2. If ADR-0010/0011/0012 are amended, §4.1/§6/§12 conclusions must be re-derived — Domain is the second capability designed against all three.
3. If PSL logic is ever added (D9), determinism demands a pinned list version + regenerator or re-entry/snapshot guarantees break.
4. If the kernel (`paxman/core/grammar/`, ADR-0009) grows a dedicated IDNA matcher kind, both IDNA grammars (URL, Domain) share it **via `paxman.core` only**.
5. If Email adopts IDN hosts (`用户@example.com`), Unicode-local-part stays with Email rules — Domain remains host-only.
6. If the IANA list format changes (v2026092300 today), the regenerator must fail loudly (IBAN-registry tooling precedent, `tools/regenerate_iban_registry_data.py`).
7. If generic `shared_data` snapshot tooling emerges, migrate root-zone/IDNA tables there to retire duplicated generators.

## Appendix B — What the Shipped URL, Email, IBAN and Currency Capabilities Teach Domain (verbatim precedent)

| Precedent | Source (codebase path) | Lesson for Domain |
|---|---|---|
| URL already does IDNA end-to-end: `domain_to_ascii`-style conversion + generated UTS #46 table | `paxman/capabilities/URL/parsing.py`, `URL/rules/data/idna_uts46_mapping.py`, `tools/regenerate_idna_uts46_data.py` | the *machinery* pattern is proven; Domain copies the *pattern* (own generated module), never the *module* (import ban) |
| URL's host grammar is recognition-side and regex-shaped; TLD = PARSER only | `URL/grammar/absolute_uri_recognition.py` | ships today under the ADR-0012 vacuity exception — Domain deliberately adds LOOKUP instead (O3, D11) |
| Trailing dots in URL hosts are preserved | `URL/parsing.py` host handling | asymmetry O1 must be documented, not "fixed" silently in either capability |
| Registry-kind rules with generated snapshots + regenerator tools | `tools/regenerate_iban_registry_data.py`, `tools/regenerate_bic_data.py`, `tools/regenerate_currency_data.py` | `iana_root_zone_membership.py` follows this exact shape (`kind="registry"`, completeness invariant, version stamp) |
| Cross-capability data sharing goes through `paxman/shared_data/` | `paxman/shared_data/currency_snapshot.json` → Currency + Money | the sanctioned seam for a shared IDNA/root-zone snapshot (O2) — capabilities never import each other |
| Email owns the `local@` grammar; rules are one publication per RFC | `paxman/capabilities/Email/rules/rfc_5322_ed2008.py`, `HOW_TO_ADD_NEW_CAPABILITY.md` §5 | Domain's rule files named per publication (§5.2); `@` never reaches Domain rules |
| Re-entry invariant suite exists and new capabilities must extend it | `tests/property/test_reentry_invariant.py`, ADR-0010 | Domain adds `ascii`/`unicode` fixed-point cases (§12) |
| Capability export completeness is test-enforced | `paxman/capabilities/__init__.py`, `tests/unit/test_capability_exports.py` | scaffolding PR must update exports + `register_all_shipped()` (`paxman/api/bootstrap.py`) |
| Scaffolder automates Step 0 | `tools/new_capability.py` | §10.1 — no hand-rolled layout |
| Benchmark harness is CI-run | `benchmarks/harness.py`, `benchmarks/grammar_stage_parity.py` | add Domain corpus row; parity harness N/A (kernel-first, ADR-0009) |
