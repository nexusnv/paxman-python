# SI Unit Capability — Implementation Plan (Rebased)

| **Title** | SI Unit Capability |
| **Date** | 2026-08-12 |
| **Status** | Draft — ready for review |
| **Branch** | `feature/si-unit-capability` (commit per task) |
| **Milestone** | `docs/development/MILESTONE.md` row #23 — “SI unit” (LOOKUP_TABLE strategy) |
| **Sibling template** | `paxman/capabilities/Currency/` (identifier-only LOOKUP_TABLE capability) |
| **Authoritative spec** | `HOW_TO_ADD_NEW_CAPABILITY.md` (62 KB) — read before Task 1; where this plan and HOW_TO disagree, HOW_TO wins |
| **Seam rebase** | 2026-08-12 — plan updated for the grammar-extension seam now on main (PRs #19–#21: `Grammar.semantics` + `Rule.target_semantics` affinity routing per ADR-0003, optional `active_grammars` with base-`None` fallback, `extra_grammars` community opt-in) and the replay-hash removal (PR #18). The seam deltas are marked **SEAM** inline; R1/R2 engine refinements were re-verified against the current engine and still hold. |

> **For agentic workers.** This plan is written to be executed by a
> worker agent one task at a time. Every task is TDD: **Step 1 RED**
> (write the failing test), **Step 2 GREEN** (write the implementation),
> then the scoped verify command and the commit. Do not skip steps, do
> not reorder tasks, do not “improve” the design — D-decisions are
> locked (see §1). The full suite is only green after Task 13; the
> per-task verify commands are scoped so each task is independently
> green. Commit with the exact message given for each task.

---

## §1 Cross-Part Contract

### Naming

The package is `paxman/capabilities/SIUnit/` — the capability
canonicalizes **SI unit expressions** (symbols, names, compounds), not
the SI system itself. Class names: `SIUnitNotation`, `SIUnitContract`,
`SIUnitCapability`; internal registry `capability_name = "si_unit"` and
capability class `name = "si_unit"`; public alias `SIUnit` in
`paxman/capabilities/__init__.py` (mirrors `Currency`, `ISBN`). Tests
live in `tests/capabilities/si_unit/` and use the `si_unit` marker;
commit scopes are `feat(si_unit)`.

### Goal

`canonicalize_text("megahertz")` → `"MHz"`, `canonicalize_text("m/s²")` →
`"m/s2"`, with full provenance — the MILESTONE row #23 examples:

| Input | Canonical |
|-------|-----------|
| `"Kilogram"` | `"kg"` |
| `"Kelvin"` | `"K"` |
| `"megahertz"` | `"MHz"` |
| `"m/s²"` | `"m/s2"` |
| `"km/h"` | `"km/h"` |

Identity-only: no quantities, no magnitudes, no name-compounds
("metre per second" does not resolve as a compound — its words are recognized
separately, yielding AMBIGUOUS). Strategy per MILESTONE row #23:
**LOOKUP_TABLE (unit name/symbol/prefix lookup, case-sensitive canonical
symbols)** — BIPM SI Brochure (9th edition, 2019) + ISO 80000-1:2022.

### D-Decisions (locked — do not revisit without a new ADR)

- **D1 — Three recognition grammars.** `symbol_recognition` (case-exact
  lexicon), `name_recognition` (case-folded lexicon), `compound_recognition`
  (regex shape). Grammar names must be lowercase snake_case; each file is
  one grammar (the `Grammar` ABC with a `name` class attr + `recognize()`);
  names are `symbol_recognition` / `name_recognition` / `compound_recognition`.
  **SEAM:** each grammar ALSO declares `semantics` — the identity id
  (`semantics = "symbol_recognition"`, etc.), mandatory at class-definition
  time by `Grammar.__init_subclass__`. SIUnit has no coalesced groups
  (ADR-0003): all three ids are singletons, so identity-with-name is the
  sanctioned form and nothing is added to the `_COALESCED_SEMANTICS`
  allowlist in `tests/unit/test_grammar_semantics_metadata.py`.
- **D2 — Symbol lookarounds block separators.** The symbol grammar's
  lookarounds block `\w`, sign chars (`-`, `+`, U+2212), **and** the
  compound separators `/`, `·`, `⋅`. This is what keeps `"m/s²"`, `"N·m"`,
  `"km/h"` from fragmenting into bare symbol matches — the milestone
  compounds resolve via the compound grammar as a single token, and the
  symbol grammar finds *nothing* inside them (engine-verified: `_dedup_spans`
  is per-grammar, so a symbol match inside a compound would collide into
  AMBIGUOUS).
- **D3 — Canonical form is the unit symbol.** Prefixed units keep their
  written symbol (`"km"`, `"MHz"`, `"µg"`); `"l"` canonicalizes to `"L"`
  (litre, BIPM Table 8); compounds render ASCII exponents and `·`
  separators (`"m/s²"` → `"m/s2"`, `"N⋅m"` → `"N·m"`, `"m·s⁻²"` →
  `"m·s-2"`).
- **D4 — Longest-first token tables.** Symbol and name alternations are
  built from generated, longest-first token tuples (`unit_symbol_tokens.py`,
  `unit_name_tokens.py` in `grammar/data/`), so `"cm"` beats `"c"`, `"MHz"`
  beats `"M"`, `"degree celsius"` beats `"degree"`.
- **D5 — Prefixed units and names are generated.** `tools/regenerate_si_prefix_data.py`
  computes the prefixed-unit set (prefix symbol + prefixable unit symbol)
  and the prefixed-name map (prefix name + unit name → prefixed symbol)
  from the maintained authority tables, excluding official-symbol and
  official-name collisions. Generated modules are edited only via the tool
  (ISBN range-message precedent).
- **D6 — Case-exact canonical symbols.** `"pa"` is *not* `"Pa"` (pascal
  is uppercase); `"Kg"` is not `"kg"`. Symbols are arbitrary glyph strings
  and case matters (`"s"` second vs `"S"` siemens, `"K"` kelvin vs `"k"`
  kilo). Only the *name* grammar case-folds.
- **D7 — Status semantics.** Recognized-but-unresolved tokens are
  INVALID; unrecognized input is MISSING; multiple distinct canonical
  values are AMBIGUOUS (engine `_determine_status`: AMBIGUOUS > SUCCESS >
  INVALID > MISSING). Quantity-glued input (`"25°C"`, `"5kg"`) is
  MISSING — same house rule as Currency's `"USD500"` → MISSING.
- **D8 — Name resolution is a dedicated rule.** Names resolve via a
  dedicated `SectionNames` rule (BIPM module, **SEAM:** `target_semantics =
  frozenset({"name_recognition"})` — the affinity-routing replacement for
  `target_grammars`, ADR-0003) against `FULL_NAME_TO_SYMBOL` = maintained
  `NAME_TO_SYMBOL` ∪ generated `PREFIXED_NAME_TO_SYMBOL` (Task 4) — the
  Currency `SectionNames`/`word_recognition` precedent. This is what makes
  the locked e2e rows `"megahertz"` → `"MHz"` and `"Kilogram"` → `"kg"`
  reachable: the symbol rules only ever see symbol-shaped notations.
- **D9 — The kilogram is not prefixable (BIPM §3.2).** Prefixes attach to
  the gram (`"g"`), never to `"kg"`: the Task 4 generator excludes `"kg"`
  from `_prefixable_units()` so it never emits `"kkg"`, `"Mkg"`,
  `"kilokilogram"`, or any kilo-stacked junk. `"kg"` remains the official
  base-unit symbol and `"kilogram"` the official base-unit name.

### Engine-verified refinements (three research conflicts, locked)

- **R1 — `"KHz"` → MISSING, not INVALID.** §7.6 of the research paper
  locked `"KHz"` → INVALID, but the locked symbol grammar is a token
  alternation with lookarounds; no token covers `"KHz"`, so nothing is
  recognized → MISSING. Do not add a fallback grammar to force INVALID —
  it would break name/symbol disambiguation and prose → MISSING. (Mirrors
  the Currency precedent: `"USD500"` → MISSING, never INVALID.)
- **R2 — `"m s"` → AMBIGUOUS, not compound-SUCCESS.** §7.6 locked `"m s"`
  → compound `"m·s"`, but the engine preserves cross-grammar overlaps by
  design, so `"m"` and `"s"` each survive as symbol candidates → 2
  distinct canonical values → AMBIGUOUS. The compound grammar does **not**
  accept a space separator (space-separated symbols are a symbol list, not
  a compound; the research's `"m s⁻²"` form is dropped for this reason).
  Do not suppress the symbol grammar or the compound grammar to force
  SUCCESS.
- **R3 — Semantics affinity routing (SEAM, ADR-0003).** The engine routes
  each recognition only to rules whose `target_semantics` includes the
  producing grammar's `semantics` (composition built per capability in
  `run_capability` via `semantics_by_name = {g.name: g.semantics}`), and
  `_validate_affinity` fails fast with `ContractError` if a rule declares a
  semantics id no grammar claims. Because the three SIUnit grammars declare
  identity semantics and the six rules target exactly those ids, routing is
  a straight rename of the plan's original grammar-name routing — no
  behavioral change to any locked row. This also means SIUnit's
  `"name_recognition"` semantics id may coincide with Country's same-named
  id: semantics groups are scoped per capability (the engine composes per
  capability; `tests/unit/test_grammar_semantics_consistency.py` blesses
  cross-capability id reuse, e.g. Currency/Money `code_recognition`).

### Capability surface

| Contract | Value |
|----------|-------|
| `SIUnitContract` | `@dataclass(frozen=True)` extending `CapabilityContract` — NO slots |
| `DEFAULT_OUTPUT_FORMAT` | `"symbol"` (ClassVar) |
| `OFFERED_OUTPUT_FORMATS` | `frozenset()` (ClassVar) |
| `capability_name` | `field(default="si_unit", init=False)` |
| `active_grammars` | **SEAM:** do NOT override — base default `None` (engine runs all three shipped grammars in `get_grammars()` order; `active_grammars` is implemented only by feature-gated capabilities, HOW_TO §Implementing `active_grammars`) |
| `extra_grammars` | **SEAM:** inherited base field, default `()` — surfaced on `create_contract` (community opt-in; the Task 9 factory forwards it) |
| `_extra_dict_fields` | base `{}` (no capability-specific fields — do not override) |
| `format_value()` | identity (base — do not override) |

`create_contract()` is a staticmethod with the unanimous common block
(`excluded_rules`, `pinned_rules`, `year`, `output_format`, keyword-only)
and **no** capability-specific parameters (satisfies `ContractFactory`).

### Module layout (research §7.1, rebased)

```text
paxman/capabilities/SIUnit/
├── __init__.py          # exports SIUnitCapability, SIUnitContract, SIUnitNotation
├── notation.py          # SIUnitNotation (frozen, slots=True)
├── contract.py          # SIUnitContract (frozen, NO slots)
├── capability.py        # SIUnitCapability — wiring + static create_contract
├── grammar/
│   ├── symbol_recognition.py      # Lexicon, case-exact (D2/D6)
│   ├── name_recognition.py        # Lexicon, case-folded (D4)
│   ├── compound_recognition.py    # Regex shape (D3)
│   └── data/
│       ├── unit_symbol_tokens.py  # GENERATED — SYMBOL_TOKENS, longest-first
│       ├── unit_name_tokens.py    # GENERATED — NAME_TOKENS, longest-first
│       └── compound_tokens.py     # GENERATED — shape constants for the compound grammar
└── rules/
    ├── bipm_si_brochure_ed2019.py # PUBLICATION + 5 rule classes
    ├── iso_80000_ed2022.py        # PUBLICATION + SectionCompounds
    └── data/
        ├── si_base_units.py       # BASE_UNIT_SYMBOLS (7)
        ├── si_derived_units.py    # DERIVED_UNIT_SYMBOLS (22 special names + "g")
        ├── si_nonsi_units.py      # NONSI_UNIT_SYMBOLS (Tables 8–9) + LITRE_WRITTEN_FORMS
        ├── si_prefixes.py         # PREFIX_SYMBOLS (24) + PREFIX_NAMES (24)
        ├── unit_names.py          # NAME_TO_SYMBOL (maintained names — Tables 1, 3–4, 8–9)
        ├── prefixed_units.py      # GENERATED — PREFIXED_UNIT_SYMBOLS
        └── prefixed_unit_names.py # GENERATED — PREFIXED_NAME_TO_SYMBOL
tools/regenerate_si_prefix_data.py  # the generator (ISBN range-data precedent)
```

### e2e contract (locked — `tests/integration/test_si_unit_pipeline.py` rows)

| Input | Status | Canonical | Validated by |
|-------|--------|-----------|--------------|
| `"Kilogram"` | SUCCESS | `"kg"` | BIPM Table 1 (name→symbol) |
| `"Kelvin"` | SUCCESS | `"K"` | BIPM Table 1 |
| `"megahertz"` | SUCCESS | `"MHz"` | BIPM §3.2 (prefix) |
| `"m"` | SUCCESS | `"m"` | BIPM Table 1 |
| `"kg"` | SUCCESS | `"kg"` | BIPM Table 1 |
| `"cd"` | SUCCESS | `"cd"` | BIPM Table 1 |
| `"Pa"` | SUCCESS | `"Pa"` | BIPM Tables 3–4 |
| `"°C"` | SUCCESS | `"°C"` | BIPM Tables 3–4 |
| `"l"` | SUCCESS | `"L"` | BIPM Tables 8–9 (l→L) |
| `"L"` | SUCCESS | `"L"` | BIPM Tables 8–9 |
| `"km"` | SUCCESS | `"km"` | BIPM §3.2 |
| `"µg"` | SUCCESS | `"µg"` | BIPM §3.2 |
| `"m/s²"` | SUCCESS | `"m/s2"` | ISO 80000-1 §6.5 |
| `"km/h"` | SUCCESS | `"km/h"` | ISO 80000-1 §6.5 |
| `"N·m"` | SUCCESS | `"N·m"` | ISO 80000-1 §6.5 |
| `"kg·m/s²"` | SUCCESS | `"kg·m/s2"` | ISO 80000-1 §6.5 |
| `"g/cm³"` | SUCCESS | `"g/cm3"` | ISO 80000-1 §6.5 |
| `"m·s⁻²"` | SUCCESS | `"m·s-2"` | ISO 80000-1 §6.5 |
| `"da"` | INVALID | — | bare prefix (recognized, no rule) |
| `"k"` | INVALID | — | bare prefix (recognized, no rule) |
| `"QQQ/zzz"` | INVALID | — | compound shape, unknown groups |
| `"pa"` | MISSING | — | case-exact symbols (D6) |
| `"KHz"` | MISSING | — | refinement R1 |
| `"Kg"` | MISSING | — | case-exact (D6) |
| `"25°C"` | MISSING | — | quantity-glued (D7) |
| `"m s"` | AMBIGUOUS | — | refinement R2 |
| `"USD"` | MISSING | — | not an SI token |

### Data-authoring note (Currency List One precedent)

The authority tables (`si_base_units.py`, `si_derived_units.py`,
`si_nonsi_units.py`, `si_prefixes.py`, maintained names in
`unit_names.py`) are snapshots of the cited BIPM tables. The plan locks
their structure, the entries verifiable here (7 base, 22 special-name
derived + `"g"`, 24 prefixes, the name→symbol rows), and invariant
/ locked-row tests (counts, collision guards). The implementer completes
any remaining Table 8–9 non-SI entries directly from the cited brochure
and adjusts the non-SI count guard to the true total — never fabricate
data, never invent an entry not in the brochure.

---

## §2 Implementation Tasks

### Task 1 — `feat(si_unit): add SIUnitNotation and package skeleton`

**Step 1 RED** — `tests/capabilities/si_unit/test_notation.py`:

```python
"""Tests for SIUnitNotation."""

import pytest

from paxman.capabilities.SIUnit.notation import SIUnitNotation


@pytest.mark.capability
@pytest.mark.si_unit
class TestSIUnitNotation:
    """Tests for SIUnitNotation."""

    def test_text_and_shape(self) -> None:
        n = SIUnitNotation(text="kg", shape="symbol")
        assert n.text == "kg"
        assert n.shape == "symbol"

    def test_rejects_empty_text(self) -> None:
        with pytest.raises(ValueError):
            SIUnitNotation(text="", shape="symbol")

    def test_rejects_unknown_shape(self) -> None:
        with pytest.raises(ValueError):
            SIUnitNotation(text="kg", shape="quantity")

    def test_as_list(self) -> None:
        n = SIUnitNotation(text="kg", shape="symbol")
        assert n.as_list() == ["kg", "symbol"]

    def test_frozen(self) -> None:
        n = SIUnitNotation(text="kg", shape="symbol")
        with pytest.raises(Exception):
            n.text = "m"  # type: ignore[misc]
```

**Step 2 GREEN** — `paxman/capabilities/SIUnit/notation.py`:

```python
"""SI unit notation — an SI unit expression as written."""

from __future__ import annotations

from dataclasses import dataclass

_VALID_SHAPES = frozenset({"symbol", "name", "compound"})


@dataclass(frozen=True, slots=True)
class SIUnitNotation:
    """An SI unit (no quantity, no magnitude) as written in the input.

    Attributes:
        text: The unit text. Symbols keep their exact casing; names are
            grammar-folded to lowercase; compounds keep the written form.
        shape: One of "symbol", "name", "compound".
    """

    text: str
    shape: str

    def __post_init__(self) -> None:
        """Validate the shape and non-empty text.

        Raises:
            ValueError: If text is empty or shape is not a valid shape.
        """
        if not self.text:
            raise ValueError("text must be non-empty")
        if self.shape not in _VALID_SHAPES:
            raise ValueError(
                f"invalid shape {self.shape!r}; expected one of {sorted(_VALID_SHAPES)}"
            )

    def as_list(self) -> list[str]:
        """Flatten the notation for structural equality checks."""
        return [self.text, self.shape]
```

Also create the subpackage skeletons (one-line docstring `__init__.py`
files, mirroring Currency): `SIUnit/grammar/__init__.py`,
`SIUnit/grammar/data/__init__.py`, `SIUnit/rules/__init__.py`,
`SIUnit/rules/data/__init__.py`. Create `SIUnit/__init__.py` with only
the notation export — the full three-export form lands in Task 9:

```python
"""SI Unit capability package."""

from __future__ import annotations

from paxman.capabilities.SIUnit.notation import SIUnitNotation

__all__ = ["SIUnitNotation"]
```

Register the per-capability marker now so every later `pytest.mark.si_unit`
is warning-free — add to `markers` in `[tool.pytest.ini_options]`
(`pyproject.toml`), after `"url: url capability tests",`:

```toml
    "si_unit: si unit capability tests",
```

Check `uv run import-linter lint` — if the contract config enumerates
capability packages explicitly, add the SIUnit package to the relevant
sources; the blanket `paxman.capabilities` contract otherwise covers it.

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `feat(si_unit): add SIUnitNotation and package skeleton`

---

### Task 2 — `feat(si_unit): add SIUnitContract`

**Step 1 RED** — `tests/capabilities/si_unit/test_contract.py`:

```python
"""Tests for SIUnitContract."""

import pytest

from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import ContractError


@pytest.mark.capability
@pytest.mark.si_unit
class TestSIUnitContract:
    """Tests for SIUnitContract."""

    def test_is_capability_contract_subclass(self) -> None:
        assert issubclass(SIUnitContract, CapabilityContract)

    def test_capability_name(self) -> None:
        assert SIUnitContract().capability_name == "si_unit"

    def test_default_output_format(self) -> None:
        assert SIUnitContract().output_format == "symbol"

    def test_offered_formats(self) -> None:
        assert SIUnitContract.OFFERED_OUTPUT_FORMATS == frozenset()

    def test_default_format_resolution(self) -> None:
        for fmt in (None, "default", "symbol"):
            assert SIUnitContract(output_format=fmt).output_format == "symbol"

    def test_unknown_format_rejected(self) -> None:
        with pytest.raises(ContractError):
            SIUnitContract(output_format="name")

    def test_active_grammars_is_base_default(self) -> None:
        # SEAM: no feature gating -> the contract does NOT override
        # active_grammars; the base returns None and the engine runs every
        # shipped grammar in get_grammars() declaration order.
        assert SIUnitContract().active_grammars is None

    def test_extra_grammars_defaults_empty(self) -> None:
        # SEAM: the community opt-in field is inherited from the base.
        assert SIUnitContract().extra_grammars == ()

    def test_frozen(self) -> None:
        with pytest.raises(Exception):
            SIUnitContract().capability_name = "other"  # type: ignore[misc]
```

**Step 2 GREEN** — `paxman/capabilities/SIUnit/contract.py`:

```python
"""SI Unit contract — user-facing configuration for SI Unit capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class SIUnitContract(CapabilityContract):
    """User-facing configuration for SI Unit capability.

    Attributes:
        capability_name: Fixed to "si_unit" (not user-settable).
        output_format: Canonical output format — "symbol" (the canonical
            unit symbol) is the only format. Optional — None/"default"/
            "symbol" all resolve to "symbol".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over
            excluded_rules).
        year: Year for temporal filtering.
        extra_grammars: Community grammar names (opt-in) to run alongside
            the shipped grammars, in order (SEAM — inherited from base).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "symbol"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="si_unit", init=False)
```

No `active_grammars` override (SEAM: the base `None` default runs all three
shipped grammars; SI Unit has no input-shape feature flags), no
`_extra_dict_fields` override (no capability-specific fields — base `{}`
applies) and no `__post_init__` (nothing to validate beyond the base
`Contract` resolution of `output_format`/`year`/pinned-excluded).

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `feat(si_unit): add SIUnitContract`

### Task 3 — `feat(si_unit): add authority data tables`

**Step 1 RED** — `tests/capabilities/si_unit/test_data.py` (authority-table
part only; the generated-data part lands with the generator in Task 4):

```python
"""Tests for the SI Unit maintained authority tables."""

import pytest

from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import NONSI_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_prefixes import (
    PREFIX_NAMES,
    PREFIX_SYMBOLS,
)
from paxman.capabilities.SIUnit.rules.data.unit_names import NAME_TO_SYMBOL


@pytest.mark.capability
@pytest.mark.si_unit
class TestAuthorityTables:
    """Locked counts and rows for the maintained authority tables."""

    def test_base_unit_symbols(self) -> None:
        assert BASE_UNIT_SYMBOLS == frozenset({"m", "kg", "s", "A", "K", "mol", "cd"})

    def test_derived_unit_symbols(self) -> None:
        # 22 BIPM Table 3 special-name units + "g" (the gram — the
        # prefix attachment point for mass, per BIPM SI Brochure §3.2).
        assert len(DERIVED_UNIT_SYMBOLS) == 23
        assert {"rad", "Hz", "Pa", "Ω", "°C", "kat"} <= DERIVED_UNIT_SYMBOLS

    def test_prefix_symbols(self) -> None:
        assert len(PREFIX_SYMBOLS) == 24
        assert PREFIX_SYMBOLS == frozenset(
            {
                "da",
                "h",
                "k",
                "M",
                "G",
                "T",
                "P",
                "E",
                "Z",
                "Y",
                "R",
                "Q",
                "d",
                "c",
                "m",
                "µ",
                "n",
                "p",
                "f",
                "a",
                "z",
                "y",
                "r",
                "q",
            }
        )

    def test_prefix_names(self) -> None:
        assert len(PREFIX_NAMES) == 24
        assert PREFIX_NAMES["k"] == "kilo"
        assert PREFIX_NAMES["µ"] == "micro"
        assert PREFIX_NAMES["da"] == "deca"

    def test_non_si_units(self) -> None:
        assert {
            "min",
            "h",
            "d",
            "°",
            "′",
            "″",
            "ha",
            "L",
            "l",
            "t",
            "Da",
            "eV",
        } <= NONSI_UNIT_SYMBOLS

    def test_name_to_symbol_locked_rows(self) -> None:
        assert NAME_TO_SYMBOL["kilogram"] == "kg"
        assert NAME_TO_SYMBOL["kelvin"] == "K"
        assert NAME_TO_SYMBOL["degree celsius"] == "°C"
        assert NAME_TO_SYMBOL["litre"] == "L"
        assert NAME_TO_SYMBOL["metre"] == "m"
        assert NAME_TO_SYMBOL["hertz"] == "Hz"
```

**Step 2 GREEN** — the four maintained authority modules in
`paxman/capabilities/SIUnit/rules/data/`:

`si_base_units.py` — `BASE_UNIT_SYMBOLS: frozenset[str] = frozenset({"m", "kg", "s", "A", "K", "mol", "cd"})` — BIPM SI Brochure (9th ed., 2019), Table 1.

`si_derived_units.py` — `DERIVED_UNIT_SYMBOLS` = the 22 Table 3 special-name
symbols (`rad`, `sr`, `Hz`, `N`, `Pa`, `J`, `W`, `C`, `V`, `F`, `Ω`, `S`,
`Wb`, `T`, `H`, `°C`, `lm`, `lx`, `Bq`, `Gy`, `Sv`, `kat`) plus `"g"`
(the gram — prefix attachment point; not itself a Table 3 entry).

`si_nonsi_units.py` — `NONSI_UNIT_SYMBOLS` = BIPM Tables 8–9 non-SI units
accepted for use with the SI, plus `LITRE_WRITTEN_FORMS = frozenset({"L", "l"})`.
The entries verifiable here are `min`, `h`, `d`, `°`, `′`, `″`, `ha`, `L`,
`l`, `t`, `Da`, `eV`, `u`, `Å`, `b`, `bar`, `mmHg` — complete the set from
the cited brochure and mirror the test's non-SI subset accordingly.

`si_prefixes.py`:

```python
"""SI prefix symbols and names (BIPM SI Brochure, 9th ed., 2019, Table 5)."""

from __future__ import annotations

PREFIX_SYMBOLS: frozenset[str] = frozenset(
    {
        "da",
        "h",
        "k",
        "M",
        "G",
        "T",
        "P",
        "E",
        "Z",
        "Y",
        "R",
        "Q",
        "d",
        "c",
        "m",
        "µ",
        "n",
        "p",
        "f",
        "a",
        "z",
        "y",
        "r",
        "q",
    }
)

PREFIX_NAMES: dict[str, str] = {
    "Q": "quetta",
    "R": "ronna",
    "Y": "yotta",
    "Z": "zetta",
    "E": "exa",
    "P": "peta",
    "T": "tera",
    "G": "giga",
    "M": "mega",
    "k": "kilo",
    "h": "hecto",
    "da": "deca",
    "d": "deci",
    "c": "centi",
    "m": "milli",
    "µ": "micro",
    "n": "nano",
    "p": "pico",
    "f": "femto",
    "a": "atto",
    "z": "zepto",
    "y": "yocto",
    "r": "ronto",
    "q": "quecto",
}
```

`unit_names.py` — `NAME_TO_SYMBOL: dict[str, str]` mapping every maintained
unit name (lowercase, single- or multi-word) to its canonical symbol: the
base, derived, and non-SI names of the tables above. **`"gram"` is a
maintained name here** (`"gram": "g"` — the gram is the prefix attachment
point per BIPM §3.2/D9, and Task 8's `test_gram_is_the_prefix_attachment_point`
plus the generator's "microgram" row both require it). Prefixed names are NOT
maintained here — they live in the generated `prefixed_unit_names.py`
(D8). Locked rows: `"kilogram": "kg"`, `"kelvin": "K"`,
`"degree celsius": "°C"`, `"litre": "L"`, `"metre": "m"`, `"hertz": "Hz"`,
`"gram": "g"`, plus the full name set for every table entry.

Each module carries a docstring citing its BIPM table and a note that it is
a maintained authority snapshot (regenerate via the tool in Task 4 after
edits). Additional data modules added to this directory MUST be registered
in the Task 4 consistency scan.

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `feat(si_unit): add authority data tables`

---

### Task 4 — `feat(si_unit): add prefixed-unit data generator`

**Step 1 RED** — extend `tests/capabilities/si_unit/test_data.py` with the
generated-data tests (write the generated module imports first; RED until
the tool runs in GREEN):

```python
"""Tests for the generated SI Unit data modules."""

import subprocess
import sys
from pathlib import Path

import pytest

from paxman.capabilities.SIUnit.grammar.data.unit_name_tokens import NAME_TOKENS
from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.capabilities.SIUnit.rules.data.prefixed_unit_names import (
    PREFIXED_NAME_TO_SYMBOL,
)
from paxman.capabilities.SIUnit.rules.data.prefixed_units import PREFIXED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import NONSI_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_prefixes import PREFIX_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.unit_names import NAME_TO_SYMBOL

TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools"
GENERATOR = TOOLS_DIR / "regenerate_si_prefix_data.py"


@pytest.mark.capability
@pytest.mark.si_unit
class TestGeneratedData:
    """Invariants and locked rows for the generated tables."""

    def test_prefixed_units_disjoint_from_official(self) -> None:
        official = BASE_UNIT_SYMBOLS | DERIVED_UNIT_SYMBOLS | NONSI_UNIT_SYMBOLS
        assert PREFIXED_UNIT_SYMBOLS.isdisjoint(official)

    def test_locked_prefixed_rows(self) -> None:
        for token in ("km", "MHz", "µg", "mg", "cm", "hPa", "keV", "kDa", "dam"):
            assert token in PREFIXED_UNIT_SYMBOLS
        assert "kg" not in PREFIXED_UNIT_SYMBOLS  # official base symbol wins
        assert "cd" not in PREFIXED_UNIT_SYMBOLS  # candela wins over centi-day

    def test_prefixed_name_to_symbol_locked_rows(self) -> None:
        assert PREFIXED_NAME_TO_SYMBOL["megahertz"] == "MHz"
        assert PREFIXED_NAME_TO_SYMBOL["kilometre"] == "km"
        assert PREFIXED_NAME_TO_SYMBOL["microgram"] == "µg"
        assert "kilogram" not in PREFIXED_NAME_TO_SYMBOL  # official name wins
        assert "kg" not in PREFIXED_NAME_TO_SYMBOL

    def test_no_kg_prefix_stacking(self) -> None:
        # BIPM §3.2 (D9): prefixes attach to the gram, so "kg" is never a
        # prefixable unit — no "kilokilogram"/"megakilogram" junk.
        assert not any(name.endswith("kilogram") for name in PREFIXED_NAME_TO_SYMBOL)
        assert set(PREFIXED_NAME_TO_SYMBOL).isdisjoint(NAME_TO_SYMBOL)

    def test_symbol_tokens_cover_and_order(self) -> None:
        official = BASE_UNIT_SYMBOLS | DERIVED_UNIT_SYMBOLS | NONSI_UNIT_SYMBOLS
        assert set(SYMBOL_TOKENS) == official | PREFIX_SYMBOLS | PREFIXED_UNIT_SYMBOLS
        lengths = [len(t) for t in SYMBOL_TOKENS]
        assert lengths == sorted(lengths, reverse=True)

    def test_name_tokens_longest_first(self) -> None:
        lengths = [len(t) for t in NAME_TOKENS]
        assert lengths == sorted(lengths, reverse=True)
        assert "degree celsius" in NAME_TOKENS
        assert "kilometre" in NAME_TOKENS
        assert "megahertz" in NAME_TOKENS

    def test_generator_is_idempotent(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            capture_output=True,
            text=True,
            cwd=TOOLS_DIR.parent,
        )
        assert result.returncode == 0, result.stderr
```

**Step 2 GREEN** — `tools/regenerate_si_prefix_data.py`: a deterministic
generator in the `tools/regenerate_isbn_range_data.py` style. It reads the
maintained authority tables, computes the four generated modules, and writes
them (or, with `--check`, compares in memory and exits non-zero on drift).
The core logic, which must be implemented exactly:

```python
"""Regenerate SI Unit prefixed-unit data modules.

Computes the prefixed-unit set and the grammar token tables from the
maintained authority tables in paxman/capabilities/SIUnit/rules/data/.
Deterministic: same tables -> byte-identical output. Run after editing
any maintained SIUnit data module:

    uv run python tools/regenerate_si_prefix_data.py

--check regenerates in memory and exits non-zero if any generated file
differs (used by tests/capabilities/si_unit/test_data.py). Mirrors
tools/regenerate_isbn_range_data.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import NONSI_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_prefixes import (
    PREFIX_NAMES,
    PREFIX_SYMBOLS,
)
from paxman.capabilities.SIUnit.rules.data.unit_names import NAME_TO_SYMBOL

ROOT = Path(__file__).resolve().parents[1]
RULES_DATA = ROOT / "paxman" / "capabilities" / "SIUnit" / "rules" / "data"
GRAMMAR_DATA = ROOT / "paxman" / "capabilities" / "SIUnit" / "grammar" / "data"

# BIPM SI Brochure §3.2 + Table 8 footnote: prefixes are NOT used with
# min/h/d/° ′ ″, °C, or ha; the gram ("g") is the prefix attachment point.
_PREFIXABLE_NONSI = frozenset({"L", "t", "Da", "eV", "u", "Å", "b", "bar"})
_NO_PREFIX = frozenset({"min", "h", "d", "°", "′", "″", "°C", "ha"})


def _prefixable_units() -> frozenset[str]:
    # BIPM §3.2 (D9): prefixes attach to the gram ("g"), not to the
    # kilogram — exclude "kg" so "kkg"/"Mkg"/"µkg" are never generated.
    return (
        (BASE_UNIT_SYMBOLS - {"kg"}) | DERIVED_UNIT_SYMBOLS | _PREFIXABLE_NONSI
    ) - _NO_PREFIX


def _official_symbols() -> frozenset[str]:
    return BASE_UNIT_SYMBOLS | DERIVED_UNIT_SYMBOLS | NONSI_UNIT_SYMBOLS


def _prefixed_symbols() -> frozenset[str]:
    """Prefix + prefixable unit, excluding official-symbol collisions."""
    official = _official_symbols()
    return frozenset(
        prefix + unit
        for prefix in PREFIX_SYMBOLS
        for unit in _prefixable_units()
        if prefix + unit not in official
    )


def _longest_first(tokens: set[str]) -> tuple[str, ...]:
    return tuple(sorted(tokens, key=lambda t: (-len(t), t)))


def _symbol_tokens() -> tuple[str, ...]:
    return _longest_first(_official_symbols() | PREFIX_SYMBOLS | _prefixed_symbols())


def _prefixed_name_to_symbol() -> dict[str, str]:
    """Prefixed name -> prefixed symbol, excluding official-name collisions.

    BIPM §3.2 (D9): prefix name + unit name ("mega" + "hertz") maps to the
    prefixed symbol ("MHz"). "kilogram" is never regenerated as kilo+gram —
    official names win (D8).
    """
    official = frozenset(NAME_TO_SYMBOL)
    # Last-write-wins by dict order: if two names share a symbol (e.g.
    # "litre"/"liter" -> "L"), the maintained table's later entry wins.
    # Both spellings resolve to the same symbol, so the collision is
    # harmless for symbol generation — keep the maintained order stable.
    symbol_to_name = {v: k for k, v in NAME_TO_SYMBOL.items()}
    result: dict[str, str] = {}
    for prefix_symbol, prefix_name in PREFIX_NAMES.items():
        for unit_symbol in _prefixable_units():
            unit_name = symbol_to_name.get(unit_symbol)
            if unit_name is None:
                continue
            name = prefix_name + unit_name
            symbol = prefix_symbol + unit_symbol
            if name not in official and symbol in _prefixed_symbols():
                result[name] = symbol
    return result


def _name_tokens() -> tuple[str, ...]:
    return _longest_first(
        frozenset(NAME_TO_SYMBOL) | frozenset(_prefixed_name_to_symbol())
    )
```

Then the emitters (`_emit_prefixed_units()`, `_emit_prefixed_unit_names()`,
`_emit_symbol_tokens()`, `_emit_name_tokens()`, `_emit_compound_tokens()`)
build each module's text with a shared `_emit_module(docstring, assignment)`
helper, and `main()` writes the five files: `rules/data/prefixed_units.py`
(`PREFIXED_UNIT_SYMBOLS: frozenset[str]`), `rules/data/prefixed_unit_names.py`
(`PREFIXED_NAME_TO_SYMBOL: dict[str, str]`), `grammar/data/unit_symbol_tokens.py`
(`SYMBOL_TOKENS: tuple[str, ...]` — longest-first), `grammar/data/unit_name_tokens.py`
(`NAME_TOKENS: tuple[str, ...]` — longest-first), and
`grammar/data/compound_tokens.py` (`COMPOUND_SEPARATORS: str = "/·⋅"`,
`EXPONENT_CHARACTERS: str = "0-9⁻⁰¹²³⁴⁵⁶⁷⁸⁹\\-"`). Each generated file
carries the header `GENERATED by tools/regenerate_si_prefix_data.py — do not
edit by hand.` The compound rule in Task 6 keeps its own split patterns
locally (rules never import from `grammar/` — grammar↔rules purity scan).

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run python tools/regenerate_si_prefix_data.py --check`
**Commit:** `feat(si_unit): add prefixed-unit data generator`

### Task 5 — `feat(si_unit): add BIPM rule sections`

**Step 1 RED** — `tests/capabilities/si_unit/test_rules.py` (BIPM part):

```python
"""Tests for the BIPM SI Brochure rule sections."""

import pytest

from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.bipm_si_brochure_ed2019 import (
    SectionBaseUnits,
    SectionDerivedUnits,
    SectionNames,
    SectionNonSiUnits,
    SectionPrefixes,
)
from paxman.core.domain import RuleStrategy

CONTRACT = SIUnitContract()


@pytest.mark.capability
@pytest.mark.si_unit
class TestSectionBaseUnits:
    """BIPM Table 1 — base unit symbols."""

    def setup_method(self) -> None:
        self.rule = SectionBaseUnits()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 2.3.1-base-units"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"symbol_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2019

    @pytest.mark.parametrize("symbol", ["m", "kg", "s", "A", "K", "mol", "cd"])
    def test_matches(self, symbol: str) -> None:
        assert self.rule.matches(SIUnitNotation(text=symbol, shape="symbol"), CONTRACT)

    @pytest.mark.parametrize("text", ["Pa", "km", "pa", "m/s", "da"])
    def test_rejects(self, text: str) -> None:
        assert not self.rule.matches(
            SIUnitNotation(text=text, shape="symbol"), CONTRACT
        )

    def test_rejects_non_symbol_shape(self) -> None:
        assert not self.rule.matches(SIUnitNotation(text="kg", shape="name"), CONTRACT)

    def test_normalize_is_identity(self) -> None:
        assert (
            self.rule.normalize(SIUnitNotation(text="kg", shape="symbol"), CONTRACT)
            == "kg"
        )

    def test_temporal_gate(self) -> None:
        old = SIUnitContract(year=2018)
        assert not self.rule.matches(SIUnitNotation(text="kg", shape="symbol"), old)
        assert self.rule.matches(SIUnitNotation(text="kg", shape="symbol"), CONTRACT)


@pytest.mark.capability
@pytest.mark.si_unit
class TestSectionDerivedUnits:
    """BIPM Tables 3–4 — derived units with special names."""

    def setup_method(self) -> None:
        self.rule = SectionDerivedUnits()

    @pytest.mark.parametrize("text", ["rad", "Hz", "Pa", "Ω", "°C", "kat"])
    def test_matches(self, text: str) -> None:
        assert self.rule.matches(SIUnitNotation(text=text, shape="symbol"), CONTRACT)

    @pytest.mark.parametrize("text", ["m", "km", "pa", "Hzs"])
    def test_rejects(self, text: str) -> None:
        assert not self.rule.matches(
            SIUnitNotation(text=text, shape="symbol"), CONTRACT
        )

    def test_normalize_is_identity(self) -> None:
        assert (
            self.rule.normalize(SIUnitNotation(text="Pa", shape="symbol"), CONTRACT)
            == "Pa"
        )


@pytest.mark.capability
@pytest.mark.si_unit
class TestSectionNonSiUnits:
    """BIPM Tables 8–9 — non-SI units accepted for use with the SI."""

    def setup_method(self) -> None:
        self.rule = SectionNonSiUnits()

    @pytest.mark.parametrize(
        "text", ["min", "h", "d", "°", "ha", "L", "l", "t", "Da", "eV"]
    )
    def test_matches(self, text: str) -> None:
        assert self.rule.matches(SIUnitNotation(text=text, shape="symbol"), CONTRACT)

    def test_litre_canonicalization(self) -> None:
        assert (
            self.rule.normalize(SIUnitNotation(text="l", shape="symbol"), CONTRACT)
            == "L"
        )
        assert (
            self.rule.normalize(SIUnitNotation(text="L", shape="symbol"), CONTRACT)
            == "L"
        )

    def test_rejects(self) -> None:
        assert not self.rule.matches(SIUnitNotation(text="m", shape="symbol"), CONTRACT)
        assert not self.rule.matches(
            SIUnitNotation(text="kelvin", shape="name"), CONTRACT
        )


@pytest.mark.capability
@pytest.mark.si_unit
class TestSectionPrefixes:
    """BIPM Table 5 + §3.2 — prefixed unit symbols."""

    def setup_method(self) -> None:
        self.rule = SectionPrefixes()

    @pytest.mark.parametrize(
        "text", ["km", "MHz", "µg", "mg", "hPa", "keV", "kDa", "dam"]
    )
    def test_matches(self, text: str) -> None:
        assert self.rule.matches(SIUnitNotation(text=text, shape="symbol"), CONTRACT)

    @pytest.mark.parametrize("text", ["k", "da", "M", "µ", "m", "cd", "kg"])
    def test_bare_prefixes_and_official_do_not_match(self, text: str) -> None:
        assert not self.rule.matches(
            SIUnitNotation(text=text, shape="symbol"), CONTRACT
        )

    def test_normalize_is_identity(self) -> None:
        assert (
            self.rule.normalize(SIUnitNotation(text="MHz", shape="symbol"), CONTRACT)
            == "MHz"
        )


@pytest.mark.capability
@pytest.mark.si_unit
class TestSectionNames:
    """BIPM Tables 1, 3–4, 8–9 — unit names resolve to canonical symbols."""

    def setup_method(self) -> None:
        self.rule = SectionNames()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section-names"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"name_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2019

    @pytest.mark.parametrize(
        ("name", "symbol"),
        [
            ("kilogram", "kg"),
            ("kelvin", "K"),
            ("megahertz", "MHz"),  # generated prefixed name
            ("kilometre", "km"),  # generated prefixed name
            ("microgram", "µg"),  # generated prefixed name
            ("degree celsius", "°C"),
            ("litre", "L"),
        ],
    )
    def test_matches_and_normalize(self, name: str, symbol: str) -> None:
        notation = SIUnitNotation(text=name, shape="name")
        assert self.rule.matches(notation, CONTRACT)
        assert self.rule.normalize(notation, CONTRACT) == symbol

    @pytest.mark.parametrize("text", ["quark", "kg", "megahert", "meter"])
    def test_rejects_unknown_names(self, text: str) -> None:
        assert not self.rule.matches(SIUnitNotation(text=text, shape="name"), CONTRACT)

    def test_rejects_non_name_shape(self) -> None:
        assert not self.rule.matches(
            SIUnitNotation(text="kg", shape="symbol"), CONTRACT
        )
        assert not self.rule.matches(
            SIUnitNotation(text="m/s", shape="compound"), CONTRACT
        )

    def test_temporal_gate(self) -> None:
        old = SIUnitContract(year=2018)
        assert not self.rule.matches(SIUnitNotation(text="kelvin", shape="name"), old)
        assert self.rule.matches(SIUnitNotation(text="kelvin", shape="name"), CONTRACT)
```

**Step 2 GREEN** — `paxman/capabilities/SIUnit/rules/bipm_si_brochure_ed2019.py`:

**SEAM:** `Rule.__init_subclass__` enforces all six metadata attributes
(`name`, `strategy`, `provenance`, `citation`, `target_semantics`,
`requires_features` — the last two as non-empty `frozenset[str]`) at
class-definition time: a rule missing any of them fails the module import
with a `TypeError`. Every class below declares all six; `target_semantics`
names the producing grammar's `semantics` id (identity for SIUnit).

```python
"""BIPM SI Brochure rules (9th edition, 2019).

The SI Brochure defines the base units (Table 1), derived units with
special names (Tables 3–4), non-SI units accepted for use with the SI
(Tables 8–9), and the prefix symbols (Table 5). Each section validates
the corresponding symbol shape against its authority table. Syntax-only
recognition is the grammars' job; the rules resolve the canonical
symbol and provide provenance.
"""

from __future__ import annotations

from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.data.prefixed_unit_names import (
    PREFIXED_NAME_TO_SYMBOL,
)
from paxman.capabilities.SIUnit.rules.data.prefixed_units import PREFIXED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import (
    LITRE_WRITTEN_FORMS,
    NONSI_UNIT_SYMBOLS,
)
from paxman.capabilities.SIUnit.rules.data.unit_names import NAME_TO_SYMBOL
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

# Full name→symbol resolution: maintained official names + generated
# prefixed names (D8). No key overlap by construction (Task 4).
FULL_NAME_TO_SYMBOL = NAME_TO_SYMBOL | PREFIXED_NAME_TO_SYMBOL

PUBLICATION = Provenance(
    authority="BIPM",
    specification_name="SI Brochure: The International System of Units (SI)",
    kind="specification",
    reference_url="https://www.bipm.org/en/publications/si-brochure",
    version="9th edition",
    lifecycle="active",
    publication_year=2019,
)


class SectionBaseUnits(Rule[SIUnitNotation]):
    """SI Brochure Table 1 — base unit symbols."""

    name = "Section 2.3.1-base-units"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Table 1"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a base-unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in BASE_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical base-unit symbol."""
        return notation.text


class SectionDerivedUnits(Rule[SIUnitNotation]):
    """SI Brochure Tables 3–4 — derived units with special names."""

    name = "Section 2.3.2-derived-units"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Tables 3–4"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a derived-unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in DERIVED_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical derived-unit symbol."""
        return notation.text


class SectionNonSiUnits(Rule[SIUnitNotation]):
    """SI Brochure Tables 8–9 — non-SI units accepted for use with the SI.

    "l" (litre) canonicalizes to "L" (D3). "′" and "″" are recognized
    but normalize to themselves.
    """

    name = "Section 4.1-non-si-units"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Tables 8–9"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a non-SI unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in NONSI_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical symbol ("l" -> "L")."""
        if notation.text in LITRE_WRITTEN_FORMS:
            return "L"
        return notation.text


class SectionPrefixes(Rule[SIUnitNotation]):
    """SI Brochure Table 5 + §3.2 — prefixed unit symbols.

    A prefixed symbol ("km", "MHz", "µg") is a valid unit: prefix symbol
    concatenated with a prefixable unit symbol, generated from the
    maintained tables (Task 4). A bare prefix symbol ("k", "da") is not
    a unit and never matches — it stays INVALID (recognized, unresolved).
    """

    name = "Section 3.2-prefixes"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Table 5 and §3.2"
    target_semantics = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a prefixed unit symbol."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "symbol":
            return False
        return notation.text in PREFIXED_UNIT_SYMBOLS

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical prefixed symbol."""
        return notation.text


class SectionNames(Rule[SIUnitNotation]):
    """SI Brochure Tables 1, 3–4, 8–9 — unit names resolve to symbols.

    The name grammar case-folds (D4), so this lookup is exact. The table is
    FULL_NAME_TO_SYMBOL (maintained official names + generated prefixed
    names, D8): "megahertz" -> "MHz", "kilometre" -> "km", "microgram" -> "µg".
    """

    name = "Section-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "BIPM SI Brochure (9th ed., 2019), Tables 1, 3–4, 8–9 (unit names)"
    target_semantics = frozenset({"name_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a known unit name."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "name":
            return False
        return notation.text in FULL_NAME_TO_SYMBOL

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical unit symbol."""
        return FULL_NAME_TO_SYMBOL[notation.text]
```

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `feat(si_unit): add BIPM rule sections`

---

### Task 6 — `feat(si_unit): add ISO 80000-1 compound rule`

**Step 1 RED** — extend `tests/capabilities/si_unit/test_rules.py`:

```python
"""Tests for the ISO 80000-1 compound rule."""

import pytest

from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.iso_80000_ed2022 import SectionCompounds
from paxman.core.domain import RuleStrategy

CONTRACT = SIUnitContract()


@pytest.mark.capability
@pytest.mark.si_unit
class TestSectionCompounds:
    """ISO 80000-1:2022 §6.5 — product and quotient unit compounds."""

    def setup_method(self) -> None:
        self.rule = SectionCompounds()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 6.5-compounds"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"compound_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2022

    @pytest.mark.parametrize(
        "text",
        [
            "m/s²",
            "m/s2",
            "km/h",
            "N·m",
            "N⋅m",
            "kg·m/s²",
            "g/cm³",
            "m·s⁻²",
            "µg/mL",
            "m/°C",
        ],
    )
    def test_matches(self, text: str) -> None:
        assert self.rule.matches(SIUnitNotation(text=text, shape="compound"), CONTRACT)

    @pytest.mark.parametrize("text", ["QQQ/zzz", "m/", "/s", "m s", "m/2", "/"])
    def test_rejects(self, text: str) -> None:
        assert not self.rule.matches(
            SIUnitNotation(text=text, shape="compound"), CONTRACT
        )

    def test_rejects_non_compound_shape(self) -> None:
        assert not self.rule.matches(
            SIUnitNotation(text="m/s", shape="symbol"), CONTRACT
        )

    @pytest.mark.parametrize(
        ("text", "canonical"),
        [
            ("m/s²", "m/s2"),
            ("m/s2", "m/s2"),
            ("N·m", "N·m"),
            ("N⋅m", "N·m"),
            ("kg·m/s²", "kg·m/s2"),
            ("g/cm³", "g/cm3"),
            ("m·s⁻²", "m·s-2"),
            ("l/s", "L/s"),
            ("µm/s", "µm/s"),
        ],
    )
    def test_normalize(self, text: str, canonical: str) -> None:
        result = self.rule.normalize(
            SIUnitNotation(text=text, shape="compound"), CONTRACT
        )
        assert result == canonical

    def test_temporal_gate(self) -> None:
        old = SIUnitContract(year=2021)
        assert not self.rule.matches(SIUnitNotation(text="m/s", shape="compound"), old)
        assert self.rule.matches(SIUnitNotation(text="m/s", shape="compound"), CONTRACT)
```

**Step 2 GREEN** — `paxman/capabilities/SIUnit/rules/iso_80000_ed2022.py`:

```python
"""ISO 80000-1 compound unit rule (edition 2022).

ISO 80000-1 §6.5 defines how unit symbols combine into product and
quotient compounds: "N·m", "m/s", "kg·m/s²". This rule validates the
compound shape against the full SI symbol lexicon (official + prefixed)
and renders the canonical ASCII-exponent form: superscripts translate
to ASCII digits, "⋅"/"·" normalize to "·", "/" stays "/", "l" -> "L".
The split patterns are kept local (not imported from grammar/data) so
rules never import from the grammar tree (grammar↔rules purity scan).
"""

from __future__ import annotations

import re

from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.data.prefixed_units import PREFIXED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import NONSI_UNIT_SYMBOLS
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 80000-1:2022 Quantities and units — Part 1: General",
    kind="specification",
    reference_url="https://www.iso.org/standard/76921.html",
    version="2022",
    lifecycle="active",
    publication_year=2022,
)

_FULL_SYMBOL_LEXICON = (
    BASE_UNIT_SYMBOLS
    | DERIVED_UNIT_SYMBOLS
    | NONSI_UNIT_SYMBOLS
    | PREFIXED_UNIT_SYMBOLS
)
_EXPONENT_SUFFIX = re.compile(r"[0-9⁻⁰¹²³⁴⁵⁶⁷⁸⁹\-]*$")
_SUPERSCRIPT_TRANSLATE = str.maketrans(
    {
        "⁰": "0",
        "¹": "1",
        "²": "2",
        "³": "3",
        "⁴": "4",
        "⁵": "5",
        "⁶": "6",
        "⁷": "7",
        "⁸": "8",
        "⁹": "9",
        "⁻": "-",
    }
)
_SEPARATOR_TRANSLATE = str.maketrans({"⋅": "·"})  # D3: U+22C5 dot → U+00B7


class SectionCompounds(Rule[SIUnitNotation]):
    """ISO 80000-1 §6.5 — product and quotient unit compounds.

    Accepts compounds of the shape UNIT (separator UNIT){1,3} where each
    UNIT is a known symbol plus an optional exponent ("m/s²", "N·m",
    "kg·m/s²", "g/cm³"). "l" canonicalizes to "L" inside compounds.
    """

    name = "Section 6.5-compounds"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "ISO 80000-1:2022, §6.5 (unit symbols in products and quotients)"
    target_semantics = frozenset({"compound_recognition"})
    requires_features = frozenset()

    def matches(self, notation: SIUnitNotation, contract: Contract) -> bool:
        """Check if the notation is a valid SI compound."""
        if (
            contract.year is not None
            and contract.year < self.provenance.publication_year
        ):
            return False
        if notation.shape != "compound":
            return False
        return all(
            self._symbol_part(group) in _FULL_SYMBOL_LEXICON
            for group in re.split(r"[/·⋅]", notation.text)
        )

    def normalize(self, notation: SIUnitNotation, contract: Contract) -> str:
        """Normalize to the canonical compound: ASCII exponents, "·" separators."""
        return "".join(
            part if part in ("/", "·", "⋅") else self._canonical_group(part)
            for part in re.split(r"([/·⋅])", notation.text)
        ).translate(_SEPARATOR_TRANSLATE)

    @staticmethod
    def _symbol_part(group: str) -> str:
        """The symbol without its trailing exponent ("m/s2" -> "m/s2" group "m")."""
        return _EXPONENT_SUFFIX.sub("", group)

    @classmethod
    def _canonical_group(cls, group: str) -> str:
        """Canonical group: ASCII exponent, "l" -> "L", symbol unchanged."""
        match = _EXPONENT_SUFFIX.search(group)
        if match is None:
            return group
        symbol = group[: match.start()]
        exponent = group[match.start() :].translate(_SUPERSCRIPT_TRANSLATE)
        canonical_symbol = "L" if symbol == "l" else symbol
        return canonical_symbol + exponent
```

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `feat(si_unit): add ISO 80000-1 compound rule`

### Task 7 — `feat(si_unit): add recognition grammars`

**Step 1 RED** — `tests/capabilities/si_unit/test_grammar.py` (all three
grammars, driven directly with no rules):

```python
"""Tests for SIUnit recognition grammars.

Grammars are exercised directly (no rules): each test drives
Grammar.recognize() against raw text and asserts the emitted spans —
half-open [start, end) offsets, raw_text, and the SIUnitNotation
text/shape — mirroring Currency's grammar test structure.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.SIUnit.grammar.compound_recognition import CompoundRecognition
from paxman.capabilities.SIUnit.grammar.name_recognition import NameRecognition
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.domain import Grammar, RecognitionMatch

pytestmark = [pytest.mark.capability, pytest.mark.si_unit]

# Expected-span tuple: (raw_text, start, end, notation_text, shape).
Span = tuple[str, int, int, str, str]


def _assert_span_invariants(text: str, match: RecognitionMatch[SIUnitNotation]) -> None:
    """Verify the RecognitionMatch span contract (half-open [start, end))."""
    assert 0 <= match.start <= match.end
    assert len(match.raw_text) == match.end - match.start
    assert match.raw_text == text[match.start : match.end]


def _assert_spans(
    text: str,
    expected: list[Span],
    results: list[RecognitionMatch[SIUnitNotation]],
) -> None:
    """Compare results against (raw_text, start, end, text, shape) tuples."""
    assert len(results) == len(expected)
    for match, (raw_text, start, end, notation_text, shape) in zip(
        results, expected, strict=True
    ):
        _assert_span_invariants(text, match)
        assert match.start == start
        assert match.end == end
        assert match.raw_text == raw_text
        assert match.notation.text == notation_text
        assert match.notation.shape == shape


class TestSymbolRecognition:
    """Grammar: symbol_recognition — case-exact unit symbol tokens."""

    def setup_method(self) -> None:
        self.grammar: Grammar[SIUnitNotation] = SymbolRecognition()

    def test_semantics_identity(self) -> None:
        # SEAM (ADR-0003): every shipped grammar declares `semantics`;
        # SIUnit grammars use identity ids (no coalesced groups).
        assert self.grammar.semantics == "symbol_recognition"

    @pytest.mark.parametrize(
        ("text", "token"),
        [
            ("m", "m"),
            ("kg", "kg"),
            ("MHz", "MHz"),
            ("Pa", "Pa"),
            ("cd", "cd"),
            ("°C", "°C"),
            ("µg", "µg"),
            ("min", "min"),
            ("da", "da"),  # bare prefix is recognized (the rule rejects -> INVALID)
            ("k", "k"),
        ],
    )
    def test_recognizes(self, text: str, token: str) -> None:
        results = self.grammar.recognize(text)
        assert len(results) == 1
        match = results[0]
        assert match.notation.text == token
        assert match.notation.shape == "symbol"
        assert match.start == 0
        assert match.end == len(text)
        assert match.raw_text == text

    @pytest.mark.parametrize(
        "text",
        ["pa", "Kg", "KHz", "metre", "m/s²", "N·m", "xkg", "kg5", "2m", "25°C", "5kg"],
    )
    def test_rejects(self, text: str) -> None:
        assert self.grammar.recognize(text) == []

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("m s", [("m", 0, 1, "m", "symbol"), ("s", 2, 3, "s", "symbol")]),
            ("m; s", [("m", 0, 1, "m", "symbol"), ("s", 3, 4, "s", "symbol")]),
        ],
    )
    def test_multiple_spans(self, text: str, expected: list[Span]) -> None:
        _assert_spans(text, expected, self.grammar.recognize(text))


class TestNameRecognition:
    """Grammar: name_recognition — case-folded unit names."""

    def setup_method(self) -> None:
        self.grammar: Grammar[SIUnitNotation] = NameRecognition()

    def test_semantics_identity(self) -> None:
        # SEAM (ADR-0003): identity semantics id; no coalesced groups.
        assert self.grammar.semantics == "name_recognition"

    @pytest.mark.parametrize(
        ("text", "name"),
        [
            ("kilogram", "kilogram"),
            ("Kilogram", "kilogram"),
            ("KILOGRAM", "kilogram"),
            ("kelvin", "kelvin"),
            ("degree celsius", "degree celsius"),
            ("Degree Celsius", "degree celsius"),
            ("megahertz", "megahertz"),
            ("kilometre", "kilometre"),
        ],
    )
    def test_recognizes(self, text: str, name: str) -> None:
        results = self.grammar.recognize(text)
        assert len(results) == 1
        match = results[0]
        assert match.notation.text == name
        assert match.notation.shape == "name"
        assert match.start == 0
        assert match.end == len(text)

    @pytest.mark.parametrize(
        "text", ["kilograms", "kilogran", "kg", "kelvins", "xkelvin", "kelvinx"]
    )
    def test_rejects(self, text: str) -> None:
        assert self.grammar.recognize(text) == []

    def test_multiple_spans(self) -> None:
        _assert_spans(
            "kelvin pascal",
            [("kelvin", 0, 6, "kelvin", "name"), ("pascal", 7, 13, "pascal", "name")],
            self.grammar.recognize("kelvin pascal"),
        )


class TestCompoundRecognition:
    """Grammar: compound_recognition — product/quotient unit shapes."""

    def setup_method(self) -> None:
        self.grammar: Grammar[SIUnitNotation] = CompoundRecognition()

    def test_semantics_identity(self) -> None:
        # SEAM (ADR-0003): identity semantics id; no coalesced groups.
        assert self.grammar.semantics == "compound_recognition"

    @pytest.mark.parametrize(
        ("text", "body"),
        [
            ("m/s²", "m/s²"),
            ("m/s2", "m/s2"),
            ("km/h", "km/h"),
            ("N·m", "N·m"),
            ("N⋅m", "N⋅m"),
            ("kg·m/s²", "kg·m/s²"),
            ("g/cm³", "g/cm³"),
            ("m·s⁻²", "m·s⁻²"),
            ("m/°C", "m/°C"),
            ("µg/mL", "µg/mL"),
            ("QQQ/zzz", "QQQ/zzz"),  # shape-only: the rule rejects unknown groups
        ],
    )
    def test_recognizes(self, text: str, body: str) -> None:
        results = self.grammar.recognize(text)
        assert len(results) == 1
        match = results[0]
        assert match.notation.text == body
        assert match.notation.shape == "compound"
        assert match.start == 0
        assert match.end == len(text)

    @pytest.mark.parametrize("text", ["m", "m s", "m s²", "5m/s", "m/sx", "xN·m"])
    def test_rejects(self, text: str) -> None:
        assert self.grammar.recognize(text) == []
```

**Step 2 GREEN** — the three grammar modules:

`paxman/capabilities/SIUnit/grammar/symbol_recognition.py`:

```python
"""Symbol recognition grammar for SI Unit.

Recognizes unit symbols exactly as written (case-exact): base symbols
("m", "kg"), derived special-name symbols ("Pa", "°C"), non-SI symbols
("min", "L"), prefix symbols ("k", "M") and prefixed units ("km", "MHz").
Each recognition emits a span-bearing RecognitionMatch over the symbol
text. Recognition only: no validation, no canonicalization (D1/D2/D6).
"""

from __future__ import annotations

import re

from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Word chars, signs, and the compound separators block a token: they
# never merge into a symbol and never split a compound (D2).
_LOOKAROUND = r"(?<![\w\-+\u2212/·⋅])(?![\w\-+\u2212/·⋅])"
_ALTERNATION = "|".join(re.escape(t) for t in SYMBOL_TOKENS)
_TOKEN_RE = re.compile(_LOOKAROUND + r"(?P<token>" + _ALTERNATION + r")" + _LOOKAROUND)


class SymbolRecognition(Grammar[SIUnitNotation]):
    """Grammar: symbol_recognition — case-exact unit symbol tokens."""

    name = "symbol_recognition"
    semantics = "symbol_recognition"  # SEAM (ADR-0003): identity id

    def recognize(self, text: str) -> list[RecognitionMatch[SIUnitNotation]]:
        """Emit one RecognitionMatch per symbol token found in text."""
        return [
            RecognitionMatch(
                raw_text=text[m.start() : m.end()],
                start=m.start(),
                end=m.end(),
                notation=SIUnitNotation(text=m.group("token"), shape="symbol"),
            )
            for m in _TOKEN_RE.finditer(text)
        ]
```

`paxman/capabilities/SIUnit/grammar/name_recognition.py`:

```python
"""Name recognition grammar for SI Unit.

Recognizes unit names case-insensitively: the grammar folds the input
to lowercase and matches against the longest-first name token table
(D4). "Kilogram", "KILOGRAM", "kilogram" all emit a RecognitionMatch
over the span of the name text. Recognition only: no validation.
"""

from __future__ import annotations

import re

from paxman.capabilities.SIUnit.grammar.data.unit_name_tokens import NAME_TOKENS
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.domain import Grammar, RecognitionMatch

_LOOKAROUND = r"(?<![a-z])(?![a-z])"
_ALTERNATION = "|".join(re.escape(t) for t in NAME_TOKENS)
_NAME_RE = re.compile(
    _LOOKAROUND + r"(?P<name>" + _ALTERNATION + r")" + _LOOKAROUND, re.IGNORECASE
)


class NameRecognition(Grammar[SIUnitNotation]):
    """Grammar: name_recognition — case-folded unit names."""

    name = "name_recognition"
    semantics = "name_recognition"  # SEAM (ADR-0003): identity id

    def recognize(self, text: str) -> list[RecognitionMatch[SIUnitNotation]]:
        """Emit one RecognitionMatch per unit name found in text."""
        return [
            RecognitionMatch(
                raw_text=text[m.start() : m.end()],
                start=m.start(),
                end=m.end(),
                notation=SIUnitNotation(text=m.group("name").lower(), shape="name"),
            )
            for m in _NAME_RE.finditer(text)
        ]
```

`paxman/capabilities/SIUnit/grammar/compound_recognition.py`:

```python
"""Compound recognition grammar for SI Unit.

Recognizes product/quotient compound shapes over unit symbols: UNIT
(separator UNIT){1,3} where each UNIT is a symbol character run with an
optional exponent, and the separator is "/", "·" or "⋅" (D3). The
grammar is shape-only: it does not validate that the units are known
(the ISO 80000-1 rule does that). "m/s²", "N·m", "kg·m/s²", "g/cm³"
are recognized as single spans; "m s" (space) is not a compound.
"""

from __future__ import annotations

import re

from paxman.capabilities.SIUnit.grammar.data.compound_tokens import (
    COMPOUND_SEPARATORS,
    EXPONENT_CHARACTERS,
)
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Shape constants come from the Task 4 generated module (grammars may import
# from grammar/data/ — only rules are barred by the grammar↔rules purity
# scan). Keeps the separator/exponent characters in one place.
_EXPONENT = rf"[{EXPONENT_CHARACTERS}]*"
_UNIT = rf"(?:°?[A-Za-zµΩÅ][A-Za-zµΩÅ0-9]*{_EXPONENT})"
_SEP = f"[{COMPOUND_SEPARATORS}]"
_COMPOUND_RE = re.compile(
    rf"(?<![\w\-+\u2212])(?P<body>{_UNIT}(?:{_SEP}{_UNIT}){{1,3}})(?![\w\-+\u2212])"
)


class CompoundRecognition(Grammar[SIUnitNotation]):
    """Grammar: compound_recognition — product/quotient unit shapes."""

    name = "compound_recognition"
    semantics = "compound_recognition"  # SEAM (ADR-0003): identity id

    def recognize(self, text: str) -> list[RecognitionMatch[SIUnitNotation]]:
        """Emit one RecognitionMatch per compound shape found in text."""
        return [
            RecognitionMatch(
                raw_text=text[m.start() : m.end()],
                start=m.start(),
                end=m.end(),
                notation=SIUnitNotation(text=m.group("body"), shape="compound"),
            )
            for m in _COMPOUND_RE.finditer(text)
        ]
```

All three grammars emit only span-bearing `RecognitionMatch` (never bare
notation), never validate, never dedup, never order (house rule: the
engine's `_dedup_spans` handles overlap).

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `feat(si_unit): add recognition grammars`

### Task 8 — `test(si_unit): add cross-layer data-consistency tests`

**Step 1 RED** — `tests/capabilities/si_unit/test_data_consistency.py` (the
house-mandate file, mirroring Currency's `test_data_consistency.py`): every
recognition key shipped by `grammar/data/` must resolve through the
authority tables in `rules/data/`, and every authority symbol must be
reachable from the token tables. Written first; RED until Tasks 3–7 land:

```python
"""Cross-layer data-consistency tests for the SI Unit capability.

House mandate (Currency precedent): every recognition key shipped by the
grammar/data token tables must resolve through the rules/data authority
tables, and every authority symbol must be reachable from the token
tables. Grammar<->rule key agreement is asserted here, not per-file.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.SIUnit.grammar.data.unit_name_tokens import NAME_TOKENS
from paxman.capabilities.SIUnit.grammar.data.unit_symbol_tokens import SYMBOL_TOKENS
from paxman.capabilities.SIUnit.rules.data.prefixed_unit_names import (
    PREFIXED_NAME_TO_SYMBOL,
)
from paxman.capabilities.SIUnit.rules.data.prefixed_units import PREFIXED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_base_units import BASE_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_derived_units import DERIVED_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_nonsi_units import NONSI_UNIT_SYMBOLS
from paxman.capabilities.SIUnit.rules.data.si_prefixes import (
    PREFIX_NAMES,
    PREFIX_SYMBOLS,
)
from paxman.capabilities.SIUnit.rules.data.unit_names import NAME_TO_SYMBOL

pytestmark = [pytest.mark.capability, pytest.mark.si_unit]

OFFICIAL_SYMBOLS = BASE_UNIT_SYMBOLS | DERIVED_UNIT_SYMBOLS | NONSI_UNIT_SYMBOLS
FULL_NAME_TO_SYMBOL = NAME_TO_SYMBOL | PREFIXED_NAME_TO_SYMBOL


class TestSymbolCoverage:
    """Every grammar symbol token is an authority symbol, and vice versa."""

    def test_token_set_equals_authority_symbols(self) -> None:
        assert (
            set(SYMBOL_TOKENS)
            == OFFICIAL_SYMBOLS | PREFIX_SYMBOLS | PREFIXED_UNIT_SYMBOLS
        )

    def test_generated_symbols_disjoint_from_official(self) -> None:
        assert PREFIXED_UNIT_SYMBOLS.isdisjoint(OFFICIAL_SYMBOLS)

    def test_kg_not_prefixable(self) -> None:
        # D9: prefixes attach to the gram, never to the kilogram.
        assert "kg" not in PREFIXED_UNIT_SYMBOLS
        assert "g" in OFFICIAL_SYMBOLS


class TestNameCoverage:
    """Every grammar name token resolves; every resolvable name is a token."""

    def test_name_tokens_equal_full_name_map(self) -> None:
        assert set(NAME_TOKENS) == set(FULL_NAME_TO_SYMBOL)

    def test_names_resolve_to_known_symbols(self) -> None:
        assert (
            set(FULL_NAME_TO_SYMBOL.values())
            <= OFFICIAL_SYMBOLS | PREFIXED_UNIT_SYMBOLS
        )

    def test_prefixed_names_disjoint_from_official_names(self) -> None:
        assert set(PREFIXED_NAME_TO_SYMBOL).isdisjoint(NAME_TO_SYMBOL)

    def test_no_kilogram_stacking(self) -> None:
        assert not any(n.endswith("kilogram") for n in PREFIXED_NAME_TO_SYMBOL)


class TestDecompositionInvariants:
    """Generated prefixed symbols/names decompose into known parts."""

    def test_gram_is_the_prefix_attachment_point(self) -> None:
        # D9: "microgram" -> "µg" is reachable only via name "gram" -> "g".
        assert NAME_TO_SYMBOL["gram"] == "g"

    def test_prefixed_symbols_decompose(self) -> None:
        prefixes = sorted(PREFIX_SYMBOLS, key=lambda p: (-len(p), p))
        for symbol in PREFIXED_UNIT_SYMBOLS:
            for prefix in prefixes:
                if symbol.startswith(prefix):
                    unit = symbol[len(prefix) :]
                    assert unit in OFFICIAL_SYMBOLS
                    assert unit != "kg"  # D9
                    break
            else:
                pytest.fail(f"{symbol!r} does not start with any prefix symbol")

    def test_prefixed_names_decompose(self) -> None:
        prefix_names = sorted(set(PREFIX_NAMES.values()), key=lambda n: (-len(n), n))
        for name, symbol in PREFIXED_NAME_TO_SYMBOL.items():
            for prefix_name in prefix_names:
                if name.startswith(prefix_name):
                    unit_name = name[len(prefix_name) :]
                    assert unit_name in NAME_TO_SYMBOL
                    assert NAME_TO_SYMBOL[unit_name] in OFFICIAL_SYMBOLS
                    break
            else:
                pytest.fail(f"{name!r} does not start with any prefix name")
            assert symbol in PREFIXED_UNIT_SYMBOLS


class TestTokenShapeInvariants:
    """Symbol tokens are bare; name tokens are lowercase (grammar folds)."""

    def test_no_whitespace_in_symbol_tokens(self) -> None:
        assert all(" " not in t for t in SYMBOL_TOKENS)

    def test_name_tokens_lowercase(self) -> None:
        assert all(t == t.lower() for t in NAME_TOKENS)

    def test_no_empty_tokens(self) -> None:
        assert all(SYMBOL_TOKENS)
        assert all(NAME_TOKENS)
```

**Step 2 GREEN** — no new source: Tasks 3–7 already produce the data; this
task locks their agreement at the grammar/rule seam. If a decomposition
assertion fails, the generator or a maintained table is wrong — fix the
data (rerun `tools/regenerate_si_prefix_data.py`), never loosen the test.

**Verify:** `uv run pytest tests/capabilities/si_unit -v` and
`uv run ruff check paxman/capabilities/SIUnit/ tests/capabilities/si_unit/`
**Commit:** `test(si_unit): add cross-layer data-consistency tests`

---

### Task 9 — `feat(si_unit): wire SIUnitCapability with create_contract`

**Step 1 RED** — `tests/capabilities/si_unit/test_capability.py` (mirror
`tests/capabilities/currency/test_capability.py`): class-level
`@pytest.mark.capability` / `@pytest.mark.si_unit` markers; imports from
`paxman.capabilities.SIUnit.capability` / `.contract` / `.notation`:

```python
"""Tests for the SIUnit capability wiring."""

import pytest

from paxman.capabilities.SIUnit.capability import SIUnitCapability
from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.notation import SIUnitNotation


@pytest.mark.capability
@pytest.mark.si_unit
class TestSIUnitCapability:
    """Capability wiring — grammars, rules, factory, exports."""

    def setup_method(self) -> None:
        self.capability = SIUnitCapability()

    def test_metadata(self) -> None:
        # name == "si_unit"; version == "1.0.0"
        assert self.capability.name == "si_unit"
        assert self.capability.version == "1.0.0"

    def test_get_grammars(self) -> None:
        # 3 instances with names {symbol_recognition, name_recognition,
        # compound_recognition}
        names = {g.name for g in self.capability.get_grammars()}
        assert names == {
            "symbol_recognition",
            "name_recognition",
            "compound_recognition",
        }

    def test_get_rules(self) -> None:
        # 6 instances: 5 BIPM sections + 1 ISO compound section
        names = {r.name for r in self.capability.get_rules()}
        assert names == {
            "Section 2.3.1-base-units",
            "Section 2.3.2-derived-units",
            "Section 4.1-non-si-units",
            "Section 3.2-prefixes",
            "Section-names",
            "Section 6.5-compounds",
        }

    def test_create_contract_defaults(self) -> None:
        # create_contract() returns SIUnitContract with defaults
        contract = self.capability.create_contract()
        assert isinstance(contract, SIUnitContract)
        assert contract.excluded_rules == ()
        assert contract.pinned_rules is None
        assert contract.output_format == "symbol"  # DEFAULT_OUTPUT_FORMAT

    def test_create_contract_excluded_rules(self) -> None:
        contract = self.capability.create_contract(excluded_rules=["Section-names"])
        assert contract.excluded_rules == ("Section-names",)

    def test_create_contract_extra_grammars(self) -> None:
        # SEAM: the community opt-in field is forwarded by the factory
        # (surface guard: default () + forwarding through create_contract).
        contract = self.capability.create_contract(
            extra_grammars=["dot_unit_recognition"]
        )
        assert contract.extra_grammars == ("dot_unit_recognition",)
        assert self.capability.create_contract().extra_grammars == ()

    def test_create_contract_keyword_only(self) -> None:
        # ContractFactory conformance: the common block is keyword-only
        with pytest.raises(TypeError):
            self.capability.create_contract("Section-names")  # type: ignore[call-arg]

    def test_format_value_identity(self) -> None:
        # offered formats are empty -> base identity is the contract
        notation = SIUnitNotation(text="kg", shape="symbol")
        assert self.capability.format_value("kg", "symbol", notation) == "kg"


def test_package_exports() -> None:
    # __all__ exports SIUnitCapability, SIUnitContract, SIUnitNotation
    from paxman.capabilities.SIUnit import (
        SIUnitCapability as CapabilityExport,
        SIUnitContract as ContractExport,
        SIUnitNotation as NotationExport,
    )

    assert CapabilityExport is SIUnitCapability
    assert ContractExport is SIUnitContract
    assert NotationExport is SIUnitNotation
```

**Step 2:** verify fail (no `capability.py` yet).

**Step 3 GREEN** — `paxman/capabilities/SIUnit/capability.py`:

```python
"""SI Unit capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.grammar.compound_recognition import CompoundRecognition
from paxman.capabilities.SIUnit.grammar.name_recognition import NameRecognition
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.SIUnit.notation import SIUnitNotation
from paxman.capabilities.SIUnit.rules.bipm_si_brochure_ed2019 import (
    SectionBaseUnits,
    SectionDerivedUnits,
    SectionNames,
    SectionNonSiUnits,
    SectionPrefixes,
)
from paxman.capabilities.SIUnit.rules.iso_80000_ed2022 import SectionCompounds
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["SIUnitCapability", "SIUnitContract", "SIUnitNotation"]


class SIUnitCapability(Capability[SIUnitNotation]):
    """SI unit canonicalization capability.

    Canonicalizes SI unit expressions — a unit symbol, a unit name, or a
    product/quotient compound — to the canonical symbol form, with full
    provenance.     Identity-only: no quantities, no magnitudes, no
    name-compounds ("metre per second" does not resolve as a compound —
    its words are recognized separately, yielding AMBIGUOUS; "25°C" is
    MISSING). Strategy: BIPM SI Brochure (9th ed., 2019) + ISO 80000-1.
    """

    name = "si_unit"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[SIUnitNotation]]:
        """Return all grammar instances.

        Returns:
            List of 3 grammars: symbol, name, compound.
        """
        return [SymbolRecognition(), NameRecognition(), CompoundRecognition()]

    def get_rules(self) -> list[Rule[SIUnitNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 6 rules: 5 BIPM sections (base, derived, non-SI,
            prefixes, names) and 1 ISO 80000-1 compound section.
        """
        return [
            SectionBaseUnits(),
            SectionDerivedUnits(),
            SectionNonSiUnits(),
            SectionPrefixes(),
            SectionNames(),
            SectionCompounds(),
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> SIUnitContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"symbol" resolve to "symbol".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).

        Returns:
            Configured SIUnitContract instance.
        """
        return SIUnitContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    # format_value: NOT overridden — the canonical value IS the "symbol"
    # format, and there are no offered alternatives. The Capability base
    # provides the identity formatter.
```

Replace `SIUnit/__init__.py` with the final three-export form (Task 1's
placeholder):

```python
"""SI Unit capability package."""

from __future__ import annotations

from paxman.capabilities.SIUnit.capability import SIUnitCapability
from paxman.capabilities.SIUnit.contract import SIUnitContract
from paxman.capabilities.SIUnit.notation import SIUnitNotation

__all__ = ["SIUnitCapability", "SIUnitContract", "SIUnitNotation"]
```

**Step 4:** `uv run pytest tests/capabilities/si_unit -v` → pass; ruff +
pyright clean; `uv run import-linter lint` → clean (no cross-package
imports so far). Commit `feat(si_unit): wire SIUnitCapability with create_contract`.

---

### Task 10 — `feat(si_unit): register SIUnit capability and extend export/surface guards`

**Step 1 RED** — extend the existing guards first (each fails before the
registration lands):

- `tests/unit/test_capability_exports.py`: add a `TestSIUnitCapabilityExports`
  class (mirror `TestCurrencyCapabilityExports` — asserts
  `capabilities.SIUnit` imports and `name == "si_unit"`), and extend the
  count test (`test_export_list_contains_nine_names` →
  `test_export_list_contains_ten_names`) to **ten** names:
  `{"Country", "Currency", "Date", "Email", "IP", "ISBN", "Money",
  "Phone", "SIUnit", "URL"}`.
- `tests/unit/test_capability_surface.py`: add the SIUnit row to the
  `_CAPABILITY_SURFACES` parametrization —
  `pytest.param(SIUnitCapability, SIUnitContract, "symbol", id="si_unit")`
  (with imports from `paxman.capabilities.SIUnit.capability` /
  `.contract`) plus the `SIUnitNotation` import. The parametrized guard
  then enforces, for SIUnit, all five surface items: `CapabilityContract`
  inheritance, `ContractFactory` conformance, the keyword-only
  `create_contract` common block `excluded_rules, pinned_rules, year,
  output_format, extra_grammars` in that order, `output_format`
  resolving `None`/`"default"`/`"symbol"` to `"symbol"`, and
  `extra_grammars` defaulting to `()` on the contract while forwarding a
  provided value through `create_contract`. (The guard no longer asserts
  per-row `active_grammars` — the base `None` default is the convention
  for non-gated capabilities.)
- `tests/unit/test_grammar_semantics_metadata.py` (SEAM): add SIUnit to
  the hardcoded capability list. Its three grammars declare identity
  `semantics`, so the identity-or-allowlist check passes with **no**
  addition to `_COALESCED_SEMANTICS`.
- `tests/unit/test_grammar_semantics_consistency.py` (SEAM): add SIUnit
  to `_SHIPPED_CAPABILITIES`. No `_PROBE_ROWS` entry is needed — all
  three semantics are singletons (the probe table seeds only coalesced
  groups); `test_every_grammar_semantics_claimed_by_rule_target`
  auto-verifies that each of SIUnit's semantics ids is targeted by an
  in-capability rule (`symbol_recognition` → the four BIPM symbol
  sections, `name_recognition` → `SectionNames`, `compound_recognition`
  → `SectionCompounds`). The `name_recognition` id coinciding with
  Country's same-named id is fine — groups are scoped per capability
  (R3).

Both semantics guards import SIUnit through the `paxman.capabilities`
package, so their RED failure is the missing export — the same commit's
GREEN (registration) turns them green.

**Step 2:** `uv run pytest tests/unit -v` → the guards fail (no `SIUnit`
export yet).

**Step 3 GREEN** — `paxman/capabilities/__init__.py`:

```python
"""Paxman capabilities."""

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
```

The `si_unit` pytest marker is already registered (Task 1 Step 2) — nothing
to add to `pyproject.toml` markers here.

**Step 4:** `uv run ruff check paxman/ tests/` → clean; `uv run pytest
tests/unit -v` → pass (all four extended guards — exports, surface,
semantics metadata, semantics consistency — green with registration); `uv
run import-linter lint` → clean. Commit `feat(si_unit): register SIUnit capability and extend export/surface guards`.

---

### Task 11 — `test(si_unit): lock SIUnit pipeline semantics and determinism`

**Step 1 RED** — `tests/integration/test_si_unit_pipeline.py` mirroring
`tests/integration/test_currency_pipeline.py`: autouse `_clean_registry`
fixture calling `reset_registry()` before/after each test (registry hygiene
per `paxman/core/AGENTS.md`); class docstring locks the semantics;
`register_capability(SIUnitCapability())` per test; `from paxman.api import
canonicalize`. Run **every row of the §1 e2e contract** as a parametrized
case, plus:

```python
# status per row; canonicalized_value per SUCCESS row; Resolution.MISSING
#     for MISSING rows; no candidates for MISSING rows
# provenance: "Kilogram" SUCCESS row -> candidates[0].provenance[0]
#     .specification_name contains "SI Brochure" and authority == "BIPM";
#     "megahertz" row -> BIPM (prefix rule); "m/s²" row -> "ISO 80000-1"
# frozen registry: a second canonicalize() call after the first still
#     succeeds (registry freezes once, never re-registers)
# AMBIGUOUS row ("m s"): status is AMBIGUOUS, candidates carry both
#     "m" and "s" canonical values (engine preserves cross-grammar overlaps)
# INVALID rows ("da", "k", "QQQ/zzz"): recognized but no rule resolves
```

**Step 2:** verify fail (SIUnit not yet importable through the pipeline).

**Step 3 GREEN** — no new source needed (Tasks 3–9 already wired
everything); this task proves the full `canonicalize()` path (registry →
run_capability → grammar → rule → Resolution) and catches
integration regressions early (Traps §T13: the moment SIUnit joins the
registry, every existing integration test must still pass).

**Step 4** — canonical determinism (SEAM: the replay-hash baseline suite
was removed in PR #18 — `VersionStamp.replay_hash` no longer exists and
`tests/integration/test_default_replay_hashes.py` is gone; determinism is
now locked by the "run twice, byte-identical" convention in
`tests/integration/test_pipeline.py`'s
`TestCanonicalDeterminismAndCandidateOrder`). Add **one** SIUnit row to
that parametrized class, mirroring the existing rows exactly:

```python
(
    pytest.param(
        SIUnitCapability,
        lambda: SIUnitCapability.create_contract(),
        "megahertz",
        id="si_unit-prefixed-name",
    ),
)
```

The row registers SIUnit, runs `run_capability("megahertz", contract)`
twice, and asserts `second == first`, plus identical status /
`canonicalized_value` ("MHz") / candidate tuple. **No hash literal exists
to obtain** — determinism is asserted structurally, never by snapshot.

**Verify:** `uv run pytest tests/integration -v` → pass (all capabilities).
**Commit:** `test(si_unit): lock SIUnit pipeline semantics and determinism`

---

### Task 12 — `test(si_unit): add property invariants and e2e coverage`

**Step 1 RED** — `tests/property/test_si_unit_properties.py`
(`@pytest.mark.property` + `@given`; property tests drive grammars
directly and never touch the registry — the Money full-pipeline suite is
the documented exception):

```python
# given a symbol token t in SYMBOL_TOKENS (sample strategy):
#   SymbolRecognition().recognize(t) yields exactly one match whose
#   notation text == t and shape == "symbol"     # D6 case-exact invariant
# given a lowercase name n in NAME_TO_SYMBOL (sample strategy):
#   NameRecognition().recognize(n.title()).notation.text == n  # D4 fold
# given a prefixed name pn in PREFIXED_NAME_TO_SYMBOL (sample strategy):
#   NameRecognition().recognize(pn).notation.text == pn and
#   SectionNames().matches(notation, SIUnitContract()) is True
# given a compound text ct built from two known symbol tokens joined
#   by "/" (sample strategy):
#   CompoundRecognition().recognize(ct) yields exactly one match with
#   shape == "compound"
# given any recognized match m: m.end - m.start == len(m.raw_text)
#     and m.raw_text == text[m.start:m.end]       # half-open span invariant
```

> **Controller amendment (2026-08-12):** the compound invariant's sample
> strategy draws from the *compoundable* lexicon — the glyph-only plane-angle
> tokens `°` `′` `″` (BIPM Table 8, present in `SYMBOL_TOKENS`) are excluded
> with a documented module constant. Verified exhaustive: the compound
> grammar's `_UNIT` composes letter-based units (`[A-Za-zµΩÅ]`, `°?` prefix
> for `°C` only), and the 5571 failing pairs are exactly those containing a
> bare `°`/`′`/`″` — no §1 locked row requires a bare-glyph compound
> (`m/°C` composes via the `°C` token itself). Every remaining
> `SYMBOL_TOKENS` pair (exhaustive) composes exactly one compound match.

**Step 2 GREEN** — extend `tests/e2e/test_canonicalize.py` (autouse
`_clean_registry` fixture; `from paxman.api import canonicalize`), adding
the SIUnit e2e rows from the §1 contract (the Milestone trio `"Kilogram"`,
`"megahertz"`, `"m/s²"` first).

**Step 3:** verify + commit — `uv run pytest tests/property tests/e2e -v`
→ pass. Commit `test(si_unit): add property invariants and e2e coverage`.

---

### Task 13 — `docs(si_unit): document SIUnit capability and update capability counts`

**Step 1 RED (docs-as-spec)** — grep the repo for stale references:
`rg -n "nine|9 capabilities|nine built-in|eight built-in" README.md AGENTS.md CONTEXT.md docs/`
→ list every hit to update (no code test needed — the Task 10 surface
guards already enforce the 10-capability surface; this task is the
documentation mirror).

**Step 2 GREEN** — update:

- `README.md`: capabilities table — add the **SI Unit** row
  (`| **SI Unit** | SI unit expressions | 3 (symbol, name, compound) | 6 | BIPM SI Brochure, ISO 80000-1 |`)
  and the count line ("nine built-in" → "ten built-in"); add an **SI Unit
  Capability** section after the URL section with the Milestone trio +
  identity-only note (mirror the Currency section's style). No
  capability-specific parameters exist — do **not** add an SI Unit row to
  the Capability-Specific Parameters table.
- `AGENTS.md` (root): "9 capabilities" → "10 capabilities" in the
  Overview; capability-count mentions anywhere else found by the grep;
  the NOTES section's "A 10th — SI Unit … is in development on
  `feature/si-unit-capability`" line becomes shipped (drop the
  "in development" framing).
- `paxman/capabilities/AGENTS.md`: "9 capability packages" → "10
  capability packages"; add SIUnit to the package list.
- `paxman/capabilities/__init__.py` docstring comment if it mentions the
  count (Task 10 may have handled it).
- `CONTEXT.md` (domain glossary): add the SIUnit Notation entry and the
  relevant glossary rows (grammar ↔ rule vocabulary) — kept in sync with
  the code per root AGENTS.md.
- `docs/development/MILESTONE.md`: if the row-23 status column has a
  convention, mark SI Unit per the URL row's treatment; otherwise leave
  the roadmap untouched (roadmap status is a product-owner call, out of
  scope).

**Step 3: Final pre-PR gate (authoritative, `.github/workflows/ci.yml`)**
— run the full merge-blocking suite and confirm green:

```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
uv run pyright
uv run import-linter lint
uv run pytest
uv run coverage report --include="paxman/core/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/*" --fail-under=95
uv run coverage report --include="paxman/engine/*" --fail-under=95
uv run coverage report --include="paxman/api/*" --fail-under=95
uv run coverage report --include="paxman/capabilities/SIUnit/*" --fail-under=95
```

Coverage: `paxman/capabilities/SIUnit/` must be ≥95% (per-package gate).
If a line is structurally unreachable (e.g. a defensive branch in the
generator), the sanctioned pattern is a scoped `per-file-ignores` entry in
`pyproject.toml` — never `# noqa` / `# pragma` / `# type: ignore` in
source.

**Step 4:** verify + commit — all gates green. Commit
`docs(si_unit): document SIUnit capability and update capability counts`.
---

## §3 Sequencing and Parallelism

- **Strictly sequential, one executor, one worktree**: Tasks 1 → 2 → 3 → 4
  → 5 → 6 → 7 (each feeds the next; TDD red/green per task; Task 4's
  generator is the only place an external data source can bite — do **not**
  parallelize it).
- Task 8 depends on Tasks 3–7 (it locks the seam between generated token
  tables and authority tables).
- Tasks 9 → 10 depend on Task 7 (the capability needs all grammars and
  rules wired before registration); Task 10 also depends on Task 9 — its
  surface row imports `SIUnitCapability`, and its semantics-guard edits
  import SIUnit through the `paxman.capabilities` package, so the guard
  edits and the registration land in the **same** Task 10 commit (RED:
  missing export; GREEN: registration).
- Tasks 11 → 12 depend on Task 10 (registration must land before the
  pipeline/determinism/e2e tasks can run).
- Task 13 is last (docs reflect the registered surface).
- Each task commits atomically with the message in its header; never merge
  tasks' commits.
- The `si_unit` pytest marker is registered in Task 1; every later task
  uses it (pyproject accepts unknown markers only as warnings — Task 1 is
  the sanctioned point).

## §4 Traps (call out explicitly in the plan doc)

- **T1. No cross-capability imports.** SIUnit must vendor its own data
  tables (import-linter enforces the boundary). Never
  `from paxman.capabilities.Money...` or Currency. The generator re-derives
  from the same primary sources.
- **T2. Case-exact symbols are non-negotiable (D6).** `"pa"` is *not*
  `"Pa"`; `"Kg"` is not `"kg"`. Only the *name* grammar case-folds. Do not
  "helpfully" uppercase the symbol grammar — it would break `"s"` vs `"S"`,
  `"K"` vs `"k"`.
- **T3. One file = one publication.** `bipm_si_brochure_ed2019.py`
  (year 2019) and `iso_80000_ed2022.py` (year 2022). Do not split the
  BIPM rule classes across files; do not merge the ISO rule into the BIPM
  file.
- **T4. Rules never read `output_format`; `format_value` is the only
  presentation seam.** SIUnit has no offered formats → base identity
  `format_value`, do not override, do not mention `output_format` in rule
  code (CI source-scan).
- **T5. Grammar/rule boundary is absolute.** Grammars are shape-only +
  case-fold (symbols) / lowercase-fold (names); validity against the
  authority tables lives in rules; `grammar/data/` holds key-only token
  tables; authority mappings live in `rules/data/` and are imported only
  by rules. `tests/capabilities/si_unit/test_data_consistency.py` (Task 8)
  must cover every shipped recognition key against the rule-data mappings
  (house mandate). **SEAM:** the routing seam is declared, not inferred —
  every grammar carries `semantics`, every rule carries `target_semantics`
  naming it; the auto-discovering purity guards
  (`test_grammar_semantic_purity.py`, `test_rule_output_format_purity.py`)
  need no edits but SIUnit must satisfy them (grammars never import from
  `rules/`; rule modules contain no `output_format` token).
- **T6. The symbol grammar must not fragment compounds.** D2 lookarounds
  block `/`, `·`, `⋅` — keep them. If a compound input also yields a bare
  symbol match, the engine's per-grammar `_dedup_spans` cannot rescue it
  (R2: `"m s"` → AMBIGUOUS by design).
- **T7. The kilogram is not prefixable (D9).** Prefixes attach to the gram.
  Never hand-write `"kkg"`, `"Mkg"`, or `"kilokilogram"` anywhere — the
  generator excludes `"kg"` from `_prefixable_units()`; `"kilogram"` and
  `"kg"` stay the official base-unit name/symbol.
- **T8. Determinism is structural, not snapshot.** The replay-hash
  baseline suite was removed (PR #18): there is no hash literal to obtain
  or back-solve. Lock determinism the current way — the
  `TestCanonicalDeterminismAndCandidateOrder` "run twice, byte-identical"
  row for `"megahertz"` (Task 11 Step 4). Do not reintroduce a snapshot
  literal.
- **T9. Type safety / style.** No `# type: ignore` / `# noqa` /
  `# pyright: ignore` in `paxman/` source (tests may use
  `# type: ignore[misc]` for immutability checks). Rule classes CapWords.
  Contracts frozen **without** slots; notation frozen **with** slots.
  `_extra_dict_fields()` override, never hand-written `as_dict()`.
- **T10. Generated files are never hand-edited.** `prefixed_units.py`,
  `prefixed_unit_names.py`, and the grammar token modules are regenerated
  by `tools/regenerate_si_prefix_data.py` (ISBN range-data precedent).
  Edit the maintained tables, rerun the tool, and let
  `test_generator_is_idempotent` verify the committed state.
- **T11. Data-authoring honesty.** The maintainable tables are snapshots
  of the cited BIPM tables. The implementer completes any remaining
  Table 8–9 non-SI entries directly from the brochure and adjusts the
  non-SI count guard to the true total — never fabricate an entry, never
  invent a unit not in the brochure.
- **T12. Status semantics (D7).** Recognized-but-unresolved → INVALID;
  unrecognized → MISSING; multiple distinct canonicals → AMBIGUOUS. Do not
  add a fallback grammar to force a specific status — R1 (`"KHz"` →
  MISSING) and R2 (`"m s"` → AMBIGUOUS) are locked refinements.
- **T13. Registry freezing.** The moment SIUnit joins the registry
  (Task 10), every existing integration test runs against 10
  capabilities — all must stay green (including the
  `TestCanonicalDeterminismAndCandidateOrder` rows for the shipped nine).
  Do not touch other capabilities' rows or registration code.
- **T14. Registration surface.** `__init__.py` import + `__all__` together
  (acronym aliases are already per-file-ignored for N814); export guard
  count test 9 → 10; the `si_unit` marker is already registered in
  Task 1 — do not add it again.
- **T15. Compound split patterns stay local.** The ISO rule keeps its own
  split regex (never imported from `grammar/data/compound_tokens.py`) —
  rules must not import from the grammar tree (grammar↔rules purity scan).
- **T16. Semantics metadata is mandatory (SEAM, ADR-0003).** Every
  grammar class declares `semantics` (identity id for SIUnit) and every
  rule class declares `target_semantics` — the old `target_grammars`
  attribute no longer exists. `Grammar.__init_subclass__` and
  `Rule.__init_subclass__` fail the **import** with a `TypeError` if the
  metadata is missing or mistyped (e.g. `requires_features` must be
  `frozenset`, `target_semantics` non-empty), so a rule missing one of the
  six required attributes never reaches the pipeline.
- **T17. `active_grammars` is base-default `None` (SEAM, PR #20).** SIUnit
  has no input-shape feature flags, so `SIUnitContract` must **not**
  override `active_grammars` — the base `None` runs every shipped grammar
  in `get_grammars()` order. Adding an override (or a static tuple) is a
  convention violation caught by review, not by a guard.
- **T18. `create_contract` ends with `extra_grammars` (SEAM, PR #19).**
  The surface guard's `_COMMON_BLOCK` is `excluded_rules, pinned_rules,
  year, output_format, extra_grammars` in that order, and it asserts both
  the default `()` and forwarding. Do not omit the parameter or reorder
  the block; the contract itself inherits the field from the base.

## §5 Definition of Done

- [ ] All 13 tasks checked, each with its atomic commit (`feat(si_unit):`
      / `test(si_unit):` / `docs(si_unit):`).
- [ ] `tests/capabilities/si_unit/` green: test_notation, test_contract,
      test_data, test_grammar, test_rules, test_capability,
      test_data_consistency (7 files — **no** test_parsing: SIUnit has no
      quantities).
- [ ] `tests/unit` guards green with SIUnit registered: capability
      exports (ten names), capability surface (`_CAPABILITY_SURFACES`
      row), grammar-semantics metadata, grammar-semantics consistency
      (SEAM — Tasks 10).
- [ ] `tests/integration/test_si_unit_pipeline.py` green with the full §1
      e2e contract (27 rows: 18 SUCCESS, 3 INVALID, 5 MISSING, 1 AMBIGUOUS;
      "USD" is one of the MISSING rows — not an SI token).
- [ ] Canonical determinism row for `"megahertz"` in
      `TestCanonicalDeterminismAndCandidateOrder` green (SEAM — Task 11;
      the replay-hash baseline was removed in PR #18).
- [ ] Property + e2e coverage green (Task 12).
- [ ] Docs: README (10 capabilities, SI Unit section), root AGENTS.md,
      capabilities AGENTS.md, CONTEXT.md.
- [ ] Full pre-PR gate green (Task 13 Step 3), including ≥95% coverage on
      `paxman/capabilities/SIUnit/`.
