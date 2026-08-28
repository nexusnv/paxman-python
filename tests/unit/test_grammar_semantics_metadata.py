"""Tests for grammar ``semantics`` metadata on shipped grammars."""

from __future__ import annotations

from typing import Any

import pytest

from paxman.capabilities import (
    IP,
    ISBN,
    URL,
    Country,
    Currency,
    Date,
    Email,
    Money,
    Phone,
    SIUnit,
)
from paxman.core.domain import Grammar, RecognitionMatch

# Semantics ids that legitimately differ from a grammar's ``name`` (semantic
# affinity routing, ADR-0003): coalesced ids shared by several grammars
# (``iso8601_calendar_date``, ``rfc5322_addr_spec``, ``e164_international``)
# and renamed singletons (``us_calendar_date``, ``european_calendar_date``).
# A grammar in this set declares ``semantics`` differing from its ``name``
# without failing the identity check. ``date_calendar_date`` is the
# consolidated Date candidate grammar (ADR §9.6).
_COALESCED_SEMANTICS: frozenset[str] = frozenset(
    {
        "iso8601_calendar_date",
        "us_calendar_date",
        "european_calendar_date",
        "rfc5322_addr_spec",
        "e164_international",
        "date_calendar_date",
    }
)


class TestGrammarSemanticsMetadata:
    @pytest.mark.unit
    def test_shipped_grammars_declare_semantics_identity(self) -> None:
        """Every shipped grammar declares ``semantics``: identity with its name
        for non-coalesced grammars, or one of the coalesced ids (an explicit
        allowlist) for grammars sharing a semantic group."""
        capabilities = [
            Country,
            Currency,
            Date,
            Email,
            IP,
            ISBN,
            Money,
            Phone,
            SIUnit,
            URL,
        ]
        for capability in capabilities:
            for grammar in capability().get_grammars():
                assert isinstance(grammar.semantics, str)
                assert grammar.semantics != ""
                assert (
                    grammar.semantics == grammar.name
                    or grammar.semantics in _COALESCED_SEMANTICS
                )

    @pytest.mark.unit
    def test_renamed_singletons_pin_exact_semantics_ids(self) -> None:
        """The renamed singleton grammars pin their exact ``semantics`` ids.

        The allowlist above would accept a cross-swap (e.g. ``us_recognition``
        declaring ``european_calendar_date``), and with dual-target date rules
        such a swap is behaviorally inert today — but the moment any rule
        targets a single id, a wrong declaration silently mis-canonicalizes
        US/EU dates. Pin the name→id mapping explicitly (ADR-0003
        consistency-guard rationale).
        """
        grammars = list(Date().get_grammars())
        by_name = {grammar.name: grammar.semantics for grammar in grammars}
        if len(grammars) == 1 and grammars[0].name == "date_recognition":
            # Consolidated DateGrammar with candidates (ADR §9.6)
            assert grammars[0].semantics == "date_calendar_date"
            cand = grammars[0].matchers[0]  # type: ignore[union-attr]
            cand_by_name = dict(
                zip(cand.candidate_names, cand.candidate_semantics, strict=True)
            )
            assert cand_by_name["us_recognition"] == "us_calendar_date"
            assert cand_by_name["european_recognition"] == "european_calendar_date"
        else:
            assert by_name["us_recognition"] == "us_calendar_date"
            assert by_name["european_recognition"] == "european_calendar_date"


class TestGrammarSemanticsEnforcement:
    @pytest.mark.unit
    def test_bare_grammar_subclass_raises_type_error(self) -> None:
        """A Grammar subclass missing ``semantics`` fails at class-definition time."""

        with pytest.raises(TypeError, match="must define Grammar metadata"):

            class _BareGrammar(Grammar[Any]):
                name = "bare_grammar"

                def recognize(self, text: str) -> list[RecognitionMatch[Any]]:
                    return []

    @pytest.mark.unit
    def test_missing_semantics_raises(self) -> None:
        """The missing-``semantics`` error message names the attribute."""

        with pytest.raises(TypeError, match="semantics"):

            class _MissingSemanticsGrammar(Grammar[Any]):
                name = "missing_semantics_grammar"

                def recognize(self, text: str) -> list[RecognitionMatch[Any]]:
                    return []

    @pytest.mark.unit
    def test_empty_semantics_raises(self) -> None:
        """An empty ``semantics`` string is valid type-wise but a bug:
        the grammar would carry no semantics. The runtime guard must reject it."""
        with pytest.raises(TypeError, match="non-empty"):

            class _EmptySemanticsGrammar(Grammar[Any]):
                name = "empty_semantics_grammar"
                semantics = ""

                def recognize(self, text: str) -> list[RecognitionMatch[Any]]:
                    return []

    @pytest.mark.unit
    @pytest.mark.parametrize("value", [42, frozenset()])
    def test_semantics_must_be_str(self, value: object) -> None:
        """A non-str ``semantics`` value fails during Grammar subclass creation."""
        namespace: dict[str, Any] = {
            "name": "test_grammar",
            "recognize": lambda self, text: [],
            "semantics": value,
        }

        with pytest.raises(TypeError, match="semantics must be str"):
            type("_InvalidSemantics", (Grammar,), namespace)

    @pytest.mark.unit
    def test_inherited_semantics_satisfies_enforcement(self) -> None:
        """A subclass inheriting ``semantics`` needs no own declaration.

        Locks the ``vars(cls).get`` fallback: the resolved value is read from
        the class namespace first, then from the MRO.
        """

        class _CompliantGrammar(Grammar[Any]):
            name = "compliant_grammar"
            semantics = "compliant_grammar"

            def recognize(self, text: str) -> list[RecognitionMatch[Any]]:
                return []

        class _InheritedSemanticsGrammar(_CompliantGrammar):
            pass

        assert _InheritedSemanticsGrammar.semantics == "compliant_grammar"
