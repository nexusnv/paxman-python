---
title: "Glossary"
---

Common terms used throughout Paxman — in the library API, the pipeline, the capability guides, and the provenance tables. Definitions are short; each links to the concept page where the term is introduced.

---

## A

**AMBIGUOUS** — A `Resolution` status. One logical mention produced two or more distinct validated values (e.g. `"01/02/2026"` → `2026-01-02` vs `2026-02-01`). `canonicalized_value` and `span` are `None`; inspect `candidates` for competing provenances. See [Candidates & Ambiguity](concepts/candidates-and-ambiguity/) and [Execution Result](concepts/execution-result/).

**Authority** — Who published the specification. Appears on `Provenance.authority` (e.g. `"IETF"`, `"ISO"`, `"BIPM"`, `"WHATWG"`, `"Unicode CLDR"`). See [Provenance](concepts/provenance/) and [Citations](citations/).

**Autogenerate (sidebar)** — Starlight sidebar entries that auto-list pages from a directory (e.g. `Concepts`, `Capabilities`). See `docs_site/astro.config.mjs`.

---

## B

**BIC** — Bank Identifier Code (ISO 9362). A Paxman capability with notation `BICNotation`. See Capabilities table in [Concepts — Capabilities](concepts/capabilities/).

**BIPM** — Bureau International des Poids et Mesures. Authority for the SI Brochure (9th ed., 2019) cited by the SI Unit capability. See [Citations](citations/).

**BCP 47** — IETF Best Current Practice 47 (RFC 5646) for language tags. Cited by the Language capability via the `Section 2.1-syntax` rule. See [Citations](citations/).

---

## C

**Candidate** — A validated proposal for a canonical value. Fields: `value`, `recognition_rule` (grammar name), `validation_rule` (rule name), `span`, `provenance`. Deduplicated by `(value, recognition_rule, validation_rule)` during resolution. See [Execution Result](concepts/execution-result/) and [Pipeline](concepts/pipeline/).

**Capability** — A self-contained domain module (e.g. Email, Country, URL) that defines its own `Notation`, `Grammars`, `Rules`, `Contract`, and `format_value`. 15 shipped in v0.2.0; the set grows in minor releases. Import via `paxman.capabilities`. See [Concepts — Capabilities](concepts/capabilities/).

**Canonicalization** — Resolving ambiguous human input to what an authoritative specification says it means, with provenance. Paxman is a canonicalization library — deterministic, provenance-first. See [Home](index/).

**Canonicalized value** — `ExecutionResult.canonicalized_value`: the `str` on `SUCCESS`, `None` otherwise. Never infer success from its truthiness — branch on `status`. See [Execution Result](concepts/execution-result/).

**Citation** — Human-readable section reference on a rule (e.g. `Section 3.4.1 (addr-spec)`, `CLDR v47 currency symbols`). Together with `Provenance` it forms a complete citable claim. See [Provenance](concepts/provenance/) and [Citations](citations/).

**CLDR** — Unicode Common Locale Data Repository. Authorities `"Unicode"` and `"Unicode CLDR"` in provenance both refer to CLDR. Cited by Country (v45), Currency/Money (v47), Language (v46 display names). See [Citations](citations/).

**Contract** — User-facing frozen configuration for one capability. Common fields: `excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`, `suppress_common_words`; capability-specific `include_*`/`allow_*`/`default_*` flags gate grammars or validation. Created via `SomeCapability.create_contract(...)`. See [Concepts — Contracts](concepts/contracts/).

**Country** — Paxman capability for ISO 3166 country codes/names, with optional CLDR localized and historical coverage. See per-capability guide under [Capabilities](capabilities/).

**Currency** — Paxman capability for ISO 4217 currency identifiers (no amounts). See [Capabilities](capabilities/) and [Citations](citations/).

---

## D

**Date** — Paxman capability for calendar dates (ISO 8601, US, European, slash-ISO). Canonical form is ISO `YYYY-MM-DD` by default. See [Capabilities](capabilities/).

**Derived convention** — Non-authoritative locale convention (e.g. Date `MM/DD/YYYY`). Carries `authority="Derived convention"`, `kind="convention"`, no `reference_url`. Included for completeness in [Citations](citations/).

**Deterministic** — Given the same input, the same contract, and the same installed library snapshot (version, rule tables, snapshot SHAs), the pipeline yields the same output. No randomness, clock, or network. See [Concepts — Pipeline](concepts/pipeline/) and [Migration](migration/).

