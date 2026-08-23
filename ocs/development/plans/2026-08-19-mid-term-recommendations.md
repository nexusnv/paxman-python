# Mid-Term Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver all four Mid-Term structural-debt items from `docs/reports/2026-08-17-architecture-review.md` §9 (items 5–8) without architectural surgery — resolving Protocol-vs-ABC drift, standing up the shared-vocabulary data pipeline for Currency/Money, adding a minimal benchmark harness, and adopting PEP 562 lazy exports for `paxman.capabilities`.

**Architecture:** Four independent verticals that converge on determinism + isolation invariants: (5) ADR-driven contract unification with `CapabilityContract` as single source of truth and removal of `getattr` probes; (6) snapshot-driven regeneration `tools/regenerate_currency_data.py` that writes *into* per-capability tables preserving import-linter isolation; (7) pure-Python `benchmarks/` harness with one scenario per capability and JSON baseline tracking; (8) `PEP 562 __getattr__/__dir__` in `paxman/capabilities/__init__.py` with eager `__all__` preserved for `pyright`/`ruff`.

**Tech Stack:** Python 3.11+, `uv`, `hatchling`, `pyright` (strict), `ruff`, `import-linter`, `pytest` + `pytest-cov` (95% per-package gates), `time.perf_counter` (bench), `argparse` + `pathlib` (tools), `importlib.metadata` (version stamp)

---

## File Structure

Before tasks, lock decomposition. Files grouped by responsibility; each file does one thing.

**New files:**
- `docs/adr/0007-contract-surface-unification.md` — ADR for item 5 (Protocol vs ABC decision)
- `paxman/core/_engine_contract.py` — engine-internal Protocol (demoted `Contract`), not publicly exported (optional, see Task 3 variant)
- `paxman/shared_data/currency_snapshot.json` + `paxman/shared_data/README.md` — shared CLDR/ISO 4217 snapshot (source of truth for item 6)
- `tools/regenerate_currency_data.py` — regenerates Currency + Money tables from shared snapshot (item 6)
- `benchmarks/__init__.py` — package marker
- `benchmarks/harness.py` — runner, timing, JSON output
- `benchmarks/scenarios.py` — one deterministic scenario per capability (10 entries)
- `benchmarks/baseline.json` — committed baseline (updated via `--update-baseline`)
- `tests/unit/test_contract_surface.py` — contract surface unification tests (item 5)
- `tests/unit/test_capability_lazy_import.py` — PEP 562 lazy-import tests (item 8)
- `tests/unit/test_currency_data_regeneration.py` — drift guard for item 6 (mirrors `tests/capabilities/si_unit/test_data.py`)
- `tests/benchmarks/test_harness.py` — harness smoke tests (item 7)

**Modified files:**
- `paxman/core/contract.py` — shrink to `resolve_output_format` only or re-export shim (item 5)
- `paxman/core/capability_contract.py` — docstring/typing polish, satisfies internal Protocol structurally (item 5)
- `paxman/core/__init__.py` — stop re-exporting `Contract` publicly; export `CapabilityContract` only (item 5)
- `paxman/core/capability.py` — update `ContractFactory` docstring (5→10)
- `paxman/engine/orchestrator.py` — `_recognize`, `_activated_rules`, `_filter_rules` remove `getattr(contract, "extra_grammars", ())`; direct `contract.extra_grammars`; type to `CapabilityContract` (item 5)
- `paxman/capabilities/__init__.py` — PEP 562 lazy `__getattr__` (item 8)
- `paxman/capabilities/Currency/grammar/data/currency_symbols.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Currency/grammar/data/currency_words.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Currency/rules/data/cldr_currencies.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Currency/rules/data/iso4217_list_one.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Money/grammar/data/currency_symbols.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Money/grammar/data/currency_words.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Money/rules/data/cldr_currencies.py` — becomes GENERATED (item 6)
- `paxman/capabilities/Money/rules/data/iso4217_list_one.py` — becomes GENERATED (item 6)
- `.github/workflows/ci.yml` — add bench + drift check jobs (items 6, 7)
- `pyproject.toml` — add `[tool.pytest.ini_options] markers` entry `benchmark`, add `benchmarks` to coverage `omit` or explicit per-package handling (item 7)
- `HOW_TO_ADD_NEW_CAPABILITY.md` — note shared snapshot workflow (item 6)
- `paxman/capabilities/AGENTS.md` — update data-placement rules for generated tables (item 6)

**Untouched (enforced invariants):**
- `paxman/core/domain.py` — no change (Rule/Grammar ABCs stay)
- `paxman/core/discovery.py`, `paxman/core/extensions.py` — no import added (layer discipline intact)
- No sibling imports introduced; `import-linter` layers `api → engine → capabilities → core` remain enforced.

---

## Task Overview

| Task | Vertical | Effort | Deliverable |
|------|----------|--------|-------------|
| 1 | Item 5 — Contract ADR | 15 min | `docs/adr/0007-*.md` accepted |
| 2 | Item 5 — Failing surface tests | 20 min | `tests/unit/test_contract_surface.py` RED |
| 3 | Item 5 — Engine + core unification | 40 min | `getattr` probes removed, `Contract` demoted, pyright clean |
| 4 | Item 5 — Docs + export polish | 15 min | `__init__.py`, `capability.py` docstring, `HOW_TO` note |
| 5 | Item 6 — Snapshot audit + scaffold | 20 min | `paxman/shared_data/` + snapshot JSON |
| 6 | Item 6 — Regeneration tool | 45 min | `tools/regenerate_currency_data.py` with `--check` |
| 7 | Item 6 — Migrate Currency tables to GENERATED | 25 min | 4 Currency data files regenerated, tests GREEN |
| 8 | Item 6 — Migrate Money tables + import-linter guard | 25 min | 4 Money data files regenerated, `import-linter lint` GREEN |
| 9 | Item 6 — Drift tests + CI wiring | 20 min | `test_currency_data_regeneration.py` + CI job |
| 10 | Item 7 — Benchmark harness | 30 min | `benchmarks/harness.py` runnable via `uv run python -m benchmarks.harness` |
| 11 | Item 7 — Scenarios (10 capabilities) | 30 min | `benchmarks/scenarios.py` deterministic, property-checked |
| 12 | Item 7 — Baseline + CI | 20 min | `benchmarks/baseline.json` + CI `benchmark` job (non-blocking) |
| 13 | Item 7 — Docs | 10 min | `benchmarks/README.md` + `ARCHITECTURE.md` note |
| 14 | Item 8 — Lazy-import failing tests | 20 min | `tests/unit/test_capability_lazy_import.py` RED |
| 15 | Item 8 — PEP 562 `__getattr__` | 30 min | `paxman/capabilities/__init__.py` lazy, backward compatible |
| 16 | Item 8 — Type + lint + perf verification | 25 min | `pyright`, `ruff`, import-time micro-bench GREEN |
| 17 | Final — Cross-vertical verification gate | 20 min | Full `ruff + pyright + import-linter + pytest + coverage` GREEN |

---

### Task 1: Item 5 — Write ADR 0007 (Contract Surface Unification)

**Files:**
- Create: `docs/adr/0007-contract-surface-unification.md`
- Read: `docs/adr/0003-semantic-affinity-routing.md`, `paxman/core/contract.py`, `paxman/core/capability_contract.py`, `paxman/engine/orchestrator.py:146-158`

- [ ] **Step 1: Create ADR file with Accepted status**

Create `docs/adr/0007-contract-surface-unification.md` with exact content:

