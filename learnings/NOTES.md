# Teaching notes

> **Workspace location:** all teaching materials live in `learnings/`
> (`learnings/MISSION.md`, `learnings/lessons/`, `learnings/reference/`,
> `learnings/assets/`, `learnings/learning-records/`, this file, `RESOURCES.md`) —
> not the repo root. Future sessions: create new lessons/records there.
>
> **Publishing a lesson:** the user serves `learnings/` statically. New lessons MUST
> also be registered in `learnings/index.html`'s `COURSE.lessons` manifest (set
> status "live" + fill slug) and should link back to `../index.html` in their crumbs.

## Facts established
- Session 1 (2026-08-27): Mission set = onboarding curiosity about paxman's recognition layer.
- Prior knowledge: comfortable with regular expressions; no lexer/parser-tool experience (no ANTLR/Lark/etc.).
  Bridge strategy: map every kernel concept onto its closest regex analogue first, then generalize.

## Proposed lesson arc (adjust per progress)
1. **L0001 — Spans**: `Grammar.recognize()` → `list[RecognitionMatch]`, half-open `[start, end)`,
   recognition ≠ meaning. *(built)*
2. **Views & the offset discipline**: `ScanContext`, lazy `View` objects, normalizers
   (`CaseFold`, `AccentStrip`, `StripSeparators`), why `state.text` never mutates,
   length-preserving vs offset-map normalization. Regex analogue: matches on transformed text
   mapped back to original indices. *(built)*

## Progress capture (added session 2026-08-27)
- `learnings/serve.py`: static server + POST /api/progress capture endpoint + `--digest`
  teacher summary. Widgets (`span-picker.js`, `answer-check.js`) emit telemetry onto
  `PaxmanTeach.telemetry`; `assets/progress.js` aggregates → schema-1 JSON per lesson.
- Serving command is now `uv run python learnings/serve.py` (plain static servers still work —
  captures degrade to localStorage + chip export).
- Teacher workflow: after learner plays lessons, run `uv run python learnings/serve.py --digest`;
  wrong picks (`miss_picks`) and failed retrieval questions are the calibration signals for the
  next lesson. Latest capture per round/question wins (replay overwrite).
3. **Matchers**: `LexiconMatcher` (alternation ≤500 tokens / trie >500, FlashText-style
   longest-match-first, word-anchored), `RegexMatcher`, `ScannerMatcher`
   ((ctx,pos)→(end,notation)|None, non-overlapping advance).
4. **Boundaries & anchors as data**: `BoundarySpec`/`check_boundary` = declarative lookaround;
   `AnchorSet`. Regex analogue: `(?<!...)`(?!...)`.
5. **Pipeline & policy**: `StandardPre`/stages, engine containment dedup ("longer wins"),
   ordering `(start, end, active-set index, grammar name)`; read `HOW_TO_ADD_NEW_GRAMMAR.md`.
6. **Practicum**: trace a real input through Date or Phone grammars; optionally draft a grammar.

## Preferences observed
- None yet beyond constraints recorded in MISSION.md. Watch for pacing feedback.

## Open questions
- Does the user want hands-on repo work (edit test fixtures, run pytest) inside lessons? Ask during L0001 debrief.
