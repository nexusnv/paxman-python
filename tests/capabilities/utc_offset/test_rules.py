"""Tests for UtcOffset validation rules (Task 6).

ISO 8601-1:2019 offset representations: shape plus the real-world
total-minutes range (-12:00..+14:00, Baker Island .. Kiritimati),
canonical ``+HH:MM`` normalization, and refusal of the RFC 3339
unknown-offset ``-00:00``.
"""

import pytest

from paxman.capabilities.UtcOffset.contract import UtcOffsetContract
from paxman.capabilities.UtcOffset.notation import UtcOffsetNotation
from paxman.capabilities.UtcOffset.rules.iso8601_offset_ed2019 import (
    SectionOffsetStructure,
)
from paxman.core.domain import RuleStrategy


def _offset(compact: str) -> UtcOffsetNotation:
    """Build an offset notation carrying ``compact`` as written."""
    return UtcOffsetNotation(compact=compact)


@pytest.mark.capability
class TestOffsetStructure:
    """Section offset-structure — PARSER over offset shape and range."""

    def setup_method(self) -> None:
        self.rule = SectionOffsetStructure()
        self.contract = UtcOffsetContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section offset-structure"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"utc_offset"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.citation != ""

    def test_provenance(self) -> None:
        provenance = self.rule.provenance
        assert provenance.authority == "ISO"
        assert provenance.specification_name == "ISO 8601-1"
        assert provenance.kind == "specification"
        assert provenance.reference_url == "https://www.iso.org/standard/70907.html"
        assert provenance.version == "2019"
        assert provenance.lifecycle == "active"
        assert provenance.publication_year == 2019

    def test_extended_form_matches(self) -> None:
        assert self.rule.matches(_offset("+05:30"), self.contract) is True
        assert self.rule.normalize(_offset("+05:30"), self.contract) == "+05:30"

    def test_basic_form_normalizes_to_extended(self) -> None:
        assert self.rule.matches(_offset("+0530"), self.contract) is True
        assert self.rule.normalize(_offset("+0530"), self.contract) == "+05:30"

    def test_reduced_hour_form_zero_pads(self) -> None:
        assert self.rule.matches(_offset("+05"), self.contract) is True
        assert self.rule.normalize(_offset("+05"), self.contract) == "+05:00"

    def test_single_digit_hour_zero_pads(self) -> None:
        assert self.rule.matches(_offset("+5"), self.contract) is True
        assert self.rule.normalize(_offset("+5"), self.contract) == "+05:00"

    def test_zulu_normalizes_to_zero(self) -> None:
        assert self.rule.matches(_offset("Z"), self.contract) is True
        assert self.rule.normalize(_offset("Z"), self.contract) == "+00:00"

    def test_lowercase_zulu_normalizes_to_zero(self) -> None:
        assert self.rule.matches(_offset("z"), self.contract) is True
        assert self.rule.normalize(_offset("z"), self.contract) == "+00:00"

    def test_utc_prefixed_human_notation(self) -> None:
        assert self.rule.matches(_offset("UTC+5"), self.contract) is True
        assert self.rule.normalize(_offset("UTC+5"), self.contract) == "+05:00"

    def test_gmt_prefixed_extended_notation(self) -> None:
        assert self.rule.matches(_offset("GMT-05:30"), self.contract) is True
        assert self.rule.normalize(_offset("GMT-05:30"), self.contract) == "-05:30"

    def test_lowercase_utc_prefix_accepted(self) -> None:
        assert self.rule.matches(_offset("utc+5"), self.contract) is True
        assert self.rule.normalize(_offset("utc+5"), self.contract) == "+05:00"

    def test_negative_offset_keeps_sign(self) -> None:
        assert self.rule.matches(_offset("-08:00"), self.contract) is True
        assert self.rule.normalize(_offset("-08:00"), self.contract) == "-08:00"

    def test_unknown_offset_refused(self) -> None:
        # RFC 3339 unknown-offset states ignorance of the offset — a
        # different entity from zero, with no information state in v1.
        assert self.rule.matches(_offset("-00:00"), self.contract) is False

    def test_negative_zero_refused_in_every_form(self) -> None:
        assert self.rule.matches(_offset("-00"), self.contract) is False
        assert self.rule.matches(_offset("-0000"), self.contract) is False

    def test_positive_zero_accepted(self) -> None:
        assert self.rule.matches(_offset("+00:00"), self.contract) is True
        assert self.rule.normalize(_offset("+00:00"), self.contract) == "+00:00"

    def test_maximum_offset_boundary(self) -> None:
        assert self.rule.matches(_offset("+14:00"), self.contract) is True
        assert self.rule.normalize(_offset("+14:00"), self.contract) == "+14:00"

    def test_total_minutes_bound_pins(self) -> None:
        """Real-world range is a signed total (-720..+840 minutes), not
        independent HH/MM caps: +14:00 (Kiritimati) and -12:00 (Baker
        Island) hold; +14:30 (nowhere on Earth), -12:30, and -14:00 fail.
        """
        assert self.rule.matches(_offset("+14:00"), self.contract) is True
        assert self.rule.normalize(_offset("+14:00"), self.contract) == "+14:00"
        assert self.rule.matches(_offset("-12:00"), self.contract) is True
        assert self.rule.normalize(_offset("-12:00"), self.contract) == "-12:00"
        assert self.rule.matches(_offset("+14:30"), self.contract) is False
        assert self.rule.matches(_offset("-12:30"), self.contract) is False
        assert self.rule.matches(_offset("-14:00"), self.contract) is False

    def test_beyond_maximum_offset_rejected(self) -> None:
        assert self.rule.matches(_offset("+15:00"), self.contract) is False
        assert self.rule.matches(_offset("UTC+15:00"), self.contract) is False
        assert self.rule.matches(_offset("-13:00"), self.contract) is False

    def test_minute_range_enforced(self) -> None:
        assert self.rule.matches(_offset("+05:60"), self.contract) is False
        assert self.rule.matches(_offset("+05:61"), self.contract) is False
        assert self.rule.matches(_offset("+05:59"), self.contract) is True

    @pytest.mark.parametrize(
        "compact",
        [
            "",
            "05:30",
            "UTC",
            "GMT",
            "+053",
            "+05301",
            "+5:3",
            "+05:3",
            "+05:30:00",
            "hello",
            "+",
            "UTC+",
            "Zulu",
        ],
    )
    def test_malformed_shapes_rejected(self, compact: str) -> None:
        assert self.rule.matches(_offset(compact), self.contract) is False

    def test_matches_never_raises_and_normalize_echoes(self) -> None:
        assert self.rule.matches(_offset(""), self.contract) is False
        assert isinstance(self.rule.normalize(_offset(""), self.contract), str)
