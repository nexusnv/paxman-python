# Plan: Domain / IDN Capability (canonicalize hostname mentions to an A-label FQDN)

> **For workers:** Execute task-by-task via `tdd` + `verification-before-completion`. This plan
> and the research report it derives from live in `docs/development/` and are never referenced by
> any code, test, docstring, comment, or shipped document — see the **Hard fixture rule** below.

**Goal:** Ship `domain`, capability 27 of 27 (MILESTONE row 1 — D9 delay cleared): one ambiguity
decision (§9 R1–R8) per human hostname mention — mixed-case, root-dot, Unicode U-label, ACE
A-label, fullwidth/dot-variant, NFD, space/hyphen-broken, free-text-embedded — canonicalized to a
lowercase ASCII A-label FQDN with no trailing dot, plus an offered `unicode` U-label rendering.
Validated against RFC 1034 §3.1, RFC 1035 §2.3.1/§2.3.4, RFC 1123 §2.1, RFC 3492, RFC 5890/5891,
RFC 5893 §2, UTS #46 (spec v18.0.0; **shipped table 15.1.0** — see deviation D-a), STD3 rules on,
non-transitional processing pinned, and the single registry LOOKUP
`iana_root_zone_membership` over the IANA `tlds-alpha` snapshot (v2026092300, 1,438 entries) as
the ADR-0012 non-vacuous candidate-qualification chokepoint: when it fails there is no LOOKUP, all
PARSER candidates are dropped, the qualified set is empty, and status is INVALID — never a
SUCCESS without registry corroboration.

**Architecture:** Existing capabilities' pipeline pattern (BCP47/URL/Country exemplar), zero
changes to `paxman/core` or `paxman/engine`. Two `PipelineGrammar`s —
`ascii_hostname` + `idn_hostname` — scan/match/boundary over the original text with an identity
view; each match's emit calls shared `idna_processing.map_domain()` (casefold-via-table mapping,
NFC, dot-mapping, one trailing-dot strip) to build a span-bearing
`DomainNotation(raw, labels, tld)` (frozen+slots, **no `canonical` field** — canonical is built by
`finalize()` inside every `normalize()`: encode-in-resolution, §4.5). Five publications, one file
each: `Rfc1034NameSyntax` (≥2 labels, no empty label — single-label scope is contract-commented
deferred D6), `Rfc1035LabelLength` (63 octets/label post-ACE, 253 chars/name), 
`UnicodeUts46Statuses` (ALL hyphen checks — D13 `CheckHyphens=true`, STD3, ACE round-trip — plus
the status table), `Rfc5893BidiContext` (RFC 5893 §2 six conditions with non-Bidi fast path +
ContextJ join-control rejection), and `IanaRootZoneMembership` (the only
`RuleStrategy.LOOKUP_TABLE`, `kind="registry"`), whose predicate ANDs the four public rule
predicates + encoded-TLD membership — one chokepoint, no cross-capability imports (predicates are
intra-capability; import-linter bans only cross-capability). `DomainCapability.format_value()`:
`ascii` identity, `unicode` decodes each `xn--` label via the stdlib `"punycode"` codec (never
raises — decode failure leaves the label unchanged). Contract:
`DEFAULT_OUTPUT_FORMAT="ascii"`, `OFFERED_OUTPUT_FORMATS=frozenset({"unicode"})`,
`capability_name="domain"`. Two generators snapshot the shipped tables (one UTS #46 text in-tree,
shared with URL = G8 closed). Counts move 26→27 across exactly seven pinned surfaces (mid-plan red
until Task 12).

**Tech Stack:** Python 3.11+, `unicodedata` (NFC + bidi classes — stdlib, no new data module),
stdlib `"punycode"` codec, uv + hatchling, pytest (marker `capability`), hypothesis `ci` profile,
ruff / strict pyright / import-linter / coverage `--fail-under=95`.

