"""Tests for Rfc1035LabelLength — RFC 1035 §2.3.4 size constraints."""

import pytest

from paxman.capabilities.Domain.contract import DomainContract
from paxman.capabilities.Domain.idna_processing import ace_encode
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.rfc_1035_label_length import (
    MAX_LABEL_OCTETS,
    MAX_NAME_CHARS,
    Rfc1035LabelLength,
    label_lengths_ok,
)
from paxman.core.domain import RuleStrategy

pytestmark = pytest.mark.capability


def _notation(*labels: str, raw: str = "example.com") -> DomainNotation:
    return DomainNotation(raw=raw, labels=tuple(labels), tld=labels[-1])


class TestRfc1035LabelLength:
    """63 octets per label post-encode, 253 chars per name."""

    def setup_method(self) -> None:
        self.rule = Rfc1035LabelLength()
        self.contract = DomainContract()

    def test_accepts_63_octet_label(self) -> None:
        assert self.rule.matches(_notation("a" * 63, "com"), self.contract) is True

    def test_rejects_64_octet_label(self) -> None:
        assert self.rule.matches(_notation("a" * 64, "com"), self.contract) is False

    def test_accepts_253_char_name(self) -> None:
        labels = ("a" * 63, "a" * 63, "a" * 63, "a" * 61)
        assert len(".".join(labels)) == 253
        assert self.rule.matches(_notation(*labels), self.contract) is True

    def test_rejects_254_char_name(self) -> None:
        labels = ("a" * 63, "a" * 63, "a" * 63, "a" * 62)
        assert len(".".join(labels)) == 254
        assert self.rule.matches(_notation(*labels), self.contract) is False

    def test_length_is_post_encode(self) -> None:
        # "mü" + 54 a's ACE-encodes to exactly 63 octets (passes); one more
        # a tips it to 64 (fails).
        ok_label = "mü" + "a" * 54
        assert len(ace_encode(ok_label)) == 63
        assert self.rule.matches(_notation(ok_label, "de"), self.contract) is True
        bad_label = "mü" + "a" * 55
        assert len(ace_encode(bad_label)) == 64
        assert self.rule.matches(_notation(bad_label, "de"), self.contract) is False

    def test_public_predicate_label_lengths_ok(self) -> None:
        assert label_lengths_ok(_notation("example", "com")) is True
        assert label_lengths_ok(_notation("a" * 64, "com")) is False

    def test_metadata(self) -> None:
        assert self.rule.name == "Section-2.3.4-label-length"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset(
            {"ascii_hostname", "idn_hostname"}
        )
        assert self.rule.requires_features == frozenset()
        assert MAX_LABEL_OCTETS == 63
        assert MAX_NAME_CHARS == 253

    def test_provenance_attributes(self) -> None:
        assert self.rule.provenance.authority == "IETF"
        assert self.rule.provenance.specification_name == "RFC 1035"
        assert self.rule.provenance.kind == "specification"
        assert (
            self.rule.provenance.reference_url
            == "https://www.rfc-editor.org/rfc/rfc1035"
        )
        assert self.rule.provenance.version == "1987"
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.publication_year == 1987
        assert self.rule.citation == "RFC 1035 §2.3.4 size constraints"
