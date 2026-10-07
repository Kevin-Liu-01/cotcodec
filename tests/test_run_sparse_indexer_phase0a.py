from __future__ import annotations

import hashlib
import json
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest
import yaml

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from harness.sparse_indexer_k1_marker import read_checkpoint_marker  # noqa: E402
from scripts.run_sparse_indexer_k1_doctor import (  # noqa: E402
    TinyRun,
    copy_checkpoints,
    final_state,
    receipt_of,
    rewrite_main_read,
    signal_during_worker_start,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tiny(tmp_path_factory) -> TinyRun:
    return TinyRun(tmp_path_factory.mktemp("k1-entry"))


@pytest.fixture(scope="module")
def main_run(tiny, tmp_path_factory) -> Path:
    run_dir = tmp_path_factory.mktemp("k1-main") / "main"
    result = tiny.run("0a-k1", run_dir)
    assert result.returncode == 0, result.stderr[-3000:]
    return run_dir


def test_contract_and_entry_point_agree() -> None:
    from scripts import run_sparse_indexer_phase0a as entry

    contract = yaml.safe_load((PROJECT_ROOT / "experiments" / "architectures" /
                               "translation-supervised-sparse-indexer-k1-screen.yaml").read_text())
    assert contract["name"] == entry.CONTRACT_NAME
    assert contract["preregistration"]["experiment_id"] == entry.EXPERIMENT_ID
    assert contract["preregistration"]["path"].endswith(f"{entry.EXPERIMENT_ID}.md")


def test_registered_limits_match_the_manifests_and_the_filler() -> None:
    from scripts import fill_sparse_indexer_k1_manifests as filler
    from scripts import run_sparse_indexer_phase0a as entry

    manifests = PROJECT_ROOT / "experiments" / "manifests"
    main = yaml.safe_load((manifests / "q3-k1-main.yaml").read_text())
    extension = yaml.safe_load((manifests / "q3-k1-extension.yaml").read_text())
    assert main["resources"]["minutes"] == entry.MAIN_MAX_MINUTES == filler.MAIN_LIMIT_MINUTES
    assert extension["resources"]["minutes"] == entry.EXTENSION_LIMIT_MINUTES
    # The filler re-checks the smoke gate with the entry point's own constants.
    assert filler.PROJECTION_MARGIN == entry.PROJECTION_MARGIN
    assert filler.SIGNAL_LEAD_MINUTES == entry.SIGNAL_LEAD_MINUTES


def test_smoke_projects_the_extension_without_gating_on_it(tiny, tmp_path) -> None:
    # Pre-freeze audit: the extension's 22 minutes were never projected.
    run = tiny.run("smoke", tmp_path / "smoke", workers=1)
    assert run.returncode == 0, run.stderr[-3000:]
    receipt = receipt_of(tmp_path / "smoke")
    projection = receipt["projection"]
    extension = projection["extension"]
    assert extension["limit_minutes"] == 22.0
    assert extension["required_limit_minutes"] == pytest.approx(
        1.2 * extension["wall_minutes"] + 3.0)
    assert extension["fits_limit"] == (extension["required_limit_minutes"] <= 22.0)
    assert len(extension["train_wall_s_per_worker"]) == len(
        projection["train_wall_s_per_worker"])
    assert receipt["status"] in {"SMOKE_PASS", "SMOKE_PASS_OVER_BUDGET"}  # not gated on it


def test_startup_fails_closed_with_exit_two(tiny, tmp_path) -> None:
    assert tiny.run("smoke", tmp_path / "a", bundle_sha="0" * 64).returncode == 2
    seeds = tiny.argv("smoke", tmp_path / "b")
    seeds[seeds.index("--seeds") + 1 : seeds.index("--seeds") + 4] = ["1", "2", "3"]
    (tmp_path / "b").mkdir()
    run = subprocess.run(seeds, env=tiny.env(tmp_path / "b"), capture_output=True, text=True,
                         timeout=300, check=False)
    assert run.returncode == 2 and "seeds" in run.stderr
    tampered = tmp_path / "prereg.md"
    tampered.write_text("changed\n")
    argv = tiny.argv("smoke", tmp_path / "c")
    argv[argv.index("--preregistration") + 1] = str(tampered)
    (tmp_path / "c").mkdir()
    run = subprocess.run(argv, env=tiny.env(tmp_path / "c"), capture_output=True, text=True,
                         timeout=300, check=False)
    assert run.returncode == 2


def test_signal_checkpoint_and_fresh_job_resume_are_bitwise(tiny, tmp_path) -> None:
    from scripts.compare_sparse_indexer_resume import compare

    r0 = tiny.run("resume-test", tmp_path / "r0", "--stop-after-step", "4",
                  "--checkpoint-every", "2")
    assert r0.returncode == 0, r0.stderr[-2000:]
    assert not (tmp_path / "r0" / "checkpoint.ready").exists()
    r1_dir = tmp_path / "r1"
    r1_dir.mkdir()
    process = subprocess.Popen(
        tiny.argv("resume-test", r1_dir, "--stop-after-step", "4", "--hold-after-step", "2",
                  "--checkpoint-every", "2"),
        env=tiny.env(r1_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    holding = r1_dir / "phase-0a-k1" / "checkpoints" / "holding"
    deadline = time.time() + 600
    while len(list(holding.glob("worker-*.json"))) < 2 and time.time() < deadline:
        assert process.poll() is None, process.communicate()[1][-2000:]
        time.sleep(0.5)
    marker = r1_dir / "checkpoint.ready"
    marker.write_text("stale\n")
    process.send_signal(signal.SIGUSR1)
    _, err = process.communicate(timeout=600)
    assert process.returncode == 75, err[-2000:]
    text = marker.read_text()
    assert "\ntrigger=SIGUSR1\n" in "\n" + text  # the batch script's confirmation line
    ack = read_checkpoint_marker(marker)
    assert {a["step"] for a in ack["acks"].values()} == {2} and len(ack["acks"]) == 2
    r2_dir = tmp_path / "r2"
    (r2_dir / "phase-0a-k1").mkdir(parents=True)
    shutil.copytree(r1_dir / "phase-0a-k1" / "checkpoints", r2_dir / "phase-0a-k1" / "checkpoints")
    r2 = tiny.run("resume-test", r2_dir, "--stop-after-step", "4", "--checkpoint-every", "2")
    assert r2.returncode == 0, r2.stderr[-2000:]
    (r1_dir / "termination.env").write_text(
        "reason=signal_USR1_checkpoint_confirmed\nexit_code=75\ncheckpoint_ready=true\n")
    report = compare(tmp_path / "r0", r1_dir, r2_dir)
    assert report["equivalent"], report
    assert report["r2_resumed_from"] == [2]


@pytest.mark.parametrize("delay", [0.0, 0.3])
def test_signal_while_workers_start_checkpoints_instead_of_killing_them(tiny, tmp_path,
                                                                         delay) -> None:
    # Review finding: a SIGUSR1 forwarded before a worker installed its handler
    # killed it (exit 3, no marker). Workers now start with the signal blocked.
    process = signal_during_worker_start(tiny, tmp_path / "early", delay)
    _, err = process.communicate(timeout=600)
    assert process.returncode == 75, err[-2000:]
    marker = read_checkpoint_marker(tmp_path / "early" / "checkpoint.ready")
    assert marker["trigger"] == "SIGUSR1" and len(marker["acks"]) == 2


def test_main_job_continues_after_the_lr_freeze(tiny, main_run, tmp_path) -> None:
    # Review finding: a resumed 0a-k1 job crashed with UnboundLocalError on the
    # LR freeze after re-running the audit evaluation.
    original = receipt_of(main_run)
    ckpt = copy_checkpoints(main_run, tmp_path / "continued", "main-read.json")
    assert (ckpt / "lr_freeze.json").is_file()
    chunks = sorted((ckpt / "eval" / "audit-main").glob("chunk-*.npz"))
    for chunk in chunks[: len(chunks) // 2]:
        chunk.unlink()
    run = tiny.run("0a-k1", tmp_path / "continued")
    assert run.returncode == 0, run.stderr[-3000:]
    again = receipt_of(tmp_path / "continued")
    assert again["lr_freeze"] == original["lr_freeze"]
    assert again["hashes"]["lr_freeze_sha256"] == original["hashes"]["lr_freeze_sha256"]
    assert again["training_workers"] == []  # completed training is not repeated
    assert again["verdict"]["verdict"] == original["verdict"]["verdict"]
    for target in ("hs", "mp"):
        assert again["targets"][target]["xi"] == original["targets"][target]["xi"]
    assert (ckpt / "main-read.json").is_file()


def test_corrupt_final_generation_is_an_integrity_failure(tiny, main_run, tmp_path) -> None:
    # Review finding: evaluation silently used the previous generation (exit 0).
    ckpt = copy_checkpoints(main_run, tmp_path / "corrupt", "eval", "lr_freeze.json",
                            "main-read.json")
    final = sorted((ckpt / "worker-0").glob("step-*"))[-1] / "state.safetensors"
    data = bytearray(final.read_bytes())
    data[-1] ^= 0xFF
    final.write_bytes(bytes(data))
    run = tiny.run("0a-k1", tmp_path / "corrupt")
    assert run.returncode == 3
    assert "fails its digest check" in run.stderr
    assert not (tmp_path / "corrupt" / "phase-0a-k1" / "receipt.json").exists()


def test_extension_retrains_and_rereads_only_the_v1_failing_target(tiny, main_run,
                                                                   tmp_path) -> None:
    # Review finding: the extension retrained and re-read both targets.
    ext = tmp_path / "extension"
    synthetic = rewrite_main_read(copy_checkpoints(main_run, ext, "eval") / "main-read.json",
                                  mp_region="none")
    assert synthetic["verdict"] == "INCONCLUSIVE" and synthetic["extension_targets"] == ["hs"]
    run = tiny.run("0a-k1-extend", ext)
    assert run.returncode == 0, run.stderr[-3000:]
    receipt = receipt_of(ext, "receipt-extension.json")
    assert receipt["reread_targets"] == ["hs"] and receipt["kept_main_read_targets"] == ["mp"]
    assert set(receipt["targets"]) == {"hs"}
    # Program decision D16: the extension's combined verdict is final unless it is VOID.
    expected_final = ("INCONCLUSIVE" if receipt["verdict"]["verdict"] == "VOID"
                      else receipt["verdict"]["verdict"])
    assert receipt["final_verdict"]["verdict"] == expected_final
    assert receipt["verdict"]["per_target"]["mp"]["xi"] == json.loads(
        json.dumps(synthetic["reads"][1]["xi"]))
    main = receipt_of(main_run)
    steps = main["training_workers"][0]["final_step"]
    hs_lr = main["lr_freeze"]["selected_lr"]["hs"]
    for worker in (0, 1):
        before, after = final_state(main_run, worker, steps), final_state(ext, worker, 3 * steps)
        changed = {name for name in before if "|param|" in name
                   and not torch.equal(before[name], after[name])}
        assert changed and all(f"|hs|{hs_lr}|" in name for name in changed)


def test_extension_refuses_a_read_that_does_not_call_for_it(tiny, main_run, tmp_path) -> None:
    go = tmp_path / "go"
    rewrite_main_read(copy_checkpoints(main_run, go, "eval") / "main-read.json", mp_region="go")
    run = tiny.run("0a-k1-extend", go)
    assert run.returncode == 3 and "does not call for the V1 extension" in run.stderr
    tampered = tmp_path / "tampered"
    path = copy_checkpoints(main_run, tampered, "eval") / "main-read.json"
    payload = rewrite_main_read(path, mp_region="none")
    payload["extension_targets"] = ["hs", "mp"]
    path.write_text(json.dumps(payload))
    run = tiny.run("0a-k1-extend", tampered)
    assert run.returncode == 3 and "disagrees with the registered verdict rules" in run.stderr


def test_main_phase_writes_a_verdict_and_refuses_a_rerun(tiny, main_run) -> None:
    receipt = receipt_of(main_run)
    assert receipt["verdict"]["verdict"] in {"GO", "NEGATIVE", "INCONCLUSIVE", "UNINTERPRETABLE",
                                             "HOLD", "V1_EXTENSION_REQUIRED"}
    assert set(receipt["targets"]) == {"hs", "mp"}
    assert receipt["verdict_is_final"] == (not receipt["extension_targets"])
    assert receipt["seed_noise"]["degrees_of_freedom"] == 4
    assert receipt["hashes"]["lr_freeze_sha256"]
    assert len(receipt["stream_dev_kl"]) == 4 * 18
    hs = receipt["targets"]["hs"]
    assert {"S_vs_U_cx", "S_vs_Uk_cx", "lambda_en", "lambda_x"} <= set(hs)
    assert any("depth=" in key for key in receipt["descriptive"]["main_by_depth"])
    assert [w["final_step"] for w in receipt["training_workers"]] == [6, 6]
    main_read = main_run / "phase-0a-k1" / "checkpoints" / "main-read.json"
    assert hashlib.sha256(main_read.read_bytes()).hexdigest() == (
        receipt["hashes"]["main_read_sha256"])
    assert json.loads(main_read.read_text())["verdict"] == receipt["verdict"]["verdict"]
    again = tiny.run("0a-k1", main_run)
    assert again.returncode == 2
