# Paxman Recognition Layer Resources

(This file lives in `learnings/`; links to repo files go one level up via `../`.)

## Knowledge

- [Local: `ARCHITECTURE.md` — Separation of Recognition and Validation + Recognition Pipeline Contract (lines 17–48)](../ARCHITECTURE.md)
  The authoritative statement of what grammars may and may not do, plus the engine's dedup/ordering
  policy ("longer wins", `(start, end, active-set index, grammar name)`). Use for: any question about
  the recognition/validation seam.
- [Local: `HOW_TO_ADD_NEW_GRAMMAR.md`](../HOW_TO_ADD_NEW_GRAMMAR.md)
  Step-by-step spec for adding a grammar to an existing capability, including strategy choice
  (lexicon/regex/scanner) and the rule side of the contract. Use for: lessons on writing grammars.
- [Local source of truth: `paxman/core/domain.py`](../paxman/core/domain.py)
  `Grammar` ABC (~line 299) and `RecognitionMatch` (~line 68). Every claim in lessons about the
  recognition contract is checked against this file.
- [Local: `paxman/core/grammar/` kernel](../paxman/core/grammar/)
  `ScanContext`, views/normalizers, matchers (`LexiconMatcher`, `RegexMatcher`, `ScannerMatcher`),
  `BoundarySpec`. The machinery every shipped grammar composes.
- [Python docs: `re` module](https://docs.python.org/3/library/re.html#match-objects)
  Match objects, `.span()`, lookaround assertions — the user's existing vocabulary, used as the bridge.
- [Paper: "Replace or Retrieve Keywords In Documents at Scale" (FlashText), Vikash Singh, arXiv:1711.00046](https://arxiv.org/abs/1711.00046)
  One-pass dictionary keyword search: complete-word matching only, longest match first, O(N).
  This is exactly what `LexiconMatcher`'s trie mode implements (the code comments call it the
  "FlashText model"). Use for: why the kernel prefers tries over big alternation regexes.
- [Wikipedia: Trie](https://en.wikipedia.org/wiki/Trie)
  Prefix-tree data structure backing large lexicons in paxman.

## Wisdom (Communities)

- [r/learnpython](https://www.reddit.com/r/learnpython/)
  High-volume Python Q&A; good for regex mechanics questions at any depth. Moderated against low-effort answers by community voting.
- [Python Discord](https://discord.com/invite/python)
  Real-time help channels; a place to test explanations of parsing concepts against practitioners.

## Gaps

- No public community exists for paxman itself (private repo, no Discussions/forum found) — for
  paxman-specific wisdom, use the maintainer/team channel or ask me; revisit if a forum appears.
