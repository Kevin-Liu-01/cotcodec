"""Registered S1a VM jobs run the plan's slots: A0a, A1 session 1 (fill) and session 2.

``scripts/render_q2_stage1_manifest.py`` renders each manifest from ``plan.a0a_slots`` and
``plan.a1_slots``; ``lane.validate_manifest`` refuses any registered manifest whose slots
or fill blocks differ (sections 5.4-5.6, 6.1).
"""

from __future__ import annotations

import collections
import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from harness.q2_stage1 import lane
from harness.q2_stage1 import plan as P
from harness.q2_stage1.records import validate

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import preregister  # noqa: E402
import render_q2_stage1_manifest as builder  # noqa: E402
import render_q2_stage1_plan as renderer  # noqa: E402

RUNS = "/home/kevin/cotcodec-runs/stage0/q2-stage1"
HOST = {
    "run_root": f"{RUNS}/runs",
    "vm": {**lane.VM_PINS, "guest_ip": "20.20.20.21",
           "qcow2": {"host_path": f"{RUNS}/../q2-action-path/vm/Ubuntu.qcow2",
                     "sha256": lane.QCOW2_SHA256, "size_bytes": lane.QCOW2_BYTES}},
    "osworld": {"host_dir": f"{RUNS}/inputs/OSWorld", "commit": lane.OSWORLD_COMMIT},
    "file_cache": {"host_dir": f"{RUNS}/inputs/files"},
    "engine": {"bridge_dir": f"{RUNS}/gpu/{{gpu_job_id}}/bridge",
               "gpu_job_id_file": f"{RUNS}/pairs/a1/gpu_job_id"},
}  # fmt: skip
DEV_A0A = ["6a33f9b9", "bf4e9888", "d681960f", "4172ea6e", "12382c62"]  # G0 item 5


def a0a(n_star: int = 40) -> dict[str, Any]:
    return builder.vm_manifest(purpose="a0a", host=HOST, source_dir=ROOT, n_star=n_star)


def test_a0a_manifest_is_the_plans_and_the_lane_accepts_it():
    m = a0a()
    assert lane.validate_manifest(m, ROOT)["slots"] == m["slots"]
    assert m["vm"]["concurrency"] == 20 and m["slurm"]["cpus"] == 90
    assert m["slurm"]["minutes"] == 35 and m["engine"]["gpu_cap_min"] == 25
    assert m["date"] == P.PROMPT_DATE and "fill" not in m
    assert lane.check_slurm(m)["cpus"] == 90
    slots = m["slots"]
    assert len(slots) == 20 and sorted({s["task_id"][:8] for s in slots}) == sorted(DEV_A0A)
    cells = collections.Counter((s["task_id"], s["harness"], s["rerun"]) for s in slots)
    assert set(cells.values()) == {1} and len(cells) == 20
    assert {(s["block"], s["rerun"]) for s in slots} == {("a0a.1", 1), ("a0a.2", 2)}
    assert {(s["job"], s["size"], s["session"]) for s in slots} == {("A0a", "9B", "S1")}
    assert m["episode_image_id"] == lane.EPISODE_IMAGE_ID
    assert not set(lane.FIXED_KEYS) & set(m)
    with pytest.raises(ValueError, match="back to review before A0a"):
        a0a(16)  # N* = 16: K_base 32 is out of reach at V = 16 (section 5.5)
    small = P.a0a_slots(json.loads((ROOT / lane.SPLITS).read_text())["dev"],
                        P.dev_setup_ok(P.load_setup_check(ROOT)),
                        16)  # fmt: skip
    assert sorted({s["task_id"][:8] for s in small}) == sorted(DEV_A0A[:4])
    with pytest.raises(ValueError, match="may not set"):
        builder.vm_manifest(purpose="a0a", host={**HOST, "episode_timeout_s": 60},
                            source_dir=ROOT, n_star=40)  # fmt: skip


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        (lambda m: m["slots"].reverse(), "slots differ from plan.a0a_slots"),
        (lambda m: m["slots"][0].update(rerun=2), "slots differ"),
        (lambda m: m["slots"].pop(), "slots differ"),
        (lambda m: m.update(n_star=24), None),  # N* = 24 is V = 20 too: still valid
        (lambda m: m.update(n_star=16), "back to review before A0a"),
        (lambda m: m.update(n_star=8), "S1a does not start"),
        (lambda m: m.pop("n_star"), "n_star is required"),
        (lambda m: m["engine"].update(gpu_cap_min=30), "GPU cap is 25"),
        (lambda m: m.update(episode_image_id="sha256:" + "2" * 64), "registered metric image"),
        (lambda m: m.update(requeue=False), "requeue is fixed"),
        (lambda m: m.update(episode_timeout_s=60), "episode_timeout_s is fixed"),
        (lambda m: m.update(episode_python="/usr/bin/python3"), "episode_python is fixed"),
        (lambda m: m["engine"].update(bridge_dir=f"{RUNS}/gpu/1/bridge"), "gpu_job_id"),
    ],
)
def test_a0a_manifest_that_differs_from_the_plan_is_refused(tamper, message):
    m = a0a()
    tamper(m)
    if message is None:
        lane.validate_manifest(m, ROOT)
        return
    with pytest.raises(lane.LaneError, match=message):
        lane.validate_manifest(m, ROOT)


