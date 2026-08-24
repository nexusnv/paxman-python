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
