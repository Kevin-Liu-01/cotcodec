"""Set properties in a LibreOffice ``registrymodifications.xcu`` (standard library only).

The file is a flat list of ``<item oor:path="..."><prop oor:name="..." oor:op="fuse">
<value>...</value></prop></item>`` lines inside ``<oor:items>``. Setting a property removes
every existing item for the same (path, name) and appends one new item before
``</oor:items>``; nothing else in the file changes, so the control cell's profile (no
overrides) stays byte-identical to the VM's.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

_ITEM = re.compile(r"<item\s+oor:path=(\"[^\"]*\"|'[^']*')\s*>(.*?)</item>\s*", re.DOTALL)
_PROP_NAME = re.compile(r"<prop\s+oor:name=(\"[^\"]*\"|'[^']*')")
_VALUE = re.compile(r"<value>(.*?)</value>", re.DOTALL)
CLOSE = "</oor:items>"


def _unquote(text: str) -> str:
    return text[1:-1]


def item_line(path: str, name: str, value: str) -> str:
    return (
        f'<item oor:path={quoteattr(path)}><prop oor:name={quoteattr(name)} oor:op="fuse">'
        f"<value>{escape(value)}</value></prop></item>\n"
    )


def read_props(text: str) -> dict[tuple[str, str], str | None]:
    """(path, name) -> value text (the last occurrence wins, as LibreOffice reads it)."""
    out: dict[tuple[str, str], str | None] = {}
    for match in _ITEM.finditer(text):
        path = _unquote(match.group(1))
        body = match.group(2)
        name = _PROP_NAME.search(body)
        if not name:
            continue
        value = _VALUE.search(body)
        out[(path, _unquote(name.group(1)))] = value.group(1) if value else None
    return out


def set_props(text: str, props: Iterable[tuple[str, str, str]]) -> str:
    props = list(props)
    if not props:
        return text
    if CLOSE not in text:
        raise ValueError("not a registrymodifications.xcu: no </oor:items>")
    wanted = {(path, name) for path, name, _ in props}

    def keep(match: re.Match[str]) -> str:
        name = _PROP_NAME.search(match.group(2))
        key = (_unquote(match.group(1)), _unquote(name.group(1)) if name else "")
        return "" if key in wanted else match.group(0)

    stripped = _ITEM.sub(keep, text)
    head, _, tail = stripped.rpartition(CLOSE)
    added = "".join(item_line(path, name, value) for path, name, value in props)
    return f"{head}{added}{CLOSE}{tail}"


def apply_to_profile(user_dir: Path, props: Iterable[tuple[str, str, str]]) -> list[str]:
    """Edit ``<user_dir>/registrymodifications.xcu`` in place; return what was set."""
    props = list(props)
    if not props:
        return []
    path = user_dir / "registrymodifications.xcu"
    text = path.read_text(encoding="utf-8")
    new = set_props(text, props)
    path.write_text(new, encoding="utf-8")
    got = read_props(new)
    for p, n, v in props:
        if got.get((p, n)) != escape(v):
            raise ValueError(f"profile property {p}/{n} was not set")
    return [f"{p}/{n}={v}" for p, n, v in props]
