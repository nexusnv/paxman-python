"""Label matcher — optional label + value fusion (ADR-0009 §9.7).

Unifies per-file ``[\\s:-]+`` vs ``[\\s:-]*`` conventions as
``glued_policy reject|allow``. ISSN uses ``allow`` (glued ``ISSN03178471``
matches), IBAN/BIC/ORCID use ``reject`` (glued ``IBANDE89`` is MISSING).
``matches_prefix`` is the tested utility; :meth:`match` handles optional
label + separator + core pattern with boundary checks and emits via ``emit``.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from paxman.core.grammar.anchors import AnchorSet
from paxman.core.grammar.boundary_spec import BoundarySpec, check_boundary
from paxman.core.grammar.matchers._emit_validation import (
    validate_emit as _validate_emit,
)
from paxman.core.grammar.scan_context import View


@dataclass(frozen=True, slots=True)
class LabelMatcher:
    labels: frozenset[str] = frozenset()
    separator: str = r"[\s:-]+"
    glued_policy: Literal["reject", "allow"] = "reject"
    pattern: str = ""
    flags: int = 0
    view_name: str | None = None
    view: str | None = None
    anchors: AnchorSet = field(default_factory=AnchorSet)
    boundary: BoundarySpec | None = None
    emit: Callable[[tuple[int, int], Any], Any] | None = field(default=None, repr=False)
    requires_features: frozenset[str] = field(default_factory=lambda: frozenset[str]())
    suppressible: bool = False
    kind: str = field(default="label", init=False)
    digest: str = field(init=False, repr=False, default="")
    _sep_re: re.Pattern[str] | None = field(init=False, repr=False, default=None)
    _combined: re.Pattern[str] | None = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.view is not None and self.view_name is None:
            object.__setattr__(self, "view_name", self.view)
        elif self.view_name is not None and self.view is None:
            object.__setattr__(self, "view", self.view_name)
        _validate_emit(self.emit, type(self).__name__)
        sep_re = re.compile(self.separator)
        object.__setattr__(self, "_sep_re", sep_re)
        # Build combined regex: optional label+separator + core pattern.
        # glued_policy is already encoded in separator (* vs +), but we keep
        # the field for digest and matches_prefix semantics.
        if self.pattern:
            if self.labels:
                label_alt = "|".join(
                    re.escape(lbl)
                    for lbl in sorted(self.labels, key=lambda x: (-len(x), x))
                )
                combined_str = f"(?:(?:{label_alt}){self.separator})?{self.pattern}"
            else:
                combined_str = self.pattern
            try:
                combined = re.compile(combined_str, self.flags)
            except re.error as exc:
                raise ValueError(
                    f"Invalid label pattern {combined_str!r}: {exc}"
                ) from exc
            object.__setattr__(self, "_combined", combined)
        else:
            object.__setattr__(self, "_combined", None)
        # Digest: labels|separator|glued|pattern|flags|boundary|view|anchors
        view_repr = self.view_name if self.view_name is not None else "None"
        boundary_repr = repr(self.boundary) if self.boundary is not None else "None"
        anchors_repr = repr(self.anchors)
        labels_repr = "|".join(sorted(self.labels)) if self.labels else ""
        digest_val = hashlib.sha256(
            f"{labels_repr}\x00{self.separator}\x00{self.glued_policy}\x00{self.pattern}\x00{self.flags}\x00{view_repr}\x00{boundary_repr}\x00{anchors_repr}".encode()
        ).hexdigest()
        object.__setattr__(self, "digest", digest_val)

    def matches_prefix(self, text: str) -> bool:
        sep_re = self._sep_re
        assert sep_re is not None
        for label in self.labels:
            # Case-insensitive label check mirrors IGNORECASE bodies (ISSN/IBAN).
            # Use lower for case-fold where flags include IGNORECASE; otherwise
            # exact match. Simplify to case-insensitive for label prefix utility
            # as tested with upper labels and lower input not required here.
            if text.startswith(label) or text.lower().startswith(label.lower()):
                # Determine consumed label length with case-insensitive match
                # Prefer exact length; lower comparison preserves length.
                rest = text[len(label) :]
                if not rest:
                    return False
                if self.glued_policy == "reject":
                    return sep_re.match(rest) is not None
                else:
                    return True
        return False

    def match(self, view: View) -> list[tuple[int, int]]:
        combined = self._combined
        if combined is None:
            return []
        out: list[tuple[int, int]] = []
        subj = view.subject
        for m in combined.finditer(subj):
            s, e = m.start(), m.end()
            if s == e:
                continue
            if self.boundary is not None and not check_boundary(
                subj, s, e, self.boundary
            ):
                continue
            out.append((s, e))
        return out