**References:** `docs/development/research/2026-09-24-domain-name-canonicalization.md` (this
plan's input — W-table :55-79, E-table :489-512, §4.2 patterns :195-215, §4.4 boundary/freespan
:226-243, §5.2 rule map :279-303, §6.1 contract :346-364, §7.2/§7.3 chokepoint algorithm
:440-466, §9 resolution R1–R8 :514-523, §11 tree :566-610, §13 D-table :641-712, §15 G-table
:714-745); `paxman/engine/orchestrator.py:116-175` (candidate ordering), `:625` (invariant —
qualified candidates only), `:750-783` (`_require_lookup_corroboration`), `:882-889`
(`_determine_status`); `paxman/core/domain.py:243-244,274,279,295` (Rule ABC); 
`paxman/core/grammar/boundary_spec.py:259-260`; `tools/new_capability.py:53-235,679,706-738`;
`paxman/capabilities/URL/rules/data/idna_uts46_mapping.txt` (shipped 15.1.0 table — the 
Domain generator's SNAPSHOT); `tests/property/test_reentry_invariant.py:98,145,238`;
`tests/property/test_output_format_preservation.py:155-160,239,322-324`;
`tests/unit/test_offered_format_class_declarations.py:61-95,100-140`;
`paxman/api/bootstrap.py:41-68`; `paxman/cli.py:163-167`;
`paxman/capabilities/__init__.py:23,58,93`; `benchmarks/scenarios.py:10,21,203-215`;
RFC 1034/1035/1123/3492/5890/5891/5893 (5893 §2 "The Bidi Rule" — six conditions verified
first-hand) + UTS #46 + IANA tlds-alpha v2026092300.

**Branch:** `feature/domain-idn-capability` from `dev`.

---

## File Structure

**Created:**

| Path | Task |
|---|---|
| `paxman/capabilities/Domain/__init__.py` | T1 scaffold |
| `paxman/capabilities/Domain/notation.py` | T1 scaffold → rewrite |
| `paxman/capabilities/Domain/contract.py` | T1 scaffold → T2 rewrite |
| `paxman/capabilities/Domain/capability.py` | T1 scaffold → T9 fill |
| `paxman/capabilities/Domain/idna_processing.py` | T3 |
| `paxman/capabilities/Domain/grammar/__init__.py` | T1 scaffold |
| `paxman/capabilities/Domain/grammar/ascii_hostname.py` | T1 scaffold (renamed) → T4 fill |
| `paxman/capabilities/Domain/grammar/idn_hostname.py` | T5 |
| `paxman/capabilities/Domain/grammar/data/__init__.py` | T3 |
| `paxman/capabilities/Domain/grammar/data/idna_mapping.py` | T3 generated |
| `paxman/capabilities/Domain/rules/__init__.py` | T1 scaffold |
| `paxman/capabilities/Domain/rules/rfc_1034_name_syntax.py` | T1 scaffold (renamed) → T6 fill |
| `paxman/capabilities/Domain/rules/rfc_1035_label_length.py` | T6 |
| `paxman/capabilities/Domain/rules/unicode_uts46_statuses.py` | T7 |
| `paxman/capabilities/Domain/rules/rfc_5893_bidi_context.py` | T7 |
| `paxman/capabilities/Domain/rules/iana_root_zone_membership.py` | T8 |
| `paxman/capabilities/Domain/rules/data/__init__.py` | T3 |
| `paxman/capabilities/Domain/rules/data/root_zone_tlds.py` | T3 generated |
| `paxman/shared_data/root_zone_snapshot.json` | T3 generated |
| `tools/regenerate_domain_idna_data.py` | T3 |
| `tools/regenerate_root_zone_tld_data.py` | T3 |
| `tests/capabilities/domain/__init__.py` | T1 scaffold |
| `tests/capabilities/domain/test_notation.py` | T1 scaffold → rewrite |
| `tests/capabilities/domain/test_contract.py` | T2 |
| `tests/capabilities/domain/test_grammar.py` | T1 scaffold → T4/T5 fill |
| `tests/capabilities/domain/test_rules.py` | T1 scaffold → T3 fill |
| `tests/capabilities/domain/test_rfc_1034_name_syntax.py` | T6 |
| `tests/capabilities/domain/test_rfc_1035_label_length.py` | T6 |
| `tests/capabilities/domain/test_unicode_uts46_statuses.py` | T7 |
| `tests/capabilities/domain/test_rfc_5893_bidi_context.py` | T7 |
| `tests/capabilities/domain/test_iana_root_zone_membership.py` | T8 |
| `tests/capabilities/domain/test_data.py` | T3 (carries `pytestmark = pytest.mark.capability`) |
| `tests/capabilities/domain/test_capability.py` | T1 scaffold → T9 fill |
| `tests/capabilities/domain/test_capability_wild_variants.py` | T10 |
| `tests/integration/test_domain_idna_parity.py` | T10 |
| `docs/user/capabilities/domain.md` | T12 |

**Modified:**

| Path | Task |
|---|---|
| `paxman/capabilities/__init__.py` | T9 (scaffolder-wired; verify) |
| `paxman/api/bootstrap.py` | T9 (`_SHIPPED` entry between DOI :49 and Email :50) |
| `paxman/cli.py` | T9 (dispatch branch after doi :166, before chemical_element :167) |
| `tests/unit/test_capability_surface.py` | T9 (scaffolder-wired param `id="domain"` — verify) |
| `tests/unit/test_cli.py` | T9 (`test_cli_domain_dispatch`) |
| `tests/property/test_reentry_invariant.py` | T11 (rows after DOI :145; import between :69/:70; A0 test appended at end of file, :418) |
| `tests/property/test_output_format_preservation.py` | T11 (CLASS_MAP section after DOI :159; import after :80; first pair before :324) |
| `tests/unit/test_api_coverage_fix.py` | T12 (`==26`→`==27` at :31) |
| `tests/unit/test_capability_lazy_import.py` | T12 (:56 word, :67/:68 entry) |
| `tests/unit/test_capability_exports.py` | T12 (:283 entry) |
| `tests/unit/test_offered_format_class_declarations.py` | T12 (class list after Date :46; factory after "doi" :68) |
| `tests/unit/test_bootstrap.py` | T12 ("domain" after "doi" :37; `==25`→`==26` at :74) |
| `benchmarks/scenarios.py` | T12 (helpers after :21; row between date :215 and email) |
| `README.md` | T12 (:69 row; regenerate table) |
| `CONTEXT.md` | T12 (:76, :832, :1041) |
| `ARCHITECTURE.md` | T12 (:83) |
| `AGENTS.md` | T12 (:8, :50, :104, :105) |
| `paxman/capabilities/AGENTS.md` | T12 (:4, :67) |
| `tests/AGENTS.md` | T12 (:4) |
| `CHANGELOG.md` | T12 ([Unreleased] :8) |
| `docs/user/capabilities-index.md` + unversioned `docs/user/*` site rows | T12 (guide + chooser + index/getting-started/concepts/api-reference/citations/glossary/migration rows wherever `lei`/`gtin` appear; **never `docs/user/v0.x/`**) |

---

## Background the implementer needs

#### Hard fixture rule (binding on every task)

Every test in this plan uses **inline literals only** — never a file fixture, never a read of
anything under `docs/development/`. No code file, test, docstring, comment, or shipped document
created or edited by this plan may name or paraphrase any `docs/development/` file. RFC/IANA/UTS
citations and ADR numbers are the only external references permitted in code. This plan and the
research report may reference each other freely (both are non-shipping).

#### Current state

`Domain` does not exist: no `paxman/capabilities/Domain/`, no `tests/capabilities/domain/` (probed
absent), no bootstrap/CLI/export surface. `test_capability_surface.py` has no `domain` param.
The shipped UTS #46 table (15.1.0) lives at
`paxman/capabilities/URL/rules/data/idna_uts46_mapping.{txt,py}` — one table text in-tree (G8).

#### Locked decisions (each verified first-hand against source)

1. **Notation (deliberate deviation from report §3.1):** `DomainNotation(raw, labels, tld)` —
   `raw` = span text verbatim (original case, original trailing dot); `labels` = mapped tuple
   (table mapping applied, NFC, ONE trailing empty label stripped); `tld` = `labels[-1]`.
   Frozen + slots; **no `canonical` field** — canonical is produced by shared `finalize()` called
   inside each `normalize()`. Test asserts `"canonical" not in DomainNotation.__dataclass_fields__`.
2. **Scan — Design I:** matcher reads original text with `view=None` (the identity/original-text
   view — `paxman/capabilities/Country/grammar/alpha2_recognition.py:28` exemplar);
   recognition-layer normalization (table mapping, NFC) happens at emit via
   `map_domain()`, NOT as a kernel normalizer. Punycode encoding occurs only in rules.
3. **Patterns (final):** `_LABEL = r"[A-Za-z0-9-]+"`, `_LABEL0 = r"[A-Za-z0-9-]*"`,
   `_FQDN = rf"{_LABEL}(?:\.{_LABEL0})*\.*"` — trailing `\.*` (NOT `\.?`; `\.*` is what makes
   `example.com..` one span → INVALID instead of a sub-span carve → MISSING).
   IDN: `_IDN_LABEL = r"[^\s.@:/\\?#\[\]%*;,]+"`, `_IDN_LABEL0 = rf"{_IDN_LABEL}*"`,
   `_IDN_FQDN = rf"{_IDN_LABEL}(?:\.{_IDN_LABEL0})*\.*"`. ASCII grammar also accepts uppercase
   (case is recognition-neutral). **No ≥1-non-ASCII predicate in the idn grammar** (§4.3 overlap is
   resolved by same-span dedup, not by predicate).
4. **Boundary:** module `_ASCII_KILL = ("\\w","\\.","\\*","@",":","/","\\\\","?","#","\\[","\\]","%","[^\\x00-\x7F]")`
   on both `BoundarySpec.left`/`.right`; idn tuple = the same 13 minus the non-ASCII class (12
   elements). Kills W14–W16, `nchen.de` sub-carve, NFD `mu\u0308nchen.de` sub-carve (leading
   combining mark caught by `\w`), `[::1]` → no span → MISSING.
5. **Ownership:** `unicode_uts46_statuses` owns ALL hyphen checks (D13 `--`@idx2-3 w/o `xn--`
   prefix; leading `-`; trailing `-`; STD3 underscore; ACE round-trip E6) + the status check
   (allowed = `{"valid","deviation"}` — everything else, incl. `disallowed_STD3_valid`, rejects;
   STD3 rules ON = D7). Its public predicate `uts46_ok = ACE ∧ statuses ∧ hyphens`.
   `rfc_1035_label_length` owns post-encode lengths (`MAX_LABEL_OCTETS=63`,
   `MAX_NAME_CHARS=253` over `finalize()`-style joined name) → `label_lengths_ok`.
   `rfc_1034_name_syntax` owns ≥2 labels + no empty label only → `name_syntax_ok`.
   `rfc_5893_bidi_context` owns RFC 5893 §2 (six conditions, typed by FIRST char; non-Bidi fast
   path returns True — no label contains a char with bidi class R/AL/AN per §1.4; NSM-trailing
   strip for conditions 3/6; classes via `unicodedata.bidirectional`) + ContextJ: reject U+200C /
   U+200D outright (join-control conservative reject; no joining tables shipped) → `bidi_ok`.
6. **Chokepoint:** `iana_root_zone_membership.matches(n)` =
   `name_syntax_ok(n) and label_lengths_ok(n) and uts46_ok(n) and bidi_ok(n) and
   ace_encode(n.tld) in ROOT_ZONE_TLDS`. Failure ⇒ no LOOKUP ⇒ orchestrator
   `_require_lookup_corroboration` (`orchestrator.py:750-783`) drops every PARSER candidate on
   that recognition ⇒ `_enforce_single_value_invariant` (`:625`) sees only qualified candidates
   (comment at `:152-156` cites ADR-0012 — disqualified ghosts must not trip multi-mention) ⇒
   zero survivors + `had_recognitions=True` ⇒ INVALID (`:882-889`); no recognition ⇒ MISSING;
   SUCCESS iff the qualified value set has exactly one element.
7. **ADR-0012 structural pins:** exactly one `RuleStrategy.LOOKUP_TABLE` rule in the capability
   (the iana rule); vacuity unreachable by default (the lookup rule is never filtered out by
   default `pinned_rules`/`excluded_rules`/`requires_features`). Tests: default contract → W10
   INVALID; `excluded_rules=("root-zone-membership",)` → vacuous lookup → W10 flips to SUCCESS
   (documents that qualification, not the parsers, is what rejects it).
8. **Data flow (Task 3 API):** `paxman/capabilities/Domain/idna_processing.py` —
   `status_of(cp)` (default `"valid"`, resolved from range keys), `map_domain(text)` (MAPPING for
   `mapped` — values are the table target verbatim and may be space-separated multi-target
   (1,018 rows, e.g. U+FB00 → `"0066 0066"`; expand each via `chr(int(h, 16))`) — `""` for
   `ignored`, verbatim for `deviation`/`disallowed` per non-transitional pin;
   **no `str.casefold` — the shipped table carries the case mapping** (`0041;mapped;0061` etc.);
   NFC; split `"."`; strip ONE trailing empty), `ace_encode(label)` (ASCII passthrough else
   `"xn--" + label.encode("punycode").decode("ascii")`), `ace_decode_ok(label)` (only meaningful
   for `xn--` labels: non-empty ASCII payload, non-empty decode, `"xn--" + reencode == label`;
   guards the `''.encode()==b''` bypass), `ace_decode(label)` (failure → label unchanged),
   `finalize(labels)` (map-independent ACE encode + `".".join`).
9. **Table versions (documented deviation from report §5.2/§7.2):** shipped table = **15.1.0**
   (`IDNA_VERSION` of the URL data module — the single in-tree `.txt`); rule provenance string
   cites UTS #46 **v18.0.0** (spec lineage). The report's "v18.0.0 table" phrasing conflated spec
   and table versions — closed by this pin + `test_idna_version_matches_url_shipped_table`.
10. **Shipped-table semantics that differ from the report's expectations (deviations D-a/D-b):**
    in the shipped 15.1.0 table, **U+200B ZWSP is `ignored`** (line 2333) — removed at map, so
    `example\u200b.com` → `example.com` **SUCCESS**, not INVALID (report W13/E16 claimed
    `disallowed`); **U+200C/U+200D are `deviation`** (line 2334) — kept by non-transitional map,
    then rejected by the ContextJ check in the bidi rule. The report's "invisible character →
    INVALID" intent is preserved by plan rows X8 (U+202E RLO — table `2028..202E ; disallowed`,
    line 2343) and X9 (ZWNJ ContextJ). Underscore U+005F is `disallowed_STD3_valid` (covered by
    `005B..0060`, line 43).
11. **Rule combination order (first-hand `orchestrator.py:116-175`):** `_collect_candidates` (:140)
    → `_require_lookup_corroboration` (:149) → invariant on **qualified** candidates (:152-156) →
    `_dedup_candidates` → `_determine_status(deduped, had_recognitions)` (:164; `had_recognitions`
    :130) → `ExecutionResult` (:64, `status` :73, `canonicalized_value` :74, assigned :174).
12. **Rule metadata pins (`kind` lives on `Provenance`, never on `Rule` —
    `paxman/core/domain.py:36-46`; `Rule.__init_subclass__` enforces exactly
    name/strategy/provenance/citation/target_semantics/requires_features):**

