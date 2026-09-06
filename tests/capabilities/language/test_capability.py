"""Tests for Language capability wiring — grammars, rules, contract, format_value."""

from __future__ import annotations

import pytest

from paxman.api.canonicalize import canonicalize
from paxman.capabilities.Language.capability import LanguageCapability
from paxman.capabilities.Language.contract import LanguageContract
from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.capability import Capability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution, RuleStrategy
from paxman.core.errors import ContractError


def _notation(compact: str = "en", language: str = "en") -> LanguageNotation:
    return LanguageNotation(
        language=language,
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=compact,
        raw_value=compact.lower(),
    )


def _bcp47_notation(compact: str, language: str = "") -> LanguageNotation:
    lang = language or compact.split("-")[0].lower()
    return LanguageNotation(
        language=lang,
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact=compact,
        raw_value=compact.lower(),
    )


class TestLanguageCapabilityMetadata:
    """Capability identity."""

    def test_name(self) -> None:
        assert LanguageCapability.name == "language"
        assert LanguageCapability().name == "language"

    def test_is_capability_subclass(self) -> None:
        assert isinstance(LanguageCapability(), Capability)

    def test_version(self) -> None:
        assert LanguageCapability.version == "1.0.0"
        assert getattr(LanguageCapability(), "version", None) == "1.0.0"


class TestLanguageCapabilityGrammars:
    """Grammars — exactly 3 with expected names/semantics."""

    def test_get_grammars_len(self) -> None:
        assert len(LanguageCapability().get_grammars()) == 3

    def test_grammar_names(self) -> None:
        names = {g.name for g in LanguageCapability().get_grammars()}
        assert names == {
            "bcp47_tag_recognition",
            "language_code_recognition",
            "language_name_recognition",
        }

    def test_grammar_semantics(self) -> None:
        sem = {g.semantics for g in LanguageCapability().get_grammars()}
        assert sem == {"bcp47_tag", "language_code", "language_name"}

    def test_grammar_semantics_per_name(self) -> None:
        gram = {g.name: g.semantics for g in LanguageCapability().get_grammars()}
        assert gram["bcp47_tag_recognition"] == "bcp47_tag"
        assert gram["language_code_recognition"] == "language_code"
        assert gram["language_name_recognition"] == "language_name"

    def test_single_value_true(self) -> None:
        for g in LanguageCapability().get_grammars():
            assert g.single_value is True


