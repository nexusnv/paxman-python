---
title: "CreditCard"
---

Canonicalizes **one payment card number (PAN) mention** per call — a compact 12–19-digit run, a space- or hyphen-grouped form, or a `PAN:`-labelled form — to the compact contiguous ASCII digits.

> **In plain language:** give it `4111111111111111`, `4111 1111 1111 1111`, `4716-2210-5188-5662`, `3782 822463 10005`, or `PAN: 4111 1111 1111 1111` and it hands back `4111111111111111` when the run is 12–19 contiguous ASCII digits and the Luhn MOD-10 check digit passes per ISO/IEC 7812-1:2017 §5 + Annex B. A single flipped digit (`4111111111111112`) is `INVALID`, never a guess; masked, truncated, tokenized, and out-of-window shapes are `MISSING`. Brand prefix/length checking (Visa, Mastercard, American Express, Discover, Diners Club, JCB, China UnionPay, Maestro) is available behind `include_brand_validation=True` and off by default.

> **PCI handling warning:** `SUCCESS` means the digits pass ISO/IEC 7812-1 structure + Luhn — it is **not** an authorization, an issuer lookup, or proof that an account exists. Real PANs are cardholder data under PCI DSS: Paxman makes no network calls and confers no compliance. Keep PANs out of logs, mask them in display per your PCI DSS obligations, and put publicly documented test PANs (like `4111111111111111`) in fixtures rather than live cardholder data.

---

## What it recognizes — and what it does not

| Recognizes | Does not recognize |
|------------|--------------------|
| Compact contiguous run (`4111111111111111`, `378282246310005`, `36050234196908`) | Runs outside the 12–19 window (`41111111111`, `4111111111111111111111`) → `MISSING` (floor/ceiling, never carved) |
| Spaced 4-4-4-4 grouping (`4111 1111 1111 1111`, `4242 4242 4242 4242`) | Double spaces / tabs (`4111  1111 1111 1111`) → `MISSING` (a single space or hyphen per gap only) |
| Dashed 4-4-4-4 grouping (`4716-2210-5188-5662`) and mixed space+hyphen (`4444-3333 2222 1111`) | Dot / underscore / slash grouping (`4111.1111.1111.1111`) → `MISSING` (**DEFER** — add a community grammar via `extra_grammars`) |
| Amex 4-6-5 grouping (`3782 822463 10005`, `3714 496353 98431`) | Masked / truncated (`4111****1111`, `411111...1111`) → `MISSING` (**REJECT** — PCI handling outputs are never a PAN) |
| 14-digit Diners grouping (`3622 720627 1667`) | Token (`tok_visa_abc123`) → `MISSING` (**REJECT** — different identifier domain) |
| Label with separator (`PAN: 4111 1111 1111 1111`, `card number: 4111111111111111`, `credit card 4111…`, `cc 4111…` — case-insensitive) | OCR digit look-alikes (`4l11111111111111`) → `MISSING` (**REJECT** — ASCII digits only) |
| Expiry adjacency (`4111111111111111 12/27` — the span stops before the date) | Glued label / letter-glued run (`PAN4111111111111111`, `X4111111111111111`) → `MISSING` (a separator or word boundary is required) |

---

## Canonical output

The default `output_format` is `"pan"` — the compact digits, unchanged.

| `output_format` | Renders | Example |
|-----------------|---------|---------|
| *(default)* `pan` / `None` / `"default"` | Compact contiguous ASCII digits — the canonical identity | `4111111111111111` |
| `grouped` | Groups of four from the left, last group takes the remainder (encoding — the same digits re-chunked, so it re-enters exactly; grouping-agnostic, so a 15-digit Amex renders `3782 8224 6310 005`, never brand 4-6-5 — presentation never sniffs brand) | `3782 8224 6310 005` from `378282246310005` |

Any other value raises `ContractError` — including `compact`, which is not an offered alias (the digits are already compact).

```python
from paxman.capabilities import CreditCard
import paxman

paxman.register_all_shipped()
print(
    paxman.canonicalize(
        "4111 1111 1111 1111", CreditCard.create_contract()
    ).canonicalized_value
)
print(
    paxman.canonicalize(
        "PAN: 378282246310005", CreditCard.create_contract()
    ).canonicalized_value
)
print(
    paxman.canonicalize(
        "4716-2210-5188-5662", CreditCard.create_contract()
    ).canonicalized_value
)
print(
    paxman.canonicalize(
        "378282246310005", CreditCard.create_contract(output_format="grouped")
    ).canonicalized_value
)
print(
    paxman.canonicalize(
        "4111111111111111 12/27", CreditCard.create_contract()
    ).canonicalized_value
)
```

