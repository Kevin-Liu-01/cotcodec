#!/usr/bin/env python3
"""S2 v3 Phase 0: generated interface catalogs for LibreOffice 7.3.7.2, built offline.

Runs inside the LO-VM container (the certified OSWorld VM's own LibreOffice userland), with the
container's system Python 3.10 and the standard library only. Nothing is downloaded: every
catalog is generated from the English strings the installed build already ships.

Three string sources, each with the key LibreOffice looks the string up by:

* ``.ui`` dialog and panel definitions under ``share/config/soffice.cfg``: every element marked
  ``translatable="yes"`` carries its gettext context; the domain is the file's
  ``<interface domain=...>``. Exact keys.
* code strings (the ``.hrc`` tables compiled into the libraries): ``NC_("CTX", "msgid")`` puts the
  context and the msgid into the libraries' read-only data as two NUL-terminated strings, usually
  next to each other; a table of entries sharing one context stores the context once, followed by
  its msgids. Every identifier-like string (the context form) is paired with the non-identifier
  strings that follow it up to the next identifier-like string (at most 800) and the two before it. A wrong pair is never looked up, so it is
  inert; a missed pair leaves that string in English. Coverage is measured, not assumed (the
  Arabic chrome share P0.13 and the tagged cell's comparison).
* the registry: every localized property value in the system layer's ``.xcd`` files
  (``xml:lang="en-US"``: menu, command, toolbar and window-state labels) becomes a value in a
  generated ``res/registry_<lang>.xcd`` with the same node path.

Two transforms:

* ``pseudo_ar``: Arabic-script letters of matched length (one Arabic letter per Latin letter, a
  fixed map), keeping placeholders (``%1``, ``%PRODUCTNAME``, ``$(ARG1)``, ``{0}``), mnemonic
  marks (``~``, ``_``), digits, punctuation, whitespace and Latin acronyms (two or more capitals).
  It stands in for the shipped Arabic catalogs, which are a download the program owner approves.
* ``tag``: the tagged pseudo-catalog of P0.8 for registry strings (``[r]‖`` + text); gettext
  strings are tagged by LibreOffice's own KeyID UI language ``qtz`` (each shown as a five-character
  key, U+2016 and the English text), which needs no catalog.

Writes: ``<out>/all.mo`` (one gettext catalog with every pair; the domains are symlinks to it),
``<out>/registry_ar.xcd``, ``<out>/registry_qtz.xcd``, ``<out>/catalog-stats.json``.
Seed: none needed (deterministic).
"""

from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

