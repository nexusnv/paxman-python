"""Paxman CLI — `python -m paxman` and `paxman` console script."""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn

from paxman.api.bootstrap import list_shipped_capabilities
from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import MultipleMentionsError


def _normalize_capability(raw: str) -> str:
    """Normalize capability name: case-insensitive, alias-aware."""
    lowered = raw.strip().lower().replace("-", "_")
    if lowered == "siunit":
        return "si_unit"
    return lowered


def _build_parser() -> argparse.ArgumentParser:
    shipped = ", ".join(list_shipped_capabilities())
    parser = argparse.ArgumentParser(
        prog="paxman",
        description=(
            "Paxman CLI — canonicalize text with provenance.\n"
            "Examples:\n"
            '  paxman email "User@Example.COM"\n'
            '  echo "usd" | paxman currency\n'
            "  paxman --list\n"
            '  paxman email --json "user@example.com"'
        ),
        epilog=(
            f"Capabilities: {shipped}\n"
            "Aliases: si_unit accepts siunit, si-unit, si_unit (case-insensitive).\n"
            "Contract flags (e.g. --include-localized) require the Python API; "
            "see docs for create_contract() options."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list shipped capabilities and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output JSON with status, value, provenance",
    )
    parser.add_argument(
        "capability",
        nargs="?",
        help="capability name (case-insensitive, e.g. email, Email, EMAIL)",
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="text to canonicalize (stdin if omitted)",
    )
    return parser


def _print_list() -> None:
    for name in list_shipped_capabilities():
        print(name)


def _create_contract(normalized: str) -> CapabilityContract:
    """Create a default contract for the normalized capability name."""
    if normalized == "country":
        from paxman.capabilities import Country

        return Country.create_contract()
    if normalized == "currency":
        from paxman.capabilities import Currency

        return Currency.create_contract()
    if normalized == "date":
        from paxman.capabilities import Date

        return Date.create_contract()
    if normalized == "email":
        from paxman.capabilities import Email

        return Email.create_contract()
    if normalized == "iban":
        from paxman.capabilities import IBAN

        return IBAN.create_contract()
    if normalized == "ip":
        from paxman.capabilities import IP

        return IP.create_contract()
    if normalized == "isbn":
        from paxman.capabilities import ISBN

        return ISBN.create_contract()
    if normalized == "issn":
        from paxman.capabilities import ISSN

        return ISSN.create_contract()
    if normalized == "money":
        from paxman.capabilities import Money

        return Money.create_contract()
    if normalized == "orcid":
        from paxman.capabilities import ORCID

        return ORCID.create_contract()
    if normalized == "phone":
        from paxman.capabilities import Phone

        return Phone.create_contract()
    if normalized == "si_unit":
        from paxman.capabilities import SIUnit

        return SIUnit.create_contract()
    if normalized == "url":
        from paxman.capabilities import URL

        return URL.create_contract()
    # Should be unreachable after validation, but keep for type safety.
    raise ValueError(f"Unknown capability: {normalized!r}")


def _resolve_text(arg_text: str | None) -> str | None:
    if arg_text is not None:
        return arg_text
    # No text arg: try stdin if piped or redirected.
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        # Preserve inner whitespace, strip only trailing newlines for pipe ergonomics.
        # Empty stdin is treated as no input.
        if data == "":
            return None
        # Remove a single trailing newline common with `echo`, but keep other content.
        if data.endswith("\n"):
            data = data[:-1]
            if data.endswith("\r"):
                data = data[:-1]
        return data
    return None


def _fail(message: str, code: int = 1) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def _print_human(result: object) -> None:
    # Typed locally to avoid top-level circular imports.
    # Validated by pyright structurally.
    from paxman.engine.orchestrator import ExecutionResult

    assert isinstance(result, ExecutionResult)
    # Status name is uppercase (SUCCESS, MISSING, etc.)
    print(f"status: {result.status.name}")
    if result.canonicalized_value is not None:
        print(f"value: {result.canonicalized_value}")
    else:
        print("value: null")
    if result.span is not None:
        print(f"span: [{result.span[0]}, {result.span[1]})")
    else:
        print("span: null")
    if result.candidates:
        for cand in result.candidates:
            for prov in cand.provenance:
                print(
                    f"provenance: {prov.authority} — {prov.specification_name}"
                    + f" [{prov.reference_url}]"
                )
            # Candidate span trace
            if cand.span is not None:
                rec = cand.recognition_rule
                val = cand.validation_rule
                span = f"[{cand.span[0]}, {cand.span[1]})"
                print(f"candidate: {cand.value!r} via {rec}/{val} span={span}")
            else:
                rec = cand.recognition_rule
                val = cand.validation_rule
                print(f"candidate: {cand.value!r} via {rec}/{val}")
    else:
        print("provenance: —")


def _print_json(result: object) -> None:
    from paxman.engine.orchestrator import ExecutionResult

    assert isinstance(result, ExecutionResult)
    provenance_list: list[dict[str, object]] = []
    for cand in result.candidates:
        for prov in cand.provenance:
            provenance_list.append(
                {
                    "authority": prov.authority,
                    "specification_name": prov.specification_name,
                    "kind": prov.kind,
                    "reference_url": prov.reference_url,
                    "version": prov.version,
                    "lifecycle": prov.lifecycle,
                    "publication_year": prov.publication_year,
                    "citation": cand.validation_rule,
                }
            )
    payload: dict[str, object] = {
        "status": result.status.name,
        "value": result.canonicalized_value,
        "span": list(result.span) if result.span is not None else None,
        "provenance": provenance_list,
        "candidates": [
            {
                "value": c.value,
                "recognition_rule": c.recognition_rule,
                "validation_rule": c.validation_rule,
                "span": list(c.span) if c.span is not None else None,
            }
            for c in result.candidates
        ],
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --list must not freeze registry (bootstrap list is pure).
    if args.list:
        _print_list()
        return

    if args.capability is None:
        parser.print_help(sys.stdout)
        sys.exit(1)

    normalized = _normalize_capability(args.capability)
    shipped_set = set(list_shipped_capabilities())
    if normalized not in shipped_set:
        shipped_str = ", ".join(list_shipped_capabilities())
        _fail(
            f"unknown capability {args.capability!r}. "
            f"Run `paxman --list` to see: {shipped_str}"
        )

    text = _resolve_text(args.text)
    if text is None:
        _fail("no text provided — pass an argument or pipe via stdin")

    # Register before canonicalizing; keep help/list above this freeze point.
    from paxman.api.bootstrap import register_all_shipped
    from paxman.api.canonicalize import canonicalize

    register_all_shipped()

    contract = _create_contract(normalized)

    try:
        result = canonicalize(text, contract)
    except MultipleMentionsError as exc:
        # Print the message which contains docs/recipes/segmentation.md
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:  # ContractError, CapabilityError, etc.
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        _print_json(result)
    else:
        _print_human(result)


if __name__ == "__main__":
    main()
