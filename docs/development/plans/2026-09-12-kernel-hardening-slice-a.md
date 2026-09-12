# Kernel Hardening Slice A — Plan (issues #71, #73 + docs #144, #149)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Close the latent kernel traps in #73 (L1 bracket-escape parsing, L2 width windowing) and the remainder of #71 item 2 (single ordinal space for `_recognize` ordering), remove the one truly dead variable (L6 `nfd_pos`), and ride along the two independent docs fixes (#144 URL guarantee, #149 MacAddress guide) — with zero live-behavior change outside the documented ordering-key fix.

**Architecture:** Pure `paxman/core` + `paxman/engine` hardening (no capability logic changes): `_chars_from_bracket` learns `\uXXXX`/`\xNN`/`\UXXXXXXXX` with malformed-escape fallback to the regex path; `_estimate_width` returns `None` on quantifiers so `check_boundary` slices the full remainder; `_recognize` orders every match by the producing grammar's active-set index (dropping the mixed `cand_idx`-vs-`grammar_index` key); docs edits mirror the `language.md` guide structure and the `money.md` Limitations style. L3 (combinator backtracking), #71 items 3–4 (property-test tightening, blocked on the Language parity flake), and L6's deletion targets (`View.offsets`, `check_boundary_compiled`) are explicitly OUT — evidence for each exclusion is in Background.

**Tech Stack:** Python 3.11+, uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property/e2e), `paxman/core/grammar` kernel + `paxman/engine/orchestrator.py`.

**References:** Issues #71, #73, #144, #149; `paxman/core/grammar/boundary_spec.py:32-160,217-249,269-344`; `paxman/engine/orchestrator.py:296-320,381-449,452-469,783-839`; `paxman/core/grammar/normalizers.py:291-305`; `paxman/core/grammar/scan_context.py:48-60`; `paxman/core/discovery.py:155-180`; `docs/adr/0009-recognition-kernel.md` §9.4/§9.6/§10/§16; `docs/user/capabilities/language.md:11-175`; `docs/user/capabilities/url.md:5-46`; `docs/user/capabilities/money.md:156-159`.

**Branch:** `fix/kernel-slice-a-v050` (cut from `dev`).

---

## File Structure

