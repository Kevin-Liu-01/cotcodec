# ruff: noqa: E501  (fixture XML is clearer on one line)
"""Small synthetic documents written from scratch for tests and harness validation.

None of this content comes from OSWorld. Each builder takes keyword options so
tests can write both a base document and the document an operator should
produce, and compare them with the purity checker. The matching synthetic
specs follow the binding schema but are test fixtures, not task specs.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

SYNTH_TASK_IDS = {
    "xlsx": "00000000-0000-4000-8000-00000000a001",
    "docx": "00000000-0000-4000-8000-00000000a002",
    "pptx": "00000000-0000-4000-8000-00000000a003",
    "config": "00000000-0000-4000-8000-00000000a004",
    "ini": "00000000-0000-4000-8000-00000000a005",
    "text": "00000000-0000-4000-8000-00000000a006",
}

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">{title}<dc:creator>synthetic</dc:creator></cp:coreProperties>"""
REL_DOC = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL_PKG = "http://schemas.openxmlformats.org/package/2006/relationships"


def _write_zip(path: Path, parts: dict[str, str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(parts, key=lambda n: (n != "[Content_Types].xml", n)):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, parts[name])
    return path


def _rels(entries: list[tuple[str, str, str]]) -> str:
    body = "".join(
        f'<Relationship Id="{rid}" Type="{rtype}" Target="{target}"/>'
        for rid, rtype, target in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<Relationships xmlns="{REL_PKG}">{body}</Relationships>'
    )


def _core(title: str | None) -> str:
    return CORE.format(title=f"<dc:title>{escape(title)}</dc:title>" if title else "")


# --------------------------------------------------------------------------- xlsx

XLSX_CELLS: dict[str, dict[str, tuple]] = {
    "Data": {
        "A1": ("s", "Item", 1), "B1": ("s", "Qty", 1), "C1": ("s", "Price", 1),
        "D1": ("s", "Total", 1),
        "A2": ("s", "Apple", 0), "B2": ("n", 3, 0), "C2": ("n", 1.5, 0),
        "D2": ("f", "B2*C2", 2, 4.5),
        "A3": ("s", "Pear", 0), "B3": ("n", 2, 0), "C3": ("n", 2.25, 0),
        "D3": ("f", "B3*C3", 2, 4.5),
        "A4": ("s", "Plum", 0), "B4": ("n", 5, 0), "C4": ("n", 0.8, 0),
        "D4": ("f", "B4*C4", 2, 4.0),
        "A5": ("s", "Sum", 3), "B5": ("f", "SUM(B2:B4)", 0, 10.0),
        "D5": ("f", "D2+D3+D4", 2, 13.0),
        "A6": ("s", "Mean", 0), "B6": ("f", "AVERAGE(B2:B4)", 0, 10 / 3),
        "A7": ("s", "Label", 0), "B7": ("fs", 'CONCATENATE(A2,"-",A3)', 0, "Apple-Pear"),
        "A8": ("s", "Target", 0), "B8": ("n", 12, 0),
        "A10": ("s", "Region", 0), "B10": ("s", "North", 0), "C10": ("n", 7, 0),
        "A11": ("s", "Region", 0), "B11": ("s", "South", 0), "C11": ("n", 9, 0),
    },
    "Notes": {
        "A1": ("s", "Notes", 0), "A2": ("s", "Keep this archive", 0), "B2": ("n", 12, 0),
    },
}

XLSX_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="0.00"/></numFmts>
<fonts count="2"><font><sz val="11"/><name val="Liberation Sans"/></font><font><b/><sz val="11"/><name val="Liberation Sans"/></font></fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FFFFFF00"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="0" fillId="2" borderId="0" xfId="0" applyFill="1"/></cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""


def _xlsx_cell(address: str, spec: tuple) -> str:
    kind = spec[0]
    style = spec[2]
    if kind == "s":
        return f'<c r="{address}" s="{style}" t="inlineStr"><is><t>{escape(spec[1])}</t></is></c>'
    if kind == "n":
        return f'<c r="{address}" s="{style}"><v>{spec[1]}</v></c>'
    if kind == "f":
        return f'<c r="{address}" s="{style}"><f>{escape(spec[1])}</f><v>{spec[3]!r}</v></c>'
    if kind == "fs":
        return (f'<c r="{address}" s="{style}" t="str"><f>{escape(spec[1])}</f>'
                f"<v>{escape(spec[3])}</v></c>")
    raise ValueError(kind)


def _sheet_xml(cells: dict[str, tuple], selected: bool) -> str:
    import re

    rows: dict[int, list[str]] = {}
    for address in cells:
        row = int(re.sub(r"[A-Z]+", "", address))
        rows.setdefault(row, []).append(address)

    def col_key(addr: str) -> tuple[int, str]:
        letters = re.sub(r"\d+", "", addr)
        return (len(letters), letters)

    body = "".join(
        f'<row r="{r}">' + "".join(_xlsx_cell(a, cells[a]) for a in sorted(addrs, key=col_key))
        + "</row>"
        for r, addrs in sorted(rows.items())
    )
    tab = ' tabSelected="1"' if selected else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetViews><sheetView workbookViewId="0"{tab}/></sheetViews>'
        f"<sheetData>{body}</sheetData></worksheet>"
    )


