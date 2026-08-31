"""BoundaryGuard unit tests — 10 distinct lookarounds, one family."""

from __future__ import annotations

import re

import pytest

from paxman.core.grammar.boundary import BoundaryGuard

pytestmark = pytest.mark.unit


def test_word_sign_guard_blocks_inside_token() -> None:
    g = BoundaryGuard.word_sign()  # (?<![\w\-+\u2212]) / (?![\w\-+\u2212])
    # "€" inside "x€" must NOT match (preceding char is a word char).
    assert g.wrap("€").search("x€") is None
    # Leading/trailing whitespace is a valid boundary.
    assert g.wrap("€").search(" €") is not None
    assert g.wrap("€").search("€") is not None


def test_siunit_degree_guard_differs_from_word_sign() -> None:
    # SIUnit includes ° in the lookaround; Currency does not.
    g_word = BoundaryGuard.word_sign()
    g_degree = BoundaryGuard.degree_word_sign()
    assert g_word.lookbehind != g_degree.lookbehind
    assert "°" in g_degree.lookbehind


def test_scheme_char_guard_for_url() -> None:
    g = BoundaryGuard.scheme_char()  # (?<![A-Za-z0-9+.\-])
    assert g.wrap("https:").search("xhttps:") is None
    assert g.wrap("https:").search(" https:") is not None


def test_e164_guard() -> None:
    g = BoundaryGuard.e164()  # (?<![\w:.])
    # The caller (LexiconAlternation) re.escape's tokens before wrapping.
    alt = re.escape("+1")
    assert g.wrap(alt).search("a+1") is None
    assert g.wrap(alt).search(" +1") is not None
    assert g.wrap(alt).search("tel:+1") is None


def test_digit_guard_for_date() -> None:
    g = BoundaryGuard.digit()  # (?<!\d) / (?!\d)
    assert g.wrap("2026-01-15").search("12026-01-15") is None
    assert g.wrap("2026-01-15").search("2026-01-15") is not None


def test_word_only_guard_for_country() -> None:
    g = BoundaryGuard.word_only()  # (?<!\w) / (?!\w)  (equiv. \b)
    assert g.wrap("US").search("XUS") is None
    assert g.wrap("US").search(" US ") is not None


def test_phone_national_guard_four_chain() -> None:
    g = BoundaryGuard.phone_national()
    # A bare national number at string start matches.
    assert g.wrap("555").search("555") is not None
    # A national number preceded by "+1 " is blocked by the 4-lookbehind chain.
    assert g.wrap("555").search("+1 555") is None
    # A national number preceded by a word boundary (space) matches.
    assert g.wrap("555").search("call 555") is not None


def test_ipv6_token_guard() -> None:
    g = BoundaryGuard.ipv6_token()
    # At string start matches.
    assert g.wrap("2001:db8").search("2001:db8") is not None
    # Preceded by a non-delimiter char is blocked.
    assert g.wrap("2001:db8").search("x2001:db8") is None
    # Preceded by a delimiter (space) and followed by a delimiter (comma) matches.
    assert g.wrap("2001:db8").search(" 2001:db8,") is not None


def test_mac_midrun_guard_blocks_tail_of_longer_run() -> None:
    import re

    from paxman.core.grammar.boundary import BoundaryGuard

    guard = BoundaryGuard.mac_midrun()
    assert guard.lookbehind == r"(?<!\w)(?<![0-9A-Fa-f][-.:])"
    assert guard.lookahead == r"(?!\w)"
    pattern = re.compile(
        guard.lookbehind + r"(?P<c>(?:[0-9A-F]{2}:){5}[0-9A-F]{2})" + guard.lookahead
    )
    # head claim of a truncated 7-octet run blocked by the truncation guard
    # is a grammar concern; here: the tail of a longer run must not start
    # after hex+separator. At guard level the head remains, but the tail
    # "1A:2B:3C:4D:5E:66" must never appear as a separate claim.
    matches = pattern.findall("00:1A:2B:3C:4D:5E:66")
    assert matches == ["00:1A:2B:3C:4D:5E"]
    assert "1A:2B:3C:4D:5E:66" not in matches
    assert pattern.findall("00:1A:2B:3C:4D:5E") == ["00:1A:2B:3C:4D:5E"]
