"""Tests for Email recognition grammars."""

from __future__ import annotations

import pytest

from paxman.capabilities.Email.grammar.localhost_recognition import (
    LocalhostEmailGrammar,
)
from paxman.capabilities.Email.grammar.obfuscated_recognition import (
    ObfuscatedEmailGrammar,
)
from paxman.capabilities.Email.grammar.standard_recognition import (
    StandardEmailGrammar,
)
from paxman.capabilities.Email.notation import EmailNotation


class TestStandardEmailGrammar:
    """Tests for StandardEmailGrammar."""

    @pytest.mark.capability
    def test_recognizes_standard_email(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("Contact us at user@example.com")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="user", domain_part="example.com"
        )

    @pytest.mark.capability
    def test_recognizes_email_with_dots(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("Send to first.last@domain.co.uk")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="first.last", domain_part="domain.co.uk"
        )

    @pytest.mark.capability
    def test_recognizes_email_with_plus(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("user+tag@gmail.com")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="user+tag", domain_part="gmail.com"
        )

    @pytest.mark.capability
    def test_recognizes_multiple_emails(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("Email a@b.com or c@d.org")
        assert len(results) == 2
        assert results[0].notation == EmailNotation(local_part="a", domain_part="b.com")
        assert results[1].notation == EmailNotation(local_part="c", domain_part="d.org")

    @pytest.mark.capability
    def test_ignores_invalid_email(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("not an email")
        assert len(results) == 0

    @pytest.mark.capability
    def test_ignores_obfuscated_email(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("user at example dot com")
        assert len(results) == 0

    @pytest.mark.capability
    def test_returns_empty_for_empty_input(self) -> None:
        grammar = StandardEmailGrammar()
        results = grammar.recognize("")
        assert len(results) == 0

    @pytest.mark.capability
    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("Contact us at user@example.com")
        assert len(results) == 1
        assert results[0].start == 14
        assert results[0].end == 30
        assert results[0].raw_text == "user@example.com"

    @property
    def grammar(self) -> StandardEmailGrammar:
        return StandardEmailGrammar()


class TestObfuscatedEmailGrammar:
    """Tests for ObfuscatedEmailGrammar."""

    @pytest.mark.capability
    def test_recognizes_at_dot_format(self) -> None:
        grammar = ObfuscatedEmailGrammar()
        results = grammar.recognize("Contact user at example dot com")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="user", domain_part="example.com"
        )

    @pytest.mark.capability
    def test_recognizes_at_symbol_format(self) -> None:
        grammar = ObfuscatedEmailGrammar()
        results = grammar.recognize("Email user at gmail.com")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="user", domain_part="gmail.com"
        )

    @pytest.mark.parametrize(
        "text",
        [
            "USER AT EXAMPLE DOT COM",
            "User At Example Dot Com",
            "USER AT GMAIL.COM",
            "user AT example DOT com",
        ],
    )
    @pytest.mark.capability
    def test_recognizes_case_insensitive_keywords(self, text: str) -> None:
        """Keywords "at"/"dot" match case-insensitively (re.IGNORECASE); the
        local part and domain keep their input casing for the rule to fold."""
        grammar = ObfuscatedEmailGrammar()
        results = grammar.recognize(text)
        assert len(results) == 1

    @pytest.mark.capability
    def test_ignores_standard_email(self) -> None:
        grammar = ObfuscatedEmailGrammar()
        results = grammar.recognize("user@example.com")
        assert len(results) == 0

    @pytest.mark.capability
    def test_returns_empty_for_no_email(self) -> None:
        grammar = ObfuscatedEmailGrammar()
        results = grammar.recognize("no email here")
        assert len(results) == 0

    @pytest.mark.capability
    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("Contact user at example dot com")
        assert len(results) == 1
        assert results[0].start == 8
        assert results[0].end == 31
        assert results[0].raw_text == "user at example dot com"

    @property
    def grammar(self) -> ObfuscatedEmailGrammar:
        return ObfuscatedEmailGrammar()


class TestLocalhostEmailGrammar:
    """Tests for LocalhostEmailGrammar."""

    @pytest.mark.capability
    def test_recognizes_localhost_email(self) -> None:
        grammar = LocalhostEmailGrammar()
        results = grammar.recognize("Send to admin@localhost")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="admin", domain_part="localhost"
        )

    @pytest.mark.capability
    def test_recognizes_localhost_with_port(self) -> None:
        grammar = LocalhostEmailGrammar()
        results = grammar.recognize("user@localhost:8080")
        assert len(results) == 1
        assert results[0].notation == EmailNotation(
            local_part="user", domain_part="localhost"
        )

    @pytest.mark.capability
    def test_ignores_standard_email(self) -> None:
        grammar = LocalhostEmailGrammar()
        results = grammar.recognize("user@example.com")
        assert len(results) == 0

    @pytest.mark.capability
    def test_returns_empty_for_no_email(self) -> None:
        grammar = LocalhostEmailGrammar()
        results = grammar.recognize("no email here")
        assert len(results) == 0

    @pytest.mark.capability
    def test_emits_spans(self) -> None:
        results = self.grammar.recognize("Send to admin@localhost")
        assert len(results) == 1
        assert results[0].start == 8
        assert results[0].end == 23
        assert results[0].raw_text == "admin@localhost"

    @property
    def grammar(self) -> LocalhostEmailGrammar:
        return LocalhostEmailGrammar()
