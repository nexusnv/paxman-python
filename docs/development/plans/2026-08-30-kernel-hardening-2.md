# Kernel Hardening II Implementation Plan (issues #66, #67, #62, #63, #64)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five remaining kernel-hardening findings: restore the grammar-path error contract (#66), make `BoundarySpec` reject negated bracket classes instead of mis-lowering them (#67), make the boundary char sets exact vs `re` for non-BMP neighbors and Unicode digits (#62), pin the no-expansion invariant in `NormalizerSequence` (#63), and bound the NFD cache (#64).

**Architecture:** #66 adds `LookupError` to the existing narrow exception tuples (orchestrator grammar paths, `CandidatesMatcher` per-candidate, `CombinatorMatcher` per-leaf + predicate) so internal data bugs surface as `RecognitionError`, never as raw `KeyError`/`IndexError`. #67 is a two-line guard in `_pattern_to_chars`. #62 introduces an internal `_pattern_lowering(pat) -> (chars, fallback)` that pairs the BMP char set with the compiled escape (`\w`/`\d`/`\s`); `check_boundary` consults the fallback only for non-BMP neighbors (`ord(ch) > 0xFFFF`) where the BMP scan cannot see — the public `_pattern_to_chars` keeps its `frozenset | None` contract. #63 documents + asserts the unit-width offset invariant. #64 replaces the unbounded `_NFD_CACHE` dict with `functools.lru_cache(maxsize=8192)` on a per-char helper.

**Tech Stack:** Python 3.11+, pytest (`unit`, `integration`, `property` markers), strict pyright, ruff, import-linter, uv.

**References:** #66, #67, #62, #63, #64. Branch: `fix/kernel-boundary-normalizer-hardening` (cut from updated `dev`, post-#98).

---

## Background the implementer needs

### Verified facts (controller-measured — trust these, they save you an hour)

