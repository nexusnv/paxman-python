# Capability Scaffolder — Implementation Plan

| **Title** | `tools/new_capability.py`: generate the unanimous capability surface (skeleton + test stubs + registration wiring) and restructure HOW_TO from instructions to commentary |
| **Date** | 2026-08-17 |
| **Status** | Planned — not started |
| **Branch** | `feature/capability-scaffolder` (one commit per task) |
| **Origin** | `docs/reports/2026-08-17-architecture-review.md` §9 Near-Term item 1 (§5 deterrent 1: "the reading tax") |
| **Depends on** | **Hard:** `2026-08-17-stale-surface-cleanup.md` Tasks 1–2 landed first — templates must emit **no `as_list()`** and **no `Capability.version`** (those surfaces must already be gone). Rebase onto its branch if running in parallel. |
| **Supersedes** | Nothing |

> **For agentic workers.** Execute one task at a time. Task 1 is TDD:
> **Step 1 RED** (failing scaffolder tests first), **Step 2 GREEN**
> (implement the tool), then the scoped verify and the commit. Task 2 is a
> manual-QA evidence task with **no commit** (throwaway worktree).
> Task 3 is docs (RED-exempt). Task 4 is a verify-only gate with
> **no commit**. Commit with the exact messages given.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | Task 1 — scaffolder tool + tests (TDD) | ☐ pending | |
> | Task 2 — full-gate proof on a scaffolded throwaway (no commit) | ☐ pending | |
> | Task 3 — HOW_TO restructure + contributor-doc pointers | ☐ pending | |
> | Task 4 — final gate (no commit) | ☐ pending | |

---

## §1 Cross-Part Contract

### Goal

A stdlib-only generator, `tools/new_capability.py`, that emits a complete,
gate-passing capability skeleton — package files, one placeholder grammar +
rule with full enforced metadata, test stubs, and the
`paxman/capabilities/__init__.py` wiring — so a contributor's job changes
from "hand-assemble the unanimous surface from 62KB of prose" to "verify
and fill in the domain". Then restructure `HOW_TO_ADD_NEW_CAPABILITY.md` to
lead with the scaffolder (generated steps become verification commentary;
reference content is kept, not deleted).

### D-Decisions (locked — do not revisit without a new plan)

- **D1 — Stdlib-only, in `tools/`.** `argparse` + `pathlib` + string
  templates embedded in the script. No cookiecutter, no template-engine
  dependency (the zero-dependency mandate covers dev tooling too).
  `tools/` is outside pyright's `include` (`paxman` only), outside
  coverage (`source = ["paxman"]`), and **outside CI's ruff scope** —
  `ci.yml` lints `paxman/ tests/` only. It IS covered by the full pre-PR
  `ruff check .` gate documented in AGENTS.md and by this plan's explicit
  verify commands (`ruff check paxman/ tests/ tools/`) — the worker MUST
  run those; do not rely on CI to lint `tools/`.
- **D2 — CLI surface (exact):**
  ```bash
  uv run python tools/new_capability.py <PackageName> --name <snake> \
      --authority <str> --spec-name <str> --spec-url <str> \
      --publication-year <int> \
      [--spec-version <str>] [--default-format <str>]
  ```
  - `<PackageName>` positional: CapWords identifier (package dir + class
    prefix, e.g. `Timezone`); validated with `str.isidentifier()` + a
    CapWords check (`PackageName[0].isupper()`), else exit 2 with a clear
    message.
  - `--name` REQUIRED lowercase snake registry name (e.g. `timezone`).
    No auto-derivation — the ISBN→isbn / SIUnit→si_unit acronym cases make
    CamelCase→snake conversion a trap; requiring both names removes it.
  - `--authority`, `--spec-name`, `--spec-url`, `--publication-year`
    REQUIRED (fail fast beats placeholder provenance — M11).
  - `--spec-version` optional (default `None`; `Provenance.version` allows
    None). `--default-format` optional (default `"canonical"`; the
    capability's `DEFAULT_OUTPUT_FORMAT` string, TODO-commented to rename
    meaningfully).
