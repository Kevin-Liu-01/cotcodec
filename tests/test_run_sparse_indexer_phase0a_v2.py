"""The K1 successor's entry point end to end on a tiny random Qwen3 model (CPU)."""

from __future__ import annotations

import json
import math
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest
import yaml

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from harness import sparse_indexer_k1_budget_v2 as budget  # noqa: E402
from harness.sparse_indexer_k1_marker import read_checkpoint_marker  # noqa: E402
from scripts.run_sparse_indexer_k1_doctor import (  # noqa: E402
    copy_checkpoints,
    final_state,
    receipt_of,
    rewrite_main_read,
)
from scripts.run_sparse_indexer_k1_v2_doctor import TinyRunV2, tight_limits  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def tiny(tmp_path_factory) -> TinyRunV2:
    return TinyRunV2(tmp_path_factory.mktemp("k1-v2-entry"))


@pytest.fixture(scope="module")
def main_run(tiny, tmp_path_factory) -> Path:
    run_dir = tmp_path_factory.mktemp("k1-v2-main") / "main"
    result = tiny.run("0a-k1", run_dir)
    assert result.returncode == 0, result.stderr[-3000:]
    return run_dir


def test_contract_entry_point_and_v1_agree() -> None:
    from scripts import run_sparse_indexer_phase0a as v1
    from scripts import run_sparse_indexer_phase0a_v2 as entry

    contract = yaml.safe_load((PROJECT_ROOT / "experiments" / "architectures" /
                               "translation-supervised-sparse-indexer-k1-screen-v2.yaml"
                               ).read_text())
    assert contract["name"] == entry.CONTRACT_NAME
    assert contract["preregistration"]["experiment_id"] == entry.EXPERIMENT_ID
    assert entry.PHASES == v1.PHASES and entry.TARGETS == v1.TARGETS
    assert entry.EXTENSION_EPOCHS == v1.EXTENSION_EPOCHS == budget.EXTENSION_STEPS // 610 + 1
    assert entry.CAPTURE_REL_ERROR_MAX == v1.CAPTURE_REL_ERROR_MAX
    assert entry.EAGER_TV_MAX == v1.EAGER_TV_MAX
    assert budget.PROJECTION_MARGIN == v1.PROJECTION_MARGIN
    assert budget.SIGNAL_LEAD_MINUTES == v1.SIGNAL_LEAD_MINUTES
    assert set(v1.CODE_FILES) <= set(entry.CODE_FILES)


def test_registered_profile_refuses_until_the_limits_exist(tiny, tmp_path) -> None:
    argv = tiny.argv("smoke", tmp_path / "registered", workers=1)
    argv[argv.index("--profile") + 1] = "registered"
    (tmp_path / "registered").mkdir()
    run = subprocess.run(argv, env=tiny.env(tmp_path / "registered"), capture_output=True,
                         text=True, timeout=300, check=False)
    assert run.returncode == 2 and "job limits are not set" in run.stderr
    override = tiny.argv("smoke", tmp_path / "override", "--limits-override",
                         str(tight_limits(tmp_path / "limits.json")), workers=1)
    override[override.index("--profile") + 1] = "registered"
    (tmp_path / "override").mkdir()
    run = subprocess.run(override, env=tiny.env(tmp_path / "override"), capture_output=True,
                         text=True, timeout=300, check=False)
    assert run.returncode == 2


def test_smoke_measures_rates_and_gates_main_and_extension(tiny, tmp_path) -> None:
    run = tiny.run("smoke", tmp_path / "smoke", workers=1)
    assert run.returncode == 0, run.stderr[-3000:]
    receipt = receipt_of(tmp_path / "smoke")
    assert receipt["status"] == "SMOKE_PASS"
    projection = receipt["projection"]
    rates = budget.Rates.from_dict(projection["rates"])
    assert budget.smoke_gate(rates, receipt["job_limits"])["passed"]
    for job in ("main", "extension"):
        assert projection[job]["required_limit_minutes"] == pytest.approx(
            1.2 * projection[job]["wall_minutes"] + 3.0)
    timings = receipt["timings"]
    assert timings["train"]["steps_measured"] == 6 - budget.STEADY_SKIP_STEPS
    assert timings["extension_timing"]["steps_measured"] >= 1
    units = timings["eval_units"]
    assert {"select_only", "select_mc", "mc_only"} <= set(units)
    assert all(units[k]["measured"] == units[k]["units"] - 1
               for k in ("select_only", "select_mc", "mc_only"))
    assert timings["train_startup_s"] > 0 and timings["eval_startup_s"] > 0
    # The checkpoint read is timed apart and left out of the start-up rate (the probe
    # loads nothing); the budget prices it at the save rate.
    assert 0 < timings["eval_load_s"] < timings["eval_startup_s"]
    assert projection["rates"]["eval_startup_s"] == pytest.approx(
        timings["eval_startup_s"] - timings["eval_load_s"])
    assert projection["main"]["projection"]["eval_load_s"] == pytest.approx(
        budget.eval_load_s(rates))
    assert receipt["recall_smoke"]["finite"] and receipt["engine"] == "k1-batched-bank-v2"
    # The extension timing run trained only the 6 LR-1e-3 indexers.
    log = (tmp_path / "smoke" / "phase-0a-k1" / "train-loss-worker-0.jsonl").read_text()
    assert len(log.splitlines()) == 6 + 6  # the 18-indexer run and the 6-indexer run
    tight = tiny.run("smoke", tmp_path / "tight", "--limits-override",
                     str(tight_limits(tmp_path / "tight.json")), workers=1)
    assert tight.returncode == 0
    assert receipt_of(tmp_path / "tight")["status"] == "SMOKE_PASS_OVER_BUDGET"


