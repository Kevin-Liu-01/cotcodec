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
    (src / "program/evidence/q2-mutation/harness").mkdir(parents=True)
    shutil.copy(ROOT / L.FILE_CACHE_RECEIPTS, src / L.FILE_CACHE_RECEIPTS)
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
    got = L.check_slurm(m)
    assert {k: got[k] for k in ("cpus", "memory_gb", "minutes")} == {"cpus": 16, "memory_gb": 32,
                                                                    "minutes": 60}
    assert got["hash_minutes"] == 1 and got["slot_minutes"] == 11  # ceil(1.5 x 6 x 3.5 / 3)


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
    (lambda m: m.update(purpose="phase0"), "only after the freeze"),
    (lambda m: m.update(purpose="acceptance"), "purpose must be"),
    (lambda m: m.update(engine={"kind": "bridge"}), "engine"),
    (lambda m: m["images"]["S"].update(host_path="/tmp/x.qcow2"), "host_path"),
])
def test_validate_refuses(tmp_path, edit, match):
    src = _source(tmp_path)
    m = _manifest(src)
    edit(m)
    with pytest.raises(L.LaneError, match=match):
        L.validate_manifest(m, src)


def _freeze(src: Path, head: str = "a" * 40, sha: str = "b" * 40) -> dict:
    """A scratch freeze of a stand-in registration in ``src``'s own ledger (the chain as
    ``scripts/preregister.py`` writes it); the export's ``.git_sha`` is the freeze commit."""
    import hashlib

    reg = src / L.REGISTRATION
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text("# S2 v4 frozen stand-in\n")
    body = {"experiment_id": L.EXPERIMENT_ID, "frozen_at": "2026-10-12T00:00:00Z",
            "git_head_at_freeze": head, "path": L.REGISTRATION,
            "previous_hash": "0" * 64, "sha256": hashlib.sha256(reg.read_bytes()).hexdigest()}
    body["hash"] = hashlib.sha256(json.dumps({k: v for k, v in body.items()}, sort_keys=True,
                                             separators=(",", ":")).encode()).hexdigest()
    (src / L.LEDGER).write_text(json.dumps(body) + "\n")
    (src / ".git_sha").write_text(sha + "\n")
    return body


