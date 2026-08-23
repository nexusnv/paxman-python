# First-Time User Experience Report — Paxman

**Date:** 2026-08-22
**Author:** Simulated fresh user (no prior Paxman knowledge)
**Method:** Clone from `https://github.com/nexusnv/paxman-python.git` into a disposable directory (`/tmp/paxman-fresh-test`), read README / QUICKSTART cold, install and run canonicalization experiments across multiple capabilities with varying input conditions.
**Commit (fresh clone):** `0.2.0` tag on default branch at time of cloning (2026-08-22)

---

## 1. Executive Summary

Paxman makes a strong first impression once it runs: the canonicalization model (Recognize → Validate → Resolve with typed `Resolution` statuses and full provenance) is coherent, deterministic, and well-differentiated from one-off validators like `phonenumbers` or `babel`. The README is comprehensive, the core API is small (`register` + `create_contract` + `canonicalize`), and the per-capability contract options are discoverable.

The first 5 minutes, however, have meaningful friction for a true newcomer. The headline `pip install paxman` does not work (no distribution on PyPI at time of test), the `register_all_shipped()` bootstrap silently omits the two newest capabilities (ISSN, IBAN) while the README claims 11 shipped capabilities, and the README vs QUICKSTART import paths disagree (`from paxman.capabilities import Email` vs `from paxman.capabilities.Email.capability import EmailCapability`). None of these block an experienced developer for long, but together they cost a first-time user 15–20 minutes of "am I holding it wrong?" debugging. After that, the library behaves predictably and pleasantly — with a few conceptual surprises (bare `$` is `INVALID` by default, IPv6-mapped IPv4 addresses are `AMBIGUOUS`, `bad@.com` is `MISSING` not `INVALID`) that are defensible but deserve stronger callouts in the getting-started path.

**Verdict:** Documentation is thorough enough to recover from every stumble, but a first-time user would finish the session thinking Paxman is a well-engineered library that has not yet polished its packaging and onboarding story.

---

## 2. Method & Environment

| Step | What was done | Outcome |
|------|--------------|---------|
| **Clone** | `git clone https://github.com/nexusnv/paxman-python.git /tmp/paxman-fresh-test` | Clean, no auth needed, ~1s. No `CONTRIBUTING`-style bootstrap script needed. |
| **Read cold** | Opened `README.md` first (625 lines), then `QUICKSTART.md` (94 lines) | Both exist and are linked from README. No separate `GETTING_STARTED.md` — README is the entry point. |
| **Install attempt 1 (as docs say)** | `pip index versions paxman` | `ERROR: No matching distribution found for paxman` — PyPI distribution does not exist yet. |
| **Install attempt 2 (dev path)** | `uv sync --all-extras` inside the cloned repo, then `uv run python ...` | Works. Required knowing `uv` exists (mentioned only in `CONTRIBUTING.md`, not in README install block). Fresh venv created in `/tmp/paxman-fresh-test/.venv` (Python 3.13.14). |
| **Experiment harness** | Single script exercising 4 primary families (Email, URL, IP, Date) + 5 secondary (Country, Currency, Money, Phone, SIUnit) + ISBN/ISSN, each with 3–6 inputs spanning valid / missing / invalid / ambiguous / embedded-in-text / opt-in-flag conditions (~40 `canonicalize()` calls total) | All results logged with `status`, `canonicalized_value`, `span`, candidate count, provenance, and recognition/validation rule names. |

All experiments were run via `uv run --project /tmp/paxman-fresh-test python ...` to keep the fresh clone isolated from the worktree's own venv.

---

## 3. What I Tried (Capability-by-Capability Log)

### 3.1 Registration

```python
import paxman

paxman.register_all_shipped()
```

Succeeded. Idempotent second call returned the tuple of newly-registered names; a manual `register_capability(Email())` after freeze correctly raised `CapabilityError: registry is frozen`. That freeze semantic is clearly documented in both README and QUICKSTART — good.

**Surprise:** `register_all_shipped()` registers only 10 capabilities (Country, Currency, Date, Email, IP, ISBN, Money, Phone, SIUnit, URL). The README capability table lists 11 (adds ISSN) and the repo also ships IBAN (visible in `paxman/capabilities/`). Fresh-clone bootstrap omits both:

