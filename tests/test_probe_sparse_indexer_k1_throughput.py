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
    assert set(train["solo"]) == {"0", "1", "2", "3"}
    assert all(entry["steps"]["steps_measured"] >= 1 for entry in train["solo"].values())
    check = complete["composition_check"]
    assert set(check["workers"]) == {"0", "1", "2", "3"}
    # The registered composition counts 4 sequences per step; the tiny profile runs 2,
    # so the binding worker's composed step can only exceed its measured one.
    assert 0 < check["workers"]["2"]["ratio"] <= 1.0 + 1e-9
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


def test_composition_check_flags_a_worker_slower_than_composed() -> None:
    from scripts import probe_sparse_indexer_k1_throughput as probe

    rates = budget.scenario_rates("central")
    solo = {str(w): {"layers": list(layers),
                     "steps": {"step_s": budget.shard_step_s(rates, layers)}}
            for w, layers in enumerate(budget.SHARDS)}
    assert probe.composition_check(rates, {"solo": solo})["passed"]
    solo["0"]["steps"]["step_s"] *= 1 + budget.HEADROOM + 0.01
    check = probe.composition_check(rates, {"solo": solo})
    assert not check["passed"] and check["max_ratio"] > 1.15


def test_a_cut_concurrent_arm_is_replaced_by_its_registered_bound(probe, tmp_path) -> None:
    from scripts import probe_sparse_indexer_k1_throughput as module

    out = tmp_path / "bounded"
    process = subprocess.Popen(probe.argv(out), env=probe.env(), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 1200
    while time.time() < deadline and not (out / "arms" / "concurrent-0.json").exists():
        if process.poll() is not None:
            break
        time.sleep(0.2)
    process.send_signal(signal.SIGUSR1)
    _, err = process.communicate(timeout=600)
    receipt = json.loads((out / "receipt.json").read_text())
    assert process.returncode == 0, err[-2000:]
    assert receipt["status"] == "PROBE_COMPLETE" and receipt["concurrent_bound_used"] is True
    solo = receipt["arms"]["train"]["solo"]
    assert receipt["rates"]["concurrent_step_s"] == pytest.approx(
        module.CONCURRENT_BOUND_FACTOR * sum(e["steps"]["step_s"] for e in solo.values()))
    assert set(receipt["failures"]) == {"concurrent"}


def test_registered_sizing_leaves_every_arm_the_outcome_needs_60_s_before_usr1() -> None:
    # Review finding: per-arm timeouts summed past the 9-minute limit and only the
    # concurrent arm has a fallback. The registered sizes must leave the margins
    # the registration states, in every design scenario.
    import yaml

    from scripts import probe_sparse_indexer_k1_throughput as probe

    manifest = yaml.safe_load((PROJECT_ROOT / "experiments" / "manifests"
                               / "q3-k1-throughput-probe-v1" / "q3-k1-throughput-probe.yaml"
                               ).read_text())
    assert 60 * manifest["resources"]["minutes"] == probe.LIMIT_S
    assert manifest["budget"]["max_gpu_hours"] == budget.PROBE_GPU_HOURS
    assert probe.USR1_AT_S == probe.LIMIT_S - 60 * budget.SIGNAL_LEAD_MINUTES
    shapes = probe.Shapes.registered()
    assert shapes.deadline_s == probe.DEADLINE_S
    assert probe.LANE_ALLOWANCE_S + shapes.deadline_s < probe.USR1_AT_S  # receipt before USR1
    for name in budget.SCENARIO_INPUTS:
        plan = probe.planned_wall_s(budget.scenario_rates(name), shapes)
        usr1 = probe.USR1_AT_S - probe.REQUIRED_MARGIN_S
        assert probe.LANE_ALLOWANCE_S + plan["all"] <= usr1, name
        assert probe.LANE_ALLOWANCE_S + probe.SLOW_REQUIRED * plan["required"] <= usr1, name
        assert probe.SLOW_ALL * plan["all"] <= shapes.deadline_s, name


def test_the_deadline_cuts_an_arm_and_counts_it_as_timed_out(tmp_path, monkeypatch) -> None:
    from scripts import probe_sparse_indexer_k1_throughput as probe

    runner = probe.Probe.__new__(probe.Probe)
    runner.args = type("Args", (), {"model_dir": tmp_path, "device": "cpu",
                                    "profile": "registered"})()
    runner.out, runner.shapes = tmp_path, probe.Shapes.registered()
    runner.results, runner.failures, runner.timed_out, runner.arm_wall_s = {}, {}, set(), {}
    seen: list[float] = []
    monkeypatch.setattr(runner, "_spawn", lambda arm, spec, label: (None, tmp_path / label),
                        raising=False)
    monkeypatch.setattr(runner, "_wait", lambda processes, timeout: seen.append(timeout)
                        or "timed out", raising=False)
    runner.run_arm("eval", time.monotonic() + 40.0)  # the arm's own timeout is 150 s
    assert len(seen) == 1 and 0 < seen[0] <= 40.0
    assert runner.failures["eval"] == "timed out" and "eval" in runner.timed_out
    runner.run_arm("concurrent", time.monotonic() - 1.0)
    assert len(seen) == 1  # nothing spawned after the deadline
    assert runner.failures["concurrent"] == "not run: the probe deadline passed"
    assert "concurrent" in runner.timed_out
