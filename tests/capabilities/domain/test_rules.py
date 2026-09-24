"""Tests for shared Domain rule processing (Task 3: idna_processing)."""

import pytest


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

    def test_map_domain_decodes_well_formed_ace(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        # Well-formed ACE (non-ASCII, NFC/map-stable) arrives decoded so
        # every rule validates the U-label.
        assert map_domain("XN--MNCHEN-3YA.de") == ("münchen", "de")

    def test_map_domain_keeps_ascii_only_ace(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("xn--abc-.com") == ("xn--abc-", "com")

    def test_map_domain_keeps_non_nfc_ace(self) -> None:
        from paxman.capabilities.Domain.idna_processing import map_domain

        assert map_domain("xn--munchen-gie.de") == ("xn--munchen-gie", "de")

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

    def test_ace_decode_ok_non_ace_passthrough(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("example") is True

    def test_ace_decode_ok_rejects_empty_payload(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--") is False

    def test_ace_decode_ok_rejects_undecodable_payload(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--!!!!") is False

    def test_ace_decode_ok_rejects_empty_decode(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        # "-" decodes to "" — the empty-decode bypass guard.
        assert ace_decode_ok("xn---") is False

    def test_ace_decode_ok_rejects_non_ascii_payload(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--münchen") is False

    def test_ace_decode_ok_rejects_reencode_mismatch(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        # Uppercase extension digits decode (case-insensitively) to münchen,
        # which re-encodes lowercase — payload and re-encoding differ.
        assert ace_decode_ok("xn--mnchen-3YA") is False

    def test_ace_decode_ok_rejects_ascii_only_decode(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--abc-") is False

    def test_ace_decode_ok_rejects_non_nfc_decode(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        assert ace_decode_ok("xn--munchen-gie") is False

    def test_ace_decode_ok_rejects_map_unstable_decode(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode_ok

        # Uppercase basic chars survive decoding ("MüNCHEN") but remap.
        assert ace_decode_ok("xn--MNCHEN-3YA") is False

    def test_ace_decode_never_raises(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode

        assert ace_decode("xn--") == "xn--"

    def test_ace_decode_non_ace_passthrough(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode

        assert ace_decode("example") == "example"

    def test_ace_decode_failure_returns_label(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode

        assert ace_decode("xn--!!!!") == "xn--!!!!"

    def test_ace_decode_empty_decode_returns_label(self) -> None:
        from paxman.capabilities.Domain.idna_processing import ace_decode

        assert ace_decode("xn---") == "xn---"

    def test_finalize_joins_ace_labels(self) -> None:
        from paxman.capabilities.Domain.idna_processing import finalize

        assert finalize(("münchen", "de")) == "xn--mnchen-3ya.de"
