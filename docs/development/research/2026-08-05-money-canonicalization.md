# Money Canonicalization Research — Paxman Money Capability

**Date:** 2026-08-05
**Scope:** Primary-source survey of money notation standards (ISO 4217, Unicode
CLDR/LDML), ecosystem money libraries, and Paxman's capability architecture
(per `HOW_TO_ADD_NEW_CAPABILITY.md`, the 12-step add-a-capability guide), to
ground the design of a `Money` capability that recognizes and canonicalizes
currency+amount representations such as `USD500`, `US$50.79`, `100MYR`,
`18 Dollar`, `$500`. Localized words-to-money recognition (e.g., *"Ringgit
Malaysia Satu Ribu Ringgit Sahaja"*) is explicitly **out of scope** for the
initial capability and is reserved as a future enhancement implemented by
adding additional Grammar files. No source code, tests, or configuration were
modified.
**Evidence basis:** Live fetch of the ISO 4217 Maintenance Agency's
`list-one.xml` (SIX Financial Information, 2026-08-05), live fetch of Unicode
CLDR `cldr-json` (`cldr-numbers-full` + `cldr-core`), LDML TR35 numbers
specification, the source of established libraries (`python-babel/babel`,
`py-moneyed/py-moneyed`, `MicroPyramid/forex-python`,
`arshadkazmi42/currency-symbols`, `carlospalol/money`), and Paxman's own
architecture (`HOW_TO_ADD_NEW_CAPABILITY.md`; the IP capability as the minimal
capability skeleton; the Country capability as the lexicon/data-generation
exemplar; `tools/regenerate_isbn_range_data.py` as the regeneration-tool
pattern; `paxman/core/{domain,contract,capability,capability_contract}.py` and
`paxman/engine/orchestrator.py` for the contract surfaces). Repo state: branch
`feature/CURRENCY-capability` @ `7a4017c`.

---

## Executive Summary

Money is an excellent fit for a Paxman capability: it has an authoritative
standard with provenance-able data (ISO 4217 List One — 178 active alphabetic
codes with numeric codes and minor units), a complementary authority for the
human-facing vocabulary (Unicode CLDR — symbols, qualified symbols, display
names, number patterns), a well-understood ambiguity model (the `$` symbol is
shared by 20+ currencies — this maps directly onto Paxman's `SUCCESS` /
`AMBIGUOUS` status semantics), and a mandatory two-part intermediate
representation that matches the user's requirement exactly:
**Currency-part** and **Amount-part**.

Key findings that shape the design:

1. **The notation is `MoneyNotation(currency_part, amount_part)`.** Per the
   requirement, these two parts are mandatory; a `shape` discriminator on each
   part (following Country's `shape`+`value` pattern) lets rules route by
   representation without the grammar doing meaning. `currency_shape`
   (`"code"`/`"symbol"`/`"qualified_symbol"`/`"word"`) and `amount_shape`
   (`"integer"`/`"dot_decimal"`/`"comma_decimal"`/`"space_decimal"`/
   `"accounting"`) are optional but recommended, so `1.000,50` vs `1,000.50`
   can resolve to `AMBIGUOUS` exactly like Date's `01/02/2026`.
2. **The grammar layer is per-representation, and each grammar matches the
   complete currency+amount token.** The engine routes recognitions to rules
   by `Rule.target_grammars` and never merges two recognitions into one
   notation, so a money grammar must emit a *complete* notation — the currency
   part and the amount part together in one span (`USD500`, `US$50.79`,
   `100MYR`, `18 Dollar`, `$500` each as one `RecognitionMatch`). Three
   grammars cover the initial scope: `code_recognition` (Regex — `[A-Z]{3}`
   adjacent to an amount), `symbol_recognition` (Regex over a curated symbol
   key table compiled at module scope — qualified symbols like `US$`/`CA$`
   matched before bare `$`), and `word_recognition` (Lexicon over CLDR display
   names — `Dollar`, `Ringgit`, `Euro`). Localized words later add a fourth
   grammar file, exactly as the requirement's future-enhancement path states.
3. **Authority split: ISO 4217 owns codes and minor units; CLDR owns symbols,
   names, and number patterns.** One rule file per publication (the
   one-provenance-per-file convention): `iso_4217_ed2015.py` validates the
   currency code and supplies the canonical code + minor-unit precision
   (provenance: ISO 4217:2015); `cldr_currencies_ed2025.py` resolves symbols
   and word names to their currency code (provenance: Unicode CLDR v47).
   `$` alone is a multi-candidate token (29 currencies) resolved by the rule
   via the contract's opt-in `dollar_sign_currency` — default `None`, so bare
   `$` is `INVALID` unless the caller asserts a currency. This mirrors Phone's
   `default_country` rule parameter pattern but is default-off: the library
   never guesses the CLDR-`en` default.
4. **`$` ambiguity is a `dollar_sign_currency` decision, not a grammar
   decision.** CLDR's per-locale data is the authoritative answer: in `en`, USD
   → `$` and everything else is qualified (`CAD` → `CA$`, `AUD` → `A$`, `MXN`
   → `MX$`); in `es`, USD itself is `US$`. A bare `$` names 29 currencies, so
   the rule resolves it only through the opt-in `dollar_sign_currency`; the
   default `None` makes bare `$` `INVALID` (recognized, but no authority
   validates it) — never a guessed `SUCCESS` and never `AMBIGUOUS`. Only
   genuinely competing interpretations (e.g., separator-shape clashes on the
   amount) produce `AMBIGUOUS`, like Date.
5. **Minor-unit-aware amount parsing is a rule concern.** ISO List One's
   `CcyMnrUnts` column is authoritative: 7 currencies have 3 decimal places
   (BHD, IQD, JOD, KWD, LYD, OMR, TND), 2 have 4 (CLF, UYW), 16 have 0 (JPY,
   KRW, …). A known data discrepancy to resolve by provenance: CLDR's
   `fractions` lists IQD as 0 digits while ISO List One says 3 — ISO wins for
   a provenance-first library.
6. **No existing library is a drop-in data source.** Babel (BSD-3-Clause) is
   the only one worth using — as a **dev-time reference only**, never as a
   runtime grammar dependency. py-moneyed has the right `Currency` shape but
   stale hand-maintained data and no symbols; forex-python is incomplete (161
   of 178 codes) and network-bound; currency-symbols is one-symbol-per-code
   and cannot support recognition. Curate `rules/data/` from SIX
   `list-one.xml` (ISO) + CLDR `currencies.json` (Unicode) as plain
   maintained-in-place tables (per the repository data policy — only the ISBN
   range message is generated), citing the source URL and snapshot date in
   each module docstring.

Recommended file layout, rule set, notation, contract, and data modules are
specified in §7. Open decisions (exact canonical string shape, whether to pad
amounts to minor-unit precision, `dollar_sign_currency` semantics, symbol-grammar
mechanism) are flagged in §9 with a recommendation for each.

---

## 1. The Money Domain (HOW_TO Step 1: Plan Your Capability)

The guide's Step 1 requires answering five planning questions before writing
code. The answers for Money:

1. **What domain are you canonicalizing?** Currency + amount pairs — money
   quantities written by humans in mixed formats.
2. **What authoritative specifications govern this domain?**
   - **ISO 4217:2015** (*Codes for the representation of currencies and
     funds*) — the currency code standard; its List One (published by the
     Maintenance Agency, SIX) carries codes, numeric codes, and minor units.
   - **Unicode CLDR / LDML TR35 Part 3 (Numbers)** — symbols, qualified
     symbols, display names, and the number-pattern grammar (`¤`/`¤¤`/`¤¤¤`)
     that governs how currency and amount are placed relative to each other.
3. **What are the different ways users might write this value?** `$500`,
   `US$50.79`, `USD500`, `500 USD`, `100MYR`, `18 Dollar`, `500 Ringgit`,
   `€50`, `50,00 €`, `($1,234.57)` — each is one token in which the currency
   part (code/symbol/word) and the amount part are adjacent.
4. **What is the canonical output format?** The ISO 4217 code form —
   `CODE + amount` (e.g., `USD 500.00`), with the amount normalized to the
   currency's minor-unit precision. This is the "always-pair-with-code"
   convention ISO itself recommends for unambiguous display; see §9 for the
   exact-string decision.
5. **What is the intermediate representation?** `MoneyNotation` with the two
   mandatory parts `currency_part` and `amount_part` plus `shape`
   discriminators (see §7.1).

The canonical form is *unambiguous by construction* (unlike Date, where
`01/02/2026` legitimately means two things): a money token that names its
currency unambiguously has exactly one canonical value. Genuine ambiguity
arises only from ambiguous *amount* shapes (`1.000,50`) or a bare `$` with no
`dollar_sign_currency` opt-in — both resolve through the existing status
model (the bare-`$` case is `INVALID`, not `AMBIGUOUS`).

---

## 2. ISO 4217: the currency-code authority

### 2.1 Code structure (ISO 4217:2015)

- **Alphabetic code** — exactly 3 uppercase Latin letters. The first two
  letters are the ISO 3166-1 alpha-2 country code; the third is the first
  letter of the currency name "where possible" (`USD` = US + D, `CHF` = CH +
  F). Source: [ISO 4217 — Currency codes](https://www.iso.org/iso-4217-currency-codes.html);
  normative wording in [ISO 4217:2015 §5.1](https://cdn.standards.iteh.ai/samples/64758/bd374e5824f444d3936c81afaf9c108a/ISO-4217-2015.pdf).
- **Numeric code** — 3 digits, derived where possible from the UN country
  code; user-assigned range 900–998. Example: `USD` = 840, `EUR` = 978,
  `GBP` = 826.
- **Minor unit** — "the decimal relationship between such units and the
  currency itself (i.e. whether it divides into 100 or 1000)" — the `3` in
  `BHD` (Bahraini dinar, 3 decimal places) vs the `2` in `USD`.

### 2.2 How many active currencies?

The authoritative machine-readable list is **List One**, published by the ISO
4217 Maintenance Agency (SIX Financial Information AG, on behalf of SNV/ISO):

- `https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml`
- **Live fetch (2026-08-05):** 280 country/entity rows, **178 distinct
  alphabetic codes**. Corroborated by a SIX-sourced snapshot
  ([moneyconvert.net](https://moneyconvert.net/currency-codes/): "Active
  currencies: 178"). The ISO page's "almost 300" counts current + historical
  + funds; CLDR `en` lists 307 codes including withdrawn ones.

Counts vary by source based on exclusions — e.g., UniRateAPI's "154 active +
11 X codes" excludes the four circulating X-prefixed currencies (XAF, XCD,
XOF, XPF) and treats funds differently. **A Paxman data module should
standardize on the 178 codes in List One** — that is what the standard itself
publishes.

### 2.3 Special cases (verified in the live List One)

- **Precious metals:** XAU (gold), XAG (silver), XPD (palladium), XPT
  (platinum) — minor unit `N.A.`
- **Funds/special units:** XDR (IMF Special Drawing Right), XTS (testing),
  XXX (no currency), XBA–XBD (bond market units), XSU, XUA, XAD, XCG
  (additional funds registered with the Maintenance Agency — ISO 4217:2015
  List Two, §8.2)
- **Circulating X-prefixed currencies that must NOT be excluded:** XAF, XOF,
  XPF, XCD
- **Historic codes** live in List Three (ZWL, ROL, FRF, …):
  `https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-three.xml`

### 2.4 Which authoritative list to use

| Source | Content | Verdict |
|---|---|---|
| **SIX List One XML** ([six-group.com](https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html)) | Codes, numeric, minor units, entity | **Primary** — the maintenance agency's own machine-readable output |
| **ISO 4217:2015** ([iteh.ai preview](https://cdn.standards.iteh.ai/samples/64758/bd374e5824f444d3936c81afaf9c108a/ISO-4217-2015.pdf)) | Normative text (paywalled at iso.org) | Reference for wording; not a data feed |
| **UN/CEFACT Rec 9** ([unece.org](https://unece.org/trade/uncefact/cl-recommendations)) | Endorses ISO 4217 alpha-3; points to SIX | Policy endorsement, not a list |
| **datahub.io/core/currency-codes** | List One + List Three CSV, Public Domain | Convenient; verify against SIX |
| **Unicode CLDR** | Symbols, names, locale data, fractions | **Complementary** — ISO has no symbol/name data |

---

## 3. Currency symbols and the `$` ambiguity problem

### 3.1 The scale of the problem

The dollar sign is shared by 20+ currencies (USD, CAD, AUD, NZD, HKD, SGD,
MXN, ARS, …) — [Investopedia](https://www.investopedia.com/terms/c/currency-symbol.asp).
Other collisions: `£` (GBP + EGP, LBP, SHP, GIP, FKP, SDG, SSP), `¥` (JPY and
CNY), `C$` (CAD and Nicaraguan córdoba), `₨` (PKR, LKR, NPR, MUR, SCR).
There is **no Unicode code point per currency** — `$` is U+0024 for all of
them. A grammar cannot resolve `$` from the symbol alone; resolution is a
rule decision.

### 3.2 How real systems disambiguate `$`

**A. Locale-qualified symbols (CLDR — the authoritative answer).** CLDR's
per-locale currency data reserves the bare symbol for the locale's default
currency and qualifies the rest. Verified live in `cldr-numbers-full`:

- **en** (`main/en/currencies.json`): USD → `$`, CAD → `CA$`, AUD → `A$`,
  MXN → `MX$`, CNY → `CN¥`, MYR → `MYR` (narrow `RM`), GBP → `£`, EUR → `€`,
  JPY → `¥`, INR → `₹`
- **es** (`main/es/currencies.json`): USD → `US$`, CAD → `CAD` (narrow `$`),
  MXN → `MXN` (narrow `$`), EUR → `€`

CLDR's translation guidance states the rule explicitly: *"Never use the same
symbol for two different currencies. If '$' is used for USD, it cannot also be
used for AUD… however, in en-AU, the choices are switched: $ is AUD, and USD
is US$."* ([CLDR currency names](https://cldr.unicode.org/translation/currency-names-and-symbols/currency-names))

**B. Bare `$` defaults to the locale's currency.** Babel:
`get_currency_symbol('USD', locale='en_US')` → `'$'`;
`Locale('es','CO').currency_symbols['USD']` → `'US$'`
([babel/core.py](https://github.com/python-babel/babel/blob/master/babel/core.py)).
**For Paxman, bare `$` is not silently defaulted to USD.** The bare symbol is
shared by 29 currencies, and this library never guesses: the contract exposes
an opt-in `dollar_sign_currency` so callers assert a context explicitly (e.g.
`dollar_sign_currency="AUD"`), defaulting to `None` — bare `$` is `INVALID`
unless opted in.

**C. Country-prefix conventions in prose/finance.** The Canadian Translation
Bureau recommends `US$25.99` and `Can$`, noting finance texts use the ISO code
with a non-breaking space (`CAD 125.00`; `USD$`/`$USD` are explicitly wrong)
([Translation Bureau: American dollar](https://www.noslangues-ourlanguages.gc.ca/writing-tips-plus/american-dollar-symbol),
[Canadian dollar](https://nos-langues.canada.ca/en/writing-tips-plus/canadian-dollar-symbol)).
Common prefixes in the wild: `US$`, `CA$`/`Can$`/`C$`, `A$`, `S$`, `NT$`,
`MX$`, `AR$`, `$U` ([Investopedia](https://www.investopedia.com/terms/c/currency-symbol.asp);
[Wikipedia: Canadian dollar](https://en.wikipedia.org/wiki/CA$)). `C$` is
discouraged because it collides with the córdoba.

**D. Always-pair-with-code** is the engineering consensus for multi-currency
systems; ISO 4217 itself recommends the `USD 100` form
([UniRateAPI](https://unirateapi.com/currency-symbols)).

**Parsing implication:** a money symbol grammar must match **qualified
prefixes** (`US$`, `CA$`, `A$`, `S$`, `MX$`, `RM`, `NT$`, `CN¥`) with priority
over the bare ambiguous symbol, then fall back to bare `$` → the rule's opt-in
`dollar_sign_currency`. The qualified-prefix table can be generated from
CLDR's per-locale `symbol` fields.

---

## 4. Money written forms (the recognition matrix)

The placement of currency relative to amount is governed by CLDR/LDML number
patterns, which use the currency placeholder `¤`:

| Placeholder | Expands to | Example result |
|---|---|---|
| `¤` | localized symbol | `$1,432.00` |
| `¤¤` | ISO 4217 code | `USD 1,432.00` |
| `¤¤¤` | long display name | `1.432,00 dólares estadounidenses` |

([LDML TR35 numbers](https://unicode-org.github.io/cldr/ldml/tr35-numbers.html);
[Babel format_currency](https://babel.pocoo.org/en/latest/api/numbers.html).)
Symbol before or after the amount is a per-locale pattern decision — en_US
prefixes (`$500`), many European locales suffix (`500 €`).

The full matrix the initial grammars must recognize (each row is **one token**,
mapped to one `RecognitionMatch`):

| Form | Examples | Grammar |
|---|---|---|
| Symbol + amount (prefix) | `$500`, `€50`, `RM100` | `symbol_recognition` |
| Qualified symbol + amount | `US$50.79`, `CA$25`, `A$10` | `symbol_recognition` |
| Code + amount (either order) | `USD500`, `500 USD`, `100MYR` | `code_recognition` |
| Word + amount | `18 Dollar`, `500 Ringgit`, `500 Euro` | `word_recognition` |
| Amount + symbol (suffix) | `500 €`, `1.000,00 €` | `symbol_recognition` |
| Accounting negative | `($1,234.57)` | any (amount shape) |

Word currencies map to CLDR `displayName` values (`en/currencies.json`: "US
Dollar", "Malaysian Ringgit", "Euro", "Japanese Yen") — English word
recognition can be generated from CLDR display names. CLDR also defines
`currencyPatternAppendISO` for the explicit double-tag form `"$1,432.00 USD"`
("recommended to resolve ambiguity") — a natural optional grammar later.

---

## 5. Amount syntax

### 5.1 Integer vs decimal; thousands separators

Decimal and grouping separators are **locale-defined** (LDML `numberSymbols`),
so the same digits parse differently by locale. Babel's `parse_decimal` shows
the canonical behavior ([babel/numbers.py](https://github.com/python-babel/babel/blob/master/babel/numbers.py)):

```python
parse_decimal("1,099.98", locale="en_US")  # → Decimal('1099.98')
parse_decimal("1.099,98", locale="de")  # → Decimal('1099.98')  # European style
parse_decimal("12 345,123", locale="ru")  # → Decimal('12345.123')  # space grouping
parse_decimal("2,109,998", locale="de")  # → NumberFormatError  # wrong separator order
```

**Paxman implication:** there is no locale signal in a bare input like
`1,000.50` — the grammar must capture the raw amount span and its **shape**
(which separator is the decimal), and the rule resolves. `1.000,50` vs
`1,000.50` for a 2-decimal currency should produce `AMBIGUOUS` (the Date
`01/02/2026` pattern), unless the present currency's minor units force one
reading (a 3-decimal currency makes `1.000,50` unambiguous). `Decimal` is the
correct internal type; the canonical value is still a `str` (every
`Candidate.value` is a string).

### 5.2 Negatives

Three real forms: prefix minus `-$5`, Unicode minus `$−5` (U+2212), and the
**accounting parens** form `($5)` — a first-class CLDR pattern. Babel's en_US
`currency_formats['accounting']` is `<NumberPattern '\xa4#,##0.00;(\xa4#,##0.00)'>`
— the `;` separates positive/negative subpatterns
([babel/core.py](https://github.com/python-babel/babel/blob/master/babel/core.py)).

### 5.3 Minor units (3-decimal, 0-decimal, and the IQD discrepancy)

The authoritative minor-unit table is List One's `CcyMnrUnts` column
(verified live, 2026-08-05):

- **3 decimal places (7):** BHD, IQD, JOD, KWD, LYD, OMR, TND
- **4 decimal places (2):** CLF, UYW
- **0 decimal places (16):** BIF, CLP, DJF, GNF, ISK, JPY, KMF, KRW, PYG,
  RWF, UGX, VND, VUV, XAF, XOF, XPF
- **Metals/funds:** `N.A.` (XAU, XAG, XPD, XPT, XDR, XTS, XXX, XBA–XBD, XSU,
  XUA)
- Everything else: 2

**Known data discrepancy to flag:** CLDR `supplemental/currencyData.json`
`fractions` says **IQD has 0 digits**, while ISO List One says **IQD minor
unit = 3** (verified live in both files). For a provenance-first library,
**ISO is the authority for minor units**; CLDR is the authority for
symbols/names/patterns. Where they disagree, that is a provenance decision,
not a merge. CLDR also adds cash-rounding nuance (HUF `_cashRounding: 5`) that
ISO does not carry — out of scope for canonical parsing.

---

## 6. Existing Python libraries (data-source suitability)

| Library | License | Symbols | Names | Numeric | Minor units | Locale-aware | Authority | Verdict for Paxman |
|---|---|---|---|---|---|---|---|---|
| **Babel** | BSD-3-Clause | ✅ per-locale (`CA$`, `US$`) | ✅ per-locale | ❌ | ❌ | ✅ | CLDR (generated) | **Dev-time regenerator** for symbol/name/pattern data |
| **py-moneyed** | BSD-3-Clause | ❌ | ✅ (via Babel) | ✅ | ✅ (`sub_unit`) | partial | Hand table + old ISO FAQ | Reuse the *data shape*, not the data |
| **python-money (money)** | MIT | via Babel | via Babel | ❌ | ❌ | ✅ | None bundled | Avoid (abandoned since ~2023) |
| **forex-python** | MIT | ✅ (161/178, incomplete) | ✅ (hand) | ❌ | ❌ | ❌ | Hand-curated JSON | Avoid (incomplete, network-bound) |
| **currency-symbols** | MIT | ✅ (1 per code) | ❌ | ❌ | ❌ | ❌ | Static dict | Insufficient alone (no reverse disambiguation) |
| **SIX list-one.xml** | free | ❌ | ❌ | ✅ | ✅ | ❌ | **ISO 4217 MA** | **Primary for codes/numeric/minor units** |
| **CLDR cldr-json** | Unicode-3.0 | ✅ | ✅ | ❌ | ✅ (`fractions`) | ✅ | Unicode CLDR | **Primary for symbols/names** |

Details:

- **Babel** ([github](https://github.com/python-babel/babel)) — full CLDR-backed
  i18n; its own data file is generated from CLDR by `scripts/import_cldr.py`.
  The right role is dev-time only (spot-checking curated tables), never a
  runtime grammar dependency — Paxman's data modules are plain tables
  maintained in place, with only the ISBN range message generated.
- **py-moneyed** ([github](https://github.com/py-moneyed/py-moneyed)) — `Currency`
  fields `code, numeric, sub_unit, name, countries` is the right data shape,
  but **no symbol field**, hand-maintained data citing an old ISO FAQ URL,
  last push April 2024.
- **python-money / "money"** ([github](https://github.com/carlospalol/money/)) —
  explicitly ships **no** currency database ("There is no need for a currency
  class… CLDR via Babel is the database"); abandoned. Its design stance is the
  argument for Paxman's generate-from-CLDR approach.
- **forex-python** ([github](https://github.com/MicroPyramid/forex-python)) —
  `raw_data/currencies.json` verified as a 161-entry hand-curated list;
  reverse `symbol → code` is a first-match scan that cannot disambiguate `$`.
- **currency-symbols** ([pypi](https://pypi.org/project/currency-symbols/)) —
  forward-only code→symbol; cannot support recognition of an ambiguous symbol.

**Conclusion:** no library supplies Paxman-ready data. Curate two modules —
ISO from SIX `list-one.xml`, CLDR from `cldr-json` — as plain
maintained-in-place tables, and keep the runtime dependency surface at zero.

---

## 7. Paxman Architectural Mapping (HOW_TO Steps 2–10)

This section maps the Money design onto the 12-step guide's requirements. All
naming, signature, and boundary rules below are the guide's own conventions
(`HOW_TO_ADD_NEW_CAPABILITY.md`, steps 2–10, 12).

### 7.1 Directory structure (Step 2) and Notation (Step 3)

```
paxman/capabilities/Money/
├── __init__.py            # exports MoneyCapability, MoneyContract, MoneyNotation
├── notation.py            # MoneyNotation — frozen, slots=True
├── contract.py            # MoneyContract(CapabilityContract)
├── capability.py          # MoneyCapability(Capability[MoneyNotation])
├── grammar/
│   ├── __init__.py
│   ├── code_recognition.py       # Regex: [A-Z]{3} + amount
│   ├── symbol_recognition.py     # Regex over key-only symbol table (qualified first)
│   ├── word_recognition.py       # Lexicon: CLDR display names + amount
│   └── data/
│       ├── __init__.py
│       ├── currency_symbols.py   # key-only: {"$", "US$", "CA$", "RM", …}
│       └── currency_words.py     # key-only: {"DOLLAR", "RINGGIT", "EURO", …}
└── rules/
    ├── __init__.py
    ├── iso_4217_ed2015.py        # PUBLICATION: ISO 4217:2015 — codes + minor units
    ├── cldr_currencies_ed2025.py # PUBLICATION: Unicode CLDR — symbols/words → code
    └── data/
        ├── __init__.py
        ├── iso4217_list_one.py   # plain table, curated from SIX snapshot
        └── cldr_currencies.py    # plain table, curated from CLDR
```

```python
# notation.py
@dataclass(frozen=True, slots=True)
class MoneyNotation:
    """Money notation: a currency part and an amount part (both mandatory)."""

    currency_part: str  # recognized currency token: "USD", "$", "US$", "Dollar"
    amount_part: str  # recognized amount token: "500", "50.79", "1,000.50"
    currency_shape: str = ""  # discriminator: "code"|"symbol"|"qualified_symbol"|"word"
    amount_shape: str = ""  # discriminator: "integer"|"dot_decimal"|"comma_decimal"|"space_decimal"|"accounting"

    def as_list(self) -> list[str]:
        return [
            self.currency_part,
            self.amount_part,
            self.currency_shape,
            self.amount_shape,
        ]
```

This satisfies the guide's notation rules: frozen, `slots=True` (newer
capability convention; IP/Email are legacy without slots), every field a `str`,
named-field access for rules, and the optional `as_list()` generic-interface
helper. The two mandatory parts match the requirement; the shape fields follow
Country's `shape`+`value` discriminator pattern (Country
`notation.py`, `CountryNotation(shape, value)`).

### 7.2 Grammar layer (Step 4)

Per the guide's strategy decision table, Money is a "both" capability — one
grammar per strategy:

| Grammar (`name`) | Strategy | Recognizes | Emits |
|---|---|---|---|
| `code_recognition` | **Regex** | `USD500`, `500 USD`, `100MYR` — `[A-Z]{3}` adjacent to an amount, either order (suffix form only when no prefix-form claims the amount — D6) | `currency_part` = uppercased code, `currency_shape="code"` |
| `symbol_recognition` | **Regex over key table** | `$500`, `US$50.79`, `500 €`, `RM100` — symbol/qualified-symbol adjacent to an amount | `currency_part` = raw symbol token, `currency_shape="qualified_symbol"`/`"symbol"` |
| `word_recognition` | **Lexicon** | `18 Dollar`, `500 Ringgit` — CLDR display-name key adjacent to an amount | `currency_part` = trimmed raw token, `currency_shape="word"` |

**Single-currency precedence (D6, locked):** exactly one currency per amount. When a
prefix-form recognition (`symbol_recognition`/`word_recognition`) claims an amount, the
suffix-form recognition (`code_recognition`) of that same amount is suppressed — prefix
always wins, suffix is recognized only when no prefix is present. `$1,432.00 USD` →
`USD 1,432.00` via the `$` (trailing `USD` is non-matching context), never `AMBIGUOUS`,
never two currency parts. There is **no** `currency_pattern_append_iso` grammar in v1.

Each grammar compiles its regex once at module scope (never inside
`recognize()`) and returns span-bearing `RecognitionMatch` objects with
`len(raw_text) == end - start` and `raw_text == text[start:end]` holding. No
grammar validates, dedups, orders, or maps a token to a canonical value — the
engine owns containment dedup ("longer wins") and total ordering; rules own
meaning. The `currency_shape`/`amount_shape` discriminators are syntactic
(normalized at recognition), exactly like Country's grammars uppercasing
tokens — no semantic decisions leak into the grammar layer.

**Key design point (why one grammar matches the whole token):** the engine
routes each recognition to rules via `Rule.target_grammars` and never merges
two recognitions into one notation, so a money grammar must emit a *complete*
`MoneyNotation` in one span. Splitting "currency grammar" and "amount grammar"
would leave both notations half-empty and unvalidatable. The grammar split is
therefore **by currency representation** (code/symbol/word), each pairing its
representation with the amount — and the requirement's future enhancement
("adding additional Grammar files that support localized words") slots in
exactly here as a fourth grammar, e.g. `localized_word_recognition`.

**Symbol grammar mechanism (recommended):** compile the alternation at module
scope from the key-only table with qualified symbols first
(`(?:US\$|CA\$|A\$|RM|…|\$)`) so the longest/qualified form wins per span;
bare `$` remains a key the **rule** resolves via the opt-in
`dollar_sign_currency`. (The
guide's alternative of `\p{Sc}` Unicode-property matching is explicitly
discouraged there for curated vocabularies: "\p{Emoji} is too broad… use
key-set tables" — the same reasoning applies to currency symbols.)

**Word grammar mechanism (recommended):** mirror Country's `name_recognition`
Lexicon exemplar — normalize the token with a shared `normalize_name()`-style
helper (NFKD → separator-fold → case-fold), test membership in a key-only
frozenset in `grammar/data/currency_words.py`, emit the trimmed raw token with
`currency_shape="word"`. Rules own token→code meaning via CLDR.

### 7.3 Rule layer (Step 5) — one publication per file

Two rule files, each with a single module-level `PUBLICATION` (the
one-provenance-per-file pattern):

**`rules/iso_4217_ed2015.py`** — the currency-code authority:

```python
PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 4217:2015",
    kind="registry",  # List One is a registry of the standard
    reference_url="https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html",
    version="2015",  # or the List One publish date
    lifecycle="active",
    publication_year=2015,
)
```

- `SectionCurrencyCodes` — strategy `LOOKUP_TABLE`; `target_grammars =
  frozenset({"code_recognition"})`; `requires_features = frozenset()`.
  `matches()`: the code is in the ISO 4217 table (via the shared normalizer,
  uppercased). `normalize()`: returns the canonical `CODE + amount` string.
- `SectionMinorUnits` — strategy `LOOKUP_TABLE`; `target_grammars =
  frozenset({"code_recognition", "symbol_recognition", "word_recognition"})`
  (minor-unit precision applies to every representation). Supplies the
  authoritative `CcyMnrUnts` for amount normalization/quantization.

**`rules/cldr_currencies_ed2025.py`** — the symbol/name authority:

```python
PUBLICATION = Provenance(
    authority="Unicode",
    specification_name="CLDR v47",
    kind="registry",
    reference_url="https://cldr.unicode.org/",
    version="47",
    lifecycle="active",
    publication_year=2025,
)
```

- `SectionCurrencySymbols` — strategy `LOOKUP_TABLE`; `target_grammars =
  frozenset({"symbol_recognition"})`. `matches()`: the symbol/qualified symbol
  is in the CLDR-derived symbol table. `normalize()`: resolves symbol →
  code via the authority table; bare `$` resolves via the contract's
  `dollar_sign_currency` (cast, Phone's `default_country` pattern).
- `SectionCurrencyWords` — strategy `LOOKUP_TABLE`; `target_grammars =
  frozenset({"word_recognition"})`. `matches()`: the word is in the
  CLDR-derived name table. `normalize()`: word → code.

Both files follow the guide's rule conventions: six metadata attrs enforced by
`Rule.__init_subclass__` (missing → `TypeError` at import); `matches()` and
`normalize()` never raise; `normalize()` never reads `output_format` (CI
source scan enforces the token's absence in rule modules); feature gating via
`requires_features`, never inside `matches()`.

**Amount resolution is distributed:** the *grammar* captures the amount shape;
`SectionCurrencyCodes`/`SectionCurrencySymbols`/`SectionCurrencyWords`
normalize the amount using the minor-unit rule's precision table. Ambiguous
separator shapes (`1.000,50` with a 2-decimal currency) yield distinct
canonical values across the interpretation → `AMBIGUOUS`, exactly like Date.
For a 3-decimal currency, `1.000,50` is forced (only one valid reading), so
it resolves `SUCCESS` — the rule encodes the constraint, not the grammar.

### 7.4 Capability and Contract (Steps 6–7)

**`capability.py`** — `MoneyCapability(Capability[MoneyNotation])`:
`name = "money"`, `version = "1.0.0"`; `get_grammars()` returns the three
grammar instances; `get_rules()` returns the four rule instances; static
`create_contract()` opens with the unanimous keyword-only common block
(`excluded_rules`, `pinned_rules`, `year`, `output_format`) followed by
capability-specific params; `format_value()` implements the presentation seam
for offered formats (identity for the default).

**`contract.py`** — `MoneyContract(CapabilityContract)`,
`@dataclass(frozen=True)` (no slots — contract rule):

```python
@dataclass(frozen=True)
class MoneyContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "code_amount"  # CODE + amount
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact"})

    capability_name: str = field(default="money", init=False)
    precision: Literal["strict", "truncate", "round"] = "strict"
    dollar_sign_currency: str | None = None  # bare "$" resolution (opt-in)

    @property
    def active_grammars(self) -> tuple[str, ...]:
        return ("code_recognition", "symbol_recognition", "word_recognition")

    def _extra_dict_fields(self) -> dict[str, object]:
        return {
            "precision": self.precision,
            "dollar_sign_currency": self.dollar_sign_currency,
        }
```

`dollar_sign_currency` is a rule *parameter* (read via `typing.cast` in the
symbol rule, like Phone's `default_country`), not a feature-toggle flag — it
affects validity/resolution, and no `requires_features` entry is needed for
it. `output_format` is inherited (`str | None = None`, resolved in base
`__post_init__` via `resolve_output_format`); the `"compact"` offered format
removes the separator space (`USD500.00`) but cannot change candidates — the
presentational-only invariant. `_extra_dict_fields()` includes `precision` and
`dollar_sign_currency` so the replay hash reflects the resolution policy.

### 7.5 Registration and exports (Steps 8–9)

- `paxman/capabilities/Money/__init__.py` exports `MoneyCapability`,
  `MoneyContract`, `MoneyNotation` in `__all__`.
- `paxman/capabilities/__init__.py` adds
  `from paxman.capabilities.Money.capability import MoneyCapability as Money`
  and `"Money"` to `__all__`.
- `tests/unit/test_capability_exports.py` gains the enforced export check
  (`Money is not None`, `Money.name == "money"`).
- Users register at runtime: `register_capability(Money())` — there is no
  self-registration in Paxman.

### 7.6 Tests (Step 10)

Four layers per the guide:
- `tests/capabilities/money/test_grammar.py` — per grammar: recognizes valid
  input, variants, multiple matches, ignores incompatible formats, empty
  input; markers `capability` + `money`.
- `tests/capabilities/money/test_rules.py` — per rule: matches valid,
  variant-valid, rejects invalid; normalize produces canonical; provenance
  attributes; rule name; strategy.
- `tests/capabilities/money/test_capability.py` — notation (frozen, equality,
  hashable, `as_list` order) + wiring (subclass, name, version, grammar/rule
  counts).
- `tests/integration/test_pipeline.py` + `tests/e2e/test_canonicalize.py` —
  full pipeline via `run_capability()`/`canonicalize()`: SUCCESS
  (`USD500` → `USD 500.00`), MISSING (no money token), INVALID (recognized but
  unvalidated — e.g. an amount-only token), AMBIGUOUS (`1.000,50` with a
  2-decimal currency), version stamp determinism; `_clean_registry` autouse
  fixture; inline `register_capability(Money())` per test.
- `tests/capabilities/money/test_data_consistency.py` — the guide's mandated
  consistency test: every recognition key in `grammar/data/` is covered by at
  least one rule-data mapping (see §7.8).

### 7.7 Data modules (Step 2 optional; ISBN/Country precedents)

Two plain data modules under `rules/data/`, maintained in place per the
repository data policy (AGENTS.md: only the ISBN range message is generated —
via `tools/regenerate_isbn_range_data.py`; unmarked data files are edited
directly), following the Country `rules/data/` layout:

- `rules/data/iso4217_list_one.py` — plain table of the ISO 4217 List One
  snapshot (source URL + snapshot date cited in the docstring). Exports:
  `CURRENCY_CODES` (frozenset of the 165 codes with a numeric minor-unit
  exponent; the 13 `N.A.` codes — metals/funds — are excluded, with no usable
  minor units), `MINOR_UNITS: dict[str, int]` (exponent per code).
- `rules/data/cldr_currencies.py` — plain table of the CLDR v47 English +
  Spanish currency data (`main/en/currencies.json` plus `es` for the `US$`
  qualified form, matching the CLDR `symbol` fields). Exports:
  `SYMBOL_TO_CODES` (symbol → sorted tuple of codes, incl. qualified forms,
  longest first), `NAME_TO_CODES` (normalized display-name keys → code).

**Known data discrepancy:** CLDR `fractions` disagrees with ISO List One on
IQD (0 vs 3 minor digits). The module keeps the ISO value — IQD minor units
3 — because ISO List One is authoritative for minor units.

### 7.8 Consistency test (the grammar/rule boundary, enforced)

Following Country's `tests/capabilities/country/test_data_consistency.py`,
Money ships a one-directional coverage assertion: every key in
`grammar/data/currency_symbols.py` ∪ `grammar/data/currency_words.py` is
covered by the union of rule-data mapping keys (`SYMBOL_TO_CODES`,
`NAME_TO_CODES`), with per-authority ownership tests (symbols → CLDR only;
words → CLDR only; codes → ISO only). This is the test that lets the two
catalogs drift independently without breaking shipped behavior — and the
exact seam the future localized-words grammar will plug into (its keys must
be covered by the extended CLDR rule data).

---

## 8. Out of scope: localized words-to-money (future enhancement)

The requirement explicitly defers *"Ringgit Malaysia Satu Ribu Ringgit
Sahaja"* to a future enhancement, implemented "just by adding additional
Grammar files that support localize words to money conversion." The
architecture above is deliberately shaped so this is a **pure additive
change**:

1. **New grammar file:** e.g. `grammar/localized_word_recognition.py`
   (Lexicon strategy over a key-only table of normalized localized currency
   words — `RINGGIT MALAYSIA`, `RINGGIT`, …). It pairs the localized word with
   its amount and emits the same `MoneyNotation` with a new
   `currency_shape="localized_word"`.
2. **Extended CLDR rule data:** `rules/data/cldr_currencies.py` gains a
   `LOCALIZED_WORD_TO_CODE` mapping (generated from per-locale CLDR display
   names), and `cldr_currencies_ed2025.py` gains a rule targeting the new
   grammar — or a new rule file if the provenance differs (e.g. a specific
   locale authority).
3. **Consistency test extension:** the new recognition keys must be covered by
   the extended rule data — the §7.8 test enforces this automatically.
4. **Optional feature gate:** a contract flag (e.g. `include_localized`)
   toggling the grammar via `active_grammars` and gating the rule via
   `requires_features`, following Country's `include_localized` exactly.

Two sub-problems in the example belong to *different* future grammars and
should be called out so the scope boundary stays honest: (a) the currency
word itself (`Ringgit Malaysia` → MYR) is the localized-word grammar above;
(b) the *number words* (`Satu Ribu` → 1000) are a number-in-words grammar —
an orthogonal recognition problem (English already has "one thousand" forms)
that would be its own grammar file over the amount part. Neither is needed for
the initial capability; both slot into the per-representation grammar
architecture without touching existing files' contracts.

---

## 9. Open decisions (with recommendations)

**ALL RESOLVED** (locked 2026-08-05 — decisions 1–7, including sub-decisions 2a/2b/4a).

### Resolved

- **D1 — Canonical string shape: `CODE + " " + amount`** with a single ASCII space, e.g.
  `USD 500.00`. Compact `USD500.00` is offered as an alternative presentation via the
  existing `output_format` seam: `default_format="code_amount"`, `offered_formats={"compact"}`.
  Matches the established per-capability pattern (Country `alpha2`+`alpha3`/`numeric`/`name`,
  Phone `e164`+`rfc3966`/`national`, ISBN `isbn13`+`hyphenated`).
- **D2 — Pad amounts to ISO 4217 minor-unit precision:** `500` → `500.00` (2dp majority);
  3dp for BHD, IQD, JOD, KWD, LYD, OMR, TND; 4dp for CLF, UYW; 0dp for JPY, KRW and the other
  zero-decimal currencies. Deterministic: `$500` and `$500.00` canonicalize to the identical
  value; round-trip stable.
- **D2a — Over-precision input** (e.g. `USD 500.123`): caller-selectable contract argument
  `precision`, accepted values:
  - `"strict"` — reject non-conforming input: `USD 50.123` → `INVALID`, `JPY 499.8` → `INVALID`
  - `"truncate"` — cut to the allowed precision: `USD 400.123` → `USD 400.12`, `JPY 78.9` → `JPY 78`
  - `"round"` — round to the allowed precision: `USD 400.599` → `USD 400.60`, `USD 100.512` → `USD 100.51`
- **D2b — `precision` default is `"strict"`** (reject over-precision input unless the caller
  opts into `"truncate"`/`"round"`). Aligns with the codebase's conservative `include_*`
  default-off posture: rounding/truncation silently change the value, so they are explicit opt-ins.
- **D3 — `dollar_sign_currency: str | None = None`**: bare `$500` is `INVALID` by default
  (recognized, but no authority validates a 29-way-ambiguous symbol — never a guessed
  `SUCCESS`, never `AMBIGUOUS`); the caller opts in with an ISO 4217 alpha-3 code
  (`dollar_sign_currency="MYR"` → `MYR 500.00` (`SUCCESS`)) to assert a context for
  bare/shared symbols (Phone `default_country` precedent, but default-off); the override
  never remaps symbols with a definitive `en` meaning (`¥` → JPY stays, `RM` is MYR's own
  symbol). This supersedes the research draft's `default_currency="USD"` (CLDR-`en` default):
  Paxman does not guess, so the CLDR-`en` bias became an explicit opt-in.
- **D4 — Symbol grammar mechanism: key-table regex alternation**, compiled once at module
  scope from generated data tables (`SYMBOL_TO_CODE`, `QUALIFIED_TO_CODE`), every token
  `re.escape()`d, longest-first alternation (qualified `CA$`/`A$`/`CN¥` before bare `$`).
  Curated CLDR vocabulary (never `\p{Sc}`), plain key tables maintained in place per the
  repository data policy (only the ISBN range message is generated).
- **D4a — Symbol → code mapping lives in the rule layer.** The grammar emits only the raw
  token (`currency_part="$"`); the CLDR rule resolves `$` → `USD` via the tables. Preserves
  the core boundary: grammars never map tokens to canonical values.
- **D5 — One `cldr_currencies_ed2025.py` with two rule classes** (`SectionSymbols` resolves
  `$` → `USD`; `SectionNames` resolves `Dollar` → `USD`). Mirrors `iso_3166_ed2024.py`
  (one publication, multiple `Section*` classes); enables independent pinning/exclusion of
  symbol vs word validation; one provenance citation for CLDR v47.
- **D6 — Single-currency recognition, prefix prioritized; no `currency_pattern_append_iso`
  grammar.** An amount is resolved to **exactly one currency**: a **prefix** indicator
  (`$1,432.00`) always wins; a **suffix** indicator (`1,432.00 USD`) is recognized only
  when no prefix is present; never both. `$1,432.00 USD` → `USD 1,432.00` via the `$`
  (the trailing `USD` is non-matching context), never `AMBIGUOUS`. This precedence rule is
  enforced at the grammar layer (see §7.2): when a prefix-form recognition (symbol/word)
  claims an amount, the suffix-code recognition of that same amount is suppressed — no
  dedicated append-ISO grammar ships in v1; `1,432.00 USD` is covered by `code_recognition`.
- **D7 — No `include_localized` gate in v1.** `Money.create_contract()` takes only
  `excluded_rules`, `pinned_rules`, `year`, `output_format`, `precision`,
  `dollar_sign_currency`. The gate arrives *with* the localized grammar later as a
  non-breaking additive change (Phone `default_country`, ISBN `include_range_validation`
  precedent). No dead configuration knob: Country's gate exists only because its CLDR rule
  exists.

### Closed design summary (v1 contract surface)

```python
Money.create_contract(
    excluded_rules: Sequence[str] | None = None,
    pinned_rules: Sequence[str] | None = None,
    year: int | None = None,
    output_format: str | None = None,      # None/"default"/"code_amount" → "code_amount"
                                           # "compact" → offered format
    precision: str | None = None,          # None/"strict" → "strict"
                                           # "truncate" / "round" → opt-in leniency
    dollar_sign_currency: str | None = None,  # None → bare $ is INVALID
)
```

Canonical: `CODE + " " + amount` padded to ISO 4217 minor units (`USD 500.00`,
`BHD 500.000`, `JPY 1000`); `output_format="compact"` → `USD500.00`.
Grammars: `code_recognition`, `symbol_recognition`, `word_recognition` (prefix-priority
single-currency, D6). Rules: `iso_4217_ed2015.py` (codes + minor units),
`cldr_currencies_ed2025.py` (`SectionSymbols` + `SectionNames`). Data: plain
`rules/data/` modules maintained in place (only the ISBN range message is
generated).

---

## Sources (primary, verified 2026-08-05)

1. ISO 4217 standard page — https://www.iso.org/iso-4217-currency-codes.html
2. ISO 4217:2015 normative text (preview) — https://cdn.standards.iteh.ai/samples/64758/bd374e5824f444d3936c81afaf9c108a/ISO-4217-2015.pdf
3. SIX Maintenance Agency page (List One XLS/XML) — https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html
4. SIX List One XML (fetched; 280 rows, 178 codes, minor units) — https://www.six-group.com/dam/download/financial-information/data-center/iso-currrency/lists/list-one.xml
5. UN/CEFACT Rec 9 — https://unece.org/trade/uncefact/cl-recommendations
6. Unicode CLDR — https://cldr.unicode.org/ ; cldr-json — https://github.com/unicode-org/cldr-json ; npm cldr-numbers-full (Unicode-3.0 license) — https://registry.npmjs.org/cldr-numbers-full
7. CLDR currency names/symbols translation rules (en-AU switch; never reuse a symbol) — https://cldr.unicode.org/translation/currency-names-and-symbols/currency-names
8. LDML TR35 Part 3 (Numbers; `¤` patterns, negative subpatterns, `currencyPatternAppendISO`) — https://unicode-org.github.io/cldr/ldml/tr35-numbers.html
9. Babel numbers API — https://babel.pocoo.org/en/latest/api/numbers.html ; numbers.py — https://github.com/python-babel/babel/blob/master/babel/numbers.py ; core.py — https://github.com/python-babel/babel/blob/master/babel/core.py ; CLDR import script — https://github.com/python-babel/babel/blob/d7a7589a/scripts/import_cldr.py
10. py-moneyed — https://github.com/py-moneyed/py-moneyed (classes.py: https://github.com/py-moneyed/py-moneyed/blob/master/src/moneyed/classes.py ; PyPI: https://pypi.org/project/py-moneyed/)
11. python-money / "money" — https://github.com/carlospalol/money/ ; PyPI: https://pypi.org/project/money/
12. forex-python — https://github.com/MicroPyramid/forex-python ; converter.py — https://github.com/MicroPyramid/forex-python/blob/master/forex_python/converter.py
13. currency-symbols — https://pypi.org/project/currency-symbols/ ; https://github.com/arshadkazmi42/currency-symbols
14. `$` disambiguation: Canadian Translation Bureau (US$/Can$) — https://www.noslangues-ourlanguages.gc.ca/writing-tips-plus/american-dollar-symbol and https://nos-langues.canada.ca/en/writing-tips-plus/canadian-dollar-symbol ; Investopedia — https://www.investopedia.com/terms/c/currency-symbol.asp ; Wikipedia CAD — https://en.wikipedia.org/wiki/CA$ ; UniRateAPI symbols — https://unirateapi.com/currency-symbols
15. datahub.io consolidated ISO 4217 CSV — https://datahub.io/core/currency-codes
16. Paxman: HOW_TO_ADD_NEW_CAPABILITY.md (repo root, 12-step add-a-capability guide) — https://github.com/nexusnv/paxman-python/blob/7a4017c/HOW_TO_ADD_NEW_CAPABILITY.md
17. Paxman regeneration-tool pattern — https://github.com/nexusnv/paxman-python/blob/7a4017c/tools/regenerate_isbn_range_data.py

**Note on counts:** the "154 active" figure some references cite excludes the
four circulating X-prefixed currencies and funds; the live SIX List One fetch
(178) is the number a Paxman data module should standardize on. Minor-unit
data and the IQD discrepancy were verified directly against both live sources.
