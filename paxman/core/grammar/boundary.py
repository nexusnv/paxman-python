"""BoundaryGuard family — parameterized lookarounds replacing 10 distinct literals.

Each guard produces a compiled alternation-ready regex via `wrap(alternation)`,
or exposes its `(lookbehind, lookahead)` pair for `LexiconStage` injection.
No grammar file hard-codes a lookaround literal after migration — each grammar
references a `BoundaryGuard` instance (ADR-0009 §10).

Legacy path: BoundaryGuard for RegexStage/LexiconStage; kernel path: BoundarySpec
declarative checks. Unmigrated grammars still reference guards; §10 target is
guard-free kernel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BoundaryGuard:
    """A parameterized boundary guard producing lookaround-wrapped patterns."""

    lookbehind: str
    lookahead: str

    def wrap(self, alternation: str, flags: int = 0) -> re.Pattern[str]:
        """Wrap an alternation with this guard's lookarounds and compile.

        Args:
            alternation: The escaped ``|``-joined token alternation.
            flags: Optional ``re`` flags (e.g. ``re.IGNORECASE``) passed to
                ``re.compile`` so case-insensitive lexicon grammars (Currency
                word, Money word) preserve the old ``re.IGNORECASE`` behavior.
        """
        return re.compile(rf"{self.lookbehind}(?:{alternation}){self.lookahead}", flags)

    # Factory constructors — one per distinct semantic variant.
    @classmethod
    def word_sign(cls) -> BoundaryGuard:
        return cls(lookbehind=r"(?<![\w\-+\u2212])", lookahead=r"(?![\w\-+\u2212])")

    @classmethod
    def degree_word_sign(cls) -> BoundaryGuard:
        # SIUnit degree prefix: ° must be preserved in the lookbehind.
        return cls(
            lookbehind=r"(?<![°\w\-+\u2212/·⋅])", lookahead=r"(?![\w\-+\u2212/·⋅])"
        )

    @classmethod
    def digit(cls) -> BoundaryGuard:
        return cls(lookbehind=r"(?<!\d)", lookahead=r"(?!\d)")

    @classmethod
    def word_only(cls) -> BoundaryGuard:
        return cls(lookbehind=r"(?<!\w)", lookahead=r"(?!\w)")

    @classmethod
    def e164(cls) -> BoundaryGuard:
        return cls(lookbehind=r"(?<![\w:.])", lookahead=r"")

    @classmethod
    def e164_00(cls) -> BoundaryGuard:
        """International 00-prefix: like e164() but also excludes a leading "+".

        Contradictory "+00..." input is left to the e164 grammar; the 00
        grammar must not treat it as a 00-prefixed number.
        """
        return cls(lookbehind=r"(?<![\w:.+])", lookahead=r"")

    @classmethod
    def scheme_char(cls) -> BoundaryGuard:
        return cls(lookbehind=r"(?<![A-Za-z0-9+.\-])", lookahead=r"")

    @classmethod
    def phone_national(cls) -> BoundaryGuard:
        # 4-lookbehind chain: blocks a national number that is itself preceded
        # by a digit/+, a separator, an opening paren, or a digit/paren pair.
        return cls(
            lookbehind=(
                r"(?<![\d+])"
                r"(?<![\d+][\s.\-])"
                r"(?<![\d+][\s.\-]\()"
                r"(?<![\d+]\()"
            ),
            lookahead=r"(?!\d)",
        )

    @classmethod
    def mac_midrun(cls) -> BoundaryGuard:
        # MAC address guard: word_only plus rejection of a claim start
        # preceded by hex + separator — the tail of a longer colon/hyphen
        # run ("00:1A:2B:3C:4D:5E:66" must not yield "1A:2B:3C:4D:5E:66").
        # Plain word_only treats ':'/'-'/'.' as boundaries; the second
        # stacked lookbehind closes that gap (phone_national() precedent).
        return cls(lookbehind=r"(?<!\w)(?<![0-9A-Fa-f][-.:])", lookahead=r"(?!\w)")

    @classmethod
    def ipv6_token(cls) -> BoundaryGuard:
        # Token boundary for IPv6: start/end of string or a delimiter class.
        # NOTE: Unlike the other guards, this is a *consuming* anchor pair
        # (``(?:^|(?<=...))`` / ``(?:$|(?=...))``) rather than a zero-width
        # lookaround. It cannot be used interchangeably with
        # LexiconStage.wrap's lookaround mental model; it is a token
        # delimiter for RegexStage only. Parity-proven against the legacy
        # ``(?:^|(?<=[\\s,;([ ]))`` / ``(?:$|(?=[\\s,;().\\]]))`` idiom.
        return cls(
            lookbehind=r"(?:^|(?<=[\s,;([ ]))",
            lookahead=r"(?:$|(?=[\s,;().\]]))",
        )

    @classmethod
    def isbn_trail(cls) -> BoundaryGuard:
        # Trailing guard for ISBN-13/ISBN-10: the address must not be
        # immediately preceded by a separator (whitespace, colon, hyphen),
        # which would mean it is glued to surrounding label text.
        return cls(lookbehind=r"(?<![\s:-])", lookahead=r"")

    @classmethod
    def isbn10_lead(cls) -> BoundaryGuard:
        # Leading guard for ISBN-10: the address must not be immediately
        # preceded by a digit or a digit followed by a separator, which would
        # mean it is glued to surrounding digits (e.g. an ID run).
        return cls(lookbehind=r"(?<!\d)(?<!\d[ -])", lookahead=r"")