def test_signal_checkpoint_and_fresh_job_resume_are_bitwise(tiny, tmp_path) -> None:
    from scripts.compare_sparse_indexer_resume import compare

    r0 = tiny.run("resume-test", tmp_path / "r0", "--stop-after-step", "4",
                  "--checkpoint-every", "2")
    assert r0.returncode == 0, r0.stderr[-2000:]
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
    (r1_dir / "checkpoint.ready").write_text("stale\n")
    process.send_signal(signal.SIGUSR1)
    _, err = process.communicate(timeout=600)
    assert process.returncode == 75, err[-2000:]
    ack = read_checkpoint_marker(r1_dir / "checkpoint.ready")
    assert ack["trigger"] == "SIGUSR1" and {a["step"] for a in ack["acks"].values()} == {2}
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


def test_main_phase_writes_v1s_read_and_refuses_a_rerun(tiny, main_run) -> None:
    receipt = receipt_of(main_run)
    assert receipt["verdict"]["verdict"] in {"GO", "NEGATIVE", "INCONCLUSIVE", "UNINTERPRETABLE",
                                             "HOLD", "V1_EXTENSION_REQUIRED"}
    assert set(receipt["targets"]) == {"hs", "mp"}
    assert receipt["verdict_is_final"] == (not receipt["extension_targets"])
    assert len(receipt["stream_dev_kl"]) == 4 * 18
    assert [w["final_step"] for w in receipt["training_workers"]] == [6, 6]
    assert receipt["eval_workers"] and receipt["engine"] == "k1-batched-bank-v2"
    assert tiny.run("0a-k1", main_run).returncode == 2


