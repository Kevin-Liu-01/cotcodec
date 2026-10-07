#!/usr/bin/env python3
"""Synthetic-token throughput probe of the K1 successor code (q3-k1-throughput-probe-v1).

Measurement only: it decides the K1 successor's job limits, never a scientific
quantity. It reads no Belebele text, no bundle and no partition: every token id
is synthetic (NumPy seed 42, uniform over the regular vocabulary, each training
sequence opening with the registered sink token 151643), at the registered
shapes (8,192-token sequences, batch 4, 28 layers, 18 indexers per layer,
evaluation contexts of 8,192 tokens). One GPU.

The parent process holds no GPU memory; each arm runs in a child process
spawned the way the v2 entry point spawns its workers, so start-up (process
start, imports, teacher load, indexer initialisation) is measured from the
spawn, separately from the steady-state times:

1. ``tolerance``  the registered device gates of
   ``harness/sparse_indexer_k1_equivalence_v2.py`` (TF32 bank against v1's
   per-indexer path, the Adam step, slot independence, chunked targets, exact
   selection, one evaluation unit against v1's loop). A failure ends the probe
   ``PROBE_TOLERANCE_FAIL``.
2. ``train``      the binding shard (layers 15-21) as one worker: 8 steps of the
   18-indexer bank (steps 0 and 1 excluded), one checkpoint save, 6 steps with
   the extension's 6 trainable indexers (steps 0 and 1 excluded) and 4
   stream-dev KL sequences (the first excluded); then each other registered
   worker solo, 4 steps (steps 0 and 1 excluded), which checks the per-layer
   composition the limits use (``PROBE_INCONSISTENT`` if a worker is more than
   the 15 percent headroom slower than composed).
3. ``eval``       one worker with 6 indexers per layer on all 28 layers: 13
   selection-only, 13 selection plus multiple-choice and 13 multiple-choice-only
   units at 34 query rows (the audit mean is 33.2), and 5 selection-only units
   at 220 rows (the audit maximum, descriptive); the first unit of each kind is
   excluded.
4. ``capture``    v1's smoke capture and eager check on a synthetic prompt.
5. ``concurrent`` the four registered shards as four workers sharing the one
   GPU (the resume legs' layout): 6 steps each (steps 0 and 1 excluded), and
   each worker's start-up and peak memory.

The receipt holds the measured ``Rates`` and, for the v2 registration to adopt,
the limits ``harness/sparse_indexer_k1_budget_v2.derive_limits`` computes from
them, with the gauntlet check (caps with the probe above 8 GPU-h). A SIGUSR1 or
SIGTERM stops the probe at once (it holds no state worth saving): it writes a
``PROBE_INCOMPLETE`` receipt and exits 3.

Exit codes: 0 complete, 2 contract violation at startup, 3 incomplete or failed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from harness import sparse_indexer_k1_budget_v2 as budget  # noqa: E402
from harness import sparse_indexer_k1_runtime as rt  # noqa: E402

EXPERIMENT_ID = "q3-k1-throughput-probe-v1"
MODEL_ID = "qwen3-0.6b-base"
MODEL_REVISION = "da87bfb608c14b7cf20ba1ce41287e8de496c0cd"
SEEDS = [42, 43, 44]
DATA_SEED = 42
SINK = 151643
EXTENSION_LR = 1e-3  # the 6 trainable indexers' learning rate does not change their cost
EXIT_OK, EXIT_CONTRACT, EXIT_INCOMPLETE = 0, 2, 3
CODE_FILES = (
    "scripts/probe_sparse_indexer_k1_throughput.py",
    "harness/sparse_indexer_bank.py",
    "harness/sparse_indexer_k1_budget_v2.py",
    "harness/sparse_indexer_k1_equivalence_v2.py",
    "harness/sparse_indexer_k1_runtime_v2.py",
    "harness/sparse_indexer_torch.py",
    "harness/sparse_indexer_k1_runtime.py",
    "harness/sparse_indexer_k1_marker.py",
    "scripts/run_sparse_indexer_phase0a.py",
)
ARM_ORDER = ("tolerance", "train", "eval", "capture", "concurrent")


class StartupError(RuntimeError):
    """A fail-closed startup check failed (exit code 2)."""


@dataclass(frozen=True)
class Shapes:
    """Registered probe sizes (``tiny`` exists only for the CPU tests)."""

    name: str
    sequence: int
    batch: int
    binding_shard: int
    train_steps: int
    extension_steps: int
    devkl_sequences: int
    units_per_kind: int
    unit_rows: int
    long_units: int
    long_rows: int
    context: int
    needle: int
    option_tokens: int
    concurrent_steps: int
    tolerance_sequence: int
    solo_steps: int
    timeouts_s: dict[str, float]

    @classmethod
    def registered(cls) -> Shapes:
        return cls("registered", 8192, 4, 2, 8, 6, 4, 13, 34, 5, 220, 8192, 150, 24, 6, 8192, 4,
                   {"tolerance": 150.0, "train": 210.0, "eval": 150.0, "capture": 120.0,
                    "concurrent": 240.0})

    @classmethod
    def tiny(cls) -> Shapes:
        return cls("tiny", 64, 2, 2, 4, 3, 2, 3, 5, 2, 9, 120, 6, 3, 3, 128, 3,
                   {"tolerance": 600.0, "train": 600.0, "eval": 600.0, "capture": 600.0,
                    "concurrent": 900.0})


def shards_for(n_layers: int) -> list[list[int]]:
    from harness import sparse_indexer_torch as sit

    return sit.balanced_layer_shards(n_layers, 4)


def synthetic_tokens(rng: np.random.Generator, rows: int, length: int, vocab: int,
                     sink: bool = True) -> np.ndarray:
    """Uniform ids over the regular vocabulary; column 0 is the sink token."""

    top = min(vocab, SINK)
    out = rng.integers(0, top, size=(rows, length), dtype=np.int64)
    if sink:
        out[:, 0] = SINK if vocab > SINK else 1
    return out


# --------------------------------------------------------------------------- #
# Arms (child processes)
# --------------------------------------------------------------------------- #


def _setup(spec: dict[str, Any]) -> tuple[Any, Any, Shapes, rt.Profile]:
    import torch

    from harness import sparse_indexer_torch as sit

    sit.set_determinism(allow_tf32=True)
    device = torch.device("cuda:0" if spec["device"] == "cuda" else "cpu")
    shapes = Shapes.registered() if spec["profile"] == "registered" else Shapes.tiny()
    profile = rt.Profile.registered() if spec["profile"] == "registered" else rt.Profile.tiny()
    return torch, device, shapes, profile


def _peak(torch: Any, device: Any) -> int | None:
    return int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None


def _train_records(torch: Any, teacher: Any, layers: list[int], banks: Any, steps: int,
                   rng: np.random.Generator, shapes: Shapes, profile: rt.Profile,
                   scaling: float, device: Any, log: Path) -> list[dict[str, Any]]:
    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_k1_runtime_v2 as rt2

    vocab = int(teacher.config.vocab_size)
    records = []
    for step in range(steps):
        started = time.perf_counter()
        batch = torch.as_tensor(synthetic_tokens(rng, shapes.batch, shapes.sequence, vocab),
                                device=device)
        losses, timing = rt2.train_step(teacher, layers, banks, batch, step, profile.warmup,
                                        scaling, device)
        flat = {skb.slot_name(layer, key): float(value) for layer, values in losses.items()
                for key, value in zip(banks.banks[layer].keys, values.tolist(), strict=True)}
        if not all(np.isfinite(list(flat.values()))):
            raise RuntimeError(f"non-finite probe loss at step {step}")
        with log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"step": step, "losses": flat}, sort_keys=True) + "\n")
        timing["step_s"] = time.perf_counter() - started
        records.append(timing)
    return records


def _components(torch: Any, teacher: Any, layers: list[int], banks: Any, shapes: Shapes,
                scaling: float, device: Any, repeats: int = 3) -> dict[str, Any]:
    """Descriptive split of one layer and one sequence (the last of ``repeats`` runs):
    targets alone, targets plus bank forward and backward, the host's enqueue time of
    the latter (close to its wall time means launch-bound), and clipping plus Adam."""

    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_torch as sit

    def sync() -> None:
        if device.type == "cuda":
            torch.cuda.synchronize(device)

    layer = layers[0]
    vocab = int(teacher.config.vocab_size)
    tokens = torch.as_tensor(synthetic_tokens(np.random.default_rng(DATA_SEED + 3), 1,
                                              shapes.sequence, vocab), device=device)
    with sit.CaptureSession(teacher, [layer]) as cap, torch.no_grad():
        teacher.model(input_ids=tokens, use_cache=False)
        q, k, hidden = cap.query[layer][0], cap.key[layer][0], cap.hidden[layer][0]
    bank = banks.banks[layer]
    provide = skb.truncated_targets(q, k, scaling)
    bounds = skb.chunk_bounds(hidden.shape[0], skb.ROW_CHUNK, bank.spec.block_size)
    record: dict[str, Any] = {"layer": layer, "slots": bank.slots}
    for _ in range(repeats):
        sync()
        started = time.perf_counter()
        with torch.no_grad():
            for first, end in bounds:
                provide(first, end)
        sync()
        record["targets_s"] = time.perf_counter() - started
        params = bank.working_params()
        sync()
        started = time.perf_counter()
        bank.accumulate_sequence(params, hidden, provide, grad_scale=1.0)
        record["enqueue_s"] = time.perf_counter() - started
        sync()
        record["targets_plus_bank_s"] = time.perf_counter() - started
        bank.adopt_grads(params)
        del params
        sync()
        started = time.perf_counter()
        bank.clip_()
        for optimiser in bank.optimisers:
            optimiser.zero_grad(set_to_none=True)
        sync()
        record["clip_s"] = time.perf_counter() - started
    record["bank_s"] = record["targets_plus_bank_s"] - record["targets_s"]
    return record


def arm_train(spec: dict[str, Any]) -> dict[str, Any]:
    torch, device, shapes, profile = _setup(spec)
    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_k1_runtime_v2 as rt2
    from harness import sparse_indexer_torch as sit

    out = Path(spec["out_dir"])
    n_layers = int(json.loads((Path(spec["model_dir"]) / "config.json").read_text())[
        "num_hidden_layers"])
    shards = shards_for(n_layers)
    layers = shards[shapes.binding_shard]
    # Every weight is loaded; the forward runs the worker's prefix only, as
    # load_teacher(max_layer=...) arranges for a training worker.
    teacher = sit.load_teacher(spec["model_dir"], device, max_layer=n_layers - 1)
    teacher.config.num_hidden_layers = max(layers) + 1
    scaling = rt2.teacher_scaling(teacher.config)
    ispec = sit.IndexerSpec(d_model=int(teacher.config.hidden_size))
    keys = [rt.indexer_key(t, lr, s) for t in sit.TRAINED_TARGETS for lr in rt.LEARNING_RATES
            for s in SEEDS]
    banks = rt2.WorkerBanks(ispec, layers, keys, set(keys), device)
    startup_s = time.time() - float(spec["spawned_at"])
    rng = np.random.default_rng(DATA_SEED)
    records = _train_records(torch, teacher, layers, banks, shapes.train_steps, rng, shapes,
                             profile, scaling, device, out / "probe-train-loss.jsonl")
    store = rt.CheckpointStore(out / "probe-checkpoint" / "worker-0")
    state_before = banks.state_tensors()
    started = time.perf_counter()
    store.save(shapes.train_steps, banks.state_tensors(), {"probe": EXPERIMENT_ID})
    save_s = time.perf_counter() - started
    shutil.rmtree(out / "probe-checkpoint")
    components = _components(torch, teacher, layers, banks, shapes, scaling, device)
    state = state_before  # the extension and stream-dev arms start from the 8-step state
    peak_main = _peak(torch, device)
    del banks
    ext_keys = [rt.indexer_key(t, EXTENSION_LR, s) for t in sit.TRAINED_TARGETS for s in SEEDS]
    ext_banks = rt2.WorkerBanks(ispec, layers, keys, set(ext_keys), device)
    ext_banks.load_state(state)
    ext_records = _train_records(torch, teacher, layers, ext_banks, shapes.extension_steps,
                                 rng, shapes, profile, scaling, device,
                                 out / "probe-extension-loss.jsonl")
    del ext_banks
    params = {layer: skb.stack_from_state(state, layer, keys, device) for layer in layers}
    runs = skb.target_runs([key.split("|")[0] for key in keys])
    devkl = []
    vocab = int(teacher.config.vocab_size)
    for _ in range(shapes.devkl_sequences):
        tokens = torch.as_tensor(synthetic_tokens(rng, 1, shapes.sequence, vocab), device=device)
        _, timing = rt2.devkl_sequence(teacher, layers, params, runs, ispec, tokens, scaling,
                                       device)
        devkl.append(timing)
    del params, state, state_before
    # Every other registered worker, solo, with the same per-step timing.
    solo = {str(shapes.binding_shard): {"layers": layers, "steps": rt2.summarise_steps(
        records, budget.STEADY_SKIP_STEPS)}}
    for worker, shard in enumerate(shards):
        if worker == shapes.binding_shard:
            continue
        teacher.config.num_hidden_layers = max(shard) + 1
        shard_banks = rt2.WorkerBanks(ispec, shard, keys, set(keys), device)
        shard_records = _train_records(torch, teacher, shard, shard_banks, shapes.solo_steps,
                                       rng, shapes, profile, scaling, device,
                                       out / f"probe-solo-loss-{worker}.jsonl")
        solo[str(worker)] = {"layers": shard, "steps": rt2.summarise_steps(
            shard_records, budget.STEADY_SKIP_STEPS)}
        del shard_banks
    return {"layers": layers, "prefix_layers": max(layers) + 1, "batch": shapes.batch,
            "startup_s": startup_s, "save_s": save_s, "solo": solo,
            "steps": rt2.summarise_steps(records, budget.STEADY_SKIP_STEPS),
            "extension": rt2.summarise_steps(ext_records, budget.STEADY_SKIP_STEPS),
            "devkl": devkl, "components_descriptive": components,
            "peak_memory_bytes": _peak(torch, device),
            "peak_memory_bytes_main_bank": peak_main}


def _unit_plan(shapes: Shapes) -> list[tuple[str, int]]:
    plan = []
    for _ in range(shapes.units_per_kind):
        plan += [("select_only", shapes.unit_rows), ("select_mc", shapes.unit_rows),
                 ("mc_only", shapes.unit_rows)]
    plan += [("select_only_long", shapes.long_rows)] * shapes.long_units
    return plan


def arm_eval(spec: dict[str, Any]) -> dict[str, Any]:
    torch, device, shapes, profile = _setup(spec)
    from harness import sparse_indexer_bank as skb
    from harness import sparse_indexer_k1_runtime_v2 as rt2
    from harness import sparse_indexer_torch as sit

    teacher = sit.load_teacher(spec["model_dir"], device)
    config = teacher.config
    n_layers = int(config.num_hidden_layers)
    scaling = rt2.teacher_scaling(config)
    ispec = sit.IndexerSpec(d_model=int(config.hidden_size))
    keys = [rt.indexer_key(t, EXTENSION_LR, s) for t in sit.TRAINED_TARGETS for s in SEEDS]
    params = {layer: skb.stack_from_state(skb.initial_state(ispec, layer, keys), layer, keys,
                                          device) for layer in range(n_layers)}
    names = rt.selector_names(SEEDS)
    startup_s = time.time() - float(spec["spawned_at"])
    rng = np.random.default_rng(DATA_SEED + 1)
    vocab = int(config.vocab_size)
    records = []
    for index, (kind, rows) in enumerate(_unit_plan(shapes)):
        tokens = synthetic_tokens(rng, 1, shapes.context + rows + 3, vocab)[0]
        q0, q1 = shapes.context + 2, shapes.context + 2 + rows
        n0 = shapes.context // 2
        n1 = n0 + shapes.needle
        select = kind != "mc_only"
        mc = kind in ("select_mc", "mc_only")
        options = [synthetic_tokens(rng, 1, shapes.option_tokens, vocab, sink=False)[0]
                   for _ in range(4)]
        started = time.perf_counter()
        rt2.evaluate_unit(teacher, tokens, q0, q1, n0, n1, do_select=select, do_mc=mc,
                          options=options, option_bytes=[4 * shapes.option_tokens] * 4,
                          answer=0, eval_params=params, n_selectors=len(names),
                          profile=profile, scaling=scaling, ispec=ispec, device=device)
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        records.append({"unit": f"synthetic-{index}", "kind": kind, "select": select, "mc": mc,
                        "rows": rows, "seconds": time.perf_counter() - started})
    regular = [r for r in records if r["kind"] != "select_only_long"]
    long = [r["seconds"] for r in records if r["kind"] == "select_only_long"][budget.UNIT_SKIP:]
    return {"startup_s": startup_s, "units": records,
            "summary": rt2.summarise_units(regular, budget.UNIT_SKIP),
            "select_only_long_mean_s": float(np.mean(long)) if long else None,
            "long_rows": shapes.long_rows, "peak_memory_bytes": _peak(torch, device)}


class SyntheticStaged:
    """The two members of ``StagedData`` v1's capture check reads."""

    def __init__(self, tokens: np.ndarray) -> None:
        self.meta = {"prompts": [{"role": "dev", "prompt_id": "synthetic"}]}
        self._tokens = tokens

    def prompt_tokens(self, prompt: dict[str, Any]) -> tuple[np.ndarray, int, int, int, int]:
        return self._tokens, 0, 0, 0, 0


