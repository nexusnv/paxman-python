"""Hypothesis property tests for the URL capability.

Each property locks a mathematical invariant of the WHATWG parser or the
recognition grammar using an independently derived expectation:

- parsing is total and canonical: ``parse_and_serialize`` never raises and
  canonical output is a fixed point (idempotence);
- every serialized value matches the canonical absolute-URI shape (lowercase
  scheme, no surrounding whitespace);
- recognition spans are honest: offsets are bounded by the input and
  ``raw_text`` matches the span exactly;
- the grammar never rejects a span the rule could accept (D7/D8: ``recognize``
  is a superset of the rule's domain; the rule decides validity).

Property tests stay off the registry and the frozen pipeline (tests/AGENTS.md
convention — Money is the documented exception): these drive
``parse_and_serialize`` and the grammar directly.
"""

from __future__ import annotations

import re
import string

import pytest
from hypothesis import given
from hypothesis import strategies as st

from paxman.capabilities.URL.grammar.absolute_uri_recognition import (
    AbsoluteUriRecognition,
)
from paxman.capabilities.URL.parsing import parse_and_serialize

# Canonical absolute-URI shape: lowercase scheme, ":", then the serialized
# remainder. ".*" (not ".+") admits bare-scheme URLs such as "a:" — a
# legitimate WHATWG serialization (empty path) that the grammar deliberately
# excludes (D16: at least one body character after the colon).
_CANONICAL_SHAPE = re.compile(r"^[a-z][a-z0-9+.\-]*:.*$")

# The grammar's body class (its Appendix C right boundary) excludes exactly:
# space, angle brackets, double quote, every C0 control except tab/LF/CR
# (which it admits for multi-line URIs), and DEL. A body opened by one of
# these, or whose leading ")" run the Appendix C paren strip reduces to the
# bare scheme, is deliberately not emitted as a span.
_GRAMMAR_BODY_EXCLUDED = frozenset(
    ' <>"'
    + "".join(chr(code) for code in range(0x20) if code not in (0x09, 0x0A, 0x0D))
    + "\x7f"
)

# WHATWG strips tab/LF/CR before parsing (parse_and_serialize): a scheme
# interrupted by one of these parses after stripping but is unanchorable
# for the grammar, which only admits them inside the body.
_WHITESPACE_STRIPPED = "\t\n\r"


@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_parsing_is_total_and_canonical(text: str) -> None:
    """parse_and_serialize never raises; canonical output is a fixed point."""
    serialized = parse_and_serialize(text)
    if serialized is not None:
        assert parse_and_serialize(serialized) == serialized


@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_serialized_output_matches_shape(text: str) -> None:
    """Every non-None output matches the canonical absolute-URI shape."""
    serialized = parse_and_serialize(text)
    if serialized is not None:
        assert _CANONICAL_SHAPE.fullmatch(serialized) is not None


@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_span_invariant(text: str) -> None:
    """Every RecognitionMatch span is honest: bounded by the input text."""
    for match in AbsoluteUriRecognition().recognize(text):
        assert 0 <= match.start <= match.end <= len(text)
        assert match.raw_text == text[match.start : match.end]


@pytest.mark.property
@given(text=st.text(alphabet=string.printable, max_size=120))
def test_recognize_subset_of_parseable(text: str) -> None:
    """The grammar never rejects a span the rule could accept (D7/D8).

    ``recognize`` is a superset of the rule's domain: every recognized span
    either parses (the rule validates it) or is a recognized-but-unvalidated
    span (the rule rejects it — INVALID). The converse is bounded by the
    grammar's extraction boundaries: when the parser accepts a body the
    grammar declines, that body must be non-extractable — bare (D16), opened
    by an Appendix C delimiter or a C0/DEL control, an all-paren body the
    paren strip reduces to the bare scheme, or a scheme interrupted by
    whitespace the parser strips (tab/LF/CR).
    """
    grammar = AbsoluteUriRecognition()
    matches = grammar.recognize(text)
    for match in matches:
        # Never raises; outcome is a value (accepted) or None (unvalidated).
        parse_and_serialize(match.raw_text)
    if parse_and_serialize(text) is not None and not matches:
        body = text.partition(":")[2]
        stripped_body = body.replace("\t", "").replace("\n", "").replace("\r", "")
        stripped_leading = stripped_body.lstrip(")")
        assert (
            not stripped_body
            or stripped_body[0] in _GRAMMAR_BODY_EXCLUDED
            or stripped_leading == ""
            or stripped_leading[0] in _GRAMMAR_BODY_EXCLUDED
            or any(char in _WHITESPACE_STRIPPED for char in text.partition(":")[0])
        )
