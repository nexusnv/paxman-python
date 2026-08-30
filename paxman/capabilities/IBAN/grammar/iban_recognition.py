"""IBAN recognition — label kind (ADR §9.7) with glued reject.

Electronic: contiguous 15-34 alphanum (CC2 + DD2 + BBAN 11-30).
Paper: groups-of-four with single spaces: CC2 DD2 (space AAAA){2,7} (space A{1,4})?
  e.g. "DE89 3704 0044 0532 0130 00", "GB82 WEST 1234 5698 7654 32".
  Single-space discipline is per ISO 13616 paper format (groups of four);
  hyphens, tabs, double-spaces, irregular groups are NOT recognized
  (MISSING) — intentionally strict to avoid trailing-word absorption.
  Use electronic contiguous if hyphenated input must be handled (or
  normalize hyphens to spaces before calling canonicalize).

Label: optional ``IBAN`` prefix with one-or-more separators ``[\\s:-]+``
  (space, colon, hyphen) via ``LabelMatcher`` (ADR-0009 §9.7). The
  separator is never zero-width and ``glued_policy="reject"`` keeps
  "IBANDE89..." from fusing into a mention (ISBN-13 precedent; the
  zero-width ``BoundarySpec.WORD`` guard also rejects a core match
  preceded by the glued letters). Uppercase label forms are absorbed
  into the span: "IBAN DE89...", "IBAN: DE89...", "IBAN - DE89...".
  A lowercase ``iban:`` prefix is not absorbed (labels are matched
  case-sensitively) but does not block recognition — the core is
  matched after it.

Boundaries: ``BoundarySpec.WORD`` zero-width ``\\w`` checks on both
  span edges — no leading/trailing alnum within the same word.
  Electronic alternative may absorb a glued alnum tail up to 30 chars
  (e.g. "DE89370400440532013000Y" → compact Y included, rejected
  downstream as INVALID via mod97/per-country length). Paper final
  group absorbs a glued alnum tail up to 4 chars ("...00n" →
  "...00N" INVALID).

Body uses inline (?ai:...) to restrict case-folding and character classes
to ASCII (reject Kelvin sign K U+212A and Unicode digits) while
``BoundarySpec.WORD`` remains Unicode-aware (no global re.ASCII).

Single-value: True — input with 2 distinct IBAN mentions (e.g.
"DE89… / GB29…") raises MultipleMentionsError; caller must segment per
docs/recipes/segmentation.md. Scanning is deterministic and case-insensitive
for the IBAN body (grammar uppercases via notation).

Two alternatives: electronic (contiguous) and paper (groups-of-four).
Paper uses groups-of-four to prevent greedy absorption of trailing English
words (e.g. "DE89 ... 00 now" should not include "now"); the zero-width
word boundary plus the 30-char cap still blocks >34-char runs, while a
glued alnum tail <=4 chars in paper is absorbed by design and rejected
downstream via per-country length/mod97 (INVALID).
"""

from __future__ import annotations

import re as _re

from paxman.capabilities.IBAN.notation import IBANNotation
from paxman.core.grammar import BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.label import LabelMatcher
from paxman.core.grammar.scan_context import ScanContext


def _iban_emit(span: tuple[int, int], ctx: ScanContext) -> IBANNotation:
    raw = ctx.text[span[0] : span[1]]
    m = _re.search(_IBAN_CORE, raw)
    raw_compact = m.group(0) if m is not None else raw
    compact = "".join(ch for ch in raw_compact if ch.isalnum()).upper()
    country_code = compact[0:2]
    check_digits = compact[2:4]
    bban = compact[4:]
    return IBANNotation(
        country_code=country_code, check_digits=check_digits, bban=bban, compact=compact
    )


_IBAN_CORE = (
    r"(?ai:(?:[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}"
    r"|[A-Z]{2}[0-9]{2}(?: [A-Z0-9]{4}){2,7}(?: [A-Z0-9]{1,4})?))"
)

_IBAN_LABEL_MATCHER = LabelMatcher(
    labels=frozenset({"IBAN"}),
    separator=r"[\s:-]+",
    glued_policy="reject",
    pattern=_IBAN_CORE,
    flags=0,
    boundary=BoundarySpec.WORD,
    emit=_iban_emit,
)


class IBANRecognitionGrammar(PipelineGrammar[IBANNotation]):
    """IBAN recognition — CCDD+BBAN with optional IBAN label (glued reject).

    Covers electronic contiguous and paper groups-of-four (single-space)
    forms, optional IBAN label (uppercase, separators ``[\\s:-]+``, never
    zero-width, glued reject), ASCII-only body via (?ai:...), zero-width
    word boundaries (``BoundarySpec.WORD``), and deterministic greedy tail
    handling (glued alnum <=4 chars in paper, <=30 in electronic → INVALID
    downstream). Single-value: caller must segment multi-IBAN input.
    """

    name = "iban_recognition"
    semantics = "iban_recognition"
    single_value = True
    pre = StandardPre[IBANNotation](empty_guard=True)
    matchers = (_IBAN_LABEL_MATCHER,)
