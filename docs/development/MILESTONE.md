# Paxman Capability Milestones

> **Purpose:** Roadmap guidance for capabilities to bring into Paxman, ordered by priority.
> This table is a planning aid — details need not be exactly accurate in terms of implementation.
> 23 capabilities are shipped (BIC, ChemicalElement, Coordinates, Country, Currency, Date, DOI, Email, IBAN, IP, ISBN, ISIN, ISSN, Language, MacAddress, Money, ORCID, Phone, SIUnit, Timezone, URL, UtcOffset, UUID) and are listed in §1 only — they are excluded from the future roadmap in §2.

---

## 1. Delivered Capabilities (23 shipped)

Verified against `paxman/capabilities/__init__.py` + `paxman/api/bootstrap.py:_SHIPPED` (alphabetical bootstrap order) and `paxman/capabilities/<Name>/rules/` provenance constants. Examples were re-checked through `canonicalize()` on 2026-09-22.

| # | Capability | Authorities | Example input → canonical_value | Research / Plan |
|---|-----------|------------|-------------------------------|-----------------|
| 1 | **BIC** | ISO 9362:2022, ISO 3166-1 (country codes plus XK) | "deutdeff" → "DEUTDEFF" | `research/2026-08-23-bic-canonicalization.md`, `plans/2026-08-23-bic-capability.md` |
| 2 | **ChemicalElement** | IUPAC Red Book 2005, IUPAC Periodic Table 04 May 2022 | "Iron" → "Fe" | `research/2026-09-02-chemical-element-canonicalization.md`, `plans/2026-09-04-element-capability.md` |
| 3 | **Coordinates** | ISO 6709:2022, RFC 5870:2010, RFC 7946:2016 | "40.4461, -79.9822" → "40.4461, -79.9822" | `research/2026-09-01-coordinates-canonicalization.md`, `plans/2026-09-01-coordinates-capability.md` |
| 4 | **Country** | ISO 3166-1:2020, ISO 3166-3, CLDR v45 | "Germany" → "DE" | `plans/2026-07-28-country-capability-implementation.md` |
| 5 | **Currency** | ISO 4217, CLDR v47 | "euro" → "EUR" | `plans/2026-08-08-currency-capability.md` |
| 6 | **Date** | ISO 8601:2019, US federal convention, EN 50160 convention | "2024-01-15" → "2024-01-15" | — |
| 7 | **DOI** | ISO 26324:2025 | "doi:10.1000/xyz123" → "10.1000/xyz123" | `research/2026-09-18-doi-canonicalization.md`, `plans/2026-09-18-doi-capability.md` |
| 8 | **Email** | RFC 5322:2008, RFC 6761:2012 | "User@Example.COM" → "User@example.com" | `plans/2026-07-26-email-capability.md` |
| 9 | **IBAN** | ISO 13616-1:2020 (MOD 97-10 per ISO/IEC 7064) | "DE89 3704 0044 0532 0130 00" → "DE89370400440532013000" | `research/2026-08-22-iban-canonicalization.md`, `plans/2026-08-22-iban-capability.md` |
| 10 | **IP** | RFC 791:1981, RFC 4291 §2.2, RFC 5952:2010 | "192.168.0.1" → "192.168.0.1" | — |
| 11 | **ISBN** | ISO 2108:2017, ISBN Users' Manual, ISBN Range Message 2026-08-05 | "0-14-044913-2" → "9780140449136" | `research/2026-08-05-isbn-canonicalization.md`, `plans/2026-08-05-isbn-capability.md` |
| 12 | **ISIN** | ISO 6166:2021, ANNA ISIN Guidelines Dec 2025 | "US0378331005" → "US0378331005" | `research/2026-08-24-isin-canonicalization.md`, `plans/2026-09-21-isin-capability.md` |
| 13 | **ISSN** | ISO 3297:2022 | "0024-9319" → "0024-9319" | `research/2026-08-21-issn-canonicalization.md`, `plans/2026-08-21-issn-capability.md` |
| 14 | **Language** (absorbs the old "Language tag (BCP 47)" roadmap row — BCP 47 tags such as "EN_us" → "en-US" already canonicalize under this capability) | ISO 639-1:2002, ISO 639-2:1998, ISO 639-3:2007, ISO 639-5:2008, BCP 47 RFC 5646, IANA Language Subtag Registry (File-Date 2026-08-08), CLDR | "German" → "de"; "EN_us" → "en-US" | `research/2026-08-23-language-canonicalization.md`, `plans/2026-08-23-language-capability.md` |
| 15 | **MacAddress** | IEEE Std 802-2024 | "00-1A-2B-3C-4D-5E" → "00:1A:2B:3C:4D:5E" | `research/2026-08-31-mac-address-canonicalization.md`, `plans/2026-09-01-mac-address-capability.md` |
| 16 | **Money** | ISO 4217, CLDR v47 | "$100 USD" → "USD 100.00" | `research/2026-08-05-money-canonicalization.md`, `plans/2026-08-05-money-capability.md` |
| 17 | **ORCID** | ISO 27729:2024 (MOD 11-2) | "https://orcid.org/0000-0002-1825-0097" → "0000-0002-1825-0097" | `research/2026-08-23-orcid-canonicalization.md`, `plans/2026-08-23-orcid-capability.md` |
| 18 | **Phone** | ITU-T E.164:2010, RFC 3966:2004, NANP | "+1 650-253-0000" → "+16502530000" | `plans/2026-08-01-phone-number-capability.md` |
| 19 | **SIUnit** | BIPM SI Brochure 9th ed. 2019, ISO 80000-1:2022 | "Kilogram" → "kg" | `research/2026-08-09-si-unit-canonicalization.md`, `plans/2026-08-09-si-units-capability.md` |
| 20 | **Timezone** | IANA Time Zone Database 2026d | "US/Eastern" → "America/New_York" (bare abbreviations such as "EST"/"CET" are refused → `INVALID`, not resolved) | `research/2026-09-14-timezone-canonicalization.md`, `plans/2026-09-14-timezone-capability.md` |
| 21 | **URL** | WHATWG URL Living Standard | "HTTPS://Example.COM:443/a/../b" → "https://example.com/b" | `research/2026-08-06-url-canonicalization.md`, `plans/2026-08-06-url-capability.md` |
| 22 | **UtcOffset** | ISO 8601-1:2019, RFC 3339 | "UTC+5:30" → "+05:30" | — |
| 23 | **UUID** | RFC 9562:2024 (obsoletes RFC 4122) | "urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8" → "6ba7b810-9dad-11d1-80b4-00c04fd430c8" | `research/2026-09-16-uuid-canonicalization.md`, `plans/2026-09-17-uuid-capability.md` |

