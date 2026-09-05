# Output-Format Information Preservation — Soft-Mandate Invariant Study — paxman-python

**Date:** 2026-09-05
**Amended:** 2026-09-06 — review amendments: (1) the formal invariant statement is corrected to **entity-relative** injectivity with a four-class format taxonomy (§2, §8.1), so the audit's PASS verdicts for `bic11`/`eui64` no longer contradict the formal statement; (2) Coordinates `dms`/`dm` are reclassified from BORDERLINE to **documented quantization** — keep with declared quanta and locked stability properties, de-offer demoted to fallback (§7.2); (3) the Phone defect framing is made precise — param dependence and value-dependent shape are live, the GB/MY collision is latent behind the preservation branch (§3, §4.2); (4) a sequencing section for plan synthesis was added (§13).
**Scope:** Research report proposing a new soft-mandate (hard-mandate later) invariant: an `output_format` must be an equal representation of the canonical value — it must not remove information from the canonical value when that information is used for recognition or validation or both. Applies the invariant to the direction change that `phone` de-offers `output_format="national"`, audits all 18 shipped capabilities for the same violation class, and uses the requester's compact / loose / split phone examples purely as non-binding illustrations of what an information-preserving replacement looks like (not acceptance criteria; the implementer chooses the final replacement set). No source code, tests, or configuration were modified.
**Evidence basis:** Verbatim shipped code read 2026-09-05 — all 18 `paxman/capabilities/*/contract.py` (`DEFAULT_OUTPUT_FORMAT` / `OFFERED_OUTPUT_FORMATS`) and all 13 `format_value()` implementations; `paxman/capabilities/Phone/{contract,capability,notation}.py`, `rules/{e164_ed2010,nanp_ed2024}.py`, `rules/data/e164_country_codes.py`; `paxman/capabilities/Language/{capability,contract,notation}.py`; `paxman/capabilities/Coordinates/{capability,contract}.py`; `paxman/capabilities/BIC/{capability,contract}.py` + `rules/iso_9362_ed2022.py`; `paxman/core/{contract,capability_contract}.py` (`resolve_output_format`); `docs/adr/0010-re-entry-fixed-point-invariant.md`; `tests/property/test_reentry_invariant.py` (18 rows); `tests/capabilities/phone/test_capability.py` (`TestPhoneNationalOutput`, `test_national_requires_default_country`). Repo state: `dev @ 6ba875a`.
**Conventions grounding this report:** HOW_TO_ADD_NEW_CAPABILITY.md (presentational-only invariant, `format_value` seam, rules never read `output_format`), ARCHITECTURE.md (determinism, MISSING vs INVALID vs AMBIGUOUS), ADR-0007 (contract unification), ADR-0010 (re-entry fixed point), `paxman/capabilities/AGENTS.md`, `docs/development/AGENTS.md` (this directory is ephemeral, not shipped, not referenced by code).

---

## Executive Summary

`output_format` is defined as another equal representation of the canonical value. Phone `national` violates that definition: it strips the country code (CC) that recognition and validation both depend on, and leans on `default_country` to make the truncated value re-enter. The truncation is not an encoding — it is a projection, and projections collide.

Verdict and direction change:

1. **Phone de-offers `national`.** The format removes the country code (CC) — the exact field `split_country_code` / `valid_e164_value` use for routing and validation — and re-enters only because the contract carries the missing information as a parameter (`national` requires a NANP `default_country` at construction). Its live defects: it is the only offered format in the repo that cannot re-enter under its **default** contract (param dependence), and its output shape depends on the value (`+1…` renders as bare NSN, `+44…` renders as E.164 under the same format name). The headline collision — `+4412341234` and `+6012341234` both rendering `12341234` — is **latent, not live**: the preservation branch avoids it by refusing to render non-NANP values at all, which is itself the defect (a format safe only by refusing most of its value space is not an equal representation of it; §3, §4.2, Appendix). Re-entry passes; equality fails. The format is removed from `OFFERED_OUTPUT_FORMATS` with a migration note (ADR-0010 Consequences: de-offering is breaking).
2. **Illustrative replacement direction (suggestion only, not criteria).** The requester's examples show the shape of a compliant replacement — e.g. canonical `+4412341234` equally represented as compact `4412341234`, loose `+44 1234 1234`, or split `+44 12341234`. Each preserves the CC, re-enters under the default (country-less) contract, and needs no `default_country`. The final replacement set is the implementer's choice; §5 works these examples only to prove the compliance pattern. Recognition input (domestic dialing via `default_country`) is untouched — this change is output-only.
3. **The rule generalizes to a soft-mandate invariant, hard later.** No offered format may remove canonical information used for recognition or validation or both; injectivity is **entity-relative** — no two canonicals of *different entities* may share a rendering, while documented same-entity merges (expansions) and declared-precision quantizations are permitted classes with their own obligations (§8.1). Soft now: new formats must comply and declare their class; existing violations are listed with migration plans and a warning-level audit. Hard later: CI gates (static scan + entity-relative injectivity / param-free pre-image property tests) fail violating formats.
4. **Same-category audit: Language is the second violator; Coordinates dms/dm is a documented quantization (not a violation).** Language `alpha2` / `alpha3` / `alpha3-bib` / `name` drop region/script/variant subtags that BCP 47 syntax and IANA-registry validation both use (`en-US` → `en`) — and `en-US`/`en-GB` are different entities sharing a rendering, so entity-relative injectivity still catches it. It passes ADR-0010 (the truncated value re-enters to itself) while changing the entity — the same hole as Phone, without even needing an extra contract param to hide it. Coordinates `dms` / `dm` remove no field and no recognition/validation bit; they render at a declared display unit (arcsecond / 0.001 minute), merging canonicals only below that unit — reclassified as **documented quantization**: keep, with the quantum declared at the contract seam and the render-stability + bounded-drift properties locked in CI (§7.2). All other 16 capabilities pass (details in §6).
5. **Sequencing is fixed for plan synthesis (§13).** ADR-0011 (the invariant) is the must-implement and lands first; Coordinates' quantum declarations + stability properties land pre-ADR (cheap, and the ADR cites them); Phone de-offer is the directed post-ADR breaking change; Language remediation (option b) follows; suite hardening completes the soft mandate; hard CI gates are deferred to a promotion ADR.

