"""BoundarySpec data — declarative, checked at hit positions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

_W_CHARS: frozenset[str] = frozenset(
    chr(c) for c in range(0x10000) if chr(c) == "_" or chr(c).isalnum()
)
_D_CHARS: frozenset[str] = frozenset("0123456789")
_S_CHARS: frozenset[str] = frozenset(chr(c) for c in range(0x10000) if chr(c).isspace())


def _chars_from_bracket(content: str) -> frozenset[str]:
    res: set[str] = set()
    i = 0
    while i < len(content):
        ch = content[i]
        if ch == "\\" and i + 1 < len(content):
            nxt = content[i + 1]
            if nxt == "w":
                res.update(_W_CHARS)
                i += 2
                continue
            if nxt == "d":
                res.update(_D_CHARS)
                i += 2
                continue
            if nxt == "s":
                res.update(_S_CHARS)
                i += 2
                continue
            # escaped literal (\-, \., \+, \[, etc.)
            res.add(nxt)
            i += 2
            continue
        # range a-b
        if i + 2 < len(content) and content[i + 1] == "-":
            start_c = ch
            end_c = content[i + 2]
            # Avoid misinterpreting literal '-' at boundaries; ranges are valid
            # when start <= end and neither is an escape start
            if start_c != "\\" and end_c != "\\":
                for code in range(ord(start_c), ord(end_c) + 1):
                    res.add(chr(code))
                i += 3
                continue
        res.add(ch)
        i += 1
    return frozenset(res)


def _pattern_to_chars(pat: str) -> frozenset[str] | None:
    if pat == r"\w":
        return _W_CHARS
    if pat == r"\d":
        return _D_CHARS
    if pat == r"\s":
        return _S_CHARS
    if len(pat) >= 2 and pat[0] == "[" and pat[-1] == "]":
        # reject if contains quantifiers that would make it multi-char
        interior = pat[1:-1]
        # pure char-class must not contain unescaped regex meta beyond the bracket
        # presets have no quantifiers; treat any interior containing
        # '*+?{}|' as not single-char
        if any(m in interior for m in "*+?{}|"):
            return None
        return _chars_from_bracket(interior)
    return None


def _estimate_width(pat: str) -> int:
    i = 0
    cnt = 0
    while i < len(pat):
        if pat[i] == "\\" and i + 1 < len(pat):
            cnt += 1
            i += 2
            continue
        if pat[i] == "[":
            j = pat.find("]", i)
            if j == -1:
                cnt += 1
                i += 1
            else:
                cnt += 1
                i = j + 1
            continue
        cnt += 1
        i += 1
    return max(1, cnt)


@dataclass(frozen=True, slots=True)
class BoundarySpec:
    """Declarative boundary constraint evaluated at hit positions."""

    left: tuple[str, ...] | None
    right: tuple[str, ...] | None
    mode: str = "zero_width"
    left_chars: frozenset[str] | None = field(default=None, init=False, repr=False)
    right_chars: frozenset[str] | None = field(default=None, init=False, repr=False)
    left_multi: tuple[tuple[int, re.Pattern[str]], ...] = field(
        default=(), init=False, repr=False
    )
    right_multi: tuple[tuple[int, re.Pattern[str]], ...] = field(
        default=(), init=False, repr=False
    )

    def __post_init__(self) -> None:
        lc: set[str] = set()
        lm: list[tuple[int, re.Pattern[str]]] = []
        rc: set[str] = set()
        rm: list[tuple[int, re.Pattern[str]]] = []
        if self.left is not None:
            for pat in self.left:
                chars = _pattern_to_chars(pat)
                if chars is not None:
                    lc.update(chars)
                else:
                    w = _estimate_width(pat)
                    lm.append((w, re.compile(pat + r"\Z")))
        if self.right is not None:
            for pat in self.right:
                chars = _pattern_to_chars(pat)
                if chars is not None:
                    rc.update(chars)
                else:
                    w = _estimate_width(pat)
                    rm.append((w, re.compile(r"\A" + pat)))
        object.__setattr__(self, "left_chars", frozenset(lc) if lc else None)
        object.__setattr__(self, "right_chars", frozenset(rc) if rc else None)
        object.__setattr__(self, "left_multi", tuple(lm))
        object.__setattr__(self, "right_multi", tuple(rm))

    @property
    def is_consuming(self) -> bool:
        return self.mode == "consuming"

    # Preset table — assigned after class body to avoid dataclass field capture.
    WORD_SIGN: ClassVar[BoundarySpec]
    DEGREE_WORD_SIGN: ClassVar[BoundarySpec]
    DIGIT: ClassVar[BoundarySpec]
    WORD: ClassVar[BoundarySpec]
    E164_LEFT: ClassVar[BoundarySpec]
    E164_00_LEFT: ClassVar[BoundarySpec]
    SCHEME_CHAR_LEFT: ClassVar[BoundarySpec]
    PHONE_NATIONAL: ClassVar[BoundarySpec]
    ISBN10_LEAD: ClassVar[BoundarySpec]
    ISBN_TRAIL_LEFT: ClassVar[BoundarySpec]
    IPV6_TOKEN: ClassVar[BoundarySpec]


def check_boundary(subject: str, start: int, end: int, spec: BoundarySpec) -> bool:
    if spec.left is not None and start > 0:
        if spec.left_chars is not None and subject[start - 1] in spec.left_chars:
            return False
        for w, pat in spec.left_multi:
            lo = start - w
            if lo < 0:
                lo = 0
            if pat.search(subject[lo:start]) is not None:
                return False
    if spec.right is not None and end < len(subject):
        if spec.right_chars is not None and subject[end] in spec.right_chars:
            return False
        for w, pat in spec.right_multi:
            hi = end + w
            if hi > len(subject):
                hi = len(subject)
            if pat.search(subject[end:hi]) is not None:
                return False
    return True


def check_boundary_compiled(
    subject: str, start: int, end: int, spec: BoundarySpec
) -> bool:
    return check_boundary(subject, start, end, spec)


BoundarySpec.WORD_SIGN = BoundarySpec(
    left=("[\\w\\-+\\u2212]",), right=("[\\w\\-+\\u2212]",), mode="zero_width"
)
BoundarySpec.DEGREE_WORD_SIGN = BoundarySpec(
    left=("[°\\w\\-+\\u2212/·⋅]",), right=("[\\w\\-+\\u2212/·⋅]",), mode="zero_width"
)
BoundarySpec.DIGIT = BoundarySpec(left=("\\d",), right=("\\d",), mode="zero_width")
BoundarySpec.WORD = BoundarySpec(left=("\\w",), right=("\\w",), mode="zero_width")
BoundarySpec.E164_LEFT = BoundarySpec(left=("[\\w:.]",), right=None, mode="zero_width")
BoundarySpec.E164_00_LEFT = BoundarySpec(
    left=("[\\w:.+]",), right=None, mode="zero_width"
)
BoundarySpec.SCHEME_CHAR_LEFT = BoundarySpec(
    left=("[A-Za-z0-9+.\\-]",), right=None, mode="zero_width"
)
BoundarySpec.PHONE_NATIONAL = BoundarySpec(
    left=("[\\d+]",), right=("\\d",), mode="zero_width"
)
BoundarySpec.ISBN10_LEAD = BoundarySpec(
    left=("\\d", "\\d[ -]"), right=None, mode="zero_width"
)
BoundarySpec.ISBN_TRAIL_LEFT = BoundarySpec(
    left=("[\\s:-]",), right=None, mode="zero_width"
)
BoundarySpec.IPV6_TOKEN = BoundarySpec(
    left=("[\\s,;([ ]",), right=("[\\s,;().\\]]",), mode="consuming"
)