def _census(src: Path, monkeypatch, m: dict) -> list:
    import hashlib

    census = {"schema": "s2v4-census-v1", "slots": m["slots"]}
    path = src / L.CENSUS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(census))
    monkeypatch.setattr(L, "CENSUS_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    return m["slots"]


def _registered(src: Path, row: dict, m: dict) -> dict:
    m = dict(m, purpose="phase0", episode_timeout_s=L.EPISODE_TIMEOUT_S,
             run_root=L.PHASE0_RUN_ROOT,
             freeze={"commit": "b" * 40, "ledger_row_hash": row["hash"],
                     "git_head_at_freeze": row["git_head_at_freeze"]},
             osworld=dict(m["osworld"], host_dir=L.OSWORLD_HOST),
             file_cache={"host_dir": L.FILE_CACHE_HOST})
    m["vm"] = dict(m["vm"], concurrency=L.V_REGISTERED)
    m["images"] = dict(m["images"], S=dict(m["images"]["S"], host_path=L.S_HOST_PATH))
    return m


def test_frozen_registration_refuses_development(tmp_path):
    src = _source(tmp_path)
    _freeze(src)
    with pytest.raises(L.LaneError, match="frozen: development no longer runs"):
        L.validate_manifest(_manifest(src), src)


def test_broken_ledger_chain_refuses(tmp_path):
    src = _source(tmp_path)
    _freeze(src)
    text = (src / L.LEDGER).read_text().replace("2026-10-12", "2026-10-13")
    (src / L.LEDGER).write_text(text)
    with pytest.raises(L.LaneError, match="hash chain"):
        L.validate_manifest(_manifest(src), src)


def test_phase0_admitted_only_from_the_freeze_export(tmp_path, monkeypatch):
    src = _source(tmp_path)
    row = _freeze(src)
    base = _manifest(src)
    _census(src, monkeypatch, base)
    monkeypatch.setattr(L, "CAPTURE_CELLS", ("S", "E", "AR"))
    monkeypatch.setattr(L, "IMAGE_OF", {})
    m = _registered(src, row, base)
    assert L.validate_manifest(m, src)["purpose"] == "phase0"
    for edit, match in (
        (lambda x: x.update(slots=x["slots"][1:]), "census"),
        (lambda x: x["vm"].update(concurrency=8), "V = 20"),
        (lambda x: x.update(evaluate=False), "postconfig"),
        (lambda x: x["freeze"].update(commit="c" * 40), "freeze commit"),
        (lambda x: x["freeze"].update(ledger_row_hash="0" * 64), "another ledger row"),
    ):
        bad = json.loads(json.dumps(m))
        edit(bad)
        with pytest.raises(L.LaneError, match=match):
            L.validate_manifest(bad, src)
    (src / ".git_sha").write_text(row["git_head_at_freeze"] + "\n")  # the parent's export
    with pytest.raises(L.LaneError, match="freeze commit"):
        L.validate_manifest(m, src)
    (src / ".git_sha").write_text("b" * 40 + "\n")
    (src / L.REGISTRATION).write_text("# edited after the freeze\n")
    with pytest.raises(L.LaneError, match="changed after the freeze"):
        L.validate_manifest(m, src)


def _interrupted(root: Path, job: str, m: dict, records: list) -> Path:
    """An interrupted census job's run directory as the lane and the batch file leave it."""
    run = root / job
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps(m, indent=2, sort_keys=True))
    (run / "lane-receipt.json").write_text(json.dumps({"job_id": job, "t_start": 1.0}))
    (run / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    return run


def _phase0_root(tmp_path: Path, monkeypatch) -> Path:
    root = tmp_path / "phase0-runs"
    monkeypatch.setattr(L, "RUN_ROOT", "/")
    monkeypatch.setattr(L, "PHASE0_RUN_ROOT", str(root))
    return root


def test_phase0_resume_is_recomputed_from_the_interrupted_job(tmp_path, monkeypatch):
    src = _source(tmp_path)
    row = _freeze(src)
    base = _manifest(src)
    slots = _census(src, monkeypatch, base)
    monkeypatch.setattr(L, "CAPTURE_CELLS", ("S", "E", "AR"))
    monkeypatch.setattr(L, "IMAGE_OF", {})
    root = _phase0_root(tmp_path, monkeypatch)
    m = _registered(src, row, base)
    assert L.validate_manifest(m, src)

    def rec(slot, status, attempt=1):
        return {"slot": slot["slot"], "block": slot["block"], "status": status,
                "attempt": attempt}

    # block t000 finished; in t001 one slot was lost once and its re-queue cut by the stop signal
    records = [rec(s, "probed") for s in slots[:3]]
    records += [rec(slots[3], "infrastructure"), rec(slots[3], "cap_truncated", 2)]
    records += [rec(s, "probed") for s in slots[4:]]
    run = _interrupted(root, "1300", m, records)
    fields = L.resume_fields(run, slots)
    assert fields["resume_from_block"] == "t001" and fields["slots"] == slots[3:]
    assert fields["resumes"] == {"job_id": "1300", "run_dir": f"{root}/1300",
                                 "records_sha256": L.interrupted_job(run)["records_sha256"]}
    resumed = {**m, **fields}
    assert L.validate_manifest(resumed, src)
    for edit, match in (
        (dict(resume_from_block="t000", slots=slots), "must be t001"),
        (dict(resumes={**fields["resumes"], "records_sha256": "0" * 64}), "records_sha256"),
        (dict(resumes={**fields["resumes"], "run_dir": "/elsewhere/1300"}), "run directory"),
        (dict(resumes={}), "resumes"),
        (dict(slots=slots[4:]), "census suffix"),
    ):
        with pytest.raises(L.LaneError, match=match):
            L.validate_manifest({**resumed, **edit}, src)
    # a resumed job is never resumed again
    again = _interrupted(root, "1301", resumed, [rec(slots[3], "cap_truncated")])
    with pytest.raises(L.LaneError, match="not resumed again"):
        L.resume_fields(again, slots)
    # every slot final (probed, or lost twice): nothing to resume
    done = [rec(s, "probed") for s in slots[:3]]
    done += [rec(slots[3], "infrastructure"), rec(slots[3], "infrastructure", 2)]
    done += [rec(s, "probed") for s in slots[4:]]
    with pytest.raises(L.LaneError, match="final record for every slot"):
        L.resume_fields(_interrupted(root, "1302", m, done), slots)


def test_render_census_resume_from_records_is_what_validation_requires(tmp_path, monkeypatch):
    src = _source(tmp_path)
    row = _freeze(src)
    base = _manifest(src)
    slots = _census(src, monkeypatch, base)
    monkeypatch.setattr(L, "CAPTURE_CELLS", ("S", "E", "AR"))
    monkeypatch.setattr(L, "IMAGE_OF", {})
    root = _phase0_root(tmp_path, monkeypatch)
    m = _registered(src, row, base)
    records = [{"slot": s["slot"], "status": "probed", "attempt": 1} for s in slots[:3]]
    run = _interrupted(root, "1300", m, records)
    monkeypatch.setattr(L, "census_slots", lambda tasks, golds: slots)
    monkeypatch.setattr("harness.s2_locale.golds.pool_tasks", lambda pool: [])
    base_path = tmp_path / "base.json"
    base_path.write_text(json.dumps({k: v for k, v in m.items() if k != "slots"}))
    (tmp_path / "pool.json").write_text("{}")
    (tmp_path / "golds.jsonl").write_text("")
    out = tmp_path / "resume.json"
    assert L.main(["render-census", "--base", str(base_path), "--pool",
                   str(tmp_path / "pool.json"), "--golds", str(tmp_path / "golds.jsonl"),
                   "--resume-from-records", str(run / "probes.jsonl"), "--out", str(out)]) == 0
    resumed = json.loads(out.read_text())
    assert resumed["resume_from_block"] == "t001" and resumed["slots"] == slots[3:]
    assert L.validate_manifest(resumed, src)


def test_submission_runs_the_census_once_and_resumes_it_at_most_once(tmp_path, monkeypatch):
    root = _phase0_root(tmp_path, monkeypatch)
    census = {"purpose": "phase0", "run_root": str(root)}
    resume = {**census, "resume_from_block": "b010"}
    L.check_once(census)  # nothing has run
    _interrupted(root, "1300", census, [])
    with pytest.raises(L.LaneError, match="has run already"):
        L.check_once(census)
    L.check_once(resume)  # the one resume
    _interrupted(root, "1301", resume, [])
    with pytest.raises(L.LaneError, match="resumed already"):
        L.check_once(resume)
    L.check_once({"purpose": "development", "run_root": str(root)})


def test_census_slots_order_and_content():
    pool = [{"task_id": f"{i:08x}-0000-0000-0000-000000000000",
             "split": "dev" if i < 3 else "confirm"} for i in range(10)]
    golds = [{"task_id": pool[0]["task_id"], "job_id": "g", "candidate_sha256": "a" * 64,
              "files": {"/home/user/a.xlsx": {"rel": "x", "sha256": "a" * 64}}},
             {"task_id": pool[5]["task_id"], "job_id": "h", "candidate_sha256": "b" * 64,
              "files": {"/home/user/b.xlsx": {"rel": "y", "sha256": "b" * 64}}}]
    slots = L.census_slots(pool, golds)
    assert slots == L.census_slots(list(reversed(pool)), golds)  # sorted before the draw
    assert len(slots) == 10 * 8 + 3 * 2 + 2 * 5
    assert len({s["slot"] for s in slots}) == len(slots)
    blocks = [s["block"] for s in slots]
    assert blocks[:20] == ["b000"] * 20 and blocks[-1] == f"b{(len(slots) - 1) // 20:03d}"
    pd = [s for s in slots if s["cell"] == "PD"]
    assert len(pd) == 3 and all(s["task_id"] in {t["task_id"] for t in pool[:3]} for s in pd)
    gold = [s for s in slots if s.get("kind") == "gold"]
    assert sorted({s["cell"] for s in gold}) == sorted(L.GOLD_CELLS) and len(gold) == 10
    e2 = [s for s in slots if s["cell"] == "E" and s["rep"] == 2]
    assert len(e2) == 10
    first = [s["cell"] for s in slots[:20]]
    assert first != sorted(first)  # interleaved within the block


def test_pd_slots_mount_the_variant_and_share_the_er_image(tmp_path, monkeypatch):
    src = _source(tmp_path)
    data = json.loads((src / L.IMAGES).read_text())
    data["cells"]["ER"] = dict(data["cells"]["E"], sha256="c" * 64,
                               selector_sha256="3" * 64)  # fmt: skip
    (src / L.IMAGES).write_text(json.dumps(data))
    pins = L.load_pins(src)
    assert pins["PD"] == pins["ER"]
    m = _manifest(src)
    er = {"host_path": f"{s1a.RUN_ROOT}stage0/s2v4/images/ER.qcow2", "sha256": "c" * 64,
          "size_bytes": pins["ER"]["size_bytes"]}
    m["images"].update(ER=er, PD=dict(er))
    m["slots"].append({"slot": L.slot_id(DEV[0], "PD", 1), "task_id": DEV[0], "cell": "PD",
                       "rep": 1, "block": "t000"})
    with pytest.raises(L.LaneError, match="file_cache_pd"):
        L.validate_manifest(m, src)
    from harness.s2_locale import pd_cache

    files = {"libreoffice_calc/x/a.xlsx": "e" * 64}
    man = src / L.PD_CACHE_MANIFEST
    man.parent.mkdir(parents=True, exist_ok=True)
    man.write_text(json.dumps({"files": files, "files_sha256": pd_cache.files_digest(files)}))
    monkeypatch.setattr(L, "PD_CACHE_FILES_SHA256", pd_cache.files_digest(files))
    m["file_cache_pd"] = {"host_dir": f"{s1a.RUN_ROOT}stage0/s2v4/pd-cache/files",
                          "files_sha256": pd_cache.files_digest(files)}
    ok = L.validate_manifest(m, src)
    bad = json.loads(json.dumps(ok))
    bad["images"]["PD"]["host_path"] = f"{s1a.RUN_ROOT}stage0/s2v4/images/E.qcow2"
    with pytest.raises(L.LaneError):
        L.validate_manifest(bad, src)
    cfg = s1a.LaneConfig(ok, "7", tmp_path / "run", src)
    pd_argv = L.episode_argv(cfg, "e", "vm", tmp_path, None, "capture", "PD")
    er_argv = L.episode_argv(cfg, "e", "vm", tmp_path, None, "capture", "ER")
    assert f"{s1a.RUN_ROOT}stage0/s2v4/pd-cache/files:/inputs/file_cache/files:ro" in pd_argv
    assert f"{s1a.RUN_ROOT}x/files:/inputs/file_cache/files:ro" in er_argv
    assert L.image_bytes(ok) == sum(e["size_bytes"] for c, e in ok["images"].items()
                                    if c != "PD")  # the shared ER file counts once


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
        self.started_episodes: list[list[str]] = []

    def start_vm(self, argv):
        self.started.append(argv)

    def run_episode(self, argv, name, timeout, stop, log):
        self.started_episodes.append(argv)
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
    def __init__(self, selector, pointer_after=None, events=None):
        self.selector = selector
        self.hashes = 0
        self.pointer_after = pointer_after
        self.events = events if events is not None else []

    def run_script(self, source, args):
        self.events.append(args[0])
        if args[0] == "pointer":
            cfg = json.loads(args[1])
            target = [cfg["x"], cfg["y"]]
            return {"target": target, "before": [1728, 972],
                    "after": self.pointer_after or target}
        if args[0] == "hash":
            self.hashes += 1
            paths = json.loads(args[1])["paths"]
            return {"files": [{"path": p, "exists": True, "sha256": str(self.hashes),
                               "mtime_ns": self.hashes} for p in paths]}
        if args[0] == "registry":
            cfg = json.loads(args[1])
            return {"path": cfg["path"], "exists": True, "sha256": "r" * 64, "items": 3,
                    "values": {f"{a}|{b}": ["3"] for a, b in cfg["keys"]}}
        if args[0] == "end":
            return {"fc_match_ar": "DejaVu Sans", "packages": {}}
        assert args[0] == "facts"
        return {"selector_sha256": self.selector, "keyboard_layout": "us", "window_titles": []}

    def screenshot(self, timeout=10.0):
        return 200, b"\x89PNG\r\n\x1a\n" + b"0" * 100, 0.01

    def _request(self, method, path, timeout=None, **kw):
        return 200, json.dumps({"AT": A11Y.format(a="File", b="Edit", c="B", x1=1,
                                                  x2=50)}).encode(), 0.01


class FakeSession:
    evaluate_replies: list = []

    def __init__(self, replies=None):
        self.evaluate_replies = list(replies or [])

    def setup(self):
        return {"failures": [], "steps": 2}

    def evaluate(self, last):
        return 0.0

    def close(self):
        pass


def _probe(tmp_path, selector_in_guest, expected, replies=None, task_id=None, guest=None,
           events=None):
    cfg = P.ProbeConfig(lane="l", purpose="development", slot="s", task_id=task_id or DEV[0],
                        cell="E", block="t000", attempt=1, image_sha256="e" * 64,
                        selector_sha256=expected, out_dir=str(tmp_path / "out"))
    task = {"id": DEV[0], "evaluator": {"result": {"type": "vm_file", "path": "~/x.xlsx"}}}
    events = events if events is not None else []
    probe = P.Probe(cfg, guest=guest or FakeGuest(selector_in_guest, events=events), task=task,
                    session_factory=lambda c, t: FakeSession(replies),
                    sleep=lambda s: events.append(("sleep", s)), gpu_glob=lambda: [])
    probe._runner.warm_up = lambda: events.append("warm_up")
    probe._runner.check_restarts = lambda key="server_end": None
    return probe.run()


def test_probe_warps_the_pointer_after_the_warm_up_and_before_the_settle(tmp_path):
    events: list = []
    rec = _probe(tmp_path, SEL["E"], SEL["E"], events=events)
    assert rec["status"] == "probed"
    start = events.index("warm_up")
    assert events[start:start + 3] == ["warm_up", "pointer", ("sleep", 60.0)]
    assert events.count("pointer") == 1  # once per boot
    assert rec["pointer"] == {"target": list(P.POINTER_TARGET), "before": [1728, 972],
                              "after": list(P.POINTER_TARGET), "moved": True}


def test_a_pointer_read_back_elsewhere_is_infrastructure(tmp_path):
    guest = FakeGuest(SEL["E"], pointer_after=[1728, 972])
    rec = _probe(tmp_path, SEL["E"], SEL["E"], guest=guest)
    assert rec["status"] == "infrastructure" and rec["infrastructure_type"] == "probe:pointer"
    assert "post_setup" not in rec  # nothing is observed after a failed warp


def test_guest_pointer_mode_is_one_absolute_xtest_motion(monkeypatch):
    """The guest helper's ``pointer`` mode with a stand-in python-xlib: one XTest MotionNotify at
    the target, an XSync, and the position read before and after."""
    import importlib.util
    import sys
    import types

    calls: list = []
    position = {"xy": (1728, 972)}

    class Reply:
        def __init__(self, xy):
            self.root_x, self.root_y = xy

    class Root:
        def query_pointer(self):
            return Reply(position["xy"])

    class Display:
        def __init__(self, name=None):
            calls.append(("display", name))

        def screen(self):
            return types.SimpleNamespace(root=Root())

        def sync(self):
            calls.append("sync")

        def close(self):
            calls.append("close")

    def fake_input(d, kind, x=None, y=None):
        calls.append(("fake_input", kind, x, y))
        position["xy"] = (x, y)

    xlib = types.ModuleType("Xlib")
    xlib.X = types.SimpleNamespace(MotionNotify=6)
    xlib.display = types.SimpleNamespace(Display=Display)
    ext = types.ModuleType("Xlib.ext")
    ext.xtest = types.SimpleNamespace(fake_input=fake_input)
    for name, mod in {"Xlib": xlib, "Xlib.ext": ext, "Xlib.ext.xtest": ext.xtest,
                      "Xlib.display": xlib.display, "Xlib.X": xlib.X}.items():
        monkeypatch.setitem(sys.modules, name, mod)
    spec = importlib.util.spec_from_file_location("s2_guest", P.GUEST_SCRIPT)
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)
    monkeypatch.setattr(guest.time, "sleep", lambda s: None)
    out = guest.MODES["pointer"]({"x": 995, "y": 540})
    assert out == {"target": [995, 540], "before": [1728, 972], "after": [995, 540]}
    motions = [c for c in calls if isinstance(c, tuple) and c[0] == "fake_input"]
    assert motions == [("fake_input", 6, 995, 540)]  # one jump, no intermediate position
    assert calls.index("sync") > calls.index(motions[0]) and calls[-1] == "close"


