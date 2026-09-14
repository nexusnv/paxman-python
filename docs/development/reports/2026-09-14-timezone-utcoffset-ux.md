# UX Experiment — Timezone + UtcOffset (100 inputs each, public API only)

**Date:** 2026-09-14
**Method:** black-box, as a library user. 100 inputs per capability (55 clean / 45 garbage each, seeded RNG 20260914, mixed families), run through `paxman.canonicalize()` under 5 contracts per capability (1000 calls total). Contracts exercised: Timezone `default` / `suppress_common_words` / `include_systemv` / `year=2020` / `output_format="link"` (error path); UtcOffset `default` / `output_format="basic"` / `suppress_common_words` / `year=2010` / `output_format="bogus"` (error path). No source code modified; disposable scripts removed after the run.

## Outcome distributions

| Capability / contract | SUCCESS | INVALID | MISSING | Other |
|---|---|---|---|---|
| Timezone default | 34 | 19 | 46 | 1× MultipleMentionsError |
| Timezone suppress | 34 | 19 | 46 | 1× MME (identical) |
| Timezone systemv | 40 | 13 | 46 | 1× MME |
| Timezone year2020 | 0 | 54 | 46 | — |
| Timezone link-format | 0 | 0 | 0 | 100× ContractError (clear message) |
| UtcOffset default | 55 | 7 | 38 | — |
| UtcOffset basic | 55 | 7 | 38 | values differ by format only |
| UtcOffset suppress | 55 | 7 | 38 | identical |
| UtcOffset year2010 | 0 | 62 | 38 | — |
| UtcOffset bogus-format | 0 | 0 | 0 | 100× ContractError (clear message) |

## Findings

1. **Suppression is a verified no-op (good).** default-vs-suppress diffs: **zero** across all 200 inputs. The flag changes nothing in these domains — predictable UX, no surprise suppressions.
2. **`include_systemv` flips exactly its 4 zones (+6 incl. fold/case rows).** `EST5EDT/CST6CDT/MST7MDT/PST8PDT` (+`est5edt`) go INVALID→SUCCESS; nothing else moves. Flag scope is exactly as documented.
3. **Year filtering is total and legible.** `year=2020` (Timezone) and `year=2010` (UtcOffset) convert every SUCCESS to INVALID while MISSING stays MISSING — the rule-drop model is observable and unsurprising.
4. **Contract errors teach.** Both `ContractError` messages name the capability, the bad value, and the legal set — a user immediately knows what to pass.
5. **Refusal design reads correctly in practice.** `EST/CET/IST` → INVALID, `XYZ/America/Narnia` → MISSING, `-00:00` → INVALID, `+05:60`/`+05:00:00`/`++05:00` → MISSING, `Etc/GMT+5` → key under Timezone and MISSING under UtcOffset, `EST then CET` → INVALID (refused mentions don't compete), `US/Eastern then America/Chicago` → MultipleMentionsError with an actionable message. No wrong-SUCCESS observed in 1000 calls.
6. **`basic` is a clean re-encoding.** Statuses identical to default on all 100 inputs; values differ only in rendering (`+05:00` vs `+0500`).
7. **Biggest UX gap: real IANA keys MISSING under the curated subset.** `Canada/Eastern` (→`America/Toronto`), `Etc/GMT-8`, and `US/PACIFIC` (→`America/Los_Angeles`) all return MISSING — valid keys a user reasonably expects to work. This is the documented subset contract behaving as designed, but it is the sharpest edge a real user will hit. Recommend broadening the vendored tables (Language Wave-2 precedent: curated waves + collision audit), not changing any semantics.
8. **No AMBIGUOUS in 1000 rows.** Ambiguity surfaces only as `MultipleMentionsError` (single multi-mention input). Consistent with single-grammar-per-family design; nothing to fix.

## Verdict

Ships as designed. The only action item is data breadth (#7) — a table-extension follow-up, zero behavior or architecture change. Disposable scripts (`ux_gen.py`, `ux_run.py`, inputs, results log) removed from /tmp after this report was written.