def build_xlsx(path: str | Path, *, cells: dict | None = None, title: str | None = None,
               drop: tuple[str, ...] = ()) -> Path:
    """Write the synthetic workbook; ``cells`` overrides ``XLSX_CELLS`` per sheet."""
    sheets = {name: dict(body) for name, body in XLSX_CELLS.items()}
    for name, body in (cells or {}).items():
        sheets.setdefault(name, {}).update(body)
    for ref in drop:
        sheet, address = ref.split("!")
        sheets[sheet].pop(address, None)
    names = list(sheets)
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            + "".join(
                f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                for i in range(len(names))
            )
            + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": _rels([
            ("rId1", f"{REL_DOC}/officeDocument", "xl/workbook.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
        ]),
        "docProps/core.xml": _core(title),
        "xl/workbook.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="{REL_DOC}">'
            '<bookViews><workbookView activeTab="0"/></bookViews><sheets>'
            + "".join(
                f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
                for i, n in enumerate(names)
            )
            + "</sheets></workbook>"
        ),
        "xl/_rels/workbook.xml.rels": _rels(
            [(f"rId{i + 1}", f"{REL_DOC}/worksheet", f"worksheets/sheet{i + 1}.xml")
             for i in range(len(names))]
            + [(f"rId{len(names) + 1}", f"{REL_DOC}/styles", "styles.xml")]
        ),
        "xl/styles.xml": XLSX_STYLES,
    }
    for i, name in enumerate(names):
        parts[f"xl/worksheets/sheet{i + 1}.xml"] = _sheet_xml(sheets[name], i == 0)
    return _write_zip(Path(path), parts)


# --------------------------------------------------------------------------- docx

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

