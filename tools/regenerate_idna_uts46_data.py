"""Regenerate paxman/capabilities/URL/rules/data/idna_uts46_mapping.py.

Usage:
    uv run python tools/regenerate_idna_uts46_data.py

Reads the committed UTS #46 IdnaMappingTable snapshot and emits the data
module. Run manually when the snapshot is refreshed. Standard library only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = _REPO_ROOT / "paxman/capabilities/URL/rules/data/idna_uts46_mapping.txt"
OUTPUT = _REPO_ROOT / "paxman/capabilities/URL/rules/data/idna_uts46_mapping.py"
LINE_LENGTH = 88  # must match ruff's line-length in pyproject.toml
IDNA_VERSION = "15.1.0"  # pinned UTS #46 version

# Statuses whose rows carry a mapping field (UTS #46 IdnaMappingTable).
_MAPPED_STATUSES = frozenset({"mapped", "deviation", "disallowed_STD3_mapped"})


def _parse_snapshot() -> tuple[dict[str, str], dict[str, str]]:
    """Return (statuses, mappings) parsed from the committed snapshot.

    statuses maps every range token (single code point or ``start..end``)
    to its UTS #46 status. mappings maps only the rows whose status is
    ``mapped``, ``deviation``, or ``disallowed_STD3_mapped`` to their target
    sequence (space-separated uppercase hex, as written). A mapped-status
    row that lacks a mapping field is recorded in statuses only.
    """
    statuses: dict[str, str] = {}
    mappings: dict[str, str] = {}
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = [f.partition("#")[0].strip() for f in stripped.split(";")]
        range_token, status = fields[0], fields[1]
        statuses[range_token] = status
        if status in _MAPPED_STATUSES and len(fields) > 2 and fields[2]:
            mappings[range_token] = fields[2]
    return statuses, mappings


def _emit_str_table(entries: dict[str, str], prefix_len: int = 0) -> str:
    """Emit a dict literal with ruff-format-compliant line lengths.

    Single-line when the whole table (including the ``prefix_len``
    characters of the assignment that precedes it at the call site) fits
    within 88 columns; otherwise multiline (one entry per line, magic
    trailing comma). An entry whose line would exceed 88 columns is
    emitted as a parenthesized implicit string concatenation split on
    token boundaries, so every line stays compliant.
    """

    one_line = (
        "{" + ", ".join(f'"{key}": "{value}"' for key, value in entries.items()) + "}"
    )
    if len(one_line) + prefix_len <= LINE_LENGTH:
        return one_line
    blocks: list[str] = []
    for key, value in entries.items():
        full = f'    "{key}": "{value}",'
        if len(full) <= LINE_LENGTH:
            blocks.append(full)
        else:
            blocks.extend(_wrapped_entry(key, value))
    return "{\n" + "\n".join(blocks) + "\n}"


def _wrapped_entry(key: str, value: str) -> list[str]:
    """Emit one entry as a parenthesized implicit string concatenation.

    Chunks are split at token boundaries (each chunk keeps its trailing
    space) so concatenation reproduces the original value exactly and
    every emitted line stays within LINE_LENGTH.
    """

    max_chunk = LINE_LENGTH - 12  # 8 indent + 2 quotes + margin
    chunks: list[str] = []
    remaining = value
    while len(remaining) > max_chunk:
        cut = remaining.rfind(" ", 0, max_chunk + 1)
        if cut == -1:  # no boundary within limit; hard split
            cut = max_chunk
            chunks.append(remaining[:cut])
            remaining = remaining[cut:]
        else:
            chunks.append(remaining[: cut + 1])  # keep the space: lossless join
            remaining = remaining[cut + 1 :]
    if remaining:
        chunks.append(remaining)
    lines = [f'    "{key}": (']
    lines.extend(f'        "{chunk}"' for chunk in chunks)
    lines.append("    ),")
    return lines


def _build_module(statuses: dict[str, str], mappings: dict[str, str]) -> str:
    """Assemble the generated module text for the parsed snapshot tables."""

    status_assign = "IDNA_STATUS: dict[str, str] = "
    mapped_assign = "IDNA_MAPPED: dict[str, str] = "
    doc = (
        '"""UTS #46 IdnaMappingTable data — GENERATED, do not edit by hand.\n'
        "\n"
        f"Source: https://www.unicode.org/Public/idna/{IDNA_VERSION}/IdnaMappingTable.txt\n"
        f"Version: {IDNA_VERSION}\n"
        "Regenerate with: uv run python tools/regenerate_idna_uts46_data.py\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n\n"
        f'IDNA_VERSION = "{IDNA_VERSION}"\n\n'
        + status_assign
        + _emit_str_table(statuses, len(status_assign))
        + "\n\n"
        + mapped_assign
        + _emit_str_table(mappings, len(mapped_assign))
        + "\n"
    )
    if "output_format" in doc:  # purity guard — see test_no_output_format_token
        raise RuntimeError("generated module must not contain 'output_format'")
    return doc


def render() -> str:
    """Return the generated module text (pure — does not touch OUTPUT)."""

    statuses, mappings = _parse_snapshot()
    return _build_module(statuses, mappings)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate UTS #46 mapping.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and exit non-zero if drift",
    )
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                f"DRIFT: {OUTPUT.relative_to(_REPO_ROOT)} differs from generated output",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print("all UTS #46 generated data modules are up to date")
        return
    statuses, mappings = _parse_snapshot()
    OUTPUT.write_text(_build_module(statuses, mappings), encoding="utf-8")
    print(f"wrote {OUTPUT}: {len(statuses)} statuses, {len(mappings)} mappings")


if __name__ == "__main__":
    main()
