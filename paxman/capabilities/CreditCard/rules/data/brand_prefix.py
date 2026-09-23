"""Brand IIN prefix allowlist — SECONDARY evidence, never ISO authority.

Each row is ``(prefix_intervals, allowed_lengths)`` where a prefix interval
is ``(start, end, width)`` — the inclusive integer interval read over the
first ``width`` digits of the compact PAN (width carried explicitly because
a 1-digit ``4`` and a 2-digit ``65`` collide as raw integers).

SECONDARY status: this table is seeded from secondary synthesis (the
Payment card number reference table cross-checked against per-network brand
specs). It never ISO-authoritative: the ISO/IEC structure+Luhn rule owns
validity, this allowlist only membership-checks a gated secondary rule.
Absence of a prefix here says nothing about PAN validity — a PAN whose
prefix is absent is generic-valid with the brand gate off and brand-invalid
with the gate on.

REFRESH procedure: brands change ranges — re-verify each brand's prefix and
length rows against its own published brand specification before adding or
editing rows, record the change in the capability's citation surface, and
re-run the credit_card suite (the seed vectors are pinned there).

DEFERRED "Others" row: Mir (2200-2204), RuPay (60/65/81/82/508), Troy
(9792/65), UATP (1/15) and friends are deliberately deferred — they are
absent from this allowlist by decision, not by oversight. Consequently an
otherwise-valid PAN of a deferred brand fails membership when the gate is
on (documented, decision 6).
"""

from __future__ import annotations

# brand key -> (prefix intervals [(start, end, width)...], allowed lengths)
BRAND_PREFIXES: dict[str, tuple[tuple[tuple[int, int, int], ...], frozenset[int]]] = {
    "visa": (
        ((4, 4, 1),),
        frozenset({13, 16, 19}),
    ),
    "mastercard": (
        ((51, 55, 2), (2221, 2720, 4)),
        frozenset({16}),
    ),
    "american-express": (
        ((34, 34, 2), (37, 37, 2)),
        frozenset({15}),
    ),
    "discover": (
        ((6011, 6011, 4), (644, 649, 3), (65, 65, 2), (622126, 622925, 6)),
        frozenset({16, 17, 18, 19}),
    ),
    "diners-club": (
        ((30, 30, 2), (36, 36, 2), (38, 38, 2), (39, 39, 2), (300, 305, 3)),
        frozenset({14, 15, 16, 17, 18, 19}),
    ),
    "jcb": (
        ((3528, 3589, 4), (2131, 2131, 4), (1800, 1800, 4)),
        frozenset({16, 17, 18, 19}),
    ),
    "china-unionpay": (
        ((62, 62, 2), (81, 81, 2)),
        frozenset({16, 17, 18, 19}),
    ),
    "maestro": (
        (
            (5018, 5018, 4),
            (5020, 5020, 4),
            (5038, 5038, 4),
            (5893, 5893, 4),
            (6304, 6304, 4),
            (6759, 6759, 4),
            (6761, 6763, 4),
        ),
        frozenset({12, 13, 14, 15, 16, 17, 18, 19}),
    ),
}
