"""Tests for MinorPlanet codec + rules."""

import pytest

from paxman.capabilities.MinorPlanet.contract import MinorPlanetContract
from paxman.capabilities.MinorPlanet.notation import MinorPlanetNotation
from paxman.capabilities.MinorPlanet.rules.mpc_codec import (
    mpc_pack,
    mpc_unpack,
)
from paxman.capabilities.MinorPlanet.rules.mpc_numbering import (
    Section5PermanentNumber,
)
from paxman.capabilities.MinorPlanet.rules.mpc_packed_designation import (
    Section3PackedProvisional,
    Section4PackedNumber,
)
from paxman.capabilities.MinorPlanet.rules.mpc_unpacked_designation import (
    Section1UnpackedProvisionalStructure,
    Section2SurveyDesignation,
)
from paxman.core.domain import RuleStrategy


def _notation(designation: str, form: str, packed: str = "") -> MinorPlanetNotation:
    return MinorPlanetNotation(designation=designation, form=form, packed=packed)


@pytest.mark.capability
class TestSection1Unpacked:
    """DesDoc provisional structure."""

    def setup_method(self) -> None:
        self.rule = Section1UnpackedProvisionalStructure()
        self.contract = MinorPlanetContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 1-unpacked-provisional-structure"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"minor_planet_recognition"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.publication_year == 2026

    @pytest.mark.parametrize(
        "designation",
        ["1995 XA", "2007 TA418", "A904 OA", "A/2017 U1", "1995 XZ"],
    )
    def test_valid(self, designation: str) -> None:
        assert (
            self.rule.matches(_notation(designation, "provisional"), self.contract)
            is True
        )

    @pytest.mark.parametrize("designation", ["1995 XI", "1995 IZ", "1995 XA1X"])
    def test_invalid_letter_slots(self, designation: str) -> None:
        assert (
            self.rule.matches(_notation(designation, "provisional"), self.contract)
            is False
        )

    @pytest.mark.parametrize("designation", ["1995 XA0", "2007 TA05"])
    def test_invalid_leading_zero_cycle(self, designation: str) -> None:
        assert (
            self.rule.matches(_notation(designation, "provisional"), self.contract)
            is False
        )

    def test_off_lane_rejected(self) -> None:
        assert (
            self.rule.matches(_notation("J95X00A", "packed", "J95X00A"), self.contract)
            is False
        )

    def test_normalize(self) -> None:
        assert (
            self.rule.normalize(_notation("1995 XA", "provisional"), self.contract)
            == "1995 XA"
        )


@pytest.mark.capability
class TestSection2Survey:
    """DesDoc survey designations."""

    def setup_method(self) -> None:
        self.rule = Section2SurveyDesignation()
        self.contract = MinorPlanetContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 2-survey-designation"
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"minor_planet_recognition"})

    @pytest.mark.parametrize("designation", ["2040 P-L", "3138 T-1", "1010 T-2"])
    def test_valid(self, designation: str) -> None:
        assert (
            self.rule.matches(_notation(designation, "survey"), self.contract) is True
        )

    def test_invalid_identifier(self) -> None:
        assert (
            self.rule.matches(_notation("2040 P-X", "survey"), self.contract) is False
        )

    def test_normalize(self) -> None:
        assert (
            self.rule.normalize(_notation("2040 P-L", "survey"), self.contract)
            == "2040 P-L"
        )