---

## Contract

```python
contract = CreditCard.create_contract(
    output_format=None,  # "pan" (default), "grouped"
    include_brand_validation=False,  # opt-in brand prefix/length allowlist
    # plus every common field: suppress_common_words / excluded_rules / pinned_rules / year / extra_grammars
)
```

- No grammar toggles: one grammar (`pan_recognition`), two rules (`Section 5-pan-structure-luhn`, `Section 1-brand-prefix-membership`).
- `include_brand_validation` (default `False`) gates the brand rule: off, any Luhn-valid 12–19-digit run is `SUCCESS` even if no brand claims the prefix; on, the prefix **and** length must fall inside the eight-brand allowlist and the brand rule re-checks structure + Luhn locally — ADR-0012 corroboration, never a waiver of the ISO rule.
- `year` filters by `publication_year`; e.g. `year=2016` drops both rules (2017, 2026) → `4111111111111111` becomes `INVALID`, while `year=2017` keeps the ISO structure rule → still `SUCCESS`.
- Single-value: two distinct PANs in one call raise `MultipleMentionsError` — split first per `docs/recipes/segmentation.md`.

---

## Statuses

| Input | Contract | Status | Value / why |
|-------|----------|--------|-------------|
| `4111111111111111` | defaults | `SUCCESS` | `"4111111111111111"` |
| `4111 1111 1111 1111` | defaults | `SUCCESS` | `"4111111111111111"` (grouping is presentation-only, stripped) |
| `4716-2210-5188-5662` | defaults | `SUCCESS` | `"4716221051885662"` (dashes stripped) |
| `3782 822463 10005` | defaults | `SUCCESS` | `"378282246310005"` (4-6-5 collapses to the compact twin) |
| `3622 720627 1667` | defaults | `SUCCESS` | `"36227206271667"` (14-digit Diners grouping) |
| `4444-3333 2222 1111` | defaults | `SUCCESS` | `"4444333322221111"` (mixed separators) |
| `PAN: 4111 1111 1111 1111` | defaults | `SUCCESS` | label absorbed into the span |
| `4111111111111111 12/27` | defaults | `SUCCESS` | `"4111111111111111"`, span `(0, 16)` — the date guard keeps the expiry out of the claim |
| `9999999999999995` | defaults | `SUCCESS` | Luhn-valid, brand gate off (unknown prefix accepted) |
| `9999999999999995` | `include_brand_validation=True` | `INVALID` | prefix falls outside the allowlist |
| `4111111111111111` | `include_brand_validation=True` | `SUCCESS` | `visa` `4` / {13, 16, 19} corroborates |
| `6200000000000005` | `include_brand_validation=True` | `SUCCESS` | `china-unionpay` `62` / {16–19} corroborates |
| `6200000000000001` | any | `INVALID` | recognized UnionPay shape, Luhn fails — the brand rule never waives |
| `4111111111111112` | any | `INVALID` | recognized shape, Luhn check digit fails |
| `4111111111111111` | `output_format="grouped"` | `SUCCESS` | `"4111 1111 1111 1111"` |
| `378282246310005` | `output_format="grouped"` | `SUCCESS` | `"3782 8224 6310 005"` (4-4-4-3 re-chunk — never brand 4-6-5) |
| `4111111111111111` | `pinned_rules=("Section 5-pan-structure-luhn",)` | `SUCCESS` | ISO rule alone corroborates (vacuity clause) |
| `4111111111111111` | `year=2016` | `INVALID` | both rules are newer, dropped |
| `4111111111111111` | `year=2017` | `SUCCESS` | ISO structure rule (2017) survives |
| `4111111111111111` | `excluded_rules=("Section 5-pan-structure-luhn", "Section 1-brand-prefix-membership")` | `INVALID` | no rule validates |
| `41111111111111111` (17-run) | any | `INVALID` | the whole 17-digit run is claimed atomically, Luhn arbitrates — never carved to 16 |
| `order 12 4111111111111111` | any | `INVALID` | soft-joined digits claim the whole run (18 digits), Luhn arbitrates |
| `4111  1111 1111 1111` (double space; tabs likewise) | any | `MISSING` | double spaces and tabs are not grouping separators |
| `4111.1111.1111.1111` (also `_` and `/`) | any | `MISSING` | **DEFER** — not recognized in v1; a community grammar via `extra_grammars` is the extension path |
| `4111****1111`, `411111...1111` | any | `MISSING` | **REJECT** — masked/truncated are handling outputs, not PANs |
| `tok_visa_abc123` | any | `MISSING` | **REJECT** — token domain, not a PAN |
| `4l11111111111111` | any | `MISSING` | **REJECT** — OCR `l` is not an ASCII digit |
| `41111111111`, `4111111111111111111111` | any | `MISSING` | outside the 12–19-digit window (11 and 22 digits) |
| `PAN4111111111111111` | any | `MISSING` | glued label needs a separator |
| `X4111111111111111` | any | `MISSING` | letter-glued digit run |
| `4111111111111111` | `output_format="compact"` | raises `ContractError` | not an offered format |
| Two distinct PANs in one call | any | raises `MultipleMentionsError` | split first |