**Domain vocabulary** — The shared types defined in `paxman/core/domain.py` (`Rule`, `Grammar`, `Provenance`, `Candidate`, `RecognizedRep`, `Resolution`, `VersionStamp`, …). See `paxman/core` knowledge base.

---

## E

**Email** — Paxman capability for RFC 5322 / RFC 6761 addresses. See [Capabilities](capabilities/).

**ExecutionResult** — Return type of `canonicalize()`. Fields: `status`, `canonicalized_value`, `candidates`, `span`, `version_stamp`, `contract`. Always returned — domain outcomes are statuses, not exceptions. See [Concepts — Execution Result](concepts/execution-result/).

**Extension (`extra_grammars`)** — Community grammar/rule seam. Register via `paxman.register_grammar()` / `register_rule()` before first call; opt in per-contract via `extra_grammars`. See [Extending](extending/) and `paxman/core/extensions.py`.

---

## F

**`format_value`** — The single presentation seam on a capability. Resolves `output_format` to a string rendering; rules never read `output_format`. See [Contracts](concepts/contracts/) and `paxman/capabilities/<Name>/capability.py`.

**Frozen** — Capability contracts and domain objects are `@dataclass(frozen=True)` (contracts without `slots`, domain objects with `slots`). They are immutable after construction; the capability registry also freezes after first `canonicalize()`. See [Concepts — Contracts](concepts/contracts/) and `paxman/core/discovery.py`.

---

## G

**Glossary** — This page. For the domain-heavy glossary kept in sync with code, see also `CONTEXT.md` in the repository root.

**Grammar** — Syntax-only recognizer that scans text and emits span-bearing `RecognitionMatch` objects (never bare notation). Declares `name` (`{format}_recognition`) and `semantics` (meaning id). See [Concepts — Pipeline](concepts/pipeline/) and `paxman/core/domain.py`.

**GrammarRule** — A `(capability_name, grammar_name)` reference pairing. See `paxman/core/domain.py`.

---

## H

**Historical** — Opt-in temporal coverage (e.g. `Country(include_historical=True)` for ISO 3166-3 formerly-used names). Gated via `requires_features` or contract flags; `year` also filters by `publication_year`. See [Contracts](concepts/contracts/).

---

## I

**IANA** — Internet Assigned Numbers Authority. Authority for the IANA Language Subtag Registry (Rolling File-Date 2026-08-08) cited by Language. See [Citations](citations/).

**IBAN** — International Bank Account Number (ISO 13616-1:2020). Paxman capability with one grammar + one rule. See [Citations](citations/).

