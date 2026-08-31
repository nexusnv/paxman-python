---
title: Citations
slug: v0.3.0/citations
---

Every validated value in Paxman carries **provenance** — the authority, specification, version, and section that vouches for it. This page is the curated, authority-grouped index of **all cited provenance** across the 15 shipped capabilities. Use it to audit results, write methods sections, or compare Paxman against another system.

> **How to read provenance in code:** `result.candidates[n].provenance[0]` is a `Provenance` (`authority`, `specification_name`, `version`, `publication_year`, `reference_url`, `kind`, `lifecycle`) and `candidate.validation_rule` is the section citation (e.g. `Section 3.4.1-addr-spec`). See [Provenance](concepts/provenance/) for the object shape.

```python
for c in result.candidates:
    p = c.provenance[0]
    print(f"{c.validation_rule} — {p.authority} {p.specification_name} ({p.version}), {p.reference_url}")
```

All entries below are derived from the `PUBLICATION` constants and `citation`/`name` fields on each shipped rule (`paxman/capabilities/<Name>/rules/*.py`). No network lookup is involved — the data is baked into the installed library build and versioned via `version_stamp`.

***

## At a glance — citations by authority

| Authority | Specifications | Capabilities | Rules |
|-----------|---------------|--------------|-------|
| **BIPM** | SI Brochure: The International System of Units (SI), 9th ed. (2019) | SI Unit | 6 |
| **IETF** | RFC 5322, RFC 6761, RFC 791, RFC 5952, RFC 3966, BCP 47 RFC 5646 | Email, IP, Phone, Language | 6 |
| **IANA** | IANA Language Subtag Registry (Rolling File-Date 2026-08-08) | Language | 2 |
| **ISO** | ISO 9362:2022, ISO 27729:2024, ISO 3166-1:2020, ISO 3166-3, ISO 4217, ISO 8601:2019, ISO 2108:2017, ISO 13616-1:2020, ISO 639-1/2/3/5, ISO 80000-1:2022 | BIC, ORCID, Country, Currency, Money, Date, ISBN, IBAN, Language, SI Unit | 18 |
| **ISSN International Centre** | ISO 3297:2022 | ISSN | 1 |
| **ITU-T** | E.164 (2010) | Phone | 2 |
| **NANPA** | North American Numbering Plan (NANP) (2024) | Phone | 2 |
| **Unicode Consortium (CLDR)** | CLDR v45, Unicode CLDR v47, CLDR Language Display Names v46 | Country, Currency, Money, Language | 7 |
| **SIL International (ISO 639-3 RA)** | ISO 639-3:2007 | Language | 2 |
| **International ISBN Agency** | ISBN Users' Manual (2012), ISBN Range Message (2026-08-05) | ISBN | 2 |
| **WHATWG** | URL Standard (Living Standard) | URL | 1 |
| **Derived convention** | US locale — MM/DD/YYYY, European locale — DD/MM/YYYY | Date | 2 |

> **Note on "Derived convention":** The two Date rules for `MM/DD/YYYY` and `DD/MM/YYYY` are locale conventions rather than an external standards publication. They are included here for completeness and carry `kind="convention"` with no `reference_url`.

***

## BIPM — Bureau International des Poids et Mesures

Specification: **SI Brochure: The International System of Units (SI)**, 9th edition (2019) — `https://www.bipm.org/en/publications/si-brochure` — `kind="specification"`, `lifecycle="active"`, `publication_year=2019`.

| Capability | Rule (`validation_rule`) | Citation | Publication |
|------------|--------------------------|----------|-------------|
| SI Unit | `Section 2.3.1-base-units` | BIPM SI Brochure (9th ed., 2019), Table 1 | SI Brochure |
| SI Unit | `Section 2.3.2-derived-units` | BIPM SI Brochure (9th ed., 2019), Tables 3–4 | SI Brochure |
| SI Unit | `Section 4.1-non-si-units` | BIPM SI Brochure (9th ed., 2019), Tables 8–9 | SI Brochure |
| SI Unit | `Section 3.2-prefixes` | BIPM SI Brochure (9th ed., 2019), Table 5 and §3.2 | SI Brochure |
| SI Unit | `Section-names` | BIPM SI Brochure (9th ed., 2019), Tables 1, 3–4, 8–9 (unit names) | SI Brochure |
| SI Unit | `Section 3.2-split-word-prefixes` | BIPM SI Brochure (9th ed., 2019), §3.2 (prefixes attached to unit names) | SI Brochure |

