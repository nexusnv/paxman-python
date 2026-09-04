# Paxman Domain Glossary

## Core Concepts

### Paxman
A **canonicalization authority resolver** — a library that takes ambiguous human input and returns what authoritative specifications say that input means, with full provenance. Paxman is both a **syntactic recognizer** (finds values in text) and a **semantic interpreter** (validates against authoritative specifications).

**Invariants:**
- **No fabrication:** Never guess, never infer, never suggest
- **Provenance-first:** Always cite authority-defined specifications, registries, policies
- **Deterministic:** Given the same input, the same contract, and the same library snapshot (fixed library version, registry contents, and rule-data tables), the pipeline yields the same canonical output — no world-knowledge, no clock, no environment-dependent ordering, no fuzzy logic, no network inference across recognition, validation, and canonicalization.
- **Re-entry invariant (fixed-point):** A `SUCCESS` canonical value `V` re-canonicalizes to `V` under the same **default** contract for any `output_format` — enforced by `tests/property/test_reentry_invariant.py`; custom `pinned_rules`/`excluded_rules`/`year` may break this. Whole-input canonical values that collide with `COMMON_WORDS` (`TO`, `en`, `ALL`) re-enter under `suppress_common_words=True` via the A0 whole-input exemption (#122), enforced by the extended property suite; new capabilities must extend that suite (ADR-0010).

### Capability
A domain module (e.g., Email) that:
- Defines a **Notation** (intermediate representation)
- Registers **Grammars** (recognition rules)
- Registers **Validation Rules** (semantic rules with provenance)
- Lives in `capabilities/<CapabilityName>/`

Every capability conforms to the same structural surface: `notation.py`, `contract.py`, `capability.py`, `grammar/`, `rules/` — see [The Capabilities](#the-capabilities) for the shipped set.

### Contract
User-facing configuration object that:
- **Toggles grammars ON/OFF** via `include_*` input-shape features (e.g., `include_obfuscated=True`) — a disabled grammar makes its inputs `MISSING`
- **Pins rules** to run only specific validation rules (e.g., `pinned_rules=["Section 3.4.1-addr-spec"]`)
- **Excludes rules** to skip specific validation rules (e.g., `excluded_rules=["Section 6.3-localhost"]`)
- **Pins year** to filter validation rules by `publication_year`
- **Passes parameters** to validation rules (e.g., `two_digit_base_year`)
  - Note: `output_format` is a *presentation* parameter consumed by the capability's `format_value()` seam — validation rules never read it (CI-scanned purity)
- Does NOT define Notation (that's internal to Capability)

When `pinned_rules` is set, `excluded_rules` is ignored — only the pinned rules run.

`create_contract()` is a static, keyword-only factory with a fixed common block first (`excluded_rules`, `pinned_rules`, `year`, `output_format`), then capability-specific parameters.

### Notation
Capability-defined intermediate representation that Grammars must produce:
- **Email:** `EmailNotation(local_part, domain_part)` → `["local_part", "domain_part"]`
- **Date:** `DateNotation(N1, N2, N3)` → `["N1", "N2", "N3"]` (position-sensitive: grammar determines meaning)
- **Country:** `CountryNotation(shape, value)` — `shape` discriminates `"alpha2"` / `"alpha3"` / `"numeric"` / `"name"`; `value` is the raw input (e.g., `"US"`, `"USA"`, `"840"`, `"United States"`)
- **Coordinates:** `CoordinatesNotation(latitude, longitude, altitude, coord_shape, compact)` — `latitude`/`longitude` are sign-normalized decimal-degree strings (minus only, no trailing zeros, `-0` folded to `0`, quantized to 6dp round-half-even), lat-first regardless of input order; `altitude` is metres as decimal string or `None`; `coord_shape` discriminates `"dd"` / `"ddm"` / `"dms"` / `"iso6709"` / `"geo_uri"` / `"geojson"`; `compact` is `f"{lat}, {lon}"` (+ `", {alt}"` when present). Grammar recognizes decimal pairs (signed or hemisphere-letter `N/S/E/W`, separators `[\s,;/]+`, optional `COORD`/`LAT` label), DMS/DDM with `°`/`D`/`*`, `′`/`'`/`m`, `″`/`"`/`s` and `''`→`″` fold, Geo URI `geo:lat,lon[,alt][;crs=wgs84][;u=...]`, ISO 6709 string-expression `±DD.DDD±DDD.DDD[/]` with optional altitude and `CRSWGS_84`, and GeoJSON lon-first bracketed pairs `[lon, lat[,alt]]`
- **Currency:** `CurrencyNotation(text, shape)` — `shape` is `"code"` / `"qualified_symbol"` / `"symbol"` / `"word"`; codes are grammar-folded to uppercase, words to lowercase, symbols keep exact casing
- **Money:** `MoneyNotation(currency_part, amount_part, currency_shape, amount_shape)` — verbatim currency + amount tokens with grammar-assigned shape discriminators
- **ISBN:** `ISBNNotation(shape, digits)` — `shape` is `"isbn10"` / `"isbn13"`, `digits` is the digit string (`X` only as final char of an isbn10 shape)
- **ISSN:** `ISSNNotation(digits)` — `digits` is the 8-character hyphen/space-stripped, uppercased string (grammar folds `x`→`X`); single lexical shape, no discriminator
- **Language:** `LanguageNotation(language, extlang, script, region, variant, extension, privateuse, grandfathered, compact, raw_value)` — `language` 2-8 lower, `extlang` 3-letter hyphen-joined (e.g. `cmn` for `zh-cmn`), `script` Title 4, `region` Upper 2|3-digit, `variant` lower prefix-constrained via `VARIANT_PREFIXES` dict (`sl-nedis` ok, `de-nedis` rejected), `grandfathered` lower (preferred via `GRANDFATHERED_PREFERRED`), `compact` BCP47 case-canonical tag or bare lower, `raw_value` trimmed lower for lexicon; grammar strips case/underscore via `StandardPre` (`_`→`-` in PipelineState, `raw_text` preserves original), rules own registry + Prefix + Deprecated chain + Suppress-Script (informative, never rejects)
- **BIC:** `BICNotation(bank_code, country_code, location_code, branch_code, compact)` — `bank_code` 4-char A-Z0-9, `country_code` 2-letter ISO 3166-1 plus XK, `location_code` 2-char A-Z0-9, `branch_code` 3-char or empty when BIC8, `compact` full 8 or 11 equals bank+country+location+branch, grammar uppercases and strips label, location second char 0/1/2 informative only
- **IBAN:** `IBANNotation(country_code, check_digits, bban, compact)` — `country_code` is the 2-letter ISO 3166-1 alpha-2 prefix, `check_digits` the 2-digit MOD 97-10 pair, `bban` the 1-30 alphanum remainder, `compact` the grammar-normalized candidate (≡ cc+dd+bban, uppercased with paper spaces stripped; may be shorter or longer, while the validation rule enforces the final 15–34-character ISO bound)
- **MacAddress:** `MacAddressNotation(compact, shape)` — `compact` is the uppercase hex collapse (12 hex EUI-48 or 16 hex EUI-64) and `shape` discriminates `"eui48"` / `"eui64"`; grammar strips separators (colon/hyphen/tri-dot/bare) and uppercases, fused `MAC` label included in `raw_text`; rules own structure (no checksum, I/G + U/L informative), derived OUI = `compact[:6]`
- **SIUnit:** `SIUnitNotation(text, shape)` — `shape` is `"symbol"` / `"name"` / `"compound"` / `"split_word_prefix"` / `"split_symbol_prefix"`; `text` is the unit expression as written (symbols keep exact casing, names are grammar-folded to lowercase, compounds keep the written form)
- **Element:** `ElementNotation(token, shape)` — `shape` discriminates `"symbol"` / `"name"` / `"atomic_number"`; `token` is the grammar-normalized designation (symbols in IUPAC case e.g. `Fe`, names lowercase e.g. `iron`, atomic numbers bare digits e.g. `26`); symbol matching is case-exact (`FE` unclaimed), names case-insensitive, atomic numbers label-required (`element 26` / `Z=26` — bare `26` unclaimed)
- **IP:** `IPNotation(address)` — `address` is the raw matched address text (not normalized; grammars emit mixed `::ffff:192.0.2.1` and IPv4 `192.0.2.1` separately)
- **Phone / URL:** capability-defined shapes for address / number / URI components

### Notation Type Example
```python
from dataclasses import dataclass


# Email Notation using frozen dataclass
@dataclass(frozen=True)
class EmailNotation:
    local_part: str
    domain_part: str
```

---

## The Capabilities

Paxman ships eighteen built-in capabilities (18 in `paxman/capabilities/__init__.py` and `paxman/api/bootstrap.py:_SHIPPED`, alphabetical by registry name), each wired to an authoritative specification:

| Capability | Domain | Authorities |
|------------|--------|-------------|
| **BIC** | Business identifier codes | ISO 9362:2022, ISO 3166-1 (country codes plus XK) |
| **Coordinates** | WGS 84 coordinates | ISO 6709:2022, RFC 5870, RFC 7946 |
| **Country** | Country codes/names | ISO 3166, CLDR |
| **Currency** | Currency identifiers | ISO 4217, CLDR |
| **Date** | Dates | ISO 8601, US federal, EN 50160 |
| **Element** | Chemical elements | IUPAC Red Book 2005, IUPAC Periodic Table 04 May 2022 |
| **Email** | Email addresses | RFC 5322, RFC 6761 |
| **IBAN** | Bank account numbers | ISO 13616-1:2020, ISO/IEC 7064:2003 (MOD 97-10) |
| **IP** | IP addresses | RFC 791 (RFC 1123 §2.1), RFC 4291 §2.2, RFC 5952 |
| **ISBN** | ISBNs | ISO 2108, ISBN Users' Manual, ISBN Range Message |
| **ISSN** | Serial identifiers | ISO 3297:2022 |
| **Language** | Language identifiers | ISO 639-1:2002, ISO 639-2:1998, ISO 639-3:2007, ISO 639-5:2008, BCP 47 RFC 5646, IANA Language Subtag Registry (File-Date 2026-08-08), CLDR (localized, gated) |
| **MacAddress** | MAC addresses | IEEE Std 802-2024 |
| **Money** | Money amounts | ISO 4217, CLDR |
| **ORCID** | Researcher identifiers | ISO 27729:2024, MOD 11-2 |
| **Phone** | Phone numbers | ITU-T E.164, RFC 3966, NANP |
| **SI Unit** | SI unit expressions | BIPM SI Brochure, ISO 80000-1 |
| **URL** | URLs | WHATWG URL Standard |

Capability classes are exported from `paxman/capabilities/__init__.py` as acronym aliases (`EmailCapability as Email`, etc.); the export list is enforced by `tests/unit/test_capability_exports.py`.

**Note:** the **SI Unit** capability is the first whose canonical value is case-meaningful (`K` kelvin vs `k` kilo). It canonicalizes unit expressions only (symbols, names, product/quotient compounds) to the canonical symbol form; no quantities, no magnitudes, no name-compounds.

---

## Pipeline Components

### Grammar (Recognition Rule)
Syntactic extraction rules that:
- Scan raw text for patterns
- Produce **span-bearing `RecognitionMatch` objects** (notation + half-open `[start, end)` span + matched `raw_text`) — never bare notations
- Live in `capabilities/<CapabilityName>/grammar/`
- Are **selected by the orchestrator** from the contract's `active_grammars`, or from every shipped `get_grammars()` entry when the contract returns `None` (the base default)
- Do NOT validate, de-duplicate, or order — the engine owns containment dedup and document ordering
- Only recognize (syntax, shape, lexicon keys) — never map tokens to canonical values, never import rule-layer data

### Validation Rule
Semantic rules that:
- Accept **Notation** (not raw input)
- Are backed by **Provenance** (authority specification)
- Use **Contract parameters** (e.g., `two_digit_base_year`) — never `output_format` (presentation lives in the capability's formatting seam)
- Produce **Candidate** with canonical value
- Live in `capabilities/<CapabilityName>/rules/`
- Are filtered by **pinned_rules** (if set, only those rules run) or **excluded_rules**
- Are filtered by **year** (publication_year ≤ contract.year)

### Rule Structure
Each rule file pins to **ONE publication** and contains **ONE or more rules** (sections):

```python
# capabilities/Email/rules/rfc_5322_ed2008.py

from paxman.core.domain import Provenance, Rule, RuleStrategy

# Publication-level provenance (one per file)
PUBLICATION = Provenance(
    authority="IETF",
    specification_name="RFC 5322",
    kind="specification",
    reference_url="https://tools.ietf.org/html/rfc5322",
    version="2008",
    lifecycle="active",
    publication_year=2008,
)

# Patterns compiled once at module scope, not per match call.
_LOCAL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+$")
_DOMAIN_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class Section341AddrSpec(Rule[EmailNotation]):
    """RFC 5322 Section 3.4.1 - addr-spec"""

    name = "Section 3.4.1-addr-spec"
    strategy = RuleStrategy.REGEX
    provenance = PUBLICATION
    citation = "Section 3.4.1 (addr-spec)"  # Human-readable citation
    target_semantics = frozenset({"rfc5322_addr_spec"})
    requires_features = frozenset()  # authority features this rule gates on

    def matches(self, notation: EmailNotation, contract: Contract) -> bool:
        """Check if notation matches addr-spec pattern."""
        return bool(
            _LOCAL_PATTERN.match(notation.local_part)
            and _DOMAIN_PATTERN.match(notation.domain_part)
        )

    def normalize(self, notation: EmailNotation, contract: Contract) -> str:
        """Normalize to canonical email format."""
        return f"{notation.local_part.lower()}@{notation.domain_part.lower()}"
```

Every rule declares six metadata attrs — `name`, `strategy`, `provenance`, `citation`, `target_semantics` (non-empty `frozenset[str]`), `requires_features` (`frozenset[str]`) — enforced at import time by `Rule.__init_subclass__`. Every grammar declares a `semantics` string — the meaning id its recognized notations carry (its identity id by default; a coalesced id shared by same-meaning grammars, e.g. the standard and obfuscated Email grammars both declare `"rfc5322_addr_spec"`) — enforced as a non-empty `str` at import time by `Grammar.__init_subclass__`. Rules never raise and never read `output_format`.

### Notation Purpose
Notation exists for **placement-sensitive rules**:
- **Dates:** `["01", "02", "2026"]` — position matters (DD/MM/YYYY vs MM/DD/YYYY)
- **Email:** `["azahari", "gmail.com"]` — position matters (local vs domain)
- **Country / Currency / ISBN:** a `shape` discriminator field carries which grammar produced the token (e.g., `CountryNotation(shape="name", value="United States")`); rules dispatch on shape

The resolver **consumes notation** and outputs a canonical_value (not notation).

### Rule Strategies
| Strategy | Use Case | Example |
|----------|----------|---------|
| `REGEX` | Pattern matching | Email addr-spec validation |
| `LOOKUP_TABLE` | Table lookup | Currency ISO 4217 codes, country codes |
| `PARSER` | Value parsing | Date parsing, URL parsing |

### LookupTable Example
```python
# capabilities/Currency/rules/iso_4217_ed2015.py


class SectionCode(Rule[CurrencyNotation]):
    """ISO 4217 Section 3 - Currency and funds codes"""

    name = "Section 3-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    target_semantics = frozenset(
        {"code_recognition", "symbol_recognition", "word_recognition"}
    )
    requires_features = frozenset()

    def matches(self, notation: CurrencyNotation, contract: Contract) -> bool:
        """Check if the code/symbol/word maps to a known currency code."""
        return notation.text in self.TABLE

    def normalize(self, notation: CurrencyNotation, contract: Contract) -> str:
        """Return canonical ISO 4217 alpha-3 code."""
        return self.TABLE[notation.text]
```

Authority-backed lookup tables live in `rules/data/` (e.g., `iso4217_list_one.py`, `cldr_currencies.py`), separated from rule logic; lexicon keys serving grammars live in `grammar/data/`. The Currency + Money data set is generated from the shared snapshot `paxman/shared_data/currency_snapshot.json` (CLDR v47 + ISO 4217) via `tools/regenerate_currency_data.py`; other generated modules come from their own generators: the ISBN range message (`tools/regenerate_isbn_range_data.py`), the URL IDNA UTS #46 mapping (`tools/regenerate_idna_uts46_data.py`), and the SIUnit prefixed-unit and grammar token tables (`tools/regenerate_si_prefix_data.py`) — everything else is maintained in place.

### Parser Example
```python
# capabilities/Date/rules/iso_8601_ed2019.py


class Section431CalendarDate(Rule[DateNotation]):
    """ISO 8601 Section 4.3.1 - Calendar date"""

    name = "Section 4.3.1-calendar-date"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    target_semantics = frozenset({"iso8601_calendar_date"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Try to parse as ISO 8601 date.

        ISO grammar maps: N1=year, N2=month, N3=day
        """
        try:
            year, month, day = int(notation.N1), int(notation.N2), int(notation.N3)
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize to ISO 8601 format."""
        year, month, day = int(notation.N1), int(notation.N2), int(notation.N3)
        return f"{year:04d}-{month:02d}-{day:02d}"
```

### Grammar File Structure
```python
# paxman/capabilities/Email/grammar/standard_recognition.py

import re

from paxman.core.domain import Grammar, RecognitionMatch
from paxman.capabilities.Email.notation import EmailNotation

# Pattern compiled once at module scope, not per recognize() call.
_STANDARD_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


class StandardEmailGrammar(Grammar[EmailNotation]):
    """Standard email recognition: user@domain.tld"""

    name = "standard_recognition"
    semantics = "rfc5322_addr_spec"  # coalesced — shared with obfuscated_recognition

    def recognize(self, text: str) -> list[RecognitionMatch[EmailNotation]]:
        """Extract span-bearing email matches from text."""
        return [
            RecognitionMatch(
                notation=EmailNotation(
                    local_part=match.group(0).split("@")[0],
                    domain_part=match.group(0).split("@")[1],
                ),
                start=match.start(),
                end=match.end(),
                raw_text=match.group(0),
            )
            for match in _STANDARD_EMAIL_PATTERN.finditer(text)
        ]
```

### Date Ambiguity Example
```python
# Input: "01/02/2026"
# Each grammar wraps its own notation mapping in a span-bearing RecognitionMatch:
#   ISO grammar:    N1="2026", N2="01", N3="02"  (N1=year, N2=month, N3=day)
#   US grammar:     N1="01",   N2="02", N3="2026" (N1=month, N2=day, N3=year)
#   European grammar: N1="01", N2="02", N3="2026" (N1=day, N2=month, N3=year)

# Rule 1: ISO 8601 — receives ISO notation
# N1=year=2026, N2=month=01, N3=day=02 → VALID → "2026-01-02"

# Rule 2: US federal — receives US notation
# N1=month=01, N2=day=02, N3=year=2026 → VALID → "2026-01-02"

# Rule 3: EN 50160 (European) — receives European notation
# N1=day=01, N2=month=02, N3=year=2026 → VALID → "2026-02-01"

# Result: 2 distinct canonical values → AMBIGUOUS
```

### Date Capability Details

The Date capability has **1 grammar (`date`) with 4 candidates** and **3 validation rules** (ADR-0009 §9.6 `candidates` kind — Date 4→1):

#### Grammars (Recognition)

| Candidate | Delimiter | N1 (first) | N2 (second) | N3 (third) | Notes |
|---------|-----------|------------|-------------|------------|-------|
| iso8601 | `-` | year | month | day | 4-digit year only |
| slash_iso | `/` | year | month | day | 4-digit year; shares ISO position mapping |
| us | `/` | month | day | year | Supports 2-digit years |
| european | `/` | day | month | year | Supports 2-digit years |

Represented as `CandidatesMatcher` candidates inside a single `DateGrammar`; legacy per-format files remain on disk until parity removal. European, US, and slash_iso candidates share `/` as delimiter. The ambiguity arises from different position mappings, not delimiters; a leading 4-digit year is unambiguous (slash_iso only), while a leading 1–2-digit field is ambiguous between US and European (`all` strategy keeps `01/02/2026` AMBIGUOUS).

#### Validation Rules

| Rule | Standard | Canonical Output |
|------|----------|------------------|
| ISO 8601 | ISO 8601:2019 | `YYYY-MM-DD` |
| US federal | US government standard | `YYYY-MM-DD` |
| EN 50160 | European EN 50160 | `YYYY-MM-DD` |

All rules normalize to ISO 8601 format (`YYYY-MM-DD`) regardless of input grammar.

### ORCID

The ORCID capability has **1 grammar** and **2 validation rules**:

#### Notation

`ORCIDNotation(compact, hyphenated, uri, check, is_uri)` — all `str`. `compact` is the 16-character hyphens-removed uppercase form (15 digits + check `0-9`/`X`), `hyphenated` is the `XXXX-XXXX-XXXX-XXXC` presentation (three hyphens, trailing `X` uppercase), `uri` is `https://orcid.org/XXXX-XXXX-XXXX-XXXC`, `check` is the final character `0-9` or `X`, `is_uri` is `"true"` when the raw input carried an `orcid.org` prefix else `"false"`.

#### Grammar (Recognition)

| Grammar | Pattern | Notes |
|---------|---------|-------|
| `orcid_recognition` | optional `ORCID`/`ISNI` label (`[\s:-]+`) and optional `https?://(www.)?orcid.org/` host, then hyphen-only `4-4-4-4` payload `\d{4}-\d{4}-\d{4}-\d{3}[\dX]` ending `[0-9X]` | `word_only` guards on both sides, inline `(?ai:)` ASCII flags on label/host/payload, case-insensitive `X` folded to uppercase; glued-label lookahead |

#### Validation Rules

| Rule | Standard | Canonical Output |
|------|----------|------------------|
| `Section 4-orcid-structure` | ISO 27729:2024 Section 4 | `XXXX-XXXX-XXXX-XXXC` (hyphenated) |
| `Section A-mod11-2-check-character` | ISO 27729:2024 Annex A (MOD 11-2) | `XXXX-XXXX-XXXX-XXXC` (hyphenated) |

Both rules validate the full conjunction (structure + MOD 11-2) and carry dual provenance; each produces the hyphenated canonical value.

#### Formats

Default `orcid` (hyphenated `XXXX-XXXX-XXXX-XXXC`); offered `uri` (`https://orcid.org/XXXX-XXXX-XXXX-XXXC`) and `compact` (16 chars, no hyphens). Presentation is via `Capability.format_value()` only; rules always normalize to the default.

### MacAddress

The MacAddress capability has **1 grammar** and **1 validation rule**:

#### Notation

`MacAddressNotation(compact, shape)` — `compact` is the uppercase hex collapse (12 hex EUI-48 or 16 hex EUI-64) and `shape` is `"eui48"`/`"eui64"` length discriminator; grammar strips separators and uppercases, fused `MAC` label included in `raw_text`.

#### Grammar (Recognition)

| Grammar | Pattern | Notes |
|---------|---------|-------|
| `mac_address_recognition` | EUI-48/EUI-64, colon/hyphen/tri-dot/bare, optional fused `MAC` label (`[\s:-]+`), case-insensitive | `mac_midrun` guards on both sides, per-separator branches (mixed separators never match), 64-bit before 48-bit and 16-hex before 12-hex ordering, 48-bit-only truncation guard `(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))` |

#### Validation Rules

| Rule | Standard | Canonical Output |
|------|----------|------------------|
| `Section 8.2-eui-structure` | IEEE Std 802-2024 Section 8.2 | `XX:XX:XX:XX:XX:XX` colon uppercase (8 groups for EUI-64) |

The I/G bit (0x01) and U/L bit (0x02) are informative predicates only — broadcast, nil, multicast, locally administered, and FF-FE/FF-FF mid-address markers are valid; no checksum.

#### Formats

Default `colon` (uppercase colon-separated, identity via `normalize()`); offered `hyphen` (`XX-XX-XX-XX-XX-XX`), `bare` (12/16 hex no separators), `cisco` (tri-dot `XXXX.XXXX.XXXX` / `XXXX.XXXX.XXXX.XXXX` for EUI-64), `eui64` (FF:FE insertion from EUI-48, identity for EUI-64). `bit_reversed` (RFC 2469 per-octet bit swap) was offered through `v0.3.1` and removed in `v0.4.0` (ADR-0010: not a fixed point, `f(f(x))==x`). Presentation is via `Capability.format_value()` only; rules always normalize to the default.

### Contract Rule Exclusion
```python
from paxman.capabilities import Email

# User knows input is localhost, excludes standard validation
contract = Email.create_contract(excluded_rules=["Section 3.4.1-addr-spec"])
paxman.canonicalize("user@localhost", contract)

# Or with year pinning
contract = Email.create_contract(excluded_rules=["Section 6.3-localhost"], year=2008)
paxman.canonicalize("user@example.com", contract)
# Result: "user@example.com" → SUCCESS
```

### Contract Rule Pinning
```python
from paxman.capabilities import Email

# Pin to specific rules — only these run, excluded_rules is ignored
contract = Email.create_contract(pinned_rules=["Section 3.4.1-addr-spec"])
paxman.canonicalize("user@example.com", contract)

# Pin + year filter — both apply
contract = Email.create_contract(
    pinned_rules=["Section 3.4.1-addr-spec", "Section 6.3-localhost"], year=2010
)
# Only rules matching both pinning and year filter are active
```

### Presentation: format_value and output_format

Presentation is a single seam, not a rule concern:
- `output_format` is always optional (`None` / `"default"` / the capability's `DEFAULT_OUTPUT_FORMAT` resolve to the default; offered formats resolve to themselves; anything else raises `ContractError`). Resolved once in `CapabilityContract.__post_init__`; contracts declare `DEFAULT_OUTPUT_FORMAT` / `OFFERED_OUTPUT_FORMATS` class vars.
- `format_value()` on the capability is the **ONLY presentation seam** — `normalize()` always returns the default canonical form.
- Rules never reference `output_format` (CI-scanned purity); formatting adds no provenance; offered formats must preserve the capability's ambiguity contract.
- Only capabilities with non-empty `OFFERED_OUTPUT_FORMATS` override `format_value()` — e.g., Date (`"ISO"`/`"US"`), ISBN (`"isbn13"`/`"hyphenated"`), Money (`"code_amount"`/`"compact"`), Phone (`"e164"`/`"rfc3966"`/`"national"`).

### Feature Gating — two loci, two statuses

Input-shape and authority features gate at different points and produce different statuses:
- **Input-shape features** (`include_*`) toggle grammars via the contract's `active_grammars` property — implemented only by the gated capabilities (Email, IP, ISBN); other contracts inherit the base `None` default, which runs every shipped grammar. A disabled grammar never recognizes → its inputs are **`MISSING`**.
- **Authority features** gate rules via `requires_features` (declared on the rule). The rule is dropped from the run → recognized but unvalidated input is **`INVALID`**.
- Never gate inside `matches()` / `recognize()`; never cast a contract to read `include_*` flags inside a rule (`typing.cast` is only for validity-affecting parameters).

Example: Currency's `default_currency` opt-in resolves a shared bare symbol (`"$"`) only when the code is one of that symbol's own candidate codes; otherwise the bare symbol is `INVALID` (recognized, no authority).

### RecognizedRep
Data class carrying recognition output. Produced by the engine from each
span-bearing `RecognitionMatch` after recognition, so the producing span and
raw text stay traceable end to end:
```python
@dataclass(frozen=True)
class RecognizedRep(Generic[NotationT]):
    notation: NotationT  # capability-defined shape
    contract: Contract  # contract configuration
    grammar: GrammarRule  # which grammar produced this
    start: int  # half-open start offset of the producing match
    end: int  # half-open end offset of the producing match
    raw_text: str  # matched substring (len(raw_text) == end - start)
```

### Candidate
Data class carrying validation output:
```python
@dataclass(frozen=True)
class Candidate:
    value: str  # canonical value
    recognition_rule: str  # which grammar produced notation
    validation_rule: str  # which rule validated it
    provenance: tuple[Provenance, ...]  # authorities backing this value
```

### Provenance
Authority citation for a validated value:
```python
@dataclass(frozen=True)
class Provenance:
    authority: str  # "IETF", "ISO", "W3C"
    specification_name: str  # "RFC 5322 §3.4.1"
    kind: str  # "specification" | "registry" | "policy"
    reference_url: str  # "https://..."
    version: str | None  # "2008" or None if not versioned
    lifecycle: str  # "active" | "deprecated" | "superseded"
    publication_year: int  # year this provenance came into effect
```

### GrammarRule
Reference to a grammar that produced a RecognizedRep:
```python
@dataclass(frozen=True)
class GrammarRule:
    """Reference to a grammar that produced a RecognizedRep."""

    capability_name: str  # "email"
    grammar_name: str  # "standard_recognition"
```

**Naming Convention:**
- `capability_name`: Lowercase capability name (e.g., "email", "date", "country")
- `grammar_name`: Lowercase, underscore-separated grammar name (e.g., "standard_recognition", "obfuscated_recognition")
- Grammar names are unique within a capability but may not be globally unique
- The `capability_name` field ensures global uniqueness

### RuleStrategy
Validation strategy for a rule:
```python
from enum import Enum


class RuleStrategy(Enum):
    """Validation strategy for a rule."""

    REGEX = "regex"
    LOOKUP_TABLE = "lookup_table"
    PARSER = "parser"
```

---

## Execution Result

### Resolution (Status Enum)
```python
from enum import Enum


class Resolution(Enum):
    """Status of the canonicalization execution."""

    MISSING = "missing"  # No RecognizedReps produced (fails-fast at recognition)
    INVALID = "invalid"  # Recognized, but no provenance validates
    SUCCESS = "success"  # Single canonical value resolved
    AMBIGUOUS = "ambiguous"  # Multiple conflicting canonical values
```

### ExecutionResult
Final output from `paxman.canonicalize()`. **Engine responsibility** — not capability.

```python
@dataclass(frozen=True)
class ExecutionResult:
    status: Resolution  # Enum status (computed by engine)
    canonicalized_value: str | None  # Extracted from candidates (if SUCCESS)
    candidates: tuple[Candidate, ...]  # Produced by capability validation rules
    contract: Contract  # Passed through from user
    version_stamp: VersionStamp  # Computed by engine (records library version)
```

**Responsibility Split:**
| Component | Responsibility |
|-----------|----------------|
| **Capability** | Produces candidates via validation rules |
| **Engine** | Shapes ExecutionResult, computes status, attaches VersionStamp |

### Resolution Semantics
| Resolution | Phase | Meaning | Candidates | canonicalized_value |
|------------|-------|---------|------------|---------------------|
| `MISSING` | Recognition | No RecognizedReps produced (fails-fast) | `[]` | `None` |
| `INVALID` | Validation | Recognized, but no provenance validates | `[]` | `None` |
| `SUCCESS` | Validation | Single canonical value resolved | `≥1` (all same value) | `str` |
| `AMBIGUOUS` | Validation | Multiple conflicting canonical values | `≥2` (different values) | `None` |

### VersionStamp
Library version provenance:
```python
@dataclass(frozen=True)
class VersionStamp:
    paxman_version: str  # library version
```

---

## Error Handling

### Exception Hierarchy
```python
class PaxmanError(Exception):
    """Base exception for all Paxman errors."""

    pass


class ContractError(PaxmanError):
    """Raised when contract is malformed or invalid."""

    pass


class CapabilityError(PaxmanError):
    """Raised when no capability can claim the process."""

    pass


class RecognitionError(PaxmanError):
    """Raised when grammar fails to parse input (malformed regex, etc.).

    ``original_error`` is the underlying exception for failures inside
    ``Grammar.recognize()``; it is ``None`` for structural failures the
    engine itself detects (e.g. a malformed match returned by a grammar).
    """

    def __init__(
        self, rule: str, message: str, original_error: Exception | None = None
    ) -> None:
        self.rule = rule
        self.original_error = original_error
        super().__init__(f"[{rule}] {message}")


class ValidationError(PaxmanError):
    """Raised when validation rule encounters unexpected error."""

    def __init__(self, rule: str, message: str, original_error: Exception) -> None:
        self.rule = rule
        self.original_error = original_error
        super().__init__(f"[{rule}] {message}")
```

### Error Scenarios
| Scenario | Exception | Example |
|----------|-----------|---------|
| Contract missing required fields | `ContractError` | Contract with invalid field types |
| Unknown capability name | `CapabilityError` | `canonicalize("input", contract_with_unknown_name)` |
| Grammar regex malformed | `RecognitionError` | Invalid regex pattern in grammar file |
| Validation rule crashes | `ValidationError` | Unexpected None in provenance lookup |
| Registry frozen, register attempted | `CapabilityError` | `register_capability()` after first call |

**Note:** INVALID and AMBIGUOUS are output states (Resolution enum), not exceptions.

---

## Usage Examples

### Basic Usage
```python
import paxman
from paxman.capabilities import Email
from paxman.core.domain import Resolution
from paxman.core.discovery import register_capability

# Register capability (required before first use)
register_capability(Email())

# Canonicalize an email
result = paxman.canonicalize(
    "azahari at gmail dot com", Email.create_contract(include_obfuscated=True)
)

if result.status == Resolution.SUCCESS:
    print(f"Canonical: {result.canonicalized_value}")
    print(f"Provenance: {result.candidates[0].provenance}")
else:
    print(f"Status: {result.status}")
```

### Date with Year Pinning
```python
from paxman.capabilities import Date

# Pin to 2019, include ISO 8601 rule (publication_year=2019)
contract = Date.create_contract(year=2019)
result = paxman.canonicalize("2026-01-02", contract)

# Result: "2026-01-02" (ISO 8601 grammar + rule)
```

### Custom Capability Registration
```python
from paxman import register_capability
from mypackage import MyCapability, MyContract

# Register before first canonicalize() call
register_capability(MyCapability())

# Now use it
result = paxman.canonicalize("input", MyContract())
```

### Inspecting Provenance
```python
result = paxman.canonicalize("test@example.com", Email.create_contract())

for candidate in result.candidates:
    print(f"Value: {candidate.value}")
    print(f"Grammar: {candidate.recognition_rule}")
    print(f"Rule: {candidate.validation_rule}")
    for prov in candidate.provenance:
        print(f"  Authority: {prov.authority}")
        print(f"  Specification: {prov.specification_name}")
        print(f"  URL: {prov.reference_url}")
```

---

## Capability Registration

### Capability Registry
- **Built-in capabilities:** Exported from `paxman/capabilities/__init__.py` (acronym aliases, enforced by `test_capability_exports.py`) — **registration is explicit**, via `register_capability(Email())` before first use
- **User-registered capabilities:** Added via `register_capability()` before first call
- **Registry freezes** at the start of each `run_capability()` call (engine responsibility)
- **Duplicate registration** raises `CapabilityError` — each capability name must be unique.
- **Attempting to register after freeze raises `CapabilityError`**

**Note:** The registry freeze happens at the start of each pipeline run, not just once. In testing, use `reset_registry()` between tests to allow re-registration. `freeze_registry()` is available for explicit control.

### Capability Versioning
- Capabilities do **not** declare their own versions — the `Capability` surface carries only `name`, grammars, rules, and the presentation seam.
 - Library version is resolved in `paxman/engine/orchestrator.py` — `PAXMAN_VERSION = _resolve_version()` reads the installed `paxman` package version via `importlib.metadata` (falling back to `"0.2.0"`); source of truth is `version = "0.2.0"` in `pyproject.toml`.
- Referenced in `VersionStamp.paxman_version`

### Contract Protocol
```python
# paxman/core/contract.py

from typing import Protocol, Any
from collections.abc import Sequence


class Contract(Protocol):
    """Base protocol for all capability contracts."""

    @property
    def capability_name(self) -> str:
        """Name of the capability this contract configures."""
        ...

    @property
    def active_grammars(self) -> Sequence[str] | None:
        """Grammar names to activate; None runs every shipped grammar."""
        ...

    @property
    def excluded_rules(self) -> Sequence[str]:
        """List of rule names to exclude."""
        ...

    @property
    def pinned_rules(self) -> Sequence[str] | None:
        """Pin to specific rules. If set, ONLY these rules run.

        Mutually exclusive with excluded_rules. When pinned_rules is set,
        excluded_rules is ignored.
        """
        ...

    @property
    def year(self) -> int | None:
        """Year for temporal filtering (publication_year ≤ year)."""
        ...

    @property
    def output_format(self) -> str | None:
        """Output format for canonical values (e.g., 'ISO', 'US')."""
        ...
```

Contracts subclass `CapabilityContract` (never `Contract` directly), are `@dataclass(frozen=True)` **without** `slots=True`, and set `DEFAULT_OUTPUT_FORMAT` / `OFFERED_OUTPUT_FORMATS` and `capability_name` via `field`. Every contract also carries `extra_grammars: tuple[str, ...] = ()` — the community-extension opt-in (names registered via `paxman.register_grammar()`; unknown names are silently skipped). `active_grammars` is optional: only feature-gated capabilities (Email, IP, ISBN) implement it; others inherit the base `None` default (run every shipped grammar).

---

## Directory Structure

```
paxman/
├── __init__.py                    # Public API exports (canonicalize, register_capability,
│                                  #   register_all_shipped, list_* , register_grammar/rule, CapabilityError)
├── py.typed                       # PEP 561 marker
├── cli.py                         # CLI: `paxman` console script / `python -m paxman` (--list, --json, stdin)
├── __main__.py                    # python -m paxman entry point
├── api/
│   ├── __init__.py
│   ├── bootstrap.py               # _SHIPPED (18 capabilities, alphabetical; paxman/capabilities/__init__.py exports 18), register_all_shipped(), list_shipped_capabilities()
│   └── canonicalize.py            # Public canonicalize() function → run_capability()
├── shared_data/
│   └── currency_snapshot.json     # CLDR v47 + ISO 4217 snapshot → Currency + Money data via tools/regenerate_currency_data.py
├── core/
│   ├── __init__.py                # Re-exports domain vocabulary + registry functions
│   ├── capability.py              # Capability abstract class
│   ├── capability_contract.py     # CapabilityContract base (output_format policy)
│   ├── contract.py                # Contract protocol + resolve_output_format
│   ├── discovery.py               # Capability registry (register/freeze/reset/list)
│   ├── domain.py                  # Provenance, Candidate, Rule, Grammar, Notation, etc.
│   ├── errors.py                  # Exception hierarchy
│   ├── extensions.py              # Community grammar/rule registries (extra_grammars opt-in)
│   └── grammar/                   # Capability-agnostic recognition machinery (boundary guard,
│                                  #   composer, lexicon alternation, pipeline grammar, stages)
├── engine/
│   ├── __init__.py
│   └── orchestrator.py            # run_capability() pipeline orchestrator + ExecutionResult
└── capabilities/
    ├── __init__.py                # Acronym alias exports (Email, Date, Country, ...) + __all__
    ├── BIC/                       # grammar/ (1) + rules/ (1) — ISO 9362:2022, ISO 3166-1
    │   ├── __init__.py
    │   ├── capability.py          # BICCapability
    │   ├── contract.py            # BICContract
    │   ├── notation.py            # BICNotation (bank_code, country_code, location_code, branch_code, compact)
    │   ├── grammar/               # bic_recognition
    │   └── rules/                 # iso_9362_ed2022 (structure + country lookup, 250 codes incl. XK)
    ├── Coordinates/               # grammar/ (1) + rules/ (3) — ISO 6709:2022, RFC 5870, RFC 7946
    │   ├── capability.py          # CoordinatesCapability
    │   ├── contract.py            # CoordinatesContract
    │   ├── notation.py            # CoordinatesNotation (latitude, longitude, altitude, coord_shape, compact)
    │   ├── grammar/               # coordinates_recognition
    │   └── rules/                 # iso_6709_ed2022, rfc_5870_ed2010, rfc_7946_ed2016
    ├── Element/                     # grammar/ (1) + rules/ (2) + grammar/data/ + rules/data/ — IUPAC Red Book 2005, Periodic Table 04 May 2022
    │   ├── capability.py          # ElementCapability
    │   ├── contract.py            # ElementContract
    │   ├── notation.py            # ElementNotation (token, shape)
    │   ├── grammar/               # element_recognition
    │   ├── grammar/data/          # element_keys
    │   ├── rules/                 # iupac_red_book_2005, iupac_periodic_table_ed2022
    │   └── rules/data/            # periodic_table_ed2022
    ├── Email/                     # grammar/ (3) + rules/ (2) — RFC 5322, RFC 6761
    │   ├── __init__.py
    │   ├── capability.py          # EmailCapability
    │   ├── contract.py            # EmailContract
    │   ├── notation.py            # EmailNotation dataclass
    │   ├── grammar/
    │   │   ├── standard_recognition.py
    │   │   ├── obfuscated_recognition.py
    │   │   └── localhost_recognition.py
    │   └── rules/
    │       ├── rfc_5322_ed2008.py
    │       └── rfc_6761_ed2012.py
    ├── Date/                      # grammar/ (1: date_recognition.py via CandidatesMatcher 4 candidates - iso8601, slash_iso, us, european, strategy all) + rules/ (3) — ISO 8601, US federal, EN 50160
    │   ├── capability.py          # DateCapability
    │   ├── contract.py            # DateContract
    │   ├── notation.py            # DateNotation dataclass
    │   ├── grammar/
    │   │   └── date_recognition.py  # CandidatesMatcher (4 candidates); legacy iso8601/us/european files remain on disk inert
    │   └── rules/
    │       ├── iso_8601_ed2019.py
    │       ├── us_federal_rules_ed2023.py
    │       └── en_50160_ed2010.py
    ├── Country/                   # grammar/ (4) + rules/ (3) + grammar/data/ + rules/data/
    │   ├── capability.py          # CountryCapability
    │   ├── contract.py            # CountryContract
    │   ├── notation.py            # CountryNotation (shape, value)
    │   ├── name_normalization.py  # LEGACY one-off — not a pattern to copy
    │   ├── grammar/               # alpha2, alpha3, numeric, name_recognition
    │   ├── grammar/data/          # english_names, localized_names, historical_names, chinese_names
    │   ├── rules/                 # iso_3166_ed2024, iso_3166_historical_ed2020, cldr_localized_ed2025
    │   └── rules/data/            # iso_3166_ed2024, iso_3166_ed2020_part3, cldr_ed2025
    ├── Currency/                  # grammar/ (3) + rules/ (2) + grammar/data/ + rules/data/ — ISO 4217, CLDR
    │   ├── capability.py          # CurrencyCapability
    │   ├── contract.py            # CurrencyContract (default_currency opt-in)
    │   ├── notation.py            # CurrencyNotation (text, shape)
    │   ├── grammar/               # code, symbol, word_recognition
    │   ├── grammar/data/          # currency_symbols, currency_words
    │   ├── rules/                 # iso_4217_ed2015, cldr_currencies_ed2025
    │   └── rules/data/            # iso4217_list_one, cldr_currencies
    ├── IBAN/                      # grammar/ (1) + rules/ (1) — ISO 13616-1:2020, MOD 97-10
    │   ├── capability.py          # IBANCapability
    │   ├── contract.py            # IBANContract
    │   ├── notation.py            # IBANNotation (country_code, check_digits, bban, compact)
    │   ├── grammar/               # iban_recognition
    │   └── rules/                 # iso_13616 (registry + MOD 97-10 check)
    ├── IP/                        # grammar/ (2) + rules/ (2) — RFC 791 (RFC 1123 §2.1), RFC 4291 §2.2, RFC 5952
    │   ├── capability.py          # IPCapability
    │   ├── contract.py            # IPContract
    │   ├── notation.py            # IPNotation (address)
    │   ├── grammar/               # ipv4_recognition (\\b), ipv6_recognition (full/compressed/mixed Las32)
    │   └── rules/                 # rfc_791_ed1981, rfc_5952_ed2010
    ├── ISBN/                      # grammar/ (2) + rules/ (3) + rules/data/ — ISO 2108, Users' Manual, Range Message
    │   ├── capability.py          # ISBNCapability
    │   ├── contract.py            # ISBNContract
    │   ├── notation.py            # ISBNNotation (shape, digits)
    │   ├── grammar/               # isbn10, isbn13_recognition
    │   ├── rules/                 # iso_2108_ed2017, isbn_users_manual_ed2012, isbn_range_message_ed2026
    │   └── rules/data/            # range_message (GENERATED via tools/regenerate_isbn_range_data.py)
    ├── ISSN/                      # grammar/ (1) + rules/ (1) — ISO 3297:2022
    │   ├── capability.py          # ISSNCapability
    │   ├── contract.py            # ISSNContract
    │   ├── notation.py            # ISSNNotation (digits)
    │   ├── grammar/               # issn_recognition
    │   └── rules/                 # iso_3297 (check digit + registrant validation)
    ├── MacAddress/                # grammar/ (1) + rules/ (1) — IEEE Std 802-2024, no checksum
    │   ├── capability.py          # MacAddressCapability
    │   ├── contract.py            # MacAddressContract
    │   ├── notation.py            # MacAddressNotation (compact, shape)
    │   ├── grammar/               # mac_address_recognition
    │   └── rules/                 # ieee_802_ed2024 (structure, I/G + U/L informative)
    ├── Money/                     # grammar/ (3) + rules/ (2) + grammar/data/ + rules/data/ — ISO 4217, CLDR
    │   ├── capability.py          # MoneyCapability
    │   ├── contract.py            # MoneyContract (precision, dollar_sign_currency)
    │   ├── notation.py            # MoneyNotation (currency_part, amount_part, ...)
    │   ├── parsing.py             # amount parsing helpers
    │   ├── grammar/               # code, symbol, word_recognition
    │   ├── grammar/data/          # currency_symbols, currency_words
    │   ├── rules/                 # iso_4217_ed2015, cldr_currencies_ed2025
    │   └── rules/data/            # iso4217_list_one, cldr_currencies
    ├── ORCID/                     # grammar/ (1) + rules/ (2) — ISO 27729:2024, MOD 11-2 check
    │   ├── capability.py          # ORCIDCapability
    │   ├── contract.py            # ORCIDContract (orcid/uri/compact output formats)
    │   ├── notation.py            # ORCIDNotation (compact, hyphenated, uri, check, is_uri)
    │   ├── grammar/               # orcid_recognition
    │   └── rules/                 # iso_27729_ed2024 (structure + Annex A MOD 11-2)
    ├── Phone/                     # grammar/ (4) + rules/ (3) + rules/data/ — E.164, RFC 3966, NANP
    │   ├── capability.py          # PhoneCapability
    │   ├── contract.py            # PhoneContract (default_country)
    │   ├── notation.py            # PhoneNotation
    │   ├── grammar/               # e164, tel_uri, international_00, national_recognition (+ common.py LEGACY)
    │   ├── rules/                 # e164_ed2010, rfc_3966_ed2004, nanp_ed2024
    │   └── rules/data/            # e164_country_codes, nanp_tables
    ├── SIUnit/                    # grammar/ (5) + rules/ (3) + grammar/data/ + rules/data/ — BIPM SI Brochure, ISO 80000-1
    │   ├── capability.py          # SIUnitCapability
    │   ├── contract.py            # SIUnitContract
    │   ├── notation.py            # SIUnitNotation (text, shape)
    │   ├── grammar/               # symbol, name, compound_recognition, split_word_recognition, split_symbol_recognition
    │   ├── grammar/data/          # unit_symbol_tokens, unit_name_tokens, compound_tokens (+ GENERATED via tools/regenerate_si_prefix_data.py)
    │   ├── rules/                 # bipm_si_brochure_ed2019, iso_80000_ed2022, split_prefixes
    │   └── rules/data/            # si_base_units, si_derived_units, si_nonsi_units, si_prefixes, unit_names (+ GENERATED prefixed_units, prefixed_unit_names)
    └── URL/                       # grammar/ (1) + rules/ (1) + rules/data/ — WHATWG URL Standard
        ├── capability.py          # URLCapability
        ├── contract.py            # URLContract
        ├── notation.py            # URLNotation
        ├── parsing.py             # WHATWG URL parsing helpers
        ├── grammar/               # absolute_uri_recognition
        ├── rules/                 # whatwg_url_standard
        └── rules/data/            # idna_uts46_mapping
```

### Package Responsibilities

| Package | Responsibility |
|---------|----------------|
| `paxman.core` | Domain objects, protocols, discovery (import-linter leaf — imports from nothing inside `paxman.*`) |
| `paxman.capabilities` | Capability implementations (import only from `paxman.core`) |
| `paxman.engine` | Pipeline orchestration |
| `paxman.api` | Public API entry points |

### Kernel notes (ADR-0009)
- Common-word suppression: `COMMON_WORDS` 67 via `BoundarySpec` WORD guard (`suppressible`, contract `suppress_common_words` default off). A0 whole-input exemption (#122): a suppressible hit covering the trimmed whole input is never suppressed; suppressed hits are observable via `ExecutionResult.suppressed_count` / `suppressed_spans`.
- Country `country_normalized` view — NFD-normalized view for lexicon scanning.
- `BoundarySpec` frozensets O(1) word/anchor checks.
- Normalizers two-array tuple `tuple[str, tuple[int,...]|None, tuple[int,...]|None]` (`starts`/`ends` parallel arrays).
- `PipelineGrammar` `matchers` delegation — `recognize()` delegates to `run_matchers()`.

---

## Testing Strategy

### Test Structure
```
tests/
├── conftest.py                    # loads hypothesis "ci" profile
├── unit/                          # -m unit        core domain, registry, contracts, purity scans
│   ├── test_provenance.py         # Provenance dataclass
│   ├── test_candidate.py          # Candidate dataclass
│   ├── test_recognized_rep.py     # RecognizedRep dataclass
│   ├── test_resolution.py         # Resolution enum
│   ├── test_contract.py           # Contract protocol/validation
│   ├── test_capability_contract.py# CapabilityContract (output_format policy, defaults)
│   ├── test_capability.py         # Capability ABC
│   ├── test_capability_surface.py # Surface homogeneity across capabilities
│   ├── test_capability_exports.py # __init__ export completeness (16 capabilities)
│   ├── test_version_stamp.py      # VersionStamp
│   ├── test_discovery.py          # Registry register/freeze/reset
│   ├── test_errors.py             # Exception hierarchy
│   ├── test_rule_metadata.py      # Rule modules importable + metadata
│   ├── test_rule_output_format_purity.py  # bans output_format in rules (CI scan)
│   ├── test_grammar_semantic_purity.py    # grammar↔rules import/meaning boundary
│   └── test_package_install.py    # packaging sanity
├── capabilities/                  # -m capability  per-capability, lowercase dirs
│   ├── country/                   # test_grammar, test_rules, test_capability, test_data_consistency
│   ├── currency/                  # + test_contract, test_notation, test_data
│   ├── date/                      # test_grammar, test_rules, test_capability
│   ├── email/                     # test_grammar, test_rules, test_capability
│   ├── iban/                      # test_grammar, test_rules, test_capability, test_contract, test_notation
│   ├── ip/                        # test_grammar, test_rules, test_capability
│   ├── isbn/                      # + test_contract, test_notation, test_data
│   ├── issn/                      # test_grammar, test_rules, test_capability, test_contract, test_notation
│   ├── mac_address/               # test_grammar, test_rules, test_capability, test_contract, test_notation
│   ├── money/                      # + test_contract, test_notation, test_data, test_parsing
│   ├── orcid/                      # test_grammar, test_rules, test_capability, test_notation
│   ├── phone/                      # + test_data
│   ├── si_unit/                   # test_grammar, test_rules, test_capability, test_contract, test_notation, test_data, test_data_consistency
│   └── url/                       # + test_contract, test_notation, test_data, test_parsing, test_rule
├── integration/                   # -m integration pipeline, ambiguity, temporal,
│   │                              # feature gating, format_value seam, extensions, benchmark harness,
│   │                              # per-capability pipelines
│   ├── test_pipeline.py           # Full pipeline flow
│   ├── test_ambiguity.py          # Ambiguity detection
│   ├── test_temporal.py           # Year-based filtering
│   ├── test_feature_gating.py     # include_* / requires_features loci
│   ├── test_format_value_seam.py  # output_format presentation seam
│   ├── test_recognition_seam.py   # span-bearing RecognitionMatch contract
│   ├── test_grammar_extensions.py # community extra_grammars opt-in flow
│   ├── test_span_exposure.py      # result/candidate span traceability
│   ├── test_single_value_invariant.py  # SUCCESS single-value invariant
│   └── test_<cap>_pipeline.py     # country, currency, date, iban, issn, money, phone, si_unit, url pipelines
├── property/                      # -m property    hypothesis property tests
│   ├── test_domain_properties.py
│   ├── test_grammar_properties.py
│   ├── test_rule_properties.py
│   ├── test_format_value_properties.py
│   ├── test_currency_properties.py
│   ├── test_iban_properties.py
│   ├── test_isbn_properties.py
│   ├── test_issn_properties.py
│   ├── test_money_properties.py   # full-pipeline exception (local _fresh_registry fixture)
│   ├── test_si_unit_properties.py
│   ├── test_url_properties.py
│   └── test_grammar_stage_parity.py  # grammar vs pipeline-stage parity (benchmark-adjacent)
└── e2e/                           # -m e2e         canonicalize() end-to-end
    ├── test_canonicalize.py       # End-to-end user scenarios
    └── test_bootstrap.py          # register_all_shipped / list_shipped_capabilities end-to-end
```

### Test Markers
```python
import pytest


@pytest.mark.unit
def test_provenance_immutable(): ...


@pytest.mark.capability
def test_email_grammar_recognizes_standard(): ...


@pytest.mark.integration
def test_ambiguity_detection(): ...


@pytest.mark.e2e
def test_canonicalize_email_success(): ...
```

Per-capability markers are registered for `country`, `currency`, `isbn`, `issn`, `money`, `si_unit`, and `url` — run one capability's suite directly with `uv run pytest tests/capabilities/<cap>` (or `-m <cap>`). Capability dirs are lowercase (`isbn`, not `ISBN`).

---

## Architectural Enforcement

### Toolchain
| Tool | Purpose | Configuration |
|------|---------|---------------|
| **uv** | Dependency management + command runner | `pyproject.toml` (every command via `uv run`) |
| **ruff** | Linting + formatting | `pyproject.toml` (`[tool.ruff]`) |
| **pyright** | Static type checking (strict) | `pyproject.toml` (`[tool.pyright]` — no `pyrightconfig.json`) |
| **import-linter** | Enforce import boundaries | `pyproject.toml` |
| **pytest** | Testing | `pyproject.toml` |
| **hypothesis** | Property-based testing | `tests/conftest.py` |

### Import Rules (import-linter)
```toml
# pyproject.toml
[tool.importlinter]
root_package = "paxman"

[[tool.importlinter.contracts]]
name = "Capability independence"
type = "layers"
layers = [
    "paxman.api",            # Public API (canonicalize)
    "paxman.engine",         # Pipeline orchestrator
    "paxman.capabilities",   # Capability implementations
    "paxman.core",           # Domain objects (Provenance, Candidate, etc.)
]
```

### Pytest Configuration
```toml
# pyproject.toml
[tool.pytest.ini_options]
markers = [
    "unit: unit tests",
    "capability: capability-specific tests",
    "integration: integration tests",
    "e2e: end-to-end tests",
    "property: property-based tests (Hypothesis)",
    "benchmark: benchmark harness tests",
    "country: country capability tests",
    "currency: currency capability tests",
    "isbn: isbn capability tests",
    "issn: issn capability tests",
    "money: money capability tests",
    "si_unit: si unit capability tests",
    "url: url capability tests",
]
testpaths = ["tests"]
```

### Pyright Configuration
Pyright is configured inline in `pyproject.toml` (there is **no** `pyrightconfig.json` in this repo):

```toml
[tool.pyright]
pythonVersion = "3.11"
typeCheckingMode = "strict"
reportMissingImports = true
reportMissingTypeStubs = false
include = ["paxman"]
exclude = ["tests", "docs"]
```

### Hypothesis Configuration
```python
# tests/conftest.py
from hypothesis import settings, HealthCheck

# Configure hypothesis for faster tests
settings.register_profile(
    "ci",
    max_examples=100,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
settings.load_profile("ci")
```

### Import Boundaries
| Rule | Description |
|------|-------------|
| `paxman.core` cannot import from `paxman.capabilities` | Core domain is independent |
| `paxman.capabilities` can import from `paxman.core` | Capabilities use domain objects |
| `paxman.engine` can import from `paxman.core` and `paxman.capabilities` | Engine orchestrates |
| `paxman.api` can import from everything | Public API is the entry point |

### Ruff Configuration
```toml
# pyproject.toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "B",    # flake8-bugbear
    "SIM",  # flake8-simplify
]
```