- Modify: `paxman/core/grammar/boundary_spec.py` — L1 escape parsing in `_chars_from_bracket` + malformed fallback in `_pattern_to_chars`; L2 `_estimate_width` → `int | None` + `BoundarySpec.__post_init__`/`check_boundary` full-slice handling + `left_multi`/`right_multi` type widening.
- Modify: `paxman/core/grammar/normalizers.py` — delete write-only `nfd_pos` (L6, lines 300/305).
- Modify: `paxman/engine/orchestrator.py` — `_recognize` ordering key: position-2 of the `ordered` tuple always `grammar_index[grammar.name]` (#71 item 2 remainder, lines 396-431).
- Test: `tests/unit/test_boundary_spec.py` — L1 vectors + L2 synthetic-quantifier test + shipped-preset parity test.
- Test: `tests/unit/test_dedup_scoping.py` (exists, ADR-0012) or `tests/unit/test_kernel_hardening.py` — mixed CandidatesMatcher + LexiconMatcher ordering test (#71 item 2 acceptance).
- Docs: `docs/user/capabilities/mac_address.md` (create), `docs/user/capabilities/index.md` (MacAddress row), `docs/user/capabilities/url.md` (qualify guarantee).
- Docs: `CHANGELOG.md` — Unreleased/Fixed entries for kernel + docs.
- No new modules. No capability-logic changes. No `paxman/core` ↔ `paxman.capabilities` import changes.

---

## Background the implementer needs

### Current state (verbatim)

L1 — `_chars_from_bracket` treats every escape as a literal (`boundary_spec.py:42-47`):

```python
            # escaped literal (\-, \., \+, \[, etc.)
            res.add(nxt)
            i += 2
            continue
```

So `[\w\u2212]` lowers to a frozenset containing literal `u`,`2`,`1` (missing U+2212), and `[\x41]` yields `{'x','4','1'}` instead of `{'A'}`. `_pattern_to_chars` (`:61-92`) already returns `None` for negated classes (`[^...]`, `interior.startswith("^")` guard) and for interiors containing `*+?{}|` — which is why all shipped presets containing `\u2212` (`WORD_SIGN`, `DEGREE_WORD_SIGN`, both also contain `\+`) take the regex path today. No live divergence; fix is future-proofing.

L2 — `_estimate_width` (`:147-170`) counts `\X` as 1 and `[...]` as 1 with no quantifier awareness; `check_boundary` (`:302-323`) slices `subject[lo:start]` / `subject[end:hi]` with that width. A preset like `\w+` would slice 1 char and miss violations. All shipped multi-char presets (`\d[ -]`, `[\d+]`, `[\w:.+]`, …) are quantifier-free, so no live divergence. The anchored patterns (`re.compile(pat + r"\Z")`, `re.compile(r"\A" + pat)` in `__post_init__` `:232-243`) are already correct against a full remainder — the window is purely an optimization, so `None` → full slice is always correct.

#71 item 2 — pairing half already fixed in `0bb1d78` (span-keyed `span_to_indices` deque, `orchestrator.py:396-418` with the future-IBAN/ISBN comment). Remainder is only the ordering key: candidate-attributed matches carry `cand_idx` (position in `candidate_names`, `:408-418`) while plain matches carry `grammar_index[grammar.name]` (`:420-429`), then `ordered.sort(key=(start, end, idx, name))` (`:431`) compares the two ordinal spaces against each other. `grammar_index = {name: i ...}` over `active_names` (`:307`); position-2 of the tuple is sort-only (`for start, end, _index, grammar_name, match in ordered`, `:434`).

### Design decisions (locked)

1. **L1 malformed escapes → regex path, never literal fallback.** `_chars_from_bracket` raises `ValueError` on malformed `\u`/`\x`/`\U` (short run, non-hex, `> 0x10FFFF`); `_pattern_to_chars` catches it and returns `None`. The frozenset path is taken only when exactly convertible; the compiled-regex path is always correct. No silent divergence, ever.
2. **L2 widen, don't re-derive.** `_estimate_width` returns `int | None`; `None` iff a quantifier (`*+?{`) or alternation/group (`|(`) appears outside `[...]` spans (strip bracket spans first — those chars are literals inside classes). `left_multi`/`right_multi` become `tuple[tuple[int | None, re.Pattern[str]], ...]`; `check_boundary` treats `None` as full remainder (`lo = 0`, `hi = len(subject)`; existing clamps already handle bounds). Only readers of these fields are `boundary_spec.py` itself plus `tests/unit/test_coverage_remediation.py:651-663` (asserts non-emptiness only — unaffected).
3. **#71 item 2: uniform `grammar_index`, stable sort does the rest.** Set tuple position-2 to `grammar_index[grammar.name]` for every match (candidate-attributed included; `cand_name` is already carried separately in position-3 and becomes `RecognizedRep.grammar.grammar_name`). Python sort stability preserves insertion order within equal keys. Known parity tripwire: same-start candidate matches previously ordered by `cand_idx` (flat order), now by deduped-insertion order — if any Date vector pins the old order, carry flat consumption order as an explicit final tiebreak rather than reverting.
4. **L6 rescoped to `nfd_pos` only.** `View.offsets` is pinned by `tests/unit/test_scan_context.py:29` + `tests/unit/test_coverage_remediation.py:509-513` and documented as invariant in `paxman/core/AGENTS.md` (Kernel invariants); `check_boundary_compiled` is `return check_boundary(...)` (`boundary_spec.py:344`) pinned by `tests/property/test_boundary_compiled_parity.py` — deleting either means deleting tested surface for zero gain: KEEP both, record rationale on #73. The discovery `(size, mtime_ns)` cache already re-hashes when `mtime_ns % 1_000_000 == 0` (`discovery.py:163-171`): stale-tick concern already mitigated, no change, record on #73.
5. **L3 + #71 items 3–4 deferred, not dropped.** L3 backtracking needs blowup analysis + ADR-level decision (backtracking vs documented unambiguous-leaf invariant); items 3–4 need hypothesis corpus tuning blocked on the Language parity flake. Rationale goes on #73/#71 when this slice lands.

---

### Task 1: L1 — bracket-escape parsing (#73)

**Files:** `paxman/core/grammar/boundary_spec.py:32-92`, `tests/unit/test_boundary_spec.py`

**Goal:** `\uXXXX` / `\xNN` / `\UXXXXXXXX` lower exactly; malformed falls back to regex.

- [ ] Failing tests in `tests/unit/test_boundary_spec.py`: `test_pattern_to_chars_unicode_escape` (`_pattern_to_chars(r"[\w\u2212]")` contains `\u2212`), `test_pattern_to_chars_hex_escape` (`_pattern_to_chars(r"[\x41]") == frozenset({"A"})`), `test_pattern_to_chars_negated_none` (`_pattern_to_chars("[^ab]") is None`), `test_pattern_to_chars_malformed_escape_falls_back` (`[\u12]` / `[\xZZ]` / `[\U00110000]` → `None`, never literal `u`/`x`). Run: `uv run pytest tests/unit/test_boundary_spec.py -v` → FAIL (escapes mis-parsed).
- [ ] Implement: parse the three escape forms in `_chars_from_bracket` (validate hex length, hex digits, `<= 0x10FFFF`; malformed → `raise ValueError`); catch in `_pattern_to_chars` → `return None`. Verify: targeted tests PASS; shipped-preset parity — `uv run pytest tests/unit/test_boundary_spec.py tests/unit/test_coverage_remediation.py tests/property/test_boundary_compiled_parity.py -q` → PASS (no preset changes path: every `\u2212` preset also contains `\+`).

### Task 2: L2 — quantifier-aware width windowing (#73)

**Files:** `paxman/core/grammar/boundary_spec.py:147-170,202-249,269-324`, `tests/unit/test_boundary_spec.py`

**Goal:** Quantified multi-char guards check the full remainder instead of an underestimated window.

- [ ] Failing test: `test_estimate_width_quantifier_returns_none` (`_estimate_width(r"\w+") is None`, `_estimate_width(r"\d{2,3}") is None`, `_estimate_width("[ab]+") is None`) plus `test_quantified_guard_catches_distant_violation` (synthetic `BoundarySpec(left=(r"\w+",))` where the 1-char window misses but full-slice catches — the issue's acceptance case). Run: `uv run pytest tests/unit/test_boundary_spec.py -k "width or quantif" -v` → FAIL.
- [ ] Implement: `_estimate_width` → `int | None` (strip `[...]` spans, then `None` on `*+?{|(`); widen `left_multi`/`right_multi` element type to `int | None`; `__post_init__` passes `None` through; `check_boundary` uses full remainder when `None`. Depends on: Task 1 (same file, adjacent lines — rebase, don't parallelize). Verify: `uv run pytest tests/unit -q` → PASS; strict pyright clean on the widened tuple types.

### Task 3: L6 remainder — delete `nfd_pos` (#73)

**Files:** `paxman/core/grammar/normalizers.py:299-305`, `tests/unit/test_normalizers.py` (existing suite as guard)

**Goal:** Remove the write-only accumulator; change nothing else.

- [ ] Delete `nfd_pos = 0` and `nfd_pos += seg_len` (loop var `seg_len` stays — it feeds `nfd_orig`). No new test needed (no observable behavior; coverage must not drop). Verify: `uv run pytest tests/unit/test_normalizers.py tests/capabilities/country -q` → PASS (CountryNameFold's consumer); `uv run ruff check paxman/core/grammar/normalizers.py && uv run pyright` → clean.

### Task 4: #71 item 2 remainder — single ordinal space for `_recognize` ordering

**Files:** `paxman/engine/orchestrator.py:396-434`, `tests/unit/test_dedup_scoping.py` or `tests/unit/test_kernel_hardening.py`

**Goal:** Candidate-attributed and plain matches sort in one ordinal space; candidate attribution (`grammar_name == candidate name`) unchanged.

- [ ] Failing test (the issue's acceptance): mixed `CandidatesMatcher(strategy="all")` + `LexiconMatcher` grammars through `_recognize`, asserting total order `(start, end, active-set index, grammar name)` and `RecognizedRep.grammar.grammar_name == candidate name` for candidate matches. Run: targeted test → FAIL (mixed `cand_idx` vs `grammar_index` key).
- [ ] Implement: tuple position-2 = `grammar_index[grammar.name]` for all matches (delete the `cand_idx` position-2 assignment; `cand_name` position-3 logic untouched). If the Date `01/02/2026` parity vectors pin the old same-start candidate order, add flat-consumption order as an explicit final sort tiebreak instead of reverting. Verify: new test PASS; `uv run pytest tests/capabilities/date tests/unit/test_dedup_scoping.py -q` → PASS; then full `uv run pytest -q` → green (ordering touches all 18 capabilities — no targeted-only verification).

### Task 5: Docs ride-along — MacAddress guide (#149) + URL guarantee (#144)

**Files:** `docs/user/capabilities/mac_address.md` (create), `docs/user/capabilities/index.md:42`, `docs/user/capabilities/url.md:5-46`

**Goal:** Close the user-visible docs gap for a shipped capability; stop overclaiming URL preservation.

- [ ] `mac_address.md` mirroring `language.md:11-175` section structure (recognizes/does-not / canonical output + `output_format` table: `colon` default, `hyphen`/`bare`/`cisco` encodings, `eui64` same-entity expansion per `paxman/capabilities/MacAddress/contract.py:35-36` + `capability.py:47-58`; `bit_reversed` removal + migration note per `docs/adr/0010-re-entry-fixed-point-invariant.md`; contract — no grammar toggles; statuses — `bit_reversed` → ContractError; notebook snippet with executed output via `uv run python`; provenance IEEE Std 802-2024 §8.2 + RFC 7042 per `paxman/capabilities/MacAddress/rules/ieee_802_ed2024.py:34-49`). Index row `:42` points at the new guide (drop forthcoming stub). Verify: every snippet executed with `uv run python`, `uv run ruff format --check docs/` if applicable.
- [ ] `url.md`: qualify line 5 (`preserving percent-encoding byte-for-byte` → encoded dot segments `%2e`/`%2e%2e` are removed during parsing, verified `canonicalize('https://example.com/a/%2e/b')` → `…/a/b`, code `paxman/capabilities/URL/parsing.py:593-598`) and lines 7/29-30 (opaque paths: scheme-case normalized, non-ASCII UTF-8 percent-encoded per `parsing.py:684-685` — verify with a runnable `mailto:` + non-ASCII demo before wording). Style follows the `money.md:156-159` Limitations pattern ( Moon: state behavior, give example, no spec ruling needed). Verify: demos executed, wording matches observed output exactly.

### Task 6: Changelog + full gate

**Files:** `CHANGELOG.md:9-13` (Unreleased/Fixed)

- [ ] Entries: kernel L1/L2/`nfd_pos`/ordering-key hardening (no live-behavior change except coherent cross-grammar ordering) + MacAddress guide + URL docs qualification. Gate: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest` → all green; coverage `≥95` on `paxman/core, paxman/capabilities, paxman/engine, paxman/api`. Commit per task (`fix(kernel): … (#73)`, `fix(engine): … (#71)`, `docs: … (#144, #149)`); record L3/items-3-4/`offsets`-keep rationales as comments on #73/#71 when landing.