---

## 1. Target User

| Persona | Why they need this invariant | Typical context |
|---|---|---|
| Phone caller (any country) | Stores `+44…` canonicals, renders them for display, re-imports the rendered string without remembering which `default_country` produced it | CRM export / re-import, dedup keys |
| Pipeline engineer | Renders canonicals in one job, canonicalizes rendered strings in another job with a default contract | ETL, record linkage |
| Library contributor | Adds an offered format and needs a checkable rule for whether it is legal | New capability or new rendering |
| Paxman maintainer | Needs the audit table plus a soft→hard enforcement path that does not break callers overnight | Release planning, CI gates |

**User-visible contract after this change:** `PhoneContract(output_format=…)` accepts `None` / `"default"` / `"e164"` / `"rfc3966"` / whatever information-preserving replacement set the implementer ships; `"national"` raises `ContractError` with a migration message. Domestic *input* (`(201) 555-0123` + `default_country="US"`) keeps working — only the lossy *output* is removed.

---

## 2. Definitions

- **Canonical value `V`.** The default-format string produced by `Rule.normalize()` (e.g. Phone `+4412341234`, Language `en-US`, Country `US`). Identity of the entity as the authority defines it.
- **`output_format` as equal representation.** A function `F` over canonicals such that `W = F(V)` encodes the same entity as `V`: distinct canonicals map to distinct renderings (injectivity over the canonical space), and every piece of `V` that any grammar uses to recognize it or any rule uses to validate it is recoverable from `W` alone — no extra contract parameter, no caller memory.
- **Recognition information.** Bits of `V` that determine whether a grammar claims a span (charset, length, prefix, separators that guards key on). Phone CC digits determine `split_country_code` routing and the E.164 window; BCP 47 subtags determine tag-grammar structure.
- **Validation information.** Bits of `V` that determine whether a rule returns `True` (assigned-CC lookup, NSN length floor, BCP 47 syntax, IANA registry membership, MOD check). Removing them changes the validation verdict or changes which rule validates.
- **Entity vs canonical spelling.** An *entity* is what the governing authority says a canonical value denotes. Two distinct canonical strings may denote the same entity: ISO 9362 makes the branch code implicit (`AAAABBCC` ≡ `AAAABBCCXXX`), and IEEE's EUI-48→EUI-64 derivation (`FF:FE` insertion) links a 48-bit MAC to its 64-bit form. By contrast, `en-US` is not "`en` with the region made explicit" — per BCP 47 the subtags change what the tag identifies, so `en-US` and `en` (and `en-GB`) are different entities. Injectivity in this invariant is defined over entities, not strings.
- **Format classes.** An **encoding** is reversible without side input (`electronic` ↔ `paper` by space strip/insert; `hyphenated` ↔ `compact` by hyphen strip). A **same-entity expansion** makes an implicit default explicit (`AAAABBCC` → `AAAABBCCXXX`; EUI-48 → EUI-64): it merges two spellings of one entity — permitted, documented, fixed-point. A **documented quantization** renders at a declared display unit, discarding a contiguous low-order magnitude range and nothing else (`dms` at the arcsecond; `dm` at 0.001 min): many-to-one below the declared unit, bounded-drift, render-stable. A **projection** drops a semantic field (`+CCNSN` → `NSN`; `en-US` → `en`) or discards bits with no declared quantum, and is reversible only with side input (`default_country`) or not at all.

The mandate: **offered formats must be encodings, same-entity expansions, or documented quantizations — never projections over recognition/validation information.** Presentation-only changes (spacing, grouping, wrapping, case, reordering that preserves all fields) are encodings. The dividing line between quantization and projection: a quantization discards a magnitude tail below a *declared unit of the format*; a projection discards a *field*, or bits with no unit declared. Field removal is banned — first softly, then hardly.

---

## 3. Why ADR-0010 Re-entry Is Necessary but Insufficient

ADR-0010 Property 2 requires `canonicalize(V, C) == V` under the same contract `C` that produced `V`. Phone `national` satisfies it — conditionally:

- `C = PhoneContract(output_format="national", default_country="US")`, `I = "+12125551234"` → `V = "2125551234"`. Re-entry `canonicalize("2125551234", C)` → national grammar claims 10 digits, NANP rule validates under `default_country="US"`, normalizes to `+12125551234`, renders `national` → `"2125551234"`. Fixed point holds. Locked in `tests/property/test_reentry_invariant.py:161` and `tests/capabilities/phone/test_capability.py:335-360`.
- The trick is in `C`. Without `default_country="US"`, construction raises `ContractError` (`contract.py:103-110`); without the NANP-only preservation branch (`capability.py:154-159`), non-NANP `V` would degrade to `MISSING`/`INVALID`. The format re-enters only because the contract carries the missing information as a parameter.

Three defects survive a passing re-entry check — two live, one latent:

1. **Param dependence (self-description failure) — live.** `W` alone is not a value — `(W, default_country)` is. Every other offered format in the repo re-enters under the default (param-free) contract; `national` is the only one that cannot (`PhoneContract(output_format="national")` raises). A format that needs a side channel to be readable is not another representation of the value; it is a fragment plus an instruction.
2. **Value-dependent output shape — live.** Under one format name, `+1…` renders as bare NSN and `+44…` renders as E.164 (the preservation branch, `capability.py:154-159`). A caller cannot predict the shape of `W` from `F` alone — it depends on the value's CC. Encodings are uniform; the branch is an admission that the format is not one.
3. **Collision (entity-injectivity failure) — latent, one naive fix away.** If the preservation branch were "completed" the natural-looking way — render the NSN for every assigned CC, not just `"1"` — then `F(+4412341234) = "12341234" = F(+6012341234)`: one `W`, two different entities, and dedup keys merge distinct phone numbers. As shipped, the branch prevents this by refusing to render non-NANP values as NSN at all — the format avoids the live collision only by being a partial function over its own value space (`F_national` is string-injective over the values it accepts today). Safety by refusal is the defect, not a defense: the moment anyone "fixes" the asymmetry, the collision ships. An equal representation must not be one naive edit away from non-injective.

Hence the new invariant strengthens ADR-0010 rather than repeating it: re-entry stays required, and additionally the re-entry must hold **without recognition/validation information supplied outside `W` itself**. Re-entry is contract-relative; information preservation is value-relative; injectivity is entity-relative (§2, §8.1).

---

## 4. Phone Case Study — Proof of Violation

### 4.1 Current behavior (verbatim)

- Default canonical: `normalize()` returns `f"+{value}"` (`e164_ed2010.py:97,137`); E.164 validity = digits-only, ≤15 digits, longest-prefix assigned CC via `split_country_code`, NSN ≥ 2 (`e164_ed2010.py:35-54`).
- `national` rendering: strip leading `+`, split CC, return NSN only when CC == `"1"`, else preserve E.164 (`capability.py:149-160`). Contract gate: `national` requires `default_country in PHONE_NATIONAL_COUNTRIES (={"US"})` (`contract.py:103-110`, mirroring `nanp_ed2024.py:34`).
- Domestic input path (unchanged by this proposal): `NationalGrammar` claims NANP 3-3-4 shape (`national_recognition.py`), NANP rules validate only when `default_country` is a NANP country (`nanp_ed2024.py:108-113`), normalize to `+1NSN`.

### 4.2 Collision table (the user's example, generalized — latent-class illustration, not live behavior)

The GB/MY rows below show the collision *class* the format belongs to, not behavior that ships today: as shipped, the preservation branch renders non-NANP values as E.164, so no live cross-country collision exists (§3 defect 3). The table is what ships the moment the branch is naively extended — which is why the format is de-offered rather than "completed."

| Input | Default canonical `V` | `national` rendering `W` | `W` re-entered under… | Result |
|---|---|---|---|---|
| `+44 1234 1234` (GB, illustrative NSN) | `+4412341234` | `12341234` | `C(default_country="GB")` (if GB national existed) → `+4412341234` | resolves — but only with GB memory |
| `+60 1234 1234` (MY, illustrative NSN) | `+6012341234` | `12341234` | `C(default_country="MY")` → `+6012341234` | same `W`, different `V` — collision |
| `12341234` stored bare | — | — | default (country-less) contract → `INVALID` (recognized, no rule validates without country) | fragment, not a value |

The CC (`44` vs `60`) is used by `split_country_code` (recognition routing) and `valid_e164_value` (assigned-CC validation). `national` removes exactly that field. Under the proposed invariant this is the textbook violation: removed information ∩ (recognition ∪ validation) ≠ ∅.

### 4.3 Why the NANP-only preservation branch does not save it

`capability.py:154-159` preserves E.164 for non-NANP input under a NANP contract so re-entry holds. That converts the violation from "wrong value" to "inconsistent value": NANP numbers render as fragments, everything else renders as E.164, under the same format name. A caller cannot predict the shape of `W` from `F` alone — it depends on the value's CC. Encodings are uniform; this branch is an admission that the format is not one.

---

## 5. Phone Replacement Shape — Worked Illustration (suggestion, not criteria)

> The compact / loose / split examples below are the requester's suggestions, reproduced to show what compliance looks like. They are not acceptance criteria and do not constrain the implementer: any replacement set satisfying §8.1 (injectivity + param-free pre-image round-trip, CC preserved) is compliant, whether it matches these three names/shapes or not.

Canonical stays `+CCNSN` (E.164 with leading `+`). Illustrative compliant shapes, each an encoding (string-injective over the canonical space with no same-entity merges, param-free re-entry):

| Format | Definition (from canonical `+CCNSN`) | Example (`+4412341234`) | Inverse (recognition-side) |
|---|---|---|---|
| `compact` | Strip the leading `+` only: `CCNSN` digits | `4412341234` | E.164/`00` path: digits with assigned-CC prefix; grammar claims digit run with known CC, rule validates via `split_country_code`. Re-enters with no contract param. |
| `loose` | `+CC` + single space + grouped NSN as dialed-display (`+44 1234 1234`) | `+44 1234 1234` | Separator-skipping E.164 scan (`[\s.\-]` tolerance already shipped in `e164_recognition.py`): strip separators → canonical digits. Spaces are presentation-only, never validation input. |
| `split` | `+CC` + single space + compact NSN (`+44 12341234`) | `+44 12341234` | Same separator-strip as `loose`, one space. Unambiguous CC/NSN boundary recovered by longest-prefix `split_country_code` — the same function validation already uses. |

Why each passes the invariant:

- **No field removed.** CC, NSN, `+` (or its positional equivalent) all survive. `compact` drops only the `+` sigil while keeping every digit — the digit string plus the assigned-CC table recovers the CC/NSN split deterministically (longest-prefix match, the exact function validation uses). `loose`/`split` drop nothing at all; they add one space.
- **Param-free re-entry.** Each `W` is claimed by the country-agnostic E.164 grammar and validated by the country-agnostic E.164 rules — no `default_country`, no NANP gate, no preservation branch. `canonicalize(W, default_contract) == V` for every assigned CC, not just `"1"`.
- **Injective.** Distinct `V` map to distinct `W` within each format (digit strings differ, or `+CC` prefixes differ). No GB/MY collision is expressible.

