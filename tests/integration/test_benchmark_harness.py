from __future__ import annotations

import json
from pathlib import Path

import pytest

from paxman.core.discovery import reset_registry

pytestmark = [pytest.mark.benchmark, pytest.mark.integration]


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def test_harness_runs_one_scenario() -> None:
    from benchmarks.harness import run_once

    result = run_once("email", "user@example.com", iterations=3)
    assert result["capability"] == "email"
    assert result["iterations"] == 3
    assert result["mean_ms"] >= 0
    assert result["p50_ms"] >= 0


def test_harness_writes_json() -> None:
    import tempfile

    from benchmarks.harness import main

    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.json"
        main(["--output", str(out), "--iterations", "2"])
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "scenarios" in data
        assert len(data["scenarios"]) == 14
