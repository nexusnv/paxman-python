"""Paxman CLI — `python -m paxman` and `paxman` console script."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, NoReturn, cast

from paxman.api.bootstrap import list_shipped_capabilities
from paxman.core.capability_contract import CapabilityContract
from paxman.core.errors import MultipleMentionsError, PaxmanError


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
            '  paxman email --json "user@example.com"\n'
            '  paxman scan "Ship to United States please"\n'
            '  paxman scan --json "Ship to United States please"\n'
            '  paxman scan country "Ship to United States please"'
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


def _build_scan_parser() -> argparse.ArgumentParser:
    shipped = ", ".join(list_shipped_capabilities())
    parser = argparse.ArgumentParser(
        prog="paxman scan",
        description=(
            "Scan text for mentions — one substrate pass, per-capability Mentions.\n"
            "Examples:\n"
            '  paxman scan "Ship to United States please"\n'
            '  paxman scan --json "Ship to United States please"\n'
            '  paxman scan country "Ship to United States please"\n'
            '  paxman scan --suppress-common-words "Ship to United States please"\n'
            '  echo "hello" | paxman scan --json'
        ),
        epilog=(
            f"Capabilities: {shipped}\n"
            "If no capability is given, all shipped capabilities are scanned.\n"
            "Flag --suppress-common-words gates common-word suppression for\n"
            "short-code matchers (Country alpha2/alpha3/numeric, Currency code,\n"
            "Language language_code) per ADR-0009 §16 — off by default\n"
            "(provenance-neutral; a suppressed span is simply not emitted).\n"
            "Default scan contracts are flag-off; use the API flag for\n"
            "canonicalize() control."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output JSON",
    )
    parser.add_argument(
        "--suppress-common-words",
        action="store_true",
        help=(
            "suppress common-word hits for short-code matchers "
            "(ADR-0009 §16); off by default"
        ),
    )
    parser.add_argument(
        "--capability",
        "-c",
        action="append",
        dest="capabilities",
        default=None,
        help="capability to scan (repeatable; default all)",
    )
    parser.add_argument(
        "pos",
        nargs="*",
        help=(
            "optional [capability] [text]; capability is case-insensitive, "
            "text is stdin if omitted"
        ),
    )
    return parser


def _print_list() -> None:
    for name in list_shipped_capabilities():
        print(name)


def _create_contract(
    normalized: str, suppress_common_words: bool = False
) -> CapabilityContract:
    """Create a default contract for the normalized capability name."""
    if normalized == "bic":
        from paxman.capabilities import BIC

        return BIC.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "coordinates":
        from paxman.capabilities import Coordinates

        return Coordinates.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "country":
        from paxman.capabilities import Country

        return Country.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "currency":
        from paxman.capabilities import Currency

        return Currency.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "date":
        from paxman.capabilities import Date

        return Date.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "element":
        from paxman.capabilities import Element

        return Element.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "email":
        from paxman.capabilities import Email

        return Email.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "iban":
        from paxman.capabilities import IBAN

        return IBAN.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "ip":
        from paxman.capabilities import IP

        return IP.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "isbn":
        from paxman.capabilities import ISBN

        return ISBN.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "issn":
        from paxman.capabilities import ISSN

        return ISSN.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "language":
        from paxman.capabilities import Language

        return Language.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "mac_address":
        from paxman.capabilities import MacAddress

        return MacAddress.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "money":
        from paxman.capabilities import Money

        return Money.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "orcid":
        from paxman.capabilities import ORCID

        return ORCID.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "phone":
        from paxman.capabilities import Phone

        return Phone.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "si_unit":
        from paxman.capabilities import SIUnit

        return SIUnit.create_contract(suppress_common_words=suppress_common_words)
    if normalized == "url":
        from paxman.capabilities import URL

        return URL.create_contract(suppress_common_words=suppress_common_words)
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


def _print_scan_human(result: object) -> None:
    from paxman.core.domain import ScanResult

    assert isinstance(result, ScanResult)
    print(f"text: {result.text!r}")
    if not result.mentions:
        print("mentions: —")
        return
    for cap_name in sorted(result.mentions.keys()):
        mentions = result.mentions[cap_name]
        print(f"capability: {cap_name}")
        if not mentions:
            print("  mentions: —")
            continue
        for m in mentions:
            span = f"[{m.span[0]}, {m.span[1]})"
            raw = result.text[m.span[0] : m.span[1]]
            msg = (
                f"  mention: {raw!r} span={span} "
                f"grammar={m.grammar} notation={m.notation!r}"
            )
            print(msg)


def _print_scan_json(result: object) -> None:
    import dataclasses

    from paxman.core.domain import ScanResult

    assert isinstance(result, ScanResult)
    mentions_payload: dict[str, list[dict[str, object]]] = {}
    for cap_name, mentions in result.mentions.items():
        lst: list[dict[str, object]] = []
        for m in mentions:
            notation_obj = m.notation
            if dataclasses.is_dataclass(notation_obj) and not isinstance(
                notation_obj, type
            ):
                notation_val: object = dataclasses.asdict(cast(Any, notation_obj))
            else:
                notation_val = str(notation_obj)
            lst.append(
                {
                    "span": list(m.span),
                    "grammar": m.grammar,
                    "notation": notation_val,
                    "candidates": (
                        [
                            {
                                "value": c.value,
                                "recognition_rule": c.recognition_rule,
                                "validation_rule": c.validation_rule,
                                "span": list(c.span) if c.span is not None else None,
                            }
                            for c in m.candidates
                        ]
                        if m.candidates is not None
                        else None
                    ),
                }
            )
        mentions_payload[cap_name] = lst
    payload: dict[str, object] = {
        "text": result.text,
        "mentions": mentions_payload,
    }
    json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def _handle_scan(scan_argv: list[str]) -> None:
    # Manual flag extraction to allow interspersed `--json` / `-c` with
    # positional capability/text (argparse with nargs="*" is order-sensitive).
    # Supports: `paxman scan [--json] [capability] [text]`
    #           `paxman scan country --json "text"` etc.
    parser = _build_scan_parser()
    # Only flags before `--` are real options; after `--` treat as verbatim text
    help_check_args = (
        scan_argv[: scan_argv.index("--")] if "--" in scan_argv else scan_argv
    )
    if any(a in ("-h", "--help") for a in help_check_args):
        parser.print_help(sys.stdout)
        sys.exit(0)

    json_flag = False
    suppress_flag = False
    cap_filters_raw: list[str] = []
    pos: list[str] = []
    after_double_dash = False
    text_after_dash: str | None = None
    i = 0
    while i < len(scan_argv):
        arg = scan_argv[i]
        if arg == "--json":
            json_flag = True
        elif arg == "--suppress-common-words":
            suppress_flag = True
        elif arg in ("--capability", "-c"):
            if i + 1 >= len(scan_argv):
                parser.error(f"{arg} requires an argument")
            cap_filters_raw.append(scan_argv[i + 1])
            i += 1
        elif arg.startswith("--capability="):
            cap_filters_raw.append(arg.split("=", 1)[1])
        elif arg.startswith("-c") and len(arg) > 2:
            # -ccountry is not valid; require separate arg, but handle
            cap_filters_raw.append(arg[2:])
        elif arg == "--":
            # Remaining args are positional text verbatim, never a capability
            after_double_dash = True
            if i + 1 < len(scan_argv):
                text_after_dash = " ".join(scan_argv[i + 1 :])
            break
        else:
            pos.append(arg)
        i += 1

    shipped_set = set(list_shipped_capabilities())
    # Resolve capability filters: --capability plus positional heuristic
    cap_filters: list[str] = []
    for raw in cap_filters_raw:
        norm = _normalize_capability(raw)
        if norm not in shipped_set:
            shipped_str = ", ".join(list_shipped_capabilities())
            _fail(
                f"unknown capability {raw!r}. Run `paxman --list` to see: {shipped_str}"
            )
        cap_filters.append(norm)

    text_arg: str | None = None

    # Heuristic for positional [capability] [text]
    if pos:
        # If cap_filters empty and first pos looks like a capability, treat it as filter
        first_norm = _normalize_capability(pos[0])
        if not cap_filters and first_norm in shipped_set:
            # One positional capability alone -> filter, text from stdin
            # or two positionals where first is capability and second is text
            if len(pos) == 1:
                cap_filters.append(first_norm)
                pos = []
            elif len(pos) >= 2:
                cap_filters.append(first_norm)
                # Remaining pos joined as text (preserves spaces if split)
                text_arg = " ".join(pos[1:]) if len(pos) > 2 else pos[1]
                pos = []
            else:
                pos = []
        # Remaining pos is text (join with space if multiple)
        if pos:
            text_arg = " ".join(pos) if len(pos) > 1 else pos[0]

    # Arguments after `--` are verbatim text, never a capability
    if after_double_dash and text_after_dash is not None:
        text_arg = text_after_dash

    # Fallback text resolution (stdin)
    text = _resolve_text(text_arg)
    if text is None:
        _fail("no text provided — pass an argument or pipe via stdin")

    from paxman.api.bootstrap import register_all_shipped
    from paxman.api.scan import scan

    register_all_shipped()

    # Default: scan all shipped if no filter
    if not cap_filters:
        cap_filters = list(list_shipped_capabilities())

    contracts = [
        _create_contract(norm, suppress_common_words=suppress_flag)
        for norm in cap_filters
    ]

    try:
        result = scan(text, contracts)
    except PaxmanError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if json_flag:
        _print_scan_json(result)
    else:
        _print_scan_human(result)


def main(argv: list[str] | None = None) -> None:
    # Scan subcommand check — must happen before the canonicalize parser
    # so `paxman scan ...` is not misinterpreted as `paxman <capability>`.
    argv_list = argv if argv is not None else sys.argv[1:]
    if argv_list and argv_list[0] == "scan":
        _handle_scan(list(argv_list[1:]))
        return

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
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        _print_json(result)
    else:
        _print_human(result)


if __name__ == "__main__":
    main()
