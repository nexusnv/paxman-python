# `register_all_shipped()` Bootstrap Helper — Implementation Plan

| **Title** | Sanctioned one-call bootstrap for all shipped capabilities + documented registration/threading contract |
| **Date** | 2026-08-17 |
| **Status** | Planned — not started |
| **Branch** | `feature/register-all-shipped` (one commit per task) |
| **Origin** | `docs/reports/2026-08-17-architecture-review.md` §9 Near-Term item 2 (§3.6 friction, W8) |
| **Depends on** | Nothing (independent of the other 2026-08-17 near-term plans; may run in parallel) |
| **Supersedes** | Nothing |

> **For agentic workers.** Execute one task at a time. Task 1 is TDD:
> **Step 1 RED** (failing tests first), **Step 2 GREEN** (implementation),
> then the scoped verify and the commit. Task 2 is docs (RED-exempt).
> Task 3 is a verify-only gate with **no commit**. Commit with the exact
> messages given.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | Task 1 — `paxman/api/bootstrap.py` + top-level export (TDD) | ☐ pending | |
> | Task 2 — README/QUICKSTART/ARCHITECTURE: helper + threading contract | ☐ pending | |
> | Task 3 — final gate (no commit) | ☐ pending | |

---

## §1 Cross-Part Contract

### Goal

