"""The S1a VM lane: manifest rules, dispatch, re-queue, stop and fill (sections 5.5-5.7, 14)."""

from __future__ import annotations

import copy
import json
import math
import re
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
        (
            {
                "purpose": "a0a",
                "episode_image_id": lane.EPISODE_IMAGE_ID,
                "engine": {"kind": "fake", "bridge_dir": "{gpu_job_id}"},
            },
            "fake engine is for development only",
        ),
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


def test_bridge_dir_waits_for_the_gpu_job_id(tmp_path):
    docker = FakeDocker({})
    the_lane = make_lane(tmp_path, manifest(), docker)
    id_file = tmp_path / "gpu_job_id"
    id_file.write_text("1234\n")
    engine = {
        "bridge_dir": str(tmp_path / "gpu/{gpu_job_id}/bridge"),
        "gpu_job_id_file": str(id_file),
    }
    assert the_lane.resolve_bridge_dir(engine) == tmp_path / "gpu/1234/bridge"
    id_file.write_text("not-a-job")
    with pytest.raises(lane.LaneError, match="Slurm job id"):
        the_lane.resolve_bridge_dir(engine)
    m = manifest(purpose="development", engine={"kind": "bridge", "gpu_cap_min": 25,
                 "bridge_dir": f"{RUNS}/gpu/{{gpu_job_id}}/bridge"})  # fmt: skip
    with pytest.raises(lane.LaneError, match="gpu_job_id_file"):
        lane.validate_manifest(m, ROOT)


GPU_TEMPLATE = ROOT / "experiments/manifests/q2-stage1/gpu-engine.template.yaml"
GPU_FILLS = {
    "9B": {"FILL_MODEL_ID": "qwen3.5-9b",
           "FILL_REVISION": "c202236235762e1c871ad0ccb60c8ee5ba337b9a"},
    "4B": {"FILL_MODEL_ID": "qwen3.5-4b",
           "FILL_REVISION": "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"},
    "anchor": {"FILL_MODEL_ID": "opencua-7b",
               "FILL_REVISION": "a2efb7d2b104d477a4a2666a357e79550a28aafc"},
}  # fmt: skip


def fill_gpu_template(size: str, minutes: int, vm_job: str) -> dict[str, Any]:
    import yaml

    text = GPU_TEMPLATE.read_text()
    values = {
        "FILL_JOB": f"a1-{size.lower()}-s1",
        "FILL_OVERLAY_IMAGE_ID": "sha256:" + "3" * 64,
        "FILL_GIT_SHA": "4" * 40,
        "FILL_SOURCE_SHA256": "5" * 64,
        "FILL_VM_JOB_ID": vm_job,
        "FILL_CAP_MINUTES": str(minutes),
        "FILL_CAP_HOURS": f"{math.ceil(minutes / 60 * 1e4) / 1e4:.4f}",  # never below the cap
        "FILL_RECEIPT_SHA256": "6" * 64,
        "FILL_ARTIFACT_ROOT_SHA256": "7" * 64,
        "FILL_SIZE": size,
        **GPU_FILLS[size],
    }
    for key in sorted(values, key=len, reverse=True):
        text = text.replace(key, values[key])
    assert not re.search(r"FILL_[A-Z]", text)
    return yaml.safe_load(text)


@pytest.mark.parametrize(("size", "minutes"), [("9B", 111), ("4B", 111), ("anchor", 26)])
def test_filled_gpu_template_passes_the_docker_submitter(size, minutes):
    """The GPU half of a pair: the submitter accepts the filled template and holds the job
    until its VM job starts (section 5.5)."""
    from scripts.submit_docker_research_job import sbatch_argv
    from scripts.submit_docker_research_job import validate_manifest as validate_gpu

    manifest = validate_gpu(fill_gpu_template(size, minutes, "4321"))
    assert manifest["seeds"] == [] and manifest["start_after_job_id"] == "4321"
    argv = sbatch_argv(manifest, test_only=False)
    for flag in (
        "--gres=gpu:h100:1",
        "--cpus-per-task=32",
        "--signal=B:USR1@180",
        "--dependency=after:4321",
        f"--time=0{minutes // 60}:{minutes % 60:02d}:00",
    ):
        assert flag in argv, flag  # fmt: skip
    assert manifest["command"][-6:-4] == ["--size", size]
    raw = fill_gpu_template(size, minutes, "4321")
    raw["seeds"] = [42]
    with pytest.raises(ValueError, match="deterministic jobs cannot declare seeds"):
        validate_gpu(raw)


