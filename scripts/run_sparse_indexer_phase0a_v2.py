#!/usr/bin/env python3
"""GPU entry point of the K1 successor screen (preregistration q3-k1-localization-screen-v2).

The v1 entry point (``scripts/run_sparse_indexer_phase0a.py``, unchanged) with
the batched bank and the vectorised evaluation of
``harness/sparse_indexer_k1_runtime_v2.py``, and with limits that come from the
throughput probe (``harness/sparse_indexer_k1_budget_v2.py``). The phases, the
signal protocol, the checkpoints, the LR freeze, the statistics, the verdict
and the extension rules are v1's.

Phases:

``smoke``         v1's bf16 capture consistency and eager check; a 12-step
                  training of all 28 layers (18 indexers each) and a 6-step
                  timing run of the extension's 6 indexers; a 4-sequence
                  stream-dev KL timing; 72 development units (24 selection-only,
                  24 selection plus multiple choice, 24 multiple-choice only)
                  with the 12-step indexers; steady-state rates (steps 0-1 and
                  the first unit of each kind excluded, start-up separately);
                  the projection of the main job and of the worst-case V1
                  extension, each gated against its registered limit.
``headroom-dev``  v1's dense-only development pre-check (H1, H2a, H2b).
``resume-test``   v1's resume legs.
``0a-k1``         v1's main read.
``0a-k1-extend``  v1's V1 extension.

Exit codes: 0 complete, 2 contract violation at startup, 3 integrity failure,
75 checkpointed and incomplete.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from harness import sparse_indexer_k1_budget_v2 as budget  # noqa: E402
from harness import sparse_indexer_k1_runtime as rt  # noqa: E402
from harness import sparse_indexer_k1_stats as k1s  # noqa: E402
from harness.sparse_indexer_k1_runtime import (  # noqa: E402
    EXIT_CHECKPOINTED,
    EXIT_CONTRACT,
    EXIT_INTEGRITY,
    EXIT_OK,
    CheckpointedExit,
    RuntimeContractError,
)

PHASES = ("smoke", "headroom-dev", "resume-test", "0a-k1", "0a-k1-extend")
EXPERIMENT_ID = "q3-k1-localization-screen-v2"
CONTRACT_NAME = "translation-supervised-sparse-indexer-k1-screen-v2"
TARGETS = ("hs", "mp")
SMOKE_LR = 1e-3  # v1's smoke: both targets at 1e-3, indexers never reused
EXTENSION_EPOCHS = 3
MAIN_READ = "main-read.json"
WORKER_SIGNALS = {signal.SIGUSR1, signal.SIGTERM}
CODE_FILES = (
    "scripts/run_sparse_indexer_phase0a_v2.py",
    "harness/sparse_indexer_bank.py",
    "harness/sparse_indexer_k1_budget_v2.py",
    "harness/sparse_indexer_k1_runtime_v2.py",
    "scripts/run_sparse_indexer_phase0a.py",
    "harness/sparse_indexer_torch.py",
    "harness/sparse_indexer_k1_runtime.py",
    "harness/sparse_indexer_k1_marker.py",
    "harness/sparse_indexer_k1_stats.py",
    "harness/sparse_indexer_data.py",
    "harness/translation_supervised_indexer.py",
)
TINY_LIMIT_MINUTES = 600  # the tiny profile's default limits (CPU doctor and tests only)


class StartupError(RuntimeError):
    """A fail-closed startup check failed (exit code 2)."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    # allow_abbrev=False: a prefix such as --see must never reach a seed option.
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-evidence-sha256", required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--expected-preregistration-sha256", required=True)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--ledger-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stop-after-step", type=int, default=None)
    parser.add_argument("--hold-after-step", type=int, default=None)
    parser.add_argument("--checkpoint-every", type=int, default=None)
    parser.add_argument("--profile", choices=("registered", "tiny"), default="registered")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--stage-dir", type=Path, default=None)
    parser.add_argument("--limits-override", type=Path, default=None,
                        help="tiny profile only: a JSON limits table for the smoke gate")
    return parser.parse_args(argv)


# --------------------------------------------------------------------------- #
# Startup checks
# --------------------------------------------------------------------------- #


def _sha(path: Path) -> str:
    return rt.sha256_file(path)


def registered_limits(contract: dict[str, Any]) -> dict[str, dict[str, float]]:
    """The contract's job limits; refused while they await the throughput probe."""

    limits = contract.get("execution", {}).get("job_limits")
    if not isinstance(limits, dict):
        raise StartupError("the contract's job limits are not set (they come from the "
                           "q3-k1-throughput-probe-v1 receipt)")
    try:
        return budget.check_limits(limits)
    except budget.BudgetContractError as exc:
        raise StartupError(f"the contract's job limits are invalid: {exc}") from exc


def tiny_limits(override: Path | None) -> dict[str, dict[str, float]]:
    if override is not None:
        return budget.check_limits(json.loads(override.read_text(encoding="utf-8")))
    return {job: {"minutes": TINY_LIMIT_MINUTES,
                  "max_gpu_hours": budget.gpu_hours(gpus, TINY_LIMIT_MINUTES)}
            for job, gpus in budget.JOBS}


