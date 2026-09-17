"""UUID recognition grammar — RFC 9562 §4 carriers.

Single RegexStage with dashed|bare alternation plus optional brace/URN
carrier groups (ORCID precedent): every offered output format re-enters
(ADR-0010). ASCII hex only; case folded in emit. Trailing-guard family
follows ISBN/ISSN: an id + hyphenated suffix reads MISSING, never a
truncated SUCCESS-prefix.
"""

from __future__ import annotations

import re

from paxman.capabilities.UUID.notation import UUIDNotation
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

_HEX = r"[0-9A-Fa-f]"
_UUID_DASHED = (
    rf"(?:{_HEX}{{8}}-{{1}}{_HEX}{{4}}-{{1}}{_HEX}{{4}}"
    rf"-{{1}}{_HEX}{{4}}-{{1}}{_HEX}{{12}})"
)
_UUID_BARE = rf"{_HEX}{{32}}"
_UUID_CORE = rf"(?:{_UUID_DASHED}|{_UUID_BARE})"
# Optional URN carrier (RFC §4 Fig 4) + braces (RFC §4 Python/Microsoft
# note). Braces live outside the core groups: spans include the carrier,
# notation stays carrier-free. Braces match paired-or-absent only.
_UUID_BODY = (
    r"(?:[Uu][Rr][Nn]:[Uu][Uu][Ii][Dd]:)?"
    rf"(?:\{{(?P<core_braced>{_UUID_CORE})\}}|(?P<core_plain>{_UUID_CORE}))"
)
# word_only plus unbalanced-brace discipline: both braces join the
# forbidden neighbor set on each side, so `{uuid`, `uuid}`, `}uuid`,
# `uuid{`, `x{uuid}` claim nothing; fully braced matches are consumed by
# _UUID_BODY itself.
_UUID_PATTERN = r"(?<![\w{}])" + _UUID_BODY + r"(?![\w{}])" + r"(?![-][0-9A-Fa-f])"


def _uuid_notation(match: re.Match[str]) -> UUIDNotation:
    core = match.group("core_braced") or match.group("core_plain")
    compact = re.sub(r"-", "", core).lower()
    hyphenated = (
        f"{compact[:8]}-{compact[8:12]}-{compact[12:16]}"
        f"-{compact[16:20]}-{compact[20:]}"
    )
    if compact == "0" * 32:
        version = "nil"
    elif compact == "f" * 32:
        version = "max"
    else:
        version = compact[12]
    return UUIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        urn=f"urn:uuid:{hyphenated}",
        version=version,
    )


class UUIDRecognitionGrammar(PipelineGrammar[UUIDNotation]):
    """Recognizes hyphenated/bare/braced/URN UUID mentions, any case.

    Emits the as-written mention (carrier included in span); rules own
    structure and canonical-case restoration.

    Examples: "6ba7b810-9dad-11d1-80b4-00c04fd430c8" → full span
              "{6ba7b810-9dad-11d1-80b4-00c04fd430c8}" → span covers braces
              "urn:uuid:6ba7b810-…" → span covers prefix
    Non-examples: 33-hex runs → [] (length guard)
                  "…c8-12" → [] (no truncated-prefix fallback)
                  "x6ba7b810-…" → [] (glued run)
                  "{6ba7b810-…" → [] (unbalanced brace)
    """

    name = "uuid_recognition"
    semantics = "uuid_recognition"
    single_value = True
    pre = StandardPre[UUIDNotation](empty_guard=True)
    regex = RegexStage[UUIDNotation](pattern=_UUID_PATTERN, notation_fn=_uuid_notation)