LO = Path("/usr/lib/libreoffice")
REGISTRY = Path("/etc/libreoffice/registry")
OOR = "http://openoffice.org/2001/registry"
XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# One Arabic letter per Latin letter (case-insensitive); five of the 26 targets do not join to
# the left (alef, dal, ra, zay and waw), roughly the
# share in running Arabic text, so words break into joined groups as real Arabic does.
AR_MAP = dict(zip(
    "abcdefghijklmnopqrstuvwxyz",
    ["ا", "ب", "ك", "د", "ع", "ف", "غ", "ه", "ي",
     "ج", "خ", "ل", "م", "ن", "و", "ث", "ق", "ر",
     "س", "ت", "ض", "ظ", "ش", "ص", "ط", "ز"],
))
PROTECT = re.compile(
    r"%[A-Z][A-Z0-9_]*%?"        # %PRODUCTNAME, %FILENAME% style
    r"|%\d+|%[-+0-9.]*l?[sduxfgc]|%%"  # printf and %1
    r"|\$\([A-Za-z0-9_]+\)|\$[0-9]+|\$[A-Z][A-Z0-9_]*\$?"  # $(ARG1), $1, $NAME$
    r"|\{[^{}]{0,40}\}"           # {0}, {name}
    r"|<[^<>]{1,80}>"             # markup
    r"|&[a-z]+;|&#\d+;"           # entities
    r"|\\[nt]"                    # escapes
    r"|\b[A-Z][A-Z0-9]+\b"        # acronyms (PDF, URL, CSV, A4)
    r"|https?://\S+"
)
IDENT = re.compile(rb"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
STRING = re.compile(rb"(?<=\x00)(?:[\x20-\x7e]|[\xc2-\xf4][\x80-\xbf]{1,3}){1,400}(?=\x00)")
TAG_REG = "[r]‖"
# Localized registry values that are not interface text: keyboard shortcuts (command URLs per
# language; the shipped Arabic catalog has no overrides, so Ctrl+S stays Save), and any value that
# is a command, URL, path or identifier. Transforming them would break the application, not
# translate it (debug job 1123: Ctrl+S stopped saving in the Arabic cell).
NON_TEXT_COMPONENTS = {"Accelerators"}
NON_TEXT = re.compile(r"^\s*(?:\.uno:|slot:|macro:|service:|private:|vnd\.|https?:|file:|mailto:|\$\(|/"
                      r"|[A-Za-z0-9_.-]+\.(?:xml|png|svg|xcd|ui|so|dll)$)|^(?=[^ ~]*[0-9_.:])[A-Za-z0-9_:.\-]+$")


def pseudo_ar(text: str) -> str:
    out = []
    pos = 0
    for m in PROTECT.finditer(text):
        out.append(_map_letters(text[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(_map_letters(text[pos:]))
    return "".join(out)


def _map_letters(s: str) -> str:
    return "".join(AR_MAP.get(ch.lower(), ch) if ch.isascii() and ch.isalpha() else ch for ch in s)


def tag(text: str) -> str:
    return TAG_REG + text


def letters(s: str) -> int:
    return sum(1 for ch in s if ch.isalpha())


# ------------------------------------------------------------------------------------------
# sources


def ui_pairs() -> tuple[dict[tuple[str, str], str], dict]:
    """(context, msgid) -> domain from every .ui file."""
    pairs: dict[tuple[str, str], str] = {}
    files = 0
    errors = 0
    for path in sorted((LO / "share" / "config" / "soffice.cfg").rglob("*.ui")):
        files += 1
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            errors += 1
            continue
        domain = root.get("domain") or ""
        for el in root.iter():
            if el.get("translatable") != "yes":
                continue
            msgid = el.text or ""
            ctx = el.get("context")
            if not msgid.strip() or ctx is None:
                continue
            pairs[(ctx, msgid)] = domain
    return pairs, {"ui_files": files, "ui_parse_errors": errors, "ui_pairs": len(pairs)}


def library_strings(path: Path) -> list[bytes]:
    data = path.read_bytes()
    return [m.group(0) for m in STRING.finditer(data)]


def code_pairs() -> tuple[set[tuple[str, str]], dict]:
    pairs: set[tuple[str, str]] = set()
    libs = sorted(p for p in (LO / "program").iterdir()
                  if p.is_file() and (p.suffix == ".so" or ".so." in p.name))
    n_ctx = 0
    for lib in libs:
        strs = library_strings(lib)
        is_id = [bool(IDENT.match(s)) for s in strs]
        for i, s in enumerate(strs):
            if not is_id[i]:
                continue
            n_ctx += 1
            ctx = s.decode("utf-8", "replace")
            # a table (NC_ entries of one array share one context string, emitted once) runs until
            # the next context-like string; a single entry's msgid sits next to its context
            following = []
            for j in range(i + 1, min(i + 801, len(strs))):
                if is_id[j]:
                    break
                following.append(j)
            for j in following + [i - 1, i - 2]:
                if j < 0 or is_id[j]:
                    continue
                cand = strs[j]
                try:
                    msg = cand.decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if letters(msg) == 0 or len(msg) > 300:
                    continue
                pairs.add((ctx, msg))
    return pairs, {"libraries": len(libs), "context_candidates": n_ctx, "code_pairs": len(pairs)}


# ------------------------------------------------------------------------------------------
# gettext .mo writer (GNU format, little endian); keys are "ctxt\x04msgid"


def write_mo(path: Path, entries: dict[str, str]) -> None:
    header = "Content-Type: text/plain; charset=UTF-8\nPlural-Forms: nplurals=1; plural=0;\n"
    items = sorted({"": header, **entries}.items(), key=lambda kv: kv[0].encode())
    n = len(items)
    o_off, t_off = 28, 28 + 8 * n
    data_off = 28 + 16 * n
    ids = bytearray()
    strs = bytearray()
    otab, ttab = [], []
    for k, _ in items:
        kb = k.encode()
        otab.append((len(kb), data_off + len(ids)))
        ids += kb + b"\0"
    base = data_off + len(ids)
    for _, v in items:
        vb = v.encode()
        ttab.append((len(vb), base + len(strs)))
        strs += vb + b"\0"
    out = bytearray(struct.pack("<7I", 0x950412DE, 0, n, o_off, t_off, 0, data_off))
    for x in otab:
        out += struct.pack("<2I", *x)
    for x in ttab:
        out += struct.pack("<2I", *x)
    out += ids + strs
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(out))


# ------------------------------------------------------------------------------------------
# registry


def registry_localized(files: list[Path]) -> tuple[list[tuple[str, str, list[tuple[str, str | None]], str, str]], dict]:
    """Every (package, component, node path with ops, prop, en-US value) in the given .xcd files."""
    out = []
    for f in files:
        try:
            root = ET.parse(f).getroot()
        except ET.ParseError:
            continue
        for comp in root.findall(f"{{{OOR}}}component-data"):
            pkg = comp.get(f"{{{OOR}}}package")
            name = comp.get(f"{{{OOR}}}name")
            if name in NON_TEXT_COMPONENTS:
                continue

            def walk(el, path):
                for child in el:
                    tagname = child.tag.split("}")[-1]
                    if tagname == "node":
                        walk(child, path + [(child.get(f"{{{OOR}}}name"), child.get(f"{{{OOR}}}op"))])
                    elif tagname == "prop":
                        pname = child.get(f"{{{OOR}}}name")
                        if pname == "ooSetupFactoryUIName" and not any("database" in (n or "") for n, _ in path):
                            # the shipped Arabic catalog leaves the Calc, Impress and Writer factory
                            # names (window titles) in English; only Base's are translated
                            continue
                        for val in child.findall("value"):
                            if val.get(XML_LANG) == "en-US" and (val.text or "").strip() and not NON_TEXT.match(val.text):
                                out.append((pkg, name, path, child.get(f"{{{OOR}}}name"), val.text))
            walk(comp, [])
    return out, {"registry_files": len(files), "localized_values": len(out)}


def xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def write_res_xcd(path: Path, values, lang: str, transform) -> int:
    """A res-layer .xcd with one localized value per source value (set members fused)."""
    tree: dict = {}
    for pkg, comp, nodes, prop, text in values:
        cur = tree.setdefault((pkg, comp), {})
        for name, op in nodes:
            cur = cur.setdefault(("node", name, "fuse" if op else None), {})
        cur[("prop", prop, None)] = transform(text)
    lines = ['<?xml version="1.0"?>',
             '<oor:data xmlns:xs="http://www.w3.org/2001/XMLSchema" '
             'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:oor="http://openoffice.org/2001/registry">']
    count = 0

    def emit(d, depth):
        nonlocal count
        for key, val in d.items():
            kind, name, op = key
            if kind == "prop":
                lines.append(f'{"  " * depth}<prop oor:name="{xml_escape(name)}"><value xml:lang="{lang}">'
                             f'{xml_escape(val)}</value></prop>')
                count += 1
            else:
                opattr = f' oor:op="{op}"' if op else ""
                lines.append(f'{"  " * depth}<node oor:name="{xml_escape(name)}"{opattr}>')
                emit(val, depth + 1)
                lines.append(f'{"  " * depth}</node>')

    for (pkg, comp), d in tree.items():
        lines.append(f'<oor:component-data oor:package="{pkg}" oor:name="{comp}">')
        emit(d, 1)
        lines.append("</oor:component-data>")
    lines.append("</oor:data>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return count


def build(out: Path) -> dict:
    t0 = time.monotonic()
    out.mkdir(parents=True, exist_ok=True)
    stats: dict = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    ui, s1 = ui_pairs()
    stats.update(s1)
    code, s2 = code_pairs()
    stats.update(s2)
    entries: dict[str, str] = {}
    domains = sorted({d for d in ui.values() if d})
    for ctx, msg in list(ui) + sorted(code):
        entries[f"{ctx}\x04{msg}"] = pseudo_ar(msg)
    write_mo(out / "all.mo", entries)
    (out / "code-pairs.tsv").write_text(
        "\n".join(f"{c}\t{m}" for c, m in sorted(code) if not any(x in c + m for x in "\t\n")), encoding="utf-8")
    stats["mo_entries"] = len(entries)
    stats["mo_sha256"] = hashlib.sha256((out / "all.mo").read_bytes()).hexdigest()
    stats["ui_domains"] = domains
    reg_files = sorted(REGISTRY.glob("*.xcd")) + sorted((REGISTRY / "res").glob("*en-US*.xcd"))
    values, s3 = registry_localized(reg_files)
    stats.update(s3)
    stats["registry_ar_values"] = write_res_xcd(out / "registry_ar.xcd", values, "ar", pseudo_ar)
    stats["registry_qtz_values"] = write_res_xcd(out / "registry_qtz.xcd", values, "qtz", tag)
    for f in ("registry_ar.xcd", "registry_qtz.xcd"):
        stats[f + "_sha256"] = hashlib.sha256((out / f).read_bytes()).hexdigest()
    # matched-length check on every generated value
    lens = [(len(m.split("\x04", 1)[1]), len(v)) for m, v in entries.items()]
    stats["matched_length_all"] = all(a == b for a, b in lens)
    sample = [k.split("\x04", 1)[1] for k in list(entries)[:: max(1, len(entries) // 2000)]]
    ar_letters = sum(sum(1 for ch in pseudo_ar(s) if "؀" <= ch <= "ۿ") for s in sample)
    all_letters = sum(letters(s) for s in sample)
    stats["sample_share_letters_arabic"] = round(ar_letters / all_letters, 4) if all_letters else None
    stats["examples"] = {s: pseudo_ar(s) for s in ("~File", "Save ~As...", "Sheet %1 of %2", "Default Page Style",
                                                   "%PRODUCTNAME Calc", "English (USA)", "Insert PDF")}
    stats["seconds"] = round(time.monotonic() - t0, 1)
    (out / "catalog-stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))
    return stats


if __name__ == "__main__":
    s = build(Path(sys.argv[1]))
    print(json.dumps({k: v for k, v in s.items() if k != "examples"}, ensure_ascii=False))
