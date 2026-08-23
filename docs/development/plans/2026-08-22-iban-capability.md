# IBAN Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new `IBAN` capability that recognizes tolerant human IBAN surfaces (case, paper spacing, optional `IBAN` label), validates strictly via ISO 13616-1:2020 + ISO/IEC 7064:2003 MOD 97-10 (`mod97==1`, `DD` in `02-98`), and canonicalizes to compact electronic `CCDD+BBAN` (15-34, uppercase) with `paper` groups-of-four presentation — provenance-first, no registry lookup in v1.

**Architecture:** Single `PipelineGrammar` (`RegexStage` + `StandardPre` + `BoundaryGuard.word_only`) emitting `IBANNotation(country_code, check_digits, bban, compact)`; label fused with `[\s:-]+` separator (ISBN-13 precedent — a glued `IBANDE89…` must not fuse); word-only guards block left glue (`XDE89…`) and >34-char runs, while ≤30-char alnum tails are absorbed into the BBAN loop **by design** and rejected downstream by mod-97 (`INVALID`, documented — never silently `SUCCESS`); one mandatory `PARSER` rule `Section4IBANStructureMOD97` (generic length/charset/`DD` range + `mod97==1`); `IBANCapability.format_value` renders `electronic` (identity) vs `paper` (groups-of-four); `IBANContract` with `DEFAULT_OUTPUT_FORMAT="electronic"` `OFFERED={"paper"}`. Registry per-country LOOKUP_TABLE deferred behind `include_registry_validation` (YAGNI — not shipped in this plan).

**Tech Stack:** Python 3.11+, `uv`, `hatchling`, `ruff`, `pyright` strict, `import-linter`, `pytest` 95% coverage gates, `hypothesis` property tests.

---

## File Structure

```
paxman/capabilities/IBAN/
├── __init__.py              # re-exports; registers package (scaffolder edits paxman/capabilities/__init__.py)
├── notation.py              # IBANNotation — frozen+slots, 4 str fields
├── contract.py              # IBANContract(CapabilityContract) — electronic/paper
├── capability.py            # IBANCapability — get_grammars/get_rules/create_contract/format_value
├── grammar/
│   ├── __init__.py
│   └── iban_recognition.py  # PipelineGrammar[IBANNotation] single grammar
└── rules/
    ├── __init__.py
    └── iso_13616_1_ed2020.py # PUBLICATION + Section4IBANStructureMOD97 (PARSER)

tests/capabilities/iban/
├── __init__.py
├── test_notation.py
├── test_contract.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py
tests/integration/test_iban_capability.py  # MISSING/INVALID/SUCCESS + MultipleMentionsError, segmentation
```

