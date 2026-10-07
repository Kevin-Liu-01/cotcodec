"""Canonical, JSON-able snapshots of office and text documents for purity diffs.

A snapshot records what a user (or a requirement observable) could see or rely
on: cell values and formulas, resolved cell formatting, paragraph and run text
with merged formatting spans, slide shapes and their geometry, table cells,
notes, view state and document metadata. Volatile save bookkeeping (save time,
revision counters, application name, rsids) is excluded so that two saves of
the same document model compare equal.
"""

from __future__ import annotations

import configparser
import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from harness.q2_mutation.operators import _formula as fx
from harness.q2_mutation.operators._ooxml import (
    Package,
    bool_attr,
    element_to_canonical,
    local_name,
    q,
)

# 2: pptx slides record their background, shapes their outline (a:ln) and text-body
# properties (a:bodyPr), which compare_pptx_files and the rendering depend on.
SNAPSHOT_VERSION = 2

OFFICE_FAMILIES = {"xlsx", "docx", "pptx"}
TEXT_SUFFIXES = {
    ".json": "json",
    ".jsonc": "json",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".desktop": "ini",
    ".toml": "text",
    ".yaml": "text",
    ".yml": "text",
}

# Core properties a save rewrites without any user action.
VOLATILE_CORE = {"modified", "revision", "lastModifiedBy", "lastPrinted"}

BUILTIN_NUMFMT = {
    0: "General",
    1: "0",
    2: "0.00",
    3: "#,##0",
    4: "#,##0.00",
    9: "0%",
    10: "0.00%",
    11: "0.00E+00",
    12: "# ?/?",
    13: "# ??/??",
    14: "mm-dd-yy",
    15: "d-mmm-yy",
    16: "d-mmm",
    17: "mmm-yy",
    18: "h:mm AM/PM",
    19: "h:mm:ss AM/PM",
    20: "h:mm",
    21: "h:mm:ss",
    22: "m/d/yy h:mm",
    37: "#,##0 ;(#,##0)",
    38: "#,##0 ;[Red](#,##0)",
    39: "#,##0.00;(#,##0.00)",
    40: "#,##0.00;[Red](#,##0.00)",
    45: "mm:ss",
    46: "[h]:mm:ss",
    47: "mmss.0",
    48: "##0.0E+0",
    49: "@",
}


class SnapshotError(ValueError):
    """The document cannot be snapshotted faithfully."""


