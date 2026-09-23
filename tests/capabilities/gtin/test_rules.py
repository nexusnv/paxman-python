"""Tests for GTIN rules (three publications)."""

from types import SimpleNamespace
from typing import cast

import pytest

from paxman.capabilities.GTIN.contract import GTINContract
from paxman.capabilities.GTIN.notation import GTINNotation
from paxman.capabilities.GTIN.rules.data import verified_snapshot
from paxman.capabilities.GTIN.rules.gs1_genspecs_ed2026 import (
    Section1GtinStructureCheckDigit,
)
from paxman.capabilities.GTIN.rules.gs1_genspecs_ed2026 import (
    _gs1_mod10_is_valid as _genspecs_mod10,
)
from paxman.capabilities.GTIN.rules.gs1_prefix_ed2026 import (
    Section2Gs1Prefix,
    _prefix_allocated,
)
from paxman.capabilities.GTIN.rules.gs1_prefix_ed2026 import (
    _gs1_mod10_is_valid as _prefix_mod10,
)
from paxman.capabilities.GTIN.rules.verified_by_gs1_ed2019 import (
    Section3VerifiedLiveness,
)
from paxman.capabilities.GTIN.rules.verified_by_gs1_ed2019 import (
    _gs1_mod10_is_valid as _verified_mod10,
)
from paxman.core.domain import RuleStrategy


def _n(digits: str, has_ai: bool = False) -> GTINNotation:
    return GTINNotation(digits=digits, native_length=len(digits), has_ai=has_ai)


@pytest.mark.capability
class TestParser:
    def setup_method(self) -> None:
        self.rule = Section1GtinStructureCheckDigit()
        self.contract = GTINContract()

    def test_parser_valid_all_lengths(self) -> None:
        for v in [
            "96385074",  # GTIN-8
            "614141999996",  # GTIN-12 (UPC-A flagship)
            "5012345670003",  # GTIN-13 (EAN-13)
            "10614141999993",  # GTIN-14 (indicator 1)
            "03453120000011",  # padded GTIN-13
            "00196618007309",  # padded GTIN-12
            "6291041500213",  # GTIN-13
            "9780471117094",  # Bookland GTIN-13
            "2061414199993",  # GTIN-13 (prefix 206 restricted)
            "05901234123457",  # padded GTIN-13 (GS1 Poland)
            "00000096385074",  # padded GTIN-8
        ]:
            assert self.rule.matches(_n(v), self.contract) is True, v
        # Padding invariance: native and zero-padded spellings both valid.
        assert self.rule.matches(_n("5901234123457"), self.contract) is True

    def test_parser_bad_check(self) -> None:
        assert self.rule.matches(_n("614141999997"), self.contract) is False

    def test_parser_wrong_length_nonascii(self) -> None:
        assert self.rule.matches(_n("614141999"), self.contract) is False
        assert self.rule.matches(_n("6141419999O"), self.contract) is False
        assert self.rule.matches(_n("６１４１４１９９９９９６"), self.contract) is False

    def test_provenance_attrs(self) -> None:
        assert self.rule.name == "Section 1-gtin-structure-check-digit"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.provenance.authority == "GS1"
        assert self.rule.provenance.kind == "specification"
        assert self.rule.provenance.version == "26.0"
        assert self.rule.target_semantics == frozenset({"gtin_recognition"})
        assert self.rule.requires_features == frozenset()

    def test_no_output_format_token(self) -> None:
        import pathlib

        for f in [
            "paxman/capabilities/GTIN/rules/gs1_genspecs_ed2026.py",
            "paxman/capabilities/GTIN/rules/gs1_prefix_ed2026.py",
            "paxman/capabilities/GTIN/rules/verified_by_gs1_ed2019.py",
        ]:
            assert "output_format" not in pathlib.Path(f).read_text()


