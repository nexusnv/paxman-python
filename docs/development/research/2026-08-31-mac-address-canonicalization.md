# MAC Address Canonicalization Research - paxman-python

**Date:** 2026-08-31
**Scope:** Primary-source survey of the MAC address domain (IEEE EUI-48 and EUI-64 identifiers, IEEE 802 overview-and-architecture standards, IEEE Registration Authority block registries, RFC 7042 IETF usage, RFC 2469 canonical-order caution, Bluetooth/IEEE 802.15.4-Zigbee/PostgreSQL ecosystem notation), ecosystem canonicalization practices, and Paxman's grammar/rule/provenance architecture, to ground the design of a future `MacAddress` capability. No source code, tests, or configuration were modified.
**Evidence basis:** RFC 7042 (BCP 141, fetched in full), RFC 2469 (fetched in full), IEEE Registration Authority FAQ and MAC products pages (fetched), IEEE Std 802-2014 catalogue page + 802c-2017 amendment record (fetched), Bluetooth Core 6.0 Part B Baseband BD_ADDR text (via search excerpt), PostgreSQL 18 Network Address Types documentation (fetched in full), python-stdnum `stdnum/mac.py` (fetched in full), validator.js `isMACAddress.js` (fetched in full), Go `net/mac.go` `ParseMAC` (fetched in full), netaddr EUI strategy/dialects (tutorial + `strategy/eui48.py` source), Rust `macaddr` crate docs (fetched), HL7 Terminology ZigBee Address NamingSystem (via search excerpt), Wikipedia MAC address (secondary, fetched). Shipped Paxman capabilities (BIC, IBAN, ISBN, ISSN, ISIN, Country, Phone, IP) as architectural precedents, with the BIC grammar/notation read verbatim from the working tree. Repo state: `research/mac-address-canonicalization` @ `cc8d8b7` (from `dev`) — engine owns per-grammar containment dedup, total recognition ordering, and `Capability.format_value()` presentational seam.
**Conventions grounding this report:** [HOW_TO_ADD_NEW_CAPABILITY.md](../../HOW_TO_ADD_NEW_CAPABILITY.md), [HOW_TO_ADD_NEW_GRAMMAR.md](../../HOW_TO_ADD_NEW_GRAMMAR.md), [ARCHITECTURE.md](../../ARCHITECTURE.md), and the ISSN research precedent [`docs/development/research/2026-08-21-issn-canonicalization.md`](2026-08-21-issn-canonicalization.md) plus the IBAN precedent [`docs/development/research/2026-08-22-iban-canonicalization.md`](2026-08-22-iban-canonicalization.md), the BIC precedent [`docs/development/research/2026-08-23-bic-canonicalization.md`](2026-08-23-bic-canonicalization.md), and the ISIN precedent [`docs/development/research/2026-08-24-isin-canonicalization.md`](2026-08-24-isin-canonicalization.md).

---

## Executive Summary

MAC address is a strong fit for a Paxman capability: it has an unambiguous canonical form (**colon-separated uppercase hex octets, exactly 12 or 16 hex digits**: `00:1A:2B:3C:4D:5E` for EUI-48 or `00:1A:2B:3C:4D:5E:66:77` for EUI-64), a stable lineage of single-part standards (**IEEE Std 802-2024** Overview and Architecture, current, "specifies the structure of IEEE 802 MAC addresses", preceded by IEEE Std 802-2014 §8.2 "Universal addresses" which the Bluetooth Core Specification cites normatively) with the **IEEE Registration Authority** as the registration authority for Ethernet parameters (successor to Xerox Corporation, per RFC 7042 §1.3), maintained authoritative registries (**MA-L / MA-M / MA-S** MAC address blocks plus the IEEE OUI public listing at `regauth.standards.ieee.org`), and the best-understood multi-notation human surface of any identifier domain (colon, hyphen, Cisco tri-dot, bare hex, bit-reversed Token-Ring/FDDI form, EUI-64 family — all attested by ≥2 ecosystem validators). The domain mirrors Paxman's value proposition for IBAN/BIC/ISSN: recognizing the tolerant human surface (case, separators, optional `MAC` label), validating strictly against the authority (structure per IEEE 802; no checksum — like BIC, structure is all there is), and returning a canonical value with full provenance. The **EUI-64 family and IoT carriers (Zigbee, Thread, 802.15.4, FireWire, InfiniBand GUIDs, Bluetooth BD_ADDR) are first-class citizens**, not afterthoughts.

Key findings that shape the design:

1. **Canonical form is colon-separated uppercase hex octets.** Every syntactically valid EUI-48/EUI-64 is exactly 12 or 16 hex digits once separators are stripped; there is **no checksum, no per-domain charset exception, no check-character analogue** (unlike IBAN/ISBN/ISSN/ISIN) — the full first-octet range 0x00–0xFF is valid, with the I/G bit (0x01, multicast) and U/L bit (0x02, locally administered) being *informative predicates*, never validity gates (python-stdnum, Rust `macaddr`, and netaddr all expose them as boolean queries, and none rejects on them). Colon is the dominant interchange form across Unix tooling, PostgreSQL output, Bluetooth, Zigbee/Thread, Rust `macaddr` Display, and python-stdnum's own "minimal, consistent representation"; IEEE 802's human-friendly display is hyphenated; Cisco IOS prints tri-dot. This maps onto Paxman's presentational-only invariant: `format_value()` renders `colon` (default), `hyphen`, `bare`, `cisco`, `eui64`, and `bit_reversed` without touching validity.

2. **One grammar suffices for both lengths.** Unlike ISBN (two grammars, distinct semantics, `include_isbn10` gating), EUI-48 and EUI-64 are two *lengths* of one identifier family, and an 8-octet EUI-64 **contains** 6-octet EUI-48 sub-runs (`00:1A:2B:3C:4D:5E:66:77` contains the EUI-48-shaped run `3C:4D:5E:66:77`). Two grammars would preserve cross-grammar containment (`orchestrator:_dedup_spans` never dedups across grammars) and produce spurious `AMBIGUOUS` with two different canonical values (12-hex vs 16-hex). A single `MacAddressRecognitionGrammar` resolves every embedded-prefix and truncated-run case via three mechanisms: per-separator-family branch ordering (64-octet before 48-octet; 16-hex before 12-hex bare), a stacked mid-run lookbehind (`(?<!\w)(?<![0-9A-Fa-f][-.:])` - `phone_national()` precedent), and a 48-bit-only truncation guard (`(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))`) blocking the "separator + 2 terminating hex digits" signature, plus the engine's within-grammar longer-wins dedup as the final safety net.

3. **Validation is structure-level, with an optional gated registry layer.** Level 1 (`PARSER`, always active, publication IEEE Std 802): length in {12, 16} hex, consistent separator per mention (the backreference-equivalent branch construction; Go checks `s[2]` once, validator.js uses `\1`, PostgreSQL says "separated consistently"), charset `[0-9A-F]`. Level 2 (`LOOKUP_TABLE`, **gated** behind `include_oui_validation=False`, `kind="registry"`): OUI membership in an IEEE MA-L/MA-M/MA-S snapshot for *universally administered* addresses only (U/L bit 0) — the python-stdnum `validate_manufacturer` behavior (checked by default for universal addresses, skipped for local ones) plus the ISBN Range Message / IBAN SWIFT Registry gating precedent; locally administered addresses (U/L bit 1, including IEEE 802c SLAP quadrants, Bluetooth random static, Wi-Fi randomization) skip the registry by construction.

4. **Bit-reversed forms are recognized as themselves, never reinterpreted.** Token Ring/FDDI/IBM/MSB "non-canonical" display (RFC 2469: canonical `12-34-56-78-9A-BC` bit-swaps per octet to `48-2C-6A-1E-59-3D`; PostgreSQL records the old IEEE 802-2001 colon-vs-hyphen bit-order convention and notes it is "widely ignored nowadays") is **syntactically indistinguishable** from a canonical MAC. Paxman cannot and must not apply world-knowledge to detect it (determinism by construction); the input resolves to its literal identity, and a `bit_reversed` offered format renders the per-octet bit-swap of the canonical value deterministically. This mirrors the ISIN transposed-letter checksum flaw precedent: documented, never corrected.

5. **Provenance is cleanly split** per HOW_TO_ADD_NEW_CAPABILITY.md Step 5 (one file per publication, one `PUBLICATION: Provenance` constant, one `Rule` class per section): `IEEE Std 802-2024` (active; structure, U/L and I/G bit semantics, EUI-48/EUI-64 definitions; 802-2014 §8.2 cited by Bluetooth as normative) owns generic structure; the `IEEE Registration Authority MA-L/MA-M/MA-S public listing` (`kind="registry"`, rolling) owns optional OUI-membership validation behind `requires_features`; RFC 7042, RFC 2469, IEEE 802c-2017 (SLAP), the Bluetooth Core Specification, and the IEEE EUI tutorial are evidence, not rule publications.

Recommended file layout, rule set, notation, and contract are specified in §6, §10, §11. Open decisions and their recommendations are in §13.

---

## 1. Target User

