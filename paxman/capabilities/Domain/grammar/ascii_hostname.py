"""ASCII hostname recognition grammar (kernel RegexMatcher).

Recognizes dot-separated LDH labels (ASCII letters, digits, hyphen) with an
optional trailing-dot run. Case is recognition-neutral: the raw span keeps
its original case and :func:`map_domain` folds it at emit. Syntax only:
never validates, never encodes to punycode (encoding happens in rules).
"""

from __future__ import annotations

from paxman.capabilities.Domain.idna_processing import map_domain
from paxman.capabilities.Domain.notation import DomainNotation
from paxman.core.grammar import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre
from paxman.core.grammar.matchers.regex import RegexMatcher
from paxman.core.grammar.scan_context import ScanContext

_LABEL = r"[A-Za-z0-9-]+"
_LABEL0 = r"[A-Za-z0-9-]*"
_FQDN = rf"{_LABEL}(?:\.{_LABEL0})*\.*"

# Neighbors that kill a candidate span on either side (mirroring
# (?<!...) / (?!...) zero-width guards): word chars and dots (sub-span
# carving), URL/reserved punctuation, and the non-ASCII class (IDN text
# belongs to the idn_hostname grammar).
_ASCII_KILL = (
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
    "[^\\x00-\\x7F]",
)


def _emit_ascii(span: tuple[int, int], ctx: ScanContext) -> DomainNotation:
    s, e = span
    raw = ctx.text[s:e]
    # The pattern guarantees at least one ASCII LDH char, so the mapped
    # labels are provably non-empty.
    labels = map_domain(raw)
    return DomainNotation(raw=raw, labels=labels, tld=labels[-1])


_ASCII_MATCHER = RegexMatcher(
    pattern=_FQDN,
    boundary=BoundarySpec(left=_ASCII_KILL, right=_ASCII_KILL),
    view=None,
    anchors=AnchorSet(),
    emit=_emit_ascii,
)


class AsciiHostnameGrammar(PipelineGrammar[DomainNotation]):
    """Recognizes ASCII hostname shapes (case-neutral, trailing dots kept).

    Examples: "example.com", "EXAMPLE.COM", "example.com."
    Non-examples: "münchen.de" (non-ASCII — idn_hostname owns it).
    """

    name = "ascii_hostname"
    semantics = "ascii_hostname"
    single_value = True

    pre = StandardPre[DomainNotation](empty_guard=True)
    matchers = (_ASCII_MATCHER,)