- **D3 — Generated file inventory (13 new files + 1 edit), exactly:**
  ```text
  paxman/capabilities/<P>/__init__.py            # exports Capability, Contract, Notation
  paxman/capabilities/<P>/notation.py            # frozen slots dataclass, one str field "value"
  paxman/capabilities/<P>/contract.py            # CapabilityContract subclass
  paxman/capabilities/<P>/capability.py          # Capability[<P>Notation] wiring
  paxman/capabilities/<P>/grammar/__init__.py
  paxman/capabilities/<P>/grammar/<name>_recognition.py
  paxman/capabilities/<P>/rules/__init__.py
  paxman/capabilities/<P>/rules/<authority_snake>_ed<year>.py
  tests/capabilities/<name>/__init__.py
  tests/capabilities/<name>/test_notation.py
  tests/capabilities/<name>/test_grammar.py
  tests/capabilities/<name>/test_rules.py
  tests/capabilities/<name>/test_capability.py
  EDIT  paxman/capabilities/__init__.py          # import + alphabetical __all__ entry
  ```
  Rule filename follows the shipped convention
  (`rfc_5322_ed2008.py`, `iso_4217_ed2015.py`):
  `{authority_snake}_ed{publication_year}.py`. No `rules/data/` or
  `grammar/data/` directories generated — the checklist tells the
  contributor to add them when authority tables arrive.
- **D4 — The tool wires `paxman/capabilities/__init__.py`** (the
  forgettable step, enforced by `tests/unit/test_capability_exports.py`):
  insert `from paxman.capabilities.<P>.capability import <P>Capability as <P>`
  in alphabetical position among the imports and `"<P>"` in alphabetical
  position in `__all__` (existing order is alphabetical: `IP` before
  `ISBN`). Text-insertion on stable markers (after the last
  `from paxman.capabilities.` import line; inside the `__all__` list).
  If `<P>` already appears → exit 2 (idempotency guard).
- **D5 — Template constraints (the generated code must satisfy every
  import-time enforcement, unmodified):**
  - **Grammar** (`<P>Recognition`): `name = "<name>_recognition"`,
    `semantics = "<name>_recognition"` (ADR-0003 Phase-1 identity
    convention; TODO to coalesce if it shares a shipped meaning),
    `single_value = False` (+ TODO: opt in when the grammar resolves one
    mention per call), placeholder pattern that never matches non-empty
    text
    `_PATTERN = re.compile(r"$^")  # TODO: replace with the real pattern`,
    `recognize()` returns `[]` naturally. `Grammar.__init_subclass__`
    requires `semantics` at class-definition time — the template must
    declare it or import of the module fails collection.
  - **Rule** (`SectionTODO` — class `SectionTODO<N>`? NO: class name
    `SectionScaffold`, `name = "Section 1-overview"` with TODO to rename to
    the real `Section {X.Y.Z}-{description}`): all six enforced metadata
    fields present —
    ```python
    name = "Section 1-overview"  # TODO: Section {X.Y.Z}-{description}
    strategy = RuleStrategy.REGEX  # TODO: match strategy to representation
    provenance = PUBLICATION  # from --authority/--spec-* flags
    citation = "Section TODO"  # TODO: real citation
    target_semantics = frozenset({"<name>_recognition"})
    requires_features = frozenset()
    ```
    with module-level `PUBLICATION = Provenance(...)` built from the CLI
    flags (`authority`, `specification_name=spec_name`,
    `kind="specification"`, `reference_url=spec_url`, `version=spec_version`,
    `lifecycle="active"`, `publication_year`). `matches()` returns `False`
    with a TODO body; `normalize()` returns `notation.value` defensively.
  - **Notation**: `@dataclass(frozen=True, slots=True)`, one field
    `value: str` + TODO to shape per domain. **NO `as_list()`** (cleanup
    plan Task 1).
  - **Contract**: `@dataclass(frozen=True)` subclassing
    `CapabilityContract` (no slots — base-class pattern),
    `DEFAULT_OUTPUT_FORMAT: ClassVar[str] = <default-format>`,
    `OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()` (TODO),
    `capability_name: str = field(default="<name>", init=False)`,
    `__post_init__` calls `super().__post_init__()` only.
  - **Capability**: `class <P>Capability(Capability[<P>Notation])`,
    `name = "<name>"`, **NO `version` attribute** (cleanup plan Task 2),
    `get_grammars()`/`get_rules()` return the one placeholder each,
    `create_contract` staticmethod with the exact unanimous common block
    (alphabetical argument order after the fixed prefix, matching SIUnit's
    shipped signature):
    ```python
    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        # TODO: capability-specific keyword-only parameters after this line
    ) -> <P>Contract:
    ```
    `format_value` NOT overridden (identity default; TODO note points at
    the formatting-seam rule).
  - **Test stubs** (all `@pytest.mark.unit`, all passing unmodified):
    notation construction/immutability; grammar `name`/`semantics`/`single_value`
    asserts + `recognize("anything") == []`; rule metadata asserts (six
    fields); capability asserts (ABC subclass, `name`, grammar/rule counts)
    + one pipeline test: register, `create_contract()`,
    `canonicalize("scaffold probe", contract)` → `Resolution.MISSING`
    (never-matching grammar; proves the whole skeleton executes).
  - **Docs in templates**: every TODO is a `# TODO(scaffold):` comment;
    module docstrings state the capability is scaffolded.
