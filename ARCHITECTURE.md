# Paxman Architecture

Paxman is a canonicalization authority resolver — a library that takes ambiguous human input and returns what authoritative specifications say that input means, with full provenance. This document describes the architectural principles, structural layers, and design decisions that shape the system.

---

## Core Principles

### Determinism

Paxman never guesses. Given the same input, the same contract configuration, and the same library snapshot (fixed library version, registry contents, and rule-data tables), the pipeline always yields the same canonical output. This property holds by construction: every pipeline stage — grammar recognition, rule validation, capability formatting, candidate deduplication, and status determination — is a pure function of its inputs with no world-knowledge, no clock, no environment-dependent ordering, no fuzzy logic, and no network inference. Identical inputs therefore always produce identical outputs, enabling auditability and reproducibility. Across library snapshots, provenance or rule-routing changes may alter the resulting metadata; the determinism guarantee is scoped to a fixed snapshot.

### Provenance-First

Every canonicalized value carries full provenance — a citation of the authoritative specification, registry, or policy that validates it. Provenance is not optional metadata; it is a structural requirement. If no authority can validate a recognized input, the system reports INVALID rather than returning an unvalidated value. This ensures that users always know *why* a value is considered canonical.

### Separation of Recognition and Validation

Paxman strictly separates the act of finding values in text (recognition) from the act of determining whether those values are valid (validation). This separation is the foundation of the architecture:

- **Recognition** (syntactic): Grammars scan raw text and extract structured representations. They do not validate — they only find.
- **Validation** (semantic): Rules accept structured representations and determine whether authoritative specifications validate them. They produce canonical values with provenance.

This separation means that a single input can be recognized by multiple grammars and validated by multiple rules, enabling ambiguity detection when different authoritative sources disagree.

### Recognition Pipeline Contract

Every grammar implements `recognize(text) -> list[RecognitionMatch]`, where
`RecognitionMatch` carries the notation plus a half-open `[start, end)` span
and the matched `raw_text`. The grammar produces positions; the engine owns
all cross-match policy:

- **Containment dedup (per grammar):** a match fully contained in a longer
  match from the SAME grammar is dropped ("longer wins"). Matches from the
  same grammar with identical `[start, end)` spans keep the first-emitted
  match. Dedup never runs across grammars, so two grammars agreeing on the
  same span (e.g. US vs European date reading of `01/02/2026`) are both
  preserved and ambiguity stays observable.
- **Ordering:** recognitions are emitted in the total order
  `(start, end, active-set index, grammar name)`, i.e. document order — where the
  active set is `contract.active_grammars` or, when the contract returns `None`,
  every shipped grammar in `get_grammars()` order.
- **Candidate dedup** (`value, recognition_rule, validation_rule`) runs
  after validation as a stability net.

Grammars perform syntax-level extraction and normalization only; rules own
semantic validation with provenance. This contract applies identically to
every capability, built-in or future.

### Capability Isolation

Each domain (Email, Date, Country, etc.) is encapsulated as a **Capability** — an independent module that defines its own intermediate representation, recognition rules, and validation rules. Capabilities cannot import from each other. The engine and core domain provide the orchestration layer; capabilities provide the domain expertise.

---

## Structural Layers

Paxman is organized into four layers, each with a distinct responsibility. Dependencies flow inward — outer layers depend on inner layers, never the reverse.

### Core Domain

The innermost layer defines the shared vocabulary and abstract contracts that all other layers consume. It contains:

- **Abstract base classes** for Grammars (recognition) and Rules (validation)
- **Immutable value objects** representing provenance, candidates, recognized representations, and version stamps
- **Enums** for resolution status (MISSING, INVALID, SUCCESS, AMBIGUOUS) and rule strategies (REGEX, LOOKUP_TABLE, PARSER)
- **The Contract protocol** — a structural interface that all capability contracts must satisfy
- **The Capability abstract class** — a base class that all capability implementations must extend
- **The discovery registry** — a module-level registry that manages capability registration and lookup
- **Exception hierarchy** — typed errors for different failure modes

The core layer has no knowledge of specific capabilities. It defines *what* a capability is, not *how* any particular capability works.

### Capabilities

Each capability is a self-contained domain module that provides:

- **A Notation type** — a typed intermediate representation specific to the domain (e.g., email local part and domain part, date N1/N2/N3)
- **Grammars** — recognition rules that extract the notation from raw text
- **Validation Rules** — semantic rules that validate the notation against authoritative specifications
- **A Contract** — a user-facing configuration object that toggles grammars, excludes rules, and passes parameters