```
_SHIPPED in paxman/api/bootstrap.py: 10 entries (alphabetical, no ISSN/IBAN)
README table:                          11 entries (includes ISSN, omits IBAN)
Filesystem:                            12 entries (adds ISSN + IBAN)
```

Attempting `ISSN.create_contract()` + `canonicalize()` on a freshly bootstrapped process raises `CapabilityError: Unknown capability: 'issn'`. Manual `paxman.register_capability(ISSN())` fixes it. This is the single biggest "fresh user" bug — copy-pasting the README's ISSN example fails out of the box.

### 3.2 Email (5 inputs) — following Quick Start verbatim

| Input | Status | Value | Notes |
|-------|--------|-------|-------|
| `Contact user@Example.com` | `SUCCESS` | `user@example.com` | Lowercasing + span `(8, 24)` correct. Provenance `IETF: RFC 5322`. |
| `user@Example.COM` | `SUCCESS` | `user@example.com` | Case folding works. |
| `not an email` | `MISSING` | `None` | Expected. |
| `bad@.com` | `MISSING` | `None` | **Expected `INVALID`**, got `MISSING`. Grammar rejected before validation — defensible, but a newcomer would expect "recognized but invalid". |
| `user at example dot com` with `include_obfuscated=True` | `SUCCESS` | `user@example.com` | Works; `obfuscated_recognition` provenance. Without flag correctly `MISSING`. |

`USER@Example.COM extra` embedded in text also resolved with span `(0, 16)` — the "finds entity inside a sentence" behavior is delightful and under-advertised until the Recognition Span section.

### 3.3 URL (6 inputs)

