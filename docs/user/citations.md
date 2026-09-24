---
title: "Citations"
---

Every validated value in Paxman carries **provenance** — the authority, specification, version, and section that vouches for it. This page is the curated, authority-grouped index of **all cited provenance** across the 27 shipped capabilities. Use it to audit results, write methods sections, or compare Paxman against another system.

> **How to read provenance in code:** `result.candidates[n].provenance[0]` is a `Provenance` (`authority`, `specification_name`, `version`, `publication_year`, `reference_url`, `kind`, `lifecycle`) and `candidate.validation_rule` is the section citation (e.g. `Section 3.4.1-addr-spec`). See [Provenance](concepts/provenance/) for the object shape.

```python
for c in result.candidates:
    p = c.provenance[0]
    print(f"{c.validation_rule} — {p.authority} {p.specification_name} ({p.version}), {p.reference_url}")
```

All entries below are derived from the `PUBLICATION` constants and `citation`/`name` fields on each shipped rule (`paxman/capabilities/<Name>/rules/*.py`). No network lookup is involved — the data is baked into the installed library build and versioned via `version_stamp`.

---

## At a glance — citations by authority

| Authority | Specifications | Capabilities | Rules |
|-----------|---------------|--------------|-------|
| **BIPM** | SI Brochure: The International System of Units (SI), 9th ed. (2019) | SI Unit | 6 |
| **IETF** | RFC 5322, RFC 6761, RFC 791, RFC 5952, RFC 3966, BCP 47 RFC 5646, RFC 5870, RFC 7946, RFC 9562, RFC 1034, RFC 1035, RFC 5893 | Email, IP, Phone, Language, Coordinates, UUID, Domain | 12 |
| **IANA** | IANA Language Subtag Registry (Rolling File-Date 2026-08-08); IANA Time Zone Database 2026d; IANA Root Zone Database (tlds-alpha v2026092300) | Language, Timezone, Domain | 7 |
| **ISO** | ISO 9362:2022, ISO 27729:2024, ISO 3166-1:2020, ISO 3166-3, ISO 4217, ISO 8601:2019, ISO 8601-1:2019, ISO 2108:2017, ISO 13616-1:2020, ISO 639-1/2/5, ISO 80000-1:2022, ISO 6709:2022, ISO 26324:2025, ISO 6166:2021, ISO 17442-1:2020, ISO/IEC 7812-1:2017 | BIC, ORCID, Country, Currency, Money, Date, ISBN, IBAN, Language, SI Unit, Coordinates, UtcOffset, DOI, ISIN, LEI, CreditCard | 26 |
| **ISSN International Centre** | ISO 3297:2022 | ISSN | 1 |
| **ANNA** | ANNA ISIN Guidelines V25 (Dec 2025) | ISIN | 1 |
| **GLEIF** | GLEIF LOU prefix list (accredited-LOU directory + concatenated-file census) | LEI | 1 |
| **GS1** | GS1 General Specifications 26.0, GS1 Prefix allocation, Verified by GS1 | GTIN | 3 |
| **Brand networks** | Brand IIN/length tables (secondary) | CreditCard | 1 |
| **ITU-T** | E.164 (2010) | Phone | 2 |
| **NANPA** | North American Numbering Plan (NANP) (2024) | Phone | 2 |
| **Unicode Consortium (CLDR)** | CLDR v45, Unicode CLDR v47, CLDR Language Display Names v46 | Country, Currency, Money, Language | 6 |
| **Unicode Consortium** | UTS #46 v18.0.0 (shipped table 15.1.0) | Domain | 1 |
| **SIL International (ISO 639-3 RA)** | ISO 639-3:2007 | Language | 2 |
| **International ISBN Agency** | ISBN Users' Manual (2012), ISBN Range Message (2026-08-05) | ISBN | 2 |
| **WHATWG** | URL Standard (Living Standard) | URL | 1 |
| **IEEE** | IEEE Std 802-2024 | MacAddress | 1 |
| **IUPAC** | IUPAC Periodic Table 04 May 2022, IUPAC Red Book 2005 Ch. IR-3 | ChemicalElement | 2 |
| **Derived convention** | US locale — MM/DD/YYYY, European locale — DD/MM/YYYY | Date | 2 |

> **Note on "Derived convention":** The two Date rules for `MM/DD/YYYY` and `DD/MM/YYYY` are locale conventions rather than an external standards publication. They are included here for completeness and carry `kind="convention"` with no `reference_url`.

---

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

---

## IETF — Internet Engineering Task Force

