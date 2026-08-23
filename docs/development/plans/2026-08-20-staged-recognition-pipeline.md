# ADR-0008 Staged Recognition Pipeline — Implementation Plan

| | |
|---|---|
| **Title** | From bespoke `recognize()` scripts to declarative staged pipeline |
| **Date** | 2026-08-20 |
| **Status** | Draft — for review |
| **Branch** | `feature/staged-recognition-pipeline` (create before Task 1; one commit per task) |
| **Authoritative spec** | `docs/adr/0008-staged-recognition-pipeline.md` Rev.1 (Accepted 2026-08-20) — where this plan and the ADR disagree, the ADR wins |
| **Related ADRs** | ADR-0001 (pipeline seam), ADR-0003 (semantic affinity), ADR-0004 (single-value invariant) |
| **Oracle review** | `ses_fe24b48daffeCucuRVJMF2OWlL` (Rev.1 corrections already folded into ADR body) |

> **For agentic workers — REQUIRED SUB-SKILLS:** `test-driven-development` (RED → GREEN → refactor per task), `using-git-worktrees` (isolated workspace before Task 1). Every task ends with a scoped verify command and an atomic commit whose message is given in the task header. The executor is treated as having **zero context**: every file to create, every pattern to mirror, and every assertion matrix is specified below. Follow the embedded code verbatim — it was verified against the live sources on `main` at `1a7c4b2`. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | Task 1 — land `paxman/core/grammar/` skeleton (Stage Protocol, PipelineState, PipelineGrammar) | ☐ pending | |
> | Task 2 — BoundaryGuard family | ☐ pending | |
> | Task 3 — LexiconAlternation builder | ☐ pending | |
> | Task 4 — Migration Proof Harness (parity gate) | ☐ pending | |
> | Task 5 — migrate Currency grammars (S3) | ☐ pending | |
> | Task 6 — migrate Money grammars (S4+S5 hardest) | ☐ pending | |
> | Task 7 — migrate SIUnit grammars (S3+S4+S5) | ☐ pending | |
> | Task 8 — migrate Phone + URL grammars (S5) | ☐ pending | |
> | Task 9 — migrate remaining S1 grammars (Date, Email, IP, ISBN) | ☐ pending | |
> | Task 10 — retire legacy helpers + docs sweep | ☐ pending | |
> | Task 11 — final gate (no commit) | ☐ pending | |

---

## §1 Cross-Part Contract

### Goal

Replace 29 bespoke `Grammar.recognize()` implementations with a **fixed-order pipeline with optional stages** (`Pre → Regex → Lexicon → Composer → Post`). Each grammar declares which stages it needs; the pipeline executes them. The engine (`paxman/engine/orchestrator.py`), `Grammar` ABC surface, `RecognitionMatch`/`Notation` types, `grammar/data/` vs `rules/data/` boundary, determinism, and public API are **unchanged**. Every migration step is **byte-identical** on `RecognitionMatch` output, proven by the Migration Proof Harness.

### D-Decisions (locked — do not revisit without a new ADR)

- **D1 — Fixed order, optional stages.** Stage order is hard-coded in `PipelineGrammar.recognize()` as `pre → regex → lexicon → composer → post`. A grammar declares which stages to include (each is `Optional[Stage]`); undeclared stages are skipped. No grammar may reorder stages. This preserves the ADR's pipeline-of-optionals design (not Template Method — stages are included by declaration). If a future grammar needs a different order, extend the fixed order or add a new stage kind; do not add a bespoke `recognize()` escape hatch without a new ADR (ADR Open Question 1).

- **D2 — Layering: core stays capability-agnostic.** `paxman/core/grammar/` **never imports from `paxman.capabilities`**. `AMOUNT_PATTERN` and `classify_amount_shape` remain in `paxman/capabilities/Money/grammar/__init__.py` and are passed into the composer as constructor arguments (`AmountComposer(pattern=..., classify=...)`). An `amount.py` in core, if ever added, contains only a generic `AmountToken` abstraction — not Money's regex. Import-linter invariant: `paxman.core.grammar → (no capability imports)`; `paxman.capabilities.*.grammar → paxman.core.grammar + paxman.core.domain`. Adding `paxman/core/grammar` as a subpackage of `paxman.core` inherits core's leaf status — no new import-linter layer entry (to be confirmed at Task 1 landing).

- **D3 — Stage Protocol + PipelineState.** Inter-stage contract is explicit (`stages.py`):
  ```python
  @dataclass(frozen=True, slots=True)
  class PipelineState:
      text: str
      matches: list[RecognitionMatch[Any]]  # produced so far
      scratch: dict[str, object]  # stage-local (normalized text, offsets)


  class Stage(Protocol[NotationT]):
      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]: ...
  ```
  `Pre` produces normalized view and early-exit; `RegexStage` appends via `finditer`; `LexiconStage` (including `WholeInputLookup` variant for S2) appends alternation hits with `BoundaryGuard`; `ComposerStage` consumes `state.matches` + `state.text` to fuse adjacent tokens; `PostStage` refines spans/shapes in place.

- **D4 — Alternation ordering: longest-first, qualified-first.** `LexiconAlternation` sorts tokens by `(-len(token), -is_qualified, token)` where `is_qualified` is `any(c.isascii() and c.isalpha() for c in token)` (mirrors `Currency/SymbolRecognition._is_qualified`). This reproduces `SYMBOL_TOKENS` duplication between Currency and Money without code duplication per file. Tokens are `re.escape`d and joined with `|`.

- **D5 — BoundaryGuard family.** The 8 distinct lookaround variants enumerated in the ADR are unified behind a parameterized family in `boundary.py`. No grammar file hard-codes a lookaround literal after migration — each grammar references a `BoundaryGuard` instance. The `°` degree prefix in SIUnit (`(?<![°\w\-+\u2212/·⋅])`) is a semantic differentiator that must be preserved. `(?<![A-Za-z0-9+.\-])` (URL scheme-char) and `(?<![\w:.])` (Phone e164) remain distinct guards.

- **D6 — Span-merge contract for composers.** `AmountComposer` (Money) must reconstruct the exact combined span `[min(sym_start, amt_start), max(sym_end, amt_end))` that the current single-regex `SYMBOL ? AMOUNT | AMOUNT ? SYMBOL` patterns produce, including the ` ?` optional-space handling. Byte-identical `start/end/raw_text` is the migration invariant; the Proof Harness gates it. Same contract applies to any future composer that fuses lexicon + amount.

- **D7 — WholeInputLookup emits original `trimmed` value.** `Country/name_recognition` returns `value=trimmed` (original case) with `start = len(text) - len(text.lstrip())` and `end = start + len(trimmed)`, not the normalized key. The `WholeInputLookup` lexicon variant must reproduce this exactly.

- **D8 — Migration order and proof gate.** Incremental, capability-at-a-time (ADR §4):
  1. Land `paxman/core/grammar/*` + Proof Harness (no grammar migration yet).
  2. Currency + Money (highest duplication, hardest composer — proves S3→S4 + span-merge).
  3. SIUnit (proves S3+S5 split-prefix + S4 compound).
  4. Phone + URL (proves S5 trims in isolation).
  5. Remaining S1 (Date, Email, IP, ISBN) — mechanical.
  6. Retire `Phone/grammar/common.py:strip_separators` + `Country/name_normalization.py` (flagged legacy in `capabilities/AGENTS.md`).

  Every migration PR must pass the Migration Proof Harness: `assert old_grammar.recognize(text) == new_grammar.recognize(text)` over a curated corpus + property inputs. The harness is the migration gate; `benchmarks/harness.py` is informational, non-blocking (50 iterations in CI, `continue-on-error: true`).

- **D9 — No breaking change to community extensions.** `README.md`'s `Grammar[NotationT]` subclass example remains valid; shipped grammars may adopt `PipelineGrammar`, but community extensions are **not** forced into it (`isinstance` branch in engine stays `Grammar`).

- **D10 — Spec-codegen boundary.** Only three data tables are generated (each via its `tools/regenerate_*_data.py`): ISBN range message, URL IDNA UTS #46 mapping, SIUnit prefixed-unit + grammar token tables. All other tables under `grammar/data/` and `rules/data/` are plain module-level tables edited directly. This pipeline does not introduce new codegen.

### Out of scope

- No change to `Grammar` ABC surface (`name`, `semantics`, `single_value`, `recognize` signature), `RecognitionMatch`, `Notation`, `Rule`, `Provenance`, `Resolution`, `ExecutionResult`, or engine pipeline (`_recognize` → `_collect_candidates` → `_enforce_single_value_invariant`).
- No change to `grammar/data/` vs `rules/data/` boundary; no change to `get_grammars()` wiring (returns `PipelineGrammar` instances, no caller change).
- No benchmark gating (ADR Open Question 3 — out of scope; `benchmarks/harness.py` stays informational).
- No edits to historical `docs/adr/*` beyond this ADR's own status flip (already landed on `main`), no edits to `docs/development/report/*` or `docs/research/*`.

### Module layout

```text
paxman/core/grammar/               # NEW — recognition-layer internals, no capability imports
├── __init__.py                    # re-exports PipelineGrammar, PipelineState, Stage, BoundaryGuard, LexiconAlternation
├── stages.py                      # PipelineState + Stage Protocol + 5 concrete stage types
├── boundary.py                    # BoundaryGuard family (parameterized — replaces 8 lookarounds)
├── lexicon.py                     # LexiconAlternation builder (longest-first, qualified-first)
└── pipeline.py                    # PipelineGrammar[NotationT] — fixed-order pipeline with optional stages

paxman/capabilities/*/grammar/     # grammars shrink to ~15-line declarations
├── *_recognition.py               # tokens/regex/composer/post references (no inline re.compile loops)
└── data/                          # unchanged

tests/
├── unit/test_pipeline_stages.py           # stage unit tests (new)
├── unit/test_boundary_guards.py           # boundary unit tests (new)
├── unit/test_lexicon_alternation.py       # lexicon builder unit tests (new)
└── property/test_grammar_stage_parity.py  # Migration Proof Harness (new, parametrized)
```

### Authoritative file inventory

Verified on `main` at `1a7c4b2` (29 grammars, 56 files under `paxman/capabilities/*/grammar/**`):

| Capability | Grammars | Files |
|------------|----------|-------|
| Country | 4 (alpha2, alpha3, numeric, name) | 4 |
| Currency | 3 (code, symbol, word) | 3 |
| Date | 4 (iso8601, us, european, slash_iso) | 4 |
| Email | 3 (standard, obfuscated, localhost) | 3 |
| IP | 2 (ipv4, ipv6) | 2 |
| ISBN | 2 (isbn13, isbn10) | 2 |
| Money | 3 (code, symbol, word) | 3 |
| Phone | 4 (e164, tel_uri, international_00, national) | 4 |
| SIUnit | 3 (symbol, name, compound) | 3 |
| URL | 1 (absolute_uri) | 1 |

