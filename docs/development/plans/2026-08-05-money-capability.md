# Money Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the **Money capability** that canonicalizes ambiguous currency-amount input to the canonical `CODE + " " + amount` form (e.g. `USD 500.00`) with full provenance. Design source: `docs/research/2026-08-05-money-canonicalization.md` (its §9 "Locked Decisions" is authoritative for reasoning; the cross-part contract below is authoritative for shapes). This plan covers Tasks 1–11 in order: package skeleton, `MoneyNotation`, `MoneyContract`, data tables, rules, grammars, parsing helper, capability wiring, registration, integration/property/replay-hash tests, and documentation.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

**Architecture:** A seventh self-contained capability package `paxman/capabilities/Money/` following the unanimous surface: three recognition grammars (`code_recognition`, `symbol_recognition`, `word_recognition`) emit span-bearing `RecognitionMatch[MoneyNotation]`; three authority rules (`SectionCode`, `SectionSymbols`, `SectionNames`) validate against ISO 4217 / CLDR data modules and normalize to the canonical `CODE amount` string; `format_value()` renders `"code_amount"` (identity, the default) or `"compact"` (removes the single space). The contract carries `precision` ("strict"/"truncate"/"round") and `dollar_sign_currency` (uppercase ISO 4217 alpha-3 or `None`; `None` is the default — bare `$`-style symbols only resolve when a currency is explicitly opted in); rules receive the contract, so they read `precision` and `dollar_sign_currency` directly.

**Tech Stack:** Python 3.11, standard library only (re-based grammars, frozen dataclasses). Tests: pytest with the `capability` marker; a `-m money` marker is added in Task 7, so every command in this task runs by path. Gates unchanged: ruff (line-length 88, target py311), pyright strict (`include = ["paxman"]` — tests are excluded), import-linter layers, pytest at 95% coverage.

---

**Plan scope:** Tasks 1 and 2 (this first task group) — the package skeleton, `MoneyNotation` (notation.py), `MoneyContract` (contract.py), and their tests. No rules, grammars, data tables, parsing helper, or capability wiring are implemented here; later tasks add them (referenced by name only where the contract fields require).

## Cross-Part Contract (must stay identical across all tasks)

- `MoneyNotation` (notation.py): frozen slots dataclass with fields `currency_part: str`, `amount_part: str`, `currency_shape: str = ""` (valid values `"code" | "symbol" | "qualified_symbol" | "word"`), `amount_shape: str = ""` (valid values `"integer" | "dot_decimal" | "comma_decimal" | "space_decimal" | "accounting"`); method `as_list() -> list[str]` returns `[currency_part, amount_part, currency_shape, amount_shape]`.
- `MoneyContract(CapabilityContract)` (contract.py): `capability_name = field(default="money", init=False)`; `active_grammars` = `("code_recognition", "symbol_recognition", "word_recognition")`; `precision: Literal["strict", "truncate", "round"] = "strict"`; `dollar_sign_currency: str | None = None`; `DEFAULT_OUTPUT_FORMAT = "code_amount"`; `OFFERED_OUTPUT_FORMATS = frozenset({"compact"})`; `__post_init__` calls `super().__post_init__()` FIRST, then validates `precision` and `dollar_sign_currency`; `_extra_dict_fields()` returns `{"precision", "dollar_sign_currency"}`.
- Canonical value shape: `"CODE" + " " + amount_with_minor_unit_padding`, e.g. `USD 500.00`, built in `Rule.normalize()`. `"compact"` removes the single space (`USD500.00`).
- Later-task names (not implemented in Tasks 1–2): grammar files `grammar/code_recognition.py`, `grammar/symbol_recognition.py`, `grammar/word_recognition.py`; rule files `rules/iso_4217_ed2015.py` (`SectionCode`), `rules/cldr_currencies_ed2025.py` (`SectionSymbols`, `SectionNames`); data modules `rules/data/iso4217_list_one.py`, `rules/data/cldr_currencies.py`, `grammar/data/currency_symbols.py`, `grammar/data/currency_words.py`; package-root `parsing.py` (`ParsedAmount`, `parse_amount`, `format_amount`); `capability.py` (`MoneyCapability`).

---

### Task 1: Package skeleton and MoneyNotation

**Files:**
- Create: `paxman/capabilities/Money/__init__.py`
- Create: `paxman/capabilities/Money/grammar/__init__.py`
- Create: `paxman/capabilities/Money/grammar/data/__init__.py`
- Create: `paxman/capabilities/Money/rules/__init__.py`
- Create: `paxman/capabilities/Money/rules/data/__init__.py`
- Create: `paxman/capabilities/Money/notation.py`
- Create: `tests/capabilities/money/__init__.py`
- Create: `tests/capabilities/money/test_notation.py`

- [ ] **Step 1: Write the failing test**

`tests/capabilities/money/test_notation.py` — the test module marks `@pytest.mark.capability` at module level (ISBN precedent, the newest exemplar). It imports `MoneyNotation`, so it cannot collect until the package exists:

```python
# tests/capabilities/money/test_notation.py
"""Tests for Money notation."""

import dataclasses

import pytest

from paxman.capabilities.Money.notation import MoneyNotation

pytestmark = [pytest.mark.capability]


def test_notation_frozen_and_slots() -> None:
    """Notation must be a frozen, slots-based dataclass."""
    assert dataclasses.is_dataclass(MoneyNotation)
    assert "__slots__" in MoneyNotation.__dict__


def test_notation_fields() -> None:
    """Notation fields are exactly the four component fields."""
    assert [f.name for f in dataclasses.fields(MoneyNotation)] == [
        "currency_part",
        "amount_part",
        "currency_shape",
        "amount_shape",
    ]


def test_field_defaults() -> None:
    """Shape fields default to the empty unset sentinel."""
    notation = MoneyNotation(currency_part="USD", amount_part="500")
    assert notation.currency_shape == ""
    assert notation.amount_shape == ""


def test_shape_value_validation() -> None:
    """Invalid shape values raise ValueError at construction."""
    with pytest.raises(ValueError):
        MoneyNotation(currency_part="USD", amount_part="500", currency_shape="bogus")
    with pytest.raises(ValueError):
        MoneyNotation(currency_part="USD", amount_part="500", amount_shape="bogus")


def test_valid_shapes_accepted() -> None:
    """Every enumerated shape value is accepted; the empty sentinel is too."""
    for shape in ("code", "symbol", "qualified_symbol", "word"):
        MoneyNotation(currency_part="USD", amount_part="500", currency_shape=shape)
    for shape in (
        "integer",
        "dot_decimal",
        "comma_decimal",
        "space_decimal",
        "accounting",
    ):
        MoneyNotation(currency_part="USD", amount_part="500", amount_shape=shape)
    MoneyNotation(currency_part="USD", amount_part="500")


def test_as_list_order() -> None:
    """as_list returns [currency_part, amount_part, currency_shape, amount_shape]."""
    notation = MoneyNotation(
        currency_part="$",
        amount_part="1,234.56",
        currency_shape="symbol",
        amount_shape="comma_decimal",
    )
    assert notation.as_list() == ["$", "1,234.56", "symbol", "comma_decimal"]


def test_notation_hashable() -> None:
    """Equal instances hash equal."""
    a = MoneyNotation(currency_part="USD", amount_part="500")
    b = MoneyNotation(currency_part="USD", amount_part="500")
    assert hash(a) == hash(b)
    assert a == b


def test_notation_equality_inequality() -> None:
    """Equal instances compare equal; differing fields do not."""
    a = MoneyNotation(currency_part="USD", amount_part="500")
    b = MoneyNotation(currency_part="USD", amount_part="500")
    c = MoneyNotation(currency_part="EUR", amount_part="500")
    assert a == b
    assert a != c


def test_notation_immutable() -> None:
    """Assigning a field raises FrozenInstanceError."""
    notation = MoneyNotation(currency_part="USD", amount_part="500")
    with pytest.raises(dataclasses.FrozenInstanceError):
        notation.amount_part = "600"  # type: ignore[misc]
```

Also create the test package `__init__.py`:

```python
# tests/capabilities/money/__init__.py
"""Money capability tests."""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/money/test_notation.py -v`
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'paxman.capabilities.Money'` (the test module imports from a package that does not exist yet).

- [ ] **Step 3: Create the package skeleton**

```bash
mkdir -p paxman/capabilities/Money/grammar/data
mkdir -p paxman/capabilities/Money/rules/data
```

One-line docstring each, ISBN/Country precedent (Money is not an acronym, so the N814 per-file-ignore does not apply here):

```python
# paxman/capabilities/Money/__init__.py
"""Money capability for canonicalizing currency amounts."""
```

```python
# paxman/capabilities/Money/grammar/__init__.py
"""Money recognition grammars."""
```

```python
# paxman/capabilities/Money/grammar/data/__init__.py
"""Money grammar data tables (recognition keys)."""
```

```python
# paxman/capabilities/Money/rules/__init__.py
"""Money validation rules."""
```

```python
# paxman/capabilities/Money/rules/data/__init__.py
"""Money rule data tables (authority mappings)."""
```

(The `Money/__init__.py` re-exports of `MoneyCapability`/`MoneyContract`/`MoneyNotation` are added in the registration task of a later part, exactly like the ISBN plan deferred its aliases.)

- [ ] **Step 4: Write the minimal implementation**

`paxman/capabilities/Money/notation.py` — frozen slots dataclass mirroring `PhoneNotation`/`CountryNotation` (`as_list()` returns a plain `list[str]` for the generic rule interface), plus a `__post_init__` shape validator. The `""` field defaults are the allowed unset sentinel; any non-empty value must be in the enumerated set or construction raises `ValueError`:

```python
# paxman/capabilities/Money/notation.py
"""Money notation — intermediate representation for currency amount recognition."""

from __future__ import annotations

from dataclasses import dataclass

_VALID_CURRENCY_SHAPES = frozenset({"code", "symbol", "qualified_symbol", "word"})
_VALID_AMOUNT_SHAPES = frozenset(
    {"integer", "dot_decimal", "comma_decimal", "space_decimal", "accounting"}
)


@dataclass(frozen=True, slots=True)
class MoneyNotation:
    """Intermediate representation for currency amount recognition.

    Attributes:
        currency_part: The currency token as written (e.g., "USD", "$", "CA$",
            "euro"), taken verbatim from the input by the grammar.
        amount_part: The amount token as written (e.g., "1,234.56", "500"),
            taken verbatim from the input by the grammar.
        currency_shape: Discriminator assigned by the grammar: "code",
            "symbol", "qualified_symbol", or "word"; "" when not yet assigned.
        amount_shape: Discriminator assigned by the grammar: "integer",
            "dot_decimal", "comma_decimal", "space_decimal", or "accounting";
            "" when not yet assigned.
    """

    currency_part: str
    amount_part: str
    currency_shape: str = ""
    amount_shape: str = ""

    def __post_init__(self) -> None:
        """Validate shape discriminators.

        Grammars assign only the enumerated values; "" is the allowed unset
        default. Any other value is a recognition-layer bug surfaced loudly.

        Raises:
            ValueError: If a shape field holds a value outside its enumerated
                set (the empty string is the allowed unset sentinel).
        """
        if self.currency_shape and self.currency_shape not in _VALID_CURRENCY_SHAPES:
            raise ValueError(f"invalid currency_shape: {self.currency_shape!r}")
        if self.amount_shape and self.amount_shape not in _VALID_AMOUNT_SHAPES:
            raise ValueError(f"invalid amount_shape: {self.amount_shape!r}")

    def as_list(self) -> list[str]:
        """Bridge to generic list[str] interface.

        Returns:
            [currency_part, amount_part, currency_shape, amount_shape].
        """
        return [
            self.currency_part,
            self.amount_part,
            self.currency_shape,
            self.amount_shape,
        ]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/money/test_notation.py -v`
Expected: PASS — `9 passed` (frozen_and_slots, fields, field_defaults, shape_value_validation, valid_shapes_accepted, as_list_order, hashable, equality_inequality, immutable).

- [ ] **Step 6: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_notation.py
uv run ruff check paxman/capabilities/Money tests/capabilities/money
uv run pyright paxman/capabilities/Money/notation.py
```

All three pass. Stage ONLY the Task 1 files (the two new directories contain only Task 1 files at this point):

```bash
git add paxman/capabilities/Money tests/capabilities/money
git commit -m "feat(money): add MoneyNotation and package skeleton"
```

---

### Task 2: MoneyContract

**Files:**
- Create: `paxman/capabilities/Money/contract.py`
- Create: `tests/capabilities/money/test_contract.py`

- [ ] **Step 1: Write the failing test**

`tests/capabilities/money/test_contract.py` — contract tests use the **class-level** `@pytest.mark.capability` marker (Country `test_capability.py` pattern) plus `@pytest.mark.parametrize` where apt. Note: `tests/` is excluded from pyright (`include = ["paxman"]`), so the invalid-value parametrizations need no `# type: ignore`:

