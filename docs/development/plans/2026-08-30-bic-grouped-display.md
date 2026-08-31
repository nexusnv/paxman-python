# BIC Grouped Display Implementation Plan (issue #41)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Recognize SWIFT grouped display `AAAA BB CC [XXX]` (e.g. `DEUT DE FF`, `BNPA FR PP XXX`) so `canonicalize("DEUT DE FF", BICContract)` returns `SUCCESS → DEUTDEFF` instead of `MISSING`, while `DEUT  DEFF` (double space) stays `MISSING`.

**Architecture:** Minimal inline change to `paxman/capabilities/BIC/grammar/bic_recognition.py:_BIC_BODY`: insert optional single space ` ?` between the 4-2-2-(3) groups (`[A-Z0-9]{4} ?[A-Z]{2} ?[A-Z0-9]{2}(?: ?[A-Z0-9]{3})?`). The existing `notation_fn` already strips via `isalnum() + upper()`, so no `Pre` stage is needed. `BoundaryGuard.word_only()` stays correct (outer word boundaries unchanged). Updated docstring documents grouped input as accepted.

**Tech Stack:** Python 3.11+, pytest (capability marker), strict pyright, ruff, import-linter, uv.

**References:** Issue #41, `paxman/capabilities/BIC/grammar/bic_recognition.py:16-22` (`_BIC_BODY`), `docs/development/research/2026-08-23-bic-canonicalization.md` §2 row 4 & §4.2, `tests/capabilities/bic/test_grammar.py`.

---

## File Structure

- Modify: `paxman/capabilities/BIC/grammar/bic_recognition.py` — `_BIC_BODY` regex, `_BIC_PATTERN` trailing guard, and `BICRecognitionGrammar` docstring.
- Test: `tests/capabilities/bic/test_grammar.py` — add grouped display vectors (grammar-level), double-space and 9/10-length negative cases.
- Test: `tests/integration/test_bic_grouped.py` — `canonicalize` integration guard for grouped display (`pytest.mark.integration`, autouse `_clean_registry`).
- Docs: `CHANGELOG.md` (add Fixed entry), `paxman/capabilities/BIC/grammar/bic_recognition.py` docstring.

No new modules; no changes to `paxman/core` (RegexStage + BoundaryGuard unchanged, trailing guard is in BIC pattern). No `Pre` stage.

---

### Task 1: Reproduce grouped display MISSING (TDD red)

**Files:**
- Modify: `tests/capabilities/bic/test_grammar.py` (add grouped tests)
- Modify: none yet (production)

- [ ] **Step 1: Write the failing grammar tests**

Add to `tests/capabilities/bic/test_grammar.py` (e.g. after the existing `test_name` or in a new `TestBICGroupedDisplay` class, but inside the same file):

