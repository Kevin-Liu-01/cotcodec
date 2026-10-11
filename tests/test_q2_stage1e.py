"""Successor E (q2-stage1-successor-e-v1): plan, records, lane, episode entry point, analysis.

E adds data to S1a's design: all 113 eligible pool tasks, both sizes, four new sessions,
one episode per (size, task, harness, session). These tests check that E's code changes
nothing S1a fixed: the tasks are S1a's pool, the engine, prompt date and episode container
are S1a's, the records are S1a's schema (E's session labels aside), and the analysis is S1a's
estimators and rules; and that E's own rules (the job order, the session gaps, the caps from
arithmetic, the slots from the plan) hold.
"""

from __future__ import annotations

import collections
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from harness.q2_stage1 import analysis as A1
from harness.q2_stage1 import estimators as E
from harness.q2_stage1 import lane as L1
from harness.q2_stage1 import plan as P1
from harness.q2_stage1 import records as R1
from harness.q2_stage1e import analysis as AE
from harness.q2_stage1e import driver as DE
from harness.q2_stage1e import lane as LE
from harness.q2_stage1e import plan as PE
from harness.q2_stage1e import records as RE

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402
import render_q2e_manifest as builder  # noqa: E402

RUNS = "/home/kevin/cotcodec-runs/stage0/q2-stage1"
HOST = {
    "run_root": f"{RUNS}/runs",
    "vm": {**L1.VM_PINS, "guest_ip": "20.20.20.21",
           "qcow2": {"host_path": f"{RUNS}/../q2-action-path/vm/Ubuntu.qcow2",
                     "sha256": L1.QCOW2_SHA256, "size_bytes": L1.QCOW2_BYTES}},
    "osworld": {"host_dir": f"{RUNS}/inputs/OSWorld", "commit": L1.OSWORLD_COMMIT},
    "file_cache": {"host_dir": f"{RUNS}/inputs/files"},
    "engine": {"bridge_dir": f"{RUNS}/gpu/{{gpu_job_id}}/bridge",
               "gpu_job_id_file": f"{RUNS}/pairs/e/gpu_job_id"},
}  # fmt: skip


@pytest.fixture(scope="module")
def plan() -> dict[str, Any]:
    return PE.load_plan(ROOT / PE.PLAN_FILE)


# --------------------------------------------------------------------------- plan


def test_the_committed_plan_is_the_rendered_plan(plan):
    assert PE.render_plan(ROOT) == plan
    assert plan["plan_sha256"] == PE.digest({k: v for k, v in plan.items() if k != "plan_sha256"})


def test_tasks_are_s1a_pool_without_a_draw(plan):
    s1a = PE.load_s1a_plan(ROOT)
    pool = list(s1a["base"]) + [t for b in s1a["extension_blocks"].values() for t in b]
    assert plan["tasks"] == sorted(pool) and len(plan["tasks"]) == 113
    assert plan["s1a_base"] == s1a["base"] and len(plan["s1a_base"]) == 32
    assert not set(plan["tasks"]) & set(P1.OFFLINE_EXCLUDED)
    assert not {t[:8] for t in plan["tasks"]} & set(P1.K1_RAW_GOLD_FAILURES)
    assert plan["flagged_tasks"] == [t for t in P1.FLAGGED_TASKS if t in plan["tasks"]]


def test_engine_sampling_and_prompt_are_s1a(plan):
    for size in PE.SIZES:
        assert plan["engine_argv"][size] == s1a_argv(size)
    assert plan["sampling"] == {h: P1.sampling(h) for h in P1.HARNESSES}
    assert plan["prompt_date"] == P1.PROMPT_DATE == "2026-10-08"
    assert plan["size_order"] == P1.size_order() == ["9B", "4B"]
    assert plan["V"] == P1.a1_concurrency(plan["n_star"]) == 20


def s1a_argv(size: str) -> list[str]:
    return json.loads((ROOT / PE.S1A_PLAN).read_text())["engine_argv"][size]


def test_caps_come_from_arithmetic_on_s1a_realized_cost(plan):
    """ceil(3 + (L + (N x slot / V + drain) x 1.2 x 1.05) / 60), the design study's rule."""
    inputs = PE.cost_inputs(PE.load_cost_model(ROOT))
    for size, slot, drain, cap in (
        ("9B", 185.426773, 104.60958, 52),
        ("4B", 173.047879, 92.870499, 48),
    ):
        seconds = 113.18587 + (226 * slot / 20 + drain) * 1.2 * 1.05
        assert np.ceil(3 + seconds / 60) == cap == plan["caps_minutes"][f"E-{size}"]
        assert PE.job_cap_minutes(size, 226, inputs) == cap
    assert plan["total_cap_minutes"] == 4 * (52 + 48) + 6 == 406 <= PE.ALLOCATABLE_MINUTES
    assert round(406 / 60, 2) == 6.77
    with pytest.raises(PE.PlanError, match="above 478"):
        PE.total_cap_minutes({"9B": 70, "4B": 60})


