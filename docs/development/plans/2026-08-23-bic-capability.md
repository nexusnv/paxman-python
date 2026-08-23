# BIC Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a new `BIC` capability that recognizes tolerant human BIC surfaces (case, grouping, optional `BIC`/`SWIFT` label), validates strictly via ISO 9362:2022 Section 5 BIC structure 8 or 11 plus charset `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` plus country in ISO 3166-1 alpha-2 plus `XK` (Kosovo user-assigned), canonicalizes to compact uppercase 8 or 11 with branch preserved and grouped `AAAA BB CC [XXX]` plus `bic11` presentation, no directory lookup in v1, provenance first, deterministic.

**Architecture:** Single `PipelineGrammar` (`RegexStage` + `StandardPre(empty_guard=True)` + `BoundaryGuard.word_only` both sides) emitting `BICNotation(bank_code, country_code, location_code, branch_code, compact)` where `compact` is `bank_code+country_code+location_code+branch_code` and equals the uppercased alphanum collapse of the match; label fused with `[\s:-]+` one or more separator (ISBN-13 precedent prevents `BICDEUTDEFF` gluing, see `paxman/capabilities/ISBN/grammar/isbn13_recognition.py` and Research section 4.2), `word_only` guards block left and right glue and prevent carving a valid 8 char run out of a longer alnum token; one mandatory `PARSER` rule `Section5BICStructureCountry` (generic length and charset plus country lookup, Research section 7, no checksum, location second char `0`/`1`/`2` informative only, `XXX` preserved) with `target_semantics={"bic_recognition"}`; `BICCapability.format_value` renders `bic` identity vs `grouped` vs `bic11`; `BICContract` with `DEFAULT_OUTPUT_FORMAT="bic"` and `OFFERED_OUTPUT_FORMATS=frozenset({"grouped", "bic11"})` justified as non lossy `grouped` and explicitly documented lossy `bic11` expansion appending `XXX` when branch absent (Research section 6.1, decision 1). No `include_directory_validation` in v1, directory `LOOKUP_TABLE` deferred behind gated feature like ISBN `include_range_validation` and ISSN deferred Register.

**Tech Stack:** Python 3.11+, `uv`, `hatchling`, `ruff`, `pyright` strict, `import-linter`, `pytest` 95% coverage gates, `hypothesis` property tests.

---

## File Structure

```
paxman/capabilities/BIC/
├── __init__.py              # re-exports; registers package (scaffolder edits paxman/capabilities/__init__.py)
├── notation.py              # BICNotation — frozen+slots, 5 str fields
├── contract.py              # BICContract(CapabilityContract) — bic default, grouped and bic11 offered
├── capability.py            # BICCapability — get_grammars/get_rules/create_contract/format_value
├── grammar/
│   ├── __init__.py
│   └── bic_recognition.py   # PipelineGrammar[BICNotation] single grammar
└── rules/
    ├── __init__.py
    └── iso_9362_ed2022.py   # PUBLICATION + Section5BICStructureCountry (PARSER, fused structure plus country)

tests/capabilities/bic/
├── __init__.py
├── test_notation.py
├── test_contract.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py
tests/integration/test_bic_capability.py  # MISSING/INVALID/SUCCESS + MultipleMentionsError, segmentation, year filter
tests/property/test_bic_properties.py     # hypothesis: valid generation, country gating, grouped round trip
```

**Created vs Modified:**
- **Create:** All `paxman/capabilities/BIC/*` files (via `tools/new_capability.py` then domain fill, the scaffold `rules/iso_ed2022.py` placeholder is renamed to `iso_9362_ed2022.py` in Task 4 Step 0)
- **Modify:** `paxman/capabilities/__init__.py` (alphabetical export, scaffolder does it), `tests/unit/test_capability_exports.py` (add `BIC` import plus `TestBICCapabilityExports` plus expected set entry, Task 6 Step 1, it fails once the export exists so it needs this patch), `CONTEXT.md` (notation bullet plus 3 column table row plus count wording), `docs/development/MILESTONE.md` line for BIC row
- **Test:** `tests/capabilities/bic/*` (marked `capability`), `tests/integration/test_bic_capability.py` (marked `integration`, per test registration), `tests/property/test_bic_properties.py`, `tests/unit/test_capability_surface.py` (auto wired by scaffolder)
- **Not touched in v1:** `paxman/api/bootstrap.py` `_SHIPPED` is deliberately NOT touched for BIC v1 like ISSN and IBAN precedent (shipped but not bootstrapped, Task 7 registers directly), `rules/data/` plus `swift_bic_directory_ed2025.py` intentionally deferred, plan documents refresh procedure but does not implement, `paxman/capabilities/BIC/rules/data/` deferred

---

### Task 0: Scaffold and Baseline

**Files:**
- Create: `paxman/capabilities/BIC/*` (via scaffolder)
- Modify: `paxman/capabilities/__init__.py` (auto edited)
- Test: `tests/capabilities/bic/*` stubs (auto generated)

- [ ] **Step 1: Run scaffolder**

```bash
uv run python tools/new_capability.py BIC --name bic --authority "ISO" --spec-name "ISO 9362:2022" --spec-url "https://www.iso.org/standard/84108.html" --publication-year 2022 --default-format bic
```

Expected: prints `Generated capability skeleton:` followed by 13 file paths (9 package files plus 4 test stubs) and `paxman/capabilities/__init__.py (wired)`. Verify `ls paxman/capabilities/BIC/` lists `notation.py contract.py capability.py grammar/ rules/`.

Two scaffolder byproducts to know about:
- It also wires `tests/unit/test_capability_surface.py` (`_wire_surface_guard` adds the `_CAPABILITY_SURFACES` entry), no manual edit needed there.
- It derives the rule file name from `--authority "ISO"` to `rules/iso_ed2022.py` with placeholder class `BICRule` (`Section 1-overview`, `TODO(scaffold)` markers). Task 4 Step 0 renames it to `iso_9362_ed2022.py`, do not leave the placeholder behind.
- It does **not** patch `tests/unit/test_capability_exports.py`, once BIC is in `__all__` that gate fails by design, Task 6 Step 1 patches it.

- [ ] **Step 2: Run baseline lint and type on scaffold**

```bash
uv run ruff check paxman/capabilities/BIC/ --fix
uv run pyright paxman/capabilities/BIC/
uv run pytest tests/capabilities/bic/ -v
```

Expected: `ruff` clean or auto fix, `pyright` 0 errors (stub passes), pytest stubs pass (scaffold placeholder `test_notation.py` checks `value`).

- [ ] **Step 3: Commit scaffold**

```bash
git add paxman/capabilities/BIC/ paxman/capabilities/__init__.py tests/capabilities/bic/
git commit -m "feat(bic): scaffold BIC capability via tools/new_capability.py"
```

---

### Task 1: Notation — BICNotation

**Files:**
- Modify: `paxman/capabilities/BIC/notation.py`
- Test: `tests/capabilities/bic/test_notation.py`

Research section 3.1: `bank_code` 4 char `A-Z0-9`, `country_code` 2 `A-Z`, `location_code` 2 `A-Z0-9`, `branch_code` 0 or 3 `A-Z0-9` or empty when BIC8, `compact` 8 or 11 equals `bank_code+country_code+location_code+branch_code`. Frozen plus slots, all `str`. No validation in `__post_init__` beyond type shape, grammar owns stripping and uppercasing, rules own country membership. Mirrors `paxman/capabilities/IBAN/notation.py` 4 field split and `paxman/core/domain.py` frozen slots precedent.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/bic/test_notation.py
import pytest
from dataclasses import FrozenInstanceError

from paxman.capabilities.BIC.notation import BICNotation

pytestmark = [pytest.mark.capability]


def test_frozen_slots_hash():
    n = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="",
        compact="DEUTDEFF",
    )
    assert n.bank_code == "DEUT"
    assert n.country_code == "DE"
    assert n.location_code == "FF"
    assert n.branch_code == ""
    assert n.compact == "DEUTDEFF"
    assert hash(n) is not None
    assert hasattr(n, "__slots__")
    with pytest.raises(FrozenInstanceError):
        n.compact = "X"  # type: ignore[misc]