**ISBN** — International Standard Book Number (ISO 2108:2017, plus ISBN Users' Manual and Range Message). Paxman capability. See [Citations](citations/).

**ISSN** — International Standard Serial Number (ISO 3297:2022). Paxman capability. See [Citations](citations/).

**IETF** — Internet Engineering Task Force. Authority for RFC 5322, RFC 6761, RFC 791, RFC 5952, RFC 3966, BCP 47 RFC 5646. See [Citations](citations/).

**INVALID** — A `Resolution` status. Recognition found a match, but no rule validated it. Distinct from `MISSING` (nothing recognized). See [Execution Result](concepts/execution-result/) and [Pipeline](concepts/pipeline/).

**IP** — Paxman capability for IPv4 (RFC 791) and IPv6 (RFC 5952). See [Capabilities](capabilities/).

**ISO** — International Organization for Standardization. Authority for ISO 9362, 27729, 3166, 4217, 8601, 2108, 13616-1, 639-*, 80000-1, etc. See [Citations](citations/).

**ITU-T** — International Telecommunication Union — Telecommunication Standardization Sector. Authority for E.164 (Phone). See [Citations](citations/).

---

## L

**Language** — Paxman capability for language tags (ISO 639-*, BCP 47, IANA Registry, CLDR display names). See [Capabilities](capabilities/).

**Lifecycle** — Stage of a specification (`"active"` for all shipped provenance; no deprecated shipped rules yet). Field `Provenance.lifecycle`. See [Provenance](concepts/provenance/).

---

## M

**MISSING** — A `Resolution` status. No grammar recognized the input (consider toggling an `include_*` flag). Distinct from `INVALID`. See [Execution Result](concepts/execution-result/).

**Money** — Paxman capability for amounts paired with currency identifiers (ISO 4217 + CLDR). See [Capabilities](capabilities/).

**MultipleMentionsError** — Exception raised when one `canonicalize()` call contains two non-overlapping mentions that resolve to different values. Caller must split first (see Segmentation Recipe) or use `paxman.scan()`. See [Pipeline](concepts/pipeline/) and [API Reference](api-reference/).

---

## N

**NANPA** — North American Numbering Plan Administrator. Authority for the NANP registry cited by Phone. See [Citations](citations/).

**Notation** — Capability-defined intermediate shape (e.g. `EmailNotation(local_part, domain_part)`, `CountryNotation(shape, value)`, `SIUnitNotation(text, shape)`). Produced by grammars, consumed by rules. Internal — not part of the public API. See `CONTEXT.md` "Notation" section and per-capability `notation.py`.

---

## O

**ORCID** — Open Researcher and Contributor ID (ISO 27729:2024). Paxman capability. See [Citations](citations/).

**Output format** — Presentation choice per capability (e.g. `Country` `alpha2`/`alpha3`/`numeric`/`name`, `ISBN` `isbn13`/`hyphenated`, `Phone` `e164`/`rfc3966`/`national`). Default via `DEFAULT_OUTPUT_FORMAT`; alternatives via `OFFERED_OUTPUT_FORMATS`; validation never reads it. See [Contracts](concepts/contracts/) and [API Reference](api-reference/).

---

## P

**Phone** — Paxman capability for telephone numbers (E.164, RFC 3966, NANP). See [Capabilities](capabilities/).

**Pinned / Excluded rules** — Contract filters for validation. `pinned_rules` (when not `None`) runs only those rules; `excluded_rules` skips named rules. Stale names raise `ContractError`. See [Contracts](concepts/contracts/).

**Pipeline** — The three-stage execution inside `canonicalize()`: **Recognition → Validation → Resolution** (rendering via `format_value` after resolution on `SUCCESS`). See [Concepts — Pipeline](concepts/pipeline/).

**Provenance** — The authority citation on every `Candidate`. Fields: `authority`, `specification_name`, `kind`, `reference_url`, `version`, `lifecycle`, `publication_year`; the section lives on `candidate.validation_rule`. See [Concepts — Provenance](concepts/provenance/) and [Citations](citations/).

**Publication year** — Integer year on both `Provenance.publication_year` and contract temporal filtering (`contract.year` keeps only rules with `publication_year <= year`). See [Contracts](concepts/contracts/) and [Migration](migration/).

---

## R

**Recognition** — Stage 1 of the pipeline: grammars scan for syntactic patterns and emit `RecognitionMatch`es. Pure syntax — sanctions ordering, never validation. See [Pipeline](concepts/pipeline/).

**RecognitionMatch / RecognizedRep** — Span-bearing match types. `RecognitionMatch` is what a `Grammar.recognize()` returns; `RecognizedRep` adds contract and `GrammarRule` context for validation. Both carry half-open `[start, end)` and `raw_text` with `len(raw_text) == end - start`. See `paxman/core/domain.py`.

**Registry** — Module-level capability map in `paxman/core/discovery.py`. Populated via `register_all_shipped()` or `register_capability()` from one thread before first `canonicalize()`; then frozen. See [Concepts — Capabilities](concepts/capabilities/) and [API Reference](api-reference/).

**Resolution** — Enum: `MISSING` | `INVALID` | `SUCCESS` | `AMBIGUOUS`. The `status` field on `ExecutionResult`. See [Execution Result](concepts/execution-result/).

**Rule (Validation Rule)** — Spec-backed validator. Declares `name` (`Section X.Y.Z-...`), `strategy` (`REGEX`/`LOOKUP_TABLE`/`PARSER`), `provenance`, `citation`, `target_semantics`, `requires_features`; implements `matches()`/`normalize()`. One publication per file. See `CONTEXT.md` "Rule Structure" and `paxman/core/domain.py`.

**RuleStrategy** — `REGEX` | `LOOKUP_TABLE` | `PARSER`. See `paxman/core/domain.py`.

---

## S

**Scan / `paxman.scan()`** — Batch API: one `ScanContext` substrate pass, per-capability `mentions` dict. Honest F1 path for prose after the 0.2.0 Recognition Kernel (replaces silent wins on multi-mention inputs). Supports `suppress_common_words` per contract via `COMMON_WORDS` (67). See [API Reference](api-reference/) and [Migration](migration/).

**Mention** — A maximal cluster of recognitions for one logical mention. `span` is the covering interval, `grammar` the first grammar in total order, `notation` its notation, optional `candidates`. Produced by `scan()`; also traceable via `Candidate.span`. See `paxman/core/domain.py`.

**ScanContext** — Kernel substrate that lazily builds word spans and normalized views (`ScanContext`/`MatcherSpec`/`engine_loop` in `paxman/core/grammar/`). Shared across `scan()` contracts. See `paxman/core` knowledge base and ADR-0009.

**Segmentation** — Caller-owned split-then-canonicalize loop for text with multiple entities; the `scan()` API exposes the substrate for it. See `docs/recipes/segmentation.md`.

**Semantics (`target_semantics` / `Grammar.semantics`)** — Meaning id a grammar's notations carry (identity id by default; shared ids coalesce same-meaning grammars, e.g. Email's standard + obfuscated grammars both declare `rfc5322_addr_spec`). Rules declare `target_semantics` to claim which grammars' output they judge. See `CONTEXT.md`.

