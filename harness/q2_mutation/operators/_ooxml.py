"""Standard-library OOXML access shared by the snapshot reader and test fixtures.

The purity diff deliberately avoids openpyxl, python-docx and python-pptx, which
are the libraries the OSWorld checkers use. Reading the package with zipfile and
ElementTree keeps the mutation oracle on a stack independent of the checker.
"""

from __future__ import annotations

import posixpath
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "xdr": "http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing",
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}

REL_OFFICE_DOCUMENT = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
)


def q(prefix: str, local: str) -> str:
    """Return the Clark-notation tag for ``prefix:local``."""
    return f"{{{NS[prefix]}}}{local}"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


class Package:
    """A read-only view of an OOXML zip package."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        with zipfile.ZipFile(self.path) as archive:
            self.parts = {info.filename: archive.read(info) for info in archive.infolist()}

    def has(self, name: str) -> bool:
        return name in self.parts

    def xml(self, name: str) -> ET.Element | None:
        data = self.parts.get(name)
        if data is None:
            return None
        return ET.fromstring(data)

    def rels(self, part: str) -> dict[str, tuple[str, str, str]]:
        """Map relationship id to (type, resolved target, target mode) for ``part``."""
        directory, base = posixpath.split(part)
        rels_name = posixpath.join(directory, "_rels", base + ".rels")
        root = self.xml(rels_name)
        result: dict[str, tuple[str, str, str]] = {}
        if root is None:
            return result
        for rel in root.findall(q("rel", "Relationship")):
            target = rel.get("Target", "")
            mode = rel.get("TargetMode", "Internal")
            if mode == "External":
                resolved = target
            elif target.startswith("/"):
                resolved = target.lstrip("/")
            else:
                resolved = posixpath.normpath(posixpath.join(directory, target))
            result[rel.get("Id", "")] = (rel.get("Type", ""), resolved, mode)
        return result

    def main_part(self) -> str:
        for _rid, (rtype, target, _mode) in self.rels("").items():
            if rtype == REL_OFFICE_DOCUMENT:
                return target
        raise ValueError(f"{self.path}: package has no officeDocument relationship")


def bool_attr(value: str | None, default: bool = True) -> bool:
    """OOXML on/off attributes: absent means ``default``; 0/false/off mean False."""
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "off", "none"}


def element_to_canonical(element: ET.Element) -> dict:
    """A JSON-able canonical form of an element: local names, sorted attributes."""
    attrs = {local_name(k): v for k, v in sorted(element.attrib.items())}
    children = [element_to_canonical(child) for child in element]
    node: dict = {"tag": local_name(element.tag)}
    if attrs:
        node["attrs"] = attrs
    if children:
        node["children"] = children
    text = (element.text or "").strip()
    if text:
        node["text"] = text
    return node