def test_compact_is_concatenation():
    n8 = BICNotation(
        bank_code="BNPA",
        country_code="FR",
        location_code="PP",
        branch_code="",
        compact="BNPAFRPP",
    )
    assert (
        n8.compact == n8.bank_code + n8.country_code + n8.location_code + n8.branch_code
    )
    assert len(n8.compact) == 8
    n11 = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="500",
        compact="DEUTDEFF500",
    )
    assert (
        n11.compact
        == n11.bank_code + n11.country_code + n11.location_code + n11.branch_code
    )
    assert len(n11.compact) == 11


def test_branch_empty_when_8():
    n = BICNotation(
        bank_code="CHAS",
        country_code="US",
        location_code="33",
        branch_code="",
        compact="CHASUS33",
    )
    assert n.branch_code == ""
    assert len(n.compact) == 8
    n2 = BICNotation(
        bank_code="BNPA",
        country_code="FR",
        location_code="PP",
        branch_code="XXX",
        compact="BNPAFRPPXXX",
    )
    assert n2.branch_code == "XXX"
    assert len(n2.compact) == 11
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/bic/test_notation.py -v`
Expected: FAIL, `BICNotation` still has `value: str` stub, missing fields `bank_code` etc, `test_compact_is_concatenation` fails on instantiation.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/BIC/notation.py
"""BIC notation — grammar-normalized compact form."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BICNotation:
    """BIC notation — compact plus structured decomposition.

    ``bank_code`` 4-char institution prefix, uppercased, A-Z0-9.
    ``country_code`` 2-letter ISO 3166-1 alpha-2 plus XK, uppercased, A-Z.
    ``location_code`` 2-char location suffix, uppercased, A-Z0-9.
    ``branch_code`` 3-char branch, uppercased, A-Z0-9, or empty string when BIC8.
    ``compact`` full BIC string 8 or 11, uppercased, equals bank+country+location+branch.
    The grammar never validates country membership or liveness, rules own that.
    """

    bank_code: str  # e.g. "DEUT" — length 4, A-Z0-9
    country_code: str  # e.g. "DE" — length 2, A-Z
    location_code: str  # e.g. "FF" — length 2, A-Z0-9
    branch_code: str  # e.g. "500", "XXX", "" — length 0 or 3, A-Z0-9
    compact: str  # e.g. "DEUTDEFF" or "DEUTDEFF500" — 8 or 11
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/bic/test_notation.py -v`
Expected: PASS (3 passed). Also `uv run pyright paxman/capabilities/BIC/notation.py` 0 errors, `uv run ruff check paxman/capabilities/BIC/notation.py`.

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/BIC/notation.py tests/capabilities/bic/test_notation.py
git commit -m "feat(bic): define BICNotation frozen+slots with 5 str fields"
```

---

### Task 2: Contract — BICContract

**Files:**
- Modify: `paxman/capabilities/BIC/contract.py`
- Test: `tests/capabilities/bic/test_contract.py`

Research section 6.1 and decision 1: `DEFAULT_OUTPUT_FORMAT="bic"` (compact no space uppercase, branch as matched, SWIFT compact is wire key), `OFFERED_OUTPUT_FORMATS=frozenset({"grouped", "bic11"})`. Choice `{"grouped", "bic11"}` over `{"grouped"}` alone is deliberate: `grouped` is non lossy reinsertion `AAAA BB CC [XXX]`, `bic11` is explicitly documented lossy expansion appending `XXX` when branch absent (Research section 6.1 table). Loss is acceptable because `BIC8` and `BIC8+XXX` are functionally head office equivalent for routing but lexicographically distinct, and callers that need head office blind dedup can normalize via `bic11` themselves. No `include_directory_validation` in v1 deferred. Inherits `CapabilityContract`, `capability_name="bic"`, `resolve_output_format` exercised via base `__post_init__`. Must be `@dataclass(frozen=True)` without `slots`, per `paxman/capabilities/ISSN/contract.py` and `paxman/capabilities/IBAN/contract.py` precedent and `paxman/core/capability_contract.py`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/bic/test_contract.py
import pytest
from dataclasses import FrozenInstanceError

from paxman.core.errors import ContractError
from paxman.capabilities.BIC.contract import BICContract

pytestmark = [pytest.mark.capability]


def test_default_output_format_resolves():
    c = BICContract()
    assert c.output_format == "bic"
    assert c.capability_name == "bic"
    assert BICContract.DEFAULT_OUTPUT_FORMAT == "bic"
    assert BICContract.OFFERED_OUTPUT_FORMATS == frozenset({"grouped", "bic11"})


def test_grouped_offered():
    c = BICContract(output_format="grouped")
    assert c.output_format == "grouped"


def test_bic11_offered():
    c = BICContract(output_format="bic11")
    assert c.output_format == "bic11"


def test_default_alias_via_none_and_default_string():
    for alias in (None, "default", "bic"):
        c = BICContract(output_format=alias)
        assert c.output_format == "bic"


def test_invalid_output_format_raises():
    with pytest.raises(ContractError):
        BICContract(output_format="hyphenated")  # ISSN ism, not BIC
    with pytest.raises(ContractError):
        BICContract(output_format="paper")  # IBAN ism, not BIC
    with pytest.raises(ContractError):
        BICContract(output_format="compact")  # not offered


def test_frozen_contract():
    c = BICContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "grouped"  # type: ignore[misc]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/bic/test_contract.py -v`
Expected: FAIL, scaffold baked `DEFAULT_OUTPUT_FORMAT="bic"` from `--default-format bic` and `capability_name="bic"` so `test_default_output_format_resolves` partially passes, but `OFFERED_OUTPUT_FORMATS` is empty `frozenset()` so `test_grouped_offered` and `test_bic11_offered` FAIL, `test_invalid_output_format_raises` may not raise for offered values.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/BIC/contract.py
"""BIC contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class BICContract(CapabilityContract):
    """User-facing contract for BIC capability.

    Default ``bic`` is compact uppercase 8 or 11, branch as matched.
    ``grouped`` renders ``AAAA BB CC [XXX]`` for readability.
    ``bic11`` always 11, appending ``XXX`` head office when branch absent,
    lossy expansion documented as such.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "bic"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"grouped", "bic11"})

    capability_name: str = field(default="bic", init=False)
    # No include_directory_validation in v1, deferred YAGNI
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/bic/test_contract.py -v` to PASS.
Run: `uv run pyright paxman/capabilities/BIC/contract.py` to 0 errors, `uv run ruff check paxman/capabilities/BIC/`.

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/BIC/contract.py tests/capabilities/bic/test_contract.py
git commit -m "feat(bic): define BICContract bic default with grouped and bic11 offered"
```

---

### Task 3: Grammar — bic_recognition

**Files:**
- Modify: `paxman/capabilities/BIC/grammar/bic_recognition.py`, `paxman/capabilities/BIC/grammar/__init__.py`
- Test: `tests/capabilities/bic/test_grammar.py`

Research section 4.2 and 4.3: Single `PipelineGrammar` with `StandardPre(empty_guard=True)`, `RegexStage` using `BoundaryGuard.word_only().lookbehind` plus `BoundaryGuard.word_only().lookahead`. Pattern module scope string, compiled by `RegexStage`, never inside `recognize()`. Fused label `(?:(?:BIC|SWIFT)[\s:-]+)?` with `[\s:-]+` one or more separator, never zero width, so `BICDEUTDEFF` does not glue. Body `(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)` is exactly 4 plus 2 plus 2 plus optional 3, only 8 or 11 total, never 9 or 10. ASCII restriction via `(?ai:...)` wrapper and `ch.isascii() and ch.isalnum()` filtering to reject non ASCII like `K` or unicode digits while `BoundaryGuard.word_only` stays unicode aware (mirrors `paxman/capabilities/IBAN/grammar/iban_recognition.py:25` `(?ai:` precedent, Research section 4.2 note). No global `flags=re.IGNORECASE` — the inline `(?ai:)` already provides ASCII+case-insensitive; a global flag would widen label matching to unicode case-fold. `notation_fn` via `isascii` plus `isalnum` plus `upper` plus split into fields. `single_value=True` per shipped precedent Research section 4.6. Shipped `paxman/capabilities/ISSN/grammar/issn_recognition.py` is `word_only` lookbehind precedent, `paxman/capabilities/IBAN/grammar/iban_recognition.py` is `word_only` both sides precedent.