def slurm_view(purpose: str, v: int, cpus: int, minutes: int, gpu_cap: int | None = 25):
    engine = {"kind": "bridge", "gpu_cap_min": gpu_cap} if gpu_cap else {"kind": "fake"}
    return {"purpose": purpose, "vm": {"concurrency": v, "cpu_cores": 4}, "engine": engine,
            "slurm": {"cpus": cpus, "memory_gb": 6 * v + 6, "minutes": minutes}}  # fmt: skip


def test_registered_vm_jobs_take_section_5_5s_cpus():
    """A0a and A1 at V = 20 take 4V + runner_cpus(V) = 90 CPUs (72 at V = 16), and the VM
    job's limit is the GPU cap plus 10 minutes."""
    assert lane.check_slurm(slurm_view("a0a", 20, 90, 35)) == {
        "cpus": 90, "memory_gb": 126, "minutes": 35}  # fmt: skip
    assert lane.check_slurm(slurm_view("a1", 20, 90, 121, gpu_cap=111))["cpus"] == 90
    assert lane.check_slurm(slurm_view("a1", 16, 72, 114, gpu_cap=104))["cpus"] == 72
    for bad, message in (
        (slurm_view("a0a", 20, 8, 35), "must be 4V"),  # the old 8-CPU cap
        (slurm_view("a0a", 20, 89, 35), "= 90 at V = 20"),
        (slurm_view("a0a", 20, 90, 60), "GPU cap plus 10"),
        (slurm_view("a1", 40, 180, 121, gpu_cap=111), "212 CPUs, above 200"),
    ):
        with pytest.raises(lane.LaneError, match=message):
            lane.check_slurm(bad)
    with pytest.raises(lane.LaneError, match="host-load CPU limit applies to"):
        lane.check_slurm(slurm_view("a0a", 20, 90, 35), host_load_cpus=8)


def test_host_load_limit_is_an_operator_flag_for_development_and_setup_checks():
    dev = slurm_view("development", 1, 8, 45, gpu_cap=None)
    assert lane.check_slurm(dev, host_load_cpus=8)["cpus"] == 8
    assert lane.check_slurm(slurm_view("setup-check", 1, 5, 240, gpu_cap=None))["cpus"] == 5
    with pytest.raises(lane.LaneError, match="above the host-load limit 8"):
        lane.check_slurm(slurm_view("development", 2, 12, 45, gpu_cap=None), host_load_cpus=8)
    with pytest.raises(lane.LaneError, match="fit 2 VMs"):
        lane.check_slurm(slurm_view("development", 2, 8, 45, gpu_cap=None))
    # The committed development and setup-check manifests still pass under the 8-CPU flag.
    for name in ("dev-smoke-v1", "setup-check-v1"):
        m = json.loads((ROOT / f"experiments/manifests/q2-stage1/{name}.json").read_text())
        assert lane.check_slurm(m, host_load_cpus=8)["cpus"] == 8


def test_registered_purposes_pin_the_prompt_date(tmp_path):
    """Every A0a/A0b/ANC/A1 episode sees one system-prompt date (plan.PROMPT_DATE), so
    between- and within-session pairs do not differ by a calendar change in the prompt."""
    from harness.q2_stage1 import plan

    bridge = {"kind": "bridge", "gpu_cap_min": 25, "bridge_dir": f"{RUNS}/gpu/{{gpu_job_id}}/b",
              "gpu_job_id_file": f"{RUNS}/pairs/a0a/gpu_job_id"}  # fmt: skip
    for date in (None, "2026-10-09"):
        m = manifest(purpose="a0a", engine=bridge, episode_image_id=lane.EPISODE_IMAGE_ID)
        if date:
            m["date"] = date
        with pytest.raises(lane.LaneError, match="pinned prompt date 2026-10-08"):
            lane.validate_manifest(m, ROOT)
    with pytest.raises(lane.LaneError, match="YYYY-MM-DD"):
        lane.validate_manifest(manifest(date="today"), ROOT)
    m = manifest(date=plan.PROMPT_DATE)
    docker = FakeDocker({})
    make_lane(tmp_path, m, docker).run()
    out = Path(next(v.split(":")[0] for v in docker.episodes[0] if v.endswith(":/out")))
    assert json.loads((out / "config.json").read_text())["date"] == "2026-10-08"