1. **Python `re`'s `\w` ≡ `isalnum() ∪ {"_"}` EXACTLY.** Measured: combining mark U+0301 → `re \w` NO and `isalnum()` False; superscript `²` (No) → both YES; Deseret U+10400 and math U+1D400 (non-BMP) → both YES. So the current set-builder predicate `chr(c) == "_" or chr(c).isalnum()` is **correct**; the ONLY defect is `range(0x10000)` (BMP-only). 88,857 supplementary-plane word chars exist — far too many to build eagerly (full-range build measures **0.49 s**; unacceptable at import). Hence: keep the BMP frozenset, add a **non-BMP regex fallback**.
2. **`re`'s `\d` = Unicode category `Nd` exactly.** Measured: `³` U+0663 (Nd) → match; `²` (No) → no match; math digit U+1D7CE (Nd, non-BMP) → match. The current `_D_CHARS = frozenset("0123456789")` misses **370 BMP Nd digits** (Arabic-Indic, full-width, Devanagari, …) — a real parity break vs the legacy regex path. Fix: BMP scan on `unicodedata.category(ch) == "Nd"` + non-BMP fallback. (310 supplementary Nd digits exist.)
3. **`re`'s `\s` ≡ `str.isspace()` on the BMP** (0 mismatches measured) and **0 supplementary whitespace chars exist**, so `_S_CHARS` is already exact; it still gets the fallback mechanism for uniformity (zero cost when the tuple is empty).
4. **`UnicodeError ⊂ ValueError` and `RecursionError ⊂ RuntimeError`** — both already covered by the existing tuples. The only real gaps in the post-`1ed7a5a` narrowing are **`KeyError` and `IndexError`**, i.e. the `LookupError` family.
5. **`paxman/api/scan.py` delegates to `run_scan` in the orchestrator** — no separate error path to fix for #66.
6. `_pattern_to_chars` / `_chars_from_bracket` are pinned by `tests/unit/test_coverage_remediation.py:608-635` with the `frozenset | None` contract — **do not change their signatures**; add a new internal lowering function instead.
7. Current negated-class bug: `_chars_from_bracket("^a-z")` treats `^` as a literal char, so `BoundarySpec(left=("[^a-z]",))` would build a positive set containing `^`,`a`…`z` and reject neighbors IN a-z — exactly inverted semantics (#67).
8. The negated fragment falling to the multi/regex path is **semantically correct**: `_estimate_width("[^a-z]") == 1`, compiled as `"[^a-z]\Z"` (left) / `"\A[^a-z]"` (right), matched against the 1-char neighbor window — regex negation does the right thing.

### Current code state (relevant excerpts)

`paxman/engine/orchestrator.py` — two grammar-path exception tuples (lines ~304 and ~320), both currently:
```python
            except (
                re.error,
                ValueError,
                TypeError,
                AttributeError,
                RuntimeError,
                AssertionError,
            ) as exc:
                raise RecognitionError(
                    rule=grammar.name,
                    message=f"Grammar failed: {exc}",
                    original_error=exc,
                ) from exc
```
(The rules path `_collect_candidates` at ~579 keeps `except Exception -> ValidationError` — leave it.)

`paxman/core/grammar/matchers/candidates.py` — per-candidate swallow (~line 162):
```python
            except (
                re.error,
                ValueError,
                TypeError,
                AttributeError,
                RuntimeError,
            ):
                spans = cast(list[tuple[int, int]], [])
```

`paxman/core/grammar/matchers/combinator.py` — per-leaf swallow (~line 228) and predicate guard (~line 255), same 5-tuple; the predicate one wraps `ok = self.predicate(subj[pos:end], subj)`.

`paxman/core/grammar/boundary_spec.py` — `_W_CHARS`/`_D_CHARS`/`_S_CHARS` at lines 12-16; `_chars_from_bracket` (19-55); `_pattern_to_chars` (58-74); `BoundarySpec.__post_init__` (134-158) loops `chars = _pattern_to_chars(pat)`; `check_boundary` (178-215) does `if spec.left_chars is not None and subject[start - 1] in spec.left_chars: return False` (and the right-side mirror).

`paxman/core/grammar/normalizers.py` — `NormalizerSequence.normalize` (40-65) composes with
```python
                    composed_starts = tuple(cur_starts[o] for o in off_starts)
                    composed_ends = tuple(
                        cur_ends[o - 1] if o > 0 else cur_ends[0] for o in off_ends
                    )
```
and `_NFD_CACHE: dict[str, str] = {}` (line ~132) used inside `CountryNameFold.normalize` (`cached = _NFD_CACHE.get(ch); if cached is None: cached = unicodedata.normalize("NFD", ch); _NFD_CACHE[ch] = cached`).

### Conventions
- `uv run` only; pyright strict + ruff (`paxman/ tests/`) + import-linter clean; **no `# type: ignore` / `# noqa` in `paxman/`** (tests: `# type: ignore[misc]` only).
- TDD; `paxman/` functions all carry docstrings (CodeRabbit gates on it); asserts are acceptable kernel invariants (`scan_context.py` precedent).
- New unit tests: `tests/unit/test_kernel_hardening.py` (`pytestmark = pytest.mark.unit`); the #66 integration wrap test goes in `tests/integration/test_grammar_error_wrapping.py` (autouse `_clean_registry` fixture exists there).

---

### Task 1: Error contract — grammar-path failures wrap into `RecognitionError` (#66)

**Files:**
- Modify: `paxman/engine/orchestrator.py` (two grammar-path tuples)
- Modify: `paxman/core/grammar/matchers/candidates.py` (per-candidate tuple)
- Modify: `paxman/core/grammar/matchers/combinator.py` (per-leaf + predicate tuples)
- Test: `tests/unit/test_kernel_hardening.py` (create), `tests/integration/test_grammar_error_wrapping.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `tests/unit/test_kernel_hardening.py`:

```python
"""Kernel hardening II — error contract, boundary parity, invariants (#66-#64).

Coverage:

- grammar-path errors wrap into RecognitionError, never raw KeyError/IndexError (#66)
- BoundarySpec negated bracket classes fall back to the regex path (#67)
- boundary char sets exact vs re for non-BMP neighbors and Unicode Nd digits (#62)
- NormalizerSequence no-expansion invariant pinned (#63)
- NFD per-char cache bounded (#64)
"""

from __future__ import annotations

import pytest

from paxman.core.grammar.matchers.combinator import CombinatorMatcher
from paxman.core.grammar.matchers.candidates import CandidatesMatcher
from paxman.core.grammar.scan_context import ScanContext, View

pytestmark = pytest.mark.unit


class _ExplodingCandidate:
    """Candidate double whose match() raises KeyError (data-bug shape)."""

    digest = "exploding-candidate"

    def match(self, view: View) -> list[tuple[int, int]]:
        raise KeyError("missing token table entry")

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        return span


class _ExplodingLeaf:
    """Combinator leaf double whose match() raises IndexError."""

    def match(self, view: View) -> list[tuple[int, int]]:
        raise IndexError("offset map out of range")

    def emit(self, span: tuple[int, int], ctx: object) -> tuple[int, int]:
        return span


def test_candidates_swallows_key_error_from_candidate() -> None:
    """(#66) A candidate raising KeyError yields no spans, not a raw crash."""
    m = CandidatesMatcher(candidates=(_ExplodingCandidate(),), strategy="all")
    view = ScanContext.of("ab").view("orig", lambda t: (t, None, None))
    assert m.match(view) == []


def test_combinator_swallows_index_error_from_leaf() -> None:
    """(#66) A combinator leaf raising IndexError yields no spans."""
    m = CombinatorMatcher(expr=("leaf", _ExplodingLeaf()))
    view = ScanContext.of("ab").view("orig", lambda t: (t, None, None))
    assert m.match(view) == []
```

NOTE: verify the combinator expr shape — read `_collect_leaves` in `paxman/core/grammar/matchers/combinator.py` first and construct the leaf however leaves are actually collected (e.g. `("seq", [leaf])` or a bare object in a tuple tree); adapt the test to the real expr vocabulary so the leaf's `match` is actually invoked. If leaves are invoked via `lf.match(view)` any object works.

Then create `tests/integration/test_grammar_error_wrapping.py` (model the fake grammar + registration on the existing `tests/integration/test_grammar_extensions.py` patterns — read it first; reuse its fixture/registry conventions and NOTATION/contract types):

```python
"""Grammar-path error contract: internal errors wrap as RecognitionError (#66)."""

from __future__ import annotations

import pytest

from paxman.api.canonicalize import canonicalize
from paxman.core.discovery import register_grammar
from paxman.core.errors import RecognitionError


class _ExplodingGrammar:
    """Community grammar whose recognize raises KeyError (data-bug shape)."""

    name = "exploding_recognition"
    semantics = "exploding_recognition"

    def recognize(self, text: str) -> list:
        raise KeyError("missing token table entry")


@pytest.mark.integration
def test_grammar_key_error_wraps_as_recognition_error() -> None:
    """(#66) A grammar raising KeyError surfaces as RecognitionError."""
    register_grammar("date", _ExplodingGrammar)
    contract = DateContractWithExtra()  # see note
    with pytest.raises(RecognitionError):
        canonicalize("2024-01-01", contract)
```

NOTE for the implementer: `DateContractWithExtra` is a placeholder — look at `tests/integration/test_grammar_extensions.py:186-215`: it does `register_grammar("date", DotDateGrammar)` then `DateContract(extra_grammars=("dot_date_recognition",))`. Mirror that exactly: import the real `DateContract` from wherever that test imports it, register `_ExplodingGrammar` with the SAME grammar-name convention it uses, and build the contract with `extra_grammars=("exploding_recognition",)`. Also add a second test where the grammar's `matchers` list raises (fake matcher object with a `match` that raises `IndexError`) to cover the compiled path (orchestrator's `run_matchers_with_context` wrap) — a `SimpleNamespace(matchers=[bad_matcher], name="exploding")` registered the same way works since the orchestrator reads `grammar.matchers`. Both must raise `RecognitionError`, NOT `KeyError`/`IndexError`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_kernel_hardening.py tests/integration/test_grammar_error_wrapping.py -v`
Expected: FAIL — `KeyError: 'missing token table entry'` / `IndexError` propagate raw instead of being swallowed (unit) / wrapped (integration).

- [ ] **Step 3: Implement — add `LookupError` to the four tuples**

- `paxman/engine/orchestrator.py`: add `LookupError,` to BOTH grammar-path except tuples (~304, ~320).
- `paxman/core/grammar/matchers/candidates.py`: add `LookupError,` to the per-candidate match tuple (~162).
- `paxman/core/grammar/matchers/combinator.py`: add `LookupError,` to the per-leaf tuple (~228) AND the predicate tuple (~255).

Do NOT touch `_resolve_version` (orchestrator ~55) or `_collect_candidates` (`except Exception` → ValidationError at ~579 — intentional per issue).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_hardening.py tests/integration/test_grammar_error_wrapping.py -v`
Expected: all PASS.

- [ ] **Step 5: Regression**

Run: `uv run pytest tests/unit -q tests/property/test_combinator_parity.py -q`
Expected: green.

- [ ] **Step 6: Commit**

```bash
git add paxman/engine/orchestrator.py paxman/core/grammar/matchers/candidates.py paxman/core/grammar/matchers/combinator.py tests/unit/test_kernel_hardening.py tests/integration/test_grammar_error_wrapping.py
git commit -m "fix(kernel): grammar-path LookupError wraps as RecognitionError (#66)"
```

---

### Task 2: Negated bracket classes fall back to the regex path (#67)

**Files:**
- Modify: `paxman/core/grammar/boundary_spec.py` (`_pattern_to_chars`)
- Test: `tests/unit/test_kernel_hardening.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_kernel_hardening.py`:

```python
from paxman.core.grammar.boundary_spec import BoundarySpec, _pattern_to_chars, check_boundary


def test_negated_bracket_class_not_lowered_to_positive_set() -> None:
    """(#67) '[^...]' must fall back to the regex path, not become a set."""
    assert _pattern_to_chars("[^a-z]") is None
    # escaped caret is a literal member, NOT negation
    lowered = _pattern_to_chars(r"[\^a]")
    assert lowered is not None and "^" in lowered and "a" in lowered


def test_negated_bracket_class_regex_semantics() -> None:
    """(#67) A negated left guard fires when the neighbor is NOT in the set."""
    spec = BoundarySpec(left=("[^0-9]",), right=None, mode="zero_width")
    # neighbor 'a' is NOT a digit → the negated guard fires → boundary fails.
    assert check_boundary("xa", 1, 2, spec) is False
    # neighbor '5' IS a digit → guard does not fire → boundary passes.
    assert check_boundary("x5", 1, 2, spec) is True
```

Careful with `check_boundary` semantics: a `left` entry is a fragment that must NOT match the adjacent char; `check_boundary` returns True when no guard fires. With `left=("[^0-9]",)` the guard fires when the neighbor is a non-digit. Confirm the exact boolean direction by reading `check_boundary` before asserting — adjust the test if the direction reads differently (the assertions above encode: neighbor 'a' → False, neighbor '5' → True).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -k negated -v`
Expected: FAIL — `_pattern_to_chars("[^a-z]")` currently returns a positive frozenset containing `^` and letters; the regex-semantics test fails with inverted booleans.

- [ ] **Step 3: Implement**

In `paxman/core/grammar/boundary_spec.py`, inside `_pattern_to_chars`, after computing `interior = pat[1:-1]` and the quantifier guard, add:

```python
        # Negated class: a positive char set would invert the guard
        # semantics (#67). Fall back to the compiled regex path, where
        # '[^...]' keeps its negated meaning against the 1-char window.
        if interior.startswith("^"):
            return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -v`
Expected: all PASS (Task 1 + Task 2 tests).

- [ ] **Step 5: Regression**

Run: `uv run pytest tests/unit/test_boundary_spec.py tests/unit/test_coverage_remediation.py tests/property -q`
Expected: green (no shipped BoundarySpec uses negated classes, so behavior is unchanged).

- [ ] **Step 6: Commit**

```bash
git add paxman/core/grammar/boundary_spec.py tests/unit/test_kernel_hardening.py
git commit -m "fix(kernel): negated bracket classes fall back to regex path (#67)"
```

---

### Task 3: Boundary char sets exact vs `re` — non-BMP fallback + Unicode Nd digits (#62)

**Files:**
- Modify: `paxman/core/grammar/boundary_spec.py` (`_W_CHARS`/`_D_CHARS`, new `_pattern_lowering`, `BoundarySpec` fields, `check_boundary`)
- Modify: `paxman/core/AGENTS.md` (kernel invariant bullet)
- Test: `tests/unit/test_kernel_hardening.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/unit/test_kernel_hardening.py`:

```python
from paxman.core.grammar.boundary_spec import (
    _D_CHARS,
    _pattern_lowering,
)


def test_digit_chars_cover_bmp_nd_category() -> None:
    """(#62) '\\d' lowers to Unicode Nd, not ASCII — Arabic-Indic digits fire."""
    assert _D_CHARS is not None and "\u0663" in _D_CHARS  # ٣ Arabic-Indic three
    assert "\u00b2" not in _D_CHARS  # superscript two is No, re \d rejects it
    assert _D_CHARS == frozenset(
        chr(c) for c in range(0x10000) if __import__("unicodedata").category(chr(c)) == "Nd"
    )


def test_non_bmp_word_neighbor_fires_word_guard() -> None:
    """(#62) Non-BMP word chars (Deseret) fire \\w guards via the fallback."""
    spec = BoundarySpec(left=(r"\w",), right=None, mode="zero_width")
    # U+10400 DESERET LETTER — isalnum() True, re \w matches, BMP scan misses it.
    assert check_boundary("a\U00010400", 1, 2, spec) is False


def test_non_bmp_digit_neighbor_fires_digit_guard() -> None:
    """(#62) Non-BMP Nd digits (math digits) fire \\d guards via the fallback."""
    spec = BoundarySpec(left=(r"\d",), right=None, mode="zero_width")
    assert check_boundary("a\U0001D7CE", 1, 2, spec) is False


def test_non_bmp_non_word_neighbor_passes_word_guard() -> None:
    """(#62) Non-BMP non-word chars do NOT fire \\w guards."""
    spec = BoundarySpec(left=(r"\w",), right=None, mode="zero_width")
    # U+1F600 emoji — not alnum, re \w does not match → guard stays silent.
    assert check_boundary("a\U0001F600", 1, 2, spec) is True


def test_pattern_lowering_pairs_sets_with_fallbacks() -> None:
    """(#62) Class escapes carry compiled fallbacks; enumerations do not."""
    w_chars, w_fb = _pattern_lowering(r"\w")
    d_chars, d_fb = _pattern_lowering(r"\d")
    s_chars, s_fb = _pattern_lowering(r"\s")
    assert w_fb is not None and d_fb is not None and s_fb is not None
    assert w_chars is not None and d_chars is not None and s_chars is not None
    b_chars, b_fb = _pattern_lowering("[abc]")
    assert b_fb is None and b_chars == frozenset({"a", "b", "c"})
    assert _pattern_lowering("abc") == (None, None)
```

NOTE: the `__import__("unicodedata")` inline in the first test is ugly — instead add `import unicodedata` at the top of the module and write the comprehension with it. Final test asserts the tuple shape of the new internal lowering function.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -k "digit_chars or non_bmp or lowering" -v`
Expected: FAIL — `_D_CHARS` lacks `\u0663`; non-BMP neighbors don't fire guards; `_pattern_lowering` doesn't exist (`ImportError`).

- [ ] **Step 3: Implement — `_pattern_lowering` + BoundarySpec fallback fields**

In `paxman/core/grammar/boundary_spec.py`:

1. Add imports and compiled escapes near the top:

```python
import unicodedata

_W_RE: re.Pattern[str] = re.compile(r"\w")
_D_RE: re.Pattern[str] = re.compile(r"\d")
_S_RE: re.Pattern[str] = re.compile(r"\s")
```

2. Change `_D_CHARS` to the Nd scan (BMP; fallback covers the rest):

```python
_D_CHARS: frozenset[str] = frozenset(
    chr(c) for c in range(0x10000) if unicodedata.category(chr(c)) == "Nd"
)
```

(`_W_CHARS` and `_S_CHARS` builders stay as they are — measured exact.)

3. Add the internal lowering function right after `_pattern_to_chars`:

```python
def _pattern_lowering(
    pat: str,
) -> tuple[frozenset[str] | None, re.Pattern[str] | None]:
    """Lower a single-char boundary fragment to a BMP set + non-BMP fallback.

    Returns ``(chars, fallback)``. ``chars`` is the BMP-exact frozenset for
    enumeration fragments (brackets, escaped literals) and the BMP scan for
    class escapes. ``fallback`` is the compiled escape (``\\w``, ``\\d``,
    ``\\s``) whose BMP scan is an approximation: it is consulted by
    :func:`check_boundary` for non-BMP neighbors (``ord(ch) > 0xFFFF``),
    keeping set membership exact against ``re`` for the whole codepoint
    space without an import-time scan of all 0x110000 codepoints.
    """
    if pat == r"\w":
        return _W_CHARS, _W_RE
    if pat == r"\d":
        return _D_CHARS, _D_RE
    if pat == r"\s":
        return _S_CHARS, _S_RE
    if len(pat) >= 2 and pat[0] == "[" and pat[-1] == "]":
        interior = pat[1:-1]
        if any(m in interior for m in "*+?{}|"):
            return None, None
        if interior.startswith("^"):
            return None, None
        return _chars_from_bracket(interior), None
    return None, None
```

4. Keep `_pattern_to_chars` as a thin delegate so the pinned test contract (`tests/unit/test_coverage_remediation.py`) is unchanged:

```python
def _pattern_to_chars(pat: str) -> frozenset[str] | None:
    """Return the BMP char set for a fragment, or None (multi/regex path)."""
    return _pattern_lowering(pat)[0]
```

(Replace the existing body; keep the docstring updated to mention negated classes fall back per #67.)

5. Extend `BoundarySpec` with two new fields (after `left_multi`/`right_multi`):

```python
    left_char_fallback: tuple[re.Pattern[str], ...] = field(
        default=(), init=False, repr=False
    )
    right_char_fallback: tuple[re.Pattern[str], ...] = field(
        default=(), init=False, repr=False
    )
```

Document them in the class docstring Attributes block (one line each: compiled class escapes consulted for non-BMP neighbors).

6. In `__post_init__`, switch the loops to `_pattern_lowering`:

```python
        lfb: list[re.Pattern[str]] = []
        rfb: list[re.Pattern[str]] = []
        if self.left is not None:
            for pat in self.left:
                chars, fallback = _pattern_lowering(pat)
                if chars is not None:
                    lc.update(chars)
                    if fallback is not None:
                        lfb.append(fallback)
                else:
                    w = _estimate_width(pat)
                    lm.append((w, re.compile(pat + r"\Z")))
        if self.right is not None:
            for pat in self.right:
                chars, fallback = _pattern_lowering(pat)
                if chars is not None:
                    rc.update(chars)
                    if fallback is not None:
                        rfb.append(fallback)
                else:
                    w = _estimate_width(pat)
                    rm.append((w, re.compile(r"\A" + pat)))
        object.__setattr__(self, "left_chars", frozenset(lc) if lc else None)
        object.__setattr__(self, "right_chars", frozenset(rc) if rc else None)
        object.__setattr__(self, "left_multi", tuple(lm))
        object.__setattr__(self, "right_multi", tuple(rm))
        object.__setattr__(self, "left_char_fallback", tuple(lfb))
        object.__setattr__(self, "right_char_fallback", tuple(rfb))
```

- [ ] **Step 4: Implement — `check_boundary` non-BMP fallback**

In `check_boundary`, replace the left block:

```python
    if spec.left is not None and start > 0:
        if spec.left_chars is not None and subject[start - 1] in spec.left_chars:
            return False
        for w, pat in spec.left_multi:
```

with:

```python
    if spec.left is not None and start > 0:
        ch = subject[start - 1]
        if spec.left_chars is not None and ch in spec.left_chars:
            return False
        # Non-BMP fallback: the char sets are BMP scans; for supplementary-
        # plane neighbors decide via the compiled escape (exact vs re) (#62).
        if spec.left_char_fallback and ord(ch) > 0xFFFF:
            if any(pat.match(ch) for pat in spec.left_char_fallback):
                return False
        for w, pat in spec.left_multi:
```

and mirror for the right block:

```python
    if spec.right is not None and end < len(subject):
        ch = subject[end]
        if spec.right_chars is not None and ch in spec.right_chars:
            return False
        if spec.right_char_fallback and ord(ch) > 0xFFFF:
            if any(pat.match(ch) for pat in spec.right_char_fallback):
                return False
        for w, pat in spec.right_multi:
```

(The hot path is unchanged for specs without class escapes: empty fallback tuples short-circuit, and BMP neighbors never reach `ord`.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -v`
Expected: all PASS.

- [ ] **Step 6: Regression — boundary + parity suites**

Run: `uv run pytest tests/unit/test_boundary_spec.py tests/unit/test_boundary_guards.py tests/unit/test_coverage_remediation.py tests/property -q`
Expected: green. If `test_boundary_compiled_parity` (or similar) fails, the fallback has a direction bug — fix, do not weaken the test.

- [ ] **Step 7: Update `paxman/core/AGENTS.md`**

Replace the kernel invariant bullet `- BoundarySpec frozensets O(1) — word/anchor guards use frozenset membership.` with:

```markdown
- `BoundarySpec` frozensets O(1) — word/anchor guards use `frozenset` membership;
  class escapes (`\w`, `\d`, `\s`) carry a compiled non-BMP fallback so neighbor
  decisions stay exact vs `re` across the full codepoint space (`\d` = Nd).
```

- [ ] **Step 8: Commit**

```bash
git add paxman/core/grammar/boundary_spec.py paxman/core/AGENTS.md tests/unit/test_kernel_hardening.py
git commit -m "fix(kernel): boundary char sets exact vs re for non-BMP and Nd (#62)"
```

---

### Task 4: `NormalizerSequence` no-expansion invariant (#63)

**Files:**
- Modify: `paxman/core/grammar/normalizers.py` (`NormalizerSequence`)
- Test: `tests/unit/test_kernel_hardening.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_kernel_hardening.py`:

```python
from paxman.core.grammar.normalizers import NormalizerSequence


class _ExpandingNormalizer:
    """Test normalizer violating the no-expansion invariant (1 cur -> 2 nxt)."""

    name = "expanding"
    provenance = None
    stripped_chars = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        if not text:
            return "", (), ()
        subject = text[0] + "-" + text[1:]  # 1 cur char -> 2 nxt chars
        starts: list[int] = []
        ends: list[int] = []
        for i, ch in enumerate(text):
            if i == 0:
                starts.extend([0, 0])  # expansion: two nxt chars from cur[0]
                ends.extend([1, 1])
            else:
                starts.append(i)
                ends.append(i + 1)
        return subject, tuple(starts), tuple(ends)


def test_sequence_composition_rejects_expanding_normalizer() -> None:
    """(#63) Composition asserts the unit-width invariant — expansion fails fast."""
    seq = NormalizerSequence(steps=(_ExpandingNormalizer(),))
    with pytest.raises(AssertionError):
        seq.normalize("ab")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -k expanding -v`
Expected: FAIL — the current composition silently mis-composes ends for expanding normalizers (no assertion fires).

- [ ] **Step 3: Implement**

In `paxman/core/grammar/normalizers.py`:

1. Extend the `Normalizer` protocol docstring (or `NormalizerSequence` docstring) with the invariant:

```text
    Normalizers must not expand: each character of the input maps to at most
    one character of the subject (stripping or 1:1 rewriting only). Sequence
    composition asserts unit-width offsets (``ends[i] == starts[i] + 1``) and
    fails fast otherwise — expansion would silently mis-map end offsets (#63).
```

2. In `NormalizerSequence.normalize`, inside the compose branch (where `composed_starts`/`composed_ends` are built), add the assertion before composing:

```python
                    # No-expansion invariant (#63): stripping normalizers map
                    # each cur char to at most one nxt char (unit-width
                    # offsets). Composition indexes cur arrays per nxt char;
                    # an expanding normalizer would silently mis-map ends.
                    assert all(
                        s + 1 == e for s, e in zip(off_starts, off_ends, strict=True)
                    ), "normalizer expansion is not supported in sequences"
```

(`off_starts`/`off_ends` are the non-None tuples already unpacked in that branch — keep the existing composition code unchanged.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -k expanding -v` and then `uv run pytest tests/unit/test_normalizers.py tests/unit/test_country_name_fold_golden.py tests/property -q`
Expected: new test PASS; regressions green (all shipped normalizers are stripping-only).

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/normalizers.py tests/unit/test_kernel_hardening.py
git commit -m "fix(kernel): pin no-expansion invariant in NormalizerSequence (#63)"
```

---

### Task 5: Bound the NFD per-char cache (#64)

**Files:**
- Modify: `paxman/core/grammar/normalizers.py` (`_NFD_CACHE` → `_nfd_char`)
- Modify: `paxman/core/AGENTS.md` (kernel invariant bullet)
- Test: `tests/unit/test_kernel_hardening.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/unit/test_kernel_hardening.py`:

```python
def test_nfd_char_cache_is_bounded() -> None:
    """(#64) The per-char NFD memo is an lru_cache, not an unbounded dict."""
    from paxman.core.grammar import normalizers

    assert normalizers._nfd_char.cache_info().maxsize == 8192
    # deterministic pure function: same char -> same decomposition
    assert normalizers._nfd_char("é") == normalizers._nfd_char("é")
    assert normalizers._nfd_char("é") == "e\u0301"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -k nfd -v`
Expected: FAIL — `AttributeError: module ... has no attribute '_nfd_char'`.

- [ ] **Step 3: Implement**

In `paxman/core/grammar/normalizers.py`:

1. Add `from functools import lru_cache` to the imports.
2. Replace `_NFD_CACHE: dict[str, str] = {}` with:

```python
@lru_cache(maxsize=8192)
def _nfd_char(ch: str) -> str:
    """NFD-decompose a single character (bounded memo, deterministic).

    Unicode decomposition mappings are per-codepoint, so per-char NFD
    concatenation equals whole-text NFD; the cache is a pure memo of a
    deterministic function — no input-dependent global state (#64, the
    former ``_NFD_CACHE`` dict grew without bound).
    """
    return unicodedata.normalize("NFD", ch)
```

3. In `CountryNameFold.normalize`, replace the cache block:

```python
            cached = _NFD_CACHE.get(ch)
            if cached is None:
                cached = unicodedata.normalize("NFD", ch)
                _NFD_CACHE[ch] = cached
            seg_len = len(cached)
```

with:

```python
            seg_len = len(_nfd_char(ch))
```

(the `nfd_orig` loop that consumes `seg_len` stays unchanged). Grep `_NFD_CACHE` afterwards — zero remaining references in `paxman/`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/unit/test_kernel_hardening.py -k nfd -v tests/unit/test_country_name_fold_golden.py tests/unit/test_normalizers.py -q`
Expected: PASS; country golden tests green (fold behavior unchanged).

- [ ] **Step 5: Update `paxman/core/AGENTS.md`**

Replace the bullet `- CountryNameFold single-pass NFD with _NFD_CACHE — one-pass fold, cached.` with:

```markdown
- `CountryNameFold` single-pass NFD with `_nfd_char` — one-pass fold, per-char
  memo is a bounded `lru_cache(maxsize=8192)` (no unbounded input-keyed state).
```

- [ ] **Step 6: Commit**

```bash
git add paxman/core/grammar/normalizers.py paxman/core/AGENTS.md tests/unit/test_kernel_hardening.py
git commit -m "fix(kernel): bound NFD per-char cache with lru_cache (#64)"
```

---

### Task 6: CHANGELOG, full gate, PR

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Update `CHANGELOG.md`**

Under `## [Unreleased]` → `### Fixed`, append (keep the existing #87/#88 entry above it):

```markdown
- **Kernel — grammar-path error contract (#66):** internal lookup failures
  (`KeyError`/`IndexError`) from grammars, candidate matchers, combinator leaves,
  and predicates now surface as `RecognitionError` (or are swallowed at the
  per-candidate/leaf boundary, as before) instead of escaping as raw exceptions.
  The rules path keeps its `except Exception → ValidationError` contract.
- **Kernel — `BoundarySpec` negated bracket classes (#67):** `[^...]` fragments no
  longer lower to an inverted positive char set; they fall back to the compiled
  regex path, preserving negated semantics.
- **Kernel — boundary char sets exact vs `re` (#62):** `\d` lowers to Unicode `Nd`
  (was ASCII-only), and class escapes (`\w`, `\d`, `\s`) carry a compiled non-BMP
  fallback so neighbor decisions are exact across the whole codepoint space without
  an import-time scan. Hot path unchanged (empty fallbacks short-circuit; BMP
  neighbors never compute `ord`).
- **Kernel — `NormalizerSequence` no-expansion invariant (#63):** composition asserts
  unit-width offsets; expanding normalizers fail fast instead of silently mis-mapping
  end offsets.
- **Kernel — bounded NFD cache (#64):** the per-char NFD memo is an
  `lru_cache(maxsize=8192)`; the unbounded input-keyed `_NFD_CACHE` dict is gone.
```

- [ ] **Step 2: Run the full pre-PR gate (mirrors CI)**

```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
uv run pyright
uv run import-linter lint
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
```

Expected: all green, coverage ≥ 95% per package. (Known pre-existing flake: `tests/property/test_hypothesis_parity_corpora.py` ISSN/IBAN in some combined orders — if only those fail, re-run in isolation and report.)

- [ ] **Step 3: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: changelog for kernel hardening II (#66 #67 #62 #63 #64)"
```

(The controller pushes and opens the PR against `dev`.)

---

## Self-review notes (spec ↔ plan)

- #66 ("KeyError/IndexError wrapped; test that grammar raising KeyError is wrapped; UnicodeError documented") → Task 1 (LookupError covers KeyError+IndexError; UnicodeError already ⊂ ValueError — noted in plan background; integration test covers grammar.recognize AND compiled-matchers paths). ✔
- #67 ("detect `^`, fall back to regex path; test `_chars_from_bracket("^a-z")` → None/fallback") → Task 2. ✔
- #62 ("\w parity incl. supplementary plane; property test") → Task 3 (exact-vs-re unit tests over BMP Nd + non-BMP spots; existing property suites re-run). ✔
- #63 ("document invariant + assertion") → Task 4. ✔
- #64 ("size-bound via lru_cache; comment asserting per-char equality") → Task 5. ✔
- Placeholder scan: none ("DateContractWithExtra" is explicitly marked as a placeholder with instructions to mirror the real pattern from `test_grammar_extensions.py`). ✔