def startup_checks(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict,
                                                      dict[str, dict[str, float]]]:
    """Fail closed before any work; returns (bundle, contract, hashes, limits)."""

    from harness import sparse_indexer_data as sid
    from scripts import preregister

    if not args.contract.is_file():
        raise StartupError("contract file is missing")
    contract = yaml.safe_load(args.contract.read_text(encoding="utf-8"))
    if not isinstance(contract, dict) or contract.get("name") != CONTRACT_NAME:
        raise StartupError(f"contract must be {CONTRACT_NAME}")
    if contract.get("preregistration", {}).get("experiment_id") != args.experiment_id:
        raise StartupError("contract and argv disagree on the experiment id")
    if len(set(args.seeds)) < 3 or args.seeds != sorted(set(args.seeds)):
        raise StartupError("seeds must be at least three distinct ascending integers")
    if args.seeds != contract["statistics"]["seeds"]:
        raise StartupError("argv seeds differ from the contract's declared seeds")
    if args.profile == "registered":
        if args.limits_override is not None:
            raise StartupError("--limits-override is for the tiny profile only")
        limits = registered_limits(contract)
    else:
        limits = tiny_limits(args.limits_override)
    try:
        bundle = sid.load_bundle(args.evidence, args.expected_evidence_sha256)
    except (OSError, sid.DataContractError) as exc:
        raise StartupError(f"bundle check failed: {exc}") from exc
    prereg_sha = _sha(args.preregistration)
    if prereg_sha != args.expected_preregistration_sha256:
        raise StartupError("preregistration sha256 differs from the expected digest")
    try:
        row = preregister.verify(args.experiment_id, ledger=args.ledger or
                                 preregister.DEFAULT_LEDGER, root=args.ledger_root)
    except preregister.PreregistrationError as exc:
        raise StartupError(f"preregistration ledger check failed: {exc}") from exc
    if row["sha256"] != prereg_sha:
        raise StartupError("ledger row digest differs from the preregistration file")
    receipt_sha = _sha(args.receipt)
    if receipt_sha != args.expected_receipt_sha256:
        raise StartupError("model receipt sha256 differs from the expected digest")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    model = contract.get("k1_model", {})
    for field in ("model_id", "revision"):
        if model.get(field) and receipt.get(field) != model[field]:
            raise StartupError(f"receipt {field} differs from the contract")
    tokenizer_entries = [f for f in receipt.get("files", []) if isinstance(f, dict)
                         and str(f.get("path", "")).endswith("tokenizer.json")]
    if args.profile == "registered":
        if not tokenizer_entries:
            raise StartupError("receipt lists no tokenizer.json")
        if tokenizer_entries[0].get("sha256") != bundle.get("tokenizer_sha256"):
            raise StartupError("bundle tokens were not produced by the receipted tokenizer")
        if bundle["stream"]["sequence_length"] != 8192:
            raise StartupError("registered profile needs 8,192-token sequences")
    output_root = os.environ.get("COTCODEC_OUTPUT_DIR")
    if output_root:
        manifest_path = Path(output_root) / "manifest.json"
        if not manifest_path.is_file():
            raise StartupError("the batch manifest is missing from the output root")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("seeds") != args.seeds:
            raise StartupError("manifest seeds differ from argv seeds")
        if manifest.get("model", {}).get("receipt_sha256") not in (None, receipt_sha):
            raise StartupError("manifest receipt digest differs")
        study = manifest.get("study_artifact", {})
        if study and study.get("sha256") != args.expected_evidence_sha256:
            raise StartupError("manifest study artifact digest differs")
    if args.device == "cuda":
        import torch

        visible = torch.cuda.device_count()
        expected = os.environ.get("COTCODEC_EXPECTED_GPUS")
        if expected is not None and visible != int(expected):
            raise StartupError(f"{visible} visible GPUs, expected {expected}")
        if visible < 1:
            raise StartupError("no GPU is visible")
    hashes = {
        "bundle_sha256": args.expected_evidence_sha256,
        "preregistration_sha256": prereg_sha,
        "ledger_row_hash": str(row["hash"]),
        "receipt_sha256": receipt_sha,
        "contract_sha256": _sha(args.contract),
        "git_sha": os.environ.get("COTCODEC_GIT_SHA", "unknown"),
        "source_sha256": os.environ.get("COTCODEC_SOURCE_SHA256", "unknown"),
        "code": {name: _sha(PROJECT_ROOT / name) for name in CODE_FILES},
    }
    return bundle, contract, hashes, limits


# --------------------------------------------------------------------------- #
# Parent orchestration
# --------------------------------------------------------------------------- #


