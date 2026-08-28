# CAPABILITIES KNOWLEDGE BASE

## OVERVIEW
The deepest directory in the repo (174 py files): 15 shipped capability packages (BIC, Country, Currency, Date, Email, IBAN, IP, ISBN, ISSN, Language, Money, ORCID, Phone, SI Unit, URL), each an independent recognize→validate→resolve mini-system wired into the shared pipeline via `paxman.core`. Each package is self-contained: grammars recognize representations, rules assign meaning with provenance, the contract selects what runs, and `format_value()` renders the result.

**Authoritative spec:** the root `HOW_TO_ADD_NEW_CAPABILITY.md` (62KB — read it before touching this directory). This file is the compact governance reference: intended architecture, hard rules, and known legacy exceptions. Where the two differ, HOW_TO wins.

## STRUCTURE (intended)
```text
paxman/capabilities/
├── __init__.py          # registration imports + __all__ (see NOTES)
├── <Name>/              # one self-contained package per capability
│   ├── __init__.py      # exports Capability, <Name>Contract, <Name>Notation
│   ├── notation.py      # frozen slots dataclass — the intermediate token
│   ├── contract.py      # frozen CapabilityContract subclass (NO slots)
│   ├── capability.py    # Capability[NotationT] subclass — wiring + format_value()
│   ├── grammar/         # recognizers — one file per grammar
│   ├── grammar/data/    # data serving grammars — key-only recognition tables
│   ├── rules/           # validators — one file per publication
│   └── rules/data/      # data serving rules — authority-backed lookup tables
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Build/extend a capability | root `HOW_TO_ADD_NEW_CAPABILITY.md` (62KB spec — read first) |
| Wire grammars + rules | `<Name>/capability.py` → `get_grammars()`, `get_rules()`, static `create_contract()` |
| Presentation | `<Name>/capability.py` → `format_value()` — the ONLY presentation seam |
| Feature flags / active grammars | `<Name>/contract.py` → `include_*` fields + `active_grammars` property (optional: only Email/IP/ISBN override it; `None` = run every shipped grammar) |
| Token shape | `<Name>/notation.py` |
| Recognition | `<Name>/grammar/` (+ `grammar/data/` for lexicon key tables) |
| Validation | `<Name>/rules/` (+ `rules/data/` for authority tables) |
| Data tables | `rules/data/` (authority data serving rules), `grammar/data/` (keys serving grammars) — plain module-level tables, separated from logic |
| Generated data | only modules with a source snapshot + tool (ISBN range message → `tools/regenerate_isbn_range_data.py`, SIUnit prefixed units → `tools/regenerate_si_prefix_data.py`, URL IDNA UTS #46 mapping → `tools/regenerate_idna_uts46_data.py`, Currency + Money data set → `tools/regenerate_currency_data.py` from `paxman/shared_data/currency_snapshot.json`) — edit via the snapshot, then regenerate |
| Register a capability | `paxman/capabilities/__init__.py` (import + `__all__`) → `paxman/core/discovery.py` |

## INTENDED ARCHITECTURE (the unanimous surface)
Every capability must conform to the same structural surface. `CapabilityContract` and `Rule.__init_subclass__` make most of it structural rather than documentary:

- **Notation** — `@dataclass(frozen=True, slots=True)`; one `str` field per component; the sole type parameter of the capability's `Grammar[NotationT]` / `Rule[NotationT]`.
- **Contract** — `@dataclass(frozen=True)` extending `CapabilityContract`, NO `slots=True` (incompatible with the base `super()` pattern). Sets `DEFAULT_OUTPUT_FORMAT` / `OFFERED_OUTPUT_FORMATS` class vars; `capability_name` via `field(init=False)`; inherits `output_format` (always optional; base `__post_init__` resolves it and validates offered alternatives); `active_grammars` is optional — only feature-gated capabilities (Email, IP, ISBN) override it, and the base `None` default runs every shipped grammar. Subclass `CapabilityContract` (never `Contract` directly). `Contract` is engine-internal since ADR-0007.
- **Grammar** — one file = one recognizer; exception: CandidatesMatcher consolidates same-meaning formats in one file (Date 4->1); combinator customers (SIUnit split) share lexicons in one file; `name` = `{format}_recognition` (snake_case, unique per capability); `semantics` = non-empty string declaring the meaning the grammar's notations carry (identity id unless the format shares another grammar's meaning, in which case declare that coalesced id — shared meaning ⇒ shared id); emits span-bearing `RecognitionMatch` (half-open `[start, end)`, `raw_text`); syntax-only — extraction and sanitization, never validation, dedup, ordering, or token→canonical mapping. Shipped kernel kinds (6): regex, lexicon, scanner, combinator, candidates, label — see file header and HOW_TO §4.
- **Rule** — one file = one publication (module-level `PUBLICATION` provenance constant); class = one spec section; declares `name` (`Section {X.Y.Z}-{description}`), `strategy`, `provenance`, `citation`, `target_semantics` (non-empty), `requires_features` — all six enforced at import time. Rule classes sharing one publication live in the same file; authority-backed lookup tables live in `rules/data/`, separated from rule logic.
- **Feature gating — two loci, two statuses** — input-shape features toggle grammars via `active_grammars` (disabled grammar → `MISSING`), implemented only by the gated capabilities (Email, IP, ISBN) — other contracts inherit the `None` default, which runs every shipped grammar; authority features gate rules via `requires_features` (dropped rule → `INVALID`). Never gate inside `matches()`; never cast to read `include_*` flags. `typing.cast` is only for validity-affecting parameters. Common-word suppression via `COMMON_WORDS` 67 (`BoundarySpec` WORD guard + `suppressible`, contract `suppress_common_words` default off, CLI `--suppress-common-words`).
- **Presentation-only invariant** — rules never reference `output_format` (CI-scanned); `normalize()` always returns the default canonical form; `format_value()` is the only presentation seam, overridden only when `OFFERED_OUTPUT_FORMATS` is non-empty; formatting adds no provenance; offered formats must preserve the capability's ambiguity contract.
- **`create_contract()`** — static, keyword-only; fixed common block first (`excluded_rules`, `pinned_rules`, `year`, `output_format`), capability-specific params after.

## GOVERNANCE (hard rules)
- **Grammar/Rule boundary is absolute**: grammars own syntax, rules own meaning. Grammar tables are key-only; authority-backed mappings live in `rules/data/` and are imported only by rules. A consistency test must cover every shipped recognition key against rule-data mappings.
- **No cross-capability imports** — a capability package imports only from `paxman.core`, never from a sibling `paxman.capabilities.*` (enforced by import-linter).
- **Rules never read `output_format`**, never raise (best-effort returns; unreachable branches return input unchanged), never gate on `include_*` (declared as `requires_features` instead).
- **Data files are plain tables, most maintained in place** — `rules/data/` and `grammar/data/` exist to separate data from logic, not to mark generated output. Only modules that carry a generator (source snapshot + script — currently the ISBN range message via `tools/regenerate_isbn_range_data.py`, the SIUnit prefixed-unit and grammar token tables via `tools/regenerate_si_prefix_data.py`, the URL IDNA UTS #46 mapping via `tools/regenerate_idna_uts46_data.py`, and the Currency + Money data set via `tools/regenerate_currency_data.py` from `paxman/shared_data/currency_snapshot.json`) must be edited through the snapshot and regenerated, never by hand, or they drift from their authority. Unmarked data files are edited directly.
- **No type suppression** — no `# type: ignore` / `# noqa` / `# pyright: ignore` in source; fix the root cause or use a scoped per-file-ignore in pyproject.
- **Rule class names are CapWords** — the legacy `Section6_1`-style naming is scoped to `Phone/rules/*.py` (and its tests) via the N801 per-file-ignore: legacy coverage, not a pattern.
- **`__init__.py` acronym aliases trip N814** — covered by the scoped per-file-ignore; don't add inline `# noqa`.
- **No additions to `__init__.py` without matching `__all__`** — the export list is the registration surface.
- **Quality gates before merge** — `ruff check`, `ruff format --check`, `pyright` (strict), `import-linter lint`, `pytest` (95% coverage).

## ANTI-PATTERNS & LEGACY EXCEPTIONS
- Don't force a representation into a regex that fights it — consult HOW_TO's recognition-strategy section (Recognition Kernel kinds: regex/lexicon/scanner/combinator/candidates/label) before choosing.
- Don't invert the two-locus gating model (e.g., gating recognition on authority features or gating validation on input-shape features) — it produces the wrong `Resolution` statuses.
- Don't add `slots=True` to contracts.
- Don't put authority data in `grammar/data/` or recognition keys in `rules/data/` — `grammar/data/` serves grammars (keys), `rules/data/` serves rules (authority mappings); the boundary is the point.
- When extending an existing capability, check whether the file you're touching is a flagged legacy exception before copying its style; new code follows the intended architecture.

## NOTES
- `__init__.py` exports all fifteen shipped capabilities; completeness is enforced by `tests/unit/test_capability_exports.py`. IBAN and ISSN are the minimal-surface members (1 grammar + 1 rule each).
- Root AGENTS.md is authoritative for pipeline flow, domain objects, and quality gates; this file adds capability-package structure and governance specifics.
