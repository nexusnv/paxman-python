# ISBN Canonicalization Research - paxman-alternative

**Date:** 2026-08-05
**Scope:** Primary-source survey of the ISBN standard (ISO 2108), the ISBN Range
Message, ecosystem canonicalization libraries, and Paxman's grammar/rule/
provenance architecture, to ground the design of an `ISBN` capability. No
source code, tests, or configuration were modified.
**Evidence basis:** Official standard pages (iso.org), the International ISBN
Agency (isbn-international.org, including a live fetch of the Range Message
XML), IANA URN registrations, and the source of established libraries
(`xlcnd/isbnlib`, `arthurdejong/python-stdnum`). Repo state: branch
`refactor/streamline-recognition` @ `49cf0f2` — grammars return span-bearing
`RecognitionMatch` objects and the engine owns per-grammar containment dedup and
total ordering (recognition-homogeneity refactor, per
`docs/superpowers/plans/2026-08-04-recognition-homogeneity.md`).

---

## Executive Summary

ISBN is an excellent fit for a Paxman capability: it has an unambiguous
canonical form (the 13-digit digit-only string), an authoritative standard
(ISO 2108:2017) with provenance-able clauses, a published machine-readable
registry (the ISBN Range Message) that maps directly onto Paxman's
`LOOKUP_TABLE` rule strategy, and a well-understood check-digit algorithm for
`PARSER` rules.

Key findings that shape the design:

1. **Canonical form is the 13-digit string.** Since 1 Jan 2007 only ISBN-13 is
   issued. ISO 2108:2017 §4.1 defines the human-readable display form (with
   `ISBN` prefix and hyphens) and the machine-readable form (bare digits); the
   IANA `urn:isbn` registration states ISBN-13 is the canonical equivalence
   form. Hyphens/spaces have **no lexical significance** — they are pure
   presentation. This maps perfectly onto Paxman's presentational-only
   `output_format` invariant: the hyphenated display form is a
   `Capability.format_value()` concern, never a rule concern.
2. **ISBN-10 is legacy but must still canonicalize.** ISBN-10 is deprecated
   (removed from ISO 2108:2017) but ubiquitous in the wild. Any ISBN-10
   converts losslessly to ISBN-13 (`978` + first 9 digits + recomputed mod-10
   check digit), so both shapes converge on one canonical value — a natural
   `SUCCESS` (never `AMBIGUOUS`), and a cross-shape containment property that
   makes the two grammars safe to run concurrently.
3. **Check digit is the definitive structural validation**; prefix
   (`978`/`979`) and Range Message registrant ranges are the stricter layers.
   The Range Message (a live XML from isbn-international.org) is the authority
   for registration group / registrant ranges and hyphenation. Following the
   Country capability's `rules/data/` pattern, an embedded snapshot of the
   range data keeps canonicalization deterministic and replay-safe (no runtime
   network fetch).
4. **Provenance is split across three authorities**: ISO 2108:2017 (structure,
   ISBN-13 check digit), the ISBN Users' Manual / withdrawn ISO 2108:2005
   (ISBN-10 mod-11 check digit), and the ISBN Range Message (registrant
   ranges). Each maps to one rule file with one `PUBLICATION`, matching the
   one-provenance-per-file convention.

Recommended file layout, rule set, notation, and contract are specified in
§7–§9. Open decisions (range-validation gating, whether the grammar bakes in
the `978`/`979` prefix) are flagged in §10 with a recommendation for each.

---

## 1. The ISBN Standard (ISO 2108)

### 1.1 The standard itself

| Field | Value |
|-------|-------|
| Standard | ISO 2108:2017, *Information and documentation — International Standard Book Number (ISBN)* |
| Edition | 5th (2017-12-15), confirmed 2023 |
| Maintainer | ISO/TC 46/SC 9 (Identification and description) |
| Registration Authority | International ISBN Agency Ltd |
| URL | <https://www.iso.org/standard/65483.html> |