Notes on §1:

- The old roadmap's aspirational Timezone example ("EST" → "America/New_York") was wrong: the shipped `iana_tz_abbreviations` rule refuses bare abbreviations (`INVALID`). The link form ("US/Eastern" → "America/New_York") is the correct example.
- The old roadmap's "Language tag (BCP 47)" row is absorbed: `Language` already ships BCP 47 + IANA-registry + CLDR rules, so it is not a separate future capability.
- "Geographic coordinate" is shipped as `Coordinates` (ISO 6709 string-expression input "+40.4461-079.9822/" re-enters as "40.4461, -79.9822").

---

## 2. Future Roadmap (not yet implemented)

### 2A. Retained candidates (carried over — still unbuilt)

| # | Capability | Why this capability? | Grammar strategy | Provenance publications | Example input → canonical_value |
|---|-----------|---------------------|------------------|------------------------|-------------------------------|
| 1 | **Domain name / IDN** | Hostnames mix case, trailing dots, Unicode vs punycode. Overlaps the URL IDNA table but no standalone host capability exists. | PARSER (lowercase, IDNA 2008 punycode-encode, strip trailing dot) | RFC 1034, RFC 1035, RFC 5890/5891 (IDNA 2008), IANA Root Zone Database | "Example.COM" → "example.com", "münchen.de" → "xn--mnchen-3ya.de" |
| 2 | **MIME media type** | Content-Type headers vary in case and legacy aliases ("TEXT/HTML", "image/jpg"). IANA registry is authoritative. | LOOKUP_TABLE (case-insensitive IANA registry + alias resolution) | IANA Media Types registry, RFC 6838, RFC 2045 | "Text/Plain" → "text/plain", "image/jpg" → "image/jpeg" |
| 3 | **Character encoding** | Encoding labels vary wildly ("UTF8", "latin1", "unicode"). IANA charset registry + WHATWG Encoding give canonical names. | LOOKUP_TABLE (case-insensitive alias resolution) | IANA Character Sets registry, WHATWG Encoding Standard | "UTF8" → "utf-8", "latin1" → "windows-1252" (verify against registry; iso-8859-1 alias per WHATWG) |
| 4 | **HTTP header name** | Header field names are case-insensitive but conventionally cased ("Content-Type" vs "content-type"). RFC 9110 normalizes. | PARSER (lowercase, preserve hyphens) | RFC 9110 (HTTP Semantics), RFC 9111 (Caching) | "Content-Type" → "content-type" |
| 5 | **Unicode normalization** | Visually identical strings differ in combining sequences and compatibility forms. UAX #15 defines NFC/NFD/NFKC/NFKD. | PARSER (NFC default; NFKC/NFD as offered formats) | Unicode UAX #15 | "e + combining acute" → "é" (NFC) |
| 6 | **LEI** | Legal-entity IDs for finance; natural sibling to shipped BIC/IBAN/ISIN. 20-char alphanumeric with LOU prefix and 2 MOD 97-10 check digits. | PARSER (uppercase, strip spaces, LOU-prefix structure) | ISO 17442-1:2020, GLEIF registry (deferred live lookup) | "5493 001K JTII GC8Y 1R12" → "5493001KJTIIGC8Y1R12" |
| 7 | **Credit card number (PAN)** | PANs appear spaced, dashed, continuous. ISO/IEC 7812 + Luhn gives deterministic validation. Note PCI-DSS handling caveats. | PARSER (strip separators, Luhn check, compact canonical) | ISO/IEC 7812-1:2017 | "4111-1111-1111-1111" → "4111111111111111" |
| 8 | **SPDX license** | License strings vary ("MIT License", "GPLv3", "Apache-2.0"). SPDX License List is the authority. | LOOKUP_TABLE (case-insensitive + deprecated-ID mapping) | SPDX License List, SPDX Specification v3.x | "MIT License" → "MIT", "GPLv3" → "GPL-3.0-only" |
| 9 | **Semantic version** | Version strings carry "v" prefixes and partial triples ("v1.0", "1.0.0-beta.1"). SemVer 2.0.0 defines canonical form. | PARSER (strip "v", three-part normalization, preserve pre-release/build) | SemVer 2.0.0 (semver.org) | "v1.0.0" → "1.0.0" |
| 10 | **TLD** | Suffixes appear with/without dot and mixed case (".COM", "org"). IANA root zone is authoritative; consider folding into Domain-name work. | LOOKUP_TABLE (case-insensitive IANA root zone, lowercase with leading dot) | IANA Root Zone Database, RFC 1591 | ".COM" → ".com" |
| 11 | **Color name (CSS)** | Design data mixes named colors ("Red", "Aqua"). CSS Color Module 4 fixes the keyword set. | LOOKUP_TABLE (case-insensitive → lowercase hex) | W3C CSS Color Module Level 4 | "Red" → "#ff0000" |
| 12 | **HTML tag name** | Markup mixes tag case ("<DIV>", "<Br />"). WHATWG fixes lowercase names. | PARSER (lowercase, strip brackets) | WHATWG HTML Living Standard | "<DIV>" → "div" |
| 13 | **Postal code** | Address data varies by country ("10001-1234", "SW1A 1AA"). No single global spec — needs a `country` contract parameter. | PARSER (country-dispatched; uppercase/strip per national rule) | UPU S42, USPS Publication 28, Royal Mail PAF, Canada Post guides | "sw1a 1aa" → "SW1A 1AA" (with `country="GB"`) |

