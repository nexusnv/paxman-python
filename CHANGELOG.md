# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Coordinates — WGS 84 coordinates:** new capability with one grammar (`coordinates_recognition`) covering decimal pairs, hemisphere letters, DMS/DDM, Geo URI `geo:`, ISO 6709 string-expression, and GeoJSON lon-first pairs, and four parser rules backed by ISO 6709:2022 (`Section 6-coordinate-structure`, `Section Annex-h-string-expression`), RFC 5870 (`Section 3.3-geo-uri-validity`), and RFC 7946 (`Section 3.1.1-position`). Canonical form is lat-first signed decimal degrees quantized to 6dp round-half-even with `-0` folded to `0`; six output formats `decimal` (default), `iso6709`, `geo_uri`, `geojson_pair`, `dms`, `dm`.
- **Bootstrap — MacAddress registration activated:** `register_all_shipped()` / `paxman --list` now include the `mac_address` capability (17 shipped capabilities). The registration had been deliberately deferred on `dev`; it ships together with Coordinates in this release.

### Breaking

- **MacAddress — de-offer `bit_reversed` output format (#123, ADR-0010):** `MacAddressContract(output_format="bit_reversed")` now raises `ContractError` (was `SUCCESS` with per-octet bit-swap). The format is an involution (`f(f(x)) == x`) and therefore not a fixed point — `canonicalize(V, bit_reversed)` re-flips to `W != V`. Per ADR-0010 an offered format must re-enter as itself, so the view is no longer offered. The `Capability.format_value()` `bit_reversed` branch and `_bit_reverse_octet` helper have been removed (no dead code; off-contract direct use would previously have silently succeeded). Migrate: use the default `colon` form for storage and round-tripping; compute the Token-Ring display locally if needed.
- **Phone — `national` now requires `default_country` (#123, ADR-0010):** `PhoneContract(output_format="national")` without a NANP `default_country` (currently `"US"`) now raises `ContractError` (was `SUCCESS` with a non-re-enterable bare NSN). Per ADR-0010 Scope decision 2 re-entry is unconditional for default contracts; a default (country-less) contract must never produce a non-re-enterable `national` V (`2125551234` → `INVALID` on re-entry without country). Callers needing `national` must supply `default_country="US"`; `PhoneContract(output_format="national", default_country="US")` re-enters as a fixed point and remains offered. Migrate: add `default_country="US"` where `national` is used, or use `e164`/`rfc3966` for country-less contracts.

### Fixed

- **ORCID — fix re-entry for `compact` bare-digit output (#123, ADR-0010):** `ORCIDRecognitionGrammar` now accepts both hyphenated `0000-0002-1825-0097` and compact `0000000218250097` (and `https://orcid.org/0000000218250097`). Previously `format_value(..., "compact")` produced a bare 16-digit value that the grammar did not recognize (`MISSING` on re-entry). The grammar now has an alternation `(?ai:\d{4}-\d{4}-\d{4}-\d{3}[\dX]|\d{15}[\dX])` and normalizes compact to hyphenated `XXXX-XXXX-XXXX-XXXC` for validation. Re-entry is now a fixed point (`canonicalize(V, compact) == SUCCESS V`). No breaking change — `compact` remains offered, now re-enterable.
- **Phone — fix re-entry fixture for `national` (#123, ADR-0010):** `tests/property/test_reentry_invariant.py` now uses a valid NANP fixture `+12125551234` (was fictional `+12125550123` in `555-01xx` reserved range, always `INVALID` even with country) and carries `default_country="US"` for the Phone row so the lossy `national` rendering (`2125551234`) can re-enter via the NANP rule. The format `national` is context-dependent (bare NSN discards the country code); its re-entry is contract-relative per ADR-0010 Scope decision 2. Contract now enforces the invariant — `national` without a NANP `default_country` is rejected at construction (see Breaking above); `national` remains offered when country is supplied, now verifiably re-enterable under its producing contract. For non-NANP E.164 (e.g. `+33`, `+44`) requested as `national` the capability now preserves the E.164 value instead of stripping to a bare non-NANP number that cannot re-enter (`142345678` → `MISSING`); two-pass `national` re-entry is now a fixed point for all E.164 countries (#127).
- **Coordinates — review hardening (oracle + adversarial audit):** recognition
  never fabricates values: structural observations (sign/hemisphere contradiction,
  hemisphere axis mismatch, DMS unit overflow, ISO 6709 digit width, missing
  Annex H solidus, foreign CRS) are recorded on `CoordinatesNotation.defects`
  and rejected by the rule layer. Whitespace-separated bare number runs
  ("pages 12 40", phone numbers) are no longer recognized as coordinates
  (whitespace pairs require hemisphere/sign affinity on both components); a
  match can no longer start at the fractional tail of a dotted number
  (`192.168.1.1, 10.0` → MISSING, was a wrong-value SUCCESS); `geo:`-prefixed
  tails are never salvaged by the pair branch; a foreign CRS label in a Geo
  URI or ISO 6709 string resolves INVALID (no silent datum transform) instead
  of being silently accepted or dropped; `--48.5, 2.3` sign glue is MISSING;
  `iso6709` output pads fractions to the 4-place Annex H presentation width.

## [0.3.2] - 2026-09-03

> **Hotfix release — no new capability added.** ISBN + ISSN deep-audit fixes and one kernel label-matching fix (all contract-compatible).

### Fixed

- **ISBN — deep audit (#116, #117):** truncated hyphen continuations (`1 0-306-40615-2`, `978-…` cut mid-group) are now rejected via a trailing `(?![-]\d)` guard on both grammars instead of matching a truncated prefix (→ `MISSING`); `_find_length` duplication extracted to `find_registrant_length` in `rules/data/range_message.py` (emitted by `tools/regenerate_isbn_range_data.py`, back-compat alias kept); `Rule.normalize()` / `_to_isbn13` now `try/except ValueError` → return input instead of raising; recognition-vs-validation table clarified in `docs/user/capabilities/isbn.md`.
- **ISSN — deep audit (#125, #126):** truncated hyphen-digit continuations (`0317-8471-2`) rejected via the same trailing-guard class; new user doc `docs/user/capabilities/issn.md` (every shipped capability now has a page); capability/contract/notation/rule docstrings expanded (7th edition 2022-06 provenance, weights 8→2, `X=10`).
- **Kernel — LabelMatcher span swallow (#130):** a boundary-rejected span no longer consumes input, so valid label matches starting inside it surface. Concretely, an IBAN paper-form tail absorbing ` IBAN` hid the labeled match in `'...0000 IBAN:AA0000000000000'` (new reported core-only `(31, 46)`, legacy `(26, 46)` with label) — now both report `(26, 46, 'IBAN:AA0000000000000')`. Only IBAN + ISSN consume `LabelMatcher`; parity corpora pin the behavior.

## [0.3.1] - 2026-09-02

### Fixed

- **IP — deep audit (#113, #114):** mixed IPv6 with embedded IPv4 (`::ffff:192.0.2.1`, `64:ff9b::192.0.2.1`, `::192.0.2.1`) now recognized as a single IPv6 candidate via Las32 branches (RFC 4291 §2.2 / RFC 5952 §5); previously truncated to `::ffff:192` and returned `AMBIGUOUS ['::ffff:192','192.0.2.1']`. The trailing `192.0.2.1` is still emitted by the IPv4 grammar (`\b` boundary) so `canonicalize("::ffff:192.0.2.1")` yields `AMBIGUOUS ['::ffff:192.0.2.1','192.0.2.1']` — prefer the IPv6 value until engine cross-grammar dedup exists (documented, no IPv4 `\b` → lookaround without ADR). Triple-colon / double-`::` over-match (`:::1`, `2001:db8::1::2`) remains intentionally broad and sanitizes to `INVALID` (deferred low).
- **IP — notation & rules:** `IPNotation` now `@dataclass(frozen=True, slots=True)` + field docs (C1, D1); both IPv4/IPv6 `normalize()` now `try/except ValueError` (IPv4 also `IndexError`) → return input instead of raising (B3, C2); provenance URLs migrated `tools.ietf.org` → `datatracker.ietf.org` (D4); docstrings clarify RFC 1123 §2.1 dotted-decimal and RFC 4291 §2.2 architecture for `LS32`.
- **Docs — IP:** `docs/user/capabilities/ip.md` now documents mixed addresses, leading-zero normalization (`010.020.030.040` → `10.20.30.40`), overlap/over-broad notes and RFC 4291 provenance; `README.md` IP section updated; `CONTEXT.md` IP authorities and `IPNotation` entry updated; `docs/user/citations.md` IP URLs migrated to `datatracker`.

## [0.3.0] - 2026-08-31

> **Housekeeping release — no new capability added.** This release consolidates kernel hardening, phone/BIC fixes, Unicode property stage, and versioned docs infrastructure.

### Added

- **Core — UnicodePropertyStage (#51):** build-time range generator for
  `\p{Sc}`, `Script=Han` etc., vendored in `unicode_ranges.py`; pilot
  parity for SI `°µΩÅ` vs Sc and Han vs Latin (incl. supplementary).

### Fixed

- **Kernel — data-driven stripped-view handling (#87, #88):** the recognition kernel no
  longer special-cases the idna view by name. Views carry `stripped_chars` as data
  (`IDNAFold` declares `"\t\n\r"`), and the engine loop / scanner branch on
  `view.stripped_chars`. Community grammars using other stripped views now get the same
  re-absorption and boundary-deferral semantics, and views without the flag get neither.
  The boundary re-check on the original text now runs at the pre-extension end, so a
  right-side guard sees the immediate neighbor instead of the character after a
  re-absorbed stripped run (#88). No shipped capability changes behavior (parity suites
  green).
- **Kernel — grammar-path error contract (#66):** internal lookup failures
  (`KeyError`/`IndexError`) from grammars, candidate matchers, combinator leaves,
  and predicates now surface as `RecognitionError` (or are swallowed at the
  per-candidate/leaf boundary, as before) instead of escaping as raw exceptions.
  The rules path keeps its `except Exception → ValidationError` contract.
- **Kernel — `BoundarySpec` negated bracket classes (#67):** `[^...]` fragments no
  longer lower to an inverted positive char set; they fall back to the compiled
  regex path, preserving negated semantics.
- **Kernel — boundary char sets exact vs `re` (#62):** `\d` lowers to Unicode `Nd`
  (was ASCII-only), and class escapes (`\w`, `\d`, `\s`) carry a compiled non-BMP
  fallback so neighbor decisions are exact across the whole codepoint space without
  an import-time scan. Hot path unchanged (empty fallbacks short-circuit; BMP
  neighbors never compute `ord`).
- **Kernel — `NormalizerSequence` no-expansion invariant (#63):** composition asserts
  unit-width offsets and strictly increasing starts; expanding normalizers fail fast
  instead of silently mis-mapping end offsets.
- **Kernel — bounded NFD cache (#64):** the per-char NFD memo is an
  `lru_cache(maxsize=8192)`; the unbounded input-keyed `_NFD_CACHE` dict is gone.
- **Phone — E.164 window 32 → 64 for spaced numbers (#65):** the
  `max_window` was too tight for 15-digit numbers with separators
  between every digit (e.g. "+1 - 2 - 3 …" = 44-58 chars, was truncated
  at 32). Raised to 64 (worst case 58 + margin) so spaced E.164 is
  fully recognized with correct span.
- **BIC — grouped display (#41):** recognizes SWIFT paper form
  `AAAA BB CC [XXX]` with single spaces (e.g. `DEUT DE FF` →
  `DEUTDEFF`, `BNPA FR PP XXX` → `BNPAFRPPXXX`); double spaces remain
  `MISSING`.
- **Kernel — scanner right-gap deferral (#99):** `ScannerMatcher` now defers
  view-level boundary checks on both left and right gaps for stripped views
  (previously only left), so a stripped char immediately right of a hit does
  not cause view-level over-rejection; the engine's original-text re-check
  governs. Unreachable with shipped grammars (URL `idna` is left-only).

### Changed

- **Kernel — `Normalizer` protocol declares `stripped_chars` (#87):** community
  normalizer implementations should declare it (default `None`; `""` is treated as "no
  stripping").
- **Kernel — `CandidatesMatcher` single-pass boundary filter (#68):** `result` and
  `stored_flat` are now derived in one pass; `check_boundary` runs once per span instead
  of twice. No behavior change.
- **Docs — versioned docs (#96):** `website/` renamed to `docs_site/`; Pages
  deploys now ship every version listed in `docs_site/versions.json`
  (`/vX.Y.Z/` immutable per tag, `/latest/` from `dev`, root redirects
  to `/latest/` and `/stable/` to the last pinned version) with an in-site
  version switcher.

## [0.2.2] - 2026-08-30

### Fixed

- **IBAN — complete SWIFT registry + per-country lengths (#69):** the empty 90-code registry stub is replaced by the full SWIFT IBAN Registry (111 country rows, R99 Dec 2024 / R100 Oct 2025 via the iban.com mirror, 8 May 2026), generated into `paxman/capabilities/IBAN/rules/data/iban_registry.py` from `paxman/shared_data/iban_registry_snapshot.json` with `tools/regenerate_iban_registry_data.py --check` drift gating. Per-country fixed lengths are now enforced before MOD 97-10, so wrong-length IBANs with a valid checksum (`DE20`, `NO16`, `NI92`) are `INVALID` instead of `SUCCESS`; `FP` (French Polynesia, not an IBAN jurisdiction) is removed; the Nicaragua vector is corrected (`NI79…`, 28); 2024 West/Central African jurisdictions (`AO`, `BF`, `DZ`, …) are now recognized.
- **Email — RFC 5322 §3.4.1 validation tightened (#60):** the local/domain patterns now enforce `dot-atom-text = 1*atext *("." 1*atext)` and per-label hyphen discipline, so `user..test@example.com`, `user.@example.com`, `user@.example.com`, `user@-example.com`, `user@example-.com`, and `user@example..com` are `INVALID` (were wrongly `SUCCESS`). Obfuscated recognition matches the `at`/`dot` keywords case-insensitively (`USER AT EXAMPLE DOT COM` → `SUCCESS` under `include_obfuscated=True`); `EmailNotation` is now frozen + slots; provenance URLs moved to datatracker.
- **Currency — audit clarifications (#55):** symbol ordering and the case-exact symbol contract are documented with non-examples (`us$` → `MISSING`, `Lei` → `INVALID` via the code path); ISO 4217 temporal-filtering note (edition-year vs 2026-01-01 snapshot); `default_currency` cross-reference on `CurrencyCapability`; `tools/regenerate_currency_data.py` template synced and case-exact grammar tests added.
- **Language BCP-47 parity corpus (#90):** the frozen legacy reference matched grandfathered tags inside longer syntactically-valid tags (`zh-min` inside `zh-min-nan00`), failing hypothesis CI randomly on any branch. The legacy reference is amended to the kernel's longest-valid-prefix semantics (grandfathered tags are exact-match) with divergent inputs pinned in the golden corpus. Kernel behavior unchanged.
- **Country name parity corpus (#92):** the hypothesis corpus asserted byte parity between the whole-input legacy `NameGrammar` and the kernel in-text scan outside the legacy's domain (e.g. `:马里`, `Name: 中国`), failing CI randomly. The corpus now gates the kernel by F1 honest behavior per the ADR-0009 Rev.3 exemption, retaining byte parity on the legacy's whole-input domain (verified for all 503 keys). Kernel behavior unchanged.

## [0.2.1] - 2026-08-29

### Fixed

- **URL `absolute_uri_recognition` parity on Python 3.12 (IDNAFold view):** `A\n:0` was incorrectly recognized as `A:0` (newline between scheme and `:` stripped by `IDNAFold`), `A:0\n` was truncated to `A:0` (trailing `\t\n\r` stripped), and `A\nB:0` missed `B:0` due to view-based `SCHEME_CHAR_LEFT` (`[A-Za-z0-9+.\-]`) seeing `A` instead of `\n`. Fixed by (1) rejecting any gap (`\t\n\r`) inside `scheme+colon` via `view.source_starts/ends` in `paxman/capabilities/URL/grammar/absolute_uri_recognition.py:74`, (2) deferring `SCHEME_CHAR_LEFT` to `paxman/core/grammar/engine_loop.py:125` on original text for `view_name=="idna"` (BCP47 `SeparatorFold` `_→-` keeps view check), (3) extending trailing `\t\n\r` in `engine_loop` and `absolute_uri_recognition._url_emit` to match legacy body `[^ <>"…]*` (e.g. `A:0\n` → `A:0\n`). Restores `620 passed` `property` on `3.12` (was `len mismatch 'A\n:0'`) and `25` Starlight pages.

## [0.2.0] - 2026-08-28

Recognition Kernel (ADR-0009 Rev.4). Pre-1.0 minor bump `0.1.0 → 0.2.0` with one
intentional breaking fix (F1) and span-presentation breaking change (two-array
offset maps). All other inputs are byte-identical under the parity gate. See
`docs/user/migration.md` and `docs/adr/0009-recognition-kernel.md` for the full
migration guide.

### BREAKING

- **Country `name_recognition` — F1 correctness fix (ADR-0009):** Whole-input
  country-name lookup moved to an in-text word-anchored trie on the
  `CountryNameFold` view. Short-code grammars (`alpha2`) now honestly compete
  with the name grammar instead of silently winning when the name was invisible
  in prose.

  | Input class | Before (0.1.x) | After (0.2.0) |
  |---|---|---|
  | Exact name, whole input (`"United States"`) | `SUCCESS "US"` | `SUCCESS "US"` — unchanged |
  | Name embedded in prose (`"Ship to United States please"`) | `SUCCESS "TO"` (Tonga) — wrong | `MultipleMentionsError` under a `single_value` contract; both mentions via `paxman.scan()` |
  | Short code as ordinary word (`"to"` in prose) | recognized as alpha-2 | recognized; competes with name mention — no silent win |
  | All other inputs | — | byte-identical (parity gate) |

  Migrate prose with embedded values via `paxman.scan()` or the
  caller-owned split-then-canonicalize recipe (`docs/recipes/segmentation.md`).

- **Two-array offset maps (ADR-0009 Rev.4, breaking in spans only):**
  `Normalizer` now returns `(subject, starts, ends)` with
  `len(starts)==len(ends)==len(subject)` and
  `View.original_span(s, e) -> (starts[s], ends[e-1])` when mapped.
  Trailing dropped punctuation is no longer absorbed into the span:

  | Input | Before | After |
  |---|---|---|
  | `"United States."` name mention | `(0, 14)` `raw_text="United States."` | `(0, 13)` `raw_text="United States"` |
  | `"United States of America,"` | `(0, 25)` includes `,` | `(0, 24)` trimmed |
  | `"+1 (555) 123-4567"` via `StripSeparators` | sentinel `ends[-1]==len(text)` | per-char `ends`, `original_span(0,n)==(0,17)` exact |

  Whole-input canonical values are unchanged; only `span`/`raw_text`
  presentation shifts. `raw_text == text[start:end]` is now an engine
  invariant. Golden samples asserting `(0, 14)` for `"United States."` should
  assert `(0, 13)`.

### Added

- **`paxman.scan(text, contracts) -> ScanResult` batch API + `Mention`/`ScanResult` model + `paxman scan` CLI** — one `ScanContext` substrate pass
  shared across all contracts in the batch; mentions are maximal clusters under
  the existing total-order + containment policy (ADR-0009 §§6, 11, 13).
- **`VersionStamp.recognition_revision`** — hash of the compiled matcher set +
  snapshot SHAs (ADR-0009 §13). Same-snapshot diff signal: if
  `recognition_revision` changes, recognition behavior changed for at least one
  capability even when `paxman_version` is unchanged. Store both fields for
  audit trails (`docs/user/migration.md`).
- **Common-word suppression for `scan()` (ADR-0009 §16, B1)** — off by
  default, additive. `CapabilityContract.suppress_common_words: bool = False`
  (frozen, no slots), forwarded by every `create_contract(..., suppress_common_words=False)`.
  Table `paxman/core/grammar/data/common_words.py:COMMON_WORDS` (67 entries,
  Google 1000 ∩ ISO 3166 α2/α3 + ISO 4217 + ISO 639, `assert len==67`,
  `USD` deliberately excluded). Short-code matchers marked `suppressible=True`
  (`Country` alpha2/alpha3/numeric, `Currency` code, `Language` language_code;
  all `BoundarySpec.WORD`-bounded). Engine skips emit when
  `contract.suppress_common_words and matcher.suppressible and text[span].lower() in COMMON_WORDS`.
  CLI: `paxman scan --suppress-common-words`. Bare-code `canonicalize("to")`
  stays `SUCCESS "TO"` when the flag is off.
- **Recognition Kernel infrastructure (ADR-0009)** — `ScanContext` lazy views,
  `MatcherSpec` 6 kinds (`regex`/`lexicon`/`scanner`/`combinator`/`candidates`/`label`)
  with `BoundarySpec` presets and `AnchorSet` T0 prefilter, two-array
  `Normalizer` protocol, `CandidatesMatcher` (`Date` 4→1 consolidation, strategy
  `"all"` preserving `01/02/2026` `AMBIGUOUS`), snapshot rails
  (`paxman/shared_data/*_snapshot.json` + `tools/regenerate_*` + CI drift gate)
  and derived recognition keys (BIC country codes, Language IANA subset).
- **15 shipped capabilities** — `BIC`, `Country`, `Currency`, `Date`, `Email`,
  `IBAN`, `IP`, `ISBN`, `ISSN`, `Language`, `Money`, `ORCID`, `Phone`,
  `SIUnit`, `URL` (`paxman/api/bootstrap.py:_SHIPPED`, alphabetical; see
  `README.md` capability table). Register via `paxman.register_all_shipped()`
  or `paxman.register_capability(Cap())`.

### Changed

- **Date grammars consolidated 4→1** — ISO 8601, slash-ISO, US, and European
  formats now live in a single `CandidatesMatcher` with `strategy="all"`;
  `README.md` table shows `Date | Dates | 1 (date) | 3`.
- **Performance** — `LexiconMatcher` auto-selects regex alternation (≤~500
  tokens) vs word-anchored dict trie (>~500), measured 2.4–6.5× at 650/820
  tokens; `SIUnit` split-prefix migrated to `seq(prefix, ws, unit)` combinator
  replacing a 19,530-token product trie; `ScanContext` construction moved out
  of the per-grammar hot path for `scan()` batch reuse.

### Removed

- **`PropertyMatcher` / `unicode_ranges` kind** — generator
  `tools/regenerate_unicode_property_data.py` and its snapshot/data modules
  deleted in `8116145` (single-customer kind deferred per ADR-0009 §9.5
  until a second property recurs). No remaining `Property` grammar.

### Fixed

- **Boundary/lexicon correctness** — `BoundarySpec` O(1) frozensets, shared
  `ScanContext` word spans, and trie word-anchoring fix the F1 prose defect
  while preserving the parity gate for all non-F1 inputs.
- **CI drift gates** — 8 drift checks (currency, si_prefix, idna_uts46,
  isbn_range, bic, iban_registry, iana_language, language) + `git diff --exit-code`
  and informational benchmark remain merge-blocking per `.github/workflows/ci.yml`.

### Migrations

Migrate prose with embedded values via `paxman.scan()` or the caller-owned
split-then-canonicalize recipe (`docs/recipes/segmentation.md`). For whole-input
values, no change. Golden samples asserting `(0, 14)` for `"United States."`
should assert `(0, 13)` per two-array offset map. See `docs/user/migration.md`
and `docs/adr/0009-recognition-kernel.md` for the full guide.

## [0.1.0] - 2026-08-22

- Initial release — first-time user experience + publish workflow (Trusted
  Publishing OIDC, `paxman/py.typed` PEP 561, `pyproject.toml` version
  `0.1.0`, tag `v0.1.0`).

[Unreleased]: https://github.com/nexusnv/paxman-python/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/nexusnv/paxman-python/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/nexusnv/paxman-python/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/nexusnv/paxman-python/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/nexusnv/paxman-python/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/nexusnv/paxman-python/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/nexusnv/paxman-python/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/nexusnv/paxman-python/releases/tag/v0.1.0