Previous editions: ISO 2108:2005 (4th, withdrawn 2017-12-15), ISO 2108:1992
(3rd), ISO 2108:1978 (2nd).

**Critical fact:** ISO 2108:2017 specifies **13-digit ISBNs only**. The
10-digit format and its mod-11 check digit were **removed from the standard**;
they survive only in historical editions and the ISBN Users' Manual. Any rule
validating ISBN-10 must therefore cite a superseded/withdrawn provenance, not
ISO 2108:2017.

### 1.2 ISBN-13 structure

An ISBN-13 is 13 decimal digits in five elements (ISO 2108:2017 §4):

| Element | Length | Example (`978-0-306-40615-7`) |
|---------|--------|-------------------------------|
| GS1 prefix (EAN element) | 3 (fixed) | `978` |
| Registration group | 1–5 | `0` |
| Registrant (publisher) | up to 7 | `306` |
| Publication (title) | up to 6 | `40615` |
| Check digit | 1 | `7` |

Element lengths sum to 12; the check digit makes 13. The GS1 prefix is
currently `978` (all registration groups) or `979` (partial: 979-0 reserved
for ISMN; 979-8 US; 979-10 France; 979-11 South Korea; 979-12 Italy; 979-13
Spain).

### 1.3 ISBN-10 structure (legacy)

10 characters: registration group + registrant + publication + check digit.
The final character is 0–9 or `X` (= 10). Deprecated since 1 Jan 2007; no new
assignments; still encountered in legacy systems and existing collections.

### 1.4 The 2007 transition

- From 1 Jan 2007, national ISBN agencies issue **only** 13-digit ISBNs.
- Existing ISBN-10s convert to ISBN-13 by prefixing `978` and recomputing the
  mod-10 check digit; the conversion is *a new representation of the same
  ISBN*, not a new ISBN.
- `979` was introduced to extend capacity beyond `978`; ISBN-13s starting with
  `979` have **no ISBN-10 equivalent**.

Sources: <https://www.iso.org/news/2006/10/Ref1032.html>,
<https://www.loc.gov/catdir/cpso/13digit.html>,
<https://www.iana.org/assignments/urn-formal/isbn>.

---

## 2. Check Digit Algorithms

### 2.1 ISBN-13 — modulus 10 (weights 1, 3)

1. Multiply the first 12 digits alternately by 1, 3, 1, 3, … (left to right).
2. Sum the weighted products: `S = Σ (digit_i × weight_i)`.
3. Check digit = `(10 − (S mod 10)) mod 10`.

Verification: `(S + check) mod 10 == 0`.

Worked example — `978-0-11-000222-?`:
`9·1+7·3+8·1+0·3+1·1+1·3+0·1+0·3+0·1+2·3+2·1+2·3` = 9+21+8+0+1+3+0+0+0+6+2+6 = **56**;
`56 mod 10 = 6`; check = `(10−6) mod 10 = 4` → `978-0-11-000222-4`.

Sources: ISO 2108:2017 Annex C; ISBN Users' Manual (7th ed.) Appendix A1.1 —
<https://www.isbn-international.org/sites/default/files/ISBN%20Manual%202012%20-corr.pdf>.

### 2.2 ISBN-10 — modulus 11 (weights 10…2)

1. Multiply the first 9 digits by weights 10, 9, …, 2.
2. Sum the weighted products: `S = Σ (digit_i × (11 − i))` for i = 1..9.
3. Check digit = `(11 − (S mod 11)) mod 11`; if the result is 10 → `X`; if 11 → `0`.

Verification: `Σ (digit_i × (11 − i)) ≡ 0 (mod 11)` over all 10 characters.

Worked example — `0-306-40615-?`:
`0·10+3·9+0·8+6·7+4·6+0·5+6·4+1·3+5·2` = 0+27+0+42+24+0+24+3+10 = **130**;
`130 mod 11 = 9`; check = `(11−9) mod 11 = 2` → `0-306-40615-2`.