```python
# tests/capabilities/money/test_contract.py
"""Tests for Money contract."""

import dataclasses

import pytest

from paxman.capabilities.Money.contract import MoneyContract
from paxman.core.errors import ContractError

_STANDARD_KEYS = frozenset(
    {"capability_name", "excluded_rules", "pinned_rules", "year", "output_format"}
)


@pytest.mark.capability
class TestMoneyContractDefaults:
    """Default field values."""

    def test_default_output_format(self) -> None:
        """output_format resolves to code_amount by default."""
        assert MoneyContract().output_format == "code_amount"

    def test_offered_output_formats(self) -> None:
        """Only compact is offered beyond the default."""
        assert frozenset({"compact"}) == MoneyContract.OFFERED_OUTPUT_FORMATS

    def test_capability_name(self) -> None:
        """capability_name is fixed to money."""
        assert MoneyContract().capability_name == "money"

    def test_precision_default(self) -> None:
        """precision defaults to strict."""
        assert MoneyContract().precision == "strict"

    def test_dollar_sign_currency_default(self) -> None:
        """dollar_sign_currency defaults to None (bare $ stays INVALID)."""
        assert MoneyContract().dollar_sign_currency is None

    def test_active_grammars(self) -> None:
        """All three recognition grammars are active by default."""
        assert MoneyContract().active_grammars == (
            "code_recognition",
            "symbol_recognition",
            "word_recognition",
        )

    def test_frozen(self) -> None:
        """Assigning a field raises FrozenInstanceError."""
        contract = MoneyContract()
        with pytest.raises(dataclasses.FrozenInstanceError):
            contract.precision = "round"  # type: ignore[misc]


@pytest.mark.capability
class TestMoneyContractPrecision:
    """precision validation."""

    @pytest.mark.parametrize("precision", ["strict", "truncate", "round"])
    def test_valid_precision_accepted(self, precision: str) -> None:
        """Each of the three precision values is accepted."""
        assert MoneyContract(precision=precision).precision == precision

    @pytest.mark.parametrize("precision", ["bogus", "", "STRICT", 42, None])
    def test_invalid_precision_raises_contract_error(self, precision: object) -> None:
        """Anything outside the three raises ContractError at construction."""
        with pytest.raises(ContractError):
            MoneyContract(precision=precision)


@pytest.mark.capability
class TestMoneyContractDollarSignCurrency:
    """dollar_sign_currency validation."""

    def test_none_allowed(self) -> None:
        """None (the default) means bare $ symbols stay unresolved."""
        assert MoneyContract(dollar_sign_currency=None).dollar_sign_currency is None

    def test_uppercase_alpha3_accepted(self) -> None:
        """An uppercase ISO 4217 alpha-3 code is accepted (opt-in)."""
        assert MoneyContract(dollar_sign_currency="EUR").dollar_sign_currency == "EUR"

    @pytest.mark.parametrize("currency", ["usd", "US", "US1", "USDD", "U$D", 123])
    def test_invalid_dollar_sign_currency_raises_contract_error(
        self, currency: object
    ) -> None:
        """Non-alpha-3 dollar_sign_currency values raise ContractError."""
        with pytest.raises(ContractError):
            MoneyContract(dollar_sign_currency=currency)


@pytest.mark.capability
class TestMoneyContractOutputFormat:
    """output_format resolution (base-class rules)."""

    @pytest.mark.parametrize("value", [None, "default", "code_amount"])
    def test_default_paths_resolve_to_code_amount(self, value: str | None) -> None:
        """None/default/code_amount all resolve to code_amount."""
        assert MoneyContract(output_format=value).output_format == "code_amount"

    def test_compact_resolves_to_compact(self) -> None:
        """The offered compact format resolves to itself."""
        assert MoneyContract(output_format="compact").output_format == "compact"

    @pytest.mark.parametrize("fmt", ["", "none", "None", "hyphenated", "compact "])
    def test_unknown_format_raises_contract_error(self, fmt: str) -> None:
        """Unoffered output_format values raise ContractError at construction."""
        with pytest.raises(ContractError):
            MoneyContract(output_format=fmt)


@pytest.mark.capability
class TestMoneyContractSerialization:
    """as_dict surface."""

    def test_as_dict_deterministic_key_set(self) -> None:
        """as_dict() emits the standard keys plus precision and dollar_sign_currency."""
        assert set(MoneyContract().as_dict().keys()) == _STANDARD_KEYS | {
            "precision",
            "dollar_sign_currency",
        }

    def test_as_dict_values(self) -> None:
        """as_dict() serializes precision and dollar_sign_currency with their values."""
        d = MoneyContract(precision="round", dollar_sign_currency="JPY").as_dict()
        assert d["precision"] == "round"
        assert d["dollar_sign_currency"] == "JPY"

    def test_as_dict_includes_resolved_output_format(self) -> None:
        """as_dict() emits the resolved (non-None) output_format."""
        assert MoneyContract().as_dict()["output_format"] == "code_amount"

    def test_extra_dict_fields_do_not_collide_with_standard_keys(self) -> None:
        """Capability-specific as_dict() keys never shadow the standard keys."""
        assert not (set(MoneyContract()._extra_dict_fields()) & _STANDARD_KEYS)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/capabilities/money/test_contract.py -v`
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'paxman.capabilities.Money.contract'` (the contract module does not exist yet).

- [ ] **Step 3: Write the minimal implementation**

`paxman/capabilities/Money/contract.py` — extends `CapabilityContract` exactly like the ISBN/Country/Phone contracts: frozen dataclass, no `slots=True`, `capability_name` via `field(default=..., init=False)`, `super().__post_init__()` first, `_extra_dict_fields()` override. `dollar_sign_currency` validation mirrors the Phone `_validate_alpha2` helper pattern (widened `cast(object, ...)` check, same two-branch `ContractError` message shape) adapted to ISO 4217 alpha-3. The `precision` check also widens to `object` before the `in` test, so pyright strict never treats the Literal-typed comparison as statically decidable:

```python
# paxman/capabilities/Money/contract.py
"""Money contract — user-facing configuration for Money capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Literal, cast

from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import ContractError

_PRECISION_VALUES = ("strict", "truncate", "round")


def _validate_alpha3(value: str | None) -> None:
    """Validate an ISO 4217 alpha-3 currency code.

    Args:
        value: Currency code to validate (None is allowed — means "no default").

    Raises:
        ContractError: If the value is present but not an uppercase
            3-letter ASCII ISO 4217 alpha-3 code (or not a str at all).
    """
    if value is None:
        return
    candidate = cast(object, value)
    if not isinstance(candidate, str):
        raise ContractError(
            "dollar_sign_currency must be an uppercase ISO 4217 alpha-3 code, "
            f"got {value!r}"
        )
    if (
        len(candidate) != 3
        or not candidate.isascii()
        or not candidate.isalpha()
        or not candidate.isupper()
    ):
        raise ContractError(
            "dollar_sign_currency must be an uppercase ISO 4217 alpha-3 code, "
            f"got {value!r}"
        )


@dataclass(frozen=True)
class MoneyContract(CapabilityContract):
    """User-facing configuration for Money capability.

    Attributes:
        capability_name: Fixed to "money" (not user-settable).
        precision: Amount normalization to ISO 4217 minor units — "strict"
            (over-precision → INVALID, decided by the rules' matches()),
            "truncate" (excess digits dropped), or "round" (half-to-even).
        dollar_sign_currency: ISO 4217 alpha-3 code (opt-in) used to resolve
            bare multi-candidate symbol input (e.g., "$500" with
            dollar_sign_currency="MYR" → "MYR 500.00"). Defaults to None:
            bare "$" is then recognized but never resolved (status INVALID).
            Never remaps a definitive symbol (e.g. "€" → EUR) or a qualified
            symbol ("US$" → USD).
        output_format: Canonical output format ("code_amount" default;
            "compact" removes the single space). Optional — None/"default"/
            "code_amount" all resolve to "code_amount".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
        year: Year for temporal filtering.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "code_amount"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact"})

    capability_name: str = field(default="money", init=False)

    # Capability-specific fields
    precision: Literal["strict", "truncate", "round"] = "strict"
    dollar_sign_currency: str | None = None

    def __post_init__(self) -> None:
        """Validate contract configuration.

        Calls the base output_format resolution first, then enforces
        Money-specific rules: precision must be one of "strict"/"truncate"/
        "round" and dollar_sign_currency must be an uppercase ISO 4217
        alpha-3 code when present.

        Raises:
            ContractError: If output_format is unsupported, precision is not
                one of the three, or dollar_sign_currency is present but not an
                uppercase alpha-3 code.
        """
        super().__post_init__()
        candidate = cast(object, self.precision)
        if candidate not in _PRECISION_VALUES:
            raise ContractError(
                "precision must be one of 'strict', 'truncate', or 'round', "
                f"got {self.precision!r}"
            )
        _validate_alpha3(self.dollar_sign_currency)

    @property
    def active_grammars(self) -> tuple[str, ...]:
        """All grammars active by default.

        All three recognition grammars are always active; Money has no
        input-shape feature flags.

        Returns:
            The three recognition grammar names.
        """
        return ("code_recognition", "symbol_recognition", "word_recognition")

    def _extra_dict_fields(self) -> dict[str, object]:
        """Serialize capability-specific fields for replay hash.

        > **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

                Returns:
                    Dictionary of precision and dollar_sign_currency fields.
        """
        return {
            "precision": self.precision,
            "dollar_sign_currency": self.dollar_sign_currency,
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/capabilities/money/test_contract.py -v`
Expected: PASS — `36 passed` (defaults ×7, precision ×3 valid + ×5 invalid, dollar_sign_currency ×2 valid + ×6 invalid, output_format ×3 default-path + ×1 compact + ×5 invalid, serialization ×4).

- [ ] **Step 5: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_contract.py
uv run ruff check paxman/capabilities/Money tests/capabilities/money
uv run pyright paxman/capabilities/Money/contract.py
```

All three pass. Stage ONLY the Task 2 files:

```bash
git add paxman/capabilities/Money/contract.py tests/capabilities/money/test_contract.py
git commit -m "feat(money): add MoneyContract"
```
### Task 3: Currency data tables

**Files:**
- Create: `paxman/capabilities/Money/rules/data/iso4217_list_one.py`
- Create: `paxman/capabilities/Money/rules/data/cldr_currencies.py`
- Create: `paxman/capabilities/Money/grammar/data/currency_symbols.py`
- Create: `paxman/capabilities/Money/grammar/data/currency_words.py`
- Create: `tests/capabilities/money/test_data.py`

**Dependency note (cross-part contract):** the data tables are pure module-level constants; rules import them at module scope; the grammar fixtures load them from `tests/conftest.py`. Task 4 (validation rules) consumes `CURRENCY_CODES`, `MINOR_UNITS`, `SYMBOL_TO_CODES`, and `NAME_TO_CODES`; Task 5 (recognition grammars) consumes `SYMBOL_TOKENS` and `WORD_TOKENS`. The `-m money` marker is added in Task 7, so every command in this task runs by path and the test module uses only `@pytest.mark.capability`.

**Scope note (data provenance):** the four modules are PLAIN hand-maintainable data tables — no `GENERATED` banner, no committed snapshots, exactly like `Phone/rules/data/e164_country_codes.py` and `Country/rules/data/cldr_ed2025.py` (one item per line, the ruff-format-sanctioned data-table style). The derivation script below is a one-off plan aid that PRINTS the four module bodies from the research snapshots; it is never committed (Step 8 stages only the four modules and the test). The two ISO 4217 tables (`CURRENCY_CODES`, `MINOR_UNITS`) and the two grammar token tuples (`SYMBOL_TOKENS`, `WORD_TOKENS`) are reproduced COMPLETE below so the script output can be verified by eye; the two CLDR dicts (`SYMBOL_TO_CODES`, `NAME_TO_CODES`) show representative complete rows — the full 67-key / 62-key content comes from the script output (Step 3), which the tests in Step 1 then verify.

**Count facts (locked):** the snapshot lists 178 codes; the 13 codes whose `CcyMnrUnts` is `"N.A."` (XAG XAU XBA XBB XBC XBD XDR XPD XPT XSU XTS XUA XXX) are EXCLUDED — they have no usable minor units — leaving **165 in-scope codes**. Minor-unit buckets: 0 for 17 codes (BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF), 3 for 7 codes (BHD IQD JOD KWD LYD OMR TND), 4 for 2 codes (CLF UYW), 2 for the rest. 67 distinct symbol forms (40 qualified, 27 bare) after the ISO-code-lookalike and whitespace filters.

- [ ] **Step 1: RED — write the data tests** (`tests/capabilities/money/test_data.py`, module-level `pytestmark = [pytest.mark.capability]`, Phone `test_data.py` structure: locked counts, structure checks, spot checks; plus token-ordering tests for D4 and filter tests for the CLDR purity rules)

```python
"""Tests for Money currency data table integrity."""

from __future__ import annotations

import pytest
from paxman.capabilities.Money.grammar.data.currency_symbols import SYMBOL_TOKENS
from paxman.capabilities.Money.grammar.data.currency_words import WORD_TOKENS
from paxman.capabilities.Money.rules.data.cldr_currencies import (
    NAME_TO_CODES,
    SYMBOL_TO_CODES,
)
from paxman.capabilities.Money.rules.data.iso4217_list_one import (
    CURRENCY_CODES,
    MINOR_UNITS,
)

pytestmark = [pytest.mark.capability]


def _is_qualified(token: str) -> bool:
    """A symbol token is qualified when it contains an ASCII letter."""
    return any(ch.isascii() and ch.isalpha() for ch in token)


class TestIso4217ListOne:
    """Tests for the ISO 4217 List One code and minor-unit tables."""

    def test_verified_count(self) -> None:
        """The code set is locked to the verified in-scope count of 165.

        The 2026-01-01 snapshot lists 178 codes; the 13 codes whose
        CcyMnrUnts is "N.A." (XAG XAU XBA XBB XBC XBD XDR XPD XPT XSU
        XTS XUA XXX) are excluded: they have no usable minor units.
        """
        assert len(CURRENCY_CODES) == 165

    def test_minor_units_cover_exactly_the_codes(self) -> None:
        """MINOR_UNITS has exactly one entry per code and no extras."""
        assert len(MINOR_UNITS) == len(CURRENCY_CODES)
        assert set(MINOR_UNITS) == CURRENCY_CODES

    def test_all_codes_uppercase_alpha3(self) -> None:
        """Every code is an uppercase 3-letter ASCII code."""
        for code in CURRENCY_CODES:
            assert len(code) == 3
            assert code.isascii()
            assert code.isalpha()
            assert code.isupper()

    def test_minor_unit_spot_checks(self) -> None:
        """Spot-check the exponent buckets: 0, 2, 3, and 4 minor units."""
        assert MINOR_UNITS["USD"] == 2
        assert MINOR_UNITS["EUR"] == 2
        assert MINOR_UNITS["JPY"] == 0
        assert MINOR_UNITS["KRW"] == 0
        assert MINOR_UNITS["BHD"] == 3
        assert MINOR_UNITS["KWD"] == 3
        assert MINOR_UNITS["CLF"] == 4
        assert MINOR_UNITS["UYW"] == 4

    def test_no_minor_unit_exceeds_four(self) -> None:
        """No code has more than 4 minor units (CLF/UYW are the max)."""
        assert max(MINOR_UNITS.values()) == 4

    def test_na_minor_units_codes_excluded(self) -> None:
        """Codes with a N.A. minor-unit exponent are not in the table."""
        for code in (
            "XAG",
            "XAU",
            "XBA",
            "XBB",
            "XBC",
            "XBD",
            "XDR",
            "XPD",
            "XPT",
            "XSU",
            "XTS",
            "XUA",
            "XXX",
        ):
            assert code not in CURRENCY_CODES

    def test_new_and_fund_codes_present(self) -> None:
        """Spot-check recently added and fund codes present in the table."""
        for code in (
            "XAD",
            "XCG",
            "VED",
            "CHE",
            "CHW",
            "COU",
            "MXV",
            "BOV",
            "UYI",
            "USN",
        ):
            assert code in CURRENCY_CODES


class TestCldrCurrencies:
    """Tests for the CLDR symbol and display-name tables."""

    def test_symbol_values_are_sorted_tuples_of_known_codes(self) -> None:
        """Every symbol value is a non-empty sorted tuple of in-scope codes."""
        for codes in SYMBOL_TO_CODES.values():
            assert isinstance(codes, tuple)
            assert codes
            assert codes == tuple(sorted(codes))
            assert set(codes) <= CURRENCY_CODES

    def test_dollar_family(self) -> None:
        """The bare $ maps to the 29 dollar-family codes, including USD."""
        assert len(SYMBOL_TO_CODES["$"]) == 29
        assert "USD" in SYMBOL_TO_CODES["$"]

    def test_qualified_symbols_definitive(self) -> None:
        """Qualified symbols map to exactly one code (D4/D6)."""
        assert SYMBOL_TO_CODES["US$"] == ("USD",)
        assert SYMBOL_TO_CODES["CA$"] == ("CAD",)
        assert SYMBOL_TO_CODES["RM"] == ("MYR",)
        assert SYMBOL_TO_CODES["C$"] == ("NIO",)

    def test_bare_multi_candidate_symbols(self) -> None:
        """Bare symbols shared by several currencies list every code."""
        assert SYMBOL_TO_CODES["¥"] == ("CNY", "JPY")
        assert SYMBOL_TO_CODES["£"] == ("FKP", "GBP", "GIP", "SHP", "SSP", "SYP")
        assert SYMBOL_TO_CODES["₩"] == ("KPW", "KRW")

    def test_definitive_bare_symbols(self) -> None:
        """Bare single-candidate symbols are definitive (D3)."""
        assert SYMBOL_TO_CODES["€"] == ("EUR",)
        assert SYMBOL_TO_CODES["₽"] == ("RUB",)

    def test_no_symbol_equals_its_code(self) -> None:
        """CLDR code-fallback symbols (e.g. AED -> "AED") are omitted."""
        for symbol, codes in SYMBOL_TO_CODES.items():
            assert symbol not in codes
            assert not (
                len(symbol) == 3
                and symbol.isascii()
                and symbol.isalpha()
                and symbol.isupper()
            )

    def test_no_symbol_contains_whitespace(self) -> None:
        """Symbols containing (narrow no-break) spaces are omitted."""
        for symbol in SYMBOL_TO_CODES:
            assert not any(ch.isspace() for ch in symbol)

    def test_code_fallback_symbols_absent(self) -> None:
        """Codes whose CLDR symbol is the code itself have no symbol row."""
        assert "BHD" not in SYMBOL_TO_CODES
        assert "AED" not in SYMBOL_TO_CODES

    def test_name_values_are_sorted_tuples_of_known_codes(self) -> None:
        """Every name value is a non-empty sorted tuple of in-scope codes."""
        for codes in NAME_TO_CODES.values():
            assert isinstance(codes, tuple)
            assert codes
            assert codes == tuple(sorted(codes))
            assert set(codes) <= CURRENCY_CODES

    def test_brief_anchored_names_definitive(self) -> None:
        """The brief-anchored display names are definitive mappings."""
        assert NAME_TO_CODES["Dollar"] == ("USD",)
        assert NAME_TO_CODES["Euro"] == ("EUR",)
        assert NAME_TO_CODES["Ringgit"] == ("MYR",)

    def test_every_name_is_definitive(self) -> None:
        """Each curated name maps to exactly one canonical code."""
        assert all(len(codes) == 1 for codes in NAME_TO_CODES.values())


class TestCurrencySymbolTokens:
    """Tests for the grammar symbol-token ordering (D4)."""

    def test_tokens_are_exactly_the_symbol_table_keys(self) -> None:
        """Every shipped symbol token must resolve through SYMBOL_TO_CODES."""
        assert set(SYMBOL_TOKENS) == set(SYMBOL_TO_CODES)

    def test_qualified_tokens_before_bare(self) -> None:
        """All qualified tokens precede all bare tokens (D4)."""
        tokens = list(SYMBOL_TOKENS)
        first_bare = next(
            i for i, token in enumerate(tokens) if not _is_qualified(token)
        )
        assert all(_is_qualified(token) for token in tokens[:first_bare])
        assert all(not _is_qualified(token) for token in tokens[first_bare:])

    def test_longest_first_within_each_class(self) -> None:
        """Within each class, tokens are ordered longest first (D4)."""
        for cls in ("qualified", "bare"):
            tokens = [
                token
                for token in SYMBOL_TOKENS
                if _is_qualified(token) == (cls == "qualified")
            ]
            lengths = [len(token) for token in tokens]
            assert lengths == sorted(lengths, reverse=True)


class TestCurrencyWordTokens:
    """Tests for the grammar word-token ordering."""

    def test_tokens_are_exactly_the_name_table_keys(self) -> None:
        """Every shipped word token must resolve through NAME_TO_CODES."""
        assert set(WORD_TOKENS) == set(NAME_TO_CODES)

    def test_longest_first(self) -> None:
        """Word tokens are ordered longest first for alternation."""
        lengths = [len(token) for token in WORD_TOKENS]
        assert lengths == sorted(lengths, reverse=True)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/capabilities/money/test_data.py -v`
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'paxman.capabilities.Money.rules.data.iso4217_list_one'` (the test imports all four data modules, none of which exist yet).

- [ ] **Step 3: GREEN — derive the four module bodies**

The derivation script below is the one-off plan aid (never committed). It reads the three research snapshots and PRINTS the four complete module bodies. The snapshots are already on this machine at `/tmp/opencode/` (research artifacts, never committed): `list-one.xml` (ISO 4217 List One, Pblshd 2026-01-01), `en_currencies.json` and `es_currencies.json` (CLDR v47 English + Spanish currency data, raw nested `main.<lang>.numbers.currencies` shape).

Copy the script into the repo temporarily and run it:

```bash
cp /tmp/opencode/derive_currency_tables.py tools/derive_currency_tables.py
uv run python tools/derive_currency_tables.py > /tmp/opencode/derived_tables.txt
```

`/tmp/opencode/derived_tables.txt` opens with `#`-comment summary lines, then four `===== <name>.py =====` sections — one per module. Each section is the COMPLETE module body (docstring through the final closing `}` / `)`); paste each into its file in Steps 4-6. The `#`-summary lines are NOT part of any module. The pasted modules must not carry any `GENERATED` banner — they are plain tables, hand-maintainable after this task, exactly like the ISBN plan's generator output is not re-run.

```python
# tools/derive_currency_tables.py (temporary — NEVER committed)
"""One-off derivation of the Money Task 3 data tables.

Reads the three research sources and PRINTS the full content of the four
plain data modules (ready to paste). Not committed anywhere; it is a plan
aid only, exactly like the ISBN plan's generator.

Sources:
- /tmp/opencode/list-one.xml        (ISO 4217 List One snapshot, Pblshd 2026-01-01)
- /tmp/opencode/en_currencies.json  (CLDR v47 English currency data, raw nested shape)
- /tmp/opencode/es_currencies.json  (CLDR v47 Spanish currency data, raw nested shape)

Derivation rules:
1. CURRENCY_CODES = the 165 codes with a NUMERIC CcyMnrUnts (the 13 codes
   whose CcyMnrUnts is "N.A." — XAG XAU XBA XBB XBC XBD XDR XPD XPT XSU XTS
   XUA XXX — are excluded: they have no usable minor units).
2. MINOR_UNITS = that numeric CcyMnrUnts per code.
3. SYMBOL_TO_CODES: for each in-scope code, collect `symbol` and
   `symbol-alt-narrow` from en then es CLDR. Skip: empty symbols; symbols
   equal to the code itself (CLDR code fallback, e.g. AED -> "AED");
   symbols containing whitespace (narrow no-break space variants);
   3-letter uppercase-ASCII letter strings (code lookalikes).
4. NAME_TO_CODES: curated English display-name words -> canonical codes
   (brief-anchored: Dollar -> USD, Euro -> EUR, Ringgit -> MYR).
5. SYMBOL_TOKENS: keys of SYMBOL_TO_CODES, QUALIFIED symbols first
   (token contains an ASCII letter, e.g. "US$", "CA$", "RM") then BARE
   symbols (pure symbol characters, e.g. "$", "\u00a5"), longest first
   within each class (so "US$" alternates before "$").
6. WORD_TOKENS: keys of NAME_TO_CODES, longest first.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

LIST_ONE = Path("/tmp/opencode/list-one.xml")
EN_CURRENCIES = Path("/tmp/opencode/en_currencies.json")
ES_CURRENCIES = Path("/tmp/opencode/es_currencies.json")


def _load_clrd_currencies(path: Path) -> dict[str, dict[str, object]]:
    """Unwrap CLDR's nested main.<lang>.numbers.currencies.<CODE> shape."""
    payload = json.loads(path.read_text())
    lang_block = next(iter(payload["main"].values()))
    return lang_block["numbers"]["currencies"]


def _minor_units() -> dict[str, int]:
    """ISO 4217 List One CcyMnrUnts for the 165 codes with numeric minor units."""
    root = ET.parse(LIST_ONE).getroot()
    minor: dict[str, int] = {}
    for row in root.findall(".//CcyNtry"):
        ccy = row.findtext("Ccy")
        units = row.findtext("CcyMnrUnts")
        if ccy is None or units is None or units == "N.A.":
            continue
        minor[ccy] = int(units)
    return dict(sorted(minor.items()))


def _symbol_forms(
    code: str,
    en: dict[str, dict[str, object]],
    es: dict[str, dict[str, object]],
) -> set[str]:
    """All en+es symbol strings for a code, after the purity filters."""
    forms: set[str] = set()
    for table in (en, es):
        entry = table.get(code)
        if not entry:
            continue
        for key in ("symbol", "symbol-alt-narrow"):
            value = entry.get(key)
            if not isinstance(value, str) or not value:
                continue
            sym = value.strip()
            if not sym:
                continue
            if sym == code:  # CLDR code fallback (e.g. AED -> "AED")
                continue
            if any(ch.isspace() for ch in sym):  # narrow no-break space variants
                continue
            if len(sym) == 3 and sym.isascii() and sym.isalpha() and sym.isupper():
                continue  # code lookalike
            forms.add(sym)
    return forms


def _is_qualified(token: str) -> bool:
    """A symbol is qualified when it contains an ASCII letter (US$, CA$, RM)."""
    return any(ch.isascii() and ch.isalpha() for ch in token)


def _emit_set(values: list[str], indent: str = "    ") -> str:
    """Emit one item per line (ruff format-clean, repo data-table style)."""
    return "\n".join(f'{indent}"{v}",' for v in values)


def _emit_tuple(values: list[str]) -> str:
    inner = ", ".join(f'"{v}"' for v in values)
    if len(values) == 1:
        inner += ","  # ("USD",) — a tuple, not a bare string
    return "(" + inner + ")"


def _emit_dict(
    items: list[tuple[str, tuple[str, ...]]],
    indent: str = "    ",
) -> str:
    """Emit one entry per line (ruff format-clean at line-length 88).

    Multi-code tuples that fit on one line stay inline; the 29-code "$"
    row wraps with one code per continuation line (ruff format expands
    magic-trailing-comma containers to one item per line).
    """
    lines = []
    for key, values in items:
        rendered = _emit_tuple(list(values))
        if len(indent) + len(key) + len(rendered) + 4 <= 88:
            lines.append(f'{indent}"{key}": {rendered},')
            continue
        lines.append(f'{indent}"{key}": (')
        for code in values:
            lines.append(f'{indent}    "{code}",')
        lines.append(f"{indent}),")
    return "\n".join(lines)


def main() -> None:
    minor = _minor_units()
    codes = sorted(minor)
    print(f"# {len(codes)} in-scope codes, {len(minor)} minor-unit entries")
    print(
        f"# zero-minor ({sum(1 for v in minor.values() if v == 0)}): "
        f"{' '.join(c for c, v in minor.items() if v == 0)}"
    )
    print(
        f"# three-minor ({sum(1 for v in minor.values() if v == 3)}): "
        f"{' '.join(c for c, v in minor.items() if v == 3)}"
    )
    print(
        f"# four-minor ({sum(1 for v in minor.values() if v == 4)}): "
        f"{' '.join(c for c, v in minor.items() if v == 4)}"
    )

    en = _load_clrd_currencies(EN_CURRENCIES)
    es = _load_clrd_currencies(ES_CURRENCIES)

    symbol_map: dict[str, set[str]] = {}
    for code in codes:
        for sym in _symbol_forms(code, en, es):
            symbol_map.setdefault(sym, set()).add(code)

    symbols_sorted = sorted(symbol_map)
    qualified = [s for s in symbols_sorted if _is_qualified(s)]
    bare = [s for s in symbols_sorted if not _is_qualified(s)]
    tokens = sorted(qualified, key=lambda s: (-len(s), s)) + sorted(
        bare, key=lambda s: (-len(s), s)
    )

    print(
        f"# {len(symbol_map)} distinct symbol forms "
        f"({len(qualified)} qualified, {len(bare)} bare)"
    )

    # --- iso4217_list_one.py -------------------------------------------------
    print("\n===== iso4217_list_one.py =====")
    print('"""ISO 4217 List One snapshot data: currency codes and minor units.')
    print()
    print("Source: ISO 4217 List One (https://www.six-group.com/en/products-services/")
    print(
        "        financial-services/data-standards.html), snapshot published "
        "2026-01-01."
    )
    print()
    print("CURRENCY_CODES holds the 165 codes with a numeric minor-unit exponent;")
    print('the 13 codes whose CcyMnrUnts is "N.A." (XAG XAU XBA XBB XBC XBD XDR')
    print("XPD XPT XSU XTS XUA XXX) are excluded: they have no usable minor units.")
    print("MINOR_UNITS maps each code to its exponent (2 for most, 0 for")
    print("JPY/KRW/..., 3 for BHD/..., 4 for CLF/UYW).")
    print('"""')
    print()
    print("from __future__ import annotations")
    print()
    print("CURRENCY_CODES: frozenset[str] = frozenset(")
    print("    {")
    for code in codes:
        print(f'        "{code}",')
    print("    }")
    print(")")
    print()
    print("MINOR_UNITS: dict[str, int] = {")
    for c in codes:
        print(f'    "{c}": {minor[c]},')
    print("}")

    # --- cldr_currencies.py --------------------------------------------------
    print("\n===== cldr_currencies.py =====")
    print('"""Unicode CLDR currency symbol and display-name lookup tables.')
    print()
    print("Source: Unicode CLDR v47 (https://cldr.unicode.org/), English + Spanish")
    print("currency data (symbols/symbol-alt-narrow and display names).")
    print()
    print("SYMBOL_TO_CODES maps each symbol form to the sorted tuple of ISO 4217")
    print('codes whose CLDR data uses it ("$" -> the 29 dollar-family codes,')
    print('"US$" -> ("USD",), "\\u00a5" -> ("CNY", "JPY")). Symbols that equal')
    print("the code itself, contain whitespace, or are 3-letter uppercase code")
    print("lookalikes are omitted (CLDR code fallbacks).")
    print("NAME_TO_CODES maps curated English currency words to their canonical")
    print('ISO 4217 code ("Dollar" -> ("USD",), "Euro" -> ("EUR",),')
    print('"Ringgit" -> ("MYR",)).')
    print('"""')
    print()
    print("from __future__ import annotations")
    print()
    print("SYMBOL_TO_CODES: dict[str, tuple[str, ...]] = {")
    sym_items = [(s, tuple(sorted(symbol_map[s]))) for s in symbols_sorted]
    print(_emit_dict(sym_items))
    print("}")
    print()

    # NAME_TO_CODES curated table (complete inline)
    name_items = [
        ("Afghani", ("AFN",)),
        ("Baht", ("THB",)),
        ("Bolivar", ("VES",)),
        ("Boliviano", ("BOB",)),
        ("Cedi", ("GHS",)),
        ("Colon", ("CRC",)),
        ("Cordoba", ("NIO",)),
        ("Dinar", ("KWD",)),
        ("Dirham", ("AED",)),
        ("Dollar", ("USD",)),
        ("Dong", ("VND",)),
        ("Dram", ("AMD",)),
        ("Euro", ("EUR",)),
        ("Florin", ("AWG",)),
        ("Forint", ("HUF",)),
        ("Franc", ("CHF",)),
        ("Guarani", ("PYG",)),
        ("Hryvnia", ("UAH",)),
        ("Kina", ("PGK",)),
        ("Kip", ("LAK",)),
        ("Koruna", ("CZK",)),
        ("Krona", ("SEK",)),
        ("Krone", ("NOK",)),
        ("Kwacha", ("MWK",)),
        ("Kyat", ("MMK",)),
        ("Lari", ("GEL",)),
        ("Lempira", ("HNL",)),
        ("Leu", ("RON",)),
        ("Lev", ("BGN",)),
        ("Lilangeni", ("SZL",)),
        ("Lira", ("TRY",)),
        ("Manat", ("AZN",)),
        ("Mark", ("BAM",)),
        ("Nakfa", ("ERN",)),
        ("Naira", ("NGN",)),
        ("Pataca", ("MOP",)),
        ("Peso", ("MXN",)),
        ("Pound", ("GBP",)),
        ("Pula", ("BWP",)),
        ("Quetzal", ("GTQ",)),
        ("Rand", ("ZAR",)),
        ("Real", ("BRL",)),
        ("Rial", ("IRR",)),
        ("Riel", ("KHR",)),
        ("Ringgit", ("MYR",)),
        ("Riyal", ("SAR",)),
        ("Ruble", ("RUB",)),
        ("Rufiyaa", ("MVR",)),
        ("Rupee", ("INR",)),
        ("Rupiah", ("IDR",)),
        ("Shekel", ("ILS",)),
        ("Sol", ("PEN",)),
        ("Som", ("KGS",)),
        ("Somoni", ("TJS",)),
        ("Taka", ("BDT",)),
        ("Tala", ("WST",)),
        ("Tenge", ("KZT",)),
        ("Tugrik", ("MNT",)),
        ("Vatu", ("VUV",)),
        ("Won", ("KRW",)),
        ("Yen", ("JPY",)),
        ("Yuan", ("CNY",)),
        ("Zloty", ("PLN",)),
    ]
    print("NAME_TO_CODES: dict[str, tuple[str, ...]] = {")
    print(_emit_dict(name_items))
    print("}")

    # --- currency_symbols.py --------------------------------------------------
    print("\n===== currency_symbols.py =====")
    print('"""Currency symbol recognition keys (grammar data).')
    print()
    print("Source: keys of SYMBOL_TO_CODES in paxman/capabilities/Money/rules/data/")
    print("cldr_currencies.py (Unicode CLDR v47, en + es).")
    print()
    print("Qualified symbols (containing an ASCII letter, e.g. US$, CA$, RM) are")
    print("ordered before bare symbols ($, \\u00a5, \\u20ac), longest first within")
    print('each class, so the grammar alternates "US$" before "$".')
    print('"""')
    print()
    print("from __future__ import annotations")
    print()
    print("SYMBOL_TOKENS: tuple[str, ...] = (")
    print(_emit_set(tokens))
    print(")")

    # --- currency_words.py -----------------------------------------------------
    print("\n===== currency_words.py =====")
    print('"""English currency word recognition keys (grammar data).')
    print()
    print("Source: keys of NAME_TO_CODES in paxman/capabilities/Money/rules/data/")
    print("cldr_currencies.py (Unicode CLDR v47 English display names).")
    print()
    print("Ordered longest-first so the grammar alternates multi-word names")
    print("before their shorter tails when present.")
    print('"""')
    print()
    print("from __future__ import annotations")
    print()
    word_tokens = sorted(name_items, key=lambda kv: (-len(kv[0]), kv[0]))
    print("WORD_TOKENS: tuple[str, ...] = (")
    print(_emit_set([w for w, _ in word_tokens]))
    print(")")


if __name__ == "__main__":
    main()
```

Sanity-check the script output before pasting: the summary lines must read `# 165 in-scope codes, 165 minor-unit entries`, `# zero-minor (17): BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX UYI VND VUV XAF XOF XPF`, `# three-minor (7): BHD IQD JOD KWD LYD OMR TND`, `# four-minor (2): CLF UYW`, and `# 67 distinct symbol forms (40 qualified, 27 bare)`.

- [ ] **Step 4: GREEN — write `paxman/capabilities/Money/rules/data/iso4217_list_one.py`**

Complete content (matches the script's `===== iso4217_list_one.py =====` section; reproduced here in full because the count tests lock every entry):

```python
"""ISO 4217 List One snapshot data: currency codes and minor units.

Source: ISO 4217 List One (https://www.six-group.com/en/products-services/
        financial-services/data-standards.html), snapshot published 2026-01-01.

CURRENCY_CODES holds the 165 codes with a numeric minor-unit exponent;
the 13 codes whose CcyMnrUnts is "N.A." (XAG XAU XBA XBB XBC XBD XDR
XPD XPT XSU XTS XUA XXX) are excluded: they have no usable minor units.
MINOR_UNITS maps each code to its exponent (2 for most, 0 for
JPY/KRW/..., 3 for BHD/..., 4 for CLF/UYW).
"""

from __future__ import annotations

CURRENCY_CODES: frozenset[str] = frozenset(
    {
        "AED",
        "AFN",
        "ALL",
        "AMD",
        "AOA",
        "ARS",
        "AUD",
        "AWG",
        "AZN",
        "BAM",
        "BBD",
        "BDT",
        "BHD",
        "BIF",
        "BMD",
        "BND",
        "BOB",
        "BOV",
        "BRL",
        "BSD",
        "BTN",
        "BWP",
        "BYN",
        "BZD",
        "CAD",
        "CDF",
        "CHE",
        "CHF",
        "CHW",
        "CLF",
        "CLP",
        "CNY",
        "COP",
        "COU",
        "CRC",
        "CUP",
        "CVE",
        "CZK",
        "DJF",
        "DKK",
        "DOP",
        "DZD",
        "EGP",
        "ERN",
        "ETB",
        "EUR",
        "FJD",
        "FKP",
        "GBP",
        "GEL",
        "GHS",
        "GIP",
        "GMD",
        "GNF",
        "GTQ",
        "GYD",
        "HKD",
        "HNL",
        "HTG",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "IQD",
        "IRR",
        "ISK",
        "JMD",
        "JOD",
        "JPY",
        "KES",
        "KGS",
        "KHR",
        "KMF",
        "KPW",
        "KRW",
        "KWD",
        "KYD",
        "KZT",
        "LAK",
        "LBP",
        "LKR",
        "LRD",
        "LSL",
        "LYD",
        "MAD",
        "MDL",
        "MGA",
        "MKD",
        "MMK",
        "MNT",
        "MOP",
        "MRU",
        "MUR",
        "MVR",
        "MWK",
        "MXN",
        "MXV",
        "MYR",
        "MZN",
        "NAD",
        "NGN",
        "NIO",
        "NOK",
        "NPR",
        "NZD",
        "OMR",
        "PAB",
        "PEN",
        "PGK",
        "PHP",
        "PKR",
        "PLN",
        "PYG",
        "QAR",
        "RON",
        "RSD",
        "RUB",
        "RWF",
        "SAR",
        "SBD",
        "SCR",
        "SDG",
        "SEK",
        "SGD",
        "SHP",
        "SLE",
        "SOS",
        "SRD",
        "SSP",
        "STN",
        "SVC",
        "SYP",
        "SZL",
        "THB",
        "TJS",
        "TMT",
        "TND",
        "TOP",
        "TRY",
        "TTD",
        "TWD",
        "TZS",
        "UAH",
        "UGX",
        "USD",
        "USN",
        "UYI",
        "UYU",
        "UYW",
        "UZS",
        "VED",
        "VES",
        "VND",
        "VUV",
        "WST",
        "XAD",
        "XAF",
        "XCD",
        "XCG",
        "XOF",
        "XPF",
        "YER",
        "ZAR",
        "ZMW",
        "ZWG",
    }
)

MINOR_UNITS: dict[str, int] = {
    "AED": 2,
    "AFN": 2,
    "ALL": 2,
    "AMD": 2,
    "AOA": 2,
    "ARS": 2,
    "AUD": 2,
    "AWG": 2,
    "AZN": 2,
    "BAM": 2,
    "BBD": 2,
    "BDT": 2,
    "BHD": 3,
    "BIF": 0,
    "BMD": 2,
    "BND": 2,
    "BOB": 2,
    "BOV": 2,
    "BRL": 2,
    "BSD": 2,
    "BTN": 2,
    "BWP": 2,
    "BYN": 2,
    "BZD": 2,
    "CAD": 2,
    "CDF": 2,
    "CHE": 2,
    "CHF": 2,
    "CHW": 2,
    "CLF": 4,
    "CLP": 0,
    "CNY": 2,
    "COP": 2,
    "COU": 2,
    "CRC": 2,
    "CUP": 2,
    "CVE": 2,
    "CZK": 2,
    "DJF": 0,
    "DKK": 2,
    "DOP": 2,
    "DZD": 2,
    "EGP": 2,
    "ERN": 2,
    "ETB": 2,
    "EUR": 2,
    "FJD": 2,
    "FKP": 2,
    "GBP": 2,
    "GEL": 2,
    "GHS": 2,
    "GIP": 2,
    "GMD": 2,
    "GNF": 0,
    "GTQ": 2,
    "GYD": 2,
    "HKD": 2,
    "HNL": 2,
    "HTG": 2,
    "HUF": 2,
    "IDR": 2,
    "ILS": 2,
    "INR": 2,
    "IQD": 3,
    "IRR": 2,
    "ISK": 0,
    "JMD": 2,
    "JOD": 3,
    "JPY": 0,
    "KES": 2,
    "KGS": 2,
    "KHR": 2,
    "KMF": 0,
    "KPW": 2,
    "KRW": 0,
    "KWD": 3,
    "KYD": 2,
    "KZT": 2,
    "LAK": 2,
    "LBP": 2,
    "LKR": 2,
    "LRD": 2,
    "LSL": 2,
    "LYD": 3,
    "MAD": 2,
    "MDL": 2,
    "MGA": 2,
    "MKD": 2,
    "MMK": 2,
    "MNT": 2,
    "MOP": 2,
    "MRU": 2,
    "MUR": 2,
    "MVR": 2,
    "MWK": 2,
    "MXN": 2,
    "MXV": 2,
    "MYR": 2,
    "MZN": 2,
    "NAD": 2,
    "NGN": 2,
    "NIO": 2,
    "NOK": 2,
    "NPR": 2,
    "NZD": 2,
    "OMR": 3,
    "PAB": 2,
    "PEN": 2,
    "PGK": 2,
    "PHP": 2,
    "PKR": 2,
    "PLN": 2,
    "PYG": 0,
    "QAR": 2,
    "RON": 2,
    "RSD": 2,
    "RUB": 2,
    "RWF": 0,
    "SAR": 2,
    "SBD": 2,
    "SCR": 2,
    "SDG": 2,
    "SEK": 2,
    "SGD": 2,
    "SHP": 2,
    "SLE": 2,
    "SOS": 2,
    "SRD": 2,
    "SSP": 2,
    "STN": 2,
    "SVC": 2,
    "SYP": 2,
    "SZL": 2,
    "THB": 2,
    "TJS": 2,
    "TMT": 2,
    "TND": 3,
    "TOP": 2,
    "TRY": 2,
    "TTD": 2,
    "TWD": 2,
    "TZS": 2,
    "UAH": 2,
    "UGX": 0,
    "USD": 2,
    "USN": 2,
    "UYI": 0,
    "UYU": 2,
    "UYW": 4,
    "UZS": 2,
    "VED": 2,
    "VES": 2,
    "VND": 0,
    "VUV": 0,
    "WST": 2,
    "XAD": 2,
    "XAF": 0,
    "XCD": 2,
    "XCG": 2,
    "XOF": 0,
    "XPF": 0,
    "YER": 2,
    "ZAR": 2,
    "ZMW": 2,
    "ZWG": 2,
}
```

- [ ] **Step 5: GREEN — write `paxman/capabilities/Money/rules/data/cldr_currencies.py`**

The block below is an **excerpt** (a subset of the full tables — 16 of the 67 `SYMBOL_TO_CODES` keys, 5 of the 62 `NAME_TO_CODES` keys). The COMPLETE module body is the script's `===== cldr_currencies.py =====` section (Step 3) — that output is authoritative. The module has the exact shape below: docstring + `from __future__ import annotations` + the `SYMBOL_TO_CODES` dict (67 keys, one entry per line, keys sorted, the 29-code `"$"` row wrapped one code per line) + the `NAME_TO_CODES` dict (62 keys, one entry per line). The excerpted rows shown are the brief-anchored and D6-critical mappings — spot-check the script output against these (note BHD/AED have NO symbol row: their CLDR symbol is the code itself, filtered as a code fallback):

```python
"""Unicode CLDR currency symbol and display-name lookup tables.

Source: Unicode CLDR v47 (https://cldr.unicode.org/), English + Spanish
currency data (symbols/symbol-alt-narrow and display names).

SYMBOL_TO_CODES maps each symbol form to the sorted tuple of ISO 4217
codes whose CLDR data uses it ("$" -> the 29 dollar-family codes,
"US$" -> ("USD",), "\u00a5" -> ("CNY", "JPY")). Symbols that equal
the code itself, contain whitespace, or are 3-letter uppercase code
lookalikes are omitted (CLDR code fallbacks).
NAME_TO_CODES maps curated English currency words to their canonical
ISO 4217 code ("Dollar" -> ("USD",), "Euro" -> ("EUR",),
"Ringgit" -> ("MYR",)).
"""

from __future__ import annotations

SYMBOL_TO_CODES: dict[str, tuple[str, ...]] = {
    "$": (
        "ARS",
        "AUD",
        "BBD",
        "BMD",
        "BND",
        "BSD",
        "BZD",
        "CAD",
        "CLP",
        "COP",
        "CUP",
        "DOP",
        "FJD",
        "GYD",
        "HKD",
        "JMD",
        "KYD",
        "LRD",
        "MXN",
        "NAD",
        "NZD",
        "SBD",
        "SGD",
        "SRD",
        "TTD",
        "TWD",
        "USD",
        "UYU",
        "XCD",
    ),
    "A$": ("AUD",),
    "C$": ("NIO",),
    "CA$": ("CAD",),
    "CFPF": ("XPF",),
    "K": ("MMK",),
    "L": ("HNL", "RON"),
    "RM": ("MYR",),
    "Rs": ("LKR", "MUR", "NPR", "PKR"),
    "US$": ("USD",),
    "kr": ("DKK", "ISK", "NOK", "SEK"),
    "£": ("FKP", "GBP", "GIP", "SHP", "SSP", "SYP"),
    "¥": ("CNY", "JPY"),
    "€": ("EUR",),
    "₩": ("KPW", "KRW"),
    "₽": ("RUB",),
}

NAME_TO_CODES: dict[str, tuple[str, ...]] = {
    "Dollar": ("USD",),
    "Euro": ("EUR",),
    "Franc": ("CHF",),
    "Peso": ("MXN",),
    "Ringgit": ("MYR",),
}
```

**Formatting rule (ruff, verified):** one dict entry per line with a trailing comma; any value tuple that does not fit on the entry line (only `"$"`) is wrapped with ONE code per continuation line and the closing `)` on its own line. Entries that fit (up to 6 codes, e.g. `"£"`) stay inline. The `"$"` row is FIRST — keys are sorted, and `$` (U+0024) sorts before `A`.

- [ ] **Step 6: GREEN — write `paxman/capabilities/Money/grammar/data/currency_symbols.py` and `paxman/capabilities/Money/grammar/data/currency_words.py`**

Complete content for both (matches the script's `===== currency_symbols.py =====` and `===== currency_words.py =====` sections; reproduced here in full because the D4 ordering tests lock every position). `SYMBOL_TOKENS` is the 67 keys of `SYMBOL_TO_CODES`, qualified (contains an ASCII letter) first, then bare, longest-first within each class — so the grammar alternates `"US$"` before `"$"`. `WORD_TOKENS` is the 62 keys of `NAME_TO_CODES`, longest-first:

```python
# paxman/capabilities/Money/grammar/data/currency_symbols.py
"""Currency symbol recognition keys (grammar data).

Source: keys of SYMBOL_TO_CODES in paxman/capabilities/Money/rules/data/
cldr_currencies.py (Unicode CLDR v47, en + es).

Qualified symbols (containing an ASCII letter, e.g. US$, CA$, RM) are
ordered before bare symbols ($, \u00a5, \u20ac), longest first within
each class, so the grammar alternates "US$" before "$".
"""

from __future__ import annotations

SYMBOL_TOKENS: tuple[str, ...] = (
    "CFPF",
    "FCFA",
    "CA$",
    "CN¥",
    "Cg.",
    "EC$",
    "GH₵",
    "HK$",
    "MX$",
    "NT$",
    "NZ$",
    "US$",
    "lei",
    "A$",
    "Ar",
    "Bs",
    "C$",
    "CF",
    "Db",
    "E£",
    "FG",
    "Ft",
    "KM",
    "Kz",
    "Kč",
    "L£",
    "R$",
    "RF",
    "RM",
    "Rp",
    "Rs",
    "T$",
    "ZK",
    "kr",
    "zł",
    "K",
    "L",
    "P",
    "Q",
    "R",
    "р.",
    "$",
    "£",
    "¥",
    "֏",
    "؋",
    "৳",
    "฿",
    "៛",
    "₡",
    "₦",
    "₩",
    "₪",
    "₫",
    "€",
    "₭",
    "₮",
    "₱",
    "₲",
    "₴",
    "₸",
    "₹",
    "₺",
    "₼",
    "₽",
    "₾",
    "⃀",
)
```

```python
# paxman/capabilities/Money/grammar/data/currency_words.py
"""English currency word recognition keys (grammar data).

Source: keys of NAME_TO_CODES in paxman/capabilities/Money/rules/data/
cldr_currencies.py (Unicode CLDR v47 English display names).

Ordered longest-first so the grammar alternates multi-word names
before their shorter tails when present.
"""

from __future__ import annotations

WORD_TOKENS: tuple[str, ...] = (
    "Boliviano",
    "Lilangeni",
    "Afghani",
    "Bolivar",
    "Cordoba",
    "Guarani",
    "Hryvnia",
    "Lempira",
    "Quetzal",
    "Ringgit",
    "Rufiyaa",
    "Dirham",
    "Dollar",
    "Florin",
    "Forint",
    "Koruna",
    "Kwacha",
    "Pataca",
    "Rupiah",
    "Shekel",
    "Somoni",
    "Tugrik",
    "Colon",
    "Dinar",
    "Franc",
    "Krona",
    "Krone",
    "Manat",
    "Naira",
    "Nakfa",
    "Pound",
    "Riyal",
    "Ruble",
    "Rupee",
    "Tenge",
    "Zloty",
    "Baht",
    "Cedi",
    "Dong",
    "Dram",
    "Euro",
    "Kina",
    "Kyat",
    "Lari",
    "Lira",
    "Mark",
    "Peso",
    "Pula",
    "Rand",
    "Real",
    "Rial",
    "Riel",
    "Taka",
    "Tala",
    "Vatu",
    "Yuan",
    "Kip",
    "Leu",
    "Lev",
    "Sol",
    "Som",
    "Won",
    "Yen",
)
```

**Cross-module consistency (locked by the tests):** `set(SYMBOL_TOKENS) == set(SYMBOL_TO_CODES)` and `set(WORD_TOKENS) == set(NAME_TO_CODES)` — every shipped recognition key resolves through a rule-data mapping (the grammar/rule data boundary invariant, mirroring `draft_test_data_consistency.py` which a later part ships for the pipeline level). Every code in every `SYMBOL_TO_CODES` / `NAME_TO_CODES` value is in `CURRENCY_CODES` (165), so no recognition key can resolve to a code the ISO rule rejects.

- [ ] **Step 7: Run the tests to verify they pass**

Run: `uv run pytest tests/capabilities/money/test_data.py -v`
Expected: PASS — `23 passed` (ISO tables ×7, CLDR tables ×11, symbol tokens ×3, word tokens ×2).

- [ ] **Step 8: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_data.py
uv run ruff check paxman/capabilities/Money tests/capabilities/money
uv run ruff format --check paxman/capabilities/Money tests/capabilities/money
uv run pyright paxman/capabilities/Money/rules/data paxman/capabilities/Money/grammar/data
```

Expected: pytest green (23 passed); ruff clean (line-length 88); ruff format clean (the data tables are one-item-per-line, the sanctioned data-table style — `nanp_tables.py` precedent for the `frozenset(\n    {...}\n)` form); pyright strict clean (plain module-level constants — no `# type: ignore` / `# noqa` / `# pyright: ignore` anywhere).

Remove the temporary derivation script, then stage ONLY the five files created in this task (the script and `/tmp/opencode/*` are never committed):

```bash
rm tools/derive_currency_tables.py
git add paxman/capabilities/Money/rules/data/iso4217_list_one.py
git add paxman/capabilities/Money/rules/data/cldr_currencies.py
git add paxman/capabilities/Money/grammar/data/currency_symbols.py
git add paxman/capabilities/Money/grammar/data/currency_words.py
git add tests/capabilities/money/test_data.py
git commit -m "feat(money): add currency data tables"
```

### Task 4: Validation rules

**Files:**
- Create: `paxman/capabilities/Money/rules/iso_4217_ed2015.py`
- Create: `paxman/capabilities/Money/rules/cldr_currencies_ed2025.py`
- Create: `tests/capabilities/money/test_rules.py`

**Dependency note (cross-part contract):** the rules import `MoneyNotation`/`MoneyContract` (scaffolding), `parse_amount`/`format_amount`/`ParsedAmount` (parsing helper), and the `CURRENCY_CODES`/`MINOR_UNITS`/`SYMBOL_TO_CODES`/`NAME_TO_CODES` tables (Task 3 data modules) — all exist before this task executes in the assembled plan. The tests construct `MoneyContract(...)` directly, mirroring exactly how `tests/capabilities/country/test_rules.py` constructs `CountryContract()` (rule-level tests never need the `create_contract` factory).

- [ ] **Step 1: RED — write the rule tests** (`tests/capabilities/money/test_rules.py`, module-level `pytestmark = [pytest.mark.capability]`, per-rule classes with `setup_method`, `@pytest.mark.parametrize` for canonical-output groups)

```python
"""Tests for Money capability validation rules."""

from __future__ import annotations

import pytest

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.rules.cldr_currencies_ed2025 import (
    SectionNames,
    SectionSymbols,
)
from paxman.capabilities.Money.rules.iso_4217_ed2015 import SectionCode
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]


def _notation(
    currency_part: str,
    amount_part: str,
    currency_shape: str,
    amount_shape: str = "integer",
) -> MoneyNotation:
    """Build a MoneyNotation directly (no grammar) for rule-level testing."""
    return MoneyNotation(
        currency_part=currency_part,
        amount_part=amount_part,
        currency_shape=currency_shape,
        amount_shape=amount_shape,
    )


class TestSectionCode:
    """Tests for SectionCode rule."""

    def setup_method(self) -> None:
        self.rule = SectionCode()

    def test_matches_valid_code(self) -> None:
        """Happy path: known code + integer amount matches."""
        contract = MoneyContract()
        notation = _notation("USD", "500", "code")
        assert self.rule.matches(notation, contract) is True

    @pytest.mark.parametrize(
        ("currency_part", "amount_part", "amount_shape", "expected"),
        [
            ("USD", "500", "integer", "USD 500.00"),
            ("JPY", "500", "integer", "JPY 500"),
            ("BHD", "500", "integer", "BHD 500.000"),
            ("EUR", "500.50", "dot_decimal", "EUR 500.50"),
        ],
    )
    def test_normalize_pads_to_minor_units(
        self,
        currency_part: str,
        amount_part: str,
        amount_shape: str,
        expected: str,
    ) -> None:
        """Canonical output pads the amount to the code's minor units (D2)."""
        contract = MoneyContract()
        notation = _notation(currency_part, amount_part, "code", amount_shape)
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == expected

    def test_rejects_unknown_code(self) -> None:
        """Unknown code XYZ is not in the ISO 4217 List One table."""
        contract = MoneyContract()
        notation = _notation("XYZ", "500", "code")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_lowercase_code(self) -> None:
        """Lowercase 'usd' is not in the uppercase CURRENCY_CODES table."""
        contract = MoneyContract()
        notation = _notation("usd", "500", "code")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """A symbol-shaped notation is not validated by the code rule."""
        contract = MoneyContract()
        notation = _notation("USD", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_non_digit_amount(self) -> None:
        """An amount with no digits fails parse_amount (defensive path)."""
        contract = MoneyContract()
        notation = _notation("USD", "abc", "code")
        assert self.rule.matches(notation, contract) is False

    def test_strict_rejects_over_precision(self) -> None:
        """USD 500.123 exceeds the 2 minor units: INVALID in strict mode."""
        contract = MoneyContract()
        notation = _notation("USD", "500.123", "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is False

    def test_strict_rejects_jpy_fraction(self) -> None:
        """JPY has 0 minor units; 500.5 is over-precision in strict mode."""
        contract = MoneyContract()
        notation = _notation("JPY", "500.5", "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is False

    @pytest.mark.parametrize(
        ("amount_part", "expected"),
        [
            ("500.5", "JPY 500"),
            ("2.5", "JPY 2"),
            ("3.5", "JPY 4"),
        ],
    )
    def test_round_precision_half_to_even(
        self, amount_part: str, expected: str
    ) -> None:
        """precision=round rounds half-to-even: 2.5 to 2, 3.5 to 4 (D2)."""
        contract = MoneyContract(precision="round")
        notation = _notation("JPY", amount_part, "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == expected

    def test_truncate_precision_drops_excess_digits(self) -> None:
        """precision=truncate drops digits past the minor unit (D2)."""
        contract = MoneyContract(precision="truncate")
        notation = _notation("USD", "500.999", "code", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 500.99"

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, kind, year, lifecycle, version."""
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 4217"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.publication_year == 2015
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.version is None

    def test_rule_name(self) -> None:
        """Verify name follows the Section-{description} convention (Country style)."""
        assert self.rule.name == "Section-codes"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_target_grammars(self) -> None:
        """The code rule targets only the code grammar."""
        assert self.rule.target_grammars == frozenset({"code_recognition"})

    def test_requires_features_empty(self) -> None:
        """The ISO rule never gates on contract features (always runs)."""
        assert self.rule.requires_features == frozenset()


class TestSectionSymbols:
    """Tests for SectionSymbols rule."""

    def setup_method(self) -> None:
        self.rule = SectionSymbols()

    def test_qualified_symbol_definitive(self) -> None:
        """US$ is a qualified symbol mapped definitively to USD."""
        contract = MoneyContract()
        notation = _notation("US$", "50.79", "qualified_symbol", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 50.79"

    def test_qualified_symbol_never_remapped(self) -> None:
        """A definitive qualified symbol ignores dollar_sign_currency (D3)."""
        contract = MoneyContract(dollar_sign_currency="CAD")
        notation = _notation("US$", "50.79", "qualified_symbol", "dot_decimal")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 50.79"

    def test_bare_symbol_resolves_via_dollar_sign_currency(self) -> None:
        """Bare $ with dollar_sign_currency=USD resolves to USD (D3)."""
        contract = MoneyContract(dollar_sign_currency="USD")
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 500.00"

    def test_bare_symbol_dollar_sign_currency_cad(self) -> None:
        """Bare $ with dollar_sign_currency=CAD resolves to CAD (D3)."""
        contract = MoneyContract(dollar_sign_currency="CAD")
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "CAD 500.00"

    def test_bare_symbol_no_dollar_sign_currency_invalid(self) -> None:
        """Bare $ with dollar_sign_currency=None is INVALID, never dropped (D3)."""
        contract = MoneyContract(dollar_sign_currency=None)
        notation = _notation("$", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_definitive_symbol_without_dollar_sign_currency(self) -> None:
        """Euro sign is definitive (EUR) and needs no dollar_sign_currency (D3)."""
        contract = MoneyContract(dollar_sign_currency=None)
        notation = _notation("\u20ac", "5", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 5.00"

    def test_definitive_symbol_default_contract(self) -> None:
        """Euro sign with the default contract (dollar_sign_currency=None) still resolves to EUR (D3)."""
        contract = MoneyContract()
        notation = _notation("\u20ac", "5", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 5.00"

    def test_multi_candidate_symbol_dollar_sign_currency(self) -> None:
        """Yen sign (multi-candidate) resolves via dollar_sign_currency (D3)."""
        contract = MoneyContract(dollar_sign_currency="JPY")
        notation = _notation("\u00a5", "500", "symbol")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "JPY 500"

    def test_strict_over_precision_through_symbol(self) -> None:
        """Euro 5.555 exceeds EUR's 2 minor units: INVALID in strict mode."""
        contract = MoneyContract()
        notation = _notation("\u20ac", "5.555", "symbol", "dot_decimal")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """A code-shaped notation is not validated by the symbol rule."""
        contract = MoneyContract()
        notation = _notation("$", "500", "code")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_unknown_symbol(self) -> None:
        """An unknown symbol token is not in SYMBOL_TO_CODES."""
        contract = MoneyContract()
        notation = _notation("\u20ac\u00a3", "500", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, kind, year, lifecycle, version."""
        assert self.rule.provenance.authority == "Unicode CLDR"
        assert self.rule.provenance.specification_name == "Unicode CLDR"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.publication_year == 2025
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.version == "47"

    def test_rule_name(self) -> None:
        """Verify name follows the Section-{description} convention (Country style)."""
        assert self.rule.name == "Section-symbols"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_target_grammars(self) -> None:
        """The symbol rule targets only the symbol grammar."""
        assert self.rule.target_grammars == frozenset({"symbol_recognition"})

    def test_requires_features_empty(self) -> None:
        """Never gate on dollar_sign_currency: bare $ yields INVALID, not MISSING."""
        assert self.rule.requires_features == frozenset()


class TestSectionNames:
    """Tests for SectionNames rule."""

    def setup_method(self) -> None:
        self.rule = SectionNames()

    def test_definitive_word_dollar(self) -> None:
        """Dollar is a definitive display name for USD."""
        contract = MoneyContract()
        notation = _notation("Dollar", "18", "word")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "USD 18.00"

    def test_definitive_word_euro(self) -> None:
        """Euro resolves to EUR regardless of dollar_sign_currency (D3)."""
        contract = MoneyContract()
        notation = _notation("Euro", "5", "word")
        assert self.rule.matches(notation, contract) is True
        assert self.rule.normalize(notation, contract) == "EUR 5.00"

    def test_rejects_unknown_word(self) -> None:
        """Zorkmids is not a CLDR currency display name."""
        contract = MoneyContract()
        notation = _notation("Zorkmids", "18", "word")
        assert self.rule.matches(notation, contract) is False

    def test_rejects_wrong_shape(self) -> None:
        """A symbol-shaped notation is not validated by the word rule."""
        contract = MoneyContract()
        notation = _notation("Euro", "5", "symbol")
        assert self.rule.matches(notation, contract) is False

    def test_provenance_attributes(self) -> None:
        """Verify authority, spec name, kind, year, lifecycle, version."""
        assert self.rule.provenance.authority == "Unicode CLDR"
        assert self.rule.provenance.specification_name == "Unicode CLDR"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.publication_year == 2025
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.version == "47"

    def test_rule_name(self) -> None:
        """Verify name follows the Section-{description} convention (Country style)."""
        assert self.rule.name == "Section-names"

    def test_strategy(self) -> None:
        """Verify the rule strategy enum."""
        assert self.rule.strategy == RuleStrategy.LOOKUP_TABLE

    def test_target_grammars(self) -> None:
        """The word rule targets only the word grammar."""
        assert self.rule.target_grammars == frozenset({"word_recognition"})

    def test_requires_features_empty(self) -> None:
        """The CLDR name rule never gates on contract features."""
        assert self.rule.requires_features == frozenset()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/capabilities/money/test_rules.py -v`
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'paxman.capabilities.Money.rules.iso_4217_ed2015'` (plus a second `ModuleNotFoundError` for `cldr_currencies_ed2025`), because neither rule module exists yet.

- [ ] **Step 3: GREEN — implement `paxman/capabilities/Money/rules/iso_4217_ed2015.py`**

Mirror the Phone E.164 shape: module-level `PUBLICATION` provenance, a module-level shared validator, and a `Rule[MoneyNotation]` subclass declaring all six metadata attributes. The strategy is `LOOKUP_TABLE` (the code is validated by table membership, exactly like `SectionAlpha2Codes`); the amount parse is a helper, not the strategy. `matches()` never raises; `normalize()` falls back to the raw amount part on the unreachable parse failure, like the Phone rules' defensive best-effort.

```python
"""ISO 4217:2015 rule: currency code validation.

ISO 4217 assigns alpha-3 currency codes and the minor-unit exponent for
each currency. This rule validates the code against the List One table
and, in strict precision mode, rejects amounts with more decimal digits
than the code's minor units.
"""

from __future__ import annotations

from typing import cast

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.parsing import (
    ParsedAmount,
    format_amount,
    parse_amount,
)
from paxman.capabilities.Money.rules.data.iso4217_list_one import (
    CURRENCY_CODES,
    MINOR_UNITS,
)
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 4217",
    kind="specification",
    reference_url="https://www.iso.org/iso-4217-currency-codes.html",
    version=None,
    lifecycle="active",
    publication_year=2015,
)


def _valid_amount(
    parsed: ParsedAmount,
    code: str,
    contract: MoneyContract,
) -> bool:
    """Strict over-precision check: the amount may not exceed the minor units.

    Args:
        parsed: Parsed amount to check.
        code: ISO 4217 currency code (guaranteed present in MINOR_UNITS
            because matches() already rejected codes outside CURRENCY_CODES).
        contract: Money contract (precision mode).

    Returns:
        True when precision is not "strict", or when the parsed amount has
        at most MINOR_UNITS[code] decimal digits.
    """
    if contract.precision == "strict" and parsed.decimal_digits() > MINOR_UNITS[code]:
        return False
    return True


class SectionCode(Rule[MoneyNotation]):
    """ISO 4217 Section: currency codes.

    Validates a "code"-shaped notation: the currency part must be an
    uppercase alpha-3 code in the ISO 4217 List One table, and the amount
    must parse and (in strict precision mode) not exceed the code's minor
    units. Lowercase codes are rejected: case folding is the grammar's
    concern, mirroring how ISBN folds x to X at recognition time.
    """

    name = "Section-codes"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "ISO 4217 currency codes"
    target_grammars = frozenset({"code_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MoneyNotation, contract: Contract) -> bool:
        """Check if the notation is a known currency code with a valid amount.

        Args:
            notation: Money notation to validate.
            contract: Contract configuration.

        Returns:
            True if shape == "code", the code is in CURRENCY_CODES, the
            amount parses, and strict precision is not exceeded.
        """
        if notation.currency_shape != "code":
            return False
        code = notation.currency_part
        if code not in CURRENCY_CODES:
            return False
        typed_contract = cast(MoneyContract, contract)
        parsed = parse_amount(notation.amount_part)
        if parsed is None:
            return False
        return _valid_amount(parsed, code, typed_contract)

    def normalize(self, notation: MoneyNotation, contract: Contract) -> str:
        """Normalize to the canonical CODE + amount form.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            "{code} {amount}" where the amount is padded, rounded, or
            truncated to the code's minor units per the contract precision.
        """
        typed_contract = cast(MoneyContract, contract)
        parsed = parse_amount(notation.amount_part)
        if parsed is None:
            return notation.amount_part  # unreachable post-matches(); defensive
        minor_units = MINOR_UNITS[notation.currency_part]
        amount = format_amount(parsed, minor_units, typed_contract.precision)
        return f"{notation.currency_part} {amount}"
```

- [ ] **Step 4: GREEN — implement `paxman/capabilities/Money/rules/cldr_currencies_ed2025.py`**

Two rules share this file because they share one publication (`PUBLICATION`), mirroring how `iso_3166_ed2024.py` co-locates rules of the same provenance. The resolution helpers encode D3: qualified symbols are definitive and never remapped; bare single-candidate symbols and definitive display names resolve to their own code; bare multi-candidate tokens resolve via the opt-in `dollar_sign_currency`; `dollar_sign_currency=None` (the default) with a bare multi-candidate token resolves to None, which makes `matches()` return False (pipeline status INVALID, never MISSING). Both rules then apply the same amount validation as `SectionCode` (parse + strict over-precision check against the resolved code's minor units), guarded so a bad `dollar_sign_currency` value cannot KeyError.

```python
"""Unicode CLDR currency rules: currency symbols and display names.

Currency symbols and display names share the CLDR publication and lookup
tables. Both rules resolve a symbol/word token to an ISO 4217 code before
applying the shared amount validation (parse + strict over-precision
check).
"""

from __future__ import annotations

from typing import cast

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.parsing import (
    ParsedAmount,
    format_amount,
    parse_amount,
)
from paxman.capabilities.Money.rules.data.cldr_currencies import (
    NAME_TO_CODES,
    SYMBOL_TO_CODES,
)
from paxman.capabilities.Money.rules.data.iso4217_list_one import MINOR_UNITS
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="Unicode CLDR",
    specification_name="Unicode CLDR",
    kind="specification",
    reference_url="https://cldr.unicode.org/",
    version="47",
    lifecycle="active",
    publication_year=2025,
)


def _resolve_symbol_code(
    notation: MoneyNotation,
    contract: MoneyContract,
) -> str | None:
    """Resolve a symbol/qualified_symbol notation to an ISO 4217 code.

    Qualified symbols (e.g. "US$") map definitively to one code and are
    never remapped. Bare symbols map to their code only when the table has
    exactly one candidate; multi-candidate symbols (e.g. "$", the yen sign)
    resolve via the opt-in ``contract.dollar_sign_currency`` (default None).
    A bare multi-candidate symbol with ``dollar_sign_currency=None``
    resolves to None, which makes matches() return False (INVALID, never
    silently dropped).

    Args:
        notation: Money notation to resolve.
        contract: Money contract (dollar_sign_currency).

    Returns:
        The resolved ISO 4217 code, or None when no code can be resolved.
    """
    codes = SYMBOL_TO_CODES.get(notation.currency_part)
    if codes is None:
        return None
    if notation.currency_shape == "qualified_symbol":
        return codes[0]
    if len(codes) == 1:
        return codes[0]
    return contract.dollar_sign_currency


def _resolve_name_code(
    notation: MoneyNotation,
    contract: MoneyContract,
) -> str | None:
    """Resolve a word notation to an ISO 4217 code (definitive or default).

    A display name with exactly one candidate is definitive and never
    remapped; a multi-candidate name resolves via the opt-in
    ``contract.dollar_sign_currency`` (None, the default, -> matches()
    False -> INVALID).

    Args:
        notation: Money notation to resolve.
        contract: Money contract (dollar_sign_currency).

    Returns:
        The resolved ISO 4217 code, or None when no code can be resolved.
    """
    codes = NAME_TO_CODES.get(notation.currency_part)
    if codes is None:
        return None
    if len(codes) == 1:
        return codes[0]
    return contract.dollar_sign_currency


def _amount_matches(
    parsed: ParsedAmount,
    code: str,
    contract: MoneyContract,
) -> bool:
    """Shared amount validation: parse result + strict over-precision check.

    The code comes from the CLDR tables or ``contract.dollar_sign_currency``;
    codes absent from MINOR_UNITS (e.g. a bad dollar_sign_currency value) are
    rejected defensively so neither this check nor normalize() can KeyError
    (rules never raise).

    Args:
        parsed: Parsed amount to check.
        code: Resolved ISO 4217 code.
        contract: Money contract (precision mode).

    Returns:
        True if the code is known and strict precision is not exceeded.
    """
    if code not in MINOR_UNITS:
        return False
    if contract.precision == "strict" and parsed.decimal_digits() > MINOR_UNITS[code]:
        return False
    return True


class SectionSymbols(Rule[MoneyNotation]):
    """CLDR Section: currency symbols.

    Validates "symbol"/"qualified_symbol" shapes. The token resolves to an
    ISO 4217 code (qualified or definitive via the table, multi-candidate
    via dollar_sign_currency), then the amount must parse and (in strict
    precision mode) not exceed that code's minor units.
    """

    name = "Section-symbols"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v47 currency symbols"
    target_grammars = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MoneyNotation, contract: Contract) -> bool:
        """Check if the notation is a valid currency symbol with a valid amount.

        Args:
            notation: Money notation to validate.
            contract: Contract configuration.

        Returns:
            True if shape is "symbol"/"qualified_symbol", a code can be
            resolved, and the amount passes the shared validation.
        """
        if notation.currency_shape not in ("symbol", "qualified_symbol"):
            return False
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_symbol_code(notation, typed_contract)
        if code is None:
            return False
        parsed = parse_amount(notation.amount_part)
        if parsed is None:
            return False
        return _amount_matches(parsed, code, typed_contract)

    def normalize(self, notation: MoneyNotation, contract: Contract) -> str:
        """Normalize to the canonical CODE + amount form.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            "{code} {amount}" where the amount is padded, rounded, or
            truncated to the resolved code's minor units.
        """
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_symbol_code(notation, typed_contract)
        parsed = parse_amount(notation.amount_part)
        if code is None or code not in MINOR_UNITS or parsed is None:
            return notation.amount_part  # unreachable post-matches(); defensive
        minor_units = MINOR_UNITS[code]
        amount = format_amount(parsed, minor_units, typed_contract.precision)
        return f"{code} {amount}"


class SectionNames(Rule[MoneyNotation]):
    """CLDR Section: currency display names.

    Validates "word" shapes. The display name resolves to an ISO 4217 code
    (definitive via the table, multi-candidate via dollar_sign_currency), then
    the amount must parse and (in strict precision mode) not exceed that
    code's minor units.
    """

    name = "Section-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v47 currency display names"
    target_grammars = frozenset({"word_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MoneyNotation, contract: Contract) -> bool:
        """Check if the notation is a valid display name with a valid amount.

        Args:
            notation: Money notation to validate.
            contract: Contract configuration.

        Returns:
            True if shape == "word", a code can be resolved, and the amount
            passes the shared validation.
        """
        if notation.currency_shape != "word":
            return False
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_name_code(notation, typed_contract)
        if code is None:
            return False
        parsed = parse_amount(notation.amount_part)
        if parsed is None:
            return False
        return _amount_matches(parsed, code, typed_contract)

    def normalize(self, notation: MoneyNotation, contract: Contract) -> str:
        """Normalize to the canonical CODE + amount form.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            "{code} {amount}" where the amount is padded, rounded, or
            truncated to the resolved code's minor units.
        """
        typed_contract = cast(MoneyContract, contract)
        code = _resolve_name_code(notation, typed_contract)
        parsed = parse_amount(notation.amount_part)
        if code is None or code not in MINOR_UNITS or parsed is None:
            return notation.amount_part  # unreachable post-matches(); defensive
        minor_units = MINOR_UNITS[code]
        amount = format_amount(parsed, minor_units, typed_contract.precision)
        return f"{code} {amount}"
```

**Semantics note (locked decisions, from the cross-part contract):**

- Symbol/name resolution never remaps a definitive mapping: qualified symbols (`US$`) and single-candidate symbols/names always resolve to their own code, ignoring `dollar_sign_currency` (D3). Only bare multi-candidate tokens (`$`, yen sign) resolve via `dollar_sign_currency` — an explicit opt-in that defaults to None.
- `dollar_sign_currency=None` (the default) plus a bare multi-candidate token makes `matches()` return False, so the pipeline reports INVALID, never MISSING. That is why all three rules declare `requires_features = frozenset()`: gating on `dollar_sign_currency` would silently drop the rule and misreport the status.
- Lowercase `usd` returns False: codes are exact-matched against the uppercase `CURRENCY_CODES` table; case folding is the grammar's job (grammars emit the currency_part token). Display names (`Dollar`, `Euro`) are exact-matched against `NAME_TO_CODES` keys.
- All failure paths return False from `matches()`; rules never raise. `MINOR_UNITS[code]` is guarded (`code not in MINOR_UNITS` returns False) so a bad `dollar_sign_currency` value cannot KeyError, and normalize() falls back to the raw amount part only on unreachable defensive paths.
- The over-precision check runs only in strict mode; `precision="round"`/`"truncate"` accept any fraction and let `format_amount` handle it.
- None of the rule modules contain the token `output_format` (the CI purity scan over `*/rules/*.py` must stay green).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/capabilities/money/test_rules.py -v`
Expected: PASS — all tests green (three classes, ~40 tests).

- [ ] **Step 6: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_rules.py
uv run ruff check paxman/capabilities/Money tests/capabilities/money
uv run pyright paxman/capabilities/Money/rules
```

Expected: pytest green; ruff clean; pyright strict clean (no `# type: ignore` / `# noqa` / `# pyright: ignore` anywhere in the two rule files). Commit stages ONLY the three files created in this task:

```bash
git add paxman/capabilities/Money/rules/iso_4217_ed2015.py
git add paxman/capabilities/Money/rules/cldr_currencies_ed2025.py
git add tests/capabilities/money/test_rules.py
git commit -m "feat(money): add Money validation rules"
```
### Task 5: Amount parsing and recognition grammars

**Files:**
- Create: `paxman/capabilities/Money/parsing.py`
- Create: `paxman/capabilities/Money/grammar/__init__.py` (replaces the docstring-only placeholder from Task 1 with the shared amount regex + shape classifier)
- Create: `paxman/capabilities/Money/grammar/code_recognition.py`
- Create: `paxman/capabilities/Money/grammar/symbol_recognition.py`
- Create: `paxman/capabilities/Money/grammar/word_recognition.py`
- Create: `tests/capabilities/money/test_parsing.py`
- Create: `tests/capabilities/money/test_grammar.py`

**Dependency note (cross-part contract):** the rules (Task 4) import `from paxman.capabilities.Money.parsing import ParsedAmount, format_amount, parse_amount` and call `parse_amount(notation.amount_part)` (None for no-digits), `parsed.decimal_digits()`, and `format_amount(parsed, MINOR_UNITS[code], contract.precision)`. Those signatures are locked here: `parse_amount(raw: str) -> ParsedAmount | None`, `format_amount(parsed: ParsedAmount, minor_units: int, precision: Literal["strict", "truncate", "round"]) -> str`, `ParsedAmount` with `decimal_digits()`. The grammars consume the Task 3 grammar-data tables (`SYMBOL_TOKENS` from `grammar/data/currency_symbols.py`, `WORD_TOKENS` from `grammar/data/currency_words.py`) and the `MoneyNotation` from Task 1. Task 5 touches nothing else; the `-m money` marker is added in Task 7, so every command in this task runs by path and both test modules use only `@pytest.mark.capability`.

**Purity note (locked):** `parsing.py` sits at the package root (outside `grammar/` and `rules/`), imports nothing from `paxman.*`, and is never imported by any grammar — the purity gate (`tests/unit/test_grammar_semantic_purity.py` scans `*/grammar/*.py` for imports containing `"rules"`) stays green. The three recognition modules import ONLY from `paxman.core` (`Grammar`, `RecognitionMatch`), `paxman.capabilities.Money.notation`, `paxman.capabilities.Money.grammar` (the shared amount helpers), and `paxman.capabilities.Money.grammar.data.*`. `grammar/__init__.py` defines the shared regex/classifier and imports nothing else. The grammars never call `parse_amount` (syntactic classification only) and never map a token to a canonical value — validity is the Task 4 rules' job.

- [ ] **Step 1: RED — write the parsing tests** (`tests/capabilities/money/test_parsing.py`, module-level `pytestmark = [pytest.mark.capability]`, parametrize-heavy, mirroring part3's `test_rules.py` convention)

```python
"""Tests for Money amount parsing and formatting helpers."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.Money.parsing import (
    ParsedAmount,
    format_amount,
    parse_amount,
)

pytestmark = [pytest.mark.capability]


class TestParsedAmount:
    """Tests for the ParsedAmount value object."""

    def test_frozen_and_slots(self) -> None:
        """ParsedAmount is a frozen, slots-based dataclass."""
        assert dataclasses.is_dataclass(ParsedAmount)
        assert "__slots__" in ParsedAmount.__dict__

    def test_decimal_digits(self) -> None:
        """decimal_digits is the fraction length."""
        assert ParsedAmount("500", "").decimal_digits() == 0
        assert ParsedAmount("1000", "50").decimal_digits() == 2

    def test_to_decimal_string_no_fraction(self) -> None:
        """No fraction renders as the bare integer."""
        assert ParsedAmount("500", "").to_decimal_string() == "500"

    def test_to_decimal_string_with_fraction(self) -> None:
        """Fraction renders after a decimal point."""
        assert ParsedAmount("1000", "50").to_decimal_string() == "1000.50"


class TestParseAmount:
    """The locked 'last separator wins' algorithm table."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            (".50", ("0", "50")),
            ("500.", ("500", "")),
            ("0,05", ("0", "05")),
            ("1,00", ("1", "")),
            ("1.234", ("1", "234")),
            ("1,00.50", ("1000", "50")),
            ("1.000,50", ("1000", "50")),
            ("1.500,50", ("1500", "50")),
            ("1,234.56", ("1234", "56")),
            ("12.345.678,90", ("12345678", "90")),
            ("500", ("500", "")),
        ],
    )
    def test_parse_amount_table(self, raw: str, expected: tuple[str, str]) -> None:
        """The full locked edge-case table (D2 'last separator wins')."""
        parsed = parse_amount(raw)
        assert parsed is not None
        assert (parsed.integer, parsed.fraction) == expected

    @pytest.mark.parametrize("raw", ["abc", "", "USD", "!?@#"])
    def test_parse_amount_none(self, raw: str) -> None:
        """A token with no digit character parses to None."""
        assert parse_amount(raw) is None

    def test_parse_amount_strips_leading_zeros(self) -> None:
        """No-separator integers strip leading zeros."""
        assert parse_amount("007") == ParsedAmount("7", "")

    def test_parse_amount_accounting_parens(self) -> None:
        """Accounting-form parentheses are ignored; the digit run is kept."""
        assert parse_amount("(500)") == ParsedAmount("500", "")


class TestFormatAmount:
    """format_amount pads, truncates, or rounds to minor_units digits."""

    @pytest.mark.parametrize(
        ("parsed", "minor_units", "precision", "expected"),
        [
            (ParsedAmount("500", ""), 2, "strict", "500.00"),
            (ParsedAmount("1000", "5"), 2, "strict", "1000.50"),
            (ParsedAmount("500", "999"), 2, "truncate", "500.99"),
            (ParsedAmount("500", "5"), 0, "round", "500"),
            (ParsedAmount("2", "5"), 0, "round", "2"),
            (ParsedAmount("3", "5"), 0, "round", "4"),
            (ParsedAmount("500", "9"), 0, "round", "501"),
        ],
    )
    def test_format_amount_table(
        self,
        parsed: ParsedAmount,
        minor_units: int,
        precision: str,
        expected: str,
    ) -> None:
        """The locked examples: strict pads, truncate drops, round half-to-even."""
        assert format_amount(parsed, minor_units, precision) == expected

    def test_zero_minor_units_never_render_decimal_point(self) -> None:
        """minor_units == 0 produces an integer string, never '500.'."""
        assert format_amount(ParsedAmount("500", ""), 0, "strict") == "500"
        assert format_amount(ParsedAmount("500", ""), 0, "round") == "500"

    def test_truncate_pads_short_fraction(self) -> None:
        """Truncate zero-pads fractions shorter than minor_units."""
        assert format_amount(ParsedAmount("500", "5"), 2, "truncate") == "500.50"

    def test_round_pads_to_minor_units(self) -> None:
        """Round quantizes to the exact minor-unit scale."""
        assert format_amount(ParsedAmount("500", "5"), 2, "round") == "500.50"
```

- [ ] **Step 2: Run the parsing tests to verify they fail**

Run: `uv run pytest tests/capabilities/money/test_parsing.py -v`
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'paxman.capabilities.Money.parsing'` (the module does not exist yet).

- [ ] **Step 3: GREEN — implement `paxman/capabilities/Money/parsing.py`**

Pure digit-string logic at the package root. The `ParsedAmount` dataclass is locked exactly as given; `parse_amount` implements the user-locked "last separator wins" algorithm (a single separator is always the decimal point; base-1000 grouping folds only the separators BEFORE the last one; an all-zero or empty fraction collapses to `""`; no separator at all keeps the plain digit run with leading zeros stripped); `format_amount` pads (strict), truncates toward zero (truncate), or quantizes half-to-even with `Decimal.quantize(..., ROUND_HALF_EVEN)` (round) to exactly `minor_units` decimal digits, never rendering a decimal point at zero minor units. `parse_amount` never raises: the digit-run extraction per group absorbs accounting parentheses, so `"(500)"` → `("500", "")` and rules stay non-raising on every grammar-emitted amount token.

```python
"""Amount parsing and canonical formatting helpers for the Money capability.

Pure digit-string logic: parsing.py sits at the package root (outside
grammar/ and rules/) and imports nothing from paxman.*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Literal


@dataclass(frozen=True, slots=True)
class ParsedAmount:
    """A parsed amount: normalized integer and fractional digit strings."""

    integer: str
    fraction: str

    def decimal_digits(self) -> int:
        """Return the number of fractional digits."""
        return len(self.fraction)

    def to_decimal_string(self) -> str:
        """Render as "integer[.fraction]" for value construction."""
        if not self.fraction:
            return self.integer
        return f"{self.integer}.{self.fraction}"


def parse_amount(raw: str) -> ParsedAmount | None:
    """Parse an amount token into normalized integer and fraction strings.

    "Last separator wins": the final "," or "." is the decimal point; any
    separators before it are base-1000 grouping. A single separator is
    therefore always a decimal point ("1,00" -> integer "1", fraction "";
    "1.234" -> integer "1", fraction "234"). Grouping folds to a plain
    integer ("1,00.50" -> integer "1000", fraction "50"). A token with no
    separator keeps the plain digit run with leading zeros stripped.
    Parentheses (accounting form) are ignored: only digit characters and
    the separators participate.

    Assumption note: "1.500,50" parses to integer "1500", fraction "50"
    (the final "," is the decimal point and "1.500" folds to 1500), a
    single authoritative result matching the plan's test table. Separately,
    "1,00.50" parses to integer "1000", fraction "50".

    Args:
        raw: The amount token as written (e.g. "1,00.50", "(500)").

    Returns:
        The parsed amount, or None when the token contains no digit
        character (e.g. "" or "abc").
    """
    if not any(ch.isdigit() for ch in raw):
        return None
    last_separator = max(raw.rfind(","), raw.rfind("."))
    if last_separator == -1:
        digits = "".join(ch for ch in raw if ch.isdigit())
        return ParsedAmount(integer=digits.lstrip("0") or "0", fraction="")
    integer_raw = raw[:last_separator]
    fraction_raw = raw[last_separator + 1 :]
    groups = [g for g in re.split(r"[.,]", integer_raw) if g]
    total = 0
    for group in groups:
        group_digits = "".join(ch for ch in group if ch.isdigit()) or "0"
        total = total * 1000 + int(group_digits)
    fraction_digits = "".join(ch for ch in fraction_raw if ch.isdigit())
    if not fraction_digits or set(fraction_digits) == {"0"}:
        fraction = ""
    else:
        fraction = fraction_digits
    return ParsedAmount(integer=str(total), fraction=fraction)


def format_amount(
    parsed: ParsedAmount,
    minor_units: int,
    precision: Literal["strict", "truncate", "round"],
) -> str:
    """Format a parsed amount to exactly ``minor_units`` decimal digits.

    "strict" trusts the caller: the rules guarantee the parsed amount has
    at most ``minor_units`` decimal digits, so the fraction is only
    zero-padded. "truncate" drops excess digits (toward zero at the
    minor-unit scale) and zero-pads shorter fractions. "round" quantizes
    the numeric value half-to-even (ROUND_HALF_EVEN). Zero minor units
    never render a decimal point ("500", not "500.").

    Args:
        parsed: Parsed amount to format.
        minor_units: Number of decimal digits in the output.
        precision: Over-precision policy ("strict" | "truncate" | "round").

    Returns:
        The amount digit string with exactly ``minor_units`` decimal
        digits (e.g. "500.00", or "500" when minor_units == 0).
    """
    if precision == "round":
        value = Decimal(parsed.integer or "0") + Decimal(parsed.fraction or "0") / (
            Decimal(10) ** len(parsed.fraction)
        )
        quantum = Decimal(1).scaleb(-minor_units)
        return format(value.quantize(quantum, rounding=ROUND_HALF_EVEN), "f")
    if precision == "truncate":
        fraction = parsed.fraction[:minor_units].ljust(minor_units, "0")
    else:  # strict — rules guarantee decimal_digits() <= minor_units
        fraction = parsed.fraction.ljust(minor_units, "0")
    if minor_units == 0:
        return parsed.integer or "0"
    return f"{parsed.integer or '0'}.{fraction}"
```

- [ ] **Step 4: Run the parsing tests to verify they pass**

Run: `uv run pytest tests/capabilities/money/test_parsing.py -v`
Expected: PASS — `31 passed` (ParsedAmount ×4, parse_amount table ×11 + none ×4 + leading-zeros + accounting, format_amount table ×7 + zero-minor-units + truncate-pads + round-pads).

- [ ] **Step 5: RED — write the grammar tests** (`tests/capabilities/money/test_grammar.py`, module-level `pytestmark = [pytest.mark.capability]`, per-grammar classes with `setup_method`, mirroring `tests/capabilities/country/test_grammar.py`)

```python
"""Tests for Money recognition grammars."""

from __future__ import annotations

import pytest

from paxman.capabilities.Money.grammar import classify_amount_shape
from paxman.capabilities.Money.grammar.code_recognition import CodeRecognition
from paxman.capabilities.Money.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.Money.grammar.word_recognition import WordRecognition
from paxman.core.domain import RecognitionMatch

pytestmark = [pytest.mark.capability]


def _assert_span_invariants(text: str, match: RecognitionMatch[object]) -> None:
    """Verify the RecognitionMatch span contract (half-open [start, end))."""
    assert 0 <= match.start <= match.end
    assert len(match.raw_text) == match.end - match.start
    assert match.raw_text == text[match.start : match.end]


class TestCodeRecognition:
    """Tests for CodeRecognition."""

    def setup_method(self) -> None:
        self.grammar = CodeRecognition()

    def test_recognizes_prefix_adjacent(self) -> None:
        """Happy path: uppercase code directly adjacent to the amount."""
        results = self.grammar.recognize("USD500")
        assert len(results) == 1
        assert results[0].notation.currency_part == "USD"
        assert results[0].notation.amount_part == "500"
        assert results[0].notation.currency_shape == "code"
        assert results[0].notation.amount_shape == "integer"

    def test_recognizes_prefix_with_space(self) -> None:
        """A single ASCII space between code and amount is allowed."""
        results = self.grammar.recognize("USD 500")
        assert len(results) == 1
        assert results[0].notation.currency_part == "USD"
        assert results[0].notation.amount_part == "500"
        assert results[0].raw_text == "USD 500"

    def test_recognizes_suffix(self) -> None:
        """Amount-first order: '500 USD'."""
        results = self.grammar.recognize("500 USD")
        assert len(results) == 1
        assert results[0].notation.currency_part == "USD"
        assert results[0].notation.amount_part == "500"

    def test_recognizes_suffix_adjacent(self) -> None:
        """Amount-first, no space: '100MYR'."""
        results = self.grammar.recognize("100MYR")
        assert len(results) == 1
        assert results[0].notation.currency_part == "MYR"
        assert results[0].notation.amount_part == "100"

    def test_recognizes_comma_decimal_suffix(self) -> None:
        """'1.000,50 EUR' keeps the raw amount and comma_decimal shape."""
        results = self.grammar.recognize("1.000,50 EUR")
        assert len(results) == 1
        assert results[0].notation.currency_part == "EUR"
        assert results[0].notation.amount_part == "1.000,50"
        assert results[0].notation.amount_shape == "comma_decimal"

    def test_recognizes_dot_decimal_suffix(self) -> None:
        """'1,00.50 USD' keeps the raw amount and dot_decimal shape."""
        results = self.grammar.recognize("1,00.50 USD")
        assert len(results) == 1
        assert results[0].notation.currency_part == "USD"
        assert results[0].notation.amount_part == "1,00.50"
        assert results[0].notation.amount_shape == "dot_decimal"

    def test_recognizes_multiple(self) -> None:
        """Two independent code+amount tokens both match."""
        results = self.grammar.recognize("USD 500 and EUR 200")
        assert len(results) == 2

    def test_recognizes_unknown_code(self) -> None:
        """Unknown codes ARE matched — validity is the rule's job."""
        results = self.grammar.recognize("ZZZ 500")
        assert len(results) == 1
        assert results[0].notation.currency_part == "ZZZ"

    def test_recognizes_accounting_form(self) -> None:
        """Parenthesized amounts match as one token with accounting shape."""
        results = self.grammar.recognize("(500) USD")
        assert len(results) == 1
        assert results[0].notation.amount_part == "(500)"
        assert results[0].notation.amount_shape == "accounting"

    def test_rejects_bare_code(self) -> None:
        """A code with no amount is not a money token."""
        assert self.grammar.recognize("USD") == []

    def test_rejects_bare_amount(self) -> None:
        """An amount with no code is not a money token."""
        assert self.grammar.recognize("500") == []

    def test_rejects_lowercase_code(self) -> None:
        """Only uppercase alpha-3 codes match."""
        assert self.grammar.recognize("usd 500") == []

    def test_rejects_two_letter_code(self) -> None:
        """A 2-letter code is not alpha-3."""
        assert self.grammar.recognize("US 500") == []

    def test_rejects_preceded_by_word_char(self) -> None:
        """No match inside a longer token: xUSD500."""
        assert self.grammar.recognize("xUSD500") == []

    def test_rejects_followed_by_word_char(self) -> None:
        """No match inside a longer token: USD500x."""
        assert self.grammar.recognize("USD500x") == []

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty/whitespace-only input returns an empty list."""
        assert self.grammar.recognize("") == []
        assert self.grammar.recognize("   ") == []

    def test_name(self) -> None:
        """Verify the grammar name."""
        assert self.grammar.name == "code_recognition"

    def test_emits_spans(self) -> None:
        """The whole token is one span: raw_text == text[start:end]."""
        results = self.grammar.recognize("USD 500")
        assert len(results) == 1
        _assert_span_invariants("USD 500", results[0])


class TestSymbolRecognition:
    """Tests for SymbolRecognition."""

    def setup_method(self) -> None:
        self.grammar = SymbolRecognition()

    def test_bare_symbol_prefix(self) -> None:
        """'$500' matches as a bare symbol, shape 'symbol'."""
        results = self.grammar.recognize("$500")
        assert len(results) == 1
        assert results[0].notation.currency_part == "$"
        assert results[0].notation.currency_shape == "symbol"
        assert results[0].notation.amount_part == "500"
        assert results[0].notation.amount_shape == "integer"

    def test_qualified_symbol_ordering(self) -> None:
        """'US$50.79' matches as the qualified form, not bare '$' (D4)."""
        results = self.grammar.recognize("US$50.79")
        assert len(results) == 1
        assert results[0].notation.currency_part == "US$"
        assert results[0].notation.currency_shape == "qualified_symbol"
        assert results[0].notation.amount_part == "50.79"
        assert results[0].notation.amount_shape == "dot_decimal"

    def test_euro_prefix(self) -> None:
        """'€5' matches at string start (lookbehind boundary)."""
        results = self.grammar.recognize("\u20ac5")
        assert len(results) == 1
        assert results[0].notation.currency_part == "\u20ac"
        assert results[0].notation.currency_shape == "symbol"

    def test_qualified_rm(self) -> None:
        """'RM100' — a letter-containing symbol is qualified."""
        results = self.grammar.recognize("RM100")
        assert len(results) == 1
        assert results[0].notation.currency_part == "RM"
        assert results[0].notation.currency_shape == "qualified_symbol"

    def test_symbol_suffix(self) -> None:
        """'500 €' — amount-first order."""
        results = self.grammar.recognize("500 \u20ac")
        assert len(results) == 1
        assert results[0].notation.currency_part == "\u20ac"
        assert results[0].notation.amount_part == "500"

    def test_comma_decimal_suffix(self) -> None:
        """'1.000,00 €' keeps the raw amount and comma_decimal shape."""
        results = self.grammar.recognize("1.000,00 \u20ac")
        assert len(results) == 1
        assert results[0].notation.amount_part == "1.000,00"
        assert results[0].notation.amount_shape == "comma_decimal"

    def test_rejects_bare_symbol(self) -> None:
        """A symbol with no amount is not a money token."""
        assert self.grammar.recognize("$") == []

    def test_rejects_code_shape(self) -> None:
        """Codes are not symbols: 'USD 500' does not match."""
        assert self.grammar.recognize("USD 500") == []

    def test_rejects_mid_word(self) -> None:
        """No match inside a longer token: $500x."""
        assert self.grammar.recognize("$500x") == []

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty input returns an empty list."""
        assert self.grammar.recognize("") == []

    def test_name(self) -> None:
        """Verify the grammar name."""
        assert self.grammar.name == "symbol_recognition"

    def test_emits_spans(self) -> None:
        """The whole token is one span: raw_text == text[start:end]."""
        text = "  $500  "
        results = self.grammar.recognize(text)
        assert len(results) == 1
        assert results[0].start == 2
        assert results[0].end == 6
        _assert_span_invariants(text, results[0])


class TestWordRecognition:
    """Tests for WordRecognition."""

    def setup_method(self) -> None:
        self.grammar = WordRecognition()

    def test_recognizes_amount_first(self) -> None:
        """'18 Dollar' — amount-first order, word as written."""
        results = self.grammar.recognize("18 Dollar")
        assert len(results) == 1
        assert results[0].notation.currency_part == "Dollar"
        assert results[0].notation.currency_shape == "word"
        assert results[0].notation.amount_part == "18"
        assert results[0].notation.amount_shape == "integer"

    def test_recognizes_ringgit(self) -> None:
        """'500 Ringgit'."""
        results = self.grammar.recognize("500 Ringgit")
        assert len(results) == 1
        assert results[0].notation.currency_part == "Ringgit"

    def test_recognizes_euro(self) -> None:
        """'500 Euro'."""
        results = self.grammar.recognize("500 Euro")
        assert len(results) == 1
        assert results[0].notation.currency_part == "Euro"

    def test_recognizes_word_first(self) -> None:
        """Word-first order: 'Euro 500'."""
        results = self.grammar.recognize("Euro 500")
        assert len(results) == 1
        assert results[0].notation.currency_part == "Euro"
        assert results[0].notation.amount_part == "500"

    def test_recognizes_case_insensitive_as_written(self) -> None:
        """Matching is case-insensitive; the word is kept as written."""
        results = self.grammar.recognize("500 euro")
        assert len(results) == 1
        assert results[0].notation.currency_part == "euro"

    def test_rejects_code_shape(self) -> None:
        """Codes are not words: '500 USD' does not match."""
        assert self.grammar.recognize("500 USD") == []

    def test_rejects_bare_word(self) -> None:
        """A word with no amount is not a money token."""
        assert self.grammar.recognize("Dollar") == []

    def test_rejects_plural(self) -> None:
        """'500 Dollars' — 'Dollar' inside a longer word does not match."""
        assert self.grammar.recognize("500 Dollars") == []

    def test_returns_empty_for_empty_input(self) -> None:
        """Empty input returns an empty list."""
        assert self.grammar.recognize("") == []

    def test_name(self) -> None:
        """Verify the grammar name."""
        assert self.grammar.name == "word_recognition"

    def test_emits_spans(self) -> None:
        """The whole token is one span: raw_text == text[start:end]."""
        text = "18 Dollar"
        results = self.grammar.recognize(text)
        assert len(results) == 1
        assert results[0].start == 0
        assert results[0].end == 9
        _assert_span_invariants(text, results[0])


class TestClassifyAmountShape:
    """The amount-shape classifier table (syntax only)."""

    @pytest.mark.parametrize(
        ("amount", "expected"),
        [
            ("500", "integer"),
            ("500.50", "dot_decimal"),
            ("1,00.50", "dot_decimal"),
            ("1.000,50", "comma_decimal"),
            ("1,234.56", "dot_decimal"),
            ("12.345.678,90", "comma_decimal"),
            ("1\u202f234,50", "space_decimal"),
            ("(500)", "accounting"),
        ],
    )
    def test_classify_amount_shape(self, amount: str, expected: str) -> None:
        """The five syntactic shapes are classified from the token alone."""
        assert classify_amount_shape(amount) == expected
```

- [ ] **Step 6: Run the grammar tests to verify they fail**

Run: `uv run pytest tests/capabilities/money/test_grammar.py -v`
Expected: FAIL — collection error `ModuleNotFoundError: No module named 'paxman.capabilities.Money.grammar.code_recognition'` (none of the four grammar modules exist yet).

- [ ] **Step 7: GREEN — implement `paxman/capabilities/Money/grammar/__init__.py`**

Replaces the docstring-only placeholder from Task 1. Holds the SINGLE shared amount-token regex and the syntactic amount-shape classifier; the three recognition modules import both from here. It imports nothing from `paxman.*` (purity gate) and never calls `parse_amount` — classification is purely syntactic. The amount pattern allows digits with `,`/`.`/narrow-no-break-space (U+202F) separators and an optional wrapping pair of parentheses (accounting form); it never contains an ASCII space, so the only ASCII space in a matched token is always the currency/amount separator (which is what makes the Task 6 `"compact"` format's `replace(" ", "", 1)` safe):

```python
"""Shared amount token helpers for Money recognition grammars.

Holds the single amount-token regex and the syntactic amount-shape
classifier shared by the three recognition grammars. This module is part
of the recognition layer and imports nothing from paxman.* (the purity
gate forbids grammar modules from importing rules or parsing): shape
classification is purely syntactic — the grammars never resolve an
amount, only describe its shape for the rules.
"""

from __future__ import annotations

import re

# A digit run with optional "," / "." / narrow no-break-space (U+202F)
# separators, optionally wrapped in parentheses (accounting form). The
# amount never contains an ASCII space: the single ASCII space in a
# matched token is always the currency/amount separator.
_AMOUNT_CORE = r"[0-9][0-9.,\u202f]*"
AMOUNT_PATTERN = rf"(?:\({_AMOUNT_CORE}\)|{_AMOUNT_CORE})"


def classify_amount_shape(amount: str) -> str:
    """Classify an amount token's syntactic shape (syntax only).

    Shape is decided from the token alone, never by parsing its value:
    "accounting" when the whole token is wrapped in parentheses,
    "space_decimal" when it contains a (narrow no-break) space,
    otherwise "dot_decimal" or "comma_decimal" by the LAST separator,
    else "integer".

    Args:
        amount: The amount token as written (e.g. "1.000,50", "(500)").

    Returns:
        One of "integer", "dot_decimal", "comma_decimal",
        "space_decimal", "accounting".
    """
    if amount.startswith("(") and amount.endswith(")"):
        return "accounting"
    if any(ch.isspace() for ch in amount):
        return "space_decimal"
    if amount.rfind(".") > amount.rfind(","):
        return "dot_decimal"
    if amount.rfind(",") > amount.rfind("."):
        return "comma_decimal"
    return "integer"
```

- [ ] **Step 8: GREEN — implement `paxman/capabilities/Money/grammar/code_recognition.py`**

Matches `[A-Z]{3}` adjacent to an amount in EITHER order (`"USD500"`, `"USD 500"`, `"500 USD"`, `"100MYR"`), one match per full token in ONE span. `\b` word boundaries (the Country `Alpha2Grammar` precedent) prevent mid-token matches. Unknown codes (e.g. `"ZZZ"`) ARE matched — validity is the Task 4 rules' job. The prefix/suffix alternation sets exactly one branch, so `cast(str, group_a or group_b)` is deterministic:

```python
"""ISO 4217 alpha-3 currency code recognition grammar.

Recognizes an ISO 4217 alpha-3 code shape adjacent to an amount, in
either order, as one span-bearing token. Syntax only: unknown codes are
still matched — deciding validity is the rules' job.
"""

from __future__ import annotations

import re
from typing import cast

from paxman.capabilities.Money.grammar import AMOUNT_PATTERN, classify_amount_shape
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.core.domain import Grammar, RecognitionMatch

_CODE_PATTERN = re.compile(
    rf"\b(?:(?P<prefix_code>[A-Z]{{3}}) ?(?P<prefix_amount>{AMOUNT_PATTERN})"
    rf"|(?P<suffix_amount>{AMOUNT_PATTERN}) ?(?P<suffix_code>[A-Z]{{3}}))\b"
)


class CodeRecognition(Grammar[MoneyNotation]):
    """Recognizes ISO 4217 alpha-3 code + amount tokens.

    Matches a 3-letter uppercase ASCII code adjacent to an amount in
    either order: "USD500", "USD 500" (prefix) or "500 USD", "100MYR"
    (suffix). Word boundaries keep the whole token inside one span.

    Examples: "USD500" -> currency_part "USD", amount_part "500"
              "500 USD" -> same notation, suffix order
    Non-examples: "USD" (no amount), "usd 500" (lowercase),
                  "xUSD500" (inside a longer token)
    """

    name = "code_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[MoneyNotation]]:
        """Extract code+amount tokens from text.

        Args:
            text: Raw input text.

        Returns:
            List of span-bearing matches with shape "code" notations.
        """
        if not text.strip():
            return []
        matches: list[RecognitionMatch[MoneyNotation]] = []
        for match in _CODE_PATTERN.finditer(text):
            currency = cast(
                str, match.group("prefix_code") or match.group("suffix_code")
            )
            amount = cast(
                str, match.group("prefix_amount") or match.group("suffix_amount")
            )
            matches.append(
                RecognitionMatch(
                    notation=MoneyNotation(
                        currency_part=currency,
                        amount_part=amount,
                        currency_shape="code",
                        amount_shape=classify_amount_shape(amount),
                    ),
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(0),
                )
            )
        return matches
```

- [ ] **Step 9: GREEN — implement `paxman/capabilities/Money/grammar/symbol_recognition.py`**

Module-scope compiled alternation built from `SYMBOL_TOKENS` (qualified forms first, longest-first within each class — the data guarantees the order), `re.escape`d and joined with `|`, so `"US$50.79"` matches as the qualified form, never as bare `"$"` plus a stray amount. Boundary handling uses `(?<!\w)` / `(?!\w)` lookarounds instead of `\b` because pure-symbol tokens (`$`, `€`) are non-word characters that `\b` would reject at string start; the lookarounds still block mid-token matches. `currency_shape` is `"qualified_symbol"` when the matched symbol contains an ASCII letter, else `"symbol"`:

```python
"""CLDR currency symbol recognition grammar.

Recognizes a currency symbol token adjacent to an amount, in either
order, as one span-bearing token. The symbol alternation is built from
SYMBOL_TOKENS (qualified forms first, longest-first within each class,
so "US$" alternates before "$"). Syntax only: resolving the symbol to a
code is the rules' job.
"""

from __future__ import annotations

import re
from typing import cast

from paxman.capabilities.Money.grammar import AMOUNT_PATTERN, classify_amount_shape
from paxman.capabilities.Money.grammar.data.currency_symbols import SYMBOL_TOKENS
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.core.domain import Grammar, RecognitionMatch

_SYMBOL_ALTERNATION = "|".join(re.escape(token) for token in SYMBOL_TOKENS)
# Lookarounds, not \b: pure-symbol tokens ("$", "€") are non-word
# characters that \b would reject at string start, and the lookarounds
# still block matches inside a longer token.
_SYMBOL_PATTERN = re.compile(
    rf"(?<!\w)(?:(?P<prefix_symbol>{_SYMBOL_ALTERNATION})"
    rf" ?(?P<prefix_amount>{AMOUNT_PATTERN})"
    rf"|(?P<suffix_amount>{AMOUNT_PATTERN}) ?(?P<suffix_symbol>{_SYMBOL_ALTERNATION}))"
    rf"(?!\w)"
)


def _is_qualified(token: str) -> bool:
    """A symbol is qualified when it contains an ASCII letter (US$, RM)."""
    return any(ch.isascii() and ch.isalpha() for ch in token)


class SymbolRecognition(Grammar[MoneyNotation]):
    """Recognizes currency symbol + amount tokens.

    Matches a CLDR symbol adjacent to an amount in either order:
    "$500", "US$50.79", "RM100", "€5" (prefix) or "500 €",
    "1.000,00 €" (suffix). A symbol containing an ASCII letter (e.g.
    "US$", "CA$", "RM") is emitted with currency_shape
    "qualified_symbol"; a pure-symbol token ("$", "€") with "symbol".
    The qualified-before-bare token ordering makes "US$50.79" match as
    the qualified form, not as bare "$" followed by a stray amount.

    Examples: "US$50.79" -> currency_part "US$", shape "qualified_symbol"
              "$500" -> currency_part "$", shape "symbol"
    Non-examples: "$" (no amount), "USD 500" (codes are not symbols)
    """

    name = "symbol_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[MoneyNotation]]:
        """Extract symbol+amount tokens from text.

        Args:
            text: Raw input text.

        Returns:
            List of span-bearing matches with "symbol"/"qualified_symbol"
            notations.
        """
        if not text.strip():
            return []
        matches: list[RecognitionMatch[MoneyNotation]] = []
        for match in _SYMBOL_PATTERN.finditer(text):
            symbol = cast(
                str, match.group("prefix_symbol") or match.group("suffix_symbol")
            )
            amount = cast(
                str, match.group("prefix_amount") or match.group("suffix_amount")
            )
            matches.append(
                RecognitionMatch(
                    notation=MoneyNotation(
                        currency_part=symbol,
                        amount_part=amount,
                        currency_shape=(
                            "qualified_symbol" if _is_qualified(symbol) else "symbol"
                        ),
                        amount_shape=classify_amount_shape(amount),
                    ),
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(0),
                )
            )
        return matches
```

- [ ] **Step 10: GREEN — implement `paxman/capabilities/Money/grammar/word_recognition.py`**

Compiled alternation from `WORD_TOKENS` (longest-first), word-boundary anchored (`(?<!\w)` / `(?!\w)`) and `re.IGNORECASE`; word adjacent to amount in either order (`"18 Dollar"`, `"500 Ringgit"`, `"500 Euro"`). `currency_part` is the matched word AS WRITTEN (`m.group()` — `"Dollar"` from `"18 Dollar"`, `"euro"` from `"500 euro"`), so the Task 4 rules' exact-match against `NAME_TO_CODES` decides validity:

```python
"""CLDR currency display-name word recognition grammar.

Recognizes a currency display-name word adjacent to an amount, in
either order, as one span-bearing token. The word alternation is built
from WORD_TOKENS (longest-first), word-boundary anchored and
case-insensitive. Syntax only: resolving the word to a code is the
rules' job.
"""

from __future__ import annotations

import re
from typing import cast

from paxman.capabilities.Money.grammar import AMOUNT_PATTERN, classify_amount_shape
from paxman.capabilities.Money.grammar.data.currency_words import WORD_TOKENS
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.core.domain import Grammar, RecognitionMatch

_WORD_ALTERNATION = "|".join(re.escape(token) for token in WORD_TOKENS)
_WORD_PATTERN = re.compile(
    rf"(?<!\w)(?:(?P<prefix_word>{_WORD_ALTERNATION})"
    rf" ?(?P<prefix_amount>{AMOUNT_PATTERN})"
    rf"|(?P<suffix_amount>{AMOUNT_PATTERN}) ?(?P<suffix_word>{_WORD_ALTERNATION}))"
    rf"(?!\w)",
    re.IGNORECASE,
)


class WordRecognition(Grammar[MoneyNotation]):
    """Recognizes currency display-name word + amount tokens.

    Matches a CLDR display-name word adjacent to an amount in either
    order: "18 Dollar" (amount-first) or "500 Ringgit", "500 Euro".
    Matching is case-insensitive; the currency_part is the word as
    written in the input (e.g. "Dollar" from "18 Dollar", "euro" from
    "500 euro"). Word boundaries keep the match inside one token:
    "500 Dollars" does not match.

    Examples: "18 Dollar" -> currency_part "Dollar", shape "word"
              "500 euro" -> currency_part "euro", shape "word"
    Non-examples: "500 USD" (codes are not words), "500 Dollars"
    """

    name = "word_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[MoneyNotation]]:
        """Extract word+amount tokens from text.

        Args:
            text: Raw input text.

        Returns:
            List of span-bearing matches with shape "word" notations.
        """
        if not text.strip():
            return []
        matches: list[RecognitionMatch[MoneyNotation]] = []
        for match in _WORD_PATTERN.finditer(text):
            word = cast(str, match.group("prefix_word") or match.group("suffix_word"))
            amount = cast(
                str, match.group("prefix_amount") or match.group("suffix_amount")
            )
            matches.append(
                RecognitionMatch(
                    notation=MoneyNotation(
                        currency_part=word,
                        amount_part=amount,
                        currency_shape="word",
                        amount_shape=classify_amount_shape(amount),
                    ),
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(0),
                )
            )
        return matches
```

**Semantics note (locked decisions, from the cross-part contract):**

- The three grammars are syntax-only recognizers: they emit `MoneyNotation(currency_part, amount_part, currency_shape, amount_shape)` with span-bearing `RecognitionMatch` (one match per full currency+amount token, `raw_text == text[start:end]`), and they never call `parse_amount` — the amount shape is the classifier's purely syntactic verdict. Token→code resolution, over-precision checks, and canonical `CODE + " " + amount` output are entirely the Task 4 rules' job.
- `currency_shape` values are exactly `"code"`, `"symbol"` / `"qualified_symbol"`, `"word"`; `amount_shape` values are exactly `"integer"`, `"dot_decimal"`, `"comma_decimal"`, `"space_decimal"`, `"accounting"` — all accepted by the Task 1 `MoneyNotation.__post_init__` validator.
- `SYMBOL_TOKENS` ordering (qualified before bare, longest-first within each class, locked by Task 3's D4 tests) is what makes `"US$50.79"` match as `"qualified_symbol"` — verified by `test_qualified_symbol_ordering`.
- The shared amount pattern allows an optional single ASCII space between the currency and the amount (`"USD 500"`), optional `,`/`.`/U+202F separators inside the amount, and optional surrounding parentheses (accounting). It never allows an ASCII space inside the amount, so `space_decimal` amounts (e.g. `1\u202f234,50`) carry the narrow no-break space — the invariant the Task 6 `"compact"` branch relies on.
- None of the grammar modules contain the token `output_format`, import anything with `"rules"` in its path, or import `parsing` (the `tests/unit/test_grammar_semantic_purity.py` scan stays green).

- [ ] **Step 11: Run the grammar tests to verify they pass**

Run: `uv run pytest tests/capabilities/money/test_grammar.py -v`
Expected: PASS — `48 passed` (code ×18, symbol ×12, word ×11, classifier table ×7).

- [ ] **Step 12: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_parsing.py tests/capabilities/money/test_grammar.py
uv run ruff check paxman/capabilities/Money tests/capabilities/money
uv run ruff format --check paxman/capabilities/Money tests/capabilities/money
uv run pyright paxman/capabilities/Money/parsing.py paxman/capabilities/Money/grammar
```

Expected: pytest green (31 parsing + 48 grammar); ruff clean (line-length 88); ruff format clean; pyright strict clean (no `# type: ignore` / `# noqa` / `# pyright: ignore` anywhere — the `cast(str, group_a or group_b)` pattern is the sanctioned narrowing for mutually exclusive alternation groups). The Task 4 rules' `parse_amount(notation.amount_part)` / `parsed.decimal_digits()` / `format_amount(parsed, MINOR_UNITS[code], contract.precision)` calls are satisfied by the exact signatures locked in Step 3. Commit stages ONLY the seven files created in this task:

```bash
git add paxman/capabilities/Money/parsing.py
git add paxman/capabilities/Money/grammar/__init__.py
git add paxman/capabilities/Money/grammar/code_recognition.py
git add paxman/capabilities/Money/grammar/symbol_recognition.py
git add paxman/capabilities/Money/grammar/word_recognition.py
git add tests/capabilities/money/test_parsing.py
git add tests/capabilities/money/test_grammar.py
git commit -m "feat(money): add amount parsing and recognition grammars"
```
### Task 6: MoneyCapability and format_value

**Files:**
- Create: `paxman/capabilities/Money/capability.py`
- Create: `tests/capabilities/money/test_capability.py`

The wiring mirrors `paxman/capabilities/Phone/capability.py` exactly: module docstring, `from __future__ import annotations`, alphabetical import block, module-level `__all__`, class attrs `name`/`version`, `get_grammars()`/`get_rules()` returning fresh instances, a static keyword-only `create_contract` factory with the unanimous common block FIRST (`excluded_rules`, `pinned_rules`, `year`, `output_format`) followed by the capability-specific `precision` and `dollar_sign_currency`, and a `format_value()` presentation seam whose default path is the identity. The capability only *imports* grammars, rules, contract, and notation — it creates no grammar/rule/contract/notation logic of its own.

- [ ] **Step 1: RED — write the capability tests** (`tests/capabilities/money/test_capability.py`, `@pytest.mark.capability` class markers, imports from `paxman.capabilities.Money.capability` / `.contract` / `.notation`)

```python
"""Tests for MoneyCapability wiring."""

import pytest

from paxman.capabilities.Money.capability import MoneyCapability
from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.core.capability import Capability


@pytest.mark.capability
class TestMoneyCapability:
    """Tests for MoneyCapability wiring."""

    def test_is_capability_subclass(self) -> None:
        """Verify inheritance from the base Capability."""
        assert issubclass(MoneyCapability, Capability)

    def test_name(self) -> None:
        """Verify the capability name."""
        assert MoneyCapability.name == "money"

    def test_version(self) -> None:
        """Verify the capability version."""
        assert MoneyCapability.version == "1.0.0"

    def test_get_grammars(self) -> None:
        """Verify the three grammar instances and their names."""
        cap = MoneyCapability()
        grammars = cap.get_grammars()
        assert len(grammars) == 3
        assert [g.name for g in grammars] == [
            "code_recognition",
            "symbol_recognition",
            "word_recognition",
        ]

    def test_get_rules(self) -> None:
        """Verify the three rule instances and their names."""
        cap = MoneyCapability()
        rules = cap.get_rules()
        assert len(rules) == 3
        assert [r.name for r in rules] == [
            "Section-codes",
            "Section-symbols",
            "Section-names",
        ]

    def test_rule_classes(self) -> None:
        """Verify the exact rule classes wired by get_rules()."""
        cap = MoneyCapability()
        assert [type(r).__name__ for r in cap.get_rules()] == [
            "SectionCode",
            "SectionSymbols",
            "SectionNames",
        ]

    def test_create_contract_defaults(self) -> None:
        """create_contract() with no args produces the correct defaults."""
        c = MoneyCapability.create_contract()
        assert c.capability_name == "money"
        assert c.precision == "strict"
        assert c.dollar_sign_currency is None
        assert c.output_format == "code_amount"

    def test_create_contract_precision(self) -> None:
        """precision passes through to the contract."""
        c = MoneyCapability.create_contract(precision="round")
        assert c.precision == "round"

    def test_create_contract_dollar_sign_currency(self) -> None:
        """dollar_sign_currency passes through to the contract."""
        c = MoneyCapability.create_contract(dollar_sign_currency="MYR")
        assert c.dollar_sign_currency == "MYR"

    def test_create_contract_dollar_sign_currency_none(self) -> None:
        """dollar_sign_currency=None passes through (bare $ becomes INVALID)."""
        c = MoneyCapability.create_contract(dollar_sign_currency=None)
        assert c.dollar_sign_currency is None

    def test_create_contract_common_block(self) -> None:
        """The unanimous common block passes through to the contract."""
        c = MoneyCapability.create_contract(
            excluded_rules=["Section-names"],
            pinned_rules=["Section-codes"],
            year=2020,
            output_format="compact",
        )
        assert c.excluded_rules == ("Section-names",)
        assert c.pinned_rules == ("Section-codes",)
        assert c.year == 2020
        assert c.output_format == "compact"

    def test_create_contract_output_format_default(self) -> None:
        """An unset output_format resolves to code_amount."""
        c = MoneyCapability.create_contract()
        assert c.output_format == "code_amount"

    def test_create_contract_output_format_compact(self) -> None:
        """output_format="compact" resolves to compact."""
        c = MoneyCapability.create_contract(output_format="compact")
        assert c.output_format == "compact"

    def test_contract_format_surface(self) -> None:
        """The formatter's formats match the contract class variables."""
        assert MoneyContract.DEFAULT_OUTPUT_FORMAT == "code_amount"
        assert MoneyContract.OFFERED_OUTPUT_FORMATS == frozenset({"compact"})


@pytest.mark.capability
class TestMoneyCapabilityFormatValue:
    """Tests for MoneyCapability.format_value()."""

    NOTATION = MoneyNotation(currency_part="USD", amount_part="500.00")

    def test_code_amount_is_identity(self) -> None:
        """The default code_amount path returns the canonical value unchanged."""
        cap = MoneyCapability()
        assert (
            cap.format_value("USD 500.00", "code_amount", self.NOTATION) == "USD 500.00"
        )

    def test_default_format_is_identity(self) -> None:
        """An unset output format returns the canonical value unchanged."""
        cap = MoneyCapability()
        assert cap.format_value("USD 500.00", None, self.NOTATION) == "USD 500.00"

    def test_compact_removes_separator_space(self) -> None:
        """Compact rendering removes the single ASCII space between code and amount."""
        cap = MoneyCapability()
        assert cap.format_value("USD 500.00", "compact", self.NOTATION) == "USD500.00"

    def test_compact_zero_decimal_currency(self) -> None:
        """Compact rendering works for 0-decimal amounts (no fraction)."""
        cap = MoneyCapability()
        notation = MoneyNotation(currency_part="JPY", amount_part="1000")
        assert cap.format_value("JPY 1000", "compact", notation) == "JPY1000"

    def test_compact_three_decimal_currency(self) -> None:
        """Compact rendering works for 3-decimal amounts."""
        cap = MoneyCapability()
        notation = MoneyNotation(currency_part="BHD", amount_part="500.000")
        assert cap.format_value("BHD 500.000", "compact", notation) == "BHD500.000"

    def test_compact_preserves_amount_with_narrow_no_break_space(self) -> None:
        """Only the code/amount ASCII space is removed.

        The space_decimal amount shape carries a NARROW NO-BREAK SPACE
        (U+202F) in its token, never an ASCII space, so the sole ASCII space
        in the canonical value is always the code/amount separator.
        """
        cap = MoneyCapability()
        notation = MoneyNotation(currency_part="EUR", amount_part="1\u202f234,50")
        assert (
            cap.format_value("EUR 1\u202f234,50", "compact", notation)
            == "EUR1\u202f234,50"
        )
```

**Cross-part note (rule-name strings):** `get_rules()` instantiates the rule classes created in Task 4 (`SectionCode` from `iso_4217_ed2015.py`; `SectionSymbols`, `SectionNames` from `cldr_currencies_ed2025.py`). The `name` strings asserted above (`"Section-codes"`, `"Section-symbols"`, `"Section-names"`) follow the Country `Section-{description}` convention (Country's `SectionNames` -> `"Section-names"`, `SectionAlpha2Codes` -> `"Section-alpha2-codes"`) and MUST match the `name` class attrs written in the Task 4 rule files — the capability itself only depends on the class names, never on the name strings.

**Space-decimal note (assumption flagged):** the research doc does not pin the exact separator character for the `space_decimal` amount shape — §9 (resolved decisions) never mentions it, and §5.1's Babel `ru` example shows ASCII-space grouping (`'12 345,123'`). The cross-part contract locks `space_decimal` to a NARROW NO-BREAK SPACE (U+202F) in the grammar token, never an ASCII space; that is what makes the `"compact"` branch's `replace(" ", "", 1)` safe. Task 5 (grammars) must honor that. If Task 5 used a different non-ASCII separator, `"compact"` behavior is still correct, but the guard test `test_compact_preserves_amount_with_narrow_no_break_space` should be updated to that character.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/capabilities/money/test_capability.py -v`
Expected: FAIL at collection — `ModuleNotFoundError: No module named 'paxman.capabilities.Money.capability'` (the file does not exist yet).

- [ ] **Step 3: GREEN — implement `paxman/capabilities/Money/capability.py`**

```python
"""Money capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.grammar.code_recognition import CodeRecognition
from paxman.capabilities.Money.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.Money.grammar.word_recognition import WordRecognition
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Money.rules.cldr_currencies_ed2025 import (
    SectionNames,
    SectionSymbols,
)
from paxman.capabilities.Money.rules.iso_4217_ed2015 import SectionCode
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["MoneyCapability", "MoneyContract", "MoneyNotation"]


class MoneyCapability(Capability[MoneyNotation]):
    """Money canonicalization capability.

    Canonicalizes money amounts (ISO 4217 code, CLDR symbol, or CLDR name
    adjacent to an amount) to ``CODE + " " + amount`` padded to ISO 4217
    minor-unit precision, with full provenance.
    """

    name = "money"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[MoneyNotation]]:
        """Return all grammar instances.

        Returns:
            List of 3 grammars: code, symbol, word.
        """
        return [CodeRecognition(), SymbolRecognition(), WordRecognition()]

    def get_rules(self) -> list[Rule[MoneyNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 3 rules: ISO 4217 code + minor units, CLDR symbols,
            CLDR names.
        """
        return [SectionCode(), SectionSymbols(), SectionNames()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        precision: Literal["strict", "truncate", "round"] = "strict",
        dollar_sign_currency: str | None = None,
    ) -> MoneyContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"code_amount" resolve to "code_amount", or the
                offered alternative "compact".
            precision: Over-precision amount handling. "strict" rejects
                amounts exceeding the currency's minor-unit precision (the
                default); "truncate" cuts excess digits; "round" rounds
                half-to-even to the allowed precision.
            dollar_sign_currency: ISO 4217 alpha-3 code (opt-in) used to
                resolve bare or shared symbols (e.g. "$"). None (the default)
                makes a bare "$" INVALID (recognized, but no authority
                validates it).

        Returns:
            Configured MoneyContract instance.
        """
        return MoneyContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            precision=precision,
            dollar_sign_currency=dollar_sign_currency,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: MoneyNotation,
    ) -> str:
        """Render a default code_amount canonical value in the requested format.

        The default ``"code_amount"`` path is the identity: the rule-produced
        ``CODE + " " + amount`` canonical value is returned unchanged.
        ``"compact"`` removes the single ASCII space between the code and the
        amount (``"USD 500.00"`` -> ``"USD500.00"``).

        The removal is safe because the canonical value's only ASCII space is
        the code/amount separator: the space_decimal amount shape carries a
        NARROW NO-BREAK SPACE (U+202F) in its token, never an ASCII space, so
        ``replace(" ", "", 1)`` always strips exactly the separator.

        Args:
            value: The default canonical value produced by ``Rule.normalize()``
                (``CODE + " " + amount``, e.g. ``"USD 500.00"``).
            output_format: The contract's resolved output format (``"code_amount"``
                or ``"compact"``).
            notation: The original money notation that produced the canonical
                value, retained for interface compatibility.

        Returns:
            The value rendered in the requested format.
        """
        if output_format == "compact":
            # The amount never contains an ASCII space (space_decimal uses a
            # NARROW NO-BREAK SPACE, U+202F); the only ASCII space in the
            # canonical value is the code/amount separator.
            return value.replace(" ", "", 1)
        return value
```

- [ ] **Step 4: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_capability.py
uv run ruff check paxman/capabilities/Money tests/capabilities/money
uv run pyright paxman/capabilities/Money
```

Expected: all 19 tests pass; ruff clean (line-length 88); pyright strict clean. The `paxman/core/capability.py` `ContractFactory` protocol and the keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format` first) are satisfied structurally — `tests/unit/test_capability_surface.py` re-verifies this for Money after Task 7 registers it.

Commit (stage only this task's files; `MoneyContract`/`MoneyNotation` were committed in Tasks 1–2, the rules/grammars in Tasks 4–5):

```bash
git add paxman/capabilities/Money/capability.py tests/capabilities/money/test_capability.py
git commit -m "feat(money): wire MoneyCapability with create_contract and format_value"
```
### Task 7: Capability registration and exports

**Files:**
- Modify: `paxman/capabilities/__init__.py`
- Modify: `pyproject.toml`
- Modify: `tests/unit/test_capability_exports.py`
- Modify: `tests/unit/test_capability_surface.py`

The Money package already exists and is fully tested (`tests/capabilities/money/` — capability-marked, committed in Tasks 1–6). This task makes Money a first-class citizen of the package surface: the `paxman.capabilities` export list (the registration surface), the `money` pytest marker (so `-m money` selects the Task 1–6 capability suite), and the two unit-layer guard suites that enforce export completeness and the unanimous capability surface.

- [ ] **Step 1: RED — extend the exports guard test** (`tests/unit/test_capability_exports.py`)

Replace the import line and append the Money test class. Final file:

```python
"""Tests for capability exports."""

from __future__ import annotations

import pytest

from paxman.capabilities import (
    Country,
    Date,
    Email,
    IP,
    ISBN,
    Money,
    Phone,
)


class TestCapabilityExports:
    @pytest.mark.unit
    def test_email_capability_importable(self) -> None:
        """Email capability is importable from paxman.capabilities."""
        assert Email is not None

    @pytest.mark.unit
    def test_email_capability_name(self) -> None:
        """Email capability has correct name."""
        assert Email.name == "email"


class TestCountryCapabilityExports:
    @pytest.mark.unit
    def test_country_capability_importable(self) -> None:
        """Country capability is importable from paxman.capabilities."""
        assert Country is not None

    @pytest.mark.unit
    def test_country_capability_name(self) -> None:
        """Country capability has correct name."""
        assert Country.name == "country"


class TestDateCapabilityExports:
    @pytest.mark.unit
    def test_date_capability_importable(self) -> None:
        """Date capability is importable from paxman.capabilities."""
        assert Date is not None

    @pytest.mark.unit
    def test_date_capability_name(self) -> None:
        """Date capability has correct name."""
        assert Date.name == "date"


class TestPhoneCapabilityExports:
    @pytest.mark.unit
    def test_phone_capability_importable(self) -> None:
        """Phone capability is importable from paxman.capabilities."""
        assert Phone is not None

    @pytest.mark.unit
    def test_phone_capability_name(self) -> None:
        """Phone capability has correct name."""
        assert Phone.name == "phone"


class TestISBNCapabilityExports:
    @pytest.mark.unit
    def test_isbn_capability_importable(self) -> None:
        """ISBN capability is importable from paxman.capabilities."""
        assert ISBN is not None

    @pytest.mark.unit
    def test_isbn_capability_name(self) -> None:
        """ISBN capability has correct name."""
        assert ISBN.name == "isbn"


class TestIPCapabilityExports:
    @pytest.mark.unit
    def test_ip_capability_importable(self) -> None:
        """IP capability is importable from paxman.capabilities."""
        assert IP is not None

    @pytest.mark.unit
    def test_ip_capability_name(self) -> None:
        """IP capability has correct name."""
        assert IP.name == "ip"


class TestMoneyCapabilityExports:
    @pytest.mark.unit
    def test_money_capability_importable(self) -> None:
        """Money capability is importable from paxman.capabilities."""
        assert Money is not None

    @pytest.mark.unit
    def test_money_capability_name(self) -> None:
        """Money capability has correct name."""
        assert Money.name == "money"
```

Run:

```bash
uv run pytest tests/unit/test_capability_exports.py -v
```

Expected: FAIL at collection — `ImportError: cannot import name 'Money' from 'paxman.capabilities'` (`Money` only resolves once `__init__.py` exports it).

- [ ] **Step 2: GREEN — register Money** (`paxman/capabilities/__init__.py`)

Final file:

```python
"""Paxman capabilities."""

from paxman.capabilities.Country.capability import CountryCapability as Country
from paxman.capabilities.Date.capability import DateCapability as Date
from paxman.capabilities.Email.capability import EmailCapability as Email
from paxman.capabilities.IP.capability import IPCapability as IP
from paxman.capabilities.ISBN.capability import ISBNCapability as ISBN
from paxman.capabilities.Money.capability import MoneyCapability as Money
from paxman.capabilities.Phone.capability import PhoneCapability as Phone

__all__ = ["Country", "Date", "Email", "IP", "ISBN", "Money", "Phone"]
```

Money goes between ISBN and Phone (alphabetical). The N814 per-file-ignore for this file already exists in `pyproject.toml`, so no new config is needed. The `__all__` list is the registration surface — never add an import without the matching `__all__` entry.

Add the `money` marker to `pyproject.toml` under `[tool.pytest.ini_options] markers` (alphabetical — between `isbn` and `property`):

```toml
markers = [
    "unit: unit tests",
    "capability: capability-specific tests",
    "integration: integration tests",
    "e2e: end-to-end tests",
    "property: property-based tests (Hypothesis)",
    "country: country capability tests",
    "isbn: isbn capability tests",
    "money: money capability tests",
]
```

Re-run:

```bash
uv run pytest tests/unit/test_capability_exports.py -v
```

Expected: `14 passed` (7 capability classes × 2 tests). This also closes the pre-existing gap flagged in review: the current file omits Country and Date despite AGENTS.md claiming all six exports are enforced — the rewritten file covers all seven capabilities.

**Cross-task note (marker semantics):** `pytest.mark.money` is applied per module, not per directory — the Task 1–6 suite under `tests/capabilities/money/` is `capability`-marked, and `test_data_consistency.py` (created in Task 8) additionally carries `pytest.mark.money`. Run the suite via `uv run pytest -m capability` or the directory directly (`uv run pytest tests/capabilities/money`); `-m money` selects only the modules that carry the marker, per tests/AGENTS.md.

- [ ] **Step 3: GREEN — extend the capability-surface guard test** (`tests/unit/test_capability_surface.py`)

The current file has five parametrize entries (email, date, country, ip, phone). Money slots in between ip and phone in every list, plus the `_MONEY_KEYS` set, the Money entries in `_FORMAT_SURFACES` / `_FORMATTED_EXPECTATIONS`, and the docstring bump. Replace the whole file with the version below (complete, ruff/isort-verified — every Money import sits alphabetically in the single first-party block, so no `# noqa` is needed):

```python
"""Guard tests for the unanimous capability contract & rule surface.

These tests lock the homogeneity mandate so it cannot regress: every one of
the six built-in capabilities (Email, Date, Country, IP, Money, Phone) must

- inherit :class:`CapabilityContract` (item 1),
- satisfy the :class:`ContractFactory` protocol (item 2),
- expose a keyword-only ``create_contract`` whose parameters begin with the
  unanimous common block ``excluded_rules, pinned_rules, year, output_format``
  (item 3 — guards the signature itself, which the runtime_checkable
  protocol cannot),
- keep ``output_format`` optional and resolving to the concrete default
  (item 4),
- emit a replay-deterministic ``as_dict()`` key set (item 5), and
- never return keys from ``_extra_dict_fields()`` that collide with the
  standard base keys (item 6).
"""

from __future__ import annotations

import inspect
from inspect import Parameter

import pytest

from paxman.capabilities.Country.capability import CountryCapability
from paxman.capabilities.Country.contract import CountryContract
from paxman.capabilities.Country.notation import CountryNotation
from paxman.capabilities.Date.capability import DateCapability
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Email.capability import EmailCapability
from paxman.capabilities.Email.contract import EmailContract
from paxman.capabilities.Email.notation import EmailNotation
from paxman.capabilities.IP.capability import IPCapability
from paxman.capabilities.IP.contract import IPContract
from paxman.capabilities.IP.notation import IPNotation
from paxman.capabilities.Money.capability import MoneyCapability
from paxman.capabilities.Money.contract import MoneyContract
from paxman.capabilities.Money.notation import MoneyNotation
from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.core.capability import ContractFactory
from paxman.core.capability_contract import CapabilityContract

_COMMON_BLOCK = ("excluded_rules", "pinned_rules", "year", "output_format")

_STANDARD_KEYS = frozenset(
    {"capability_name", "excluded_rules", "pinned_rules", "year", "output_format"}
)

_EMAIL_KEYS = _STANDARD_KEYS | {"include_obfuscated", "include_localhost"}
_DATE_KEYS = _STANDARD_KEYS | {"two_digit_base_year"}
_COUNTRY_KEYS = _STANDARD_KEYS | {"include_localized", "include_historical"}
_IP_KEYS = _STANDARD_KEYS | {"include_ipv6"}
_MONEY_KEYS = _STANDARD_KEYS | {"precision", "dollar_sign_currency"}
_PHONE_KEYS = _STANDARD_KEYS | {"default_country"}

_CAPABILITY_SURFACES = [
    pytest.param(
        EmailCapability,
        EmailContract,
        "email",
        _EMAIL_KEYS,
        id="email",
    ),
    pytest.param(
        DateCapability,
        DateContract,
        "ISO",
        _DATE_KEYS,
        id="date",
    ),
    pytest.param(
        CountryCapability,
        CountryContract,
        "alpha2",
        _COUNTRY_KEYS,
        id="country",
    ),
    pytest.param(
        IPCapability,
        IPContract,
        "ip",
        _IP_KEYS,
        id="ip",
    ),
    pytest.param(
        MoneyCapability,
        MoneyContract,
        "code_amount",
        _MONEY_KEYS,
        id="money",
    ),
    pytest.param(
        PhoneCapability,
        PhoneContract,
        "e164",
        _PHONE_KEYS,
        id="phone",
    ),
]


class TestContractHomogeneity:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_contracts_inherit_capability_contract(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """Every contract class inherits CapabilityContract."""
        assert issubclass(_contract_class, CapabilityContract)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_capabilities_satisfy_contract_factory(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """Every capability class satisfies the ContractFactory protocol."""
        assert isinstance(_capability, ContractFactory)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_create_contract_signature_has_unanimous_common_block(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """create_contract parameters begin with the unanimous common block.

        The runtime_checkable ``ContractFactory`` protocol only checks
        attribute presence, not the signature — so this test pins the actual
        parameter shape: the first four parameters, in order, are
        ``excluded_rules, pinned_rules, year, output_format`` and every
        parameter is keyword-only.
        """
        parameters = list(
            inspect.signature(_capability.create_contract).parameters.values()
        )
        assert [parameter.name for parameter in parameters[:4]] == list(_COMMON_BLOCK)
        assert len(parameters) >= 4
        assert all(parameter.kind == Parameter.KEYWORD_ONLY for parameter in parameters)

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_output_format_optional_in_contract_signature(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """output_format defaults to None on every contract __init__."""
        parameters = inspect.signature(_contract_class).parameters
        assert parameters["output_format"].default is None

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_output_format_none_resolves_to_concrete_default(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """A no-arg contract resolves output_format to the concrete default."""
        assert _contract_class().output_format == _default_format

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_as_dict_replay_shape(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """as_dict() emits exactly the expected replay-deterministic key set."""
        assert set(_contract_class().as_dict().keys()) == _expected_keys

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_default_format,_expected_keys",
        _CAPABILITY_SURFACES,
    )
    def test_extra_dict_fields_do_not_collide_with_standard_keys(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _default_format: str,
        _expected_keys: frozenset[str],
    ) -> None:
        """Capability-specific as_dict() keys never shadow the standard keys."""
        assert not (set(_contract_class()._extra_dict_fields()) & _STANDARD_KEYS)


# ---------------------------------------------------------------------------
# format_value surface: one formatter per capability, offered formats handled
# ---------------------------------------------------------------------------

# Real instances + concrete notations per capability. The canonical value is
# the rule-produced default representation; expectations are independent
# literals (not derived from the formatter under test).
_FORMAT_SURFACES = [
    pytest.param(
        EmailCapability,
        EmailContract,
        "user@example.com",
        EmailNotation(local_part="user", domain_part="example.com"),
        id="email",
    ),
    pytest.param(
        DateCapability,
        DateContract,
        "2026-01-15",
        DateNotation(N1="2026", N2="01", N3="15"),
        id="date",
    ),
    pytest.param(
        CountryCapability,
        CountryContract,
        "DE",
        CountryNotation(shape="alpha2", value="DE"),
        id="country",
    ),
    pytest.param(
        IPCapability,
        IPContract,
        "192.0.2.1",
        IPNotation(address="192.0.2.1"),
        id="ip",
    ),
    pytest.param(
        MoneyCapability,
        MoneyContract,
        "USD 500.00",
        MoneyNotation(
            currency_part="USD",
            amount_part="500",
            currency_shape="code",
            amount_shape="integer",
        ),
        id="money",
    ),
    pytest.param(
        PhoneCapability,
        PhoneContract,
        "+15551234567",
        PhoneNotation(shape="e164", value="15551234567"),
        id="phone",
    ),
]

# Capabilities with non-empty OFFERED_OUTPUT_FORMATS, and the independent
# literal each offered format must render for the sample canonical value.
_FORMATTED_EXPECTATIONS = [
    pytest.param(
        DateCapability,
        DateContract,
        "2026-01-15",
        DateNotation(N1="2026", N2="01", N3="15"),
        {"US": "01/15/2026"},
        id="date",
    ),
    pytest.param(
        CountryCapability,
        CountryContract,
        "DE",
        CountryNotation(shape="alpha2", value="DE"),
        {"alpha3": "DEU", "numeric": "276", "name": "GERMANY"},
        id="country",
    ),
    pytest.param(
        MoneyCapability,
        MoneyContract,
        "USD 500.00",
        MoneyNotation(
            currency_part="USD",
            amount_part="500",
            currency_shape="code",
            amount_shape="integer",
        ),
        {"compact": "USD500.00"},
        id="money",
    ),
    pytest.param(
        PhoneCapability,
        PhoneContract,
        "+15551234567",
        PhoneNotation(shape="e164", value="15551234567"),
        {"rfc3966": "tel:+15551234567", "national": "5551234567"},
        id="phone",
    ),
]

# Capabilities that offer no alternative formats: their formatter must be the
# identity regardless of the requested format.
_IDENTITY_SURFACES = [
    pytest.param(
        EmailCapability,
        EmailContract,
        "user@example.com",
        EmailNotation(local_part="user", domain_part="example.com"),
        id="email",
    ),
    pytest.param(
        IPCapability,
        IPContract,
        "192.0.2.1",
        IPNotation(address="192.0.2.1"),
        id="ip",
    ),
]


class TestFormatValueSurface:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_canonical,_notation",
        _FORMAT_SURFACES,
    )
    def test_formatter_default_agrees_with_contract_default(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _canonical: str,
        _notation: object,
    ) -> None:
        """Rendering in the contract's default format keeps the value."""
        capability = _capability()
        default_format = _contract_class.DEFAULT_OUTPUT_FORMAT
        assert capability.format_value(_canonical, default_format, _notation) == (
            _canonical
        )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_canonical,_notation,_expected_by_format",
        _FORMATTED_EXPECTATIONS,
    )
    def test_every_offered_format_renders_expected_value(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _canonical: str,
        _notation: object,
        _expected_by_format: dict[str, str],
    ) -> None:
        """Each offered format is handled by the formatter.

        The expectation table must cover exactly the capability's offered
        formats: a newly offered format with no expectation (or a stale
        expectation for a withdrawn format) fails the set-equality guard.
        """
        assert set(_contract_class.OFFERED_OUTPUT_FORMATS) == set(_expected_by_format)
        capability = _capability()
        for output_format, expected in _expected_by_format.items():
            assert (
                capability.format_value(_canonical, output_format, _notation)
                == expected
            )

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "_capability,_contract_class,_canonical,_notation",
        _IDENTITY_SURFACES,
    )
    def test_no_offered_format_capabilities_are_identity(
        self,
        _capability: type[object],
        _contract_class: type[object],
        _canonical: str,
        _notation: object,
    ) -> None:
        """Email/IP offer no formats; the formatter leaves the value unchanged."""
        assert not _contract_class.OFFERED_OUTPUT_FORMATS
        capability = _capability()
        assert (
            capability.format_value(
                _canonical, _contract_class.DEFAULT_OUTPUT_FORMAT, _notation
            )
            == _canonical
        )
        assert capability.format_value(_canonical, None, _notation) == _canonical
```

Run:

```bash
uv run pytest tests/unit/test_capability_surface.py -v
```

Expected: `54 passed` (TestContractHomogeneity 7 tests × 6 params = 42; TestFormatValueSurface 6 + 4 + 2 = 12).

Note: this guard suite is green by construction — `MoneyCapability`/`MoneyContract`/`MoneyNotation` already exist from Tasks 1–6. Its purpose is locking the homogeneity mandate (unanimous common block, replay-deterministic key sets, format surface) so Money cannot regress.

- [ ] **Step 4: Verify + commit**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py
uv run ruff check paxman/capabilities/__init__.py tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py
uv run ruff format --check tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py
uv run pyright
```

Expected: tests pass (`10` + `54`); ruff clean — run ruff only now that Money is first-party, so isort classifies `paxman.capabilities.*` correctly; format clean; pyright strict clean.

Commit (stage only this task's files):

```bash
git add paxman/capabilities/__init__.py pyproject.toml tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py
git commit -m "feat(money): register Money capability and extend export/surface guards"
```

---

### Task 8: Consistency and pipeline integration tests

**Files:**
- Create: `tests/capabilities/money/test_data_consistency.py`
- Create: `tests/integration/test_money_pipeline.py`

These two files lock the Tasks 1–6 implementation. They are green by construction (the data modules and capability already exist and were TDD-verified in their own tasks): the "RED" that matters here is any assertion failure, which signals a regression in Tasks 1–6 and must be fixed at the source — never by weakening the test or editing a baseline literal.

- [ ] **Step 1: Write the data-consistency suite** (`tests/capabilities/money/test_data_consistency.py`)

```python
"""Recognition-to-rule data consistency for the Money grammars.

Every currency representation the Money grammars recognize must be backed
by at least one authority rule-data mapping. If a recognition key had no
rule-data mapping, a grammar could emit a notation that no validation rule
can resolve — a pipeline dead end (MISSING/INVALID) for an input the
grammar explicitly claims to understand.

The assertion is deliberately one-directional: recognition keys must be a
subset of the rule-data keys. Rule data may contain additional round-trip
and lookup-only keys that no recognition key targets.

Data ownership matches the rule layer: symbols and words resolve through
the CLDR tables only, and every resolved code must exist in the ISO 4217
List One code set.
"""

from __future__ import annotations

import pytest

from paxman.capabilities.Money.grammar.data.currency_symbols import SYMBOL_TOKENS
from paxman.capabilities.Money.grammar.data.currency_words import WORD_TOKENS
from paxman.capabilities.Money.rules.data.cldr_currencies import (
    NAME_TO_CODES,
    SYMBOL_TO_CODES,
)
from paxman.capabilities.Money.rules.data.iso4217_list_one import CURRENCY_CODES

pytestmark = [pytest.mark.capability, pytest.mark.money]


def _uncovered_report(uncovered: list[str], kind: str) -> str:
    """Build a sorted, readable failure report for uncovered keys."""
    lines = [f"Recognition keys with no backing rule-data mapping ({kind}):"]
    lines.extend(f"  - {key}" for key in uncovered)
    return "\n".join(lines)


class TestRecognitionKeysAreRuleDataCovered:
    """Recognition key sets must be covered by authority rule-data maps."""

    def test_every_symbol_token_is_a_symbol_to_codes_key(self) -> None:
        """Every shipped symbol token resolves through the CLDR symbol table."""
        uncovered = sorted(set(SYMBOL_TOKENS) - set(SYMBOL_TO_CODES))
        assert not uncovered, _uncovered_report(uncovered, "symbols")

    def test_every_word_token_is_a_name_to_codes_key(self) -> None:
        """Every shipped word token resolves through the CLDR name table."""
        uncovered = sorted(set(WORD_TOKENS) - set(NAME_TO_CODES))
        assert not uncovered, _uncovered_report(uncovered, "words")

    def test_every_symbol_resolves_to_at_least_one_iso_code(self) -> None:
        """Every CLDR symbol key resolves to at least one ISO 4217 code."""
        uncovered = sorted(
            key
            for key, codes in SYMBOL_TO_CODES.items()
            if not (set(codes) & CURRENCY_CODES)
        )
        assert not uncovered, _uncovered_report(uncovered, "symbol codes")

    def test_every_word_resolves_to_at_least_one_iso_code(self) -> None:
        """Every CLDR word key resolves to at least one ISO 4217 code."""
        uncovered = sorted(
            key
            for key, codes in NAME_TO_CODES.items()
            if not (set(codes) & CURRENCY_CODES)
        )
        assert not uncovered, _uncovered_report(uncovered, "word codes")
```

Run:

```bash
uv run pytest tests/capabilities/money/test_data_consistency.py -v
```

Expected: `4 passed` (marker `capability,money`). If any test fails, the Task 3 data modules violate the one-directional coverage contract (grammar keys ⊆ rule-data keys; every rule-data key resolves to an ISO code) — fix the data module, never the test. `-m money` also selects this file from now on.

- [ ] **Step 2: Write the pipeline integration suite** (`tests/integration/test_money_pipeline.py`)

```python
"""Integration tests for the Money capability pipeline."""

import pytest

from paxman.capabilities.Money.capability import MoneyCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.engine.orchestrator import run_capability


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestMoneyPipeline:
    """Full-pipeline tests for the Money capability.

    Locked semantics:
    - the code grammar is case-sensitive ``[A-Z]{3}`` (research doc §7.2):
      lowercase ``usd 500`` is not recognized -> MISSING;
    - money only recognizes currency+amount together: a bare amount
      (``500``) or a bare currency (``USD``) alone is not recognized ->
      MISSING;
    - D6 single-currency precedence (research doc §9): a prefix symbol and
      a suffix code claiming the same amount collapse to one canonical
      value (never AMBIGUOUS). With the default ``dollar_sign_currency=None``
      the bare ``$`` yields no candidate, so ``$1,432.00 USD`` resolves via
      the suffix code (the ``$`` is non-matching context);
    - last-separator-wins amount parsing (user ruling): the final ``,`` or
      ``.`` is the decimal point, earlier separators are grouping;
    - AMBIGUOUS arises only from genuinely different canonical values:
      cross-grammar overlap (a symbol and a word both claiming the same
      amount) or multiple amounts with different currencies.
    """

    @pytest.mark.integration
    def test_success_code_prefix(self) -> None:
        """USD500 resolves to the padded canonical value."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("USD500", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 500.00"

    @pytest.mark.integration
    def test_lowercase_code_missing(self) -> None:
        """The code grammar is case-sensitive; lowercase codes are MISSING."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("usd 500", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_success_qualified_symbol(self) -> None:
        """US$50.79 resolves via the qualified symbol to USD."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("US$50.79", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 50.79"

    @pytest.mark.integration
    def test_success_code_suffix(self) -> None:
        """100MYR resolves via the suffix code."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("100MYR", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MYR 100.00"

    @pytest.mark.integration
    def test_success_word(self) -> None:
        """18 Dollar resolves via the CLDR word table to USD."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("18 Dollar", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 18.00"

    @pytest.mark.integration
    def test_bare_symbol_default_contract_invalid(self) -> None:
        """$500 with the default contract (dollar_sign_currency=None) is INVALID."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("$500", contract)
        assert result.status == Resolution.INVALID
        assert result.candidates == ()

    @pytest.mark.integration
    def test_bare_symbol_opt_in_dollar_sign_currency(self) -> None:
        """$500 with dollar_sign_currency=MYR resolves to MYR 500.00."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract(dollar_sign_currency="MYR")
        result = run_capability("$500", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "MYR 500.00"

    @pytest.mark.integration
    def test_bare_symbol_explicit_none_invalid(self) -> None:
        """$500 with dollar_sign_currency=None is recognized but unvalidated."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract(dollar_sign_currency=None)
        result = run_capability("$500", contract)
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_suffix_code_wins_over_unresolvable_symbol(self) -> None:
        """D6: $1,432.00 USD collapses to one canonical value, never AMBIGUOUS.

        With the default dollar_sign_currency=None the bare $ yields no
        candidate (SectionSymbols.matches() -> False), so the suffix code is
        the sole candidate: SUCCESS "USD 1432.00" with exactly one candidate.
        (Oracle review finding: this single-candidate assertion only holds
        because the symbol candidate is absent — under the old
        default_currency="USD" two same-valued candidates survived.)
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("$1,432.00 USD", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 1432.00"
        assert len(result.candidates) == 1
        assert {c.recognition_rule for c in result.candidates} == {"code_recognition"}

    @pytest.mark.integration
    def test_comma_decimal_european(self) -> None:
        """1.000,50 EUR: last separator is the decimal point."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("1.000,50 EUR", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "EUR 1000.50"

    @pytest.mark.integration
    def test_mixed_separators_last_wins(self) -> None:
        """1,00.50 USD: last separator (.) is the decimal point."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("1,00.50 USD", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "USD 1000.50"

    @pytest.mark.integration
    def test_success_definitive_symbol(self) -> None:
        """€5 resolves via the definitive EUR symbol."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("\u20ac5", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "EUR 5.00"

    @pytest.mark.integration
    def test_missing(self) -> None:
        """Nothing recognized."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("gibberish", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_bare_amount_missing(self) -> None:
        """A bare amount without a currency is not a money token (MISSING)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("500", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_bare_currency_missing(self) -> None:
        """A bare currency without an amount is not a money token (MISSING)."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("USD", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_cross_grammar_ambiguous(self) -> None:
        """A symbol and a word claiming the same amount are AMBIGUOUS.

        The euro symbol and the word Dollar both claim the amount 18; the
        engine keeps cross-grammar overlaps, so two different canonical
        values emerge.
        """
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("18 \u20ac Dollar", contract)
        assert result.status == Resolution.AMBIGUOUS
        assert result.canonicalized_value is None
        assert {c.value for c in result.candidates} == {"EUR 18.00", "USD 18.00"}

    @pytest.mark.integration
    def test_multi_amount_ambiguous(self) -> None:
        """Two amounts with different currencies yield AMBIGUOUS."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result = run_capability("USD 100 and EUR 200", contract)
        assert result.status == Resolution.AMBIGUOUS
        assert result.canonicalized_value is None

    @pytest.mark.integration
    def test_version_stamp(self) -> None:
        """Replay hash is present and deterministic."""
        register_capability(MoneyCapability())
        contract = MoneyCapability.create_contract()
        result1 = run_capability("USD500", contract)
        result2 = run_capability("USD500", contract)
        assert result1.version_stamp.replay_hash == result2.version_stamp.replay_hash
        assert len(result1.version_stamp.replay_hash) == 64  # SHA-256 hex
```

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

Run:

```bash
uv run pytest tests/integration/test_money_pipeline.py -v
```

Expected: `18 passed` (marker `integration`).

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/money/test_data_consistency.py tests/integration/test_money_pipeline.py
uv run ruff check tests/capabilities/money/test_data_consistency.py tests/integration/test_money_pipeline.py
uv run ruff format --check tests/capabilities/money/test_data_consistency.py tests/integration/test_money_pipeline.py
```

Expected: all tests pass (`4` + `18`); ruff clean (isort satisfies the canonical grouping: grammar/data then rules/data imports in one first-party block; `paxman.capabilities.Money.*` then `paxman.core.*`/`paxman.engine.*`); format clean.

Commit:

```bash
git add tests/capabilities/money/test_data_consistency.py tests/integration/test_money_pipeline.py
git commit -m "test(money): lock grammar-rule data coverage and pipeline semantics"
```

---

### Task 9: Property tests

**Files:**
- Create: `tests/property/test_money_properties.py`

```python
"""Hypothesis property tests for the Money capability.

Each property locks a mathematical invariant of parsing, formatting, or the
full pipeline using an independently derived expectation:

- repeated runs over the same input and contract are byte-identical
  (replay safety);
- format_amount then parse_amount round-trips the value for conforming
  precision;
- random ASCII input never raises and every status is well-formed;
- every SUCCESS canonical value matches ``CODE amount`` shape and carries
  exactly the code's ISO 4217 minor units.
"""

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

from __future__ import annotations

import re
import string
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.Money.capability import MoneyCapability
from paxman.capabilities.Money.parsing import ParsedAmount, format_amount, parse_amount
from paxman.capabilities.Money.rules.data.iso4217_list_one import MINOR_UNITS
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.engine.orchestrator import run_capability

_CANONICAL_SHAPE = re.compile(r"[A-Z]{3} \d+(\.\d+)?")


@pytest.fixture(autouse=True)
def _fresh_registry() -> None:
    """Reset the registry and register Money before and after each test.

    Registration happens once per test, before the hypothesis examples run;
    ``run_capability`` freezes the registry on the first example, which is
    fine because the capability is already present.
    """
    reset_registry()
    register_capability(MoneyCapability())
    yield
    reset_registry()


@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_replay_determinism(text: str) -> None:
    """Same input + same contract -> byte-identical ExecutionResult."""
    contract = MoneyCapability.create_contract()
    result1 = run_capability(text, contract)
    result2 = run_capability(text, contract)
    assert result1 == result2
    assert result1.version_stamp.replay_hash == result2.version_stamp.replay_hash

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

@pytest.mark.property
@given(
    integer=st.text(alphabet=string.digits, min_size=1, max_size=9),
    fraction=st.text(alphabet=string.digits, min_size=0, max_size=2),
)
def test_parse_format_round_trip_preserves_value(
    integer: str, fraction: str
) -> None:
    """format_amount then parse_amount returns the same value."""
    parsed = ParsedAmount(integer=integer.lstrip("0") or "0", fraction=fraction)
    assert parsed.decimal_digits() <= 2
    formatted = format_amount(parsed, 2, "strict")
    reparsed = parse_amount(formatted)
    assert reparsed is not None
    assert Decimal(reparsed.to_decimal_string()) == Decimal(parsed.to_decimal_string())
    assert format_amount(reparsed, 2, "strict") == formatted


@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_fuzz_random_text_never_raises(text: str) -> None:
    """Random ASCII input never raises; every status is well-formed."""
    contract = MoneyCapability.create_contract()
    result = run_capability(text, contract)
    assert result.status in {
        Resolution.MISSING,
        Resolution.INVALID,
        Resolution.SUCCESS,
        Resolution.AMBIGUOUS,
    }
    assert (result.canonicalized_value is not None) == (
        result.status == Resolution.SUCCESS
    )
    assert len(result.version_stamp.replay_hash) == 64

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_success_canonical_shape(text: str) -> None:
    """Every SUCCESS value matches CODE amount with the code's minor units."""
    contract = MoneyCapability.create_contract()
    result = run_capability(text, contract)
    if result.status != Resolution.SUCCESS:
        return
    value = result.canonicalized_value
    assert value is not None
    assert _CANONICAL_SHAPE.fullmatch(value) is not None
    code, _, amount = value.partition(" ")
    if "." in amount:
        assert len(amount.split(".", 1)[1]) == MINOR_UNITS[code]
    else:
        assert MINOR_UNITS[code] == 0
```

**Registry note (assumption flagged):** tests/AGENTS.md says property tests "must stay off the registry and the frozen pipeline" and keep to grammar/rule/`format_value` inputs. This file deliberately drives the full `run_capability` pipeline instead, because three of the four properties lock *pipeline-level* invariants (replay determinism, status well-formedness, canonical-shape + minor-unit padding) that unit-level inputs cannot express. The deviation is safe and documented in the fixture: the registry is reset before and after every test and the capability is registered *before* the first hypothesis example runs; `run_capability` freezes the registry on the first example, which is fine because Money is already present. No ambient registry state can leak across tests.

- [ ] **Step 1: Write the property suite** (content above)
- [ ] **Step 2: Run**

```bash
uv run pytest tests/property/test_money_properties.py -v
```

Expected: `4 passed` (hypothesis "ci" profile — `max_examples=100`, `deadline=None` — loaded by `tests/conftest.py`; do not override per test).

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/property/test_money_properties.py
uv run ruff check tests/property/test_money_properties.py
uv run ruff format --check tests/property/test_money_properties.py
```

Expected: `4 passed`; ruff clean; format clean.

Commit:

```bash
git add tests/property/test_money_properties.py
git commit -m "test(money): add property-based invariants for parsing and pipeline"
```

---

### Task 10: Replay-hash baseline

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

**Files:**
- Modify: `tests/integration/test_default_replay_hashes.py`

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

The replay hash is the engine's behavioral contract: any pipeline change that alters the candidate set, provenance set, or serialized contract shifts a hash and fails here. Adding Money to the baseline is an *addition* — the six existing literals must not change (nothing about the existing pipelines changed in Tasks 7–9). The Money literal is captured from the engine, not invented; this plan cannot (and must not) predict it.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

- [ ] **Step 1: RED — add the Money case with a placeholder**

Edit `tests/integration/test_default_replay_hashes.py`:

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

1. Add the import between ISBN and Phone (alphabetical):

```python
from paxman.capabilities.Money.capability import MoneyCapability
```

2. Rewrite the stale NOTE comment (lines 25–27 claim IP is NOT auto-registered and list the exports as five capabilities; after Task 7 the exports are Country, Date, Email, IP, ISBN, Money, Phone):

```python
# NOTE: each case registers its capability explicitly. The
# paxman/capabilities/__init__.py exports (Country, Date, Email, IP, ISBN,
# Money, Phone) are a packaging surface, not a registry side effect.
```

3. Add the Money baseline placeholder to `BASELINE_HASHES` (after `isbn`):

```python
    "money": "0" * 64,
```

4. Add the Money case to `CASES` (after `isbn`):

```python
(("money", MoneyCapability, "USD500"),)
```

5. Update the module docstring: append a line after the ISBN line:

```python
ISBN baseline added 2026-08-05. Money baseline added 2026-08-06.
```

Run:

```bash
uv run pytest tests/integration/test_default_replay_hashes.py -v
```

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

Expected: `1 failed, 6 passed` — the `money` case fails with `assert <64-char actual hash> == '0000000000000000000000000000000000000000000000000000000000000000'`. The failure output shows the engine's real replay hash for `("money", MoneyCapability, "USD500")`.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

- [ ] **Step 2: GREEN — capture the actual hash**

Copy the 64-char actual hash from the assertion failure into `BASELINE_HASHES`, replacing the placeholder:

```python
    "money": "<actual 64-char hash from the failure output>",
```

Re-run:

```bash
uv run pytest tests/integration/test_default_replay_hashes.py -v
```

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

Expected: `7 passed`. Do NOT touch the six existing literals — if any of them fail, stop and investigate the regression (a Money change must not shift existing pipelines' hashes).

- [ ] **Step 3: Verify + commit**

```bash
uv run pytest tests/integration/
uv run ruff check tests/integration/test_default_replay_hashes.py
uv run ruff format --check tests/integration/test_default_replay_hashes.py
```

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

Expected: the whole integration suite passes; ruff clean; format clean.

Commit:

```bash
git add tests/integration/test_default_replay_hashes.py
git commit -m "test(money): baseline replay hash for the Money capability"
```

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

---

### Task 11: Documentation and full pre-PR gate

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `paxman/capabilities/AGENTS.md`
- Modify: `tests/AGENTS.md`

- [ ] **Step 1: README.md**

1. Capabilities intro and table. Change "Paxman ships with six built-in capabilities:" to "Paxman ships with seven built-in capabilities:" and add a Money row to the table (alphabetically, after ISBN):

```markdown
| **Money** | Money amounts | 3 (code, symbol, word) | 3 | ISO 4217, CLDR |
```

2. Add a Money section between the ISBN and Phone sections:

````markdown
### Money Capability

Recognizes ISO 4217 codes, CLDR currency symbols, and CLDR currency names adjacent to amounts, canonicalizing to `CODE + amount` padded to ISO 4217 minor units.

```python
from paxman.capabilities import Money

register_capability(Money())

# Code + amount
contract = Money.create_contract()
result = paxman.canonicalize("USD500", contract)
# → "USD 500.00"

# Bare $ is unresolved by default: INVALID (recognized, no authority)
contract = Money.create_contract()
result = paxman.canonicalize("$500", contract)
# → Status: INVALID

# Opt in: bare $ resolves via dollar_sign_currency
contract = Money.create_contract(dollar_sign_currency="MYR")
result = paxman.canonicalize("$500", contract)
# → "MYR 500.00"

# European comma-decimal: last separator is the decimal point
contract = Money.create_contract()
result = paxman.canonicalize("1.000,50 EUR", contract)
# → "EUR 1000.50"

# Compact rendering removes the code/amount separator space
contract = Money.create_contract(output_format="compact")
result = paxman.canonicalize("USD500", contract)
# → "USD500.00"
```
````

3. Capability-Specific Parameters table — add Money rows (after the ISBN rows, before Phone):

```markdown
| Money | `precision` | `str` | Over-precision amount handling: `"strict"` (reject), `"truncate"`, `"round"` (default: `"strict"`) |
| Money | `dollar_sign_currency` | `str` \| `None` | ISO 4217 alpha-3 code resolving bare/shared symbols (opt-in); `None` (default) makes bare symbols INVALID |
| Money | `output_format` | `str` | Output format (`"code_amount"` default, `"compact"`) |
```

- [ ] **Step 2: AGENTS.md files** (the 6→7 / six→seven sweep)

1. Root `AGENTS.md`:
   - OVERVIEW: `6 capabilities (Country, Date, Email, IP, ISBN, Phone)` → `7 capabilities (Country, Date, Email, IP, ISBN, Money, Phone)`
   - NOTES: `exports all six capabilities (Country, Date, Email, IP, ISBN, Phone)` → `exports all seven capabilities (Country, Date, Email, IP, ISBN, Money, Phone)`

2. `paxman/capabilities/AGENTS.md`:
   - OVERVIEW: `6 capability packages (Country, Date, Email, IP, ISBN, Phone)` → `7 capability packages (Country, Date, Email, IP, ISBN, Money, Phone)`
   - NOTES: `exports all six capabilities` → `exports all seven capabilities`

3. `tests/AGENTS.md`:
   - OVERVIEW: `5 layers, 6 capability packages.` → `5 layers, 7 capability packages.`
   - STRUCTURE: `(country, date, email, ip, isbn, phone)` → `(country, date, email, ip, isbn, money, phone)`
   - CONVENTIONS: `(marker -m isbn also exists for country/isbn)` → `(markers -m isbn and -m money also exist for country/isbn/money)`

- [ ] **Step 3: Full pre-PR gate**

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run import-linter lint
uv run pytest
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/{core,capabilities,engine,api}/*" --fail-under=95
```

Expected: ruff clean; format clean; pyright strict clean; import-linter clean (Money imports only from `paxman.core` — no cross-capability imports); the whole test suite passes (existing six capabilities' replay hashes unchanged, money suite included); coverage ≥ 95% overall and per package. If the Money package reports below 95%, add targeted unit cases under `tests/capabilities/money/` to cover the gaps — never lower the gate.

> **Note — replay-hash removed; do not use as a sample.** The `replay_hash` (replay-hash / byte-identical canonicalization) mechanism referenced in the paragraph above was **removed** from Paxman (see `docs/adr/0002-remove-replay-hash.md`). The text above reflects the pre-removal design and MUST NOT be copied, adapted, or used as a template for future work.

- [ ] **Step 4: Commit**

```bash
git add README.md AGENTS.md paxman/capabilities/AGENTS.md tests/AGENTS.md
git commit -m "docs(money): document Money capability and update capability counts"
```
