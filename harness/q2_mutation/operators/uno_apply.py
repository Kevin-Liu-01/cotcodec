#!/usr/bin/env python3
"""Apply mutation recipes through LibreOffice's document model and save via ``.uno:Save``.

Runs inside the LibreOffice container (no network, no GPU, non-root) with the
office's own Python (``/opt/libreoffice7.3/program/python``) or a system Python
with ``python3-uno``. It is deliberately self-contained and Python-3.8
compatible: it imports nothing from this repository.

For each row of the apply manifest it copies the input document to the
output path, opens it visibly under Xvfb, performs the recipe's primitive
edits through the UNO API, marks the document modified and dispatches
``.uno:Save`` on the document frame, the same command Ctrl+S sends in the
OSWorld VM's postconfig. A profile equivalent to the VM's "always save as"
OOXML setting suppresses the keep-format dialog. A row with no steps is the
saved base (LibreOffice-save of the gold file).

Every edit first checks a SHA-256 digest of the text it expects to find, so a
recipe planned on one document can never silently edit a different one.

Usage::

    python uno_apply.py --manifest apply.jsonl --root /work --log /work/apply-log.jsonl
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback

import uno  # noqa: F401  (provided by LibreOffice)
from com.sun.star.beans import PropertyValue  # type: ignore[import-not-found]

APPLIER_VERSION = "q2-uno-apply-v1"
PIPE_PREFIX = "q2mutapply"
DEFAULT_TIMEOUT = 180

FONT_WEIGHT_BOLD = 150.0
FONT_WEIGHT_NORMAL = 100.0
UNDERLINE_SINGLE = 1
UNDERLINE_NONE = 0
CASEMAP_UPPER = 1
CLEAR_CONTENTS = 1 | 2 | 4 | 16  # VALUE | DATETIME | STRING | FORMULA
CLEAR_HARDATTR = 32
ZOOM_BY_VALUE = 3
# Formula parse errors (Err:501..511 and #NAME?); value errors such as #DIV/0! are legitimate.
PARSE_ERRORS = frozenset(list(range(501, 512)) + [525])

FACTORY = "/org.openoffice.Setup/Office/Factories/org.openoffice.Setup:Factory"
# (node path, property, value): the VM's "always save as" OOXML filters, no keep-format
# dialog, no autosave or recovery, no first-run dialogs.
PROFILE_SETTINGS = (
    ("/org.openoffice.Office.Common/Save/Document", "WarnAlienFormat", "false"),
    ("/org.openoffice.Office.Common/Save/Document", "AutoSave", "false"),
    ("/org.openoffice.Office.Recovery/AutoSave", "Enabled", "false"),
    ("/org.openoffice.Office.Recovery/RecoveryInfo", "Enabled", "false"),
    ("/org.openoffice.Office.Common/Misc", "FirstRun", "false"),
    ("/org.openoffice.Office.Common/Misc", "ShowTipOfTheDay", "false"),
    (FACTORY + "['com.sun.star.text.TextDocument']", "ooSetupFactoryDefaultFilter",
     "MS Word 2007 XML"),
    (FACTORY + "['com.sun.star.sheet.SpreadsheetDocument']", "ooSetupFactoryDefaultFilter",
     "Calc MS Excel 2007 XML"),
    (FACTORY + "['com.sun.star.presentation.PresentationDocument']",
     "ooSetupFactoryDefaultFilter", "Impress MS PowerPoint 2007 XML"),
    ("/org.openoffice.Office.Common/Security/Scripting", "MacroSecurityLevel", "3"),
)


def profile_xcu():
    items = "".join(
        f'<item oor:path="{path}"><prop oor:name="{name}" oor:op="fuse">'
        f"<value>{value}</value></prop></item>\n"
        for path, name, value in PROFILE_SETTINGS
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<oor:items xmlns:oor="http://openoffice.org/2001/registry" '
        'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'
        + items + "</oor:items>\n"
    )


class ApplyError(RuntimeError):
    """A recipe step could not be applied faithfully."""


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prop(name, value):
    item = PropertyValue()
    item.Name = name
    item.Value = value
    return item


def enum(type_name, value):
    return uno.Enum(type_name, value)


def check_digest(text, expected, what):
    if expected is None:
        return
    if isinstance(expected, list):
        raise ApplyError("internal: list digest passed to check_digest")
    actual = sha256_text(text)
    if actual != expected:
        raise ApplyError(
            f"{what} text digest mismatch (expected {expected[:12]}, found {actual[:12]})")


# --------------------------------------------------------------------------- office session


class Office:
    def __init__(self, soffice, workdir, display, profile_xcu=None, profile_template=None):
        self.soffice = soffice
        self.workdir = workdir
        self.display = display
        self.profile_xcu = profile_xcu
        self.profile_template = profile_template
        self.xvfb = None
        self.proc = None
        self.pipe = f"{PIPE_PREFIX}{os.getpid()}"
        self.desktop = None
        self.ctx = None
        self.smgr = None

    def start(self):
        env = dict(os.environ)
        if self.display:
            env["DISPLAY"] = self.display
            if not os.path.exists("/tmp/.X11-unix/X" + self.display.lstrip(":")):
                self.xvfb = subprocess.Popen(
                    ["Xvfb", self.display, "-screen", "0", "1920x1080x24", "-nolisten", "tcp"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                time.sleep(1.0)
        profile = os.path.join(self.workdir, "lo-profile")
        user_dir = os.path.join(profile, "user")
        if self.profile_template and not os.path.exists(user_dir):
            shutil.copytree(self.profile_template, user_dir, symlinks=True)
        os.makedirs(user_dir, exist_ok=True)
        xcu_path = os.path.join(user_dir, "registrymodifications.xcu")
        if self.profile_xcu:
            shutil.copyfile(self.profile_xcu, xcu_path)
        elif not self.profile_template and not os.path.exists(xcu_path):
            with open(xcu_path, "w") as handle:
                handle.write(profile_xcu())
        args = [
            self.soffice,
            "-env:UserInstallation=file://" + profile,
            f"--accept=pipe,name={self.pipe};urp;StarOffice.ComponentContext",
            "--norestore", "--nologo", "--nodefault", "--nolockcheck",
            "--nofirststartwizard",
        ]
        if not self.display:
            args.append("--headless")
        self.proc = subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        local = uno.getComponentContext()
        resolver = local.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local)
        deadline = time.time() + 60
        while True:
            try:
                self.ctx = resolver.resolve(
                    f"uno:pipe,name={self.pipe};urp;StarOffice.ComponentContext")
                break
            except Exception as exc:
                if time.time() > deadline or self.proc.poll() is not None:
                    raise ApplyError("soffice did not accept a UNO connection") from exc
                time.sleep(0.5)
        self.smgr = self.ctx.ServiceManager
        self.desktop = self.smgr.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)

    def stop(self):
        try:
            if self.desktop is not None:
                self.desktop.terminate()
        except Exception:
            pass
        for proc in (self.proc, self.xvfb):
            if proc is None:
                continue
            try:
                proc.wait(timeout=20)
            except Exception:
                proc.kill()
        self.desktop = None
        self.proc = None
        self.xvfb = None

    def kill(self):
        for proc in (self.proc, self.xvfb):
            if proc is not None and proc.poll() is None:
                proc.send_signal(signal.SIGKILL)
        self.desktop = None
        self.proc = None
        self.xvfb = None

    def load(self, path):
        url = uno.systemPathToFileUrl(os.path.abspath(path))
        hidden = not bool(self.display)
        doc = self.desktop.loadComponentFromURL(
            url, "_blank", 0, (prop("Hidden", hidden), prop("UpdateDocMode", 0),
                               prop("MacroExecutionMode", 0)))
        if doc is None:
            raise ApplyError(f"LibreOffice could not open {path}")
        return doc

    def gui_save(self, doc):
        """Dispatch .uno:Save on the document frame, as Ctrl+S does."""
        frame = doc.getCurrentController().getFrame()
        helper = self.smgr.createInstanceWithContext("com.sun.star.frame.DispatchHelper",
                                                     self.ctx)
        doc.setModified(True)
        helper.executeDispatch(frame, ".uno:Save", "", 0, ())
        deadline = time.time() + 60
        while doc.isModified():
            if time.time() > deadline:
                raise ApplyError(".uno:Save did not complete")
            time.sleep(0.2)

    def build_id(self):
        provider = self.smgr.createInstanceWithContext(
            "com.sun.star.configuration.ConfigurationProvider", self.ctx)
        access = provider.createInstanceWithArguments(
            "com.sun.star.configuration.ConfigurationAccess",
            (prop("nodepath", "/org.openoffice.Setup/Product"),))
        return "LibreOffice " + str(access.getByName("ooSetupVersionAboutBox"))


# --------------------------------------------------------------------------- shared props


def char_props(target, props):
    for key, value in props.items():
        if key == "bold":
            weight = FONT_WEIGHT_BOLD if value else FONT_WEIGHT_NORMAL
            for name in ("CharWeight", "CharWeightAsian", "CharWeightComplex"):
                _set_if_present(target, name, weight)
        elif key == "italic":
            slant = enum("com.sun.star.awt.FontSlant", "ITALIC" if value else "NONE")
            for name in ("CharPosture", "CharPostureAsian", "CharPostureComplex"):
                _set_if_present(target, name, slant)
        elif key == "underline":
            target.setPropertyValue("CharUnderline", UNDERLINE_SINGLE if value else UNDERLINE_NONE)
        elif key == "color":
            target.setPropertyValue("CharColor", int(value, 16) if value else -1)
        elif key == "highlight":
            _set_if_present(target, "CharHighlight", int(value, 16) if value else -1)
        elif key == "back_color":
            if value:
                target.setPropertyValue("CharBackColor", int(value, 16))
                _set_if_present(target, "CharBackTransparent", False)
            else:
                target.setPropertyValue("CharBackColor", -1)
                _set_if_present(target, "CharBackTransparent", True)
        elif key == "case_map":
            target.setPropertyValue("CharCaseMap", CASEMAP_UPPER if value == "upper" else 0)
        else:
            raise ApplyError(f"unknown character property {key!r}")


def _set_if_present(target, name, value):
    info = target.getPropertySetInfo()
    if info.hasPropertyByName(name):
        target.setPropertyValue(name, value)


def set_document_property(doc, field, value):
    props = doc.getDocumentProperties()
    if field == "Title":
        props.Title = value
    elif field == "Subject":
        props.Subject = value
    elif field == "Keywords":
        props.Keywords = (value,)
    else:
        raise ApplyError(f"unknown document property {field!r}")


# --------------------------------------------------------------------------- calc


def calc_sheet(doc, name):
    sheets = doc.getSheets()
    if not sheets.hasByName(name):
        raise ApplyError(f"no sheet {name!r}")
    return sheets.getByName(name)


def calc_step(office, doc, step):
    op = step["op"]
    if op == "xlsx.set_value":
        cell = calc_sheet(doc, step["sheet"]).getCellRangeByName(step["cell"])
        kind, value = step["value"]
        if kind == "n":
            cell.setValue(float(value))
        elif kind == "s":
            cell.setString(value)
        else:
            raise ApplyError(f"unsupported value kind {kind!r}")
    elif op == "xlsx.set_formula":
        cell = calc_sheet(doc, step["sheet"]).getCellRangeByName(step["cell"])
        cell.setFormula(step["formula_api"])
        doc.calculateAll()
        if cell.getError() in PARSE_ERRORS:
            raise ApplyError(f"formula {step['formula']!r} did not parse ({cell.getError()})")
    elif op == "xlsx.clear_contents":
        calc_sheet(doc, step["sheet"]).getCellRangeByName(step["range"]).clearContents(
            CLEAR_CONTENTS)
    elif op == "xlsx.set_char_props":
        char_props(calc_sheet(doc, step["sheet"]).getCellRangeByName(step["range"]),
                   step["props"])
    elif op == "xlsx.set_cell_props":
        target = calc_sheet(doc, step["sheet"]).getCellRangeByName(step["range"])
        for key, value in step["props"].items():
            if key == "fill":
                if value:
                    target.setPropertyValue("CellBackColor", int(value, 16))
                    target.setPropertyValue("IsCellBackgroundTransparent", False)
                else:
                    target.setPropertyValue("CellBackColor", -1)
                    target.setPropertyValue("IsCellBackgroundTransparent", True)
            elif key == "number_format":
                target.setPropertyValue("NumberFormat", number_format_key(doc, value))
            else:
                raise ApplyError(f"unknown cell property {key!r}")
    elif op == "xlsx.direct_to_named_style":
        direct_to_cell_style(doc, step)
    elif op == "xlsx.set_view":
        calc_view(doc, step)
    elif op == "xlsx.rename_sheet":
        calc_sheet(doc, step["sheet"]).setName(step["new_name"])
    elif op == "xlsx.remove_sheet":
        calc_sheet(doc, step["sheet"])
        doc.getSheets().removeByName(step["sheet"])
    elif op == "doc.set_property":
        set_document_property(doc, step["field"], step["value"])
    else:
        raise ApplyError(f"unknown calc step {op!r}")


def number_format_key(doc, code):
    formats = doc.getNumberFormats()
    locale = uno.createUnoStruct("com.sun.star.lang.Locale")
    locale.Language = "en"
    locale.Country = "US"
    key = formats.queryKey(code, locale, False)
    if key == -1:
        key = formats.addNew(code, locale)
    return key


STYLE_PROPS = (
    "CharWeight", "CharPosture", "CharUnderline", "CharColor", "CharHeight", "CharFontName",
    "CharStrikeout", "CellBackColor", "IsCellBackgroundTransparent", "NumberFormat",
    "HoriJustify", "VertJustify", "IsTextWrapped", "TopBorder", "BottomBorder",
    "LeftBorder", "RightBorder",
)
STYLE_VERIFY = ("CharWeight", "CharPosture", "CharUnderline", "CharColor", "CharHeight",
                "CharFontName", "CellBackColor", "NumberFormat")


def direct_to_cell_style(doc, step):
    cell = calc_sheet(doc, step["sheet"]).getCellRangeByName(step["cell"])
    values = {}
    for name in STYLE_PROPS:
        values[name] = cell.getPropertyValue(name)
    families = doc.getStyleFamilies().getByName("CellStyles")
    if families.hasByName(step["style_name"]):
        raise ApplyError(f"cell style {step['style_name']!r} exists")
    style = doc.createInstance("com.sun.star.style.CellStyle")
    families.insertByName(step["style_name"], style)
    for name, value in values.items():
        style.setPropertyValue(name, value)
    cell.setPropertyValue("CellStyle", step["style_name"])
    cell.clearContents(CLEAR_HARDATTR)
    for name in STYLE_VERIFY:
        if cell.getPropertyValue(name) != values[name]:
            raise ApplyError(f"named style does not reproduce {name}")


def calc_view(doc, step):
    controller = doc.getCurrentController()
    original = controller.getActiveSheet()
    target = calc_sheet(doc, step["sheet"])
    controller.setActiveSheet(target)
    if "zoom" in step:
        controller.setPropertyValue("ZoomType", ZOOM_BY_VALUE)
        controller.setPropertyValue("ZoomValue", int(step["zoom"]))
    if "select" in step:
        controller.select(target.getCellRangeByName(step["select"]))
    if step.get("restore_active"):
        controller.setActiveSheet(original)


# --------------------------------------------------------------------------- writer


def writer_block(doc, index):
    enumeration = doc.getText().createEnumeration()
    position = 0
    while enumeration.hasMoreElements():
        element = enumeration.nextElement()
        if position == index:
            return element
        position += 1
    raise ApplyError(f"no body block {index}")


def writer_paragraph(doc, step):
    block = writer_block(doc, step["block"])
    if "cell" not in step:
        if not block.supportsService("com.sun.star.text.Paragraph"):
            raise ApplyError(f"block {step['block']} is not a paragraph")
        return block
    if not block.supportsService("com.sun.star.text.TextTable"):
        raise ApplyError(f"block {step['block']} is not a table")
    row, col = step["cell"]
    cell = block.getCellByPosition(col, row)
    enumeration = cell.getText().createEnumeration()
    position = 0
    while enumeration.hasMoreElements():
        element = enumeration.nextElement()
        if position == step["para"]:
            return element
        position += 1
    raise ApplyError(f"no paragraph {step['para']} in cell {step['cell']!r}")


def text_range_cursor(paragraph, start, end):
    text = paragraph.getText()
    cursor = text.createTextCursorByRange(paragraph.getStart())
    if start:
        cursor.goRight(start, False)
    if end > start:
        cursor.goRight(end - start, True)
    return cursor


WRITER_CHAR_STYLE_PROPS = {
    "bold": ("CharWeight", "CharWeightAsian", "CharWeightComplex"),
    "italic": ("CharPosture", "CharPostureAsian", "CharPostureComplex"),
    "underline": ("CharUnderline",),
    "color": ("CharColor",),
}
PARA_PROPS = (
    "ParaAdjust", "ParaTopMargin", "ParaBottomMargin", "ParaLeftMargin", "ParaRightMargin",
    "ParaFirstLineIndent", "ParaLineSpacing", "ParaContextMargin",
)
PORTION_PROPS = (
    "CharWeight", "CharWeightAsian", "CharWeightComplex", "CharPosture", "CharPostureAsian",
    "CharPostureComplex", "CharUnderline", "CharColor", "CharHeight", "CharHeightAsian",
    "CharHeightComplex", "CharFontName", "CharFontNameAsian", "CharFontNameComplex",
    "CharCaseMap", "CharStrikeout", "CharKerning", "CharEscapement", "CharEscapementHeight",
)


def writer_step(office, doc, step):
    op = step["op"]
    if op == "doc.set_property":
        set_document_property(doc, step["field"], step["value"])
        return
    if op == "docx.set_view":
        settings = doc.getCurrentController().getViewSettings()
        settings.setPropertyValue("ZoomType", ZOOM_BY_VALUE)
        settings.setPropertyValue("ZoomValue", int(step["zoom"]))
        return
    paragraph = writer_paragraph(doc, step)
    check_digest(paragraph.getString(), step.get("expect_sha256"), "paragraph")
    if op == "docx.replace_text":
        text_range_cursor(paragraph, step["start"], step["end"]).setString(step["new"])
    elif op == "docx.set_char_props":
        char_props(text_range_cursor(paragraph, step["start"], step["end"]), step["props"])
    elif op == "docx.set_para_props":
        for key, value in step["props"].items():
            if key == "adjust":
                paragraph.setPropertyValue(
                    "ParaAdjust", enum("com.sun.star.style.ParagraphAdjust", value.upper()))
            elif key == "line_spacing":
                spacing = uno.createUnoStruct("com.sun.star.style.LineSpacing")
                spacing.Mode = 0
                spacing.Height = int(value["value"])
                paragraph.setPropertyValue("ParaLineSpacing", spacing)
            else:
                raise ApplyError(f"unknown paragraph property {key!r}")
    elif op == "docx.delete_block":
        paragraph.dispose()
    elif op == "docx.direct_to_char_style":
        cursor = text_range_cursor(paragraph, step["start"], step["end"])
        families = doc.getStyleFamilies().getByName("CharacterStyles")
        if families.hasByName(step["style_name"]):
            raise ApplyError(f"character style {step['style_name']!r} exists")
        style = doc.createInstance("com.sun.star.style.CharacterStyle")
        families.insertByName(step["style_name"], style)
        names = [n for attr in step["attrs"] for n in WRITER_CHAR_STYLE_PROPS[attr]]
        values = {n: cursor.getPropertyValue(n) for n in names}
        for name, value in values.items():
            style.setPropertyValue(name, value)
        cursor.setPropertyValue("CharStyleName", step["style_name"])
        for name in names:
            cursor.setPropertyToDefault(name)
        for name, value in values.items():
            if cursor.getPropertyValue(name) != value:
                raise ApplyError(f"character style does not reproduce {name}")
    elif op == "docx.para_style_to_direct":
        para_style_to_direct(paragraph)
    else:
        raise ApplyError(f"unknown writer step {op!r}")


def para_style_to_direct(paragraph):
    para_values = {n: paragraph.getPropertyValue(n) for n in PARA_PROPS}
    portions = []
    offset = 0
    enumeration = paragraph.createEnumeration()
    while enumeration.hasMoreElements():
        portion = enumeration.nextElement()
        length = len(portion.getString())
        if length:
            portions.append((offset, offset + length,
                             {n: portion.getPropertyValue(n) for n in PORTION_PROPS}))
        offset += length
    paragraph.setPropertyValue("ParaStyleName", "Standard")
    for name, value in para_values.items():
        paragraph.setPropertyValue(name, value)
    for start, end, values in portions:
        cursor = text_range_cursor(paragraph, start, end)
        for name, value in values.items():
            cursor.setPropertyValue(name, value)
    for start, end, values in portions:
        cursor = text_range_cursor(paragraph, start, end)
        for name, value in values.items():
            if cursor.getPropertyValue(name) != value:
                raise ApplyError(f"direct formatting does not reproduce {name}")


# --------------------------------------------------------------------------- impress


def impress_slide(doc, index):
    pages = doc.getDrawPages()
    if index >= pages.getCount():
        raise ApplyError(f"no slide {index}")
    return pages.getByIndex(index)


def impress_shape(doc, step):
    slide = impress_slide(doc, step["slide"])
    if step["shape"] >= slide.getCount():
        raise ApplyError(f"no shape {step['shape']} on slide {step['slide']}")
    return slide, slide.getByIndex(step["shape"])


def shape_text(shape, step):
    """The XText the step addresses: the shape itself or one table cell."""
    if "cell" in step:
        model = shape.getPropertyValue("Model")
        row, col = step["cell"]
        return model.getCellByPosition(col, row)
    return shape


def impress_paragraph(text_obj, index):
    enumeration = text_obj.getText().createEnumeration()
    position = 0
    while enumeration.hasMoreElements():
        element = enumeration.nextElement()
        if position == index:
            return element
        position += 1
    raise ApplyError(f"no paragraph {index}")


def impress_cursor(text_obj, para_index, start, end):
    paragraph = impress_paragraph(text_obj, para_index)
    cursor = text_obj.getText().createTextCursorByRange(paragraph.getStart())
    if start:
        cursor.goRight(start, False)
    if end > start:
        cursor.goRight(end - start, True)
    return cursor


def emu_to_hmm(value):
    if value % 360:
        raise ApplyError(f"EMU value {value} is not a whole number of 1/100 mm")
    return int(value // 360)


COPY_SHAPE_PROPS = ("TextVerticalAdjust", "TextLeftDistance", "TextRightDistance",
                    "TextUpperDistance", "TextLowerDistance")
COPY_CHAR_PROPS = ("CharHeight", "CharWeight", "CharPosture", "CharUnderline", "CharColor",
                   "CharFontName", "CharCaseMap")


def impress_step(office, doc, step):
    op = step["op"]
    if op == "doc.set_property":
        set_document_property(doc, step["field"], step["value"])
        return
    if op == "pptx.delete_slide":
        slide = impress_slide(doc, step["slide"])
        if slide.getCount() != step.get("expect_shapes", slide.getCount()):
            raise ApplyError(
                f"slide {step['slide']} has {slide.getCount()} shapes, "
                f"expected {step['expect_shapes']}")
        doc.getDrawPages().remove(slide)
        return
    if op == "pptx.add_textbox":
        add_textbox(doc, step)
        return
    if op == "pptx.set_notes":
        notes_page = impress_slide(doc, step["slide"]).getNotesPage()
        target = None
        for i in range(notes_page.getCount()):
            shape = notes_page.getByIndex(i)
            if shape.getShapeType() == "com.sun.star.presentation.NotesShape":
                target = shape
        if target is None:
            raise ApplyError(f"slide {step['slide']} has no notes text shape")
        check_digest(target.getString(), step.get("expect_sha256"), "notes")
        target.setString(step["text"])
        return
    if op == "pptx.swap_z":
        slide = impress_slide(doc, step["slide"])
        first, second = slide.getByIndex(step["a"]), slide.getByIndex(step["b"])
        digests = step.get("expect_sha256") or [None, None]
        check_digest(_string(first), digests[0], "shape a")
        check_digest(_string(second), digests[1], "shape b")
        z_first, z_second = first.getPropertyValue("ZOrder"), second.getPropertyValue("ZOrder")
        second.setPropertyValue("ZOrder", z_first)
        first.setPropertyValue("ZOrder", z_second)
        return
    slide, shape = impress_shape(doc, step)
    target = shape_text(shape, step)
    check_digest(_string(target), step.get("expect_sha256"), "shape")
    if op == "pptx.replace_text":
        impress_cursor(target, step["para"], step["start"], step["end"]).setString(step["new"])
    elif op == "pptx.set_char_props":
        char_props(impress_cursor(target, step["para"], step["start"], step["end"]),
                   step["props"])
    elif op == "pptx.move_shape":
        position = shape.getPosition()
        position.X += emu_to_hmm(step["dx_emu"])
        position.Y += emu_to_hmm(step["dy_emu"])
        shape.setPosition(position)
    elif op == "pptx.delete_shape":
        slide.remove(shape)
    else:
        raise ApplyError(f"unknown impress step {op!r}")


def _string(shape):
    try:
        return shape.getString()
    except Exception:
        return ""


def add_textbox(doc, step):
    slide = impress_slide(doc, step["slide"])
    shape = doc.createInstance("com.sun.star.drawing.TextShape")
    slide.add(shape)
    shape.setPropertyValue("TextAutoGrowHeight", False)
    shape.setPropertyValue("TextAutoGrowWidth", False)
    shape.setPropertyValue("TextWordWrap", True)
    point = uno.createUnoStruct("com.sun.star.awt.Point")
    point.X = emu_to_hmm(step["x_emu"])
    point.Y = emu_to_hmm(step["y_emu"])
    size = uno.createUnoStruct("com.sun.star.awt.Size")
    size.Width = emu_to_hmm(step["w_emu"])
    size.Height = emu_to_hmm(step["h_emu"])
    shape.setPosition(point)
    shape.setSize(size)
    text = shape.getText()
    cursor = text.createTextCursor()
    for i, para in enumerate(step["paras"]):
        if i:
            text.insertControlCharacter(cursor, 0, False)
        text.insertString(cursor, para, False)
    source_index = step.get("copy_format_from")
    if source_index is not None:
        source = slide.getByIndex(source_index)
        check_digest(_string(source), step.get("expect_sha256"), "source shape")
        for name in COPY_SHAPE_PROPS:
            shape.setPropertyValue(name, source.getPropertyValue(name))
        for i in range(len(step["paras"])):
            src = impress_paragraph(source, i)
            dst = impress_paragraph(shape, i)
            dst.setPropertyValue("ParaAdjust", src.getPropertyValue("ParaAdjust"))
            first = src.createEnumeration().nextElement()
            for name in COPY_CHAR_PROPS:
                dst.setPropertyValue(name, first.getPropertyValue(name))


# --------------------------------------------------------------------------- driver


def apply_row(office, root, row):
    src = os.path.join(root, row["input"])
    dst = os.path.join(root, row["output"])
    if row.get("input_sha256") and sha256_file(src) != row["input_sha256"]:
        raise ApplyError("input digest mismatch")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    doc = office.load(dst)
    try:
        family = row["family"]
        handler = {"xlsx": calc_step, "docx": writer_step, "pptx": impress_step}[family]
        for step in row["steps"]:
            handler(office, doc, step)
        office.gui_save(doc)
    finally:
        with contextlib.suppress(Exception):
            doc.close(True)
    return sha256_file(dst)


def lo_version(soffice):
    """``soffice --version`` text, or the version file the LO-VM image records at build."""
    try:
        text = subprocess.run([soffice, "--version"], stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        text = ""
    if not text and os.path.exists("/opt/q2/soffice-version.txt"):
        with open("/opt/q2/soffice-version.txt") as handle:
            text = handle.read().strip()
    return text


class Watchdog:
    """Kill a hung office after ``seconds``; the row is then recorded as an error."""

    def __init__(self, office, seconds):
        self.office = office
        self.done = threading.Event()
        self.timer = threading.Timer(seconds, self._fire)

    def _fire(self):
        if not self.done.is_set():
            self.office.kill()

    def __enter__(self):
        self.timer.start()
        return self

    def __exit__(self, *exc):
        self.done.set()
        self.timer.cancel()
        return False


def run(args):
    rows = []
    with open(args.manifest) as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    workdir = tempfile.mkdtemp(prefix="q2-uno-")

    def new_office():
        return Office(args.soffice, workdir, args.display, args.profile_xcu,
                      args.profile_template)

    office = new_office()
    office.start()
    build = office.build_id()
    version = lo_version(args.soffice)
    try:
        with open(args.log, "a") as log:
            for row in rows:
                started = time.time()
                record = {"mutant_id": row["mutant_id"], "applier": APPLIER_VERSION,
                          "lo_build": version or build, "display": bool(args.display)}
                try:
                    with Watchdog(office, args.timeout):
                        record["output_sha256"] = apply_row(office, args.root, row)
                    record["status"] = "ok"
                except Exception as exc:  # recorded, never relabelled
                    record["status"] = "error"
                    record["error"] = f"{exc.__class__.__name__}: {exc}"
                    record["trace"] = traceback.format_exc()[-2000:]
                    if office.proc is None or office.proc.poll() is not None:
                        office.kill()
                        office = new_office()
                        office.start()
                record["seconds"] = round(time.time() - started, 3)
                log.write(json.dumps(record, sort_keys=True) + "\n")
                log.flush()
    finally:
        office.stop()
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--soffice", default="soffice")
    parser.add_argument("--display", default=":99",
                        help="X display for a visible office; empty for headless fallback")
    parser.add_argument("--profile-xcu", default=None,
                        help="registrymodifications.xcu to use instead of the built-in one")
    parser.add_argument("--profile-template", default=None,
                        help="a LibreOffice user profile directory to copy (the VM's profile)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