***

## IETF — Internet Engineering Task Force

| Capability | Specification | Version | Rule | Citation | Year | Reference |
|------------|---------------|---------|------|----------|------|-----------|
| Email | RFC 5322 | 2008 | `Section 3.4.1-addr-spec` | Section 3.4.1 (addr-spec) | 2008 | https://tools.ietf.org/html/rfc5322 |
| Email | RFC 6761 | 2012 | `Section 6.3-localhost` | Section 6.3 (localhost) | 2012 | https://tools.ietf.org/html/rfc6761 |
| IP | RFC 791 | 1981 | `Section 3.2-ipv4-address` | Section 3.2 (internet addressing) | 1981 | https://tools.ietf.org/html/rfc791 |
| IP | RFC 5952 | 2010 | `Section 4-ipv6-text-representation` | Section 4 (IPv6 text representation) | 2010 | https://tools.ietf.org/html/rfc5952 |
| Phone | RFC 3966 | 2004 | `Section 3-tel-uri` | Section 3 (tel URI) / Section 3.1 (global numbers) | 2004 | https://tools.ietf.org/html/rfc3966 |
| Language | BCP 47 RFC 5646 | 2009-09 | `Section 2.1-syntax` | Section 2.1 (Language-Tag ABNF, well-formed only) | 2009 | https://www.rfc-editor.org/rfc/rfc5646.txt |

All IETF entries are `kind="specification"`, `lifecycle="active"`.

***

## IANA — Internet Assigned Numbers Authority

Specification: **IANA Language Subtag Registry**, Rolling File-Date 2026-08-08 — `https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry` — `kind="registry"`, `lifecycle="active"`, `publication_year=2026`.

| Capability | Rule | Citation |
|------------|------|----------|
| Language | `Section-iana-registry` | IANA Registry Type language/script/region/variant Deprecated Preferred Prefix Suppress-Script |
| Language | `Section-iana-registry-private` | IANA Registry private-use qaa-qtz/Qaaa-Qabx/QM-QZ/AA/XA-XZ/ZZ/x- |

***

## ISO — International Organization for Standardization

Across 10 ISO publications (18 rules):

