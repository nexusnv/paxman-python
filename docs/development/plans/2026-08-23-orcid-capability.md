# ORCID Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a 14th Paxman capability, `orcid`, that canonicalizes tolerant human ORCID input (bare hyphenated, `https://orcid.org/` URI, `ORCID:`/`ISNI:` label) to the hyphenated form `XXXX-XXXX-XXXX-XXXC`, validated by MOD 11-2 against ISO 27729:2024 with full provenance.

**Architecture:** Single always-active `PipelineGrammar` (`orcid_recognition`) with an optional fused label+URI prefix group and a strict `(?ai:)` ASCII hyphenated payload; one fused rule file `rules/iso_27729_ed2024.py` carrying TWO `Rule` classes (both validating the full structure+checksum conjunction, ISBN-style dual provenance); contract offers `uri` and `compact` renderings through the `format_value()` seam. Recognition is syntax-only; rules own meaning; presentation never leaks into rules.

**Tech Stack:** Python 3.11+, uv, pytest (+ hypothesis for property tests), ruff, pyright strict, import-linter. No new dependencies.

**Basis:** `docs/development/research/2026-08-23-orcid-canonicalization.md` (audit-revised: inline `(?ai:)` flags, `[\s:-]+` label + glued-label guard, hyphen-only v1 grammar, edition pinned to ISO 27729:2024 active).

**Verified checksum vectors** (recomputed by hand — these become test constants):

| Base 15 | Check | Full |
|---|---|---|
| `000000021825009` | `7` | `0000-0002-1825-0097` |
| `000000021694233` | `X` | `0000-0002-1694-233X` |
| `000000015109370` | `0` | `0000-0001-5109-3700` |
| `142245863573047` | `6` | `1422-4586-3573-0476` (ISNI sample) |
| `000000012281955` | `X` | `0000-0001-2281-955X` (python-stdnum docstring vector) |

Algorithm: `total = 0; for ch in base15: total = (total + int(ch)) * 2; result = (12 - total % 11) % 11; "X" if result == 10 else str(result)`.

---

## File Structure

```
paxman/capabilities/ORCID/
├── __init__.py                  # Task 0 (scaffolder): exports
├── notation.py                  # Task 1: 5-field frozen-slots dataclass
├── contract.py                  # Task 4: DEFAULT "orcid", OFFERED {"uri","compact"}
├── capability.py                # Task 4: wiring + format_value seam
├── grammar/
│   ├── __init__.py              # Task 0 (scaffolder)
│   └── orcid_recognition.py     # Task 2: PipelineGrammar + RegexStage
└── rules/
    ├── __init__.py              # Task 0 (scaffolder)
    └── iso_27729_ed2024.py      # Task 3: PUBLICATION + Section4OrcidStructure + SectionAnnexAMod11Dash2

tests/capabilities/orcid/
├── __init__.py                  # Task 0 (scaffolder)
├── test_notation.py             # Tasks 0→1
├── test_grammar.py              # Tasks 0→2
├── test_rules.py                # Tasks 0→3
└── test_capability.py           # Tasks 0→4

tests/integration/test_orcid_capability.py   # Task 5 (new)
tests/property/test_orcid_property.py        # Task 6 (new)

Modify:
paxman/api/bootstrap.py                       # Task 5 (_SHIPPED)
tests/unit/test_api_coverage_fix.py:27        # Task 5 (== 13 → == 14)
README.md                                     # Task 7 (regen table)
CONTEXT.md                                    # Task 7 (capability entries)
```

**Engine semantics note (read before Task 3):** `_collect_candidates` in `paxman/engine/orchestrator.py` treats every rule as an independent authority — each rule whose `matches()` returns `True` produces its own candidate. Therefore **both ORCID rule classes must validate the full conjunction (structure AND MOD 11-2)**, exactly like ISBN's `Section53Isbn13CheckDigit` / `Section42Gs1Prefix` pair (each re-checks prefix + check digit). A naive split where the "structure" rule omits the checksum would make bad-checksum input resolve `SUCCESS`. Dual classes exist to give dual provenance on SUCCESS; if either aspect fails, both reject → `INVALID`.

---

### Task 0: Scaffold the skeleton

**Files:**
- Create: `paxman/capabilities/ORCID/**` (13 files via scaffolder)
- Create: `tests/capabilities/orcid/**` (5 files via scaffolder)
- Modify: `paxman/capabilities/__init__.py` (scaffolder edits import + `__all__`)

- [ ] **Step 0.1: Verify clean tree**

Run: `git status --short`
Expected: empty (or only pre-existing changes unrelated to this work — do not proceed on top of unrelated dirty state).

- [ ] **Step 0.2: Run the scaffolder**

```bash
uv run python tools/new_capability.py ORCID --name orcid \
    --authority "ISO" \
    --spec-name "ISO 27729:2024" \
    --spec-url "https://www.iso.org/standard/87177.html" \
    --publication-year 2024 \
    --spec-version "2024-11" \
    --default-format orcid
```

Expected output: list of created files ending with the human checklist ("Replace the placeholder grammar pattern…"). Note: the scaffolder emits `PUBLICATION` with `lifecycle="active"` — correct for our 2024 pin; no manual lifecycle edit needed.

- [ ] **Step 0.3: Confirm stub tests are green**

Run: `uv run pytest tests/capabilities/orcid/ -q`
Expected: all pass (the scaffolder guarantees a green skeleton).

Run: `uv run pytest tests/unit/test_capability_exports.py -q`
Expected: PASS (scaffolder wired `paxman/capabilities/__init__.py`; export-completeness test is dynamic).

- [ ] **Step 0.4: Rename the generated rule file**

The scaffolder names rule files `<authority_snake>_ed<year>.py` → `rules/iso_ed2024.py`. The report pins `iso_27729_ed2024.py`:

```bash
git mv paxman/capabilities/ORCID/rules/iso_ed2024.py paxman/capabilities/ORCID/rules/iso_27729_ed2024.py
```

Then fix the import inside `paxman/capabilities/ORCID/capability.py` (and anywhere else it appears):

Run: `grep -rn "iso_ed2024" paxman/ tests/`
Expected: hits only in `paxman/capabilities/ORCID/capability.py` (import of the placeholder rule). Replace `from paxman.capabilities.ORCID.rules.iso_ed2024 import ...` with `from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import ...` keeping whatever class name the placeholder used for now (it is replaced in Task 3).

