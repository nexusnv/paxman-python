"""BoundarySpec data — declarative, checked at hit positions."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class BoundarySpec:
    """Declarative boundary constraint evaluated at hit positions."""

    left: tuple[str, ...] | None
    right: tuple[str, ...] | None
    mode: str = "zero_width"

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
    """Single source for boundary checks (consolidates triplicated logic)."""
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