def arm_capture(spec: dict[str, Any]) -> dict[str, Any]:
    torch, device, shapes, profile = _setup(spec)
    from scripts.run_sparse_indexer_phase0a import smoke_capture_check

    config = json.loads((Path(spec["model_dir"]) / "config.json").read_text())
    tokens = synthetic_tokens(np.random.default_rng(DATA_SEED + 2), 1, shapes.context,
                              int(config["vocab_size"]))[0]
    args = argparse.Namespace(device=spec["device"], model_dir=Path(spec["model_dir"]))
    started = time.perf_counter()
    report = smoke_capture_check(args, SyntheticStaged(tokens), profile)
    seconds = time.perf_counter() - started
    return {"seconds": seconds, "max_rel_output_error": report["max_rel_output_error"],
            "max_layer_mean_tv": report["max_layer_mean_tv"],
            "note": "descriptive: synthetic tokens; the v2 smoke gates the real check",
            "peak_memory_bytes": _peak(torch, device)}


def arm_concurrent_worker(spec: dict[str, Any]) -> dict[str, Any]:
    torch, device, shapes, profile = _setup(spec)
    from harness import sparse_indexer_k1_runtime_v2 as rt2
    from harness import sparse_indexer_torch as sit

    out = Path(spec["out_dir"])
    layers = list(spec["layers"])
    teacher = sit.load_teacher(spec["model_dir"], device, max_layer=max(layers))
    scaling = rt2.teacher_scaling(teacher.config)
    ispec = sit.IndexerSpec(d_model=int(teacher.config.hidden_size))
    keys = [rt.indexer_key(t, lr, s) for t in sit.TRAINED_TARGETS for lr in rt.LEARNING_RATES
            for s in SEEDS]
    banks = rt2.WorkerBanks(ispec, layers, keys, set(keys), device)
    startup_s = time.time() - float(spec["spawned_at"])
    rng = np.random.default_rng(DATA_SEED + 10 + int(spec["worker"]))
    records = _train_records(torch, teacher, layers, banks, shapes.concurrent_steps, rng,
                             shapes, profile, scaling, device,
                             out / f"probe-concurrent-loss-{spec['worker']}.jsonl")
    return {"worker": spec["worker"], "layers": layers, "startup_s": startup_s,
            "steps": rt2.summarise_steps(records, budget.STEADY_SKIP_STEPS),
            "peak_memory_bytes": _peak(torch, device)}