def test_probe_records_a_probed_slot(tmp_path):
    rec = _probe(tmp_path, SEL["E"], SEL["E"])
    assert rec["status"] == "probed" and rec["verdict"] == "fail" and rec["score"] == 0.0
    assert rec["post_setup"]["stable"] is True
    assert rec["post_setup"]["a11y"]["summary"]["menubar_order"] == "ltr"
    assert rec["result_files"]["/home/user/x.xlsx"]["rewritten"] is True
    assert (tmp_path / "out/screens/post_setup-1.png").is_file()
    assert json.loads((tmp_path / "out/probe.json").read_text())["slot"] == "s"


def test_probe_reads_p010_and_end_facts(tmp_path):
    rec = _probe(tmp_path, SEL["E"], SEL["E"], task_id="2cd43775-7085-45d8-89fa-9e35c0a915cf")
    key = "/org.openoffice.Office.Common/Save/Document|AutoSaveTimeIntervall"
    assert rec["p010"]["keys"] == [list(P.P010_KEYS["2cd43775"][0])]
    assert rec["p010"]["values"] == {key: ["3"]} and rec["p010"]["path"] == P.REGISTRY_XCU
    assert rec["end_facts"]["fc_match_ar"] == "DejaVu Sans"
    other = _probe(tmp_path, SEL["E"], SEL["E"])  # a dev task reads all three keys
    assert len(other["p010"]["values"]) == len(P.P010_ALL) == 3


