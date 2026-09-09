# Coordinates Capability Implementation Plan

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. Review gate: `paxman-momus-review` (plan), `paxman-oracle-review` (after impl).

**Goal:** Add the `Coordinates` capability (17th shipped): recognize every attested human spelling of a WGS 84 latitude/longitude point (decimal pairs, hemisphere letters, DMS/DDM, Geo URIs, ISO 6709 strings, lon-first GeoJSON pairs), validate strictly (structure + range), and return one canonical lat-first decimal pair with per-publication provenance.

**Architecture:** Single `coordinates_recognition` PipelineGrammar (StandardPre + RegexStage) with four disjoint alternation branches — bare pair (decimal/DMS/DDM with hemisphere letters), Geo URI, ISO 6709 string-expression, GeoJSON bracketed lon-first pair — all emitting one frozen `CoordinatesNotation` (latitude/longitude decimal strings + optional altitude + `coord_shape` discriminator + `compact`). Three rule files (one per publication: ISO 6709:2022, RFC 5870, RFC 7946) carry five PARSER rules scoped by `coord_shape`; no lookup tables, no registry, no checksum (proved negative in the research report §5.1/§5.4). `format_value()` is the only presentation seam, rendering six output formats including the lon-first GeoJSON inversion. Nothing in `paxman/core` changes; the kernel, orchestrator, and registry are consumed as-is.

**Tech Stack:** Python 3.11+, `decimal.Decimal` (stdlib, exact DMS→DD arithmetic), uv, ruff, strict pyright, import-linter, pytest (markers: unit/capability/integration/property/hypothesis), `paxman/capabilities/Coordinates` via `tools/new_capability.py` scaffolder.

**References:**
- Research report: `docs/development/research/2026-09-01-coordinates-canonicalization.md` (§2.1 inventory = recognition contract; §5.2 = rule map; §6.1 = output formats; §8 = edge cases)
- Scaffolder: `tools/new_capability.py:442-451` (CLI flags)
- Newest capability precedent: `paxman/capabilities/MacAddress/` (notation/contract/capability/grammar/rules verbatim anchors in report Appendix)
- Multi-part numeric precedent: `paxman/capabilities/Money/notation.py:1-47` (`_VALID_*_SHAPES` frozensets), `paxman/capabilities/Money/grammar/__init__.py:13-45` (`classify_amount_shape`)
- Kernel: `paxman/core/grammar/stages.py:49-79` (`StandardPre.empty_guard`, `RegexStage.notation_fn: Callable[[re.Match[str]], NotationT]`), `paxman/core/grammar/boundary.py:54` (`word_only`), `paxman/core/grammar/pipeline.py:17`
- Rule metadata enforcement: `paxman/core/domain.py:246-271` (`__init_subclass__` six attributes, frozenset types), `paxman/core/domain.py:36-47` (`Provenance`)
- Engine: `paxman/engine/orchestrator.py:426-458` (`_dedup_spans` longer-wins), `:590-648` (`_enforce_single_value_invariant`)
- Conventions: `HOW_TO_ADD_NEW_CAPABILITY.md` §5 (one file per publication), §6 (capability), §7 (contract), §10 (test strategy); `AGENTS.md` anti-patterns (no ignore-comments in `paxman/`, no `output_format` in rules, frozen+slots notation)

**Branch:** `feature/coordinates` (cut from `dev`; not a hotfix — no worktree from tag needed)

---

## Locked Design Decisions (from research report — do not re-derive)

