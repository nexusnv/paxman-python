# Scanner Right-Gap Deferral Fix Implementation Plan (issue #99)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `ScannerMatcher` right-gap asymmetry so a stripped char immediately right of a hit does not cause view-level over-rejection — extend the left-gap deferral symmetrically to the right, letting the engine's original-text re-check adjudicate.

**Architecture:** In `paxman/core/grammar/matchers/scanner.py:ScannerMatcher.match`, the left-gap deferral (`pos > 0 and source_starts[pos] != source_ends[pos-1]`) is mirrored for the right edge (`end < n and source_starts[end] != source_ends[end-1]`). When either gap exists and `view.stripped_chars` is truthy, the view-level `check_boundary` is deferred to the engine's `check_boundary(text, o_s, o_e, boundary)` at pre-extension end (#88). No change to `engine_loop` (already correct) and no change to `BoundarySpec` (single-source check). Optionally remove redundant `_url_emit` trailing `\t\n\r` loop now that the kernel does it data-driven.

**Tech Stack:** Python 3.11+, `ScannerMatcher`, `View` (`source_starts`/`source_ends`), `BoundarySpec`, `ScanContext`, `pytest` (unit/property), strict `pyright`, `ruff`, `import-linter`, `uv`.

**References:** Issue #99, PR #98 final review, `paxman/core/grammar/matchers/scanner.py:100-113`, `paxman/core/grammar/engine_loop.py:137-139`, `paxman/capabilities/URL/grammar/absolute_uri_recognition.py:101-107`.

---

## File Structure

- Modify: `paxman/core/grammar/matchers/scanner.py` — `ScannerMatcher.match` boundary block (extend deferral to right gap).
- Modify (optional): `paxman/capabilities/URL/grammar/absolute_uri_recognition.py` — remove redundant trailing `\t\n\r` extension in `_url_emit` (now handled by `engine_loop` data-driven).
- Test: `tests/unit/test_kernel_stripped_chars.py` or `tests/unit/test_scanner_right_gap.py` — right-gap deferral unit tests.
- Test: `tests/capabilities/url/test_grammar.py` or existing `test_url_scanner_parity.py` — ensure URL parity still green after redundant loop removal.

No new modules; no changes to `paxman/core/grammar/boundary_spec.py` or `engine_loop.py`.

---

### Task 1: Reproduce right-gap over-rejection (TDD red)

**Files:**
- Create: `tests/unit/test_scanner_right_gap.py` (or add to `tests/unit/test_kernel_stripped_chars.py`)
- Modify: none yet (production)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_scanner_right_gap.py`:

```python
import pytest
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.scan_context import ScanContext, View

pytestmark = pytest.mark.unit

def _gap_view_right(stripped: str | None) -> View:
    """View over original "AB\\tX" → subject "ABX" with gap before X at end.

    Original indices: A[0,1), B[1,2), \\t[2,3) stripped, X[3,4). Subject "ABX" len 3:
    - subject[0]='A' maps to [0,1)
    - subject[1]='B' maps to [1,2)
    - subject[2]='X' maps to [3,4)
    Hit (0,2) "AB" has right neighbor in original '\\t', not 'X', so
    view-level right guard would see 'X' (forbidden) but engine would see '\\t' (pass).
    """
    return View(
        subject="ABX",
        source_starts=(0, 1, 3),
        source_ends=(1, 2, 4),
        _text_len=4,
        stripped_chars=stripped,
    )

def _scan_ab(view: View, pos: int):
    return (2, None) if pos == 0 else None

def test_scanner_defers_right_gap_when_stripped():
    """Right gap + stripped_chars set → view-level right check deferred."""
    m = ScannerMatcher(scan=_scan_ab, boundary=BoundarySpec(left=None, right=("X",), mode="zero_width"), emit=lambda s,c: s)
    # With stripped_chars="\\t", right gap at end=2 (source_starts[2]=3 != source_ends[1]=2) → defer, so hit passes view check
    assert m.match(_gap_view_right("\t")) == [(0, 2)]

def test_scanner_checks_right_gap_without_stripped():
    """Same gap, no stripped_chars → deferral must NOT apply, right guard fires."""
    m = ScannerMatcher(scan=_scan_ab, boundary=BoundarySpec(left=None, right=("X",), mode="zero_width"), emit=lambda s,c: s)
    assert m.match(_gap_view_right(None)) == []
    assert m.match(_gap_view_right("")) == []  # empty string also falsy → no deferral
