# Paxman

Paxman is a canonicalization authority resolver. It takes ambiguous human input and returns what authoritative specifications say that input means, with full provenance.

For a deeper understanding of the system, see [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Installation

```bash
pip install paxman
```

---

## Quick Start

```python
import paxman
from paxman.capabilities import Email
from paxman.core.domain import Resolution

paxman.register_all_shipped()  # once, before first use

# Create a contract and canonicalize
contract = Email.create_contract()
result = paxman.canonicalize("Contact user@Example.com", contract)

# Check the result
if result.status == Resolution.SUCCESS:
    print(result.canonicalized_value)  # "user@example.com"
```

To register only what you need, call `paxman.register_capability(Email())` per capability.

**Registration and threading:** Registration — single (`register_capability`) or bootstrap (`paxman.register_all_shipped()`) — must complete from a single thread before the first `canonicalize()` call; the registry then freezes and reads are safe from any thread; registering later raises `CapabilityError`.

---

## What Happens

When you call `paxman.canonicalize()`, the system:

1. **Recognizes** — grammars scan your input text and find patterns that match known formats
2. **Validates** — rules check those patterns against authoritative specifications (like RFCs)
3. **Resolves** — if exactly one canonical value emerges, it is returned with full provenance

If multiple specifications disagree on the canonical value, the status is `AMBIGUOUS`. If nothing is recognized, the status is `MISSING`. If something is recognized but no specification validates it, the status is `INVALID`.

> **MISSING vs INVALID:** `MISSING` means no grammar found the pattern; `INVALID` means a grammar found it but no rule accepted it.

---

## Capabilities

Paxman ships with fifteen built-in capabilities:

| Capability | Domain | Grammars | Rules | Description |
|---|---|---|---|---|
| **BIC** | Business identifier codes | 1 (bic) | 1 | ISO 9362:2022, ISO 3166-1 (country codes plus XK) |
| **Country** | Country codes/names | 4 (alpha2, alpha3, numeric, name) | 6 | ISO 3166, CLDR |
| **Currency** | Currency identifiers | 3 (code, symbol, word) | 3 | ISO 4217, CLDR |
| **Date** | Dates | 1 (date) | 3 | ISO 8601-1:2019 §5.2.1.1, derived conventions (US/European locale) |
| **Email** | Email addresses | 3 (standard, obfuscated, localhost) | 2 | RFC 5322, RFC 6761 |
| **IBAN** | Bank account numbers | 1 (iban) | 1 | ISO 13616, SWIFT Registry, MOD 97-10 |
| **IP** | IP addresses | 2 (ipv4, ipv6) | 2 | RFC 791, RFC 5952 |
| **ISBN** | ISBNs | 2 (isbn13, isbn10) | 4 | ISO 2108, ISBN Users' Manual, ISBN Range Message |
| **ISSN** | Serial identifiers | 1 (issn) | 1 | ISO 3297:2022 |
| **Language** | Language identifiers | 3 (bcp47_tag, language_code, language_name) | 10 | ISO 639, IANA Language Subtag Registry, BCP 47 RFC 5646, CLDR |
| **Money** | Money amounts | 3 (code, symbol, word) | 3 | ISO 4217, CLDR |
| **ORCID** | Researcher identifiers | 1 (orcid) | 2 | ISO 27729:2024, MOD 11-2 |
| **Phone** | Phone numbers | 4 (e164, tel_uri, international_00, national) | 5 | ITU-T E.164, RFC 3966, NANP |
| **SI Unit** | SI unit expressions | 3 (symbol, name, compound) | 7 | BIPM SI Brochure, ISO 80000-1 |
| **URL** | URLs | 1 (absolute_uri) | 1 | WHATWG URL Standard |

> **Note:** Table generated from `paxman/api/bootstrap.py:_SHIPPED` (alphabetical by registry name). To regenerate, run `uv run python tools/generate_readme_table.py`.

### Email Capability

Recognizes standard, obfuscated (`user at domain dot com`), and localhost email addresses.

```python
from paxman.capabilities import Email

register_capability(Email())

# Standard email
contract = Email.create_contract()
result = paxman.canonicalize("user@Example.COM", contract)
# → "user@example.com"

# Enable obfuscated recognition
contract = Email.create_contract(include_obfuscated=True)
result = paxman.canonicalize("Contact user at example dot com", contract)
# → "user@example.com"

# Exclude localhost validation
contract = Email.create_contract(excluded_rules=["Section 6.3-localhost"])
result = paxman.canonicalize("admin@localhost", contract)
```

### Date Capability

Recognizes dates in ISO 8601 (`YYYY-MM-DD`), slash-ISO (`YYYY/MM/DD`), US (`MM/DD/YYYY`), and European (`DD/MM/YYYY`) formats.

```python
from paxman.capabilities import Date

register_capability(Date())

# ISO format (unambiguous)
contract = Date.create_contract()
result = paxman.canonicalize("2026-01-15", contract)
# → "2026-01-15"

# Slash-ISO format (4-digit year first)
contract = Date.create_contract()
result = paxman.canonicalize("2026/01/15", contract)
# → "2026-01-15"

# US/European format (potentially ambiguous)
contract = Date.create_contract()
result = paxman.canonicalize("01/02/2026", contract)
# → Status: AMBIGUOUS (US: 2026-01-02, European: 2026-02-01)

# Pin to specific rules
contract = Date.create_contract(pinned_rules=["Section 4.3.1-calendar-date"])
result = paxman.canonicalize("2026-01-15", contract)
```

### Country Capability

Recognizes country representations as alpha-2, alpha-3, numeric codes, or country names.

```python
from paxman.capabilities import Country

register_capability(Country())

# Alpha-2 code
contract = Country.create_contract()
result = paxman.canonicalize("US", contract)
# → "US"

# Country name
contract = Country.create_contract()
result = paxman.canonicalize("United States", contract)
# → "US"

# Enable localized names (CLDR multilingual)
contract = Country.create_contract(include_localized=True)
result = paxman.canonicalize("Alemania", contract)
# → "DE"

# Enable historical/deprecated names (ISO 3166-3)
contract = Country.create_contract(include_historical=True)
result = paxman.canonicalize("Burma", contract)
# → "BU"
```

Localized names are validated by the CLDR rule, so an enabled resolution like `Alemania` → `DE` carries Unicode/CLDR provenance. Recognizing a localized token is not ISO validation: without `include_localized`, recognized localized input (e.g., `Alemania`) is `INVALID` — recognized, but no authority rule runs — rather than being resolved via ISO. Historical names resolve through ISO 3166-3 and return the historical entity's own former code (`Burma` → `BU`), not a successor state's code.

### Currency Capability

Recognizes ISO 4217 alpha-3 codes, CLDR currency symbols, and CLDR currency display-name words as standalone identifiers, canonicalizing to the uppercase alpha-3 code. Identifier-only: amounts are the Money capability's domain (`USD 500` resolves via its `USD` span; amount-glued tokens like `US$5` are not recognized at all).

> **Note:** Bare symbols like `$` are `INVALID` by default. `$` is shared by 29 currencies whose CLDR symbol is `$` — without disambiguation Paxman cannot pick one. Opt in with `default_currency` to resolve the bare symbol only when it is one of that symbol's own candidates.

```python
from paxman.capabilities import Currency

register_capability(Currency())

# Lowercase code folds to uppercase alpha-3
contract = Currency.create_contract()
result = paxman.canonicalize("usd", contract)
# → "USD"

# Lowercase CLDR display-name word resolves to its code
contract = Currency.create_contract()
result = paxman.canonicalize("euro", contract)
# → "EUR"

# Shared bare symbol is unresolved by default: INVALID (recognized, no authority)
contract = Currency.create_contract()
result = paxman.canonicalize("$", contract)
# → Status: INVALID

# Opt in: default_currency resolves the shared bare symbol only when the
# code is one of that symbol's own candidates ("$" -> the 29 codes whose
# CLDR symbol is "$")
contract = Currency.create_contract(default_currency="USD")
result = paxman.canonicalize("$", contract)
# → "USD"

# A valid code that is NOT a candidate of "$" (MYR's symbol is RM) is INVALID
contract = Currency.create_contract(default_currency="MYR")
result = paxman.canonicalize("$", contract)
# → Status: INVALID
```

### IBAN Capability

Recognizes International Bank Account Numbers with check-digit and country validation, canonicalizing to electronic compact form.

```python
from paxman.capabilities import IBAN

register_capability(IBAN())

# Bare IBAN (compact)
contract = IBAN.create_contract()
result = paxman.canonicalize("GB82WEST12345698765432", contract)
# → "GB82WEST12345698765432"

# Paper IBAN with spaces
contract = IBAN.create_contract()
result = paxman.canonicalize("GB82 WEST 1234 5698 7654 32", contract)
# → "GB82WEST12345698765432"

# Paper presentation (spaced groups of four)
contract = IBAN.create_contract(output_format="paper")
result = paxman.canonicalize("GB82WEST12345698765432", contract)
# → "GB82 WEST 1234 5698 7654 32"

# Invalid country or bad MOD 97 check
contract = IBAN.create_contract()
result = paxman.canonicalize("ZZ82WEST12345698765432", contract)
# → Status: INVALID
```

### IP Capability

Recognizes IPv4 and IPv6 addresses with canonical normalization.

```python
from paxman.capabilities import IP

register_capability(IP())

# IPv4
contract = IP.create_contract()
result = paxman.canonicalize("192.168.1.1", contract)
# → "192.168.1.1"

# IPv6 (canonical form per RFC 5952)
contract = IP.create_contract()
result = paxman.canonicalize("2001:0db8:0000:0000:0000:0000:0000:0001", contract)
# → "2001:db8::1"

# Disable IPv6 recognition
contract = IP.create_contract(include_ipv6=False)
result = paxman.canonicalize("2001:db8::1", contract)
# → Status: MISSING
```

### ISBN Capability

Recognizes ISBN-10 and ISBN-13 identifiers with check-digit validation, canonicalizing legacy ISBN-10 input to ISBN-13.

```python
from paxman.capabilities import ISBN

register_capability(ISBN())

# Bare ISBN-13
contract = ISBN.create_contract()
result = paxman.canonicalize("9780306406157", contract)
# → "9780306406157"

# Legacy ISBN-10 converts to ISBN-13
contract = ISBN.create_contract()
result = paxman.canonicalize("0306406152", contract)
# → "9780306406157"

# Range Message hyphenation (presentation only)
contract = ISBN.create_contract(output_format="hyphenated")
result = paxman.canonicalize("9780110002224", contract)
# → "978-0-11-000222-4"

# Enable registrant-range provenance (ISBN Range Message authority)
contract = ISBN.create_contract(include_range_validation=True)
result = paxman.canonicalize("9780110002224", contract)
# → Status: SUCCESS (Section 4-registrant-range provenance)

# Disable ISBN-10 recognition
contract = ISBN.create_contract(include_isbn10=False)
result = paxman.canonicalize("0306406152", contract)
# → Status: MISSING
```

### Money Capability

Recognizes ISO 4217 codes, CLDR currency symbols, and CLDR currency names adjacent to amounts, canonicalizing to `CODE + amount` padded to ISO 4217 minor units.

> **Note:** Bare symbols like `$500` are `INVALID` by default. The dollar sign is shared by many currencies — without disambiguation Paxman cannot pick one. Opt in with `dollar_sign_currency`.

```python
from paxman.capabilities import Money

register_capability(Money())

# Code + amount
contract = Money.create_contract()
result = paxman.canonicalize("USD500", contract)
# → "USD 500.00"

# Bare $ is unresolved by default: INVALID (recognized, no authority)
contract = Money.create_contract()
result = paxman.canonicalize("$500", contract)
# → Status: INVALID

# Opt in: bare $ resolves via dollar_sign_currency
contract = Money.create_contract(dollar_sign_currency="MYR")
result = paxman.canonicalize("$500", contract)
# → "MYR 500.00"

# European comma-decimal: last separator is the decimal point
contract = Money.create_contract()
result = paxman.canonicalize("1.000,50 EUR", contract)
# → "EUR 1000.50"

# Compact rendering removes the code/amount separator space
contract = Money.create_contract(output_format="compact")
result = paxman.canonicalize("USD500", contract)
# → "USD500.00"
```

### ORCID Capability

Recognizes ORCID iDs (ISNI-compatible identifiers, ISO 27729:2024) with MOD 11-2 check-digit validation, canonicalizing to the hyphenated form.

```python
import paxman
from paxman.capabilities import ORCID

paxman.register_capability(ORCID())

# Bare hyphenated iD
contract = ORCID.create_contract()
result = paxman.canonicalize("0000-0002-1825-0097", contract)
# → "0000-0002-1825-0097"

# URI input resolves to the same canonical value
result = paxman.canonicalize("https://orcid.org/0000-0002-1694-233X", contract)
# → "0000-0002-1694-233X"

# Render as the storage URI
contract = ORCID.create_contract(output_format="uri")
result = paxman.canonicalize("0000-0002-1825-0097", contract)
# → "https://orcid.org/0000-0002-1825-0097"

# Bad check digit is INVALID
result = paxman.canonicalize("0000-0002-1825-0098", ORCID.create_contract())
# → Status: INVALID
```

### Phone Capability

Recognizes international (E.164, 00-prefix), tel-URI, and NANP national phone numbers.

```python
from paxman.capabilities import Phone

register_capability(Phone())

# International number
contract = Phone.create_contract()
result = paxman.canonicalize("+1 555 123 4567", contract)
# → "+15551234567"

# National number (requires default_country)
contract = Phone.create_contract(default_country="US")
result = paxman.canonicalize("(555) 234-5678", contract)
# → "+15552345678"

# Output as RFC 3966 tel-URI
contract = Phone.create_contract(output_format="rfc3966")
result = paxman.canonicalize("+15551234567", contract)
# → "tel:+15551234567"
```

### URL Capability

Recognizes absolute URIs and IRIs, canonicalizing them per the WHATWG URL Standard (lowercased scheme/host, default-port removal, dot-segment resolution, UTS #46 IDNA for internationalized hosts, byte-preserving percent-encoding).

```python
from paxman.capabilities import URL

register_capability(URL())

# Absolute URI canonicalization (milestone)
contract = URL.create_contract()
result = paxman.canonicalize("HTTPS://Example.COM:443/path/../other", contract)
# → "https://example.com/other"

# Opaque (non-special) scheme — verbatim
contract = URL.create_contract()
result = paxman.canonicalize("mailto:user@example.com", contract)
# → "mailto:user@example.com"

# IDN host canonicalizes via UTS #46 (IDNA)
contract = URL.create_contract()
result = paxman.canonicalize("http://münchen.de", contract)
# → "http://xn--mnchen-3ya.de/"
```

### SI Unit Capability

Recognizes SI unit expressions: symbols, names, and product/quotient compounds, canonicalizing to the canonical symbol form with BIPM SI Brochure (9th ed.) and ISO 80000-1 provenance. Identity-only: no quantities, no magnitudes, no name-compounds ("metre per second" does not resolve as a compound — its words are recognized separately, yielding AMBIGUOUS; "25°C" is MISSING).

```python
from paxman.capabilities import SIUnit

register_capability(SIUnit())

# Unit name resolves to its canonical symbol
contract = SIUnit.create_contract()
result = paxman.canonicalize("Kilogram", contract)
# → "kg"

# Prefixed name resolves to the prefixed symbol
contract = SIUnit.create_contract()
result = paxman.canonicalize("megahertz", contract)
# → "MHz"

# Compound expression canonicalizes to the symbol form
contract = SIUnit.create_contract()
result = paxman.canonicalize("m/s²", contract)
# → "m/s2"

# Spoken word-prefix form, merged only when opted in
contract = SIUnit.create_contract(allow_split_word_prefixes=True)
result = paxman.canonicalize("kilo gram", contract)
# → "kg"

# Symbol-prefix spacing is always rejected (no flag)
contract = SIUnit.create_contract()
result = paxman.canonicalize("k g", contract)
# → Status: INVALID

# Multi-solidus preserved only when opted in
contract = SIUnit.create_contract(allow_multi_solidus=True)
result = paxman.canonicalize("kg/m/s", contract)
# → "kg/m/s"
```

---

## Contract Configuration

Every capability provides a `create_contract()` factory method with common and capability-specific parameters.

### Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `excluded_rules` | `Sequence[str]` | Rule names to exclude from validation |
| `pinned_rules` | `Sequence[str]` | Pin to specific rules (overrides `excluded_rules`) |
| `year` | `int` | Temporal filter — only rules with `publication_year ≤ year` run |

### Capability-Specific Parameters

| Capability | Parameter | Type | Description |
|------------|-----------|------|-------------|
| Email | `include_obfuscated` | `bool` | Enable "user at domain dot com" recognition |
| Email | `include_localhost` | `bool` | Enable localhost email recognition (default: `True`) |
| Date | `output_format` | `str` | Output format (e.g., `"ISO"`, `"US"`) |
| Date | `two_digit_base_year` | `int` | Base year for 2-digit years (e.g., `2000` → `"26"` = `2026`) |
| Country | `include_localized` | `bool` | Enable CLDR multilingual name recognition |
| Country | `include_historical` | `bool` | Enable deprecated/historical country name recognition |
| Country | `output_format` | `str` | Output format (`"alpha2"` default, `"alpha3"`, `"numeric"`, `"name"`) |
| Currency | `default_currency` | `str` \| `None` | ISO 4217 alpha-3 code resolving a shared bare symbol (e.g. `"$"`), valid only when it is one of that symbol's own candidate codes; `None` (default) or a non-candidate code makes them INVALID |
| IP | `include_ipv6` | `bool` | Enable IPv6 recognition (default: `True`) |
| ISBN | `include_isbn10` | `bool` | Enable ISBN-10 recognition (default: `True`) |
| ISBN | `include_range_validation` | `bool` | Enable ISBN Range Message registrant-range provenance |
| ISBN | `output_format` | `str` | Output format (`"isbn13"` default, `"hyphenated"`) |
| Money | `precision` | `str` | Over-precision amount handling: `"strict"` (reject), `"truncate"`, `"round"` (default: `"strict"`) |
| Money | `dollar_sign_currency` | `str` \| `None` | ISO 4217 alpha-3 code resolving bare/shared symbols (opt-in); `None` (default) makes bare symbols INVALID |
| Money | `output_format` | `str` | Output format (`"code_amount"` default, `"compact"`) |
| Phone | `default_country` | `str` | ISO 3166-1 alpha-2 country code to resolve national numbers (e.g., `"US"`) |
| Phone | `output_format` | `str` | Output format (`"e164"` default, `"rfc3966"`, `"national"`) |
| SIUnit | `allow_split_word_prefixes` | `bool` | Merge a word prefix split from its unit by whitespace (e.g. `"kilo gram"` → `"kg"`) when True; default False rejects the spoken form (→ INVALID) |
| SIUnit | `allow_multi_solidus` | `bool` | Preserve the legacy accept-multi-solidus behavior (e.g. `"kg/m/s"`) when True; default False rejects more than one top-level solidus (→ INVALID) per ISO 80000-1 §6.6.2 |

### Rule Pinning and Exclusion

```python
from paxman.capabilities import Email

# Pin to specific rules — only these run
contract = Email.create_contract(pinned_rules=["Section 3.4.1-addr-spec"])
result = paxman.canonicalize("user@example.com", contract)

# Pin + year filter — both apply
contract = Email.create_contract(
    pinned_rules=["Section 3.4.1-addr-spec", "Section 6.3-localhost"], year=2010
)

# Exclude specific rules
contract = Email.create_contract(excluded_rules=["Section 6.3-localhost"])
result = paxman.canonicalize("admin@localhost", contract)
```

### Temporal Filtering

```python
from paxman.capabilities import Date

# Only rules published on or before 2019
contract = Date.create_contract(year=2019)
result = paxman.canonicalize("2026-01-15", contract)
```

---

## Community Extensions

Paxman ships with fourteen built-in capabilities, but a capability is closed for modification yet open for extension: you can add recognition and validation without touching the library. Register a `Grammar` subclass and the `Rule` subclass that validates it, then opt a contract into them by naming the grammar in `extra_grammars`:

```python
import re
from datetime import datetime

import paxman
from paxman.capabilities import Date
from paxman.capabilities.Date.notation import DateNotation
from paxman.core.contract import Contract
from paxman.core.discovery import register_capability
from paxman.core.domain import (
    Grammar,
    Provenance,
    RecognitionMatch,
    Rule,
    RuleStrategy,
)

register_capability(Date())


class DotDateGrammar(Grammar[DateNotation]):
    """Recognize YYYY.MM.DD dates with dot separators."""

    name = "dot_date_recognition"
    semantics = "dot_date_recognition"
    _PATTERN = re.compile(r"\b(\d{4})\.(\d{2})\.(\d{2})\b")

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        """Return span-bearing matches for dot-separated dates."""
        return [
            RecognitionMatch(
                notation=DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3)),
                start=m.start(),
                end=m.end(),
                raw_text=m.group(0),
            )
            for m in self._PATTERN.finditer(text)
        ]


class DotDateRule(Rule[DateNotation]):
    """Validate dot-separated dates, normalizing to ISO YYYY-MM-DD."""

    name = "dot_date_rule"
    strategy = RuleStrategy.PARSER
    provenance = Provenance(
        authority="ISO",
        specification_name="ISO 8601",
        kind="specification",
        reference_url="https://www.iso.org/standard/70907.html",
        version="2019",
        lifecycle="active",
        publication_year=2019,
    )
    citation = "Section 4.3.1 (calendar date)"
    target_semantics = frozenset({"dot_date_recognition"})
    requires_features = frozenset()

    def matches(self, notation: DateNotation, contract: Contract) -> bool:
        """Accept valid calendar dates."""
        try:
            datetime(int(notation.N1), int(notation.N2), int(notation.N3))
            return True
        except ValueError:
            return False

    def normalize(self, notation: DateNotation, contract: Contract) -> str:
        """Normalize YYYY.MM.DD to ISO YYYY-MM-DD."""
        return f"{int(notation.N1):04d}-{int(notation.N2):02d}-{int(notation.N3):02d}"


paxman.register_grammar("date", DotDateGrammar)
paxman.register_rule("date", DotDateRule)

contract = Date.create_contract(extra_grammars=("dot_date_recognition",))
result = paxman.canonicalize("2024.01.01", contract)
print(result.canonicalized_value)  # → "2024-01-01"
```

Rules of the seam:

- **Register before the first `canonicalize()` call** — the extension registries freeze with the capability registry.
- **Opt-in only** — a registered grammar runs only when named in `extra_grammars` (available on every `create_contract` factory), and a registered rule runs only when the contract's `extra_grammars` resolve to one of its `target_semantics` ids; un-named grammars and un-opted rules never affect results.
- **Unknown `extra_grammars` names are silently skipped** for grammar activation, so a contract naming an uninstalled grammar still runs identically (deterministically); the unknown name is kept as-is as the semantics key for rule activation. A name that is not a grammar name but matches a known semantics id therefore activates that semantics's rules without opting in a grammar — those rules fire only on recognitions carrying that semantics (fail-fast `ContractError` applies only to ids no grammar claims).
- **Names must be unique in the composed set** — a community grammar colliding with a shipped name fails fast with `CapabilityError`.
- **Community rules declare `target_semantics`** and activate only when the contract's `extra_grammars` resolve to one of those ids; a rule opted in via an id that no grammar claims fails fast with `ContractError`, while a rule that is not opted in stays inert regardless of any dangling targets.

---

## Resolution Status

| Status | Meaning |
|--------|---------|
| `MISSING` | No patterns recognized in the input |
| `INVALID` | Recognized, but no specification validates it |
| `SUCCESS` | Single canonical value resolved |
| `AMBIGUOUS` | Multiple specifications disagree on the canonical value |

> **MISSING vs INVALID:** If the grammar cannot find the pattern, the result is `MISSING`. If a grammar finds it but no rule accepts it, the result is `INVALID`. Example: `bad@.com` is `MISSING` (no grammar matches), while `999.999.999.999` as IP is `INVALID` (IPv4 grammar matched, RFC 791 rejected).

---

## Real-World Example

Paxman extracts and canonicalizes entities embedded in messy human text, preserving provenance and span for each mention:

```python
import paxman
from paxman.capabilities import Country, Email, Money, URL
from paxman.core.domain import Resolution

paxman.register_all_shipped()

text = "Invoice of 1.000,50 EUR due 01/02/2026 — contact billing@example.com. See https://Example.COM:443/path/../other"

for Cap in (Money, Email, URL, Country):
    contract = Cap.create_contract()
    result = paxman.canonicalize(text, contract)
    if result.status == Resolution.SUCCESS:
        print(f"{Cap.name}: {result.canonicalized_value!r} at {result.span}")
        for prov in result.candidates[0].provenance:
            print(
                f"  via {prov.authority}: {prov.specification_name} ({prov.citation})"
            )
# Money: 'EUR 1000.50' at (11, 23) via ISO: ISO 4217
# Email: 'billing@example.com' at (49, 68) via IETF: RFC 5322
# URL:   'https://example.com/other' at (74, 111) via WHATWG: URL Standard
```

For inputs with multiple mentions of the same capability, split the text first — see [docs/recipes/segmentation.md](docs/recipes/segmentation.md). The CLI offers the same extraction without code: `python -m paxman email "Contact billing@example.com"`.

For scan on prose, short-code noise (`to`→Tonga) can dominate: use the off-by-default
`suppress_common_words` gate (ADR-0009 §16) — `Country.create_contract(suppress_common_words=True)` /
`paxman scan --suppress-common-words "Ship to the United States of America, total 45.50 USD, weight 3.5 kg"` keeps the name mention while `USD` remains for currency and bare `canonicalize("to")` stays `SUCCESS "TO"` when the flag is off. See [docs/user/migration.md](docs/user/migration.md) for the full 0.2.0 suppression note.

---

## Provenance

Every resolved value carries provenance — the authoritative specification that validates it:

```python
from paxman.capabilities import Email

contract = Email.create_contract()
result = paxman.canonicalize("user@example.com", contract)

for candidate in result.candidates:
    for prov in candidate.provenance:
        print(f"{prov.authority}: {prov.specification_name}")
        # "IETF: RFC 5322"
```

---

## Recognition Span

Every `Candidate` and the top-level `ExecutionResult` expose the half-open
`[start, end)` character range the recognition occupied in the input, so callers
can locate exactly where a canonicalized entity sat:

```python
from paxman.capabilities import Email

contract = Email.create_contract()
result = paxman.canonicalize("user@example.com", contract)

print(result.span)  # (0, 16)
for candidate in result.candidates:
    print(candidate.span)  # (0, 16)
    print(candidate.recognition_rule)  # "standard_recognition"
```

`result.span` is the source span of the single resolved value on `SUCCESS`; it
is `None` for `MISSING`, `INVALID`, or `AMBIGUOUS`, since those cases have no
single resolved entity. For `AMBIGUOUS` results, locate each mention via the
per-candidate `Candidate.span`.

## Error Handling

Paxman raises typed exceptions for different failure modes:

```python
from paxman.core.errors import (
    CapabilityError,  # Unknown capability or registry frozen
    ContractError,  # Malformed contract configuration
    RecognitionError,  # Grammar failed during recognition
    ValidationError,  # Rule failed during validation
)

try:
    result = paxman.canonicalize("input", contract)
except CapabilityError as e:
    print(f"Capability error: {e}")
except ContractError as e:
    print(f"Contract error: {e}")
except RecognitionError as e:
    print(f"Recognition failed in {e.rule}: {e}")
except ValidationError as e:
    print(f"Validation failed in {e.rule}: {e}")
```

### Working with Multi-Entity Input

Paxman resolves one mention per `canonicalize()` call; `MultipleMentionsError` occurs only when distinct recognized mentions in one slice resolve to different canonical values — identical canonical values still coalesce to `SUCCESS`. For the caller-owned split-then-canonicalize pattern, see [docs/recipes/segmentation.md](docs/recipes/segmentation.md).

---

## Learn More

- [ARCHITECTURE.md](ARCHITECTURE.md) — architectural principles and design decisions
- [HOW_TO_ADD_NEW_CAPABILITY.md](HOW_TO_ADD_NEW_CAPABILITY.md) — guide to adding new domain capabilities. To add a new capability, start from the `tools/new_capability.py` scaffolder (see HOW_TO_ADD_NEW_CAPABILITY.md, Step 0) which generates the full skeleton.
- [CONTRIBUTING.md](CONTRIBUTING.md) — development setup and contribution guidelines