| Persona | Why they need MAC address canonicalization | Typical context |
|---------|---------------------------------------------|-----------------|
| **Network / infrastructure engineers** | Normalize `00:1a:2b:3c:4d:5e` vs `00-1A-2B-3C-4D-5E` vs `001a.2b3c.4d5e` vs `001A2B3C4D5E` to one key for ACL entries, DHCP reservations, MAC filtering, switch port-security tables, and cross-vendor tool joins (Cisco tri-dot vs Unix colon vs Windows hyphen) | Switch/ACL configuration, NAC onboarding, network-inventory reconciliation, config-drift detectors |
| **IoT / device-fleet engineers** | Canonicalize Zigbee/Thread/802.15.4 EUI-64 IEEE addresses (`a4:c1:38:0c:ac:70:4c:37`) and Bluetooth BD_ADDRs across device registries, commissioning records, and telemetry labels; the EUI-64 IoT surface (HL7's ZigBee Address, Home Assistant device configs) mixes case and carries `ff:fe` mid-address | Matter/Thread commissioning, Zigbee coordinator tables, BLE provisioning, fleet inventories |
| **Security / incident-response teams** | Extract and dedup MAC mentions from logs, ARP/NDP dumps, packet captures, and IoC reports with span-bearing provenance; correlate vendor (OUI) when a registry snapshot is opted in | Forensic log mining, SIEM enrichment, rogue-device tracking, MAC-randomization awareness (U/L bit) |
| **Data engineering / asset-management pipelines** | Join on a canonical key across CSV exports (bare hex), PostgreSQL `macaddr` columns, Windows tooling (hyphens), and free-text runbooks; dedup the same NIC across display variants | ETL normalization, CMDB dedup, LLM extraction post-processing, inventory audit |

**User-visible contract:** The caller supplies raw human text (free-form, possibly containing zero, one, or many MAC mentions) and a contract; Paxman returns one canonical MAC address (or `MISSING`/`INVALID`/`AMBIGUOUS`) with citation. This mirrors BIC (`bic` compact default) and IBAN (`electronic` default) ergonomics, but the canonical default is **colon-separated uppercase octets** (`00:1A:2B:3C:4D:5E` / 8 octets for EUI-64), with `hyphen`, `bare`, `cisco`, `eui64`, and `bit_reversed` as presentational alternatives.

---

## 2. Shape of Input (Human Surface)

### 2.1 Recognition-surface inventory - every distinct written form (MANDATORY)

Attested written representations of one MAC address value, from the IEEE 802/RA corpus, RFC 7042's own notation, ecosystem validator strip/emit logic (validator.js separator classes, netaddr dialects, Go `ParseMAC` format list, PostgreSQL input table — removed/accepted separators are direct evidence of wild forms), and real device-fleet corpora (Bluetooth, Zigbee/Thread/Home Assistant, Cisco IOS):

| Form | Example | Attested where | Prevalence | Paxman v1 decision | Grammar mechanism |
|------|---------|----------------|------------|--------------------|-------------------|
| Colon-separated EUI-48 | `00:1A:2B:3C:4D:5E` | Unix `ifconfig`/`ip link` output, Go `HardwareAddr.String()`, PostgreSQL `macaddr` output form, Bluetooth BD_ADDR display, Rust `macaddr` Display default, python-stdnum `validate()` output ("minimal, consistent representation") | canonical de-facto + common | **RECOGNIZE** | colon branch (main pattern body) |
| Hyphen-separated EUI-48 | `00-1A-2B-3C-4D-5E` | IEEE 802 standard human-friendly form ("six groups of two hexadecimal digits, separated by hyphens", Wikipedia/IEEE EUI tutorial; PostgreSQL: "IEEE Standard 802-2001 specifies the second form shown (with hyphens)"), Windows `ipconfig`/`getmac`, RFC 7042's own notation ("Successive octets are separated by a hyphen"), netaddr `mac_eui48` default, python-stdnum `to_eui48()` | official display + common | **RECOGNIZE** | hyphen branch |
| Cisco tri-dot hextets | `001A.2B3C.4D5E` | Cisco IOS `show` outputs, netaddr `mac_cisco` dialect ("Cisco 'triple hextet' MAC address dialect class"), Go `ParseMAC` dot form (`0000.5e00.5301`), PostgreSQL input, Wikipedia notation section, validator.js `macAddress48WithDots` | common (networking) | **RECOGNIZE** | dot branch (3 x 4-hex) |
| Bare/compact hex EUI-48 | `001A2B3C4D5E` | netaddr `mac_bare` dialect, Go `ParseMAC` bare form, PostgreSQL input, validator.js `macAddress48NoSeparators`, DB/API dumps | common (DB keys) | **RECOGNIZE** | bare branch (12 hex) |
| EUI-64 colon (8 octets) | `00:1A:2B:3C:4D:5E:66:77` | Zigbee/Thread/IEEE 802.15.4 extended address (HL7 ZigBee NamingSystem: "8 bytes written in hexadecimal and separated by colons (example - DF:3B:00:11:22:33:FF:EE)"), Home Assistant device configs, IPv6 IID base, FireWire, InfiniBand GUIDs, Go `ParseMAC` n=8, validator.js `macAddress64`, PostgreSQL `macaddr8` | official for 64-bit domains + common | **RECOGNIZE** | colon-64 branch |
| EUI-64 hyphen | `00-1A-2B-3C-4D-5E-66-77` | IEEE display form "also commonly used for EUI-64" (Wikipedia citing IEEE EUI tutorial), PostgreSQL `macaddr8` input | common | **RECOGNIZE** | hyphen-64 branch |
| EUI-64 dot hextets | `001A.2B3C.4D5E.6677` | validator.js `macAddress64WithDots`, PostgreSQL `macaddr8` (`0800.2b01.0203.0405`), Go `ParseMAC` dot form | occasional | **RECOGNIZE** | dot-64 branch (4 x 4-hex) |
| EUI-64 bare hex | `001A2B3C4D5E6677` | validator.js `macAddress64NoSeparators`, Go `ParseMAC`, PostgreSQL `macaddr8` input | occasional | **RECOGNIZE** | bare branch (16 hex, tried before 12) |
| Modified EUI-64 (IPv6 IID / Zigbee derived) | `02:00:5E:FF:FE:yy:yy:yy`; real Zigbee `84:71:27:ff:fe:93:17:24` | RFC 7042 §2.2.1 (U/L-bit inverted + `FF-FE` inserted), RFC 4291 App A, PostgreSQL `macaddr8_set7bit` (`08:00:2b:01:02:03` → `0a:00:2b:ff:fe:01:02:03`), attested mid-address `ff:fe` in Home Assistant Zigbee addresses | common in IPv6/Zigbee corpora | **RECOGNIZE** (lexically a plain EUI-64; U/L-flip and FF-FE semantics documented, never reinterpreted — see §4.2/§14) | colon-64 branch |
| Bit-reversed / non-canonical / Token Ring / FDDI / MSB / IBM form | `48-2C-6A-1E-59-3D` (per-octet bit-swap of canonical `12-34-56-78-9A-BC`) | RFC 2469 §2 (full worked figure), Wikipedia §4.1, PostgreSQL note ("IEEE Standard 802-2001 ... specifies the first form (with colons) as used with bit-reversed, MSB-first notation, so that 08-00-2b-01-02-03 = 10:00:D4:80:40:C0. This convention is widely ignored nowadays") | rare (legacy Token Ring/FDDI tooling) | **RECOGNIZE as-is** (syntactically indistinguishable from canonical; identity is the literal string; `bit_reversed` offered format renders the deterministic per-octet swap — see §13 decision 10) | any branch (no lexical marker exists) |
| 24-bit-word colon/hyphen (PostgreSQL form) | `08002b:010203` (also `08002b-010203`) | PostgreSQL `macaddr` input table, netaddr `mac_pgsql` dialect ("A PostgreSQL style (2 x 24-bit words) MAC address dialect class") | occasional | **DEFER** (community `extra_grammars` candidate; v1 keeps the hextet grammar definitive — rationale §13 decision 5) | none in v1 |
| Single-hex-digit octets (no leading zeros) | `0:1b:77:49:54:fd` | netaddr `mac_unix` output (`word_fmt = '%x'`, no zero-fill), netaddr `RE_MAC_FORMATS` `([0-9A-F]{1,2})` octets, python-stdnum `compact()` zero-pads single-digit elements (input tolerance) | common in Unix tooling output | **DEFER** (1-2-digit octet tolerance collides with IPv6 textual forms — an all-short-group IPv6 like `0:0:0:0:0:0:0:1` would be claimed as a local EUI-64; exactly-2-digit is the Go/validator.js/PostgreSQL consensus — rationale §13 decision 5) | none in v1 |
| Whitespace as separator | `00 1A 2B 3C 4D 5E` | validator.js separator class `([-:\s])` (the only ecosystem validator accepting whitespace) | rare | **DEFER** (single-validator attestation; whitespace-separated hex runs are prose-adjacent) | none in v1 |
| `MAC` label-prefixed prose | `MAC: 00:1A:2B:3C:4D:5E`, `MAC 00-1A-...`, `mac - 001a.2b3c.4d5e` | device inventories and config exports; the shipped IBAN/ISSN/ISBN/BIC label-fusion precedent (`(?:(?:BIC|SWIFT)[\s:-]+)?` in `paxman/capabilities/BIC/grammar/bic_recognition.py`) | common | **RECOGNIZE** | fused optional `(?ai:MAC)[\s:-]+` label |
| Tool-context labels (`HWaddr`, `ether`) | `ether 00:1b:77:49:54:fd` (`ip link`), `HWaddr 00:1b:...` (legacy ifconfig) | ifconfig/iproute2 output labels | common (tool output) | **DEFER** (tool-specific labels, not identifier-display conventions; body still recognized without the label) | none in v1 |
| `EUI-48:` / `EUI-64:` prefixed | `EUI-48: 00-00-5E-00-53-01` | IEEE EUI documentation style, RFC 7043 RRTYPE examples discussions | rare | **DEFER** | none in v1 |
| Case variants (upper/lower/mixed) | `00:1a:2b:3c:4d:5e`, `A4:C1:38:0C:AC:70:4C:37` vs config-only lowercase (Home Assistant issue 42913: UI shows uppercase, `device_config:` keys require lowercase) | every validator is case-insensitive; the HA case-mismatch bug report is direct evidence that real systems mix case per field | universal | **RECOGNIZE** | `(?ai:...)` inline flags + `notation_fn` `.upper()` |
| InfiniBand 20-octet IPoIB link-layer address | `00:00:00:00:fe:80:00:00:00:00:00:00:02:00:5e:10:00:00:01` | Go `ParseMAC` ("or a 20-octet IP over InfiniBand link-layer address", n=20 accepted) | rare | **DEFER** (outside EUI-48/EUI-64 identifier space; Go-only attestation in this form) | none in v1 |

No other written form is attested: MAC addresses have no resolver-URI convention, no URN namespace (RFC 7043 defines DNS `EUI48`/`EUI64` RRTYPES carrying the bare address, not a URI scheme), no per-domain print exception, and no check-character analogue. The `bit-reversed` form is deliberately **RECOGNIZE-as-is** rather than REJECT: a bit-reversed spelling is a valid MAC for every validator; only its *provenance* (Token Ring display of a different canonical address) is lost, and Paxman's determinism rules forbid recovering it.

### 2.2 Wild variants - adversarial mutations of each inventoried form

Enumerated from the RFCs, IEEE 802/RA pages, PostgreSQL documentation, and real validators; stress-test every §2.1 RECOGNIZE form:

| # | Category | Example Inputs | Recognition concern |
|---|----------|----------------|---------------------|
| 1 | Canonical colon 48 | `00:1A:2B:3C:4D:5E`, documentation range `00:00:5E:00:53:01` | RFC 7042 assigned documentation values (unicast `00-00-5E-00-53-00`–`FF`); spec-adjacent master form |
| 2 | Canonical hyphen 48 (IEEE display) | `00-1A-2B-3C-4D-5E`, `01-23-45-67-89-AB` | IEEE 802 human-friendly standard form; RFC 7042's own textual notation is hyphenated |
| 3 | Lowercase / mixed case | `00:1a:2b:3c:4d:5e`, `De:Ad:Be:Ef:Ca:Fe`, `A4:C1:38:0c:AC:70:4C:37` | Case-insensitive charset; canonical uppercase (Paxman convention); HA issue shows systems disagree on case per field |
| 4 | Cisco tri-dot | `001a.2b3c.4d5e`, `001A.2B3C.4D5E` | 4-hex hextets with dot separators only; the dot branch must not accept 2-hex dot groups (`00.1a` is not a MAC form anywhere) |
| 5 | Bare compact | `001A2B3C4D5E`, `001a2b3c4d5e` | 12-hex run; git short-SHA collision surface (§14); no separators to anchor on |
| 6 | EUI-64 family | `00:1A:2B:3C:4D:5E:66:77`, `00-1A-2B-3C-4D-5E-66-77`, `001A.2B3C.4D5E.6677`, `001A2B3C4D5E6677` | All four separators x 64; contains EUI-48-shaped sub-runs — single grammar + longer-wins dedup |
| 7 | Modified EUI-64 (U/L flipped, FF-FE) | `02:00:5E:FF:FE:00:53:01`, `84:71:27:ff:fe:93:17:24` | Lexically an EUI-64; U/L bit set + `FF-FE` at octets 4-5; recognized as-is, semantics documented (RFC 7042 §2.2.1) |
| 8 | Bit-reversed (Token Ring/FDDI) | `48-2C-6A-1E-59-3D`, `10:00:D4:80:40:C0` | Per-octet bit-swap of canonical; indistinguishable lexically; resolves to itself; `bit_reversed` format renders the swap |
| 9 | Special/sentinel values | `FF:FF:FF:FF:FF:FF` (broadcast), `00:00:00:00:00:00` (nil), `01:80:C2:00:00:00` (STP), `33:33:00:00:00:01` (IPv6 ND multicast, RFC 7042 §2.3.1) | All syntactically valid; group bit 1 on broadcast/multicast/STP; never validity-gated (validators expose predicates only) |
| 10 | Label with colon/space/hyphen | `MAC: 00:1A:2B:3C:4D:5E`, `mac - 001a.2b3c.4d5e`, `MAC\t00-1A-...` | Case-insensitive `MAC`, `[\s:-]+` one-or-more never zero-width (BIC label precedent); `raw_text` includes label, `compact` does not |
| 11 | Glued label without separator | `MAC001A2B3C4D5E`, `MAC001A.2B3C.4D5E` | Label branch needs `[\s:-]+` → fails; body branch cannot carve (M is not hex; word_only blocks mid-token) → `MISSING` (§4.2 analysis) |
| 12 | Mixed separators | `00:1A-2B:3C-4D:5E`, `001A.2B3C:4D5E` | No validator accepts: validator.js backreference `\1`, Go checks one separator char (`s[2]`/`s[4]`), PostgreSQL "separated consistently" → `MISSING` |
| 13 | Over-long / under-long | `00:1A:2B:3C:4D:5E:66` (7 octets), `001A2B3C4D5` (11 hex), `001A2B3C4D5E6` (13 hex), `0:1A:2B:3C:4D:5E` (5.5 octets) | Only 12 or 16 hex valid; 7-octet colon run must not be claimed; bare 13-hex must not yield inner 12-hex (word_only + trailing guard) |
| 14 | Ecosystem-only tolerances (deferred) | `0:1b:77:49:54:fd` (1-digit octets), `08002b:010203` (24-bit words), `00 1A 2B 3C 4D 5E` (whitespace sep) | netaddr/stdnum/validator.js/Go/PG each accept a superset Paxman v1 defers; documented DEFER, not silent blindness (§2.1, §13 decision 5) |
| 15 | Invalid charset / OCR homoglyphs | `00:1A:2B:3C:4D:OG` (letter O), `００:1A:2B:3C:4D:5E` (fullwidth zeros), `00:1A:2B:3C:4D:G5` | Strict `(?ai:)` ASCII hex; no autocorrection; fullwidth digits rejected → `MISSING` |
| 16 | Quoted / bracketed / embedded | `"00:1A:2B:3C:4D:5E"`, `[001A.2B3C.4D5E]`, `MAC address of eth0 is 00:1A:2B:3C:4D:5E (eth0)` | Punctuation is non-word so `word_only` guards hold; parenthetical not swallowed; span-bearing extraction |
| 17 | Multiple per line | `from 00:1A:2B:3C:4D:5E to 00-1B-77-49-54-FD`, ACL lines `permit 001a.2b3c.4d5e 001a.2b3c.4d5f` | 2+ matches per call; identical values coalesce, distinct values `AMBIGUOUS`/`MultipleMentionsError` (`single_value=True`) |
| 18 | X-glued runs | `X001A2B3C4D5E`, `001A2B3C4D5EY`, `A001A2B3C4D5E6677B` | Stacked guard lookarounds (`(?<!\w)`/`(?!\w)` plus the mid-run hex-separator check) - never carved out of longer alphanum tokens (hex chars are `\w`) |

**Real-world regex / validation snippets (ecosystem evidence):**

| Source | Pattern / Logic |
|--------|-----------------|
| `arthurdejong/python-stdnum` `stdnum/mac.py` | `compact(number) = clean(number, ' ').strip().lower().replace('-', ':')` + zero-pads single-digit elements; `_mac_re = re.compile('^([0-9a-f]{2}:){5}[0-9a-f]{2}$')` applied **after** compacting; canonical output is lowercase colon; `validate_manufacturer` checks OUI against IEEE `numdb` for universally administered addresses (`int(number[:2], 16) & 2 == 0`); predicates `is_unicast` (`& 1 == 0`), `is_broadcast`, `is_multicast`, `is_locally_administered` |
| `validatorjs/validator.js` `isMACAddress.js` | `macAddress48 = /^(?:[0-9a-fA-F]{2}([-:\s]))([0-9a-fA-F]{2}\1){4}([0-9a-fA-F]{2})$/` — backreference `\1` enforces **one consistent separator per mention** (colons, hyphens, or whitespace); `macAddress48NoSeparators = /^([0-9a-fA-F]){12}$/`; `macAddress48WithDots = /^([0-9a-fA-F]{4}\.){2}([0-9a-fA-F]{4})$/`; 64-bit siblings with `{6}`/`{2}`/`{3}` counts; `options.eui` selects `'48'`/`'64'` |
| `golang/go` `src/net/mac.go` `ParseMAC` | Doc comment enumerates the accepted formats verbatim: `00:00:5e:00:53:01`, `02:00:5e:10:00:00:00:01`, 20-octet IPoIB, hyphen twins, `0000.5e00.5301` (dot hextets), `00005e005301` (bare); implementation dispatches on `s[2]` (`:`/`-`) or `s[4]` (`.`) and enforces lengths n ∈ {6, 8, 20} — one consistent separator per mention by construction |
| `netaddr/netaddr` `strategy/eui48.py` | `RE_MAC_FORMATS` regex list: 6 x `([0-9A-F]{1,2})` joined by `:` then by `-`; 3 x `([0-9A-F]{1,4})` joined by `:` then by `-`; 2 x 6-digit; bare — note the `{1,2}`/`{1,4}` width tolerance (the loosest ecosystem set) and the dialect classes `mac_eui48` (`-`), `mac_unix` (`:`, `%x` no zero-fill), `mac_unix_expanded` (`:`, `%.2x`), `mac_cisco` (`.` word_size 16), `mac_bare` (`''`), `mac_pgsql` (`:` word_size 24) |
| `svartalf/rust-macaddr` | Types `MacAddr6`/`MacAddr8` (EUI-48/EUI-64); `Display` renders `AB:0D:EF:12:34:56` (`{}`), `AB-0D-EF-12-34-56` (`{:-}`), `AB0.DEF.123.456` (`{:#}`); predicates `is_unicast`/`is_multicast`/`is_universal`/`is_local`/`is_broadcast`/`is_nil` — first-octet bit queries, never rejections |
| `PostgreSQL` 18 docs `datatype-net-types.html` | `macaddr` accepts **seven** input spellings (`08:00:2b:01:02:03`, `08-00-2b-01-02-03`, `08002b:010203`, `08002b-010203`, `0800.2b01.0203`, `0800-2b01-0203`, `08002b010203`), outputs always the colon form; `macaddr8` accepts 6- and 8-byte input, inserts `FF`/`FE` on 6→8, `macaddr8_set7bit` performs the IPv6 modified-EUI-64 U/L flip (`0a:00:2b:ff:fe:01:02:03`); "IEEE Standard 802-2001 specifies the second form (with hyphens) as the canonical form ... and the first form (with colons) as used with bit-reversed, MSB-first notation, so that 08-00-2b-01-02-03 = 10:00:D4:80:40:C0. This convention is widely ignored nowadays" |

**Normalization contract (reuse BIC/ISBN emit pattern):**

```python
# After the regex has validated shape and separator consistency, the
# notation_fn strips separators and case-folds exactly like the shipped BIC
# grammar (paxman/capabilities/BIC/grammar/bic_recognition.py):
compact = "".join(ch for ch in raw if ch.isascii() and ch.isalnum()).upper()
# compact is now 12 or 16 chars of [0-9A-F]; shape = "eui64" if len == 16 else "eui48"
```

### 2.3 What input is NOT a MAC address mention

- **IPv6 addresses** — 4-hex-digit groups with `::` compression (`fe80::1`, `2001:db8::1`): different capability, different Paxman grammar. The EUI-64 colon form with exactly-2-digit octets *is* textually a valid full IPv6 address (all 2-digit groups), so a caller pasting IPv6 into a MAC pipeline gets a candidate — cross-capability disambiguation is caller-owned (§14); this residual overlap is the reason v1 defers 1-2-digit octet tolerance (§2.1 row 12).
- **UUIDs** (`550e8400-e29b-41d4-a716-446655440000`, 36 with dashes; 32 bare) — disjoint length; `word_only` guards prevent carving 12/16-hex fragments out of UUID text.
- **git SHAs** — 40-hex full SHAs are too long; *abbreviated* SHAs at exactly 12 hex collide with bare MACs (§14, §13 decision 4). Other common lengths (7-11, 13-39) are rejected by length guards.
- **MEID** (14 hex), **IMEI** (15 decimal digits) — disjoint lengths.
- **CSS hex colors** (`#001A2B`, 6 hex after `#`) — too short; a `#` + 12-hex token would claim the bare 12 (not valid CSS anyway).
- **Short hex runs** (1-11 hex), bare country codes, port numbers — `MISSING` boundary (see §9).
- **802.15.4 16-bit short addresses** (`0x1234`) — a different Zigbee/802.15.4 identifier space; 4 hex digits is far under the 12-hex floor.

### 2.4 Single-mention vs multi-mention input

Paxman resolves **one mention per `canonicalize()` call** (ARCHITECTURE.md, segmentation recipe; `docs/recipes/segmentation.md` ADR-0004 companion). An input containing two distinct MAC addresses that normalize to different canonical values is `AMBIGUOUS` in the single-slice semantics (or `MultipleMentionsError` with `single_value=True` enforcement); the caller-owned segmentation path (split then canonicalize each slice) is the intended multi-entity pattern for ARP tables, ACL lines, and device inventories. Identical MAC mentions in one slice still coalesce to `SUCCESS` (candidate dedup by `(value, recognition_rule, validation_rule)`).

---

## 3. Shape of Notation (Intermediate Representation)

### 3.1 Recommended notation - compact plus shape discriminator

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MacAddressNotation:
    """MAC address notation - grammar-normalized compact hex form.

    ``compact`` is the full identifier, uppercase hex, separators stripped:
    exactly 12 hex digits (EUI-48) or 16 hex digits (EUI-64).
    ``shape`` discriminates the two identifier lengths ("eui48" / "eui64"),
    mirroring the ISBN two-length precedent.

    The grammar never validates OUI membership or interprets the U/L and I/G
    bits; rules own that (grammar/rule boundary per HOW_TO_ADD_NEW_GRAMMAR.md).
    Derived rule-side values: OUI/first block = ``compact[:6]``; U/L bit =
    ``int(compact[0:2], 16) & 0x02``; I/G bit = ``int(compact[0:2], 16) & 0x01``.
    """

    compact: str  # e.g. "001A2B3C4D5E" (12) or "001A2B3C4D5E6677" (16) - uppercase [0-9A-F]
    shape: str  # "eui48" or "eui64" - length discriminator, mirroring ISBN
```

**Considered alternatives:**

- **Single field `compact` only (IP-style atomic, `IPNotation(address: str)`):** `len(compact)` already discriminates 48 vs 64, so a separate `shape` is logically redundant. Rejected for v1 because two lexical lengths with different downstream behavior (the `eui64` offered format is an expansion from EUI-48 and identity from EUI-64; rule expectations and test vectors differ per length) deserve an explicit, self-documenting discriminator exactly as ISBN ships `shape` for its 10/13 lengths, and because a frozen-slots 2-field dataclass costs nothing.
- **BIC-style full decomposition (`oui`, `extension`, `first_octet`, ...):** rejected — the rule layer's only lookup key is `compact[:6]` (ISIN slices `compact[0:2]` for its country prefix with the same reasoning), the U/L and I/G bits are single integer derivations from `compact[0:2]`, and no routing decision needs more. Adding six derived-string fields would freeze derivable data into the notation and invite drift between field values and `compact`.

**Invariants the grammar enforces (before rules):**

- `compact` is exactly 12 or 16 characters, all in `[0-9A-F]` (uppercased by the grammar from case-insensitive hex input).
- `shape == "eui48"` iff `len(compact) == 12`; `shape == "eui64"` iff `len(compact) == 16`. No other values are constructible.
- `raw_text` preserves the original span (label plus separators plus case); `compact` is the syntax-normalized token; `len(raw_text) >= len(compact)` always (equality for the bare form).
- Separator consistency (one of `:`, `-`, `.` per mention, or none) is enforced by the pattern's per-separator branches, never by post-hoc filtering.

### 3.2 Why not carry separators or labels in the notation

Separators, grouping, and the `MAC` label have **no lexical significance** for validity — the identifier is the 48/64-bit value; every ecosystem validator strips separators before its real check, and PostgreSQL normalizes all seven accepted input spellings to one output form. Compact and separated forms of the same address have the same identity regardless of input spelling; dedup and status logic operate on `compact`. Presentation is `Capability.format_value()` only — the canonical colon form and the offered `hyphen`/`cisco`/`bare` renderings are re-insertions of separators onto `compact`, never re-parses.

### 3.3 Why `shape` is a free `str`, not a `Literal`

ISBN ships a two-value discriminator and ISIN/Country demonstrate the free-`str` + rule-validation alternative for vocabularies. For `shape` the value set is closed (`"eui48"`, `"eui64"`) and constructible only by the grammar, so either typing works; the recommendation is a plain `str` field with the invariant documented in the class docstring, matching the BIC notation's plain-`str` field style and keeping the notation importable without typing gymnastics in `matches()` comparisons. A `Literal` alias is a acceptable v2 refinement; nothing in the rule layer branches on anything but the two documented strings.

---

## 4. Grammar / Recognition Strategy

### 4.1 Strategy choice - Regex (structural pattern matching)

Per HOW_TO_ADD_NEW_GRAMMAR.md and HOW_TO_ADD_NEW_CAPABILITY.md Step 4, every shipped Paxman grammar is either **Regex** (distinctive shape: delimiters, fixed widths, character classes) or **Lexicon** (finite vocabulary of free-form tokens). MAC addresses have a maximally distinctive fixed-width shape (12 or 16 hex digits in 2-digit or 4-digit groups with one consistent separator family or none), so **Regex** is the correct strategy — the same choice as every hex-identifier grammar shipped to date (ISBN digits, ORCID, BIC alphanum, IP dotted-quad). No lexicon table is involved at recognition; the only vocabulary in the domain (the OUI registry) lives in the rule layer (§5.2) — grammar data stays key-free entirely (there are no recognition keys at all).

### 4.2 Reference pattern (adapted from BIC and ISSN verbatim precedent)

ISSN precedent (`paxman/capabilities/ISSN/grammar/issn_recognition.py`):
```python
_ISSN_BODY = r"(?:ISSN(?:-L|-H)?[\s:-]+)?(?P<body>\d{4}-?\d{3}[0-9Xx])"
_ISSN_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + _ISSN_BODY
    + BoundaryGuard.word_only().lookahead
)
```
Shipped BIC precedent (read verbatim from `paxman/capabilities/BIC/grammar/bic_recognition.py`, lines 101-106 and 125-138):
```python
_BIC_PATTERN = (
    BoundaryGuard.word_only().lookbehind
    + rf"(?!(?ai:(?:BIC|SWIFT){_BIC_SUFFIX_RE}\b))"
    + _BIC_BODY
    + BoundaryGuard.word_only().lookahead
)