def arm_tolerance(spec: dict[str, Any]) -> dict[str, Any]:
    torch, device, shapes, profile = _setup(spec)
    from harness import sparse_indexer_k1_equivalence_v2 as eq
    from harness import sparse_indexer_torch as sit

    teacher = sit.load_teacher(spec["model_dir"], device)
    report = eq.device_check(teacher, device, profile=profile,
                             length=shapes.tolerance_sequence,
                             layer=min(eq.CHECK_LAYER, int(teacher.config.num_hidden_layers) - 1),
                             unit_rows=shapes.unit_rows, unit_context=shapes.context)
    report["torch"] = torch.__version__
    report["cuda"] = torch.version.cuda
    report["gpu"] = torch.cuda.get_device_name(device) if device.type == "cuda" else None
    report["peak_memory_bytes"] = _peak(torch, device)
    return report


ARMS = {"tolerance": arm_tolerance, "train": arm_train, "eval": arm_eval,
        "capture": arm_capture, "concurrent-worker": arm_concurrent_worker}


# --------------------------------------------------------------------------- #
# Parent
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--expected-receipt-sha256", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--expected-preregistration-sha256", required=True)
    parser.add_argument("--experiment-id", default=EXPERIMENT_ID)
    parser.add_argument("--ledger", type=Path, default=None)
    parser.add_argument("--ledger-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--profile", choices=("registered", "tiny"), default="registered")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    return parser.parse_args(argv)


