# PROJECT KNOWLEDGE BASE

**Generated:** 2026-08-22
**Commit:** d7737f0
**Branch:** chores/pre-release-housekeeping

## OVERVIEW
Paxman is a Python 3.11+ canonicalization library with a small CLI: takes ambiguous human input, returns what authoritative specs say it means, with full provenance. Deterministic, provenance-first. 15 capabilities (BIC, Country, Currency, Date, Email, IBAN, IP, ISBN, ISSN, Language, Money, ORCID, Phone, SI Unit, URL) — recognition via the Recognition Kernel (ADR-0009) with legacy pipeline stages retained for unmigrated grammars. Toolchain: uv + hatchling, ruff, strict pyright, import-linter, pytest at 95% coverage.

## STRUCTURE
```text
paxman/
├── api/            # canonicalize() + bootstrap (register_all_shipped, list_shipped_capabilities)
├── cli.py          # CLI: `paxman` console script / `python -m paxman` (--list, --json, stdin)
├── __main__.py     # python -m paxman entry
├── engine/         # run_capability() pipeline orchestrator
├── core/           # domain objects, Contract protocol, registry, extensions, errors (+ grammar/ shared machinery — kernel ScanContext/MatcherSpec/engine_loop + legacy stages)
├── capabilities/   # 15 self-contained capability packages
├── shared_data/    # cross-capability source snapshots (currency_snapshot.json → Currency + Money data)
└── py.typed        # PEP 561 marker
benchmarks/         # harness.py (CI-run), grammar_stage_parity.py, baseline.json
tests/              # unit / capabilities/<cap> / integration / property / e2e
tools/              # new_capability.py (scaffolder), generate_readme_table.py,
                    # regenerate_{isbn_range,si_prefix,idna_uts46,currency}_data.py
docs/               # adr/, development/, recipes/, user/
```

## WHERE TO LOOK
| Task | Location |
|------|----------|
| Trace pipeline flow | `paxman/engine/orchestrator.py` → `run_capability()` |
| Domain vocabulary (Rule, Provenance, Candidate…) | `paxman/core/domain.py` |
| Contract protocol | `paxman/core/contract.py`, `paxman/core/capability_contract.py` |
| Capability registration | `paxman/core/discovery.py` (explicit, never auto) |
| Community extensions | `paxman/core/extensions.py` → `register_grammar` / `register_rule` + `extra_grammars` on contracts |
| Error hierarchy | `paxman/core/errors.py` |
| Add a capability | `HOW_TO_ADD_NEW_CAPABILITY.md` (62KB spec — read first). Scaffold first with `tools/new_capability.py` (see HOW_TO_ADD_NEW_CAPABILITY.md Step 0); then fill in the domain. |
| Recognition (per cap) | `paxman/capabilities/<Name>/grammar/` |
| Validation (per cap) | `paxman/capabilities/<Name>/rules/` |
| Presentation seam | `paxman/capabilities/<Name>/capability.py` → `format_value()` |
| Regenerate generated data | `tools/regenerate_isbn_range_data.py` (ISBN range), `tools/regenerate_si_prefix_data.py` (SIUnit prefixed units), `tools/regenerate_idna_uts46_data.py` (URL IDNA mapping), `tools/regenerate_currency_data.py` (Currency + Money from `paxman/shared_data/currency_snapshot.json`) |
| CLI behavior | `paxman/cli.py` (`--list`, `--json`, stdin; contract flags are API-only) |
| Merge-blocking commands | `.github/workflows/ci.yml` (authoritative) |

## CODE MAP
| Symbol | Type | Location | Role |
|--------|------|----------|------|
| `canonicalize()` | function | `paxman/api/canonicalize.py` | Sole user entry point → `run_capability()` |
| `register_all_shipped()` / `list_shipped_capabilities()` | functions | `paxman/api/bootstrap.py` | One-call registration of the 15 shipped capabilities; deterministic name list |
| `list_registered_capabilities()` | function | `paxman/core/discovery.py` | Introspection of the live registry |
| `register_capability()` | function | `paxman/core/discovery.py` | Registry add; freezes on first run |
| `register_grammar()` / `register_rule()` | functions | `paxman/core/extensions.py` | Community extension seam (opt-in via contract `extra_grammars`) |
| `run_capability()` | function | `paxman/engine/orchestrator.py` | Full pipeline (recognize→validate→resolve→hash) |
| `ExecutionResult` | dataclass | `paxman/engine/orchestrator.py` | Return type of `canonicalize()` |
| `Capability` | ABC | `paxman/core/capability.py` | `get_grammars`/`get_rules`/`format_value` |
| `CapabilityContract` | dataclass | `paxman/core/capability_contract.py` | Frozen contract base (no slots) |
| `Contract` | Protocol | `paxman/core/contract.py` | Structural contract interface |
| `Rule` / `Grammar` | ABCs | `paxman/core/domain.py` | Validation / recognition units |
| `Resolution`, `Provenance`, `Candidate`, `RecognizedRep`, `VersionStamp` | dataclasses | `paxman/core/domain.py` | Pipeline value objects |
| `main()` | function | `paxman/cli.py` | CLI entry (`[project.scripts] paxman` + `python -m paxman`) |