def test_anchor_purposes_are_refused():
    for purpose in ("a0b", "anc"):
        m = a0a()
        m["purpose"] = purpose
        with pytest.raises(lane.LaneError, match="anchor is UNAVAILABLE|runs only after"):
            lane.validate_manifest(m, ROOT)


def test_committed_development_manifests_still_validate():
    for name in ("dev-smoke-v1", "setup-check-v1"):
        m = json.loads((ROOT / f"experiments/manifests/q2-stage1/{name}.json").read_text())
        assert lane.validate_manifest(m, ROOT)["purpose"] in ("development", "setup-check")


# --------------------------------------------------------------------------- A1 (frozen)

GATES = P.a0a_gates(
    [{"harness": h, "steps": [{"executed": [{"timing_s": {"total": 2.0}}]}]} for h in P.HARNESSES],
    2.71,
)


@pytest.fixture(scope="module")
def frozen_tree(tmp_path_factory) -> tuple[Path, dict[str, Any]]:
    """A source tree as the freeze leaves it: the ledger row, the frozen plan file and the
    registration stating its digest (anchor unavailable, K_base 32)."""
    root = tmp_path_factory.mktemp("src")
    (root / "program/evidence/q2-mutation").mkdir(parents=True)
    shutil.copy(ROOT / lane.SPLITS, root / lane.SPLITS)
    inputs = renderer.load_inputs(ROOT)
    constants = P.freeze_constants(
        n_star=40, a0a_slot_seconds=[640.0] * 20, launch_a0a_min=4, prefreeze_caps=[3, 25],
        anchor_available=False, a0a_gates=GATES,
    )  # fmt: skip
    plan = P.render_plan(**inputs, constants=constants)
    (root / "plan").mkdir()
    (root / "plan/plan-frozen.json").write_text(json.dumps(plan, indent=1, sort_keys=True))
    freeze(root, f"Frozen plan SHA-256: `{plan['plan_sha256']}`.\n")
    return root, plan


def freeze(root: Path, registration: str) -> None:
    """Write the registration and freeze it into a fresh ledger, as ``scripts/preregister.py
    freeze`` does."""
    path = root / lane.REGISTRATION
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(registration, encoding="utf-8")
    ledger = root / lane.LEDGER
    ledger.unlink(missing_ok=True)
    preregister.freeze(path, lane.EXPERIMENT_ID, ledger=ledger, root=root)


def a1(tree: tuple[Path, dict[str, Any]], size: str, session: str, prior=()) -> dict:
    return builder.vm_manifest(
        purpose="a1", host=HOST, source_dir=tree[0], plan_path="plan/plan-frozen.json",
        size=size, session=session, prior_run_dirs=prior,
    )  # fmt: skip


