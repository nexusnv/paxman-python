"""BCP 47 tag recognition — ScannerMatcher on SeparatorFold view."""

from __future__ import annotations

from paxman.capabilities.Language.grammar.data.grandfathered_tags import (
    GRANDFATHERED_TAGS as _GRANDFATHERED_TAGS_SET,
)
from paxman.capabilities.Language.notation import LanguageNotation
from paxman.core.grammar import BoundarySpec, ScannerMatcher, StandardPre
from paxman.core.grammar.pipeline import PipelineGrammar
from paxman.core.grammar.scan_context import ScanContext, View

_GRANDFATHERED_SET: frozenset[str] = _GRANDFATHERED_TAGS_SET
_GRANDFATHERED_SORTED: tuple[str, ...] = tuple(
    sorted(_GRANDFATHERED_TAGS_SET, key=lambda t: (-len(t), t))
)


def _is_variant(subtag: str) -> bool:
    return (5 <= len(subtag) <= 8 and subtag.isalnum()) or (
        len(subtag) == 4 and subtag[0].isdigit() and subtag[1:].isalnum()
    )


def _notation_from_tag(tag: str) -> LanguageNotation:
    lower_tag = tag.lower()
    if lower_tag in _GRANDFATHERED_SET:
        return LanguageNotation(
            language="",
            extlang="",
            script="",
            region="",
            variant="",
            extension="",
            privateuse="",
            grandfathered=lower_tag,
            compact=lower_tag,
            raw_value=lower_tag,
        )
    if lower_tag.startswith("x-") or lower_tag == "x":
        compact = lower_tag
        return LanguageNotation(
            language="",
            extlang="",
            script="",
            region="",
            variant="",
            extension="",
            privateuse=compact,
            grandfathered="",
            compact=compact,
            raw_value=lower_tag,
        )
    parts = tag.split("-")
    language = parts[0].lower()
    idx = 1
    extlangs: list[str] = []
    if len(language) in (2, 3):
        while (
            idx < len(parts)
            and len(parts[idx]) == 3
            and parts[idx].isalpha()
            and len(extlangs) < 3
        ):
            extlangs.append(parts[idx].lower())
            idx += 1
    extlang = "-".join(extlangs)
    script = ""
    if idx < len(parts) and len(parts[idx]) == 4 and parts[idx].isalpha():
        s = parts[idx]
        script = s[0].upper() + s[1:].lower()
        idx += 1
    region = ""
    if idx < len(parts) and (
        (len(parts[idx]) == 2 and parts[idx].isalpha())
        or (len(parts[idx]) == 3 and parts[idx].isdigit())
    ):
        region = parts[idx].upper() if parts[idx].isalpha() else parts[idx]
        idx += 1
    variant_parts: list[str] = []
    extension_parts: list[str] = []
    privateuse = ""
    while idx < len(parts):
        sub = parts[idx]
        if sub.lower() == "x":
            privateuse = "-".join(p.lower() for p in parts[idx:])
            idx = len(parts)
            break
        if len(sub) == 1 and sub.isalnum() and sub.lower() != "x":
            break
        if _is_variant(sub):
            variant_parts.append(sub.lower())
            idx += 1
            continue
        break
    while idx < len(parts):
        sub = parts[idx]
        if sub.lower() == "x":
            privateuse = "-".join(p.lower() for p in parts[idx:])
            idx = len(parts)
            break
        if len(sub) == 1 and sub.isalnum() and sub.lower() != "x":
            singleton = sub.lower()
            idx += 1
            ext_subtags: list[str] = []
            while (
                idx < len(parts) and 2 <= len(parts[idx]) <= 8 and parts[idx].isalnum()
            ):
                if parts[idx].lower() == "x" and len(parts[idx]) == 1:
                    break
                ext_subtags.append(parts[idx].lower())
                idx += 1
            if ext_subtags:
                extension_parts.append(singleton + "-" + "-".join(ext_subtags))
            else:
                extension_parts.append(singleton)
            continue
        break
    variant = "-".join(variant_parts)
    extension = "-".join(extension_parts)
    compact_pieces: list[str] = []
    compact_pieces.append(language)
    if extlang:
        compact_pieces.extend(extlang.split("-"))
    if script:
        compact_pieces.append(script)
    if region:
        compact_pieces.append(region)
    if variant:
        compact_pieces.extend(variant.split("-"))
    if extension:
        compact_pieces.extend(extension.split("-"))
    if privateuse:
        compact_pieces.extend(privateuse.split("-"))
    compact = "-".join(compact_pieces)
    raw_value = lower_tag
    return LanguageNotation(
        language=language,
        extlang=extlang,
        script=script,
        region=region,
        variant=variant,
        extension=extension,
        privateuse=privateuse,
        grandfathered="",
        compact=compact,
        raw_value=raw_value,
    )


