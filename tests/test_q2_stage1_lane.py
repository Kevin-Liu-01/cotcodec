"""The S1a VM lane: manifest rules, dispatch, re-queue, stop and fill (sections 5.5-5.7, 14)."""

from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any

import pytest

from harness.q2_stage1 import lane
from harness.q2_stage1.records import validate

ROOT = Path(__file__).resolve().parents[1]
SPLITS = json.loads((ROOT / lane.SPLITS).read_text())
DEV = sorted(SPLITS["dev"])
CONFIRM = sorted(t for t in SPLITS["confirm"] if t[:8] not in ("0a0faba3", "15aece23"))
RUNS = "/home/kevin/cotcodec-runs/stage0/q2-stage1"


def slot(i: int, task: str, block: str = "b1", harness: str = "H-OSW-fixed") -> dict[str, Any]:
    return {"slot": f"dev:{block}:{i}", "job": "dev-smoke", "size": "9B", "session": "S1",
            "task_id": task, "harness": harness, "rerun": 1, "block": block,
            "extension_block": None}  # fmt: skip


def manifest(**overrides: Any) -> dict[str, Any]:
    m = {
        "schema": lane.SCHEMA,
        "experiment_id": lane.EXPERIMENT_ID,
        "purpose": "development",
        "name": "dev-smoke-v1",
        "run_root": f"{RUNS}/runs",
        "vm": {**lane.VM_PINS, "guest_ip": "20.20.20.21", "concurrency": 1,
               "qcow2": {"host_path": f"{RUNS}/../q2-action-path/vm/Ubuntu.qcow2",
                         "sha256": lane.QCOW2_SHA256, "size_bytes": lane.QCOW2_BYTES}},
        "episode_image_id": "sha256:" + "2" * 64,
        "osworld": {"host_dir": f"{RUNS}/inputs/OSWorld", "commit": lane.OSWORLD_COMMIT},
        "file_cache": {"host_dir": f"{RUNS}/inputs/files"},
        "engine": {"kind": "fake", "script": {"replies": ["x"]}},
        "mode": "episode",
        "slots": [slot(0, DEV[0])],
        "slurm": {"cpus": 8, "memory_gb": 16, "minutes": 60},
    }  # fmt: skip
    m.update(overrides)
    return m


def test_a_development_manifest_is_valid():
    out = lane.validate_manifest(manifest(), ROOT)
    assert out["slots"][0]["task_id"] == DEV[0]


@pytest.mark.parametrize(
    "change, message",
    [
        ({"slots": [slot(0, CONFIRM[0])]}, "not a dev-split task"),
        ({"purpose": "a0a"}, "fake engine is for development only"),
        ({"purpose": "a1"}, "runs only after the freeze"),
        ({"purpose": "anc"}, "runs only after the freeze"),
        ({"mode": "setup-only"}, "runs mode episode"),
        ({"step_cap": 10}, "step_cap is 15"),
        ({"settle_after_reset_s": 0}, "settle after reset"),
        ({"slots": [slot(0, DEV[0]), slot(0, DEV[1])]}, "duplicate slot"),
        ({"osworld": {"host_dir": f"{RUNS}/x", "commit": "0" * 40}}, "osworld.commit"),
    ],
)
def test_manifest_rules(change, message):
    with pytest.raises(lane.LaneError, match=message):
        lane.validate_manifest(manifest(**change), ROOT)


def test_vm_settings_are_the_action_path_runtime():
    for key, value in (("cpu_cores", 2), ("ram_size", "8G"), ("network", "bridge-unpublished")):
        m = manifest()
        m["vm"][key] = value
        with pytest.raises(lane.LaneError, match=f"vm.{key}"):
            lane.validate_manifest(m, ROOT)


def test_setup_check_touches_pool_and_dev_but_runs_nothing_else():
    slots = [slot(0, DEV[0]), slot(1, CONFIRM[0])]
    m = manifest(purpose="setup-check", mode="setup-only", engine={"kind": "none"}, slots=slots)
    assert len(lane.validate_manifest(m, ROOT)["slots"]) == 2
    with pytest.raises(lane.LaneError, match="runs no engine"):
        lane.validate_manifest({**m, "engine": {"kind": "fake", "script": {}}}, ROOT)
    k1 = next(t for t in SPLITS["confirm"] if t.startswith("0a0faba3"))
    with pytest.raises(lane.LaneError, match="not a pool or dev task"):
        lane.validate_manifest({**m, "slots": [slot(0, k1)]}, ROOT)


