"""Normalizers — first-class, composable, provenance-aware.

Two-array (starts,ends) offset mapping; CountryNameFold is single-pass NFD
with cache."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol, runtime_checkable

from paxman.core.domain import Provenance


@runtime_checkable
class Normalizer(Protocol):
    """A single recognition-view rewrite step over scanner text.

    Normalizers must not expand: each input character maps to at most one
    subject character (stripping or 1:1 rewriting only) — see
    ``NormalizerSequence`` (#63).
    """

    @property
    def name(self) -> str: ...

    @property
    def provenance(self) -> Provenance | None: ...

    # Chars the normalizer strips that matchers may re-absorb into spans.
    @property
    def stripped_chars(self) -> str | None: ...

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]: ...


@dataclass(frozen=True, slots=True)
class NormalizerSequence:
    """Compose normalizer steps, threading offset maps through composition.

    Normalizers must not expand: each input character maps to at most one
    subject character (stripping or 1:1 rewriting only). Sequence composition
    asserts unit-width offsets (``ends[i] == starts[i] + 1``) that are
    strictly increasing (no cur char reused by two nxt chars) and fails fast
    otherwise — expansion would silently mis-map end offsets (#63).
    """

    steps: tuple[Normalizer, ...]
    # Sequence composition does not aggregate stripped chars (no shipped
    # sequence needs it).
    stripped_chars: str | None = None

    @property
    def name(self) -> str:
        return "+".join(s.name for s in self.steps)

    @property
    def provenance(self) -> Provenance | None:
        for s in self.steps:
            if s.provenance is not None:
                return s.provenance
        return None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        cur = text
        cur_starts: tuple[int, ...] | None = None
        cur_ends: tuple[int, ...] | None = None
        for step in self.steps:
            nxt, off_starts, off_ends = step.normalize(cur)
            if off_starts is None and off_ends is None:
                if len(nxt) != len(cur):
                    raise ValueError(
                        f"Normalizer {step.name} returned no offset map but "
                        f"changed length {len(cur)} -> {len(nxt)}"
                    )
                if (
                    cur_starts is not None
                    and cur_ends is not None
                    and (len(cur_starts) != len(cur) or len(cur_ends) != len(cur))
                ):
                    raise ValueError(
                        "NormalizerSequence invariant broken: prior offset "
                        f"length {len(cur_starts)} != subject length {len(cur)}"
                    )
                if (
                    cur_starts is not None
                    and cur_ends is not None
                    and len(nxt) != len(cur_starts)
                ):
                    raise ValueError(
                        f"Normalizer {step.name} changed length without "
                        f"offset map in sequence "
                        f"({len(cur_starts)} -> {len(nxt)})"
                    )
                cur = nxt
                if (
                    cur_starts is not None
                    and cur_ends is not None
                    and (len(cur_starts) != len(cur) or len(cur_ends) != len(cur))
                ):
                    raise ValueError(
                        "NormalizerSequence invariant broken: offset length "
                        f"{len(cur_starts)} != subject length "
                        f"{len(cur)} after step {step.name}"
                    )
                continue
            if off_starts is None or off_ends is None:
                raise ValueError(
                    f"Normalizer {step.name} returned mismatched offset maps "
                    "(one None, one not)"
                )
            if len(off_starts) != len(nxt) or len(off_ends) != len(nxt):
                raise ValueError(
                    f"Normalizer {step.name} offset length "
                    f"({len(off_starts)}, {len(off_ends)}) "
                    f"!= subject length {len(nxt)}"
                )
            # Validate one-pair-per-character and no-expansion invariants
            # for this step's map
            for s, e in zip(off_starts, off_ends, strict=True):
                if not (0 <= s < e <= len(cur)):
                    raise ValueError(
                        f"Normalizer {step.name} offset [{s},{e}) out of "
                        f"bounds for cur length {len(cur)}"
                    )
                if e != s + 1:
                    raise ValueError(
                        f"Normalizer {step.name} offsets must be unit-width "
                        f"in sequences (got [{s},{e}))"
                    )
            for a, b in zip(off_starts, off_starts[1:], strict=False):
                if not (a < b):
                    raise ValueError(
                        f"Normalizer {step.name} expansion is not supported "
                        f"in sequences (starts not strictly increasing: "
                        f"{a} >= {b})"
                    )
            if cur_starts is None and cur_ends is None:
                cur_starts = off_starts
                cur_ends = off_ends
            else:
                if cur_starts is None or cur_ends is None:
                    raise ValueError(
                        "NormalizerSequence inconsistent state: partial offset map"
                    )
                # Empty subjects (e.g. "" -> "", (), ()) compose trivially to empty;
                # allow them instead of failing the non-empty invariant.
                if len(cur) == 0 and len(nxt) == 0:
                    cur_starts = ()
                    cur_ends = ()
                    cur = nxt
                    continue
                if len(cur_starts) != len(cur) or len(cur_ends) != len(cur):
                    raise ValueError(
                        "NormalizerSequence invariant broken: prior offset length "
                        f"{len(cur_starts)} != subject length {len(cur)}"
                    )
                for o in off_starts:
                    if not (0 <= o < len(cur_starts)):
                        raise ValueError(
                            f"Normalizer {step.name} offset index {o} out of "
                            f"range for cur offsets length {len(cur_starts)}"
                        )
                for o in off_ends:
                    if not (0 <= o < len(cur_ends)):
                        raise ValueError(
                            f"Normalizer {step.name} offset index {o} out of "
                            f"range for cur offsets length {len(cur_ends)}"
                        )
                if len(cur_ends) == 0:
                    raise ValueError(
                        "NormalizerSequence cannot compose onto empty offset map"
                    )
                composed_starts = tuple(cur_starts[o] for o in off_starts)
                composed_ends = tuple(
                    cur_ends[o - 1] if o > 0 else cur_ends[0] for o in off_ends
                )
                cur_starts = composed_starts
                cur_ends = composed_ends
            cur = nxt
            if len(cur_starts) != len(cur) or len(cur_ends) != len(cur):
                raise ValueError(
                    "NormalizerSequence invariant broken: offset length "
                    f"{len(cur_starts)} != subject length {len(cur)} "
                    f"after step {step.name}"
                )
        if (
            cur_starts is not None
            and cur_ends is not None
            and (len(cur_starts) != len(cur) or len(cur_ends) != len(cur))
        ):
            raise ValueError(
                "NormalizerSequence invariant broken: final offset length "
                f"{len(cur_starts)} != subject length {len(cur)}"
            )
        return cur, cur_starts, cur_ends


@dataclass(frozen=True, slots=True)
class CaseFold:
    name: str = "casefolded"
    provenance: Provenance | None = None
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        return text.lower(), None, None


@dataclass(frozen=True, slots=True)
class SeparatorFold:
    name: str = "normalized"
    provenance: Provenance | None = Provenance(
        authority="IETF",
        specification_name="BCP 47 §2.1",
        kind="specification",
        reference_url="https://www.rfc-editor.org/info/bcp47",
        version="47",
        lifecycle="active",
        publication_year=2009,
    )
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        return text.replace("_", "-"), None, None


@dataclass(frozen=True, slots=True)
class AccentStrip:
    name: str = "normalized"
    provenance: Provenance | None = Provenance(
        authority="CLDR",
        specification_name="CLDR/ISO 3166",
        kind="specification",
        reference_url="https://cldr.unicode.org/",
        version="47",
        lifecycle="active",
        publication_year=2024,
    )
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        nfd = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        return stripped.lower(), None, None


@lru_cache(maxsize=8192)
def _nfd_char(ch: str) -> str:
    """NFD-decompose a single character (bounded memo, deterministic).

    Unicode decomposition mappings are per-codepoint, so per-char NFD
    concatenation equals whole-text NFD; the cache is a pure memo of a
    deterministic function — no input-dependent global state (#64, the
    former ``_NFD_CACHE`` dict grew without bound).
    """
    return unicodedata.normalize("NFD", ch)


@dataclass(frozen=True, slots=True)
class CountryNameFold:
    """Country name view: accent-strip + separator fold + punctuation strip.

    Mirrors ``paxman.capabilities.Country.notation.normalize_name`` but
    lowercases and preserves offset mapping for kernel views. Used for the
    ``normalized`` view when the Country lexicon trie scans in-text.
    """

    name: str = "normalized"
    provenance: Provenance | None = Provenance(
        authority="CLDR",
        specification_name="CLDR/ISO 3166",
        kind="specification",
        reference_url="https://cldr.unicode.org/",
        version="47",
        lifecycle="active",
        publication_year=2024,
    )
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        if not text:
            return "", (), ()
        nfd = unicodedata.normalize("NFD", text)
        # Map each NFD char back to its original index via cached per-char
        # decomposition lengths (avoids per-char normalize of the whole text).
        nfd_orig: list[int] = []
        nfd_pos = 0
        for orig_idx, ch in enumerate(text):
            seg_len = len(_nfd_char(ch))
            for _ in range(seg_len):
                nfd_orig.append(orig_idx)
            nfd_pos += seg_len
        chars: list[str] = []
        offs: list[int] = []
        for c, orig_idx in zip(nfd, nfd_orig, strict=True):
            if unicodedata.category(c) == "Mn":
                continue
            if c in "-/\u2013":
                c = " "
            if c.isalnum() or c.isspace():
                chars.append(c.lower())
                offs.append(orig_idx)
        final_chars: list[str] = []
        final_offs: list[int] = []
        prev_space = False
        for c, o in zip(chars, offs, strict=True):
            is_space = c.isspace()
            if is_space:
                if prev_space:
                    continue
                final_chars.append(" ")
                final_offs.append(o)
                prev_space = True
            else:
                final_chars.append(c)
                final_offs.append(o)
                prev_space = False
        subject = "".join(final_chars)
        if not subject:
            return "", (), ()
        final_starts = tuple(final_offs)
        final_ends = tuple(o + 1 for o in final_offs)
        if (
            len(subject) == len(text)
            and subject == text.lower()
            and all(off == idx for idx, off in enumerate(final_offs))
        ):
            return subject, None, None
        return subject, final_starts, final_ends


@dataclass(frozen=True, slots=True)
class SymbolFold:
    name: str = "normalized"
    provenance: Provenance | None = Provenance(
        authority="BIPM",
        specification_name="SI Brochure",
        kind="specification",
        reference_url="https://www.bipm.org/en/measurement-units/",
        version="9",
        lifecycle="active",
        publication_year=2019,
    )
    _table: tuple[tuple[str, str], ...] = (
        ("²", "2"),
        ("³", "3"),
        ("µ", "μ"),
        ("Ω", "Ω"),
        ("Å", "Å"),
        ("°", "°"),
    )
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        for src, dst in self._table:
            text = text.replace(src, dst)
        return text, None, None


@dataclass(frozen=True, slots=True)
class StripSeparators:
    name: str = "compact"
    provenance: Provenance | None = Provenance(
        authority="ITU-T",
        specification_name="E.164",
        kind="specification",
        reference_url="https://www.itu.int/rec/T-REC-E.164",
        version="15",
        lifecycle="active",
        publication_year=2010,
    )
    stripped_chars: str | None = None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        subject_chars: list[str] = []
        starts: list[int] = []
        for i, ch in enumerate(text):
            if ch in " ().-":
                continue
            starts.append(i)
            subject_chars.append(ch)
        subject = "".join(subject_chars)
        if len(subject) == len(text):
            return subject, None, None
        if not subject:
            return "", (), ()
        ends = tuple(s + 1 for s in starts)
        return subject, tuple(starts), ends


@dataclass(frozen=True, slots=True)
class IDNAFold:
    """IDNA view: strip ``\\t\\n\\r``.

    The stripped characters are declared as data (``stripped_chars``) so the
    kernel engine loop and scanner can re-absorb trailing stripped chars into
    emitted spans without special-casing the view name.
    """

    name: str = "idna"
    provenance: Provenance | None = Provenance(
        authority="Unicode",
        specification_name="UTS #46",
        kind="specification",
        reference_url="https://unicode.org/reports/tr46/",
        version="31",
        lifecycle="active",
        publication_year=2024,
    )
    stripped_chars: str | None = "\t\n\r"

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        cleaned_chars: list[str] = []
        starts: list[int] = []
        for idx, ch in enumerate(text):
            if ch in "\t\n\r":
                continue
            cleaned_chars.append(ch)
            starts.append(idx)
        cleaned = "".join(cleaned_chars)
        if len(cleaned) == len(text):
            return cleaned, None, None
        if not cleaned:
            return "", (), ()
        ends = tuple(s + 1 for s in starts)
        return cleaned, tuple(starts), ends