def startup_checks(args: argparse.Namespace) -> dict[str, Any]:
    from scripts import preregister

    if args.seeds != SEEDS:
        raise StartupError(f"seeds must be exactly {SEEDS} (indexer initialisation)")
    if args.experiment_id != EXPERIMENT_ID:
        raise StartupError(f"experiment id must be {EXPERIMENT_ID}")
    prereg_sha = rt.sha256_file(args.preregistration)
    if prereg_sha != args.expected_preregistration_sha256:
        raise StartupError("preregistration sha256 differs from the expected digest")
    try:
        row = preregister.verify(args.experiment_id, ledger=args.ledger or
                                 preregister.DEFAULT_LEDGER, root=args.ledger_root)
    except preregister.PreregistrationError as exc:
        raise StartupError(f"preregistration ledger check failed: {exc}") from exc
    if row["sha256"] != prereg_sha:
        raise StartupError("ledger row digest differs from the preregistration file")
    receipt_sha = rt.sha256_file(args.receipt)
    if receipt_sha != args.expected_receipt_sha256:
        raise StartupError("model receipt sha256 differs from the expected digest")
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    if args.profile == "registered":
        if receipt.get("model_id") != MODEL_ID or receipt.get("revision") != MODEL_REVISION:
            raise StartupError("the model receipt is not Qwen3-0.6B-Base at the registered "
                               "revision")
        config = json.loads((args.model_dir / "config.json").read_text(encoding="utf-8"))
        if int(config["num_hidden_layers"]) != budget.LAYERS:
            raise StartupError("the registered probe needs the 28-layer model")
    output_root = os.environ.get("COTCODEC_OUTPUT_DIR")
    if output_root:
        manifest_path = Path(output_root) / "manifest.json"
        if not manifest_path.is_file():
            raise StartupError("the batch manifest is missing from the output root")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("seeds") != args.seeds:
            raise StartupError("manifest seeds differ from argv seeds")
        if manifest.get("study_artifact"):
            raise StartupError("the probe reads no study artifact")
    expected = os.environ.get("COTCODEC_EXPECTED_GPUS")
    if args.device == "cuda" and expected is not None and int(expected) != 1:
        raise StartupError("the probe runs on exactly one GPU")
    return {"preregistration_sha256": prereg_sha, "ledger_row_hash": str(row["hash"]),
            "receipt_sha256": receipt_sha,
            "git_sha": os.environ.get("COTCODEC_GIT_SHA", "unknown"),
            "source_sha256": os.environ.get("COTCODEC_SOURCE_SHA256", "unknown"),
            "code": {name: rt.sha256_file(PROJECT_ROOT / name) for name in CODE_FILES}}