DOCX_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{W}">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Liberation Serif" w:hAnsi="Liberation Serif"/><w:sz w:val="24"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr/></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:pPr><w:jc w:val="center"/><w:spacing w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/></w:rPr></w:style>
</w:styles>"""

DEFAULT_DOCX = [
    {"style": "Title", "runs": [("ANNUAL REPORT", {})]},
    {"runs": [("Revenue grew ", {}), ("strongly", {"b": True}), (" this year.", {})]},
    {"jc": "center", "runs": [("Costs were stable.", {})]},
    {"runs": [("Highlights include ", {}), ("new markets", {"highlight": "yellow"}),
              (".", {})]},
    {"table": [["Region", "Sales"], ["North", "120"]]},
    {"runs": [("Prepared by the finance team.", {})]},
    {"runs": [("Appendix follows on the next page.", {})]},
]


def _docx_run(text: str, props: dict) -> str:
    rpr = ""
    if props.get("b"):
        rpr += "<w:b/>"
    if props.get("i"):
        rpr += "<w:i/>"
    if props.get("highlight"):
        rpr += f'<w:highlight w:val="{props["highlight"]}"/>'
    if props.get("color"):
        rpr += f'<w:color w:val="{props["color"]}"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _docx_paragraph(spec: dict) -> str:
    ppr = ""
    if spec.get("style"):
        ppr += f'<w:pStyle w:val="{spec["style"]}"/>'
    if spec.get("jc"):
        ppr += f'<w:jc w:val="{spec["jc"]}"/>'
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}" + "".join(_docx_run(t, p) for t, p in spec["runs"]) + "</w:p>"


def _docx_table(rows: list[list[str]]) -> str:
    grid = "".join('<w:gridCol w:w="2400"/>' for _ in rows[0])
    body = "".join(
        "<w:tr>" + "".join(
            f'<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/></w:tcPr>{_docx_paragraph({"runs": [(cell, {})]})}</w:tc>'
            for cell in row
        ) + "</w:tr>"
        for row in rows
    )
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="4800" w:type="dxa"/></w:tblPr>'
        f"<w:tblGrid>{grid}</w:tblGrid>{body}</w:tbl>"
    )


def build_docx(path: str | Path, *, blocks: list[dict] | None = None,
               title: str | None = None, zoom: int = 100) -> Path:
    blocks = DEFAULT_DOCX if blocks is None else blocks
    body = "".join(
        _docx_table(b["table"]) if "table" in b else _docx_paragraph(b) for b in blocks
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}" xmlns:r="{REL_DOC}"><w:body>{body}'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" '
        'w:bottom="1440" w:left="1440" w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )
    parts = {
        "[Content_Types].xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": _rels([
            ("rId1", f"{REL_DOC}/officeDocument", "word/document.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
        ]),
        "docProps/core.xml": _core(title),
        "word/document.xml": document,
        "word/_rels/document.xml.rels": _rels([
            ("rId1", f"{REL_DOC}/styles", "styles.xml"),
            ("rId2", f"{REL_DOC}/settings", "settings.xml"),
        ]),
        "word/styles.xml": DOCX_STYLES,
        "word/settings.xml": (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<w:settings xmlns:w="{W}"><w:zoom w:percent="{zoom}"/></w:settings>'
        ),
    }
    return _write_zip(Path(path), parts)


# --------------------------------------------------------------------------- pptx

A = "http://schemas.openxmlformats.org/drawingml/2006/main"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"

THEME = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="{A}" name="Synthetic"><a:themeElements>
<a:clrScheme name="Synthetic"><a:dk1><a:srgbClr val="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F497D"/></a:dk2><a:lt2><a:srgbClr val="EEECE1"/></a:lt2><a:accent1><a:srgbClr val="4F81BD"/></a:accent1><a:accent2><a:srgbClr val="C0504D"/></a:accent2><a:accent3><a:srgbClr val="9BBB59"/></a:accent3><a:accent4><a:srgbClr val="8064A2"/></a:accent4><a:accent5><a:srgbClr val="4BACC6"/></a:accent5><a:accent6><a:srgbClr val="F79646"/></a:accent6><a:hlink><a:srgbClr val="0000FF"/></a:hlink><a:folHlink><a:srgbClr val="800080"/></a:folHlink></a:clrScheme>
<a:fontScheme name="Synthetic"><a:majorFont><a:latin typeface="Liberation Sans"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Liberation Sans"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont></a:fontScheme>
<a:fmtScheme name="Synthetic"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
</a:themeElements></a:theme>"""

EMPTY_TREE = (
    '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
    '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
    '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
)

DEFAULT_SLIDES = [
    [
        {"kind": "title", "name": "Title 1", "off": (457200, 274320), "ext": (8229600, 1143000),
         "paras": [[("QUARTERLY RESULTS", {})]]},
        {"kind": "text", "name": "TextBox 2", "off": (457200, 1600200), "ext": (4114800, 914400),
         "paras": [[("Revenue rose in the ", {}), ("north", {"b": True}), (" region", {})]]},
        {"kind": "table", "name": "Table 3", "off": (457200, 3200400), "ext": (4114800, 740664),
         "rows": [["Region", "Sales"], ["North", "120"]]},
        {"kind": "text", "name": "TextBox 4", "off": (5029200, 1600200), "ext": (3657600, 914400),
         "paras": [[("Outlook remains positive", {})]]},
    ],
    [
        {"kind": "text", "name": "TextBox 1", "off": (457200, 457200), "ext": (8229600, 914400),
         "paras": [[("Backup material for questions", {})]]},
        {"kind": "rect", "name": "Rectangle 2", "off": (457200, 2286000),
         "ext": (2743200, 1371600)},
    ],
]


def _a_runs(runs: list[tuple[str, dict]]) -> str:
    out = ""
    for text, props in runs:
        attrs = ' lang="en-US"'
        if props.get("b"):
            attrs += ' b="1"'
        if props.get("i"):
            attrs += ' i="1"'
        out += f"<a:r><a:rPr{attrs}/><a:t>{escape(text)}</a:t></a:r>"
    return out