@pytest.mark.capability
class TestSection3Packed:
    """PackedDes provisional coherence."""

    def setup_method(self) -> None:
        self.rule = Section3PackedProvisional()
        self.contract = MinorPlanetContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 3-packed-provisional"
        assert self.rule.strategy is RuleStrategy.PARSER

    @pytest.mark.parametrize(
        "spelled,canonical",
        [
            ("J95X00A", "1995 XA"),
            ("K07Tf8A", "2007 TA418"),
            ("K99AJ3Z", "2099 AZ193"),
            ("PLS2040", "2040 P-L"),
            ("T1S3138", "3138 T-1"),
        ],
    )
    def test_valid(self, spelled: str, canonical: str) -> None:
        form = (
            "packed"
            if len(spelled) == 7 and spelled[0] != "_"
            else ("survey_packed" if spelled[0] in "PT" else "packed")
        )
        assert (
            self.rule.matches(_notation(spelled, form, spelled), self.contract) is True
        )
        assert (
            self.rule.normalize(_notation(spelled, form, spelled), self.contract)
            == canonical
        )

    @pytest.mark.parametrize("spelled", ["Q95X00A", "J95I00A", "J94P01b"])
    def test_invalid(self, spelled: str) -> None:
        assert (
            self.rule.matches(_notation(spelled, "packed", spelled), self.contract)
            is False
        )


@pytest.mark.capability
class TestSection4PackedNumber:
    """PackedDes number coherence."""

    def setup_method(self) -> None:
        self.rule = Section4PackedNumber()
        self.contract = MinorPlanetContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 4-packed-number"
        assert self.rule.strategy is RuleStrategy.PARSER

    @pytest.mark.parametrize(
        "spelled,canonical",
        [
            ("03202", "(3202)"),
            ("A0345", "(100345)"),
            ("a0017", "(360017)"),
            ("~000z", "(620061)"),
            ("~AZaz", "(3140113)"),
        ],
    )
    def test_valid(self, spelled: str, canonical: str) -> None:
        assert (
            self.rule.matches(
                _notation(spelled, "packed_number", spelled), self.contract
            )
            is True
        )
        assert (
            self.rule.normalize(
                _notation(spelled, "packed_number", spelled), self.contract
            )
            == canonical
        )

    def test_case_trap_distinct(self) -> None:
        assert self.rule.normalize(
            _notation("a0017", "packed_number", "a0017"), self.contract
        ) != self.rule.normalize(
            _notation("A0345", "packed_number", "A0345"), self.contract
        )

    def test_zero_number_rejected(self) -> None:
        assert (
            self.rule.matches(
                _notation("00000", "packed_number", "00000"), self.contract
            )
            is False
        )
        assert mpc_unpack("00000") is None


@pytest.mark.capability
class TestSection5Number:
    """HowNamed permanent numbers."""

    def setup_method(self) -> None:
        self.rule = Section5PermanentNumber()
        self.contract = MinorPlanetContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 5-permanent-number"
        assert self.rule.strategy is RuleStrategy.PARSER

    @pytest.mark.parametrize("designation", ["(433)", "(274301)", "(15396335)"])
    def test_valid(self, designation: str) -> None:
        assert (
            self.rule.matches(_notation(designation, "number"), self.contract) is True
        )

    @pytest.mark.parametrize("designation", ["(0433)", "(0)", "(43a)"])
    def test_invalid(self, designation: str) -> None:
        assert (
            self.rule.matches(_notation(designation, "number"), self.contract) is False
        )

    def test_normalize(self) -> None:
        assert (
            self.rule.normalize(_notation("(433)", "number"), self.contract) == "(433)"
        )


