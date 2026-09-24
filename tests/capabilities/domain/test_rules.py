"""Tests for the RFC 1034 name-syntax rule (scaffold)."""

import pytest

from paxman.capabilities.Domain.rules.rfc_1034_name_syntax import Rfc1034NameSyntax
from paxman.core.domain import RuleStrategy


@pytest.mark.capability
class TestRfc1034NameSyntax:
    """Rule: Section 1-overview (scaffold)."""

    def setup_method(self) -> None:
        self.rule = Rfc1034NameSyntax()

    def test_rule_metadata(self) -> None:
        assert self.rule.name == "Section 1-overview"
        assert self.rule.strategy is RuleStrategy.REGEX
        assert self.rule.target_semantics == frozenset({"ascii_hostname"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 1987

    def test_matches(self) -> None:
        from paxman.capabilities.Domain.contract import DomainContract
        from paxman.capabilities.Domain.notation import DomainNotation

        contract = DomainContract()
        notation = DomainNotation(raw="example", labels=("example",), tld="example")
        assert self.rule.matches(notation, contract) is True


@pytest.mark.capability
class TestIdnaProcessing:
    """Shared UTS #46 map-step processing (Task 3)."""

    def test_status_of_valid_ascii(self) -> None:
        from paxman.capabilities.Domain.idna_processing import status_of

        assert status_of(ord("a")) == "valid"

    def test_status_of_std3_underscore(self) -> None:
        from paxman.capabilities.Domain.idna_processing import status_of

        assert status_of(0x5F) == "disallowed_STD3_valid"

    def test_status_of_disallowed_replacement_char(self) -> None:
        from paxman.capabilities.Domain.idna_processing import status_of

        assert status_of(0xFFFD) == "disallowed"

    def test_status_of_disallowed_directional_override(self) -> None:
        from paxman.capabilities.Domain.idna_processing import status_of

        assert status_of(0x202E) == "disallowed"

    def test_status_of_deviation_sharp_s(self) -> None:
        from paxman.capabilities.Domain.idna_processing import status_of

        assert status_of(0x00DF) == "deviation"

    def test_status_of_ignored_zero_width_space(self) -> None:
        from paxman.capabilities.Domain.idna_processing import status_of

        assert status_of(0x200B) == "ignored"

    def test_map_domain_case_and_trailing_dot(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("EXAMPLE.COM.") == ("example", "com")

    def test_map_domain_fullwidth_and_dot_variants(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("ｅxample。ｊｐ") == ("example", "jp")

    def test_map_domain_nfc_convergence(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert (
            map_domain("mu\u0308nchen.de")
            == map_domain("münchen.de")
            == (
                "münchen",
                "de",
            )
        )

    def test_map_domain_removes_ignored_soft_hyphen(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("exa\u00admple.com") == ("example", "com")

    def test_map_domain_removes_ignored_zero_width_space(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("example\u200b.com") == ("example", "com")

    def test_map_domain_keeps_disallowed_for_status_rejection(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        # RLO survives the map step verbatim, to be rejected by the statuses rule.
        assert map_domain("exam\u202eple.com")[0] == "exam\u202eple"

    def test_map_domain_deviation_kept_verbatim(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("straße.de") == ("straße", "de")

    def test_map_domain_expands_multi_target_mapping(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("\ufb00oo.com") == ("ffoo", "com")

    def test_ace_encode_ascii_passthrough(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_encode

        assert ace_encode("com") == "com"

    def test_ace_encode_punycode(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_encode

        assert ace_encode("münchen") == "xn--mnchen-3ya"
        assert ace_encode("straße") == "xn--strae-oqa"

    def test_ace_decode_ok_round_trip(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--mnchen-3ya") is True

    def test_ace_decode_ok_rejects_empty_payload(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--") is False

    def test_ace_decode_ok_rejects_non_ascii_payload(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--münchen") is False

    def test_ace_decode_ok_rejects_reencode_mismatch(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        # Uppercase extension digits decode (case-insensitively) to münchen,
        # which re-encodes lowercase — payload and re-encoding differ.
        assert ace_decode_ok("xn--mnchen-3YA") is False

    def test_ace_decode_never_raises(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode

        assert ace_decode("xn--") == "xn--"

    def test_finalize_joins_ace_labels(self) -> None:
        from paxman.capabilities.Domain.idna_processing import finalize

        assert finalize(("münchen", "de")) == "xn--mnchen-3ya.de"