class Parent:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.flag = rt.SignalFlag()
        self.flag.install()
        self.out = args.output_dir
        self.ckpt = self.out / "checkpoints"
        self.marker = Path(os.environ.get("COTCODEC_CHECKPOINT_MARKER",
                                          str(self.out.parent / "checkpoint.ready")))
        self.profile = rt.Profile.registered() if args.profile == "registered" else (
            rt.Profile.tiny())
        self.timings: dict[str, float] = {}
        self.hashes: dict[str, Any] = {}
        self.limits: dict[str, dict[str, float]] = {}

    # -- signal protocol (v1) ------------------------------------------------- #

    def _delete_stale_marker(self) -> None:
        if self.marker.exists():
            self.marker.unlink()

    def _request_token(self) -> str:
        token = f"{int(time.time())}-{os.getpid()}-{self.flag.received}"
        rt.atomic_write_json(self.ckpt / "signal" / "request.json",
                             {"token": token, "signal": self.flag.received})
        return token

    def _write_marker(self, token: str, acks: dict[str, Any]) -> None:
        # Written only here, after every running worker acknowledged its
        # signal-triggered save; periodic saves never touch this file.
        rt.write_checkpoint_marker(self.marker, str(self.flag.received), token, acks)

    def checkpoint_without_workers(self) -> None:
        """A signal outside a worker stage: all state is already on disk."""

        self._delete_stale_marker()
        token = self._request_token()
        self._write_marker(token, {"parent": "no worker running; state already persisted"})
        raise CheckpointedExit(-1)

    def run_workers(self, specs: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
        if self.flag.received:
            self.checkpoint_without_workers()
        spec_dir = self.out / "worker-specs" / label
        spec_dir.mkdir(parents=True, exist_ok=True)
        children: list[tuple[int, subprocess.Popen]] = []
        n_devices = self._device_count()
        started = time.perf_counter()
        # Workers inherit SIGUSR1/SIGTERM blocked and unblock them only after
        # installing their handler (v1's start-up protocol).
        previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, WORKER_SIGNALS)
        try:
            for spec in specs:
                worker = int(spec["worker"])
                path = spec_dir / f"worker-{worker}.json"
                spec = {**spec, "spawned_at": time.time()}
                rt.atomic_write_json(path, spec)
                env = dict(os.environ)
                if self.args.device == "cuda":
                    env["CUDA_VISIBLE_DEVICES"] = str(worker % n_devices)
                children.append((worker, subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "--worker", str(path)],
                    env=env)))
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        token: str | None = None
        running_at_signal: set[int] = set()
        failed = False
        while any(child.poll() is None for _, child in children):
            if self.flag.received and token is None:
                self._delete_stale_marker()
                token = self._request_token()
                for worker, child in children:
                    if child.poll() is None:
                        running_at_signal.add(worker)
                        child.send_signal(signal.SIGUSR1)
            if not failed and any(child.poll() not in (None, 0, EXIT_CHECKPOINTED)
                                  for _, child in children):
                failed = True
                for _, child in children:
                    if child.poll() is None:
                        child.terminate()
            time.sleep(0.2)
        codes = {worker: child.wait() for worker, child in children}
        self._reap_orphans()
        self.timings[f"workers:{label}"] = time.perf_counter() - started
        if any(code not in (0, EXIT_CHECKPOINTED) for code in codes.values()):
            raise RuntimeContractError(f"{label}: worker exit codes {codes}")
        if token is not None or any(code == EXIT_CHECKPOINTED for code in codes.values()):
            token = token or "unrequested"
            acks: dict[str, Any] = {}
            for worker, code in codes.items():
                ack = self.ckpt / "signal" / token / f"worker-{worker}.json"
                if code == EXIT_CHECKPOINTED:
                    if not ack.is_file():
                        raise RuntimeContractError(f"worker {worker} exited 75 without an ack")
                    acks[str(worker)] = json.loads(ack.read_text(encoding="utf-8"))
                elif worker in running_at_signal and code == 0:
                    acks[str(worker)] = {"completed_before_save": True}
            self._write_marker(token, acks)
            raise CheckpointedExit(-1)
        results = []
        for worker in sorted(codes):
            result_path = spec_dir / f"worker-{worker}.result.json"
            results.append(json.loads(result_path.read_text(encoding="utf-8")))
        return results

    @staticmethod
    def _reap_orphans() -> None:
        while True:
            try:
                pid, _ = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if pid == 0:
                return

    def _device_count(self) -> int:
        if self.args.device != "cuda":
            return 1
        import torch

        return max(1, torch.cuda.device_count())

    # -- shared pieces ------------------------------------------------------ #

    def base_spec(self, worker: int, kind: str, ckpt: Path | None = None) -> dict[str, Any]:
        return {"worker": worker, "kind": kind, "out_dir": str(self.out),
                "ckpt_dir": str(ckpt or self.ckpt), "stage_dir": str(self.stage_dir),
                "model_dir": str(self.args.model_dir), "device": self.args.device,
                "profile": self.args.profile, "hashes": {
                    k: v for k, v in self.hashes.items() if isinstance(v, str)}}

    def layer_shards(self, n_layers: int, workers: int) -> list[list[int]]:
        from harness import sparse_indexer_torch as sit

        return sit.balanced_layer_shards(n_layers, workers)

    def model_layers(self) -> int:
        config = json.loads((self.args.model_dir / "config.json").read_text(encoding="utf-8"))
        return int(config["num_hidden_layers"])

    def train_spec(self, layers: list[int], steps: int, *, epochs: int = 1,
                   train_only: list[str] | None = None,
                   accept_config_digests: list[str] | None = None,
                   stop_after_step: int | None = None) -> rt.TrainSpec:
        every = self.args.checkpoint_every or self.profile.checkpoint_every
        stop = self.args.stop_after_step if stop_after_step is None else stop_after_step
        return rt.TrainSpec(layers=layers, seeds=list(self.args.seeds), targets=list(TARGETS),
                            lrs=list(rt.LEARNING_RATES), steps=steps, batch=self.profile.batch,
                            warmup=self.profile.warmup, checkpoint_every=every,
                            stop_after_step=stop, hold_after_step=self.args.hold_after_step,
                            epochs=epochs, train_only=train_only,
                            accept_config_digests=accept_config_digests)

    def total_steps(self, staged: rt.StagedData) -> int:
        n_train = int(staged.array("train_tokens").shape[0])
        return self.profile.steps or n_train // self.profile.batch

    def train(self, staged: rt.StagedData, label: str, shards: list[list[int]], steps: int,
              *, ckpt: Path | None = None, **kwargs: Any) -> list[dict[str, Any]]:
        specs = []
        for worker, layers in enumerate(shards):
            spec = self.base_spec(worker, "train", ckpt)
            spec["train"] = asdict(self.train_spec(layers, steps, **kwargs))
            specs.append(spec)
        return self.run_workers(specs, label)

    def training_complete(self, shards: list[list[int]], steps: int) -> bool:
        return rt.training_completed(self.ckpt, len(shards), steps)

    def evaluate(self, staged: rt.StagedData, stage: str, units: list[dict[str, Any]],
                 with_indexers: bool, freeze: tuple[str, str] | None,
                 shards: list[list[int]], workers: int, final_step: int | None = None
                 ) -> list[dict[str, Any]]:
        per_worker = [units[w::workers] for w in range(workers)]
        specs = []
        for worker, assigned in enumerate(per_worker):
            spec = self.base_spec(worker, "eval")
            spec["eval"] = asdict(rt.EvalSpec(
                stage=stage, units=assigned, seeds=list(self.args.seeds),
                with_indexers=with_indexers,
                lr_freeze_path=freeze[0] if freeze else None,
                lr_freeze_sha256=freeze[1] if freeze else None, train_layers=shards,
                final_step=final_step))
            specs.append(spec)
        return self.run_workers(specs, f"eval-{stage}")

    def write_receipt(self, name: str, payload: dict[str, Any]) -> str:
        from harness.sparse_indexer_k1_runtime_v2 import ENGINE

        payload = {**payload, "hashes": self.hashes, "timings_s": self.timings,
                   "experiment_id": self.args.experiment_id, "phase": self.args.phase,
                   "profile": self.profile.name, "seeds": list(self.args.seeds),
                   "engine": ENGINE, "job_limits": self.limits,
                   "slurm_job_id": os.environ.get("SLURM_JOB_ID")}
        return rt.atomic_write_json(self.out / name, payload)

    # -- phases --------------------------------------------------------------- #

    def run(self) -> int:
        args = self.args
        self.out.mkdir(parents=True, exist_ok=True)
        receipt_name = {"0a-k1-extend": "receipt-extension.json"}.get(args.phase, "receipt.json")
        if (self.out / receipt_name).exists():
            raise StartupError(f"{self.out / receipt_name} exists; a rerun needs a new run root")
        started = time.perf_counter()
        bundle, contract, hashes, limits = startup_checks(args)
        self.hashes = hashes
        self.contract = contract
        self.limits = limits
        self.stage_dir = args.stage_dir or Path(os.environ.get("TMPDIR", "/tmp")) / (
            f"k1-stage-{os.getpid()}")
        rt.stage_bundle(bundle, self.stage_dir)
        self.bundle_reports = bundle.get("reports", {})
        del bundle
        staged = rt.StagedData(self.stage_dir)
        self.timings["startup"] = time.perf_counter() - started
        handler = {
            "smoke": self.phase_smoke,
            "headroom-dev": self.phase_headroom_dev,
            "resume-test": self.phase_resume_test,
            "0a-k1": self.phase_main,
            "0a-k1-extend": self.phase_extend,
        }[args.phase]
        return handler(staged)

    def phase_resume_test(self, staged: rt.StagedData) -> int:
        if self.args.stop_after_step is None:
            raise StartupError("resume-test needs --stop-after-step")
        shards = self.layer_shards(self.model_layers(), self.args.workers)
        steps = self.total_steps(staged)
        results = self.train(staged, "resume-test", shards, steps)
        self.write_receipt("receipt.json", {
            "status": "RESUME_TEST_LEG_COMPLETE",
            "stop_after_step": self.args.stop_after_step,
            "workers": [{key: value for key, value in result.items() if key != "step_records"}
                        for result in results],
            "final_state_digests": {str(r["worker"]): r["state_digest"] for r in results},
            "comparison": "compare final_state_digests and param digests of the resumed leg "
                          "with the uninterrupted leg (scripts/compare_sparse_indexer_resume.py)",
        })
        return EXIT_OK

    def _units(self, staged: rt.StagedData, partition: str, selection_roles: set[str],
               mc_roles: set[str], mc_conditions: set[str]) -> tuple[list, dict, list]:
        prompts = [p for p in staged.meta["prompts"] if p["partition"] == partition]
        from harness.translation_supervised_indexer import PassageSplit, assert_reads_within

        split = PassageSplit(
            development=frozenset(staged.meta["split"]["development"]),
            audit=frozenset(staged.meta["split"]["audit"]),
            primary=frozenset(staged.meta["split"]["primary"]),
            seed=int(staged.meta["split"]["seed"]))
        assert_reads_within((p["cluster"] for p in prompts), split, partition)
        units, prompt_to_unit = rt.plan_units(prompts, selection_roles, mc_roles, mc_conditions)
        return units, prompt_to_unit, prompts

    def audit_units(self, staged: rt.StagedData) -> tuple[list, dict, list]:
        return self._units(staged, "audit", {"main", "same-script", "literal"},
                           {"main", "absent"}, {"MN", "CX"})

    def dev_units(self, staged: rt.StagedData) -> tuple[list, dict, list]:
        return self._units(staged, "development", {"dev"},
                           {"dev", "dev-absent", "dev-nohaystack"}, {"CX"})

    def phase_headroom_dev(self, staged: rt.StagedData) -> int:
        units, prompt_to_unit, prompts = self.dev_units(staged)
        self.evaluate(staged, "dev-headroom", units, False, None, [], self.args.workers)
        results = rt.collect_eval(self.ckpt, "dev-headroom", prompt_to_unit)
        report = self._headroom_report(prompts, results, "dev", "dev-absent")
        nohay = [p for p in prompts if p["role"] == "dev-nohaystack"]
        report["no_haystack_accuracy"] = float(np.mean(
            [rt.mc_correct(results["rows"][p["prompt_id"]]) for p in nohay])) if nohay else None
        report["delta_se_cluster"] = self._delta_se(prompts, results, "dev")
        go = (report["h1_points"] >= k1s.H1_INTERPRET_POINTS
              and report["h2a"]["lower"] > k1s.H2A_ACCURACY_POINTS
              and report["h2b"]["lower"] > 0.0 and report["h2b"]["point"] >= k1s.H2B_POINTS)
        report["decision"] = "PROCEED_TO_K1" if go else "ESCALATE_OR_STOP"
        report["h1_negative_ready"] = report["h1_points"] >= k1s.H1_NEGATIVE_POINTS
        rt.atomic_write_json(self.out / "headroom.json", report)
        self.write_receipt("receipt.json", {"status": "HEADROOM_DEV_COMPLETE", **report,
                                            "units": results["units"]})
        return EXIT_OK

    def _headroom_report(self, prompts: list, results: dict, present: str,
                         absent: str) -> dict[str, Any]:
        summary = rt.summarise_headroom(prompts, results, TARGETS, present, absent)
        return {"h1_by_target": summary["h1_by_target"], "h1_points": summary["h1_points"],
                "h2a": rt.interval_dict(summary["h2a"]), "h2b": rt.interval_dict(summary["h2b"]),
                "needle_absent_accuracy": summary["absent_accuracy"]}

    def _delta_se(self, prompts: list, results: dict, role: str) -> dict[str, float]:
        rows, selectors = results["rows"], results["selectors"]
        families: dict[str, dict[str, Any]] = {}
        for p in prompts:
            if p["role"] == role:
                families.setdefault(p["family_id"], {})[p["condition"]] = p
        pairs = sorted({f["MN"]["pair"] for f in families.values()})
        clusters = sorted({f["MN"]["cluster"] for f in families.values()})
        out = {}
        for name in ("T:hs", "T:mp", "U"):
            values, pair, cluster = [], [], []
            for family in families.values():
                mn = rt.prompt_recall(rows[family["MN"]["prompt_id"]], selectors, name)
                cx = rt.prompt_recall(rows[family["CX"]["prompt_id"]], selectors, name)
                values.append(mn - cx)
                pair.append(pairs.index(family["MN"]["pair"]))
                cluster.append(clusters.index(family["MN"]["cluster"]))
            interval = k1s.macro_mean_interval(np.asarray(values), np.asarray(pair),
                                               np.asarray(cluster))
            out[name] = {"delta": interval.point, "se_cluster": interval.se_cluster}
        return out

    # -- smoke ---------------------------------------------------------------- #

    def phase_smoke(self, staged: rt.StagedData) -> int:
        from harness.sparse_indexer_k1_runtime_v2 import summarise_steps, summarise_units
        from scripts.run_sparse_indexer_phase0a import smoke_capture_check

        report: dict[str, Any] = {}
        started = time.perf_counter()
        report["capture"] = smoke_capture_check(self.args, staged, self.profile)
        capture_s = time.perf_counter() - started
        n_layers = self.model_layers()
        shards = [list(range(n_layers))]
        total = self.total_steps(staged)
        train_steps = min(budget.SMOKE_TRAIN_STEPS, total)
        ext_steps = min(budget.SMOKE_EXTENSION_STEPS, total)
        # 1. The registered 18 indexers per layer, every layer, one worker.
        trained = self.train(staged, "smoke-train", shards, total, stop_after_step=train_steps)[0]
        # 2. The extension's worst case: 6 trainable indexers per layer (timing only).
        ext_keys = [rt.indexer_key(t, SMOKE_LR, s) for t in TARGETS for s in self.args.seeds]
        extension = self.train(staged, "smoke-extension-timing", shards, total,
                               ckpt=self.ckpt / "smoke-extension-timing",
                               stop_after_step=ext_steps, train_only=ext_keys)[0]
        # 3. Stream-dev KL on a prefix of the stream-dev sequences (timing only).
        spec = self.base_spec(0, "devkl")
        spec["train"] = asdict(self.train_spec(shards[0], train_steps))
        spec["max_sequences"] = budget.SMOKE_DEVKL_SEQUENCES
        devkl = self.run_workers([spec], "smoke-devkl-timing")[0]
        # 4. Development units of each kind with the 12-step indexers.
        freeze = {"rule": "smoke only: LR 1e-3 for both targets, no stream-dev KL",
                  "selected_lr": {t: rt.lr_tag(SMOKE_LR) for t in TARGETS}}
        freeze_path = self.ckpt / "smoke-lr.json"
        freeze_sha = rt.atomic_write_json(freeze_path, freeze)
        units, _, _ = self.dev_units(staged)
        chosen = smoke_units(units, budget.SMOKE_UNITS_PER_KIND, staged)
        evaluated = self.evaluate(staged, "smoke", chosen, True, (str(freeze_path), freeze_sha),
                                  shards, 1, final_step=int(trained["final_step"]))[0]
        merged = rt.collect_eval(self.ckpt, "smoke", {u["unit"]: u["unit"] for u in chosen})
        selection_rows = [row["recall"] for unit, row in merged["rows"].items()
                          if np.isfinite(row["recall"]).any()]
        recalls = np.stack(selection_rows) if selection_rows else np.zeros((0, n_layers, 1))
        report["recall_smoke"] = {
            "units": len(chosen),
            "selection_units": len(selection_rows),
            "finite": bool(np.isfinite(recalls).all()),
            "mean_recall_by_selector": dict(zip(merged["selectors"], np.nanmean(
                recalls, axis=(0, 1)).tolist(), strict=True)) if selection_rows else {},
            "max_selected_tokens": int(max(r["max_selected"] for r in merged["rows"].values())),
            "note": "plumbing only: 12-step indexers at LR 1e-3, never reused; multiple-choice "
                    "scores are timed, not summarised",
        }
        steps = summarise_steps(trained["step_records"], budget.STEADY_SKIP_STEPS)
        ext = summarise_steps(extension["step_records"], budget.STEADY_SKIP_STEPS)
        unit_summary = summarise_units(evaluated["timings"]["units"], budget.UNIT_SKIP)
        report["timings"] = {"train": steps, "extension_timing": ext,
                             "devkl": devkl["timings"], "eval_units": unit_summary,
                             "train_startup_s": trained["timings"]["startup_s"],
                             "extension_startup_s": extension["timings"]["startup_s"],
                             "eval_startup_s": evaluated["timings"]["startup_s"],
                             "eval_load_s": evaluated["timings"]["load_s"],
                             "save_s": trained["timings"]["save_s"], "capture_s": capture_s}
        gates = {
            "capture_reconstruction": report["capture"]["max_rel_output_error"]
            <= CAPTURE_REL_ERROR_MAX,
            "eager_sanity": report["capture"]["max_layer_mean_tv"] <= EAGER_TV_MAX,
            "recall_finite": report["recall_smoke"]["finite"],
            "selection_budget": report["recall_smoke"]["max_selected_tokens"]
            <= self.profile.k_blocks * 4 + 3,
        }
        if self.profile.name == "registered":
            # Metadata only (roles, partitions, indices, query spans), as v1's projection.
            audit_plan, _ = rt.plan_units(
                [p for p in staged.meta["prompts"] if p["partition"] == "audit"],
                {"main", "same-script", "literal"}, {"main", "absent"}, {"MN", "CX"})
            gates["audit_unit_mix_registered"] = unit_mix(audit_plan, staged) == budget.AUDIT_MIX
            gates["dev_unit_mix_registered"] = unit_mix(units, staged) == budget.DEV_MIX
        report["gates"] = gates
        try:
            rates = smoke_rates(report, n_layers, self.profile.batch)
        except (KeyError, TypeError, ValueError, budget.BudgetContractError) as exc:
            raise RuntimeContractError(f"the smoke could not measure its rates: {exc}") from exc
        gate = budget.smoke_gate(rates, self.limits)
        report["projection"] = {"rates": rates.as_dict(), **gate,
                                "descriptive": {job: budget.project(rates, job)
                                                for job in ("smoke", "headroom-dev")}}
        status = "SMOKE_PASS" if all(gates.values()) else "SMOKE_FAIL"
        if status == "SMOKE_PASS" and not gate["passed"]:
            status = "SMOKE_PASS_OVER_BUDGET"
        self.write_receipt("receipt.json", {"status": status, **report})
        return EXIT_OK if all(gates.values()) else EXIT_INTEGRITY

    # -- main read and extension (v1) ------------------------------------------ #

    def _main_flow(self, staged: rt.StagedData, *, extension: bool) -> int:
        from harness import sparse_indexer_k1_runtime_v2 as rt2

        n_layers = self.model_layers()
        shards = self.layer_shards(n_layers, self.args.workers)
        steps = self.total_steps(staged)
        freeze_path = self.ckpt / "lr_freeze.json"
        main_read_path = self.ckpt / MAIN_READ
        training: list[dict[str, Any]] = []
        main_read: dict[str, Any] | None = None
        if not extension:
            if not self.training_complete(shards, steps):
                training = self.train(staged, "train", shards, steps)
            if not all((self.ckpt / "devkl" / f"worker-{w}.json").is_file()
                       for w in range(len(shards))):
                specs = []
                for worker, layers in enumerate(shards):
                    spec = self.base_spec(worker, "devkl")
                    spec["train"] = asdict(self.train_spec(layers, steps))
                    specs.append(spec)
                self.run_workers(specs, "devkl")
            if not freeze_path.is_file():
                devkl = [json.loads((self.ckpt / "devkl" / f"worker-{w}.json").read_text(
                    encoding="utf-8")) for w in range(len(shards))]
                frozen = rt.freeze_learning_rates(devkl, TARGETS, rt.LEARNING_RATES,
                                                  self.args.seeds)
                frozen["written_before_audit_read"] = True
                rt.atomic_write_json(freeze_path, frozen)
            stage, final_step, read_targets = "audit-main", steps, list(TARGETS)
        else:
            if not freeze_path.is_file():
                raise RuntimeContractError("the extension needs the main run's LR freeze")
            main_read, main_read_sha = load_main_read(main_read_path)
            self.hashes["main_read_sha256"] = main_read_sha
            read_targets = list(main_read["extension_targets"])
            if not read_targets:
                raise RuntimeContractError(
                    f"the main read ({main_read['verdict']}) does not call for the V1 extension")
            if main_read["lr_freeze_sha256"] != rt.sha256_file(freeze_path):
                raise RuntimeContractError("lr_freeze.json differs from the main read's freeze")
            selected = json.loads(freeze_path.read_text(encoding="utf-8"))["selected_lr_value"]
            # Only the V1-failing targets' frozen-LR indexers train on epochs 2-3.
            keys = [rt.indexer_key(t, selected[t], s)
                    for t in read_targets for s in self.args.seeds]
            total = steps * EXTENSION_EPOCHS
            if not self.training_complete(shards, total):
                accept = [rt2.config_digest(self.train_spec(layers, steps), self.profile,
                                            self.hashes) for layers in shards]
                training = self.train(staged, "train-extension", shards, total,
                                      epochs=EXTENSION_EPOCHS, train_only=keys,
                                      accept_config_digests=accept)
            stage, final_step = "audit-extension", total
        # The freeze is read back from the bytes whose digest the evaluation
        # workers verify, on a fresh run and on a resumed one alike.
        freeze_bytes = freeze_path.read_bytes()
        freeze_sha = hashlib.sha256(freeze_bytes).hexdigest()
        freeze = json.loads(freeze_bytes)
        self.hashes["lr_freeze_sha256"] = freeze_sha
        if self.flag.received:
            self.checkpoint_without_workers()
        units, prompt_to_unit, prompts = self.audit_units(staged)
        evaluated = self.evaluate(staged, stage, units, True, (str(freeze_path), freeze_sha),
                                  shards, self.args.workers, final_step=final_step)
        if self.flag.received:
            self.checkpoint_without_workers()
        results = rt.collect_eval(self.ckpt, stage, prompt_to_unit)
        report, reads, headroom_read = self.statistics(prompts, results,
                                                       staged.meta["context_meta"],
                                                       read_targets)
        if extension:
            assert main_read is not None
            main_reads = [k1s.TargetRead.from_dict(r) for r in main_read["reads"]]
            combined = k1s.combine_after_extension(main_reads, reads)
            decision_headroom = k1s.HeadroomRead.from_dict(main_read["headroom"])
            verdict = k1s.k1_verdict(combined, decision_headroom, after_extension=True)
            # Program decision D16: the extension's combined verdict is final,
            # except that a void extension makes the final verdict INCONCLUSIVE.
            final = k1s.final_verdict(k1s.k1_verdict(main_reads, decision_headroom),
                                      main_reads, verdict)
            report["final_verdict"] = {"verdict": final.verdict,
                                       "reasons": list(final.reasons)}
            report["headroom_recomputed_descriptive"] = report.pop("headroom")
            report["headroom"] = main_read["headroom_report"]
            report["main_read"] = main_read
            report["reread_targets"] = read_targets
            report["kept_main_read_targets"] = [r.target for r in main_reads
                                                if r.target not in read_targets]
        else:
            verdict = k1s.k1_verdict(reads, headroom_read)
            ext_targets = k1s.extension_targets(verdict, reads)
            payload = {"schema": "cotcodec-k1-main-read-v1",
                       "reads": [read.as_dict() for read in reads],
                       "headroom": headroom_read.as_dict(),
                       "headroom_report": report["headroom"],
                       "verdict": verdict.verdict, "reasons": list(verdict.reasons),
                       "extension_targets": ext_targets, "lr_freeze_sha256": freeze_sha}
            self.hashes["main_read_sha256"] = rt.atomic_write_json(main_read_path, payload)
            report["extension_targets"] = ext_targets
            report["verdict_is_final"] = not ext_targets
        report["verdict"] = {"verdict": verdict.verdict, "reasons": list(verdict.reasons),
                             "per_target": verdict.per_target}
        report["training_workers"] = [
            {key: result.get(key) for key in ("worker", "final_step", "state_digest", "timings",
                                               "resumed_from")} for result in training]
        report["eval_workers"] = [{"worker": r["worker"], "timings": {
            "startup_s": r["timings"]["startup_s"],
            "units": rt2.summarise_units(r["timings"]["units"], 0)}} for r in evaluated]
        report["lr_freeze"] = freeze
        report["units"] = results["units"]
        devkl_all = {}
        for worker in range(len(shards)):
            path = self.ckpt / "devkl" / f"worker-{worker}.json"
            if path.is_file():
                devkl_all.update(json.loads(path.read_text(encoding="utf-8"))["kl"])
        report["stream_dev_kl"] = devkl_all
        report["bundle_reports"] = self.bundle_reports
        name = "receipt-extension.json" if stage == "audit-extension" else "receipt.json"
        self.write_receipt(name, report)
        return EXIT_OK if verdict.verdict != "VOID" else EXIT_INTEGRITY

    def phase_main(self, staged: rt.StagedData) -> int:
        return self._main_flow(staged, extension=False)

    def phase_extend(self, staged: rt.StagedData) -> int:
        return self._main_flow(staged, extension=True)

    def statistics(self, prompts: list, results: dict, context_meta: list[dict[str, Any]],
                   read_targets: list[str]) -> tuple[dict[str, Any], list[k1s.TargetRead],
                                                     k1s.HeadroomRead]:
        """Per-target reads for ``read_targets``, the dense headroom read and descriptives."""

        seeds = list(self.args.seeds)
        rows, selectors = results["rows"], results["selectors"]
        k_limit = self.profile.k_blocks * 4 + 3
        integrity = all(row["max_selected"] <= k_limit for row in rows.values())
        literal_en = [p for p in prompts if p["role"] == "literal" and p["pair"] == "en>en"]
        reads, report = [], {"targets": {}}
        for target in read_targets:
            table, pair_names = rt.build_family_table(prompts, results, target, seeds, "main",
                                                      "CX")
            xi = k1s.xi_interval(table)
            xi_rel = k1s.xi_rel_interval(table)
            ind_ml = tuple(float(np.mean([rt.prompt_recall(rows[p["prompt_id"]], selectors,
                                                           f"I:{target}:{s}")
                                          for p in literal_en])) for s in seeds)
            tgt_ml = float(np.mean([rt.prompt_recall(rows[p["prompt_id"]], selectors,
                                                     f"T:{target}") for p in literal_en]))
            adequacy = k1s.AdequacyRead(ind_ml, tgt_ml)
            reads.append(k1s.TargetRead(target, xi, xi_rel, adequacy, integrity))
            cs_table, _ = rt.build_family_table(prompts, results, target, seeds, "same-script",
                                                "CS")
            xi_cs = k1s.xi_point(cs_table)
            ind_cx = table.ind_cx.mean(axis=0)
            report["targets"][target] = {
                "xi": rt.interval_dict(xi), "xi_rel": rt.interval_dict(xi_rel),
                "xi_cs": xi_cs, "attribution": k1s.attribution_label(xi.point, xi_cs),
                "english_ml": {"indexer_by_seed": ind_ml, "target": tgt_ml,
                               "v1_pass": adequacy.v1_pass, "v2_bug_tell": adequacy.v2_bug_tell},
                "delta_ind": float(np.mean(table.ind_mn.mean(axis=0) - ind_cx)),
                "delta_target": float(np.mean(table.tgt_mn - table.tgt_cx)),
                "single_difference_cx": float(np.mean(table.tgt_cx - ind_cx)),
                "pairs": pair_names,
                "cx_recall_by_seed": [float(v) for v in table.ind_cx.mean(axis=1)],
                **rt.reference_and_literal_rows(prompts, results, target, seeds),
            }
        headroom = rt.summarise_headroom(prompts, results, TARGETS, "main", "absent")
        headroom_read = k1s.HeadroomRead(headroom["h1_points"], headroom["h2a"], headroom["h2b"])
        report["headroom"] = {"h1_by_target": headroom["h1_by_target"],
                              "h1_points": headroom["h1_points"],
                              "h2a": rt.interval_dict(headroom["h2a"]),
                              "h2b": rt.interval_dict(headroom["h2b"]),
                              "needle_absent_accuracy": headroom["absent_accuracy"]}
        report["seed_noise"] = k1s.seed_noise_report(
            {t: report["targets"][t]["cx_recall_by_seed"] for t in read_targets})
        report["integrity"] = {"selection_within_budget_and_finite": integrity,
                               "k_token_limit": k_limit, "units": results["units"]}
        report["descriptive"] = {
            "main": rt.descriptive_tables(prompts, results, "main"),
            "same_script": rt.descriptive_tables(prompts, results, "same-script"),
            "literal": rt.descriptive_tables(prompts, results, "literal"),
            "main_by_depth": rt.depth_tables(prompts, results, context_meta, "main"),
            "tie_counts": {name: int(sum(int(row["ties"][i]) for row in rows.values()))
                           for i, name in enumerate(selectors)},
        }
        return report, reads, headroom_read


