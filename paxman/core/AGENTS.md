# PAXMAN CORE KNOWLEDGE BASE

**Scope:** `paxman/core/` — the foundation layer and import-linter leaf. 8 modules plus the `grammar/` subpackage (capability-agnostic recognition-layer machinery: kernel surface `ScanContext`/`MatcherSpec`/`engine_loop`/`matchers/`/`anchors`/`boundary_spec`/`normalizers` plus legacy `BoundaryGuard`/`AmountComposer`/`LexiconAlternation`/`PipelineGrammar`/stage types which remain for unmigrated grammars). Imports from nothing inside `paxman.*`; every other package imports from here.

## OVERVIEW
Core owns the domain vocabulary (pipeline value objects + `Rule`/`Grammar` ABCs), the contract surface (`Contract` protocol, `CapabilityContract` base, `output_format` policy), the capability registry, the community extension registries (`extensions.py`), shared recognition machinery (`grammar/`), and the error hierarchy. Everything `paxman.api` and `paxman.engine` shuffle through the pipeline is defined here.

## WHERE TO LOOK

| Task | Location |
|------|----------|
| Add a pipeline value object | `paxman/core/domain.py` |
| Write a validation rule | `paxman/core/domain.py` → subclass `Rule` |
| Write a recognition grammar | `paxman/core/domain.py` → subclass `Grammar` |
| Add a capability contract | `paxman/core/capability_contract.py` → subclass `CapabilityContract` |
| Extend `output_format` policy / protocol surface | `paxman/core/contract.py` |
| Add a capability class | `paxman/core/capability.py` → subclass `Capability` |
| Registry / freezing behavior | `paxman/core/discovery.py` (+ `list_registered_capabilities()`, `is_registry_frozen()`) |
| Community grammar/rule extensions | `paxman/core/extensions.py` → `register_grammar()` / `register_rule()`; contracts opt in via `extra_grammars`; registries freeze with the capability registry |
| Shared recognition machinery — kernel (`ScanContext`, `MatcherSpec`, `engine_loop`, `matchers/`, `anchors`, `boundary_spec`, `normalizers`; legacy `stages`, `BoundaryGuard`, `LexiconAlternation`, `PipelineGrammar` remain) | `paxman/core/grammar/` |
| New exception type | `paxman/core/errors.py` → subclass `PaxmanError` |
| Top-level re-exports | `paxman/core/__init__.py` |

## CONVENTIONS
- **Layer discipline:** `paxman.core` must never import from `paxman.api`, `paxman.engine`, or `paxman.capabilities`. If a new core type needs something from outside, it does not belong here.
- **Value objects** (`domain.py`): `@dataclass(frozen=True, slots=True)`. Spans are half-open with `len(raw_text) == end - start`, enforced in `__post_init__`. `GrammarRule` enforces lowercase names; `RecognizedRep.__hash__` handles unhashable list notations; `Candidate._provenance` is `init=False` and tuple-ized in `__init__`.
- **`Rule` subclasses** must declare `name`, `strategy`, `provenance`, `citation`, `target_semantics` (non-empty `frozenset[str]`), `requires_features` (`frozenset[str]`) as class attrs. `Rule.__init_subclass__` raises `TypeError` at import time for missing/mistyped metadata — keep it a hard import-time failure. `matches()`/`normalize()` never raise.
- **`Grammar` subclasses** must declare `name` and `semantics` — a non-empty string, the meaning id the grammar's notations carry (identity id by default; same-meaning grammars share one coalesced id). `Grammar.__init_subclass__` raises `TypeError` at import time for a missing, non-string, or empty `semantics`. `recognize()` returns span-bearing `RecognitionMatch` only, never bare notation.
- **Contracts:** subclass `CapabilityContract`, never `Contract` directly. Set `DEFAULT_OUTPUT_FORMAT`/`OFFERED_OUTPUT_FORMATS`, set `capability_name` via `field(default=..., init=False)`. `active_grammars` is optional: it returns `None` by default (the engine then runs every shipped `get_grammars()` entry); only feature-gated capabilities (Email, IP, ISBN) override it.
- **`output_format`** is always optional: `None`/`"default"`/`DEFAULT_OUTPUT_FORMAT` resolve to the default, offered formats resolve to themselves, anything else raises `ContractError`. Resolved once in `CapabilityContract.__post_init__`; subclasses with their own `__post_init__` call `super().__post_init__()` first. Note: `resolve_output_format` is imported lazily there to break the `capability_contract` ↔ `contract` import cycle.
- **`pinned_rules` wins over `excluded_rules`** (non-`None` pins; empty tuple pins to nothing); `year` filtering still applies after pinning.
- **Registry** (`discovery.py`): module-level `_registry` dict + `_frozen` flag. `register_capability()` takes `Any` and isinstance-checks `Capability`; rejects dupes and post-freeze adds with `CapabilityError`. Introspection via `list_registered_capabilities()` / `is_registry_frozen()`. `freeze_registry()` also freezes the extension registries (`extensions.py`) and is called by the engine at pipeline start; `reset_registry()` is TESTING ONLY (autouse fixtures) and resets extensions with it.
- **Extension registries** (`extensions.py`): community grammars/rules registered explicitly before first `canonicalize()`; a contract opts a grammar in by naming it in `extra_grammars`; unknown names are silently skipped (deterministic no-op), and rules activate only when an opted-in id matches their `target_semantics`.
- **Exceptions:** new types subclass `PaxmanError`. `RecognitionError`/`ValidationError` carry `rule` (+ `original_error`, `None` for structural failures) and render as `"[rule] message"`.
- **Imports:** prefer `from paxman.core import ...` — `__init__.py` re-exports the domain vocabulary and registry functions.

### Kernel invariants (ADR-0009)
- `BoundarySpec` frozensets O(1) — word/anchor guards use `frozenset` membership.
- Normalizers two-array tuple `tuple[str, tuple[int,...]|None, tuple[int,...]|None]` — `starts`/`ends` parallel arrays.
- View `source_starts`/`source_ends` + `offsets` property — views carry source offset maps.
- `CountryNameFold` single-pass NFD with `_NFD_CACHE` — one-pass fold, cached.
- `validate_emit` at construction — span/raw_text invariants fail fast at emit.
- Matcher digests memoised — per-matcher digest cached.
- `PipelineGrammar` `matchers` delegation — `recognize()` delegates to `run_matchers()`.
- Common-word suppression 67 + 6 kinds (`regex`/`lexicon`/`scanner`/`combinator`/`candidates`/`label`, `Property` deleted) — `COMMON_WORDS` + `suppressible` + `suppress_common_words`.

## ANTI-PATTERNS (THIS PACKAGE)
- No import of `paxman.api` / `paxman.engine` / `paxman.capabilities` from here — breaks the import-linter leaf.
- No `slots=True` on contract dataclasses (root convention: contracts frozen, no slots).
- No weakening `Rule.__init_subclass__` into runtime defaults — missing metadata stays an import-time `TypeError`.
- No raising from `Rule.matches()`/`normalize()` internals; surface rule/grammar failures as `RecognitionError`/`ValidationError` from the engine, never as ad-hoc exceptions.