Sources: historical ISO 2108:2005 Annex C (withdrawn); cross-checked against
Wikipedia ISBN and MathWorld — <https://en.wikipedia.org/wiki/ISBN>,
<https://mathworld.wolfram.com/ISBN.html>.

### 2.3 What makes an ISBN "valid"?

The check digit algorithm is the **sole mathematical validation criterion**.
The International ISBN Agency ecosystem distinguishes:

- **valid ISBN** — built according to the rules (length, characters, check
  digit); and
- **issued ISBN** — actually allocated to a publisher by a national agency.

The Range Message XML is the authority that can distinguish issued-ness
(allocated registrant ranges) from mere structural validity. isbnlib states
this distinction explicitly
(<https://isbnlib.readthedocs.io/en/latest/>).

---

## 3. Canonical Form and Conversion

### 3.1 Canonical form = 13-digit digit-only string

- ISO 2108:2017 §4.1: in human-readable form the ISBN is preceded by `ISBN`
  and elements are hyphen-separated; hyphens/spaces "have no lexical
  significance and [are] purely to enhance readability."
- IANA `urn:isbn` registration: "Since ISBN-13 is the canonical form for ISBN,
  all equivalence checking should be performed using that format"; "Remove all
  hyphens from the NSSs" for the machine-readable form.
- Ecosystem norm: `isbnlib.canonical()` strips everything except digits/`X`.

**Paxman implication:** the default canonical value is the bare 13-digit
string (e.g. `9780306406157`). The hyphenated display form is presentation —
exactly what Paxman's `Capability.format_value()` seam exists for (see §7.5).

### 3.2 ISBN-10 → ISBN-13 (always possible)

1. Drop the ISBN-10 check digit.
2. Prepend `978` to the remaining 9 digits.
3. Recompute the mod-10 check digit (weights 1, 3) over the 12 digits.

Worked example — `0-8493-9640-9` → drop check → `084939640` → `978084939640`
→ weighted sum = 107, `107 mod 10 = 7`, check = `3` → `978-0-8493-9640-3`.

Source: IANA `urn:isbn`
(<https://www.iana.org/assignments/urn-formal/isbn>).

### 3.3 ISBN-13 → ISBN-10 (only for `978`-prefix)

Strip `978`, drop the mod-10 check digit, run mod-11 on the remaining 9
digits. `979`-prefix ISBNs have no ISBN-10 form. Since `output_format` must be
a well-defined transform for every value the capability can produce, **"isbn10"
should NOT be an offered output format** — it is undefined for `979` values.

---

## 4. The ISBN Range Message (hyphenation + issued-ness)

### 4.1 What it is

A machine-readable XML file published by the International ISBN Agency defining
every allocated registration group and registrant range, per GS1 prefix. It is
the authority for hyphen placement and for issued-ISBN validation.

- Page: <https://www.isbn-international.org/range_file_generation>
- Live XML: <https://www.isbn-international.org/export_rangemessage.xml>
  (fetched 2026-08-05; `MessageSerialNumber` 6f6063f3-6f2a-4619-8bd9-116a3addc690,
  `MessageDate` "Wed, 5 Aug 2026 08:25:28 BST")

### 4.2 XML structure (two sections)

```xml
<EAN.UCCPrefixes>
  <EAN.UCC>
    <Prefix>978</Prefix>
    <Agency>International ISBN Agency</Agency>
    <Rules>
      <Rule><Range>0000000-5999999</Range><Length>1</Length></Rule>
      <Rule><Range>6000000-6499999</Range><Length>3</Length></Rule>
      <!-- ... -->
    </Rules>
  </EAN.UCC>
</EAN.UCCPrefixes>
<RegistrationGroups>
  <Group>
    <Prefix>978-0</Prefix>
    <Agency>English language</Agency>
    <Rules>
      <Rule><Range>0000000-1999999</Range><Length>2</Length></Rule>
      <Rule><Range>2000000-2279999</Range><Length>3</Length></Rule>
      <!-- ... -->
    </Rules>
  </Group>
</RegistrationGroups>
```

- Ranges are zero-padded (7 digits for both prefix and registrant rules).
- `Length` is the number of digits of the element; `Length 0` = range not
  allocated.
- The `<Group><Prefix>` is `EAN.UCC prefix + registration group` (e.g. `978-0`).

### 4.3 The hyphenation algorithm (longest-match, two steps)

Given a 13-digit ISBN:

1. **Registration group length.** For the GS1 prefix (first 3 digits), walk the
   prefix's rules; take the N-digit prefix of the remaining digits where N =
   the rule's `<Length>`, and test it against the rule's `<Range>`. First
   match fixes the group length.
2. **Registrant length.** Look up `<Group><Prefix>` = `978-{group}`; walk its
   rules the same way, testing M-digit prefixes against registrant ranges.
   First match fixes the registrant length.
3. **Split.** `{prefix}-{group}-{registrant}-{publication}-{check}`; the
   publication element length is `13 − 3 − len(group) − len(registrant) − 1`.

This is the algorithm behind isbnlib's `mask()` and the `hornc/isbn_hyphenate`
and BookWyrm `IsbnHyphenator` implementations.

### 4.4 isbnlib implementation (`xlcnd/isbnlib`)

- `isbnlib/_msk.py` — `msk()` hyphenation engine; embeds the range data as a
  Python dict literal (`_data/data4mask.py`, keys like `'978-0'`, values of
  `(start, end, registrant_length)` tuples) auto-generated from the
  RangeMessage.xml; a sliding window extends the group prefix one digit at a
  time until a key matches.
- `isbnlib/_core.py` — `canonical()`, `EAN13()`, `to_isbn10()`, `to_isbn13()`,
  check-digit validation.
- Known weakness: the embedded data goes stale when the live XML updates
  (isbnlib issues #143, #148; last regen 2023-07-28). For Paxman, embed the
  snapshot with its `MessageDate` in the provenance (like Country's CLDR
  `ed2025` convention) and document the refresh procedure.

---

## 5. Ecosystem Norms (evidence for design choices)

| Library | Canonical form | Hyphenation | Conversion | Notes |
|---------|---------------|-------------|------------|-------|
| isbnlib (Python) | `canonical()` → digit-only string | `mask()` per range data | `to_isbn10/13()` | Dominant Python library; valid vs issued distinction |
| python-stdnum (Python) | `compact()` → `validate()` → `format()` | via range data | internal | Already cited in `docs/report/recognition-handling-library-research.md` as the clean-pipeline reference; its `isbn` module uses `InvalidChecksum` exceptions — **do not** adopt exception-based validation in Paxman |
| go-isbn (Go), isbn3 (JS), PostgreSQL `isn` | digit strings | range-message data | 978-only reverse | Same canonical-form consensus |

Consensus: **canonical = bare digits; hyphens = presentation**; ISBN-10→13
always, ISBN-13→10 only for `978`. Paxman's design should match this consensus
so results interoperate with the ecosystem.

---

## 6. Current Paxman Architecture (grounding for the mapping)

Verified against `refactor/streamline-recognition` @ `49cf0f2`:

- **Grammar** (`paxman/core/domain.py`): `recognize(self, text) ->
  list[RecognitionMatch[NotationT]]`; `RecognitionMatch` carries
  `notation`, half-open `[start, end)`, `raw_text` (invariant
  `len(raw_text) == end - start`).
- **Engine** (`paxman/engine/orchestrator.py`): filters grammars by
  `contract.active_grammars`; validates span invariants; per-grammar
  containment dedup (longer wins, ties keep first); total order
  `(start, end, grammar_index, grammar_name)`; cross-grammar overlaps
  preserved (ambiguity observable). Rules filtered by `pinned_rules` /
  `excluded_rules` / `year` / `requires_features`, then routed per
  `Rule.target_grammars`; `Capability.format_value()` called after
  `normalize()`; candidates deduped by `(value, recognition_rule,
  validation_rule)`; status = `MISSING`/`INVALID`/`SUCCESS`/`AMBIGUOUS`;
  SHA-256 replay hash over input + contract + status + candidates.
- **Rule** (`Rule[NotationT]`): six enforced class attributes — `name`,
  `strategy` (`REGEX`/`LOOKUP_TABLE`/`PARSER`), `provenance`, `citation`,
  `target_grammars`, `requires_features`; abstract `matches()`,
  `normalize()`; rules never read `output_format` (CI-enforced).
- **Provenance**: `authority`, `specification_name`, `kind`
  (`specification`/`registry`/`policy`), `reference_url`, `version`,
  `lifecycle` (`active`/`deprecated`/`superseded`), `publication_year`.
- **Capability contract** (`CapabilityContract` base): `DEFAULT_OUTPUT_FORMAT`
  + `OFFERED_OUTPUT_FORMATS` class vars; `capability_name` via
  `field(default=..., init=False)`; inherited `output_format` (resolved to a
  concrete string); `active_grammars` property; `_extra_dict_fields()` for
  replay-hash serialization.
- **Conventions**: rule files `{spec}_ed{year}.py` with one module-level
  `PUBLICATION`; grammar files `{format}_recognition.py`; rule names
  `Section {ref}-{description}`; large lookup tables in `rules/data/`
  (Country `iso_3166_ed2024.py` is the model — `frozenset`/`dict` constants,
  a `shape` discriminator on the notation).

---

## 7. Proposed ISBN Capability Design

### 7.1 Notation

Follow the Country `shape` + `value` discriminator pattern — the two ISBN
shapes share one notation type and differ only in shape:

```python
@dataclass(frozen=True, slots=True)
class ISBNNotation:
    shape: str  # "isbn10" | "isbn13"
    digits: str  # digit string; "X" allowed only as the final
    # char of an "isbn10" shape

    def as_list(self) -> list[str]:
        return [self.shape, self.digits]
```

The grammar normalizes syntax only (strips hyphens/spaces/`ISBN` label, folds
`x` → `X`); it never computes or validates the check digit — that is the
rules' job (grammar/rule boundary, per HOW_TO_ADD_NEW_CAPABILITY.md).

### 7.2 Grammars

Two grammars, both returning span-bearing `RecognitionMatch[ISBNNotation]`:

| Grammar | `name` | Recognizes | Notes |
|---------|--------|-----------|-------|
| ISBN-13 | `isbn13_recognition` | 13-digit runs, optional separators, optional `ISBN`/`ISBN-13` label | Digit-count discriminator: exactly 13 digits → `shape="isbn13"` |
| ISBN-10 | `isbn10_recognition` | 10-character runs (0–9, final may be `X`), optional separators, optional `ISBN`/`ISBN-10` label | Exactly 10 chars → `shape="isbn10"` |

**Design decision — prefix in grammar or rule?** Recommend the grammar
recognizes any 13-digit run and the **rule** enforces prefix ∈ {`978`, `979`}
(provenance-backed by ISO 2108 §4.2). This keeps recognition purely syntactic
and lets a 13-digit EAN that is not an ISBN surface as `INVALID` (recognized,
no authority validates) rather than `MISSING` — consistent with how Email
recognizes `@localhost` and the rule validates it. (Alternative — baking the
prefix into the grammar — is discussed in §10.)

**Containment property (why two grammars are safe together):** an ISBN-10
match can be contained inside an ISBN-13 match's span (e.g. the trailing 10
digits of `978-0-306-40615-7`). The engine preserves cross-grammar overlaps,
so both candidates would be produced — but both `normalize()` to the **same**
13-digit canonical value, so the result is `SUCCESS`, never `AMBIGUOUS`. In
the common case the trailing 10 digits fail the mod-11 check anyway, so only
the ISBN-13 candidate survives. This convergence is the core argument for a
13-digit canonical form.

### 7.3 Rules and provenance

Three rule files, one publication each:

**`rules/iso_2108_ed2017.py`** — `PUBLICATION = Provenance(
authority="ISO", specification_name="ISO 2108:2017", kind="specification",
reference_url="https://www.iso.org/standard/65483.html", version="2017",
lifecycle="active", publication_year=2017)`

| Rule | `name` | Strategy | Validates |
|------|--------|----------|-----------|
| ISBN-13 check digit | `Section 5.3-isbn13-check-digit` | `PARSER` | mod-10 over `shape="isbn13"` digits; `target_grammars={"isbn13_recognition"}` |
| GS1 prefix | `Section 4.2-gs1-prefix` | `LOOKUP_TABLE` | `digits[:3] ∈ {"978", "979"}`; same target |

**`rules/isbn_users_manual_ed2012.py`** — `PUBLICATION = Provenance(
authority="International ISBN Agency", specification_name="ISBN Users' Manual",
kind="specification",
reference_url="https://www.isbn-international.org/sites/default/files/ISBN%20Manual%202012%20-corr.pdf",
version="2012", lifecycle="superseded", publication_year=2012)` — lifecycle
`superseded` because ISBN-10 was removed from the current standard; the
publication_year 2012 keeps the rule active under `year >= 2012` filters.

| Rule | `name` | Strategy | Validates |
|------|--------|----------|-----------|
| ISBN-10 check digit | `Section 6-isbn10-check-digit` | `PARSER` | mod-11 over `shape="isbn10"` chars, `X` = 10; `target_grammars={"isbn10_recognition"}` |

**`rules/isbn_range_message_ed2026.py`** — `PUBLICATION = Provenance(
authority="International ISBN Agency", specification_name="ISBN Range Message",
kind="registry", reference_url="https://www.isbn-international.org/range_file_generation",
version="2026-08-05", lifecycle="active", publication_year=2026)`; lookup data
in `rules/data/range_message.py` (embedded snapshot of the EAN.UCC and
registrant ranges, mirroring isbnlib's `data4mask.py` structure).

| Rule | `name` | Strategy | Validates |
|------|--------|----------|-----------|
| Registrant range | `Section 4-registrant-range` | `LOOKUP_TABLE` | group/registrant falls within an allocated range (issued-ness); `target_grammars` both |

**Normalization** (all rules converge): return the 13-digit canonical string —
for `isbn10` shape, `978` + `digits[:9]` + recomputed mod-10 check digit; for
`isbn13` shape, the digits unchanged. Rules never read `output_format`; the
hyphenated display form lives in the capability (below).

### 7.4 Contract

```python
@dataclass(frozen=True)
class ISBNContract(CapabilityContract):
    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "isbn13"  # bare 13 digits
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"hyphenated"})

    capability_name: str = field(default="isbn", init=False)
    include_isbn10: bool = True  # legacy input recognition
    include_range_validation: bool = False  # gates the Range Message rule

    @property
    def active_grammars(self) -> list[str]:
        grammars = ["isbn13_recognition"]
        if self.include_isbn10:
            grammars.append("isbn10_recognition")
        return grammars

    def _extra_dict_fields(self) -> dict[str, object]:
        return {
            "include_isbn10": self.include_isbn10,
            "include_range_validation": self.include_range_validation,
        }
```

- `include_isbn10` toggles the legacy grammar (input-shape feature → disabled
  yields `MISSING` for ISBN-10-only input), parallel to Email's
  `include_localhost`.
- `include_range_validation` gates the Range Message rule via
  `requires_features` (authority feature → disabled yields `INVALID` for
  recognized-but-unallocated digits), parallel to Country's
  `include_localized`. Default off: a check-digit-valid ISBN in an
  unallocated range is still "valid per the rules" — issued-ness is a
  stricter claim the caller opts into.

### 7.5 Capability and the presentation seam

`ISBNCapability(Capability[ISBNNotation])`, `name="isbn"`, `version="1.0.0"`;
`get_grammars()` and `get_rules()` as above; `format_value()` implements the
one offered alternative:

```python
def format_value(
    self, value: str, output_format: str | None, notation: ISBNNotation
) -> str:
    if output_format == "hyphenated":
        return hyphenate(value)  # Range Message longest-match, §4.3
    return value  # "isbn13" default is identity
```

This is a textbook presentational-only transform: it never changes candidate
identity (two hyphenations of the same digits are the same canonical value),
adds no provenance, and cannot affect status.

### 7.6 Resolution-state map

| Input | Status | Why |
|-------|--------|-----|
| Valid ISBN-13 (check digit OK, prefix 978/979) | `SUCCESS` → `978…` digits | single canonical value |
| Valid ISBN-10 | `SUCCESS` → converted `978…` digits | canonical form is ISBN-13 |
| ISBN-10 + its ISBN-13 equivalent in one input | `SUCCESS` | both normalize to the same digits |
| ISBN-10 match contained in an ISBN-13 match | `SUCCESS` | cross-grammar candidates converge (§7.2) |
| 13 digits, check digit OK, prefix ∉ {978, 979} | `INVALID` | recognized EAN-13, no ISBN authority validates |
| Check digit fails | `INVALID` | definitive structural failure |
| 10 digits with bad mod-11 check | `INVALID` | — |
| Other digit counts (9, 11, 12, 14…) | `INVALID` or `MISSING` depending on grammar scope | 13-digit grammar may match sub-runs; rules reject |
| Text with no digit runs | `MISSING` | — |

---

## 8. Ambiguity Analysis (Paxman-specific)

- **No inherent ISBN ambiguity.** ISBNs are unique by design; the check digit
  eliminates the parsing ambiguity that dates (DD/MM vs MM/DD) exhibit.
- **The two shapes converge**, so the engine's `AMBIGUOUS` fires only for
  genuinely different books (e.g. two ISBNs in one input) — the same semantic
  as multiple emails in one text.
- **Hyphenation is never an ambiguity signal.** Differently-hyphenated forms
  of the same digits must canonicalize identically. The range-message
  hyphenation rule must therefore **not** reject input whose hyphens are in
  non-canonical positions — hyphens carry no lexical significance (ISO 2108
  §4.1), and enforcing placement would turn presentation into validity.

---

## 9. Test Strategy (mirroring HOW_TO_ADD_NEW_CAPABILITY.md)

- **Grammar tests** (`tests/capabilities/isbn/test_grammar.py`): each grammar —
  valid input, variants (separators, `ISBN` label, `x` vs `X`), multiple
  matches, incompatible format, empty input; span invariants
  (`len(raw_text) == end - start`).
- **Rule tests** (`test_rules.py`): per-rule `matches()` valid/variant/
  invalid, `normalize()` canonical output (incl. ISBN-10→13 conversion),
  provenance attributes, name/strategy conventions.
- **Capability tests** (`test_capability.py`): notation frozen/hashable/
  `as_list`; wiring counts; grammar/rule name conventions.
- **Integration** (`tests/integration/test_pipeline.py`): SUCCESS / MISSING /
  INVALID / AMBIGUOUS; version-stamp determinism; `_clean_registry` fixture.
- **Property tests** (hypothesis): generate valid ISBN-13s from the algorithm
  → canonicalize round-trips; random 13-digit strings → INVALID with high
  probability; ISBN-10→13→10 round-trip for `978` prefixes; hyphenated vs
  bare input → identical canonical value (replay hashes differ — the hash
  covers the original input, so separators are not normalized away).
- **Consistency test** (grammar/rule boundary): every recognition shape is
  covered by at least one rule's `target_grammars`; range-message data covers
  the shipped prefixes.
- **Presentation purity**: the CI `output_format` source scan already applies
  to any new `rules/` module.

---

## 10. Open Decisions (with recommendations)

1. **Prefix in grammar vs rule** — recommend **rule** (`Section 4.2-gs1-prefix`,
   `LOOKUP_TABLE`): keeps recognition syntactic, yields `INVALID` (not
   `MISSING`) for non-ISBN EAN-13s, provenance stays in rules.
2. **Range-validation default** — recommend **opt-in** (`include_range_validation=False`,
   `requires_features` gating): issued-ness is a stricter authority claim;
   mirrors Country's `include_localized`/`include_historical`.
3. **Range Message data freshness** — embed a snapshot with the `MessageDate`
   in the provenance and a documented refresh procedure; never fetch at
   runtime (replay-safety). Publication-year convention: year of the snapshot
   (2026), like Country's `ed2025` CLDR rule.
4. **`"hyphenated"` as the only offered format** — do **not** offer `"isbn10"`;
   it is undefined for `979` values and would violate the well-defined-
   transform requirement.
5. **ISBN-10 rule lifecycle** — `superseded` (not `deprecated`): the format is
   deprecated, but the rule remains the authority for legacy input the
   capability must still canonicalize. Year filtering still applies
   (`year >= 2012` keeps it active).

---

## 11. URL Reference

| Claim | URL |
|-------|-----|
| ISO 2108:2017 (ISO page) | <https://www.iso.org/standard/65483.html> |
| ISO 2108:2017 sample (structure, §4) | <https://cdn.standards.iteh.ai/samples/iso/iso-2108-2017/bfb5ebe9e04b46aaa89549124ece5dd0/iso-2108-2017.pdf> |
| ISO 2108:2005 sample (ISBN-10, withdrawn) | <https://cdn.standards.iteh.ai/samples/36563/9165030b96a143a49da0502ab462a292/ISO-2108-2005.pdf> |
| ISBN Users' Manual (7th ed. / 2012 PDF) | <https://www.isbn-international.org/sites/default/files/ISBN%20Manual%202012%20-corr.pdf> |
| "What is an ISBN?" (IIA) | <https://www.isbn-international.org/content/what-isbn/10> |
| 2007 transition (ISO news) | <https://www.iso.org/news/2006/10/Ref1032.html> |
| Library of Congress 13-digit plan | <https://www.loc.gov/catdir/cpso/13digit.html> |
| IANA urn:isbn registration | <https://www.iana.org/assignments/urn-formal/isbn> |
| Range File Generation page | <https://www.isbn-international.org/range_file_generation> |
| Range Message XML (live) | <https://www.isbn-international.org/export_rangemessage.xml> |
| ISBN Calculator (conversion tool) | <https://www.isbn-international.org/content/isbn-calculator> |
| isbnlib (PyPI) | <https://pypi.org/project/isbnlib/> |
| isbnlib (GitHub, `_msk.py`, `_data/data4mask.py`) | <https://github.com/xlcnd/isbnlib> |
| isbnlib docs (valid vs issued) | <https://isbnlib.readthedocs.io/en/latest/> |
| python-stdnum (GitHub, `isbn` module) | <https://github.com/arthurdejong/python-stdnum> |
| go-isbn (Go) | <https://github.com/mstrucken/go-isbn> |
| isbn3 (JavaScript) | <https://github.com/inventaire/isbn3> |
| ISBN ranges (Ruby gem) | <https://github.com/takatoh/ISBNRanges> |
| Wikipedia ISBN (algorithm cross-check) | <https://en.wikipedia.org/wiki/ISBN> |
| MathWorld ISBN | <https://mathworld.wolfram.com/ISBN.html> |
| GS1 ISBN barcode FAQ | <https://support.gs1.org/support/solutions/articles/43000734165-how-is-an-isbn-used-in-a-gs1-barcode-> |