Two deterministic rules over one single-value grammar yield at most one value, so `AMBIGUOUS` is unreachable for this capability.

```mermaid
flowchart TB
    A[Text] --> G[Grammar:<br>pan_recognition]
    G --> R1{Section 5<br>structure + Luhn MOD-10}
    R1 --> R2{Section 1<br>brand prefix (gated)}
    R2 -->|corroborates or gate off| OK[SUCCESS]
    R1 -->|no rule validates| INV[INVALID]
    R2 -->|outside allowlist| INV
    G -->|no shape| MISS[MISSING]

    style OK fill:#e6ffed,stroke:#2d8a4e
    style INV fill:#fff5f5,stroke:#cc3333
    style MISS fill:#fff5f5,stroke:#cc3333
```

---

## Notebook snippet — normalize a mixed column

```python
import paxman
from paxman.capabilities import CreditCard
from paxman.core.domain import Resolution
from paxman.core.errors import ContractError

paxman.register_all_shipped()
contract = CreditCard.create_contract()

rows = [
    "4111111111111111",
    "4111 1111 1111 1111",
    "4716-2210-5188-5662",
    "3782 822463 10005",
    "PAN: 4111 1111 1111 1111",
    "4111111111111111 12/27",
    "4111111111111112",
    "6200000000000005",
    "9999999999999995",
    "4111  1111 1111 1111",
    "4111.1111.1111.1111",
    "4111****1111",
    "41111111111",
    "not a card",
]

for text in rows:
    r = paxman.canonicalize(text, contract)
    val = r.canonicalized_value if r.status == Resolution.SUCCESS else "—"
    rule = r.candidates[0].validation_rule if r.candidates else "—"
    print(f"{text!r:32} → {r.status.value:10} {val!r:24} ({rule})")

try:
    CreditCard.create_contract(output_format="compact")
except ContractError as e:
    print(f"compact → ContractError: {e}")
```

---

## Provenance

- **ISO/IEC 7812-1:2017** §5 PAN structure (IIN + individual account identifier + check digit, 12–19 digits) and Annex B Luhn MOD-10 double-add-double check digit — `Section 5-pan-structure-luhn` (`PARSER`). Catalogue at `https://www.iso.org/standard/70484.html`. The check algorithm itself is Hans Peter Luhn's modulus-10 scheme, published as US Patent 2,950,048 and adopted verbatim by Annex B.
- **Brand IIN/length tables** (eight brands — `visa`, `mastercard`, `amex`, `discover`, `diners`, `jcb`, `china-unionpay`, `maestro` — each a prefix-interval set plus allowed lengths) — `Section 1-brand-prefix-membership` (`LOOKUP_TABLE`), gated behind `include_brand_validation`. Secondary evidence, cross-checked against the payment card number reference table at `https://en.wikipedia.org/wiki/Payment_card_number`; the per-network brand specs remain authoritative.

Deferred in v1: the "Others" brand tier (Mir, RuPay, Troy, UATP and friends) is deliberately absent from the allowlist — a structurally valid PAN of one of those brands is `SUCCESS` with the brand gate off (the default) and `INVALID` with it on. Dot/underscore/slash grouping is a **DEFER** — add it as a community grammar via `extra_grammars`; masked, truncated, tokenized, and OCR spellings are **REJECT**s and must never be repaired into a PAN.

Each candidate's `validation_rule` carries the section, and `candidate.provenance[0].publication_year` the year.

See also: [Execution Result](../concepts/execution-result/), [Provenance](../concepts/provenance/), [Segmentation](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md).