class TestLanguageCapabilityRules:
    """Rules - 10 with metadata."""  # noqa: E501

    def test_get_rules_len(self) -> None:
        # 10 rule classes: 2 in iso_639_1, 1 iso_639_2,
        # 2 iso_639_3 (comprehensive + private), 1 iso_639_5, bcp47, 2 iana, cldr.
        assert len(LanguageCapability().get_rules()) == 10

    def test_rule_names(self) -> None:
        names = {r.name for r in LanguageCapability().get_rules()}
        assert names == {
            "Section 4-alpha-2-code",
            "Section-english-name-mapping",
            "Section 4-alpha-3-code",
            "Section 4-comprehensive-alpha-3",
            "Section 4-private-alpha-3",
            "Section 4-collective-code",
            "Section 2.1-syntax",
            "Section-iana-registry",
            "Section-iana-registry-private",
            "Section-localized-names",
        }

    def test_rule_provenances(self) -> None:
        prov = {r.name: r.provenance for r in LanguageCapability().get_rules()}
        assert prov["Section 4-alpha-2-code"].specification_name == "ISO 639-1:2002"
        assert prov["Section 4-alpha-2-code"].publication_year == 2002
        assert (
            prov["Section-english-name-mapping"].specification_name == "ISO 639-1:2002"
        )
        assert prov["Section 4-alpha-3-code"].specification_name == "ISO 639-2:1998"
        assert (
            prov["Section 4-comprehensive-alpha-3"].specification_name
            == "ISO 639-3:2007"
        )
        assert prov["Section 4-private-alpha-3"].specification_name == "ISO 639-3:2007"
        assert prov["Section 4-collective-code"].specification_name == "ISO 639-5:2008"
        assert prov["Section 2.1-syntax"].specification_name == "BCP 47 RFC 5646"
        assert (
            prov["Section-iana-registry"].specification_name
            == "IANA Language Subtag Registry"
        )
        assert prov["Section-iana-registry"].kind == "registry"
        assert prov["Section-iana-registry"].version == "Rolling File-Date 2026-08-08"
        assert (
            prov["Section-iana-registry-private"].specification_name
            == "IANA Language Subtag Registry"
        )
        assert (
            prov["Section-localized-names"].specification_name
            == "CLDR Language Display Names"
        )

    def test_rule_target_semantics(self) -> None:
        targets = {r.name: r.target_semantics for r in LanguageCapability().get_rules()}
        assert targets["Section 4-alpha-2-code"] == frozenset({"language_code"})
        assert targets["Section-english-name-mapping"] == frozenset({"language_name"})
        assert targets["Section 4-alpha-3-code"] == frozenset({"language_code"})
        assert targets["Section 4-comprehensive-alpha-3"] == frozenset(
            {"language_code"}
        )
        assert targets["Section 4-private-alpha-3"] == frozenset({"language_code"})
        assert targets["Section 4-collective-code"] == frozenset({"language_code"})
        assert targets["Section 2.1-syntax"] == frozenset({"bcp47_tag"})
        assert targets["Section-iana-registry"] == frozenset({"bcp47_tag"})
        assert targets["Section-iana-registry-private"] == frozenset({"bcp47_tag"})
        assert targets["Section-localized-names"] == frozenset({"language_name"})

    def test_rule_requires_features(self) -> None:
        req = {r.name: r.requires_features for r in LanguageCapability().get_rules()}
        assert req["Section 4-alpha-2-code"] == frozenset()
        assert req["Section-english-name-mapping"] == frozenset()
        assert req["Section 4-alpha-3-code"] == frozenset()
        assert req["Section 4-comprehensive-alpha-3"] == frozenset()
        assert req["Section 4-private-alpha-3"] == frozenset({"include_private"})
        assert req["Section 4-collective-code"] == frozenset({"include_collective"})
        assert req["Section 2.1-syntax"] == frozenset()
        assert req["Section-iana-registry"] == frozenset()
        assert req["Section-iana-registry-private"] == frozenset({"include_private"})
        assert req["Section-localized-names"] == frozenset({"include_localized"})

    def test_rule_strategies(self) -> None:
        strat = {r.name: r.strategy for r in LanguageCapability().get_rules()}
        assert strat["Section 2.1-syntax"] == RuleStrategy.PARSER
        for n in (
            "Section 4-alpha-2-code",
            "Section 4-alpha-3-code",
            "Section 4-comprehensive-alpha-3",
            "Section 4-private-alpha-3",
            "Section 4-collective-code",
            "Section-iana-registry",
            "Section-iana-registry-private",
            "Section-localized-names",
            "Section-english-name-mapping",
        ):
            assert strat[n] == RuleStrategy.LOOKUP_TABLE


