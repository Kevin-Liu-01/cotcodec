"""The K1 throughput probe on a tiny random Qwen3 model (CPU): arms, receipt, refusals."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from harness import sparse_indexer_k1_budget_v2 as budget  # noqa: E402
from scripts.run_sparse_indexer_k1_doctor import (  # noqa: E402
    make_tiny_model,
    write_stand_in_receipt,
)
from scripts.run_sparse_indexer_k1_v2_doctor import freeze_stand_in  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE = PROJECT_ROOT / "scripts" / "probe_sparse_indexer_k1_throughput.py"


class TinyProbe:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.model = make_tiny_model(root / "model")
        self.prereg, self.prereg_sha, self.ledger = freeze_stand_in(
            root / "repo", "q3-k1-throughput-probe-v1")
        self.receipt = root / "receipt.json"
        self.receipt_sha = write_stand_in_receipt(self.receipt)

    def argv(self, out: Path, *, seeds: tuple[str, ...] = ("42", "43", "44")) -> list[str]:
        return [sys.executable, str(PROBE), "--output-dir", str(out),
                "--model-dir", str(self.model), "--receipt", str(self.receipt),
                "--expected-receipt-sha256", self.receipt_sha,
                "--preregistration", str(self.prereg),
                "--expected-preregistration-sha256", self.prereg_sha,
                "--ledger", str(self.ledger), "--ledger-root", str(self.root / "repo"),
                "--seeds", *seeds, "--profile", "tiny", "--device", "cpu"]

    @staticmethod
    def env() -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if not k.startswith("COTCODEC_")}
        env["OMP_NUM_THREADS"] = "2"
        return env


@pytest.fixture(scope="module")
def probe(tmp_path_factory) -> TinyProbe:
    return TinyProbe(tmp_path_factory.mktemp("k1-probe"))


@pytest.fixture(scope="module")
def complete(probe, tmp_path_factory) -> dict:
    out = tmp_path_factory.mktemp("k1-probe-run") / "probe"
    run = subprocess.run(probe.argv(out), env=probe.env(), capture_output=True, text=True,
                         timeout=1800, check=False)
    assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-4000:]
    return json.loads((out / "receipt.json").read_text())


def test_probe_completes_every_arm_and_derives_limits(complete) -> None:
    assert complete["status"] == "PROBE_COMPLETE" and not complete["failures"]
    assert set(complete["arms"]) == {"tolerance", "train", "eval", "capture", "concurrent"}
    assert complete["arms"]["tolerance"]["passed"] is True
    rates = budget.Rates.from_dict(complete["rates"])
    assert rates.concurrent_step_s is not None and rates.train_startup_s > 0
    derived = budget.derive_limits(rates)
    assert budget.limits_table(derived) == complete["limits_table"]
    assert complete["data"].startswith("synthetic token ids")
    assert set(complete["hashes"]["code"]) >= {"harness/sparse_indexer_bank.py",
                                               "harness/sparse_indexer_k1_runtime_v2.py",
                                               "scripts/probe_sparse_indexer_k1_throughput.py"}


def test_probe_measures_steady_state_apart_from_startup(complete) -> None:
    train = complete["arms"]["train"]
    assert train["steps"]["steps_skipped"] == budget.STEADY_SKIP_STEPS
    assert len(train["steps"]["step_s_all"]) == 4 and train["steps"]["steps_measured"] == 2
    assert train["extension"]["steps_measured"] == 1 and len(train["devkl"]) == 2
    split = train["components_descriptive"]
    assert split["layer"] == 2 and split["slots"] == 18
    assert split["targets_plus_bank_s"] >= split["enqueue_s"] > 0
    evaluation = complete["arms"]["eval"]
    summary = evaluation["summary"]
    for kind in ("select_only", "select_mc", "mc_only"):
        assert summary[kind]["units"] == 3 and summary[kind]["measured"] == 2
    assert summary["selection_mean_rows"] == 5.0
    assert evaluation["select_only_long_mean_s"] is not None
    concurrent = complete["arms"]["concurrent"]
    assert [w["layers"] for w in concurrent] == [[0], [1], [2], [3]]
    assert all(w["startup_s"] > 0 for w in concurrent)


def test_probe_refuses_other_seeds_and_a_changed_registration(probe, tmp_path) -> None:
    run = subprocess.run(probe.argv(tmp_path / "a", seeds=("1", "2", "3")), env=probe.env(),
                         capture_output=True, text=True, timeout=300, check=False)
    assert run.returncode == 2 and "seeds" in run.stderr
    argv = probe.argv(tmp_path / "b")
    tampered = tmp_path / "prereg.md"
    tampered.write_text("changed\n")
    argv[argv.index("--preregistration") + 1] = str(tampered)
    run = subprocess.run(argv, env=probe.env(), capture_output=True, text=True, timeout=300,
                         check=False)
    assert run.returncode == 2


def test_a_signal_stops_the_probe_incomplete(probe, tmp_path) -> None:
    out = tmp_path / "signalled"
    process = subprocess.Popen(probe.argv(out), env=probe.env(), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 600
    while time.time() < deadline and not (out / "arms" / "train.json").exists():
        if process.poll() is not None:
            break
        time.sleep(0.2)
    process.send_signal(signal.SIGUSR1)
    _, err = process.communicate(timeout=600)
    assert process.returncode == 3, err[-2000:]
    receipt = json.loads((out / "receipt.json").read_text())
    assert receipt["status"] == "PROBE_INCOMPLETE" and "rates" not in receipt
    assert any("SIGUSR1" in reason for reason in receipt["failures"].values())