def test_dispatcher_blocks_and_requeue():
    d = lane.Dispatcher([slot(0, "a", "b1"), slot(1, "b", "b1"), slot(2, "c", "b2")])
    first = d.next()
    d.requeue(first)  # its block still has b pending: goes after b
    assert [d.next().id, d.next().id] == ["dev:b1:1", "dev:b1:0"]
    third = d.next()
    assert third.id == "dev:b2:2"
    d.requeue(third)  # its block is exhausted: dispatched next
    again = d.next()
    assert again.id == "dev:b2:2" and again.attempt == 2
    assert d.next() is None


class FakeDocker:
    """Simulates VM start, the episode container and teardown."""

    def __init__(self, outcomes: dict[str, list[str]], block_until: threading.Event | None = None):
        self.outcomes = {k: list(v) for k, v in outcomes.items()}
        self.vms: list[list[str]] = []
        self.episodes: list[list[str]] = []
        self.removed: list[str] = []
        self.block_until = block_until

    def start_vm(self, argv: list[str]) -> None:
        self.vms.append(argv)

    def run_episode(self, argv, name, timeout, stop, log):
        self.episodes.append(argv)
        out = Path(next(v.split(":")[0] for v in argv if v.endswith(":/out")))
        config = json.loads((out / "config.json").read_text())
        if self.block_until is not None:
            self.block_until.wait(5)
            if stop.is_set():
                return None
        queue = self.outcomes.get(config["task_id"])
        outcome = queue.pop(0) if queue else "scored"
        record = {
            "schema": "q2-stage1a-episode-v1", "job": config["job"], "size": config["size"],
            "session": config["session"], "task_id": config["task_id"],
            "harness": config["harness"], "rerun": config["rerun"],
            "extension_block": config["extension_block"], "attempt": config["attempt"],
            "slot": config["slot"], "block": config["block"],
            "status": outcome, "score": 1.0 if outcome == "scored" else None,
            "infrastructure_type": "vm_boot" if outcome == "infrastructure" else None,
        }  # fmt: skip
        (out / "episode.json").write_text(json.dumps(record))
        return 0

    def remove(self, name: str) -> dict[str, Any]:
        self.removed.append(name)
        return {"container_gone": True}


def make_lane(tmp_path: Path, m: dict[str, Any], docker: FakeDocker, **kw: Any) -> lane.Lane:
    m = copy.deepcopy(m)
    m["engine"] = {"kind": "none"}
    cfg = lane.LaneConfig(m, "999", tmp_path / "run", ROOT)
    cfg.run_dir.mkdir()
    return lane.Lane(cfg, docker=docker, certified=["Return"], **kw)


def test_lane_runs_requeues_once_and_records(tmp_path):
    slots = [slot(0, DEV[0]), slot(1, DEV[1]), slot(2, DEV[2], "b2")]
    docker = FakeDocker({DEV[1]: ["infrastructure", "infrastructure"]})
    receipt = make_lane(tmp_path, manifest(slots=slots), docker).run()
    records = [json.loads(x) for x in (tmp_path / "run/episodes.jsonl").read_text().splitlines()]
    assert receipt["statuses"] == {"scored": 2, "infrastructure": 2}
    lost = [r for r in records if r["task_id"] == DEV[1]]
    assert [r["attempt"] for r in lost] == [1, 2]  # one re-queue, then missing
    assert len(docker.removed) == len(docker.vms) == 4
    assert all("slot_occupancy_s" in r["host"] for r in records)
    assert receipt["dispatched"] == ["dev:b1:0#1", "dev:b1:1#1", "dev:b1:1#2", "dev:b2:2#1"]
    for r in records:
        validate({k: v for k, v in r.items() if k != "host"})


