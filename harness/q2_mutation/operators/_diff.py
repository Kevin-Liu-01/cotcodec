"""Alignment-aware structural diff between two canonical snapshots.

Every change carries a locator (slash-separated path in base coordinates), a
kind (content, format, layout, structure, view or meta) and an operation
(changed, added, removed). Ordered collections (Writer body blocks, slides,
shapes, text lines) are aligned with a sequence matcher, so deleting one
paragraph reports one removal instead of shifting every later paragraph.
"""

from __future__ import annotations

import difflib
import json
import math
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, unquote

CONTENT = "content"
FORMAT = "format"
LAYOUT = "layout"
STRUCTURE = "structure"
VIEW = "view"
META = "meta"
KINDS = (CONTENT, FORMAT, LAYOUT, STRUCTURE, VIEW, META)


class DiffError(ValueError):
    """The snapshots cannot be compared."""


@dataclass(frozen=True)
class Change:
    loc: str
    kind: str
    op: str
    before: Any = None
    after: Any = None

    def as_dict(self) -> dict:
        return {
            "loc": self.loc,
            "kind": self.kind,
            "op": self.op,
            "before": self.before,
            "after": self.after,
        }


def seg(value: object) -> str:
    """Escape one locator segment (``/``, glob metacharacters and ``%``)."""
    return quote(str(value), safe=" !$'(),;:=@-._~")


def unseg(value: str) -> str:
    return unquote(value)


def join(*parts: object) -> str:
    return "/".join(seg(p) for p in parts)


