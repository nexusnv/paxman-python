import pytest

import paxman
from paxman.capabilities.IBAN.capability import IBANCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test (shipped ISSN pattern)."""
    reset_registry()
    yield
    reset_registry()


def _register_iban() -> None:
    register_capability(IBANCapability())


def test_success_electronic_and_paper_same_canonical():
    _register_iban()
    contract = IBANCapability.create_contract()
    for txt in [
        "DE89370400440532013000",
        "DE89 3704 0044 0532 0130 00",
        "de89370400440532013000",
        "IBAN: DE89 3704 0044 0532 0130 00",
    ]:
        r = paxman.canonicalize(txt, contract)
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == "DE89370400440532013000"
        assert r.candidates[0].provenance[0].specification_name == "ISO 13616-1:2020"
        assert r.span is not None


def test_paper_output_format():
    _register_iban()
    contract = IBANCapability.create_contract(output_format="paper")
    r = paxman.canonicalize("DE89370400440532013000", contract)
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "DE89 3704 0044 0532 0130 00"


def test_invalid_mod97():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert (
        paxman.canonicalize("DE89370400440532013001", contract).status
        == Resolution.INVALID
    )


def test_tail_glue_absorbed_is_invalid():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert (
        paxman.canonicalize("DE89370400440532013000Y", contract).status
        == Resolution.INVALID
    )


def test_missing_short_and_bban_only():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert paxman.canonicalize("AB12", contract).status == Resolution.MISSING
    assert (
        paxman.canonicalize("370400440532013000", contract).status == Resolution.MISSING
    )


def test_two_distinct_ibans_raise_multiple_mentions():
    _register_iban()
    contract = IBANCapability.create_contract()
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize(
            "DE89 3704 0044 0532 0130 00 / GB29 NWBK 6016 1331 9268 19", contract
        )


def test_span_word_guard():
    _register_iban()
    contract = IBANCapability.create_contract()
    assert (
        paxman.canonicalize("XDE89370400440532013000", contract).status
        == Resolution.MISSING
    )


def test_longest_vectors():
    _register_iban()
    contract = IBANCapability.create_contract()
    for compact in [
        "LC55HEMM000100010012001200023015",
        "NI79BAMC00000000000003123123",
    ]:
        r = paxman.canonicalize(compact, contract)
        assert r.status == Resolution.SUCCESS, compact


def test_year_filter_excludes_rule():
    _register_iban()
    contract = IBANCapability.create_contract(year=2019)
    r = paxman.canonicalize("DE89370400440532013000", contract)
    assert r.status == Resolution.INVALID


def test_trailing_word_not_part_of_mention():
    # Fix pin (34b569a): a trailing English word must not be absorbed into the
    # mention — SUCCESS with the span ending at the IBAN's final "00".
    _register_iban()
    contract = IBANCapability.create_contract()
    r = paxman.canonicalize("Pay to DE89 3704 0044 0532 0130 00 now", contract)
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "DE89370400440532013000"
    assert r.span == (7, 34)


def test_word_separator_two_mentions_raise():
    # Fix pin (34b569a): a word-separated second mention is a distinct
    # mention -> MultipleMentionsError (the uniform-loop pattern would have
    # absorbed " and GB29..." into one mention and reported INVALID instead).
    _register_iban()
    contract = IBANCapability.create_contract()
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize(
            "DE89 3704 0044 0532 0130 00 and GB29 NWBK 6016 1331 9268 19",
            contract,
        )


def test_truncated_paper_is_invalid():
    # Pinned: truncated 2-group paper is recognized by the grammar (min = 2
    # groups) but fails the rule's 15-34 length -> INVALID, never MISSING
    # (grammar test test_truncated_two_group_paper_recognized pins the match).
    _register_iban()
    contract = IBANCapability.create_contract()
    assert paxman.canonicalize("DE89 3704 0044", contract).status == Resolution.INVALID
