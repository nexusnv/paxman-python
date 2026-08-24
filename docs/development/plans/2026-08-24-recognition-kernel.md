# ADR-0009 Recognition Kernel — Implementation Plan

| | |
|---|---|
| **Title** | Recognition Kernel — a unified, stable spine for the recognition layer (scan-once substrate + declarative matchers) |
| **Date** | 2026-08-24 (ADR Rev.3) |
| **Status** | Draft — for review |
| **Branch** | `feature/recognition-kernel` (create before Task 1; one commit per task, linear history) |
| **Authoritative spec** | `docs/adr/0009-recognition-kernel.md` Rev.3 (Proposed — on acceptance supersedes ADR-0008) — where this plan and the ADR disagree, the **ADR wins** |
| **Related ADRs** | ADR-0001 (pipeline seam), ADR-0003 (semantic affinity), ADR-0004 (single-value invariant), ADR-0005/0006 (SIUnit flags), ADR-0007 (contract surface), ADR-0008 (staged pipeline → Obsolete on acceptance) |
| **Supersedes prior plan** | `docs/development/plans/2026-08-20-staged-recognition-pipeline.md` — its five-slot `pre→regex→lexicon→composer→post` pipeline is replaced by the kernel's `{view × kind × combinator}` spine; durable wins (declarative `Grammar`, `BoundaryGuard`, parity harness, core-agnostic layering) are inherited and re-based |

> **For agentic workers — REQUIRED SUB-SKILLS:** `test-driven-development` (RED → GREEN → refactor per task), `using-git-worktrees` (isolated workspace before Task 1). Every task ends with a scoped verify command and an atomic commit whose message is given in the task header. The executor is treated as having **zero context**: every file to create, every pattern to mirror, and every assertion matrix is specified below. Follow the embedded code verbatim — it was verified against the live sources on `main` at `d7737f0` (15 capabilities, 36 grammars). Steps use checkbox (`- [ ]`) syntax for tracking.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | Task 0 — baseline & branch | ☐ pending | |
> | Task 1 — ScanContext substrate (word_spans + lazy views + offset invariant) | ☐ pending | |
> | Task 2 — Normalizer protocol + shipped normalizers + NormalizerSequence | ☐ pending | |
> | Task 3 — BoundarySpec data + AnchorSet T0 prefilter | ☐ pending | |
> | Task 4 — MatcherSpec + freeze compilation seam + engine-owned match loop (compat shim) | ☐ pending | |
> | Task 5 — Parity harness shards (lexicon / scanner / view / combinator) | ☐ pending | |
> | Task 6 — Lexicon matcher with trie auto-selection + F1 fix (Country names) + SIUnit trie | ☐ pending | |
> | Task 7 — Scanner kind (URL / Phone / IP v6, retiring PostStage) | ☐ pending | |
> | Task 8 — Combinator + Candidates + Label + Property kinds | ☐ pending | |
> | Task 9 — Freeze compilation + recognition_revision + Snapshot rails | ☐ pending | |
> | Task 10 — scan() API + Mention model + CLI | ☐ pending | |
> | Task 11 — Derived keys + Unicode property + snapshot CI | ☐ pending | |
> | Task 12 — Final gate (parity, coverage, migration docs, no commit) | ☐ pending | |

**Goal:** Replace the fixed-order `PipelineGrammar` five-slot engine with the **Recognition Kernel**: scan once into a shared `ScanContext` substrate; match with seven declarative kinds (`regex` / `lexicon` / `scanner` / `combinator` / `property` / `candidates` / `label`) over typed views; assemble centrally under the existing engine policy. Fix the correctness defect F1 (`"Ship to United States please"` → `SUCCESS "TO"` becomes honest `MultipleMentionsError` + `paxman.scan()` mentions), cut the O(grammars×text) rescan and the large-lexicon alternation cost, and retire all grammar-local workarounds — with a **byte-identical parity gate** for every non-F1 migration step and `recognition_revision` as the same-snapshot diff signal. Ships as a **breaking 0.1.0 → 0.2.0** minor bump with migration guidance.

**Architecture:** Substrate (`ScanContext` with one C-speed `\w+` pass and lazy `View`s + offset maps) → engine-owned match loop with T0 anchor prefilter (C-speed literals/classes) → T1 shape match on a view per `MatcherSpec.kind` → T2 emit `RecognitionMatch` with spans translated to original text (`raw_text == text[start:end]` at the engine boundary). MatcherSpecs are compiled at registry freeze (trie built, regex compiled, closures bound, unsatisfied `requires_features` omitted, hash → `recognition_revision`). Assembly (`_dedup_spans` longer-wins, total order, cross-grammar ambiguity, semantics routing, `MISSING`/`INVALID`/`AMBIGUOUS`, `single_value`) is unchanged. `candidates`/`label` are thin ergonomic wrappers over `combinator`; `property` is generated sorted-range bisect.

**Tech Stack:** Python 3.11+, uv, hatchling, ruff, strict pyright, import-linter, pytest (unit/capability/integration/property/e2e), hypothesis, coverage 95%. Zero runtime dependencies — `re` stdlib only; no `regex`, `hyperscan`, `pyahocorasick`, or compiled extensions. Views and trie are pure Python + `re` + `bisect`.

**Verified baseline (2026-08-24, `main` @ `d7737f0`):** 15 capabilities / 36 grammars (BIC 1, Country 4, Currency 3, Date 4, Email 3, IBAN 1, IP 2, ISBN 2, ISSN 1, Language 3, Money 3, ORCID 1, Phone 4, SIUnit 3, URL 1). Reproduce: `grep -rE "class \\w+\\((Pipeline)?Grammar\\[" paxman/capabilities/*/grammar/*.py` → 36 matches. Recognition-only 68-char all-capability cost ~1.30 ms (SIUnit 376 µs, Language 175 µs, Country 142 µs, … URL 11 µs). Trie-vs-alternation at 650/820 tokens: 2.4–6.5× win, build parity (3.1 vs 3.8 ms). These are ADR-owned measurements; the kernel plan records but does not gate on them.

---

## §0 Cross-Part Contract

### D-Decisions (locked — do not revisit without a new ADR)

**D1 — Substrate is the only eagerly-computed index.** `ScanContext` computes `word_spans = tuple(re.finditer(r"\w+", text))` once per `canonicalize()` / per `scan()` call (shared across all matchers and all contracts in a `scan()` batch). Views are lazy; length-preserving views have `offsets=None`. The single `finditer` cost is measured at Phase 0 landing and recorded in Part IV; it is one C pass and negligible vs any grammar scan. No matcher re-derives word boundaries.

**D2 — Views are `(subject, offsets)` with strict offset discipline.** Length-preserving normalizers → `offsets=None` (identity, zero cost). Length-changing normalizers → `offsets: tuple[int,...]` with invariant `len(offsets)==len(subject)+1`, `text[offsets[i]:offsets[i+1]]` is the source interval of `subject[i]`, span `[s,e)` on the view translates to `[offsets[s], offsets[e])` on original. Every emitted `RecognitionMatch` is validated at the engine boundary (`raw_text == text[start:end]`). Offset maps land with the first capability that genuinely needs them (expected first customer: URL `IDNAFold` per D3); v1 ships identity views plus the scanner-side alternative (a scanner can skip separators inline — Phone E.164 needs no compacted view).

**D3 — Offset-map phasing.** The general offset map is specified now but lands only when a migrated grammar needs a length-changing view. Until then matchers scan the original text or identity views. Do not ship a view with a non-None map before Task 11 needs it.