### 2B. Newly surfaced candidates (websearch 2026-09-22)

Screened for Paxman fit: ambiguous human representations, stable authority, deterministic checkable canonical form, no network inference.

| # | Capability | Why this capability? | Grammar strategy | Provenance publications | Example input → canonical_value |
|---|-----------|---------------------|------------------|------------------------|-------------------------------|
| 14 | **GTIN / EAN / UPC** | Product identifiers appear as GTIN-8/12/13/14 with spaces/hyphens and missing leading zeros. GS1 check digit makes them self-validating; natural sibling to ISBN/ISSN. | PARSER (strip separators, zero-pad to GTIN-14 for validation, GS1 Mod-10 check, canonical GTIN-13/14) | GS1 General Specifications (GenSpecs), GS1 check-digit calculator | "590 1234 12345 7" → "05901234123457" |
| 15 | **VIN** | 17-char vehicle IDs appear lowercased/spaced; letters I/O/Q excluded. ISO 3779 defines structure; FMVSS 115 check digit (pos. 9, transliteration-weighted) applies to NA-market VINs. | PARSER (uppercase, strip separators, charset guard, transliteration check where applicable) | ISO 3779:2009, ISO 4030, SAE J272 / 49 CFR 565 (check digit) | "1m8gdm9axkp042788" → "1M8GDM9AXKP042788" |
| 16 | **CAS Registry Number** | Chemistry data cites CAS RNs with/without hyphens and wrong check digits. Short `2–7 digits – 2 digits – 1 check` format with MOD-10 check is deterministic. | PARSER (hyphen normalization, MOD-10 check) | CAS Registry (CAS.org check-digit documentation) | "58 08 2" → "58-08-2" |
| 17 | **InChI / InChIKey** | Structures are shared as non-standard InChI, bare Keys, or prefixed strings. IUPAC InChI is the open standard; Key is a fixed 27-char SHA-256 hash — canonical by construction. Pairs with shipped ChemicalElement. | PARSER (validate `InChI=1S/` prefix and layer syntax; Key `AAAAAAAAAAAAAA-BBBBBBBBFV-P` shape) | IUPAC InChI (InChI Trust, `iupac.org/inchi`), Heller et al. J. Cheminformatics 2015 | "inchi=1s/c2h5no2/c3-1-2(4)5/h1,3h2,(h,4,5)" → "InChI=1S/C2H5NO2/c3-1-2(4)5/h1,3H2,(H,4,5)" |
| 18 | **ISMN / ISRC** | Music-edition and recording codes are the ISBN/ISSN siblings for audio: ISMN-13 (979-0 prefix, EAN-13 check) and ISRC (12-char `CC-XXX-YY-NNNNN`). Both have ISO standing and IFPI handbooks. | PARSER (ISMN: 979-0 handling + EAN-13 check; ISRC: uppercase + hyphen canonicalization) | ISO 10957:2021 (ISMN), ISO 3901:2001 + IFPI ISRC Handbook (ISRC) | "979-0-2600-0043-8" → "9790260000438"; "usrc17607839" → "US-RC1-76-07839" |
| 19 | **ISNI** | Public-identity IDs for creators/organizations; same 16-digit MOD 11-2 family as shipped ORCID (ISO 27729). Display varies spaced/hyphenated/compact/URI. | PARSER (strip spaces/hyphens/URI, MOD 11-2 check, spaced-quad canonical) | ISO 27729:2012 (ISNI), isni.org | "0000000121032683" → "0000 0001 2103 2683" |
| 20 | **ROR ID** | Affiliation strings ("MIT", "Max Planck") need org-identifier normalization; ROR is the open CC0 registry with URL-form IDs. Registry snapshot required. | LOOKUP_TABLE (registry snapshot) + PARSER (URL normalization to `https://ror.org/…`) | ROR Registry (ror.org, CC0 data dump/API) | "ror.org/04aj4c181" → "https://ror.org/04aj4c181" |
| 21 | **UN/LOCODE** | Port/location codes in logistics data vary in case/spacing ("usnyc", "US NYC"). 5-char `CCLLL` over ~100k entries; UNECE publishes CSV/TXT. | LOOKUP_TABLE (CC + LLL snapshot; uppercase compact canonical) | UNECE UN/LOCODE 2025-1, ISO 3166-1 (country) / ISO 3166-2 (subdivision) | "usnyc" → "USNYC" |
| 22 | **IMEI** | Device IDs appear hyphen/space grouped; 15 digits with Luhn check per 3GPP. Natural sibling to MAC/IP/Phone. | PARSER (strip separators, length + Luhn check) | 3GPP TS 22.016 (GSM 02.16), GSMA Device Check guidance | "49-015420-323751-8" → "490154203237518" |
| 23 | **ABA routing transit number** | US bank routing numbers appear dashed/spaced; 9 digits with `3-7-1` checksum. Pairs with shipped IBAN/BIC for US coverage. | PARSER (strip separators, 9-digit checksum) | ABA Key to Routing Numbers (routingnumber.aba.com) | "0210-0002-1" → "021000021" |
| 24 | **CVE identifier** | Vulnerability IDs vary in case and year handling ("cve-2024-1234"). CNA Rules fix `CVE-YYYY-NNNNN+` syntax. | PARSER (uppercase `CVE-`, 4-digit year, 4+ digit sequence, no zero-pad invention) | CVE CNA Operational Rules v4.2.0 (cve.org), MITRE CVE / NVD | "cve-2024-1234" → "CVE-2024-1234" |
| 25 | **ISO 15924 script code** | Script subtags appear as names or codes ("latin", "HANS", "Latn"). ISO 15924 (Unicode RA) fixes alpha-4 Titlecase + numeric. Extends shipped Language script handling. | LOOKUP_TABLE (name/code/numeric → Titlecase alpha-4) | ISO 15924:2022, Unicode ISO 15924 RA code lists | "latin" → "Latn" |
| 26 | **URN** | Persistent names (`urn:isbn:…`, `urn:uuid:…`, `urn:ietf:…`) vary in scheme case and namespace casing. RFC 8141 fixes `urn:` + lowercase NID syntax. DOI/ISBN/ISSN/UUID carriers become URN namespaces. | PARSER (lowercase `urn:` + NID, preserve NSS case per namespace rule) | RFC 8141 (URN Syntax, obsoletes RFC 2141) | "URN:ISBN:0451450523" → "urn:isbn:0451450523" |
| 27 | **Open Location Code (Plus Codes)** | Drop-pin addresses without street data ("849VCW3F+G3"). Open spec, 20-char alphabet (no I/L/O), `+` separator, padding — fully deterministic. Complements shipped Coordinates. | PARSER (uppercase, alphabet guard, `+` position/padding validation) | OLC Specification (github.com/google/open-location-code, Apache 2.0; plus.codes) | "849vcw3f+g3" → "849VCW3F+G3" |
| 28 | **UCUM unit expressions** | Clinical/engineering data uses non-SI units shipped SIUnit rejects (`mg/dL`, `[in_i]`, `mm[Hg]`). UCUM (Regenstrief) is the open case-sensitive code system for these. Scope as SIUnit-extension, not replacement. | LOOKUP_TABLE (case-sensitive UCUM atoms + expression grammar) | UCUM (ucum.org, Regenstrief), ISO 1000 / ISO 2955 source units | "MG/DL" → "mg/dL" |

