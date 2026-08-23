# Language Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a 15th Paxman capability, `language`, that canonicalizes tolerant human language input (bare `en`/`eng`/`ger`, display names `German`/`Deutsch`, BCP 47 tags `en-US`/`fr_FR`/`zh-Hans-CN`/`sl-nedis`, grandfathered `i-cherokee`→`chr`) to BCP 47 canonical tag (`language[-script][-region][-variant]`, case per RFC 5646 §2.1.1: language lower, script Title, region Upper) validated by ISO 639-1:2002 + ISO 639-2:1998 + ISO 639-3:2007 + ISO 639-5:2008 + BCP 47 RFC 5646 + IANA Language Subtag Registry (File-Date 2026-08-08) with full provenance, no checksum, deterministic.

**Architecture:** Three always-active `PipelineGrammar`s (`bcp47_tag_recognition` Regex ABNF-approximate longest-first, `language_code_recognition` Regex 2-3/5-8 bare code, `language_name_recognition` Lexicon `WholeInputLookup` with `normalize_name` union keyset) emitting `LanguageNotation(language, extlang, script, region, variant, extension, privateuse, grandfathered, compact, raw_value)` where `compact` is BCP 47 case-canonicalized or bare lower; six publications as six rule files — `iso_639_1_ed2002.py` (LOOKUP, alpha-2 184), `iso_639_2_ed1998.py` (LOOKUP, alpha-3 487 with T/B split), `iso_639_3_ed2007.py` (LOOKUP, comprehensive 7000+), `iso_639_5_ed2008.py` (LOOKUP, families/groups 115, `Scope: collection` gated), `bcp47_rfc5646_ed2009.py` (PARSER, ABNF well-formed only), `iana_language_subtag_registry_ed2026.py` (LOOKUP, Type membership + Prefix + Deprecated→Preferred-Value) — plus optional seventh `cldr_language_display_name_ed2025.py` (LOOKUP, `requires_features={"include_localized"}`) — with `target_semantics` routing (`bcp47_tag` validates via BCP47 PARSER + IANA LOOKUP, `language_code` validates via ISO 639-1/2/3/5 snapshots, `language_name` validates via English Description mapping and via CLDR when gated); `LanguageCapability.format_value` renders `bcp47` identity vs `alpha2`/`alpha3`/`alpha3-bib`/`name`; `LanguageContract` with `DEFAULT="bcp47"` `OFFERED={"alpha2","alpha3","alpha3-bib","name"}` and gated flags `include_localized/include_collective/include_private/include_grandfathered`; `single_value=True` per grammar; per-grammar containment dedup preserves `en-US` over `en`.

**Tech Stack:** Python 3.11+, uv, pytest (+ hypothesis), ruff, pyright strict, import-linter. No new dependencies.

**Basis:** `docs/development/research/2026-08-23-language-canonicalization.md` (913 lines, 91 KB, 16-section BIC/IBAN/ORCID-parity, primary-source citations: ISO 639 22109/4767/39534/74575, RFC 5646, IANA File-Date 2026-08-08, pycountry/langcodes/validator.js).

**Verified canonical vectors** (from research, become test constants):

| Input | Canonical `bcp47` | `alpha2` | `alpha3` | `name` | Note |
|---|---|---|---|---|---|
| `en` | `en` | `en` | `eng` | `English` | 639-1 exists → alpha-2 |
| `ENG` | `en` | `en` | `eng` | `English` | case-insensitive bare 3 |
| `ger` | `de` | `de` | `deu` | `German` | B 639-2 bib `ger` → T `deu` → alpha-2 `de` |
| `German` | `de` | `de` | `deu` | `German` | lexicon name → code |
| `fr_FR` | `fr-FR` | `fr` | `fra` | `French` | underscore tolerance |
| `EN-us` | `en-US` | `en` | `eng` | `English` | case canonicalization |
| `zh-Hans-CN` | `zh-Hans-CN` | `zh` | `zho` | `Chinese` | script Title + region Upper |
| `sl-nedis` | `sl-nedis` | `sl` | `slv` | `Slovenian` | variant prefix-constrained |
| `i-cherokee` | `chr` | `chr` | `chr` | `Cherokee` | grandfathered → preferred |
| `en-GB-oed` | `en-GB-oxendict` | `en` | `eng` | `English` | Deprecated+Preferred-Value |
| `iw` | `he` | `he` | `heb` | `Hebrew` | 639-1 deprecated 1989 |
| `qaa` (private) | `INVALID` default, `qaa` if `include_private` | — | — | — | gated |
| `aus` (collective) | `INVALID` default | — | — | — | Scope collection gated |

---

## File Structure

