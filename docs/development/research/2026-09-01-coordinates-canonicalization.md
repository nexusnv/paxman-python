# Coordinates Canonicalization Research — paxman-python

**Date:** 2026-09-01
**Scope:** Primary-source survey of geographic coordinate representation standards (ISO 6709:2022, IETF RFC 5870 'geo' URI, IETF RFC 7946 GeoJSON, WGS 84 as default CRS), ecosystem canonicalization practices (geopy, validator.js, python-iso6709, python-stdnum negative precedent), and Paxman's grammar/rule/provenance architecture, to ground the design of a future `Coordinates` capability. No source code, tests, or configuration were modified.
**Evidence basis:** ISO 6709:2022 catalogue (`https://www.iso.org/standard/75147.html` — Ed. 3, Published 2022-09, ISO/TC 211), RFC 5870 (`https://www.rfc-editor.org/rfc/rfc5870.txt`), RFC 7946 (`https://www.rfc-editor.org/rfc/rfc7946.txt`), validator.js `isLatLong` source (`https://github.com/validatorjs/validator.js/blob/master/src/lib/isLatLong.js`), geopy `point.py` (`https://github.com/geopy/geopy/blob/master/geopy/point.py`), `seanson/python-iso6709` source + test corpus (`https://github.com/seanson/python-iso6709`), python-stdnum repo listing (`https://github.com/arthurdejong/python-stdnum` — **no coordinates module: negative precedent confirmed**), Wikipedia ISO 6709 Annex H transcription (`https://en.wikipedia.org/wiki/ISO_6709`, secondary but verbatim-quoting), Wikipedia Geographic coordinate conversion (`https://en.wikipedia.org/wiki/Geographic_coordinate_conversion`, secondary); shipped Paxman precedents `paxman/capabilities/MacAddress/`, `Money/`, `SIUnit/`, `IBAN/`, `ISSN/` plus `paxman/engine/orchestrator.py` and `paxman/core/domain.py`. Repo state: `dev @ d82bbdd` — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md, and the ISSN research precedent (`docs/development/research/2026-08-21-issn-canonicalization.md`), plus the IBAN/BIC precedents (`2026-08-22-iban-canonicalization.md`, `2026-08-23-bic-canonicalization.md`) and the newest executed instance (`2026-08-31-mac-address-canonicalization.md`).

---

## Executive Summary

Coordinates are a **strong fit** for a Paxman capability: they have a **single unambiguous canonical value** (a WGS 84 latitude/longitude pair), a **stable multi-publication standard set** (ISO 6709:2022 Ed. 3, Published 2022-09, ISO/TC 211; RFC 5870 'geo' URI, June 2010, Standards Track; RFC 7946 GeoJSON, August 2016, Standards Track) with **no registry in play** — the "authority" is a set of format specifications plus one fixed datum (WGS 84, EPSG 4326/4979) — and an extraordinarily **wide, well-attested human surface** (decimal pairs, DMS with ° ′ ″, hemisphere letters, zero-padded aviator style, Geo URIs, ISO 6709 compact strings, lon-first JSON pairs). The domain mirrors Paxman's value proposition for SIUnit and Money: the same physical quantity, many human spellings, one canonical value with provenance. **There is no checksum** — validity is structure plus numeric range (latitude −90…+90, longitude −180…+180), and every fetched source splits *syntactic* recognition from *range* validation (RFC 5870's ABNF admits `geo:94,0`; §9.1 bans it semantically), which is exactly Paxman's grammar-vs-rule split.

Key findings that shape the design:

1. **Canonical form is a lat-first signed decimal-degree pair** (`48.8577, 2.295`) in the WGS 84 datum. Lat-first is the human normative order in ISO 6709 ("Latitude comes before longitude", Annex H), RFC 5870, geopy, and validator.js; **GeoJSON is the single normative lon-first inversion** (RFC 7946 §3.1.1, Appendix A.1, §9 — which explicitly maps `geo:lat,lon` ⇔ `[lon, lat]`). Ordering is therefore a *presentation* concern, resolved in `format_value()`, not an ambiguity.
2. **One grammar vs N grammars:** a single `coordinates_recognition` grammar with alternation branches per written form. All forms share one semantics (`coordinates_recognition`), and cross-branch containment (e.g. a DMS string contained in a longer label-prefixed span) is exactly the containment dedup `_dedup_spans` already solves — longer wins per grammar. A split grammar set would manufacture spurious `AMBIGUOUS` between `48.8577, 2.295` (decimal) and `48°51′27.7″N, 2°17′42″E` (DMS) describing the same point.
3. **Validation is structure + range, two levels, both PARSER.** Level 1: per-form structural validity (digit-count tables for ISO 6709 truncation, DMS unit ranges minutes<60/seconds<60). Level 2: numeric range (lat ±90, lon ±180) per RFC 5870 §3.3/§9.1 and GeoJSON §4. There is **no Level 3**: no gazetteer or land/sea membership check is possible without world knowledge, which Paxman's determinism anti-patterns forbid — the explicit analogue of BIC §5.4's directory-scope decision, resolved the opposite way.
4. **Sign vs hemisphere letters are alternative encodings of one fact**, not distinct identities — `48.8577 N`, `+48.8577`, and `48°51′27.7″N` coalesce to the same canonical value (unlike BIC's XXX-head-office and ISBN-10→13, which are distinct values). Double-marked sign+hemisphere that contradicts (e.g. `-41.5 S`) is `INVALID`, not a competing value.
5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5: one file per publication — ISO 6709:2022 (structure + truncation + human-interface rules), RFC 5870 (geo URI validity), RFC 7946 (position ordering/range) — one `PUBLICATION` constant each, one Rule class per section. WGS 84 itself (NGA.STND.0012 / NGA TR8350.2) remains an **unfetched primary source** and is recorded as an open decision (§13).

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and recommendations are in §13.

---
## 1. Target User

| Persona | Why they need Coordinates canonicalization | Typical context |
|---------|--------------------------------------------|-----------------|
| Data engineer normalizing location columns | Scraped/pasted coordinates arrive as DMS, hemisphere-lettered, zero-padded, or Geo URIs; downstream storage wants one decimal-degree pair | Cleaning a addresses/places dataset; deduplicating venue records |
| Author of a geo API consumer | Input may be `geo:` URIs (QR codes, HTML links), GeoJSON pairs, or human prose; wants a single canonical value with a citation for why it parsed | Accepting a "where" field from mixed upstream systems |
| Journalist / researcher quoting a location | Source documents use aviation/military zero-padded DMS (`05° 09' 01'' S 008° 03' 02'' E`); wants the decimal equivalent with provenance | Verifying an event location across sources |
| QA of geocoding pipelines | Needs deterministic round-tripping: same input string → same canonical pair, and exact equality classes (`geo:22.300;-118.44` ≡ `geo:22.3;-118.4400`, RFC 5870 §6.5) | Snapshot tests, dedup keys |
| Library user matching Paxman's identifier ergonomics | Already uses ISBN/IBAN/ISSN; wants the same MISSING/INVALID/SUCCESS contract for the "coordinate mention" in a text slice | Mixed-notation ingestion pipelines |

**User-visible contract:** The caller supplies raw human text (a slice expected to contain at most one coordinate mention) and a contract; Paxman returns one canonical WGS 84 coordinate pair (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors IBAN/MacAddress ergonomics, but the canonical default is a **lat-first signed decimal-degree pair** with the altitude preserved when the input carried one.

---
## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory — every distinct written form (MANDATORY)

Coordinates are unusual among Paxman capabilities: the human surface is not one identifier with separators, but a **family of notations** (decimal degrees DD, degrees-and-decimal-minutes DDM, degrees-minutes-seconds DMS) × **sign encodings** (ASCII sign, hemisphere letters, both) × **pair separators** (comma, semicolon, whitespace, slash) × **carriers** (bare pair, Geo URI, ISO 6709 string, JSON position, label-prefixed prose) × **component order** (lat-first everywhere human; lon-first in GeoJSON). The inventory below is built from the Phase 1C evidence: the geopy `POINT_PATTERN` regex (the single densest attestation — its char classes enumerate the symbols humans actually type), validator.js `isLatLong`, ISO 6709 Annex H examples, RFC 5870/7946 examples, python-iso6709's test corpus, and Wikipedia's conversion article.

| # | Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|---|------|---------|----------------|------------|--------------------|-------------------|
| 1 | Bare signed decimal pair, comma | `48.8566,2.3522` | validator.js `lat`/`long` regexes; geopy `41.5,-81.0`; RFC 5870 §2 comma-delimited pair | canonical de-facto | **RECOGNIZE** | decimal branch, `SEP` = comma |
| 2 | Parenthesized decimal pair | `(41.5, -81.0)` | validator.js `^\(?…` / `…\)?$` | common | **RECOGNIZE** | optional `(` `)` wrapping the pair |
| 3 | Signed decimal, space separator, `+` commonly omitted | `+40.446 -79.982` | Wikipedia GeoCoordConv | common | **RECOGNIZE** | decimal branch, `SEP` = whitespace |
| 4 | Semicolon-separated decimal | `41.5;-81.0` | geopy `from_string` docstring | common | **RECOGNIZE** | `SEP` includes `;` |
| 5 | Slash-separated decimal | `41.5/-81.0` | geopy `SEP = r'\s*[,;/\s]\s*'`; geopy `UT: N 39°20' 0'' / W 74°35' 0''` | occasional | **RECOGNIZE** | `SEP` includes `/` |
| 6 | Hemisphere-suffixed decimal | `41.5 N -81.0 W` | geopy `(?P<latitude_direction_back>[NS])?`; validator.js DMS `[NSns]?` | common | **RECOGNIZE** | optional trailing `[NS]`/`[EW]` per component |
| 7 | Hemisphere-prefixed decimal | `N 48.8566, E 2.3522` | geopy `(?P<latitude_direction_front>[NS])?` | common | **RECOGNIZE** | optional leading `[NS]`/`[EW]` per component |
| 8 | Sign + hemisphere double-marked (consistent) | `-41.5 S, 81.0 E, 2.5km` | geopy docstring verbatim | occasional | **RECOGNIZE** (rule enforces consistency) | both sign and letter captured; rule checks agreement |
| 9 | DMS with unicode symbols | `40° 26′ 46″ N 79° 58′ 56″ W` | Wikipedia GeoCoordConv; geopy `format_unicode()`; ISO 6709 Annex D ("symbols ° (U+00B0), ′ (U+2032), ″ (U+2033)") | official display | **RECOGNIZE** | DMS branch with `°`/`′`/`″` char classes |
| 10 | DMS with ASCII quotes | `23 26' 22" N 23 27' 30" E` | geopy docstring; validator.js `\D+` separators | common | **RECOGNIZE** | `'` and `''`→`″` (geopy pre-substitutes `re.sub(r"''", r'"', s)`) |
| 11 | DMS with letter units | `23 26m 22s N 23 27m 30s E` | geopy char classes `[%(PRIME)s'm]`, `[%(DOUBLE_PRIME)s"s]` | occasional | **RECOGNIZE** | unit class includes `m`/`s` letters |
| 12 | Degrees-and-decimal-minutes (DDM) | `40° 26.767′ N 79° 58.933′ W` | Wikipedia GeoCoordConv (3 spellings incl. `40° 26'767 N`) | common | **RECOGNIZE** | DMS branch with optional seconds; fraction attaches to minutes |
| 13 | Zero-padded fixed-width DMS | `05° 09' 01'' S 008° 03' 02'' E` | Wikipedia GeoCoordConv ("consistent use of three digits for degrees of longitude below 100°") | occasional (aviation/nautical) | **RECOGNIZE** | DMS digit runs 1–3 (lat) / 1–3 (lon), no fixed-width requirement |
| 14 | Degenerate DMS, spaces omitted | `10°59'26''123N000°00'04''902W` | Wikipedia GeoCoordConv verbatim | rare | **RECOGNIZE** | separator-tolerant DMS symbols (no required spaces) |
| 15 | Label-prefixed prose | `UT: N 39°20' 0'' / W 74°35' 0''` | geopy leading `.*?` (any prefix tolerated); `LAT:`/`LONG:` conventions | common | **RECOGNIZE** | fused label `[\s:-]+` on the pair prefix, span includes label |
| 16 | Geo URI 2-D | `geo:48.8566,2.3522` | RFC 5870 §1, §6 examples | common (web/QR) | **RECOGNIZE** | `geo:` scheme branch, RFC 5870 ABNF subset |
| 17 | Geo URI 3-D with altitude | `geo:48.2010,16.3695,183` | RFC 5870 §6.1 | common | **RECOGNIZE** | optional third `num` component → altitude |
| 18 | Geo URI with `;crs=` / `;u=` params | `geo:48.198634,16.371648;crs=wgs84;u=40` | RFC 5870 §6.2, §6.4 (`crs=WGS84` case-insensitive) | occasional | **RECOGNIZE** | optional `;crs=`/`;u=` parameter tail, captured and ignored for v1 validation |
| 19 | ISO 6709 signed fixed-width decimal + solidus | `+48.52+002.20/`, `+40.75-074.00/` | ISO 6709 Annex H examples (via Wikipedia transcription) | official interchange | **RECOGNIZE** | ISO branch: `±DD.D±DDD.D/`, fixed 2/3 integer digits |
| 20 | ISO 6709 truncated degrees-only | `+00-025/`, `+46+002/` | ISO 6709 Annex H examples | official interchange | **RECOGNIZE** | ISO branch: 2/3-digit degrees, no fraction |
| 21 | ISO 6709 truncated minutes form | `+1234.7-09854.1/` | python-iso6709 test corpus verbatim | official interchange | **RECOGNIZE** | ISO branch: `±DDMM.M±DDDMM.M/` |
| 22 | ISO 6709 full compact DMS + integer altitude | `+352139+1384339+3776/` | python-iso6709 test corpus verbatim | official interchange | **RECOGNIZE** | ISO branch: `±DDMMSS±DDDMMSS+alt/` |
| 23 | ISO 6709 with CRS suffix | `+27.5916+086.5640+8850CRSWGS_84/` | ISO 6709 Annex H example | official interchange | **RECOGNIZE** (capture `CRS…` tail, require `WGS_84` family in rule) | ISO branch optional `CRS<label>` before trailing `/` |
| 24 | GeoJSON lon-first JSON pair | `[2.295, 48.8577]` | RFC 7946 §3.1.1 ("first two elements are longitude and latitude … precisely in that order"), Appendix A.1, §9 mapping | common (API payloads) | **RECOGNIZE** (bracketed, lon-first order flipped on capture) | bracketed branch; notation swaps to lat-first; `coord_shape="geojson"` records the flip |
| 25 | European comma-decimal pair | `48,8566 2,3522` | validator.js structurally rejects (comma is the pair split; `48` / `8566` fail the component regexes) | regional, unattested in fetched validators | **DEFER** | would require Money-style `classify_amount_shape` disambiguation; community `extra_grammars` candidate |
| 26 | Unicode minus (U+2212) | `−41.5, 81.0` | **None of the fetched parsers accept U+2212** (geopy class is ASCII `[+-]`; ISO 6709 Annex D uses U+2212 for *display* only) | rare | **DEFER** | trivial Pre-stage strip candidate once display-vs-input asymmetry is settled |
| 27 | Non-latlon tile/hash systems (MGRS `31U DQ 48251 11932`, Plus Codes `9G8F+6X Paris`, geohash `u09tv`) | — | Not in any fetched lat/lon spec; separate identifier domains with their own specs | adjacent domain | **DEFER** (each is its own future capability) | distinct charset/shape; a lat/lon grammar cannot recognize them without lexicon machinery |
| 28 | Truncated/homoglyph/OCR mangled | `48.8566°` (single component), `l48.8566,2.3522` (`l` for `1`) | — | invalid input | **REJECT** | single component ≠ pair → MISSING; homoglyph fails charset → MISSING |

A v1 that does NOT recognize a commonly attested form must state that explicitly here AND raise it as an Open Decision (§13). The deliberate scope cuts in this inventory are: European comma-decimal (row 25), Unicode minus (row 26), and non-latlon tile systems (row 27) — all DEFER; no common RECOGNIZE-form is silently dropped.

### 2.2 Wild variants — adversarial mutations of each inventoried form

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical compact decimal pair | `48.8577,2.295` | Master form; canonical output derives from it |
| 2 | Lowercase / mixed case hemisphere | `48.8577n, 2.295e`, `N 48.8577` vs `n 48.8577` | case-insensitive letters; validator.js uses `/i`; `.upper()` fold |
| 3 | Grouped / spaced DMS | `40° 26′ 46″ N` vs `40°26′46″N` | ISO 6709 Annex D says "without spaces"; wild corpora include spaces — grammar tolerates `\s*` |
| 4 | Label with colon/space/hyphen | `Lat: 48.8577 Lon: 2.295`, `UT: N 39°20' 0''` | fused label `[\s:-]+`, span includes label; note per-component labels (`Lat:`/`Lon:`) vs pair label (`UT:`) |
| 5 | Irregular whitespace | `48.8577   ,  2.295`, tab-separated | `\s*` around SEP; geopy `SEP = r'\s*[,;/\s]\s*'` |
| 6 | All four pair separators | `48.8577,2.295` · `48.8577;2.295` · `48.8577 2.295` · `48.8577/2.295` | one `SEP` class `[,;/\s]` — attested by geopy verbatim |
| 7 | Parenthesized pair | `(41.5, -81.0)` | validator.js requires matched parens (`(lat,` without `)` fails) — mirror that pairing rule |
| 8 | Hemisphere front vs back | `N 48.8577 E 2.295` vs `48.8577 N, 2.295 E` | both positions optional and independent (geopy) |
| 9 | Double-marked sign+hemisphere | `-41.5 S, 81.0 E` (consistent) vs `-41.5 N` (contradictory) | consistent → SUCCESS; contradictory → INVALID (rule-level, geopy negates on S/W) |
| 10 | With trailing annotation | `48.8577, 2.295 (Paris)` | lookaround guard must not swallow parenthetical; annotation outside span |
| 11 | Multiple per line | `48.8577,2.295 and 40.7128,-74.0060` | 2+ matches → MultipleMentionsError under `single_value` |
| 12 | Quoted / bracketed | `"48.8577, 2.295"`, `[48.8577, 2.295]` vs GeoJSON `[2.295, 48.8577]` | inside punctuation succeeds; bracketed is the GeoJSON branch — **order disambiguates** |
| 13 | OCR / homoglyph | `4B.8577,2.295`, `48.8577，2.295` (fullwidth comma) | strict ASCII charset for v1; fullwidth comma → MISSING (no autocorrection) |
| 14 | Over-long / under-long | `48.8577123456789, 2.295` (>6 decimals) · `48.8, 2.2, 3.3, 4.4` (4 components) | precision cap is a rule concern (RFC 7946 §11.2 guidance); >3 components fails RFC 5870 ABNF → MISSING |
| 15 | Out-of-range but syntactically valid | `geo:94,0`, `91.0, 2.0`, `48.8577, 181.0` | grammar claims, rule rejects → **INVALID** (RFC 5870 §9.1 precedent) |
| 16 | DMS unit overflow | `40° 75′ 46″ N`, `40° 26′ 90″ N` | minutes/seconds ≥ 60 → INVALID; validator.js tolerates `60` — Paxman recommends strict (<60) |
| 17 | Zero-padded fixed width | `05° 09' 01'' S 008° 03' 02'' E` | leading zeros must not trigger word-glue rejection — guard must allow digit adjacency inside the token |
| 18 | ISO 6709 truncation matrix | `+40.20361` (DD.D) · `+4012.22` (DDMM.M) · `+401213.1` (DDMMSS.S) · `+00-025/` | fixed-width integer digit counts (2/4/6 lat, 3/5/7 lon) guarantee unit parsing; wrong widths → MISSING |
| 19 | Adjacent sibling numerics | `ISO 6709 +40-075/ and ISBN 978-0-306-40615-7` | digit-boundary guards; sibling capabilities have disjoint shapes |
| 20 | `-0` negative zero | `geo:-0.0,122.0` | RFC 5870: "The value of '-0' … is allowed and is identical to '0'" — normalize folds to `0` |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| validator.js `isLatLong` (decimal) | `const lat = /^\(?[+-]?(90(\.0+)?|[1-8]?\d(\.\d+)?)$/;` `const long = /^\s?[+-]?(180(\.0+)?|1[0-7]\d(\.\d+)?|\d{1,2}(\.\d+)?)\)?$/;` — range encoded syntactically; optional parens split across the comma |
| validator.js `isLatLong` (DMS, `checkDMS`) | `const latDMS = /^(([1-8]?\d)\D+([1-5]?\d|60)\D+([1-5]?\d|60)(\.\d+)?|90\D+0\D+0)\D+[NSns]?$/i;` — `\D+` accepts any non-digit separator (° ′ ″ spaces all pass); minutes/seconds `\|60` tolerated |
| geopy `POINT_PATTERN` (core) | `(?P<latitude_direction_front>[NS])?[ ]*(?P<latitude_degrees>[+-]?\d+(?:\.\d+)?)(?:[°D\*\u00B0\s][ ]*(?:(?P<latitude_arcminutes>\d+(?:\.\d+)?)[′'m][ ]*)?(?:(?P<latitude_arcseconds>\d+(?:\.\d+)?)[″"s][ ]*)?)?(?P<latitude_direction_back>[NS])?` with `SEP = r'\s*[,;/\s]\s*'` — the canonical human-surface grammar |
| geopy pre-normalization | `re.sub(r"''", r'"', string)` — double ASCII apostrophe normalized to `″` before matching |
| python-iso6709 | `(?P<lat_sign>\+|-)(?P<lat_degrees>[0,1]?\d{2})(?P<lat_minutes>\d{2}?)?(?P<lat_seconds>\d{2}?)?(?P<lat_fraction>\.\d+)?` — fractional part attaches to the last present unit (DD.D / DDMM.M / DDMMSS.S in one grammar) |
| RFC 5870 (geo ABNF) | `coordinates = coord-a "," coord-b [ "," coord-c ]` with `latitude = [ "-" ] 1*2DIGIT [ "." 1*DIGIT ]` — range-agnostic ABNF; §9.1 `<geo:94,0>` invalidity is a separate semantic rule |
| RFC 7946 (position) | "The first two elements are longitude and latitude … precisely in that order and using decimal numbers. Altitude or elevation MAY be included as an optional third element." |

**Normalization contract (new for Coordinates, modeled on Money's `classify_amount_shape` at `paxman/capabilities/Money/grammar/__init__.py`):**
```python
def _decimal_degrees(degrees: str, minutes: str | None, seconds: str | None,
                     hemisphere: str | None) -> "Decimal":
    """DDM/DMS → decimal degrees with exact Decimal arithmetic.

    Wikipedia GeoCoordConv: decimal degrees = degrees + minutes/60 +
    seconds/3600. Hemisphere S/W negates (geopy parse_degrees semantics).
    """
    value = Decimal(degrees)
    if minutes is not None:
        value += Decimal(minutes) / Decimal(60)
    if seconds is not None:
        value += Decimal(seconds) / Decimal(3600)
    if hemisphere in ("S", "W"):
        value = -value
    return value

def _normalize_pair(lat: Decimal, lon: Decimal) -> tuple[str, str]:
    """Quantize to 6 decimal places (RFC 7946 §11.2 guidance), strip
    trailing zeros, fold -0 to 0 (RFC 5870 §3.3)."""
    def _one(v: Decimal) -> str:
        q = v.quantize(Decimal("0.000001")).normalize()
        if q == 0:
            q = Decimal(0)
        return str(q)
    return _one(lat), _one(lon)
```

### 2.3 What input is NOT a Coordinates mention

- **Single component** — `48.8566` alone, `2.3522°` alone: a degree value without its pair. `MISSING` (the pair is the unit of identity; RFC 5870 and every validator require two components).
- **Pure integer runs** — `488566` or `20240901` (looks like a date): no separator, no sign pattern → `MISSING`; no grammar claims.
- **Non-latlon tile systems** — MGRS, Plus Codes, geohash, UTM: adjacent identifier domains, each with its own spec → `MISSING` for this capability, DEFER row 27.
- **Other countries of the numeric world** — currency amounts (`$48.86`), SI quantities (`48.86 kg`), ISBN/ISSN runs: disjoint shapes via charset and separator guards → their own capabilities' matches, not cross-capability ambiguity.
- **Percentages / scores in prose** (`48.86%`): `%` suffix exclusion in lookahead; without it, false positives on statistics sentences.

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004). Two distinct mentions → `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True`; identical values coalesce to `SUCCESS` (e.g. `48.8577,2.295 and 48°51′27.7″N, 2°17′42″E` — same point, two spellings — dedup to one candidate because notation-normalized values agree).

---
## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation — decimal pair plus structured decomposition

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CoordinatesNotation:
    """WGS 84 coordinate notation - decimal pair plus shape discriminator.

    ``latitude``/``longitude`` are canonical signed decimal-degree strings
    (minus sign only, no plus, no trailing zeros, -0 folded to 0), lat-first
    regardless of the input's component order. ``altitude`` is the third
    component in metres when the input carried one (RFC 5870 coord-c; ISO
    6709 ±alt), else None. ``coord_shape`` records the recognized input
    family ("dd" decimal degrees, "ddm" degrees decimal minutes, "dms"
    degrees-minutes-seconds, "iso6709", "geo_uri", "geojson"), mirroring
    MoneyNotation's amount_shape discriminator. ``compact`` is the default
    presentation form: "lat, lon" with ASCII comma+space.
    """

    latitude: str          # e.g. "48.8577"  (−90 ≤ value ≤ 90)
    longitude: str         # e.g. "2.295"    (−180 ≤ value ≤ 180)
    altitude: str | None   # e.g. "8850" metres, or None
    coord_shape: str       # "dd" | "ddm" | "dms" | "iso6709" | "geo_uri" | "geojson"
    compact: str           # e.g. "48.8577, 2.295"
```

**Considered alternative — single field `compact` only:** a lone `compact` pair would lose (1) the rule-routing key — the ISO 6709 truncation rules and the GeoJSON ordering rule must know which input family they are validating, exactly as MacAddressNotation's `shape` routes EUI-48 vs EUI-64 and MoneyNotation's `amount_shape` routes decimal conventions; (2) the ordering provenance — whether the input was lon-first (GeoJSON) is presentation-relevant for round-trip fidelity and must survive to `format_value`; (3) altitude — dropping it silently would be lossy for the `+27.5916+086.5640+8850CRSWGS_84/` surface. The decomposition is preferred.

**Invariants the grammar enforces (before rules):**
- `latitude`/`longitude` are sign-normalized decimal strings with `.` decimal point only (no comma decimals in v1)
- `altitude` is an unsigned-or-signed integer/decimal metre value or None
- `coord_shape` ∈ the six-value frozenset above
- `compact == latitude + ", " + longitude` (+ altitude when present)

### 3.2 Why not carry symbols, labels, or input order in the notation

Degree symbols, hemisphere letters, zero padding, `CRSWGS_84` suffixes, and `geo:`/`UT:` labels have **no lexical significance** for validity — they are alternative encodings of sign and carrier. They live in the span (`raw_text`), not the notation. The only carrier fact worth keeping is `coord_shape`, because rules need to know which publication's structural constraints apply (ISO 6709 digit-width rules vs RFC 5870 ABNF), and `format_value` needs the lon-first bit for GeoJSON round-trips.

### 3.3 Why `coord_shape` is not a shape discriminator literal

Free `str` validated against a module-level `_VALID_SHAPES` frozenset in `__post_init__` (MoneyNotation `_VALID_AMOUNT_SHAPES` precedent at `paxman/capabilities/Money/notation.py`) — not a `Literal` type, mirroring Country/SIUnit precedent, so community extensions can add shapes without forking the notation type.

---
## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice — Regex

Per HOW_TO_ADD_NEW_GRAMMAR.md, Coordinates have a distinctive, highly regular numeric-symbol shape (fixed alternation of numeric components with a small symbol alphabet), no open vocabulary, no lexicon growth — **Regex** is correct. There is no Country-style name surface ("Paris" is not a coordinate) and nothing for a LexiconStage.

### 4.2 Reference pattern (adapted from MacAddress/Money and geopy evidence)

MacAddress precedent (verbatim shape, `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py`): module-scope alternation strings, `(?ai:)` guard, fused optional label, `BoundaryGuard` factory, `PipelineGrammar` with `pre` + `regex`. Proposed Coordinates pattern (single grammar, staged pipeline):

```python
import re

from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Component sub-patterns. DEC = decimal number, no sign (sign captured
# separately so hemisphere letters and signs compose).
_DEC = r"\d{1,3}(?:\.\d{1,7})?"
_SIGNS = r"(?P<sign>[-+])?"
_HEMI = r"(?P<hemi_front>[NSEWnsew])?[\s:]?"
_UNITS = (r"(?:\s*[°D\*]?\s*(?P<minutes>\d{1,2}(?:\.\d+)?)\s*[′'m]?"
          r"(?:\s*(?P<seconds>\d{1,2}(?:\.\d+)?)\s*[″\"s])?)?")

# SEP class is geopy's, verbatim evidence: comma, semicolon, slash, whitespace.
_SEP = r"[\s,;/]+"

# ISO 6709 branch: signed fixed-width components, optional CRS, trailing /.
_ISO_BODY = (r"(?P<iso>[+-]\d{2,7}(?:\.\d+)?[+-]\d{2,8}(?:\.\d+)?"
             r"(?:[+-]\d+)?(?:CRS[A-Za-z0-9_]+)?/)")

# Geo URI branch: RFC 5870 geo-scheme ":" geo-path.
_GEO_BODY = (r"(?P<geo>geo:[+-]?\d{1,3}(?:\.\d+)?,[+-]?\d{1,3}(?:\.\d+)?"
             r"(?:,[+-]?\d+(?:\.\d+)?)?(?:;crs=[A-Za-z0-9\-]+)?(?:;u=\d+(?:\.\d+)?)?)")

# GeoJSON bracketed lon-first pair (RFC 7946 §3.1.1).
_JSON_BODY = r"(?P<geojson>\[\s*[+-]?\d{1,3}(?:\.\d+)?\s*,\s*[+-]?\d{1,3}(?:\.\d+)?(?:\s*,\s*[+-]?\d+(?:\.\d+)?)?\s*\])"

# Bare pair branch: two components, hemisphere letters front/back, any SEP.
_PAIR_BODY = (rf"(?P<pair>{_HEMI}{_SIGNS}{_DEC}{_UNITS}\s*[NSEWnsew]?\s*"
              rf"{_SEP}{_HEMI}{_SIGNS}{_DEC}{_UNITS}\s*[NSEWnsew]?)")

_BODY_ALTS = f"{_GEO_BODY}|{_ISO_BODY}|{_JSON_BODY}|(?:{_PAIR_BODY})"
_COORDS_BODY = rf"(?ai:(?:(?:COORDS?|LAT(\/LON)?)[\s:-]+)?(?P<core>{_BODY_ALTS}))"

# NOTE: BoundaryGuard.word_only() is insufficient here — a coordinate may be
# legally glued to digits on the outside only in the ISO branch's leading
# sign; the practical v1 guard is word_only on the open end and a
# trailing-annotation-safe lookahead (no greedy parenthetical swallow).
_GUARD = BoundaryGuard.word_only()
_COORDS_PATTERN = _GUARD.lookbehind + _COORDS_BODY + _GUARD.lookahead


def _notation(match: re.Match[str]) -> CoordinatesNotation:
    """Branch-dispatch builder: parse groupdict, convert DMS/DDM to Decimal
    degrees per §2.2 normalization contract, detect lon-first GeoJSON order,
    emit frozen notation."""
    ...


class CoordinatesRecognitionGrammar(PipelineGrammar[CoordinatesNotation]):
    name = "coordinates_recognition"
    semantics = "coordinates_recognition"
    single_value = True
    pre = StandardPre[CoordinatesNotation](empty_guard=True)
    regex = RegexStage[CoordinatesNotation](
        pattern=_COORDS_PATTERN, notation_fn=_notation
    )
```

*Notes on fidelity vs MacAddress/ISSN precedent:* module-scope strings; `(?ai:...)` ASCII+casing guard; branch ordering geo → iso → geojson → pair is irrelevant to correctness because the shapes are disjoint, but the engine's longer-wins `_dedup_spans` still protects label-prefixed pair spans from inner bare-pair submatches. **Form-coverage traceability:** rows 1–8, 12–15 map to `_PAIR_BODY` (SEP class, hemisphere front/back, sign, DMS units); rows 16–18 to `_GEO_BODY`; rows 19–23 to `_ISO_BODY`; row 24 to `_JSON_BODY`; row 25 (comma-decimal) and 26 (U+2212) are DEFER with named future mechanisms (Money-style shape classifier; Pre-stage strip); row 27 DEFER as separate capabilities; row 28 REJECT via charset/structure.

**One grammar vs N:** (Recommended) single grammar, alternation branches — avoids cross-grammar spurious `AMBIGUOUS` between spellings of the same point. Alternative: `coordinates_decimal` + `coordinates_dms` + `coordinates_carrier` grammars with coalesced semantics; deferred to community extension if a capability-specific contract field ever needs to gate one family.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)
- Grammar emits span-bearing RecognitionMatch, half-open [start,end), raw_text == text[start:end] (label included for row 15)
- RegexStage loops re.finditer, builds RecognitionMatch; Stages must not mutate text
- Engine owns within-grammar containment dedup (longer wins) and total recognition ordering
- Candidate dedup (value, recognition_rule, validation_rule) after validation — `48.8577,2.295` and its DMS spelling coalesce because normalize() agrees

### 4.4 Guard boundaries against sibling grammars

| Grammar | Chars | Start | End guard |
|---------|-------|-------|-----------|
| Coordinates (pair branch) | `[0-9.+-NSEW°′″'"s]` | `(?<!\w)` + no preceding digit/sign glue | `(?!\w)` + no trailing digit/% glue |
| Coordinates (geo branch) | `geo:…` | scheme_char-style `(?<![A-Za-z0-9+.\-])` (URL precedent) | `(?!\w)` |
| Coordinates (ISO branch) | `[+-]…/` | `(?<!\d)(?<!\d[+\-])` (ISBN10_lead-style) | trailing `/` anchors |
| Money | `$48.86`, `48,86 €` | `word_sign()` | disjoint: currency symbol/word required |
| SIUnit | `48.86 kg` | `degree_word_sign()` | disjoint: unit token required |
| Date | `2024-09-01` | digit guards | disjoint: 4-2-2 shape, no `NSEW`/degree symbols |

Risk note: `48.8577 2.295` (whitespace-only SEP) is genuinely close to two bare decimals; the pair branch's requirement of two components joined by exactly one SEP run, with hemisphere/degree-symbol affinity, is what keeps sibling false positives at bay. The `phone_national()` multi-lookbehind pattern (`paxman/core/grammar/boundary.py`) is the precedent if a custom `coord_midrun()` guard becomes necessary.

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)
- semantics = `"coordinates_recognition"` identity id; coalesce only if a second grammar (e.g. a comma-decimal regional variant) is added
- `extra_grammars` seam is the DEFER landing spot for rows 25–27

### 4.6 `single_value` — one mention per call vs batch processing
Recommendation: `single_value=True` (shipped precedent, MacAddress/IBAN); segmentation path for batches; an `extra_grammars` free-text variant with `False` if a "find all coordinates in a document" need emerges.

---
## 5. Provenance — the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec & lineage

| Attribute | Finding |
|-----------|---------|
| Governing publishers | ISO (ISO 6709), IETF (RFC 5870, RFC 7946) |
| Registration Authority | None — coordinates are a format+datum domain, not a registry domain (proved negative: no RA role exists in any fetched spec) |
| Spec names | ISO 6709 "Standard representation of geographic point location by coordinates"; RFC 5870 "A Uniform Resource Identifier for Geographic Locations ('geo' URI)"; RFC 7946 "The GeoJSON Format" |
| Current editions | ISO 6709:2022 (Ed. 3); RFC 5870 (June 2010); RFC 7946 (August 2016) |
| Datum / CRS | WGS 84 — RFC 5870 §3.4.1 (default `crs=wgs84`), §2 (EPSG 4326 2-D / 4979 3-D); RFC 7946 §4 (`urn:ogc:def:crs:OGC::CRS84`) |
| Check character system | **None — proved negative.** No checksum exists in any fetched source; validity is structure + numeric range (lat −90…+90, lon −180…+180, RFC 5870 §3.3/§9.1) |
| Related specs | ISO 19111 (CRS definitions, referenced by ISO 6709 Annex H style 3); NGA WGS 84 standards (NGA.STND.0012, TR8350.2 — **unfetched**, see §13/§16) |

**Structure (ISO 6709 Annex H, via Wikipedia transcription, verbatim):** "A string expression of a point consists of latitude, longitude, height or depth, CRS identifier, and trailing solidus (`/`) without any delimiting character." "Latitude comes before longitude / North latitude is positive / East longitude is positive." Fixed-width integer digit counts signal units: lat `±DD.D` / `±DDMM.M` / `±DDMMSS.S`; lon `±DDD.D` / `±DDDMM.M` / `±DDDMMSS.S`. Human-interface (Annex D): "Degree, minutes and seconds should be followed by the symbols ° (U+00B0), ′ (U+2032), and ″ (U+2033)… North and south latitudes should be indicated by N and S following immediately after the digits."

**Lineage table:**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| ISO 6709:1983 (Ed. 1) | 1983 | withdrawn | Developed by ISO/IEC JTC 1/SC 32 (per Wikipedia lineage) |
| ISO 6709:2008 (Ed. 2) + Cor 1:2009 | 2008-07 | withdrawn (superseded) | Complete committee revision; Annex H string expression |
| ISO 6709:2022 (Ed. 3) | 2022-09 | **Published (current)** | Adds human-readable simpler string structure (abstract, verbatim); ISO/TC 211; ICS 35.240.70; 35 pp |
| RFC 5870 | 2010-06 | Published | Standards Track; obsoletes none |
| RFC 7946 | 2016-08 | Published | Standards Track; obsoletes GeoJSON 2008 spec (GJ2008), removes alternative-CRS clause |

**Citation Details Table (for Provenance):**

| authority | specification_name | version | reference_url | lifecycle | publication_year | kind |
|-----------|--------------------|---------|---------------|-----------|------------------|------|
| ISO | ISO 6709 | 2022 | https://www.iso.org/standard/75147.html | active | 2022 | specification |
| IETF | RFC 5870 | — | https://www.rfc-editor.org/rfc/rfc5870.txt | active | 2010 | specification |
| IETF | RFC 7946 | — | https://www.rfc-editor.org/rfc/rfc7946.txt | active | 2016 | specification |

### 5.2 Rule / publication map (one file per publication — HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level PUBLICATION (Provenance) | Rules in file | What it validates |
|-----------|----------------------------------------|----------------|-------------------|
| rules/iso_6709_ed2022.py | authority="ISO", specification_name="ISO 6709", kind="specification", reference_url="https://www.iso.org/standard/75147.html", version="2022", lifecycle="active", publication_year=2022 | `Section 6-coordinate-structure` (PARSER) | Sign conventions, unit digit-width (2/4/6 lat, 3/5/7 lon), fraction attachment to last unit, DMS unit ranges (min<60, sec<60), `coord_shape` in {dd, ddm, dms, iso6709} |
| rules/iso_6709_ed2022.py (same file, second class) | (same PUBLICATION) | `Section Annex-h-string-expression` (PARSER) | ISO 6709 carrier: trailing solidus, fixed-width integer parts, optional altitude, CRS-suffix family check (`CRSWGS_84` accepted; other CRS → INVALID) |
| rules/rfc_5870_ed2010.py | authority="IETF", specification_name="RFC 5870", kind="specification", reference_url="https://www.rfc-editor.org/rfc/rfc5870.txt", version="5870", lifecycle="active", publication_year=2010 | `Section 3.3-geo-uri-validity` (PARSER) | geo-URI branch: −90…+90 / −180…+180 ranges, `-0` identity, unknown-altitude MUST NOT be `0` sentinel, `crs=wgs84` (case-insensitive) or non-wgs84 CRS → INVALID for v1 |
| rules/rfc_7946_ed2016.py | authority="IETF", specification_name="RFC 7946", kind="specification", reference_url="https://www.rfc-editor.org/rfc/rfc7946.txt", version="7946", lifecycle="active", publication_year=2016 | `Section 3.1.1-position` (PARSER) | GeoJSON branch: lon-first order sanity (lon value within ±180 where components are within range of only one axis), ≤3 elements, ranges per §4 |

All rules route on `target_semantics = frozenset({"coordinates_recognition"})` and are scoped by `coord_shape` so each publication's structural law applies to its own input family; every rule's `normalize()` produces the same lat-first decimal pair so candidate dedup coalesces equivalent spellings.

### 5.3 What each rule does vs does not own
- `matches()` validates strictly (ranges, unit widths, consistency of sign+hemisphere), never raises; contract misconfigs caught in `contract.__post_init__`
- `normalize()` returns the default lat-first decimal pair, never reads `output_format` (CI purity scan), same value across all four rules for dedup
- RuleStrategy: **PARSER** for all four (numeric range and cross-field consistency checks are beyond regex; there is no LOOKUP_TABLE layer because there is no registry — proved negative in §5.1)

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)
IBAN/BIC faced "is country/registry validation gated?" — Coordinates face the inverted question: **is there any membership layer at all?** Answer: no. A gazetteer/land-sea/live-place check would import world knowledge and break determinism-by-snapshot (same input + contract + snapshot → same output) — the anti-pattern is explicit in AGENTS.md. Resolved: two always-active validation levels (structure, range), no gated third level. Non-WGS-84 CRS inputs (`CRSWGS_84` is fine; `CRSPS56` or `;crs=ed50` → INVALID) because canonicalizing a non-WGS-84 point to decimal degrees without a datum transform would be silently wrong — a lossy conversion Paxman must not perform.

### 5.5 Assignment / registration authority & Registry content
None. Coordinates are assigned by nature and convention: WGS 84 is maintained by NGA (the U.S. National Geospatial-Intelligence Agency, per TR8350.2 — **standard unfetched**, flagged in §13); EPSG codes 4326/4979 are assigned by the EPSG Geodetic Parameter Dataset (IOGP). No registration data, no directory, no cadence — the emptiness of this section is itself a finding.

---
## 6. Presentation Seam — Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class CoordinatesContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "decimal"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"iso6709", "geo_uri", "geojson_pair", "dms", "dm"}
    )
    capability_name: str = field(default="coordinates", init=False)
```

- DEFAULT_OUTPUT_FORMAT concrete string `"decimal"`; OFFERED excludes the default; resolved via `resolve_output_format` in `CapabilityContract.__post_init__`; `create_contract()` opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`) then capability-specific params (none needed in v1).
- Presentational-only invariant: no rule reads `output_format`; `format_value()` is the only presentation seam.