@pytest.mark.capability
class TestMpcCodec:
    """Pack/unpack codec — sbpy-parity vectors from PackedDes."""

    def test_tilde_vectors(self) -> None:
        assert mpc_unpack("~0000") == "(620000)"
        assert mpc_unpack("~000z") == "(620061)"
        assert mpc_unpack("~AZaz") == "(3140113)"
        assert mpc_unpack("~zzzz") == "(15396335)"

    def test_packed_number_case_trap(self) -> None:
        assert mpc_unpack("A0345") == "(100345)"
        assert mpc_unpack("a0017") == "(360017)"
        assert mpc_unpack("03202") == "(3202)"
        assert mpc_unpack("K3289") == "(203289)"

    def test_packed_provisional_vectors(self) -> None:
        assert mpc_unpack("J95X00A") == "1995 XA"
        assert mpc_unpack("J95X01L") == "1995 XL1"
        assert mpc_unpack("K07Tf8A") == "2007 TA418"
        assert mpc_unpack("K99AJ3Z") == "2099 AZ193"
        assert mpc_unpack("K08Aa0A") == "2008 AA360"

    def test_survey_packs(self) -> None:
        assert mpc_unpack("PLS2040") == "2040 P-L"
        assert mpc_unpack("T1S3138") == "3138 T-1"
        assert mpc_pack("2040 P-L") == "PLS2040"
        assert mpc_pack("3138 T-1") == "T1S3138"

    def test_pack_roundtrip(self) -> None:
        assert mpc_pack("1995 XA") == "J95X00A"
        assert mpc_pack("2007 TA418") == "K07Tf8A"
        assert mpc_pack("(3202)") == "03202"
        assert mpc_pack("(100345)") == "A0345"
        assert mpc_pack("(360017)") == "a0017"
        assert mpc_pack("(620000)") == "~0000"
        assert mpc_pack("(620061)") == "~000z"

    def test_pack_none_for_a_lane(self) -> None:
        assert mpc_pack("A/2017 U1") is None

    def test_unpack_none_for_incoherent(self) -> None:
        assert mpc_unpack("Q95X00A") is None
        assert mpc_unpack("J95I00A") is None
        assert mpc_unpack("J94P01b") is None


@pytest.mark.capability
class TestMpcCodecRobustness:
    """Defensive branches: malformed input returns None/False, never raises."""

    @pytest.mark.parametrize(
        "spelled",
        [
            "",
            "x",
            "1234",
            "123456",
            "~~~~~",
            "PLS",
            "PLS0000",
            "PLS99999",
            "T9S1234",
            "T1S",
            "_",
            "_qC0000",
            "_QZ0000",
            "_QC00",
            "_QC00000",
            "J95X00a",
            "j95X00A",
            "K328",
            "K32890",
            "~000",
            "~00000",
            "~!!!!",
            "(433",
            "433)",
            "()",
            "(0)",
            "(-1)",
            "A/2017 U1",
            "1995 XA",
            "2040 P-L",
            "00000",
            "٤٥٦٧٨",
            "A٤٥٦٧",
            "123٤5",
        ],
    )
    def test_unpack_garbage_none_or_shaped(self, spelled: str) -> None:
        result = mpc_unpack(spelled)
        assert result is None or isinstance(result, str)

    def test_unpack_non_ascii_digits_none(self) -> None:
        assert mpc_unpack("٤٥٦٧٨") is None
        assert mpc_unpack("A٤٥٦٧") is None
        assert mpc_unpack("123٤5") is None

    def test_unpack_zero_number_none(self) -> None:
        assert mpc_unpack("00000") is None

    @pytest.mark.parametrize(
        "designation",
        [
            "",
            "hello",
            "(0)",
            "()",
            "(433",
            "433)",
            "(43a)",
            "0 P-L",
            "10000 P-L",
            "2040 P-X",
            "1995 XI",
            "1892 XA",
            "2100 XA",
            "1995 X",
            "1995 XA1X",
            "(99999999)",
            "1995 XA0",
            "2007 TA05",
        ],
    )
    def test_pack_garbage_none(self, designation: str) -> None:
        assert mpc_pack(designation) is None

    def test_pack_number_bounds(self) -> None:
        assert mpc_pack("(1)") == "00001"
        assert mpc_pack("(99999)") == "99999"
        assert mpc_pack("(619999)") == "z9999"
        assert mpc_pack("(15396335)") == "~zzzz"
        assert mpc_pack("(15396336)") is None
        assert mpc_pack("(0)") is None

    def test_pack_high_cycle_extended(self) -> None:
        packed = mpc_pack("2026 CA1000")
        assert packed is not None and packed.startswith("_")

    def test_pack_cycle_beyond_extended_none(self) -> None:
        assert mpc_pack("2026 CA99999999") is None