```
paxman/capabilities/Language/
├── __init__.py                         # Task 0 (scaffolder): exports
├── notation.py                         # Task 1: 10-field frozen-slots dataclass + normalize_name
├── contract.py                         # Task 2: DEFAULT bcp47, OFFERED {alpha2,alpha3,alpha3-bib,name}
├── capability.py                       # Task 5: wiring + create_contract + format_value seam
├── grammar/
│   ├── __init__.py                     # Task 0 (scaffolder)
│   ├── bcp47_tag_recognition.py        # Task 3: PipelineGrammar Regex ABNF-approximate
│   ├── language_code_recognition.py    # Task 3: PipelineGrammar Regex bare 2-3/5-8
│   ├── language_name_recognition.py    # Task 3: PipelineGrammar Lexicon WholeInputLookup
│   └── data/
│       ├── __init__.py                 # Task 3
│       ├── english_names.py            # Task 3: ENGLISH_LANGUAGE_KEYS (derived from rules/data/english_language_map.py keys)
│       └── localized_names.py          # Task 3: LOCALIZED stub — populated in Task 4 from CLDR data; gated via rule requires_features
└── rules/
    ├── __init__.py                     # Task 0 (scaffolder)
    ├── iso_639_1_ed2002.py             # Task 4: PUBLICATION ISO 639-1:2002 + Section4Alpha2 (LOOKUP, 184)
    ├── iso_639_2_ed1998.py             # Task 4: PUBLICATION ISO 639-2:1998 + Section4Alpha3 T/B (LOOKUP, 487; Library of Congress RA)
    ├── iso_639_3_ed2007.py             # Task 4: PUBLICATION ISO 639-3:2007 + Section4Comprehensive (LOOKUP, 7000+; SIL RA)
    ├── iso_639_5_ed2008.py             # Task 4: PUBLICATION ISO 639-5:2008 + families/groups (LOOKUP, 115; Scope collection gated)
    ├── bcp47_rfc5646_ed2009.py         # Task 4: PUBLICATION BCP 47 RFC 5646 + Section21Syntax (PARSER, well-formed only)
    ├── iana_language_subtag_registry_ed2026.py  # Task 4: PUBLICATION IANA Registry File-Date 2026-08-08 + Type membership + Prefix + Deprecated→Preferred (LOOKUP)
    ├── cldr_language_display_name_ed2025.py     # Task 4: PUBLICATION CLDR + localized display names (LOOKUP, requires_features={"include_localized"})
    └── data/
        ├── __init__.py
        ├── iso_639_1.py                # Task 4: ISO6391_ALPHA2 frozenset 184
        ├── iso_639_2.py                # Task 4: ISO6392_T/B dicts + ISO6392_BIB_TO_TERM map (ger→deu, fre→fra etc.)
        ├── iso_639_3.py                # Task 4: ISO6393_ALPHA3 frozenset 7000+ (comprehensive, T only)
        ├── iso_639_5.py                # Task 4: ISO6395_COLLECTIONS frozenset 115 + SCOPE_COLLECTION set (aus, afa etc.)
        ├── iana_language_subtags.py    # Task 4: IANA_LANGUAGE_SUBTAGS frozenset (Type: language)
        ├── iana_script_subtags.py      # Task 4: IANA_SCRIPT_SUBTAGS frozenset (Type: script, ISO 15924)
        ├── iana_region_subtags.py      # Task 4: IANA_REGION_SUBTAGS frozenset (Type: region, ISO 3166-1 + UN M.49)
        ├── iana_variant_subtags.py     # Task 4: IANA_VARIANT_PREFIXES dict[str, set[str]] (variant→prefixes) + IANA_VARIANT_SUBTAGS frozenset
        ├── iana_grandfathered.py       # Task 4: GRANDFATHERED_PREFERRED dict (lower→preferred) + GRANDFATHERED_TAGS frozenset
        ├── iana_deprecated_map.py      # Task 4: DEPRECATED_MAP dict (iw→he etc.) + DEPRECATED_SET frozenset
        └── english_language_map.py     # Task 4: NAME_TO_CANONICAL dict (normalize_name key → canonical bcp47 lower)

tests/capabilities/language/
├── __init__.py                         # Task 0 (scaffolder)
├── test_notation.py                    # Tasks 0→1
├── test_contract.py                    # Tasks 0→2
├── test_grammar.py                     # Tasks 0→3 (3 grammars + WholeInputLookup + BoundaryGuard)
├── test_rules.py                       # Tasks 0→4 (6 publications + CLDR gated)
└── test_capability.py                  # Tasks 0→5

tests/integration/test_language_capability.py   # Task 7 (new)
tests/property/test_language_property.py        # Task 8 (new)

Modify:
paxman/api/bootstrap.py                          # Task 7 (_SHIPPED, if bootstrapped — see Task 6 note)
tests/unit/test_capability_exports.py:XX         # Task 6 (== 14 → == 15 if bootstrapped, else no)
CONTEXT.md                                       # Task 6 (notation bullet + 3-col table row + count)
README.md                                        # Task 6 (regen table via tools/generate_readme_table.py)
```

**Engine semantics note (read before Task 4):** `_collect_candidates` in `paxman/engine/orchestrator.py` routes each recognition to rules whose `target_semantics` contains the grammar's `semantics`. Therefore Language's three grammars MUST have distinct `semantics` (`bcp47_tag`, `language_code`, `language_name`) and rules MUST declare the correct `target_semantics`. A bare `en` recognized by `language_code_recognition` must NOT be validated by the BCP47 ABNF rule (which expects hyphenated structure) — keep routing strict. Candidate dedup `(value, recognition_rule, validation_rule)` ensures `ger`→`de` and `de`→`de` coalesce only when normalize agrees. IANA registry rule also declares `target_semantics={"bcp47_tag"}` and validates `Type: language/script/region/variant` + `Prefix` per subtag, not bare codes.

**Country precedent note:** `paxman/capabilities/Country/notation.py:normalize_name()` is the shared normalizer used by both `WholeInputLookup` and rule normalized views. Language MUST replicate this pattern: `paxman/capabilities/Language/notation.py:normalize_name()` used by `language_name_recognition` lexicon and `iso_639_*` rules. Do not duplicate normalization logic in `rules/data/`.

**Provenance per-file note (read before Task 4 — one file per publication):** Each `rules/*.py` carries exactly one `PUBLICATION: Provenance` with publication-specific `authority`/`specification_name`/`reference_url`/`version`/`lifecycle`/`publication_year`/`kind`. Do not copy-paste the scaffolder's `IETF` provenance into ISO files. Correct mapping per research §5 citation table: `iso_639_1_ed2002.py` → `authority="ISO"`, `iso_639_2_ed1998.py` → `authority="ISO"` + `Library of Congress RA` citation header, `iso_639_3_ed2007.py` → `authority="SIL International (ISO 639-3 RA)"`, `iso_639_5_ed2008.py` → `authority="ISO"`, `bcp47_rfc5646_ed2009.py` → `authority="IETF"`, `iana_language_subtag_registry_ed2026.py` → `authority="IANA"` `kind="registry"` `version="Rolling File-Date 2026-08-08"`, `cldr_language_display_name_ed2025.py` → `authority="Unicode CLDR"` `kind="registry"`.

---

### Task 0: Scaffold the skeleton

**Files:**
- Create: `paxman/capabilities/Language/**` (13 files via scaffolder)
- Create: `tests/capabilities/language/**` (5 files via scaffolder)
- Modify: `paxman/capabilities/__init__.py` (scaffolder edits import + `__all__`)
- Test: `tests/capabilities/language/*` stubs (auto-generated)

- [ ] **Step 0.1: Verify clean tree**

Run: `git status --short`
Expected: empty (or only pre-existing `docs/development/research/2026-08-23-language-canonicalization.md` untracked — do not proceed on dirty `paxman/` without stashing).

- [ ] **Step 0.2: Run the scaffolder**

```bash
uv run python tools/new_capability.py Language --name language \
    --authority "IETF" \
    --spec-name "BCP 47 RFC 5646" \
    --spec-url "https://www.rfc-editor.org/rfc/rfc5646.txt" \
    --publication-year 2009 \
    --spec-version "2009-09" \
    --default-format bcp47
```

Expected output: list of created files ending with human checklist ("Replace the placeholder grammar pattern…"). Note: scaffolder emits `PUBLICATION` with `lifecycle="active"` — correct for BCP47. Scaffold rule file will be `rules/ietf_ed2009.py` — renamed in Task 4.

- [ ] **Step 0.3: Confirm stub tests are green**

Run: `uv run pytest tests/capabilities/language/ -q`
Expected: all pass (scaffold guarantees green skeleton).

Run: `uv run pytest tests/unit/test_capability_exports.py -q`
Expected: PASS — scaffolder wired `paxman/capabilities/__init__.py`; export-completeness is dynamic and now sees `Language`.

- [ ] **Step 0.4: Commit**

```bash
git add paxman/capabilities/Language tests/capabilities/language paxman/capabilities/__init__.py
git commit -m "feat(language): scaffold Language capability skeleton"
```

---

### Task 1: Notation — 10-field frozen dataclass + normalize_name

**Files:**
- Modify: `paxman/capabilities/Language/notation.py` (replace scaffold placeholder)
- Modify: `tests/capabilities/language/test_notation.py` (replace scaffold placeholder tests)