def run_dir(tmp: Path, job: str, rows: list[dict[str, Any]], t_end: float = 1.0e9,
            error: str | None = None) -> Path:  # fmt: skip
    """A finished A1 job's lane run directory: manifest, records and receipt."""
    _, size, session = job.split("-")
    out = tmp / job
    out.mkdir(parents=True, exist_ok=True)
    (out / "manifest.json").write_text(
        json.dumps({"purpose": "a1", "a1": {"size": size, "session": session}})
    )
    (out / "episodes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    receipt = {"t_end": t_end, **({"error": error} if error else {})}
    (out / "lane-receipt.json").write_text(json.dumps(receipt))
    return out


def scored_base(plan: dict[str, Any], size: str, session: str) -> list[dict[str, Any]]:
    slots, _ = P.a1_slots(plan, size, session, [] if session == "S2" else None)
    common = {"schema": "q2-stage1a-episode-v1", "attempt": 1, "status": "scored", "score": 1.0}
    return [{**s, **common} for s in slots if s["extension_block"] is None]


def test_a1_session_one_manifest_is_the_plans(frozen_tree):
    root, plan = frozen_tree
    m = a1(frozen_tree, "9B", "S1")
    assert P.a1_job_order()[0] == "A1-9B-S1" and m["a1"]["prior_jobs"] == []
    lane.validate_manifest(m, root)
    base = plan["base"]
    assert len(base) == 32 and len(m["slots"]) == 32 * 2 * 2
    assert [s["block"] for s in m["slots"]] == ["b1"] * 64 + ["b2"] * 64
    assert all(s["rerun"] == int(s["block"][1]) for s in m["slots"])  # rerun r is block r
    orders = plan["episode_orders"]
    assert [[s["task_id"], s["harness"]] for s in m["slots"][:64]] == orders["S1:9B:b1"]
    assert m["vm"]["concurrency"] == 20 and m["slurm"]["cpus"] == 90
    assert m["slurm"]["minutes"] == 121 and m["engine"]["gpu_cap_min"] == 111
    fill = m["fill"]
    assert fill["block_episodes"] == 32 and len(fill["blocks"]) == 11
    first = fill["blocks"][0]
    assert first["label"] == "x01" and [b["label"] for b in first["sub_blocks"]] == [
        "x01.1", "x01.2"]  # fmt: skip
    for sub in first["sub_blocks"]:
        rerun = int(sub["label"][-1])
        assert {(s["rerun"], s["extension_block"]) for s in sub["slots"]} == {(rerun, 1)}
        assert sorted({s["task_id"] for s in sub["slots"]}) == sorted(plan["extension_blocks"]["1"])
    last = plan["extension_blocks"][str(len(fill["blocks"]))]
    assert len(fill["blocks"][-1]["sub_blocks"][0]["slots"]) == 2 * len(last) < 16  # short last
    for slot in m["slots"]:
        validate(
            {**slot, "schema": "q2-stage1a-episode-v1", "attempt": 1, "status": "cap_truncated"}
        )


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        (lambda m: m["slots"].reverse(), "slots differ from plan.a1_slots"),
        (lambda m: m["slots"][3].update(rerun=2), "slots differ"),
        (lambda m: m["fill"]["blocks"].pop(0), "fill differs"),
        (lambda m: m["fill"]["blocks"][0]["sub_blocks"].reverse(), "fill differs"),
        (lambda m: m["a1"].update(size="4B"), "prior_jobs must be \\['A1-9B-S1'\\]"),
        (lambda m: m["engine"].update(gpu_cap_min=120), "T_A1 = 111"),
        (lambda m: m["plan"].update(sha256="0" * 64), "does not match its digest"),
    ],
)
def test_a1_manifest_that_differs_from_the_plan_is_refused(frozen_tree, tamper, message):
    m = a1(frozen_tree, "9B", "S1")
    tamper(m)
    with pytest.raises(lane.LaneError, match=message):
        lane.validate_manifest(m, frozen_tree[0])


def test_a1_needs_the_registered_frozen_plan(frozen_tree, tmp_path):
    root, plan = frozen_tree
    other = tmp_path / "src"
    shutil.copytree(root, other)
    freeze(other, "Frozen plan SHA-256: (not stated).\n")
    with pytest.raises(lane.LaneError, match="does not name this plan"):
        lane.validate_manifest(a1(frozen_tree, "9B", "S1"), other)
    draft = P.render_plan(**renderer.load_inputs(ROOT))
    (other / "plan/draft.json").write_text(json.dumps(draft))
    freeze(other, f"Frozen plan SHA-256: `{draft['plan_sha256']}`.\n")
    m = a1(frozen_tree, "9B", "S1")
    m["plan"] = {"path": "plan/draft.json", "sha256": draft["plan_sha256"]}
    with pytest.raises(lane.LaneError, match="frozen plan"):
        lane.validate_manifest(m, other)


