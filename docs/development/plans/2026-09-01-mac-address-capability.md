# MAC Address Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Research basis:** [`docs/development/research/2026-08-31-mac-address-canonicalization.md`](../research/2026-08-31-mac-address-canonicalization.md) (updated 2026-09-01 with the review findings: resolved 802-2024 catalogue URL, 802-1990 lineage marked not-fetched, EUI tutorial downgraded to secondary, `mac_midrun()` factory recommendation). Section references below ("Research section N") point at that report.

**Goal:** Ship a new `MacAddress` capability that recognizes the tolerant human MAC surface (case, colon/hyphen/Cisco-tri-dot/bare separators, optional fused `MAC` label, EUI-64 8-octet family, bit-reversed Token-Ring/FDDI spellings as themselves), validates strictly via IEEE Std 802-2024 §8.2 structure (12 or 16 uppercase hex digits, exactly 6 or 8 octets — no checksum, no bit gating: I/G and U/L are predicates), canonicalizes to colon-separated uppercase octets (`00:1A:2B:3C:4D:5E`, 8 groups for EUI-64) with `hyphen`/`bare`/`cisco`/`eui64`/`bit_reversed` offered formats, provenance first, deterministic.

**Architecture:** Single `PipelineGrammar` (`RegexStage` + `StandardPre(empty_guard=True)` + custom `BoundaryGuard.mac_midrun()` both sides) emitting `MacAddressNotation(compact, shape)` where `compact` is the 12- or 16-hex uppercase collapse of the match and `shape` is `"eui48"`/`"eui64"`. Eight shape branches (4 separators x 2 lengths, bare split 16-before-12) with per-branch hard-coded separators (mixed separators can never match — the Python-re equivalent of validator.js's backreference `\1` and Go's `s[2]` dispatch, no group-number collisions). A 48-bit-only truncation guard `(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))` blocks the "separator + 2 terminating hex digits" signature (truncated final octet of a longer run) while EUI-64 claims stay exempt (Home Assistant `{ieee}-{endpoint_id}` suffix). One mandatory `PARSER` rule `Section82EUIStructure` (structure only: length, charset, shape agreement; never rejects broadcast/nil/multicast/local/FF-FE) with `target_semantics={"mac_address_recognition"}`. `MacAddressCapability.format_value` renders `colon` identity vs `hyphen`/`bare`/`cisco`/`eui64` (FF-FE expansion from EUI-48, identity from EUI-64)/`bit_reversed` (RFC 2469 per-octet swap). `MacAddressContract` with `DEFAULT_OUTPUT_FORMAT="colon"` and `OFFERED_OUTPUT_FORMATS=frozenset({"hyphen", "bare", "cisco", "eui64", "bit_reversed"})`. No `include_oui_validation` in v1 — the OUI registry layer is deferred exactly like BIC's SWIFT Directory (Research section 5.4, 13 decision 6; refresh procedure documented, not implemented).

**Tech Stack:** Python 3.11+, `uv`, `hatchling`, `ruff`, `pyright` strict, `import-linter`, `pytest` 95% coverage gates, `hypothesis` property tests.

---

## File Structure

```
paxman/core/grammar/boundary.py               # MODIFY: add mac_midrun() factory (Task 3 Step 1)
paxman/capabilities/MacAddress/
├── __init__.py              # re-exports; scaffolder edits paxman/capabilities/__init__.py
├── notation.py              # MacAddressNotation — frozen+slots, compact + shape
├── contract.py              # MacAddressContract(CapabilityContract) — colon default, 5 offered
├── capability.py            # MacAddressCapability — get_grammars/get_rules/create_contract/format_value
├── grammar/
│   ├── __init__.py
│   └── mac_address_recognition.py   # PipelineGrammar[MacAddressNotation] single grammar
└── rules/
    ├── __init__.py
    └── ieee_802_ed2024.py   # PUBLICATION + Section82EUIStructure (PARSER, structure only)

tests/capabilities/mac_address/
├── __init__.py
├── test_notation.py
├── test_contract.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py
tests/unit/test_boundary_guards.py            # MODIFY: mac_midrun() guard tests (Task 3)
tests/integration/test_mac_address_capability.py  # MISSING/INVALID/SUCCESS + MultipleMentionsError, year filter
tests/property/test_mac_address_properties.py     # hypothesis: valid generation, spelling equivalence, bit_reversed involution
```

**Created vs Modified:**
- **Create:** All `paxman/capabilities/MacAddress/*` files (via `tools/new_capability.py` then domain fill; the scaffold `rules/ieee_ed2024.py` placeholder is renamed to `ieee_802_ed2024.py` in Task 4 Step 0)
- **Modify:** `paxman/core/grammar/boundary.py` (add `mac_midrun()` factory — one factory per distinct semantic variant convention, `phone_national()` precedent; direct `BoundaryGuard(lookbehind=..., lookahead=...)` construction in the grammar file is the documented fallback if core review rejects the core change, Research section 4.2 construction note), `paxman/capabilities/__init__.py` (alphabetical export, scaffolder does it), `tests/unit/test_boundary_guards.py` (mac_midrun coverage), `tests/unit/test_capability_exports.py` (add `MacAddress` import + `TestMacAddressCapabilityExports` + expected-set entry — fails once the export exists by design), `tests/unit/test_capability_surface.py` (auto-wired by scaffolder), `CONTEXT.md` (notation bullet + capability table row + grammar table), `README.md` (capabilities table row: grammars count `1 (EUI-48/EUI-64)`), `docs/development/MILESTONE.md` (MacAddress row)
- **Test:** `tests/capabilities/mac_address/*` (marked `capability`), `tests/integration/test_mac_address_capability.py` (marked `integration`, per-test registration), `tests/property/test_mac_address_properties.py`
- **Not touched in v1:** `paxman/api/bootstrap.py` `_SHIPPED` deliberately NOT touched (shipped but not bootstrapped, ISSN/IBAN/BIC precedent — Task 7 registers directly), `rules/data/` + `ieee_oui_registry_ed2026.py` + `include_oui_validation` contract field intentionally deferred (refresh procedure documented in Task 4 Step 4 but not implemented), `modified_eui64` format deferred to a community extension (Research section 13 decision 7), InfiniBand 20-octet / 24-bit-word / whitespace-separator / 1-digit-octet forms deferred to `extra_grammars` (Research section 2.1 DEFER rows)

---

### Task 0: Scaffold and Baseline

**Files:**
- Create: `paxman/capabilities/MacAddress/*` (via scaffolder)
- Modify: `paxman/capabilities/__init__.py` (auto edited)
- Test: `tests/capabilities/mac_address/*` stubs (auto generated)

- [ ] **Step 1: Run scaffolder**

```bash
uv run python tools/new_capability.py MacAddress --name mac_address \
    --authority "IEEE" --spec-name "IEEE Std 802-2024" \
    --spec-url "https://standards.ieee.org/ieee/802/10894" \
    --publication-year 2024 --default-format colon
```

Expected: prints `Generated capability skeleton:` followed by 13 file paths (9 package files plus 4 test stubs) and `paxman/capabilities/__init__.py (wired)`. Verify `ls paxman/capabilities/MacAddress/` lists `notation.py contract.py capability.py grammar/ rules/`.

Two scaffolder byproducts to know about:
- It also wires `tests/unit/test_capability_surface.py` (`_wire_surface_guard` adds the `_CAPABILITY_SURFACES` entry), no manual edit needed there.
- It derives the rule file name from `--authority "IEEE"` to `rules/ieee_ed2024.py` with placeholder class `MacAddressRule` (`Section 1-overview`, `TODO(scaffold)` markers). Task 4 Step 0 renames it to `ieee_802_ed2024.py`, do not leave the placeholder behind.
- It does **not** patch `tests/unit/test_capability_exports.py`, once `MacAddress` is in `__all__` that gate fails by design, Task 6 Step 1 patches it.

- [ ] **Step 2: Run baseline lint and type on scaffold**

```bash
uv run ruff check paxman/capabilities/MacAddress/ --fix
uv run pyright paxman/capabilities/MacAddress/
uv run pytest tests/capabilities/mac_address/ -v
```

Expected: `ruff` clean or auto fixed, `pyright` 0 errors (stub passes), pytest stubs pass (scaffold placeholder `test_notation.py` checks `value`).

- [ ] **Step 3: Commit scaffold**

```bash
git add paxman/capabilities/MacAddress/ paxman/capabilities/__init__.py tests/capabilities/mac_address/
git commit -m "feat(mac_address): scaffold MacAddress capability via tools/new_capability.py"
```

---

### Task 1: Notation — MacAddressNotation

