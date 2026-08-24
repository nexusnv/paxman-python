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
    subject, offsets = nf.normalize("Hello € WORLD")
    assert subject == "hello € world"
    assert offsets is None
    ctx = ScanContext.of("Hello € WORLD")
    view = ctx.view(nf.name, nf.normalize)
    assert view.subject == "hello € world"
    assert view.offsets is None


def test_separatorfold_bcp47() -> None:
    nf = SeparatorFold()
    assert nf.provenance is not None
    assert "BCP 47" in nf.provenance.specification_name
    assert SeparatorFold().normalize("en_US")[0] == "en-US"
    assert SeparatorFold().normalize("en_US")[1] is None


def test_accentstrip_country() -> None:
    nf = AccentStrip()
    assert nf.normalize("Côte d'Ivoire")[0] == "cote d'ivoire"
    assert nf.normalize("Côte d'Ivoire")[1] is None
    ctx = ScanContext.of("Côte d'Ivoire")
    view = ctx.view(nf.name, nf.normalize)
    assert ctx.text[view.original_span(0, 4)[0] : view.original_span(0, 4)[1]] == "Côte"


def test_symbolfold_si() -> None:
    nf = SymbolFold()
    # Provenance authority is BIPM; spec is SI Brochure
    assert nf.provenance is not None
    assert "BIPM" in nf.provenance.authority
    assert "SI Brochure" in nf.provenance.specification_name
    assert nf.normalize("m²")[0] == "m2"
    assert nf.normalize("µm")[0] == "μm"
    # keep IDNAFold import used
    assert IDNAFold().name == "idna"


def test_stripseparators_phone() -> None:
    nf = StripSeparators()
    subject, offsets = nf.normalize("+1 (555) 123-4567")
    assert subject == "+15551234567"
    assert offsets is not None
    assert len(offsets) == len(subject) + 1
    ctx = ScanContext.of("+1 (555) 123-4567")
    view = ctx.view("compact", nf.normalize)
    o_s, o_e = view.original_span(1, 4)
    assert 0 <= o_s < o_e <= len(ctx.text)


def test_sequence_composable() -> None:
    seq = NormalizerSequence(steps=(CaseFold(), SeparatorFold()))
    subject, offsets = seq.normalize("Hello_World")
    assert subject == "hello-world"
    assert offsets is None


def test_protocol_shape() -> None:
    assert isinstance(CaseFold(), Normalizer)
    assert isinstance(SeparatorFold(), Normalizer)