**Created vs Modified:**
- **Create:** All `paxman/capabilities/IBAN/*` files (via `tools/new_capability.py` then domain fill; the scaffold's `rules/iso_ed2020.py` is renamed to `iso_13616_1_ed2020.py` in Task 4 Step 0)
- **Modify:** `paxman/capabilities/__init__.py` (alphabetical export — scaffolder does it), `tests/unit/test_capability_exports.py` (add `IBAN` import + `TestIBANCapabilityExports` + expected-set entry — Task 6 Step 1; it fails once the export exists, so it needs this patch), `docs/development/MILESTONE.md` line 27, `CONTEXT.md` (notation bullet + 3-column table row + count wording)
- **Test:** `tests/capabilities/iban/*` (marked `capability`), `tests/integration/test_iban_capability.py` (marked `integration`, per-test registration), `tests/unit/test_capability_surface.py` (auto-wired by scaffolder), `tests/property/test_iban_properties.py`
- **Not touched in v1:** `paxman/api/bootstrap.py` `_SHIPPED` — IBAN is deliberately NOT added to `register_all_shipped()` (ISSN precedent: shipped but not bootstrapped; Task 7 registers it directly); `rules/data/iban_registry.py` + `swift_iban_registry_ed2024.py` — intentionally deferred; plan documents refresh procedure but does not implement.

---

### Task 0: Scaffold and Baseline

**Files:**
- Create: `paxman/capabilities/IBAN/*` (via scaffolder)
- Modify: `paxman/capabilities/__init__.py` (auto-edited)
- Test: `tests/capabilities/iban/*` stubs (auto-generated)

- [ ] **Step 1: Run scaffolder**

```bash
uv run python tools/new_capability.py IBAN --name iban \
    --authority "ISO" --spec-name "ISO 13616-1:2020" --spec-url "https://www.iso.org/standard/81090.html" \
    --publication-year 2020 --default-format electronic
```

Expected: prints `Generated capability skeleton:` followed by 13 file paths (9 package files + 4 test stubs) and `paxman/capabilities/__init__.py (wired)`. Verify `ls paxman/capabilities/IBAN/` lists `notation.py contract.py capability.py grammar/ rules/`.

Two scaffolder byproducts to know about:
- It also wires `tests/unit/test_capability_surface.py` (`_wire_surface_guard` adds the `_CAPABILITY_SURFACES` entry) — no manual edit needed there.
- It derives the rule file name from `--authority "ISO"` → `rules/iso_ed2020.py` with placeholder class `IBANRule` (`Section 1-overview`, `TODO(scaffold)` markers). Task 4 Step 0 renames it to `iso_13616_1_ed2020.py` — do not leave the placeholder behind.
- It does **not** patch `tests/unit/test_capability_exports.py`; once IBAN is in `__all__` that gate fails by design — Task 6 Step 1 patches it.

- [ ] **Step 2: Run baseline lint/type on scaffold**

```bash
uv run ruff check paxman/capabilities/IBAN/ --fix
uv run pyright paxman/capabilities/IBAN/
uv run pytest tests/capabilities/iban/ -v
```

Expected: `ruff` clean or auto-fix, `pyright` 0 errors (stub passes), pytest stubs pass (scaffold's placeholder `test_notation.py` checks `value`).

- [ ] **Step 3: Commit scaffold**

```bash
git add paxman/capabilities/IBAN/ paxman/capabilities/__init__.py tests/capabilities/iban/
git commit -m "feat(iban): scaffold IBAN capability via tools/new_capability.py"
```

---

### Task 1: Notation — IBANNotation

**Files:**
- Modify: `paxman/capabilities/IBAN/notation.py`
- Test: `tests/capabilities/iban/test_notation.py`

Research §3.1: `country_code` 2 A-Z, `check_digits` 2 digits, `bban` 1-30 alphanum, `compact` 15-34 ≡ `country_code+check_digits+bban`. Frozen+slots, all `str`. No validation in `__post_init__` beyond type shape — grammar owns stripping, rules own mod97.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/iban/test_notation.py
import pytest
from dataclasses import FrozenInstanceError
from paxman.capabilities.IBAN.notation import IBANNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash():
    n = IBANNotation(
        country_code="DE",
        check_digits="89",
        bban="370400440532013000",
        compact="DE89370400440532013000",
    )
    assert n.country_code == "DE"
    assert hash(n) is not None
    assert hasattr(n, "__slots__")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_compact_is_concatenation():
    n = IBANNotation(
        country_code="GB",
        check_digits="29",
        bban="NWBK60161331926819",
        compact="GB29NWBK60161331926819",
    )
    assert n.compact == n.country_code + n.check_digits + n.bban
    assert 15 <= len(n.compact) <= 34
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/iban/test_notation.py -v`
Expected: FAIL — `IBANNotation` still has `value: str` stub, missing fields.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/IBAN/notation.py
"""IBAN notation — grammar-normalized compact form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class IBANNotation:
    """IBAN notation — compact + structured decomposition.

    ``country_code`` 2-letter ISO 3166-1 alpha-2, uppercased.
    ``check_digits`` 2-digit string at positions 3-4.
    ``bban`` 1-30 alphanum, uppercased, spaces stripped.
    ``compact`` electronic string country_code+check_digits+bban (15-34).
    The grammar never computes mod-97; rules own it.
    """

    country_code: str  # e.g. "DE" — length 2, A-Z
    check_digits: str  # e.g. "89" — length 2, 0-9
    bban: str  # e.g. "370400440532013000" — 1-30 alphanum
    compact: str  # e.g. "DE89370400440532013000" — 15-34
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/iban/test_notation.py -v`
Expected: PASS (2 passed). Also `uv run pyright paxman/capabilities/IBAN/notation.py` 0 errors, `uv run ruff check paxman/capabilities/IBAN/notation.py`.

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/IBAN/notation.py tests/capabilities/iban/test_notation.py
git commit -m "feat(iban): define IBANNotation frozen+slots with 4 str fields"
```

---

### Task 2: Contract — IBANContract

**Files:**
- Modify: `paxman/capabilities/IBAN/contract.py`
- Test: `tests/capabilities/iban/test_contract.py`

Research §6.1: `DEFAULT_OUTPUT_FORMAT="electronic"` (compact no-space uppercase), `OFFERED={"paper"}` (`compact` documented as alias but not a distinct offered format to keep invariant). No `include_registry_validation` in v1 (deferred). Inherits `CapabilityContract`; `capability_name="iban"`; `resolve_output_format` exercised via base `__post_init__`. Must be `@dataclass(frozen=True)` **without** `slots`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/iban/test_contract.py
import pytest
from paxman.core.errors import ContractError
from paxman.capabilities.IBAN.contract import IBANContract

pytestmark = [pytest.mark.capability]


def test_default_output_format_resolves():
    c = IBANContract()
    assert c.output_format == "electronic"
    assert c.capability_name == "iban"
    assert IBANContract.DEFAULT_OUTPUT_FORMAT == "electronic"
    assert IBANContract.OFFERED_OUTPUT_FORMATS == frozenset({"paper"})


def test_paper_offered():
    c = IBANContract(output_format="paper")
    assert c.output_format == "paper"


def test_default_alias_via_none_and_default_string():
    for alias in (None, "default", "electronic"):
        c = IBANContract(output_format=alias)
        assert c.output_format == "electronic"


def test_invalid_output_format_raises():
    with pytest.raises(ContractError):
        IBANContract(output_format="hyphenated")  # ISSN-ism, not IBAN
    with pytest.raises(ContractError):
        IBANContract(
            output_format="compact"
        )  # alias not offered; must normalize outside


def test_frozen_contract():
    from dataclasses import FrozenInstanceError

    c = IBANContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "paper"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/iban/test_contract.py -v`
Expected: only `test_paper_offered` FAILS — the scaffold already bakes `DEFAULT_OUTPUT_FORMAT="electronic"` (from `--default-format electronic`) and `capability_name="iban"`, but its `OFFERED_OUTPUT_FORMATS` is the empty `frozenset()`. The other four tests (default resolution, `None`/`"default"`/`"electronic"` aliases, `ContractError` for `"hyphenated"`/`"compact"`, frozen) already pass on the scaffold.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/IBAN/contract.py
"""IBAN contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class IBANContract(CapabilityContract):
    """User-facing contract for IBAN capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "electronic"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"paper"})

    capability_name: str = field(default="iban", init=False)
    # No include_registry_validation in v1 — deferred YAGNI
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/iban/test_contract.py -v` → PASS.
Run: `uv run pyright paxman/capabilities/IBAN/contract.py` → 0 errors, `uv run ruff check paxman/capabilities/IBAN/`.

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/IBAN/contract.py tests/capabilities/iban/test_contract.py
git commit -m "feat(iban): define IBANContract electronic default with paper offered"
```

---

### Task 3: Grammar — iban_recognition

**Files:**
- Modify: `paxman/capabilities/IBAN/grammar/iban_recognition.py`, `paxman/capabilities/IBAN/grammar/__init__.py`
- Test: `tests/capabilities/iban/test_grammar.py`

Research §4.2 (corrected per Oracle): **Single** `PipelineGrammar` with `StandardPre(empty_guard=True)`, `RegexStage` using `BoundaryGuard.word_only().lookbehind` + `BoundaryGuard.word_only().lookahead`. Pattern fused `IBAN` label, case-insensitive, paper single-space tolerance. Minimum `11` BBAN → `15` total (`NO15`), maximum `30` BBAN → `34` total.

**Pattern (module-scope string, compiled by RegexStage) — Oracle round-2 corrected:**

```python
_IBAN_BODY = r"(?:IBAN[\s:-]+)?(?P<compact>[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})"
_IBAN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _IBAN_BODY
    + BoundaryGuard.word_only().lookahead
)
```

Key design points (verbatim in the code comments):

