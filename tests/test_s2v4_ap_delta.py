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