`README.md` lists 31 by including two planned-but-unimplemented `SIUnit/split_word_prefix` and `SIUnit/split_symbol_prefix` grammars (no `recognize` in code) — not in scope.

---

## §2 Tasks

### Task 1 — `feat(core): add PipelineState, Stage Protocol, and PipelineGrammar skeleton`

**Files:**
- Create: `paxman/core/grammar/__init__.py`
- Create: `paxman/core/grammar/stages.py`
- Create: `paxman/core/grammar/pipeline.py`
- Create: `tests/unit/test_pipeline_stages.py`

**Goal:** Land the inter-stage contract and the fixed-order pipeline base class. No grammar migrates yet; `PipelineGrammar` correctly walks `pre → regex → lexicon → composer → post` with each stage optional.

- [ ] **Step 1: Write the failing test — PipelineState + Stage Protocol**

  Create `tests/unit/test_pipeline_stages.py`:

  ```python
  """Unit tests for PipelineState and PipelineGrammar skeleton."""

  from __future__ import annotations

  import re

  import pytest

  from paxman.capabilities.Date.notation import DateNotation
  from paxman.core.domain import Grammar, RecognitionMatch
  from paxman.core.grammar import PipelineGrammar, PipelineState
  from paxman.core.grammar.stages import RegexStage, StandardPre


  class _ProbeGrammar(PipelineGrammar[DateNotation]):
      """Minimal PipelineGrammar for skeleton test."""

      name = "probe_recognition"
      semantics = "probe_recognition"
      pre = StandardPre(empty_guard=True)
      regex = RegexStage(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")


  def test_pipeline_state_is_frozen_slots() -> None:
      state = PipelineState(text="hello", matches=[], scratch={})
      assert state.text == "hello"
      with pytest.raises(AttributeError):
          state.text = "mutated"  # type: ignore[misc]


  def test_pipeline_grammar_is_grammar_subclass() -> None:
      g = _ProbeGrammar()
      assert isinstance(g, Grammar)
      assert g.name == "probe_recognition"
      assert g.semantics == "probe_recognition"


  def test_pipeline_grammar_recognize_delegates_to_stages() -> None:
      g = _ProbeGrammar()
      results = g.recognize("2026-01-15 foo 2026/01/15")
      assert len(results) == 1
      assert results[0].raw_text == "2026-01-15"
      assert results[0].start == 0
      assert results[0].end == 10


  def test_empty_input_early_exit_via_pre() -> None:
      g = _ProbeGrammar()
      assert g.recognize("") == []
      assert g.recognize("   ") == []


  def test_grammar_with_no_stages_returns_empty() -> None:
      class _EmptyGrammar(PipelineGrammar[DateNotation]):
          name = "empty_recognition"
          semantics = "empty_recognition"

      assert _EmptyGrammar().recognize("2026-01-15") == []
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest tests/unit/test_pipeline_stages.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar'` (package does not exist yet).

- [ ] **Step 3: Write minimal implementation**

  Create `paxman/core/grammar/__init__.py`:
  ```python
  """Recognition-layer pipeline internals (capability-agnostic)."""

  from __future__ import annotations

  from paxman.core.grammar.pipeline import PipelineGrammar
  from paxman.core.grammar.stages import PipelineState, RegexStage, Stage, StandardPre

  __all__ = ["PipelineGrammar", "PipelineState", "RegexStage", "Stage", "StandardPre"]
  ```

  Create `paxman/core/grammar/stages.py`:
  ```python
  """Stage Protocol and concrete stage types for the recognition pipeline."""

  from __future__ import annotations

  import re
  from dataclasses import dataclass, field
  from typing import Any, Generic, Protocol, TypeVar

  from paxman.core.domain import RecognitionMatch

  NotationT = TypeVar("NotationT")


  @dataclass(frozen=True, slots=True)
  class PipelineState(Generic[NotationT]):
      """Mutable-through-replacement state threaded through stages."""

      text: str
      matches: list[RecognitionMatch[NotationT]] = field(default_factory=list)
      scratch: dict[str, object] = field(default_factory=dict)


  class Stage(Protocol[NotationT]):
      """Inter-stage contract — each stage consumes and returns a PipelineState."""

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]: ...


  @dataclass(frozen=True, slots=True)
  class StandardPre(Generic[NotationT]):
      """Pre-processing stage: empty/whitespace early-exit, optional normalizer."""

      empty_guard: bool = True

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          if self.empty_guard and not state.text.strip():
              return PipelineState(
                  text=state.text, matches=[], scratch=dict(state.scratch)
              )
          return state


  @dataclass(frozen=True, slots=True)
  class RegexStage(Generic[NotationT]):
      """Regex parser stage: pure shape scan via finditer."""

      pattern: str
      notation_fn: Any = None  # Callable[[re.Match[str]], NotationT] | None
      _compiled: re.Pattern[str] = field(init=False, repr=False)

      def __post_init__(self) -> None:
          object.__setattr__(self, "_compiled", re.compile(self.pattern))

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          if self.notation_fn is None:
              return state
          new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
          for m in self._compiled.finditer(state.text):
              notation = self.notation_fn(m)
              new_matches.append(
                  RecognitionMatch(
                      notation=notation, start=m.start(), end=m.end(), raw_text=m.group(0)
                  )
              )
          return PipelineState(
              text=state.text, matches=new_matches, scratch=dict(state.scratch)
          )
  ```

  **Note:** The skeleton `RegexStage.run` above is intentionally generic — it returns `state` unchanged. The probe test must inject a notation factory. Refine the skeleton so `_ProbeGrammar` works: either (a) `RegexStage` accepts an optional `notation_fn` callable `(re.Match) -> NotationT` and `run` uses it, or (b) the test grammar overrides `regex` with a bound subclass. **Pick (a)** for the plan — it keeps `PipelineGrammar` generic without per-grammar subclassing. The exact field is:

  ```python
  @dataclass(frozen=True, slots=True)
  class RegexStage(Generic[NotationT]):
      pattern: str
      notation_fn: Any = None  # Callable[[re.Match[str]], NotationT] | None
      _compiled: re.Pattern[str] = field(init=False, repr=False)

      def __post_init__(self) -> None:
          object.__setattr__(self, "_compiled", re.compile(self.pattern))

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          if self.notation_fn is None:
              return state
          new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
          for m in self._compiled.finditer(state.text):
              notation = self.notation_fn(m)
              new_matches.append(
                  RecognitionMatch(
                      notation=notation, start=m.start(), end=m.end(), raw_text=m.group(0)
                  )
              )
          return PipelineState(
              text=state.text, matches=new_matches, scratch=dict(state.scratch)
          )
  ```

  And the probe grammar becomes:

  ```python
  from paxman.capabilities.Date.notation import DateNotation


  def _date_notation(m: re.Match[str]) -> DateNotation:
      return DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3))


  class _ProbeGrammar(PipelineGrammar[DateNotation]):
      name = "probe_recognition"
      semantics = "probe_recognition"
      pre = StandardPre(empty_guard=True)
      regex = RegexStage(
          r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", notation_fn=_date_notation
      )
  ```

  Create `paxman/core/grammar/pipeline.py`:
  ```python
  """PipelineGrammar base — fixed-order pipeline with optional stages."""

  from __future__ import annotations

  from typing import Any, ClassVar, Generic, TypeVar

  from paxman.core.domain import Grammar, RecognitionMatch
  from paxman.core.grammar.stages import PipelineState

  NotationT = TypeVar("NotationT")


  class PipelineGrammar(Grammar[NotationT]):
      """Grammar that declares optional stages; recognize() walks them in fixed order."""

      # Stages — each is Optional[Stage]; None means "skip".
      pre: Any = None
      regex: Any = None
      lexicon: Any = None
      composer: Any = None
      post: Any = None

      def recognize(self, text: str) -> list[RecognitionMatch[NotationT]]:
          state: PipelineState[NotationT] = PipelineState(
              text=text, matches=[], scratch={}
          )
          for stage in (self.pre, self.regex, self.lexicon, self.composer, self.post):
              if stage is not None:
                  state = stage.run(state)  # type: ignore[union-attr]
                  # Pre short-circuit: if StandardPre emptied matches on whitespace-only
                  # input, skip remaining stages — they would find nothing anyway.
                  if (
                      self.pre is not None
                      and not state.text.strip()
                      and not state.matches
                  ):
                      break
          return list(state.matches)
  ```

  **Type note:** `pipeline.py` must pass `pyright --typeCheckingMode strict` with no `# type: ignore` in source. Use `cast` or tighten the `Stage` protocol typing to avoid the `union-attr` ignore shown above — the sketch suppression is for the plan's readability, not the shipped code.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/unit/test_pipeline_stages.py -v
  uv run ruff check paxman/core/grammar/ tests/unit/test_pipeline_stages.py
  uv run pyright
  ```

  Expected: PASS (all 5 tests), ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/core/grammar/__init__.py paxman/core/grammar/stages.py paxman/core/grammar/pipeline.py tests/unit/test_pipeline_stages.py
  git commit -m "feat(core): add PipelineState, Stage Protocol, and PipelineGrammar skeleton"
  ```

---

### Task 2 — `feat(core): add BoundaryGuard family`

**Files:**
- Create: `paxman/core/grammar/boundary.py`
- Modify: `paxman/core/grammar/__init__.py` (re-export)
- Test: `tests/unit/test_boundary_guards.py`

**Goal:** Centralize the 8 distinct lookaround variants behind a parameterized family. Each guard produces a compiled alternation-ready regex or a pair of `(lookbehind, lookahead)` strings that `LexiconStage` injects.

