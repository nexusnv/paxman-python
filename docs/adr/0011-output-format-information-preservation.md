# ADR-0011: Information-Preservation (Output-Format Equality) Invariant — Offered Formats Are Encodings, Same-Entity Expansions, or Documented Quantizations

## Status

**Accepted — 2026-09-06.** Tracked as issue #139. Phase 1 of the output-format invariant sequencing (after Phase 0, the Coordinates quantization obligations).

## Context

ADR-0010 guarantees re-entry (`canonicalize(V, C) == V`) but is **contract-relative**:
Phone `national` satisfies it only because its contract carries the missing country code
as `default_country` (`paxman/capabilities/Phone/contract.py:103-110`; the render itself
at `paxman/capabilities/Phone/capability.py:142-160`; the suite row crutch at
`tests/property/test_reentry_invariant.py:155-161`), and Language `alpha2` / `alpha3` /
`alpha3-bib` / `name` pass it while silently changing the entity (`en-US` → `en` — the
truncated value is itself a valid smaller entity, so nothing flags the change;
`paxman/capabilities/Language/capability.py:153-231`).

Re-entry proves a rendering is stable; it does not prove it is equal. The harm class is
identity confusion, not style: a projection that drops recognition or validation
information collides distinct entities onto one rendering (`+44…` / `+60…` onto one NSN;
`en-US` / `en-GB` onto `en`), merging records that denote different things.

This ADR joins the invariant family ADR-0004 began (Single-Value Invariant) and ADR-0010
continued (Re-entry): a correctness property of the pipeline as a whole, held by
construction and enforced by tests, never by hot-path runtime checks. It strengthens
ADR-0010 — re-entry stays required — and does not amend it.

## Decision

**Offered formats are encodings, same-entity expansions, or documented quantizations —
never projections over recognition/validation information.**

### Formal Statement