Notes:

- Names `compact` / `loose` / `split` are the requester's illustrative labels, not mandated names or shapes; bikeshedding (e.g. `e164_compact`, `e164_spaced`, `cc_split`) is §12 OD-2, and shipping fewer, more, or differently-grouped preserving formats is compliant provided each satisfies §8.1 (entity-relative injectivity, param-free pre-image, CC preserved).
- `rfc3966` (`tel:+CCNSN[;ext=]`) already passes and stays offered — it wraps, never strips.
- Domestic *input* recognition (`NationalGrammar`, `default_country`-gated NANP rules) is orthogonal and stays. The invariant constrains outputs; inputs legitimately need context (`default_country` is a validity-affecting parameter per HOW_TO_ADD_NEW_CAPABILITY.md §5d). Removing lossy output does not remove domestic input support.
- Migration: `national` removal is breaking per ADR-0010 Consequences — `PhoneContract(output_format="national")` begins raising `ContractError` with a migration message pointing at `split` (closest visual successor for NANP callers: `2125551234` → `+1 2125551234`). Deprecation shim (warn-then-raise over one minor) vs immediate removal is §12 OD-5.

---

## 6. Full Capability Audit — All 18 Offered Surfaces

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

Single-format capabilities (Currency, Email, IP, SIUnit, URL) cannot violate the invariant — there is no second representation to lose information in.

---

## 7. Same-Category Deep Dives

### 7.1 Language — the second violator (projection without even a param)

`LanguageCapability.format_value` (`Language/capability.py:153-231`) reduces any canonical tag to its primary subtag (`_primary_language`: split on `-`, lower) before mapping: `en-US` → `en`, `zh-Hant-TW` → `zh`, `de-CH-1901` → `de`. The dropped subtags (region `US`/`CH`/`TW`, script `Hant`, variant `1901`) are recognition information (BCP 47 tag grammar structure) and validation information (BCP 47 syntax rule + IANA subtag-registry membership for region/script/variant). `alpha2`/`alpha3`/`alpha3-bib`/`name` then render only the primary language — four offered formats sharing one projection.

Why it is the same category as Phone but harder to see: Phone's projection needs `default_country` to re-enter, which made the violation visible as a construction gate. Language's projection re-enters silently — `canonicalize("en", C(alpha2))` succeeds and lands on `"en"` — because the truncated value is itself a valid smaller entity. ADR-0010's `V→V` check passes while the entity changed (`en-US` ≠ `en`). Re-entry proves the rendering is stable; it does not prove it is equal. The invariant catches what re-entry misses: `F(en-US) == F(en-GB) == "en"` collides exactly like `F(+44…) == F(+60…)`.

Remediation options (for the plan, not this report): (a) scope the four formats to primary-language canonicals only and document extended-tag behavior (render primary with a documented-projection warning — still a projection, so soft-mandate waiver with migration path); (b) extend the formats to preserve subtags (e.g. `alpha2` renders `en-US` as `en-US`, mapping only the primary part — encoding, not projection); (c) de-offer for extended tags. Recommendation is (b): map the primary subtag, carry the remaining subtags through unchanged — the BCP 47 equivalent of Phone's `split` (re-encode the shared part, preserve the rest). Bare-code canonicals (`en`, `deu`) are unaffected in all options (nothing to drop).

### 7.2 Coordinates `dms` / `dm` — documented quantization (not a violation; obligations instead)