def _pptx_shape(index: int, spec: dict) -> str:
    sid = index + 2
    xfrm = (f'<a:xfrm><a:off x="{spec["off"][0]}" y="{spec["off"][1]}"/>'
            f'<a:ext cx="{spec["ext"][0]}" cy="{spec["ext"][1]}"/></a:xfrm>')
    name = escape(spec["name"])
    if spec["kind"] == "table":
        cols = len(spec["rows"][0])
        width = spec["ext"][0] // cols
        grid = "".join(f'<a:gridCol w="{width}"/>' for _ in range(cols))
        rows = "".join(
            '<a:tr h="370332">' + "".join(
                f"<a:tc><a:txBody><a:bodyPr/><a:lstStyle/><a:p>{_a_runs([(c, {})])}</a:p>"
                "</a:txBody><a:tcPr/></a:tc>"
                for c in row
            ) + "</a:tr>"
            for row in spec["rows"]
        )
        return (
            f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{sid}" name="{name}"/>'
            '<p:cNvGraphicFramePr><a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/>'
            f'</p:nvGraphicFramePr><p:xfrm><a:off x="{spec["off"][0]}" y="{spec["off"][1]}"/>'
            f'<a:ext cx="{spec["ext"][0]}" cy="{spec["ext"][1]}"/></p:xfrm>'
            '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table">'
            f"<a:tbl><a:tblPr/><a:tblGrid>{grid}</a:tblGrid>{rows}</a:tbl>"
            "</a:graphicData></a:graphic></p:graphicFrame>"
        )
    ph = '<p:ph type="title"/>' if spec["kind"] == "title" else ""
    tx_box = ' txBox="1"' if spec["kind"] == "text" else ""
    geom = '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    fill = '<a:solidFill><a:srgbClr val="4F81BD"/></a:solidFill>' if spec["kind"] == "rect" else ""
    body = ""
    if spec.get("paras"):
        paras = "".join(f"<a:p>{_a_runs(runs)}</a:p>" for runs in spec["paras"])
        body = f'<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>{paras}</p:txBody>'
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{name}"/><p:cNvSpPr{tx_box}/>'
        f"<p:nvPr>{ph}</p:nvPr></p:nvSpPr><p:spPr>{xfrm}{geom}{fill}</p:spPr>{body}</p:sp>"
    )


def build_pptx(path: str | Path, *, slides: list[list[dict]] | None = None,
               title: str | None = None) -> Path:
    slides = DEFAULT_SLIDES if slides is None else slides
    n = len(slides)
    ct = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>'
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>'
        '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>'
        + "".join(
            f'<Override PartName="/ppt/slides/slide{i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
            for i in range(n)
        )
        + '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        "</Types>"
    )
    presentation = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:presentation xmlns:a="{A}" xmlns:r="{REL_DOC}" xmlns:p="{P}">'
        '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        "<p:sldIdLst>"
        + "".join(f'<p:sldId id="{256 + i}" r:id="rId{i + 3}"/>' for i in range(n))
        + '</p:sldIdLst><p:sldSz cx="9144000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    )
    master = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sldMaster xmlns:a="{A}" xmlns:r="{REL_DOC}" xmlns:p="{P}">'
        f"<p:cSld><p:spTree>{EMPTY_TREE}</p:spTree></p:cSld>"
        '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
        'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" '
        'folHlink="folHlink"/>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        "</p:sldMaster>"
    )
    layout = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sldLayout xmlns:a="{A}" xmlns:r="{REL_DOC}" xmlns:p="{P}" type="titleOnly">'
        f'<p:cSld name="Title Only"><p:spTree>{EMPTY_TREE}</p:spTree></p:cSld>'
        "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>"
    )
    parts = {
        "[Content_Types].xml": ct,
        "_rels/.rels": _rels([
            ("rId1", f"{REL_DOC}/officeDocument", "ppt/presentation.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
        ]),
        "docProps/core.xml": _core(title),
        "ppt/presentation.xml": presentation,
        "ppt/_rels/presentation.xml.rels": _rels(
            [("rId1", f"{REL_DOC}/slideMaster", "slideMasters/slideMaster1.xml"),
             ("rId2", f"{REL_DOC}/theme", "theme/theme1.xml")]
            + [(f"rId{i + 3}", f"{REL_DOC}/slide", f"slides/slide{i + 1}.xml") for i in range(n)]
        ),
        "ppt/slideMasters/slideMaster1.xml": master,
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": _rels([
            ("rId1", f"{REL_DOC}/slideLayout", "../slideLayouts/slideLayout1.xml"),
            ("rId2", f"{REL_DOC}/theme", "../theme/theme1.xml"),
        ]),
        "ppt/slideLayouts/slideLayout1.xml": layout,
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": _rels([
            ("rId1", f"{REL_DOC}/slideMaster", "../slideMasters/slideMaster1.xml"),
        ]),
        "ppt/theme/theme1.xml": THEME,
    }
    for i, shapes in enumerate(slides):
        tree = EMPTY_TREE + "".join(_pptx_shape(k, s) for k, s in enumerate(shapes))
        parts[f"ppt/slides/slide{i + 1}.xml"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld xmlns:a="{A}" xmlns:r="{REL_DOC}" xmlns:p="{P}">'
            f"<p:cSld><p:spTree>{tree}</p:spTree></p:cSld>"
            "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
        )
        parts[f"ppt/slides/_rels/slide{i + 1}.xml.rels"] = _rels([
            ("rId1", f"{REL_DOC}/slideLayout", "../slideLayouts/slideLayout1.xml"),
        ])
    return _write_zip(Path(path), parts)