| Input | Status | Value |
|-------|--------|-------|
| `HTTPS://Example.COM:443/path/../other` | `SUCCESS` | `https://example.com/other` (scheme/host lowered, default port stripped, dot-segments resolved) |
| `http://münchen.de` | `SUCCESS` | `http://xn--mnchen-3ya.de/` (UTS #46 IDNA worked perfectly) |
| `not a url` | `MISSING` | `None` |
| `https://example.com/./a/../b` | `SUCCESS` | `https://example.com/b` |
| `mailto:user@example.com` | `SUCCESS` | `mailto:user@example.com` (opaque, verbatim) |
| `Visit https://Example.COM:443/path/../other today` | `SUCCESS` | `https://example.com/other`, span `(6, 43)` — correctly extracted from surrounding text |

Percent-encoded `%2e%2e` resolving to `/path` was also tested and behaved per WHATWG — nice.

### 3.4 IP (5 inputs)

| Input | Status | Value | Notes |
|-------|--------|-------|-------|
| `192.168.1.1` | `SUCCESS` | `192.168.1.1` | |
| `2001:0db8:0000:0000:0000:0000:0000:0001` | `SUCCESS` | `2001:db8::1` | RFC 5952 compression correct. |
| `999.999.999.999` | `INVALID` | `None` | Recognized but failed RFC 791 — good distinction from `MISSING`. |
| `hello world` | `MISSING` | `None` | |
| `::ffff:192.168.1.1` | `AMBIGUOUS` | `None` | **Surprising.** Two candidates: `::ffff:192` (ipv6) + `192.168.1.1` (ipv4). A newcomer expects a single `SUCCESS` with the ipv6-mapped form. Docs never hint that mixed notation is ambiguous. |

The `include_ipv6=False` flag was not exercised, but its README description is clear.

### 3.5 Date (5 inputs)

| Input | Status | Value |
|-------|--------|-------|
| `2026-01-15` | `SUCCESS` | `2026-01-15` (ISO) |
| `2026/01/15` | `SUCCESS` | `2026-01-15` (slash-ISO) |
| `01/02/2026` | `AMBIGUOUS` | `None` — 4 candidates (US `2026-01-02` + European `2026-02-01`, each via two grammars). **This is Paxman's signature feature working as advertised** — powerful, once you understand it. |
| `not a date` | `MISSING` | `None` |
| `2026-13-01` | `INVALID` | `None` — correctly rejected (month 13). |

Pinning with `pinned_rules=["Section 4.3.1-calendar-date"]` does *not* resolve the `01/02/2026` ambiguity (still `AMBIGUOUS` in my test) — suggesting the ambiguity is at grammar level, not rule level. The Date section's pinning example uses `2026-01-15` which is already unambiguous, so it does not teach the ambiguous-case workflow well.

### 3.6 Remaining Capabilities (smoke tests)

| Capability | Input | Status | Value | Notes |
|------------|-------|--------|-------|-------|
| Country | `US` | `SUCCESS` | `US` | 2 candidates (alpha2 + name), same value → coalesced to SUCCESS. Elegant. |
| Country | `United States` | `SUCCESS` | `US` | |
| Country | `Alemania` | `INVALID` → with `include_localized=True` → `SUCCESS` `DE` | Correct. Localized flag is opt-in and clearly documented. |
| Country | `  usa  ` | `SUCCESS` | `US` | Whitespace-trimming is forgiving — good. |
| Currency | `usd` | `SUCCESS` | `USD` | |
| Currency | `euro` | `SUCCESS` | `EUR` | CLDR word → code. |
| Currency | `$` bare | `INVALID` | `None` | **Conceptually hard.** Docs explain the 29-candidate `$` story, but a newcomer typing `$` and getting `INVALID` without reading 6 lines of fine print will be confused. |
| Currency | `$` + `default_currency="USD"` | `SUCCESS` | `USD` | Opt-in works. `default_currency="MYR"` correctly stays `INVALID` (MYR's symbol is `RM`). |
| Money | `USD500` | `SUCCESS` | `USD 500.00` | Minor-unit padding to `.00`. |
| Money | `$500` bare | `INVALID` | `None` | Same story as Currency — requires `dollar_sign_currency`. With it → `SUCCESS` `USD 500.00`. |
| Money | `1.000,50 EUR` | `SUCCESS` | `EUR 1000.50` | European comma-decimal handled. |
| Phone | `+1 555 123 4567` | `SUCCESS` | `+15551234567` | Two provenances (E.164 §6.1 + §6.2) collapsed. |
| Phone | `(555) 234-5678` no country | `INVALID` | `None` | With `default_country="US"` → `SUCCESS` `+15552345678`. Good. |
| Phone | `tel:+1-555-123-4567` | `SUCCESS` | `+15551234567` | tel-URI recognized. |
| ISBN | `9780306406157` | `SUCCESS` | `9780306406157` | 2 provenances (check digit + GS1 prefix). |
| ISBN | `0306406152` | `SUCCESS` | `9780306406157` | ISBN-10 → ISBN-13 conversion. |
| ISBN | `9780306406158` | `INVALID` | `None` | Bad check digit correctly rejected. |
| SIUnit | `Kilogram` | `SUCCESS` | `kg` | |
| SIUnit | `m/s²` | `SUCCESS` | `m/s2` | Compound normalization. |
| SIUnit | `kilo gram` | `INVALID` | `None` | Requires `allow_split_word_prefixes=True` — documented but surprising. |
| SIUnit | `kg/m/s` | `INVALID` | `None` | Multi-solidus rejected per ISO 80000-1 §6.6.2 unless `allow_multi_solidus=True`. Clear. |
| ISSN | `0378-5955` | `SUCCESS` | `0378-5955` | Only after manual `register_capability(ISSN())`. With bootstrap alone → `CapabilityError`. |
| ISSN | `03785955` | `SUCCESS` | `0378-5955` | Bare form inserts hyphen canonically. |
| ISSN | `ISSN 0378-5955` with label | `SUCCESS` | `0378-5955` | Prefix handled. |
| ISSN | `0378-5954` | `INVALID` | `None` | Bad MOD-11 check. |

### 3.7 Provenance & Span (the "wow" moment)

```python
r = paxman.canonicalize("Reach me at USER@Example.COM for info", contract)
# r.span == (12, 28), r.candidates[0].recognition_rule == "standard_recognition"
# provenance: IETF / RFC 5322 / Section 3.4.1-addr-spec / year=2008
```

Provenance carrying authority, spec name, citation, URL, version, lifecycle, and publication year is the feature that justifies the complexity. Span tracking for extraction from free text is the second. Both worked flawlessly.

### 3.8 Error Handling & Edge Cases

| Scenario | Behavior | Verdict |
|----------|----------|---------|
| Register after freeze | `CapabilityError` | Correct, message clear. |
| `excluded_rules=["nonexistent-rule"]` | No error; just silently excluded nothing, still `SUCCESS` | **Silent.** A newcomer typo in a rule name gets no feedback. `pinned_rules` with same typo correctly raises `ContractError: Unknown pinned rule(s): [...]` — the asymmetry is confusing. |
| `pinned_rules=["not-a-rule"]` | `ContractError` | Good, fail-fast. |
| Empty string `""` | `MISSING` | Sensible — no recognition. |
| `None` as input | `RecognitionError: Grammar failed: 'NoneType' has no attribute 'strip'` | **Unhelpful message.** Should be `TypeError` or a typed `ContractError` with "expected str". Feels like an unguarded internal error leaking. |
| `MultipleMentionsError` | `a@b.com and c@d.com` with Email correctly raises `MultipleMentionsError: 2 distinct mentions resolving to 2 distinct canonical values (['a@b.com', 'c@d.com'])` with split guidance | Works, but only when values differ. Identical values coalesce to `SUCCESS` — clever but undocumented until `docs/recipes/segmentation.md`. |
| `register_all_shipped()` idempotent second call | Returns tuple of newly-registered (empty if all done) — not an error even post-freeze | Documented as idempotent, but surprising when combined with the ISSN omission — second call *after* manual ISSN registration re-registers the 10 shipped but not ISSN, so ISSN stays registered. Works, but mentally noisy. |

---

## 4. What Worked Well

1. **Core abstraction is learnable in one read.** The Recognize → Validate → Resolve pipeline plus four statuses (`SUCCESS`/`MISSING`/`INVALID`/`AMBIGUOUS`) is a crisp mental model. The README's "What Happens" section (3 steps + status table) gets this across in ~10 lines — excellent.

2. **Contract design is ergonomic.** `create_contract()` with keyword flags (`include_localized`, `default_currency`, `dollar_sign_currency`, `allow_multi_solidus`, etc.) makes opt-in behavior explicit and grep-able. The common parameters (`excluded_rules`, `pinned_rules`, `year`) are orthogonal and compose — `year=2008` still allowing RFC 5322 is a nice demo of temporal filtering.

3. **Provenance and span are first-class.** Every candidate exposes `provenance` (authority/spec/citation/year) and `span`. No other Python canonicalization library I know of offers this uniformly. For data-pipeline users, this is the killer feature.

4. **Embedded-text extraction.** Finding `https://example.com/other` inside `Visit https://Example.COM:443/path/../other today` with correct span is exactly what you want for cleaning messy human text — and it just works.

5. **Determinism claims hold.** Same input + same contract = same output. No network, no clock, no fuzzy logic. Repeated calls returned identical objects.

6. **Per-capability README examples are runnable.** Every code block I copied (except ISSN) executed verbatim and produced the documented output. Check-digit validation (ISBN, ISSN), UTS #46 IDNA, RFC 5952 compression, European comma-decimal — all correct.

7. **Error messages for contract misconfiguration are good when they fire.** `ContractError: Unknown pinned rule(s): ['not-a-rule']` is precise and actionable.

---

## 5. What Did Not Work (or Surprised)

### 5.1 Blocking / Must-Fix

| # | Issue | Impact | Evidence |
|---|-------|--------|----------|
| 1 | **`pip install paxman` has no distribution** | A fresh user following the install block hits a dead end. `pip index versions paxman` → `No matching distribution found`. | Tested at 2026-08-22; PyPI has no `paxman` 0.2.0 artifact. |
| 2 | **`register_all_shipped()` omits ISSN (and IBAN)** | Copy-pasting the ISSN example from the README after `register_all_shipped()` raises `CapabilityError: Unknown capability: 'issn'`. README capability table promises 11 shipped; bootstrap ships 10. | `_SHIPPED` tuple in `paxman/api/bootstrap.py` = 10; fresh clone repro in §3.1. |

### 5.2 Confusing / Needs Documentation Repair

| # | Issue | Why it confuses | Suggestion |
|---|-------|----------------|------------|
| 3 | **README vs QUICKSTART import mismatch** | README: `from paxman.capabilities import Email` + `Email.create_contract()`. QUICKSTART: `from paxman.capabilities.Email.capability import EmailCapability` + `EmailCapability.create_contract()`. Both work, but a newcomer sees two canonical spellings and wonders which is stable. | Pick one in both docs; mention the other as alias in a footnote. Prefer the short `Email` alias — it is what `paxman/capabilities/__init__.py` exports and what the registry expects. |
| 4 | **`MISSING` vs `INVALID` boundary is subtle** | `bad@.com` → `MISSING` (grammar rejected) while `999.999.999.999` → `INVALID` (recognized, then rejected). Newcomer mental model: both look like "invalid email/IP". The distinction is architecturally correct (recognition ≠ validation) but first-time users need a one-liner: "If the grammar can't find it, it's MISSING; if a grammar finds it but no rule accepts it, it's INVALID." | Add that sentence + a two-row example to the Resolution Status table in both README and QUICKSTART. |
| 5 | **Bare symbol `INVALID` by default (Currency `$`, Money `$500`)** | Newcomer expects `$` → `USD` or `$500` → `$500`. Getting `INVALID` feels like a bug until you read the 4-line "Opt in: default_currency" paragraph. The concept of 29 candidate currencies sharing `$` is sound but needs a top-level callout. | In each capability's README subsection, move the "Bare $ is INVALID by default" line to a bold `> **Note:**` callout before the opt-in example. |
| 6 | **IPv6-mapped `::ffff:192.168.1.1` is `AMBIGUOUS`** | User expects single IPv6 success; gets `INVALID`-looking `AMBIGUOUS` with candidates `::ffff:192` + `192.168.1.1`. No README mention of mixed-notation ambiguity. | Document as known behavior (or consider treating mapped addresses as single ipv6 recognition). At minimum, add to IP capability notes. |
| 7 | **`excluded_rules` with typo is silent; `pinned_rules` with typo is loud** | `excluded_rules=["typo"]` → no error, silently succeeds. `pinned_rules=["typo"]` → `ContractError`. Inconsistent fail-fast. | Either warn on unknown excluded rules or document why exclusion is intentionally lenient (forward-compat?). |
| 8 | **`None` input leaks internal error** | `canonicalize(None, contract)` → `RecognitionError: Grammar failed: 'NoneType' has no attribute 'strip'`. | Guard top of `canonicalize()` with `if not isinstance(text, str): raise TypeError(...)`. |

### 5.3 Minor / Polish

- `QUICKSTART.md` still says "ten built-in capabilities" in Community Extensions while README (correctly) says eleven — drift from recent ISSN addition.
- README is 625 lines. A newcomer scrolling for "how do I install and try one thing" must pass the Install block, Quick Start, What Happens, then hit the capability table. Consider moving the table to an appendix or providing a 5-line "Try this now" box at the very top.
- `ARCHITECTURE.md` is referenced twice as the deep dive but never summarized in one paragraph for the impatient reader.

---

## 6. What I Hoped Was There But Was Missing

1. **A live playground / `paxman repl` or `python -m paxman`** — Being able to run `echo "usd" | paxman currency` or a small TUI that shows status + provenance without writing a script would have made the first 5 minutes joyful. The library is pure-Python with zero dependencies, so a tiny CLI would be cheap to ship.

2. **Published PyPI artifact** — Even a `0.2.0.dev0` would let `pip install paxman` work. The current install story requires `uv` and a clone, which is contributor tooling, not user tooling.

3. **`paxman --help` or `help(canonicalize)` with capability discovery** — After `register_all_shipped()`, there is no `paxman.list_capabilities()`-style introspection in the public API (there is `get_capability` internally). A newcomer wanting to know "what can I canonicalize?" must read the README table rather than ask the library.

4. **Batch / multi-entity helper** — `MultipleMentionsError` tells you to split, and `docs/recipes/segmentation.md` exists, but it is not linked from the `MultipleMentionsError` message or from the README's Error Handling section at the point a newcomer hits the error. A one-liner import like `from paxman.helpers import split_and_canonicalize` would remove the last mile of glue every data-pipeline user will write.

5. **A `strict` vs `lenient` top-level knob** — Per-capability flags (`allow_multi_solidus`, `allow_split_word_prefixes`, `dollar_sign_currency`) are precise but numerous. A newcomer might want "just be lenient" first, then tighten. A global `lenient=True` preset (or per-capability `mode="lenient"`) would reduce initial option shock.

6. **More "real-world text" examples in README** — Most examples use bare values (`"usd"`, `"192.168.1.1"`). The embedded-text case (`"Contact user@Example.com"`) appears once. Showing `"Invoice of 1.000,50 EUR due 01/02/2026 — contact billing@example.com"` canonicalized per-capability would sell the extraction use-case immediately.

---

## 7. What Would Make Paxman Even Better

Ranked by effort-to-delight ratio for a new user:

| Priority | Change | Effort | Why |
|----------|--------|--------|-----|
| P0 | **Publish to PyPI (even as 0.2.0rc1)** so `pip install paxman` works; document `uv` as alternative, not primary | Low | Unblocks the entire onboarding funnel. |
| P0 | **Fix `register_all_shipped()` to include ISSN (and IBAN when stable)** and regenerate the README capability table from `_SHIPPED` or a single source of truth | Low | Eliminates the first copy-paste failure. |
| P1 | **Align README and QUICKSTART imports on `from paxman.capabilities import Email`** and note `EmailCapability` as long alias | Trivial | Removes the "which spelling is correct?" hesitation. |
| P1 | **Add `TypeError` guard for non-str input** and make `excluded_rules` typo handling consistent with `pinned_rules` | Low | Turns leaked internals into actionable errors. |
| P1 | **Bold callouts for bare-symbol `INVALID` + MISSING/INVALID distinction** in README | Low | Prevents the two most common "is this a bug?" questions. |
| P2 | **Add `paxman.list_capabilities()` / `paxman.get_registered()` public introspection** | Low | Lets users discover capabilities without reading docs. |
| P2 | **Ship a tiny CLI / REPL** (`python -m paxman email "user@Example.COM"`) for zero-script experimentation | Medium | Makes the first 5 minutes interactive and demo-friendly. |
| P2 | **Link `MultipleMentionsError` → `docs/recipes/segmentation.md`** in both exception message and README | Trivial | Turns a confusing error into a next step. |
| P3 | **Generate README capability table from code** (e.g., `tools/generate_readme_table.py`) | Medium | Prevents future drift as new capabilities land. |
| P3 | **Add a "real-world paragraph" example** canonicalizing email + money + date + url from one sentence, showing per-capability contracts and spans | Low | Sells the extraction story that differentiates Paxman. |

---

## 8. Did the Documentation Help?

**Yes — more than most OSS libraries at 0.2.0.** Specifics:

- **README (625 lines):** Dense but accurate. Every per-capability section is self-contained with a runnable snippet, a clear table of grammars/rules/spec, and opt-in flag examples. The Contract Configuration tables (common + capability-specific) are the reference I kept returning to. The Community Extensions section is well-written but long — a newcomer will skip it on first pass, which is fine. **Grade: A- for accuracy, B for scannability.**

- **QUICKSTART (94 lines):** The best onboarding file — 2-minute path from install to `SUCCESS`. I wish it were linked at the very top of README (it is, but as a file reference in Learn More, not as the primary "New here? Start here" CTA). Install block only shows `pip install paxman` (which fails) — adding a `git clone + uv sync` fallback would have saved 5 minutes. **Grade: B+ for clarity, C for install accuracy.**

- **ARCHITECTURE.md / CONTRIBUTING.md / HOW_TO_ADD_NEW_CAPABILITY.md:** Not needed for usage, but well-structured for the second session (contributor path). The `uv` toolchain is clearly documented in CONTRIBUTING.

- **Error messages + provenance:** Often better than the docs themselves. `ContractError: Unknown pinned rule(s): ['not-a-rule']` and per-candidate provenance (`IETF: RFC 5322 / Section 3.4.1-addr-spec`) taught me the model faster than prose did.

**Net:** Documentation carried me through every experiment after the initial install + ISSN registration stumbles. The content is there; the issues are packaging, single-source-of-truth drift, and a few missing guardrails — not prose quality.

---

## 9. Raw Log (abridged, for audit)

All experiments were run in a single detached `uv run` process against the fresh clone at `/tmp/paxman-fresh-test`. Full harness (`/tmp/run_paxman_experiments2.py`, ~40 calls) produced:

```
[SUCCESS] Email: 'Contact user@Example.com'           -> 'user@example.com' span=(8,24)
[MISSING] Email: 'not an email'                       -> None
[MISSING] Email: 'bad@.com'                           -> None
[SUCCESS] Email obf: 'user at example dot com'        -> 'user@example.com'
[SUCCESS] URL: 'HTTPS://Example.COM:443/...'          -> 'https://example.com/other'
[SUCCESS] URL IDN: 'http://münchen.de'                -> 'http://xn--mnchen-3ya.de/'
[MISSING] URL: 'not a url'                            -> None
[SUCCESS] URL in sentence                             -> 'https://example.com/other' span=(6,43)
[SUCCESS] IP: '192.168.1.1'                           -> '192.168.1.1'
[SUCCESS] IP v6 zero-padded                           -> '2001:db8::1'
[INVALID] IP: '999.999.999.999'                       -> None
[AMBIGUOUS] IP v6 mixed: '::ffff:192.168.1.1'         -> None (candidates: ::ffff:192 + 192.168.1.1)
[SUCCESS] Date ISO: '2026-01-15'                      -> '2026-01-15'
[AMBIGUOUS] Date ambiguous: '01/02/2026'              -> None (4 candidates)
[SUCCESS] Date slash-ISO: '2026/01/15'                -> '2026-01-15'
[INVALID] Date invalid: '2026-13-01'                  -> None
[SUCCESS] Country: 'US'                               -> 'US' (2 candidates coalesced)
[SUCCESS] Country: 'Alemania' localized=True          -> 'DE'
[INVALID] Currency: '$' bare                          -> None
[SUCCESS] Currency: '$' default_currency=USD          -> 'USD'
[SUCCESS] Money: 'USD500'                             -> 'USD 500.00'
[INVALID] Money: '$500' bare                          -> None
[SUCCESS] Phone: '+1 555 123 4567'                    -> '+15551234567'
[INVALID] Phone: '(555) 234-5678' no country          -> None
[SUCCESS] Phone tel-URI: 'tel:+1-555-123-4567'        -> '+15551234567'
[SUCCESS] ISBN: '9780306406157'                       -> '9780306406157'
[SUCCESS] ISBN10: '0306406152'                        -> '9780306406157'
[SUCCESS] SIUnit: 'Kilogram'                          -> 'kg'
[SUCCESS] SIUnit: 'm/s²'                              -> 'm/s2'
[INVALID] SIUnit: 'kilo gram' no flag                 -> None
[SUCCESS] ISSN: '0378-5955'                           -> '0378-5955' (after manual register)
CapabilityError: Unknown capability: 'issn'            (before manual register, via register_all_shipped)
None input -> RecognitionError: 'NoneType' has no attribute 'strip'
MultipleMentionsError: 2 distinct mentions a@b.com / c@d.com
```

Full scripts archived at `/tmp/run_paxman_experiments.py` and `/tmp/run_paxman_experiments2.py` (removed with the clone; reconstructable from §3 tables above).

---

## 10. Cleanup

The disposable clone at `/tmp/paxman-fresh-test` (including its `.venv`) was removed after report generation per the experiment's remit:

```bash
rm -rf /tmp/paxman-fresh-test /tmp/run_paxman_experiments.py /tmp/run_paxman_experiments2.py
```

This report lives in `docs/development/reports/` (non-shipping, per `docs/development/AGENTS.md`) and does not affect the published distribution.

---

*Report generated from a simulated first-time user session. All observations are from a clean clone with no prior Paxman knowledge; follow-up sessions as a returning user would have different expectations.*