> **Information-Preservation (output-format equality).** For every capability, for every `F ∈ OFFERED_OUTPUT_FORMATS`, for every default canonical `V` the capability can produce: `W = format_value(V, F, notation)` must preserve every bit of `V` used by any shipped grammar to recognize `V`'s form or any shipped rule to validate `V` — recoverable from `W` alone under the default (param-free) contract. Corollaries:
>
> 1. **Entity-relative injectivity.** For all canonicals `V1 ≠ V2` denoting **different entities** (§2), `F(V1) ≠ F(V2)`. Same-entity spelling merges are permitted only as documented same-entity expansions (`AAAABBCC`/`AAAABBCCXXX` under `bic11`) and must be fixed-point. String-level injectivity is deliberately *not* required — it would condemn the audit's own PASS verdicts for `bic11`/`eui64` (§7.3).
> 2. **Param-free pre-image re-entry** (stronger than ADR-0010's same-contract `V→V`): `canonicalize(W, default_contract)` succeeds and returns the pre-image `V` — **exact** for encodings and same-entity expansions, **bounded-drift** (within ½ of the declared render quantum plus ½ of the canonical quantum, deterministic) for documented quantizations. No offered format may require a contract parameter to make its own output readable.
>
> Classification clause: every offered format belongs to exactly one class — encoding, same-entity expansion, or documented quantization — declared in the capability (contract docstring), with the class's obligations attached. Projections are not offered.

(The §-references above resolve to this ADR's own Definitions and Baseline audit
sections.)

## Definitions

- **Canonical value `V`.** The default-format string produced by `Rule.normalize()`
  (e.g. Phone `+4412341234`, Language `en-US`, Country `US`). Identity of the entity as
  the authority defines it.
- **Entity.** What the governing authority says a canonical value denotes — decided by
  the capability's authority data, not the engine. Two distinct canonical strings may
  denote the same entity: ISO 9362 makes the branch code implicit
  (`AAAABBCC` ≡ `AAAABBCCXXX`), and IEEE's EUI-48→EUI-64 derivation (`FF:FE` insertion)
  links a 48-bit MAC to its 64-bit form. By contrast, `en-US` is not "`en` with the
  region made explicit" — per BCP 47 the subtags change what the tag identifies, so
  `en-US` and `en` (and `en-GB`) are different entities. Injectivity in this invariant
  is defined over entities, not strings.
- **Format classes.** An **encoding** is reversible without side input (`electronic` ↔
  `paper` by space strip/insert; `hyphenated` ↔ `compact` by hyphen strip). A
  **same-entity expansion** makes an implicit default explicit (`AAAABBCC` →
  `AAAABBCCXXX`; EUI-48 → EUI-64): it merges two spellings of one entity — permitted,
  documented, fixed-point. A **documented quantization** renders at a declared display
  unit, discarding a contiguous low-order magnitude range and nothing else (`dms` at the
  arcsecond; `dm` at 0.001 min): many-to-one below the declared unit, bounded-drift,
  render-stable. A **projection** drops a semantic field (`+CCNSN` → `NSN`;
  `en-US` → `en`) or discards bits with no declared quantum, and is reversible only
  with side input (`default_country`) or not at all.
- **Render quantum.** The declared display unit of a documented-quantization format —
  the arcsecond (≈ 2.78e-4°) for Coordinates `dms`, 0.001 minutes for `dm` — below
  which distinct canonicals may share a rendering. The quantum must be declared at the
  contract seam (contract docstring), and the fixpoint / bounded-drift properties must
  be pinned in CI.

The dividing line between quantization and projection: a quantization discards a
magnitude tail below a *declared unit of the format*; a projection discards a *field*,
or bits with no unit declared. Field removal is banned.

## Scope Decisions

1. **Status is Accepted, not Proposed.** Mirroring ADR-0010 Scope decision 1: an
   invariant that defines what *offered* means cannot be adopted tentatively. Adoption
   of the invariant and taxonomy is hard. Enforcement against **pre-existing** surfaces
   is sequenced honestly: Phone `national` is a directed de-offer (a sequenced
   follow-up, breaking per this ADR's Consequences); Language's four projecting formats
   are waived with a migration plan until the subtag-preserving remediation lands (a
   sequenced follow-up); Coordinates `dms` / `dm` are compliant documented
   quantizations once Phase 0's declarations and property locks are in (a prerequisite
   of this ADR, landed).
2. **Entity-relative injectivity — string-level injectivity deliberately not
   required.** Same-entity merges are allowed only as documented expansions with
   merge-fixpoint fixtures. Rationale: the audit's `bic11` / `eui64` verdicts and an
   implementable CI gate both require it — a literal string-level gate would flag
   `bic11` the first time it samples the `AAAABBCC` / `AAAABBCCXXX` pair.
3. **Declared-quantization exception in Corollary 2.** Exact pre-image for
   encodings/expansions; bounded-drift (≤ ½ declared render quantum plus
   ½ canonical quantum) for documented quantizations. The quantum must be declared at the contract seam and the
   fixpoint/bounded-drift properties pinned in CI — `tests/property/test_coordinates_quantization.py`
   is the charter lock. `W→W` never stands in for `W→V`: render→parse→render
   stability and pre-image recovery are different properties, and only the first holds
   exactly for quantizations.
4. **Outputs only.** `default_country`-gated input recognition (domestic dialing) is
   legitimate and untouched; the invariant constrains what a format may *render*, never
   what context an *input* may need.
5. **Snapshot-relative and entity authority-relative.** Like determinism and re-entry,
   the invariant is scoped to a library snapshot (`VersionStamp.paxman_version` +
   `recognition_revision`): authority-table evolution may change which `V`s exist and
   which spellings denote one entity, never whether `F` preserves them.
6. **The engine never raises at runtime.** CI property tests plus review are the
   enforcement (ADR-0010 Consequences precedent); `run_capability()` carries no
   invariant bookkeeping.

## Baseline audit (2026-09-06)

Verdict per offered format against the invariant (removed ∩ (recognition ∪ validation) = ∅ required; injectivity assessed entity-relative per §2/§8.1):

| Capability (default) | Offered format | Mechanism | Removes recognition/validation info? | Verdict |
|---|---|---|---|---|
| Phone (`e164` `+CCNSN`) | `rfc3966` | Wrap `tel:` + optional `;ext=` | No — adds scheme, preserves all digits | PASS — keep |
| Phone | `national` | Strip CC → bare NSN | **Yes — CC used by `split_country_code` + assigned-CC validation** | **VIOLATION — de-offer (§4–§5)** |
| Language (`bcp47` tag) | `alpha2`, `alpha3`, `alpha3-bib`, `name` | `_primary_language(value)` then map; drops all non-primary subtags | **Yes — region/script/variant used by BCP 47 syntax + IANA registry validation** (`en-US` → `en`) | **VIOLATION — same category as Phone (§7)** |
| Coordinates (`decimal`) | `iso6709`, `geo_uri`, `geojson_pair` | Re-encode lat/lon/alt (signs, order, prefixes) | No — all components preserved | PASS — keep |
| Coordinates | `dms`, `dm` | Decimal → degrees/minutes(/seconds) with quantization (seconds integer half-even; minutes 0.001) | No field removed; no recognition/validation bit removed (recognition itself already quantizes to 6 dp — `coordinates_recognition.py:139-143`). Merges canonicals only below the declared render unit (arcsecond / 0.001 min) | **PASS — documented quantization: declare the quantum at the contract seam, lock render-stability + bounded-drift property tests (§7.2)** |
| Country (`alpha2`) | `alpha3`, `numeric`, `name` | ISO 3166-1 table maps (`ALPHA2_TO_*`); historical without mapping passes through | No — 1:1 entity encodings, no extra param, re-enter via own grammars | PASS — keep |
| Date (`ISO`) | `US` | `YYYY-MM-DD` → `MM/DD/YYYY` field reorder | No — same fields, strict parse | PASS — keep |
| Element (`symbol`) | `name` | `SYMBOL_TO_NAME` 1:1 map | No — reversible, re-enters via name path | PASS — keep |
| IBAN (`electronic`) | `paper` | Insert space every 4 chars | No — spaces presentation-only, MOD 97 on stripped | PASS — keep |
| ISBN (`isbn13`) | `hyphenated` | Range-Message longest-match hyphenation | No — hyphens presentation-only | PASS — keep |
| ISSN (`hyphenated`) | `compact`, `urn` | Strip hyphen / wrap `urn:issn:` | No — check digit unaffected | PASS — keep |
| ORCID (`orcid`) | `compact`, `uri` | Strip hyphens / prepend `https://orcid.org/` | No — MOD 11-2 on digits unaffected | PASS — keep |
| BIC (`bic`) | `grouped` | Insert spaces `AAAA BB CC [XXX]` | No — spacing only | PASS — keep |
| BIC | `bic11` | Append `XXX` to 8-char (head-office expansion) | No removal — deterministic expansion, re-enters (11-char with `XXX` validates); NOT string-injective (`F(AAAABBCC) = F(AAAABBCCXXX)`), but the merged canonicals denote one ISO 9362 entity (implicit branch code) | **PASS — same-entity expansion; allowed under entity-relative injectivity with merge-fixpoint fixtures (§7.3)** |
| MacAddress (`colon`) | `hyphen`, `bare`, `cisco` | Re-insert separators / strip / regroup hextets | No — same hex digits | PASS — keep |
| MacAddress | `eui64` | Insert `FF:FE` (EUI-48 → EUI-64); identity for EUI-64 | No removal — deterministic expansion, fixed-point by construction (identity for 64); `bit_reversed` removal precedent cited in contract; same-entity merge class as `bic11` | **PASS — same-entity expansion; same carve-out and fixtures as `bic11` (§7.3)** |
| Money (`code_amount`) | `compact` | Remove the single ASCII space separator | No — space is separator only (amount uses U+202F narrow no-break space, never ASCII); code and amount both preserved | PASS — keep |
| Currency, Email, IP, SIUnit, URL | (none offered) | identity only | — | PASS vacuously |

Single-format capabilities (Currency, Email, IP, SIUnit, URL) cannot violate the
invariant — there is no second representation to lose information in.

### Explicit non-violators commonly suspected

- **Country `name` / `alpha3` / `numeric`.** All ISO 3166-1 codes for the same entity;
  conversion tables are total over current assignments; historical codes without
  mappings pass through unchanged rather than mis-mapping. No extra contract param;
  each rendering re-enters via its own grammar. Encodings — keep.
- **BIC `bic11`, MacAddress `eui64`.** Expansions (add `XXX` / `FF:FE`), not removals.
  Deterministic, fixed-point, documented. They are **not string-injective** —
  `F_bic11(AAAABBCC) = F_bic11(AAAABBCCXXX) = "AAAABBCCXXX"`, and the EUI-64 rendering
  of a 48-bit MAC equals that 64-bit canonical's identity rendering — but the merged
  canonicals denote the **same entity** per the authority (ISO 9362 implicit branch
  code; IEEE derivation). This is exactly why the formal statement defines injectivity
  entity-relative: under string-level injectivity these PASS verdicts would contradict
  the formal statement, and a literal CI gate would flag `bic11` the first time it
  samples the pair. Obligations: the same-entity pairs become fixtures in the property
  gate asserting merge-and-fixpoint (they may share a rendering; each rendering must
  re-enter to itself), and the expansion semantics stay documented in the contract.
  Keep with existing docstrings as the model for documenting asymmetric-but-safe
  formats.
- **Money `compact`.** Separator removal where the separator is provably unique (ASCII
  space vs U+202F in amounts, documented in `Money/capability.py:104-114`). Keep.

### Latent-collision note (Phone GB vs MY, illustrative NSNs)

`V1 = +4412341234` (CC `44`), `V2 = +6012341234` (CC `60`). Both pass E.164 validation
(digits-only, ≤15, assigned CC, NSN ≥ 2). A naive NSN-for-every-CC rendering gives
`F(V1) = "12341234" = F(V2)` — `F` is not injective, so no decoder `G` with
`G(F(V)) = V` exists without side input. As shipped, the preservation branch renders
non-NANP values as E.164, so no live cross-country collision exists; the format avoids
the live collision only by being a partial function over its own value space. Safety
by refusal is the defect, not a defense: the moment anyone "completes" the branch the
natural-looking way, the collision ships. An equal representation must not be one
naive edit away from non-injective.

## Consequences

Soft mandate now; hard gates later. The obligations:

1. **New offered formats must ship with a class declaration** (encoding / same-entity
   expansion / documented quantization, in the capability's contract docstring) plus a
   param-free pre-image and entity-relative injectivity argument in the capability's
   test module — or, for declared quantizations, the quantum documented plus
   render-stability and bounded-drift property tests.
2. **Phone `national` is directed to de-offer with a migration note** (sequenced
   follow-up): `PhoneContract(output_format="national")` begins raising
   `ContractError`, and the message must name the shipped information-preserving
   successors.
3. **Language remediation is scheduled** (sequenced follow-up): map the primary
   subtag, carry the remaining subtags through unchanged — the BCP 47 equivalent of a
   re-encode-the-shared-part, preserve-the-rest successor. Bare-code canonicals
   (`en`, `deu`) are unaffected (nothing to drop).
4. **Suite hardening expectations** (sequenced follow-up): param-free rows for every
   capability's every offered format in `tests/property/test_reentry_invariant.py`;
   same-entity expansion fixtures (`AAAABBCC` / `AAAABBCCXXX`, EUI-48/EUI-64 pair)
   asserting merge-and-fixpoint; mandatory cross-entity pairs — Language
   `en-US` / `en-GB`, Phone GB/MY for any future NSN-style format, Coordinates
   sub-quantum neighbors.
5. **Promotion criteria for a future hard-mandate ADR** (not obligations of this one):
   a static `format_value` param-branching scan (rendering must not branch on
   validity-affecting contract params such as `default_country`); a sampled
   entity-injectivity gate; de-offer deadlines for waived violations.

Also: **de-offering a format is a breaking change requiring a migration note**
(ADR-0010 precedent, restated). Once a format is offered, callers may render values in
it; removing it changes the contract surface — callers still passing the format begin
to receive `ContractError` (`CapabilityContract.__post_init__`) — and must ship with a
migration note.

*Amendment (2026-09-06 — ADR-0011 Phase 3; corrected same day after review).*
Language option (b) landed for `alpha2`: it maps the primary subtag and
carries the remaining subtags verbatim, so extended tags render distinctly
(`en-US` → `en-US`) instead of colliding onto the bare primary — an
encoding with exact pre-image. `alpha3` / `alpha3-bib` were first shipped
with the same carry, but review found the carried renderings do not
re-enter: variant Prefix is primary-relative (``deu-CH-1901`` INVALID) and
deprecated/macrolanguage resolution is primary-relative (``zho-Hant-TW``
AMBIGUOUS) — including same-contract `W→W` failures, i.e. an ADR-0010
violation introduced by the carry. Both formats were therefore reverted to
primary-only renderings for extended tags (``de-CH-1901`` → ``deu`` /
``ger``), which re-enter as fixed points; they are waived projections
alongside `name` (subtag-carrying names are not lexicon keys). The narrow
exception is identity-mapped primaries (private-use ``x-foo``), which carry
verbatim since the rendering is the canonical itself. Revisit (de-offer vs.
mapping-aware validation vs. locale-aware name grammar) at the
hard-mandate promotion.

*Amendment (2026-09-06 — ADR-0011 Phase 4; suite hardening + deferred
fold-ins landed).* The soft mandate is now locked in CI: the Corollary 1–2
preservation matrix over every offered format per class
(``tests/property/test_output_format_preservation.py`` — encoding exact
pre-image, expansion merge-and-fixpoint, quantization param-free recovery;
registry-exception #4), the mandatory cross-entity injectivity pairs
(Corollary 1), the expansion fixtures (``DEUTDEFF``/``DEUTDEFFXXX`` under
``bic11``, the EUI-48/EUI-64 pair under ``eui64``), the class-declaration
scan (``tests/unit/test_offered_format_class_declarations.py`` — every
offered format named in its contract docstring with a class term), and the
``HOW_TO_ADD_NEW_CAPABILITY.md`` offered-format checklist. All shipped
formats are measured and classified; the waived set is exactly Language
``alpha3`` / ``alpha3-bib`` / ``name`` (amended above). **Promotion
readiness, not promotion**: the hard mandate (static ``format_value``
param-branching scan, sampled entity-injectivity gate as a merge blocker,
de-offer deadlines for the waivers) waits until every capability complies
and a new capability ships clean under the invariant — promoted by a
future ADR per this section's criteria.

## Alternatives Considered

1. **String-level injectivity.** Rejected: it condemns the audit's own PASS verdicts
   for `bic11` / `eui64`; the principled line is entity-relative (see Definitions).
2. **Runtime assertion in `run_capability()`.** Rejected: hot-path cost, duplicates
   what CI property tests prove per snapshot (ADR-0010 Alternative 1 precedent).
3. **Main clause only, no injectivity corollary.** Rejected: the corollary is what
   forces per-format class declarations and catches identity collisions that involve
   no recognition/validation bits; without it the taxonomy has no enforcement hook.
4. **De-offer `dms` / `dm`.** Rejected: their obligations are closed and cheap
   (quantum-ratio stability proof + bounded drift, pinned by Phase 0's suite);
   de-offer remains the documented fallback only if the obligations later break.

## References

- Issue #139 — origin of this ADR: the information-preservation invariant requirement
  and the Accepted-status scoping (Scope decision 1). (Number to be filled in at PR
  time.)
- ADR-0004 (Single-Value Invariant) — invariant-family root: an engine-level
  correctness property enforced by tests rather than hot-path checks.
- ADR-0010 (Re-entry Fixed-Point Invariant) — invariant-family predecessor: re-entry
  stays required; this ADR adds the value-relative corollaries (entity-relative
  injectivity, param-free or bounded-drift pre-image recovery) on top.
- `tests/property/test_coordinates_quantization.py` — Phase 0's landed artifact: the
  `dms` / `dm` fixpoint + bounded-drift properties this ADR's Corollary 2 exception
  relies on.
- `paxman/capabilities/Phone/contract.py:103-110` — the `national` construction gate
  (`default_country` requirement).
- `paxman/capabilities/Phone/capability.py:142-160` — the `national` render plus the
  NANP-only preservation branch.
- `tests/property/test_reentry_invariant.py:155-161` — the Phone row's
  `default_country` crutch.
- `paxman/capabilities/Language/capability.py:153-231` — the `_primary_language`
  projection shared by `alpha2` / `alpha3` / `alpha3-bib` / `name`.
- `paxman/capabilities/Coordinates/capability.py:39-78` — the `dms` / `dm` quanta.
- `paxman/core/capability_contract.py` — `DEFAULT_OUTPUT_FORMAT`,
  `OFFERED_OUTPUT_FORMATS`, and the `resolve_output_format` seam where quanta and
  class declarations live.
