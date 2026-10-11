"""S2 v4 P0.2-P0.3: the image surgery's planner, script, block checks and cell content."""

from __future__ import annotations

import io
import shutil
import sys
import tarfile
from pathlib import Path

import pytest

from harness.s2_locale import image_build as B

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / ("program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/"
                "pilot-r1/capture-1131/selectors")  # fmt: skip


def _capture():
    for sub in ("harness/s2_locale", "harness/q2_mutation"):
        path = str(ROOT / sub)
        if path not in sys.path:
            sys.path.insert(0, path)
    import capture  # noqa: PLC0415

    return capture


@pytest.mark.parametrize("cell", B.CELLS)
def test_selector_is_the_pilot_selector_read_last(cell):
    assert B.pilot_selector(cell) == (PILOT / f"{cell}.xcd").read_text(encoding="utf-8")
    assert B.pilot_selector(cell) == _capture().selector(cell)
    text = B.selector_xcd(cell)
    head, _, rest = text.partition(B.SELECTOR_DEPENDENCIES)
    assert head == B.XCD_HEAD and rest.startswith("<oor:component-data")
    assert '<dependency file="main"/>' in text
    assert '<dependency file="ctl_ar" optional="true"/>' in text


def test_selector_depends_on_every_other_layer_file():
    # the derived images' /etc/libreoffice/registry: the certified disk's files plus the pack's two
    certified = {"Langpack-en-US", "calc", "draw", "gnome", "graphicfilter", "impress",
                 "lingucomponent", "main", "math", "ogltrans", "pdfimport", "pyuno", "writer",
                 "xsltfilter"}
    assert set(B.LAYER_FILES) | {"main"} == certified | {"Langpack-ar", "ctl_ar"}
    assert {dst.rsplit("/", 1)[1][:-4] for _, dst in B.UCF_PAIRS if "/res/" not in dst} == {
        "Langpack-ar", "ctl_ar"}


def test_selector_keys():
    ar = B.selector_xcd("AR")
    assert '"ooLocale" oor:finalized="true"><value>ar<' in ar
    assert '"UILocale" oor:finalized="true"><value>ar<' in ar
    assert '"UIMirroring" oor:finalized="true"><value>true<' in ar
    assert "UIMirroring" not in B.selector_xcd("AD")
    assert "ooSetupSystemLocale" not in ar
    with pytest.raises(B.BuildError):
        B.selector_xcd("S")


def test_toolbar_shuffle_is_the_pilot_shuffle():
    text = ('<toolbar:toolbar><toolbar:toolbaritem xlink:href=".uno:A"/>'
            '<toolbar:toolbaritem xlink:href=".uno:B"/><toolbar:toolbarseparator/>'
            '<toolbar:toolbaritem xlink:href=".uno:C"/></toolbar:toolbar>')  # fmt: skip
    path = f"{B.TOOLBAR_ROOT}/scalc/toolbar/standardbar.xml"
    key = B.toolbar_key(path)
    assert key == "share/config/soffice.cfg/modules/scalc/toolbar/standardbar.xml"
    assert B.shuffled_toolbar(text, key) == _capture().shuffled_toolbar(text, key)
    assert sorted(B.TB_ITEM.findall(B.shuffled_toolbar(text, key))) == sorted(
        B.TB_ITEM.findall(text))
    one = '<toolbar:toolbar><toolbar:toolbaritem xlink:href=".uno:A"/></toolbar:toolbar>'
    assert B.shuffled_toolbar(one, key) == one


def _tar(entries):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, kind, payload in entries:
            info = tarfile.TarInfo(name)
            info.mtime, info.uid, info.gid = 1_702_252_800, 0, 0
            if kind == "dir":
                info.type, info.mode = tarfile.DIRTYPE, 0o755
                tar.addfile(info)
            elif kind == "sym":
                info.type, info.linkname, info.mode = tarfile.SYMTYPE, payload, 0o777
                tar.addfile(info)
            else:
                info.size, info.mode = len(payload), 0o644
                tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def test_read_deb_members_and_refusals():
    data = _tar([("./", "dir", None), ("./usr/", "dir", None), ("./usr/x.mo", "file", b"mo"),
                 ("./usr/l", "sym", "../q")])  # fmt: skip
    mem = B.read_deb_members(data, "pkg")
    assert [(m.path, m.kind) for m in mem] == [("/usr", "dir"), ("/usr/x.mo", "file"),
                                               ("/usr/l", "symlink")]  # fmt: skip
    assert mem[1].data == b"mo" and mem[1].mode == 0o644 and mem[2].target == "../q"
    with pytest.raises(B.BuildError):
        B.read_deb_members(_tar([("./usr/../etc/x", "file", b"")]), "pkg")
    with pytest.raises(B.BuildError):
        B.read_deb_members(_tar([("./usr/a b", "file", b"")]), "pkg")


