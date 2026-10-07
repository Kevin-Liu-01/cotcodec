#!/usr/bin/env python3
"""GPU entry point of the Q3 K1 localization screen (preregistration q3-k1-localization-screen-v1).

Phases:

``smoke``         bf16 capture consistency (recomputed probabilities reproduce the
                  SDPA attention output) and an eager-attention sanity check on 64
                  rows x every layer at 8K; a 16-sequence training timing; a
                  20-unit indexer-versus-target recall smoke; timing projections.
``headroom-dev``  dense-only pre-check on the development partition: H1, H2a,
                  H2b, the no-haystack reference and se_cluster of Delta_T and
                  Delta_U.
``resume-test``   training only, ``--stop-after-step`` (and ``--hold-after-step``
                  for the interrupted leg); per-worker final state digests.
``0a-k1``         train 18 indexers per layer, stream-dev KL, LR freeze (hashed
                  before any audit read), audit evaluation, statistics, verdict.
``0a-k1-extend``  the registered V1 extension: epochs 2-3 for the frozen-LR
                  indexers, then one re-evaluation.

The process is PID 1 in its container. It installs SIGUSR1/SIGTERM handlers,
forwards a received signal to its workers, reaps them, and writes the
checkpoint marker (with the line ``trigger=SIG<name>`` the batch script
requires) only after every running worker acknowledged a completed
signal-triggered save (a stale marker is deleted first). Exit codes: 0
complete, 2 contract violation at startup, 3 integrity failure, 75
checkpointed and incomplete.
"""

from __future__ import annotations

import argparse
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
EXPERIMENT_ID = "q3-k1-localization-screen-v1"
CONTRACT_NAME = "translation-supervised-sparse-indexer-k1-screen"
TARGETS = ("hs", "mp")
SMOKE_ROWS = 64
SMOKE_UNITS = 20
SMOKE_TRAIN_STEPS = 4
CAPTURE_REL_ERROR_MAX = 1e-2
EAGER_TV_MAX = 0.10
MAIN_BUDGET_GPU_HOURS = 2.0
CODE_FILES = (
    "scripts/run_sparse_indexer_phase0a.py",
    "harness/sparse_indexer_torch.py",
    "harness/sparse_indexer_k1_runtime.py",
    "harness/sparse_indexer_k1_marker.py",
    "harness/sparse_indexer_k1_stats.py",
    "harness/sparse_indexer_data.py",
    "harness/translation_supervised_indexer.py",
)


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
    return parser.parse_args(argv)


# --------------------------------------------------------------------------- #
# Startup checks
# --------------------------------------------------------------------------- #


def _sha(path: Path) -> str:
    return rt.sha256_file(path)


