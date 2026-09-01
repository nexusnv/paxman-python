---
title: "Paxman — User Documentation"
slug: v0.3.1
---

:::note[Docs since v0.2.0]
User documentation is versioned from **v0.2.0** onwards (first stable docs, ADR-0009 Recognition Kernel). Earlier tags (`v0.1.x`) have no published user docs. Docs are now hosted on GitHub Pages at https://nexusnv.github.io/paxman-python/ . See [Migration](migration/) for the v0.1.x → v0.2.0 breaking change (F1 fix) and the full changelog.
:::

Paxman is a **canonicalization library**: you give it messy, human-written text and it tells you what that text *means* according to the specification that defines it — not a guess, a cited answer.

> **Example:** `"user@Example.COM"` → `"user@example.com"` (lowercased per RFC 5322), `"01/02/2026"` → either `AMBIGUOUS` (US vs European date) or a single ISO date if you pin the rules. Every answer comes with the specification that produced it.

---

## Who is this for?

These docs are written for **everyone who needs reliable identifiers** — not just Python experts:

| You are… | You will use Paxman to… |
|----------|-------------------------|
| A **Python developer** integrating validation into an app or API | Call `paxman.canonicalize()` with a typed contract; handle `ExecutionResult` in code |
| A **researcher or analyst** cleaning data in a Jupyter notebook | Normalize one column at a time — emails, country names, URLs — with two lines of Python per cell |
| A **non-Python operator** running a data pipeline | Use Paxman from any Python environment (`uv`, `pip`, notebooks, scripts) with no extra services — it is a pure library with zero runtime dependencies |

If you can run `pip install paxman` and write a few lines of Python, you can use Paxman. No servers, no network calls, no configuration files.

---

## What Paxman does and does not do

| Does | Does not |
|------|----------|
| Resolves **one mention per call** to a single canonical value when the specifications agree | Extract *all* mentions from a paragraph — you split the text first (see the [Segmentation Recipe](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md)) |
| Returns the **same output for the same input** every time (deterministic) | Learn from data or make probabilistic guesses |
| Tells you **which specification** validated the answer (provenance) | Contact a network service or clock to decide |

---

## At a glance

```python
import paxman
from paxman.capabilities import Email
from paxman.core.domain import Resolution

paxman.register_all_shipped()  # once, before your first call

contract = Email.create_contract()
result = paxman.canonicalize("Contact user@Example.com", contract)

if result.status == Resolution.SUCCESS:
    print(result.canonicalized_value)  # "user@example.com"
else:
    print(result.status)  # MISSING | INVALID | AMBIGUOUS
```

Three steps, every time: **register** → **create a contract** → **canonicalize**.

---

## Where to go next

| Doc | What you will learn |
|-----|---------------------|
| [Getting Started](getting-started/) | Install with `pip` or `uv`, run your first call in a script or notebook |
| [Concepts](concepts/) | The mental model — capabilities, contracts, pipeline, results, provenance |
| [Capabilities](capabilities/) | Per-capability guides — one page per kind of identifier |
| [API Reference](api-reference/) | Signatures, types, and error table for every public import |
| [Extending](extending/) | Add your own grammars & rules via `extra_grammars` |
| [Migration](migration/) | Versioning and upgrade checklist (SemVer) |
| [Segmentation Recipe](https://github.com/nexusnv/paxman-python/blob/main/docs/recipes/segmentation.md) | How to handle text with more than one entity |

### Concepts in detail

The [Concepts hub](concepts/) is the place to build your mental model before diving into reference docs. Each page is self-contained and includes a Mermaid diagram:

- [Capabilities](concepts/capabilities/) — what a capability is and how it is chosen
- [Contracts](concepts/contracts/) — how you configure what Paxman recognizes and validates
- [Pipeline](concepts/pipeline/) — what happens inside a `canonicalize()` call
- [Execution Result](concepts/execution-result/) — how to read `status`, `canonicalized_value`, `span`, and `candidates`
- [Provenance](concepts/provenance/) — what "authoritative" means and how to cite it
- [Candidates & Ambiguity](concepts/candidates-and-ambiguity/) — why two answers can be correct
- [Errors](concepts/errors/) — what raises an exception vs what returns a status

### Capability guides

Each guide under [Capabilities](capabilities/) is also self-contained: what it recognizes, canonical output & `output_format`, contract flags, status examples, notebook snippet, and provenance.

---

## Capabilities available today

Paxman ships with capabilities that each cover one kind of identifier. The set is **growing over time** — the list below reflects what is available in this release, not a fixed ceiling. Each capability is independently selectable via its contract:

- **Country** — country codes and names (ISO 3166, CLDR)
- **Currency** — currency codes, symbols, and display names (ISO 4217, CLDR)
- **Date** — calendar dates in ISO, US, European, and slash-ISO formats
- **Email** — standard, obfuscated, and localhost addresses (RFC 5322, RFC 6761)
- **IP** — IPv4 and IPv6 addresses (RFC 791, RFC 5952)
- **ISBN** — ISBN-10 and ISBN-13 with check-digit and hyphenation support
- **Money** — amounts paired with currency identifiers (ISO 4217, CLDR)
- **Phone** — international and national phone numbers (E.164, RFC 3966, NANP)
- **SI Unit** — SI unit expressions and compounds (BIPM SI Brochure, ISO 80000-1)
- **URL** — absolute URIs and IRIs (WHATWG URL Standard)

You only load what you use — importing `paxman.capabilities.Email` does not load the others.

> **Note on the count:** do not treat the number of capabilities as fixed. New capabilities are added in minor releases. Always check `paxman.capabilities` or the latest release notes for the current set.

---

## Requirements

- Python **3.11** or newer
- No runtime dependencies — `pip install paxman` is enough

Next: [Getting Started →](getting-started/)