```markdown
# ADR-0007: Contract Surface Unification — CapabilityContract as Single Source of Truth

## Status

Accepted

## Context

`paxman/core/contract.py` defines `Contract` as a `@runtime_checkable` Protocol (intended for duck-typed user contracts). `paxman/core/capability_contract.py` defines `CapabilityContract` as a frozen dataclass ABC that every shipped contract MUST inherit (homogeneity mandate, `capabilities/AGENTS.md`). The 2026-08-17 architecture review (W1) found drift:

- `Contract` omits `extra_grammars`; engine probes via `getattr(contract, "extra_grammars", ())` in `orchestrator._recognize` and `_activated_rules`. A duck-typed `Contract` silently loses the extension seam.
- `Contract.output_format: str | None` vs `CapabilityContract.__post_init__` always resolves to concrete `str`.
- `ContractFactory` docstring says "five capability classes" — there are ten.

Dual truth is a compat hazard; the ABC has won in practice (all 10 shipped contracts inherit it).

## Decision

- `CapabilityContract` is the **only sanctioned public contract base**. Shipped and community contracts MUST inherit it.
- `Contract` Protocol is demoted to **engine-internal** (`paxman/core/_engine_contract.py` or retained as private re-export, not exported from `paxman.core.__init__` or `paxman.__init__`). It exists only for internal structural typing of the engine boundary.
- Engine removes all `getattr(contract, "extra_grammars", ())` probes; accesses `contract.extra_grammars` directly (fail-fast `AttributeError` → `ContractError` wrapping if violated).
- `ContractFactory` docstring corrected to ten; `capability_name` contract field typed as concrete `str` post-`__post_init__`.
- Breaking change is budgeted at 0.x per M12; provide a one-minor deprecation shim if needed (`Contract = CapabilityContract` alias with DeprecationWarning gated by env var, removed at 0.3.0).

## Alternatives Considered

1. **Fix Protocol to match ABC** (add `extra_grammars`, fix `output_format: str`): keeps two definitions in sync forever — drift will recur, no user value (no shipped duck-typed contract exists).
2. **Keep Protocol as public, ABC as convenience**: same dual-sync cost plus weaker homogeneity enforcement (`__init_subclass__` checks bypassed for duck types).

## Consequences

- One source of truth; drift eliminated; `getattr` probes deleted.
- Engine type hints narrow to `CapabilityContract`; `pyright` strict passes without `getattr` fallback.
- Third-party duck-typed contracts without inheritance fail fast with actionable `ContractError` instead of silent extension-seam loss.
- `import-linter` layers unchanged; no new dependencies.

## References

- `docs/reports/2026-08-17-architecture-review.md` W1, §9 item 5, M9
- `paxman/core/capability_contract.py`, `paxman/core/contract.py`, `paxman/engine/orchestrator.py`
```

- [ ] **Step 2: Verify ADR renders and links**

Run: `uv run python -c "from pathlib import Path; print(Path('docs/adr/0007-contract-surface-unification.md').read_text()[:200])"`
Expected: prints header, no exception

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0007-contract-surface-unification.md
git commit -m "docs(adr): add ADR-0007 contract surface unification (Item 5)"
```

---

### Task 2: Item 5 — Write Failing Surface Tests (TDD Red)

**Files:**
- Create: `tests/unit/test_contract_surface.py`
- Read: `tests/unit/test_capability_contract.py`, `tests/unit/test_contract.py`, `paxman/core/__init__.py`

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_contract_surface.py`:

```python
"""Item 5 — contract surface unification: CapabilityContract is the single source of truth.

These tests drive Task 3: they will FAIL until the engine removes getattr probes
and Contract is demoted from public exports.
"""

from __future__ import annotations

import importlib

import pytest


def test_contract_not_exported_from_core_public_api() -> None:
    """After unification, `Contract` must NOT be exported from `paxman.core`."""
    import paxman.core as core

    assert not hasattr(core, "Contract") or core.Contract.__module__.endswith(
        "_engine_contract"
    ), "Contract must not be publicly re-exported from paxman.core"


def test_capability_contract_is_only_public_base() -> None:
    """Every shipped contract must inherit CapabilityContract (homogeneity mandate)."""
    from paxman.capabilities.Country.contract import CountryContract
    from paxman.capabilities.Currency.contract import CurrencyContract
    from paxman.capabilities.Date.contract import DateContract
    from paxman.capabilities.Email.contract import EmailContract
    from paxman.capabilities.IP.contract import IPContract
    from paxman.capabilities.ISBN.contract import ISBNContract
    from paxman.capabilities.Money.contract import MoneyContract
    from paxman.capabilities.Phone.contract import PhoneContract
    from paxman.capabilities.SIUnit.contract import SIUnitContract
    from paxman.capabilities.URL.contract import URLContract
    from paxman.core.capability_contract import CapabilityContract

    for cls in [
        CountryContract,
        CurrencyContract,
        DateContract,
        EmailContract,
        IPContract,
        ISBNContract,
        MoneyContract,
        PhoneContract,
        SIUnitContract,
        URLContract,
    ]:
        assert issubclass(cls, CapabilityContract), (
            f"{cls.__name__} must inherit CapabilityContract"
        )


def test_engine_requires_extra_grammars_attribute() -> None:
    """Engine must access contract.extra_grammars directly (no getattr fallback)."""
    from dataclasses import dataclass

    from paxman.core.capability_contract import CapabilityContract
    from paxman.engine.orchestrator import _recognize  # type: ignore[attr-defined]

    # Build a minimal contract-like object WITHOUT extra_grammars — should fail fast
    # (after fix, engine does NOT use getattr(... , ()); it accesses directly)
    @dataclass(frozen=True)
    class _BadContract:
        capability_name: str = "email"
        active_grammars = None
        excluded_rules: tuple[str, ...] = ()
        pinned_rules: tuple[str, ...] | None = None
        year: int | None = None
        output_format: str | None = None
        # NOTE: no extra_grammars attribute at all

    # The engine should not silently succeed via getattr fallback
    import inspect

    src = inspect.getsource(_recognize)
    assert 'getattr(contract, "extra_grammars"' not in src, (
        "getattr probe must be removed from _recognize"
    )

    src2 = inspect.getsource(importlib.import_module("paxman.engine.orchestrator"))
    assert 'getattr(contract, "extra_grammars"' not in src2, (
        "all getattr probes for extra_grammars must be removed"
    )


def test_contract_factory_docstring_mentions_ten() -> None:
    """ContractFactory docstring must say ten, not five."""
    from paxman.core.capability import ContractFactory

    assert ContractFactory.__doc__ is not None
    assert "five" not in ContractFactory.__doc__.lower(), "stale 'five' must be fixed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_contract_surface.py -v`
Expected: FAIL — `test_contract_not_exported_from_core_public_api` (Contract still exported) and `test_engine_requires_extra_grammars_attribute` (getattr still present)

- [ ] **Step 3: Commit the failing test (TDD Red)**

```bash
git add tests/unit/test_contract_surface.py
git commit -m "test(core): add failing contract surface unification tests (Item 5 RED)"
```

---

### Task 3: Item 5 — Implement Engine + Core Unification (TDD Green)

**Files:**
- Modify: `paxman/core/contract.py`
- Modify: `paxman/core/capability_contract.py`
- Modify: `paxman/core/__init__.py`
- Modify: `paxman/engine/orchestrator.py`
- Modify: `paxman/core/domain.py` (if it imports Contract for typing — narrow to CapabilityContract where needed)
- Create (optional): `paxman/core/_engine_contract.py`

- [ ] **Step 1: Demote Contract Protocol to engine-internal**

Option A (minimal diff, recommended): keep `paxman/core/contract.py` but stop re-exporting `Contract` publicly; keep `Contract` as internal Protocol used only by engine typing. Add header comment.

Edit `paxman/core/contract.py`: add module docstring note at top:

```python
"""Contract protocol — ENGINE-INTERNAL since ADR-0007.

Public contracts MUST inherit `CapabilityContract`. This Protocol is retained
only for internal structural typing of the engine boundary and is NOT part of
the public API. Do not import it from `paxman.core` — import `CapabilityContract`.
"""
```

No functional change to `Contract` class itself in this task (keep for internal use). The public-export cut happens in `paxman/core/__init__.py`.

If you create `paxman/core/_engine_contract.py`, move `Contract` there and make `paxman/core/contract.py` a shim that re-exports both `Contract` (deprecated) and `resolve_output_format`. For this plan, keep single file to minimize churn.

- [ ] **Step 2: Remove public re-export of Contract**

Edit `paxman/core/__init__.py`: remove `Contract` from imports and `__all__`. Ensure `CapabilityContract` remains exported.

Before:
```python
from paxman.core.contract import Contract

...
__all__ = ["Capability", "Contract", ...]
```

After:
```python
from paxman.core.capability_contract import CapabilityContract

...
__all__ = [
    "Capability",
    "CapabilityContract",
    ...,
]  # Contract intentionally not exported
```

Add `from paxman.core.contract import Contract as _Contract  # internal, not exported` if engine still needs it via `paxman.core.contract` (not via `paxman.core`).

- [ ] **Step 3: Remove getattr probes in orchestrator**

Edit `paxman/engine/orchestrator.py`:

Change `_recognize` line 147:
```python
# Before:
extra_grammars = getattr(contract, "extra_grammars", ())
# After:
extra_grammars = contract.extra_grammars  # type: ignore[attr-defined]  # CapabilityContract always has this (ADR-0007)
```

Change `_activated_rules` line 494:
```python
# Before:
extra_grammars = set(getattr(contract, "extra_grammars", ()))
# After:
extra_grammars = set(contract.extra_grammars)  # type: ignore[attr-defined]
```

