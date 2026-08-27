"""Normalizers — first-class, composable, provenance-aware.

Two-array (starts,ends) offset mapping; CountryNameFold is single-pass NFD
with cache."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from paxman.core.domain import Provenance


@runtime_checkable
class Normalizer(Protocol):
    name: str
    provenance: Provenance | None

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]: ...


@dataclass(frozen=True, slots=True)
class NormalizerSequence:
    steps: tuple[Normalizer, ...]

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
                cur = nxt
            else:
                assert off_starts is not None and off_ends is not None
                if cur_starts is None and cur_ends is None:
                    cur_starts = off_starts
                    cur_ends = off_ends
                else:
                    assert cur_starts is not None and cur_ends is not None
                    composed_starts = tuple(cur_starts[o] for o in off_starts)
                    composed_ends = tuple(cur_ends[o] for o in off_starts)
                    cur_starts = composed_starts
                    cur_ends = composed_ends
                cur = nxt
        return cur, cur_starts, cur_ends


@dataclass(frozen=True, slots=True)
class CaseFold:
    name: str = "casefolded"
    provenance: Provenance | None = None

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

    def normalize(
        self, text: str
    ) -> tuple[str, tuple[int, ...] | None, tuple[int, ...] | None]:
        nfd = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        return stripped.lower(), None, None


_NFD_CACHE: dict[str, str] = {}


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
            cached = _NFD_CACHE.get(ch)
            if cached is None:
                cached = unicodedata.normalize("NFD", ch)
                _NFD_CACHE[ch] = cached
            seg_len = len(cached)
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
