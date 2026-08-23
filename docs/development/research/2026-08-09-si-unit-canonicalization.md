# SI Unit Canonicalization Research — Paxman SI Unit Capability

| | |
|---|---|
| **Date** | 2026-08-09 |
| **Scope** | Research and design for the SI unit capability (MILESTONE.md row 23: "SI unit — LOOKUP_TABLE (unit name/symbol/prefix lookup, case-sensitive canonical symbols); provenance BIPM SI Brochure (9th edition, 2019), IEC 80000-1, ISO 80000"). Covers: the SI unit universe as a data surface, the case-sensitivity/ambiguity problem, recognition strategy, rule and data layout, contract surface, output-format policy (the decorative layer, §7), registration wiring, and test strategy. Sibling template: Currency (the canonical LOOKUP_TABLE capability, added 2026-08-08). |
| **Out of scope** | Quantities with numbers ("5 kg" — a future measurement capability); non-SI unit systems (imperial/US customary, cgs); IEC 80000-13 binary prefixes (kibi/quebi — a bit/byte capability); Unicode/LaTeX rendering of canonical output; conversion between units of different dimensions. |
| **Evidence basis** | Primary sources fetched and section-verified this session: [SI Brochure, 9th edition] current PDF **v4.01 (June 2026)**, 102 pp., DOI 10.59161/AUEZ1291 — extracted to `/tmp/opencode/si-brochure-9.txt` and page-verified (base units Table 3, derived units Table 4, prefixes Table 7, non-SI units Table 8, §5.2 writing rules); [27th CGPM Resolution 3 (2022)] (new prefixes) — bipm.org; [ISO 80000-1:2022] — iso.org. Empirical verification: pint @ `6fc0533` (`pint/default_en.txt` anchors L64–96 prefixes, L130 micron, L162 astronomical_unit, L169 metric_ton, L176 degree_Celsius, L180 minute; `parse_units` registry.py:1266; `get_name` registry.py:653) and sympy `physics.units` cloned and behavior-verified live; astropy.units exercised in a partial run. No source code, tests, or configuration were modified. Repo state: branch `feature/si-unit-capability` @ `0a585d2`. |

---

## Executive Summary

1. **SI is a case-meaningful domain — the direct opposite of Currency's case-folding template.** `K` (kelvin) and `k` (kilo), `S` (siemens) and `s` (second) are simultaneously valid, case-distinct official symbols. Grammar-owned case folding — the pattern Currency's `code_recognition`/`word_recognition` use — would destroy meaning here and must not be applied to symbols. Case folding is safe only for unit *names*.
2. **The authority is the BIPM SI Brochure, 9th edition (2019), currently v4.01 (June 2026).** The 27th CGPM (2022) Resolution 3 added four prefixes (quetta/ronna/ronto/quecto), growing the prefix table from 20 to 24 and making the pre-2022 "20 prefixes" figure stale — a provenance-versioning hazard the data tables must stamp.
3. **The bare-symbol ambiguity problem that forced Currency's `default_currency` opt-in does not exist for SI.** Because "prefix symbols can neither stand alone" (brochure §3), every bare token resolves deterministically: bare `m` = metre, `d` = day, `a` = are, `h` = hour, `t` = tonne; prefix-only tokens (`M`, `k`, `µ`) are **INVALID** (recognized, no valid unit), never AMBIGUOUS. No capability-specific contract parameter is needed for disambiguation.
4. **The real recognition complexity is prefixed symbols and compound expressions.** `MHz`, `km`, `µm` form a combinatorial vocabulary (24 prefixes × ~29 prefixable units, with the kilogram→gram exception), and `m/s²`, `km/h`, `N·m` are compound expressions requiring a shape grammar plus superscript normalization (`²` → `2`). This is a PARSER-shaped problem inside a LOOKUP_TABLE capability.
5. **Currency is the structural template throughout**: the same 6-slot package layout (`notation/contract/capability/grammar/rules` + `data/` subdirs), lexicon grammars feeding `LOOKUP_TABLE` rules with one `PUBLICATION` per file, key-only grammar data locked set-equal to rule data by a consistency test, and the four registration touch-points (alias import, runtime register, export test, replay-hash baseline).
6. **No existing Python library canonicalizes to the Brochure's own case-sensitive symbols.** pint (the richest registry) empirically collides on `k` → Boltzmann constant, `da` → deciyear, `u` → dalton, `B` → byte, and is whitespace-sensitive (`ms` vs `m s`); sympy ships only 20 prefixes and no `degree_Celsius`; astropy is symbol-preserving with US spellings and rejects `litre`/`celsius`/`Np`. All are validation/data cross-checks — the Brochure is the source of truth, exactly as ISO 4217 + CLDR are for Currency.
7. **The SI contract can be the minimal base contract** (Email/IP-style): zero capability-specific fields, `DEFAULT_OUTPUT_FORMAT = "symbol"`, empty `OFFERED_OUTPUT_FORMATS`, inherited identity `format_value`. It is the cleanest contract surface a LOOKUP_TABLE capability has shipped to date — and the empty offering set is a criterion-backed decision, not an accident of minimalism (§7).
8. **`output_format` is a decorative layer, not a second canonicalization.** The engine renders the rule-normalized canonical value *after* validation (`format_value` at orchestrator.py:269) and the rule layer is format-blind (CI purity scan). An offerable format must be **total** over the canonical set (Country offers `name` because every alpha-2 has one; `alpha4` is unofferable because most countries lack it) and **round-trip stable** — `canonicalize(canonicalize(x, C), C)` must reproduce the same value, since the format's output must be a re-recognizable input shape. On those criteria SI's empty `OFFERED_OUTPUT_FORMATS` survives: `"name"` fails on compounds, LaTeX is non-re-entrant, and only superscript-`"unicode"` rendering would qualify today (deferred — §7.4).

---

## 1. The Domain (HOW_TO Step 1: Plan Your Capability)

### 1.1 Input scope (D1)

The SI capability canonicalizes **standalone unit identifiers**, exactly as Currency canonicalizes standalone currency identifiers and Money does not:

| In scope | Example input → canonical value |
|---|---|
| Unit symbols, bare and prefixed | `"kg"` → `"kg"`, `"K"` → `"K"`, `"MHz"` → `"MHz"`, `"µm"` → `"µm"` |
| Unit names, bare and prefixed | `"Kilogram"` → `"kg"`, `"kelvin"` → `"K"`, `"megahertz"` → `"MHz"`, `"kilometre"` → `"km"` |
| Accepted non-SI units (Table 8) | `"litre"` → `"L"`, `"tonne"` → `"t"`, `"day"` → `"d"`, `"degree"` → `"°"` |
| Compound expressions | `"m/s²"` → `"m/s2"`, `"km/h"` → `"km/h"`, `"N·m"` → `"N·m"` |

**Out of scope** (documented, mirroring the Currency/Money split): amounts (`"5 kg"`, `"100 MHz"`) belong to a future measurement capability; the `5` and the unit are separate tokens there. Quantity-detection logic (is this a mass or a length?) is not canonicalization — both `m` and `kg` are valid units with different dimensions, and neither is "wrong".