- **D6 — Post-generation output.** Print (1) the file list, (2) a numbered
  next-steps checklist mirroring HOW_TO steps the tool could not do:
  replace placeholder pattern/rule/citation, shape the notation, add
  `grammar/data/` / `rules/data/` when tables arrive, register in your
  entry point, docs sweep (README capability table row, CONTEXT.md
  notation/table entries, AGENTS notes), delete-or-extend the placeholder
  grammar/rule. Do NOT auto-edit README/CONTEXT/AGENTS (human judgment).
- **D7 — Guards.** Refuse: existing `paxman/capabilities/<P>/` directory;
  `<P>` already wired in `paxman/capabilities/__init__.py`; invalid
  identifiers (D2); `--name` not lowercase-snake. All exit 2 with the
  offending reason. On refusal, no files written.
- **D8 — Test strategy for the tool (Task 1).** Tests live in
  `tests/unit/test_new_capability_tool.py`, `@pytest.mark.unit`, and run
  the tool in-process (`from tools import new_capability` — add
  `tools/__init__.py` (verified: it does NOT currently exist — create it;
  namespace-package imports would work without it, but a real package is
  the explicit, tooling-safe form); it is outside
  coverage, that's fine). They generate into the REAL tree (import-linter/
  package semantics require the real location) with strict cleanup
  discipline: fixture saves `paxman/capabilities/__init__.py` bytes,
  `finally:` restores them byte-for-byte and `shutil.rmtree`s the generated
  package and test dir, and purges any generated modules from
  `sys.modules`. Generated modules are imported by direct path
  (`importlib.util.spec_from_file_location`) — never by reloading
  `paxman.capabilities`. The `__init__` wiring is asserted on TEXT, not by
  import.

### Out of scope

- Cookiecutter/template-engine packaging; publishing the scaffolder to PyPI.
- Generating multiple grammars/rules, data directories, or docs edits.
- `--dry-run` / `--list-files` flags.
- PEP 562 lazy exports; any change to `paxman.core`.
- Deleting reference content from HOW_TO (restructure only — commentary,
  not amputation).

---

## §2 Tasks

### Task 1 — `feat(tools): add new_capability scaffolder`

**Step 1 — RED.** Write `tests/unit/test_new_capability_tool.py` (D8
discipline) with the fixtures/helpers:

```python
"""Tests for tools/new_capability.py — the capability scaffolder."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_PKG = _REPO / "paxman" / "capabilities" / "Widget"
_TESTS = _REPO / "tests" / "capabilities" / "widget"
_INIT = _REPO / "paxman" / "capabilities" / "__init__.py"


@pytest.fixture
def scaffolded() -> Iterator[None]:
    """Run the scaffolder; restore the tree byte-for-byte afterwards."""
    saved = _INIT.read_text(encoding="utf-8")
    try:
        yield
    finally:
        if _PKG.exists():
            shutil.rmtree(_PKG)
        if _TESTS.exists():
            shutil.rmtree(_TESTS)
        _INIT.write_text(saved, encoding="utf-8")


def _run(*args: str) -> None:
    from tools import new_capability

    new_capability.main(["Widget", *args])  # argparse argv style


_ARGS = (
    "--name",
    "widget",
    "--authority",
    "Acme",
    "--spec-name",
    "Acme Widget Standard",
    "--spec-url",
    "https://example.com/widget",
    "--publication-year",
    "2026",
)
```

Tests (each `@pytest.mark.unit`, each inside the `scaffolded` fixture):

1. `test_rejects_existing_package` — pre-`mkdir` the package dir, expect
   `SystemExit` (code 2), tree otherwise untouched.
2. `test_rejects_invalid_package_name` — `"not capwords"`, `"1Bad"`,
   `""` → `SystemExit` 2, nothing written.
3. `test_rejects_non_snake_registry_name` — `--name Widget` → `SystemExit` 2.
4. `test_generates_full_inventory` — run; assert all 13 files exist (D3).
5. `test_templates_satisfy_enforced_surface` — generated grammar source
   contains `semantics = "widget_recognition"` and `single_value = False`;
   generated rule source contains all six metadata names, the flag-fed
   `authority="Acme"` / `specification_name="Acme Widget Standard"` /
   `publication_year=2026`; generated capability source contains
   `name = "widget"`, the full `create_contract` common block (D5), and
   does NOT contain `as_list` or `version =`.
