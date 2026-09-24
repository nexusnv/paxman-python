"""Wild-variant corpus for the Domain capability (Task 10).

Every row of the golden-corpus W-, E-, and X-tables through canonicalize()
with inline literals only. Module-level autouse registry: reset, register
the Domain capability alone, reset.
"""

import pytest

from paxman.api import canonicalize
from paxman.capabilities import Domain
from paxman.capabilities.Domain.capability import DomainCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError

pytestmark = pytest.mark.capability


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    reset_registry()
    register_capability(DomainCapability())
    yield
    reset_registry()


SUCCESS = Resolution.SUCCESS
INVALID = Resolution.INVALID
MISSING = Resolution.MISSING

_CASES = [
    # W-table: wild inputs.
    ("EXAMPLE.COM", SUCCESS, "example.com"),
    ("münchen.DE", SUCCESS, "xn--mnchen-3ya.de"),
    ("münchen.de.", SUCCESS, "xn--mnchen-3ya.de"),
    ("XN--MNCHEN-3YA.de", SUCCESS, "xn--mnchen-3ya.de"),
    ("mu\u0308nchen.de", SUCCESS, "xn--mnchen-3ya.de"),
    ("ｅxample。ｊｐ", SUCCESS, "example.jp"),
    ("straße.de", SUCCESS, "xn--strae-oqa.de"),
    ("exam--ple.com", SUCCESS, "exam--ple.com"),
    ("ex--ample.com", INVALID, None),
    ("www.example.com", SUCCESS, "www.example.com"),
    ("foo.unknowntld-xyz", INVALID, None),
    ("ex..ample.com", INVALID, None),
    ("-cdn.example.com", INVALID, None),
    ("example\u200b.com", SUCCESS, "example.com"),
    ("user@example.com", MISSING, None),
    ("https://example.com:8080/", MISSING, None),
    ("*.example.com", MISSING, None),
    # E-table: edge inputs.
    ("example.com.", SUCCESS, "example.com"),
    ("EXAMPLE.COM", SUCCESS, "example.com"),
    ("münchen.de", SUCCESS, "xn--mnchen-3ya.de"),
    ("XN--MNCHEN-3YA.DE", SUCCESS, "xn--mnchen-3ya.de"),
    ("example。com", SUCCESS, "example.com"),
    ("xn--.com", INVALID, None),
    ("example.123", INVALID, None),
    ("a" * 64 + ".com", INVALID, None),
    ("a" * 63 + "." + "a" * 63 + "." + "a" * 63 + "." + "a" * 62, INVALID, None),
    ("-example.com", INVALID, None),
    ("example-.com", INVALID, None),
    ("localhost", INVALID, None),
    ("intranet", INVALID, None),
    ("user@example.com", MISSING, None),
    ("https://example.com/", MISSING, None),
    ("192.168.0.1", INVALID, None),
    ("[::1]", MISSING, None),
    ("*.example.com", MISSING, None),
    ("example\u200b.com", SUCCESS, "example.com"),
    ("ex..ample.com", INVALID, None),
    ("com", INVALID, None),
    ("straße.de", SUCCESS, "xn--strae-oqa.de"),
    # X-table: extras and shipped-table pins.
    ("visit example.com today", SUCCESS, "example.com"),
    ("  example.com  ", SUCCESS, "example.com"),
    ("STRASSE.DE", SUCCESS, "strasse.de"),
    ("a.com;a.com", SUCCESS, "a.com"),
    (".example.com", MISSING, None),
    ("example.com..", INVALID, None),
    ("exam\u202eple.com", INVALID, None),
    ("a\u200cb.com", INVALID, None),
]

_IDS = [
    "W1",
    "W2",
    "W3",
    "W4",
    "W5",
    "W6",
    "W7",
    "W8",
    "W8r",
    "W9",
    "W10",
    "W11",
    "W12",
    "W13",
    "W14",
    "W15",
    "W16",
    "E1",
    "E2",
    "E3",
    "E4",
    "E5",
    "E6",
    "E7",
    "E8",
    "E9",
    "E10a",
    "E10b",
    "E11a",
    "E11b",
    "E12",
    "E13",
    "E14a",
    "E14b",
    "E15",
    "E16",
    "E17",
    "E18a",
    "E18b",
    "X1",
    "X2",
    "X3",
    "X5",
    "X6",
    "X7",
    "X8",
    "X9",
]


@pytest.mark.parametrize(("raw", "status", "value"), _CASES, ids=_IDS)
def test_wild_corpus(raw: str, status: Resolution, value: str | None) -> None:
    result = canonicalize(raw, Domain.create_contract())
    assert result.status == status
    assert result.canonicalized_value == value


def test_multiple_distinct_mentions_raise() -> None:
    with pytest.raises(MultipleMentionsError):
        canonicalize("a.com;b.com", Domain.create_contract())


def test_duplicate_mentions_dedup() -> None:
    result = canonicalize("a.com;a.com", Domain.create_contract())
    assert result.status == Resolution.SUCCESS
    assert result.canonicalized_value == "a.com"