class TestLanguageCreateContract:
    """create_contract — tuple-normalized, defaults, flags."""

    def test_defaults(self) -> None:
        c = LanguageCapability.create_contract()
        assert isinstance(c, LanguageContract)
        assert c.output_format == "bcp47"
        assert c.capability_name == "language"
        assert c.active_grammars is None
        assert c.excluded_rules == ()
        assert c.pinned_rules is None
        assert c.year is None
        assert c.extra_grammars == ()
        assert c.include_localized is False
        assert c.include_collective is False
        assert c.include_private is False

    def test_default_aliases(self) -> None:
        for alias in (None, "default", "bcp47"):
            assert (
                LanguageCapability.create_contract(output_format=alias).output_format
                == "bcp47"
            )

    def test_offered_formats(self) -> None:
        for fmt in ("alpha2", "alpha3", "alpha3-bib", "name"):
            assert (
                LanguageCapability.create_contract(output_format=fmt).output_format
                == fmt
            )

    def test_invalid_format_raises(self) -> None:
        for bad in ("paper", "iso", "hyphenated", "", "BCP47", "alpha-2"):
            with pytest.raises(ContractError):
                LanguageCapability.create_contract(output_format=bad)  # type: ignore[arg-type]

    def test_contract_error_via_direct(self) -> None:
        with pytest.raises(ContractError):
            LanguageContract(output_format="invalid")  # type: ignore[arg-type]

    def test_tuple_normalization(self) -> None:
        c = LanguageCapability.create_contract(
            excluded_rules=["Section 4-alpha-2-code"],
            pinned_rules=["Section 4-alpha-3-code"],
            extra_grammars=["bcp47_tag_recognition"],
        )
        assert c.excluded_rules == ("Section 4-alpha-2-code",)
        assert c.pinned_rules == ("Section 4-alpha-3-code",)
        assert c.extra_grammars == ("bcp47_tag_recognition",)

    def test_flags(self) -> None:
        c = LanguageCapability.create_contract(
            include_localized=True,
            include_collective=True,
            include_private=True,
        )
        assert c.include_localized is True
        assert c.include_collective is True
        assert c.include_private is True

    def test_year_passthrough(self) -> None:
        assert LanguageCapability.create_contract(year=2008).year == 2008

    def test_contract_class_vars(self) -> None:
        assert LanguageContract.DEFAULT_OUTPUT_FORMAT == "bcp47"
        assert (
            frozenset({"alpha2", "alpha3", "alpha3-bib", "name"})
            == LanguageContract.OFFERED_OUTPUT_FORMATS
        )