CAPTURE_REL_ERROR_MAX = 1e-2  # v1's smoke gates
EAGER_TV_MAX = 0.10


NO_HAYSTACK_ROLE = "dev-nohaystack"


def smoke_units(units: list[dict[str, Any]], per_kind: int,
                staged: rt.StagedData) -> list[dict[str, Any]]:
    """The smoke's timed development units, matched to the audit's cost per unit.

    Metadata only (roles and query spans). Selection units of either kind: the
    ``per_kind`` units whose query rows are closest to ``budget.TIMED_UNIT_ROWS``
    (the audit mean of 33.2 rounded up, the probe's unit rows; ties to v1's
    unit order), so the smoke and the probe time units of the same rows, at
    the audit mean, and neither needs row scaling. Multiple-choice-only units:
    haystack contexts first, like the audit's needle-absent ones
    (``dev-nohaystack`` prompts have about half the context), then v1's unit
    order.
    """

    prompts = {p["prompt_id"]: p for p in staged.meta["prompts"]}
    order = {unit["unit"]: index for index, unit in enumerate(units)}

    def rows(unit: dict[str, Any]) -> int:
        meta = staged.meta["query_meta"][int(prompts[unit["prompt_id"]]["query_index"])]
        return int(meta["row_end"]) - int(meta["row_start"])

    kinds: dict[str, list[dict[str, Any]]] = {"select_only": [], "select_mc": [],
                                              "mc_only": []}
    for unit in units:
        kind = ("select_mc" if unit["select"] and unit["mc"]
                else "select_only" if unit["select"] else "mc_only" if unit["mc"] else None)
        if kind is not None:
            kinds[kind].append(unit)
    target = budget.TIMED_UNIT_ROWS
    picked: list[dict[str, Any]] = []
    for kind in ("select_only", "select_mc"):
        picked += sorted(kinds[kind],
                         key=lambda unit: (abs(rows(unit) - target), order[unit["unit"]])
                         )[:per_kind]
    picked += sorted(kinds["mc_only"],
                     key=lambda unit: (prompts[unit["prompt_id"]]["role"] == NO_HAYSTACK_ROLE,
                                       order[unit["unit"]]))[:per_kind]
    return sorted(picked, key=lambda unit: unit["unit"])


