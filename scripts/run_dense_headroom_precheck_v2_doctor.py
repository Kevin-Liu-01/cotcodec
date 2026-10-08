#!/usr/bin/env python3
"""CPU doctor for q3-dense-headroom-precheck-v2 on tiny random models.

v1's doctor cases for the modules v2 imports unchanged (codecs, features,
artifact derivation, statistics, selectors, multiple choice), run as they are
from ``scripts/run_dense_headroom_precheck_doctor.py``, plus v2's cases:

* ``equivalence``: v2's evaluation (``harness/dense_headroom_torch_v2.py``)
  equals v1's bit for bit on every receipt field of a unit (recall per layer
  and selector, tie counts, the largest selection, the budget, the four option
  scores, the answer) on a tiny Qwen3 and a tiny Qwen3.5-style hybrid, for
  selection-only, multiple-choice-only and combined units; ``clone_cache``
  gives the same option logits as ``copy.deepcopy`` bit for bit.
* ``end_to_end``: v2's entry point on both tiny lanes under the batch
  environment (``COTCODEC_OUTPUT_DIR`` with the job's ``manifest.json`` and the
  batch script's ``job.env``): the receipt records the Slurm job of
  ``job.env``; a job without ``job.env``, or whose ``SLURM_JOB_ID`` disagrees
  with it, exits 2; every statistic and receipt field equals v1's entry point
  on the same tiny lane (``v1_reproduction`` with tolerance 0); SIGUSR1 after
  the first chunk exits 75 with the marker; the continuation completes with
  the uninterrupted numbers; a continuation without its resume receipt exits 2.
* ``job_binding``: the end-to-end receipt, in a run root laid out as the batch
  script leaves it (``job.env``, ``termination.env``, provenance, the fill
  claim) with its orx log line, passes the v2 summariser's job check; v1's
  receipt shape (``slurm_job_id`` null) is refused, as job 727's was.
* ``usr1_displaced``: the entry point runs under
  ``scripts/dense_headroom_v2_signal_shim.py``, which does inside the model's
  first forward what flash-linear-attention's first Triton compile did in job
  730 (with Triton installed it compiles a real kernel, registering LLVM's
  handlers; without Triton it sets SIGUSR1 to SIG_IGN behind CPython). v2
  answers a SIGUSR1 after the first chunk with exit 75 and the marker; v1's
  entry point under the same shim does not answer it (job 730's failure).
* ``timing_profile``: the development timing job's profile on the tiny hybrid:
  the registered subset (the first two chunks of every stage, round robin),
  v1's path on units of every stage equal to v2's bit for bit, the diagnostics,
  then a SIGUSR1 answered with exit 75, the marker and ``timing-receipt.json``,
  and no lane receipt.
* ``v1_gate``: ``v1_reproduction`` against v1's committed job-727 receipt is
  REPRODUCED on that receipt itself and FAILED on a one-leaf perturbation.

Every number is a synthetic-case number. A PASS proves executability and gate
semantics only; it says nothing about the real models or data.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from harness import dense_headroom_data as dhd  # noqa: E402
from harness import dense_headroom_stats as dhs  # noqa: E402
from harness import dense_headroom_v2 as dv2  # noqa: E402
from harness import dense_headroom_v2_lanes as lanes  # noqa: E402
from scripts import run_dense_headroom_precheck_doctor as d1  # noqa: E402

DOCTOR_NAME = "q3-dense-headroom-precheck-v2-cpu-doctor"
EVIDENCE_GRADE = d1.EVIDENCE_GRADE
ENTRY = PROJECT_ROOT / "scripts" / "run_dense_headroom_precheck_v2.py"
SHIM = PROJECT_ROOT / "scripts" / "dense_headroom_v2_signal_shim.py"
JOB_ID = "4242"
FAKE_GIT = "b" * 40
FAKE_SOURCE = "c" * 64
FAKE_IMAGE = "sha256:" + "a" * 64
CODE_UNDER_TEST = (
    "harness/dense_headroom_v2.py", "harness/dense_headroom_v2_lanes.py",
    "harness/dense_headroom_torch_v2.py", "harness/dense_headroom_data.py",
    "harness/dense_headroom_stats.py", "harness/dense_headroom_torch.py",
    "scripts/run_dense_headroom_precheck_v2.py",
    "scripts/run_dense_headroom_precheck_v2_doctor.py",
    "scripts/dense_headroom_v2_signal_shim.py",
    "scripts/summarise_dense_headroom_precheck_v2.py")
_check = d1._check


def triton_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("triton") is not None
    except (ImportError, ValueError):
        return False


def write_job_env(run_dir: Path, job_id: str = JOB_ID, predecessor: str = "none") -> None:
    """``job.env`` as the batch script writes it before the container starts
    (the fields the entry point and the summariser read)."""

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "job.env").write_text(
        f"job_id={job_id}\npredecessor_job_id={predecessor}\ngit_sha={FAKE_GIT}\n"
        f"source_sha256={FAKE_SOURCE}\nimage_id={FAKE_IMAGE}\n"
        "started_at=2026-10-08T10:00:00Z\n", encoding="utf-8")


class TinyRunV2(d1.TinyRun):
    """v1's tiny fixtures (same bundle, models and stand-in receipts) for v2's
    entry point, with a stand-in v2 preregistration frozen in a scratch ledger."""

    def __init__(self, root: Path) -> None:
        super().__init__(root)
        self.v1_prereg, self.v1_prereg_sha, self.v1_ledger = self.prereg, self.prereg_sha, \
            self.ledger
        self.prereg, self.prereg_sha, self.ledger = freeze_stand_in_prereg(root / "repo")

    def batch_files(self, lane_id: str, run_dir: Path, *, predecessor: str | None = None,
                    resume_receipt: bool = True, job_id: str | None = JOB_ID) -> None:
        run_dir.mkdir(parents=True, exist_ok=True)
        super().batch_files(lane_id, run_dir, predecessor=predecessor,
                            resume_receipt=resume_receipt)
        if job_id is not None:
            write_job_env(run_dir, job_id, predecessor or "none")

    def argv(self, lane_id: str, run_dir: Path, *, bundle_sha: str | None = None,
             seeds: tuple[str, ...] = ("42", "43", "44"), entry: Path = ENTRY,
             v1: bool = False) -> list[str]:
        receipt, receipt_sha = self.receipts[lane_id]
        prereg, prereg_sha, ledger = ((self.v1_prereg, self.v1_prereg_sha, self.v1_ledger)
                                      if v1 else (self.prereg, self.prereg_sha, self.ledger))
        return [
            sys.executable, str(entry), "--lane", lane_id,
            "--output-dir", str(run_dir / "dense-precheck"),
            "--evidence", str(self.bundle),
            "--expected-evidence-sha256", bundle_sha or self.bundle_sha,
            "--model-dir", str(self.models[lane_id]),
            "--receipt", str(receipt), "--expected-receipt-sha256", receipt_sha,
            "--preregistration", str(prereg),
            "--expected-preregistration-sha256", prereg_sha,
            "--ledger", str(ledger), "--ledger-root", str(self.root / "repo"),
            "--seeds", *seeds, "--profile", "tiny", "--device", "cpu",
        ]

    @staticmethod
    def env(run_dir: Path, batch: bool = True) -> dict[str, str]:
        env = d1.TinyRun.env(run_dir, batch)
        env["COTCODEC_GIT_SHA"] = FAKE_GIT
        env["COTCODEC_SOURCE_SHA256"] = FAKE_SOURCE
        env.pop("SLURM_JOB_ID", None)
        return env

    def run(self, lane_id: str, run_dir: Path, timeout: int = 1800, *,
            predecessor: str | None = None, resume_receipt: bool = True,
            job_id: str | None = JOB_ID, extra_env: dict[str, str] | None = None,
            **kwargs: Any) -> subprocess.CompletedProcess:
        run_dir.mkdir(parents=True, exist_ok=True)
        self.batch_files(lane_id, run_dir, predecessor=predecessor,
                         resume_receipt=resume_receipt, job_id=job_id)
        env = {**self.env(run_dir), **(extra_env or {})}
        return subprocess.run(self.argv(lane_id, run_dir, **kwargs), env=env,
                              capture_output=True, text=True, timeout=timeout, check=False)


def freeze_stand_in_prereg(root: Path) -> tuple[Path, str, Path]:
    from scripts import preregister

    prereg = root / "program" / "preregistrations" / f"{dv2.EXPERIMENT_ID}.md"
    prereg.parent.mkdir(parents=True, exist_ok=True)
    prereg.write_text("# doctor stand-in preregistration (v2)\n\nSynthetic only.\n",
                      encoding="utf-8")
    ledger = root / "program" / "preregistrations" / "ledger.jsonl"
    preregister.freeze(prereg, dv2.EXPERIMENT_ID, ledger=ledger, root=root)
    return prereg, preregister.sha256_file(prereg), ledger


# --------------------------------------------------------------------------- #
# Cases
# --------------------------------------------------------------------------- #


def _unit_fields_equal(a: Any, b: Any) -> list[str]:
    """Receipt fields of two UnitOutputs that differ bit for bit."""

    differing = []
    for field in ("recall", "ties", "max_selected", "k_blocks", "mc_scores", "mc_correct"):
        x, y = np.asarray(getattr(a, field)), np.asarray(getattr(b, field))
        same = x.shape == y.shape and x.dtype == y.dtype and (
            np.array_equal(x.view(np.uint8), y.view(np.uint8)) if x.dtype.kind == "f"
            else np.array_equal(x, y))
        if not same:
            differing.append(field)
    return differing


def case_equivalence(tmp: Path) -> dict[str, Any]:
    import torch
    from transformers import DynamicCache

    from harness import dense_headroom_torch as dht1
    from harness import dense_headroom_torch_v2 as dht2
    from harness import sparse_indexer_torch as sit

    failures: list[str] = []
    rng = np.random.default_rng(11)
    names = dhs.selector_names([42, 43, 44])
    compared = 0
    for label, maker, vocab in (("attention", d1.make_tiny_attention, 500),
                                ("hybrid", d1.make_tiny_hybrid, d1.HYBRID_VOCAB - 1)):
        model = sit.load_teacher(maker(tmp / label), "cpu")
        hybrid = dht2.is_hybrid(model.config)
        torch.use_deterministic_algorithms(True, warn_only=hybrid)
        layers = dht2.attention_layers(model.config)
        scaling = dht2.scaling_of(model.config)
        for length in (96, 203):
            tokens = rng.integers(3, vocab, size=length).astype(np.uint32)
            q0, q1, n0, n1 = length - 14, length - 2, length // 4, length // 4 + 21
            options = [rng.integers(3, vocab, size=n).astype(np.uint32) for n in (1, 3, 6, 2)]
            lex = rng.integers(0, 3, size=length // 4).astype(np.float32)
            for select, mc in ((True, False), (False, True), (True, True)):
                kwargs = dict(layers=layers, k_blocks=max(1, length // 32), fixed_k_blocks=4,
                              scaling=scaling, do_select=select, do_mc=mc, options=options,
                              option_bytes=[3, 5, 9, 4], answer=2, lex_blocks=lex,
                              seeds=[42, 43, 44], unit_key=f"c{length}-q1", names=names,
                              hybrid=hybrid, device=torch.device("cpu"))
                old = dht1.evaluate_unit(model, tokens, q0, q1, n0, n1, **kwargs)
                new = dht2.evaluate_unit(model, tokens, q0, q1, n0, n1, **kwargs)
                timed = dht2.evaluate_unit(model, tokens, q0, q1, n0, n1,
                                           timer=dht2.UnitTimer(torch.device("cpu")), **kwargs)
                compared += 1
                for which, other in (("v2", new), ("v2 timed", timed)):
                    differing = _unit_fields_equal(old, other)
                    _check(not differing, f"{label} L{length} select={select} mc={mc}: {which} "
                                          f"differs from v1 in {differing}", failures)
        if hybrid:
            prompt = torch.as_tensor(rng.integers(3, vocab, size=57))[None]
            option = torch.as_tensor(rng.integers(3, vocab, size=5))[None]
            cache = DynamicCache(config=model.config)
            with torch.no_grad():
                model(input_ids=prompt, use_cache=True, past_key_values=cache, logits_to_keep=1)
                a = model(input_ids=option, past_key_values=copy.deepcopy(cache),
                          use_cache=True).logits
                b = model(input_ids=option, past_key_values=dht2.clone_cache(cache),
                          use_cache=True).logits
                c = model(input_ids=option, past_key_values=dht2.clone_cache(cache),
                          use_cache=True).logits
            _check(torch.equal(a, b) and torch.equal(b, c),
                   "clone_cache gives other option logits than copy.deepcopy", failures)
    torch.use_deterministic_algorithms(False)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "units_compared": compared}


def case_end_to_end(tmp: Path) -> dict[str, Any]:
    failures: list[str] = []
    run = TinyRunV2(tmp / "e2e")
    out: dict[str, Any] = {}
    missing = run.run("tiny-attention", tmp / "no-job-env", job_id=None)
    _check(missing.returncode == 2 and "job.env" in missing.stderr,
           f"a job without job.env exited {missing.returncode}", failures)
    mismatch = run.run("tiny-attention", tmp / "env-mismatch", extra_env={"SLURM_JOB_ID": "7"})
    _check(mismatch.returncode == 2, f"SLURM_JOB_ID disagreeing with job.env exited "
                                     f"{mismatch.returncode}", failures)
    bad = run.run("tiny-attention", tmp / "bad-digest", bundle_sha="0" * 64)
    _check(bad.returncode == 2, f"a bundle digest mismatch exited {bad.returncode}", failures)
    for lane_id in ("tiny-attention", "tiny-hybrid"):
        run_dir = tmp / "runs" / lane_id / JOB_ID
        started = time.perf_counter()
        done = run.run(lane_id, run_dir)
        elapsed = time.perf_counter() - started
        if done.returncode != 0:
            failures.append(f"{lane_id}: exit {done.returncode}: {done.stderr[-1500:]}")
            continue
        receipt = d1.receipt_of(run_dir)
        _check(receipt["slurm_job_id"] == JOB_ID and receipt["slurm_job_id_source"] == "job.env",
               f"{lane_id}: receipt job {receipt['slurm_job_id']}", failures)
        _check(receipt["experiment_id"] == dv2.EXPERIMENT_ID, f"{lane_id}: experiment id",
               failures)
        # v1's entry point on the same lane, inputs and models.
        v1_dir = tmp / "v1" / lane_id
        v1_dir.mkdir(parents=True)
        run.batch_files(lane_id, v1_dir, job_id=None)
        v1_done = subprocess.run(run.argv(lane_id, v1_dir, entry=d1.ENTRY, v1=True),
                                 env=run.env(v1_dir), capture_output=True, text=True,
                                 timeout=1800, check=False)
        if v1_done.returncode != 0:
            failures.append(f"{lane_id}: v1 exit {v1_done.returncode}: {v1_done.stderr[-800:]}")
            continue
        old = d1.receipt_of(v1_dir)
        same = dv2.v1_reproduction(receipt, old, tolerance=0.0)
        _check(same["status"] == "REPRODUCED",
               f"{lane_id}: v2's receipt differs from v1's: {same['mismatches'][:3]}", failures)
        _check(old["slurm_job_id"] is None, "v1's entry point now records a job id", failures)
        out[lane_id] = {"seconds": round(elapsed, 1), "decisions": receipt["decisions"],
                        "units": receipt["coverage"]["units"],
                        "dev_artifact_sha256": receipt["hashes"]["dev_artifact_sha256"],
                        "v1_equal": same["status"], "numeric_leaves": same["numeric_leaves"],
                        "signals": receipt["signals"]}
    # Interrupt after the first chunk, then continue in a fresh job directory.
    lane_id = "tiny-hybrid"
    run_dir = tmp / "interrupted" / "5001"
    run.batch_files(lane_id, run_dir, job_id="5001")
    process = subprocess.Popen(run.argv(lane_id, run_dir), env=run.env(run_dir),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    sent = _signal_after_first_chunk(process, run_dir, signal.SIGUSR1)
    _, stderr = process.communicate(timeout=900)
    marker = run_dir / "checkpoint.ready"
    _check(sent and process.returncode == 75,
           f"interrupted run exited {process.returncode}: {stderr[-800:]}", failures)
    _check(marker.is_file() and "trigger=SIGUSR1" in marker.read_text(),
           "the interrupted run wrote no marker with the trigger line", failures)
    interrupted = run_dir / "dense-precheck" / "receipt-interrupted.json"
    if interrupted.is_file():
        _check(json.loads(interrupted.read_text())["slurm_job_id"] == "5001",
               "the interrupted receipt does not record its job", failures)
    saved = run_dir / "dense-precheck" / "checkpoints"
    unreceipted = tmp / "continued-no-receipt" / "5002"
    (unreceipted / "dense-precheck").mkdir(parents=True)
    if saved.is_dir():
        import shutil

        shutil.copytree(saved, unreceipted / "dense-precheck" / "checkpoints")
    refused = run.run(lane_id, unreceipted, predecessor="5001", resume_receipt=False,
                      job_id="5002")
    _check(refused.returncode == 2, "a continuation without its resume receipt exited "
           f"{refused.returncode}", failures)
    resumed = tmp / "continued" / "5003"
    (resumed / "dense-precheck").mkdir(parents=True)
    if saved.is_dir():
        import shutil

        shutil.copytree(saved, resumed / "dense-precheck" / "checkpoints")
    cont = run.run(lane_id, resumed, predecessor="5001", job_id="5003")
    _check(cont.returncode == 0, f"continuation exited {cont.returncode}: {cont.stderr[-800:]}",
           failures)
    full_dir = tmp / "runs" / lane_id / JOB_ID
    if cont.returncode == 0 and (full_dir / "dense-precheck" / "receipt.json").is_file():
        full, again = d1.receipt_of(full_dir), d1.receipt_of(resumed)
        _check(full["report"] == again["report"] and full["decisions"] == again["decisions"],
               "the continuation's read differs from the uninterrupted run", failures)
        _check(again["hashes"]["job"]["kind"] == "continuation"
               and again["hashes"]["job"]["predecessor_job_id"] == "5001"
               and again["slurm_job_id"] == "5003", "continuation job fields", failures)
    out["run_root"] = str(tmp / "runs")
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, **out}


def _signal_after_first_chunk(process: subprocess.Popen, run_dir: Path, signum: int,
                              deadline_s: float = 900) -> bool:
    eval_dir = run_dir / "dense-precheck" / "checkpoints" / "eval"
    deadline = time.time() + deadline_s
    while time.time() < deadline and process.poll() is None:
        if list(eval_dir.glob("*/chunk-*.npz")):
            process.send_signal(signum)
            return True
        time.sleep(0.05)
    return False


def lay_out_batch_job(run_root: Path, job_dir: Path, *, minutes: int,
                      lane_id: str = "qwen3-0.6b-base") -> Path:
    """Complete a job directory the entry point wrote into as the batch script and
    the filler leave it; returns the saved orx log."""

    from scripts import fill_dense_headroom_precheck_manifests as filler

    manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
    manifest.update({"name": "q3-dense-headroom-v2-0p6b", "minutes": minutes,
                     "image_id": FAKE_IMAGE})
    (job_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    (job_dir / "termination.env").write_text(
        f"job_id={job_dir.name}\nreason=completed\nexit_code=0\n"
        "finished_at=2026-10-08T10:04:38Z\ncheckpoint_ready=false\n", encoding="utf-8")
    (job_dir / "provenance-verification.txt").write_text(json.dumps(
        {"status": "PASS", "git_sha": FAKE_GIT, "source_sha256": FAKE_SOURCE}) + "\n")
    lane = lanes.LANES[lane_id]
    plan = filler.NextJob("first", minutes, 0, None, 0)
    text = json.dumps({"name": manifest["name"], "resources": {"minutes": minutes},
                       "image_id": FAKE_IMAGE})
    filler.claim_slot(run_root, lane, plan, text, FAKE_IMAGE)
    log = run_root.parent / f"orx-{job_dir.name}.log"
    log.write_text(f"ORX_SLURM_TERMINAL {job_dir.name} state=COMPLETED exit_code=0:0\n"
                   f"ORX_RESULT kind=slurm-manifest direction=translation-supervised-sparse-indexer"
                   f" job={job_dir.name} exit=0\n", encoding="utf-8")
    return log


def case_job_binding(e2e: dict[str, Any], tmp: Path) -> dict[str, Any]:
    from scripts import summarise_dense_headroom_precheck_v2 as summariser

    failures: list[str] = []
    source = Path(e2e.get("run_root", "")) / "tiny-attention" / JOB_ID
    if not (source / "dense-precheck" / "receipt.json").is_file():
        return {"status": "FAIL", "failures": ["the end-to-end case left no receipt"]}
    import shutil

    run_root = tmp / "binding" / "run-root"
    job_dir = run_root / JOB_ID
    shutil.copytree(source, job_dir)
    lane = lanes.LANES["qwen3-0.6b-base"]
    log = lay_out_batch_job(run_root, job_dir, minutes=lane.minutes)
    path = job_dir / "dense-precheck" / "receipt.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    orx = summariser.v1s.orx_results([log])
    try:
        checked = summariser.v1s.check_job(path, receipt, lane, orx)
        accepted = checked["job_id"] == JOB_ID
    except summariser.v1s.SummaryError as exc:
        accepted = False
        failures.append(f"the batch-path receipt was refused: {exc}")
    _check(accepted, "the summariser did not bind the receipt to its job", failures)
    nulled = dict(receipt, slurm_job_id=None)
    try:
        summariser.v1s.check_job(path, nulled, lane, orx)
        failures.append("a receipt with slurm_job_id null was accepted")
    except summariser.v1s.SummaryError:
        pass
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "accepted_job": JOB_ID if accepted else None}


def case_usr1_displaced(tmp: Path) -> dict[str, Any]:
    failures: list[str] = []
    mode = "triton" if triton_available() else "ignore"
    run = TinyRunV2(tmp / "usr1")
    out: dict[str, Any] = {"mode": mode}
    for which, entry in (("v2", ENTRY), ("v1", d1.ENTRY)):
        run_dir = tmp / "usr1-runs" / which / "6001"
        run.batch_files("tiny-hybrid", run_dir, job_id="6001")
        report = run_dir / "shim.json"
        env = {**run.env(run_dir), "COTCODEC_SHIM_REPORT": str(report)}
        argv = run.argv("tiny-hybrid", run_dir, entry=entry, v1=which == "v1")
        process = subprocess.Popen([sys.executable, str(SHIM), "--mode", mode, "--", *argv[1:]],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True)
        sent = _signal_after_first_chunk(process, run_dir, signal.SIGUSR1)
        try:
            _, stderr = process.communicate(timeout=900)
        except subprocess.TimeoutExpired:
            process.kill()
            _, stderr = process.communicate()
        marker = run_dir / "checkpoint.ready"
        shim = json.loads(report.read_text()) if report.is_file() else {}
        answered = (process.returncode == 75 and marker.is_file()
                    and "trigger=SIGUSR1" in marker.read_text())
        out[which] = {"signal_sent": sent, "exit": process.returncode, "answered": answered,
                      "shim": shim}
        _check(sent, f"{which}: the run ended before its first chunk", failures)
        _check(bool(shim.get("displaced")), f"{which}: the shim did not displace SIGUSR1 "
                                            f"({shim})", failures)
        if which == "v2":
            _check(answered, f"v2 did not answer SIGUSR1 after the displacement (exit "
                             f"{process.returncode}): {stderr[-600:]}", failures)
            interrupted = run_dir / "dense-precheck" / "receipt-interrupted.json"
            if interrupted.is_file():
                signals = json.loads(interrupted.read_text())["signals"]
                out[which]["guard"] = signals
                _check(signals["received"] == "SIGUSR1", "v2 recorded another signal", failures)
        else:
            _check(not answered, "v1 answered SIGUSR1 under the displacement: the stand-in "
                                 "does not reproduce job 730", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures, **out}


def case_timing_profile(tmp: Path) -> dict[str, Any]:
    """The timing profile on the tiny hybrid (CPU): the registered subset, the v1
    reference compared bit for bit, the diagnostics, then SIGUSR1 answered with
    exit 75, the marker and a timing receipt; it never writes a lane receipt."""

    failures: list[str] = []
    run = TinyRunV2(tmp / "timing")
    run_dir = tmp / "timing-runs" / "8001"
    run.batch_files("tiny-hybrid", run_dir, job_id="8001")
    manifest = json.loads((run_dir / "manifest.json").read_text())
    manifest["minutes"] = lanes.TIMING_MINUTES
    (run_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
    argv = run.argv("tiny-hybrid", run_dir)
    for flag in ("--preregistration", "--expected-preregistration-sha256"):
        at = argv.index(flag)
        del argv[at : at + 2]
    argv[argv.index("--profile") + 1] = "timing"
    process = subprocess.Popen(argv, env=run.env(run_dir), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True)
    progress = run_dir / "dense-precheck" / "timing-progress.json"
    deadline = time.time() + 900
    sent = False
    while time.time() < deadline and process.poll() is None:
        try:
            state = json.loads(progress.read_text())
        except (OSError, ValueError):
            state = {}
        if state.get("subset_complete") and state.get("chunks", 0) > 8:
            process.send_signal(signal.SIGUSR1)
            sent = True
            break
        time.sleep(0.05)
    _, stderr = process.communicate(timeout=900)
    receipt_path = run_dir / "dense-precheck" / "timing-receipt.json"
    if not receipt_path.is_file():
        return {"status": "FAIL", "failures": [f"no timing receipt (exit {process.returncode}): "
                                               f"{stderr[-800:]}"]}
    receipt = json.loads(receipt_path.read_text())
    timing = receipt["timing"]
    marker = run_dir / "checkpoint.ready"
    if sent:
        _check(process.returncode == 75 and timing["status"] == "TIMING_INTERRUPTED",
               f"the timing job answered SIGUSR1 with exit {process.returncode}", failures)
        _check(marker.is_file() and "trigger=SIGUSR1" in marker.read_text(),
               "no marker after SIGUSR1", failures)
    else:
        _check(process.returncode == 0 and timing["status"] == "TIMING_COMPLETE",
               f"the timing job ended {process.returncode} {timing['status']}", failures)
    _check(not (run_dir / "dense-precheck" / "receipt.json").exists(),
           "the timing job wrote a lane receipt", failures)
    subset = [(c["stage"], c["chunk"]) for c in timing["chunks"] if c["phase"] == "subset"]
    _check(subset == [(s, i) for i in (0, 1) for s in dhd.STAGES],
           f"the subset chunks were {subset}", failures)
    _check(timing["reference"] and all(r["bitwise_equal"] for r in timing["reference"]),
           f"v1's path differs from v2's on the timing units: {timing['reference']}", failures)
    _check({r["stage"] for r in timing["reference"]} == set(dhd.STAGES),
           "the v1 reference does not cover every stage", failures)
    _check(set(timing["torch_profiles"]) == {"v1", "v2"}, "torch profiles missing", failures)
    _check(receipt["slurm_job_id"] == "8001" and receipt["profile"] == "timing",
           "timing receipt job fields", failures)
    _check(all("parts" in u and "prefill_forward" in u["parts"] for u in timing["units"]),
           "unit component timings missing", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "signal_sent": sent, "exit": process.returncode, "units": len(timing["units"]),
            "reference": timing["reference"],
            "torch_profiles": {k: v["status"] for k, v in timing["torch_profiles"].items()}}


def case_v1_gate() -> dict[str, Any]:
    failures: list[str] = []
    v1 = dv2.load_v1_small_lane_receipt(PROJECT_ROOT)
    same = dv2.v1_reproduction(v1, v1)
    _check(same["status"] == "REPRODUCED" and same["numeric_leaves"] > 1000,
           f"v1's receipt does not reproduce itself: {same['status']}", failures)
    moved = copy.deepcopy(v1)
    moved["report"]["headroom"]["h1_cx_points"] += 2e-6
    _check(dv2.v1_reproduction(moved, v1)["status"] == "FAILED",
           "a 2e-6 gap on H1_CX passed the 1e-6 gate", failures)
    within = copy.deepcopy(v1)
    within["report"]["headroom"]["h1_cx_points"] += 5e-7
    _check(dv2.v1_reproduction(within, v1)["status"] == "REPRODUCED",
           "a 5e-7 gap failed the 1e-6 gate", failures)
    other = copy.deepcopy(v1)
    other["decisions"]["lane_class"] = "GO_ONLY_CAPABLE"
    _check(dv2.v1_reproduction(other, v1)["status"] == "FAILED",
           "a changed decision passed the gate", failures)
    artifact = copy.deepcopy(v1)
    artifact["hashes"]["dev_artifact_sha256"] = "0" * 64
    _check(dv2.v1_reproduction(artifact, v1)["status"] == "FAILED",
           "another development artifact passed the gate", failures)
    return {"status": "PASS" if not failures else "FAIL", "failures": failures,
            "numeric_leaves": same["numeric_leaves"], "other_leaves": same["other_leaves"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--skip-end-to-end", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists():
        print(f"refusing to overwrite {args.output}", file=sys.stderr)
        return 2
    dhd.block_gpu_only_kernels()  # CPU only (see v1's make_tiny_hybrid)
    started = time.perf_counter()
    cases: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="dense-v2-doctor-") as tmp_name:
        tmp = Path(tmp_name)
        runners = [("codecs", d1.case_codecs), ("features", d1.case_features),
                   ("derive", lambda: d1.case_derive(tmp / "derive")),
                   ("statistics", d1.case_statistics),
                   ("selectors", lambda: d1.case_selectors(tmp / "selectors")),
                   ("multiple_choice", lambda: d1.case_multiple_choice(tmp / "mc")),
                   ("equivalence", lambda: case_equivalence(tmp / "equivalence")),
                   ("v1_gate", case_v1_gate)]
        if not args.skip_end_to_end:
            runners += [("end_to_end", lambda: case_end_to_end(tmp / "e2e")),
                        ("job_binding", lambda: case_job_binding(cases.get("end_to_end", {}),
                                                                 tmp)),
                        ("usr1_displaced", lambda: case_usr1_displaced(tmp / "usr1")),
                        ("timing_profile", lambda: case_timing_profile(tmp / "timing"))]
        for name, runner in runners:
            began = time.perf_counter()
            try:
                cases[name] = runner()
            except Exception as exc:  # noqa: BLE001 - a crashing case is a failing case
                cases[name] = {"status": "FAIL", "failures": [f"{type(exc).__name__}: {exc}"]}
            cases[name]["seconds"] = round(time.perf_counter() - began, 1)
    status = ("DENSE_V2_DOCTOR_PASS" if all(c["status"] == "PASS" for c in cases.values())
              else "DENSE_V2_DOCTOR_FAIL")
    receipt = {"doctor": DOCTOR_NAME, "experiment_id": dv2.EXPERIMENT_ID, "status": status,
               "evidence_grade": EVIDENCE_GRADE, "numbers_are_synthetic": True,
               "triton_available": triton_available(),
               "case_status": {name: c["status"] for name, c in cases.items()},
               "cases": cases, "seconds": round(time.perf_counter() - started, 1),
               "code_sha256": {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()
                                                    ).hexdigest()
                               for name in CODE_UNDER_TEST}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True, default=str) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": status, "case_status": receipt["case_status"]}))
    return 0 if status == "DENSE_V2_DOCTOR_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

