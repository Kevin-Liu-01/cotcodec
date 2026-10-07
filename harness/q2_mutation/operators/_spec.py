"""Requirement specs, aspect vocabulary and requirement-to-site binding.

Specs come from a blind author (``author: blind-model-author-v1``) who never saw
checker code. Operators never read checker code either; their labels are
derived only from the spec: which aspects a requirement statement or
observable mentions, which aspects the spec lists as unconstrained, and where
in the gold document a requirement's observable lives.

Aspect matching is deliberately simple (case-insensitive word patterns) and
every match is quoted back in the witness, so an auditor can check each label.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from harness.q2_mutation.operators import _formula as fx
from harness.q2_mutation.operators._diff import Change, seg, unseg
from harness.q2_mutation.schema import Requirement, RequirementSpec

Spec = RequirementSpec


def load_spec(path: str | Path) -> RequirementSpec:
    """Load and strictly validate a blind-author requirement spec (YAML)."""
    import yaml  # the LibreOffice container plans from dicts and has no PyYAML

    return RequirementSpec.from_dict(yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def req_text(req: Requirement) -> str:
    return f"{req.statement}\n{req.observable}"


def requirement_by_id(spec: RequirementSpec, req_id: str) -> Requirement:
    for req in spec.requirements:
        if req.req_id == req_id:
            return req
    raise KeyError(req_id)


# --------------------------------------------------------------------------- aspects

ASPECTS: dict[str, tuple[str, ...]] = {
    "formula": (r"formula", r"function", r"\bSUM\b", r"\bAVERAGE\b", r"\bCOUNT", r"\bIF\(",
                r"\bVLOOKUP\b", r"calculat", r"\bcompute", r"\bderive"),
    "literal": (r"hard.?cod", r"\bliteral", r"paste.{0,20}values?", r"values? only", r"static"),
    "bold": (r"\bbold",),
    "italic": (r"\bitalic",),
    "underline": (r"underlin",),
    "strike": (r"strike",),
    "color": (r"colou?r", r"\bred\b", r"\bblue\b", r"\bgreen\b", r"\byellow\b", r"\bblack\b",
              r"\bwhite\b", r"\borange\b", r"\bpurple\b", r"\bgr[ae]y\b", r"\bpink\b"),
    "font_size": (r"font.?size", r"\bpt\b", r"\bpoints?\b", r"\bsize\b"),
    "font_name": (r"\bfont\b", r"typeface", r"\bArial\b", r"\bCalibri\b", r"Times New Roman",
                  r"\bLiberation", r"\bDejaVu"),
    "highlight": (r"highlight",),
    "fill": (r"\bfill", r"background", r"shad(e|ing)"),
    "number_format": (r"decimal", r"percent", r"%", r"currency", r"\$", r"number format",
                      r"format(ted)? as", r"date format", r"thousand", r"digits?"),
    "alignment": (r"align", r"\bcent(er|re)", r"justif"),
    "spacing": (r"spacing", r"double.?spac", r"single.?spac", r"line height", r"\bindent"),
    "style": (r"\bstyles?\b", r"\bheading", r"\bstyled\b"),
    "case": (r"upper.?case", r"lower.?case", r"capitali", r"title case", r"\bcaps\b",
             r"all capitals"),
    "position": (r"position", r"\bmov(e|ed|ing)\b", r"\bplace", r"\blocat", r"\bleft\b",
                 r"\bright\b", r"\btop\b", r"\bbottom\b", r"\bcent(er|re)", r"\balign",
                 r"coordinates?"),
    "geometry": (r"\bresiz", r"\bwidth", r"\bheight", r"\bdimension", r"\bsize\b"),
    "order": (r"\bsort", r"\border", r"ascending", r"descending", r"\brank", r"sequence"),
    "exact_geometry": (r"coordinates?", r"exact(ly)? (position|location|size|placement)",
                       r"\b\d+(\.\d+)?\s?(cm|mm|in|inch|inches|pt|px|emu)\b"),
    "z_order": (r"bring to front", r"send to back", r"\bforeground", r"\blayer",
                r"z.?order", r"\boverlap", r"\bin front\b", r"\bbehind\b"),
    "zoom": (r"\bzoom",),
    "selection": (r"\bselect", r"active cell", r"\bcursor", r"\bfocus"),
    "active_sheet": (r"active (sheet|tab)", r"\bactivat", r"\bswitch to\b",
                     r"\bopen (the )?(sheet|tab)"),
    "function": (r"\bfunctions?\b",),
    "references": (r"\babsolute\b", r"\brelative\b", r"\$[A-Z]{1,3}\$?[0-9]", r"\breferenc"),
    "metadata": (r"propert(y|ies)", r"metadata", r"\bauthor\b", r"\bsubject\b",
                 r"\bkeywords?\b", r"document title"),
    "sheet_name": (r"\brenam", r"sheet name", r"\btab name", r"name (the|a|this) (sheet|tab)",
                   r"\bcalled\b"),
    "sheet_set": (r"\bsheets?\b", r"\bworksheets?\b", r"\btabs?\b"),
    "slide_set": (r"\bslides?\b",),
    "notes": (r"\bnotes?\b", r"\bspeaker",),
    "paragraph_set": (r"\bparagraphs?\b", r"\bdelete", r"\bremove", r"\binsert", r"\badd"),
    "whitespace": (r"\bindent", r"whitespace", r"\bspaces\b", r"\btabs?\b", r"\bformatting\b"),
    "comments": (r"\bcomments?\b",),
    "newline": (r"newline", r"line ending", r"end of (the )?file", r"\bEOF\b", r"trailing"),
    "key_order": (r"\border\b", r"\bsort", r"alphabetical"),
    "number_type": (r"\binteger", r"\bfloat", r"whole number", r"decimal point"),
    "table": (r"\btables?\b", r"\bcells?\b"),
}

_COMPILED = {
    aspect: tuple(re.compile(p, re.IGNORECASE) for p in patterns)
    for aspect, patterns in ASPECTS.items()
}


def mentions(text: str, aspect: str) -> list[str]:
    """Return the snippets of ``text`` that mention ``aspect``."""
    found = []
    for pattern in _COMPILED[aspect]:
        for match in pattern.finditer(text):
            found.append(match.group(0))
    return sorted(set(found))


def requirement_mentions(req: Requirement, aspect: str) -> list[str]:
    return mentions(req_text(req), aspect)


def spec_mentions(spec: RequirementSpec, aspect: str) -> list[tuple[str, list[str]]]:
    """Every requirement that mentions ``aspect``, with the matched snippets."""
    out = []
    for req in spec.requirements:
        hits = requirement_mentions(req, aspect)
        if hits:
            out.append((req.req_id, hits))
    return out


AMBIGUOUS_FLAG = "[AMBIGUOUS]"


def is_flagged(text: str) -> bool:
    """The blind author marks open questions with a leading ``[AMBIGUOUS]``."""
    return text.lstrip().startswith(AMBIGUOUS_FLAG)


def allowed_mentions(spec: RequirementSpec, aspect: str) -> list[tuple[int, str, list[str]]]:
    """Allowed-variation entries that mention ``aspect`` (index, text, snippets).

    Entries the author flagged ``[AMBIGUOUS]`` record an open question, not a
    freedom, so they never count here; see :func:`flagged_mentions`.
    """
    out = []
    for index, text in enumerate(spec.allowed_variations):
        hits = mentions(text, aspect)
        if hits and not is_flagged(text):
            out.append((index, text, hits))
    return out


def flagged_mentions(spec: RequirementSpec, aspect: str) -> list[str]:
    """Flagged requirements or allowed variations that mention ``aspect``."""
    out = []
    for req in spec.requirements:
        if is_flagged(req.statement) and requirement_mentions(req, aspect):
            out.append(req.req_id)
    for index, text in enumerate(spec.allowed_variations):
        if is_flagged(text) and mentions(text, aspect):
            out.append(f"allowed_variations[{index}]")
    return out


# --------------------------------------------------------------------------- units


def unit_of(loc: str, family: str) -> str | None:
    """Truncate a change locator to its mutable unit (cell, block, shape, line, key)."""
    parts = loc.split("/")
    if family == "xlsx":
        if len(parts) >= 4 and parts[0] == "sheets" and parts[2] == "cells":
            return "/".join(parts[:4])
        return None
    if family == "docx":
        if parts[0] != "body" or len(parts) < 2 or parts[1].startswith("+"):
            return None
        if len(parts) >= 6 and parts[2] == "cell":
            return "/".join(parts[:6])
        return "/".join(parts[:2])
    if family == "pptx":
        if parts[0] != "slides" or len(parts) < 2 or parts[1].startswith("+"):
            return None
        if len(parts) >= 4 and parts[2] == "shapes" and not parts[3].startswith("+"):
            if len(parts) >= 8 and parts[4] == "table" and parts[5] == "rows":
                return "/".join(parts[:8])
            return "/".join(parts[:4])
        return "/".join(parts[:2])
    if family in {"text", "config"}:
        if parts[0] == "lines" and len(parts) >= 2 and not parts[1].startswith("+"):
            return "/".join(parts[:2])
        if parts[0] == "parsed" and len(parts) >= 3 and parts[1] == "value":
            return loc
        return None
    return None


def delta_units(delta: list[Change], family: str) -> dict[str, set[str]]:
    """Units the task changed (initial -> gold), keyed by unit, with the change kinds."""
    units: dict[str, set[str]] = {}
    for change in delta:
        unit = unit_of(change.loc, family)
        if unit is not None:
            units.setdefault(unit, set()).add(change.kind)
    return units


# --------------------------------------------------------------------------- binding


@dataclass(frozen=True)
class Binding:
    req_id: str
    units: tuple[str, ...]
    method: str
    confidence: str
    hints: tuple[str, ...] = field(default=())

    def as_dict(self) -> dict:
        return {
            "req_id": self.req_id,
            "units": list(self.units),
            "method": self.method,
            "confidence": self.confidence,
            "hints": list(self.hints),
        }


_QUOTED = re.compile(r"\"([^\"]{2,200})\"|“([^”]{2,200})”|'([^']{3,200})'|‘([^’]{3,200})’")
_CELL_REF = re.compile(
    r"(?:(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))!)?\b(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6})"
    r"(?::(\$?[A-Z]{1,3}\$?[1-9][0-9]{0,6}))?\b"
)
_COLUMN = re.compile(r"\b[Cc]olumns?\s+([A-Z]{1,3})\b")
# A reference right after one of these words names cells the requirement excludes
# ("cells outside B1:E30 are not touched"), so it binds nothing.
_EXCLUDING = re.compile(
    r"(outside|except|other than|apart from|beyond|besides|not in|excluding)"
    r"(\s+(of|the|range|cells?|columns?|rows?))*\s*$",
    re.IGNORECASE,
)


def _excluded(text: str, start: int) -> bool:
    return _EXCLUDING.search(text[max(0, start - 40):start]) is not None
_SLIDE = re.compile(r"\bslides?\s+(\d{1,3})\b", re.IGNORECASE)
_ORDINAL = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
}
_ORDINAL_SLIDE = re.compile(r"\b(" + "|".join(_ORDINAL) + r")\s+slide\b", re.IGNORECASE)
_PARAGRAPH = re.compile(r"\bparagraph\s+(\d{1,3})\b", re.IGNORECASE)
_ORDINAL_PARAGRAPH = re.compile(r"\b(" + "|".join(_ORDINAL) + r")\s+paragraph\b", re.IGNORECASE)
_KEY = re.compile(
    r"[\"'`]?([A-Za-z_][A-Za-z0-9_\-]*(?:\.[A-Za-z0-9_\-]+)+|[A-Za-z_][A-Za-z0-9_]{2,})[\"'`]?"
)


def quoted(text: str) -> list[str]:
    return [next(g for g in m.groups() if g) for m in _QUOTED.finditer(text)]


def _xlsx_hint_units(req: Requirement, snap: dict) -> tuple[list[str], list[str]]:
    units: list[str] = []
    hints: list[str] = []
    sheets = list(snap["sheets"])
    default_sheet = next(
        (s for s in sheets if snap["sheets"][s].get("view", {}).get("tab_selected")),
        sheets[0] if sheets else "",
    )
    text = req_text(req)
    mentioned_sheets = [s for s in sheets if re.search(rf"\b{re.escape(s)}\b", text)]
    for match in _CELL_REF.finditer(text):
        if _excluded(text, match.start()):
            continue
        sheet = match.group(1) or match.group(2)
        if sheet is not None and sheet not in snap["sheets"]:
            continue
        if sheet is None:
            sheet = mentioned_sheets[0] if len(mentioned_sheets) == 1 else default_sheet
        try:
            cells = fx.cells_in_ref(match.group(3), match.group(4), cap=2048)
        except fx.FormulaError:
            continue
        hints.append(match.group(0))
        for row, col in cells:
            units.append(f"sheets/{seg(sheet)}/cells/{seg(fx.make_address(row, col))}")
    for match in _COLUMN.finditer(text):
        if _excluded(text, match.start()):
            continue
        letters = match.group(1)
        hints.append(match.group(0))
        targets = mentioned_sheets or [default_sheet]
        for sheet in targets:
            for address in snap["sheets"][sheet]["cells"]:
                if re.fullmatch(rf"{letters}\d+", address):
                    units.append(f"sheets/{seg(sheet)}/cells/{seg(address)}")
    return units, hints


def _docx_blocks_with_paths(blocks: list[dict], prefix: str) -> list[tuple[str, dict]]:
    out = []
    for i, block in enumerate(blocks):
        path = f"{prefix}/{i}"
        if block["type"] == "p":
            out.append((path, block))
        else:
            for r, row in enumerate(block["rows"]):
                for c, cell in enumerate(row):
                    for k, inner in enumerate(cell):
                        if inner["type"] == "p":
                            out.append((f"{path}/cell/{r}/{c}/{k}", inner))
    return out


def docx_paragraphs(snap: dict) -> list[tuple[str, dict]]:
    return _docx_blocks_with_paths(snap["body"], "body")


def _docx_hint_units(req: Requirement, snap: dict) -> tuple[list[str], list[str]]:
    units: list[str] = []
    hints: list[str] = []
    paragraphs = docx_paragraphs(snap)
    for text in quoted(req_text(req)):
        for path, block in paragraphs:
            if text.strip() and text.strip() in block["text"]:
                units.append(path)
                hints.append(f'"{text}"')
    top_level = [(p, b) for p, b in paragraphs if p.count("/") == 1 and b["text"].strip()]
    for match in _PARAGRAPH.finditer(req_text(req)):
        n = int(match.group(1))
        if 1 <= n <= len(top_level):
            units.append(top_level[n - 1][0])
            hints.append(match.group(0))
    for match in _ORDINAL_PARAGRAPH.finditer(req_text(req)):
        n = _ORDINAL[match.group(1).lower()]
        if 1 <= n <= len(top_level):
            units.append(top_level[n - 1][0])
            hints.append(match.group(0))
    if re.search(r"\b(title|heading)\b", req_text(req), re.IGNORECASE):
        for path, block in paragraphs:
            if re.search(r"(title|heading)", block.get("style", ""), re.IGNORECASE):
                units.append(path)
                hints.append(f"style {block['style']}")
    return units, hints


def pptx_shapes(snap: dict) -> list[tuple[str, dict]]:
    out = []
    for s, slide in enumerate(snap["slides"]):
        for k, shape in enumerate(slide["shapes"]):
            out.append((f"slides/{s}/shapes/{k}", shape))
    return out


def _pptx_hint_units(req: Requirement, snap: dict) -> tuple[list[str], list[str]]:
    units: list[str] = []
    hints: list[str] = []
    slides = set()
    for match in _SLIDE.finditer(req_text(req)):
        n = int(match.group(1))
        if 1 <= n <= len(snap["slides"]):
            slides.add(n - 1)
            hints.append(match.group(0))
    for match in _ORDINAL_SLIDE.finditer(req_text(req)):
        n = _ORDINAL[match.group(1).lower()]
        if 1 <= n <= len(snap["slides"]):
            slides.add(n - 1)
            hints.append(match.group(0))
    for text in quoted(req_text(req)):
        for path, shape in pptx_shapes(snap):
            if text.strip() and text.strip() in (shape.get("text") or ""):
                units.append(path)
                hints.append(f'"{text}"')
            for r, row in enumerate((shape.get("table") or {}).get("rows", [])):
                for c, cell in enumerate(row):
                    if text.strip() and text.strip() in cell["text"]:
                        units.append(f"{path}/table/rows/{r}/{c}")
                        hints.append(f'"{text}"')
    if re.search(r"\btitle\b", req_text(req), re.IGNORECASE):
        for path, shape in pptx_shapes(snap):
            slide = int(path.split("/")[1])
            if (shape.get("placeholder") or {}).get("type") in {"title", "ctrTitle"} and (
                not slides or slide in slides
            ):
                units.append(path)
                hints.append("title placeholder")
    if slides and not units:
        units.extend(f"slides/{s}" for s in sorted(slides))
    elif slides:
        units = [u for u in units if int(u.split("/")[1]) in slides] or units
    return units, hints


def config_paths(value: object, prefix: str = "parsed/value") -> list[tuple[str, object]]:
    out: list[tuple[str, object]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}/{seg(key)}"
            out.append((path, child))
            out.extend(config_paths(child, path))
    return out


def _text_hint_units(req: Requirement, snap: dict) -> tuple[list[str], list[str]]:
    units: list[str] = []
    hints: list[str] = []
    parsed = (snap.get("parsed") or {}).get("value")
    if isinstance(parsed, dict):
        candidates = {m.group(1) for m in _KEY.finditer(req_text(req))} | set(quoted(req_text(req)))
        matched = [
            (path, value) for path, value in config_paths(parsed)
            if unseg(path.rsplit("/", 1)[-1]) in candidates
        ]
        leaves = [(p, v) for p, v in matched if not isinstance(v, dict)]
        for path, _value in leaves or matched:
            units.append(path)
            hints.append(unseg(path.rsplit("/", 1)[-1]))
    for text in quoted(req_text(req)):
        for i, line in enumerate(snap["lines"]):
            if text.strip() and text.strip() in line:
                units.append(f"lines/{i}")
                hints.append(f'"{text}"')
    return units, hints


def bind(req: Requirement, snap: dict, delta: dict[str, set[str]] | None) -> Binding:
    """Locate the units a requirement's observable reads in the base document."""
    family = snap["family"]
    if family == "xlsx":
        units, hints = _xlsx_hint_units(req, snap)
    elif family == "docx":
        units, hints = _docx_hint_units(req, snap)
    elif family == "pptx":
        units, hints = _pptx_hint_units(req, snap)
    else:
        units, hints = _text_hint_units(req, snap)
    units = list(dict.fromkeys(units))
    delta_set = set(delta or {})
    text = req_text(req)
    if units and _PRESERVE.search(text) and delta_set:
        # A preservation requirement ("keep the original values") reads the units the
        # task must not change: its explicit units minus the task delta.
        kept = [u for u in units if not _touches_delta(u, delta_set)]
        if kept:
            return Binding(req.req_id, tuple(kept), "explicit-delta", "medium", tuple(hints))
    if units:
        if delta_set:
            touched = [
                u for u in units
                if u in delta_set or any(d.startswith(u + "/") for d in delta_set)
            ]
            if touched:
                return Binding(req.req_id, tuple(touched), "explicit+delta", "high", tuple(hints))
        return Binding(req.req_id, tuple(units), "explicit", "medium", tuple(hints))
    if _has_excluded_reference(text):
        # Every reference names cells the requirement excludes; the task delta is
        # not what such a requirement reads, so do not fall back to it.
        return Binding(req.req_id, (), "excluded_only", "none", ())
    kind_units = [u for u, kinds in (delta or {}).items() if _kind_fits(req.check_kind, kinds, u)]
    if kind_units:
        return Binding(req.req_id, tuple(sorted(kind_units)), "delta_kind", "low", ())
    return Binding(req.req_id, (), "none", "none", ())