1. **Canonical form:** lat-first signed decimal degrees, `.` decimal point, minus sign only, quantized to **6 decimal places round-half-even, trailing zeros stripped, `-0` folded to `0`** (RFC 7946 §11.2 guidance; RFC 5870 §3.3 `-0` identity). `compact == f"{lat}, {lon}"` (+ `", {alt}"` when altitude present). All arithmetic via `decimal.Decimal`, never float.
2. **Notation:** `CoordinatesNotation(latitude: str, longitude: str, altitude: str | None, coord_shape: str, compact: str)` — frozen+slots; `coord_shape` ∈ `{"dd", "ddm", "dms", "iso6709", "geo_uri", "geojson"}` validated against a module-level frozenset in `__post_init__` (MoneyNotation precedent). Input always captured lat-first; `coord_shape="geojson"` records that the input was lon-first so `format_value("geojson_pair")` can re-invert losslessly.
3. **One grammar, four branches:** `_GEO_BODY | _ISO_BODY | _JSON_BODY | _PAIR_BODY`, branch order geo→iso→json→pair, all under one `(?ai:(?:(?:COORDS?|LAT(\/LON)?)[\s:-]+)?(?P<core>…))` label-fused body with `BoundaryGuard.word_only()` lookarounds. Hemisphere letters `[NSEWnsew]` front/back/suffix; pair `SEP = [\s,;/]+` (geopy-verbatim class); DMS units `°`/`D`/`*`, `′`/`'`/`m`, `″`/`"`/`s` (plus `''`→`″` pre-fold inside the builder, not the text).
4. **Strict units:** minutes < 60 and seconds < 60 (diverges from validator.js `|60` tolerance — injectivity rationale, report §13.4). Sign+hemisphere both present → consistent `SUCCESS`, contradictory `INVALID`.
5. **Ranges are rule-level, not regex-level:** lat ∈ [−90, 90], lon ∈ [−180, 180]; out-of-range → `INVALID` (RFC 5870 §9.1). **Never normalize longitude mod 360** (report §13.9).
6. **CRS policy:** `crs=wgs84` (case-insensitive) or absent → OK; `CRSWGS_84` → OK; any other CRS label → `INVALID` (no silent datum transform, report §5.4/§13.7). Geo-URI altitude `0` is a real altitude (RFC 5870 unknown-altitude rule affects emission only, not recognition).
7. **Provenance split:** `rules/iso_6709_ed2022.py` (PUBLICATION ISO 6709:2022; rules `Section 6-coordinate-structure`, `Section Annex-h-string-expression`), `rules/rfc_5870_ed2010.py` (`Section 3.3-geo-uri-validity`), `rules/rfc_7946_ed2016.py` (`Section 3.1.1-position`). All `RuleStrategy.PARSER`, all `target_semantics = frozenset({"coordinates_recognition"})`, all `requires_features = frozenset()`.
8. **Contract:** `DEFAULT_OUTPUT_FORMAT = "decimal"`; `OFFERED_OUTPUT_FORMATS = frozenset({"iso6709", "geo_uri", "geojson_pair", "dms", "dm"})`; `capability_name = "coordinates"`.
9. **DEFER list (do NOT implement):** European comma-decimals, Unicode minus U+2212, MGRS/Plus Codes/geohash (report §2.1 rows 25–27). REJECT: single components, >3 components, homoglyphs.
10. **No `output_format` token anywhere in `paxman/capabilities/Coordinates/rules/`** (CI source-scan). No `# type: ignore`/`# noqa` in `paxman/` source.

## File Structure

Scaffolder generates 13 files + wiring (Task 0); tasks then fill them. Nothing outside this list is touched.

- Create: `paxman/capabilities/Coordinates/__init__.py` — exports `Coordinates`, `CoordinatesNotation` (scaffold, verify)
- Create: `paxman/capabilities/Coordinates/notation.py` — filled Task 1
- Create: `paxman/capabilities/Coordinates/contract.py` — filled Task 2
- Create: `paxman/capabilities/Coordinates/capability.py` — filled Task 8
- Create: `paxman/capabilities/Coordinates/grammar/__init__.py`, `grammar/coordinates_recognition.py` — filled Tasks 3–4
- Create: `paxman/capabilities/Coordinates/rules/__init__.py`, `rules/iso_6709_ed2022.py`, `rules/rfc_5870_ed2010.py`, `rules/rfc_7946_ed2016.py` — filled Tasks 5–7
- Modify: `paxman/capabilities/__init__.py` — sorted `Coordinates` export (scaffolder does it; Task 9 verifies)
- Test: `tests/capabilities/coordinates/{test_notation,test_contract,test_grammar,test_rules,test_capability}.py` — scaffold stubs, filled Tasks 1–8
- Test: `tests/integration/test_coordinates_pipeline.py` — created Task 10
- Test: `tests/property/test_coordinates_properties.py` — created Task 11
- Modify: `CONTEXT.md` — Coordinates glossary rows (Task 12)
- Modify: `CHANGELOG.md` — Added entry (Task 12)
- Docs: README capability table — regenerate with `tools/generate_readme_table.py` (Task 12)

No `paxman/core` change. No `rules/data/` or `grammar/data/` (no registry — report §11).

---

### Task 0: Scaffold — `tools/new_capability.py` (HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

**Files:** everything in File Structure marked "scaffold".

- [ ] Run:
  ```bash
  uv run python tools/new_capability.py Coordinates --name coordinates \
    --authority "ISO" --spec-name "ISO 6709" \
    --spec-url "https://www.iso.org/standard/75147.html" \
    --publication-year 2022 --spec-version "2022" --default-format decimal
  ```
