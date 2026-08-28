"""CapabilityContract base class — the unanimous contract surface.

Every capability contract MUST inherit from :class:`CapabilityContract` so
the standard fields and ``output_format`` resolution are implemented
identically across capabilities.  This is the homogeneity mandate that makes
the contract surface structural rather than documentary: future contributors
cannot accidentally reintroduce the per-capability drift that previously
existed.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class CapabilityContract(ABC):
    """Base class for all capability contracts.

    Provides the unanimous contract surface shared by every capability:

    - ``output_format`` is **always optional** and validated/normalized by a
      single base ``__post_init__`` via :func:`resolve_output_format`.
    - ``active_grammars`` is optional: the base-class default (``None``)
      activates every shipped grammar in ``get_grammars()`` declaration
      order, so adding a grammar to a capability is a single-edit change.

    Subclasses MUST:

    - Override the ``DEFAULT_OUTPUT_FORMAT`` and ``OFFERED_OUTPUT_FORMATS``
      class variables.
    - Set ``capability_name`` via ``field(default="<name>", init=False)``.
    - Call ``super().__post_init__()`` first if they add their own
      ``__post_init__`` validation.

    Subclasses MAY override ``active_grammars`` to narrow the surface —
    typically to gate grammars behind ``include_*`` feature flags.

    The class satisfies the :class:`Contract` protocol structurally.
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str]
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]]

    capability_name: str = field(init=False)
    excluded_rules: tuple[str, ...] = ()
    pinned_rules: tuple[str, ...] | None = None
    year: int | None = None
    output_format: str | None = None
    extra_grammars: tuple[str, ...] = ()
    """Community grammar names to opt in, appended after ``active_grammars``.
    Unknown names are silently skipped by the engine."""
    suppress_common_words: bool = False

    def __post_init__(self) -> None:
        """Validate and normalize ``output_format``.

        Delegates to :func:`resolve_output_format` so every capability
        contract applies the same ``output_format`` policy: ``None``,
        ``"default"``, and the capability's ``DEFAULT_OUTPUT_FORMAT`` all
        resolve to the concrete default; offered alternatives resolve to
        themselves; any other value raises :class:`ContractError`.

        ``resolve_output_format`` is imported here rather than at module level
        to break the import cycle between this module and
        ``paxman.core.contract``, which re-exports ``CapabilityContract``.

        Raises:
            ContractError: If ``output_format`` is not an acceptable value.
        """
        from paxman.core.contract import resolve_output_format

        object.__setattr__(
            self,
            "output_format",
            resolve_output_format(
                self.output_format,
                capability_name=self.capability_name,
                offered_formats=type(self).OFFERED_OUTPUT_FORMATS,
                default_format=type(self).DEFAULT_OUTPUT_FORMAT,
            ),
        )

    @property
    def active_grammars(self) -> Sequence[str] | None:
        """Grammar names to activate.

        ``None`` — the base-class default — tells the engine to activate
        every shipped grammar in the capability's ``get_grammars()``
        declaration order. Override to narrow the surface (e.g. gate
        grammars behind ``include_*`` feature flags).
        """
        return None