```

Also add a test for the engine's authoritative check via `engine_loop` (optional, but ensures #88 still governs):

```python
def test_engine_right_gap_is_authoritative(monkeypatch):
    """Engine re-check on original text governs right gap, not view."""
    from paxman.core.grammar.engine_loop import _VIEW_REGISTRY, run_matchers_with_context
    from types import SimpleNamespace

    class _TabStrip:
        name="tstrip"; provenance=None; stripped_chars="\t"
        def normalize(self, text):
            # same as previous _TabStrip helper
            chars=[]; starts=[]
            for i,ch in enumerate(text):
                if ch=="\t": continue
                chars.append(ch); starts.append(i)
            subj="".join(chars)
            return (subj, tuple(starts), tuple(s+1 for s in starts)) if subj else ("", (), ())

    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    m = ScannerMatcher(scan=lambda v,p: (2, None) if p==0 else None, view_name="tstrip", boundary=BoundarySpec(left=None, right=("X",), mode="zero_width"), emit=lambda s,c: s)
    ctx = ScanContext.of("AB\tX")
    grammar = SimpleNamespace(matchers=[m], name="toy")
    out = list(run_matchers_with_context(ctx, [grammar]))
    # Engine checks original text[2]=='\\t', not view subject[2]=='X', so hit at [0,2) "AB" should be kept (right neighbor is tab, not X)
    # With current left-only deferral, scanner would have rejected, but after fix it should be deferred and engine keeps it
    # For this specific test, we expect the hit to be kept after fix, so before fix it would be [].
    # Adjust assertion to reflect the fixed behavior: after fix, hit is kept.
    # Before fix, this test will FAIL (0 results), after fix PASS (1 result)
    assert [(m.start,m.end,m.raw_text) for m in out] == [(0,3,"AB\t")]
```

Simplify: Keep the first two tests as primary red; the engine test is optional for Task 1, can be deferred to Task 2 verification.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_scanner_right_gap.py -v`
Expected: `test_scanner_defers_right_gap_when_stripped` FAIL — with current left-only deferral, right gap at `end=2` is not deferred, so view-level right guard sees `subject[2]='X'` (forbidden) and returns `[]` instead of `[(0,2)]`. The other test should PASS (no deferral, correctly rejects).

- [ ] **Step 3: Verify existing left-gap tests still pass**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -k "test_scanner_defers_left" -v` (or the previous left-gap tests in `test_kernel_stripped_chars.py`)
Expected: still PASS (left deferral unchanged).

---

### Task 2: Extend deferral symmetrically to right gap

**Files:**
- Modify: `paxman/core/grammar/matchers/scanner.py:100-113` (`ScannerMatcher.match`)

- [ ] **Step 1: Update `ScannerMatcher.match` boundary block**

Replace:

```python
                # Boundary check at hit positions (O(hits), not O(positions)).
                # On a stripped view the subject's left char may not be the
                # original left char: if there's a gap between pos and pos-1
                # in the original (a stripped char), the original left char
                # is that stripped char — the engine re-checks the boundary
                # on the original text for stripped views, so the view-level
                # check is deferred here. Otherwise the view check is
                # accurate.
                if self.boundary is not None:
                    if (
                        view.stripped_chars
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and pos > 0
                        and view.source_starts[pos] != view.source_ends[pos - 1]
                    ):
                        # Gap → original left char is a stripped char, not
                        # forbidden, so boundary passes; no view check.
                        pass
                    elif not check_boundary(s, pos, end, self.boundary):
                        pos += 1
                        continue
```

with:

```python
                # Boundary check at hit positions (O(hits), not O(positions)).
                # On a stripped view the subject's left/right char may not be
                # the original neighbor: if there's a gap between pos and
                # pos-1 or between end and end-1 in the original (a stripped
                # char), the original neighbor is that stripped char — the
                # engine re-checks the boundary on the original text for
                # stripped views, so the view-level check is deferred here.
                # Otherwise the view check is accurate (single-char guards;
                # multi-char guard windows spanning an older stripped char are
                # governed by the engine's original-text re-check).
                if self.boundary is not None:
                    left_gap = (
                        view.stripped_chars
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and pos > 0
                        and view.source_starts[pos] != view.source_ends[pos - 1]
                    )
                    right_gap = (
                        view.stripped_chars
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and end < n
                        and end > 0
                        and view.source_starts[end] != view.source_ends[end - 1]
                    )
                    if left_gap or right_gap:
                        # Gap → original neighbor is a stripped char, not
                        # forbidden, so boundary passes; no view check.
                        # Engine's original-text re-check governs.
                        pass
                    elif not check_boundary(s, pos, end, self.boundary):
                        pos += 1
                        continue
```

Note: `n = len(s)` is already defined as `n = len(s)  # s = view.subject already in scope` (or `len(view.subject)`) in the surrounding `match` method — use the existing `n`.

Keep `max_window` and `digest` logic unchanged.

Update module docstring if it mentions left-only deferral — reword to "left and right gaps".

- [ ] **Step 2: Run the previously failing tests**

Run: `uv run pytest tests/unit/test_scanner_right_gap.py -v`
Expected: all PASS — `test_scanner_defers_right_gap_when_stripped` now returns `[(0,2)]` (deferred), the other still `[]`.

