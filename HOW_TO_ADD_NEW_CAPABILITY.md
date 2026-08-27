# How to Add a New Capability

This guide walks you through adding a new domain capability to Paxman. It is written for developers who are new to the project and assumes no prior knowledge of the internal architecture.

By the end of this guide, you will have a fully functional capability with grammars, validation rules, a contract, tests, and integration with the Paxman engine.

---

## Prerequisites

Before starting, understand these concepts:

- **Capability** — a self-contained domain module (like Email) that knows how to recognize and validate values in that domain
- **Grammar** — a recognition rule that scans raw text and extracts structured patterns
- **Validation Rule** — a semantic rule that checks extracted patterns against authoritative specifications
- **Notation** — the intermediate representation that grammars produce and rules consume
- **Contract** — a user-facing configuration object that controls which grammars and rules are active
- **Provenance** — a citation of the authoritative specification that validates a value

---

## Step 0 — Generate the skeleton

Before hand-writing anything, generate the full capability skeleton with the
scaffolder. It emits every file the pipeline requires — package modules, one
placeholder grammar + rule with full enforced metadata, test stubs, and the
`paxman/capabilities/__init__.py` wiring — so your job becomes "fill in the
domain", not "assemble the unanimous surface from prose".

Run it from the repo root:

```bash
uv run python tools/new_capability.py <PackageName> --name <snake> \
    --authority <str> --spec-name <str> --spec-url <str> \
    --publication-year <int> \
    [--spec-version <str>] [--default-format <str>]
```

This creates 13 files plus one edit:

- `paxman/capabilities/<PackageName>/__init__.py`
- `paxman/capabilities/<PackageName>/notation.py`
- `paxman/capabilities/<PackageName>/contract.py`
- `paxman/capabilities/<PackageName>/capability.py`
- `paxman/capabilities/<PackageName>/grammar/__init__.py`
- `paxman/capabilities/<PackageName>/grammar/<name>_recognition.py`
- `paxman/capabilities/<PackageName>/rules/__init__.py`
- `paxman/capabilities/<PackageName>/rules/<authority_snake>_ed<year>.py`
- `tests/capabilities/<name>/__init__.py`
- `tests/capabilities/<name>/test_notation.py`
- `tests/capabilities/<name>/test_grammar.py`
- `tests/capabilities/<name>/test_rules.py`
- `tests/capabilities/<name>/test_capability.py`
- *edit* `paxman/capabilities/__init__.py` — adds the import line and `__all__` entry (alphabetically).

After generating, the tool prints a checklist of what only a human can do:

1. Replace the placeholder grammar pattern with a real recognizer.
2. Rename `Section 1-overview` and implement `matches()`/`normalize()`.
3. Shape the notation beyond the placeholder `value` field.
4. Add `grammar/data/` and `rules/data/` when authority tables arrive.
5. Register in your entry point; sweep README/CONTEXT/AGENTS docs.
6. Delete or extend the placeholder grammar/rule as needed.

The generated code already satisfies every import-time enforcement and passes
its own test stubs, so you start from a green skeleton.

---

## Step 1: Plan Your Capability

Before writing code, answer these questions:

1. **What domain are you canonicalizing?** (e.g., phone numbers, URLs, postal codes)
2. **What authoritative specifications govern this domain?** (e.g., RFCs, ISO standards, government registries)
3. **What are the different ways users might write this value?** (e.g., "555-1234", "+1 555 1234", "(555) 123-4567")
4. **What is the canonical output format?** (e.g., E.164 for phone numbers)
5. **What is the intermediate representation?** (e.g., country code, area code, local number)

Document your answers. You will reference them when writing grammars and rules.

---

## Step 2: Create the Directory Structure

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

Create the following directory structure. Replace `YourDomain` with your capability name (use PascalCase):

```
paxman/capabilities/YourDomain/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── your_grammar.py
└── rules/
    ├── __init__.py
    └── your_rule.py
```

Also create the test directory:

```
tests/capabilities/yourdomain/
├── __init__.py
├── test_grammar.py
├── test_rules.py
└── test_capability.py
```

Use lowercase for the test directory name.

### Optional: `rules/data/` subdirectory

If your capability uses large lookup tables (e.g., country codes, status code mappings), create a `rules/data/` subdirectory to keep data files separate from rule logic:

```
rules/
├── __init__.py
├── your_rule.py
└── data/
    ├── __init__.py
    └── lookup_table.py
```

Data files contain only module-level dictionaries and sets — no classes or functions. Rule files import from data files:

```python
# rules/your_rule.py
from paxman.capabilities.YourDomain.rules.data.lookup_table import VALID_CODES


class SectionYourRule(Rule[YourDomainNotation]):
    TABLE = VALID_CODES
```

This pattern keeps rule logic readable and data maintainable. Use it when your lookup table exceeds ~20 entries.

---

## Step 3: Define the Notation

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

The Notation is your domain's intermediate representation. It is a frozen dataclass with named fields that represent the components of the value you are canonicalizing.

Create `paxman/capabilities/YourDomain/notation.py`:

1. Import `dataclass` from `dataclasses`
2. Define a frozen dataclass with `@dataclass(frozen=True)` and one field per component of your notation

The engine passes typed notation objects to rules, not lists. Rules access fields by name (e.g., `notation.field_name`).

**Rules for Notation:**

- Every field must be a `str` type
- The dataclass must be frozen (immutable)
- Rules access notation fields by name (e.g., `notation.field_name`), not by list position

**Example patterns:**

- Email: `local_part` + `domain_part` (2 fields)
- Phone number: `country_code` + `area_code` + `local_number` (3 fields)
- IP address: `address` (1 field) — when the value is atomic
- Country: `shape` + `value` (2 fields) — discriminator pattern where `shape` tells rules which format `value` contains (e.g., `"alpha2"`, `"alpha3"`, `"numeric"`, `"name"`)

**Optional: `slots=True`**

You can add `slots=True` to your frozen dataclass for memory efficiency:

```python
@dataclass(frozen=True, slots=True)
class YourDomainNotation:
    field_one: str
    field_two: str
```

This is optional. Use it when your notation will be instantiated many times (e.g., processing bulk input).

---

## Step 4: Create a Grammar

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

Grammars are recognition rules that scan raw text and extract span-bearing notations. Each grammar handles one specific pattern or format.

Create `paxman/capabilities/YourDomain/grammar/your_grammar.py`:

1. Import `Grammar` and `RecognitionMatch` from `paxman.core.domain`
2. Import your `YourDomainNotation` from the notation module
3. Define a class that extends `Grammar`
4. Set the `name` class attribute to a snake_case identifier (this name is used by the contract to toggle grammars)
5. Implement the `recognize(text: str) -> list[RecognitionMatch[YourDomainNotation]]` method

**The `recognize` method must:**

- Accept a single string parameter (the raw input text)
- Return a list of `RecognitionMatch` objects — NOT bare notations. Every match carries the notation plus a half-open `[start, end)` span and the matched `raw_text`, so `len(raw_text) == end - start` always holds
- Return an empty list if nothing matches
- Never raise exceptions for normal input (use try/except for regex or parsing errors)
- Handle edge cases gracefully (empty strings, partial matches, Unicode)

Example:

```python
import re

from paxman.core.domain import Grammar, RecognitionMatch
from paxman.capabilities.MyDomain.notation import MyDomainNotation

# Compile reusable regexes once at module scope — never per call inside
# recognize() (runs for every input).
_PATTERN = re.compile(r"...")  # your pattern


class StandardMyDomainGrammar(Grammar[MyDomainNotation]):
    """Standard recognition for the MyDomain capability."""

    name = "standard_recognition"
    semantics = "standard_recognition"

    def recognize(self, text: str) -> list[RecognitionMatch[MyDomainNotation]]:
        """Extract span-bearing matches from raw text.

        The engine dedups contained matches and orders recognitions; the
        grammar only extracts and emits spans.
        """
        matches = []
        for match in _PATTERN.finditer(text):
            matches.append(
                RecognitionMatch(
                    notation=MyDomainNotation(...),  # parsed from groups
                    start=match.start(),
                    end=match.end(),
                    raw_text=match.group(0),
                )
            )
        return matches
```

**Grammar design principles:**

- Each grammar should handle one logical format (e.g., "obfuscated email", "IPv6 address")
- The grammar does syntax only — extraction and separator/case normalization. It does NOT de-duplicate, sort, or validate: the engine owns within-grammar containment dedup ("longer wins", with identical `[start, end)` spans keeping the first-emitted match) and the total recognition order, and rules own meaning
- A single grammar can return multiple matches if the input contains multiple occurrences
- Grammar names must be unique within the capability
- Never import from `rules/` — a grammar that imports a rule would let semantics leak across the pipeline's separation boundary (enforced by the semantic purity gate)
- Cross-grammar containment is expected and resolves through normalization: an ISBN-10 sub-run inside an ISBN-13 match is a contained span, and both shapes normalize to the same canonical value, so the resolution succeeds rather than ambiguating

**Choose a recognition strategy before writing the grammar.** Every grammar in the codebase follows one of two strategies, and the choice follows directly from the representation you are recognizing. Decide this in Step 1, alongside your notation design — it determines whether you write a pattern or a key set.

**Strategy 1 — Regex (structural pattern matching)**

Recognize by syntactic *shape*: fixed widths, delimiters, or character classes. Compile the pattern at module scope, iterate with `re.finditer()`, map capture groups to notation fields, and sanitize the raw token (strip separators, case-fold, length-guard) before storing it in the notation. Recognition is shape-only — rules own semantic validity.

Choose Regex when the representation has a distinctive, enumerable shape. All Email, IP, ISBN, and many Phone/Country grammars are Regex; Date is CandidatesMatcher; Language/URL/Phone E.164 are ScannerMatcher; SIUnit uses Lexicon+Combinator. Three recurring sub-patterns:

- **Compile once, iterate with `finditer()`** — never compile inside `recognize()` (it runs for every input).
- **Sanitize the matched token** — the notation value is a *cleaned* raw token, never a canonical value. Phone strips separators (a local `strip_separators` in each Phone grammar), Country uppercases, ISBN strips separators and guards length. `raw_text` is always the original span, so `len(raw_text) == end - start` keeps holding.
- **Guard boundaries against sibling grammars** — when two grammars could claim the same span, use lookbehind/lookahead so each claims only its own representation. See Phone's `national_recognition` (four stacked lookbehinds rejecting `+1…` and `tel:+…` prefixes) and `e164_recognition` (a `(?<![\w:.])` lookbehind rejecting email plus-tags and `tel:+…`).

**Strategy 2 — Lexicon (key-set membership)**

Recognize by membership in a known vocabulary, not by shape. Normalize the input (case-fold, Unicode decomposition, separator folding), test membership in a key-only table under `grammar/data/`, and emit the trimmed input token as the notation value (with a `shape` discriminator when rules route by format). Keys are syntax-normalized forms only — no token maps to a canonical value; rules own every token-to-meaning decision.

Choose Lexicon when the representation is free-form text whose recognizability *is* the vocabulary — no regex shape separates "United States" from "XYZ". Country's `name_recognition` is the exemplar: it normalizes with `normalize_name()` (in `Country/notation.py`) for lookup-key membership against `_KNOWN_NAME_KEYS` (the union of per-locale key sets in `grammar/data/`), but emits the original trimmed token (`raw_text` and `notation.value` preserve the input case, not the normalized key) with `shape="name"`. Phone's `strip_separators` (in `paxman/capabilities/Phone/grammar/_common.py`) and ISBN's digit extraction follow the same ownership model: syntax-only cleaning lives in the grammar layer, semantic mapping in rules. See its `grammar/data/` modules for the key-only table pattern.

**Decision guidance:**

| Your representation… | Strategy |
|---|---|
| Has a distinctive syntactic shape (delimiters, fixed widths, character classes) | **Regex** |
| Is a finite vocabulary of free-form tokens (names, spelled-out forms) | **Lexicon** |
| Both (e.g., codes *and* names) | One grammar per strategy |

The strategies are not interchangeable: a regex shape cannot enumerate a vocabulary, and a key set cannot recognize an open-ended shape. A capability commonly mixes them — Country ships three Regex grammars and one Lexicon grammar.

**Shipped Recognition Kernel kinds (ADR-0009, post Part B)**

The two strategies above are the user-facing chooser, the kernel implements them as six declarative matcher kinds with landed customers. Pick the kind that matches your representation, then declare it as a `MatcherSpec`. Every kind shares the same substrate, anchor prefilter, and assembly policy (see ADR-0009 §9).

| Kind | Matcher class | Recognizes by | Landed customers |
|---|---|---|---|
| **regex** | `RegexMatcher` | Bounded shape — character classes, repetitions, delimiters; `re.compile(...).finditer(view)` with offset-translated emit | BIC core, IP v4, Email `standard_recognition`, ISBN/ISSN cores; Date candidates shadow RegexStage until parity (kind declared, legacy path still shipped) |
| **lexicon** | `LexiconMatcher` | Vocabulary — normalized key membership on a view; `≤ ~500` tokens → regex alternation, `> ~500` → word-anchored dict trie (parity-tested, byte-identical) | Country `name_recognition` (~600 union keys), SIUnit `symbol` (820) / `name` (650), Currency `symbol`/`word` (67/80, alt tier) |
| **scanner** | `ScannerMatcher` | Character state machine — `(context, pos) → (end, Notation)` with `max_window` bounds and `SeparatorFold` view (`_`→`-`); non-overlapping advance | Language BCP-47 subtag walk (`bcp47_tag_recognition` — deletes 160-line `_BCP47RegexStage`), URL paren-balance + bare-scheme drop, Phone E.164 15-digit window |
| **combinator** | `CombinatorMatcher` | Compositional shapes — minimal expr tree `seq`/`alt`/`opt`/`rep` with span capture, ordered `alt` | SIUnit `split_word_prefix` (`kilo gram` → `kg`) and `compound` (`UNIT(SEP UNIT){1,3}`) — first combinator customer (ADR §9.4) |
| **candidates** | `CandidatesMatcher` | Enumerated strict formats — `tuple[MatcherSpec]` sharing one grammar, `first`/`all` strategy, per-candidate `target_semantics` preserved for ambiguity | Date 4→1 (`DateGrammar` — iso8601/us/european/slash_iso as candidates; `all` keeps US vs European `01/02/2026` AMBIGUOUS) |
| **label** | `LabelMatcher` | Optional label + value fusion — `labels: frozenset[str]`, `separator`, `glued_policy="reject"` (`[\s:-]+`) vs `"allow"` (`[\s:-]*`) | ISSN (`ISSN` label, `[\s:-]*` glued `ISSN03178471` allowed) and IBAN (`IBAN` label, `[\s:-]+` glued `IBANDE89…` → MISSING) — BIC/ORCID/ISBN are next label customers |

The `property` kind (open Unicode classes via generated sorted ranges, `bisect` per ADR §9.5) is declared but not yet a shipped customer; `ScannerMatcher` covers length-changing views (`SeparatorFold`) until the first length-changing normalizer needs a general offset map (URL IDNA, ADR D3).