Research §3.1: `language` 2-8 lower, `extlang` "" or hyphen-joined 3-letter, `script` "" or Title 4, `region` "" or UPPER 2|3-digit, `variant` "" or hyphen-joined lower, `extension` "", `privateuse` "", `grandfathered` "", `compact` case-canonicalized tag, `raw_value` trimmed lower. All `str`, frozen+slots. Optional `__post_init__` enforces `slots` via dataclass, not manual. Shared `normalize_name()` for lexicon: NFKD → strip accents → lower → separator→space → punctuation strip → whitespace collapse (mirror `Country/notation.py:normalize_name`).

- [ ] **Step 1.1: Write the failing notation tests**

Replace `tests/capabilities/language/test_notation.py`:

```python
"""Tests for LanguageNotation — frozen, slots, all-str fields, normalize_name."""

from __future__ import annotations

import dataclasses

import pytest

from paxman.capabilities.Language.notation import LanguageNotation, normalize_name

pytestmark = [pytest.mark.capability]


class TestLanguageNotation:
    def test_frozen(self) -> None:
        notation = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US",
            raw_value="en-US",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            notation.compact = "x"  # type: ignore[misc]

    def test_hashable_and_eq(self) -> None:
        a = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US",
            raw_value="en-US",
        )
        b = LanguageNotation(
            language="en",
            extlang="",
            script="",
            region="US",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="en-US",
            raw_value="en-US",
        )
        assert a == b
        assert hash(a) == hash(b)
        assert len({a, b}) == 1

    def test_slots(self) -> None:
        assert LanguageNotation.__dataclass_params__.slots is True

    def test_all_fields_are_str(self) -> None:
        for field in dataclasses.fields(LanguageNotation):
            assert field.type is str, field.name

    def test_field_values(self) -> None:
        notation = LanguageNotation(
            language="zh",
            extlang="",
            script="Hans",
            region="CN",
            variant="",
            extension="",
            privateuse="",
            grandfathered="",
            compact="zh-Hans-CN",
            raw_value="zh-Hans-CN",
        )
        assert notation.script == "Hans"
        assert notation.region == "CN"
        assert notation.compact == "zh-Hans-CN"

    def test_normalize_name(self) -> None:
        assert normalize_name("German") == "german"
        assert normalize_name("  Français  ") == "francais"
        assert normalize_name("Srpski (Serbian)") == "srpski serbian"
        assert normalize_name("Español") == "espanol"
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/language/test_notation.py -q`
Expected: FAIL — placeholder notation has single `value` field, not 10 fields.

- [ ] **Step 1.3: Write the notation**

Replace `paxman/capabilities/Language/notation.py`:

```python
"""Language notation: grammar-normalized BCP 47 / bare code / name form."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def normalize_name(name: str) -> str:
    """Normalize language display name for lexicon lookup.

    Mirrors Country normalize_name: NFKD decomposition, separator→space,
    alphanumeric-or-space filter, whitespace collapse, lower. Shared by
    grammar WholeInputLookup and rule views — do not duplicate.
    """
    nfkd = unicodedata.normalize("NFKD", name)
    without_accents = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    # separators to space
    as_space = re.sub(r"[\"'’`._\-\u2010-\u2015]+", " ", without_accents)
    filtered = "".join(ch if ch.isalnum() or ch == " " else " " for ch in as_space)
    collapsed = " ".join(filtered.lower().split())
    return collapsed


@dataclass(frozen=True, slots=True)
class LanguageNotation:
    """Language normalized form.

    ``language`` primary subtag lower (2-8), or "" when grandfathered/privateuse-only.
    ``extlang`` hyphen-joined 3-letter extlangs or "".
    ``script`` 4-letter Title or "".
    ``region`` 2-letter Upper or 3-digit or "".
    ``variant`` hyphen-joined lower or "".
    ``extension`` hyphen-joined lower or "".
    ``privateuse`` "x-..." or "".
    ``grandfathered`` raw grandfathered lower or "".
    ``compact`` BCP 47 case-canonicalized tag or bare lower.
    ``raw_value`` original trimmed lower for lexicon.
    Grammar never validates registry; rules own it.
    """

    language: str
    extlang: str
    script: str
    region: str
    variant: str
    extension: str
    privateuse: str
    grandfathered: str
    compact: str
    raw_value: str
```

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/language/test_notation.py -q`
Expected: PASS (all). Other modules `test_grammar.py` etc. may FAIL until Tasks 3-5 — expected.

- [ ] **Step 1.5: Commit**

```bash
git add paxman/capabilities/Language/notation.py tests/capabilities/language/test_notation.py
git commit -m "feat(language): 10-field LanguageNotation + normalize_name"
```

---

### Task 2: Contract — LanguageContract

**Files:**
- Modify: `paxman/capabilities/Language/contract.py`
- Modify: `tests/capabilities/language/test_contract.py` (scaffold placeholder → contract tests)

Research §6.1 + Decision 1: `DEFAULT="bcp47"` (case-canonical tag per §2.1.1), `OFFERED={"alpha2","alpha3","alpha3-bib","name"}`. Flags: `include_localized` (CLDR display names, default False → lexicon still recognizes localized keys but rule dropped → INVALID), `include_collective` (Scope collection `aus`), `include_private` (`qaa-qtz` + `x-`), `include_grandfathered` (default True). No `active_grammars` override in v1 (base None runs all 3 grammars); if you add one, mirror ISBN pattern (conditional list).

- [ ] **Step 2.1: Write the failing contract tests**

Replace `tests/capabilities/language/test_contract.py`:

```python
import pytest
from dataclasses import FrozenInstanceError
from paxman.capabilities.Language.contract import LanguageContract
from paxman.core.errors import ContractError

pytestmark = [pytest.mark.capability]


def test_defaults():
    c = LanguageContract()
    assert c.output_format == "bcp47"
    assert c.capability_name == "language"
    assert LanguageContract.DEFAULT_OUTPUT_FORMAT == "bcp47"
    assert LanguageContract.OFFERED_OUTPUT_FORMATS == frozenset(
        {"alpha2", "alpha3", "alpha3-bib", "name"}
    )
    assert c.include_localized is False
    assert c.include_collective is False
    assert c.include_private is False
    assert c.include_grandfathered is True


def test_offered():
    for fmt in ("alpha2", "alpha3", "alpha3-bib", "name"):
        assert LanguageContract(output_format=fmt).output_format == fmt


def test_default_alias():
    for alias in (None, "default", "bcp47"):
        assert LanguageContract(output_format=alias).output_format == "bcp47"


def test_invalid_raises():
    for bad in ("paper", "iso", "hyphenated", "", "BCP47"):
        with pytest.raises(ContractError):
            LanguageContract(output_format=bad)  # type: ignore[arg-type]


def test_flags():
    c = LanguageContract(include_private=True, include_collective=True)
    assert c.include_private is True and c.include_collective is True


def test_frozen():
    c = LanguageContract()
    with pytest.raises(FrozenInstanceError):
        c.output_format = "alpha2"  # type: ignore[misc]
```