- **Label separator is `[\s:-]+` (one-or-more), not `*`.** A glued `IBANDE89…` must NOT fuse into a mention. Shipped ISBN-13 uses `[\s:-]+` for exactly this (`_ISBN13_BODY`); ISSN's `*` would absorb the label. With `+`, `IBANDE89…` has no valid label prefix (needs ≥1 separator) and the bare `DE89…` carve at index 4 is blocked by the `(?<!\w)` lookbehind (preceded by `N`).
- **`BoundaryGuard.word_only()` (`(?<!\w)` / `(?!\w)`):** the lookbehind blocks preceding-letter glue (`XDE89…` → `MISSING`, verified — a carve can only start at a position whose previous char is non-word, and the `CC` prefix pins the start). The trailing lookahead blocks >34-char runs: the `{11,30}` BBAN loop caps at 30, and every interior end position of an alnum run is followed by a word char, so no end passes `(?!\w)` → no match.
- **Documented limitation (do not "fix" with a guard):** an alnum tail ≤30 chars glued to a valid IBAN (`DE89370400440532013000Y`) is **absorbed into the BBAN loop** — the match claims the tail inside `compact`. This is inherent to a variable-length loop (the engine always extends rather than stop before valid IBAN chars). Downstream, mod-97 rejects the absorbed form (`INVALID` — verified: `mod97("DE89370400440532013000Y") == 37`), never `SUCCESS`. The grammar test `test_alnum_tail_absorbed_documented` pins this so it stays deliberate; callers needing strict mention boundaries pre-tokenize.

`notation_fn` via `isalnum().upper()` split into `country_code/check_digits/bban/compact`. Shipped ISSN precedent is `word_only().lookbehind` (not `isbn10_lead`) — cite in comment.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/iban/test_grammar.py
import pytest

from paxman.capabilities.IBAN.grammar.iban_recognition import IBANRecognitionGrammar

pytestmark = [pytest.mark.capability]

GRAMMAR = IBANRecognitionGrammar()


def test_valid_electronic():
    m = GRAMMAR.recognize("DE89370400440532013000")
    assert len(m) == 1
    n = m[0].notation
    assert n.compact == "DE89370400440532013000"
    assert n.country_code == "DE" and n.check_digits == "89"
    assert m[0].raw_text == "DE89370400440532013000"
    assert m[0].end - m[0].start == len(m[0].raw_text)


def test_paper_groups_of_four():
    m = GRAMMAR.recognize("DE89 3704 0044 0532 0130 00")
    assert m[0].notation.compact == "DE89370400440532013000"


def test_case_insensitive_and_label():
    for txt in [
        "de89370400440532013000",
        "IBAN: DE89 3704 0044 0532 0130 00",
        "iban:gb29nwbk60161331926819",
        "IBAN - FR14 2004 1010 0505 0001 3M02 606",
        "IBAN DE89370400440532013000",
    ]:
        assert len(GRAMMAR.recognize(txt)) == 1


def test_lowercase_label_and_compact():
    m = GRAMMAR.recognize("iban: gb29 nwbk 6016 1331 9268 19")
    assert m[0].notation.compact == "GB29NWBK60161331926819"


def test_word_guard_blocks_left_and_label_glue():
    # Left glue: (?<!\w) lookbehind rejects carving out of a longer token.
    assert GRAMMAR.recognize("XDE89370400440532013000") == []
    # Glued label: separator is [\s:-]+ (ISBN-13 precedent), never zero-width.
    assert GRAMMAR.recognize("IBANDE89370400440532013000") == []


def test_alnum_tail_absorbed_documented():
    # A <=30-char alnum tail is absorbed into the BBAN loop BY DESIGN (the
    # variable-length loop extends rather than stop before valid IBAN chars).
    # mod-97 rejects the absorbed form downstream (INVALID), never SUCCESS.
    # Do not "fix" by tightening the loop — that would also break paper
    # single-space tolerance; pre-tokenize for strict mention boundaries.
    m = GRAMMAR.recognize("DE89370400440532013000Y")
    assert len(m) == 1
    assert m[0].notation.compact == "DE89370400440532013000Y"


def test_min_and_max_length_bounds():
    assert GRAMMAR.recognize("NO938601111794") == []  # 14 — below 15 min
    assert len(GRAMMAR.recognize("NO93 8601 1117 947")) == 1  # 15 min (paper)
    assert GRAMMAR.recognize("DE89" + "A" * 31) == []  # 35 — above 34 max
    # A >34 alnum run cannot be carved: every interior end position is
    # followed by a word char, so the trailing (?!\w) rejects all candidates.


def test_multi_whitespace_rejected_narrow_tolerance():
    # Only single spaces are tolerated (paper groups-of-four). Double spaces
    # and tabs are NOT matched — documented narrow decision (research edge 3
    # "MISSING with strict [ ]? only"). Do not add \s+ tolerance here.
    assert GRAMMAR.recognize("DE89  3704 0044 0532 0130 00") == []
    assert GRAMMAR.recognize("DE89\t3704 0044") == []


def test_multiple_matches():
    txt = "DE89 3704 0044 0532 0130 00 / GB29 NWBK 6016 1331 9268 19"
    assert len(GRAMMAR.recognize(txt)) == 2


def test_semantics_and_name():
    assert GRAMMAR.name == "iban_recognition"
    assert GRAMMAR.semantics == "iban_recognition"
    assert GRAMMAR.single_value is True


def test_span_invariants():
    txt = "Pay to DE89 3704 0044 0532 0130 00 now"
    m = GRAMMAR.recognize(txt)[0]
    assert txt[m.start : m.end] == m.raw_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/iban/test_grammar.py -v`
Expected: FAIL — scaffold grammar still matches `value` placeholder.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/IBAN/grammar/iban_recognition.py
"""IBAN recognition — CCDD+BBAN with optional IBAN label and paper spacing."""

from __future__ import annotations

import re

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ (one-or-more), never zero-width: a glued
# "IBANDE89..." must not fuse into a mention (ISBN-13 precedent).
_IBAN_BODY = r"(?:IBAN[\s:-]+)?(?P<compact>[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,30})"
# word_only guards: the lookbehind blocks left glue (XDE89...); the trailing
# lookahead plus the 30-char loop cap blocks >34-char runs (every interior
# end is followed by a word char). A <=30-char alnum tail is absorbed by
# design — mod-97 rejects it downstream (INVALID); see
# test_alnum_tail_absorbed_documented in the grammar tests.
_IBAN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _IBAN_BODY
    + BoundaryGuard.word_only().lookahead
)


def _iban_notation(match: re.Match[str]) -> IBANNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isalnum()).upper()
    country_code = compact[0:2]
    check_digits = compact[2:4]
    bban = compact[4:]
    return IBANNotation(
        country_code=country_code, check_digits=check_digits, bban=bban, compact=compact
    )


class IBANRecognitionGrammar(PipelineGrammar[IBANNotation]):
    """IBAN recognition — CCDD+BBAN with optional IBAN label and paper spacing."""

    name = "iban_recognition"
    semantics = "iban_recognition"
    single_value = True
    pre = StandardPre[IBANNotation](empty_guard=True)
    regex = RegexStage[IBANNotation](
        pattern=_IBAN_PATTERN, notation_fn=_iban_notation, flags=re.IGNORECASE
    )
```