| Class | file | `name` | strategy | `PUBLICATION` — exact field values |
|---|---|---|---|---|
| `Rfc1034NameSyntax` | `rfc_1034_name_syntax.py` | `Section-3.1-name-syntax` | PARSER | authority `"IETF"`, specification_name `"RFC 1034"`, kind `"specification"`, reference_url `https://www.rfc-editor.org/rfc/rfc1034`, version `"1987"`, lifecycle `"active"`, publication_year `1987`; citation `"RFC 1034 §3.1 name syntax"` |
| `Rfc1035LabelLength` | `rfc_1035_label_length.py` | `Section-2.3.4-label-length` | PARSER | `"IETF"` / `"RFC 1035"` / `"specification"` / `https://www.rfc-editor.org/rfc/rfc1035` / `"1987"` / `"active"` / `1987`; citation `"RFC 1035 §2.3.4 size constraints"` |
| `UnicodeUts46Statuses` | `unicode_uts46_statuses.py` | `UTS46-statuses` | PARSER | `"Unicode"` / `"UTS #46"` / `"specification"` / `https://www.unicode.org/reports/tr46/` / `"18.0.0"` / `"active"` / `2026`; citation `"UTS #46 processing with STD3 rules"` |
| `Rfc5893BidiContext` | `rfc_5893_bidi_context.py` | `Section-2-bidi-context` | PARSER | `"IETF"` / `"RFC 5893"` / `"specification"` / `https://www.rfc-editor.org/rfc/rfc5893` / `"2010"` / `"active"` / `2010`; citation `"RFC 5893 §2 Bidi rule"` |
| `IanaRootZoneMembership` | `iana_root_zone_membership.py` | `root-zone-membership` | **LOOKUP_TABLE** | `"IANA"` / `"tlds-alpha-by-domain.txt"` / `"registry"` / `https://data.iana.org/TLD/tlds-alpha-by-domain.txt` / `"IANA tlds-alpha v2026092300"` / `"active"` / `2026`; citation `"IANA Root Zone Database membership"` |

    The iana `version` carries the full snapshot stamp deliberately — the T10 provenance test
    reads it off the surviving candidates' provenance tuples. Per-rule `test_metadata` follows
    the country convention (`tests/capabilities/country/test_rules.py:75-80`):
    `test_provenance_attributes` asserting each `rule.provenance.<field>` above plus the
    `citation` string — never a flat `rule.kind` (no such attribute).

    All five: `target_semantics = frozenset({"ascii_hostname", "idn_hostname"})`,
    `requires_features = frozenset()` (D6/D7 knobs stay contract comments; no
    `scope_selectors.py` shipped; report §5.2 defers it to a D6/D7 flip).
13. **Grammars:** distinct semantics `ascii_hostname` / `idn_hostname`; both
    `single_value = True` (exemplar `bcp47_tag_recognition.py:301-306`); `single_value=False`
    default at `domain.py:295`.
14. **Contract docstring class gate** (`test_offered_format_class_declarations.py:100-140`,
    `_CLASS_TERMS` :90): `DomainContract`'s `inspect.getdoc()` must have **exactly one** paragraph
    containing both the literal `"unicode"` and a class term (use `"encoding"`); no paragraph may
    contain the banned token `"projection"`. Exact paragraph is pinned in Task 2.
15. **Scaffolder:** `uv run python tools/new_capability.py Domain --name domain --authority IETF
    --spec-name "RFC 1034" --spec-url https://www.rfc-editor.org/rfc/rfc1034 --publication-year
    1987 --default-format ascii` → `rule_file = "ietf_ed1987"` (:679), grammar file
    `domain_recognition.py`, grammar class `DomainRecognition`, `name=semantics="domain_recognition"`,
    `single_value = False` TODO (:190-195), rule class `DomainRule`, `name = "Section 1-overview"`
    TODO (:224-235); 13 files (:706-738); probe test `test_scaffold_probe_missing` (:390) exists
    until T1 deletes it (it asserts single-label scaffold behavior → INVALID ≠ MISSING at T4);
    scaffold wires `capabilities/__init__.py` + `test_capability_surface.py` (verify only);
    scaffold does **not** touch `pyproject.toml` (no `domain` marker needed — the project has no
    `credit_card` marker either; `pytestmark = pytest.mark.capability` suffices).
16. **Registration (T9/T10 only):** `test_capability_wild_variants.py` is the ONLY
    capability-layer file that calls `canonicalize()` — module-level autouse `_clean_registry`
    (reset → register `DomainCapability` → yield → reset, `isin/test_capability.py:116-120`
    pattern). `test_capability.py` calls `get_grammars()`/`get_rules()`/`format_value()` directly
    — no `canonicalize()`, no registration. Integration test mirrors
    `tests/integration/test_phone_pipeline.py:12-36`. Property suites auto-register via their
    `_fresh_registry` (`test_reentry_invariant.py:274-283`).
17. **A0 whole-input pin:** `de` is a COMMON_WORD (`paxman/core/grammar/data/common_words.py:70`)
    — with `suppress_common_words=True`, input `"de"` → recognition suppressed by common-word
    guard BUT A0 whole-input exemption keeps it → then single-label → rfc_1034 fails → no
    LOOKUP → INVALID (regression would be MISSING).
18. **Generators:** `tools/regenerate_domain_idna_data.py` mirrors
    `tools/regenerate_idna_uts46_data.py` (`SNAPSHOT` :17 = the committed URL
    `idna_uts46_mapping.txt` — one table text in-tree, G8; `IDNA_VERSION="15.1.0"` :10;
    `_MAPPED_STATUSES` :23; argparse `--check` :137-147 exits 1 on drift) and writes
    `grammar/data/idna_mapping.py` exporting `IDNA_VERSION: str`, `MAPPING: dict[int, str]`
    (mapped rows expanded — 5,698 rows → 5,935 codepoints, measured), `STATUSES: dict[str, str]`
    (3,314 range keys — full int expansion would be ~10⁶ entries, infeasible: **documented
    refinement**; `idna_processing` resolves range keys via a sorted-interval bisect built at
    import). `tools/regenerate_root_zone_tld_data.py` — **required** `--snapshot-version` (no
    clock; `--check` runs offline from the committed snapshot), fetches
    `https://data.iana.org/TLD/tlds-alpha-by-domain.txt` once, writes
    `paxman/shared_data/root_zone_snapshot.json` (`_meta{source,version,entry_count,generated_by}`
    + uppercase-as-fetched list — **mandatory**, report §11 called it "optional" = deviation D-c)
    and `rules/data/root_zone_tlds.py` (report §7.3 exact shape: Source/Snapshot/Cross-check/
    Generator/Invariant/Spot-check header comments, `ROOT_ZONE_TLDS: frozenset[str]` lowercase,
    `SNAPSHOT_VERSION="tlds-alpha-by-domain.txt@2026092300"`, **1,438 entries** — G5 note: Root
    Zone DB lists 1,595, the machine list is 1,438; both stamps go in the tool header).
    IBAN `--check` precedent (`tools/regenerate_iban_registry_data.py:124-143`).
19. **Seven count surfaces 26→27** (exact edits in T12; mid-plan red between T9 and T11/T12):
    `test_api_coverage_fix.py:31`, `test_capability_lazy_import.py:56` (+word), 
    `test_capability_exports.py:283`, `test_offered_format_class_declarations.py` (:46/:68 — gate
    :95 red at T9), `test_bootstrap.py` (:37/:74), `test_capability_surface.py` (scaffolder-wired,
    NOT red), plus the reentry/preservation gates below. Sweep command:
    `rg -n 'twenty-six|all 26|26 capabilities|== 26|26 shipped' -g '!docs/development/**' -g '!CHANGELOG.md'`.
20. **Reentry (ADR-0010, `test_reentry_invariant.py`):** `_row` :98; insert after DOI row :145,
    before Email comment :146 — `_row(Domain, "example.com", "example.com")`,
    `_row(Domain, "EXAMPLE.COM.", "example.com")`,
    `_row(Domain, "münchen.de", "xn--mnchen-3ya.de")` with a source-test comment; import `Domain,`
    between :69/:70; formats/variants auto-derive; gate `{row.name for row in ROWS} ==
    set(list_shipped_capabilities())` at :238-239 (red at T9). Do NOT add to `_SUPPRESS_CASES`
    (:363) or `_SUPPRESS_WS_CASES` (:389). A0 test appended at end of file (:418).
21. **Preservation (ADR-0011, `test_output_format_preservation.py`):** `("domain", "unicode"):
    "encoding"` Domain section between DOI (:155-159) and GTIN (:160) with an explanatory comment
    (gate :239 red at T9); import `Domain,` after :80, before :81; `_InjectivityPair("domain",
    Domain, "unicode", "münchen.de", "straße.de", "")` as the FIRST entry of
    `_INJECTIVITY_PAIRS` (before the Language pair at :324).
22. **Benchmark (deviation from report §13, which named `harness.py`):** the scenario lives in
    `benchmarks/scenarios.py` — `_domain_register` mirroring `_country_register` (:10),
    `_domain_contract` mirroring (:21), SCENARIOS row between `date` (:215) and `email`, four keys
    `capability/text/register/contract_factory` (:203-208 exemplar), input `"münchen.DE."`.
23. **Bidi v1 scope:** six §2 conditions + conservative ContextJ (reject U+200C/U+200D), no
    joining tables, no ContextO tables shipped. Robust fixtures only (pure-RTL accept, L-edge and
    digit-edge rejects, AN/EN-mix reject, trailing-EN accept per condition 3, ZWNJ reject,
    LDH/ACE fast-path) — no mixing-rule fixtures pinned beyond these.
24. **`format_value` seam (T9):** `format_value(self, value, output_format, notation)` — THREE
    args; the engine passes the source notation positionally (`paxman/engine/orchestrator.py:870-872`,
    DOI exemplar `paxman/capabilities/DOI/capability.py:72-77`). `ascii`/default returns
    value; `unicode` splits value on `"."`, for each label `startswith("xn--")` →
    `ace_decode(label)` else label, rejoin. Never raises by construction (decode failure →
    label unchanged).

#### Golden corpus (inline literals — T10 executes all of these through `canonicalize()`)

Contract for every row: `canonicalize(text, Domain.create_contract())`, assert
`result.status == <status>` and `result.canonicalized_value == <value>` (`None` for
INVALID/MISSING).

**W-table (from the report, with shipped-table corrections):**