Capabilities are registered with the discovery registry before the first canonicalization call. The registry freezes on the first `canonicalize()` call and remains frozen for later runs, ensuring that the set of available capabilities is stable during execution. The sanctioned bulk form is `paxman.register_all_shipped()`, which registers all fifteen shipped capabilities in fixed alphabetical order; registration — single or bootstrap — must complete from a single thread before the first `canonicalize()` call, after which reads are safe from any thread. Recognition is via the Recognition Kernel (ADR-0009) — see that ADR for the substrate, matcher kinds, and boundary/anchor discipline; legacy pipeline stages remain for unmigrated grammars.

### Engine

The engine is the orchestration layer that coordinates the full pipeline. It:

1. Freezes the capability registry
2. Looks up the requested capability by name
3. Runs the recognition phase — iterating over active grammars to extract span-bearing recognition matches
4. Runs the validation phase — testing each notation against active rules, which normalize to each capability's default canonical form and never inspect `output_format`
5. Formats each validated value through the capability's `format_value()` seam — immediately after normalization and before deduplication and status determination
6. Deduplicates identical candidates
7. Determines the resolution status based on candidate outcomes
8. Assembles the final execution result

The engine is capability-agnostic. It does not know what a "grammar" or "rule" does — it only knows that grammars produce span-bearing recognition matches and rules produce candidates.

Before the recognition phase, the engine composes each capability's shipped grammars and rules with any community extensions registered for that capability (see "Community Extensions" below). Composition is guarded: duplicate names fail fast, and every rule's declared `target_semantics` must resolve within the composed set.

### Public API

The outermost layer exposes the user-facing interface. It is intentionally minimal — a single entry point that accepts input text and a contract, and returns a fully-resolved execution result with full provenance.

---

## Key Architectural Patterns

### Protocol-Based Contracts

Contracts are defined as structural protocols (`Contract`), not inheritance-based base classes. Any class that satisfies the structural interface — providing the required attributes and methods — qualifies as a contract. This allows capability authors to design contract objects that fit their domain (using dataclasses, Pydantic models, etc.) without being constrained by a base class hierarchy. This prioritizes **user flexibility** and **decoupling**.

### ABC-Based Capabilities

In contrast to contracts, Capabilities are defined as Abstract Base Classes (`Capability`). This prioritizes **internal rigidity** and **reliability**. Since capabilities are internal components managed by the engine's registry, strict inheritance ensures they adhere to the required structure (`get_grammars()`, `get_rules()`) and prevents runtime errors during discovery.

### Capability as Factory

Capabilities do not hold state. They are factories that produce grammars and rules on demand. The engine queries a capability for its available grammars and rules, then filters them based on the contract configuration. This design keeps capabilities lightweight and makes the filtering logic centralized in the engine.

### Typed Notation

Each capability defines a frozen dataclass Notation with one `str` field per recognized component (e.g., `DateNotation` carries `N1`, `N2`, `N3`). The concrete notation type is the sole type parameter threaded end to end: `Grammar[NotationT]` recognizes it and `Rule[NotationT]` validates it, so the engine and every rule operate on the fully typed object rather than a positional `list[str]`. Rules read notation fields by name (e.g., `notation.N1`); there is no generic list alias and no conversion bridge between the typed notation and a list form.

### Contract Parameters

Contracts pass configuration parameters to validation rules, enabling rules to adapt their behavior based on user preferences.

**Base Contract Parameters:**
- **`output_format`**: Controls the canonical value format (e.g., `"ISO"` for `YYYY-MM-DD`, `"US"` for `MM/DD/YYYY`). `CapabilityContract.__post_init__` resolves `None`, `"default"`, and each capability's default format to a concrete string; the capability's `format_value()` seam applies the format to the rule-produced default canonical value. Validation rules never inspect `output_format` — they always normalize to the default canonical form. See "The Formatting Seam" below.
- **`pinned_rules`**: Pins to specific validation rules by name. When set, ONLY those rules run — `excluded_rules` is ignored. Takes precedence over `excluded_rules`.
- **`extra_grammars`**: Names community grammars (opt-in) to run alongside the capability's shipped active set — `contract.active_grammars`, or every shipped grammar when the contract returns `None` — in order. Unknown names are silently skipped; shipped names listed here are deduplicated. Registration happens through `paxman.register_grammar` / `paxman.register_rule` (see "Community Extensions" below).