- [ ] **Step 2.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/language/test_contract.py -v`
Expected: FAIL — scaffold has empty `OFFERED_OUTPUT_FORMATS` plus missing flags.

- [ ] **Step 2.3: Write minimal implementation**

Replace `paxman/capabilities/Language/contract.py`:

```python
"""Language contract — user-facing configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.capability_contract import CapabilityContract


@dataclass(frozen=True)
class LanguageContract(CapabilityContract):
    """Contract for the Language capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "bcp47"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"alpha2", "alpha3", "alpha3-bib", "name"}
    )

    capability_name: str = field(default="language", init=False)
    include_localized: bool = False
    include_collective: bool = False
    include_private: bool = False
    include_grandfathered: bool = True
```

- [ ] **Step 2.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/language/test_contract.py -v` → PASS.
Run: `uv run pyright paxman/capabilities/Language/contract.py` → 0 errors, `uv run ruff check paxman/capabilities/Language/contract.py`

- [ ] **Step 2.5: Commit**

```bash
git add paxman/capabilities/Language/contract.py tests/capabilities/language/test_contract.py
git commit -m "feat(language): LanguageContract bcp47 default with 4 offered formats"
```

---

### Task 3: Grammars — 3 PipelineGrammars (TDD)

**Files:**
- Modify: `paxman/capabilities/Language/grammar/bcp47_tag_recognition.py` (new)
- Modify: `paxman/capabilities/Language/grammar/language_code_recognition.py` (new)
- Modify: `paxman/capabilities/Language/grammar/language_name_recognition.py` (new)
- Create: `paxman/capabilities/Language/grammar/data/english_names.py`, `localized_names.py`, `__init__.py`
- Modify: `paxman/capabilities/Language/grammar/__init__.py`
- Modify: `tests/capabilities/language/test_grammar.py`

Research §4.2: `bcp47_tag` Regex ABNF-approximate with underscore tolerance via `StandardPre` that replaces `_`→`-` in `PipelineState` scratch (not in `raw_text`), keeping span `[start,end)` on original text and `notation.compact` hyphen-canonical; `language_code` Regex `2-3|5-8` via `BoundaryGuard.word_only`; `language_name` Lexicon `WholeInputLookup` union `ENGLISH_LANGUAGE_KEYS` (≈200 English display names derived from `rules/data/english_language_map.py` keys) + `LOCALIZED_LANGUAGE_KEYS` (≈1000, generated from `rules/data/cldr` source — populated in Task 4, not hand-curated).

- [ ] **Step 3.0: Prepare grammar data stubs**

Create `paxman/capabilities/Language/grammar/data/english_names.py` (keys derived from `rules/data/english_language_map.py` union — do NOT hand-curate 20 entries; initial stub of 20 is for green-skeleton only, expanded to 200+ in Task 4 from ISO 639 English Description fields):

```python
# Derived from paxman/capabilities/Language/rules/data/english_language_map.py
# Header: Source IANA Language Subtag Registry + ISO 639 English Description, generated 2026-08-08
ENGLISH_LANGUAGE_KEYS: frozenset[str] = frozenset(
    {
        "english",
        "german",
        "french",
        "spanish",
        "japanese",
        "chinese",
        "arabic",
        "russian",
        "portuguese",
        "italian",
        "dutch",
        "korean",
        "hindi",
        "turkish",
        "polish",
        "swedish",
        "danish",
        "norwegian",
        "finnish",
        "czech",
        "hebrew",
        "indonesian",
        "yiddish",
        "moldavian",
        "cherokee",
        "bihari",
        "serbo croatian",
    }
)
```

Create `paxman/capabilities/Language/grammar/data/localized_names.py` as gated stub (populated in Task 4 from `rules/data/cldr_language_display_name.py` or CLDR JSON; grammar always recognizes union but validation is gated via `cldr_language_display_name_ed2025.py` `requires_features={"include_localized"}` — without flag, localized recognition yields `INVALID` not `MISSING`, matching Country precedent):

```python
LOCALIZED_LANGUAGE_KEYS: frozenset[str] = frozenset(
    {
        # Populated in Task 4 from CLDR; stub empty or minimal for Task 3 green
    }
)
```

(Real Task 4 will populate `english_names.py` 200+ from `rules/data/english_language_map.py` keys and `localized_names.py` 1000+ from CLDR; grammar/data stays key-only, data logic in rules/data.)

- [ ] **Step 3.1: Write the failing grammar tests**

Replace `tests/capabilities/language/test_grammar.py` (expect 25+ tests across 3 grammars: valid bcp47 `zh-Hans-CN`, underscore `fr_FR`, mixed case `EN-us`, multiple matches, boundary guards, semantics/name, empty, span invariants, lexicon case).

Prose: Tests assert `len == 1` + span `(start,end)` + `notation.compact` + `notation.language/script/region` for bcp47; bare codes; lexicon names; multiple mentions; quoted/bracketed; invalid `Xen`/`enUS` glue → `MISSING`. **Must assert underscore span invariant:** `fr_FR` at `(0,5)` has `raw_text=="fr_FR"` and `notation.compact=="fr-FR"` and `notation.language=="fr"` `region=="FR"`.

- [ ] **Step 3.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/language/test_grammar.py -q`
Expected: FAIL — placeholders produce no matches.

- [ ] **Step 3.3: Write the 3 grammars**

`bcp47_tag_recognition.py` — module-scope string `_BCP47_BODY` with ABNF `language ["-" script] ["-" region] *("-" variant) *("-" extension) ["-" privateuse]` plus grandfathered enumerated alternation (26 tags) plus `x-` privateuse; wrapped via `BoundaryGuard.word_only()`; `PipelineGrammar` with `StandardPre(empty_guard=True)` that **first** replaces `_`→`-` in `PipelineState.text` scratch for regex matching while preserving original `raw_text` span, then `RegexStage` with `notation_fn` decomposing via RFC 5646 §2.2 position/length inference: `language` 2-8 at start, `extlang` 3-letter following `language` (`zh-cmn` → `language=zh extlang=cmn`), `script` 4 letters Title (`Hans`), `region` 2 letters Upper or 3 digits (`US`/`419`), `variant` 5-8 alphanum or digit+3alphanum split on `-`, singleton→`extension` (`a-`), `x`→`privateuse`, `grandfathered` enumerated table (lower). `compact` assembled as BCP 47 case-canonicalized tag (language lower, script Title, region Upper, variant/extension/private lower, grandfathered lower→preferred not yet — preferred applied in rules). Do NOT use `[-_]` inside regex — underscore handling is Pre-only to keep `raw_text` vs `compact` contract.

`language_code_recognition.py` — `BoundaryGuard.word_only()` + `r"(?P<code>[A-Za-z]{2,3}|[A-Za-z]{5,8})"`; notation lower + empty other fields.

`language_name_recognition.py` — `WholeInputLookup(keys=_KNOWN_LANGUAGE_KEYS, normalizer=normalize_name, ...)` where `_KNOWN_LANGUAGE_KEYS = frozenset(ENGLISH_LANGUAGE_KEYS | LOCALIZED_LANGUAGE_KEYS)`; lexicon case-insensitive via `normalize_name` (NFKD etc.).

Expose in `grammar/__init__.py`. All 3 grammars `single_value=True`, distinct `semantics` (`bcp47_tag`, `language_code`, `language_name`).

- [ ] **Step 3.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/language/test_grammar.py -v` → 20+ PASS.

- [ ] **Step 3.5: Commit**

