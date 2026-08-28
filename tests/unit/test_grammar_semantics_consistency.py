"""D8 — same-semantics grammars must produce identical notation field mappings
and canonicalization; guards semantic affinity routing.

The affinity-routing engine treats every grammar claiming the same
``semantics`` id as interchangeable: any member of a group may recognize an
input, and its notation is routed to the group's shared rules. A group whose
members map the same input to different notation fields (or whose shared rule
canonicalizes differently) would resolve the same text differently depending
on which member happened to recognize it — silent nondeterminism. This guard
enumerates all shipped grammar classes, groups them by ``semantics`` within
each capability, and pins every seeded group's members to a single canonical
mapping: each member must recognize at least one probe row into the group's
expected notation, and the group's shared rule must canonicalize every match
identically. Group members may recognize disjoint input sets (e.g. the dash
and slash ISO grammars), so agreement is asserted member-vs-table — no
cross-member comparison is claimed.
"""

from __future__ import annotations

from typing import Any, NamedTuple

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
from paxman.capabilities.Date.contract import DateContract
from paxman.capabilities.Date.notation import DateNotation
from paxman.capabilities.Date.rules.iso_8601_ed2019 import Section431CalendarDate
from paxman.capabilities.Email.contract import EmailContract
from paxman.capabilities.Email.notation import EmailNotation
from paxman.capabilities.Email.rules.rfc_5322_ed2008 import Section341AddrSpec
from paxman.capabilities.Phone.contract import PhoneContract
from paxman.capabilities.Phone.notation import PhoneNotation
from paxman.capabilities.Phone.rules.e164_ed2010 import Section6_1InternationalNumber
from paxman.core.capability_contract import CapabilityContract
from paxman.core.domain import Grammar, Rule

