"""Tests for UnicodeUts46Statuses — UTS #46 statuses, hyphens, ACE."""

import pytest

from paxman.capabilities.Domain.contract import DomainContract
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.unicode_uts46_statuses import (
    UnicodeUts46Statuses,
    uts46_ok,
)
from paxman.core.domain import RuleStrategy

pytestmark = pytest.mark.capability


def _notation(*labels: str, raw: str = "example.com") -> DomainNotation:
    return DomainNotation(raw=raw, labels=tuple(labels), tld=labels[-1])


class TestUnicodeUts46Statuses:
    """Status table, D13 hyphens, STD3, and the ACE round trip."""

    def setup_method(self) -> None:
        self.rule = UnicodeUts46Statuses()
        self.contract = DomainContract()

    def test_accepts_valid_ascii_labels(self) -> None:
        assert self.rule.matches(_notation("example", "com"), self.contract) is True

    def test_accepts_non_ascii_u_label(self) -> None:
        assert self.rule.matches(_notation("münchen", "de"), self.contract) is True

    def test_accepts_valid_ace_label(self) -> None:
        assert (
            self.rule.matches(_notation("xn--mnchen-3ya", "de"), self.contract) is True
        )

    def test_rejects_ace_label_with_empty_payload(self) -> None:
        assert self.rule.matches(_notation("xn--", "com"), self.contract) is False

    def test_rejects_ace_label_with_undecodable_payload(self) -> None:
        assert self.rule.matches(_notation("xn--!!!!", "com"), self.contract) is False

    def test_rejects_underscore_std3(self) -> None:
        assert self.rule.matches(_notation("_dmarc", "com"), self.contract) is False

    def test_rejects_disallowed_char(self) -> None:
        # RLO is disallowed in the shipped table; ZWSP/ZWNJ handling lives
        # in the map + ContextJ tests, not here — ignored chars never
        # reach statuses.
        assert (
            self.rule.matches(_notation("exam\u202eple", "com"), self.contract) is False
        )

    def test_deviation_sharp_s_accepted(self) -> None:
        assert self.rule.matches(_notation("straße", "de"), self.contract) is True

    def test_rejects_leading_hyphen(self) -> None:
        # RFC 1123 §2.1 relaxes the first character for digits only.
        assert self.rule.matches(_notation("-cdn", "com"), self.contract) is False

    def test_rejects_trailing_hyphen(self) -> None:
        assert self.rule.matches(_notation("example-", "com"), self.contract) is False

    def test_rejects_double_hyphen_at_3rd_4th_position(self) -> None:
        assert self.rule.matches(_notation("ex--ample", "com"), self.contract) is False

    def test_allows_double_hyphen_outside_3rd_4th(self) -> None:
        assert self.rule.matches(_notation("exam--ple", "com"), self.contract) is True

    def test_ace_prefix_exempt_from_hyphen_3_4(self) -> None:
        assert (
            self.rule.matches(_notation("xn--mnchen-3ya", "de"), self.contract) is True
        )

    def test_public_predicate_uts46_ok(self) -> None:
        assert uts46_ok(_notation("example", "com")) is True
        assert uts46_ok(_notation("ex--ample", "com")) is False
        assert uts46_ok(_notation("_dmarc", "com")) is False

    def test_metadata(self) -> None:
        assert self.rule.name == "UTS46-statuses"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset(
            {"ascii_hostname", "idn_hostname"}
        )
        assert self.rule.requires_features == frozenset()

    def test_provenance_attributes(self) -> None:
        assert self.rule.provenance.authority == "Unicode"
        assert self.rule.provenance.specification_name == "UTS #46"
        assert self.rule.provenance.kind == "specification"
        assert (
            self.rule.provenance.reference_url
            == "https://www.unicode.org/reports/tr46/"
        )
        assert self.rule.provenance.version == "18.0.0"
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.publication_year == 2026
        assert self.rule.citation == "UTS #46 processing with STD3 rules"