- [ ] **Step 3: Run left-gap and existing scanner tests**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v tests/unit/test_scanner_right_gap.py -v`
Expected: all PASS (left deferral still works, right now works, falsy `""` still no deferral).

- [ ] **Step 4: Commit**

```bash
git add paxman/core/grammar/matchers/scanner.py tests/unit/test_scanner_right_gap.py
git commit -m "fix(kernel): defer scanner boundary on right gap for stripped views (#99)"
```

---

### Task 3: Remove redundant `_url_emit` trailing extension (optional, safe)

**Files:**
- Modify: `paxman/capabilities/URL/grammar/absolute_uri_recognition.py:101-107` (`_url_emit`)

- [ ] **Step 1: Write a parity test for URL trailing `\t\n\r`**

Add to `tests/unit/test_scanner_right_gap.py` or `tests/property/test_url_scanner_parity.py` (if not already covered):

```python
def test_url_trailing_tab_via_kernel():
    """URL trailing tab is now handled by kernel, not _url_emit."""
    from paxman.capabilities.URL.grammar.absolute_uri_recognition import AbsoluteUriRecognition
    g = AbsoluteUriRecognition()
    m = g.recognize("A:0\n")
    assert len(m) == 1 and m[0].raw_text == "A:0\n"
```

If this test already exists in `test_url_scanner_parity.py`, skip.

- [ ] **Step 2: Remove redundant loop in `_url_emit`**

In `paxman/capabilities/URL/grammar/absolute_uri_recognition.py`, `_url_emit` currently:

```python
def _url_emit(span, ctx):
    s, e = span
    text = ctx.text
    while e < len(text) and text[e] in "\t\n\r":
        e += 1
    # ... return URLNotation
```

Remove the `while e < len(text) and text[e] in "\t\n\r": e += 1` loop (kernel `engine_loop.py:137-139` already does `while o_e < len(text) and text[o_e] in view.stripped_chars: o_e += 1` for `view.stripped_chars == "\t\n\r"`). Keep the rest of `_url_emit` unchanged.

- [ ] **Step 3: Run tests to verify still pass**

Run: `uv run pytest tests/capabilities/url/test_grammar.py tests/property/test_url_scanner_parity.py tests/unit/test_scanner_right_gap.py -v`
Expected: all PASS — trailing `\t\n\r` still included via kernel, now idempotent.

- [ ] **Step 4: Commit (if changed)**

```bash
git add paxman/capabilities/URL/grammar/absolute_uri_recognition.py
git commit -m "refactor(url): remove redundant trailing tab extension (kernel now handles #99)"
```

If you skip this task (keep idempotent loop), it is also correct — no behavior change, just DRY. Either is acceptable; if skipped, note in commit message that the loop is intentionally left as idempotent.

---

### Task 4: Full regression

**Files:**
- Modify: none (verify)

- [ ] **Step 1: Run full scanner and URL suites**

Run: `uv run pytest tests/property/test_url_scanner_parity.py tests/property/test_hypothesis_view_roundtrip.py tests/property/test_e164_scanner_parity.py tests/unit/test_b1_common_word_suppression.py -q`
Expected: all PASS.

- [ ] **Step 2: Run full gate**

Run:
```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
uv run pyright
uv run import-linter lint
uv run pytest -q
```

Expected: all green.

- [ ] **Step 3: Update CHANGELOG.md**

Under `## [Unreleased]` → `### Fixed`, add:

```markdown
- **Kernel — scanner right-gap deferral (#99):** `ScannerMatcher` now defers
  view-level boundary checks on both left and right gaps for stripped views
  (previously only left), so a stripped char immediately right of a hit does
  not cause view-level over-rejection; the engine's original-text re-check
  governs. Unreachable with shipped grammars (URL `idna` is left-only).
```

- [ ] **Step 4: Commit docs**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for scanner right-gap deferral (#99)"
```

---

## Self-Review

**1. Spec coverage:**
- Right-gap deferral for stripped views — Task 2 (symmetric `right_gap` check).
- Left-gap still works — Task 2 Step 3.
- Engine re-check remains authoritative — Task 2 comment and engine_loop unchanged (#88).
- Redundant `_url_emit` loop removal — Task 3 (optional, idempotent if kept).

**2. Placeholder scan:** No TODOs — every step has exact code, file paths, expected outputs.

**3. Type consistency:** `view.stripped_chars: str | None`, `view.source_starts: tuple[int, ...] | None`, `n = len(s)` already in scope, `check_boundary(s, pos, end, self.boundary)` signature unchanged — all consistent.

If any gap found, fix inline before handing off.

---

## Execution Handoff

Plan complete and saved to `docs/development/plans/2026-08-30-scanner-right-gap.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