- [ ] Verify: `uv run pytest tests/capabilities/coordinates -q` → scaffold stubs PASS; `uv run python -c "from paxman.capabilities import Coordinates; print(Coordinates)"` → imports. `git add -A && git commit -m "feat(coordinates): scaffold capability via new_capability.py"`.

### Task 1: Notation — frozen+slots dataclass with shape validation

**Files:** `paxman/capabilities/Coordinates/notation.py`, `tests/capabilities/coordinates/test_notation.py`

Depends on: Task 0.

- [ ] Failing tests first: `test_frozen_slots_hash` (immutability + hashability + `__slots__`), `test_valid_shapes_construct`, `test_invalid_shape_raises_value_error` (`coord_shape="utm"` → `ValueError`), `test_compact_consistency` (`compact == f"{lat}, {lon}"` alt-free), `test_minimal_fields`. Run: `uv run pytest tests/capabilities/coordinates/test_notation.py -v` → Expected: FAIL.
- [ ] Implement exactly:

  ```python
  from dataclasses import dataclass

  _VALID_SHAPES = frozenset({"dd", "ddm", "dms", "iso6709", "geo_uri", "geojson"})


  @dataclass(frozen=True, slots=True)
  class CoordinatesNotation:
      """WGS 84 coordinate - decimal pair plus input-family discriminator.

      ``latitude``/``longitude`` are sign-normalized decimal-degree strings
      (minus only, no trailing zeros, -0 folded to 0), lat-first regardless of
      input order. ``altitude`` is metres as a decimal string or None.
      ``coord_shape`` records the recognized input family so rules can apply
      the owning publication's structural law and ``format_value`` can invert
      lon-first GeoJSON input losslessly.
      """

      latitude: str
      longitude: str
      altitude: str | None
      coord_shape: str
      compact: str

      def __post_init__(self) -> None:
          if self.coord_shape not in _VALID_SHAPES:
              raise ValueError(f"invalid coord_shape: {self.coord_shape!r}")
  ```
- [ ] Verify: `uv run pytest tests/capabilities/coordinates/test_notation.py -v` → PASS. Commit: `feat(coordinates): notation with coord_shape discriminator`.

### Task 2: Contract — DEFAULT/OFFERED formats, create_contract common block

**Files:** `paxman/capabilities/Coordinates/contract.py`, `tests/capabilities/coordinates/test_contract.py`

Depends on: Task 1.

- [ ] Failing tests: `test_default_output_format_decimal`, `test_offered_excludes_default` (`"decimal" not in OFFERED_OUTPUT_FORMATS`), `test_resolve_output_format_iso6709` (`create_contract(output_format="iso6709").output_format == "iso6709"`), `test_rejects_unknown_format` (pytest.raises), `test_capability_name_frozen`, `test_create_contract_keyword_only` (positional call → `TypeError`). Run → FAIL.
- [ ] Implement:

  ```python
  from collections.abc import Sequence
  from dataclasses import dataclass, field
  from typing import ClassVar

  from paxman.core.contract import CapabilityContract


  @dataclass(frozen=True)
  class CoordinatesContract(CapabilityContract):
      DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "decimal"
      OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
          {"iso6709", "geo_uri", "geojson_pair", "dms", "dm"}
      )
      capability_name: str = field(default="coordinates", init=False)


  def create_contract(  # re-exported on the capability in Task 8
      *,
      excluded_rules: Sequence[str] | None = None,
      pinned_rules: Sequence[str] | None = None,
      year: int | None = None,
      output_format: str | None = None,
      extra_grammars: Sequence[str] | None = None,
      suppress_common_words: bool = False,
  ) -> CoordinatesContract:
      return CoordinatesContract(
          excluded_rules=tuple(excluded_rules) if excluded_rules else (),
          pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
          year=year,
          output_format=output_format,
          extra_grammars=tuple(extra_grammars) if extra_grammars else (),
          suppress_common_words=suppress_common_words,
      )
  ```
- [ ] Verify: targeted PASS, then `uv run pytest tests/capabilities/coordinates -q`. Commit: `feat(coordinates): contract with six output formats`.

### Task 3: Grammar — decimal/DMS/DDM pair branch (the wide human surface)

**Files:** `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py`, `tests/capabilities/coordinates/test_grammar.py`

Depends on: Task 1. `RegexStage.notation_fn: Callable[[re.Match[str]], NotationT]` (`paxman/core/grammar/stages.py:67`).

