"""Tests for ISBNCapability wiring."""

import pytest

from paxman.capabilities.ISBN.capability import ISBNCapability
from paxman.capabilities.ISBN.notation import ISBNNotation

pytestmark = [pytest.mark.capability]


def test_capability_name() -> None:
    """ISBNCapability has the correct name."""
    assert ISBNCapability.name == "isbn"


def test_get_grammars() -> None:
    """get_grammars returns exactly 2 grammars with the correct names."""
    cap = ISBNCapability()
    grammars = cap.get_grammars()
    assert len(grammars) == 2
    assert {g.name for g in grammars} == {
        "isbn13_recognition",
        "isbn10_recognition",
    }


def test_get_rules() -> None:
    """get_rules returns exactly 4 rules in the correct order."""
    cap = ISBNCapability()
    rules = cap.get_rules()
    assert len(rules) == 4
    assert [r.name for r in rules] == [
        "Section 5.3-isbn13-check-digit",
        "Section 4.2-gs1-prefix",
        "Section 6-isbn10-check-digit",
        "Section 4-registrant-range",
    ]


def test_create_contract_defaults() -> None:
    """create_contract() with no args produces the correct defaults."""
    c = ISBNCapability.create_contract()
    assert c.include_isbn10 is True
    assert c.include_range_validation is False
    assert c.output_format == "isbn13"
    assert c.active_grammars == ["isbn13_recognition", "isbn10_recognition"]


def test_create_contract_feature_flags() -> None:
    """Feature flags gate grammars and rules correctly."""
    c = ISBNCapability.create_contract(
        include_isbn10=False, include_range_validation=True
    )
    assert c.include_isbn10 is False
    assert c.include_range_validation is True
    assert c.active_grammars == ["isbn13_recognition"]


def test_create_contract_output_format() -> None:
    """output_format can be set to an offered alternative."""
    c = ISBNCapability.create_contract(output_format="hyphenated")
    assert c.output_format == "hyphenated"


def test_format_value_identity() -> None:
    """Default isbn13 and None formats return the value unchanged."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="9780306406157")
    assert cap.format_value("9780306406157", "isbn13", notation) == "9780306406157"
    assert cap.format_value("9780306406157", None, notation) == "9780306406157"


def test_format_value_hyphenated() -> None:
    """Hyphenated format applies Range Message hyphens."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="9780110002224")
    assert (
        cap.format_value("9780110002224", "hyphenated", notation) == "978-0-11-000222-4"
    )


def test_format_value_hyphenated_unregistered() -> None:
    """Unregistered group passes through unchanged (no error)."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="9789990000000")
    assert cap.format_value("9789990000000", "hyphenated", notation) == "9789990000000"


def test_format_value_hyphenated_unknown_prefix() -> None:
    """Unknown prefix passes through unchanged (no error)."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="1234567890123")
    assert cap.format_value("1234567890123", "hyphenated", notation) == "1234567890123"


def test_format_value_hyphenated_too_short() -> None:
    """Too-short input passes through unchanged (no crash)."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="9780")
    assert cap.format_value("9780", "hyphenated", notation) == "9780"


def test_format_value_hyphenated_too_long() -> None:
    """Too-long input passes through unchanged (no truncation)."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="97801100022241")
    assert (
        cap.format_value("97801100022241", "hyphenated", notation) == "97801100022241"
    )


def test_format_value_hyphenated_979_allocated() -> None:
    """979 prefix with allocated group hyphenates (uses shared _find_length)."""
    cap = ISBNCapability()
    # 979-10 is allocated (prefix 979, group 10 → registrant length via 979-10 table)
    # Use a synthetic valid ISBN-13 under 979-10; check that hyphenation inserts hyphens
    # and does not pass through as bare digits.
    notation = ISBNNotation(shape="isbn13", digits="9791000000000")
    hyphenated = cap.format_value("9791000000000", "hyphenated", notation)
    assert hyphenated.count("-") >= 2
    assert hyphenated.startswith("979-10-")


def test_format_value_hyphenated_979_unallocated() -> None:
    """979-9 has no GROUP_RULES entry → hyphenation falls through."""
    cap = ISBNCapability()
    notation = ISBNNotation(shape="isbn13", digits="9799000000000")
    assert cap.format_value("9799000000000", "hyphenated", notation) == "9799000000000"