class BICRecognitionGrammar(PipelineGrammar[BICNotation]):
    name = "bic_recognition"
    semantics = "bic_recognition"
    single_value = True
    pre = StandardPre[BICNotation](empty_guard=True)
    regex = RegexStage[BICNotation](pattern=_BIC_PATTERN, notation_fn=_bic_notation)
```

**Proposed MAC address pattern (single grammar, per-separator branches):**

```python
import re

from paxman.capabilities.MacAddress.notation import MacAddressNotation
from paxman.core.domain import RecognitionMatch
from paxman.core.grammar.boundary import BoundaryGuard
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.stages import RegexStage, StandardPre

# 2-hex octet / 4-hex hextet building blocks. Case handling is delegated to
# the (?ai:...) inline group (ASCII + IGNORECASE), exactly like the shipped
# BIC grammar; [0-9A-F] classes therefore accept a-f too.
_OCTET = r"[0-9A-F]{2}"
_HEXTET = r"[0-9A-F]{4}"

# Separator families are internally consistent per branch: each branch
# hard-codes its separator, so mixed-separator input ("00:1A-2B:...") can
# never match - the Python-re equivalent of validator.js's backreference \1
# and Go's single-separator dispatch, without group-number collisions across
# alternation branches.
_EUI48_COLON = rf"(?:{_OCTET}:){{5}}{_OCTET}"
_EUI64_COLON = rf"(?:{_OCTET}:){{7}}{_OCTET}"
_EUI48_HYPHEN = rf"(?:{_OCTET}-){{5}}{_OCTET}"
_EUI64_HYPHEN = rf"(?:{_OCTET}-){{7}}{_OCTET}"
_EUI48_DOT = rf"(?:{_HEXTET}\.){{2}}{_HEXTET}"
_EUI64_DOT = rf"(?:{_HEXTET}\.){{3}}{_HEXTET}"

# Bare forms split by length so the truncation guard can be applied to the
# 48-bit side only: 16 hex (4 hextets, tried first) and 12 hex (6 octets).
_BARE16 = rf"{_HEXTET}{_HEXTET}{_HEXTET}{_HEXTET}"
_BARE12 = rf"{_OCTET}{_OCTET}{_OCTET}{_OCTET}{_OCTET}{_OCTET}"

# Truncation guard (48-bit branches only): a 6-octet / 12-hex claim must not
# stand when immediately followed by a separator + exactly 2 terminating hex
# digits - the signature of a truncated final octet of a longer run
# ("00:1A:2B:3C:4D:5E:66" is a malformed 8-octet address, not a 6-octet one
# plus junk). The outer word_only lookahead cannot see this: ':'/'-'/'.' are
# not \w. EUI-64 claims are EXEMPT: "84:71:27:ff:fe:93:17:24-11" (Home
# Assistant's "{ieee}-{endpoint_id}" device_config key shape) must keep
# claiming the 8-octet address with the endpoint suffix as residue.
_TRUNCATION_GUARD = r"(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))"

# Branch ordering: all four 64-bit forms precede all four 48-bit forms and
# the 16-hex bare precedes the 12-hex bare, so finditer consumes the longest
# span at each scan position. The engine's within-grammar containment dedup
# ("longer wins", orchestrator:_dedup_spans) is the second safety net: any
# shorter same-start match (e.g. the EUI-48 prefix of an EUI-64) is fully
# contained in the emitted longer match and dropped. This is why ONE grammar
# must own both lengths - two grammars would preserve cross-grammar
# containment and produce spurious AMBIGUOUS with 12-hex vs 16-hex values.
_64_ALTS = "|".join([_EUI64_COLON, _EUI64_HYPHEN, _EUI64_DOT, _BARE16])
_48_ALTS = "|".join([_EUI48_COLON, _EUI48_HYPHEN, _EUI48_DOT, _BARE12])
_BODY_ALTS = f"{_64_ALTS}|(?:{_48_ALTS}){_TRUNCATION_GUARD}"

# Optional fused label: (?ai:MAC)[\s:-]+ one-or-more, never zero width
# (BIC/ISSN/IBAN label precedent). "MAC001A2B3C4D5E" (glued) cannot match:
# the label branch requires a separator, and no body branch can start at
# "M" (not a hex digit) or carve after it (word_only lookbehind sees \w).
_MAC_BODY = rf"(?ai:(?:(?:MAC)[\s:-]+)?(?P<compact>(?:{_BODY_ALTS})))"

# Mid-run lookbehind (stacked, phone_national() precedent in
# paxman/core/grammar/boundary.py:75-86): word_only alone treats ':'/'-'/'.'
# as boundaries, so the TAIL of a longer colon run would be claimed as a
# fresh 6-octet match ("00:1A:2B:3C:4D:5E:66" must not yield
# "1A:2B:3C:4D:5E:66"). The second lookbehind rejects a claim start preceded
# by hex + separator. It constrains only the MATCH START, so the fused label
# case is unaffected ("MAC:00:1A:..." starts at the M, preceded by
# non-hex+separator text; the label-internal "C:" boundary is mid-match and
# never lookbehind-checked).
_MAC_GUARD = BoundaryGuard(
    lookbehind=r"(?<!\w)(?<![0-9A-Fa-f][-.:])", lookahead=r"(?!\w)"
)

_MAC_PATTERN = _MAC_GUARD.lookbehind + _MAC_BODY + _MAC_GUARD.lookahead


def _mac_notation(match: re.Match[str]) -> MacAddressNotation:
    raw_compact = match.group("compact")
    compact = "".join(ch for ch in raw_compact if ch.isascii() and ch.isalnum()).upper()
    shape = "eui64" if len(compact) == 16 else "eui48"
    return MacAddressNotation(compact=compact, shape=shape)


class MacAddressRecognitionGrammar(PipelineGrammar[MacAddressNotation]):
    """MAC address recognition - EUI-48/EUI-64 in colon, hyphen, Cisco
    tri-dot, or bare hex form with optional fused ``MAC`` label.

    Recognizes all eight shape families (4 separators x 2 lengths, plus bare
    x 2 lengths). Case-insensitive; notation strips separators via
    isascii()/isalnum() and uppercases. One consistent separator per mention
    by construction. Does not interpret U/L or I/G bits and does not check
    OUI membership - rules own that.
    """

    name = "mac_address_recognition"
    semantics = "mac_address_recognition"
    single_value = True
    pre = StandardPre[MacAddressNotation](empty_guard=True)
    regex = RegexStage[MacAddressNotation](
        pattern=_MAC_PATTERN, notation_fn=_mac_notation
    )
