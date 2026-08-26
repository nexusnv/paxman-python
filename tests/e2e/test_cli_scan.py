"""CLI scan subcommand."""

import json
import subprocess


def _run_cli(
    args: list[str], input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "python", "-m", "paxman", *args],
        input=input_text,
        capture_output=True,
        text=True,
    )


def test_cli_scan_country_mentions_human() -> None:
    result = _run_cli(["scan", "country", "Ship to United States please"])
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    # Human output should mention both substrings
    assert "United States" in result.stdout
    assert "to" in result.stdout
    assert "country" in result.stdout.lower()


def test_cli_scan_json_contains_both_spans() -> None:
    result = _run_cli(["scan", "--json", "country", "Ship to United States please"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["text"] == "Ship to United States please"
    mentions = payload["mentions"]["country"]
    spans = sorted((m["span"][0], m["span"][1]) for m in mentions)
    assert (5, 7) in spans
    assert (8, 21) in spans or (9, 22) in spans
    # Grammar field present
    grammars = {m["grammar"] for m in mentions}
    assert "alpha2_recognition" in grammars
    assert "name_recognition" in grammars


def test_cli_scan_default_all_json() -> None:
    # No capability filter -> scans all shipped; must still include country mentions
    result = _run_cli(["scan", "--json", "Ship to United States please"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert "country" in payload["mentions"]
    country_spans = {
        (m["span"][0], m["span"][1]) for m in payload["mentions"]["country"]
    }
    assert (5, 7) in country_spans
    assert (8, 21) in country_spans or (9, 22) in country_spans


def test_cli_scan_stdin() -> None:
    result = _run_cli(
        ["scan", "--json", "country"], input_text="Ship to United States please"
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["text"] == "Ship to United States please"
    assert len(payload["mentions"]["country"]) == 2


def test_cli_scan_double_dash_text_is_not_capability() -> None:
    # Text matching a shipped capability (e.g. "country") after `--` must be
    # treated as positional text, never as a capability filter.
    result = _run_cli(["scan", "--json", "--", "country"])
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    payload = json.loads(result.stdout)
    assert payload["text"] == "country"
    # When scanning default all, the payload must contain all capabilities
    assert "country" in payload["mentions"]

    # Explicit capability before `--`, text after `--` that also looks like a capability
    result2 = _run_cli(["scan", "--json", "country", "--", "country"])
    assert result2.returncode == 0, f"stderr: {result2.stderr}"
    payload2 = json.loads(result2.stdout)
    assert payload2["text"] == "country"
    assert "country" in payload2["mentions"]


def test_cli_scan_double_dash_preserves_flag_like_text() -> None:
    result = _run_cli(["scan", "--json", "--", "--json"])
    assert result.returncode == 0, f"stderr: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["text"] == "--json"
