# Currency Capability Implementation Plan

| | |
|---|---|
| **Date** | 2026-08-08 |
| **Status** | Draft — ready for review |
| **Author** | Sisyphus |
| **Branch** | `feature/currency-capability` (create before Task 1; commit per task) |
| **Milestone** | `docs/development/MILESTONE.md` row #1 — Currency (ISO 4217, LOOKUP_TABLE strategy) |
| **Sibling template** | `paxman/capabilities/Money/` (currency **+ amount**) — Currency is the identifier-only variant |

> **For agentic workers — REQUIRED SUB-SKILLS:** `test-driven-development` (RED → GREEN → refactor per task), `using-git-worktrees` (isolated workspace before Task 1). Every task ends with a verify command and an atomic commit whose message is given in the task header. The executor is treated as having **zero context**: every file to create, every pattern to mirror, and every assertion matrix is specified below. Follow the embedded code verbatim — it was verified against the live Money/Country sources.

---

## 1. Cross-Part Contract (must stay identical across all tasks)

### Goal

Canonicalize **currency identifiers** — an ISO 4217 alpha-3 code, a CLDR currency symbol, or a CLDR display-name word — to the canonical uppercase alpha-3 code, with full provenance. **Identifier-only: no amounts.** Amounts are the Money capability's domain. The Milestone examples must hold: `"US$" → "USD"`, `"euro" → "EUR"`, `"GBP" → "GBP"`.

### D-Decisions (locked — do not revisit without a new ADR)

