"""Tests for DOI recognition grammar."""

from __future__ import annotations

import pytest

from paxman.capabilities.DOI.grammar.doi_recognition import (
    DOIRecognitionGrammar,
)
from paxman.capabilities.DOI.notation import DOINotation

pytestmark = [pytest.mark.capability]


def _expected(prefix: str, suffix: str) -> DOINotation:
    return DOINotation(prefix=prefix, suffix=suffix, canonical=f"{prefix}/{suffix}")


class TestDOIRecognitionGrammar:
    """Bare 10.-prefixed core with carrier groups, ASCII-only fold."""

    def test_bare_span(self) -> None:
        text = "10.1038/nature12345"
        results = DOIRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345")
        assert (results[0].start, results[0].end) == (0, len(text))
        assert results[0].raw_text == text

    def test_uppercase_ascii_fold(self) -> None:
        results = DOIRecognitionGrammar().recognize("10.1038/NATURE12345")
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345")

    def test_nonlatin_case_preserved(self) -> None:
        # Handbook case Ex.2: U+00C1 vs U+00E1 are NOT equivalent — the
        # ASCII-only fold must preserve both byte-identically.
        upper = DOIRecognitionGrammar().recognize("10.26321/Á")
        lower = DOIRecognitionGrammar().recognize("10.26321/á")
        assert len(upper) == 1
        assert len(lower) == 1
        assert upper[0].notation.suffix == "Á"
        assert lower[0].notation.suffix == "á"
        assert upper[0].notation.canonical != lower[0].notation.canonical

    def test_no_unicode_normalization(self) -> None:
        # Precomposed U+00E1 vs decomposed U+0061+U+0301 must not coalesce:
        # Handbook performs no ISO/IEC 10646 normalization on comparison.
        precomposed = DOIRecognitionGrammar().recognize("10.26321/\u00e1")
        decomposed = DOIRecognitionGrammar().recognize("10.26321/a\u0301")
        assert len(precomposed) == 1
        assert len(decomposed) == 1
        assert precomposed[0].notation != decomposed[0].notation

    def test_resolver_url_span(self) -> None:
        text = "https://doi.org/10.1038/nature12345"
        results = DOIRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345")
        assert (results[0].start, results[0].end) == (0, len(text))
        assert results[0].raw_text == text

    def test_www_host_span(self) -> None:
        text = "https://www.doi.org/10.1038/nature12345"
        results = DOIRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345")
        assert results[0].raw_text == text

    def test_dx_http_hosts(self) -> None:
        for text in (
            "http://dx.doi.org/10.1000/182",
            "http://doi.org/10.1000/182",
        ):
            results = DOIRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation == _expected("10.1000", "182")
            assert results[0].raw_text == text

    def test_doi_label_span(self) -> None:
        for text, canonical in (
            ("doi:10.1038/nature12345", "10.1038/nature12345"),
            ("DOI: 10.1038/nature12345", "10.1038/nature12345"),
            ("doi 10.1038/nature12345", "10.1038/nature12345"),
        ):
            results = DOIRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation.canonical == canonical
            assert results[0].raw_text == text

    def test_uppercase_scheme_host_folded(self) -> None:
        results = DOIRecognitionGrammar().recognize(
            "HTTPS://DOI.ORG/10.1038/NATURE12345"
        )
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345")

    def test_urn_info_carriers(self) -> None:
        for text in (
            "urn:doi:10.1038/nature12345",
            "info:doi/10.1038/nature12345",
        ):
            results = DOIRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation == _expected("10.1038", "nature12345")
            assert results[0].raw_text == text

    def test_handbook_case_vector(self) -> None:
        upper = DOIRecognitionGrammar().recognize("10.5594/SMPTE.ST2067-21.2020")
        lower = DOIRecognitionGrammar().recognize("10.5594/sMPTE.sT2067-21.2020")
        assert len(upper) == 1
        assert len(lower) == 1
        assert upper[0].notation == lower[0].notation
        assert upper[0].notation.canonical == "10.5594/smpte.st2067-21.2020"

    def test_dotted_subregistrant(self) -> None:
        results = DOIRecognitionGrammar().recognize("10.13003/5jchdy")
        assert len(results) == 1
        assert results[0].notation == _expected("10.13003", "5jchdy")

    def test_suffix_slashes_retained(self) -> None:
        results = DOIRecognitionGrammar().recognize("10.7774/cevr.2016.5.1.19")
        assert len(results) == 1
        assert results[0].notation == _expected("10.7774", "cevr.2016.5.1.19")

    def test_trailing_punct_excluded(self) -> None:
        for text, span_end in (
            ("See 10.1038/nature12345.", 23),
            ("See 10.1038/nature12345)", 23),
            ("See 10.1038/nature12345,", 23),
        ):
            results = DOIRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation == _expected("10.1038", "nature12345")
            assert results[0].end == span_end, f"failed for {text!r}"

    def test_percent2f_literal(self) -> None:
        # Percent-escapes are retained literally (never decoded to '/');
        # the hex letters are Basic Latin so the ASCII fold applies, and
        # the folded form is the fixed point.
        results = DOIRecognitionGrammar().recognize("10.1038/a%2Fb")
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "a%2fb")

    def test_embedded_in_sentence(self) -> None:
        text = "see 10.1038/nature12345 for details"
        results = DOIRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345")
        assert results[0].raw_text == "10.1038/nature12345"

    def test_multiple_matches(self) -> None:
        text = "10.1000/182 and 10.1038/nature12345"
        results = DOIRecognitionGrammar().recognize(text)
        assert len(results) == 2
        assert results[0].start < results[1].start
        for m in results:
            assert m.raw_text == text[m.start : m.end]

    def test_missing_suffix_slash_prefix(self) -> None:
        assert DOIRecognitionGrammar().recognize("") == []
        assert DOIRecognitionGrammar().recognize("10.1038/") == []
        assert DOIRecognitionGrammar().recognize("10.1038nature12345") == []
        assert DOIRecognitionGrammar().recognize("nature12345") == []
        assert DOIRecognitionGrammar().recognize("20.500.1234/abc") == []
        assert DOIRecognitionGrammar().recognize("doi:") == []

    def test_shortdoi_missing(self) -> None:
        assert DOIRecognitionGrammar().recognize("10/gf2p3c") == []

    def test_overlong_registrant_missing(self) -> None:
        assert DOIRecognitionGrammar().recognize("10.1234567890/x") == []

    def test_urn_colon_form_missing(self) -> None:
        # Proxy URN-colon form is DEFERRED to a future carrier group (v1:
        # no claim). The colon is not a structural separator here.
        assert (
            DOIRecognitionGrammar().recognize("https://doi.org/urn:doi:10.123:456")
            == []
        )

    def test_left_glued_runs_missing(self) -> None:
        assert DOIRecognitionGrammar().recognize("x10.1038/nature12345") == []
        assert DOIRecognitionGrammar().recognize("110.1038/nature12345") == []
        assert DOIRecognitionGrammar().recognize("doi10.1038/nature12345") == []

    def test_right_glue_merges_opaque_suffix(self) -> None:
        # Variable-width opaque suffix: trailing alphanumerics are part of
        # the (longer) DOI name, unlike fixed-width ORCID trailing guards.
        results = DOIRecognitionGrammar().recognize("10.1038/nature12345x")
        assert len(results) == 1
        assert results[0].notation == _expected("10.1038", "nature12345x")

    def test_name_semantics_single_value(self) -> None:
        grammar = DOIRecognitionGrammar()
        assert grammar.name == "doi_recognition"
        assert grammar.semantics == "doi_recognition"
        assert grammar.single_value is True