def test_ucf_pairs_from_postinst():
    text = ('\tucf --three-way "/usr/lib/libreoffice/share/.registry/ctl_ar.xcd" '
            '"/etc/libreoffice/registry/ctl_ar.xcd"\n\tucfr --force p "/etc/x"\n')  # fmt: skip
    assert B.ucf_pairs(text) == [B.UCF_PAIRS[3]]


def _e(ino, mode):
    return B.Entry(ino, mode, 0, 0, 0)


LISTING = {
    "/": {"usr": _e(10, 0o40755), "etc": _e(11, 0o40755)},
    "/usr": {"lib": _e(12, 0o40755)},
    "/usr/lib": {"libreoffice": _e(13, 0o40755)},
    "/usr/lib/libreoffice": {"share": _e(14, 0o40755)},
    "/usr/lib/libreoffice/share": {"registry": _e(15, 0o120777), ".registry": _e(16, 0o40755)},
    "/usr/lib/libreoffice/share/.registry": {"main.xcd": _e(17, 0o100644)},
    "/etc": {"libreoffice": _e(18, 0o40755)},
    "/etc/libreoffice": {"registry": _e(19, 0o40755)},
    "/etc/libreoffice/registry": {"main.xcd": _e(20, 0o100644)},
}


def _m(path, kind="file", data=b"d"):
    return B.Member(path, kind, 0o755 if kind == "dir" else 0o644, 0, 0, 5, data)


def test_plan_install_orders_and_copies():
    members = [_m("/usr", "dir"), _m("/usr/lib/libreoffice/program", "dir"),
               _m("/usr/lib/libreoffice/program/a.mo"),
               _m("/usr/lib/libreoffice/share/.registry/Langpack-ar.xcd", data=b"lp")]  # fmt: skip
    ucf = [("/usr/lib/libreoffice/share/.registry/Langpack-ar.xcd",
            "/etc/libreoffice/registry/Langpack-ar.xcd")]  # fmt: skip
    plan = B.plan_install(members, ucf, LISTING)
    assert plan.skipped_dirs == ["/usr"]
    assert [(o.kind, o.path) for o in plan.ops] == [
        ("mkdir", "/usr/lib/libreoffice/program"),
        ("write", "/usr/lib/libreoffice/program/a.mo"),
        ("write", "/usr/lib/libreoffice/share/.registry/Langpack-ar.xcd"),
        ("write", "/etc/libreoffice/registry/Langpack-ar.xcd"),
    ]
    assert plan.ops[-1].data == b"lp" and plan.ops[-1].mode == 0o100644
    assert plan.ops[0].mode == 0o40755


@pytest.mark.parametrize("members", [
    [_m("/usr/lib/libreoffice/share/registry/res/x.xcd")],  # through the image's symlink
    [_m("/usr/lib/libreoffice/share/.registry/main.xcd")],  # overwrites a file
    [_m("/usr/lib/libreoffice/nodir/x.mo")],  # parent neither exists nor is created
    [_m("/etc/libreoffice/registry/main.xcd", "dir")],  # a dir over a file
])
def test_plan_install_refuses(members):
    with pytest.raises(B.BuildError):
        B.plan_install(members, [], LISTING)


def test_plan_cell_selector_and_placebo():
    tb = f"{B.TOOLBAR_ROOT}/scalc/toolbar"
    listing = {**LISTING, tb: {"a.xml": _e(30, 0o100644), "b.xml": _e(31, 0o100644)}}
    toolbars = {
        f"{tb}/a.xml": b'<t><toolbar:toolbaritem xlink:href=".uno:A"/>'
                       b'<toolbar:toolbaritem xlink:href=".uno:B"/>'
                       b'<toolbar:toolbaritem xlink:href=".uno:C"/></t>',
        f"{tb}/b.xml": b'<t><toolbar:toolbaritem xlink:href=".uno:Z"/></t>',
    }
    er = B.plan_cell("ER", listing)
    assert [(o.kind, o.path) for o in er.ops] == [("write", B.SELECTOR_PATH)]
    assert er.ops[0].data == B.selector_xcd("ER").encode()
    pl = B.plan_cell("PL", listing, toolbars)
    kinds = [(o.kind, o.path) for o in pl.ops]
    changed = B.shuffled_toolbar(toolbars[f"{tb}/a.xml"].decode(),
                                 B.toolbar_key(f"{tb}/a.xml")).encode() != toolbars[f"{tb}/a.xml"]
    expect = [("write", B.SELECTOR_PATH)]
    if changed:
        expect += [("rm", f"{tb}/a.xml"), ("write", f"{tb}/a.xml")]
    assert kinds == expect
    with pytest.raises(B.BuildError):
        B.plan_cell("PL", listing, None)
    taken = {**listing, "/etc/libreoffice/registry": {"zz-s2v4-cell.xcd": _e(40, 0o100644)}}
    with pytest.raises(B.BuildError):
        B.plan_cell("E", taken)