**Date-Specific Parameters:**
- **`two_digit_base_year`**: Specifies the base year for interpreting two-digit years (e.g., `2000` means `"26"` becomes `2026`). Only available on Date contracts, not part of the base Contract protocol. Used by US and European grammars to resolve ambiguous year values.

These parameters are passed through the contract to rule methods (`matches()` and `normalize()`), allowing rules to be contract-aware without direct coupling to specific capabilities. `output_format` is the exception: it is a presentation parameter consumed by the capability's formatting seam, never by validation rules.

### The Formatting Seam

Validation and presentation are separated at the pipeline level. Rules own validation and default normalization only: `matches()` never consults `output_format`, and `normalize()` always returns the capability's default canonical form (e.g., `YYYY-MM-DD` for Date, E.164 `+CCNSN` for Phone, alpha-2 for Country). The engine then renders each validated value through the capability's `format_value(value, output_format, notation)` method — called immediately after `normalize()` and before candidate deduplication and status determination:

**recognition → validation → default normalization → capability formatting → candidate deduplication → status → result**

Formatting adds no provenance: `Candidate.provenance`, `recognition_rule`, and `validation_rule` are set from the rule that validated the notation, and the formatter only transforms the value. Date, Phone, and Country implement conversions; Email and IP inherit the identity implementation because they offer no alternative formats.

A CI source scan (`tests/unit/test_rule_output_format_purity.py`) rejects any `output_format` token in `paxman/capabilities/*/rules/` modules — in code, comments, or docstrings — so presentation cannot migrate back into rules. In the Country capability, localized names (e.g., `Alemania` → `DE`) are formatted through the current alpha-2 conversion tables for `alpha3`, `numeric`, and `name` while retaining Unicode/CLDR provenance; historical former codes (e.g., `SU`) pass through unchanged for those formats when no current mapping exists, retaining ISO 3166-3 provenance.

### Immutability

All domain objects are immutable. Once created, they cannot be modified. This is enforced through `@dataclass(frozen=True, slots=True)` — stdlib dataclasses that prevent attribute assignment and use efficient slot-based storage. Immutability ensures that objects can be safely shared, hashed, and used as dictionary keys without defensive copying.

### Temporal Filtering

Rules carry a publication year from their authoritative specification. When a contract specifies a year, the engine filters out rules whose publication year exceeds that year. This allows users to pin to a specific historical version of a specification, excluding rules from newer revisions.

### Determinism by Construction

Determinism is a structural property of the layered pipeline, not a post-hoc artifact:

- **Recognition layer.** Active grammars emit span-bearing `RecognitionMatch` objects from the input text, matching the `Grammar.recognize()` contract. Grammar output depends only on the input and the grammar itself.
- **Validation layer.** Rules accept recognized representations and produce candidates, each carrying a canonical value and provenance. A rule's output depends only on the representation and the contract.
- **Result layer.** The engine deduplicates identical candidates and folds the distinct candidate values into one of the resolution statuses: `SUCCESS` when all candidates agree on a single canonical value, `AMBIGUOUS` when they disagree, `INVALID` when nothing validated, and `MISSING` when no grammar recognized anything.

Every stage is a pure function of its inputs — no clocks, no randomness, no environment-dependent ordering, no world-knowledge, no fuzzy logic, no network inference — so the same input, contract configuration, and library snapshot (fixed library version, registry contents, and rule-data tables) always produce the same canonical output. The `VersionStamp` on each execution result records the library version for provenance; the determinism guarantee rests on this determinism-by-construction. Changes to provenance or rule routing across library snapshots can alter result metadata; the determinism guarantee is scoped to a fixed snapshot.

### Community Extensions

Capabilities are closed for modification but open for extension. Community contributors register additional grammars (and the rules that validate them) against an existing capability through `paxman.core.extensions` — never by editing the capability package. The registries freeze with the capability registry at the first pipeline run.

A contract opts a registered grammar in by naming it in `extra_grammars`, a base `CapabilityContract` field surfaced on every `create_contract` factory. The engine composes the shipped active set with the opted-in extras, deduplicating names while preserving order — shipped slots first, extras after (unknown extra names are silently skipped). The shipped slots are `contract.active_grammars` when the contract implements it (the gated capabilities), or every shipped grammar in `get_grammars()` order when it returns `None` (the base default). Opt-in preserves determinism: a contract that names no extras composes to exactly the shipped set, so non-opt-in behavior is identical (deterministic).

