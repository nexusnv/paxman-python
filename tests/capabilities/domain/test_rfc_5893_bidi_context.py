"""Tests for Rfc5893BidiContext — RFC 5893 §2 Bidi rule + ContextJ."""

import pytest

from paxman.capabilities.Domain.contract import DomainContract
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.capabilities.Domain.rules.rfc_5893_bidi_context import (
    Rfc5893BidiContext,
    bidi_ok,
)
from paxman.core.domain import RuleStrategy

pytestmark = pytest.mark.capability


def _notation(*labels: str, raw: str = "example.com") -> DomainNotation:
    return DomainNotation(raw=raw, labels=tuple(labels), tld=labels[-1])


class TestRfc5893BidiContext:
    """Six §2 conditions with a non-Bidi fast path, plus ContextJ."""

    def setup_method(self) -> None:
        self.rule = Rfc5893BidiContext()
        self.contract = DomainContract()

    def test_non_bidi_fast_path_true(self) -> None:
        # RFC 5893 §1.1 places no requirements on non-Bidi names.
        assert self.rule.matches(_notation("example", "com"), self.contract) is True
        assert (
            self.rule.matches(_notation("xn--mnchen-3ya", "de"), self.contract) is True
        )

    def test_pure_rtl_label_and_ascii_coexist(self) -> None:
        assert self.rule.matches(_notation("مثال", "com"), self.contract) is True

    def test_rtl_label_rejects_ltr_char_inside(self) -> None:
        assert self.rule.matches(_notation("مa", "com"), self.contract) is False

    def test_ltr_typed_label_rejects_rtl_char(self) -> None:
        assert self.rule.matches(_notation("aم", "com"), self.contract) is False

    def test_rtl_label_leading_digit_rejected(self) -> None:
        assert self.rule.matches(_notation("2مثال", "com"), self.contract) is False

    def test_rtl_label_trailing_european_digit_accepted(self) -> None:
        assert self.rule.matches(_notation("مثال2", "com"), self.contract) is True

    def test_rtl_label_rejects_an_en_mix(self) -> None:
        assert self.rule.matches(_notation("م٠2", "com"), self.contract) is False

    def test_rtl_label_trailing_nsm_accepted(self) -> None:
        # Conditions 3/6 allow zero or more trailing NSM (U+0300 here).
        assert self.rule.matches(_notation("مثال\u0300", "com"), self.contract) is True

    def test_bidi_skips_empty_label(self) -> None:
        # Emptiness is rfc_1034's jurisdiction; bidi judges the rest.
        assert bidi_ok(_notation("مثال", "", "com")) is True

    def test_rtl_label_rejects_bad_end(self) -> None:
        # Condition 3: RTL labels must end R/AL/EN/AN (+ NSM) — "!" is ON.
        assert self.rule.matches(_notation("مثال!", "com"), self.contract) is False

    def test_ltr_label_rejects_bad_end(self) -> None:
        # Condition 6: LTR labels must end L/EN — "-" is ES (allowed inside).
        # The name must be Bidi (an RTL label present) for conditions to apply.
        assert self.rule.matches(_notation("ab-", "مثال"), self.contract) is False

    def test_contextj_join_control_rejected(self) -> None:
        # ZWNJ is deviation (kept by the non-transitional map); the six
        # conditions would pass (BN allowed) — the explicit ContextJ check
        # rejects it. No joining tables shipped: conservative reject.
        assert self.rule.matches(_notation("م‌ث", "com"), self.contract) is False

    def test_public_predicate_bidi_ok(self) -> None:
        assert bidi_ok(_notation("example", "com")) is True
        assert bidi_ok(_notation("مثال", "com")) is True
        assert bidi_ok(_notation("2مثال", "com")) is False

    def test_metadata(self) -> None:
        assert self.rule.name == "Section-2-bidi-context"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset(
            {"ascii_hostname", "idn_hostname"}
        )
        assert self.rule.requires_features == frozenset()

    def test_provenance_attributes(self) -> None:
        assert self.rule.provenance.authority == "IETF"
        assert self.rule.provenance.specification_name == "RFC 5893"
        assert self.rule.provenance.kind == "specification"
        assert (
            self.rule.provenance.reference_url
            == "https://www.rfc-editor.org/rfc/rfc5893"
        )
        assert self.rule.provenance.version == "2010"
        assert self.rule.provenance.lifecycle == "active"
        assert self.rule.provenance.publication_year == 2010
        assert self.rule.citation == "RFC 5893 §2 Bidi rule"
