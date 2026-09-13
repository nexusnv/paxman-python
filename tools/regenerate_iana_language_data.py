"""Guard removed IANA language generated data (B7/D5 closeout).

Previously generated from ``paxman/shared_data/iana_language_snapshot.json``
plus ``paxman/shared_data/language_snapshot.json``:

  - paxman/capabilities/Language/grammar/data/iana_registry.py
    (stub with an empty registry — zero consumers)
  - paxman/capabilities/Language/grammar/data/names.py
    (NAME_TOKENS projection padded to 100 entries with synthetic tokens —
    single consumer asserting ``> 77``, true only because of the padding)

Both were dead weight in shipped data. They were removed at the generator
(not just the files) so regeneration cannot resurrect them; this tool now
guards their absence instead of emitting them.

Usage:
    uv run python tools/regenerate_iana_language_data.py
    uv run python tools/regenerate_iana_language_data.py --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REMOVED: tuple[Path, ...] = (
    ROOT
    / "paxman"
    / "capabilities"
    / "Language"
    / "grammar"
    / "data"
    / "iana_registry.py",
    ROOT / "paxman" / "capabilities" / "Language" / "grammar" / "data" / "names.py",
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Guard removed IANA language generated data."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if a removed module is present",
    )
    args = parser.parse_args()
    present = [path for path in REMOVED if path.exists()]
    if args.check:
        if present:
            for path in present:
                print(
                    f"DRIFT: {path.relative_to(ROOT)} should not exist",
                    file=sys.stderr,
                )
            raise SystemExit(1)
        print("all IANA language generated data modules are up to date")
        return
    for path in present:
        path.unlink()
        print(f"removed {path.relative_to(ROOT)}")
    if not present:
        print("all IANA language generated data modules are up to date")


if __name__ == "__main__":
    main()
