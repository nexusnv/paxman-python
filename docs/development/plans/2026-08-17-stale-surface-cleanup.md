# Stale-Surface Cleanup — Implementation Plan

| **Title** | Remove drifted/dead surfaces: `Notation` alias, `as_list()`, `Capability.version`, `ContractFactory` docstring, `pyproject` metadata, CI trigger, CONTRIBUTING drift |
| **Date** | 2026-08-17 |
| **Status** | Planned — not started |
| **Branch** | `refactor/stale-surface-cleanup` (one commit per task) |
| **Origin** | `docs/reports/2026-08-17-architecture-review.md` §9 Near-Term item 3 (weaknesses W1-docstring, W2, W6) |
| **Depends on** | Nothing. **Execute FIRST** of the 2026-08-17 near-term plans — the capability-scaffolder plan's templates assume Tasks 1–2 have landed (no `as_list`, no `version`). |
| **Supersedes** | Nothing |

> **For agentic workers.** This plan is written to be executed by a worker agent
> one task at a time. Every behavior-removal task is TDD: **Step 1 RED** (write
> the failing guard test first), **Step 2 GREEN** (do the removal sweep), then
> the scoped verify command and the commit. Do not skip steps, do not reorder
> tasks. **Mechanical/docs-only tasks are exempt from a meaningful RED step** —
> Tasks 3, 5, and 6 say so explicitly and their instruction wins. Commit with
> the exact message given for each task. Task 7 is a verify-only gate with
> **no commit**.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | Task 1 — remove `Notation = list[str]` alias + `as_list()` bridging | ☐ pending | |
> | Task 2 — remove dead `Capability.version` metadata | ☐ pending | |
> | Task 3 — fix `ContractFactory` "five capability classes" docstring | ☐ pending | |
> | Task 4 — `pyproject`: license/urls/readme + dev-deps dedup | ☐ pending | |
> | Task 5 — CI trigger for feature/refactor branches | ☐ pending | |
> | Task 6 — CONTRIBUTING.md: repo name, uv workflow, HOW_TO links | ☐ pending | |
> | Task 7 — final gate (no commit) | ☐ pending | |

---

## §1 Cross-Part Contract

### Goal

Close every stale/drifted surface named by review §9 item 3, exactly six
sub-items, no more:

1. `Notation = list[str]` alias + `as_list()` bridging — removed from core,
   all notations, tests, and docs (review W2).
2. `Capability.version` — removed (dead metadata; `VersionStamp.paxman_version`
   owns versioning) (review W6 bullet 4: "consume-or-remove" → **remove**).
3. `ContractFactory` docstring "the five capability classes satisfy it" —
   there are ten; fix wording without hardcoding a count that drifts again.
4. `pyproject.toml` — declare `license`, `license-files`, `urls`, `readme`;
   collapse the duplicated dev-dependency blocks (optional-dependencies vs
   dependency-groups) into one; regenerate `uv.lock`.
