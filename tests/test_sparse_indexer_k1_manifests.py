from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from scripts import fill_sparse_indexer_k1_manifests as filler
from scripts import preregister
from scripts.compare_sparse_indexer_resume import compare
from scripts.compare_sparse_indexer_resume import main as compare_main
from scripts.submit_docker_research_job import sbatch_argv, validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = sorted((PROJECT_ROOT / "experiments" / "manifests").glob("q3-k1-*.yaml"))
LANE_SBATCH = PROJECT_ROOT / "infra" / "slurm" / "host-single-node" / "docker-research.sbatch"
CONTRACT = yaml.safe_load(
    (PROJECT_ROOT / "experiments" / "architectures"
     / "translation-supervised-sparse-indexer-k1-screen.yaml").read_text(encoding="utf-8"))


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_every_registered_job_has_a_manifest() -> None:
    names = {path.stem for path in MANIFESTS}
    assert names == {"q3-k1-smoke", "q3-k1-headroom-dev", "q3-k1-resume-r0", "q3-k1-resume-r1",
                     "q3-k1-resume-r2", "q3-k1-main", "q3-k1-main-resume", "q3-k1-extension"}


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: p.stem)
def test_manifest_template_is_consistent(path: Path) -> None:
    manifest = load(path)
    command = manifest["command"]
    assert manifest["container_profile"] in {"default", "vllm", "large-cpu-mem"}
    assert manifest["seed_binding"] == {"flag": "--seeds"}
    start = command.index("--seeds") + 1
    assert [int(v) for v in command[start : start + 3]] == manifest["seeds"]
    assert manifest["seeds"] == CONTRACT["statistics"]["seeds"]
    assert command[command.index("--evidence") + 1] == "/inputs/study-artifact.json"
    assert command[command.index("--expected-evidence-sha256") + 1] == "FILL-bundle-sha256"
    assert manifest["study_artifact"]["sha256"] == "FILL-bundle-sha256"
    assert manifest["study_artifact"]["license"] == "LicenseRef-cotcodec-k1-bundle-v1"
    assert manifest["model"]["receipt_sha256"] == CONTRACT["k1_model"]["receipt_sha256"]
    assert command[command.index("--expected-receipt-sha256") + 1] == (
        manifest["model"]["receipt_sha256"])
    assert not any("memory" in part for part in command)
    assert manifest["run_root"].startswith("/home/kevin/cotcodec-runs/")
    if path.stem == "q3-k1-main-resume":  # minutes and budget are measured remainders
        assert manifest["resources"]["minutes"] == "FILL-main-resume-minutes"
        assert manifest["budget"]["max_gpu_hours"] == "FILL-main-resume-gpu-hours"
    else:
        gpu_hours = manifest["resources"]["gpus"] * manifest["resources"]["minutes"] / 60
        assert gpu_hours <= manifest["budget"]["max_gpu_hours"] + 1e-9
    # Fail closed: the unfilled template is not a valid image id.
    assert manifest["image_id"].startswith("FILL-")


def test_registered_budget_matches_the_contract() -> None:
    # The extension is conditional; the main-job continuation spends what is left
    # of the main job's own 2.0 GPU-h cap.
    total = sum(load(p)["budget"]["max_gpu_hours"] for p in MANIFESTS
                if p.stem not in {"q3-k1-extension", "q3-k1-main-resume"})
    assert total <= CONTRACT["execution"]["max_gpu_hours"] + 1e-9
    main = load(PROJECT_ROOT / "experiments/manifests/q3-k1-main.yaml")
    assert main["budget"]["max_gpu_hours"] == 2.0 and main["resources"]["minutes"] == 30


def test_resume_legs_share_the_stop_step_and_r1_holds() -> None:
    legs = {stem: load(PROJECT_ROOT / f"experiments/manifests/{stem}.yaml")["command"]
            for stem in ("q3-k1-resume-r0", "q3-k1-resume-r1", "q3-k1-resume-r2")}
    stops = {stem: argv[argv.index("--stop-after-step") + 1] for stem, argv in legs.items()}
    assert len(set(stops.values())) == 1
    assert "--hold-after-step" in legs["q3-k1-resume-r1"]
    assert "--hold-after-step" not in legs["q3-k1-resume-r0"]
    r2 = load(PROJECT_ROOT / "experiments/manifests/q3-k1-resume-r2.yaml")
    assert r2["resume_subpath"] == "phase-0a-k1/checkpoints"


