# Baseline established: mission set; prior knowledge is regex-only

Session 1 set the mission: onboarding-level fluency in paxman's recognition (grammar) layer so the
user can read `paxman/capabilities/*/grammar/` and the `paxman/core/grammar/` kernel unaided. The
user reports comfort with regular expressions and no parser-tool experience; teach via regex
bridges first, parser theory second. Success signals were defined as hand-predicting spans,
explaining kernel pieces line-by-line, and tracing one input end-to-end.

**Implications**: Skip foundational regex material entirely; when introducing span logic, normalizers,
and boundary specs, anchor each to its nearest regex analogue before generalizing. Do not assume
trie/Aho-Corasick familiarity when reaching LexiconMatcher (teach FlashText concept fresh, citing
arXiv:1711.00046).