| id | input literal | status | value |
|---|---|---|---|
| W1 | `"EXAMPLE.COM"` | SUCCESS | `example.com` |
| W2 | `"münchen.DE"` | SUCCESS | `xn--mnchen-3ya.de` |
| W3 | `"münchen.de."` | SUCCESS | `xn--mnchen-3ya.de` |
| W4 | `"XN--MNCHEN-3YA.de"` | SUCCESS | `xn--mnchen-3ya.de` |
| W5 | `"mu\u0308nchen.de"` | SUCCESS | `xn--mnchen-3ya.de` (W2 ≡ W5 convergence) |
| W6 | `"ｅxample。ｊｐ"` | SUCCESS | `example.jp` (fullwidth ｅ/ｊ/ｐ + ideographic 。) |
| W7 | `"straße.de"` | SUCCESS | `xn--strae-oqa.de` (non-transitional ß pin) |
| W8 | `"exam--ple.com"` | SUCCESS | `exam--ple.com` (`--` NOT at idx2-3) |
| W8r | `"ex--ample.com"` | INVALID | `None` (D13 `--` at idx2-3, no `xn--` prefix) |
| W9 | `"www.example.com"` | SUCCESS | `www.example.com` |
| W10 | `"foo.unknowntld-xyz"` | INVALID | `None` (LOOKUP miss — ADR-0012 flip target) |
| W11 | `"ex..ample.com"` | INVALID | `None` (empty label) |
| W12 | `"-cdn.example.com"` | INVALID | `None` (leading hyphen) |
| W13 | `"example\u200b.com"` | **SUCCESS** | `example.com` (ZWSP `ignored` in shipped table — **deviation D-a**) |
| W14 | `"user@example.com"` | MISSING | `None` (both spans killed at `@`) |
| W15 | `"https://example.com:8080/"` | MISSING | `None` (kills at `:` `/` + right boundary) |
| W16 | `"*.example.com"` | MISSING | `None` (`*` in both kill tuples; left-`.` kill) |

**E-table (from the report):**

| id | input literal | status | value |
|---|---|---|---|
| E1 | `"example.com."` | SUCCESS | `example.com` (root dot stripped) |
| E2 | `"EXAMPLE.COM"` | SUCCESS | `example.com` |
| E3 | `"münchen.de"` | SUCCESS | `xn--mnchen-3ya.de` |
| E4 | `"XN--MNCHEN-3YA.DE"` | SUCCESS | `xn--mnchen-3ya.de` |
| E5 | `"example。com"` | SUCCESS | `example.com` (mapped dot) |
| E6 | `"xn--.com"` | INVALID | `None` (empty ACE payload) |
| E7 | `"example.123"` | INVALID | `None` (TLD not in root zone) |
| E8 | `"a" * 64 + ".com"` | INVALID | `None` (label > 63 post-encode) |
| E9 | `"a" * 63 + "." + "a" * 63 + "." + "a" * 63 + "." + "a" * 62` | INVALID | `None` (name 254 chars) |
| E10a | `"-example.com"` | INVALID | `None` (leading hyphen; RFC 1123 relaxes digits only) |
| E10b | `"example-.com"` | INVALID | `None` (trailing hyphen; RFC 1035 §2.3.1) |
| E11a | `"localhost"` | INVALID | `None` (single label + not in zone; D6 deferred) |
| E11b | `"intranet"` | INVALID | `None` (same) |
| E12 | `"user@example.com"` | MISSING | `None` |
| E13 | `"https://example.com/"` | MISSING | `None` |
| E14a | `"192.168.0.1"` | INVALID | `None` (shapes OK; tld `1` not in zone — report §5.4) |
| E14b | `"[::1]"` | MISSING | `None` (brackets excluded; sub-spans boundary-killed) |
| E15 | `"*.example.com"` | MISSING | `None` |
| E16 | `"example\u200b.com"` | **SUCCESS** | `example.com` (**deviation D-a**, same as W13) |
| E17 | `"ex..ample.com"` | INVALID | `None` |
| E18a | `"com"` | INVALID | `None` (single label) |
| E18b | `"straße.de"` | SUCCESS | `xn--strae-oqa.de` (W7 duplicate, keyed E18b) |

**X-table (plan additions — extras, raise, and shipped-table pins):**

| id | input literal | status / behavior | value |
|---|---|---|---|
| X1 | `"visit example.com today"` | SUCCESS | `example.com` (free text; `visit`/`today` lack LOOKUP → dropped) |
| X2 | `"  example.com  "` | SUCCESS | `example.com` (padded — whole-string WS does not suppress) |
| X3 | `"STRASSE.DE"` | SUCCESS | `strasse.de` (≠ W7 — non-transitional divergence) |
| X4 | `"a.com;b.com"` | raises `MultipleMentionsError` | — |
| X5 | `"a.com;a.com"` | SUCCESS | `a.com` (same value dedups, no raise) |
| X6 | `".example.com"` | MISSING | `None` (sub-span left-`.` kill) |
| X7 | `"example.com.."` | INVALID | `None` (`\.*` full-span; two empties, one stripped) |
| X8 | `"exam\u202eple.com"` | INVALID | `None` (RLO `disallowed` — table `2028..202E`) |
| X9 | `"a\u200cb.com"` | INVALID | `None` (ZWNJ `deviation` → ContextJ reject) |

Idempotence note for the parametrize: every `(input, status, value)` triple is unique except the
literal W13/E16 and W7/E18b duplicates — use `ids=` labels (`"W13"`, `"E16"`, …) on
`@pytest.mark.parametrize`.

#### Expected red state (do not "fix" early — documented convergence)

Between Task 9 and Task 11/12 the suite is red at exactly:
`test_api_coverage_fix` (26≠27), `test_capability_lazy_import` (word + missing entry),
`test_capability_exports` (missing `Domain`), `test_offered_format_class_declarations` (factory
gate :95), `test_bootstrap` (missing `domain`, `25≠26`), `test_reentry_invariant:238`,
`test_output_format_preservation:239`. `test_capability_surface` is NOT red (scaffolder-wired).
Everything else must stay green task by task.

---

### Task 1: Scaffold + renames + Notation (TDD)

**Files:** create `paxman/capabilities/Domain/` skeleton + `tests/capabilities/domain/` per the
scaffold; rewrite `notation.py`, `test_notation.py`; rename scaffold files/classes.

Steps:
- [ ] Run scaffold: `uv run python tools/new_capability.py Domain --name domain --authority IETF --spec-name "RFC 1034" --spec-url https://www.rfc-editor.org/rfc/rfc1034 --publication-year 1987 --default-format ascii`.
- [ ] Failing test first — replace `test_notation.py` with: `test_notation_is_frozen_with_slots`
      (construct `DomainNotation(raw=..., labels=..., tld=...)`; assignment raises
      `FrozenInstanceError` under `# type: ignore[misc]`; `"__slots__"` in
      `DomainNotation.__dict__`... use `DomainNotation.__slots__` truthy),
      `test_notation_fields_raw_labels_tld` (raw `"münchen.DE."`, labels `("münchen","de")`,
      tld `"de"`; `.raw == "münchen.DE."` — span text verbatim),
      `test_notation_has_no_canonical_field`
      (`"canonical" not in DomainNotation.__dataclass_fields__`),
      `test_notation_raw_preserves_input_span_text`. Class marked
      `@dataclass(frozen=True, slots=True)`.
- [ ] Red → implement `notation.py` (`DomainNotation`, docstring cites RFC 5890 §2.3 U-label/
      A-label vocabulary only — no docs/development references) → green:
      `uv run pytest tests/capabilities/domain/test_notation.py -q`.
- [ ] Renames (same commit): `grammar/domain_recognition.py` → `grammar/ascii_hostname.py`,
      class `DomainRecognition` → `AsciiHostnameGrammar`, `name`/`semantics` → `"ascii_hostname"`;
      add empty `grammar/idn_hostname.py` stub with class `IdnHostnameGrammar`,
      `name`/`semantics` → `"idn_hostname"` (filled T5); `rules/ietf_ed1987.py` →
      `rules/rfc_1034_name_syntax.py`, class `DomainRule` → `Rfc1034NameSyntax`; update
      `capability.py` (the scaffold template imports the renamed grammar + rule modules at
      `tools/new_capability.py:106-111` — without this the renames ImportError),
      `rules/__init__.py`, `grammar/__init__.py`, `test_rules.py`, `test_grammar.py`,
      `test_capability.py` imports/assertions that named pre-rename identifiers
      (`domain_recognition`, `DomainRule`, `ietf_ed1987`).
- [ ] Delete the scaffold probe test (`test_scaffold_probe_missing` from the scaffolded test
      file) — its single-label expectation would be INVALID at T4, not the scaffold's MISSING.
- [ ] `pytestmark = pytest.mark.capability` (the project has no `credit_card`-style marker;
      scaffolder does not add one to `pyproject.toml` — nothing to edit there).

Verify: `uv run pytest tests/capabilities/domain -q` green, and
`rg -n 'domain_recognition|ietf_ed1987' paxman/capabilities/Domain tests/capabilities/domain`
prints nothing.

### Task 2: Contract (TDD)

**Files:** rewrite `paxman/capabilities/Domain/contract.py`; create `tests/capabilities/domain/test_contract.py`
(new file carries `pytestmark = pytest.mark.capability`).

- [ ] Failing tests first: `test_default_output_format_is_ascii`,
      `test_offered_output_formats_is_unicode` (`== frozenset({"unicode"})`),
      `test_output_format_resolution_variants` (`None`/`"default"`/`"ascii"` → `"ascii"`;
      `"unicode"` → `"unicode"` — resolved by `CapabilityContract.__post_init__`),
      `test_unknown_format_contract_error` (`pytest.raises(ContractError)` on
      `create_contract(output_format="json")`; `ContractError` from `paxman.core.errors`),
      `test_capability_name_is_domain`, `test_contract_is_frozen`
      (assignment raises, `# type: ignore[misc]` sanctioned), `test_suppress_common_words_default_false`,
      `test_scope_knobs_not_shipped` (no `allow_single_label`/`allow_underscore`/`transitional`
      attributes — knobs deferred to `requires_features`-gated rules per D6/D7/D4),
      `test_unicode_class_encoding_declared` (class-gate parity: `inspect.getdoc(DomainContract)`
      — exactly one blank-line-delimited paragraph contains both `"unicode"` and `"encoding"`;
      no paragraph contains `"projection"`).
