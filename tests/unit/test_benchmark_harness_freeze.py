"""RED→GREEN gate for Task A0: freeze outside timed region.

Asserts benchmarks/harness.py run_once orders freeze_registry() before
time.perf_counter() and keeps reset/register outside the timed window.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_harness_freeze_outside_timed_region() -> None:
    harness_path = Path(__file__).resolve().parents[2] / "benchmarks" / "harness.py"
    source = harness_path.read_text(encoding="utf-8")

    # Extract run_once function body (from def run_once to next def at same indent)
    match = re.search(r"def run_once\(.*?\n(?=def |\Z)", source, flags=re.DOTALL)
    assert match is not None, "run_once not found in harness"
    body = match.group(0)

    # 1) freeze_registry() must appear before time.perf_counter() in run_once
    freeze_pos = body.find("freeze_registry")
    perf_pos = body.find("time.perf_counter()")
    assert freeze_pos != -1, "freeze_registry() not found in run_once"
    assert perf_pos != -1, "time.perf_counter() not found in run_once"
    assert freeze_pos < perf_pos, (
        "freeze_registry() must appear before time.perf_counter() in run_once; "
        f"freeze at {freeze_pos}, perf_counter at {perf_pos}"
    )

    # 2) No reset_registry() or scenario["register"] between start= and canonicalize
    # for the main pipeline path (last start->canonicalize window). Earlier branches
    # (freeze, recognition-only) have their own timing windows and are excluded.
    starts = [m.start() for m in re.finditer(r"start = time\.perf_counter\(\)", body)]
    assert starts, "start = time.perf_counter() not found"
    canons = [m.start() for m in re.finditer(r"canonicalize\(", body)]
    assert canons, "canonicalize( not found"
    # Use the last canonicalize and the latest start before it (main pipeline)
    last_canon = canons[-1]
    # Find the start that immediately precedes the last canonicalize
    pipeline_start = max(s for s in starts if s < last_canon)
    timed_window = body[pipeline_start:last_canon]
    assert "reset_registry()" not in timed_window, (
        "reset_registry() must not appear between start= and canonicalize() — "
        "it should be hoisted before the timer"
    )
    has_register = (
        'scenario["register"]' in timed_window or "scenario['register']" in timed_window
    )
    assert not has_register, (
        'scenario["register"] must not appear between start= and canonicalize() — '
        "hoist before timer"
    )


def test_harness_freeze_imported() -> None:
    harness_path = Path(__file__).resolve().parents[2] / "benchmarks" / "harness.py"
    source = harness_path.read_text(encoding="utf-8")
    assert "freeze_registry" in source, "harness must import/use freeze_registry"