Expose in `grammar/__init__.py`:

```python
from paxman.capabilities.IBAN.grammar.iban_recognition import IBANRecognitionGrammar

__all__ = ["IBANRecognitionGrammar"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/iban/test_grammar.py -v` → 11 passed.
Run: `uv run pyright paxman/capabilities/IBAN/grammar/iban_recognition.py` → 0 errors.
Run: `uv run ruff check paxman/capabilities/IBAN/grammar/`

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/IBAN/grammar/iban_recognition.py paxman/capabilities/IBAN/grammar/__init__.py tests/capabilities/iban/test_grammar.py
git commit -m "feat(iban): implement iban_recognition PipelineGrammar with word_only guards"
```

---

### Task 4: Rules — ISO 13616-1:2020 + MOD 97-10

**Files:**
- Modify: `paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py`, `paxman/capabilities/IBAN/rules/__init__.py`
- Test: `tests/capabilities/iban/test_rules.py`

Research §5 + §7: One `PUBLICATION` (`authority="ISO"`, `specification_name="ISO 13616-1:2020"`, `reference_url="https://www.iso.org/standard/81090.html"`, `version="2020"`, `lifecycle="active"`, `publication_year=2020`, `kind="specification"`). One `PARSER` rule `Section4IBANStructureMOD97` (`name="Section 4-iban-structure-mod97"`, `target_semantics={"iban_recognition"}`, `requires_features=frozenset()`). Docstring cites `ISO/IEC 7064:2003 MOD 97-10` as normative reference (fused v1; split file later if reviewers demand per-publication purity — YAGNI). **Never reads `output_format`** (CI source-scan enforced). `matches()` validates `15-34`, `[A-Z]{2}\d{2}[A-Z0-9]{1,30}`, `DD` in `02-98` (reject `00/01/99`), `mod97==1`. `normalize()` returns `notation.compact` (electronic).

Piece-wise `mod97` to avoid big-int: `r=0; for ch in expanded: r=(r*10+int(ch))%97` where `expanded` is rearranged `bban+cc+dd` with `A=10…Z=35` (`ord-55`).

- [ ] **Step 0: Rename the scaffold placeholder rule file**

The scaffolder created `rules/iso_ed2020.py` (name derived from `--authority "ISO"`) with placeholder class `IBANRule` / `Section 1-overview` / `TODO(scaffold)`. Rename it to the per-publication convention before filling; leaving the placeholder behind would trip Task 8's placeholder scan, and its `normalize()` would break on the new notation shape:

```bash
git mv paxman/capabilities/IBAN/rules/iso_ed2020.py paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py
```

`rules/__init__.py` stays the scaffold docstring-only stub; Step 3 replaces it with the module exposure.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/iban/test_rules.py
import pytest

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import (
    Section4IBANStructureMOD97,
    PUBLICATION,
)
from paxman.capabilities.IBAN.contract import IBANContract

pytestmark = [pytest.mark.capability]

RULE = Section4IBANStructureMOD97()
CONTRACT = IBANContract()


def n(compact: str) -> IBANNotation:
    return IBANNotation(
        country_code=compact[:2],
        check_digits=compact[2:4],
        bban=compact[4:],
        compact=compact,
    )


def test_provenance_metadata():
    assert PUBLICATION.authority == "ISO"
    assert PUBLICATION.specification_name == "ISO 13616-1:2020"
    assert PUBLICATION.reference_url == "https://www.iso.org/standard/81090.html"
    assert PUBLICATION.lifecycle == "active"
    assert PUBLICATION.publication_year == 2020
    assert PUBLICATION.kind == "specification"
    assert RULE.name == "Section 4-iban-structure-mod97"
    assert RULE.strategy.name == "PARSER"
    assert RULE.target_semantics == frozenset({"iban_recognition"})
    assert RULE.requires_features == frozenset()


def test_valid_vectors():
    # Oracle-corrected vectors; LC/NI 32 are longest per R100
    for compact in [
        "DE89370400440532013000",  # DE22 8!n10!n
        "GB29NWBK60161331926819",  # GB22 4!a6!n8!n
        "FR1420041010050500013M02606",  # FR27
        "NO9386011117947",  # NO15 4!n6!n1!n (corrected per Oracle)
        "MT84MALT011000012345MTLCAS T001S".replace(
            " ", ""
        ),  # MT31 -> MT84MALT011000012345MTLCAST001S
        "SC18SSCB11010000000000001497USD",  # SC31 group 1497 (0149 fails mod97==60)
        "LC55HEMM000100010012001200023015",  # LC32 longest
        "NI92BAMC000000000000000003123123",  # NI32 longest
        "GB82WEST12345698765432",  # Wikipedia check-positive
    ]:
        compact = compact.replace(" ", "")
        assert RULE.matches(n(compact), CONTRACT) is True, compact
        assert RULE.normalize(n(compact), CONTRACT) == compact


def test_invalid_mod97_and_dd_range():
    assert RULE.matches(n("DE89370400440532013001"), CONTRACT) is False  # check flipped
    for bad_dd in [
        "DE00370400440532013000",
        "DE01370400440532013000",
        "DE99370400440532013000",
    ]:
        # 00/01/99 never assigned — fast-reject before mod97 (generic still mod97-invalid for most)
        assert RULE.matches(n(bad_dd), CONTRACT) is False
    assert (
        RULE.matches(n("DE8937040044053201300"), CONTRACT) is False
    )  # 21 vs DE22 too short (<15 still, but generic 15-34 path)
    assert RULE.matches(n("AB12"), CONTRACT) is False


def test_structure_edge_table():
    # Rule-level structural edges (the grammar normally prevents these shapes;
    # exercised directly so the rule's defensive branches stay covered — the
    # per-package 95% gate needs them):
    assert RULE.matches(n("DE89" + "A" * 31), CONTRACT) is False  # 35 > 34
    assert RULE.matches(n("NO938601111794"), CONTRACT) is False  # 14 < 15
    assert RULE.matches(n("1E89370400440532013000"), CONTRACT) is False  # CC not alpha
    assert (
        RULE.matches(n("DEAB3704004405320130000"), CONTRACT) is False
    )  # DD not digits
    assert (
        RULE.matches(n("de89370400440532013000"), CONTRACT) is False
    )  # lowercase (isupper)
    assert (
        RULE.matches(n("DE89 3704 0044 0532 0130 00"), CONTRACT) is False
    )  # space inside compact
```