**SI Unit** — Paxman capability for SI unit expressions (BIPM SI Brochure, ISO 80000-1). Canonical form is case-meaningful (`K` vs `k`). See [Capabilities](capabilities/).

**Single-value invariant** — Engine invariant: `canonicalize()` expects one mention per call; two non-overlapping mentions with different canonical values raise `MultipleMentionsError`. Grammars set `single_value=True` to opt in. See [Pipeline](concepts/pipeline/).

**Span** — Half-open `[start, end)` character range into the original input, with `len(raw_text) == end - start`. On `SUCCESS` the `ExecutionResult.span` is the resolved mention; on other statuses it is `None` (use `candidate.span`). See [Execution Result](concepts/execution-result/).

**SUCCESS** — A `Resolution` status. Exactly one distinct canonical value survived validation and dedup. `canonicalized_value` is `str` and `span` is set. See [Execution Result](concepts/execution-result/).

**Suppress common words** — `contract.suppress_common_words` (`bool`, default `False`) + `COMMON_WORDS` (`frozenset[str]`, 67) + `matcher.suppressible`. When `True`, word-bounded short-code hits whose lowercased span is in the table are suppressed at recognition (provenance-neutral). See [Migration](migration/) §16 and `paxman/core/grammar/`.

---

## T

**Target semantics** — See **Semantics**.

**Temporal filtering (`year`)** — Contract field `year: int | None` that keeps only rules with `publication_year <= year`. Use with a pinned `paxman` version and `version_stamp` for reproducibility. See [Contracts](concepts/contracts/) and [Migration](migration/).

---

## U

**URL** — Paxman capability for absolute URIs/IRIs (WHATWG URL Standard). See [Capabilities](capabilities/).

**Unicode / Unicode CLDR** — For Paxman provenance, `"Unicode"` (Country CLDR v45) and `"Unicode CLDR"` (Currency/Money/CLDR Language Display Names) both denote the Unicode CLDR project. See [Citations](citations/).

---

## V

**VersionStamp** — `ExecutionResult.version_stamp`: `.paxman_version` (library version from `pyproject.toml`) and `.recognition_revision` (hash of compiled matcher set + snapshot SHAs, ADR-0009 §13; `"0"` before registry freeze). See [Execution Result](concepts/execution-result/) and [Migration](migration/).

**Validation** — Stage 2 of the pipeline: rules check each recognition against their spec and emit `Candidate`s. Gated by `pinned_rules`/`excluded_rules`/`year`/`requires_features`. See [Pipeline](concepts/pipeline/).

---

## W

**WHATWG** — Web Hypertext Application Technology Working Group. Authority for the URL Standard (Living Standard) cited by URL. See [Citations](citations/).

**Word-bounded / `BoundarySpec.WORD`** — Kernel word-boundary guard for short-code matchers (required for `suppressible` matchers). See `paxman/core/grammar/boundary_spec.py`.

---

## See also

- [Provenance](concepts/provenance/) — what "authoritative" means how to cite it
- [Citations](citations/) — the full grouped bibliography
- [Concepts](concepts/) — the seven-concept hub (diagram + reading order)
- [Capabilities](capabilities/) — per-capability guides (recognized forms, output formats, contract flags, provenance)
- [Pipeline](concepts/pipeline/) — recognition → validation → resolution
- [API Reference](api-reference/) — registration, `canonicalize()`/`scan()` signatures, contract table, error hierarchy
- `CONTEXT.md` (repo root) — domain glossary kept in sync with code (Notation shapes, capability table, rule structure)
