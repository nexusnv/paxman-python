---
title: "MinorPlanet"
---

Canonicalizes **one minor-planet mention** per call — an unpacked provisional (`1995 XA`, `2007 TA418`), a retrospective (`A904 OA`) or `A/`-prefixed (`A/2017 U1`) designation, a packed 7-char (`J95X00A`, `K07Tf8A`) or extended `_` (`_QC0000`) form, a survey designation in either spelling (`2040 P-L` / `PLS2040`), a parenthesized number (`(433)`), or a packed number (`03202`, `a0017`, `~000z`) — to the unpacked canonical.

> **In plain language:** give it `J95X00A`, `1995 XA`, `PLS2040`, or `(433) Eros` and it hands back `1995 XA` / `2040 P-L` / `(433)` with the MPC publication cited. Structure-only at v1 (no registry): a well-formed but never-assigned shape is `SUCCESS`, never a guess about issuance; shapes outside the lanes are `MISSING`.

---

## What it recognizes — and what it does not

| Recognizes | Does not recognize |
|------------|--------------------|
| Unpacked provisionals (`1995 XA`, `2007 TA418`, `1992 QB1`) | Glued runs (`1995XA`) → `MISSING` (separator required) |
| Spaced lowercase/underscore (`2003 cp20`, `1995 xa`, `1995_XA` → upper/space canonical) | Glued lowercase (`2003cp20`) → `MISSING` (JPL search liberality is resolution, not grammar) |
| Retrospective (`A904 OA`) and `A/`-prefixed (`A/2017 U1`, 1–2 letters) | Old-style systems (`1892 A`, `1914 VV`, `SIGMA 27`) → `MISSING` (superseded 1925) |
| Packed 7-char, case-exact (`J95X00A`, `K07Tf8A`; `a0017` ≠ `A0345`) | Bad-century packs (`Q95X00A`) → `MISSING` (century is lane-defining) |
| Extended `_` packs (`_QC0000`), survey packs (`PLS2040`, `T1S3138`) | Comet/satellite forms (`C/1995 O1`, `S/2000 J 11`, `1I/2017 U1`) → `MISSING` (deferred/disjoint namespaces) |
| Surveys either spelling (`2040 P-L` / `PLS2040`) | Bare numbers (`433`) → `MISSING` (parens load-bearing) |
| Parenthesized numbers (`(433)`, `(274301)`; name outside span in `(433) Eros`) | Bare names (`Eros`) → `MISSING` (names lane deferred) |
| Packed numbers (`03202`, `A0345`, `a0017`, `~000z`, `~AZaz`) | Subscript cycles (`1995 SA₁`) → `MISSING` (ASCII-only wire) |

Known v1 overclaims (no registry): `(555)`-shaped phone area codes match the number lane and bare 5-digit runs match the packed-number lane. Segment phone/ZIP contexts before calling; the future MPCORB snapshot disambiguates.

---

## Canonical output

Default `output_format` is `"designation"` (unpacked canonical).

| `output_format` | Renders | Example |
|-----------------|---------|---------|
| *(default)* `designation` / `None` / `"default"` | Unpacked canonical | `1995 XA` |
| `packed` | Case-exact wire encoding | `J95X00A` |

Any other value raises `ContractError`. The `packed` rendering re-enters under the default contract (ADR-0010 fixed point); the `A/` lane defines no packed mapping and falls back to the designation.

```python
from paxman.capabilities import MinorPlanet
import paxman

paxman.register_all_shipped()
print(paxman.canonicalize("J95X00A", MinorPlanet.create_contract()).canonicalized_value)
print(paxman.canonicalize("(433) Eros", MinorPlanet.create_contract()).canonicalized_value)
print(paxman.canonicalize("1995 XA", MinorPlanet.create_contract(output_format="packed")).canonicalized_value)
```

---

## Contract

```python
contract = MinorPlanet.create_contract(
    output_format=None,  # "designation" (default); "packed" offered
    # plus every common field: suppress_common_words / excluded_rules / pinned_rules / year / extra_grammars
)
```

No capability-specific flags at v1. `year` filters rules by `publication_year` (all three publications are 2026 living documents).
