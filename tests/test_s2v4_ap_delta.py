"""S2 v4 K1: ap_delta's plan, manifests, harness/q2 admission and rung verdict (no Docker)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from harness.s2_locale import ap_delta as D
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]


def test_committed_k1_plan_is_the_registered_plan():
    data = (ROOT / D.K1_PLAN).read_bytes()
    assert hashlib.sha256(data).hexdigest() == D.K1_PLAN_SHA256
    ops = yaml.safe_load((ROOT / "harness/q2/action_path/mutation_operators.yaml").read_text())
    plan = json.loads(data)["campaigns"]
    assert plan == D.k1_plan_entries(ops)
    assert len(plan) == 284
    per = {}
    for e in plan:
        per.setdefault((e["check"], e["cell"]), []).append(e)
    for cell in D.K1_CELLS:
        assert len(per[("C3", cell)]) == 47  # 44 mutant runs and 3 references, as attempt 1
        assert len(per[("A1", cell)]) == 2 and len(per[("C1", cell)]) == 2
    assert [e["layer"] for e in per[("A3", "AR")]] == ["L0-fixed", "H-OSW-fixed", "H-GA"]
    (rung,) = per[("rung", "E+A+ER+AR+PL")]
    assert rung["concurrency"] == D.RUNG_N == 20 and rung["seed"] == 43


def _dev_source(tmp_path: Path) -> Path:
    """A pre-freeze view of the tree: the harness and the ledger's rows before this id's (so the
    test holds whether or not the repository's own ledger already freezes S2 v4)."""
    import shutil

    src = tmp_path / "src"
    shutil.copytree(ROOT / "harness", src / "harness",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))  # fmt: skip
    (src / "program/preregistrations").mkdir(parents=True)
    lines = []
    for line in (ROOT / L.LEDGER).read_text().splitlines():
        if line.strip() and json.loads(line).get("experiment_id") == L.EXPERIMENT_ID:
            break
        lines.append(line)
    (src / L.LEDGER).write_text("\n".join(lines) + "\n")
    return src


def _args(tmp_path):
    return argparse.Namespace(source_dir=_dev_source(tmp_path), git_sha="f" * 40,
                              host_root=f"{L.RUN_ROOT}stage0/s2v4/apdelta-dev",
                              images_root=f"{L.RUN_ROOT}stage0/s2v4/image-build-v5/a")


def test_development_manifest_is_admitted_by_harness_q2(tmp_path):
    args = _args(tmp_path)
    m = D.render_dev(args)
    assert m["purpose"] == "development" and len(m["campaigns"]) == 2
    single, rung = m["campaigns"]
    assert single["cells"] == ["E"] and not D.is_rung(single)
    assert rung["cells"] == ["E", "AR"] and D.is_rung(rung)
    pins = L.load_pins(args.source_dir)
    assert single["manifest"]["vm"]["qcow2"]["sha256"] == pins["E"]["sha256"]
    assert rung["qcow2"]["AR"]["sha256"] == pins["AR"]["sha256"]
    for key, value in D.CERTIFIED_PROVENANCE.items():
        assert single["manifest"]["vm"]["qcow2"][key] == value
    assert single["manifest"]["workload"]["sessions"] == 1
    assert rung["manifest"]["workload"]["sessions"] == 2  # one per image
    slurm = D.check_slurm(m)
    assert slurm["budget_minutes"] <= m["slurm"]["minutes"]


@pytest.mark.parametrize("edit, match", [
    (lambda m: m["campaigns"][0]["manifest"]["vm"]["qcow2"].update(sha256="0" * 64), "pinned"),
    (lambda m: m["campaigns"][0]["manifest"]["vm"]["qcow2"].update(revision="0" * 40),
     "certified disk"),
    (lambda m: m["campaigns"][0]["manifest"]["randomness"].update(seeds=[43]), "harness/q2"),
    (lambda m: m["campaigns"][0].update(cells=["S"]), "cells"),
    (lambda m: m.update(purpose="k1"), "only after the freeze"),
    (lambda m: m["campaigns"][1]["qcow2"].pop("AR"), "qcow2 per cell"),
])
def test_development_manifest_refusals(tmp_path, edit, match):
    args = _args(tmp_path)
    m = D.render_dev(args)
    edit(m)
    with pytest.raises(D.DeltaError, match=match):
        D.validate_manifest(m, args.source_dir)


