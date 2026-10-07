from __future__ import annotations

import json
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest
import yaml

pytest.importorskip("torch")
pytest.importorskip("transformers")

from scripts.run_sparse_indexer_k1_doctor import TinyRun, receipt_of  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tiny(tmp_path_factory) -> TinyRun:
    return TinyRun(tmp_path_factory.mktemp("k1-entry"))


def test_contract_and_entry_point_agree() -> None:
    from scripts import run_sparse_indexer_phase0a as entry

    contract = yaml.safe_load((PROJECT_ROOT / "experiments" / "architectures" /
                               "translation-supervised-sparse-indexer-k1-screen.yaml").read_text())
    assert contract["name"] == entry.CONTRACT_NAME
    assert contract["preregistration"]["experiment_id"] == entry.EXPERIMENT_ID
    assert contract["preregistration"]["path"].endswith(f"{entry.EXPERIMENT_ID}.md")


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
    ack = json.loads(marker.read_text())
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


def test_main_phase_writes_a_verdict_and_refuses_a_rerun(tiny, tmp_path) -> None:
    run = tiny.run("0a-k1", tmp_path / "main")
    assert run.returncode == 0, run.stderr[-3000:]
    receipt = receipt_of(tmp_path / "main")
    assert receipt["verdict"]["verdict"] in {"GO", "NEGATIVE", "INCONCLUSIVE", "UNINTERPRETABLE",
                                             "HOLD", "V1_EXTENSION_REQUIRED"}
    assert set(receipt["targets"]) == {"hs", "mp"}
    assert receipt["seed_noise"]["degrees_of_freedom"] == 4
    assert receipt["hashes"]["lr_freeze_sha256"]
    assert len(receipt["stream_dev_kl"]) == 4 * 18
    hs = receipt["targets"]["hs"]
    assert {"S_vs_U_cx", "S_vs_Uk_cx", "lambda_en", "lambda_x"} <= set(hs)
    assert any("depth=" in key for key in receipt["descriptive"]["main_by_depth"])
    assert [w["final_step"] for w in receipt["training_workers"]] == [6, 6]
    again = tiny.run("0a-k1", tmp_path / "main")
    assert again.returncode == 2
