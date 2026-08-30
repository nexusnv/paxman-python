# Grammar Kernel Hardening Implementation Plan (issues #87, #88, #68)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the stringly-typed `view_name == "idna"` special-casing from the recognition kernel (replace with a data flag on the view), fix the ordering bug where the trailing `\t\n\r` extension runs before the idna boundary re-check, and de-duplicate the double boundary filtering in `CandidatesMatcher`.

**Architecture:** Views (`paxman/core/grammar/scan_context.py::View`) gain a `stripped_chars: str | None` field carrying *which characters the normalizer strips* as data. `IDNAFold` declares `stripped_chars="\t\n\r"`. The engine loop (`paxman/core/grammar/engine_loop.py`) and the scanner matcher (`paxman/core/grammar/matchers/scanner.py`) branch on `view.stripped_chars is not None` instead of the literal view name. The trailing-extension ordering in the engine loop is fixed so the boundary check sees the pre-extension span. `CandidatesMatcher.match` builds `result` and `stored_flat` in a single pass so `check_boundary` runs once per span.

**Tech Stack:** Python 3.11+, pytest (markers: `unit`, `property`), strict pyright, ruff, import-linter, uv for all commands.

**References:** #87 (stringly-typed idna special casing), #88 (extension/boundary ordering), #68 (double boundary filtering). Branch: `fix/grammar-kernel-hardening` (cut from `dev`).

**Scope guard:** Only `paxman/core/grammar/{scan_context,normalizers,engine_loop}.py`, `paxman/core/grammar/matchers/scanner.py`, `paxman/core/grammar/matchers/candidates.py`, one new test module, plus docs/CHANGELOG. No capability packages change behavior (verified by the existing parity suites).

---

## Background the implementer needs

### Current state of the code (verbatim context)

**`paxman/core/grammar/engine_loop.py`** — inside `_run_matchers_with_context`, after a matcher returns a span, the engine translates it to original coordinates and then does TWO idna-only things gated on the magic string `view_name == "idna"`:

```python
o_s, o_e = view.original_span(s, e)
# IDNAFold trailing \t\n\r: ... (comment)
if view_name == "idna":                      # ← MAGIC STRING #1 (line ~119)
    while o_e < len(text) and text[o_e] in "\t\n\r":
        o_e += 1
# ... common-word suppression ...
# Boundary check on original for IDNAFold (stripped \t\n\r).
# Scanner defers for view_name=="idna"; ...
boundary = getattr(matcher, "boundary", None)
if (
    view_name == "idna"                      # ← MAGIC STRING #2 (line ~138)
    and boundary is not None
    and not check_boundary(text, o_s, o_e, boundary)
):
    continue
```