_SHIPPED_CAPABILITIES = [
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

# D7 no-coalesce ids: groups that must NEVER grow a second member. The
# date formats and the six identity singletons are distinct enough that
# coalescing them would silently change what they resolve.
_NO_COALESCE_SEMANTICS = (
    "us_calendar_date",
    "european_calendar_date",
    "name_recognition",
    "alpha2_recognition",
    "alpha3_recognition",
    "numeric_recognition",
    "isbn13_recognition",
    "isbn10_recognition",
)

# Contract class used to drive each seeded group's shared rule ``normalize()``.
# The right contract per group keeps the guard honest if a rule ever starts
# reading contract fields.
_CONTRACTS: dict[str, type[CapabilityContract]] = {
    "iso8601_calendar_date": DateContract,
    "rfc5322_addr_spec": EmailContract,
    "e164_international": PhoneContract,
}


class _ProbeRow(NamedTuple):
    """One input run through every member of a semantics group.

    ``expected_notation`` is deliberately untyped: the probe table spans
    capabilities, so each row's notation type is the group's own.
    """

    input: str
    expected_notation: object
    expected_canonical: str


# Probe rows keyed by semantics id. Each key must name a real group in the
# shipped grammar enumeration (test A); each member of a group must recognize
# the probe input into the identical notation, and the group's shared rule
# must canonicalize it identically (test B).
_PROBE_ROWS: dict[str, tuple[type[Rule[Any]], tuple[_ProbeRow, ...]]] = {
    "iso8601_calendar_date": (
        Section431CalendarDate,
        (
            _ProbeRow(
                input="2026-01-15",
                expected_notation=DateNotation(N1="2026", N2="01", N3="15"),
                expected_canonical="2026-01-15",
            ),
            _ProbeRow(
                input="2026/01/15",
                expected_notation=DateNotation(N1="2026", N2="01", N3="15"),
                expected_canonical="2026-01-15",
            ),
        ),
    ),
    "rfc5322_addr_spec": (
        Section341AddrSpec,
        (
            _ProbeRow(
                input="user@example.com",
                expected_notation=EmailNotation(
                    local_part="user", domain_part="example.com"
                ),
                expected_canonical="user@example.com",
            ),
            _ProbeRow(
                input="user at example dot com",
                expected_notation=EmailNotation(
                    local_part="user", domain_part="example.com"
                ),
                expected_canonical="user@example.com",
            ),
        ),
    ),
    "e164_international": (
        Section6_1InternationalNumber,
        (
            _ProbeRow(
                input="+15551234567",
                expected_notation=PhoneNotation(shape="e164", value="15551234567"),
                expected_canonical="+15551234567",
            ),
            _ProbeRow(
                input="0015551234567",
                expected_notation=PhoneNotation(shape="e164", value="15551234567"),
                expected_canonical="+15551234567",
            ),
        ),
    ),
}


def _group_shipped_grammars_by_capability_semantics() -> dict[
    str, dict[str, list[type[Grammar[Any]]]]
]:
    """Group shipped grammar classes per capability by their ``semantics`` id.

    The affinity-routing engine treats grammars as interchangeable only within
    one capability, so groups are scoped per capability: a semantics id reused
    across capabilities (Currency and Money both declaring ``code_recognition``
    etc.) yields separate per-capability groups that never co-route and must
    not be probed as one unit.
    """
    groups: dict[str, dict[str, list[type[Grammar[Any]]]]] = {}
    for capability in _SHIPPED_CAPABILITIES:
        per_capability: dict[str, list[type[Grammar[Any]]]] = {}
        for grammar in capability().get_grammars():
            per_capability.setdefault(grammar.semantics, []).append(type(grammar))
        groups[capability.__name__] = per_capability
    return groups


@pytest.mark.unit
def test_probe_keys_name_real_semantics_groups() -> None:
    """Every probe-table key must be a real semantics group in the enumeration."""
    groups = _group_shipped_grammars_by_capability_semantics()
    # Collect candidate semantics for Date's consolidated grammar
    candidate_semantics: set[str] = set()
    for g in Date().get_grammars():
        for m in getattr(g, "matchers", None) or ():
            cs = getattr(m, "candidate_semantics", None)
            if cs:
                candidate_semantics.update(cs)  # type: ignore[arg-type]
    assert all(
        any(key in per_capability for per_capability in groups.values())
        or key in candidate_semantics
        for key in _PROBE_ROWS
    )


@pytest.mark.unit
def test_same_semantics_grammars_agree_on_notation_and_canonical() -> None:
    """Members of a seeded semantics group pin the group's canonical mapping.

    Every member must recognize at least one probe row into the group's
    expected notation, and the group's shared rule must canonicalize every
    match to the expected canonical value. Because members may recognize
    disjoint input sets, agreement is asserted member-vs-table (against the
    group's single expected mapping), not by comparing members on one input.
    A member that recognizes none of the probes — or a probe that no member
    recognizes — fails loudly instead of passing silently.
    """
    groups = _group_shipped_grammars_by_capability_semantics()
    for semantics, (rule_cls, probes) in _PROBE_ROWS.items():
        rule = rule_cls()
        member_lists = [
            per_capability.get(semantics, ()) for per_capability in groups.values()
        ]
        # For Date's consolidated candidates, also consider candidate semantics
        if not any(member_lists):
            for g in Date().get_grammars():
                for m in getattr(g, "matchers", None) or ():
                    cs = getattr(m, "candidate_semantics", None)
                    if cs and semantics in cs:  # type: ignore[union-attr]
                        member_lists = [[type(g)]]
                        break
        assert sum(1 for members in member_lists if members) == 1, (
            f"semantics {semantics!r} spans multiple capabilities; probe rows "
            "must stay scoped to one capability"
        )
        members = [member for group_members in member_lists for member in group_members]
        for member_cls in members:
            member = member_cls()
            matched_any = False
            for probe in probes:
                matches = member.recognize(probe.input)
                if not matches:
                    continue
                matched_any = True
                assert all(m.notation == probe.expected_notation for m in matches), (
                    f"{member_cls.__name__} mapped {probe.input!r} to "
                    f"{[m.notation for m in matches]}, expected "
                    f"{probe.expected_notation!r}"
                )
                assert (
                    rule.normalize(matches[0].notation, _CONTRACTS[semantics]())
                    == probe.expected_canonical
                )
            assert matched_any, (
                f"{member_cls.__name__} (semantics {semantics!r}) recognized none "
                "of the probe rows"
            )
        for probe in probes:
            assert any(member_cls().recognize(probe.input) for member_cls in members), (
                f"probe {probe.input!r} matched by no member of {semantics!r}"
            )


@pytest.mark.unit
def test_every_shipped_grammar_belongs_to_one_semantics_group() -> None:
    """No shipped grammar is dropped or duplicated by the semantics grouping.

    Every grammar enumerated via ``get_grammars()`` must land in exactly one
    group with a non-empty semantics id; a dropped or double-counted grammar
    would break the member-count equality.
    """
    groups = _group_shipped_grammars_by_capability_semantics()
    shipped_count = sum(
        len(capability().get_grammars()) for capability in _SHIPPED_CAPABILITIES
    )
    assert (
        sum(
            len(members)
            for per_capability in groups.values()
            for members in per_capability.values()
        )
        == shipped_count
    )
    assert all(
        semantics for per_capability in groups.values() for semantics in per_capability
    )


@pytest.mark.unit
def test_every_grammar_semantics_claimed_by_rule_target() -> None:
    """Every shipped grammar's semantics is claimed by an in-capability rule.

    A grammar whose semantics no rule declares routes every recognition to
    zero rules — input matching only it yields INVALID instead of resolving,
    silently. Requiring in-capability rule-target coverage keeps
    ``_collect_candidates()`` free of unroutable shipped grammars; a grammar
    added without a claiming rule fails here at test time.
    """
    for capability in _SHIPPED_CAPABILITIES:
        instance = capability()
        targets = {s for rule in instance.get_rules() for s in rule.target_semantics}
        for grammar in instance.get_grammars():
            assert grammar.semantics in targets, (
                f"{capability.__name__} grammar {grammar.name!r} declares "
                f"semantics {grammar.semantics!r} claimed by no shipped rule "
                f"(rule targets: {sorted(targets)})"
            )


@pytest.mark.unit
def test_every_multi_member_semantics_group_has_probe_rows() -> None:
    """A coalesced group must be seeded or the guard fails loudly.

    The affinity-routing engine only treats grammars as interchangeable within
    one capability, so a multi-member group arises only from a coalescing
    inside a capability. Cross-capability id reuse (Currency and Money both
    declaring ``code_recognition`` etc.) is per-capability identity — those
    grammars never co-route — and must not demand probe rows. A future
    coalescing that adds a group without probe rows bypasses the same-notation
    field-mapping guarantee and fails here.
    """
    multi_member_ids: set[str] = set()
    for capability in _SHIPPED_CAPABILITIES:
        counts: dict[str, int] = {}
        for grammar in capability().get_grammars():
            counts[grammar.semantics] = counts.get(grammar.semantics, 0) + 1
        multi_member_ids.update(
            semantics for semantics, count in counts.items() if count > 1
        )
    assert multi_member_ids <= set(_PROBE_ROWS)


@pytest.mark.unit
def test_d7_no_coalesce_semantics_groups_stay_singleton() -> None:
    """The D7-locked groups must never grow a second member.

    ``us_calendar_date``/``european_calendar_date`` are renamed singletons and
    the other six are identity singletons; coalescing any of them would change
    what the shared semantics resolves to. Each id must stay a singleton
    within every capability: coalescing happens only inside one capability,
    so a second member anywhere in the same capability would silently change
    what the id resolves to, while reuse across capabilities (Country and
    SIUnit both declaring ``name_recognition``) never co-routes and is safe
    (R3). Each locked id must still exist in at least one capability.
    """
    groups = _group_shipped_grammars_by_capability_semantics()
    candidate_semantics_for_date: set[str] = set()
    for g in Date().get_grammars():
        for m in getattr(g, "matchers", None) or ():
            cs = getattr(m, "candidate_semantics", None)
            if cs:
                candidate_semantics_for_date.update(cs)  # type: ignore[arg-type]
    for semantics in _NO_COALESCE_SEMANTICS:
        counts = [
            len(per_capability.get(semantics, ())) for per_capability in groups.values()
        ]
        # Date's consolidated candidates also count as singleton members
        if semantics in candidate_semantics_for_date:
            total_candidates = sum(
                1
                for g in Date().get_grammars()
                for m in getattr(g, "matchers", None) or ()
                for s in getattr(m, "candidate_semantics", ()) or ()
                if s == semantics
            )
            assert total_candidates == 1, (
                f"{semantics!r} must appear exactly once in Date candidates, found {total_candidates}"  # noqa: E501
            )
            assert all(c <= 1 for c in counts), (
                f"{semantics!r} must stay a singleton per capability, found {counts}"
            )
            # Candidate semantics must be the sole occurrence (no grammar member)
            assert sum(counts) == 0, (
                f"{semantics!r} candidate semantics must not also appear as grammar semantics, found {counts}"  # noqa: E501
            )
            continue
        assert any(counts), f"{semantics!r} must stay a singleton, found none"
        assert all(count <= 1 for count in counts), (
            f"{semantics!r} must stay a singleton per capability, found {counts}"
        )
