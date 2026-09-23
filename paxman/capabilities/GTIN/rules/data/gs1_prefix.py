"""GS1 Prefix MO ranges (projection of the GS1 company-prefix list).

Source: GS1 Global Office company-prefix page
(https://www.gs1.org/standards/id-keys/company-prefix) — primary fetch was
403/WAF at research time (2026-09-22), so ranges below are projected from the
secondary census (Wikipedia List of GS1 country codes, 2026-09-10 revision,
itself sourced from the GS1 prefix list; cross-checked against
activebarcode.com GS1-prefix table). Per-row comments carry the MO origin.

KEYING NOTE (see rules/gs1_prefix_ed2026.py): rows are 3-digit prefixes read
in the EAN-13 view. A 12-digit UPC-A is the EAN-13 view with a prepended
zero, so the rule keys UPC-A `614...` at `061` (GS1 US) — never at the
as-spelled `614`. A 14-digit GTIN skips its packaging indicator
(`106...` -> `061`), and padded spellings are zero-stripped first
(`05901234123457` -> 590; `00000096385074` -> 963).

SUB-RANGE / EXCLUSION NOTES:
  - `000` is GS1-reserved rather than MO-allocated (internal-use
    sub-ranges 0001-0009 and 0000001-0000009), so it is intentionally
    absent: a native prefix of 000 misses. Never hand-invent rows.
  - 614 and 623 are unallocated (GS1 "future MO" blocks; Wikipedia
    2026-09-10 omits them) — 614 is a genuinely different prefix from the
    UPC-A flagship's EAN-13-view key 061. 622 is allocated (GS1 Egypt) and
    present as its own row.
  - 981-984 are allocated (GS1 Global Office common-currency coupons).
    990-999 appears in no consulted source as an allocated MO range, so it
    stays out — that is what makes 999 the unallocated miss fixture. Add
    it only if the primary list allocates it (add-only, step 1).

Allocated-reserved gaps (050-059 future use, unlisted 3-digit blocks like
610/614/623 future-MO, 951-952 EPC/demo) are INTENTIONALLY ABSENT: a native
prefix falling in a gap is INVALID (prefix miss fixture: 999).

REFRESH PROCEDURE (confirm full list, add-only for allocated ranges):
  1. Retry the gs1.org primary
     (https://www.gs1.org/standards/id-keys/company-prefix). If reachable,
     reconcile every row below against it; add newly allocated ranges with
     per-row MO comments; NEVER delete an allocated range (prefixes are
     never deallocated — licensees keep minting GTINs on retired blocks).
  2. Cross-check 200-299 / 020-029 / 040-049 restricted-circulation ranges
     (valid GS1-issued, not MO-allocated — always-active LOOKUP accepts
     them; 999 / reserved gaps stay INVALID).
  3. Confirm GTIN-8 carve-outs (960-961 UK, 9620-9624 UK, 9625-9626 Poland,
     9627-969 Global Office) — 962 prefix is ambiguous at 3 chars, so it is
     EXCLUDED from MO ranges and resolved via GS1_GTIN8_EXCEPTIONS (4-char).
  4. Re-run tests/capabilities/gtin/test_data.py (suite prefixes resolve).
"""

from __future__ import annotations

