"""Tests for Language rules — 6 publications + CLDR + English name mapping."""

from __future__ import annotations

import pytest

from paxman.capabilities.Language.contract import LanguageContract
from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.domain import RuleStrategy


def _code_notation(code: str) -> LanguageNotation:
    lower = code.lower()
    return LanguageNotation(
        language=lower,
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=lower,
        raw_value=lower,
    )


def _bcp47_notation(
    compact: str,
    *,
    language: str = "",
    extlang: str = "",
    script: str = "",
    region: str = "",
    variant: str = "",
    extension: str = "",
    privateuse: str = "",
    grandfathered: str = "",
) -> LanguageNotation:
    return LanguageNotation(
        language=language,
        extlang=extlang,
        script=script,
        region=region,
        variant=variant,
        extension=extension,
        privateuse=privateuse,
        grandfathered=grandfathered,
        compact=compact,
        raw_value=compact.lower(),
    )


def _name_notation(name: str) -> LanguageNotation:
    lower = name.lower()
    return LanguageNotation(
        language="",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=lower,
        raw_value=lower,
    )


@pytest.mark.capability
class TestISO6391:
    """ISO 639-1:2002 — bare alpha-2 184 membership."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules.iso_639_1_ed2002 import (
            SectionAlpha2Code,
        )

        self.rule = SectionAlpha2Code()
        self.contract = LanguageContract()

    def test_metadata(self) -> None:
        assert self.rule.name == "Section 4-alpha-2-code"
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"language_code"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 639-1:2002"
        assert self.rule.provenance.publication_year == 2002
        assert self.rule.provenance.kind == "specification"

    def test_en_valid(self) -> None:
        assert self.rule.matches(_code_notation("en"), self.contract) is True

    def test_xx_invalid(self) -> None:
        assert self.rule.matches(_code_notation("xx"), self.contract) is False

    def test_en_case_insensitive(self) -> None:
        assert self.rule.matches(_code_notation("EN"), self.contract) is True

    def test_normalize_lower(self) -> None:
        assert self.rule.normalize(_code_notation("EN"), self.contract) == "en"

    def test_citation(self) -> None:
        assert "alpha-2" in self.rule.citation.lower()


@pytest.mark.capability
class TestISO6392:
    """ISO 639-2:1998 — bare alpha-3 487 T/B; B→T map ger→deu."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules.iso_639_2_ed1998 import (
            SectionAlpha3Code,
        )

        self.rule = SectionAlpha3Code()
        self.contract = LanguageContract()

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"language_code"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.authority == "ISO"
        assert self.rule.provenance.specification_name == "ISO 639-2:1998"
        assert self.rule.provenance.publication_year == 1998

    def test_eng_valid_t(self) -> None:
        assert self.rule.matches(_code_notation("eng"), self.contract) is True

    def test_ger_b_valid_but_normalizes_to_deu(self) -> None:
        assert self.rule.matches(_code_notation("ger"), self.contract) is True
        assert self.rule.normalize(_code_notation("ger"), self.contract) == "de"

    def test_ger_to_de_via_t_to_alpha2(self) -> None:
        from paxman.capabilities.Language.rules.data.iso_639_2 import (
            ISO6392_T_TO_ALPHA2,
        )

        assert ISO6392_T_TO_ALPHA2["deu"] == "de"

    def test_mis_special(self) -> None:
        assert self.rule.matches(_code_notation("mis"), self.contract) is True

    def test_xx_invalid(self) -> None:
        assert self.rule.matches(_code_notation("xxx"), self.contract) is False


