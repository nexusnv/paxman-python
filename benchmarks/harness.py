"""Minimal benchmark harness — one scenario per capability (W5, Item 7).

No external deps. Deterministic per contract+input+library snapshot.
Measures wall-clock via time.perf_counter, reports mean/p50/p95 per scenario.
Used in CI as non-blocking signal and locally via --update-baseline.

Usage:
    uv run python -m benchmarks.harness --iterations 200
    uv run python -m benchmarks.harness --output /tmp/bench.json
    uv run python -m benchmarks.harness --update-baseline
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from benchmarks.scenarios import SCENARIOS

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "benchmarks" / "baseline.json"


def run_once(
    capability: str, text: str, iterations: int = 100
) -> dict[str, float | str | int]:
    from paxman import canonicalize
    from paxman.core.discovery import freeze_registry, get_capability, reset_registry

    if iterations <= 0:
        raise ValueError(f"iterations must be a positive integer, got {iterations!r}")

    # Import capability lazily to respect PEP 562 (Item 8)
    # — harness must not hide import cost
    # Scenarios carry a factory: lambda: (contract, text)
    scenario = next(s for s in SCENARIOS if s["capability"] == capability)
    durations: list[float] = []

    # Freeze-cost scenario: times reset + register + freeze only (reported separately)
    if capability == "freeze":
        for _ in range(iterations):
            reset_registry()
            start = time.perf_counter()
            scenario["register"]()
            freeze_registry()
            durations.append((time.perf_counter() - start) * 1000)
            reset_registry()
        durations.sort()
        p50 = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95)]
        return {
            "capability": capability,
            "iterations": iterations,
            "mean_ms": statistics.mean(durations),
            "p50_ms": p50,
            "p95_ms": p95,
            "min_ms": min(durations),
            "max_ms": max(durations),
        }

    # Recognition-only scenarios: grammar recognition only (no rules)
    if "-recognition-" in capability:
        base = capability.split("-recognition-")[0]
        for _ in range(iterations):
            reset_registry()
            scenario["register"]()
            freeze_registry()
            cap = get_capability(base)
            grammars = cap.get_grammars()
            start = time.perf_counter()
            for grammar in grammars:
                grammar.recognize(text)
            durations.append((time.perf_counter() - start) * 1000)
            reset_registry()
        durations.sort()
        p50 = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95)]
        return {
            "capability": capability,
            "iterations": iterations,
            "mean_ms": statistics.mean(durations),
            "p50_ms": p50,
            "p95_ms": p95,
            "min_ms": min(durations),
            "max_ms": max(durations),
        }

    for _ in range(iterations):
        reset_registry()
        # Register only the needed capability for this scenario
        # (isolates import cost if lazy)
        scenario["register"]()
        contract = scenario["contract_factory"]()
        freeze_registry()
        start = time.perf_counter()
        canonicalize(text, contract)
        durations.append((time.perf_counter() - start) * 1000)
        # reset_registry cleans for next iteration
        reset_registry()
    durations.sort()
    p50 = durations[len(durations) // 2]
    p95 = durations[int(len(durations) * 0.95)]
    return {
        "capability": capability,
        "iterations": iterations,
        "mean_ms": statistics.mean(durations),
        "p50_ms": p50,
        "p95_ms": p95,
        "min_ms": min(durations),
        "max_ms": max(durations),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Paxman benchmark harness (Item 7)")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args(argv)

    results: list[dict[str, float | str | int]] = []
    for scenario in SCENARIOS:
        results.append(
            run_once(
                scenario["capability"], scenario["text"], iterations=args.iterations
            )
        )

    payload: dict[str, object] = {"scenarios": results, "iterations": args.iterations}
    if args.output:
        Path(args.output).write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.output}")
    elif args.update_baseline:
        BASELINE.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {BASELINE}")
    else:
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