_PRESERVE = re.compile(
    r"\b(keep|keeps|kept|unchanged|preserv\w*|untouched|remain\w*|stay\w*|"
    r"not (be )?(touched|changed|modified|altered))\b",
    re.IGNORECASE,
)


def _touches_delta(unit: str, delta: set[str]) -> bool:
    return unit in delta or any(d.startswith(unit + "/") for d in delta)


def _has_excluded_reference(text: str) -> bool:
    for pattern in (_CELL_REF, _COLUMN):
        for match in pattern.finditer(text):
            if _excluded(text, match.start()):
                return True
    return False


def _kind_fits(check_kind: str, kinds: set[str], unit: str) -> bool:
    if check_kind in {"cell_value", "config_value"}:
        return "content" in kinds
    if check_kind in {"cell_format", "paragraph_format"}:
        return "format" in kinds
    if check_kind == "text_run":
        return bool(kinds & {"content", "format"})
    if check_kind == "slide_object":
        return bool(kinds & {"layout", "structure", "content", "format"}) and "/shapes/" in unit
    if check_kind == "table_cell":
        return "/cell/" in unit or "/table/" in unit
    return False


def bind_all(
    spec: RequirementSpec, snap: dict, delta: dict[str, set[str]] | None
) -> dict[str, Binding]:
    return {req.req_id: bind(req, snap, delta) for req in spec.requirements}


def bound_units(bindings: dict[str, Binding]) -> set[str]:
    return {u for b in bindings.values() for u in b.units}