**Pattern:**

```python
_BIC_BODY = r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?))"
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)
```

Design points verbatim in code comments:
- Label separator is `[\s:-]+` one or more, not `*`, a glued `BICDEUTDEFF` must not fuse into a mention, shipped ISBN-13 uses `[\s:-]+` for exactly this, ISSN `*` would absorb the label.
- `BoundaryGuard.word_only()` `(?<!\w)` and `(?!\w)`: lookbehind blocks preceding letter glue `XDEUTDEFF` to `MISSING`, trailing lookahead blocks longer alnum tail absorption beyond 11 and prevents carving valid 8 out of `DEUTDEFFY`. Within single grammar longer wins via engine `_dedup_spans` per grammar containment, cross grammar would be spurious `AMBIGUOUS` but single grammar avoids this (Research section 4.2 eight vs eleven discussion).
- Documented limitation: an 8 char BIC followed by exactly 3 alnum immediately glued `DEUTDEFF500X` where `500X` tail would be 12 total is not same as 11 char BIC, the 11 char optional branch consumes exactly 3, remaining single `X` is outside span and blocked by `(?!\w)` only if glued, the 11 char match wins. Longer wins per grammar. Cross grammar containment would be preserved not deduped per `paxman/engine/orchestrator.py:_dedup_spans`, hence single grammar choice avoids spurious `AMBIGUOUS`.

`notation_fn` via `isascii` plus `isalnum` plus `upper` split into `bank_code`, `country_code`, `location_code`, `branch_code`, `compact`. Use `StandardPre` plus `RegexStage` because that is staged pipeline ISBN actually ships, `HOW_TO_ADD_NEW_GRAMMAR.md` bare `Grammar` recipe is minimal teaching form, shipped grammars use `PipelineGrammar`.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/bic/test_grammar.py
import pytest

from paxman.capabilities.BIC.grammar.bic_recognition import BICRecognitionGrammar

pytestmark = [pytest.mark.capability]

GRAMMAR = BICRecognitionGrammar()


def test_valid_electronic():
    for compact in ["DEUTDEFF", "BNPAFRPP", "CHASUS33", "BARCGB22", "NEDSZAJJ"]:
        m = GRAMMAR.recognize(compact)
        assert len(m) == 1, compact
        n = m[0].notation
        assert n.compact == compact
        assert n.bank_code == compact[0:4]
        assert n.country_code == compact[4:6]
        assert n.location_code == compact[6:8]
        assert n.branch_code == ""
        assert m[0].raw_text == compact
        assert m[0].end - m[0].start == len(m[0].raw_text)
    for compact in [
        "DEUTDEFF500",
        "BNPAFRPPXXX",
        "SOGEFRPPBRE",
        "DSBACNBXSHA",
        "NEDSZAJJXXX",
    ]:
        m = GRAMMAR.recognize(compact)
        assert len(m) == 1, compact
        assert m[0].notation.compact == compact
        assert m[0].notation.branch_code == compact[8:11]
        assert len(m[0].notation.compact) == 11


def test_case_insensitive_and_label():
    for txt, expected in [
        ("deutdeff", "DEUTDEFF"),
        ("DeUtDeFf500", "DEUTDEFF500"),
        ("BIC: DEUTDEFF", "DEUTDEFF"),
        ("SWIFT: BNPAFRPPXXX", "BNPAFRPPXXX"),
        ("BIC DEUTDEFF500", "DEUTDEFF500"),
        ("bic - NEDSZAJJ", "NEDSZAJJ"),
        ("swift-code: CHASUS33", "CHASUS33"),
        ("SWIFT  DSBACNBXSHA", "DSBACNBXSHA"),
    ]:
        m = GRAMMAR.recognize(txt)
        assert len(m) == 1, txt
        assert m[0].notation.compact == expected, txt


def test_word_guard_blocks_left_and_label_glue():
    # Left glue: (?<!\w) lookbehind rejects carving out of longer token
    assert GRAMMAR.recognize("XDEUTDEFF") == []
    assert GRAMMAR.recognize("ADEUTDEFF500B") == []
    assert GRAMMAR.recognize("DEUTDEFFY") == []
    # Glued label: separator is [\s:-]+ never zero width
    assert GRAMMAR.recognize("BICDEUTDEFF") == []
    assert GRAMMAR.recognize("SWIFTDEUTDEFF500") == []
    assert GRAMMAR.recognize("BICDEUTDEFF500") == []


def test_length_bounds():
    # Only 8 or 11 valid, 7/9/10/12 must not be recognized as BIC
    assert GRAMMAR.recognize("DEUTDEF") == []  # 7
    assert GRAMMAR.recognize("DEUTDEFF5") == []  # 9
    assert GRAMMAR.recognize("DEUTDEFF50") == []  # 10
    assert GRAMMAR.recognize("DEUTDEFF5000") == []  # 12
    # valid 8 and 11 are accepted
    assert len(GRAMMAR.recognize("DEUTDEFF")) == 1
    assert len(GRAMMAR.recognize("DEUTDEFF500")) == 1
    # 7 plus valid 8 needs word guard: XDEUTDEF is not valid anyway
    assert GRAMMAR.recognize("DEUTDEFF50000") == []  # 13 alnum glued, no word break


def test_multiple_matches():
    txt = "DEUTDEFF / BNPAFRPPXXX"
    m = GRAMMAR.recognize(txt)
    assert len(m) == 2
    assert m[0].notation.compact == "DEUTDEFF"
    assert m[1].notation.compact == "BNPAFRPPXXX"
    txt2 = "BICs: DEUTDEFF500, CHASUS33"
    assert len(GRAMMAR.recognize(txt2)) == 2


def test_semantics_and_name():
    assert GRAMMAR.name == "bic_recognition"
    assert GRAMMAR.semantics == "bic_recognition"
    assert GRAMMAR.single_value is True


def test_span_invariants():
    txt = "Please remit to BIC DEUTDEFF (Deutsche Bank)"
    m = GRAMMAR.recognize(txt)
    assert len(m) == 1
    assert txt[m[0].start : m[0].end] == m[0].raw_text
    assert 0 <= m[0].start < m[0].end <= len(txt)
    # raw_text includes label when present
    assert m[0].raw_text == "BIC DEUTDEFF"
    assert m[0].notation.compact == "DEUTDEFF"
    # bare without label
    m2 = GRAMMAR.recognize("Pay to DEUTDEFF now")[0]
    assert m2.raw_text == "DEUTDEFF"


def test_empty_and_quoted():
    assert GRAMMAR.recognize("") == []
    m = GRAMMAR.recognize('"DEUTDEFF"')
    assert len(m) == 1 and m[0].notation.compact == "DEUTDEFF"
    m2 = GRAMMAR.recognize("[BNPAFRPPXXX]")
    assert len(m2) == 1 and m2[0].notation.compact == "BNPAFRPPXXX"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/bic/test_grammar.py -v`
Expected: FAIL, scaffold grammar still matches `value` placeholder, `test_word_guard_blocks_left_and_label_glue` and `test_length_bounds` fail.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/BIC/grammar/bic_recognition.py
"""BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""

from __future__ import annotations

import re

from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one or more, never zero width: a glued
# "BICDEUTDEFF" must not fuse into a mention (ISBN-13 precedent).
# Body is 4!c + 2!a + 2!c + optional 3!c = 8 or 11 only, never 9 or 10.
# (?ai:) ASCII restriction plus isascii filter rejects non ASCII like K.
_BIC_BODY = r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?))"
# word_only guards block left glue XDEUTDEFF and right glue DEUTDEFFY
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)


def _bic_notation(match: re.Match[str]) -> BICNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    bank_code = compact[0:4]
    country_code = compact[4:6]
    location_code = compact[6:8]
    branch_code = compact[8:11] if len(compact) == 11 else ""
    return BICNotation(
        bank_code=bank_code,
        country_code=country_code,
        location_code=location_code,
        branch_code=branch_code,
        compact=compact,
    )


class BICRecognitionGrammar(PipelineGrammar[BICNotation]):
    """BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""

    name = "bic_recognition"
    semantics = "bic_recognition"
    single_value = True
    pre = StandardPre[BICNotation](empty_guard=True)
    regex = RegexStage[BICNotation](pattern=_BIC_PATTERN, notation_fn=_bic_notation)
```