| Capability | Specification | Version | Rule | Citation | Year | Reference |
|------------|---------------|---------|------|----------|------|-----------|
| Email | RFC 5322 | 2008 | `Section 3.4.1-addr-spec` | Section 3.4.1 (addr-spec) | 2008 | https://tools.ietf.org/html/rfc5322 |
| Email | RFC 6761 | 2012 | `Section 6.3-localhost` | Section 6.3 (localhost) | 2012 | https://tools.ietf.org/html/rfc6761 |
| IP | RFC 791 | 1981 | `Section 3.2-ipv4-address` | Section 3.2 (internet addressing) — dotted-decimal per RFC 1123 §2.1 | 1981 | https://datatracker.ietf.org/doc/html/rfc791 |
| IP | RFC 5952 | 2010 | `Section 4-ipv6-text-representation` | Section 4 (IPv6 text representation) + RFC 4291 §2.2 (mixed `LS32` `::ffff:192.0.2.1`) | 2010 | https://datatracker.ietf.org/doc/html/rfc5952 |
| Phone | RFC 3966 | 2004 | `Section 3-tel-uri` | Section 3 (tel URI) / Section 3.1 (global numbers) | 2004 | https://tools.ietf.org/html/rfc3966 |
| Language | BCP 47 RFC 5646 | 2009-09 | `Section 2.1-syntax` | Section 2.1 (Language-Tag ABNF, well-formed only) | 2009 | https://www.rfc-editor.org/rfc/rfc5646.txt |
| Coordinates | RFC 5870 | 2010 | `Section 3.3-geo-uri-validity` | Section 3.3 (Geo URI validity) | 2010 | https://www.rfc-editor.org/rfc/rfc5870.txt |
| Coordinates | RFC 7946 | 2016 | `Section 3.1.1-position` | Section 3.1.1 (Position) | 2016 | https://www.rfc-editor.org/rfc/rfc7946.txt |
| UUID | RFC 9562 | 2024 | `Section 4-uuid-format` | Section 4 (128-bit format; hex-and-dash ABNF, no checksum, no registry) | 2024 | https://www.rfc-editor.org/rfc/rfc9562 |
| Domain | RFC 1034 | 1987 | `Section-3.1-name-syntax` | Section 3.1 (name syntax: ≥2 labels, no empty label) | 1987 | https://www.rfc-editor.org/rfc/rfc1034 |
| Domain | RFC 1035 | 1987 | `Section-2.3.4-label-length` | Section 2.3.4 (63 octets/label, 253 chars/name post-encode) | 1987 | https://www.rfc-editor.org/rfc/rfc1035 |
| Domain | RFC 5893 | 2010 | `Section-2-bidi-context` | Section 2 (Bidi rule six conditions, plus ContextJ) | 2010 | https://www.rfc-editor.org/rfc/rfc5893 |

All IETF entries are `kind="specification"`, `lifecycle="active"`.

---

## IANA — Internet Assigned Numbers Authority

Specification: **IANA Language Subtag Registry**, Rolling File-Date 2026-08-08 — `https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry` — `kind="registry"`, `lifecycle="active"`, `publication_year=2026`.

| Capability | Rule | Citation |
|------------|------|----------|
| Language | `Section-iana-registry` | IANA Registry Type language/script/region/variant Deprecated Preferred Prefix Suppress-Script |
| Language | `Section-iana-registry-private` | IANA Registry private-use qaa-qtz/Qaaa-Qabx/QM-QZ/AA/XA-XZ/ZZ/x- |
| Timezone | `Section zone-key-membership` | zone1970.tab col 3 + backward Links + etcetera (vendored File-Date 2026d) |
| Timezone | `Section link-resolution` | backward Link TARGET LINK-NAME lines (vendored File-Date 2026d) |
| Timezone | `Section systemv-zones` | backward SystemV Zones EST5EDT/CST6CDT/MST7MDT/PST8PDT (vendored File-Date 2026d) |
| Timezone | `Section abbreviation-refusal` | theory.html abbreviation ambiguity (IST/CST/PST) + backward short-caps Links carve set (vendored File-Date 2026d) |
| Domain | `root-zone-membership` | tlds-alpha snapshot membership (encoded TLD must be delegated; 1,438 entries) |

Specification for the Timezone rows: **IANA Time Zone Database**, release 2026d — `https://www.iana.org/time-zones` (membership/link/systemv) and `https://data.iana.org/time-zones/theory.html` (abbreviation refusal) — `kind="registry"`, `lifecycle="active"`, `publication_year=2026`.