def startup_checks(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any], dict]:
    """Fail closed before any work; returns (bundle, contract, hashes)."""

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
    return bundle, contract, hashes


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

    # -- signal protocol --------------------------------------------------- #

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
        for spec in specs:
            worker = int(spec["worker"])
            path = spec_dir / f"worker-{worker}.json"
            rt.atomic_write_json(path, spec)
            env = dict(os.environ)
            if self.args.device == "cuda":
                env["CUDA_VISIBLE_DEVICES"] = str(worker % n_devices)
            children.append((worker, subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--worker", str(path)], env=env)))
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

    def base_spec(self, worker: int, kind: str) -> dict[str, Any]:
        return {"worker": worker, "kind": kind, "out_dir": str(self.out),
                "ckpt_dir": str(self.ckpt), "stage_dir": str(self.stage_dir),
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
                   accept_config_digests: list[str] | None = None) -> rt.TrainSpec:
        every = self.args.checkpoint_every or self.profile.checkpoint_every
        return rt.TrainSpec(layers=layers, seeds=list(self.args.seeds), targets=list(TARGETS),
                            lrs=list(rt.LEARNING_RATES), steps=steps, batch=self.profile.batch,
                            warmup=self.profile.warmup, checkpoint_every=every,
                            stop_after_step=self.args.stop_after_step,
                            hold_after_step=self.args.hold_after_step, epochs=epochs,
                            train_only=train_only,
                            accept_config_digests=accept_config_digests)

    def total_steps(self, staged: rt.StagedData) -> int:
        n_train = int(staged.array("train_tokens").shape[0])
        return self.profile.steps or n_train // self.profile.batch

    def train(self, staged: rt.StagedData, label: str, shards: list[list[int]], steps: int,
              **kwargs: Any) -> list[dict[str, Any]]:
        specs = []
        for worker, layers in enumerate(shards):
            spec = self.base_spec(worker, "train")
            spec["train"] = asdict(self.train_spec(layers, steps, **kwargs))
            specs.append(spec)
        return self.run_workers(specs, label)

    def training_complete(self, shards: list[list[int]], steps: int) -> bool:
        for worker in range(len(shards)):
            generations = rt.CheckpointStore(self.ckpt / f"worker-{worker}").generations()
            if not generations or generations[-1] < steps:
                return False
        return True

    def evaluate(self, staged: rt.StagedData, stage: str, units: list[dict[str, Any]],
                 with_indexers: bool, freeze: tuple[str, str] | None,
                 shards: list[list[int]], workers: int) -> None:
        per_worker = [units[w::workers] for w in range(workers)]
        specs = []
        for worker, assigned in enumerate(per_worker):
            spec = self.base_spec(worker, "eval")
            spec["eval"] = asdict(rt.EvalSpec(
                stage=stage, units=assigned, seeds=list(self.args.seeds),
                with_indexers=with_indexers,
                lr_freeze_path=freeze[0] if freeze else None,
                lr_freeze_sha256=freeze[1] if freeze else None, train_layers=shards))
            specs.append(spec)
        self.run_workers(specs, f"eval-{stage}")

    def write_receipt(self, name: str, payload: dict[str, Any]) -> str:
        payload = {**payload, "hashes": self.hashes, "timings_s": self.timings,
                   "experiment_id": self.args.experiment_id, "phase": self.args.phase,
                   "profile": self.profile.name, "seeds": list(self.args.seeds),
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
        bundle, contract, hashes = startup_checks(args)
        self.hashes = hashes
        self.contract = contract
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
            "workers": results,
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

    def phase_headroom_dev(self, staged: rt.StagedData) -> int:
        units, prompt_to_unit, prompts = self._units(
            staged, "development", {"dev"}, {"dev", "dev-absent", "dev-nohaystack"}, {"CX"})
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

    def phase_smoke(self, staged: rt.StagedData) -> int:
        report: dict[str, Any] = {}
        report["capture"] = smoke_capture_check(self.args, staged, self.profile)
        shards = [list(range(self.model_layers()))]
        steps = SMOKE_TRAIN_STEPS
        saved_stop = self.args.stop_after_step
        self.args.stop_after_step = steps
        started = time.perf_counter()
        train_results = self.train(staged, "smoke-train", shards, self.total_steps(staged))
        self.args.stop_after_step = saved_stop
        report["training"] = {"sequences": steps * self.profile.batch,
                              "wall_s": time.perf_counter() - started,
                              "worker_timings": train_results[0]["timings"]}
        freeze = {"rule": "smoke only: LR 1e-3 for both targets, no stream-dev KL",
                  "selected_lr": {t: rt.lr_tag(1e-3) for t in TARGETS}}
        freeze_path = self.ckpt / "smoke-lr.json"
        freeze_sha = rt.atomic_write_json(freeze_path, freeze)
        units, _, _ = self._units(staged, "development", {"dev"}, set(), set())
        units = [unit for unit in units if unit["select"]][:SMOKE_UNITS]
        started = time.perf_counter()
        self.evaluate(staged, "smoke", units, True, (str(freeze_path), freeze_sha), shards, 1)
        eval_s = time.perf_counter() - started
        merged = rt.collect_eval(self.ckpt, "smoke", {u["unit"]: u["unit"] for u in units})
        recalls = np.stack([row["recall"] for row in merged["rows"].values()])
        report["recall_smoke"] = {
            "units": len(units), "finite": bool(np.isfinite(recalls).all()),
            "mean_recall_by_selector": dict(zip(merged["selectors"], np.nanmean(
                recalls, axis=(0, 1)).tolist(), strict=True)),
            "max_selected_tokens": int(max(r["max_selected"] for r in merged["rows"].values())),
            "eval_wall_s_per_unit": eval_s / max(len(units), 1),
        }
        report["projection"] = project_main_cost(report, self.model_layers(),
                                                 self.total_steps(staged), staged,
                                                 self.profile)
        k_limit = self.profile.k_blocks * 4 + 3
        gates = {
            "capture_reconstruction": report["capture"]["max_rel_output_error"]
            <= CAPTURE_REL_ERROR_MAX,
            "eager_sanity": report["capture"]["max_layer_mean_tv"] <= EAGER_TV_MAX,
            "recall_finite": report["recall_smoke"]["finite"],
            "selection_budget": report["recall_smoke"]["max_selected_tokens"] <= k_limit,
        }
        report["gates"] = gates
        status = "SMOKE_PASS" if all(gates.values()) else "SMOKE_FAIL"
        if status == "SMOKE_PASS" and report["projection"]["main_gpu_hours"] > (
                MAIN_BUDGET_GPU_HOURS):
            status = "SMOKE_PASS_OVER_BUDGET"
        self.write_receipt("receipt.json", {"status": status, **report})
        return EXIT_OK if all(gates.values()) else EXIT_INTEGRITY

    def _main_flow(self, staged: rt.StagedData, *, extension: bool) -> int:
        n_layers = self.model_layers()
        shards = self.layer_shards(n_layers, self.args.workers)
        steps = self.total_steps(staged)
        freeze_path = self.ckpt / "lr_freeze.json"
        training: list[dict[str, Any]] = []
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
                freeze = rt.freeze_learning_rates(devkl, TARGETS, rt.LEARNING_RATES,
                                                  self.args.seeds)
                freeze["written_before_audit_read"] = True
                rt.atomic_write_json(freeze_path, freeze)
            stage = "audit-main"
        else:
            if not freeze_path.is_file():
                raise RuntimeContractError("the extension needs the main run's LR freeze")
            freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
            keys = [rt.indexer_key(t, freeze["selected_lr_value"][t], s)
                    for t in TARGETS for s in self.args.seeds]
            total = steps * 3
            if not self.training_complete(shards, total):
                accept = [rt.config_digest(self.train_spec(layers, steps), self.profile,
                                           self.hashes) for layers in shards]
                training = self.train(staged, "train-extension", shards, total, epochs=3,
                                      train_only=keys, accept_config_digests=accept)
            stage = "audit-extension"
        freeze_sha = rt.sha256_file(freeze_path)
        self.hashes["lr_freeze_sha256"] = freeze_sha
        if self.flag.received:
            self.checkpoint_without_workers()
        units, prompt_to_unit, prompts = self._units(
            staged, "audit", {"main", "same-script", "literal"}, {"main", "absent"},
            {"MN", "CX"})
        self.evaluate(staged, stage, units, True, (str(freeze_path), freeze_sha), shards,
                      self.args.workers)
        if self.flag.received:
            self.checkpoint_without_workers()
        results = rt.collect_eval(self.ckpt, stage, prompt_to_unit)
        report = self.statistics(prompts, results, staged.meta["context_meta"])
        report["training_workers"] = [
            {key: result.get(key) for key in ("worker", "final_step", "state_digest", "timings",
                                               "resumed_from")} for result in training]
        report["lr_freeze"] = freeze
        report["units"] = results["units"]
        devkl_all = {}
        for worker in range(len(shards)):
            path = self.ckpt / "devkl" / f"worker-{worker}.json"
            if path.is_file():
                devkl_all.update(json.loads(path.read_text(encoding="utf-8"))["kl"])
        report["stream_dev_kl"] = devkl_all
        report["bundle_reports"] = self.bundle_reports
        name = "receipt-extension.json" if extension else "receipt.json"
        self.write_receipt(name, report)
        return EXIT_OK if report["verdict"]["verdict"] != "VOID" else EXIT_INTEGRITY

    def phase_main(self, staged: rt.StagedData) -> int:
        return self._main_flow(staged, extension=False)

    def phase_extend(self, staged: rt.StagedData) -> int:
        return self._main_flow(staged, extension=True)

    def statistics(self, prompts: list, results: dict,
                   context_meta: list[dict[str, Any]]) -> dict[str, Any]:
        seeds = list(self.args.seeds)
        rows, selectors = results["rows"], results["selectors"]
        k_limit = self.profile.k_blocks * 4 + 3
        # Non-finite recall on a selection unit raises inside prompt_recall (exit 3);
        # the remaining V3 item checked here is the achieved budget.
        integrity = all(row["max_selected"] <= k_limit for row in rows.values())
        literal_en = [p for p in prompts if p["role"] == "literal" and p["pair"] == "en>en"]
        reads, report = [], {"targets": {}}
        for target in TARGETS:
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
        verdict = k1s.k1_verdict(reads, headroom_read)
        report["headroom"] = {"h1_by_target": headroom["h1_by_target"],
                              "h1_points": headroom["h1_points"],
                              "h2a": rt.interval_dict(headroom["h2a"]),
                              "h2b": rt.interval_dict(headroom["h2b"]),
                              "needle_absent_accuracy": headroom["absent_accuracy"]}
        report["verdict"] = {"verdict": verdict.verdict, "reasons": list(verdict.reasons)}
        report["seed_noise"] = k1s.seed_noise_report(
            {t: report["targets"][t]["cx_recall_by_seed"] for t in TARGETS})
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
        return report


def smoke_capture_check(args: argparse.Namespace, staged: rt.StagedData,
                        profile: rt.Profile) -> dict[str, Any]:
    """Capture consistency and eager sanity on SMOKE_ROWS rows of one dev prompt."""

    import torch
    from transformers.integrations.sdpa_attention import repeat_kv
    from transformers.models.qwen3.modeling_qwen3 import eager_attention_forward

    from harness import sparse_indexer_torch as sit

    sit.set_determinism(allow_tf32=True)
    device = torch.device("cuda:0" if args.device == "cuda" else "cpu")
    prompt = next(p for p in staged.meta["prompts"] if p["role"] == "dev")
    tokens, _, _, _, _ = staged.prompt_tokens(prompt)
    length = len(tokens)
    rng = np.random.default_rng(42)
    rows_np = np.sort(rng.choice(np.arange(3, length), size=min(SMOKE_ROWS, length - 3),
                                 replace=False))
    rows = torch.as_tensor(rows_np, device=device)
    ids = torch.as_tensor(tokens.astype(np.int64), device=device)[None]
    teacher = sit.load_teacher(args.model_dir, device)
    n_layers = int(teacher.config.num_hidden_layers)
    scaling = float(teacher.config.head_dim) ** -0.5
    out: dict[str, Any] = {"rows": len(rows_np), "length": length, "per_layer": []}
    with sit.CaptureSession(teacher, range(n_layers), query_rows=rows, keep_values=True) as cap, \
            torch.no_grad():
        teacher.model(input_ids=ids, use_cache=False)
        captured = {layer: (cap.query[layer][0], cap.key[layer][0], cap.value[layer][0],
                            cap.output[layer][0]) for layer in range(n_layers)}
    eager_rows: dict[int, torch.Tensor] = {}

    def eager_rows_attention(module, query, key, value, attention_mask, **kwargs):
        output, weights = eager_attention_forward(module, query, key, value, attention_mask,
                                                  **kwargs)
        eager_rows[int(module.layer_idx)] = weights[0].index_select(1, rows).float()
        return output, None

    from transformers import AttentionInterface
    from transformers.masking_utils import AttentionMaskInterface, eager_mask

    AttentionInterface.register("cotcodec_eager_rows", eager_rows_attention)
    AttentionMaskInterface.register("cotcodec_eager_rows", eager_mask)
    eager = sit.load_teacher(args.model_dir, device, attn_implementation="cotcodec_eager_rows")
    with torch.no_grad():
        eager.model(input_ids=ids, use_cache=False)
    del eager
    worst_rel, worst_tv = 0.0, 0.0
    for layer in range(n_layers):
        q, k, v, sdpa_out = captured[layer]
        probs = sit.head_probs_rows(q, k, rows, scaling)
        groups = q.shape[0] // k.shape[0]
        v_rep = repeat_kv(v[None], groups)[0].float()
        recon = torch.matmul(probs, v_rep).transpose(0, 1)
        reference = sdpa_out.float()
        rel = float((recon - reference).abs().max() / reference.abs().max().clamp_min(1e-12))
        mine = probs.sum(0)
        mine = mine / mine.sum(-1, keepdim=True)
        theirs = eager_rows[layer].sum(0)
        theirs = theirs / theirs.sum(-1, keepdim=True)
        tv = 0.5 * (mine - theirs).abs().sum(-1)
        dense_mine = sit.block_targets(probs, rows)
        dense_theirs = sit.block_targets(eager_rows[layer], rows)
        a = sit.select_top_blocks(dense_mine["hs"], dense_mine["valid"], profile.k_blocks)
        b = sit.select_top_blocks(dense_theirs["hs"], dense_theirs["valid"], profile.k_blocks)
        jaccards = []
        for i in range(a.shape[0]):
            sa = {int(x) for x in a[i] if int(x) >= 0}
            sb = {int(x) for x in b[i] if int(x) >= 0}
            jaccards.append(len(sa & sb) / max(len(sa | sb), 1))
        out["per_layer"].append({"layer": layer, "rel_output_error": rel,
                                 "mean_tv": float(tv.mean()), "max_tv": float(tv.max()),
                                 "hs_block_jaccard": float(np.mean(jaccards))})
        worst_rel = max(worst_rel, rel)
        worst_tv = max(worst_tv, float(tv.mean()))
    out["max_rel_output_error"] = worst_rel
    out["max_layer_mean_tv"] = worst_tv
    out["thresholds"] = {"rel_output_error": CAPTURE_REL_ERROR_MAX, "mean_tv": EAGER_TV_MAX}
    eager_rows.clear()
    del teacher, captured
    if device.type == "cuda":
        torch.cuda.empty_cache()  # the training worker shares this GPU next
    return out


def project_main_cost(report: dict[str, Any], n_layers: int, steps: int,
                      staged: rt.StagedData, profile: rt.Profile) -> dict[str, Any]:
    """Project the 4-worker main job from the single-worker smoke timings."""

    timings = report["training"]["worker_timings"]
    sequences = max(report["training"]["sequences"], 1)
    teacher_per_layer_seq = timings["teacher_s"] / sequences / n_layers
    targets_per_layer_seq = timings["targets_s"] / sequences / n_layers
    indexers_per_layer_seq = timings["indexers_s"] / sequences / n_layers
    from harness import sparse_indexer_torch as sit

    shards = sit.balanced_layer_shards(n_layers, 4) if n_layers >= 4 else [list(range(n_layers))]
    train_seqs = steps * profile.batch
    dev_seqs = int(staged.array("dev_tokens").shape[0])
    per_worker = []
    for layers in shards:
        prefix = (max(layers) + 1) * teacher_per_layer_seq
        own = len(layers) * (targets_per_layer_seq + indexers_per_layer_seq)
        per_worker.append(train_seqs * (prefix + own) + dev_seqs * (
            prefix + len(layers) * (targets_per_layer_seq + indexers_per_layer_seq / 3)))
    audit_units = len({(p["context_index"], p["query_index"]) for p in staged.meta["prompts"]
                       if p["partition"] == "audit"})
    eval_s = audit_units * report["recall_smoke"]["eval_wall_s_per_unit"] / len(shards)
    wall = max(per_worker) + eval_s + 300.0
    return {"train_wall_s_per_worker": per_worker, "eval_wall_s": eval_s,
            "startup_allowance_s": 300.0, "main_wall_minutes": wall / 60.0,
            "main_gpu_hours": wall * len(shards) / 3600.0,
            "note": "single-GPU smoke timings scaled to the registered 4-worker layout"}


# --------------------------------------------------------------------------- #
# Workers
# --------------------------------------------------------------------------- #


def worker_main(spec_path: Path) -> int:
    import torch

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    flag = rt.SignalFlag()
    flag.install()
    device = torch.device("cuda:0" if spec["device"] == "cuda" else "cpu")
    profile = rt.Profile.registered() if spec["profile"] == "registered" else rt.Profile.tiny()
    ctx = rt.WorkerContext(
        worker=int(spec["worker"]), out_dir=Path(spec["out_dir"]), ckpt_dir=Path(spec["ckpt_dir"]),
        stage=rt.StagedData(Path(spec["stage_dir"])), model_dir=Path(spec["model_dir"]),
        device=device, flag=flag, hashes=dict(spec["hashes"]))
    result_path = spec_path.with_name(spec_path.name.replace(".json", ".result.json"))
    try:
        if spec["kind"] == "train":
            result = rt.run_training_worker(ctx, rt.TrainSpec(**spec["train"]), profile)
        elif spec["kind"] == "devkl":
            result = rt.run_devkl_worker(ctx, rt.TrainSpec(**spec["train"]))
        else:
            result = rt.run_eval_worker(ctx, rt.EvalSpec(**spec["eval"]), profile)
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
        return worker_main(Path(argv[1]))
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
    except RuntimeContractError as exc:
        print(f"INTEGRITY: {exc}", file=sys.stderr)
        return EXIT_INTEGRITY
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return EXIT_INTEGRITY


if __name__ == "__main__":
    raise SystemExit(main())
