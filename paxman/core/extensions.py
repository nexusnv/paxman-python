"""Community grammar and rule extension registries.

Community contributors register additional grammars (and the rules that
validate them) for existing capabilities. Registration is explicit and must
complete before the first ``canonicalize()`` call: the registries freeze with
the capability registry (see ``paxman.core.discovery``).

A contract opts a registered grammar in by naming it in
``CapabilityContract.extra_grammars``. Unknown names in ``extra_grammars`` are
silently skipped so a contract that names an uninstalled grammar still runs
identically (deterministically).
"""

from __future__ import annotations

from typing import Any

from paxman.core.domain import Grammar, Rule
from paxman.core.errors import CapabilityError

_grammar_registry: dict[str, dict[str, type[Grammar[Any]]]] = {}
_rule_registry: dict[str, dict[str, type[Rule[Any]]]] = {}
_frozen: bool = False


def _ensure_not_frozen() -> None:
    """Raise CapabilityError if the extension registries are frozen."""
    if _frozen:
        raise CapabilityError(
            "Extension registries are frozen. Cannot register grammars or "
            "rules after the first canonicalize() call."
        )


def register_grammar(capability_name: str, grammar: Any) -> None:
    """Register a community grammar for a capability.

    The ``grammar`` parameter is ``Any`` because this is a runtime
    validation entry point: untyped callers may pass non-classes or
    non-Grammar classes and the isinstance guard below provides the
    safety net.

    Raises:
        CapabilityError: if the registries are frozen, ``grammar`` is not a
            Grammar subclass, its ``name`` is missing/empty/mixed-case, or a
            grammar with that name is already registered for the capability.
    """
    _ensure_not_frozen()
    if not (isinstance(grammar, type) and issubclass(grammar, Grammar)):
        raise CapabilityError(f"Expected Grammar subclass, got {grammar!r}")
    name: Any = grammar.name
    if not isinstance(name, str) or not name:
        raise CapabilityError(
            f"Grammar {grammar.__name__} must declare a non-empty string name"
        )
    if name != name.lower():
        raise CapabilityError(f"Grammar name {name!r} must be lowercase")
    per_capability = _grammar_registry.setdefault(capability_name, {})
    if name in per_capability:
        raise CapabilityError(
            f"Grammar '{name}' already registered for capability '{capability_name}'"
        )
    per_capability[name] = grammar


def register_rule(capability_name: str, rule: Any) -> None:
    """Register a community validation rule for a capability.

    The ``rule`` parameter is ``Any`` because this is a runtime validation
    entry point: untyped callers may pass non-classes or non-Rule classes
    and the isinstance guard below provides the safety net. Rule metadata
    (``target_semantics``, ``requires_features``, ...) is enforced by
    ``Rule.__init_subclass__`` at class-definition time; this function
    validates the class type and name uniqueness only.

    Raises:
        CapabilityError: if the registries are frozen, ``rule`` is not a Rule
            subclass, its ``name`` is missing/empty, or a rule with that name
            is already registered for the capability.
    """
    _ensure_not_frozen()
    if not (isinstance(rule, type) and issubclass(rule, Rule)):
        raise CapabilityError(f"Expected Rule subclass, got {rule!r}")
    name: Any = rule.name
    if not isinstance(name, str) or not name:
        raise CapabilityError(
            f"Rule {rule.__name__} must declare a non-empty string name"
        )
    per_capability = _rule_registry.setdefault(capability_name, {})
    if name in per_capability:
        raise CapabilityError(
            f"Rule '{name}' already registered for capability '{capability_name}'"
        )
    per_capability[name] = rule


def get_extended_grammars(capability_name: str) -> list[Grammar[Any]]:
    """Return fresh instances of the community grammars for a capability."""
    return [cls() for cls in _grammar_registry.get(capability_name, {}).values()]


def get_extended_rules(capability_name: str) -> list[Rule[Any]]:
    """Return fresh instances of the community rules for a capability."""
    return [cls() for cls in _rule_registry.get(capability_name, {}).values()]


def freeze_extensions() -> None:
    """Freeze the extension registries (called by ``discovery.freeze_registry``)."""
    global _frozen
    _frozen = True


def reset_extensions() -> None:
    """Reset the extension registries for testing (mirrors ``discovery``)."""
    global _frozen
    _grammar_registry.clear()
    _rule_registry.clear()
    _frozen = False