class Probe:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.flag = rt.SignalFlag()
        self.flag.install()
        self.out = args.output_dir
        self.results: dict[str, Any] = {}
        self.failures: dict[str, str] = {}
        self.arm_wall_s: dict[str, float] = {}
        self.shapes = Shapes.registered() if args.profile == "registered" else Shapes.tiny()

    def _spawn(self, arm: str, spec: dict[str, Any], label: str) -> tuple[subprocess.Popen,
                                                                           Path]:
        path = self.out / "arms" / f"{label}.json"
        rt.atomic_write_json(path, {**spec, "spawned_at": time.time()})
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--arm", arm,
                                    "--spec", str(path)], env=dict(os.environ))
        return process, path

    def _wait(self, processes: list[subprocess.Popen], timeout: float) -> str | None:
        deadline = time.monotonic() + timeout
        while any(p.poll() is None for p in processes):
            if self.flag.received:
                reason = f"stopped by {self.flag.received}"
            elif time.monotonic() > deadline:
                reason = f"timed out after {timeout:.0f} s"
            else:
                time.sleep(0.2)
                continue
            for process in processes:
                if process.poll() is None:
                    process.kill()
            for process in processes:
                process.wait()
            return reason
        codes = [p.returncode for p in processes]
        return None if all(code == 0 for code in codes) else f"exit codes {codes}"

    def run_arm(self, arm: str) -> None:
        base = {"model_dir": str(self.args.model_dir), "device": self.args.device,
                "profile": self.args.profile, "out_dir": str(self.out)}
        started = time.perf_counter()
        if arm == "concurrent":
            n_layers = int(json.loads((self.args.model_dir / "config.json").read_text())[
                "num_hidden_layers"])
            spawned = [self._spawn("concurrent-worker", {**base, "worker": w, "layers": layers},
                                   f"concurrent-{w}")
                       for w, layers in enumerate(shards_for(n_layers))]
            failure = self._wait([p for p, _ in spawned], self.shapes.timeouts_s[arm])
            if failure is None:
                self.results[arm] = [json.loads(path.with_suffix(".result.json").read_text())
                                     for _, path in spawned]
        else:
            process, path = self._spawn(arm, base, arm)
            failure = self._wait([process], self.shapes.timeouts_s[arm])
            if failure is None:
                self.results[arm] = json.loads(path.with_suffix(".result.json").read_text())
        self.arm_wall_s[arm] = time.perf_counter() - started
        if failure is not None:
            self.failures[arm] = failure

    def rates(self) -> budget.Rates:
        train, evaluation = self.results["train"], self.results["eval"]
        steps, ext = train["steps"], train["extension"]
        n_layers, prefix = len(train["layers"]), train["prefix_layers"]
        sequences = train["devkl"][budget.UNIT_SKIP:] or train["devkl"]
        summary = evaluation["summary"]
        concurrent = self.results["concurrent"]
        return budget.Rates(
            teacher_layer_seq_s=steps["teacher_s"] / (train["batch"] * prefix),
            layer_step_s=steps["layers_total_s"] / n_layers,
            layer_step_ext_s=ext["layers_total_s"] / n_layers,
            step_overhead_s=max(0.0, steps["overhead_s"]),
            devkl_teacher_layer_seq_s=float(np.mean([s["teacher_s"] for s in sequences]))
            / prefix,
            devkl_layer_seq_s=float(np.mean([sum(s["layers_s"].values()) for s in sequences]))
            / n_layers,
            save_layer_s=train["save_s"] / n_layers,
            train_startup_s=train["startup_s"],
            eval_startup_s=evaluation["startup_s"],
            eval_select_s=summary["select_only"]["mean_s"],
            eval_select_mc_s=summary["select_mc"]["mean_s"],
            eval_mc_only_s=summary["mc_only"]["mean_s"],
            eval_rows=summary["selection_mean_rows"],
            capture_check_s=self.results["capture"]["seconds"],
            concurrent_step_s=max(w["steps"]["step_s"] for w in concurrent),
            concurrent_startup_s=max(w["startup_s"] for w in concurrent))

    def run(self) -> int:
        receipt_path = self.out / "receipt.json"
        if receipt_path.exists():
            raise StartupError(f"{receipt_path} exists; a rerun needs a new output directory")
        self.out.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        hashes = startup_checks(self.args)
        startup_s = time.perf_counter() - started
        for arm in ARM_ORDER:
            if self.flag.received:
                self.failures[arm] = f"not run: {self.flag.received} received"
                continue
            if arm != "tolerance" and "tolerance" in self.failures:
                self.failures[arm] = "not run: the tolerance arm failed"
                continue
            self.run_arm(arm)
            if arm == "tolerance" and "tolerance" in self.results and not self.results[
                    "tolerance"]["passed"]:
                self.failures["tolerance"] = "registered device tolerance gates failed"
        payload: dict[str, Any] = {
            "experiment_id": EXPERIMENT_ID, "profile": self.args.profile,
            "seeds": SEEDS, "data": "synthetic token ids (NumPy seed 42); no bundle, no "
                                   "Belebele, no partition read",
            "shapes": asdict(self.shapes), "hashes": hashes, "arms": self.results,
            "failures": self.failures, "arm_wall_s": self.arm_wall_s,
            "startup_checks_s": startup_s, "slurm_job_id": os.environ.get("SLURM_JOB_ID")}
        if "tolerance" in self.failures and "tolerance" in self.results:
            status = "PROBE_TOLERANCE_FAIL"
        elif self.failures or set(self.results) != set(ARM_ORDER):
            status = "PROBE_INCOMPLETE"
        else:
            status = "PROBE_COMPLETE"
        if status == "PROBE_COMPLETE":
            rates = self.rates()
            payload["rates"] = rates.as_dict()
            payload["composition_check"] = composition_check(rates, self.results["train"])
            if not payload["composition_check"]["passed"] and self.args.profile == "registered":
                status = "PROBE_INCONSISTENT"  # the tiny CPU profile reports it only
            else:
                payload["derived_limits"] = budget.derive_limits(rates)
                payload["limits_table"] = budget.limits_table(payload["derived_limits"])
        payload["status"] = status
        payload["wall_s"] = time.perf_counter() - started
        rt.atomic_write_json(receipt_path, payload)
        print(json.dumps({"status": status, "failures": self.failures,
                          "total_gpu_hours_with_probe": payload.get("derived_limits", {}).get(
                              "total_gpu_hours_with_probe")}))
        return EXIT_OK if status == "PROBE_COMPLETE" else EXIT_INCOMPLETE