```bash
git add paxman/capabilities/Language/grammar/ tests/capabilities/language/test_grammar.py
git commit -m "feat(language): 3 grammars bcp47/code/name with BoundaryGuard and WholeInputLookup"
```

---

### Task 4: Rules — 6 publications + 1 CLDR with data (TDD)

**Files:**
- Rename: `paxman/capabilities/Language/rules/ietf_ed2009.py` → `paxman/capabilities/Language/rules/bcp47_rfc5646_ed2009.py` (`git mv`)
- Create: `paxman/capabilities/Language/rules/iso_639_1_ed2002.py`, `iso_639_2_ed1998.py`, `iso_639_3_ed2007.py`, `iso_639_5_ed2008.py`, `iana_language_subtag_registry_ed2026.py`, `cldr_language_display_name_ed2025.py`
- Create: `paxman/capabilities/Language/rules/data/*.py` (11 files: `iso_639_1.py`, `iso_639_2.py`, `iso_639_3.py`, `iso_639_5.py`, `iana_language_subtags.py`, `iana_script_subtags.py`, `iana_region_subtags.py`, `iana_variant_subtags.py`, `iana_grandfathered.py`, `iana_deprecated_map.py`, `english_language_map.py`)
- Modify: `tests/capabilities/language/test_rules.py`

Research §5.2: One `PUBLICATION` per file, 6 enforced metadata attrs. `Strategy` is `LOOKUP_TABLE` except `bcp47_rfc5646_ed2009.py` is `PARSER` (ABNF well-formed only — no registry, no Prefix, no Deprecated). `target_semantics` + `requires_features` exact:

| Rule file | `target_semantics` | `requires_features` | Strategy | Validates |
|---|---|---|---|---|
| `iso_639_1_ed2002.py` | `{"language_code"}` | `{}` | LOOKUP | Bare alpha-2 184 membership |
| `iso_639_2_ed1998.py` | `{"language_code"}` | `{}` | LOOKUP | Bare alpha-3 487 T/B; B→T map `ger→deu` via `iso_639_2.py` |
| `iso_639_3_ed2007.py` | `{"language_code"}` | `{}` | LOOKUP | Bare alpha-3 comprehensive 7000+ (T only) |
| `iso_639_5_ed2008.py` | `{"language_code"}` | `{"include_collective"}` | LOOKUP | Scope collection 115 (`aus`, `afa`, `bih` etc.) — only when flag True; without flag `aus` is not validated → `INVALID` |
| `bcp47_rfc5646_ed2009.py` | `{"bcp47_tag"}` | `{}` | PARSER | ABNF well-formed only (`en-US` ok, `en--US`/`en-`/`e` rejected); grandfathered shape via enumerated table but Preferred-Value applied by IANA rule; no registry lookup |
| `iana_language_subtag_registry_ed2026.py` | `{"bcp47_tag"}` | `{}` (private sub-check gated internally via `contract.include_private`) | LOOKUP | Registry Type membership: `language` exists in `IANA_LANGUAGE_SUBTAGS`, `script` in `IANA_SCRIPT_SUBTAGS`, `region` in `IANA_REGION_SUBTAGS`, `variant` in `IANA_VARIANT_SUBTAGS` + **Prefix constraint** `variant` prefix must contain tag prefix (`sl-nedis` needs prefix `sl`, `de-nedis` rejected), `Deprecated→Preferred-Value` chain, `private` `qaa-qtz` + `x-` only when `include_private=True`, grandfathered `i-cherokee→chr` preferred |
| `cldr_language_display_name_ed2025.py` | `{"language_name"}` | `{"include_localized"}` | LOOKUP | Localized display names (`Deutsch→de`) — only when flag True |

`language_name` for English names is validated by `iso_639_*` rules that also accept `language_name` semantics? No — keep strict: English name→code is own LOOKUP via `english_language_map.py` shared with `iso_639_*`? Instead: add `SectionEnglishNameMapping` LOOKUP with `target_semantics={"language_name"}` `requires_features={}` in `iso_639_3_ed2007.py` or `cldr`? Plan keeps English name validation in `iso_639_*` family: simplest is `iso_639_1_ed2002.py` additional class `SectionEnglishName` LOOKUP `{"language_name"}`. Do not create value-only English name table without owning publication — English Description is field of IANA/ISO records.

- [ ] **Step 4.0: Rename scaffold rule**

```bash
git mv paxman/capabilities/Language/rules/ietf_ed2009.py paxman/capabilities/Language/rules/bcp47_rfc5646_ed2009.py
```

Fix imports in `paxman/capabilities/Language/capability.py` later (Task 5). For each new rule file, set `PUBLICATION` with correct `authority`/`specification_name`/`reference_url`/`version`/`lifecycle`/`publication_year`/`kind` per Provenance per-file note above — do not copy-paste IETF into ISO.

- [ ] **Step 4.1: Populate rules/data from IANA + ISO snapshots**

Generate 184-entry `iso_639_1.py` `frozenset` from ISO table (use `pycountry` enumeration as seed; cite source header URL + date + File-Date). Generate `iso_639_2.py` with `ISO6392_T` frozenset, `ISO6392_B` frozenset, `ISO6392_BIB_TO_TERM: dict[str,str]` (`ger→deu`, `fre→fra`, `chi→zho` etc.), `ISO6392_T_TO_ALPHA2: dict[str,str]` for bib→alpha2. Generate `iso_639_3.py` 7000+ `frozenset`. Generate `iso_639_5.py` 115 `frozenset` + `SCOPE_COLLECTION` set. Generate `iana_language_subtags.py` `frozenset` Type: language, `iana_script_subtags.py` Type: script via ISO 15924, `iana_region_subtags.py` Type: region via ISO 3166-1 + UN M.49, `iana_variant_subtags.py` with `IANA_VARIANT_SUBTAGS` frozenset + `VARIANT_PREFIXES: dict[str, set[str]]` (`nedis→{"sl"}`, `1996→{"de","sl"}` etc.), `iana_grandfathered.py` with `GRANDFATHERED_PREFERRED: dict[str,str]` lower→preferred + `GRANDFATHERED_TAGS` frozenset (26), `iana_deprecated_map.py` with `DEPRECATED_MAP: dict[str,str]` (`iw→he`, `in→id`, `ji→yi`, `jw→jv`, `mo→ro`, `bh→bih` etc.) chain. Generate `english_language_map.py` `NAME_TO_CANONICAL: dict[str,str]` keys are `normalize_name` output → value is lower canonical `de`/`en` etc. (derived from IANA Description first entry + ISO 639 English name). Keep plain module-level tables separated from logic (HOW_TO §5). Grammar/data `english_names.py` keys are exactly `set(english_language_map.NAME_TO_CANONICAL)` and `localized_names.py` keys are `set(cldr_map)` — single source of truth, no duplication.

- [ ] **Step 4.2: Write the failing rule tests**

Replace `tests/capabilities/language/test_rules.py` — 7 test classes:

- `TestISO6391`: `en` valid, `xx` invalid, `EN` lower variant, normalize lower, provenance `authority="ISO"` `specification_name="ISO 639-1:2002"` `publication_year=2002` `kind="specification"`, `strategy=LOOKUP_TABLE`, `target_semantics={"language_code"}`, `requires_features` empty.
- `TestISO6392`: `eng` valid T, `ger` B valid but normalizes to `deu` preferred T, `ger→de` via T→alpha2 mapping, `mis` special, provenance `ISO 639-2:1998` `Library of Congress` citation, `LOOKUP_TABLE`, `{"language_code"}`.
- `TestISO6393`: `cmn` extlang comprehensive valid, `qaa` private reserved without flag → `INVALID` vs with `include_private`? Actually `qaa` is ISO 639-3 private, but IANA `qaa-qtz` private gated — clarify: `iso_639_3` rejects `qaa` unless `include_private`; test both branches.
- `TestISO6395`: `aus` Scope collection `INVALID` default (rule not run), `SUCCESS` with `include_collective=True`, provenance `ISO 639-5:2008`.
- `TestBCP47`: valid `en-US`, invalid `en--US`, `i-cherokee` grandfathered shape well-formed (preferred applied by IANA rule, not BCP47), `x-fr-CH` privateuse shape well-formed, `en-Qaaa` shape well-formed (`4 letters` script position), `DEPRECATED_MAP` chain not applied here, well-formed vs registry: `en-US-123456789` too-long rejected, `requires_features` empty, `PARSER`.
- `TestIANA`: valid `sl-nedis`, invalid prefix `de-nedis`, script `Hans` valid vs `Qaaa` private (only with `include_private`), region `US` valid vs `ZZ` private (only with `include_private`) vs `XX` private, `Deprecated`→`Preferred` chain `iw→he`, `en-GB-oed→en-GB-oxendict` via grandfathered, `zh-Hans-CN` script+region membership passes, `Prefix` dict enforced, `Suppress-Script: Latn` informative (`en-Latn` still `SUCCESS`), `extlang` `zh-cmn` macrolanguage envelope valid (`cmn` extlang + `zh` language), `target_semantics={"bcp47_tag"}`, provenance `IANA` `kind="registry"` `version="Rolling File-Date 2026-08-08"`.
- `TestCLDR`: `Deutsch→de` with `include_localized=True` `SUCCESS`, without flag `INVALID` (rule not run, no other language_name validator), `strategy=LOOKUP_TABLE`, `requires_features={"include_localized"}`, provenance `Unicode CLDR`.

- [ ] **Step 4.3: Write the 7 rule files**

Each with `PUBLICATION = Provenance(...)` citing `authority`, `specification_name`, `reference_url`, `version`, `lifecycle`, `publication_year` per table above plus `kind`. Example:

```python
# bcp47_rfc5646_ed2009.py — PARSER well-formed only
PUBLICATION = Provenance(
    authority="IETF",
    specification_name="BCP 47 RFC 5646",
    kind="specification",
    reference_url="https://www.rfc-editor.org/rfc/rfc5646.txt",
    version="2009-09",
    lifecycle="active",
    publication_year=2009,
)


class Section21Syntax(Rule[LanguageNotation]):
    name = "Section 2.1-syntax"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 2.1 (ABNF well-formed)"
    target_semantics = frozenset({"bcp47_tag"})
    requires_features = frozenset()

    def matches(
        self, notation: LanguageNotation, contract: Contract
    ) -> bool:  # ABNF regex fullmatch + no empty subtags, extlang 3* handling
        ...
    def normalize(
        self, notation: LanguageNotation, contract: Contract
    ) -> str:  # language lower, script Title, region Upper, variant lower, x- lower
        ...
```

Analog for LOOKUP rules: `if notation.language not in IANA_LANGUAGE_SUBTAGS: return False` plus `Deprecated→Preferred` via `DEPRECATED_MAP`, `variant` Prefix check via `VARIANT_PREFIXES[notation.variant]` must contain tag prefix, `script`/`region` Type membership via split IANA sets, `private` `qaa-qtz` and `x-` gated via `if not contract.include_private and (is_private(...)): return False`, `Suppress-Script` never rejects, `extlang` validated via `iso_639_3` macrolanguage envelope.

No `output_format` token anywhere (source scan).