**Files:**
- Modify: `paxman/capabilities/MacAddress/notation.py`
- Test: `tests/capabilities/mac_address/test_notation.py`

Research section 3.1: `compact` is 12 (`shape="eui48"`) or 16 (`shape="eui64"`) uppercase `[0-9A-F]` hex digits; `shape` is the length discriminator mirroring the ISBN two-length precedent. Frozen plus slots, both fields `str`. No validation in `__post_init__` beyond the type shape — the grammar owns stripping and uppercasing, rules own structure and (deferred) registry membership. Derived rule-side values (`compact[:6]` OUI, `int(compact[0:2], 16) & 0x02` U/L, `& 0x01` I/G) are documented in the docstring but NOT frozen into fields (no derivable data in the notation, BIC-full-decomposition rejection, Research section 3.1).

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/mac_address/test_notation.py
import pytest
from dataclasses import FrozenInstanceError

from paxman.capabilities.MacAddress.notation import MacAddressNotation

pytestmark = [pytest.mark.capability]


def test_creates_with_fields():
    n = MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")
    assert n.compact == "001A2B3C4D5E"
    assert n.shape == "eui48"
    n64 = MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64")
    assert n64.compact == "001A2B3C4D5E6677"
    assert n64.shape == "eui64"


def test_is_frozen():
    n = MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        n.shape = "eui64"  # type: ignore[misc]


def test_equality():
    assert MacAddressNotation(
        compact="001A2B3C4D5E", shape="eui48"
    ) == MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")
    assert MacAddressNotation(
        compact="001A2B3C4D5E", shape="eui48"
    ) != MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64")


def test_hashable():
    s = {
        MacAddressNotation(compact="001A2B3C4D5E", shape="eui48"),
        MacAddressNotation(compact="001A2B3C4D5E", shape="eui48"),
        MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64"),
    }
    assert len(s) == 2


def test_has_slots():
    assert hasattr(MacAddressNotation, "__slots__")