def test_debugfs_script(tmp_path):
    plan = B.Plan([B.Op("mkdir", "/a/b", 0o40755, 0, 0, 7),
                   B.Op("write", "/a/b/c.mo", 0o100644, 0, 0, 7, data=b"xyz"),
                   B.Op("symlink", "/a/b/l", 0o120777, 0, 0, 7, target="../q/r.gz"),
                   B.Op("rm", "/a/old")])  # fmt: skip
    script = B.debugfs_script(plan, tmp_path)
    lines = script.splitlines()
    assert lines[0] == "mkdir /a/b" and "sif /a/b mode 040755" in lines
    i = lines.index("cd /a/b")
    assert lines[i + 1] == f"write {tmp_path / '000001'} c.mo" and lines[i + 2] == "cd /"
    assert (tmp_path / "000001").read_bytes() == b"xyz"
    assert "symlink /a/b/l ../q/r.gz" in lines and "sif /a/b/l mode" not in script
    assert "sif /a/b/c.mo mtime @7" in lines and "rm /a/old" in lines
    with pytest.raises(B.BuildError):
        B.debugfs_script(B.Plan([B.Op("write", "/a b", 0o100644)]), tmp_path)


def test_parse_ls_p_and_split():
    text = "debugfs: ls -p /x\n/2/040755/0/0/.//\n/12/100644/0/0/a.mo/123/\n/13/040755/0/0/d//\n"
    parts = B.split_debugfs_output(text)
    got = B.parse_ls_p(parts["ls -p /x"])
    assert set(got) == {"a.mo", "d"}
    assert got["a.mo"].size == 123 and got["d"].is_dir and not got["a.mo"].is_link


