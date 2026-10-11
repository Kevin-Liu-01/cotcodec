#!/usr/bin/env python3
"""S2 v4 P0.2-P0.3: the derived image and its cell images, built offline without host root.

Registration ``s2-arabic-cua-locale-v4`` P0.2 and P0.3 (decision D80 (iv)). Runs inside the
``cotcodec-q2-vmprobe`` container (Ubuntu 22.04: qemu-utils 6.2, e2fsprogs 1.46.5, fdisk, dpkg,
Python 3.10; ``infra/q2-mutation/vmprobe/Dockerfile``) as the host user, ``--network=none``,
read-only root, no capabilities, through ``infra/slurm/host-single-node/s2v4-cpu.sbatch``. No
step needs root: the disk is copied to a sparse raw file with ``qemu-img``, the guest's ext4
root filesystem is edited in that file with ``debugfs -w`` (the image file, never a device or a
mount), checked with ``e2fsck -fn`` and converted back to a standalone qcow2.

The derived base image ``D`` is the certified OSWorld disk (HF ``xlangai/ubuntu_osworld``
``a5d9c3ea``, ``Ubuntu.qcow2`` sha256 ``6bf667a8...``) plus what installing the three official
packages fetched by ``fetch_langpacks.py`` puts on disk:

* every file, directory and symlink of each package's data archive (``dpkg-deb --fsys-tarfile``),
  with the archive's modes, owners and modification times; a path that already exists as a
  file is refused (a package install would not overwrite another package's file here), an
  existing directory is left as it is (dpkg does not touch it), and a path whose parent chain
  in the image holds a symlink is refused (no path is resolved through a link);
* the four configuration copies that ``libreoffice-l10n-ar``'s postinst makes with ``ucf``
  (the files LibreOffice actually reads: ``/usr/lib/libreoffice/share/registry`` is a symlink to
  ``/etc/libreoffice/registry``); the pairs are read from the package's own postinst and must
  equal ``UCF_PAIRS``.

Not done, and recorded: the language packs' postinst (``locale-gen --keep-existing ar``: no
Arabic system locale is generated, the system locale stays ``en_US.UTF-8`` in every cell, and
neither LibreOffice's nor GTK's catalogs need one) and the package databases (``dpkg``'s status
and ``ucf``'s hash file are not edited, so ``dpkg -l`` in the guest does not list the three
packages; ``image-manifest.json`` lists every file written instead).

Each cell image is ``D`` plus the cell's files and nothing else:

* every cell: the selector ``/etc/libreoffice/registry/zz-s2v4-cell.xcd`` (``selector_xcd``),
  in the system configuration layer that both ``xcsxcu:`` and ``res:`` read; it sorts after
  every package file, and its values are finalized, so the user profile cannot override them;
* PL: also every toolbar definition under ``share/config/soffice.cfg/modules/*/toolbar`` whose
  items the seeded shuffle reorders (``shuffled_toolbar``, the pilot's function and key).

Every cell image is checked block by block against ``D``: each 4 KiB block of the root
filesystem that differs is classified (``classify_blocks``) as data of a file the cell writes,
a directory the cell edits, the inode-table block of an inode the cell writes or removes, a
block or inode bitmap, or a superblock or group-descriptor copy; any other changed block fails
the build. The cell images and ``D`` are written as standalone qcow2 files (no backing file),
each checked against its raw source with ``qemu-img compare`` and pinned by SHA-256.

Usage (inside the container):
  python3 -m harness.s2_locale.image_build build --certified /ro/vm/Ubuntu.qcow2
      --debs /inputs/debs --out /out [--cells E,A,ER,AR,PL,AD] [--parallel 3]
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "s2v4-image-build-v1"
# The certified disk (action-path v2 section 2.1; harness/q2_stage1/lane.py QCOW2_SHA256).
CERTIFIED_SHA256 = "6bf667a852b3c307f61d9f09c42559351f45e0607e428b4997becf534cf4d313"
CERTIFIED_BYTES = 24_460_197_888
CERTIFIED_VIRTUAL = 53_687_091_200
# Its GPT root partition (infra/q2-mutation/vmprobe facts, job 378; re-read from the GPT here).
ROOT_START_SECTOR = 1_054_720
ROOT_SECTORS = 61_857_792
SECTOR = 512
FS_BLOCK = 4096
# The three archives fetched under D80 (iv) (program/evidence/2026-10-11/s2v4-image/fetch/).
DEBS: tuple[tuple[str, str, int, str], ...] = (
    ("libreoffice-l10n-ar_7.3.7-0ubuntu0.22.04.4_all.deb",
     "765339432f140aede4af39c8cb2b2ab87077abccba768a14cb9da387a2b6a9cd", 663_804,
     "libreoffice-l10n-ar"),
    ("language-pack-ar-base_22.04+20230801_all.deb",
     "d6503a116a4a73d7a6fecac635f50efce962b3a05ec1f2312db6c28bab9cf057", 151_600,
     "language-pack-ar-base"),
    ("language-pack-gnome-ar-base_22.04+20230801_all.deb",
     "13e8cd8a3dbd3bd3069b76f5f245c7d9f536c9011b58af099cb4966ac0c45f15", 930_704,
     "language-pack-gnome-ar-base"),
)  # fmt: skip
UCF_PAIRS: tuple[tuple[str, str], ...] = (
    ("/usr/lib/libreoffice/share/.registry/Langpack-ar.xcd",
     "/etc/libreoffice/registry/Langpack-ar.xcd"),
    ("/usr/lib/libreoffice/share/.registry/res/fcfg_langpack_ar.xcd",
     "/etc/libreoffice/registry/res/fcfg_langpack_ar.xcd"),
    ("/usr/lib/libreoffice/share/.registry/res/registry_ar.xcd",
     "/etc/libreoffice/registry/res/registry_ar.xcd"),
    ("/usr/lib/libreoffice/share/.registry/ctl_ar.xcd",
     "/etc/libreoffice/registry/ctl_ar.xcd"),
)  # fmt: skip
SELECTOR_PATH = "/etc/libreoffice/registry/zz-s2v4-cell.xcd"
TOOLBAR_ROOT = "/usr/lib/libreoffice/share/config/soffice.cfg/modules"
LO_ROOT = "/usr/lib/libreoffice"
CELL_MTIME = 1_702_252_800  # 2023-12-11T00:00:00Z, the l10n archive's own date
SEED = 42
# The Phase 1 cells and the Phase 0 layout-by-language cell (P7). S, the stock cell, is the
# certified disk itself.
CELLS = ("E", "A", "ER", "AR", "PL", "AD")
SAFE_PATH = re.compile(r"^/[A-Za-z0-9._+@/-]+$")

XCD_HEAD = ('<?xml version="1.0"?>\n<oor:data xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'xmlns:oor="http://openoffice.org/2001/registry">\n')  # fmt: skip
XCD_TAIL = "</oor:data>\n"
TB_ITEM = re.compile(r"(<toolbar:toolbar(?:item|separator)\b[^>]*/>)")


class BuildError(RuntimeError):
    """A build step or check failed; no image from this run may be used."""


# --------------------------------------------------------------------------- cell content


def _prop(name: str, value: str) -> str:
    return f'<prop oor:name="{name}" oor:finalized="true"><value>{value}</value></prop>'


def _comp(package: str, name: str, body: str) -> str:
    return (f'<oor:component-data oor:package="{package}" oor:name="{name}">{body}'
            "</oor:component-data>\n")  # fmt: skip


# Every other configuration file of the derived images' system layer. The selector declares a
# dependency on each, so configmgr reads it last in the layer and its finalized values win there.
# Development smoke 1197 (dev split): without these declarations the language pack's ctl_ar.xcd,
# read after the selector, set CTLFont true in every derived cell, and E showed the two
# text-direction buttons that S does not (E against S: 1,398 and 1,399 px on the Calc and Writer
# dev tasks). Only main is required; the rest are optional, as pdfimport.xcd declares its own.
LAYER_FILES = ("Langpack-ar", "Langpack-en-US", "calc", "ctl_ar", "draw", "gnome", "graphicfilter",
               "impress", "lingucomponent", "math", "ogltrans", "pdfimport", "pyuno", "writer",
               "xsltfilter")  # fmt: skip
SELECTOR_DEPENDENCIES = ('<dependency file="main"/>\n' + "".join(
    f'<dependency file="{name}" optional="true"/>\n' for name in LAYER_FILES))


def selector_xcd(cell: str) -> str:
    """The cell's selector: the S2 v3 pilot's values (capture.py ``selector``) after a block of
    dependency declarations that makes the system layer read it last (``LAYER_FILES``).

    Text: both interface-language keys (``ooLocale`` for the gettext catalogs, ``UILocale``
    for the registry labels). Layout: the finalized ``UIMirroring`` key (absent in AD, whose
    layout follows the language). Pins in every cell: ``CTLFont`` false (over the language
    pack's ``ctl_ar.xcd``), Calc's default sheet prefix "Sheet" and English function names.
    ``ooSetupSystemLocale`` is not set (the system locale, ``en_US.UTF-8``, in every cell)."""
    if cell not in CELLS:
        raise BuildError(f"unknown cell {cell}")
    locale = "ar" if cell in ("A", "AR", "AD") else "en-US"
    mirror = {"ER": "true", "AR": "true", "AD": None}.get(cell, "false")
    setup = '<node oor:name="L10N">' + _prop("ooLocale", locale) + "</node>"
    ling = '<node oor:name="General">' + _prop("UILocale", locale) + "</node>"
    ctl = '<node oor:name="I18N"><node oor:name="CTL">' + _prop("CTLFont", "false")
    if mirror is not None:
        ctl += _prop("UIMirroring", mirror)
    ctl += "</node></node>"
    calc = ('<node oor:name="Defaults"><node oor:name="Sheet">' + _prop("SheetPrefix", "Sheet")
            + "</node></node>" + '<node oor:name="Formula"><node oor:name="Syntax">'
            + _prop("EnglishFunctionName", "true") + "</node></node>")  # fmt: skip
    body = (_comp("org.openoffice", "Setup", setup)
            + _comp("org.openoffice.Office", "Linguistic", ling)
            + _comp("org.openoffice.Office", "Common", ctl)
            + _comp("org.openoffice.Office", "Calc", calc))  # fmt: skip
    return XCD_HEAD + SELECTOR_DEPENDENCIES + body + XCD_TAIL


def pilot_selector(cell: str) -> str:
    """The selector without its dependency block: the S2 v3 pilot's bytes."""
    return selector_xcd(cell).replace(SELECTOR_DEPENDENCIES, "", 1)


def shuffled_toolbar(text: str, key: str) -> str:
    """A toolbar definition with its items (and separators) in a seeded order (the pilot's)."""
    items = TB_ITEM.findall(text)
    if len(items) < 2:
        return text
    order = sorted(range(len(items)),
                   key=lambda i: hashlib.sha256(f"{SEED}:{key}:{i}".encode()).hexdigest())
    it = iter([items[i] for i in order])
    return TB_ITEM.sub(lambda m: next(it), text)


def toolbar_key(image_path: str) -> str:
    """The pilot's shuffle key: the path relative to ``/usr/lib/libreoffice``."""
    rel = PurePosixPath(image_path).relative_to(LO_ROOT)
    return str(rel)


# --------------------------------------------------------------------------- packages


@dataclass
class Member:
    path: str  # absolute image path
    kind: str  # "dir", "file" or "symlink"
    mode: int  # permission bits
    uid: int
    gid: int
    mtime: int
    data: bytes = b""
    target: str = ""
    package: str = ""


def read_deb_members(tar_bytes: bytes, package: str) -> list[Member]:
    """The data archive's entries (``dpkg-deb --fsys-tarfile`` output) in archive order."""
    out: list[Member] = []
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:") as tar:
        for info in tar.getmembers():
            name = info.name
            if name in (".", "./"):
                continue
            path = "/" + name[2:] if name.startswith("./") else "/" + name.lstrip("/")
            path = path.rstrip("/")
            if not SAFE_PATH.fullmatch(path) or ".." in PurePosixPath(path).parts:
                raise BuildError(f"{package}: unsafe archive path {name!r}")
            if info.isdir():
                kind, data, target = "dir", b"", ""
            elif info.isfile():
                handle = tar.extractfile(info)
                kind, data, target = "file", handle.read() if handle else b"", ""
            elif info.issym():
                kind, data, target = "symlink", b"", info.linkname
            else:
                raise BuildError(f"{package}: unsupported archive entry {name!r} ({info.type!r})")
            out.append(Member(path, kind, info.mode & 0o7777, info.uid, info.gid,
                              int(info.mtime), data, target, package))  # fmt: skip
    return out


UCF_RE = re.compile(r'ucf --three-way "([^"]+)" "([^"]+)"')


def ucf_pairs(postinst: str) -> list[tuple[str, str]]:
    return UCF_RE.findall(postinst)


# --------------------------------------------------------------------------- planning


@dataclass
class Entry:
    ino: int
    mode: int  # full i_mode (type and permission bits)
    uid: int
    gid: int
    size: int

    @property
    def is_dir(self) -> bool:
        return (self.mode & 0o170000) == 0o040000

    @property
    def is_link(self) -> bool:
        return (self.mode & 0o170000) == 0o120000


LS_P = re.compile(r"^/(\d+)/(\d+)/(\d+)/(\d+)/(.*)/(\d*)/$")


def parse_ls_p(text: str) -> dict[str, Entry]:
    """``debugfs ls -p`` lines (``/ino/mode/uid/gid/name/size/``) of one directory."""
    out: dict[str, Entry] = {}
    for line in text.splitlines():
        m = LS_P.match(line.strip())
        if not m:
            continue
        ino, mode, uid, gid, name, size = m.groups()
        if name in (".", "..") or int(ino) == 0:
            continue
        out[name] = Entry(int(ino), int(mode, 8), int(uid), int(gid), int(size or 0))
    return out


def split_debugfs_output(text: str) -> dict[str, str]:
    """Output of ``debugfs -f`` keyed by the echoed command (``debugfs: <command>``)."""
    out: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        if line.startswith("debugfs: "):
            current = line[len("debugfs: "):].strip()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


@dataclass
class Op:
    kind: str  # mkdir, write, symlink, rm
    path: str
    mode: int = 0
    uid: int = 0
    gid: int = 0
    mtime: int = CELL_MTIME
    data: bytes = b""
    target: str = ""
    source: str = ""  # package or cell


@dataclass
class Plan:
    ops: list[Op] = field(default_factory=list)
    skipped_dirs: list[str] = field(default_factory=list)
    shared_dirs: list[str] = field(default_factory=list)

    def written(self) -> list[Op]:
        return [op for op in self.ops if op.kind in ("write", "symlink", "mkdir")]


def parents(path: str) -> list[str]:
    p = PurePosixPath(path)
    return [str(x) for x in reversed(p.parents) if str(x) != "/"]


def plan_install(members: Sequence[Member], ucf: Sequence[tuple[str, str]],
                 listing: Mapping[str, Mapping[str, Entry]]) -> Plan:  # fmt: skip
    """Ordered operations for unpacking ``members`` and making the ``ucf`` copies.

    ``listing`` maps an image directory to its entries (``parse_ls_p``); a directory absent
    from ``listing`` is one that does not exist in the image (it must then be created by an
    earlier operation of this plan)."""
    plan = Plan()
    created: dict[str, str] = {}  # path -> kind, made by this plan
    by_path = {m.path: m for m in members}

    def existing(path: str) -> Entry | None:
        parent, name = str(PurePosixPath(path).parent), PurePosixPath(path).name
        return (listing.get(parent) or {}).get(name)

    def check_parents(path: str) -> None:
        for anc in parents(path):
            ent = existing(anc)
            if ent is not None:
                if ent.is_link:
                    raise BuildError(f"{path}: ancestor {anc} is a symlink in the image")
                if not ent.is_dir:
                    raise BuildError(f"{path}: ancestor {anc} is not a directory")
            elif created.get(anc) != "dir":
                raise BuildError(f"{path}: ancestor {anc} neither exists nor is created first")

    for m in members:
        if not SAFE_PATH.fullmatch(m.path):
            raise BuildError(f"unsafe path {m.path!r}")
        check_parents(m.path)
        ent = existing(m.path)
        if m.kind == "dir":
            if ent is not None:
                if not ent.is_dir:
                    raise BuildError(f"{m.path}: exists in the image and is not a directory")
                plan.skipped_dirs.append(m.path)
                continue
            if created.get(m.path) == "dir":
                # A directory an earlier package of this install created (the two language
                # packs share /usr/share/locale-langpack/ar/LC_MESSAGES): dpkg shares it too.
                plan.shared_dirs.append(m.path)
                continue
            if m.path in created:
                raise BuildError(f"{m.path}: a directory over a {created[m.path]} of this install")
            plan.ops.append(Op("mkdir", m.path, 0o040000 | m.mode, m.uid, m.gid, m.mtime,
                               source=m.package))  # fmt: skip
            created[m.path] = "dir"
            continue
        if ent is not None or m.path in created:
            raise BuildError(f"{m.path}: already exists in the image; refusing to overwrite")
        if m.kind == "file":
            plan.ops.append(Op("write", m.path, 0o100000 | m.mode, m.uid, m.gid, m.mtime,
                               data=m.data, source=m.package))  # fmt: skip
        else:
            plan.ops.append(Op("symlink", m.path, 0o120777, m.uid, m.gid, m.mtime,
                               target=m.target, source=m.package))  # fmt: skip
        created[m.path] = m.kind
    for src, dst in ucf:
        if src not in by_path or by_path[src].kind != "file":
            raise BuildError(f"ucf source {src} is not a file of the archives")
        check_parents(dst)
        if existing(dst) is not None or dst in created:
            raise BuildError(f"ucf target {dst} already exists")
        s = by_path[src]
        plan.ops.append(Op("write", dst, 0o100644, 0, 0, s.mtime, data=s.data, source="ucf"))
        created[dst] = "file"
    return plan


def plan_cell(cell: str, listing: Mapping[str, Mapping[str, Entry]],
              toolbars: Mapping[str, bytes] | None = None) -> Plan:  # fmt: skip
    """The cell's operations on the derived base: its selector (and PL's toolbars)."""
    plan = Plan()
    parent = str(PurePosixPath(SELECTOR_PATH).parent)
    if PurePosixPath(SELECTOR_PATH).name in (listing.get(parent) or {}):
        raise BuildError(f"{SELECTOR_PATH} already exists in the base")
    plan.ops.append(Op("write", SELECTOR_PATH, 0o100644, 0, 0, CELL_MTIME,
                       data=selector_xcd(cell).encode("utf-8"), source=cell))  # fmt: skip
    if cell == "PL":
        if not toolbars:
            raise BuildError("PL needs the base's toolbar definitions")
        for path in sorted(toolbars):
            new = shuffled_toolbar(toolbars[path].decode("utf-8"), toolbar_key(path)).encode()
            if new == toolbars[path]:
                continue
            ent = (listing.get(str(PurePosixPath(path).parent)) or {}).get(PurePosixPath(path).name)
            if ent is None or (ent.mode & 0o170000) != 0o100000:
                raise BuildError(f"{path}: not a regular file in the base")
            plan.ops.append(Op("rm", path, source=cell))
            plan.ops.append(Op("write", path, ent.mode, ent.uid, ent.gid, CELL_MTIME, data=new,
                               source=cell))  # fmt: skip
    return plan


def debugfs_script(plan: Plan, stage: Path) -> str:
    """The ``debugfs -w -f`` script; file contents are staged under ``stage``."""
    lines: list[str] = []
    for i, op in enumerate(plan.ops):
        p = PurePosixPath(op.path)
        if not SAFE_PATH.fullmatch(op.path):
            raise BuildError(f"unsafe path {op.path!r}")
        if op.kind == "rm":
            lines.append(f"rm {op.path}")
            continue
        if op.kind == "mkdir":
            lines.append(f"mkdir {op.path}")
        elif op.kind == "write":
            local = stage / f"{i:06d}"
            local.write_bytes(op.data)
            lines.append(f"cd {p.parent}")
            lines.append(f"write {local} {p.name}")
            lines.append("cd /")
        elif op.kind == "symlink":
            if not re.fullmatch(r"[A-Za-z0-9._+@/-]+", op.target):
                raise BuildError(f"unsafe symlink target {op.target!r}")
            lines.append(f"symlink {op.path} {op.target}")
        else:
            raise BuildError(f"unknown op {op.kind}")
        if op.kind != "symlink":
            lines.append(f"sif {op.path} mode 0{op.mode:o}")
        lines.append(f"sif {op.path} uid {op.uid}")
        lines.append(f"sif {op.path} gid {op.gid}")
        for f in ("atime", "mtime", "ctime", "crtime"):
            lines.append(f"sif {op.path} {f} @{op.mtime}")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------- block checks


def gpt_root(sfdisk_json: Mapping[str, Any]) -> tuple[int, int]:
    parts = sfdisk_json["partitiontable"]["partitions"]
    root = max(parts, key=lambda p: int(p["size"]))
    return int(root["start"]), int(root["size"])


@dataclass
class Layout:
    """Where ext4 keeps its metadata (from ``dumpe2fs``)."""

    inodes_per_group: int
    inode_size: int
    block_size: int
    sb_gdt: set[int] = field(default_factory=set)
    block_bitmaps: set[int] = field(default_factory=set)
    inode_bitmaps: set[int] = field(default_factory=set)
    inode_tables: list[tuple[int, int, int]] = field(default_factory=list)  # (group, first, last)

    def inodes_in_table_block(self, block: int) -> list[int] | None:
        per_block = self.block_size // self.inode_size
        for group, first, last in self.inode_tables:
            if first <= block <= last:
                start = group * self.inodes_per_group + (block - first) * per_block + 1
                return list(range(start, start + per_block))
        return None


def _span(text: str) -> tuple[int, int]:
    a, _, b = text.partition("-")
    return int(a), int(b or a)


def parse_dumpe2fs(text: str) -> Layout:
    ipg = int(re.search(r"^Inodes per group:\s+(\d+)", text, re.M).group(1))
    isz = int(re.search(r"^Inode size:\s+(\d+)", text, re.M).group(1))
    bsz = int(re.search(r"^Block size:\s+(\d+)", text, re.M).group(1))
    lay = Layout(ipg, isz, bsz)
    group = -1
    for line in text.splitlines():
        m = re.match(r"^Group (\d+):", line)
        if m:
            group = int(m.group(1))
            continue
        for label in ("superblock at", "Group descriptors at", "Reserved GDT blocks at"):
            for m in re.finditer(label + r" (\d+(?:-\d+)?)", line):
                a, b = _span(m.group(1))
                lay.sb_gdt.update(range(a, b + 1))
        m = re.search(r"Block bitmap at (\d+)", line)
        if m:
            lay.block_bitmaps.add(int(m.group(1)))
        m = re.search(r"Inode bitmap at (\d+)", line)
        if m:
            lay.inode_bitmaps.add(int(m.group(1)))
        m = re.search(r"Inode table at (\d+)-(\d+)", line)
        if m and group >= 0:
            lay.inode_tables.append((group, int(m.group(1)), int(m.group(2))))
    if 0 not in lay.sb_gdt:
        lay.sb_gdt.add(0)  # the primary superblock lives in block 0 when the block size is 4 KiB
    return lay


def changed_blocks(a: Path, b: Path, offset: int, length: int, block: int = FS_BLOCK,
                   chunk: int = 4 << 20) -> list[int]:  # fmt: skip
    """Filesystem blocks (relative to ``offset``) whose bytes differ between ``a`` and ``b``.

    Holes read as zeros; a chunk that is a hole in both files is skipped (SEEK_DATA)."""

    def next_data(fd: int, pos: int) -> int:
        try:
            return os.lseek(fd, pos, os.SEEK_DATA)
        except OSError:  # ENXIO: no data at or after pos
            return offset + length

    out: list[int] = []
    with open(a, "rb") as fa, open(b, "rb") as fb:
        pos = 0  # partition-relative, always a multiple of chunk
        while pos < length:
            n = min(chunk, length - pos)
            nd = min(next_data(fa.fileno(), offset + pos), next_data(fb.fileno(), offset + pos))
            if nd >= offset + pos + n:
                if nd >= offset + length:
                    break
                pos = ((nd - offset) // chunk) * chunk
                continue
            fa.seek(offset + pos)
            fb.seek(offset + pos)
            xa, xb = fa.read(n), fb.read(n)
            xa += b"\0" * (n - len(xa))
            xb += b"\0" * (n - len(xb))
            if xa != xb:
                for j in range(0, n, block):
                    if xa[j:j + block] != xb[j:j + block]:
                        out.append((pos + j) // block)
            pos += n
    return out


def parse_icheck(text: str) -> dict[int, int | None]:
    out: dict[int, int | None] = {}
    for line in text.splitlines():
        m = re.match(r"^(\d+)\s+(\d+|<block not found>)\s*$", line.strip())
        if m:
            out[int(m.group(1))] = int(m.group(2)) if m.group(2).isdigit() else None
    return out


def parse_ncheck(text: str) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for line in text.splitlines():
        m = re.match(r"^(\d+)\s+(/.*)$", line.strip())
        if m:
            out.setdefault(int(m.group(1)), []).append(m.group(2))
    return out


def classify_blocks(blocks: Iterable[int], owner: Mapping[int, int | None],
                    paths: Mapping[int, Sequence[str]], layout: Layout,
                    intended: set[str], intended_dirs: set[str],
                    touched_inodes: set[int]) -> dict[str, Any]:  # fmt: skip
    """Every changed block must be explained by the cell's own writes."""
    kinds: dict[str, list[int]] = {k: [] for k in (
        "file_data", "directory", "inode_table", "block_bitmap", "inode_bitmap", "sb_gdt",
        "unexplained")}  # fmt: skip
    for blk in sorted(blocks):
        ino = owner.get(blk)
        if ino is not None:
            names = set(paths.get(ino, ()))
            if names & intended:
                kinds["file_data"].append(blk)
            elif names & intended_dirs:
                kinds["directory"].append(blk)
            else:
                kinds["unexplained"].append(blk)
            continue
        if blk in layout.sb_gdt:
            kinds["sb_gdt"].append(blk)
        elif blk in layout.block_bitmaps:
            kinds["block_bitmap"].append(blk)
        elif blk in layout.inode_bitmaps:
            kinds["inode_bitmap"].append(blk)
        else:
            inodes = layout.inodes_in_table_block(blk)
            if inodes is not None and set(inodes) & touched_inodes:
                kinds["inode_table"].append(blk)
            else:
                kinds["unexplained"].append(blk)
    counts = {k: len(v) for k, v in kinds.items()}
    return {"counts": counts, "ok": not kinds["unexplained"],
            "unexplained": kinds["unexplained"][:50]}  # fmt: skip


# --------------------------------------------------------------------------- tools


def run(argv: Sequence[str], timeout: float = 3600, check: bool = True,
        **kw: Any) -> subprocess.CompletedProcess:  # fmt: skip
    proc = subprocess.run(list(argv), capture_output=True, timeout=timeout, **kw)
    if check and proc.returncode != 0:
        err = proc.stderr
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        raise BuildError(f"{argv[0]} {argv[1] if len(argv) > 1 else ''} failed "
                         f"({proc.returncode}): {err[-800:]}")  # fmt: skip
    return proc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


class Image:
    """A raw disk file and its ext4 root partition at a byte offset (e2fsprogs ``?offset=``)."""

    def __init__(self, raw: Path, offset: int):
        self.raw = raw
        self.offset = offset
        self.dev = f"{raw}?offset={offset}"

    def debugfs(self, script: str, write: bool = False, timeout: float = 3600) -> tuple[str, str]:
        # Reads run with -n (no metadata checksum verification): the certified disk has one inode
        # whose checksum does not match (1214912, a VS Code file), and an inode scan (icheck,
        # ncheck) stops at it otherwise. Writes verify checksums as usual.
        argv = ["debugfs"] + (["-w"] if write else ["-n"]) + ["-f", "-", self.dev]
        proc = subprocess.run(argv, input=script.encode(), capture_output=True, timeout=timeout)
        return proc.stdout.decode(errors="replace"), proc.stderr.decode(errors="replace")

    def ls_dirs(self, dirs: Iterable[str]) -> dict[str, dict[str, Entry]]:
        dirs = sorted(set(dirs))
        out, err = self.debugfs("".join(f"ls -p {d}\n" for d in dirs))
        parts = split_debugfs_output(out)
        result: dict[str, dict[str, Entry]] = {}
        for d in dirs:
            text = parts.get(f"ls -p {d}", "")
            if text.strip():
                result[d] = parse_ls_p(text)
        return result

    def fsck(self) -> dict[str, Any]:
        proc = run(["e2fsck", "-fn", self.dev], check=False)
        text = (proc.stdout + proc.stderr).decode(errors="replace")
        return {"returncode": proc.returncode, "findings": fsck_findings(text),
                "tail": text.strip().splitlines()[-4:]}  # fmt: skip


def fsck_findings(text: str) -> list[str]:
    """The problems ``e2fsck -fn`` reports (pass headers, banner, warning and summary removed)."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if (not line or line.startswith(("Pass ", "e2fsck ")) or "still has errors" in line
                or re.match(r"^\S+: \d+/\d+ files", line)):  # fmt: skip
            continue
        out.append(line)
    return out


def fsck_same(result: Mapping[str, Any], baseline: Mapping[str, Any]) -> bool:
    """No operational error and exactly the baseline's findings (none new, none gone)."""
    return not (int(result["returncode"]) & 8) and result["findings"] == baseline["findings"]


def errors_of(stderr: str) -> list[str]:
    return [ln for ln in stderr.splitlines()
            if ln.strip() and not ln.startswith("debugfs ")]  # fmt: skip


def apply_plan(img: Image, plan: Plan, stage: Path) -> dict[str, Any]:
    stage.mkdir(parents=True, exist_ok=True)
    script = debugfs_script(plan, stage)
    (stage.parent / f"{stage.name}.debugfs").write_text(script)
    out, err = img.debugfs(script, write=True)
    errs = errors_of(err)
    if errs:
        raise BuildError(f"debugfs reported {len(errs)} errors: {errs[:5]}")
    return {"commands": script.count("\n"), "ops": len(plan.ops),
            "script_sha256": hashlib.sha256(script.encode()).hexdigest()}  # fmt: skip


def verify_plan(img: Image, plan: Plan, readback: Path) -> dict[str, Any]:
    """Every written path reads back with the planned bytes, mode, owner and target."""
    readback.mkdir(parents=True, exist_ok=True)
    final: dict[str, Op] = {}
    removed: set[str] = set()
    for op in plan.ops:
        if op.kind == "rm":
            removed.add(op.path)
            final.pop(op.path, None)
        else:
            final[op.path] = op
            removed.discard(op.path)
    listing = img.ls_dirs(str(PurePosixPath(p).parent) for p in list(final) + list(removed))
    script = []
    files = sorted(p for p, op in final.items() if op.kind == "write")
    for i, path in enumerate(files):
        script.append(f"dump {path} {readback / f'{i:06d}'}")
    links = sorted(p for p, op in final.items() if op.kind == "symlink")
    for path in links:
        script.append(f"stat {path}")
    out, err = img.debugfs("\n".join(script) + "\n")
    parts = split_debugfs_output(out)
    bad: list[str] = []
    manifest: list[dict[str, Any]] = []
    for path, op in sorted(final.items()):
        ent = (listing.get(str(PurePosixPath(path).parent)) or {}).get(PurePosixPath(path).name)
        if ent is None:
            bad.append(f"{path}: missing")
            continue
        if ent.mode != op.mode or ent.uid != op.uid or ent.gid != op.gid:
            bad.append(f"{path}: mode/owner {ent.mode:o} {ent.uid}:{ent.gid}")
        row = {"path": path, "kind": op.kind, "mode": f"{op.mode:o}", "uid": op.uid,
               "gid": op.gid, "source": op.source, "ino": ent.ino}  # fmt: skip
        if op.kind == "write":
            got = readback / f"{files.index(path):06d}"
            data = got.read_bytes() if got.is_file() else None
            if data != op.data:
                bad.append(f"{path}: content differs")
            row.update(size=len(op.data), sha256=hashlib.sha256(op.data).hexdigest())
        elif op.kind == "symlink":
            text = parts.get(f"stat {path}", "")
            m = re.search(r'Fast link dest: "([^"]*)"', text)
            if not m or m.group(1) != op.target:
                bad.append(f"{path}: link target {m.group(1) if m else None!r}")
            row.update(target=op.target)
        manifest.append(row)
    for path in removed:
        if (listing.get(str(PurePosixPath(path).parent)) or {}).get(PurePosixPath(path).name):
            bad.append(f"{path}: still present")
    shutil.rmtree(readback, ignore_errors=True)
    if bad:
        raise BuildError(f"readback failed on {len(bad)} paths: {bad[:5]}")
    return {"verified_paths": len(final), "manifest": manifest}


def to_qcow2(raw: Path, out: Path) -> dict[str, Any]:
    run(["qemu-img", "convert", "-f", "raw", "-O", "qcow2", "-o",
         "compat=1.1,cluster_size=65536", "-m", "8", str(raw), str(out)])  # fmt: skip
    cmp = run(["qemu-img", "compare", "-f", "raw", "-F", "qcow2", str(raw), str(out)],
              check=False)  # fmt: skip
    info = json.loads(run(["qemu-img", "info", "--output=json", str(out)]).stdout)
    if cmp.returncode != 0:
        raise BuildError(f"qemu-img compare {out}: {cmp.stdout.decode()[-300:]}")
    if info.get("backing-filename"):
        raise BuildError(f"{out} has a backing file")
    return {
        "path": out.name,
        "sha256": sha256_file(out),
        "bytes": out.stat().st_size,
        "virtual_size": info.get("virtual-size"),
        "format": info.get("format"),
        "cluster_size": info.get("cluster-size"),
        "compare": cmp.stdout.decode().strip(),
    }


def tool_versions() -> dict[str, str]:
    out = {}
    for name, argv in (("qemu-img", ["qemu-img", "--version"]), ("debugfs", ["debugfs", "-V"]),
                       ("sfdisk", ["sfdisk", "--version"]), ("dpkg-deb", ["dpkg-deb", "--version"]),
                       ("python", [sys.executable, "--version"])):  # fmt: skip
        proc = run(argv, check=False)
        text = (proc.stdout + proc.stderr).decode(errors="replace").strip().splitlines()
        out[name] = text[0] if text else ""
    pkgs = Path("/opt/vmprobe-packages.tsv")
    if pkgs.is_file():
        out["vmprobe_packages"] = pkgs.read_text().strip()
    return out


# --------------------------------------------------------------------------- build


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_debs(debs_dir: Path) -> tuple[list[Member], list[tuple[str, str]], list[dict]]:
    members: list[Member] = []
    ucf: list[tuple[str, str]] = []
    records = []
    for filename, sha, size, package in DEBS:
        path = debs_dir / filename
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != sha or len(data) != size:
            raise BuildError(f"{filename}: digest or size differs from the fetched archive")
        tar = run(["dpkg-deb", "--fsys-tarfile", str(path)]).stdout
        mem = read_deb_members(tar, package)
        ctrl_dir = Path(os.environ.get("TMPDIR", "/tmp")) / f"ctrl-{package}"
        shutil.rmtree(ctrl_dir, ignore_errors=True)
        run(["dpkg-deb", "-e", str(path), str(ctrl_dir)])
        postinst = (ctrl_dir / "postinst").read_text() if (ctrl_dir / "postinst").is_file() else ""
        pairs = ucf_pairs(postinst)
        ucf += pairs
        records.append({"filename": filename, "package": package, "sha256": sha, "bytes": size,
                        "members": len(mem), "files": sum(m.kind == "file" for m in mem),
                        "postinst_sha256": hashlib.sha256(postinst.encode()).hexdigest(),
                        "ucf_pairs": pairs,
                        "postinst_not_run": bool(postinst.strip())})  # fmt: skip
        members += mem
    if sorted(ucf) != sorted(UCF_PAIRS):
        raise BuildError(f"the postinst ucf pairs differ from UCF_PAIRS: {ucf}")
    return members, ucf, records


def base_listing_dirs(paths: Iterable[str]) -> set[str]:
    dirs: set[str] = {"/"}
    for p in paths:
        for anc in parents(p):
            dirs.add(anc)
        dirs.add(str(PurePosixPath(p).parent))
    return dirs


def diff_against(img: Image, ref: Path, length: int, layout: Layout,
                 manifest: Sequence[Mapping[str, Any]],
                 removed_inodes: Iterable[int] = ()) -> dict[str, Any]:  # fmt: skip
    """Classify every root-filesystem block of ``img`` that differs from ``ref``."""
    blocks = changed_blocks(ref, img.raw, img.offset, length)
    owner: dict[int, int | None] = {}
    paths: dict[int, list[str]] = {}
    batch = 200
    if blocks:
        script = "".join("icheck " + " ".join(map(str, blocks[i:i + batch])) + "\n"
                         for i in range(0, len(blocks), batch))  # fmt: skip
        owner = parse_icheck(img.debugfs(script)[0])
        inos = sorted({i for i in owner.values() if i})
        if inos:
            script = "".join("ncheck " + " ".join(map(str, inos[i:i + batch])) + "\n"
                             for i in range(0, len(inos), batch))  # fmt: skip
            paths = parse_ncheck(img.debugfs(script)[0])
    written = {str(r["path"]) for r in manifest}
    touched = {int(r["ino"]) for r in manifest} | set(removed_inodes)
    dirs = {str(PurePosixPath(p).parent) for p in written}
    dir_listing = img.ls_dirs({str(PurePosixPath(d).parent) for d in dirs})
    for d in dirs:
        ent = (dir_listing.get(str(PurePosixPath(d).parent)) or {}).get(PurePosixPath(d).name)
        if d == "/":
            touched.add(2)  # the root directory's inode
        elif ent is not None:
            touched.add(ent.ino)
    out = classify_blocks(blocks, owner, paths, layout, written, dirs, touched)
    out["blocks"] = len(blocks)
    return out


def build_cell(cell: str, base_raw: Path, work: Path, out: Path, offset: int, length: int,
               layout: Layout, toolbars: Mapping[str, bytes],
               baseline: Mapping[str, Any] | None = None) -> dict[str, Any]:  # fmt: skip
    t0 = time.time()
    raw = work / f"cell-{cell}.raw"
    run(["cp", "--sparse=always", str(base_raw), str(raw)])
    img = Image(raw, offset)
    targets = [SELECTOR_PATH] + (sorted(toolbars) if cell == "PL" else [])
    listing = img.ls_dirs(base_listing_dirs(targets))
    plan = plan_cell(cell, listing, toolbars if cell == "PL" else None)
    removed = [(listing.get(str(PurePosixPath(op.path).parent)) or {}).get(
        PurePosixPath(op.path).name) for op in plan.ops if op.kind == "rm"]  # fmt: skip
    applied = apply_plan(img, plan, work / f"stage-{cell}")
    fsck = img.fsck()
    if not fsck_same(fsck, baseline or {"findings": []}):
        raise BuildError(f"cell {cell}: e2fsck -fn differs from the baseline: "
                         f"{fsck['findings'][:5]}")
    verified = verify_plan(img, plan, work / f"readback-{cell}")
    classified = diff_against(img, base_raw, length, layout, verified["manifest"],
                              [e.ino for e in removed if e])  # fmt: skip
    if not classified["ok"]:
        raise BuildError(f"cell {cell}: unexplained changed blocks {classified['unexplained']}")
    qcow = to_qcow2(raw, out / f"s2v4-cell-{cell}.qcow2")
    raw.unlink()
    selector = selector_xcd(cell).encode()
    return {
        "cell": cell,
        "selector_path": SELECTOR_PATH,
        "selector_sha256": hashlib.sha256(selector).hexdigest(),
        "toolbar_files_rewritten": sum(1 for op in plan.ops if op.kind == "rm"),
        "applied": applied,
        "fsck": fsck,
        "verified_paths": verified["verified_paths"],
        "manifest": verified["manifest"],
        "changed_blocks": classified,
        "qcow2": qcow,
        "seconds": round(time.time() - t0, 1),
    }


def build(args: argparse.Namespace) -> dict[str, Any]:
    t0 = time.time()
    out, work = args.out, args.out / "work"
    work.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {"schema": SCHEMA, "t_start": time.time(), "tools": tool_versions()}
    log("checking the certified disk")
    certified = Path(args.certified)
    if not args.skip_certified_hash:
        digest = sha256_file(certified)
        if digest != CERTIFIED_SHA256:
            raise BuildError(f"certified disk digest {digest} is not the pinned one")
    if certified.stat().st_size != CERTIFIED_BYTES:
        raise BuildError("certified disk size differs")
    info = json.loads(run(["qemu-img", "info", "-U", "--output=json", str(certified)]).stdout)
    if info.get("virtual-size") != CERTIFIED_VIRTUAL:
        raise BuildError("certified virtual size differs")
    rec["certified"] = {"sha256": CERTIFIED_SHA256, "bytes": CERTIFIED_BYTES,
                        "virtual_size": CERTIFIED_VIRTUAL,
                        "hash_checked": not args.skip_certified_hash}  # fmt: skip
    log("reading the archives")
    members, ucf, debs = load_debs(Path(args.debs))
    rec["debs"] = debs
    log("converting the certified disk to raw")
    cert_raw = work / "certified.raw"
    run(["qemu-img", "convert", "-U", "-f", "qcow2", "-O", "raw", "-m", "8", str(certified),
         str(cert_raw)])  # fmt: skip
    table = json.loads(run(["sfdisk", "--json", str(cert_raw)]).stdout)
    start, size = gpt_root(table)
    if (start, size) != (ROOT_START_SECTOR, ROOT_SECTORS):
        raise BuildError(f"root partition {start}+{size} is not the pinned one")
    offset, length = start * SECTOR, size * SECTOR
    rec["root_partition"] = {"start_sector": start, "sectors": size, "offset": offset}
    cert = Image(cert_raw, offset)
    head = run(["dumpe2fs", "-h", cert.dev], check=False).stdout.decode(errors="replace")
    state = re.search(r"^Filesystem state:\s+(.+)$", head, re.M)
    features = re.search(r"^Filesystem features:\s+(.+)$", head, re.M)
    rec["filesystem"] = {"state": state.group(1).strip() if state else None,
                         "features": features.group(1).split() if features else None}  # fmt: skip
    if not state or state.group(1).strip() != "clean" or "needs_recovery" in head:
        raise BuildError(f"the root filesystem is not clean: {rec['filesystem']}")
    pre = cert.fsck()
    if int(pre["returncode"]) & 8:
        raise BuildError(f"e2fsck could not check the certified filesystem: {pre['tail']}")
    # The certified disk's own findings (one inode checksum mismatch in a VS Code file, inode
    # 1214912) are the baseline: every image built here must report exactly these, none new.
    rec["fsck_certified"] = pre
    log("copying the raw disk for the derived base")
    base_raw = work / "base.raw"
    run(["cp", "--sparse=always", str(cert_raw), str(base_raw)])
    img = Image(base_raw, offset)
    log("planning the install")
    targets = [m.path for m in members] + [dst for _, dst in ucf]
    listing = img.ls_dirs(base_listing_dirs(targets))
    plan = plan_install(members, ucf, listing)
    rec["install"] = {"ops": len(plan.ops), "skipped_existing_dirs": plan.skipped_dirs,
                      "shared_dirs": plan.shared_dirs,
                      "by_kind": {k: sum(op.kind == k for op in plan.ops)
                                  for k in ("mkdir", "write", "symlink")}}  # fmt: skip
    log(f"applying {len(plan.ops)} operations")
    rec["install"]["applied"] = apply_plan(img, plan, work / "stage-base")
    post = img.fsck()
    if not fsck_same(post, pre):
        raise BuildError(f"e2fsck -fn after the install differs from the certified baseline: "
                         f"{post['findings'][:5]}")  # fmt: skip
    rec["fsck_derived"] = post
    verified = verify_plan(img, plan, work / "readback-base")
    rec["install"]["verified_paths"] = verified["verified_paths"]
    (out / "image-manifest.json").write_text(json.dumps(verified["manifest"], indent=0))
    rec["install"]["manifest_sha256"] = sha256_file(out / "image-manifest.json")
    full = run(["dumpe2fs", img.dev], check=False).stdout.decode(errors="replace")
    layout = parse_dumpe2fs(full)
    log("checking the derived base against the certified disk, block by block")
    rec["install"]["changed_blocks"] = diff_against(img, cert_raw, length, layout,
                                                    verified["manifest"])  # fmt: skip
    if not rec["install"]["changed_blocks"]["ok"]:
        raise BuildError(f"derived base: unexplained changed blocks "
                         f"{rec['install']['changed_blocks']['unexplained']}")  # fmt: skip
    cert_raw.unlink()
    tb_dir = work / "toolbars"
    shutil.rmtree(tb_dir, ignore_errors=True)
    tb_dir.mkdir(parents=True)
    img.debugfs(f"rdump {TOOLBAR_ROOT} {tb_dir}\n")
    toolbars = {}
    for p in sorted((tb_dir / "modules").glob("*/toolbar/*.xml")):
        if p.is_symlink():
            raise BuildError(f"toolbar definition {p} is a symlink")
        toolbars[f"{TOOLBAR_ROOT}/{p.relative_to(tb_dir / 'modules')}"] = p.read_bytes()
    rec["toolbar_definitions"] = len(toolbars)
    log("writing the derived base qcow2")
    rec["derived_base"] = to_qcow2(base_raw, out / "s2v4-derived-base.qcow2")
    cells = [c for c in args.cells.split(",") if c]
    rec["cells"] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.parallel)) as pool:
        futures = {pool.submit(build_cell, c, base_raw, work, out, offset, length, layout,
                               toolbars, pre): c for c in cells}  # fmt: skip
        for fut in concurrent.futures.as_completed(futures):
            cell = futures[fut]
            rec["cells"][cell] = fut.result()
            log(f"cell {cell}: {rec['cells'][cell]['qcow2']['sha256']}")
    base_raw.unlink()
    shutil.rmtree(work, ignore_errors=True)
    rec["seconds"] = round(time.time() - t0, 1)
    rec["ok"] = True
    return rec


def selftest(work: Path) -> dict[str, Any]:
    """Round trip on a small synthetic ext4 at a byte offset (needs mke2fs and debugfs).

    Checks the install planner, ``debugfs`` application, readback and the block-level diff on
    a filesystem shaped like the guest's (a symlinked ``share/registry``, a ``.registry``
    source, toolbar definitions), and that the diff flags a change the plan did not make."""
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    offset, length = 1 << 20, 64 << 20
    cert = work / "cert.raw"
    with open(cert, "wb") as f:
        f.truncate(offset + length + (1 << 20))
    run(["mke2fs", "-q", "-F", "-t", "ext4", "-b", "4096", "-I", "256", "-O",
         "metadata_csum,64bit", "-E", f"offset={offset}", str(cert),
         f"{length >> 10}k"])  # fmt: skip
    seed = Image(cert, offset)
    tb_a = ('<toolbar:toolbar><toolbar:toolbaritem xlink:href=".uno:A"/>'
            '<toolbar:toolbaritem xlink:href=".uno:B"/><toolbar:toolbarseparator/>'
            '<toolbar:toolbaritem xlink:href=".uno:C"/></toolbar:toolbar>\n')  # fmt: skip
    tb_b = '<toolbar:toolbar><toolbar:toolbaritem xlink:href=".uno:Z"/></toolbar:toolbar>\n'
    (work / "a.xml").write_text(tb_a)
    (work / "b.xml").write_text(tb_b)
    (work / "main.xcd").write_text("<main/>\n")
    (work / "bad.json").write_text("{}\n" * 2000)
    script = "\n".join([
        "mkdir /etc", "mkdir /etc/libreoffice", "mkdir /etc/libreoffice/registry",
        "mkdir /etc/libreoffice/registry/res", "mkdir /usr", "mkdir /usr/lib",
        "mkdir /usr/lib/libreoffice", "mkdir /usr/lib/libreoffice/program",
        "mkdir /usr/lib/libreoffice/program/resource", "mkdir /usr/lib/libreoffice/share",
        "mkdir /usr/lib/libreoffice/share/.registry", "mkdir /usr/lib/libreoffice/share/config",
        "mkdir /usr/lib/libreoffice/share/config/soffice.cfg",
        f"mkdir {TOOLBAR_ROOT}", f"mkdir {TOOLBAR_ROOT}/scalc",
        f"mkdir {TOOLBAR_ROOT}/scalc/toolbar", "mkdir /usr/share", "mkdir /usr/share/doc",
        "symlink /usr/lib/libreoffice/share/registry /etc/libreoffice/registry",
        "cd /etc/libreoffice/registry", f"write {work / 'main.xcd'} main.xcd",
        f"cd {TOOLBAR_ROOT}/scalc/toolbar", f"write {work / 'a.xml'} a.xml",
        f"write {work / 'b.xml'} b.xml", "cd /usr/share/doc", f"write {work / 'bad.json'} bad.json",
        "cd /", "sif /usr/share/doc/bad.json checksum 0xdeadbeef",
    ]) + "\n"
    _, err = seed.debugfs(script, write=True)
    if errors_of(err):
        raise BuildError(f"selftest seed: {errors_of(err)}")
    t = 1_702_252_800
    members = [
        Member("/usr", "dir", 0o755, 0, 0, t),
        Member("/usr/lib", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/program", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/program/resource", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/program/resource/ar", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/program/resource/ar/LC_MESSAGES", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/program/resource/ar/LC_MESSAGES/sc.mo", "file", 0o644, 0,
               0, t, b"\xde\x12\x04\x95" + b"x" * 9000),
        Member("/usr/lib/libreoffice/share", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/share/.registry", "dir", 0o755, 0, 0, t),
        Member("/usr/lib/libreoffice/share/.registry/Langpack-ar.xcd", "file", 0o644, 0, 0, t,
               b"<langpack ar/>\n"),
        Member("/usr/share", "dir", 0o755, 0, 0, t),
        Member("/usr/share/doc", "dir", 0o755, 0, 0, t),
        Member("/usr/share/doc/p", "dir", 0o755, 0, 0, t),
        Member("/usr/share/doc/p/changelog.gz", "symlink", 0o777, 0, 0, t,
               target="../q/changelog.gz"),
    ]  # fmt: skip
    ucf = [("/usr/lib/libreoffice/share/.registry/Langpack-ar.xcd",
            "/etc/libreoffice/registry/Langpack-ar.xcd")]  # fmt: skip
    checks: dict[str, Any] = {}
    baseline = Image(cert, offset).fsck()  # one inode checksum mismatch, as on the certified disk
    checks["baseline_has_the_planted_finding"] = any("checksum" in f for f in baseline["findings"])
    # refusals: a path through the image's symlink, and an existing file
    through = [*members[:6], Member("/usr/lib/libreoffice/share/registry/res/x.xcd", "file",
                                    0o644, 0, 0, t, b"x")]  # fmt: skip
    probe = Image(cert, offset)
    for name, bad in (("through_symlink", through),
                      ("overwrite", [*members[:4], Member(
                          f"{TOOLBAR_ROOT}/scalc/toolbar/a.xml", "file", 0o644, 0, 0, t)])):
        try:
            plan_install(bad, [], probe.ls_dirs(base_listing_dirs(m.path for m in bad)))
            checks[f"refuses_{name}"] = False
        except BuildError:
            checks[f"refuses_{name}"] = True
    base = work / "base.raw"
    run(["cp", "--sparse=always", str(cert), str(base)])
    img = Image(base, offset)
    targets = [m.path for m in members] + [d for _, d in ucf]
    plan = plan_install(members, ucf, img.ls_dirs(base_listing_dirs(targets)))
    apply_plan(img, plan, work / "stage-base")
    checks["fsck_base"] = fsck_same(img.fsck(), baseline)
    ver = verify_plan(img, plan, work / "rb-base")
    layout = parse_dumpe2fs(run(["dumpe2fs", img.dev]).stdout.decode(errors="replace"))
    diff = diff_against(img, cert, length, layout, ver["manifest"])
    checks["base_diff_explained"] = diff["ok"] and diff["blocks"] > 0
    toolbars = {f"{TOOLBAR_ROOT}/scalc/toolbar/a.xml": tb_a.encode(),
                f"{TOOLBAR_ROOT}/scalc/toolbar/b.xml": tb_b.encode()}  # fmt: skip
    cells: dict[str, Any] = {}
    for cell in ("ER", "PL"):
        raw = work / f"{cell}.raw"
        run(["cp", "--sparse=always", str(base), str(raw)])
        ci = Image(raw, offset)
        listing = ci.ls_dirs(base_listing_dirs([SELECTOR_PATH, *toolbars]))
        cplan = plan_cell(cell, listing, toolbars if cell == "PL" else None)
        removed = [(listing.get(str(PurePosixPath(op.path).parent)) or {}).get(
            PurePosixPath(op.path).name) for op in cplan.ops if op.kind == "rm"]  # fmt: skip
        apply_plan(ci, cplan, work / f"stage-{cell}")
        cver = verify_plan(ci, cplan, work / f"rb-{cell}")
        cdiff = diff_against(ci, base, length, layout, cver["manifest"],
                             [e.ino for e in removed if e])  # fmt: skip
        cells[cell] = {"fsck": fsck_same(ci.fsck(), baseline), "diff_ok": cdiff["ok"],
                       "rewritten": sum(op.kind == "rm" for op in cplan.ops),
                       "counts": cdiff["counts"]}  # fmt: skip
        if cell == "ER":
            # tamper: a file the plan did not write must make the diff unexplained
            (work / "extra").write_bytes(b"not planned\n" * 400)
            ci.debugfs(f"cd /usr/share/doc\nwrite {work / 'extra'} extra\n", write=True)
            tdiff = diff_against(ci, base, length, layout, cver["manifest"])
            cells[cell]["tamper_flagged"] = not tdiff["ok"]
        raw.unlink()
    checks["cells"] = cells
    checks["ok"] = (all(v for k, v in checks.items()
                        if k.startswith(("refuses", "fsck", "base")))
                    and all(c["fsck"] and c["diff_ok"] for c in cells.values())
                    and cells["ER"].get("tamper_flagged") is True
                    and cells["PL"]["rewritten"] == 1
                    and cells["ER"]["rewritten"] == 0)  # fmt: skip
    shutil.rmtree(work, ignore_errors=True)
    return checks


def pins_from_record(record: Mapping[str, Any], build_dir: str) -> dict[str, Any]:
    """``harness/s2_locale/images.json`` from a successful build record."""
    if not record.get("ok"):
        raise BuildError("the build record is not a successful build")
    cells = {}
    for cell, r in sorted(record["cells"].items()):
        if not r["changed_blocks"]["ok"] or r["selector_sha256"] != hashlib.sha256(
                selector_xcd(cell).encode()).hexdigest():  # fmt: skip
            raise BuildError(f"cell {cell}: the record does not check out")
        cells[cell] = {"sha256": r["qcow2"]["sha256"], "size_bytes": r["qcow2"]["bytes"],
                       "selector_sha256": r["selector_sha256"],
                       "file": f"{build_dir}/{r['qcow2']['path']}"}  # fmt: skip
    base = record["derived_base"]
    return {
        "schema": "s2v4-images-v1",
        "build": {"executor_commit": record.get("executor_commit"), "dir": build_dir,
                  "certified_sha256": record["certified"]["sha256"],
                  "derived_base": {"sha256": base["sha256"], "size_bytes": base["bytes"],
                                   "file": f"{build_dir}/{base['path']}"},
                  "image_manifest_sha256": record["install"]["manifest_sha256"]},
        "cells": cells,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--certified", required=True)
    b.add_argument("--debs", required=True)
    b.add_argument("--out", type=Path, required=True)
    b.add_argument("--cells", default=",".join(CELLS))
    b.add_argument("--parallel", type=int, default=3)
    b.add_argument("--skip-certified-hash", action="store_true")
    s = sub.add_parser("selector")
    s.add_argument("cell")
    st = sub.add_parser("selftest")
    st.add_argument("--work", type=Path, required=True)
    pn = sub.add_parser("pins", help="images.json from a build record")
    pn.add_argument("record", type=Path)
    pn.add_argument("--build-dir", required=True)
    args = parser.parse_args(argv)
    if args.command == "pins":
        record = json.loads(args.record.read_text())
        print(json.dumps(pins_from_record(record, args.build_dir), indent=1, sort_keys=True))
        return 0
    if args.command == "selector":
        sys.stdout.write(selector_xcd(args.cell))
        return 0
    if args.command == "selftest":
        result = selftest(args.work)
        print(json.dumps(result, indent=1, sort_keys=True))
        return 0 if result["ok"] else 1
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        rec = build(args)
    except BuildError as exc:
        (args.out / "build-failed.json").write_text(json.dumps({"ok": False, "error": str(exc)}))
        log(f"FAILED: {exc}")
        return 2
    sha = Path("/src/.git_sha")
    if sha.is_file():
        rec["executor_commit"] = sha.read_text().strip()
    cells_manifest = {c: r.pop("manifest") for c, r in rec["cells"].items()}
    (args.out / "cell-manifests.json").write_text(json.dumps(cells_manifest, indent=0))
    (args.out / "build-record.json").write_text(json.dumps(rec, indent=1, sort_keys=True))
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
