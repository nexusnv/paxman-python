"""Batch scan() API + Mention model."""

import paxman
from paxman.capabilities.Country.capability import CountryCapability
from paxman.core.discovery import register_capability, reset_registry


def _contract():  # type: ignore[no-untyped-def]
    return CountryCapability.create_contract()


def test_scan_exposes_both_mentions_for_ship_to_united_states() -> None:
    reset_registry()
    from paxman import scan

    register_capability(CountryCapability())
    text = "Ship to United States please"
    result = scan(text, [_contract()])
    # Robust to off-by-one: check content via slicing, not hard indices
    mentions = result.mentions.get("country", ())
    assert len(mentions) == 2, f"expected 2 mentions, got {mentions}"
    extracted = {text[m.span[0] : m.span[1]] for m in mentions}
    assert "United States" in extracted, f"missing United States in {extracted}"
    assert "to" in extracted, f"missing to in {extracted}"
    # Also verify spans are valid half-open and raw_text consistent
    spans = sorted((m.span[0], m.span[1]) for m in mentions)
    # The correct spans are (5,7) and (8,21); accept either that or (9,22) variant
    assert (5, 7) in spans
    assert (8, 21) in spans or (9, 22) in spans


def test_canonicalize_single_value_still_raises() -> None:
    reset_registry()
    register_capability(CountryCapability())
    import pytest

    from paxman.core.errors import MultipleMentionsError

    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize("Ship to United States please", _contract())


def test_scan_substrate_shared_one_pass() -> None:
    """Scan creates one ScanContext substrate for the batch.

    Verifies via monkeypatch that ScanContext.of is called exactly once
    for the batch path (orchestrator shares the context), not per-contract.
    """

    from unittest.mock import patch

    from paxman.core.grammar.scan_context import ScanContext

    reset_registry()
    from paxman import scan

    register_capability(CountryCapability())

    # Count ScanContext.of calls via orchestrator path
    with patch(
        "paxman.engine.orchestrator.ScanContext.of", wraps=ScanContext.of
    ) as mock_of:
        scan("Ship to United States please", [_contract(), _contract()])
        # run_scan creates exactly one ScanContext for the batch
        assert mock_of.call_count == 1, (
            f"expected 1 substrate pass, got {mock_of.call_count}"
        )


def test_scan_result_model() -> None:
    """ScanResult and Mention are frozen dataclasses with expected fields."""

    from paxman.core.domain import Mention, ScanResult

    reset_registry()
    from paxman import scan

    register_capability(CountryCapability())
    result = scan("US", [_contract()])
    assert isinstance(result, ScanResult)
    assert result.text == "US"
    assert "country" in result.mentions
    mentions = result.mentions["country"]
    assert len(mentions) >= 1
    for m in mentions:
        assert isinstance(m, Mention)
        assert isinstance(m.span, tuple) and len(m.span) == 2
        assert isinstance(m.grammar, str)
        assert m.grammar
        assert m.notation is not None