| Capability | Specification | Version | Rule | Citation | Year | Reference |
|------------|---------------|---------|------|----------|------|-----------|
| BIC | ISO 9362:2022 | 2022 | `Section 5-bic-structure-country` | Section 5 (BIC structure) | 2022 | https://www.iso.org/standard/84108.html |
| ORCID | ISO 27729:2024 | 2024-11 | `Section 4-orcid-structure` | Section 4 (16 chars: 15 digits + MOD 11-2 check character) | 2024 | https://www.iso.org/standard/87177.html |
| ORCID | ISO 27729:2024 | 2024-11 | `Section A-mod11-2-check-character` | Annex A (MOD 11-2 over the first 15 decimal digits) | 2024 | https://www.iso.org/standard/87177.html |
| Country | ISO 3166-1:2020 | 2020 | `Section-alpha2-codes` | ISO 3166-1 alpha-2 codes | 2020 | https://www.iso.org/guest/en/ISO3166-1/RegistrationTable/Active%20country%20list.html |
| Country | ISO 3166-1:2020 | 2020 | `Section-alpha3-codes` | ISO 3166-1 alpha-3 codes | 2020 | https://www.iso.org/guest/en/ISO3166-1/RegistrationTable/Active%20country%20list.html |
| Country | ISO 3166-1:2020 | 2020 | `Section-numeric-codes` | ISO 3166-1 numeric (M49) codes | 2020 | https://www.iso.org/guest/en/ISO3166-1/RegistrationTable/Active%20country%20list.html |
| Country | ISO 3166-1:2020 | 2020 | `Section-names` | ISO 3166-1 official English short names | 2020 | https://www.iso.org/guest/en/ISO3166-1/RegistrationTable/Active%20country%20list.html |
| Country | ISO 3166-3 | 2020 | `Section-historical-names` | ISO 3166-3:2020 (formerly used names) | 2020 | https://www.iso.org/standard/72484.html |
| Currency | ISO 4217 | — | `Section-code` | ISO 4217:2015 alpha-3 currency codes, as amended by the ISO 4217 Maintenance Agency amendment series (SIX List One, 2026-01-01) | 2015 | https://www.iso.org/iso-4217-currency-codes.html |
| Money | ISO 4217 | — | `Section-codes` | ISO 4217 currency codes | 2015 | https://www.iso.org/iso-4217-currency-codes.html |
| Date | ISO 8601 | 2019 | `Section 5.2.1.1-calendar-date` | Section 5.2.1.1 (calendar date) | 2019 | https://www.iso.org/standard/70907.html |
| ISBN | ISO 2108:2017 | 2017 | `Section 5.3-isbn13-check-digit` | Section 5.3 (ISBN-13 check digit) | 2017 | https://www.iso.org/standard/65483.html |
| ISBN | ISO 2108:2017 | 2017 | `Section 4.2-gs1-prefix` | Section 4.2 (GS1 prefix) | 2017 | https://www.iso.org/standard/65483.html |
| IBAN | ISO 13616-1:2020 | 2020 | `Section 4-iban-structure-mod97` | Section 4-5 (structure + MOD 97-10, via ISO/IEC 7064:2003) | 2020 | https://www.iso.org/standard/81090.html |
| Language | ISO 639-1:2002 | 2002 | `Section 4-alpha-2-code` | Section 4 (alpha-2 code, 184 entries) | 2002 | https://www.iso.org/standard/22109.html |
| Language | ISO 639-1:2002 | 2002 | `Section-english-name-mapping` | Section 4 (English language names → alpha-2) | 2002 | https://www.iso.org/standard/22109.html |
| Language | ISO 639-2:1998 | 1998 | `Section 4-alpha-3-code` | Section 4 (alpha-3 code, 487 entries T/B) | 1998 | https://www.iso.org/standard/4767.html |
| Language | ISO 639-5:2008 | 2008 | `Section 4-collective-code` | Section 4 (collective code, 115 entries) | 2008 | https://www.iso.org/standard/39536.html |
| SI Unit | ISO 80000-1:2022 Quantities and units — Part 1: General | 2022 | `Section 6.5-compounds` | ISO 80000-1:2022, §6.5 (unit symbols in products and quotients) | 2022 | https://www.iso.org/standard/76921.html |

All ISO entries are `lifecycle="active"`. ISO 3166-1 entries are `kind="registry"`; ISO 3166-3, ISO 8601, ISO 2108, ISO 13616-1, ISO 639-\* and ISO 80000-1 are `kind="specification"`; ISO 4217 is `kind="specification"` with `version=None` (the code list is maintained by the ISO 4217 Maintenance Agency — see citation).

***

## ISSN International Centre

Specification: **ISO 3297:2022**, `https://www.iso.org/standard/84536.html`, `kind="specification"`, `version="2022"`, `lifecycle="active"`, `publication_year=2022`.

| Capability | Rule | Citation |
|------------|------|----------|
| ISSN | `Section 4-issn-check-digit` | Section 4 (check digit) |

***

## ITU-T — International Telecommunication Union

Specification: **E.164**, `https://www.itu.int/rec/T-REC-E.164`, `kind="specification"`, `version="2010"`, `lifecycle="active"`, `publication_year=2010`.

| Capability | Rule | Citation |
|------------|------|----------|
| Phone | `Section 6.1-international-number` | Section 6.1 (number structure) |
| Phone | `Section 6.2-country-code` | Annex A (table of assigned country codes) |

***

## NANPA — North American Numbering Plan Administrator

Specification: **North American Numbering Plan (NANP)**, `https://www.nanpa.com/`, `kind="registry"`, `version="2024"`, `lifecycle="active"`, `publication_year=2024`.

| Capability | Rule | Citation |
|------------|------|----------|
| Phone | `Section 1.1-nanp-structure` | NANP numbering plan structure (NPA NXX-XXXX) |
| Phone | `Section 1.2-service-npa` | NANPA service NPA assignment table |

***

## Unicode Consortium — CLDR

