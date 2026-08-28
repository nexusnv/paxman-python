---
title: "IP"
---

Canonicalizes **one IP address** per call to its normalized textual form.

> **In plain language:** give it `"192.168.1.1"` or `"2001:0db8:0000:0000:0000:0000:0000:0001"` and it hands back the normalized address if a spec says it is valid. IPv6 canonicalization follows RFC 5952 so the same address always looks the same.

---

## What it recognizes — and what it does not

| Recognizes | Does not recognize |
|------------|--------------------|
| IPv4 dotted-decimal (`192.168.1.1`) | CIDR notation (`192.168.1.0/24`) — address only |
| IPv6 (compressed or expanded, e.g. `2001:db8::1`) | Hostnames — use [URL](url/) |

---

## Canonical output

Single format — the normalized address. IPv6 is rendered per **RFC 5952** (lowercase hex, `::` compression, etc.).

| `output_format` | Renders |
|-----------------|---------|
| *(only)* `ip` / `None` / `"default"` | normalized address string |

```python
from paxman.capabilities import IP
import paxman

paxman.register_all_shipped()
paxman.canonicalize(
    "192.168.1.1", IP.create_contract()
).canonicalized_value  # "192.168.1.1"
paxman.canonicalize(
    "2001:0db8:0000:0000:0000:0000:0000:0001", IP.create_contract()
).canonicalized_value  # "2001:db8::1"
```

---

## Contract

```python
contract = IP.create_contract(
    include_ipv6=True,  # bool, default True — recognize IPv6
    output_format=None,  # "ip" (only format)
    # plus every common field: excluded_rules / pinned_rules / year / extra_grammars
)
```

- With `include_ipv6=True` (the default) both grammars run. With `False`, only `ipv4_recognition` runs — an IPv6 address is then `MISSING` (never seen), not `INVALID`.

```python
paxman.canonicalize(
    "2001:db8::1", IP.create_contract(include_ipv6=False)
).status.value  # "missing"
paxman.canonicalize(
    "2001:db8::1", IP.create_contract()
).canonicalized_value  # "2001:db8::1"
```

---

## Statuses

| Input | Contract | Status | Why |
|-------|----------|--------|-----|
| `192.168.1.1` | any | `SUCCESS` | normalized IPv4 |
| `2001:db8::1` | defaults | `SUCCESS` | → `2001:db8::1` (RFC 5952) |
| `2001:db8::1` | `include_ipv6=False` | `MISSING` | IPv6 grammar not active |
| `999.999.999.999` | any | `INVALID` | recognized shape but no spec accepts it |
| `hello` | any | `MISSING` | no IP pattern |
| `10.0.0.1 and 10.0.0.2` (two distinct values) | any | raises `MultipleMentionsError` | split first |

```mermaid
flowchart TB
    A[Text] --> G1[ipv4_recognition]
    A --> G2[ipv6_recognition<br>only if include_ipv6]
    G1 --> R1[Rule: RFC 791]
    G2 --> R2[Rule: RFC 5952]
    R1 & R2 --> D{One value?}
    D -->|yes| OK[SUCCESS<br>normalized]
    D -->|none| MISS_OR_INV[MISSING or INVALID]
    D -->|two values<br>same mention| AMB[AMBIGUOUS<br>rare for IP]

    style OK fill:#e6ffed,stroke:#2d8a4e
```

---

## Notebook snippet

```python
import paxman
from paxman.capabilities import IP
from paxman.core.domain import Resolution

paxman.register_all_shipped()
contract = IP.create_contract()

for text in [
    "192.168.1.1",
    "2001:0db8:0000:0000:0000:0000:0000:0001",
    "999.999.999.999",
    "hello",
]:
    r = paxman.canonicalize(text, contract)
    print(f"{text!r:45} → {r.status.value:10} {r.canonicalized_value!r}")
```

---

## Provenance

- **RFC 791** — IPv4 address validation.
- **RFC 5952** — IPv6 text representation and canonical compression.

See also: [URL](url/), [Execution Result](../concepts/execution-result/), [Segmentation](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md).