- [ ] Failing tests (one positive per research §2.1 RECOGNIZE pair-branch row + negatives): `test_decimal_comma_pair`, `test_decimal_semicolon`, `test_decimal_slash`, `test_decimal_whitespace_sep`, `test_parenthesized_pair`, `test_hemisphere_front`, `test_hemisphere_back`, `test_hemisphere_lowercased`, `test_signed_and_hemisphere_consistent`, `test_dms_unicode_symbols` (`40° 26′ 46″ N 79° 58′ 56″ W`), `test_dms_ascii_quotes` (`23 26' 22" N`), `test_dms_double_apostrophe_seconds` (`39°20'' 0''`-style from geopy corpus), `test_dms_letter_units` (`23 26m 22s N`), `test_ddm_fraction_on_minutes` (`40° 26.767′ N`), `test_zero_padded_fixed_width` (`05° 09' 01'' S 008° 03' 02'' E`), `test_degenerate_no_space_dms` (`10°59'26''123N000°00'04''902W`), `test_label_prefix_span_includes_label` (`UT: N 39°20' 0'' / W 74°35' 0''` — assert `match.raw_text` starts with `UT:`), `test_negative_zero_folded` (`-0.0,122.0` → lat `"0"`), `test_span_half_open_raw_text_equality`, `test_single_component_missing` (`48.8566` → []), `test_fullwidth_comma_missing`, `test_percent_suffix_missing`, `test_midrun_glue_missing` (`ID48.8577,2.295` → []), `test_multiple_matches_two_pairs`. Run: `uv run pytest tests/capabilities/coordinates/test_grammar.py -v` → FAIL.
- [ ] Implement the grammar skeleton:

  ```python
  import re
  from decimal import Decimal

  from paxman.capabilities.Coordinates.notation import CoordinatesNotation
  from paxman.core.grammar.boundary import BoundaryGuard
  from paxman.core.grammar.pipeline import PipelineGrammar
  from paxman.core.grammar.stages import RegexStage, StandardPre

  # --- shared component fragments (module scope, uncompiled) ---------------
  _DEC = r"\d{1,3}(?:\.\d{1,7})?"
  _SEP = r"[\s,;/]+"
  _HEMI = r"(?P<hemi_front_lat>[NSEWnsew])?[\s:]?"
  # pair branch: two {HEMI SIGN DEC UNITS TAIL} components joined by SEP
  # carrier branches added in Task 4; _BODY_ALTS grows then.
  ```

  Builder `_notation(match)` semantics (locked, deterministic): capture degrees/minutes/seconds/fraction/sign/hemisphere per component; `Decimal` arithmetic `deg + min/60 + sec/3600` (fraction attaches to the last present unit — python-iso6709 semantics); hemisphere `S`/`W` negates; sign and hemisphere must agree (disagreement still *recognizes* — the rule rejects in Task 5, per grammar-claims/rule-rejects split; record both facts by treating hemisphere as authoritative and preserving the sign in the raw text only); quantize `Decimal("0.000001")` round-half-even, `.normalize()`, fold `q == 0 → Decimal(0)`; emit `CoordinatesNotation(...)` with `coord_shape="dd"|"ddm"|"dms"` by unit presence. `''` → `″` handling: the pattern accepts `''` via the seconds-unit class alternation (no text mutation — Stages must not mutate text).
- [ ] Verify: grammar tests PASS; `uv run pytest tests/capabilities/coordinates -q`. Commit: `feat(coordinates): pair-branch recognition grammar`.

### Task 4: Grammar — carrier branches (Geo URI, ISO 6709, GeoJSON) + pipeline wiring

**Files:** `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py` (extend), `tests/capabilities/coordinates/test_grammar.py` (extend)

Depends on: Task 3.