```python
def test_recognizes_grouped_8_char():
    """(#41) Grouped 8-char BIC with single spaces must be recognized."""
    # Use the module-level GRAMMAR = BICRecognitionGrammar() already in file
    for raw, expected_compact in [
        ("DEUT DE FF", "DEUTDEFF"),
        ("BNPA FR PP", "BNPAFRPP"),
    ]:
        matches = GRAMMAR.recognize(raw)
        assert len(matches) == 1, f"{raw!r} should match"
        assert matches[0].notation.compact == expected_compact
        assert matches[0].raw_text == raw
        assert matches[0].start == 0
        assert matches[0].end == len(raw)

def test_recognizes_grouped_11_char():
    """(#41) Grouped 11-char BIC with single spaces must be recognized."""
    for raw, expected_compact in [
        ("DEUT DE FF 500", "DEUTDEFF500"),
        ("BNPA FR PP XXX", "BNPAFRPPXXX"),
        ("CHAS US 33", "CHASUS33"),  # 4+2+2 variant grouped as 4 2 2
    ]:
        matches = GRAMMAR.recognize(raw)
        assert len(matches) == 1, f"{raw!r} should match"
        assert matches[0].notation.compact == expected_compact
        assert matches[0].raw_text == raw

def test_grouped_double_space_is_missing():
    """(#41) Double space must stay MISSING (only single spaces allowed)."""
    assert GRAMMAR.recognize("DEUT  DE FF") == []
    assert GRAMMAR.recognize("DEUT DE  FF") == []
    # double space before branch also MISSING (no valid 8/11 with single-space groups)
    assert GRAMMAR.recognize("DEUT DE FF  500") == []

def test_grouped_invalid_lengths_are_missing():
    """(#41) 9/10-length spaced variants must not be recognized."""
    # 9 alnum (8+1) and 10 alnum (8+2) with single spaces — stripped length 9/10
    assert GRAMMAR.recognize("DEUT DE FF 5") == []
    assert GRAMMAR.recognize("DEUT DE FF 50") == []
    assert GRAMMAR.recognize("BNPA FR PP XX") == []  # 10
    assert GRAMMAR.recognize("BNPA FR PP X") == []   # 9

def test_grouped_case_insensitive_and_with_label():
    """(#41) Grouped case-insensitive and with BIC/SWIFT label."""
    assert GRAMMAR.recognize("deut de ff").pop().notation.compact == "DEUTDEFF"
    assert GRAMMAR.recognize("BIC DEUT DE FF").pop().notation.compact == "DEUTDEFF"
    assert GRAMMAR.recognize("SWIFT: BNPA FR PP XXX").pop().notation.compact == "BNPAFRPPXXX"
```

For integration guard, create `tests/integration/test_bic_grouped.py` (per `tests/AGENTS.md` layer discipline — pipeline checks belong in `integration/` with `pytest.mark.integration` and autouse `_clean_registry` fixture; see `tests/integration/test_grammar_extensions.py` for pattern):

```python
import pytest
from paxman.api import canonicalize
from paxman.capabilities.BIC import BICCapability
from paxman.core.discovery import reset_registry  # via autouse fixture, not direct

pytestmark = pytest.mark.integration

def test_canonicalize_grouped_display():
    """(#41) canonicalize grouped must be SUCCESS, double space MISSING."""
    c = BICCapability.create_contract()
    assert canonicalize("DEUT DE FF", c).status.name == "SUCCESS"
    assert canonicalize("DEUT DE FF", c).canonicalized_value == "DEUTDEFF"
    assert canonicalize("BNPA FR PP XXX", c).canonicalized_value == "BNPAFRPPXXX"
    assert canonicalize("DEUT  DE FF", c).status.name == "MISSING"
    # 9/10-length spaced variants stay MISSING at pipeline level as well
    assert canonicalize("DEUT DE FF 5", c).status.name == "MISSING"
```

Add autouse `_clean_registry` fixture as in `tests/integration/test_grammar_extensions.py` (calls `reset_registry()` before/after). Adjust imports to match that file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/bic/test_grammar.py -k "test_recognizes_grouped or test_grouped" -v`
Expected: FAIL — `assert len(matches)==1` fails with `0` (grammar returns `[]` for `"DEUT DE FF"`). Double-space test currently PASSES (already `[]`), but grouped tests must fail.

Also run the integration guard if added:

Run: `uv run pytest tests/capabilities/bic/test_capability.py -k test_canonicalize_grouped -v` or `tests/integration/test_bic_grouped.py -v`
Expected: FAIL — `MISSING` instead of `SUCCESS`.

- [ ] **Step 3: Verify no other BIC tests broke yet (sanity)**

Run: `uv run pytest tests/capabilities/bic/test_grammar.py -v`
Expected: existing tests PASS, only the 3 new grouped tests FAIL.

---

### Task 2: Allow single spaces inline in `_BIC_BODY`

**Files:**
- Modify: `paxman/capabilities/BIC/grammar/bic_recognition.py:19-22` (`_BIC_BODY`)
- Modify: `paxman/capabilities/BIC/grammar/bic_recognition.py:58-65` (class docstring)

- [ ] **Step 1: Update `_BIC_BODY` to allow optional single spaces and fix trailing guard**

Replace:

```python
_BIC_BODY = (
    r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?"
    r"(?P<compact>[A-Z0-9]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?))"
)
```

with:

```python
_BIC_BODY = (
    r"(?ai:(?:(?:BIC|SWIFT)[\s:-]+)?"
    r"(?P<compact>[A-Z0-9]{4} ?[A-Z]{2} ?[A-Z0-9]{2}(?: ?[A-Z0-9]{3})?))"
)
```

Add comment above `_BIC_BODY`: `# Grouped display: single optional space between 4-2-2-3 groups, e.g. "DEUT DE FF" (#41). Double spaces stay MISSING; notation_fn strips via isalnum().`

