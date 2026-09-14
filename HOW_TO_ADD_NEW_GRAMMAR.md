# How to Add a New Grammar to an Existing Capability

This guide walks you through making an existing Paxman capability smarter by teaching it to recognize a new representation. It is written for contributors who are new to the project and assumes no prior knowledge of the internal architecture.

Where [HOW_TO_ADD_NEW_CAPABILITY.md](HOW_TO_ADD_NEW_CAPABILITY.md) covers building a capability from scratch, this guide covers the smaller, more common task: **adding one recognition format to a shipped capability** (e.g., teaching the Date capability to recognize `YYYY/MM/DD`).

By the end of this guide, you will have added a grammar that changes real behavior — an input that previously resolved `MISSING` now resolves `SUCCESS` — with tests proving the difference.

> **Two ways to extend recognition.** If you are a Paxman contributor shipping the grammar *inside* the library, this guide is for you. If you are a downstream user who wants to extend a capability without touching the library, use the community seam instead: write the same `Grammar` subclass, register it with `paxman.register_grammar()` / `paxman.register_rule()`, and opt a contract into it via `extra_grammars`. See README's **Community Extensions** section for that path. The grammar class itself looks identical in both paths; only the wiring differs.

---

## Prerequisites

Before starting, understand these concepts (all defined in depth in HOW_TO_ADD_NEW_CAPABILITY.md):

- **Grammar** — a recognition unit that scans raw text and extracts span-bearing notations. Syntax only: it never validates, dedups, orders, or maps tokens to canonical values.
- **Rule** — a validation unit that checks a notation against an authoritative specification and produces the canonical value with provenance. Semantics.
- **Notation** — the intermediate token grammars produce and rules consume.
- **`active_grammars`** — the *optional* contract property naming which grammars run. A contract that does not implement it runs every shipped grammar returned by `get_grammars()`; only the gated capabilities (Email, IP, ISBN) implement it to name a subset.
- **`semantics`** — the grammar metadata declaring the *meaning* the grammar assigns to its recognized notations: an identity id by default, or a coalesced id shared with grammars that carry the same meaning (e.g. both the ISO and slash-ISO Date grammars declare `"iso8601_calendar_date"`).
- **`target_semantics`** — the rule metadata declaring which grammar semantics a rule validates. A recognition only routes to rules whose `target_semantics` includes its producing grammar's `semantics`.

**The one sentence that matters:** a new grammar changes behavior only when it is (1) returned by `get_grammars()`, and (2) its `semantics` is claimed by at least one rule via `target_semantics` — plus (3) named in `active_grammars`, but **only for the gated capabilities (Email, IP, ISBN) that implement it**. For all other capabilities, the contract has no `active_grammars` and the engine runs every shipped grammar, so `get_grammars()` alone activates the new grammar. Miss condition (1) or (3) and the grammar never runs — input matching only it stays `MISSING`. Miss condition (2) and the grammar still runs, but its recognitions route to no rules, so input matching only it becomes `INVALID` (recognized, no authority rule validates) instead of resolving — never a candidate. Either way the resolved output is unchanged, which is why a shipped grammar ships with a test that proves the difference (Step 5).

---

## Step 1: Choose the Representation and the Strategy

Before writing code, answer these questions:

