"""Parity shard — scanner Language BCP-47 (ADR §9.3)."""

from __future__ import annotations

import pytest

from paxman.capabilities.Language.grammar.bcp47_tag_recognition import (
    BCP47TagGrammar,
)
from paxman.core.grammar import BoundarySpec, ScannerMatcher
from tests.property._legacy_language_grammars import LegacyBCP47TagGrammar
from tests.property.grammar_kernel_parity import assert_kernel_parity

pytestmark = [pytest.mark.property]


def test_bcp47_uses_scanner_matcher() -> None:
    g = BCP47TagGrammar()
    assert hasattr(g, "matchers"), "BCP47TagGrammar must expose matchers"
    matchers = g.matchers
    assert matchers is not None
    assert len(matchers) == 1
    m = matchers[0]
    assert isinstance(m, ScannerMatcher)
    assert m.view_name == "bcp47_normalized"
    assert m.boundary == BoundarySpec.WORD
    # scanner fork deleted
    import pathlib

    src = pathlib.Path(
        "paxman/capabilities/Language/grammar/bcp47_tag_recognition.py"
    ).read_text()
    assert "_BCP47RegexStage" not in src
    assert "_bcp47_notation" not in src


# Golden corpus from pre-migration grammar — valid/invalid, case variants,
# underscore, grandfathered, privateuse, extensions, region, script.
_CORPUS: tuple[str, ...] = (
    # valid langtags
    "zh-Hans-CN",
    "EN-us",
    "fr_FR",
    "zh_Hans_CN",
    "sl-nedis",
    "ZH-HANS-CN",
    "x-private",
    "i-cherokee",
    "es-419",
    "en-GB",
    "en-US-x-private",
    "en-a-foo",
    "en-x-private",
    "zh-yue",
    "sr-Latn-RS",
    "de-CH-1996",
    "en-US-u-co-phonebk",
    # surrounding
    "lang: fr-FR here",
    "en fr-FR",
    '"en-US"',
    "[fr-FR]",
    "Contact en-US please",
    "Xenon en-US here",
    # invalid / edge
    "en",
    "enUS",
    "Xenon",
    "",
    "   ",
    "en-US-",
    "x",
    "en-a",
    "en-123",
    "too-long-subtag-abcdeabcdeabcde",
    "en--US",
    "i-klingon",
    # underscore variants
    "en_US_x_private",
    "sr_Latn_RS",
    # mixed multiple mentions (single call extracts longest)
    "en-US and fr-FR",
    "Visit https://example.com and en-GB please",
)


@pytest.mark.parametrize("text", _CORPUS)
def test_bcp47_scanner_parity_byte_identical(text: str) -> None:
    assert_kernel_parity(LegacyBCP47TagGrammar(), BCP47TagGrammar(), text)


def test_bcp47_scanner_parity_corpus_len() -> None:
    # ensure corpus not trivially small — byte-identical over full legacy corpus
    assert len(_CORPUS) >= 30