@pytest.mark.parametrize("status", [500, 503, None])
def test_postconfig_server_error_is_infrastructure(tmp_path, status):
    reply = {"phase": "evaluate", "step": 1, "type": "execute", "path": "/setup/execute",
             "status": status}
    rec = _probe(tmp_path, SEL["E"], SEL["E"], replies=[reply])
    assert rec["status"] == "infrastructure"
    assert rec["infrastructure_type"] == "probe:postconfig_server_error"
    assert rec["postconfig"]["replies"]  # the replies are kept with the loss


def test_postconfig_returncode_under_http_200_is_scored(tmp_path):
    reply = {"phase": "evaluate", "step": 1, "type": "execute", "path": "/setup/execute",
             "status": 200, "returncode": 1}
    rec = _probe(tmp_path, SEL["E"], SEL["E"], replies=[reply])
    assert rec["status"] == "probed" and rec["postconfig"]["failures"]


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


GOLD_REL = "libreoffice_calc/12382c62-0cd1-4bf2-bdc8-1d20bf9b2371/13_WeeklySales_gt1.xlsx"


def _gold_row():
    sha = L.file_cache_receipts(ROOT)[GOLD_REL]
    return {"task_id": "12382c62-0cd1-4bf2-bdc8-1d20bf9b2371", "job_id": "12382c62__gold",
            "candidate_sha256": sha, "files": {"/home/user/WeeklySales.xlsx":
                                               {"rel": GOLD_REL, "sha256": sha}}}


