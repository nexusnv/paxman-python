"""Regenerate the IANA root-zone TLD snapshot and data module.

Usage:
    uv run python tools/regenerate_root_zone_tld_data.py \\
        --snapshot-version 2026092300 [--check]

Fetches https://data.iana.org/TLD/tlds-alpha-by-domain.txt once and writes
both paxman/shared_data/root_zone_snapshot.json (the mandatory canonical
source: _meta plus the uppercase-as-fetched list) and
paxman/capabilities/Domain/rules/data/root_zone_tlds.py (lowercase
frozenset plus snapshot stamp). --check runs offline from the committed
snapshot and exits non-zero on drift (IBAN --check precedent).
Standard library only.

Note on counts (gap G5): the Root Zone Database counts 1,595 delegations,
but the machine-readable tlds-alpha-by-domain.txt snapshot carries 1,438
entries — the module stamps the machine list, which is what the
iana_root_zone_membership rule consults.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"
SNAPSHOT_JSON = _REPO_ROOT / "paxman" / "shared_data" / "root_zone_snapshot.json"
OUTPUT = (
    _REPO_ROOT
    / "paxman"
    / "capabilities"
    / "Domain"
    / "rules"
    / "data"
    / "root_zone_tlds.py"
)
LINE_LENGTH = 88  # must match ruff's line-length in pyproject.toml


def _fetch_snapshot() -> tuple[str, list[str]]:
    """Fetch the live list; return (file version, uppercase entries)."""
    with urllib.request.urlopen(SOURCE_URL) as response:
        text = response.read().decode("utf-8")
    version = ""
    entries: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            if stripped.startswith("# Version"):
                version = stripped.removeprefix("# Version").split(",")[0].strip()
            continue
        entries.append(stripped)
    return version, entries


def _load_snapshot() -> tuple[str, list[str]]:
    """Load (file version, uppercase entries) from the committed snapshot."""
    snapshot = json.loads(SNAPSHOT_JSON.read_text(encoding="utf-8"))
    return str(snapshot["_meta"]["version"]), list(snapshot["tlds"])


def _build_module(tlds: list[str], version: str) -> str:
    """Assemble the generated root_zone_tlds.py module text."""
    stamp = f"tlds-alpha-by-domain.txt@{version}"
    lower = sorted(t.lower() for t in tlds)
    # Ruff-canonical layout (verified: ruff format is a fixed point here):
    # frozenset( { 8-space entries } ) — one entry per line, magic comma.
    entries = "\n".join(f'        "{tld}",' for tld in lower)
    doc = (
        '"""IANA root-zone TLD membership table — GENERATED, do not edit by hand.\n'
        "\n"
        f"Source: {SOURCE_URL}\n"
        f"Snapshot: {stamp} ({len(lower)} entries)\n"
        "Cross-check: Root Zone Database counts 1,595 delegations; the\n"
        "machine-readable tlds-alpha list carries fewer (no infrastructural\n"
        "pseudodomains) — the module stamps the machine list.\n"
        "Generator: uv run python tools/regenerate_root_zone_tld_data.py\n"
        "  --snapshot-version <version>\n"
        "Invariant: every entry lowercase ASCII; membership is checked on\n"
        "ace_encode(tld) by iana_root_zone_membership.\n"
        "Spot-check: com, org, net, de, jp, xn--p1ai are members;\n"
        "xn--mnchen-3ya, 123, 1 are not.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n\n"
        f'SNAPSHOT_VERSION = "{stamp}"\n\n'
        "ROOT_ZONE_TLDS: frozenset[str] = frozenset(\n"
        "    {\n"
        f"{entries}\n"
        "    }\n"
        ")\n"
    )
    for line in doc.splitlines():
        if len(line) > LINE_LENGTH:
            raise RuntimeError(f"generated line exceeds {LINE_LENGTH} columns")
    if "output_format" in doc:  # purity guard — see test_no_output_format_token
        raise RuntimeError("generated module must not contain 'output_format'")
    return doc


def render_from_snapshot() -> str:
    """Return the generated module text from the committed snapshot (pure)."""
    version, tlds = _load_snapshot()
    return _build_module(tlds, version)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate root-zone TLD data.")
    parser.add_argument(
        "--snapshot-version",
        default=None,
        help="required for generation: the IANA file version to fetch",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="offline: regenerate from the committed snapshot, exit non-zero on drift",
    )
    args = parser.parse_args()
    if args.check:
        rendered = render_from_snapshot()
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            rel = OUTPUT.relative_to(_REPO_ROOT)
            print(f"DRIFT: {rel} differs from generated output", file=sys.stderr)
            raise SystemExit(1)
        print("root-zone generated data module is up to date")
        return
    if not args.snapshot_version:
        print("--snapshot-version is required for generation", file=sys.stderr)
        raise SystemExit(2)
    fetched_version, entries = _fetch_snapshot()
    if fetched_version != args.snapshot_version:
        print(
            f"VERSION MISMATCH: live file is {fetched_version}, "
            f"requested {args.snapshot_version} — re-pin the plan pins, "
            "never hand-edit the generated module",
            file=sys.stderr,
        )
        raise SystemExit(1)
    snapshot = {
        "_meta": {
            "source": SOURCE_URL,
            "version": fetched_version,
            "entry_count": len(entries),
            "generated_by": "tools/regenerate_root_zone_tld_data.py",
        },
        "tlds": entries,
    }
    SNAPSHOT_JSON.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    (OUTPUT.parent / "__init__.py").touch(exist_ok=True)
    OUTPUT.write_text(_build_module(entries, fetched_version), encoding="utf-8")
    print(f"wrote {SNAPSHOT_JSON} + {OUTPUT}: {len(entries)} entries")


if __name__ == "__main__":
    main()