def composition_check(rates: budget.Rates, train: dict[str, Any]) -> dict[str, Any]:
    """Each registered worker's solo steady step against the composition the limits use.

    The probe and the v2 smoke both project a worker's step as
    ``4 x prefix x teacher + layers x layer step + overhead`` from per-layer
    rates; a worker slower than that by more than the headroom would make
    every limit, and the smoke's gate, too short for it.
    """

    workers = {}
    for worker, entry in sorted(train["solo"].items()):
        composed = budget.shard_step_s(rates, entry["layers"])
        direct = float(entry["steps"]["step_s"])
        workers[worker] = {"layers": entry["layers"], "direct_step_s": direct,
                           "composed_step_s": composed, "ratio": direct / composed}
    limit = 1.0 + budget.HEADROOM
    return {"workers": workers, "max_ratio": max(w["ratio"] for w in workers.values()),
            "limit": limit, "passed": all(w["ratio"] <= limit for w in workers.values())}


def arm_main(arm: str, spec_path: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    try:
        result = ARMS[arm](spec)
    except Exception:  # noqa: BLE001 - an arm that fails is reported, never retried
        traceback.print_exc()
        return EXIT_INCOMPLETE
    rt.atomic_write_json(spec_path.with_suffix(".result.json"), result)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--arm"]:
        signal.signal(signal.SIGUSR1, signal.SIG_DFL)
        return arm_main(argv[1], Path(argv[argv.index("--spec") + 1]))
    args = parse_args(argv)
    try:
        return Probe(args).run()
    except StartupError as exc:
        print(f"CONTRACT: {exc}", file=sys.stderr)
        return EXIT_CONTRACT


if __name__ == "__main__":
    raise SystemExit(main())