Expose in `grammar/__init__.py`:

```python
"""BIC recognition grammars."""

from paxman.capabilities.BIC.grammar.bic_recognition import BICRecognitionGrammar

__all__ = ["BICRecognitionGrammar"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/bic/test_grammar.py -v` to 8 passed.
Run: `uv run pyright paxman/capabilities/BIC/grammar/bic_recognition.py` to 0 errors.
Run: `uv run ruff check paxman/capabilities/BIC/grammar/`

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/BIC/grammar/bic_recognition.py paxman/capabilities/BIC/grammar/__init__.py tests/capabilities/bic/test_grammar.py
git commit -m "feat(bic): implement bic_recognition PipelineGrammar with word_only guards"
```

---

### Task 4: Rules — ISO 9362:2022

**Files:**
- Modify: `paxman/capabilities/BIC/rules/iso_9362_ed2022.py`, `paxman/capabilities/BIC/rules/__init__.py`
- Test: `tests/capabilities/bic/test_rules.py`

Research section 5 and 7: One `PUBLICATION` (`authority="ISO"`, `specification_name="ISO 9362:2022"`, `kind="specification"`, `reference_url="https://www.iso.org/standard/84108.html"`, `version="2022"`, `lifecycle="active"`, `publication_year=2022`, `citation` Section 5 BIC structure). One `PARSER` rule `Section5BICStructureCountry` (`name="Section 5-bic-structure-country"`, `strategy=PARSER`, `target_semantics={"bic_recognition"}`, `requires_features=frozenset()`). Validates length in `{8,11}`, charset `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$` after upper, country_code in ISO 3166-1 plus `XK` via frozenset, location second char `0`/`1`/`2` informative only not rejected, branch `XXX` preserved, `normalize` returns compact. Never reads `output_format` (CI source scan enforced, `tests/unit/test_rule_output_format_purity.py`). Country set reuse note: either embed frozenset of 249 codes plus `XK` inline or document reuse of Country table snapshot, but do not import cross capability at runtime (import linter), so copy the set. No checksum, no mod97.

- [ ] **Step 0: Rename the scaffold placeholder rule file**

The scaffolder created `rules/iso_ed2022.py` (name derived from `--authority "ISO"`) with placeholder class `BICRule` `Section 1-overview` `TODO(scaffold)`. Rename it to per publication convention before filling, leaving placeholder behind would trip Task 8 placeholder scan:

```bash
git mv paxman/capabilities/BIC/rules/iso_ed2022.py paxman/capabilities/BIC/rules/iso_9362_ed2022.py
```

`rules/__init__.py` stays scaffold docstring only stub, Step 3 replaces it with module exposure.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/bic/test_rules.py
import pytest

from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.BIC.notation import BICNotation
from paxman.capabilities.BIC.rules.iso_9362_ed2022 import (
    PUBLICATION,
    Section5BICStructureCountry,
)

pytestmark = [pytest.mark.capability]

RULE = Section5BICStructureCountry()
CONTRACT = BICContract()


def n(compact: str) -> BICNotation:
    c = compact.upper()
    return BICNotation(
        bank_code=c[0:4],
        country_code=c[4:6],
        location_code=c[6:8],
        branch_code=c[8:11] if len(c) == 11 else "",
        compact=c,
    )


def test_provenance_metadata():
    assert PUBLICATION.authority == "ISO"
    assert PUBLICATION.specification_name == "ISO 9362:2022"
    assert PUBLICATION.reference_url == "https://www.iso.org/standard/84108.html"
    assert PUBLICATION.lifecycle == "active"
    assert PUBLICATION.publication_year == 2022
    assert PUBLICATION.kind == "specification"
    assert PUBLICATION.version == "2022"
    assert RULE.name == "Section 5-bic-structure-country"
    assert RULE.strategy.name == "PARSER"
    assert RULE.target_semantics == frozenset({"bic_recognition"})
    assert RULE.requires_features == frozenset()
    assert "Section 5" in RULE.citation


def test_valid_vectors():
    for compact in [
        "DEUTDEFF",  # DE 8
        "DEUTDEFF500",  # DE 11 branch numeric
        "BNPAFRPP",  # FR 8
        "BNPAFRPPXXX",  # FR 11 head office
        "CHASUS33",  # US 8
        "BARCGB22",  # GB 8
        "NEDSZAJJ",  # ZA 8
        "NEDSZAJJXXX",  # ZA 11
        "SOGEFRPPBRE",  # FR 11 branch BRE
        "DSBACNBXSHA",  # CN 11
        "BANKXK22",  # XK Kosovo user assigned, Research section 8 edge 18
        "CBKIXKPRXXX",  # XK 11
    ]:
        assert RULE.matches(n(compact), CONTRACT) is True, compact
        assert RULE.normalize(n(compact), CONTRACT) == compact


def test_invalid_country_and_charset():
    # invalid country XX, QQ, ZZ not in ISO 3166-1 plus XK
    for bad in ["DEUTXXFF", "BNPAQQPP", "CHASZZ33", "DEUTQQFF"]:
        assert RULE.matches(n(bad), CONTRACT) is False, bad
    # digit in country position fails charset (2!a must be A-Z)
    assert RULE.matches(n("DEUT1EFF"), CONTRACT) is False
    assert RULE.matches(n("DEUT12FF"), CONTRACT) is False
    # lowercase compact fails isupper check (grammar uppercases, but rule defends)
    assert (
        RULE.matches(
            BICNotation(
                bank_code="deut",
                country_code="de",
                location_code="ff",
                branch_code="",
                compact="deutdeff",
            ),
            CONTRACT,
        )
        is False
    )
    # wrong length 7/9/10/12
    assert (
        RULE.matches(
            BICNotation(
                bank_code="DEUT",
                country_code="DE",
                location_code="F",
                branch_code="",
                compact="DEUTDEF",
            ),
            CONTRACT,
        )
        is False
    )
    assert RULE.matches(n("DEUTDEFF5"), CONTRACT) is False
    assert RULE.matches(n("DEUTDEFF50"), CONTRACT) is False
    assert RULE.matches(n("DEUTDEFF5000"), CONTRACT) is False


def test_location_second_char_not_rejected():
    # 0 test, 1 passive, 2 reverse billing, informative only, must not reject
    for compact in ["DEUTDE0F", "BARCGB1L", "CHASGB2L", "DEUTDEFF", "BARCGB22"]:
        assert RULE.matches(n(compact), CONTRACT) is True, compact


def test_branch_xxx_preserved():
    assert RULE.matches(n("NEDSZAJJXXX"), CONTRACT) is True
    assert RULE.normalize(n("NEDSZAJJXXX"), CONTRACT) == "NEDSZAJJXXX"
    assert RULE.matches(n("NEDSZAJJ"), CONTRACT) is True
    assert RULE.normalize(n("NEDSZAJJ"), CONTRACT) == "NEDSZAJJ"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/bic/test_rules.py -v`
Expected: FAIL, `Section5BICStructureCountry` not implemented, country valid vectors `BANKXK22` reveal off by one set missing `XK`.

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/BIC/rules/iso_9362_ed2022.py
"""ISO 9362:2022 Section 5 — BIC structure plus country lookup."""

from __future__ import annotations

import re

from paxman.capabilities.BIC.notation import BICNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 9362:2022",
    kind="specification",
    reference_url="https://www.iso.org/standard/84108.html",
    version="2022",
    lifecycle="active",
    publication_year=2022,
)