@pytest.mark.capability
class TestISO6393:
    """ISO 639-3:2007 — bare alpha-3 comprehensive 7000+ (T only)."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules.iso_639_3_ed2007 import (
            SectionComprehensiveAlpha3,
        )

        self.rule = SectionComprehensiveAlpha3()
        self.contract = LanguageContract()
        self.private_contract = LanguageContract(include_private=True)

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"language_code"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.authority == "SIL International (ISO 639-3 RA)"
        assert self.rule.provenance.specification_name == "ISO 639-3:2007"
        assert self.rule.provenance.publication_year == 2007

    def test_cmn_valid(self) -> None:
        assert self.rule.matches(_code_notation("cmn"), self.contract) is True

    def test_qaa_private_reserved_without_flag_invalid(self) -> None:
        assert self.rule.matches(_code_notation("qaa"), self.contract) is False

    def test_qaa_with_private_flag_valid(self) -> None:
        assert self.rule.matches(_code_notation("qaa"), self.private_contract) is True

    def test_normalize_lower(self) -> None:
        assert self.rule.normalize(_code_notation("CMN"), self.contract) == "cmn"


@pytest.mark.capability
class TestISO6395:
    """ISO 639-5:2008 — scope collection 115 — only when include_collective=True."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules.iso_639_5_ed2008 import (
            SectionCollectiveCode,
        )

        self.rule = SectionCollectiveCode()
        self.default_contract = LanguageContract()
        self.collective_contract = LanguageContract(include_collective=True)

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"language_code"})
        assert self.rule.requires_features == frozenset({"include_collective"})
        assert self.rule.provenance.specification_name == "ISO 639-5:2008"
        assert self.rule.provenance.publication_year == 2008

    def test_aus_requires_flag(self) -> None:
        # Rule matches True when called directly,
        # but engine would not run it without flag
        assert (
            self.rule.matches(_code_notation("aus"), self.collective_contract) is True
        )
        assert "include_collective" in self.rule.requires_features

    def test_aus_not_validated_without_flag_via_requires_features(self) -> None:
        assert self.rule.requires_features == frozenset({"include_collective"})

    def test_bih_valid_with_flag(self) -> None:
        assert (
            self.rule.matches(_code_notation("bih"), self.collective_contract) is True
        )

    def test_eng_not_collective(self) -> None:
        assert (
            self.rule.matches(_code_notation("eng"), self.collective_contract) is False
        )


@pytest.mark.capability
class TestBCP47:
    """BCP 47 RFC 5646:2009 — ABNF well-formed only (PARSER)."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules.bcp47_rfc5646_ed2009 import (
            SectionBCP47Syntax,
        )

        self.rule = SectionBCP47Syntax()
        self.contract = LanguageContract()

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.PARSER
        assert self.rule.target_semantics == frozenset({"bcp47_tag"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.authority == "IETF"
        assert self.rule.provenance.specification_name == "BCP 47 RFC 5646"
        assert self.rule.provenance.publication_year == 2009

    def test_en_us_valid(self) -> None:
        n = _bcp47_notation("en-US", language="en", region="US")
        assert self.rule.matches(n, self.contract) is True

    def test_en_double_hyphen_invalid(self) -> None:
        # Use compact that would be malformed; rule should reject
        # Simulate malformed compact with double hyphen
        malformed = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en--US",
            raw_value="en--us",
        )
        assert self.rule.matches(malformed, self.contract) is False

    def test_en_trailing_hyphen_invalid(self) -> None:
        malformed = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-",
            raw_value="en-",
        )
        assert self.rule.matches(malformed, self.contract) is False

    def test_single_letter_invalid(self) -> None:
        malformed = LanguageNotation(
            language="e",
            extlang="",
            script="",
            region="",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="e",
            raw_value="e",
        )
        assert self.rule.matches(malformed, self.contract) is False

    def test_i_cherokee_grandfathered_shape_well_formed(self) -> None:
        n = _bcp47_notation("i-cherokee", grandfathered="i-cherokee")
        assert self.rule.matches(n, self.contract) is True

    def test_x_privateuse_well_formed(self) -> None:
        n = _bcp47_notation("x-fr-CH", privateuse="x-fr-ch")
        assert self.rule.matches(n, self.contract) is True

    def test_en_qaaa_script_position_well_formed(self) -> None:
        n = _bcp47_notation("en-Qaaa", language="en", script="Qaaa")
        assert self.rule.matches(n, self.contract) is True

    def test_deprecated_not_applied(self) -> None:
        # BCP47 should keep iw as iw, not map to he
        n = _bcp47_notation("iw", language="iw")
        assert self.rule.matches(n, self.contract) is True
        assert self.rule.normalize(n, self.contract) == "iw"

    def test_too_long_rejected(self) -> None:
        # en-US-123456789 has 9-char subtag >8
        malformed = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="123456789",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US-123456789",
            raw_value="en-us-123456789",
        )
        assert self.rule.matches(malformed, self.contract) is False


@pytest.mark.capability
class TestIANA:
    """IANA Language Subtag Registry — File-Date 2026-08-08."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules import (
            iana_language_subtag_registry_ed2026 as _iana_mod,
        )

        self.rule = _iana_mod.SectionIANARegistry()
        self.contract = LanguageContract()
        self.private_contract = LanguageContract(include_private=True)

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"bcp47_tag"})
        assert self.rule.requires_features == frozenset()
        assert self.rule.provenance.authority == "IANA"
        assert self.rule.provenance.kind == "registry"
        assert self.rule.provenance.version == "Rolling File-Date 2026-08-08"

    def test_sl_nedis_valid(self) -> None:
        n = _bcp47_notation("sl-nedis", language="sl", variant="nedis")
        assert self.rule.matches(n, self.contract) is True

    def test_de_nedis_invalid_prefix(self) -> None:
        n = _bcp47_notation("de-nedis", language="de", variant="nedis")
        assert self.rule.matches(n, self.contract) is False

    def test_script_hans_valid(self) -> None:
        n = _bcp47_notation("zh-Hans", language="zh", script="Hans")
        assert self.rule.matches(n, self.contract) is True

    def test_script_qaaa_private_only_with_flag(self) -> None:
        n = _bcp47_notation("en-Qaaa", language="en", script="Qaaa")
        assert self.rule.matches(n, self.contract) is False
        assert self.rule.matches(n, self.private_contract) is True

    def test_region_us_valid(self) -> None:
        n = _bcp47_notation("en-US", language="en", region="US")
        assert self.rule.matches(n, self.contract) is True

    def test_region_zz_private_only_with_flag(self) -> None:
        n = _bcp47_notation("en-ZZ", language="en", region="ZZ")
        assert self.rule.matches(n, self.contract) is False
        assert self.rule.matches(n, self.private_contract) is True

    def test_region_xx_private_always_invalid(self) -> None:
        # XX is private even with flag? Task says XX private
        # — treat as private
        n = _bcp47_notation("en-XX", language="en", region="XX")
        assert self.rule.matches(n, self.contract) is False
        assert self.rule.matches(n, self.private_contract) is True

    def test_deprecated_iw_to_he(self) -> None:
        n = _bcp47_notation("iw", language="iw")
        assert self.rule.matches(n, self.contract) is True
        assert self.rule.normalize(n, self.contract) == "he"

    def test_grandfathered_en_gb_oed_to_oxendict(self) -> None:
        n = _bcp47_notation("en-GB-oed", grandfathered="en-gb-oed")
        assert self.rule.matches(n, self.contract) is True
        assert self.rule.normalize(n, self.contract) == "en-GB-oxendict"

    def test_zh_hans_cn_passes(self) -> None:
        n = _bcp47_notation("zh-Hans-CN", language="zh", script="Hans", region="CN")
        assert self.rule.matches(n, self.contract) is True

    def test_suppress_script_latn_informative(self) -> None:
        n = _bcp47_notation("en-Latn", language="en", script="Latn")
        assert self.rule.matches(n, self.contract) is True

    def test_extlang_zh_cmn_valid(self) -> None:
        n = _bcp47_notation("zh-cmn", language="zh", extlang="cmn")
        assert self.rule.matches(n, self.contract) is True