- [ ] **Step 4.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/language/test_rules.py -v` → PASS (7 classes, ~30 tests).
Run: `grep -r output_format paxman/capabilities/Language/rules/ || echo "clean"` → clean.
Run: `uv run pyright paxman/capabilities/Language/rules/` → 0 errors.

- [ ] **Step 4.5: Commit**

```bash
git add paxman/capabilities/Language/rules/ tests/capabilities/language/test_rules.py
git commit -m "feat(language): 7 rule files ISO639 1/2/3/5 + BCP47 PARSER + IANA LOOKUP + CLDR gated"
```

---

### Task 5: Capability — wiring, create_contract, format_value

**Files:**
- Modify: `paxman/capabilities/Language/capability.py`
- Modify: `tests/capabilities/language/test_capability.py`

Research §6.2: `name="language"`, `version="1.0.0"`, `get_grammars() → 3`, `get_rules() → 7` (6 always + 1 CLDR gated), `create_contract` tuple-normalizes args (shipped idiom), `format_value` branch per `output_format`: `bcp47` identity, `alpha2` via `ALPHA2_MAP` (639-1 else T→alpha-2 else `ger`→`de`), `alpha3` Term lower (`deu`), `alpha3-bib` Bib lower (`ger`), `name` English Description title.

- [ ] **Step 5.1: Write the failing capability tests**

Replace `tests/capabilities/language/test_capability.py` — assert `name`, `get_grammars` len 3 with names/semantics, `get_rules` len 7 with names/provenances/target_semantics, `create_contract` defaults (`output_format bcp47`, `active_grammars None`, flags), invalid format raises `ContractError`, `format_value` for each offered vs identity, version string.

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `uv run pytest tests/capabilities/language/test_capability.py -v` → FAIL (stub).

- [ ] **Step 5.3: Write minimal implementation**

Replace `paxman/capabilities/Language/capability.py` with 3-grammar / 7-rule wiring + `format_value` mapping via `rules/data/*.py` (alpha2 via `ISO6391_ALPHA2` else `ISO6392_T_TO_ALPHA2[term]` else term itself; alpha3 Term via `ISO6392_BIB_TO_TERM.get(code, code)`; alpha3-bib via reverse map; name via `english_language_map` reverse).

- [ ] **Step 5.4: Run tests to verify they pass**

Run: `uv run pytest tests/capabilities/language/test_capability.py -v` → PASS.

- [ ] **Step 5.5: Commit**

```bash
git add paxman/capabilities/Language/capability.py tests/capabilities/language/test_capability.py
git commit -m "feat(language): wire LanguageCapability with bcp47/alpha2/alpha3/name seam"
```

---

### Task 6: Exports, Surface Homogeneity, and Docs

**Files:**
- Modify: `paxman/capabilities/__init__.py` (verify — scaffolder auto)
- Modify: `tests/unit/test_capability_exports.py` (if bootstrapped, else no)
- Modify: `CONTEXT.md` (notation bullet + 3-col table row + count wording)
- Modify: `docs/development/MILESTONE.md` (Language row already exists — verify)
- Modify: `README.md` (regen table)

Scaffolder already edited `__init__.py` alphabetically + `tests/unit/test_capability_surface.py`. `Language` insertion between `ISBN` and `Money`? Check `__all__` order: existing 14 are `["BIC","Country","Currency","Date","Email","IBAN","IP","ISBN","ISSN","Money","ORCID","Phone","SIUnit","URL"]` — `Language` sorts after `ISSN` before `Money` (L...) so `__all__` becomes 15. Update `test_capability_exports.py` only if `bootstrap._SHIPPED` includes Language (see decision below); otherwise like IBAN precedent keep `_SHIPPED` without Language (shipped but not bootstrapped) and skip export test patch for bootstrap — but exports test checks `__all__` which DOES include Language (scaffolder), so patch it regardless.

- [ ] **Step 6.1: Patch the exports completeness gate**

Verify `uv run pytest tests/unit/test_capability_exports.py -v` — expect FAIL showing set mismatch missing `Language`. Patch:

```python
from paxman.capabilities import (
    BIC,
    Country,
    Currency,
    Date,
    Email,
    IBAN,
    IP,
    ISBN,
    ISSN,
    Language,
    Money,
    ORCID,
    Phone,
    SIUnit,
    URL,
)


class TestLanguageCapabilityExports:
    @pytest.mark.unit
    def test_language_capability_importable(self) -> None:
        assert Language is not None

    @pytest.mark.unit
    def test_language_capability_name(self) -> None:
        assert Language.name == "language"


# In test_export_list_contains expected set, add "Language"
assert set(capabilities.__all__) == {
    "BIC",
    "Country",
    "Currency",
    "Date",
    "Email",
    "IBAN",
    "IP",
    "ISBN",
    "ISSN",
    "Language",
    "Money",
    "ORCID",
    "Phone",
    "SIUnit",
    "URL",
}
```

- [ ] **Step 6.2: Run homogeneity gate**

Run: `uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py -v` → PASS.

- [ ] **Step 6.3: Patch CONTEXT.md**

Edits:

1. Notation bullet after ISSN:
```
- **Language:** `LanguageNotation(language, extlang, script, region, variant, extension, privateuse, grandfathered, compact, raw_value)` — `language` 2-8 lower, `extlang` 3-letter hyphen-joined (e.g. `cmn` for `zh-cmn`), `script` Title 4, `region` Upper 2|3-digit, `variant` lower prefix-constrained via `VARIANT_PREFIXES` dict (`sl-nedis` ok, `de-nedis` rejected), `grandfathered` lower (preferred via `GRANDFATHERED_PREFERRED`), `compact` BCP47 case-canonical tag or bare lower, `raw_value` trimmed lower for lexicon; grammar strips case/underscore via `StandardPre` (`_`→`-` in PipelineState, `raw_text` preserves original), rules own registry + Prefix + Deprecated chain + Suppress-Script (informative, never rejects)
```

2. Capabilities table row after ISSN:
```
| **Language** | Language identifiers | ISO 639-1:2002, ISO 639-2:1998, ISO 639-3:2007, ISO 639-5:2008, BCP 47 RFC 5646, IANA Language Subtag Registry (File-Date 2026-08-08), CLDR (localized, gated) |
```

3. Count wording intro sentence `fourteen built-in` → `fifteen built-in`.

Do NOT paste 7-col row; CONTEXT table is 3 columns.

- [ ] **Step 6.4: Verify MILESTONE row**

MILESTONE row 2 for Language already exists with correct grammar strategy LOOKUP_TABLE and example inputs — verify it still matches; do not duplicate.

- [ ] **Step 6.5: Regenerate README table**

```bash
uv run python tools/generate_readme_table.py
git diff README.md  # should show Language row inserted alphabetically
```

- [ ] **Step 6.6: Run gates**

```bash
uv run pytest tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py tests/unit/test_rule_output_format_purity.py -v
uv run pyright
uv run ruff check paxman/ tests/
uv run import-linter lint
```

Expected: all PASS (purity scan finds no `output_format` in `Language/rules/`).

- [ ] **Step 6.7: Commit**

```bash
git add paxman/capabilities/__init__.py tests/unit/test_capability_exports.py tests/unit/test_capability_surface.py CONTEXT.md README.md
git commit -m "docs(language): exports, CONTEXT, README table"
```

---

### Task 7: Integration — resolution map, segmentation, year filter

**Files:**
- Create: `tests/integration/test_language_capability.py`

Research §8-9, §12: Full pipeline `MISSING`/`INVALID`/`SUCCESS` with `single_value=True` per grammar — two distinct mentions (`en, fr`) raise `MultipleMentionsError`, never `AMBIGUOUS` for disjoint clusters; `year` temporal filter; `VersionStamp` determinism; span invariants; underscore tolerance.

- [ ] **Step 7.1: Write the integration tests**

Create `tests/integration/test_language_capability.py`:

```python
import pytest
import paxman
from paxman.capabilities.Language.capability import LanguageCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution
from paxman.core.errors import MultipleMentionsError


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_registry()
    yield
    reset_registry()


def _register():
    register_capability(LanguageCapability())


@pytest.mark.integration
def test_bare_code_success():
    _register()
    r = paxman.canonicalize("en", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "en"


@pytest.mark.integration
def test_bcp47_case_canonicalization():
    _register()
    r = paxman.canonicalize("EN-us", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "en-US"


@pytest.mark.integration
def test_underscore_tolerance():
    _register()
    r = paxman.canonicalize("fr_FR", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "fr-FR"


@pytest.mark.integration
def test_display_name_success():
    _register()
    r = paxman.canonicalize("German", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "de"


@pytest.mark.integration
def test_grandfathered_preferred():
    _register()
    r = paxman.canonicalize("i-cherokee", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "chr"


@pytest.mark.integration
def test_deprecated_preferred():
    _register()
    r = paxman.canonicalize("iw", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "he"


@pytest.mark.integration
def test_collective_invalid_by_default():
    _register()
    r = paxman.canonicalize("aus", LanguageCapability.create_contract())
    assert r.status == Resolution.INVALID


@pytest.mark.integration
def test_collective_success_when_gated():
    _register()
    r = paxman.canonicalize(
        "aus", LanguageCapability.create_contract(include_collective=True)
    )
    assert r.status == Resolution.SUCCESS


@pytest.mark.integration
def test_variant_prefix_invalid():
    _register()
    r = paxman.canonicalize("de-nedis", LanguageCapability.create_contract())
    assert r.status == Resolution.INVALID
    r2 = paxman.canonicalize("sl-nedis", LanguageCapability.create_contract())
    assert r2.status == Resolution.SUCCESS and r2.canonicalized_value == "sl-nedis"


@pytest.mark.integration
def test_output_format_alpha2():
    _register()
    r = paxman.canonicalize(
        "eng", LanguageCapability.create_contract(output_format="alpha2")
    )
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "en"


@pytest.mark.integration
def test_output_format_alpha3():
    _register()
    r = paxman.canonicalize(
        "en", LanguageCapability.create_contract(output_format="alpha3")
    )
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "eng"


@pytest.mark.integration
def test_year_filter():
    _register()
    # BCP 47 rule is 2009, so year 2008 drops bcp47_tag but bare code still works via ISO rules
    r = paxman.canonicalize("en-US", LanguageCapability.create_contract(year=2008))
    assert r.status == Resolution.INVALID  # bcp47_tag rule excluded, no candidate


@pytest.mark.integration
def test_two_distinct_raise():
    _register()
    with pytest.raises(MultipleMentionsError):
        paxman.canonicalize("en, fr", LanguageCapability.create_contract())


@pytest.mark.integration
def test_identical_coalesce():
    _register()
    r = paxman.canonicalize("en en", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "en"


@pytest.mark.integration
def test_missing():
    _register()
    r = paxman.canonicalize("xx", LanguageCapability.create_contract())
    assert (
        r.status == Resolution.INVALID
    )  # 2-letter shape claimed, registry rejects → INVALID not MISSING
    r2 = paxman.canonicalize("!!!", LanguageCapability.create_contract())
    assert r2.status == Resolution.MISSING


@pytest.mark.integration
def test_script_region_canonical():
    _register()
    r = paxman.canonicalize("zh-Hans-CN", LanguageCapability.create_contract())
    assert r.status == Resolution.SUCCESS and r.canonicalized_value == "zh-Hans-CN"
```

- [ ] **Step 7.2: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_language_capability.py -v` → PASS (all 15). If `aus` passes without flag, fix `iso_639_5_ed2008.py` `requires_features={"include_collective"}` — without flag the rule is not run, so `aus` has no validating rule → `INVALID` as intended; with flag rule runs and validates `aus` via `ISO6395_COLLECTIONS`.

- [ ] **Step 7.3: Run coverage gates**

```bash
uv run pytest tests/capabilities/language/ tests/integration/test_language_capability.py -v
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/capabilities/Language/*" --fail-under=95
```

Expected: ≥95% on new package.

- [ ] **Step 7.4: Commit**

```bash
git add tests/integration/test_language_capability.py
git commit -m "test(language): integration resolution map, gating, output_format"
```

---

### Task 8: Property tests + Final Verification

**Files:**
- Create: `tests/property/test_language_property.py`

- [ ] **Step 8.1: Write property tests**

Create `tests/property/test_language_property.py`:

```python
from hypothesis import given, strategies as st
import paxman
from paxman.capabilities.Language.capability import LanguageCapability
from paxman.core.discovery import register_capability, reset_registry
from paxman.core.domain import Resolution

_VALID_LANGUAGES = st.sampled_from(["en", "de", "fr", "zh", "ja", "es", "ar"])


@given(lang=_VALID_LANGUAGES)
def test_bare_code_round_trip(lang: str):
    reset_registry()
    try:
        register_capability(LanguageCapability())
        r = paxman.canonicalize(lang, LanguageCapability.create_contract())
        assert r.status == Resolution.SUCCESS and r.canonicalized_value == lang
        r2 = paxman.canonicalize(lang.upper(), LanguageCapability.create_contract())
        assert r2.canonicalized_value == lang  # case fold
    finally:
        reset_registry()


@given(lang=_VALID_LANGUAGES)
def test_bcp47_region_round_trip(lang: str):
    tag = f"{lang}-US"
    reset_registry()
    try:
        register_capability(LanguageCapability())
        r = paxman.canonicalize(tag, LanguageCapability.create_contract())
        # only valid combos: some languages lack region but en/fr/de + US is valid per IANA region
        # just smoke: never raises, status in valid set
        assert r.status in (Resolution.SUCCESS, Resolution.INVALID)
    finally:
        reset_registry()


@given(st.sampled_from(["sl-nedis", "en-GB-oxendict", "zh-cmn", "zh-Hans-CN"]))
def test_variant_extlang_prefix_valid(tag: str):
    reset_registry()
    try:
        register_capability(LanguageCapability())
        r = paxman.canonicalize(tag, LanguageCapability.create_contract())
        assert r.status == Resolution.SUCCESS
    finally:
        reset_registry()
```

- [ ] **Step 8.2: Run property tests**

Run: `uv run pytest tests/property/test_language_property.py -q` → PASS.

- [ ] **Step 8.3: Full gate**

```bash
uv run ruff format paxman/ tests/
uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest -m "unit or capability or integration or e2e" -q
uv run pytest --cov=paxman --cov-report=term-missing --tb=short -q
uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95
```

Expected: 0 errors, 95% global.

- [ ] **Step 8.4: Remove anti-patterns**

```bash
grep -rn "type: ignore\|noqa\|pyright: ignore" paxman/capabilities/Language/ || echo "clean"
grep -rn "output_format" paxman/capabilities/Language/rules/ || echo "clean"
```

Expected: `clean` both.

- [ ] **Step 8.5: Manual smoke**

```bash
uv run python - << 'PY'
import paxman
from paxman.capabilities.Language.capability import LanguageCapability
paxman.register_capability(LanguageCapability())
for txt in ["en","ENG","German","fr_FR","EN-us","zh-Hans-CN","sl-nedis","i-cherokee","iw", "de-nedis", "zh-cmn", "en-Latn"]:
    r=paxman.canonicalize(txt, LanguageCapability.create_contract())
    print(txt, "->", r.canonicalized_value, r.status, f"span={r.span}")
    print(" alpha2:", paxman.canonicalize(txt, LanguageCapability.create_contract(output_format="alpha2")).canonicalized_value if r.status.name=="SUCCESS" else "—")
PY
```

- [ ] **Step 8.6: Push or hand off** — do not delete `docs/development/research/2026-08-23-language-canonicalization.md`; it already pins IANA File-Date rolling and variant prefix constraints.

---

## Self-Review Checklist

- [ ] All 8 tasks committed with `feat(language):` prefix, no `# type: ignore` in `paxman/`, no `output_format` in `rules/`, import-linter clean, pyright 0.
- [ ] `paxman/capabilities/Language/rules/data/*.py` are 11 plain frozensets/dicts sourced from IANA/ISO with header citation URLs + dates + File-Date; `grammar/data/*.py` keys derived from `rules/data` single source (no duplication).
- [ ] `normalize_name` is single source of truth for lexicon (grammar/data uses it, rules/data does not duplicate).
- [ ] `single_value=True` on all 3 grammars, engine `MultipleMentionsError` tested, `MISSING` vs `INVALID` split verified; underscore `fr_FR` span `(0,5)` `raw_text=="fr_FR"` `compact=="fr-FR"` invariant verified.
- [ ] Variant Prefix (`sl-nedis` vs `de-nedis`), extlang (`zh-cmn`), Suppress-Script (`en-Latn` still SUCCESS), grandfathered `i-cherokee→chr` preferred chain verified.
- [ ] `CONTEXT.md` 3-col table row added with full 7-authority provenance, `README.md` table regenerated, `MILESTONE.md` verified (no duplicate row).
- [ ] If `bootstrap._SHIPPED` decision was "not bootstrapped" (IBAN precedent), integration tests register per-test via `register_capability(LanguageCapability())` — suite remains order-independent; revisit bootstrap in follow-up PR.

