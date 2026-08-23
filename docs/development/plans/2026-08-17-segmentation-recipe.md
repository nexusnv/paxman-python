# Segmentation Recipe Doc — Implementation Plan

| **Title** | `docs/recipes/segmentation.md`: the caller-owned split-then-canonicalize pattern for multi-entity input |
| **Date** | 2026-08-17 |
| **Status** | Planned — not started |
| **Branch** | `docs/segmentation-recipe` (one commit per task) |
| **Origin** | `docs/reports/2026-08-17-architecture-review.md` §9 Near-Term item 4 (§6 table: "Multi-entity extraction — correctly out of scope; a companion recipe would serve the demand without bending scope") |
| **Depends on** | Nothing (fully independent; uses only existing public API — ADR-0004, `MultipleMentionsError`, spans) |
| **Supersedes** | Nothing |

> **For agentic workers.** Docs-only plan — **all tasks are RED-exempt**
> (no production behavior; the TDD mandate exempts prompt/doc-text work).
> Task 3 is a verify-only gate with **no commit**. The one nontrivial
> requirement is §2 Task 1's **execution check**: the doc's worked example
> must be RUN, not just written. Commit with the exact messages given.

> **Progress**
>
> | Task | Status | Commit |
> |------|--------|--------|
> | Task 1 — write `docs/recipes/segmentation.md` (+ execution check) | ☐ pending | |
> | Task 2 — link from README + ARCHITECTURE | ☐ pending | |
> | Task 3 — final gate (no commit) | ☐ pending | |

---

## §1 Cross-Part Contract

### Goal

Serve the "find all X in this text" demand **without bending scope**
(M1/ADR-0004): a user-facing recipe documenting the split-then-canonicalize
loop — caller segments, paxman canonicalizes each mention, spans and
`MultipleMentionsError` make the loop robust — plus an explicit scope
statement so nobody plans a document-extractor on top of the library.

### D-Decisions (locked — do not revisit without a new plan)

- **D1 — Location: `docs/recipes/segmentation.md`** (new `docs/recipes/`
  dir; user-facing recipe, distinct from internal `docs/development/`).
  Linked from README and ARCHITECTURE (Task 2).
- **D2 — Content contract (exact section outline):**
  1. **The invariant** — one entity per `canonicalize()` call is the
     product contract (ADR-0004): AMBIGUOUS means a genuine single-mention
     spec conflict; multi-entity input raises `MultipleMentionsError`
     instead of masquerading as ambiguity. Segmentation is caller-owned by
     charter, not a missing feature (link the review report §8 M1).
  2. **The recipe** — segment → canonicalize per mention → reassemble,
     with a complete, runnable worked example (Email; code block below is
     the canonical text):
     ```python
     import re

     import paxman
     from paxman.capabilities import Email
     from paxman.core.discovery import register_capability
     from paxman.core.domain import Resolution
     from paxman.core.errors import MultipleMentionsError

     register_capability(Email())
     contract = Email.create_contract()

     # Caller-owned segmentation: a coarse pattern finds mention candidates…
     EMAIL_LIKE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


     def canonicalize_emails(text: str) -> list[tuple[str, str, str]]:
         """Return (raw, canonical, position) for every email mention."""
         out: list[tuple[str, str, str]] = []
         for m in EMAIL_LIKE.finditer(text):
             try:
                 result = paxman.canonicalize(m.group(0), contract)
             except MultipleMentionsError:
                 # Your segmenter let two mentions through — tighten it.
                 raise
             if result.status is Resolution.SUCCESS:
                 out.append((m.group(0), result.canonicalized_value or "", str(m.start())))
         return out
     ```
  3. **Span mechanics** — `ExecutionResult.span` /
     `Candidate.span` are half-open `[start, end)` offsets into the text
     passed to THAT call; with per-mention calls, mention-local spans plus
     the segmenter's offsets reassemble document positions.
  4. **Signals, not failures** — per mention, `SUCCESS` / `INVALID` /
     `MISSING` / `AMBIGUOUS` keep their exact meanings;
     `MultipleMentionsError` is a segmenter bug detector (two mentions in
     one slice), never a paxman state.
  5. **Pitfalls** — (a) naive text splitting (commas/newlines) vs
     capability-shaped patterns; (b) your segmenter and paxman's grammars
     may disagree on boundaries: feed the segment, trust the status
     (honest INVALID/AMBIGUOUS beats pre-filtering); (c) don't widen a
     segment to "give context" — extra mentions raise
     `MultipleMentionsError`.
  6. **Scope statement** — extraction stays caller-owned forever (M1);
     this recipe is the sanctioned pattern, and requests for built-in
     document extraction are out of scope by charter, not by limitation.