`_decimal_to_dms_parts` quantizes seconds to integer half-even; `_decimal_to_dm_parts` quantizes minutes to 0.001 (`Coordinates/capability.py:39-78`). Classification (per §2's taxonomy): no field is removed and no recognition/validation bit is removed — the recognition layer itself already quantizes latitude/longitude to 6 dp, `ROUND_HALF_EVEN` (`_quantize`, `coordinates_recognition.py:139-143`), so sub-arcsecond magnitude is never recognition or validation input, and range validation (`±90`/`±180`) never branches on it. What `dms`/`dm` do is render at a **declared display unit** — the arcsecond (≈ 2.78e-4°) for `dms`, 0.001 minutes for `dm` — which makes them many-to-one over the canonical space (51.507400 and 51.507412, distinct canonical points ~1.3 m apart, both render `51°30′27″N`). That is quantization, not projection: the discarded bits are a contiguous magnitude tail below a declared unit of the format, whereas `national`/Language discard semantic fields with no unit anywhere in sight. The earlier BORDERLINE verdict is resolved in favor of **keep, as the charter members of the documented-quantization class**, with two obligations replacing the earlier "proof or de-offer" framing:

1. **Render stability (fixpoint) — provable now, lock it in CI.** The canonical quantum (1e-6° ≈ 0.0036″) is three orders of magnitude below the half-second rounding boundary (0.5″): a re-parse of an integer-second `W` lands within ±0.0018″ of that second, so render → parse → render can never cross a render boundary. The same argument covers `dm` (render quantum 0.001 min = 0.06″ vs ≤ 3e-5° re-parse error) and the carry cases already exercised by `test_dms_sec_and_minute_carry`. The reason this is a CI obligation rather than a one-time proof: the argument depends on the **ratio** of the canonical quantum to the render quantum — a future change to the canonical quantum (e.g. 7 dp) could silently break it, so the property must be pinned, not assumed.
2. **Bounded-drift pre-image (documented, not exact).** `canonicalize(W, default_contract)` does not return the pre-image `V`: `canonicalize("51°30′27″N")` = `51.507500`, not `51.507412` — a stored `W` re-imported under the default contract shifts by up to half a render quantum (≈ 1.39e-4° ≈ 140 canonical quanta ≈ 1.3 m at the equator), deterministically and silently. This is acceptable **iff declared**: the caller who requests `dms` is opting into arcsecond display precision. The obligations are (a) the quanta documented at the contract seam (contract docstrings + CONTEXT/README tables), and (b) the ADR's pre-image corollary carrying an explicit exception for declared-quantization formats: exact pre-image for encodings/expansions, bounded-drift (≤ ½ render quantum) for documented quantizations. Do not let the `W→W` fixpoint stand in for the `W→V` claim — they are different properties, and only the first holds exactly.

De-offer (`dms`/`dm` demoted to display helpers outside `OFFERED_OUTPUT_FORMATS`) remains the fallback if either obligation proves unmeetable, but it is no longer the default outcome. `iso6709` / `geo_uri` / `geojson_pair` are unaffected (lossless re-encodings — `iso6709` keeps fraction digits whole and pads to 4 places, `_pad_fraction`, `capability.py:81-88`; altitude preserved including sign handling).

### 7.3 Explicit non-violators commonly suspected

- **Country `name`/`alpha3`/`numeric`.** All ISO 3166-1 codes for the same entity; conversion tables are total over current assignments; historical codes without mappings pass through unchanged rather than mis-mapping. No extra contract param; each rendering re-enters via its own grammar. Encodings — keep.
- **BIC `bic11`, MacAddress `eui64`.** Expansions (add `XXX` / `FF:FE`), not removals. Deterministic, fixed-point, documented. They are **not string-injective** — `F_bic11(AAAABBCC) = F_bic11(AAAABBCCXXX) = "AAAABBCCXXX"`, and the EUI-64 rendering of a 48-bit MAC equals that 64-bit canonical's identity rendering — but the merged canonicals denote the **same entity** per the authority (ISO 9362 implicit branch code; IEEE derivation). This is exactly why §8.1 defines injectivity entity-relative: under string-level injectivity these PASS verdicts would contradict the formal statement, and a literal CI gate would flag `bic11` the first time it samples the pair. Obligations: the same-entity pairs become fixtures in the property gate asserting merge-and-fixpoint (they may share a rendering; each rendering must re-enter to itself), and the expansion semantics stay documented in the contract. Keep with existing docstrings as the model for documenting asymmetric-but-safe formats.
- **Money `compact`.** Separator removal where the separator is provably unique (ASCII space vs U+202F in amounts, documented in `Money/capability.py:104-114`). Keep.

---

## 8. The Invariant — Soft Now, Hard Later

### 8.1 Formal statement (proposed)

> **Information-Preservation (output-format equality).** For every capability, for every `F ∈ OFFERED_OUTPUT_FORMATS`, for every default canonical `V` the capability can produce: `W = format_value(V, F, notation)` must preserve every bit of `V` used by any shipped grammar to recognize `V`'s form or any shipped rule to validate `V` — recoverable from `W` alone under the default (param-free) contract. Corollaries:
>
> 1. **Entity-relative injectivity.** For all canonicals `V1 ≠ V2` denoting **different entities** (§2), `F(V1) ≠ F(V2)`. Same-entity spelling merges are permitted only as documented same-entity expansions (`AAAABBCC`/`AAAABBCCXXX` under `bic11`) and must be fixed-point. String-level injectivity is deliberately *not* required — it would condemn this audit's own PASS verdicts for `bic11`/`eui64` (§7.3).
> 2. **Param-free pre-image re-entry** (stronger than ADR-0010's same-contract `V→V`): `canonicalize(W, default_contract)` succeeds and returns the pre-image `V` — **exact** for encodings and same-entity expansions, **bounded-drift** (within ½ of the declared render quantum, deterministic) for documented quantizations. No offered format may require a contract parameter to make its own output readable.
>
> Classification clause: every offered format belongs to exactly one class — encoding, same-entity expansion, or documented quantization — declared in the capability (contract docstring), with the class's obligations attached. Projections are not offered.

Scope notes: constrains offered formats only (defaults are identity by construction); snapshot-relative like determinism/re-entry (authority-table evolution may change which `V`s exist, never whether `F` preserves them); entity is authority-relative and snapshot-relative too (which spellings denote one entity is decided by the capability's authority data, not the engine); engine enforces nothing at runtime (off-hot-path, ADR-0010 Consequences precedent).

### 8.2 Soft mandate (now — this report lands it)

- New offered formats must satisfy §8.1 with a class declaration (encoding / same-entity expansion / documented quantization), a param-free re-entry + entity-relative injectivity argument in the capability's test module (or a waiver citing this report's audit), and — for documented quantizations — the declared quantum plus render-stability and bounded-drift property tests.
- Existing violations carry migration plans, not immediate removal (except Phone `national`, directed): Language projection documented with options (§7.1); Coordinates `dms`/`dm` are not violations — they are documented quantizations whose declarations and stability properties land pre-ADR (§7.2, §13 Phase 0).
- Audit (§6) published in this directory; no CI failures added. Reviewers cite this report (allowed: reviewer clarifying a point per `docs/development/AGENTS.md` PR policy) to block new projections.

### 8.3 Hard mandate (later — promotion criteria)

- CI gate: (i) existing `output_format` purity scan stays (rules never read the field); (ii) new static scan — `format_value` bodies must not branch on validity-affecting contract params (`default_country`, `dollar_sign_currency`-class resolvers) to select renderings (the `default_country`-dependent render is the Phone smell); (iii) property gate — per offered format, sampled canonicals round-trip through the default contract to their pre-image (bounded-drift for declared quantizations), **different-entity** sampled pairs render distinctly (mandatory cross-entity pairs: Phone GB/MY, Language `en-US`/`en-GB`, Coordinates sub-quantum neighbors), and declared same-entity expansion pairs assert merge-and-fixpoint rather than distinctness.
- De-offer deadlines for waived violations (Language, Coordinates-pending-proof) with ADR-0010 migration notes (callers passing a removed format get `ContractError` — breaking, announced).
- Promotion itself recorded as an ADR (re-entry family, after ADR-0010) — `docs/development/` reports never bind shipped behavior; the ADR does.

---

## 9. Enforcement Design (no hot-path cost)

| Layer | Check | Catches |
|---|---|---|
| Static scan (new, unit layer) | `format_value` must not read validity-affecting contract fields to choose/drop fields (`default_country`, amount/currency resolvers) | Param-dependent renders (Phone `national` pattern) |
| Property test (extend `test_reentry_invariant.py`) | Param-free pre-image round-trip: `canonicalize(F(V), default_contract)` → `V` (bounded-drift for declared quantizations); entity-relative injectivity: different-entity pairs render distinctly (GB/MY, `en-US`/`en-GB` mandatory); same-entity expansion fixtures assert merge-and-fixpoint | Collisions (Language `en-US`/`en-GB`; latent Phone GB/MY) and same-entity false positives (bic11/eui64 pairs) |
| Quantization properties (Coordinates `dms`/`dm`) | Render→parse→render fixpoint + bounded-drift bound (≤ ½ declared render quantum), locked pre-ADR; guards the canonical-quantum : render-quantum ratio the stability proof depends on | Silent breakage of the dms/dm stability argument under a future canonical-quantum change |
| Review checklist | New `OFFERED_OUTPUT_FORMATS` entry ships with encoding argument + cross-entity pair test | Future projections blocked at review under soft mandate |

Deliberately not runtime: like ADR-0010, the invariant is a property of capability data + formatter, re-proved per snapshot in CI, never re-checked per call.

---

## 10. Migration Plan — Phone `national` Removal

1. **Announce + deprecate.** Changelog + migration note: `national` → whichever preserving successor the implementer ships (the §5 `split` illustration, `+1 2125551234`, is one compliant option for NANP callers previously receiving `2125551234`; the final mapping is the implementer's choice). `ContractError` message for `national` names the shipped successor(s).
2. **Remove from `OFFERED_OUTPUT_FORMATS`; delete the preservation branch** (`capability.py:154-159`) and the construction gate (`contract.py:103-110`); derive nothing (no replacement mirror constant). `default_country` stays for *input* (domestic recognition) — output no longer consults it.
3. **Add the implementer's chosen preserving successor(s)** per the §5 compliance pattern (injectivity + param-free re-entry; CC preserved) with param-free re-entry rows in `test_reentry_invariant.py` (default contract, no `default_country`) plus GB/MY-style cross-entity injectivity tests. The §5 trio is one compliant option, not the required set.
4. **Update capability tests** (`TestPhoneNationalOutput` → successor-format suites; `test_national_requires_default_country` retires with the format), docs tables (CONTEXT/README where phone formats are listed — shipped docs, not this directory), and the re-entry row comment (the `default_country="US"` crutch on the Phone row goes away: the row becomes param-free like every other capability).
5. **Follow-ups under the same mandate:** Language remediation option (b) scoped and scheduled; Coordinates quantum declarations + stability property tests land pre-ADR (§13 Phase 0); hard-mandate ADR drafted once Phone + Language land.

---

## 11. Risks & Mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Removing `national` breaks callers rendering NSNs | Breaking-change discipline per ADR-0010 (migration note, `ContractError` guidance, `split` successor); soft→hard pacing applies to the mandate, the directed Phone removal ships with the note |
| 2 | `compact` (bare digits, no `+`) looks like another projection | Distinguish sigil from field: `+` is recovered positionally (longest-prefix CC split, the validation function itself); property gate proves it. Document the sigil-vs-field distinction in the hard-mandate ADR |
| 3 | Language remediation scope (4 formats × extended tags) | Option (b) preserves subtags — additive change to renderer, no grammar/rule churn; bare-code behavior unchanged |
| 4 | Coordinates obligations unmeetable later (the quantum-ratio stability argument could drift if the canonical quantum ever changes) | De-offer fallback retained; the pinned CI properties make any breakage loud, not silent; `decimal`/`iso6709`/`geo_uri`/`geojson_pair` already cover lossless needs |
| 5 | Over-scoping: reviewers apply the invariant to inputs (`default_country` itself) | State explicitly: inputs may need context; the invariant constrains *outputs*. `default_country`-gated recognition stays legitimate |
| 6 | Injectivity sampling misses a collision pair | Mandate cross-entity pairs per capability in the property gate (Language `en-US`/`en-GB`, Phone GB/MY for any future NSN-style format, Coordinates sub-quantum neighbors); enumerate same-entity expansion fixtures separately (bic11, eui64) so the gate tests merges and distinctness with the right expectation each |

---

## 12. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|---|---|---|
| 1 | Phone successor set: §5 trio (compact/loose/split) vs minimal single vs other preserving set | **Implementer's choice — any set satisfying §8.1**; §5 trio is one compliant illustration | The invariant constrains properties (injectivity, param-free round-trip, CC preserved), not the count or labels of successors |
| 2 | Successor names | Illustrative only — keep the requester's `compact` / `loose` / `split` labels only if the implementer adopts those shapes; otherwise name per the shipped semantics and document exact definitions in contract docstrings | Labels are free; §8.1 properties are what the gate checks |
| 3 | Deprecation shim vs immediate removal of `national` | **Immediate removal with migration note** (directed change) | A warn-then-raise shim prolongs the collision window for stored fragments; ADR-0010 already treats de-offer as announced-breaking |
| 4 | Language remediation option | **(b) preserve subtags** (map primary, carry rest) | Only option satisfying the invariant without de-offering four formats; waiver otherwise |
| 5 | Coordinates `dms`/`dm` disposition | **Keep as documented quantization** — declare quanta at the contract seam, lock render-stability + bounded-drift property tests; de-offer demoted to fallback | The stability proof is closed and cheap (§7.2) and the invariant's main clause (recognition/validation bits) is not implicated; exact pre-image is replaced by a documented bounded-drift promise for declared-quantization formats |
| 6 | `bic11` / `eui64` expansions under the hard mandate | **Allow documented same-entity expansions** (additive, fixed-point, no removal) | Invariant bans removing validation info, not making implicit defaults explicit; injectivity is entity-relative, so these merges are compliant — the formal statement (§8.1) must say so or contradict this audit |
| 7 | Hard-mandate vehicle | **ADR + CI gates** (§8.3), not another development report | `docs/development/` is ephemeral per its AGENTS.md; binding rules live in ADRs and tests |
| 8 | Grandfathering other projections discovered later | **Audit-then-deadline** (soft waiver → hard removal) | Same pacing as Language/Coordinates; no silent permanent waivers |

---

## 13. Implementation Sequencing (Input to Plan Synthesis)

The plan writer synthesizes implementation steps and open questions from this report; this section fixes the order and the *why* of each work item without prescribing steps. One item is mandatory (the ADR); the rest are recommended and ordered by dependency. Open questions remain in §12; sequencing decisions here are recommendations a plan may revisit with rationale.

| # | Phase | What | Why it must be done (and why here) | Depends on |
|---|---|---|---|---|
| 0 | Pre-ADR (independent, cheap) | Coordinates quantization obligations: declare the `dms`/`dm` render quanta at the contract seam (contract docstrings + CONTEXT/README tables); add property tests for render→parse→render fixpoint and bounded-drift (≤ ½ render quantum), including the carry boundaries (`test_dms_sec_and_minute_carry` already exercises the carry path) | The ADR will classify `dms`/`dm` as compliant documented quantizations and cite these properties (§7.2); they must be locked before the ADR cites them. The stability argument depends on the *ratio* of canonical quantum (1e-6°) to render quantum — pinning it in CI protects the classification against future canonical-quantum changes. Docs + tests only; no shipped-code change | — |
| 1 | **The ADR (must implement)** | `docs/adr/0011-*.md` — Information-Preservation (Output-Format Equality) Invariant: entity-relative injectivity; the four-class taxonomy (§2); param-free / bounded-drift pre-image corollary; classification clause for offered formats; soft mandate + hard-promotion criteria (§8); the §6 audit as the baseline violation ledger; explicit relationship to ADR-0010 (strengthens — re-entry stays required — does not amend) | `docs/development/` is ephemeral; only an ADR binds shipped behavior. Every later change cites it — the soft mandate (§8.2) gives reviewers the citation to block new projections, and the directed Phone change needs the ADR to exist before the breaking removal lands | Phase 0 (so the dms/dm classification is evidenced, not asserted) |
| 2 | Post-ADR — directed breaking change | Phone `national` de-offer + implementer's-choice successor set per §5/§8.1: remove preservation branch + construction gate, add successors, param-free re-entry row (the `default_country="US"` crutch on the suite row retires), GB/MY cross-entity injectivity tests, migration note + `ContractError` naming successors, CONTEXT/README tables | The removal is justified *by* the invariant; ADR-0010 discipline applies (de-offer = announced breaking). Landing it before the ADR inverts governance — a development report cannot direct a breaking change | Phase 1 |
| 3 | Post-ADR — same-category remediation | Language option (b) (§7.1): map the primary subtag, carry remaining subtags through, across `alpha2`/`alpha3`/`alpha3-bib`/`name`; cross-entity pairs (`en-US`/`en-GB`, `zh-Hant-TW`-class) into the property suite; bare-code behavior unchanged (no-op) | Closes the second, silent violator (entity change without even a param to reveal it). Additive and lower-risk than Phase 2 but touches four offered formats' extended-tag behavior, so it needs its own re-entry + injectivity rows | Phase 1; may run parallel to Phase 2 (different capability, no shared code) |
| 4 | Post-ADR — soft-mandate completion | Suite hardening in `tests/property/test_reentry_invariant.py`: param-free rows for every capability's every offered format; same-entity expansion fixtures (`AAAABBCC`/`AAAABBCCXXX`, eui64 pair) asserting merge-and-fixpoint; review-checklist codification — a new `OFFERED_OUTPUT_FORMATS` entry ships with a class declaration + encoding argument | These are the soft-mandate obligations (§8.2), not CI gates; landing them makes the hard-mandate promotion (§8.3) a mechanical flip rather than new engineering | Phases 2–3 |
| — | Explicitly deferred | Hard-mandate CI gates: static param-branching scan on `format_value`; sampled entity-injectivity gate; de-offer deadlines for waived violations | Promotion criteria are recorded in ADR-0011 (§8.3, OD-7); promotion is its own future ADR/issue, sequenced after the soft mandate has operated for a release cycle | Phases 2–4 |

Notes for the plan writer:

- The ADR's formal statement must be entity-relative (§8.1 Corollary 1) — the one correction without which the ADR contradicts this report's audit table (§6 vs §7.3).
- The pre-image corollary needs the declared-quantization exception worded exactly as in §8.1 Corollary 2 (exact for encodings/expansions, bounded-drift for documented quantizations) — otherwise the ADR de-offers `dms`/`dm` by accident.
- Phase 2's successor set, names, and deprecation posture are open decisions OD-1/OD-2/OD-3; Phase 3's shape is fixed by §7.1 recommendation (b) but its scope (which extended-tag shapes to cover) is a plan-level question.
- Hygiene note discovered during review: `paxman/capabilities/AGENTS.md` says fifteen shipped capabilities while root AGENTS.md says eighteen — whoever touches shipped docs in Phases 2–3 should reconcile; out of scope here.

## 14. URL Reference (authoritative — consulted 2026-09-05)

| Claim | URL | Kind |
|---|---|---|
| ITU-T E.164 (2010) — number structure, 15-digit limit, Annex A assigned CCs | https://www.itu.int/rec/T-REC-E.164 | primary |
| IETF RFC 3966 (2004) — tel URI global vs local, `;ext=` | https://tools.ietf.org/html/rfc3966 | primary |
| NANPA — NANP administration | https://www.nanpa.com/ | primary |
| BCP 47 / RFC 5646 — language tags, subtags (primary/script/region/variant) | https://www.rfc-editor.org/rfc/rfc5646.html | primary |
| IANA Language Subtag Registry — region/script/variant membership (validation authority) | https://www.iana.org/assignments/language-subtag-registry | primary |
| ISO 3166-1 — alpha-2/alpha-3/numeric/name 1:1 entity encodings | https://www.iso.org/iso-3166-country-codes.html | primary |
| Re-entry fixed-point invariant (necessary-but-insufficient baseline) | `docs/adr/0010-re-entry-fixed-point-invariant.md` | primary (codebase) |
| Contract surface + `resolve_output_format` (always-optional, base-resolved) | `paxman/core/capability_contract.py`, `paxman/core/contract.py` | primary (codebase) |
| Phone `national` construction gate + preservation branch + tests | `paxman/capabilities/Phone/contract.py:103-110`, `paxman/capabilities/Phone/capability.py:154-159`, `tests/capabilities/phone/test_capability.py:310-360` | primary (codebase) |
| Language primary-subtag projection | `paxman/capabilities/Language/capability.py:153-231` (`_primary_language`) | primary (codebase) |
| Coordinates quantization | `paxman/capabilities/Coordinates/capability.py:39-78` | primary (codebase) |
| Coordinates canonical quantum (recognition-time 6 dp, half-even) | `paxman/capabilities/Coordinates/grammar/coordinates_recognition.py:139-143` | primary (codebase) |
| DMS/DM carry behavior under quantization | `tests/capabilities/coordinates/test_coverage_95.py` (`test_dms_sec_and_minute_carry`) | primary (codebase) |
| Re-entry suite (18 rows; Phone row's `default_country` crutch) | `tests/property/test_reentry_invariant.py:112-167` | primary (codebase) |
| Paxman conventions | `HOW_TO_ADD_NEW_CAPABILITY.md`, `ARCHITECTURE.md`, `paxman/capabilities/AGENTS.md` | primary (codebase) |

---

## 15. Evidence Completion — Resolved

- [x] Phone violation proved: CC removal ∩ (`split_country_code` routing ∪ assigned-CC validation) with GB/MY collision table and param-dependence analysis (§4).
- [x] ADR-0010 gap stated: same-contract `V→V` passes while equality fails; param-free pre-image round-trip formulated as the stronger check (§3, §8.1).
- [x] Phone successors illustrated (not mandated): compact / loose / split worked as non-binding compliance examples — definitions, examples, inverses, injectivity + param-free re-entry arguments (§5).
- [x] All-18 audit complete: every offered format classified PASS / VIOLATION with mechanism + rationale and format class (§6).
- [x] Same-category capabilities named: Language (violator, §7.1), Coordinates dms/dm (documented quantization — keep with obligations, §7.2); explicit non-violators recorded (§7.3).
- [x] Soft→hard path specified: soft obligations now, hard gates (static scan + property + proof) and ADR vehicle later (§8–§9).
- [x] Phone migration sequenced: announce, remove + delete branches, add successors + rows, update tests/docs/re-entry row (§10).
- [x] Risks (6) and open decisions (8) with recommendations recorded (§11–§12).
- [x] Formal statement corrected to entity-relative injectivity with the four-class format taxonomy; `bic11`/`eui64` carve-out reconciled with the audit so §6 and §8.1 agree (§2, §7.3, §8.1).
- [x] Coordinates `dms`/`dm` reclassified BORDERLINE → documented quantization: stability proof closed (quantum-ratio argument), bounded-drift bound stated (≈ 1.39e-4° ≈ 140 canonical quanta), obligations defined, de-offer demoted to fallback (§7.2).
- [x] Phone live-defect framing made precise: param dependence and value-dependent shape are live; the GB/MY collision is latent behind the preservation branch (§3, §4.2, Appendix unchanged).
- [x] Implementation sequencing added for plan synthesis: ADR-0011 first (must-implement), Coordinates obligations pre-ADR, Phone post-ADR, Language next, suite hardening, hard gates deferred (§13).

---

## Appendix — Worked Collision Proof (Phone GB vs MY, illustrative NSNs)

`V1 = +4412341234` (CC `44`, assigned per E.164 Annex A), `V2 = +6012341234` (CC `60`, assigned). Both pass `valid_e164_value` (digits-only, ≤15, assigned CC, NSN ≥ 2). `F_national(V1) = "12341234" = F_national(V2)` — `F` is not injective, so no decoder `G` with `G(F(V)) = V` exists without side input. Under `C(US)` both inputs (if entered as E.164) render per the preservation branch as themselves — the only reason no live collision ships today is that `national` refuses non-NANP values rather than rendering them. A format whose correctness depends on refusing most of the value space is not an equal representation of the value space. Successors (§5) admit no such pair: `F_compact(V1) = "4412341234" ≠ "6012341234" = F_compact(V2)`, and longest-prefix CC recovery is the validation function itself.

---

*Report saved to `docs/development/research/` per the request. It directs a shipped-code change (Phone de-offer + successors) but implements none; implementation follows §10 under TDD with an ADR-0010 migration note.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` — not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
