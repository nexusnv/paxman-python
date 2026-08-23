# URL Canonicalization Research — Paxman URL Capability

| | |
|---|---|
| **Date** | 2026-08-06 |
| **Scope** | Research and design for the URL capability (MILESTONE.md row 4). Covers: input scope, normative authority, normalization semantics, recognition strategy, notation shape, rule decomposition, data strategy, contract surface, and test plan. |
| **Out of scope** | Relative reference resolution (RFC 3986 §5); protocol-based equivalence (RFC 3986 §6.2.4); Unicode normalization to NFC (RFC 3987 §5.3.2.2 — recorded, deferred); fragment comparison policy; IDNA table freshness beyond the vendored snapshot. |
| **Evidence basis** | Primary sources fetched and section-verified: [RFC 3986] (STD 66, Jan 2005), [RFC 3987] (Jan 2005), [WHATWG URL Standard] (living standard, fetched snapshot). Empirical verification: 4 Node.js scripts against `new URL()` (30+ edge cases, all outputs captured in this document). Paxman architecture references: `paxman/capabilities/IP/` (PARSER-strategy sibling), `paxman/core/domain.py`, `tests/`. No source code, tests, or configuration were modified. Repo state: branch `feature/CURRENCY-capability` @ `efab963`. |

---

## Executive Summary

1. **Two authoritative grammars compete.** RFC 3986/3987 define the URI/IRI grammar and a *comparative* normalization ladder; the WHATWG URL Standard defines a *single deterministic* parse→serialize pipeline that subsumes both for web-style identifiers. They diverge materially on percent-encoding, default ports, empty-path handling, IPv4 leading zeros, and IDNA.
2. **WHATWG URL Standard is the single normative pipeline (D2).** Its parser is a total function — every input maps to exactly one output or a rejection — which satisfies Paxman's determinism contract ("same input + contract = byte-identical output"). RFC 3986's §6 ladder is SHOULD-level guidance for *comparison*, not a canonicalization algorithm, and applying RFC §6.2.2.2 (decode unreserved) *after* WHATWG dot-segment removal can resurrect `../` sequences, producing different outputs for equivalent inputs.
3. **RFC 3986/3987 remain provenance references.** The rule cites the WHATWG pipeline for the algorithm, and RFC 3986 §3.1 / RFC 3987 §2 for the grammar and IRI mapping rationale. Provenance stays multi-source; behavior is single-source.
4. **WHATWG preservation semantics verified empirically.** Percent-encoding is preserved byte-for-byte in path/query/fragment — including invalid sequences (`%zz`, bare `%`) — diverging directly from RFC 3986 §6.2.2.2's recommendation to decode unreserved characters. In a special-scheme host, in contrast, a bare `%` is rejected (§4.1). Empty `?`/`#` and trailing host dots are preserved, matching RFC 3986 §6.2.3's "cannot be assumed equivalent" position.
5. **IRI support requires vendored IDNA tables (D3/D13).** RFC 3987 §3.1 explicitly defers internationalized hosts to IDNA at the application layer; WHATWG §3.3 mandates UTS #46. UTS #46 tables are vendored as a generated data module (ISBN `tools/regenerate_isbn_range_data.py` pattern) — zero runtime dependencies.
6. **Recognition is regex span-matching, not a hand-written parser (D7/D16).** "PARSER" in MILESTONE.md describes the *rule's* parse-and-transform; the grammar is a shape matcher over spans, exactly as IP does today. One grammar, `absolute_uri_recognition`.
7. **Notation is a single text field (D15).** `URLNotation(text: str)` mirrors `IPNotation`; components would smuggle a second parser into the grammar layer, which the single-rule decision (D11) forbids.

---

## 1. The Domain

A URL (Uniform Resource Locator) is an identifier for a retrievable resource. Paxman's input is ambiguous human text — an *absolute URI/IRI embedded in prose* — and the capability's job is to return the identifier as the authoritative specification says it must be serialized.

### 1.1 Input scope (D1)

