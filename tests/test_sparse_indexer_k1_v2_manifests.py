"""The K1 successor's manifests, its filler's gates and the probe's manifest (no torch)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from harness import sparse_indexer_k1_budget_v2 as budget
from scripts import derive_sparse_indexer_k1_v2_limits as derive
from scripts import fill_sparse_indexer_k1_probe_manifest as probe_filler
from scripts import fill_sparse_indexer_k1_v2_manifests as filler
from scripts import preregister
from scripts.submit_docker_research_job import sbatch_argv, validate_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = sorted(filler.TEMPLATES.glob("q3-k1-v2-*.yaml"))
CONTRACT = yaml.safe_load((PROJECT_ROOT / filler.CONTRACT_PATH).read_text(encoding="utf-8"))
V1_MANIFESTS = PROJECT_ROOT / "experiments" / "manifests"
JOBS = {"smoke", "headroom-dev", "resume-r0", "resume-r1", "resume-r2", "main", "main-resume",
        "extension"}
BUNDLE_COMMIT = "ec81fe3292d8559251adb273cb4e6ec5b070c162"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_every_registered_job_has_a_v2_template_and_v1_is_untouched() -> None:
    assert {path.stem for path in TEMPLATES} == {f"q3-k1-v2-{job}" for job in JOBS}
    # v1's filler and tests glob experiments/manifests/q3-k1-*.yaml (not recursive).
    assert {p.stem for p in V1_MANIFESTS.glob("q3-k1-*.yaml")} == {f"q3-k1-{job}" for job in JOBS}


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: p.stem)
def test_v2_template_is_consistent(path: Path) -> None:
    manifest = load(path)
    job = path.stem.removeprefix("q3-k1-v2-")
    v1 = load(V1_MANIFESTS / f"q3-k1-{job}.yaml")
    command = manifest["command"]
    assert manifest["name"] == path.stem
    assert command[1] == "scripts/run_sparse_indexer_phase0a_v2.py"
    assert command[2] == filler.CONTRACT_PATH
    assert command[command.index("--preregistration") + 1] == (
        "program/preregistrations/q3-k1-localization-screen-v2.md")
    assert manifest["seed_binding"] == {"flag": "--seeds"}
    start = command.index("--seeds") + 1
    assert [int(v) for v in command[start : start + 3]] == manifest["seeds"] == [42, 43, 44]
    assert manifest["seeds"] == CONTRACT["statistics"]["seeds"]
    assert "/k1-screen-v2/" in manifest["run_root"] and "k1-screen-v1" not in manifest["run_root"]
    assert manifest["image_id"] == "FILL-image-b2-image-id"
    assert manifest["study_artifact"]["sha256"] == "FILL-bundle-sha256"
    assert manifest["study_artifact"]["revision"] == "FILL-bundle-commit-git-sha"
    assert manifest["model"] == v1["model"]
    assert not any("memory" in part for part in command)
    if job == "main-resume":
        assert manifest["resources"]["minutes"] == "FILL-main-resume-minutes"
    else:
        assert manifest["resources"]["minutes"] == f"FILL-limit-{job}-minutes"
        assert manifest["budget"]["max_gpu_hours"] == f"FILL-limit-{job}-gpu-hours"
    # Everything but the names, paths, limits and placeholders is v1's.
    for key in ("container_profile", "randomness_contract", "seeds"):
        assert manifest[key] == v1[key]
    assert manifest["resources"]["gpus"] == v1["resources"]["gpus"]
    v1_tail = v1["command"][3:]
    v2_tail = command[3:]
    assert [a for a in v2_tail if "q3-k1" not in a] == [a for a in v1_tail if "q3-k1" not in a]


@pytest.mark.parametrize(("successor", "predecessor"), [("resume-r2", "resume-r1"),
                                                        ("main-resume", "main"),
                                                        ("extension", "main")])
def test_resumed_legs_share_their_predecessors_run_root(successor, predecessor) -> None:
    after = load(filler.TEMPLATES / f"q3-k1-v2-{successor}.yaml")
    before = load(filler.TEMPLATES / f"q3-k1-v2-{predecessor}.yaml")
    assert after["run_root"] == before["run_root"]
    assert after["resume_subpath"] == "phase-0a-k1/checkpoints"


def test_contract_limits_await_the_probe() -> None:
    assert CONTRACT["execution"]["job_limits"] is None
    assert CONTRACT["throughput_probe"]["receipt_sha256"] is None
    assert CONTRACT["preregistration"]["experiment_id"] == filler.EXPERIMENT_ID


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
IMAGE = {"image_id": "sha256:" + "a" * 64, "git_sha": "b" * 40, "source_tar_sha256": "c" * 64}
GATE_INTERVAL = {"point": 0.0, "per_seed": [0.0], "s_seed": 0.0, "se_cluster": 1.0,
                 "se_total": 1.0, "lower": 0.0, "upper": 0.0, "half_width": 1.0,
                 "percentile_lower": 0.0, "percentile_upper": 0.0, "replicates": 10000,
                 "evaluable": True}
PROBE_RATES = budget.scenario_rates("central")


class World:
    """A frozen v2 registration with its code table, limits, probe receipt and gate jobs."""

    def __init__(self, root: Path, *, rates: budget.Rates = PROBE_RATES) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.image = root / "image-receipt.json"
        self.image.write_text(json.dumps(IMAGE))
        self.bundle = root / "k1-bundle-v1.json"
        self.bundle.write_bytes(b"{}\n")
        self.bundle_sha = hashlib.sha256(b"{}\n").hexdigest()
        self.sidecar = root / "k1-bundle-v1.json.manifest.json"
        self.sidecar.write_text(json.dumps({"sha256": self.bundle_sha, "size_bytes": 3}))
        self.repo = root / "repo"
        self.derived = budget.derive_limits(rates)
        self.limits = budget.limits_table(self.derived)
        self.probe = root / "probe-receipt.json"
        self.write_probe(rates)
        self.write_contract(self.limits)
        self.code = {path: preregister.sha256_file(PROJECT_ROOT / path)
                     for path in filler.SELF_PATHS}
        self.code["harness/sparse_indexer_bank.py"] = "e" * 64
        self.prereg_sha = self.freeze()
        self.env = {"image_id": IMAGE["image_id"], "git_sha": IMAGE["git_sha"],
                    "source_sha256": IMAGE["source_tar_sha256"],
                    "study_artifact_sha256": self.bundle_sha}

    def write_probe(self, rates: budget.Rates, **fields: object) -> None:
        derived = budget.derive_limits(rates)
        payload = {"experiment_id": filler.PROBE_ID, "status": "PROBE_COMPLETE",
                   "profile": "registered", "rates": rates.as_dict(),
                   "derived_limits": derived, "limits_table": budget.limits_table(derived),
                   "hashes": {"code": {"harness/sparse_indexer_bank.py": "e" * 64}}, **fields}
        self.probe.write_text(json.dumps(payload))

    def write_contract(self, limits: dict | None) -> None:
        contract = self.repo / filler.CONTRACT_PATH
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text(yaml.safe_dump({"name": "stand-in",
                                            "execution": {"job_limits": limits}}))

    def freeze(self, *, bundle: str | None = None, commit: str = BUNDLE_COMMIT,
               probe: str | None = None, code: dict | None = None) -> str:
        self.code[filler.CONTRACT_PATH] = preregister.sha256_file(
            self.repo / filler.CONTRACT_PATH)
        prereg = self.repo / "program" / "preregistrations" / f"{filler.EXPERIMENT_ID}.md"
        prereg.parent.mkdir(parents=True, exist_ok=True)
        rows = "".join(f"| {path} | {digest} |\n" for path, digest in (code or self.code).items())
        probe_sha = probe or preregister.sha256_file(self.probe)
        prereg.write_text(
            f"# K1 v2\n\n| File | SHA-256 |\n|---|---|\n{rows}\n| Item | Value |\n|---|---|\n"
            f"| k1-bundle-v1.json SHA-256 | {bundle or self.bundle_sha} |\n"
            f"| k1-bundle-v1.json built at commit | {commit} |\n"
            f"| q3-k1-throughput-probe-v1 receipt SHA-256 | {probe_sha} |\n")
        ledger = self.repo / "program" / "preregistrations" / "ledger.jsonl"
        ledger.unlink(missing_ok=True)
        preregister.freeze(prereg, filler.EXPERIMENT_ID, ledger=ledger, root=self.repo)
        return preregister.sha256_file(prereg)

    def receipt(self, phase: str, **fields: object) -> dict:
        return {"experiment_id": filler.EXPERIMENT_ID, "phase": phase, "profile": "registered",
                "hashes": {"preregistration_sha256": self.prereg_sha,
                           "bundle_sha256": self.bundle_sha,
                           "contract_sha256": self.code[filler.CONTRACT_PATH],
                           "code": {"harness/sparse_indexer_bank.py": "e" * 64}},
                **fields}

    def gates(self, *, smoke: dict | None = None, smoke_rates: budget.Rates | None = None,
              headroom: dict | None = None, r2_digest: str = "a", r2_predecessor: str = "502",
              env: dict | None = None) -> None:
        env = {**self.env, **(env or {})}
        measured = (smoke_rates or PROBE_RATES).as_dict()
        _job(self.root / "smoke", 401, "q3-k1-v2-smoke", DONE, env=env, receipt=self.receipt(
            "smoke", **{"status": "SMOKE_PASS", "gates": {"capture_reconstruction": True,
                                                          "selection_budget": True},
                        "projection": {"rates": measured}, **(smoke or {})}))
        h2a = {**GATE_INTERVAL, "point": 50.0, "lower": 45.0}
        h2b = {**GATE_INTERVAL, "point": 12.0, "lower": 3.0}
        _job(self.root / "headroom-dev", 411, "q3-k1-v2-headroom-dev", DONE, env=env,
             receipt=self.receipt("headroom-dev", **{
                 "status": "HEADROOM_DEV_COMPLETE", "decision": "PROCEED_TO_K1",
                 "h1_points": 40.0, "h2a": h2a, "h2b": h2b, **(headroom or {})}))
        leg = {"status": "RESUME_TEST_LEG_COMPLETE", "stop_after_step": 40}
        _job(self.root / "resume-r0", 501, "q3-k1-v2-resume-r0", DONE, env=env,
             receipt=self.receipt("resume-test", **leg, final_state_digests={"0": "a"},
                                  workers=[{"worker": 0, "param_digests": {"L00": "x"},
                                            "resumed_from": None}]))
        r1 = _job(self.root / "resume-r1-r2", 502, "q3-k1-v2-resume-r1", CONFIRMED, env=env)
        (r1 / "checkpoint.ready").write_text(
            "trigger=SIGUSR1\ntoken=t\nacks=" + json.dumps({"0": {"step": 25}}) + "\n")
        _job(self.root / "resume-r1-r2", 503, "q3-k1-v2-resume-r2", DONE,
             env={**env, "predecessor_job_id": r2_predecessor},
             receipt=self.receipt("resume-test", **leg, final_state_digests={"0": r2_digest},
                                  workers=[{"worker": 0, "param_digests": {"L00": "x"},
                                            "resumed_from": 25}]))

    def argv(self, output: Path, *extra: str) -> list[str]:
        return ["--image-receipt", str(self.image), "--bundle", str(self.bundle),
                "--bundle-sidecar", str(self.sidecar), "--bundle-commit", BUNDLE_COMMIT,
                "--probe-receipt", str(self.probe),
                "--repo-root", str(self.repo), "--smoke-run-root", str(self.root / "smoke"),
                "--headroom-dev-run-root", str(self.root / "headroom-dev"),
                "--r0-run-root", str(self.root / "resume-r0"),
                "--r1-run-root", str(self.root / "resume-r1-r2"), "--output", str(output),
                *extra]


def _report(capsys) -> dict:
    return json.loads(capsys.readouterr().out)


def test_filler_uses_measured_values_and_the_probe_derived_limits(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    out = tmp_path / "filled"
    assert filler.main(world.argv(out)) == 0
    report = _report(capsys)
    assert report["blocked"] == {} and all(g["passed"] for g in report["pre_main_gates"].values())
    for job, entry in world.limits.items():
        if job == "extension":  # filled only once a main read calls for it (below)
            continue
        manifest = load(out / f"q3-k1-v2-{job}.yaml")
        assert manifest["resources"]["minutes"] == entry["minutes"]
        assert manifest["budget"]["max_gpu_hours"] == pytest.approx(entry["max_gpu_hours"])
    main = load(out / "q3-k1-v2-main.yaml")
    assert main["image_id"] == IMAGE["image_id"]
    assert main["study_artifact"]["sha256"] == world.bundle_sha
    assert main["study_artifact"]["revision"] == BUNDLE_COMMIT
    argv = main["command"]
    assert argv[argv.index("--expected-preregistration-sha256") + 1] == world.prereg_sha
    assert load(out / "q3-k1-v2-resume-r2.yaml")["resume_from_job_id"] == 502
    for path in sorted(out.glob("q3-k1-v2-*.yaml")):
        validated = validate_manifest(load(path))
        assert validated["seed_binding"] == {"flag": "--seeds"}
        assert sbatch_argv(validated, test_only=True)[-2] == "--test-only"
    assert not (out / "q3-k1-v2-extension.yaml").exists()
    assert not (out / "q3-k1-v2-main-resume.yaml").exists()
    # An interrupted main job: its one continuation gets what is left of the main limit.
    main_root = tmp_path / "main"
    _job(main_root, 201, "q3-k1-v2-main", CONFIRMED)  # 14 minutes used (12.5 rounded up, + 1)
    later = tmp_path / "filled-later"
    assert filler.main(world.argv(later, "--main-run-root", str(main_root))) == 0
    capsys.readouterr()
    resumed = validate_manifest(load(later / "q3-k1-v2-main-resume.yaml"))
    assert resumed["minutes"] == world.limits["main"]["minutes"] - 14
    assert str(resumed["resume_from_job_id"]) == "201"
    _job(main_root, 202, "q3-k1-v2-main-resume", DONE,
         receipt={"verdict": {"verdict": "INCONCLUSIVE"}, "extension_targets": ["hs"]})
    last = tmp_path / "filled-last"
    assert filler.main(world.argv(last, "--main-run-root", str(main_root))) == 0
    assert any("second continuation" in note for note in _report(capsys)["notes"])
    extension = validate_manifest(load(last / "q3-k1-v2-extension.yaml"))
    assert str(extension["resume_from_job_id"]) == "202"
    assert extension["minutes"] == world.limits["extension"]["minutes"]


SLOWER = budget.Rates(**{**PROBE_RATES.as_dict(),
                         "layer_step_s": PROBE_RATES.layer_step_s * 1.6})
SLOWER_EXT = budget.Rates(**{**PROBE_RATES.as_dict(),
                             "layer_step_ext_s": PROBE_RATES.layer_step_ext_s * 1.7})
GATE_FAILURES = {
    "smoke over budget": (dict(smoke={"status": "SMOKE_PASS_OVER_BUDGET"}), "not SMOKE_PASS"),
    "smoke main over its limit": (dict(smoke_rates=SLOWER), "main: 1.2 x projected"),
    "smoke extension over its limit": (dict(smoke_rates=SLOWER_EXT),
                                       "extension: 1.2 x projected"),
    "a smoke gate false": (dict(smoke={"gates": {"capture_reconstruction": False}}),
                           "not every smoke gate"),
    "smoke rates missing": (dict(smoke={"projection": {}}), "rates are unreadable"),
    "headroom escalates": (dict(headroom={"decision": "ESCALATE_OR_STOP"}),
                           "not PROCEED_TO_K1"),
    "headroom numbers fail H2b": (dict(headroom={"h2b": {**GATE_INTERVAL, "point": 3.0,
                                                         "lower": 1.0}}),
                                  "rules do not give PROCEED_TO_K1"),
    "resume not bitwise": (dict(r2_digest="z"), "not equivalent"),
    "R2 resumed another job": (dict(r2_predecessor="999"), "did not resume from R1"),
    "gate jobs on another image": (dict(env={"image_id": "sha256:" + "9" * 64}),
                                   "image_id is not the v2 image B's"),
}


@pytest.mark.parametrize("failure", sorted(GATE_FAILURES))
def test_filler_blocks_the_main_read_until_every_pre_main_gate_passes(tmp_path, capsys,
                                                                       failure) -> None:
    mutation, reason = GATE_FAILURES[failure]
    world = World(tmp_path)
    world.gates(**mutation)
    main_root = tmp_path / "main"
    _job(main_root, 201, "q3-k1-v2-main", CONFIRMED)
    out = tmp_path / "filled"
    assert filler.main(world.argv(out, "--main-run-root", str(main_root))) == 0
    report = _report(capsys)
    assert set(report["blocked"]) == {f"{name}.yaml" for name in filler.MAIN_READ_TEMPLATES}
    assert any(reason in problem for problem in report["blocked"]["q3-k1-v2-main.yaml"]), report
    assert not (out / "q3-k1-v2-main.yaml").exists()
    assert (out / "q3-k1-v2-smoke.yaml").exists()


def test_filler_binds_gate_receipts_to_the_registered_identity(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    receipt_path = tmp_path / "headroom-dev" / "411" / "phase-0a-k1" / "receipt.json"
    receipt = json.loads(receipt_path.read_text())
    receipt["hashes"]["code"]["harness/sparse_indexer_bank.py"] = "1" * 64
    receipt["experiment_id"] = "q3-k1-localization-screen-v1"
    receipt_path.write_text(json.dumps(receipt))
    assert filler.main(world.argv(tmp_path / "filled")) == 0
    problems = _report(capsys)["pre_main_gates"]["headroom_dev"]["problems"]
    for name in ("code digests", "experiment_id"):
        assert any(name in problem for problem in problems), problems


def test_filler_fills_nothing_while_the_limits_await_the_probe(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    world.write_contract(None)
    world.prereg_sha = world.freeze()
    assert filler.main(world.argv(tmp_path / "pending")) == 2
    assert "not set" in capsys.readouterr().err
    assert not (tmp_path / "pending").exists() or not list((tmp_path / "pending").iterdir())


def test_filler_refuses_limits_typed_by_hand_or_from_another_probe(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    edited = {**world.limits, "main": {"minutes": world.limits["main"]["minutes"] + 5,
                                       "max_gpu_hours": budget.gpu_hours(
                                           4, world.limits["main"]["minutes"] + 5)}}
    world.write_contract(edited)
    world.prereg_sha = world.freeze()
    assert filler.main(world.argv(tmp_path / "a")) == 2
    assert "not the registered formula's limits" in capsys.readouterr().err
    world.write_contract(world.limits)
    world.prereg_sha = world.freeze(probe="0" * 64)
    assert filler.main(world.argv(tmp_path / "b")) == 2
    assert "not the one the preregistration states" in capsys.readouterr().err
    world.write_probe(PROBE_RATES, hashes={"code": {"harness/sparse_indexer_bank.py": "7" * 64}})
    world.prereg_sha = world.freeze()
    assert filler.main(world.argv(tmp_path / "c")) == 2
    assert "another version" in capsys.readouterr().err
    world.write_probe(PROBE_RATES, status="PROBE_INCOMPLETE")
    world.prereg_sha = world.freeze()
    assert filler.main(world.argv(tmp_path / "d")) == 2


def test_filler_refuses_caps_over_the_gauntlet_threshold(tmp_path, capsys) -> None:
    heavy = budget.scenario_rates("conservative")
    world = World(tmp_path, rates=heavy)
    world.gates(smoke_rates=heavy)
    assert filler.main(world.argv(tmp_path / "heavy")) == 2
    assert "gauntlet applies" in capsys.readouterr().err


def test_filler_refuses_another_bundle_commit_or_filler(tmp_path, capsys) -> None:
    world = World(tmp_path)
    world.gates()
    argv = world.argv(tmp_path / "a")
    argv[argv.index("--bundle-commit") + 1] = "d" * 40
    assert filler.main(argv) == 2
    world.prereg_sha = world.freeze(bundle="0" * 64)
    assert filler.main(world.argv(tmp_path / "b")) == 2
    world.prereg_sha = world.freeze(code={**world.code,
                                          "scripts/fill_sparse_indexer_k1_v2_manifests.py":
                                          "3" * 64})
    assert filler.main(world.argv(tmp_path / "c")) == 2
    world.prereg_sha = world.freeze()
    assert filler.main(world.argv(tmp_path / "d")) == 0


def test_continuation_refused_beyond_the_main_cap(tmp_path) -> None:
    main = tmp_path / "main"
    _job(main, 201, "q3-k1-v2-main", CONFIRMED.replace("10:12:30", "10:36:10"))
    values, notes = filler.predecessor_values(None, main, 40)
    assert "FILL-main-checkpointed-job-id" not in values
    assert "no continuation within the cap" in notes[0]


# --------------------------------------------------------------------------- #
# The probe's manifest and the limits derivation
# --------------------------------------------------------------------------- #


PROBE_TEMPLATE = probe_filler.TEMPLATE


def test_probe_template_reads_no_study_artifact_and_fits_its_cap() -> None:
    manifest = load(PROBE_TEMPLATE)
    assert "study_artifact" not in manifest
    assert manifest["resources"]["gpus"] == 1
    assert manifest["resources"]["gpus"] * manifest["resources"]["minutes"] / 60 <= (
        manifest["budget"]["max_gpu_hours"] + 1e-9)
    assert manifest["budget"]["max_gpu_hours"] == budget.PROBE_GPU_HOURS
    command = manifest["command"]
    assert command[1] == "scripts/probe_sparse_indexer_k1_throughput.py"
    assert "--evidence" not in command
    assert command[command.index("--seeds") + 1 :] == ["42", "43", "44"]


def _probe_repo(root: Path, table: dict[str, str], *, commit: bool = True) -> tuple[Path, str]:
    """A real git repo holding the frozen probe row and the tabled files at their digests."""
    import shutil
    import subprocess

    repo = root / "repo"
    prereg = repo / "program" / "preregistrations" / f"{probe_filler.EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True)
    rows = "".join(f"| {path} | {digest} |\n" for path, digest in table.items())
    prereg.write_text(f"# probe\n\n| File | SHA-256 |\n|---|---|\n{rows}")
    for path in table:
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PROJECT_ROOT / path, target)
    preregister.freeze(prereg, probe_filler.EXPERIMENT_ID,
                       ledger=repo / "program" / "preregistrations" / "ledger.jsonl", root=repo)
    git = ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
           "-c", "commit.gpgsign=false"]
    subprocess.run([*git, "init", "-q"], check=True)
    if not commit:
        subprocess.run([*git, "commit", "-q", "--allow-empty", "-m", "empty"], check=True)
    else:
        subprocess.run([*git, "add", "-A"], check=True)
        subprocess.run([*git, "commit", "-q", "-m", "frozen probe"], check=True)
    sha = subprocess.run([*git, "rev-parse", "HEAD"], check=True, capture_output=True,
                         text=True).stdout.strip()
    return repo, sha


def _image(tmp_path: Path, git_sha: str) -> Path:
    image = tmp_path / f"image-{git_sha[:8]}.json"
    image.write_text(json.dumps({**IMAGE, "git_sha": git_sha}))
    return image


def _probe_table() -> dict[str, str]:
    return {path: preregister.sha256_file(PROJECT_ROOT / path) for path in (
        probe_filler.SELF_PATH, "scripts/probe_sparse_indexer_k1_throughput.py")}


def test_probe_filler_binds_the_registered_probe_code(tmp_path) -> None:
    table = _probe_table()
    repo, sha = _probe_repo(tmp_path / "ok", table)
    assert probe_filler.main(["--image-receipt", str(_image(tmp_path, sha)), "--repo-root",
                              str(repo), "--output", str(tmp_path / "out")]) == 0
    filled = validate_manifest(load(tmp_path / "out" / PROBE_TEMPLATE.name))
    assert filled["image_id"] == IMAGE["image_id"] and filled["minutes"] == 9
    bad, bad_sha = _probe_repo(tmp_path / "bad", {
        **table, "scripts/probe_sparse_indexer_k1_throughput.py": "0" * 64})
    assert probe_filler.main(["--image-receipt", str(_image(tmp_path, bad_sha)), "--repo-root",
                              str(bad), "--output", str(tmp_path / "out2")]) == 2


def test_probe_filler_refuses_an_image_commit_without_the_frozen_row(tmp_path) -> None:
    repo, sha = _probe_repo(tmp_path / "nocommit", _probe_table(), commit=False)
    assert probe_filler.main(["--image-receipt", str(_image(tmp_path, sha)), "--repo-root",
                              str(repo), "--output", str(tmp_path / "out")]) == 2
    repo2, _sha2 = _probe_repo(tmp_path / "unknown", _probe_table())
    assert probe_filler.main(["--image-receipt", str(_image(tmp_path, "b" * 40)), "--repo-root",
                              str(repo2), "--output", str(tmp_path / "out2")]) == 2


@pytest.mark.parametrize("edit", [
    ("  minutes: 9", "  minutes: 20"),
    ("  max_gpu_hours: 0.15", "  max_gpu_hours: 0.34"),
    ("  gpus: 1", "  gpus: 2"),
])
def test_probe_filler_refuses_a_template_with_another_limit_or_cap(tmp_path, edit) -> None:
    repo, sha = _probe_repo(tmp_path / "ok", _probe_table())
    text = PROBE_TEMPLATE.read_text(encoding="utf-8")
    assert edit[0] in text
    template = tmp_path / PROBE_TEMPLATE.name
    template.write_text(text.replace(edit[0], edit[1]))
    assert probe_filler.main(["--image-receipt", str(_image(tmp_path, sha)), "--repo-root",
                              str(repo), "--template", str(template),
                              "--output", str(tmp_path / "out")]) == 2


def test_derive_script_applies_only_complete_registered_receipts(tmp_path, capsys) -> None:
    world = World(tmp_path)
    contract = tmp_path / "contract.yaml"
    contract.write_text((PROJECT_ROOT / filler.CONTRACT_PATH).read_text())
    assert derive.main(["--probe-receipt", str(world.probe), "--apply",
                        "--contract", str(contract)]) == 0
    out = json.loads(capsys.readouterr().out)
    applied = yaml.safe_load(contract.read_text())
    assert budget.check_limits(applied["execution"]["job_limits"]) == world.limits == out["limits"]
    assert applied["throughput_probe"]["receipt_sha256"] == preregister.sha256_file(world.probe)
    assert derive.main(["--probe-receipt", str(world.probe), "--apply",
                        "--contract", str(contract)]) == 2  # placeholders already replaced
    capsys.readouterr()
    world.write_probe(PROBE_RATES, limits_table={})
    assert derive.main(["--probe-receipt", str(world.probe)]) == 2
    heavy = World(tmp_path / "heavy", rates=budget.scenario_rates("conservative"))
    fresh = tmp_path / "contract-2.yaml"
    fresh.write_text((PROJECT_ROOT / filler.CONTRACT_PATH).read_text())
    assert derive.main(["--probe-receipt", str(heavy.probe), "--apply",
                        "--contract", str(fresh)]) == 2
    assert "job_limits: null" in fresh.read_text()
    capsys.readouterr()
    assert derive.main(["--scenario", "conservative"]) == 1
    assert json.loads(capsys.readouterr().out)["gauntlet_required"] is True
    assert derive.main(["--scenario", "central"]) == 0
