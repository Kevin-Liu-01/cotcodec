"""The K2 lane: manifest rules before and after the freeze, the run loop and the batch file."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

from harness.q2_mutation_k2 import lane
from harness.q2_stage1 import lane as s1a

ROOT = Path(__file__).resolve().parents[1]
DEV_SAMPLE = ROOT / "program/evidence/2026-10-11/q2-mutation-k2/dev-inputs/k2-sample.jsonl"
BATCH = ROOT / lane.BATCH
RUN_ROOT = "/home/kevin/cotcodec-runs/"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def base(purpose: str = "development", run: str = "dev-mutants-v9", v: int = 2) -> dict:
    return {
        "schema": lane.SCHEMA,
        "experiment_id": lane.EXPERIMENT_ID,
        "purpose": purpose,
        "name": "k2-test",
        "mode": lane.MODE,
        "engine": {"kind": "none"},
        "run_root": RUN_ROOT + "stage0/q2-mutation-k2/runs",
        "vm": {
            **lane.VM_PINS,
            "qcow2": {
                "host_path": RUN_ROOT + "vm/Ubuntu.qcow2",
                "sha256": lane.QCOW2_SHA256,
                "size_bytes": lane.QCOW2_BYTES,
            },
            "guest_ip": "20.20.20.21",
            "hmp_port": 7100,
            "concurrency": v,
        },
        "episode_image_id": lane.EPISODE_IMAGE_ID,
        "episode_python": "/opt/venv-lock/bin/python",
        "osworld": {"host_dir": RUN_ROOT + "inputs/OSWorld", "commit": lane.OSWORLD_COMMIT},
        "file_cache": {"host_dir": RUN_ROOT + "inputs/file_cache_1e112283/files"},
        "candidates": {
            "host_dir": RUN_ROOT + f"stage0/q2-evaluator-mutation/runs/{run}/build/files",
            "run": run,
        },
        "slurm": {"cpus": 4 * v + 2, "memory_gb": 7 * v + 6, "minutes": 60},
    }


def pair_files(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "/home/user/X.xlsx": {
            "root": "candidates",
            "rel": f"{row['mutant_id']}/home/user/X.xlsx",
            "sha256": row["candidate_sha256"],
        }
    }


def dev_manifest(n: int = 2, **kw: Any) -> dict[str, Any]:
    rows = read_jsonl(DEV_SAMPLE)[:n]
    pairs = [
        {"set": "k2", "pair": i, **lane._identity(r), "files": pair_files(r)}
        for i, r in enumerate(rows)
    ]
    return {**base(**kw), "slots": lane.expand_runs(pairs)}


def test_a_dev_manifest_validates_and_runs_each_pair_twice_in_two_blocks() -> None:
    m = lane.validate_manifest(dev_manifest(3), ROOT)
    assert [s["slot"] for s in m["slots"]] == [
        "k2:000:r1",
        "k2:001:r1",
        "k2:002:r1",
        "k2:000:r2",
        "k2:001:r2",
        "k2:002:r2",
    ]
    assert [s["block"] for s in m["slots"]] == ["k2-r1"] * 3 + ["k2-r2"] * 3


def mutate(m: dict[str, Any], path: str, value: Any) -> dict[str, Any]:
    out = json.loads(json.dumps(m))
    node = out
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[int(key)] if key.isdigit() else node[key]
    if value is KeyError:
        del node[keys[-1]]
    else:
        node[keys[-1]] = value
    return out


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        ("purpose", "k2", "only after the addendum is frozen"),
        ("vm.concurrency", 33, "1-32"),
        ("vm.image_id", "sha256:" + "0" * 64, "action-path v2"),
        ("vm.qcow2.sha256", "0" * 64, "pinned guest disk"),
        ("episode_image_id", "sha256:" + "1" * 64, "metric image"),
        ("engine", {"kind": "fake"}, "no engine"),
        ("candidates.run", "confirm-mutants-v1", "named mutation run"),
        ("runs_per_pair", 3, "runs_per_pair"),
        ("slots.0.block", "k2-r2", "block must be <set>-r<run>"),
        ("slots.0.task_id", "550ce7e7-747b-495f-b122-acdc4d0b8e54", "not a dev task"),
        ("slots.0.files./home/user/X.xlsx.rel", "other/home/user/X.xlsx", "outside its mutant"),
        ("slots.0.files./home/user/X.xlsx.rel", "../x", "unsafe rel"),
        ("slots.0.candidate_sha256", "e" * 64, "carries candidate_sha256"),
    ],
)
def test_manifest_refusals(path: str, value: Any, message: str) -> None:
    m = dev_manifest()
    if path.startswith("slots.0.files./home/user/X.xlsx."):
        bad = json.loads(json.dumps(m))
        bad["slots"][0]["files"]["/home/user/X.xlsx"][path.rsplit(".", 1)[1]] = value
    else:
        bad = mutate(m, path, value)
    with pytest.raises(lane.LaneError, match=message):
        lane.validate_manifest(bad, ROOT)


def test_a_confirm_mutation_run_cannot_be_named_development() -> None:
    m = dev_manifest(run="confirm-mutants-v1")
    with pytest.raises(lane.LaneError, match="dev-split mutation run"):
        lane.validate_manifest(m, ROOT)


def test_context_files_must_match_the_file_cache_receipts() -> None:
    m = dev_manifest(1)
    rel, digest = next(iter(lane.file_cache_receipts(ROOT).items()))
    for slot in m["slots"]:
        slot["files"]["/home/user/ctx.bin"] = {"root": "file_cache", "rel": rel, "sha256": digest}
    lane.validate_manifest(m, ROOT)
    m["slots"][0]["files"]["/home/user/ctx.bin"]["sha256"] = "0" * 64
    with pytest.raises(lane.LaneError, match="file cache receipts"):
        lane.validate_manifest(m, ROOT)


def frozen_tree(tmp_path: Path, *, k2c_sha: str | None = None) -> Path:
    """A source tree holding what the lane reads, with this addendum frozen in a scratch ledger."""
    src = tmp_path / "src"
    for rel in (lane.SPLITS, lane.FILE_CACHE_RECEIPTS, lane.REGISTERED_SAMPLE, lane.REGISTERED_K2C):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, src / rel)
    registration = src / lane.REGISTRATION
    registration.parent.mkdir(parents=True, exist_ok=True)
    digest = k2c_sha or lane.sha256_file(ROOT / lane.REGISTERED_K2C)
    registration.write_text(f"# test registration\n\nK2-C list SHA-256: `{digest}`\n")
    sys.path.insert(0, str(ROOT / "scripts"))
    import preregister

    preregister.freeze(registration, lane.EXPERIMENT_ID, ledger=src / lane.LEDGER, root=src)
    return src


def registered_manifest(src: Path) -> dict[str, Any]:
    """The committed base manifest of the registered job with the registered slots."""
    pairs = [{**p, "files": pair_files(p)} for p in lane.registered_pairs(src)]
    m = json.loads(
        (ROOT / "experiments/manifests/q2-mutation-k2/k2-confirm-v1.base.json").read_text()
    )
    return {**m, "slots": lane.expand_runs(pairs)}


def test_after_the_freeze_only_the_registered_k2_job_runs(tmp_path: Path) -> None:
    src = frozen_tree(tmp_path)
    m = registered_manifest(src)
    checked = lane.validate_manifest(m, src)
    assert len(checked["slots"]) == 2 * (80 + 41)
    order = [s["slot"] for s in checked["slots"]]
    assert order[0] == "k2:000:r1" and order[80] == "k2:000:r2"
    assert order[160] == "k2c:000:r1" and order[201] == "k2c:000:r2"
    with pytest.raises(lane.LaneError, match="only the registered k2 job"):
        lane.validate_manifest(dev_manifest(), src)
    swapped = json.loads(json.dumps(m))
    swapped["slots"][0], swapped["slots"][1] = swapped["slots"][1], swapped["slots"][0]
    with pytest.raises(lane.LaneError):
        lane.validate_manifest(swapped, src)
    short = {**m, "slots": m["slots"][:-1]}
    with pytest.raises(lane.LaneError, match="registered slots"):
        lane.validate_manifest(short, src)
    with pytest.raises(lane.LaneError, match="fixed"):
        lane.validate_manifest({**m, "episode_timeout_s": 1200}, src)
    with pytest.raises(lane.LaneError, match="V = 8"):
        lane.validate_manifest(mutate(m, "vm.concurrency", 4), src)
    with pytest.raises(lane.LaneError, match="Slurm request"):
        lane.validate_manifest(mutate(m, "slurm.minutes", 30), src)
    lane.check_slurm(m)
    (src / lane.REGISTRATION).write_text("edited after the freeze\n")
    with pytest.raises(lane.LaneError, match="changed after the freeze"):
        lane.validate_manifest(m, src)


def test_a_k2c_list_other_than_the_registered_one_is_refused(tmp_path: Path) -> None:
    src = frozen_tree(tmp_path, k2c_sha="0" * 64)
    with pytest.raises(lane.LaneError, match="K2-C list"):
        lane.registered_pairs(src)


def test_map_files_and_render_hash_every_candidate_file(tmp_path: Path) -> None:
    build, cache = tmp_path / "build", tmp_path / "cache"
    (build / "m1/home/user").mkdir(parents=True)
    (build / "m1/home/user/X.xlsx").write_bytes(b"mutant")
    (cache / "calc/t").mkdir(parents=True)
    (cache / "calc/t/X.csv").write_bytes(b"gold")
    target = lane.sha256_file(build / "m1/home/user/X.xlsx")
    job = {
        "job_id": "m1",
        "candidate_sha256": target,
        "files": {
            "/home/user/X.xlsx": "/out/files/m1/home/user/X.xlsx",
            "/home/user/X.csv": "/inputs/file_cache_1e112283/files/calc/t/X.csv",
        },
    }
    pair = {
        "set": "k2",
        "pair": 0,
        "job_id": "m1",
        "mutant_id": "m1",
        "task_id": "t",
        "kind": "mutant",
        "candidate_sha256": target,
    }
    slots = lane.render_slots(
        [pair],
        {"m1": job},
        roots={"candidates": "/out/files", "file_cache": "/inputs/file_cache_1e112283/files"},
        host_roots={"candidates": build, "file_cache": cache},
    )
    assert len(slots) == 2
    files = slots[0]["files"]
    assert files["/home/user/X.xlsx"] == {
        "root": "candidates",
        "rel": "m1/home/user/X.xlsx",
        "sha256": target,
    }
    assert files["/home/user/X.csv"]["root"] == "file_cache"
    assert lane.container_path(files["/home/user/X.csv"]) == "/inputs/file_cache/files/calc/t/X.csv"
    with pytest.raises(lane.LaneError, match="candidate_sha256 differs"):
        lane.render_slots(
            [{**pair, "candidate_sha256": "0" * 64}],
            {"m1": job},
            roots={"candidates": "/out/files"},
            host_roots={"candidates": build},
        )


class FakeDocker:
    def __init__(self, outcomes: list[str]):
        self.outcomes = list(outcomes)
        self.vms: list[list[str]] = []
        self.episodes: list[list[str]] = []
        self.removed: list[str] = []

    def start_vm(self, argv: list[str]) -> None:
        self.vms.append(argv)

    def run_episode(self, argv, name, timeout, stop, log):
        self.episodes.append(argv)
        out = Path(next(v.split(":")[0] for v in argv if v.endswith(":/out")))
        config = json.loads((out / "config.json").read_text())
        outcome = self.outcomes.pop(0) if self.outcomes else "scored"
        if outcome == "crash":
            return 1
        record = {
            "schema": lane.RUN_SCHEMA,
            "set": config["set"],
            "pair": config["pair"],
            "run": config["run"],
            "attempt": config["attempt"],
            "slot": config["slot"],
            "purpose": config["purpose"],
            "candidate_sha256": config["candidate_sha256"],
            "status": outcome,
            "verdict": "pass" if outcome == "scored" else None,
            "exclusion": None if outcome == "scored" else "vm_infrastructure_failure",
        }
        (out / "k2-run.json").write_text(json.dumps(record))
        return 0

    def remove(self, name: str) -> dict[str, Any]:
        self.removed.append(name)
        return {"container_gone": True}


def test_the_k2_lane_dispatches_requeues_once_and_records(tmp_path: Path) -> None:
    m = lane.validate_manifest(dev_manifest(2, v=1), ROOT)
    src = tmp_path / "src"
    src.mkdir()
    (src / ".git_sha").write_text("b" * 40 + "\n")
    (src / "harness").mkdir()
    (src / "harness" / "x.py").write_text("x = 1\n")
    docker = FakeDocker(["crash", "scored", "scored", "scored", "infrastructure", "infrastructure"])
    k2 = lane.K2Lane(
        s1a.LaneConfig(m, "4242", tmp_path / "run", src),
        docker=docker,
        snapshot=lambda job: {"t": 0},
    )
    receipt = k2.run()
    records = read_jsonl(tmp_path / "run" / "k2-runs.jsonl")
    slots = [(r["slot"], r["attempt"], r["status"]) for r in records]
    assert ("k2:000:r1", 1, "infrastructure") in slots  # the crash, recorded by the lane
    assert ("k2:000:r1", 2, "scored") in slots  # its re-queue
    assert len(records) == 6 and len(docker.vms) == 6 and len(docker.removed) == 6
    # The second loss of a slot is not re-queued again.
    assert sum(1 for s in slots if s[0] == "k2:001:r2") == 2
    saved = json.loads((tmp_path / "run" / "lane-receipt.json").read_text())
    assert saved["schema"] == "q2m-k2-lane-receipt-v1"
    assert saved["identity"]["executor_commit"] == "b" * 40
    assert saved["identity"]["vm_image_id"] == lane.VM_PINS["image_id"]
    assert receipt["records"] == 6
    argv = docker.episodes[0]
    assert "--gpus" not in argv and "--privileged" not in argv
    assert argv[argv.index("--network") + 1].startswith("container:")
    mounts = [argv[i + 1] for i, a in enumerate(argv) if a == "--volume"]
    assert all(v.endswith(":ro") for v in mounts if not v.endswith(":/out"))
    assert any(v.endswith(":/inputs/candidates:ro") for v in mounts)
    assert argv[-4:] == ["-m", "harness.q2_mutation_k2.executor", "--config", "/out/config.json"]
    vm_argv = docker.vms[0]
    assert "cotcodec.campaign=q2mk2-k2-test" in vm_argv
    config = json.loads(
        next((tmp_path / "run" / "runs").glob("k2_000_r1.a1/config.json")).read_text()
    )
    assert config["files"]["/home/user/X.xlsx"]["local"].startswith("/inputs/candidates/")
    assert config["settle_after_reset_s"] == 60 and config["settle_before_eval_s"] == 20


def test_slurm_request_bounds() -> None:
    m = dev_manifest(v=2)
    assert lane.check_slurm(m) == {"cpus": 10, "memory_gb": 20, "minutes": 60}
    with pytest.raises(lane.LaneError, match="slurm.cpus"):
        lane.check_slurm(mutate(m, "slurm.cpus", 8))
    with pytest.raises(lane.LaneError, match="memory"):
        lane.check_slurm(mutate(m, "slurm.memory_gb", 12))


def test_the_batch_file_is_cpu_only_and_runs_the_k2_lane() -> None:
    text = BATCH.read_text()
    assert "--gres" not in text.replace("no --gres line", "")
    assert "python3 -E -s -m harness.q2_mutation_k2.lane run" in text
    for guard in (
        "COTCODEC_BATCH_SHA256",
        "COTCODEC_K2_MANIFEST_SHA256",
        "COTCODEC_SOURCE_TREE_SHA256",
        "gres/gpu",
        "DefaultRuntime",
        "label=cotcodec.slurm_job=",
    ):
        assert guard in text
    assert "/home/kevin/cotcodec-runs/stage0/q2-mutation-k2/slurm/" in text
    s1a_text = (ROOT / "infra/slurm/host-single-node/s1a-vm.sbatch").read_text()
    # The same guard block as the S1a batch file, with K2's names.
    core = s1a_text[s1a_text.index("fail() {") : s1a_text.index('cd "${source_dir}"')]
    core = core.replace("s1a-vm", "q2m-k2-vm").replace("S1a VM jobs", "K2 VM jobs")
    core = core.replace("COTCODEC_S1A_", "COTCODEC_K2_")
    assert core in text