def _is_valid_langtag(tag: str) -> bool:
    parts = tag.split("-")
    if not parts or any(p == "" for p in parts):
        return False
    idx = 0
    first = parts[0]
    if 2 <= len(first) <= 3 and first.isalpha():
        idx = 1
        ext = 0
        while (
            idx < len(parts)
            and len(parts[idx]) == 3
            and parts[idx].isalpha()
            and ext < 3
        ):
            ext += 1
            idx += 1
    elif (len(first) == 4 and first.isalpha()) or (
        5 <= len(first) <= 8 and first.isalpha()
    ):
        idx = 1
    else:
        return False
    if idx < len(parts) and len(parts[idx]) == 4 and parts[idx].isalpha():
        idx += 1
    if idx < len(parts):
        p = parts[idx]
        if (len(p) == 2 and p.isalpha()) or (len(p) == 3 and p.isdigit()):
            idx += 1
    while idx < len(parts):
        p = parts[idx]
        if _is_variant(p):
            idx += 1
            continue
        if len(p) == 1 and p.isalnum() and p.lower() != "x":
            break
        if p.lower() == "x":
            break
        return False
    while idx < len(parts):
        p = parts[idx]
        if p.lower() == "x":
            break
        if len(p) == 1 and p.isalnum() and p.lower() != "x":
            idx += 1
            if idx >= len(parts):
                return False
            if not (2 <= len(parts[idx]) <= 8 and parts[idx].isalnum()):
                return False
            cnt = 0
            while (
                idx < len(parts) and 2 <= len(parts[idx]) <= 8 and parts[idx].isalnum()
            ):
                cnt += 1
                idx += 1
            if cnt == 0:
                return False
            continue
        return False
    if idx < len(parts) and parts[idx].lower() == "x":
        idx += 1
        if idx >= len(parts):
            return False
        has = False
        while idx < len(parts):
            p = parts[idx]
            if 1 <= len(p) <= 8 and p.isalnum():
                has = True
                idx += 1
            else:
                return False
        if not has:
            return False
    return idx == len(parts)


def _is_bare_language(tag: str) -> bool:
    return (
        (2 <= len(tag) <= 3 and tag.isalpha())
        or (len(tag) == 4 and tag.isalpha())
        or (5 <= len(tag) <= 8 and tag.isalpha())
    )


def _is_valid_tag(tag: str) -> bool:
    lower = tag.lower()
    if lower in _GRANDFATHERED_SET:
        return True
    parts = tag.split("-")
    if parts and parts[0].lower() == "x":
        return bool(
            len(parts) >= 2 and all(1 <= len(p) <= 8 and p.isalnum() for p in parts[1:])
        )
    if "-" not in tag:
        return False
    return _is_valid_langtag(tag)


def _bcp47_scan(view: View, pos: int) -> tuple[int, LanguageNotation] | None:
    subj = view.subject
    n = len(subj)
    if pos < 0 or pos >= n:
        return None
    # Grandfathered — longest-first
    lower_slice = subj[pos:].lower()
    for gt in _GRANDFATHERED_SORTED:
        if lower_slice.startswith(gt):
            end = pos + len(gt)
            tag = subj[pos:end]
            return (end, _notation_from_tag(tag))
    # Maximal hyphen-alnum run starting at pos
    run_end = pos
    while run_end < n and (subj[run_end].isalnum() or subj[run_end] == "-"):
        run_end += 1
    while run_end > pos and subj[run_end - 1] == "-":
        run_end -= 1
    if run_end <= pos:
        return None
    run = subj[pos:run_end]
    if "--" in run:
        double = run.find("--")
        run = run[:double]
        run_end = pos + len(run)
        if not run:
            return None
    parts = run.split("-")
    if any(p == "" for p in parts):
        return None
    for k in range(len(parts), 0, -1):
        candidate = "-".join(parts[:k])
        if _is_valid_tag(candidate):
            end = pos + len(candidate)
            return (end, _notation_from_tag(candidate))
        if "-" not in candidate and _is_bare_language(candidate):
            cand_end = pos + len(candidate)
            if cand_end < n and subj[cand_end] == "-":
                return (cand_end, _notation_from_tag(candidate))
    return None


def _bcp47_emit(span: tuple[int, int], ctx: ScanContext) -> LanguageNotation:
    s, e = span
    raw = ctx.text[s:e]
    normalized = raw.replace("_", "-")
    return _notation_from_tag(normalized)


_BCP47_SCANNER = ScannerMatcher(
    scan=_bcp47_scan,
    view_name="bcp47_normalized",
    boundary=BoundarySpec.WORD,
    emit=_bcp47_emit,
)


class BCP47TagGrammar(PipelineGrammar[LanguageNotation]):
    """BCP47 tag recognition — ScannerMatcher on SeparatorFold view."""

    name = "bcp47_tag_recognition"
    semantics = "bcp47_tag"
    single_value = True

    pre = StandardPre[LanguageNotation](empty_guard=True)
    matchers = (_BCP47_SCANNER,)