- [ ] Implement contract.py: frozen dataclass (no slots), `DEFAULT_OUTPUT_FORMAT: ClassVar[str]
      = "ascii"`, `OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset({"unicode"})`,
      `capability_name: str = field(default="domain", init=False)`, knob **comments only**.
      Docstring — pinned exact paragraph (Task 2's gate reads it):

```python
    """User-facing configuration for the Domain capability.

    The default ``ascii`` format renders the canonical A-label form:
    lowercase ASCII labels joined by dots, without a trailing dot — the
    DNS wire/protocol form (RFC 5890 §2.3.2.1).

    Offered formats (ADR-0011 classes): ``unicode`` — encoding. The
    rendering decodes each ``xn--`` label with the RFC 3492 Punycode
    codec to produce the U-label presentation of the SAME canonical
    entity; decode∘encode is the identity on validated labels, so the
    rendering re-enters the default contract onto the same canonical
    value (ADR-0010 re-entry holds).

    Non-default scope knobs (single-label acceptance, underscore
    selector labels) are deliberately not shipped: they arrive later
    only as gated features declared through ``requires_features`` on
    the rule that reads them, never as contract fields read by
    grammars.
    """
```

Verify: `uv run pytest tests/capabilities/domain/test_contract.py -q` and
`uv run pytest tests/unit/test_offered_format_class_declarations.py -q` (only the factory gate
:95 stays red — the class scan :100-140 must pass from here on).

### Task 3: Generators, generated data, idna_processing (TDD)

**Files:** `tools/regenerate_domain_idna_data.py`, `tools/regenerate_root_zone_tld_data.py`,
`grammar/data/__init__.py`, `grammar/data/idna_mapping.py` (generated),
`rules/data/__init__.py`, `rules/data/root_zone_tlds.py` (generated),
`paxman/shared_data/root_zone_snapshot.json` (generated),
`paxman/capabilities/Domain/idna_processing.py`,
`tests/capabilities/domain/test_data.py`, idna_processing tests inside `test_rules.py`.

- [ ] Write `test_data.py` first (red — modules don't exist): `test_idna_version_is_15_1_0`
      (`idna_mapping.IDNA_VERSION == "15.1.0"`), `test_idna_version_matches_url_shipped_table`
      (Domain `IDNA_VERSION ==` URL
      `paxman.capabilities.URL.rules.data.idna_uts46_mapping.IDNA_VERSION`),
      `test_mapping_shape` (MAPPING keys int, values ASCII strings; spot
      `MAPPING[0x0041] == "0061"`, `MAPPING[0x3002] == "002E"`, `MAPPING[0xFF45] == "0065"`,
      `MAPPING[0xFB00] == "0066 0066"` — values are the table target verbatim: single 4-char
      hex OR space-separated multi-target (1,018 rows). Names are ours, not URL's: URL's dicts
      are `IDNA_STATUS`/`IDNA_MAPPED` (`idna_uts46_mapping.py:12,9027`); `MAPPING`/`STATUSES`
      is a structural mirror only), `test_statuses_shape` (STATUSES keys are
      `start`/`start..end` hex strings; spot underscore range covers U+005F),
      `test_root_zone_entry_count` (`len(ROOT_ZONE_TLDS) == 1438`),
      `test_root_zone_members` (`{"com","org","net","de","jp","xn--p1ai"} <= ROOT_ZONE_TLDS`),
      `test_root_zone_non_members` (`{"xn--mnchen-3ya","123","1"}.isdisjoint(ROOT_ZONE_TLDS)`),
      `test_root_zone_all_lowercase` (all `t == t.lower()`), `test_snapshot_version`
      (`SNAPSHOT_VERSION == "tlds-alpha-by-domain.txt@2026092300"`),
      `test_root_zone_snapshot_consistency` (shared json `_meta["version"]`/list ↔ module:
      parse `paxman/shared_data/root_zone_snapshot.json`, lowercase set equality with
      `ROOT_ZONE_TLDS`, `entry_count == 1438`, `_meta["source"]` endswith
      `tlds-alpha-by-domain.txt`).
- [ ] `test_rules.py` idna_processing tests (red first): `test_status_of_valid_ascii`
      (`status_of(ord("a")) == "valid"` — unlisted default), `test_status_of_std3_underscore`
      (`status_of(0x5F) == "disallowed_STD3_valid"`),
      `test_status_of_disallowed_replacement_char` (`status_of(0xFFFD) == "disallowed"`),
      `test_status_of_disallowed_directional_override` (`status_of(0x202E) == "disallowed"`),
      `test_status_of_deviation_sharp_s` (`status_of(0x00DF) == "deviation"`),
      `test_status_of_ignored_zero_width_space` (`status_of(0x200B) == "ignored"`),
      `test_map_domain_case_and_trailing_dot`
      (`map_domain("EXAMPLE.COM.") == ("example","com")`... returns tuple),
      `test_map_domain_fullwidth_and_dot_variants`
      (`map_domain("ｅxample。ｊｐ") == ("example","jp")`),
      `test_map_domain_nfc_convergence`
      (`map_domain("mu\u0308nchen.de") == map_domain("münchen.de") == ("münchen","de")`),
      `test_map_domain_removes_ignored_soft_hyphen` (`map_domain("exa\u00admple.com") ==
      ("example","com")`), `test_map_domain_removes_ignored_zero_width_space`
      (`map_domain("example\u200b.com") == ("example","com")`),
      `test_map_domain_keeps_disallowed_for_status_rejection`
      (`("exam\u202eple",) in [map_domain("exam\u202eple.com")[0]]` — i.e. RLO survives map, to be
      rejected by the statuses rule), `test_map_domain_deviation_kept_verbatim`
      (`map_domain("straße.de") == ("straße","de")`),
      `test_map_domain_expands_multi_target_mapping`
      (`map_domain("ﬀoo.com") == ("ffoo","com")` — U+FB00 ligature expands to two chars),
      `test_ace_encode_ascii_passthrough` (`ace_encode("com") == "com"`),
      `test_ace_encode_punycode` (`ace_encode("münchen") == "xn--mnchen-3ya"`,
      `ace_encode("straße") == "xn--strae-oqa"`),
      `test_ace_decode_ok_round_trip` (`ace_decode_ok("xn--mnchen-3ya") is True`),
      `test_ace_decode_ok_rejects_empty_payload` (`ace_decode_ok("xn--") is False`),
      `test_ace_decode_ok_rejects_non_ascii_payload`
      (`ace_decode_ok("xn--münchen") is False`),
      `test_ace_decode_ok_rejects_reencode_mismatch`
      (`ace_decode_ok("xn--mnchen-3ya-") is False` — decode yields the ASCII basic string,
      re-encode ≠ payload), `test_ace_decode_never_raises`
      (`ace_decode("xn--") == "xn--"` — failure returns label unchanged),
      `test_finalize_joins_ace_labels`
      (`finalize(("münchen","de")) == "xn--mnchen-3ya.de"`).
- [ ] Implement `tools/regenerate_domain_idna_data.py` (mirror `tools/regenerate_idna_uts46_data.py`:
      `SNAPSHOT` :17 = `paxman/capabilities/URL/rules/data/idna_uts46_mapping.txt`,
      `IDNA_VERSION="15.1.0"` :10, `_MAPPED_STATUSES` :23, `--check` :137-147; header docstring
      cites UTS #46 and states the spec-vs-table provenance pin) → generate
      `grammar/data/idna_mapping.py` by running it bare:
      `uv run python tools/regenerate_domain_idna_data.py`. Parse rule: for each
      `source ; mapped ; target` row, expand source ranges and emit
      `MAPPING[int(cp, 16)] = <target verbatim>` per codepoint (broadcast — zero range-target
      rows exist, verified; targets may be space-separated multi-codepoint).
- [ ] Implement `tools/regenerate_root_zone_tld_data.py` (required `--snapshot-version`, fetch
      once, `--check` offline from committed json exit-1-on-drift per
      `tools/regenerate_iban_registry_data.py:124-143`; header stamps 1,438 + the G5 note
      1,595 vs 1,438) → generate with the pinned version (live file verified 2026092300 /
      1,438 entries on 2026-09-24):
      `uv run python tools/regenerate_root_zone_tld_data.py --snapshot-version 2026092300`.
      The tool MUST parse the fetched file's `# Version XXXX` header line and exit non-zero
      when it differs from `--snapshot-version` (the versionless URL always serves current —
      on drift the worker re-pins `SNAPSHOT_VERSION`, `entry_count`, the iana `version`, and
      the T10 provenance string consistently, never hand-edits the generated module) →
      snapshot json + `rules/data/root_zone_tlds.py` (report §7.3
      header-comment shape verbatim: Source/Snapshot/Cross-check/Generator/Invariant/Spot-check).
- [ ] Implement `idna_processing.py`: range-key STATUSES resolved by a sorted-interval bisect
      built at module import; `status_of` default `"valid"`; `map_domain` per locked decision 8
      (table-only mapping, no `casefold`; NFC via `unicodedata.normalize`; split; strip ONE
      trailing empty); `ace_encode`/`ace_decode_ok`/`ace_decode`/`finalize` per locked decision 8.

Verify: `uv run python tools/regenerate_domain_idna_data.py --check` &&
`uv run python tools/regenerate_root_zone_tld_data.py --check` (both exit 0) &&
`uv run pytest tests/capabilities/domain/test_data.py tests/capabilities/domain/test_rules.py -q`.

### Task 4: ASCII grammar (TDD)

**Files:** `grammar/ascii_hostname.py`, `grammar/__init__.py`, `test_grammar.py`.

- [ ] Failing tests in `test_grammar.py` (mirror `tests/capabilities/language/test_grammar.py`
      accessors: `results[0].start/.end/.raw_text/.notation.*`; `self.grammar.recognize(text)`):
      `test_semantics_and_name` (`name == "ascii_hostname"`, `semantics == "ascii_hostname"`),
      `test_single_value_true`, `test_recognizes_simple_fqdn`
      (`recognize("example.com")` → 1, start 0, end 11, raw_text `example.com`, notation
      labels `("example","com")`, tld `"com"`, raw verbatim),
      `test_recognizes_uppercase_input` (`recognize("EXAMPLE.COM")` → notation labels
      `("example","com")` — mapped at emit; raw_text stays `EXAMPLE.COM`),
      `test_recognizes_trailing_dot` (`recognize("example.com.")` → end 12, notation labels
      `("example","com")` — ONE empty stripped),
      `test_misses_in_container` (free text `recognize("visit example.com today")` → spans for
      `visit`, `example.com`, `today` with boundary kills verified by exact start/end),
      `test_misses_left_dot_neighbor` (`.example.com` → the match is boundary-killed: `recognize`
      returns no span touching the leading dot — assert exact surviving span set),
      `test_misses_non_ascii_only_input` (ascii grammar on `"münchen.de"` → no ASCII-label span
      surviving — the non-ASCII class is in the kill tuple).
- [ ] Implement (line-exact exemplar `paxman/capabilities/Country/grammar/alpha2_recognition.py:1-47`
      — RegexMatcher, NOT the BCP47 ScannerMatcher): module constants `_LABEL`/`_LABEL0`/`_FQDN`
      (locked decision 3), `_ASCII_KILL` (locked decision 4);
      `def _emit_ascii(span: tuple[int, int], ctx: ScanContext) -> DomainNotation` building
      `DomainNotation(raw=ctx.text[s:e], labels=..., tld=...)` via `idna_processing.map_domain(raw)`
      (mirror `_emit`, alpha2 :19-22); `_ASCII_MATCHER = RegexMatcher(pattern=_FQDN,
      boundary=BoundarySpec(left=_ASCII_KILL, right=_ASCII_KILL), view=None, anchors=AnchorSet(),
      emit=_emit_ascii)` — `view=None` IS the identity/original-text view (mirror alpha2 :25-32;
      `mode` defaults to `"zero_width"`, `suppressible` defaults to `False` — leave both unset);
      `class AsciiHostnameGrammar(PipelineGrammar[DomainNotation])` with `name`/`semantics =
      "ascii_hostname"`, `single_value = True`, `pre = StandardPre[DomainNotation](empty_guard=True)`,
      `matchers = (_ASCII_MATCHER,)` (mirror alpha2 :35-47). Imports: `from paxman.core.grammar
      import AnchorSet, BoundarySpec, PipelineGrammar, StandardPre`, `from
      paxman.core.grammar.matchers.regex import RegexMatcher`, `from
      paxman.core.grammar.scan_context import ScanContext`.

Verify: `uv run pytest tests/capabilities/domain/test_grammar.py -q`.

### Task 5: IDN grammar (TDD)

**Files:** `grammar/idn_hostname.py` (stub from T1 → fill), `grammar/__init__.py`,
`test_grammar.py`.

- [ ] Failing tests: `test_idn_semantics_and_name` (`name == "idn_hostname"`,
      `semantics == "idn_hostname"`), `test_idn_single_value_true`,
      `test_idn_recognizes_unicode_labels` (`recognize("münchen.de")` → 1 span 0..13,
      notation labels `("münchen","de")` — NFC'd at emit; **no ≥1-non-ASCII predicate**: it also
      matches `example.com`),
      `test_idn_recognizes_fullwidth_dot` (`recognize("ｅxample。ｊｐ")` → span over full input,
      labels `("example","jp")` — U+3002 is in-class, mapped at emit),
      `test_idn_misses_ascii_punctuation` (no span for `[::1]`, `user@example.com`,
      `https://example.com/` — every reserved ASCII excluded by `_IDN_LABEL`),
      `test_ascii_idn_overlap_dedup` (`recognize("example.com")` on BOTH grammars returns the
      identical span — dedup is same-span, not predicate; assert equal start/end).
- [ ] Implement per locked decisions 3+4 (`_IDN_LABEL`/`_IDN_LABEL0`/`_IDN_FQDN`, 12-element
      kill tuple = `_ASCII_KILL` minus the non-ASCII class) as a second `RegexMatcher` +
      `IdnHostnameGrammar(PipelineGrammar[DomainNotation])` mirroring the exact T4 exemplar shape
      (`view=None`, `AnchorSet()`, module `_emit_idn`, `pre = StandardPre[DomainNotation](empty_guard=True)`,
      `matchers = (_IDN_MATCHER,)`).

Verify: `uv run pytest tests/capabilities/domain/test_grammar.py -q`.

### Task 6: Rules — rfc_1034 + rfc_1035 (TDD)

**Files:** `rules/rfc_1034_name_syntax.py`, `rules/rfc_1035_label_length.py`,
`tests/capabilities/domain/test_rfc_1034_name_syntax.py`,
`tests/capabilities/domain/test_rfc_1035_label_length.py`.

- [ ] `test_rfc_1034_name_syntax.py` (red): `test_matches_two_labels`, `test_rejects_single_label`
      (`localhost`, `com` — D6 scope note in comment, citation RFC 1034 §3.1),
      `test_rejects_empty_label` (`ex..ample`, `example.` — after strip),
      `test_public_predicate_name_syntax_ok` (the exported predicate mirrors `matches`),
      `test_metadata` (name `Section-3.1-name-syntax`, `strategy == RuleStrategy.PARSER`,
      `target_semantics == {"ascii_hostname","idn_hostname"}`,
      `requires_features == frozenset()`); `test_provenance_attributes` in country style
      (`tests/capabilities/country/test_rules.py:75-80`): `rule.provenance.authority == "IETF"`,
      `.specification_name == "RFC 1034"`, `.kind == "specification"`,
      `.reference_url == "https://www.rfc-editor.org/rfc/rfc1034"`, `.version == "1987"`,
      `.lifecycle == "active"`, `.publication_year == 1987`, plus `rule.citation ==
      "RFC 1034 §3.1 name syntax"`; construct `DomainNotation` directly (raw/labels/tld).
      New file carries `pytestmark = pytest.mark.capability`.
- [ ] `test_rfc_1035_label_length.py` (red): `test_accepts_63_octet_label`
      (`"a"*63` label ok), `test_rejects_64_octet_label` (`"a"*64` → False — E8),
      `test_accepts_253_char_name` (3×63+62 = 253 → True), `test_rejects_254_char_name`
      (E9 tuple → False), `test_length_is_post_encode`
      (`ace_encode` over labels before measuring: a Unicode label whose ACE form is 63 passes and
      64 fails — build labels around `xn--mnchen-3ya` padding), `test_public_predicate_label_lengths_ok`,
      `test_metadata` (name `Section-2.3.4-label-length`, PARSER, both semantics, empty features),
      `test_provenance_attributes` (`"IETF"` / `"RFC 1035"` / `"specification"` /
      `https://www.rfc-editor.org/rfc/rfc1035` / `"1987"` / `"active"` / `1987`; citation
      `"RFC 1035 §2.3.4 size constraints"`). Constants `MAX_LABEL_OCTETS = 63`,
      `MAX_NAME_CHARS = 253`. New file carries `pytestmark = pytest.mark.capability`.
- [ ] Implement both; predicates are module-level public functions imported by the iana rule (T8).

Verify: `uv run pytest tests/capabilities/domain/test_rfc_1034_name_syntax.py tests/capabilities/domain/test_rfc_1035_label_length.py -q`.

### Task 7: Rules — uts46 statuses + bidi (TDD)

**Files:** `rules/unicode_uts46_statuses.py`, `rules/rfc_5893_bidi_context.py`,
`tests/capabilities/domain/test_unicode_uts46_statuses.py`,
`tests/capabilities/domain/test_rfc_5893_bidi_context.py`.

- [ ] `test_unicode_uts46_statuses.py` (red): `test_accepts_valid_ascii_labels`,
      `test_accepts_non_ascii_u_label` (`münchen` — statuses valid/deviation allowed),
      `test_accepts_valid_ace_label` (`xn--mnchen-3ya` — round-trip ok),
      `test_rejects_ace_label_with_empty_payload` (`xn--` → False — E6),
      `test_rejects_underscore_std3` (`_dmarc` label → False — D7 STD3 on),
      `test_rejects_disallowed_char` (`exam\u202eple` RLO → False; ZWSP/ZWNJ handling lives in
      the map + ContextJ tests, not here — `ignored` chars never reach statuses),
      `test_deviation_sharp_s_accepted` (`straße` label → True),
      `test_rejects_leading_hyphen` (`-cdn` → False; RFC 1123 §2.1 relaxes digits only),
      `test_rejects_trailing_hyphen` (`example-` → False; RFC 1035 §2.3.1),
      `test_rejects_double_hyphen_at_3rd_4th_position` (`ex--ample` → False; D13 /
      RFC 5890 §2.3.2.1 + RFC 5891 §4.2.3.1),
      `test_allows_double_hyphen_outside_3rd_4th` (`exam--ple` → True — W8),
      `test_ace_prefix_exempt_from_hyphen_3_4` (`xn--mnchen-3ya` → True),
      `test_public_predicate_uts46_ok` (= ACE ∧ statuses ∧ hyphens),
      `test_metadata` (name `UTS46-statuses`, PARSER, both semantics, empty features),
      `test_provenance_attributes` (`"Unicode"` / `"UTS #46"` / `"specification"` /
      `https://www.unicode.org/reports/tr46/` / `"18.0.0"` / `"active"` / `2026`; citation
      `"UTS #46 processing with STD3 rules"`). New file carries
      `pytestmark = pytest.mark.capability`.
- [ ] `test_rfc_5893_bidi_context.py` (red) — build `DomainNotation` with Unicode labels
      directly (inline Arabic literals are fine): `test_non_bidi_fast_path_true`
      (`("example","com")` → True; `("xn--mnchen-3ya","de")` → True — pure LDH, RFC 5893 §1.1
      places no requirements on non-Bidi names),
      `test_pure_rtl_label_and_ascii_coexist` (`("مثال","com")` → True — six conditions apply
      because the name contains an R/AL/AN char),
      `test_rtl_label_rejects_ltr_char_inside` (`("مa","com")` → False — condition 2),
      `test_ltr_typed_label_rejects_rtl_char` (`("aم","com")` → False — first char L types the
      label LTR, condition 5),
      `test_rtl_label_leading_digit_rejected` (`("2مثال","com")` → False — condition 1, first
      char must be L/R/AL),
      `test_rtl_label_trailing_european_digit_accepted` (`("مثال2","com")` → True — condition 3
      allows EN at end, §4.3 relaxation),
      `test_rtl_label_rejects_an_en_mix` (`("م٠2","com")` → False — condition 4),
      `test_contextj_join_control_rejected` (`("م\u200cث","com")` → False — ZWNJ is `deviation`
      (kept by map); the six conditions would pass (BN allowed), the explicit ContextJ check
      rejects; no joining tables shipped — conservative reject, comment cites RFC 5892),
      `test_public_predicate_bidi_ok`,
      `test_metadata` (name `Section-2-bidi-context`, PARSER, both semantics, empty features),
      `test_provenance_attributes` (`"IETF"` / `"RFC 5893"` / `"specification"` /
      `https://www.rfc-editor.org/rfc/rfc5893` / `"2010"` / `"active"` / `2010`; citation
      `"RFC 5893 §2 Bidi rule"`). New file carries `pytestmark = pytest.mark.capability`.
      Implementation: `unicodedata.bidirectional` per char; name is Bidi iff any label contains
      class R/AL/AN (§1.4); non-Bidi → `True`; else type each label by FIRST char (condition 1)
      and check conditions 1–6 with NSM-trailing strip for 3/6; then ContextJ reject of
      U+200C/U+200D.

Verify: `uv run pytest tests/capabilities/domain/test_unicode_uts46_statuses.py tests/capabilities/domain/test_rfc_5893_bidi_context.py -q`.

### Task 8: iana chokepoint + ADR-0012 structural tests (TDD)

**Files:** `rules/iana_root_zone_membership.py`,
`tests/capabilities/domain/test_iana_root_zone_membership.py`; structural test appended to
`test_capability.py` (registration-free — see note).

- [ ] `test_iana_root_zone_membership.py` (red): `test_matches_known_tld`
      (`("example","com")` → True), `test_matches_known_unicode_tld`
      (`("münchen","de")` → True — membership checks `ace_encode(tld)`),
      `test_rejects_unknown_tld` (`("example","unknowntld-xyz")` → False — W10),
      `test_rejects_numeric_tld` (`("192","168")`-style numeric tail → False — E14a authority),
      `test_rejects_single_label` (single label → False — D6 scope),
      `test_rejects_when_any_predicate_fails` (empty label, 64-octet label, underscore label,
      ZWNJ label each → False — the AND, one test per conjunct),
      `test_chokepoint_ands_public_predicates` (call the four imported predicates directly and
      assert `matches == (name_syntax_ok and label_lengths_ok and uts46_ok and bidi_ok and
      membership)` over a table of ~8 constructed notations),
      `test_metadata` (name `root-zone-membership`,
      `strategy == RuleStrategy.LOOKUP_TABLE`, both semantics, empty features),
      `test_provenance_attributes` (`rule.provenance.authority == "IANA"`,
      `.specification_name == "tlds-alpha-by-domain.txt"`, `.kind == "registry"`,
      `.reference_url == "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"`,
      `.version == "IANA tlds-alpha v2026092300"`, `.lifecycle == "active"`,
      `.publication_year == 2026`; `rule.citation == "IANA Root Zone Database membership"`).
      New file carries `pytestmark = pytest.mark.capability`.
- [ ] ADR-0012 structural tests (in `test_capability.py` — read
      `capability.get_rules()` directly, no registry, no `canonicalize`):
      `test_exactly_one_lookup_table_rule` (exactly one rule with
      `strategy == RuleStrategy.LOOKUP_TABLE`, and it is `IanaRootZoneMembership`),
      `test_lookup_rule_always_applied_by_default` (`Domain.create_contract()` — the lookup rule
      is in neither `pinned_rules` nor `excluded_rules`, and its `requires_features` is empty —
      vacuity unreachable).
- [ ] Implement `IanaRootZoneMembership` — import the four public predicates from their module
      paths (intra-capability import; import-linter bans only cross-capability) and AND with
      `ace_encode(tld) in ROOT_ZONE_TLDS`. Comments cite RFC 1034 §3.1 / RFC 1035 §2.3.4 /
      UTS #46 / RFC 5893 / IANA Root Zone — never docs/development.

Verify: `uv run pytest tests/capabilities/domain/test_iana_root_zone_membership.py tests/capabilities/domain/test_capability.py -q`.

### Task 9: Capability surface, registration, CLI dispatch (TDD)

**Files:** `capability.py`, `paxman/api/bootstrap.py`, `paxman/cli.py`,
`paxman/capabilities/__init__.py` (scaffolder-wired — verify only),
`tests/capabilities/domain/test_capability.py`, `tests/unit/test_cli.py`.

- [ ] `test_capability.py` additions (no `canonicalize`, no registration):
      `test_get_grammars_returns_two` (AsciiHostnameGrammar + IdnHostnameGrammar),
      `test_get_rules_returns_five` (the five classes, in metadata order 1034/1035/uts46/5893/iana),
      `test_capability_name_is_domain` (`DomainCapability().name == "domain"`),
      `test_format_value_ascii_identity`,
      `test_format_value_unicode_decodes_ace` (notation `DomainNotation(raw="XN--MNCHEN-3YA.de",
      labels=("xn--mnchen-3ya","de"), tld="de")`;
      `format_value("xn--mnchen-3ya.de", "unicode", notation) == "münchen.de"`),
      `test_format_value_unicode_passes_ascii_through`
      (`format_value("example.com", "unicode", notation)` → unchanged),
      `test_format_value_default_is_ascii`.
- [ ] Implement `DomainCapability(Capability[DomainNotation])` — `name = "domain"` (scaffold-wired
      at `tools/new_capability.py:123`, verify); `get_grammars` returns
      `[AsciiHostnameGrammar(), IdnHostnameGrammar()]`; `get_rules` returns the five rule
      instances in metadata order; `format_value(self, value, output_format, notation)` per locked
      decision 24 (THREE args — the engine passes `notation` positionally); `create_contract` is
      the exact six-param keyword-only staticmethod mirroring
      `paxman/capabilities/DOI/capability.py:36-70` (`excluded_rules, pinned_rules, year,
      output_format, extra_grammars, suppress_common_words`, all keyword-only, returning
      `DomainContract(...)` with tuple-ized sequences) — the scaffold template ships only the
      first five (`tools/new_capability.py:133-164`), so ADD `suppress_common_words: bool = False`
      and pass it through, otherwise the CLI branch below TypeErrors. The surface guard
      (`test_create_contract_signature_has_unanimous_common_block`) requires the first five
      params in order, all keyword-only.
- [ ] Registration: `paxman/api/bootstrap.py` — add `Domain,` to the
      `from paxman.capabilities import (...)` between `Date,` (:25) and `Email,` (:26), and its
      `_SHIPPED` entry **exactly between the DOI (:49) and Email (:50) entries**.
      `paxman/capabilities/__init__.py` — three anchors: `__all__` after `Date` (:23), `_LAZY`
      after `Date` (:58), TYPE_CHECKING import between `Date` (:92) and `DOI` (:93)
      (scaffolder may already have wired these — verify, don't duplicate).
- [ ] CLI: `paxman/cli.py` — dispatch branch after the `doi` branch (ends :166), before
      `chemical_element` (:167):

```python
    if normalized == "domain":
        from paxman.capabilities import Domain

        return Domain.create_contract(suppress_common_words=suppress_common_words)
```

- [ ] `test_cli_domain_dispatch` in `tests/unit/test_cli.py` (mirror
      `test_cli_creates_orcid_contract` :9-14, including the `@pytest.mark.unit` decorator):
      `_create_contract("domain")` → `capability_name == "domain"`, `output_format == "ascii"`.
- [ ] Verify `test_capability_surface.py` already has `id="domain"` with third member `"ascii"`
      (scaffolder-wired — if absent, add the param exactly in that shape).

Verify: `uv run pytest tests/capabilities/domain tests/unit/test_cli.py tests/unit/test_capability_surface.py -q`.
Expected red from here until T11/T12 (locked decision 19/20/21 surfaces + factory gate) — see
**Expected red state**.

### Task 10: Wild corpus + integration parity (TDD)

**Files:** `tests/capabilities/domain/test_capability_wild_variants.py`,
`tests/integration/test_domain_idna_parity.py`.

- [ ] `test_capability_wild_variants.py` — `pytestmark = pytest.mark.capability`; module-level
      autouse `_clean_registry`
      (reset → `register_capability(DomainCapability())` → yield → reset;
      `tests/capabilities/isin/test_capability.py:116-120` pattern). Imports:
      `from paxman.api import canonicalize` (scaffold convention),
      `from paxman.capabilities.Domain.capability import DomainCapability`,
      `from paxman.capabilities.Domain.contract import DomainContract` (or the `Domain` alias —
      either; be consistent), `from paxman.core.discovery import register_capability,
      reset_registry`, `from paxman.core.domain import Resolution`. Helper:
      `canonicalize(text, Domain.create_contract())`, assert `result.status == status` and
      `result.canonicalized_value == value` (`None` for INVALID/MISSING).
      One `@pytest.mark.parametrize("raw,status,value,ids", [...])` containing **every row of the
      golden-corpus W-, E-, and X-tables verbatim** (inline literals exactly as pinned —
      `"mu\u0308nchen.de"`, `"ｅxample。ｊｐ"`, `"a" * 64 + ".com"`, the four-`"a"*63 E9
      concatenation, `"example\u200b.com"` → SUCCESS per D-a, `"exam\u202eple.com"` → INVALID,
      `"a\u200cb.com"` → INVALID, `"  example.com  "`, `"visit example.com today"`).
      Separate test `test_multiple_distinct_mentions_raise`
      (`pytest.raises(MultipleMentionsError)` on `"a.com;b.com"` — X4) and
      `test_duplicate_mentions_dedup` (`"a.com;a.com"` → SUCCESS `a.com` — X5).
      `from paxman.core.errors import MultipleMentionsError`.
- [ ] `tests/integration/test_domain_idna_parity.py` — every test carries
      `@pytest.mark.integration` (mirror `tests/integration/test_phone_pipeline.py:12-36`: module
      autouse `_clean_registry` + in-test `register_capability`).
      Tests: `test_nfc_nfd_convergence` (`canonicalize("mu\u0308nchen.de") ==
      canonicalize("münchen.de") == "xn--mnchen-3ya.de"`),
      `test_uts46_mapping_fixed_point` (`v = canonicalize("münchen.DE.",
      Domain.create_contract()).canonicalized_value; assert v == "xn--mnchen-3ya.de"; assert
      canonicalize(v, Domain.create_contract()).canonicalized_value == v`),
      `test_non_transitional_sharp_s_pin`
      (`canonicalize("straße.de") == "xn--strae-oqa.de"` and `!= canonicalize("STRASSE.DE")` —
      W7 vs X3 divergence), `test_root_zone_provenance_version`
      (rule-level: `IanaRootZoneMembership.provenance.version == "IANA tlds-alpha v2026092300"`;
      pipeline-level: `any("IANA tlds-alpha v2026092300" in str(p) for c in
      canonicalize("example.com", Domain.create_contract()).candidates for p in c.provenance)` —
      `ExecutionResult` carries NO `provenance` field (`orchestrator.py:63-80`); per-rule
      candidates survive dedup (`:843-851`), so the iana candidate's provenance tuple is read
      off `result.candidates`),
      `test_ace_u_label_convergence` (`canonicalize("münchen.de") ==
      canonicalize("XN--MNCHEN-3YA.de")`), `test_lookup_vacuity_flip`
      (default contract → W10 `"foo.unknowntld-xyz"` INVALID;
      `Domain.create_contract(excluded_rules=("root-zone-membership",))` → SUCCESS with value
      `foo.unknowntld-xyz` — the ADR-0012 flip proving qualification, not parser rejection).

Verify: `uv run pytest tests/capabilities/domain tests/integration/test_domain_idna_parity.py -q`.

### Task 11: Property suites — reentry, preservation, A0 (TDD)

**Files:** `tests/property/test_reentry_invariant.py`,
`tests/property/test_output_format_preservation.py`.

- [ ] `test_reentry_invariant.py`: import `Domain,` between the `Date,` (:69) and `Email,` (:70)
      import lines; insert three rows after the DOI row (:145), before the Email comment (:146),
      with a source-test comment: `_row(Domain, "example.com", "example.com")`,
      `_row(Domain, "EXAMPLE.COM.", "example.com")`,
      `_row(Domain, "münchen.de", "xn--mnchen-3ya.de")` (formats/variants auto-derive; do NOT
      touch `_SUPPRESS_CASES` :363 or `_SUPPRESS_WS_CASES` :389). Append at end of file, after
      `test_reentry_under_suppression_padded_variants` (ends :418 — the file's last line),
      `test_a0_whole_input_common_word_domain`: `canonicalize("de",
      Domain.create_contract(suppress_common_words=True))` → `status == INVALID` with
      `canonicalized_value is None` (A0 keeps the recognition → single-label → no LOOKUP →
      INVALID; a MISSING regression means A0 was bypassed). Registry comes from the file's
      `_fresh_registry` autouse (`:274-283`) — no new fixture.
- [ ] `test_output_format_preservation.py`: import `Domain,` after :80, before :81; add
      `("domain", "unicode"): "encoding"` to the CLASS_MAP section between DOI (:155-159) and
      GTIN (:160) with an explanatory comment (encoding-class rationale); add
      `_InjectivityPair("domain", Domain, "unicode", "münchen.de", "straße.de", "")` as the
      FIRST entry of `_INJECTIVITY_PAIRS` (before the Language pair at :324).

Verify: `uv run pytest tests/property/test_reentry_invariant.py tests/property/test_output_format_preservation.py -q`
(the two gates at :238/:239 now see `domain`; remaining red = T12 count surfaces).

### Task 12: Counts, docs, benchmark, CHANGELOG

**Files:** the seven count surfaces + `benchmarks/scenarios.py` + shipped docs per File Structure.

- [ ] Count edits (exact): `test_api_coverage_fix.py:31` `== 26` → `== 27` and add
      `assert "domain" in shipped` beside :30; `test_capability_lazy_import.py:56` "twenty-six"
      → "twenty-seven" and `"Domain",` between :67/:68; `test_capability_exports.py:283`
      `"Domain",` between `"DOI",`/`"Email",`;
      `test_offered_format_class_declarations.py` — `Domain,` between `Date,` (:46)/`Email,` (:47)
      and `"domain": Domain,` between `"doi": DOI,` (:68)/`"email": Email,` (:69);
      `test_bootstrap.py` — `"domain",` between "doi" (:37)/"email" (:38) and :74 `== 25` → `== 26`.
- [ ] Benchmark: `benchmarks/scenarios.py` — `_domain_register` (after `_country_register` :10),
      `_domain_contract` (after :21), SCENARIOS row between `date` (:215) and `email`, keys
      `capability/text/register/contract_factory`, input `"münchen.DE."`.
- [ ] Docs: README :69 table row + regenerate via
      `uv run python tools/generate_readme_table.py` (run only; the tool is unchanged); CONTEXT
      :76/:832/:1041 (capability count + Notation/table entries); ARCHITECTURE :83; AGENTS
      :8/:50/:104/:105 ("twenty-six"→"twenty-seven" and the capability list + commands);
      `paxman/capabilities/AGENTS.md` :4/:67; `tests/AGENTS.md` :4 (lowercase dir list).
- [ ] Guide `docs/user/capabilities/domain.md` (mirror an existing guide's structure —
      recognition/validation/output-format/choices sections; cite RFCs + UTS #46 + IANA, never
      docs/development) + capabilities-index chooser row + unversioned `docs/user/` site rows
      wherever `lei`/`gtin` appear (index, getting-started, concepts, api-reference, citations,
      glossary, migration). **Never touch `docs/user/v0.x/`.**
- [ ] `CHANGELOG.md` [Unreleased] :8 — one Added bullet mirroring the CreditCard bullet style
      (capability name, formats offered, authority pointers).
- [ ] Sweep: `rg -n 'twenty-six|all 26|26 capabilities|== 26|26 shipped' -g '!docs/development/**' -g '!CHANGELOG.md'`
      → empty (CHANGELOG history is exempt). Verify `docs/development` appears in NO shipped
      file: `rg -n 'docs/development' paxman/ tests/ benchmarks/ docs/user/ README.md CONTEXT.md ARCHITECTURE.md CHANGELOG.md tools/`
      → empty.

Verify: `uv run pytest tests/unit/test_api_coverage_fix.py tests/unit/test_capability_lazy_import.py tests/unit/test_capability_exports.py tests/unit/test_offered_format_class_declarations.py tests/unit/test_bootstrap.py -q` green — **full suite green again**.

### Task 13: Full gate + PR

- [ ] CLI smoke: `uv run python -m paxman domain "münchen.DE."` → `xn--mnchen-3ya.de`;
      `uv run python -m paxman --json domain "example.com."` → `"canonicalized_value": "example.com"`;
      `echo "EXAMPLE.COM" | uv run python -m paxman domain` → `example.com`; `--list` shows `domain`.
- [ ] Full pre-PR gate (one command):
      `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run import-linter lint && uv run pytest`
      then `uv run coverage report --include="paxman/core/*,paxman/capabilities/*,paxman/engine/*,paxman/api/*" --fail-under=95`.
- [ ] Open PR `feature/domain-idn-capability` → `dev`, title
      "feat(domain): add Domain/IDN capability (capability 27)", body = goal + corpus counts +
      the seven count surfaces + deviation summary (D-a shipped-table ZWSP, 15.1.0/v18.0.0 pin,
      `scenarios.py` filename, mandatory snapshot json, range-key STATUSES). Review via
      `paxman-oracle-review`.

Verify: gate commands all exit 0; `uv run python -m paxman --list | rg -n '^domain$'`.

---

## Documented deviations from the research report (all deliberate, all verified first-hand)

| # | Report says | Plan pins | Why |
|---|---|---|---|
| D-a | W13/E16 `example\u200b.com` → INVALID (`disallowed`) | → **SUCCESS `example.com`**; new X8 (RLO) + X9 (ZWNJ) carry the reject intent | Shipped 15.1.0 table line 2333: `200B ; ignored` — removed at map (first-hand) |
| D-b | (no pin) | ZWNJ/ZWJ: table `deviation` (kept by non-transitional map) → **ContextJ reject in `rfc_5893_bidi_context`** | Table line 2334 + UTS #46 CheckJoiners; conservative reject, RFC 5892 cited in comment |
| D-c | `root_zone_snapshot.json` "optional canonical source" | **Mandatory** — the generator always writes both json + module; `--check` validates from json | One source of truth; IBAN `--check` precedent |
| D-d | UTS #46 **v18.0.0 table** (spec/table conflated) | Shipped table **15.1.0** (URL's `IDNA_VERSION`); provenance cites spec **v18.0.0** | 17.0.0/18.0.0 table dirs 404; G8 requires one in-tree table |
| D-e | §4.2 lowercase-fold sketch; idn ≥1-non-ASCII predicate; kernel normalizer view | Original-text scan + emit-time `map_domain`; **no** idn predicate; identity view | §4.3 overlap resolved by same-span dedup (Design I) |
| D-f | `example.com..` implied MISSING (sub-span carve) | → **INVALID** via `\.*` trailing pattern | Full-span + one-empty-strip + no-empty rule → INVALID is the faithful reading |
| D-g | benchmark file `harness.py` | `benchmarks/scenarios.py` | First-hand: scenarios live there (`harness.py` is the runner) |
| D-h | STATUSES full int expansion | Range keys + bisect (5,935 int-keyed only for MAPPING — measured) | ~10⁶ entries infeasible in a source module |
| D-i | §4.2 boundary sketch | 13-tuple `_ASCII_KILL` / 12-tuple idn (adds `\*`, `%`, `[`/`]`) | Kills `[::1]`, `*.example.com`, URL-in-text sub-spans (first-hand trace) |

## Plan saved to `docs/development/plans/2026-09-24-domain-idn-capability.md`

Execute task-by-task via `tdd` + `verification-before-completion`; review gate:
`paxman-momus-review` before execution, `paxman-oracle-review` after implementation.
