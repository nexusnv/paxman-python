from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class CoordinatesContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "decimal"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"iso6709", "geo_uri", "geojson_pair", "dms", "dm"}
    )
    capability_name: str = field(default="coordinates", init=False)


def create_contract(  # re-exported on the capability in Task 8
    *,
    excluded_rules: Sequence[str] | None = None,
    pinned_rules: Sequence[str] | None = None,
    year: int | None = None,
    output_format: str | None = None,
    extra_grammars: Sequence[str] | None = None,
    suppress_common_words: bool = False,
) -> CoordinatesContract:
    return CoordinatesContract(
        excluded_rules=tuple(excluded_rules) if excluded_rules else (),
        pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
        year=year,
        output_format=output_format,
        extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        suppress_common_words=suppress_common_words,
    )
