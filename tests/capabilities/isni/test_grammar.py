"""Tests for ISNI recognition grammar."""

import pytest

from paxman.capabilities.ISNI.grammar.isni_recognition import (
    ISNIRecognitionGrammar,
)


@pytest.mark.capability
class TestISNIRecognitionGrammar:
    """isni_recognition claims every §2.1 RECOGNIZE row with exact spans."""

    def setup_method(self) -> None:
        self.grammar = ISNIRecognitionGrammar()

    def test_identity(self) -> None:
        assert self.grammar.name == "isni_recognition"
        assert self.grammar.semantics == "isni_recognition"
        assert self.grammar.single_value is True

    @pytest.mark.parametrize(
        ("text", "compact", "span"),
        [
            ("ISNI 0000 0001 2103 2683", "0000000121032683", (0, 24)),
            ("0000 0001 2103 2683", "0000000121032683", (0, 19)),
            ("0000000121032683", "0000000121032683", (0, 16)),
            ("0000-0001-2103-2683", "0000000121032683", (0, 19)),
            (
                "https://isni.org/isni/0000000121032683",
                "0000000121032683",
                (0, 38),
            ),
            ("urn:isni:0000000121032683", "0000000121032683", (0, 25)),
            ("ISNI: 0000 0001 2103 2683", "0000000121032683", (0, 25)),
            ("0000 0001 2281 955x", "000000012281955X", (0, 19)),
            ("see ISNI 0000 0001 2103 2683 (Shakespeare)", "0000000121032683", (4, 28)),
        ],
    )
    def test_recognize_rows(
        self, text: str, compact: str, span: tuple[int, int]
    ) -> None:
        matches = self.grammar.recognize(text)
        assert len(matches) == 1
        assert matches[0].notation.compact == compact
        assert (matches[0].start, matches[0].end) == span
        assert matches[0].raw_text == text[span[0] : span[1]]
        assert matches[0].notation.spaced.replace(" ", "") == compact

    @pytest.mark.parametrize(
        "text",
        [
            "ISNI0000000121032683",
            "0000  0001 2103 2683",
            "0000\t0001 2103 2683",
            "００００ ０００１ ２１０３ ２６８３",
            "000000012103268",
            "00000001210326833",
            "X0000000121032683",
            "0000000121032683Y",
            "not an isni",
            "",
        ],
    )
    def test_reject_rows(self, text: str) -> None:
        assert self.grammar.recognize(text) == []

    def test_pipe_carrier_matches_inner_compact(self) -> None:
        # No dedicated MARC/VIAF pipe pattern (DEFERRED): the bare compact
        # inside still resolves as an embedded mention.
        matches = self.grammar.recognize("ISNI|000000012146438X")
        assert len(matches) == 1
        assert matches[0].notation.compact == "000000012146438X"
        assert (matches[0].start, matches[0].end) == (5, 21)

    def test_multiple_matches(self) -> None:
        matches = self.grammar.recognize("0000000121032683 and 000000012146438X")
        assert len(matches) == 2
        assert matches[0].notation.compact == "0000000121032683"
        assert matches[1].notation.compact == "000000012146438X"
