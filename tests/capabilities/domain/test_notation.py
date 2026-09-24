"""Tests for DomainNotation — the intermediate token for hostname mentions."""

import dataclasses

import pytest

from paxman.capabilities.Domain.notation import DomainNotation


@pytest.mark.capability
class TestDomainNotation:
    """DomainNotation shape: span text plus mapped labels."""

    def test_notation_is_frozen_with_slots(self) -> None:
        n = DomainNotation(raw="münchen.DE.", labels=("münchen", "de"), tld="de")
        assert DomainNotation.__slots__  # truthy slots
        with pytest.raises(dataclasses.FrozenInstanceError):
            n.raw = "other"  # type: ignore[misc]

    def test_notation_fields_raw_labels_tld(self) -> None:
        n = DomainNotation(raw="münchen.DE.", labels=("münchen", "de"), tld="de")
        assert n.raw == "münchen.DE."
        assert n.labels == ("münchen", "de")
        assert n.tld == "de"

    def test_notation_has_no_canonical_field(self) -> None:
        # The canonical value is built by finalize() inside each normalize()
        # (encode-in-resolution) — the notation carries no canonical field.
        assert "canonical" not in DomainNotation.__dataclass_fields__

    def test_notation_raw_preserves_input_span_text(self) -> None:
        n = DomainNotation(raw="EXAMPLE.COM.", labels=("example", "com"), tld="com")
        assert n.raw == "EXAMPLE.COM."