def test_gold_slots_render_validate_and_run(tmp_path):
    src = _source(tmp_path)
    m = _manifest(src)
    m = L.render(m, ["12382c62-0cd1-4bf2-bdc8-1d20bf9b2371"], ["S", "E", "AR"])
    m = L.render_gold(m, [_gold_row()], ["E", "AR"])
    m = L.validate_manifest(m, src)
    gold = [s for s in m["slots"] if s.get("kind") == "gold"]
    assert [s["slot"] for s in gold] == ["12382c6:E:g1".replace("12382c6", "12382c62"),
                                         "12382c62:AR:g1"]
    assert gold[0]["block"] == "t000"
    seen: list[dict] = []
    docker = FakeDocker(seen)
    lane = L.S2Lane(s1a.LaneConfig(m, "779", tmp_path / "run", src), docker=docker,
                    verify=False, certified=[])
    lane.run()
    modules = [argv[argv.index("-m") + 1] for argv in docker.started_episodes]
    assert modules.count("harness.s2_locale.vm_gold") == 2
    cfg = [c for c in seen if "gold" in c][0]
    assert cfg["gold"]["job_id"] == "12382c62__gold" and cfg["selector_sha256"] in SEL.values()


@pytest.mark.parametrize("edit, match", [
    (lambda g: g["files"]["/home/user/WeeklySales.xlsx"].update(sha256="0" * 64), "receipts"),
    (lambda g: g.update(candidate_sha256="1" * 64), "candidate"),
    (lambda g: g["files"].update({"/etc/x": {"rel": GOLD_REL, "sha256": g["candidate_sha256"]}}),
     "outside"),
])
def test_gold_slot_refusals(tmp_path, edit, match):
    src = _source(tmp_path)
    m = L.render(_manifest(src), ["12382c62-0cd1-4bf2-bdc8-1d20bf9b2371"], ["E"])
    row = _gold_row()
    edit(row)
    m = L.render_gold(m, [row], ["E"])
    with pytest.raises(L.LaneError, match=match):
        L.validate_manifest(m, src)