- [ ] **Step 1: Write the failing test**

  Create `tests/unit/test_boundary_guards.py`:

  ```python
  """BoundaryGuard unit tests — 8 distinct lookarounds, one family."""

  from __future__ import annotations

  from paxman.core.grammar.boundary import BoundaryGuard


  def test_word_sign_guard_blocks_inside_token() -> None:
      g = BoundaryGuard.word_sign()  # (?<![\w\-+\u2212]) / (?![\w\-+\u2212])
      assert g.blocks("x$", 1) is True  # "$" inside "x$"? Actually test via regex match
      # Prefer integration: the guard's pattern must NOT match "x€" at offset 1
      assert g.pattern_for("€").search("x€") is None
      assert g.pattern_for("€").search(" €") is not None
      assert g.pattern_for("€").search("€") is not None


  def test_siunit_degree_guard_differs_from_word_sign() -> None:
      # SIUnit includes ° in the lookaround; Currency does not.
      g_word = BoundaryGuard.word_sign()
      g_degree = BoundaryGuard.degree_word_sign()
      assert g_word.lookbehind != g_degree.lookbehind
      assert "°" in g_degree.lookbehind


  def test_scheme_char_guard_for_url() -> None:
      g = BoundaryGuard.scheme_char()  # (?<![A-Za-z0-9+.\-])
      assert g.pattern_for("https:").search("xhttps:") is None
      assert g.pattern_for("https:").search(" https:") is not None


  def test_e164_word_colon_dot_guard() -> None:
      g = BoundaryGuard.e164()  # (?<![\w:.])
      assert g.pattern_for("+1").search("a+1") is None
      assert g.pattern_for("+1").search(" +1") is not None
      assert g.pattern_for("+1").search("tel:+1") is None


  def test_digit_guard_for_date() -> None:
      g = BoundaryGuard.digit()  # (?<!\d) / (?!\d)
      assert g.pattern_for("2026-01-15").search("12026-01-15") is None
      assert g.pattern_for("2026-01-15").search("2026-01-15") is not None


  def test_word_only_guard_for_country() -> None:
      g = BoundaryGuard.word_only()  # (?<!\w) / (?!\w)  (equiv. \b)
      assert g.pattern_for("US").search("XUS") is None
      assert g.pattern_for("US").search(" US ") is not None
  ```

  Adjust the API (`pattern_for`, `blocks`, `lookbehind`) to whatever the implementation actually exposes — the test above is the contract; the implementation must satisfy it, not vice versa. If the implementation exposes `wrap(alternation: str) -> re.Pattern`, rename `pattern_for` to `wrap` in the test before landing.

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest tests/unit/test_boundary_guards.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar.boundary'` or `ImportError: cannot import name 'BoundaryGuard'`.

- [ ] **Step 3: Write minimal implementation**

  Create `paxman/core/grammar/boundary.py`:

  ```python
  """BoundaryGuard family — parameterized lookarounds replacing 8 distinct literals."""

  from __future__ import annotations

  import re
  from dataclasses import dataclass


  @dataclass(frozen=True, slots=True)
  class BoundaryGuard:
      """A parameterized boundary guard producing lookaround-wrapped patterns."""

      lookbehind: str
      lookahead: str

      def wrap(self, alternation: str) -> re.Pattern[str]:
          """Wrap an alternation with this guard's lookarounds and compile."""
          return re.compile(rf"{self.lookbehind}(?:{alternation}){self.lookahead}")

      # Factory constructors — one per distinct semantic variant.
      @classmethod
      def word_sign(cls) -> BoundaryGuard:
          return cls(lookbehind=r"(?<![\w\-+\u2212])", lookahead=r"(?![\w\-+\u2212])")

      @classmethod
      def degree_word_sign(cls) -> BoundaryGuard:
          return cls(
              lookbehind=r"(?<![°\w\-+\u2212/·⋅])", lookahead=r"(?![\w\-+\u2212/·⋅])"
          )

      @classmethod
      def digit(cls) -> BoundaryGuard:
          return cls(lookbehind=r"(?<!\d)", lookahead=r"(?!\d)")

      @classmethod
      def word_only(cls) -> BoundaryGuard:
          return cls(lookbehind=r"(?<!\w)", lookahead=r"(?!\w)")

      @classmethod
      def e164(cls) -> BoundaryGuard:
          return cls(lookbehind=r"(?<![\w:.])", lookahead=r"")

      @classmethod
      def scheme_char(cls) -> BoundaryGuard:
          return cls(lookbehind=r"(?<![A-Za-z0-9+.\-])", lookahead=r"")

      # Additional variants for the remaining two of the 8 (if needed):
      #   (?<![\s:-])  and  (?<![\w:.+]) / (?<![\d+])
      # Add as @classmethod factories when a grammar needing them migrates.
  ```

  Update `paxman/core/grammar/__init__.py` to re-export `BoundaryGuard`.

  After landing, the 8 ADR variants are covered as:
  | Variant | Factory |
  |---------|---------|
  | `(?<![\w\-+\u2212])` | `word_sign` |
  | `(?<![\w\-+\u2212/·⋅])` / `(?<![°\w\-+\u2212/·⋅])` | `degree_word_sign` |
  | `(?<![\w:.])` | `e164` |
  | `(?<![A-Za-z0-9+.\-])` | `scheme_char` |
  | `(?<!\d)` | `digit` |
  | `(?<!\w)` / `\b` | `word_only` |
  | `(?<![\s:-])`, `(?<![\w:.+])`, `(?<![\d+])` | add factories when Phone/URL migration needs them |

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/unit/test_boundary_guards.py -v
  uv run ruff check paxman/core/grammar/boundary.py tests/unit/test_boundary_guards.py
  uv run pyright
  ```

  Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/core/grammar/boundary.py paxman/core/grammar/__init__.py tests/unit/test_boundary_guards.py
  git commit -m "feat(core): add BoundaryGuard family"
  ```

---

### Task 3 — `feat(core): add LexiconAlternation builder`

**Files:**
- Create: `paxman/core/grammar/lexicon.py`
- Modify: `paxman/core/grammar/stages.py` (add `LexiconStage`, `WholeInputLookup`)
- Modify: `paxman/core/grammar/__init__.py` (re-exports)
- Test: `tests/unit/test_lexicon_alternation.py`

**Goal:** Centralize the `re.escape` + `longest-first, qualified-first` alternation that is copy-pasted in 5 files. `LexiconStage` wraps the alternation with a `BoundaryGuard` and emits `RecognitionMatch`es.

- [ ] **Step 1: Write the failing test**

  Create `tests/unit/test_lexicon_alternation.py`:

  ```python
  """LexiconAlternation unit tests."""

  from __future__ import annotations

  import re

  from paxman.core.grammar.boundary import BoundaryGuard
  from paxman.core.grammar.lexicon import LexiconAlternation
  from paxman.core.grammar.stages import LexiconStage, WholeInputLookup
  from paxman.capabilities.Currency.notation import CurrencyNotation


  def test_longest_first_ordering() -> None:
      alt = LexiconAlternation(tokens=["$", "US$", "A$"], longest_first=True)
      # US$ (3) before A$ (2) before $ (1); qualified-first tie-break is secondary
      assert alt.ordered_tokens[0] == "US$"
      assert alt.alternation.startswith("US\\$")


  def test_qualified_first_within_same_length() -> None:
      alt = LexiconAlternation(tokens=["€", "US$"], longest_first=True)
      # Both length-different, but qualified ("US$") sorts before bare ("€") at same len
      # Longest dominates, so US$ still first
      assert alt.ordered_tokens[0] == "US$"


  def test_alternation_is_escaped() -> None:
      alt = LexiconAlternation(tokens=["$", "("], longest_first=True)
      assert r"\$" in alt.alternation
      assert r"\(" in alt.alternation


  def test_lexicon_stage_emits_matches_with_boundary() -> None:
      stage = LexiconStage[CurrencyNotation](
          tokens=["$", "US$"],
          boundary=BoundaryGuard.word_sign(),
          longest_first=True,
          notation_fn=lambda token: CurrencyNotation(text=token, shape="symbol"),
      )
      from paxman.core.grammar.stages import PipelineState

      state = PipelineState(text="Pay US$ and $", matches=[], scratch={})
      out = stage.run(state)
      assert len(out.matches) == 2
      assert out.matches[0].raw_text == "US$"
      assert out.matches[1].raw_text == "$"


  def test_whole_input_lookup_emits_original_trimmed_case() -> None:
      stage: WholeInputLookup[CurrencyNotation] = WholeInputLookup(
          keys={"us", "eur"},  # normalized keys
          notation_fn=lambda trimmed: CurrencyNotation(text=trimmed, shape="code"),
      )
      from paxman.core.grammar.stages import PipelineState

      state = PipelineState(text="  Us  ", matches=[], scratch={})
      out = stage.run(state)
      assert len(out.matches) == 1
      assert out.matches[0].raw_text == "Us"  # original trimmed, not "us"
      assert out.matches[0].start == 2
      assert out.matches[0].end == 4
  ```

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest tests/unit/test_lexicon_alternation.py -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar.lexicon'`.

- [ ] **Step 3: Write minimal implementation**

  Create `paxman/core/grammar/lexicon.py`:

  ```python
  """LexiconAlternation builder — longest-first, qualified-first, escaped."""

  from __future__ import annotations

  import re
  from dataclasses import dataclass, field


  def _is_qualified(token: str) -> bool:
      return any(c.isascii() and c.isalpha() for c in token)


  @dataclass(frozen=True, slots=True)
  class LexiconAlternation:
      """Builds a longest-first, qualified-first escaped alternation."""

      tokens: frozenset[str] | set[str] | list[str]
      longest_first: bool = True

      ordered_tokens: list[str] = field(init=False)
      alternation: str = field(init=False)

      def __post_init__(self) -> None:
          toks = list(self.tokens)
          if self.longest_first:
              toks.sort(key=lambda t: (-len(t), -int(_is_qualified(t)), t))
          else:
              toks.sort()
          object.__setattr__(self, "ordered_tokens", toks)
          object.__setattr__(self, "alternation", "|".join(re.escape(t) for t in toks))
  ```

  Update `paxman/core/grammar/stages.py` to add `LexiconStage` and `WholeInputLookup`:

  ```python
  @dataclass(frozen=True, slots=True)
  class LexiconStage(Generic[NotationT]):
      tokens: frozenset[str] | set[str] | list[str]
      boundary: BoundaryGuard
      longest_first: bool = True
      notation_fn: Any = None  # Callable[[str], NotationT]

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          if self.notation_fn is None:
              return state
          from paxman.core.grammar.lexicon import LexiconAlternation

          alt = LexiconAlternation(tokens=self.tokens, longest_first=self.longest_first)
          pat = self.boundary.wrap(alt.alternation)
          new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
          for m in pat.finditer(state.text):
              token = m.group(0)
              new_matches.append(
                  RecognitionMatch(
                      notation=self.notation_fn(token),
                      start=m.start(),
                      end=m.end(),
                      raw_text=token,
                  )
              )
          return PipelineState(
              text=state.text, matches=new_matches, scratch=dict(state.scratch)
          )


  @dataclass(frozen=True, slots=True)
  class WholeInputLookup(Generic[NotationT]):
      """S2 whole-input membership — a LexiconStage variant for Country/name_recognition."""

      keys: frozenset[str] | set[str]
      notation_fn: Any = None  # Callable[[str], NotationT]
      normalizer: Any = None  # Callable[[str], str] | None

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          if self.notation_fn is None:
              return state
          trimmed = state.text.strip()
          if not trimmed:
              return state
          normalized = (
              self.normalizer(trimmed) if self.normalizer is not None else trimmed.lower()
          )
          if normalized in self.keys:
              start = len(state.text) - len(state.text.lstrip())
              end = start + len(trimmed)
              new_matches: list[RecognitionMatch[NotationT]] = list(state.matches)
              new_matches.append(
                  RecognitionMatch(
                      notation=self.notation_fn(trimmed),
                      start=start,
                      end=end,
                      raw_text=trimmed,
                  )
              )
              return PipelineState(
                  text=state.text, matches=new_matches, scratch=dict(state.scratch)
              )
          return state
  ```

  The `normalizer` field on `WholeInputLookup` lets Country pass its `normalize_name` function; when `None`, a default `lower()` is used for the test. Adjust signature to match the real `Country/name_normalization.py:normalize_name` when wiring.

  Update `paxman/core/grammar/__init__.py` re-exports.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/unit/test_lexicon_alternation.py -v
  uv run ruff check paxman/core/grammar/lexicon.py paxman/core/grammar/stages.py tests/unit/test_lexicon_alternation.py
  uv run pyright
  ```

  Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/core/grammar/lexicon.py paxman/core/grammar/stages.py paxman/core/grammar/__init__.py tests/unit/test_lexicon_alternation.py
  git commit -m "feat(core): add LexiconAlternation builder and LexiconStage"
  ```

