"""Helper for kernel-vs-legacy byte-identical gate."""

from __future__ import annotations

from typing import Any

from paxman.core.domain import Grammar


def assert_kernel_parity(old: Grammar[Any], new: Grammar[Any], text: str) -> None:
    old_matches = old.recognize(text)
    new_matches = new.recognize(text)
    assert len(old_matches) == len(new_matches), (
        f"len mismatch for {text!r}: {old_matches} vs {new_matches}"
    )
    for o, n in zip(old_matches, new_matches, strict=True):
        assert o.start == n.start, f"start mismatch for {text!r}: {o} vs {n}"
        assert o.end == n.end, f"end mismatch for {text!r}: {o} vs {n}"
        assert o.raw_text == n.raw_text, (
            f"raw_text {o.raw_text!r} vs {n.raw_text!r} for {text!r}"
        )
        assert o.notation == n.notation, (
            f"notation {o.notation!r} vs {n.notation!r} for {text!r}"
        )


def assert_delegation_parity(grammar: Grammar[Any], text: str) -> None:
    """Gating assertion: PipelineGrammar delegation to engine loop.

    For any grammar that declares ``matchers``, ``g.recognize(text)``
    must be identical to ``run_matchers(text, [g])``. If delegation is
    reverted to a hand-rolled body, a token mutation will diverge and
    this assertion fails. This locks the single-path invariant (A7/R10).
    """
    from paxman.core.grammar.engine_loop import run_matchers  # noqa: PLC0415

    via_recognize = grammar.recognize(text)
    via_engine = run_matchers(text, [grammar])
    assert via_recognize == via_engine, (
        f"delegation mismatch for {type(grammar).__name__!r} text={text!r}: "
        f"recognize={via_recognize!r} vs run_matchers={via_engine!r}"
    )
