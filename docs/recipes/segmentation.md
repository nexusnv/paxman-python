# Segmentation Recipe — Multi-Entity Input

> One `paxman.canonicalize()` call resolves one presumed entity. Multi-entity
> input is caller-owned segmentation: split, then canonicalize per mention.

This recipe is the sanctioned pattern for "find all X in this text" demand
without bending Paxman's scope. See [ADR-0004](../adr/0004-single-value-invariant.md)
and the architecture review [§8 M1](../reports/2026-08-17-architecture-review.md) for the charter.

---

## 1. The invariant

One entity per `canonicalize()` call is the product contract ([ADR-0004](../adr/0004-single-value-invariant.md)).
Paxman operates at the *mention* level: the caller ensures the slice passed to
each call contains one presumed entity (or none).

* **`AMBIGUOUS`** means a genuine single-mention spec conflict — one recognized
  span, two authorities disagreeing on its canonical value (e.g. `01/02/2026`
  as `2026-01-02` vs `2026-02-01`).
* **`MultipleMentionsError`** means your input contained two or more separate
  mentions that resolved to different values. It is a segmentation-usage signal,
  not a domain result — it fails fast instead of masquerading as ambiguity.

Segmentation is **caller-owned by charter**, not a missing feature. This is
mandate [M1 in the architecture review §8](../reports/2026-08-17-architecture-review.md)
and the core decision of ADR-0004: multi-entity extraction belongs outside the
library. For the four resolution statuses see [README — Resolution Status](../../README.md#resolution-status).

---

## 2. The recipe

Segment → canonicalize per mention → reassemble.

Your segmenter finds mention *candidates*; Paxman canonicalizes each candidate
and tells you whether it is `SUCCESS`, `INVALID`, `MISSING`, or `AMBIGUOUS`.
Spans and `MultipleMentionsError` make the loop robust — the error fires when
your segmenter let two mentions through.

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


def canonicalize_emails(
    text: str,
) -> list[tuple[str, Resolution, str | None, tuple[int, int] | None]]:
    """Return (raw, status, canonical, absolute_span) for every email candidate."""
    out: list[tuple[str, Resolution, str | None, tuple[int, int] | None]] = []
    for m in EMAIL_LIKE.finditer(text):
        try:
            result = paxman.canonicalize(m.group(0), contract)
        except MultipleMentionsError:
            # Your segmenter let two mentions through — tighten it.
            raise
        abs_span = (
            (m.start() + result.span[0], m.start() + result.span[1])
            if result.span is not None
            else None
        )
        out.append((m.group(0), result.status, result.canonicalized_value, abs_span))
    return out
```

The regex above is **deliberately coarse** — it is a caller-owned candidate
finder, not an RFC 5322 validator. Treat it as a cheap pre-filter; Paxman's
grammars and rules remain the authority on whether a candidate is `SUCCESS`,
`INVALID`, or `AMBIGUOUS`. This is pitfall (a) below: a coarse,
capability-shaped pattern beats naive splitting, but must not pretend to
replace capability validation.

---

## 3. Span mechanics

Every `ExecutionResult.span` and `Candidate.span` is a half-open `[start, end)`
offset into **the slice passed to THAT `canonicalize()` call**, not into the
original document. With per-mention calls, `result.span` is relative to the
SLICE (the single-mention string you handed to `canonicalize()`), e.g. `0`
means "start of this candidate string."

To reassemble document positions, add the segmenter's offset:

* `m.start()` / `m.end()` from your segmenter — document-absolute.
* `result.span` / `candidate.span` — mention-local, slice-relative.

So the document position of a resolved mention is `m.start() + result.span[0]`
when you passed `m.group(0)` as the slice. For `SUCCESS` there is a single
resolved entity and `result.span` is set; for `MISSING`/`INVALID`/`AMBIGUOUS`
there is no single resolved entity and `result.span` is `None` — locate
mentions via per-`Candidate.span` on `AMBIGUOUS` instead.

---

## 4. Signals, not failures

Per mention, the four statuses keep their exact meanings (see
[README — Resolution Status](../../README.md#resolution-status)):

* `SUCCESS` — one canonical value resolved.
* `INVALID` — recognized, but no authority validates it.
* `MISSING` — nothing recognized.
* `AMBIGUOUS` — one mention, multiple authorities disagree.

`MultipleMentionsError` is **not** a Paxman status (it is a `PaxmanError` exception, not a `Resolution` status). It is a segmenter bug
detector: two mentions landed in one slice and they disagree on value. It never
represents Paxman state; it tells you to tighten the segmenter so each slice
holds at most one mention. Handle it as an invariant violation in the caller,
not as a domain outcome to branch on.

Canonical `SUCCESS` output is safe to feed back under a **default** contract — `canonicalize(V, C)` re-resolves `V` to itself for any `output_format` (ADR-0010, #123); custom `pinned_rules`/`excluded_rules`/`year` that drop the validating rule, or `suppress_common_words=True` whole-input common words (e.g. `TO` → `MISSING`) until the A0 exemption lands, break this and remain conditional (#122).

---

## 5. Pitfalls

(a) **Naive splitting vs capability-shaped patterns.** Splitting on commas,
newlines, or whitespace is brittle — addresses, display names, and surrounding
punctuation break naive delimiters. Prefer a capability-shaped coarse pattern
(like `EMAIL_LIKE` above) that approximates the capability's own grammars. Keep
it coarse and let Paxman decide validity; a too-strict pre-filter silently
drops mentions that would have been `INVALID`/`AMBIGUOUS` honestly.

(b) **Segmenter vs grammar boundary disagreement.** Your segmenter and Paxman's
grammars may disagree on where a mention starts or ends. Always feed the
segmenter's slice to `canonicalize()` and **trust the returned status** — an
honest `INVALID` or `AMBIGUOUS` beats pre-filtering or trimming the slice to
force a `SUCCESS`. Only `MultipleMentionsError` indicates a segmentation error; `INVALID` and `AMBIGUOUS` are valid per-mention outcomes that tell you the candidate was recognized but not validated or was ambiguous, so handle them as domain results rather than discarding them as segmentation failures.

(c) **Don't widen a segment to "give context."** Adding surrounding words to
help Paxman understand a mention backfires: extra text that contains another
mention with a *different* canonical value triggers `MultipleMentionsError`
(identical values still coalesce to `SUCCESS` per ADR-0004). Keep slices tight
to one presumed entity; Paxman is stateless per call and needs no surrounding
document context.

---

## 6. Scope statement

For single-mention input use `canonicalize()`; for scanning a document for many mentions use the batch API `paxman.scan()` which shares one `ScanContext` across capabilities. Caller-owned segmentation (split-then-canonicalize as shown above) remains correct when you need tight control, but `scan()` is now the preferred library-owned batch helper.

Extraction stays **caller-owned forever** ([M1](../reports/2026-08-17-architecture-review.md),
[ADR-0004](../adr/0004-single-value-invariant.md)). This recipe is the sanctioned
pattern for multi-entity input, and requests for built-in document extraction
are out of scope by charter, with `scan()` as the library-owned batch helper — not by limitation. By charter, Paxman will not ship a
"find all emails/phones/dates in this document" API beyond `scan()` — the split-then-canonicalize
loop above remains the intended interface for caller-controlled segmentation.

---

## References

* [ADR-0004: Single-Value Invariant](../adr/0004-single-value-invariant.md)
* [Architecture Review §8 M1](../reports/2026-08-17-architecture-review.md) — "One entity per call, forever"
* [README — Resolution Status](../../README.md#resolution-status) — `MISSING` / `INVALID` / `SUCCESS` / `AMBIGUOUS`