def test_post_freeze_jobs_need_the_registration_the_ledger_froze(frozen_tree, tmp_path):
    """Section 5.5: A1 and ANC are admitted only while the source tree's registration has
    its ledger row's SHA-256 and the chain holds (what ``preregister.py verify`` and
    ``check-chain`` check), not merely while a row exists; the GPU half is rendered only from
    a VM manifest the lane validates, so it is refused too."""
    root, _ = frozen_tree
    row = lane.frozen_registration(root)
    assert row["path"] == lane.REGISTRATION
    assert row["sha256"] == lane.sha256_file(root / lane.REGISTRATION)
    m = a1(frozen_tree, "9B", "S1")
    lane.validate_manifest(m, root)
    anc = copy.deepcopy(m)
    anc["purpose"] = "anc"
    anc.pop("fill")
    with pytest.raises(lane.LaneError, match="anchor is UNAVAILABLE"):
        lane.validate_manifest(anc, root)

    edited = tmp_path / "edited"
    shutil.copytree(root, edited)
    reg = edited / lane.REGISTRATION
    reg.write_text(reg.read_text(encoding="utf-8") + "A rule added after the freeze.\n")
    for manifest in (m, anc):
        with pytest.raises(lane.LaneError, match="changed after the freeze"):
            lane.validate_manifest(manifest, edited)
    (tmp_path / "a1.json").write_text(json.dumps(m))
    (tmp_path / "values.json").write_text("{}")
    with pytest.raises(lane.LaneError, match="changed after the freeze"):
        builder.main(["gpu", "--vm-manifest", str(tmp_path / "a1.json"), "--source-dir",
                      str(edited), "--vm-job-id", "5", "--values", str(tmp_path / "values.json"),
                      "--out", str(tmp_path / "gpu.yaml")])  # fmt: skip
    assert not (tmp_path / "gpu.yaml").exists()

    # A ledger row moved to the edited file's digest breaks the chain.
    ledger = edited / lane.LEDGER
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
    rows[-1]["sha256"] = lane.sha256_file(reg)
    ledger.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    with pytest.raises(lane.LaneError, match="hash chain does not hold"):
        lane.validate_manifest(m, edited)

    # A row that names only the id (no digest) is not a freeze.
    bare = tmp_path / "bare"
    shutil.copytree(root, bare)
    (bare / lane.LEDGER).write_text(json.dumps({"experiment_id": lane.EXPERIMENT_ID}) + "\n")
    assert lane.frozen(bare)
    with pytest.raises(lane.LaneError, match="hash chain does not hold"):
        lane.validate_manifest(m, bare)


def test_a1_jobs_run_in_order_and_stop_when_dr0_fired(frozen_tree, tmp_path, monkeypatch):
    """Section 11: each A1 job names every earlier one's records and receipt by digest (9B
    then 4B, session 1 then 2), and none may have fired DR0."""
    root, plan = frozen_tree
    monkeypatch.setattr(lane, "RUN_ROOT", "/")  # the run directories live in tmp_path here
    with pytest.raises(ValueError, match="needs the run directories of \\['A1-9B-S1'\\]"):
        a1(frozen_tree, "4B", "S1")  # 4B before 9B's session-1 job ran
    good = run_dir(tmp_path / "ok", "A1-9B-S1", scored_base(plan, "9B", "S1"))
    m = a1(frozen_tree, "4B", "S1", [good])
    lane.validate_manifest(m, root)
    # DR0 fires on the earlier job: more than 5% of a cell's first attempts lost.
    rows = scored_base(plan, "9B", "S1")
    for row in rows[:8]:
        row.update(status="infrastructure", score=None, infrastructure_type="transport")
    rows += [dict(r, attempt=2, status="scored", score=1.0, infrastructure_type=None)
             for r in rows[:8]]  # fmt: skip
    lossy = run_dir(tmp_path / "lossy", "A1-9B-S1", rows)
    with pytest.raises(lane.LaneError, match="DR0 fired for A1-9B-S1 .cell loss"):
        lane.validate_manifest(a1(frozen_tree, "4B", "S1", [lossy]), root)
    incomplete = run_dir(tmp_path / "short", "A1-9B-S1", scored_base(plan, "9B", "S1")[:-3])
    with pytest.raises(lane.LaneError, match="base incomplete"):
        lane.validate_manifest(a1(frozen_tree, "4B", "S1", [incomplete]), root)
    refused = run_dir(tmp_path / "err", "A1-9B-S1", scored_base(plan, "9B", "S1"),
                      error="LaneError: engine argv")  # fmt: skip
    with pytest.raises(lane.LaneError, match="gate of section 3"):
        lane.validate_manifest(a1(frozen_tree, "4B", "S1", [refused]), root)
    tampered = a1(frozen_tree, "4B", "S1", [good])
    (good / "episodes.jsonl").write_text("")
    with pytest.raises(lane.LaneError, match="does not match its digest"):
        lane.validate_manifest(tampered, root)