def test_setup_check_v2_probes_the_postconfig_and_runs_the_diagnostics(tmp_path):
    """G0 item 5's second pass: the postconfig probe and the registered diagnostics reach the
    episode config of a setup-check slot, and no other purpose may ask for the probe."""
    from harness.q2_stage1 import plan

    m = json.loads((ROOT / "experiments/manifests/q2-stage1/setup-check-v2.json").read_text())
    assert lane.validate_manifest(m, ROOT)["postconfig_probe"] is True
    assert lane.check_slurm(m, host_load_cpus=8)["cpus"] == 8
    assert len(m["slots"]) == 148 and "requeue" not in m  # a failed slot is re-queued once
    vscode = next(s for s in m["slots"] if s["task_id"].startswith("53ad5833"))
    small = {**m, "slots": [vscode, m["slots"][0]]}
    docker = FakeDocker({})
    the_lane = make_lane(tmp_path, small, docker)
    the_lane.run()
    outs = [Path(next(v.split(":")[0] for v in argv if v.endswith(":/out"))) for argv in
            docker.episodes]  # fmt: skip
    configs = [json.loads((out / "config.json").read_text()) for out in outs]
    assert all(c["postconfig_probe"] is True and c["mode"] == "setup-only" for c in configs)
    expected = [dict(d) for d in plan.SETUP_DIAGNOSTICS[vscode["task_id"]]]
    assert configs[0]["diagnostics"] == expected
    assert configs[1]["diagnostics"] == []
    with pytest.raises(lane.LaneError, match="postconfig_probe belongs to a setup check"):
        lane.validate_manifest(manifest(postconfig_probe=True), ROOT)


def test_a_gpu_device_in_an_episode_container_stops_the_lane(tmp_path):
    class GpuDocker(FakeDocker):
        def run_episode(self, argv, name, timeout, stop, log):
            rc = super().run_episode(argv, name, timeout, stop, log)
            out = Path(next(v.split(":")[0] for v in argv if v.endswith(":/out")))
            record = json.loads((out / "episode.json").read_text())
            record.update(status="infrastructure", infrastructure_type="runner_crash",
                          score=None, gpu_devices=["/dev/nvidia0"])  # fmt: skip
            (out / "episode.json").write_text(json.dumps(record))
            return rc

    docker = GpuDocker({})
    slots = [slot(i, DEV[i]) for i in range(3)]
    receipt = make_lane(tmp_path, manifest(slots=slots), docker).run()
    assert "D12" in receipt["error"] and len(docker.episodes) == 1


# --------------------------------------------------------------------------- the GPU half


def test_parse_scontrol_reads_start_and_limit():
    text = (
        "JobId=1234 JobName=q2s1a-a0a JobState=RUNNING Reason=None TimeLimit=01:51:00 "
        "SubmitTime=2026-10-08T20:00:00 StartTime=2026-10-08T21:30:00 EndTime=Unknown"
    )
    info = lane.parse_scontrol(text)
    assert info["state"] == "RUNNING" and info["time_limit_min"] == 111
    assert info["start_time"] == "2026-10-08T21:30:00" and isinstance(info["start_epoch"], float)
    done = lane.parse_scontrol(
        "JobId=1 JobState=COMPLETED StartTime=2026-10-08T21:30:00 "
        "EndTime=2026-10-08T23:21:00 TimeLimit=01:51:00"
    )
    assert done["end_epoch"] - done["start_epoch"] == 111 * 60
    for value, minutes in (("25", 25), ("00:25:00", 25), ("1-00:00:00", 1440), ("25:30", 26),
                           ("2-03", 51 * 60), ("UNLIMITED", None)):  # fmt: skip
        assert lane.parse_time_limit(value) == minutes, value
    assert lane.parse_scontrol("JobId=1 StartTime=Unknown")["start_epoch"] is None


