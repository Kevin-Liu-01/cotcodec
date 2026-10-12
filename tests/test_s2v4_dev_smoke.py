"""S2 v4 round 4 (D90): the development smoke's manifest and its reading (no VM)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from harness.s2_locale import dev_smoke as S
from harness.s2_locale import vm_lane as L

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "program/proposals/evidence/2026-10-11-s2v3-arabic-cua-locale-pilot/compute/pool" / (
    "pool-v3.json")
V4 = ROOT / "experiments/manifests/s2v4/dev-smoke-v4.json"
V5 = ROOT / "experiments/manifests/s2v4/dev-smoke-v5.json"


def test_committed_round4_manifest_is_the_rendering():
    pool = json.loads(POOL.read_text())
    base = json.loads(V4.read_text())
    m = S.second_boots(base, S.impress_dev(pool), "s2v4-dev-smoke-v5")
    assert json.loads(V5.read_text()) == m
    assert len(S.impress_dev(pool)) == 7
    assert len(m["slots"]) == 310 and [s for s in m["slots"] if s in base["slots"]] == base["slots"]
    impress = {t[:8] for t in S.impress_dev(pool)}
    boots = [s for s in m["slots"] if s["task_id"][:8] in impress and s.get("kind") != "gold"]
    assert len(boots) == 140  # 70 in smoke 1240's shape, and a second boot of each
    by_cell: dict = {}
    for s in boots:
        by_cell.setdefault((s["task_id"], s["cell"]), []).append((s["rep"], s["block"]))
    for (_task, cell), reps in by_cell.items():
        assert sorted(r for r, _ in reps) == ([1, 2, 3, 4] if cell in ("E", "ER") else [1, 2])
    for i, s in enumerate(m["slots"]):  # each second boot right after its first, same block
        if s["task_id"][:8] in impress and s.get("kind") != "gold" and s["slot"] not in {
                x["slot"] for x in base["slots"]}:
            first = m["slots"][i - 1]
            assert (first["task_id"], first["cell"], first["block"]) == (
                s["task_id"], s["cell"], s["block"])
    assert L.check_slurm(m)["minutes"] == m["slurm"]["minutes"] == 98


def _png(path: Path, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8)).save(path)


def _run(tmp_path: Path, boots: dict) -> Path:
    """A lane run directory with one probed capture attempt per (task, cell, rep)."""
    run = tmp_path / "1500"
    run.mkdir()
    (run / "preflight.txt").write_text("job_id=1500\n")
    rows = []
    for (task, cell, rep), img in boots.items():
        slot = L.slot_id(task, cell, rep)
        rows.append({"slot": slot, "task_id": task, "cell": cell, "attempt": 1,
                     "status": "probed"})
        d = run / "slots" / f"{slot.replace(':', '_')}.a1" / "screens"
        _png(d / "post_setup-1.png", img)
        _png(d / "post_setup-2.png", img)
    (run / "probes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return run


@pytest.mark.parametrize("field_change, deviating", [(0, False), (8, False), (40, True)])
def test_read_flags_a_deviating_status_bar_field(tmp_path, field_change, deviating):
    imp, calc = "aaaaaaaa-0000", "bbbbbbbb-0000"
    pool = {"tasks": [{"task_id": imp, "split": "dev", "app": S.IMPRESS},
                      {"task_id": calc, "split": "dev", "app": "libreoffice_calc"}]}
    base = np.zeros((1080, 1920, 3))
    changed = base.copy()
    changed[1066:1066 + 4, 900:900 + field_change // 4] = 255  # in the pointer field's rows
    boots = {(t, c, r): base for t in (imp, calc) for c, r in
             (("E", 1), ("E", 2), ("S", 1), ("ER", 1), ("ER", 2), ("AD", 1), ("AR", 1))}
    boots[(imp, "A", 1)] = base
    boots[(imp, "A", 2)] = changed  # a second boot whose field reads another value
    out = S.read([_run(tmp_path, boots)], pool, tol6=50)
    assert out["registered_pairs_missing"] == [] and out["registered_pairs_over_tol6"] == []
    assert out["per_task"]["aaaaaaaa"]["pairs"]["A_vs_A2"]["status_bar_pixels"] == field_change
    assert bool(out["impress_status_bar_deviations"]) is deviating
    assert out["pass"] is not deviating
    assert out["impress_boots_read"] == 9


def test_read_needs_every_registered_pair_at_most_tol6(tmp_path):
    imp = "aaaaaaaa-0000"
    pool = {"tasks": [{"task_id": imp, "split": "dev", "app": S.IMPRESS}]}
    base = np.zeros((1080, 1920, 3))
    other = base.copy()
    other[500:510, 500:510] = 255  # 100 px in the document region
    boots = {(imp, c, r): base for c, r in (("E", 1), ("E", 2), ("S", 1), ("ER", 1), ("AD", 1),
                                           ("AR", 1))}
    boots[(imp, "S", 1)] = other
    out = S.read([_run(tmp_path, boots)], pool, tol6=50)
    assert out["registered_pairs_over_tol6"] == [["aaaaaaaa", "E_vs_S", 100]]
    assert out["registered_pairs_missing"] == [["aaaaaaaa", "ER_vs_ER2"]]
    assert out["pass"] is False