Specification for the Domain row: **IANA Root Zone Database** (tlds-alpha-by-domain.txt v2026092300) — `https://data.iana.org/TLD/tlds-alpha-by-domain.txt` — `kind="registry"`, `version="IANA tlds-alpha v2026092300"`, `lifecycle="active"`, `publication_year=2026`.

---

## ISO — International Organization for Standardization

Across 15 ISO publications (26 rules):

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
| DOI | ISO 26324:2025 | 2025 | `Section 4-doi-syntax` | Section 4 (DOI name syntax: prefix/suffix, no checksum, no registry) | 2025 | https://www.iso.org/standard/88862.html |
| ISIN | ISO 6166:2021 | 2021 | `Section 4-isin-structure-check-digit` | Section 4 (ISIN structure + modulus 10 Double-Add-Double check digit) | 2021 | https://www.iso.org/standard/78502.html |
| LEI | ISO 17442-1:2020 | 2020 | `Section 4-lei-structure-mod97-10` | Section 4 (LEI structure + whole-string MOD 97-10, via ISO/IEC 7064:2003) | 2020 | https://www.iso.org/standard/78829.html |
| ISBN | ISO 2108:2017 | 2017 | `Section 5.3-isbn13-check-digit` | Section 5.3 (ISBN-13 check digit) | 2017 | https://www.iso.org/standard/65483.html |
| ISBN | ISO 2108:2017 | 2017 | `Section 4.2-gs1-prefix` | Section 4.2 (GS1 prefix) | 2017 | https://www.iso.org/standard/65483.html |
| IBAN | ISO 13616-1:2020 | 2020 | `Section 4-iban-structure-mod97` | Section 4-5 (structure + MOD 97-10, via ISO/IEC 7064:2003) | 2020 | https://www.iso.org/standard/81090.html |
| Coordinates | ISO 6709:2022 | 2022 | `Section 6-coordinate-structure` | Section 6 (Coordinate structure) | 2022 | https://www.iso.org/standard/75147.html |
| Coordinates | ISO 6709:2022 | 2022 | `Section Annex-h-string-expression` | Annex H (String expression of a point) | 2022 | https://www.iso.org/standard/75147.html |
| Language | ISO 639-1:2002 | 2002 | `Section 4-alpha-2-code` | Section 4 (alpha-2 code, 184 entries) | 2002 | https://www.iso.org/standard/22109.html |
| Language | ISO 639-1:2002 | 2002 | `Section-english-name-mapping` | Section 4 (English language names → alpha-2) | 2002 | https://www.iso.org/standard/22109.html |
| Language | ISO 639-2:1998 | 1998 | `Section 4-alpha-3-code` | Section 4 (alpha-3 code, 487 entries T/B) | 1998 | https://www.iso.org/standard/4767.html |
| Language | ISO 639-5:2008 | 2008 | `Section 4-collective-code` | Section 4 (collective code, 115 entries) | 2008 | https://www.iso.org/standard/39536.html |
| SI Unit | ISO 80000-1:2022 Quantities and units — Part 1: General | 2022 | `Section 6.5-compounds` | ISO 80000-1:2022, §6.5 (unit symbols in products and quotients) | 2022 | https://www.iso.org/standard/76921.html |
| UtcOffset | ISO 8601-1:2019 | 2019 | `Section offset-structure` | ISO 8601-1:2019 Section 3 (offset representations); RFC 3339 Section 5.6 (time-numoffset +-HH:MM, Z) | 2019 | https://www.iso.org/standard/70907.html |
| CreditCard | ISO/IEC 7812-1:2017 | 2017 | `Section 5-pan-structure-luhn` | ISO/IEC 7812-1:2017 Section 5 (structure) + Annex B (Luhn MOD-10) | 2017 | https://www.iso.org/standard/70484.html |

All ISO entries are `lifecycle="active"`. ISO 3166-1 entries are `kind="registry"`; ISO 3166-3, ISO 8601, ISO 2108, ISO 13616-1, ISO 639-* and ISO 80000-1 are `kind="specification"`; ISO 4217 is `kind="specification"` with `version=None` (the code list is maintained by the ISO 4217 Maintenance Agency — see citation).

---

## ISSN International Centre

Specification: **ISO 3297:2022**, `https://www.iso.org/standard/84536.html`, `kind="specification"`, `version="2022"`, `lifecycle="active"`, `publication_year=2022`.

| Capability | Rule | Citation |
|------------|------|----------|
| ISSN | `Section 4-issn-check-digit` | Section 4 (check digit) |

---

## ANNA — Association of National Numbering Agencies