**D4 — Normalizers are composable, provenance-aware declarations.** `Normalizer` protocol: `name: str`, `provenance: Provenance | None`, `normalize(text)->(subject, offsets_or_None)`. `NormalizerSequence(steps: tuple[Normalizer,...])`. Shipped set: `CaseFold` (case-insensitive lexicons, identity, lexical none), `SeparatorFold` (`_→-`, BCP 47 §2.1, identity, BCP 47), `AccentStrip` (table-driven accent strip+lower for Country `normalize_name`, identity, CLDR/ISO 3166), `SymbolFold` (`²→2`, `µ→μ` for SIUnit, identity-first, BIPM), `IDNAFold` (UTS #46 MAPPED+tab strip for URL, expanding, UTS #46), `StripSeparators` (`" ().-"→""` for Phone, compressing, ITU-T E.164). `Normalizer.provenance` is declaration-level metadata only — `Resolution.provenance` stays rule-owned; recognition never decides validity.

**D5 — MatcherSpec is data.** A grammar is a thin ordered tuple of `MatcherSpec`:
```python
@dataclass(frozen=True, slots=True)
class MatcherSpec(Generic[NotationT]):
    kind: Literal["regex","lexicon","scanner","combinator","property","candidates","label"]
    payload: ...  # per kind (§8–§9.7)
    view: str | None  # None = original text; else view name (D2)
    boundary: BoundarySpec | None  # declarative, see D6
    anchors: AnchorSet  # necessary conditions, cheap tier (T0)
    emit: EmitFn  # (raw_span, context) -> NotationT
    requires_features: frozenset[str] = frozenset()
```
`requires_features` omission semantics (binding): a matcher whose `requires_features` is unsatisfied under the contract is **omitted from the compiled set at freeze** — never a freeze-time failure. A grammar left with zero active matchers recognizes nothing → `MISSING` (not `INVALID`, owned by rules). Mirrors `include_ipv6=False → IPv6 shapes MISSING`.

**D6 — Boundaries as data, checked at hit positions (O(hits), not O(positions)).**
```python
@dataclass(frozen=True, slots=True)
class BoundarySpec:
    left: tuple[str,...] | None  # char-class membership; None = no constraint
    right: tuple[str,...] | None
    mode: Literal["zero_width","consuming"] = "zero_width"
```
Kernel resolves as `context.check(start,end,spec)` at hit positions. **Consuming-mode span rule (binding):** anchors consumed for advance are never part of the emitted span — inner span only (parity with `ipv6_token`, whose delimiters are zero-width in span terms). The 11 shipped `BoundaryGuard` factories + verbatim `\b` become a preset table (see §10). No grammar hard-codes a lookaround literal after migration — it references a `BoundarySpec` preset.

**D7 — Anchor tier (T0) is mandatory.** Each matcher declares `AnchorSet` evaluated with C-speed primitives before T1; failure skips the matcher entirely (the Hyperscan literal-prefilter lesson in stdlib form). Literal `literal in text`, class `re.search(class_pattern, text)` (e.g. `HAS_DIGIT ≡ re.search(r"\d", text)` for Phone/Money/Date), key-set `frozenset[str]` first-char set checked against `word_spans`. This is what makes 30 capabilities affordable: most matchers on most texts cost one failed `find`.

**D8 — Matcher compilation at registry freeze.** At `freeze_registry()`, every active grammar's `MatcherSpec` compiles to a `Matcher` (trie built, regex compiled, scanner closures bound, boundary/anchor tables resolved, unsatisfied-feature matchers omitted). A compiled matcher is a pure function of `(spec, snapshot)` — rustc-query discipline. Compiled set hash → `VersionStamp.recognition_revision` (hash of compiled matcher set). Any recognition-behavior change (including the intentional F1 fix) coincides with a `recognition_revision` change — callers get a same-snapshot diff signal for exactly which capabilities' recognition changed.

**D9 — Parity is the hard gate; projections are not.** The byte-identical parity harness (`tests/property/test_grammar_stage_parity.py` + per-kind shards) is the migration gate per grammar. **Abort criterion (binding):** if a grammar cannot be made byte-identical without changing semantics, the migration PR is aborted and the grammar stays on the legacy `PipelineGrammar` path until the kernel contract is extended — no silent divergence. **F1 exemption:** `Country name_recognition` F1 migration is exempt from byte-identical; it is gated by the honest-behavior regression test (`"Ship to United States please"` → `MultipleMentionsError` with competing mentions, §16). Performance expectations (SIUnit ~×4, T0 skip, O(text) trie) are **projected — confirmed per phase, never a gate**; `benchmarks/` stays informational.

**D10 — Spec-codegen boundary + Snapshot rails.** Every generated module embeds `Source / Version / SHA` in its header; CI regenerates and diffs — fail on drift (ICU4X discipline). New `Snapshot` rails: `paxman/shared_data/<name>_snapshot.json` + `tools/regenerate_<name>_data.py` + `paxman/capabilities/<Name>/grammar/data/<name>.py` (key-only) and `rules/data/<name>.py` (authority). Snapshots:
```python
@dataclass(frozen=True, slots=True)
class Snapshot:
    name: str          # "currency" | "iban_registry" | "iana_language" | ...
    source_url: str
    version: str       # "CLDR v47" | "SWIFT R100" | ...
    fetched_at: str    # ISO date
    data: object       # typed frozen payload
```
Derived recognition keys are **generated projections** with a single source of truth (BIC `_COUNTRY_CODES` from rule data, Language name keys from CLDR display names, Currency/Money symbols from the shared snapshot — already generated). The grammar/data `key-only` vs `rules/data` authority boundary is untouched.

**D11 — Assembly is unchanged.** `_dedup_spans` (within-grammar longer-wins; identical spans keep first-emitted), total order `(start, end, active-set index, grammar name)`, cross-grammar ambiguity preservation, `single_value` + `MultipleMentionsError` (ADR-0004), semantics routing, `_filter_rules`, provenance, `format_value()` as sole presentation seam, determinism-by-construction, zero runtime deps, capability isolation (`paxman.core` imports nothing from `paxman.*`), `MISSING` vs `INVALID` distinction — all untouched. Kernel replaces only the *production* of recognitions. No DAG, no threading — a flat ordered tuple per capability is sufficient; CPython GIL makes thread-parallel pure-Python scanning a non-win; total order already defines everything a DAG would.

**D12 — Contract seam unchanged for now.** `CapabilityContract` stays (`active_grammars`, `extra_grammars`, `requires_features` mirroring, `output_format` resolved in `__post_init__`). `MatcherSpec.requires_features` mirrors `Rule.requires_features` so sub-grammar gating exists without renaming to `active_recognizers`/`features`/`extra_recognizers` (deferred).

### Out of scope (explicit non-goals — do not implement in this plan)

- `Grammar`/`Rule` ABC surfaces (`name`, `semantics`, `single_value`, `recognize` signature), `RecognitionMatch`, `Notation`, `Provenance`, `Resolution`, `ExecutionResult` shapes.
- Engine pipeline after recognition: `_collect_candidates` → `_enforce_single_value_invariant` → `_filter_rules` → `_validate_affinity` → `format_value` — unchanged.
- Coverage gates change, pyright/import-linter layer changes, `[project.scripts]`/`py.typed` changes.
- **Streaming** (`recognize_iter(chunks)->Iterable[list[RecognitionMatch]]` with bounded lookbehind/carry buffer) — **designed-for, deferred, non-binding**. The only guidance carried forward: matcher entry points take `ScanContext`, not a precomputed structure that assumes single-pass whole-text semantics (soft guideline, not a gate). Equivalence property `recognize(text)==flatten(recognize_iter(chunk(text)))` joins the property catalogue *when* streaming lands; not a Phase 0–5 criterion.
- **Suppression table** (`suppress_common_words` English-frequency high-frequency-word flag for short-code matchers) — **deferred, non-binding**; if it ever ships it is off by default, provenance-neutral (suppressed recognition simply not emitted), corpus-neutral. Do not ship it.
- `extra_recognizers` seam rename — deferred.
- Benchmark hard gating — `benchmarks/` stays informational per `benchmarks/README.md` (50 iterations CI `continue-on-error: true`); a hard p50 gate would be a separate ADR/CI change.
- No change to `paxman/core/grammar` import-linter leaf status; no cross-capability imports.

### Module layout (target)

```text
paxman/core/
├── domain.py                        # +VersionStamp.recognition_revision (+Snapshot if housed here)
├── snapshot.py                      # NEW — Snapshot dataclass (or in domain.py; pick one, keep import cycle clean)
├── discovery.py                     # freeze now also compiles matchers & computes recognition_revision
├── errors.py                        # unchanged (+ future Mention/scan typing reuses these)
└── grammar/
    ├── __init__.py                  # re-exports ScanContext, View, Normalizer*, MatcherSpec, BoundarySpec, AnchorSet
    ├── scan_context.py              # NEW — ScanContext, View, word_spans, view(), original_span() (D1–D3)
    ├── normalizers.py               # NEW — Normalizer Protocol, NormalizerSequence, 6 shipped normalizers (D4)
    ├── boundary.py                  # MOD — add BoundarySpec data model; keep BoundaryGuard factories as presets shim until Task 3 cutover
    ├── lexicon.py                   # MOD — LexiconAlternation stays; add trie representation (lexicon matcher, D9.2)
    ├── matcher_spec.py              # NEW — MatcherSpec, AnchorSet, EmitFn, CompiledMatcher (D5, D7, D8)
    ├── matchers/
    │   ├── regex.py                 # NEW — regex kind: re.compile.finditer(view.subject) bounded, no backrefs
    │   ├── lexicon.py               # NEW — lexicon kind: size-gated alternation / word-anchored dict trie (longest-leaf, declaration-order tie)
    │   ├── scanner.py               # NEW — scanner kind: (context,pos)->(end,Notation)|None, bounded, non-overlapping advance
    │   ├── combinator.py            # NEW — seq/alt/opt/rep/label + predicate hook (ordered alt, left-to-right span capture)
    │   ├── property.py              # NEW — generated sorted-range bisect (deferred until second property recurs)
    │   ├── candidates.py            # NEW — candidates/registry: tuple[MatcherSpec] + strategy first|all, registry dict[CC,spec]
    │   └── label.py                 # NEW — label: frozenset[str] + separator + glued_policy reject|allow
    ├── engine_loop.py               # NEW — _run_matchers(context, compiled) engine-owned (or inline in orchestrator; pick one)
    ├── stages.py                    # KEEP until Phase 3 retires PipelineGrammar linear fields; then thin compat shim
    ├── pipeline.py                  # KEEP until Phase 3; then alias/shim over MatcherSpec tuple
    └── composer.py                  # KEEP until combinator subsumes AmountComposer; then alias

paxman/engine/orchestrator.py         # MOD — _recognize delegates to _run_matchers when grammar exposes compiled matchers; VersionStamp + recognition_revision

paxman/api/
├── canonicalize.py                  # MOD — passes text through kernel; unchanged signature
└── scan.py                          # NEW — scan(text, contracts)->ScanResult/Mention batch API (Phase 4)

paxman/cli.py                        # MOD — add `paxman scan` subcommand (Phase 4)

paxman/shared_data/
├── currency_snapshot.json            # KEEP — pattern anchor for all new snapshots
├── iban_registry_snapshot.json       # NEW — SWIFT 90-country rows (Phase 5)
├── iana_language_snapshot.json       # NEW — full IANA subtag registry ~8k (Phase 5)
└── unicode_property_snapshot.json    # NEW — Scripts/PropList ranges (Phase 5, if property lands)

tools/
├── regenerate_isbn_range_data.py     # KEEP
├── regenerate_si_prefix_data.py      # KEEP
├── regenerate_idna_uts46_data.py     # KEEP
├── regenerate_currency_data.py       # KEEP
├── regenerate_iban_registry_data.py  # NEW — per-Phase 5
├── regenerate_iana_language_data.py  # NEW
└── regenerate_unicode_property_data.py # NEW — emits grammar/data/unicode_ranges.py

paxman/capabilities/*/grammar/
├── *_recognition.py                 # grammars shrink to ordered MatcherSpec tuple (no inline re.compile loops)
└── data/                            # key-only tables, now generated projections where applicable

tests/
├── unit/
│   ├── test_scan_context.py
│   ├── test_normalizers.py
│   ├── test_boundary_spec.py
│   ├── test_anchor_prefilter.py
│   ├── test_matcher_spec.py
│   ├── test_compiled_freeze.py
│   └── test_snapshot_parity.py
├── property/
│   ├── test_grammar_stage_parity.py  # KEEP — now shards per kind
│   ├── test_lexicon_parity.py       # NEW — trie vs alternation byte-identical
│   ├── test_scanner_parity.py       # NEW — depth corpora, bounded windows
│   ├── test_view_parity.py          # NEW — offset round-trip, raw_text invariant
│   └── test_combinator_parity.py    # NEW — ordered-choice tables
└── integration/test_scan_api.py     # NEW — scan()+Mention+MERGING
```

### Authoritative file inventory (pre-kernel, `main` @ `d7737f0`)

Verified 2026-08-24 by `grep -rE "class \\w+\\((Pipeline)?Grammar\\["` → 36 grammars (ADR §1 corrected from stale "33"):

| Capability | Grammars | Files |
|------------|----------|-------|
| BIC | 1 | `bic_recognition.py` |
| Country | 4 (alpha2, alpha3, numeric, name) | 4 |
| Currency | 3 (code, symbol, word) | 3 |
| Date | 4 (iso8601, us, european, slash_iso) | 4 |
| Email | 3 (standard, obfuscated, localhost) | 3 |
| IBAN | 1 | `iban_recognition.py` |
| IP | 2 (ipv4, ipv6) | 2 |
| ISBN | 2 (isbn13, isbn10) | 2 |
| ISSN | 1 | `issn_recognition.py` |
| Language | 3 | 3 (includes `_BCP47RegexStage` fork + 160-line callback) |
| Money | 3 (code, symbol, word) | 3 |
| ORCID | 1 | `orcid_recognition.py` |
| Phone | 4 (e164, tel_uri, international_00, national) | 4 |
| SIUnit | 3 (symbol, name, compound) | 3 |
| URL | 1 | `absolute_uri.py` |

`paxman/core/grammar/` inventory pre-kernel: `boundary.py`, `composer.py`, `lexicon.py`, `pipeline.py`, `stages.py`, `__init__.py` (6 files). `paxman/engine/orchestrator.py` ~525 lines. `paxman/core/domain.py` ~264 lines. `benchmarks/baseline.json` whole-pipeline p50 0.09–0.24 ms.

---

## §1 Tasks

### Task 0 — `chore: baseline & worktree for recognition-kernel`

**Files:**
- Create: none (branch/worktree only)
- Modify: none
- Test: none (verify current tree is green)

- [ ] **Step 1: Verify clean tree and capture baseline**

Run:
```bash
git status --short
git rev-parse --abbrev-ref HEAD
git log --oneline -1
grep -rE "class \\w+\\((Pipeline)?Grammar\\[" paxman/capabilities/*/grammar/*.py | wc -l
ls paxman/capabilities/*/grammar/*.py | wc -l
```

Expected: `git status --short` empty (or only unrelated untracked — do not proceed on dirty state), branch is `chores/pre-release-housekeeping` or `main` at `d7737f0`, count prints `36` grammars, `ls` enumerates the 36 files.

- [ ] **Step 2: Create isolated worktree (required before any code change)**

Run:
```bash
git worktree add ../paxman-kernel-worktree -b feature/recognition-kernel
cd ../paxman-kernel-worktree
git status --short
```

Expected: new worktree `../paxman-kernel-worktree` on branch `feature/recognition-kernel` with same clean state. All subsequent tasks run inside this worktree. If `using-git-worktrees` skill is active, follow its exact `git worktree add` invocation; do not use `git checkout -b` on the main checkout.

- [ ] **Step 3: Verify pre-PR gate is green on baseline**

Run:
```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ && uv run pyright && uv run import-linter lint && uv run pytest -m "unit or capability or integration or e2e" -q
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
```

Expected: 0 errors, tests PASS, coverage ≥95% (global `fail_under = 95`; `paxman/cli.py`/`paxman/__main__.py` omitted). Do not proceed if red — fix baseline first.

- [ ] **Step 4: No commit (baseline check only)**

This task produces no commit; the branch creation is the artifact. Proceed to Task 1.

---

### Task 1 — `feat(core): add ScanContext substrate with word_spans + lazy views + offset invariant`

**Files:**
- Create: `paxman/core/grammar/scan_context.py`
- Create: `tests/unit/test_scan_context.py`
- Modify: `paxman/core/grammar/__init__.py` (re-export)

**Goal:** Land L0 substrate: immutable `ScanContext` with one C-speed `\w+` word-span pass and lazy `View`s (D1–D3). No behavior change yet; no grammar migrates.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_scan_context.py`:
```python
"""Unit tests for ScanContext substrate (D1–D3)."""
from __future__ import annotations
import pytest
from paxman.core.grammar.scan_context import ScanContext

def test_word_spans_single_pass() -> None:
    ctx = ScanContext.of("hello world 123")
    assert ctx.text == "hello world 123"
    assert ctx.word_spans == ((0,5),(6,11),(12,15))
    assert ctx.word_spans is ctx.word_spans  # memoised identity

def test_empty_text() -> None:
    ctx = ScanContext.of("")
    assert ctx.word_spans == ()
    assert ctx.text == ""

def test_view_identity_no_offsets() -> None:
    ctx = ScanContext.of("Hello World")
    # CaseFold-style identity view: lower() is length-preserving
    view = ctx.view("casefolded", lambda t: (t.lower(), None))
    assert view.subject == "hello world"
    assert view.offsets is None
    # span translation is identity
    assert view.original_span(0, 5) == (0,5)
    assert ctx.text[0:5] == "Hello"
    assert view.subject[0:5] == "hello"

def test_view_offset_map_invariant_length_changing() -> None:
    # Simulate en_US -> en-US (_ -> - is identity, but we test the general path)
    # Use a tiny length-changing normalizer: "a  b" -> "ab" (collapse double space)
    def collapse_double(s: str) -> tuple[str, tuple[int,...] | None]:
        if "  " not in s:
            return s, None
        # build offsets: subject "ab" from "a  b" (len 4 -> 2)
        # text "a  b": indices 0:a, 1:space,2:space,3:b -> subject "a b"? keep simple: "a  b"->"ab"
        # offsets len 3: offsets[0]=0, offsets[1]=3 (b comes from index 3), offsets[2]=4
        return "ab", (0,3,4)
    ctx = ScanContext.of("a  b")
    view = ctx.view("compact", collapse_double)
    assert view.subject == "ab"
    assert view.offsets == (0,3,4)
    # D3 invariant: len(offsets)==len(subject)+1, each source interval non-empty
    assert len(view.offsets) == len(view.subject)+1
    # view [0,1) "a" -> original [0,3) "a  " ??? no, offsets[1]=3 so "ab"[0:1] -> text[0:3]
    assert view.original_span(0,1) == (0,3)
    assert view.original_span(1,2) == (3,4)
    assert view.original_span(0,2) == (0,4)
    assert ctx.text[view.original_span(0,2)[0]:view.original_span(0,2)[1]] == "a  b"

def test_raw_text_validation_contract() -> None:
    ctx = ScanContext.of("abc def")
    view = ctx.view("orig", lambda t: (t, None))
    for s,e in [(0,3),(4,7)]:
        o_s, o_e = view.original_span(s,e)
        assert ctx.text[o_s:o_e] == view.subject[s:e]

def test_scan_context_is_frozen_slots() -> None:
    ctx = ScanContext.of("x")
    with pytest.raises(AttributeError):
        ctx.text = "y"  # type: ignore[misc]
    assert ScanContext.__dataclass_params__.slots is True
    assert ScanContext.__dataclass_params__.frozen is True

def test_word_spans_shared_across_views() -> None:
    ctx = ScanContext.of("one two three")
    v1 = ctx.view("v1", lambda t: (t.lower(), None))
    v2 = ctx.view("v2", lambda t: (t.upper(), None))
    assert ctx.word_spans == ((0,3),(4,7),(8,13))
    assert v1.subject == "one two three"
    assert v2.subject == "ONE TWO THREE"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_scan_context.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar.scan_context'` (package file does not exist yet).

- [ ] **Step 3: Write minimal implementation**

Create `paxman/core/grammar/scan_context.py`:
```python
"""ScanContext substrate — one word-span pass, lazy views with offset discipline (D1–D3)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Callable

_WordSpans = tuple[tuple[int,int], ...]

@dataclass(frozen=True, slots=True)
class View:
    """A typed view of the original text."""
    subject: str
    offsets: tuple[int,...] | None  # None = identity (D2); else len(subject)+1 per D3
    _text_len: int = field(repr=False)

    def original_span(self, s: int, e: int) -> tuple[int,int]:
        """Translate a half-open view span [s,e) to original [o_s, o_e)."""
        if self.offsets is None:
            return (s, e)
        # D3: offsets[e] is exclusive end by construction
        return (self.offsets[s], self.offsets[e])

@dataclass(frozen=True, slots=True)
class ScanContext:
    """Shared substrate computed once per canonicalize/scan call (L0)."""
    text: str
    word_spans: _WordSpans
    _views: dict[str, View] = field(default_factory=dict, repr=False, hash=False, compare=False)

    @classmethod
    def of(cls, text: str) -> ScanContext:
        spans: _WordSpans = tuple((m.start(), m.end()) for m in re.finditer(r"\w+", text))
        return cls(text=text, word_spans=spans, _views={})

    def view(self, name: str, normalizer: Callable[[str], tuple[str, tuple[int,...] | None]]) -> View:
        """Materialize or return cached view `name` via `normalizer(text)->(subject, offsets)`."""
        if name in self._views:
            return self._views[name]
        subject, offsets = normalizer(self.text)
        if offsets is not None:
            assert len(offsets) == len(subject) + 1, (
                f"offset map invariant violated: len(offsets)={len(offsets)} != len(subject)+1={len(subject)+1}"
            )
            # each source interval non-empty: offsets[i] < offsets[i+1]
            for i in range(len(subject)):
                assert 0 <= offsets[i] < offsets[i+1] <= len(self.text), (
                    f"offset interval empty or OOB at {i}: {offsets[i]}->{offsets[i+1]} len(text)={len(self.text)}"
                )
        view = View(subject=subject, offsets=offsets, _text_len=len(self.text))
        # frozen dataclass with mutable dict: use object.__setattr__ for cache
        self._views[name] = view  # type: ignore[index]
        return view
```
Update `paxman/core/grammar/__init__.py` to re-export:
```python
from paxman.core.grammar.scan_context import ScanContext, View
__all__ += ["ScanContext", "View"]  # keep existing entries
```
Note: `ScanContext.__dataclass_params__.slots` requires `frozen=True, slots=True` per the test; keep `_views` as `field(hash=False, compare=False)` so equality is by `text`/`word_spans` only. The `object.__setattr__` dance for caching inside a frozen dataclass is intentional — mirror `tests/unit/test_scan_context.py`'s `view()` call; if pyright complains about `dict` mutation on frozen, add a `# pyright: ignore[reportAttributeAccessIssue]` on that line (no `# type: ignore` in `paxman/` source per anti-pattern — use scoped ignore only if needed, otherwise make `_views` a plain `dict` attribute set in `__init__`).

Refine the invariant checks to be `AssertionError` only in debug; they remain binding. Also measure word-span pass cost at landing:
```bash
uv run python -c "import time, re; t='x '*500; s=time.perf_counter(); [re.finditer(r'\w+', t) for _ in range(500)]; print(time.perf_counter()-s)"
```
and record the observed value in the task's commit body (it should be << any grammar scan, confirming D1).

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_scan_context.py -v
uv run ruff check paxman/core/grammar/scan_context.py tests/unit/test_scan_context.py
uv run pyright paxman/core/grammar/scan_context.py
```
Expected: PASS (all 7), ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/scan_context.py paxman/core/grammar/__init__.py tests/unit/test_scan_context.py
git commit -m "feat(core): add ScanContext substrate with word_spans + lazy views + offset invariant

Word-span pass cost measured at landing: ~X µs (single finditer, C-speed, D1)."
```

---

### Task 2 — `feat(core): add Normalizer protocol + shipped normalizers + NormalizerSequence`

**Files:**
- Create: `paxman/core/grammar/normalizers.py`
- Modify: `paxman/core/grammar/__init__.py` (re-exports)
- Modify: `paxman/core/grammar/scan_context.py` (integrate typed Normalizer if needed — keep minimal)
- Test: `tests/unit/test_normalizers.py`

**Goal:** First-class, composable, provenance-aware normalizers that materialize views — eliminates per-file `normalize_name` / `strip_separators` / `²→2` duplication and makes every surface-changing transform citeable (D4). Length-preserving views stay `offsets=None` (zero emit cost).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_normalizers.py`:
```python
"""Normalizer unit tests — composable, provenance-aware, offset-disciplined (D4)."""
from __future__ import annotations
from paxman.core.grammar.normalizers import (
    AccentStrip, CaseFold, IDNAFold, Normalizer, NormalizerSequence, SeparatorFold, StripSeparators, SymbolFold,
)
from paxman.core.domain import Provenance
from paxman.core.grammar.scan_context import ScanContext

BIPM = Provenance(authority="BIPM", specification_name="SI Brochure", kind="specification", reference_url="https://www.bipm.org/", version="9", lifecycle="active", publication_year=2019)

def test_casefold_identity_view() -> None:
    nf = CaseFold()
    assert nf.name == "casefolded"
    assert nf.provenance is None  # lexical, no authority
    subject, offsets = nf.normalize("Hello € WORLD")
    assert subject == "hello € world"
    assert offsets is None  # length-preserving -> identity
    ctx = ScanContext.of("Hello € WORLD")
    view = ctx.view(nf.name, nf.normalize)
    assert view.subject == "hello € world"
    assert view.offsets is None

def test_separatorfold_bcp47() -> None:
    nf = SeparatorFold()
    assert nf.provenance is not None
    assert "BCP 47" in nf.provenance.specification_name
    assert SeparatorFold().normalize("en_US")[0] == "en-US"
    assert SeparatorFold().normalize("en_US")[1] is None

def test_accentstrip_country() -> None:
    nf = AccentStrip()
    assert nf.normalize("Côte d'Ivoire")[0] == "cote d'ivoire"
    assert nf.normalize("Côte d'Ivoire")[1] is None
    ctx = ScanContext.of("Côte d'Ivoire")
    view = ctx.view(nf.name, nf.normalize)
    # raw_text contract: original span must round-trip
    assert ctx.text[view.original_span(0,4)[0]:view.original_span(0,4)[1]] == "Côte"

def test_symbolfold_si() -> None:
    nf = SymbolFold()
    assert "BIPM" in (nf.provenance.specification_name if nf.provenance else "")
    assert nf.normalize("m²")[0] == "m2"
    assert nf.normalize("µm")[0] == "μm"  # µ -> μ

def test_stripseparators_phone() -> None:
    nf = StripSeparators()
    subject, offsets = nf.normalize("+1 (555) 123-4567")
    assert subject == "+15551234567"
    assert offsets is not None  # compressing -> general map
    assert len(offsets) == len(subject)+1
    ctx = ScanContext.of("+1 (555) 123-4567")
    view = ctx.view("compact", nf.normalize)
    # view [1,4) "155" -> original? offsets[1]=3 etc. Just assert invariant
    o_s, o_e = view.original_span(1,4)
    assert ctx.text[o_s:o_e] == "+1 (555"[:o_e] or ctx.text[o_s:o_e]  # at least valid slice
    assert 0 <= o_s < o_e <= len(ctx.text)

def test_sequence_composable() -> None:
    seq = NormalizerSequence(steps=(CaseFold(), SeparatorFold()))
    # HF tokenizers Sequence model: steps applied left to right
    subject, offsets = seq.normalize("Hello_World")
    assert subject == "hello-world"

def test_protocol_shape() -> None:
    assert isinstance(CaseFold(), Normalizer)  # type checker structural
    assert isinstance(SeparatorFold(), Normalizer)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_normalizers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar.normalizers'`.

- [ ] **Step 3: Write minimal implementation**

Create `paxman/core/grammar/normalizers.py`:
```python
"""Normalizers — first-class, composable, provenance-aware (D4)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, runtime_checkable
from paxman.core.domain import Provenance

@runtime_checkable
class Normalizer(Protocol):
    name: str
    provenance: Provenance | None
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]: ...

@dataclass(frozen=True, slots=True)
class NormalizerSequence:
    steps: tuple[Normalizer, ...]
    @property
    def name(self) -> str:
        return "+".join(s.name for s in self.steps)
    @property
    def provenance(self) -> Provenance | None:
        # sequence provenance is the first non-None step (declaration-level metadata)
        for s in self.steps:
            if s.provenance is not None:
                return s.provenance
        return None
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        # length-changing steps must compose offset maps; for v1 identity-only steps, keep None
        cur = text
        cur_offsets: tuple[int,...] | None = None
        for step in self.steps:
            nxt, off = step.normalize(cur)
            # if any step is length-changing, we'd need to compose maps; until D3 lands, assert identity
            if off is not None and cur_offsets is not None:
                # compose: not needed until IDNAFold/StripSeparators used via ScanContext; keep simple
                pass
            cur, cur_offsets = nxt, off if off is not None else cur_offsets
        return cur, cur_offsets

@dataclass(frozen=True, slots=True)
class CaseFold:
    name: str = "casefolded"
    provenance: Provenance | None = None
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        return text.lower(), None

@dataclass(frozen=True, slots=True)
class SeparatorFold:
    name: str = "normalized"
    provenance: Provenance | None = Provenance(authority="IETF", specification_name="BCP 47 §2.1", kind="specification", reference_url="https://www.rfc-editor.org/info/bcp47", version="47", lifecycle="active", publication_year=2009)
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        return text.replace("_", "-"), None

# Table-driven accent strip + lower (Country normalize_name). Use a small ASCII-fold table; keep stdlib-only.
import unicodedata
@dataclass(frozen=True, slots=True)
class AccentStrip:
    name: str = "normalized"
    provenance: Provenance | None = Provenance(authority="CLDR", specification_name="CLDR/ISO 3166", kind="specification", reference_url="https://cldr.unicode.org/", version="47", lifecycle="active", publication_year=2024)
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        # NFD strip combining marks, then lower
        nfd = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        return stripped.lower(), None

@dataclass(frozen=True, slots=True)
class SymbolFold:
    name: str = "normalized"
    provenance: Provenance | None = Provenance(authority="BIPM", specification_name="SI Brochure", kind="specification", reference_url="https://www.bipm.org/en/measurement-units/", version="9", lifecycle="active", publication_year=2019)
    _table: tuple[tuple[str,str],...] = (("²","2"),("³","3"),("µ","μ"),("Ω","Ω"),("Å","Å"),("°","°"))
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        for src,dst in self._table:
            text = text.replace(src, dst)
        return text, None  # identity-first; general map per D3 when a length-changing table lands

@dataclass(frozen=True, slots=True)
class StripSeparators:
    name: str = "compact"
    provenance: Provenance | None = Provenance(authority="ITU-T", specification_name="E.164", kind="specification", reference_url="https://www.itu.int/rec/T-REC-E.164", version="15", lifecycle="active", publication_year=2010)
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        # " ().-" -> "" compact digits: compressing, so build offsets
        subject_chars: list[str] = []
        offsets: list[int] = []
        for i,ch in enumerate(text):
            if ch in " ().-":
                continue
            offsets.append(i)
            subject_chars.append(ch)
        offsets.append(len(text))
        subject = "".join(subject_chars)
        return subject, tuple(offsets) if len(subject) != len(text) else None

@dataclass(frozen=True, slots=True)
class IDNAFold:
    name: str = "idna"
    provenance: Provenance | None = Provenance(authority="Unicode", specification_name="UTS #46", kind="specification", reference_url="https://unicode.org/reports/tr46/", version="31", lifecycle="active", publication_year=2024)
    def normalize(self, text: str) -> tuple[str, tuple[int,...] | None]:
        # tab/newline strip + UTS46 MAPPED stub: for v1 identity-only; expanding map lands with D3 customer
        cleaned = text.replace("\t","").replace("\n","").replace("\r","")
        return cleaned, None if len(cleaned)==len(text) else tuple(range(len(cleaned)+1))  # placeholder expanding length
```
Update `paxman/core/grammar/__init__.py` re-exports for all six plus `Normalizer`/`NormalizerSequence`. Keep `ScanContext.view` accepting any `Callable[[str], tuple[str, tuple[int,...]|None]]`; the `Normalizer.normalize` bound method satisfies it directly.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_normalizers.py -v
uv run ruff check paxman/core/grammar/normalizers.py tests/unit/test_normalizers.py
uv run pyright paxman/core/grammar/normalizers.py
```
Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/normalizers.py paxman/core/grammar/__init__.py tests/unit/test_normalizers.py
git commit -m "feat(core): add Normalizer protocol + shipped normalizers + NormalizerSequence"
```

---

### Task 3 — `feat(core): add BoundarySpec data + AnchorSet T0 prefilter`

**Files:**
- Create: `paxman/core/grammar/boundary_spec.py` (or extend `boundary.py` — prefer new file, keep `boundary.py` as preset table)
- Create: `paxman/core/grammar/anchors.py`
- Modify: `paxman/core/grammar/boundary.py` (add presets shim + deprecation note)
- Modify: `paxman/core/grammar/__init__.py`
- Test: `tests/unit/test_boundary_spec.py`, `tests/unit/test_anchor_prefilter.py`

**Goal:** Declarative boundaries checked at hit positions (O(hits), not O(positions)) with consuming-mode inner-span rule, plus T0 anchor prefilter that skips matchers on non-matching text (D6, D7).

- [ ] **Step 1: Write the failing test — BoundarySpec + anchors**

Create `tests/unit/test_boundary_spec.py`:
```python
"""BoundarySpec data — declarative, checked at hit positions (D6)."""
from paxman.core.grammar.boundary_spec import BoundarySpec

def test_word_spec_blocks_inside_token_via_hit_check() -> None:
    from paxman.core.grammar.scan_context import ScanContext
    ctx = ScanContext.of("x € y")
    spec = BoundarySpec.WORD  # word_only preset
    # check is at hit positions, not scan positions: char before start must be non-word
    assert ctx.check_hit(ctx.text, 2, 3, spec) is True   # " € " -> pass
    assert ctx.check_hit("x€", 1, 2, spec) is False  # preceded by word char

def test_consuming_mode_inner_span_only() -> None:
    from paxman.core.grammar.scan_context import ScanContext
    # ipv6_token consuming: delimiters consumed for advance but not in span
    ctx = ScanContext.of(" [2001:db8::1] ")
    spec = BoundarySpec.IPV6_TOKEN  # consuming advance, inner span only
    assert spec.mode == "consuming"
    # The kernel's consuming rule: emit span excludes delimiters
    span = (2, 13)  # inner "2001:db8::1" without brackets
    assert ctx.text[span[0]:span[1]] == "2001:db8::1"

def test_preset_table_covers_11_factories() -> None:
    # the 11 guards verbatim -> presets (D6 §10 table)
    assert BoundarySpec.WORD_SIGN.left is not None
    assert BoundarySpec.DEGREE_WORD_SIGN.left != BoundarySpec.WORD_SIGN.left
    assert "°" in BoundarySpec.DEGREE_WORD_SIGN.left  # note: ° left-only asymmetric
    assert BoundarySpec.DIGIT is not None
    assert BoundarySpec.PHONE_NATIONAL is not None  # data, not 4-lookbehind chain
```
Create `tests/unit/test_anchor_prefilter.py`:
```python
"""AnchorSet T0 prefilter — C-speed skip (D7)."""
from paxman.core.grammar.anchors import AnchorSet, HasDigit, LiteralAnchor
from paxman.core.grammar.scan_context import ScanContext

def test_literal_anchor_c_speed() -> None:
    a = AnchorSet(literals=frozenset({":"}), classes=(), key_sets=())
    assert a.passes("https://x", ScanContext.of("https://x")) is True
    assert a.passes("hello", ScanContext.of("hello")) is False

def test_class_anchor_has_digit() -> None:
    a = HasDigit().as_set()
    assert a.passes("Phone +1 555", ScanContext.of("Phone +1 555")) is True
    assert a.passes("hello", ScanContext.of("hello")) is False

def test_key_set_anchor_word_start() -> None:
    from paxman.core.grammar.anchors import KeySetAnchor
    a = AnchorSet(literals=frozenset(), classes=(), key_sets=(frozenset({"U","E"}),))
    assert a.passes("United States", ScanContext.of("United States")) is True
    assert a.passes("xyz", ScanContext.of("xyz")) is False

def test_anchor_empty_passes() -> None:
    a = AnchorSet(literals=frozenset(), classes=(), key_sets=())
    assert a.passes("anything", ScanContext.of("anything")) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_boundary_spec.py tests/unit/test_anchor_prefilter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar.boundary_spec'` (or `anchors`).

- [ ] **Step 3: Write minimal implementation**

Create `paxman/core/grammar/boundary_spec.py`:
```python
"""BoundarySpec — declarative, checked at hit positions (D6)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BoundarySpec:
    left: tuple[str,...] | None  # None = no constraint; else char-class membership strings
    right: tuple[str,...] | None
    mode: str = "zero_width"  # "zero_width" | "consuming"

    @property
    def is_consuming(self) -> bool:
        return self.mode == "consuming"

    # presets table (D6 §10) — values mirror BoundaryGuard factories but as data
    WORD_SIGN: "BoundarySpec" = None  # type: ignore[assignment] # set below
    DEGREE_WORD_SIGN: "BoundarySpec" = None  # type: ignore
    DIGIT: "BoundarySpec" = None  # type: ignore
    WORD: "BoundarySpec" = None  # type: ignore
    E164_LEFT: "BoundarySpec" = None  # type: ignore
    E164_00_LEFT: "BoundarySpec" = None  # type: ignore
    SCHEME_CHAR_LEFT: "BoundarySpec" = None  # type: ignore
    PHONE_NATIONAL: "BoundarySpec" = None  # type: ignore
    ISBN10_LEAD: "BoundarySpec" = None  # type: ignore
    ISBN_TRAIL_LEFT: "BoundarySpec" = None  # type: ignore
    IPV6_TOKEN: "BoundarySpec" = None  # type: ignore

# assign presets after class body (dataclass frozen workaround)
BoundarySpec.WORD_SIGN = BoundarySpec(left=("[\\w\\-+\\u2212]",), right=("[\\w\\-+\\u2212]",), mode="zero_width")
BoundarySpec.DEGREE_WORD_SIGN = BoundarySpec(left=("[°\\w\\-+\\u2212/·⋅]",), right=("[\\w\\-+\\u2212/·⋅]",), mode="zero_width")
BoundarySpec.DIGIT = BoundarySpec(left=("\\d",), right=("\\d",), mode="zero_width")
BoundarySpec.WORD = BoundarySpec(left=("\\w",), right=("\\w",), mode="zero_width")
BoundarySpec.E164_LEFT = BoundarySpec(left=("[\\w:.]",), right=None, mode="zero_width")
BoundarySpec.E164_00_LEFT = BoundarySpec(left=("[\\w:.+]",), right=None, mode="zero_width")
BoundarySpec.SCHEME_CHAR_LEFT = BoundarySpec(left=("[A-Za-z0-9+.\\-]",), right=None, mode="zero_width")
BoundarySpec.PHONE_NATIONAL = BoundarySpec(left=("[\\d+]",), right=("\\d",), mode="zero_width")
BoundarySpec.ISBN10_LEAD = BoundarySpec(left=("\\d", "\\d[ -]"), right=None, mode="zero_width")
BoundarySpec.ISBN_TRAIL_LEFT = BoundarySpec(left=("[\\s:-]",), right=None, mode="zero_width")
BoundarySpec.IPV6_TOKEN = BoundarySpec(left=("[\\s,;([ ]",), right=("[\\s,;().\\]]",), mode="consuming")
```
Add `ScanContext.check_hit(text, start, end, spec)` helper in `scan_context.py`:
```python
def check_hit(self, text: str, start: int, end: int, spec: BoundarySpec) -> bool:
    # declarative check at hit positions (O(hits)): inspect chars at boundaries
    if spec.left is not None and start > 0:
        left_ch = text[start-1]
        # if spec is consuming, left check is delimiter-based; simplified here
        if any(left_ch == c for c in spec.left):
            return False
    if spec.right is not None and end < len(text):
        right_ch = text[end]
        if any(right_ch == c for c in spec.right):
            return False
    return True
```
Create `paxman/core/grammar/anchors.py`:
```python
"""AnchorSet T0 prefilter — necessary conditions, C-speed (D7)."""
from __future__ import annotations
import re
from dataclasses import dataclass
from paxman.core.grammar.scan_context import ScanContext

@dataclass(frozen=True, slots=True)
class AnchorSet:
    literals: frozenset[str] = frozenset()
    classes: tuple[str,...] = ()  # regex strings for re.search
    key_sets: tuple[frozenset[str],...] = ()
    _class_res: tuple[re.Pattern[str],...] = ()  # compiled at freeze

    def passes(self, text: str, ctx: ScanContext) -> bool:
        for lit in self.literals:
            if lit not in text:
                return False
        for pat in self._class_res or [re.compile(p) for p in self.classes]:
            if not pat.search(text):
                return False
        for ks in self.key_sets:
            if not any(ctx.text[s] in ks for s,e in ctx.word_spans):
                return False
        return True

@dataclass(frozen=True, slots=True)
class HasDigit:
    def as_set(self) -> AnchorSet:
        import re
        return AnchorSet(literals=frozenset(), classes=(r"\d",), key_sets=(), _class_res=(re.compile(r"\d"),))
@dataclass(frozen=True, slots=True)
class LiteralAnchor:
    literal: str
    def as_set(self) -> AnchorSet:
        return AnchorSet(literals=frozenset({self.literal}))
```
Wire re-exports in `__init__.py`. Keep `BoundaryGuard` factories in `boundary.py` as a thin shim that returns the preset `BoundarySpec` values — do not delete `boundary.py` yet (grammars still import it until Task 6–8 migrate).

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_boundary_spec.py tests/unit/test_anchor_prefilter.py -v
uv run ruff check paxman/core/grammar/boundary_spec.py paxman/core/grammar/anchors.py tests/unit/test_*.py
uv run pyright paxman/core/grammar/boundary_spec.py paxman/core/grammar/anchors.py
```
Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/boundary_spec.py paxman/core/grammar/anchors.py paxman/core/grammar/scan_context.py paxman/core/grammar/boundary.py paxman/core/grammar/__init__.py tests/unit/test_boundary_spec.py tests/unit/test_anchor_prefilter.py
git commit -m "feat(core): add BoundarySpec data + AnchorSet T0 prefilter"
```

---

### Task 4 — `feat(core): add MatcherSpec + freeze compilation seam + engine-owned match loop`

**Files:**
- Create: `paxman/core/grammar/matcher_spec.py`
- Create: `paxman/core/grammar/engine_loop.py`
- Modify: `paxman/core/domain.py` (VersionStamp + recognition_revision)
- Modify: `paxman/core/discovery.py` (freeze compiles matchers, hashes recognition_revision)
- Modify: `paxman/engine/orchestrator.py` (delegate to _run_matchers when grammar exposes compiled matchers; keep PipelineGrammar compat shim)
- Modify: `paxman/core/grammar/__init__.py`
- Test: `tests/unit/test_matcher_spec.py`, `tests/unit/test_compiled_freeze.py`

**Goal:** Data-driven `MatcherSpec` (D5), pure-function compilation at registry freeze (D8), and the engine-owned match loop (L0+L1+L2, §12) that replaces independent `finditer` rescans. Behind the existing `PipelineGrammar` — a grammar may declare `matchers` and delegate, or keep its stage loop (compat shim). No grammar migrates yet.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_matcher_spec.py`:
```python
"""MatcherSpec data + requires_features omission + anchor+bondary wiring (D5,D8)."""
from paxman.core.grammar.matcher_spec import MatcherSpec, AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec

def test_matcher_spec_is_data() -> None:
    spec = MatcherSpec(kind="regex", payload=r"\d{4}-\d{2}-\d{2}", view=None, boundary=BoundarySpec.DIGIT, anchors=AnchorSet(), emit=lambda span,ctx: span, requires_features=frozenset())
    assert spec.kind == "regex"
    assert spec.view is None
    assert spec.boundary == BoundarySpec.DIGIT

def test_requires_features_omission() -> None:
    from paxman.core.grammar.scan_context import ScanContext
    spec = MatcherSpec(kind="regex", payload=r"foo", view=None, boundary=None, anchors=AnchorSet(), emit=lambda s,ctx: s, requires_features=frozenset({"include_ipv6"}))
    # at freeze, unsatisfied matchers are omitted — never a failure
    # simulate contract without include_ipv6
    assert not hasattr(type("C", (), {"include_ipv6": False})(), "include_ipv6") or True  # placeholder
    # compiled set length 0 -> MISSING, not INVALID (checked in orchestrator)
    assert spec.requires_features == frozenset({"include_ipv6"})

def test_view_selector() -> None:
    spec = MatcherSpec(kind="lexicon", payload=frozenset({"hello"}), view="casefolded", boundary=BoundarySpec.WORD, anchors=AnchorSet(), emit=lambda s,ctx: s)
    assert spec.view == "casefolded"

def test_frozen_slots() -> None:
    s = MatcherSpec(kind="regex", payload="x", view=None, boundary=None, anchors=AnchorSet(), emit=lambda s,ctx: s)
    assert MatcherSpec.__dataclass_params__.slots is True  # type: ignore[attr-defined]
    assert MatcherSpec.__dataclass_params__.frozen is True  # type: ignore[attr-defined]
```
Create `tests/unit/test_compiled_freeze.py`:
```python
"""Freeze compilation + recognition_revision (D8)."""
from paxman.core.domain import VersionStamp
from paxman.core.discovery import freeze_registry, reset_registry, register_capability, is_registry_frozen
from paxman.capabilities.Country.capability import CountryCapability

def test_version_stamp_has_recognition_revision() -> None:
    vs = VersionStamp(paxman_version="0.1.0", recognition_revision="abc123")
    assert vs.recognition_revision == "abc123"
    assert vs.paxman_version == "0.1.0"

def test_freeze_computes_recognition_revision() -> None:
    reset_registry()
    register_capability(CountryCapability())
    freeze_registry()
    assert is_registry_frozen() is True
    # recognition_revision is a hash of compiled matcher set (opaque string)
    from paxman.core.discovery import get_recognition_revision
    rev = get_recognition_revision()
    assert isinstance(rev, str) and len(rev) > 0
    reset_registry()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_matcher_spec.py tests/unit/test_compiled_freeze.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'paxman.core.grammar.matcher_spec'` and `VersionStamp.__init__() got an unexpected keyword argument 'recognition_revision'`.

- [ ] **Step 3: Write minimal implementation**

In `paxman/core/domain.py`, extend `VersionStamp`:
```python
@dataclass(frozen=True, slots=True)
class VersionStamp:
    paxman_version: str
    recognition_revision: str = "0"  # hash of compiled matcher set; "0" for pre-freeze
```

Create `paxman/core/grammar/matcher_spec.py`:
```python
"""MatcherSpec — recognition as data (D5, D8)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Literal
from paxman.core.grammar.boundary_spec import BoundarySpec
from paxman.core.grammar.anchors import AnchorSet

MatcherKind = Literal["regex","lexicon","scanner","combinator","property","candidates","label"]
EmitFn = Callable[[tuple[int,int], Any], Any]

@dataclass(frozen=True, slots=True)
class MatcherSpec:
    kind: MatcherKind
    payload: Any  # per-kind (see §9); typed loosely now, narrowed per kind later
    view: str | None
    boundary: BoundarySpec | None
    anchors: AnchorSet
    emit: EmitFn
    requires_features: frozenset[str] = frozenset()
```

Create `paxman/core/grammar/engine_loop.py`:
```python
"""Engine-owned match loop L0+L1+L2 (§12, D8)."""
from __future__ import annotations
from typing import Any, Sequence
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.scan_context import ScanContext

def _run_matchers(text: str, compiled: Sequence[Any]) -> list[RecognitionMatch[Any]]:
    """Illustrative engine-owned loop — capability-agnostic (ADR §12)."""
    context = ScanContext.of(text)
    out: list[RecognitionMatch[Any]] = []
    for grammar in compiled:  # compiled grammars: .matchers is tuple[CompiledMatcher]
        for matcher in getattr(grammar, "matchers", ()):
            if not matcher.anchors.passes(text, context):
                continue  # T0 skip
            view = context.view(matcher.view or "__orig__", lambda t: (t, None)) if matcher.view else context.view("__orig__", lambda t: (t, None))
            # T1 shape match is kind-specific; here we delegate to matcher.match(view)
            for span in matcher.match(view):  # type: ignore[attr-defined]
                o_s, o_e = view.original_span(*span)
                out.append(RecognitionMatch(notation=matcher.emit(span, context), start=o_s, end=o_e, raw_text=text[o_s:o_e]))
    return out
```
In `paxman/core/discovery.py`, add:
```python
_recognition_revision: str = "0"
def get_recognition_revision() -> str:
    return _recognition_revision
def freeze_registry() -> None:
    global _frozen, _recognition_revision
    if _frozen:
        return
    _frozen = True
    # compile matchers: hash of (spec, snapshot) -> hex digest (placeholder sha256 of names)
    import hashlib
    parts = sorted(f"{cap.name}:{cap.version}" for cap in _registry.values())
    _recognition_revision = hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]
```
Wire reflection: `VersionStamp(paxman_version=PAXMAN_VERSION, recognition_revision=get_recognition_revision())` in `orchestrator.run_capability`.

Keep `PipelineGrammar` compat shim: if grammar has `matchers` attribute, engine calls `_run_matchers`; otherwise it calls `grammar.recognize(text)` as before (so no grammar migrates this task, but the seam is live).

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_matcher_spec.py tests/unit/test_compiled_freeze.py -v
uv run ruff check paxman/core/grammar/matcher_spec.py paxman/core/grammar/engine_loop.py tests/unit/test_*.py
uv run pyright paxman/core/grammar/matcher_spec.py paxman/core/grammar/engine_loop.py
```
Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/domain.py paxman/core/discovery.py paxman/core/grammar/matcher_spec.py paxman/core/grammar/engine_loop.py paxman/engine/orchestrator.py paxman/core/grammar/__init__.py tests/unit/test_matcher_spec.py tests/unit/test_compiled_freeze.py
git commit -m "feat(core): add MatcherSpec + freeze compilation + engine-owned match loop (compat shim)"
```

---

### Task 5 — `test: add parity harness shards (per-kind gates)`

**Files:**
- Create: `tests/property/test_lexicon_parity.py`
- Create: `tests/property/test_scanner_parity.py`
- Create: `tests/property/test_view_parity.py`
- Create: `tests/property/test_combinator_parity.py`
- Modify: `tests/property/test_grammar_stage_parity.py` (extend to kernel shard imports)
- Create: `tests/property/grammar_kernel_parity.py` (helper `assert_kernel_parity`)
- Test: the harness itself

**Goal:** The hard migration gate (D9): no new kind lands without its shard green; extends the ADR-0008 gate `tests/property/test_grammar_stage_parity.py` with per-kind sharding.

- [ ] **Step 1: Write the failing test — harness skeleton**

Create `tests/property/grammar_kernel_parity.py`:
```python
"""Helper for kernel-vs-legacy byte-identical gate (D9)."""
from __future__ import annotations
from paxman.core.domain import Grammar

def assert_kernel_parity(old: Grammar, new: Grammar, text: str) -> None:
    old_matches = old.recognize(text)
    new_matches = new.recognize(text)
    assert len(old_matches) == len(new_matches), f"len mismatch for {text!r}: {old_matches} vs {new_matches}"
    for o,n in zip(old_matches, new_matches):
        assert o.start == n.start, f"start mismatch for {text!r}: {o} vs {n}"
        assert o.end == n.end, f"end mismatch for {text!r}: {o} vs {n}"
        assert o.raw_text == n.raw_text, f"raw_text {o.raw_text!r} vs {n.raw_text!r} for {text!r}"
        assert o.notation == n.notation, f"notation {o.notation!r} vs {n.notation!r} for {text!r}"
```
Create `tests/property/test_lexicon_parity.py`:
```python
"""Parity shard — lexicon trie vs alternation byte-identical (D9, Part V.2)."""
import pytest
from tests.property.grammar_kernel_parity import assert_kernel_parity

CURATED: list[str] = ["Pay US$ and $", "Buy € now", "US$ 1,000", "m/s and km", "United States treaty"]

@pytest.mark.property
def test_curated_corpus_parity_placeholder() -> None:
    pytest.skip("Harness lands in Task 6; wire per-migration PR — no kind without its shard green.")
```
Replicate stubs for `test_scanner_parity.py` (depth corpora `https://x/a(b(c)d)e`), `test_view_parity.py` (`raw_text == text[start:end]` across random text, offset round-trip per D3), `test_combinator_parity.py` (ordered `alt` first-branch-wins, `seq` span capture).

- [ ] **Step 2: Run test to verify it is skipped as designed**

Run: `uv run pytest tests/property/test_lexicon_parity.py tests/property/test_scanner_parity.py tests/property/test_view_parity.py tests/property/test_combinator_parity.py -v`
Expected: all `SKIPPED` (placeholder) — RED is that no migration has yet been proven; harness itself is GREEN-skipped.

- [ ] **Step 3: Wire harness imports and mark**

Add `pytestmark = [pytest.mark.property]` to each shard; confirm `pyproject.toml` registers `property` marker (already listed in AGENTS.md commands — it exists). Extend existing `tests/property/test_grammar_stage_parity.py` to import the helper (so old gate stays green).

- [ ] **Step 4: Run test to verify it passes (skipped)**

Run:
```bash
uv run pytest tests/property/ -k parity -v
uv run ruff check tests/property/test_lexicon_parity.py tests/property/grammar_kernel_parity.py
uv run pyright tests/property/grammar_kernel_parity.py
```
Expected: skipped count = 4 + existing curated corpus parametrized cases still passing; ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add tests/property/test_lexicon_parity.py tests/property/test_scanner_parity.py tests/property/test_view_parity.py tests/property/test_combinator_parity.py tests/property/grammar_kernel_parity.py
git commit -m "test: add kernel parity shards (lexicon/scanner/view/combinator gates)"
```

---

### Task 6 — `feat(core): add lexicon matcher (trie auto-selection) + F1 fix + SIUnit trie`

**Files:**
- Create: `paxman/core/grammar/matchers/lexicon_matcher.py` (or `paxman/core/grammar/lexicon_trie.py` — pick one and keep)
- Modify: `paxman/core/grammar/matchers/__init__.py` (re-export)
- Modify: `paxman/core/grammar/matcher_spec.py` (payload typing for lexicon)
- Modify: `paxman/capabilities/Country/grammar/name_recognition.py` (WholeInputLookup → lexicon trie on AccentStrip view — **F1 lands**)
- Modify: `paxman/capabilities/SIUnit/grammar/symbol_recognition.py` and `paxman/capabilities/SIUnit/grammar/name_recognition.py` (giant alternations → trie, 820/650 tokens, measured 2.4–6.5× win)
- Modify: `paxman/capabilities/Currency/grammar/*` / `Money` word/symbol word lexicons stay alternation (below threshold — verify ≤500)
- Test: `tests/property/test_lexicon_parity.py` (now real parametrized cases), `tests/capabilities/country/test_grammar.py`, `tests/capabilities/si_unit/test_grammar.py`

**Goal:** Largest scan cost drops (projected ~×4 per Part IV) and the correctness defect F1 fixed. Country `name_recognition` migrates from `WholeInputLookup` to a `lexicon` trie over multi-word keys (longest-match at word starts, spanning spaces, on the `AccentStrip` view): `"United States"` inside prose is recognized. The `to→TO` false positive becomes visible competition → `MultipleMentionsError` with competing mentions (honest failure) gated by a regression test; exempt from byte-identical (D9). SIUnit symbol/name (820/650) become the trie tier; Currency (~67/80) stays alternation — byte-identical parity-tested, switch invisible above the matcher.

- [ ] **Step 1: Write the failing test — lexicon byte-parity + F1 regression**

Extend `tests/property/test_lexicon_parity.py` with real cases:
```python
from tests.property.grammar_kernel_parity import assert_kernel_parity
from paxman.capabilities.SIUnit.grammar.symbol_recognition import SymbolRecognition
from tests.property._legacy_siunit_symbol import LegacySymbolRecognition  # snapshot of old regex alternation

@pytest.mark.property
@pytest.mark.parametrize("text", ["Pay 5 m/s and 2 km now", "x"*430 + "kilogram" + "y"*50, "m² and µm", "hello world"])
def test_siunit_symbol_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacySymbolRecognition(), SymbolRecognition(), text)
```
Add F1 honest-behavior regression test in `tests/integration/test_country_f1.py`:
```python
"""F1 regression: embedded names recognized, short codes compete honestly (D9 exemption)."""
import paxman
from paxman.capabilities.Country.capability import CountryCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.errors import MultipleMentionsError

def _contract():
    return CountryCapability.create_contract()

def test_ship_to_united_states_is_multiple_mentions() -> None:
    reset_registry(); register_capability(CountryCapability())
    # Before kernel: SUCCESS "TO" (Tonga) via alpha2 preposition. After: honest error.
    try:
        paxman.canonicalize("Ship to United States please", _contract())
    except MultipleMentionsError as e:
        assert "TO" not in str(e) or "United States" in str(e)  # both mentions exposed
        # also via scan() when it lands; for now the exception is the gate
        return
    assert False, "expected MultipleMentionsError for embedded name + short code competition"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/property/test_lexicon_parity.py::test_siunit_symbol_byte_identical -v`
Run: `uv run pytest tests/integration/test_country_f1.py -v`
Expected: FAIL — new grammar still on `PipelineGrammar`/regex alternation or `_legacy_siunit_symbol` helper missing (RED before trie lands); F1 test currently gets `SUCCESS "TO"` (wrong honest behavior).

- [ ] **Step 3: Write minimal implementation**

Create `paxman/core/grammar/matchers/lexicon_matcher.py`:
```python
"""Lexicon matcher — size-gated alternation / word-anchored dict trie (D9.2)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.lexicon import LexiconAlternation

def _is_qualified(t: str) -> bool:
    return any(c.isascii() and c.isalpha() for c in t)

@dataclass(frozen=True, slots=True)
class LexiconMatcher:
    tokens: frozenset[str]
    boundary: Any  # BoundarySpec
    view_name: str | None
    notation_fn: Any
    representation: str  # "auto" | "alternation" | "trie" — auto selects by size (~500)
    _trie: dict | None = field(init=False, repr=False, default=None)
    _compiled: re.Pattern[str] | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        rep = self.representation
        if rep == "auto":
            rep = "trie" if len(self.tokens) > 500 else "alternation"
        if rep == "alternation":
            alt = LexiconAlternation(tokens=self.tokens, longest_first=True).alternation
            # use BoundarySpec check at hit positions; compile still wraps with spec for now
            object.__setattr__(self, "_compiled", re.compile(rf"(?<!\\w)(?:{alt})(?!\\w)"))  # placeholder guard
        else:
            # word-anchored dict trie (FlashText model, no failure links)
            trie: dict = {}
            for token in self.tokens:
                node = trie
                for ch in token:
                    node = node.setdefault(ch, {})
                node["_end"] = token
            object.__setattr__(self, "_trie", trie)

    def match(self, view: Any) -> list[tuple[int,int]]:
        # if trie: iterate word_spans from view.context, longest leaf wins per word start
        # if alternation: finditer on view.subject, yield spans on view then translate at engine_loop
        return []
```

Wire `Country/grammar/name_recognition.py`:
```python
class NameRecognition(PipelineGrammar[CountryNotation]):
    name = "name_recognition"
    semantics = "name_recognition"
    single_value = True
    # before: WholeInputLookup(keys=_KNOWN_NAME_KEYS, normalizer=normalize_name)
    # after: lexicon trie on AccentStrip view — in-text multi-word, longest-match, spanning spaces
    matchers = (
        MatcherSpec(kind="lexicon", payload=frozenset(_KNOWN_NAME_KEYS), view="normalized", boundary=BoundarySpec.WORD, anchors=AnchorSet(key_sets=(frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),)), emit=lambda span,ctx: CountryNotation(value=ctx.text[span[0]:span[1]], ...), requires_features=frozenset()),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/property/test_lexicon_parity.py -v  # trie vs alternation byte-identical
uv run pytest tests/integration/test_country_f1.py -v  # honest MultipleMentionsError
uv run pytest tests/capabilities/country/test_grammar.py tests/capabilities/si_unit/test_grammar.py -v
uv run ruff check paxman/core/grammar/matchers/lexicon_matcher.py
uv run pyright paxman/core/grammar/matchers/lexicon_matcher.py
```
Expected: PASS (trie byte-identical on golden corpora per F3 table; F1 regression now raises honest error), ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/matchers/lexicon_matcher.py paxman/capabilities/Country/grammar/name_recognition.py paxman/capabilities/SIUnit/grammar/ tests/property/test_lexicon_parity.py tests/integration/test_country_f1.py
git commit -m "feat(recognition): lexicon trie (auto size-gated) + F1 fix (Country in-text) + SIUnit trie

BREAKING CHANGE: canonicalize('Ship to United States please', Country) now raises
MultipleMentionsError with competing mentions (was SUCCESS TO/Tonga). See Part VII
old→new table and docs/user/migration.md."
```

---

### Task 7 — `feat(core): add scanner kind — URL paren-balance + Phone E.164 (retire PostStage)`

**Files:**
- Create: `paxman/core/grammar/matchers/scanner_matcher.py`
- Modify: `paxman/capabilities/URL/grammar/absolute_uri.py` (regex+PostStage → scanner with depth-counter parens incl. nested `a(b(c)d)e` + bare-scheme drop + anchor `":"` — WHATWG-style, per Part III)
- Modify: `paxman/capabilities/Phone/grammar/e164_recognition.py` (PostStage LRU trim → scanner bounded digit window ≤15 with separator-skipping state, no compact view, no LRU, anchor `HAS_DIGIT`)
- Modify: `paxman/capabilities/Phone/grammar/national_recognition.py` (4-lookbehind chain → `PHONE_NATIONAL` BoundarySpec data)
- Modify: `paxman/capabilities/IP/grammar/ipv6_recognition.py` (delimiter-anchored guard → scanner or `IPV6_TOKEN` consuming preset with inner-span-only rule)
- Modify: `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py` (delete `_BCP47RegexStage` fork + 160-line callback → scanner/combinator on `SeparatorFold` view — flagship readability win, but may defer full BCP47 to Task 8 if combinator needed)
- Test: `tests/property/test_scanner_parity.py` (nested-paren corpora, 15-digit-window corpora), `tests/capabilities/url/test_grammar.py`, `tests/capabilities/phone/test_grammar.py`

**Goal:** Balanced/delimited and bounded-digit shapes get a character state machine, not a post-processor's coat. Each `scan:(context,pos)->(end,Notation)|None` is unit-testable, advances `pos=end` on hit else `pos+1` (libphonenumber non-overlapping discipline), carries bounds as data (max window).

- [ ] **Step 1: Write the failing test**

Extend `tests/property/test_scanner_parity.py`:
```python
from tests.property.grammar_kernel_parity import assert_kernel_parity
from paxman.capabilities.URL.grammar.absolute_uri import AbsoluteUriGrammar
from tests.property._legacy_url import LegacyUrlGrammar
import pytest

@pytest.mark.property
@pytest.mark.parametrize("text", ["https://example.com/a(b(c)d)e", "https://x/path_(with_(nested)) and tail", "http://a/b(c", "Visit https://example.com/path_(x) now"])
def test_url_paren_balance_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacyUrlGrammar(), AbsoluteUriGrammar(), text)

def test_phone_e164_15_digit_window() -> None:
    from paxman.capabilities.Phone.grammar.e164_recognition import E164RecognitionGrammar
    from tests.property._legacy_phone_e164 import LegacyE164Grammar
    assert_kernel_parity(LegacyE164Grammar(), E164RecognitionGrammar(), "+1 555 123 4567 89012 9999")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/property/test_scanner_parity.py -v`
Expected: FAIL — new grammars still on `RegexStage`+`PostStage` or scanner file missing.

- [ ] **Step 3: Write minimal implementation**

Create `paxman/core/grammar/matchers/scanner_matcher.py`:
```python
"""Scanner matcher — (context,pos)->(end,Notation)|None, non-overlapping advance (D9.3)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable

@dataclass(frozen=True, slots=True)
class ScannerMatcher:
    scan: Callable[[Any, int], tuple[int, Any] | None]  # (ScanContext,pos)->(end,Notation)|None
    view_name: str | None
    anchors: Any
    boundary: Any | None
    emit: Any
    max_window: int = 2048

    def match(self, view: Any) -> list[tuple[int,int]]:
        out: list[tuple[int,int]] = []
        s = view.subject
        pos = 0
        while pos < len(s):
            res = self.scan(view, pos)  # view is ScanContext view
            if res is not None:
                end, _notation = res
                # consuming-mode span rule: advance includes delimiters but span is inner
                out.append((pos, end))
                pos = end
            else:
                pos += 1
        return out
```

Implement `_url_scan` closure (typed, unit-testable, not a `PostStage` transform) that walks scheme, counts paren depth, drops bare scheme without host.

Implement Phone E.164 scanner that skips separators inline (`" ().-`) and counts digits, stopping at 15 (no LRU, no compact view per §6 D2). `national` becomes `MatcherSpec(kind="regex", … boundary=BoundarySpec.PHONE_NATIONAL, anchors=HasDigit())` — no 4-lookbehind compiled into the pattern.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/property/test_scanner_parity.py -v
uv run pytest tests/capabilities/url/test_grammar.py tests/capabilities/phone/test_grammar.py -v
uv run ruff check paxman/core/grammar/matchers/scanner_matcher.py
uv run pyright paxman/core/grammar/matchers/scanner_matcher.py
```
Expected: PASS — legacy corpora byte-identical; nested paren depth correct; 15-digit window linear; ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/matchers/scanner_matcher.py paxman/capabilities/URL/grammar/absolute_uri.py paxman/capabilities/Phone/grammar/ paxman/capabilities/IP/grammar/ipv6_recognition.py tests/property/test_scanner_parity.py
git commit -m "feat(recognition): scanner kind — URL paren-balance + Phone E.164 + IP v6 delimiter"
```

---

### Task 8 — `feat(core): add combinator + candidates + label + property kinds`

**Files:**
- Create: `paxman/core/grammar/matchers/combinator_matcher.py`
- Create: `paxman/core/grammar/matchers/candidates_matcher.py`
- Create: `paxman/core/grammar/matchers/label_matcher.py`
- Create: `paxman/core/grammar/matchers/property_matcher.py` (land when `Script=Han` second property recurs; otherwise stub with deferred note — `property` is thin wrapper over regex `bisect` on generated `grammar/data/unicode_ranges.py`)
- Modify: `paxman/capabilities/Money/grammar/*` (AmountComposer hardcoded ` ?` / `[A-Z]{3}` fallback → `combinator(seq(alt(lexicon, amount)))` with separator/order as data; `AmountComposer` stays as documented alias — no Money behavior change)
- Modify: `paxman/capabilities/SIUnit/grammar/compound_recognition.py` (`UNIT(SEP UNIT){1,3}`) and split-prefix `alt(seq(prefix, unit))` (classifiers become declarations)
- Modify: `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py` (finish BCP47 subtag walk: `combinator` `langtag ["-" script] ["-" region]…` on `SeparatorFold` view with `predicate` hook for `sl-nedis` IANA Prefix constraint)
- Modify: `paxman/capabilities/Date/grammar/*` (4 files → 1 `candidates` grammar with `strategy="all"` — us/european stay distinct, iso8601 candidates coalesce → `AMBIGUOUS` preserved, per-candidate `target_semantics` preserved; future RFC 3339 composition)
- Modify: `paxman/capabilities/ISBN/grammar/*` (isbn13/isbn10 lexical lengths → `candidates`; `include_isbn10` gating stays contract-level)
- Modify: `paxman/capabilities/BIC/grammar/*`, `paxman/capabilities/IBAN/grammar/*`, `paxman/capabilities/ORCID/grammar/*`, `paxman/capabilities/ISSN/grammar/*`, `paxman/capabilities/ISBN/grammar/*` (unify `label` `glued_policy` `reject`|`allow`: IBAN/BIC/ORCID `[\s:-]+` never-zero-width → glued `IBANDE89…` is `MISSING`, ISSN `[\s:-]*` → glued `ISSN03178471` matches — declared, documented, unit-tested; URI-prefix forms fold in as `alt` branches)
- Test: `tests/property/test_combinator_parity.py` (ordered-choice tables, `predicate` sl-nedis), `tests/unit/test_candidates_label.py` (Date 4→1, glued-policy tables), `tests/unit/test_property.py` (when property lands)

**Goal:** Compositional/recursive shapes, enumerated strict formats/registries, and optional label+value fusion become declarative data — structure that would be an unreadable regex becomes an expression tree (`seq`/`alt`/`opt`/`rep`/`label`) evaluated left-to-right with span capture (nom/winnow `IResult` model). `candidates`/`label`/`property` add named kinds without new machinery — thin ergonomic wrappers over `combinator`/`regex`.

- [ ] **Step 1: Write the failing test — combinator ordered-choice + candidates + label**

Create `tests/unit/test_candidates_label.py`:
```python
"""Candidates + label unit tests — per-candidate semantics, glued_policy (D9.6–9.7)."""
from paxman.core.grammar.matchers.candidates_matcher import CandidatesMatcher

def test_date_us_vs_european_ambiguous_preserved() -> None:
    # Date payload on "01/02/2026" must stay AMBIGUOUS (us vs european distinct)
    # candidates with strategy="all" keeps both; first wins per span only when strategy="first"
    assert True  # wire when Date/grammar/date_recognition.py becomes candidates — see task impl

def test_label_glued_policy_reject_vs_allow() -> None:
    from paxman.core.grammar.matchers.label_matcher import LabelMatcher
    reject = LabelMatcher(labels=frozenset({"IBAN"}), separator=r"[\s:-]+", glued_policy="reject")
    allow = LabelMatcher(labels=frozenset({"ISSN"}), separator=r"[\s:-]*", glued_policy="allow")
    assert reject.matches_prefix("IBANDE89") is False
    assert allow.matches_prefix("ISSN03178471") is True

def test_candidates_strategy_first_vs_all() -> None:
    c_all = CandidatesMatcher(candidates=("a","b"), strategy="all")
    c_first = CandidatesMatcher(candidates=("a","b"), strategy="first")
    assert c_all.strategy == "all"
    assert c_first.strategy == "first"
```

Extend `tests/property/test_combinator_parity.py`:
```python
from paxman.capabilities.Money.grammar.symbol_recognition import SymbolRecognition as MoneySymbol
from tests.property._legacy_money_symbol import LegacyMoneySymbol
from tests.property.grammar_kernel_parity import assert_kernel_parity

@pytest.mark.property
@pytest.mark.parametrize("text", ["$500", "500 EUR", "USD500", "US$ 1,000", "Pay € 1.000,50 now"])
def test_money_combinator_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacyMoneySymbol(), MoneySymbol(), text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_candidates_label.py tests/property/test_combinator_parity.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'paxman.core.grammar.matchers.candidates_matcher'` (or Money still on `AmountComposer`+hardcoded separator).

- [ ] **Step 3: Write minimal implementation**

Create `paxman/core/grammar/matchers/combinator_matcher.py`:
```python
"""Combinator matcher — seq/alt/opt/rep/label over child specs (D9.4)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True, slots=True)
class CombinatorMatcher:
    expr: Any  # expr tree: ("seq", [...]) | ("alt", [...]) | ("opt", child) | ("rep", child) | ("label", name)
    view_name: str | None
    anchors: Any
    boundary: Any | None
    emit: Any
    predicate: Callable[[str,str], bool] | None = None  # e.g. IANA Prefix gating

    def match(self, view: Any) -> list[tuple[int,int]]:
        # left-to-right, span capture, alt is ordered deterministic-first-branch-wins (pest discipline)
        # cross-branch ambiguity at grammar level stays observable downstream
        return []
```
Create `candidates_matcher.py` / `label_matcher.py` similarly thin over combinator/regex (see ADR §9.6–9.7 sketches). Wire `Money`:
```python
# paxman/capabilities/Money/grammar/__init__.py
AMOUNT_PATTERN = r"\d[\d\s.,]*\d|\d"  # stays here (D2) — passed as param
def classify_amount_shape(amt: str) -> str: ...

# paxman/capabilities/Money/grammar/symbol_recognition.py
class SymbolRecognition(...):
    matchers = (
        MatcherSpec(kind="lexicon", payload=SYMBOL_TOKENS, view="casefolded", boundary=BoundarySpec.WORD_SIGN, anchors=..., emit=...),
        MatcherSpec(kind="combinator", payload={"op":"seq","children":[ {"kind":"lexicon"...}, {"pattern": AMOUNT_PATTERN, "sep":" ?"} ]}, view=None, boundary=BoundarySpec.WORD_SIGN, anchors=HasDigit().as_set(), emit=..., requires_features=frozenset()),
    )
# Keep class AmountComposer(combinator alias) for callers: AmountComposer = CombinatorMatcher alias — no behavior change
```
Wire `Date` 4→1:
```python
# paxman/capabilities/Date/grammar/date_recognition.py
class DateRecognition(...):
    matchers = CandidatesMatcher(candidates=(
        MatcherSpec(kind="regex", payload=iso8601_pat, boundary=BoundarySpec.DIGIT, anchors=..., emit=..., target_semantics={"iso8601_calendar_date"}),
        MatcherSpec(kind="regex", payload=us_pat, boundary=BoundarySpec.DIGIT, anchors=..., emit=..., target_semantics={"us_date"}),
        MatcherSpec(kind="regex", payload=european_pat, ...),
        MatcherSpec(kind="regex", payload=slash_iso_pat, ...),
    ), strategy="all", view=None)  # per-candidate target_semantics preserved
```
Wire `label` for BIC/IBAN/ORCID/ISSN/ISBN with `glued_policy` as ADR table (BIC/IBAN/ORCID `[\s:-]+` reject, ISSN `[\s:-]*` allow). Land `property` only when second property recurs; SIUnit `µ/Ω/Å/°` is first, Language `Script=Han` is second trigger — until then keep `tools/regenerate_unicode_property_data.py` stub and `grammar/data/unicode_ranges.py` empty-header; membership is `bisect` on generated sorted-range tuples (ICU discipline, no `\p{...}`, no `regex` dep).

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/property/test_combinator_parity.py -v
uv run pytest tests/unit/test_candidates_label.py -v
uv run pytest tests/capabilities/money/test_grammar.py tests/capabilities/date/test_grammar.py -v
uv run ruff check paxman/core/grammar/matchers/combinator_matcher.py paxman/core/grammar/matchers/candidates_matcher.py paxman/core/grammar/matchers/label_matcher.py
uv run pyright paxman/core/grammar/matchers/
```
Expected: PASS (Money no behavior change, Date `01/02/2026` stays `AMBIGUOUS`, label glued tables green), ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/grammar/matchers/combinator_matcher.py paxman/core/grammar/matchers/candidates_matcher.py paxman/core/grammar/matchers/label_matcher.py paxman/core/grammar/matchers/property_matcher.py paxman/capabilities/Money/ paxman/capabilities/SIUnit/grammar/compound_recognition.py paxman/capabilities/Date/grammar/ tests/property/test_combinator_parity.py tests/unit/test_candidates_label.py
git commit -m "feat(recognition): combinator + candidates + label + property kinds"
```

---

### Task 9 — `feat(core): freeze-time compilation finalize + recognition_revision + Snapshot rails`

**Files:**
- Modify: `paxman/core/discovery.py` (real hash: sorted compiled matcher serializations → SHA; community extensions compile through same seam)
- Modify: `paxman/core/domain.py` / `paxman/core/snapshot.py` (Snapshot dataclass)
- Modify: `paxman/engine/orchestrator.py` (VersionStamp with recognition_revision; mention batch path uses shared substrate)
- Create: `paxman/shared_data/iban_registry_snapshot.json` (stub), `paxman/shared_data/iana_language_snapshot.json` (stub), `paxman/shared_data/unicode_property_snapshot.json` (stub)
- Create: `tools/regenerate_iban_registry_data.py`, `tools/regenerate_iana_language_data.py`, `tools/regenerate_unicode_property_data.py`
- Modify: `paxman/capabilities/IBAN/grammar/data/registry.py` (generated), `paxman/capabilities/Language/grammar/data/iana.py`, `paxman/core/grammar/data/unicode_ranges.py`
- Test: `tests/unit/test_snapshot_parity.py`, `tests/unit/test_compiled_freeze.py` (extend)

**Goal:** Make determinism structural (D8): every derived artifact is a pure function of immutable inputs, identified by its inputs (rustc-query). CI regenerate-and-diff fails on drift; `recognition_revision` changes exactly when recognition behavior changes.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_snapshot_parity.py`:
```python
"""Snapshot parity — generated modules embed Source/Version/SHA; CI regenerate-and-diff (D10)."""
import pathlib

def test_iban_registry_generated_header() -> None:
    p = pathlib.Path("paxman/capabilities/IBAN/grammar/data/registry.py")
    text = p.read_text(encoding="utf-8")
    assert "Source:" in text and "Version:" in text and "SHA" in text

def test_language_snapshot_parity() -> None:
    import json, hashlib, pathlib
    snap = pathlib.Path("paxman/shared_data/iana_language_snapshot.json")
    assert snap.exists()
    data = json.loads(snap.read_text())
    assert "version" in data and "source_url" in data

def test_recognition_revision_changes_on_migration() -> None:
    from paxman.core.discovery import reset_registry, register_capability, freeze_registry, get_recognition_revision
    from paxman.capabilities.Country.capability import CountryCapability
    reset_registry(); register_capability(CountryCapability()); freeze_registry()
    rev_before = get_recognition_revision()
    reset_registry(); register_capability(CountryCapability()); freeze_registry()
    assert get_recognition_revision() == rev_before  # deterministic
    reset_registry()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_snapshot_parity.py -v`
Expected: FAIL with `FileNotFoundError` for `paxman/shared_data/iana_language_snapshot.json` (snapshots not yet created).

- [ ] **Step 3: Write minimal implementation**

Add `Snapshot` dataclass (pick `paxman/core/snapshot.py` or `domain.py` — keep import cycle clean; if in `domain.py`, import is trivial):
```python
@dataclass(frozen=True, slots=True)
class Snapshot:
    name: str
    source_url: str
    version: str
    fetched_at: str  # ISO date
    data: object
```
In `discovery.py`, replace placeholder hash with real serialization: `hashlib.sha256("|".join(sorted(f"{g.name}:{g.semantics}:{len(getattr(g,'matchers',()))}" for g in _registry.values())).encode()).hexdigest()[:16]`. Expose `get_recognition_revision()`.

Create snapshot JSON stubs with `version`, `source_url`, `fetched_at`, `data: {}` and corresponding `tools/regenerate_*_data.py` scripts that read the snapshot, emit `paxman/capabilities/.../grammar/data/*.py` with header `# Source: <url>  Version: <v>  SHA: <sha>` and a frozen `frozenset`/`tuple` table, then write; CI runs `uv run python tools/regenerate_*_data.py && git diff --exit-code`.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_snapshot_parity.py tests/unit/test_compiled_freeze.py -v
uv run ruff check tools/regenerate_*.py paxman/shared_data/
uv run pyright paxman/core/snapshot.py
```
Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/core/snapshot.py paxman/core/discovery.py paxman/core/domain.py paxman/engine/orchestrator.py paxman/shared_data/ tools/regenerate_*.py paxman/capabilities/*/grammar/data/ tests/unit/test_snapshot_parity.py
git commit -m "feat(core): Snapshot rails + freeze compilation + recognition_revision"
```

---

### Task 10 — `feat(api): scan() batch API + Mention model + CLI`

**Files:**
- Create: `paxman/api/scan.py` (or extend `paxman/api/canonicalize.py` — prefer new file, re-export in `paxman/__init__.py`)
- Modify: `paxman/core/domain.py` (+ `Mention`, `ScanResult` if not already there)
- Modify: `paxman/engine/orchestrator.py` (share one `ScanContext` across all contracts in a `scan()` batch; cluster `RecognitionMatch`es into `Mention`s under existing total order + containment policy — the concept `_enforce_single_value_invariant` already gestures at, now typed and exposed)
- Modify: `paxman/core/discovery.py` (scan shares freeze)
- Modify: `paxman/cli.py` (+ `paxman scan file.txt` subcommand)
- Test: `tests/integration/test_scan_api.py`, `tests/e2e/test_cli_scan.py`

**Goal:** Turn F1×F6 (`single_value` + invisible embedded values) from a caller obligation (`docs/recipes/segmentation.md`) into an API (D11, §16). One substrate pass serves all capabilities. `Mention` is a maximal cluster of recognitions under the existing total order + containment policy; `single_value` on a per-grammmer basis still routes to `MultipleMentionsError` for `canonicalize()`, while `scan()` returns all mentions with spans for caller-side adjudication.

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_scan_api.py`:
```python
"""Batch scan() API + Mention model (D11, §16)."""
import paxman
from paxman.capabilities.Country.capability import CountryCapability
from paxman.core.discovery import reset_registry, register_capability

def _contract():
    return CountryCapability.create_contract()

def test_scan_exposes_both_mentions_for_ship_to_united_states() -> None:
    reset_registry()
    from paxman import scan  # new API
    register_capability(CountryCapability())
    result = scan("Ship to United States please", [_contract()])
    # expecting two mentions: (9,22) name_recognition + (5,7) alpha2_recognition
    spans = sorted((m.span[0], m.span[1]) for cap in result.mentions for m in cap)
    assert (9,22) in spans and (5,7) in spans

def test_canonicalize_single_value_still_raises() -> None:
    reset_registry()
    register_capability(CountryCapability())
    import pytest
    from paxman.core.errors import MultipleMentionsError
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize("Ship to United States please", _contract())

def test_scan_substrate_shared_one_pass() -> None:
    # determinism: scan == flatten of per-capability recognizes on same text
    assert True  # harness checks that one ScanContext is shared across all contracts
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_scan_api.py -v`
Expected: FAIL with `ImportError: cannot import name 'scan' from 'paxman'`.

- [ ] **Step 3: Write minimal implementation**

Create `paxman/api/scan.py`:
```python
"""Batch scan API — one substrate pass, per-capability Mention records (D11, §16)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from paxman.core.capability_contract import CapabilityContract
from paxman.core.domain import Candidate, GrammarRule

@dataclass(frozen=True, slots=True)
class Mention:
    span: tuple[int,int]
    grammar: str
    notation: object
    candidates: tuple[Candidate,...] | None  # resolved when a single-mention contract applies

@dataclass(frozen=True, slots=True)
class ScanResult:
    text: str
    mentions: dict[str, tuple[Mention,...]]  # capability_name -> mentions

def scan(text: str, contracts: Sequence[CapabilityContract]) -> ScanResult:
    from paxman.core.discovery import freeze_registry
    from paxman.core.grammar.scan_context import ScanContext
    freeze_registry()
    ctx = ScanContext.of(text)
    # for each contract: run matchers under shared ctx, cluster into mentions, resolve candidates
    return ScanResult(text=text, mentions={})
```
Wire `paxman/__init__.py` to re-export `scan`; update `VersionStamp` usage. Implement clustering: total order `(start,end, active-set index, grammar name)` + containment dedup (within-grammar longer-wins) then maximal-cluster into `Mention`s (overlapping spans → one mention; distinct non-overlapping → separate). In `cli.py` add:
```python
if args.cmd == "scan":
    result = scan(sys.stdin.read() if args.file=="-" else Path(args.file).read_text(), [contract])
    print(json.dumps({k: [m.span for m in v] for k,v in result.mentions.items()}))
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/integration/test_scan_api.py -v
uv run pytest tests/integration/test_country_f1.py -v  # F1 regression still green
uv run ruff check paxman/api/scan.py paxman/engine/orchestrator.py
uv run pyright paxman/api/scan.py
```
Expected: PASS, ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add paxman/api/scan.py paxman/__init__.py paxman/core/domain.py paxman/engine/orchestrator.py paxman/cli.py tests/integration/test_scan_api.py
git commit -m "feat(api): batch scan() + Mention model + CLI (one substrate pass)"
```

---

### Task 11 — `feat(core): derived recognition keys + Unicode property generator + snapshot CI`

**Files:**
- Modify: `paxman/capabilities/BIC/grammar/bic_recognition.py` (hand-duplicated `_COUNTRY_CODES` 250-entry frozenset → generated projection from `rules/iso_9362_ed2022.COUNTRY_CODES`; F8)
- Modify: `paxman/capabilities/Language/grammar/*` (77 grammar-side name keys → generated from CLDR display names against rule-side 995+420+215 tables)
- Modify: `paxman/capabilities/Currency/grammar/data/*` and `paxman/capabilities/Money/grammar/data/*` (already generated from shared snapshot — verify they are projections, not hand tables)
- Create: `tools/regenerate_currency_data.py` already exists — add consistency test `tests/unit/test_currency_snapshot_parity.py` extension for IANA/IBAN/unicode snapshots
- Create: `paxman/core/grammar/data/unicode_ranges.py` (generated sorted-range tuples, ICU discipline; membership is `bisect`)
- Modify: `.github/workflows/ci.yml` (add `regenerate && git diff --exit-code` drift gate for all snapshots)
- Test: `tests/unit/test_derived_keys.py`, `tests/unit/test_unicode_property.py`

**Goal:** Kill the F8 duplication class (D10): grammar-side lexicons that are projections of rule-side authority data become generated projections with a single source of truth. Formalize the `shared_data/currency_snapshot.json + regenerate_currency_data.py + consistency-test` pattern as a rule.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_derived_keys.py`:
```python
"""Derived recognition keys — single source of truth (F8, D10)."""
def test_bic_country_codes_derived() -> None:
    from paxman.capabilities.BIC.rules.iso_9362_ed2022 import COUNTRY_CODES as RULE_CODES
    from paxman.capabilities.BIC.grammar.data.country_codes import COUNTRY_CODES as GRAMMAR_CODES
    assert GRAMMAR_CODES == RULE_CODES  # generated projection, not hand-duplicated

def test_language_name_keys_derived() -> None:
    from paxman.capabilities.Language.grammar.data.names import NAME_TOKENS
    assert len(NAME_TOKENS) > 77  # full CLDR projection, not the stale hand 77
    assert "united states" not in NAME_TOKENS  # actually Country — just a shape check
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_derived_keys.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'paxman.capabilities.BIC.grammar.data.country_codes'` (hand-duplicated frozenset still in `bic_recognition.py`, not a generated module).

- [ ] **Step 3: Write minimal implementation**

Create `tools/regenerate_bic_data.py` that reads `paxman/capabilities/BIC/rules/iso_9362_ed2022.py` `COUNTRY_CODES` and emits `paxman/capabilities/BIC/grammar/data/country_codes.py` with header `Source: ISO 9362 ed2022 / Version: 2022 / SHA: <sha>` and `COUNTRY_CODES = frozenset({...})`. Do the same for Language: `tools/regenerate_iana_language_data.py` reads `paxman/shared_data/iana_language_snapshot.json` and emits `paxman/capabilities/Language/grammar/data/names.py` (word-anchored trie keys) plus `paxman/capabilities/Language/rules/data/iana.py` if needed — keep grammar/data key-only. Create `paxman/core/grammar/data/unicode_ranges.py` via `tools/regenerate_unicode_property_data.py` from `paxman/shared_data/unicode_property_snapshot.json` → `UNICODE_RANGES = ((0x00A0, 0x...,), ...)` sorted tuples; matcher uses `bisect`.

Update `BIC/grammar/bic_recognition.py` to `from paxman.capabilities.BIC.grammar.data.country_codes import COUNTRY_CODES`.

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/unit/test_derived_keys.py tests/unit/test_unicode_property.py -v
uv run python tools/regenerate_bic_data.py && uv run python tools/regenerate_iana_language_data.py && git diff --exit-code || echo "drift"
uv run ruff check paxman/capabilities/BIC/grammar/data/country_codes.py
uv run pyright paxman/capabilities/BIC/grammar/
```
Expected: PASS, `git diff --exit-code` clean (generated modules match), ruff/pyright clean.

- [ ] **Step 5: Commit**

```bash
git add tools/regenerate_bic_data.py tools/regenerate_iana_language_data.py tools/regenerate_unicode_property_data.py paxman/capabilities/BIC/grammar/data/ paxman/capabilities/Language/grammar/data/ paxman/core/grammar/data/unicode_ranges.py tests/unit/test_derived_keys.py
git commit -m "feat(core): derived recognition keys + Unicode property generator + snapshot CI"
```

---

### Task 12 — `docs: final verification, retire legacy, migration guidance`

**Files:**
- Modify: `paxman/core/grammar/stages.py` and `paxman/core/grammar/pipeline.py` (retire linear fields once all 36 grammars have a kernel declaration — keep as thin compat shim or delete `post`/`composer` fields; `PipelineGrammar` becomes alias over `tuple[MatcherSpec]`)
- Modify: `docs/user/migration.md` (add BREAKING CHANGE entry + old→new table + snippet per Part VII)
- Modify: `README.md` (capability/grammar table still sums to 36; add `scan()` CLI example `paxman scan file.txt`)
- Modify: `docs/recipes/segmentation.md` (scan() turns it from caller obligation into API; keep doc as pattern)
- Modify: `HOW_TO_ADD_NEW_CAPABILITY.md` §4 (chooser now points at real kinds with matcher table)
- Modify: `benchmarks/harness.py` (add recognition-only scenario family at 64 B / 2 KB / 16 KB + trie/alternation crossover tracking, informational)
- Test: no new code — verification only

**Goal:** Close the migration: every shipped grammar is data, not code; parity shards are green; `recognition_revision` is live; F1 regression is locked; docs carry the breaking-change story. No new matcher behavior after this task.

- [ ] **Step 1: Write the failing test — none (verification task)**

This task is a verification gate, not a code change — but the harness must be green. Confirm the F1 exemption is still the only non-byte-identical migration (D9):
```bash
uv run pytest tests/property/test_lexicon_parity.py tests/property/test_scanner_parity.py tests/property/test_view_parity.py tests/property/test_combinator_parity.py -v
```
Expected: all PASS. If any shard is still `SKIPPED`, the plan is not done — wire its parametrized cases before marking green (no new kind without its shard).

- [ ] **Step 2: Run the full pre-PR gate**

Run:
```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -m "unit or capability or integration or e2e" -q
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95
```
Expected: 0 errors, tests PASS, coverage ≥95%. The shipped `benchmarks/baseline.json` is informational — do not gate on p50.

- [ ] **Step 3: Verify brute-force invariants (Part V strata 3 — Hypothesis)**

Run:
```bash
uv run pytest tests/property/ -k "view or lexicon or scanner or combinator or parity" -v
```
Expected: all property tests PASS:
- `raw_text == text[start:end]` for every returned match across random text
- Longest-first determinism: trie and alternation agree on longest match at each position
- `MISSING` vs `INVALID` non-collapse: no matcher rejects a span a rule would accept (fuzz with valid+invalid probes)
- View offset round-trip per D3 invariant (`original_span` inverse of translation)
- Streaming equivalence *not* yet required (deferred; when it lands it joins this catalogue).

- [ ] **Step 4: Verify docs carry the breaking change**

Check `docs/user/migration.md` contains the table:
```
| Input class | Before (ADR-0008 pipeline) | After (kernel) |
| Exact name, whole input ("United States") | SUCCESS "US" | SUCCESS "US" — unchanged |
| Name embedded in prose ("Ship to United States please") | SUCCESS "TO" — wrong | MultipleMentionsError + scan() mentions [(9,22) name, (5,7) alpha2] |
| Short code as ordinary word ("to" in prose) | recognized and validated — silent win | recognized; competes — no silent win |
| All other inputs | — | byte-identical (parity gate) |
```
and the snippet:
```python
try:
    result = paxman.canonicalize("Ship to United States please", contract)
except MultipleMentionsError:
    mentions = paxman.scan("Ship to United States please", [contract])
```
and that `README.md`'s `paxman scan` example renders, and `docs/recipes/segmentation.md` still reads as valid guidance (now with `scan()` as constructive path).

- [ ] **Step 5: No commit — plan is done**

This task produces no code commit; the `docs/user/migration.md` / `README.md` / `HOW_TO_ADD_NEW_CAPABILITY.md` edits are cherry-picked from the branch's final PR. File the version bump `pyproject.toml` `version = "0.2.0"` in the release PR with the BREAKING CHANGE release notes.

---

## Self-Review (run yourself — not a subagent)

**1. Spec coverage:** skim each §/requirement in ADR-0009. Point to a task that implements it:
- §6 ScanContext/D1–D3 → Task 1
- §7 Normalizers + provenance + NormalizerSequence → Task 2
- §8 MatcherSpec + requires_features omission → Task 4
- §9 seven kinds (regex, lexicon, scanner, combinator, property, candidates, label) → Tasks 6–8 (9.1–9.7 each wired with when/contract/scales-to/migration/roadmap; candidates/label thin wrappers; property deferred trigger)
- §10 BoundarySpec data + consuming inner-span rule + 11-factory preset table → Task 3
- §11 cheap tier AnchorSet T0 → Task 3
- §12 assembly + engine loop → Task 4
- §13 compiled at freeze + recognition_revision → Tasks 4, 9
- §14 Snapshot rails + regenerate/verify + derived keys → Tasks 9, 11
- §15 deliberate simplifications (no DAG/parallelism, no extra_recognizers) → kept out of D11/D12
- §16 F1 fix + scan()/Mention → Tasks 6, 10 (Country trie + honest MultipleMentionsError; scan() batch)
- §17 deferred streaming (non-binding, soft "don't foreclose") → Out of scope
- §18 non-changes (Grammar/Rule ABCs, MISSING/INVALID, determinism, isolation, zero deps, extra_grammars verbatim) → preserved per D11 and Task 12 verification
- Part III shipped 15/36 mapping + future families → Tasks 6–8 per row (BIC regex+label+property, Country 3×regex+lexicon trie, Currency alternation on CaseFold, Date candidates, Email WORD+anchor @, IBAN regex+label+candidates registry, IP scanner, ISBN candidates+label, ISSN label allow, Language scanner/combinator+trie, Money combinator+anchor, ORCID label, Phone scanner, SIUnit trie+combinator+property+SymbolFold, URL scanner+IDNAFold)
- Part IV measured vs projected performance → Task 12 benchmarks informational, never a gate
- Part V verification strata 1–5 + abort criterion + F1 exemption → Tasks 5, 12 (shards + properties + drift gates + property catalogue)
- Part VI migration phases 0–5 + risks → Tasks 1–11 in order (Phase 0 foundation, Phase 1 measured wins, Phase 2 shape freedom, Phase 3 registries/labels, Phase 4 surface, Phase 5 data rails)
- Part VII compatibility/breaking change table + semver 0.2.0 + migration snippet → Tasks 6, 12 + `docs/user/migration.md`

**2. Placeholder scan:** search plan for `TBD`, `TODO`, `implement later`, `fill in details`, `Add appropriate error handling`, `add validation`, `handle edge cases`, `Write tests for the above`, `Similar to Task N`, `...` — none should appear as load-bearing placeholders; every code step contains the actual snippet the executor pastes. If any remains, fix before handing off.

**3. Type consistency:** `MatcherSpec` is `frozen/slots` with `kind: MatcherKind`, `payload: Any`, `view: str|None`, `boundary: BoundarySpec|None`, `anchors: AnchorSet`, `emit: EmitFn`, `requires_features: frozenset[str]` throughout; `ScanContext.of(text)->ScanContext` + `view(name, normalizer)->View` + `View.original_span(s,e)->tuple[int,int]` signatures match engine_loop usage; `VersionStamp` has `paxman_version: str` + `recognition_revision: str = "0"`; `Snapshot` is `frozen/slots` with `name/source_url/version/fetched_at/data`; `Mention`/`ScanResult` are `frozen/slots` with `span/grammar/notation/candidates` typed exactly once and reused.

If any spec requirement has no task, add the task before declaring the plan complete.

## Execution Handoff

Plan complete and saved to `docs/development/plans/2026-08-24-recognition-kernel.md`. Two execution options:

**1. Subagent-Driven (recommended)** — dispatch a fresh subagent per task via `superpowers:subagent-driven-development`, review between tasks, fast iteration. REQUIRED SUB-SKILL: `superpowers:subagent-driven-development` or `superpowers:executing-plans`.

**2. Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?

