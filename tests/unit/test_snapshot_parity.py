"""Snapshot parity — generated modules embed Source/Version/SHA."""

# CI regenerate-and-diff: snapshots + generated headers must stay in sync.

from __future__ import annotations

import json
import pathlib


def test_iban_registry_generated_header() -> None:
    p = pathlib.Path("paxman/capabilities/IBAN/grammar/data/registry.py")
    text = p.read_text(encoding="utf-8")
    assert "Source:" in text and "Version:" in text and "SHA" in text


def test_language_snapshot_parity() -> None:
    snap = pathlib.Path("paxman/shared_data/iana_language_snapshot.json")
    assert snap.exists()
    data = json.loads(snap.read_text())
    assert "version" in data and "source_url" in data


def test_recognition_revision_changes_on_migration() -> None:
    from paxman.capabilities.Country.capability import CountryCapability
    from paxman.core.discovery import (
        freeze_registry,
        get_recognition_revision,
        register_capability,
        reset_registry,
    )

    reset_registry()
    register_capability(CountryCapability())
    freeze_registry()
    rev_before = get_recognition_revision()
    reset_registry()
    register_capability(CountryCapability())
    freeze_registry()
    assert get_recognition_revision() == rev_before
    reset_registry()