## CONVENTIONS
- **uv only** — no Makefile/tox/nox. Every command via `uv run`.
- Per-capability layout: `notation.py`, `contract.py`, `capability.py`, `grammar/`, `rules/`.
- Rule file = ONE publication (`rfc_5322_ed2008.py`); class = one section; rule `name` = `"Section 3.4.1-addr-spec"`.
- Grammars recognize only: span-bearing `RecognitionMatch`, never bare notation, never validate/dedup/order.
- Rules never read `output_format` (CI source-scan enforced), never raise, never gate on `include_*` (declared as `requires_features`).
- `format_value()` is the ONLY presentation seam; `output_format` resolved in `CapabilityContract.__post_init__`.
- Domain objects: `@dataclass(frozen=True, slots=True)`. Contracts: `@dataclass(frozen=True)` **without** slots.
- Test doubles local to the test file/conftest — no shared mock libraries.
- Registry is module-level and freezes per pipeline run; tests use autouse `_clean_registry` fixture (integration/e2e).
- TDD: failing test first. No skipped tests without justification.

## ANTI-PATTERNS (THIS PROJECT)
- **No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source** — fix root cause or use scoped ruff `per-file-ignores` (sanctioned pattern in pyproject). Tests may use `# type: ignore[misc]` for immutability checks.
- Deterministic by construction: given the same input, the same contract, and the same library snapshot (fixed library version, registry contents, and rule-data tables), the pipeline always yields the same canonical output — no world-knowledge, no clock, no environment-dependent ordering, no fuzzy logic, no network inference across recognition, validation, and canonicalization.
- No cross-capability imports; capabilities import only from `paxman.core`; `paxman.core` imports nothing from `paxman.*`.
- Grammars must not map tokens to canonical values or import rule-layer data.
- Rules never contain the token `output_format` (code, comments, or docstrings).
- No `as any`, no broad exception suppression.

## COMMANDS
```bash
uv sync --all-extras                                   # install
uv run ruff check paxman/ tests/                      # lint
uv run ruff format --check paxman/ tests/             # format check
uv run pyright                                        # strict typecheck
uv run import-linter lint                             # layer boundaries
uv run pytest                                         # all tests
uv run pytest -m "unit or capability or integration or e2e"      # by marker (also: property, benchmark, country, currency, isbn, issn, money, url, si_unit)
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95
uv run python tools/regenerate_isbn_range_data.py     # regenerate ISBN range message module
uv run python tools/regenerate_si_prefix_data.py      # regenerate SIUnit prefixed-unit modules
uv run python tools/regenerate_idna_uts46_data.py     # regenerate URL IDNA UTS #46 mapping
uv run python tools/regenerate_currency_data.py       # regenerate Currency + Money data from shared snapshot
uv run python -m paxman email "user@example.com"      # CLI smoke test
```
Full pre-PR gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest`

## NOTES
- `paxman/capabilities/__init__.py` exports all fifteen shipped capabilities (BIC, Country, Currency, Date, Email, IBAN, IP, ISBN, ISSN, Language, Money, ORCID, Phone, SI Unit, URL); export completeness is enforced by `tests/unit/test_capability_exports.py`.
- CONTEXT.md is the domain glossary for the full shipped set (fifteen capabilities). It is kept in sync with the code; when adding a capability, update its Notation/table entries there too.
- No `pyrightconfig.json` — pyright config is inline `[tool.pyright]` in pyproject.toml. No `.editorconfig`.
- Data modules live under `rules/data/` and `grammar/data/` — plain module-level tables separating data from logic. Generated modules (edit via snapshot + regenerate, never by hand): ISBN range message (`tools/regenerate_isbn_range_data.py`), URL IDNA UTS #46 mapping (`tools/regenerate_idna_uts46_data.py`), SIUnit prefixed-unit and grammar token tables (`tools/regenerate_si_prefix_data.py`), and the Currency + Money data set (`tools/regenerate_currency_data.py`, from `paxman/shared_data/currency_snapshot.json`). Unmarked data files are edited directly.
- Library + CLI: `[project.scripts] paxman = "paxman.cli:main"` and `python -m paxman`; CLI supports `--list`, `--json`, stdin input. Version 0.1.0.
- Publishing: `.github/workflows/publish.yml` uses PyPI Trusted Publishing (OIDC) with a Git-tag ↔ `pyproject.toml` version safety check; `paxman/py.typed` ships PEP 561 conformance.
- Coverage: global `fail_under = 95`; `paxman/cli.py` and `paxman/__main__.py` are omitted from coverage (smoke-tested via e2e).
