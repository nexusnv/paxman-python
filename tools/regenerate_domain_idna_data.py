"""Regenerate paxman/capabilities/Domain/grammar/data/idna_mapping.py.

Usage:
    uv run python tools/regenerate_domain_idna_data.py [--check]

Reads the committed UTS #46 IdnaMappingTable snapshot — the single in-tree
table text shared with URL, closing gap G8 — and emits the Domain
grammar-side data module. Run manually when the snapshot is refreshed.
Standard library only.

Table-vs-spec provenance pin: the shipped table is UTS #46 15.1.0
(``IDNA_VERSION``, equal to the URL data module's version); validation
rules cite the UTS #46 specification lineage (v18.0.0) in their
provenance. The research report's "v18.0.0 table" phrasing conflated the
two; this pin separates them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT = _REPO_ROOT / "paxman/capabilities/URL/rules/data/idna_uts46_mapping.txt"
OUTPUT = _REPO_ROOT / "paxman/capabilities/Domain/grammar/data/idna_mapping.py"
LINE_LENGTH = 88  # must match ruff's line-length in pyproject.toml
IDNA_VERSION = "15.1.0"  # pinned UTS #46 table version (== URL shipped table)


def _parse_snapshot() -> tuple[dict[str, str], dict[int, str]]:
    """Return (statuses, mapping) parsed from the committed snapshot.

    statuses maps every range token (single code point or ``start..end``)
    to its UTS #46 status. mapping expands only ``mapped``-status rows to
    integer code points; values are the table target verbatim (single
    4-char hex or space-separated multi-target, e.g. ``"0066 0066"`` —
    1,018 rows). Source ranges broadcast their target to every code
    point (no range-target rows exist in the table). ``deviation`` rows
    are deliberately NOT expanded: non-transitional processing keeps
    them verbatim.
    """
    statuses: dict[str, str] = {}
    mapping: dict[int, str] = {}
    for line in SNAPSHOT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = [f.partition("#")[0].strip() for f in stripped.split(";")]
        range_token, status = fields[0], fields[1]
        statuses[range_token] = status
        if status == "mapped" and len(fields) > 2 and fields[2]:
            target = fields[2]
            if ".." in range_token:
                start, _, end = range_token.partition("..")
                for cp in range(int(start, 16), int(end, 16) + 1):
                    mapping[cp] = target
            else:
                mapping[int(range_token, 16)] = target
    return statuses, mapping


def _emit_str_table(entries: dict[str, str], prefix_len: int = 0) -> str:
    """Emit a str-keyed dict literal with ruff-format-compliant line lengths.

    Mirrors tools/regenerate_idna_uts46_data.py: single-line when the
    whole table fits within 88 columns, otherwise one entry per line
    (magic trailing comma); overlong values become parenthesized
    implicit string concatenations split on token boundaries.
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


def _emit_int_table(entries: dict[int, str]) -> str:
    """Emit the int-keyed MAPPING literal, one entry per line (sorted)."""
    blocks: list[str] = []
    for key in sorted(entries):
        value = entries[key]
        full = f'    {key}: "{value}",'
        if len(full) <= LINE_LENGTH:
            blocks.append(full)
        else:
            blocks.extend(_wrapped_int_entry(key, value))
    return "{\n" + "\n".join(blocks) + "\n}"


def _wrapped_entry(key: str, value: str) -> list[str]:
    """Emit one str entry as parenthesized implicit string concatenation."""
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


def _wrapped_int_entry(key: int, value: str) -> list[str]:
    """Emit one int-keyed entry as parenthesized implicit concatenation."""
    max_chunk = LINE_LENGTH - 14  # indent + key + quotes + margin
    chunks: list[str] = []
    remaining = value
    while len(remaining) > max_chunk:
        cut = remaining.rfind(" ", 0, max_chunk + 1)
        if cut == -1:
            cut = max_chunk
            chunks.append(remaining[:cut])
            remaining = remaining[cut:]
        else:
            chunks.append(remaining[: cut + 1])
            remaining = remaining[cut + 1 :]
    if remaining:
        chunks.append(remaining)
    lines = [f"    {key}: ("]
    lines.extend(f'        "{chunk}"' for chunk in chunks)
    lines.append("    ),")
    return lines


def _build_module(statuses: dict[str, str], mapping: dict[int, str]) -> str:
    """Assemble the generated module text for the parsed snapshot tables."""
    status_assign = "STATUSES: dict[str, str] = "
    mapping_assign = "MAPPING: dict[int, str] = "
    doc = (
        '"""UTS #46 IdnaMappingTable data for Domain grammars — GENERATED.\n'
        "\n"
        "Do not edit by hand. Source: the single in-tree table text shared\n"
        "with URL (paxman/capabilities/URL/rules/data/idna_uts46_mapping.txt).\n"
        f"Table version: {IDNA_VERSION} (spec lineage: UTS #46 v18.0.0).\n"
        "Regenerate with: uv run python tools/regenerate_domain_idna_data.py\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n\n"
        f'IDNA_VERSION = "{IDNA_VERSION}"\n\n'
        + mapping_assign
        + _emit_int_table(mapping)
        + "\n\n"
        + status_assign
        + _emit_str_table(statuses, len(status_assign))
        + "\n"
    )
    if "output_format" in doc:  # purity guard — see test_no_output_format_token
        raise RuntimeError("generated module must not contain 'output_format'")
    return doc


def render() -> str:
    """Return the generated module text (pure — does not touch OUTPUT)."""
    statuses, mapping = _parse_snapshot()
    return _build_module(statuses, mapping)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate Domain UTS #46 data.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="regenerate in memory and exit non-zero if drift",
    )
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            rel = OUTPUT.relative_to(_REPO_ROOT)
            print(f"DRIFT: {rel} differs from generated output", file=sys.stderr)
            raise SystemExit(1)
        print("Domain UTS #46 generated data module is up to date")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT.parent / "__init__.py").touch(exist_ok=True)
    OUTPUT.write_text(render(), encoding="utf-8")
    statuses, mapping = _parse_snapshot()
    print(f"wrote {OUTPUT}: {len(statuses)} statuses, {len(mapping)} mappings")


if __name__ == "__main__":
    main()