**Offered output formats — the interchange surface (user-requested focus):**

| `output_format` | `value` example (canonical point 48.8577 N, 2.295 E, alt none / 8850) | Meaning |
|-----------------|------------------------------------------------------------------------|---------|
| `"decimal"` (default) | `48.8577, 2.295` / `48.8577, 2.295, 8850` | Lat-first signed decimal degrees, ASCII comma+space, WGS 84 — the human/interchange default |
| `"iso6709"` | `+48.8577+002.2950/` / `+48.8577+002.2950+8850/` | ISO 6709:2022 Annex H string expression: signed fixed-width (2/3 integer digits), trailing solidus; CRS omitted per Annex H when WGS 84 is the agreed default |
| `"geo_uri"` | `geo:48.8577,2.295` / `geo:48.8577,2.295,8850` | RFC 5870 'geo' URI: lat-first comma coordinates, altitude as third component; no `;crs=` emitted (default WGS 84) |
| `"geojson_pair"` | `[2.295, 48.8577]` / `[2.295, 48.8577, 8850.0]` | RFC 7946 position array: **lon-first** JSON text — the single inversion, emitted for API payloads |
| `"dms"` | `48°51′28″N 2°17′42″E` | ISO 6709 Annex D human-interface sexagesimal: unicode ° ′ ″, hemisphere letter immediately after digits, no internal spaces |
| `"dm"` | `48°51.462′N 2°17.7′E` | Degrees-and-decimal-minutes (Wikipedia GeoCoordConv "degrees and decimal minutes" family); nautical display convention |

