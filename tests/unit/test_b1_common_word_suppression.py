"""B1 RED — common-word suppression off vs on (ADR-0009 §16 / R7).

Fails before B1 lands, passes after:
- CapabilityContract gains suppress_common_words bool=False
  (frozen no-slots, default off)
- Each capability's create_contract propagates the flag
- COMMON_WORDS derived intersection lowercased, USD not suppressed
- Engine loop skips suppressible short-code hits when flag on
"""

from __future__ import annotations

import paxman
from paxman.api.canonicalize import canonicalize
from paxman.api.scan import scan
from paxman.capabilities import Country, Currency
from paxman.core.discovery import reset_registry
from paxman.core.domain import Resolution

TEXT = "Ship to the United States of America, total 45.50 USD, weight 3.5 kg"


def _contract_country(suppress: bool):
    return Country.create_contract(suppress_common_words=suppress)


def _contract_currency(suppress: bool):
    return Currency.create_contract(suppress_common_words=suppress)


def test_common_words_table_invariants() -> None:
    from paxman.core.grammar.data.common_words import COMMON_WORDS

    # frozen size guard — Google1000 ∩ (ISO3166 α2/α3 + ISO4217 + ISO639)
    assert len(COMMON_WORDS) == 67
    assert "USD" not in COMMON_WORDS
    assert "usd" not in COMMON_WORDS
    # spot checks — curated via Google1000 ∩ code sets, USD never suppressed
    assert "to" in COMMON_WORDS
    assert "and" in COMMON_WORDS
    assert "is" in COMMON_WORDS
    assert "all" in COMMON_WORDS
    # not in intersection (shape-only noise, not valid-code collision)
    assert "the" not in COMMON_WORDS
    assert "of" not in COMMON_WORDS


def test_capability_contract_default_off() -> None:
    c = Country.create_contract()
    assert hasattr(c, "suppress_common_words")
    assert c.suppress_common_words is False
    c2 = Country.create_contract(suppress_common_words=True)
    assert c2.suppress_common_words is True
    # byte-identical when off (default)
    assert c.suppress_common_words is False


def test_scan_off_snapshot_locked() -> None:
    reset_registry()
    paxman.register_all_shipped()
    contract = _contract_country(False)
    result = scan(TEXT, [contract])
    mentions = result.mentions["country"]
    # 9 clustered mentions off — locked snapshot
    assert len(mentions) == 9
    spans = {m.span for m in mentions}
    assert (5, 7) in spans  # to -> Tonga
    assert (8, 11) in spans  # the
    assert (66, 68) in spans  # kg


def test_scan_on_suppresses_common_words() -> None:
    reset_registry()
    paxman.register_all_shipped()
    contract = _contract_country(True)
    result = scan(TEXT, [contract])
    mentions = result.mentions["country"]
    name_mentions = [m for m in mentions if m.grammar == "name_recognition"]
    assert len(name_mentions) == 1
    assert name_mentions[0].span == (12, 36)
    assert name_mentions[0].grammar == "name_recognition"
    spans = {m.span for m in mentions}
    assert (5, 7) not in spans  # to is common word -> suppressed
    # the / kg are not in COMMON_WORDS (not valid-code collisions) so they remain
    assert (8, 11) in spans  # the not suppressed
    assert (66, 68) in spans  # kg not suppressed (kg not in Google1000)
    # total noise reduced: off 9 -> on 8 (only to removed)
    assert len(mentions) == 8


def test_scan_on_usd_remains_for_currency() -> None:
    reset_registry()
    paxman.register_all_shipped()
    contract = Currency.create_contract(suppress_common_words=True)
    result = scan(TEXT, [contract])
    mentions = result.mentions["currency"]
    spans = {m.span for m in mentions}
    assert (50, 53) in spans
    # the is not in COMMON_WORDS, so it remains even with suppression
    assert (8, 11) in spans
    # currency 'all' etc would be suppressed if present, but not in this text
    assert len(mentions) == 2


def test_canonicalize_to_off_vs_on() -> None:
    reset_registry()
    paxman.register_all_shipped()
    off = canonicalize("to", _contract_country(False))
    assert off.status == Resolution.SUCCESS
    assert off.canonicalized_value == "TO"

    reset_registry()
    paxman.register_all_shipped()
    on = canonicalize("to", _contract_country(True))
    assert on.status == Resolution.MISSING
    assert on.canonicalized_value is None


def test_canonicalize_usd_not_suppressed() -> None:
    reset_registry()
    paxman.register_all_shipped()
    off = canonicalize("USD", Currency.create_contract(suppress_common_words=False))
    assert off.status == Resolution.SUCCESS
    assert off.canonicalized_value == "USD"
    reset_registry()
    paxman.register_all_shipped()
    on = canonicalize("USD", Currency.create_contract(suppress_common_words=True))
    assert on.status == Resolution.SUCCESS
    assert on.canonicalized_value == "USD"