6. `test_wires_capabilities_init` — `_INIT` text contains the new import
   line and `"Widget",` inside `__all__`, positioned alphabetically
   (between existing neighbors).
7. `test_skeleton_passes_the_full_gate` — the load-bearing test:
   import the generated capability module by path (D8), register it via
   `register_capability(instance)` (registry reset in fixture), run
   `canonicalize("scaffold probe", <P>Capability.create_contract())` and
   assert `status is Resolution.MISSING`; additionally run the generated
   test stubs via
   `subprocess.run([sys.executable, "-m", "pytest", str(_TESTS), "-q"])`
   → returncode 0.

Run: `uv run pytest tests/unit/test_new_capability_tool.py -q` → FAILS
(no `tools/new_capability.py`).

**Step 2 — GREEN.** Implement `tools/new_capability.py` per §1 (D1–D7):
argparse CLI, name validation, per-file template strings (f-string or
`string.Template` — one template constant per generated file, kept in a
`_TEMPLATES` section of the module), the `__init__` wiring inserter, the
guards, and `main(argv: list[str]) -> int` (invoked by
`if __name__ == "__main__": raise SystemExit(main(sys.argv[1:]))`).
Type-annotate fully (pyright does not check `tools/`, but the repo standard
is typed code); run `uv run ruff format tools/new_capability.py` and
`uv run ruff check tools/`.

Re-run the tool tests → PASS.

**Verify.**
```bash
uv run ruff check paxman/ tests/ tools/ && uv run ruff format --check paxman/ tests/ tools/
uv run pytest tests/unit/test_new_capability_tool.py -q
git status --porcelain   # MUST be empty after the suite (cleanup discipline proof)
```

**Commit.** `feat(tools): add new_capability scaffolder`

### Task 2 — Full-gate proof on a scaffolded throwaway (no commit)

Manual QA — the real surface, per the MANUAL QA mandate. This task proves
D5's "generated code passes the full gate unmodified".

1. In a throwaway worktree of this branch (house worktree habit):
   `git worktree add ../paxman-scaffold-proof feature/capability-scaffolder`
2. Run: `uv run python tools/new_capability.py Timezone --name timezone \
   --authority IANA --spec-name "IANA Time Zone Database" \
   --spec-url "https://www.iana.org/time-zones" --publication-year 2026`
3. Run the FULL CI-authoritative gate inside the worktree:
   ```bash
   uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/
   uv run pyright && uv run import-linter lint
   uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
   uv run coverage report --include="paxman/core/*" --fail-under=95
   uv run coverage report --include="paxman/capabilities/*" --fail-under=95
   uv run coverage report --include="paxman/engine/*" --fail-under=95
   uv run coverage report --include="paxman/api/*" --fail-under=95
   ```
   (Four per-package coverage calls matching `ci.yml` — a combined
   `--include` aggregates and can mask a package under 95%.)
4. Capture the gate output (especially: generated `Timezone` package
   coverage — the stubs must cover their own code) and the tool's printed
   checklist as PR evidence.
5. Clean up: remove the worktree (`git worktree remove --force`), leaving
   the branch untouched. **No commit** — the proof is the evidence, not
   artifact code.

If any gate leg fails on generated code, fix the TEMPLATE in
`tools/new_capability.py` on the branch (amend Task 1's commit is NOT
allowed — add a fixup commit `fix(tools): correct scaffold template for
<gated failure>`), and repeat this task until clean.

### Task 3 — `docs: lead HOW_TO with the scaffolder and link it from contributor docs`

Docs-only — **RED-exempt**. Scope-tight restructure; reference content is
kept.

1. `HOW_TO_ADD_NEW_CAPABILITY.md`: insert a new **Step 0 — Generate the
   skeleton (recommended)** right after Prerequisites: the exact command
   from D2, what it generates (D3), and the checklist it prints. Annotate
   the headers of Steps 2–9 with a one-line italic note:
   *"(the scaffolder generates this step's skeleton — verify against your
   domain rather than writing from scratch)"*. Do NOT delete step content;
   Steps 3–9 remain the authoritative reference for what the skeleton
   means. Update Step 10 (tests) to reference the generated stubs as the
   starting point.
2. `CONTRIBUTING.md` §"Before You Write Code" (created by the cleanup
   plan's Task 6 — coordinate; if that plan hasn't landed, add the links
   there anyway, conflict-free): add a line for the scaffolder.