Formatting rules all deterministic: rounding to 6 decimal places (RFC 7946 §11.2 guidance) with round-half-even; hemisphere letters derived from sign (never both); altitude emitted only when present in the notation; `dms`/`dm` quantize from the exact decimal value, so `format_value(format_value(x)) == format_value(x)` round-trips on the decimal branch.

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from collections.abc import Sequence

from paxman.capabilities.Coordinates.contract import CoordinatesContract
from paxman.capabilities.Coordinates.grammar.coordinates_recognition import (
    CoordinatesRecognitionGrammar,
)
from paxman.capabilities.Coordinates.notation import CoordinatesNotation
from paxman.capabilities.Coordinates.rules.iso_6709_ed2022 import (
    Section6CoordinateStructure,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class CoordinatesCapability(Capability[CoordinatesNotation]):
    name = "coordinates"

    def get_grammars(self) -> list[Grammar[CoordinatesNotation]]:
        return [CoordinatesRecognitionGrammar()]

    def get_rules(self) -> list[Rule[CoordinatesNotation]]:
        return [
            Section6CoordinateStructure(),
            # + SectionAnnexHStringExpression, Section33GeoUriValidity,
            #   Section311Position
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> CoordinatesContract:
        return CoordinatesContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: CoordinatesNotation
    ) -> str:
        # dispatch on resolved output_format; default "decimal" is identity
        ...
```

Registration via `tools/new_capability.py` scaffolder (§10.1).

---
## 7. Validation — Structure, Range

### 7.1 Level 1 structure (per-form), Level 2 numeric range (always active); no Level 3

**Level 1 — structural validity (PARSER, per `coord_shape`):**
- Decimal family: each component is a decimal number; hemisphere letter (if any) ∈ {N,S,E,W}; sign+hemisphere consistency; DDM/DMS unit ranges — degrees lat ≤ 90, lon ≤ 180, minutes < 60, seconds < 60 (stricter than validator.js, which tolerates `60`; recommendation §13.6).
- ISO 6709 family: integer part digit-width table — lat 2 (DD.D), 4 (DDMM.M), 6 (DDMMSS.S); lon 3, 5, 7 — fraction attaches to the last present unit (python-iso6709 DMSDegree semantics, verbatim in §2.2 table); trailing solidus; altitude optional signed integer; CRS label, when present, must be `CRSWGS_84` (Annex H's own example) — any other CRS → INVALID (§5.4 rationale).
- geo URI family: RFC 5870 ABNF shape, ranges per §3.3 (`-0` identical to `0`), altitude MUST NOT be present-as-zero sentinel ("unknown altitude MUST NOT be represented by setting <altitude> to '0'" — a zero altitude is a real altitude, allowed only as explicit `0`), `;crs=` missing-or-`wgs84` (case-insensitive).
- GeoJSON family: exactly 2 or 3 elements (§3.1.1 "MUST be two or more… SHOULD NOT extend positions beyond three"), lon-first ordering, decimal numbers.

**Level 2 — numeric range (PARSER, all shapes):** latitude ∈ [−90, +90], longitude ∈ [−180, +180] — RFC 5870 §3.3 ("Latitudes range from -90 to 90 and longitudes range from -180 to 180"), §9.1 (`<geo:94,0>` invalid); RFC 7946 §4 decimal degrees on WGS 84. Note the deliberate asymmetry vs geopy, which *normalizes* longitude modulo 360 — Paxman rejects (`INVALID`) rather than silently relocating a point across the antimeridian; determinism over cleverness.

**Worked examples (Level 1+2):**
- `48°51′27.7″N 2°17′42″E` → 48 + 51/60 + 27.7/3600 = 48.85769…°, E ⇒ + → canonical `48.857692, 2.295`
- `+1234.7-09854.1/` → lat +12°34.7′ = 12.578333…, lon −98°54.1′ = −98.901667 → canonical `12.578333, -98.901667`
- `geo:48.2010,16.3695,183` → `48.201, 16.3695, alt 183` (trailing zero stripped)
- `05° 09' 01'' S 008° 03' 02'' E` → −(5 + 9/60 + 1/3600), +(8 + 3/60 + 2/3600) → `-5.150278, 8.050556`

### 7.2 What makes Coordinates "valid" vs "well-formed-but-unverifiable"
- **valid (generic)** — correct per-form structure + in-range values, always-active PARSER. This is the shipped v1 ceiling.
- **well-formed-but-unverifiable** — in-range WGS 84 point that may be mid-ocean or mid-desert; Paxman makes **no claim** about real-world place existence. There is no ISBN-style valid-vs-allocated split and no ISSN-style valid-vs-issued split because there is no registry; §5.4 proves the negative. Like ISBN "valid vs allocated", the distinction is documented but the second tier is deliberately absent.

---
## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase hemisphere | SUCCESS → compact | grammar folds case (`(?ai:)` guard; validator.js `/i` precedent) |
| 2 | Grouped/spaced DMS (`40° 26′ 46″ N`) | SUCCESS → compact | spacing presentation-only; Annex D spacing is a display rule, not validity |
| 3 | Label present (`UT: N 39°20' 0'' / W 74°35' 0''`) | SUCCESS, span includes label | fused label pattern (MacAddress `MAC` label precedent) |
| 4 | Zero-padded fixed width (`05° 09' 01'' S 008° 03' 02'' E`) | SUCCESS → compact | leading zeros semantically void; guard must tolerate inner digit adjacency |
| 5 | Hemisphere front vs back | Both SUCCESS, same compact | presentation-only; geopy accepts both positions |
| 6 | Sign+hemisphere contradictory (`-41.5 N`) | INVALID | rule-level consistency check; neither value is authoritative |
| 7 | Out-of-range (`geo:94,0`, `181.0`) | INVALID | RFC 5870 §9.1; grammar claims, rule rejects |
| 8 | DMS unit overflow (`40°75′`) | INVALID | minutes/seconds ≥ 60 structural failure |
| 9 | Over-precise decimal (12 decimals) | SUCCESS → compact (quantized 6dp) | RFC 7946 §11.2 precision guidance; rounding documented |
| 10 | Four components (`48.8, 2.2, 3.3, 4.4`) | MISSING | RFC 5870 ABNF max 3 components; no grammar branch claims |
| 11 | Unknown altitude as `0` in geo URI with intent marker absent | SUCCESS (altitude `0` is a real altitude) | RFC 5870: unknown altitude MUST be omitted, not zero — but `0` present is legal; only the *absence* convention is affected |
| 12 | Embedded in sentence (`at 48.8577, 2.295 today`) | SUCCESS with span | word-boundary guards; trailing annotation not swallowed |
| 13 | Two distinct points in one slice | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity; use segmentation |
| 14 | Same point, two spellings (`48.8577,2.295` and DMS) | SUCCESS, one candidate | dedup on normalize() agreement |
| 15 | Sibling confusion (`$48.86`, `48.86 kg`, `2024-09-01`) | MISSING | disjoint sibling shapes via symbol/unit guards |
| 16 | Leading/trailing glue (`ID48.8577,2.295`) | MISSING | `(?<!\w)` lookbehind rejects mid-token |
| 17 | Quoted/bracketed (`"48.8577, 2.295"`) | SUCCESS | inside punctuation; GeoJSON bracket branch only claims `[lon, lat]` shape |
| 18 | Non-WGS-84 CRS (`;crs=ed50`, `CRSPS56/`) | INVALID | §5.4: no silent datum transform; lossy canonicalization forbidden |

---
## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid decimal/DMS/ISO/geo/GeoJSON mention | SUCCESS → `48.8577, 2.295` | single canonical via structure+range rules |
| Alternative spacing/case/label/zero-padding | SUCCESS (same compact) | presentation-only dedup |
| Sign+hemisphere contradiction | INVALID | rule rejects; no authoritative reading |
| Out-of-range component (`geo:94,0`) | INVALID | RFC 5870 §9.1 semantic ban |
| DMS unit overflow | INVALID | structural failure in rule |
| No coordinate-shaped runs | MISSING | no grammar recognized |
| Single component only | MISSING | pair is the identity unit |
| Two distinct valid in one slice | AMBIGUOUS / MultipleMentionsError | single-slice ambiguity; use segmentation |
| Non-WGS-84 CRS / GeoJSON 4-element | INVALID | §5.4 no-lossy-transform / ABNF ceiling |
| Over-precision decimal | SUCCESS (quantized) | RFC 7946 §11.2; deterministic rounding |

---
## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (tools/new_capability.py — HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py Coordinates --name coordinates \
  --authority "ISO" --spec-name "ISO 6709" \
  --spec-url "https://www.iso.org/standard/75147.html" --publication-year 2022
```

Creates 13 files + one edit: `paxman/capabilities/Coordinates/{notation,contract,capability,grammar/*,rules/*}`, test stubs, `paxman/capabilities/__init__.py` wiring. TODO(scaffold) markers guide replacement.

> Note: the scaffolder's single `--spec-name` covers one provenance. After scaffolding, add the two IETF provenance files (`rules/rfc_5870_ed2010.py`, `rules/rfc_7946_ed2016.py`) manually — the ISO file pattern is the template.

### 10.2 Contract & grammar wiring
- `get_grammars()` returns `[CoordinatesRecognitionGrammar()]`; `active_grammars` omitted (base `None` runs all); grammar carries `name = "coordinates_recognition"` and non-empty `semantics`
- `get_rules()` returns the four Rule classes across three files; all route on `coordinates_recognition`

### 10.3 Cross-cutting invariants (fail review if violated)
- No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source
- No cross-capability imports (import only from `paxman.core`; import-linter enforced)
- No `output_format` token in any `paxman/capabilities/Coordinates/rules/` module (source-scan)
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` without slots contract
- Deterministic by construction: same input + contract + library snapshot → same output (no clock, no gazetteer, no datum transform tables)

---
## 11. Recommended File Layout (mirrors MacAddress/ISSN/IBAN)

```
paxman/capabilities/Coordinates/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── coordinates_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_6709_ed2022.py      # PUBLICATION ISO 6709:2022 — structure + Annex H
    ├── rfc_5870_ed2010.py      # PUBLICATION RFC 5870 — geo URI validity
    └── rfc_7946_ed2016.py      # PUBLICATION RFC 7946 — position ordering/range
```

No `rules/data/` and no `grammar/data/` — there is no registry, no vocabulary, no lookup table. The emptiness is structural: coordinates validate by computation (PARSER), never by membership (LOOKUP_TABLE).

---
## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- **Grammar tests:** one positive vector per §2.1 RECOGNIZE row (all 24) — decimal comma/semicolon/slash/space, parenthesized, hemisphere front/back, DMS unicode/ASCII/letter-unit, DDM three spellings, zero-padded, degenerate no-space DMS, label-prefixed, geo 2-D/3-D/params, ISO decimal/degrees-only/minutes/DMS/CRS forms, GeoJSON pair; multiple matches; empty input; span invariants (label included, half-open, raw_text equality); name/semantics assertions; boundary negatives (glued, single component, `%`-suffixed, fullwidth comma).
- **Rule tests:** per-rule valid/variant/invalid for each `coord_shape`; normalize exact canonical pair agreement across all four rules (dedup precondition); provenance attributes (authority/ISO vs IETF, kind "specification", lifecycle "active"); name/strategy conventions (`Section N-description`, PARSER); ISO digit-width matrix (2/4/6 and 3/5/7 accepted; 3-digit lat rejected); DMS overflow (`60′`) rejected; sign+hemisphere consistency; `-0` folding; CRS family; GeoJSON ordering and element-count ceiling.
- **Capability tests:** notation frozen/hashable/slots; wiring counts (1 grammar, 4 rules, 3 files); grammar/rule name conventions; `format_value` round-trips for all six output formats including altitude-present cases; `create_contract` factories.
- **Integration:** SUCCESS/MISSING/INVALID/AMBIGUOUS + MultipleMentionsError through `run_capability()`; `_clean_registry` autouse fixture; determinism/VersionStamp; span-bearing match; dedup of same-point-two-spellings.
- **Property tests (hypothesis):** generate lat ∈ [−90, 90], lon ∈ [−180, 180] at ≤6dp → canonicalize(compact) == compact (self-canonical); random DMS decompositions (deg + m/60 + s/3600) round-trip to the quantized decimal; every §6.1 format applied twice is idempotent; random strings → MISSING with high probability; hemisphere-letter and sign encodings of the same point dedup to one value.
- **Consistency test:** every shipped semantics covered by Rule.target_semantics; every RECOGNIZE row of §2.1 exercised end-to-end.
- **Presentation purity:** `output_format` source scan over `rules/`.
- **Real vectors:** the RFC 5870 §6 examples, ISO 6709 Annex H examples, python-iso6709 corpus rows, geopy docstring forms — all verbatim from fetched sources.

---
## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | DEFAULT_OUTPUT_FORMAT | `"decimal"` lat-first signed pair; offer iso6709/geo_uri/geojson_pair/dms/dm | decimal is the lowest-common-denominator interchange; every other format is derivable deterministically |
| 2 | Single grammar vs N | Single `coordinates_recognition`, branch alternation; defer split to community extension | avoids cross-grammar spurious AMBIGUOUS between spellings of one point; engine containment dedup already handles label-outer/bare-inner |
| 3 | Range validation locus | Always-active PARSER rule (Level 2), not regex-encoded | RFC 5870 precedent: ABNF is range-agnostic, invalidity is semantic (`<geo:94,0>`); matches Paxman grammar-claims/rule-rejects split |
| 4 | DMS unit strictness (minutes/seconds `60`) | Strict `< 60`, diverging from validator.js `|60` tolerance | 60′ is 1° — accepting it creates two spellings of one value; canonicalization must be injective per input family |
| 5 | Canonical numeric precision | Quantize to 6 decimal places, round-half-even, strip trailing zeros | RFC 7946 §11.2 ("6 decimal places … about 10 centimeters"); 1/60 and 1/3600 expansions are non-terminating — a cap is mandatory, and the RFC supplies the principled cap |
| 6 | Sign+hemisphere double-marking | Accept when consistent, INVALID when contradictory | attested by geopy (`-41.5 S, 81.0 E`); contradiction has no authoritative reading |
| 7 | Non-WGS-84 CRS inputs | INVALID (no silent datum transform) | converting ED50 → WGS 84 needs transform tables = world knowledge; lossy-by-default, violates determinism |
| 8 | Altitude handling | RECOGNIZE third component, preserve in notation, emit in formats that carry it | RFC 5870 coord-c, ISO 6709 height, GeoJSON third element all attest; dropping would be lossy for `+27.5916+086.5640+8850CRSWGS_84/` |
| 9 | Longitude wrap-around (geopy normalizes mod 360) | INVALID, do not normalize | silent relocation breaks determinism-over-cleverness; out-of-range is the caller's data bug |
| 10 | European comma-decimal forms (§2.1 row 25) | DEFER to `extra_grammars` | validator.js structural rejection is negative evidence; Money's `classify_amount_shape` is the future mechanism |
| 11 | Unicode minus U+2212 (row 26) | DEFER (Pre-stage strip candidate) | no fetched parser accepts it on input; ISO 6709 Annex D uses it for display only — display-vs-input asymmetry unresolved upstream |
| 12 | MGRS / Plus Codes / geohash (row 27) | DEFER — separate future capabilities | distinct specs, distinct charsets; not lat/lon grammar branches |
| 13 | WGS 84 primary source (NGA.STND.0012) | Unfetched in this report; do not cite NGA claims until fetched | skill hard rule: never claim a primary source not fetched; datum identity is safely citable via RFC 5870 §2 and RFC 7946 §4 instead |
| 14 | `single_value` for batch | True initially; segmentation for multi; optional free-text variant later | consistent with shipped precedent |
| 15 | Label span inclusion | Include label in raw_text span, notation compact label-free | mirrors MacAddress `MAC`-label fusion, ISSN/ISBN/IBAN precedents |

---
## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent coordinate-vs-coordinate ambiguity.** Fixed two/three-component structure eliminates the positional ambiguity Date exhibits; two distinct points in one slice is authorial choice, and segmentation is the intended path (§2.4). Same-point-different-spelling is not ambiguity — it is candidate dedup, by design.
- **Lat-first vs lon-first is not lexical ambiguity.** It is a carrier convention: every human form is lat-first (ISO 6709 Annex H, RFC 5870, geopy, validator.js); only the bracketed GeoJSON form is lon-first, and RFC 7946 §9 states the mapping explicitly. The bracket is the discriminator; `[2.295, 48.8577]` and `48.8577, 2.295` are the same point, and notation records `coord_shape="geojson"` for the round-trip.
- **Decimal vs DMS of the same point is not ambiguity** — it is one value with two encodings, coalescing under normalize() agreement (the ISBN hyphenated-vs-compact precedent generalized to unit conversion). The injectivity requirement is what motivates strict `<60` units (§13.4): without it, two DMS inputs map to one canonical value, which is fine, but one DMS input would map to two canonical values only if unit overflow were tolerated — hence strictness.
- **Coordinates vs sibling numeric capabilities is not cross-capability ambiguity.** `$48.86` (Money requires currency symbol/word), `48.86 kg` (SIUnit requires unit token), `2024-09-01` (Date shape) all fail the pair structure; conversely a bare decimal pair fails Money's currency affinity and SIUnit's unit requirement. Sibling grammars have disjoint affinity; the riskiest overlap is two bare decimals separated by whitespace, where the pair branch's two-component affinity plus hemisphere/degree-symbol evidence is the deciding factor (§4.4).
- **Staleness is not ambiguity.** WGS 84 is a fixed datum; there is no registry snapshot to go stale, no rolling edition to re-snapshot. Provenance versions are publication years, and `VersionStamp` records the library snapshot as with every capability. The only time-varying input class — over-precision decimals — is resolved deterministically by the quantization rule, not by context.

---
## 15. URL Reference (authoritative, fetched 2026-09-01)

| Claim | URL | Kind |
|-------|-----|------|
| ISO 6709:2022 (Ed. 3, current, Published, ISO/TC 211, ICS 35.240.70) | https://www.iso.org/standard/75147.html | primary |
| ISO 6709:2008 catalogue (lineage; HTTP 403 on fetch date) | https://www.iso.org/standard/39242.html | primary (metadata only, via lineage cross-reference) |
| ISO 6709 Annex H structure + examples (transcription) | https://en.wikipedia.org/wiki/ISO_6709 | secondary (verbatim quotes of Annex H/D) |
| RFC 5870 'geo' URI (ABNF §3.3, WGS-84 default §3.4.1, invalidity §9.1) | https://www.rfc-editor.org/rfc/rfc5870.txt | primary |
| RFC 7946 GeoJSON (position §3.1.1, CRS §4, precision §11.2, ordering Appendix A.1, §9) | https://www.rfc-editor.org/rfc/rfc7946.txt | primary |
| validator.js isLatLong (decimal + DMS regexes, parens pairing) | https://github.com/validatorjs/validator.js/blob/master/src/lib/isLatLong.js | primary |
| geopy Point parser (POINT_PATTERN, hemisphere positions, SEP class, altitude units) | https://github.com/geopy/geopy/blob/master/geopy/point.py | primary |
| python-iso6709 (parse regex + truncation test corpus) | https://github.com/seanson/python-iso6709 | primary (implementation) |
| python-stdnum — no coordinates module (negative precedent) | https://github.com/arthurdejong/python-stdnum | primary (negative evidence) |
| DMS/DDM/DD notation family, zero-padded convention | https://en.wikipedia.org/wiki/Geographic_coordinate_conversion | secondary |
| Coordinates absent from shipped capabilities | paxman/capabilities/__init__.py | primary (codebase) |
| Paxman scaffolder & conventions | HOW_TO_ADD_NEW_CAPABILITY.md, HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md | primary |
| Research precedents | docs/development/research/2026-08-21-issn-canonicalization.md, 2026-08-22-iban-canonicalization.md, 2026-08-23-bic-canonicalization.md, 2026-08-31-mac-address-canonicalization.md | primary |
| Shipped codebase precedent | paxman/capabilities/MacAddress/, Money/notation.py, SIUnit/notation.py, paxman/engine/orchestrator.py, paxman/core/domain.py, paxman/core/grammar/boundary.py | primary |
| Not fetched: NGA.STND.0012 / TR8350.2 (WGS 84), ISO 6709 OBP full text (JS SPA), GB basic code set | — | gap (declared, see §13.13) |

---
## 16. Evidence Completion — Resolved

This report's Coordinates-specific authoritative evidence has been fetched and cited (2026-09-01):
- [x] ISO catalogue entry: ISO 6709:2022 (Ed. 3, current, Published) superseding ISO 6709:2008 + Cor 1:2009, back to 1983 lineage; ISO/TC 211; ICS 35.240.70; abstract quoted verbatim
- [x] No RA / no registry: proved negative across all three fetched publications; §5.5 records the datum maintainers (NGA) with the standard itself declared unfetched
- [x] Structure: lat-first, sign conventions, fixed-width digit tables, DMS/DDM/DD families, trailing solidus, CRS suffix, altitude — Annex H/D verbatim
- [x] No checksum: proved negative with two independent sources (ISO 6709 structure is sign+range only; RFC 5870 validity rules are range-only)
- [x] CRS nuance: WGS 84 default attested by RFC 5870 §3.4.1/§2 (EPSG 4326/4979) and RFC 7946 §4 (OGC CRS84 URN); non-WGS-84 → INVALID decision written
- [x] Ecosystem regex consensus: validator.js decimal+DMS, geopy POINT_PATTERN, python-iso6709 truncation regex, RFC ABNFs — four independent implementations quoted verbatim
- [x] Recognition-surface inventory complete (§2.1): 28 written forms listed with per-form evidence and RECOGNIZE/DEFER/REJECT disposition — no silently unhandled form
- [x] Wild input shapes validated (§2.2): 20 categories against spec + validators + corpora
- [x] Label scope decision (fused, span-inclusive)
- [x] Order inversion decision (GeoJSON lon-first as carrier convention)
- [x] CRS family decision (WGS_84 only, else INVALID)
- [x] Membership-layer scope decision (none; gazetteer rejected as world knowledge)
- [x] Directory liveness scope decision (N/A — no directory exists)

File Layout / Rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix — What the Shipped MacAddress, Money, SIUnit, IBAN and BIC Capabilities Teach Coordinates (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (not speculative) and anchors the proposal to what Paxman already ships.

The four architectural lessons for Coordinates:

1. **Grammar strips, rule validates, capability formats.** MacAddress's grammar folds case and captures the compact core while `Section82EUIStructure` checks structure and `format_value` renders six shapes (`paxman/capabilities/MacAddress/capability.py`). Coordinates' grammar folds case/spacing/symbols into the decimal pair while rules check digit-widths and ranges and `format_value` renders the six §6.1 formats.
2. **One file per provenance, one class per section.** `paxman/capabilities/MacAddress/rules/ieee_802_ed2024.py` — module-level `PUBLICATION`, `Section 8.2-eui-structure`. Coordinates maps this to three publications (ISO 6709, RFC 5870, RFC 7946), five rule classes.
3. **No `output_format` in rules, ever.** Every shipped rule's `normalize()` returns the default-form value (MacAddress returns colon form); CI source-scan enforces the token ban. Coordinates' `normalize()` returns the lat-first decimal pair for all rules — which is precisely what makes same-point-different-spelling dedup work.
4. **Multi-part numeric notations decompose with shape discriminators.** `MoneyNotation.currency_part/amount_part` + `amount_shape` (`paxman/capabilities/Money/notation.py`) and `classify_amount_shape`'s rfind-based decimal-convention classifier are the direct precedent for `CoordinatesNotation.latitude/longitude/altitude` + `coord_shape` and the DMS→DD conversion; `MacAddressNotation.shape` is the length-discriminator precedent for the iso/geo/json carrier shapes.

---

*Report saved to `docs/development/research/` (this directory) per MILESTONE guidance for Coordinates. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md` and `docs/development/research/2026-08-23-bic-canonicalization.md` and the newest executed precedent `2026-08-31-mac-address-canonicalization.md`. For implementation, start from `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
