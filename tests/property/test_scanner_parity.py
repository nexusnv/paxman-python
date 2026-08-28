"""Parity shard — scanner."""

import pytest

from paxman.core.grammar.matchers.scanner import ScannerMatcher
from paxman.core.grammar.scan_context import ScanContext, View


def _url_scan(view: View, pos: int) -> tuple[int, str] | None:
    # toy scanner for https://x/a(b(c)d)e : if subject[pos:].startswith("https://"),
    # count paren depth until space
    subj = view.subject
    if not subj[pos:].startswith("https://"):
        return None
    depth = 0
    end = pos + len("https://")
    while end < len(subj) and subj[end] not in (" ", "\t", "\n"):
        if subj[end] == "(":
            depth += 1
        elif subj[end] == ")":
            if depth == 0:
                break
            depth -= 1
        end += 1
    return (end, subj[pos:end])


@pytest.mark.property
def test_scanner_nested_parens() -> None:
    view = ScanContext.of("Visit https://example.com/a(b(c)d)e now").view(
        "orig", lambda t: (t, None, None)
    )
    m = ScannerMatcher(scan=_url_scan)
    spans = m.match(view)
    assert spans == [(6, 35)]  # "https://example.com/a(b(c)d)e"


@pytest.mark.property
def test_scanner_parity_placeholder() -> None:
    pytest.skip("Scanner parity harness — real URL/Phone parity deferred")
