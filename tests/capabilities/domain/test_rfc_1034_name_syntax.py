"""Tests for Rfc1034NameSyntax — RFC 1034 §3.1 name syntax."""

import pytest

from paxman.capabilities.Domain.contract import DomainContract
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.rfc_1034_name_syntax import (
    Rfc1034NameSyntax,
    name_syntax_ok,
)
from paxman.core.domain import RuleStrategy

pytestmark = pytest.mark.capability


def _notation(*labels: str, raw: str = "example.com") -> DomainNotation:
    return DomainNotation(raw=raw, labels=tuple(labels), tld=labels[-1])


class TestRfc1034NameSyntax:
    """At least two labels, no empty label (single-label scope deferred)."""

    def setup_method(self) -> None:
        self.rule = Rfc1034NameSyntax()
        self.contract = DomainContract()

    def test_matches_two_labels(self) -> None:
        assert self.rule.matches(_notation("example", "com"), self.contract) is True

    def test_rejects_single_label(self) -> None:
        # D6 scope note: single-label acceptance arrives only as a
        # requires_features-gated rule (RFC 1034 §3.1).
        assert self.rule.matches(_notation("localhost"), self.contract) is False
        assert self.rule.matches(_notation("com"), self.contract) is False

    def test_rejects_empty_label(self) -> None:
        assert (
            self.rule.matches(_notation("ex", "", "ample", "com"), self.contract)
            is False
        )
        # One trailing empty survives the single-strip (X7 "example.com..").
        assert (
            self.rule.matches(_notation("example", "com", ""), self.contract) is False
        )

    def test_public_predicate_name_syntax_ok(self) -> None:
        assert name_syntax_ok(_notation("example", "com")) is True
        assert name_syntax_ok(_notation("localhost")) is False
        assert name_syntax_ok(_notation("ex", "", "ample", "com")) is False

    def test_metadata(self) -> None:
        assert self.rule.name == "Section-3.1-name-syntax"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset(
            {"ascii_hostname", "idn_hostname"}
        )
        assert self.rule.requires_features == frozenset()

    def test_provenance_attributes(self) -> None:
        assert self.rule.provenance.authority == "IETF"
        assert self.rule.provenance.specification_name == "RFC 1034"
        assert self.rule.provenance.kind == "specification"
        assert (
            self.rule.provenance.reference_url
            == "https://www.rfc-editor.org/rfc/rfc1034"
        )
        assert self.rule.provenance.version == "1987"
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.publication_year == 1987
        assert self.rule.citation == (
            "RFC 1034 §3.1 name syntax; ≥2-label minimum is Domain policy"
        )

    def test_normalize_finalizes_labels(self) -> None:
        assert (
            self.rule.normalize(_notation("münchen", "de"), self.contract)
            == "xn--mnchen-3ya.de"
        )