# --------------------------------------------------------------------------- text files

SETTINGS_JSON = {
    "editor.fontSize": 14,
    "editor.wordWrap": "on",
    "files.autoSave": "off",
    "workbench": {"colorTheme": "Default Dark", "sideBar": "left"},
}
APP_INI = "[general]\nname = demo\nthreads = 4\nverbose = false\n\n[ui]\ntheme = dark\nfont = mono\n"
NOTES_TXT = (
    "Release checklist\n"
    "Run the full test suite\n"
    "Deploy at noon on Friday\n"
    "Notify the support channel\n"
    "Archive the old build logs\n"
)


def build_json(path: str | Path, data: dict | None = None, indent: int = 4) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(SETTINGS_JSON if data is None else data, indent=indent) + "\n",
                    encoding="utf-8")
    return path


def build_text(path: str | Path, content: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# --------------------------------------------------------------------------- specs


def synthetic_spec(kind: str) -> dict:
    """A schema-valid spec for the synthetic document of ``kind`` (test fixture)."""
    task_id = SYNTH_TASK_IDS[kind]
    author = "blind-model-author-v1"
    if kind == "xlsx":
        reqs = [
            ("R1", "Cell D5 on the Data sheet holds the grand total of D2:D4.", "cell_value",
             "Read Data!D5; it equals 13."),
            ("R2", "B6 holds the mean quantity of B2:B4.", "cell_value",
             "Data!B6 equals 10/3."),
            ("R3", "The header row A1:D1 is bold.", "cell_format",
             "Cells A1:D1 render in a bold font."),
            ("R4", "B5 holds the total quantity.", "cell_value", "Data!B5 equals 10."),
            ("R5", "B7 joins the first two item names with a hyphen.", "cell_value",
             "Data!B7 reads Apple-Pear."),
            ("R6", "D2:D4 show two decimals.", "cell_format",
             "D2:D4 use a number format with two decimal places."),
            ("R7", "B8 holds the target quantity 12.", "cell_value", "Data!B8 equals 12."),
        ]
        allowed = ["column widths", "which cell is selected"]
    elif kind == "docx":
        reqs = [
            ("R1", 'The first paragraph reads "ANNUAL REPORT".', "text_run",
             'Paragraph 1 text equals "ANNUAL REPORT".'),
            ("R2", 'The word "strongly" in the second paragraph is bold.', "text_run",
             'The run "strongly" renders bold.'),
            ("R3", 'The paragraph "Costs were stable." is centered.', "paragraph_format",
             "Its alignment is center."),
            ("R4", 'The phrase "new markets" is highlighted in yellow.', "text_run",
             'The phrase "new markets" has a yellow highlight.'),
        ]
        allowed = ["page margins"]
    elif kind == "pptx":
        reqs = [
            ("R1", 'Slide 1 has the title "QUARTERLY RESULTS".', "text_run",
             "The title placeholder on slide 1 reads QUARTERLY RESULTS."),
            ("R2", 'The table on slide 1 lists "North" with sales of 120.', "table_cell",
             'A table cell on slide 1 reads "North".'),
            ("R3", 'The text box "Revenue rose in the north region" sits at the left of slide 1.',
             "slide_object", "That text box's position is unchanged at the left."),
            ("R4", 'The word "north" in "Revenue rose in the north region" is bold.',
             "text_run", 'The run "north" renders bold.'),
        ]
        allowed = []
    elif kind == "config":
        reqs = [
            ("R1", 'Set "editor.fontSize" to 14.', "config_value",
             "settings.json key editor.fontSize equals 14."),
        ]
        allowed = []
    elif kind == "ini":
        reqs = [
            ("R1", 'In section general, "threads" is 4.', "config_value",
             "app.conf [general] threads equals 4."),
        ]
        allowed = []
    elif kind == "text":
        reqs = [
            ("R1", 'The checklist contains the line "Deploy at noon on Friday".', "text_run",
             'A line reads "Deploy at noon on Friday".'),
        ]
        allowed = []
    else:
        raise ValueError(kind)
    return {
        "task_id": task_id,
        "author": author,
        "requirements": [
            {"req_id": r, "statement": s, "check_kind": k, "observable": o}
            for r, s, k, o in reqs
        ],
        "allowed_variations": allowed,
    }
