"""Engine-owned match loop L0+L1+L2."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.normalizers import CaseFold, CountryNameFold
from paxman.core.grammar.scan_context import ScanContext

__all__ = ["_run_matchers"]


def _run_matchers(text: str, compiled: Sequence[Any]) -> list[RecognitionMatch[Any]]:
    context = ScanContext.of(text)
    out: list[RecognitionMatch[Any]] = []
    for grammar in compiled:
        for matcher in getattr(grammar, "matchers", ()):
            if not matcher.anchors.passes(text, context):
                continue
            if matcher.view is None:
                view = context.view("__orig__", lambda t: (t, None))
            else:
                if matcher.view == "casefolded":
                    view = context.view("casefolded", CaseFold().normalize)
                elif matcher.view == "normalized":
                    view = context.view("normalized", CountryNameFold().normalize)
                else:
                    view = context.view(matcher.view, lambda t: (t, None))
            for span in matcher.match(view):  # type: ignore[attr-defined]
                o_s, o_e = view.original_span(*span)
                # Emit receives the original span so notation values that
                # slice ctx.text are correct even for length-changing views
                # (e.g. CountryNameFold removes apostrophes).
                try:
                    notation = matcher.emit((o_s, o_e), context)  # type: ignore[arg-type]
                except TypeError:
                    # Fallback for emit signatures that expect view span
                    notation = matcher.emit(span, context)  # type: ignore[arg-type]
                out.append(
                    RecognitionMatch(
                        notation=notation,
                        start=o_s,
                        end=o_e,
                        raw_text=text[o_s:o_e],
                    )
                )
    return out