def test_gold_wrapper_config_and_record():
    from harness.s2_locale import vm_gold as G

    row = _gold_row()
    cfg = {"lane": "l", "purpose": "development", "slot": "12382c62:E:g1",
           "task_id": row["task_id"],
           "cell": "E", "block": "t000", "rep": 1, "attempt": 1, "image_sha256": "e" * 64,
           "selector_sha256": SEL["E"], "guest_ip": "20.20.20.21", "server_port": 5000,
           "osworld_dir": "/inputs/OSWorld", "settle_after_reset_s": 60, "settle_before_eval_s": 20,
           "gold": {k: row[k] for k in ("job_id", "candidate_sha256", "files")}}
    k2 = G.k2_config(cfg)
    from harness.q2_mutation_k2.executor import K2Config

    parsed = K2Config.from_json(k2)
    assert parsed.files["/home/user/WeeklySales.xlsx"]["local"].endswith(GOLD_REL)
    ok = G.gold_record(cfg, {"status": "scored", "score": 1.0, "verdict": "pass"}, SEL["E"], None)
    assert ok["status"] == "probed" and ok["verdict"] == "pass"
    wrong = G.gold_record(cfg, {"status": "scored", "score": 1.0, "verdict": "pass"}, None, None)
    assert wrong["status"] == "infrastructure" and wrong["verdict"] is None
    lost = G.gold_record(cfg, {"status": "infrastructure", "infrastructure_type": "vm_boot"},
                         SEL["E"], None)
    assert lost["infrastructure_type"] == "vm_boot"
    err = G.gold_record(cfg, {"status": "scored", "score": 1.0, "verdict": "pass",
                              "postconfig_replies": [{"status": 500}, {"status": 200}]},
                        SEL["E"], None)
    assert err["status"] == "infrastructure" and err["verdict"] is None
    assert err["infrastructure_type"] == "probe:postconfig_server_error"
    rc = G.gold_record(cfg, {"status": "scored", "score": 0.0, "verdict": "fail",
                             "postconfig_replies": [{"status": 200, "returncode": 1}]},
                       SEL["E"], None)
    assert rc["status"] == "probed" and rc["k2"]["postconfig_replies"]