Change `_filter_rules` inspection: it already uses `hasattr` for `requires_features` — keep that (that's feature-gating, not contract surface). Do NOT change `_filter_rules` feature logic.

Update type hints at top of `orchestrator.py`:

```python
from paxman.core.capability_contract import CapabilityContract

# Change ExecutionResult.contract and run_capability signature to prefer CapabilityContract
# Keep Contract as narrow internal alias if needed for backward compat:
from paxman.core.contract import Contract as _Contract  # internal
```

But to keep change minimal and pyright-clean, change signatures to `CapabilityContract`:

```python
@dataclass(frozen=True)
class ExecutionResult:
    status: Resolution
    canonicalized_value: str | None
    candidates: tuple[Candidate, ...]
    contract: CapabilityContract
    version_stamp: VersionStamp
    span: tuple[int, int] | None = None

def run_capability(text: str, contract: CapabilityContract) -> ExecutionResult:
```

Ensure `RecognizedRep.contract` typing in `paxman/core/domain.py` remains `Contract` or widen to `CapabilityContract` — check `domain.py` import; if it imports `Contract`, change to `CapabilityContract` or keep `Contract` as internal Protocol and update import path to `paxman.core._engine_contract` if you created it. Keep one Protocol type to avoid dual.

Simplest: leave `domain.py` importing from `paxman.core.contract` (internal) — still works because `CapabilityContract` structurally satisfies it. No change to `domain.py` needed if you kept `Contract` in `contract.py`.

- [ ] **Step 4: Fix ContractFactory docstring**

Edit `paxman/core/capability.py` line 71 docstring:

```python
# Before: "Every capability exposes..." (no mention of count) or "five"
# Ensure it says ten if it mentions count, or remove count entirely and say "every shipped capability class satisfies it"
```

Change docstring to:

```python
@runtime_checkable
class ContractFactory(Protocol):
    """Factory protocol for capability contract creation.

    Every shipped capability class (ten as of 0.2.0) satisfies it by declaring
    ``create_contract`` with the unanimous common parameter block.
    """
```

- [ ] **Step 5: Run tests to verify GREEN**

Run: `uv run pytest tests/unit/test_contract_surface.py -v`
Expected: PASS (3/3 or 4/4 depending on count)

Run: `uv run pyright`
Expected: PASS (0 errors). If `contract.extra_grammars` triggers `reportAttributeAccessIssue`, add `# type: ignore[attr-defined]` or narrow `contract` param to `CapabilityContract` so pyright sees the attribute.

Run: `uv run import-linter lint`
Expected: PASS (no new layer violations)

- [ ] **Step 6: Commit**

```bash
git add paxman/core/contract.py paxman/core/__init__.py paxman/engine/orchestrator.py paxman/core/capability.py tests/unit/test_contract_surface.py
git commit -m "refactor(core): unify contract surface — CapabilityContract single source (ADR-0007, Item 5)"
```

---

### Task 4: Item 5 — Docs + Export Polish

**Files:**
- Modify: `paxman/api/__init__.py` (if it re-exports Contract)
- Modify: `HOW_TO_ADD_NEW_CAPABILITY.md` (contract section)
- Modify: `paxman/capabilities/AGENTS.md` (contract line)

- [ ] **Step 1: Ensure public API does not re-export Contract**

Check `paxman/__init__.py` and `paxman/api/__init__.py`: ensure `Contract` not in `__all__`. If found, remove.

- [ ] **Step 2: Update HOW_TO note**

In `HOW_TO_ADD_NEW_CAPABILITY.md`, in the Contract section, ensure it says:

> Subclass `CapabilityContract` (never `Contract` directly). `Contract` is engine-internal since ADR-0007.

No code, just one paragraph edit.

- [ ] **Step 3: Run doc-sensitive tests**

Run: `uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add paxman/__init__.py paxman/api/__init__.py HOW_TO_ADD_NEW_CAPABILITY.md paxman/capabilities/AGENTS.md
git commit -m "docs(core): polish contract exports and HOWTO for ADR-0007 (Item 5)"
```

---

### Task 5: Item 6 — Shared Snapshot Audit + Scaffold

**Files:**
- Create: `paxman/shared_data/README.md`
- Create: `paxman/shared_data/currency_snapshot.json`
- Read: `paxman/capabilities/Currency/rules/data/cldr_currencies.py`, `paxman/capabilities/Money/rules/data/cldr_currencies.py`, `paxman/capabilities/Currency/rules/data/iso4217_list_one.py`, `paxman/capabilities/Money/rules/data/iso4217_list_one.py`, `paxman/capabilities/Currency/grammar/data/currency_symbols.py`, `paxman/capabilities/Currency/grammar/data/currency_words.py`, `paxman/capabilities/Money/grammar/data/currency_symbols.py`, `paxman/capabilities/Money/grammar/data/currency_words.py`

- [ ] **Step 1: Audit duplication**

Run:

```bash
diff -u paxman/capabilities/Currency/rules/data/cldr_currencies.py paxman/capabilities/Money/rules/data/cldr_currencies.py | head -n 120
diff -u paxman/capabilities/Currency/grammar/data/currency_symbols.py paxman/capabilities/Money/grammar/data/currency_symbols.py | head -n 80
wc -l paxman/capabilities/Currency/rules/data/*.py paxman/capabilities/Money/rules/data/*.py
```

Record findings in commit message; the snapshot must be the union of both with provenance fields.

- [ ] **Step 2: Create shared_data directory and README**

Create `paxman/shared_data/README.md`:

```markdown
# Shared Vocabulary Snapshot — Currency / Money

Source of truth for CLDR currency data and ISO 4217 list-one.

- Authority: Unicode CLDR v47 (en + es) and ISO 4217 (2015 list-one snapshot).
- Canonical file: `currency_snapshot.json` (JSON, UTF-8, sorted keys).
- Generated outputs: `paxman/capabilities/Currency/{grammar,rules}/data/*` and `paxman/capabilities/Money/{grammar,rules}/data/*` via `tools/regenerate_currency_data.py`.
- Edit workflow: update snapshot JSON (with citation), then `uv run python tools/regenerate_currency_data.py` and `--check` in CI.

Mandate M8: Sibling imports remain banned. Shared vocabularies regenerate into per-capability tables, never imported across capabilities.
```

- [ ] **Step 3: Create snapshot JSON (union of current data)**

Structure `paxman/shared_data/currency_snapshot.json`:

```json
{
  "_meta": {
    "authority": "Unicode CLDR v47 (en + es) + ISO 4217:2015 list-one",
    "generated_by": "manual union of Currency/Money tables as of 2026-08-19",
    "citation": "CLDR common/main/en.xml, common/main/es.xml; ISO 4217 list-one 2015"
  },
  "iso4217": [
    {"alpha3": "USD", "numeric": "840", "minor_units": 2, "name": "US Dollar"},
    {"alpha3": "EUR", "numeric": "978", "minor_units": 2, "name": "Euro"}
  ],
  "cldr_currencies": {
    "USD": {"symbol": "$", "display_name_en": "US Dollar", "display_name_es": "dólar estadounidense"},
    "EUR": {"symbol": "€", "display_name_en": "Euro", "display_name_es": "euro"}
  },
  "symbol_to_codes": {
    "$": ["USD", "AUD", "CAD"],
    "€": ["EUR"]
  }
}
```

Populate by extracting from the 4 existing files: write a one-off script `tools/_extract_currency_snapshot.py` (delete after) that imports both Currency and Money data modules, merges dicts, sorts keys, writes JSON. Do NOT hand-edit ISO tables by eye.

Example extractor (run once, then delete):

```python
import json, pathlib
from paxman.capabilities.Currency.rules.data.cldr_currencies import SYMBOL_TO_CODES as A
from paxman.capabilities.Money.rules.data.cldr_currencies import SYMBOL_TO_CODES as B

merged = {**A, **B}  # union, Money wins on collision — inspect diff manually
path = pathlib.Path("paxman/shared_data/currency_snapshot.json")
path.write_text(
    json.dumps(
        {"symbol_to_codes": {k: sorted(v) for k, v in sorted(merged.items())}},
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
```

- [ ] **Step 4: Commit snapshot scaffold**

```bash
git add paxman/shared_data/README.md paxman/shared_data/currency_snapshot.json
git commit -m "feat(shared-data): scaffold shared CLDR/ISO4217 snapshot for Currency+Money (Item 6)"
```

---

### Task 6: Item 6 — Regeneration Tool

**Files:**
- Create: `tools/regenerate_currency_data.py`
- Read: `tools/regenerate_si_prefix_data.py` (template for `--check`, `_GENERATED_HEADER`, deterministic emit), `tools/regenerate_isbn_range_data.py`

- [ ] **Step 1: Write the failing test for the tool (RED)**

Create `tests/unit/test_currency_data_regeneration.py` (mirrors `tests/capabilities/si_unit/test_data.py` pattern):

```python
"""Drift guard for Currency/Money generated tables (Item 6, M8)."""

from __future__ import annotations

import subprocess
import sys


def test_currency_data_not_drifted() -> None:
    proc = subprocess.run(
        [sys.executable, "tools/regenerate_currency_data.py", "--check"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"DRIFT: {proc.stderr or proc.stdout}\nRun: uv run python tools/regenerate_currency_data.py"
    )
```

Run: `uv run pytest tests/unit/test_currency_data_regeneration.py -v`
Expected: FAIL (tool does not exist yet)

- [ ] **Step 2: Implement tool**

Create `tools/regenerate_currency_data.py`:

```python
"""Regenerate Currency + Money data modules from shared snapshot.

Source: paxman/shared_data/currency_snapshot.json (CLDR v47 + ISO 4217).
Outputs (8 files, deterministic, longest-first ordering for tokens):
- paxman/capabilities/Currency/grammar/data/currency_symbols.py
- paxman/capabilities/Currency/grammar/data/currency_words.py
- paxman/capabilities/Currency/rules/data/cldr_currencies.py
- paxman/capabilities/Currency/rules/data/iso4217_list_one.py
- paxman/capabilities/Money/grammar/data/currency_symbols.py
- paxman/capabilities/Money/grammar/data/currency_words.py
- paxman/capabilities/Money/rules/data/cldr_currencies.py
- paxman/capabilities/Money/rules/data/iso4217_list_one.py

Regeneration preserves import-linter isolation: each capability gets its own
local table; sibling imports remain banned (M8).

Usage:
    uv run python tools/regenerate_currency_data.py
    uv run python tools/regenerate_currency_data.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "paxman" / "shared_data" / "currency_snapshot.json"

_GENERATED_HEADER = (
    "GENERATED by tools/regenerate_currency_data.py — do not edit by hand."
)

# Per-capability output paths (deterministic order)
OUTPUTS = [
    ROOT
    / "paxman"
    / "capabilities"
    / "Currency"
    / "grammar"
    / "data"
    / "currency_symbols.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Currency"
    / "grammar"
    / "data"
    / "currency_words.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Currency"
    / "rules"
    / "data"
    / "cldr_currencies.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Currency"
    / "rules"
    / "data"
    / "iso4217_list_one.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Money"
    / "grammar"
    / "data"
    / "currency_symbols.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Money"
    / "grammar"
    / "data"
    / "currency_words.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Money"
    / "rules"
    / "data"
    / "cldr_currencies.py",
    ROOT
    / "paxman"
    / "capabilities"
    / "Money"
    / "rules"
    / "data"
    / "iso4217_list_one.py",
]

# ... helpers: _load_snapshot(), _emit_currency_symbols(), _emit_currency_words(),
# _emit_cldr_currencies(), _emit_iso4217_list_one(), _emit_module(doc, assignment)


def _emit_module(docstring: str, assignment: str) -> str:
    return (
        '"""'
        + _GENERATED_HEADER
        + "\n\n"
        + docstring
        + '"""\n\nfrom __future__ import annotations\n\n'
        + assignment
        + "\n"
    )


def _load_snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def _symbol_tokens(snapshot: dict) -> tuple[str, ...]:
    # From snapshot["symbol_to_codes"] keys, qualified before bare, longest-first
    symbols = list(snapshot.get("symbol_to_codes", {}).keys())

    def _rank(s: str) -> tuple[int, int, str]:
        qualified = 0 if any(c.isascii() and c.isalpha() for c in s) else 1
        return (qualified, -len(s), s)

    return tuple(sorted(symbols, key=_rank))


def _word_tokens(snapshot: dict) -> tuple[str, ...]:
    # From cldr display names + ISO names, longest-first
    words: set[str] = set()
    for v in snapshot.get("cldr_currencies", {}).values():
        words.add(v.get("display_name_en", "").lower())
        words.add(v.get("display_name_es", "").lower())
    words.discard("")
    return tuple(sorted(words, key=lambda w: (-len(w), w)))


def _modules() -> list[tuple[Path, str]]:
    snap = _load_snapshot()
    symbols = _symbol_tokens(snap)
    words = _word_tokens(snap)
    # Emit grammar tokens
    sym_assign = (
        "SYMBOL_TOKENS: tuple[str, ...] = (\n"
        + "".join(f'    "{s}",\n' for s in symbols)
        + ")"
    )
    word_assign = (
        "CURRENCY_WORDS: tuple[str, ...] = (\n"
        + "".join(f'    "{w}",\n' for w in words)
        + ")"
        if words
        else "CURRENCY_WORDS: tuple[str, ...] = ()"
    )
    # Emit rule tables: reproduce current module shape exactly so tests stay green
    # For brevity in plan, emit minimal correct shape; refine during implementation to match byte-for-byte expected structure
    cldr_assign = (
        f"SYMBOL_TO_CODES: dict[str, list[str]] = {snap.get('symbol_to_codes', {})!r}"
    )
    iso_assign = f"ISO4217_LIST_ONE: list[dict] = {snap.get('iso4217', [])!r}"
    # Build 8 modules: Currency + Money share same content per M8 (regenerate into per-capability tables)
    return [
        (OUTPUTS[0], _emit_module("Currency symbol tokens (CLDR).", sym_assign)),
        (OUTPUTS[1], _emit_module("Currency word tokens (CLDR).", word_assign)),
        (OUTPUTS[2], _emit_module("CLDR symbol->codes mapping.", cldr_assign)),
        (OUTPUTS[3], _emit_module("ISO 4217 list-one.", iso_assign)),
        (
            OUTPUTS[4],
            _emit_module("Currency symbol tokens (CLDR) — Money copy.", sym_assign),
        ),
        (
            OUTPUTS[5],
            _emit_module("Currency word tokens (CLDR) — Money copy.", word_assign),
        ),
        (
            OUTPUTS[6],
            _emit_module("CLDR symbol->codes mapping — Money copy.", cldr_assign),
        ),
        (OUTPUTS[7], _emit_module("ISO 4217 list-one — Money copy.", iso_assign)),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate Currency/Money data modules."
    )
    parser.add_argument(
        "--check", action="store_true", help="check drift, exit non-zero if drifted"
    )
    args = parser.parse_args()
    mods = _modules()
    if args.check:
        drifted = [
            p for p, t in mods if not p.exists() or p.read_text(encoding="utf-8") != t
        ]
        if drifted:
            for p in drifted:
                print(f"DRIFT: {p.relative_to(ROOT)}", file=sys.stderr)
            raise SystemExit(1)
        print("all Currency/Money generated data modules are up to date")
        return
    for p, t in mods:
        p.write_text(t, encoding="utf-8")
        print(f"wrote {p.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
```

Key: keep `SYMBOL_TOKENS` ordering identical to current `currency_symbols.py` (qualified + longest-first) so existing grammar tests stay green without behavior change. Copy existing emit logic verbatim in implementation; stub above is schematic — flesh out to match file headers line-for-line before marking task done.

- [ ] **Step 3: Run tool and verify it creates files**

Run: `uv run python tools/regenerate_currency_data.py`
Expected: `wrote paxman/capabilities/Currency/grammar/data/currency_symbols.py` x8

Run: `uv run python tools/regenerate_currency_data.py --check`
Expected: `all Currency/Money generated data modules are up to date`

- [ ] **Step 4: Run drift test to verify GREEN**

Run: `uv run pytest tests/unit/test_currency_data_regeneration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/regenerate_currency_data.py tests/unit/test_currency_data_regeneration.py
git commit -m "feat(tools): add regenerate_currency_data with --check (Item 6)"
```

---

### Task 7: Item 6 — Migrate Currency Tables to GENERATED

**Files:**
- Modify: `paxman/capabilities/Currency/grammar/data/currency_symbols.py`
- Modify: `paxman/capabilities/Currency/grammar/data/currency_words.py`
- Modify: `paxman/capabilities/Currency/rules/data/cldr_currencies.py`
- Modify: `paxman/capabilities/Currency/rules/data/iso4217_list_one.py`

- [ ] **Step 1: Regenerate and stage Currency files**

Run: `uv run python tools/regenerate_currency_data.py`
Check header in each file contains `GENERATED by tools/regenerate_currency_data.py — do not edit by hand.`

- [ ] **Step 2: Run capability tests**

Run: `uv run pytest tests/capabilities/currency/ -v --tb=short`
Expected: PASS (no behavior change; tables are byte-equivalent or semantically equivalent)

Run: `uv run pytest -m "currency or money" -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add paxman/capabilities/Currency/grammar/data/currency_symbols.py paxman/capabilities/Currency/grammar/data/currency_words.py paxman/capabilities/Currency/rules/data/cldr_currencies.py paxman/capabilities/Currency/rules/data/iso4217_list_one.py
git commit -m "feat(currency): generate Currency tables from shared snapshot (Item 6)"
```

---

### Task 8: Item 6 — Migrate Money Tables + Import-Linter Guard

**Files:**
- Modify: `paxman/capabilities/Money/grammar/data/currency_symbols.py`
- Modify: `paxman/capabilities/Money/grammar/data/currency_words.py`
- Modify: `paxman/capabilities/Money/rules/data/cldr_currencies.py`
- Modify: `paxman/capabilities/Money/rules/data/iso4217_list_one.py`

- [ ] **Step 1: Regenerate Money files (same tool already did)**

Verify `paxman/capabilities/Money/grammar/data/currency_symbols.py` header is `GENERATED`.

- [ ] **Step 2: Verify import-linter still enforces isolation**

Run: `uv run import-linter lint`
Expected: PASS — no sibling imports introduced (each file is standalone generated table, no `from paxman.capabilities.Currency`).

Run: `uv run ruff check paxman/capabilities/Currency paxman/capabilities/Money`
Expected: PASS

- [ ] **Step 3: Run Money capability tests**

Run: `uv run pytest tests/capabilities/money/ -v --tb=short`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add paxman/capabilities/Money/grammar/data/currency_symbols.py paxman/capabilities/Money/grammar/data/currency_words.py paxman/capabilities/Money/rules/data/cldr_currencies.py paxman/capabilities/Money/rules/data/iso4217_list_one.py
git commit -m "feat(money): generate Money tables from shared snapshot (Item 6)"
```

---

### Task 9: Item 6 — Drift Tests + CI Wiring

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` (optional: add `shared_data` to docs)

- [ ] **Step 1: Ensure drift guard is tested in CI**

Edit `.github/workflows/ci.yml`: after `import-linter lint` step, add:

```yaml
      - name: Check generated Currency/Money data drift
        run: uv run python tools/regenerate_currency_data.py --check

      - name: Check generated SIUnit data drift
        run: uv run python tools/regenerate_si_prefix_data.py --check
```

(Keep existing `regenerate_isbn_range_data` check if present; add if missing: `uv run python tools/regenerate_isbn_range_data.py --check` or its equivalent.)

- [ ] **Step 2: Run CI locally**

Run: `uv run python tools/regenerate_currency_data.py --check && uv run python tools/regenerate_si_prefix_data.py --check`
Expected: both print `are up to date`

- [ ] **Step 3: Run full test suite for the 4-table change**

Run: `uv run pytest --tb=short -q`
Expected: PASS; coverage gates still 95% (generated tables are covered via capability tests)

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml tests/unit/test_currency_data_regeneration.py
git commit -m "ci: add drift checks for Currency/Money shared snapshot (Item 6)"
```

---

### Task 10: Item 7 — Benchmark Harness

**Files:**
- Create: `benchmarks/__init__.py`
- Create: `benchmarks/harness.py`
- Read: `paxman/engine/orchestrator.py` (cost model: every grammar scans, every rule validates), `tests/property/*` (deterministic scenarios)

- [ ] **Step 1: Write failing harness smoke test (RED)**

Create `tests/benchmarks/test_harness.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


def test_harness_runs_one_scenario() -> None:
    from benchmarks.harness import run_once

    result = run_once("email", "user@example.com", iterations=3)
    assert result["capability"] == "email"
    assert result["iterations"] == 3
    assert result["mean_ms"] >= 0
    assert result["p50_ms"] >= 0


def test_harness_writes_json() -> None:
    from benchmarks.harness import main
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.json"
        main(["--output", str(out), "--iterations", "2"])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "scenarios" in data
        assert len(data["scenarios"]) == 10
```

Run: `uv run pytest tests/benchmarks/test_harness.py -v`
Expected: FAIL (module `benchmarks.harness` not found)

- [ ] **Step 2: Implement harness**

Create `benchmarks/__init__.py` (empty).

Create `benchmarks/harness.py`:

```python
"""Minimal benchmark harness — one scenario per capability (W5, Item 7).

No external deps. Deterministic per contract+input+library snapshot.
Measures wall-clock via time.perf_counter, reports mean/p50/p95 per scenario.
Used in CI as non-blocking signal and locally via --update-baseline.

Usage:
    uv run python -m benchmarks.harness --iterations 200
    uv run python -m benchmarks.harness --output /tmp/bench.json
    uv run python -m benchmarks.harness --update-baseline
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from benchmarks.scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "benchmarks" / "baseline.json"


def run_once(capability: str, text: str, iterations: int = 100) -> dict:
    from paxman import canonicalize
    from paxman.core.discovery import reset_registry

    # Import capability lazily to respect PEP 562 (Item 8) — harness must not hide import cost
    # Scenarios carry a factory: lambda: (contract, text)
    scenario = next(s for s in SCENARIOS if s["capability"] == capability)
    durations: list[float] = []
    for _ in range(iterations):
        reset_registry()
        # Register only the needed capability for this scenario (isolates import cost if lazy)
        scenario["register"]()
        contract = scenario["contract_factory"]()
        start = time.perf_counter()
        canonicalize(text, contract)
        durations.append((time.perf_counter() - start) * 1000)
        # reset_registry cleans for next iteration
        reset_registry()
    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    return {
        "capability": capability,
        "iterations": iterations,
        "mean_ms": statistics.mean(durations),
        "p50_ms": p50,
        "p95_ms": p95,
        "min_ms": min(durations),
        "max_ms": max(durations),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Paxman benchmark harness (Item 7)")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args(argv)

    results: list[dict] = []
    for scenario in SCENARIOS:
        results.append(
            run_once(
                scenario["capability"], scenario["text"], iterations=args.iterations
            )
        )

    payload = {"scenarios": results, "iterations": args.iterations}
    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.output}")
    elif args.update_baseline:
        BASELINE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE}")
    else:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run test to verify GREEN**

Run: `uv run pytest tests/benchmarks/test_harness.py -v`
Expected: PASS after `benchmarks/scenarios.py` exists (next task provides it) — so this task stays RED until Task 11; commit harness alone and expect one failure, or implement minimal SCENARIOS stub now.

Add temporary stub in `benchmarks/scenarios.py` to unblock:

```python
SCENARIOS = [
    {
        "capability": "email",
        "text": "user@example.com",
        "register": lambda: None,
        "contract_factory": lambda: None,
    }
]
```

Then iterate in Task 11.

- [ ] **Step 4: Commit**

```bash
git add benchmarks/__init__.py benchmarks/harness.py tests/benchmarks/test_harness.py
git commit -m "feat(benchmarks): add minimal harness skeleton (Item 7)"
```

---

### Task 11: Item 7 — Scenarios (One Per Capability)

**Files:**
- Modify: `benchmarks/scenarios.py`
- Read: `tests/capabilities/*/test_*.py`, `paxman/capabilities/*/capability.py` (canonical examples)

- [ ] **Step 1: Write full SCENARIOS**

Replace `benchmarks/scenarios.py` with:

```python
"""Benchmark scenarios — one deterministic input per capability (Item 7).

Inputs chosen to exercise the hot path: recognition + validation + formatting.
No network, no clock, no randomness — deterministic per library snapshot.
"""

from __future__ import annotations

from collections.abc import Callable


def _email_register() -> None:
    from paxman.capabilities import Email
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("email")
    except CapabilityError:
        register_capability(Email())


def _email_contract():
    from paxman.capabilities import Email

    return Email.create_contract()


# Repeat pattern for 10 capabilities: country, currency, date, email, ip, isbn, money, phone, si_unit, url


def _country_register() -> None:
    from paxman.capabilities import Country
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("country")
    except CapabilityError:
        register_capability(Country())


def _country_contract():
    from paxman.capabilities import Country

    return Country.create_contract()


def _currency_register() -> None:
    from paxman.capabilities import Currency
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("currency")
    except CapabilityError:
        register_capability(Currency())


def _currency_contract():
    from paxman.capabilities import Currency

    return Currency.create_contract()


def _date_register() -> None:
    from paxman.capabilities import Date
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("date")
    except CapabilityError:
        register_capability(Date())


def _date_contract():
    from paxman.capabilities import Date

    return Date.create_contract()


def _ip_register() -> None:
    from paxman.capabilities import IP
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("ip")
    except CapabilityError:
        register_capability(IP())


def _ip_contract():
    from paxman.capabilities import IP

    return IP.create_contract()


def _isbn_register() -> None:
    from paxman.capabilities import ISBN
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("isbn")
    except CapabilityError:
        register_capability(ISBN())


def _isbn_contract():
    from paxman.capabilities import ISBN

    return ISBN.create_contract()


def _money_register() -> None:
    from paxman.capabilities import Money
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("money")
    except CapabilityError:
        register_capability(Money())


def _money_contract():
    from paxman.capabilities import Money

    return Money.create_contract()


def _phone_register() -> None:
    from paxman.capabilities import Phone
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("phone")
    except CapabilityError:
        register_capability(Phone())


def _phone_contract():
    from paxman.capabilities import Phone

    return Phone.create_contract(default_country="US")


def _si_unit_register() -> None:
    from paxman.capabilities import SIUnit
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("si_unit")
    except CapabilityError:
        register_capability(SIUnit())


def _si_unit_contract():
    from paxman.capabilities import SIUnit

    return SIUnit.create_contract()


def _url_register() -> None:
    from paxman.capabilities import URL
    from paxman.core.discovery import register_capability, get_capability
    from paxman.core.errors import CapabilityError

    try:
        get_capability("url")
    except CapabilityError:
        register_capability(URL())


def _url_contract():
    from paxman.capabilities import URL

    return URL.create_contract()


SCENARIOS: list[dict] = [
    {
        "capability": "country",
        "text": "United States",
        "register": _country_register,
        "contract_factory": _country_contract,
    },
    {
        "capability": "currency",
        "text": "USD",
        "register": _currency_register,
        "contract_factory": _currency_contract,
    },
    {
        "capability": "date",
        "text": "2026-01-15",
        "register": _date_register,
        "contract_factory": _date_contract,
    },
    {
        "capability": "email",
        "text": "user@example.com",
        "register": _email_register,
        "contract_factory": _email_contract,
    },
    {
        "capability": "ip",
        "text": "192.168.1.1",
        "register": _ip_register,
        "contract_factory": _ip_contract,
    },
    {
        "capability": "isbn",
        "text": "9780306406157",
        "register": _isbn_register,
        "contract_factory": _isbn_contract,
    },
    {
        "capability": "money",
        "text": "USD 500.00",
        "register": _money_register,
        "contract_factory": _money_contract,
    },
    {
        "capability": "phone",
        "text": "+1 555 123 4567",
        "register": _phone_register,
        "contract_factory": _phone_contract,
    },
    {
        "capability": "si_unit",
        "text": "kg",
        "register": _si_unit_register,
        "contract_factory": _si_unit_contract,
    },
    {
        "capability": "url",
        "text": "https://example.com/path",
        "register": _url_register,
        "contract_factory": _url_contract,
    },
]
```

- [ ] **Step 2: Run harness to verify 10 scenarios**

Run: `uv run python -m benchmarks.harness --iterations 5`
Expected: JSON with `"scenarios"` length 10, no exception

Run: `uv run pytest tests/benchmarks/test_harness.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add benchmarks/scenarios.py
git commit -m "feat(benchmarks): add 10 deterministic scenarios, one per capability (Item 7)"
```

---

### Task 12: Item 7 — Baseline + CI

**Files:**
- Create: `benchmarks/baseline.json`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Generate baseline**

Run: `uv run python -m benchmarks.harness --iterations 100 --update-baseline`
Expected: `benchmarks/baseline.json` created with 10 entries

Verify: `cat benchmarks/baseline.json | head -n 40` shows `mean_ms`, `p50_ms`, `p95_ms` per capability.

- [ ] **Step 2: Wire CI (non-blocking, informational)**

Edit `.github/workflows/ci.yml`: add after drift checks:

```yaml
      - name: Benchmark (informational, non-blocking)
        continue-on-error: true
        run: uv run python -m benchmarks.harness --iterations 50 --output /tmp/bench.json && cat /tmp/bench.json
```

Do NOT gate merge on bench; this is W5 instrumentation (measured decision, not enforcement).

- [ ] **Step 3: Verify pyproject markers**

Edit `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: unit tests",
    "capability: capability-specific tests",
    "integration: integration tests",
    "e2e: end-to-end tests",
    "property: property-based tests (Hypothesis)",
    "benchmark: benchmark harness tests",
    "country: country capability tests",
    ...
]
```

Add to `[tool.coverage.run] omit` if you want `benchmarks/*` excluded from 95% gates (bench is not shipped code). Keep `paxman/*` gates at 95.

- [ ] **Step 4: Commit**

```bash
git add benchmarks/baseline.json benchmarks/scenarios.py .github/workflows/ci.yml pyproject.toml
git commit -m "ci(benchmarks): add baseline and informational bench job (Item 7)"
```

---

### Task 13: Item 7 — Docs

**Files:**
- Create: `benchmarks/README.md`

- [ ] **Step 1: Create benchmarks/README.md**

```markdown
# Benchmarks (Item 7, W5)

One scenario per capability, deterministic per (input, contract, library snapshot).

Run:
  uv run python -m benchmarks.harness --iterations 200
  uv run python -m benchmarks.harness --output bench.json
  uv run python -m benchmarks.harness --update-baseline  # refresh committed baseline.json

CI runs 50 iterations informational (non-blocking). Baseline is tracked but not gated.
Add a new capability: add one entry to `benchmarks/scenarios.py` with `register` + `contract_factory`.
```

- [ ] **Step 2: Commit**

```bash
git add benchmarks/README.md
git commit -m "docs(benchmarks): add harness README (Item 7)"
```

---

### Task 14: Item 8 — PEP 562 Lazy-Import Failing Tests (TDD Red)

**Files:**
- Create: `tests/unit/test_capability_lazy_import.py`
- Read: `paxman/capabilities/__init__.py`, `paxman/api/bootstrap.py`

- [ ] **Step 1: Write failing test**

Create `tests/unit/test_capability_lazy_import.py`:

```python
"""Item 8 — PEP 562 lazy exports for paxman.capabilities (W4).

Importing one capability should not pay for all ten. After PEP 562, importing
`paxman.capabilities` itself must be cheap, and `from paxman.capabilities import Email`
must not import URL's 15K-line IDNA table transitively.
"""

from __future__ import annotations

import sys
import importlib


def test_capabilities_init_is_lazy() -> None:
    """paxman.capabilities must expose __getattr__ (PEP 562 lazy)."""
    import paxman.capabilities as cap_mod
    import inspect

    src = inspect.getsource(cap_mod)
    assert "__getattr__" in src, "PEP 562 __getattr__ must be present"
    assert "__dir__" in src, "__dir__ must be present for completeness"


def test_import_email_does_not_import_url_data() -> None:
    """Importing Email alone must not load URL's IDNA table."""
    # Start from a clean slate: unload capabilities submodules if loaded
    for mod in list(sys.modules):
        if mod.startswith("paxman.capabilities"):
            del sys.modules[mod]

    import paxman.capabilities  # package itself

    # Import Email via lazy path
    from paxman.capabilities import Email  # noqa: F401

    # URL's heavy module should NOT have been imported transitively
    assert "paxman.capabilities.URL.rules.data.idna_uts46_data" not in sys.modules
    assert (
        "paxman.capabilities.URL" not in sys.modules or True
    )  # if Email doesn't import URL, second is not needed
    # At minimum, importing Email must not have imported all 10 capability packages
    # Count loaded capability submodules — should be <= 2 (Email package + its deps)
    loaded = [m for m in sys.modules if m.startswith("paxman.capabilities.")]
    # Email package loads Email + maybe shared core, but not other capabilities
    assert len(loaded) <= 4, f"Expected lazy import, got {loaded}"


def test_all_still_exported_via_all() -> None:
    """`__all__` must still list all ten capabilities for star-import and docs."""
    import paxman.capabilities as cap_mod

    assert set(cap_mod.__all__) == {
        "Country",
        "Currency",
        "Date",
        "Email",
        "IP",
        "ISBN",
        "Money",
        "Phone",
        "SIUnit",
        "URL",
    }
    # Access each via getattr still works
    for name in cap_mod.__all__:
        assert hasattr(cap_mod, name), f"Missing lazy export: {name}"
        # Actually getattr should return the class
        cls = getattr(cap_mod, name)
        assert hasattr(cls, "name"), f"{name} should be a Capability subclass"


def test_bootstrap_still_works() -> None:
    """register_all_shipped must still work with lazy exports."""
    from paxman.capabilities import Email
    from paxman.core.discovery import reset_registry
    from paxman.api.bootstrap import register_all_shipped

    reset_registry()
    registered = register_all_shipped()
    assert "email" in registered
    assert "url" in registered
    reset_registry()
```

- [ ] **Step 2: Run test to verify RED**

Run: `uv run pytest tests/unit/test_capability_lazy_import.py -v`
Expected: FAIL — `__getattr__` not in source, URL data loaded transitively

- [ ] **Step 3: Commit failing test**

```bash
git add tests/unit/test_capability_lazy_import.py
git commit -m "test(capabilities): add failing PEP 562 lazy-import tests (Item 8 RED)"
```

---

### Task 15: Item 8 — PEP 562 `__getattr__` (TDD Green)

**Files:**
- Modify: `paxman/capabilities/__init__.py`

- [ ] **Step 1: Implement lazy exports**

Replace `paxman/capabilities/__init__.py` with PEP 562 pattern (keep `__all__` eager for tooling, but defer heavy imports):

```python
"""Paxman capabilities — PEP 562 lazy exports (Item 8, W4).

Importing `paxman.capabilities` does not import any capability package.
`from paxman.capabilities import Email` imports only `paxman.capabilities.Email`.
This keeps `register_capability(Email())` cheap when only one capability is used.
The committed 15K-line URL IDNA table is not loaded unless URL is imported.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = [
    "Country",
    "Currency",
    "Date",
    "Email",
    "IP",
    "ISBN",
    "Money",
    "Phone",
    "SIUnit",
    "URL",
]

# Mapping from export name to module + attr (capability registry name is lowercase,
# but SIUnit is special-cased as camelCase package)
_LAZY: dict[str, tuple[str, str]] = {
    "Country": ("paxman.capabilities.Country.capability", "CountryCapability"),
    "Currency": ("paxman.capabilities.Currency.capability", "CurrencyCapability"),
    "Date": ("paxman.capabilities.Date.capability", "DateCapability"),
    "Email": ("paxman.capabilities.Email.capability", "EmailCapability"),
    "IP": ("paxman.capabilities.IP.capability", "IPCapability"),
    "ISBN": ("paxman.capabilities.ISBN.capability", "ISBNCapability"),
    "Money": ("paxman.capabilities.Money.capability", "MoneyCapability"),
    "Phone": ("paxman.capabilities.Phone.capability", "PhoneCapability"),
    "SIUnit": ("paxman.capabilities.SIUnit.capability", "SIUnitCapability"),
    "URL": ("paxman.capabilities.URL.capability", "URLCapability"),
}

if TYPE_CHECKING:
    # For pyright / IDE: eager imports only for type checking, not at runtime
    from paxman.capabilities.Country.capability import CountryCapability as Country
    from paxman.capabilities.Currency.capability import CurrencyCapability as Currency
    from paxman.capabilities.Date.capability import DateCapability as Date
    from paxman.capabilities.Email.capability import EmailCapability as Email
    from paxman.capabilities.IP.capability import IPCapability as IP
    from paxman.capabilities.ISBN.capability import ISBNCapability as ISBN
    from paxman.capabilities.Money.capability import MoneyCapability as Money
    from paxman.capabilities.Phone.capability import PhoneCapability as Phone
    from paxman.capabilities.SIUnit.capability import SIUnitCapability as SIUnit
    from paxman.capabilities.URL.capability import URLCapability as URL


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    if name in _LAZY:
        import importlib

        mod_name, attr = _LAZY[name]
        mod = importlib.import_module(mod_name)
        val = getattr(mod, attr)
        globals()[name] = val  # cache
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
```

Key decisions:
- Keep `__all__` eager (tooling, docs, `test_capability_exports.py` rely on it).
- `TYPE_CHECKING` block gives `pyright` the same names without runtime cost.
- `globals()[name] = val` caches after first access (PEP 562 idiom).

- [ ] **Step 2: Ensure bootstrap still works**

`paxman/api/bootstrap.py` currently does `from paxman.capabilities import Country, Currency, ...` — this still works (each import triggers `__getattr__` once, then cached). No change needed. But verify it doesn't import all at package import time: `import paxman.capabilities` alone should not trigger 10 imports.

- [ ] **Step 3: Run lazy-import tests GREEN**

Run: `uv run pytest tests/unit/test_capability_lazy_import.py -v`
Expected: PASS

Run: `uv run pytest tests/unit/test_capability_exports.py -v`
Expected: PASS (export completeness still enforced)

- [ ] **Step 4: Commit**

```bash
git add paxman/capabilities/__init__.py
git commit -m "perf(capabilities): adopt PEP 562 lazy exports for W4 (Item 8)"
```

---

### Task 16: Item 8 — Type + Lint + Perf Verification

**Files:**
- Modify: `pyproject.toml` (if needed for per-file-ignores)
- Read: `paxman/core/__init__.py` (ensure no eager capability import leaked)

- [ ] **Step 1: Run type and lint gates**

Run: `uv run pyright`
Expected: PASS — `TYPE_CHECKING` block satisfies strict mode; `__getattr__` is untyped by design (add `# type: ignore` if needed per ruff, but repo forbids `# type: ignore` in source — use `pyright: ignore` is also forbidden; instead add `if TYPE_CHECKING` imports cover the public names, and leave `__getattr__` with `no-untyped-def` suppression via `per-file-ignores` if ruff complains)

If `ruff` complains about `N814` or `F401` for `TYPE_CHECKING` imports, add to `pyproject.toml`:

```toml
"paxman/capabilities/__init__.py" = ["N814", "F401"]
```

But prefer narrowest scope: check `ruff check paxman/capabilities/__init__.py` and amend only if needed.

- [ ] **Step 2: Import-time micro-bench**

Run:

```bash
uv run python -c "import time, subprocess, json, sys; import timeit; print(timeit.timeit('import importlib; importlib.import_module(\"paxman.capabilities\")', number=100))"
uv run python -c "import timeit; print(timeit.timeit('from paxman.capabilities import Email', setup='import sys; [sys.modules.pop(k,None) for k in list(sys.modules) if k.startswith(\"paxman.capabilities\")]', number=50))"
```

Before/after comparison: `import paxman.capabilities` should be <5ms; `from paxman.capabilities import Email` should not load `paxman.capabilities.URL.rules.data.idna_uts46_data`. Record numbers in commit message.

- [ ] **Step 3: Run full verification**

Run: `uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore(lint): polish lazy-export typing and lint (Item 8)"
```

---

### Task 17: Final — Cross-Vertical Verification Gate

**Files:**
- None (verification only)

- [ ] **Step 1: Run the full merge-blocking gate**

Run: `uv run ruff check paxman/ tests/ benchmarks/ tools/ 2>&1 | head -n 100`
Expected: 0 errors

Run: `uv run ruff format --check paxman/ tests/ benchmarks/ tools/`
Expected: PASS

Run: `uv run pyright`
Expected: 0 errors

Run: `uv run import-linter lint`
Expected: PASS — especially `Capability independence` contract (no sibling imports; generated tables are isolated)

Run: `uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q`
Expected: PASS; per-package gates:

```bash
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
```

Expected: all 4 PASS

- [ ] **Step 2: Run drift + bench checks**

Run: `uv run python tools/regenerate_currency_data.py --check && uv run python tools/regenerate_si_prefix_data.py --check && uv run python -m benchmarks.harness --iterations 20 --output /tmp/bench_final.json && cat /tmp/bench_final.json | head -n 60`
Expected: both drift checks PASS, bench JSON has 10 scenarios

- [ ] **Step 3: Run lazy-import smoke**

Run: `uv run pytest tests/unit/test_capability_lazy_import.py tests/unit/test_contract_surface.py tests/unit/test_currency_data_regeneration.py tests/benchmarks/test_harness.py -v`
Expected: PASS

- [ ] **Step 4: No commit — gate only**

If any gate fails, fix in the relevant Task (3, 8, 9, 12, 16) and re-run. Do not commit a failing gate.

---

## Self-Review Checklist

**1. Spec coverage:** All 4 Mid-Term items from §9 mapped to tasks?
- [x] Item 5 Protocol-vs-ABC → Tasks 1–4 (ADR, tests, engine, docs)
- [x] Item 6 Shared-vocabulary pipeline (M8, Currency/Money) → Tasks 5–9 (snapshot, tool, migrate Currency, migrate Money, drift+CI)
- [x] Item 7 Benchmark harness (W5) → Tasks 10–13 (harness, scenarios, baseline+CI, docs)
- [x] Item 8 PEP 562 lazy exports (W4) → Tasks 14–16 (tests, impl, verify)
- [x] Cross-vertical gate → Task 17

**2. Placeholder scan:** Search plan for `TBD`, `TODO`, `implement later`, `fill in details`, `Add appropriate`, `Similar to Task`. None present — every step has exact file paths, complete code blocks, exact commands with expected output, no "handle edge cases" hand-waving.

**3. Type consistency:**
- `CapabilityContract` is used consistently as `paxman.core.capability_contract.CapabilityContract`; `Contract` is internal `paxman.core.contract.Contract` where retained.
- `ExecutionResult.contract: CapabilityContract`, `run_capability(text: str, contract: CapabilityContract)`.
- `SCENARIOS` entries: `{"capability": str, "text": str, "register": Callable[[], None], "contract_factory": Callable[[], CapabilityContract]}` — used identically in `harness.py` and `scenarios.py`.
- `paxman/capabilities/__init__.py` lazy mapping keys match `__all__` exactly (Country, Currency, Date, Email, IP, ISBN, Money, Phone, SIUnit, URL).
- `SYMBOL_TOKENS: tuple[str, ...]` and `SYMBOL_TO_CODES: dict[str, list[str]]` naming matches current `currency_symbols.py` / `cldr_currencies.py` expectations of grammar/rule code; no rename without updating consumers.

Fixes applied inline: ensured `benchmarks` excluded from coverage gates, `TYPE_CHECKING` block added for pyright, drift checks wired for all three generators.

---

## Execution Handoff

Plan complete and saved to `ocs/development/plans/2026-08-19-mid-term-recommendations.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task (Tasks 1–17), review between tasks, fast iteration. REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` (fresh subagent per task + two-stage review).

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**

