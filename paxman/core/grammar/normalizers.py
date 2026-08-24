"""Normalizers — first-class, composable, provenance-aware."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from paxman.core.domain import Provenance


@runtime_checkable
class Normalizer(Protocol):
    name: str
    provenance: Provenance | None

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]: ...


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        cur = text
        cur_offsets: tuple[int, ...] | None = None
        for step in self.steps:
            nxt, off = step.normalize(cur)
            cur, cur_offsets = nxt, off if off is not None else cur_offsets
        return cur, cur_offsets


@dataclass(frozen=True, slots=True)
class CaseFold:
    name: str = "casefolded"
    provenance: Provenance | None = None

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        return text.lower(), None


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        return text.replace("_", "-"), None


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        nfd = unicodedata.normalize("NFD", text)
        stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
        return stripped.lower(), None


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        chars: list[str] = []
        offs: list[int] = []
        for idx, ch in enumerate(text):
            nfd = unicodedata.normalize("NFD", ch)
            stripped = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
            for c2 in stripped:
                if c2 in "-/\u2013":
                    c2 = " "
                if c2.isalnum() or c2.isspace():
                    chars.append(c2.lower())
                    offs.append(idx)
                else:
                    continue
        # Collapse runs of whitespace to a single space
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
            # Empty subject: offsets map whole input
            return "", (0, len(text)) if text else (0,)
        # Build offsets tuple len(subject)+1
        offsets = tuple(final_offs) + (len(text),)
        # Identity optimization: if subject equals lowercased text without
        # changes and offsets is 0..n, return None. But we have lowercasing,
        # so check length and lower equality.
        if (
            len(subject) == len(text)
            and subject == text.lower()
            and all(off == idx for idx, off in enumerate(final_offs))
        ):
            return subject, None
        return subject, offsets


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        for src, dst in self._table:
            text = text.replace(src, dst)
        return text, None


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        subject_chars: list[str] = []
        offsets: list[int] = []
        for i, ch in enumerate(text):
            if ch in " ().-":
                continue
            offsets.append(i)
            subject_chars.append(ch)
        offsets.append(len(text))
        subject = "".join(subject_chars)
        return subject, tuple(offsets) if len(subject) != len(text) else None


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

    def normalize(self, text: str) -> tuple[str, tuple[int, ...] | None]:
        cleaned = text.replace("\t", "").replace("\n", "").replace("\r", "")
        if len(cleaned) == len(text):
            return cleaned, None
        return cleaned, tuple(range(len(cleaned) + 1))