- [ ] Failing tests: `test_geo_uri_2d` (`geo:48.8566,2.3522` → `coord_shape="geo_uri"`), `test_geo_uri_3d_altitude` (`geo:48.2010,16.3695,183` → altitude `"183"`), `test_geo_uri_crs_wgs84_case_insensitive` (`;crs=WGS84`), `test_geo_uri_u_param_ignored_for_value` (`;u=40` same compact), `test_geo_uri_foreign_crs_missing` (`geo:48.8566,2.3522;crs=ed50` → `[]`), `test_iso_decimal_pair_solidus` (`+48.52+002.20/` → `"iso6709"`), `test_iso_degrees_only` (`+00-025/`), `test_iso_minutes_form` (`+1234.7-09854.1/` → `12.578333, -98.901667`), `test_iso_dms_with_altitude` (`+352139+1384339+3776/` → altitude `"3776"`), `test_iso_crs_suffix` (`+27.5916+086.5640+8850CRSWGS_84/`), `test_geojson_lon_first_flipped` (`[2.295, 48.8577]` → lat `"48.8577"`, lon `"2.295"`, `coord_shape="geojson"`), `test_geojson_with_altitude` (`[2.295, 48.8577, 8850.0]` → altitude `"8850"`), `test_geojson_bracket_requires_pair` (`[48.8577]` → []), `test_carrier_branch_disjoint_from_pair` (geo URI body not double-matched as pair — single match per input), `test_grammar_name_and_semantics` (`coordinates_recognition` both), `test_single_value_true`, `test_pre_stage_empty_guard` (whitespace-only input → []).
- [ ] Implement: add `_GEO_BODY`, `_ISO_BODY`, `_JSON_BODY` per research report §4.2 verbatim fragments; assemble `_BODY_ALTS = f"{_GEO_BODY}|{_ISO_BODY}|{_JSON_BODY}|(?:{_PAIR_BODY})"`; wire the class:

  ```python
  class CoordinatesRecognitionGrammar(PipelineGrammar[CoordinatesNotation]):
      name = "coordinates_recognition"
      semantics = "coordinates_recognition"
      single_value = True
      pre = StandardPre[CoordinatesNotation](empty_guard=True)
      regex = RegexStage[CoordinatesNotation](
          pattern=_COORDS_PATTERN, notation_fn=_notation
      )
  ```

  `_COORDS_PATTERN = BoundaryGuard.word_only().lookbehind + _LABEL_FUSED_BODY + BoundaryGuard.word_only().lookahead` with `_LABEL_FUSED_BODY = rf"(?ai:(?:(?:COORDS?|LAT(?:\/LON)?)[\s:-]+)?(?P<core>{_BODY_ALTS}))"` (MacAddress `MAC`-label fusion precedent, `paxman/capabilities/MacAddress/grammar/mac_address_recognition.py:53-71`).
- [ ] Verify: `uv run pytest tests/capabilities/coordinates/test_grammar.py -v` → PASS. Commit: `feat(coordinates): geo/iso/geojson carrier branches`.

### Task 5: Rules — ISO 6709:2022 (structure + Annex H, one file per publication)

**Files:** `paxman/capabilities/Coordinates/rules/iso_6709_ed2022.py`, `tests/capabilities/coordinates/test_rules.py`

Depends on: Tasks 1, 4. Rule metadata enforced at class-definition time (`paxman/core/domain.py:246-271`).

- [ ] Failing tests: `test_publication_provenance` (authority `"ISO"`, specification_name `"ISO 6709"`, kind `"specification"`, reference_url `"https://www.iso.org/standard/75147.html"`, version `"2022"`, lifecycle `"active"`, publication_year `2022`), `test_rule_names_convention` (`"Section 6-coordinate-structure"`, `"Section Annex-h-string-expression"`), `test_strategy_parser`, `test_target_semantics_routes_grammar` (`frozenset({"coordinates_recognition"})`), `test_matches_valid_all_shapes`, `test_rejects_hemisphere_contradiction` (`-41.5 N` → `matches` False), `test_rejects_dms_unit_overflow` (`40° 75′`), `test_rejects_out_of_range` (`91.0, 2.0` lat; `48.8577, 181.0` lon), `test_iso_rejects_wrong_digit_width` (3-digit latitude integer part in ISO form), `test_annex_h_rejects_missing_solidus` (`+48.52+002.20` bare), `test_annex_h_rejects_foreign_crs` (`CRSPS56/` → False; `CRSWGS_84` → True), `test_normalize_agreement` (all rules return identical `normalize()` for the same point — dedup precondition), `test_normalize_default_is_decimal_pair`, `test_normalize_folds_negative_zero`, `test_matches_never_raises` (feed notation with `altitude=None`, empty strings, non-numeric garbage — no exception), `test_requires_features_empty`.
- [ ] Implement: module-level `PUBLICATION = Provenance(...)` per the provenance row above; two `Rule[CoordinatesNotation]` classes. `Section 6-coordinate-structure.matches()`: per-`coord_shape` dispatch — `dd`/`ddm`/`dms`/`iso6709` re-derive each component with `Decimal`, check hemisphere/sign consistency, minutes < 60, seconds < 60, lat ∈ [−90, 90], lon ∈ [−180, 180]; ISO digit-width table (lat 2/4/6, lon 3/5/7 integer digits). `SectionAnnexHStringExpression.matches()`: only `coord_shape == "iso6709"`; re-checks the carrier law the regex left loose (trailing solidus already consumed by regex; CRS label family). Both `normalize()` return `notation.compact` after `-0` fold re-application. No `output_format` token anywhere in the file.
- [ ] Verify: `uv run pytest tests/capabilities/coordinates/test_rules.py -v` → PASS. Commit: `feat(coordinates): ISO 6709:2022 rules`.