(Adjust MT compact to `MT84MALT011000012345MTLCAST001S` — verify mod97 in Step 2.)

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/iban/test_rules.py -v`
Expected: FAIL — `Section4IBANStructureMOD97` not implemented; MT/LC/NI vectors will reveal any off-by-one mod97.

*Also verify the new vectors in isolation:*

```bash
uv run python - << 'PY'
def mod97(s):
    s=s.replace(" ","").upper(); r=s[4:]+s[:4]; exp="".join(str(ord(c)-55) if c.isalpha() else c for c in r); v=0
    for ch in exp: v=(v*10+int(ch))%97
    return v
for v in ["MT84MALT011000012345MTLCAST001S","SC18SSCB11010000000000001497USD","LC55HEMM000100010012001200023015","NI92BAMC000000000000000003123123"]:
    print(v, mod97(v))
PY
```

Expected: all `1`.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py
"""ISO 13616-1:2020 + ISO/IEC 7064:2003 MOD 97-10 — generic IBAN structure."""

from __future__ import annotations

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 13616-1:2020",
    kind="specification",
    reference_url="https://www.iso.org/standard/81090.html",
    version="2020",
    lifecycle="active",
    publication_year=2020,
)


def _mod97(compact: str) -> int:
    # Input is grammar-normalized uppercase and matches() re-checks isupper(),
    # so only A-Z expansion is needed here — a lowercase fallback branch would
    # be dead code and drag the per-package 95% line-coverage gate.
    rearranged = compact[4:] + compact[:4]
    # expand letters A=10..Z=35 (ord-55), digits stay single
    expanded_chars: list[str] = []
    for ch in rearranged:
        if "A" <= ch <= "Z":
            expanded_chars.append(str(ord(ch) - 55))
        else:
            expanded_chars.append(ch)
    expanded = "".join(expanded_chars)
    r = 0
    for d in expanded:
        r = (r * 10 + int(d)) % 97
    return r


class Section4IBANStructureMOD97(Rule[IBANNotation]):
    """ISO 13616-1 §4-5 + ISO/IEC 7064 MOD 97-10 — generic IBAN validation.

    Validates generic IBAN: total 15-34, charset [A-Z]{2}[0-9]{2}[A-Z0-9]{1,30},
    DD in 02-98 (reject 00/01/99), and mod97==1. Citations: ISO 13616-1:2020
    structure + MOD 97-10 normative reference to ISO/IEC 7064:2003.
    """

    name = "Section 4-iban-structure-mod97"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4-5 (structure + MOD 97-10, via ISO/IEC 7064:2003)"
    target_semantics = frozenset({"iban_recognition"})
    requires_features = frozenset()

    def matches(self, notation: IBANNotation, contract: Contract) -> bool:
        c = notation.compact
        if not (15 <= len(c) <= 34):
            return False
        # charset already normalized by grammar, but double-check
        if not c[:2].isalpha() or not c[2:4].isdigit() or not c[4:].isalnum():
            return False
        if not c.isupper():
            return False
        dd = c[2:4]
        if dd in ("00", "01", "99"):
            return False
        # generic charset upper alphanum
        if not all("0" <= ch <= "9" or "A" <= ch <= "Z" for ch in c):
            return False
        return _mod97(c) == 1

    def normalize(self, notation: IBANNotation, contract: Contract) -> str:
        return notation.compact
```

Expose in `rules/__init__.py`:

```python
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import Section4IBANStructureMOD97

__all__ = ["Section4IBANStructureMOD97"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/iban/test_rules.py -v` → PASS (4).
Run: `uv run pyright paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py` → 0 errors.
Run: `uv run ruff check paxman/capabilities/IBAN/rules/` → clean (no `output_format` token — verify with `grep -r output_format paxman/capabilities/IBAN/rules/` → empty).

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/IBAN/rules/iso_13616_1_ed2020.py paxman/capabilities/IBAN/rules/__init__.py tests/capabilities/iban/test_rules.py
git commit -m "feat(iban): add Section 4-iban-structure-mod97 PARSER (mod97==1, DD 02-98)"
```

---

### Task 5: Capability — wiring, create_contract, format_value

**Files:**
- Modify: `paxman/capabilities/IBAN/capability.py`
- Test: `tests/capabilities/iban/test_capability.py`

Research §6.2: `name="iban"`, `get_grammars() → [IBANRecognitionGrammar()]`, `get_rules() → [Section4IBANStructureMOD97()]`, `create_contract` tuple-normalizes `excluded_rules/pinned_rules/extra_grammars` (shipped idiom), `format_value` `paper` is `" ".join(value[i:i+4] for i in range(0, len(value), 4))`, default identity.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/iban/test_capability.py
import pytest

from paxman.capabilities.IBAN.capability import IBANCapability
from paxman.capabilities.IBAN.notation import IBANNotation

pytestmark = [pytest.mark.capability]

CAP = IBANCapability()


def test_wiring_counts():
    assert CAP.name == "iban"
    assert len(CAP.get_grammars()) == 1
    assert CAP.get_grammars()[0].name == "iban_recognition"
    assert len(CAP.get_rules()) == 1
    assert CAP.get_rules()[0].name == "Section 4-iban-structure-mod97"


def test_create_contract_defaults():
    c = CAP.create_contract()
    assert c.output_format == "electronic"
    assert c.excluded_rules == ()
    assert c.pinned_rules is None


def test_format_value_paper_roundtrip():
    cases = {
        "DE89370400440532013000": "DE89 3704 0044 0532 0130 00",
        "GB29NWBK60161331926819": "GB29 NWBK 6016 1331 9268 19",
        "NO9386011117947": "NO93 8601 1117 947",  # NO15 last group 3
        "LC55HEMM000100010012001200023015": "LC55 HEMM 0001 0001 0012 0012 0002 3015",  # 32
    }
    for electronic, paper in cases.items():
        n = IBANNotation(
            country_code=electronic[:2],
            check_digits=electronic[2:4],
            bban=electronic[4:],
            compact=electronic,
        )
        assert CAP.format_value(electronic, "paper", n) == paper
        assert CAP.format_value(electronic, None, n) == electronic
        assert CAP.format_value(electronic, "electronic", n) == electronic
        # electronic → paper → electronic is lossless via stripped spaces, but format_value does grouping only
        assert CAP.format_value(paper.replace(" ", ""), "paper", n) == paper
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/iban/test_capability.py -v` → FAIL (stub capability).

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/IBAN/capability.py
"""IBAN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.IBAN.contract import IBANContract
from paxman.capabilities.IBAN.grammar.iban_recognition import IBANRecognitionGrammar
from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import Section4IBANStructureMOD97
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["IBANCapability", "IBANContract", "IBANNotation"]


class IBANCapability(Capability[IBANNotation]):
    """IBAN canonicalization — electronic compact with paper presentation."""

    name = "iban"

    def get_grammars(self) -> list[Grammar[IBANNotation]]:
        return [IBANRecognitionGrammar()]

    def get_rules(self) -> list[Rule[IBANNotation]]:
        return [Section4IBANStructureMOD97()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> IBANContract:
        """Factory method for creating contracts with proper defaults."""
        return IBANContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    def format_value(
        self, value: str, output_format: str | None, notation: IBANNotation
    ) -> str:
        if output_format == "paper":
            return " ".join(value[i : i + 4] for i in range(0, len(value), 4))
        return value
```

*Note:* Use the shipped tuple-normalization idiom `tuple(excluded_rules) if excluded_rules else ()` (not `or []`).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/iban/test_capability.py -v` → PASS (3).
Run: `uv run pyright paxman/capabilities/IBAN/capability.py` → 0 errors (Step 3 already writes the final `-> IBANContract` annotation — no `# type: ignore` anywhere in `paxman/` source, per project anti-pattern; Task 8's grep must print `clean`).

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/IBAN/capability.py tests/capabilities/iban/test_capability.py
git commit -m "feat(iban): wire IBANCapability with electronic/paper seam"
```

---

### Task 6: Exports, Surface Homogeneity, and Docs

**Files:**
- Modify: `paxman/capabilities/__init__.py` (verify), `CONTEXT.md`, `docs/development/MILESTONE.md`
- Test: `tests/unit/test_capability_exports.py`, `tests/unit/test_capability_surface.py` (existing gates)

Scaffolder already edited `paxman/capabilities/__init__.py` alphabetically (`__all__` + `_LAZY` + `TYPE_CHECKING`) and wired `tests/unit/test_capability_surface.py`. **`tests/unit/test_capability_exports.py` is NOT patched by the scaffolder and now FAILS by design** — task Step 1 fixes it. Update `CONTEXT.md` (notation bullet + 3-column table row + count wording) and MILESTONE line 27.

> **Bootstrap note:** `paxman/api/bootstrap.py` (`_SHIPPED`) is intentionally NOT modified in this plan — `register_all_shipped()` keeps the ten-name tuple (ISSN ships but is also not bootstrapped, cf. its integration tests which register directly). Task 7 integration tests therefore register IBAN per-test inside the fixture window. Revisit only when IBAN becomes a bootstrap default.

- [ ] **Step 1: Patch the exports completeness gate**

```bash
uv run pytest tests/unit/test_capability_exports.py -v
```

Expected: FAIL — `test_export_list_contains_ten_names` now sees 12 names in `__all__` vs the expected 11. This is the REVERSE of the old expectation ("FAIL until export present"): the gate fails **because** the scaffolder's export exists. Patch the test file:

```python
# tests/unit/test_capability_exports.py — add IBAN to the import block:
from paxman.capabilities import (
    IBAN,
    IP,
    ISBN,
    ...
)

# Add a class mirroring TestISBNCapabilityExports:
class TestIBANCapabilityExports:
    @pytest.mark.unit
    def test_iban_capability_importable(self) -> None:
        """IBAN capability is importable from paxman.capabilities."""
        assert IBAN is not None

    @pytest.mark.unit
    def test_iban_capability_name(self) -> None:
        """IBAN capability has correct name."""
        assert IBAN.name == "iban"

# In test_export_list_contains_ten_names, add "IBAN" to the expected set
# (and rename the function's docstring "eleven" -> "twelve" is optional;
# the test function name itself is legacy and may stay):
assert set(capabilities.__all__) == {
    "Country",
    "Currency",
    "Date",
    "Email",
    "IBAN",
    "IP",
    "ISBN",
    "ISSN",
    "Money",
    "Phone",
    "SIUnit",
    "URL",
}
```

- [ ] **Step 2: Run the homogeneity gates**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v
```

Expected: all PASS — the scaffolder already added the `_CAPABILITY_SURFACES` entry to `test_capability_surface.py`, so only the exports test needed the Step-1 patch.

- [ ] **Step 3: Patch CONTEXT.md**

Three edits (CONTEXT.md is the domain glossary, kept in sync with the code):

1. **Notation bullet list** — add after the `**ISSN:**` bullet:

```
- **IBAN:** `IBANNotation(country_code, check_digits, bban, compact)` — `country_code` is the 2-letter ISO 3166-1 alpha-2 prefix, `check_digits` the 2-digit MOD 97-10 pair, `bban` the 1-30 alphanum remainder, `compact` the full electronic string (15-34, ≡ cc+dd+bban); grammar uppercases and strips paper spaces
```

2. **Capabilities table** (`| Capability | Domain | Authorities |`, 3 columns) — insert the row after the `| **ISSN** |` row:

```
| **IBAN** | Bank account numbers | ISO 13616-1:2020, ISO/IEC 7064:2003 (MOD 97-10) |
```

3. **Count wording** — the intro sentence "Paxman ships eleven built-in capabilities" → "twelve built-in capabilities".

(Do NOT paste the 7-column row shape from earlier drafts — CONTEXT.md's Capabilities table is 3 columns; a wider row breaks its shape.)

- [ ] **Step 4: Patch MILESTONE.md line 27 (table row 15)**

Replace the row's spec cells (currently "ISO 13616 (ECBS)" / "ISO 13616:2020, ECBS IBAN Registry, SWIFT IBAN Registry") with the plan's authority:

```
| 15 | **IBAN** | International Bank Account Numbers appear in financial data with spaces, uppercase/lowercase, and country-code prefixes. ISO 13616-1:2020 defines the structure. | PARSER (single-space paper tolerance, uppercase, validate check digits via MOD 97-10, canonical electronic + groups-of-four paper) | ISO 13616-1:2020, ISO/IEC 7064:2003 (MOD 97-10), SWIFT IBAN Registry (Release 100, Oct 2025 — deferred) | "DE89 3704 0044 0532 0130 00" → "DE89370400440532013000", "gb29 nwbk 6016 1331 9268 19" → "GB29NWBK60161331926819" |
```

Note: the IBAN row sits at file line 27 (table row 15) — edit by line, not by table row number.

- [ ] **Step 5: Run gates**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py tests/unit/test_rule_output_format_purity.py -v
uv run pyright
uv run ruff check paxman/ tests/
uv run import-linter lint
```

Expected: all PASS (purity scan must find no `output_format` in `paxman/capabilities/IBAN/rules/`).

- [ ] **Step 6: Commit**

```bash
git add paxman/capabilities/__init__.py CONTEXT.md docs/development/MILESTONE.md
git commit -m "docs(iban): exports completeness, CONTEXT and MILESTONE"
```

---

### Task 7: Integration, Resolution Map, and Property Tests

**Files:**
- Create: `tests/integration/test_iban_capability.py`
- Modify: none — the rule edge table is part of Task 4
- Test: `tests/integration/test_iban_capability.py`

Research §8-9, §12: Full pipeline `MISSING`/`INVALID`/`SUCCESS` with `single_value=True` — two distinct mentions raise `MultipleMentionsError` (never `Resolution.AMBIGUOUS`, which is reserved for one-cluster multi-value reads), paper vs electronic dedup, `year` temporal filter, `VersionStamp` determinism, span invariants, tail-absorption `INVALID`, Egypt print exception note, `00/01/99` nuance.

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_iban_capability.py
import pytest

import paxman
from paxman.capabilities.IBAN.capability import IBANCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test (shipped ISSN pattern)."""
    reset_registry()
    yield
    reset_registry()