def test_job_order_and_session_gaps(plan):
    assert plan["job_order"] == PE.job_order() == [
        "E-9B-E1", "E-4B-E1", "E-9B-E2", "E-4B-E2", "E-9B-E3", "E-4B-E3", "E-9B-E4", "E-4B-E4",
    ]  # fmt: skip
    assert PE.session_not_before("E-4B-E1", {}) is None
    ends = {"E-9B-E1": 1000.0, "E-4B-E1": 5000.0}
    assert PE.session_not_before("E-9B-E2", ends) == 5000.0 + 12 * 3600
    with pytest.raises(PE.PlanError, match="needs the end"):
        PE.session_not_before("E-9B-E3", ends)
    jobs = {j["job"]: j for j in plan["jobs"]}
    assert jobs["E-9B-E2"]["not_before"] == {"after_the_later_end_of": ["E-9B-E1", "E-4B-E1"],
                                             "hours": 12}  # fmt: skip
    assert jobs["E-4B-E3"]["vm_cpus"] == 90 and jobs["E-4B-E3"]["co_running_cpus"] == 122
    assert jobs["E-4B-E3"]["vm_minutes"] == 58 and jobs["E-9B-E3"]["vm_minutes"] == 62


def test_every_job_runs_every_cell_once_in_a_seeded_order(plan):
    seen_orders = set()
    for job in plan["job_order"]:
        size, session = PE.parse_job(job)
        slots = PE.slots(plan, size, session)
        cells = collections.Counter((s["task_id"], s["harness"]) for s in slots)
        assert len(slots) == 226 and set(cells.values()) == {1} and len(cells) == 226
        assert {(s["job"], s["size"], s["session"], s["rerun"], s["block"]) for s in slots} == {
            (job, size, session, 1, "e1")
        }
        assert [s["slot"] for s in slots] == [f"{job}:e1:{i:03d}" for i in range(226)]
        seen_orders.add(tuple((s["task_id"], s["harness"]) for s in slots))
        assert slots == P1.block_slots(job, size, session, "e1", 1,
                                       PE.block_order(plan["tasks"], session, size))  # fmt: skip
    assert len(seen_orders) == 8  # each job its own order
    bad = copy.deepcopy(plan)
    bad["episode_orders"]["E1:9B"].reverse()
    with pytest.raises(PE.PlanError, match="digest"):
        PE.slots(bad, "9B", "E1")


# --------------------------------------------------------------------------- records


def record(
    job: str = "E-9B-E2",
    task: str = "t1",
    harness: str = "H-GA",
    status: str = "scored",
    score: float | None = 1.0,
    attempt: int = 1,
    **extra: Any,
) -> dict[str, Any]:
    size, session = PE.parse_job(job)
    rec = {"schema": R1.SCHEMA, "job": job, "size": size, "session": session, "task_id": task,
           "harness": harness, "rerun": 1, "extension_block": None, "attempt": attempt,
           "status": status, "score": score if status == "scored" else None,
           "infrastructure_type": "vm_boot" if status == "infrastructure" else None,
           "slot": f"{job}:e1:{task}:{harness}", "block": "e1"}  # fmt: skip
    rec.update(extra)
    return rec


def test_records_are_s1a_schema_with_e_labels():
    rec = record()
    assert RE.validate(rec) == rec
    with pytest.raises(R1.RecordError, match="session"):
        R1.validate(rec)  # S1a's tools cannot read E's records
    for change, message in (
        ({"session": "S1"}, "session"),
        ({"session": "E5"}, "session"),
        ({"rerun": 2}, "rerun"),
        ({"rerun": True}, "rerun"),
        ({"extension_block": 1}, "extension"),
        ({"score": 1.5}, "score in"),  # S1a's own checks still apply
        ({"status": "lost"}, "status"),
        ({"schema": "other"}, "schema"),
    ):
        with pytest.raises(R1.RecordError, match=message):
            RE.validate({**rec, **change})


def test_outcome_array_has_four_sessions_one_rerun():
    recs = [
        record(f"E-9B-{s}", "t1", "H-GA", score=float(i % 2)) for i, s in enumerate(PE.SESSIONS)
    ]
    recs.append(record("E-4B-E3", "t2", "H-OSW-fixed", score=0.5))
    recs.append(record("E-4B-E4", "t2", "H-OSW-fixed", status="infrastructure", attempt=1))
    finals = RE.final_records(recs)
    y = RE.outcome_array(finals, ["t1", "t2"])
    assert y.shape == (2, 2, 2, 4, 1)
    assert list(y[1, 0, 1, :, 0]) == [0.0, 1.0, 0.0, 1.0]
    assert y[0, 1, 0, 2, 0] == 0.0 and np.isnan(y[0, 1, 0, 3, 0])
    assert RE.outcome_array(finals, ["t2"], value="score")[0, 0, 0, 2, 0] == 0.5


def test_job_dr0_reads_losses_and_completion_only():
    tasks = [f"t{i}" for i in range(20)]
    full = [record("E-9B-E1", t, h) for t in tasks for h in P1.HARNESSES]
    assert not RE.job_dr0(full, job="E-9B-E1", size="9B", session="E1", tasks=tasks)["fires"]
    # two first-attempt losses of 20 in a cell (10%), each re-queued and scored: fires
    lost = full + [record("E-9B-E1", t, "H-GA", status="infrastructure", attempt=1)
                   for t in tasks[:2]]  # fmt: skip
    lost = [r for r in lost if not (r["task_id"] in tasks[:2] and r["harness"] == "H-GA"
                                    and r["status"] == "scored")] + [
        record("E-9B-E1", t, "H-GA", attempt=2) for t in tasks[:2]]  # fmt: skip
    out = RE.job_dr0(lost, job="E-9B-E1", size="9B", session="E1", tasks=tasks)
    assert out["fires"] and "cell loss above 5%" in out["reasons"][0]
    short = [r for r in full if r["task_id"] != "t0"]
    out = RE.job_dr0(short, job="E-9B-E1", size="9B", session="E1", tasks=tasks)
    assert out["fires"] and out["reasons"] == ["base incomplete"]
    out = RE.job_dr0(full, job="E-9B-E1", size="9B", session="E1", tasks=tasks,
                     receipt={"error": "engine argv"})  # fmt: skip
    assert out["fires"] and out["reasons"][-1].startswith("lane: engine argv")