RESUMED = [("q3-k1-resume-r2", "q3-k1-resume-r1"), ("q3-k1-main-resume", "q3-k1-main"),
           ("q3-k1-extension", "q3-k1-main")]


def lane_resume_copy() -> str:
    """The lane's own resume-copy program, extracted from the batch script."""

    text = LANE_SBATCH.read_text(encoding="utf-8")
    opening = '"${COTCODEC_PREDECESSOR_JOB_ID}" "${COTCODEC_RESUME_SUBPATH}" <<\'PY\'\n'
    start = text.index(opening) + len(opening)
    return text[start : text.index("\nPY\n", start)]


@pytest.mark.parametrize(("successor", "predecessor"), RESUMED)
def test_resumed_leg_shares_its_predecessors_run_root(successor, predecessor) -> None:
    after = load(PROJECT_ROOT / f"experiments/manifests/{successor}.yaml")
    before = load(PROJECT_ROOT / f"experiments/manifests/{predecessor}.yaml")
    assert after["run_root"] == before["run_root"]
    assert after["resume_subpath"] == "phase-0a-k1/checkpoints"
    for field in ("image_id", "git_sha", "source_sha256", "container_profile", "model",
                  "study_artifact", "seeds"):
        assert after[field] == before[field]


@pytest.mark.parametrize(("successor", "predecessor"), RESUMED)
def test_lane_resume_copy_finds_the_predecessor(tmp_path, successor, predecessor) -> None:
    # Review finding: R2 and the extension named another run root, so the lane's
    # copy failed with "predecessor job.env is missing". Run the lane's own code.
    after = load(PROJECT_ROOT / f"experiments/manifests/{successor}.yaml")
    before = load(PROJECT_ROOT / f"experiments/manifests/{predecessor}.yaml")
    env = {"PATH": "/usr/bin:/bin", "COTCODEC_GIT_SHA": "g" * 40,
           "COTCODEC_SOURCE_SHA256": "s" * 64, "COTCODEC_IMAGE_ID": "sha256:" + "i" * 64,
           "COTCODEC_BATCH_SHA256": "b" * 64}
    script = lane_resume_copy()
    keys = [line.strip().strip('",') for line in
            script.split("if separator and key in {", 1)[1].split("}:", 1)[0].splitlines()
            if line.strip()]
    defaults = {"model_kind": "checkpoint", "container_profile": "default",
                "git_sha": env["COTCODEC_GIT_SHA"], "source_sha256": env["COTCODEC_SOURCE_SHA256"],
                "image_id": env["COTCODEC_IMAGE_ID"],
                "batch_script_sha256": env["COTCODEC_BATCH_SHA256"]}
    predecessor_dir = tmp_path / before["run_root"].lstrip("/") / "1001"
    (predecessor_dir / after["resume_subpath"]).mkdir(parents=True)
    (predecessor_dir / after["resume_subpath"] / "lr_freeze.json").write_text("{}")
    (predecessor_dir / "job.env").write_text(
        "".join(f"{key}={defaults.get(key, 'none')}\n" for key in keys))
    run_root = tmp_path / after["run_root"].lstrip("/")
    run_dir = run_root / "1002"
    run_dir.mkdir(parents=True)
    copied = subprocess.run([sys.executable, "-", str(run_root), str(run_dir), "1001",
                             after["resume_subpath"]], input=script, env=env,
                            capture_output=True, text=True, check=False)
    assert copied.returncode == 0, copied.stderr
    assert (run_dir / after["resume_subpath"] / "lr_freeze.json").is_file()
    receipt = json.loads((run_dir / "resume-receipt.json").read_text())
    assert receipt["predecessor_job_id"] == "1001"


def _job(root: Path, job_id: int, name: str, termination: str, *, started: str = "",
         receipt: dict | None = None, env: dict | None = None) -> Path:
    job = root / str(job_id)
    job.mkdir(parents=True)
    started = started or "2026-10-08T10:00:00Z"
    extra = "".join(f"{key}={value}\n" for key, value in (env or {}).items())
    (job / "job.env").write_text(f"job_id={job_id}\nstarted_at={started}\n{extra}")
    (job / "manifest.json").write_text(json.dumps({"name": name}))
    (job / "termination.env").write_text(f"job_id={job_id}\n{termination}")
    if receipt is not None:
        (job / "phase-0a-k1").mkdir()
        (job / "phase-0a-k1" / "receipt.json").write_text(json.dumps(receipt))
    return job


