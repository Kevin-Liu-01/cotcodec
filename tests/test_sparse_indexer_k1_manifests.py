from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts import fill_sparse_indexer_k1_manifests as filler
from scripts import preregister
from scripts.compare_sparse_indexer_resume import compare
from scripts.compare_sparse_indexer_resume import main as compare_main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = sorted((PROJECT_ROOT / "experiments" / "manifests").glob("q3-k1-*.yaml"))
CONTRACT = yaml.safe_load(
    (PROJECT_ROOT / "experiments" / "architectures"
     / "translation-supervised-sparse-indexer-k1-screen.yaml").read_text(encoding="utf-8"))


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_every_registered_job_has_a_manifest() -> None:
    names = {path.stem for path in MANIFESTS}
    assert names == {"q3-k1-smoke", "q3-k1-headroom-dev", "q3-k1-resume-r0", "q3-k1-resume-r1",
                     "q3-k1-resume-r2", "q3-k1-main", "q3-k1-extension"}


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
    gpu_hours = manifest["resources"]["gpus"] * manifest["resources"]["minutes"] / 60
    assert gpu_hours <= manifest["budget"]["max_gpu_hours"] + 1e-9
    # Fail closed: the unfilled template is not a valid image id.
    assert manifest["image_id"].startswith("FILL-")


def test_registered_budget_matches_the_contract() -> None:
    total = sum(load(p)["budget"]["max_gpu_hours"] for p in MANIFESTS
                if "extension" not in p.stem)
    assert total <= CONTRACT["execution"]["max_gpu_hours"] + 1e-9
    assert load(PROJECT_ROOT / "experiments/manifests/q3-k1-main.yaml")["budget"][
        "max_gpu_hours"] == 2.0


def test_resume_legs_share_the_stop_step_and_r1_holds() -> None:
    legs = {stem: load(PROJECT_ROOT / f"experiments/manifests/{stem}.yaml")["command"]
            for stem in ("q3-k1-resume-r0", "q3-k1-resume-r1", "q3-k1-resume-r2")}
    stops = {stem: argv[argv.index("--stop-after-step") + 1] for stem, argv in legs.items()}
    assert len(set(stops.values())) == 1
    assert "--hold-after-step" in legs["q3-k1-resume-r1"]
    assert "--hold-after-step" not in legs["q3-k1-resume-r0"]
    r2 = load(PROJECT_ROOT / "experiments/manifests/q3-k1-resume-r2.yaml")
    assert r2["resume_subpath"] == "phase-0a-k1/checkpoints"


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
    (r1 / "checkpoint.ready").write_text(json.dumps(
        {"acks": {"0": {"step": 25}, "1": {"step": 25}}}))
    assert compare(r0, r1, r2)["equivalent"]
    _receipt(tmp_path / "r3", {"0": "a", "1": "c"}, {"0": {"L00": "x"}, "1": {"L01": "z"}}, 25)
    report = compare(r0, r1, tmp_path / "r3")
    assert not report["equivalent"] and report["mismatched_indexers"] == ["L01"]
    assert compare_main(["--r0", str(r0), "--r1", str(r1), "--r2", str(tmp_path / "r3"),
                         "--output", str(tmp_path / "out.json")]) == 1


def test_filler_uses_only_measured_values(tmp_path) -> None:
    image = tmp_path / "receipt.json"
    image.write_text(json.dumps({"image_id": "sha256:" + "a" * 64, "git_sha": "b" * 40,
                                 "source_tar_sha256": "c" * 64}))
    bundle = tmp_path / "k1-bundle-v1.json"
    bundle.write_bytes(b"{}\n")
    digest = hashlib.sha256(b"{}\n").hexdigest()
    sidecar = tmp_path / "k1-bundle-v1.json.manifest.json"
    sidecar.write_text(json.dumps({"sha256": digest, "size_bytes": 3}))
    repo = tmp_path / "repo"
    prereg = repo / "program" / "preregistrations" / f"{filler.EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True)
    prereg.write_text("frozen\n")
    preregister.freeze(prereg, filler.EXPERIMENT_ID,
                       ledger=repo / "program" / "preregistrations" / "ledger.jsonl", root=repo)
    r1 = tmp_path / "r1"
    (r1 / "123").mkdir(parents=True)
    (r1 / "123" / "job.env").write_text("job_id=123\n")
    out = tmp_path / "filled"
    code = filler.main(["--image-receipt", str(image), "--bundle", str(bundle),
                        "--bundle-sidecar", str(sidecar), "--bundle-commit", "d" * 40,
                        "--repo-root", str(repo), "--r1-run-root", str(r1),
                        "--output", str(out)])
    assert code == 0
    main = load(out / "q3-k1-main.yaml")
    assert main["image_id"] == "sha256:" + "a" * 64
    assert main["study_artifact"]["sha256"] == digest
    assert main["study_artifact"]["size_bytes"] == 3
    argv = main["command"]
    assert argv[argv.index("--expected-preregistration-sha256") + 1] == (
        preregister.sha256_file(prereg))
    assert load(out / "q3-k1-resume-r2.yaml")["resume_from_job_id"] == 123
    assert not (out / "q3-k1-extension.yaml").exists()  # main job id not yet measured
    sidecar.write_text(json.dumps({"sha256": "0" * 64, "size_bytes": 3}))
    assert filler.main(["--image-receipt", str(image), "--bundle", str(bundle),
                        "--bundle-sidecar", str(sidecar), "--bundle-commit", "d" * 40,
                        "--repo-root", str(repo), "--output", str(tmp_path / "x")]) == 2