---

### Task 4 — `test: add Migration Proof Harness (parity gate)`

**Files:**
- Create: `tests/property/test_grammar_stage_parity.py`
- Create: `tests/unit/test_pipeline_parity.py` (optional — see below; pick ONE location, not both)
- Test: the harness itself

**Goal:** The harness is the migration gate (§4.1). It asserts byte-identical `list[RecognitionMatch]` (span, raw_text, notation) between old bespoke `recognize()` and new `PipelineGrammar` declarations. It must run on every migration PR and block merge on failure.

- [ ] **Step 1: Write the failing test — harness skeleton**

  Create `tests/property/test_grammar_stage_parity.py`:

  ```python
  """Migration Proof Harness — byte-identical RecognitionMatch parity.

  Every migration PR must prove the new PipelineGrammar declaration produces
  the same list[RecognitionMatch] as the old bespoke recognize() for a
  curated corpus plus property-generated inputs.

  Corpus must cover:
  - Country/name_recognition: normalized-key vs original-case value
  - Phone/e164: E164Trim (end = start + len(trimmed)) vs match.end()
  - URL: paren-balance (end = start + len(trimmed))
  - Money: either-order SYMBOL ? AMOUNT span-merge
  - SIUnit: split-prefix classifier
  - ISBN: hyphen/space tolerance
  """

  from __future__ import annotations

  import pytest

  # Import harness helper — to be implemented in this task.
  from tests.property.grammar_stage_parity import assert_grammar_parity


  CURATED_CORPUS: list[str] = [
      "United States",  # Country name — original case preservation
      "  united states  ",  # Country name — whitespace + case fold
      "+1 555 123 4567",  # Phone e164 — normal
      "+15551234567 5551234567",  # Phone e164 — runaway trim at 15 digits
      "https://example.com/path_(with_parens)",  # URL paren-balance
      "USD500",  # Money code+amount
      "$500",  # Money bare symbol + amount (shared symbol)
      "500 EUR",  # Money amount + code (either order)
      "kilo gram",  # SIUnit split_word_prefix
      "m/s",  # SIUnit compound
      "9780306406157",  # ISBN13 bare
      "978-0-11-000222-4",  # ISBN13 hyphenated (range message)
      "2026-01-15",  # Date S1
      "user@example.com",  # Email S1
      "192.168.1.1",  # IP S1
  ]


  @pytest.mark.property
  def test_curated_corpus_parity_placeholder() -> None:
      """Placeholder — will be parametrized over (grammar, text) pairs.

      RED: assert_grammar_parity does not exist yet.
      """
      # Each parametrized case will call:
      #   assert_grammar_parity(old_grammar, new_grammar, text)
      # where equality is (start, end, raw_text, notation).
      pytest.skip("Harness not yet implemented — wire in Task 5+")
  ```

  Also create the helper module `tests/property/grammar_stage_parity.py`:

  ```python
  """Helper for Migration Proof Harness."""

  from __future__ import annotations

  from paxman.core.domain import Grammar


  def assert_grammar_parity(old: Grammar, new: Grammar, text: str) -> None:
      """Assert byte-identical RecognitionMatch lists."""
      old_matches = old.recognize(text)
      new_matches = new.recognize(text)
      assert len(old_matches) == len(new_matches), (
          f"len mismatch for {text!r}: {old_matches} vs {new_matches}"
      )
      for o, n in zip(old_matches, new_matches):
          assert o.start == n.start, f"start mismatch for {text!r}: {o} vs {n}"
          assert o.end == n.end, f"end mismatch for {text!r}: {o} vs {n}"
          assert o.raw_text == n.raw_text, (
              f"raw_text mismatch for {text!r}: {o.raw_text!r} vs {n.raw_text!r}"
          )
          assert o.notation == n.notation, (
              f"notation mismatch for {text!r}: {o.notation!r} vs {n.notation!r}"
          )
  ```

- [ ] **Step 2: Run test to verify it fails (or is skipped as designed)**

  Run: `uv run pytest tests/property/test_grammar_stage_parity.py -v`
  Expected: `SKIPPED` (placeholder) — the harness is intentionally inert until Task 5 wires the first real parametrized case. The RED is that no migration has yet been proven; the harness itself is GREEN-skipped.

  Alternative RED: write the test to FAIL if the helper is missing, then make it pass — either is acceptable as long as the harness lands with a non-trivial corpus and the helper.