def test_vm_and_episode_containers_are_gpu_less_and_isolated(tmp_path):
    docker = FakeDocker({})
    make_lane(tmp_path, manifest(), docker).run()
    vm_argv, ep_argv = docker.vms[0], docker.episodes[0]
    assert "--gpus" not in vm_argv and "--network" in vm_argv
    assert vm_argv[vm_argv.index("--network") + 1] == "none"
    assert "-p" not in vm_argv and "--publish" not in vm_argv
    joined = " ".join(ep_argv)
    assert "--gpus" not in ep_argv and "--privileged" not in ep_argv
    assert f"--network container:{vm_argv[vm_argv.index('--name') + 1]}" in joined
    assert "--read-only" in ep_argv and "--cap-drop ALL" in joined
    assert ":/src:ro" in joined and ":/inputs/OSWorld:ro" in joined
    assert ":/inputs/file_cache/files:ro" in joined
    assert "NVIDIA_VISIBLE_DEVICES=void" in joined
    assert ep_argv[ep_argv.index("-m") + 1] == "harness.q2_stage1.driver"


def test_stop_cuts_in_flight_and_records_undispatched(tmp_path):
    release = threading.Event()
    docker = FakeDocker({}, block_until=release)
    slots = [slot(i, DEV[i]) for i in range(3)]
    the_lane = make_lane(tmp_path, manifest(slots=slots), docker)
    runner = threading.Thread(target=the_lane.run)
    runner.start()
    import time

    deadline = time.time() + 10
    while not docker.episodes and time.time() < deadline:
        time.sleep(0.01)
    the_lane.stop.set()
    release.set()
    runner.join(10)
    records = [json.loads(x) for x in (tmp_path / "run/episodes.jsonl").read_text().splitlines()]
    assert [r["status"] for r in records] == ["cap_truncated"] * 3
    assert records[0]["cap_detail"] == "cut at the stop signal"
    assert {r["cap_detail"] for r in records[1:]} == {"never dispatched"}


def test_bridge_usr1_stops_dispatch(tmp_path):
    docker = FakeDocker({})
    slots = [slot(i, DEV[i]) for i in range(3)]
    the_lane = make_lane(tmp_path, manifest(slots=slots), docker)
    bridge = tmp_path / "bridge"
    bridge.mkdir()
    (bridge / "usr1.json").write_text("{}")
    the_lane.engine_dir = bridge
    the_lane.start_engine = lambda: None  # the bridge is already up and has signalled
    the_lane.run()
    assert not docker.episodes


def test_fill_rule_reads_cost_not_outcomes(tmp_path):
    now = [1000.0]
    docker = FakeDocker({})
    sub = {"label": "x01.1", "slots": [slot(9, DEV[9], "x01.1")]}
    m = manifest(slots=[slot(0, DEV[0])])
    m["fill"] = {"blocks": [{"label": "x01", "sub_blocks": [sub]}], "block_episodes": 32}
    the_lane = make_lane(tmp_path, m, docker, clock=lambda: now[0])
    the_lane.usr1_epoch = 1000.0 + 120 * 60
    the_lane.run()
    assert the_lane.fill_log and the_lane.fill_log[0]["allowed"] is True
    assert any(d == "dev:x01.1:9#1" for d in the_lane.dispatcher.dispatched)

    docker = FakeDocker({})
    m["fill"] = {"blocks": [{"label": "x01", "sub_blocks": [sub]}], "block_episodes": 32}
    (tmp_path / "late").mkdir()
    late = make_lane(tmp_path / "late", m, docker, clock=lambda: now[0])
    late.usr1_epoch = 1000.0 + 5 * 60
    late.run()
    assert late.fill_log[0]["allowed"] is False
    assert not any(d.startswith("dev:x01.1") for d in late.dispatcher.dispatched)


def test_plan_cpusets():
    sets = lane.plan_cpusets(list(range(8)), 1, 4)
    assert sets == [{"vm": "0-3", "vm_mems": None, "runner": "4-7"}]
    with pytest.raises(lane.LaneError):
        lane.plan_cpusets(list(range(8)), 2, 4)


def test_batch_script_holds_no_gpu_and_forwards_usr1():
    text = (ROOT / lane.BATCH).read_text()
    assert "#SBATCH --gres" not in text and "--gpus" not in text
    assert "#SBATCH --signal=B:USR1@120" in text
    assert 'kill -USR1 "${lane_pid}"' in text
    assert "source_tree_sha256" in text and "manifest digest mismatch" in text
    assert "label=cotcodec.slurm_job=${SLURM_JOB_ID}" in text