def _register_iban() -> None:
    # register_all_shipped() does NOT include IBAN (bootstrap._SHIPPED is the
    # ten-name tuple; ISSN has the same status) — register directly per test,
    # inside the fixture window, never at module level (module-level
    # registration is wiped by every file's autouse reset).
    register_capability(IBANCapability())


def test_success_electronic_and_paper_same_canonical():
    _register_iban()
    contract = IBANCapability.create_contract()
    for txt in [
        "DE89370400440532013000",
        "DE89 3704 0044 0532 0130 00",
        "de89370400440532013000",
        "IBAN: DE89 3704 0044 0532 0130 00",
    ]:
        r = paxman.canonicalize(txt, contract)
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DE89370400440532013000"
        assert r.candidates[0].provenance[0].specification_name == "ISO 13616-1:2020"
        assert r.span is not None


def test_paper_output_format():
    _register_iban()
    contract = IBANCapability.create_contract(output_format="paper")
    r = paxman.canonicalize("DE89370400440532013000", contract)
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "DE89 3704 0044 0532 0130 00"


def test_invalid_mod97():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert (
        paxman.canonicalize("DE89370400440532013001", contract).status
        == Resolution.INVALID
    )


def test_tail_glue_absorbed_is_invalid():
    # Documented carve (grammar test test_alnum_tail_absorbed_documented):
    # the absorbed alnum tail is rejected by mod-97 -> INVALID, never SUCCESS.
    _register_iban()
    contract = IBANCapability.create_contract()
    assert (
        paxman.canonicalize("DE89370400440532013000Y", contract).status
        == Resolution.INVALID
    )


def test_missing_short_and_bban_only():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert paxman.canonicalize("AB12", contract).status == Resolution.MISSING
    assert (
        paxman.canonicalize("370400440532013000", contract).status == Resolution.MISSING
    )  # BBAN only


def test_two_distinct_ibans_raise_multiple_mentions():
    # single_value=True: two separate mentions resolving to distinct values
    # raise MultipleMentionsError (engine _enforce_single_value_invariant;
    # shipped precedent tests/integration/test_single_value_invariant.py).
    # Resolution.AMBIGUOUS is NOT produced here — it is reserved for
    # one-cluster multi-value reads (e.g. cross-grammar agreement).
    _register_iban()
    contract = IBANCapability.create_contract()
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize(
            "DE89 3704 0044 0532 0130 00 / GB29 NWBK 6016 1331 9268 19", contract
        )


def test_span_word_guard():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert (
        paxman.canonicalize("XDE89370400440532013000", contract).status
        == Resolution.MISSING
    )


def test_longest_vectors():
    _register_iban()
    contract = IBANCapability.create_contract()
    for compact in [
        "LC55HEMM000100010012001200023015",
        "NI92BAMC000000000000000003123123",
    ]:
        r = paxman.canonicalize(compact, contract)
        assert r.status == Resolution.SUCCESS, compact