def _sig(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def values_equal(a: Any, b: Any) -> bool:
    if isinstance(a, float) and isinstance(b, float):
        if math.isnan(a) and math.isnan(b):
            return True
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(values_equal(x, y) for x, y in zip(a, b, strict=True))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(values_equal(a[k], b[k]) for k in a)
    return a == b


def _span_props(spans: list) -> list:
    return [props for _text, props in spans]


class _Differ:
    def __init__(self) -> None:
        self.changes: list[Change] = []

    def add(self, loc: str, kind: str, op: str, before: Any = None, after: Any = None) -> None:
        self.changes.append(Change(loc, kind, op, before, after))

    def leaf(self, loc: str, kind: str, a: Any, b: Any) -> None:
        if not values_equal(a, b):
            if a is None:
                self.add(loc, kind, "added", None, b)
            elif b is None:
                self.add(loc, kind, "removed", a, None)
            else:
                self.add(loc, kind, "changed", a, b)

    def mapping(self, loc: str, kind: str, a: dict | None, b: dict | None) -> None:
        a = a or {}
        b = b or {}
        for key in sorted(set(a) | set(b), key=str):
            child = f"{loc}/{seg(key)}" if loc else seg(key)
            va, vb = a.get(key), b.get(key)
            if isinstance(va, dict) and isinstance(vb, dict):
                self.mapping(child, kind, va, vb)
            else:
                self.leaf(child, kind, va, vb)

    def sequence(self, loc: str, a: list, b: list, pair, removed_kind: str, coarse=None) -> None:
        """Align two lists; call ``pair(loc_i, x, y)`` for matched-but-different items."""
        sa = [_sig(x) for x in a]
        sb = [_sig(x) for x in b]
        matcher = difflib.SequenceMatcher(None, sa, sb, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            block_a = list(range(i1, i2))
            block_b = list(range(j1, j2))
            pairs: list[tuple[int, int]] = []
            if tag == "replace" and coarse is not None:
                ca = [_sig(coarse(a[i])) for i in block_a]
                cb = [_sig(coarse(b[j])) for j in block_b]
                inner = difflib.SequenceMatcher(None, ca, cb, autojunk=False)
                for itag, k1, k2, l1, l2 in inner.get_opcodes():
                    if itag in {"equal", "replace"}:
                        for offset in range(min(k2 - k1, l2 - l1)):
                            pairs.append((block_a[k1 + offset], block_b[l1 + offset]))
            elif tag == "replace":
                pairs = list(zip(block_a, block_b, strict=False))
            paired_a = {i for i, _ in pairs}
            paired_b = {j for _, j in pairs}
            for i, j in pairs:
                pair(f"{loc}/{i}", a[i], b[j])
            for i in block_a:
                if i not in paired_a:
                    self.add(f"{loc}/{i}", removed_kind, "removed", a[i], None)
            for j in block_b:
                if j not in paired_b:
                    self.add(f"{loc}/+{j}", removed_kind, "added", None, b[j])


# --------------------------------------------------------------------------- xlsx


def _cell_or_default(cells: dict, address: str, default_style: dict) -> dict:
    return cells.get(address) or {"v": None, "f": None, "style": default_style}


def _diff_xlsx(d: _Differ, a: dict, b: dict) -> None:
    d.mapping("meta", META, a.get("meta"), b.get("meta"))
    d.leaf("workbook/defined_names", STRUCTURE, a["workbook"]["defined_names"],
           b["workbook"]["defined_names"])
    d.mapping("book_view", VIEW, a.get("book_view"), b.get("book_view"))
    default_a = a.get("default_style", {})
    default_b = b.get("default_style", {})
    d.mapping("default_style", FORMAT, default_a, default_b)

    names_a = list(a["workbook"]["sheets"])
    names_b = list(b["workbook"]["sheets"])
    sheets_a, sheets_b = a["sheets"], b["sheets"]
    renamed: dict[str, str] = {}
    only_a = [n for n in names_a if n not in sheets_b]
    only_b = [n for n in names_b if n not in sheets_a]
    for name in only_a:
        for other in only_b:
            if other not in renamed.values() and _sig(sheets_a[name]) == _sig(sheets_b[other]):
                renamed[name] = other
                break
    for old, new in renamed.items():
        d.add(join("sheets", old, "name"), STRUCTURE, "changed", old, new)
    order_a = [renamed.get(n, n) for n in names_a]
    if order_a != names_b and sorted(order_a) == sorted(names_b):
        d.add("workbook/sheet_order", STRUCTURE, "changed", order_a, names_b)
    for name in names_a:
        target = renamed.get(name, name)
        if target not in sheets_b:
            d.add(join("sheets", name), STRUCTURE, "removed", "sheet", None)
            continue
        state_a = a["workbook"]["states"].get(name)
        state_b = b["workbook"]["states"].get(target)
        d.leaf(join("sheets", name, "state"), STRUCTURE, state_a, state_b)
        _diff_sheet(d, join("sheets", name), sheets_a[name], sheets_b[target], default_a,
                    default_b)
    for name in names_b:
        if name not in sheets_a and name not in renamed.values():
            d.add(join("sheets", "+" + name), STRUCTURE, "added", None, "sheet")


def _diff_sheet(d: _Differ, loc: str, a: dict, b: dict, default_a: dict, default_b: dict) -> None:
    cells_a, cells_b = a["cells"], b["cells"]
    for address in sorted(set(cells_a) | set(cells_b)):
        ca = _cell_or_default(cells_a, address, default_a)
        cb = _cell_or_default(cells_b, address, default_b)
        cell_loc = f"{loc}/cells/{seg(address)}"
        d.leaf(f"{cell_loc}/v", CONTENT, ca["v"], cb["v"])
        d.leaf(f"{cell_loc}/f", CONTENT, ca["f"], cb["f"])
        d.mapping(f"{cell_loc}/style", FORMAT, ca["style"], cb["style"])
    d.mapping(f"{loc}/rows", LAYOUT, a["rows"], b["rows"])
    d.leaf(f"{loc}/cols", LAYOUT, a["cols"], b["cols"])
    d.leaf(f"{loc}/merges", FORMAT, a["merges"], b["merges"])
    d.leaf(f"{loc}/conditional_formats", FORMAT, a["conditional_formats"],
           b["conditional_formats"])
    d.leaf(f"{loc}/validations", CONTENT, a["validations"], b["validations"])
    d.leaf(f"{loc}/autofilter", CONTENT, a["autofilter"], b["autofilter"])
    view_a = dict(a.get("view") or {})
    view_b = dict(b.get("view") or {})
    pane_a = view_a.pop("pane", None)
    pane_b = view_b.pop("pane", None)
    d.leaf(f"{loc}/view/pane", LAYOUT, pane_a, pane_b)
    d.mapping(f"{loc}/view", VIEW, view_a, view_b)
    d.leaf(f"{loc}/drawings/charts", CONTENT, a["drawings"]["charts"], b["drawings"]["charts"])
    d.leaf(f"{loc}/drawings/images", STRUCTURE, a["drawings"]["images"], b["drawings"]["images"])
    d.leaf(f"{loc}/drawings/shapes", STRUCTURE, a["drawings"]["shapes"], b["drawings"]["shapes"])


# --------------------------------------------------------------------------- docx


def _diff_paragraph(d: _Differ, loc: str, a: dict, b: dict) -> None:
    d.leaf(f"{loc}/text", CONTENT, a.get("text"), b.get("text"))
    d.leaf(f"{loc}/style", FORMAT, a.get("style"), b.get("style"))
    d.mapping(f"{loc}/ppr", FORMAT, a.get("ppr"), b.get("ppr"))
    if _span_props(a.get("spans", [])) != _span_props(b.get("spans", [])) or (
        a.get("text") == b.get("text") and a.get("spans") != b.get("spans")
    ):
        d.add(f"{loc}/spans", FORMAT, "changed", a.get("spans"), b.get("spans"))
    d.leaf(f"{loc}/drawings", STRUCTURE, a.get("drawings"), b.get("drawings"))
    d.leaf(f"{loc}/section_break", LAYOUT, a.get("section_break"), b.get("section_break"))


def _block_coarse(block: dict) -> Any:
    if block.get("type") == "p":
        return ["p", block.get("text")]
    return ["tbl", len(block.get("rows", []))]


def _diff_block(d: _Differ, loc: str, a: dict, b: dict) -> None:
    if a.get("type") != b.get("type"):
        d.add(loc, STRUCTURE, "changed", a.get("type"), b.get("type"))
        return
    if a["type"] == "p":
        _diff_paragraph(d, loc, a, b)
        return
    d.leaf(f"{loc}/style", FORMAT, a.get("style"), b.get("style"))
    rows_a, rows_b = a.get("rows", []), b.get("rows", [])
    if len(rows_a) != len(rows_b) or any(
        len(ra) != len(rb) for ra, rb in zip(rows_a, rows_b, strict=False)
    ):
        d.add(f"{loc}/shape", STRUCTURE, "changed",
              [len(r) for r in rows_a], [len(r) for r in rows_b])
        return
    for r, (row_a, row_b) in enumerate(zip(rows_a, rows_b, strict=True)):
        for c, (cell_a, cell_b) in enumerate(zip(row_a, row_b, strict=True)):
            d.sequence(f"{loc}/cell/{r}/{c}", cell_a, cell_b,
                       lambda lc, x, y: _diff_block(d, lc, x, y), CONTENT, _block_coarse)


def _diff_docx(d: _Differ, a: dict, b: dict) -> None:
    d.mapping("meta", META, a.get("meta"), b.get("meta"))
    d.mapping("settings", VIEW, a.get("settings"), b.get("settings"))
    d.mapping("styles", FORMAT, a.get("styles"), b.get("styles"))
    d.sequence("body", a["body"], b["body"], lambda lc, x, y: _diff_block(d, lc, x, y),
               CONTENT, _block_coarse)
    d.leaf("headers", CONTENT, a.get("headers"), b.get("headers"))
    d.leaf("footers", CONTENT, a.get("footers"), b.get("footers"))
    d.leaf("sections", LAYOUT, a.get("sections"), b.get("sections"))
    d.leaf("notes", CONTENT, a.get("notes"), b.get("notes"))


# --------------------------------------------------------------------------- pptx

_SHAPE_LAYOUT = {"off", "ext", "rot", "flipH", "flipV"}
_SHAPE_FORMAT = {"geom", "fill", "line", "body"}
_SHAPE_META = {"name", "descr"}


def _shape_coarse(shape: dict) -> Any:
    return [shape.get("kind"), shape.get("text"), (shape.get("placeholder") or {}).get("type")]


def _diff_shape(d: _Differ, loc: str, a: dict, b: dict) -> None:
    for key in sorted(set(a) | set(b)):
        va, vb = a.get(key), b.get(key)
        child = f"{loc}/{seg(key)}"
        if key in _SHAPE_LAYOUT:
            d.leaf(child, LAYOUT, va, vb)
        elif key in _SHAPE_FORMAT and isinstance(va, dict) and isinstance(vb, dict):
            d.mapping(child, FORMAT, va, vb)
        elif key in _SHAPE_FORMAT:
            d.leaf(child, FORMAT, va, vb)
        elif key in _SHAPE_META:
            d.leaf(child, META, va, vb)
        elif key in {"kind", "placeholder"}:
            d.leaf(child, STRUCTURE, va, vb)
        elif key == "text" or key == "image_sha256" or key == "chart":
            d.leaf(child, CONTENT, va, vb)
        elif key == "paras":
            if len(va or []) != len(vb or []):
                d.add(child, CONTENT, "changed",
                      [p["text"] for p in va or []], [p["text"] for p in vb or []])
                continue
            for i, (pa, pb) in enumerate(zip(va or [], vb or [], strict=True)):
                d.mapping(f"{child}/{i}/ppr", FORMAT, pa.get("ppr"), pb.get("ppr"))
                if _span_props(pa["spans"]) != _span_props(pb["spans"]) or (
                    pa["text"] == pb["text"] and pa["spans"] != pb["spans"]
                ):
                    d.add(f"{child}/{i}/spans", FORMAT, "changed", pa["spans"], pb["spans"])
        elif key == "table":
            _diff_table(d, child, va or {}, vb or {})
        elif key == "children":
            d.sequence(child, va or [], vb or [], lambda lc, x, y: _diff_shape(d, lc, x, y),
                       STRUCTURE, _shape_coarse)
        else:
            d.leaf(child, STRUCTURE, va, vb)


def _diff_table(d: _Differ, loc: str, a: dict, b: dict) -> None:
    rows_a, rows_b = a.get("rows", []), b.get("rows", [])
    if [len(r) for r in rows_a] != [len(r) for r in rows_b]:
        d.add(f"{loc}/shape", STRUCTURE, "changed",
              [len(r) for r in rows_a], [len(r) for r in rows_b])
        return
    for r, (row_a, row_b) in enumerate(zip(rows_a, rows_b, strict=True)):
        for c, (ca, cb) in enumerate(zip(row_a, row_b, strict=True)):
            cell = f"{loc}/rows/{r}/{c}"
            d.leaf(f"{cell}/text", CONTENT, ca.get("text"), cb.get("text"))
            props_a = [_span_props(s) for s in ca.get("spans", [])]
            props_b = [_span_props(s) for s in cb.get("spans", [])]
            if props_a != props_b or (
                ca.get("text") == cb.get("text") and ca.get("spans") != cb.get("spans")
            ):
                d.add(f"{cell}/spans", FORMAT, "changed", ca.get("spans"), cb.get("spans"))
            d.leaf(f"{cell}/fill", FORMAT, ca.get("fill"), cb.get("fill"))


def _slide_coarse(slide: dict) -> Any:
    return [_shape_coarse(s) for s in slide.get("shapes", [])][:3]


def _diff_slide(d: _Differ, loc: str, a: dict, b: dict) -> None:
    d.leaf(f"{loc}/layout", STRUCTURE, a.get("layout"), b.get("layout"))
    d.leaf(f"{loc}/hidden", STRUCTURE, a.get("hidden"), b.get("hidden"))
    d.leaf(f"{loc}/background", FORMAT, a.get("background"), b.get("background"))
    d.leaf(f"{loc}/notes", CONTENT, a.get("notes"), b.get("notes"))
    d.sequence(f"{loc}/shapes", a.get("shapes", []), b.get("shapes", []),
               lambda lc, x, y: _diff_shape(d, lc, x, y), STRUCTURE, _shape_coarse)


def _diff_pptx(d: _Differ, a: dict, b: dict) -> None:
    d.mapping("meta", META, a.get("meta"), b.get("meta"))
    d.leaf("slide_size", LAYOUT, a.get("slide_size"), b.get("slide_size"))
    d.sequence("slides", a["slides"], b["slides"], lambda lc, x, y: _diff_slide(d, lc, x, y),
               STRUCTURE, _slide_coarse)


# --------------------------------------------------------------------------- text


def _diff_text(d: _Differ, a: dict, b: dict) -> None:
    d.leaf("newline", FORMAT, a.get("newline"), b.get("newline"))
    d.leaf("trailing_newline", FORMAT, a.get("trailing_newline"), b.get("trailing_newline"))
    d.sequence("lines", a["lines"], b["lines"],
               lambda lc, x, y: d.leaf(lc, CONTENT, x, y), CONTENT)
    pa, pb = a.get("parsed"), b.get("parsed")
    if pa is not None or pb is not None:
        pa = pa or {}
        pb = pb or {}
        d.leaf("parsed/ok", CONTENT, pa.get("ok"), pb.get("ok"))
        va, vb = pa.get("value"), pb.get("value")
        if isinstance(va, dict) and isinstance(vb, dict):
            _diff_parsed(d, "parsed/value", va, vb)
        else:
            d.leaf("parsed/value", CONTENT, va, vb)
        if pa.get("ok") and pb.get("ok"):
            order_a = _key_order(pa.get("value"))
            order_b = _key_order(pb.get("value"))
            if order_a != order_b and sorted(order_a) == sorted(order_b):
                d.add("parsed/key_order", FORMAT, "changed", order_a, order_b)


def _key_order(value: Any, prefix: str = "") -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}/{key}"
            keys.append(path)
            keys.extend(_key_order(child, path))
    return keys


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _diff_parsed(d: _Differ, loc: str, a: Any, b: Any) -> None:
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b), key=str):
            child = f"{loc}/{seg(key)}"
            if key not in a:
                d.add(child, CONTENT, "added", None, b[key])
            elif key not in b:
                d.add(child, CONTENT, "removed", a[key], None)
            else:
                _diff_parsed(d, child, a[key], b[key])
        return
    if _is_number(a) and _is_number(b):
        if float(a) != float(b):
            d.add(loc, CONTENT, "changed", a, b)
        elif _sig(a) != _sig(b):
            d.add(loc, FORMAT, "changed", a, b)
        return
    if type(a) is not type(b) or _sig(a) != _sig(b):
        d.add(loc, CONTENT, "changed", a, b)