```

*Notes on fidelity vs BIC/ISSN/IP:*

- Ship as a module-scope **string** pattern; `RegexStage` compiles once in `__post_init__` (`paxman/core/grammar/stages.py:62-90`, verified) - never compile inside `recognize()`.
- `(?ai:...)` inline ASCII + IGNORECASE, uppercase classes, `isascii() and isalnum()` filter in `notation_fn` - byte-for-byte the BIC technique (`paxman/capabilities/BIC/grammar/bic_recognition.py:25-29,111`), rejecting fullwidth digits and Unicode letter homoglyphs while `BoundaryGuard.word_only()` stays Unicode-aware.
- **Separator consistency without backreferences:** validator.js uses a capture + `\1`; Go dispatches on a single separator position. A Python alternation with one backreference per branch is unusable (group numbers are shared across branches), so consistency is achieved structurally - one branch per (separator, length) pair, each internally uniform. This is deterministic, pyright-clean, and per-branch readable.
- **No BIC-style glued-label negative lookahead is needed:** for BIC, `BICDEUTDEFF` is a *valid body claim* (all chars alphanumeric) so a lookahead is required to block it; for MAC, `M` is not in `[0-9A-F]`, so the body branch fails at the label position and `word_only` blocks any mid-token carve. Documented here so a reviewer does not "fix" the asymmetry.
- **Truncation guard (48-bit branches only):** the outer lookbehind/lookahead cannot see hex-after-separator continuation (`:`/`-`/`.` are not `\w`), so without it `00:1A:2B:3C:4D:5E:66` (a malformed 8-octet address) would falsely claim the 6-octet prefix - both at the run start (`00:1A:2B:3C:4D:5E` + `:66` residue) and, worse, as a shifted tail claim (`1A:2B:3C:4D:5E:66`, because plain `word_only` treats `:` as a boundary). Two mechanisms close the gap: the stacked mid-run lookbehind `(?<![0-9A-Fa-f][-.:])` (`phone_national()` precedent, `paxman/core/grammar/boundary.py:75-86`) rejects any claim start preceded by hex+separator, and the 48-branch-only truncation guard `(?!(?ai:[-:.][0-9A-F]{2}(?!\w)))` blocks the "separator + 2 terminating hex digits" signature at the claim end. EUI-64 claims are EXEMPT from the truncation guard so Home Assistant's `84:71:27:ff:fe:93:17:24-11` (`{ieee}-{endpoint_id}` device_config key) keeps claiming the 8-octet address. Documented consequences: `00:1A:2B:3C:4D:5E:66` → `MISSING`; `00:1A:2B:3C:4D:5E:6677` (4-hex residue) and `00:1A:2B:3C:4D:5E-3` (1-hex suffix) still claim; `001A2B3C4D5E:6677` claims the bare 12-hex; `001A2B3C4D5E-66` → `MISSING` (§8 rows 11-12).
- **`PostStage` is not needed** - unlike the E.164 15-digit window or URL paren-balance trims, every MAC shape is exactly bounded by its regex; no post-hoc span trimming exists.
- **The bare 12-hex branch and git-SHA collision** are accepted for v1 (ecosystem consensus: validator.js, Go, netaddr, PostgreSQL all accept bare); §14 documents the cross-domain false-positive surface and §13 decision 4 offers a contract gate as an option.
- **`recognize()` override is not needed initially** - unlike BIC (which filters grouped-English false positives), the MAC body has no English-prose shape overlap; the seven-octet and 13-hex mis-lengths are excluded by the quantifiers, not by filtering.

**Two lengths as one grammar vs two (the EUI-48/EUI-64 decision):**

- **(Recommended) Single grammar** with per-family branch ordering - EUI-64 spans contain EUI-48-shaped sub-spans, so within-grammar longer-wins dedup is *required* to keep one candidate; cross-grammar containment is never deduped by the engine (`orchestrator:_dedup_spans`), so two grammars would surface `00:1A:2B:3C:4D:5E:66:77` as both a 16-hex and a 12-hex candidate with different canonical values - spurious `AMBIGUOUS`. Same reasoning as BIC §4.2 (8 vs 11 in one grammar via optional group) and the opposite of ISBN (where 10-digit and 13-digit shapes do *not* nest after separator stripping, so two grammars were safe).
- **Alternative:** two grammars with coalesced `semantics` (HOW_TO_ADD_NEW_GRAMMAR.md option A) - rejected for the containment reason above; coalescing semantics would not fix cross-grammar span preservation, which is structural.

### 4.3 Recognition pipeline contract (ARCHITECTURE.md)

- Grammar emits **span-bearing** `RecognitionMatch[MacAddressNotation]` with half-open `[start, end)` and `raw_text == text[start:end]`; the engine validates the span invariant and raises `RecognitionError` naming the grammar on violation (`paxman/engine/orchestrator.py:_recognize`).
- `RegexStage` loops `re.finditer(text)` and builds `RecognitionMatch(notation=notation_fn(m), start=m.start(), end=m.end(), raw_text=m.group(0))` (verified `paxman/core/grammar/stages.py:74-90`); stages never mutate `text`.
- Engine owns **within-grammar containment dedup** ("longer wins"; identical spans keep first-emitted) and **total recognition ordering** `(start, end, active-set index, grammar name)` (`_dedup_spans`). Cross-grammar containment never dedups. For MAC this is what resolves the EUI-64/embedded-EUI-48 case and the bare 16-before-12 ordering.
- Candidate dedup `(value, recognition_rule, validation_rule)` runs after validation (`_dedup_candidates`); colon vs hyphen vs tri-dot spellings of one address collapse because rules normalize to the same default value.

### 4.4 Guard boundaries against sibling grammars

| Grammar | Shape | Collision analysis | Guards |
|---------|-------|--------------------|--------|
| MAC address | 12/16 hex, `:`/`-` 2-digit groups, `.` 4-digit hextets, bare | - | custom stacked guard `(?<!\w)(?<![0-9A-Fa-f][-.:])` / `(?!\w)` (mid-run tail claims blocked; `phone_national()` precedent) + 48-bit truncation guard |
| IPv6 (sibling capability) | 1-4 hex digit groups x 8, `::` compression | EUI-64 colon text with all-2-digit groups is a valid full IPv6 textual address (`0a:00:2b:ff:fe:01:02:03`); exactly-2-digit octet floor minimizes but does not eliminate overlap; `::` compression never matches a MAC branch (needs 8 groups without compression or balanced elision) | caller-owned cross-capability disambiguation; documented §14 |
| UUID | 32 hex bare / 36 dashed | Disjoint lengths; `word_only` prevents carving 12/16 out of 32/36 | length guards |
| git SHA | 7-40 hex, typically 12 abbreviated | Exactly-12 bare collides with bare MAC (§14); other lengths rejected | length guards + Open Decision 4 |
| MEID / IMEI | 14 hex / 15 digits | Disjoint lengths | length guards |
| CSS hex color | `#RRGGBB` (6 hex) | Too short for any branch | length guards |
| ISBN/ISSN/ORCID | digit/dash shapes | 4-3 dash ISSN and 3-5-5 ISBN hyphenations never match 2-2-2-2-2-2 colon/hyphen grouping; disjoint charsets at separator positions | separator family + length |

Concrete engine check (`orchestrator:_dedup_spans`): within the single MAC grammar, a same-start shorter match (EUI-48 inside EUI-64; 12-hex inside 16-hex bare) is contained and dropped - "longer wins"; cross-grammar duplication would never be deduped, which is exactly why one grammar owns both lengths (§4.2).

### 4.5 Semantics affinity (HOW_TO_ADD_NEW_GRAMMAR.md, ARCHITECTURE.md Community Extensions)

The grammar declares a non-empty `semantics` string (enforced by `Grammar.__init_subclass__`, `paxman/core/domain.py:297-306`); every validating `Rule` declares `target_semantics: frozenset[str]` (enforced non-empty and frozenset-typed, `domain.py:246-271`); the engine `_validate_affinity` fails fast (`ContractError`) if a rule names an id no grammar claims.

- `semantics = "mac_address_recognition"` (identity id) - the shipped recommendation; both rules (§5.2) target it.
- Coalesce only if a second grammar is later added (e.g. a community `mac_24bit_word_recognition` for the PostgreSQL 24-bit-word form, §2.1 row 11) - option A in HOW_TO_ADD_NEW_GRAMMAR.md, no rule edit needed since the shipped rules' `target_semantics` already includes the coalesced id.

### 4.6 `single_value` - one mention per call vs batch processing

Shipped capabilities (BIC `single_value = True`, verified; ISBN, Country, Money, Phone likewise) set `single_value=True`, consistent with Paxman "one canonical value per `canonicalize()` call" (`MultipleMentionsError` when distinct recognized mentions in one slice resolve to different canonical values; identical values coalesce to `SUCCESS`). ARP tables, switch FDB dumps, and ACL lines legitimately contain many MACs per document.

Recommendation: **initial `single_value=True`** (shipped precedent), with the documented caller-owned segmentation path (`docs/recipes/segmentation.md`). A free-text batch community grammar with `single_value=False` can be offered via `extra_grammars` when needed.

---

## 5. Provenance - the Authority that Validation Will Be Made Against

### 5.1 Authoritative spec and lineage

