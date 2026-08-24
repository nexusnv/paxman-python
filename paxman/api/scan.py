"""Batch scan API — one substrate pass, per-capability Mention records."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.core.capability_contract import CapabilityContract
from paxman.core.domain import ScanResult
from paxman.engine.orchestrator import run_scan


def scan(text: str, contracts: Sequence[CapabilityContract]) -> ScanResult:
    """Scan text for all capability mentions in one substrate pass.

    The substrate (ScanContext) is built once and reused for every
    contract/grammar in the batch, so F1×F6 (single_value + invisible
    embedded values) becomes an API guarantee instead of a caller
    obligation. Mentions are maximal clusters of recognitions under the
    existing total order + containment policy.

    Args:
        text: Input text to scan.
        contracts: Capability contracts to scan for (one per capability).

    Returns:
        ScanResult with per-capability Mention tuples.

    Raises:
        TypeError: If text is not str.
        CapabilityError: If a contract names an unregistered capability.
    """
    if not isinstance(text, str):
        raise TypeError(f"scan() expects str for text, got {type(text).__name__}")
    if not isinstance(contracts, Sequence):
        raise TypeError(
            "scan() expects Sequence[CapabilityContract], "
            f"got {type(contracts).__name__}"
        )
    return run_scan(text, contracts)


__all__ = ["scan"]
