"""Capability base class — interface for domain modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Generic, Protocol, runtime_checkable

from paxman.core.capability_contract import CapabilityContract
from paxman.core.domain import Grammar, NotationT, Rule


class Capability(ABC, Generic[NotationT]):
    """Base class for all capabilities.

    Each capability defines a domain module (e.g., Email, Date, Country)
    that registers grammars for recognition and rules for validation.

    The generic parameter ``NotationT`` is the capability's notation type
    (e.g., ``EmailNotation``, ``DateNotation``).  Subclasses declare it
    explicitly::

        class EmailCapability(Capability[EmailNotation]): ...

    This ensures that ``get_grammars()`` and ``get_rules()`` return
    correctly-typed collections, giving compile-time safety that every
    grammar and rule operates on the same notation shape.
    """

    name: str

    @abstractmethod
    def get_grammars(self) -> list[Grammar[NotationT]]:
        """Return default grammars for this capability."""
        ...

    @abstractmethod
    def get_rules(self) -> list[Rule[NotationT]]:
        """Return default validation rules for this capability."""
        ...

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: NotationT,
    ) -> str:
        """Render a default canonical value in the requested format.

        Capabilities that offer alternative output formats override this to
        convert the rule-produced default canonical value. The default
        implementation is the identity: capabilities without alternative
        formats (e.g. Email, IP) keep their canonical value unchanged.

        Args:
            value: The default canonical value produced by ``Rule.normalize()``.
            output_format: The contract's resolved output format. Built-in
                contracts resolve omitted/default formats before the engine
                runs, so this is never ``None`` for registered capabilities.
            notation: The original notation that produced the canonical value,
                available for capabilities whose formatting needs notation
                fields beyond the canonical string.

        Returns:
            The value rendered in the requested format.
        """
        return value


@runtime_checkable
class ContractFactory(Protocol):
    """Factory protocol for capability contract creation.

    Every shipped capability class (fifteen as of 0.2.0) satisfies it by declaring
    ``create_contract`` with the unanimous common parameter block.
    """

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
    ) -> CapabilityContract:
        """Create a configured contract with the unanimous common block."""
        ...
