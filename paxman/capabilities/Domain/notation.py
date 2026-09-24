"""Domain notation — the intermediate token for hostname mentions.

A notation pairs the verbatim span text with the mapped label tuple: ``raw``
is the matched substring unchanged (original case, original trailing dot);
``labels`` is the UTS #46 mapped, NFC-normalized tuple with one trailing
empty label stripped; ``tld`` is the last mapped label. There is deliberately
no ``canonical`` field — the canonical A-label form is built by ``finalize()``
inside each rule's ``normalize()`` (encode-in-resolution), so every rule
shares one encoding path.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainNotation:
    """Span text plus mapped labels for one hostname mention.

    Vocabulary follows RFC 5890 §2.3: ``labels`` holds U-labels (Unicode,
    mapped) or LDH labels; the A-label (ASCII-compatible encoded) form is
    derived, never stored.
    """

    raw: str
    labels: tuple[str, ...]
    tld: str