Then update `_BIC_PATTERN` trailing guard to block 8-char prefix inside 9/10 or double-space trailing cases. Replace:

```python
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + rf"(?!(?ai:(?:BIC|SWIFT){_BIC_SUFFIX_RE}\b))"
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)
```

with:

```python
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + rf"(?!(?ai:(?:BIC|SWIFT){_BIC_SUFFIX_RE}\b))"
    + _BIC_BODY
    + r"(?![ ]*[A-Za-z0-9])"  # block 8-char prefix inside 9/10 or double-space trailing (#41)
    + BoundaryGuard.word_only().lookahead
)
```

This ensures `DEUT DE FF 5` (9, single space+digit) and `DEUT DE FF  500` (double space before branch) do not carve out an 8-char `DEUT DE FF` match; valid `DEUT DE FF` (8) and `DEUT DE FF 500` (11, single spaces) still match because the 11-char alternative consumes the trailing ` 500` and its own trailing guard sees end-of-string. Keep `_BIC_SUFFIX_RE`, `_COUNTRY_ALT` unchanged; the label negative lookahead still blocks glued `BICDEUTDEFF`.

If `(?![ ]*[A-Za-z0-9])` proves too broad (e.g. blocks `DEUT DE FF` when followed by `, ` punctuation?), verify: after `DEUT DE FF` at end, next char is end or `,` (not alnum, not space+alnum), so it passes. After `DEUT DE FF` with trailing `,`, substring `", "` first char `,` not space, so ` [ ]*` (zero spaces) + alnum fails (`,` not alnum), so passes. Only spaces+alnum triggers block, matching the 9/10/double-space cases.

- [ ] **Step 2: Update `BICRecognitionGrammar` docstring**

Replace:

```python
class BICRecognitionGrammar(PipelineGrammar[BICNotation]):
    """BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label."""
```

with:

```python
class BICRecognitionGrammar(PipelineGrammar[BICNotation]):
    """BIC recognition — 8 or 11 alphanum with optional BIC/SWIFT label.

    Recognizes contiguous compact forms (``DEUTDEFF``) and SWIFT grouped
    display (``DEUT DE FF``, ``DEUT DE FF 500``, ``BNPA FR PP XXX``) with
    single spaces between the 4-2-2-3 groups; double spaces are not
    recognized. Case-insensitive; notation strips non-alnum.
    """
```

- [ ] **Step 3: Run the previously failing tests**

Run: `uv run pytest tests/capabilities/bic/test_grammar.py -k "test_recognizes_grouped or test_grouped" -v`
Expected: PASS — all 3 grouped tests green, double-space still `[]`, case-insensitive and label cases green.

Also verify the raw_text span is correct: `DEUT DE FF` should have `raw_text == "DEUT DE FF"` and `start==0, end==10` (10 chars including 2 spaces). The `compact` group captures `"DEUT DE FF"` with spaces, `notation_fn` strips to `"DEUTDEFF"` via `isalnum()`.

- [ ] **Step 4: Run all BIC grammar tests**