def test_main_job_continues_after_the_lr_freeze(tiny, main_run, tmp_path) -> None:
    original = receipt_of(main_run)
    ckpt = copy_checkpoints(main_run, tmp_path / "continued", "main-read.json")
    chunks = sorted((ckpt / "eval" / "audit-main").glob("chunk-*.npz"))
    for chunk in chunks[: len(chunks) // 2]:
        chunk.unlink()
    run = tiny.run("0a-k1", tmp_path / "continued")
    assert run.returncode == 0, run.stderr[-3000:]
    again = receipt_of(tmp_path / "continued")
    assert again["lr_freeze"] == original["lr_freeze"] and again["training_workers"] == []
    for target in ("hs", "mp"):
        assert again["targets"][target]["xi"] == original["targets"][target]["xi"]


def test_extension_retrains_only_the_v1_failing_target(tiny, main_run, tmp_path) -> None:
    ext = tmp_path / "extension"
    synthetic = rewrite_main_read(copy_checkpoints(main_run, ext, "eval") / "main-read.json",
                                  mp_region="none")
    assert synthetic["extension_targets"] == ["hs"]
    run = tiny.run("0a-k1-extend", ext)
    assert run.returncode == 0, run.stderr[-3000:]
    receipt = receipt_of(ext, "receipt-extension.json")
    assert receipt["reread_targets"] == ["hs"] and receipt["kept_main_read_targets"] == ["mp"]
    main = receipt_of(main_run)
    steps = main["training_workers"][0]["final_step"]
    hs_lr = main["lr_freeze"]["selected_lr"]["hs"]
    for worker in (0, 1):
        before, after = final_state(main_run, worker, steps), final_state(ext, worker, 3 * steps)
        for name in before:
            if f"|hs|{hs_lr}|" in name:
                continue
            # Review trap: a stacked optimizer would move untrained slices; v2 never does.
            assert torch.equal(before[name], after[name]), name
        assert any(not torch.equal(before[n], after[n]) for n in before
                   if f"|hs|{hs_lr}|" in n and "|param|" in n)
    go = tmp_path / "go"
    rewrite_main_read(copy_checkpoints(main_run, go, "eval") / "main-read.json", mp_region="go")
    refused = tiny.run("0a-k1-extend", go)
    assert refused.returncode == 3 and "does not call for the V1 extension" in refused.stderr


def test_corrupt_final_generation_is_an_integrity_failure(tiny, main_run, tmp_path) -> None:
    ckpt = copy_checkpoints(main_run, tmp_path / "corrupt", "eval", "lr_freeze.json",
                            "main-read.json")
    final = sorted((ckpt / "worker-0").glob("step-*"))[-1] / "state.safetensors"
    data = bytearray(final.read_bytes())
    data[-1] ^= 0xFF
    final.write_bytes(bytes(data))
    run = tiny.run("0a-k1", tmp_path / "corrupt")
    assert run.returncode == 3 and "fails its digest check" in run.stderr


def test_a_checkpoint_from_another_engine_is_refused(tiny, tmp_path) -> None:
    # The config digest names the engine and its row chunk: a checkpoint written
    # under another configuration (v1's engine included) is refused, never resumed.
    from harness import sparse_indexer_k1_runtime as rt
    from harness import sparse_indexer_k1_runtime_v2 as rt2

    spec = rt.TrainSpec(layers=[0, 1], seeds=[42, 43, 44], targets=["hs", "mp"],
                        lrs=list(rt.LEARNING_RATES), steps=6, batch=2, warmup=2,
                        checkpoint_every=2)
    hashes = {"bundle_sha256": "b", "receipt_sha256": "r"}
    assert rt2.config_digest(spec, rt.Profile.tiny(), hashes) != rt.config_digest(
        spec, rt.Profile.tiny(), hashes)
    first = tiny.run("resume-test", tmp_path / "a", "--stop-after-step", "2",
                     "--checkpoint-every", "2")
    assert first.returncode == 0, first.stderr[-2000:]
    ckpt = copy_checkpoints(tmp_path / "a", tmp_path / "b")
    for meta_path in ckpt.glob("worker-*/step-*/meta.json"):
        meta = json.loads(meta_path.read_text())
        meta["config_digest"] = rt.config_digest(spec, rt.Profile.tiny(), hashes)
        meta_path.write_text(json.dumps(meta))
    run = tiny.run("resume-test", tmp_path / "b", "--stop-after-step", "4",
                   "--checkpoint-every", "2")
    assert run.returncode == 3 and "different configuration" in run.stderr


class _Staged:
    def __init__(self, prompts: list[dict], query_meta: list[dict]) -> None:
        self.meta = {"prompts": prompts, "query_meta": query_meta}


def test_smoke_units_are_matched_to_the_audit_rows_and_haystack_contexts() -> None:
    # Review finding: the first units of each kind measured 42 / 29 mean rows against
    # the audit's 33.2 and half the multiple-choice-only units were no-haystack
    # prompts; the smoke now times units at the rows and contexts it projects.
    from scripts import probe_sparse_indexer_k1_throughput as probe
    from scripts import run_sparse_indexer_phase0a_v2 as entry

    rows = [140, 3, 33, 34, 60, 21, 32, 35, 33, 90]
    prompts, query_meta, units = [], [], []
    for index, count in enumerate(rows):
        query_meta.append({"row_start": 0, "row_end": count})
        prompts.append({"prompt_id": f"p{index}", "role": "dev", "query_index": index})
        units.append({"unit": f"c{index:02d}-q{index}", "prompt_id": f"p{index}",
                      "select": True, "mc": index % 2 == 1})
    for index in range(6):
        role = "dev-nohaystack" if index < 3 else "dev-absent"
        prompts.append({"prompt_id": f"m{index}", "role": role, "query_index": index})
        units.append({"unit": f"c{20 + index}-q{index}", "prompt_id": f"m{index}",
                      "select": False, "mc": True})
    chosen = entry.smoke_units(units, 3, _Staged(prompts, query_meta))
    by_id = {unit["unit"]: unit for unit in chosen}
    select_only = sorted(rows[int(u["prompt_id"][1:])] for u in chosen
                         if u["select"] and not u["mc"])
    select_mc = sorted(rows[int(u["prompt_id"][1:])] for u in chosen if u["select"] and u["mc"])
    assert select_only == [32, 33, 33] and select_mc == [21, 34, 35]
    assert all(abs(sum(kind) / 3 - budget.TIMED_UNIT_ROWS) < 5
               for kind in (select_only, select_mc))
    assert probe.Shapes.registered().unit_rows == budget.TIMED_UNIT_ROWS
    assert math.ceil(budget.AUDIT_MIX.mean_rows) == budget.TIMED_UNIT_ROWS
    mc_only = [unit["prompt_id"] for unit in chosen if not unit["select"]]
    assert mc_only == ["m3", "m4", "m5"]  # haystack contexts before no-haystack ones
    assert list(by_id) == sorted(by_id)  # evaluated in v1's unit order