### Task 6: Rule — RFC 5870 geo-URI validity

**Files:** `paxman/capabilities/Coordinates/rules/rfc_5870_ed2010.py`, `tests/capabilities/coordinates/test_rules.py` (extend)

Depends on: Task 5 (test conventions established).

- [ ] Failing tests: `test_publication_provenance` (authority `"IETF"`, specification_name `"RFC 5870"`, kind `"specification"`, reference_url `"https://www.rfc-editor.org/rfc/rfc5870.txt"`, version `"5870"`, lifecycle `"active"`, publication_year `2010`), `test_rule_name_section_33_geo_uri_validity`, `test_matches_geo_uri_shapes` (2-D, 3-D, `;crs=wgs84`, `;crs=WGS84`), `test_rejects_non_wgs84_crs_shape` (geo-URI notation whose raw CRS was not wgs84 — the builder records it, e.g. reject via `coord_shape`-adjacent fact: keep a `crs` note in the notation is NOT allowed (frozen shape); instead the grammar only claims wgs84-missing-or-equal geo URIs, and this test asserts `matches` True for claimed shapes and the negative lives in Task 4's `test_geo_uri_foreign_crs_missing` → grammar returns []), `test_normalize_agreement_with_iso_rules`, `test_strategy_parser`.
- [ ] Implement: `PUBLICATION = Provenance(authority="IETF", specification_name="RFC 5870", kind="specification", reference_url="https://www.rfc-editor.org/rfc/rfc5870.txt", version="5870", lifecycle="active", publication_year=2010)`; `class Section33GeoUriValidity(Rule[CoordinatesNotation])` — `matches()`: `coord_shape == "geo_uri"` plus range re-check (same `_in_range` helper as Task 5 — put the helper in `rules/__init__.py` as `_range.py`-free module-level function `component_in_range(value: str, lo: str, hi: str) -> bool` used by all three rule files; it imports nothing cross-capability). `normalize()` → `notation.compact`.
- [ ] Verify: targeted PASS; full rules file suite PASS. Commit: `feat(coordinates): RFC 5870 geo-uri rule`.

### Task 7: Rule — RFC 7946 position (lon-first ordering sanity)

**Files:** `paxman/capabilities/Coordinates/rules/rfc_7946_ed2016.py`, `tests/capabilities/coordinates/test_rules.py` (extend)

Depends on: Task 6.

- [ ] Failing tests: `test_publication_provenance` (IETF / `"RFC 7946"` / `"https://www.rfc-editor.org/rfc/rfc7946.txt"` / version `"7946"` / 2016 / active / specification), `test_rule_name_section_311_position`, `test_matches_geojson_shapes` (2-element, 3-element), `test_normalize_matches_other_rules`, `test_strategy_parser`, `test_output_format_token_absent` (grep-level: `assert "output_format" not in Path(...).read_text()` — presentation-purity vector).
- [ ] Implement: `PUBLICATION` constant + `class Section311Position(Rule[CoordinatesNotation])`: `coord_shape == "geojson"` + ≤3-element fact (regex already enforces; re-assert via `altitude is not None`-shaped check) + shared range check. `normalize()` → `notation.compact`.
- [ ] Verify: `uv run pytest tests/capabilities/coordinates/test_rules.py -q` → all PASS. Commit: `feat(coordinates): RFC 7946 position rule`.

### Task 8: Capability — wiring + `format_value()` presentation seam (six formats)

**Files:** `paxman/capabilities/Coordinates/capability.py`, `tests/capabilities/coordinates/test_capability.py`

Depends on: Tasks 2, 4, 5–7.

- [ ] Failing tests: `test_wiring_counts` (1 grammar, 4 rules), `test_grammar_and_rule_names_convention`, `test_notation_frozen_hashable_slots` (re-assert at capability layer), `test_format_value_decimal_identity` (`"48.8577, 2.295"`), `test_format_value_iso6709` (→ `+48.8577+002.2950/`, fixed 2/3 integer digits, trailing `/`), `test_format_value_geo_uri` (→ `geo:48.8577,2.295`), `test_format_value_geojson_pair_lon_first` (→ `[2.295, 48.8577]`; for `coord_shape != "geojson"` still emits lon-first from canonical), `test_format_value_dms_unicode` (→ `48°51′28″N 2°17′42″E`, hemisphere letter immediately after digits, no internal spaces — ISO 6709 Annex D), `test_format_value_dm` (→ `48°51.462′N 2°17.7′E`), `test_format_value_altitude_emitted_when_present` (all formats, using `+27.5916+086.5640+8850CRSWGS_84/` as input), `test_format_value_altitude_omitted_when_none`, `test_format_value_round_trip` (`format_value(format_value(x, f), f)` idempotent for `decimal`/`iso6709`/`geo_uri`), `test_create_contract_factories` (keyword-only, common block passthrough).
- [ ] Implement: `CoordinatesCapability(Capability[CoordinatesNotation])` with `name = "coordinates"`, `get_grammars`/`get_rules` per research §6.2 verbatim shape, static `create_contract` delegating to Task 2's factory, and `format_value` dispatching on resolved `output_format`. All six formats derive from `notation` (not re-parsing `value`); DMS/DDM rendering quantizes from the exact `Decimal` pair; hemisphere letters derived from sign. Default `"decimal"` is identity.
- [ ] Verify: `uv run pytest tests/capabilities/coordinates -q` → PASS. Commit: `feat(coordinates): capability wiring and format_value seam`.

### Task 9: Registration & exports — `paxman/capabilities/__init__.py` completeness

**Files:** `paxman/capabilities/__init__.py` (scaffolder-wired; verify), `tests/unit/test_capability_exports.py` (existing test enforces).

- [ ] Verify: `uv run pytest tests/unit/test_capability_exports.py -v` → PASS (export-count invariant now 17). `uv run python -m paxman coordinates "48.8577, 2.295"` → canonical decimal via CLI smoke. If the scaffolder's sorted-insert missed `__all__` ordering, fix by hand — the export test is the oracle.
- [ ] Commit (only if edited): `feat(coordinates): complete capability exports`.

### Task 10: Integration — full pipeline through `run_capability()`/`canonicalize()`

**Files:** `tests/integration/test_coordinates_pipeline.py` (create)

Depends on: Task 8. Uses the autouse `_clean_registry` fixture (integration/e2e convention).

- [ ] Tests: `test_success_decimal_pair` (status SUCCESS, canonical `48.8577, 2.295`, span-bearing, provenance lists ISO/IETF publications), `test_success_dms_coalesces_with_decimal` (`"48.8577,2.295 and 48°51′27.7″N, 2°17′42″E"` → single candidate via dedup — normalize agreement), `test_success_geojson_input` (`"[2.295, 48.8577]"` → same canonical as decimal), `test_invalid_out_of_range` (`"geo:94,0"` → INVALID with rule attribution), `test_invalid_hemisphere_contradiction`, `test_invalid_foreign_crs` (`"+27.59+002.29CRSPS56/"`), `test_missing_single_component`, `test_missing_sibling_shapes` (`"$48.86"`, `"48.86 kg"`, `"2024-09-01"` → MISSING for coordinates capability), `test_ambiguous_two_distinct_points` (pytest.raises `MultipleMentionsError`), `test_determinism_version_stamp` (same input twice → identical `ExecutionResult.version_stamp`), `test_output_format_geojson_round_trip` (`canonicalize(..., contract=create_contract(output_format="geojson_pair"))`).
- [ ] Verify: `uv run pytest tests/integration/test_coordinates_pipeline.py -v` → PASS. Commit: `test(coordinates): pipeline integration`.

### Task 11: Property tests — hypothesis invariants

**Files:** `tests/property/test_coordinates_properties.py` (create)

Depends on: Task 10.

- [ ] Tests: `test_self_canonical` (lat ∈ [−90,90], lon ∈ [−180,180] at ≤6dp via `st.decimals(...)`/`st.floats`-seeded `Decimal` strings → `canonicalize(compact)` yields identical compact), `test_encodings_dedup_to_one_value` (same point spelled decimal / hemisphere-letter / DMS-with-quantization-safe-units → one candidate), `test_format_idempotent` (all six formats f(f(x)) == f(x) on the decimal branch), `test_random_strings_missing` (`st.text()` → MISSING with high probability; assert no crash), `test_unit_overflow_invalid` (minutes/seconds ≥ 60 → INVALID or MISSING, never SUCCESS).
- [ ] Verify: `uv run pytest tests/property/test_coordinates_properties.py -q` → PASS. Commit: `test(coordinates): property invariants`.

### Task 12: Docs — CONTEXT.md glossary, README table, CHANGELOG

**Files:** `CONTEXT.md`, `CHANGELOG.md`, README capability table, `docs/` user docs table pointer if present.

- [ ] CONTEXT.md: add Coordinates rows to the Notation table (decimal / DMS / DDM / Geo URI / ISO 6709 / GeoJSON) per the repo convention that CONTEXT.md is kept in sync with shipped capabilities (AGENTS.md § Notes).
- [ ] README: `uv run python tools/generate_readme_table.py` and inspect the diff.
- [ ] CHANGELOG.md: `### Added` entry for `coordinates` capability with the three publications.
- [ ] Verify: `uv run pytest -q` (docs changes must not break source-scan or export tests). Commit: `docs(coordinates): glossary, readme table, changelog`.

### Task 13: Full pre-PR gate

**Files:** none (verification only).

- [ ] Gate:
  ```bash
  uv run ruff check . && uv run ruff format --check . \
    && uv run pyright && uv run import-linter lint \
    && uv run pytest -q
  ```
- [ ] Coverage: `uv run pytest --cov=paxman --cov-report=term-missing -q` then `uv run coverage report --include="paxman/capabilities/Coordinates/*" --fail-under=95`.
- [ ] Purity spot-checks: `grep -rn "output_format\|type: ignore\|noqa" paxman/capabilities/Coordinates/rules/` → 0 hits; `grep -rn "from paxman.capabilities" paxman/capabilities/Coordinates/` → only intra-package imports (import-linter is authoritative).
- [ ] Commit any gate fixes; hand off to `paxman-oracle-review` on the branch diff.

---

## Test-Vector Appendix (frozen vectors, all verbatim from fetched sources)

| Input | Expected | Source |
|---|---|---|
| `48.8577, 2.295` | SUCCESS → `48.8577, 2.295` | self-canonical |
| `41.5 N -81.0 W` | SUCCESS → `41.5, -81` | geopy docstring |
| `-41.5 S, 81.0 E, 2.5km` | SUCCESS, alt `2.5`? — NO: altitude-with-unit is a pair-branch *display* form; v1 carries altitude only as metre value from carriers → recognize pair, altitude None (recorded scope cut, see below) | geopy docstring |
| `40° 26′ 46″ N 79° 58′ 56″ W` | SUCCESS → `40.446111, -79.982222` | Wikipedia GeoCoordConv |
| `05° 09' 01'' S 008° 03' 02'' E` | SUCCESS → `-5.150278, 8.050556` | Wikipedia zero-padded |
| `+1234.7-09854.1/` | SUCCESS → `12.578333, -98.901667` | python-iso6709 corpus |
| `+27.5916+086.5640+8850CRSWGS_84/` | SUCCESS, alt `8850` | ISO 6709 Annex H |
| `geo:48.198634,16.371648;crs=wgs84;u=40` | SUCCESS → `48.198634, 16.371648` | RFC 5870 §6.2 |
| `[2.295, 48.8577]` | SUCCESS → `48.8577, 2.295` | RFC 7946 §9 mapping |
| `geo:94,0` | INVALID | RFC 5870 §9.1 |
| `-41.5 N` | INVALID | hemisphere contradiction |

**Scope cut recorded (v1):** geopy's `2.5km`-unit altitude suffix on the bare-pair branch is recognized for the *pair* but the altitude value is dropped (None) — carrying unit-converted altitude across `km/mi/ft/nm` is deferred with the other unit-conversion extensions (research §13.8 covers carrier-borne metre altitudes only). Mention this in the grammar tests as `test_unit_altitude_pair_recognized_altitude_none`.

---

## Self-Review (performed before saving)

1. **Spec coverage:** research §2.1 RECOGNIZE rows → Tasks 3–4 tests (24 positives); §5.2 rule map → Tasks 5–7; §6.1 formats → Task 8; §8 edge cases → Tasks 3–4, 10; §12 test strategy → Tasks 3–4 (grammar), 5–7 (rules), 8 (capability), 10 (integration), 11 (property); §13 open decisions → Locked Decisions 1–10. No gap found.
2. **Placeholder scan:** no TBD/TODO/"appropriate" — every task names files, test names, and `uv run` verify. The one deferred altitude nuance is explicitly scoped, not a placeholder.
3. **Type consistency:** one `CoordinatesNotation` shape (Task 1) consumed by grammar (Tasks 3–4), rules (Tasks 5–7), and capability (Task 8); one `CoordinatesContract` (Task 2) with the locked DEFAULT/OFFERED; `Provenance` rows match research §5.1 Citation Details verbatim.
4. **Momus gate (dry):** references carry paths:lines; every task startable from scaffolder output; each QA block has tool + command + expected outcome → OKAY.
