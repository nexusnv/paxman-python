"""Golden-vector parity for CountryNameFold — single-pass NFD must preserve triple.

Frozen snapshot captured from pre-rewrite impl (per-char NFD) on 2026-08-26.
Any deviation after whole-string NFD rewrite is a regression.
"""

from paxman.core.grammar.normalizers import CountryNameFold

# (input, expected_subject, expected_starts, expected_ends)
_VECTORS: tuple[
    tuple[str, str, tuple[int, ...] | None, tuple[int, ...] | None], ...
] = (
    (
        "Côte d'Ivoire",
        "cote divoire",
        (0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12),
        (1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13),
    ),
    (
        "São Tomé and Príncipe",
        "sao tome and principe",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21),
    ),
    ("Curaçao", "curacao", (0, 1, 2, 3, 4, 5, 6), (1, 2, 3, 4, 5, 6, 7)),
    ("Réunion", "reunion", (0, 1, 2, 3, 4, 5, 6), (1, 2, 3, 4, 5, 6, 7)),
    (
        "Åland Islands",
        "aland islands",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
    ),
    ("Kyrgyzstan", "kyrgyzstan", None, None),
    ("Éire", "eire", (0, 1, 2, 3), (1, 2, 3, 4)),
    (
        "naïve café",
        "naive cafe",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
    ),
    ("日本", "日本", None, None),
    ("中国", "中国", None, None),
    (
        "대한민국",
        "대한민국",
        (0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3),
        (1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4),
    ),
    ("CJK test 日本 中国", "cjk test 日本 中国", None, None),
    (
        "Guinea-Bissau",
        "guinea bissau",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
    ),
    (
        "Guinea--Bissau",
        "guinea bissau",
        (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13),
        (1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14),
    ),
    (
        "Guinea///Bissau",
        "guinea bissau",
        (0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14),
        (1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15),
    ),
    (
        "Guinea\u2013Bissau",
        "guinea bissau",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
    ),
    (
        "St. Helena",
        "st helena",
        (0, 1, 3, 4, 5, 6, 7, 8, 9),
        (1, 2, 4, 5, 6, 7, 8, 9, 10),
    ),
    ("U.S.A.", "usa", (0, 2, 4), (1, 3, 5)),
    ("!!!", "", (), ()),
    ("---", " ", (0,), (1,)),
    ("a---b///c", "a b c", (0, 1, 4, 5, 8), (1, 2, 5, 6, 9)),
    (
        "United   States",
        "united states",
        (0, 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14),
        (1, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15),
    ),
    (
        "United\tStates",
        "united states",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
    ),
    (
        "  United States  ",
        " united states ",
        (0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15),
        (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16),
    ),
    ("a  b   c    d", "a b c d", (0, 1, 3, 4, 7, 8, 12), (1, 2, 4, 5, 8, 9, 13)),
    (
        " Côte   d'Ivoire--Guinea/Bissau  ",
        " cote divoire guinea bissau ",
        (
            0,
            1,
            2,
            3,
            4,
            5,
            8,
            10,
            11,
            12,
            13,
            14,
            15,
            16,
            18,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
        ),
        (
            1,
            2,
            3,
            4,
            5,
            6,
            9,
            11,
            12,
            13,
            14,
            15,
            16,
            17,
            19,
            20,
            21,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            29,
            30,
            31,
            32,
        ),
    ),
    (
        "São   Tomé---and   Príncipe!!!",
        "sao tome and principe",
        (0, 1, 2, 3, 6, 7, 8, 9, 10, 13, 14, 15, 16, 19, 20, 21, 22, 23, 24, 25, 26),
        (1, 2, 3, 4, 7, 8, 9, 10, 11, 14, 15, 16, 17, 20, 21, 22, 23, 24, 25, 26, 27),
    ),
    (
        "  Åland   Islands  ",
        " aland islands ",
        (0, 2, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17),
        (1, 3, 4, 5, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18),
    ),
    ("a\u0301 b\u0301 c", "a b c", (0, 2, 3, 5, 6), (1, 3, 4, 6, 7)),
    ("123 United States 456", "123 united states 456", None, None),
    ("", "", (), ()),
    (" ", " ", None, None),
    ("a", "a", None, None),
    ("é", "e", (0,), (1,)),
    ("\u2013", " ", (0,), (1,)),
    (
        "Hello-World/Test\u2013Foo",
        "hello world test foo",
        (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19),
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20),
    ),
)


def test_country_name_fold_golden_vectors() -> None:
    nf = CountryNameFold()
    for text, exp_subject, exp_starts, exp_ends in _VECTORS:
        subject, starts, ends = nf.normalize(text)
        assert subject == exp_subject, (
            f"subject mismatch for {text!r}: {subject!r} != {exp_subject!r}"
        )
        assert starts == exp_starts, (
            f"starts mismatch for {text!r}: {starts} != {exp_starts}"
        )
        assert ends == exp_ends, f"ends mismatch for {text!r}: {ends} != {exp_ends}"