def family_of(path: str | Path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in {".xlsx", ".docx", ".pptx"}:
        return suffix[1:]
    if suffix in TEXT_SUFFIXES and TEXT_SUFFIXES[suffix] != "text":
        return "config"
    return "text"


def snapshot(path: str | Path, family: str | None = None) -> dict:
    """Return the canonical snapshot of ``path``."""
    family = family or family_of(path)
    if family == "xlsx":
        body = _xlsx(Package(path))
    elif family == "docx":
        body = _docx(Package(path))
    elif family == "pptx":
        body = _pptx(Package(path))
    elif family in {"text", "config"}:
        body = _text(Path(path), family)
    else:
        raise SnapshotError(f"unsupported family {family!r}")
    return {"snapshot_version": SNAPSHOT_VERSION, "family": family, **body}


# --------------------------------------------------------------------------- common


def _color(element: ET.Element | None) -> str | None:
    if element is None:
        return None
    if element.get("rgb"):
        return "rgb:" + element.get("rgb", "").upper()[-6:]
    if element.get("theme") is not None:
        tint = element.get("tint")
        return f"theme:{element.get('theme')}" + (f":{float(tint):.4f}" if tint else "")
    if element.get("indexed") is not None:
        return f"indexed:{element.get('indexed')}"
    if bool_attr(element.get("auto"), default=False):
        return "auto"
    return None


def _core_meta(pkg: Package) -> dict:
    root = pkg.xml("docProps/core.xml")
    meta: dict[str, str] = {}
    if root is None:
        return meta
    for child in root:
        name = local_name(child.tag)
        if name in VOLATILE_CORE:
            continue
        text = "".join(child.itertext()).strip()
        if text:
            meta[name] = text
    custom = pkg.xml("docProps/custom.xml")
    if custom is not None:
        for prop in custom:
            value = "".join(prop.itertext()).strip()
            meta[f"custom:{prop.get('name')}"] = value
    return meta


# --------------------------------------------------------------------------- xlsx


def _xlsx(pkg: Package) -> dict:
    wb_part = pkg.main_part()
    wb = pkg.xml(wb_part)
    if wb is None:
        raise SnapshotError("workbook part missing")
    rels = pkg.rels(wb_part)
    shared = _shared_strings(pkg, rels)
    styles = _XlsxStyles(pkg, rels)

    sheets_el = wb.find(q("main", "sheets"))
    sheet_entries = [] if sheets_el is None else list(sheets_el)
    names = [s.get("name", "") for s in sheet_entries]
    view = wb.find(f"{q('main', 'bookViews')}/{q('main', 'workbookView')}")
    workbook = {
        "sheets": names,
        "states": {s.get("name", ""): s.get("state", "visible") for s in sheet_entries},
        "defined_names": sorted(
            f"{d.get('name')}|{d.get('localSheetId', '')}|{(d.text or '').strip()}"
            for d in wb.iter(q("main", "definedName"))
            if not (d.get("name") or "").startswith("_xlnm._FilterDatabase")
        ),
    }
    book_view = {"active_tab": int(view.get("activeTab", "0")) if view is not None else 0}

    sheets: dict[str, dict] = {}
    for entry in sheet_entries:
        rid = entry.get(q("r", "id"), "")
        if rid not in rels:
            raise SnapshotError(f"sheet {entry.get('name')!r} has no part")
        part = rels[rid][1]
        sheets[entry.get("name", "")] = _xlsx_sheet(
            pkg, part, entry.get("name", ""), shared, styles
        )
    return {
        "meta": _core_meta(pkg),
        "workbook": workbook,
        "book_view": book_view,
        "default_style": styles.resolve(0),
        "sheets": sheets,
    }


def _shared_strings(pkg: Package, rels: dict) -> list[str]:
    for _rid, (rtype, target, _mode) in rels.items():
        if rtype.endswith("/sharedStrings"):
            root = pkg.xml(target)
            if root is None:
                return []
            return [_si_text(si) for si in root.findall(q("main", "si"))]
    return []


def _si_text(si: ET.Element) -> str:
    parts = []
    for node in si.iter():
        name = local_name(node.tag)
        if name == "t" and _parent_is_not_phonetic(si, node):
            parts.append(node.text or "")
    return "".join(parts)


def _parent_is_not_phonetic(root: ET.Element, target: ET.Element) -> bool:
    for rph in root.iter(q("main", "rPh")):
        if any(node is target for node in rph.iter()):
            return False
    return True


class _XlsxStyles:
    def __init__(self, pkg: Package, rels: dict) -> None:
        self.numfmts = dict(BUILTIN_NUMFMT)
        self.fonts: list[dict] = []
        self.fills: list[dict] = []
        self.borders: list[dict] = []
        self.xfs: list[ET.Element] = []
        self.style_names: dict[int, str] = {}
        self.dxfs: list[dict] = []
        root = None
        for _rid, (rtype, target, _mode) in rels.items():
            if rtype.endswith("/styles"):
                root = pkg.xml(target)
        if root is None:
            return
        for fmt in root.iter(q("main", "numFmt")):
            self.numfmts[int(fmt.get("numFmtId", "0"))] = fmt.get("formatCode", "")
        fonts = root.find(q("main", "fonts"))
        self.fonts = [self._font(f) for f in (fonts if fonts is not None else [])]
        fills = root.find(q("main", "fills"))
        self.fills = [self._fill(f) for f in (fills if fills is not None else [])]
        borders = root.find(q("main", "borders"))
        self.borders = [self._border(b) for b in (borders if borders is not None else [])]
        xfs = root.find(q("main", "cellXfs"))
        self.xfs = list(xfs) if xfs is not None else []
        cell_styles = root.find(q("main", "cellStyles"))
        for cs in cell_styles if cell_styles is not None else []:
            self.style_names[int(cs.get("xfId", "0"))] = cs.get("name", "")
        dxfs = root.find(q("main", "dxfs"))
        self.dxfs = [element_to_canonical(d) for d in (dxfs if dxfs is not None else [])]

    @staticmethod
    def _font(font: ET.Element) -> dict:
        out: dict = {}
        for child in font:
            name = local_name(child.tag)
            if name in {"b", "i", "strike", "outline", "shadow"}:
                out[name] = bool_attr(child.get("val"))
            elif name == "u":
                out["u"] = child.get("val", "single")
            elif name == "sz":
                out["sz"] = float(child.get("val", "0"))
            elif name == "color":
                out["color"] = _color(child)
            elif name == "name":
                out["name"] = child.get("val")
            elif name == "vertAlign":
                out["vertAlign"] = child.get("val")
        for flag in ("b", "i", "strike"):
            out.setdefault(flag, False)
        return out

    @staticmethod
    def _fill(fill: ET.Element) -> dict:
        pattern = fill.find(q("main", "patternFill"))
        if pattern is not None:
            kind = pattern.get("patternType", "none")
            if kind == "none":
                return {"pattern": "none"}
            return {
                "pattern": kind,
                "fg": _color(pattern.find(q("main", "fgColor"))),
                "bg": _color(pattern.find(q("main", "bgColor"))) if kind != "solid" else None,
            }
        gradient = fill.find(q("main", "gradientFill"))
        if gradient is not None:
            return {"pattern": "gradient", "xml": element_to_canonical(gradient)}
        return {"pattern": "none"}

    @staticmethod
    def _border(border: ET.Element) -> dict:
        out = {}
        for child in border:
            name = local_name(child.tag)
            style = child.get("style")
            if style:
                out[name] = [style, _color(child.find(q("main", "color")))]
        return out

    def resolve(self, index: int) -> dict:
        if not self.xfs:
            return {"numfmt": "General"}
        if index >= len(self.xfs):
            raise SnapshotError(f"cell style index {index} is out of range")
        xf = self.xfs[index]
        numfmt_id = int(xf.get("numFmtId", "0"))
        font_id = int(xf.get("fontId", "0"))
        fill_id = int(xf.get("fillId", "0"))
        border_id = int(xf.get("borderId", "0"))
        align_el = xf.find(q("main", "alignment"))
        protection = xf.find(q("main", "protection"))
        style = {
            "numfmt": self.numfmts.get(numfmt_id, f"#{numfmt_id}"),
            "font": self.fonts[font_id] if font_id < len(self.fonts) else {},
            "fill": self.fills[fill_id] if fill_id < len(self.fills) else {"pattern": "none"},
            "border": self.borders[border_id] if border_id < len(self.borders) else {},
            "align": {
                local_name(k): v
                for k, v in sorted((align_el.attrib if align_el is not None else {}).items())
            },
            "protection": {
                local_name(k): v
                for k, v in sorted((protection.attrib if protection is not None else {}).items())
            },
            "style_name": self.style_names.get(int(xf.get("xfId", "0")), ""),
        }
        return style


_FORMULA_CACHE_TYPES = {"s", "str", "inlineStr"}


def _cell_value(cell: ET.Element, shared: list[str]) -> list | None:
    kind = cell.get("t", "n")
    v = cell.find(q("main", "v"))
    if kind == "inlineStr":
        inline = cell.find(q("main", "is"))
        return ["s", _si_text(inline)] if inline is not None else None
    if v is None or v.text is None:
        return None
    text = v.text
    if kind == "s":
        index = int(text)
        if index >= len(shared):
            raise SnapshotError(f"shared string {index} is out of range")
        return ["s", shared[index]]
    if kind == "str":
        return ["s", text]
    if kind == "b":
        return ["b", text.strip() in {"1", "true", "TRUE"}]
    if kind == "e":
        return ["e", text]
    try:
        return ["n", float(text)]
    except ValueError as exc:
        raise SnapshotError(f"numeric cell holds {text!r}") from exc


def _xlsx_sheet(
    pkg: Package, part: str, sheet_name: str, shared: list[str], styles: _XlsxStyles
) -> dict:
    root = pkg.xml(part)
    if root is None:
        raise SnapshotError(f"sheet part {part} missing")
    cells: dict[str, dict] = {}
    rows: dict[str, dict] = {}
    shared_masters: dict[str, tuple[str, int, int]] = {}
    sheet_data = root.find(q("main", "sheetData"))
    for row in sheet_data if sheet_data is not None else []:
        row_attrs = {
            key: row.get(key)
            for key in ("ht", "customHeight", "hidden", "outlineLevel", "collapsed")
            if row.get(key) is not None
        }
        if row_attrs:
            rows[row.get("r", "")] = row_attrs
        for cell in row.findall(q("main", "c")):
            address = cell.get("r", "")
            formula = _cell_formula(cell, address, shared_masters)
            value = _cell_value(cell, shared)
            style = styles.resolve(int(cell.get("s", "0")))
            cells[address] = {"v": value, "f": formula, "style": style}

    cols = []
    cols_el = root.find(q("main", "cols"))
    for col in cols_el if cols_el is not None else []:
        cols.append(
            {
                key: col.get(key)
                for key in ("min", "max", "width", "customWidth", "hidden", "outlineLevel")
                if col.get(key) is not None
            }
        )
    merges = sorted(m.get("ref", "") for m in root.iter(q("main", "mergeCell")))
    conditional = []
    for cf in root.findall(q("main", "conditionalFormatting")):
        node = element_to_canonical(cf)
        for rule in node.get("children", []):
            dxf_id = rule.get("attrs", {}).pop("dxfId", None)
            if dxf_id is not None and int(dxf_id) < len(styles.dxfs):
                rule["dxf"] = styles.dxfs[int(dxf_id)]
            rule.get("attrs", {}).pop("priority", None)
        conditional.append(node)
    validations = [
        element_to_canonical(dv) for dv in root.iter(q("main", "dataValidation"))
    ]
    autofilter = root.find(q("main", "autoFilter"))
    return {
        "cells": cells,
        "rows": rows,
        "cols": cols,
        "merges": merges,
        "conditional_formats": conditional,
        "validations": validations,
        "autofilter": element_to_canonical(autofilter) if autofilter is not None else None,
        "view": _sheet_view(root),
        "drawings": _xlsx_drawings(pkg, part),
    }


def _cell_formula(
    cell: ET.Element, address: str, masters: dict[str, tuple[str, int, int]]
) -> str | None:
    f = cell.find(q("main", "f"))
    if f is None:
        return None
    text = (f.text or "").strip()
    if f.get("t") == "shared":
        si = f.get("si", "")
        row, col = fx.split_address(address)
        if text:
            masters[si] = (text, row, col)
        elif si in masters:
            master, mrow, mcol = masters[si]
            try:
                text = fx.shift_formula(master, row - mrow, col - mcol)[1:]
            except fx.FormulaError as exc:
                raise SnapshotError(f"cannot expand shared formula at {address}") from exc
        else:
            raise SnapshotError(f"shared formula {si} at {address} has no master")
    if f.get("t") == "array":
        return "{=" + text + "}"
    return "=" + text if text else None


def _sheet_view(root: ET.Element) -> dict:
    view_el = root.find(f"{q('main', 'sheetViews')}/{q('main', 'sheetView')}")
    if view_el is None:
        return {}
    view = {
        "tab_selected": bool_attr(view_el.get("tabSelected"), default=False),
        "zoom": int(view_el.get("zoomScale", "100")),
        "show_grid": bool_attr(view_el.get("showGridLines"), default=True),
        "top_left": view_el.get("topLeftCell", "A1"),
    }
    pane = view_el.find(q("main", "pane"))
    if pane is not None:
        view["pane"] = {
            key: pane.get(key)
            for key in ("xSplit", "ySplit", "topLeftCell", "state")
            if pane.get(key) is not None
        }
    selections = view_el.findall(q("main", "selection"))
    if selections:
        chosen = selections[-1]
        if pane is not None:
            active = pane.get("activePane")
            for selection in selections:
                if selection.get("pane") == active:
                    chosen = selection
        view["active_cell"] = chosen.get("activeCell", "A1")
        view["selection"] = chosen.get("sqref", chosen.get("activeCell", "A1"))
    return view


def _xlsx_drawings(pkg: Package, sheet_part: str) -> dict:
    charts = []
    images = 0
    shapes = 0
    for _rid, (rtype, target, _mode) in pkg.rels(sheet_part).items():
        if not rtype.endswith("/drawing"):
            continue
        drawing = pkg.xml(target)
        if drawing is None:
            continue
        drawing_rels = pkg.rels(target)
        for chart in drawing.iter(q("c", "chart")):
            rid = chart.get(q("r", "id"), "")
            if rid in drawing_rels:
                charts.append(chart_summary(pkg, drawing_rels[rid][1]))
        images += sum(1 for _ in drawing.iter(q("xdr", "pic")))
        shapes += sum(1 for _ in drawing.iter(q("xdr", "sp")))
    return {"charts": charts, "images": images, "shapes": shapes}


def chart_summary(pkg: Package, chart_part: str) -> dict:
    root = pkg.xml(chart_part)
    if root is None:
        return {"missing": chart_part}
    plot = root.find(f".//{q('c', 'plotArea')}")
    types = []
    series = []
    for child in plot if plot is not None else []:
        name = local_name(child.tag)
        if not name.endswith("Chart"):
            continue
        bar_dir = child.find(q("c", "barDir"))
        grouping = child.find(q("c", "grouping"))
        types.append(
            {
                "type": name,
                "bar_dir": bar_dir.get("val") if bar_dir is not None else None,
                "grouping": grouping.get("val") if grouping is not None else None,
            }
        )
        for ser in child.findall(q("c", "ser")):
            entry = {}
            for key in ("tx", "cat", "val", "xVal", "yVal"):
                node = ser.find(q("c", key))
                if node is not None:
                    f = node.find(f".//{q('c', 'f')}")
                    entry[key] = (f.text or "").strip() if f is not None else None
            series.append(entry)
    title = root.find(f".//{q('c', 'title')}")
    title_text = (
        "".join(t.text or "" for t in title.iter(q("a", "t"))) if title is not None else None
    )
    return {"types": types, "series": series, "title": title_text}


# --------------------------------------------------------------------------- docx

_RPR_SKIP = {"lang", "noProof", "rsid", "rPrChange", "webHidden", "specVanish"}
_PPR_SKIP = {"rPr", "sectPr", "pPrChange", "rsid"}


def _docx(pkg: Package) -> dict:
    main = pkg.main_part()
    root = pkg.xml(main)
    if root is None:
        raise SnapshotError("document part missing")
    rels = pkg.rels(main)
    style_names = _docx_style_names(pkg, rels)
    body = root.find(q("w", "body"))
    blocks = _docx_blocks(body, style_names) if body is not None else []
    headers = []
    footers = []
    for _rid, (rtype, target, _mode) in sorted(rels.items(), key=lambda kv: kv[1][1]):
        if rtype.endswith("/header") or rtype.endswith("/footer"):
            part = pkg.xml(target)
            if part is None:
                continue
            text = _docx_blocks(part, style_names)
            (headers if rtype.endswith("/header") else footers).append(
                [b.get("text", "") for b in text if b["type"] == "p"]
            )
    sections = []
    if body is not None:
        for sect in body.iter(q("w", "sectPr")):
            node = element_to_canonical(sect)
            node["children"] = [
                c
                for c in node.get("children", [])
                if c["tag"] not in {"headerReference", "footerReference"}
            ]
            sections.append(node)
    settings = {}
    for _rid, (rtype, target, _mode) in rels.items():
        if rtype.endswith("/settings"):
            settings_root = pkg.xml(target)
            zoom = settings_root.find(q("w", "zoom")) if settings_root is not None else None
            if zoom is not None:
                settings["zoom"] = zoom.get(q("w", "percent"))
    notes = []
    for _rid, (rtype, target, _mode) in rels.items():
        if rtype.endswith("/footnotes") or rtype.endswith("/endnotes"):
            part = pkg.xml(target)
            for note in part if part is not None else []:
                if note.get(q("w", "type")) in {"separator", "continuationSeparator"}:
                    continue
                notes.append("".join(_docx_paragraph_text(p) for p in note.iter(q("w", "p"))))
        if rtype.endswith("/comments"):
            part = pkg.xml(target)
            for comment in part if part is not None else []:
                notes.append(
                    "comment:" + "".join(_docx_paragraph_text(p) for p in comment.iter(q("w", "p")))
                )
    return {
        "meta": _core_meta(pkg),
        "settings": settings,
        "styles": _docx_styles(pkg, rels, style_names),
        "body": blocks,
        "headers": headers,
        "footers": footers,
        "sections": sections,
        "notes": notes,
    }


def _docx_styles(pkg: Package, rels: dict, style_names: dict[str, str]) -> dict:
    """Paragraph and character styles with their own (unresolved) properties."""
    out: dict = {"defaults": {"rpr": {}, "ppr": {}}, "para": {}, "char": {}}
    for _rid, (rtype, target, _mode) in rels.items():
        if not rtype.endswith("/styles"):
            continue
        root = pkg.xml(target)
        if root is None:
            continue
        defaults = root.find(q("w", "docDefaults"))
        if defaults is not None:
            rpr = defaults.find(f"{q('w', 'rPrDefault')}/{q('w', 'rPr')}")
            ppr = defaults.find(f"{q('w', 'pPrDefault')}/{q('w', 'pPr')}")
            out["defaults"]["rpr"] = _docx_rpr(rpr, style_names)
            out["defaults"]["ppr"] = _docx_ppr(ppr)
        for style in root.findall(q("w", "style")):
            kind = style.get(q("w", "type"))
            if kind not in {"paragraph", "character"}:
                continue
            style_id = style.get(q("w", "styleId"), "")
            name = style_names.get(style_id, style_id)
            based = style.find(q("w", "basedOn"))
            entry = {
                "based_on": style_names.get(based.get(q("w", "val"), ""), "")
                if based is not None
                else "",
                "rpr": _docx_rpr(style.find(q("w", "rPr")), style_names),
                "default": bool_attr(style.get(q("w", "default")), default=False),
            }
            if kind == "paragraph":
                entry["ppr"] = _docx_ppr(style.find(q("w", "pPr")))
                out["para"][name] = entry
            else:
                out["char"][name] = entry
    return out


def _docx_ppr(ppr: ET.Element | None) -> dict:
    props: dict = {}
    if ppr is None:
        return props
    for child in ppr:
        name = local_name(child.tag)
        if name in _PPR_SKIP or name == "pStyle":
            continue
        node = element_to_canonical(child)
        node.pop("tag", None)
        props[name] = node or True
    return props


def _docx_style_names(pkg: Package, rels: dict) -> dict[str, str]:
    names: dict[str, str] = {}
    for _rid, (rtype, target, _mode) in rels.items():
        if rtype.endswith("/styles"):
            root = pkg.xml(target)
            for style in root.findall(q("w", "style")) if root is not None else []:
                name_el = style.find(q("w", "name"))
                names[style.get(q("w", "styleId"), "")] = (
                    name_el.get(q("w", "val"), "") if name_el is not None else ""
                )
    return names


def _docx_blocks(container: ET.Element, style_names: dict[str, str]) -> list[dict]:
    blocks: list[dict] = []
    for child in container:
        name = local_name(child.tag)
        if name == "p":
            blocks.append(_docx_paragraph(child, style_names))
        elif name == "tbl":
            blocks.append(_docx_table(child, style_names))
        elif name == "sdt":
            content = child.find(q("w", "sdtContent"))
            if content is not None:
                blocks.extend(_docx_blocks(content, style_names))
        elif name in {"customXml", "ins", "moveTo"}:
            blocks.extend(_docx_blocks(child, style_names))
    return blocks


def _toggle(child: ET.Element) -> bool:
    return bool_attr(child.get(q("w", "val")))


def _docx_rpr(rpr: ET.Element | None, style_names: dict[str, str]) -> dict:
    props: dict = {}
    if rpr is None:
        return props
    for child in rpr:
        name = local_name(child.tag)
        if name in _RPR_SKIP:
            continue
        if name in {"b", "bCs", "i", "iCs", "strike", "dstrike", "caps", "smallCaps", "vanish",
                    "outline", "shadow", "emboss", "imprint"}:
            props[name] = _toggle(child)
        elif name == "rStyle":
            style_id = child.get(q("w", "val"), "")
            props["rStyle"] = style_names.get(style_id, style_id)
        else:
            attrs = {local_name(k): v for k, v in sorted(child.attrib.items())}
            props[name] = attrs.get("val", attrs) if len(attrs) == 1 else attrs
    return props


def _docx_paragraph_text(p: ET.Element) -> str:
    parts = []
    for node in p.iter():
        name = local_name(node.tag)
        if name == "t":
            parts.append(node.text or "")
        elif name == "tab":
            parts.append("\t")
        elif name in {"br", "cr"}:
            parts.append("\n")
        elif name == "noBreakHyphen":
            parts.append("-")
    return "".join(parts)


def _docx_runs(p: ET.Element) -> list[ET.Element]:
    """Runs in reading order, including runs inside hyperlinks, fields and insertions."""
    runs: list[ET.Element] = []

    def walk(node: ET.Element) -> None:
        for child in node:
            name = local_name(child.tag)
            if name == "r":
                runs.append(child)
            elif name in {"hyperlink", "ins", "smartTag", "fldSimple", "moveTo", "customXml"}:
                walk(child)
            elif name == "sdt":
                content = child.find(q("w", "sdtContent"))
                if content is not None:
                    walk(content)

    walk(p)
    return runs


def _run_text(run: ET.Element) -> str:
    parts = []
    for child in run:
        name = local_name(child.tag)
        if name == "t":
            parts.append(child.text or "")
        elif name == "tab":
            parts.append("\t")
        elif name in {"br", "cr"}:
            parts.append("\n")
        elif name == "noBreakHyphen":
            parts.append("-")
    return "".join(parts)


def merge_spans(pieces: list[tuple[str, dict]]) -> list[list]:
    """Merge adjacent text pieces with equal properties; drop empty pieces."""
    spans: list[list] = []
    for text, props in pieces:
        if not text:
            continue
        if spans and spans[-1][1] == props:
            spans[-1][0] += text
        else:
            spans.append([text, props])
    return spans


def _docx_paragraph(p: ET.Element, style_names: dict[str, str]) -> dict:
    ppr = p.find(q("w", "pPr"))
    style = ""
    ppr_props = _docx_ppr(ppr)
    style_el = ppr.find(q("w", "pStyle")) if ppr is not None else None
    if style_el is not None:
        style_id = style_el.get(q("w", "val"), "")
        style = style_names.get(style_id, style_id)
    pieces = [(_run_text(r), _docx_rpr(r.find(q("w", "rPr")), style_names)) for r in _docx_runs(p)]
    drawings = sum(1 for _ in p.iter(q("w", "drawing"))) + sum(1 for _ in p.iter(q("w", "pict")))
    section_break = ppr is not None and ppr.find(q("w", "sectPr")) is not None
    block = {
        "type": "p",
        "text": "".join(text for text, _ in pieces),
        "style": style,
        "ppr": ppr_props,
        "spans": merge_spans(pieces),
    }
    if drawings:
        block["drawings"] = drawings
    if section_break:
        block["section_break"] = True
    return block


def _docx_table(tbl: ET.Element, style_names: dict[str, str]) -> dict:
    rows = []
    merged = False
    for tr in tbl.findall(q("w", "tr")):
        row = []
        for tc in tr.findall(q("w", "tc")):
            tcpr = tc.find(q("w", "tcPr"))
            if tcpr is not None and (
                tcpr.find(q("w", "gridSpan")) is not None or tcpr.find(q("w", "vMerge")) is not None
            ):
                merged = True
            row.append(_docx_blocks(tc, style_names))
        rows.append(row)
    tblpr = tbl.find(q("w", "tblPr"))
    style = tblpr.find(q("w", "tblStyle")) if tblpr is not None else None
    return {
        "type": "tbl",
        "rows": rows,
        "merged": merged,
        "style": style.get(q("w", "val")) if style is not None else "",
    }


# --------------------------------------------------------------------------- pptx

_A_RPR_ATTRS = ("b", "i", "u", "strike", "sz", "baseline", "cap", "spc")


def _pptx(pkg: Package) -> dict:
    main = pkg.main_part()
    root = pkg.xml(main)
    if root is None:
        raise SnapshotError("presentation part missing")
    rels = pkg.rels(main)
    slides = []
    id_list = root.find(q("p", "sldIdLst"))
    for sld in id_list if id_list is not None else []:
        rid = sld.get(q("r", "id"), "")
        if rid not in rels:
            raise SnapshotError("slide relationship missing")
        slides.append(_pptx_slide(pkg, rels[rid][1]))
    size = root.find(q("p", "sldSz"))
    return {
        "meta": _core_meta(pkg),
        "slide_size": [size.get("cx"), size.get("cy")] if size is not None else None,
        "slides": slides,
    }


def _pptx_slide(pkg: Package, part: str) -> dict:
    root = pkg.xml(part)
    if root is None:
        raise SnapshotError(f"slide part {part} missing")
    rels = pkg.rels(part)
    layout = ""
    notes = ""
    for _rid, (rtype, target, _mode) in rels.items():
        if rtype.endswith("/slideLayout"):
            layout_root = pkg.xml(target)
            csld = layout_root.find(q("p", "cSld")) if layout_root is not None else None
            layout = csld.get("name", "") if csld is not None else ""
        elif rtype.endswith("/notesSlide"):
            notes = _pptx_notes(pkg, target)
    tree = root.find(f"{q('p', 'cSld')}/{q('p', 'spTree')}")
    shapes = _pptx_shapes(pkg, tree, rels) if tree is not None else []
    hidden = bool_attr(root.get("show"), default=True) is False
    background = root.find(f"{q('p', 'cSld')}/{q('p', 'bg')}")
    return {
        "layout": layout,
        "hidden": hidden,
        "background": element_to_canonical(background) if background is not None else None,
        "shapes": shapes,
        "notes": notes,
    }


def _pptx_notes(pkg: Package, part: str) -> str:
    root = pkg.xml(part)
    if root is None:
        return ""
    texts = []
    for sp in root.iter(q("p", "sp")):
        ph = sp.find(f".//{q('p', 'ph')}")
        if ph is not None and ph.get("type") == "body":
            body = sp.find(q("p", "txBody"))
            if body is not None:
                texts.append("\n".join(_a_paragraph_text(p) for p in body.findall(q("a", "p"))))
    return "\n".join(texts)


def _xfrm(node: ET.Element | None) -> dict:
    if node is None:
        return {}
    off = node.find(q("a", "off"))
    ext = node.find(q("a", "ext"))
    out: dict = {}
    if off is not None:
        out["off"] = [int(off.get("x", "0")), int(off.get("y", "0"))]
    if ext is not None:
        out["ext"] = [int(ext.get("cx", "0")), int(ext.get("cy", "0"))]
    for key in ("rot", "flipH", "flipV"):
        if node.get(key) is not None:
            out[key] = node.get(key)
    return out


def _pptx_shapes(pkg: Package, tree: ET.Element, rels: dict) -> list[dict]:
    shapes = []
    for child in tree:
        name = local_name(child.tag)
        if name not in {"sp", "pic", "graphicFrame", "grpSp", "cxnSp"}:
            continue
        nv = next((c for c in child if local_name(c.tag).startswith("nv")), None)
        cnv = nv.find(q("p", "cNvPr")) if nv is not None else None
        ph = nv.find(f".//{q('p', 'ph')}") if nv is not None else None
        shape: dict = {
            "kind": name,
            "name": cnv.get("name", "") if cnv is not None else "",
            "descr": cnv.get("descr", "") if cnv is not None else "",
            "placeholder": (
                {"type": ph.get("type", "obj"), "idx": ph.get("idx")} if ph is not None else None
            ),
        }
        if name == "graphicFrame":
            shape.update(_xfrm(child.find(q("p", "xfrm"))))
            data = child.find(f"{q('a', 'graphic')}/{q('a', 'graphicData')}")
            tbl = data.find(q("a", "tbl")) if data is not None else None
            chart = data.find(q("c", "chart")) if data is not None else None
            if tbl is not None:
                shape["kind"] = "table"
                shape["table"] = _a_table(tbl)
            elif chart is not None:
                shape["kind"] = "chart"
                rid = chart.get(q("r", "id"), "")
                shape["chart"] = chart_summary(pkg, rels[rid][1]) if rid in rels else None
        elif name == "grpSp":
            grp_pr = child.find(q("p", "grpSpPr"))
            shape.update(_xfrm(grp_pr.find(q("a", "xfrm")) if grp_pr is not None else None))
            shape["children"] = _pptx_shapes(pkg, child, rels)
        else:
            sp_pr = child.find(q("p", "spPr"))
            shape.update(_xfrm(sp_pr.find(q("a", "xfrm")) if sp_pr is not None else None))
            if sp_pr is not None:
                geom = sp_pr.find(q("a", "prstGeom"))
                if geom is not None:
                    shape["geom"] = geom.get("prst")
                fill = sp_pr.find(q("a", "solidFill"))
                if fill is not None:
                    shape["fill"] = _a_color(fill)
                line = sp_pr.find(q("a", "ln"))
                if line is not None:
                    shape["line"] = element_to_canonical(line)
            if name == "pic":
                blip = child.find(f".//{q('a', 'blip')}")
                if blip is not None:
                    rid = blip.get(q("r", "embed"), "")
                    target = rels.get(rid, ("", "", ""))[1]
                    data = pkg.parts.get(target, b"")
                    shape["image_sha256"] = hashlib.sha256(data).hexdigest() if data else None
        body = child.find(q("p", "txBody"))
        if body is not None:
            body_pr = _a_body_pr(body.find(q("a", "bodyPr")))
            if body_pr:
                shape["body"] = body_pr
            shape["paras"] = [_a_paragraph(p) for p in body.findall(q("a", "p"))]
            shape["text"] = "\n".join(p["text"] for p in shape["paras"])
        shapes.append(shape)
    return shapes


def _a_body_pr(body_pr: ET.Element | None) -> dict:
    """Text-body properties: wrap, anchoring, insets, rotation, columns, autofit mode.

    Only the autofit mode is kept, not its result (``fontScale``,
    ``lnSpcReduction``), which LibreOffice recomputes whenever the text changes.
    """
    if body_pr is None:
        return {}
    props: dict = {local_name(k): v for k, v in sorted(body_pr.attrib.items())}
    for child in body_pr:
        name = local_name(child.tag)
        if name in {"normAutofit", "spAutoFit", "noAutofit"}:
            props["autofit"] = name
            continue
        node = element_to_canonical(child)
        node.pop("tag", None)
        props[name] = node or True
    return props


def _a_color(node: ET.Element | None) -> str | None:
    if node is None:
        return None
    for child in node:
        name = local_name(child.tag)
        if name == "srgbClr":
            mods = "".join(
                f";{local_name(m.tag)}={m.get('val')}" for m in child
            )
            return "rgb:" + child.get("val", "").upper() + mods
        if name == "schemeClr":
            mods = "".join(f";{local_name(m.tag)}={m.get('val')}" for m in child)
            return "scheme:" + child.get("val", "") + mods
        if name == "prstClr":
            return "preset:" + child.get("val", "")
        if name == "sysClr":
            return "sys:" + child.get("lastClr", child.get("val", ""))
    return None


def _a_rpr(rpr: ET.Element | None) -> dict:
    if rpr is None:
        return {}
    props: dict = {}
    for key in _A_RPR_ATTRS:
        if rpr.get(key) is not None:
            props[key] = rpr.get(key)
    for flag in ("b", "i"):
        if flag in props:
            props[flag] = bool_attr(props[flag])
    fill = rpr.find(q("a", "solidFill"))
    if fill is not None:
        props["color"] = _a_color(fill)
    latin = rpr.find(q("a", "latin"))
    if latin is not None:
        props["latin"] = latin.get("typeface")
    highlight = rpr.find(q("a", "highlight"))
    if highlight is not None:
        props["highlight"] = _a_color(highlight)
    return props


def _a_paragraph_text(p: ET.Element) -> str:
    parts = []
    for child in p:
        name = local_name(child.tag)
        if name in {"r", "fld"}:
            t = child.find(q("a", "t"))
            parts.append(t.text or "" if t is not None else "")
        elif name == "br":
            parts.append("\n")
    return "".join(parts)


def _a_paragraph(p: ET.Element) -> dict:
    ppr = p.find(q("a", "pPr"))
    ppr_props = {}
    if ppr is not None:
        ppr_props = {local_name(k): v for k, v in sorted(ppr.attrib.items())}
        for child in ppr:
            name = local_name(child.tag)
            if name == "defRPr":
                continue
            node = element_to_canonical(child)
            node.pop("tag", None)
            ppr_props[name] = node or True
    pieces = []
    for child in p:
        name = local_name(child.tag)
        if name in {"r", "fld"}:
            t = child.find(q("a", "t"))
            text = (t.text or "") if t is not None else ""
            pieces.append((text, _a_rpr(child.find(q("a", "rPr")))))
        elif name == "br":
            pieces.append(("\n", _a_rpr(child.find(q("a", "rPr")))))
    return {
        "text": "".join(text for text, _ in pieces),
        "ppr": ppr_props,
        "spans": merge_spans(pieces),
    }


def _a_table(tbl: ET.Element) -> dict:
    rows = []
    merged = False
    for tr in tbl.findall(q("a", "tr")):
        row = []
        for tc in tr.findall(q("a", "tc")):
            if any(tc.get(k) for k in ("gridSpan", "rowSpan", "hMerge", "vMerge")):
                merged = True
            body = tc.find(q("a", "txBody"))
            paras = [_a_paragraph(p) for p in body.findall(q("a", "p"))] if body is not None else []
            tcpr = tc.find(q("a", "tcPr"))
            fill = tcpr.find(q("a", "solidFill")) if tcpr is not None else None
            row.append(
                {
                    "text": "\n".join(p["text"] for p in paras),
                    "spans": [p["spans"] for p in paras],
                    "fill": _a_color(fill),
                }
            )
        rows.append(row)
    return {"rows": rows, "merged": merged}


# --------------------------------------------------------------------------- text


def _text(path: Path, family: str) -> dict:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SnapshotError(f"{path}: not UTF-8 text") from exc
    newline = "crlf" if "\r\n" in text else "lf"
    normalized = text.replace("\r\n", "\n")
    lines = normalized.split("\n")
    trailing = normalized.endswith("\n")
    if trailing:
        lines = lines[:-1]
    body: dict = {
        "format": TEXT_SUFFIXES.get(path.suffix.lower(), "text"),
        "newline": newline,
        "trailing_newline": trailing,
        "lines": lines,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    if family == "config":
        body["parsed"] = parse_config(normalized, body["format"])
    return body


def strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas outside JSON strings."""
    out = []
    i = 0
    in_string = False
    while i < len(text):
        char = text[i]
        if in_string:
            out.append(char)
            if char == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
                continue
            if char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end == -1 else end
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = len(text) if end == -1 else end + 2
        else:
            out.append(char)
            i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(out))


def parse_config(text: str, fmt: str) -> dict | list | None:
    if fmt == "json":
        try:
            return {"ok": True, "value": json.loads(strip_jsonc(text))}
        except json.JSONDecodeError as exc:
            return {"ok": False, "error": f"json: {exc.msg} at line {exc.lineno}"}
    if fmt == "ini":
        parser = configparser.RawConfigParser(strict=False, interpolation=None)
        parser.optionxform = str  # type: ignore[assignment,method-assign]
        try:
            parser.read_string(text if text.lstrip().startswith("[") else "[__root__]\n" + text)
        except configparser.Error as exc:
            return {"ok": False, "error": f"ini: {exc.__class__.__name__}"}
        return {
            "ok": True,
            "value": {section: dict(parser.items(section)) for section in parser.sections()},
        }
    return None
