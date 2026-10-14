"""S2 v5: the census lane under v5's id (vm_lane's own code, bound to v5; no Docker, no VM)."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from harness.q2_stage1 import lane as s1a
from harness.s2_locale import lane_v5 as LV
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]
DEV = json.loads((ROOT / L.SPLITS).read_text())["dev"]
V4 = {"EXPERIMENT_ID": "s2-arabic-cua-locale-v4",
      "REGISTRATION": "program/preregistrations/s2-arabic-cua-locale-v4.md",
      "PHASE0_RUN_ROOT": f"{s1a.RUN_ROOT}stage0/s2v4/phase0-runs",
      "BATCH": "infra/slurm/host-single-node/s2v4-vm.sbatch"}  # fmt: skip
POOL = (
    "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool/pool-v3.json"
)


def test_importing_lane_v5_leaves_vm_lane_v4s_and_bound_restores_it():
    assert {k: getattr(L, k) for k in V4} == V4
    with LV.bound() as lane:
        assert lane is L
        assert {k: getattr(L, k) for k in V4} == LV.BINDING
        assert L.EXPERIMENT_ID == "s2-arabic-cua-locale-v5"
        assert f"{s1a.RUN_ROOT}stage0/s2v5/phase0-runs" == L.PHASE0_RUN_ROOT
    assert {k: getattr(L, k) for k in V4} == V4
    with pytest.raises(RuntimeError), LV.bound():
        raise RuntimeError
    assert {k: getattr(L, k) for k in V4} == V4
    # the census, its pin and every other constant stay v4's
    assert L.CENSUS == "experiments/manifests/s2v4/phase0-census.json"
    assert hashlib.sha256((ROOT / L.CENSUS).read_bytes()).hexdigest() == L.CENSUS_SHA256


def _source(tmp_path: Path) -> Path:
    src = tmp_path / "src"
    (src / "harness/s2_locale").mkdir(parents=True)
    (src / "program/evidence/q2-mutation/harness").mkdir(parents=True)
    shutil.copy(ROOT / L.SPLITS, src / L.SPLITS)
    shutil.copy(ROOT / L.FILE_CACHE_RECEIPTS, src / L.FILE_CACHE_RECEIPTS)
    (src / L.IMAGES).write_text(
        json.dumps(
            {
                "schema": "s2v4-images-v1",
                "cells": {
                    "E": {"sha256": "e" * 64, "size_bytes": 10, "selector_sha256": "1" * 64},
                    "AR": {"sha256": "b" * 64, "size_bytes": 11, "selector_sha256": "2" * 64},
                },
            }
        )
    )
    return src


def _row(src: Path, experiment_id: str, path: str, previous: str) -> dict:
    reg = src / path
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(f"# {experiment_id} frozen stand-in\n")
    body = {"experiment_id": experiment_id, "frozen_at": "2026-10-14T00:00:00Z",
            "git_head_at_freeze": "a" * 40, "path": path, "previous_hash": previous,
            "sha256": hashlib.sha256(reg.read_bytes()).hexdigest()}  # fmt: skip
    body["hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return body


def _freeze(src: Path) -> tuple[dict, dict]:
    """Scratch freezes of v4 (its row) and v5 (the next row) in ``src``'s own ledger; the
    export's ``.git_sha`` is v5's freeze commit."""
    v4 = _row(src, V4["EXPERIMENT_ID"], V4["REGISTRATION"], "0" * 64)
    v5 = _row(src, LV.EXPERIMENT_ID, LV.REGISTRATION, v4["hash"])
    (src / L.LEDGER).write_text(json.dumps(v4) + "\n" + json.dumps(v5) + "\n")
    (src / ".git_sha").write_text("b" * 40 + "\n")
    return v4, v5


def _phase0(src: Path, row: dict, monkeypatch) -> dict:
    """A phase0 manifest over a stand-in census of three cells (pinned for the test)."""
    pins = L.load_pins(src)
    images = {c: {"host_path": f"{s1a.RUN_ROOT}stage0/s2v4/images/{c}.qcow2",
                  "sha256": pins[c]["sha256"], "size_bytes": pins[c]["size_bytes"]}
              for c in ("S", "E", "AR")}  # fmt: skip
    images["S"]["host_path"] = L.S_HOST_PATH
    base = {"schema": L.SCHEMA, "experiment_id": L.EXPERIMENT_ID, "purpose": "phase0",
            "name": "s2v5-phase0", "run_root": L.PHASE0_RUN_ROOT,
            "vm": {**L.VM_PINS, "guest_ip": "20.20.20.21", "concurrency": L.V_REGISTERED,
                   "hmp_port": 7100},
            "images": images, "episode_image_id": L.EPISODE_IMAGE_ID,
            "osworld": {"commit": L.OSWORLD_COMMIT, "host_dir": L.OSWORLD_HOST},
            "file_cache": {"host_dir": L.FILE_CACHE_HOST},
            "episode_timeout_s": L.EPISODE_TIMEOUT_S, "settle_after_reset_s": 60,
            "settle_before_eval_s": 20, "evaluate": True, "mode": L.MODE,
            "engine": {"kind": "none"}, "slurm": {"cpus": 81, "memory_gb": 126, "minutes": 60},
            "freeze": {"commit": "b" * 40, "ledger_row_hash": row["hash"],
                       "git_head_at_freeze": row["git_head_at_freeze"]}}  # fmt: skip
    m = L.render(base, DEV[:2], ["S", "E", "AR"])
    path = src / L.CENSUS
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"schema": "s2v4-census-v1", "slots": m["slots"]}))
    monkeypatch.setattr(L, "CENSUS_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(L, "CAPTURE_CELLS", ("S", "E", "AR"))
    monkeypatch.setattr(L, "IMAGE_OF", {})
    return m


def test_a_v5_census_job_is_admitted_only_under_v5(tmp_path, monkeypatch):
    src = _source(tmp_path)
    v4, v5 = _freeze(src)
    with LV.bound():
        m = _phase0(src, v5, monkeypatch)
        assert m["experiment_id"] == LV.EXPERIMENT_ID and m["run_root"] == LV.PHASE0_RUN_ROOT
        assert L.validate_manifest(m, src)["purpose"] == "phase0"
        for edit, match in (
            (lambda x: x.update(experiment_id=V4["EXPERIMENT_ID"]), "experiment_id"),
            (lambda x: x["freeze"].update(ledger_row_hash=v4["hash"]), "another ledger row"),
            (lambda x: x.update(run_root=V4["PHASE0_RUN_ROOT"]), "phase0 runs into"),
            (lambda x: x.update(slots=x["slots"][1:]), "census"),
            (lambda x: x.update(purpose="development"), "frozen: development no longer runs"),
        ):
            bad = json.loads(json.dumps(m))
            edit(bad)
            with pytest.raises(L.LaneError, match=match):
                L.validate_manifest(bad, src)
        (src / LV.REGISTRATION).write_text("# edited after the freeze\n")
        with pytest.raises(L.LaneError, match="changed after the freeze"):
            L.validate_manifest(m, src)
    # vm_lane unbound is v4's gate: it refuses v5's manifest
    with pytest.raises(L.LaneError, match="experiment_id must be s2-arabic-cua-locale-v4"):
        L.validate_manifest(m, src)


def test_without_v5s_row_the_v5_census_is_refused(tmp_path, monkeypatch):
    src = _source(tmp_path)
    v4, v5 = _freeze(src)
    (src / L.LEDGER).write_text(json.dumps(v4) + "\n")  # v4 frozen, v5 not
    with LV.bound():
        m = _phase0(src, v5, monkeypatch)
        with pytest.raises(L.LaneError, match="only after the freeze"):
            L.validate_manifest(m, src)


def test_main_runs_vm_lane_main_bound_and_names_the_census_job(monkeypatch):
    seen = {}

    def fake_main(argv):
        seen["argv"] = argv
        seen["bound"] = {k: getattr(L, k) for k in V4}
        return 0

    monkeypatch.setattr(L, "main", fake_main)
    assert LV.main(["render-census", "--pool", "p", "--golds", "g", "--out", "o"]) == 0
    assert seen["argv"][-2:] == ["--name", LV.NAME] and seen["bound"] == LV.BINDING
    assert LV.main(["render-census", "--name", "x", "--out", "o"]) == 0
    assert seen["argv"].count("--name") == 1
    assert LV.main(["validate", "m.json"]) == 0 and seen["argv"] == ["validate", "m.json"]
    assert {k: getattr(L, k) for k in V4} == V4


def test_render_census_under_v5_is_v4s_committed_census(tmp_path):
    """vm_lane's own render-census, bound to v5: v5's id, name and run root, and exactly the
    slots of v4's committed census (no freeze commit here, so no ledger row is needed)."""
    out = tmp_path / "census.json"
    assert (
        LV.main(
            [
                "render-census",
                "--pool",
                str(ROOT / POOL),
                "--golds",
                str(ROOT / L.GOLDS),
                "--source-dir",
                str(ROOT),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    m = json.loads(out.read_text())
    assert m["experiment_id"] == LV.EXPERIMENT_ID and m["name"] == LV.NAME
    assert m["run_root"] == LV.PHASE0_RUN_ROOT and m["purpose"] == "phase0"
    census = json.loads((ROOT / L.CENSUS).read_text())
    assert m["slots"] == census["slots"] and len(m["slots"]) == 1322


def test_vm_batch_is_v4s_with_the_names_and_the_program_changed():
    text = (ROOT / LV.BATCH).read_text()
    v4 = (ROOT / V4["BATCH"]).read_text()
    assert "python3 -E -s -m harness.s2_locale.lane_v5 run" in text
    assert "#SBATCH --gres" not in text and "refusing to start VMs" in text
    body = lambda t: t[t.index("set -Eeuo pipefail") :]  # noqa: E731
    mapped = body(text).replace("lane_v5 run", "vm_lane run")
    differ = [(a, b) for a, b in zip(mapped.splitlines(), body(v4).splitlines(), strict=True)
              if a != b]  # fmt: skip
    assert all("s2v5" in a.lower() or "S2 v5" in a for a, _ in differ), differ
    # vm_lane.submit's variable names are the ones the batch file reads
    assert "COTCODEC_S2V4_MANIFEST_PATH_HEX" in text