```

- [ ] **Step 2: Run test — expect ImportError (red)**

```bash
uv run pytest tests/capabilities/mac_address/test_notation.py -v
```

- [ ] **Step 3: Implement the notation**

```python
# paxman/capabilities/MacAddress/notation.py
"""MAC address notation - grammar-normalized compact hex form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MacAddressNotation:
    """MAC address notation - compact plus shape discriminator.

    ``compact`` is the full identifier, uppercase hex, separators stripped:
    exactly 12 hex digits (EUI-48) or 16 hex digits (EUI-64).
    ``shape`` discriminates the two identifier lengths ("eui48" / "eui64"),
    mirroring the ISBN two-length precedent.

    The grammar never validates OUI membership or interprets the U/L and I/G
    bits; rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    Derived rule-side values: OUI/first block = ``compact[:6]``; U/L bit =
    ``int(compact[0:2], 16) & 0x02``; I/G bit = ``int(compact[0:2], 16) & 0x01``.
    """

    compact: str  # e.g. "001A2B3C4D5E" (12) or "001A2B3C4D5E6677" (16) - [0-9A-F]
    shape: str  # "eui48" or "eui64" - length discriminator
```

- [ ] **Step 4: Run test — green; commit**

```bash
uv run pytest tests/capabilities/mac_address/test_notation.py -v
uv run ruff check paxman/capabilities/MacAddress/notation.py tests/capabilities/mac_address/test_notation.py
uv run pyright paxman/capabilities/MacAddress/notation.py
git add paxman/capabilities/MacAddress/notation.py tests/capabilities/mac_address/test_notation.py
git commit -m "feat(mac_address): MacAddressNotation compact + shape frozen-slots notation"
```

---

### Task 2: Contract — MacAddressContract

**Files:**
- Modify: `paxman/capabilities/MacAddress/contract.py`
- Test: `tests/capabilities/mac_address/test_contract.py`

Research section 6.1: `colon` default (dominant interchange form), `OFFERED_OUTPUT_FORMATS = frozenset({"hyphen", "bare", "cisco", "eui64", "bit_reversed"})` (alternatives exclude the default). `@dataclass(frozen=True)` WITHOUT `slots=True` (base `super().__post_init__` incompatible). No grammar-toggle fields (single always-active grammar → `active_grammars` omitted, base `None` runs every shipped grammar). No `include_oui_validation` in v1 (registry layer deferred, see Task 4 Step 4). Frozen dataclass without slots, `capability_name="mac_address"` via `field(default=..., init=False)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/mac_address/test_contract.py
import pytest

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults():
    c = MacAddressContract()
    assert c.capability_name == "mac_address"
    assert c.output_format == "colon"
    assert c.active_grammars is None
    assert c.excluded_rules == []
    assert c.pinned_rules is None
    assert c.year is None
    assert c.extra_grammars == []


def test_class_variables():
    assert MacAddressContract.DEFAULT_OUTPUT_FORMAT == "colon"
    assert MacAddressContract.OFFERED_OUTPUT_FORMATS == frozenset(
        {"hyphen", "bare", "cisco", "eui64", "bit_reversed"}
    )


@pytest.mark.parametrize(
    ("fmt", "expected"),
    [
        (None, "colon"),
        ("default", "colon"),
        ("colon", "colon"),
        ("hyphen", "hyphen"),
        ("bare", "bare"),
        ("cisco", "cisco"),
        ("eui64", "eui64"),
        ("bit_reversed", "bit_reversed"),
    ],
)
def test_output_format_resolution(fmt, expected):
    assert MacAddressContract(output_format=fmt).output_format == expected


@pytest.mark.parametrize("fmt", ["unix", "", "None", "none", "eui-64", "Mac"])
def test_output_format_invalid_raises(fmt):
    with pytest.raises(ContractError):
        MacAddressContract(output_format=fmt)


def test_is_frozen():
    c = MacAddressContract()
    with pytest.raises(Exception):
        c.output_format = "hyphen"  # type: ignore[misc]
```

- [ ] **Step 2: Run test — expect ImportError (red)**

```bash
uv run pytest tests/capabilities/mac_address/test_contract.py -v
```

- [ ] **Step 3: Implement the contract**

```python
# paxman/capabilities/MacAddress/contract.py
"""User-facing contract for the MacAddress capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class MacAddressContract(CapabilityContract):
    """User-facing contract for the MacAddress capability.

    ``colon`` (uppercase octets) is the canonical default; the offered
    formats are presentation-only re-insertions onto the rule-normalized
    colon form (``eui64`` inserts FF:FE from an EUI-48 and is identity for
    an EUI-64; ``bit_reversed`` is the RFC 2469 per-octet swap; both are
    deterministic value transforms). No grammar-toggle fields: the single
    shipped grammar is always active (base ``active_grammars is None``).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "colon"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"hyphen", "bare", "cisco", "eui64", "bit_reversed"}
    )

    capability_name: str = field(default="mac_address", init=False)
    # Deferred with the OUI registry layer (Research section 5.4 / 13
    # decision 6): include_oui_validation: bool = False
```

- [ ] **Step 4: Run test — green; commit**

```bash
uv run pytest tests/capabilities/mac_address/test_contract.py -v
uv run pyright paxman/capabilities/MacAddress/contract.py
git add paxman/capabilities/MacAddress/contract.py tests/capabilities/mac_address/test_contract.py
git commit -m "feat(mac_address): MacAddressContract colon default + 5 offered formats"
```

---

### Task 3: Grammar — mac_address_recognition (+ core mac_midrun guard factory)

**Files:**
- Modify: `paxman/core/grammar/boundary.py` (add `mac_midrun()` factory)
- Modify: `tests/unit/test_boundary_guards.py` (factory tests)
- Create: `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py`
- Modify: `paxman/capabilities/MacAddress/grammar/__init__.py` (re-export)
- Test: `tests/capabilities/mac_address/test_grammar.py`

Research section 4.2 (pattern **validated by execution** in the research session — 27 positive / 26 negative vectors; the block below is the validated pattern with the `mac_midrun()` factory substituted for direct construction). Key invariants: per-separator branches are internally uniform (mixed separators can never match); 64-bit branches precede 48-bit branches and 16-hex bare precedes 12-hex (longest-first at each scan position; engine within-grammar longer-wins containment dedup is the second safety net); the truncation guard applies to 48-bit branches ONLY (EUI-64 claims exempt for the Home Assistant `{ieee}-{endpoint_id}` shape); the mid-run lookbehind `(?<![0-9A-Fa-f][-.:])` blocks tail claims of longer runs while leaving the fused `MAC` label unaffected (lookbehinds constrain only the match start).

- [ ] **Step 1: Add the mac_midrun() factory to boundary.py (core, test first)**

Add to `tests/unit/test_boundary_guards.py` (red):

```python
def test_mac_midrun_guard_blocks_tail_of_longer_run():
    import re

    from paxman.core.grammar.boundary import BoundaryGuard

    guard = BoundaryGuard.mac_midrun()
    assert guard.lookbehind == r"(?<!\w)(?<![0-9A-Fa-f][-.:])"
    assert guard.lookahead == r"(?!\w)"
    pattern = re.compile(
        guard.lookbehind
        + r"(?P<c>(?:[0-9A-F]{2}:){5}[0-9A-F]{2})"
        + guard.lookahead
    )
    # head claim of a truncated 7-octet run blocked by the truncation guard
    # is a grammar concern; here: the tail of a longer run must not start
    # after hex+separator
    assert pattern.findall("00:1A:2B:3C:4D:5E:66") == []
    assert pattern.findall("00:1A:2B:3C:4D:5E") == ["00:1A:2B:3C:4D:5E"]
```

Run `uv run pytest tests/unit/test_boundary_guards.py -k mac_midrun -v` — expect AttributeError (red). Then add to `paxman/core/grammar/boundary.py` (green), directly after `phone_national()`:

```python
    @classmethod
    def mac_midrun(cls) -> BoundaryGuard:
        # MAC address guard: word_only plus rejection of a claim start
        # preceded by hex + separator — the tail of a longer colon/hyphen
        # run ("00:1A:2B:3C:4D:5E:66" must not yield "1A:2B:3C:4D:5E:66").
        # Plain word_only treats ':'/'-'/'.' as boundaries; the second
        # stacked lookbehind closes that gap (phone_national() precedent).
        return cls(
            lookbehind=r"(?<!\w)(?<![0-9A-Fa-f][-.:])", lookahead=r"(?!\w)"
        )
```

Run again — green. Full `tests/unit/test_boundary_guards.py` must stay green (no regression on existing factories).

- [ ] **Step 2: Write the failing grammar test**

```python
# tests/capabilities/mac_address/test_grammar.py
import pytest

from paxman.capabilities.MacAddress.grammar import MacAddressRecognitionGrammar
from paxman.capabilities.MacAddress.notation import MacAddressNotation

pytestmark = [pytest.mark.capability]


def spans(text):
    return MacAddressRecognitionGrammar().recognize(text)


def compacts(text):
    return [m.notation.compact for m in spans(text)]


# --- positive: one vector per Research section 2.1 RECOGNIZE form ---

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # colon 48 (research 2.1 row 1)
        ("00:1A:2B:3C:4D:5E", "001A2B3C4D5E"),
        # hyphen 48 (row 2, IEEE display)
        ("00-1A-2B-3C-4D-5E", "001A2B3C4D5E"),
        # cisco tri-dot (row 3)
        ("001A.2B3C.4D5E", "001A2B3C4D5E"),
        # bare 12 (row 4)
        ("001A2B3C4D5E", "001A2B3C4D5E"),
        # case folding (row 17)
        ("00:1a:2b:3c:4d:5e", "001A2B3C4D5E"),
        ("De:Ad:Be:Ef:Ca:Fe", "DEADBEEFCAFE"),
        # EUI-64 colon/hyphen/dot/bare (rows 5-8)
        ("00:1A:2B:3C:4D:5E:66:77", "001A2B3C4D5E6677"),
        ("00-1A-2B-3C-4D-5E-66-77", "001A2B3C4D5E6677"),
        ("001A.2B3C.4D5E.6677", "001A2B3C4D5E6677"),
        ("001A2B3C4D5E6677", "001A2B3C4D5E6677"),
        # modified EUI-64 / Zigbee (row 9)
        ("84:71:27:ff:fe:93:17:24", "847127FFFE931724"),
        # bit-reversed Token-Ring spelling (row 10) - recognized as itself
        ("48-2C-6A-1E-59-3D", "482C6A1E593D"),
        # MAC label fused (row 14)
        ("MAC: 00:1A:2B:3C:4D:5E", "001A2B3C4D5E"),
        ("MAC:00:1A:2B:3C:4D:5E", "001A2B3C4D5E"),
        ("mac - 001a.2b3c.4d5e", "001A2B3C4D5E"),
        # RFC 7042 documentation value
        ("00-00-5E-00-53-01", "00005E005301"),
        # sentinels are valid (research 7.1)
        ("FF:FF:FF:FF:FF:FF", "FFFFFFFFFFFF"),
        ("00:00:00:00:00:00", "000000000000"),
        ("01:80:C2:00:00:00", "0180C2000000"),
        ("33:33:00:00:00:01", "333300000001"),
        # quoted / embedded (research 8 edge 15)
        ('"00:1A:2B:3C:4D:5E"', "001A2B3C4D5E"),
        ("eth0 ether 00:1b:77:49:54:fd", "001B774954FD"),
        # residue policy (research 8 edge 12): 4-hex and 1-hex residues claim
        ("00:1A:2B:3C:4D:5E:6677", "001A2B3C4D5E"),
        ("00:1A:2B:3C:4D:5E-3", "001A2B3C4D5E"),
        ("001A2B3C4D5E:6677", "001A2B3C4D5E"),
        # word suffix does not block
        ("device 00:1A:2B:3C:4D:5E-end up", "001A2B3C4D5E"),
        # HA {ieee}-{endpoint} EUI-64 + endpoint (truncation-guard exemption)
        ("84:71:27:ff:fe:93:17:24-11", "847127FFFE931724"),
    ],
)
def test_recognizes(text, expected):
    result = spans(text)
    assert len(result) == 1
    assert result[0].notation.compact == expected
    assert result[0].notation.shape == ("eui64" if len(expected) == 16 else "eui48")


def test_span_invariants():
    text = "addr 00:1A:2B:3C:4D:5E end"
    result = spans(text)
    assert len(result) == 1
    m = result[0]
    assert m.raw_text == "00:1A:2B:3C:4D:5E"
    assert m.raw_text == text[m.start : m.end]
    assert len(m.raw_text) == m.end - m.start


def test_label_included_in_raw_text():
    m = spans("MAC: 00:1A:2B:3C:4D:5E")[0]
    assert m.raw_text == "MAC: 00:1A:2B:3C:4D:5E"
    assert m.notation.compact == "001A2B3C4D5E"


def test_embedded_eui48_in_eui64_single_longest_match():
    assert compacts("x 00:1A:2B:3C:4D:5E:66:77 y") == ["001A2B3C4D5E6677"]


def test_bare_16_before_12():
    assert compacts("001A2B3C4D5E6677") == ["001A2B3C4D5E6677"]


def test_multiple_mentions():
    text = "src=00:1A:2B:3C:4D:5E dst=00-1B-77-49-54-FD"
    assert compacts(text) == ["001A2B3C4D5E", "001B774954FD"]
    assert len(spans("permit 001a.2b3c.4d5e 001a.2b3c.4d5f")) == 2


# --- negatives: research 2.2 / 8 ---

@pytest.mark.parametrize(
    "text",
    [
        "MAC001A2B3C4D5E",  # glued label
        "00:1A-2B:3C-4D:5E",  # mixed separators
        "001A.2B3C:4D5E",  # mixed separator families
        "00:1A:2B:3C:4D:5E:66",  # 7 octets - truncated final octet
        "00:1A:2B:3C:4D:5E-66",
        "001A2B3C4D5E-66",
        "001A.2B3C.4D5E.66",
        "001A2B3C4D5E6",  # 13 hex
        "001A2B3C4D5",  # 11 hex
        "001A2B3C4D5E667",  # 15 hex
        "X001A2B3C4D5E",  # left glue
        "001A2B3C4D5EY",  # right glue
        "A001A2B3C4D5E6677B",
        "0:1b:77:49:54:fd",  # 1-digit octets DEFER
        "08002b:010203",  # 24-bit word DEFER
        "08002b:0102030405",
        "00 1A 2B 3C 4D 5E",  # whitespace separator DEFER
        "fe80::1",  # IPv6 compressed
        "00:1A:2B:3C:4D:0G",  # invalid charset
        "００:1A:2B:3C:4D:5E",  # fullwidth digits
        "550e8400-e29b-41d4-a716-446655440000",  # UUID
        "aabbccddeeff00112233",  # 20-hex (git full-SHA length)
        "1:00:1A:2B:3C:4D:5E",  # 7-octet 1-digit-first run, tail claim
        "",
        "   ",
        "\t\n",
    ],
)
def test_ignores(text):
    assert spans(text) == []


def test_nine_octet_claims_complete_eui64_with_residue():
    # documented policy (research 8 edge 12 / 14): a complete valid form
    # followed by junk residue claims the form
    assert compacts("00:1A:2B:3C:4D:5E:66:77:88") == ["001A2B3C4D5E6677"]


def test_grammar_metadata():
    g = MacAddressRecognitionGrammar()
    assert g.name == "mac_address_recognition"
    assert g.semantics == "mac_address_recognition"
    assert g.single_value is True
```

- [ ] **Step 3: Run test — expect ImportError (red)**

```bash
uv run pytest tests/capabilities/mac_address/test_grammar.py -v
```

- [ ] **Step 4: Implement the grammar**

```python
# paxman/capabilities/MacAddress/grammar/mac_address_recognition.py
"""MAC address recognition - EUI-48/EUI-64, 4 separator families, fused MAC label."""

from __future__ import annotations

import re

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# 2-hex octet / 4-hex hextet building blocks. Case handling is delegated to
# the (?ai:...) inline group (ASCII + IGNORECASE), exactly like the shipped
# BIC grammar; [0-9A-F] classes therefore accept a-f too.
_OCTET = r"[0-9A-F]{2}"
_HEXTET = r"[0-9A-F]{4}"

# Separator families are internally consistent per branch: each branch
# hard-codes its separator, so mixed-separator input ("00:1A-2B:...") can
# never match - the Python-re equivalent of validator.js's backreference \1
# and Go's single-separator dispatch, without group-number collisions across
# alternation branches.
_EUI48_COLON = rf"(?:{_OCTET}:){{5}}{_OCTET}"
_EUI64_COLON = rf"(?:{_OCTET}:){{7}}{_OCTET}"
_EUI48_HYPHEN = rf"(?:{_OCTET}-){{5}}{_OCTET}"
_EUI64_HYPHEN = rf"(?:{_OCTET}-){{7}}{_OCTET}"
_EUI48_DOT = rf"(?:{_HEXTET}\.){{2}}{_HEXTET}"
_EUI64_DOT = rf"(?:{_HEXTET}\.){{3}}{_HEXTET}"

# Bare forms split by length so the truncation guard can be applied to the
# 48-bit side only: 16 hex (4 hextets, tried first) and 12 hex (6 octets).
_BARE16 = rf"{_HEXTET}{_HEXTET}{_HEXTET}{_HEXTET}"
_BARE12 = rf"{_OCTET}{_OCTET}{_OCTET}{_OCTET}{_OCTET}{_OCTET}"

# Truncation guard (48-bit branches only): a 6-octet / 12-hex claim must not
# stand when immediately followed by a separator + exactly 2 terminating hex
# digits - the signature of a truncated final octet of a longer run
# ("00:1A:2B:3C:4D:5E:66" is a malformed 8-octet address, not a 6-octet one
# plus junk). The outer lookahead cannot see this: ':'/'-'/'.' are not \w.
# EUI-64 claims are EXEMPT: "84:71:27:ff:fe:93:17:24-11" (Home Assistant's
# "{ieee}-{endpoint_id}" device_config key shape) must keep claiming the
# 8-octet address with the endpoint suffix as residue.
_TRUNCATION_GUARD = r"(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))"

# Branch ordering: all four 64-bit forms precede all four 48-bit forms and
# the 16-hex bare precedes the 12-hex bare, so finditer consumes the longest
# span at each scan position. The engine's within-grammar containment dedup
# ("longer wins", orchestrator:_dedup_spans) is the second safety net: any
# shorter same-start match (e.g. the EUI-48 prefix of an EUI-64) is fully
# contained in the emitted longer match and dropped. This is why ONE grammar
# must own both lengths - two grammars would preserve cross-grammar
# containment and produce spurious AMBIGUOUS with 12-hex vs 16-hex values.
_64_ALTS = "|".join([_EUI64_COLON, _EUI64_HYPHEN, _EUI64_DOT, _BARE16])
_48_ALTS = "|".join([_EUI48_COLON, _EUI48_HYPHEN, _EUI48_DOT, _BARE12])
_BODY_ALTS = f"{_64_ALTS}|(?:{_48_ALTS}){_TRUNCATION_GUARD}"

# Optional fused label: (?ai:MAC)[\s:-]+ one-or-more, never zero width
# (BIC/ISSN/IBAN label precedent). "MAC001A2B3C4D5E" (glued) cannot match:
# the label branch requires a separator, and no body branch can start at
# "M" (not a hex digit) or carve after it (word_only lookbehind sees \w).
_MAC_BODY = rf"(?ai:(?:(?:MAC)[\s:-]+)?(?P<compact>(?:{_BODY_ALTS})))"

# Mid-run guard (mac_midrun() factory, phone_national() precedent): word_only
# alone treats ':'/'-'/'.' as boundaries, so the TAIL of a longer colon run
# would be claimed as a fresh 6-octet match ("00:1A:2B:3C:4D:5E:66" must not
# yield "1A:2B:3C:4D:5E:66"). The second stacked lookbehind rejects a claim
# start preceded by hex + separator. It constrains only the MATCH START, so
# the fused label case is unaffected ("MAC:00:1A:..." starts at the M).
_MAC_GUARD = BoundaryGuard.mac_midrun()

_MAC_PATTERN = _MAC_GUARD.lookbehind + _MAC_BODY + _MAC_GUARD.lookahead


def _mac_notation(match: re.Match[str]) -> MacAddressNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    shape = "eui64" if len(compact) == 16 else "eui48"
    return MacAddressNotation(compact=compact, shape=shape)


class MacAddressRecognitionGrammar(PipelineGrammar[MacAddressNotation]):
    """MAC address recognition - EUI-48/EUI-64, colon/hyphen/tri-dot/bare.

    Recognizes all eight shape families (4 separators x 2 lengths, bare
    split 16-before-12). Case-insensitive; notation strips separators via
    isascii()/isalnum() and uppercases. One consistent separator per mention
    by construction. Does not interpret U/L or I/G bits and does not check
    OUI membership - rules own that. Bit-reversed (Token-Ring/FDDI) spellings
    are recognized as themselves; no bit-order reinterpretation anywhere.
    """

    name = "mac_address_recognition"
    semantics = "mac_address_recognition"
    single_value = True
    pre = StandardPre[MacAddressNotation](empty_guard=True)
    regex = RegexStage[MacAddressNotation](
        pattern=_MAC_PATTERN, notation_fn=_mac_notation
    )
```

Add the re-export to `paxman/capabilities/MacAddress/grammar/__init__.py`:

```python
from paxman.capabilities.MacAddress.grammar.mac_address_recognition import (
    MacAddressRecognitionGrammar,
)

__all__ = ["MacAddressRecognitionGrammar"]
```

- [ ] **Step 5: Run test — green; quality gates; commit**

```bash
uv run pytest tests/capabilities/mac_address/test_grammar.py tests/unit/test_boundary_guards.py -v
uv run ruff check paxman/core/grammar/boundary.py paxman/capabilities/MacAddress/ --fix
uv run pyright paxman/core/grammar/boundary.py paxman/capabilities/MacAddress/
git add paxman/core/grammar/boundary.py tests/unit/test_boundary_guards.py paxman/capabilities/MacAddress/grammar/ tests/capabilities/mac_address/test_grammar.py
git commit -m "feat(mac_address): mac_address_recognition grammar + boundary.mac_midrun factory"
```

---

### Task 4: Rules — IEEE Std 802-2024 structure

**Files:**
- Rename + fill: `paxman/capabilities/MacAddress/rules/ieee_ed2024.py` → `ieee_802_ed2024.py`
- Test: `tests/capabilities/mac_address/test_rules.py`

Research section 5.1-5.3: one `PUBLICATION` (IEEE Std 802-2024, `kind="specification"`, `lifecycle="active"`, `publication_year=2024`, reference URL `https://standards.ieee.org/ieee/802/10894` — search-verified; confirm the page's exact publication date at implementation and adjust only if it differs from 2024). One `Rule` class `Section82EUIStructure` (`PARSER`): matches() checks `len(compact)` in `{12, 16}`, charset re-assertion, `shape`/length agreement — never rejects on I/G, U/L, FF-FE/FF-FF markers, or sentinels. `normalize()` returns the colon form; the CI `output_format` purity scan applies. The OUI registry layer (`ieee_oui_registry_ed2026.py` + `rules/data/oui_registry.py` + `include_oui_validation`) is **deferred** — see Step 4.

- [ ] **Step 0: Rename the scaffold placeholder**

```bash
git mv paxman/capabilities/MacAddress/rules/ieee_ed2024.py paxman/capabilities/MacAddress/rules/ieee_802_ed2024.py
```

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/mac_address/test_rules.py
import pytest

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_802_ed2024 import (
    PUBLICATION,
    Section82EUIStructure,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]


def n48(hex12: str) -> MacAddressNotation:
    return MacAddressNotation(compact=hex12, shape="eui48")


def n64(hex16: str) -> MacAddressNotation:
    return MacAddressNotation(compact=hex16, shape="eui64")


class TestSection82EUIStructure:
    def setup_method(self):
        self.rule = Section82EUIStructure()
        self.contract = MacAddressContract()

    @pytest.mark.parametrize(
        "notation",
        [
            n48("001A2B3C4D5E"),
            n48("00005E005301"),
            n48("FFFFFFFFFFFF"),  # broadcast
            n48("000000000000"),  # nil
            n48("0180C2000000"),  # STP group
            n48("020000000001"),  # locally administered
            n48("333300000001"),  # IPv6 ND multicast (RFC 7042 2.3.1)
            n64("001A2B3C4D5E6677"),
            n64("02005EFFFE005301"),  # RFC 7042 modified EUI-64 shape
            n64("847127FFFE931724"),  # Zigbee ff:fe mid-address
        ],
    )
    def test_matches_valid(self, notation):
        assert self.rule.matches(notation, self.contract) is True

    @pytest.mark.parametrize(
        "notation",
        [
            MacAddressNotation(compact="001A2B3C4D5", shape="eui48"),  # 11
            MacAddressNotation(compact="001A2B3C4D5E6", shape="eui48"),  # 13
            MacAddressNotation(compact="001A2B3C4D5E66", shape="eui48"),  # 14
            MacAddressNotation(compact="001A2B3C4D5E667", shape="eui48"),  # 15
            MacAddressNotation(compact="001A2B3C4D5E", shape="eui64"),  # shape/length disagree
            MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui48"),
        ],
    )
    def test_rejects_invalid(self, notation):
        assert self.rule.matches(notation, self.contract) is False

    def test_normalize_produces_canonical(self):
        assert (
            self.rule.normalize(n48("001A2B3C4D5E"), self.contract)
            == "00:1A:2B:3C:4D:5E"
        )
        assert (
            self.rule.normalize(n64("001A2B3C4D5E6677"), self.contract)
            == "00:1A:2B:3C:4D:5E:66:77"
        )

    def test_provenance_attributes(self):
        assert PUBLICATION.authority == "IEEE"
        assert PUBLICATION.specification_name == "IEEE Std 802-2024"
        assert PUBLICATION.kind == "specification"
        assert PUBLICATION.lifecycle == "active"
        assert PUBLICATION.publication_year == 2024
        assert PUBLICATION.reference_url == "https://standards.ieee.org/ieee/802/10894"

    def test_rule_name(self):
        assert self.rule.name == "Section 8.2-eui-structure"

    def test_strategy(self):
        assert self.rule.strategy is RuleStrategy.PARSER

    def test_target_semantics(self):
        assert self.rule.target_semantics == frozenset({"mac_address_recognition"})
        assert self.rule.requires_features == frozenset()

    def test_matches_never_raises_on_garbage(self):
        # defensive: rules never raise (research 5.3)
        for bad in ("", "zz", "00:1A:2B:3C:4D:5E"):
            assert (
                self.rule.matches(
                    MacAddressNotation(compact=bad.replace(":", ""), shape="eui48"),
                    self.contract,
                )
                in (True, False)
            )
```

- [ ] **Step 2: Run test — expect ImportError (red)**

```bash
uv run pytest tests/capabilities/mac_address/test_rules.py -v
```

- [ ] **Step 3: Implement the rule**

```python
# paxman/capabilities/MacAddress/rules/ieee_802_ed2024.py
"""IEEE Std 802-2024 - EUI-48/EUI-64 MAC address structure (Section 8.2).