def test_glmm_rows_nest_e_sessions_in_size():
    from harness.q2_stage1 import glmm as G

    finals = RE.final_records([record("E-4B-E3", "t9", "H-GA", score=0.0)])
    rows = RE.glmm_rows(finals, ["t9"])
    assert rows == [{"y": 0, "size": "4B", "harness": "H-GA", "task": "t9",
                     "session": "4B:E3", "rerun": 1}]  # fmt: skip
    assert set(rows[0]) == set(G.COLUMNS)


# --------------------------------------------------------------------------- episode entry point


def test_the_entry_point_is_s1a_driver_with_e_labels(monkeypatch, tmp_path):
    """S1a's driver refuses E's record at its final check (its sessions are S1 and S2), which
    would make every E episode a runner crash; E's entry point swaps that one check."""
    from harness.q2_stage1 import driver as D1

    monkeypatch.setattr(D1, "validate", D1.validate)  # restore after the test
    runner = D1.Runner.__new__(D1.Runner)
    runner.cfg = D1.EpisodeConfig(
        job="E-9B-E2", size="9B", session="E2", task_id="t1", harness="H-GA", rerun=1,
        attempt=1, extension_block=None, block="e1", slot="E-9B-E2:e1:000",
        out_dir=str(tmp_path), mode="episode")  # fmt: skip
    runner.out = tmp_path
    runner.clock = lambda: 1.0
    runner.timings = {}
    runner.agent_observations = {"calls": 0, "retried": 0, "slow": 0, "undelivered": 0,
                                 "max_s": None}  # fmt: skip
    runner.session = None
    runner.record = record("E-9B-E2", "t1")
    with pytest.raises(R1.RecordError, match="unknown session"):
        runner.finish(0.0)
    assert not (tmp_path / "episode.json").exists()
    DE.use_e_labels()
    assert D1.validate is RE.validate
    out = runner.finish(0.0)
    assert out["session"] == "E2" and (tmp_path / "episode.json").exists()


def test_the_lane_runs_e_entry_point_and_otherwise_s1a_argv(tmp_path):
    m = builder.development_manifest(host=HOST, source_dir=ROOT, tasks=dev()[:1],
                                     script={"replies": ["x"]}, name="e-dev")  # fmt: skip
    cfg = L1.LaneConfig(m, "999", tmp_path, ROOT)
    args = (cfg, "ep", "vm", tmp_path / "out", None, None)
    s1a, e = L1.episode_argv(*args), LE.episode_argv(*args)
    i = s1a.index("harness.q2_stage1.driver")
    assert e[:i] + e[i + 1 :] == s1a[:i] + s1a[i + 1 :] and e[i] == "harness.q2_stage1e.driver"


# --------------------------------------------------------------------------- lane


def dev() -> list[str]:
    return sorted(json.loads((ROOT / LE.SPLITS).read_text())["dev"])


@pytest.fixture(scope="module")
def draft(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("draft")
    (root / LE.SPLITS).parent.mkdir(parents=True)
    shutil.copy(ROOT / LE.SPLITS, root / LE.SPLITS)
    assert not LE.frozen(root)
    return root


@pytest.fixture(scope="module")
def frozen_tree(tmp_path_factory, plan) -> Path:
    """A tree as E's freeze leaves it: the splits, the plan file, and a registration naming
    the plan, frozen into a fresh ledger."""
    root = tmp_path_factory.mktemp("frozen")
    for rel in (LE.SPLITS, PE.PLAN_FILE):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, root / rel)
    freeze(root, LE.PLAN_LINE.format(sha=plan["plan_sha256"]) + ".\n")
    return root


def freeze(root: Path, text: str) -> None:
    path = root / LE.REGISTRATION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    ledger = root / LE.LEDGER
    ledger.unlink(missing_ok=True)
    preregister.freeze(path, LE.EXPERIMENT_ID, ledger=ledger, root=root)


def e_manifest(tree: Path, size: str = "9B", session: str = "E1", prior=()) -> dict[str, Any]:
    return builder.vm_manifest(host=HOST, source_dir=tree, plan_path=PE.PLAN_FILE, size=size,
                               session=session, prior_run_dirs=prior)  # fmt: skip