Bug (#88): `o_e` is extended over stripped `\t\n\r` *before* `check_boundary` runs, so a right-side guard inspects the char *after* the trailing run instead of the immediate neighbor. Harmless today (the only idna-view boundary is `SCHEME_CHAR_LEFT`, a left-only guard) but wrong for any future right-side guard.

**`paxman/core/grammar/matchers/scanner.py`** — inside `ScannerMatcher.match`, the left-boundary deferral for stripped views is also gated on the magic string:

```python
if self.boundary is not None:
    if (
        self.view_name == "idna"             # ← MAGIC STRING #3 (line ~98)
        and view.source_starts is not None
        and view.source_ends is not None
        and pos > 0
        and view.source_starts[pos] != view.source_ends[pos - 1]
    ):
        # Gap → original left char is stripped \t\n\r, not
        # forbidden, so boundary passes; no view check.
        pass
    elif not check_boundary(s, pos, end, self.boundary):
        pos += 1
        continue
```

**`paxman/core/grammar/matchers/candidates.py`** — `CandidatesMatcher.match` boundary-filters `result` (lines ~189-194) and then *rebuilds* `stored_flat` from `flat` with an identical second `check_boundary` loop (lines ~195-213). Correct but duplicated work, and the two loops can diverge.

**`paxman/core/grammar/scan_context.py`** — `View(subject, source_starts, source_ends, _text_len)`; `ScanContext.view(name, normalizer)` materializes and caches a `View`.

**`paxman/core/grammar/normalizers.py`** — `IDNAFold.normalize` strips `\t\n\r` from the text and returns `(cleaned, starts, ends)`; it currently records *nothing* about what it stripped.

### Design decisions (locked)

1. **Flag name:** `stripped_chars: str | None` on `View`, `ScanContext.view(...)`, and the normalizer object. `IDNAFold` sets `"\t\n\r"`. No other shipped normalizer sets it (`StripSeparators` strips `" ().-"` but must NOT set the flag — its stripped chars are never re-absorbed into spans; the flag means "stripped chars that legacy matchers may absorb into their emitted span", per #87 option 1).
2. **Engine loop order after the fix** (implements #87 + #88): translate span → boundary re-check on the **pre-extension** original span (only when `view.stripped_chars is not None` and the matcher has a boundary) → extend `o_e` over `view.stripped_chars` → common-word suppression (unchanged, uses the final span).
3. **Scanner deferral** branches on `view.stripped_chars is not None` instead of `self.view_name == "idna"`. Test doubles construct `View` directly; the new field defaults to `None` so existing tests keep their current semantics.
4. **CandidatesMatcher:** one pass over `flat` produces both `result` and `stored_flat`. For `strategy="first"`, dedup-by-`(s,e)` and boundary-filter compose in either order (the check depends only on `(s, e)`), so a single loop is behavior-identical.
5. **Acceptance enforcement:** a unit test scans `paxman/core/**/*.py` for the pattern `==\s*"idna"` and fails if any comparison remains (mirrors the existing CI source-scan style used for `output_format`).

### Test-file conventions in this repo

- New tests go in one module: `tests/unit/test_kernel_stripped_chars.py`, with `pytestmark = pytest.mark.unit`.
- Engine-level tests call `run_matchers_with_context` with a fake grammar: `SimpleNamespace(matchers=[matcher], name="toy")` — the loop only reads `grammar.matchers`.
- Views can be built directly: `View(subject=..., source_starts=..., source_ends=..., _text_len=...)` (the new `stripped_chars` field defaults to `None`).
- `ScannerMatcher` needs a `scan(view, pos) -> (end, notation) | None` callable and a 2-param `emit(span, context)` callable (`validate_emit` enforces the arity at construction).

---

### Task 1: `stripped_chars` data flag on `View`, `ScanContext.view`, `IDNAFold`

**Files:**
- Modify: `paxman/core/grammar/scan_context.py` (View fields + `view()` signature)
- Modify: `paxman/core/grammar/normalizers.py:261-290` (`IDNAFold`)
- Test: `tests/unit/test_kernel_stripped_chars.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_kernel_stripped_chars.py`:

```python
"""Kernel stripped_chars flag — data-driven view stripping (#87, #88).

Covers:
- View/ScanContext carry stripped_chars as data (Task 1)
- engine_loop consumes the flag instead of view_name == "idna" (Task 2)
- boundary re-check ordering before trailing extension (Task 3)
- scanner left-boundary deferral keyed on the flag (Task 4)
- CandidatesMatcher single-pass boundary filter (Task 5)
- acceptance: no `== "idna"` magic-name comparison in paxman/core (Task 6)
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from paxman.core.grammar.engine_loop import _VIEW_REGISTRY, run_matchers_with_context
from paxman.core.grammar.matchers.candidates import CandidatesMatcher, get_flat_for_matcher
from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.normalizers import CaseFold, IDNAFold, StripSeparators
from paxman.core.grammar.scan_context import ScanContext, View

pytestmark = pytest.mark.unit


def test_idnafold_declares_stripped_chars() -> None:
    """IDNAFold strips \\t\\n\\r and must declare it as data."""
    assert IDNAFold().stripped_chars == "\t\n\r"


def test_non_absorbing_normalizers_have_no_stripped_chars() -> None:
    """Normalizers whose stripped chars are never re-absorbed must not set the flag."""
    assert getattr(CaseFold(), "stripped_chars", None) is None
    assert getattr(StripSeparators(), "stripped_chars", None) is None


def test_view_defaults_to_no_stripped_chars() -> None:
    """A View built directly (test-double path) defaults to stripped_chars None."""
    view = View(subject="AB", source_starts=(0, 1), source_ends=(1, 2), _text_len=2)
    assert view.stripped_chars is None


def test_scan_context_view_passes_stripped_chars_through() -> None:
    """ScanContext.view forwards the flag into the cached View."""
    ctx = ScanContext.of("a\tb")
    view = ctx.view("tstrip", IDNAFold().normalize, stripped_chars="\t\n\r")
    assert view.stripped_chars == "\t\n\r"
    assert ctx.view("tstrip", IDNAFold().normalize, stripped_chars="\t\n\r") is view
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: FAIL — `AttributeError`/`AssertionError` (`IDNAFold` has no `stripped_chars`; `View` has no `stripped_chars`; `ScanContext.view` takes no `stripped_chars` kwarg).

- [ ] **Step 3: Implement — `View` field**

In `paxman/core/grammar/scan_context.py`, extend the `View` docstring attributes section and add the field after `_text_len` (frozen slots dataclass: fields with defaults must come last):

```python
    subject: str
    source_starts: tuple[int, ...] | None
    source_ends: tuple[int, ...] | None
    _text_len: int = field(repr=False)
    stripped_chars: str | None = field(default=None, repr=False)
```

And append to the class docstring's Attributes block:

```text
        stripped_chars: Characters the normalizer strips that legacy matchers
            may re-absorb into their emitted spans (e.g. ``"\\t\\n\\r"`` for
            the IDNA view), or ``None`` when the view has no such set.
```

- [ ] **Step 4: Implement — `ScanContext.view` keyword**

In `paxman/core/grammar/scan_context.py`, change the signature and the `View(...)` construction at the end of `view()`:

```python
    def view(
        self,
        name: str,
        normalizer: Callable[
            [str],
            tuple[str, tuple[int, ...] | None]
            | tuple[str, tuple[int, ...] | None, tuple[int, ...] | None],
        ],
        stripped_chars: str | None = None,
    ) -> View:
```

(docstring: add one line — ``stripped_chars: Characters stripped by the normalizer that matchers may re-absorb into spans; recorded on the View.``) and at the bottom of the method:

```python
        view = View(
            subject=subject,
            source_starts=starts,
            source_ends=ends,
            _text_len=len(self.text),
            stripped_chars=stripped_chars,
        )
```

- [ ] **Step 5: Implement — `IDNAFold` field**

In `paxman/core/grammar/normalizers.py`, extend `IDNAFold` (frozen slots dataclass, defaults last) and its docstring:

```python
@dataclass(frozen=True, slots=True)
class IDNAFold:
    """IDNA view: strip ``\\t\\n\\r``.

    The stripped characters are declared as data (``stripped_chars``) so the
    kernel engine loop and scanner can re-absorb trailing stripped chars into
    emitted spans without special-casing the view name.
    """

    name: str = "idna"
    provenance: Provenance | None = Provenance(
        authority="Unicode",
        specification_name="UTS #46",
        kind="specification",
        reference_url="https://unicode.org/reports/tr46/",
        version="31",
        lifecycle="active",
        publication_year=2024,
    )
    stripped_chars: str | None = "\t\n\r"
```

(The `normalize` body is unchanged.)

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: 4 PASS.

- [ ] **Step 7: Run the kernel-related regression suites**

Run: `uv run pytest tests/unit/test_normalizers.py tests/unit/test_boundary_spec.py tests/property/test_scanner_parity.py tests/property/test_url_scanner_parity.py -q`
Expected: all PASS (no behavior change yet — the flag is carried but not consumed).

- [ ] **Step 8: Commit**

```bash
git add paxman/core/grammar/scan_context.py paxman/core/grammar/normalizers.py tests/unit/test_kernel_stripped_chars.py
git commit -m "feat(kernel): carry stripped_chars as data on views (#87)"
```

---

### Task 2: Engine loop consumes the flag for trailing extension

**Files:**
- Modify: `paxman/core/grammar/engine_loop.py` (`_resolve_view` + `_run_matchers_with_context`)
- Test: `tests/unit/test_kernel_stripped_chars.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_kernel_stripped_chars.py`:

```python
class _TabStrip:
    """Test normalizer stripping \\t with offset maps; declares stripped_chars."""

    name = "tstrip"
    provenance = None
    stripped_chars = "\t"

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        chars: list[str] = []
        starts: list[int] = []
        for i, ch in enumerate(text):
            if ch == "\t":
                continue
            chars.append(ch)
            starts.append(i)
        subject = "".join(chars)
        if len(subject) == len(text):
            return subject, None, None
        return subject, tuple(starts), tuple(s + 1 for s in starts)


def _scan_fixed(view: View, pos: int) -> tuple[int, None] | None:
    """Toy scanner: one full-subject hit at pos 0."""
    return (len(view.subject), None) if pos == 0 else None


def _run_engine(text: str, matcher: object) -> list[object]:
    ctx = ScanContext.of(text)
    grammar = SimpleNamespace(matchers=[matcher], name="toy")
    return list(run_matchers_with_context(ctx, [grammar]))


def test_stripped_view_extends_over_trailing_stripped_chars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A view with stripped_chars (any name) gets the trailing extension."""
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    matcher = ScannerMatcher(
        scan=_scan_fixed,
        view_name="tstrip",
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\t", matcher)
    assert [(m.start, m.end, m.raw_text) for m in out] == [(0, 4, "A:0\t")]


def test_unstripped_view_does_not_extend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A normalizer with no stripped_chars gets no trailing extension."""
    monkeypatch.setitem(_VIEW_REGISTRY, "plain", CaseFold())
    matcher = ScannerMatcher(
        scan=_scan_fixed,
        view_name="plain",
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\t", matcher)
    # CaseFold view keeps the tab, so the full-subject hit ends at len 4
    # including the tab — no EXTRA extension happens either way. Assert the
    # span equals the view span exactly (1:1, no re-absorption logic fired).
    assert [(m.start, m.end, m.raw_text) for m in out] == [(0, 4, "A:0\t")]
```

Wait — the second test above is degenerate (identity-length view). Replace it with the real acceptance case: a stripping normalizer **without** the flag must NOT extend. Append instead:

```python
class _TabStripNoFlag(_TabStrip):
    """Same stripping as _TabStrip but WITHOUT the stripped_chars flag."""

    name = "tstrip_noflag"
    stripped_chars = None  # type: ignore[assignment]  # test double


def test_normalizer_without_flag_does_not_extend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip_noflag", _TabStripNoFlag())
    matcher = ScannerMatcher(
        scan=_scan_fixed,
        view_name="tstrip_noflag",
        emit=lambda span, ctx: span,
    )
    out = _run_engine("A:0\t", matcher)
    # The view strips the tab (subject "A:0", len 3) so the span maps to
    # (0, 3); without the flag the engine must NOT re-absorb the tab.
    assert [(m.start, m.end, m.raw_text) for m in out] == [(0, 3, "A:0")]
```

(Delete the degenerate `test_unstripped_view_does_not_extend` — keep only the flag-positive test and this flag-absent test.)

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: `test_stripped_view_extends_over_trailing_stripped_chars` FAIL (engine extends only for `view_name == "idna"`, so span is `(0, 3)`); `test_normalizer_without_flag_does_not_extend` PASS (current magic-string behavior already excludes it).

- [ ] **Step 3: Implement — `_resolve_view` forwards the flag**

In `paxman/core/grammar/engine_loop.py`, replace `_resolve_view`:

```python
def _resolve_view(context: ScanContext, view_name: str | None) -> Any:
    if view_name is None:
        return context.view("__orig__", lambda t: (t, None, None))
    normalizer = _VIEW_REGISTRY.get(view_name)
    if normalizer is not None:
        return context.view(
            view_name,
            normalizer.normalize,
            stripped_chars=getattr(normalizer, "stripped_chars", None),
        )
    return context.view(view_name, lambda t: (t, None, None))
```

- [ ] **Step 4: Implement — extension loop keys on the flag**

In `paxman/core/grammar/engine_loop.py`, inside `_run_matchers_with_context`, replace the idna-gated extension block:

```python
                o_s, o_e = view.original_span(s, e)
                # IDNAFold trailing \t\n\r: legacy body `[^ <>"...]*` allows
                # tab/LF/CR as body chars and includes trailing ones
                # (e.g. 'A:0\n' → 'A:0\n'). The view strips them, so
                # original_span for view 'A:0' is (0,3) not (0,4). Extend
                # to include trailing stripped chars that are allowed.
                if view_name == "idna":
                    while o_e < len(text) and text[o_e] in "\t\n\r":
                        o_e += 1
```

with (boundary handling comes in Task 3 — for now keep the extension only, still placed where it is):

```python
                o_s, o_e = view.original_span(s, e)
                # Trailing stripped chars: legacy matchers on a stripped view
                # (e.g. the URL body `[^ <>"…]*` allowing tab/LF/CR, 'A:0\n'
                # → 'A:0\n') re-absorb the chars the view stripped. Data-
                # driven via view.stripped_chars (#87) — no view-name checks.
                if view.stripped_chars is not None:
                    while o_e < len(text) and text[o_e] in view.stripped_chars:
                        o_e += 1
```

Note: `view_name` is still used for the out-of-bounds error message — leave that usage alone.

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: all PASS (7 total so far: 4 from Task 1 + 2 new + the flag-absent test).

- [ ] **Step 6: Regression check — idna path unchanged**

Run: `uv run pytest tests/property/test_url_scanner_parity.py tests/property/test_hypothesis_view_roundtrip.py tests/unit/test_b1_common_word_suppression.py -q`
Expected: all PASS (idna view still extends: `IDNAFold.stripped_chars == "\t\n\r"`).

- [ ] **Step 7: Commit**

```bash
git add paxman/core/grammar/engine_loop.py tests/unit/test_kernel_stripped_chars.py
git commit -m "feat(kernel): data-driven trailing stripped-char extension (#87)"
```

---

### Task 3: Boundary re-check BEFORE trailing extension (#88)

**Files:**
- Modify: `paxman/core/grammar/engine_loop.py` (`_run_matchers_with_context`)
- Test: `tests/unit/test_kernel_stripped_chars.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_kernel_stripped_chars.py`:

```python
def test_boundary_checked_before_trailing_extension() -> None:
    """(#88) The right guard must see the immediate neighbor (the tab),
    not the char after the stripped run."""
    text = "A:0\tB"
    # idna view: subject "A:0B", the hit (0,3) maps to original (0,3) and
    # the trailing tab is re-absorbable. Right guard forbids the tab, so
    # the pre-extension check must reject the hit.
    matcher = ScannerMatcher(
        scan=lambda view, pos: (3, None) if pos == 0 else None,
        view_name="idna",
        boundary=BoundarySpec(left=None, right=(r"\t",), mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    out = _run_engine(text, matcher)
    assert out == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py::test_boundary_checked_before_trailing_extension -v`
Expected: FAIL — the engine extends `o_e` to 4 first, so `check_boundary(text, 0, 4, spec)` sees `text[4] == "B"` (not the tab), the guard passes, and one match `A:0\t` is emitted.

- [ ] **Step 3: Implement — reorder in `_run_matchers_with_context`**

In `paxman/core/grammar/engine_loop.py`, move the boundary re-check to before the extension and key it on the flag. Replace this sequence:

```python
                o_s, o_e = view.original_span(s, e)
                # Trailing stripped chars: ... (Task 2 block)
                if view.stripped_chars is not None:
                    while o_e < len(text) and text[o_e] in view.stripped_chars:
                        o_e += 1
                # ADR §16 common-word suppression (B1): ... (unchanged block)
                if (
                    contract is not None
                    and bool(getattr(contract, "suppress_common_words", False))
                    and bool(getattr(matcher, "suppressible", False))
                    and text[o_s:o_e].lower() in COMMON_WORDS
                ):
                    continue
                # Boundary check on original for IDNAFold (stripped \t\n\r).
                # Scanner defers for view_name=="idna"; SeparatorFold
                # (BCP47 '_'->'-') keeps view check ('-' not \w, so AA_→AA passes).
                boundary = getattr(matcher, "boundary", None)
                if (
                    view_name == "idna"
                    and boundary is not None
                    and not check_boundary(text, o_s, o_e, boundary)
                ):
                    continue
```

with:

```python
                o_s, o_e = view.original_span(s, e)
                boundary = getattr(matcher, "boundary", None)
                # Boundary re-check on the original text at the PRE-extension
                # end (#88): the right guard must see the immediate neighbor,
                # not the char after any re-absorbed stripped run. Scanner
                # defers its view-level check for stripped views; SeparatorFold
                # (BCP47 '_'->'-') keeps its view check ('-' not \w, so
                # AA_→AA passes).
                if (
                    view.stripped_chars is not None
                    and boundary is not None
                    and not check_boundary(text, o_s, o_e, boundary)
                ):
                    continue
                # Trailing stripped chars: legacy matchers on a stripped view
                # (e.g. the URL body `[^ <>"…]*` allowing tab/LF/CR, 'A:0\n'
                # → 'A:0\n') re-absorb the chars the view stripped. Data-
                # driven via view.stripped_chars (#87) — no view-name checks.
                if view.stripped_chars is not None:
                    while o_e < len(text) and text[o_e] in view.stripped_chars:
                        o_e += 1
                # ADR §16 common-word suppression (B1): short-code matchers marked
                # suppressible are skipped when contract requests it and the
                # word-bounded hit is a high-frequency English function word.
                # Provenance-neutral: suppressed recognition never canonicalizes.
                if (
                    contract is not None
                    and bool(getattr(contract, "suppress_common_words", False))
                    and bool(getattr(matcher, "suppressible", False))
                    and text[o_s:o_e].lower() in COMMON_WORDS
                ):
                    continue
```

(The `# ADR §10 consuming-mode` no-op block that follows stays where it is, unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: all PASS (8 total).

- [ ] **Step 5: Regression check**

Run: `uv run pytest tests/property/test_url_scanner_parity.py tests/property/test_hypothesis_view_roundtrip.py tests/unit/test_b1_common_word_suppression.py tests/unit/test_coverage_extra.py -q`
Expected: all PASS (every shipped idna-view boundary is left-only, so checking before extension is behavior-identical for them).

- [ ] **Step 6: Commit**

```bash
git add paxman/core/grammar/engine_loop.py tests/unit/test_kernel_stripped_chars.py
git commit -m "fix(kernel): boundary re-check precedes stripped-char extension (#88)"
```

---

### Task 4: Scanner deferral keyed on the flag; remove remaining magic strings

**Files:**
- Modify: `paxman/core/grammar/matchers/scanner.py` (`ScannerMatcher.match` + docstring/comments)
- Modify: `paxman/core/grammar/engine_loop.py` (only if any `view_name == "idna"` comment/comparison remains — none should after Task 3)
- Test: `tests/unit/test_kernel_stripped_chars.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_kernel_stripped_chars.py`:

```python
def _gap_view(stripped: str | None) -> View:
    """View over a 5-char original whose subject 'AB' has a gap before 'B'.

    source maps: 'A' -> [0,1), 'B' -> [3,4); original index 1..2 hold the
    stripped char(s). pos=1 (the 'B' hit) therefore has a stripped gap to
    its left: source_starts[1]=3 != source_ends[0]=1.
    """
    return View(
        subject="AB",
        source_starts=(0, 3),
        source_ends=(1, 4),
        _text_len=5,
        stripped_chars=stripped,
    )


def _scan_at_one(view: View, pos: int) -> tuple[int, None] | None:
    return (2, None) if pos == 1 else None


def test_scanner_defers_left_guard_when_stripped_chars_set() -> None:
    """Gap to the left + stripped_chars set → view-level left check deferred."""
    matcher = ScannerMatcher(
        scan=_scan_at_one,
        boundary=BoundarySpec(left=("A",), right=None, mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    # View-level check would see subject[0] == 'A' (forbidden) and reject;
    # the deferral keys on view.stripped_chars, not the view name.
    assert matcher.match(_gap_view("\t")) == [(1, 2)]


def test_scanner_checks_left_guard_without_stripped_chars() -> None:
    """Same gap, no stripped_chars → deferral must NOT apply."""
    matcher = ScannerMatcher(
        scan=_scan_at_one,
        boundary=BoundarySpec(left=("A",), right=None, mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    assert matcher.match(_gap_view(None)) == []


def test_engine_boundary_recheck_is_data_driven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Engine re-checks the original text for ANY stripped view (not just idna)."""
    monkeypatch.setitem(_VIEW_REGISTRY, "tstrip", _TabStrip())
    # text "a\tb:0": view strips the tab → subject "ab:0"; hit (1,4) maps to
    # original (2,5) whose LEFT neighbor text[1] is the stripped tab. The
    # left guard forbids the tab, so the engine-level re-check must reject.
    matcher = ScannerMatcher(
        scan=lambda view, pos: (4, None) if pos == 1 else None,
        view_name="tstrip",
        boundary=BoundarySpec(left=(r"\t",), right=None, mode="zero_width"),
        emit=lambda span, ctx: span,
    )
    assert _run_engine("a\tb:0", matcher) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: `test_scanner_defers_left_guard_when_stripped_chars_set` FAIL — the deferral is gated on `self.view_name == "idna"` and this matcher has no view name, so the view-level check fires on `'A'` and returns `[]`. The other two PASS (they pin behavior that must not regress).

- [ ] **Step 3: Implement — scanner branches on the flag**

In `paxman/core/grammar/matchers/scanner.py`, replace the boundary block in `match`:

```python
                if self.boundary is not None:
                    if (
                        self.view_name == "idna"
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and pos > 0
                        and view.source_starts[pos] != view.source_ends[pos - 1]
                    ):
```

with:

```python
                if self.boundary is not None:
                    if (
                        view.stripped_chars is not None
                        and view.source_starts is not None
                        and view.source_ends is not None
                        and pos > 0
                        and view.source_starts[pos] != view.source_ends[pos - 1]
                    ):
```

and update the comment above it:

```python
                # Boundary check at hit positions (O(hits), not O(positions)).
                # On a stripped view the subject's left char may not be the
                # original left char: if there's a gap between pos and pos-1
                # in the original (a stripped char), the original left char
                # is a stripped char, which the engine re-checks on the
                # original text — so the view-level check is deferred here.
                # Otherwise the view check is accurate.
```

Also update the module docstring's mention of the deferral if it names `idna` (it currently describes bounds/boundary enforcement generically — leave it unless it contains the literal view name).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: all PASS (11 total).

- [ ] **Step 5: Full parity regression**

Run: `uv run pytest tests/property tests/unit/test_b1_common_word_suppression.py tests/unit/test_coverage_extra.py -q`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add paxman/core/grammar/matchers/scanner.py tests/unit/test_kernel_stripped_chars.py
git commit -m "refactor(kernel): scanner boundary deferral keyed on stripped_chars (#87)"
```

---

### Task 5: CandidatesMatcher single-pass boundary filter (#68)

**Files:**
- Modify: `paxman/core/grammar/matchers/candidates.py:178-213` (`match`)
- Test: `tests/unit/test_kernel_stripped_chars.py`

- [ ] **Step 1: Write the failing/pinning tests**

The refactor is behavior-preserving; first pin the invariant `result == [(s, e) for s, e, _ in stored_flat]` (which holds before AND after — these tests guard against divergence) plus boundary filtering:

```python
class _FakeCandidate:
    """Minimal candidate double: frozen spans, pass-through emit."""

    digest = "fake-candidate"

    def __init__(self, spans: tuple[tuple[int, int], ...]) -> None:
        self._spans = spans

    def match(self, view: View) -> list[tuple[int, int]]:
        return list(self._spans)

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        return span


def _result_flat_pair(m: CandidatesMatcher) -> tuple[list[tuple[int, int]], list[tuple[int, int, int]]]:
    spans = m.match(ScanContext.of("a1b").view("orig", lambda t: (t, None, None)))
    return spans, get_flat_for_matcher(m)


def test_candidates_boundary_filter_all_strategy() -> None:
    """strategy=all: boundary-filtered spans, flat mirrors result exactly."""
    m = CandidatesMatcher(
        candidates=(_FakeCandidate(((2, 3),)), _FakeCandidate(((0, 1),))),
        strategy="all",
        boundary=BoundarySpec(left=(r"\d",), right=None, mode="zero_width"),
    )
    spans, flat = _result_flat_pair(m)
    # span (2,3) 'b' has left neighbor '1' (digit) → filtered out.
    assert spans == [(0, 1)]
    assert [(s, e) for s, e, _ in flat] == spans


def test_candidates_boundary_filter_first_strategy() -> None:
    """strategy=first: dedup + boundary filter compose; flat mirrors result."""
    m = CandidatesMatcher(
        candidates=(_FakeCandidate(((2, 3), (0, 1), (0, 1))),),
        strategy="first",
        boundary=BoundarySpec(left=(r"\d",), right=None, mode="zero_width"),
    )
    spans, flat = _result_flat_pair(m)
    assert spans == [(0, 1)]
    assert [(s, e) for s, e, _ in flat] == spans
```

- [ ] **Step 2: Run tests to verify they pass (pinning) BEFORE the refactor**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -k candidates -v`
Expected: 2 PASS (these pin current behavior; if either fails, STOP — the refactor premise is wrong).

- [ ] **Step 3: Implement — single pass**

In `paxman/core/grammar/matchers/candidates.py`, replace the block from `result: list[tuple[int, int]] = []` through the end of the `stored_flat` build (the two boundary-filter loops):

```python
        result: list[tuple[int, int]] = []
        if self.strategy == "first":
            seen: set[tuple[int, int]] = set()
            for s, e, _ in flat:
                key = (s, e)
                if key not in seen:
                    seen.add(key)
                    result.append((s, e))
        else:
            for s, e, _ in flat:
                result.append((s, e))
        if self.boundary is not None:
            filtered: list[tuple[int, int]] = []
            for s, e in result:
                if check_boundary(view.subject, s, e, self.boundary):
                    filtered.append((s, e))
            result = filtered
        if self.strategy == "first":
            seen2: set[tuple[int, int]] = set()
            stored_flat: list[tuple[int, int, int]] = []
            for s, e, idx in flat:
                if (s, e) not in seen2:
                    if self.boundary is not None and not check_boundary(
                        view.subject, s, e, self.boundary
                    ):
                        continue
                    seen2.add((s, e))
                    stored_flat.append((s, e, idx))
        else:
            stored_flat = []
            for s, e, idx in flat:
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                stored_flat.append((s, e, idx))
```

with a single pass (boundary check runs exactly once per span; dedup and filter compose inline for "first"):

```python
        result: list[tuple[int, int]] = []
        stored_flat: list[tuple[int, int, int]] = []
        if self.strategy == "first":
            # Dedup by (s, e) and boundary-filter compose: the boundary
            # verdict depends only on (s, e), so filtering the deduped
            # stream equals deduping the filtered stream (#68).
            seen: set[tuple[int, int]] = set()
            for s, e, idx in flat:
                key = (s, e)
                if key in seen:
                    continue
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                seen.add(key)
                result.append(key)
                stored_flat.append((s, e, idx))
        else:
            for s, e, idx in flat:
                if self.boundary is not None and not check_boundary(
                    view.subject, s, e, self.boundary
                ):
                    continue
                result.append((s, e))
                stored_flat.append((s, e, idx))
```

- [ ] **Step 4: Run tests to verify they still pass**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -k candidates -v`
Expected: 2 PASS (unchanged behavior).

- [ ] **Step 5: Regression — candidates customers**

Run: `uv run pytest tests/unit/test_candidates_date_red.py tests/unit/test_candidates_label.py tests/property/test_combinator_parity.py tests/property/test_combinator_red_golden.py -q`
Expected: all PASS (Date 4→1 is the shipped CandidatesMatcher customer).

- [ ] **Step 6: Commit**

```bash
git add paxman/core/grammar/matchers/candidates.py tests/unit/test_kernel_stripped_chars.py
git commit -m "refactor(kernel): single-pass boundary filter in CandidatesMatcher (#68)"
```

---

### Task 6: Acceptance source-scan, docs, CHANGELOG, full gate

**Files:**
- Test: `tests/unit/test_kernel_stripped_chars.py`
- Modify: `CHANGELOG.md` (Unreleased section)
- Modify: `paxman/core/AGENTS.md` (kernel invariants list)
- Modify: `paxman/core/grammar/matchers/scanner.py` (module docstring, if it still names the idna deferral)

- [ ] **Step 1: Write the acceptance source-scan test**

Append to `tests/unit/test_kernel_stripped_chars.py`:

```python
def test_no_magic_idna_view_name_comparison_in_core() -> None:
    """(#87 acceptance) No `== "idna"` comparison remains in paxman/core."""
    import re
    from pathlib import Path

    core = Path(__file__).resolve().parents[2] / "paxman" / "core"
    offenders: list[str] = []
    for path in sorted(core.rglob("*.py")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if re.search(r'==\s*"idna"', line):
                offenders.append(f"{path.relative_to(core)}:{lineno}: {line.strip()}")
    assert offenders == [], "magic view-name comparison(s) found:\n" + "\n".join(
        offenders
    )
```

- [ ] **Step 2: Run the acceptance test**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py::test_no_magic_idna_view_name_comparison_in_core -v`
Expected: PASS (Tasks 2-4 removed all three comparisons; if it FAILS, an occurrence was missed — remove it, re-run Task 2-5 tests, then continue).

- [ ] **Step 3: Update `paxman/core/AGENTS.md` kernel invariants**

In the `### Kernel invariants (ADR-0009)` list, replace the bullet:

```markdown
- `CountryNameFold` single-pass NFD with `_NFD_CACHE` — one-pass fold, cached.
```

with (keeping that bullet and adding one after it):

```markdown
- `CountryNameFold` single-pass NFD with `_NFD_CACHE` — one-pass fold, cached.
- Views carry `stripped_chars` as data — engine loop + scanner branch on
  `view.stripped_chars is not None`, never on view names (`view_name == "idna"`
  is banned; source-scanned in `tests/unit/test_kernel_stripped_chars.py`).
```

- [ ] **Step 4: Update `CHANGELOG.md`**

Under `## [Unreleased]`, add:

```markdown
## [Unreleased]

### Fixed

- **Kernel — data-driven stripped-view handling (#87, #88):** the recognition kernel no
  longer special-cases the idna view by name. Views carry `stripped_chars` as data
  (`IDNAFold` declares `"\t\n\r"`), and the engine loop / scanner branch on
  `view.stripped_chars is not None`. Community grammars using other stripped views now
  get the same re-absorption and boundary-deferral semantics, and views without the flag
  get neither. The boundary re-check on the original text now runs at the pre-extension
  end, so a right-side guard sees the immediate neighbor instead of the character after
  a re-absorbed stripped run (#88). No shipped capability changes behavior (parity suites
  green).

### Changed

- **Kernel — `CandidatesMatcher` single-pass boundary filter (#68):** `result` and
  `stored_flat` are now derived in one pass; `check_boundary` runs once per span instead
  of twice. No behavior change.
```

- [ ] **Step 5: Run the new test module in full**

Run: `uv run pytest tests/unit/test_kernel_stripped_chars.py -v`
Expected: 12 PASS.

- [ ] **Step 6: Run the full pre-PR gate**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q`
Expected: all green — ruff clean, format clean, pyright strict clean (0 errors), import-linter contracts respected, full suite PASS with coverage ≥ 95%.

- [ ] **Step 7: Commit and push**

```bash
git add tests/unit/test_kernel_stripped_chars.py CHANGELOG.md paxman/core/AGENTS.md paxman/core/grammar/matchers/scanner.py
git commit -m "test(kernel): ban magic view-name comparisons; docs + changelog (#87)"
git push -u origin fix/grammar-kernel-hardening
```

- [ ] **Step 8: Open the PR**

```bash
gh pr create --base dev --title "fix(kernel): data-driven stripped views, boundary ordering, candidates DRY" --body "$(cat <<'EOF'
Resolves #87, resolves #88, resolves #68.

## What
- Views carry `stripped_chars` as data (`IDNAFold` → `"\t\n\r"`); engine loop and
  scanner branch on the flag instead of `view_name == "idna"` (#87).
- Boundary re-check on the original text runs at the pre-extension end so right-side
  guards see the immediate neighbor, not the char after a re-absorbed run (#88).
- `CandidatesMatcher` builds `result`/`stored_flat` in one pass; `check_boundary`
  runs once per span (#68).

## Verification
- New `tests/unit/test_kernel_stripped_chars.py` (12 tests) incl. a source-scan
  banning `== "idna"` in `paxman/core`.
- Full gate green: ruff, ruff format, pyright (strict), import-linter, pytest
  (parity suites `test_url_scanner_parity`, `test_hypothesis_view_roundtrip`,
  `test_combinator_parity`, E.164 property tests all green).
- No shipped capability behavior change.
EOF
)"
```

---

## Self-review notes (spec ↔ plan)

- #87 acceptance 1 ("no magic comparison in paxman/core") → Task 6 Step 1-2. ✔
- #87 acceptance 2 ("normalizer with no stripped_chars gets neither behavior") → Task 2 Step 1 (flag-absent extension test) + Task 4 Step 1 (no-deferral test). ✔
- #87 acceptance 3 ("property + unit suites green, esp. url scanner parity / view roundtrip") → regression steps in Tasks 2-4 + full gate in Task 6. ✔
- #88 acceptance 1 ("check_boundary sees pre-extend span") → Task 3. ✔
- #88 acceptance 2 ("unit test: right guard + trailing tab proves ordering") → Task 3 Step 1. ✔
- #88 acceptance 3 ("parity suites green") → Task 3 Step 5. ✔
- #68 ("derive stored_flat from result, no behavior change, DRY") → Task 5 (single pass; pinning tests first). ✔
- Plan-wide TDD order, bite-sized steps, exact paths/commands: ✔