| Attribute | Finding |
|-----------|---------|
| **Governing publisher** | **IEEE** - IEEE Std 802 family, Overview and Architecture standard ("IEEE Standard for Local and Metropolitan Area Networks: Overview and Architecture"); the 802 catalogue page states it "specifies the structure of IEEE 802 MAC addresses" (802-2014 wording; 802-2024: "it specifies the structure of IEEE 802 MAC addresses") |
| **Registration Authority (RA)** | **IEEE Registration Authority (IEEE RA)** - successor to Xerox Corporation as registration authority for Ethernet parameters (RFC 7042 §1.3: "Originally the responsibility of Xerox Corporation, the registration authority for Ethernet parameters is now the IEEE Registration Authority"); administers MA-L, MA-M, MA-S MAC address blocks, OUI and CID registries, and the public listing at `regauth.standards.ieee.org` |
| **Spec name** | `IEEE Standard for Local and Metropolitan Area Networks: Overview and Architecture` (IEEE Std 802) |
| **Current edition** | **IEEE Std 802-2024** (per the IEEE catalogue's "within the 10-year lifecycle" listing; the 802-2014 page is marked "Superseded Standard ... Revised By: IEEE 802-2024"). The normative §8.2 "Universal addresses" clause citation below follows IEEE Std 802-2014 numbering, as cited verbatim by the Bluetooth Core Specification; verify the clause number against the 802-2024 text at implementation time (the standard is free via the IEEE GET Program) |
| **Check character system** | **None** - MAC addresses have no checksum and no check character (proved by absence in IEEE 802/EUI-48 tutorial structure, RFC 7042, and all six ecosystem validators: none computes or verifies any check value; python-stdnum's only optional check is the OUI *registry lookup*, which is membership, not a check digit). Like BIC, "structure is all there is" |
| **Related specs** | IEEE Std 802c-2017 (Structured Local Address Plan amendment for locally administered addresses); IEEE Std 802d-2017 (URN allocation); RFC 7042 (IETF usage of IEEE 802 parameters, BCP 141); RFC 2469 (canonical ordering caution); RFC 4291/RFC 4862 (IPv6 Modified EUI-64 IIDs); Bluetooth Core Specification Part B §1.2 (BD_ADDR = EUI-48 per IEEE 802-2014 §8.2); IEEE EUI tutorial ("Guidelines for Use of Extended Unique Identifier (EUI), Organizationally Unique Identifier (OUI), and Company ID (CID)") |

**Structure (IEEE Std 802 §8.2 per 802-2014 numbering; RFC 7042 §2.1-2.2; IEEE RA FAQ):**

```
EUI-48 = OUI(24 bits, MA-L) | extension(24 bits, OUI holder)          = 6 octets
       | 28-bit prefix (MA-M) | 20 bits                                = 6 octets
       | 36-bit prefix (MA-S) | 12 bits                                = 6 octets
EUI-64 = OUI(24 bits, MA-L) | extension(40 bits)                      = 8 octets
       | 28-bit prefix (MA-M) | 36 bits                                = 8 octets
       | 36-bit prefix (MA-S) | 28 bits                                = 8 octets

First octet (canonical display order), RFC 7042 §2.1:
  bit 01 (0x01) - Group bit (I/G): 0 unicast / 1 multicast (group)
  bit 02 (0x02) - Local bit (U/L): 0 universally administered / 1 locally administered
  OUIs and prefixes are assigned with the Local bit zero and the Group bit unspecified.

EUI-48 -> EUI-64 (IEEE translation, deprecated for MAC-48): insert FF-FE
(EUI-48) or FF-FF (MAC-48) between OUI and extension (RFC 7042 §2.2.1 note;
Wikipedia note [a]).
EUI-48 -> Modified EUI-64 (IETF, RFC 4291 App A / RFC 7042 §2.2.1): insert
FF-FE AND invert the U/L bit (02-00-5E-aa-bb-cc-dd-ee example in RFC 7042;
PostgreSQL macaddr8_set7bit: 08:00:2b:01:02:03 -> 0a:00:2b:ff:fe:01:02:03).
```

- Formal charset per mention: 12 or 16 hex digits `[0-9A-F]` (case-insensitive in every ecosystem validator), one consistent separator (`:` | `-` | `.` | none) per IEEE-802-external display convention; IEEE's own human-friendly display is hyphenated groups of two (EUI tutorial via Wikipedia; RFC 7042 §1.1 uses hyphens throughout).
- The I/G and U/L bits are *informative*: group addresses (multicast/broadcast) and locally administered addresses (including all IEEE 802c SLAP quadrants `XA`=ELI, `XE`=SAI, `X2`=AAI, `X6`=reserved; Wi-Fi randomization; Bluetooth random static) are valid MAC addresses. No ecosystem validator rejects on either bit.
- Documentation ranges (RFC 7042 §2.1.2/2.2.3, assigned under the IANA OUI `00-00-5E`): unicast `00-00-5E-00-53-00`-`FF` and multicast `01-00-5E-90-10-00`-`FF` (EUI-48); `00-00-5E-EF-10-00-00-00`-`FF` and `00-00-5E-FF-FE-00-53-00`-`FF` (EUI-64) - the MAC analogue of RFC 5737 addresses, ideal for Paxman test vectors.

**Lineage table (IEEE Std 802 Overview and Architecture editions):**

| Edition | Date | Status | Note |
|---------|------|--------|------|
| IEEE Std 802-1990 | 1990 | superseded by 802-2001 | First standalone Overview and Architecture (per catalogue lineage) |
| IEEE Std 802-2001 | 2002 (approved 2001) | superseded by 802-2014 | §9.2 "48-bit universal LAN MAC addresses" (cited by Bluetooth Core 1.2/4.0); PostgreSQL quotes its hyphen-canonical/colon-MSB display convention |
| IEEE Std 802-2014 | 2014-06-30 | superseded by 802-2024 | §8.2 "Universal addresses" - the clause the Bluetooth Core Specification cites normatively for BD_ADDR; amendments 802a-2003 (Ethertypes), 802b-2004 (OID), 802c-2017 (SLAP), 802d-2017 (URN), 802e, 802f-2023 (YANG EtherTypes) attach to this base |
| IEEE Std 802-2024 | 2024 | **current** | Consolidation revision (P802-REVc program rolls up 802c/802d/802e/802f); abstract: "specifies the structure of IEEE 802 MAC addresses" |

**Citation Details Table (for `Provenance`):**

| `authority` | `spec_name` | `version` | `reference_url` | `lifecycle` | `publication_year` | `kind` |
|-------------|-------------|-----------|-----------------|-------------|---------------------|--------|
| IEEE | `IEEE Std 802-2024` | `2024` (current) | 802-2024 catalogue page (resolve via standards.ieee.org search at implementation; the fetched 802-2014 page's "Revised By: IEEE 802-2024" record is the fetched evidence) | `active` | `2024` | `specification` |
| IEEE | `IEEE Std 802-2014` | `2014` | `https://standards.ieee.org/standard/802-2014.html` | `superseded` (by 802-2024) | `2014` | `specification` |
| IEEE | `IEEE Std 802-2001` | `2001` | (catalogue record cited via 802-2014 page lineage + PostgreSQL quote) | `superseded` | `2001` | `specification` |
| IEEE | `IEEE Std 802c-2017` (SLAP amendment) | `2017` | `https://standards.ieee.org/ieee/802c/6890` | `active` (amendment; folded into 802-2024 program) | `2017` | `specification` |
| IEEE RA | `IEEE Registration Authority MA-L/MA-M/MA-S public listing` | `Rolling` | `https://regauth.standards.ieee.org/` (+ `https://standards.ieee.org/products-programs/regauth/mac/`) | `active` - rolling | `2026` | `registry` |
| IEEE | `Guidelines for Use of EUI, OUI, and CID` (tutorial) | (undated tutorial) | `https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf` | `active` | - | `specification` |
| IETF | `RFC 7042` (BCP 141) | `2013-10` | `https://www.rfc-editor.org/rfc/rfc7042.txt` | `active` | `2013` | `specification` |
| IETF | `RFC 2469` | `1998-12` | `https://www.rfc-editor.org/rfc/rfc2469.txt` | `active` (informational) | `1998` | `specification` |

*Lifecycle note (per ARCHITECTURE.md Provenance vocabulary):* the shipped structure rule cites the current edition (`lifecycle="active"`); a historical rule pinned via `year` temporal filtering to 802-2014 or 802-2001 would carry `lifecycle="superseded"`. The OUI registry rule is `kind="registry"` `lifecycle="active"` (rolling).

### 5.2 Rule / publication map (one file per publication - HOW_TO_ADD_NEW_CAPABILITY.md §5)

| Rule file | Module-level `PUBLICATION` (Provenance) | Rules in file | What it validates |
|-----------|------------------------------------------|----------------|-------------------|
| `rules/ieee_802_ed2024.py` | `authority="IEEE"`, `specification_name="IEEE Std 802-2024"`, `kind="specification"`, `reference_url=<802-2024 catalogue page>`, `version="2024"`, `lifecycle="active"`, `publication_year=2024` | `Section 8.2-eui-structure` | Generic structure: 12 or 16 hex (EUI-48/EUI-64), consistent separator already grammar-guaranteed, I/G and U/L bits informative (never rejected), EUI-64-FF-FE and modified forms are ordinary EUI-64s; `normalize()` returns colon-separated uppercase octets |
| `rules/ieee_oui_registry_ed2026.py` *(optional - gated)* | `authority="IEEE Registration Authority"`, `specification_name="IEEE MA-L/MA-M/MA-S public listing"`, `kind="registry"`, `reference_url="https://regauth.standards.ieee.org/"`, `version="Rolling"`, `lifecycle="active"`, `publication_year=2026` | `Section-oui-registry-membership` | For universally administered addresses (U/L bit 0): the first 24 bits (MA-L OUI) or prefix (MA-M 28-bit / MA-S 36-bit projection) exist in the IEEE block-assignment snapshot; locally administered addresses (U/L bit 1) return valid without lookup (python-stdnum `validate_manufacturer` semantics); `requires_features={"include_oui_validation"}` |

*This mirrors the ISBN three-authority split (ISO 2108 // Users Manual // Range Message) and the BIC split (ISO 9362 // ISO 3166 country lookup // SWIFT Directory gated). For MAC, only the IEEE 802 structure rule is mandatory; the OUI registry layer is optional and gated exactly like ISBN `Section 4-registrant-range` (`include_range_validation`) and IBAN `swift_iban_registry` (`include_registry_validation`). IEEE 802c-2017 (SLAP) and RFC 7042/RFC 2469 are evidence publications, not rule files: SLAP quadrants are all-valid local addresses (nothing to gate), and the RFCs are usage/display conventions.*

Each `Rule[MacAddressNotation]` subclass declares the six enforced metadata attributes at class-definition time (`Rule.__init_subclass__`, `paxman/core/domain.py:246-271`, verified - missing attribute or non-frozenset `target_semantics`/`requires_features` fails at import):

```python
class Section82EUIStructure(Rule[MacAddressNotation]):
    name = "Section 8.2-eui-structure"
    strategy = RuleStrategy.PARSER
    provenance = PUBLICATION
    citation = "Section 8.2 (Universal addresses; EUI-48/EUI-64, I/G and U/L bits)"
    target_semantics = frozenset({"mac_address_recognition"})
    requires_features = frozenset()

    def matches(self, notation: MacAddressNotation, contract: Contract) -> bool: ...
    def normalize(self, notation: MacAddressNotation, contract: Contract) -> str: ...
```

### 5.3 What each rule does vs does not own

- **`matches()`** - validates strictly, never raises. The IEEE 802 structure rule checks: `len(compact)` in `{12, 16}`, charset `[0-9A-F]` (grammar-guaranteed but re-asserted), `shape` agrees with length. It explicitly does **not** reject on I/G bit (multicast/broadcast are valid), U/L bit (locally administered are valid), the `FF-FE` / `FF-FF` mid-address markers, or the all-zeros / all-ones sentinels. The OUI registry rule checks: U/L bit 0 → `compact[:6]` (MA-L OUI key) present in the snapshot (with MA-M/MA-S prefix handling if the snapshot model includes them); U/L bit 1 → valid without lookup (802c SLAP local space is outside the universal registries by definition). Both return `False` for any invalid input; contract misconfigurations are caught in `contract.__post_init__`, never in rule methods (HOW_TO_ADD_NEW_CAPABILITY.md Step 7).
- **`normalize()`** - returns the **default canonical form** (colon-separated uppercase octets: `":".join(compact[i:i+2] for i in range(0, len(compact), 2))`). The CI source-scan `tests/unit/test_rule_output_format_purity.py` rejects any `output_format` token in `paxman/capabilities/*/rules/` modules (code, comments, or docstrings); presentation is the capability `format_value()` seam only. Both rules must return the **same** default string for the same valid notation - candidate dedup `(value, recognition_rule, validation_rule)` keeps agreement as `SUCCESS` (BIC precedent: country rule and structure rule agree).
- **`RuleStrategy` choice:** the structure rule is `PARSER` (structure validation over the normalized hex string - same class as ISBN's mod-11 `PARSER` and IP's `rfc_791_ed1981` octet-range `PARSER`); the OUI registry rule is `LOOKUP_TABLE` (set membership over a snapshot - same class as BIC country lookup and ISBN registrant ranges).

### 5.4 Scope decision (the capability's analogue of IBAN §5.4 / BIC §5.4)

Whether OUI-registry validation is always-active vs gated mirrors the stdnum divergence: python-stdnum checks the manufacturer **by default** for universally administered addresses (`validate_manufacturer` defaults to checking when U/L=0), because its `numdb` ships the IEEE OUI database. Paxman's determinism guarantee is scoped to a fixed library snapshot, and an embedded OUI snapshot (3500+ MA-L blocks and growing monthly) is staleness-prone in exactly the way the ISBN Range Message and SWIFT BIC Directory are.

**Recommendation:** ship the OUI registry rule **gated behind `include_oui_validation=False`** (ISBN/IBAN/BIC precedent for registry layers), keeping v1 `SUCCESS` semantics purely structural. Locally administered addresses (U/L=1) are never registry-checked regardless of the flag - they are outside the universal registries by construction (IEEE RA FAQ: OUIs are assigned with the Local bit zero; 802c SLAP governs local space). This diverges from stdnum's default-on behavior deliberately; §13 decision 6 records it.

Analogy: BIC's country lookup is cheap set membership and ships always-active; an OUI lookup is *equally cheap* but *semantically weaker* (a valid universal MAC whose vendor left the listing, a private registration, or a snapshot-lag gap would false-`INVALID`), so gating is the correct default.

### 5.5 Assignment / registration authority & Registry content

Network: **IEEE Registration Authority** assigns identifier blocks to organizations; the **organizations** (OUI/prefix holders) assign individual addresses. Block sizes (IEEE RA FAQ + MAC products page, fetched):

| Block | Previously named | Addresses | 48-bit | 64-bit |
|-------|------------------|-----------|--------|--------|
| MA-L (MAC Address Block Large) | OUI | 2^24 (~16 million) | yes | yes |
| MA-M (MAC Address Block Medium) | - | 2^20 (~1 million) | yes | yes |
| MA-S (MAC Address Block Small) | OUI-36 (encompasses IAB) | 2^12 (4,096) | yes | yes |

- MA-L includes an OUI; MA-M and MA-S do not (MA-M's first 24 bits are an IEEE-held OUI not reassigned; MA-S carries a 36-bit unique number). The IAB registry is **inactive since 2014-01-01** (00:50:C2 used 2007-2012; 40:D8:55 after September 2012; existing IAB owners may continue).
- **CID** (Company ID) is a 24-bit identifier that **cannot** be used to generate universally unique MAC addresses (IEEE RA FAQ) - but *is* used inside 802c SLAP quadrants for ELI local addresses (Wikipedia §802c row).
- Public listing: `https://regauth.standards.ieee.org/` (searchable per registry); assignments processed within 7 US business days after payment; confidential registrations listed as "PRIVATE" for an annual fee; 95% utilization required before an additional block.
- The registry layer snapshot (`rules/data/oui_registry.py`, §11) records block keys (24-bit OUI for MA-L; 28-bit/36-bit prefixes for MA-M/MA-S projected onto their 12/16-hex compact prefixes) - the lookup rule tests `compact[:6]` for MA-L and would test the applicable prefix width if MA-M/MA-S rows are modeled; v1 ships the MA-L OUI set only, with the snapshot format documented for extension.

---

## 6. Presentation Seam - Contract & Capability

### 6.1 Contract (HOW_TO_ADD_NEW_CAPABILITY.md §7)

Every contract **MUST inherit `CapabilityContract`** (`paxman.core.contract`), never `Contract` directly (ADR-0007). The contract is `@dataclass(frozen=True)` **without** `slots=True` (incompatible with the base `super().__post_init__` pattern).

```python
from dataclasses import dataclass, field
from typing import ClassVar

from paxman.core.contract import CapabilityContract


@dataclass(frozen=True)
class MacAddressContract(CapabilityContract):
    """User-facing contract for the MacAddress capability."""

    DEFAULT_OUTPUT_FORMAT: ClassVar[str] = "colon"
    OFFERED_OUTPUT_FORMATS: ClassVar[frozenset[str]] = frozenset(
        {"hyphen", "bare", "cisco", "eui64", "bit_reversed"}
    )

    capability_name: str = field(default="mac_address", init=False)
    # Grammar-toggle flags: none for the initial single-grammar design.
    # If the OUI registry rule ships (§5.2):
    # include_oui_validation: bool = False
    # If bare-hex recognition is ever gated (Open Decision 4):
    # include_bare: bool = True

    # active_grammars is omitted: the base returns None and the engine runs
    # every shipped grammar in get_grammars() order (single always-active
    # grammar).
```

- `DEFAULT_OUTPUT_FORMAT` is a concrete string (never `None`); `OFFERED_OUTPUT_FORMATS` alternatives exclude the default. The inherited `output_format: str | None = None` is resolved by `CapabilityContract.__post_init__` via `resolve_output_format` (verified `paxman/core/contract.py:62-123`): `None`, `"default"`, and `"colon"` are treated identically (identity rendering); only an explicit offered alternative triggers `format_value()` conversion; anything else raises `ContractError`.
- `create_contract()` opens with the fixed keyword-only common block (`excluded_rules`, `pinned_rules`, `year`, `output_format`, `extra_grammars`) in that order; capability-specific params (`include_oui_validation` when the registry rule ships) follow.
- **Presentational-only invariant (hard rule):** `output_format` is a representation transform, never a recognition or validation signal. Rules never read it; `normalize()` always returns the default colon form; the engine calls `Capability.format_value(value, output_format, notation)` immediately after `normalize()` and before candidate dedup and status determination. `AMBIGUOUS` semantics are preserved across formats; formatting adds no provenance.

For MAC, the offered formats model the interchange forms identified in §2:

| `output_format` | `value` example (from canonical `00:1A:2B:3C:4D:5E`) | Meaning |
|-----------------|-------------------------------------------------------|---------|
| `"colon"` (default) | `00:1A:2B:3C:4D:5E` | Uppercase colon octets - dominant interchange form (Unix, PostgreSQL output, Bluetooth, Zigbee/Thread, Rust, stdnum); DB-joinable and unambiguous |
| `"hyphen"` | `00-1A-2B-3C-4D-5E` | IEEE 802 human-friendly display (RFC 7042 notation, Windows tooling, `to_eui48`) |
| `"bare"` | `001A2B3C4D5E` | Compact DB-key form (netaddr `mac_bare`, validator.js no-separators) |
| `"cisco"` | `001A.2B3C.4D5E` | Cisco IOS tri-dot hextets (netaddr `mac_cisco`) |
| `"eui64"` | `00:1A:2B:FF:FE:3C:4D:5E` (from EUI-48; EUI-64 input passes through) | IEEE EUI-48 → EUI-64 `FF-FE` expansion, PostgreSQL `macaddr8` semantics; deterministic and reversible for EUI-48 input |
| `"bit_reversed"` | `48:2C:6A:1E:59:3D` | Per-octet bit-swap of the canonical value (RFC 2469 vector; Token Ring/FDDI display); deterministic both directions |

*Not offered:* `modified_eui64` (the IPv6 IID U/L-flip transform, `macaddr8_set7bit`) - it is an IPv6-domain semantic (RFC 4291/4862, and RFC 8064 now discourages EUI-64-derived stable IIDs), it is only meaningful from EUI-48 input, and flipping the U/L bit is a semantic transform rather than a display re-insertion; a community extension or the caller owns it (§13 decision 7). No label format - the `MAC:` label is not part of the identifier.

### 6.2 Capability (HOW_TO_ADD_NEW_CAPABILITY.md §6)

```python
from collections.abc import Sequence

from paxman.core.capability import Capability
from paxman.core.domain import Grammar, Rule
from paxman.capabilities.MacAddress.notation import MacAddressNotation


def _bit_reverse_octet(octet: str) -> str:
    """RFC 2469 per-octet bit swap: 0x12 -> 0x48, 0xBC -> 0x3D."""
    value = int(octet, 16)
    reversed_bits = (
        ((value & 0x01) << 7)
        | ((value & 0x02) << 5)
        | ((value & 0x04) << 3)
        | ((value & 0x08) << 1)
        | ((value & 0x10) >> 1)
        | ((value & 0x20) >> 3)
        | ((value & 0x40) >> 5)
        | ((value & 0x80) >> 7)
    )
    return f"{reversed_bits:02X}"


class MacAddressCapability(Capability[MacAddressNotation]):
    name = "mac_address"  # lowercase identifier - what users pass to the registry

    def get_grammars(self) -> list[Grammar[MacAddressNotation]]:
        return [MacAddressRecognitionGrammar()]  # single grammar; both lengths

    def get_rules(self) -> list[Rule[MacAddressNotation]]:
        return [
            Section82EUIStructure(),
            SectionOUIRegistryMembership(),  # gated: include_oui_validation
        ]

    @staticmethod
    def create_contract(
        *,
        excluded_rules: Sequence[str] | None = None,
        pinned_rules: Sequence[str] | None = None,
        year: int | None = None,
        output_format: str | None = None,
        extra_grammars: Sequence[str] | None = None,
    ) -> MacAddressContract:
        return MacAddressContract(
            excluded_rules=excluded_rules or [],
            pinned_rules=pinned_rules,
            year=year,
            output_format=output_format,
            extra_grammars=extra_grammars,
        )

    def format_value(
        self, value: str, output_format: str | None, notation: MacAddressNotation
    ) -> str:
        compact = value.replace(":", "")
        octets = [compact[i : i + 2] for i in range(0, len(compact), 2)]
        if output_format == "hyphen":
            return "-".join(octets)
        if output_format == "bare":
            return compact
        if output_format == "cisco":
            hextets = [compact[i : i + 4] for i in range(0, len(compact), 4)]
            return ".".join(hextets)
        if output_format == "eui64":
            if len(compact) == 12:
                return ":".join([*octets[:3], "FF", "FE", *octets[3:]])
            return value  # already EUI-64 - deterministic identity
        if output_format == "bit_reversed":
            return ":".join(_bit_reverse_octet(o) for o in octets)
        return value  # colon default is identity - normalize() returns colon form
```

Registration (HOW_TO_ADD_NEW_CAPABILITY.md §9 / `tools/new_capability.py`): the scaffolder adds the import line and `__all__` entry to `paxman/capabilities/__init__.py` (alphabetical); users call `paxman.register_capability(MacAddress())` or `paxman.register_all_shipped()` once before the first `canonicalize()`.

---

## 7. Validation - Structure, Registry

### 7.1 Level 1 generic structure, Level 2 OUI registry (gated)

**Level 1 - Generic structure (`PARSER`, always active):**
- `len(compact)` in `{12, 16}` hex digits exactly; never 11, 13, 14, 15 (grammar quantifiers enforce; the rule re-asserts).
- Charset `[0-9A-F]` uppercase after grammar normalization; `shape` field agrees with length (`"eui48"` ⇔ 12, `"eui64"` ⇔ 16).
- **No bit gating:** every value of the first octet is a valid MAC. The I/G bit (0x01) distinguishes unicast/group; the U/L bit (0x02) distinguishes universal/local - both are *predicates* exposed by python-stdnum (`is_multicast`, `is_locally_administered`), Rust `macaddr` (`is_unicast`, `is_local`, `is_broadcast`, `is_nil`), and netaddr; none rejects. `FF:FF:FF:FF:FF:FF` (broadcast), `00:00:00:00:00:00` (nil), `01:80:C2:00:00:00` (STP), and the `33-33` IPv6 ND multicast range (RFC 7042 §2.3.1) are all `SUCCESS`.
- **No check digit:** proved by absence across IEEE 802 structure, RFC 7042, and all validators (§5.1) - unlike IBAN MOD 97-10, ISBN mod-11, ISSN mod-11, ISIN Luhn, ORCID mod-11, EAN.
- **Display conventions are not validity:** the IEEE 802-2001 hyphen-canonical / colon-MSB-display convention (PostgreSQL quote, §2.2 row 8) is "widely ignored nowadays" and MUST NOT gate on separator choice - colon and hyphen inputs are equally valid, and neither is reinterpreted (§13 decision 10).

**Level 2 - OUI registry membership (`LOOKUP_TABLE`, gated `include_oui_validation=False`):**
- For U/L=0 (universally administered): `compact[:6]` present in the MA-L OUI snapshot (MA-M/MA-S prefix projection documented for extension, §5.5).
- For U/L=1 (locally administered): valid without lookup - IEEE assigns OUIs with the Local bit zero (RFC 7042 §2.1), so local space is definitionally outside the registries; 802c SLAP (ELI `XA`, SAI `XE`, AAI `X2`, reserved `X6`) governs it.
- python-stdnum precedent: `validate()` checks `get_manufacturer` when `validate_manufacturer or is_universally_administered(number)` - i.e. universal addresses are registry-checked, local ones are not.
- Determinism-by-snapshot: the embedded OUI set is point-in-time; snapshot staleness yields `INVALID` for a legitimately new OUI under an old snapshot - documented in `Provenance.version` (`"Rolling"`), never an ambiguity (§14).

**What makes a MAC "valid" vs "OUI-valid" vs "issued":**
- **valid (generic)** - correct length/charset/shape per IEEE 802; the always-active `PARSER` rule; every syntactically well-formed 12/16-hex value passes.
- **OUI-valid** - generic-valid plus (for universal addresses) the first block exists in an IEEE block-assignment snapshot; the gated `LOOKUP_TABLE` rule. Without it, `DE:AD:BE:EF:00:01` is a valid MAC even though `DE:AD:BE` is not a known MA-L OUI.
- **issued/assigned** - actually allocated by the OUI holder to a product; unknowable from any public snapshot (the IEEE listing records block holders, not individual addresses); permanently out of scope, like IBAN account existence and ISSN Register liveness.

### 7.2 Stdnum divergence note

python-stdnum validates manufacturer by default (universal addresses) because its snapshot ships in-distribution; Paxman gates it (§5.4). A Paxman caller wanting stdnum parity sets `include_oui_validation=True` and accepts snapshot-staleness semantics. This is the IBAN/SWIFT-Registry split restated for MAC and is recorded as Open Decision 6.

---

## 8. Edge Cases

| # | Edge case | Expected resolution | Why |
|---|-----------|---------------------|-----|
| 1 | Lowercase / mixed case: `00:1a:2b:3c:4d:5e`, `De:Ad:Be:Ef:Ca:Fe` | `SUCCESS` → `00:1A:2B:3C:4D:5E` | Grammar `(?ai:)` folds case, `notation_fn` `.upper()`; canonical uppercase (Paxman convention; stdnum/PG lowercase divergence documented §13 decision 2) |
| 2 | Separator family equivalence: `00:1A:2B:3C:4D:5E` vs `00-1A-2B-3C-4D-5E` vs `001A.2B3C.4D5E` vs `001A2B3C4D5E` | All `SUCCESS` → same compact → same canonical (candidate dedup by value) | Separators are presentation-only; every ecosystem validator strips before checking; PG normalizes 7 spellings to one output |
| 3 | EUI-64 input: `00:1A:2B:3C:4D:5E:66:77` | `SUCCESS` → 16-hex colon canonical, `shape="eui64"` | 64-bit branch; embedded EUI-48 sub-run suppressed by branch ordering + within-grammar longer-wins dedup |
| 4 | `eui64` format from EUI-48: `00:1A:2B:3C:4D:5E` → `00:1A:2B:FF:FE:3C:4D:5E` | `SUCCESS`, deterministic expansion | IEEE `FF-FE` insertion (RFC 7042 §2.2.1 note; PostgreSQL `macaddr8` 6→8 behavior); reversible for EUI-48 input; EUI-64 input passes through unchanged |
| 5 | Bit-reversed input: `48-2C-6A-1E-59-3D` (canonical `12-34-56-78-9A-BC` swapped) | `SUCCESS` → resolves to itself; `bit_reversed` format renders `12:34:56:78:9A:BC` | Syntactically indistinguishable from canonical (RFC 2469); determinism forbids world-knowledge reinterpretation; identity is the literal string (§13 decision 10) |
| 6 | Broadcast / nil / sentinel: `FF:FF:FF:FF:FF:FF`, `00:00:00:00:00:00`, `01:80:C2:00:00:00` | `SUCCESS` each | All first-octet values valid; I/G and U/L bits are predicates, never gates (stdnum/macaddr/netaddr expose, none reject) |
| 7 | Locally administered / SLAP / randomization: `02:00:00:00:00:01`, `A4:C1:38:0C:AC:70:4C:37`-class U/L-set addresses | `SUCCESS`; never registry-checked when `include_oui_validation=True` | U/L bit 1 → outside universal registries by construction (RFC 7042 §2.1; 802c SLAP; Wi-Fi/Bluetooth randomization practice) |
| 8 | `MAC` label: `MAC: 00:1A:2B:3C:4D:5E`, `mac - 001a.2b3c.4d5e` | `SUCCESS`; span includes label, `raw_text` = `MAC: 00:1A:2B:3C:4D:5E`; `compact` label-free | Fused `(?ai:MAC)[\s:-]+` label (BIC/ISSN/IBAN precedent); `[\s:-]+` never zero-width |
| 9 | Glued label: `MAC001A2B3C4D5E` | `MISSING` | Label branch requires separator; body cannot start at `M` (not hex) or carve after it (`(?<!\w)` sees `\w`) - documented asymmetry vs BIC's lookahead (§4.2) |
| 10 | Mixed separators: `00:1A-2B:3C-4D:5E`, `001A.2B3C:4D5E` | `MISSING` | Per-separator branches are internally uniform - no validator accepts mixed (validator.js `\1`, Go single-separator dispatch, PG "consistently") |
| 11 | Over/under-long: 11 hex, 13 hex, 14 hex, 7 octets colon, 5 octets | `MISSING` (no branch claims) | Quantifiers enforce exactly 12/16 hex and 6/8 octets; `word_only` prevents carving 12-hex out of 13-hex runs |
| 12 | Bare/hex residue after a 48-bit claim: `001A2B3C4D5E:6677` (4-hex residue), `001A2B3C4D5E-66` (2-hex terminating residue), `001A2B3C4D5E-3` (1-hex suffix) | `001A2B3C4D5E:6677` and `001A2B3C4D5E-3` → `SUCCESS` claiming the bare 12-hex span (residue unclaimed); `001A2B3C4D5E-66` → `MISSING` (truncation guard: separator + exactly 2 terminating hex = truncated final octet of a longer run) | Truncation guard (§4.2) blocks the truncated-octet signature on 48-bit claims; longer or shorter residues are junk the complete valid form may carry; PostgreSQL 6+8/8+8 word-split forms stay `MISSING` (no contiguous 12/16-hex run - DEFER §2.1 row 11) |
| 13 | IPv6-shaped 8x2-digit colon: `0a:00:2b:ff:fe:01:02:03` (a modified EUI-64 / also a full IPv6 textual address) | `SUCCESS` as EUI-64 | Lexically a valid EUI-64; cross-capability IPv6 collision is caller-owned (§14); exactly-2-digit octet floor is the agreed mitigation |
| 14 | OCR / homoglyphs: `00:1A:2B:3C:4D:0G`, `００:1A:2B:3C:4D:5E` (fullwidth), letter `O` for `0` | `MISSING` | Strict `(?ai:)` ASCII hex; no autocorrection (ISBN/ISSN precedent) |
| 15 | Quoted / bracketed / embedded: `"00:1A:2B:3C:4D:5E"`, `[001A.2B3C.4D5E]`, `eth0 ether 00:1b:77:49:54:fd` | `SUCCESS` with span inside punctuation | Punctuation is non-word; `word_only` guards hold; `ether` tool label DEFERred but body recognized (§2.1 row 15) |
| 16 | Two distinct MACs in one slice: `from 00:1A:2B:3C:4D:5E to 00-1B-77-49-54-FD` | `AMBIGUOUS` / `MultipleMentionsError` (`single_value=True`) | Distinct canonical values; segmentation recipe is the intended path; identical mentions coalesce to `SUCCESS` |
| 17 | U/L=0 with unknown OUI: `DE:AD:BE:EF:CA:FE` (`DE:AD:BE` not a real MA-L OUI) | Without registry rule: `SUCCESS` (valid MAC). With `include_oui_validation=True`: `INVALID` | Registry membership is the gated validity layer; `DE:AD:BE` is lexically valid but not IEEE-assigned (stdnum `validate_manufacturer` analogue) |
| 18 | `year` temporal pin: `create_contract(year=2014)` | Structure rule from 802-2024 dropped (publication_year 2024 > 2014); with only the gated registry rule (year 2026) also dropped → `INVALID` for any recognized input | Temporal filtering per ARCHITECTURE.md: rules with publication_year > contract.year are excluded; document that v1 has no pre-2024-active structure rule (or ship `ieee_802_ed2014.py` if historical pinning support is wanted - Open Decision 9) |

---

## 9. Resolution-State Map (ARCHITECTURE.md Resolution Semantics)

| Input | Status | Why |
|-------|--------|-----|
| Valid EUI-48 in any attested spelling (`00:1A:2B:3C:4D:5E`, `00-1A-2B-3C-4D-5E`, `001A.2B3C.4D5E`, `001A2B3C4D5E`, lowercase, `MAC:`-labelled, documentation range `00:00:5E:00:53:01`) | `SUCCESS` → `00:1A:2B:3C:4D:5E` (`colon` default) | Single canonical via IEEE 802 structure rule; separators/label/case are presentation-only; candidate dedup collapses spellings |
| Valid EUI-64 (`00:1A:2B:3C:4D:5E:66:77`, all four separator families) | `SUCCESS` → 16-hex colon canonical, `shape="eui64"` | 64-bit branch; embedded EUI-48 sub-run suppressed (single grammar + longer-wins) |
| Bit-reversed spelling (`48-2C-6A-1E-59-3D`) | `SUCCESS` → itself; `bit_reversed` format renders the canonical swap | Recognize-as-is policy; no world-knowledge reinterpretation (determinism) |
| 7-octet / 11-hex / 13-hex / mixed-separator / non-hex input | `MISSING` | No grammar branch claims; structural failure at recognition, not validation |
| Recognized but unknown universal OUI (`DE:AD:BE:EF:CA:FE`) with `include_oui_validation=True` | `INVALID` | Registry rule rejects (recognized, no authority validates); without the flag → `SUCCESS` (§5.4 divergence from stdnum default) |
| Locally administered address with `include_oui_validation=True` | `SUCCESS` | U/L bit 1 → registry rule skips lookup by construction (RFC 7042 / 802c) |
| No 12/16-hex runs in text | `MISSING` | No grammar recognized anything |
| Two distinct valid MACs in one slice (`from AA to BB`) | `AMBIGUOUS` or `MultipleMentionsError` with `single_value=True` | Single-slice ambiguity; caller-owned segmentation |
| `year=2014` pin | rules dropped per temporal filter → `INVALID` for any recognized input | No active rule with publication_year ≤ 2014 ships in v1 (Open Decision 9) |

---

## 10. Scaffolding & Repo Integration

### 10.1 Generated skeleton (`tools/new_capability.py` - HOW_TO_ADD_NEW_CAPABILITY.md Step 0)

```bash
uv run python tools/new_capability.py MacAddress --name mac_address \
    --authority "IEEE" --spec-name "IEEE Std 802-2024" \
    --spec-url "https://standards.ieee.org/standard/802-2014.html" \
    --publication-year 2024
```

Creates 13 files plus one edit (Step 0 checklist): `paxman/capabilities/MacAddress/{notation,contract,capability}.py`, `grammar/mac_address_recognition.py`, `rules/ieee_802_ed2024.py`, package inits, four test stubs (`tests/capabilities/mac_address/`), and the alphabetical `paxman/capabilities/__init__.py` wiring. The `TODO(scaffold)` markers then guide: replacing the placeholder grammar pattern with the §4.2 pattern, renaming `Section 1-overview` to `Section 8.2-eui-structure`, shaping the notation from placeholder `value` into `compact` + `shape`, and adding `rules/data/` only if the OUI registry layer is adopted.

> Note: the scaffolder's single `--spec-name`/`--spec-url` covers one provenance. After scaffolding, add `rules/ieee_oui_registry_ed2026.py` (with `rules/data/oui_registry.py`) manually. The `--spec-url` above uses the fetched 802-2014 catalogue page as the verifiable URL; resolve the 802-2024 catalogue page at implementation and update `PUBLICATION` (§5.1 Citation Details Table notes this explicitly - no URL was invented).

### 10.2 Contract and grammar wiring

- `get_grammars()` returns `[MacAddressRecognitionGrammar()]` - one grammar owns both lengths (§4.2).
- `active_grammars` omitted (base `None` → engine runs every shipped grammar). Only introduce if recognition becomes feature-gated (e.g. an `include_bare` gate per Open Decision 4) - the Email/IP/ISBN pattern.
- Grammar carries `name = "mac_address_recognition"` (snake_case `_recognition` suffix) and non-empty `semantics` - engine composes shipped plus `extra_grammars` community extensions in order, failing fast on name collisions (`CapabilityError`) or dangling `target_semantics` (`ContractError`).

### 10.3 Cross-cutting invariants (fail review if violated)

- **No `# type: ignore` / `# noqa` / `# pyright: ignore` in `paxman/` source** - fix root cause or scoped `per-file-ignores` (sanctioned pattern in pyproject).
- **No cross-capability imports** - import only from `paxman.core` (import-linter enforced). MacAddress must not import IP's IPv6 tables or ISBN digit helpers.
- **No `output_format` token in any `paxman/capabilities/*/rules/` module** (code, comments, docstrings) - source-scan `tests/unit/test_rule_output_format_purity.py`. Presentation is `Capability.format_value()` only.
- `@dataclass(frozen=True, slots=True)` notation; `@dataclass(frozen=True)` **without** slots contract.
- Deterministic by construction: same input + contract + library snapshot (version, registry, rule-data tables) → same canonical output; no network, clock, or environment-dependent ordering; **no bit-order world-knowledge** anywhere in the pipeline.

---

## 11. Recommended File Layout (mirrors ISSN/IBAN/BIC)

```
paxman/capabilities/MacAddress/
├── __init__.py
├── capability.py
├── contract.py
├── notation.py
├── grammar/
│   ├── __init__.py
│   └── mac_address_recognition.py        # single grammar, 8 shape branches
└── rules/
    ├── __init__.py
    ├── ieee_802_ed2024.py                # primary - generic structure (PARSER)
    ├── ieee_oui_registry_ed2026.py       # OUI membership (LOOKUP_TABLE, gated)
    └── data/                             # only if the registry layer is adopted
        └── oui_registry.py               # IEEE MA-L OUI snapshot (frozenset)
```

Per-registry data module shape (parallel to `paxman/capabilities/ISBN/rules/data/range_message.py`):

```python
# rules/data/oui_registry.py - IEEE MA-L (OUI) block-assignment snapshot
# Source: https://regauth.standards.ieee.org/  (public listing, rolling)
# Point-in-time snapshot; regenerate via tools/regenerate_oui_registry_data.py
# if automated from the IEEE public listing download. Keys are 6-hex-digit
# uppercase MA-L OUIs (first 24 bits, Local bit zero by assignment policy).
# Uppercase-keyed to match MacAddressNotation.compact slicing.

OUI_REGISTRY: frozenset[str] = frozenset(
    {
        "00005E",  # IANA (RFC 7042 §1.4)
        "001B77",  # example block holders...
        # ... full MA-L listing (~3500+ blocks, monthly churn)
    }
)
# Extension model (documented, not shipped v1): MA-M 28-bit and MA-S 36-bit
# prefixes projected onto 7/9-hex-digit compact prefixes would require a
# second table and width-aware lookup in SectionOUIRegistryMembership.
```

---

## 12. Test Strategy (mirrors HOW_TO_ADD_NEW_CAPABILITY.md and ISSN §9)

- **Grammar tests** (`tests/capabilities/mac_address/test_grammar.py`, `pytestmark = [pytest.mark.capability]`): one positive vector per §2.1 RECOGNIZE form (colon 48, hyphen 48, tri-dot 48, bare 48, colon/hyphen/dot/bare 64, `MAC:` label, case variants); multiple matches in one text; incompatible formats (7-octet, 11/13/14/15-hex, mixed separators, 1-digit octets, 24-bit-word form, `::`-compressed IPv6, UUID, quoted prose without a valid run); empty input; span invariants `len(raw_text) == end - start` and `raw_text == text[start:end]`; `name`/`semantics` checks; boundary negatives (`X001A2B3C4D5E`, `001A2B3C4D5EY`, glued `MAC001A2B3C4D5E`); embedded-prefix resolution (EUI-48 sub-run inside EUI-64 yields exactly one 16-hex match); bare 16-before-12 ordering (`001A2B3C4D5E6677` claims 16).
- **Rule tests** (`test_rules.py`):
  - *Structure rule* (`ieee_802_ed2024`): `matches()` valid 12/16 vectors, invalid lengths (11/13/14/15), shape/length disagreement, never rejects broadcast/nil/multicast/local/FF-FE; `normalize()` exact colon output (`001A2B3C4D5E` → `00:1A:2B:3C:4D:5E`; 16-hex → 8 groups); provenance attributes (`authority="IEEE"`, `publication_year=2024`, `lifecycle="active"`, `kind="specification"`); name/strategy conventions (`strategy=PARSER`).
  - *Registry rule* (`ieee_oui_registry_ed2026`): valid snapshot OUI (`00:00:5E:...` from RFC 7042's IANA OUI) → valid; unknown universal OUI (`DE:AD:BE:...`) → invalid; locally administered (`02:...`, `0A:...`) → valid without lookup; `requires_features={"include_oui_validation"}` gate; `strategy=LOOKUP_TABLE`; `kind="registry"`; `normalize()` agreement with the structure rule (same colon string - dedup invariant).
- **Capability tests** (`test_capability.py`): notation frozen/hashable/slots (mutation raises `FrozenInstanceError`, stable `hash`, `__slots__` present, `shape`/length invariant); wiring counts (`get_grammars()` len 1, `get_rules()` len 2); grammar/rule name conventions; `format_value()` round-trips (`colon` identity, `hyphen`, `bare`, `cisco`, `eui64` expansion from 48 / identity from 64, `bit_reversed` RFC 2469 vector `12-34-56-78-9A-BC` ↔ `48-2C-6A-1E-59-3D` both directions); `create_contract` factories (default, each offered format, `extra_grammars`, invalid format → `ContractError`).
- **Integration** (`tests/integration/test_mac_address_capability.py`): `MISSING`/`INVALID`/`SUCCESS`/`AMBIGUOUS` (+`MultipleMentionsError` with `single_value=True`); registry gating (`include_oui_validation=True` flips unknown-OUI universal input to `INVALID`, local input stays `SUCCESS`); `year` pinning (`year=2014` → rules dropped → `INVALID`); `_clean_registry` autouse fixture; determinism + `VersionStamp`; span-bearing match and `Candidate.span`; spelling-variant dedup (colon/hyphen/tri-dot of one address → one candidate, `SUCCESS`); recognition-rule attribution (`recognition_rule == "mac_address_recognition"`).
- **Property tests (hypothesis):** generate valid EUI-48/EUI-64 (`integers(0, 2**48-1)` / `2**64-1` formatted to hex) → must canonicalize to their own colon form; random strings → `INVALID`/`MISSING` with high probability, **never raise**; spelling equivalence (same value in all four separator families → identical canonical); `bit_reversed` involution (`format_value(bit_reversed)` applied twice returns the canonical value); `eui64` expansion from a generated EUI-48 is deterministic and reversible by deleting `FF:FE`.
- **Consistency test (grammar/rule boundary):** every shipped `semantics` covered by at least one `Rule.target_semantics`; if the OUI snapshot ships, every `OUI_REGISTRY` key is 6 uppercase hex with Local bit 0 (`int(k[:2], 16) & 2 == 0`) - the IEEE assignment policy invariant.
- **Presentation purity:** the `output_format` source scan applies to `rules/ieee_802_ed2024.py` and `rules/ieee_oui_registry_ed2026.py` (no token in code/comments/docstrings).
- **Real vectors:** RFC 7042 documentation values (`00-00-5E-00-53-01` unicast, `01-00-5E-90-10-xx` multicast); RFC 2469 bit-swap vector (`12-34-56-78-9A-BC` / `48-2C-6A-1E-59-3D`); PostgreSQL vectors (`08-00-2b-01-02-03` = `10:00:D4:80:40:C0` bit-swapped; `macaddr8` `08:00:2b:ff:fe:01:02:03`; `macaddr8_set7bit` `0a:00:2b:ff:fe:01:02:03`); RFC 7042 modified-EUI-64 example (`02-00-5E-aa-bb-cc-dd-ee`); Zigbee/HA real-device forms (`84:71:27:ff:fe:93:17:24`, uppercase UI `A4:C1:38:0C:AC:70:4C:37`); HL7 ZigBee example `DF:3B:00:11:22:33:FF:EE`; broadcast/nil sentinels.

---

## 13. Open Decisions (with recommendations)

| # | Decision | Recommendation | Rationale |
|---|----------|----------------|-----------|
| 1 | **`DEFAULT_OUTPUT_FORMAT`** - `colon` vs `hyphen` vs `bare` | **`colon` (uppercase octets) default; `hyphen`, `bare`, `cisco`, `eui64`, `bit_reversed` offered** | Colon is the dominant interchange form (Unix, PG output, Bluetooth, Zigbee/Thread, Rust, stdnum "minimal consistent representation"); Paxman canonical = machine-joinable key; hyphen is the IEEE display but colon is what most tooling emits. Presentational-only either way. |
| 2 | **Canonical case** - uppercase (Paxman convention: Country/BIC/ISBN) vs lowercase (stdnum/Go/PG output) | **Uppercase**, document the stdnum/PG divergence | Paxman folds case in grammars and canonicalizes uppercase across every shipped capability; deterministic and greppable against IEEE listing style; HA bug 42913 shows systems already disagree per field, so one documented convention beats ecosystem mimicry. |
| 3 | **Single grammar vs two (EUI-48/EUI-64)** | **Single `mac_address_recognition`** with per-family branch ordering (64 before 48; 16 before 12 bare) | EUI-64 spans contain EUI-48 sub-spans; within-grammar longer-wins dedup resolves them, cross-grammar containment would be preserved → spurious `AMBIGUOUS` with 12-hex vs 16-hex values (BIC §4.2 reasoning; the opposite of ISBN where shapes do not nest). |
| 4 | **Bare 12/16-hex recognition default-on vs gated** | **Default-on** (ecosystem consensus: validator.js/Go/netaddr/PG all accept bare); document the git-SHA collision (§14); optional `include_bare: bool = True` contract gate only if field data shows false-positive pain | Bare hex is the DB-key form the capability exists to normalize; gating it would orphan the most common API/DB dump form; the collision is cross-domain (a git SHA in a MAC pipeline is user error, same as an IPv6 in an EUI-64 field). |
| 5 | **Loose ecosystem tolerances** (1-2-digit octets `0:1b:...`; 24-bit words `08002b:010203`; whitespace separator) | **All DEFER** to community `extra_grammars` with written rationale; reconsider 24-bit-word form for v2 only if PG-corpora demand shows | 1-2-digit octets collide with IPv6 textual forms (an all-short-group IPv6 would be claimed as local EUI-64 - the exactly-2-digit floor is the Go/validator.js/PG consensus mitigation); 24-bit words have no standard backing ("not part of any standard", PG) and add a third word-split family; whitespace separator has single-validator attestation and prose-adjacent risk. Every DEFER is inventoried (§2.1), not silent. |
| 6 | **OUI registry validation always-on (stdnum parity) vs gated** | **Gated `include_oui_validation=False`**; locally administered never checked regardless | stdnum checks universal addresses by default because its snapshot ships in-distribution; Paxman's determinism is snapshot-scoped and an embedded OUI set is staleness-prone exactly like ISBN Range/SWIFT Directory - the shipped gating precedent (ISBN `include_range_validation=False`, IBAN `include_registry_validation=False`). |
| 7 | **Offered-format set** - include `modified_eui64` (IPv6 IID U/L-flip)? | **Exclude from v1**; offer `eui64` (FF-FE insertion) and `bit_reversed` (per-octet swap) only | `modified_eui64` is an IPv6-domain semantic (RFC 4291/4862; RFC 8064 now discourages EUI-64-derived IIDs), only meaningful from EUI-48 input, and the U/L flip is a semantic transform, not a display re-insertion; Paxman's format seam should stay presentation-pure. Community extension owns it. |
| 8 | **Label span inclusion (`MAC:`)** | **Include label in `raw_text` span (fused regex); `notation.compact` label-free** | Mirrors ISSN `ISSN 1234-5679` / ISBN / IBAN `IBAN: DE89...` / BIC `BIC: DEUTDEFF` shipped behavior; useful for UX highlighting of the full mention. |
| 9 | **Historical rule for `year` pinning** - ship only `ieee_802_ed2024.py` vs also `ieee_802_ed2014.py` | **Ship only the 2024 structure rule in v1**; a `year=2014` pin yields `INVALID`-for-recognized (documented §8 row 18); add `ieee_802_ed2014.py` only if a caller story for historical pinning emerges | MAC structure has not changed across editions (48/64-bit hex identifier since 802-2001; §9.2/§8.2 clause renumbering is editorial); a second rule file doubles wiring for zero behavioral difference; temporal filtering remains exercisable via tests. |
| 10 | **Bit-reversal policy** - recognize-as-is vs attempt detection vs REJECT | **Recognize-as-is; `bit_reversed` offered format renders the deterministic per-octet swap; never reinterpret** | Bit-reversed spellings are valid MACs to every validator and lexically indistinguishable from canonical ones (RFC 2469; PG "widely ignored nowadays"); detection would violate determinism-by-construction (no world-knowledge); mirrors the ISIN transposed-letter flaw precedent: documented, never corrected. |

---

## 14. Ambiguity Analysis (Paxman-specific)

- **No inherent MAC-vs-MAC ambiguity.** Like BIC and ISIN, MAC addresses have fixed structure and no positional reading ambiguity (Date's `01/02/2026` problem cannot arise: a colon run is either 6 or 8 octets, and each octet is position-fixed). Two distinct MACs in one slice are an authorial choice (ARP flow lines, ACL pairs, source/destination), not a parsing ambiguity - segmentation is the intended path. Different separator families, cases, and label presence of the same value are the same canonical value; formatting must not affect status.
- **EUI-48 nested in EUI-64 is a containment case, not ambiguity.** An 8-octet EUI-64 contains 6-octet EUI-48-shaped runs; with a single grammar, the engine's within-grammar longer-wins dedup leaves exactly one candidate, and the regex branch ordering prevents most sub-matches from being emitted at all. Had this shipped as two grammars, cross-grammar containment would be *preserved* by design (`orchestrator:_dedup_spans` never dedups across grammars) and the pipeline would surface two candidates with different canonical values (12-hex vs 16-hex) - spurious `AMBIGUOUS`. This is the concrete reason §4.2 mandates one grammar for both lengths; it is also the difference from ISBN, where 10- and 13-digit shapes do not nest and two grammars are safe.
- **EUI-64 text vs IPv6 text is a cross-capability overlap, not in-capability ambiguity.** An all-2-digit-group colon string (`0a:00:2b:ff:fe:01:02:03`) is simultaneously a valid modified EUI-64 and a valid full IPv6 textual address. Within the MacAddress capability it resolves deterministically to the EUI-64; within the IP capability it resolves as IPv6. Paxman's per-capability resolution makes this caller-owned (each capability validates its own domain), exactly like BIC-vs-IBAN length overlap and the BIC report's treatment of sibling capabilities; the v1 exactly-2-digit octet floor (§13 decision 5) exists precisely to keep this overlap as narrow as possible without losing the `mac_unix`/HA-attested 8-octet forms.
- **Bit-reversed forms are not ambiguity - they are unrecognized provenance.** RFC 2469's `12-34-56-78-9A-BC` ↔ `48-2C-6A-1E-59-3D` and PostgreSQL's `08-00-2b-01-02-03` = `10:00:D4:80:40:C0` show that a bit-swapped spelling is a *different valid MAC* under canonical interpretation. Paxman cannot detect "this was a Token Ring display" without world-knowledge, which determinism-by-construction forbids; the input resolves to its literal identity, and the `bit_reversed` offered format makes the swap available as a deterministic presentational transform. This is the ISIN transposed-letter precedent (both spellings validate; neither is corrected) restated for a display-order domain.
- **Bare-hex vs other hex domains (git SHA, MEID fragments) is a cross-domain false-positive surface, not in-capability ambiguity.** Exactly-12-hex bare tokens are legitimate MACs (validator.js/Go/netaddr/PG consensus) and also the common git abbreviated-SHA length. Within a `canonicalize(input, MacAddressContract)` call the claim is correct-by-construction; the false-positive risk only materializes when a caller feeds non-MAC text to the MAC capability - the same class of cross-domain concern as an IPv6 pasted into an EUI-64 field. Open Decision 4 records the optional `include_bare` gate if field data ever shows real pain; the default follows ecosystem consensus.
- **OUI staleness and private registrations are not ambiguity.** A universal address whose OUI is absent from an embedded snapshot resolves `INVALID` under `include_oui_validation=True` with an old snapshot and `SUCCESS` with a fresh one - determinism-by-snapshot per ARCHITECTURE.md, not competing values; the snapshot version lives in `Provenance.version` (`"Rolling"`). Private ("PRIVATE"-listed) registrations are equally unknowable from public snapshots and are covered by the same gating argument.

---

## 15. URL Reference (authoritative, fetched 2026-08-31)

| Claim | URL | Kind |
|-------|-----|------|
| RFC 7042 (BCP 141) - EUI-48/EUI-64 terminology, OUI structure, I/G + U/L bits, Modified EUI-64, documentation values, 802.15.4/ZigBee usage (fetched in full) | <https://www.rfc-editor.org/rfc/rfc7042.txt> | primary |
| RFC 2469 - canonical vs MSB/Token-Ring bit order, worked bit-swap figure (fetched in full) | <https://www.rfc-editor.org/rfc/rfc2469.txt> | primary |
| IEEE Registration Authority FAQ - EUI-48/EUI-64 definitions, MA-L/MA-M/MA-S table, CID, IAB retirement, RA history (fetched) | <https://standards.ieee.org/faqs/regauth/> | primary |
| IEEE RA MAC Addresses product page - MA-L/MA-M/MA-S blocks, Bluetooth Device Address usage, IoT framing (fetched) | <https://standards.ieee.org/products-programs/regauth/mac/> | primary |
| IEEE Std 802-2014 catalogue page - "specifies the structure of IEEE 802 MAC addresses", Superseded/Revised-By 802-2024 record, 802c-2017 amendment record with URL (fetched) | <https://standards.ieee.org/standard/802-2014.html> | primary |
| IEEE Std 802c-2017 (SLAP amendment) record (linked from the fetched 802-2014 page) | <https://standards.ieee.org/ieee/802c/6890> | primary |
| IEEE EUI/OUI/CID tutorial (cited by RFC 7042 §8.2, IEEE RA FAQ, Bluetooth Core; PDF fetch blocked by content type - content triangulated via RFC 7042 + RA FAQ + Wikipedia) | <https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf> | primary |
| IEEE RA public listing (registry of record for the OUI snapshot layer) | <https://regauth.standards.ieee.org/> | primary |
| Bluetooth Core 6.0 Part B Baseband - BD_ADDR = EUI-48 per IEEE 802-2014 §8.2, LAP/UAP/NAP fields, reserved LAP range (content retrieved via search excerpt of the official HTML spec) | <https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-60/out/en/br-edr-controller/baseband-specification.html> | primary |
| PostgreSQL 18 Network Address Types - `macaddr`/`macaddr8` input tables, `macaddr8_set7bit`, bit-order convention note (fetched in full) | <https://www.postgresql.org/docs/current/datatype-net-types.html> | primary |
| python-stdnum `stdnum/mac.py` - compact/validate regex, OUI numdb lookup, bit predicates (fetched in full) | <https://github.com/arthurdejong/python-stdnum/blob/master/stdnum/mac.py> | primary |
| python-stdnum `stdnum.mac` docs (doctest output forms) | <https://arthurdejong.org/python-stdnum/doc/2.1/stdnum.mac> | primary |
| validator.js `isMACAddress.js` - backreference-consistent separators, dot/no-separator variants, `eui` option (fetched in full) | <https://github.com/validatorjs/validator.js/blob/master/src/lib/isMACAddress.js> | primary |
| Go `net/mac.go` `ParseMAC` - accepted format list incl. 20-octet IPoIB, single-separator dispatch (fetched in full) | <https://github.com/golang/go/blob/master/src/net/mac.go> | primary |
| netaddr Tutorial 2 (MAC addresses) - dialect outputs (`mac_unix`, `mac_cisco`, `mac_bare`, `mac_pgsql`) and accepted input forms (fetched via search result embedding the tutorial) | <https://netaddr.readthedocs.io/en/latest/tutorial_02.html> | primary |
| netaddr `strategy/eui48.py` source - `RE_MAC_FORMATS` regex list, dialect class definitions (fetched via search result embedding the source) | <https://github.com/netaddr/netaddr/blob/master/netaddr/strategy/eui48.py> | primary |
| Rust `macaddr` crate - `MacAddr6`/`MacAddr8`, Display `:`/`-`/`.` forms, U/L + I/G predicates (fetched) | <https://docs.rs/macaddr/latest/macaddr/> + <https://docs.rs/macaddr/latest/macaddr/struct.MacAddr6.html> | primary |
| HL7 Terminology - ZigBee Address NamingSystem (colon-separated 8-octet display, EUI-64 status, OUI linkage; content retrieved via search excerpt of the official terminology page) | <https://terminology.hl7.org/NamingSystem-zigbee-address-identifier.html> | primary |
| Wikipedia MAC address - notation conventions, bit-reversed section, U/L + I/G bits, 802c SLAP table, MA-L/MA-M/MA-S history (secondary) | <https://en.wikipedia.org/wiki/MAC_address> | secondary |
| Home Assistant Zigbee IEEE-address case-sensitivity bug (real-device `ff:fe` addresses, UI uppercase vs config lowercase) (secondary) | <https://github.com/home-assistant/home-assistant.io/issues/42913> | secondary |
| EE Times ZigBee addressing - 64-bit IEEE address naming ("MAC address, also called IEEE address, long address, or extended address") (secondary) | <https://www.eetimes.com/zigbee-applications-part-4-zigbee-addressing/> | secondary |
| ISSN / IBAN / BIC / ISIN research precedents | `docs/development/research/2026-08-21-issn-canonicalization.md`, `2026-08-22-iban-canonicalization.md`, `2026-08-23-bic-canonicalization.md`, `2026-08-24-isin-canonicalization.md` | primary |
| Paxman scaffolder & conventions | `HOW_TO_ADD_NEW_CAPABILITY.md`, `HOW_TO_ADD_NEW_GRAMMAR.md`, `ARCHITECTURE.md` | primary |
| Paxman shipped precedent (read verbatim this session) | `paxman/capabilities/BIC/grammar/bic_recognition.py`, `paxman/capabilities/BIC/notation.py`, `paxman/core/grammar/stages.py`, `paxman/core/grammar/boundary.py`, `paxman/core/contract.py`, `paxman/core/domain.py`, `paxman/engine/orchestrator.py` | primary |

---

## 16. Evidence Completion - Resolved

This report's MAC-address-specific authoritative evidence has been fetched and cited (2026-08-31):

- [x] Governing standard + lineage: IEEE Std 802 editions 1990 → 2001 → 2014 (§9.2 / §8.2 "Universal addresses") → **802-2024 (current)**, with amendments 802a/802b/802c-2017 (SLAP)/802d/802f and the P802-REVc consolidation program; IEEE catalogue pages fetched; 802-2024 catalogue URL explicitly **not** fetched and marked for implementation-time resolution (no URL invented); citation anchored to §8.2 per 802-2014 numbering (the clause the Bluetooth Core Specification cites normatively).
- [x] RA and registry provenance: IEEE RA (successor to Xerox per RFC 7042 §1.3), MA-L (2^24) / MA-M (2^20) / MA-S (2^12) block table, CID vs OUI, IAB inactive since 2014-01-01 with its two OUI windows, public listing at regauth.standards.ieee.org, 7-business-day processing, PRIVATE/confidential option; `kind="registry"` `version="Rolling"`.
- [x] Structure: EUI-48 = 6 octets (OUI 24 + extension 24 / MA-M 28+20 / MA-S 36+12), EUI-64 = 8 octets; first-octet I/G (0x01) and U/L (0x02) bits with IEEE assignment policy (Local bit zero in OUIs); `FF-FE`/`FF-FF` translations and the IETF Modified EUI-64 (U/L invert + FF-FE) with the RFC 7042 `02-00-5E-aa-bb-cc-dd-ee` example and the PostgreSQL `macaddr8_set7bit` vector.
- [x] No checksum **proved**: no check character exists in IEEE 802, RFC 7042, the IEEE EUI tutorial, or any of the six ecosystem validators (python-stdnum's optional check is an OUI *registry membership* lookup, not a check digit) - "structure is all there is" (BIC §5.1 analogue).
- [x] Bit-order nuance: RFC 2469 canonical (LSB/Ethernet) vs MSB/IBM/Token-Ring/non-canonical forms with the full worked figure; PostgreSQL's IEEE 802-2001 colon-vs-hyphen display convention quote ("widely ignored nowadays"); the `bit_reversed` offered format defined with the verified arithmetic vector (12-34-56-78-9A-BC ↔ 48-2C-6A-1E-59-3D).
- [x] Ecosystem regex consensus: python-stdnum (compact→lowercase colon + strict post-compact regex + OUI lookup), validator.js (backreference separator consistency, dot/no-sep, eui 48/64), Go `ParseMAC` (format list, 6/8/20 octets), netaddr (`RE_MAC_FORMATS` incl. {1,2}/{1,4} tolerance + dialect table), Rust `macaddr` (Display forms + bit predicates), PostgreSQL (7 input spellings, `macaddr8`, `macaddr8_set7bit`).
- [x] Recognition-surface inventory complete (§2.1): 18 attested written forms, each with evidence and an explicit RECOGNIZE (10) / DEFER (8) disposition - no silently unhandled form; includes the user-required colon, hyphen, Cisco tri-dot, bare, bit-reversed/Token-Ring/FDDI, EUI-64, and IoT (Zigbee/Thread/802.15.4, Bluetooth BD_ADDR, InfiniBand) forms.
- [x] Wild input shapes validated (§2.2) against the RFCs, IEEE RA pages, PostgreSQL docs, device corpora (Bluetooth/Zigbee/Home Assistant/Cisco), and all six validators; 18 adversarial categories including glued labels, mixed separators, mis-lengths, OCR homoglyphs, and sentinel values.
- [x] Label scope decision: `MAC` fused `[\s:-]+` RECOGNIZE (BIC/ISSN/IBAN precedent); `HWaddr`/`ether`/`EUI-48:` DEFER with rationale; label-in-span / label-free-notation semantics fixed.
- [x] Bit-reversal policy decision (§13 decision 10): recognize-as-is, never reinterpret, deterministic presentational swap offered - documented against determinism-by-construction.
- [x] OUI registry liveness scope decision (§5.4/§13 decision 6): gated `include_oui_validation=False`, locally administered exempt, stdnum-default divergence documented; determinism-by-snapshot semantics.
- [x] IoT carrier evidence: Zigbee/Thread/802.15.4 EUI-64 (HL7 NamingSystem with colon display + OUI statement; EE Times naming; Home Assistant real-device `ff:fe` addresses and case-sensitivity bug), Bluetooth BD_ADDR = EUI-48 per IEEE 802-2014 §8.2 (Core 6.0 Part B text), InfiniBand GUID/20-octet IPoIB (Go), FireWire (RFC 7042 list).
- [x] Single-grammar-for-both-lengths decision (§4.2/§13 decision 3) grounded in the engine's per-grammar containment dedup semantics (verified in `paxman/engine/orchestrator.py:_dedup_spans` behavior per ARCHITECTURE.md).
- [x] Recognition pattern **validated by execution** (2026-08-31): the §4.2 grammar block was compiled and behavior-tested against 27 positive vectors (all §2.1 RECOGNIZE forms, RFC 7042 documentation values, Zigbee/HA real-device forms, HA `-endpoint` suffix), 26 negative vectors (mixed separators, 7-octet truncation, glued labels, 1-digit octets, 24-bit words, IPv6, UUID, OCR homoglyphs), span invariants (`raw_text == text[start:end]`), and the `format_value` seam against the RFC 2469 and PostgreSQL bit-reversal vectors with the involution property - three bugs were found and fixed during this pass (bare-branch width arithmetic, missing truncation guard, missing mid-run lookbehind), and the shipped §4.2 block is byte-equal to the validated pattern.

File layout and rule provenance in §5.2 / §11 / §12 frozen for implementation (pending scaffolder invocation per HOW_TO_ADD_NEW_CAPABILITY.md Step 0).

---

## Appendix - What the Shipped BIC, ISBN, IP and Phone Capabilities Teach MacAddress (verbatim precedent)

> The following precedent is **verbatim-sourced from the codebase** (read this session from the working tree; not speculative) and anchors the proposal to what Paxman already ships.

Refer to `paxman/capabilities/BIC/`, `paxman/capabilities/ISBN/`, `paxman/capabilities/IP/`, `paxman/capabilities/Phone/` plus `paxman/core/grammar/{pipeline,stages,boundary}.py`, `paxman/core/domain.py`, and `paxman/engine/orchestrator.py` - see the deep-dive excerpts in §4.2/§5/§6 above. The five architectural lessons for MacAddress:

1. **Grammar strips, rule validates, capability formats.** The shipped BIC grammar compiles a module-scope string via `RegexStage`, wraps it in `BoundaryGuard.word_only()` lookarounds, fuses the `BIC|SWIFT` label with `[\s:-]+`, and strips to compact via `ch.isascii() and ch.isalnum()` in `notation_fn` (verified `paxman/capabilities/BIC/grammar/bic_recognition.py:25-29,101-122`); rules enforce structure/lookup (`PARSER` + `LOOKUP_TABLE`); `format_value()` re-inserts presentation (`grouped`, `bic11`). **MacAddress mirrors this exactly**: 8 shape branches + `MAC` label fused, `compact`/`shape` notation, `Section 8.2-eui-structure` `PARSER` + gated OUI `LOOKUP_TABLE`, and a six-way `format_value()` seam.

2. **One file per provenance, one class per section.** ISBN ships `iso_2108_ed2017` (PARSER), `isbn_users_manual_ed2012` (superseded), `isbn_range_message_ed2026` (LOOKUP_TABLE, `requires_features={"include_range_validation"}`); BIC ships `iso_9362_ed2022` plus a gated directory layer in the report; IBAN fuses ISO 13616-1 + ISO 7064 and gates the SWIFT registry. **MacAddress ships `ieee_802_ed2024.py` (`PARSER`, `lifecycle="active"`) plus `ieee_oui_registry_ed2026.py` (`LOOKUP_TABLE`, `kind="registry"`, `requires_features={"include_oui_validation"}`)**; 802c-2017 and RFC 7042/2469 are evidence, not rule files (nothing they govern changes validity).

3. **No `output_format` in rules, ever.** The CI source scan (`tests/unit/test_rule_output_format_purity.py`) fails any `rules/` module containing the token; `normalize()` returns the default colon form; `format_value()` renders `hyphen`/`bare`/`cisco`/`eui64`/`bit_reversed`. The OUI registry rule must also return the identical colon string (dedup invariant, BIC precedent where the country rule and structure rule agree).

4. **Kernel enforcement is import-time, not review-time.** `Rule.__init_subclass__` rejects missing metadata, non-frozenset `target_semantics`/`requires_features`, and empty `target_semantics` (`paxman/core/domain.py:246-271`); `Grammar.__init_subclass__` requires a non-empty string `semantics` (`domain.py:297-306`); `resolve_output_format` treats `None`/`"default"`/default identically and raises `ContractError` otherwise (`paxman/core/contract.py:62-123`). Every code block in this report is written to pass those gates as-is.

5. **Single grammar with branch ordering beats two grammars where shapes nest.** BIC keeps 8/11 in one grammar via an optional group; ISBN splits 10/13 because they do not nest. EUI-48 shapes nest inside EUI-64 spans, so MacAddress follows the BIC side: one grammar, per-family branch ordering (64 before 48, 16 before 12), and the engine's within-grammar longer-wins containment dedup as the safety net - the concrete anti-spurious-`AMBIGUOUS` mechanism documented in `ARCHITECTURE.md` Recognition Pipeline Contract and `orchestrator:_dedup_spans`.

---

*Report saved to `docs/development/research/` (this directory) per the paxman-capability-research protocol for MacAddress. It mirrors the structure, depth, and provenance discipline of `docs/development/research/2026-08-22-iban-canonicalization.md`, `docs/development/research/2026-08-23-bic-canonicalization.md`, and the ISIN/ORCID precedents. For implementation, start from the `tools/new_capability.py` scaffolder per HOW_TO_ADD_NEW_CAPABILITY.md Step 0.*

*Note: `docs/development/` is ephemeral per `docs/development/AGENTS.md` - not shipped, may drift, may be removed without notice, and must not be referenced by code or shipped docs.*
