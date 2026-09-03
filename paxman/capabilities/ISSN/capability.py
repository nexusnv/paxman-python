"""ISSN capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ISSN.contract import ISSNContract
from paxman.capabilities.ISSN.grammar.issn_recognition import ISSNRecognitionGrammar
from paxman.capabilities.ISSN.notation import ISSNNotation
from paxman.capabilities.ISSN.rules.iso_3297_ed2022 import Section4CheckDigit
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ISSNCapability", "ISSNContract", "ISSNNotation"]


class ISSNCapability(Capability[ISSNNotation]):
    """ISSN canonicalization capability.

    Canonicalizes ISSN input to the hyphenated form ``XXXX-XXXX`` per
    ISO 3297:2022 (7th edition 2022-06, ISSN International Centre, Paris)
    with full provenance.

    Recognition: :class:`ISSNRecognitionGrammar` (``LabelMatcher``,
    ``ISSN``/``ISSN-L``/``ISSN-H`` label, ``[\\s:-]*`` glued allow,
    ``\\d{4}-?\\d{3}[0-9Xx]`` strict hyphen at pos 4, ``BoundarySpec.WORD``,
    ``re.IGNORECASE|ASCII``). Validation: :class:`Section4CheckDigit`
    (mod-11 weights 8→2, ``10→X``). Output via :meth:`format_value`
    seam (``hyphenated`` default, ``compact`` strips hyphen, ``urn``
    wraps ``urn:issn:``) — rules never read ``output_format``.
    Single entity per call (``single_value=True``); multi-ISSN input
    → ``AMBIGUOUS``/``MultipleMentionsError`` (segment first, see
    ``docs/recipes/segmentation.md``).
    """

    name = "issn"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[ISSNNotation]]:
        return [ISSNRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ISSNNotation]]:
        return [Section4CheckDigit()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> ISSNContract:
        """Factory for contracts with proper defaults.

        Common block (keyword-only, fixed order per HOW_TO_ADD_NEW_CAPABILITY.md §3):
        ``excluded_rules``, ``pinned_rules``, ``year``, ``output_format``,
        ``extra_grammars``, ``suppress_common_words``. ``output_format``
        resolves via ``CapabilityContract.__post_init__`` (``None``/``"default"``
        → ``"hyphenated"``, offered ``"compact"``/``"urn"`` pass, else
        ``ContractError``). ``year`` filters rules by
        ``publication_year`` (``ISO 3297:2022`` → ``2022``; ``year=2021``
        → ``INVALID`` even though check digit stable since earlier editions,
        per engine temporal filtering). ``extra_grammars`` opts in community
        grammars idempotently. No ISSN-specific ``include_*`` flags (single
        always-active grammar, ``active_grammars=None``).
        """
        return ISSNContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ISSNNotation,
    ) -> str:
        """Render the hyphenated canonical value in the requested format.

        The default ``"hyphenated"`` path is identity. ``"compact"`` strips
        the hyphen; ``"urn"`` wraps ``urn:issn:``. Never affects candidate
        identity or provenance.
        """
        if output_format == "compact":
            return value.replace("-", "")
        if output_format == "urn":
            return f"urn:issn:{value}"
        return value