CONFIRMED = ("reason=signal_USR1_checkpoint_confirmed\nexit_code=75\ncheckpoint_ready=true\n"
             "finished_at=2026-10-08T10:12:30Z\n")
DONE = "reason=completed\nexit_code=0\ncheckpoint_ready=false\nfinished_at=2026-10-08T10:20:00Z\n"


def test_filler_picks_predecessors_by_how_they_ended(tmp_path) -> None:
    r1 = tmp_path / "resume-r1-r2"
    _job(r1, 101, "q3-k1-resume-r1", "reason=workload_failed\nexit_code=3\n")
    _job(r1, 102, "q3-k1-resume-r1", CONFIRMED)
    _job(r1, 103, "q3-k1-resume-r2", DONE)
    main = tmp_path / "main"
    _job(main, 201, "q3-k1-main", CONFIRMED)  # used 13 of 30 minutes (12.5 rounded up, + 1)
    values, notes = filler.predecessor_values(r1, main)
    assert values["FILL-resume-r1-job-id"] == "102"
    assert values["FILL-main-checkpointed-job-id"] == "201"
    assert values["FILL-main-resume-minutes"] == "16"
    assert float(values["FILL-main-resume-gpu-hours"]) >= 4 * 16 / 60
    assert "FILL-main-job-id" not in values and not notes
    _job(main, 202, "q3-k1-main-resume", DONE,
         receipt={"verdict": {"verdict": "GO"}, "extension_targets": []})
    values, notes = filler.predecessor_values(r1, main)
    assert "FILL-main-job-id" not in values and any("does not call" in n for n in notes)
    # Program decision D16: a second continuation is declined.
    assert "FILL-main-checkpointed-job-id" not in values
    assert any("second continuation is declined" in n for n in notes)
    eligible = tmp_path / "main-eligible"
    _job(eligible, 301, "q3-k1-main", DONE,
         receipt={"verdict": {"verdict": "INCONCLUSIVE"}, "extension_targets": ["hs"]})
    assert filler.predecessor_values(None, eligible)[0] == {"FILL-main-job-id": "301"}
    # The extension runs once: with an extension job in the run root (however it
    # ended) no second extension is filled.
    _job(eligible, 302, "q3-k1-extension", "reason=workload_failed\nexit_code=3\n")
    values, notes = filler.predecessor_values(None, eligible)
    assert values == {} and "no second extension" in notes[0]
    _job(r1, 104, "q3-k1-resume-r1", CONFIRMED)
    with pytest.raises(filler.FillError, match="2 jobs qualify"):
        filler.predecessor_values(r1, None)


def test_filler_refuses_a_continuation_beyond_the_main_cap(tmp_path) -> None:
    main = tmp_path / "main"
    _job(main, 201, "q3-k1-main", CONFIRMED.replace("10:12:30", "10:27:10"))
    values, notes = filler.predecessor_values(None, main)
    assert "FILL-main-checkpointed-job-id" not in values
    assert "no continuation within the cap" in notes[0]


def _receipt(directory: Path, digests: dict, params: dict, resumed: object) -> None:
    (directory / "phase-0a-k1").mkdir(parents=True)
    payload = {"stop_after_step": 40, "final_state_digests": digests,
               "workers": [{"worker": int(w), "param_digests": params[w],
                            "resumed_from": resumed} for w in params]}
    (directory / "phase-0a-k1" / "receipt.json").write_text(json.dumps(payload))


def test_compare_requires_bitwise_equality_and_a_confirmed_signal(tmp_path) -> None:
    r0, r1, r2 = tmp_path / "r0", tmp_path / "r1", tmp_path / "r2"
    _receipt(r0, {"0": "a", "1": "b"}, {"0": {"L00": "x"}, "1": {"L01": "y"}}, None)
    _receipt(r2, {"0": "a", "1": "b"}, {"0": {"L00": "x"}, "1": {"L01": "y"}}, 25)
    r1.mkdir()
    (r1 / "termination.env").write_text(
        "reason=signal_USR1_checkpoint_confirmed\nexit_code=75\ncheckpoint_ready=true\n")
    (r1 / "checkpoint.ready").write_text(
        "trigger=SIGUSR1\ntoken=t\nacks=" + json.dumps({"0": {"step": 25}, "1": {"step": 25}})
        + "\n")
    assert compare(r0, r1, r2)["equivalent"]
    _receipt(tmp_path / "r3", {"0": "a", "1": "c"}, {"0": {"L00": "x"}, "1": {"L01": "z"}}, 25)
    report = compare(r0, r1, tmp_path / "r3")
    assert not report["equivalent"] and report["mismatched_indexers"] == ["L01"]
    assert compare_main(["--r0", str(r0), "--r1", str(r1), "--r2", str(tmp_path / "r3"),
                         "--output", str(tmp_path / "out.json")]) == 1