def unit_mix(units: list[dict[str, Any]], staged: rt.StagedData) -> budget.UnitMix:
    """The kind counts and selection query rows of planned units (metadata only)."""

    prompts = {p["prompt_id"]: p for p in staged.meta["prompts"]}
    rows = 0
    for unit in units:
        if unit["select"]:
            meta = staged.meta["query_meta"][int(prompts[unit["prompt_id"]]["query_index"])]
            rows += int(meta["row_end"]) - int(meta["row_start"])
    return budget.UnitMix(
        select_only=sum(1 for u in units if u["select"] and not u["mc"]),
        select_mc=sum(1 for u in units if u["select"] and u["mc"]),
        mc_only=sum(1 for u in units if u["mc"] and not u["select"]),
        selection_rows_total=rows)


def smoke_rates(report: dict[str, Any], n_layers: int, batch: int) -> budget.Rates:
    """Registered rates from the smoke's own measurements (steady state, start-up apart)."""

    timings = report["timings"]
    train, ext = timings["train"], timings["extension_timing"]
    if not train.get("steps_measured") or not ext.get("steps_measured"):
        raise ValueError("too few smoke steps to measure a steady state")
    sequences = timings["devkl"]["sequences"][budget.UNIT_SKIP:] or timings["devkl"]["sequences"]
    units = timings["eval_units"]
    kinds = {kind: units.get(kind, {}).get("mean_s") for kind in ("select_only", "select_mc",
                                                                  "mc_only")}
    if any(value is None for value in kinds.values()):
        raise ValueError("the smoke measured no unit of some kind")
    return budget.Rates(
        teacher_layer_seq_s=train["teacher_s"] / (batch * n_layers),
        layer_step_s=train["layers_total_s"] / n_layers,
        layer_step_ext_s=ext["layers_total_s"] / n_layers,
        step_overhead_s=max(0.0, train["overhead_s"]),
        devkl_teacher_layer_seq_s=float(np.mean([s["teacher_s"] for s in sequences])) / n_layers,
        devkl_layer_seq_s=float(np.mean([sum(s["layers_s"].values()) for s in sequences]))
        / n_layers,
        save_layer_s=float(timings["save_s"][-1]) / n_layers,
        train_startup_s=float(max(timings["train_startup_s"], timings["extension_startup_s"])),
        # Spawn to the first unit without the checkpoint read, as the probe
        # measures it; the budget prices the read apart (budget.eval_load_s).
        eval_startup_s=max(0.0, float(timings["eval_startup_s"])
                           - float(timings["eval_load_s"])),
        eval_select_s=float(kinds["select_only"]),
        eval_select_mc_s=float(kinds["select_mc"]),
        eval_mc_only_s=float(kinds["mc_only"]),
        eval_rows=float(units["selection_mean_rows"]),
        capture_check_s=float(timings["capture_s"]))