def registered_lane(tmp_path, *, argv_size="9B", limit=25, start=5000.0):
    """An A0a lane whose GPU job's bridge is up: ready.json carries the engine argv of
    ``argv_size``; scontrol reports ``limit`` minutes and the Slurm ``start``."""
    from harness.q2_stage1 import plan

    bridge = tmp_path / "gpu" / "77" / "bridge"
    bridge.mkdir(parents=True)
    argv = plan.engine_argv(plan.MODEL_DIRS[argv_size], plan.SERVED_NAME)
    (bridge / "ready.json").write_text(json.dumps({"engine_argv": argv, "t_start": start + 40,
                                                   "t_ready": start + 200}))  # fmt: skip
    (tmp_path / "gpu_job_id").write_text("77\n")
    m = manifest(purpose="a0a", episode_image_id=lane.EPISODE_IMAGE_ID,
                 engine={"kind": "bridge", "gpu_cap_min": 25,
                         "bridge_dir": str(tmp_path / "gpu" / "{gpu_job_id}" / "bridge"),
                         "gpu_job_id_file": str(tmp_path / "gpu_job_id")})  # fmt: skip
    cfg = lane.LaneConfig(m, "999", tmp_path / "run", ROOT)
    cfg.run_dir.mkdir()
    calls = []

    def slurm(job_id):
        calls.append(job_id)
        if (tmp_path / "gpu" / "77" / "bridge" / "vm.done").exists():  # the job has ended
            return {"state": "COMPLETED", "time_limit_min": limit, "start_epoch": start,
                    "end_epoch": start + 900}  # fmt: skip
        return {"state": "RUNNING", "time_limit_min": limit, "start_epoch": start}

    docker = FakeDocker({})
    return lane.Lane(cfg, docker=docker, certified=["Return"], slurm_job=slurm,
                     clock=lambda: start + 300), docker, calls  # fmt: skip


def test_registered_job_dispatches_only_against_the_registered_engine(tmp_path):
    the_lane, docker, calls = registered_lane(tmp_path / "ok")
    receipt = the_lane.run()
    assert "error" not in receipt and calls == ["77", "77"] and docker.episodes
    # After vm.done the lane records the GPU job's end (accounting is off on the host).
    assert receipt["gpu_job_end"]["state"] == "COMPLETED"
    assert receipt["gpu_job_end"]["end_epoch"] == 5900.0 and receipt["bridge_dir"].endswith(
        "bridge"
    )
    # USR1 comes 180 s before the GPU job's limit, counted from its Slurm start.
    assert receipt["usr1_epoch"] == 5000.0 + 25 * 60 - 180
    assert receipt["gpu_job"]["start_epoch"] == 5000.0 and receipt["first_dispatch"] == 5300.0
    wrong_model, docker, _ = registered_lane(tmp_path / "4b", argv_size="4B")
    receipt = wrong_model.run()
    assert "not the registered 9B argv" in receipt["error"] and not docker.episodes
    wrong_cap, docker, _ = registered_lane(tmp_path / "cap", limit=30)
    receipt = wrong_cap.run()
    assert "time limit is 30 minutes, not its cap of 25" in receipt["error"]
    assert not docker.episodes and receipt["statuses"] == {"cap_truncated": 1}
    assert (tmp_path / "cap" / "gpu" / "77" / "bridge" / "vm.done").exists()  # engine stopped


def test_a_gpu_job_that_has_not_ended_leaves_no_end_time(tmp_path):
    """A running job's scontrol EndTime is its projected limit; the lane does not record it
    as an end (the bridge's stop time then stands in, section 9 item 10)."""
    the_lane, _, _ = registered_lane(tmp_path)
    the_lane.gpu_job_id = "77"
    the_lane.slurm_job = lambda job: {"state": "RUNNING", "start_epoch": 1.0, "end_epoch": 9.0}
    out = the_lane.wait_gpu_end(wait_s=0.0, poll_s=0.0)
    assert out["error"] == "no final state" and "end_epoch" not in out