Give users a sanctioned one-line bootstrap — `paxman.register_all_shipped()` —
that registers all ten shipped capabilities, preserving every existing
registry semantic (explicit registration, freeze-on-first-`canonicalize()`,
duplicate-name rejection, per-capability registration still available), and
document the registration threading contract ("register from a single
thread before the first `canonicalize()` call") that closes W8. This kills
the first-five-minutes registration boilerplate called out by review §3.6
without touching the determinism story.

### D-Decisions (locked — do not revisit without a new plan)

- **D1 — Lives in `paxman/api/bootstrap.py`, NOT core.** The helper must
  import the ten capability classes; import-linter layers
  (`api > engine > capabilities > core`) forbid `paxman.core` from
  importing capabilities. Re-exported from `paxman/__init__.py`
  (`__all__` gains `"register_all_shipped"`).
- **D2 — Explicit class tuple, not dynamic enumeration.** The module holds
  a literal tuple of the ten capability classes in registry-name
  alphabetical order (`country, currency, date, email, ip, isbn, money,
  phone, si_unit, url` — same order as `paxman.capabilities.__all__`).
  Dynamic `getattr` walks over the capabilities module would defeat strict
  pyright. Order is fixed and documented: bootstrap is deterministic.
- **D3 — Semantics: idempotent by name, never freezes, never overrides.**
  For each class: if `get_capability(cls.name)` raises `CapabilityError`
  (unknown → not registered), call `register_capability(cls())`; otherwise
  SKIP (a user's earlier registration — including a subclass — is
  preserved untouched). The helper does NOT freeze the registry (freeze
  remains exclusively on the first `run_capability()` call). Calling it
  after freeze lets `register_capability` raise its natural
  `CapabilityError` — no swallowing. Returns `tuple[str, ...]` of the names
  newly registered, in call order (deterministic, directly assertable,
  loggable). No new discovery API is added — the try/except around
  `get_capability` is the membership probe (`get_capability` raises only
  for unknown names, so the except is precise).
- **D4 — Threading contract is DOCUMENTED, not locked.** Per the review's
  chosen fix ("a one-paragraph contract statement"), the docstring +
  README + ARCHITECTURE state: registration (single or bootstrap) must
  complete from a single thread before the first `canonicalize()` call;
  post-freeze reads are safe everywhere. Adding a lock is explicitly out
  of scope.
- **D5 — PEP 562 lazy registration is out of scope** (review Mid-Term 8 /
  W4). The bootstrap helper registers eagerly; lazy exports remain a
  separate future decision.
- **D6 — Implementation sketch (canonical shape; worker may adjust
  formatting only):**

```python
"""Sanctioned bootstrap: register every shipped capability in one call."""

from __future__ import annotations

from typing import Any

from paxman.capabilities import (
    Country,
    Currency,
    Date,
    Email,
    IP,
    ISBN,
    Money,
    Phone,
    SIUnit,
    URL,
)
from paxman.core.capability import Capability
from paxman.core.discovery import get_capability, register_capability
from paxman.core.errors import CapabilityError

# Fixed, documented order (alphabetical by capability registry name) —
# bootstrap is deterministic. D2: literal tuple, no dynamic enumeration.
_SHIPPED: tuple[type[Capability[Any]], ...] = (
    Country,
    Currency,
    Date,
    Email,
    IP,
    ISBN,
    Money,
    Phone,
    SIUnit,
    URL,
)


def register_all_shipped() -> tuple[str, ...]:
    """Register every shipped capability not already registered.

    Idempotent by name: a capability already registered (including a
    caller-registered subclass) is skipped, never overridden. Does not
    freeze the registry — freezing still happens on the first
    ``canonicalize()`` call. Raises ``CapabilityError`` if the registry is
    already frozen and anything remains to register.

    Threading contract: complete registration — single-calls or this
    helper — from a single thread before the first ``canonicalize()``
    call; post-freeze reads are safe from any thread.

    Returns:
        Names newly registered, in call order.
    """
    registered: list[str] = []
    for cls in _SHIPPED:
        try:
            get_capability(cls.name)
        except CapabilityError:
            register_capability(cls())
            registered.append(cls.name)
    return tuple(registered)
```

- **D7 — `paxman/__init__.py` export.** Add
  `from paxman.api.bootstrap import register_all_shipped` and extend
  `__all__` (keep the list hand-sorted; `register_all_shipped` sorts after
  `register_capability`).

### Out of scope

- Auto-registration / entry-point registration / import-time side effects.
- A registration lock or any thread-safety mechanism beyond documentation.
- PEP 562 lazy capability exports.
- Changes to freeze semantics, `reset_registry`, or the extension seam.
- Registering community grammars/rules on the user's behalf.

---

## §2 Tasks

### Task 1 — `feat(api): add register_all_shipped bootstrap helper`

**Step 1 — RED.** Two new test files (house pattern: local `_clean_registry`
fixtures, no shared mock library):

`tests/unit/test_bootstrap.py` — semantics:

```python
"""Unit tests for the register_all_shipped bootstrap helper."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

import paxman
from paxman.capabilities import Email
from paxman.core.discovery import (
    get_capability,
    is_registry_frozen,
    register_capability,
    reset_registry,
)


@pytest.fixture
def _clean_registry() -> Iterator[None]:
    reset_registry()
    yield
    reset_registry()


@pytest.mark.unit
def test_registers_all_ten_shipped(_clean_registry) -> None:
    names = paxman.register_all_shipped()
    expected = (
        "country",
        "currency",
        "date",
        "email",
        "ip",
        "isbn",
        "money",
        "phone",
        "si_unit",
        "url",
    )
    assert names == expected
    for name in expected:
        assert get_capability(name).name == name


@pytest.mark.unit
def test_idempotent_second_call_registers_nothing(_clean_registry) -> None:
    paxman.register_all_shipped()
    assert paxman.register_all_shipped() == ()


@pytest.mark.unit
def test_preserves_caller_registration(_clean_registry) -> None:
    mine = Email()
    register_capability(mine)
    names = paxman.register_all_shipped()
    assert "email" not in names
    assert len(names) == 9
    assert get_capability("email") is mine


@pytest.mark.unit
def test_does_not_freeze_registry(_clean_registry) -> None:
    paxman.register_all_shipped()
    assert is_registry_frozen() is False


@pytest.mark.unit
def test_raises_after_freeze(_clean_registry) -> None:
    """Natural freeze: one canonicalize() call freezes the registry; a later
    bootstrap with anything left to register must surface the error."""
    register_capability(Email())
    contract = Email.create_contract()
    paxman.canonicalize("user@example.com", contract)  # freezes naturally
    assert is_registry_frozen() is True
    # "url" was never registered, so the helper still has work to do — it
    # must raise (via register_capability's frozen check), never swallow.
    with pytest.raises(paxman.CapabilityError):
        paxman.register_all_shipped()
```

(Shipped as the natural-freeze variant on purpose: no monkeypatching of
module privates — trap #3. The freeze comes from the sanctioned path, a
real `canonicalize()` call.)

`tests/integration/test_bootstrap.py` — the real surface:

```python
import paxman
from paxman.capabilities import Email
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution


@pytest.mark.integration
def test_bootstrap_then_canonicalize_round_trip() -> None:
    """register_all_shipped() is a complete bootstrap: pipeline resolves."""
    reset_registry()
    try:
        paxman.register_all_shipped()
        contract = Email.create_contract()
        result = paxman.canonicalize("user@Example.COM", contract)
        assert result.status is Resolution.SUCCESS
        assert result.canonicalized_value == "user@example.com"
    finally:
        reset_registry()
```

Run: `uv run pytest tests/unit/test_bootstrap.py tests/integration/test_bootstrap.py -q`
→ FAILURES (runtime `AttributeError: paxman has no attribute
'register_all_shipped'` — the `import paxman` lines succeed; the failure is
at call time, which is the correct RED shape).

**Step 2 — GREEN.** Create `paxman/api/bootstrap.py` exactly per D6 (format
with `uv run ruff format paxman/api/bootstrap.py`), wire `paxman/__init__.py`
per D7. Re-run both files → PASS.

**Verify.**
```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/
uv run pyright && uv run import-linter lint
uv run pytest tests/unit/test_bootstrap.py tests/integration/test_bootstrap.py \
  tests/unit/test_discovery.py tests/unit/test_extensions.py -q
```

**Commit.** `feat(api): add register_all_shipped bootstrap helper`
(impl + both test files + `__init__` wiring, one atomic commit.)

### Task 2 — `docs: document register_all_shipped and the registration threading contract`

Docs-only — **RED-exempt**.

1. `README.md` Quick Start: replace the `register_capability(Email())`
   boilerplate with:
   ```python
   import paxman

   paxman.register_all_shipped()  # once, before first use
   ```
   Keep a one-sentence alternative: "To register only what you need, call
   `register_capability(Email())` per capability." Add a short
   **Registration and threading** paragraph: registration — single or
   bootstrap — must complete from a single thread before the first
   `canonicalize()` call; the registry then freezes and reads are safe from
   any thread; registering later raises `CapabilityError`.
2. `QUICKSTART.md`: same one-line switch in "Your First Canonicalization".
3. `ARCHITECTURE.md` §"Capabilities" (registry paragraph, ~line 83): append
   one sentence naming `paxman.register_all_shipped()` as the sanctioned
   bulk form and stating the threading contract (D4 wording).
4. `CONTRIBUTING.md` §"Architecture at a Glance": unchanged (layer story
   unaffected).

**Verify.** `grep -n "register_all_shipped" README.md QUICKSTART.md ARCHITECTURE.md`
→ all three hit; README snippet mentally executable against Task 1's
integration test.

**Commit.** `docs: document register_all_shipped and the registration threading contract`

### Task 3 — Final gate (no commit)

```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ \
  && uv run pyright && uv run import-linter lint \
  && uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
```

(Four per-package coverage calls matching `ci.yml` exactly — a combined
`--include` computes aggregate coverage and can mask a package under 95%.)

Manual QA: fresh `uv run python -c` one-liner exercising the documented
README path end to end (bootstrap → email canonicalize → print value),
proof captured in the PR description.

---

## §3 Traps

1. **Layer direction (D1).** Putting the helper in `paxman.core` breaks
   import-linter (core → capabilities is forbidden) — CI fails on
   `import-linter lint`. It MUST live in `paxman/api/`.
2. **Do not freeze in the helper (D3).** `register_all_shipped()` calling
   `freeze_registry()` would break the documented "freeze on first
   canonicalize" semantic and the extension-registration window
   (`register_grammar` after bootstrap but before first canonicalize must
   keep working).
3. **Frozen-registry test must use the natural freeze path** — call
   `canonicalize()` once to freeze, then assert the helper raises. Don't
   monkeypatch `_frozen`; tests must not reach into module privates.
4. **Strict pyright on the class tuple (D2/D6).** `tuple[type[Capability[Any]], ...]`
   needs `Any` (classes are `type[CountryCapability]` etc.); the shipped
   aliases (`Country`, …) are the classes themselves (`as` aliases), so the
   literal tuple typechecks as written. Verify with `uv run pyright`.
5. **Fixture hygiene.** Every test uses a local try/finally or
   yield-fixture `reset_registry()` — the 19-file house `_clean_registry`
   pattern; never add a shared conftest registry fixture (AGENTS rule).
6. **Determinism wording.** Docs must say the bootstrap order is fixed and
   alphabetical — reviewers will ask whether bulk registration is
   deterministic (it is, by construction).
7. **PR description should note**: this is additive public API; the
   per-capability path is unchanged and remains the minimal-footprint
   recommendation for libraries embedding paxman.

---

## §4 Definition of Done

- [ ] Two commits on `feature/register-all-shipped` with the exact messages.
- [ ] `paxman.register_all_shipped` exported; idempotency, preservation,
      no-freeze, frozen-raise, and round-trip behaviors locked by 6 tests.
- [ ] Full CI-authoritative gate green; per-package coverage ≥95%
      (new `bootstrap.py` fully covered by the new tests).
- [ ] README/QUICKSTART/ARCHITECTURE show the helper and the threading
      contract; README path proven by a real `python -c` run.
- [ ] No changes to `discovery.py`, `extensions.py`, freeze semantics, or
      any capability package.
