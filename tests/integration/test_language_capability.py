"""Integration tests for Language capability — resolution map, gating, output_format."""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.Language.capability import LanguageCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test."""
    reset_registry()
    yield
    reset_registry()


def _register() -> None:
    register_capability(LanguageCapability())


@pytest.mark.integration
def test_bare_code_success() -> None:
    _register()
    r = paxman.canonicalize("en", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "en"
    assert r.span == (0, 2)
    assert r.version_stamp is not None
    assert len(r.candidates) >= 1
    assert r.candidates[0].span == (0, 2)


@pytest.mark.integration
def test_bcp47_case_canonicalization() -> None:
    _register()
    r = paxman.canonicalize("EN-us", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "en-US"
    assert r.span == (0, 5)


@pytest.mark.integration
def test_underscore_tolerance() -> None:
    _register()
    r = paxman.canonicalize("fr_FR", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "fr-FR"
    # underscore preserved in raw_text, compact hyphenated
    assert r.span == (0, 5)
    assert r.candidates[0].span == (0, 5)


@pytest.mark.integration
def test_display_name_success() -> None:
    _register()
    r = paxman.canonicalize("German", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "de"
    assert r.span == (0, 6)


@pytest.mark.integration
def test_grandfathered_preferred() -> None:
    _register()
    r = paxman.canonicalize("i-cherokee", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "chr"
    # both BCP47 and IANA agree on preferred, no AMBIGUOUS
    assert {c.value for c in r.candidates} == {"chr"}


@pytest.mark.integration
def test_deprecated_preferred() -> None:
    _register()
    r = paxman.canonicalize("iw", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "he"


@pytest.mark.integration
def test_collective_invalid_by_default() -> None:
    _register()
    # "aav" is exclusive ISO 639-5 collective (115) not in 639-2/3,
    # so without flag no rule validates → INVALID
    # "aus" is also collective but overlaps ISO 639-2, so it would be
    # SUCCESS even without flag; aav is the clean vector
    r = paxman.canonicalize("aav", LanguageCapability.create_contract())
    assert r.status == Resolution.INVALID
    assert r.canonicalized_value is None


@pytest.mark.integration
def test_collective_success_when_gated() -> None:
    _register()
    r = paxman.canonicalize(
        "aav", LanguageCapability.create_contract(include_collective=True)
    )
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "aav"
    assert any(c.validation_rule == "Section 4-collective-code" for c in r.candidates)


@pytest.mark.integration
def test_variant_prefix_invalid() -> None:
    _register()
    r = paxman.canonicalize("de-nedis", LanguageCapability.create_contract())
    assert r.status == Resolution.INVALID
    # reset registry for second call (registry frozen after first canonicalize)
    reset_registry()
    _register()
    r2 = paxman.canonicalize("sl-nedis", LanguageCapability.create_contract())
    assert r2.status == Resolution.SUCCESS
    assert r2.canonicalized_value == "sl-nedis"


@pytest.mark.integration
def test_output_format_alpha2() -> None:
    _register()
    r = paxman.canonicalize(
        "eng", LanguageCapability.create_contract(output_format="alpha2")
    )
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "en"


@pytest.mark.integration
def test_output_format_alpha3() -> None:
    _register()
    r = paxman.canonicalize(
        "en", LanguageCapability.create_contract(output_format="alpha3")
    )
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "eng"


@pytest.mark.integration
def test_year_filter() -> None:
    _register()
    # BCP 47 rule is 2009, so year 2008 drops bcp47_tag;
    # bare code doesn't cover hyphenated → INVALID
    r = paxman.canonicalize("en-US", LanguageCapability.create_contract(year=2008))
    assert r.status == Resolution.INVALID
    assert r.canonicalized_value is None
    # year 2009 includes BCP47 → SUCCESS
    reset_registry()
    _register()
    r2 = paxman.canonicalize("en-US", LanguageCapability.create_contract(year=2009))
    assert r2.status == Resolution.SUCCESS
    assert r2.canonicalized_value == "en-US"


@pytest.mark.integration
def test_deprecated_three_letter_resolve_to_preferred() -> None:
    _register()
    for deprecated, preferred in (("scc", "sr"), ("scr", "hr"), ("mol", "ro")):
        r = paxman.canonicalize(deprecated, LanguageCapability.create_contract())
        assert r.status == Resolution.SUCCESS
        assert r.canonicalized_value == preferred
        reset_registry()
        _register()


@pytest.mark.integration
def test_serbo_croatian_hyphenated_is_ambiguous_documented() -> None:
    # Hyphenated display name collides with BCP47 well-formed variant path:
    # serbo-croatian (language 5-8 + variant 5-8) vs sh (English name).
    # Spaced form is the supported spelling.
    _register()
    r = paxman.canonicalize("Serbo-Croatian", LanguageCapability.create_contract())
    assert r.status == Resolution.AMBIGUOUS
    reset_registry()
    _register()
    r2 = paxman.canonicalize("Serbo Croatian", LanguageCapability.create_contract())
    assert r2.status == Resolution.SUCCESS
    assert r2.canonicalized_value == "sh"


@pytest.mark.integration
def test_two_distinct_raise() -> None:
    _register()
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize("en, fr", LanguageCapability.create_contract())


@pytest.mark.integration
def test_identical_coalesce() -> None:
    _register()
    r = paxman.canonicalize("en en", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "en"
    # dedup: identical values coalesce, not MultipleMentionsError


@pytest.mark.integration
def test_missing() -> None:
    _register()
    r = paxman.canonicalize("xx", LanguageCapability.create_contract())
    assert (
        r.status == Resolution.INVALID
    )  # shape claimed via language_code, registry rejects
    assert r.candidates == ()
    reset_registry()
    _register()
    r2 = paxman.canonicalize("!!!", LanguageCapability.create_contract())
    assert r2.status == Resolution.MISSING
    assert r2.candidates == ()


@pytest.mark.integration
def test_script_region_canonical() -> None:
    _register()
    r = paxman.canonicalize("zh-Hans-CN", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "zh-Hans-CN"
    assert r.span == (0, 10)
    # VersionStamp determinism: same input + same contract = identical result
    reset_registry()
    _register()
    r2 = paxman.canonicalize("zh-Hans-CN", LanguageCapability.create_contract())
    assert r.canonicalized_value == r2.canonicalized_value
    assert r.version_stamp.paxman_version == r2.version_stamp.paxman_version


@pytest.mark.integration
def test_output_format_alpha3_bib() -> None:
    _register()
    r = paxman.canonicalize(
        "en", LanguageCapability.create_contract(output_format="alpha3-bib")
    )
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "eng"
    reset_registry()
    _register()
    r2 = paxman.canonicalize(
        "de", LanguageCapability.create_contract(output_format="alpha3-bib")
    )
    assert r2.status == Resolution.SUCCESS
    # de -> deu term -> bib ger
    assert r2.canonicalized_value == "ger"


@pytest.mark.integration
def test_output_format_name() -> None:
    _register()
    r = paxman.canonicalize(
        "de", LanguageCapability.create_contract(output_format="name")
    )
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "German"
    reset_registry()
    _register()
    r2 = paxman.canonicalize(
        "eng", LanguageCapability.create_contract(output_format="name")
    )
    assert r2.status == Resolution.SUCCESS
    assert r2.canonicalized_value == "English"


@pytest.mark.integration
def test_extlang_and_private() -> None:
    _register()
    r = paxman.canonicalize("zh-cmn", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "zh-cmn"
    reset_registry()
    _register()
    r2 = paxman.canonicalize("en-x-private", LanguageCapability.create_contract())
    # privateuse without flag: BCP47 syntax succeeds, IANA gated
    assert r2.status == Resolution.SUCCESS
    assert r2.canonicalized_value == "en-x-private"
    assert any(c.validation_rule == "Section 2.1-syntax" for c in r2.candidates)
    reset_registry()
    _register()
    r3 = paxman.canonicalize(
        "en-x-private", LanguageCapability.create_contract(include_private=True)
    )
    assert r3.status == Resolution.SUCCESS
    assert r3.canonicalized_value == "en-x-private"
    assert any(
        c.validation_rule in ("Section-iana-registry", "Section-iana-registry-private")
        for c in r3.candidates
    )


@pytest.mark.integration
def test_variant_multiple_and_extension() -> None:
    _register()
    r = paxman.canonicalize("sl-rozaj", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "sl-rozaj"
    reset_registry()
    _register()
    r2 = paxman.canonicalize("en-a-foo", LanguageCapability.create_contract())
    assert r2.status == Resolution.SUCCESS
    assert r2.canonicalized_value == "en-a-foo"


@pytest.mark.integration
def test_format_value_edge_cases() -> None:
    # Direct format_value coverage for missing branches
    cap = LanguageCapability()
    from paxman.capabilities.Language.notation import LanguageNotation

    n = LanguageNotation(
        language="en",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en",
        raw_value="en",
    )
    # empty value
    assert cap.format_value("", "alpha2", n) == ""
    # unknown primary no mapping
    unk_n = LanguageNotation(
        language="xx",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="xx",
        raw_value="xx",
    )
    assert cap.format_value("xx", "alpha2", unk_n) == "xx"
    assert cap.format_value("xx", "alpha3", unk_n) == "xx"
    assert cap.format_value("xx", "alpha3-bib", unk_n) == "xx"
    assert cap.format_value("xx", "name", unk_n) == "xx"
    # name fallback via term
    assert cap.format_value("ger", "name", unk_n) == "German"
    # alpha3-bib mapping
    assert cap.format_value("de", "alpha3-bib", n) == "ger"


@pytest.mark.integration
def test_bcp47_grammar_edge_cases() -> None:
    from paxman.capabilities.Language.grammar.bcp47_tag_recognition import (
        BCP47TagGrammar,
    )

    g = BCP47TagGrammar()
    # extlang multiple
    r = g.recognize("zh-cmn-yue")
    assert len(r) == 1
    assert r[0].notation.extlang == "cmn-yue"
    # extension with privateuse tail
    r2 = g.recognize("en-a-bbb-x-private")
    assert len(r2) == 1
    assert r2[0].notation.extension == "a-bbb"
    assert r2[0].notation.privateuse == "x-private"
    # variant with digit prefix
    r3 = g.recognize("de-1996")
    assert len(r3) == 1
    assert r3[0].notation.variant == "1996"
    # privateuse only
    r4 = g.recognize("x-private-foo")
    assert len(r4) == 1
    assert r4[0].notation.privateuse == "x-private-foo"


@pytest.mark.integration
def test_iana_registry_edge_cases() -> None:
    from paxman.capabilities.Language.notation import LanguageNotation
    from paxman.capabilities.Language.rules.iana_language_subtag_registry_ed2026 import (  # noqa: E501
        SectionIANARegistry,
        SectionIANARegistryPrivate,
    )

    rule = SectionIANARegistry()
    private_rule = SectionIANARegistryPrivate()
    # script private Qaaa without flag should fail, with flag succeed - already covered
    # region private ZZ
    n = LanguageNotation(
        language="en",
        extlang="",
        script="",
        region="ZZ",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en-ZZ",
        raw_value="en-zz",
    )
    assert rule.matches(n, LanguageCapability.create_contract()) is False
    assert (
        private_rule.matches(
            n, LanguageCapability.create_contract(include_private=True)
        )
        is True
    )
    # variant prefix valid
    n2 = LanguageNotation(
        language="sl",
        extlang="",
        script="",
        region="",
        variant="nedis",
        extension="",
        privateuse="",
        grandfathered="",
        compact="sl-nedis",
        raw_value="sl-nedis",
    )
    assert rule.matches(n2, LanguageCapability.create_contract()) is True
    n3 = LanguageNotation(
        language="de",
        extlang="",
        script="",
        region="",
        variant="nedis",
        extension="",
        privateuse="",
        grandfathered="",
        compact="de-nedis",
        raw_value="de-nedis",
    )
    assert rule.matches(n3, LanguageCapability.create_contract()) is False
    # extlang private
    n4 = LanguageNotation(
        language="zh",
        extlang="qaa",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="zh-qaa",
        raw_value="zh-qaa",
    )
    assert rule.matches(n4, LanguageCapability.create_contract()) is False
    assert (
        private_rule.matches(
            n4, LanguageCapability.create_contract(include_private=True)
        )
        is True
    )
    # extlang invalid
    n5 = LanguageNotation(
        language="en",
        extlang="zzz",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en-zzz",
        raw_value="en-zzz",
    )
    assert rule.matches(n5, LanguageCapability.create_contract()) is False
    # language private qaa-qtz
    n6 = LanguageNotation(
        language="qaa",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="qaa",
        raw_value="qaa",
    )
    assert rule.matches(n6, LanguageCapability.create_contract()) is False
    assert (
        private_rule.matches(
            n6, LanguageCapability.create_contract(include_private=True)
        )
        is True
    )
    # script invalid
    n7 = LanguageNotation(
        language="en",
        extlang="",
        script="Zzzz",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en-Zzzz",
        raw_value="en-zzzz",
    )
    assert rule.matches(n7, LanguageCapability.create_contract()) is False
    # region invalid numeric
    n8 = LanguageNotation(
        language="en",
        extlang="",
        script="",
        region="999",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en-999",
        raw_value="en-999",
    )
    assert rule.matches(n8, LanguageCapability.create_contract()) is False
    # variant not in set
    n9 = LanguageNotation(
        language="en",
        extlang="",
        script="",
        region="",
        variant="zzzzzzzz",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en-zzzzzzzz",
        raw_value="en-zzzzzzzz",
    )
    assert rule.matches(n9, LanguageCapability.create_contract()) is False
    # privateuse-only
    n10 = LanguageNotation(
        language="",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="x-foo-bar",
        grandfathered="",
        compact="x-foo-bar",
        raw_value="x-foo-bar",
    )
    assert rule.matches(n10, LanguageCapability.create_contract()) is False
    assert (
        private_rule.matches(
            n10, LanguageCapability.create_contract(include_private=True)
        )
        is True
    )
    # grandfathered
    n11 = LanguageNotation(
        language="",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="i-cherokee",
        compact="i-cherokee",
        raw_value="i-cherokee",
    )
    assert rule.matches(n11, LanguageCapability.create_contract()) is True
    # normalize covers extension and privateuse
    n12 = LanguageNotation(
        language="en",
        extlang="",
        script="",
        region="",
        variant="",
        extension="a-foo",
        privateuse="x-bar",
        grandfathered="",
        compact="en-a-foo-x-bar",
        raw_value="en-a-foo-x-bar",
    )
    assert rule.normalize(n12, LanguageCapability.create_contract()) == "en-a-foo-x-bar"
    n13 = LanguageNotation(
        language="",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="x-foo",
        grandfathered="",
        compact="x-foo",
        raw_value="x-foo",
    )
    assert rule.normalize(n13, LanguageCapability.create_contract()) == "x-foo"
    # variant with script/region prefix candidates
    n14 = LanguageNotation(
        language="sl",
        extlang="",
        script="Latn",
        region="SI",
        variant="nedis",
        extension="",
        privateuse="",
        grandfathered="",
        compact="sl-Latn-SI-nedis",
        raw_value="sl-latn-si-nedis",
    )
    assert rule.matches(n14, LanguageCapability.create_contract()) is True
    # language invalid not private not deprecated
    n15 = LanguageNotation(
        language="xx",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="xx",
        raw_value="xx",
    )
    assert rule.matches(n15, LanguageCapability.create_contract()) is False
    # language deprecated should pass
    n16 = LanguageNotation(
        language="iw",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="iw",
        raw_value="iw",
    )
    assert rule.matches(n16, LanguageCapability.create_contract()) is True
    assert rule.normalize(n16, LanguageCapability.create_contract()) == "he"
    # extlang with hyphen
    n17 = LanguageNotation(
        language="zh",
        extlang="cmn-yue",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="zh-cmn-yue",
        raw_value="zh-cmn-yue",
    )
    assert rule.matches(n17, LanguageCapability.create_contract()) is True


@pytest.mark.integration
def test_bcp47_complex_grammar_and_iso5() -> None:
    from paxman.capabilities.Language.grammar.bcp47_tag_recognition import (
        BCP47TagGrammar,
    )
    from paxman.capabilities.Language.notation import LanguageNotation
    from paxman.capabilities.Language.rules.iso_639_5_ed2008 import (
        SectionCollectiveCode,
    )

    g = BCP47TagGrammar()
    # three extlangs
    r = g.recognize("zh-cmn-yue-ext")
    # may be 1 match with extlang cmn-yue and variant ext? Check at least one
    assert len(r) >= 1
    # complex tag with script region variant extension privateuse
    r2 = g.recognize("en-Latn-US-1996-a-foo-x-bar")
    assert len(r2) == 1
    assert r2[0].notation.script == "Latn"
    assert r2[0].notation.region == "US"
    assert r2[0].notation.variant == "1996"
    assert r2[0].notation.extension == "a-foo"
    assert r2[0].notation.privateuse == "x-bar"
    # extlang with 3 extlangs
    r3 = g.recognize("en-abc-def-ghi-jkl")
    assert len(r3) == 1
    assert r3[0].notation.extlang == "abc-def-ghi"
    # tag with variant not in expected, triggers break
    r4 = g.recognize("en-US-ab")
    assert len(r4) == 1
    assert r4[0].notation.variant == ""
    assert r4[0].notation.extension == ""
    # tag with extension singleton with subtags
    r5 = g.recognize("en-a-bbb")
    assert len(r5) == 1
    assert r5[0].notation.extension == "a-bbb"
    # tag with privateuse tail and extlang
    r6 = g.recognize("zh-cmn-x-foo")
    assert len(r6) == 1
    assert r6[0].notation.extlang == "cmn"
    assert r6[0].notation.privateuse == "x-foo"
    # all parts together
    r7 = g.recognize("zh-cmn-Hans-CN-1996-a-bbb-x-foo")
    assert len(r7) == 1
    assert r7[0].notation.language == "zh"
    assert r7[0].notation.extlang == "cmn"
    assert r7[0].notation.script == "Hans"
    assert r7[0].notation.region == "CN"
    # iso6395 with len !=3 should be false
    rule5 = SectionCollectiveCode()
    n = LanguageNotation(
        language="en",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="en",
        raw_value="en",
    )
    assert (
        rule5.matches(n, LanguageCapability.create_contract(include_collective=True))
        is False
    )
    assert (
        rule5.normalize(n, LanguageCapability.create_contract(include_collective=True))
        == "en"
    )


@pytest.mark.integration
def test_comprehensive_iana_and_bcp47() -> None:
    from paxman.capabilities.Language.notation import LanguageNotation
    from paxman.capabilities.Language.rules.bcp47_rfc5646_ed2009 import (
        SectionBCP47Syntax,
    )
    from paxman.capabilities.Language.rules.iana_language_subtag_registry_ed2026 import (  # noqa: E501
        SectionIANARegistry,
    )

    iana = SectionIANARegistry()
    bcp = SectionBCP47Syntax()
    from paxman.capabilities.Language.rules.iana_language_subtag_registry_ed2026 import (  # noqa: E501
        SectionIANARegistryPrivate,
    )

    iana_private = SectionIANARegistryPrivate()
    # Complex valid tag hits all IANA branches
    n = LanguageNotation(
        language="zh",
        extlang="cmn",
        script="Hans",
        region="CN",
        variant="pinyin",
        extension="a-foo",
        privateuse="x-bar",
        grandfathered="",
        compact="zh-cmn-Hans-CN-pinyin-a-foo-x-bar",
        raw_value="zh-cmn-hans-cn-pinyin-a-foo-x-bar",
    )
    # This should be valid for both bcp and private iana
    assert bcp.matches(n, LanguageCapability.create_contract()) is True
    assert (
        iana.matches(n, LanguageCapability.create_contract(include_private=True))
        is False
    )
    assert (
        iana_private.matches(
            n, LanguageCapability.create_contract(include_private=True)
        )
        is True
    )
    assert (
        iana_private.normalize(
            n, LanguageCapability.create_contract(include_private=True)
        )
        == "zh-cmn-Hans-CN-pinyin-a-foo-x-bar"
    )
    # Language empty with script/region
    n2 = LanguageNotation(
        language="",
        extlang="",
        script="Hans",
        region="CN",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="Hans-CN",
        raw_value="hans-cn",
    )
    # BCP47 with language empty but script/region? IANA checks
    # script/region even without language, so Hans-CN is valid
    assert iana.matches(n2, LanguageCapability.create_contract()) is True
    # Deprecated with extlang
    n3 = LanguageNotation(
        language="iw",
        extlang="cmn",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="iw-cmn",
        raw_value="iw-cmn",
    )
    assert iana.matches(n3, LanguageCapability.create_contract()) is True
    assert iana.normalize(n3, LanguageCapability.create_contract()) == "he-cmn"
    # Private language with all — private rule validates, generic rejects
    n4 = LanguageNotation(
        language="qaa",
        extlang="qab",
        script="Qaaa",
        region="ZZ",
        variant="ulster",
        extension="a-foo",
        privateuse="x-bar",
        grandfathered="",
        compact="qaa-qab-Qaaa-ZZ-ulster-a-foo-x-bar",
        raw_value="qaa-qab-qaaa-zz-ulster-a-foo-x-bar",
    )
    assert (
        iana.matches(n4, LanguageCapability.create_contract(include_private=True))
        is False
    )
    assert (
        iana_private.matches(
            n4, LanguageCapability.create_contract(include_private=True)
        )
        is True
    )


@pytest.mark.integration
def test_format_value_additional_edges() -> None:
    cap = LanguageCapability()
    from paxman.capabilities.Language.notation import LanguageNotation

    # alpha2 with term fallback
    n = LanguageNotation(
        language="ger",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="ger",
        raw_value="ger",
    )
    assert cap.format_value("ger", "alpha2", n) == "de"
    # alpha3 with 2-letter that has no mapping, fallback to BIB
    n2 = LanguageNotation(
        language="zz",
        extlang="",
        script="",
        region="",
        variant="",
        extension="",
        privateuse="",
        grandfathered="",
        compact="zz",
        raw_value="zz",
    )
    assert cap.format_value("zz", "alpha3", n2) == "zz"
    assert cap.format_value("zz", "alpha3-bib", n2) == "zz"
    assert cap.format_value("zz", "name", n2) == "zz"
    # name with term that maps
    assert cap.format_value("fra", "name", n) == "French"
    # bcp47 identity with empty
    assert cap.format_value("", "bcp47", n) == ""


@pytest.mark.integration
def test_numeric_region_and_script_private() -> None:
    _register()
    # numeric region 419 via BCP47
    r = paxman.canonicalize("es-419", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS
    assert r.canonicalized_value == "es-419"
    # private language qaa with flag
    reset_registry()
    _register()
    r3 = paxman.canonicalize(
        "qaa", LanguageCapability.create_contract(include_private=True)
    )
    assert r3.status == Resolution.SUCCESS
    assert r3.canonicalized_value == "qaa"
