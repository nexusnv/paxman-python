"""Parity shard — scanner URL paren-balance + bare-scheme (ADR §9.3)."""

from __future__ import annotations

import pathlib

import pytest

from paxman.capabilities.URL.grammar.absolute_uri_recognition import (
    AbsoluteUriRecognition,
)
from paxman.core.grammar import BoundarySpec, ScannerMatcher
from tests.property._legacy_phone_url_grammars import LegacyAbsoluteUriRecognition
from tests.property.grammar_kernel_parity import assert_kernel_parity

pytestmark = [pytest.mark.property]


def test_url_uses_scanner_matcher() -> None:
    g = AbsoluteUriRecognition()
    assert hasattr(g, "matchers"), "AbsoluteUriRecognition must expose matchers"
    matchers = g.matchers
    assert matchers is not None
    assert len(matchers) == 1
    m = matchers[0]
    assert isinstance(m, ScannerMatcher)
    assert m.view_name == "idna" or m.view == "idna"
    assert m.boundary == BoundarySpec.SCHEME_CHAR_LEFT
    src = pathlib.Path(
        "paxman/capabilities/URL/grammar/absolute_uri_recognition.py"
    ).read_text()
    assert "PostStage(" not in src
    assert "RegexStage(" not in src
    assert "_url_trim" not in src
    assert "_URL_PATTERN" not in src


# Golden corpus from pre-migration grammar — paren-balance, bare-scheme,
# multi-line, delimiters, shape-only. Byte-identical vs legacy.
_CORPUS: tuple[str, ...] = (
    # Plain URLs
    "https://example.com",
    "https://example.com/path",
    "http://example.com.",
    "http://example.com/",
    "mailto:user@münchen.de",
    # Paren-balance Appendix C
    "https://example.com/path_(with_parens)",
    "https://example.com/a(b(c)d)e",
    "https://example.com/a(b(c)d)e))",
    "https://example.com/foo))",
    "https://example.com/foo)))bar",
    "https://example.com))",
    "https://example.com)))",
    "(https://example.com)",
    "((https://example.com))",
    "(https://example.com/a(b)c)",
    "Visit https://example.com/a(b(c)d)e now",
    "See (https://example.com/path_(x)) end",
    # Bare-scheme drop (D16)
    "Note:",
    "https:",
    "https:))))",
    "https://",
    "http://99999/",
    # Scheme-char left boundary
    "ahttps://example.com",
    "1https://example.com",
    "(https://example.com",
    "xhttps://example.com y",
    # Multi-line / IDNAFold view (tab newline)
    "http://exa\nmple.com/",
    "http://exa\tmple.com/",
    "http://exa\r\nmple.com/",
    "See http://exa\nmple.com/ here",
    # Delimiters / shape-only
    '"https://example.com/"',
    '"https://example.com/" then "mailto:a@b.de"',
    "https://example.com/ and https://example.org/",
    "no url here",
    "",
    "   ",
)


@pytest.mark.parametrize("text", _CORPUS)
def test_url_scanner_parity_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacyAbsoluteUriRecognition(), AbsoluteUriRecognition(), text)


def test_url_scanner_parity_corpus_len() -> None:
    assert len(_CORPUS) >= 20