def test_an_e1_manifest_is_the_plans_and_the_lane_accepts_it(frozen_tree, plan):
    m = e_manifest(frozen_tree)
    assert LE.validate_manifest(m, frozen_tree)["slots"] == PE.slots(plan, "9B", "E1")
    assert m["vm"]["concurrency"] == 20 and m["slurm"]["cpus"] == 90
    assert m["engine"]["gpu_cap_min"] == 52 and m["slurm"]["minutes"] == 62
    assert m["date"] == P1.PROMPT_DATE and m["episode_image_id"] == L1.EPISODE_IMAGE_ID
    assert L1.check_slurm(m)["cpus"] == 90  # S1a's CPU and limit rule, unchanged
    with pytest.raises(ValueError, match="needs the run directories"):
        e_manifest(frozen_tree, "4B", "E1", prior=())
    m4 = copy.deepcopy(m)  # 4B-E1 without 9B-E1's records: the lane refuses it too
    m4["e"]["size"], m4["engine"]["gpu_cap_min"] = "4B", 48
    m4["slots"] = PE.slots(plan, "4B", "E1")
    with pytest.raises(LE.LaneError, match=r"must be \['E-9B-E1'\]"):
        LE.validate_manifest(m4, frozen_tree)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        (lambda m: m["slots"].reverse(), "slots differ from plan.slots"),
        (lambda m: m["slots"].pop(), "slots differ"),
        (lambda m: m["slots"][0].update(session="S1"), "E's labels"),
        (lambda m: m["engine"].update(gpu_cap_min=60), "GPU cap is 52"),
        (lambda m: m["vm"].update(concurrency=32), "V = 20"),
        (lambda m: m.update(date="2026-10-12"), "pinned prompt date"),
        (lambda m: m.update(episode_image_id="sha256:" + "2" * 64), "registered metric image"),
        (lambda m: m.update(requeue=False), "requeue is fixed"),
        (lambda m: m.update(episode_timeout_s=60), "episode_timeout_s is fixed"),
        (lambda m: m.update(fill={"blocks": []}), "no fill rule"),
        (lambda m: m["plan"].update(sha256="0" * 64), "plan"),
        (lambda m: m.update(experiment_id=L1.EXPERIMENT_ID), "experiment_id"),
        (lambda m: m["e"].update(session="E9"), "unknown E job"),
        (lambda m: m["engine"].update(bridge_dir=f"{RUNS}/gpu/1/bridge"), "gpu_job_id"),
    ],
)
def test_an_e_manifest_that_differs_from_the_plan_is_refused(tamper, message, frozen_tree):
    m = e_manifest(frozen_tree)
    tamper(m)
    with pytest.raises(LE.LaneError, match=message):
        LE.validate_manifest(m, frozen_tree)


def test_freeze_state_gates_the_purposes(frozen_tree, draft, tmp_path):
    m = e_manifest(frozen_tree)
    with pytest.raises(LE.LaneError, match="runs only after the freeze"):
        LE.validate_manifest(m, draft)
    d = builder.development_manifest(host=HOST, source_dir=ROOT, tasks=dev()[:2],
                                     script={"replies": ["x"]}, name="e-dev")  # fmt: skip
    assert len(LE.validate_manifest(d, draft)["slots"]) == 4
    with pytest.raises(LE.LaneError, match="pre-freeze purpose"):
        LE.validate_manifest(d, frozen_tree)
    confirm = copy.deepcopy(d)
    confirm["slots"][0]["task_id"] = PE.load_plan(ROOT / PE.PLAN_FILE)["tasks"][0]
    with pytest.raises(LE.LaneError, match="not a dev-split task"):
        LE.validate_manifest(confirm, draft)
    # A registration edited after the freeze refuses every E job.
    edited = tmp_path / "edited"
    shutil.copytree(frozen_tree, edited)
    with (edited / LE.REGISTRATION).open("a") as handle:
        handle.write("edited\n")
    with pytest.raises(LE.LaneError, match="changed after the freeze"):
        LE.validate_manifest(m, edited)
    # S1a's lane refuses E's manifests and E's lane refuses S1a's.
    with pytest.raises(L1.LaneError, match="schema"):
        L1.validate_manifest(m, frozen_tree)


