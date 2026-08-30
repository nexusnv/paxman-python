"""BoundarySpec data — declarative, checked at hit positions.

Single-char entries lower to frozenset O(1) membership,
multi-char to bounded regex."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import ClassVar

_W_CHARS: frozenset[str] = frozenset(
    chr(c) for c in range(0x10000) if chr(c) == "_" or chr(c).isalnum()
)
_D_CHARS: frozenset[str] = frozenset(
    chr(c) for c in range(0x10000) if unicodedata.category(chr(c)) == "Nd"
)
_S_CHARS: frozenset[str] = frozenset(chr(c) for c in range(0x10000) if chr(c).isspace())

# Compiled class escapes: consulted by check_boundary for non-BMP neighbors
# (ord(ch) > 0xFFFF) where the BMP-only frozenset scans above are blind (#62).
_W_RE: re.Pattern[str] = re.compile(r"\w")
_D_RE: re.Pattern[str] = re.compile(r"\d")
_S_RE: re.Pattern[str] = re.compile(r"\s")


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
    """Return the BMP char set for a fragment, or None (multi/regex path).

    Class escapes (``\\w``, ``\\d``, ``\\s``) lower to their BMP scans,
    positive bracket classes to their enumerated chars; negated bracket
    classes (``[^...]``) return ``None`` so the compiled regex path
    preserves their negated semantics (#67).
    """
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
        # Negated class: a positive char set would invert the guard
        # semantics (#67). Fall back to the compiled regex path, where
        # '[^...]' keeps its negated meaning against the 1-char window.
        if interior.startswith("^"):
            return None
        return _chars_from_bracket(interior)
    return None


# Keep in sync with the class-escape branches in _pattern_to_chars (#62).
_FALLBACK_RES: dict[str, re.Pattern[str]] = {
    r"\w": _W_RE,
    r"\d": _D_RE,
    r"\s": _S_RE,
}

_BRACKET_FALLBACK_CACHE: dict[str, re.Pattern[str]] = {}


def _pattern_lowering(
    pat: str,
) -> tuple[frozenset[str] | None, re.Pattern[str] | None]:
    """Lower a single-char boundary fragment to a BMP set + non-BMP fallback.

    Returns ``(chars, fallback)``. ``chars`` is the BMP-exact frozenset from
    :func:`_pattern_to_chars`; ``fallback`` is the compiled class escape
    (``\\w``, ``\\d``, ``\\s``) when the BMP scan is merely an approximation
    of it, or for positive bracket classes containing such escapes (``[\\w]``,
    ``[\\w:.]``, ``[\\d]``) the compiled bracket itself cached in
    ``_BRACKET_FALLBACK_CACHE``. The fallback is consulted by
    :func:`check_boundary` for non-BMP neighbors (``ord(ch) > 0xFFFF``),
    keeping neighbor decisions exact against ``re`` for the whole codepoint
    space without an import-time scan of all 0x110000 codepoints.
    """
    chars = _pattern_to_chars(pat)
    if chars is None:
        return None, None
    fallback = _FALLBACK_RES.get(pat)
    if fallback is not None:
        return chars, fallback
    # Positive bracket classes containing class escapes (\\w, \\d, \\s)
    # need a non-BMP fallback too: the BMP frozenset from
    # _chars_from_bracket is blind to supplementary-plane chars, so for
    # non-BMP neighbors consult the compiled bracket itself (exact vs re).
    if len(pat) >= 2 and pat[0] == "[" and pat[-1] == "]":
        interior = pat[1:-1]
        if ("\\w" in interior) or ("\\d" in interior) or ("\\s" in interior):
            cached = _BRACKET_FALLBACK_CACHE.get(pat)
            if cached is None:
                try:
                    cached = re.compile(pat)
                except re.error:
                    return chars, None
                _BRACKET_FALLBACK_CACHE[pat] = cached
            return chars, cached
    return chars, None


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
    """Declarative boundary constraint evaluated at hit positions.

    Each ``left`` / ``right`` entry may be a single-character or
    multi-character regex fragment that must NOT match the adjacent character
    for the hit to be accepted (mirroring ``(?<!...)`` / ``(?!...)``).
    Single-char fragments lower to ``frozenset`` O(1) membership
    (``left_chars`` / ``right_chars``); multi-char fragments compile to
    bounded regexes (``left_multi`` / ``right_multi``). Class escapes
    (``\\w``, ``\\d``, ``\\s``) additionally carry a compiled non-BMP
    fallback (``left_char_fallback`` / ``right_char_fallback``) consulted
    by :func:`check_boundary` for supplementary-plane neighbors, keeping
    decisions exact vs ``re`` across the full codepoint space (#62).
    ``mode``
    ``"consuming"`` is reserved for token-level boundaries (e.g. ``IPV6_TOKEN``)
    where the boundary characters are not part of the token.

    Attributes:
        left: Regex fragments forbidden immediately to the left of the hit.
        right: Regex fragments forbidden immediately to the right of the hit.
        mode: ``"zero_width"`` (default) or ``"consuming"``.
        left_chars: Cached frozenset of forbidden left chars (``None`` if none).
        right_chars: Cached frozenset of forbidden right chars (``None`` if none).
        left_multi: Tuple of ``(width, pattern)`` for multi-char left guards.
        right_multi: Tuple of ``(width, pattern)`` for multi-char right guards.
        left_char_fallback: Compiled class escapes for non-BMP left neighbors.
        right_char_fallback: Compiled class escapes for non-BMP right neighbors.
    """

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
    left_char_fallback: tuple[re.Pattern[str], ...] = field(
        default=(), init=False, repr=False
    )
    right_char_fallback: tuple[re.Pattern[str], ...] = field(
        default=(), init=False, repr=False
    )

    def __post_init__(self) -> None:
        lc: set[str] = set()
        lm: list[tuple[int, re.Pattern[str]]] = []
        rc: set[str] = set()
        rm: list[tuple[int, re.Pattern[str]]] = []
        lfb: list[re.Pattern[str]] = []
        rfb: list[re.Pattern[str]] = []
        if self.left is not None:
            for pat in self.left:
                chars, fallback = _pattern_lowering(pat)
                if chars is not None:
                    lc.update(chars)
                    if fallback is not None:
                        lfb.append(fallback)
                else:
                    w = _estimate_width(pat)
                    lm.append((w, re.compile(pat + r"\Z")))
        if self.right is not None:
            for pat in self.right:
                chars, fallback = _pattern_lowering(pat)
                if chars is not None:
                    rc.update(chars)
                    if fallback is not None:
                        rfb.append(fallback)
                else:
                    w = _estimate_width(pat)
                    rm.append((w, re.compile(r"\A" + pat)))
        object.__setattr__(self, "left_chars", frozenset(lc) if lc else None)
        object.__setattr__(self, "right_chars", frozenset(rc) if rc else None)
        object.__setattr__(self, "left_multi", tuple(lm))
        object.__setattr__(self, "right_multi", tuple(rm))
        object.__setattr__(self, "left_char_fallback", tuple(lfb))
        object.__setattr__(self, "right_char_fallback", tuple(rfb))

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
    """Check whether the hit at ``[start:end)`` respects ``spec``.

    Each ``left`` entry must NOT match the suffix ending at ``start``;
    each ``right`` entry must NOT match the prefix starting at ``end``.
    Single-char guards use ``frozenset`` O(1) lookup; multi-char guards use
    bounded regex search (``\\Z`` / ``\\A`` anchored). Class escapes carry
    compiled fallbacks consulted for non-BMP neighbors, where the BMP-only
    char sets are blind, keeping decisions exact vs ``re`` (#62). This is
    the single-source boundary check used by both ``ScanContext.check_hit``
    and the kernel ``engine_loop``.

    Args:
        subject: Text (or normalized view subject) containing the hit.
        start: Start offset of the hit (half-open).
        end: End offset of the hit (half-open).
        spec: Boundary specification to check.

    Returns:
        ``True`` if no guard fires (hit is valid), ``False`` otherwise.
    """
    if spec.left is not None and start > 0:
        ch = subject[start - 1]
        if spec.left_chars is not None and ch in spec.left_chars:
            return False
        # Non-BMP fallback: the char sets are BMP scans; for supplementary-
        # plane neighbors decide via the compiled escape (exact vs re) (#62).
        if (
            spec.left_char_fallback
            and ord(ch) > 0xFFFF
            and any(pat.match(ch) for pat in spec.left_char_fallback)
        ):
            return False
        for w, pat in spec.left_multi:
            lo = start - w
            if lo < 0:
                lo = 0
            if pat.search(subject[lo:start]) is not None:
                return False
    if spec.right is not None and end < len(subject):
        ch = subject[end]
        if spec.right_chars is not None and ch in spec.right_chars:
            return False
        if (
            spec.right_char_fallback
            and ord(ch) > 0xFFFF
            and any(pat.match(ch) for pat in spec.right_char_fallback)
        ):
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
    """Compiled alias for :func:`check_boundary` (kernel hot-path hook).

    Exists as a named indirection for the kernel engine loop's compiled
    boundary path; semantically identical to :func:`check_boundary`.

    Args:
        subject: Text (or normalized view subject) containing the hit.
        start: Start offset of the hit.
        end: End offset of the hit.
        spec: Boundary specification to check.

    Returns:
        ``True`` if the hit respects the boundary, ``False`` otherwise.
    """
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
