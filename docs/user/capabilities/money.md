---
title: "Money"
---

Canonicalizes **one money amount paired with a currency** per call to `CODE amount` padded to ISO 4217 minor units.

> **In plain language:** give it `"USD500"` or `"1.000,50 EUR"` and it hands back `"USD 500.00"` / `"EUR 1000.50"` if the specs say the amount and currency go together. Currency without an amount — or an amount without a currency — is not Money's domain (see [Currency](currency/)).

---

## What it recognizes — and what it does not

| Recognizes (currency + amount adjacent) | Does not recognize |
|-----------------------------------------|--------------------|
| `USD500`, `USD 500.00`, `EUR 1.000,50` | Currency identifier alone (`USD`) — use [Currency](currency/) |
| `€500`, `¥1000`, `US$ 500` (qualified symbol) | Bare shared symbol without disambiguation (`$500` with default contract) — recognized but `INVALID` |
| `1.000,50 EUR` — European comma-decimal: last separator is the decimal point | Amount-glued tokens without a clean boundary — `MISSING` |
| `$500` with `dollar_sign_currency="USD"` — opt-in for shared symbols | Bare `$` without `dollar_sign_currency` — `INVALID` |

> Shared symbol handling mirrors Currency's `default_currency` idea but for amounts: Money uses `dollar_sign_currency` (same semantics, different name because it shapes amounts).

---

## Canonical output

Default `output_format` is `"code_amount"` (space between code and amount).

| `output_format` | Renders | Example for USD 500 |
|-----------------|---------|---------------------|
| *(default)* `code_amount` / `None` / `"default"` | `CODE + space + amount` | `USD 500.00` |
| `compact` | removes the single space | `USD500.00` |

The amount is padded/normalized to the currency's ISO 4217 minor units (e.g. 2 decimals for USD/EUR). How over-precision is handled depends on `precision` (see contract).

```python
from paxman.capabilities import Money
import paxman

paxman.register_all_shipped()
# Money.create_contract() is a contract — use paxman.canonicalize() to get a result
paxman.canonicalize(
    "USD500", Money.create_contract()
).canonicalized_value  # "USD 500.00"
paxman.canonicalize(
    "USD500", Money.create_contract(output_format="compact")
).canonicalized_value  # "USD500.00"
paxman.canonicalize(
    "1.000,50 EUR", Money.create_contract()
).canonicalized_value  # "EUR 1000.50"
```

---

## Contract

```python
contract = Money.create_contract(
    dollar_sign_currency=None,  # str | None — uppercase alpha-3, e.g. "USD"
    precision="strict",  # "strict" (default) | "truncate" | "round" — over-precision policy
    output_format=None,  # "code_amount" (default) or "compact"
    # plus every common field: excluded_rules / pinned_rules / year / extra_grammars
)
```

- **`dollar_sign_currency`**: when `None` (default), a multi-candidate bare symbol amount like `$500` is recognized but never resolved → `INVALID`. When set, bare `$`/`¥`/`£` resolve to that code (any ISO 4217 code with minor units; e.g. `MYR` or `EUR` both work). `€500` never needs this — `€` is definitive for `EUR` and ignores `dollar_sign_currency`; qualified symbols like `US$`/`CA$` are also definitive. An unknown code like `ZZZ` stays `INVALID` via the minor-unit guard.
- **`precision`**: how to treat more fractional digits than the currency's minor units allow — `strict` rejects → `INVALID`, `truncate` drops excess digits, `round` half-to-even.
- `output_format` never affects validation — only the space.

```python
paxman.canonicalize("$500", Money.create_contract()).status.value  # "invalid"
paxman.canonicalize(
    "$500", Money.create_contract(dollar_sign_currency="USD")
).canonicalized_value  # "USD 500.00"
# Bare "$" resolves to any requested code with minor units (loose, tested with MYR/EUR)
paxman.canonicalize(
    "$500", Money.create_contract(dollar_sign_currency="MYR")
).canonicalized_value  # "MYR 500.00"
# Unknown code never resolves — INVALID via MINOR_UNITS guard
paxman.canonicalize(
    "$500", Money.create_contract(dollar_sign_currency="ZZZ")
).status.value  # "invalid"
paxman.canonicalize(
    "USD 1.999", Money.create_contract(precision="strict")
).status.value  # "invalid" — too many decimals for USD
paxman.canonicalize(
    "USD 1.999", Money.create_contract(precision="round")
).canonicalized_value  # "USD 2.00"
```