# --------------------------------------------------------------------------- entry


def diff(base: dict, actual: dict) -> list[Change]:
    """Return every change from ``base`` to ``actual``."""
    family = base.get("family")
    if family != actual.get("family"):
        raise DiffError(f"family mismatch: {family} vs {actual.get('family')}")
    if base.get("snapshot_version") != actual.get("snapshot_version"):
        raise DiffError("snapshot version mismatch")
    d = _Differ()
    if family == "xlsx":
        _diff_xlsx(d, base, actual)
    elif family == "docx":
        _diff_docx(d, base, actual)
    elif family == "pptx":
        _diff_pptx(d, base, actual)
    elif family in {"text", "config"}:
        _diff_text(d, base, actual)
    else:
        raise DiffError(f"unsupported family {family!r}")
    return d.changes


def resolve(snap: dict, loc: str) -> Any:
    """Return the value at ``loc`` in a snapshot (base coordinates, no ``+`` segments)."""
    node: Any = snap
    parts = [unseg(p) for p in loc.split("/")] if loc else []
    for i, part in enumerate(parts):
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict):
            if (
                part not in node
                and i >= 1
                and parts[i - 1] == "cells"
                and snap.get("family") == "xlsx"
            ):
                node = {"v": None, "f": None, "style": snap.get("default_style", {})}
                continue
            if part == "cell" and "rows" in node:
                node = node["rows"]
                continue
            node = node[part]
        else:
            raise KeyError(loc)
    return node