def test_campaign_minutes_include_both_image_checks():
    q2m = {"slurm": {"minutes": 40}}
    assert D.campaign_minutes(q2m, 24_459_214_848) == 40 + 2 * 1


def _session(cycle, steps):
    return {"cycle": cycle, "trials": [{"steps_s": steps}], "snapshots": [{}, {}]}


def test_rung_verdict_reads_the_step_p95_per_image(monkeypatch):
    from harness.q2.action_path import acceptance as A

    monkeypatch.setattr(A, "rung", lambda campaigns, ref: {"qualifies": True, "problems": [],
                                                           "aborted": False})
    image_of = {str(i): D.RUNG_CELLS[i % 5] for i in range(10)}
    sessions = [_session(i, [1.0] * 20) for i in range(10)]
    sessions[3]["trials"][0]["steps_s"] = [5.0] * 20  # image AR (3 mod 5) is slow
    rung = [{"receipt": {"image_of_session": image_of}, "sessions": sessions}]
    a1 = {c: [{"sessions": [_session(0, [1.0] * 20)]}] for c in D.RUNG_CELLS}
    out = D.rung_verdict(rung, a1)
    assert not out["qualifies"] and not out["per_image_step"]["AR"]["ok"]
    assert all(out["per_image_step"][c]["ok"] for c in D.RUNG_CELLS if c != "AR")
    sessions[3]["trials"][0]["steps_s"] = [1.5] * 20  # within 2 x its own A1
    assert D.rung_verdict(rung, a1)["qualifies"]
    assert not D.rung_verdict([], a1)["qualifies"]


