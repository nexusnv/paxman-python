"""Tests for IanaRootZoneMembership — the ADR-0012 LOOKUP chokepoint."""

import pytest

from paxman.capabilities.Domain.contract import DomainContract
from paxman.capabilities.Domain.idna_processing import ace_encode
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.data.root_zone_tlds import ROOT_ZONE_TLDS
from paxman.capabilities.Domain.rules.iana_root_zone_membership import (
    IanaRootZoneMembership,
)
from paxman.capabilities.Domain.rules.rfc_1034_name_syntax import name_syntax_ok
from paxman.capabilities.Domain.rules.rfc_1035_label_length import (
    label_lengths_ok,
)
from paxman.capabilities.Domain.rules.rfc_5893_bidi_context import bidi_ok
from paxman.capabilities.Domain.rules.unicode_uts46_statuses import uts46_ok
from paxman.core.domain import RuleStrategy

pytestmark = pytest.mark.capability


def _notation(*labels: str, raw: str = "example.com") -> DomainNotation:
    return DomainNotation(raw=raw, labels=tuple(labels), tld=labels[-1])


class TestIanaRootZoneMembership:
    """One chokepoint: four public predicates AND encoded-TLD membership."""

    def setup_method(self) -> None:
        self.rule = IanaRootZoneMembership()
        self.contract = DomainContract()

    def test_matches_known_tld(self) -> None:
        assert self.rule.matches(_notation("example", "com"), self.contract) is True

    def test_matches_known_unicode_tld(self) -> None:
        assert self.rule.matches(_notation("münchen", "de"), self.contract) is True

    def test_rejects_unknown_tld(self) -> None:
        assert (
            self.rule.matches(_notation("foo", "unknowntld-xyz"), self.contract)
            is False
        )

    def test_rejects_numeric_tld(self) -> None:
        assert (
            self.rule.matches(_notation("192", "168", "0", "1"), self.contract) is False
        )

    def test_rejects_single_label(self) -> None:
        assert self.rule.matches(_notation("localhost"), self.contract) is False

    def test_rejects_when_any_predicate_fails(self) -> None:
        assert (
            self.rule.matches(_notation("ex", "", "ample", "com"), self.contract)
            is False
        )
        assert self.rule.matches(_notation("a" * 64, "com"), self.contract) is False
        assert self.rule.matches(_notation("_dmarc", "com"), self.contract) is False
        assert self.rule.matches(_notation("م‌ث", "com"), self.contract) is False

    def test_chokepoint_ands_public_predicates(self) -> None:
        cases = [
            ("example", "com"),
            ("münchen", "de"),
            ("example", "unknowntld-xyz"),
            ("localhost",),
            ("ex", "", "ample", "com"),
            ("a" * 64, "com"),
            ("_dmarc", "com"),
            ("ex--ample", "com"),
            ("2مثال", "com"),
            ("م‌ث", "com"),
        ]
        for labels in cases:
            notation = _notation(*labels)
            expected = (
                name_syntax_ok(notation)
                and label_lengths_ok(notation)
                and uts46_ok(notation)
                and bidi_ok(notation)
                and ace_encode(notation.tld) in ROOT_ZONE_TLDS
            )
            assert self.rule.matches(notation, self.contract) == expected

    def test_metadata(self) -> None:
        assert self.rule.name == "root-zone-membership"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset(
            {"ascii_hostname", "idn_hostname"}
        )
        assert self.rule.requires_features == frozenset()

    def test_provenance_attributes(self) -> None:
        assert self.rule.provenance.authority == "IANA"
        assert self.rule.provenance.specification_name == "tlds-alpha-by-domain.txt"
        assert self.rule.provenance.kind == "registry"
        assert (
            self.rule.provenance.reference_url
            == "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
        )
        assert self.rule.provenance.version == "IANA tlds-alpha v2026092300"
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.publication_year == 2026
        assert self.rule.citation == "IANA Root Zone Database membership"