### 2C. Explicitly deferred (considered, not roadmapped)

| Domain | Reason |
|--------|--------|
| CUSIP / SEDOL / FIGI (securities family beyond ISIN) | Proprietary registries (CUSIP Global Services / LSE / Bloomberg). Paxman needs redistributable authority tables — deferred until an open snapshot exists. |
| EU VAT IDs | Country-dispatched checksums + VIES live-lookup dependence. Fails the no-network-inference invariant as a single capability; revisit as per-country parsers. |
| Generic Handle (`hdl:`, RFC 3650/3651/3652) | DOI already covers the `10.` Handle subset with provenance; a generic Handle capability adds registry dependence without new disambiguation value. |
| Geohash | Overlaps Plus Codes + Coordinates with a less stable spec home; prefer OLC (single open spec) if a geo-encoding capability is taken on. |
| JSON Canonicalization (RFC 8785 JCS) / JWT | Different layer (document canonicalization, crypto verification) — not an identifier/notation normalization fit. |
| Cron / RRULE (scheduling expressions) | Dialect split (Vixie cron vs Quartz vs RFC 5545 RRULE) with no single canonical target; revisit only with a pinned-dialect contract. |

---

## Priority Rationale

Capabilities are ordered by a combination of:

1. **Ambiguity frequency** — how often real-world input varies for the same canonical value
2. **Authoritative provenance strength** — stability and accessibility of the governing specification/registry
3. **Data surface area** — how commonly the domain appears in user-generated and machine-generated data
4. **Implementation simplicity** — whether the canonicalization rule is deterministic and well-defined