| Capability | Specification | Version | Rule | Citation | Year | Reference | Kind |
|------------|---------------|---------|------|----------|------|-----------|------|
| Country | CLDR v45 | 45 | `Section-localized-names` | CLDR v45 localized country names | 2024 | https://cldr.unicode.org/ | registry |
| Currency | Unicode CLDR | 47 | `Section-symbols` | CLDR v47 currency symbols | 2025 | https://cldr.unicode.org/ | specification |
| Currency | Unicode CLDR | 47 | `Section-names` | CLDR v47 currency display names | 2025 | https://cldr.unicode.org/ | specification |
| Money | Unicode CLDR | 47 | `Section-symbols` | CLDR v47 currency symbols | 2025 | https://cldr.unicode.org/ | specification |
| Money | Unicode CLDR | 47 | `Section-names` | CLDR v47 currency display names | 2025 | https://cldr.unicode.org/ | specification |
| Language | CLDR Language Display Names | 46 | `Section-localized-names` | CLDR v46 localized language display names | 2025 | https://www.unicode.org/cldr/charts/46/summary/root.html | registry |

Authority field in provenance is either `"Unicode"` (Country) or `"Unicode CLDR"` (Currency/Money/Language), both referring to the Unicode CLDR project. All are `lifecycle="active"`.

***

## SIL International (ISO 639-3 Registration Authority)

Specification: **ISO 639-3:2007**, `https://www.iso.org/standard/39534.html`, `kind="specification"`, `version="2007"`, `lifecycle="active"`, `publication_year=2007`, `authority="SIL International (ISO 639-3 RA)"`.

| Capability | Rule | Citation |
|------------|------|----------|
| Language | `Section 4-comprehensive-alpha-3` | Section 4 (comprehensive alpha-3, 7000+ entries) |
| Language | `Section 4-private-alpha-3` | Section 4 (private-use qaa-qtz) |

***

## International ISBN Agency

| Capability | Specification | Version | Rule | Citation | Year | Reference | Kind |
|------------|---------------|---------|------|----------|------|-----------|------|
| ISBN | ISBN Users' Manual | 2012 | `Section 6-isbn10-check-digit` | Section 6 (ISBN-10 check digit) | 2012 | https://www.isbn-international.org/sites/default/files/ISBN%20Manual%202012%20-corr.pdf | specification |
| ISBN | ISBN Range Message | 2026-08-05 | `Section 4-registrant-range` | Section 4 (registrant range) | 2026 | https://www.isbn-international.org/range\_file\_generation | registry |

***

## WHATWG — Web Hypertext Application Technology Working Group

Specification: **URL Standard**, Living Standard — `https://url.spec.whatwg.org/`, `kind="specification"`, `lifecycle="active"`, `publication_year=2026`.

| Capability | Rule | Citation |
|------------|------|----------|
| URL | `WHATWG URL Standard` | Section 4.4 (basic URL parser); RFC 3986 §3.1 / RFC 3987 §2 grammar |

***

## Derived conventions — Date (non-authoritative)

These two Date rules carry `authority="Derived convention"`, `kind="convention"` and no `reference_url`. They document widely-used locale conventions rather than an external specification.

| Capability | Specification | Rule | Citation | Year |
|------------|---------------|------|----------|------|
| Date | US locale — MM/DD/YYYY | `Derived-US-date-format` | Derived convention — MM/DD/YYYY (US locale, en-US) | 2023 |
| Date | European locale — DD/MM/YYYY | `Derived-European-date-format` | Derived convention — DD/MM/YYYY (European locale) | 2010 |

***

## How to cite Paxman in your work

A methods section can cite both Paxman itself and the underlying authority:

> "Country names were canonicalized to ISO 3166-1 alpha-2 codes using Paxman v0.2.0 (Paxman Library, https://github.com/nexusnv/paxman-python) with provenance ISO 3166-1:2020, Section-names (official English short names), publication year 2020."

Include `result.version_stamp.paxman_version` and `result.version_stamp.recognition_revision` alongside `provenance` for full reproducibility. All provenance above is baked into the library — no runtime network access is needed to reproduce a citation.

***

## See also

* [Provenance](concepts/provenance/) — the `Provenance` object shape and how `validation_rule` + provenance form a complete citation
* [Execution Result](concepts/execution-result/) — reading `candidates` and `version_stamp` on every status
* [Capabilities](capabilities/) — per-capability guides with provenance per page
* [API Reference](api-reference/) — `Provenance`, `Candidate`, `VersionStamp` type reference