### 1.2 What "canonical" means here (D2)

The Brochure defines both a **name** ("kilogram") and a **symbol** ("kg") for every unit. The milestone's example column settles the canonical form: **symbol form, case-sensitive, ASCII** — `"Kilogram"` → `"kg"`, `"Kelvin"` → `"K"`, `"megahertz"` → `"MHz"`, `"m/s²"` → `"m/s2"`. Symbols are the currency of scientific data; names are the human-written variant. This mirrors Currency (`DEFAULT_OUTPUT_FORMAT = "code"`): the symbol is the canonical value, the name is recognized input.

For compounds, canonical output follows Brochure §5.2 (single solidus; multiplication indicated by `·`): `m/s2` for metre-per-second-squared, `km/h`, `N·m`. Superscript digits (`²`) normalize to ASCII (`2`) — NFKC maps `²` → `2`, which the compound grammar applies at recognition time.

### 1.3 Where SI sits among Paxman capabilities

| Capability | Recognition strategy | Case handling | Canonical form |
|---|---|---|---|
| Currency (template) | 3 lexicon grammars (code/symbol/word) | Folds to uppercase (codes) / lowercase (words) | Uppercase alpha-3 |
| **SI (proposed)** | 3 grammars (symbol / name / compound) | **Symbols case-preserving; names case-folded** | Case-sensitive official symbol |
| Email / IP | Regex | Lowercase | Lowercase |

SI is the first capability whose *canonical value is case-meaningful*. Every downstream invariant that assumes case-folded canonical values (replay-hash literals, `format_value`, test assertions) must preserve case.

---

## 2. The Authorities

### 2.1 BIPM SI Brochure, 9th edition (2019), current v4.01 (June 2026)

The Brochure is the single authoritative document: it defines the seven base units (Table 3), the 22 derived units with special names (Table 4), the 24 prefixes (Table 7), and the non-SI units accepted for use with the SI (Table 8) — the complete universe of what the capability must canonicalize. It also states the writing rules (§5.2) that govern canonical output. Its version history is directly relevant to provenance stamping:

| Brochure version | Notable content change |
|---|---|
| 9th edition, 2019 (v1.x) | Post-2019-redefinition SI (fixed constants: ΔνCs, c, h, e, k, NA, Kcd); 20 prefixes |
| v2.01, Nov 2022 | **+4 prefixes** (quetta/ronna/ronto/quecto) per 27th CGPM Res. 3 |
| v3.01, 2024 | Angle / unit-one text improvements |
| v3.02, 2025 | Dalton value updated (CODATA 2022) |
| **v4.01, June 2026** | Current PDF fetched this session (102 pp., DOI 10.59161/AUEZ1291) |

**Provenance stamp**: `Provenance(authority="BIPM", specification_name="SI Brochure, 9th edition", version="2019", publication_year=2019, lifecycle="active")` with the edition's current revision noted in the rule docstring — the 2019 edition year is the stable anchor, and `year=2019` contract filtering continues to work (the 2022 prefixes are additions to the same edition, not a new edition).

### 2.2 CGPM resolutions that change the data surface