def test_changed_blocks_sparse(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for p in (a, b):
        with open(p, "wb") as f:
            f.truncate(64 << 20)
    with open(b, "r+b") as f:
        f.seek((1 << 20) + 3 * 4096 + 5)
        f.write(b"x")
        f.seek((1 << 20) + (40 << 20))
        f.write(b"y" * 5000)
    with open(a, "r+b") as f:
        f.seek((1 << 20) + (40 << 20))
        f.write(b"y" * 5000)
        f.seek((1 << 20) + (50 << 20))
        f.write(b"z")
    got = B.changed_blocks(a, b, 1 << 20, 60 << 20, chunk=1 << 20)
    assert got == [3, (50 << 20) // 4096]


DUMPE2FS = """Inodes per group:         8192
Inode size:	          256
Block size:               4096

Group 0: (Blocks 0-32767) csum 0x1 [ITABLE_ZEROED]
  Primary superblock at 0, Group descriptors at 1-4
  Reserved GDT blocks at 5-1028
  Block bitmap at 1029 (+1029)
  Inode bitmap at 1045 (+1045)
  Inode table at 1061-1572 (+1061)
Group 1: (Blocks 32768-65535) csum 0x2
  Backup superblock at 32768, Group descriptors at 32769-32772
  Block bitmap at 1030 (bg #0 + 1030)
  Inode bitmap at 1046 (bg #0 + 1046)
  Inode table at 1573-2084 (bg #0 + 1573)
"""


def test_layout_and_classification():
    lay = B.parse_dumpe2fs(DUMPE2FS)
    assert {0, 1, 4, 5, 1028, 32768, 32772} <= lay.sb_gdt
    assert lay.block_bitmaps == {1029, 1030} and lay.inode_bitmaps == {1045, 1046}
    assert lay.inodes_in_table_block(1061)[:2] == [1, 2]
    assert lay.inodes_in_table_block(1573)[0] == 8193
    owner = {5000: 8200, 6000: 19, 7000: 99}
    paths = {8200: ["/etc/libreoffice/registry/zz-s2v4-cell.xcd"],
             19: ["/etc/libreoffice/registry"], 99: ["/usr/other"]}  # fmt: skip
    common = dict(layout=lay, intended={"/etc/libreoffice/registry/zz-s2v4-cell.xcd"},
                  intended_dirs={"/etc/libreoffice/registry"}, touched_inodes={8200, 19})
    ok = B.classify_blocks([0, 1029, 1045, 1573, 5000, 6000], owner, paths, **common)
    assert ok["ok"] and ok["counts"]["inode_table"] == 1 and ok["counts"]["file_data"] == 1
    bad = B.classify_blocks([7000, 1100, 9999], owner, paths, **common)
    assert not bad["ok"] and bad["unexplained"] == [1100, 7000, 9999]


def test_gpt_root_is_the_largest_partition():
    table = {"partitiontable": {"partitions": [{"start": 2048, "size": 2048},
                                               {"start": 1054720, "size": 61857792}]}}
    assert B.gpt_root(table) == (B.ROOT_START_SECTOR, B.ROOT_SECTORS)


def test_pinned_archives_are_the_fetched_ones():
    import json

    prov = json.loads((ROOT / "program/evidence/2026-10-11/s2v4-image/fetch/provenance.json")
                      .read_text())  # fmt: skip
    fetched = {p["filename"]: (p["sha256"], p["size"]) for p in prov["packages"]}
    assert {f: (s, n) for f, s, n, _ in B.DEBS} == fetched
    assert prov["signature"]["ok"] and prov["ok"]


@pytest.mark.skipif(not (shutil.which("mke2fs") and shutil.which("debugfs")
                         and shutil.which("e2fsck") and shutil.which("dumpe2fs")),
                    reason="needs e2fsprogs (run in the vmprobe container)")  # fmt: skip
def test_selftest_roundtrip(tmp_path):
    result = B.selftest(tmp_path / "st")
    assert result["ok"], result


def test_plan_install_shares_a_directory_two_packages_create():
    a = [_m("/usr", "dir"), _m("/usr/lib/libreoffice/program", "dir"),
         _m("/usr/lib/libreoffice/program/a.mo")]
    b = [_m("/usr/lib/libreoffice/program", "dir"), _m("/usr/lib/libreoffice/program/b.mo")]
    plan = B.plan_install(a + b, [], LISTING)
    assert [o.kind for o in plan.ops] == ["mkdir", "write", "write"]
    assert plan.shared_dirs == ["/usr/lib/libreoffice/program"]
    with pytest.raises(B.BuildError):  # the same file from two packages is refused
        B.plan_install(a + [_m("/usr/lib/libreoffice/program/a.mo")], [], LISTING)


def test_pins_from_a_build_record():
    import hashlib

    cell = {"changed_blocks": {"ok": True}, "qcow2": {"sha256": "c" * 64, "bytes": 7,
                                                      "path": "s2v4-cell-E.qcow2"},
            "selector_sha256": hashlib.sha256(B.selector_xcd("E").encode()).hexdigest()}
    rec = {"ok": True, "cells": {"E": cell}, "executor_commit": "x",
           "certified": {"sha256": B.CERTIFIED_SHA256},
           "derived_base": {"sha256": "d" * 64, "bytes": 9, "path": "s2v4-derived-base.qcow2"},
           "install": {"manifest_sha256": "e" * 64}}
    pins = B.pins_from_record(rec, "/home/kevin/cotcodec-runs/stage0/s2v4/image-build-v3")
    assert pins["cells"]["E"]["sha256"] == "c" * 64 and pins["schema"] == "s2v4-images-v1"
    bad = {**rec, "cells": {"A": cell}}  # the E selector recorded under A
    with pytest.raises(B.BuildError):
        B.pins_from_record(bad, "/x")


def test_images_json_is_the_committed_build_records_pin_set():
    import json

    build = ROOT / "program/evidence/2026-10-11/s2v4-image/image-build-1199"
    rec = json.loads((build / "build-record.json").read_text())
    pins = json.loads((ROOT / "harness/s2_locale/images.json").read_text())
    assert pins == B.pins_from_record(rec, pins["build"]["dir"])
    assert set(pins["cells"]) == set(B.CELLS)
    for r in rec["cells"].values():
        assert r["changed_blocks"]["ok"] and r["changed_blocks"]["counts"]["unexplained"] == 0
        assert r["fsck"]["findings"] == rec["fsck_certified"]["findings"]
    assert rec["install"]["changed_blocks"]["ok"]


def test_layer_files_check():
    names = [f"{n}.xcd" for n in (*B.LAYER_FILES, "main")] + ["oo-ldap.xcd.sample"]
    assert B.check_layer_files(names)["ok"]
    assert B.check_layer_files([*names, "zz-s2v4-cell.xcd"])["ok"]  # the selector itself
    extra = B.check_layer_files([*names, "zzz-late.xcd"])
    assert not extra["ok"] and extra["unlisted"] == ["zzz-late"]
    missing = B.check_layer_files([n for n in names if n != "ctl_ar.xcd"])
    assert not missing["ok"] and missing["missing"] == ["ctl_ar"]


HEAD_A = """dumpe2fs 1.46.5 (30-Dec-2021)
Filesystem volume name:   <none>
Filesystem state:         clean
Free blocks:              100
Free inodes:              50
Last write time:          Thu Mar 21 10:00:00 2024
Lifetime writes:          10 GB
Checksum:                 0x1
Journal size:             128M
"""


def test_superblock_changes():
    after = (HEAD_A.replace("100", "90").replace("0x1", "0x2")
             .replace("10 GB", "11 GB"))  # fmt: skip
    ok = B.superblock_changes(HEAD_A, after)
    assert ok["ok"] and ok["changed"] == ["Checksum", "Free blocks", "Lifetime writes"]
    bad = B.superblock_changes(HEAD_A, after.replace("clean", "not clean"))
    assert not bad["ok"] and bad["unexpected"] == ["Filesystem state"]
    assert not B.superblock_changes("", "")["ok"]  # nothing parsed is not a pass


def test_inode_slot_changes():
    ref = bytes(4096)
    img = bytearray(ref)
    img[256 * 3 + 7] = 1  # the fourth slot
    inodes = list(range(17, 33))
    assert B.inode_slot_changes(ref, bytes(img), inodes, 256) == [20]
    assert B.inode_slot_changes(ref, ref, inodes, 256) == []


def test_classify_reads_inode_slots():
    lay = B.parse_dumpe2fs(DUMPE2FS)
    common = dict(owner={}, paths={}, layout=lay, intended=set(), intended_dirs=set(),
                  touched_inodes={1})
    # inode 1 touched, inode 2 changed in the same table block: unexplained with slots
    assert B.classify_blocks([1061], **common)["ok"]
    assert not B.classify_blocks([1061], **common, table_slots={1061: [1, 2]})["ok"]
    assert B.classify_blocks([1061], **common, table_slots={1061: [1]})["ok"]


def test_stat_mtime():
    text = (" ctime: 0x00000007:00000000 -- Thu Jan  1 00:00:07 1970\n"
            " mtime: 0x65765100:00000000 -- Mon Dec 11 00:00:00 2023\n")  # fmt: skip
    assert B.stat_mtime(text) == B.CELL_MTIME
    assert B.stat_mtime(" mtime: 0x0000000a -- x\n") == 10 and B.stat_mtime("") is None


def test_superblock_wtime_and_outside_partition(tmp_path):
    raw = tmp_path / "d.raw"
    offset = 1 << 20
    sb = bytearray(1024)
    sb[B.S_MAGIC:B.S_MAGIC + 2] = B.EXT4_MAGIC.to_bytes(2, "little")
    sb[B.S_WTIME:B.S_WTIME + 4] = (1_700_000_000).to_bytes(4, "little")
    with open(raw, "wb") as f:
        f.truncate(offset + (8 << 20) + (1 << 20))
        f.seek(offset + B.SUPERBLOCK_OFFSET)
        f.write(sb)
    assert B.superblock_wtime(raw, offset) == 1_700_000_000
    with pytest.raises(B.BuildError):
        B.superblock_wtime(raw, 0)
    other = tmp_path / "e.raw"
    shutil.copyfile(raw, other)
    assert B.outside_partition_blocks(raw, other, offset, 8 << 20)["ok"]
    with open(other, "r+b") as f:
        f.seek(offset + (8 << 20) + 5)
        f.write(b"x")
    got = B.outside_partition_blocks(raw, other, offset, 8 << 20)
    assert not got["ok"] and got["tail"] == [0] and got["head"] == []
    with open(other, "r+b") as f:  # inside the partition: not this check's business
        f.seek(offset + (8 << 20) + 5)
        f.write(b"\0")
        f.seek(offset + 4096 * 9)
        f.write(b"y")
    assert B.outside_partition_blocks(raw, other, offset, 8 << 20)["ok"]


def test_write_sessions_need_the_fixed_time(tmp_path):
    with pytest.raises(B.BuildError, match="fixed time"):
        B.Image(tmp_path / "x.raw", 0).debugfs("stats\n", write=True)