def load_main_read(path: Path) -> tuple[dict[str, Any], str]:
    """v1's check of ``checkpoints/main-read.json`` against the registered verdict rules."""

    try:
        payload = path.read_bytes()
        main_read = json.loads(payload)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeContractError("the extension needs the main job's main-read.json") from exc
    if main_read.get("schema") != "cotcodec-k1-main-read-v1":
        raise RuntimeContractError("main-read.json has an unknown schema")
    try:
        reads = [k1s.TargetRead.from_dict(read) for read in main_read["reads"]]
        headroom = k1s.HeadroomRead.from_dict(main_read["headroom"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeContractError("main-read.json does not hold complete reads") from exc
    if [read.target for read in reads] != list(TARGETS):
        raise RuntimeContractError("main-read.json must hold one read per registered target")
    verdict = k1s.k1_verdict(reads, headroom)
    if (verdict.verdict != main_read.get("verdict")
            or k1s.extension_targets(verdict, reads) != main_read.get("extension_targets")):
        raise RuntimeContractError("main-read.json disagrees with the registered verdict rules")
    return main_read, hashlib.sha256(payload).hexdigest()


# --------------------------------------------------------------------------- #
# Workers
# --------------------------------------------------------------------------- #


def worker_main(spec_path: Path, flag: rt.SignalFlag) -> int:
    import torch

    from harness import sparse_indexer_k1_runtime_v2 as rt2

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    device = torch.device("cuda:0" if spec["device"] == "cuda" else "cpu")
    profile = rt.Profile.registered() if spec["profile"] == "registered" else rt.Profile.tiny()
    ctx = rt.WorkerContext(
        worker=int(spec["worker"]), out_dir=Path(spec["out_dir"]), ckpt_dir=Path(spec["ckpt_dir"]),
        stage=rt.StagedData(Path(spec["stage_dir"])), model_dir=Path(spec["model_dir"]),
        device=device, flag=flag, hashes=dict(spec["hashes"]))
    spawned_at = spec.get("spawned_at")
    result_path = spec_path.with_name(spec_path.name.replace(".json", ".result.json"))
    try:
        if spec["kind"] == "train":
            result = rt2.run_training_worker(ctx, rt.TrainSpec(**spec["train"]), profile,
                                             spawned_at=spawned_at)
        elif spec["kind"] == "devkl":
            result = rt2.run_devkl_worker(ctx, rt.TrainSpec(**spec["train"]),
                                          spawned_at=spawned_at,
                                          max_sequences=spec.get("max_sequences"))
        else:
            result = rt2.run_eval_worker(ctx, rt.EvalSpec(**spec["eval"]), profile,
                                         spawned_at=spawned_at)
    except CheckpointedExit:
        return EXIT_CHECKPOINTED
    except Exception:  # noqa: BLE001 - every failure is an integrity failure
        traceback.print_exc()
        return EXIT_INTEGRITY
    rt.atomic_write_json(result_path, result)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--worker"]:
        # The parent spawned this worker with SIGUSR1/SIGTERM blocked; install
        # the handler first, then unblock (v1's start-up protocol).
        flag = rt.SignalFlag()
        flag.install()
        signal.pthread_sigmask(signal.SIG_UNBLOCK, WORKER_SIGNALS)
        return worker_main(Path(argv[1]), flag)
    args = parse_args(argv)
    parent = Parent(args)
    try:
        return parent.run()
    except StartupError as exc:
        print(f"CONTRACT: {exc}", file=sys.stderr)
        return EXIT_CONTRACT
    except CheckpointedExit:
        print("CHECKPOINTED: signal-triggered save confirmed; exit 75", file=sys.stderr)
        return EXIT_CHECKPOINTED
    except (RuntimeContractError, budget.BudgetContractError) as exc:
        print(f"INTEGRITY: {exc}", file=sys.stderr)
        return EXIT_INTEGRITY
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return EXIT_INTEGRITY


if __name__ == "__main__":
    raise SystemExit(main())