# (start, end, MO) — 3-digit GS1 prefixes, sorted, non-overlapping.
# Restricted-circulation ranges (020-029 region, 040-049 company, 200-299
# region) are GS1-issued and accepted (kills random-digit false positives
# while admitting internal-use GTINs like the 206 indicator-2 vector).
GS1_MO_RANGES: tuple[tuple[int, int, str], ...] = (
    (1, 19, "GS1 US"),  # 001-019 UPC-A compatible
    (20, 29, "Restricted circulation (region)"),  # GS1 restricted
    (30, 39, "GS1 US (drugs/NDC)"),  # 030-039 US drugs
    (40, 49, "Restricted circulation (company)"),  # GS1 restricted
    (60, 139, "GS1 US"),  # 060-099 + 100-139 UPC-A compatible + US
    (200, 299, "Restricted circulation (region)"),  # GS1 restricted
    (300, 379, "GS1 France (incl. Monaco)"),  # 300-379
    (380, 380, "GS1 Bulgaria"),  # 380
    (381, 381, "GS1 Kosovo"),  # 381 (ex-390 unofficial)
    (383, 383, "GS1 Slovenia"),  # 383
    (385, 385, "GS1 Croatia"),  # 385
    (387, 387, "GS1 Bosnia-Herzegovina"),  # 387
    (389, 389, "GS1 Montenegro"),  # 389
    (400, 440, "GS1 Germany"),  # 400-440 (440 ex-East Germany)
    (450, 459, "GS1 Japan (new JAN)"),  # 450-459
    (460, 469, "GS1 Russia"),  # 460-469 (ex-Soviet)
    (470, 470, "GS1 Kyrgyzstan"),  # 470
    (471, 471, "GS1 Taiwan"),  # 471
    (474, 474, "GS1 Estonia"),  # 474
    (475, 475, "GS1 Latvia"),  # 475
    (476, 476, "GS1 Azerbaijan"),  # 476
    (477, 477, "GS1 Lithuania"),  # 477
    (478, 478, "GS1 Uzbekistan"),  # 478
    (479, 479, "GS1 Sri Lanka"),  # 479
    (480, 480, "GS1 Philippines"),  # 480
    (481, 481, "GS1 Belarus"),  # 481
    (482, 482, "GS1 Ukraine"),  # 482
    (483, 483, "GS1 Turkmenistan"),  # 483
    (484, 484, "GS1 Moldova"),  # 484
    (485, 485, "GS1 Armenia"),  # 485
    (486, 486, "GS1 Georgia"),  # 486
    (487, 487, "GS1 Kazakhstan"),  # 487
    (488, 488, "GS1 Tajikistan"),  # 488
    (489, 489, "GS1 Hong Kong"),  # 489
    (490, 499, "GS1 Japan (orig JAN)"),  # 490-499
    (500, 509, "GS1 UK"),  # 500-509
    (520, 521, "GS1 Greece"),  # 520-521
    (528, 528, "GS1 Lebanon"),  # 528
    (529, 529, "GS1 Cyprus"),  # 529
    (530, 530, "GS1 Albania"),  # 530
    (531, 531, "GS1 North Macedonia"),  # 531
    (535, 535, "GS1 Malta"),  # 535
    (539, 539, "GS1 Ireland"),  # 539
    (540, 549, "GS1 Belgium/Luxembourg"),  # 540-549
    (560, 560, "GS1 Portugal"),  # 560
    (569, 569, "GS1 Iceland"),  # 569
    (570, 579, "GS1 Denmark (incl. Faroes/Greenland)"),  # 570-579
    (590, 590, "GS1 Poland"),  # 590
    (594, 594, "GS1 Romania"),  # 594
    (599, 599, "GS1 Hungary"),  # 599
    (600, 601, "GS1 South Africa"),  # 600-601
    (602, 602, "GS1 Benin"),  # 602 (activebarcode; post-2021 allocation)
    (603, 603, "GS1 Ghana"),  # 603
    (604, 604, "GS1 Senegal"),  # 604
    (605, 605, "GS1 Uganda"),  # 605 (Wikipedia 2026-09)
    (606, 606, "GS1 Angola"),  # 606 (Wikipedia 2026-09)
    (607, 607, "GS1 Oman"),  # 607 (Wikipedia 2026-09)
    (608, 608, "GS1 Bahrain"),  # 608
    (609, 609, "GS1 Mauritius"),  # 609
    (611, 611, "GS1 Morocco"),  # 611
    (612, 612, "GS1 Somalia"),  # 612 (Wikipedia 2026-09)
    (613, 613, "GS1 Algeria"),  # 613
    (615, 615, "GS1 Nigeria"),  # 615
    (616, 616, "GS1 Kenya"),  # 616
    (617, 617, "GS1 Cameroon"),  # 617 (Wikipedia 2026-09)
    (618, 618, "GS1 Ivory Coast"),  # 618
    (619, 619, "GS1 Tunisia"),  # 619
    (620, 620, "GS1 Tanzania"),  # 620
    (621, 621, "GS1 Syria"),  # 621
    (622, 622, "GS1 Egypt"),  # 622
    (624, 624, "GS1 Libya"),  # 624
    (625, 625, "GS1 Jordan"),  # 625
    (626, 626, "GS1 Iran"),  # 626
    (627, 627, "GS1 Kuwait"),  # 627
    (628, 628, "GS1 Saudi Arabia"),  # 628
    (629, 629, "GS1 UAE"),  # 629
    (630, 630, "GS1 Qatar"),  # 630
    (631, 631, "GS1 Namibia"),  # 631
    (632, 632, "GS1 Rwanda"),  # 632
    (640, 649, "GS1 Finland"),  # 640-649
    (680, 681, "GS1 China"),  # 680-681
    (690, 699, "GS1 China"),  # 690-699
    (700, 709, "GS1 Norway"),  # 700-709
    (729, 729, "GS1 Israel"),  # 729
    (730, 739, "GS1 Sweden"),  # 730-739
    (740, 740, "GS1 Guatemala"),  # 740
    (741, 741, "GS1 El Salvador"),  # 741
    (742, 742, "GS1 Honduras"),  # 742
    (743, 743, "GS1 Nicaragua"),  # 743
    (744, 744, "GS1 Costa Rica"),  # 744
    (745, 745, "GS1 Panama"),  # 745
    (746, 746, "GS1 Dominican Republic"),  # 746
    (750, 750, "GS1 Mexico"),  # 750
    (754, 755, "GS1 Canada"),  # 754-755
    (759, 759, "GS1 Venezuela"),  # 759
    (760, 769, "GS1 Switzerland/Liechtenstein"),  # 760-769
    (770, 771, "GS1 Colombia"),  # 770-771
    (773, 773, "GS1 Uruguay"),  # 773
    (775, 775, "GS1 Peru"),  # 775
    (777, 777, "GS1 Bolivia"),  # 777
    (778, 779, "GS1 Argentina"),  # 778-779
    (780, 780, "GS1 Chile"),  # 780
    (784, 784, "GS1 Paraguay"),  # 784
    (786, 786, "GS1 Ecuador"),  # 786
    (789, 790, "GS1 Brazil"),  # 789-790
    (800, 839, "GS1 Italy (incl. San Marino/Vatican)"),  # 800-839
    (840, 849, "GS1 Spain (incl. Andorra)"),  # 840-849
    (850, 850, "GS1 Cuba"),  # 850
    (858, 858, "GS1 Slovakia"),  # 858
    (859, 859, "GS1 Czechia"),  # 859 (ex-Czechoslovakia)
    (860, 860, "GS1 Serbia"),  # 860 (ex-Yugoslavia)
    (865, 865, "GS1 Mongolia"),  # 865
    (867, 867, "GS1 North Korea"),  # 867
    (868, 869, "GS1 Turkey"),  # 868-869
    (870, 879, "GS1 Netherlands"),  # 870-879
    (880, 881, "GS1 South Korea"),  # 880-881
    (883, 883, "GS1 Myanmar"),  # 883
    (884, 884, "GS1 Cambodia"),  # 884
    (885, 885, "GS1 Thailand"),  # 885
    (887, 887, "GS1 Laos"),  # 887
    (888, 888, "GS1 Singapore"),  # 888
    (890, 890, "GS1 India"),  # 890
    (893, 893, "GS1 Vietnam"),  # 893
    (894, 894, "GS1 Bangladesh"),  # 894
    (896, 896, "GS1 Pakistan"),  # 896
    (899, 899, "GS1 Indonesia"),  # 899
    (900, 919, "GS1 Austria"),  # 900-919
    (930, 939, "GS1 Australia"),  # 930-939
    (940, 949, "GS1 New Zealand"),  # 940-949
    (950, 950, "GS1 Global Office (no-MO territories)"),  # 950
    (955, 955, "GS1 Malaysia"),  # 955
    (958, 958, "GS1 Macau"),  # 958
    (960, 961, "GS1 UK (GTIN-8)"),  # 960-961 GTIN-8 UK
    (963, 969, "GS1 Global Office (GTIN-8)"),  # 963-969 GTIN-8 Global
    (977, 977, "ISSN (serial publications)"),  # 977
    (978, 979, "Bookland (ISBN/ISMN)"),  # 978-979
    (980, 980, "GS1 refund receipts"),  # 980
    (981, 984, "GS1 coupons (common currency)"),  # 981-984
)

# 4-char GTIN-8 exceptions: 962 prefix spans three MOs, so 3-char is
# ambiguous — resolve at 4 chars. 9620-9624 UK, 9625-9626 Poland,
# 9627-9629 Global Office (Wikipedia 2026-09; GS1 prefix list).
GS1_GTIN8_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "9620",  # GS1 UK (GTIN-8)
        "9621",  # GS1 UK (GTIN-8)
        "9622",  # GS1 UK (GTIN-8)
        "9623",  # GS1 UK (GTIN-8)
        "9624",  # GS1 UK (GTIN-8)
        "9625",  # GS1 Poland (GTIN-8)
        "9626",  # GS1 Poland (GTIN-8)
        "9627",  # GS1 Global Office (GTIN-8)
        "9628",  # GS1 Global Office (GTIN-8)
        "9629",  # GS1 Global Office (GTIN-8)
    }
)