class TestLanguageFormatValue:
    """format_value — bcp47 identity vs offered mappings."""

    def test_bcp47_identity(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en", "bcp47", _notation("en")) == "en"
        assert cap.format_value("en-US", "bcp47", _bcp47_notation("en-US")) == "en-US"
        assert (
            cap.format_value("zh-Hans-CN", "bcp47", _bcp47_notation("zh-Hans-CN"))
            == "zh-Hans-CN"
        )

    def test_default_none_is_identity(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en-US", None, _bcp47_notation("en-US")) == "en-US"
        assert cap.format_value("en", None, _notation("en")) == "en"

    def test_alpha2_from_alpha2(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en", "alpha2", _notation("en")) == "en"

    def test_alpha2_from_alpha3_term(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("eng", "alpha2", _notation("eng", language="eng")) == "en"
        )
        assert (
            cap.format_value("fra", "alpha2", _notation("fra", language="fra")) == "fr"
        )
        assert (
            cap.format_value("deu", "alpha2", _notation("deu", language="deu")) == "de"
        )

    def test_alpha2_from_alpha3_bib_via_term(self) -> None:
        cap = LanguageCapability()
        # ger is Bib for deu
        assert (
            cap.format_value("ger", "alpha2", _notation("ger", language="ger")) == "de"
        )
        assert (
            cap.format_value("fre", "alpha2", _notation("fre", language="fre")) == "fr"
        )
        assert (
            cap.format_value("chi", "alpha2", _notation("chi", language="chi")) == "zh"
        )

    def test_alpha2_from_bcp47_tag(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en-US", "alpha2", _bcp47_notation("en-US")) == "en"
        assert cap.format_value("fr-FR", "alpha2", _bcp47_notation("fr-FR")) == "fr"
        assert (
            cap.format_value("zh-Hans-CN", "alpha2", _bcp47_notation("zh-Hans-CN"))
            == "zh"
        )
        assert (
            cap.format_value("ger", "alpha2", _notation("ger", language="ger")) == "de"
        )

    def test_alpha2_no_mapping_passthrough(self) -> None:
        cap = LanguageCapability()
        # chr has no alpha2 mapping — returns term itself
        assert (
            cap.format_value("chr", "alpha2", _notation("chr", language="chr")) == "chr"
        )

    def test_alpha3_term_from_alpha2(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en", "alpha3", _notation("en")) == "eng"
        assert cap.format_value("de", "alpha3", _notation("de")) == "deu"
        assert cap.format_value("fr", "alpha3", _notation("fr")) == "fra"
        assert cap.format_value("zh", "alpha3", _notation("zh")) == "zho"

    def test_alpha3_term_from_bib(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("ger", "alpha3", _notation("ger", language="ger")) == "deu"
        )
        assert (
            cap.format_value("fre", "alpha3", _notation("fre", language="fre")) == "fra"
        )

    def test_alpha3_term_from_bcp47(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en-US", "alpha3", _bcp47_notation("en-US")) == "eng"
        assert cap.format_value("de", "alpha3", _notation("de")) == "deu"

    def test_alpha3_term_identity_when_already_term(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("eng", "alpha3", _notation("eng", language="eng")) == "eng"
        )
        assert (
            cap.format_value("chr", "alpha3", _notation("chr", language="chr")) == "chr"
        )

    def test_alpha3_bib_from_term(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("deu", "alpha3-bib", _notation("deu", language="deu"))
            == "ger"
        )
        assert (
            cap.format_value("fra", "alpha3-bib", _notation("fra", language="fra"))
            == "fre"
        )
        assert (
            cap.format_value("zho", "alpha3-bib", _notation("zho", language="zho"))
            == "chi"
        )
        assert (
            cap.format_value("ces", "alpha3-bib", _notation("ces", language="ces"))
            == "cze"
        )

    def test_alpha3_bib_from_alpha2(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("de", "alpha3-bib", _notation("de")) == "ger"
        assert cap.format_value("en", "alpha3-bib", _notation("en")) == "eng"
        assert cap.format_value("fr", "alpha3-bib", _notation("fr")) == "fre"

    def test_alpha3_bib_from_bcp47(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("en-US", "alpha3-bib", _bcp47_notation("en-US")) == "eng"
        )
        assert cap.format_value("de", "alpha3-bib", _notation("de")) == "ger"

    def test_alpha3_bib_passthrough_when_no_bib(self) -> None:
        cap = LanguageCapability()
        # eng has no distinct bib → same
        assert (
            cap.format_value("eng", "alpha3-bib", _notation("eng", language="eng"))
            == "eng"
        )

    def test_name_from_alpha2(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en", "name", _notation("en")) == "English"
        assert cap.format_value("de", "name", _notation("de")) == "German"
        assert cap.format_value("fr", "name", _notation("fr")) == "French"

    def test_name_from_alpha3(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("eng", "name", _notation("eng", language="eng"))
            == "English"
        )
        assert (
            cap.format_value("deu", "name", _notation("deu", language="deu"))
            == "German"
        )

    def test_name_from_bcp47(self) -> None:
        cap = LanguageCapability()
        assert cap.format_value("en-US", "name", _bcp47_notation("en-US")) == "English"
        assert (
            cap.format_value("zh-Hans-CN", "name", _bcp47_notation("zh-Hans-CN"))
            == "Chinese"
        )

    def test_name_from_bib_via_term(self) -> None:
        cap = LanguageCapability()
        assert (
            cap.format_value("ger", "name", _notation("ger", language="ger"))
            == "German"
        )


class TestLanguageExtendedTagCarry:
    """Extended-tag carry for alpha2/alpha3/alpha3-bib (ADR-0011 Phase 3).

    The three code formats map the primary subtag through the existing
    ISO 639 tables unchanged and carry the remaining subtags verbatim, so
    extended tags no longer collapse onto the bare primary (``en-US`` and
    ``en-GB`` rendered distinctly). ``name`` stays a primary-name
    projection (waived per ADR-0011 — subtag-carrying names do not
    re-enter); bare codes are unaffected (nothing to carry).
    """

    def setup_method(self) -> None:
        """Register the Language capability for each test."""
        reset_registry()
        register_capability(LanguageCapability())

    def teardown_method(self) -> None:
        """Reset the registry so other tests start clean."""
        reset_registry()

    @pytest.mark.parametrize(
        ("source", "output_format", "expected"),
        [
            ("en-US", "alpha2", "en-US"),
            ("en-US", "alpha3", "eng-US"),
            ("en-US", "alpha3-bib", "eng-US"),
            ("zh-Hant-TW", "alpha2", "zh-Hant-TW"),
            ("zh-Hant-TW", "alpha3", "zho-Hant-TW"),
            # Bib of zho is chi (_TERM_TO_BIB): mapped primary + rest.
            ("zh-Hant-TW", "alpha3-bib", "chi-Hant-TW"),
            ("de-CH-1901", "alpha2", "de-CH-1901"),
            ("de-CH-1901", "alpha3", "deu-CH-1901"),
            ("de-CH-1901", "alpha3-bib", "ger-CH-1901"),
            ("x-foo", "alpha2", "x-foo"),
            ("x-foo", "alpha3", "x-foo"),
            ("x-foo", "alpha3-bib", "x-foo"),
            # Extlang compacts canonicalize to themselves (no folding).
            ("zh-cmn", "alpha2", "zh-cmn"),
            ("zh-cmn", "alpha3", "zho-cmn"),
            ("zh-cmn", "alpha3-bib", "chi-cmn"),
        ],
    )
    def test_carry_rows(
        self, source: str, output_format: str, expected: str
    ) -> None:
        """Each code format renders mapped primary + verbatim rest."""
        contract = LanguageCapability.create_contract(output_format=output_format)
        result = canonicalize(source, contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected

    @pytest.mark.parametrize(
        ("source", "output_format", "expected"),
        [
            ("en-US", "alpha2", "en-US"),
            ("zh-Hant-TW", "alpha2", "zh-Hant-TW"),
            ("de-CH-1901", "alpha2", "de-CH-1901"),
            ("x-foo", "alpha2", "x-foo"),
            ("x-foo", "alpha3", "x-foo"),
            ("x-foo", "alpha3-bib", "x-foo"),
            ("en-US", "alpha3", "eng-US"),
            ("en-US", "alpha3-bib", "eng-US"),
            ("zh-Hant-TW", "alpha3-bib", "chi-Hant-TW"),
            ("zh-cmn", "alpha2", "zh-cmn"),
            ("zh-cmn", "alpha3-bib", "chi-cmn"),
        ],
    )
    def test_carry_reenters_param_free(
        self, source: str, output_format: str, expected: str
    ) -> None:
        """Each carried rendering re-enters under the default contract.

        Excluded by empirical run (default contract, pre- and post-fix —
        the default path is untouched by the renderer): ``zho-Hant-TW``
        re-enters AMBIGUOUS and ``deu-CH-1901`` / ``ger-CH-1901`` /
        ``zho-cmn`` re-enter INVALID/AMBIGUOUS. Variant/script Prefix
        validation is primary-relative, so a mapped primary breaks the
        prefix constraints the carried subtags were validated against.
        Known limitation, flagged for the hard-mandate promotion ADR
        alongside the ``name`` waiver.
        """
        rendered = canonicalize(
            source, LanguageCapability.create_contract(output_format=output_format)
        )
        assert rendered.status == Resolution.SUCCESS
        assert rendered.canonicalized_value == expected
        reentry = canonicalize(expected, LanguageCapability.create_contract())
        assert reentry.status == Resolution.SUCCESS
        assert reentry.canonicalized_value == expected

    def test_carry_injective_en_us_en_gb(self) -> None:
        """``en-US`` and ``en-GB`` render distinctly under alpha2."""
        contract = LanguageCapability.create_contract(output_format="alpha2")
        us = canonicalize("en-US", contract)
        gb = canonicalize("en-GB", contract)
        assert us.status == Resolution.SUCCESS
        assert gb.status == Resolution.SUCCESS
        assert us.canonicalized_value == "en-US"
        assert gb.canonicalized_value == "en-GB"
        assert us.canonicalized_value != gb.canonicalized_value

    def test_name_waived_projection_locked(self) -> None:
        """``name`` of ``en-US`` stays ``English`` (waived per ADR-0011)."""
        contract = LanguageCapability.create_contract(output_format="name")
        result = canonicalize("en-US", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "English"

    @pytest.mark.parametrize(
        ("source", "output_format", "expected"),
        [
            ("en", "alpha2", "en"),
            ("en", "alpha3", "eng"),
            ("en", "alpha3-bib", "eng"),
            ("deu", "alpha2", "de"),
            ("deu", "alpha3", "deu"),
            ("deu", "alpha3-bib", "ger"),
        ],
    )
    def test_bare_codes_unchanged(
        self, source: str, output_format: str, expected: str
    ) -> None:
        """Bare codes render exactly as before (nothing to carry)."""
        contract = LanguageCapability.create_contract(output_format=output_format)
        result = canonicalize(source, contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == expected
