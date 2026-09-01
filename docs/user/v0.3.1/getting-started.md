---
title: "Getting Started"
slug: v0.3.1/getting-started
---

This guide gets you from zero to your first `canonicalize()` call in about two minutes. It is written for all three audiences — **Python developers, notebook researchers, and operators** — so it shows each step both as plain Python and as you would run it in a Jupyter cell.

---

## 1. Install

Paxman requires **Python 3.11+** and has **zero runtime dependencies**.

### pip

```bash
pip install paxman
```

### uv (recommended for projects)

```bash
uv add paxman
```

### Jupyter / notebook

In a notebook cell:

```python
%pip install paxman
```

Check the install:

```python
import paxman

print(paxman.__doc__)  # should not raise
```

---

## 2. Register — tell Paxman which capabilities to load

Registration is a one-time setup that must happen **before your first `canonicalize()` call**, from a single thread. After that the registry freezes — this keeps results deterministic and thread-safe.

**For quick exploration** (notebooks, scripts, one-offs) register everything at once:

```python
import paxman

paxman.register_all_shipped()  # loads every capability shipped in this release
```

**For production code** where you want to be explicit about what you depend on, register only what you need:

```python
import paxman
from paxman.capabilities import Email, Date

paxman.register_capability(Email())
paxman.register_capability(Date())
```

Either approach is fine. The important rule is: **register first, canonicalize second**. Registering after the first call raises `CapabilityError`.

> **Jupyter tip:** put the registration in the *first cell* of your notebook and re-run it after a kernel restart.

---

## 3. Create a contract — tell Paxman what you expect

A **contract** is a small configuration object that says: *which capability to use, which formats to accept, and which rules to apply*. Every capability provides a `create_contract()` factory:

```python
from paxman.capabilities import Email

# The simplest contract — defaults for everything
contract = Email.create_contract()

# A contract that also looks for obfuscated addresses like "user at example dot com"
contract2 = Email.create_contract(include_obfuscated=True)
```

You will learn all the knobs a contract offers in [Contracts](concepts/contracts/). For now, know that:

- `excluded_rules`, `pinned_rules`, `year`, and `output_format` exist on **every** contract.
- Some contracts add their own flags (e.g. `include_localized` for Country, `default_country` for Phone).

---

## 4. Canonicalize — one mention per call

```python
import paxman
from paxman.capabilities import Email
from paxman.core.domain import Resolution

paxman.register_all_shipped()

contract = Email.create_contract()
result = paxman.canonicalize("Contact user@Example.com", contract)

print(result.status)  # Resolution.SUCCESS
print(result.canonicalized_value)  # "user@example.com"
print(result.span)  # (8, 24) — where it sat in the input
```

That is the full pattern. The same three lines work for any capability — only the import and the contract change:

```python
from paxman.capabilities import Country

contract = Country.create_contract()
result = paxman.canonicalize("United States", contract)
# result.canonicalized_value == "US"
```

```python
from paxman.capabilities import Date

contract = Date.create_contract()
result = paxman.canonicalize("2026-01-15", contract)
# result.canonicalized_value == "2026-01-15"
```

### One mention per call

Paxman resolves **one entity per `canonicalize()` call**. If your text contains two different entities (e.g. `"alice@example.com and bob@example.org"` → two distinct values), it raises `MultipleMentionsError` instead of guessing. This is intentional — the caller owns segmentation. For that pattern see the [Segmentation Recipe](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md): split first, then loop.

---

## 5. Read the result

Every call returns an `ExecutionResult` with the same shape regardless of capability:

```python
result.status  # Resolution enum: MISSING | INVALID | SUCCESS | AMBIGUOUS
result.canonicalized_value  # str on SUCCESS, None otherwise
result.candidates  # tuple of all validated candidates
result.span  # (start, end) of the resolved value on SUCCESS, else None
result.version_stamp  # which Paxman version produced this answer
result.contract  # the contract you passed in, echoed back

for c in result.candidates:
    print(c.value, c.provenance[0].specification_name, c.span)
```

What the statuses mean (covered in depth in [Execution Result](concepts/execution-result/)):

| Status | Meaning | What to do |
|--------|---------|------------|
| `SUCCESS` | One canonical value, validated by a spec | Use `canonicalized_value` |
| `MISSING` | No pattern that looked like this kind of entity | The input does not contain this entity |
| `INVALID` | Looked like it, but no spec accepted it | The input is malformed |
| `AMBIGUOUS` | One mention, two specs that disagree (e.g. `01/02/2026`) | Narrow the contract or ask the user |

Provenance (which spec validated the answer) is always on `candidate.provenance` — see [Provenance](concepts/provenance/).

---

## 6. Notebook walkthrough — cleaning a column

A common research task is normalizing a column of mixed country names. This works the same in a script, but is shown here as notebook cells so you can copy-paste.

**Cell 1 — setup (run once):**

```python
import paxman
from paxman.capabilities import Country
from paxman.core.domain import Resolution

paxman.register_all_shipped()
contract = Country.create_contract(include_localized=True)
```

**Cell 2 — normalize a list:**

```python
raw = ["United States", "Alemania", "JP", "not a country", "Burma"]

for text in raw:
    r = paxman.canonicalize(text, contract)
    print(
        f"{text!r:20} → {r.status.value:10} {r.canonicalized_value!r:6} span={r.span}"
    )
```

Output:

```
'United States'      → success    'US'   span=(0, 13)
'Alemania'           → success    'DE'   span=(0, 8)
'JP'                 → success    'JP'   span=(0, 2)
'not a country'      → missing    None   span=None
'Burma'              → invalid    None   span=None   # needs include_historical=True
```

**Cell 3 — keep provenance for a report:**

```python
for text in raw:
    r = paxman.canonicalize(text, contract)
    if r.status == Resolution.SUCCESS:
        prov = r.candidates[0].provenance[0]
        print(
            f"{text!r} → {r.canonicalized_value} via {prov.authority}: {prov.specification_name}"
        )
```

No extra handling for `MISSING`/`INVALID` is needed beyond checking `status` — they are domain answers, not exceptions.

---

## 7. What to do when something goes wrong

- **Unexpected `MISSING`** — did you enable the right recognition flag? (e.g. `include_obfuscated` for Email, `include_localized` for Country — see [Contracts](concepts/contracts/)).
- **Unexpected `INVALID`** — the pattern was seen but no spec accepted it. Check whether you excluded the relevant rule, or whether the input is genuinely malformed.
- **Unexpected `AMBIGUOUS`** — one input legitimately means two things under different specs. See [Candidates & Ambiguity](concepts/candidates-and-ambiguity/).
- **Exception instead of a result** — see [Errors](concepts/errors/). Common cases: registering after the first call, or a malformed contract.

---

## Next steps

- [Concepts →](concepts/) — build the full mental model.
- [Segmentation Recipe](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md) — handle text with multiple entities.
- Read the [README](https://github.com/nexusnv/paxman-python#readme) for a quick reference table of every capability and its examples.