- [ ] **Step 0.5: Commit**

```bash
git add paxman/capabilities/ORCID tests/capabilities/orcid paxman/capabilities/__init__.py
git commit -m "feat(orcid): scaffold ORCID capability skeleton"
```

---

### Task 1: Notation — five-field frozen dataclass

**Files:**
- Modify: `paxman/capabilities/ORCID/notation.py` (replace scaffold placeholder)
- Modify: `tests/capabilities/orcid/test_notation.py` (replace scaffold placeholder tests)

- [ ] **Step 1.1: Write the failing notation tests**

Replace the entire content of `tests/capabilities/orcid/test_notation.py`:

```python
"""Tests for ORCIDNotation — frozen, slots, all-str fields."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.ORCID.notation import ORCIDNotation

pytestmark = [pytest.mark.capability]


class TestORCIDNotation:
    def test_frozen(self) -> None:
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            notation.compact = "x"  # type: ignore[misc]

    def test_hashable_and_eq(self) -> None:
        a = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        b = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_slots(self) -> None:
        assert ORCIDNotation.__dataclass_params__.slots is True

    def test_all_fields_are_str(self) -> None:
        for field in dataclasses.fields(ORCIDNotation):
            assert field.type is str, field.name

    def test_field_values(self) -> None:
        notation = ORCIDNotation(
            compact="000000021694233X",
            hyphenated="0000-0002-1694-233X",
            uri="https://orcid.org/0000-0002-1694-233X",
            check="X",
            is_uri="true",
        )
        assert notation.check == "X"
        assert notation.is_uri == "true"
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/orcid/test_notation.py -q`
Expected: FAIL — placeholder notation has a single `value` field, not the five fields (`TypeError` on unexpected keyword arguments).

- [ ] **Step 1.3: Write the notation**

Replace the entire content of `paxman/capabilities/ORCID/notation.py`:

```python
"""ORCID notation: grammar-normalized hyphenated identifier."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ORCIDNotation:
    """ORCID normalized hyphenated form.

    ``compact`` is the 16-char separator-free uppercase string: 15 digits plus
    a check character ``0-9`` or ``X`` (value 10).
    ``hyphenated`` is the ``XXXX-XXXX-XXXX-XXXC`` presentation (three
    hyphen-minus separators, ``X`` uppercase).
    ``uri`` is ``https://orcid.org/`` + ``hyphenated`` (always https, even when
    the raw input carried ``http://``).
    ``check`` is the single check character at position 16.
    ``is_uri`` is ``"true"`` when the raw span carried an ``orcid.org`` prefix,
    else ``"false"`` (string-encoded so every field stays ``str``).

    The grammar never computes or validates the MOD 11-2 check digit; rules own
    that (grammar/rule boundary per HOW_TO_ADD_NEW_CAPABILITY.md Step 4).
    """

    compact: str
    hyphenated: str
    uri: str
    check: str
    is_uri: str
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/orcid/test_notation.py -q`
Expected: PASS (all). Note: `tests/capabilities/orcid/test_grammar.py`, `test_rules.py`, `test_capability.py` may now FAIL because the scaffold placeholder grammar/rules still reference the old `value` field — that is expected and fixed in Tasks 2–4. Do not fix them here.

- [ ] **Step 1.5: Commit**

```bash
git add paxman/capabilities/ORCID/notation.py tests/capabilities/orcid/test_notation.py
git commit -m "feat(orcid): five-field ORCIDNotation (compact/hyphenated/uri/check/is_uri)"
```

---

### Task 2: Grammar — `orcid_recognition` (TDD)

**Files:**
- Modify: `paxman/capabilities/ORCID/grammar/orcid_recognition.py` (replace scaffold placeholder)
- Modify: `tests/capabilities/orcid/test_grammar.py` (replace scaffold placeholder tests)

- [ ] **Step 2.1: Write the failing grammar tests**

Replace the entire content of `tests/capabilities/orcid/test_grammar.py`:

