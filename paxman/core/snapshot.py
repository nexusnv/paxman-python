"""Snapshot rail — typed frozen payload with source provenance."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Snapshot:
    name: str
    source_url: str
    version: str
    fetched_at: str
    data: object
