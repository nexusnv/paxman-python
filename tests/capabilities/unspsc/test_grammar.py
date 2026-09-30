"""Tests for UNSPSCRecognitionGrammar (§2.1 inventory, §2.2 wild shapes)."""

import pytest

from paxman.capabilities.UNSPSC.grammar.unspsc_recognition import (
    UNSPSCRecognitionGrammar,
)


@pytest.mark.capability
class TestUNSPSCRecognitionGrammar:
    """unspsc_recognition claims every §2.1 RECOGNIZE row with exact spans."""

    def setup_method(self) -> None:
        self.grammar = UNSPSCRecognitionGrammar()

    def test_identity(self) -> None:
        assert self.grammar.name == "unspsc_recognition"
        assert self.grammar.semantics == "unspsc_recognition"
        assert self.grammar.single_value is True

    @pytest.mark.parametrize(
        ("text", "digits", "level", "function", "native_length", "span"),
        [
            ("44103103", "44103103", "commodity", "", 8, (0, 8)),
            ("43211503", "43211503", "commodity", "", 8, (0, 8)),
            ("10101501", "10101501", "commodity", "", 8, (0, 8)),
            ("25101703", "25101703", "commodity", "", 8, (0, 8)),
            ("43000000", "43000000", "segment", "", 8, (0, 8)),
            ("43210000", "43210000", "family", "", 8, (0, 8)),
            ("43211500", "43211500", "class", "", 8, (0, 8)),
            ("441217", "44121700", "class", "", 6, (0, 6)),
            ("UNSPSC 44103103", "44103103", "commodity", "", 8, (0, 15)),
            ("UNSPSC: 44103103", "44103103", "commodity", "", 8, (0, 16)),
            ("UNSPSC #43211507", "43211507", "commodity", "", 8, (0, 16)),
            ("unspsc 44103103", "44103103", "commodity", "", 8, (0, 15)),
            ("UNSPSC000.44103103", "44103103", "commodity", "", 8, (0, 18)),
            ("4410310314", "44103103", "commodity", "14", 10, (0, 10)),
            ("unspsc,43211509", "43211509", "commodity", "", 8, (7, 15)),
            ("44103103.0", "44103103", "commodity", "", 8, (0, 8)),
            (
                "see UNSPSC 44103103 (Printers)",
                "44103103",
                "commodity",
                "",
                8,
                (4, 19),
            ),
            (
                "Printers (44103103) approved",
                "44103103",
                "commodity",
                "",
                8,
                (10, 18),
            ),
        ],
    )
    def test_recognize_rows(
        self,
        text: str,
        digits: str,
        level: str,
        function: str,
        native_length: int,
        span: tuple[int, int],
    ) -> None:
        matches = self.grammar.recognize(text)
        assert len(matches) == 1
        assert matches[0].notation.digits == digits
        assert matches[0].notation.level == level
        assert matches[0].notation.function == function
        assert matches[0].notation.native_length == native_length
        assert (matches[0].start, matches[0].end) == span
        assert matches[0].raw_text == text[span[0] : span[1]]

    def test_multiple_matches(self) -> None:
        matches = self.grammar.recognize("44103103, 43211503")
        assert [(m.start, m.end) for m in matches] == [(0, 8), (10, 18)]
        assert [m.notation.digits for m in matches] == ["44103103", "43211503"]

    @pytest.mark.parametrize(
        "text",
        [
            "43",
            "4321",
            "43 21 15 03",
            "43.21.15.03",
            "4410-3103",
            "44103103-14",
            "4410310",
            "441031031",
            "44103103144",
            "X44103103",
            "44103103Y",
            "A4410310314B",
            "",
        ],
    )
    def test_reject_rows(self, text: str) -> None:
        assert self.grammar.recognize(text) == []