def s1_records(plan: dict[str, Any], tmp: Path, done: dict[str, set[int]],
               t_end: float = 1.0e9) -> list[Path]:  # fmt: skip
    """Both session-1 jobs' lane run directories: the base scored, the extension blocks in
    ``done[size]`` final (one slot lost after its re-queue), the next block cut at USR1."""
    tmp.mkdir(parents=True, exist_ok=True)
    files = []
    for size in P.size_order():
        slots, fill = P.a1_slots(plan, size, "S1")
        blocks = {int(b["label"][1:]): b for b in fill["blocks"]}
        cut_block = max(done[size], default=0) + 1
        finished = [s for b in sorted(done[size]) for sub in blocks[b]["sub_blocks"]
                    for s in sub["slots"]]  # fmt: skip
        cut = [s for sub in blocks[cut_block]["sub_blocks"] for s in sub["slots"]][:5]
        common = {"schema": "q2-stage1a-episode-v1", "attempt": 1}
        rows = [{**s, **common, "status": "scored", "score": 1.0} for s in slots + finished]
        rows += [{**s, **common, "status": "cap_truncated", "score": None} for s in cut]
        rows += [dict(rows[len(slots)], attempt=2, status="infrastructure", score=None,
                      infrastructure_type="transport")] if finished else []  # fmt: skip
        files.append(run_dir(tmp, P.a1_job(size, "S1"), rows, t_end=t_end))
    return files


def test_a1_session_two_runs_the_blocks_both_session_one_jobs_completed(
    frozen_tree, tmp_path, monkeypatch
):
    root, plan = frozen_tree
    monkeypatch.setattr(lane, "RUN_ROOT", "/")  # the record files live in tmp_path here
    files = s1_records(plan, tmp_path / "both", {"9B": {1, 2}, "4B": {1, 2}})
    s2_9b = run_dir(tmp_path / "both", "A1-9B-S2", scored_base(plan, "9B", "S2"))
    m = a1(frozen_tree, "4B", "S2", files + [s2_9b])
    assert m["a1"]["s2_extension_blocks"] == [1, 2] and "fill" not in m
    assert [j["job"] for j in m["a1"]["prior_jobs"]] == P.a1_job_order()[:3]
    lane.validate_manifest(m, root)
    blocks = [s["block"] for s in m["slots"]]
    assert blocks == ["b1"] * 64 + ["b2"] * 64 + ["x01.1"] * 16 + ["x01.2"] * 16 + [
        "x02.1"] * 16 + ["x02.2"] * 16  # fmt: skip
    assert m["slots"][0]["job"] == "A1-4B-S2" and m["slots"][-1]["extension_block"] == 2
    assert [[s["task_id"], s["harness"]] for s in m["slots"][128:144]] == plan["episode_orders"][
        "S2:4B:x01.1"]  # fmt: skip
    for tamper, message in (
        (lambda x: x["a1"].update(s2_extension_blocks=[1, 2, 3]), "must be \\[1, 2\\]"),
        (lambda x: x["a1"]["prior_jobs"].pop(0), "prior_jobs must be"),
        (lambda x: x["a1"]["prior_jobs"][0]["records"].update(sha256="0" * 64), "does not match"),
        (lambda x: x["slots"].pop(), "slots differ"),
    ):
        bad = copy.deepcopy(m)
        tamper(bad)
        with pytest.raises(lane.LaneError, match=message):
            lane.validate_manifest(bad, root)
    # A block that only one size completed does not run in session 2.
    uneven = s1_records(plan, tmp_path / "uneven", {"9B": {1, 2}, "4B": {1}})
    m = a1(frozen_tree, "9B", "S2", uneven)
    assert m["a1"]["s2_extension_blocks"] == [1]
    lane.validate_manifest(m, root)