Community rules follow the same opt-in discipline: a registered rule runs only when the contract's `extra_grammars` resolve to one of its `target_semantics` ids. An un-opted community rule — even one targeting a shipped grammar's semantics — never affects results, so a default contract resolves with shipped rules only.

Composition is guarded at pipeline start: a community grammar name colliding with a shipped name raises `CapabilityError`, and an opted-in community rule whose `target_semantics` names an id no grammar claims raises `ContractError` — failing fast rather than producing a silently wrong result. Community grammars and rules are pure functions of their inputs, and the composed set is fixed once the registries freeze, so the determinism guarantees of "Determinism by Construction" extend unchanged.

---

## Resolution Semantics

The system produces one of four resolution statuses:

| Status | Meaning |
|--------|---------|
| **MISSING** | No grammars recognized anything in the input. The input does not match any known pattern. |
| **INVALID** | Grammars recognized the input, but no validation rule could validate it against an authoritative specification. |
| **SUCCESS** | One or more rules validated the input, and all agree on the same canonical value. |
| **AMBIGUOUS** | Multiple rules validated the input but produced different canonical values. The system cannot determine which is correct. |

Ambiguity is detected at the value level, not the candidate level. Multiple candidates with the same canonical value still produce SUCCESS. Ambiguity requires genuinely different canonical outputs from different authoritative sources.

For multi-entity input, segmentation is caller-owned — see the [segmentation recipe](docs/recipes/segmentation.md) (ADR-0004 companion).

---

## Error Handling

The exception hierarchy separates different failure modes:

- **CapabilityError** — the requested capability is unknown or the registry is in an invalid state
- **ContractError** — the contract configuration is malformed or missing required fields
- **RecognitionError** — a grammar failed during recognition (e.g., malformed regex), wrapping the original exception
- **ValidationError** — a rule failed during validation (e.g., unexpected data), wrapping the original exception

Recognition and validation errors carry the name of the offending rule and the original exception, enabling targeted debugging without losing context.

---

## Quality Enforcement

Paxman enforces architectural invariants through tooling:

- **Static type checking** in strict mode ensures type safety across all layers
- **Import boundary enforcement** prevents capability-to-capability dependencies and ensures the core layer remains independent
- **Linting and formatting** enforce consistent code style
- **Rule-purity source scan** fails CI when any validation-rule module under `paxman/capabilities/*/rules/` references `output_format`, enforcing that presentation is owned solely by `Capability.format_value()`
- **Property-based testing** validates domain object contracts (immutability, equality, hashability)

These tools run as part of the development workflow and block merges when invariants are violated.

---

## Date Capability Design

The Date capability demonstrates the system's handling of ambiguous inputs through a single grammar and multiple validation rules.

### Grammars

1 grammar (`date`) with 4 candidates (iso8601, slash_iso, us, european) via `CandidatesMatcher` strategy=`'all'`:

| Candidate | Delimiter | N1 (first) | N2 (second) | N3 (third) | Notes |
|-----------|-----------|------------|-------------|------------|-------|
| iso8601 | `-` | year | month | day | 4-digit year only |
| slash_iso | `/` | year | month | day | 4-digit year first |
| us | `/` | month | day | year | Supports 2-digit years |
| european | `/` | day | month | year | Supports 2-digit years |

Candidates share the single `DateGrammar` via `CandidatesMatcher`; `us` and `european` both use `/` so `strategy='all'` keeps `01/02/2026` as two recognitions and `AMBIGUOUS` stays observable.

### Validation Rules

Three rules validate date notations against authoritative specifications:

| Rule | Standard | Canonical Output |
|------|----------|------------------|
| ISO 8601 | ISO 8601:2019 | `YYYY-MM-DD` |
| US federal | US government standard | `YYYY-MM-DD` |
| EN 50160 | European EN 50160 | `YYYY-MM-DD` |

All rules normalize to ISO 8601 format (`YYYY-MM-DD`) regardless of input grammar; the capability's formatting seam applies a requested alternative (e.g., `output_format="US"`) to that default afterward.

### Ambiguity Detection

When the same input matches multiple candidates, the single `DateGrammar` emits two `RecognitionMatch`es via `us` + `european` candidates with different position mappings. For example, `"01/02/2026"`:
- `us` candidate: N1=month=01, N2=day=02, N3=year=2026
- `european` candidate: N1=day=01, N2=month=02, N3=year=2026

Each recognition flows to its corresponding validation rule. If both rules validate and produce different canonical values, the system reports AMBIGUOUS.