def test_run_rung_puts_session_i_on_image_i_mod_n(tmp_path, monkeypatch):
    """run_rung is driver.main's concurrent branch with a per-worker disk (driver stubbed)."""
    from harness.q2.vm import driver

    args = _args(tmp_path)
    m = D.render_dev(args)
    item = json.loads(json.dumps(m["campaigns"][1]))  # the development rung over E and AR
    item["cells"] = ["E", "AR"]
    seen: dict[int, str] = {}
    plan = [{"setting": "screenshot", "index": i, "trials": [[0, "type_plain"]]} for i in range(6)]
    monkeypatch.setattr(D.os, "stat", lambda p, follow_symlinks=False: type(
        "S", (), {"st_size": 24_459_214_848, "st_mode": 0o100444})())
    monkeypatch.setattr(D.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(D.os.path, "islink", lambda p: False)
    digest = {e["host_path"]: e["sha256"] for e in item["qcow2"].values()}
    monkeypatch.setattr(driver, "sha256_file", lambda p: digest[p])
    monkeypatch.setattr(driver, "session_plan", lambda q, c: plan)
    monkeypatch.setattr(driver, "slurm_cpu_ids", lambda j: list(range(16)))
    monkeypatch.setattr(driver, "numa_nodes", lambda: {0: set(range(16))})
    monkeypatch.setattr(driver, "snapshot_host", lambda j: {"t": 0, "squeue_foreign": []})

    def run_cycle(q2m, job, cycle, prev, run_dir, src, cpus, session=None):
        seen[cycle] = q2m["vm"]["qcow2"]["sha256"]
        return {"cycle": cycle, "token": f"t{cycle}"}

    monkeypatch.setattr(driver, "run_cycle", run_cycle)
    monkeypatch.setattr(driver, "cycle_verdict", lambda r, t: {"ok": True})
    monkeypatch.setattr(driver, "summarize", lambda v, r: {
        "boots_ok": len(r), "cycles": len(r), "no_gpu_all": True, "no_published_ports_all": True,
        "containers_removed_all": True, "leaked_volumes": []})
    monkeypatch.setattr(driver, "session_summary", lambda r: {"runner_errors": []})
    monkeypatch.setattr(D, "docker", lambda *a, **k: type("P", (), {"stdout": ""})())
    q2m = item["manifest"]
    pre: list = []

    def run(argv, timeout=120.0, check=True):
        pre.append(argv)
        if argv[1] == "info":
            out = json.dumps({"ServerVersion": "27", "DefaultRuntime": "runc"})
        elif argv[1:3] == ["image", "inspect"] and argv[-1] == q2m["vm"]["image_id"]:
            out = f"{q2m['vm']['image_id']} [\"{q2m['vm']['image']}\"]"
        elif argv[1:3] == ["image", "inspect"]:
            out = q2m["runner"]["image_id"]
        elif argv[1] == "run":  # qemu-img info, one per image
            out = json.dumps({"format": "qcow2", "virtual-size": 53687091200})
        else:  # dangling volumes
            out = ""
        return type("P", (), {"stdout": out})()

    monkeypatch.setattr(driver, "run", run)
    rc = D.run_rung(item, tmp_path / "run", Path(args.source_dir), "77")
    assert rc == 0
    # driver.main's pre-run checks, made before any session: docker info, the VM and runner
    # images, qemu-img info per image, the dangling volumes before (and after)
    assert [a[1] for a in pre[:3]] == ["info", "image", "image"]
    assert sum(1 for a in pre if a[1] == "run") == 2
    assert [a[1:3] for a in pre].count(["volume", "ls"]) == 2
    pins = L.load_pins(args.source_dir)
    assert [seen[i] for i in range(6)] == [pins["E"]["sha256"], pins["AR"]["sha256"]] * 3
    receipt = json.loads((tmp_path / "run" / "receipt.json").read_text())
    assert receipt["qcow2_unchanged"] and receipt["summary"]["infra_gates_pass"]
    assert receipt["image_of_session"] == {str(i): ["E", "AR"][i % 2] for i in range(6)}
    assert (tmp_path / "run" / "preflight.txt").read_text().splitlines()[-1] == (
        "driver_exit=0 labelled_containers_left=0")
    assert set(receipt["qcow2_info"]) == {"E", "AR"} and receipt["docker"]["server_version"]
    assert receipt["dangling_volumes_before"] == receipt["dangling_volumes_after"] == 0
    # a missing runner image stops the rung before any session, as driver.main stops
    seen.clear()
    monkeypatch.setattr(driver, "run", lambda argv, timeout=120.0, check=True: type(
        "P", (), {"stdout": "" if argv[-1] == q2m["runner"]["image_id"] else run(argv).stdout})())
    assert D.run_rung(item, tmp_path / "run2", Path(args.source_dir), "78") == 3
    assert not seen and "runner image is missing" in json.loads(
        (tmp_path / "run2" / "receipt.json").read_text())["error"]


def test_k1_job_campaigns_all_run_on_one_image(monkeypatch):
    """check_registered matches the plan on the first campaign's image: every other campaign of
    the job must run on that image too."""
    entry = {"kind": "suite-acceptance", "criterion": "C1", "layer": "H-GA-buggy", "seed": 42,
             "mutant": None, "concurrency": 1}
    other = dict(entry, layer="H-OSW-up")
    monkeypatch.setattr(D, "load_k1_plan", lambda src: [
        {"check": "C1", "cell": "E", **entry}, {"check": "C1", "cell": "E", **other}])

    def item(cell, key):
        q2m = {"workload": {k: key[k] for k in ("kind", "criterion", "layer", "mutant")},
               "randomness": {"seeds": [key["seed"]]},
               "vm": {"concurrency": 1, "qcow2": {"host_path": f"/x/{cell}.qcow2"}},
               "purpose": "acceptance", "run_root": f"{D.K1_ROOT}/x"}
        return {"cells": [cell], "manifest": q2m}

    m = {"check": "C1", "campaigns": [item("E", entry), item("E", other)]}
    D.check_registered(m, Path("."))
    m["campaigns"][1] = item("A", other)
    with pytest.raises(D.DeltaError, match="first campaign's image"):
        D.check_registered(m, Path("."))