3. `README.md` §"Learn More": add `HOW_TO_ADD_NEW_CAPABILITY.md` already
   linked — append one sentence pointing at the scaffolder quick path.
4. Root `AGENTS.md` §"WHERE TO LOOK" — update the "Add a capability" row:
   `HOW_TO_ADD_NEW_CAPABILITY.md` (62KB spec) **or generate the skeleton:
   `uv run python tools/new_capability.py --help`**.

**Verify.** `uv run python tools/new_capability.py --help` renders; links
resolve; `grep -c "scaffold" HOW_TO_ADD_NEW_CAPABILITY.md` ≥ 5.

**Commit.** `docs: lead HOW_TO with the scaffolder and link it from contributor docs`

### Task 4 — Final gate (no commit)

```bash
uv run ruff check paxman/ tests/ tools/ && uv run ruff format --check paxman/ tests/ tools/ \
  && uv run pyright && uv run import-linter lint \
  && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
git status --porcelain   # clean tree — no scaffold residue
```

---

## §3 Traps

1. **Import-time enforcement bites the templates (D5).** A generated
   grammar missing `semantics`, or a rule missing any of the six metadata
   fields, raises `TypeError` at class-definition time — which kills test
   COLLECTION for the whole suite, not just the new package. This is why
   Task 2 runs the full gate, and why test 7 (stub run via subprocess
   pytest) exists.
2. **Never-matching-on-non-empty pattern choice.** `re.compile(r"$^")`
   never matches NON-EMPTY text in Python's `re` (zero-width
   contradictions at every position) — the scaffold probes ("scaffold
   probe", "anything") are non-empty, so the MISSING proof holds. Caveat:
   it DOES match the empty string (start == end), so `recognize("")`
   would emit one zero-span match; the template comment must say "never
   matches non-empty text", never "never matches". Do not "fix" it to
   `r""` (matches empty string everywhere → span-hell) or a comment-only
   pattern.
3. **Cleanup discipline is part of the contract (D8).** A scaffolder test
   that leaves `Widget/` behind breaks the NEXT test run's collection
   (duplicate `__all__` wiring / import errors) and dirties the tree.
   `git status --porcelain` after the suite is the proof; the fixture's
   byte-for-byte `__init__` restore avoids format churn.
4. **Import generated modules by path, not by reloading** —
   `importlib.reload(paxman.capabilities)` would re-execute the wired
   `__init__` mid-suite and cascade. The `__init__` wiring is asserted as
   text (D8).
5. **Alphabetical `__all__` insertion (D4).** `IP` sorts before `ISBN`
   (verified: `sorted(['ISBN','IP'])` → `['IP','ISBN']`; second chars
   `'P'` < `'S'`). Insert with a real sort over the parsed list, not
   naive string concatenation at a fixed anchor.
6. **`tools/` scope.** pyright's `include` is `paxman` — the tool is NOT
   type-checked by the gate; CI's ruff runs on `paxman/ tests/` only, so
   `tools/` linting lives in the plan's explicit verify commands and the
   full-repo `ruff check .` pre-PR gate. Keep annotations anyway; do not
   add a pyright exclude for tools.
7. **N814/N801 scoped ignores do NOT extend to the new package**
   (`paxman/capabilities/__init__.py` per-file-ignore covers acronym
   aliases in THAT file only — the scaffolder's inserted line lands in it,
   which is exactly why the wiring goes there and is covered). Generated
   `rules/` classes are CapWords (`SectionScaffold`) — no N801 issue.
8. **Dependency ordering.** If the cleanup plan (Tasks 1–2) has NOT landed,
   the templates' no-`as_list`/no-`version` shape will collide with tests
   asserting those surfaces. Rebase; do not "temporarily" add them back.
9. **Idempotency guard before ANY write (D7).** Validate everything
   (names, existing dir, existing wiring) before creating the first file —
   a half-generated package on a guard failure is the worst failure mode.

---

## §4 Definition of Done

- [ ] Two commits on `feature/capability-scaffolder` (+ optional fixups
      from Task 2) with the exact messages.
- [ ] 7 tool tests green; suite leaves `git status --porcelain` clean.
- [ ] Task 2 evidence captured: a scaffolded `Timezone` passes the ENTIRE
      CI-authoritative gate (ruff/format/pyright/import-linter/pytest +
      95% per-package coverage) unmodified, in a removed worktree.
- [ ] HOW_TO leads with Step 0; contributor docs point at the tool.
- [ ] Templates contain no `as_list`, no `Capability.version`, and the
      exact `create_contract` common block.
- [ ] Full gate green on the branch; no scaffold residue in the tree.
