"""Normalizer unit tests — composable, provenance-aware, offset-disciplined."""

from __future__ import annotations

from paxman.core.domain import Provenance
from paxman.core.grammar.normalizers import (
    AccentStrip,
    CaseFold,
    IDNAFold,
    Normalizer,
    NormalizerSequence,
    SeparatorFold,
    StripSeparators,
    SymbolFold,
)
from paxman.core.grammar.scan_context import ScanContext

BIPM = Provenance(
    authority="BIPM",
    specification_name="SI Brochure",
    kind="specification",
    reference_url="https://www.bipm.org/",
    version="9",
    lifecycle="active",
    publication_year=2019,
)


def test_casefold_identity_view() -> None:
    nf = CaseFold()
    assert nf.name == "casefolded"
    assert nf.provenance is None
    subject, starts, ends = nf.normalize("Hello € WORLD")
    assert subject == "hello € world"
    assert starts is None and ends is None
    ctx = ScanContext.of("Hello € WORLD")
    view = ctx.view(nf.name, nf.normalize)
    assert view.subject == "hello € world"
    assert view.source_starts is None
    assert view.source_ends is None


def test_separatorfold_bcp47() -> None:
    nf = SeparatorFold()
    assert nf.provenance is not None
    assert "BCP 47" in nf.provenance.specification_name
    assert SeparatorFold().normalize("en_US")[0] == "en-US"
    subj, s, e = SeparatorFold().normalize("en_US")
    assert s is None and e is None
    _ = subj


def test_accentstrip_country() -> None:
    nf = AccentStrip()
    assert nf.normalize("Côte d'Ivoire")[0] == "cote d'ivoire"
    subj, s, e = nf.normalize("Côte d'Ivoire")
    assert s is None and e is None
    _ = subj
    ctx = ScanContext.of("Côte d'Ivoire")
    view = ctx.view(nf.name, nf.normalize)
    assert ctx.text[view.original_span(0, 4)[0] : view.original_span(0, 4)[1]] == "Côte"


def test_symbolfold_si() -> None:
    nf = SymbolFold()
    assert nf.provenance is not None
    assert "BIPM" in nf.provenance.authority
    assert "SI Brochure" in nf.provenance.specification_name
    assert nf.normalize("m²")[0] == "m2"
    assert nf.normalize("µm")[0] == "μm"
    subj, s, e = nf.normalize("m²")
    assert s is None and e is None
    _ = subj
    assert IDNAFold().name == "idna"


def test_stripseparators_phone() -> None:
    nf = StripSeparators()
    subject, starts, ends = nf.normalize("+1 (555) 123-4567")
    assert subject == "+15551234567"
    assert starts is not None and ends is not None
    assert len(starts) == len(subject)
    assert len(ends) == len(subject)
    ctx = ScanContext.of("+1 (555) 123-4567")
    view = ctx.view("compact", nf.normalize)
    o_s, o_e = view.original_span(1, 4)
    assert 0 <= o_s < o_e <= len(ctx.text)


def test_sequence_composable() -> None:
    seq = NormalizerSequence(steps=(CaseFold(), SeparatorFold()))
    subject, starts, ends = seq.normalize("Hello_World")
    assert subject == "hello-world"
    assert starts is None and ends is None


def test_protocol_shape() -> None:
    assert isinstance(CaseFold(), Normalizer)
    assert isinstance(SeparatorFold(), Normalizer)