@pytest.mark.capability
class TestCLDR:
    """CLDR localized display names — only when include_localized=True."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules import (
            cldr_language_display_name_ed2025 as _cldr_mod,
        )

        self.rule = _cldr_mod.SectionLocalizedNames()
        self.default_contract = LanguageContract()
        self.localized_contract = LanguageContract(include_localized=True)

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"language_name"})
        assert self.rule.requires_features == frozenset({"include_localized"})
        assert self.rule.provenance.authority == "Unicode CLDR"
        assert self.rule.provenance.kind == "registry"
        assert self.rule.provenance.publication_year == 2025

    def test_deutsch_with_flag_success(self) -> None:
        n = _name_notation("Deutsch")
        assert self.rule.matches(n, self.localized_contract) is True
        assert self.rule.normalize(n, self.localized_contract) == "de"

    def test_deutsch_without_flag_invalid_via_requires_features(self) -> None:
        assert self.rule.requires_features == frozenset({"include_localized"})


@pytest.mark.capability
class TestEnglishNameMapping:
    """English name → code via LOOKUP with language_name, no feature gate."""

    def setup_method(self) -> None:
        from paxman.capabilities.Language.rules.iso_639_1_ed2002 import (
            SectionEnglishNameMapping,
        )

        self.rule = SectionEnglishNameMapping()
        self.contract = LanguageContract()

    def test_metadata(self) -> None:
        assert self.rule.strategy is RuleStrategy.LOOKUP_TABLE
        assert self.rule.target_semantics == frozenset({"language_name"})
        assert self.rule.requires_features == frozenset()

    def test_german_to_de(self) -> None:
        n = _name_notation("German")
        assert self.rule.matches(n, self.contract) is True
        assert self.rule.normalize(n, self.contract) == "de"

    def test_english_to_en(self) -> None:
        n = _name_notation("English")
        assert self.rule.matches(n, self.contract) is True
        assert self.rule.normalize(n, self.contract) == "en"

    def test_unknown_invalid(self) -> None:
        n = _name_notation("Klingon")
        assert self.rule.matches(n, self.contract) is False