- **27th CGPM (2022) Resolution 3** — the four new prefixes ([bipm.org](https://www.bipm.org/en/committees/cg/cgpm/27-2022/resolution-3)). Data-table consequence: the prefix table is 24 rows, and any test asserting "20 prefixes" is stale.
- **16th CGPM (1979) Resolution 6** — the second litre symbol `L` ("to avoid the risk of confusion between the letter 1 and the letter l"); both `l` and `L` are accepted (Table 8 note 1). Canonicalization consequence: `"l"` → `"L"` (canonicalize the lowercase symbol to uppercase, mirroring how Currency folds codes).
- **20th CGPM (1995) Resolution 8** — abrogated the "supplementary units" class; radian and steradian are ordinary derived units (brochure p. 51 note). They are dimensionless (`rad = m/m`), with the brochure's own caveat that the quotient form "is not intrinsic and may be misleading" — the canonicalizer must treat `rad` and `sr` as official symbols, not as decomposable products.
- **13th CGPM (1967) Resolution 3** — renamed "degree Kelvin" → **kelvin**; `°K` is abrogated and must not resolve.

### 2.3 ISO/IEC 80000 series

- **ISO 80000-1:2022** "Quantities and units — Part 1: General" (2nd ed., Dec 2022, [iso.org/standard/76921.html](https://www.iso.org/standard/76921.html), jointly with IEC/TC 25) — the *terminology and formatting* authority: quantity symbols italic, unit symbols upright roman, value formatting (`number × unit` with spacing). It deliberately no longer duplicates the SI Brochure's unit tables.
- **ISO 80000-3:2019** "Space and time" ([iso.org/standard/64974.html](https://www.iso.org/standard/64974.html)) — names/symbols/conversion factors for the time and angle quantities (the Table 8 time rows in ISO form).
- **IEC 80000-13** — binary prefixes (kibi…quebi); explicitly **out of scope** for the SI capability (brochure §3: SI prefixes "refer strictly to powers of 10").

### 2.4 Why the Brochure wins the algorithm seat (D3)

| Candidate authority | Verdict |
|---|---|
| BIPM SI Brochure 9th ed. | **Primary.** Complete, current (v4.01), and authoritative for every canonical value the capability emits. |
| ISO 80000-1:2022 / ISO 80000-3 | **Secondary.** Formatting grammar and time/angle tables; carries the writing conventions the compound rule cites. |
| IEC 80000-13 | Out of scope (binary regime). |
| pint / sympy / astropy | Validation cross-checks only (see §6) — none canonicalizes to the Brochure's symbols. |

One publication per rule file, per house pattern: `bipm_si_brochure_ed2019.py` for all four brochure tables (multiple rule classes, one `PUBLICATION`), and `iso_80000_ed2022.py` for the compound-expression formatting rule.

---

## 3. The SI unit universe (the data surface)

All tables below are section-verified against the extracted brochure PDF (`/tmp/opencode/si-brochure-9.txt`; page = PDF page, folio = page + 110).

### 3.1 Seven base units (Table 3, p. 22 / folio 132)

| Quantity | Name | Symbol | Dimension |
|---|---|---|---|
| time `t` | second | s | T |
| length `l, x, r` | metre | m | L |
| mass `m` | kilogram | kg | M |
| electric current `I, i` | ampere | A | I |
| thermodynamic temperature `T` | kelvin | K | Θ |
| amount of substance `n` | mole | mol | N |
| luminous intensity `I_v` | candela | cd | J |

Each is fixed by a defining constant (Table 1, p. 13–14 / folio 123–124): ΔνCs = 9 192 631 770 Hz, c = 299 792 458 m/s, h = 6.626 070 15×10⁻³⁴ J·s, e = 1.602 176 634×10⁻¹⁹ C, k = 1.380 649×10⁻²³ J/K, NA = 6.022 140 76×10²³ mol⁻¹, Kcd = 683 lm/W.

### 3.2 Twenty-two derived units with special names (Table 4, p. 23–24 / folio 133–134)

| # | Name | Symbol | Quantity | In base units |
|---|---|---|---|---|
| 1 | radian | rad | plane angle | m/m (= 1) |
| 2 | steradian | sr | solid angle | m²/m² (= 1) |
| 3 | hertz | Hz | frequency | s⁻¹ |
| 4 | newton | N | force, weight | m·kg·s⁻² |
| 5 | pascal | Pa | pressure, stress | m⁻¹·kg·s⁻² |
| 6 | joule | J | energy, work, heat | m²·kg·s⁻² |
| 7 | watt | W | power, radiant flux | m²·kg·s⁻³ |
| 8 | coulomb | C | electric charge | s·A |
| 9 | volt | V | voltage, e.m.f. | m²·kg·s⁻³·A⁻¹ |
| 10 | farad | F | capacitance | m⁻²·kg⁻¹·s⁴·A² |
| 11 | ohm | Ω | resistance | m²·kg·s⁻³·A⁻² |
| 12 | siemens | S | conductance | m⁻²·kg⁻¹·s³·A² |
| 13 | weber | Wb | magnetic flux | m²·kg·s⁻²·A⁻¹ |
| 14 | tesla | T | magnetic flux density | kg·s⁻²·A⁻¹ |
| 15 | henry | H | inductance | m²·kg·s⁻²·A⁻² |
| 16 | degree Celsius | °C | Celsius temperature | K |
| 17 | lumen | lm | luminous flux | cd·sr |
| 18 | lux | lx | illuminance | cd·sr·m⁻² |
| 19 | becquerel | Bq | activity | s⁻¹ |
| 20 | gray | Gy | absorbed dose | m²·s⁻² |
| 21 | sievert | Sv | dose equivalent | m²·s⁻² |
| 22 | katal | kat | catalytic activity | mol·s⁻¹ |

Key footnotes (p. 24 / folio 134): **(d)** Hz only for periodic phenomena, Bq only for stochastic processes; **(f)** °C is a special name for kelvin when expressing Celsius temperatures (differences are identical in °C and K); **(i)** sievert is reserved for dose equivalent — 16th CGPM 1979 Res. 5 adopted it "to safeguard human health" against absorbed-dose/dose-equivalent confusion. The brochure also warns torque is "newton metre", never "joule" (p. 26 / folio 136) — a naming-ambiguity data point (see §4.4).

### 3.3 Radian and steradian: the abrogated supplementary class

11th CGPM (1960) Res. 12 created the "supplementary units" class (and named the system "Système International d'Unités"); 20th CGPM (1995) Res. 8 abrogated the class. Today rad and sr are ordinary derived units with unit-one dimension. They are official symbols in the canonical table — not decomposable into `m/m` or `m²/m²` products.

### 3.4 Twenty-four prefixes (Table 7, p. 28 / folio 138) (D4)

| 10ⁿ | Prefix | Symbol | | 10ⁿ | Prefix | Symbol |
|---|---|---|---|---|---|---|
| 10³⁰ | **quetta** | **Q** | | 10⁻¹ | deci | d |
| 10²⁷ | **ronna** | **R** | | 10⁻² | centi | c |
| 10²⁴ | yotta | Y | | 10⁻³ | milli | m |
| 10²¹ | zetta | Z | | 10⁻⁶ | micro | µ |
| 10¹⁸ | exa | E | | 10⁻⁹ | nano | n |
| 10¹⁵ | peta | P | | 10⁻¹² | pico | p |
| 10¹² | tera | T | | 10⁻¹⁵ | femto | f |
| 10⁹ | giga | G | | 10⁻¹⁸ | atto | a |
| 10⁶ | mega | M | | 10⁻²¹ | zepto | z |
| 10³ | kilo | k | | 10⁻²⁴ | yocto | y |
| 10² | hecto | h | | 10⁻²⁷ | **ronto** | **r** |
| 10¹ | deca | da | | 10⁻³⁰ | **quecto** | **q** |

The four bolded prefixes are the 2022 additions. **Combination rules** (p. 28–29 / folio 138–139) that shape recognition and validation:

- Prefixes attach directly — the grouping "constitutes a new inseparable unit symbol"; prefix names are always lowercase; uppercase symbols only for multiples ≥ M, plus da/h/k.
- **Mass exception**: multiples of mass are formed on **gram**, not kilogram — "10⁻⁶ kg is written as milligram, mg, not as microkilogram, µkg". The prefixed-symbol generator must attach prefixes to `g` for mass, with `kg` remaining the base unit's own symbol.
- **No compound prefixes**; prefixes can "neither stand alone nor be attached to the number 1"; no prefixing of `%`/`‰`; prefixing `°C` is discouraged.
- SI prefixes are strictly powers of 10 — the binary prefixes (kibi…quebi) are a separate regime (out of scope).

### 3.5 Non-SI units accepted for use with the SI (Table 8, p. 30–31 / folio 140–141)

| Group | Name | Symbol | SI value |
|---|---|---|---|
| Time | minute | min | 60 s |
| | hour | h | 3 600 s |
| | day | d | 86 400 s |
| Plane/phase angle | degree | ° | (π/180) rad |
| | minute | ′ | (1/60)° |
| | second | ″ | (1/60)′ |
| Historical decimal multiples | are | a | 1 dam² = 10² m² |
| | hectare | ha | 1 hm² = 10⁴ m² |
| | barn | b | 100 fm² = 10⁻²⁸ m² |
| | litre | l, **L** | 1 dm³ = 10⁻³ m³ |
| | tonne | t | 1 Mg = 10³ kg |
| | angstrom | Å | 0.1 nm = 10⁻¹⁰ m |
| | gal | Gal | 1 cm·s⁻² = 10⁻² m·s⁻² |
| | bar | bar | 0.1 MPa = 10⁵ Pa |
| Internationally recognized, non-decimal | dalton | Da | 1.660 539 068 92(52)×10⁻²⁷ kg (CODATA 2022) |
| | astronomical unit | au | 149 597 870 700 m (IAU 2012) |
| | nautical mile | *(no symbol)* | 1852 m |
| | knot | *(no symbol)* | (1852/3600) m·s⁻¹ |
| | electronvolt | eV | 1.602 176 634×10⁻¹⁹ J (exact) |
| Specialized disciplines | neper | Np | 1 Np = 1 |
| | bel | B | (1/2) ln 10 Np |
| | decibel | dB | 0.1 B |
| | var | var | 1 V·A = 1 W |

Table 8 notes with canonicalization consequences (p. 31 / folio 141): litre has **both** symbols (`l` and `L`; canonicalize `l` → `L`); **dalton is an alternative name for the unified atomic mass unit, whose symbol is `u`** (so `u` must resolve to `Da`, the canonical name, and *not* to the micro prefix — a collision pint gets wrong); nautical mile and knot have **no internationally agreed symbol** (recognizable by name only); the dalton value moved at CODATA 2022 (provenance versioning, §2.1).

---

## 4. Ambiguity analysis

### 4.1 Case collisions — official symbols differing only by case (D3, D5)

Every pair below is simultaneously valid and case-distinct (Tables 3, 4, 7, 8):

- **K** kelvin vs **k** kilo · **S** siemens vs **s** second
- **T** tesla vs **t** tonne · **H** henry vs **h** hour (and hecto)
- **N** newton vs **n** nano · **A** ampere vs **a** atto (and are)
- **M** mega vs **m** metre/milli · **P** peta vs **p** pico · **F** farad vs **f** femto · **C** coulomb vs **c** centi · **G** giga vs **g** gram · **E** exa vs **e** (elementary charge)
- **Y** yotta vs **y** yocto · **Z** zetta vs **z** zepto · **Q** quetta vs **q** quecto · **R** ronna vs **r** ronto
- **d** day (Table 8) vs **d** deci · **da** deca vs **Da** dalton

**Consequence**: symbol recognition must be exact, case-sensitive membership — never case-folded. `K` resolves to kelvin; `k` is a prefix token that cannot stand alone (INVALID). This is the single hard divergence from the Currency template's grammar-owned folding.

### 4.2 Prefix-vs-unit collisions and the "prefix cannot stand alone" rule (D5)

The brochure (§3, p. 29) states prefix symbols can neither stand alone nor attach to the number 1. This makes every **bare** token deterministic:

| Bare token | Resolution | Why |
|---|---|---|
| `m` | metre (unit) | Official symbol beats milli prefix (prefix can't stand alone) |
| `d` | day (Table 8) | Unit beats deci prefix |
| `a` | are (Table 8) | Unit beats atto prefix |
| `h` | hour (Table 8) | Unit beats hecto prefix |
| `t` | tonne (Table 8) | Unit; tera prefix is `T` |
| `K` | kelvin (unit) | `k` is the kilo prefix |
| `M`, `k`, `µ`, `n`, `p`, … | **INVALID** | Recognized as prefix tokens; no valid bare unit → INVALID, not MISSING |
| `min`, `ha`, `eV`, `dB`, `Wb` | official symbols | Longest-first official membership |

Resolution precedence for a recognized symbol token: **(1) exact membership in the official unit-symbol set** (base ∪ derived ∪ Table 8); **(2) if not, exact membership in the valid prefixed-symbol set** (generated product, §4.3); **(3) if neither** — e.g. prefix-only — INVALID. This precedence is what keeps `Pa` (pascal) from decomposing into `P·a` (peta·are) and `cd` (candela) from `c·d` (centi·day). **No `default_unit`-style contract parameter is required** — unlike Currency's `$`, SI has no shared bare symbol.

### 4.3 Prefixed symbols — a generated combinatorial vocabulary (D4)

A prefixed symbol is `prefix_symbol + unit_symbol`, except the mass exception (prefixes attach to `g`). The valid set is the **product** of the 24-prefix table with the prefixable unit symbols (gram, metre, second, ampere, kelvin, mole, candela, and the derived units with symbols that take prefixes — not rad, sr, °C, and not the Table 8 "no symbol" units). Examples: `MHz`, `km`, `µm`, `mg`, `ms` (millisecond), `dam` (decametre), `kPa`, `GV`, `ng`, `quectogram`… The product is finite (24 × ~25 ≈ 600 symbols + ~600 names) and generated at data-edit time into a sorted tuple — exactly the `grammar/data/` key-token pattern, with the rule-side authoritative table being the generator itself.

Recognition subtlety: `ms` (milli·second) must not be read as `m·s` (metre·second) — the brochure requires a separator for multiplication, so the concatenated `ms` is unambiguously millisecond. Longest-first token ordering handles `ms` vs `m`, and `MHz` vs `M`/`Hz`.

### 4.4 Spelling and script variants (D7)

| Variant | Canonical | Notes |
|---|---|---|
| metre / **meter** | m | US spelling accepted as alias (brochure uses "metre") |
| litre / **liter** | L | Both spellings + both symbols |
| deca / **deka** | da | pint registers `deka` too |
| tonne / **metric ton** | t | |
| µm / **micron** | µm | "micron" abrogated as a name (13th CGPM 1967) — accept or reject is a policy call |
| micro **µ** / **u** / **mc** | µ | pint accepts all three (default_en.txt L75); brochure uses µ only — `u` collides with dalton's symbol, so **only µ is a valid prefix** in Paxman |
| ohm **Ω** / "ohm" | Ω | Symbol is the Greek capital Omega; name is "ohm" |
| °C / **celsius** / degC | °C | Name form "degree Celsius" |
| hertz | Hz | Singular/plural invariant |
| °K / "degree Kelvin" | — | Abrogated 1967; must not resolve |
| rad, sr | rad, sr | Do not decompose to m/m |

### 4.5 Empirical collision evidence from pint (verification cross-check)

| Input | pint result | Brochure meaning | Paxman policy |
|---|---|---|---|
| `k` | Boltzmann constant | k = kilo prefix | INVALID (prefix alone) |
| `da` | deciyear (d × year-'a') | da = deca prefix | INVALID (prefix alone) |
| `u` | unified atomic mass unit | u = dalton alias `Da` | `Da` (via u-as-name? **no** — `u` alone is a prefix-less symbol; resolve to Da only via the name "dalton"/"unified atomic mass unit") |
| `B` | byte | B = bel | bel (byte is IEC 80000-13, out of scope) |
| `KHz` | undefined | K·Hz | case-sensitive; INVALID (K is kelvin, not kilo) |
| `ms` vs `m s` | millisecond vs metre·second | same | whitespace-sensitive; `m s` is a compound expression |

pint's canonical form is **lowercase US-style names** (`str(Q)` → `"5 megahertz"`, `~Q` → `"5 MHz"`) — two canonical strings for one quantity, and neither is the brochure's symbol-first convention. This confirms no library can be the authority.

---

## 5. SI written forms (the recognition matrix)

| Form | Examples | Grammar | Strategy |
|---|---|---|---|
| Bare unit symbol | `kg`, `K`, `m`, `d`, `Ω`, `Å` | `symbol_recognition` | Lexicon, **case-sensitive** |
| Prefixed unit symbol | `MHz`, `km`, `µm`, `kPa`, `ms` | `symbol_recognition` | Lexicon (generated product), case-sensitive |
| Bare/prefixed unit name | `Kilogram`, `kelvin`, `megahertz`, `kilometre`, `meter`, `degree Celsius` | `name_recognition` | Lexicon, **case-folded** (safe: names are case-insensitive) |
| Compound expression | `m/s²`, `km/h`, `N·m`, `kg·m/s²`, `m s⁻²` | `compound_recognition` | Regex shape + rule-validated components |

Three grammars, mirroring Currency's three — but with two strategic differences: **symbols are recognized case-sensitively** (Currency folds), and **a third grammar handles compounds** (Currency has no analogue). Grammar names: `symbol_recognition`, `name_recognition`, `compound_recognition` — all always active (Currency's always-all `active_grammars` pattern), so no `include_*` flags.

---

## 6. Existing Python libraries (data-source suitability)

| Library | Canonical form | Coverage | Collisions / gaps | Verdict for Paxman |
|---|---|---|---|---|
| **pint** `6fc0533` | Lowercase US-style names (`str`/`~` split: "5 megahertz" vs "5 MHz"); `parse_units` registry.py:1266, `get_name` registry.py:653 | All 24 prefixes (default_en.txt L64–96), rich unit set (924 lines) | `k` → Boltzmann, `da` → deciyear, `u` → dalton, `B` → byte; whitespace-sensitive; extra aliases (`mc`, `um`, `deka`) | **Validation cross-check only** — wrong canonical philosophy (names not symbols) and added collisions |
| **sympy** `physics.units` | `Quantity.name` (`str(kg)` = "kilogram"), `.abbrev` separate | Only **20 prefixes** (no quetta/ronna/ronto/quecto); no `degree_Celsius`/°C, sievert, lumen; `Da` = physical constant | Stale vs 2022; incomplete temperature surface | Reference only; its `convert_to` machinery is out of scope |
| **astropy.units** | Case-preserving symbols (`Unit('MHz').to_string()` = `'MHz'`) | US spellings; rejected `litre`, `degC`, `celsius`, `Np`, `n` (empirical) | Astronomy-flavored defaults; different philosophy | Validation cross-check |
| **UCUM / ucum-lib** | UCUM case-sensitive codes | Health-care oriented, not the SI brochure's universe | UCUM's case conventions differ from the brochure's in places | Not needed |

**Verdict (D3)**: for a deterministic, provenance-first canonicalizer, the Brochure itself — machine-read into plain data tables, exactly as this project already does for Currency/ISBN/Phone — is the authority. Libraries are empirical regression oracles: every pint collision in §4.5 becomes a locked test case.

---

## 7. Output format: the decorative layer

Paxman's `output_format` is a **decorative layer applied after the canonical value has been derived** — never a second canonicalization, never a revalidation. This section states where the layer sits in the pipeline, the two criteria any offered format must satisfy, the shipped evidence for those criteria, and what they mean for SI.

### 7.1 Positioning: after derivation, never during it

The engine's `_collect_candidates` (orchestrator.py:245) runs each recognized span through `rule.matches()` (validation), then `rule.normalize()` (canonical derivation), and **only then** renders the value through the capability's presentation seam — `capability.format_value(canonical, contract.output_format, notation)` (orchestrator.py:269) — before candidate dedup and status resolution. The formatted string is what the caller receives; the recognition and validation that produced it never saw the format:

- Rules **cannot read `output_format`** — the CI purity scan (`tests/unit/test_rule_output_format_purity.py`) bans the token from the rule layer.
- `resolve_output_format()` (paxman/core/contract.py:54) gates *contract construction*, not the pipeline: `None` / `"default"` / the declared default all resolve to the default format; only members of `OFFERED_OUTPUT_FORMATS` pass through; anything else is a `ContractError`.

The positioning is deliberate, and its purpose is usefulness rather than decoration for its own sake. A user who wants the canonical value in a different form does not need a separate resolution path — the usual alternative would re-run recognition and validation against the same authority tables, wasting processing time and risking a *different* answer. Paxman instead validates the true canonical value **once**, then presents that validated value in whatever offered form the caller finds useful. Two consequences are load-bearing:

- **`output_format` never triggers revalidation.** The formatted value is not re-parsed or re-checked within the pass.
- **`output_format` never changes the canonicalization result.** Recognition, validation, and `normalize()` are format-blind; only the returned presentation differs. If a requested format *would* change the result, it must not be offered at all (§7.2).

### 7.2 Two criteria for an offerable format

**Criterion 1 — total representability.** A format is offerable only if *every* value the capability can canonicalize has a rendering in it — the mapping must be total, not partial. Country offers `"name"` because every ISO 3166-1 alpha-2 code (the canonical value) has an English name; `ALPHA2_TO_NAME` is total. Country can **not** offer `"alpha4"`: alpha-4 codes exist only in ISO 3166-3 for former entities, so most countries have none — the mapping is undefined for the large majority of canonical values, and the format would silently pass them through as if the rendering were meaningful. A partial rendering is not a format, it is a defect.

**Criterion 2 — round-trip stability.** Any offered format's output must be able to re-enter the Paxman pipeline and resolve to the same canonical value, under the same contract promise it was derived from. If the canonical value changes on the second pass, the format is not stable enough to be considered an offering:

```
paxman.canonicalize(paxman.canonicalize(successful_canonicalize_input, contract), contract) = canonical_value
```

regardless of which output format the caller wants, or none at all. The double application is a fixed point: the second pass must reproduce the first pass's returned value exactly. For the default format (identity) this reduces to "re-canonicalizing a canonical value returns itself"; for an offered format it means the format's output must be a **recognized input shape** of the same capability — the re-entry must run the same grammars over the formatted string and reach the same canonical value. Criterion 2 is what rules out formats that are merely decorative: any rendering that no grammar can re-read (LaTeX, presentation markup) fails immediately.

### 7.3 Shipped evidence (empirically verified this session)

| Capability | Default | Offered | Criterion 1 | Criterion 2 (verified round-trips) |
|---|---|---|---|---|
| Country | `alpha2` | `alpha3`, `numeric`, `name` | ✓ total (every alpha-2 has all three) | ✓ `"US"` → `"USA"` / `"840"` / `"UNITED STATES"` — all re-enter to the same value |
| ISBN | `isbn13` | `hyphenated` | ✓ Range-Message hyphens are positional, never lossy | ✓ `"9780110002224"` → `"978-0-11-000222-4"` — the isbn13 grammar accepts `[ -]?` separators |
| Money | `code_amount` | `compact` | ✓ the code/amount separator space is optional in the code grammar | ✓ `"USD500"` → `"USD500.00"` — same glued shape as the original input |
| Phone | `e164` | `rfc3966`, `national` | ✓ | `rfc3966` ✓ (`"+15551234567"` → `"tel:+15551234567"` re-enters); `national` **⚠** — stable only while the number is valid in the national path; an E.164-valid but NANP-invalid number (`"+15551234567"` → `"5551234567"`) re-enters **INVALID** |
| Date | `ISO` | `US` | ✓ | **⚠** — stable only while the US reading is unambiguous on re-entry; `"2026-01-02"` → `"01/02/2026"` re-enters **AMBIGUOUS** (a valid European reading also exists) |

The two ⚠ rows are the criterion doing its job. Phone's `national` and Date's `US` both predate the criterion and both have re-entry holes for a subset of inputs — exactly the failure class the criterion exists to prevent. They are the cautionary evidence for why SI's offerings must be gated on both criteria *before* shipping, not audited after.

### 7.4 What the criteria mean for SI

SI ships `DEFAULT_OUTPUT_FORMAT = "symbol"` with an **empty** `OFFERED_OUTPUT_FORMATS` — and the criteria show that is a decision, not a default. Three candidate formats were evaluated:

| Candidate | Rendering | Criterion 1 (total) | Criterion 2 (round-trip) | Verdict |
|---|---|---|---|---|
| `"name"` | `kg` → `kilogram`, `MHz` → `megahertz` | ✓ for bare and prefixed symbols — the Brochure names every unit | **✗ for compounds** — `m/s2` has no single-table name; the §5.2 phrase "metre per second squared" is not a recognized input (the name grammar holds unit names, not phrase names) | Not offerable as a whole-capability format; would require compound phrase-name recognition first |
| `"latex"` | `kg` → `\mathrm{kg}` | ✓ trivially — any string renders | **✗** — no grammar recognizes LaTeX; the output cannot re-enter | **Never offerable** — the textbook case of decorative-but-not-re-entrant |
| `"unicode"` (superscripts) | `m/s2` → `m/s²`, `s-2` → `s⁻²` | ✓ — every compound exponent is a superscript digit; bare/prefixed symbols are already the Brochure's Unicode (Ω, µ, Å, °C) | ✓ — the compound grammar NFKC-folds `²`→`2` / `⁻²`→`-2` at recognition, so the rendering re-enters to the same ASCII canonical | The **only** format that satisfies both criteria today |

The conclusion: SI v1 keeps `OFFERED_OUTPUT_FORMATS = frozenset()` with identity `format_value`. The symbol form is already the maximal canonical value, and the single re-entrant presentation alternative — superscript `"unicode"` — is a typographic nicety that can be added later behind the same seam. `"name"` stays out until compound phrase-names are a recognized input shape; LaTeX stays out permanently.

---

## 8. Paxman Architectural Mapping (HOW_TO Steps 2–10)

### 8.1 Directory structure (Step 2) and Notation (Step 3)

Mirrors Currency file-for-file; capability directory is `SI` (PascalCase per spec), test directory `si`:

```
paxman/capabilities/SI/
├── __init__.py                    # exports SICapability, SIContract, SIUnitNotation
├── notation.py                    # SIUnitNotation (frozen, slots=True)
├── contract.py                    # SIContract (frozen, NO slots)
├── capability.py                  # SICapability (name="si", version="1.0.0")
├── grammar/
│   ├── __init__.py
│   ├── symbol_recognition.py      # Lexicon, case-sensitive
│   ├── name_recognition.py        # Lexicon, case-folded
│   ├── compound_recognition.py    # Regex shape (D6)
│   └── data/
│       ├── __init__.py
│       ├── unit_symbol_tokens.py  # official symbols + generated prefixed symbols
│       ├── unit_name_tokens.py    # names + generated prefixed names
│       └── compound_tokens.py     # component keys for the compound grammar
└── rules/
    ├── __init__.py
    ├── bipm_si_brochure_ed2019.py # PUBLICATION: BIPM 2019 — Section-base-units,
    │                              #   Section-derived-units, Section-non-si-units,
    │                              #   Section-prefixes
    ├── iso_80000_ed2022.py        # PUBLICATION: ISO 80000-1:2022 — Section-compounds
    └── data/
        ├── __init__.py
        ├── si_base_units.py       # BASE_UNITS frozenset (7)
        ├── si_derived_units.py    # DERIVED_UNITS frozenset (22)
        ├── si_prefixes.py         # PREFIX_SYMBOLS/PREFIX_NAMES dicts (24) + generator
        ├── si_nonsi_units.py      # Table 8 unit tables
        └── unit_names.py          # NAME_TO_SYMBOL dict (name → canonical symbol)
```

**Notation** — the Currency discriminator pattern, extended for compounds:

```python
@dataclass(frozen=True, slots=True)
class SIUnitNotation:
    text: str  # the recognized token, as written
    shape: str  # "symbol" | "name" | "compound"
```

`_VALID_SHAPES = frozenset({"symbol", "name", "compound"})`, `__post_init__` rejects empty text / bad shape, `as_list()` returns `[text, shape]`. Currency's exact convention.

### 8.2 Grammar layer (Step 4)

- **`symbol_recognition`** — Lexicon strategy, **case-sensitive** (no folding!). Token table = official unit symbols (base ∪ derived ∪ Table 8, minus the "no symbol" units) **plus** the generated prefixed-symbol product, sorted longest-first. Lookarounds (`(?<![\w])…(?![\w])`) prevent mid-word matches, mirroring Currency's sign-blocking lookarounds. Emits `shape="symbol"`.
- **`name_recognition`** — Lexicon strategy, **case-folded** (the one place folding is safe — unit names are case-insensitive words). Tokens = unit names + prefixed names, longest-first; `"degree Celsius"` multi-word entry; lookbehind blocks attaching to preceding words. Emits `shape="name"`.
- **`compound_recognition`** — Regex strategy for `A(/|·|⋅)B` and `A·B^n` shapes; applies NFKC to fold `²`→`2`, `⁻²`→`-2`; emits the whole expression as one span with `shape="compound"`. Grammar is shape-only — component validation belongs to the rule (§8.3), exactly the grammar/rule boundary.

All three compile patterns/alternations at module scope, early-return `[]` on blank text, and emit span-bearing `RecognitionMatch` objects only.

### 8.3 Rule layer (Step 5)

Two rule files, one `PUBLICATION` each (house pattern: one publication per file):

**`bipm_si_brochure_ed2019.py`** — `PUBLICATION = Provenance(authority="BIPM", specification_name="SI Brochure, 9th edition", kind="specification", reference_url="https://www.bipm.org/en/publications/si-brochure/", version="2019", lifecycle="active", publication_year=2019)`:

| Rule class | `name` | `strategy` | `target_grammars` | Validates |
|---|---|---|---|---|
| `SectionBaseUnits` | `Section-base-units` | `LOOKUP_TABLE` | `{symbol_recognition, name_recognition}` | Table 3 membership; name→symbol |
| `SectionDerivedUnits` | `Section-derived-units` | `LOOKUP_TABLE` | `{symbol_recognition, name_recognition}` | Table 4 membership; name→symbol |
| `SectionNonSiUnits` | `Section-non-si-units` | `LOOKUP_TABLE` | `{symbol_recognition, name_recognition}` | Table 8 membership; `l`→`L`; name→symbol |
| `SectionPrefixes` | `Section-prefixes` | `LOOKUP_TABLE` | `{symbol_recognition, name_recognition}` | Prefixed-token validity (generator product); prefix-alone → False (INVALID) |

The shared resolution helper mirrors Currency's `_resolve_code`: for a recognized token, look up official membership first, then generated prefixed membership (the precedence of §4.2), returning the canonical symbol or `None` (→ `matches()` False).

**`iso_80000_ed2022.py`** — `PUBLICATION = Provenance(authority="ISO/IEC", specification_name="ISO 80000-1:2022", …)`; `SectionCompounds` (`name = "Section-compounds"`, `strategy = PARSER`, `target_grammars = {compound_recognition}`): splits the expression on `/` and `·`, validates each component against the same unit tables, normalizes to canonical `A/B` (single solidus) / `A·B` (centred dot), `²` already folded by the grammar. `requires_features = frozenset()` (always runs).

All rules: never raise, never read `output_format`, six metadata attributes enforced by `Rule.__init_subclass__`. No capability-specific contract field is cast-for (D5) — the contract is pure base.

### 8.4 Capability and Contract (Steps 6–7)

```python
@dataclass(frozen=True)
class SIContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "symbol"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="si", init=False)

    @property
    def active_grammars(self) -> tuple[str, ...]:
        return ("symbol_recognition", "name_recognition", "compound_recognition")
```

- **No capability-specific fields, no `_extra_dict_fields` override** — the first LOOKUP_TABLE capability with a pure base contract (Email/IP-style). Replay hash carries the five standard keys only.
- `create_contract()`: the unanimous keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`), then nothing — `DEFAULT_OUTPUT_FORMAT="symbol"` is the single canonical form and `OFFERED_OUTPUT_FORMATS` is empty, so **`format_value` is inherited (identity)**, like Currency. The empty set is criterion-backed (§7.4): no alternative format is both total over the canonical set and round-trip stable.
- `SICapability.name = "si"`, `version = "1.0.0"`; `get_grammars()` returns the three grammars, `get_rules()` the five rule classes.

### 8.5 Registration and exports (Steps 8–9)

The four Currency touch-points, with SI-specific notes:

1. **`paxman/capabilities/__init__.py`** — `from paxman.capabilities.SI.capability import SICapability as SI` + `__all__` entry. The `SI` acronym alias trips ruff **N814**, already covered by the existing file-wide scoped ignore `"paxman/capabilities/__init__.py" = ["N814"]` (pyproject.toml) — no inline `# noqa` needed.
2. **Runtime** — users call `register_capability(SI())` (unchanged machinery in `paxman/core/discovery.py`).
3. **Export test** — `tests/unit/test_capability_exports.py` asserts the exact 9-name `__all__`; must grow to 10 (add `SI` to the import block and the exact-set assertion).
4. **Replay-hash baseline** — `tests/integration/test_default_replay_hashes.py` gains a `"si"` entry driven with `SICapability.create_contract(year=2026)`; literals never edited to green.

Plus: `pytestmark` marker `si` registered in pyproject `[tool.pytest.ini_options]`, and the README capabilities table gains the tenth row.

### 8.6 Tests (Step 10)

Currency's nine test files, renamed:

```
tests/capabilities/si/
├── test_notation.py       # frozen immutability, as_list, shape validation
├── test_contract.py       # output_format resolution, active_grammars, replay keys
├── test_capability.py     # wiring, create_contract pass-through, format_value identity, package exports
├── test_grammar.py        # span-contract invariants; parametrized recognize/reject/precedence
├── test_rules.py          # matches/normalize per rule + metadata attrs
├── test_data.py           # table integrity: 24 prefixes, 29 unit symbols, generated-product invariants
└── test_data_consistency.py  # grammar tokens == rule-data keys (the locked boundary)
tests/integration/test_si_pipeline.py   # e2e rows via canonicalize(); _clean_registry fixture
```

The **pint collision table (§4.5) becomes the locked regression suite**: `k`→INVALID, `da`→INVALID, `B`→bel, `KHz`→INVALID, `ms`→millisecond, `m s`→compound. And the milestone examples are the e2e contract rows: `"Kilogram"`→`"kg"`, `"Kelvin"`→`"K"`, `"megahertz"`→`"MHz"`, `"m/s²"`→`"m/s2"`, `"km/h"`→`"km/h"` — all SUCCESS, single candidate.

### 8.7 Data modules

Plain module-level tables, maintained in place (house rule: only ISBN data is generator-produced — but SI's *prefixed-symbol set* is a legitimate exception, generated by a documented `tools/` script from `si_prefixes.py` × unit tables, exactly like `tools/regenerate_isbn_range_data.py`):

- `rules/data/si_base_units.py` — `BASE_UNITS: frozenset[str]` (7 symbols)
- `rules/data/si_derived_units.py` — `DERIVED_UNITS: frozenset[str]` (22 symbols)
- `rules/data/si_prefixes.py` — `PREFIX_SYMBOLS: dict[str, int]`, `PREFIX_NAMES: dict[str, int]` (24 each), plus the product generator with the kg→gram exception
- `rules/data/si_nonsi_units.py` — Table 8 tables, with `l`→`L` canonicalization rule and the no-symbol units (nautical mile, knot) flagged name-only
- `rules/data/unit_names.py` — `NAME_TO_SYMBOL: dict[str, str]` (case-folded keys → canonical symbols; US-spelling aliases `meter`/`liter`)
- `grammar/data/unit_symbol_tokens.py`, `unit_name_tokens.py` — key-only tuples, longest-first (keys of the rule tables / generator output)
- `grammar/data/compound_tokens.py` — component keys the compound grammar needs

### 8.8 Consistency test (the grammar/rule boundary, enforced)

`test_data_consistency.py` locks the two catalogs equal, Currency-style: `set(unit_symbol_tokens) == set(BASE_UNITS | DERIVED_UNITS | NONSI_SYMBOLS | GENERATED_PREFIXED_SYMBOLS)`; name tokens == `set(NAME_TO_SYMBOL)`; every canonical symbol is brochure-derived; no token maps to a canonical value at the grammar layer.

---

## 9. Out of Scope and Future Work

| Future capability / enhancement | Note |
|---|---|
| **Measurement/quantity** ("5 kg", "100 MHz") | Currency/Money split analog; amount parsing + unit pairing |
| **Unit conversion** (m↔km, °C↔K) | Requires quantity/dimension algebra (sympy-style) — different mission |
| **Imperial/US customary, cgs** | Separate registries, separate provenance |
| **IEC 80000-13 binary prefixes** (kibi…quebi) | Bit/byte capability; must not leak into SI's decimal table |
| **`output_format` alternatives** | Only formats that pass both offerability criteria (§7.2) may be added — the seam exists (ISBN's `hyphenated` is the precedent). Superscript `"unicode"` rendering (`m/s2` → `m/s²`) is the one candidate that qualifies today and is the natural first addition. `"name"` (`kg` → `kilogram`) is deferred until compound phrase-names are a recognized input; LaTeX is **not offerable** — no grammar recognizes it, so its output cannot re-enter the pipeline |
| **Acceptance of abrogated names** ("micron", "degree Kelvin") | Policy toggle if users demand; default reject (13th CGPM 1967) |

---

## 10. Resolved Decisions

| ID | Question | Decision |
|---|---|---|
| D1 | Input scope | Standalone unit identifiers only: bare/prefixed symbols, names, and compound expressions (`A/B`, `A·B`). Quantities ("5 kg") out of scope (future measurement capability). |
| D2 | Canonical form | Brochure **symbol form, case-sensitive**: `"Kilogram"`→`"kg"`, `"megahertz"`→`"MHz"`, `"m/s²"`→`"m/s2"`. `DEFAULT_OUTPUT_FORMAT="symbol"`, empty `OFFERED_OUTPUT_FORMATS`, identity `format_value` — the empty set is criterion-backed (§7.4). |
| D3 | Authority | BIPM SI Brochure 9th ed. (2019, v4.01 current) is the sole data authority; ISO 80000-1:2022 carries compound-formatting provenance; pint/sympy/astropy are regression oracles only. |
| D4 | Prefixed symbols | Generated product table (24 prefixes × prefixable units, kg→gram exception), created by a `tools/` script, key-only in `grammar/data/`, authority side in `rules/data/si_prefixes.py`; longest-first token ordering. |
| D5 | Bare-symbol ambiguity | None exists: official-symbol membership wins over decomposition; prefix-only tokens are INVALID (never AMBIGUOUS). **No capability-specific contract parameter.** Resolution precedence: official set → generated prefixed set → INVALID. |
| D6 | Compound expressions | Third grammar (`compound_recognition`, regex shape) + `SectionCompounds` PARSER rule validating components against the shared tables; NFKC folds `²`→`2`; canonical `A/B` / `A·B`. Always active (no `include_*`). |
| D7 | Names & spellings | Names case-folded (safe); US spellings (`meter`, `liter`, `deka`) accepted as aliases; `u` is **not** micro (collides with dalton); `°K`/`micron` rejected (abrogated); `l`→`L`. |
| D8 | Output-format policy | `output_format` is a post-`normalize()` presentation seam (orchestrator.py:269): it never triggers revalidation and never changes the canonicalization result — rules are format-blind by purity scan. An offerable format must be (1) **total** over the canonical set (Country's `name` qualifies; `alpha4` does not — most countries have none) and (2) **round-trip stable**: re-canonicalizing under the same contract reproduces the same value, `paxman.canonicalize(paxman.canonicalize(x, C), C) = canonical_value`, for every offered format and for none. SI ships no offering: `"name"` fails on compounds, LaTeX is non-re-entrant, `"unicode"` superscripts is the one qualifying candidate (deferred). |

---

## 11. Glossary

| Term | Meaning |
|---|---|
| **Base unit** | One of the seven dimension-defining units (Table 3): s, m, kg, A, K, mol, cd |
| **Derived unit with special name** | One of the 22 named combinations (Table 4), e.g. Hz, N, Pa, Ω, Sv |
| **Prefix** | One of the 24 decimal multipliers (Table 7), e.g. kilo `k`, mega `M`, micro `µ`, quetta `Q` |
| **Prefixed symbol** | `prefix + unit` concatenation (e.g. `MHz`); the kg→gram exception governs mass |
| **Non-SI unit accepted for use with the SI** | Table 8 unit (min, h, L, t, eV, bar, …) |
| **Compound expression** | `A/B` or `A·B` form (e.g. `m/s²`, `N·m`) |
| **Shape** | Notation discriminator: `"symbol"` / `"name"` / `"compound"` |
| **Canonical symbol** | The case-sensitive brochure symbol a token resolves to |
| **INVALID vs MISSING** | Recognized-but-unvalidated (prefix alone) vs not recognized at all |
| **Output format** | A decorative presentation of the validated canonical value, applied by `format_value()` after `normalize()`; offerable only if total over the canonical set and round-trip stable (§7) |

---

## Sources

**Primary (fetched and section-verified this session):**
1. [SI Brochure, 9th edition] — BIPM; current v4.01 (June 2026), 102 pp., DOI 10.59161/AUEZ1291. `https://www.bipm.org/documents/20126/41483022/SI-Brochure-9-EN.pdf` (local: `/tmp/opencode/si-brochure-9.txt`). Verified: Table 1 defining constants (p. 13–14), Table 3 base units (p. 22), Table 4 derived units + footnotes (p. 23–24), §3 prefix rules (p. 28–29), Table 7 prefixes (p. 28), Table 8 non-SI units + notes (p. 30–31), §5.2 writing rules (p. 32), 11th CGPM Res. 12 / 20th CGPM Res. 8 notes (p. 50–51), 16th CGPM Res. 5/6 texts (p. 60).
2. [27th CGPM Resolution 3 (2022)] — new prefixes quetta/ronna/ronto/quecto. `https://www.bipm.org/en/committees/cg/cgpm/27-2022/resolution-3`.
3. [ISO 80000-1:2022] — Quantities and units — Part 1: General, 2nd ed., Dec 2022, 22 pp. `https://www.iso.org/standard/76921.html`.
4. [ISO 80000-3:2019] — Space and time, 2nd ed. `https://www.iso.org/standard/64974.html`.

**Empirical verification (this session):**
5. pint @ `6fc05335ef2820736efec7c5b9d55433acfb6aad` — cloned to `/tmp/opencode/pint`; `pint/default_en.txt` anchors L64–96 (24 prefixes), L75 (micro aliases μ/u/mc), L130 (micron), L162 (astronomical_unit), L169 (metric_ton), L176 (degree_Celsius), L180 (minute); `parse_units` `registry.py:1266`; `get_name` `registry.py:653`. Behavior verified live: `k`→Boltzmann, `da`→deciyear, `u`→dalton, `B`→byte, `KHz` undefined, `ms` vs `m s` whitespace-sensitive, `str(Q)`/`~Q` dual canonical forms.
6. sympy `physics.units` — cloned to `/tmp/opencode/sympy`; `PREFIXES` has 20 entries (no 2022 four); `str(kg)` = "kilogram"; no `degree_Celsius`/sievert/lumen; `Da` = `atomic_mass_constant`.
7. astropy.units (latest via uv) — partial run: case-preserving symbols; rejected `litre`, `degC`, `celsius`, `Np`, `n`.

**Project references:**
8. `docs/development/MILESTONE.md` — row 23 (SI unit; strategy LOOKUP_TABLE; provenance BIPM SI Brochure 9th ed. 2019, IEC 80000-1, ISO 80000; examples `"Kilogram"`→`"kg"`, `"Kelvin"`→`"K"`, `"megahertz"`→`"MHz"`, `"m/s²"`→`"m/s2"`, `"km/h"`→`"km/h"`).
9. `HOW_TO_ADD_NEW_CAPABILITY.md` — Steps 1–12 (this report's sections map to its steps).
10. `paxman/capabilities/Currency/` — the LOOKUP_TABLE template (structure, conventions, data patterns, registration; verified this session).
11. `docs/research/2026-08-05-money-canonicalization.md`, `docs/research/2026-08-06-url-canonicalization.md` — report house style.

**Note on counts:** the prefix table is **24**, not the 20 of the pre-2022 edition — the 27th CGPM (2022) Resolution 3 added quetta/ronna/ronto/quecto. The milestone's "IEC 80000-1" reference resolves to ISO 80000-1:2022 (dual-published with IEC/TC 25); IEC 80000-13 (binary prefixes) is explicitly out of scope.