CONTRACT_PATH = filler.CONTRACT_PATH
IMAGE = {"image_id": "sha256:" + "a" * 64, "git_sha": "b" * 40, "source_tar_sha256": "c" * 64}


class World:
    """Measured inputs of a filler run: image B, the bundle, a frozen preregistration
    with its identity table, and the gate jobs (smoke, headroom-dev, R0, R1, R2)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.image = root / "image-receipt.json"
        self.image.write_text(json.dumps(IMAGE))
        self.bundle = root / "k1-bundle-v1.json"
        self.bundle.write_bytes(b"{}\n")
        self.bundle_sha = hashlib.sha256(b"{}\n").hexdigest()
        self.sidecar = root / "k1-bundle-v1.json.manifest.json"
        self.sidecar.write_text(json.dumps({"sha256": self.bundle_sha, "size_bytes": 3}))
        self.code = {path: preregister.sha256_file(PROJECT_ROOT / path)
                     for path in filler.SELF_PATHS}
        self.code["harness/sparse_indexer_k1_stats.py"] = "e" * 64
        self.code[CONTRACT_PATH] = "f" * 64
        self.repo = root / "repo"
        self.prereg_sha = self.freeze(self.bundle_sha)
        self.env = {"image_id": IMAGE["image_id"], "git_sha": IMAGE["git_sha"],
                    "source_sha256": IMAGE["source_tar_sha256"],
                    "study_artifact_sha256": self.bundle_sha}

    def freeze(self, stated_bundle: str, code: dict | None = None) -> str:
        prereg = self.repo / "program" / "preregistrations" / f"{filler.EXPERIMENT_ID}.md"
        prereg.parent.mkdir(parents=True, exist_ok=True)
        rows = "".join(f"| {path} | {digest} |\n" for path, digest in (code or self.code).items())
        prereg.write_text(f"# K1\n\n| File | SHA-256 |\n|---|---|\n{rows}\n| Item | Value |\n"
                          f"|---|---|\n| k1-bundle-v1.json SHA-256 | {stated_bundle} |\n")
        ledger = self.repo / "program" / "preregistrations" / "ledger.jsonl"
        ledger.unlink(missing_ok=True)
        preregister.freeze(prereg, filler.EXPERIMENT_ID, ledger=ledger, root=self.repo)
        return preregister.sha256_file(prereg)

    def receipt(self, phase: str, **fields: object) -> dict:
        return {"experiment_id": filler.EXPERIMENT_ID, "phase": phase, "profile": "registered",
                "hashes": {"preregistration_sha256": self.prereg_sha,
                           "bundle_sha256": self.bundle_sha,
                           "contract_sha256": self.code[CONTRACT_PATH],
                           "code": {"harness/sparse_indexer_k1_stats.py":
                                    self.code["harness/sparse_indexer_k1_stats.py"]}},
                **fields}

    def gates(self, *, smoke: dict | None = None, headroom: dict | None = None,
              r2_digest: str = "a", r2_predecessor: str = "502",
              env: dict | None = None) -> None:
        env = {**self.env, **(env or {})}
        _job(self.root / "smoke", 401, "q3-k1-smoke", DONE, env=env, receipt=self.receipt(
            "smoke", **{"status": "SMOKE_PASS", "gates": {"capture_reconstruction": True,
                                                          "selection_budget": True},
                        "projection": {"main_wall_minutes": 20.0}, **(smoke or {})}))
        h2a = {**GATE_INTERVAL, "point": 50.0, "lower": 45.0}
        h2b = {**GATE_INTERVAL, "point": 12.0, "lower": 3.0}
        _job(self.root / "headroom-dev", 411, "q3-k1-headroom-dev", DONE, env=env,
             receipt=self.receipt("headroom-dev", **{
                 "status": "HEADROOM_DEV_COMPLETE", "decision": "PROCEED_TO_K1",
                 "h1_points": 40.0, "h2a": h2a, "h2b": h2b, **(headroom or {})}))
        leg = {"status": "RESUME_TEST_LEG_COMPLETE", "stop_after_step": 40}
        _job(self.root / "resume-r0", 501, "q3-k1-resume-r0", DONE, env=env,
             receipt=self.receipt("resume-test", **leg, final_state_digests={"0": "a"},
                                  workers=[{"worker": 0, "param_digests": {"L00": "x"},
                                            "resumed_from": None}]))
        r1 = _job(self.root / "resume-r1-r2", 502, "q3-k1-resume-r1", CONFIRMED, env=env)
        (r1 / "checkpoint.ready").write_text(
            "trigger=SIGUSR1\ntoken=t\nacks=" + json.dumps({"0": {"step": 25}}) + "\n")
        _job(self.root / "resume-r1-r2", 503, "q3-k1-resume-r2", DONE,
             env={**env, "predecessor_job_id": r2_predecessor},
             receipt=self.receipt("resume-test", **leg, final_state_digests={"0": r2_digest},
                                  workers=[{"worker": 0, "param_digests": {"L00": "x"},
                                            "resumed_from": 25}]))

    def argv(self, output: Path, *extra: str) -> list[str]:
        return ["--image-receipt", str(self.image), "--bundle", str(self.bundle),
                "--bundle-sidecar", str(self.sidecar), "--bundle-commit", "d" * 40,
                "--repo-root", str(self.repo), "--smoke-run-root", str(self.root / "smoke"),
                "--headroom-dev-run-root", str(self.root / "headroom-dev"),
                "--r0-run-root", str(self.root / "resume-r0"),
                "--r1-run-root", str(self.root / "resume-r1-r2"), "--output", str(output),
                *extra]


GATE_INTERVAL = {"point": 0.0, "per_seed": [0.0], "s_seed": 0.0, "se_cluster": 1.0,
                 "se_total": 1.0, "lower": 0.0, "upper": 0.0, "half_width": 1.0,
                 "percentile_lower": 0.0, "percentile_upper": 0.0, "replicates": 10000,
                 "evaluable": True}


def _report(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_filler_uses_only_measured_values(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    out = tmp_path / "filled"
    assert filler.main(world.argv(out)) == 0
    report = _report(capsys)
    assert report["blocked"] == {} and all(g["passed"] for g in report["pre_main_gates"].values())
    main = load(out / "q3-k1-main.yaml")
    assert main["image_id"] == IMAGE["image_id"]
    assert main["study_artifact"]["sha256"] == world.bundle_sha
    assert main["study_artifact"]["size_bytes"] == 3
    argv = main["command"]
    assert argv[argv.index("--expected-preregistration-sha256") + 1] == world.prereg_sha
    assert load(out / "q3-k1-resume-r2.yaml")["resume_from_job_id"] == 502
    # Every filled manifest passes the discovery-lane submitter's validation.
    for path in sorted(out.glob("q3-k1-*.yaml")):
        validated = validate_manifest(load(path))
        assert validated["seed_binding"] == {"flag": "--seeds"}
        assert validated["container_profile"] == "default"
        assert sbatch_argv(validated, test_only=True)[-2] == "--test-only"
    assert not (out / "q3-k1-extension.yaml").exists()  # main job id not yet measured
    assert not (out / "q3-k1-main-resume.yaml").exists()  # no interrupted main job
    # An interrupted main job: its one continuation fills and passes the lane's validation.
    main_root = tmp_path / "main"
    _job(main_root, 201, "q3-k1-main", CONFIRMED)
    later = tmp_path / "filled-later"
    assert filler.main(world.argv(later, "--main-run-root", str(main_root))) == 0
    capsys.readouterr()
    resumed = validate_manifest(load(later / "q3-k1-main-resume.yaml"))
    assert str(resumed["resume_from_job_id"]) == "201" and resumed["minutes"] == 16
    # The continuation completed with a read that calls for the extension: the
    # extension fills, and no second continuation does.
    _job(main_root, 202, "q3-k1-main-resume", DONE,
         receipt={"verdict": {"verdict": "INCONCLUSIVE"}, "extension_targets": ["hs"]})
    last = tmp_path / "filled-last"
    assert filler.main(world.argv(last, "--main-run-root", str(main_root))) == 0
    assert any("second continuation" in note for note in _report(capsys)["notes"])
    extension = validate_manifest(load(last / "q3-k1-extension.yaml"))
    assert str(extension["resume_from_job_id"]) == "202"
    assert not (last / "q3-k1-main-resume.yaml").exists()
    world.sidecar.write_text(json.dumps({"sha256": "0" * 64, "size_bytes": 3}))
    assert filler.main(world.argv(tmp_path / "x")) == 2


GATE_FAILURES = {
    "smoke over budget": (dict(smoke={"status": "SMOKE_PASS_OVER_BUDGET"}), "not SMOKE_PASS"),
    "smoke projection over the limit": (dict(smoke={"projection": {"main_wall_minutes": 23.0}}),
                                        "over 30 min"),
    "a smoke gate false": (dict(smoke={"gates": {"capture_reconstruction": False}}),
                           "not every smoke gate"),
    "headroom escalates": (dict(headroom={"decision": "ESCALATE_OR_STOP"}),
                           "not PROCEED_TO_K1"),
    "headroom numbers fail H2b": (dict(headroom={"h2b": {**GATE_INTERVAL, "point": 3.0,
                                                         "lower": 1.0}}),
                                  "rules do not give PROCEED_TO_K1"),
    "resume not bitwise": (dict(r2_digest="z"), "not equivalent"),
    "R2 resumed another job": (dict(r2_predecessor="999"), "did not resume from R1"),
    "gate jobs on another image": (dict(env={"image_id": "sha256:" + "9" * 64}),
                                   "image_id is not image B's"),
}


@pytest.mark.parametrize("failure", sorted(GATE_FAILURES))
def test_filler_blocks_the_main_read_until_every_pre_main_gate_passes(tmp_path, capsys,
                                                                       failure) -> None:
    # Pre-freeze audit: the pre-step, smoke-budget and resume gates were computed
    # but never enforced; program decision D16 makes the filler enforce them.
    mutation, reason = GATE_FAILURES[failure]
    world = World(tmp_path)
    world.gates(**mutation)
    main_root = tmp_path / "main"
    _job(main_root, 201, "q3-k1-main", CONFIRMED)
    out = tmp_path / "filled"
    assert filler.main(world.argv(out, "--main-run-root", str(main_root))) == 0
    report = _report(capsys)
    assert set(report["blocked"]) == {f"{name}.yaml" for name in filler.MAIN_READ_TEMPLATES}
    assert any(reason in problem for problem in report["blocked"]["q3-k1-main.yaml"])
    assert not (out / "q3-k1-main.yaml").exists()
    assert not (out / "q3-k1-main-resume.yaml").exists()
    assert (out / "q3-k1-smoke.yaml").exists()  # the gate jobs' own manifests still fill


def test_filler_binds_gate_receipts_to_the_registered_identity(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    receipt_path = tmp_path / "headroom-dev" / "411" / "phase-0a-k1" / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["hashes"]["code"]["harness/sparse_indexer_k1_stats.py"] = "1" * 64
    receipt["hashes"]["preregistration_sha256"] = "2" * 64
    receipt["profile"] = "tiny"
    receipt_path.write_text(json.dumps(receipt))
    assert filler.main(world.argv(tmp_path / "filled")) == 0
    problems = _report(capsys)["pre_main_gates"]["headroom_dev"]["problems"]
    for name in ("code digests", "preregistration digest", "profile"):
        assert any(name in problem for problem in problems), problems


def test_filler_blocks_the_main_read_without_the_gate_run_roots(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    argv = world.argv(tmp_path / "filled")
    argv[argv.index("--smoke-run-root"): argv.index("--smoke-run-root") + 2] = []
    assert filler.main(argv) == 0
    report = _report(capsys)
    assert "smoke: no --smoke-run-root was given" in report["blocked"]["q3-k1-main.yaml"]


def test_filler_refuses_a_bundle_or_filler_other_than_the_registered_one(tmp_path) -> None:
    world = World(tmp_path)
    world.gates()
    world.prereg_sha = world.freeze("0" * 64)  # the bundle differs from the stated digest
    assert filler.main(world.argv(tmp_path / "a")) == 2
    world.prereg_sha = world.freeze(world.bundle_sha, {
        **world.code, "scripts/fill_sparse_indexer_k1_manifests.py": "3" * 64})
    assert filler.main(world.argv(tmp_path / "b")) == 2
    world.prereg_sha = world.freeze(world.bundle_sha)
    assert filler.main(world.argv(tmp_path / "c")) == 0
