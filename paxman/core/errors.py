"""Core exception hierarchy for Paxman."""


class PaxmanError(Exception):
    """Base exception for all Paxman errors."""


class ContractError(PaxmanError):
    """Raised when contract is malformed or invalid."""


class CapabilityError(PaxmanError):
    """Raised when no capability can claim the process."""


class RecognitionError(PaxmanError):
    """Raised when grammar fails to parse input.

    ``original_error`` is the underlying exception for failures inside
    ``Grammar.recognize()``; it is ``None`` for structural failures the
    engine itself detects (e.g. a malformed match returned by a grammar).
    """

    def __init__(
        self, rule: str, message: str, original_error: Exception | None = None
    ) -> None:
        """Store rule and original error; render as "[rule] message"."""
        self.rule = rule
        self.original_error = original_error
        super().__init__(f"[{rule}] {message}")


class MultipleMentionsError(PaxmanError):
    """Raised when a single call carries more than one recognized entity.

    Paxman resolves one entity per call (the single-value invariant, ADR-0004):
    the caller is responsible for splitting free text into individual mentions
    before calling ``canonicalize()``. When recognition yields more than one
    distinct mention (recognition span) that resolves to more than one distinct
    canonical value, the input was not pre-segmented and the engine fails fast
    instead of returning a misleading aggregate ``AMBIGUOUS`` status.

    This is a usage/contract signal, distinct from ``ContractError`` (malformed
    contract configuration) and from the ``AMBIGUOUS`` ``Resolution`` status
    (a legitimate single-mention spec conflict).

    See ``docs/recipes/segmentation.md`` for the split-then-canonicalize pattern.
    """


class ValidationError(PaxmanError):
    """Raised when validation rule encounters unexpected error."""

    def __init__(self, rule: str, message: str, original_error: Exception) -> None:
        """Store rule and original error; render as "[rule] message"."""
        self.rule = rule
        self.original_error = original_error
        super().__init__(f"[{rule}] {message}")