1. **Provenance: ONE SectionCode rule for "ISO 4217:2015 as amended".** Research (2026-08-08, SIX amendment series + ISO store + ISO OBP/RSS) established that **no document "ISO 4217 Amendment 17" exists for the 2015 edition**. The literal *MA Amendment No. 17* amended ISO 4217:**1981** (Brazil → CRUZADO/BRC, 4 Mar 1986). The 2015 edition (5 pages) deliberately contains **no code list** — the normative code data lives in the ISO 4217 Maintenance Agency (SIX Financial Information AG) List One/Two/Three, updated by a sequential amendment-notice series now at **#180** (2025-09-22, Bulgaria BGN→EUR). Therefore: one rule file `iso_4217_ed2015.py`, `PUBLICATION` = ISO 4217:2015 (base, `publication_year=2015`), code data derived from the **SIX List One snapshot 2026-01-01** (178 distinct codes). The rule's `citation` names the amendment series explicitly. The Milestone's "ISO 4217 Amendment 17" string is **not** used verbatim anywhere. (Rejected alternative: one rule per amendment — 21+ post-2015 notices, mostly name corrections; fragments a single lookup table across files.)
2. **Full code set.** `CURRENCY_CODES` includes **all 178** List One codes — including the 13 with minor unit "N.A." (`XAG XAU XBA XBB XBC XBD XDR XPD XPT XSU XTS XUA XXX`) that the Money capability excludes. Money's exclusion is amount-driven (no minor units to pad); Currency canonicalizes identifiers, and `"XAU" → "XAU"` is correct. This is a **deliberate divergence** from Money's 165-code set — document it in the data module docstring. Current List One also includes post-2015 entries `ZWG`, `VES`, `VED`, `SLE`, `XAD`, `XCG`; `ZWL`, `SLL`, `BGN`, `ANG`, `HRK` are historic (List Three) and NOT in the set.
3. **Code grammar is case-insensitive with grammar-owned case folding.** `"usd" → "USD"` is a Milestone requirement; Money's uppercase-only `[A-Z]{3}` code grammar would reject it. Currency mirrors the **Country** precedent exactly: pattern `[A-Za-z]{3}`, grammar emits the token uppercased (`match.group("code").upper()`), rule is a pure table lookup.
4. **Word grammar folds to lowercase; `NAME_TO_CODES` keys are lowercase.** Money's Title-Case keys + as-written lookup make `"500 euro"` INVALID in Money today. The Milestone requires `"euro" → "EUR"`. Currency's word grammar emits the token lowercased (`match.group(0).lower()`); the data table stores lowercase keys; the rule is a pure lookup. Symbols stay **case-exact** (no folding — glyph strings).
5. **Standalone tokens only.** Grammars never couple to an amount (no `AMOUNT_PATTERN` anywhere — deliberate divergence from Money's amount-coupled patterns). Whole-token discipline: `"US$5"`, `"$500"`, `"USD500"` are amount-glued → **MISSING** (never partial-matched). The **sign-blocking lookarounds** `(?<![\w\-+\u2212])` / `(?![\w\-+\u2212])` from Money's grammars are kept.
6. **Shared-symbol resolution via `default_currency`.** Multi-candidate bare symbols (`"$"` → 29 dollar-family codes, `"¥"` → CNY/JPY, `"₩"`) are **INVALID** unless the contract opts in with `default_currency`. The resolver gates the opt-in against `CURRENCY_CODES` (a shape-valid-but-unknown default can never produce SUCCESS). `default_currency` never remaps a definitive symbol (`"€" → EUR`) or a qualified symbol (`"US$" → USD`). Param name is `default_currency` (parallels Phone's `default_country`), **not** Money's amount-era `dollar_sign_currency`.
7. **No cross-capability imports (import-linter enforced).** Currency vendors its **own** data tables via a temporary derivation script; it never imports from `paxman.capabilities.Money.*`.
8. **No offered output formats.** `DEFAULT_OUTPUT_FORMAT = "code"`, `OFFERED_OUTPUT_FORMATS = frozenset()`. The Capability base's identity `format_value()` is used — **do not override** (rules never read `output_format`; `format_value` is the only presentation seam).

### Capability surface

| Aspect | Value |
|---|---|
| Package | `paxman/capabilities/Currency/` |
| Capability name | `"currency"` |
| Version | `"1.0.0"` |
| Grammars (3) | `code_recognition`, `symbol_recognition`, `word_recognition` |
| Rules (3) | `Section-code` (ISO 4217:2015 as-amended), `Section-symbols` (CLDR v47), `Section-names` (CLDR v47) |
| Notation | `CurrencyNotation(text: str, shape: str)` — shapes `code` / `qualified_symbol` / `symbol` / `word` |
| Contract param | `default_currency: str | None = None` (validated uppercase alpha-3; opt-in for shared bare symbols) |
| Output format | `"code"` (canonical = uppercase alpha-3); no offered alternatives |
| Canonical value | The uppercase alpha-3 code (`"USD"`, `"EUR"`, `"GBP"`) |

### Module layout (mirrors Money exactly)

```text
paxman/capabilities/Currency/
├── __init__.py                  # exports CurrencyCapability, CurrencyContract, CurrencyNotation
├── notation.py                  # CurrencyNotation (frozen, slots=True)
├── contract.py                  # CurrencyContract (frozen, NO slots)
├── capability.py                # CurrencyCapability + static create_contract (identity format_value)
├── grammar/
│   ├── __init__.py
│   ├── code_recognition.py      # CodeRecognition
│   ├── symbol_recognition.py    # SymbolRecognition
│   ├── word_recognition.py      # WordRecognition
│   └── data/
│       ├── __init__.py
│       ├── currency_symbols.py  # SYMBOL_TOKENS (qualified-first, longest-first)
│       └── currency_words.py    # WORD_TOKENS (longest-first)
└── rules/
    ├── __init__.py
    ├── iso_4217_ed2015.py       # SectionCode  (PUBLICATION year=2015)
    ├── cldr_currencies_ed2025.py# SectionSymbols + SectionNames (PUBLICATION CLDR v47)
    └── data/
        ├── __init__.py
        ├── iso4217_list_one.py  # CURRENCY_CODES: frozenset[str] — all 178 codes
        └── cldr_currencies.py   # SYMBOL_TO_CODES, NAME_TO_CODES (keys: lowercase words)
```

### e2e contract (the semantic lock — used verbatim by Tasks 8 and 10)

| Input | Contract | Status | Canonical value |
|---|---|---|---|
| `"USD"` | default | SUCCESS | `"USD"` |
| `"usd"` | default | SUCCESS | `"USD"` (D3: case-insensitive code) |
| `"Gbp"` | default | SUCCESS | `"GBP"` |
| `"GBP"` | default | SUCCESS | `"GBP"` (Milestone) |
| `"US$"` | default | SUCCESS | `"USD"` (qualified symbol — Milestone) |
| `"€"` | default | SUCCESS | `"EUR"` (definitive bare symbol) |
| `"£"` | default | SUCCESS | `"GBP"` (definitive bare symbol) |
| `"$"` | default | INVALID | — (shared: 29 candidates, no opt-in) |
| `"$"` | `default_currency="USD"` | SUCCESS | `"USD"` |
| `"¥"` | `default_currency="CNY"` | SUCCESS | `"CNY"` |
| `"euro"` | default | SUCCESS | `"EUR"` (lowercase word — Milestone; D4) |
| `"Euro"` | default | SUCCESS | `"EUR"` |
| `"US Dollar"` | default | SUCCESS | `"USD"` (via the `"Dollar"` span → `"dollar"` → USD; `"US"` matches nothing) |
| `"XAU"` | default | SUCCESS | `"XAU"` (D2: full set) |
| `"ZZZ"` | default | INVALID | — (3-letter shape, unknown code) |
| `"the"` | default | INVALID | — (3-letter shape, not a code; accepted shape-only false positive, Country parity) |
| `"Dollars"` | default | INVALID | — (plural not in table; word-boundary guard) |
| `"USD 500"` | default | SUCCESS | `"USD"` (via the code span; the amount is Money's domain) |
| `"US$5"` | default | MISSING | — (amount-glued token, whole-token discipline; D5) |
| `"$500"` | default | MISSING | — (same) |
| `"hello world"` | default | MISSING | — (no identifier-shaped token) |
| `"123"` | default | MISSING | — |
| `""` | default | MISSING | — |

Provenance rows: `"USD"` → ISO 4217 (Section-code); `"€"` → CLDR (Section-symbols); `"euro"` → CLDR (Section-names).

Contract-error rows: `create_contract(default_currency="usd")`, `= "US"`, `= "USDD"`, `= 123` → all raise `ContractError`.

---

## 2. Implementation Tasks

Work in the `feature/currency-capability` branch. Each task: **Step 1 RED** (write the failing test) → **Step 2 verify it fails** → **Step 3 GREEN** (implement) → **Step 4 verify passes + commit**. Command verbatim: `uv run pytest <target> -v`. Test modules use module-level `pytestmark = [pytest.mark.capability, pytest.mark.currency]` (unit/capability-level tasks) — the `currency` marker is added in Task 7.

### Task 1: `feat(currency): add CurrencyNotation and package skeleton`

- [ ] **Step 1: RED** — `tests/capabilities/currency/test_notation.py` mirroring `tests/capabilities/money/test_notation.py`:

```python
# tests/capabilities/currency/test_notation.py
"""CurrencyNotation structural tests."""

from __future__ import annotations

import pytest

from paxman.capabilities.Currency.notation import CurrencyNotation

pytestmark = [pytest.mark.capability, pytest.mark.currency]


def test_frozen() -> None:
    notation = CurrencyNotation(text="USD", shape="code")
    with pytest.raises(AttributeError):
        notation.text = "EUR"  # type: ignore[misc]


def test_as_list() -> None:
    assert CurrencyNotation(text="US$", shape="qualified_symbol").as_list() == [
        "US$",
        "qualified_symbol",
    ]


@pytest.mark.parametrize(
    ("text", "shape"),
    [
        ("USD", "code"),
        ("usd", "code"),  # grammar folds; the notation may hold any casing pre-fold
        ("US$", "qualified_symbol"),
        ("€", "symbol"),
        ("euro", "word"),
    ],
)
def test_valid_shapes(text: str, shape: str) -> None:
    assert CurrencyNotation(text=text, shape=shape).shape == shape


@pytest.mark.parametrize(
    ("text", "shape"),
    [
        ("", "code"),
        ("USD", "amount"),  # not an identifier shape
        ("USD", "code+amount"),  # Money's shape vocabulary is out of scope
    ],
)
def test_invalid(text: str, shape: str) -> None:
    with pytest.raises(ValueError):
        CurrencyNotation(text=text, shape=shape)
```

- [ ] **Step 2:** `uv run pytest tests/capabilities/currency/test_notation.py -v` → fails to import (no package).

- [ ] **Step 3: GREEN** — package skeleton + `notation.py` (verbatim):

```python
# paxman/capabilities/Currency/__init__.py
"""Currency capability package."""

# paxman/capabilities/Currency/grammar/__init__.py
"""Currency recognition grammars."""

# paxman/capabilities/Currency/grammar/data/__init__.py
"""Currency grammar data tables."""

# paxman/capabilities/Currency/rules/__init__.py
"""Currency validation rules."""

# paxman/capabilities/Currency/rules/data/__init__.py
"""Currency rule data tables."""
```

```python
# paxman/capabilities/Currency/notation.py
"""Currency notation — an ISO 4217 currency identifier as written."""

from __future__ import annotations

from dataclasses import dataclass

_VALID_SHAPES = frozenset({"code", "qualified_symbol", "symbol", "word"})


@dataclass(frozen=True, slots=True)
class CurrencyNotation:
    """A currency identifier (no amount) as written in the input.

    Attributes:
        text: The identifier text. Codes are grammar-folded to uppercase
            and words to lowercase (grammar-owned case folding); symbols
            keep their exact casing.
        shape: One of "code", "qualified_symbol", "symbol", "word".
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

- [ ] **Step 4:** `uv run pytest tests/capabilities/currency -v` → pass (test_notation only). `uv run ruff check paxman/capabilities/Currency/ tests/capabilities/currency/` → clean. Commit `feat(currency): add CurrencyNotation and package skeleton`.

### Task 2: `feat(currency): add CurrencyCapabilityContract`

- [ ] **Step 1: RED** — `tests/capabilities/currency/test_contract.py` mirroring `tests/capabilities/money/test_contract.py`:

```python
# tests/capabilities/currency/test_contract.py
"""CurrencyContract configuration tests."""

from __future__ import annotations

import pytest

from paxman.capabilities.Currency.contract import CurrencyContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability, pytest.mark.currency]


def test_capability_name() -> None:
    assert CurrencyContract().capability_name == "currency"


def test_active_grammars() -> None:
    assert CurrencyContract().active_grammars == (
        "code_recognition",
        "symbol_recognition",
        "word_recognition",
    )


def test_default_output_format_resolution() -> None:
    assert CurrencyContract().output_format == "code"
    assert CurrencyContract(output_format=None).output_format == "code"
    assert CurrencyContract(output_format="default").output_format == "code"
    assert CurrencyContract(output_format="code").output_format == "code"


def test_unsupported_output_format_rejected() -> None:
    with pytest.raises(ContractError):
        CurrencyContract(output_format="compact")  # Money's format, not offered here


def test_default_currency_default_is_none() -> None:
    assert CurrencyContract().default_currency is None


@pytest.mark.parametrize("value", ["usd", "US", "USDD", "U5D", 123, None, ""])
def test_invalid_default_currency(value: object) -> None:
    if value is None:
        return
    with pytest.raises(ContractError):
        CurrencyContract(default_currency=value)  # type: ignore[arg-type]


def test_valid_default_currency() -> None:
    assert CurrencyContract(default_currency="USD").default_currency == "USD"


def test_as_dict_replay_keys() -> None:
    d = CurrencyContract(default_currency="USD").as_dict()
    assert d["capability_name"] == "currency"
    assert d["output_format"] == "code"
    assert d["default_currency"] == "USD"
    assert set(d) >= {
        "capability_name",
        "excluded_rules",
        "pinned_rules",
        "year",
        "output_format",
        "default_currency",
    }


def test_common_block() -> None:
    c = CurrencyContract(
        excluded_rules=("Section-code",),
        pinned_rules=None,
        year=2020,
    )
    assert c.excluded_rules == ("Section-code",)
    assert c.year == 2020
```

- [ ] **Step 2:** verify it fails (no module).

- [ ] **Step 3: GREEN** — `contract.py` (verbatim; mirrors `Money/contract.py` — frozen, **no slots**, `super().__post_init__()` first, `_extra_dict_fields()` override, never hand-written `as_dict()`):

```python
# paxman/capabilities/Currency/contract.py
"""Currency contract — user-facing configuration for Currency capability."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, cast

from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import ContractError


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
            "default_currency must be an uppercase ISO 4217 alpha-3 code, "
            f"got {value!r}"
        )
    if (
        len(candidate) != 3
        or not candidate.isascii()
        or not candidate.isalpha()
        or not candidate.isupper()
    ):
        raise ContractError(
            "default_currency must be an uppercase ISO 4217 alpha-3 code, "
            f"got {value!r}"
        )


@dataclass(frozen=True)
class CurrencyContract(CapabilityContract):
    """User-facing configuration for Currency capability.

    Attributes:
        capability_name: Fixed to "currency" (not user-settable).
        default_currency: ISO 4217 alpha-3 code (opt-in) used to resolve
            shared bare symbol input (e.g. "$", "¥"). Defaults to None:
            a shared bare symbol is then recognized but never resolved
            (status INVALID). Never remaps a definitive symbol (e.g.
            "€" -> EUR) or a qualified symbol ("US$" -> USD).
        output_format: Canonical output format — "code" (the uppercase
            alpha-3 code) is the only format. Optional — None/"default"/
            "code" all resolve to "code".
        excluded_rules: Tuple of rule names to exclude.
        pinned_rules: Pin to specific rules (takes precedence over excluded_rules).
        year: Year for temporal filtering.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "code"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset()

    capability_name: str = field(default="currency", init=False)

    # Capability-specific field
    default_currency: str | None = None

    def __post_init__(self) -> None:
        """Validate contract configuration.

        Calls the base output_format resolution first, then enforces
        Currency-specific rules: default_currency must be an uppercase
        ISO 4217 alpha-3 code when present.

        Raises:
            ContractError: If output_format is unsupported or
                default_currency is present but not an uppercase alpha-3
                code.
        """
        super().__post_init__()
        _validate_alpha3(self.default_currency)

    @property
    def active_grammars(self) -> tuple[str, ...]:
        """All grammars active by default.

        All three recognition grammars are always active; Currency has no
        input-shape feature flags.

        Returns:
            The three recognition grammar names.
        """
        return ("code_recognition", "symbol_recognition", "word_recognition")

    def _extra_dict_fields(self) -> dict[str, object]:
        """Serialize capability-specific fields for replay hash.

        Returns:
            Dictionary of the default_currency field.
        """
        return {"default_currency": self.default_currency}
```

- [ ] **Step 4:** `uv run pytest tests/capabilities/currency -v` → pass; ruff clean. Commit `feat(currency): add CurrencyCapabilityContract`.

### Task 3: `feat(currency): add ISO 4217 and CLDR data tables`

- [ ] **Step 1: RED** — `tests/capabilities/currency/test_data.py` (mirror `tests/capabilities/money/test_data.py`): locked counts, structure checks, ordering checks, filter checks, spot checks. Lock these counts by running the derivation script once, **then** freeze them in the test:

```python
# tests/capabilities/currency/test_data.py
"""Currency data-table structure, ordering, and filter tests."""
# (module-level pytestmark; parametrized checks:)

# CURRENCY_CODES (rules/data/iso4217_list_one.py)
#   - frozenset[str]; every code matches ^[A-Z]{3}$
#   - len == 178                       (D2: FULL List One, incl. the 13 N.A. codes)
#   - superset checks (locked literals):
#       {"USD", "EUR", "GBP", "JPY", "MYR"} <= CURRENCY_CODES
#       {"XAG", "XAU", "XBA", "XBB", "XBC", "XBD", "XDR", "XPD", "XPT",
#        "XSU", "XTS", "XUA", "XXX"} <= CURRENCY_CODES        # D2 divergence from Money
#   - post-amendment entries present: {"ZWG", "VES", "VED", "SLE", "XAD", "XCG"} <= CURRENCY_CODES
#   - historic (List Three) entries ABSENT:
#       CURRENCY_CODES.isdisjoint({"ZWL", "SLL", "BGN", "ANG", "HRK", "VEF", "BYR", "MRO", "STD"})

# SYMBOL_TO_CODES (rules/data/cldr_currencies.py)
#   - dict[str, tuple[str, ...]]; every value tuple sorted; every code in CURRENCY_CODES
#   - spot checks (locked literals):
#       SYMBOL_TO_CODES["US$"] == ("USD",)
#       "€" in SYMBOL_TO_CODES and SYMBOL_TO_CODES["€"] == ("EUR",)
#       "$" maps to >= 25 codes (the dollar family) and "USD" in that tuple
#       "¥" maps to both "CNY" and "JPY"
#   - filters (D4/D5 boundary): no symbol equals a code (^[A-Z]{3}$), no symbol
#       contains whitespace, no symbol is empty

# NAME_TO_CODES (rules/data/cldr_currencies.py)
#   - dict[str, tuple[str, ...]]; EVERY key is lowercase (D4 — divergence from Money's Title-Case)
#       (assert all(k == k.lower() for k in NAME_TO_CODES))
#   - spot checks: NAME_TO_CODES["dollar"] == ("USD",), ["euro"] == ("EUR",),
#       ["ringgit"] == ("MYR",); every value code in CURRENCY_CODES

# SYMBOL_TOKENS (grammar/data/currency_symbols.py)
#   - tuple[str, ...]; equals the keys of SYMBOL_TO_CODES, ordering: qualified
#       (letter-bearing) tokens first, then bare; longest-first within each group
#       (mirror Money's D4 token-ordering tests)
#   - token ordering is stable: no token is a prefix of an earlier token
#       (longest-first guarantees longest-match)

# WORD_TOKENS (grammar/data/currency_words.py)
#   - tuple[str, ...]; equals the keys of NAME_TO_CODES; longest-first
```

Also in Step 1, `tests/capabilities/currency/test_data_consistency.py` (mirror `tests/capabilities/money/test_data_consistency.py` — the house mandate that every shipped recognition key is covered against rule-data mappings):

```python
# test_data_consistency.py (module-level pytestmark)
#   - set(SYMBOL_TOKENS) == set(SYMBOL_TO_CODES)          # grammar keys == rule keys
#   - set(WORD_TOKENS) == set(NAME_TO_CODES)
#   - every code in every SYMBOL_TO_CODES / NAME_TO_CODES value tuple is in CURRENCY_CODES
#   - no symbol token equals a code (^[A-Z]{3}$), contains whitespace, or is empty
#   - every NAME_TO_CODES key is lowercase (D4)
```

- [ ] **Step 2:** verify fail (no data modules).

- [ ] **Step 3: GREEN** — write a **temporary** derivation script `tools/derive_currency_tables.py` (mirror Money's temporary `tools/derive_currency_tables.py` — **NEVER committed**; delete after this task). It reads the same primary sources Money's derivation used — **SIX List One XML snapshot (published 2026-01-01)** and **Unicode CLDR v47 en + es** — and emits the four module bodies:

1. `rules/data/iso4217_list_one.py` — `CURRENCY_CODES: frozenset[str]` = **all 178** distinct alpha-3 codes from List One (no minor-unit exclusion — D2). Module docstring: source (`ISO 4217 Maintenance Agency (SIX), List One, published 2026-01-01, as amended by the amendment series through #180`), the full-set note, and the explicit Money divergence note.
2. `rules/data/cldr_currencies.py` — `SYMBOL_TO_CODES` (same derivation as Money's: symbols excluding code-equal, whitespace-containing, and `^[A-Z]{3}$` lookalikes) and `NAME_TO_CODES` with **lowercased** keys (D4). Every target code filtered to `CURRENCY_CODES`. Module docstring: source CLDR v47 en+es, lowercase-keys note, divergence note.
3. `grammar/data/currency_symbols.py` — `SYMBOL_TOKENS` = keys of `SYMBOL_TO_CODES` reordered **qualified-first, longest-first** (D4).
4. `grammar/data/currency_words.py` — `WORD_TOKENS` = keys of `NAME_TO_CODES` longest-first.

The script prints the four counts (codes / symbol tokens / word tokens) and the code count **must print 178**. Verify against the research facts: `ZWG` present, `ZWL`/`SLL`/`BGN` absent.

- [ ] **Step 4:** `uv run pytest tests/capabilities/currency -v` → pass (test_data + test_data_consistency). Then **delete `tools/derive_currency_tables.py`** (never committed) and confirm `git status` shows only the four data modules + `__init__.py` files. Commit `feat(currency): add ISO 4217 and CLDR data tables`.

### Task 4: `feat(currency): add validation rules (ISO 4217, CLDR symbols/names)`

- [ ] **Step 1: RED** — `tests/capabilities/currency/test_rules.py` (mirror `tests/capabilities/money/test_rules.py`: per-rule classes with `setup_method`, `@pytest.mark.parametrize` canonical-output groups, contract-error-free). Key matrices:

```python
# tests/capabilities/currency/test_rules.py
# class TestSectionCode:
#   canonical: ("USD", "code") -> "USD"; ("usd", "code") -> "USD"; ("GBP", "code") -> "GBP";
#              ("XAU", "code") -> "XAU"            # D2 full set
#   rejected:  ("ZZZ", "code"); ("the", "code"); ("USD", "word"); ("USD", "symbol")
#   provenance: SectionCode().provenance.publication_year == 2015
#               SectionCode().citation contains "ISO 4217:2015" and "Maintenance Agency"
#
# class TestSectionSymbols:
#   canonical (default contract): ("US$", "qualified_symbol") -> "USD"; ("€", "symbol") -> "EUR";
#                                 ("£", "symbol") -> "GBP"
#   rejected (default contract):  ("$", "symbol"); ("¥", "symbol"); ("US$", "word")
#   default_currency="USD":       ("$", "symbol") -> "USD"
#   default_currency="CNY":       ("¥", "symbol") -> "CNY"
#   default_currency="ZZZ":       ("$", "symbol") rejected   # D6: unknown opt-in never resolves
#   definitive symbol never remapped: default_currency="USD" + ("€", "symbol") -> "EUR"
#   qualified symbol never remapped:  default_currency="CNY" + ("US$", "qualified_symbol") -> "USD"
#   provenance: publication_year == 2025, version == "47", authority == "Unicode CLDR"
#
# class TestSectionNames:
#   canonical: ("euro", "word") -> "EUR"; ("dollar", "word") -> "USD";
#              ("ringgit", "word") -> "MYR"      # text arrives lowercase (grammar folded)
#   rejected:  ("pound", "word")  # not a CLDR display-name token; ("dollar", "symbol")
#   provenance: same CLDR publication as SectionSymbols
```

- [ ] **Step 2:** verify fail (no rules).

- [ ] **Step 3: GREEN** — two rule files (verbatim):

```python
# paxman/capabilities/Currency/rules/iso_4217_ed2015.py
"""ISO 4217 alpha-3 currency code rule.

The normative code data is the current List One of the ISO 4217
Maintenance Agency (SIX Financial Information AG), cited as ISO 4217:2015
as amended by the Maintenance Agency amendment series (see D-decision 1
of the implementation plan). ISO 4217:2015 itself defines the coding
method; the code list lives with the Maintenance Agency. The data module
snapshots SIX List One, published 2026-01-01.
"""

from __future__ import annotations

from typing import cast

from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.capabilities.Currency.rules.data.iso4217_list_one import CURRENCY_CODES
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


class SectionCode(Rule[CurrencyNotation]):
    """ISO 4217:2015 Section 3 — alpha-3 currency codes.

    Validates "code" shapes against the current List One as-amended (the
    full 178-code set, including the 13 codes with no minor units that
    the Money capability excludes). The grammar already folded the token
    to uppercase, so the lookup is exact.
    """

    name = "Section-code"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = (
        "ISO 4217:2015 alpha-3 currency codes, as amended by the ISO 4217 "
        "Maintenance Agency amendment series (SIX List One, 2026-01-01)"
    )
    target_grammars = frozenset({"code_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CurrencyNotation, contract: Contract) -> bool:
        """Check if the notation is a known ISO 4217 alpha-3 code.

        Args:
            notation: Currency notation to validate.
            contract: Contract configuration.

        Returns:
            True if the shape is "code" and the text is in CURRENCY_CODES.
        """
        if notation.shape != "code":
            return False
        return notation.text in CURRENCY_CODES

    def normalize(self, notation: CurrencyNotation, contract: Contract) -> str:
        """Normalize to the canonical uppercase alpha-3 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            The uppercase code (the grammar already folded the case).
        """
        return notation.text
```

```python
# paxman/capabilities/Currency/rules/cldr_currencies_ed2025.py
"""Unicode CLDR currency rules: currency symbols and display names.

Currency symbols and display names share the CLDR publication and lookup
tables. Both rules resolve a symbol/word token to an ISO 4217 code: a
token with exactly one candidate is definitive; a multi-candidate token
resolves via the opt-in ``contract.default_currency`` (None, the default,
-> matches() False -> INVALID, never silently dropped).
"""

from __future__ import annotations

from typing import cast

from paxman.capabilities.Currency.contract import CurrencyContract
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.capabilities.Currency.rules.data.cldr_currencies import (
    NAME_TO_CODES,
    SYMBOL_TO_CODES,
)
from paxman.capabilities.Currency.rules.data.iso4217_list_one import CURRENCY_CODES
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
    notation: CurrencyNotation,
    contract: CurrencyContract,
) -> str | None:
    """Resolve a symbol/qualified_symbol notation to an ISO 4217 code.

    A token with exactly one candidate resolves to it; a multi-candidate
    token (e.g. "$", "¥") resolves via the opt-in ``contract.default_currency``
    when that code is a known ISO 4217 code (guarded against
    CURRENCY_CODES so a shape-valid-but-unknown default can never produce
    a SUCCESS). Resolves to None otherwise, which makes matches() return
    False (INVALID).

    Args:
        notation: Currency notation to resolve.
        contract: Currency contract (default_currency).

    Returns:
        The resolved ISO 4217 code, or None when no code can be resolved.
    """
    codes = SYMBOL_TO_CODES.get(notation.text)
    if codes is None:
        return None
    if len(codes) == 1:
        return codes[0]
    candidate = contract.default_currency
    return candidate if candidate in CURRENCY_CODES else None


def _resolve_name_code(
    notation: CurrencyNotation,
    contract: CurrencyContract,
) -> str | None:
    """Resolve a word notation to an ISO 4217 code.

    The grammar folded the word to lowercase; the table keys are
    lowercase, so the lookup is exact. Same definitiveness policy as
    symbols (single candidate definitive; multi-candidate via the opt-in
    default_currency, gated against CURRENCY_CODES).

    Args:
        notation: Currency notation to resolve.
        contract: Currency contract (default_currency).

    Returns:
        The resolved ISO 4217 code, or None when no code can be resolved.
    """
    codes = NAME_TO_CODES.get(notation.text)
    if codes is None:
        return None
    if len(codes) == 1:
        return codes[0]
    candidate = contract.default_currency
    return candidate if candidate in CURRENCY_CODES else None


class SectionSymbols(Rule[CurrencyNotation]):
    """CLDR Section: currency symbols.

    Validates "symbol"/"qualified_symbol" shapes. A definitive token
    resolves to its single candidate; a multi-candidate token resolves
    via ``contract.default_currency`` when set to a known ISO 4217 code.
    """

    name = "Section-symbols"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v47 currency symbols"
    target_grammars = frozenset({"symbol_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CurrencyNotation, contract: Contract) -> bool:
        """Check if the notation is a resolvable currency symbol.

        Args:
            notation: Currency notation to validate.
            contract: Contract configuration.

        Returns:
            True if the shape is "symbol"/"qualified_symbol" and a code
            can be resolved.
        """
        if notation.shape not in ("symbol", "qualified_symbol"):
            return False
        typed_contract = cast(CurrencyContract, contract)
        return _resolve_symbol_code(notation, typed_contract) is not None

    def normalize(self, notation: CurrencyNotation, contract: Contract) -> str:
        """Normalize to the canonical alpha-3 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            The resolved uppercase code.
        """
        typed_contract = cast(CurrencyContract, contract)
        code = _resolve_symbol_code(notation, typed_contract)
        return code if code is not None else notation.text  # unreachable post-matches()


class SectionNames(Rule[CurrencyNotation]):
    """CLDR Section: currency display names.

    Validates "word" shapes. Same definitiveness policy as SectionSymbols.
    """

    name = "Section-names"
    strategy = RuleStrategy.LOOKUP_TABLE
    provenance = PUBLICATION
    citation = "CLDR v47 currency display names"
    target_grammars = frozenset({"word_recognition"})
    requires_features = frozenset()

    def matches(self, notation: CurrencyNotation, contract: Contract) -> bool:
        """Check if the notation is a resolvable display-name word.

        Args:
            notation: Currency notation to validate.
            contract: Contract configuration.

        Returns:
            True if the shape is "word" and a code can be resolved.
        """
        if notation.shape != "word":
            return False
        typed_contract = cast(CurrencyContract, contract)
        return _resolve_name_code(notation, typed_contract) is not None

    def normalize(self, notation: CurrencyNotation, contract: Contract) -> str:
        """Normalize to the canonical alpha-3 code.

        Args:
            notation: Validated notation.
            contract: Contract configuration.

        Returns:
            The resolved uppercase code.
        """
        typed_contract = cast(CurrencyContract, contract)
        code = _resolve_name_code(notation, typed_contract)
        return code if code is not None else notation.text  # unreachable post-matches()
```

- [ ] **Step 4:** `uv run pytest tests/capabilities/currency -v` → pass; ruff clean; `uv run pyright` clean. Commit `feat(currency): add validation rules (ISO 4217, CLDR symbols/names)`.

### Task 5: `feat(currency): add recognition grammars (code, symbol, word)`

- [ ] **Step 1: RED** — `tests/capabilities/currency/test_grammar.py` (mirror `tests/capabilities/money/test_grammar.py`: per-grammar classes with `setup_method`, parametrized spans). Key matrices:

```python
# class TestCodeRecognition:
#   recognized: ("USD", [("USD", 0, 3, "USD", "code")]);
#               (" usd ", [("usd", 1, 4, "USD", "code")])          # D3 case folding
#               ("GBP, EUR", [("GBP", 0, 3, "GBP", "code"), ("EUR", 5, 8, "EUR", "code")])
#   rejected:   ("US$", []); ("xUSD", []); ("USD-500", []); ("USD500", []);  # D5 whole-token + sign block
#               ("123", []); ("", [])
#
# class TestSymbolRecognition:
#   recognized: ("US$", [("US$", 0, 3, "US$", "qualified_symbol")]);
#               ("€", [("€", 0, 1, "€", "symbol")]);
#               ("A$ is the Australian dollar", [("A$", 0, 2, "A$", "qualified_symbol")])
#   rejected:   ("US$5", []); ("$500", []); ("x€", []); ("€5", [])   # D5 whole-token
#   # longest-first/qualified-first precedence: "CA$" matches before "$" in "CA$"
#
# class TestWordRecognition:
#   recognized: ("euro", [("euro", 0, 4, "euro", "word")]);
#               ("Euro", [("Euro", 0, 4, "euro", "word")]);          # D4 folding to lowercase
#               ("EURO", [("EURO", 0, 4, "euro", "word")]);
#               ("US Dollar", [("Dollar", 3, 9, "dollar", "word")])  # span on the word only
#   rejected:   ("Dollars", []); ("euro500", []); ("the", [])        # "the" is not a display-name token
#               ("", [])
```

- [ ] **Step 2:** verify fail.

- [ ] **Step 3: GREEN** — three grammar files (verbatim):

```python
# paxman/capabilities/Currency/grammar/code_recognition.py
"""ISO 4217 alpha-3 currency code recognition grammar.

Recognizes a standalone 3-letter ASCII code shape (case-insensitive) as
one span-bearing token. Case folding is the grammar's concern (Country
alpha-2/alpha-3 precedent): the token is emitted uppercase so the rule is
a pure table lookup. Syntax only: unknown codes are still matched —
deciding validity is the rules' job.
"""

from __future__ import annotations

import re
from typing import cast

from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.core.domain import Grammar, RecognitionMatch

# Sign characters ('-', U+2212, '+') are outside the identifier grammar; the
# boundary guards reject sign-adjacent tokens (mirrors Money's code grammar).
_CODE_PATTERN = re.compile(r"(?<![\w\-+\u2212])(?P<code>[A-Za-z]{3})(?![\w\-+\u2212])")


class CodeRecognition(Grammar[CurrencyNotation]):
    """Recognizes standalone ISO 4217 alpha-3 code shapes.

    Matches a 3-letter ASCII code in any casing: "USD", "usd", "Gbp".
    The grammar folds the token to uppercase at recognition; the rule
    validates against CURRENCY_CODES.

    Examples: "USD" -> text "USD", shape "code"
              "usd" -> text "USD", shape "code"
    Non-examples: "USD500"/"USD-500" (amount/sign-glued: blocked by the
        lookarounds), "xUSD" (inside a longer token).
    """

    name = "code_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[CurrencyNotation]]:
        """Extract standalone 3-letter code tokens from text.

        Args:
            text: Raw input text.

        Returns:
            List of span-bearing matches with shape "code" notations.
        """
        if not text.strip():
            return []
        matches: list[RecognitionMatch[CurrencyNotation]] = []
        for match in _CODE_PATTERN.finditer(text):
            matches.append(
                RecognitionMatch(
                    notation=CurrencyNotation(
                        text=match.group("code").upper(),
                        shape="code",
                    ),
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(0),
                )
            )
        return matches
```

```python
# paxman/capabilities/Currency/grammar/symbol_recognition.py
"""CLDR currency symbol recognition grammar.

Recognizes a standalone currency symbol token (qualified or bare) as one
span-bearing token. The alternation is built from SYMBOL_TOKENS
(qualified-first, longest-first — D4). Syntax only: resolving the symbol
to a code is the rules' job.
"""

from __future__ import annotations

import re
from typing import cast

from paxman.capabilities.Currency.grammar.data.currency_symbols import SYMBOL_TOKENS
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.core.domain import Grammar, RecognitionMatch

_SYMBOL_ALTERNATION = "|".join(re.escape(token) for token in SYMBOL_TOKENS)
# Lookarounds, not \b: pure-symbol tokens ("$", "€") are non-word
# characters that \b would reject at string start, and the lookarounds
# still block matches inside a longer token. The sign block mirrors the
# Money symbol grammar.
_SYMBOL_PATTERN = re.compile(
    rf"(?<![\w\-+\u2212])(?:{_SYMBOL_ALTERNATION})(?![\w\-+\u2212])"
)


def _is_qualified(token: str) -> bool:
    """Whether a symbol token carries an ASCII letter (e.g. "US$")."""
    return any(char.isascii() and char.isalpha() for char in token)


class SymbolRecognition(Grammar[CurrencyNotation]):
    """Recognizes standalone CLDR currency symbol tokens.

    A token is "qualified" when it embeds an ASCII letter ("US$", "A$",
    "R$") and "bare" otherwise ("$", "€", "¥"). Symbols are case-exact —
    no case folding (symbols are arbitrary glyph strings).

    Examples: "US$" -> text "US$", shape "qualified_symbol"
              "€"    -> text "€",    shape "symbol"
    Non-examples: "US$5"/"$500" (amount-glued: the trailing digit is a
        word character, blocked by the lookaround), "x€" (inside a
        longer token).
    """

    name = "symbol_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[CurrencyNotation]]:
        """Extract standalone symbol tokens from text.

        Args:
            text: Raw input text.

        Returns:
            List of span-bearing matches with shape "symbol" or
            "qualified_symbol" notations.
        """
        if not text.strip():
            return []
        matches: list[RecognitionMatch[CurrencyNotation]] = []
        for match in _SYMBOL_PATTERN.finditer(text):
            token = match.group(0)
            matches.append(
                RecognitionMatch(
                    notation=CurrencyNotation(
                        text=token,
                        shape="qualified_symbol" if _is_qualified(token) else "symbol",
                    ),
                    start=match.start(),
                    end=match.end(),
                    raw_text=token,
                )
            )
        return matches
```

```python
# paxman/capabilities/Currency/grammar/word_recognition.py
"""CLDR currency display-name word recognition grammar.

Recognizes a standalone currency display-name word (case-insensitive) as
one span-bearing token. The alternation is built from WORD_TOKENS
(longest-first). Case folding is the grammar's concern (Country/ISBN
precedent): the token is emitted lowercase so the rule is a pure
lowercase-key table lookup. Syntax only.
"""

from __future__ import annotations

import re
from typing import cast

from paxman.capabilities.Currency.grammar.data.currency_words import WORD_TOKENS
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.core.domain import Grammar, RecognitionMatch

_WORD_ALTERNATION = "|".join(re.escape(token) for token in WORD_TOKENS)
_WORD_PATTERN = re.compile(
    rf"(?<![\w\-+\u2212])(?:{_WORD_ALTERNATION})(?![\w\-+\u2212])",
    re.IGNORECASE,
)


class WordRecognition(Grammar[CurrencyNotation]):
    """Recognizes standalone CLDR currency display-name word tokens.

    Matching is case-insensitive; the emitted text is the token folded to
    lowercase so the rule's NAME_TO_CODES lookup is an exact lowercase-key
    hit. "Euro"/"euro"/"EURO" all emit text "euro". Word boundaries keep
    the match inside one token: "Dollars" does not match "Dollar".

    Examples: "Euro" -> text "euro", shape "word"
              "US Dollar" -> the "Dollar" span matches (text "dollar");
                  "US" (2 letters) matches nothing.
    Non-examples: "Dollars" (plural, blocked by the lookahead), "euro500"
        (amount-glued, blocked), "the" (not a display-name token).
    """

    name = "word_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[CurrencyNotation]]:
        """Extract standalone display-name word tokens from text.

        Args:
            text: Raw input text.

        Returns:
            List of span-bearing matches with shape "word" notations.
        """
        if not text.strip():
            return []
        matches: list[RecognitionMatch[CurrencyNotation]] = []
        for match in _WORD_PATTERN.finditer(text):
            matches.append(
                RecognitionMatch(
                    notation=CurrencyNotation(
                        text=match.group(0).lower(),
                        shape="word",
                    ),
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(0),
                )
            )
        return matches
```

- [ ] **Step 4:** `uv run pytest tests/capabilities/currency -v` → pass; ruff + pyright clean. Commit `feat(currency): add recognition grammars (code, symbol, word)`.

### Task 6: `feat(currency): wire CurrencyCapability with create_contract`

- [ ] **Step 1: RED** — `tests/capabilities/currency/test_capability.py` (mirror `tests/capabilities/money/test_capability.py`): class-level `@pytest.mark.capability`/`@pytest.mark.currency` markers; imports from `paxman.capabilities.Currency.capability` / `.contract` / `.notation`. Assert:

```python
# name == "currency"; version == "1.0.0"
# get_grammars() returns 3 instances with names
#     {"code_recognition", "symbol_recognition", "word_recognition"}
# get_rules() returns 3 instances with names {"Section-code", "Section-symbols", "Section-names"}
# create_contract() returns CurrencyContract with defaults (default_currency is None)
# create_contract(default_currency="USD").default_currency == "USD"
# create_contract(excluded_rules=["Section-code"]).excluded_rules == ("Section-code",)
# format_value identity: capability.format_value("USD", "code", notation) == "USD"
#     (offered formats are empty -> base identity is the contract)
# ContractFactory conformance: create_contract accepts the common keyword-only block
# __all__ exports CurrencyCapability, CurrencyContract, CurrencyNotation
```

- [ ] **Step 2:** verify fail.

- [ ] **Step 3: GREEN** — `capability.py` (verbatim):

```python
# paxman/capabilities/Currency/capability.py
"""Currency capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Currency.contract import CurrencyContract
from paxman.capabilities.Currency.grammar.code_recognition import CodeRecognition
from paxman.capabilities.Currency.grammar.symbol_recognition import SymbolRecognition
from paxman.capabilities.Currency.grammar.word_recognition import WordRecognition
from paxman.capabilities.Currency.notation import CurrencyNotation
from paxman.capabilities.Currency.rules.cldr_currencies_ed2025 import (
    SectionNames,
    SectionSymbols,
)
from paxman.capabilities.Currency.rules.iso_4217_ed2015 import SectionCode
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["CurrencyCapability", "CurrencyContract", "CurrencyNotation"]


class CurrencyCapability(Capability[CurrencyNotation]):
    """Currency canonicalization capability.

    Canonicalizes currency identifiers — an ISO 4217 alpha-3 code, a CLDR
    currency symbol, or a CLDR display-name word — to the uppercase
    alpha-3 code, with full provenance. Identifier-only: amounts are the
    Money capability's domain ("USD 500" resolves via its "USD" span;
    amount-glued tokens like "US$5" are not matched at all).
    """

    name = "currency"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[CurrencyNotation]]:
        """Return all grammar instances.

        Returns:
            List of 3 grammars: code, symbol, word.
        """
        return [CodeRecognition(), SymbolRecognition(), WordRecognition()]

    def get_rules(self) -> list[Rule[CurrencyNotation]]:
        """Return all validation rule instances.

        Returns:
            List of 3 rules: ISO 4217 codes, CLDR symbols, CLDR names.
        """
        return [SectionCode(), SectionSymbols(), SectionNames()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        default_currency: str | None = None,
    ) -> CurrencyContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"code" resolve to "code".
            default_currency: ISO 4217 alpha-3 code (opt-in) used to
                resolve shared bare symbols (e.g. "$", "¥"). None (the
                default) makes a shared symbol INVALID (recognized, but
                no authority resolves it). Never remaps a definitive
                symbol (e.g. "€" -> EUR) or a qualified symbol ("US$").

        Returns:
            Configured CurrencyContract instance.
        """
        return CurrencyContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            default_currency=default_currency,
        )

    # format_value: NOT overridden — the canonical value IS the "code"
    # format (uppercase alpha-3), and there are no offered alternatives.
    # The Capability base provides the identity formatter.
```

- [ ] **Step 4:** `uv run pytest tests/capabilities/currency -v` → pass; ruff + pyright clean; `uv run import-linter lint` → clean (no cross-package imports so far). Commit `feat(currency): wire CurrencyCapability with create_contract`.

### Task 7: `feat(currency): register Currency capability and extend export/surface guards`

- [ ] **Step 1: RED** — extend the existing guards first (each fails before the registration lands):

- `tests/unit/test_capability_exports.py`: add a `TestCurrencyCapabilityExports` class (mirror `TestMoneyCapabilityExports` — asserts `capabilities.Currency` imports and `name == "currency"`), and extend the count test to **nine** names: `{"Country", "Currency", "Date", "Email", "IP", "ISBN", "Money", "Phone", "URL"}`.
- `tests/unit/test_capability_surface.py`: add the Currency rows (capability name/version; notation class; contract `capability_name`/`output_format`/`default_currency`; grammar count/names; rule count/names; format_value surface row with an independent literal — canonical value `"USD"`).
- `pyproject.toml`: add `"currency: currency capability tests"` to the markers list (alphabetical, next to `country`).

- [ ] **Step 2:** `uv run pytest tests/unit -v` → the guards fail (no `Currency` export yet).

- [ ] **Step 3: GREEN** — `paxman/capabilities/__init__.py`:

```python
"""Paxman capabilities."""

from paxman.capabilities.Country.capability import CountryCapability as Country
from paxman.capabilities.Currency.capability import CurrencyCapability as Currency
from paxman.capabilities.Date.capability import DateCapability as Date
# ... (rest unchanged)

__all__ = [
    "Country",
    "Currency",
    "Date",
    "Email",
    "IP",
    "ISBN",
    "Money",
    "Phone",
    "URL",
]
```

- [ ] **Step 4:** `uv run ruff check paxman/ tests/` → clean; `uv run pytest tests/unit -v` → pass (guards green with registration); `uv run import-linter lint` → clean. Commit `feat(currency): register Currency capability and extend export/surface guards`.

### Task 8: `test(currency): lock Currency pipeline semantics`

- [ ] **Step 1: RED** — `tests/integration/test_currency_pipeline.py` mirroring `tests/integration/test_money_pipeline.py`: autouse `_clean_registry` fixture calling `reset_registry()` before/after each test (registry hygiene per `paxman/core/AGENTS.md`); class docstring locks the semantics; `register_capability(CurrencyCapability())` per test; `from paxman.api import canonicalize`. Run **every row of the §1 e2e contract** as a parametrized case, plus:

```python
# status per row; canonicalized_value per SUCCESS row; Resolution.MISSING for
# MISSING rows; no candidates for MISSING rows
# provenance: "USD" SUCCESS row -> candidates[0].provenance[0].specification_name
#     == "ISO 4217" and authority == "ISO"; "€" row -> "Unicode CLDR";
#     "euro" row -> "Unicode CLDR"
# frozen registry: a second canonicalize() call after the first still succeeds
#     (registry freezes once, never re-registers)
```

- [ ] **Step 2:** verify fail (Currency not yet importable through the pipeline).

- [ ] **Step 3: GREEN** — no new source needed (Tasks 3–7 already wired everything); this task proves the full `canonicalize()` path (registry → run_capability → grammar → rule → Resolution → hash) and catches integration regressions early (Traps §T15: the moment Currency joins the registry, every existing replay-hash test must still pass).

- [ ] **Step 4:** `uv run pytest tests/integration -v` → pass (all capabilities). Commit `test(currency): lock Currency pipeline semantics`.

### Task 9: `test(currency): baseline replay hash for the Currency capability`

- [ ] **Step 1: RED** — extend `tests/integration/test_default_replay_hashes.py` mirroring the existing per-capability cases exactly (per-case `register_capability(CurrencyCapability())` + `canonicalize(input, year=2026)`), adding **one** Currency case:

```python
# canonicalize("US$", CurrencyCapability.create_contract(), year=2026)
# baseline hash literal: obtain by running once (see Step 2) — never edited to green.
```

- [ ] **Step 2: GREEN** — run `uv run pytest tests/integration/test_default_replay_hashes.py -v` once to obtain the baseline hash; write that literal into the test; re-run → pass (now 9 capability cases). **Do NOT fabricate or back-solve the literal** — the hash is the replay-safety contract.

- [ ] **Step 3: Verify + commit** — `uv run pytest tests/integration/test_default_replay_hashes.py -v` → pass. Commit `test(currency): baseline replay hash for the Currency capability`.

### Task 10: `test(currency): add property invariants and e2e coverage`

- [ ] **Step 1: RED** — `tests/property/test_currency_properties.py` (`@pytest.mark.property` + `@given`; property tests drive grammars directly and never touch the registry — the Money full-pipeline suite is the documented exception):

```python
# given a standalone 3-letter ASCII token t (any casing):
#   CodeRecognition().recognize(t) yields exactly one match whose notation
#   text == t.upper() and shape == "code"     # D3 folding invariant
# given a known code c in CURRENCY_CODES (sample strategy):
#   CodeRecognition().recognize(c).notation.text == c and
#   SectionCode().matches(notation, CurrencyContract()) is True
# given a lowercase word w in NAME_TO_CODES:
#   WordRecognition().recognize(w.title()).notation.text == w     # D4 folding invariant
# given any recognized match m: m.end - m.start == len(m.raw_text)
#     and m.raw_text == text[m.start:m.end]                       # half-open span invariant
```

- [ ] **Step 2: GREEN** — extend `tests/e2e/test_canonicalize.py` (autouse `_clean_registry` fixture; `from paxman.api import canonicalize`), adding the Currency e2e rows from the §1 contract (the Milestone trio `"US$"`, `"euro"`, `"GBP"` first).

- [ ] **Step 3: Verify + commit** — `uv run pytest tests/property tests/e2e -v` → pass. Commit `test(currency): add property invariants and e2e coverage`.

### Task 11: `docs(currency): document Currency capability and update capability counts`

- [ ] **Step 1: RED (docs-as-spec)** — grep the repo for stale references: `rg -n "eight|8 capabilities|eight built-in" README.md AGENTS.md docs/` → list every hit to update (no code test needed — the Task 7 surface guards already enforce the 9-capability surface; this task is the documentation mirror).

- [ ] **Step 2: GREEN** — update:

- `README.md`: capabilities table — add the **Currency** row (`| **Currency** | Currency identifiers | 3 (code, symbol, word) | 3 | ISO 4217, CLDR |`) and the count line ("eight built-in" → "nine built-in"); add a **Currency Capability** section after the Country section with the Milestone trio + `default_currency` example (mirror the Money section's style); add `default_currency` to the Capability-Specific Parameters table (row: `Currency | default_currency | str \| None | ISO 4217 alpha-3 code resolving shared bare symbols (e.g. "$"); None (default) makes them INVALID`).
- `AGENTS.md` (root): "8 capabilities" → "9 capabilities" in the Overview; capability-count mentions anywhere else found by the grep.
- `paxman/capabilities/AGENTS.md`: "8 capability packages" → "9 capability packages"; add Currency to the package list.
- `paxman/capabilities/__init__.py` docstring comment if it mentions the count (Task 7 may have handled it).
- `docs/development/MILESTONE.md`: if the row-1 status column has a convention, mark Currency per the URL row's treatment; otherwise leave the roadmap untouched (roadmap status is a product-owner call, out of scope).

- [ ] **Step 3: Final pre-PR gate (authoritative, `.github/workflows/ci.yml`)** — run the full merge-blocking suite and confirm green:

```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
uv run pyright
uv run import-linter lint
uv run pytest
uv run coverage report --include="paxman/{core,capabilities,engine,api}/*" --fail-under=95
```

Coverage: `paxman/capabilities/Currency/` must be ≥95% (per-package gate). If a line is structurally unreachable (e.g. the defensive `normalize()` fallbacks), the sanctioned pattern is a scoped `per-file-ignores` entry in `pyproject.toml` — never `# noqa` / `# pragma` / `# type: ignore` in source.

- [ ] **Step 4: Verify + commit** — all gates green. Commit `docs(currency): document Currency capability and update capability counts`.

---

## 3. Sequencing and Parallelism

- **Strictly sequential, one executor, one worktree**: Tasks 1 → 2 → 3 → 4 → 5 → 6 (each feeds the next; TDD red/green per task; Task 3's derivation script is the only place an external data source can bite — do **not** parallelize it).
- Tasks 7 → 10 depend on Task 6 (registration must land before the pipeline/replay/e2e tasks can run).
- Task 11 is last (docs reflect the registered surface).
- Each task commits atomically with the message in its header; never merge tasks' commits.
- The `currency` pytest marker is registered in Task 7; Tasks 1–6 use it too (pyproject accepts unknown markers only as warnings — registering it early in Task 1 is acceptable if preferred, but Task 7 is the sanctioned point).

## 4. Traps (call out explicitly in the plan doc)

- **T1. No cross-capability imports.** Currency must vendor its own data tables (import-linter enforces the boundary). Never `from paxman.capabilities.Money...`. The derivation script re-derives from the same primary sources.
- **T2. Don't fabricate "ISO 4217 Amendment 17".** The research (D-decision 1) is authoritative: no such document exists for the 2015 edition; the literal Amendment No. 17 amended ISO 4217:1981 (Brazil, 1986). Cite `ISO 4217:2015` + the SIX List One 2026-01-01 snapshot. The milestone string is **not** copied into any provenance constant, docstring, or test literal.
- **T3. One file = one publication.** `iso_4217_ed2015.py` (year 2015) and `cldr_currencies_ed2025.py` (CLDR v47, year 2025). Do not split the codes rule by amendment; do not merge the CLDR rules into the ISO file.
- **T4. Rules never read `output_format`; `format_value` is the only presentation seam.** Currency has no offered formats → base identity `format_value`, do not override, do not mention `output_format` in rule code (CI source-scan).
- **T5. Grammar/rule boundary is absolute.** Grammars are shape-only + case-fold; validity against `CURRENCY_CODES` lives in rules; `grammar/data/` holds key-only token tables; authority mappings live in `rules/data/` and are imported only by rules. `tests/capabilities/currency/test_data_consistency.py` must cover every shipped recognition key against the rule-data mappings (house mandate).
- **T6. Code grammar: case-insensitive + fold, NOT Money's uppercase-only.** `"usd" → "USD"` is a Milestone requirement. Mirror `Country/grammar/alpha3_recognition.py` (`\b[A-Za-z]{3}\b`-style shape with `.upper()` emission) but keep Money's **sign-blocking lookarounds** (`(?<![\w\-+\u2212])` / `(?![\w\-+\u2212])`).
- **T7. Word grammar folds to lowercase; `NAME_TO_CODES` keys lowercase.** Copying Money's Title-Case keys + as-written lookup would make the Milestone's `"euro" → "EUR"` fail. This is D-decision 4.
- **T8. Standalone tokens only — never copy Money's amount-coupled patterns.** No `AMOUNT_PATTERN` anywhere. `"US$5"` / `"$500"` / `"USD500"` → MISSING (whole-token discipline), not partial matches.
- **T9. Shared bare symbols never silently resolve.** `"$"`, `"¥"`, `"₩"` are multi-candidate → INVALID without `default_currency`; the opt-in is gated against `CURRENCY_CODES`; definitive and qualified symbols are never remapped.
- **T10. Full 178-code set (D2).** Including the 13 N.A.-minor-unit codes Money excludes. Do not "align" Currency's set down to Money's 165 — the divergence is deliberate and documented. Reconcile the two snapshots' shared codes at derivation time only if they disagree (they should not: same 2026-01-01 List One source).
- **T11. Replay-hash literals: obtain by running once; never edit to green** (root AGENTS.md anti-pattern).
- **T12. Type safety / style.** No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source (tests may use `# type: ignore[misc]` for immutability checks). Rule classes CapWords. Contracts frozen **without** slots; notation frozen **with** slots. `_extra_dict_fields()` override, never hand-written `as_dict()`.
- **T13. Prose false positives are accepted, not "fixed".** 3-letter prose words (`"the"`, `"and"`) → INVALID (shape matched, rule rejected). Country's alpha-2 grammar has the same property. Do NOT add a wordlist filter to the grammar — that would violate the grammar/rule boundary.
- **T14. Registration surface.** `__init__.py` import + `__all__` together (acronym aliases are already per-file-ignored for N814); export guard count test 8 → 9; marker added in pyproject.
- **T15. Registry freezing.** The moment Currency joins the registry (Task 7), every existing integration/replay-hash test runs against 9 capabilities — all baselines must stay green. Do not touch other capabilities' replay-hash literals.

## 5. Definition of Done

- [ ] All 11 tasks checked, each with its atomic commit (`feat(currency):` / `test(currency):` / `docs(currency):`).
- [ ] `tests/capabilities/currency/` green: test_data, test_data_consistency, test_notation, test_contract, test_grammar, test_rules, test_capability (7 files — **no** test_parsing: Currency has no amounts).
- [ ] `tests/integration/test_currency_pipeline.py` green with the full §1 e2e contract.
- [ ] Replay-hash baseline for `"US$"` (year=2026) locked; `test_default_replay_hashes.py` green for all 9 capabilities.
- [ ] Property + e2e coverage green (Tasks 10).
- [ ] Docs: README (9 capabilities, Currency section + param row), root AGENTS.md, capabilities AGENTS.md.
- [ ] Full pre-PR gate green (Task 11 Step 3), including ≥95% coverage on `paxman/capabilities/Currency/`.