def test_year_filter_excludes_rule():
    # year=2019 filters out the 2020 rule (orchestrator _filter_rules), so the
    # input is recognized but nothing validates it -> deterministic INVALID
    # (_determine_status: recognitions true, zero candidates). Not MISSING —
    # recognition did happen.
    _register_iban()
    contract = IBANCapability.create_contract(year=2019)
    r = paxman.canonicalize("DE89370400440532013000", contract)
    assert r.status == Resolution.INVALID
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_iban_capability.py -v` → PASS once Tasks 1-5 are correct (registration is per-test inside the fixture window, so no cross-file registry state matters — the suite is order-independent by construction).

- [ ] **Step 3: No engine glue expected — verify span invariants only**

No code change expected. The engine already enforces recognition span invariants (`orchestrator._recognize`), single-value semantics (two distinct mentions → `MultipleMentionsError`, which `test_two_distinct_ibans_raise_multiple_mentions` pins), and determinism (same input + contract + snapshot → same `VersionStamp`). If a test fails here, it is a Task 1-5 defect, not an engine one — do not modify `paxman/engine/`. Sanity-reference `tests/integration/test_single_value_invariant.py` and `tests/integration/test_issn_capability.py` (the shipped ISSN resolution-map pattern this file mirrors).

- [ ] **Step 4: Run to pass + coverage gates**

```bash
uv run pytest tests/capabilities/iban/ tests/integration/test_iban_capability.py -v
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/capabilities/IBAN/*" --fail-under=95
```

Expected: coverage `≥95%` on new package (if below, add missing branch: `DD` range, `mod97` edge).

- [ ] **Step 5: Property test (optional hypothesis)**

```python
# tests/property/test_iban_properties.py
from hypothesis import given, strategies as st

from paxman.capabilities.IBAN.contract import IBANContract
from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.capabilities.IBAN.rules.iso_13616_1_ed2020 import Section4IBANStructureMOD97


def calc_check(country: str, bban: str) -> str:
    """ISO/IEC 7064 MOD 97-10 generation: 98 - (mod97 of bban+cc+\"00\")."""
    rearr = bban + country + "00"
    exp = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearr)
    r = 0
    for ch in exp:
        r = (r * 10 + int(ch)) % 97
    return f"{98 - r:02d}"


@given(
    st.text(min_size=15, max_size=34, alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
)
def test_random_strings_usually_invalid(s: str) -> None:
    rule = Section4IBANStructureMOD97()
    n = IBANNotation(country_code=s[:2], check_digits=s[2:4], bban=s[4:], compact=s)
    # Smoke: matches() never raises on any 15-34 alnum string. The status
    # split is statistically dominated by INVALID — mod97 is ~uniform over
    # the 97 residues, so only ~1/97 random strings pass.
    assert rule.matches(n, IBANContract()) in (True, False)


def test_generated_valid_is_valid() -> None:
    bban = "370400440532013000"
    cc = "DE"
    dd = calc_check(cc, bban)
    compact = cc + dd + bban
    assert Section4IBANStructureMOD97().matches(
        IBANNotation(country_code=cc, check_digits=dd, bban=bban, compact=compact),
        IBANContract(),
    )
```

(No `pytestmark` here — property tests carry the layer marker in this repo only where shipped files do; the `-m` gate in Task 8 does not select property tests, mirroring shipped convention.)

Run: `uv run pytest tests/property/test_iban_properties.py -k iban -v`

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_iban_capability.py tests/property/test_iban_properties.py
git commit -m "test(iban): integration, resolution map, and property checks"
```

---

### Task 8: Final Verification and Cleanup

- [ ] **Step 1: Full gate**

Format first — the plan's snippets are semantically exact but not byte-formatted:

```bash
uv run ruff format paxman/ tests/
```

Then:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -m "unit or capability or integration or e2e" -q
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95
```

Expected: 0 errors, `95%` global. (Tasks 1-7 put layer markers on every IBAN test module, so this `-m` filter **executes** the IBAN suite — IBAN tests being skipped here is a Task 1-7 defect, not a filter artifact.)

- [ ] **Step 2: Remove any `# type: ignore` / `# noqa` in `paxman/`**

```bash
grep -rn "type: ignore\|noqa\|pyright: ignore" paxman/capabilities/IBAN/ || echo "clean"
```

Expected: `clean` (tests may use `# type: ignore[misc]` for frozen checks).

- [ ] **Step 3: Manual canonicalize smoke**

```bash
uv run python - << 'PY'
import paxman
from paxman.capabilities.IBAN.capability import IBANCapability
paxman.register_capability(IBANCapability())
for txt in ["DE89 3704 0044 0532 0130 00","GB29 NWBK 6016 1331 9268 19","LC55 HEMM 0001 0001 0012 0012 0002 3015","SC18 SSCB 1101 0000 0000 0000 1497 USD"]:
    c=IBANCapability.create_contract()
    print(txt, "->", paxman.canonicalize(txt,c).canonicalized_value, paxman.canonicalize(txt,c).status)
    print(" paper:", paxman.canonicalize(txt, IBANCapability.create_contract(output_format="paper")).canonicalized_value)
PY
```

- [ ] **Step 4: Push or hand off** — do not delete `docs/development/research/2026-08-22-iban-canonicalization.md`; it is already corrected to Release 100 with LC32/NI32, NO `4!n6!n1!n`, SC `1497`.

---

## Self-Review

- **Spec coverage:** Research §3 Notation → Task 1; §4 Grammar → Task 3; §5-7 Rules/Provenance/MOD97 → Task 4; §6 Contract/Capability seam → Tasks 2+5; §8-9 Edges/Resolution → Task 7; §11 File layout → all tasks; §13 Decisions (defer registry LOOKUP_TABLE) documented; Oracle P1/P2 corrections (Release 100, SC 1497, LC/NI 32, NO structure, word_only citation, quote reattribution, dates, JohnPeel mirror, MILESTONE line 27) captured in Tasks 1-7; Oracle round-2 corrections (label `[\s:-]+`, tail-absorption documented → `INVALID`, `MultipleMentionsError` not `AMBIGUOUS`, per-test registration inside the fixture window, exports-gate patch in the correct direction, layer markers on every test module, `iso_ed2020.py` rename in Task 4, `year` → deterministic `INVALID`, CONTEXT.md row shapes, `create_contract` final form without `# type: ignore`, no dead `_mod97` branch, no unused test imports) captured in the tasks above.
- **Placeholder scan:** No `TBD`/`TODO(scaffold)` remains — the scaffold placeholder rule file is renamed and overwritten in Task 4 Step 0 (the only other placeholder artifacts are the scaffold grammar/capability/test files, each replaced wholesale by the task that fills its domain); deferred registry is the only explicit YAGNI. All code blocks are complete — no "handle edge cases" instructions.
- **Gate honesty:** Every test module carries its layer marker (Tasks 1-7), so Task 8's `-m "unit or capability or integration or e2e"` gate actually executes the IBAN suite — it cannot pass while the IBAN tests are skipped. Every snippet is `ruff`/`pyright`-clean as written (imports included; no unused `import re`/`random`).
- **Type consistency:** `IBANNotation(country_code, check_digits, bban, compact)` used identically across Tasks 1,3,4,5,7; `IBANContract` `electronic`/`paper` matches `format_value`; `PipelineGrammar[IBANNotation]`, `Rule[IBANNotation]` consistent; `create_contract` tuple-normalization matches shipped `ISBN`/`ISSN` idiom.

---

## Execution Handoff

Plan complete and saved to `docs/development/plans/2026-08-22-iban-capability.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