5. `.github/workflows/ci.yml` — run CI on pushes to `feature/**` and
   `refactor/**` branches (this repo's actual development pattern), not just
   `main`.
6. `CONTRIBUTING.md` — fix stale repo name (`paxman-alternative`), align setup
   with CI's `uv sync --all-extras`, remove the duplicated install block, and
   link the two HOW_TO guides.

Public-API removals (`Notation` export, `as_list()`, `Capability.version`)
are **0.x-budgeted breaking changes** under the M12/ADR-0002 precedent
(break at 0.x, document in the plan). Nothing outside the six sub-items
changes.

### D-Decisions (locked — do not revisit without a new plan)

- **D1 — Guard tests, not just deletions.** Each removal is locked by a
  source-scan/attribute test in a new `tests/unit/test_removed_surfaces.py`,
  mirroring the repo's `test_rule_output_format_purity.py` culture
  (architecture-as-law). The guard test is the RED step; the sweep is GREEN.
- **D2 — Tests for removed APIs are deleted WITH the API, replaced by the
  guard.** Deleting `test_as_list_*` / `test_version` assertions is removal
  of tests for behavior that no longer exists — this is NOT the "delete
  failing tests to pass" anti-pattern; the guard test preserves the intent
  (the surface stays gone). State this in the PR description.
- **D3 — `RecognizedRep.__hash__` list-defense stays.** Community grammars
  may still legitimately parameterize `Grammar[list[str]]`; the hash guard
  for unhashable notation types is defensive core code, not part of the
  deprecated alias. Do not touch it.
- **D4 — `Capability.version` is REMOVED, not consumed.** Wiring a per-
  capability semver into `VersionStamp` would create a versioning discipline
  nobody maintains; `VersionStamp.paxman_version` already answers the
  consumer's question. Removing the ABC annotation is non-breaking for
  community subclasses (an extra class attribute on a subclass is legal
  Python and pyright-clean).
- **D5 — License declaration uses PEP 639 SPDX form**: `license = "MIT"` +
  `license-files = ["LICENSE.md"]`, no `License ::` classifier (mutually
  exclusive under PEP 639). **Fallback if the build backend rejects PEP 639
  metadata** (hatchling is a build-time dependency and is NOT pinned in
  `uv.lock` — verified: zero `hatchling` matches — so there is no locked
  version to inspect): `license = { file = "LICENSE.md" }` + classifier
  `"License :: OSI Approved :: MIT License"`. Choose by running `uv build`
  after the edit; the form that builds clean wins (do not upgrade build
  deps to force PEP 639). Record which form landed in the PR description.
- **D6 — Dev deps consolidate into `[dependency-groups] dev`** (PEP 735,
  uv-native, matches the "uv only" mandate). CI stays on `uv sync
  --all-extras` unchanged: uv special-cases the `dev` group and syncs it by
  default, so the dev tools remain installed (verified against uv docs —
  do NOT add `--all-groups`; it is unnecessary).
  `[project.optional-dependencies].dev` is deleted.
  Floors take the maximum of the two current blocks: `pytest>=8.0`,
  `pytest-cov>=5.0`, `hypothesis>=6.100`, `ruff>=0.5`, `pyright>=1.1`,
  `import-linter>=2.13`. `uv.lock` is regenerated and committed in the same
  commit.
- **D7 — CI trigger adds `"feature/**"` and `"refactor/**"` to the existing
  `push.branches` list only.** The `pull_request` trigger (base `main`) is
  untouched. Concurrency key `ci-${{ github.ref }}` already isolates branch
  runs. No `workflow_dispatch`.
- **D8 — Sweep greps run per task, then once more in Task 7.** Known
  greppable residuals and their owners: `as_list` (T1), `Notation = list`
  (T1), `five capability` (T3), `paxman-alternative` (T6),
  `[project.optional-dependencies]` in CONTRIBUTING (T6, after T4). When
  grepping for `Capability.version` removal residuals, use
  `capability.version|Capability\.version|\.version == "1\.0\.0"` — a bare
  `\.version` grep false-positives on `Provenance.version` (legitimate,
  stays).

### Out of scope

- `Contract` Protocol vs `CapabilityContract` ABC unification (review
  Mid-Term 5 — separate ADR).
- `Rule[NotationT, ContractT]` cast elimination (Mid-Term 9).
- PEP 562 lazy capability exports (Mid-Term 8).
- Registration thread-lock (documented contract only, in the bootstrap plan).
- CHANGELOG / examples/ / docs site (review W6 mentions; not in Near-Term 3).
- Any behavior change to the pipeline.

---

## §2 Tasks

### Task 1 — `refactor: remove Notation list alias and as_list bridging`

**Scope of the sweep (verified this session):**

- `paxman/core/domain.py` — delete `Notation = list[str]` alias + its
  two-line comment (around line 36–39).
- `paxman/core/__init__.py` — remove `Notation` from the
  `from paxman.core.domain import (...)` block and from `__all__`.
- Notation modules defining `as_list()` — the ten
  `paxman/capabilities/<Name>/notation.py` files (Country, Currency, Date,
  Email, IP, ISBN, Money, Phone, SIUnit, URL). Re-enumerate at execution
  time with `grep -rl "def as_list" paxman/` and sweep every hit.
- `paxman/capabilities/URL/notation.py` — its docstring references
  `as_list()` (line ~14); rewrite that sentence to describe the single
  `text` component without the bridge mention.
- Test files referencing `as_list` (11 files, ~45 refs):
  `tests/capabilities/{currency,si_unit,url,money,isbn}/test_notation.py`,
  `tests/capabilities/{phone,ip,country,email,date}/test_capability.py`,
  `tests/capabilities/date/test_grammar.py`. Re-enumerate with
  `grep -rln "as_list" tests/` and touch every hit. `test_notation.py`
  files whose only subject is `as_list` shrink to the remaining
  construction/immutability tests; delete only the `as_list` test
  functions, never whole files.
- `tests/unit/test_capability.py` — line 9 imports `Notation` from
  `paxman.core.domain`; the doubles subclass `Grammar`/`Rule` bare (no
  subscription), and `Notation` appears only in annotations (lines ~20,
  ~42, ~45) — retype those usages to `list[str]` and remove the import.
- Docs: `ARCHITECTURE.md` §"Notation Bridging" (line ~122) — rewrite the
  section to describe the typed-dataclass notation model (the bridge no
  longer exists; the section's honest replacement: each capability defines a
  frozen dataclass notation; `Grammar[NotationT]`/`Rule[NotationT]` carry
  it end to end). `CONTEXT.md` lines ~47 and ~60 — remove the bridging note
  and the `as_list` snippet. `HOW_TO_ADD_NEW_CAPABILITY.md` line ~749 —
  remove the `test_as_list_returns_correct` stub item and any other
  `as_list` teaching references (grep the file).

**Step 1 — RED.** Create `tests/unit/test_removed_surfaces.py`:

```python
"""Guards for removed legacy surfaces (architecture-review Near-Term 3).

Each test locks a removal: the surface must not reappear in source.
"""

from __future__ import annotations

from pathlib import Path

import paxman.core.domain
import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_generic_notation_alias_removed() -> None:
    """`Notation = list[str]` alias is gone from core and its export."""
    assert not hasattr(paxman.core.domain, "Notation")
    assert not hasattr(paxman.core, "Notation")


@pytest.mark.unit
def test_no_as_list_bridging_in_source() -> None:
    """No paxman source module defines as_list() bridging."""
    offenders = [
        p.as_posix()
        for p in (_REPO_ROOT / "paxman").rglob("*.py")
        if "def as_list" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"as_list bridging found in: {offenders}"
```

Run: `uv run pytest tests/unit/test_removed_surfaces.py -q` → both FAIL.

**Step 2 — GREEN.** Perform the sweep exactly as scoped above. Re-run the
guard → PASS.

**Verify.**
```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/
uv run pyright
uv run pytest tests/unit/ tests/capabilities/ -q
```

**Commit.** `refactor: remove Notation list alias and as_list bridging`

### Task 2 — `refactor: remove dead Capability.version metadata`

**Scope:**

- `paxman/core/capability.py` — delete the `version: str` class annotation
  from the `Capability` ABC (keep `name: str`).
- The ten `paxman/capabilities/<Name>/capability.py` modules — delete the
  `version = "1.0.0"` class attribute. Enumerate with
  `grep -rn 'version = "1' paxman/capabilities/*/capability.py`.
- Capability tests asserting `.version == "1.0.0"` — at least
  currency:26, phone:147, si_unit:24, url:36, date:62, ip:81, country:192,
  money:25 (re-enumerate with
  `grep -rn '\.version ==' tests/capabilities/`); delete those assertions
  or the test functions whose only subject is `version`.
- `tests/unit/test_capability.py` — the test double sets `version = "0.1.0"`
  and asserts it (line ~117); remove both sides.
- `HOW_TO_ADD_NEW_CAPABILITY.md` — line ~366 (Step 5 list item "Set
  `version` to a semantic version string"), line ~758 (`test_version` test
  stub), line ~1091 (checklist "…grammar count, and rule count" — drop the
  version mention). Grep `version` in the file and remove only
  Capability-version items; `Provenance.version` references are legitimate
  and stay.

**Step 1 — RED.** Extend `tests/unit/test_removed_surfaces.py`:

```python
@pytest.mark.unit
def test_capability_abc_has_no_version_surface() -> None:
    """`Capability.version` annotation is removed from the ABC."""
    from paxman.core.capability import Capability

    assert "version" not in Capability.__annotations__


@pytest.mark.unit
def test_shipped_capabilities_do_not_declare_version() -> None:
    """No shipped capability class carries a dead version attribute."""
    from paxman.capabilities import (
        IP,
        ISBN,
        URL,
        Country,
        Currency,
        Date,
        Email,
        Money,
        Phone,
        SIUnit,
    )

    for cls in (Country, Currency, Date, Email, IP, ISBN, Money, Phone, SIUnit, URL):
        assert "version" not in vars(cls), cls.__name__
```

Run: `uv run pytest tests/unit/test_removed_surfaces.py -q` → the two new
tests FAIL.

**Step 2 — GREEN.** Perform the sweep. Re-run the guard → PASS.

**Verify.**
```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/
uv run pyright && uv run import-linter lint
uv run pytest tests/unit/ tests/capabilities/ -q
```

**Commit.** `refactor: remove dead Capability.version metadata`

### Task 3 — `docs(core): fix ContractFactory capability-count drift`

Mechanical docs-only — **RED-exempt**.

`paxman/core/capability.py`, `ContractFactory` docstring (lines ~77–81):
replace "the five capability classes satisfy it by declaring" with
future-proof wording: "every shipped capability class satisfies it by
declaring" (no hardcoded count — the count is what drifted). No other
changes to the protocol.

**Verify.** `uv run ruff check paxman/ && uv run pyright`

**Commit.** `docs(core): fix ContractFactory capability-count drift`

### Task 4 — `build: declare license, urls and readme; dedupe dev dependencies`

**Step 1 — RED.** Extend `tests/unit/test_package_install.py` (it already
parses installed metadata) with a pyproject-declaration test:

```python
@pytest.mark.unit
def test_project_metadata_declared() -> None:
    """pyproject declares license, urls, and readme (community-trust floor)."""
    import tomllib

    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project.get("license"), "license must be declared"
    assert project.get("urls", {}).get("Homepage"), (
        "project.urls.Homepage must be declared"
    )
    assert project.get("readme") == "README.md"
    assert "dev" not in project.get("optional-dependencies", {}), (
        "dev deps live in [dependency-groups] only"
    )
```

Run: `uv run pytest tests/unit/test_package_install.py -q` → new test FAILS.

**Step 2 — GREEN.** Edit `pyproject.toml`:

- Add to `[project]`: `readme = "README.md"`, and per D5: PEP 639
  `license = "MIT"` + `license-files = ["LICENSE.md"]` (fallback form per
  D5 if `uv build` rejects).
- Add:
  ```toml
  [project.urls]
  Homepage = "https://github.com/nexusnv/paxman-python"
  Repository = "https://github.com/nexusnv/paxman-python"
  Issues = "https://github.com/nexusnv/paxman-python/issues"
  ```
- Delete `[project.optional-dependencies]` entirely; set
  `[dependency-groups] dev` to the consolidated floors (D6): pytest>=8.0,
  pytest-cov>=5.0, hypothesis>=6.100, ruff>=0.5, pyright>=1.1,
  import-linter>=2.13.
- Regenerate the lock: `uv sync --all-extras` → commit updated `uv.lock`.

**Verify.**
```bash
uv sync --all-extras
uv run pytest tests/unit/test_package_install.py -q
uv build && unzip -p dist/paxman-*.whl "*/METADATA" | grep -iE "license|project-url|home-page"
uv run import-linter lint
```

**Commit.** `build: declare license, urls and readme; dedupe dev dependencies`

### Task 5 — `ci: run CI on feature and refactor branches`

Mechanical config — **RED-exempt** (no local runner; verified by inspection
and by this branch's own CI run once pushed).

`.github/workflows/ci.yml`: change

```yaml
  push:
    branches: [main]
```

to

```yaml
  push:
    branches: [main, "feature/**", "refactor/**"]
```

Leave `pull_request` untouched. **Verify.** `git diff .github/workflows/ci.yml`
shows exactly that hunk; YAML structure unchanged otherwise. The real-surface
proof is the CI run on this plan's own branch after push.

**Commit.** `ci: run CI on feature and refactor branches`

### Task 6 — `docs: align CONTRIBUTING with the uv workflow and link contributor guides`

Docs-only — **RED-exempt**. `CONTRIBUTING.md`:

1. Line ~19: `cd paxman-alternative` → `cd paxman-python`.
2. Lines ~22–30 (duplicated `uv venv` / `uv pip install` / `--group dev`
   blocks) → replace with the CI-identical single command:
   ```bash
   uv sync --all-extras
   ```
   and a one-line note that all commands run via `uv run` (matches root
   AGENTS.md "uv only").
3. Line ~33 ("All dev dependencies are listed … under
   `[project.optional-dependencies] dev`") → "under `[dependency-groups] dev`"
   (valid only after Task 4; this is why Task 6 follows Task 4).
4. New short section **"Before You Write Code"** linking
   `HOW_TO_ADD_NEW_CAPABILITY.md`, `HOW_TO_ADD_NEW_GRAMMAR.md`, and
   `TESTING_STRATEGY.md`, with one sentence each.
5. PR-process quality-suite command (line ~123) stays as-is (it already
   matches the CI-authoritative gate).

**Verify.** `grep -n "paxman-alternative\|uv pip install\|optional-dependencies" CONTRIBUTING.md`
→ no hits; links resolve (`test -f` each linked file).

**Commit.** `docs: align CONTRIBUTING with the uv workflow and link contributor guides`

### Task 7 — Final gate (no commit)

**Residual sweep (D8):**
```bash
grep -rn "as_list\|Notation = list\|five capability\|paxman-alternative" \
  paxman/ tests/ ARCHITECTURE.md CONTEXT.md CONTRIBUTING.md \
  HOW_TO_ADD_NEW_CAPABILITY.md HOW_TO_ADD_NEW_GRAMMAR.md README.md QUICKSTART.md
grep -rn 'version = "1' paxman/capabilities/*/capability.py
```
→ only historical/archival hits under `docs/` are acceptable (ADR-0003
precedent: historical plans stay as-is); zero hits in shipped source,
tests, and living docs.

**Full CI-authoritative gate:**
```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ \
  && uv run pyright && uv run import-linter lint \
  && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
```

(The four separate per-package coverage calls match `ci.yml`'s
"Enforce per-package coverage" step exactly. A single combined
`--include="paxman/core/*,paxman/capabilities/*,..."` computes AGGREGATE
coverage and would mask one package dropping under 95 — do not collapse
them.)

Note: the full-repo `ruff format --check .` variant still flags 8
pre-existing historical docs (ADR-0003 plan precedent) — out of scope here.

---

## §3 Traps

1. **Sweep tasks are atomic per task.** Task 1 and Task 2 each delete an API
   across source+tests+docs in ONE commit. A split-brain state (alias gone,
   tests importing it) fails collection for the whole suite, not just one
   file — same class of trap as the ADR-0003 D2 atomic rename.
2. **`test_capability.py` double retyping (Task 1).** The doubles subclass
   `Grammar`/`Rule` bare (no type parameter); only the `Notation`
   annotations (lines ~20, ~42, ~45) change to `list[str]`. `Grammar[list[str]]`
   remains legal for community grammars (D3) — retype, don't redesign the
   double.
3. **False-positive greps (Task 2).** `Provenance.version` (rule metadata)
   and `paxman_version`/`version_stamp` are legitimate. Use the D8 patterns;
   never sweep `Provenance.version` away.
4. **PEP 639 backend support (Task 4).** If `uv build` fails on
   `license = "MIT"`, the build backend predates PEP 639 — switch to the
   D5 fallback form; do not upgrade build deps to force it. (There is no
   `hatchling` entry in `uv.lock` to check — build deps are not pinned
   there; the `uv build` probe is the decision mechanism.)
5. **`uv.lock` must land in Task 4's commit.** Deleting the optional-extra
   changes the lock; a stale lock breaks CI's `uv sync --all-extras`.
6. **Coverage floor.** Removing `as_list` bodies deletes covered lines —
   harmless. But the new guard test must import cleanly on every Python
   version in the matrix (3.11–3.13); `tomllib` is stdlib ≥3.11, safe.
7. **Docs in ruff scope.** CI lints `paxman/ tests/` only — the
   CONTRIBUTING/ARCHITECTURE/CONTEXT edits are verified by grep + link
   checks, not ruff. Do not "fix" formatting of historical docs.
8. **`vars(cls)` guard (Task 2).** Use `vars(cls)`, not `hasattr` — the ABC
   annotation alone never creates a class attribute, so `hasattr` would pass
   vacuously before the sweep.

---

## §4 Definition of Done

- [ ] All seven tasks executed in order; six commits on
      `refactor/stale-surface-cleanup` with the exact messages above.
- [ ] `tests/unit/test_removed_surfaces.py` green and merged into the suite;
      full pytest run green (1,62x+ tests, count ≥ prior total minus deleted
      as_list/version tests, plus 5 guards).
- [ ] Full CI-authoritative gate green locally, including per-package 95%
      coverage.
- [ ] `uv build` produces a wheel whose METADATA shows license, urls, and
      readme; `uv.lock` committed and consistent.
- [ ] Zero residual hits for the D8 patterns in shipped source/tests/living
      docs.
- [ ] CI ran on this feature branch itself (proving Task 5).
- [ ] Scaffolder plan unblocked: templates may assume no `as_list`, no
      `Capability.version`, `[dependency-groups]`-only dev deps.
