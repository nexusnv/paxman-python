"""ISSN contract configuration."""

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ISSNContract(CapabilityContract):
    """Contract for the ISSN capability.

    ``capability_name`` fixed to ``"issn"``. Output formats
    ``hyphenated`` (default, ``XXXX-XXXX``), ``compact`` (``XXXXXXXX``),
    ``urn`` (``urn:issn:XXXX-XXXX``) via ``CapabilityContract.__post_init__``
    (``None``/``"default"`` → default, unknown → ``ContractError``).
    Common block fields ``excluded_rules``, ``pinned_rules``, ``year``,
    ``output_format``, ``extra_grammars``, ``suppress_common_words``
    inherited from ``CapabilityContract``; ``year`` filters rules by
    ``publication_year`` (``ISO 3297:2022`` → 2022, so ``year=2021``
    → ``INVALID`` per temporal filtering). No ISSN-specific
    ``include_*`` flags (single grammar, ``active_grammars=None`` →
    engine runs every ``get_grammars()`` grammar in order).
    """

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "hyphenated"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"compact", "urn"})

    capability_name: str = field(default="issn", init=False)
