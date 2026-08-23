# 2026-08-05 — ISBN Capability Implementation Plan

> **For agentic workers: REQUIRED SUB-SKILL: `superpowers:writing-plans` workflow.** This is an implementation plan, not a design doc. Execute it task-by-task with `superpowers:executing-plans` or `superpowers:subagent-driven-development`, TDD-first (Red-Green-Refactor), with a commit after every task. Assume the engineer executing this plan has zero codebase context; every file change below is self-contained.

**Design authority:** `docs/research/2026-08-05-isbn-canonicalization.md` — read it first if any section here seems ambiguous. It contains the full primary-source survey (ISO 2108, ISBN Users' Manual, IANA `urn:isbn`, isbnlib, the ISBN Range Message) that grounds every decision below.
**Repo state:** branch `refactor/streamline-recognition` @ `49cf0f2` — grammars return span-bearing `RecognitionMatch` objects; the engine owns per-grammar containment dedup and total order `(start, end, active_grammars index, grammar name)` (recognition-homogeneity refactor).

## Goal

Implement the **ISBN capability** that canonicalizes ISBN-13 and legacy ISBN-10 input to the **bare 13-digit canonical form** (e.g. `9780306406157`) with full provenance:

1. **Recognize** ISBN-13 and ISBN-10 shapes (bare, hyphenated, space-separated, with optional `ISBN`/`ISBN-13`/`ISBN-10` label) as span-bearing `RecognitionMatch[ISBNNotation]` objects.
2. **Validate** against three authorities:
   - **ISO 2108:2017** — ISBN-13 mod-10 check digit (`Section 5.3-isbn13-check-digit`) and GS1 prefix ∈ {`978`, `979`} (`Section 4.2-gs1-prefix`).
   - **ISBN Users' Manual (2012)** — ISBN-10 mod-11 check digit (`Section 6-isbn10-check-digit`), lifecycle `superseded`.
   - **ISBN Range Message (2026-08-05 snapshot)** — registrant-range issued-ness (`Section 4-registrant-range`), gated behind `include_range_validation`.
3. **Resolve** both shapes to one canonical 13-digit string — never `AMBIGUOUS` between shapes, because ISBN-10 converts losslessly to ISBN-13 and cross-shape candidates converge (§7.2 of the memo).
4. **Present** the optional hyphenated display form only through `Capability.format_value()` when `output_format="hyphenated"`; rules never read `output_format`.

**Correctness gate:** the five existing baseline replay hashes MUST NOT change (Task 10 re-pins them).

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

## Architecture

```text
ISBNNotation(shape: "isbn10" | "isbn13", digits: str)
        ▲                              ▲
        │ grammar                      │ grammar
isbn13_recognition               isbn10_recognition
(13-digit runs,                  (10 chars, final may be X)
 separators, label)                     │
        └──────────────┬────────────────┘
                       ▼
        span-bearing RecognitionMatch[ISBNNotation]
                       ▼
        engine: per-grammar containment dedup, total order,
        _filter_rules (pinned → excluded → year → requires_features)
                       ▼
   rules/iso_2108_ed2017.py          (Section 5.3 check digit, Section 4.2 GS1 prefix)
   rules/isbn_users_manual_ed2012.py (Section 6 ISBN-10 check digit)
   rules/isbn_range_message_ed2026.py (Section 4 registrant range,
                                       requires_features={"include_range_validation"})
   rules/data/range_message.py       (generated snapshot constants, 1682 rules)
                       ▼
        normalize() → bare 13-digit canonical value (ISBN-10 converted)
                       ▼
        ISBNCapability.format_value(value, "hyphenated" → hyphenate(value))
```

**Responsibility split (the invariant):**

| Concern | Owner |
|---|---|
| Extraction + syntax normalization (strip hyphens/spaces/`ISBN` label, fold `x` → `X`) | Grammar |
| Shape discrimination (13 digits → `isbn13`; 10 chars → `isbn10`) | Grammar (digit-count discriminator) |
| Check digit, GS1 prefix, registrant range | Rules (provenance-backed) |
| ISBN-10 → ISBN-13 conversion | Rules (`normalize`) |
| Hyphenation (presentation) | `Capability.format_value()` only |
| Ordering, dedup, status, replay hash | Engine (untouched) |

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

**Design decisions that resolve memo §7.3/§7.6:** the ISBN-13 check-digit rule ALSO enforces prefix ∈ {`978`, `979`} inside `matches()`. This is the only way the memo's resolution map ("13 digits, check digit OK, prefix ∉ {978, 979} → `INVALID`") is achievable under the engine's alternative-rules semantics (each rule independently emits a candidate; zero candidates → `INVALID`). The standalone `Section 4.2-gs1-prefix` rule still exists to add its own provenance claim for valid ISBNs. Both are cited to ISO 2108.

## Tech Stack

- Python 3.11, standard library only — no new runtime dependencies.
- `re` for grammars (module-scope compiled patterns, never compiled per call); `xml.etree.ElementTree` in the generator script only (never at import time — replay-safety).
- Frozen dataclasses: `@dataclass(frozen=True, slots=True)` notation, `@dataclass(frozen=True)` contract (extends `CapabilityContract`).
- Gates (unchanged): ruff (line-length 88, E/W/F/I/N/UP/B/SIM), pyright strict, import-linter layers, pytest + hypothesis, coverage `branch=true` `fail_under=95`.

## Behavioral Contract

| Input | Contract | Status / canonical |
|---|---|---|
| `9780306406157` | default | `SUCCESS` → `9780306406157` |
| `978-0-306-40615-7` | default | `SUCCESS` → `9780306406157` (hyphens are presentation) |
| `0-306-40615-2` | default | `SUCCESS` → `9780306406157` (ISBN-10 converted) |
| `0-306-40615-2` | `include_isbn10=False` | `MISSING` (grammar inactive) |
| `080442957X` | default | `SUCCESS` → `9780804429573` (`X` = 10) |
| `9780110002224` | default | `SUCCESS` → `9780110002224` |
| `1234567890123` (check-digit-valid, prefix ∉ {`978`,`979`}) | default | `INVALID` (recognized EAN-13, no ISBN authority validates) |
| `9780306406158` (bad mod-10 check) | default | `INVALID` |
| `0306406153` (bad mod-11 check) | default | `INVALID` |
| `9780306406157 9780201310054` (two different books) | default | `AMBIGUOUS` (two canonical values) |
| `call me at noon` | default | `MISSING` |
| any recognized value | `include_range_validation=False` | Range Message rule excluded via `requires_features`; status decided by check-digit + GS1 rules alone (no issued-ness claim) |

Key rules:

- Hyphens/spaces carry **no lexical significance** (ISO 2108 §4.1) — placement is never validated; an ISBN with non-canonical hyphenation still canonicalizes.
- Both shapes in one input (an ISBN-10 and its ISBN-13 equivalent) → `SUCCESS`, never `AMBIGUOUS` (same canonical value).
- `output_format="isbn10"` is **NOT offered** (undefined for `979` values); only `"hyphenated"` is an alternative to the `"isbn13"` default.
- Contract params: `include_isbn10: bool = True` (grammar toggle), `include_range_validation: bool = False` (rule toggle via `requires_features`).

---

## File Structure

```text
paxman/capabilities/ISBN/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   ├── isbn13_recognition.py
│   └── isbn10_recognition.py
└── rules/
    ├── __init__.py
    ├── iso_2108_ed2017.py
    ├── isbn_users_manual_ed2012.py
    ├── isbn_range_message_ed2026.py
    └── data/
        ├── __init__.py
        ├── range_message.py              (GENERATED — do not hand-edit)
        └── range_message_2026-08-05.xml  (committed snapshot)

tools/
└── regenerate_isbn_range_data.py         (GENERATOR — stdlib only)

tests/capabilities/isbn/
├── __init__.py
├── test_notation.py
├── test_contract.py
├── test_data.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py

tests/property/test_isbn_properties.py
```

## Files And Responsibilities

| File | Action | Responsibility |
|---|---|---|
| `paxman/capabilities/ISBN/__init__.py` | create | re-export `ISBNCapability`, `ISBNContract`, `ISBNNotation` |
| `paxman/capabilities/ISBN/notation.py` | create | `ISBNNotation` frozen dataclass (Task 1) |
| `paxman/capabilities/ISBN/contract.py` | create | `ISBNContract` (Task 2) |
| `paxman/capabilities/ISBN/capability.py` | create | `ISBNCapability`: wiring + `format_value()` hyphenation (Task 6) |
| `paxman/capabilities/ISBN/grammar/__init__.py` | create | grammar package (Task 1) |
| `paxman/capabilities/ISBN/grammar/isbn13_recognition.py` | create | ISBN-13 grammar (Task 5) |
| `paxman/capabilities/ISBN/grammar/isbn10_recognition.py` | create | ISBN-10 grammar (Task 5) |
| `paxman/capabilities/ISBN/rules/__init__.py` | create | rules package (Task 1) |
| `paxman/capabilities/ISBN/rules/iso_2108_ed2017.py` | create | check-digit + GS1 prefix rules (Task 4) |
| `paxman/capabilities/ISBN/rules/isbn_users_manual_ed2012.py` | create | ISBN-10 check-digit rule (Task 4) |
| `paxman/capabilities/ISBN/rules/isbn_range_message_ed2026.py` | create | registrant-range rule (Task 4) |
| `paxman/capabilities/ISBN/rules/data/__init__.py` | create | data package (Task 3) |
| `paxman/capabilities/ISBN/rules/data/range_message.py` | create (generated) | `EAN_PREFIX_RULES`, `GROUP_RULES`, `MESSAGE_DATE` (Task 3) |
| `paxman/capabilities/ISBN/rules/data/range_message_2026-08-05.xml` | create (copied) | committed Range Message snapshot (Task 3) |
| `tools/regenerate_isbn_range_data.py` | create | stdlib-only generator (Task 3) |
| `paxman/capabilities/__init__.py` | modify | ISBN aliases (Task 7) |
| `pyproject.toml` | modify | add `"isbn: isbn capability tests",` marker (Task 7) |
| `tests/capabilities/isbn/__init__.py` | create | test package (Task 1) |
| `tests/capabilities/isbn/test_notation.py` | create | (Task 1) |
| `tests/capabilities/isbn/test_contract.py` | create | (Task 2) |
| `tests/capabilities/isbn/test_data.py` | create | (Task 3) |
| `tests/capabilities/isbn/test_grammar.py` | create | (Task 5) |
| `tests/capabilities/isbn/test_rules.py` | create | (Task 4) |
| `tests/capabilities/isbn/test_capability.py` | create | (Task 6) |
| `tests/integration/test_pipeline.py` | modify | ISBN resolution-map cases (Task 8) |
| `tests/integration/test_feature_gating.py` | modify | ISBN feature-gating cases (Task 8) |
| `tests/integration/test_default_replay_hashes.py` | modify | ISBN baseline hash (Task 10) |
| `tests/property/test_isbn_properties.py` | create | hypothesis suite (Task 9) |
| `tests/unit/test_capability_exports.py` | modify | ISBN exports coverage (Task 7) |
| `HOW_TO_ADD_NEW_CAPABILITY.md` | modify | Step 4 span-contract rewrite (Task 11) |

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

---

## Task 1: Package Skeleton + ISBNNotation

**Files:**
- Create: `paxman/capabilities/ISBN/__init__.py`
- Create: `paxman/capabilities/ISBN/grammar/__init__.py`
- Create: `paxman/capabilities/ISBN/rules/__init__.py`
- Create: `paxman/capabilities/ISBN/rules/data/__init__.py`
- Create: `paxman/capabilities/ISBN/notation.py`
- Create: `tests/capabilities/isbn/__init__.py`
- Create: `tests/capabilities/isbn/test_notation.py`

- [ ] **Step 1: Create the package directories**

```bash
mkdir -p paxman/capabilities/ISBN/grammar
mkdir -p paxman/capabilities/ISBN/rules/data
mkdir -p tests/capabilities/isbn
```

- [ ] **Step 2: Create package `__init__.py` files** (one-line docstring each, Country precedent)

```python
# paxman/capabilities/ISBN/__init__.py
"""ISBN capability for canonicalizing ISBN-13 and ISBN-10 input."""
```

```python
# paxman/capabilities/ISBN/grammar/__init__.py
"""ISBN recognition grammars."""
```

```python
# paxman/capabilities/ISBN/rules/__init__.py
"""ISBN validation rules."""
```

```python
# paxman/capabilities/ISBN/rules/data/__init__.py
"""ISBN Range Message snapshot data (generated)."""
```

```python
# tests/capabilities/isbn/__init__.py
"""ISBN capability tests."""
```

- [ ] **Step 3: RED — write the notation tests** (`tests/capabilities/isbn/test_notation.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISBN.notation import ISBNNotation`)

- `test_notation_frozen_and_slots` — `dataclasses.is_dataclass(ISBNNotation)`; `"__slots__" in ISBNNotation.__dict__`.
- `test_notation_fields` — `dataclasses.fields(ISBNNotation)` names == `["shape", "digits"]`.
- `test_as_list` — `ISBNNotation(shape="isbn13", digits="9780306406157").as_list() == ["isbn13", "9780306406157"]`.
- `test_notation_hashable` — equal instances hash equal.
- `test_notation_immutable` — assigning `notation.digits = "x"` raises `dataclasses.FrozenInstanceError`.

- [ ] **Step 4: GREEN — implement the notation**

```python
# paxman/capabilities/ISBN/notation.py
"""ISBN notation: shape discriminator + normalized digit string."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISBNNotation:
    """ISBN shape discriminator + normalized digit string.

    ``shape`` is "isbn10" or "isbn13". ``digits`` is the digit string;
    ``X`` is allowed only as the final char of an "isbn10" shape.
    """

    shape: str
    digits: str

    def as_list(self) -> list[str]:
        """Convert to list[str] for the generic Rule interface."""
        return [self.shape, self.digits]
```

- [ ] **Step 5: Verify + commit**

```bash
uv run pytest tests/capabilities/isbn/test_notation.py
uv run ruff check paxman/capabilities/ISBN tests/capabilities/isbn
uv run pyright paxman/capabilities/ISBN/notation.py
```

Commit: `feat(isbn): add ISBNNotation and package skeleton`.

## Task 2: ISBNContract

**Files:**
- Create: `paxman/capabilities/ISBN/contract.py`
- Create: `tests/capabilities/isbn/test_contract.py`

- [ ] **Step 1: RED — write the contract tests** (`tests/capabilities/isbn/test_contract.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISBN.contract import ISBNContract`)

- `test_default_output_format` — `ISBNContract().output_format == "isbn13"`.
- `test_offered_output_formats` — `ISBNContract.OFFERED_OUTPUT_FORMATS == frozenset({"hyphenated"})`.
- `test_capability_name` — `ISBNContract().capability_name == "isbn"`.
- `test_feature_defaults` — `include_isbn10 is True`, `include_range_validation is False`.
- `test_active_grammars_default` — `["isbn13_recognition", "isbn10_recognition"]`.
- `test_active_grammars_isbn10_disabled` — `ISBNContract(include_isbn10=False).active_grammars == ["isbn13_recognition"]`.
- `test_frozen` — reassigning `contract.include_isbn10` raises `dataclasses.FrozenInstanceError`.
- `test_as_dict_includes_features` — `ISBNContract().as_dict()` contains `"include_isbn10"` and `"include_range_validation"` with correct values.

- [ ] **Step 2: GREEN — implement the contract**

Read `paxman/capabilities/Country/contract.py` first — `ISBNContract` must extend `CapabilityContract` exactly the same way (frozen dataclass, `capability_name` via `field(default=..., init=False)`, `super().__post_init__()` handled by the base, `_extra_dict_fields()` override):

```python
# paxman/capabilities/ISBN/contract.py
"""ISBN contract configuration."""

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class ISBNContract(CapabilityContract):
    """Contract for the ISBN capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isbn13"  # bare 13 digits
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"hyphenated"})

    capability_name: str = field(default="isbn", init=False)
    include_isbn10: bool = True  # legacy input recognition
    include_range_validation: bool = False  # gates the Range Message rule

    @property
    def active_grammars(self) -> list[str]:
        grammars = ["isbn13_recognition"]
        if self.include_isbn10:
            grammars.append("isbn10_recognition")
        return grammars

    def _extra_dict_fields(self) -> dict[str, object]:
        return {
            "include_isbn10": self.include_isbn10,
            "include_range_validation": self.include_range_validation,
        }
```

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/isbn/test_contract.py
uv run ruff check paxman/capabilities/ISBN tests/capabilities/isbn
uv run pyright paxman/capabilities/ISBN/contract.py
```

Commit: `feat(isbn): add ISBNContract`.

## Task 3: Range Message Snapshot + Generator + Data Module

**Files:**
- Create (copied): `paxman/capabilities/ISBN/rules/data/range_message_2026-08-05.xml` (committed snapshot)
- Create: `tools/regenerate_isbn_range_data.py`
- Create (generated): `paxman/capabilities/ISBN/rules/data/range_message.py`
- Create: `tests/capabilities/isbn/test_data.py`

- [ ] **Step 1: Copy the verified snapshot into the repo**

```bash
cp /tmp/opencode/range_message.xml paxman/capabilities/ISBN/rules/data/range_message_2026-08-05.xml
```

Then verify the copy with a one-shot XML parse (expected values are the verified on-disk snapshot):

```bash
uv run python -c "
import xml.etree.ElementTree as ET
root = ET.parse('paxman/capabilities/ISBN/rules/data/range_message_2026-08-05.xml').getroot()
print(root.tag)
print(root.findtext('MessageSerialNumber'))
print(root.findtext('MessageDate'))
print(len(root.findall('.//EAN.UCC')))
print(len(root.findall('.//Group')))
print(len(root.findall('.//Rule')))
"
```

Expected output (STOP and confirm with the user if anything differs):

```text
ISBNRangeMessage
6f6063f3-6f2a-4619-8bd9-116a3addc690
Wed, 5 Aug 2026 08:25:28 BST
2
287
1864
```

If the file is missing, fall back to a live fetch before proceeding:

```bash
curl -L -o paxman/capabilities/ISBN/rules/data/range_message_2026-08-05.xml https://www.isbn-international.org/export_rangemessage.xml
```

(re-run the verification and confirm the new serial/date/counts with the user — the counts above pin THIS snapshot and its derived data module.)

- [ ] **Step 2: RED — write the data-module tests** (`tests/capabilities/isbn/test_data.py`, mark `@pytest.mark.capability`, import the constants `from paxman.capabilities.ISBN.rules.data.range_message import EAN_PREFIX_RULES, GROUP_RULES, MESSAGE_DATE, MESSAGE_SERIAL`)

- `test_shipped_prefixes` — `set(EAN_PREFIX_RULES) == {"978", "979"}`.
- `test_group_count` — `len(GROUP_RULES) == 287`.
- `test_emitted_rule_count` — `sum(len(r) for r in EAN_PREFIX_RULES.values()) + sum(len(r) for r in GROUP_RULES.values()) == 1682`.
- `test_message_serial` — `MESSAGE_SERIAL == "6f6063f3-6f2a-4619-8bd9-116a3addc690"`.
- `test_message_date` — `MESSAGE_DATE.startswith("Wed, 5 Aug 2026")`.
- `test_known_groups` — `"978-0" in GROUP_RULES` and `"979-10" in GROUP_RULES` and `"979-8" in GROUP_RULES` (979 keys are `979-10, 979-11, 979-12, 979-13, 979-8` — there is no `979-9`).
- `test_ranges_seven_digit` — for every `(start, end, length)` in both tables: `len(start) == len(end) == 7` and `start.isdigit() and end.isdigit()` (the actual XML zero-pads ALL ranges to 7 digits — verified; this test is the tripwire if a future snapshot changes padding).
- `test_no_length_zero` — every `length >= 1` (Length-0 = unallocated rules are never emitted).
- `test_no_output_format_token` — the source text of `range_message.py` does not contain `output_format` (the CI purity glob `*/rules/*.py` does NOT descend into `rules/data/`, so this test is the guard).

- [ ] **Step 3: GREEN — write the generator and emit the data module**

`tools/regenerate_isbn_range_data.py` — standard library only, never imports paxman (keeps `tools/` out of the import-linter layers):

```python
# tools/regenerate_isbn_range_data.py
"""Regenerate paxman/capabilities/ISBN/rules/data/range_message.py.

Usage:
    uv run python tools/regenerate_isbn_range_data.py

Reads the committed Range Message snapshot XML and emits the data module.
Run manually when the snapshot is refreshed. Standard library only.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

SNAPSHOT = Path("paxman/capabilities/ISBN/rules/data/range_message_2026-08-05.xml")
OUTPUT = Path("paxman/capabilities/ISBN/rules/data/range_message.py")


def _collect_rules(parent: ET.Element) -> list[tuple[str, str, int]]:
    """Return [(range_start, range_end, length), ...], skipping Length 0."""
    rules: list[tuple[str, str, int]] = []
    for rule in parent.findall("Rules/Rule"):
        length = int(rule.findtext("Length", "0"))
        if length == 0:
            continue  # "range not allocated" — never emitted
        start, _, end = rule.findtext("Range", "").partition("-")
        rules.append((start, end, length))
    return rules


def _emit_rule_table(entries: list[tuple[str, list[tuple[str, str, int]]]]) -> str:
    blocks = []
    for key, rules in entries:
        tuples = ",\n        ".join(
            f'("{start}", "{end}", {length})' for start, end, length in rules
        )
        blocks.append(f'    "{key}": (\n        {tuples},\n    ),')
    return "{\n" + "\n".join(blocks) + "\n}"


def main() -> None:
    root = ET.parse(SNAPSHOT).getroot()
    serial = root.findtext("MessageSerialNumber", "")
    message_date = root.findtext("MessageDate", "")

    prefixes = [
        (e.findtext("Prefix", ""), _collect_rules(e))
        for e in root.findall("EAN.UCCPrefixes/EAN.UCC")
    ]
    groups = [
        (g.findtext("Prefix", ""), _collect_rules(g))
        for g in root.findall("RegistrationGroups/Group")
    ]

    doc = (
        '"""ISBN Range Message snapshot data — GENERATED, do not edit by hand.\n'
        "\nSource: https://www.isbn-international.org/export_rangemessage.xml\n"
        f"MessageSerialNumber: {serial}\n"
        f"MessageDate: {message_date}\n"
        "Regenerate with: uv run python tools/regenerate_isbn_range_data.py\n"
        '"""\n'
        "\nfrom __future__ import annotations\n\n"
        f'MESSAGE_SERIAL = "{serial}"\n'
        f'MESSAGE_DATE = "{message_date}"\n\n'
        "EAN_PREFIX_RULES: dict[str, tuple[tuple[str, str, int], ...]] = "
        + _emit_rule_table(prefixes)
        + "\n\nGROUP_RULES: dict[str, tuple[tuple[str, str, int], ...]] = "
        + _emit_rule_table(groups)
        + "\n"
    )
    assert "output_format" not in doc  # purity guard — see test_no_output_format_token
    OUTPUT.write_text(doc)
    emitted = sum(len(r) for _, r in prefixes) + sum(len(r) for _, r in groups)
    print(f"wrote {OUTPUT}: {emitted} rules")


if __name__ == "__main__":
    main()
```

Then run it and sanity-check the emitted constants:

```bash
uv run python tools/regenerate_isbn_range_data.py
uv run python -c "
from paxman.capabilities.ISBN.rules.data.range_message import EAN_PREFIX_RULES, GROUP_RULES, MESSAGE_DATE
assert set(EAN_PREFIX_RULES) == {'978', '979'}
assert '978-0' in GROUP_RULES
assert MESSAGE_DATE.startswith('Wed, 5 Aug 2026')
print('data module OK')
"
```

- [ ] **Step 4: Verify + commit**

```bash
uv run pytest tests/capabilities/isbn/test_data.py
uv run ruff check tools paxman/capabilities/ISBN
uv run pyright paxman/capabilities/ISBN/rules/data/range_message.py
```

Commit: `feat(isbn): add Range Message snapshot and generated range data`.

## Task 4: Validation Rules

**Files:**
- Create: `paxman/capabilities/ISBN/rules/iso_2108_ed2017.py`
- Create: `paxman/capabilities/ISBN/rules/isbn_users_manual_ed2012.py`
- Create: `paxman/capabilities/ISBN/rules/isbn_range_message_ed2026.py`
- Create: `tests/capabilities/isbn/test_rules.py`

- [ ] **Step 1: RED — write the rule tests** (`tests/capabilities/isbn/test_rules.py`, mark `@pytest.mark.capability`)

Cover, per rule: `matches()` valid / variant / invalid, `normalize()` canonical output (incl. ISBN-10→13 conversion), provenance attributes (authority, `lifecycle`, `publication_year`), and the name/strategy/citation conventions:

- `test_isbn13_check_digit_valid` — `Section53Isbn13CheckDigit().matches(ISBNNotation("isbn13", "9780110002224"), contract)` is True (workbook: `978-0-11-000222-4`).
- `test_isbn13_check_digit_invalid` — `"9780306406158"` (wrong check) → False; `"9780306406157"` → True.
- `test_check_digit_rejects_non_gs1_prefix` — `"1234567890123"` with a valid check digit → False (the check-digit rule enforces prefix ∈ {`978`,`979`} so non-GS1 EAN-13s resolve `INVALID`, not `SUCCESS`).
- `test_gs1_prefix_rule` — `Section42Gs1Prefix` matches `"9780306406157"`, rejects `"1234567890123"`; `normalize()` returns digits unchanged.
- `test_isbn10_check_digit` — valid: `"0306406152"`, `"0849396409"`, `"080442957X"` (and lowercase `"080442957x"`); invalid: `"0306406153"`.
- `test_isbn10_normalize_conversion` — `Section6Isbn10CheckDigit().normalize(...)` maps `"0306406152" → "9780306406157"`, `"0849396409" → "9780849396403"`, `"080442957X" → "9780804429573"`.
- `test_range_rule_allocated` — `Section4RegistrantRange` matches `"9780110002224"` (group `0`, registrant `11` in the first `978-0` range) and its ISBN-10 equivalent `"0110002229"` (mod-11 check over `0,1,1,0,0,0,2,2,2` with weights 10..2 sums to 35 → check `9`; `_to_isbn13` converts it back to `9780110002224`).
- `test_range_rule_unallocated` — `Section4RegistrantRange` does NOT match `"9789990000000"`: the 978 prefix rules derive group `9990000`, and `GROUP_RULES` has no `978-9990000` entry. If the emitted snapshot derives a different group for `9990000`, pick any 978 value whose derived group key is absent from `GROUP_RULES` — the invariant under test is "missing group key → no match".

- `test_range_rule_requires_feature` — `Section4RegistrantRange.requires_features == frozenset({"include_range_validation"})`.
- `test_rule_conventions` — names/strategies/citations per table below; provenance: `iso_2108` PUBLICATION has `lifecycle=="active"`, `publication_year==2017`; `isbn_users_manual` PUBLICATION has `lifecycle=="superseded"`, `publication_year==2012`; `isbn_range_message` PUBLICATION has `kind=="registry"`, `version=="2026-08-05"`, `publication_year==2026`.

- [ ] **Step 2: GREEN — implement the three rule files**

Read `paxman/capabilities/Phone/rules/e164_ed2010.py` first for the two-rules-one-file pattern and the `Rule` base class contract (six enforced class attributes: `name`, `strategy`, `provenance`, `citation`, `target_grammars`, `requires_features`).

```python
# paxman/capabilities/ISBN/rules/iso_2108_ed2017.py
"""ISO 2108:2017 rules: ISBN-13 check digit and GS1 prefix."""

from paxman.core.domain import Contract, Provenance, Rule, RuleStrategy
from paxman.capabilities.ISBN.notation import ISBNNotation

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 2108:2017",
    kind="specification",
    reference_url="https://www.iso.org/standard/65483.html",
    version="2017",
    lifecycle="active",
    publication_year=2017,
)

_GS1_PREFIXES = frozenset({"978", "979"})


def _isbn13_check_digit(digits: str) -> bool:
    """mod-10 over the first 12 digits (weights 1, 3); check = (10 - S % 10) % 10."""
    weighted = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    return int(digits[12]) == (10 - weighted % 10) % 10


class Section53Isbn13CheckDigit(Rule[ISBNNotation]):
    """ISO 2108 Section 5.3 - ISBN-13 check digit (structure + prefix)."""

    name = "Section 5.3-isbn13-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 5.3 (ISBN-13 check digit)"
    target_grammars = frozenset({"isbn13_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        if notation.shape != "isbn13" or len(notation.digits) != 13:
            return False
        if notation.digits[:3] not in _GS1_PREFIXES:  # ISO 2108 §4.2 structure
            return False
        return _isbn13_check_digit(notation.digits)

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        return notation.digits


class Section42Gs1Prefix(Rule[ISBNNotation]):
    """ISO 2108 Section 4.2 - GS1 prefix is 978 or 979."""

    name = "Section 4.2-gs1-prefix"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4.2 (GS1 prefix)"
    target_grammars = frozenset({"isbn13_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        return notation.shape == "isbn13" and notation.digits[:3] in _GS1_PREFIXES

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        return notation.digits
```

```python
# paxman/capabilities/ISBN/rules/isbn_users_manual_ed2012.py
"""ISBN Users' Manual 2012 rule: ISBN-10 check digit (mod-11)."""

from paxman.core.domain import Contract, Provenance, Rule, RuleStrategy
from paxman.capabilities.ISBN.notation import ISBNNotation

PUBLICATION = Provenance(
    authority="International ISBN Agency",
    specification_name="ISBN Users' Manual",
    kind="specification",
    reference_url=(
        "https://www.isbn-international.org/sites/default/files/"
        "ISBN%20Manual%202012%20-corr.pdf"
    ),
    version="2012",
    lifecycle="superseded",  # ISBN-10 removed from the current standard (memo §10.5)
    publication_year=2012,
)


def _isbn10_check_digit(chars: str) -> bool:
    """mod-11 (weights 10..2 over the first 9); final char 0-9 or X (=10)."""
    total = sum(int(c) * (10 - i) for i, c in enumerate(chars[:9]))
    check = (11 - total % 11) % 11
    return chars[9].upper() == ("X" if check == 10 else str(check))


class Section6Isbn10CheckDigit(Rule[ISBNNotation]):
    """ISBN Users' Manual - ISBN-10 check digit."""

    name = "Section 6-isbn10-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 6 (ISBN-10 check digit)"
    target_grammars = frozenset({"isbn10_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        if notation.shape != "isbn10" or len(notation.digits) != 10:
            return False
        if not notation.digits[:9].isdigit():
            return False
        return _isbn10_check_digit(notation.digits)

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        """ISBN-10 -> ISBN-13: '978' + first 9 + recomputed mod-10 check digit."""
        base = "978" + notation.digits[:9]
        weighted = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base))
        return base + str((10 - weighted % 10) % 10)
```

```python
# paxman/capabilities/ISBN/rules/isbn_range_message_ed2026.py
"""ISBN Range Message rule: registrant-range issued-ness (LOOKUP_TABLE)."""

from paxman.core.domain import Contract, Provenance, Rule, RuleStrategy
from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.capabilities.ISBN.rules.data.range_message import (
    EAN_PREFIX_RULES,
    GROUP_RULES,
)

PUBLICATION = Provenance(
    authority="International ISBN Agency",
    specification_name="ISBN Range Message",
    kind="registry",
    reference_url="https://www.isbn-international.org/range_file_generation",
    version="2026-08-05",
    lifecycle="active",
    publication_year=2026,
)


def _find_length(rules: tuple[tuple[str, str, int], ...], digits: str) -> int | None:
    """Length of the first rule whose 7-digit window covers the digit prefix."""
    window = (digits + "0" * 7)[:7]
    for start, end, length in rules:
        if start <= window <= end:
            return length
    return None


class Section4RegistrantRange(Rule[ISBNNotation]):
    """ISBN Range Message - registrant range issued-ness (memo §4.3 algorithm)."""

    name = "Section 4-registrant-range"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "Section 4 (registrant range)"
    target_grammars = frozenset({"isbn13_recognition", "isbn10_recognition"})
    requires_features = frozenset({"include_range_validation"})

    def matches(self, notation: ISBNNotation, contract: Contract) -> bool:
        digits = self._to_isbn13(notation)
        if digits is None:
            return False
        prefix = digits[:3]
        if prefix not in EAN_PREFIX_RULES:
            return False
        rest = digits[3:]
        group_len = _find_length(EAN_PREFIX_RULES[prefix], rest)
        if group_len is None:
            return False
        group = rest[:group_len]
        registrant_rules = GROUP_RULES.get(f"{prefix}-{group}")
        if registrant_rules is None:
            return False
        return _find_length(registrant_rules, rest[group_len:]) is not None

    def normalize(self, notation: ISBNNotation, contract: Contract) -> str:
        digits = self._to_isbn13(notation)
        if digits is None:
            return notation.digits
        return digits

    @staticmethod
    def _to_isbn13(notation: ISBNNotation) -> str | None:
        if notation.shape == "isbn13":
            return notation.digits
        if notation.shape == "isbn10" and len(notation.digits) == 10:
            if not notation.digits[:9].isdigit():
                return None
            base = "978" + notation.digits[:9]
            weighted = sum(
                int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(base)
            )
            return base + str((10 - weighted % 10) % 10)
        return None
```

**Test-vector note:** the allocated vector `9780110002224` derives from the FIRST `978-0` range (`0000000-1999999`, length 2 → registrant `11`, hyphenation `978-0-11-000222-4`). Its ISBN-10 equivalent is `0110002229` (mod-11 check over `0,1,1,0,0,0,2,2,2` with weights 10..2 sums to 35 → check 9). For `test_range_rule_unallocated`, use `"9789990000000"`: the 978 prefix rules map `9990000` to group `9990000`, which has no `978-9990000` entry in `GROUP_RULES` → no match. If the emitted snapshot differs from that mapping, pick any 978 value whose derived group key is absent from `GROUP_RULES` — the invariant under test is "missing group key → no match".

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/isbn/test_rules.py
uv run ruff check paxman/capabilities/ISBN
uv run pyright paxman/capabilities/ISBN/rules
```

Commit: `feat(isbn): add ISBN validation rules`.

## Task 5: Grammars

**Files:**
- Create: `paxman/capabilities/ISBN/grammar/isbn13_recognition.py`
- Create: `paxman/capabilities/ISBN/grammar/isbn10_recognition.py`
- Create: `tests/capabilities/isbn/test_grammar.py`

**Purity gate (from the 08-04 recognition-homogeneity plan):** grammars do syntax only — extraction + separator/case normalization. No grammar imports from `rules`; no rule imports from `grammar`.

- [ ] **Step 1: RED — write the grammar tests** (`tests/capabilities/isbn/test_grammar.py`, mark `@pytest.mark.capability`, import both grammar classes)

ISBN-13 grammar:
- `test_isbn13_bare` — `"9780306406157"` → 1 match; `notation.shape == "isbn13"`, `notation.digits == "9780306406157"`, `start == 0`, `end == 13`, `raw_text == "9780306406157"`.
- `test_isbn13_hyphenated` — `"978-0-306-40615-7"` → `digits == "9780306406157"`.
- `test_isbn13_spaces` — `"978 0 306 40615 7"` → `digits == "9780306406157"`.
- `test_isbn13_label` — `"ISBN 9780306406157"` and `"ISBN-13: 978-0-306-40615-7"` each → 1 match.
- `test_isbn13_glued_label` — `"ISBN9780306406157"` → `[]` (the label must be separated from the digits).
- `test_isbn13_fourteen_digits` — `"97803064061577"` → `[]`.
- `test_isbn13_embedded_in_word` — `"abc9780306406157xyz"` → `[]`.
- `test_isbn13_multiple` — `"9780306406157 9780201310054"` → 2 matches, ascending `start`.
- `test_isbn13_span_invariants` — for every match, `len(raw_text) == end - start` and `0 <= start <= end`.
- `test_isbn13_empty` — `""` → `[]`.

ISBN-10 grammar:
- `test_isbn10_bare` — `"0306406152"` → `shape == "isbn10"`, `digits == "0306406152"`.
- `test_isbn10_hyphenated` — `"0-306-40615-2"` → `digits == "0306406152"`.
- `test_isbn10_x_fold` — `"080442957X"` → `digits == "080442957X"`; `"080442957x"` → `digits == "080442957X"`.
- `test_isbn10_label` — `"ISBN-10 0-306-40615-2"` → 1 match.
- `test_isbn10_eleven_digits` — `"03064061523"` → `[]`.
- `test_isbn10_span_invariants` — same as above.
- `test_isbn10_empty` — `""` → `[]`.

- [ ] **Step 2: GREEN — implement the two grammars**

```python
# paxman/capabilities/ISBN/grammar/isbn13_recognition.py
"""ISBN-13 recognition grammar."""

import re

from paxman.core.domain import Grammar, RecognitionMatch
from paxman.capabilities.ISBN.notation import ISBNNotation

# Optional "ISBN"/"ISBN-13" label — REQUIRES a separator, so glued labels
# like "ISBN9780306406157" do not match. Then exactly 13 digits with
# optional single hyphens/spaces between. The lookahead pins the end: the
# char after the 13th digit must not be a digit or separator, so 14+-digit
# runs fail. \b rejects matches embedded in a longer word.
_ISBN13_PATTERN = re.compile(
    r"\b(?:ISBN(?:-13)?[\s:-]+)?(?=(?:\d[ -]?){13}(?![\d -]))(?:\d[ -]?){13}\b",
    re.IGNORECASE,
)


class ISBN13RecognitionGrammar(Grammar[ISBNNotation]):
    """ISBN-13 recognition: 13-digit runs with optional separators/label."""

    name = "isbn13_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[ISBNNotation]]:
        matches = []
        for m in _ISBN13_PATTERN.finditer(text):
            digits = "".join(ch for ch in m.group(0) if ch.isdigit())
            if len(digits) != 13:
                continue
            matches.append(
                RecognitionMatch(
                    notation=ISBNNotation(shape="isbn13", digits=digits),
                    start=m.start(),
                    end=m.end(),
                    raw_text=m.group(0),
                )
            )
        return matches
```

```python
# paxman/capabilities/ISBN/grammar/isbn10_recognition.py
"""ISBN-10 recognition grammar."""

import re

from paxman.core.domain import Grammar, RecognitionMatch
from paxman.capabilities.ISBN.notation import ISBNNotation

# Optional "ISBN"/"ISBN-10" label (requires a separator), then exactly 10
# characters: 9 digits + a final digit or X. Lowercase x folds to X.
_ISBN10_PATTERN = re.compile(
    r"\b(?:ISBN(?:-10)?[\s:-]+)?(?=(?:\d[ -]?){9}[0-9Xx](?![\d -]))(?:\d[ -]?){9}[0-9Xx]\b",
    re.IGNORECASE,
)


class ISBN10RecognitionGrammar(Grammar[ISBNNotation]):
    """ISBN-10 recognition: 10-character runs (0-9, final may be X)."""

    name = "isbn10_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[ISBNNotation]]:
        matches = []
        for m in _ISBN10_PATTERN.finditer(text):
            cleaned = "".join(
                ch for ch in m.group(0) if ch.isdigit() or ch in "xX"
            ).upper()
            if len(cleaned) != 10:
                continue
            matches.append(
                RecognitionMatch(
                    notation=ISBNNotation(shape="isbn10", digits=cleaned),
                    start=m.start(),
                    end=m.end(),
                    raw_text=m.group(0),
                )
            )
        return matches
```

**Containment note:** the ISBN-10 grammar may match a 10-character sub-run inside an ISBN-13 match (e.g. the trailing `0-306-40615-7` of `978-0-306-40615-7`). This is EXPECTED and safe: the engine preserves cross-grammar overlaps, both shapes' rules normalize to the same 13-digit value, so the result is `SUCCESS`, never `AMBIGUOUS` (memo §7.2). Do not add grammar-level cross-grammar dedup — that is the engine's job.

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/isbn/test_grammar.py
uv run ruff check paxman/capabilities/ISBN
uv run pyright paxman/capabilities/ISBN/grammar
```

Commit: `feat(isbn): add ISBN recognition grammars`.

## Task 6: Capability wiring

**Files:**
- Create: `paxman/capabilities/ISBN/capability.py`
- Create: `tests/capabilities/isbn/test_capability.py`

The wiring mirrors `paxman/capabilities/Country/capability.py` exactly: module `__all__`, a staticmethod `create_contract` factory, `get_grammars()`/`get_rules()` returning fresh instances, and a `format_value()` seam. `hyphenate()` is a module-level helper in the capability file; it is presentation only and never touches candidate identity or provenance.

- [ ] **Step 1: RED — write the capability tests** (`tests/capabilities/isbn/test_capability.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISBN.capability import ISBNCapability`)

- `test_capability_name_version` — `ISBNCapability.name == "isbn"`, `.version == "1.0.0"`.
- `test_get_grammars` — `len(cap.get_grammars()) == 2`; names `{"isbn13_recognition", "isbn10_recognition"}`.
- `test_get_rules` — `len(cap.get_rules()) == 4`; names in order: `["Section 5.3-isbn13-check-digit", "Section 4.2-gs1-prefix", "Section 6-isbn10-check-digit", "Section 4-registrant-range"]`.
- `test_create_contract_defaults` — `c = ISBNCapability.create_contract()`; `c.include_isbn10 is True`; `c.include_range_validation is False`; `c.output_format == "isbn13"` (resolved by `CapabilityContract.__post_init__`); `c.active_grammars == ["isbn13_recognition", "isbn10_recognition"]`.
- `test_create_contract_feature_flags` — `create_contract(include_isbn10=False, include_range_validation=True)` → `include_isbn10 is False`, `include_range_validation is True`, `active_grammars == ["isbn13_recognition"]`.
- `test_create_contract_output_format` — `create_contract(output_format="hyphenated")` → `c.output_format == "hyphenated"`.
- `test_format_value_identity` — default `"isbn13"` and `None` both return the input unchanged: `format_value("9780306406157", "isbn13", notation) == "9780306406157"`, `format_value("9780306406157", None, notation) == "9780306406157"`.
- `test_format_value_hyphenated` — `format_value("9780110002224", "hyphenated", notation) == "978-0-11-000222-4"` (the Task 4 allocation vector — first `978-0` registrant range `00-19` → registrant `11`).
- `test_format_value_hyphenated_unregistered` — `format_value("9789990000000", "hyphenated", notation) == "9789990000000"` (no group rule → unchanged, no error).
- `test_format_value_hyphenated_unknown_prefix` — `format_value("1234567890123", "hyphenated", notation) == "1234567890123"` (no `123` prefix rules → unchanged).

Use a helper `notation = ISBNNotation(shape="isbn13", digits=value)` for the format tests.

- [ ] **Step 2: GREEN — implement `paxman/capabilities/ISBN/capability.py`**

```python
"""ISBN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISBN.contract import ISBNContract
from paxman.capabilities.ISBN.grammar.isbn10_recognition import ISBN10RecognitionGrammar
from paxman.capabilities.ISBN.grammar.isbn13_recognition import ISBN13RecognitionGrammar
from paxman.capabilities.ISBN.notation import ISBNNotation
from paxman.capabilities.ISBN.rules.data.range_message import (
    EAN_PREFIX_RULES,
    GROUP_RULES,
)
from paxman.capabilities.ISBN.rules.isbn_range_message_ed2026 import (
    Section4RegistrantRange,
)
from paxman.capabilities.ISBN.rules.isbn_users_manual_ed2012 import (
    Section6Isbn10CheckDigit,
)
from paxman.capabilities.ISBN.rules.iso_2108_ed2017 import (
    Section42Gs1Prefix,
    Section53Isbn13CheckDigit,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ISBNCapability", "ISBNContract", "ISBNNotation"]


def _find_length(rules: tuple[tuple[str, str, int], ...], digits: str) -> int | None:
    """Length of the first rule whose 7-digit window covers the digit prefix."""
    window = (digits + "0" * 7)[:7]
    for start, end, length in rules:
        if start <= window <= end:
            return length
    return None


def hyphenate(value: str) -> str:
    """Render a 13-digit ISBN with Range Message hyphens (memo §4.3).

    Unregistered prefixes/groups/registrants pass through unchanged (bare
    digits) — hyphenation is presentation, never a validity signal.
    """
    prefix = value[:3]
    rest = value[3:]
    prefix_rules = EAN_PREFIX_RULES.get(prefix)
    if prefix_rules is None:
        return value
    group_len = _find_length(prefix_rules, rest)
    if group_len is None:
        return value
    group = rest[:group_len]
    registrant_rules = GROUP_RULES.get(f"{prefix}-{group}")
    if registrant_rules is None:
        return value
    registrant_len = _find_length(registrant_rules, rest[group_len:])
    if registrant_len is None:
        return value
    registrant = rest[group_len : group_len + registrant_len]
    publication = rest[group_len + registrant_len : 10]
    check = rest[10]
    return f"{prefix}-{group}-{registrant}-{publication}-{check}"


class ISBNCapability(Capability[ISBNNotation]):
    """ISBN canonicalization capability.

    Canonicalizes ISBN-13 and legacy ISBN-10 input to the bare 13-digit
    form with full provenance.
    """

    name = "isbn"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[ISBNNotation]]:
        return [ISBN13RecognitionGrammar(), ISBN10RecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISBNNotation]]:
        return [
            Section53Isbn13CheckDigit(),
            Section42Gs1Prefix(),
            Section6Isbn10CheckDigit(),
            Section4RegistrantRange(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        include_isbn10: bool = True,
        include_range_validation: bool = False,
    ) -> ISBNContract:
        """Factory method for creating contracts with proper defaults."""
        return ISBNContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            include_isbn10=include_isbn10,
            include_range_validation=include_range_validation,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ISBNNotation,
    ) -> str:
        """Render the bare 13-digit canonical value in the requested format.

        The default ``"isbn13"`` path is the identity. ``"hyphenated"``
        applies Range Message longest-match hyphenation. Never affects
        candidate identity or provenance.
        """
        if output_format == "hyphenated":
            return hyphenate(value)
        return value
```

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/isbn/test_capability.py
uv run ruff check paxman/capabilities/ISBN
uv run pyright paxman/capabilities/ISBN
```

Commit: `feat(isbn): wire ISBNCapability with create_contract and format_value`.

## Task 7: Registration — capability registry, pytest marker, exports test

**Files:**
- Modify: `paxman/capabilities/__init__.py`
- Modify: `pyproject.toml`
- Modify: `tests/unit/test_capability_exports.py`

- [ ] **Step 1: RED — extend the exports test** (`tests/unit/test_capability_exports.py`)

Change the import to `from paxman.capabilities import Email, ISBN, Phone` and add a class mirroring the existing Email/Phone classes:

```python
class TestISBNCapabilityExports:
    @pytest.mark.unit
    def test_isbn_capability_importable(self) -> None:
        """ISBN capability is importable from paxman.capabilities."""
        assert ISBN is not None

    @pytest.mark.unit
    def test_isbn_capability_name(self) -> None:
        """ISBN capability has correct name."""
        assert ISBN.name == "isbn"
```

- [ ] **Step 2: GREEN — wire the registry**

`paxman/capabilities/__init__.py` — add the ISBN alias import in alphabetical position and append `"ISBN"` to `__all__` in alphabetical position (keep every existing line untouched):

```python
from paxman.capabilities.Country.capability import CountryCapability as Country
from paxman.capabilities.Date.capability import DateCapability as Date
from paxman.capabilities.Email.capability import EmailCapability as Email
from paxman.capabilities.ISBN.capability import ISBNCapability as ISBN
from paxman.capabilities.Phone.capability import PhoneCapability as Phone

__all__ = ["Country", "Date", "Email", "ISBN", "Phone"]
```

`pyproject.toml` — add the ISBN marker after the country marker (alphabetical):

```toml
    "country: country capability tests",
    "isbn: isbn capability tests",
```

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/capabilities/isbn
uv run ruff check paxman/capabilities/__init__.py
uv run pyright paxman/capabilities
```

Sanity: `python -c "from paxman.capabilities import ISBN; print(ISBN.name)"` → `isbn`.

Commit: `feat(isbn): register ISBN capability and pytest marker`.

## Task 8: Integration tests — resolution map and feature gating

**Files:**
- Modify: `tests/integration/test_pipeline.py`
- Modify: `tests/integration/test_feature_gating.py`

Both files already have the autouse `_clean_registry` fixture and `run_capability` imports; add `from paxman.capabilities.ISBN.capability import ISBNCapability` to each import block. This task IS the memo §7.6 resolution map — every row below is a locked semantic.

- [ ] **Step 1: RED — `tests/integration/test_pipeline.py`**

Add a `TestISBNPipeline` class (mark every test `@pytest.mark.integration`):

| Test | Input | Contract | Expected |
|------|-------|----------|----------|
| `test_isbn13_bare_success` | `"9780306406157"` | default | `SUCCESS`, `"9780306406157"`, ≥1 candidate |
| `test_isbn13_hyphenated_success` | `"978-0-306-40615-7"` | default | `SUCCESS`, `"9780306406157"` |
| `test_isbn13_labeled_success` | `"ISBN 9780306406157"` | default | `SUCCESS`, `"9780306406157"` |
| `test_isbn10_success` | `"0306406152"` | default | `SUCCESS`, `"9780306406157"` |
| `test_isbn10_x_folds` | `"080442957x"` | default | `SUCCESS`, `"9780804429573"` |
| `test_cross_shape_collapse_success` | `"ISBN 978-0-306-40615-7 and 0-306-40615-2"` | default | `SUCCESS`, `"9780306406157"` — the ISBN-10 sub-run is contained in the ISBN-13 match; both normalize to the same value, so the result is SUCCESS, never AMBIGUOUS (memo §7.2) |
| `test_bad_check_digit_invalid` | `"9780306406158"` | default | `INVALID`, no candidates |
| `test_unallocated_range_default_success` | `"9789990000009"` | default | `SUCCESS`, `"9789990000009"` — valid check digit; range rule off by default; range is a provenance amplifier, not a validity gate |
| `test_unallocated_range_with_validation_success` | `"9789990000009"` | `include_range_validation=True` | `SUCCESS`, `"9789990000009"` — range rule adds no provenance (unallocated) but the check-digit rule still validates |
| `test_two_books_ambiguous` | `"9780306406157 and 9780201310054"` | default | `AMBIGUOUS`, `canonicalized_value is None`, `{c.value for c in result.candidates} == {"9780306406157", "9780201310054"}` |
| `test_missing_yields_missing` | `"no isbn here"` | default | `MISSING`, no candidates |
| `test_hyphenated_output_format` | `"978-0-11-000222-4"` | `output_format="hyphenated"` | `SUCCESS`, `canonicalized_value == "978-0-11-000222-4"` (formatting precedes dedup; the bare value stays the candidate identity) |
| `test_isbn10_conversion_0849396409` | `"0849396409"` | default | `SUCCESS`, `"9780849396403"` |

Also append two rows to the existing `TestReplayAndCandidateOrder.test_repeated_run_is_byte_identical` parametrize list:

```python
(
    pytest.param(
        ISBNCapability,
        lambda: ISBNCapability.create_contract(output_format="hyphenated"),
        "978-0-11-000222-4",
        id="isbn-hyphenated",
    ),
)
(
    pytest.param(
        ISBNCapability,
        lambda: ISBNCapability.create_contract(),
        "0306406152",
        id="isbn10-default",
    ),
)
```

- [ ] **Step 2: RED — `tests/integration/test_feature_gating.py`**

Add a `TestISBNFeatureGates` class (mark `@pytest.mark.integration`), mirroring `test_country_pinned_disabled_historical_yields_invalid`:

- `test_isbn_range_pinned_disabled_yields_invalid` — `pinned_rules=("Section 4-registrant-range",)`, `include_range_validation=False`, input `"9780110002224"` → `INVALID`, `canonicalized_value is None`. (Feature filtering applies after pinning: the pinned range rule is dropped, so no authority validates. This is the engine-enforced gate — same mechanism as Country historical.)
- `test_isbn_range_pinned_enabled_yields_success` — same pin, `include_range_validation=True`, input `"9780110002224"` → `SUCCESS`, `"9780110002224"`.
- `test_isbn10_disabled_yields_missing` — `include_isbn10=False`, input `"0306406152"` → `MISSING` (grammar-level gate: `active_grammars == ("isbn13_recognition",)`; nothing recognized).
- `test_isbn10_enabled_yields_success` — default contract, input `"0306406152"` → `SUCCESS`, `"9780306406157"`.

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/integration/test_pipeline.py tests/integration/test_feature_gating.py
uv run ruff check tests/integration
```

Commit: `feat(isbn): add integration resolution-map and feature-gating tests`.

## Task 9: Property tests (Hypothesis)

**Files:**
- Create: `tests/property/test_isbn_properties.py`

Mirror the existing property test style: module-level `@given` strategies, `@pytest.mark.property`, deterministic (no network — the Range Message data module is shipped). Generation helpers (documented against ISO 2108 §5.3 / Users' Manual §6):

```python
def _check_digit_isbn13(first12: str) -> str:
    """ISO 2108 §5.3 check digit: alternating 1/3 weights, mod 10."""
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(first12))
    return str((10 - total % 10) % 10)


def _check_digit_isbn10(first9: str) -> str:
    """Users' Manual §6 check digit: weights 10..2, mod 11; 10 -> 'X'."""
    total = sum(int(d) * (10 - i) for i, d in enumerate(first9))
    rem = total % 11
    if rem == 0:
        return "0"
    return str(11 - rem) if 11 - rem < 10 else "X"
```

Tests:
- `test_isbn13_grammar_recognized_implies_check_digit` — `@given(text())`: if `run_capability(text, ISBNCapability.create_contract())` is `SUCCESS` and the producing grammar is `isbn13_recognition`, then the canonical value's last digit equals `_check_digit_isbn13(value[:12])`. (Conditional property — only asserts on SUCCESS runs.)
- `test_hyphenate_round_trips_digits` — `@given(digits(13))`: `"".join(c for c in hyphenate(value) if c.isdigit()) == value` (pure function; registered or not, hyphenation never alters digits).
- `test_isbn10_and_converted_isbn13_agree` — `@given(digits(9))`: build a valid ISBN-10 `first9 + _check_digit_isbn10(first9)`; canonicalizing it and canonicalizing `"978" + first9 + _check_digit_isbn13("978" + first9)` both yield `SUCCESS` with the same canonical value.
- `test_replay_determinism` — `@given(text())`: two consecutive `run_capability` calls on the same input/contract produce identical `replay_hash`, status, and candidates.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

Import `hyphenate` from `paxman.capabilities.ISBN.capability` (it is a public helper of the capability module — do NOT import the `_find_length` private). Verify + commit:

```bash
uv run pytest tests/property/test_isbn_properties.py
uv run ruff check tests/property
```

Commit: `feat(isbn): add property tests for recognition, hyphenation, and replay safety`.

## Task 10: Replay-hash baseline

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

**Files:**
- Modify: `tests/integration/test_default_replay_hashes.py`

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

The `replay_hash` is the engine's behavioral contract. This task ADDS the ISBN baseline; the five existing literals (`date`, `country`, `email`, `ip`, `phone`) MUST NOT change — the ISBN capability is additive and touches no existing pipeline code. Keep the module's NOTE comment about IP untouched.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

- [ ] **Step 1: RED — register the ISBN case**

Add the import `from paxman.capabilities.ISBN.capability import ISBNCapability` to the import block, and:

```python
BASELINE_HASHES = {
    ...
    "phone": "01cd035c735461929e5c2974e3b65fbbd615c389c15c3a650113e5050057df7a",
    "isbn": "",
}

CASES = [
    ...
    ("phone", PhoneCapability, "+1 555 123 4567"),
    ("isbn", ISBNCapability, "9780306406157"),
]
```

Run `uv run pytest tests/integration/test_default_replay_hashes.py -k isbn` — it fails with the actual hash in the assertion output (`AssertionError: assert '' == '<64-hex-hash>'` or `KeyError` on the empty literal).

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

- [ ] **Step 2: GREEN — capture and pin the literal**

Replace `"isbn": ""` with the `<64-hex-hash>` reported by the failure. The case asserts `status == Resolution.SUCCESS` and `replay_hash == BASELINE_HASHES["isbn"]` — the canonical value is `"9780306406157"` with provenance from the two ISO 2108:2017 rules that validate it (Section 5.3-isbn13-check-digit and Section 4.2-gs1-prefix); the ISBN Users' Manual rule targets the isbn10 grammar only and the range rule is gated behind `include_range_validation` (off by default).

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

- [ ] **Step 3: Verify**

```bash
uv run pytest tests/integration/test_default_replay_hashes.py
```

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

All six cases pass. The five pre-existing literals are byte-identical to their 2026-08-04 captures — confirm the diff shows only the added ISBN lines plus the docstring date note ("Literals captured 2026-08-04 … ISBN baseline added 2026-08-05").

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

Commit: `feat(isbn): pin ISBN replay-hash baseline`.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

## Task 11: Documentation and final gates

**Files:**
- Modify: `HOW_TO_ADD_NEW_CAPABILITY.md` (only if a drift is found — see below)
- Modify: `README.md`

- [ ] **Step 1: Verify the HOW-TO span contract**

`HOW_TO_ADD_NEW_CAPABILITY.md` Step 4 already documents the span-bearing contract that the ISBN grammars implement (span-bearing `RecognitionMatch`, `len(raw_text) == end - start`, syntax-only grammars, "longer wins" engine dedup, rules own meaning). Read the section; update ONLY if you find drift against the shipped ISBN grammars. Add one sentence to Step 4 noting the ISBN cross-grammar containment case is expected (an ISBN-10 sub-run inside an ISBN-13 match) and resolves to SUCCESS because both shapes normalize to the same value.

- [ ] **Step 2: README — add ISBN to the capabilities table**

Add a row to the capabilities table (alphabetical, between IP and Phone):

```text
| **ISBN** | ISBN numbers | 2 (isbn13, isbn10) | 4 | ISO 2108, ISBN Users' Manual, ISBN Range Message |
```

And a brief `### ISBN Capability` subsection mirroring the Country/Phone ones:

```python
from paxman.capabilities import ISBN

register_capability(ISBN())

# Bare ISBN-13
contract = ISBN.create_contract()
result = paxman.canonicalize("9780306406157", contract)
# → "9780306406157"

# Legacy ISBN-10 converts to ISBN-13
contract = ISBN.create_contract()
result = paxman.canonicalize("0306406152", contract)
# → "9780306406157"

# Range Message hyphenation (presentation only)
contract = ISBN.create_contract(output_format="hyphenated")
result = paxman.canonicalize("9780110002224", contract)
# → "978-0-11-000222-4"

# Enable registrant-range provenance (ISBN Range Message authority)
contract = ISBN.create_contract(include_range_validation=True)
result = paxman.canonicalize("9780110002224", contract)
# → SUCCESS with Section 4-registrant-range provenance

# Disable ISBN-10 recognition
contract = ISBN.create_contract(include_isbn10=False)
result = paxman.canonicalize("0306406152", contract)
# → Status: MISSING
```

- [ ] **Step 3: Final gates — run the full toolchain from the repo root**

```bash
uv run pytest
uv run ruff check paxman tests
uv run pyright
uv run pytest --cov=paxman --cov-branch --cov-fail-under=95
```

Run the repo's import-linter contract check (the command configured in `pyproject.toml`/CI; commonly `uv run lint-imports`). Every gate must pass. `paxman/capabilities/ISBN/rules/data/` intentionally escapes the `paxman/capabilities/*/rules/*.py` purity glob — the data module's `test_no_output_format_token` guards it instead.

Commit: `docs(isbn): document ISBN capability and verify span contract`.

---

## Plan Gaps (design-authority discrepancies — recorded for review)

Two discrepancies exist between the design memo (`docs/research/2026-08-05-isbn-canonicalization.md`) and the verified ground truth this plan pins. Both are intentional: the plan follows the verified on-disk reality and flags the memo for correction.

1. **Range Message fetch metadata.** The memo's §7.3 table logs an earlier fetch (serial `6ae30b93…`, time 08:13:31); the snapshot committed at `/tmp/opencode/range_message.xml` carries serial `6f6063f3-6f2a-4619-8bd9-116a3addc690` and `Wed, 5 Aug 2026 08:25:28 BST`. Task 3 step-1 verifies the on-disk values; the memo's table should be corrected to match when convenient.

2. **Registrant-range padding.** The memo §4.2 claims 6-digit registrant padding; the actual XML zero-pads ALL ranges to 7 digits (verified). The generator reads the `Length` element and `_find_length` slices windows of up to 7 digits, so hyphenation output is unaffected; Task 3's `test_ranges_seven_digit` is the tripwire that keeps this documented. The memo's §4.2 text should be corrected to "7-digit zero-padding".
