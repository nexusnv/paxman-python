# Release notes — v0.5.0 (draft, from `v0.4.1..dev`, 75 commits)

## Summary

Paxman 0.5.0 adds two capabilities — IANA **Timezone** identifiers and ISO **UtcOffset** values (20 shipped) — plus Language compositional descriptions, a Money shared-symbol guard, BIC phrase filtering, ADR-0012 candidate qualification, and kernel hardening with no shipped behavior regressions. Contract compatibility is preserved; four result changes need golden-sample review (see Migration). Docs cover all 20 capabilities with citations, glossary, and migration notes.

## Highlights

- **Timezone + UtcOffset** (MILESTONE #3): `US/Eastern` → `America/New_York`; `UTC+5` → `+05:00`.
- **Language compositional phrases**: `Singapore Chinese in traditional script` → `AMBIGUOUS {zh-Hant-SG, id}` by default, `SUCCESS zh-Hant-SG` suppressed; `Chinese (Traditional, Singapore)` → direct `SUCCESS`.
- **ADR-0012 candidate qualification**: syntax-only ghosts disqualified (`Serbo-Croatian` → `SUCCESS sh`).
- **Money `$` honesty**: resolves only to the symbol's own CLDR candidates.

## Added

- **Timezone** — IANA Time Zone Database 2026d; 2 grammars, 4 rules; canonical IANA key; `include_systemv` flag; abbreviations refused → `INVALID`.
- **UtcOffset** — ISO 8601-1:2019 + RFC 3339; canonical `+HH:MM`; offered `basic` `+HHMM` (re-enters).
- **Language description grammar** — `in`-forms + parenthesized forms; Wave-2 script/region tables; `nb` renders `Norwegian Bokmål`.
- **User guides** for BIC/Coordinates/Element/IBAN/ORCID/MacAddress/Timezone/UtcOffset; citations + glossary + migration coverage for all 20.

## Changed

- Language bare 5–8 letter runs `INVALID` → `MISSING`; Money `$`+non-candidate `SUCCESS` → `INVALID`; BIC lowercase end-of-text phrases no longer claim; ADR-0012 reclassifications (`xx-yyyyy` → `INVALID`, `en-x-private` → `INVALID` without flag).

## Fixed

- UtcOffset `+05:60` truncation (`SUCCESS +05:00` → `MISSING`); bare `GMT` unclaimed → `SUCCESS GMT`; kernel Slice A/G/H (bracket escapes, boundary widths, combinator backtracking, ordering space) with no shipped vector moves; docstring closeout (#107) pinned by presence test.

## Deprecated / Removed / Security

- None. (`national`/`bit_reversed` de-offers shipped in 0.4.0.)

## Breaking changes & migration

No contract-shape breakage. Four golden-sample updates (see `docs/user/migration.md` Unreleased–0.5.0 section): Language bare 5–8 + compositional ambiguity; Money non-candidate `$`; BIC phrase filter; ADR-0012 reclassifications. Fixes: #15, #71, #73, #106, #107, #144, #145, #147, #148, #149, #150, #161, #162, #165.

## Quality dashboard

- Tests: 5168 passed, 2 skipped · Coverage 95.79% (floor 95) · pyright 0 errors · ruff (CI scope) clean · import-linter kept.
- Experiment: 123-row corpus ×2 byte-identical; 12/12 re-entry; 12/12 CLI parity; provenance complete.
- Benchmarks: uniformly elevated vs `baseline.json` on this box (incl. `freeze` +29%) — environment noise, no scenario-specific regression; re-run on CI runner.

## Install & upgrade

- `uv add paxman==0.5.0` / `pip install paxman==0.5.0`; Python 3.11+.
- Re-run golden samples (data-driven result changes above); pin `paxman` version + store `version_stamp` where reproducibility matters.

## Known limitations

- #154 e2e CLI-scan flake: unreproduced (20+ green loops), deferred past 0.5.0, still tracked.
- JST abbreviations out of the Timezone v1 curated subset → `MISSING` by design; Windows zone names deferred; multi-token regions + `thai` deferred (#148).