---

## Statuses

| Input | Contract | Status | Why |
|-------|----------|--------|-----|
| `USD500` | defaults | `SUCCESS` | → `USD 500.00` |
| `€500` | defaults | `SUCCESS` | → `EUR 500.00` (definitive symbol) |
| `$500` | defaults | `INVALID` | shared symbol, no `dollar_sign_currency` |
| `$500` | `dollar_sign_currency="USD"` | `SUCCESS` | → `USD 500.00` |
| `1.000,50 EUR` | defaults | `SUCCESS` | European comma-decimal → `EUR 1000.50` |
| `USD 1.999` | `precision="strict"` | `INVALID` | over-precision → rejected |
| `hello` | any | `MISSING` | no Money pattern |
| Two different amounts | any | raises `MultipleMentionsError` | split first |

```mermaid
flowchart TB
    A[Text e.g. $500] --> G[Grammars:<br>code / symbol / word + amount]
    G --> R{Rules: ISO 4217 +<br>CLDR symbols/names<br>+ minor units}
    R -->|definitive symbol<br>or code/word| OK[SUCCESS<br>CODE amount]
    R -->|shared symbol<br>needs dollar_sign_currency| INV[INVALID<br>or SUCCESS if matches]
    R -->|over-precision + strict| INV2[INVALID]
    G -->|no pattern| MISS[MISSING]

    style OK fill:#e6ffed,stroke:#2d8a4e
    style INV fill:#fff5f5,stroke:#cc3333
    style INV2 fill:#fff5f5,stroke:#cc3333
    style MISS fill:#fff5f5,stroke:#cc3333
```

---

## Notebook snippet — clean a column with mixed formats

```python
import paxman
from paxman.capabilities import Money
from paxman.core.domain import Resolution
from paxman.core.errors import CapabilityError, ContractError, MultipleMentionsError

paxman.register_all_shipped()
c_strict = Money.create_contract()
c_usd = Money.create_contract(dollar_sign_currency="USD")
c_round = Money.create_contract(precision="round")

rows = ["USD500", "€500", "$500", "1.000,50 EUR", "USD 1.999", "hello"]

for text in rows:
    for label, c in [("strict", c_strict), ("USD bare-$", c_usd), ("round", c_round)]:
        try:
            r = paxman.canonicalize(text, c)
        except (MultipleMentionsError, CapabilityError, ContractError) as e:
            print(f"{text!r:15} [{label:10}] → exception {type(e).__name__}: {e}")
            continue
        val = r.canonicalized_value if r.status == Resolution.SUCCESS else "—"
        print(f"{text!r:15} [{label:10}] → {r.status.value:10} {val!r}")
```

---

## Provenance

- **ISO 4217:2015** — currency codes and minor units (List One, as amended through #180, snapshot 2026-01-01 via SIX; provenance `PUBLICATION` year 2015, `https://www.iso.org/iso-4217-currency-codes.html`). `CURRENCY_CODES` holds 165 codes with numeric minor units (13 N.A. codes excluded); `MINOR_UNITS` maps exponent (0 for JPY/KRW, 2 for most, 3 for BHD, 4 for CLF/UYW).
- **Unicode CLDR v47 (2025-03-13)** — currency symbols and English display names (`https://cldr.unicode.org/`, `https://cldr.unicode.org/downloads/cldr-47`). Word recognition is case-insensitive (any casing of `Euro`/`euro`/`EURO` resolves to `EUR`); symbols are case-exact (`lei` vs `Lei`). Newer CLDR v48/48.1 (2025-10 and 2026-01) exists — regeneration planned via `tools/regenerate_currency_data.py`.
- Amount parsing: last separator wins, single separator always decimal (`1,00` → `1`, `1.234` → `1.234`); grouping with multiple separators folds base-1000 (`1,00.50` → `1000.50`); narrow NBSP (`U+202F`) is the only space-grouping form — ASCII `1 234.56` is not grouped (see Limitations).

Compare [Currency](currency/) for identifier-only canonicalization (no amount).

See also: [Execution Result](../concepts/execution-result/), [Segmentation](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md).