§2A keeps its inherited order. §2B is ordered by the same rationale: bibliographic/finance siblings of shipped capabilities first (GTIN → ABA), then geo/org/script extensions (UN/LOCODE → UCUM).

---

## Sources consulted (2026-09-22 websearch)

GS1 General Specifications + check-digit calculator (gs1.org); ISO 3779:2009 VIN content/structure (iso.org/obp); IUPAC InChI / InChI Trust (iupac.org, inchi-trust.org, Heller et al. 2015); ISO 10957:2021 ISMN + ISO 3901 ISRC + IFPI ISRC Handbook; ISNI/ISO 27729:2012 (isni.org); ROR Registry (ror.org, CC0); UNECE UN/LOCODE 2025-1 code list; 3GPP TS 22.016 IMEI/Luhn; CAS Registry check-digit docs (cas.org); ABA routing numbers (aba.com); CVE CNA Operational Rules v4.2.0 (cve.org); ISO 15924:2022 + Unicode RA; RFC 8141 URN; OLC/Plus Codes spec (github.com/google/open-location-code); UCUM (ucum.org).

---

## Notes

- All capabilities are listed as **guidance only** — implementation details (grammar count, rule count, contract parameters) are not specified and may change.
- Provenance publications are the primary authoritative sources; secondary references (CLDR, WHATWG, etc.) are listed where they provide the practical canonicalization rules.
- Some domains (e.g., Postal code, Color name) have regional or vendor-specific variations that may require capability-specific contract parameters (e.g., `country` for postal codes).
- The "grammar strategy" column uses Paxman's internal terminology: **REGEX** (pattern matching), **LOOKUP_TABLE** (table-driven validation), **PARSER** (value parsing and transformation).
- §1 is generated from code (`paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`, `paxman/capabilities/<Name>/rules/`); §2 is the planning surface. If they disagree, code wins.