- **D3 — Execution check is mandatory.** The worked example must be run
  verbatim via `uv run python -c` (or a temp script under `/tmp`) before
  Task 1's commit: assert `canonicalize_emails("Contact a@Foo.com or b@bar.org")`
  returns two SUCCESS tuples with canonical values `a@foo.com`,
  `b@bar.org`. Evidence pasted into the PR. A recipe with an unrunnable
  example is worse than no recipe.
- **D4 — Uses only existing public API.** `register_capability(Email())`
  (not the planned `register_all_shipped()` — this plan must not depend on
  the bootstrap plan). If the bootstrap plan has already landed, a
  follow-up may modernize the snippet; not required here.

### Out of scope

- Any code change to `paxman/` (no extraction helpers, no new API — the
  whole point is serving demand WITHOUT scope bend).
- Segmentation utilities shipped in the library.
- Recipes for other topics (batching, streaming) — future docs, if asked.

---

## §2 Tasks

### Task 1 — `docs: add segmentation recipe for multi-entity input`

**RED-exempt (docs).** Create `docs/recipes/segmentation.md` per the D2
outline — all six sections, the exact code block from D2 §2, links to
ADR-0004 (`docs/adr/0004-single-value-invariant.md`), the review report
(§8 M1), and README's "Resolution Status" section.

**Execution check (D3 — mandatory, run before committing):**
```bash
uv run python -c "
<the D2 code block verbatim, then:>
print(canonicalize_emails('Contact a@Foo.com or b@bar.org'))
"
```
Expected output: two tuples, canonical values `a@foo.com` and `b@bar.org`.
Capture the output as PR evidence. If it does not run, fix the DOC, never
the library.

**Verify.** `test -f docs/recipes/segmentation.md`; the execution-check
output matches expectations; all relative links resolve (spot-check the
two ADR/report paths).

**Commit.** `docs: add segmentation recipe for multi-entity input`

### Task 2 — `docs: link the segmentation recipe from README and ARCHITECTURE`

**RED-exempt (docs).**

1. `README.md` — new short subsection **"Working with Multi-Entity Input"**
   after "Error Handling": two sentences (paxman resolves one mention per
   call; multi-entity input raises `MultipleMentionsError`) + link to
   `docs/recipes/segmentation.md` for the split-then-canonicalize pattern.
2. `ARCHITECTURE.md` — §"Resolution Semantics" (locate by section name —
   the heading sits around line 180; insert after the AMBIGUOUS row
   discussion at the end of the section): one sentence pointing to the same recipe as the
   caller-owned answer to multi-entity input (ADR-0004 companion).

**Verify.** `grep -n "segmentation" README.md ARCHITECTURE.md` → both hit;
links resolve from repo root.

**Commit.** `docs: link the segmentation recipe from README and ARCHITECTURE`

### Task 3 — Final gate (no commit)

Docs-only change, but the gate proves nothing regressed:

```bash
uv run ruff check paxman/ tests/ && uv run ruff format --check paxman/ tests/ \
  && uv run pyright && uv run import-linter lint && uv run pytest -q
git status --porcelain   # only the two committed docs files in history; tree clean
```

(CI lints `paxman/ tests/` only — the new `docs/recipes/` file is outside
ruff scope by design; verify its markdown links by hand.)

---

## §3 Traps

1. **The example must run verbatim (D3).** The biggest risk in a recipe
   doc is a plausible-but-unexecuted snippet. The Email regex in D2 is
   deliberately a COARSE caller pattern (not RFC-grade) — that's the
   doc's own Pitfall (a): keep it coarse and say so, don't "improve" it
   into a false RFC 5322 claim.
2. **Don't imply extraction support (M1 framing).** Every draft sentence
   that reads like "paxman helps you find entities" must be rewritten to
   "YOUR segmenter finds candidates; paxman canonicalizes each". The
   scope-statement section is the load-bearing part of the doc.
3. **No library edits, period.** If the execution check surfaces a real
   library bug, STOP — report it separately; do not fix it inside a
   docs plan.
4. **Span semantics accuracy.** With per-mention calls, `result.span` is
   relative to the SLICE, not the original document — the doc must say
   this explicitly (D2 §3) or users will double-offset.
5. **Link targets are commit-relative.** `docs/reports/…` and `docs/adr/…`
   paths must be correct from `docs/recipes/` (i.e., `../reports/…`,
   `../adr/…`).

---

## §4 Definition of Done

- [ ] Two commits on `docs/segmentation-recipe` with the exact messages.
- [ ] `docs/recipes/segmentation.md` exists with all six D2 sections; the
      worked example's execution-check output captured as evidence.
- [ ] README + ARCHITECTURE link the recipe; all links resolve.
- [ ] Zero changes outside `docs/` (README/ARCHITECTURE are root docs —
      no `paxman/`, `tests/`, or config files touched).
- [ ] Full CI-authoritative gate green (unchanged code, unchanged results).