```python
"""Tests for ORCID recognition grammar."""

from __future__ import annotations

import pytest

from paxman.capabilities.ORCID.grammar.orcid_recognition import (
    ORCIDRecognitionGrammar,
)
from paxman.capabilities.ORCID.notation import ORCIDNotation

pytestmark = [pytest.mark.capability]


def _expected(hyphenated: str, *, is_uri: bool = False) -> ORCIDNotation:
    compact = hyphenated.replace("-", "")
    return ORCIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        uri=f"https://orcid.org/{hyphenated}",
        check=compact[-1],
        is_uri="true" if is_uri else "false",
    )


class TestORCIDRecognitionGrammar:
    """Hyphenated 4-4-4-4 payload, optional label/host prefix, word_only guards."""

    def test_bare_hyphenated(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0002-1825-0097")
        assert len(results) == 1
        assert results[0].notation == _expected("0000-0002-1825-0097")
        assert (results[0].start, results[0].end) == (0, 19)
        assert results[0].raw_text == "0000-0002-1825-0097"

    def test_uri_prefix_canonical(self) -> None:
        text = "https://orcid.org/0000-0002-1825-0097"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].notation.hyphenated == "0000-0002-1825-0097"
        assert results[0].notation.is_uri == "true"
        assert results[0].raw_text == text
        assert (results[0].start, results[0].end) == (0, len(text))

    def test_http_uri_variant(self) -> None:
        text = "http://orcid.org/0000-0002-1694-233X"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        # scheme normalized: uri field is always https
        assert results[0].notation.uri.startswith("https://")

    def test_domain_only_host(self) -> None:
        for text in (
            "orcid.org/0000-0002-1825-0097",
            "www.orcid.org/0000-0002-1825-0097",
        ):
            results = ORCIDRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].notation.hyphenated == "0000-0002-1825-0097"

    def test_uppercase_host_fold(self) -> None:
        text = "https://ORCID.org/0000-0002-1825-0097"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1

    def test_label_orcid_and_isni(self) -> None:
        for text in (
            "ORCID: 0000-0002-1825-0097",
            "orcid - 0000-0002-1825-0097",
            "ISNI: 0000-0002-1825-0097",
        ):
            results = ORCIDRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].raw_text == text
            assert results[0].notation.hyphenated == "0000-0002-1825-0097"

    def test_glued_label_does_not_fuse(self) -> None:
        # Label requires [\s:-]+ separator: glued label means no claim at all.
        assert ORCIDRecognitionGrammar().recognize("ORCID0000-0002-1825-0097") == []

    def test_lowercase_x_folds_to_upper(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0002-1694-233x")
        assert len(results) == 1
        assert results[0].notation.check == "X"
        assert results[0].notation.hyphenated.endswith("X")

    def test_leading_zeros_preserved(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0001-5109-3700")
        assert len(results) == 1
        assert results[0].notation.compact == "0000000151093700"

    def test_embedded_in_prose(self) -> None:
        text = "see https://orcid.org/0000-0002-1825-0097 for author"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].start == text.index("https://")
        assert results[0].end == len("https://orcid.org/0000-0002-1825-0097") + (
            results[0].start
        )

    def test_trailing_slash_not_claimed(self) -> None:
        text = "https://orcid.org/0000-0002-1825-0097/"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 1
        assert results[0].raw_text.endswith("0097")
        assert not results[0].raw_text.endswith("/")

    def test_quoted_and_bracketed(self) -> None:
        for text in ('"0000-0002-1825-0097"', "[0000-0002-1825-0097]"):
            results = ORCIDRecognitionGrammar().recognize(text)
            assert len(results) == 1, f"failed for {text!r}"
            assert results[0].raw_text == "0000-0002-1825-0097"

    def test_compact_digits_missing(self) -> None:
        # v1 grammar is hyphen-only: contiguous digits are MISSING.
        assert ORCIDRecognitionGrammar().recognize("0000000218250097") == []

    def test_spaced_isni_style_missing(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("0000 0002 1825 0097") == []

    def test_overlong_rejected(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("0000-0002-1825-00977") == []
        assert (
            ORCIDRecognitionGrammar().recognize(
                "https://orcid.org/0000-0002-1825-00977"
            )
            == []
        )

    def test_underlong_rejected(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("0000-0002-1825-009") == []

    def test_x_mid_run_missing(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("000X-0002-1825-0097") == []

    def test_fullwidth_digits_missing(self) -> None:
        # (?ai:) ASCII-only body rejects fullwidth digits.
        assert (
            ORCIDRecognitionGrammar().recognize(
                "\uff10\uff10\uff10\uff10-\uff10\uff10\uff10\uff12-"
                "\uff11\uff18\uff12\uff15-\uff10\uff10\uff19\uff17"
            )
            == []
        )

    def test_digit_glued_runs_rejected(self) -> None:
        assert ORCIDRecognitionGrammar().recognize("X0000-0002-1825-0097") == []
        assert ORCIDRecognitionGrammar().recognize("A0000-0002-1825-0097B") == []

    def test_trailing_hyphen_continuation_claims_payload_only(self) -> None:
        results = ORCIDRecognitionGrammar().recognize("0000-0002-1825-0097-1234")
        assert len(results) == 1
        assert results[0].raw_text == "0000-0002-1825-0097"

    def test_multiple_matches(self) -> None:
        text = "0000-0002-1825-0097 / 0000-0001-5109-3700"
        results = ORCIDRecognitionGrammar().recognize(text)
        assert len(results) == 2
        assert results[0].start < results[1].start
        for m in results:
            assert m.raw_text == text[m.start : m.end]

    def test_span_invariants(self) -> None:
        texts = [
            "0000-0002-1825-0097",
            "https://orcid.org/0000-0002-1825-0097",
            "ORCID: 0000-0002-1694-233X",
            "see orcid.org/0000-0001-5109-3700 (Jane)",
        ]
        for text in texts:
            for m in ORCIDRecognitionGrammar().recognize(text):
                assert 0 <= m.start <= m.end <= len(text)
                assert m.raw_text == text[m.start : m.end]
                assert len(m.raw_text) == m.end - m.start

    def test_empty(self) -> None:
        g = ORCIDRecognitionGrammar()
        assert g.recognize("") == []
        assert g.recognize("   ") == []

    def test_single_value_true(self) -> None:
        assert ORCIDRecognitionGrammar.single_value is True

    def test_name_and_semantics(self) -> None:
        g = ORCIDRecognitionGrammar()
        assert g.name == "orcid_recognition"
        assert g.semantics == "orcid_recognition"
        assert g.semantics != ""
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/orcid/test_grammar.py -q`
Expected: FAIL — the placeholder grammar does not recognize ORCID payloads (most recognition assertions return `[]` where matches expected), and `single_value` may be absent.

- [ ] **Step 2.3: Write the grammar**

Replace the entire content of `paxman/capabilities/ORCID/grammar/orcid_recognition.py`:

```python
"""ORCID recognition grammar — regex structural pattern matching."""

from __future__ import annotations

import re

from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# Label separator is [\s:-]+ one or more, never zero width: a glued
# "ORCID0000-..." must not fuse into a mention (BIC precedent).
# Host tolerance mirrors ORCID XSD orcid-uri plus ecosystem practice:
# https://orcid.org/ (canonical v2.1), http:// (v2.0 legacy),
# orcid.org/, www.orcid.org/.
# Payload is ASCII-only via inline (?ai:) — fullwidth digits never match;
# the i flag folds lowercase x into [X] before .upper() normalization.
_ORCID_LABEL = r"(?:(?ai:ORCID|ISNI)[\s:-]+)?"
_ORCID_HOST = r"(?:(?ai:(?:https?://)?(?:www\.)?orcid\.org)/)?"
_ORCID_GLUED_GUARD = r"(?!(?ai:(?:ORCID|ISNI)[0-9]))"
_ORCID_BODY = (
    rf"{_ORCID_LABEL}{_ORCID_HOST}{_ORCID_GLUED_GUARD}"
    r"(?P<hyphenated>(?ai:\d{4}-\d{4}-\d{4}-\d{3}[\dX]))"
)
# word_only guards block left glue X0000-... and right glue ...0097Y.
# The negative lookahead blocks glued label without separator.
_ORCID_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ORCID_BODY
    + BoundaryGuard.word_only().lookahead
)


def _orcid_notation(match: re.Match[str]) -> ORCIDNotation:
    hyphenated = match.group("hyphenated").upper()
    compact = hyphenated.replace("-", "")
    return ORCIDNotation(
        compact=compact,
        hyphenated=hyphenated,
        uri=f"https://orcid.org/{hyphenated}",
        check=compact[-1],
        is_uri="true" if "orcid.org" in match.group(0).lower() else "false",
    )


class ORCIDRecognitionGrammar(PipelineGrammar[ORCIDNotation]):
    """ORCID recognition — hyphenated 4-4-4-4 with optional label and URI host."""

    name = "orcid_recognition"
    semantics = "orcid_recognition"
    single_value = True
    pre = StandardPre[ORCIDNotation](empty_guard=True)
    regex = RegexStage[ORCIDNotation](pattern=_ORCID_PATTERN, notation_fn=_orcid_notation)
```