**Deferred patterns (not kernel kinds)**

The `Grammar` contract — scan free text, emit span-bearing `RecognitionMatch` objects, never validate — can also host other techniques, but they are not matcher kinds and stay out of the kernel unless a capability's spec forces them. They are noted here so a contributor does not force a representation into regex:

| Strategy | Recognizes by | Producing spans | Example in the wild | Reach for it when |
|---|---|---|---|---|
| **Parser generator** (lark) | An EBNF grammar compiled to a parser | `Lark.scan()` yields `ScanMatch(range=(start, end), value)` — LALR only, silently skips non-matches, O(n·m) worst case; tree nodes carry `start_pos`/`end_pos` with `propagate_positions` | lark's own recipe scans prose for dates; `examples/advanced/scan_json.py` extracts JSON from log lines | Truly recursive or ambiguous-by-design syntax; heavier conceptual model, zero runtime dependencies |
| **Unicode-property matching** | Open character classes: any currency symbol (`\p{Sc}`), any Han letter (`\p{Script=Han}`) | stdlib `re` has no `\p{…}` (a long-open CPython request) — use the third-party `regex` module, or generate character-range tables at build time exactly like `tools/regenerate_isbn_range_data.py` | CleverCSV (`\p{Sc}` for currency); python-textile (falls back to hand-rolled ranges); TensorFlow Text (`\p{Sm}`, `\P{L}`) | A Unicode property defines the class; but keep curated vocabularies on Lexicon — `\p{Emoji}` is too broad for "is an emoji", so the `emoji` library uses key-set tables instead |
| **Multi-key automaton** (Aho–Corasick) | Many literal keys in a single pass — a prefilter when regex alternation over a large vocabulary degenerates | Match positions come straight from the automaton | `pyahocorasick`; eyecite prefilters legal-citation text; Zulip alert words | A large literal vocabulary (units, codes, stopwords) where `(key1|key2|…)` becomes slow or unwieldy |

### The Grammar/Rule Boundary (hard rule)

Grammars recognize *representations*; rules assign *meaning*. Keep the two layers apart:

- **Grammars may normalize syntax and use key-only recognition tables.** Case folding, Unicode decomposition, punctuation removal, and whitespace collapsing are not semantic decisions. A grammar lookup table may contain *keys only* — the raw spellings the grammar recognizes — with no token mapped to a canonical value.
- **Grammars must not map tokens to canonical values or import provenance-backed semantic tables.** A grammar must never return a canonical country, code, or name in place of the recognized input token, and it must not import the rule layer's authority data. If a representation needs a synonym, the rule owns it.
- **Rules validate notation, assign meaning, normalize the default canonical form, and carry provenance.** Validation rules hold the authority-backed tables (e.g., ISO 3166-1 for official names and synonyms, ISO 3166-3 for former names, CLDR for localized names) and produce the candidate with that provenance.
- **Recognition and authority data may evolve separately.** Keep grammar recognition keys and rule lookup tables in separate files, and add a consistency test that asserts every shipped recognition key is covered by at least one rule-data mapping. That test is what lets the two catalogs drift independently without breaking shipped behavior.

---

## Step 5: Create Validation Rules

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

Validation rules check notations against authoritative specifications. Each rule belongs to one specific publication (e.g., one RFC, one ISO standard).

Create `paxman/capabilities/YourDomain/rules/your_rule.py`:

### 5a: Define the Provenance

At the top of the file, define a module-level `PUBLICATION` constant. This is the provenance for all rules in this file:

- `authority` — the organization that published the spec (e.g., "IETF", "ISO", "W3C")
- `specification_name` — the name and section of the spec (e.g., "RFC 5322 Section 3.4.1")
- `kind` — one of "specification", "registry", or "policy"
- `reference_url` — a URL to the authoritative document
- `version` — the version string (e.g., "2008") or `None` if unversioned
- `lifecycle` — one of "active", "deprecated", or "superseded"
- `publication_year` — the year this specification came into effect (integer)

### 5b: Define the Rule Class

Create a class that extends `Rule`:

1. Set `name` to an identifier following the pattern `Section X.Y.Z-description` (e.g., `Section 3.4.1-addr-spec`)
2. Set `strategy` to the appropriate `RuleStrategy` enum value:
   - `REGEX` — for pattern matching rules
   - `LOOKUP_TABLE` — for table-based validation (e.g., status codes, country codes)
   - `PARSER` — for rules that parse and validate structured input

**Match the rule strategy to your grammar strategy.** The grammar decides how input becomes a notation; the rule strategy decides how the notation becomes meaning:

| Grammar strategy (Step 4) | Natural rule strategies | Why |
|---|---|---|
| Regex (shape) | `REGEX` (validate the exact shape), `LOOKUP_TABLE` (validate the extracted token against authority data), or `PARSER` (validate structure the regex left loose — check digits, octet ranges, lengths) | The grammar extracts cheaply; rules own the strict, authoritative check |
| Lexicon (vocabulary) | `LOOKUP_TABLE` | The rule maps the recognized token to its canonical value with provenance — the grammar's key set must never do that |

Codebase examples: IP's IPv4 grammar is a loose regex (`\d{1,3}` octets) and `rfc_791_ed1981` is a `PARSER` rule enforcing the 0–255 range; ISBN's grammars strip separators and `iso_2108_ed2017` is a `PARSER` rule computing the check digit; Country's `name_recognition` (Lexicon) feeds the `LOOKUP_TABLE` ISO 3166 and CLDR rules that own token→country meaning.

3. Set `provenance` to the `PUBLICATION` constant defined above
4. Set `citation` to a human-readable citation (e.g., "Section 3.4.1 (addr-spec)")
5. Set `target_semantics` to the `frozenset[str]` of grammar semantics whose notations this rule validates (e.g., `frozenset({"standard_recognition"})`)
6. Set `requires_features` to the `frozenset[str]` of contract fields that must be truthy for the rule to run (`frozenset()` when it always runs)

All six attributes are enforced by `Rule.__init_subclass__` at class-definition time; see the Rule metadata section in Step 7.

### 5c: Implement the `matches` method

The `matches` method checks whether a notation is valid according to this rule:

```python
def matches(self, notation: YourDomainNotation, contract: Contract) -> bool:
```

- Accept a typed notation and the contract
- Return `True` if the notation is valid according to the specification
- Return `False` if it is not valid
- Never raise exceptions — return `False` for any invalid input
- Access notation fields by name (e.g., `notation.field_name`)

**For regex rules:** Compile the regex once at module level, then use it in `matches`.

**For lookup table rules:** Define a module-level dictionary mapping valid values to canonical forms.

**For parser rules:** Attempt to parse the notation and return `True` if parsing succeeds without errors.

### 5d: Implement the `normalize` method

The `normalize` method converts a valid notation into its capability's default canonical string form:

```python
def normalize(self, notation: YourDomainNotation, contract: Contract) -> str:
```

- Accept a typed notation and the contract
- Return the default canonical string representation
- Only called after `matches` returns `True` (you can assume the notation is valid)
- Apply normalization rules from the specification (e.g., lowercase, remove whitespace, pad with zeros)
- **Never read `contract.output_format`.** Presentation is the capability's job, not the rule's. `normalize()` always returns the default canonical form, and the engine applies `Capability.format_value()` afterward. A CI source scan rejects any `output_format` token in rule modules (see the presentational-only invariant below).

### Accessing Capability-Specific Contract Fields

Your rules receive the base `Contract` protocol type. To access capability-specific fields that carry parameters, like `two_digit_base_year` or `default_country`, use `typing.cast`:

```python
from typing import cast
from paxman.capabilities.YourDomain.contract import YourDomainContract


class SectionYourRule(Rule[YourDomainNotation]):
    def normalize(self, notation: YourDomainNotation, contract: Contract) -> str:
        typed_contract = cast(YourDomainContract, contract)
        base_year = typed_contract.two_digit_base_year
        # ... use base_year in normalization logic
```

**Why cast?** The engine passes `Contract` (the protocol type) to rules. Your rules know they'll only be called with your capability's contract, so the cast is safe. The alternative — checking `isinstance` — adds unnecessary runtime overhead.

**When to use:** When your rule needs a capability-specific parameter, such as `two_digit_base_year` (Date) or `default_country` (Phone). Parameters that affect validity may be read in `matches()` or `normalize()`. Standard fields (`year`, `pinned_rules`) are available on the base protocol; `output_format` is a presentation parameter consumed by `Capability.format_value()`, never by rules.

**When not to use:** Never cast to read feature-toggle flags (`include_*`) for gating. Feature routing is the engine's job: declare the dependency in `Rule.requires_features`, and the engine drops the rule when the flag is false. `matches()` must never consult `include_*` flags or `output_format`; validity comes from the notation, the specification, and legitimate validity-affecting parameters.

---

## Step 6: Create the Capability Class

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

The Capability class is the entry point that the engine uses to discover your grammars and rules.

Create `paxman/capabilities/YourDomain/capability.py`:

1. Import `Capability` from `paxman.core.capability`
2. Import your grammars and rules
3. Define a class that extends `Capability`
 4. Set `name` to a lowercase identifier (e.g., "yourdomain") — this is the name users pass to the contract
 5. Implement `get_grammars()` — return a list of grammar instances
 6. Implement `get_rules()` — return a list of rule instances
 7. Define a `create_contract()` static method that returns a default contract
 8. Implement `format_value(value, output_format, notation)` — the single presentation seam. The engine calls it immediately after `Rule.normalize()` and before candidate deduplication and status determination. Return the value unchanged for the default format; only an explicitly offered alternative triggers conversion (e.g., Date `"US"` rendering, Country `alpha3`/`numeric`/`name` conversion, Phone RFC 3966/national rendering). A capability with no alternative formats (e.g., Email, IP) inherits the identity implementation from `Capability` and does not override it. Rules never implement presentation — see Step 5d and the presentational-only invariant in Step 7.

---

## Step 7: Create the Contract Class

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

The Contract is a user-facing configuration object that controls which grammars and rules are active.

### Unanimous contract & rule surface

Every contract and rule in the codebase follows the same structural rules. The `CapabilityContract` base class makes this unanimous surface structural rather than documentary: the pieces below are implemented once, in the base class, and your capability inherits them. Read this before writing your contract.

**1. Every contract MUST inherit `CapabilityContract`**

Subclass `CapabilityContract` (never `Contract` directly). `Contract` is engine-internal since ADR-0007.

