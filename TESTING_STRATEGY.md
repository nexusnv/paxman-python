# Testing Strategy

Paxman's test suite exists to protect one core promise: given the same input, the same contract, and the same library snapshot (fixed library version, registry contents, and rule-data tables), the pipeline always yields the same canonical output. Every test, from the lowest-level unit check to the full end-to-end run, reinforces that determinism — achieved by construction through no world-knowledge, no clock, no environment-dependent ordering, no fuzzy logic, and no network inference across recognition, validation, and canonicalization. The suite is built on `pytest` and organized into five layers that mirror the architectural boundaries of the system itself.

---

## Why Testing Matters Here

Paxman resolves ambiguity by deferring to authoritative specifications. A bug in a grammar regex or a validation rule doesn't just produce wrong output. It produces wrong output *with a provenance trail*, making the error look authoritative. The testing strategy has to account for that. Each layer exists to catch a different class of mistake before it can masquerade as a correct answer.

---

## Test Layers

### Unit Tests

**Marker:** `@pytest.mark.unit`
**Location:** `tests/unit/`

Unit tests verify the structural contracts of individual domain objects in isolation. They answer questions like: Is `Provenance` actually immutable? Can two `Candidate` instances with the same fields be compared by value? Does the `Contract` protocol reject classes that are missing required members?

These tests use no real capabilities, no pipeline, no engine. They construct objects directly and assert their behavior. Where a capability or grammar is needed as input, the tests use lightweight stubs (e.g., `FakeContract`, `StubCapability`, `StubGrammar`) that exist only within the test file.

Key properties under test:
- **Immutability.** Every domain object (`Provenance`, `Candidate`, `RecognitionMatch`, `GrammarRule`, `VersionStamp`, `RecognizedRep`) raises `AttributeError` on attribute assignment. Tests confirm this explicitly.
- **Value equality.** Objects with identical fields compare as equal; objects with different fields do not.
- **Hashability.** Objects can be hashed, which makes them safe to use in sets and as dictionary keys.
- **Protocol compliance.** The `Contract` protocol is runtime-checkable. Tests verify that classes satisfying the structural interface pass `isinstance` checks, while incomplete classes do not.
- **ABC enforcement.** The `Capability` abstract class cannot be instantiated directly. Subclasses missing abstract methods (`get_grammars`, `get_rules`) also fail to instantiate.
- **Exception hierarchy.** All custom exceptions inherit from `PaxmanError`. `RecognitionError` and `ValidationError` preserve the original exception and the rule name that caused the failure.
- **Enum completeness.** `Resolution` and `RuleStrategy` have exactly the expected members with the expected string values.

Unit tests also exercise `hypothesis` for property-based testing of domain objects, configured via the `tests/conftest.py` profile with `max_examples=100` and the `too_slow` health check suppressed.

### Capability Tests

**Marker:** `@pytest.mark.capability`
**Location:** `tests/capabilities/<CapabilityName>/`

Capability tests verify that a specific domain module's grammars, rules, and notation type work correctly on their own. They don't run the full pipeline. They instantiate grammars and rules directly, feed them known inputs, and check the outputs.

For the Email capability, this means three classes of tests:

**Grammar tests** confirm that each recognition grammar finds exactly the patterns it should and ignores everything else. `StandardEmailGrammar` picks up `user@example.com` but ignores `user at example dot com`. `ObfuscatedEmailGrammar` does the opposite. `LocalhostEmailGrammar` catches `admin@localhost` but not standard domain emails. Tests also verify that grammars return an empty list for empty input and non-matching text.

**Rule tests** confirm that each validation rule's `matches()` method accepts valid notation and rejects invalid notation. They verify that `normalize()` produces the expected canonical string. They check that rule metadata (name, strategy, provenance attributes, citation) is set correctly. For example, `Section341AddrSpec` lowercases the email during normalization, while `Section63localhost` preserves case.

**Capability tests** verify that the capability class itself satisfies the `Capability` ABC, that it returns the correct number and type of grammars and rules from `get_grammars()` and `get_rules()`, and that its notation type (`EmailNotation`) is an immutable, equality-comparable, hashable frozen dataclass with one `str` field per component.

### Integration Tests

**Marker:** `@pytest.mark.integration`
**Location:** `tests/integration/`

Integration tests run the full engine pipeline (`run_capability`) with a real capability registered. They exercise the complete flow: registry setup, grammar recognition, rule filtering, candidate production, status determination, and version stamp computation.

Every integration test uses an autouse `reset_registry` fixture that clears and un-freezes the capability registry before and after each test. This isolation prevents cross-test pollution from the module-level registry state.

Key scenarios:

- **Success path.** Standard email input produces `Resolution.SUCCESS` with the expected canonical value.
- **Obfuscated recognition.** Enabling `include_obfuscated=True` in the contract activates the obfuscated grammar, which then recognizes natural-language email representations.
- **Localhost recognition.** `admin@localhost` resolves through the localhost grammar and RFC 6761 validation.
- **Missing input.** Text with no email patterns produces `Resolution.MISSING` with zero candidates.
- **Version stamp presence.** Every successful result carries a `VersionStamp` recording the library version.
- **Candidate-multiset determinism.** Running the same input through the same contract twice produces the same candidate multiset and identical canonical values. This directly tests the system's core determinism invariant.
- **Provenance authority.** Each resolved value's candidates carry provenance citations; integration tests assert the authoritative specification behind a resolution (e.g. RFC 5322 for email), and that a recognized-but-unvalidated input stays `INVALID` rather than resolving without authority.
- **Ambiguity detection.** Two different emails in one input produce `Resolution.AMBIGUOUS` with `canonicalized_value` set to `None`, even though each individual email resolves cleanly.
- **Temporal filtering.** Setting `year=2007` excludes RFC 5322 (published 2008) and RFC 6761 (published 2012), producing `Resolution.INVALID` for input that would otherwise resolve. Setting `year=2010` includes RFC 5322 but excludes RFC 6761, narrowing the set of valid candidates.

### Property Tests

**Marker:** `@pytest.mark.property`
**Location:** `tests/property/`

Property tests use `hypothesis` to lock invariants across generated inputs:
grammar-stage parity, re-entry fixed points (`test_reentry_invariant.py` ROWS —
every capability extends this suite per ADR-0010), output-format preservation
(`test_output_format_preservation.py` CLASS_MAP — every offered format per
ADR-0011), and per-capability robustness suites (e.g. Timezone/UtcOffset).
Eleven suites touch the registry — all full-pipeline with an isolated
single-capability registry: `test_money_properties`, `test_reentry_invariant`,
`test_coordinates_quantization`, `test_output_format_preservation`,
`test_timezone_properties`, `test_issn_properties`, `test_orcid_property`, and
`test_coordinates_properties` (local `_fresh_registry` autouse fixture);
`test_element_properties` (mixed — direct grammar/rule key tests plus
full-pipeline self-canonicalization under `_fresh_registry`);
`test_mac_address_properties` (local `_clean_registry` autouse fixture); and
`test_language_property` (manual `reset_registry()` in try/finally per test).
The rest drive grammars/rules/`format_value` directly and never touch the
registry.

### End-to-End Tests

**Marker:** `@pytest.mark.e2e`
**Location:** `tests/e2e/`

End-to-end tests exercise the public `canonicalize()` API from `paxman.api`. They're the closest thing to a user's perspective. Where integration tests call the engine directly, e2e tests go through the same entry point that a consumer of the library would use.

These tests verify:
- Standard, obfuscated, and localhost email canonicalization through the public API.
- `MISSING` status when input contains no recognizable patterns.
- `CapabilityError` when the contract references an unknown capability name.

The e2e tests also use the autouse registry reset fixture, keeping each test fully isolated.

---

## Shared Infrastructure

### Registry Reset

The capability registry is module-level state. Without cleanup, a test that registers a capability would affect every subsequent test. The `_clean_registry` autouse fixture (found in both `tests/integration/` and `tests/e2e/`) calls `reset_registry()` before and after each test, guaranteeing a fresh registry. This is essential for deterministic test outcomes.

### Hypothesis Profile

The `tests/conftest.py` file registers a `ci` profile for `hypothesis` that limits examples to 100 per property test, disables the `too_slow` health check, and removes the deadline. This keeps property-based tests fast enough for CI while still exercising meaningful coverage of domain object contracts.

### Test Doubles

Tests use localized stubs and fakes rather than shared fixture libraries. Each test file defines exactly the doubles it needs: `FakeContract` in unit tests, `StubCapability` in discovery tests, `StubGrammar` and `StubRule` in capability tests. This keeps test dependencies explicit and prevents hidden coupling between test files.

---

## Running the Tests

```bash
# All tests
uv run pytest

# By layer
uv run pytest -m unit
uv run pytest -m capability
uv run pytest -m integration
uv run pytest -m property
uv run pytest -m e2e

# With coverage
uv run pytest --cov=paxman --cov-report=term-missing
```

---

## Design Principles

**Tests mirror architecture.** The five test layers correspond to the structural layers of the system. Unit tests cover the core domain. Capability tests cover capability implementations. Integration tests cover the engine. Property tests lock cross-cutting invariants. E2e tests cover the public API.

**Determinism is testable.** The determinism test in `test_pipeline.py` runs the same input through the same contract twice and asserts an identical candidate multiset and identical canonical values. This is the most important single test in the suite, because it proves the system keeps its central promise.

**Isolation is mandatory.** Every layer that touches shared state (the registry) uses fixtures to reset it. Tests never depend on execution order.

**Provenance is verified, not just present.** Capability tests check that rules carry the correct authority, specification name, publication year, and lifecycle status. This ensures that the provenance trail isn't just there, it's accurate.

**Negative cases matter as much as positive ones.** The suite tests for `MISSING`, `INVALID`, and `AMBIGUOUS` outcomes, not just `SUCCESS`. It verifies that protocols reject non-compliant classes, that registries reject duplicate registrations, and that grammars ignore non-matching input.