Note: no `flags=` argument — case-insensitivity and ASCII restriction live in the inline `(?ai:)` groups (BIC precedent). If `RegexStage` requires `flags` as a keyword, pass nothing; it defaults to no flags. If pyright complains about a missing argument, check `paxman/core/grammar/stages.py` for the parameter default and rely on it.

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/orcid/test_grammar.py -q`
Expected: PASS (all). If `test_glued_label_does_not_fuse` fails because the payload still claims after a glued label, verify the lookbehind sees the word char `D` in `ORCID` — the `word_only().lookbehind` must be applied to the whole composed pattern (label included), which it is, since guards wrap `_ORCID_BODY`.

- [ ] **Step 2.5: Lint the new file**

Run: `uv run ruff check paxman/capabilities/ORCID/grammar/orcid_recognition.py && uv run ruff format --check paxman/capabilities/ORCID/grammar/orcid_recognition.py`
Expected: exit 0 both.

- [ ] **Step 2.6: Commit**

```bash
git add paxman/capabilities/ORCID/grammar/orcid_recognition.py tests/capabilities/orcid/test_grammar.py
git commit -m "feat(orcid): orcid_recognition grammar with label/URI tolerance and ASCII guards"
```

---

### Task 3: Rules — fused `iso_27729_ed2024.py` with two full-conjunction classes (TDD)

**Files:**
- Modify: `paxman/capabilities/ORCID/rules/iso_27729_ed2024.py` (replace scaffold placeholder)
- Modify: `tests/capabilities/orcid/test_rules.py` (replace scaffold placeholder tests)

- [ ] **Step 3.1: Write the failing rule tests**

Replace the entire content of `tests/capabilities/orcid/test_rules.py`:

```python
"""Tests for ORCID rules (ISO 27729:2024 + Annex A MOD 11-2)."""

from __future__ import annotations

import pathlib

import pytest

from paxman.capabilities.ORCID.contract import ORCIDContract
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import (
    PUBLICATION,
    Section4OrcidStructure,
    SectionAnnexAMod11Dash2,
)
from paxman.core.domain import RuleStrategy

pytestmark = [pytest.mark.capability]

VALID = [
    "0000-0002-1825-0097",
    "0000-0002-1694-233X",
    "0000-0001-5109-3700",
    "0000-0001-2281-955X",  # python-stdnum ISNI docstring vector
]


def _notation(hyphenated: str) -> ORCIDNotation:
    compact = hyphenated.replace("-", "").upper()
    return ORCIDNotation(
        compact=compact,
        hyphenated=compact[:4]
        + "-"
        + compact[4:8]
        + "-"
        + compact[8:12]
        + "-"
        + compact[12:],
        uri=f"https://orcid.org/{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:]}",
        check=compact[-1],
        is_uri="false",
    )


