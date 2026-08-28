"""Parity between compiled and regex boundary checks (ADR §10)."""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from paxman.core.grammar.boundary_spec import (
    BoundarySpec,
    check_boundary,
    check_boundary_compiled,
)

pytestmark = [pytest.mark.property]


def _oracle(subject: str, start: int, end: int, spec: BoundarySpec) -> bool:
    if spec.left is not None and start > 0:
        prefix = subject[:start]
        for pat in spec.left:
            if re.search(pat + r"\Z", prefix) is not None:
                return False
    if spec.right is not None and end < len(subject):
        suffix = subject[end:]
        for pat in spec.right:
            if re.search(r"\A" + pat, suffix) is not None:
                return False
    return True


# All §10 presets
PRESETS: dict[str, BoundarySpec] = {
    "WORD_SIGN": BoundarySpec.WORD_SIGN,
    "DEGREE_WORD_SIGN": BoundarySpec.DEGREE_WORD_SIGN,
    "DIGIT": BoundarySpec.DIGIT,
    "WORD": BoundarySpec.WORD,
    "E164_LEFT": BoundarySpec.E164_LEFT,
    "E164_00_LEFT": BoundarySpec.E164_00_LEFT,
    "SCHEME_CHAR_LEFT": BoundarySpec.SCHEME_CHAR_LEFT,
    "PHONE_NATIONAL": BoundarySpec.PHONE_NATIONAL,
    "ISBN10_LEAD": BoundarySpec.ISBN10_LEAD,
    "ISBN_TRAIL_LEFT": BoundarySpec.ISBN_TRAIL_LEFT,
    "IPV6_TOKEN": BoundarySpec.IPV6_TOKEN,
}

# Alphabet mixing preset class chars incl ° µ Ω · ⋅ − +
_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    " \t\n\r"
    "°µΩ·⋅−+"
    "/:.+,;()[]-"
    " \u2212"
)


@settings(max_examples=80, deadline=None)
@given(st.text(alphabet=st.sampled_from(list(_ALPHABET)), min_size=0, max_size=24))
def test_boundary_compiled_parity(text: str) -> None:
    for _name, spec in PRESETS.items():
        n = len(text)
        for s in range(n + 1):
            for e in range(s, n + 1):
                a = check_boundary(text, s, e, spec)
                b = check_boundary_compiled(text, s, e, spec)
                c = _oracle(text, s, e, spec)
                assert a == b == c, (
                    f"mismatch preset={_name} text={text!r} s={s} e={e} "
                    f"check_boundary={a} compiled={b} oracle={c} spec={spec}"
                )


def test_boundary_compiled_isbn10_lead_window() -> None:
    spec = BoundarySpec.ISBN10_LEAD
    # Positive cases for two-char window r"\d[ -]"
    assert (
        check_boundary("1 ", 2, 2, spec) is False
    )  # prefix ends with "1 " matches \d[ -]
    assert check_boundary_compiled("1 ", 2, 2, spec) is False
    # Single digit boundary
    assert check_boundary("1", 1, 1, spec) is False
    assert check_boundary_compiled("1", 1, 1, spec) is False
    # No violation
    assert check_boundary("a ", 2, 2, spec) is True
    assert check_boundary_compiled("a ", 2, 2, spec) is True