Specification: **ANNA ISIN Guidelines**, V25 (Dec 2025) — `https://anna-web.org/wp-content/uploads/2025/11/ISIN-Guidelines-Dec-2025_Amendment_clean.pdf` — `kind="policy"`, `version="2025-12 (V25; superseded by V26 Jun 2026)"`, `lifecycle="active"`, `publication_year=2025`.

| Capability | Rule | Citation |
|------------|------|----------|
| ISIN | `Section 5-country-and-special-prefix` | Section 5 (country and special prefix: ISO 3166-1 alpha-2 plus Guidelines-attested `EU`/`XS`/`XA`–`XD`/`XT`, RA-attested `EZ`, validator/user-assigned `XF`/`XK`/`QS`/`QT`; `ZZ` provisional, excluded) |

> **V26 note:** the ANNA ISIN Guidelines V26 (Jun 2026) supersedes V25. The ISIN capability pins V25 as its v1 authority; re-attest the prefix table against V26 before adopting it.

---

## GLEIF — Global Legal Entity Identifier Foundation

Specification: **GLEIF LOU prefix list** — `https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file` — `kind="registry"`, `version="Rolling"`, `lifecycle="active"`, `publication_year=2026`.

| Capability | Rule | Citation |
|------------|------|----------|
| LEI | `Section 1-lou-prefix-membership` | Section 1 (accredited-LOU prefix membership: 4-char issuer blocks from the accredited-LOU directory + concatenated-file census; append-only) |

---

## GS1

Specifications: **GS1 General Specifications** — `https://ref.gs1.org/standards/genspecs/` — `kind="specification"`, `version="26.0"`, `lifecycle="active"`, `publication_year=2026`.

**GS1 Prefix allocation** — `https://www.gs1.org/standards/id-keys/company-prefix` — `kind="registry"`, `version="Rolling 2026"`, `lifecycle="active"`, `publication_year=2026`.

**Verified by GS1** — `https://www.gs1.org/services/verified-by-gs1` — `kind="registry"`, `version="Rolling"`, `lifecycle="active"`, `publication_year=2019`.

| Capability | Rule | Citation |
|------------|------|----------|
| GTIN | `Section 1-gtin-structure-check-digit` | Section 1 (GTIN structure + Mod-10 check digit) |
| GTIN | `Section 2-gs1-prefix` | Section 2 (GS1 prefix allocation) |
| GTIN | `Section 3-verified-liveness` | Section 3 (Verified by GS1 liveness) |

---

## Brand networks

Specification: **Brand IIN/length tables (secondary)** — `https://en.wikipedia.org/wiki/Payment_card_number` — `kind="registry"`, `version="Rolling 2026"`, `lifecycle="active"`, `publication_year=2026`.

| Capability | Rule | Citation |
|------------|------|----------|
| CreditCard | `Section 1-brand-prefix-membership` | Brand IIN/length tables (secondary) |

---

## ITU-T — International Telecommunication Union

Specification: **E.164**, `https://www.itu.int/rec/T-REC-E.164`, `kind="specification"`, `version="2010"`, `lifecycle="active"`, `publication_year=2010`.

| Capability | Rule | Citation |
|------------|------|----------|
| Phone | `Section 6.1-international-number` | Section 6.1 (number structure) |
| Phone | `Section 6.2-country-code` | Annex A (table of assigned country codes) |

---

## NANPA — North American Numbering Plan Administrator

Specification: **North American Numbering Plan (NANP)**, `https://www.nanpa.com/`, `kind="registry"`, `version="2024"`, `lifecycle="active"`, `publication_year=2024`.

| Capability | Rule | Citation |
|------------|------|----------|
| Phone | `Section 1.1-nanp-structure` | NANP numbering plan structure (NPA NXX-XXXX) |
| Phone | `Section 1.2-service-npa` | NANPA service NPA assignment table |

---

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

## Unicode Consortium — UTS #46

Specification: **UTS #46 v18.0.0**, Unicode IDNA Compatibility Processing — `https://www.unicode.org/reports/tr46/` — `kind="specification"`, `version="18.0.0"`, `lifecycle="active"`, `publication_year=2026`, `authority="Unicode"`. The shipped mapping table is UTS #46 15.1.0 (shared in-tree text with URL); STD3 rules ON, non-transitional processing.

| Capability | Rule | Citation |
|------------|------|----------|
| Domain | `UTS46-statuses` | Statuses + STD3 + hyphen checks + ACE round trip (shipped table 15.1.0) |

---

## SIL International (ISO 639-3 Registration Authority)