@pytest.mark.parametrize("rule_cls", [Section4OrcidStructure, SectionAnnexAMod11Dash2])
class TestBothRulesConjunction:
    """Both classes validate the FULL structure+checksum conjunction."""

    def test_valid_match(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        for h in VALID:
            assert rule.matches(_notation(h), contract) is True, h

    def test_bad_checksum_rejects(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        # Correct shape, wrong check digit (expected 7, given 8).
        assert rule.matches(_notation("0000-0002-1825-0098"), contract) is False

    def test_wrong_length_rejects(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        short = ORCIDNotation(
            compact="0000000218250090"[:15],
            hyphenated="0000-0002-1825-009",
            uri="",
            check="9",
            is_uri="false",
        )
        assert rule.matches(short, contract) is False

    def test_non_digit_base_rejects(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        bad = ORCIDNotation(
            compact="000X000218250097",
            hyphenated="000X-0002-1825-0097",
            uri="",
            check="7",
            is_uri="false",
        )
        assert rule.matches(bad, contract) is False

    def test_normalize_hyphenated_upper(self, rule_cls: type) -> None:
        rule = rule_cls()
        contract = ORCIDContract()
        n = _notation("0000-0002-1694-233x")
        assert rule.normalize(n, contract) == "0000-0002-1694-233X"

    def test_normalize_agreement(self, rule_cls: type) -> None:
        """Both rules normalize identically (candidate dedup stays SUCCESS)."""
        rule_a = Section4OrcidStructure()
        rule_b = SectionAnnexAMod11Dash2()
        contract = ORCIDContract()
        n = _notation("0000-0002-1825-0097")
        assert rule_a.normalize(n, contract) == rule_b.normalize(n, contract)


class TestProvenanceAndConventions:
    def setup_method(self) -> None:
        self.rule = Section4OrcidStructure()

    def test_publication(self) -> None:
        assert PUBLICATION.authority == "ISO"
        assert PUBLICATION.specification_name == "ISO 27729:2024"
        assert PUBLICATION.kind == "specification"
        assert PUBLICATION.reference_url == "https://www.iso.org/standard/87177.html"
        assert PUBLICATION.version == "2024-11"
        assert PUBLICATION.lifecycle == "active"
        assert PUBLICATION.publication_year == 2024

    def test_names_strategies_semantics(self) -> None:
        a = Section4OrcidStructure()
        b = SectionAnnexAMod11Dash2()
        assert a.name == "Section 4-orcid-structure"
        assert b.name == "Section A-mod11-2-check-character"
        for rule in (a, b):
            assert rule.strategy == RuleStrategy.PARSER
            assert rule.provenance == PUBLICATION
            assert rule.target_semantics == frozenset({"orcid_recognition"})
            assert rule.requires_features == frozenset()
            assert isinstance(rule.citation, str) and rule.citation != ""

    def test_distinct_citations(self) -> None:
        assert (
            Section4OrcidStructure().citation != SectionAnnexAMod11Dash2().citation
        )

    @pytest.mark.parametrize(
        "rule_cls", [Section4OrcidStructure, SectionAnnexAMod11Dash2]
    )
    def test_no_output_format_token(self, rule_cls: type) -> None:
        path = (
            pathlib.Path(__file__).resolve().parents[3]
            / "paxman"
            / "capabilities"
            / "ORCID"
            / "rules"
            / "iso_27729_ed2024.py"
        )
        text = path.read_text(encoding="utf-8")
        assert "output_format" not in text
```

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/orcid/test_rules.py -q`
Expected: FAIL with `ImportError` — `Section4OrcidStructure` / `SectionAnnexAMod11Dash2` do not exist yet (placeholder class from scaffold has a different name).

- [ ] **Step 3.3: Write the rules**

Replace the entire content of `paxman/capabilities/ORCID/rules/iso_27729_ed2024.py`:

```python
"""ISO 27729:2024 rules: ORCID/ISNI structure plus MOD 11-2 check character.

Both rule classes validate the full conjunction (structure AND check digit):
each Paxman rule is an independent authority producing its own candidate, so
a partial validator would let checksum-invalid input resolve SUCCESS. The two
classes mirror ISBN's iso_2108 pair and exist for dual provenance on SUCCESS.
"""

from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.contract import Contract
from paxman.core.domain import Provenance, Rule, RuleStrategy

PUBLICATION = Provenance(
    authority="ISO",
    specification_name="ISO 27729:2024",
    kind="specification",
    reference_url="https://www.iso.org/standard/87177.html",
    version="2024-11",
    lifecycle="active",
    publication_year=2024,
)


def _mod_11_2_check(base15: str) -> str:
    """Compute the MOD 11-2 check char for 15 ASCII digits (X = 10)."""
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)


def _is_valid_orcid(notation: ORCIDNotation) -> bool:
    """Full conjunction: 16 chars, ASCII-digit base, matching check char."""
    if len(notation.compact) != 16:
        return False
    base, check = notation.compact[:15], notation.compact[15]
    if not base.isascii() or not base.isdigit():
        return False
    return check == _mod_11_2_check(base)


def _normalize(notation: ORCIDNotation) -> str:
    compact = notation.compact.upper()
    return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:]}"


class Section4OrcidStructure(Rule[ORCIDNotation]):
    """ISO 27729:2024 Section 4 - ISNI/ORCID structure (with Annex A check)."""

    name = "Section 4-orcid-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 4 (16 chars: 15 digits + MOD 11-2 check character)"
    target_semantics = frozenset({"orcid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ORCIDNotation, contract: Contract) -> bool:
        return _is_valid_orcid(notation)

    def normalize(self, notation: ORCIDNotation, contract: Contract) -> str:
        return _normalize(notation)


class SectionAnnexAMod11Dash2(Rule[ORCIDNotation]):
    """ISO 27729:2024 Annex A - MOD 11-2 check character (with S4 structure)."""

    name = "Section A-mod11-2-check-character"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Annex A (MOD 11-2 over the first 15 decimal digits)"
    target_semantics = frozenset({"orcid_recognition"})
    requires_features = frozenset()

    def matches(self, notation: ORCIDNotation, contract: Contract) -> bool:
        return _is_valid_orcid(notation)

    def normalize(self, notation: ORCIDNotation, contract: Contract) -> str:
        return _normalize(notation)
```

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/orcid/test_rules.py -q`
Expected: PASS (all).

Also confirm the global rule-purity scan still passes (no `output_format` token anywhere in any capability's rules):

Run: `uv run pytest tests/unit/test_rule_output_format_purity.py -q`
Expected: PASS.

- [ ] **Step 3.5: Commit**

```bash
git add paxman/capabilities/ORCID/rules/iso_27729_ed2024.py tests/capabilities/orcid/test_rules.py
git commit -m "feat(orcid): ISO 27729:2024 rules with dual full-conjunction provenance"
```

---

### Task 4: Contract + Capability wiring (TDD)

**Files:**
- Modify: `paxman/capabilities/ORCID/contract.py` (replace scaffold placeholder)
- Modify: `paxman/capabilities/ORCID/capability.py` (replace scaffold placeholder)
- Modify: `tests/capabilities/orcid/test_capability.py` (replace scaffold placeholder tests)

- [ ] **Step 4.1: Write the failing capability tests**

Replace the entire content of `tests/capabilities/orcid/test_capability.py`:

```python
"""ORCID capability wiring — ORCIDCapability + format_value seam."""

import pytest

from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.core.errors import ContractError


@pytest.mark.capability
class TestORCIDCapability:
    def test_capability_name_version(self) -> None:
        assert ORCIDCapability.name == "orcid"
        assert ORCIDCapability.version == "1.0.0"

    def test_get_grammars(self) -> None:
        grammars = ORCIDCapability().get_grammars()
        assert len(grammars) == 1
        assert {g.name for g in grammars} == {"orcid_recognition"}

    def test_get_rules(self) -> None:
        rules = ORCIDCapability().get_rules()
        assert len(rules) == 2
        assert {r.name for r in rules} == {
            "Section 4-orcid-structure",
            "Section A-mod11-2-check-character",
        }

    def test_create_contract_defaults(self) -> None:
        c = ORCIDCapability.create_contract()
        assert c.output_format == "orcid"
        assert c.capability_name == "orcid"
        assert c.excluded_rules == ()
        assert c.pinned_rules is None
        assert c.year is None
        assert c.extra_grammars == ()
        assert c.active_grammars is None  # no gating: engine runs all shipped

    def test_create_contract_output_formats(self) -> None:
        assert ORCIDCapability.create_contract(output_format="uri").output_format == "uri"
        assert (
            ORCIDCapability.create_contract(output_format="compact").output_format
            == "compact"
        )
        with pytest.raises(ContractError):
            ORCIDCapability.create_contract(output_format="isni")

    def test_format_value_default_identity(self) -> None:
        cap = ORCIDCapability()
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert cap.format_value("0000-0002-1825-0097", None, notation) == (
            "0000-0002-1825-0097"
        )
        assert cap.format_value("0000-0002-1825-0097", "default", notation) == (
            "0000-0002-1825-0097"
        )
        assert cap.format_value("0000-0002-1825-0097", "orcid", notation) == (
            "0000-0002-1825-0097"
        )

    def test_format_value_uri_always_https(self) -> None:
        cap = ORCIDCapability()
        notation = ORCIDNotation(
            compact="000000021694233X",
            hyphenated="0000-0002-1694-233X",
            uri="https://orcid.org/0000-0002-1694-233X",
            check="X",
            is_uri="true",
        )
        assert cap.format_value("0000-0002-1694-233X", "uri", notation) == (
            "https://orcid.org/0000-0002-1694-233X"
        )

    def test_format_value_compact(self) -> None:
        cap = ORCIDCapability()
        notation = ORCIDNotation(
            compact="0000000218250097",
            hyphenated="0000-0002-1825-0097",
            uri="https://orcid.org/0000-0002-1825-0097",
            check="7",
            is_uri="false",
        )
        assert cap.format_value("0000-0002-1825-0097", "compact", notation) == (
            "0000000218250097"
        )
```

- [ ] **Step 4.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/orcid/test_capability.py -q`
Expected: FAIL — placeholder contract has wrong default/offered formats; placeholder capability returns scaffold rule names and lacks `version`/`format_value` behavior.

- [ ] **Step 4.3: Write the contract**

Replace the entire content of `paxman/capabilities/ORCID/contract.py`:

```python
"""ORCID contract configuration."""

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class ORCIDContract(CapabilityContract):
    """Contract for the ORCID capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "orcid"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"uri", "compact"})

    capability_name: str = field(default="orcid", init=False)
```

- [ ] **Step 4.4: Write the capability**

Replace the entire content of `paxman/capabilities/ORCID/capability.py`:

```python
"""ORCID capability — wires grammars and rules together."""

from __future__ import annotations

from collections.abc import Sequence

from paxman.capabilities.ORCID.contract import ORCIDContract
from paxman.capabilities.ORCID.grammar.orcid_recognition import (
    ORCIDRecognitionGrammar,
)
from paxman.capabilities.ORCID.notation import ORCIDNotation
from paxman.capabilities.ORCID.rules.iso_27729_ed2024 import (
    Section4OrcidStructure,
    SectionAnnexAMod11Dash2,
)
from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule

__all__ = ["ORCIDCapability", "ORCIDContract", "ORCIDNotation"]


class ORCIDCapability(Capability[ORCIDNotation]):
    """ORCID canonicalization capability.

    Canonicalizes ORCID input to the hyphenated form XXXX-XXXX-XXXX-XXXC per
    ISO 27729:2024 (ISNI-compatible, MOD 11-2 check) with full provenance.
    """

    name = "orcid"
    version = "1.0.0"

    def get_grammars(self) -> list[Grammar[ORCIDNotation]]:
        return [ORCIDRecognitionGrammar()]

    def get_rules(self) -> list[Rule[ORCIDNotation]]:
        return [Section4OrcidStructure(), SectionAnnexAMod11Dash2()]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> ORCIDContract:
        """Factory for contracts with proper defaults."""
        return ORCIDContract(
            excluded_rules=tuple(excluded_rules) if excluded_rules else (),
            pinned_rules=tuple(pinned_rules) if pinned_rules is not None else None,
            year=year,
            output_format=output_format,
            extra_grammars=tuple(extra_grammars) if extra_grammars else (),
        )

    def format_value(
        self,
        value: str,
        output_format: str | None,
        notation: ORCIDNotation,
    ) -> str:
        """Render the hyphenated canonical value in the requested format.

        The default ``"orcid"`` path is identity. ``"uri"`` prepends the
        canonical https host; ``"compact"`` strips the hyphens. Never affects
        candidate identity or provenance.
        """
        if output_format == "uri":
            return f"https://orcid.org/{notation.hyphenated}"
        if output_format == "compact":
            return notation.compact
        return value
```

Also update `paxman/capabilities/ORCID/__init__.py` to export all three public names (mirror ISSN):

```python
from paxman.capabilities.ORCID.capability import (
    ORCIDCapability,
    ORCIDContract,
)
from paxman.capabilities.ORCID.notation import ORCIDNotation

__all__ = ["ORCIDCapability", "ORCIDContract", "ORCIDNotation"]
```

- [ ] **Step 4.5: Run the whole capability suite**

Run: `uv run pytest tests/capabilities/orcid/ -q`
Expected: PASS (all four test modules).

- [ ] **Step 4.6: Type-check the package**

Run: `uv run pyright paxman/capabilities/ORCID/`
Expected: 0 errors.

- [ ] **Step 4.7: Commit**

```bash
git add paxman/capabilities/ORCID tests/capabilities/orcid
git commit -m "feat(orcid): contract (orcid/uri/compact) and capability wiring"
```

---

### Task 5: Bootstrap registration + shipped-count + integration resolution map (TDD)

**Files:**
- Modify: `paxman/api/bootstrap.py` (`_SHIPPED`)
- Modify: `tests/unit/test_api_coverage_fix.py:27` (`== 13` → `== 14`)
- Create: `tests/integration/test_orcid_capability.py`

- [ ] **Step 5.1: Update the shipped-count assertion first (red)**

In `tests/unit/test_api_coverage_fix.py`, change line 27:

```python
        assert len(shipped) == 13
```

to:

```python
        assert len(shipped) == 14
```

Run: `uv run pytest tests/unit/test_api_coverage_fix.py::test_list_shipped_and_registered -q`
Expected: FAIL — shipped count is still 13 because bootstrap does not include ORCID yet.

- [ ] **Step 5.2: Register ORCID in the sanctioned bootstrap**

In `paxman/api/bootstrap.py`, add `ORCID` to the lazy-import block. Ruff isort orders the ALL-CAPS aliases as their own sorted group (`BIC, IBAN, IP, ISBN, ISSN, ORCID, URL`) before the CamelCase group — so `ORCID` slots between `ISSN` and `URL`, **not** near `Money`:

```python
from paxman.capabilities import (
    BIC,
    IBAN,
    IP,
    ISBN,
    ISSN,
    ORCID,
    URL,
    Country,
    Currency,
    Date,
    Email,
    Money,
    Phone,
    SIUnit,
)
```

and insert `ORCID` into `_SHIPPED` between `Money` and `Phone` (alphabetical by registry name — deterministic order):

```python
_SHIPPED: tuple[type[Capability[Any]], ...] = (
    BIC,
    Country,
    Currency,
    Date,
    Email,
    IBAN,
    IP,
    ISBN,
    ISSN,
    Money,
    ORCID,
    Phone,
    SIUnit,
    URL,
)
```

- [ ] **Step 5.3: Run count test to verify green**

Run: `uv run pytest tests/unit/test_api_coverage_fix.py -q`
Expected: PASS.

- [ ] **Step 5.4: Write the integration resolution-map tests**

Create `tests/integration/test_orcid_capability.py`:

```python
"""Integration tests for ORCID capability — resolution map + pipeline."""

from __future__ import annotations

import pytest

import paxman
from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset registry before each test."""
    reset_registry()
    yield
    reset_registry()


def _contract(**kwargs: object):
    return ORCIDCapability.create_contract(**kwargs)


class TestORCIDResolutionMap:
    @pytest.mark.integration
    def test_bare_hyphenated_success(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-0097", _contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"
        assert len(result.candidates) == 2  # dual provenance, same value
        assert {c.validation_rule for c in result.candidates} == {
            "Section 4-orcid-structure",
            "Section A-mod11-2-check-character",
        }
        for candidate in result.candidates:
            assert candidate.recognition_rule == "orcid_recognition"
            assert candidate.provenance[0].specification_name == "ISO 27729:2024"
            assert candidate.span == (0, 19)
        assert result.span == (0, 19)

    @pytest.mark.integration
    def test_uri_input_same_canonical(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "https://orcid.org/0000-0002-1825-0097", _contract()
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"
        assert result.span == (0, len("https://orcid.org/0000-0002-1825-0097"))

    @pytest.mark.integration
    def test_label_input_span_includes_label(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("ORCID: 0000-0002-1825-0097", _contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"
        assert result.span == (0, len("ORCID: 0000-0002-1825-0097"))

    @pytest.mark.integration
    def test_lowercase_x_success_upper(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1694-233x", _contract())

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1694-233X"

    @pytest.mark.integration
    def test_invalid_checksum_invalid(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-0098", _contract())

        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_underlong_missing(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-009", _contract())

        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_compact_digits_missing_v1(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000000218250097", _contract())

        assert result.status == Resolution.MISSING

    @pytest.mark.integration
    def test_two_distinct_mentions_raise(self) -> None:
        register_capability(ORCIDCapability())
        with pytest.raises(MultipleMentionsError):
            paxman.canonicalize(
                "0000-0002-1825-0097 and 0000-0001-5109-3700", _contract()
            )

    @pytest.mark.integration
    def test_identical_mentions_coalesce_success(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "0000-0002-1825-0097 and 0000-0002-1825-0097", _contract()
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "0000-0002-1825-0097"

    @pytest.mark.integration
    def test_temporal_filter_drops_rules(self) -> None:
        """year < 2024 drops both rules -> recognized but INVALID."""
        register_capability(ORCIDCapability())
        result = paxman.canonicalize("0000-0002-1825-0097", _contract(year=2023))

        assert result.status == Resolution.INVALID

    @pytest.mark.integration
    def test_output_format_uri_rendering(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "0000-0002-1825-0097", _contract(output_format="uri")
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "https://orcid.org/0000-0002-1825-0097"

    @pytest.mark.integration
    def test_output_format_compact_rendering(self) -> None:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(
            "https://orcid.org/0000-0002-1694-233X", _contract(output_format="compact")
        )

        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == "000000021694233X"

    @pytest.mark.integration
    def test_register_all_shipped_includes_orcid(self) -> None:
        names = paxman.register_all_shipped()
        assert "orcid" in names
        assert names.index("money") < names.index("orcid") < names.index("phone")
```

- [ ] **Step 5.5: Run integration tests to verify they pass**

Run: `uv run pytest tests/integration/test_orcid_capability.py -v`
Expected: PASS (all 13). If `test_bare_hyphenated_success` shows only 1 candidate, check that both rule classes share `PUBLICATION` and both `matches()` return True for valid input (Task 3).

- [ ] **Step 5.6: Run the full unit suite for collateral damage**

Run: `uv run pytest tests/unit -q`
Expected: PASS. Watch especially `test_bootstrap*`, `test_capability_exports.py`, README/doc-sync tests.

- [ ] **Step 5.7: Commit**

```bash
git add paxman/api/bootstrap.py tests/unit/test_api_coverage_fix.py tests/integration/test_orcid_capability.py
git commit -m "feat(orcid): bootstrap registration + integration resolution map"
```

---

### Task 6: Property tests (hypothesis, TDD-light)

**Files:**
- Create: `tests/property/test_orcid_property.py`

- [ ] **Step 6.1: Check how property tests are marked**

Run: `ls tests/property/ && sed -n '1,30p' tests/property/$(ls tests/property/ | grep '^test_' | head -1)`
Expected: existing property module(s) using `pytestmark = [pytest.mark.property]` and `hypothesis.given`. Mirror their fixture/registration style.

- [ ] **Step 6.2: Write the property tests**

Create `tests/property/test_orcid_property.py`:

```python
"""Property-based tests for ORCID canonicalization (hypothesis)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

import paxman
from paxman.capabilities.ORCID.capability import ORCIDCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

pytestmark = [pytest.mark.property]

_digits = st.text(alphabet="0123456789", min_size=15, max_size=15)


def _check(base15: str) -> str:
    total = 0
    for ch in base15:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return "X" if result == 10 else str(result)


def _hyphenate(compact: str) -> str:
    return f"{compact[:4]}-{compact[4:8]}-{compact[8:12]}-{compact[12:]}"


@given(base=_digits)
def test_generated_valid_orcids_round_trip(base: str) -> None:
    compact = base + _check(base)
    hyphenated = _hyphenate(compact)
    reset_registry()
    try:
        register_capability(ORCIDCapability())
        result = paxman.canonicalize(hyphenated, ORCIDCapability.create_contract())
        assert result.status == Resolution.SUCCESS
        assert result.canonicalized_value == hyphenated
    finally:
        reset_registry()


@given(base=_digits)
def test_uri_form_equals_bare_form(base: str) -> None:
    compact = base + _check(base)
    hyphenated = _hyphenate(compact)
    reset_registry()
    try:
        register_capability(ORCIDCapability())
        bare = paxman.canonicalize(hyphenated, ORCIDCapability.create_contract())
        uri = paxman.canonicalize(
            f"https://orcid.org/{hyphenated}", ORCIDCapability.create_contract()
        )
        assert bare.status == uri.status == Resolution.SUCCESS
        assert bare.canonicalized_value == uri.canonicalized_value == hyphenated
        assert bare.span is not None and uri.span is not None
        assert uri.span[1] - uri.span[0] > bare.span[1] - bare.span[0]
    finally:
        reset_registry()
```

If `tests/property/` does not exist, create `tests/property/__init__.py` alongside (empty file), and confirm the `property` marker is registered in `pyproject.toml` (`grep -n "property" pyproject.toml` under `[tool.pytest.ini_options] markers`) — it is listed in AGENTS.md commands, so it should already exist.

- [ ] **Step 6.3: Run property tests**

Run: `uv run pytest tests/property/test_orcid_property.py -q`
Expected: PASS.

- [ ] **Step 6.4: Commit**

```bash
git add tests/property/test_orcid_property.py
git commit -m "test(orcid): property round-trip and URI/bare equivalence"
```

---

### Task 7: Docs sync (README table + CONTEXT.md)

**Files:**
- Modify: `README.md` (regenerated table + counts)
- Modify: `CONTEXT.md` (capability entries)

- [ ] **Step 7.1: Regenerate the README capabilities table**

Run: `uv run python tools/generate_readme_table.py`
Expected: README table gains an `| **ORCID** | … | 1 (orcid) | 2 | … |` row (alphabetical between Money and Phone).

- [ ] **Step 7.2: Fix remaining capability-count prose in README**

Run: `grep -n "thirteen\|twelve\|built-in capabilities" README.md`
Expected: hits such as "ships with thirteen built-in capabilities". Update prose to **fourteen** wherever the count refers to the shipped set (note: the Community Extensions section historically says "twelve" — update that too; it was stale before this change and is touched only to correct the count).

Add an ORCID example section after the Money section, mirroring the ISSN style. The section content is exactly this (four-backtick outer fence shown here only to delimit it in the plan — write the inner content into README as a normal `### ORCID Capability` section with a single ```python block):

````markdown
### ORCID Capability

Recognizes ORCID iDs (ISNI-compatible identifiers, ISO 27729:2024) with MOD 11-2 check-digit validation, canonicalizing to the hyphenated form.

```python
from paxman.capabilities import ORCID

register_capability(ORCID())

# Bare hyphenated iD
contract = ORCID.create_contract()
result = paxman.canonicalize("0000-0002-1825-0097", contract)
# → "0000-0002-1825-0097"

# URI input resolves to the same canonical value
result = paxman.canonicalize("https://orcid.org/0000-0002-1694-233X", contract)
# → "0000-0002-1694-233X"

# Render as the storage URI
contract = ORCID.create_contract(output_format="uri")
result = paxman.canonicalize("0000-0002-1825-0097", contract)
# → "https://orcid.org/0000-0002-1825-0097"

# Bad check digit is INVALID
result = paxman.canonicalize("0000-0002-1825-0098", ORCID.create_contract())
# → Status: INVALID
```
````

- [ ] **Step 7.3: Update CONTEXT.md**

Under `## The Capabilities` add the ORCID row to the capability table (match the existing row shape exactly — read a neighboring row first), and add an `### ORCID` subsection under Capability Details describing:

- Notation: `ORCIDNotation` — `compact`, `hyphenated`, `uri`, `check`, `is_uri` (all `str`).
- Grammar: `orcid_recognition` — optional `ORCID`/`ISNI` label (`[\s:-]+`) and `https?://(www.)?orcid.org/` host, hyphen-only `4-4-4-4` payload with final `[0-9X]`, `word_only` guards, inline `(?ai:)`.
- Rules: `Section 4-orcid-structure` + `Section A-mod11-2-check-character` (both ISO 27729:2024, full conjunction).
- Formats: default `orcid`; offered `uri`, `compact`.

- [ ] **Step 7.4: Verify docs-sync tests**

Run: `uv run pytest tests/unit -k "readme or context or doc" -q`
Expected: PASS (if such tests exist; otherwise skip — no-op).

- [ ] **Step 7.5: Commit**

```bash
git add README.md CONTEXT.md
git commit -m "docs(orcid): README table + capability section, CONTEXT.md entries"
```

---

### Task 8: Full quality gate

**Files:** none (verification only)

- [ ] **Step 8.1: Run the merge-blocking gate**

```bash
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest
```

Expected: every command exits 0. Coverage gate (95% global) must pass with the new package fully covered by Tasks 1–6 tests.

- [ ] **Step 8.2: Explicit coverage check for the new package**

Run: `uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q` then inspect `paxman/capabilities/ORCID/*` lines in the report.
Expected: ≥ 95% for every ORCID module (target: 100%; the only acceptable gaps are defensive branches, none expected).

- [ ] **Step 8.3: CLI smoke test**

Run: `uv run python -m paxman orcid "see https://orcid.org/0000-0002-1825-0097 (Jane)"`
Expected: JSON/text output showing `SUCCESS`, canonical value `0000-0002-1825-0097`, provenance `ISO 27729:2024`.

Run: `uv run python -m paxman --list`
Expected: `orcid` appears in the shipped capability list.

- [ ] **Step 8.4: Final commit (if anything was touched by format/lint fixes)**

```bash
git status --short
# only if non-empty after fixing any gate complaints:
git add -A && git commit -m "chore(orcid): quality-gate fixes"
```

---

## Out of scope (explicitly deferred per research report §5.4 / §13)

- Registry-liveness `LOOKUP_TABLE` rule behind `include_registry_validation` (needs CC0 snapshot + refresh procedure).
- Compact/spaced-input tolerance (second grammar or `Pre` normalizer) — v1 is hyphen-only; compact input is `MISSING`.
- Reserved-block validation (`0000-0001…` / `0009…`) — assignment history, not structural validity.
- Free-text batch grammar with `single_value=False` via community extension.
