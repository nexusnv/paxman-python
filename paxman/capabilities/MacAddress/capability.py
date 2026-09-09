"""MacAddress capability - wiring, contract factory, presentation seam."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.MacAddress.contract import MacAddressContract
from paxman.capabilities.MacAddress.grammar import MacAddressRecognitionGrammar
from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.capabilities.MacAddress.rules.ieee_802_ed2024 import (
    Section82EUIStructure,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule


class MacAddressCapability(Capability[MacAddressNotation]):
    name = "mac_address"  # lowercase identifier - what users pass to the registry

    def get_grammars(self) -> list[Grammar[MacAddressNotation]]:
        return [MacAddressRecognitionGrammar()]  # single grammar; both lengths

    def get_rules(self) -> list[Rule[MacAddressNotation]]:
        # v1 ships the structure rule only; the OUI registry layer is deferred.
        return [Section82EUIStructure()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
        suppress_common_words: bool = False,
    ) -> MacAddressContract:
        return MacAddressContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
            suppress_common_words=suppress_common_words,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: MacAddressNotation
    ) -> str:
        compact = value.replace(":", "")
        octets = [compact[i : i + 2] for i in range(0, len(compact), 2)]
        if output_format == "hyphen":
            return "-".join(octets)
        if output_format == "bare":
            return compact
        if output_format == "cisco":
            hextets = [compact[i : i + 4] for i in range(0, len(compact), 4)]
            return ".".join(hextets)
        if output_format == "eui64":
            if len(compact) == 12:
                return ":".join([*octets[:3], "FF", "FE", *octets[3:]])
            return value  # already EUI-64 - deterministic identity
        return value  # colon default is identity - normalize() returns colon form