Specification: **ISO 639-3:2007**, `https://www.iso.org/standard/39534.html`, `kind="specification"`, `version="2007"`, `lifecycle="active"`, `publication_year=2007`, `authority="SIL International (ISO 639-3 RA)"`.

| Capability | Rule | Citation |
|------------|------|----------|
| Language | `Section 4-comprehensive-alpha-3` | Section 4 (comprehensive alpha-3, 7000+ entries) |
| Language | `Section 4-private-alpha-3` | Section 4 (private-use qaa-qtz) |

---

## International ISBN Agency

| Capability | Specification | Version | Rule | Citation | Year | Reference | Kind |
|------------|---------------|---------|------|----------|------|-----------|------|
| ISBN | ISBN Users' Manual | 2012 | `Section 6-isbn10-check-digit` | Section 6 (ISBN-10 check digit) | 2012 | https://www.isbn-international.org/sites/default/files/ISBN%20Manual%202012%20-corr.pdf | specification |
| ISBN | ISBN Range Message | 2026-08-05 | `Section 4-registrant-range` | Section 4 (registrant range) | 2026 | https://www.isbn-international.org/range_file_generation | registry |

---

## WHATWG — Web Hypertext Application Technology Working Group

Specification: **URL Standard**, Living Standard — `https://url.spec.whatwg.org/`, `kind="specification"`, `lifecycle="active"`, `publication_year=2026`.

| Capability | Rule | Citation |
|------------|------|----------|
| URL | `WHATWG URL Standard` | Section 4.4 (basic URL parser); RFC 3986 §3.1 / RFC 3987 §2 grammar |

---

## IEEE — Institute of Electrical and Electronics Engineers

| Capability | Specification | Version | Rule | Citation | Year | Reference |
|------------|---------------|---------|------|----------|------|-----------|
| MacAddress | IEEE Std 802-2024 | 2024 | `Section 8.2-eui-structure` | Section 8.2 (Universal addresses; EUI-48/EUI-64, I/G and U/L bits) | 2024 | https://standards.ieee.org/ieee/802/10894 |

All IEEE entries are `kind="specification"`, `lifecycle="active"`.

## IUPAC — International Union of Pure and Applied Chemistry

| Capability | Specification | Version | Rule | Citation | Year | Reference |
|------------|---------------|---------|------|----------|------|-----------|
| ChemicalElement | IUPAC Periodic Table of the Elements | 04 May 2022 | `Section PTOE-element-registry` | Table I names and symbols (118 elements, Z 1-118) | 2022 | https://iupac.org/wp-content/uploads/2022/07/IUPAC_Periodic_Table-04May22_CRA.pdf |
| ChemicalElement | IUPAC Red Book 2005, Ch. IR-3 (Nomenclature of Inorganic Chemistry) | 2005 | `Section IR-3.1-names-and-symbols` | Chapter IR-3, Table I (names and symbols) | 2005 | https://iupac.qmul.ac.uk/RedBook2005.pdf |

The registry entry is `kind="registry"`; the Red Book entry is `kind="specification"`; both are `lifecycle="active"`.

## Derived conventions — Date (non-authoritative)

These two Date rules carry `authority="Derived convention"`, `kind="convention"` and no `reference_url`. They document widely-used locale conventions rather than an external specification.

| Capability | Specification | Rule | Citation | Year |
|------------|---------------|------|----------|------|
| Date | US locale — MM/DD/YYYY | `Derived-US-date-format` | Derived convention — MM/DD/YYYY (US locale, en-US) | 2023 |
| Date | European locale — DD/MM/YYYY | `Derived-European-date-format` | Derived convention — DD/MM/YYYY (European locale) | 2010 |

---

## How to cite Paxman in your work

A methods section can cite both Paxman itself and the underlying authority:

> "Country names were canonicalized to ISO 3166-1 alpha-2 codes using Paxman v0.2.0 (Paxman Library, https://github.com/nexusnv/paxman-python) with provenance ISO 3166-1:2020, Section-names (official English short names), publication year 2020."

Include `result.version_stamp.paxman_version` and `result.version_stamp.recognition_revision` alongside `provenance` for full reproducibility. All provenance above is baked into the library — no runtime network access is needed to reproduce a citation.

---

## See also

- [Provenance](concepts/provenance/) — the `Provenance` object shape and how `validation_rule` + provenance form a complete citation
- [Execution Result](concepts/execution-result/) — reading `candidates` and `version_stamp` on every status
- [Capabilities](capabilities/) — per-capability guides with provenance per page
- [API Reference](api-reference/) — `Provenance`, `Candidate`, `VersionStamp` type reference
