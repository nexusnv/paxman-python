"""Capability discovery registry.

Stores registered capabilities by name. Freezes after the first
``canonicalize()`` call so no new capabilities can be registered.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from paxman.core.capability import Capability
from paxman.core.errors import CapabilityError
from paxman.core.extensions import freeze_extensions, reset_extensions

_registry: dict[str, Capability[Any]] = {}
_frozen: bool = False
_recognition_revision: str = "0"
_snapshot_hashes: dict[tuple[str, int, int], str] = {}


def register_capability(capability: Any) -> None:
    """Register a capability.

    The parameter is ``Any`` because this is a runtime validation entry
    point: untyped callers may pass non-Capability objects and the
    isinstance guard below provides the safety net.

    Raises:
        CapabilityError: If the registry is frozen, the argument is not a
            Capability instance, or a capability with the same name is
            already registered.
    """
    global _frozen
    if _frozen:
        raise CapabilityError(
            "Registry is frozen. Cannot register after first canonicalize() call."
        )
    if not isinstance(capability, Capability):
        raise CapabilityError(
            f"Expected Capability instance, got {type(capability).__name__}"
        )
    if capability.name in _registry:
        raise CapabilityError(f"Capability '{capability.name}' already registered.")
    _registry[capability.name] = capability


def get_capability(name: str) -> Capability[Any]:
    """Look up a capability by name.

    Raises:
        CapabilityError: If no capability with that name is registered.
    """
    if name not in _registry:
        raise CapabilityError(f"Unknown capability: '{name}'")
    return _registry[name]


def get_recognition_revision() -> str:
    """Return the current recognition revision hash."""
    return _recognition_revision


def freeze_registry() -> None:
    """Freeze the registry so no more capabilities can be registered.

    Also computes ``recognition_revision`` as a hash of the compiled matcher
    set (pure function of ``(spec, snapshot)`` per ADR-0009 §13). Any
    recognition-behavior change — including lexicon token changes, regex
    pattern edits, boundary presets, anchor sets, ``requires_features`` gating,
    or snapshot SHAs — changes the revision, giving callers a same-snapshot
    diff signal. Capability ``version`` strings are *not* the signal; they are
    included only as a fallback for legacy grammars without compiled matchers.
    """
    global _frozen, _recognition_revision
    if _frozen:
        return
    _frozen = True
    freeze_extensions()
    import hashlib
    import pathlib

    parts: list[str] = []
    for cap in sorted(_registry.values(), key=lambda c: c.name):
        grammars = cap.get_grammars()
        for grammar in sorted(grammars, key=lambda g: g.name):
            matchers = getattr(grammar, "matchers", None)
            if matchers:
                matchers_typed: Sequence[Any] = cast(Sequence[Any], matchers)
                for matcher in matchers_typed:
                    kind = getattr(matcher, "kind", type(matcher).__name__)
                    view = getattr(matcher, "view", None)
                    if view is None:
                        view = getattr(matcher, "view_name", None)
                    boundary = getattr(matcher, "boundary", None)
                    anchors = getattr(matcher, "anchors", None)
                    requires: frozenset[str] = getattr(
                        matcher, "requires_features", frozenset[str]()
                    )
                    requires_repr = ",".join(sorted(requires))
                    digest_val: str | None = getattr(matcher, "digest", None)
                    if digest_val is not None:
                        tokens_repr = digest_val
                    else:
                        tokens_set: Any = getattr(matcher, "tokens", None)
                        if tokens_set is not None:
                            tokens_repr = repr(tokens_set)
                        else:
                            payload = getattr(matcher, "payload", None)
                            if payload is not None:
                                tokens_repr = repr(payload)
                            else:
                                scan_fn = getattr(
                                    matcher, "scan", None
                                )  # pragma: no cover
                                if scan_fn is not None:  # pragma: no cover
                                    qualname = getattr(  # pragma: no cover
                                        scan_fn, "__qualname__", type(matcher).__name__
                                    )  # pragma: no cover
                                    max_window = getattr(matcher, "max_window", 0)
                                    boundary_repr_inner = (
                                        repr(boundary)
                                        if boundary is not None
                                        else "None"
                                    )
                                    tokens_repr = (
                                        f"{qualname}:{max_window}:{view}:"
                                        f"{boundary_repr_inner}"
                                    )
                                else:
                                    fallback_chosen = getattr(
                                        matcher, "_chosen", ""
                                    )  # pragma: no cover
                                    tokens_repr = (  # pragma: no cover
                                        f"{type(matcher).__name__}:{fallback_chosen}"
                                    )
                    # Include matcher-specific choices (e.g., lexicon _chosen)
                    chosen = getattr(matcher, "_chosen", "")
                    # Deterministic boundary/anchors repr
                    boundary_repr = repr(boundary) if boundary is not None else "None"
                    anchors_repr = repr(anchors) if anchors is not None else "None"
                    parts.append(
                        f"{cap.name}:{grammar.name}:{kind}:{view}:{boundary_repr}:"
                        f"{anchors_repr}:{requires_repr}:{chosen}:{tokens_repr}"
                    )
            else:
                # Legacy PipelineGrammar shims: include grammar identity so F2 rescan
                # grammars still contribute to revision via capability version fallback
                cap_version = getattr(cap, "version", getattr(cap, "__version__", "0"))
                parts.append(
                    f"{cap.name}:{grammar.name}:{grammar.semantics}:{cap_version}"
                )
    # Snapshot rails — include JSON hashes so data drift changes revision
    snapshot_dir = pathlib.Path(__file__).resolve().parents[1] / "shared_data"
    if snapshot_dir.is_dir():  # pragma: no cover
        for snap_path in sorted(snapshot_dir.glob("*_snapshot.json")):
            try:
                st = snap_path.stat()
                key = (str(snap_path), st.st_size, st.st_mtime_ns)
                cached = _snapshot_hashes.get(key)
                if cached is not None:
                    if st.st_mtime_ns % 1_000_000 == 0:
                        content = snap_path.read_bytes()
                        sha = hashlib.sha256(content).hexdigest()[:12]
                        if sha != cached:
                            _snapshot_hashes[key] = sha
                        else:
                            sha = cached
                    else:
                        sha = cached
                else:
                    content = snap_path.read_bytes()
                    sha = hashlib.sha256(content).hexdigest()[:12]
                    _snapshot_hashes[key] = sha
                parts.append(f"snapshot:{snap_path.name}:{sha}")
            except OSError:  # pragma: no cover
                continue  # pragma: no cover

    # Include capability-level version as tie-breaker for legacy + new mix
    for cap in sorted(_registry.values(), key=lambda c: c.name):
        cap_version = getattr(cap, "version", getattr(cap, "__version__", "0"))
        parts.append(f"cap_version:{cap.name}:{cap_version}")

    if not parts:  # pragma: no cover
        _recognition_revision = "0"  # pragma: no cover
    else:
        # Sort for total order regardless of insertion
        parts_sorted = sorted(parts)
        _recognition_revision = hashlib.sha256(
            "|".join(parts_sorted).encode()
        ).hexdigest()[:12]


def is_registry_frozen() -> bool:
    """Check if the registry is frozen."""
    return _frozen


def list_registered_capabilities() -> tuple[str, ...]:
    """List registered capability names in sorted order.

    Returns:
        Sorted tuple of capability names currently in the registry.
        Empty if nothing has been registered yet.
    """
    return tuple(sorted(_registry.keys()))


def reset_registry() -> None:
    """Reset the registry (for testing only)."""
    global _frozen, _recognition_revision
    _registry.clear()
    _frozen = False
    _recognition_revision = "0"
    reset_extensions()
