"""S2 v4: the per-slot cell-image lane and the VM probe (no Docker, no VM)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from harness.q2_stage1 import lane as s1a
from harness.s2_locale import vm_lane as L
from harness.s2_locale import vm_probe as P

ROOT = Path(__file__).resolve().parents[1]
DEV = json.loads((ROOT / L.SPLITS).read_text())["dev"]
CONFIRM = json.loads((ROOT / L.SPLITS).read_text())["confirm"]
SEL = {"E": "1" * 64, "AR": "2" * 64}


def _source(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "harness/s2_locale").mkdir(parents=True)
    (src / "program/evidence/q2-mutation").mkdir(parents=True)
    shutil.copy(ROOT / L.SPLITS, src / L.SPLITS)
    (src / L.IMAGES).write_text(json.dumps({"schema": "s2v4-images-v1", "cells": {
        c: {"sha256": c[0].lower() * 64 if c != "AR" else "b" * 64, "size_bytes": 10 + i,
            "selector_sha256": SEL[c]} for i, c in enumerate(SEL)}}))
    return src


def _manifest(src: Path) -> dict:
    pins = L.load_pins(src)
    images = {c: {"host_path": f"{s1a.RUN_ROOT}stage0/s2v4/images/{c}.qcow2",
                  "sha256": pins[c]["sha256"], "size_bytes": pins[c]["size_bytes"]}
              for c in ("S", "E", "AR")}
    base = {
        "schema": L.SCHEMA, "experiment_id": L.EXPERIMENT_ID, "purpose": "development",
        "name": "smoke-v1", "run_root": f"{s1a.RUN_ROOT}stage0/s2v4/vm-runs",
        "vm": {**L.VM_PINS, "guest_ip": "20.20.20.21", "concurrency": 3, "hmp_port": 7100},
        "images": images, "episode_image_id": L.EPISODE_IMAGE_ID,
        "osworld": {"commit": L.OSWORLD_COMMIT, "host_dir": f"{s1a.RUN_ROOT}x/OSWorld"},
        "file_cache": {"host_dir": f"{s1a.RUN_ROOT}x/files"}, "episode_timeout_s": 900,
        "settle_after_reset_s": 60, "settle_before_eval_s": 20, "evaluate": True,
        "mode": "s2v4-probe", "engine": {"kind": "none"},
        "slurm": {"cpus": 16, "memory_gb": 32, "minutes": 60},
    }
    return L.render(base, DEV[:2], ["S", "E", "AR"])


def test_render_replicates_by_cell():
    m = L.render({"x": 1}, DEV[:2], ["S", "E"], reps_by_cell={"E": 2})
    assert [s["slot"] for s in m["slots"]][:3] == [f"{DEV[0][:8]}:S:r1", f"{DEV[0][:8]}:E:r1",
                                                   f"{DEV[0][:8]}:E:r2"]
    assert len(m["slots"]) == 6 and m["slots"][-1]["block"] == "t001"


def test_pins_include_the_certified_stock_disk(tmp_path):
    pins = L.load_pins(_source(tmp_path))
    assert pins["S"] == {"sha256": s1a.QCOW2_SHA256, "size_bytes": s1a.QCOW2_BYTES,
                         "selector_sha256": None}
    assert pins["AR"]["selector_sha256"] == SEL["AR"]


def test_render_and_validate(tmp_path):
    src = _source(tmp_path)
    m = L.validate_manifest(_manifest(src), src)
    assert len(m["slots"]) == 6
    assert m["slots"][0]["slot"] == f"{DEV[0][:8]}:S:r1" and m["slots"][0]["block"] == "t000"
    assert L.check_slurm(m) == {"cpus": 16, "memory_gb": 32, "minutes": 60}


@pytest.mark.parametrize("edit, match", [
    (lambda m: m["images"]["E"].update(sha256="f" * 64), "sha256 differs"),
    (lambda m: m["images"].update(PL=dict(m["images"]["E"])), "no pinned image"),
    (lambda m: m["vm"].update(qcow2={}), "per slot"),
    (lambda m: m["vm"].update(ram_size="8G"), "ram_size"),
    (lambda m: m["vm"].update(concurrency=33), "concurrency"),
    (lambda m: m["slots"][0].update(task_id=CONFIRM[0],
                                    slot=L.slot_id(CONFIRM[0], "S", 1)), "dev-split"),
    (lambda m: m["slots"][0].update(cell="ER", slot=L.slot_id(DEV[0], "ER", 1)), "no image"),
    (lambda m: m.update(settle_after_reset_s=30), "settles"),
    (lambda m: m.update(purpose="phase0"), "purpose"),
    (lambda m: m.update(engine={"kind": "bridge"}), "engine"),
    (lambda m: m["images"]["S"].update(host_path="/tmp/x.qcow2"), "host_path"),
])
def test_validate_refuses(tmp_path, edit, match):
    src = _source(tmp_path)
    m = _manifest(src)
    edit(m)
    with pytest.raises(L.LaneError, match=match):
        L.validate_manifest(m, src)


def test_frozen_registration_refuses_development(tmp_path):
    src = _source(tmp_path)
    (src / "program/preregistrations").mkdir(parents=True)
    (src / L.LEDGER).write_text(json.dumps({"experiment_id": L.EXPERIMENT_ID}) + "\n")
    with pytest.raises(L.LaneError, match="frozen"):
        L.validate_manifest(_manifest(src), src)


def test_vm_view_swaps_only_the_disk(tmp_path):
    src = _source(tmp_path)
    m = L.validate_manifest(_manifest(src), src)
    from harness.q2.vm.driver import vm_run_argv

    stock = vm_run_argv(L.vm_view(m, "S"), "123", 0, None, None)
    ar = vm_run_argv(L.vm_view(m, "AR"), "123", 0, None, None)
    diff = [(a, b) for a, b in zip(stock, ar, strict=True) if a != b]
    assert len(stock) == len(ar)
    assert diff == [(f"{m['images']['S']['host_path']}:/System.qcow2:ro",
                     f"{m['images']['AR']['host_path']}:/System.qcow2:ro")]


class FakeDocker:
    def __init__(self, records):
        self.records, self.started, self.removed = records, [], []

    def start_vm(self, argv):
        self.started.append(argv)

    def run_episode(self, argv, name, timeout, stop, log):
        out = Path([a for a in argv if a.endswith(":/out")][0].split(":")[0])
        cfg = json.loads((out / "config.json").read_text())
        self.records.append(cfg)
        (out / "probe.json").write_text(json.dumps({"slot": cfg["slot"], "cell": cfg["cell"],
                                                    "status": "probed"}))
        return 0

    def remove(self, name):
        self.removed.append(name)
        return {"removed": True}


def test_lane_mounts_each_slot_cell_and_passes_its_selector(tmp_path):
    src = _source(tmp_path)
    m = L.validate_manifest(_manifest(src), src)
    seen: list[dict] = []
    docker = FakeDocker(seen)
    lane = L.S2Lane(s1a.LaneConfig(m, "777", tmp_path / "run", src), docker=docker,
                    verify=False, certified=[])
    receipt = lane.run()
    assert receipt["records"] == 6 and receipt["statuses"] == {"probed": 6}
    mounts = [[a for a in argv if a.endswith(":/System.qcow2:ro")][0] for argv in docker.started]
    by_cell = {cfg["cell"]: cfg for cfg in seen}
    assert sorted(set(mounts)) == sorted(
        f"{m['images'][c]['host_path']}:/System.qcow2:ro" for c in ("S", "E", "AR"))
    assert by_cell["S"]["selector_sha256"] is None
    assert by_cell["AR"]["selector_sha256"] == SEL["AR"]
    assert by_cell["E"]["image_sha256"] == m["images"]["E"]["sha256"]
    assert json.loads((tmp_path / "run/lane-receipt.json").read_text())["experiment_id"] == (
        L.EXPERIMENT_ID)


def test_lane_refuses_to_dispatch_on_a_wrong_image(tmp_path, monkeypatch):
    src = _source(tmp_path)
    m = L.validate_manifest(_manifest(src), src)
    monkeypatch.setattr(s1a, "sha256_file", lambda p: "0" * 64)
    docker = FakeDocker([])
    lane = L.S2Lane(s1a.LaneConfig(m, "778", tmp_path / "run", src), docker=docker)
    receipt = lane.run()
    assert "image check" in receipt["error"] and not docker.started


A11Y = """<desktop-frame xmlns:st="https://accessibility.ubuntu.example.org/ns/state"
 xmlns:cp="https://accessibility.ubuntu.example.org/ns/component" name="main">
 <application name="soffice" st:showing="true">
  <frame name="x.xlsx - LibreOffice Calc" st:showing="true">
   <menu-bar name="" st:showing="true">
    <menu name="{a}" st:showing="true" cp:screencoord="({x1}, 60)" cp:size="(40, 20)"/>
    <menu name="{b}" st:showing="true" cp:screencoord="({x2}, 60)" cp:size="(40, 20)"/>
   </menu-bar>
   <push-button name="{c}" st:showing="true"/>
   <push-button name="hidden" />
   <document-spreadsheet name="Sheet1" st:showing="true">
    <table-cell name="Revenue" st:showing="true"/>
   </document-spreadsheet>
  </frame>
 </application>
 <application name="gnome-shell"><label name="Activities" st:showing="true"/></application>
