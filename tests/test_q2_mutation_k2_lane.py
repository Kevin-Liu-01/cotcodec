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


def draft_tree(tmp_path: Path) -> Path:
    """A source tree holding what the lane reads for a development job (the splits and the
    file cache receipts) and no ledger: the addendum as a draft. Development manifests are
    validated here, never against the repository's tree, so this suite passes on the freeze
    commit too, where the repository's tree refuses every development job (S1a's V-B1)."""
    src = tmp_path / "draft"
    for rel in (lane.SPLITS, lane.FILE_CACHE_RECEIPTS):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, src / rel)
    assert lane.ledger_row(src) is None
    return src


def test_the_repositorys_tree_admits_development_only_until_the_freeze() -> None:
    """Before the freeze the repository's tree admits a development job and refuses k2; once
    its ledger holds this addendum's row it refuses every development job."""
    m = dev_manifest()
    if lane.ledger_row(ROOT) is None:
        lane.validate_manifest(m, ROOT)
        with pytest.raises(lane.LaneError, match="only after the addendum is frozen"):
            lane.validate_manifest(mutate(m, "purpose", "k2"), ROOT)
    else:
        lane.frozen_registration(ROOT)
        with pytest.raises(lane.LaneError, match="only the registered k2 job"):
            lane.validate_manifest(m, ROOT)


def test_a_dev_manifest_validates_and_runs_each_pair_twice_in_two_blocks(tmp_path: Path) -> None:
    m = lane.validate_manifest(dev_manifest(3), draft_tree(tmp_path))
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
def test_manifest_refusals(tmp_path: Path, path: str, value: Any, message: str) -> None:
    m = dev_manifest()
    if path.startswith("slots.0.files./home/user/X.xlsx."):
        bad = json.loads(json.dumps(m))
        bad["slots"][0]["files"]["/home/user/X.xlsx"][path.rsplit(".", 1)[1]] = value
    else:
        bad = mutate(m, path, value)
    with pytest.raises(lane.LaneError, match=message):
        lane.validate_manifest(bad, draft_tree(tmp_path))


def test_a_confirm_mutation_run_cannot_be_named_development(tmp_path: Path) -> None:
    m = dev_manifest(run="confirm-mutants-v1")
    with pytest.raises(lane.LaneError, match="dev-split mutation run"):
        lane.validate_manifest(m, draft_tree(tmp_path))


def test_context_files_must_match_the_file_cache_receipts(tmp_path: Path) -> None:
    src = draft_tree(tmp_path)
    m = dev_manifest(1)
    rel, digest = next(iter(lane.file_cache_receipts(src).items()))
    for slot in m["slots"]:
        slot["files"]["/home/user/ctx.bin"] = {"root": "file_cache", "rel": rel, "sha256": digest}
    lane.validate_manifest(m, src)
    m["slots"][0]["files"]["/home/user/ctx.bin"]["sha256"] = "0" * 64
    with pytest.raises(lane.LaneError, match="file cache receipts"):
        lane.validate_manifest(m, src)


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
    """The committed base manifest of the registered job with the registered slots, as
    ``lane render`` writes it (with the pinned job list's digest)."""
    pairs = [{**p, "files": pair_files(p)} for p in lane.registered_pairs(src)]
    m = json.loads(
        (ROOT / "experiments/manifests/q2-mutation-k2/k2-confirm-v1.base.json").read_text()
    )
    return {**m, "jobs_sha256": lane.REGISTERED_JOBS_SHA256, "slots": lane.expand_runs(pairs)}


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
    with pytest.raises(lane.LaneError, match="jobs_sha256"):
        lane.validate_manifest({k: v for k, v in m.items() if k != "jobs_sha256"}, src)
    with pytest.raises(lane.LaneError, match="jobs_sha256"):
        lane.validate_manifest({**m, "jobs_sha256": "0" * 64}, src)
    # The run root is the registered one, so the one-job guard sees every k2 job: another
    # directory under the host's run root would pass the generic check and hide an earlier job.
    assert m["run_root"] == lane.REGISTERED_RUN_ROOT
    for other in (RUN_ROOT + "stage0/q2-mutation-k2/runs-2", RUN_ROOT + "elsewhere"):
        with pytest.raises(lane.LaneError, match="run root"):
            lane.validate_manifest({**m, "run_root": other}, src)
    lane.check_slurm(m)
    (src / lane.REGISTRATION).write_text("edited after the freeze\n")
    with pytest.raises(lane.LaneError, match="changed after the freeze"):
        lane.validate_manifest(m, src)


def test_the_k2_job_runs_from_the_freeze_commit_never_its_parent(tmp_path: Path) -> None:
    """The freeze commit's tree holds the ledger row; its parent's (git_head_at_freeze) does
    not, so an export of the parent is refused (S1a section 1's convention)."""
    parent_tree = frozen_tree(tmp_path)
    m = registered_manifest(parent_tree)
    lane.validate_manifest(m, parent_tree)  # the freeze commit's tree: row present
    (parent_tree / lane.LEDGER).unlink()  # git_head_at_freeze's tree: no row
    with pytest.raises(lane.LaneError, match="only after the addendum is frozen"):
        lane.validate_manifest(m, parent_tree)