Structure is clause "8.2 Universal addresses" per IEEE Std 802-2014
numbering, the clause the Bluetooth Core Specification cites normatively for
BD_ADDR; verify the clause number against the 802-2024 text (free via the
IEEE GET Program) at implementation. MAC addresses have no checksum and no
check character (Research section 5.1 - proved by absence across IEEE 802,
RFC 7042, and all ecosystem validators): structure is all there is.
"""

from __future__ import annotations

from typing import ClassVar

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.capability_contract import Provenance
from paxman.core.contract import Contract
from paxman.core.domain import Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="IEEE",
    specification_name="IEEE Std 802-2024",
    kind="specification",
    reference_url="https://standards.ieee.org/ieee/802/10894",
    version="2024",
    lifecycle="active",
    publication_year=2024,
)

_VALID_LENGTHS = frozenset({12, 16})
_HEX = frozenset("0123456789ABCDEF")
_SHAPE_BY_LENGTH = {12: "eui48", 16: "eui64"}


class Section82EUIStructure(Rule[MacAddressNotation]):
    """EUI-48/EUI-64 structure per IEEE Std 802 (Section 8.2, 802-2014 numbering).

    Length exactly 12 or 16 uppercase hex digits, shape agreeing with length.
    The I/G bit (0x01, unicast/group) and U/L bit (0x02, universal/local) are
    informative predicates - broadcast, nil, multicast, locally administered,
    FF-FE/FF-FF mid-address markers, and all sentinels are valid. Bit-order
    provenance (Token-Ring/FDDI MSB display) is not detectable and is never
    reinterpreted (Research section 13 decision 10).
    """

    name = "Section 8.2-eui-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 8.2 (Universal addresses; EUI-48/EUI-64, I/G and U/L bits)"
    target_semantics: ClassVar[frozenset[str]] = frozenset(
        {"mac_address_recognition"}
    )
    requires_features: ClassVar[frozenset[str]] = frozenset()

    def matches(self, notation: MacAddressNotation, contract: Contract) -> bool:
        compact = notation.compact
        if len(compact) not in _VALID_LENGTHS:
            return False
        if any(ch not in _HEX for ch in compact):
            return False
        return notation.shape == _SHAPE_BY_LENGTH[len(compact)]

    def normalize(self, notation: MacAddressNotation, contract: Contract) -> str:
        compact = notation.compact
        return ":".join(compact[i : i + 2] for i in range(0, len(compact), 2))
```

**Import-path check before running:** confirm the `Provenance` import path against the shipped rule files (`paxman/capabilities/BIC/rules/iso_9362_ed2022.py` imports it from the same module the scaffolder's placeholder uses — keep whatever the scaffold placeholder already imports; do not guess a second path).

- [ ] **Step 4: Document the deferred OUI registry layer (no code)**

Append to the module docstring of `ieee_802_ed2024.py` (or a `# Deferred:` comment block): the OUI registry layer (`ieee_oui_registry_ed2026.py`, `LOOKUP_TABLE`, `requires_features={"include_oui_validation"}`, `rules/data/oui_registry.py` MA-L snapshot, universal-addresses-only with U/L-bit-1 exemption per python-stdnum `validate_manufacturer`) is deliberately deferred, mirroring the BIC SWIFT Directory deferral; refresh procedure = download the IEEE public listing from `https://regauth.standards.ieee.org/`, project MA-L 24-bit OUIs to uppercase 6-hex keys (Local bit zero by assignment policy), regenerate via a future `tools/regenerate_oui_registry_data.py`. Not implemented in this plan.

- [ ] **Step 5: Run test — green; purity scan; commit**

```bash
uv run pytest tests/capabilities/mac_address/test_rules.py -v
uv run pytest tests/unit/test_rule_output_format_purity.py -v
uv run pyright paxman/capabilities/MacAddress/rules/
git add paxman/capabilities/MacAddress/rules/ tests/capabilities/mac_address/test_rules.py
git commit -m "feat(mac_address): IEEE 802-2024 Section 8.2 structure rule (PARSER)"
```

---

### Task 5: Capability — wiring, create_contract, format_value

**Files:**
- Modify: `paxman/capabilities/MacAddress/capability.py`
- Test: `tests/capabilities/mac_address/test_capability.py`

Research section 6.2: `get_grammars()` returns the single grammar; `get_rules()` returns `[Section82EUIStructure()]` in v1 (registry rule deferred); `create_contract()` opens with the fixed keyword-only common block; `format_value()` implements the six-way seam with the `_bit_reverse_octet` helper (RFC 2469 per-octet swap, verified: `12→48`, `34→2C`, `56→6A`, `78→1E`, `9A→59`, `BC→3D`; PostgreSQL vector `08→10, 2B→D4`).

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/mac_address/test_capability.py
import pytest

from paxman.capabilities.MacAddress.capability import MacAddressCapability
from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.grammar import MacAddressRecognitionGrammar
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_802_ed2024 import (
    Section82EUIStructure,
)
from paxman.core.capability import Capability

pytestmark = [pytest.mark.capability]


def m48():
    return MacAddressNotation(compact="001A2B3C4D5E", shape="eui48")


def m64():
    return MacAddressNotation(compact="001A2B3C4D5E6677", shape="eui64")


def test_is_capability_subclass():
    assert issubclass(MacAddressCapability, Capability)
    assert isinstance(MacAddressCapability(), Capability)


def test_name():
    assert MacAddressCapability.name == "mac_address"


def test_get_grammars_returns_all():
    grammars = MacAddressCapability().get_grammars()
    assert len(grammars) == 1
    assert isinstance(grammars[0], MacAddressRecognitionGrammar)
    assert grammars[0].name == "mac_address_recognition"


def test_get_rules_returns_all():
    rules = MacAddressCapability().get_rules()
    assert len(rules) == 1
    assert isinstance(rules[0], Section82EUIStructure)


def test_format_value_identity_default():
    cap = MacAddressCapability()
    assert cap.format_value("00:1A:2B:3C:4D:5E", None, m48()) == "00:1A:2B:3C:4D:5E"
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E", "colon", m48()) == "00:1A:2B:3C:4D:5E"
    )
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E", "default", m48()) == "00:1A:2B:3C:4D:5E"
    )


def test_format_value_hyphen_bare_cisco():
    cap = MacAddressCapability()
    assert cap.format_value("00:1A:2B:3C:4D:5E", "hyphen", m48()) == "00-1A-2B-3C-4D-5E"
    assert cap.format_value("00:1A:2B:3C:4D:5E", "bare", m48()) == "001A2B3C4D5E"
    assert cap.format_value("00:1A:2B:3C:4D:5E", "cisco", m48()) == "001A.2B3C.4D5E"
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E:66:77", "cisco", m64())
        == "001A.2B3C.4D5E.6677"
    )


def test_format_value_eui64():
    cap = MacAddressCapability()
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E", "eui64", m48())
        == "00:1A:2B:FF:FE:3C:4D:5E"
    )
    # EUI-64 input passes through unchanged (deterministic identity)
    assert (
        cap.format_value("00:1A:2B:3C:4D:5E:66:77", "eui64", m64())
        == "00:1A:2B:3C:4D:5E:66:77"
    )


def test_format_value_bit_reversed_vectors():
    cap = MacAddressCapability()
    # RFC 2469 vector
    rfc = MacAddressNotation(compact="123456789ABC", shape="eui48")
    assert (
        cap.format_value("12:34:56:78:9A:BC", "bit_reversed", rfc)
        == "48:2C:6A:1E:59:3D"
    )
    # PostgreSQL vector
    pg = MacAddressNotation(compact="08002B010203", shape="eui48")
    assert (
        cap.format_value("08:00:2B:01:02:03", "bit_reversed", pg)
        == "10:00:D4:80:40:C0"
    )
    # involution: swap twice returns the canonical value
    once = cap.format_value("00:1A:2B:3C:4D:5E", "bit_reversed", m48())
    assert (
        cap.format_value(
            once, "bit_reversed", MacAddressNotation(compact="0058D43CB27A", shape="eui48")
        )
        == "00:1A:2B:3C:4D:5E"
    )


def test_create_contract_factories():
    c = MacAddressCapability.create_contract()
    assert isinstance(c, MacAddressContract)
    assert c.output_format == "colon"
    assert (
        MacAddressCapability.create_contract(output_format="hyphen").output_format
        == "hyphen"
    )
    assert MacAddressCapability.create_contract(year=2024).year == 2024
    assert MacAddressCapability.create_contract(
        extra_grammars=("some_community",)
    ).extra_grammars == ("some_community",)
```

- [ ] **Step 2: Run test — expect failures (red)**

```bash
uv run pytest tests/capabilities/mac_address/test_capability.py -v
```

- [ ] **Step 3: Implement the capability**

```python
# paxman/capabilities/MacAddress/capability.py
"""MacAddress capability - wiring, contract factory, presentation seam."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.grammar import MacAddressRecognitionGrammar
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_802_ed2024 import (
    Section82EUIStructure,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


def _bit_reverse_octet(octet: str) -> str:
    """RFC 2469 per-octet bit swap: 0x12 -> 0x48, 0xBC -> 0x3D."""
    value = int(octet, 16)
    reversed_bits = (
        ((value & 0x01) << 7)
        | ((value & 0x02) << 5)
        | ((value & 0x04) << 3)
        | ((value & 0x08) << 1)
        | ((value & 0x10) >> 1)
        | ((value & 0x20) >> 3)
        | ((value & 0x40) >> 5)
        | ((value & 0x80) >> 7)
    )
    return f"{reversed_bits:02X}"


class MacAddressCapability(Capability[MacAddressNotation]):
    name = "mac_address"  # lowercase identifier - what users pass to the registry

    def get_grammars(self) -> list[Grammar[MacAddressNotation]]:
        return [MacAddressRecognitionGrammar()]  # single grammar; both lengths

    def get_rules(self) -> list[Rule[MacAddressNotation]]:
        # v1 ships the structure rule only; the OUI registry layer is
        # deferred (Research section 5.4 / 13 decision 6).
        return [Section82EUIStructure()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> MacAddressContract:
        return MacAddressContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: MacAddressNotation
    ) -> str:
        compact = value.replace(":", "")
        octets = [compact[i : i + 2] for i in range(0, len(compact), 2)]
        if output_format == "hyphen":
            return "-".join(octets)
        if output_format == "bare":
            return compact
        if output_format == "cisco":
            hextets = [compact[i : i + 4] for i in range(0, len(compact), 4)]
            return ".".join(hextets)
        if output_format == "eui64":
            if len(compact) == 12:
                return ":".join([*octets[:3], "FF", "FE", *octets[3:]])
            return value  # already EUI-64 - deterministic identity
        if output_format == "bit_reversed":
            return ":".join(_bit_reverse_octet(o) for o in octets)
        return value  # colon default is identity - normalize() returns colon form
```

- [ ] **Step 4: Run test — green; commit**

```bash
uv run pytest tests/capabilities/mac_address/ -v
uv run pyright paxman/capabilities/MacAddress/
git add paxman/capabilities/MacAddress/capability.py tests/capabilities/mac_address/test_capability.py
git commit -m "feat(mac_address): MacAddressCapability wiring + 6-way format_value seam"
```

---

### Task 6: Exports, Surface Homogeneity, and Docs

**Files:**
- Modify: `paxman/capabilities/MacAddress/__init__.py`, `tests/unit/test_capability_exports.py`, `CONTEXT.md`, `README.md`, `docs/development/MILESTONE.md`
- Test: `tests/unit/test_capability_exports.py`, `tests/unit/test_capability_surface.py` (auto-wired by scaffolder)

- [ ] **Step 1: Patch test_capability_exports.py (fails by design until patched)**

Run `uv run pytest tests/unit/test_capability_exports.py -v` — expect failure listing `MacAddress`. Add:

```python
from paxman.capabilities import MacAddress


class TestMacAddressCapabilityExports:
    def test_exports_capability(self):
        assert MacAddress is not None
```

…and add `"MacAddress"` to the module's expected-shipped-set entry (find the set literal the other fifteen capabilities are listed in, insert in alphabetical position after `Language`/`Money` per existing ordering).

- [ ] **Step 2: Verify the package `__init__` re-exports**

`paxman/capabilities/MacAddress/__init__.py` must export `MacAddressCapability` (as `MacAddress`), `MacAddressContract`, and `MacAddressNotation`:

```python
from paxman.capabilities.MacAddress.capability import (
    MacAddressCapability as MacAddress,
    MacAddressContract,
)
from paxman.capabilities.MacAddress.notation import MacAddressNotation

__all__ = ["MacAddress", "MacAddressContract", "MacAddressNotation"]
```

(Check the exact alias pattern the scaffolder generated and keep it — `from paxman.capabilities import MacAddress` must work.)

- [ ] **Step 3: Run export + surface gates**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v
```

Expected: green (surface gate auto-wired by Task 0 scaffolding).

- [ ] **Step 4: Update CONTEXT.md**

- Add `MacAddressNotation` (`compact` + `shape`) to the notation vocabulary section.
- Add the capability row: 1 grammar (`mac_address_recognition` — EUI-48/EUI-64, colon/hyphen/tri-dot/bare, fused `MAC` label), 1 rule (`Section 8.2-eui-structure`, IEEE Std 802-2024, no checksum, I/G + U/L informative), canonical colon uppercase, offered `hyphen`/`bare`/`cisco`/`eui64`/`bit_reversed`.

- [ ] **Step 5: Update README.md and MILESTONE.md**

- README capabilities table: add the MacAddress row (grammars `1 (EUI-48/EUI-64)`); update the shipped count 15 → 16 in any prose that states it.
- `docs/development/MILESTONE.md`: add/complete the MacAddress row pointing at the research report and this plan.

- [ ] **Step 6: Commit**

```bash
uv run pytest tests/unit/ -q
git add paxman/capabilities/MacAddress/__init__.py tests/unit/test_capability_exports.py CONTEXT.md README.md docs/development/MILESTONE.md
git commit -m "docs(mac_address): exports gate, surface wiring, CONTEXT/README/MILESTONE"
```

---

### Task 7: Integration, Resolution Map, and Property Tests

**Files:**
- Create: `tests/integration/test_mac_address_capability.py`, `tests/property/test_mac_address_properties.py`

- [ ] **Step 1: Write integration tests (TDD — run against the wired capability)**

```python
# tests/integration/test_mac_address_capability.py
import pytest

import paxman
from paxman.capabilities import MacAddress
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

# real vectors: research section 12


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def _contract(**kwargs):
    return MacAddress.create_contract(**kwargs)


def _register():
    register_capability(MacAddress())


class TestMacAddressPipeline:
    def test_success_colon(self):
        _register()
        result = paxman.canonicalize("00:1a:2b:3c:4d:5e", _contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "00:1A:2B:3C:4D:5E"
        assert result.candidates[0].recognition_rule == "mac_address_recognition"

    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("00-1A-2B-3C-4D-5E", "00:1A:2B:3C:4D:5E"),
            ("001A.2B3C.4D5E", "00:1A:2B:3C:4D:5E"),
            ("001A2B3C4D5E", "00:1A:2B:3C:4D:5E"),
            ("MAC: 00:1A:2B:3C:4D:5E", "00:1A:2B:3C:4D:5E"),
            ("00:1A:2B:3C:4D:5E:66:77", "00:1A:2B:3C:4D:5E:66:77"),
            ("84:71:27:ff:fe:93:17:24", "84:71:27:FF:FE:93:17:24"),
            ("48-2C-6A-1E-59-3D", "48:2C:6A:1E:59:3D"),  # bit-reversed as-is
            ("FF:FF:FF:FF:FF:FF", "FF:FF:FF:FF:FF:FF"),
            ("00-00-5E-00-53-01", "00:00:5E:00:53:01"),
        ],
    )
    def test_success_spellings(self, raw, canonical):
        _register()
        result = paxman.canonicalize(raw, _contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == canonical

    def test_spelling_variants_dedup_to_success(self):
        _register()
        result = paxman.canonicalize(
            "00:1A:2B:3C:4D:5E and 00-1A-2B-3C-4D-5E", _contract()
        )
        assert result.status == Resolution.SUCCESS  # identical values coalesce

    def test_missing(self):
        _register()
        assert paxman.canonicalize("no hardware addresses here", _contract()).status == (
            Resolution.MISSING
        )

    @pytest.mark.parametrize(
        "raw",
        [
            "00:1A:2B:3C:4D:5E:66",  # 7 octets
            "00:1A-2B:3C-4D:5E",  # mixed separators
            "001A2B3C4D5E6",  # 13 hex
        ],
    )
    def test_missing_truncated_and_malformed(self, raw):
        _register()
        assert paxman.canonicalize(raw, _contract()).status == Resolution.MISSING

    def test_two_distinct_multiple_mentions(self):
        _register()
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(
                "from 00:1A:2B:3C:4D:5E to 00-1B-77-49-54-FD", _contract()
            )

    def test_year_temporal_filter(self):
        _register()
        result = paxman.canonicalize("00:1A:2B:3C:4D:5E", _contract(year=2014))
        assert result.status == Resolution.INVALID  # 2024 rule filtered

    def test_version_stamp_and_determinism(self):
        _register()
        a = paxman.canonicalize("00:1a.2b3c.4d5e", _contract())
        b = paxman.canonicalize("00:1a.2b3c.4d5e", _contract())
        assert a.canonicalized_value == b.canonicalized_value
        assert a.version_stamp == b.version_stamp

    def test_output_format_seam(self):
        _register()
        assert (
            paxman.canonicalize("00:1A:2B:3C:4D:5E", _contract(output_format="hyphen")).canonicalized_value
            == "00-1A-2B-3C-4D-5E"
        )
        assert (
            paxman.canonicalize("00:1A:2B:3C:4D:5E", _contract(output_format="cisco")).canonicalized_value
            == "001A.2B3C.4D5E"
        )
        assert (
            paxman.canonicalize("00:1A:2B:3C:4D:5E", _contract(output_format="eui64")).canonicalized_value
            == "00:1A:2B:FF:FE:3C:4D:5E"
        )
```

Run and fix any API-shape mismatches against the actual `ExecutionResult`/`Candidate` fields (`result.version_stamp` naming, `MultipleMentionsError` import path — mirror `tests/integration/test_bic_capability.py`).

- [ ] **Step 2: Write property tests**

```python
# tests/property/test_mac_address_properties.py
from hypothesis import given, settings
from hypothesis import strategies as st

import pytest

import paxman
from paxman.capabilities import MacAddress
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = [pytest.mark.property]


def _hex_digits(n: int):
    return st.lists(st.sampled_from("0123456789ABCDEF"), min_size=n, max_size=n).map(
        "".join
    )


def _colon(compact: str) -> str:
    return ":".join(compact[i : i + 2] for i in range(0, len(compact), 2))


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**48 - 1))
def test_generated_eui48_canonicalizes_to_itself(value):
    register_capability(MacAddress())
    compact = f"{value:012X}"
    contract = MacAddress.create_contract()
    result = paxman.canonicalize(_colon(compact), contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == _colon(compact)


@settings(max_examples=200)
@given(st.integers(min_value=0, max_value=2**64 - 1))
def test_generated_eui64_canonicalizes_to_itself(value):
    register_capability(MacAddress())
    compact = f"{value:016X}"
    contract = MacAddress.create_contract()
    result = paxman.canonicalize(_colon(compact), contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == _colon(compact)


@settings(max_examples=100)
@given(_hex_digits(12))
def test_spelling_equivalence_all_families(compact):
    register_capability(MacAddress())
    contract = MacAddress.create_contract()
    colon = _colon(compact)
    hyphen = colon.replace(":", "-")
    dot = ".".join(compact[i : i + 4] for i in range(0, 12, 4))
    values = {
        paxman.canonicalize(s, contract).canonicalized_value
        for s in (colon, hyphen, dot, compact.lower(), f"MAC: {colon}")
    }
    assert len(values) == 1


@settings(max_examples=100)
@given(st.text(min_size=0, max_size=64))
def test_random_strings_never_raise(text):
    register_capability(MacAddress())
    contract = MacAddress.create_contract()
    result = paxman.canonicalize(text, contract)  # must not raise
    assert result.status in (
        Resolution.SUCCESS,
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.AMBIGUOUS,
    )


def test_bit_reversed_involution():
    from paxman.capabilities.MacAddress.capability import MacAddressCapability
    from paxman.capabilities.MacAddress.notation import MacAddressNotation

    cap = MacAddressCapability()
    for value in range(0, 256):
        octet = f"{value:02X}"
        notation = MacAddressNotation(compact=octet + "0000000000", shape="eui48")
        once = cap.format_value(f"{octet}:00:00:00:00:00", "bit_reversed", notation)
        back = cap.format_value(
            once, "bit_reversed", MacAddressNotation(compact=once.replace(":", ""), shape="eui48")
        )
        assert back == f"{octet}:00:00:00:00:00"
```

- [ ] **Step 3: Run integration + property suites; commit**

```bash
uv run pytest tests/integration/test_mac_address_capability.py tests/property/test_mac_address_properties.py -v
git add tests/integration/test_mac_address_capability.py tests/property/test_mac_address_properties.py
git commit -m "test(mac_address): integration resolution map + hypothesis property suite"
```

---

### Task 8: Final Verification and Cleanup

- [ ] **Step 1: Full pre-PR gate**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest
```

Expected: all green. Pay attention to:
- `tests/unit/test_rule_output_format_purity.py` — no `output_format` token in `paxman/capabilities/MacAddress/rules/`.
- Coverage ≥ 95% for the new package (`uv run coverage report --include="paxman/capabilities/MacAddress/*,paxman/core/grammar/boundary.py"`).
- `import-linter` — MacAddress imports only from `paxman.core` (the boundary.py change is core-side, no capability-to-capability import).

- [ ] **Step 2: CLI smoke test**

```bash
uv run python -m paxman mac_address "00:1a:2b:3c:4d:5e"
uv run python -m paxman mac_address "84:71:27:ff:fe:93:17:24"
uv run python -m paxman --list
```

Expected: `SUCCESS` colon canonical for both; `--list` shows `mac_address` (if the CLI lists registered capabilities — registration happens via `register_all_shipped` only if the bootstrap list is touched; if `mac_address` is absent because `_SHIPPED` is intentionally untouched, smoke-test through `register_capability(MacAddress())` in a `uv run python` REPL instead, per the BIC deferral precedent).

- [ ] **Step 3: Verify bootstrap deferral is deliberate**

`paxman/api/bootstrap.py` `_SHIPPED` must NOT contain `MacAddress` in v1 (ISSN/IBAN/BIC precedent: shipped but not bootstrapped). If a reviewer wants bootstrap inclusion, that is a separate one-line follow-up — do not bundle it.

- [ ] **Step 4: Final commit and hand-off**

```bash
git add -A
git commit -m "chore(mac_address): final verification pass for MacAddress capability"
```

Do not delete `docs/development/research/2026-08-31-mac-address-canonicalization.md`; it is the provenance record for the capability's design decisions.

---

## Behavioral Contract

| Input | Contract | Status / canonical |
|---|---|---|
| `00:1A:2B:3C:4D:5E` | default `colon` | `SUCCESS` -> `00:1A:2B:3C:4D:5E` |
| `00-1A-2B-3C-4D-5E` / `001A.2B3C.4D5E` / `001A2B3C4D5E` | default `colon` | `SUCCESS` -> `00:1A:2B:3C:4D:5E` (spellings dedup) |
| `00:1a:2b:3c:4d:5e` / `De:Ad:Be:Ef:Ca:Fe` | default `colon` | `SUCCESS` case folded uppercase |
| `MAC: 00:1A:2B:3C:4D:5E` / `mac - 001a.2b3c.4d5e` | default `colon` | `SUCCESS`, span includes label |
| `00:1A:2B:3C:4D:5E:66:77` (+ hyphen/dot/bare 64) | default `colon` | `SUCCESS` -> 8-group colon, `shape="eui64"` |
| `84:71:27:ff:fe:93:17:24` (Zigbee modified EUI-64) | default `colon` | `SUCCESS` -> `84:71:27:FF:FE:93:17:24` |
| `48-2C-6A-1E-59-3D` (bit-reversed Token-Ring spelling) | default `colon` | `SUCCESS` -> `48:2C:6A:1E:59:3D` (as-is, never reinterpreted) |
| `FF:FF:FF:FF:FF:FF` / `00:00:00:00:00:00` / `01:80:C2:00:00:00` / `33:33:00:00:00:01` | default `colon` | `SUCCESS` — sentinels valid, bits are predicates |
| any valid 48 | `output_format="hyphen"` / `"bare"` / `"cisco"` | `SUCCESS` -> `00-1A-2B-3C-4D-5E` / `001A2B3C4D5E` / `001A.2B3C.4D5E` |
| `00:1A:2B:3C:4D:5E` | `output_format="eui64"` | `SUCCESS` -> `00:1A:2B:FF:FE:3C:4D:5E` (FF-FE expansion) |
| `00:1A:2B:3C:4D:5E:66:77` | `output_format="eui64"` | `SUCCESS` -> unchanged (identity for EUI-64) |
| any valid | `output_format="bit_reversed"` | `SUCCESS` -> RFC 2469 per-octet swap (`12:34:56:78:9A:BC` -> `48:2C:6A:1E:59:3D`), involution holds |
| `MAC001A2B3C4D5E` (glued label) | default `colon` | `MISSING` (label `[\s:-]+` never zero-width; `M` not hex) |
| `00:1A-2B:3C-4D:5E` / `001A.2B3C:4D5E` (mixed separators) | default `colon` | `MISSING` |
| `00:1A:2B:3C:4D:5E:66` / `-66` / `001A.2B3C.4D5E.66` (truncated final octet) | default `colon` | `MISSING` (truncation guard + mid-run lookbehind) |
| `00:1A:2B:3C:4D:5E:6677` / `-3` (4-hex / 1-hex residue) | default `colon` | `SUCCESS` -> `00:1A:2B:3C:4D:5E` (complete valid form claims; residue unclaimed) |
| `84:71:27:ff:fe:93:17:24-11` (HA endpoint suffix) | default `colon` | `SUCCESS` -> `84:71:27:FF:FE:93:17:24` (EUI-64 truncation-guard exemption) |
| `001A2B3C4D5E6` (13 hex) / `001A2B3C4D5` (11 hex) | default `colon` | `MISSING` (quantifiers + guards) |
| `0:1b:77:49:54:fd` / `08002b:010203` / `00 1A 2B 3C 4D 5E` | default `colon` | `MISSING` (DEFERred tolerances, Research section 2.1) |
| `fe80::1` / `550e8400-e29b-…` / `X001A2B3C4D5E` | default `colon` | `MISSING` |
| `００:1A:2B:3C:4D:5E` / `00:1A:2B:3C:4D:0G` | default `colon` | `MISSING` (strict `(?ai:)` ASCII hex) |
| two distinct MACs in one slice | default `colon` | `MultipleMentionsError` (`single_value=True`) |
| identical MAC twice in one slice | default `colon` | `SUCCESS` (candidate dedup coalesces) |
| any valid | `year=2014` | `INVALID` (2024 rule temporally filtered; no pre-2024 rule ships) |

## Self Review Checklist

- One grammar, eight shape branches, single semantics `mac_address_recognition` — EUI-48 nests inside EUI-64 spans, so within-grammar longer-wins dedup applies and cross-grammar spurious `AMBIGUOUS` is structurally avoided (Research section 4.2/13 decision 3; `orchestrator:_dedup_spans`).
- Separator consistency per branch, not backreferences (group-number collision avoidance documented); mixed separators `MISSING` (validator.js `\1`, Go `s[2]`, PG "consistently" equivalence).
- Truncation guard on 48-bit branches only; EUI-64 exempt for the Home Assistant `{ieee}-{endpoint_id}` shape; mid-run lookbehind blocks tail claims; the fused `MAC` label is unaffected (lookbehinds constrain only the match start).
- No bit gating anywhere: broadcast/nil/multicast/local/FF-FE/FF-FF all `SUCCESS`; no bit-order reinterpretation (determinism; RFC 2469 + PostgreSQL "widely ignored" evidence).
- Rule `PARSER`, structure only, `normalize()` returns colon form; no checksum (proved); no `output_format` token in `rules/` (CI purity scan); provenance `IEEE Std 802-2024` `active` `2024`.
- Contract frozen without slots; `colon` default; 5 offered formats; `resolve_output_format` semantics (`None`/`"default"`/`"colon"` identical); no `active_grammars` override (base `None` runs the single shipped grammar).
- `modified_eui64` NOT offered (IPv6-domain semantic, Research section 13 decision 7); OUI registry layer + `include_oui_validation` deferred (13 decision 6) with the refresh procedure documented, not implemented; `_SHIPPED` bootstrap untouched (ISSN/IBAN/BIC precedent).
- No `# type: ignore` / `# noqa` in `paxman/` (the two `# type: ignore[misc]` in tests are the sanctioned immutability-check pattern); no cross-capability imports; deterministic; no network.

## Execution Notes for Agents

- TDD mandatory: failing test first for every task, red-green-commit cadence, one commit per task, do not batch completions.
- Notations frozen with slots; contracts frozen without slots (`paxman/core/domain.py`, `paxman/core/capability_contract.py`).
- Use `uv run` for every command (ruff, pyright, pytest, import-linter, coverage).
- The §4.2 pattern in the research report is **execution-validated** (27 positive / 26 negative vectors, byte-equal check); if the grammar tests disagree with it, suspect the transcription first, then re-run the research-report validation script before changing the pattern.
- The boundary.py `mac_midrun()` factory is the only core change; if core review rejects it, fall back to direct `BoundaryGuard(lookbehind=..., lookahead=...)` construction inside the grammar file and record the decision in the research report's §4.2 construction note.
- `paxman/api/bootstrap.py` `_SHIPPED` not touched in v1; integration tests register `MacAddress` directly inside the `_clean_registry` fixture window.
- URLs usable in code comments are only those from Research section 15: `https://standards.ieee.org/ieee/802/10894` (802-2024, search-verified), `https://standards.ieee.org/standard/802-2014.html` (fetched), `https://www.rfc-editor.org/rfc/rfc7042.txt`, `https://www.rfc-editor.org/rfc/rfc2469.txt`, `https://regauth.standards.ieee.org/`, `https://www.postgresql.org/docs/current/datatype-net-types.html`. Do not quote the EUI tutorial PDF in code comments until it has been re-fetched via the IEEE GET Program (research §15 marks it secondary).