@pytest.mark.capability
class TestLookupPrefix:
    def setup_method(self) -> None:
        self.rule = Section2Gs1Prefix()
        self.contract = GTINContract()

    def test_lookup_valid_prefix(self) -> None:
        # Every suite vector's native prefix resolves to an MO row. The key
        # is derived from the zero-stripped view: 8 -> [:3] (962 -> [:4]),
        # 12 -> "0"+[:2] (EAN-13 view of UPC-A), 13 -> [:3], 14 -> [1:4].
        for v in [
            "5012345670003",  # 13 -> 501 (GS1 UK)
            "96385074",  #  8 -> 963 (GS1 Global Office GTIN-8)
            "614141999996",  # 12 -> 061 (GS1 US; UPC-A = EAN-13 view)
            "10614141999993",  # 14 -> 061 (skip indicator 1)
            "03453120000011",  # 14 -> 345 (GS1 France; zero-strip -> 13)
            "00196618007309",  # 14 -> 019 (GS1 US; zero-strip -> 12)
            "6291041500213",  # 13 -> 629 (GS1 UAE)
            "9780471117094",  # 13 -> 978 (Bookland)
            "2061414199993",  # 13 -> 206 (restricted circulation)
            "05901234123457",  # 14 -> 590 (GS1 Poland; zero-strip -> 13)
            "05012345670003",  # 14 -> 501 (GS1 UK; zero-strip -> 13)
            "00000096385074",  # 14 -> 963 (zero-strip -> 8, GTIN-8 view)
        ]:
            assert self.rule.matches(_n(v), self.contract) is True, v

    def test_lookup_miss_unallocated(self) -> None:
        # 999 stays the miss fixture (the 990-999 coupon block is excluded).
        assert self.rule.matches(_n("9991414199996"), self.contract) is False

    def test_lookup_upca_ean13_view(self) -> None:
        # UPC-A 614141999996 carries prefix 061 (GS1 US), not 614 (GS1
        # Global Office "future MO" / unallocated). The 12-digit view is
        # the EAN-13 with a prepended zero.
        assert self.rule.matches(_n("614141999996"), self.contract) is True

    def test_lookup_native_not_padded(self) -> None:
        # 05012345670003 is the padded spelling of 5012345670003. The rule
        # must test the NATIVE prefix 501 (GS1 UK), never the padded-view
        # prefix 050 (GS1 US reserved -> unallocated).
        n = GTINNotation(digits="05012345670003", native_length=14, has_ai=False)
        assert self.rule.matches(n, self.contract) is True
        # Counter-proof: 050 itself is unallocated, so a rule that tested
        # the padded view would MISS here.
        from paxman.capabilities.GTIN.rules.data.gs1_prefix import GS1_MO_RANGES

        assert not any(s <= 50 <= e for s, e, _ in GS1_MO_RANGES)

    def test_lookup_gtin8_four_char(self) -> None:
        # 962 spans three MOs (9620-9624 UK, 9625-9626 Poland, 9627-9629
        # Global Office), so it is excluded from the 3-char MO ranges and
        # resolved at 4 chars. A Mod-10-valid GTIN-8 on 9620 matches only
        # if the rule performs the 4-char lookup (3-char 962 is a miss).
        assert self.rule.matches(_n("96201237"), self.contract) is True
        from paxman.capabilities.GTIN.rules.data.gs1_prefix import (
            GS1_GTIN8_EXCEPTIONS,
        )

        assert "9620" in GS1_GTIN8_EXCEPTIONS
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.provenance.kind == "registry"

    def test_normalize_agreement(self) -> None:
        parser = Section1GtinStructureCheckDigit()
        verified = Section3VerifiedLiveness()
        for v in ["5012345670003", "96385074", "10614141999993"]:
            n = _n(v)
            assert parser.normalize(n, self.contract) == n.digits.rjust(14, "0")
            assert self.rule.normalize(n, self.contract) == n.digits.rjust(14, "0")
            assert verified.normalize(n, self.contract) == n.digits.rjust(14, "0")

    def test_strategy_six_attrs(self) -> None:
        assert self.rule.name == "Section 2-gs1-prefix"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"gtin_recognition"})
        assert self.rule.requires_features == frozenset()


@pytest.mark.capability
class TestVerifiedGate:
    def setup_method(self) -> None:
        self.rule = Section3VerifiedLiveness()

    def test_verified_gate_off_dropped(self) -> None:
        # Default contract (include_verified=False) drops this rule via
        # requires_features — engine-level gating, not matches().
        assert self.rule.requires_features == frozenset({"include_verified"})
        assert self.rule.provenance.kind == "registry"

    def test_verified_gate_on_absent_invalid(self) -> None:
        contract = GTINContract(include_verified=True)
        assert (
            self.rule.matches(_n("5012345670003"), contract) is False
        )  # empty snapshot

    def test_verified_gate_on_present_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            verified_snapshot, "ISSUED_GTINS", frozenset({"05012345670003"})
        )
        contract = GTINContract(include_verified=True)
        assert self.rule.matches(_n("5012345670003"), contract) is True


class TestDefensiveGuards:
    """Guard branches the grammar makes unreachable (defensive depth).

    Recognition only emits well-shaped notations, so these guards never
    fire in the pipeline; direct calls pin them down so every rule module
    carries full branch coverage of its own checks.
    """

    def setup_method(self) -> None:
        self.parser = Section1GtinStructureCheckDigit()
        self.prefix = Section2Gs1Prefix()
        self.verified = Section3VerifiedLiveness()
        self.contract = GTINContract()

    def test_mod10_helpers_reject_single_char(self) -> None:
        # len < 2 short-circuit in each rule file's local helper copy.
        assert _genspecs_mod10("") is False
        assert _prefix_mod10("7") is False
        assert _verified_mod10("0") is False

    def test_non_str_digits_rejected(self) -> None:
        fake = cast(
            GTINNotation,
            SimpleNamespace(digits=12345678, native_length=8, has_ai=False),
        )
        assert self.parser.matches(fake, self.contract) is False
        assert self.prefix.matches(fake, self.contract) is False
        assert self.verified.matches(fake, self.contract) is False

    def test_native_length_mismatch_rejected(self) -> None:
        mismatched = GTINNotation(digits="614141999996", native_length=11, has_ai=False)
        assert self.parser.matches(mismatched, self.contract) is False
        assert self.prefix.matches(mismatched, self.contract) is False
        assert self.verified.matches(mismatched, self.contract) is False

    def test_wrong_length_rejected_by_prefix_and_verified(self) -> None:
        assert self.prefix.matches(_n("614141999"), self.contract) is False
        assert self.verified.matches(_n("614141999"), self.contract) is False

    def test_non_digit_rejected_by_prefix_and_verified(self) -> None:
        alpha = _n("61414199999A")
        assert self.prefix.matches(alpha, self.contract) is False
        assert self.verified.matches(alpha, self.contract) is False

    def test_verified_mod10_failure_rejected(self) -> None:
        assert self.verified.matches(_n("614141999997"), self.contract) is False

    def test_prefix_key_paths_on_unreachable_inputs(self) -> None:
        # "00012": zero-stripping leaves a non-GTIN length → as-spelled
        # fallback, then a None key. "abcdefgh": non-numeric key hits the
        # int() ValueError guard. Both are grammar-unreachable shapes.
        assert _prefix_allocated("00012") is False
        assert _prefix_allocated("abcdefgh") is False

    def test_prefix_rule_checks_mod10_before_lookup(self) -> None:
        # A failed check digit short-circuits before the prefix table.
        assert self.prefix.matches(_n("614141999997"), self.contract) is False