def test_session_two_waits_twelve_hours_after_session_one(frozen_tree, tmp_path, monkeypatch):
    """Section 5.5: the S2 jobs start at least 12 h after the later S1 job ends. The lane
    refuses to start earlier, and the submission holds the job with --begin."""
    root, plan = frozen_tree
    monkeypatch.setattr(lane, "RUN_ROOT", "/")
    ends = 1.9e9
    files = s1_records(plan, tmp_path / "s1", {"9B": set(), "4B": set()}, t_end=ends)
    m = a1(frozen_tree, "9B", "S2", files)
    lane.validate_manifest(m, root)
    assert lane.earliest_start(m) == ends + 12 * 3600
    assert lane.earliest_start(a1(frozen_tree, "9B", "S1")) is None
    now = [ends + 11 * 3600]
    cfg = lane.LaneConfig(m, "999", tmp_path / "run", root)
    cfg.run_dir.mkdir()
    early = lane.Lane(cfg, docker=object(), certified=["Return"], clock=lambda: now[0])
    receipt = early.run()
    assert "at least 12 h" in receipt["error"] and receipt["dispatched"] == []
    assert receipt["statuses"] == {"cap_truncated": len(m["slots"])}  # never dispatched


def test_gpu_half_comes_from_the_vm_manifest(frozen_tree):
    """The GPU half's size and minutes are the VM manifest's (A0a: 9B for 25 minutes; A1:
    its size for the frozen T_A1), never free arguments."""
    import yaml

    template = (ROOT / builder.GPU_TEMPLATE).read_text()
    values = {
        "FILL_JOB": "x", "FILL_OVERLAY_IMAGE_ID": "sha256:" + "3" * 64,
        "FILL_GIT_SHA": "1234567" * 5 + "89abc", "FILL_SOURCE_SHA256": "5" * 64,
        "FILL_RECEIPT_SHA256": "6" * 64, "FILL_ARTIFACT_ROOT_SHA256": "7" * 64,
    }  # fmt: skip
    gpu = yaml.safe_load(builder.gpu_for_vm_manifest(template, a0a(), vm_job_id="5", values=values))
    assert gpu["resources"]["minutes"] == 25 and gpu["command"][-5] == "9B"
    one = a1(frozen_tree, "9B", "S1")
    gpu = yaml.safe_load(builder.gpu_for_vm_manifest(template, one, vm_job_id="5", values=values))
    assert gpu["resources"]["minutes"] == 111 and gpu["model"]["model_id"] == "qwen3.5-9b"
    with pytest.raises(ValueError, match="may hold only"):
        builder.gpu_for_vm_manifest(template, one, vm_job_id="5",
                                    values={**values, "FILL_CAP_MINUTES": "200"})  # fmt: skip


def test_gpu_half_from_the_builder_passes_the_docker_submitter():
    import yaml

    from scripts.submit_docker_research_job import sbatch_argv
    from scripts.submit_docker_research_job import validate_manifest as validate_gpu

    template = (ROOT / builder.GPU_TEMPLATE).read_text()
    values = {
        "FILL_JOB": "a1-9b-s1", "FILL_OVERLAY_IMAGE_ID": "sha256:" + "3" * 64,
        "FILL_GIT_SHA": "1234567" * 5 + "89abc", "FILL_SOURCE_SHA256": "5" * 64,
        "FILL_RECEIPT_SHA256": "6" * 64, "FILL_ARTIFACT_ROOT_SHA256": "7" * 64,
    }  # fmt: skip
    text = builder.gpu_manifest(template, size="9B", minutes=111, vm_job_id="4321", values=values)
    manifest = validate_gpu(yaml.safe_load(text))
    assert manifest["model"]["revision"] == builder.MODELS["9B"][1]
    assert manifest["minutes"] == 111 and manifest["start_after_job_id"] == "4321"
    assert "--dependency=after:4321" in sbatch_argv(manifest, test_only=False)
    with pytest.raises(ValueError, match="unfilled template slots"):
        builder.gpu_manifest(template, size="9B", minutes=111, vm_job_id="4321", values={})
