"""IDN hostname recognition grammar (kernel RegexMatcher).

Recognizes dot-separated labels of any non-reserved characters (Unicode
letters included, ASCII URL/reserved punctuation excluded) with an
optional trailing-dot run. No non-ASCII predicate: ASCII-only input
matches here too — same-span dedup with ascii_hostname resolves the
overlap. Case/dot-variants fold at emit via :func:`map_domain`. Syntax
only: never validates, never encodes to punycode.
"""

from __future__ import annotations

from paxman.capabilities.Domain.idna_processing import map_domain
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

_IDN_CHARS = r"[^\s.@:/\\?#\[\]%*;,]"
_IDN_LABEL = rf"{_IDN_CHARS}+"
_IDN_LABEL0 = rf"{_IDN_CHARS}*"
_IDN_FQDN = rf"{_IDN_LABEL}(?:\.{_IDN_LABEL0})*\.*"

# == _ASCII_KILL minus the non-ASCII class: IDN text must match here.
_IDN_KILL = (
    "\\w",
    "\\.",
    "\\*",
    "@",
    ":",
    "/",
    "\\\\",
    "\\?",
    "#",
    "\\[",
    "\\]",
    "%",
)


def _emit_idn(span: tuple[int, int], ctx: ScanContext) -> DomainNotation:
    s, e = span
    raw = ctx.text[s:e]
    # The pattern guarantees at least one in-class char; mapped ASCII
    # fallbacks (case/dot variants) never vanish, so labels is non-empty.
    labels = map_domain(raw)
    return DomainNotation(raw=raw, labels=labels, tld=labels[-1])


_IDN_MATCHER = RegexMatcher(
    pattern=_IDN_FQDN,
    boundary=BoundarySpec(left=_IDN_KILL, right=_IDN_KILL),
    view=None,
    anchors=AnchorSet(),
    emit=_emit_idn,
)


class IdnHostnameGrammar(PipelineGrammar[DomainNotation]):
    """Recognizes IDN hostname shapes (any script, mapped at emit).

    Examples: "münchen.de", "ｅxample。ｊｐ", "example.com" (overlap).
    Non-examples: "[::1]", "user@example.com" (reserved ASCII excluded).
    """

    name = "idn_hostname"
    semantics = "idn_hostname"
    single_value = True

    pre = StandardPre[DomainNotation](empty_guard=True)
    matchers = (_IDN_MATCHER,)
