"""Element capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.Element.contract import ElementContract
from paxman.capabilities.Element.grammar.element_recognition import (
    ElementRecognitionGrammar,
)
from paxman.capabilities.Element.notation import ElementNotation
from paxman.capabilities.Element.rules.data.periodic_table_ed2022 import (
    SYMBOL_TO_NAME,
)
from paxman.capabilities.Element.rules.iupac_periodic_table_ed2022 import (
    SectionPtoeRegistry,
)
from paxman.capabilities.Element.rules.iupac_red_book_2005 import (
    SectionIR31NamesAndSymbols,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class ElementCapability(Capability[ElementNotation]):
    """Element canonicalization capability.

    Canonicalizes human element designations (IUPAC symbols, lowercase
    English names, labeled atomic numbers) to the proper-case IUPAC symbol
    with Red Book + Periodic Table provenance.
    """

    name = "element"

    def get_grammars(self) -> list[Grammar[ElementNotation]]:
        """Return the default grammar instances."""
        return [ElementRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ElementNotation]]:
        """Return the default validation rule instances."""
        return [SectionIR31NamesAndSymbols(), SectionPtoeRegistry()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> ElementContract:
        """Factory method for creating contracts with proper defaults.

        Args:
            excluded_rules: Rule names to exclude.
            pinned_rules: Pin to specific rules (takes precedence over
                excluded_rules).
            year: Year for temporal filtering.
            output_format: Output format for canonical values. Optional;
                None/"default"/"symbol" resolve to "symbol".
            extra_grammars: Community grammar names (opt-in) to run
                alongside the shipped grammars, in order (SEAM — the
                surface guard's common block ends with this parameter).
            suppress_common_words: Suppress common-word mentions.

        Returns:
            Configured ElementContract instance.
        """
        return ElementContract(
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
        notation: ElementNotation,
    ) -> str:
        """Render a default symbol canonical value in the requested format.

        The default ``"symbol"`` path is the identity: the rule-produced
        proper-case symbol is returned unchanged. ``"name"`` maps the
        symbol through the IUPAC spelling table (aliases such as
        ``aluminum`` resolve but never render).

        Args:
            value: The default canonical value produced by
                ``Rule.normalize()`` (a proper-case IUPAC symbol).
            output_format: The contract's resolved output format
                (``"symbol"`` or ``"name"``).
            notation: The original element notation that produced the
                canonical value, retained for interface compatibility.

        Returns:
            The value rendered in the requested format.
        """
        if output_format == "name":
            return SYMBOL_TO_NAME.get(value, value)
        return value
