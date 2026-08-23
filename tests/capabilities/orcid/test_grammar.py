"""Tests for ORCID recognition grammar."""

from __future__ import annotations

import pytest

from paxman.capabilities.ORCID.grammar.orcid_recognition import (
    ORCIDRecognitionGrammar,
)
from paxman.capabilities.ORCID.notation import ORCIDNotation

pytestmark = [pytest.mark.capability]


def _expected(hyphenated: str, *, is_uri: bool = False) -> ORCIDNotation:
    compact = hyphenated.replace("-", "")
    return ORCIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        uri=f"https://orcid.org/{hyphenated}",
        check=compact[-1],
        is_uri="true" if is_uri else "false",
    )


class TestORCIDRecognitionGrammar:
    """Hyphenated 4-4-4-4 payload, optional label/host prefix, word_only guards."""

    def test_bare_hyphenated(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0002-1825-0097")
        assert len(results) == 1
        assert results[0].notation == _expected("0000-0002-1825-0097")
        assert (results[0].start, results[0].end) == (0, 19)
        assert results[0].raw_text == "0000-0002-1825-0097"

    def test_uri_prefix_canonical(self) -> None:
        text = "https://orcid.org/0000-0002-1825-0097"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].notation.hyphenated == "0000-0002-1825-0097"
        assert results[0].notation.is_uri == "true"
        assert results[0].raw_text == text
        assert (results[0].start, results[0].end) == (0, len(text))

    def test_http_uri_variant(self) -> None:
        text = "http://orcid.org/0000-0002-1694-233X"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        # scheme normalized: uri field is always https
        assert results[0].notation.uri.startswith("https://")

    def test_domain_only_host(self) -> None:
        for text in (
            "orcid.org/0000-0002-1825-0097",
            "www.orcid.org/0000-0002-1825-0097",
        ):
            results = ORCIDRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation.hyphenated == "0000-0002-1825-0097"

    def test_uppercase_host_fold(self) -> None:
        text = "https://ORCID.org/0000-0002-1825-0097"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1

    def test_label_orcid_and_isni(self) -> None:
        for text in (
            "ORCID: 0000-0002-1825-0097",
            "orcid - 0000-0002-1825-0097",
            "ISNI: 0000-0002-1825-0097",
        ):
            results = ORCIDRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].raw_text == text
            assert results[0].notation.hyphenated == "0000-0002-1825-0097"

    def test_glued_label_does_not_fuse(self) -> None:
        # Label requires [\s:-]+ separator: glued label means no claim at all.
        assert ORCIDRecognitionGrammar().recognize("ORCID0000-0002-1825-0097") == []

    def test_lowercase_x_folds_to_upper(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0002-1694-233x")
        assert len(results) == 1
        assert results[0].notation.check == "X"
        assert results[0].notation.hyphenated.endswith("X")

    def test_leading_zeros_preserved(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0001-5109-3700")
        assert len(results) == 1
        assert results[0].notation.compact == "0000000151093700"

    def test_embedded_in_prose(self) -> None:
        text = "see https://orcid.org/0000-0002-1825-0097 for author"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].start == text.index("https://")
        assert results[0].end == len("https://orcid.org/0000-0002-1825-0097") + (
            results[0].start
        )

    def test_trailing_slash_not_claimed(self) -> None:
        text = "https://orcid.org/0000-0002-1825-0097/"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].raw_text.endswith("0097")
        assert not results[0].raw_text.endswith("/")

    def test_quoted_and_bracketed(self) -> None:
        for text in ('"0000-0002-1825-0097"', "[0000-0002-1825-0097]"):
            results = ORCIDRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].raw_text == "0000-0002-1825-0097"

    def test_compact_digits_missing(self) -> None:
        # v1 grammar is hyphen-only: contiguous digits are MISSING.
        assert ORCIDRecognitionGrammar().recognize("0000000218250097") == []

    def test_spaced_isni_style_missing(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("0000 0002 1825 0097") == []

    def test_overlong_rejected(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("0000-0002-1825-00977") == []
        assert (
            ORCIDRecognitionGrammar().recognize(
                "https://orcid.org/0000-0002-1825-00977"
            )
            == []
        )

    def test_underlong_rejected(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("0000-0002-1825-009") == []

    def test_x_mid_run_missing(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("000X-0002-1825-0097") == []

    def test_fullwidth_digits_missing(self) -> None:
        # (?ai:) ASCII-only body rejects fullwidth digits.
        assert (
            ORCIDRecognitionGrammar().recognize(
                "\uff10\uff10\uff10\uff10-\uff10\uff10\uff10\uff12-"
                "\uff11\uff18\uff12\uff15-\uff10\uff10\uff19\uff17"
            )
            == []
        )

    def test_digit_glued_runs_rejected(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("X0000-0002-1825-0097") == []
        assert ORCIDRecognitionGrammar().recognize("A0000-0002-1825-0097B") == []

    def test_trailing_hyphen_continuation_claims_payload_only(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0002-1825-0097-1234")
        assert len(results) == 1
        assert results[0].raw_text == "0000-0002-1825-0097"

    def test_multiple_matches(self) -> None:
        text = "0000-0002-1825-0097 / 0000-0001-5109-3700"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 2
        assert results[0].start < results[1].start
        for m in results:
            assert m.raw_text == text[m.start : m.end]

    def test_span_invariants(self) -> None:
        texts = [
            "0000-0002-1825-0097",
            "https://orcid.org/0000-0002-1825-0097",
            "ORCID: 0000-0002-1694-233X",
            "see orcid.org/0000-0001-5109-3700 (Jane)",
        ]
        for text in texts:
            for m in ORCIDRecognitionGrammar().recognize(text):
                assert 0 <= m.start <= m.end <= len(text)
                assert m.raw_text == text[m.start : m.end]
                assert len(m.raw_text) == m.end - m.start

    def test_empty(self) -> None:
        g = ORCIDRecognitionGrammar()
        assert g.recognize("") == []
        assert g.recognize("   ") == []

    def test_single_value_true(self) -> None:
        assert ORCIDRecognitionGrammar.single_value is True

    def test_name_and_semantics(self) -> None:
        g = ORCIDRecognitionGrammar()
        assert g.name == "orcid_recognition"
        assert g.semantics == "orcid_recognition"
        assert g.semantics != ""