- [ ] **Step 3: Write minimal implementation (harness lands)**

  Land both files as above. Add hypothesis strategy for property-generated inputs if desired (optional — curated corpus is the gate; property is the amplifier).

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/property/test_grammar_stage_parity.py -v
  uv run ruff check tests/property/test_grammar_stage_parity.py tests/property/grammar_stage_parity.py
  uv run pyright
  ```

  Expected: 1 skipped (placeholder) + 0 failures; ruff/pyright clean for the helper (the `Grammar` import is typed).

- [ ] **Step 5: Commit**

  ```bash
  git add tests/property/test_grammar_stage_parity.py tests/property/grammar_stage_parity.py
  git commit -m "test: add Migration Proof Harness (parity gate)"
  ```

---

### Task 5 — `refactor(currency): migrate Currency grammars to PipelineGrammar (S3)`

**Files:**
- Modify: `paxman/capabilities/Currency/grammar/code_recognition.py`
- Modify: `paxman/capabilities/Currency/grammar/symbol_recognition.py`
- Modify: `paxman/capabilities/Currency/grammar/word_recognition.py`
- Test: `tests/capabilities/currency/test_grammar.py` (existing — must stay green)
- Test: parametrize harness for Currency

**Goal:** Prove S3 (lexicon-driven regex) via the lowest-risk capability. Each grammar shrinks from a `finditer` script to ~15 lines of stage declarations.

- [ ] **Step 1: Write the failing test — harness parametrized for Currency**

  Extend `tests/property/test_grammar_stage_parity.py` with a real parametrized case for Currency. Keep the old bespoke class importable (cheat: import the file's previous commit copy, or snapshot the old `recognize` into a helper). The simplest RED: duplicate the old grammar logic into `tests/property/_legacy_currency_grammars.py` (copied verbatim from `main`) and assert parity against the new declaration which does not yet exist.

  ```python
  import pytest
  from tests.property._legacy_currency_grammars import LegacySymbolRecognition
  from paxman.capabilities.Currency.grammar.symbol_recognition import SymbolRecognition
  from tests.property.grammar_stage_parity import assert_grammar_parity


  @pytest.mark.property
  @pytest.mark.parametrize("text", ["US$", "$", "€", "¥", "x€", "US$5", "Pay € now"])
  def test_currency_symbol_parity(text: str) -> None:
      assert_grammar_parity(LegacySymbolRecognition(), SymbolRecognition(), text)
  ```

  Run: `uv run pytest tests/property/test_grammar_stage_parity.py::test_currency_symbol_parity -v` → RED (new grammar still bespoke, or not yet parity-clean — the test is written before the migration, so it should fail on at least one span/normalization edge).

- [ ] **Step 2: Run test to verify it fails**

  Run as above. Expected: FAIL (byte-identical gate is not yet met).

- [ ] **Step 3: Write minimal implementation — migrate one grammar, then the others**

  Example for `Currency/grammar/symbol_recognition.py` (after migration):

  ```python
  """CLDR currency symbol recognition grammar — PipelineGrammar declaration."""

  from __future__ import annotations

  from paxman.capabilities.Currency.grammar.data.currency_symbols import SYMBOL_TOKENS
  from paxman.capabilities.Currency.notation import CurrencyNotation
  from paxman.core.domain import RecognitionMatch  # for notation_fn typing only
  from paxman.core.grammar import BoundaryGuard, PipelineGrammar
  from paxman.core.grammar.stages import LexiconStage, StandardPre


  def _is_qualified(token: str) -> bool:
      return any(c.isascii() and c.isalpha() for c in token)


  class SymbolRecognition(PipelineGrammar[CurrencyNotation]):
      name = "symbol_recognition"
      semantics = "symbol_recognition"
      single_value = True
      pre = StandardPre(empty_guard=True)
      lexicon = LexiconStage(
          tokens=SYMBOL_TOKENS,
          boundary=BoundaryGuard.word_sign(),
          longest_first=True,
          notation_fn=lambda token: CurrencyNotation(
              text=token, shape="qualified_symbol" if _is_qualified(token) else "symbol"
          ),
      )
  ```

  Apply the same pattern to `code_recognition.py` (boundary `word_sign`, tokens are not needed — it is a pure `[A-Za-z]{3}` shape so it stays `RegexStage` with `(?<![\w\-+\u2212])[A-Za-z]{3}(?![\w\-+\u2212])` and a `str.upper` notation_fn; or lexicon over `CURRENCY_CODES` — pick one and keep it consistent with the S3 table). `word_recognition.py` is lexicon over `WORD_TOKENS` with `word_sign`. Verify each file's original `recognize()` behavior before choosing — the plan's sketch is not authoritative over the file's actual logic.

  **Critical:** Remove the old `import re` + `re.compile` + `finditer` loop; the declaration must not contain an imperative `recognize()` body.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/capabilities/currency/test_grammar.py -v
  uv run pytest tests/property/test_grammar_stage_parity.py::test_currency_symbol_parity -v
  uv run ruff check paxman/capabilities/Currency/grammar/ tests/property/test_grammar_stage_parity.py
  uv run pyright
  ```

  Expected: PASS (both the existing capability test and the harness parity test), ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/capabilities/Currency/grammar/code_recognition.py paxman/capabilities/Currency/grammar/symbol_recognition.py paxman/capabilities/Currency/grammar/word_recognition.py tests/property/test_grammar_stage_parity.py tests/property/_legacy_currency_grammars.py
  git commit -m "refactor(currency): migrate Currency grammars to PipelineGrammar (S3)"
  ```

---

### Task 6 — `refactor(money): migrate Money grammars to PipelineGrammar (S4+S5 hardest)`

**Files:**
- Modify: `paxman/capabilities/Money/grammar/code_recognition.py`
- Modify: `paxman/capabilities/Money/grammar/symbol_recognition.py`
- Modify: `paxman/capabilities/Money/grammar/word_recognition.py`
- Create: `paxman/core/grammar/composer.py` (or extend `stages.py` — pick one and keep it)
- Modify: `paxman/core/grammar/__init__.py` (re-export composer)
- Test: `tests/capabilities/money/test_grammar.py` + harness parity for Money

**Goal:** The hardest composer case — S3 lexicon + S4 either-order composition + S5 `classify_amount_shape`. Proves the span-merge contract. `AMOUNT_PATTERN`/`classify_amount_shape` stay in `Money/grammar/__init__.py` and are passed as constructor args (D2).

- [ ] **Step 1: Write the failing test — Money parity with span-merge corpus**

  Extend `tests/property/test_grammar_stage_parity.py`:

  ```python
  from tests.property._legacy_money_grammars import LegacyMoneySymbolRecognition
  from paxman.capabilities.Money.grammar.symbol_recognition import (
      SymbolRecognition as MoneySymbolRecognition,
  )
  from tests.property.grammar_stage_parity import assert_grammar_parity


  @pytest.mark.property
  @pytest.mark.parametrize(
      "text",
      [
          "USD500",
          "$500",
          "500 EUR",
          "€ 1.000,50",
          "Pay $500 now",
          "US$ 1,000",
          "(500) USD",
      ],
  )
  def test_money_symbol_parity(text: str) -> None:
      assert_grammar_parity(
          LegacyMoneySymbolRecognition(), MoneySymbolRecognition(), text
      )
  ```

  Run: `uv run pytest tests/property/test_grammar_stage_parity.py::test_money_symbol_parity -v` → RED (composer not yet landed, or span-merge off by the optional space).

- [ ] **Step 2: Run test to verify it fails**

  Run as above. Expected: FAIL (span-merge contract not yet satisfied).

- [ ] **Step 3: Write minimal implementation**

  Create `paxman/core/grammar/composer.py` (or add to `stages.py` — if added to `stages.py`, delete this file entry and keep the re-export in `__init__.py`):

  ```python
  """ComposerStage — fuses lexicon hits with amount tokens (Money S4)."""

  from __future__ import annotations

  import re
  from dataclasses import dataclass, field
  from typing import Any, Generic, TypeVar

  from paxman.core.domain import RecognitionMatch
  from paxman.core.grammar.stages import PipelineState

  NotationT = TypeVar("NotationT")


  def _strip_separators(text: str, *, plus: bool = False) -> str:
      """Local helper — mirrors Phone/grammar/common.py:strip_separators."""
      # Keep digits only (and optional leading +); drop spaces/dots/dashes/parens.
      return re.sub(r"[^\d+]" if plus else r"[^\d]", "", text)


  @dataclass(frozen=True, slots=True)
  class AmountComposer(Generic[NotationT]):
      """Either-order composer: LEXICON ? AMOUNT | AMOUNT ? LEXICON.

      Must reconstruct the exact combined span [min(lex_start, amt_start),
      max(lex_end, amt_end)) including the optional single ASCII space.
      Span-merge contract (D6) is the harness gate — no off-by-one on the space.

      `pattern` and `classify` are caller-supplied (D2) — the stage is
      capability-agnostic; Money passes AMOUNT_PATTERN and classify_amount_shape.
      """

      pattern: str  # AMOUNT_PATTERN from Money — caller-supplied (D2)
      boundary_lookbehind: str = r"(?<![\w\-+\u2212])"
      boundary_lookahead: str = r"(?![\w\-+\u2212])"
      notation_fn: Any = None  # Callable[[str, str, str, str], NotationT] — (lex, amount, lex_shape, amount_shape)
      classify: Any = None  # Callable[[str], str] — classify_amount_shape
      lexicon_tokens: frozenset[str] | None = None  # for ALT rebuild if needed

      _amount_re: re.Pattern[str] = field(init=False, repr=False)

      def __post_init__(self) -> None:
          object.__setattr__(self, "_amount_re", re.compile(self.pattern))

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          if not state.matches or self.notation_fn is None:
              return state
          # Re-scan text with either-order fused pattern built from the lexicon
          # alternation + amount pattern. This mirrors the current single-regex:
          #   rf"(?<![\w\-+\u2212])(?:(?P<prefix_lex>{ALT}) ?(?P<prefix_amt>{AMOUNT_PATTERN})"
          #   rf"|(?P<suffix_amt>{AMOUNT_PATTERN}) ?(?P<suffix_lex>{ALT}))(?![\w\-+\u2212])"
          # The lexicon alternation (ALT) is derived from state.matches' notations
          # or from lexicon_tokens if supplied. The amount regex is self.pattern.
          # For each fused match, create a NEW RecognitionMatch (frozen — cannot
          # mutate) with start=min, end=max, raw_text=fused_span, notation from
          # notation_fn(lex, amount, lex_shape, classify(amount)).
          # Clear prior lexicon-only matches — the fused list replaces them.
          # If no fused match, return state unchanged (no false positives).
          # Verify by the Migration Proof Harness — byte-identical is the gate.
          # NOTE: implement the scan; the ... below is not shipped — the worker
          # must write the actual finditer + span-merge loop before marking green.
          fused: list[RecognitionMatch[NotationT]] = []
          # --- worker fills in finditer loop here (no placeholder) ---
          # Example loop shape (illustrative — adapt to actual tokens):
          #   alt = "|".join(re.escape(t) for t in sorted(self.lexicon_tokens or [], key=lambda t: (-len(t), -int(any(c.isascii() and c.isalpha() for c in t)), t)))
          #   fused_re = re.compile(rf"{self.boundary_lookbehind}(?:(?P<prefix_lex>{alt}) ?(?P<prefix_amt>{self.pattern})|(?P<suffix_amt>{self.pattern}) ?(?P<suffix_lex>{alt})){self.boundary_lookahead}")
          #   for m in fused_re.finditer(state.text):
          #       lex = m.group("prefix_lex") or m.group("suffix_lex") or ""
          #       amt = m.group("prefix_amt") or m.group("suffix_amt") or ""
          #       shape = self.classify(amt) if self.classify else "integer"
          #       notation = self.notation_fn(lex, amt, shape)
          #       fused.append(RecognitionMatch(notation=notation, start=m.start(), end=m.end(), raw_text=m.group(0)))
          # return PipelineState(text=state.text, matches=fused if fused else list(state.matches), scratch=dict(state.scratch))
          return PipelineState(
              text=state.text,
              matches=fused if fused else list(state.matches),
              scratch=dict(state.scratch),
          )
  ```

  > **Oracle fix — Rev.1:** The prior `...` placeholder hid the span-merge loop and the frozen-dataclass replacement contract. `RecognitionMatch` is `frozen=True, slots=True` — the composer cannot mutate `start/end/raw_text` in place; it must **create new `RecognitionMatch` instances**. The illustrative loop above is the required shape; the worker must land the real `finditer` loop with the exact ` ?` space handling before the harness can pass. No `...` placeholder is shipped.

  Wire `Money/grammar/symbol_recognition.py` (after migration):

  ```python
  from paxman.capabilities.Money.grammar import AMOUNT_PATTERN, classify_amount_shape
  from paxman.capabilities.Money.grammar.data.currency_symbols import SYMBOL_TOKENS
  from paxman.capabilities.Money.notation import MoneyNotation
  from paxman.core.grammar import (
      BoundaryGuard,
      LexiconStage,
      PipelineGrammar,
      StandardPre,
  )
  from paxman.core.grammar.composer import AmountComposer


  class SymbolRecognition(PipelineGrammar[MoneyNotation]):
      name = "symbol_recognition"
      semantics = "symbol_recognition"
      single_value = True
      pre = StandardPre(empty_guard=True)
      lexicon = LexiconStage(
          tokens=SYMBOL_TOKENS, boundary=BoundaryGuard.word_sign(), longest_first=True
      )
      composer = AmountComposer(
          pattern=AMOUNT_PATTERN,
          order="either",
          lexicon_first=True,
          classify=classify_amount_shape,
      )
      post = AmountShapePost(
          classify=classify_amount_shape
      )  # if needed, or fold into composer
  ```

  The `post` here is `AmountShapePost` that calls `classify_amount_shape(amount)` to set `MoneyNotation.amount_shape` — if the composer already classifies, the post may be folded. Keep the pipeline's post stage for `shape` assignment (`classify_amount_shape`) so the composer stays span-focused.

  **Span-merge contract (D6):** For `"$500"` with `"$"` at `[0,1)` and `"500"` at `[1,4)` or `[2,4)` (space case), the composer must emit `[0,4)` with `raw_text="$500"` / `"$ 500"` matching the old single regex exactly. No off-by-one on the optional space.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/capabilities/money/test_grammar.py -v
  uv run pytest tests/property/test_grammar_stage_parity.py::test_money_symbol_parity -v
  uv run ruff check paxman/capabilities/Money/grammar/ paxman/core/grammar/composer.py tests/property/test_grammar_stage_parity.py
  uv run pyright
  ```

  Expected: PASS, ruff/pyright clean, harness gate green.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/capabilities/Money/grammar/code_recognition.py paxman/capabilities/Money/grammar/symbol_recognition.py paxman/capabilities/Money/grammar/word_recognition.py paxman/core/grammar/composer.py paxman/core/grammar/__init__.py tests/property/test_grammar_stage_parity.py
  git commit -m "refactor(money): migrate Money grammars to PipelineGrammar (S4+S5)"
  ```

---

### Task 7 — `refactor(siunit): migrate SIUnit grammars to PipelineGrammar (S3+S4+S5)`

**Files:**
- Modify: `paxman/capabilities/SIUnit/grammar/symbol_recognition.py`
- Modify: `paxman/capabilities/SIUnit/grammar/name_recognition.py`
- Modify: `paxman/capabilities/SIUnit/grammar/compound_recognition.py`
- Modify: `paxman/core/grammar/stages.py` (add `SiSplitPrefixClassifier` post stage)
- Test: `tests/capabilities/si_unit/test_grammar.py` + harness parity for SIUnit

**Goal:** Prove S3 lexicon + S5 split-prefix classifier + S4 compound (`UNIT(SEP UNIT){1,3}`). The `°` degree guard and `PREFIX_ONLY_SYMBOLS` filtering are preserved.

- [ ] **Step 1: Write the failing test — SIUnit parity**

  ```python
  from tests.property._legacy_siunit_grammars import (
      LegacySymbolRecognition as LegacySiSymbol,
  )
  from paxman.capabilities.SIUnit.grammar.symbol_recognition import (
      SymbolRecognition as SiSymbol,
  )
  from tests.property.grammar_stage_parity import assert_grammar_parity


  @pytest.mark.property
  @pytest.mark.parametrize(
      "text",
      [
          "kg",
          "MHz",
          "kilo gram",
          "k g",
          "m/s",
          "m/s²",
          "kg/m/s",
          "degree celsius",
          "m·kg",
          "kPa",
      ],
  )
  def test_siunit_symbol_parity(text: str) -> None:
      assert_grammar_parity(LegacySiSymbol(), SiSymbol(), text)
  ```

  Run: `uv run pytest tests/property/test_grammar_stage_parity.py::test_siunit_symbol_parity -v` → RED (split-prefix classifier not yet wired).

- [ ] **Step 2: Run test to verify it fails**

  Run as above. Expected: FAIL (shape `split_symbol_prefix` vs `symbol` mismatch, or span error).

- [ ] **Step 3: Write minimal implementation**

  Migration sketch for `SIUnit/grammar/symbol_recognition.py`:

  ```python
  from paxman.capabilities.SIUnit.grammar.data.prefix_tokens import PREFIX_SYMBOL_TOKENS
  from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
  from paxman.capabilities.SIUnit.notation import SIUnitNotation
  from paxman.core.grammar import (
      BoundaryGuard,
      LexiconStage,
      PipelineGrammar,
      StandardPre,
  )

  PREFIX_ONLY_SYMBOLS = frozenset(PREFIX_SYMBOL_TOKENS) - frozenset({"a", "d", "h", "m"})


  class SymbolRecognition(PipelineGrammar[SIUnitNotation]):
      name = "symbol_recognition"
      semantics = "symbol_recognition"
      pre = StandardPre(empty_guard=True)
      lexicon = LexiconStage(
          tokens=SYMBOL_TOKENS
          | PREFIX_SYMBOL_TOKENS,  # or two-stage: prefix alt + unit alt
          boundary=BoundaryGuard.degree_word_sign(),
          longest_first=True,
      )
      post = SiSplitPrefixClassifier(prefix_only=PREFIX_ONLY_SYMBOLS)
  ```

  `SiSplitPrefixClassifier` (post stage) — concrete, frozen-safe — mirrors the current inline classifier at `symbol_recognition.py:68-76` / `name_recognition.py:54-62`:

  ```python
  @dataclass(frozen=True, slots=True)
  class SiSplitPrefixClassifier(Generic[NotationT]):
      """Post stage for SIUnit split-prefix shape assignment (S5).

      The lexicon stage emits one span for "kilo gram" (split form) or "kg" (attached).
      This post stage splits raw_text on whitespace and checks prefix_only to set
      notation.shape to "split_word_prefix" / "split_symbol_prefix" vs "symbol"/"name".
      Frozen-safe — creates new RecognitionMatch with updated notation.
      """

      prefix_only: frozenset[str]

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          new: list[RecognitionMatch[NotationT]] = []
          for m in state.matches:
              parts = m.raw_text.split()
              if len(parts) >= 2 and parts[0] in self.prefix_only:
                  # Rebuild notation with split shape — m.notation is frozen.
                  # Worker must branch on notation type: SIUnitNotation(symbol vs name).
                  # Example (symbol case):
                  #   from paxman.capabilities.SIUnit.notation import SIUnitNotation
                  #   notation: Any = SIUnitNotation(text=m.raw_text, shape="split_symbol_prefix")
                  # Preserve the lexicon's span (start/end/raw_text unchanged — split is intra-span).
                  from paxman.capabilities.SIUnit.notation import (
                      SIUnitNotation,
                  )  # local to avoid core→capability import at module load if shared

                  # Shape depends on originating grammar: symbol vs name — worker
                  # parameterizes via constructor (e.g. split_shape="split_symbol_prefix").
                  shape = (
                      "split_word_prefix"
                      if " " in m.raw_text and m.raw_text.split()[0] in self.prefix_only
                      else m.notation.shape
                  )  # type: ignore[attr-defined]
                  notation: Any = SIUnitNotation(text=m.raw_text, shape=shape)  # type: ignore[arg-type]
                  new.append(
                      RecognitionMatch(
                          notation=notation, start=m.start, end=m.end, raw_text=m.raw_text
                      )
                  )
              else:
                  new.append(m)
          return PipelineState(text=state.text, matches=new, scratch=dict(state.scratch))
  ```

  > **Oracle fix — Rev.1:** Prior sketch had `...` and omitted the frozen replacement. The split-prefix shape assignment is a **notation-shape mutation** on a frozen `RecognitionMatch` — must create a new match. Also the lexicon span for `"kilo gram"` is a single fused span `[0,9)` (not two spans merged by composer) — the post only **relabels shape**, it does not merge spans. Clarified above.

  `compound_recognition.py` migrates to `RegexStage` or a dedicated `CompoundComposer` that builds `_UNIT (SEP _UNIT){1,3}` from `grammar/data/compound_tokens.py`.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/capabilities/si_unit/test_grammar.py -v
  uv run pytest tests/property/test_grammar_stage_parity.py::test_siunit_symbol_parity -v
  uv run ruff check paxman/capabilities/SIUnit/grammar/ paxman/core/grammar/stages.py tests/property/test_grammar_stage_parity.py
  uv run pyright
  ```

  Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/capabilities/SIUnit/grammar/symbol_recognition.py paxman/capabilities/SIUnit/grammar/name_recognition.py paxman/capabilities/SIUnit/grammar/compound_recognition.py paxman/core/grammar/stages.py tests/property/test_grammar_stage_parity.py
  git commit -m "refactor(siunit): migrate SIUnit grammars to PipelineGrammar (S3+S4+S5)"
  ```

---

### Task 8 — `refactor(phone,url): migrate Phone + URL grammars to PipelineGrammar (S5)`

**Files:**
- Modify: `paxman/capabilities/Phone/grammar/e164_recognition.py`
- Modify: `paxman/capabilities/Phone/grammar/tel_uri_recognition.py`
- Modify: `paxman/capabilities/Phone/grammar/international_00_recognition.py`
- Modify: `paxman/capabilities/Phone/grammar/national_recognition.py`
- Modify: `paxman/capabilities/URL/grammar/absolute_uri_recognition.py`
- Modify: `paxman/core/grammar/stages.py` (add `E164Trim`, `UrlParenBalance` post stages)
- Test: `tests/capabilities/phone/test_grammar.py`, `tests/capabilities/url/test_grammar.py` + harness parity

**Goal:** Prove S5 trims in isolation — `E164Trim(15)` with `start+len(trimmed)` span fixup and URL paren-balance with `start+len(trimmed)` span fixup. No lexicon/composer needed.

- [ ] **Step 1: Write the failing test — Phone + URL parity**

  ```python
  from tests.property._legacy_phone_grammars import LegacyE164
  from paxman.capabilities.Phone.grammar.e164_recognition import E164Grammar
  from tests.property.grammar_stage_parity import assert_grammar_parity


  @pytest.mark.property
  @pytest.mark.parametrize(
      "text",
      [
          "+15551234567",
          "+1 555 123 4567",
          "+15551234567 5551234567",  # runaway — must trim to 15 digits
          "tel:+15551234567",  # must NOT match e164 (colon guard)
          "user+123@example.com",  # must NOT match e164
      ],
  )
  def test_phone_e164_parity(text: str) -> None:
      assert_grammar_parity(LegacyE164(), E164Grammar(), text)
  ```

  URL parity:

  ```python
  from tests.property._legacy_url_grammars import LegacyAbsoluteUri
  from paxman.capabilities.URL.grammar.absolute_uri_recognition import (
      AbsoluteUriRecognition,
  )


  @pytest.mark.property
  @pytest.mark.parametrize(
      "text",
      [
          "https://example.com/other",
          "See https://example.com/path_(with_parens)) trailing",
          "mailto:user@example.com",
          "https://example.com:443/path/../other",
      ],
  )
  def test_url_parity(text: str) -> None:
      assert_grammar_parity(LegacyAbsoluteUri(), AbsoluteUriRecognition(), text)
  ```

  Run: `uv run pytest tests/property/test_grammar_stage_parity.py::test_phone_e164_parity tests/property/test_grammar_stage_parity.py::test_url_parity -v` → RED (trim logic not yet wired).

- [ ] **Step 2: Run test to verify it fails**

  Run as above. Expected: FAIL (span `end` mismatch: `match.end()` vs `start+len(trimmed)`).

- [ ] **Step 3: Write minimal implementation**

  Add post stages to `paxman/core/grammar/stages.py` (no `...` — concrete logic, frozen replacement):

  ```python
  import re
  from dataclasses import dataclass
  from typing import Any, Generic, TypeVar

  from paxman.core.domain import RecognitionMatch
  from paxman.core.grammar.stages import PipelineState

  NotationT = TypeVar("NotationT")


  def _trim_to_e164_boundary(raw: str, max_digits: int = 15) -> str:
      """Trim runaway raw match at last digit-run group within limit (mirrors Phone/grammar/e164_recognition.py)."""
      runs = list(re.finditer(r"\d+", raw))
      total = 0
      for idx, run in enumerate(runs):
          total += len(run.group(0))
          if total > max_digits:
              if idx == 0:
                  return raw
              return raw[: runs[idx - 1].end()]
      return raw


  @dataclass(frozen=True, slots=True)
  class E164Trim(Generic[NotationT]):
      """Post stage for Phone E.164 — trims runaway spans and recomputes end/value.

      `RecognitionMatch` is frozen — the stage creates NEW matches with
      `end = start + len(trimmed)` and `value = strip_separators(trimmed)`.
      The regex stage's notation_fn must NOT call strip_separators; the post stage owns it.
      """

      max_digits: int = 15

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          new: list[RecognitionMatch[NotationT]] = []
          for m in state.matches:
              trimmed = _trim_to_e164_boundary(m.raw_text, self.max_digits)
              if trimmed != m.raw_text:
                  # Recompute notation.value from trimmed; PhoneNotation is frozen so build new.
                  # Worker wires the real PhoneNotation(shape="e164", value=_strip_separators(trimmed, plus=True)).
                  # The stage must reconstruct notation — access via m.notation and produce new.
                  from paxman.capabilities.Phone.notation import PhoneNotation

                  notation: Any = PhoneNotation(
                      shape="e164", value=re.sub(r"[^\d+]", "", trimmed)
                  )
                  new.append(
                      RecognitionMatch(
                          notation=notation,
                          start=m.start,
                          end=m.start + len(trimmed),
                          raw_text=trimmed,
                      )
                  )
              else:
                  new.append(m)
          return PipelineState(text=state.text, matches=new, scratch=dict(state.scratch))


  @dataclass(frozen=True, slots=True)
  class UrlParenBalance(Generic[NotationT]):
      """Post stage for URL — paren-balance trim and bare-scheme drop.

      Mirrors URL/grammar/absolute_uri_recognition.py: excess = count(")") - count("(");
      trim trailing ")" while excess>0; drop spans where len(raw_span) <= scheme_end+1.
      Also frozen-safe — creates new RecognitionMatch with end = start + len(trimmed).
      """

      def run(self, state: PipelineState[NotationT]) -> PipelineState[NotationT]:
          new: list[RecognitionMatch[NotationT]] = []
          for m in state.matches:
              raw = m.raw_text
              excess = raw.count(")") - raw.count("(")
              trim = 0
              while trim < excess and raw[-(trim + 1)] == ")":
                  trim += 1
              if trim:
                  raw = raw[:-trim]
              scheme_end = raw.find(":")
              if len(raw) <= scheme_end + 1:
                  continue  # bare scheme — drop (D16)
              if raw != m.raw_text:
                  from paxman.capabilities.URL.notation import URLNotation

                  notation: Any = URLNotation(text=raw)
                  new.append(
                      RecognitionMatch(
                          notation=notation,
                          start=m.start,
                          end=m.start + len(raw),
                          raw_text=raw,
                      )
                  )
              else:
                  new.append(m)
          return PipelineState(text=state.text, matches=new, scratch=dict(state.scratch))
  ```

  > **Oracle fix — Rev.1:** Prior `...` hid the frozen-replacement contract and the bare-scheme drop. `RecognitionMatch` is `frozen=True` — post stages cannot mutate `m.raw_text`/`m.end` in place; they must create **new** `RecognitionMatch` instances (as above). `E164Trim` owns `strip_separators` / digit reconstruction — the `RegexStage.notation_fn` must emit raw `m.group(0)` only. `UrlParenBalance` must drop bare-scheme spans (`len(raw) <= scheme_end+1`) — without this, `"http:"` would emit a false positive.

  Wire Phone `e164_recognition.py` (regex stage emits raw only — post owns normalization):

  ```python
  from paxman.capabilities.Phone.notation import PhoneNotation
  from paxman.core.grammar import PipelineGrammar
  from paxman.core.grammar.stages import E164Trim, RegexStage, StandardPre


  class E164Grammar(PipelineGrammar[PhoneNotation]):
      name = "e164_recognition"
      semantics = "e164_international"
      single_value = True
      pre = StandardPre(empty_guard=True)
      # Regex stage emits raw value — post stage recomputes value=end+len(trimmed)
      regex = RegexStage(
          r"(?<![\w:.])\+\d[\d\s().\-]*(?<=\d)",
          notation_fn=lambda m: PhoneNotation(shape="e164", value=m.group(0)),
      )
      post = E164Trim(max_digits=15)
  ```

  Wire URL `absolute_uri_recognition.py` (same — regex emits raw, post trims and drops bare-scheme):

  ```python
  from paxman.capabilities.URL.notation import URLNotation
  from paxman.core.grammar import PipelineGrammar
  from paxman.core.grammar.stages import RegexStage, StandardPre, UrlParenBalance


  class AbsoluteUriRecognition(PipelineGrammar[URLNotation]):
      name = "absolute_uri_recognition"
      semantics = "absolute_uri_recognition"
      single_value = True
      pre = StandardPre(empty_guard=True)
      regex = RegexStage(
          r"(?<![A-Za-z0-9+.\-])[A-Za-z][A-Za-z0-9+.\-]*:[^ <>\"\x00-\x08\x0B\x0C\x0E-\x1F\x7F]*[^ <>\"\x00-\x08\x0B\x0C\x0E-\x1F\x7F]",
          notation_fn=lambda m: URLNotation(text=m.group(0)),
      )
      post = UrlParenBalance()
  ```

  The post stage is responsible for the span fixup (`end = start + len(trimmed)`) and `strip_separators` / paren-balance. The regex `notation_fn` above intentionally uses `m.group(0)` raw — the post recomputes the canonical `value`/`text`.

  Migrate `tel_uri`, `international_00`, `national` with S1 `RegexStage` declarations (no post trim needed, unless national needs its own guard).

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/capabilities/phone/test_grammar.py tests/capabilities/url/test_grammar.py -v
  uv run pytest tests/property/test_grammar_stage_parity.py::test_phone_e164_parity tests/property/test_grammar_stage_parity.py::test_url_parity -v
  uv run ruff check paxman/capabilities/Phone/grammar/ paxman/capabilities/URL/grammar/ paxman/core/grammar/stages.py tests/property/test_grammar_stage_parity.py
  uv run pyright
  ```

  Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/capabilities/Phone/grammar/e164_recognition.py paxman/capabilities/Phone/grammar/tel_uri_recognition.py paxman/capabilities/Phone/grammar/international_00_recognition.py paxman/capabilities/Phone/grammar/national_recognition.py paxman/capabilities/URL/grammar/absolute_uri_recognition.py paxman/core/grammar/stages.py tests/property/test_grammar_stage_parity.py
  git commit -m "refactor(phone,url): migrate Phone and URL grammars to PipelineGrammar (S5)"
  ```

---

### Task 9 — `refactor(capabilities): migrate remaining S1 grammars (Date, Email, IP, ISBN)`

**Files:**
- Modify: `paxman/capabilities/Date/grammar/iso8601_recognition.py`
- Modify: `paxman/capabilities/Date/grammar/us_recognition.py`
- Modify: `paxman/capabilities/Date/grammar/european_recognition.py`
- Modify: `paxman/capabilities/Date/grammar/slash_iso_recognition.py`
- Modify: `paxman/capabilities/Email/grammar/standard_recognition.py`
- Modify: `paxman/capabilities/Email/grammar/obfuscated_recognition.py`
- Modify: `paxman/capabilities/Email/grammar/localhost_recognition.py`
- Modify: `paxman/capabilities/IP/grammar/ipv4_recognition.py`
- Modify: `paxman/capabilities/IP/grammar/ipv6_recognition.py`
- Modify: `paxman/capabilities/ISBN/grammar/isbn13_recognition.py`
- Modify: `paxman/capabilities/ISBN/grammar/isbn10_recognition.py`
- Modify: `paxman/capabilities/Country/grammar/alpha2_recognition.py`
- Modify: `paxman/capabilities/Country/grammar/alpha3_recognition.py`
- Modify: `paxman/capabilities/Country/grammar/numeric_recognition.py`
- Test: `tests/capabilities/*/test_grammar.py` + harness parity for each

**Goal:** Mechanical migration — S1 pure `RegexStage` declarations with `StandardPre`. No composer, no post. ISBN hyphen/space tolerance stays regex-native (not a post-trim — ADR §Context clarifies `isbn13_recognition.py:10-11,26` is `(?=((?:\d[ -]?){12}\d)(?![\d]))\1` + `m.group(1)`).

- [ ] **Step 1: Write the failing test — S1 parity (sample one, repeat per grammar)**

  ```python
  from tests.property._legacy_date_grammars import LegacyISO8601
  from paxman.capabilities.Date.grammar.iso8601_recognition import ISO8601DateGrammar
  from tests.property.grammar_stage_parity import assert_grammar_parity


  @pytest.mark.property
  @pytest.mark.parametrize(
      "text",
      ["2026-01-15", "2026/01/15", "01/02/2026", "12026-01-15", "foo 2026-01-15 bar"],
  )
  def test_date_iso8601_parity(text: str) -> None:
      assert_grammar_parity(LegacyISO8601(), ISO8601DateGrammar(), text)
  ```

  Run: `uv run pytest tests/property/test_grammar_stage_parity.py::test_date_iso8601_parity -v` → RED (not yet migrated) or GREEN (if already migrated — extend to a not-yet-migrated S1 grammar).

- [ ] **Step 2: Run test to verify it fails**

  Run as above. Expected: FAIL until migration lands.

- [ ] **Step 3: Write minimal implementation — migrate each S1 grammar**

  Example for `Date/grammar/iso8601_recognition.py` (after migration):

  ```python
  """ISO 8601 date recognition — PipelineGrammar declaration."""

  from __future__ import annotations

  import re

  from paxman.capabilities.Date.notation import DateNotation
  from paxman.core.grammar import PipelineGrammar
  from paxman.core.grammar.stages import RegexStage, StandardPre


  def _iso_notation(m: re.Match[str]) -> DateNotation:
      return DateNotation(N1=m.group(1), N2=m.group(2), N3=m.group(3))


  class ISO8601DateGrammar(PipelineGrammar[DateNotation]):
      name = "iso8601_recognition"
      semantics = "iso8601_calendar_date"
      pre = StandardPre(empty_guard=True)
      regex = RegexStage(
          r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", notation_fn=_iso_notation
      )
  ```

  Repeat for US/European/slash_iso with their respective patterns and `us_calendar_date` / `european_calendar_date` semantics (already coalesced per ADR-0003 D6). For ISBN, keep the lookahead-digit-extraction pattern verbatim.

  **Country alpha2/alpha3/numeric:** `RegexStage` with `\b` / digit patterns and their respective `BoundaryGuard.word_only` / `digit` guards. **Do not migrate `Country/name_recognition.py` here** — it is S2 (`WholeInputLookup`), migrate it alongside this task as:

  ```python
  from paxman.capabilities.Country.grammar.data.country_names import (
      COUNTRY_NAME_KEYS,
  )  # or the real table
  from paxman.capabilities.Country.grammar.name_normalization import normalize_name
  from paxman.capabilities.Country.notation import CountryNotation
  from paxman.core.grammar import PipelineGrammar, StandardPre
  from paxman.core.grammar.stages import WholeInputLookup


  class NameGrammar(PipelineGrammar[CountryNotation]):
      name = "name_recognition"
      semantics = "name_recognition"
      single_value = True
      pre = StandardPre(empty_guard=True)
      lexicon = WholeInputLookup(
          keys=COUNTRY_NAME_KEYS,
          normalizer=normalize_name,
          notation_fn=lambda trimmed: CountryNotation(shape="name", value=trimmed),
      )
  ```

  Verify the real `COUNTRY_NAME_KEYS` frozenset name from `Country/grammar/name_recognition.py:14` (`_KNOWN_NAME_KEYS`) and the `normalize_name` helper path before wiring. **Oracle fix — Rev.1:** `WholeInputLookup` with `normalizer=None` defaults to `lower()` and would break `Country/name_recognition` parity (which uses `normalize_name`, not `lower`). The Country wiring above **must** pass `normalizer=normalize_name`; the `lower()` default is only for the Task 3 Currency unit test sandbox. Without this param the harness fails on `"United States"` vs `"united states"` casing.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/capabilities/date tests/capabilities/email tests/capabilities/ip tests/capabilities/isbn tests/capabilities/country -v
  uv run pytest tests/property/test_grammar_stage_parity.py -k "date or email or ip or isbn or country" -v
  uv run ruff check paxman/capabilities/Date/grammar/ paxman/capabilities/Email/grammar/ paxman/capabilities/IP/grammar/ paxman/capabilities/ISBN/grammar/ paxman/capabilities/Country/grammar/ tests/property/test_grammar_stage_parity.py
  uv run pyright
  ```

  Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/capabilities/Date/grammar/ paxman/capabilities/Email/grammar/ paxman/capabilities/IP/grammar/ paxman/capabilities/ISBN/grammar/ paxman/capabilities/Country/grammar/ tests/property/test_grammar_stage_parity.py
  git commit -m "refactor(capabilities): migrate remaining S1 grammars to PipelineGrammar"
  ```

---

### Task 10 — `refactor: retire legacy helpers + docs sweep`

**Files:**
- Modify: `paxman/capabilities/Phone/grammar/common.py` — delete `strip_separators` or move it into `E164Trim` stage internals (flagged non-pattern in `capabilities/AGENTS.md`)
- Modify: `paxman/capabilities/Country/name_normalization.py` — become stage internals or deleted (same flag)
- Modify: `HOW_TO_ADD_NEW_CAPABILITY.md` — reference `paxman/core/grammar/stages.py` as entry point for new grammars
- Modify: `paxman/capabilities/AGENTS.md` — sanctioned strategies now include the staged pipeline
- Test: full suite must stay green after deletions

**Goal:** Remove the two helpers flagged as non-patterns, sweep docs to reference the pipeline.

- [ ] **Step 1: Write the failing test — helpers are no longer importable from old paths**

  ```python
  def test_strip_separators_moved_to_stage() -> None:
      # After retirement, the old helper is gone — stage internals own it.
      import pytest

      with pytest.raises(ImportError):
          from paxman.capabilities.Phone.grammar.common import strip_separators

          _ = strip_separators
  ```

  Actually: if the helper is kept as a stage internal (re-exported), the test should instead assert that `paxman.capabilities.Phone.grammar.common` no longer exists or that the pipeline tests still pass without it. The RED here is: delete the file, run `uv run pytest tests/capabilities/phone -v` → FAIL if any grammar still imports `common`.

- [ ] **Step 2: Run test to verify it fails**

  Run: `uv run pytest tests/capabilities/phone -v`
  Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.capabilities.Phone.grammar.common'` after deletion, until imports are updated to stage internals.

- [ ] **Step 3: Write minimal implementation**

  - Inline `strip_separators` logic into `E164Trim.run` (or keep it as a private `_strip_separators` inside `stages.py` — do not keep `common.py` as a public grammar helper).
  - Inline `normalize_name` into `WholeInputLookup.normalizer` or a `CountryPre` stage.
  - Delete `paxman/capabilities/Phone/grammar/common.py` and `paxman/capabilities/Country/name_normalization.py` if fully inlined.
  - Update `HOW_TO_ADD_NEW_CAPABILITY.md` Step "Add recognition grammars" to point to `paxman/core/grammar/stages.py` + `boundary.py` + `lexicon.py` as the entry point.

- [ ] **Step 4: Run test to verify it passes**

  Run:
  ```bash
  uv run pytest tests/capabilities/phone tests/capabilities/country -v
  uv run ruff check paxman/ tests/
  uv run pyright
  uv run import-linter lint
  ```

  Expected: PASS, import-linter clean (no capability imports in `paxman.core.grammar`).

- [ ] **Step 5: Commit**

  ```bash
  git add paxman/capabilities/Phone/grammar/common.py paxman/capabilities/Country/name_normalization.py paxman/core/grammar/stages.py HOW_TO_ADD_NEW_CAPABILITY.md paxman/capabilities/AGENTS.md
  git commit -m "refactor: retire legacy helpers and sweep docs for staged pipeline"
  ```

---

### Task 11 — Final gate (no commit)

**Verify — full pre-PR gate** (authoritative per `.github/workflows/ci.yml`; ruff lint and format are CI-scoped to `paxman/ tests/`):

```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ \
  && uv run pyright && uv run import-linter lint && uv run pytest
```

Coverage gate (one include pattern per package — brace shorthand `paxman/{core,capabilities,engine,api}/*` is not expanded by the installed coverage version and reports "No data to report"):

```bash
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
```

Migration Proof Harness gate (must be green on every migration PR):

```bash
uv run pytest tests/property/test_grammar_stage_parity.py -v
```

Zero-grep proof that no grammar file hard-codes a lookaround literal after migration (each grammar references a `BoundaryGuard`):

```bash
grep -rn "\\\\?<!\[" paxman/capabilities/*/grammar/*_recognition.py
```

Expected: no matches (all lookarounds live in `paxman/core/grammar/boundary.py`).

If any gate fails, fix it in a follow-up commit — never by weakening a test, never by restoring bespoke `recognize()` bodies, never by editing `docs/adr/*` (historical).

---

## §3 Traps

1. **Do not embed `AMOUNT_PATTERN` in core.** `AmountComposer` accepts `pattern` and `classify` as constructor args (D2). Copying `AMOUNT_PATTERN` into `paxman/core/grammar/` fails `import-linter lint` and violates `paxman/core/AGENTS.md` ("capability-agnostic"). The composer must remain generic; Money supplies its regex.

2. **Span-merge off-by-one on the optional space.** The old Money single-regex includes ` ?` (one optional ASCII space) between symbol and amount. The `AmountComposer` must emit the space as part of `raw_text` when present and exclude it from the amount token's classification — the old grammar does `m.group("prefix_symbol")` / `m.group("prefix_amount")` separately. A naive `f"{lex}{amt}"` loses the space; a naive `f"{lex} {amt}"` invents one that was not there.

3. **`WholeInputLookup` must emit original `trimmed`, not normalized key.** `Country/name_recognition.py:70,76-80` is explicit: `value=trimmed` (original case), `raw_text=trimmed`, `start` accounts for leading whitespace. Emitting the lowercased key breaks `Country/name_recognition` parity for `"United States"` vs `"united states"` — the notation value preserves casing.

4. **`E164Trim` and `UrlParenBalance` fix `end`, not `match.end()`.** `e164_recognition.py: _trim_to_e164_boundary` then `end = match.start() + len(raw_text)` where `raw_text` is the trimmed string (`recognize` body). `absolute_uri_recognition.py: UrlParenBalance` then `end = start + len(raw_span)` after trimming `")"`. Using `match.end()` re-introduces the runaway span that the trim was meant to remove — the harness corpus includes the runaway case (`"+15551234567 5551234567"`) to catch this. (Line numbers omitted — verify against live file at migration start.)

5. **Country name is the exception — it skips regex.** The pipeline must allow `regex=None`. A pipeline that forces every input through a regex reintroduces the duct-tape it was meant to remove (ADR Consequences/Negative).

6. **SIUnit `°` differentiator.** `degree_word_sign` includes `°`; `word_sign` does not. A single `word_sign` guard for both SIUnit and Currency loses the degree-char boundary that `SIUnit/symbol_recognition.py:38` relies on (`(?<![°\w\-+\u2212/·⋅])`).

7. **Benchmark is not a gate.** `benchmarks/harness.py` is informational, `continue-on-error: true` in CI (D8). Do not block a migration PR on a benchmark regression unless a separate ADR gates it (ADR Open Question 3).

8. **Generated artifacts trip the zero-grep proof.** `htmlcov/`, `.hypothesis/`, `.pytest_cache/` contain stale matches and are gitignored — exclude them from any `grep` proof (same precedent as ADR-0003 plan D9). The Task 11 proof command scopes to `paxman/capabilities/*/grammar/*_recognition.py` to avoid false positives.

9. **Import-linter inherits leaf status — confirm on landing.** Adding `paxman/core/grammar` as a subpackage of `paxman.core` is expected to inherit the leaf with no new `importlinter` config. Run `uv run import-linter lint` at Task 1 landing; if it requires a new layer entry, add it in Task 1's commit (ADR §2 note).

10. **Legacy helper retirement is last-mile, not first-mile.** `Phone/grammar/common.py:strip_separators` and `Country/name_normalization.py` are flagged non-patterns in `capabilities/AGENTS.md`, but grammars migrate *before* the helpers are deleted — deleting too early breaks Tasks 5-8. Task 10 is the retirement window.

---

## §4 Definition of Done

- [ ] `paxman/core/grammar/` lands with `stages.py` (Stage Protocol + 5 stage types), `boundary.py` (BoundaryGuard family), `lexicon.py` (LexiconAlternation), `pipeline.py` (PipelineGrammar) — all with `ruff + pyright + import-linter` clean and unit tests (`test_pipeline_stages`, `test_boundary_guards`, `test_lexicon_alternation`).
- [ ] Migration Proof Harness (`tests/property/test_grammar_stage_parity.py` + helper) lands and is green on the curated corpus (Country normalized-key vs original-case, Phone E164 trim, URL paren-balance, Money either-order span-merge, SIUnit split-prefix, ISBN hyphen/space tolerance).
- [ ] All 29 grammars migrated to `PipelineGrammar` declarations — byte-identical `RecognitionMatch` output proven by the harness; engine routing (`semantics`) and candidate dedup untouched.
- [ ] Currency+Money migration proves S3→S4 and span-merge; SIUnit proves S3+S5 split-prefix + S4 compound; Phone+URL prove S5 trims in isolation; remaining S1 migration is mechanical.
- [ ] `Phone/grammar/common.py:strip_separators` and `Country/name_normalization.py` retired (become stage internals or deleted); no capability helper re-export leaks back into `paxman.core.grammar`.
- [ ] No grammar file hard-codes a lookaround literal — boundary guards have one definition each in `boundary.py`.
- [ ] `AMOUNT_PATTERN`/`classify_amount_shape` remain in `Money/grammar/__init__.py` and are passed to the composer as params — `paxman.core.grammar` has no capability imports (`import-linter lint` clean).
- [ ] Full pre-PR gate green: `ruff check + ruff format --check + pyright + import-linter lint + pytest` and 95% coverage per package (`paxman/core`, `paxman/capabilities`, `paxman/engine`, `paxman/api`).
- [ ] Import-linter layer `paxman.core.grammar → (no capability imports)` confirmed; `paxman.capabilities.*.grammar → paxman.core.grammar + paxman.core.domain` holds.

---

## References

- `docs/adr/0008-staged-recognition-pipeline.md` Rev.1 (Accepted 2026-08-20) — authoritative spec
- `paxman/core/domain.py` — `Grammar`, `RecognitionMatch`, `Rule`, `Provenance`
- `paxman/core/capability.py` — `Capability`, `get_grammars`
- `paxman/engine/orchestrator.py` — `_recognize` (L185 `grammar.recognize(text)`), `_collect_candidates`, `_enforce_single_value_invariant`
- `paxman/capabilities/*/grammar/**` — 29 grammar files, 56 files surveyed
- `paxman/capabilities/Money/grammar/__init__.py` — `AMOUNT_PATTERN`, `classify_amount_shape` (remain in Money)
- `paxman/capabilities/AGENTS.md` — sanctioned strategies, legacy-exception flags
- `paxman/core/AGENTS.md` — core is capability-agnostic (no capability imports)
- `HOW_TO_ADD_NEW_CAPABILITY.md` — extended recognition-strategy section (scanner, format-candidate, parser combinators, Unicode-property, automaton)
- `benchmarks/harness.py` + `benchmarks/README.md` — informational, non-blocking (50 iterations in CI, baseline tracked not gated)
- `.github/workflows/ci.yml` — authoritative pre-PR gate (ruff, pyright, import-linter, data-drift checks, benchmark non-blocking, pytest + 95% per-package coverage)