</desktop-frame>"""


def test_a11y_summary_text_and_direction():
    ltr = P.a11y_summary(A11Y.format(a="File", b="Edit", c="Bold", x1=10, x2=60))
    assert ltr["arabic_share"] == 0.0 and ltr["menubar_order"] == "ltr"
    assert ltr["named_showing"] == 3 and ltr["menubar_first_on_right"] is False
    rtl = P.a11y_summary(A11Y.format(a="ملف", b="تحرير", c="غامق", x1=1870, x2=1820))
    assert rtl["arabic_share"] == 1.0 and rtl["menubar_order"] == "rtl"
    assert rtl["menubar_first"] == "ملف" and rtl["menubar_first_on_right"] is True
    assert "parse_error" in P.a11y_summary("<unclosed")


class FakeGuest:
    def __init__(self, selector):
        self.selector = selector
        self.hashes = 0

    def run_script(self, source, args):
        if args[0] == "hash":
            self.hashes += 1
            paths = json.loads(args[1])["paths"]
            return {"files": [{"path": p, "exists": True, "sha256": str(self.hashes),
                               "mtime_ns": self.hashes} for p in paths]}
        assert args[0] == "facts"
        return {"selector_sha256": self.selector, "keyboard_layout": "us", "window_titles": []}

    def screenshot(self, timeout=10.0):
        return 200, b"\x89PNG\r\n\x1a\n" + b"0" * 100, 0.01

    def _request(self, method, path, timeout=None, **kw):
        return 200, json.dumps({"AT": A11Y.format(a="File", b="Edit", c="B", x1=1,
                                                  x2=50)}).encode(), 0.01


class FakeSession:
    evaluate_replies: list = []

    def setup(self):
        return {"failures": [], "steps": 2}

    def evaluate(self, last):
        return 0.0

    def close(self):
        pass


def _probe(tmp_path, selector_in_guest, expected):
    cfg = P.ProbeConfig(lane="l", purpose="development", slot="s", task_id=DEV[0], cell="E",
                        block="t000", attempt=1, image_sha256="e" * 64,
                        selector_sha256=expected, out_dir=str(tmp_path / "out"))
    task = {"id": DEV[0], "evaluator": {"result": {"type": "vm_file", "path": "~/x.xlsx"}}}
    probe = P.Probe(cfg, guest=FakeGuest(selector_in_guest), task=task,
                    session_factory=lambda c, t: FakeSession(), sleep=lambda s: None,
                    gpu_glob=lambda: [])
    probe._runner.warm_up = lambda: None
    probe._runner.check_restarts = lambda key="server_end": None
    return probe.run()


def test_probe_records_a_probed_slot(tmp_path):
    rec = _probe(tmp_path, SEL["E"], SEL["E"])
    assert rec["status"] == "probed" and rec["verdict"] == "fail" and rec["score"] == 0.0
    assert rec["post_setup"]["stable"] is True
    assert rec["post_setup"]["a11y"]["summary"]["menubar_order"] == "ltr"
    assert rec["result_files"]["/home/user/x.xlsx"]["rewritten"] is True
    assert (tmp_path / "out/screens/post_setup-1.png").is_file()
    assert json.loads((tmp_path / "out/probe.json").read_text())["slot"] == "s"


def test_probe_refuses_the_wrong_image(tmp_path):
    rec = _probe(tmp_path, None, SEL["E"])
    assert rec["status"] == "infrastructure" and rec["infrastructure_type"] == "probe:image_check"


def test_result_paths_and_rewritten():
    task = {"evaluator": {"result": [{"type": "vm_file", "path": "$HOME/a.docx"},
                                     {"type": "vm_file", "path": ["b.csv", "/tmp/c"]},
                                     {"type": "cloud_file", "path": "x"}]}}
    assert P.result_paths(task) == ["/home/user/a.docx", "/home/user/b.csv", "/tmp/c"]
    same = {"exists": True, "sha256": "a", "mtime_ns": 1}
    assert not P.rewritten(same, same)
    assert P.rewritten(same, {**same, "mtime_ns": 2})
    assert P.rewritten({"exists": False}, same) and not P.rewritten(same, {"exists": False})


def test_smoke_summary_masks_the_shell_and_caret(tmp_path):
    import numpy as np
    from PIL import Image

    from harness.s2_locale import smoke_summary as S

    def slot(cell, rep, img1, img2, share, order):
        d = tmp_path / "slots" / f"{DEV[0][:8]}_{cell}_r{rep}.a1"
        (d / "screens").mkdir(parents=True)
        Image.fromarray(img1).save(d / "screens/post_setup-1.png")
        Image.fromarray(img2).save(d / "screens/post_setup-2.png")
        rec = {"slot": L.slot_id(DEV[0], cell, rep), "task_id": DEV[0], "cell": cell,
               "attempt": 1, "status": "probed", "verdict": "fail",
               "post_setup": {"stable": True, "facts": {"keyboard_layout": "us",
                                                        "window_titles": ["x - LibreOffice Calc"]},
                              "a11y": {"summary": {"arabic_share": share,
                                                   "menubar_order": order}}}}
        (d / "probe.json").write_text(json.dumps(rec))

    base = np.zeros((100, 120, 3), dtype=np.uint8)
    clock = base.copy()
    clock[5, 60] = 255  # top bar: masked
    caret = base.copy()
    caret[50, 10] = 255  # differs between E's two shots: masked
    real = base.copy()
    real[80, 80:83] = 200  # a real difference in A
    slot("S", 1, base, base, 0.0, "ltr")
    slot("E", 1, clock, caret, 0.0, "ltr")
    slot("E", 2, base, base, 0.0, "ltr")
    slot("A", 1, real, real, 0.9, "ltr")
    slot("AR", 1, real, real, 0.9, "rtl")
    out = S.summarize(tmp_path)
    d = out["pixel_diffs"][DEV[0][:8]]
    assert d["E_vs_S"]["diff_pixels"] == 0 and d["E_vs_E2"]["diff_pixels"] == 0
    assert d["A_vs_E"]["diff_pixels"] == 3
    rows = {r["cell"]: r for r in out["slots"]}
    assert rows["A"]["arabic_as_expected"] and rows["AR"]["order_as_expected"]
    assert rows["E"]["arabic_as_expected"] and not rows["E"]["image_check_failed"]