Run: `uv run pytest tests/capabilities/bic/test_grammar.py -v`
Expected: all PASS, including:
- Existing compact tests (`DEUTDEFF`, `DEUTDEFF500`, `BIC: DEUTDEFF`)
- Boundary tests (`XDEUTDEFF`, `BICDEUTDEFF` still `[]`, `BICXUS1AABC` still `1`)
- New grouped tests

- [ ] **Step 5: Commit**

```bash
git add paxman/capabilities/BIC/grammar/bic_recognition.py tests/capabilities/bic/test_grammar.py tests/integration/test_bic_grouped.py
git commit -m "fix(bic): recognize grouped display DEUT DE FF (#41)"
```

---

### Task 3: Full regression, integration, and changelog

**Files:**
- Modify: `CHANGELOG.md` (add Fixed entry)
- Test: all suites

- [ ] **Step 1: Run BIC capability and integration suites**

Run: `uv run pytest tests/capabilities/bic -v`
Expected: all PASS.

If you added an integration test file `tests/integration/test_bic_grouped.py`, run `uv run pytest tests/integration -k bic -v` as well.

- [ ] **Step 2: Run full gate**

Run:
```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
uv run pyright
uv run import-linter lint
uv run pytest -q
```

Expected: all green (ruff, format, pyright 0 errors, import-linter KEPT, 95% coverage — previously 3744 passed / 2 skipped, now 3744+3 new grouped tests = 3747).

- [ ] **Step 3: Update `CHANGELOG.md`**

Under `## [Unreleased]` → `### Fixed`, add (keep existing entries verbatim, add after Phone entry):

```markdown
- **BIC — grouped display (#41):** recognizes SWIFT paper form
  `AAAA BB CC [XXX]` with single spaces (e.g. `DEUT DE FF` →
  `DEUTDEFF`, `BNPA FR PP XXX` → `BNPAFRPPXXX`); double spaces remain
  `MISSING`.
```

- [ ] **Step 4: Commit docs**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for BIC grouped display (#41)"
```

---

## Self-Review

**1. Spec coverage:**
- Issue #41 requires `DEUT DE FF` → `DEUTDEFF`, `DEUT DE FF 500` → `DEUTDEFF500`, `BNPA FR PP XXX` → `BNPAFRPPXXX` — Task 1 tests pin all three, plus `CHAS US 33` (grouped 8-char variant).
- Requires `DEUT  DEFF` (double space) stays `MISSING` — Task 1 `test_grouped_double_space_is_missing` pins it (including `DEUT DE FF  500` double space before branch).
- Requires 9/10-length spaced variants negative — Task 1 `test_grouped_invalid_lengths_are_missing` pins `DEUT DE FF 5` (9) and `DEUT DE FF 50` (10) as `[]` via trailing guard `(?![ ]*[A-Za-z0-9])`.
- Requires `isalnum()` stripping preserved — Task 2 keeps `notation_fn` unchanged, only pattern changes.
- Requires no `Pre` stage — Task 2 does inline ` ?`, not `StandardPre` collapsing.
- Requires docstring/capability docs updated — Task 2 updates class docstring.
- Requires regression for glued label `BICDEUTDEFF` still `MISSING` and `BICXUS1AABC` still recognized — Task 2 Step 4 checks.

**2. Placeholder scan:** No TODOs, no "add appropriate handling" — every step has exact code, file paths, and expected outputs.

**3. Type consistency:** `BICRecognitionGrammar` is `PipelineGrammar[BICNotation]` with `RegexStage` pattern `str` and `notation_fn: re.Match -> BICNotation`; `ScannerMatcher` not involved; tests use `GRAMMAR.recognize` returning `list[RecognitionMatch[BICNotation]]` and `canonicalize` returning `ExecutionResult` — all consistent.

If any gap found, fix inline before handing off.

---

## Execution Handoff

Plan complete and saved to `docs/development/plans/2026-08-30-bic-grouped-display.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
