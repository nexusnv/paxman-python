"""PipelineGrammar base — fixed-order pipeline with optional stages."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, TypeVar, cast

from paxman.core.domain import Grammar, RecognitionMatch
from paxman.core.grammar.stages import PipelineState, Stage

NotationT = TypeVar("NotationT")


class PipelineGrammar(Grammar[NotationT]):
    """Grammar that declares optional stages; recognize() walks them in fixed order."""

    # Placeholder semantics for the abstract base; concrete grammars override it
    # (Grammar.__init_subclass__ requires a non-empty semantics at class-def time).
    semantics: ClassVar[str] = "pipeline_grammar"

    # Stages — each is Optional[Stage]; None means "skip".
    pre: Stage[NotationT] | None = None
    regex: Stage[NotationT] | None = None
    lexicon: Stage[NotationT] | None = None
    composer: Stage[NotationT] | None = None
    post: Stage[NotationT] | None = None

    # Declarative matcher set — when set, recognize() delegates to the
    # engine-owned loop (single recognition path). Legacy grammars leave
    # this None and keep the stage loop.
    matchers: ClassVar[tuple[Any, ...] | None] = None

    def recognize(self, text: str) -> list[RecognitionMatch[NotationT]]:
        _matchers = getattr(self, "matchers", None)
        if _matchers is not None:
            from paxman.core.grammar.engine_loop import run_matchers

            return run_matchers(text, cast(Sequence[Any], [self]))
        state: PipelineState[NotationT] = PipelineState(
            text=text, matches=[], scratch={}
        )
        # Pre short-circuit: if StandardPre emptied matches on whitespace-only
        # input, skip remaining stages — they would find nothing anyway.
        if self.pre is not None:
            state = self.pre.run(state)
            if not state.text.strip() and not state.matches:
                return list(state.matches)
        for stage in (
            self.regex,
            self.lexicon,
            self.composer,
            self.post,
        ):
            if stage is not None:
                state = stage.run(state)
        return list(state.matches)
