"""Verified by GS1 snapshot for the GTIN capability (add-only).

Shipped empty: liveness is snapshot-gated, never a live lookup (determinism
mandate — no network inference). A GTIN is "issued/live-registered" only when
its 14-digit canonical form is present in ``ISSUED_GTINS``.

ADD-ONLY REFRESH PROCEDURE:
  1. Query Verified by GS1 / GEPIR for the brand-owner GTIN set under test
     (6 brand-owner attributes exposed: brand, description, image, GPC, net
     content, country of sale — snapshot a boolean liveness subset only,
     never PII).
  2. Normalize every issued GTIN to 14-digit zero-padded canonical
     (``digits.rjust(14, "0")``) and UNION into ``ISSUED_GTINS`` below.
  3. NEVER delete an entry (GTINs survive brand-owner changes; allocation
     is permanent per GTIN Management Rules). Record the census date/count
     in a comment.
  4. Re-run tests/capabilities/gtin/test_data.py
     (``ISSUED_GTINS == frozenset()`` must be updated to the new census
     only when shipping a populated snapshot — v1 ships empty).

CENSUS PROVENANCE: v1 ships empty (no verified GTINs bundled).
"""

from __future__ import annotations

# 14-digit canonical GTINs known issued/live-registered (add-only; v1 empty).
ISSUED_GTINS: frozenset[str] = frozenset()
