# Mission: Reading paxman's recognition layer

## Why
You're onboarding to the **paxman-python** codebase and the recognition (grammar) layer is your
current reading goal. You want to open any file under `paxman/capabilities/*/grammar/` and the
kernel under `paxman/core/grammar/` and understand what you're looking at — without needing to ask
someone what a `RecognitionMatch` is.

## Success looks like
- Hand-predict `[start, end)` spans and `raw_text` a given grammar will emit for a sample input.
- Explain, line by line, how any shipped grammar uses the kernel (`ScanContext`, views, matchers).
- Trace one input through recognition → engine dedup/ordering → validation, naming each seam.
- Stretch goal: add or modify a grammar by following `HOW_TO_ADD_NEW_GRAMMAR.md` unaided.

## Constraints
- Parsing background is **regex only** — teach parser ideas by bridging from regex mechanics
  (`re.finditer`, `.span()`, lookaround), never assume lexer/CFG vocabulary.
- Lessons must be short and interactive, tied to real files in this repo, not generic parsing theory.

## Out of scope (for now)
- Writing a whole new capability (revisit once the recognition layer is fluent).
- Validation-rule internals, provenance/hash construction, CLI/API surface.
