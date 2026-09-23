"""Integration tests for the Phone capability pipeline."""

import pytest

from paxman.capabilities.Phone.capability import PhoneCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError
from paxman.engine.orchestrator import run_capability


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Reset the capability registry before and after each test."""
    reset_registry()
    yield
    reset_registry()


class TestPhonePipeline:
    """Full-pipeline tests for the Phone capability.

    Note on the single-value invariant (ADR-0004): paxman resolves one entity
    per call. A single-number input maps to exactly one grammar/shape and the
    two E.164 rules (Section 6.1 / 6.2) always agree, so single-number inputs
    are never AMBIGUOUS. Multi-number input is a segmentation violation: the
    engine fails fast with ``MultipleMentionsError`` rather than returning
    AMBIGUOUS (genuine single-mention ambiguity is still possible, e.g. a
    number whose E.164 and tel-URI readings disagreed would surface as
    AMBIGUOUS from one span).
    """

    @pytest.mark.integration
    def test_success_e164(self) -> None:
        """International number resolves to E.164."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("+1 555 123 4567", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+15551234567"

    @pytest.mark.integration
    def test_success_national_with_default_country(self) -> None:
        """National number resolves when default_country is set."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(default_country="US")
        result = run_capability("(555) 234-5678", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+15552345678"

    @pytest.mark.integration
    def test_success_tel_uri(self) -> None:
        """tel: URI resolves to E.164."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("tel:+1-201-555-0123", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+12015550123"

    @pytest.mark.integration
    def test_tel_uri_single_candidate(self) -> None:
        """tel: URIs yield exactly one candidate (no grammar overlap)."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("tel:+1-201-555-0123", contract)
        assert result.status == Resolution.SUCCESS
        assert len(result.candidates) == 1

    @pytest.mark.integration
    def test_no_plus_tel_uri_is_not_global(self) -> None:
        """No-plus tel: URIs are local numbers — never global candidates.

        Regression for RFC 3966 §3.1 (global numbers require '+'); local
        numbers are out of scope, so the tel-URI rule must not fire.
        """
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("tel:2125550123", contract)
        assert result.status == Resolution.INVALID
        assert all(c.validation_rule != "Section 3-tel-uri" for c in result.candidates)

    @pytest.mark.integration
    def test_no_plus_tel_uri_local_number_via_national(self) -> None:
        """NANP-shaped local tel: URI resolves via the national grammar.

        With default_country="US", the number content of a local tel: URI
        is recognized as a national number — no AMBIGUOUS (previously the
        tel-URI grammar produced a conflicting foreign-country reading).
        """
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(default_country="US")
        result = run_capability("tel:2125556789", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+12125556789"
        assert len(result.candidates) == 1

    @pytest.mark.integration
    def test_email_plus_tag_not_a_phone(self) -> None:
        """Email plus-addresses must not canonicalize to phone numbers."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("user+1555@example.com", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_decimal_number_not_a_phone(self) -> None:
        """A decimal number must not canonicalize to a phone number."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("0.00442079460958", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_short_nsn_rejected(self) -> None:
        """A degenerate 1-digit NSN ('+12') is INVALID, not SUCCESS."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("+12", contract)
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_multi_number_ambiguous(self) -> None:
        """Two different numbers in one input fail fast (single-value invariant).

        A single call must resolve one entity. Two numbers are un-segmented
        multi-entity input, so the engine raises MultipleMentionsError instead
        of returning AMBIGUOUS.
        """
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(default_country="US")
        with pytest.raises(MultipleMentionsError):
            run_capability("+15552345678 and (555) 234-5679", contract)

    @pytest.mark.integration
    def test_tel_uri_extension_preserved(self) -> None:
        """e164 and tel-URI inputs never produce conflicting candidates."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(output_format="rfc3966")
        result = run_capability("tel:+15551234567;ext=890", contract)
        # Extension is preserved; no conflicting candidate drops it.
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "tel:+15551234567;ext=890"
        assert len(result.candidates) == 1

    @pytest.mark.integration
    def test_two_tel_uris_differing_only_by_extension_coalesce(self) -> None:
        """Extension pairs share one canonical E.164: one entity, not two.

        The canonical value does not carry ``;ext=`` — ``rfc3966`` is the
        only extension-preserving format, re-appending it from the
        notation — so two tel URIs differing only by extension resolve to
        the SAME canonical value. Identity reads canonical values, so the
        pair coalesces to SUCCESS under every offered format, rendered as
        the first mention's rfc3966 URI; the default contract agrees
        (SUCCESS, bare E.164). Previously rfc3966 raised
        MultipleMentionsError while the default format succeeded —
        ``output_format`` had leaked into candidate identity.
        Genuinely distinct numbers still fail fast (see
        ``test_multi_number_ambiguous`` above).
        """
        register_capability(PhoneCapability())
        text = "tel:+15551234567;ext=890 and tel:+15551234567;ext=891"
        rfc3966 = run_capability(
            text, PhoneCapability.create_contract(output_format="rfc3966")
        )
        default = run_capability(text, PhoneCapability.create_contract())

        assert rfc3966.status is Resolution.SUCCESS
        assert rfc3966.canonicalized_value == "tel:+15551234567;ext=890"
        assert default.status is Resolution.SUCCESS
        assert default.canonicalized_value == "+15551234567"

    @pytest.mark.integration
    def test_pinned_rules_only(self) -> None:
        """Pinning to one rule runs only that rule."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(
            pinned_rules=["Section 6.1-international-number"]
        )
        result = run_capability("+15551234567", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+15551234567"
        # Only the pinned rule produced candidates.
        assert {c.validation_rule for c in result.candidates} == {
            "Section 6.1-international-number"
        }

    @pytest.mark.integration
    def test_excluded_rule_skipped(self) -> None:
        """Excluding a rule prevents it from producing candidates."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(
            excluded_rules=["Section 6.2-country-code"]
        )
        result = run_capability("+15551234567", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+15551234567"
        assert "Section 6.2-country-code" not in {
            c.validation_rule for c in result.candidates
        }

    @pytest.mark.integration
    def test_success_international_00(self) -> None:
        """00-prefixed international number resolves to E.164."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("00 44 20 7946 0958", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "+442079460958"

    @pytest.mark.integration
    def test_missing(self) -> None:
        """Nothing recognized."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("hello world", contract)
        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_invalid_unassigned_cc(self) -> None:
        """Recognized but no rule validates (unassigned country code)."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("+999123456789", contract)
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_invalid_national_without_default_country(self) -> None:
        """National input without default_country is invalid, not missing."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result = run_capability("(555) 234-5678", contract)
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_invalid_nanp_structure(self) -> None:
        """N11 NPA is recognized but fails NANP validation."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(default_country="US")
        result = run_capability("(911) 555-1234", contract)
        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_output_format_rfc3966(self) -> None:
        """output_format=rfc3966 renders tel: URI."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract(output_format="rfc3966")
        result = run_capability("+15551234567", contract)
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "tel:+15551234567"

    @pytest.mark.integration
    def test_version_stamp(self) -> None:
        """Version stamp is present and canonicalization is deterministic."""
        register_capability(PhoneCapability())
        contract = PhoneCapability.create_contract()
        result1 = run_capability("+15551234567", contract)
        result2 = run_capability("+15551234567", contract)
        assert result1 == result2
        assert result1.status == result2.status
        assert result1.canonicalized_value == result2.canonicalized_value
        assert [c.value for c in result1.candidates] == [
            c.value for c in result2.candidates
        ]
        assert len(result1.candidates) == 2
        assert {c.value for c in result1.candidates} == {"+15551234567"}
        assert {p.authority for c in result1.candidates for p in c.provenance} == {
            "ITU-T"
        }
        assert isinstance(result1.version_stamp.paxman_version, str)