1. **What new representation are you recognizing?** Write down examples of real human input, including edge cases (`2024/1/5`, not just `2024/01/01`).
2. **Does an existing notation already fit it?** If the representation decomposes into the same fields as an existing grammar (e.g., Date's `DateNotation(N1, N2, N3)`), reuse it. Only extend the notation when the new format genuinely carries different components.
3. **Does an existing rule already assign the same meaning?** If the new format means the same thing and normalizes the same way as an already-validated format (e.g., `2024/01/01` *is* ISO 8601's calendar date), declare that meaning's shipped `semantics` id on the new grammar and stop — no rule edit (Step 4, option A).
4. **Which recognition strategy fits the representation?**

Every grammar follows one of two core strategies (see HOW_TO_ADD_NEW_CAPABILITY.md Step 4 for the extended set):

| Your representation… | Strategy | Example |
|---|---|---|
| Has a distinctive syntactic shape (delimiters, fixed widths, character classes) | **Regex** — compile at module scope, iterate with `re.finditer()`, map groups to notation fields | `YYYY/MM/DD` dates, `IPv6` addresses, `ISBN-10` |
| Is a finite vocabulary of free-form tokens (names, spelled-out forms) | **Lexicon** — normalize input, test a key-only table under `grammar/data/`, emit the trimmed token | Country `name_recognition` |

The boundary is a hard rule: **grammars own syntax, rules own meaning**. A grammar never maps a token to a canonical value and never imports rule-layer authority data (enforced by the semantic purity gate). If your representation needs a synonym or a canonical mapping, the rule owns it.

---

## Step 2: Write the Grammar File (TDD: test first)

Test-first, as everywhere in this project: write the failing grammar tests before the grammar exists.

### 2a: Grammar tests (red)

Add a test class for your grammar to `tests/capabilities/<cap>/test_grammar.py`, following the existing test classes in that file:

```python
@pytest.mark.capability
class TestSlashISODateGrammar:
    """Tests for slash-ISO date grammar (YYYY/MM/DD)."""

    def test_recognizes_valid_input(self) -> None:
        grammar = SlashISODateGrammar()
        result = grammar.recognize("2026/07/26")
        assert len(result) == 1
        assert result[0].notation == DateNotation(N1="2026", N2="07", N3="26")

    def test_does_not_match_us_or_european_order(self) -> None:
        """A 2-digit-first slash date is not a slash-ISO date."""
        grammar = SlashISODateGrammar()
        assert grammar.recognize("07/26/2026") == []
        assert grammar.recognize("26/07/2026") == []

    def test_emits_spans(self) -> None:
        result = SlashISODateGrammar().recognize("x 2026/07/26 y")
        assert len(result) == 1
        assert result[0].start == 2
        assert result[0].end == 12
        assert result[0].raw_text == "2026/07/26"
        assert result[0].notation == DateNotation(N1="2026", N2="07", N3="26")

    def test_grammar_name(self) -> None:
        grammar = SlashISODateGrammar()
        assert grammar.name == "slash_iso_recognition"
```

Cover, at minimum: the happy path, the notation field mapping, variant input (different widths/separators), multiple matches, empty input, an incompatible format the grammar must *not* claim, and span correctness (`start`/`end`/`raw_text`).

### 2b: The grammar file (green)

Create `paxman/capabilities/<Cap>/grammar/<format>_recognition.py`:

1. Import `Grammar` and `RecognitionMatch` from `paxman.core.domain`, and the capability's notation.
2. Compile the regex once at module scope — never inside `recognize()` (it runs for every input).
3. Define a class extending `Grammar[Notation]` with a `name` of the form `{format}_recognition` (snake_case, unique within the capability) and a non-empty `semantics` string declaring the meaning its notations carry.
4. Implement `recognize(text) -> list[RecognitionMatch[Notation]]` — one `RecognitionMatch` per `finditer()` hit, carrying the notation, the half-open `[start, end)` span, and `raw_text`.

```python
"""Slash-ISO date grammar — recognizes YYYY/MM/DD format.

Notation mapping: N1=year, N2=month, N3=day
"""

from __future__ import annotations

import re

from paxman.capabilities.Date.notation import DateNotation
from paxman.core.domain import Grammar, RecognitionMatch

_SLASH_ISO_PATTERN = re.compile(r"(?<!\d)(\d{4})/(\d{1,2})/(\d{1,2})(?!\d)")


class SlashISODateGrammar(Grammar[DateNotation]):
    """Slash-delimited ISO date recognition: YYYY/MM/DD."""

    name = "slash_iso_recognition"
    semantics = "iso8601_calendar_date"  # same meaning as the dash ISO grammar (Step 4)

    def recognize(self, text: str) -> list[RecognitionMatch[DateNotation]]:
        """Extract YYYY/MM/DD date patterns from text."""
        return [
            RecognitionMatch(
                notation=DateNotation(N1=year, N2=month, N3=day),
                start=match.start(),
                end=match.end(),
                raw_text=match.group(0),
            )
            for match in _SLASH_ISO_PATTERN.finditer(text)
            for year, month, day in [match.groups()]
        ]
```

**The `recognize()` contract is enforced by the engine.** Every match must satisfy `0 <= start <= end <= len(text)` and `raw_text == text[start:end]`; a grammar returning a malformed match raises `RecognitionError` naming the grammar (see `_recognize` in `paxman/engine/orchestrator.py`). The engine owns within-grammar containment dedup and total recognition ordering — the grammar only extracts and emits spans.

**Guard boundaries against sibling grammars.** When two grammars could claim the same span, use lookarounds so each claims only its own representation. The slash-ISO pattern is naturally disjoint from the US/European grammars (a leading 4-digit year vs. a leading 1–2-digit month/day) — verify that with a negative test like `test_does_not_match_us_or_european_order`. Digit lookarounds (`(?<!\d)`/`(?!\d)`) additionally keep a date from being partially matched inside a longer digit run such as an ID (`12026/01/15` must not yield `2026/01/15`) — pin that with a negative test too.

---

## Step 3: Wire the Grammar into the Capability

A grammar must be returned by **`get_grammars()`** — and, only for the gated capabilities, named in **`active_grammars`** — or it silently never runs:

1. **`get_grammars()`** in `paxman/capabilities/<Cap>/capability.py` — supplies the grammar *instances* the engine can compose. This is the one wiring step every capability needs:

```python
def get_grammars(self) -> list[Grammar[DateNotation]]:
    return [
        ISO8601DateGrammar(),
        USDateGrammar(),
        EuropeanDateGrammar(),
        SlashISODateGrammar(),  # new
    ]
```

2. **`active_grammars`** in `paxman/capabilities/<Cap>/contract.py` — **only for the gated capabilities** (Email, IP, ISBN) that implement it to select grammars behind feature flags. For every other capability there is no `active_grammars` to update: the base contract returns `None` and the engine falls back to running every shipped grammar in `get_grammars()` order. **No contract edit is needed for those capabilities.**

If the capability does implement `active_grammars`, append the new name **at the end** of the list (gated behind its `include_*` flag if the capability has one):

```python
@property
def active_grammars(self) -> list[str]:
    grammars = ["standard_recognition"]
    if self.include_obfuscated:
        grammars.append("obfuscated_recognition")
    return grammars
```

Recognition order (and the same-span tiebreak) follows the runnable set — `get_grammars()` order for the all-active capabilities, the `active_grammars` list for the three gated ones — so appending at the end keeps every existing grammar's behavior identical (deterministic). Update the capability test asserting the grammar count (`test_get_grammars_returns_all`) and add one asserting the new name is wired.

> **The missing-half bug (gated capabilities only).** For Email, IP, and ISBN, the engine builds the runnable set from `contract.active_grammars`, not from `get_grammars()` — a grammar returned by `get_grammars()` but missing from `active_grammars` is dead code that will pass unit tests on the class and fail silently in the pipeline. The integration test in Step 5 is what catches this. The all-active capabilities have no such hole: the engine falls back to `get_grammars()` itself.

---

## Step 4: Make a Rule Validate It

A recognition only becomes a candidate when a rule's `target_semantics` includes the producing grammar's `semantics`. Whether you need to touch a rule at all depends on whether the new grammar's *meaning* is genuinely new. Two options:

### Option A — Reuse an existing rule's meaning (declare the shipped semantics id and stop)

When the new representation means the same thing and normalizes to the same canonical form as a format an existing rule already validates (the slash-ISO date *is* ISO 8601's calendar date), declare the *shipped* `semantics` id on the new grammar — and **stop**. No rule edit and no new rule: the existing rule's `target_semantics` already includes that id, so its `matches()` and `normalize()` — which already handle the notation — validate the new grammar's recognitions unchanged. This is the minimal change:

```python
class SlashISODateGrammar(Grammar[DateNotation]):
    """Slash-delimited ISO date recognition: YYYY/MM/DD."""

    name = "slash_iso_recognition"
    semantics = (
        "iso8601_calendar_date"  # the shipped id — same meaning as the dash ISO grammar
    )
```

Same-meaning grammars **share** a semantics id (a *coalesced* id). The shipped Date rule `Section431CalendarDate` already declares `target_semantics = frozenset({"iso8601_calendar_date"})`, so the slash-ISO grammar joins the ISO grammar under that one id and nothing in `rules/` changes.

### Option B — Add a new rule (new meaning, different normalization, or different authority)

When the new format means something genuinely new, give the grammar its own identity `semantics` id and add a rule file whose `target_semantics` names it — one file per publication, one class per spec section (see HOW_TO_ADD_NEW_CAPABILITY.md Step 5 for the full rule template). `Rule.__init_subclass__` enforces the six metadata attributes (`name`, `strategy`, `provenance`, `citation`, `target_semantics`, `requires_features`) at class-definition time, and `target_semantics` must be a non-empty `frozenset[str]`.

Whichever option you choose, the engine **fails fast** if you get it wrong: `_validate_affinity` raises `ContractError` when a rule's `target_semantics` names an id that no grammar claims in the composed set (shipped + opted-in community), so a dangling target can never silently disable a rule.

> **ADR-0012 note:** with Option B, a `PARSER`-only rule on LOOKUP-backed
> semantics yields disqualified ghosts — pair it with a `LOOKUP_TABLE` rule on
> the same grammar (see HOW_TO_ADD_NEW_CAPABILITY.md rule-strategy warning).

---

## Step 5: Prove It Makes a Difference (integration test)

The whole point of the grammar is observable behavior change. Write an integration test asserting the full pipeline resolves input that previously did not — this is the test that proves Steps 3 and 4 were both completed.

Add to `tests/integration/test_<cap>_capability.py` (which registers the capability and drives `paxman.canonicalize()`):

```python
def test_slash_iso_date_resolves(self) -> None:
    """YYYY/MM/DD input resolves via the slash-ISO grammar.

    Before this grammar shipped, "2024/01/01" was not recognized by any
    Date grammar (US/European require a leading month/day, ISO requires
    dashes) and resolved MISSING; the slash-ISO grammar makes it SUCCESS.
    """
    contract = Date.create_contract()
    result = paxman.canonicalize("2024/01/01", contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == "2024-01-01"
    assert result.candidates[0].recognition_rule == "slash_iso_recognition"


def test_slash_iso_invalid_month_invalid(self) -> None:
    """A slash-ISO shape with an impossible month is INVALID, not resolved."""
    contract = Date.create_contract()
    result = paxman.canonicalize("2024/13/01", contract)
    assert result.status == Resolution.INVALID


def test_slash_iso_does_not_disturb_us_ambiguity(self) -> None:
    """US/European slash formats still resolve exactly as before."""
    contract = Date.create_contract()
    result = paxman.canonicalize("07/26/2026", contract)
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == "2026-07-26"
```

Three assertions to always include:

- **Difference** — the new format now resolves (assert `recognition_rule` names your grammar, proving *your* grammar produced the candidate).
- **Semantics still hold** — impossible values under the new shape are `INVALID`, not resolved.
- **No regression** — sibling formats resolve exactly as before (your grammar claims only its own representation).

---

## Step 6: Update the Documentation

A shipped grammar is part of the capability's public surface. Update:

- **`README.md`** — the capabilities table's **Grammars** count for the capability (e.g., `3 (ISO, US, European)` → `4 (ISO, US, European, slash-ISO)`) and the capability section's format list and examples (regenerate via `uv run python tools/generate_readme_table.py`).
- **`CONTEXT.md`** — the "Capability Details" grammar table (delimiter, component mapping, notes) for the affected capability.
- **User guide** — `docs/user/capabilities/<cap>.md` Recognized-forms + Statuses rows for the new representation (plus the `capabilities/index.md` chooser link if the representation is a new row); citations/migration only when provenance or the output surface changes.

---

## Step 7: Quality Gates

Before merging, run the full pre-PR gate (all must pass):

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest
```

Project conventions that apply to new grammar code (violations fail review):

- **No type suppression** — no `# type: ignore` / `# noqa` / `# pyright: ignore` in source; fix the root cause.
- **No cross-capability imports** — a capability imports only from `paxman.core` (enforced by import-linter).
- **No rule-layer imports in grammars** — grammars never import from `rules/` or `rules/data/` (semantic purity gate).
- **Syntax only** — no validation, dedup, ordering, or token→canonical mapping in the grammar; rules own all of that.
- **Coverage ≥ 95%** per package — new grammar and wiring must be fully covered by the Step 2/5 tests.

---

## Worked Example: What This Guide Just Did

This guide's every snippet is drawn from a real change: the **slash-ISO date grammar** (`YYYY/MM/DD`) added to the Date capability. The complete change, in order:

| Step | File | Change |
|------|------|--------|
| 2a | `tests/capabilities/date/test_grammar.py` | `TestSlashISODateGrammar` (failing first) |
| 2b | `paxman/capabilities/Date/grammar/slash_iso_recognition.py` | New `SlashISODateGrammar` (`name = "slash_iso_recognition"`, `semantics = "iso8601_calendar_date"`) |
| 3 | `paxman/capabilities/Date/capability.py` | `SlashISODateGrammar()` appended to `get_grammars()` |
| 3 | `paxman/capabilities/Date/contract.py` | No change — Date is all-active; the engine runs every `get_grammars()` entry |
| 4 | `paxman/capabilities/Date/rules/iso_8601_ed2019.py` | No change — `Section431CalendarDate.target_semantics` already covers the shared `"iso8601_calendar_date"` semantics |
| 5 | `tests/capabilities/date/test_capability.py` | Grammar count 3 → 4; new name wired |
| 5 | `tests/integration/test_date_capability.py` | `"2024/01/01"` → `SUCCESS "2024-01-01"` (was `MISSING`) |
| 6 | `README.md`, `CONTEXT.md` | Counts, format list, grammar table row |

**Proof it works:** `paxman.canonicalize("2024/01/01", Date.create_contract())` now returns `SUCCESS` with canonical value `2024-01-01` and `recognition_rule == "slash_iso_recognition"`; before the change the same input resolved `MISSING`.
