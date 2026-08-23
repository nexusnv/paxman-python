# 2026-08-21 — ISSN Capability Implementation Plan

> **For agentic workers: REQUIRED SUB-SKILL: `superpowers:writing-plans` workflow.** This is an implementation plan, not a design doc. Execute it task-by-task with `superpowers:executing-plans` or `superpowers:subagent-driven-development`, TDD-first (Red-Green-Refactor), with a commit after every task. Assume the engineer executing this plan has zero codebase context; every file change below is self-contained.

**Design authority:** `docs/development/research/2026-08-21-issn-canonicalization.md` (rev. 2026-08-22 Oracle alignment) — read it first if any section here seems ambiguous. It contains the full primary-source survey (ISO 3297:2022, RFC 3044, ISSN Manual 2025, IANA `urn:issn`, ecosystem validators, ISSN-L/H) that grounds every decision below. **2026-08-22 revision:** §4.2/§4.4 corrected from `isbn10_lead` to shipped `word_only().lookbehind + digit().lookahead + r"\b"` per Oracle P2 (`paxman/capabilities/ISSN/grammar/issn_recognition.py:11-16`).

**2026-08-22 revision (plan-vs-memo Oracle audit fixes):** Behavioral Contract aligned with shipped behavior — mid-`X` inputs (`X234-5679`/`12X4-5679`) resolve `MISSING` end-to-end (the grammar's `\d{4}` guard filters them; rule-level `matches()` rejection is unreachable), the glued label `ISSN03178471` **matches** (`[\s:-]*` permits zero separators — documented, not rejected), exotic Unicode dashes are `MISSING` (hyphen-minus only, memo §13#7). Task 4 GREEN code now matches shipped `rules/iso_3297_ed2022.py:38` (`.isascii()` guard). README/CONTEXT tables updated with the ISSN row; checkboxes reflect the executed state.

**Repo state:** branch `feature/CURRENCY-capability` @ `7a4017c` → `2026-08-22` shipped ISSN verified — engine owns per-grammar containment dedup and total order `(start, end, active_grammars index, grammar name)`, `Capability.format_value()` is the sole presentation seam, `CapabilityContract` resolves `output_format` via `resolve_output_format`. Ten shipped capabilities (Country, Currency, Date, Email, IP, ISBN, Money, Phone, SI Unit, URL) plus ISSN (greenfield → now shipped; this plan is the implementation record).

## Goal

Implement the **ISSN capability** that canonicalizes International Standard Serial Numbers per **ISO 3297:2022** to the **hyphenated canonical form** `XXXX-XXXX` (e.g., `0317-8471`) with full provenance:

1. **Recognize** ISSN shapes (bare `12345679`, hyphenated `1234-5679`, with optional `ISSN`/`ISSN-L`/`ISSN-H` label, case-insensitive, `x`→`X` folded) as span-bearing `RecognitionMatch[ISSNNotation]` objects. URN form (`urn:issn:1234-5679`) is deferred to a future community grammar (optional fuse — not required for v1).
2. **Validate** against one authoritative publication:
   - **ISO 3297:2022** — structure (8 chars, 7 digits + check char) + **mod-11 weights 8→2** check digit (`Section 4-issn-check-digit`, `PARSER`), `X`=10.
   - Optional `RFC 3044` / `ISSN Register` rules are explicitly out-of-scope for v1 (see §13#3 of memo) — deferred behind `include_register_validation` + `rules/data/` snapshot when needed.
3. **Resolve** to one canonical `XXXX-XXXX` hyphenated string — tolerant input hyphens/spaces re-canonicalized; `X` always uppercased. No `AMBIGUOUS` within single ISSN (unique by design); two distinct ISSNs in one slice → `AMBIGUOUS` via segmentation recipe.
4. **Present** alternative forms only through `Capability.format_value()` when `output_format="compact"` (`XXXXXXXX`) or `"urn"` (`urn:issn:XXXX-XXXX`); rules never read `output_format` (CI `tests/unit/test_rule_output_format_purity.py` enforced).

**Correctness gate:** existing capability pipeline unchanged; ISSN canonicalizes deterministically (no network, no clock).

## Architecture

```text
ISSNNotation(digits: str)          # 8-char, hyphen-stripped, x→X
         ▲
         │ grammar
issn_recognition (PipelineGrammar)  # RegexStage, strict -? at position 4
                                    # optional ISSN(?:-L|-H)? label, re.IGNORECASE
                                    # BoundaryGuard.word_only().lookbehind + BoundaryGuard.digit().lookahead + r"\b" (shipped)
         └──────────────┬────────────┘
                        ▼
         span-bearing RecognitionMatch[ISSNNotation]
                        ▼
         engine: StandardPre empty_guard, per-grammar containment dedup,
                 total order, _filter_rules (pinned → excluded → year → requires_features)
                 → affinity routing via target_semantics
                        ▼
         rules/iso_3297_ed2022.py    # Section 4-issn-check-digit (PARSER)
                                     # structure + mod-11 8→2, X=10
                        ▼
         normalize() → hyphenated XXXX-XXXX (default canonical)
                        ▼
         ISSNCapability.format_value(value, "compact" → remove hyphen,
                                            "urn" → urn:issn:XXXX-XXXX)
```

**Responsibility split (the invariant):**

| Concern | Owner |
|---|---|
| Extraction + syntax normalization (strip hyphen at pos 4, fold `x`→`X`, strip `ISSN` label) | Grammar (`notation_fn`) |
| Span bearing `[start,end)` + `raw_text == text[start:end]` | Grammar (`RecognitionMatch`) |
| Length 8, charset, mod-11 8→2, `X`=10 | Rules (provenance-backed, `PARSER`) |
| Hyphenation / URN wrapping (presentation) | `Capability.format_value()` only |
| Ordering, dedup, status, `VersionStamp` | Engine (untouched) |
| ISSN-L/H linking, Register issued-ness | Deferred — future `LOOKUP_TABLE` + `requires_features` |

**Design decisions from memo §7 / Oracle audit applied (2026-08-22):**

- Grammar ships as **module-scope string** `_ISSN_PATTERN: str` (not `re.compile().pattern`); `RegexStage` compiles in `paxman/core/grammar/stages.py:72` — matches `paxman/capabilities/ISBN/grammar/isbn13_recognition.py:17`.
- Leading guard `BoundaryGuard.word_only().lookbehind` (`(?<!\w)`) + trailing `BoundaryGuard.digit().lookahead` (`(?!\d)`) + `r"\b"` — blocks `a1234-5679` and `912345679` glue leaks; strictly stronger than `isbn10_lead` (`(?<!\d)(?<!\d[ -])`) per shipped `paxman/capabilities/ISSN/grammar/issn_recognition.py:11-16` (Oracle P2 fix; report revised 2026-08-22).
- Hyphen strict at canonical position (`-?`) — tolerant `1234 - 5679` / `1234 5679` are `MISSING` unless a `Pre` normalizer added (Oracle fix 3 alignment). `normalize()`/`format_value()` enforces `XXXX-XXXX`.
- `S = Σ(digit_i × (8-i))` for `i=0..6` (Oracle fix 1 — was `9-i` typo).
- `DEFAULT_OUTPUT_FORMAT="hyphenated"` (ISSN Manual §4 machine exchange hyphen), `OFFERED={"compact","urn"}`.

## Tech Stack

- Python 3.11, standard library only — no new runtime dependencies.
- `re` for grammars (module-scope string patterns, `re.IGNORECASE` for label/`x`); `PipelineGrammar` + `StandardPre(empty_guard=True)` + `RegexStage`.
- Frozen dataclasses: `@dataclass(frozen=True, slots=True)` notation, `@dataclass(frozen=True)` contract (extends `CapabilityContract`, no `slots`).
- Gates (unchanged): `uv run ruff check` + `ruff format --check`, `uv run pyright` (strict), `uv run import-linter lint`, `uv run pytest` (markers `unit`/`capability`/`integration`/`property`), coverage `branch=true` `fail_under=95`.

## Behavioral Contract

| Input | Contract | Status / canonical |
|---|---|---|
| `0317-8471` | default (`hyphenated`) | `SUCCESS` → `0317-8471` |
| `03178471` | default | `SUCCESS` → `0317-8471` (bare → hyphenated) |
| `ISSN 0317-8471` / `ISSN: 0317-8471` / `ISSN-L 0317-8471` | default | `SUCCESS` → `0317-8471`, span includes label |
| `0317-847x` | default | `INVALID` (`x`→`X` folded; check for `0317-847X` fails); `1050-124x` → `SUCCESS` → `1050-124X` |
| `1050-124X` / `1050-124x` | default | `SUCCESS` → `1050-124X` (`X`=10) |
| `0000-0019` | default | `SUCCESS` → `0000-0019` (leading zeros preserved) |
| `0378-5955` (Hearing Research) | default | `SUCCESS` → `0378-5955` |
| `0378-5954` (bad mod-11) | default | `INVALID` (recognized, check fails) |
| `1234-567` (7 chars) / `123456789` (9) | default | `MISSING` (grammar length guard) |
| `X234-5679` / `12X4-5679` | default | `MISSING` (grammar `\d{4}` guard filters mid-X; rule-level `matches()` also rejects, but is unreachable end-to-end) |
| `12-345679` / `1234 - 5679` | default | `MISSING` (strict hyphen — Oracle fix 3) |
| `1234–5679` / `1234—5679` (en/em dash) | default | `MISSING` (hyphen-minus only; exotic dashes documented-unsupported per memo §13#7) |
| `call me at noon` | default | `MISSING` |
| `0264-2875 / 1750-0095` (two distinct) | default | `AMBIGUOUS` / `MultipleMentionsError` (`single_value=True`) |
| `0317-8471` | `output_format="compact"` | `SUCCESS` → `03178471` |
| `0317-8471` | `output_format="urn"` | `SUCCESS` → `urn:issn:0317-8471` |
| any | `pinned_rules=["Section 4-issn-check-digit"]` etc. | Pin respected; `excluded_rules`, `year` filtering via engine |

Key rules:

- Hyphen has **no lexical significance for identity** but is **strict at canonical position** in grammar; differently-hyphenated same ISSN that passes grammar still canonicalizes identically (presentation-only).
- Unicode dashes (U+2013 en, U+2014 em, U+2212 minus) are **not recognized** — hyphen-minus (U+002D) only in the `-?` slot; exotic dashes yield `MISSING` and are documented-unsupported (memo §13#7). No `Pre` normalizer in v1.
- `normalize()` returns hyphenated `XXXX-XXXX`; `format_value("compact")` strips hyphen, `"urn"` wraps `urn:issn:` — never affects candidate identity or provenance.
- Contract params: **no** `include_*` flags for v1 (single always-active grammar); `output_format` always optional via `CapabilityContract.__post_init__` (`None`/`"default"`/default string → default, `ContractError` otherwise).
- `single_value=True` — free-text multi-ISSN mining uses caller-owned segmentation (`docs/recipes/segmentation.md`), not a second grammar.

---

## File Structure

```text
paxman/capabilities/ISSN/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── issn_recognition.py
└── rules/
    ├── __init__.py
    └── iso_3297_ed2022.py

tests/capabilities/issn/
├── __init__.py
├── test_notation.py
├── test_contract.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py

tests/property/test_issn_properties.py
```

Deferred for future Register validation (not in this plan):
```text
paxman/capabilities/ISSN/rules/data/   # ISSN Register snapshot (LOOKUP_TABLE)
tools/regenerate_issn_data.py
```

## Files And Responsibilities

| File | Action | Responsibility |
|---|---|---|
| `paxman/capabilities/ISSN/__init__.py` | create (scaffolder) | re-export `ISSNCapability`, `ISSNContract`, `ISSNNotation` |
| `paxman/capabilities/ISSN/notation.py` | create | `ISSNNotation` frozen `slots` dataclass (Task 1) |
| `paxman/capabilities/ISSN/contract.py` | create | `ISSNContract` (`hyphenated` default, `compact`/`urn` offered) (Task 2) |
| `paxman/capabilities/ISSN/capability.py` | create | `ISSNCapability`: wiring + `format_value()` (Task 5) |
| `paxman/capabilities/ISSN/grammar/__init__.py` | create | grammar package |
| `paxman/capabilities/ISSN/grammar/issn_recognition.py` | create | ISSN grammar — `PipelineGrammar` + `RegexStage` (Task 3) |
| `paxman/capabilities/ISSN/rules/__init__.py` | create | rules package |
| `paxman/capabilities/ISSN/rules/iso_3297_ed2022.py` | create | `Section 4-issn-check-digit` rule (`PARSER`) (Task 4) |
| `paxman/capabilities/__init__.py` | modify | ISSN alias import alphabetically + `__all__` (Task 6) |
| `pyproject.toml` | modify | add `"issn: issn capability tests"` marker (Task 6) |
| `tests/capabilities/issn/__init__.py` | create | test package |
| `tests/capabilities/issn/test_notation.py` | create | notation unit tests (Task 1) |
| `tests/capabilities/issn/test_contract.py` | create | contract unit tests (Task 2) |
| `tests/capabilities/issn/test_grammar.py` | create | grammar tests (Task 3) |
| `tests/capabilities/issn/test_rules.py` | create | rule tests (Task 4) |
| `tests/capabilities/issn/test_capability.py` | create | capability wiring + format_value tests (Task 5) |
| `tests/integration/test_issn_capability.py` | create | resolution map + feature gating integration (Task 7) |
| `tests/property/test_issn_properties.py` | create | hypothesis property suite (Task 8) |
| `tests/unit/test_capability_exports.py` | modify | ISSN exports coverage (Task 6) |

---

## Task 1: Package Skeleton + ISSNNotation

**Files:**
- Create: `paxman/capabilities/ISSN/__init__.py`
- Create: `paxman/capabilities/ISSN/grammar/__init__.py`
- Create: `paxman/capabilities/ISSN/rules/__init__.py`
- Create: `paxman/capabilities/ISSN/notation.py`
- Create: `tests/capabilities/issn/__init__.py`
- Create: `tests/capabilities/issn/test_notation.py`

- [x] **Step 1: Generate skeleton via scaffolder (HOW_TO_ADD_NEW_CAPABILITY.md Step 0)**

```bash
uv run python tools/new_capability.py ISSN --name issn \
    --authority "ISSN International Centre" --spec-name "ISO 3297:2022" \
    --spec-url "https://www.iso.org/standard/84536.html" \
    --publication-year 2022
```

This creates 13 files + edits `paxman/capabilities/__init__.py`. Verify `paxman/capabilities/ISSN/notation.py` placeholder and `tests/capabilities/issn/test_notation.py` exist, then **replace** the placeholder notation.

- [x] **Step 2: Create minimal package inits if scaffolder left TODOs** (one-line docstring each, Country precedent)

```python
# paxman/capabilities/ISSN/__init__.py — scaffolder already creates re-exports; ensure:
"""ISSN capability for canonicalizing ISSN input."""
```

```python
# paxman/capabilities/ISSN/grammar/__init__.py
"""ISSN recognition grammars."""
```

```python
# paxman/capabilities/ISSN/rules/__init__.py
"""ISSN validation rules."""
```

```python
# tests/capabilities/issn/__init__.py
"""ISSN capability tests."""
```

- [x] **Step 3: RED — write the notation tests** (`tests/capabilities/issn/test_notation.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISSN.notation import ISSNNotation`)

- `test_notation_frozen_and_slots` — `dataclasses.is_dataclass(ISSNNotation)`; `"__slots__" in ISSNNotation.__dict__`.
- `test_notation_fields` — `dataclasses.fields(ISSNNotation)` names == `["digits"]`.
- `test_notation_hashable` — equal instances hash equal.
- `test_notation_immutable` — assigning `notation.digits = "x"` raises `dataclasses.FrozenInstanceError`.
- `test_notation_digits_length` — `ISSNNotation(digits="03178471")` stores 8, uppercased `x`→`X` handled by grammar (notation holds whatever grammar gave it).

- [x] **Step 4: GREEN — implement the notation** (replace scaffolder placeholder `value` field with single `digits`)

```python
# paxman/capabilities/ISSN/notation.py
"""ISSN notation: normalized digit string."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ISSNNotation:
    """ISSN normalized digit string.

    ``digits`` is the 8-character string, hyphen/space stripped, uppercased
    (``x`` → ``X``). The grammar never computes or validates the check digit;
    rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_CAPABILITY.md §4).
    """

    digits: str
```

- [x] **Step 5: Verify + commit**

```bash
uv run pytest tests/capabilities/issn/test_notation.py -q
uv run ruff check paxman/capabilities/ISSN tests/capabilities/issn
uv run pyright paxman/capabilities/ISSN/notation.py
```

Commit: `feat(issn): add ISSNNotation and package skeleton`.

## Task 2: ISSNContract

**Files:**
- Modify: `paxman/capabilities/ISSN/contract.py` (replace scaffolder placeholder)
- Create: `tests/capabilities/issn/test_contract.py`

- [x] **Step 1: RED — write the contract tests** (`tests/capabilities/issn/test_contract.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISSN.contract import ISSNContract`)

- `test_default_output_format` — `ISSNContract().output_format == "hyphenated"`.
- `test_offered_output_formats` — `ISSNContract.OFFERED_OUTPUT_FORMATS == frozenset({"compact", "urn"})`.
- `test_capability_name` — `ISSNContract().capability_name == "issn"`.
- `test_default_is_hyphenated_via_none_and_default_string` — `ISSNContract(output_format=None).output_format == "hyphenated"` and `ISSNContract(output_format="default").output_format == "hyphenated"` and `ISSNContract(output_format="hyphenated").output_format == "hyphenated"` (via `CapabilityContract.__post_init__` + `resolve_output_format`).
- `test_offered_compact_and_urn` — `ISSNContract(output_format="compact").output_format == "compact"`; `"urn"` likewise.
- `test_frozen` — reassigning `contract.output_format` raises `dataclasses.FrozenInstanceError`.
- `test_invalid_output_format_raises` — `ISSNContract(output_format="issn")` raises `ContractError` (unknown format).

No `active_grammars` override — base returns `None` (run every `get_grammars()` grammar). Assert `ISSNContract().active_grammars is None` or that the property is absent.

- [x] **Step 2: GREEN — implement the contract** (replace scaffolder placeholder)

Read `paxman/capabilities/Country/contract.py` first — `ISSNContract` must extend `CapabilityContract` exactly the same way (frozen dataclass, `capability_name` via `field(default=..., init=False)`):

```python
# paxman/capabilities/ISSN/contract.py
"""ISSN contract configuration."""

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ISSNContract(CapabilityContract):
    """Contract for the ISSN capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "hyphenated"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact", "urn"})

    capability_name: str = field(default="issn", init=False)
```

No `_extra_dict_fields()` needed for v1 (no `include_*` flags). Inherited `output_format` resolution is via `CapabilityContract.__post_init__` (do not redeclare `output_format`). Import via `from paxman.core.contract import CapabilityContract` (not `paxman.core.capability_contract`) for homogeneity with `paxman/capabilities/ISBN/contract.py:8`.

- [x] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/issn/test_contract.py -q
uv run ruff check paxman/capabilities/ISSN tests/capabilities/issn
uv run pyright paxman/capabilities/ISSN/contract.py
```

Commit: `feat(issn): add ISSNContract`.

## Task 3: Grammar — ISSN Recognition

**Files:**
- Create: `paxman/capabilities/ISSN/grammar/issn_recognition.py`
- Create: `tests/capabilities/issn/test_grammar.py`

**Purity gate:** grammars do syntax only — extraction + separator/case normalization. No grammar imports from `rules`; no rule imports from `grammar`. CI `tests/unit/test_rule_output_format_purity.py` will fail if any `rules/*.py` contains `output_format`.

- [x] **Step 1: RED — write the grammar tests** (`tests/capabilities/issn/test_grammar.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISSN.grammar.issn_recognition import ISSNRecognitionGrammar`)

- `test_bare_hyphenated` — `"0317-8471"` → 1 match; `notation.digits == "03178471"`, `start == 0`, `end == 9`, `raw_text == "0317-8471"`.
- `test_bare_compact` — `"03178471"` → `digits == "03178471"`.
- `test_label_issn` — `"ISSN 0317-8471"` and `"ISSN: 0317-8471"` each → 1 match; `raw_text` includes label, `digits` stripped.
- `test_label_variants` — `"ISSN-L 0264-2875"` and `"ISSN-H 1365-201X"` → 1 match each (`ISSN(?:-L|-H)?` label).
- `test_lowercase_label_and_x_fold` — `"issn 1050-124x"` → `digits == "1050124X"` (lowercase `x`→`X` folded in `notation_fn`); ensure `re.IGNORECASE` makes `issn` label match.
- `test_leading_zeros_preserved` — `"0000-0019"` → `digits == "00000019"`.
- `test_embedded_in_prose` — `"see ISSN 0317-8471 (print)"` → 1 match with correct `start`/`end`/`raw_text` span.
- `test_glued_label_matches` — `"ISSN03178471"` (no separator after label) → 1 match, `raw_text == "ISSN03178471"`, `digits == "03178471"`. The `[\s:-]*` label group permits zero separators, so the glued label matches and the span includes it — documented shipped behavior; switch to `[\s:-]+` only if strictness is ever wanted.
- `test_wrong_hyphen_placement` — `"12-345679"` → `[]` (strict `-?` at canonical position only — Oracle fix 3).
- `test_tolerant_space_hyphen_rejects` — `"1234 - 5679"` and `"1234 5679"` → `[]` (strict; tolerant variants are `MISSING` unless a `Pre` normalizer added).
- `test_unicode_dash_missing` — `"1234–5679"` (en-dash U+2013) and `"1234—5679"` (em-dash) → `[]` (hyphen-minus only; exotic dashes documented-unsupported).
- `test_digit_glued_rejects` — `"a0317-8471"` → `[]`; `"912345679"` (embedded 8 in 9-digit run) → `[]` or single inner must be blocked by `BoundaryGuard.word_only().lookbehind` (`(?<!\w)`) — shipped; strictly stronger than `isbn10_lead` (`(?<!\d)(?<!\d[ -])`).
- `test_multiple_spans` — `"0317-8471 0378-5955"` → 2 matches ascending `start`; each span `len(raw_text) == end - start`.
- `test_span_invariants` — for every match, `0 <= start <= end <= len(text)` and `raw_text == text[start:end]`.
- `test_empty` — `""` → `[]`.
- `test_name_and_semantics` — `grammar.name == "issn_recognition"`; `grammar.semantics == "issn_recognition"`; non-empty semantics.

- [x] **Step 2: GREEN — implement the grammar** (strict hyphen, module-scope string pattern)

```python
# paxman/capabilities/ISSN/grammar/issn_recognition.py
"""ISSN recognition grammar — regex structural pattern matching."""

import re

from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Module-scope STRING pattern — RegexStage compiles (never re.compile().pattern)
# Strict hyphen at canonical position (pos 4) — tolerant "1234 - 5679" is MISSING.
# Optional ISSN / ISSN-L / ISSN-H label with required separator; case-insensitive.
# word_only (shipped) strengthens isbn10_lead per Oracle P2 — see research rev. 2026-08-22.
_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]*)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN: str = (
    BoundaryGuard.word_only().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.digit().lookahead
    + r"\b"
)


def _issn_notation(match: re.Match[str]) -> ISSNNotation:
    raw_body = match.group("body")
    digits = "".join(ch for ch in raw_body if ch in "0123456789Xx").upper()
    return ISSNNotation(digits=digits)


class ISSNRecognitionGrammar(PipelineGrammar[ISSNNotation]):
    """ISSN recognition: 8-char identifier with optional label."""

    name = "issn_recognition"
    semantics = "issn_recognition"
    single_value = True
    pre = StandardPre[ISSNNotation](empty_guard=True)
    regex = RegexStage[ISSNNotation](
        pattern=_ISSN_PATTERN, notation_fn=_issn_notation, flags=re.IGNORECASE
    )
```

Notes for reviewer: `BoundaryGuard.word_only().lookbehind == r"(?<!\w)"` (shipped); `BoundaryGuard.digit().lookahead == r"(?!\d)"` plus `r"\b"`. The `(?P<body>...)` group isolates the ISSN core for `notation_fn` (label stripped). Trailing `\b` blocks `1234-5679a`. Do **not** double-compile; ship as `str`. For context, `isbn10_lead` is `r"(?<!\d)(?<!\d[ -])"` — word_only is strictly stronger.

- [x] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/issn/test_grammar.py -q
uv run ruff check paxman/capabilities/ISSN
uv run pyright paxman/capabilities/ISSN/grammar/issn_recognition.py
```

Commit: `feat(issn): add ISSN recognition grammar`.

## Task 4: Validation Rule — ISO 3297:2022 Check Digit

**Files:**
- Create: `paxman/capabilities/ISSN/rules/iso_3297_ed2022.py`
- Create: `tests/capabilities/issn/test_rules.py`

- [x] **Step 1: RED — write the rule tests** (`tests/capabilities/issn/test_rules.py`, mark `@pytest.mark.capability`)

Per-rule coverage: `matches()` valid / variant / invalid, `normalize()` canonical output, provenance, name/strategy/citation:

- `test_check_digit_valid_hyphenated` — `Section4CheckDigit().matches(ISSNNotation("03178471"), contract)` True (via `0317-8471`); also `03785955` (Hearing Research), `00280836` (Nature `0028-0836`), `00000019` (leading zeros), `1050124X` (`X`=10).
- `test_check_digit_lowercase_x_valid` — `ISSNNotation("1050124x".upper() → but test with digits "1050124X" is valid; also test that `ISSNNotation("0317847x".upper())` normalizes — variant already covered by grammar folding; rule must accept `X`.
- `test_check_digit_invalid` — `"03785954"` (should be `5`) → False; `"0378595Y"` char invalid; `"12345678"` random → False.
- `test_check_mid_x_rejects` — `ISSNNotation("12X45679")` / `"X2345679"` → False (X not final; `digits[:-1].isdigit()` guard).
- `test_normalize_hyphenated` — `normalize(ISSNNotation("03178471"), contract) == "0317-8471"`; `"1050124X"` → `"1050-124X"`.
- `test_provenance` — `Section4CheckDigit.provenance.authority` contains `ISSN`; `specification_name` contains `ISO 3297:2022`; `kind=="specification"`; `reference_url=="https://www.iso.org/standard/84536.html"`; `version=="2022"`; `lifecycle=="active"`; `publication_year==2022`.
- `test_rule_conventions` — `name=="Section 4-issn-check-digit"`; `strategy==RuleStrategy.PARSER`; `citation` contains `Section 4`; `target_semantics==frozenset({"issn_recognition"})`; `requires_features==frozenset()`.
- `test_no_output_format_token` — source of `iso_3297_ed2022.py` does not contain `output_format` (double-lock with CI scan).

For invalid, use both bad-check and malformed (`len != 8`, non-digit prefix). `normalize()` is only called after `matches()` True, but must still handle defensively: return `f"{digits[:4]}-{digits[4:]}"` or `digits` unchanged for unreachable.

- [x] **Step 2: GREEN — implement the rule file**

Read `paxman/capabilities/ISBN/rules/iso_2108_ed2017.py` first for the `PUBLICATION` + `Rule[Notation]` pattern (six enforced attrs via `Rule.__init_subclass__` in `paxman/core/domain.py`):

```python
# paxman/capabilities/ISSN/rules/iso_3297_ed2022.py
"""ISO 3297:2022 rule: ISSN structure + mod-11 check digit."""

from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISSN International Centre",
    specification_name="ISO 3297:2022",
    kind="specification",
    reference_url="https://www.iso.org/standard/84536.html",
    version="2022",
    lifecycle="active",
    publication_year=2022,
)


def _issn_check(digits: str) -> str:
    """Compute expected check char for 8-char digits (weights 8→2, X=10)."""
    total = sum(int(d) * (8 - i) for i, d in enumerate(digits[:7]))
    check = (11 - total % 11) % 11
    return "X" if check == 10 else str(check)


class Section4CheckDigit(Rule[ISSNNotation]):
    """ISO 3297 Section 4 — ISSN check digit (8→2, X=10)."""

    name = "Section 4-issn-check-digit"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (check digit)"
    target_semantics = frozenset({"issn_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ISSNNotation, contract: Contract) -> bool:
        if len(notation.digits) != 8:
            return False
        if not notation.digits[:7].isascii() or not notation.digits[:7].isdigit():
            return False
        last = notation.digits[7].upper()
        if last not in "0123456789X":
            return False
        return last == _issn_check(notation.digits)

    def normalize(self, notation: ISSNNotation, contract: Contract) -> str:
        # Default canonical is hyphenated XXXX-XXXX (per ISSNContract DEFAULT)
        digits = notation.digits.upper()
        return f"{digits[:4]}-{digits[4:]}"
```

Never read `contract.output_format` here — CI purity gate fails otherwise. `normalize()` always returns hyphenated (the `DEFAULT_OUTPUT_FORMAT`); `format_value()` handles `compact`/`urn`.

- [x] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/issn/test_rules.py -q
uv run ruff check paxman/capabilities/ISSN
uv run pyright paxman/capabilities/ISSN/rules/iso_3297_ed2022.py
```

Commit: `feat(issn): add ISO 3297:2022 check-digit rule`.

## Task 5: Capability Wiring — `ISSNCapability` + `format_value`

**Files:**
- Create: `paxman/capabilities/ISSN/capability.py`
- Create: `tests/capabilities/issn/test_capability.py`

The wiring mirrors `paxman/capabilities/Country/capability.py` and `paxman/capabilities/ISBN/capability.py`: module `__all__`, staticmethod `create_contract` factory, `get_grammars()`/`get_rules()` returning fresh instances, and `format_value()` seam (presentation only, never touches candidate identity or provenance).

- [x] **Step 1: RED — write the capability tests** (`tests/capabilities/issn/test_capability.py`, mark `@pytest.mark.capability`, import `from paxman.capabilities.ISSN.capability import ISSNCapability`)

- `test_capability_name_version` — `ISSNCapability.name == "issn"`, `.version == "1.0.0"`.
- `test_get_grammars` — `len(cap.get_grammars()) == 1`; names `{"issn_recognition"}`.
- `test_get_rules` — `len(cap.get_rules()) == 1`; names `["Section 4-issn-check-digit"]` in order.
- `test_create_contract_defaults` — `c = ISSNCapability.create_contract()`; `c.output_format == "hyphenated"` (resolved by `CapabilityContract.__post_init__`); `c.capability_name == "issn"`; no `active_grammars` gating (inherits `None`).
- `test_create_contract_output_format` — `create_contract(output_format="compact")` → `c.output_format == "compact"`; `"urn"` likewise; `"issn"` raises `ContractError`.
- `test_format_value_hyphenated_identity` — `format_value("0317-8471", "hyphenated", notation) == "0317-8471"` and `format_value("0317-8471", None, notation) == "0317-8471"` (default path — None is treated as hyphenated via resolve).
- `test_format_value_compact` — `format_value("0317-8471", "compact", notation) == "03178471"`.
- `test_format_value_urn` — `format_value("0317-8471", "urn", notation) == "urn:issn:0317-8471"`.
- `test_format_value_urn_with_x` — `format_value("1050-124X", "urn", notation) == "urn:issn:1050-124X"` (X preserved uppercase).

Use helper `notation = ISSNNotation(digits="03178471")` for the format tests (value is hyphenated string, notation is the object).

- [x] **Step 2: GREEN — implement `paxman/capabilities/ISSN/capability.py`**

```python
"""ISSN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISSN.contract import ISSNContract
from paxman.capabilities.ISSN.grammar.issn_recognition import ISSNRecognitionGrammar
from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.capabilities.ISSN.rules.iso_3297_ed2022 import Section4CheckDigit
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ISSNCapability", "ISSNContract", "ISSNNotation"]


class ISSNCapability(Capability[ISSNNotation]):
    """ISSN canonicalization capability.

    Canonicalizes ISSN input to the hyphenated form XXXX-XXXX
    per ISO 3297:2022 with full provenance.
    """

    name = "issn"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[ISSNNotation]]:
        return [ISSNRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISSNNotation]]:
        return [Section4CheckDigit()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> ISSNContract:
        """Factory for contracts with proper defaults."""
        return ISSNContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ISSNNotation,
    ) -> str:
        """Render the hyphenated canonical value in the requested format.

        The default ``"hyphenated"`` path is identity. ``"compact"`` strips
        the hyphen; ``"urn"`` wraps ``urn:issn:``. Never affects candidate
        identity or provenance.
        """
        if output_format == "compact":
            return value.replace("-", "")
        if output_format == "urn":
            return f"urn:issn:{value}"
        return value
```

- [x] **Step 3: Verify + commit**

```bash
uv run pytest tests/capabilities/issn/test_capability.py -q
uv run ruff check paxman/capabilities/ISSN
uv run pyright paxman/capabilities/ISSN
```

Commit: `feat(issn): wire ISSNCapability with create_contract and format_value`.

## Task 6: Registration — Capability Registry, Pytest Marker, Exports

**Files:**
- Modify: `paxman/capabilities/__init__.py`
- Modify: `pyproject.toml`
- Modify: `tests/unit/test_capability_exports.py`

- [x] **Step 1: RED — extend the exports test** (`tests/unit/test_capability_exports.py`)

Change the import to `from paxman.capabilities import Country, Currency, Date, Email, IP, ISBN, ISSN, Money, Phone, SIUnit, URL` (add `ISSN`) and add a class mirroring existing ones:

```python
class TestISSNCapabilityExports:
    @pytest.mark.unit
    def test_issn_capability_importable(self) -> None:
        """ISSN capability is importable from paxman.capabilities."""
        assert ISSN is not None

    @pytest.mark.unit
    def test_issn_capability_name(self) -> None:
        """ISSN capability has correct name."""
        assert ISSN.name == "issn"
```

- [x] **Step 2: GREEN — wire the registry (PEP 562 lazy)**

`paxman/capabilities/__init__.py` — add the ISSN entry to `_LAZY` (alphabetical after `ISBN`), append `"ISSN"` to `__all__` alphabetically, and add the `TYPE_CHECKING` import. Keep every existing line, keep `__getattr__`/`__dir__` untouched:

```python
__all__ = [
    "Country",
    "Currency",
    "Date",
    "Email",
    "IP",
    "ISBN",
    "ISSN",
    "Money",
    "Phone",
    "SIUnit",
    "URL",
]

_LAZY: dict[str, tuple[str, str]] = {
    "Country": ("paxman.capabilities.Country.capability", "CountryCapability"),
    "Currency": ("paxman.capabilities.Currency.capability", "CurrencyCapability"),
    "Date": ("paxman.capabilities.Date.capability", "DateCapability"),
    "Email": ("paxman.capabilities.Email.capability", "EmailCapability"),
    "IP": ("paxman.capabilities.IP.capability", "IPCapability"),
    "ISBN": ("paxman.capabilities.ISBN.capability", "ISBNCapability"),
    "ISSN": ("paxman.capabilities.ISSN.capability", "ISSNCapability"),
    "Money": ("paxman.capabilities.Money.capability", "MoneyCapability"),
    "Phone": ("paxman.capabilities.Phone.capability", "PhoneCapability"),
    "SIUnit": ("paxman.capabilities.SIUnit.capability", "SIUnitCapability"),
    "URL": ("paxman.capabilities.URL.capability", "URLCapability"),
}

if TYPE_CHECKING:
    from paxman.capabilities.Country.capability import CountryCapability as Country
    from paxman.capabilities.Currency.capability import CurrencyCapability as Currency
    from paxman.capabilities.Date.capability import DateCapability as Date
    from paxman.capabilities.Email.capability import EmailCapability as Email
    from paxman.capabilities.IP.capability import IPCapability as IP
    from paxman.capabilities.ISBN.capability import ISBNCapability as ISBN
    from paxman.capabilities.ISSN.capability import ISSNCapability as ISSN
    from paxman.capabilities.Money.capability import MoneyCapability as Money
    from paxman.capabilities.Phone.capability import PhoneCapability as Phone
    from paxman.capabilities.SIUnit.capability import SIUnitCapability as SIUnit
    from paxman.capabilities.URL.capability import URLCapability as URL
```

`pyproject.toml` — add the ISSN marker alphabetically under `[tool.pytest.ini_options] markers` between `isbn` and `money`:

```toml
    "issn: issn capability tests",
```

- [x] **Step 3: Verify + commit**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/capabilities/issn -q
uv run ruff check paxman/capabilities/__init__.py
uv run pyright paxman/capabilities
```

Sanity: `uv run python -c "from paxman.capabilities import ISSN; print(ISSN.name)"` → `issn`.

Commit: `feat(issn): register ISSN capability and pytest marker`.

## Task 7: Integration Tests — Resolution Map + Pipeline

**Files:**
- Create: `tests/integration/test_issn_capability.py`

Add autouse `_clean_registry` fixture? Only if integration style uses it — follow `tests/integration/test_pipeline.py` pattern. Otherwise use `paxman.register_capability(ISSN())` per test or `register_all_shipped()`.

- [x] **Step 1: RED — write integration tests** (`tests/integration/test_issn_capability.py`, mark every test `@pytest.mark.integration`)

Resolution map (from §9 of the memo — every row is a locked semantic):

| Test | Input | Contract | Expected |
|------|-------|----------|----------|
| `test_bare_hyphenated_success` | `"0317-8471"` | default | `SUCCESS`, `canonicalized_value=="0317-8471"` |
| `test_compact_success` | `"03178471"` | default | `SUCCESS`, `"0317-8471"` |
| `test_label_success` | `"ISSN 0317-8471"` | default | `SUCCESS`, `"0317-8471"`, `recognition_rule=="issn_recognition"` |
| `test_x_fold_success` | `"1050-124x"` | default | `SUCCESS`, `"1050-124X"` (folded) |
| `test_leading_zeros_success` | `"0000-0019"` | default | `SUCCESS`, `"0000-0019"` |
| `test_compact_output` | `"0317-8471"` | `output_format="compact"` | `SUCCESS`, `"03178471"` |
| `test_urn_output` | `"0317-8471"` | `output_format="urn"` | `SUCCESS`, `"urn:issn:0317-8471"` |
| `test_invalid_check` | `"0378-5954"` | default | `INVALID` (bad mod-11) |
| `test_mid_x_missing` | `"12X4-5679"` | default | `MISSING` (grammar filters mid-X; rule-level `matches()` rejects but is unreachable end-to-end) |
| `test_wrong_hyphen_missing` | `"12-345679"` | default | `MISSING` (strict grammar) |
| `test_no_digits_missing` | `"call me at noon"` | default | `MISSING` |
| `test_two_distinct_ambiguous` | `"0317-8471 / 0378-5955"` | default | `AMBIGUOUS` or `MultipleMentionsError` (`single_value=True`) |
| `test_pinned_rule` | `"0317-8471"` | `pinned_rules=["Section 4-issn-check-digit"]` | `SUCCESS`, `"0317-8471"` |
| `test_year_filter` | `"0317-8471"` | `year=2022` / `year=2021` | `SUCCESS` / `INVALID` (2022 rule filtered when year<2022) — verifies temporal filtering |
| `test_excluded_rule` | `"0317-8471"` | `excluded_rules=["Section 4-issn-check-digit"]` | `INVALID` (no validating rule) |

Also assert `result.span` / `candidate.span` / `recognition_rule` / `validation_rule` / `provenance` where relevant (`candidate.provenance[0].specification_name == "ISO 3297:2022"`).

- [x] **Step 2: GREEN — make them pass (no code change expected if tasks 3-5 are correct)**

```bash
uv run pytest tests/integration/test_issn_capability.py -q
```

Commit: `feat(issn): add ISSN integration suite`.

## Task 8: Property-Based Tests

**Files:**
- Create: `tests/property/test_issn_properties.py` (or `tests/property/test_issn.py` per existing naming)

- [x] **Step 1: RED — write hypothesis tests**

- `test_generate_valid_issn_round_trip` — generate valid ISSNs from mod-11 algorithm: random 7 digits → compute check → build `digits` → `SUCCESS` round-trip, hyphenated canonical stable.
- `test_random_8char_is_invalid_high_prob` — random 8-char strings (excluding valid ISSNs) → `INVALID` with high probability (grammar may recognize but check fails).
- `test_hyphenated_vs_bare_same_value` — for a valid ISSN, `canonicalize("0317-8471")` and `canonicalize("03178471")` produce identical `canonicalized_value` (both hyphenated).
- `test_compact_vs_hyphenated_same_identity` — `output_format` only changes rendering; value without `compact`/`urn` is hyphenated.
- `test_x_uppercase_invariant` — valid ISSN with `X` check (`1050-124X`) lower `x` → upper.

Use `hypothesis` `given` with `strategies.text` constrained, or direct `digits` generation.

- [x] **Step 2: GREEN — run**

```bash
uv run pytest tests/property/test_issn_properties.py -q
```

Commit: `feat(issn): add ISSN property suite`.

## Task 9: Final Verification + Docs Sweep

**Files:** all files changed by Tasks 1-8; `README.md`, `CONTEXT.md` if capability table exists.

- [x] **Step 1: Run the pre-PR gate**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -q
```

Expected: all green; coverage ≥95% per package (new ISSN fully covered by unit + integration + property tests). Note: `paxman/capabilities/__init__.py` export completeness is enforced by `tests/unit/test_capability_exports.py`.

- [x] **Step 2: Verify purity and contracts**

```bash
uv run pytest tests/unit/test_rule_output_format_purity.py -q
uv run pytest tests/unit/test_capability_exports.py -q
uv run pytest -m "issn or integration" -q
```

- [x] **Step 3: Docs sweep**

- Update `README.md` capabilities table (if present) — Grammars: 1, Rules: 1, add ISSN row.
- Ensure `CONTEXT.md` notation table (if present) reflects `ISSNNotation(digits)`.
- No references to `docs/development/` in shipped code (`paxman/`, `tests/`, or `README.md` prose) — `docs/development/AGENTS.md` forbids it; ISSN test files must not cite plan task numbers or quote plan content (docstrings/comments swept in this revision).

- [x] **Step 4: Commit**

Atomic commits per task already done; final `git status` clean except plan/report which are `docs/development/` (excluded from sdist). Push branch and open PR.

---

## Execution Notes for Agents

- **TDD mandatory:** failing test first for every task.
- **`output_format` purity:** no `output_format` token in `paxman/capabilities/ISSN/rules/*.py` (code, comments, docstrings) — CI fails otherwise.
- **`@dataclass(frozen=True)` contracts without `slots`**; notations with `frozen=True, slots=True`.
- **Cross-capability imports forbidden** — `paxman.core` only (import-linter).
- **No `# type: ignore` / `# noqa` in `paxman/` source.**
- **Use `uv run` for every command** (ruff, pyright, pytest, import-linter).