Import it from `paxman.core.contract` (defined in `paxman/core/capability_contract.py`). Your contract is a frozen dataclass subclass:

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class YourDomainContract(CapabilityContract):
    """User-facing contract for YourDomain capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "iso"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"us"})

    capability_name: str = field(default="yourdomain", init=False)
    include_extended: bool = False  # toggles extended_recognition grammar

    @property
    def active_grammars(self) -> list[str]:
        grammars = ["standard_recognition"]
        if self.include_extended:
            grammars.append("extended_recognition")
        return grammars
```

Concretely, a `CapabilityContract` subclass:

- Overrides `DEFAULT_OUTPUT_FORMAT` (a concrete string) and `OFFERED_OUTPUT_FORMATS` (a `frozenset[str]` of *alternative* formats) as class variables. The default format is **not** included in `OFFERED_OUTPUT_FORMATS`.
- Sets `capability_name` via `field(default="<name>", init=False)`.
- Declares `output_format` nowhere — the base field `output_format: str | None = None` is inherited. It is **never** a non-optional `str`. The base `__post_init__` resolves `None`, `"default"`, and the default format string to the concrete default, validates offered alternatives, and raises `ContractError` for anything else.
- Implements `active_grammars` **only when recognition is feature-gated** (the Email/IP/ISBN pattern). Otherwise the property is omitted entirely: the base returns `None` and the engine runs every shipped grammar in `get_grammars()` order.
- Adds its own `__post_init__` validation by calling `super().__post_init__()` first. Use `@dataclass(frozen=True)` exactly like the base — do NOT add `slots=True` (incompatible with the base's `super()` pattern).

`CapabilityContract` satisfies the `Contract` protocol structurally, so your subclass does too.

**2. `create_contract()` signature**

The static `create_contract()` on your capability class must open with the fixed keyword-only common-parameter block, in this order, all optional:

```python
@staticmethod
def create_contract(
    *,
    excluded_rules: Sequence[str] | None = None,
    pinned_rules: Sequence[str] | None = None,
    year: int | None = None,
    output_format: str | None = None,
    extra_grammars: Sequence[str] | None = None,
    include_extended: bool = False,  # capability-specific params follow
) -> YourDomainContract: ...
```

Capability-specific parameters come after the common block. Every capability satisfies the `ContractFactory` protocol in `paxman/core/capability.py`.

**3. Rule metadata**

Every `Rule` subclass must declare six class attributes: `name`, `strategy`, `provenance`, `citation`, `target_semantics`, and `requires_features`. `Rule.__init_subclass__` enforces this at class-definition time, and a subclass missing any of them fails to import with a `TypeError`:

```python
class SectionYourRule(Rule[YourDomainNotation]):
    name = "Section 1-your-rule"
    strategy = RuleStrategy.REGEX
    provenance = PUBLICATION
    citation = "Section 1 (your-rule)"
    target_semantics = frozenset({"your_recognition"})
    requires_features = frozenset()
```

- **`target_semantics: ClassVar[frozenset[str]]`** is the non-empty set of grammar `semantics` ids whose notations this rule validates. The engine uses it for affinity routing: each recognition is validated only by rules whose `target_semantics` includes the producing grammar's `semantics`, and a rule declaring a semantics id no grammar claims fails fast with a `ContractError` before any candidate is produced. `Rule.__init_subclass__` also rejects an empty set at import time, since such a rule could never match a recognition.
- **`requires_features: ClassVar[frozenset[str]]`** is the set of Contract field names that must be truthy for the rule to run. An empty set is valid and is the common case: it means the rule always runs once selected. The engine validates that every named feature exists on the contract (a missing name raises `ContractError`) and applies the final feature filter *after* pinning, exclusion, and year selection: a rule whose required feature is present but `False` is dropped.

**Feature gating has two loci, and they produce different `Resolution` statuses:**

- **Input-shape features toggle grammars via `active_grammars`** (implemented only by the gated capabilities — Email, IP, ISBN; other contracts inherit the base `None` default, which runs every shipped grammar). A flag like `include_obfuscated` decides whether the `obfuscated_recognition` grammar runs at all. A disabled grammar recognizes nothing, so input readable only by that grammar yields `MISSING`.
- **Authority features use `requires_features`.** A flag like `include_localized` gates the CLDR rule that validates localized names, not the grammar. Recognition still runs and produces a notation, but the engine drops the gated rule, so the recognized-but-unvalidated input yields `INVALID`.

**Hard rule: never gate inside `matches()`.** Do not read `include_*` feature-toggle flags, and do not `cast(Contract, ...)` to reach them, inside `matches()`. `matches()` must never consult `output_format` either; validity comes from the notation, the specification, and any legitimate validity-affecting parameters (e.g. `default_country`, `two_digit_base_year`). The engine owns feature routing: declare the dependency in `requires_features` and let the filter decide whether the rule runs.

**4. `normalize()` never raises**

Rule methods must never raise — not `ValidationError`, `RecognitionError`, `ContractError`, or `ValueError`. `normalize()` is only called for a notation that passed `matches()`, and both methods must handle that input defensively: best-effort returns, with any unreachable branch returning the input unchanged rather than raising. Contract misconfigurations are caught in the contract's `__post_init__`, not in rule methods.

### Define the Contract

Define the Contract in `paxman/capabilities/YourDomain/contract.py` (separate file from the Capability class):

1. Import `CapabilityContract` from `paxman.core.contract`, `dataclass` and `field` from `dataclasses`, and `ClassVar` from `typing`
2. Define a frozen dataclass that inherits `CapabilityContract` (`@dataclass(frozen=True)` — do not add `slots=True`)
3. Override `DEFAULT_OUTPUT_FORMAT` (a concrete string) and `OFFERED_OUTPUT_FORMATS` (a `frozenset[str]` of alternative formats, excluding the default) as class variables
4. Set `capability_name` via `field(default="yourdomain", init=False)` (users never set this)
5. Add configuration fields for toggling grammars (e.g., `include_obfuscated: bool = False`)
6. Implement `active_grammars` as a `@property` that builds the grammar list from configuration flags — only if recognition is feature-gated; otherwise omit it (base default: run every shipped grammar)

`excluded_rules`, `pinned_rules`, `year`, and `output_format` are declared once on `CapabilityContract` — you don't redeclare them.

### Capability-Specific Fields

Beyond the standard protocol fields, your contract can include domain-specific configuration. These fields control grammar activation and rule behavior:

**Grammar toggle flags** — boolean fields that control which grammars are active:

```python
@dataclass(frozen=True)
class YourDomainContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "standard"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"expanded"})

    capability_name: str = field(default="yourdomain", init=False)
    include_obfuscated: bool = False  # toggles obfuscated_recognition grammar
    include_ipv6: bool = True  # toggles ipv6_recognition grammar

    @property
    def active_grammars(self) -> list[str]:
        grammars = ["standard_recognition"]
        if self.include_obfuscated:
            grammars.append("obfuscated_recognition")
        if self.include_ipv6:
            grammars.append("ipv6_recognition")
        return grammars
```

`excluded_rules`, `pinned_rules`, `year`, and `output_format` are declared once on `CapabilityContract` and inherited — they don't appear in this example.

**Rule parameters** — fields that rules read during normalization:

```python
two_digit_base_year: int | None = None  # Date: base year for 2-digit year parsing
```

**Pattern:** Each capability defines its own fields. There is no fixed set beyond the protocol requirements. Choose fields that:
- Toggle optional grammars (boolean flags)
- Pass parameters to rules (strings, ints, options)
- Control output behavior (`output_format`)

### Implementing `active_grammars` (optional)

`active_grammars` is **optional**: the base `CapabilityContract.active_grammars` returns `None`, and the engine falls back to running every shipped grammar returned by `get_grammars()`, in order. Implement it only when recognition is feature-gated — an `include_*` flag decides whether a grammar runs at all:

1. **Conditional** (Email, IP, ISBN): Build the list from boolean flags. Grammars are included only when their flag is `True`.

```python
@property
def active_grammars(self) -> list[str]:
    grammars = ["standard_recognition"]
    if self.include_obfuscated:
        grammars.append("obfuscated_recognition")
    if self.include_localhost:
        grammars.append("localhost_recognition")
    return grammars
```

Do **not** implement a static "always-all" override returning every grammar name (the former Date/Country pattern). The base `None` default already runs every shipped grammar, so a static override adds maintenance with zero behavior change — and it silently excludes any future grammar added to `get_grammars()` unless someone remembers to extend the list. Choose conditional when grammars are expensive or mutually exclusive; otherwise omit the property entirely and let the fallback run all shipped grammars.

### Implementing `output_format` (always optional, homogeneous across capabilities)

`output_format` is **always optional** and is handled identically by every capability. No capability may make it mandatory, and no capability may give it a meaning that diverges from the others — this is what keeps the contract surface predictable for future contributors.

You never declare the field yourself. `CapabilityContract` declares `output_format: str | None = None` — never a non-optional `str` — and its `__post_init__` validates and normalizes it through the shared `resolve_output_format` helper. After construction, `contract.output_format` **always holds a concrete format string** (never `None`).

Every contract subclass MUST override two class variables:

1. `DEFAULT_OUTPUT_FORMAT` — a concrete string naming the format the canonical value is returned in by default (e.g. `"ISO"` for Date, `"alpha2"` for Country, `"email"` for Email). This is the canonical output.
2. `OFFERED_OUTPUT_FORMATS` — a `frozenset[str]` of the *alternative* formats the capability supports **beyond** the default. The default format is **not** included here.

The acceptance rules (enforced by `resolve_output_format`) are:

| Input | Resolves to | Notes |
|-------|-------------|-------|
| `None` (omitted) | `DEFAULT_OUTPUT_FORMAT` | The field is optional; `None` is always allowed |
| `"default"` | `DEFAULT_OUTPUT_FORMAT` | Explicit revert to the canonical output |
| the default format string | `DEFAULT_OUTPUT_FORMAT` | e.g. `output_format="ISO"` when `DEFAULT_OUTPUT_FORMAT="ISO"` |
| any value in `OFFERED_OUTPUT_FORMATS` | that value | An explicit alternative format |
| anything else (e.g. `""`, `"None"`, `"none"`, a typo) | — | raises `ContractError` |

The key invariant: `None`, `"default"`, and the default format string are **treated identically by the capability formatter** — they leave the canonical value untouched. Only an explicit offered alternative triggers reformatting. This means a caller who omits `output_format`, passes `output_format="default"`, or passes the default format string gets exactly the same result, with no behavioral difference.

#### Presentational-only invariant (hard rule)

`output_format` is a *representation* transform, never a *recognition* or *validation* signal. Rules own validation and default normalization only: `matches()` never consults `output_format`, and `normalize()` always returns the default canonical form. Presentation lives in one place — the capability's `format_value(value, output_format, notation)` method — which the engine calls immediately after `normalize()` and before candidate deduplication and status determination. The format choice cannot change which candidates exist or which canonical values they carry; it only changes how each candidate is rendered. This is the contract mandate: the pipeline reports what authoritative specifications say, regardless of how the caller wants the answer displayed. Concretely:

- **Rules validate and normalize; the capability formats; the engine counts.** Each rule's `normalize()` returns the default canonical value; `Capability.format_value()` renders it in the requested format; the engine stores the formatted string as the candidate value and computes status from the set of distinct candidate values. No grammar is re-run, no input is re-parsed, and no rule is re-invoked.
- **Rules never read `output_format`.** Not to render, not to accept/reject a notation, and not to prefer one candidate over another. A CI source scan (`tests/unit/test_rule_output_format_purity.py`) fails any validation-rule module under `paxman/capabilities/*/rules/` that contains the token `output_format` — in code, comments, or docstrings — so a rule module must have no reference to the presentation field at all. Validity comes from the notation, the specification, and any legitimate validity-affecting parameters (e.g. `default_country`, `two_digit_base_year`). Using `output_format` to disambiguate (e.g. "drop the EU interpretation because `output_format='US'`") is forbidden — it would silently change the candidates the engine sees and break the always-report-ambiguity guarantee.
- **Offered formats must preserve the capability's ambiguity contract.** `AMBIGUOUS` means that one input produces multiple candidates with different canonical values. An offered format may be lossy when the capability explicitly defines a single-value input contract: Phone `national`, for example, intentionally omits the country code (and RFC 3966 extensions) from one resolved phone value. Do not use `output_format` to filter, reject, or disambiguate input; document any lossy representation and the input scope in which it is valid.
- **Formatting adds no provenance.** `Candidate.provenance`, `recognition_rule`, and `validation_rule` are set from the rule that validated the notation; the formatter only transforms the value.

Example — Date input `"01/02/2026"` is recognized by both the US and European grammars and validated by both rules, yielding two distinct canonical values (`2026-01-02` and `2026-02-01`). The result is `AMBIGUOUS` regardless of `output_format`. `output_format="US"` merely renders those two values as `01/02/2026` and `02/01/2026`; it cannot and must not decide which interpretation is "correct".

> Note: the grammar→rule routing decision (which rule validates which recognized notation) is an entirely separate concern from `output_format`. Routing is declared on the rule (`Rule.target_semantics`) and matched against each grammar's `semantics`; it operates in the recognition→validation stage and never touches formatting. Keep the two orthogonal.

Example wiring — inherited from `CapabilityContract`, you only set the class variables:

```python
@dataclass(frozen=True)
class YourDomainContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "alpha2"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"alpha3", "numeric", "name"}
    )
    # ... your capability-specific fields ...
```

For a capability with a single canonical form, `OFFERED_OUTPUT_FORMATS` is empty and `DEFAULT_OUTPUT_FORMAT` is simply the name of that form (e.g. `"email"`, `"ip"`). `output_format="email"` is then accepted and equivalent to omitting the field.

Rules never read `output_format`: `normalize()` always returns the default canonical form. Presentation lives in the capability's `format_value()` method, which the engine calls with the rule-produced default value, the contract's resolved format string (never `None` at runtime), and the original notation:

```python
def format_value(
    self, value: str, output_format: str | None, notation: YourDomainNotation
) -> str:
    if output_format == "us":
        return us_format(value)
    return value  # the default format (also covers "default" and None-resolved) is identity
```


**The Contract must satisfy the `Contract` protocol** (inheriting `CapabilityContract` does this structurally):

- `capability_name: str` — the capability this contract configures
- `active_grammars: Sequence[str] | None` — grammar names to activate; `None` (base default) runs every shipped grammar in `get_grammars()` order
- `excluded_rules: Sequence[str]` — list of rule names to exclude
- `pinned_rules: Sequence[str] | None` — pin to specific rules (takes precedence over `excluded_rules` when set)
- `year: int | None` — year for temporal filtering
- `output_format: str | None` — output format for canonical values. Always optional; after construction it resolves to a concrete format string (the capability's default when unset). Consumed by `Capability.format_value()`; rules never read it.

---

## Architectural Note: Protocol vs. ABC

Paxman uses two different patterns for its core interfaces: **Protocol** (duck typing) for the `Contract` and **Abstract Base Class (ABC)** (inheritance) for the `Capability`.

### Why `Contract` uses Protocol (Duck Typing)

The `Contract` is a **user-facing configuration object**. By defining it as a `Protocol`, we prioritize **flexibility** and **convenience** for the user:

1.  **Duck-Typed Protocol:** `Contract` stays a Protocol, not an ABC — anything with the right attributes satisfies it. In practice every built-in contract inherits the `CapabilityContract` base class (see Step 7), which satisfies the protocol structurally, so contributors never write the six protocol members by hand.
2.  **Data Structure Focus:** Contracts are primarily data holders. A Protocol allows users to use whatever data structure fits their domain (dataclasses, Pydantic models, TypedDicts) as long as they "quack like a duck" (provide the right attributes).
3.  **Decoupling:** The capability module doesn't need to depend tightly on the core contract class definition.

### Why `Capability` uses ABC (Inheritance)

The `Capability` is an **internal engine component**. By defining it as an `ABC`, we prioritize **strictness** and **reliability**:

1.  **Lifecycle Enforcement:** The engine relies on capabilities to provide grammars and rules. An ABC ensures that implementers *must* define `get_grammars()` and `get_rules()` before the code runs.
2.  **Internal Consistency:** Capabilities are discovered and managed by the engine's registry. Strict inheritance guarantees they adhere to the expected structure, preventing runtime errors during the discovery phase.
3.  **Behavioral Definition:** Unlike contracts (which hold state), capabilities define behavior. ABCs are the standard way to enforce behavioral contracts in Python.

**Summary:** Be **strict with yourself** (use ABC for engine components like `Capability`) but **open to others** (use Protocol for user-facing interfaces like `Contract`).

---

## Step 8: Create Package Init Files

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

### Capability package init

Create `paxman/capabilities/YourDomain/__init__.py`:

Export the Capability class, Contract class, and Notation type:

```python
from paxman.capabilities.YourDomain.capability import (
    YourDomainCapability,
    YourDomainContract,
)
from paxman.capabilities.YourDomain.notation import YourDomainNotation

__all__ = ["YourDomainCapability", "YourDomainContract", "YourDomainNotation"]
```

### Grammar and Rules package inits

Create `paxman/capabilities/YourDomain/grammar/__init__.py` and `paxman/capabilities/YourDomain/rules/__init__.py`:

These can be empty files (just a docstring or `pass`). They exist to make the directories proper Python packages.

### Test package inits

Create `tests/capabilities/yourdomain/__init__.py`:

This can be an empty file.

---

## Step 9: Register the Capability

*The `tools/new_capability.py` scaffolder (Step 0) already generated the starting point for this step — complete the `TODO(scaffold)` markers it left behind.*

The engine discovers capabilities through a registry. You must register your capability before using it.

In `paxman/capabilities/__init__.py`, add an import for your capability:

```python
from paxman.capabilities.YourDomain import YourDomainCapability as YourDomain
```

This makes your capability importable as:

```python
from paxman.capabilities import YourDomain
```

Users register the capability before first use:

```python
import paxman
from paxman.capabilities import YourDomain

paxman.register_capability(YourDomain())
```

---

## Step 10: Write Tests

Tests are organized into four layers. You must write tests for all layers.

### 10a: Grammar Tests

Create `tests/capabilities/yourdomain/test_grammar.py`:

For each grammar class, create a test class with these test methods:

1. `test_recognizes_valid_input` — happy path, grammar finds the expected pattern
2. `test_recognizes_variant_input` — edge cases (different delimiters, whitespace, case)
3. `test_recognizes_multiple` — input contains multiple matches
4. `test_ignores_incompatible_format` — grammar does not match patterns it should not handle
5. `test_returns_empty_for_empty_input` — empty string returns empty list

**Test pattern:**

- Instantiate the grammar directly (no fixtures needed)
- Call `grammar.recognize(text)`
- Assert the length of the result list
- Assert each result matches the expected list of strings

### 10b: Rule Tests

Create `tests/capabilities/yourdomain/test_rules.py`:

For each rule class, create a test class with these test methods:

1. `test_matches_valid_input` — happy path, notation is valid
2. `test_matches_variant_valid` — edge cases that should still be valid
3. `test_rejects_invalid_input` — notation that should not match
4. `test_normalize_produces_canonical` — verify exact canonical output
5. `test_provenance_attributes` — verify authority, spec name, year, lifecycle
6. `test_rule_name` — verify name follows convention
7. `test_strategy` — verify the rule strategy enum

**Test pattern:**

- Instantiate the rule directly
- Call `rule.matches(notation, contract)` and assert `True` or `False`
- Call `rule.normalize(notation, contract)` and assert exact string output
- Access `rule.provenance.*` fields and assert expected values

### 10c: Capability Tests

Create `tests/capabilities/yourdomain/test_capability.py`:

Two sections in one file:

**Notation tests:**

1. `test_creates_with_fields` — verify field access
2. `test_is_frozen` — verify immutability (assigning raises error)
3. `test_equality` — verify value equality
4. `test_hashable` — verify it can be used in sets or as dict keys

**Capability wiring tests:**

 1. `test_is_capability_subclass` — verify isinstance check
 2. `test_name` — verify name matches expected value
 3. `test_get_grammars_returns_all` — verify grammar count
 4. `test_get_rules_returns_all` — verify rule count
 5. `test_grammar_name` — verify grammar names follow convention
 6. `test_rule_name` — verify rule names follow convention

### 10d: Integration Tests

Create or extend `tests/integration/test_pipeline.py`:

Add tests that exercise the full pipeline through `run_capability()`:

1. `test_success` — recognized and validated, single canonical value
2. `test_missing` — nothing recognized
3. `test_invalid` — recognized but not validated
4. `test_ambiguity` — multiple conflicting canonical values
5. `test_version_stamp` — verify a `VersionStamp` recording the library version is present

**Critical:** All integration tests must use the `_clean_registry` autouse fixture:

```python
@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()
```

### 10e: End-to-End Tests

Create or extend `tests/e2e/test_canonicalize.py`:

Test through the public API (`paxman.api.canonicalize`):

1. `test_canonicalize_success` — full happy path
2. `test_canonicalize_missing` — no match
3. `test_canonicalize_with_options` — contract configuration

### Test Markers

Use pytest markers to categorize tests. Place markers on either the class or individual methods:

**Per-class** (when all methods share the same marker):

```python
@pytest.mark.capability
class TestYourGrammar:
    def test_recognizes_valid_input(self): ...
```

**Per-method** (when methods have different markers):

```python
class TestYourGrammar:
    @pytest.mark.capability
    def test_recognizes_valid_input(self): ...

    @pytest.mark.unit
    def test_regex_pattern_compiled(self): ...
```

Both styles are acceptable. Be consistent within each test file.

### Test Setup

For tests that need repeated object construction, use `setup_method`:

```python
class TestYourRule:
    def setup_method(self):
        self.rule = YourRule()
        self.contract = YourDomainContract()

    def test_matches_valid_input(self):
        notation = YourDomainNotation(field="value")
        assert self.rule.matches(notation, self.contract) is True
```

For simpler tests, construct objects inline in each method. Both patterns are used in the codebase.

### Registering Capabilities in Integration Tests

Each integration test file registers the capability it tests. Do this inside test methods, not in fixtures:

```python
from paxman.core.discovery import register_capability, reset_registry


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


class TestYourCapabilityPipeline:
    def test_success(self):
        register_capability(YourDomainCapability())
        contract = YourDomainCapability.create_contract()
        result = run_capability("your input", contract)
        assert result.status == Resolution.SUCCESS
```

**Why inline registration?** Each test registers only the capability it needs. This keeps tests independent and avoids fixture coupling.

---

## Step 11: Verify Quality Gates

Before considering your capability complete, verify all quality gates pass:

### Type Checking

```bash
uv run pyright --strict
```

Must pass with zero errors. No `# type: ignore` or `# noqa` comments are allowed.

### Linting and Formatting

```bash
uv run ruff check paxman/ tests/
uv run ruff format --check paxman/ tests/
```

Must pass with zero errors.

### Import Boundaries

```bash
uv run import-linter lint
```

Must pass. Your capability must not import from other capabilities. It may only import from `paxman.core`.

### Tests

```bash
uv run pytest tests/ -v
```

All tests must pass. No skipped tests without explicit justification.

---

## Step 12: Common Patterns and Pitfalls

### Pattern: One Provenance Per File

Each rule file defines a single `PUBLICATION` constant at module level. If you have multiple rules from the same specification, they share that provenance. If rules come from different specifications, put them in separate files.

### Pattern: Grammar Names Are Identifiers

Grammar names are snake_case strings used by the contract to toggle grammars. They must be unique within the capability. Follow the pattern `{format}_recognition` (e.g., `standard_recognition`, `obfuscated_recognition`).

### Pattern: Rule Names Follow Section Convention

Rule names follow the pattern `Section {X.Y.Z}-{description}` (e.g., `Section 3.4.1-addr-spec`). This makes it easy to map rules back to the specification.

### Pattern: Notation Fields Are Typed

Rules access notation fields by name (e.g., `notation.field_name`), not by list position.

### Pitfall: Grammar Regex Must Be Compiled Once

Compile regex patterns at module level, not inside the `recognize` method. Recompiling on every call is wasteful and can cause subtle bugs with cached groups.

### Pitfall: Matching the Strategy to the Representation

Choose the recognition strategy from the representation, not from habit (see Step 4). A finite vocabulary of free-form tokens with no syntactic shape (country names, spelled-out words) cannot be recognized by regex — use the Lexicon strategy with a key-only table. A distinctive shape (fixed widths, delimiters, character classes) is over-engineering as a lexicon — use Regex and let rules own validity. Country demonstrates both in one capability: `alpha2`/`alpha3`/`numeric` are Regex grammars, `name_recognition` is a Lexicon grammar. If the representation fits neither strategy (nested structure, enumerated formats, open Unicode classes), read the additional strategies at the end of Step 4 before forcing it into a regex that fights it.

### Pitfall: Rule Methods Must Never Raise

The `matches` method must return `False` for any invalid input, never raise. The `normalize` method is only called after `matches` returns `True`, but it must also never raise — not `ValidationError`, `RecognitionError`, `ContractError`, or `ValueError`. Handle edge cases defensively: best-effort returns, and unreachable branches return the input unchanged. Contract misconfigurations are caught in the contract's `__post_init__`, not in rule methods.

### Pitfall: Using `output_format` as a Routing or Filtering Signal

`output_format` is a presentation transform, not a recognition or validation signal. Rules never read `output_format` at all — not in `matches()` to accept/reject a notation, and not in `normalize()` to render, prefer one candidate over another, or disambiguate between competing interpretations. `AMBIGUOUS` describes one input that produces multiple candidates with different canonical values; it is not a caller preference. Presentation is owned by `Capability.format_value()`, which the engine calls after `normalize()`. A lossy formatter is permitted only when the capability's input contract makes that representation meaningful — Phone `national` is intentionally lossy for a single resolved phone token. A CI source scan enforces that rule modules contain no `output_format` reference at all. See the presentational-only invariant above.

### Pitfall: Contract Fields Must Have Defaults

Users should be able to construct a contract with zero arguments: `YourDomainContract()`. All fields except `capability_name` must have sensible defaults.

### Pitfall: Import Boundaries Are Enforced

Your capability cannot import from `paxman.capabilities.OtherCapability`. If you need shared utilities, they belong in `paxman.core` or a separate shared module.

### Pattern: Multiple Rule Files Per Capability

When your capability has rules from different specifications, put each in its own file:

```
rules/
├── __init__.py
├── specification_a_ed2020.py    # rules from Spec A
├── specification_b_ed2022.py    # rules from Spec B
└── data/
    └── lookup_tables.py         # shared data
```

Each file defines its own `PUBLICATION` provenance. Rules from the same specification share a file (see Pattern: One Provenance Per File above).

### Pattern: Multiple Rule Classes Per File

When multiple rules share the same `PUBLICATION` provenance, put them in one file:

```python
# rules/specification_a_ed2020.py

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 3166-1",
    ...
)

class SectionAlpha2Codes(Rule[CountryNotation]):
    provenance = PUBLICATION
    ...

class SectionAlpha3Codes(Rule[CountryNotation]):
    provenance = PUBLICATION
    ...
```

This is the recommended pattern when rules come from the same section of the same specification.

### Pattern: Grammar Naming Convention

Grammar names follow the pattern `{format}_recognition`:

| Capability | Grammar Name | What it recognizes |
|-----------|-------------|-------------------|
| Email | `standard_recognition` | `user@domain.tld` |
| Email | `obfuscated_recognition` | `user at domain dot tld` |
| Email | `localhost_recognition` | `user@localhost` |
| Date | `date` (candidates: `iso8601`, `slash_iso`, `us`, `european`) | `YYYY-MM-DD` / `YYYY/MM/DD` / `MM/DD/YYYY` / `DD/MM/YYYY` via `CandidatesMatcher` `all` |
| Country | `alpha2_recognition` | `US` (2 letters) |
| Country | `alpha3_recognition` | `USA` (3 letters) |
| Country | `numeric_recognition` | `840` (1-3 digits) |
| Country | `name_recognition` | `United States` |
| IP | `ipv4_recognition` | `192.168.1.1` |
| IP | `ipv6_recognition` | `2001:db8::1` |

> Legacy per-format Date files (`iso8601`/`us`/`european`) remain on disk inert — the shipped grammar is the single `date` CandidatesMatcher above.

### Pattern: Rule Naming Convention

Rule names follow `Section {reference}-{description}`:

| Capability | Rule Name | Reference |
|-----------|-----------|-----------|
| Email | `Section 3.4.1-addr-spec` | RFC 5322 §3.4.1 |
| Email | `Section 6.3-localhost` | RFC 6761 §6.3 |
| Date | `Section 4.3.1-calendar-date` | ISO 8601 §4.3.1 |
| Date | `Section 1-date-format` | US Federal Rules |
| Date | `Section 4-date-format` | EN 50160 §4 |
| Country | `Section-alpha2-codes` | ISO 3166-1 (alpha-2) |
| Country | `Section-alpha3-codes` | ISO 3166-1 (alpha-3) |
| Country | `Section-numeric-codes` | ISO 3166-1 (numeric) |
| Country | `Section-names` | ISO 3166-1 (names) |
| IP | `Section 3.2-ipv4-address` | RFC 791 §3.2 |
| IP | `Section 4-ipv6-text-representation` | RFC 5952 §4 |

### Pitfall: Forgetting to Register the Capability

Your capability must be registered in `paxman/capabilities/__init__.py`. Without this, users cannot import it via `from paxman.capabilities import YourDomain`.

### Pitfall: Not Using `typing.cast` for Contract-Specific Fields

If your rule needs to read a capability-specific parameter (like `two_digit_base_year` or `default_country`), you must use `typing.cast` to narrow the type. Accessing undefined attributes on the base `Contract` protocol will fail at runtime. Feature-toggle flags (`include_*`) are not cast-for parameters: declare them in `Rule.requires_features` and let the engine gate the rule.

---

## Extending an Existing Capability with Community Grammars

A shipped capability is closed for modification but open for extension: you can add recognition and validation without touching the capability package.

1. **Author** a `Grammar` subclass (Step 4) and a `Rule` subclass (Step 5) for the capability's notation, exactly as you would for a new capability — the same contracts apply, including span-bearing `RecognitionMatch` output, `semantics` on the grammar, `target_semantics` on the rule, and `requires_features`.
2. **Register** them before the first `canonicalize()` call:

   ```python
   import paxman

   paxman.register_grammar("date", DotDateGrammar)
   paxman.register_rule("date", DotDateRule)
   ```

3. **Opt in** per contract via `extra_grammars` — a base `CapabilityContract` field surfaced on every `create_contract` factory:

   ```python
   contract = Date.create_contract(extra_grammars=("dot_date_recognition",))
   result = paxman.canonicalize("2024.01.01", contract)
   ```

Semantics to rely on:

- The extension registries freeze with the capability registry — registration after the first pipeline run raises `CapabilityError`.
- Opt-in only: an un-named registered grammar never affects results, so shipped behavior stays identical (deterministic) for non-opt-in contracts.
- Community rules are opt-in too: a registered rule runs only when the contract's `extra_grammars` resolve to one of its `target_semantics`; an un-opted rule — even one targeting a shipped grammar's semantics — never affects results.
- Unknown `extra_grammars` names are silently skipped; shipped names listed in `extra_grammars` are deduplicated.
- Composition is guarded: a grammar name colliding with a shipped name, or an opted-in community rule naming a missing grammar, fails fast at pipeline start.

---

## Checklist

Use this checklist to verify your capability is complete:

- [ ] Notation is a frozen dataclass with one `str` field per component
- [ ] Each grammar extends `Grammar[YourDomainNotation]` and implements `recognize(text) -> list[RecognitionMatch[YourDomainNotation]]`
- [ ] Each rule extends `Rule[YourDomainNotation]` and implements `matches(notation, contract) -> bool` and `normalize(notation, contract) -> str`
- [ ] Each rule declares `target_semantics` (non-empty `frozenset[str]`) and `requires_features` (`frozenset()` when the rule always runs)
- [ ] Each rule file has a `PUBLICATION` provenance constant
- [ ] Capability extends `Capability` and implements `get_grammars()` and `get_rules()`
- [ ] Contract inherits `CapabilityContract` (frozen dataclass, no `slots=True`) and satisfies the `Contract` protocol
- [ ] Contract inherits `pinned_rules: tuple[str, ...] | None = None` from `CapabilityContract`
- [ ] Contract inherits `output_format` from `CapabilityContract` (always optional; base `__post_init__` validates via `resolve_output_format`)
- [ ] Contract inherits `extra_grammars` from `CapabilityContract` (opt-in community grammar names; unknown names silently skipped)
- [ ] Contract declares a `DEFAULT_OUTPUT_FORMAT` (concrete string) and `OFFERED_OUTPUT_FORMATS` (alternatives only, excluding the default)
- [ ] Rules never reference `output_format`: `normalize()` returns only the default canonical form, and presentation lives in `Capability.format_value()`; any lossy offered format is explicitly documented against the capability's input/ambiguity contract (see presentational-only invariant)
- [ ] If using lookup tables: `rules/data/` directory contains data files
- [ ] Grammar data is key-only (no token-to-canonical mappings); rule data owns all authority-backed mappings (see The Grammar/Rule Boundary)
- [ ] Recognition keys and rule tables live in separate files, with a consistency test covering every shipped recognition key
- [ ] If rules access capability-specific contract fields: uses `typing.cast`
- [ ] Grammar emits span-bearing `RecognitionMatch` objects and does NOT deduplicate or order — the engine owns containment dedup ("longer wins") and document ordering
- [ ] Each grammar implements one of the documented recognition strategies (Regex or Lexicon) for its representation — see Step 4
- [ ] Package `__init__.py` files export the public API
- [ ] Capability is registered in `paxman/capabilities/__init__.py`
- [ ] Test markers are consistent within each file
- [ ] Grammar tests cover happy path, edge cases, multiple matches, and empty input
- [ ] Rule tests cover valid input, invalid input, normalization, provenance, and naming
- [ ] Notation tests cover creation, immutability, and equality
- [ ] Capability tests cover subclass check, name, grammar count, and rule count
- [ ] Integration tests use the `_clean_registry` fixture
- [ ] End-to-end tests exercise the public API
- [ ] `pyright --strict` passes with zero errors
- [ ] `ruff check` passes with zero errors
- [ ] `ruff format --check` passes with zero errors
- [ ] `import-linter` passes
- [ ] All tests pass with `uv run pytest`