# ISO 3166-1 alpha-2 plus XK (Kosovo user assigned, Research section 5.4, validator.js issue 2045)
# Snapshot point in time, 249 ISO assigned plus XK. Keep as frozenset for O(1) lookup.
# Source: https://www.iso.org/iso-3166-country-codes.html plus RA landing
# https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html
# This set mirrors python-stdnum bic.py _country_codes including XK and AQ.
COUNTRY_CODES: frozenset[str] = frozenset(
    {
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "XK",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
    }
)

_BIC_RE = re.compile(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$")


class Section5BICStructureCountry(Rule[BICNotation]):
    """ISO 9362:2022 Section 5 — BIC structure plus country lookup.

    Validates length 8 or 11, charset per position, and country_code in
    ISO 3166-1 plus XK. Location second char 0/1/2 informative only.
    Branch XXX preserved, not coalesced. No checksum.
    """

    name = "Section 5-bic-structure-country"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 5 (BIC structure, branch optional, country ISO 3166-1 plus XK)"
    target_semantics = frozenset({"bic_recognition"})
    requires_features = frozenset()

    def matches(self, notation: BICNotation, contract: Contract) -> bool:
        c = notation.compact
        if len(c) not in (8, 11):
            return False
        if not c.isupper():
            return False
        if _BIC_RE.match(c) is None:
            return False
        if notation.country_code not in COUNTRY_CODES:
            return False
        # Defensive field agreement, compact must equal concatenation
        if (
            c
            != notation.bank_code
            + notation.country_code
            + notation.location_code
            + notation.branch_code
        ):
            return False
        return True

    def normalize(self, notation: BICNotation, contract: Contract) -> str:
        return notation.compact
```

Expose in `rules/__init__.py`:

```python
"""BIC validation rules."""

from paxman.capabilities.BIC.rules.iso_9362_ed2022 import Section5BICStructureCountry

__all__ = ["Section5BICStructureCountry"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/bic/test_rules.py -v` to PASS (5).
Run: `uv run pyright paxman/capabilities/BIC/rules/iso_9362_ed2022.py` to 0 errors.
Run: `grep -r output_format paxman/capabilities/BIC/rules/ || echo "clean"` to clean (no `output_format` token, CI purity gate `tests/unit/test_rule_output_format_purity.py` enforced).
Run: `uv run ruff check paxman/capabilities/BIC/rules/`

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/BIC/rules/iso_9362_ed2022.py paxman/capabilities/BIC/rules/__init__.py tests/capabilities/bic/test_rules.py
git commit -m "feat(bic): add Section 5-bic-structure-country PARSER with ISO 3166-1 plus XK"
```

---

### Task 5: Capability — wiring, create_contract, format_value

**Files:**
- Modify: `paxman/capabilities/BIC/capability.py`
- Test: `tests/capabilities/bic/test_capability.py`

Research section 6.2: `name="bic"`, `version="1.0.0"`, `get_grammars` returns 1, `get_rules` returns 1, `create_contract` tuple normalizes `excluded_rules` `pinned_rules` `extra_grammars` via `tuple(...) if ... else ()` shipped idiom (see `paxman/capabilities/IBAN/capability.py` and `paxman/capabilities/ISSN/capability.py`), `format_value` `bic` identity, `grouped` inserts spaces `AAAA BB CC [XXX]`, `bic11` appends `XXX` when len 8 else identity.

- [ ] **Step 1: Write the failing test**

```python
# tests/capabilities/bic/test_capability.py
import pytest

from paxman.capabilities.BIC.capability import BICCapability
from paxman.capabilities.BIC.notation import BICNotation

pytestmark = [pytest.mark.capability]

CAP = BICCapability()


def test_wiring_counts():
    assert CAP.name == "bic"
    assert CAP.version == "1.0.0"
    assert len(CAP.get_grammars()) == 1
    assert CAP.get_grammars()[0].name == "bic_recognition"
    assert len(CAP.get_rules()) == 1
    assert CAP.get_rules()[0].name == "Section 5-bic-structure-country"


def test_create_contract_defaults():
    c = CAP.create_contract()
    assert c.output_format == "bic"
    assert c.capability_name == "bic"
    assert c.excluded_rules == ()
    assert c.pinned_rules is None


def test_format_value_grouped():
    cases = {
        "DEUTDEFF": "DEUT DE FF",
        "DEUTDEFF500": "DEUT DE FF 500",
        "BNPAFRPP": "BNPA FR PP",
        "BNPAFRPPXXX": "BNPA FR PP XXX",
        "CHASUS33": "CHAS US 33",
        "NEDSZAJJXXX": "NEDS ZA JJ XXX",
    }
    for bic, grouped in cases.items():
        n = BICNotation(
            bank_code=bic[0:4],
            country_code=bic[4:6],
            location_code=bic[6:8],
            branch_code=bic[8:11] if len(bic) == 11 else "",
            compact=bic,
        )
        assert CAP.format_value(bic, "grouped", n) == grouped
        assert CAP.format_value(bic, None, n) == bic
        assert CAP.format_value(bic, "bic", n) == bic


def test_format_value_bic11():
    # Always 11, append XXX when branch absent, lossy expansion documented
    for bic8, bic11 in [
        ("DEUTDEFF", "DEUTDEFFXXX"),
        ("BNPAFRPP", "BNPAFRPPXXX"),
        ("NEDSZAJJ", "NEDSZAJJXXX"),
    ]:
        n = BICNotation(
            bank_code=bic8[0:4],
            country_code=bic8[4:6],
            location_code=bic8[6:8],
            branch_code="",
            compact=bic8,
        )
        assert CAP.format_value(bic8, "bic11", n) == bic11
    # Already 11 stays identity (notation must match value)
    n2 = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="500",
        compact="DEUTDEFF500",
    )
    assert CAP.format_value("DEUTDEFF500", "bic11", n2) == "DEUTDEFF500"
    n3 = BICNotation(
        bank_code="BNPA",
        country_code="FR",
        location_code="PP",
        branch_code="XXX",
        compact="BNPAFRPPXXX",
    )
    assert CAP.format_value("BNPAFRPPXXX", "bic11", n3) == "BNPAFRPPXXX"


def test_format_value_identity():
    n = BICNotation(
        bank_code="DEUT",
        country_code="DE",
        location_code="FF",
        branch_code="",
        compact="DEUTDEFF",
    )
    assert CAP.format_value("DEUTDEFF", "bic", n) == "DEUTDEFF"
    assert CAP.format_value("DEUTDEFF", None, n) == "DEUTDEFF"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/bic/test_capability.py -v` to FAIL (stub capability, version or format missing).

- [ ] **Step 3: Write minimal implementation**

```python
# paxman/capabilities/BIC/capability.py
"""BIC capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.BIC.grammar.bic_recognition import BICRecognitionGrammar
from paxman.capabilities.BIC.notation import BICNotation
from paxman.capabilities.BIC.rules.iso_9362_ed2022 import Section5BICStructureCountry
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["BICCapability", "BICContract", "BICNotation"]


class BICCapability(Capability[BICNotation]):
    """BIC canonicalization — compact with grouped and bic11 presentation."""

    name = "bic"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[BICNotation]]:
        return [BICRecognitionGrammar()]

    def get_rules(self) -> list[Rule[BICNotation]]:
        return [Section5BICStructureCountry()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> BICContract:
        """Factory method for creating contracts with proper defaults."""
        return BICContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    def format_value(
        self, value: str, output_format: str | None, notation: BICNotation
    ) -> str:
        if output_format == "grouped":
            if len(value) == 11:
                return f"{value[0:4]} {value[4:6]} {value[6:8]} {value[8:11]}"
            return f"{value[0:4]} {value[4:6]} {value[6:8]}"
        if output_format == "bic11":
            if len(value) == 8:
                return value + "XXX"
            return value
        return value
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/bic/test_capability.py -v` to PASS (4).
Run: `uv run pyright paxman/capabilities/BIC/capability.py` to 0 errors (no `# type: ignore` anywhere in `paxman/` source per anti pattern, Task 8 grep must print `clean`).

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/BIC/capability.py tests/capabilities/bic/test_capability.py
git commit -m "feat(bic): wire BICCapability with bic/grouped/bic11 seam"
```

---

### Task 6: Exports, Surface Homogeneity, and Docs

**Files:**
- Modify: `paxman/capabilities/__init__.py` (verify), `tests/unit/test_capability_exports.py`, `CONTEXT.md`, `docs/development/MILESTONE.md`
- Test: `tests/unit/test_capability_exports.py`, `tests/unit/test_capability_surface.py` (existing gates)

Scaffolder already edited `paxman/capabilities/__init__.py` alphabetically (`__all__` plus `_LAZY` plus `TYPE_CHECKING`) and wired `tests/unit/test_capability_surface.py`. `tests/unit/test_capability_exports.py` is NOT patched by scaffolder and now FAILS by design, task Step 1 fixes it. Update `CONTEXT.md` notation bullet plus 3 column table row plus count wording and MILESTONE BIC row. Like ISSN and IBAN `paxman/api/bootstrap.py` `_SHIPPED` is intentionally NOT modified, `register_all_shipped()` keeps its twelve name tuple, Task 7 integration registers BIC per test.

- [ ] **Step 1: Patch the exports completeness gate**

```bash
uv run pytest tests/unit/test_capability_exports.py -v
```

Expected: FAIL, `test_export_list_contains` now sees 13 names in `__all__` vs expected 12. Patch the test file:

```python
# tests/unit/test_capability_exports.py — add BIC to import block:
from paxman.capabilities import (
    BIC,
    Country,
    Currency,
    Date,
    Email,
    IBAN,
    IP,
    ISBN,
    ISSN,
    Money,
    Phone,
    SIUnit,
    URL,
)


# Add class mirroring TestISBNCapabilityExports and TestIBANCapabilityExports:
class TestBICCapabilityExports:
    @pytest.mark.unit
    def test_bic_capability_importable(self) -> None:
        """BIC capability is importable from paxman.capabilities."""
        assert BIC is not None

    @pytest.mark.unit
    def test_bic_capability_name(self) -> None:
        """BIC capability has correct name."""
        assert BIC.name == "bic"


# In test_export_list_contains expected set, add "BIC" (alphabetically first — letter B). Use set comparison so file order does not matter:
assert set(capabilities.__all__) == {
    "BIC",
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
# File order: keep `paxman/capabilities/__init__.py` `__all__` alphabetically sorted (BIC first). Scaffolder inserts alphabetically — do not hand-edit order; the set check is order-insensitive. Keep import block alphabetically sorted for ruff.
```

- [ ] **Step 2: Run the homogeneity gates**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v
```

Expected: all PASS, scaffolder already added `_CAPABILITY_SURFACES` entry to `test_capability_surface.py` so only exports test needed Step 1 patch.

- [ ] **Step 3: Patch CONTEXT.md**

Three edits (CONTEXT.md is domain glossary, kept in sync with code):

1. **Notation bullet list**, add after `**ISSN:**` bullet:

```
- **BIC:** `BICNotation(bank_code, country_code, location_code, branch_code, compact)` — `bank_code` 4-char institution prefix `A-Z0-9`, `country_code` 2-letter ISO 3166-1 plus `XK`, `location_code` 2-char suffix `A-Z0-9`, `branch_code` 3-char branch `A-Z0-9` or empty when BIC8, `compact` full string 8 or 11 equals `bank+country+location+branch`, grammar uppercases and strips label, location second char 0/1/2 informative only
```

2. **Capabilities table** (`| Capability | Domain | Authorities |`, 3 columns), insert row after `| **ISSN** |` row:

```
| **BIC** | Bank identifier codes | ISO 9362:2022, ISO 3166-1 (country codes plus XK) |
```

3. **Count wording**, intro sentence `Paxman ships twelve built-in capabilities` to `thirteen built-in capabilities`.

Do NOT paste 7 column row shape from earlier drafts, CONTEXT.md Capabilities table is 3 columns, wider row breaks its shape, see `paxman/capabilities/__init__.py` note.

- [ ] **Step 4: Patch MILESTONE.md BIC row**

Insert or replace BIC row (file line near 27, table row for BIC). Use authority from Research section 5.1 and section 15 URLs:

```
| 16 | **BIC** | Bank Identifier Codes appear with case variation, BIC/SWIFT label, without separators, 8 or 11 char. ISO 9362:2022 defines structure. Country at 5-6 is ISO 3166-1 plus XK. No checksum. | PARSER (optional BIC/SWIFT label `[\s:-]+`, uppercase, validate length 8 or 11, charset per position, country lookup, branch XXX preserved, location 0/1/2 not rejected, canonical compact plus grouped and bic11) | ISO 9362:2022, ISO 3166-1 (https://www.iso.org/iso-3166-country-codes.html, plus XK), SWIFT BIC Directory (https://www.swift.com/products/swiftref-bic-directory, https://www.swift.com/standards/data-standards/bic-business-identifier-code, rolling monthly, deferred) | "DEUTDEFF" -> "DEUTDEFF", "BIC: DEUTDEFF500" -> "DEUTDEFF500", "deutdeff" -> "DEUTDEFF", "BANKXK22" -> "BANKXK22" |
```

Note: keep MILESTONE pipe table intact, edit by file line not by table row number.

- [ ] **Step 5: Run gates**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py tests/unit/test_rule_output_format_purity.py -v
uv run pyright
uv run ruff check paxman/ tests/
uv run import-linter lint
```

Expected: all PASS (purity scan must find no `output_format` in `paxman/capabilities/BIC/rules/`).

- [ ] **Step 6: Commit**

```bash
git add paxman/capabilities/__init__.py tests/unit/test_capability_exports.py CONTEXT.md docs/development/MILESTONE.md
git commit -m "docs(bic): exports completeness, CONTEXT and MILESTONE"
```

---

### Task 7: Integration, Resolution Map, and Property Tests

**Files:**
- Create: `tests/integration/test_bic_capability.py`
- Create: `tests/property/test_bic_properties.py`
- Test: `tests/integration/test_bic_capability.py`

Research section 8, 9, 12: Full pipeline `MISSING` `INVALID` `SUCCESS` with `single_value=True`, two distinct mentions raise `MultipleMentionsError` never `Resolution.AMBIGUOUS` which is reserved for one cluster multi value reads, grouped vs compact dedup, `year` temporal filter, `VersionStamp` determinism, span invariants, location `0`/`1`/`2` not rejected, `XK` accepted, `XX` rejected via country rule, `bic11` expansion.

- [ ] **Step 1: Write the failing integration test**

```python
# tests/integration/test_bic_capability.py
import pytest

import paxman
from paxman.capabilities.BIC.capability import BICCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test (shipped ISSN and IBAN pattern)."""
    reset_registry()
    yield
    reset_registry()


def _register_bic() -> None:
    # register_all_shipped() does NOT include BIC (bootstrap._SHIPPED is twelve name tuple,
    # ISSN and IBAN have same status), register directly per test inside fixture window,
    # never at module level (module level registration is wiped by every file autouse reset).
    register_capability(BICCapability())


def test_success_electronic_and_label():
    _register_bic()
    contract = BICCapability.create_contract()
    for txt, expected in [
        ("DEUTDEFF", "DEUTDEFF"),
        ("deutdeff", "DEUTDEFF"),
        ("BIC: DEUTDEFF", "DEUTDEFF"),
        ("SWIFT: BNPAFRPPXXX", "BNPAFRPPXXX"),
        ("BIC DEUTDEFF500", "DEUTDEFF500"),
        ("DSBACNBXSHA", "DSBACNBXSHA"),
        ("CHASUS33", "CHASUS33"),
        ("BANKXK22", "BANKXK22"),
    ]:
        r = paxman.canonicalize(txt, contract)
        assert r.status == Resolution.SUCCESS, txt
        assert r.canonicalized_value == expected, txt
        assert r.candidates[0].provenance[0].specification_name == "ISO 9362:2022"
        assert r.span is not None
        assert r.candidates[0].recognition_rule == "bic_recognition"
        assert r.candidates[0].validation_rule == "Section 5-bic-structure-country"


def test_grouped_and_bic11_output():
    _register_bic()
    r = paxman.canonicalize(
        "DEUTDEFF", BICCapability.create_contract(output_format="grouped")
    )
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "DEUT DE FF"
    r2 = paxman.canonicalize(
        "DEUTDEFF500", BICCapability.create_contract(output_format="grouped")
    )
    assert r2.canonicalized_value == "DEUT DE FF 500"
    r3 = paxman.canonicalize(
        "DEUTDEFF", BICCapability.create_contract(output_format="bic11")
    )
    assert r3.canonicalized_value == "DEUTDEFFXXX"
    r4 = paxman.canonicalize(
        "DEUTDEFF500", BICCapability.create_contract(output_format="bic11")
    )
    assert r4.canonicalized_value == "DEUTDEFF500"


def test_invalid_country_and_charset():
    _register_bic()
    contract = BICCapability.create_contract()
    assert paxman.canonicalize("DEUTXXFF", contract).status == Resolution.INVALID
    assert paxman.canonicalize("BNPAQQPP", contract).status == Resolution.INVALID
    assert paxman.canonicalize("DEUT1EFF", contract).status == Resolution.INVALID


def test_missing_short_and_wrong_length():
    _register_bic()
    contract = BICCapability.create_contract()
    assert paxman.canonicalize("AB12", contract).status == Resolution.MISSING
    assert paxman.canonicalize("DEUTDEF", contract).status == Resolution.MISSING  # 7
    assert (
        paxman.canonicalize("DEUTDEFF50", contract).status == Resolution.MISSING
    )  # 10
    assert paxman.canonicalize("call me at noon", contract).status == Resolution.MISSING


def test_two_distinct_bics_raise_multiple_mentions():
    # single_value=True: two separate mentions resolving to distinct values
    # raise MultipleMentionsError (engine _enforce_single_value_invariant,
    # shipped precedent tests/integration/test_single_value_invariant.py).
    # Resolution.AMBIGUOUS is NOT produced here, it is reserved for one cluster multi value reads.
    _register_bic()
    contract = BICCapability.create_contract()
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize("DEUTDEFF / BNPAFRPPXXX", contract)


def test_span_word_guard():
    _register_bic()
    contract = BICCapability.create_contract()
    assert paxman.canonicalize("XDEUTDEFF", contract).status == Resolution.MISSING
    assert paxman.canonicalize("BICDEUTDEFF", contract).status == Resolution.MISSING


def test_year_filter_excludes_rule():
    # year=2021 filters out 2022 rule (orchestrator _filter_rules), so input is
    # recognized but nothing validates it -> deterministic INVALID (_determine_status: recognitions true, zero candidates). Not MISSING.
    _register_bic()
    contract = BICCapability.create_contract(year=2021)
    r = paxman.canonicalize("DEUTDEFF", contract)
    assert r.status == Resolution.INVALID


def test_location_second_char_not_rejected():
    _register_bic()
    contract = BICCapability.create_contract()
    for bic in ["DEUTDE0F", "BARCGB1L", "CHASGB2L"]:
        assert paxman.canonicalize(bic, contract).status == Resolution.SUCCESS, bic


def test_identical_bics_coalesce_to_success():
    _register_bic()
    contract = BICCapability.create_contract()
    # Two identical mentions in one slice coalesce by candidate dedup (value, recognition_rule, validation_rule) to SUCCESS
    r = paxman.canonicalize("DEUTDEFF and DEUTDEFF", contract)
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "DEUTDEFF"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest tests/integration/test_bic_capability.py -v` to PASS once Tasks 1 to 5 are correct (registration is per test inside fixture window, so no cross file registry state matters, suite is order independent by construction).

- [ ] **Step 3: No engine glue expected, verify span invariants only**

No code change expected. Engine already enforces recognition span invariants (`paxman/engine/orchestrator.py:_recognize`), single value semantics (two distinct mentions to `MultipleMentionsError`, which `test_two_distinct_bics_raise_multiple_mentions` pins), and determinism (same input plus contract plus snapshot to same `VersionStamp`). If a test fails here it is a Task 1 to 5 defect not an engine one, do not modify `paxman/engine/`. Sanity reference `tests/integration/test_single_value_invariant.py` and `tests/integration/test_issn_capability.py`.

- [ ] **Step 4: Run to pass plus coverage gates**

```bash
uv run pytest tests/capabilities/bic/ tests/integration/test_bic_capability.py -v
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/capabilities/BIC/*" --fail-under=95
```

Expected: coverage at least 95% on new package (if below, add missing branch: country set, `bic11` expansion, grouped length 8 vs 11).

- [ ] **Step 5: Property test (hypothesis)**

```python
# tests/property/test_bic_properties.py
from hypothesis import given, strategies as st

from paxman.capabilities.BIC.contract import BICContract
from paxman.capabilities.BIC.notation import BICNotation
from paxman.capabilities.BIC.rules.iso_9362_ed2022 import (
    Section5BICStructureCountry,
    COUNTRY_CODES,
)

RULE = Section5BICStructureCountry()
CONTRACT = BICContract()
COUNTRIES = sorted(COUNTRY_CODES)


def make_bic(bank: str, country: str, location: str, branch: str = "") -> str:
    return bank + country + location + branch


@given(
    st.text(min_size=8, max_size=11, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
)
def test_random_strings_usually_invalid_or_valid(s: str) -> None:
    # Smoke: matches() never raises on any 8 or 11 alnum string
    if len(s) not in (8, 11):
        return
    n = BICNotation(
        bank_code=s[0:4],
        country_code=s[4:6],
        location_code=s[6:8],
        branch_code=s[8:11] if len(s) == 11 else "",
        compact=s,
    )
    assert RULE.matches(n, CONTRACT) in (True, False)


def test_generated_valid_country_is_valid() -> None:
    bank = "DEUT"
    country = "DE"
    location = "FF"
    branch = "500"
    compact = bank + country + location + branch
    n = BICNotation(
        bank_code=bank,
        country_code=country,
        location_code=location,
        branch_code=branch,
        compact=compact,
    )
    assert RULE.matches(n, CONTRACT) is True


@given(
    st.sampled_from(COUNTRIES),
    st.text(min_size=4, max_size=4, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    st.text(min_size=2, max_size=2, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"),
)
def test_all_countries_in_set_are_valid(country: str, bank: str, location: str) -> None:
    compact = bank + country + location
    n = BICNotation(
        bank_code=bank,
        country_code=country,
        location_code=location,
        branch_code="",
        compact=compact,
    )
    # generic structure plus country in set to valid, no exception
    assert RULE.matches(n, CONTRACT) is True


def test_grouped_roundtrip_via_compact():
    from paxman.capabilities.BIC.capability import BICCapability

    cap = BICCapability()
    for bic in ["DEUTDEFF", "DEUTDEFF500", "BNPAFRPPXXX"]:
        n = BICNotation(
            bank_code=bic[0:4],
            country_code=bic[4:6],
            location_code=bic[6:8],
            branch_code=bic[8:11] if len(bic) == 11 else "",
            compact=bic,
        )
        grouped = cap.format_value(bic, "grouped", n)
        # grouped detaches via compact pivot, re grouping is deterministic
        compact2 = grouped.replace(" ", "")
        assert compact2 == bic
```

Run: `uv run pytest tests/property/test_bic_properties.py -k bic -v`

- [ ] **Step 6: Commit**

```bash
git add tests/integration/test_bic_capability.py tests/property/test_bic_properties.py
git commit -m "test(bic): integration, resolution map, and property checks"
```

---

### Task 8: Final Verification and Cleanup

- [ ] **Step 1: Full gate**

Format first, the plan snippets are semantically exact but not byte formatted:

```bash
uv run ruff format paxman/ tests/
```

Then:

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -m "unit or capability or integration or e2e" -q
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95
```

Expected: 0 errors, 95% global. Tasks 1 to 7 put layer markers on every BIC test module, so this `-m` filter executes the BIC suite, BIC tests being skipped here is a Task 1 to 7 defect not a filter artifact.

- [ ] **Step 2: Remove any `# type: ignore` or `# noqa` in `paxman/`**

```bash
grep -rn "type: ignore\|noqa\|pyright: ignore" paxman/capabilities/BIC/ || echo "clean"
```

Expected: `clean` (tests may use `# type: ignore[misc]` for frozen checks). Also verify no `output_format` token in rules:

```bash
grep -rn "output_format" paxman/capabilities/BIC/rules/ || echo "clean"
```

Expected: `clean`.

- [ ] **Step 3: Manual canonicalize smoke**

```bash
uv run python - << 'PY'
import paxman
from paxman.capabilities.BIC.capability import BICCapability

paxman.register_capability(BICCapability())

cases = [
    "DEUTDEFF",
    "BIC: DEUTDEFF500",
    "deutdeff",
    "BNPAFRPPXXX",
    "CHASUS33",
    "NEDSZAJJ",
    "NEDSZAJJXXX",
    "BANKXK22",
    "DEUTXXFF",
]

for txt in cases:
    c = BICCapability.create_contract()
    r = paxman.canonicalize(txt, c)
    print(f"{txt!r:20} -> {r.canonicalized_value!r:20} {r.status.name:8} span={r.span}")
    if r.status.name == "SUCCESS":
        print("  grouped:", paxman.canonicalize(txt, BICCapability.create_contract(output_format="grouped")).canonicalized_value)
        print("  bic11:  ", paxman.canonicalize(txt, BICCapability.create_contract(output_format="bic11")).canonicalized_value)

# Two distinct should raise
try:
    paxman.canonicalize("DEUTDEFF / BNPAFRPPXXX", BICCapability.create_contract())
except Exception as e:
    print("two distinct:", type(e).__name__, e)

# Word guard
print("XDEUTDEFF:", paxman.canonicalize("XDEUTDEFF", BICCapability.create_contract()).status)
print("BICDEUTDEFF:", paxman.canonicalize("BICDEUTDEFF", BICCapability.create_contract()).status)
PY
```

Expected: `DEUTDEFF` `SUCCESS`, `BIC: DEUTDEFF500` `SUCCESS` grouped `DEUT DE FF 500`, lowercase folds, `BANKXK22` `SUCCESS`, `DEUTXXFF` `INVALID`, two distinct raises `MultipleMentionsError`, guards `MISSING`.

- [ ] **Step 4: Push or hand off**, do not delete `docs/development/research/2026-08-23-bic-canonicalization.md`, it is already grounded to ISO 9362:2022 5th ed 2022-04-12 and SWIFT BIC Directory plus ISO 3166-1 plus XK, and to `paxman/capabilities/ISSN` and `paxman/capabilities/IBAN` precedent.

---

## Behavioral Contract

| Input | Contract | Status / canonical |
|---|---|---|
| `DEUTDEFF` | default `bic` | `SUCCESS` -> `DEUTDEFF` |
| `DEUTDEFF500` | default `bic` | `SUCCESS` -> `DEUTDEFF500` |
| `deutdeff` / `DeUtDeFf500` | default `bic` | `SUCCESS` -> `DEUTDEFF` / `DEUTDEFF500` case folded |
| `BIC: DEUTDEFF` / `SWIFT: BNPAFRPPXXX` / `BIC - NEDSZAJJ` | default `bic` | `SUCCESS` -> `DEUTDEFF` / `BNPAFRPPXXX` / `NEDSZAJJ`, span includes label |
| `BANKXK22` / `CBKIXKPRXXX` | default `bic` | `SUCCESS` -> `BANKXK22` / `CBKIXKPRXXX` (XK Kosovo, Research section 8 edge 18) |
| `DEUTXXFF` / `BNPAQQPP` | default `bic` | `INVALID` country not in ISO 3166-1 plus XK |
| `DEUT1EFF` (digit at 5) | default `bic` | `INVALID` charset per position |
| `DEUTDEF` (7) / `DEUTDEFF5` (9) / `DEUTDEFF50` (10) / `DEUTDEFF5000` (12) | default `bic` | `MISSING` grammar length guard 8 or 11 only |
| `BICDEUTDEFF` / `XDEUTDEFF` / `DEUTDEFFY` | default `bic` | `MISSING` word_only guards and label `[\s:-]+` never zero width |
| `DEUTDEFF` | `output_format="grouped"` | `SUCCESS` -> `DEUT DE FF` |
| `DEUTDEFF500` | `output_format="grouped"` | `SUCCESS` -> `DEUT DE FF 500` |
| `DEUTDEFF` | `output_format="bic11"` | `SUCCESS` -> `DEUTDEFFXXX` lossy expansion |
| `DEUTDEFF500` | `output_format="bic11"` | `SUCCESS` -> `DEUTDEFF500` already 11 |
| `DEUTDEFF / BNPAFRPPXXX` (two distinct) | default `bic` | `MultipleMentionsError` (`single_value=True`) |
| `DEUTDEFF and DEUTDEFF` (identical) | default `bic` | `SUCCESS` -> `DEUTDEFF` dedup coalesces |
| `call me at noon` | default `bic` | `MISSING` |
| any valid | `year=2021` | `INVALID` 2022 rule filtered, recognition true but zero candidates |
| `DEUTDE0F` / `BARCGB1L` / `CHASGB2L` | default `bic` | `SUCCESS` location second char 0/1/2 informative only (Research section 7) |

## Self Review Checklist

- One grammar, optional branch, single semantics `bic_recognition` avoids spurious `AMBIGUOUS` where 11 contains 8 as prefix, longer wins per grammar, cross grammar preserved per `orchestrator:_dedup_spans` (Research section 4.2).
- Label fused `[\s:-]+` one or more, ISBN-13 precedent prevents `BICDEUTDEFF` gluing, word_only both sides, `(?ai:)` ASCII restriction plus `isascii` filter (Research section 4.2, IBAN iban_recognition precedent).
- Rule `PARSER` fused structure plus country lookup, charset `^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$`, country set includes `XK` plus `AQ` and 249 codes, `XXX` preserved, `0`/`1`/`2` not rejected (Research section 7, 5.4, 5.1).
- Contract `bic` default, `grouped` and `bic11` offered, `bic11` documented lossy, frozen without slots, `capability_name="bic"` (Research section 6.1, decision 1).
- No `output_format` in `paxman/capabilities/BIC/rules/` (CI purity scan enforced), no `type: ignore` in `paxman/`, no cross capability imports, deterministic, no network.

---

## Execution Notes for Agents

- TDD mandatory: failing test first for every task, Red Green Commit cadence, one commit per task, do not batch completions.
- Contracts frozen without slots, notations frozen with slots, per `paxman/core/domain.py` and `paxman/core/capability_contract.py`.
- Use `uv run` for every command (ruff, pyright, pytest, import-linter, coverage).
- `paxman/api/bootstrap.py` `_SHIPPED` not touched in v1 like ISSN and IBAN precedent, integration registers `BICCapability()` directly per test inside `_clean_registry` fixture window.
- Document limitations verbatim in code comments: label glue blocked by `[\s:-]+`, longer wins per grammar, `bic11` lossy, location `0`/`1`/`2` informative.
- URLs are only those from Research section 15: `https://www.iso.org/standard/84108.html` (ISO 9362:2022), `https://www.iso.org/standard/60390.html` (2014), `https://www.iso.org/standard/17047.html` (2009), `https://www.swift.com/standards/data-standards/bic-business-identifier-code`, `https://www.swift.com/products/swiftref-bic-directory`, `https://www.swiftref.com/en/bicsearch`, `https://www.swift.com/sites/default/files/files/swift_bic_registration_procedures_2021.pdf`, `https://www.iso.org/iso-3166-country-codes.html`, `https://www.iso.org/cms/live/live/en/sites/isoorg/home/developing-standards/who-develops-standards/maintenance_agencies.html`.