def test_the_receipt_identity_names_the_exports_freeze(tmp_path: Path) -> None:
    src = frozen_tree(tmp_path)
    (src / ".git_sha").write_text("c" * 40 + "\n")
    (src / "harness").mkdir()
    (src / "harness" / "x.py").write_text("x = 1\n")
    row = lane.ledger_row(src)
    assert row is not None
    ident = lane.identity(src, registered_manifest(src))
    assert ident["executor_commit"] == "c" * 40
    assert ident["git_head_at_freeze"] == row["git_head_at_freeze"]
    assert ident["ledger_row_hash"] == row["hash"]
    assert ident["registration_sha256"] == row["sha256"]
    (src / lane.LEDGER).unlink()
    dev = lane.identity(src, registered_manifest(src))
    assert dev["git_head_at_freeze"] is None and dev["ledger_row_hash"] is None


def write_run(run_root: Path, name: str, purpose: str, **extra: Any) -> Path:
    run_dir = run_root / name
    run_dir.mkdir(parents=True)
    manifest = {"experiment_id": lane.EXPERIMENT_ID, "purpose": purpose}
    (run_dir / "manifest.json").write_text(json.dumps(manifest))
    for file_name, text in extra.items():
        (run_dir / file_name).write_text(text)
    return run_dir


def test_one_k2_job_prior_runs_are_found_and_refused(tmp_path: Path) -> None:
    run_root = tmp_path / "runs"
    write_run(run_root, "1130", "development")
    assert lane.prior_k2_runs(run_root) == []
    lane.check_one_job({"purpose": "k2", "run_root": str(run_root)})
    first = write_run(run_root, "1200", "k2")
    assert lane.prior_k2_runs(run_root) == ["1200"]
    assert lane.prior_k2_runs(run_root, exclude=first) == []
    with pytest.raises(lane.LaneError, match="already ran"):
        lane.check_one_job({"purpose": "k2", "run_root": str(run_root)})
    lane.check_one_job({"purpose": "development", "run_root": str(run_root)})
    write_run(run_root, "1201", "k2", **{lane.REFUSED: "{}"})
    assert lane.prior_k2_runs(run_root) == ["1200"]  # a refused run started no VM
    (run_root / "1202").mkdir()
    (run_root / "1202" / "lane-receipt.json").write_text("{not json")
    assert lane.prior_k2_runs(run_root) == ["1200", "1202"]  # unreadable: fail closed


def test_submit_and_run_refuse_a_second_k2_job(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = frozen_tree(tmp_path)
    host_root = tmp_path / "host"
    monkeypatch.setattr(lane, "RUN_ROOT", str(host_root))
    monkeypatch.setattr(
        lane,
        "REGISTERED_RUN_ROOT",
        lane.REGISTERED_RUN_ROOT.replace(RUN_ROOT.rstrip("/"), str(host_root)),
    )
    text = json.dumps(registered_manifest(src)).replace(RUN_ROOT.rstrip("/"), str(host_root))
    manifest = tmp_path / "k2.json"
    manifest.write_text(text)
    run_root = Path(json.loads(text)["run_root"])
    write_run(run_root, "1200", "k2")
    with pytest.raises(lane.LaneError, match="already ran"):
        lane.submit(manifest, src, dry_run=True)
    second = write_run(run_root, "1201", "k2")
    argv = ["run", "--manifest", str(manifest), "--run-dir", str(second)]
    with pytest.raises(SystemExit, match="refused"):
        lane.main([*argv, "--source-dir", str(src), "--job-id", "1201"])
    assert (second / lane.REFUSED).is_file()
    assert lane.prior_k2_runs(run_root) == ["1200"]


def test_render_maps_slots_only_from_the_sampled_job_list(tmp_path: Path) -> None:
    sample = tmp_path / "k2-sample.jsonl"
    sample.write_text('{"job_id": "m1"}\n')
    jobs = tmp_path / "scoring-jobs.jsonl"
    jobs.write_text('{"job_id": "m1"}\n')
    digests = {"sample_sha256": lane.sha256_file(sample), "jobs_sha256": lane.sha256_file(jobs)}
    summary = tmp_path / "k2-sample.summary.json"
    summary.write_text(json.dumps(digests))
    assert lane.check_job_list("development", sample, jobs, summary) == digests
    with pytest.raises(lane.LaneError, match="--sample-summary"):
        lane.check_job_list("development", sample, jobs, None)
    other = tmp_path / "other-jobs.jsonl"
    other.write_text('{"job_id": "m2"}\n')
    with pytest.raises(lane.LaneError, match="jobs_sha256 differs"):
        lane.check_job_list("development", sample, other, summary)
    with pytest.raises(lane.LaneError, match="pinned scoring-jobs.jsonl"):
        lane.check_job_list("k2", ROOT / lane.REGISTERED_SAMPLE, jobs, None)
    registered = json.loads(
        (
            ROOT / "program/evidence/2026-10-08/q2-mutation-confirm/mutants-confirm-v1/score/"
            "k2-sample.summary.json"
        ).read_text()
    )
    assert registered["jobs_sha256"] == lane.REGISTERED_JOBS_SHA256
    assert registered["sample_sha256"] == lane.REGISTERED_SAMPLE_SHA256


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
    m = lane.validate_manifest(dev_manifest(2, v=1), draft_tree(tmp_path))
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