- **Absolute URIs/IRIs only.** Relative references (`/path`, `../x`, `?q`) and protocol-relative (`//example.com/path`) are not recognized. The milestone example is absolute: `HTTPS://Example.COM:443/path/../other`.
- **IRIs are in scope (D3).** Full IRI syntax per RFC 3987 §2: non-ASCII characters in host (→ UTS #46 punycode), path/query/fragment (→ UTF-8 percent-encoding).
- **Spans embedded in prose (D7).** Recognition happens over spans in running text (house convention — see §6).

### 1.2 What "canonical" means here

Canonical value = the WHATWG-serialized URL string (D10): scheme and host lowercased, dot-segments removed, default ports dropped, percent-encoding preserved, everything else verbatim (§4.5 URL serializing). One input + one contract → exactly one string, byte-identical across runs.

### 1.3 Losslessness (D4)

The capability is **lossless over the components it preserves**: no preserved component is dropped or elided, and percent-encoding case is retained byte-for-byte. Fragment, userinfo, empty `?`/`#`, trailing host dots, port 0, and percent-encoding case are all preserved. (Deliberate WHATWG normalizations — default-port elision, dot-segment resolution, IPv4 base conversion, IDNA host encoding — apply to the components the serializer rewrites, never to the preserved ones.) This follows RFC 3986 §6.2.3's position that `http://example.com/` and `http://example.com/#` are *different* URIs and "cannot be assumed equivalent". Dropping components would be a second, undocumented normalization — and would violate determinism for inputs that differ only in those components.

---

## 2. The Authorities

Three specifications govern URLs. Each contributes a different layer; only one defines the algorithm.

### 2.1 RFC 3986 — URI syntax and comparison (STD 66, Jan 2005)

- **§3** grammar: `URI = scheme ":" hier-part [ "?" query ] [ "#" fragment ]`; `scheme = ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )` (§3.1, case-insensitive, "should only produce lowercase").
- **§3.2.2** host is case-insensitive; **§3.2.3** port syntax; **§7.5** deprecates userinfo passwords.
- **§5.2** reference resolution and the `remove_dot_segments` algorithm (§5.2.4).
- **§6.2** the normalization ladder — §6.2.1 simple string comparison, §6.2.2 syntax-based, §6.2.3 scheme-based, §6.2.4 protocol-based. **§6.2 is explicitly *comparative* guidance, phrased in SHOULD terms, not a canonicalization algorithm** (see §3).
- **§7.4** forbids non-decimal IP literals ("rare IP formats") in the grammar.
- **Appendix C** documents how URIs appear in text (delimiters, line breaks) — the basis for the recognition boundary rules.
- **Appendix D** confirms empty-path URIs are legal (`dav:`, `about:`).

### 2.2 RFC 3987 — IRI (Internationalized Resource Identifier)

- **§2.1**: `IRI = scheme ":" ihier-part [ "?" iquery ] [ "#" ifragment ]`; **§2.2** extends `unreserved` with `ucschar` (non-ASCII code points).
- **§3.1** maps IRIs to URIs: non-ASCII → UTF-8 → percent-encode; **the internationalized host is explicitly handed to IDNA at the application layer** — RFC 3987 does not prescribe an IDNA profile.
- **§5.3.2.2** recommends NFC character normalization *in the absence of knowledge of the intended interpretation* — a conditional recommendation, not a mandate (D9, deferred).
- **§5.3.2.3** percent-encoding normalization; **§5.3.2.4** path segment normalization (mirrors RFC 3986 §6.2.2.3).

### 2.3 WHATWG URL Standard — the deterministic pipeline

- **§1.3** percent-encode sets (C0 control, fragment, query, special-query, path, userinfo, component).
- **§3.3** IDNA: domain-to-ASCII via **UTS #46** (mandatory, with transitional/UTS46 mapping details); **§3.5/§3.6** host parsing/serializing; **§3.7** host equivalence.
- **§4.4** the basic URL parser — a state machine that is a **total function**: every input string maps to exactly one URL record or a rejection (fatal validation error). First step: "Remove all ASCII tab or newline from input." Special schemes table (ftp:21, file:null, http:80, https:443, ws:80, wss:443) sets default ports and enables authority-style parsing. IPv4 parser interprets leading-zero parts as octal and re-serializes decimal ("09" is caught at a later stage).
- **§4.5** the URL serializer: emits lowercase scheme/host, drops the port when it equals the scheme's default, percent-encodes per component sets.
- **§4.6** URL equivalence; **§4.8** URL rendering (punycode → Unicode for *display only* — the serialized value keeps punycode).

### 2.4 Why WHATWG wins the algorithm seat (D2)

| Criterion | RFC 3986 §6.2 | WHATWG URL Standard |
|---|---|---|
| Nature | SHOULD-level comparative guidance | Mandatory parse→serialize algorithm |
| Determinism | "Should" per form; requires human judgment | Total function; one output per input |
| IDNA | Deferred to application | Mandatory (UTS #46) |
| Default ports | "should be removed" | Deterministic (special schemes) |
| Percent-encoding | Decode unreserved (SHOULD) | Preserve byte-for-byte |
| Implementation precedent | Speculative | Implemented by every browser, Node, deno, curl |

RFC 3986 §6.2 was written to answer "are these two URIs equivalent?" — not "what is the canonical spelling of this URI?". Conflating the two is the classic source of non-deterministic canonicalizers. The WHATWG pipeline is the only one of the two that is an algorithm.

---

## 3. RFC 3986 §6 Normalization Ladder — Why It Cannot Stand Alone

RFC 3986 §6.2 describes four levels of comparison. Each higher level *assumes* the lower ones, and each is advisory:

- **§6.2.1 Simple string comparison** — trivial; case-sensitive, so of limited use.
- **§6.2.2 Syntax-based normalization**:
  - **§6.2.2.1 Case normalization** — lowercase scheme/host; uppercase hex in percent-encoding is the *recommended* form.
  - **§6.2.2.2 Percent-encoding normalization** — "the percent-encoded forms of a URI must be compared for equivalence after decoding"; recommends decoding unreserved characters.
  - **§6.2.2.3 Path segment normalization** — remove dot-segments.
- **§6.2.3 Scheme-based normalization** — empty path → `/` **only when the authority is present**; default port "should be removed"; empty query/fragment are *significant*: `http://example.com/?` "cannot be assumed equivalent" to `http://example.com/`; **two URIs that differ only by the suffix `#` are considered different**; the fragment "is not used in the scheme-specific processing".
- **§6.2.4 Protocol-based normalization** — delegated to the protocol spec.

Two problems make §6.2 unsuitable as the sole normative source:

1. **Order matters and is unspecified.** Decoding unreserved (6.2.2.2) and removing dot-segments (6.2.2.3) interact: decoding `%2e` to `.` *then* resolving dot-segments changes meaning; applying 6.2.2.2 *after* dot-segment removal can re-materialize `..` segments that were already resolved. The RFC does not prescribe the order.
2. **SHOULD ≠ deterministic.** Each form leaves room for judgment; two implementations of §6.2 alone will not produce byte-identical output.

WHATWG resolves both: the pipeline fixes the order and the outcome.

---

## 4. WHATWG URL Standard — Verified Behavior

All behaviors below were verified empirically against Node.js `new URL()` in this session (scripts in `/tmp/opencode/url-research/`). They are the evidence base for the divergence table in §5 and for the rule-layer test cases in §7.6.

### 4.1 Fatal validation errors → input is unrecognized (D8)

Throwing inputs (WHATWG: fatal validation error; Paxman: the grammar/rule layer returns **no recognition**):

| Input | Reason |
|---|---|
| `http://example.com:99999/` | Port > 65535 |
| `http://example.com:80x/` | Non-digit in port |
| `http://example.com:80:90/` | Two port components |
| `http://exa mple.com/` | Space in host |
| `http://[::1` | Unclosed IPv6 literal |
| `http://[2001:db8::1::1]/` | Two `::` in one IPv6 literal |
| `http://xn--abc-def/` | Invalid `xn--` label (punycode payload fails UTS #46 validation) |
| `http://exa%mple.com/` | Bare `%` in a special-scheme host |
| `file://exa:mple/` | `:` in a non-drive-letter file host |

### 4.2 Silent recoveries → canonical + recovery recorded in provenance (D8)

| Input | Output | Recovery |
|---|---|---|
| `http://exa\nmple.com/` | `http://example.com/` | Tab/newline stripped pre-parse (§4.4 step 1) |
| `http://example.com:` | `http://example.com/` | Empty port dropped |
| `http://example.com:0/` | `http://example.com:0/` | Port 0 **preserved** (not a default) |
| `http://example.com\path` | `http://example.com/path` | Backslash → `/` (special schemes) |
| `http://%65xample.com/` | `http://example.com/` | Host percent-decoding |
| `http://example.com/a b` | `http://example.com/a%20b` | Path space → `%20` |
| `http://user name@example.com/` | `http://user%20name@example.com/` | Userinfo space → `%20` |
| `http://[2001:db8::1]/` | `http://[2001:db8::1]/` | IPv6 literal parsed and re-serialized (see note) |
| `http://[2001:0DB8:0:0:0:0:0:1]/` | `http://[2001:db8::1]/` | IPv6 re-serialized: lowercase hex, leading zeros dropped, zero run compressed |
| `http://[::ffff:192.168.1.1]/` | `http://[::ffff:c0a8:101]/` | IPv4-mapped tail serialized as hex pieces |
| `file://localhost/etc/hosts` | `file:///etc/hosts` | `localhost` host dropped for file (case-insensitive) |
| `file://LOCALHOST/etc/hosts` | `file:///etc/hosts` | Same, uppercase `LOCALHOST` |
| `file://a:/x` | `file:///a:/x` | Drive letter (single ASCII alpha + `:`) moved into the path |

IPv6 literals are parsed, not passed through: at most 8 pieces of 1-4 hex digits each (value ≤ 0xFFFF), at most one `::`, and an IPv4-embedded tail only in the final two slots (after six explicit pieces or a `::`); invalid literals are fatal (§4.1). Serialization emits lowercase hex with no leading zeros, compresses the longest run of ≥ 2 zero pieces (ties go leftmost) to `::` with single zeros left explicit, and renders IPv4-mapped tails as hex, not dotted decimal.

### 4.3 Percent-encoding is preserved byte-for-byte (the big divergence)

| Input | Output |
|---|---|
| `http://example.com/a%2fb` | `http://example.com/a%2fb` — **`%2f` ≠ `%2F`; case kept** |
| `http://example.com/%41` | `http://example.com/%41` — **`%41` not decoded to `A`** |
| `http://example.com/~x` | `http://example.com/~x` — `~` stays literal, `%7e` stays encoded |
| `http://example.com/%zz` | `http://example.com/%zz` — invalid escape **preserved** |
| `http://example.com/a%` | `http://example.com/a%` — bare `%` **preserved** |

Contrast with RFC 3986 §6.2.2.2 (decode unreserved, uppercase hex). The rule must **not** normalize percent-encoding case or decode unreserved — doing so would violate WHATWG equivalence and break losslessness (D4).

### 4.4 Query and fragment are verbatim (D6)

| Input | Output |
|---|---|
| `http://example.com/?a=b c` | `http://example.com/?a=b%20c` — space → `%20` |
| `http://example.com/?a='b'c` | `http://example.com/?a=%27b%27c` — `'` percent-encoded (special-query set) |
| `http://example.com/?x=%7e` | `http://example.com/?x=%7e` — `%7e` not decoded |
| `http://example.com/?a+b` | `http://example.com/?a+b` — `+` is a **literal**, never a space |
| `http://example.com/?` | `http://example.com/?` — **empty query preserved** |
| `http://example.com/#` | `http://example.com/#` — **empty fragment preserved** |
| `http://example.com/#a b` | `http://example.com/#a%20b` |

No parameter ordering, no plus-sign decoding, no empty-component elision.

Special schemes use the special-query percent-encode set: space, `"`, `<`, `>`, and `'` are percent-encoded; `+` stays literal; everything else passes through verbatim. Non-special schemes use the plain query set, which omits the apostrophe (`custom:?a='b'c` keeps `'` raw).

### 4.5 Non-special schemes pass through (D5)

WHATWG splits the world: special schemes (ftp, file, http, https, ws, wss) get the full parser; every other valid scheme gets scheme-lowercasing plus one of two path branches — a hierarchical `//` path (opaque-host state with an empty host, then the `//` path state: spaces percent-encoded, dot segments resolved) or an opaque path (no `//` after the scheme: §4.4 opaque path state, spaces preserved raw).

| Input | Output | Note |
|---|---|---|
| `mailto:user@example.com` | `mailto:user@example.com` | Verbatim |
| `GIT://github.com/user/repo` | `git://github.com/user/repo` | Scheme lowercased only |
| `ssh://user@host:22/path` | `ssh://user@host:22/path` | Port 22 **kept** (non-special) |
| `ftp://example.com:21/a` | `ftp://example.com/a` | Port 21 dropped (special, default) |
| `ws://example.com:80/a` | `ws://example.com/a` | Port 80 dropped (special, default) |
| `mailto:user@münchen.de` | `mailto:user@m%C3%BCnchen.de` | Non-ASCII always percent-encoded |
| `data:text/plain,hello world` | `data:text/plain,hello world` | **Opaque path: space preserved raw** |
| `git://github.com/user/my repo` | `git://github.com/user/my%20repo` | `//` path state: space → `%20` |
| `custom:scheme with space` | `custom:scheme with space` | Opaque path: space preserved raw |

The opaque-path rule (WHATWG §4.4 opaque path state): a space is appended raw **unless** it is followed by `?` or `#` (then `%20`); non-ASCII is UTF-8 percent-encoded; `%HH` is preserved.

### 4.6 Hosts, IPv4, and structure

| Input | Output | Note |
|---|---|---|
| `HTTPS://Example.COM:443/path/../other` | `https://example.com/other` | **The milestone example** — holds in both standards |
| `http://010.010.010.010/` | `http://8.8.8.8/` | IPv4 leading zeros: **octal → decimal** |
| `http://192.168.001.001/` | `http://192.168.1.1/` | Same rule |
| `http:///path` | `http://path/` | Empty host with special scheme → host takes the path |
| `http://münchen.de/` | `http://xn--mnchen-3ya.de/` | UTS #46 punycode (per WHATWG §3.3) |
| `http://caf%C3%A9.de/` | `http://xn--caf-dma.de/` | Percent-encoded host decoded, then IDNA |
| `http://café.example/` | `http://xn--caf-dma.example/` | IRI host → punycode |
| `git://münchen.de/` | `git://m%C3%BCnchen.de/` | Non-special host: non-ASCII UTF-8 percent-encoded, no IDNA |

Special-scheme hosts run IDNA (UTS #46): non-ASCII labels map to punycode (`münchen.de` → `xn--mnchen-3ya.de`), and existing `xn--` labels are validated rather than trusted: the punycode payload must decode to ≥ 1 non-ASCII code point, every code point must be valid per UTS #46 (including BIDI), and re-encoding must reproduce the label; any failure rejects the host (`xn--abc-def` is rejected, §4.1). Non-special hosts skip IDNA: non-ASCII is UTF-8 percent-encoded instead. A bare `%` in a special-scheme host is rejected; only `%HH` is decoded (§4.1, §4.2).

### 4.7 No Unicode normalization (D9)

| Input | Output |
|---|---|
| `http://example.com/café` (precomposed) | `http://example.com/caf%C3%A9` |
| `http://example.com/cafe\u0301` (NFD) | `http://example.com/cafe%CC%81` |

Precomposed and decomposed spellings produce **different** outputs. NFC (RFC 3987 §5.3.2.2) would collapse them — that is a *semantic* alias decision Paxman deliberately does not make (recorded, deferred; see §8).

---

## 5. Divergence Analysis and Precedence

The two standards disagree in five places. Every divergence was resolved toward WHATWG (D2), with the RFC position recorded in provenance:

| Topic | RFC 3986 / 3987 | WHATWG URL Standard | Resolution |
|---|---|---|---|
| Percent-encoding | §6.2.2.2: decode unreserved, uppercase hex (SHOULD) | §4.4: preserve byte-for-byte, incl. invalid | **WHATWG.** Decoding breaks equivalence and can resurrect `..` |
| Default ports | §6.2.3: "should be removed" | §4.5: always dropped when equal to scheme default | **WHATWG.** Deterministic rule, not a SHOULD |
| Empty path | §6.2.3: → `/` only when authority present | §4.4: always `/` for special schemes | **WHATWG.** Simple, total |
| IPv4 leading zeros | §7.4: disallowed by grammar | §4.4 IPv4 parser: octal → decimal | **WHATWG.** Deterministic recovery; documented |
| IDNA | RFC 3987 §3.1: deferred to application | §3.3: UTS #46 mandatory | **WHATWG.** Removes the application-level ambiguity |
| Unicode normalization | RFC 3987 §5.3.2.2: NFC (conditional) | none — verbatim | **WHATWG.** No NFC (D9) |
| Empty `?`/`#`, trailing dot | §6.2.3: significant, cannot be assumed equivalent | §4.4/§4.5: preserved | **Agree.** Both preserve (lossless, D4) |

Precedence rule for the rule layer: **WHATWG URL Standard is normative for the algorithm; RFC 3986 §3 and RFC 3987 §2 are normative for grammar provenance; RFC 3986 §6.2 and RFC 3987 §5 are cited only as "considered and rejected/superseded" provenance.** Provenance records all three; behavior follows exactly one.

---

## 6. Recognition Strategy (grammar layer)

MILESTONE.md row 4 labels the strategy **PARSER**. In this codebase that does **not** mean a hand-written parser in the grammar layer — it describes the *rule's* parse-and-transform, exactly as with IP: the IP grammar is a regex shape matcher (`\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b`) that recognizes `999.999.999.999` (shape-only) and lets the rule reject it. Grammars recognize; rules validate, normalize, and resolve. D11 (single rule) additionally forbids the grammar from pre-parsing what the rule owns.

### 6.1 Grammar: `absolute_uri_recognition` (D16)

One grammar, regex-driven:

- **Anchor** on the scheme: `[A-Za-z][A-Za-z0-9+.\-]*:` (RFC 3986 §3.1, RFC 3987 §2.1 — the scheme is the only mandatory, non-ambiguous prefix).
- **Body**: URI/IRI code points — ASCII per RFC 3986 §2 plus `ucschar` per RFC 3987 §2.2, and tab/newline *inside* the span (RFC 3986 Appendix C documents multi-line URIs; WHATWG §4.4 strips them pre-parse — recognition keeps them so the rule can apply WHATWG's strip-and-recover path).
- **Minimum substance**: at least **one body character** after the colon (D16). `Note:` (empty path, no body) is prose, not a URL — matches RFC 3986 Appendix D's admission that empty-path schemes are legal but rejects treating namespace prefixes as identifiers. `dav:` alone is not recognized; `dav:path` is.
- **Boundaries** (Appendix C-aware):
  - Left: not preceded by a scheme-legal character (`ahttps://…` inside a word is not recognized; `(https://…` is).
  - Right: terminated by whitespace, control characters, `<`, `>`, `"` — the RFC 3986 Appendix C delimiters. A trailing `.` is **included** in the span (it is legal in path/host; §6.2.3 treats trailing-dot hosts as distinct) and a trailing `)` is excluded only when unbalanced — Appendix C's "not part of the URI" convention.
- **Shape-only, never validates**: `https://` with no host, `http://99999/`-style spans, and `http://exa mple.com/` are all recognized as spans; the rule decides validity per WHATWG (fatal → unrecognized, D8).
- Emits a span-bearing `RecognitionMatch` with `notation=URLNotation(raw_text)` and the invariant `len(raw_text) == end - start`.

### 6.2 What recognition does NOT do

- No scheme table, no port validation, no host parsing, no default-port knowledge — **grammars never map tokens to canonical values** (house rule).
- No dot-segment resolution, no percent-decoding, no IDNA — all rule-layer work.
- No deduplication or ordering of candidates — the engine owns that.

---

## 7. Paxman Architectural Mapping

### 7.1 Directory layout

```
paxman/capabilities/URL/
├── __init__.py          # URLCapability
├── notation.py          # URLNotation (D15)
├── contract.py          # URLCapabilityContract (D14)
├── capability.py        # URLCapability(Capability): get_grammars/get_rules/format_value
├── grammar/
│   └── absolute_uri_recognition.py   # D16
└── rules/
    └── whatwg_url_standard.py        # D11 — the single rule
    └── data/
        └── idna_uts46_mapping.py     # D13 — vendored UTS #46 tables (generated)
```

### 7.2 Notation — `URLNotation` (D15)

```python
@dataclass(frozen=True, slots=True)
class URLNotation:
    """A span of text recognized as an absolute URI/IRI (shape-only)."""

    text: str

    def as_list(self) -> list[str]:
        return [self.text]
```

Exact sibling of `IPNotation` (`address: str`). **Deliberately single-field**: the grammar must not pre-parse components (D11), the rule needs nothing beyond the raw text to run WHATWG, and `as_list()` keeps the standard engine interface. A component-carrying notation (`scheme: str, host: str, …`) would smuggle a second parser into the grammar layer and duplicate the rule's work.

### 7.3 The rule — `whatwg_url_standard.py` (D11)

One rule, name `"WHATWG URL Standard"`, implementing the full parse→serialize pipeline:

1. Strip ASCII tab/newline (WHATWG §4.4 step 1) — **this is what turns an Appendix C multi-line span into a canonical URL**, making D8's recovery path reachable from prose.
2. Run the basic URL parser state machine: scheme, special-scheme table, userinfo, host (UTS #46 for non-ASCII), port, path (dot-segment removal, percent-encode sets), query, fragment.
3. On **fatal validation error** → return no resolution (unrecognized input; the engine's no-candidate path).
4. On **silent recovery** (validation error flagged but parsing continues) → canonicalize **and** record the recovery in `Provenance` (e.g. "port `99999` rejected" vs "empty port dropped").
5. Serialize per WHATWG §4.5 (lowercase scheme/host, default port elision, percent-encode sets).
6. Produce `Resolution(value=serialized, provenance=[WHATWG §4.4 parse, §4.5 serialize, RFC 3986 §3.1/3987 §2 grammar, RFC 3986 §6.2 superseded notes as applicable])`.

The rule **never** reads `output_format`, never gates on `include_*` (declared `requires_features=()`), never raises (returns no-resolution instead).

### 7.4 Capability and contract (D14)

- `URL` registered in `paxman/capabilities/__init__.py` (export completeness enforced by `tests/unit/test_capability_exports.py`).
- `URLCapabilityContract` — frozen, no slots, minimal: capability name `"url"`, notation `URLNotation`, canonical value is a serialized string (D10). **No feature flags** (D14): no `strip_fragment`, no `normalize_query`, no `punycode_display`. Feature requests are future capabilities or future contracts — not flags on this one. (Flags would multiply the state space and break the "one input + one contract = one output" invariant.)

### 7.5 Data strategy — vendored UTS #46 tables (D13)

UTS #46 domain-to-ASCII needs mapping tables (code points → validity, mapping, deviation flags). Options evaluated:

| Option | Verdict |
|---|---|
| `idna` PyPI package (a dependency) | Rejected — violates zero-runtime-dependency posture; version drift changes outputs (determinism risk) |
| Thin wrapper over stdlib `encodings.idna` | Rejected — UTS #46 ≠ stdlib IDNA 2003; deviation handling differs (e.g. `ß`) |
| **Vendored generated tables** | **Adopted** — commit the UTS #46 mapping as `data/idna_uts46_mapping.py`, generated by a tool |

Pattern: exactly the ISBN capability's `tools/regenerate_isbn_range_data.py` — a committed generator that emits a plain module-level table, separating data from logic. The generator (`tools/regenerate_idna_uts46_data.py`) pins the UTS #46 source version and records it in the generated file header, so table provenance is auditable and regeneration is a documented, re-runnable act. **Zero runtime dependencies.**

### 7.6 Test plan (TDD; failing tests first)

- **Unit — grammar**: `Note:` rejected (D16); `https://example.com` span in prose with leading `(` and trailing `)` (Appendix C); multi-line span with embedded newline; trailing-dot host included in span; left-boundary word rejection (`ahttps://…`); non-ASCII body (`mailto:user@münchen.de`).
- **Unit — rule**: every row of §4.1 (fatal → no recognition), §4.2 (recoveries → canonical + provenance), §4.3 (percent preservation), §4.4 (verbatim query/fragment), §4.5 (non-special schemes), §4.6 (hosts/IPv4), §4.7 (no NFC) as parametrized cases.
- **Milestone case**: `HTTPS://Example.COM:443/path/../other` → `https://example.com/other` (integration, through `canonicalize()`).
- **Contract/provenance**: recovery events appear in provenance; fatal cases carry no resolution; output is byte-identical across repeated runs (determinism).
- **Data**: IDNA table tests (`münchen.de` → `xn--mnchen-3ya.de`, `ß.de` per UTS #46 deviation); generator regeneration is idempotent.
- **Export/registration**: `test_capability_exports.py` includes URL; registry freeze behavior (integration).
- **Replay hashes**: `test_default_replay_hashes.py` baseline updated **only** when the pipeline output legitimately changes.

---

## 8. Out of Scope and Future Work

- **Relative reference resolution** (RFC 3986 §5.2): requires a base URI parameter — a different contract. Recorded in provenance as out of scope (D1).
- **NFC normalization** (RFC 3987 §5.3.2.2): recognized-but-deferred (D9). A future `NFC`-semantics contract could collapse `café`/`cafe\u0301`; today they are distinct canonical values, and the provenance cites §5.3.2.2 as considered.
- **Fragment comparison policy / fragment stripping**: WHATWG and RFC agree fragments are significant and preserved (D4); a "comparison" product is a different capability.
- **Query structure** (param sorting, `+` decoding): explicitly rejected (D6); verbatim is the deterministic choice.
- **IDNA table drift**: vendored snapshot (D13) means the tables age; regeneration tool + pinned source version make refresh a deliberate, tested act.
- **Protocol-based equivalence** (RFC 3986 §6.2.4): per-scheme semantic comparison — not a canonicalization concern.

---

## 9. Resolved Decisions

All sixteen design questions were settled during the design interview (grilling rounds 1–3 plus notation/strategy follow-ups). Every decision adopted the recommended option; the frontier is empty.

| ID | Question | Decision |
|---|---|---|
| D1 | Input scope | Absolute URIs/IRIs only; relative and protocol-relative refs unrecognized |
| D2 | Normative authority | WHATWG URL Standard = single pipeline; RFC 3986 §6.2 rejected as algorithm, kept as provenance |
| D3 | IRI scope | Full IRI: non-ASCII host → UTS #46 punycode; path/query/fragment → UTF-8 percent-encoding |
| D4 | Losslessness | Preserve fragment, userinfo, empty `?`/`#`, trailing host dot, port 0, encoding case |
| D5 | Scheme handling | WHATWG special-scheme split (ftp/file/http/https/ws/wss full pipeline; others opaque) |
| D6 | Query normalization | Verbatim: no param sorting, `+` literal; special-query set percent-encodes space, `"`, `<`, `>`, `'` |
| D7 | Recognition scope | Spans in prose (house convention) |
| D8 | Invalid-input policy | WHATWG semantics exactly: fatal → unrecognized; recoverable → canonical + provenance |
| D9 | Unicode normalization | No NFC; RFC 3987 §5.3.2.2 recorded as considered/deferred |
| D10 | Canonical value shape | Serialized string (`href`-equivalent) |
| D11 | Rule decomposition | One rule: WHATWG URL Standard (parse + serialize is one algorithm) |
| D12 | Capability name | `URL` (`paxman/capabilities/URL/`) |
| D13 | IDNA data | Vendored UTS #46 tables + committed generator (ISBN pattern); zero runtime deps |
| D14 | Contract surface | Minimal, no feature flags |
| D15 | Notation shape | `URLNotation(text: str)` + `as_list()` |
| D16 | Grammar substance | One regex grammar, scheme-anchored, ≥1 body char after colon |

---

## 10. Glossary

- **URL** — Uniform Resource Locator; an identifier for a retrievable resource with an absolute scheme. This capability's name and domain.
- **URI** — Uniform Resource Identifier; the RFC 3986 term for the syntax `scheme ":" …`. Every URL is a URI; "URL" is used where the resource is locatable. (RFC 3986 §1.1.3.)
- **IRI** — Internationalized Resource Identifier; a URI that may contain non-ASCII characters (RFC 3987 §2).
- **Scheme** — the leading `ALPHA *( ALPHA / DIGIT / "+" / "-" / "." )` component that selects the interpretation rules (RFC 3986 §3.1).
- **Special scheme** — WHATWG's fixed set (ftp, file, http, https, ws, wss) that receives the full parser with default ports (WHATWG §4.4).
- **Percent-encoding** — the `%HH` escape syntax for octets not representable literally (RFC 3986 §2.1). WHATWG preserves it byte-for-byte; RFC 3986 §6.2.2.2 recommends decoding unreserved.
- **Default port** — the port a special scheme implies (http:80, https:443, ftp:21, ws:80, wss:443; file:null). Elided by the serializer when equal (WHATWG §4.5).
- **Dot-segment** — `.` / `..` path components removed by the `remove_dot_segments` algorithm (RFC 3986 §5.2.4; WHATWG §4.4).
- **UTS #46** — Unicode Technical Standard 46, "Unicode IDNA Compatibility Processing"; the mapping WHATWG mandates for internationalized hosts (WHATWG §3.3).
- **IDNA** — Internationalized Domain Names in Applications; the framework for encoding non-ASCII domain labels.
- **Punycode** — the ASCII-compatible encoding used by IDNA for non-ASCII labels (e.g. `münchen` → `xn--mnchen-3ya`).
- **Opaque path** — the path of a non-special scheme parsed without authority/path splitting (WHATWG §4.4 opaque path state); spaces preserved raw.
- **Validation error / fatal error** — WHATWG's two error classes; fatal aborts parsing (→ Paxman: unrecognized); validation errors are flagged recoveries (→ Paxman: canonical + provenance).
- **RecognitionMatch** — the grammar-layer span result: `notation`, `start`, `end`, `raw_text` with `len(raw_text) == end - start` (paxman core domain).
- **Canonical value** — the byte-identical serialized output for a given input + contract; here, the WHATWG-serialized URL string.
- **Provenance** — the rule-layer record of which specification sections produced the canonical value, including considered-and-rejected sources and recoveries applied.
- **NFC** — Unicode Normalization Form C (canonical composition); RFC 3987 §5.3.2.2's conditional recommendation, deliberately deferred (D9).
- **Lossless canonicalization** — the property that no preserved component is dropped or elided (D4): the WHATWG serializer rewrites only what it must (default ports, dot segments, IPv4 bases, IDNA hosts), never the preserved components.

---

## Sources

**Primary (fetched and section-verified this session):**

1. [RFC 3986] — T. Berners-Lee, R. Fielding, L. Masinter, "Uniform Resource Identifier (URI): Generic Syntax", STD 66, January 2005. `https://www.rfc-editor.org/rfc/rfc3986.txt` (local: `/tmp/opencode/url-research/rfc3986.txt`).
2. [RFC 3987] — M. Dürst, M. Suignard, "Internationalized Resource Identifiers (IRIs)", January 2005. `https://www.rfc-editor.org/rfc/rfc3987.txt` (local: `/tmp/opencode/url-research/rfc3987.txt`).
3. [WHATWG URL Standard] — A. van Kesteren, "URL", WHATWG Living Standard. `https://url.spec.whatwg.org/` (local: `/tmp/opencode/url-research/whatwg-url.txt`; §1.3, §3.3–3.7, §4.4–4.8 verified).
4. [UTS #46] — M. Davis, "Unicode IDNA Compatibility Processing", Unicode Technical Standard 46. Referenced via WHATWG §3.3; tables to be vendored per D13.

**Empirical verification (this session):**

5. Node.js `new URL()` behavior — scripts `verify-whatwg.mjs`, `verify-whatwg2.mjs`, `verify-whatwg3.mjs`, `verify-whatwg4.mjs` in `/tmp/opencode/url-research/`; outputs reproduced in §4.

**Project references:**

6. `docs/development/MILESTONE.md` — row 4 (URL capability: strategy PARSER; provenance RFC 3986/3987/WHATWG).
7. `paxman/capabilities/IP/` — PARSER-strategy sibling (regex grammar + validating rule).
8. `paxman/capabilities/Email/notation.py`, `paxman/core/domain.py` — notation and span conventions.
9. `tools/regenerate_isbn_range_data.py` — the generated-data-module pattern adopted for UTS #46 tables (D13).