def test_committed_census_is_the_registered_render():
    import hashlib

    from harness.s2_locale.golds import POOL, pool_tasks

    path = ROOT / L.CENSUS
    assert hashlib.sha256(path.read_bytes()).hexdigest() == L.CENSUS_SHA256
    census = json.loads(path.read_text())
    golds_path = ROOT / L.GOLDS
    golds = [json.loads(x) for x in golds_path.read_text().splitlines() if x.strip()]
    tasks = pool_tasks(json.loads((ROOT / POOL).read_text()))
    assert len(tasks) == 106 and len(golds) == 88
    assert census["golds_sha256"] == hashlib.sha256(golds_path.read_bytes()).hexdigest()
    assert census["slots"] == L.census_slots(tasks, golds)
    kinds = [s.get("kind", "capture") for s in census["slots"]]
    assert kinds.count("capture") == 882 and kinds.count("gold") == 440
    receipts = L.file_cache_receipts(ROOT)
    for s in census["slots"]:
        if s.get("kind") == "gold":
            L.check_gold(s["slot"], s["gold"], receipts)


def test_committed_pd_variant_is_pinned():
    from harness.s2_locale import pd_cache

    data = json.loads((ROOT / L.PD_CACHE_MANIFEST).read_text())
    assert data["files_sha256"] == pd_cache.files_digest(data["files"]) == L.PD_CACHE_FILES_SHA256
    planted = {p["task_id"][:8] for p in data["plants"] if p.get("planted")}
    from harness.s2_locale import k0_v4

    assert set(k0_v4.PD_VISIBLE_DEV) <= planted  # every named PD control has a plant


def test_registered_base_matches_the_pins_and_the_budget():
    m = L.registered_base(ROOT)
    pins = L.load_pins(ROOT)
    assert set(m["images"]) == {*L.CAPTURE_CELLS, "PD"}
    for cell, entry in m["images"].items():
        assert entry["sha256"] == pins[cell]["sha256"]
    assert m["images"]["PD"] == m["images"]["ER"]
    census = json.loads((ROOT / L.CENSUS).read_text())
    full = L.render_census(m, census["slots"])
    got = L.check_slurm(full)
    assert got["cpus"] == 81 and got["memory_gb"] == 126
    assert got["minutes"] == got["hash_minutes"] + got["slot_minutes"] + 10