def run_dir(
    tmp: Path,
    job: str,
    plan: dict[str, Any],
    *,
    t_end: float = 1.0e9,
    gpu_end: float | None = None,
    drop: int = 0,
    error: str | None = None,
) -> Path:
    """A finished E job's lane run directory: manifest, records and receipt."""
    size, session = PE.parse_job(job)
    out = tmp / job
    out.mkdir(parents=True)
    slots = PE.slots(plan, size, session)[drop:]
    rows = [record(job, s["task_id"], s["harness"], slot=s["slot"]) for s in slots]
    (out / "manifest.json").write_text(
        json.dumps({"purpose": "e", "e": {"size": size, "session": session}})
    )
    (out / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    receipt: dict[str, Any] = {"t_end": t_end}
    if gpu_end is not None:
        receipt["gpu_job_end"] = {"end_epoch": gpu_end, "state": "COMPLETED"}
    if error:
        receipt["error"] = error
    (out / "lane-receipt.json").write_text(json.dumps(receipt))
    return out


def test_job_order_dr0_and_session_gap_are_enforced(frozen_tree, plan, tmp_path, monkeypatch):
    monkeypatch.setattr(L1, "RUN_ROOT", "/")  # the run directories live in tmp_path here
    e1 = [run_dir(tmp_path, "E-9B-E1", plan, t_end=1000.0),
          run_dir(tmp_path, "E-4B-E1", plan, t_end=5000.0, gpu_end=5100.0)]  # fmt: skip
    m = e_manifest(frozen_tree, "9B", "E2", prior=e1)
    assert LE.validate_manifest(m, frozen_tree)
    assert LE.earliest_start(m) == 5100.0 + 12 * 3600  # the later end, GPU EndTime included
    with pytest.raises(ValueError, match="needs the run directories"):
        e_manifest(frozen_tree, "9B", "E2", prior=e1[:1])
    # A changed record file is refused by digest.
    with (e1[0] / "episodes.jsonl").open("a") as handle:
        handle.write(json.dumps(record("E-9B-E1", plan["tasks"][0], "H-GA", attempt=2)) + "\n")
    with pytest.raises(LE.LaneError, match="does not match its digest"):
        LE.validate_manifest(m, frozen_tree)
    # A prior job that fired DR0 (an incomplete job) stops every later job.
    cut = tmp_path / "cut"
    prior = [run_dir(cut, "E-9B-E1", plan, drop=3), run_dir(cut, "E-4B-E1", plan)]
    with pytest.raises(LE.LaneError, match="DR0 fired for E-9B-E1"):
        LE.validate_manifest(e_manifest(frozen_tree, "9B", "E2", prior=prior), frozen_tree)
    refused = tmp_path / "refused"
    prior = [run_dir(refused, "E-9B-E1", plan), run_dir(refused, "E-4B-E1", plan,
                                                         error="engine argv")]  # fmt: skip
    with pytest.raises(LE.LaneError, match="DR0 fired for E-4B-E1"):
        LE.validate_manifest(e_manifest(frozen_tree, "9B", "E2", prior=prior), frozen_tree)


def e_lane(tmp_path: Path, m: dict[str, Any], *, argv_size: str, limit: int, clock: float,
           start: float = 5000.0) -> tuple[LE.Lane, Any]:  # fmt: skip
    """An E lane whose GPU job's bridge is up (ready.json with ``argv_size``'s engine argv;
    scontrol reports ``limit`` minutes)."""
    import test_q2_stage1_lane as S1L

    bridge = tmp_path / "gpu" / "77" / "bridge"
    bridge.mkdir(parents=True)
    argv = P1.engine_argv(P1.MODEL_DIRS[argv_size], P1.SERVED_NAME)
    (bridge / "ready.json").write_text(json.dumps({"engine_argv": argv, "t_start": start + 40,
                                                   "t_ready": start + 200}))  # fmt: skip
    (tmp_path / "gpu_job_id").write_text("77\n")
    m = copy.deepcopy(m)
    m["slots"] = m["slots"][:2]
    m["engine"] = {**m["engine"], "bridge_dir": str(tmp_path / "gpu" / "{gpu_job_id}" / "bridge"),
                   "gpu_job_id_file": str(tmp_path / "gpu_job_id")}  # fmt: skip
    cfg = L1.LaneConfig(m, "999", tmp_path / "run", ROOT)
    cfg.run_dir.mkdir()

    def slurm(job_id: str) -> dict[str, Any]:
        done = (bridge / "vm.done").exists()
        return {"state": "COMPLETED" if done else "RUNNING", "time_limit_min": limit,
                "start_epoch": start, **({"end_epoch": start + 900} if done else {})}  # fmt: skip

    docker = S1L.FakeDocker({})
    return LE.Lane(cfg, docker=docker, certified=["Return"], slurm_job=slurm,
                   clock=lambda: clock), docker  # fmt: skip


def test_the_lane_checks_the_engine_and_the_gap_before_dispatching(
    frozen_tree, plan, tmp_path, monkeypatch
):
    monkeypatch.setattr(L1, "RUN_ROOT", "/")
    e1 = [run_dir(tmp_path / "prior", "E-9B-E1", plan, t_end=1000.0),
          run_dir(tmp_path / "prior", "E-4B-E1", plan, t_end=5000.0)]  # fmt: skip
    m = e_manifest(frozen_tree, "9B", "E2", prior=e1)
    gap = 5000.0 + 12 * 3600
    ok, docker = e_lane(tmp_path / "ok", m, argv_size="9B", limit=52, clock=gap + 1)
    receipt = ok.run()
    assert "error" not in receipt and len(docker.episodes) == 2
    assert all("harness.q2_stage1e.driver" in argv for argv in docker.episodes)
    assert receipt["usr1_epoch"] == 5000.0 + 52 * 60 - 180
    early, docker = e_lane(tmp_path / "early", m, argv_size="9B", limit=52, clock=gap - 1)
    receipt = early.run()
    assert "starts at least 12 h" in receipt["error"] and not docker.episodes
    wrong, docker = e_lane(tmp_path / "4b", m, argv_size="4B", limit=52, clock=gap + 1)
    assert "not the registered 9B argv" in wrong.run()["error"] and not docker.episodes
    cap, docker = e_lane(tmp_path / "cap", m, argv_size="9B", limit=60, clock=gap + 1)
    receipt = cap.run()
    assert "time limit is 60 minutes, not its cap of 52" in receipt["error"]
    assert not docker.episodes and receipt["statuses"] == {"cap_truncated": 2}


def test_gpu_half_uses_s1a_template_for_the_jobs_size_and_cap(frozen_tree):
    import yaml

    m = LE.validate_manifest(e_manifest(frozen_tree), frozen_tree)
    values = {"FILL_JOB": "e-9b-e1", "FILL_OVERLAY_IMAGE_ID": "sha256:" + "1" * 64,
              "FILL_GIT_SHA": "a" * 40, "FILL_SOURCE_SHA256": "b" * 64,
              "FILL_RECEIPT_SHA256": "c" * 64, "FILL_ARTIFACT_ROOT_SHA256": "d" * 64}  # fmt: skip
    template = (ROOT / builder.GPU_TEMPLATE).read_text()
    text = builder.gpu_for_vm_manifest(template, m, vm_job_id="123", values=values)
    data = yaml.safe_load(text)
    assert data["resources"]["minutes"] == 52 and "9B" in data["command"]
    assert data["model"]["revision"] == "c202236235762e1c871ad0ccb60c8ee5ba337b9a"
    assert data["start_after_job_id"] == 123


def test_batch_script_is_s1a_with_e_lane_module():
    s1a = (ROOT / L1.BATCH).read_text().splitlines()
    e = (ROOT / LE.BATCH).read_text().splitlines()
    changed = [(a, b) for a, b in zip(s1a, e, strict=False) if a != b]
    assert "#SBATCH --job-name=cotcodec-q2e-vm" in e
    assert not [line for line in e if line.startswith("#SBATCH") and "gres" in line]
    assert "python3 -E -s -m harness.q2_stage1e.lane run \\" in e
    assert sum(1 for line in e if "harness.q2_stage1.lane" in line) == 0
    body = [x for x in e if not x.startswith("#")]
    body_s1a = [x for x in s1a if not x.startswith("#")]
    assert [b.replace("q2_stage1e", "q2_stage1") for b in body] == body_s1a
    assert changed  # the header and comment lines differ


# --------------------------------------------------------------------------- analysis


def simulated(seed: int = 3, k: int = 40, sessions: int = 4, reruns: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eta = rng.normal(-0.8, 2.0, size=(1, k, 1, 1, 1)) + rng.normal(0, 0.9, size=(2, k, 2, 1, 1))
    return (rng.random((2, k, 2, sessions, reruns)) < 1 / (1 + np.exp(-eta))).astype(float)


def test_on_s1a_shaped_data_e_analysis_is_s1a_analysis():
    y = simulated(sessions=2, reruns=2)
    a = A1.analyse_array(y, n_boot=300, n_rand=300)
    b = AE.analyse_array(y, n_boot=300, n_rand=300)
    shared = [k for k in b["estimates"] if k in a["estimates"]]
    assert len(shared) >= 18 and all(a["estimates"][k] == b["estimates"][k] for k in shared)
    for key in ("delta_paired_t", "delta_paired_t_by_size", "x_signflip_p",
                "x_label_permutation_p_sensitivity"):  # fmt: skip
        assert a["tests"][key] == b["tests"][key]
    assert a["tests"]["session_signflip_p"] == b["tests"]["session_signflip_p_by_pair"]["E1-E2"]
    assert a["delta_session_heterogeneity"] == b["delta_session_heterogeneity_by_pair"]["E1-E2"]
    assert (a["DR1_drop_4B"], a["DR2"], a["DR5"]) == (b["DR1_drop_4B"], b["DR2"], b["DR5"])


def test_on_e_data_it_is_the_design_studys_analysis():
    """The design study's operating characteristics for E come from
    ``harness.q2_design.analyse.analyse``; the registered analysis gives the same readings."""
    from harness.q2_design import analyse as DA

    y = simulated(seed=11, k=60)
    b = AE.analyse_array(y, n_boot=400, n_rand=400)
    d = DA.analyse(y[None], ("4B", "9B"), n_boot=400, n_flip=400, rng=np.random.default_rng(42))
    assert b["tests"]["x_signflip_p"] == d["p_x"][0]
    assert b["estimates"]["pi_small"]["one_sided_95"] == [d["pi_small_lb"][0], d["pi_small_ub"][0]]
    assert b["DR2"]["class"] == d["dr2"][0] and b["DR5"]["outcome"] == d["dr5"][0]
    assert b["tests"]["delta_paired_t"]["estimate"] == round(float(d["delta"][0]), 6)


def test_frozen_estimators_take_four_sessions():
    """X is the mean over ordered session pairs (the U-statistic), D_b every cross pair."""
    y = simulated(seed=5, k=30)
    d = E.harness_diff(y)  # (Z, K, S)
    pairs = [(a, b) for a in range(4) for b in range(4) if a != b]
    manual = np.mean([d[..., a] * d[..., b] for a, b in pairs], axis=0).mean(axis=-1)
    assert np.allclose(E.x_by_size(y), manual)
    disc = np.mean([(y[..., a, 0] != y[..., b, 0]) for a in range(4) for b in range(a + 1, 4)],
                   axis=0).reshape(2, -1).mean(axis=-1)  # fmt: skip
    assert np.allclose(E.d_between(y), disc)
    assert np.all(np.isnan(E.d_within(y)))
    with pytest.raises(ValueError, match="exactly two sessions"):
        E.session_shift(y)


def test_r1_quantities_are_not_estimable_and_p1_is_not_read():
    y = simulated(seed=8)
    out = AE.analyse_array(y, n_boot=200, n_rand=200)
    assert set(out["not_estimable_at_R1"]) == {"D_w_4B", "D_w_9B", "D_w", "excess_4B",
                                               "excess_9B", "excess", "D_b_cross_block",
                                               "session_common_share"}  # fmt: skip
    assert set(out["tests"]["session_signflip_p_by_pair"]) == {
        "E1-E2",
        "E1-E3",
        "E1-E4",
        "E2-E3",
        "E2-E4",
        "E3-E4",
    }
    assert out["tests"]["session_signflip_holm_by_size"]["9B"]["tests"] == 6
    preds = AE.predictions(out, dr4_exceeds=False)
    assert "not_estimable" in preds["P1"] and preds["P1"]["read"].startswith("one-sided")
    assert preds["P3"]["falsified"] == (out["DR2"]["class"] == "Present")
    assert "not_estimable" in AE.predictions(out, dr4_exceeds=None)["P5"]


def test_incomplete_data_follow_d59_d61_d62():
    y = simulated(seed=9)
    one = y.copy()
    one[0, :, :, 1:, :] = np.nan  # 4B holds one session
    out = AE.analyse_array(one, n_boot=200, n_rand=200)
    assert out["pi_undefined_sizes"] == ["4B"]
    assert out["DR5"]["outcome"] == AE.DR5_NOT_EVALUABLE
    assert "description_only" in out["DR5"] and "incomplete_note" in out["DR2"]
    assert all("not_estimable" in out["tests"]["session_signflip_p_by_pair"][p][0]
               for p in ("E1-E2", "E2-E3"))  # fmt: skip
    # D62: a size with sessions but no task holding both harness cells in two sessions.
    d62 = y.copy()
    d62[0, :, 1, 1:, :] = np.nan
    d62[0, :, 0, 0, :] = np.nan
    out = AE.analyse_array(d62, n_boot=200, n_rand=200)
    assert "4B" in out["pi_undefined_sizes"] and out["DR5"]["outcome"] == AE.DR5_NOT_EVALUABLE
    none = np.full_like(y, np.nan)
    none[..., 0, :] = y[..., 0, :]  # one session for both sizes
    out = AE.analyse_array(none, n_boot=100, n_rand=100)
    assert "not_estimable" in out["tests"]["x_signflip_p"] and "not_estimable" in out["DR2"]
    assert out["DR5"]["outcome"] == AE.DR5_NOT_EVALUABLE


def synthetic_records(plan: dict[str, Any], seed: int = 1, tasks: int | None = None) -> list:
    rng = np.random.default_rng(seed)
    p = {t: rng.uniform(0, 0.6) for t in plan["tasks"]}
    rows = []
    for job in plan["job_order"]:
        size, session = PE.parse_job(job)
        for s in PE.slots(plan, size, session)[: tasks or None]:
            rows.append(
                record(
                    job,
                    s["task_id"],
                    s["harness"],
                    score=float(rng.random() < p[s["task_id"]]),
                    slot=s["slot"],
                    steps=5,
                    host={"slot_occupancy_s": 180.0},
                )
            )
    return rows


def test_report_end_to_end_and_fractional_scores(plan):
    rows = synthetic_records(plan)
    rows[0]["score"] = 0.4  # a fractional checker score (three pool tasks use continuous metrics)
    out = AE.report(rows, plan, n_boot=100, n_rand=100,
                    costs={"E-9B-E1": {"gpu_h_per_episode": 0.0027, "V": 20, "size": "9B",
                                       "episodes": 226, "gpu_h": 0.61, "vm_h_per_episode": 0.05,
                                       "job": "E-9B-E1"}})  # fmt: skip
    assert out["primary"]["tasks"] == 113 and out["secondary_s1a_base"]["tasks"] == 32
    assert out["labels"] == {"incomplete": None, "incomplete_reasons": [],
                             "external_anchor": "not externally anchored"}  # fmt: skip
    assert out["predictions"]["P5"]["falsified"] is False and not out["DR4"]["exceeds_high"]
    assert out["fractional_score"] is not None and E._check is not None
    assert set(out["cells_by_size_session"]) == {f"{z}/{s}" for z in PE.SIZES for s in PE.SESSIONS}
    with pytest.raises(ValueError, match="0, 1 or NaN"):  # the widening was restored
        E.delta(RE.outcome_array(RE.final_records(rows), plan["tasks"], value="score"))


def test_report_labels_incomplete_data(plan):
    rows = [r for r in synthetic_records(plan) if r["job"] not in ("E-9B-E4", "E-4B-E4")]
    out = AE.report(rows, plan, n_boot=50, n_rand=50)
    assert out["labels"]["incomplete"] == "incomplete"
    assert "no records from E-9B-E4, E-4B-E4" in out["labels"]["incomplete_reasons"]
    assert out["primary"]["sessions"] == 4 and out["primary"]["DR5"]["outcome"] in (
        "GO",
        "NO-GO",
        "INCONCLUSIVE",
    )  # three sessions per size still define X and pi


def test_joint_reading_is_descriptive_and_resamples_tasks_jointly(plan):
    rows = synthetic_records(plan, seed=2)
    s1a = R1.read_jsonl(ROOT / "program/evidence/2026-10-10/q2-stage1-analysis/a1.jsonl")
    out = AE.joint_reading(rows, s1a, plan["tasks"], n_boot=100)
    assert out["label"] == AE.JOINT_LABEL and out["tasks"] == 113
    s1a_y = R1.outcome_array(R1.final_records(s1a), plan["tasks"])
    assert out["s1a"]["delta"]["estimate"] == A1._f(E.delta(s1a_y))
    e_delta = out["e"]["delta"]["estimate"]
    assert out["e_minus_s1a"]["delta"]["estimate"] == pytest.approx(
        e_delta - out["s1a"]["delta"]["estimate"], abs=2e-6
    )
    assert set(out) >= {"s1a", "e", "e_minus_s1a", "six_sessions", "designs"}


def test_section15_items_and_first_divergence(plan, tmp_path):
    from harness.q2_stage1e import section15 as S15

    rows = synthetic_records(plan, seed=4)
    for r in rows:
        r.update(
            ended="terminate_success" if r["score"] == 1.0 else "step_cap",
            tokens={"completion": 900, "prompt": 20000},
            guest_server_restarts=0,
        )
    rows.append(record("E-4B-E2", plan["tasks"][0], "H-GA", status="infrastructure",
                       attempt=1, slot=PE.slots(plan, "4B", "E2")[0]["slot"]))  # fmt: skip
    runs = {}
    for job in ("E-9B-E1", "E-9B-E2"):
        size, session = PE.parse_job(job)
        run = tmp_path / job
        (run / "episodes").mkdir(parents=True)
        (run / "manifest.json").write_text(
            json.dumps({"purpose": "e", "e": {"size": size, "session": session}})
        )
        (run / "lane-receipt.json").write_text(
            json.dumps(
                {
                    "job_id": "1",
                    "snapshots": [
                        {
                            "block": "start",
                            "t": 1.0,
                            "squeue_foreign": [["9", "u", "RUNNING", "8", ""]],
                        }
                    ],
                }
            )
        )
        cells = [(s["task_id"], s["harness"]) for s in PE.slots(plan, "9B", "E1")[:3]]
        chosen = [s for s in PE.slots(plan, size, session) if (s["task_id"], s["harness"]) in cells]
        for i, s in enumerate(chosen):
            d = run / "episodes" / f"{s['slot'].replace(':', '_')}.a1"
            d.mkdir()
            step = {"processed_sha256": f"{job}{i}", "messages_sha256": "m", "ir_sha256": "i"}
            (d / "steps.jsonl").write_text(json.dumps(step) + "\n")
        runs[job] = run
    assert S15.run_dirs_by_job(runs.values()) == runs
    out = S15.assemble(rows, plan, labels={"incomplete": None}, runs=runs,
                       costs={"E-9B-E1": {"gpu_h_per_episode": 0.0027, "V": 20, "size": "9B",
                                          "episodes": 226, "gpu_h": 0.61,
                                          "vm_h_per_episode": 0.05, "job": "E-9B-E1"}})  # fmt: skip
    cell = out["steps"]["9B/H-GA"]
    assert cell["episodes"] == 4 * 113 and set(cell["step_of_termination"]) <= {
        "05",
        "censored_at_15",
    }
    assert out["output_tokens"]["9B/H-GA"]["completion_per_step"] == 180.0
    assert out["losses_by_task"][plan["tasks"][0]]["attempts_lost"] == 1
    assert out["cost_card_prices"]["jobs"]["E-9B-E1"]["ratio_to_high"] == round(
        0.0027 / 0.011274, 4
    )
    assert out["host_snapshots"]["E-9B-E1"]["snapshots_with_foreign_running_job"] == 1
    fd = out["first_divergence"]
    assert fd["step_logs_read"] == 6 and set(fd["first_divergence"]) == {"within", "between"}
    assert (
        sum(fd["first_divergence"]["between"].values()) >= 1
        and not fd["first_divergence"]["within"]
    )


def test_cost_and_dr0_command_lines_read_e_run_dirs(plan, tmp_path):
    run = run_dir(tmp_path, "E-4B-E3", plan)
    receipt = json.loads((run / "lane-receipt.json").read_text())
    receipt.update(
        gpu_job={"job_id": "77", "start_epoch": 1000.0},
        gpu_job_end={"state": "COMPLETED", "end_epoch": 1000.0 + 2160.0},
    )
    (run / "lane-receipt.json").write_text(json.dumps(receipt))
    manifest = json.loads((run / "manifest.json").read_text())
    manifest["vm"] = {"concurrency": 20}
    (run / "manifest.json").write_text(json.dumps(manifest))
    out = AE.run_dir_dr0(run, plan)
    assert (
        out["job"] == "E-4B-E3"
        and not out["fires"]
        and set(out["files"]) == {"manifest.json", "episodes.jsonl", "lane-receipt.json"}
    )
    costs = tmp_path / "costs.json"
    assert AE.main(["costs", "--run-dir", str(run), "--out", str(costs)]) == 0
    card = json.loads(costs.read_text())["E-4B-E3"]
    assert card["episodes"] == 226 and card["gpu_h"] == round(2160 / 3600, 6)
    assert card["gpu_h_per_episode"] == round(0.6 / 226, 6)


def test_glmm_synthetic_rows_have_e_shape(tmp_path):
    rows = RE.glmm_synthetic(k=10, seed=42)
    assert len(rows) == 2 * 10 * 2 * 4
    assert {r["session"] for r in rows} == {f"{z}:{s}" for z in PE.SIZES for s in PE.SESSIONS}
    assert {r["rerun"] for r in rows} == {1} and RE.glmm_synthetic(k=10, seed=42) == rows
    out = tmp_path / "syn.csv"
    assert AE.main(["glmm-synthetic", "--out", str(out), "--k", "10"]) == 0
    assert out.read_text().splitlines()[0] == "y,size,harness,task,session,rerun"


def test_committed_development_smoke_is_valid_before_the_freeze_only(draft, frozen_tree):
    m = json.loads((ROOT / "experiments/manifests/q2-stage1e/dev-smoke-v1.json").read_text())
    s1a = json.loads((ROOT / "experiments/manifests/q2-stage1/dev-smoke-v1.json").read_text())
    assert LE.validate_manifest(m, draft)["purpose"] == "development"
    assert L1.check_slurm(m)["cpus"] == 8
    assert m["engine"] == s1a["engine"] and m["vm"] == s1a["vm"]
    assert {s["task_id"] for s in m["slots"]} == {s["task_id"] for s in s1a["slots"]}
    assert len(m["slots"]) == 4  # both dev tasks under both harnesses
    assert {(s["session"], s["rerun"]) for s in m["slots"]} == {("E1", 1)}
    with pytest.raises(LE.LaneError, match="pre-freeze purpose"):
        LE.validate_manifest(m, frozen_tree)
